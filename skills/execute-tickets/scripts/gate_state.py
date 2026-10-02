#!/usr/bin/env python3
"""Capture and compare deterministic final-gate input manifests."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from review_state import (
    StateError,
    git,
    load_snapshot,
    path_is_ignored,
    repository_root,
    sha256,
    split_paths,
)


FORMAT_VERSION = 1
MAX_COMMAND_BYTES = 1024 * 1024
MAX_DECLARATIONS = 256
SUPPORTED_FILE_MODES = {"100644", "100755", "120000"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
OBJECT_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StateError(f"manifest field {field} must be a non-empty string")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def normalize_gate_id(raw: str) -> str:
    if not raw or raw != raw.strip() or len(raw) > 128:
        raise StateError("gate id must be 1-128 characters without surrounding space")
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise StateError("gate id must not contain control characters")
    return raw


def normalize_input_paths(repo: Path, raw_paths: list[str]) -> list[str]:
    if not raw_paths:
        raise StateError("at least one explicit gate input path is required")
    if len(raw_paths) > MAX_DECLARATIONS:
        raise StateError(f"gate input declarations exceed {MAX_DECLARATIONS} paths")

    normalized: list[str] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        if (
            not raw_path
            or candidate.is_absolute()
            or raw_path in {".", ".."}
            or ".." in candidate.parts
        ):
            raise StateError(
                f"gate input must be an exact repository-relative file or directory: {raw_path!r}"
            )
        if any(character in raw_path for character in "*?[]"):
            raise StateError(f"gate input must not contain glob syntax: {raw_path!r}")

        relative = candidate.as_posix()
        absolute = repo / relative
        if not os.path.lexists(absolute):
            raise StateError(f"gate input does not exist in the working tree: {relative}")
        info = absolute.lstat()
        if not (
            stat.S_ISREG(info.st_mode)
            or stat.S_ISDIR(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
        ):
            raise StateError(f"gate input is not a regular file, directory, or symlink: {relative}")
        normalized.append(relative)

    if len(set(normalized)) != len(normalized):
        raise StateError("gate input declarations must not contain duplicates")

    ordered = sorted(normalized)
    for position, first in enumerate(ordered):
        prefix = first.rstrip("/") + "/"
        for second in ordered[position + 1 :]:
            if second.startswith(prefix):
                raise StateError(
                    "gate input declarations must not overlap: "
                    f"{first!r} contains {second!r}"
                )
    return ordered


def parse_index_entries(raw: bytes) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, separator, raw_path = record.partition(b"\t")
        fields = header.decode("ascii", errors="strict").split()
        if not separator or len(fields) != 3:
            raise StateError("Git returned a malformed index entry")
        mode, object_id, stage = fields
        path = os.fsdecode(raw_path)
        if stage != "0":
            raise StateError(f"gate input has an unmerged index entry: {path}")
        if mode not in SUPPORTED_FILE_MODES:
            if mode == "160000":
                raise StateError(f"gate input contains a Git submodule: {path}")
            raise StateError(f"gate input has an unsupported Git mode {mode}: {path}")
        if not OBJECT_PATTERN.fullmatch(object_id) or set(object_id) == {"0"}:
            raise StateError(f"gate input has an invalid Git object id: {path}")
        entries.append({"path": path, "mode": mode, "object": object_id})
    return entries


def expand_index_entries(repo: Path, declarations: list[str]) -> list[dict[str, str]]:
    entries_by_path: dict[str, dict[str, str]] = {}
    for declaration in declarations:
        absolute = repo / declaration
        raw = git(
            repo,
            "--literal-pathspecs",
            "ls-files",
            "--stage",
            "-z",
            "--",
            declaration,
        )
        entries = parse_index_entries(raw)
        if not entries:
            raise StateError(
                f"gate input does not expand to a tracked index entry: {declaration}"
            )
        if absolute.is_symlink() or absolute.is_file():
            if len(entries) != 1 or entries[0]["path"] != declaration:
                raise StateError(f"gate input is not an exact tracked file: {declaration}")
        else:
            prefix = declaration.rstrip("/") + "/"
            if any(not entry["path"].startswith(prefix) for entry in entries):
                raise StateError(
                    f"gate input directory expanded outside its boundary: {declaration}"
                )
        for entry in entries:
            prior = entries_by_path.get(entry["path"])
            if prior is not None and prior != entry:
                raise StateError(f"gate input has conflicting index entries: {entry['path']}")
            entries_by_path[entry["path"]] = entry

    return [entries_by_path[path] for path in sorted(entries_by_path)]


def assess_worktree(repo: Path, declarations: list[str]) -> None:
    unstaged = sorted(
        split_paths(
            git(
                repo,
                "--literal-pathspecs",
                "diff",
                "--name-only",
                "--no-renames",
                "-z",
                "--",
                *declarations,
            )
        )
    )
    if unstaged:
        raise StateError(
            "gate inputs differ between the working tree and index: "
            + ", ".join(unstaged[:20])
        )

    untracked = sorted(
        split_paths(
            git(
                repo,
                "--literal-pathspecs",
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                *declarations,
            )
        )
    )
    if untracked:
        raise StateError(
            "gate input boundary contains non-ignored untracked paths: "
            + ", ".join(untracked[:20])
        )


def read_command(path: Path) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise StateError(f"cannot read gate command file {path}: {error}") from error
    if len(raw) > MAX_COMMAND_BYTES:
        raise StateError(f"gate command exceeds {MAX_COMMAND_BYTES} bytes")
    try:
        command = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise StateError("gate command must be UTF-8") from error
    if not command.strip():
        raise StateError("gate command must not be empty")
    return (command.rstrip("\r\n") + "\n").encode("utf-8")


def ensure_output_excluded_from_candidates(output: Path, repo: Path) -> Path:
    """Allow an in-repository artifact path only when Git ignores it."""
    resolved = output.resolve(strict=False)
    try:
        relative = resolved.relative_to(repo)
    except ValueError:
        return resolved
    if not path_is_ignored(repo, relative):
        raise StateError(
            "gate manifest output inside the working tree must be ignored by Git: "
            + relative.as_posix()
        )
    return resolved


def write_new_file(output: Path, content: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as error:
            raise StateError(f"gate manifest output already exists: {output}") from error
        except OSError as error:
            raise StateError(f"cannot create gate manifest {output}: {error}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def manifest_without_fingerprint(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "input_fingerprint"}


def validate_manifest(manifest: Any, source: Path) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise StateError(f"gate manifest is not a JSON object: {source}")
    expected_keys = {
        "version",
        "repo_root",
        "head",
        "run_start",
        "gate_id",
        "command_sha256",
        "declarations",
        "index_entries",
        "input_fingerprint",
    }
    if set(manifest) != expected_keys:
        raise StateError(f"gate manifest has an unsupported schema: {source}")
    if manifest["version"] != FORMAT_VERSION:
        raise StateError(f"gate manifest uses an unsupported format: {source}")

    require_string(manifest["repo_root"], "repo_root")
    require_string(manifest["head"], "head")
    normalize_gate_id(require_string(manifest["gate_id"], "gate_id"))
    command_hash = require_string(manifest["command_sha256"], "command_sha256")
    fingerprint = require_string(manifest["input_fingerprint"], "input_fingerprint")
    if not SHA256_PATTERN.fullmatch(command_hash):
        raise StateError(f"manifest command_sha256 is invalid: {source}")
    if not SHA256_PATTERN.fullmatch(fingerprint):
        raise StateError(f"manifest input_fingerprint is invalid: {source}")

    run_start = manifest["run_start"]
    if not isinstance(run_start, dict) or set(run_start) != {
        "path",
        "snapshot_sha256",
        "repo_root",
        "head",
        "index_entries_sha256",
    }:
        raise StateError(f"manifest run_start identity is invalid: {source}")
    for field in ("path", "repo_root", "head"):
        require_string(run_start[field], f"run_start.{field}")
    for field in ("snapshot_sha256", "index_entries_sha256"):
        value = require_string(run_start[field], f"run_start.{field}")
        if not SHA256_PATTERN.fullmatch(value):
            raise StateError(f"manifest run_start.{field} is invalid: {source}")

    declarations = manifest["declarations"]
    if (
        not isinstance(declarations, list)
        or not declarations
        or any(not isinstance(path, str) or not path for path in declarations)
        or declarations != sorted(set(declarations))
    ):
        raise StateError(f"manifest declarations are invalid: {source}")

    entries = manifest["index_entries"]
    if not isinstance(entries, list) or not entries:
        raise StateError(f"manifest index_entries are invalid: {source}")
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "mode", "object"}:
            raise StateError(f"manifest index entry is invalid: {source}")
        path = require_string(entry["path"], "index_entries.path")
        mode = require_string(entry["mode"], "index_entries.mode")
        object_id = require_string(entry["object"], "index_entries.object")
        if mode not in SUPPORTED_FILE_MODES or not OBJECT_PATTERN.fullmatch(object_id):
            raise StateError(f"manifest index entry is invalid: {source}")
        paths.append(path)
    if paths != sorted(set(paths)):
        raise StateError(f"manifest index entry paths are invalid: {source}")

    actual_fingerprint = sha256(canonical_bytes(manifest_without_fingerprint(manifest)))
    if fingerprint != actual_fingerprint:
        raise StateError(f"gate manifest fingerprint does not match its contents: {source}")
    return manifest


def load_manifest(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read gate manifest {path}: {error}") from error
    return validate_manifest(parsed, path), raw


def command_capture(args: argparse.Namespace) -> None:
    repo = repository_root()
    output = ensure_output_excluded_from_candidates(Path(args.output), repo)
    if output.exists():
        raise StateError(f"gate manifest output already exists: {output}")

    run_start_path = Path(args.run_start).resolve()
    run_start = load_snapshot(run_start_path)
    current_head = os.fsdecode(git(repo, "rev-parse", "HEAD").strip())
    if run_start.get("repo_root") != str(repo):
        raise StateError("run-start snapshot belongs to a different repository")
    if run_start.get("head") != current_head:
        raise StateError("HEAD differs from the retained run-start snapshot")
    try:
        run_start_raw = (run_start_path / "snapshot.json").read_bytes()
    except OSError as error:
        raise StateError(f"cannot read run-start snapshot identity: {error}") from error

    gate_id = normalize_gate_id(args.gate_id)
    declarations = normalize_input_paths(repo, args.input_path)
    entries = expand_index_entries(repo, declarations)
    assess_worktree(repo, declarations)
    command = read_command(Path(args.command_file))

    manifest: dict[str, Any] = {
        "version": FORMAT_VERSION,
        "repo_root": str(repo),
        "head": current_head,
        "run_start": {
            "path": str(run_start_path),
            "snapshot_sha256": sha256(run_start_raw),
            "repo_root": require_string(run_start.get("repo_root"), "run_start.repo_root"),
            "head": require_string(run_start.get("head"), "run_start.head"),
            "index_entries_sha256": require_string(
                run_start.get("index_entries_sha256"),
                "run_start.index_entries_sha256",
            ),
        },
        "gate_id": gate_id,
        "command_sha256": sha256(command),
        "declarations": declarations,
        "index_entries": entries,
    }
    manifest["input_fingerprint"] = sha256(canonical_bytes(manifest))
    raw_manifest = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    write_new_file(output, raw_manifest)
    print(
        json.dumps(
            {
                "input_fingerprint": manifest["input_fingerprint"],
                "manifest": str(output),
                "manifest_sha256": sha256(raw_manifest),
            },
            sort_keys=True,
        )
    )


def command_compare(args: argparse.Namespace) -> None:
    before_path = Path(args.before)
    after_path = Path(args.after)
    before_hash = args.before_sha256
    if not SHA256_PATTERN.fullmatch(before_hash):
        raise StateError("prior manifest SHA-256 must be 64 lowercase hexadecimal characters")

    before, before_raw = load_manifest(before_path)
    after, _ = load_manifest(after_path)
    if sha256(before_raw) != before_hash:
        raise StateError("prior manifest SHA-256 does not match the retained evidence")

    fields = (
        ("version", "format"),
        ("repo_root", "repository"),
        ("head", "HEAD"),
        ("run_start", "run-start identity"),
        ("gate_id", "gate id"),
        ("command_sha256", "command"),
        ("declarations", "input declarations"),
        ("index_entries", "indexed inputs"),
        ("input_fingerprint", "input fingerprint"),
    )
    changed = [label for field, label in fields if before[field] != after[field]]
    if changed:
        raise StateError("gate inputs are not reusable; changed: " + ", ".join(changed))
    print("reusable")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser(
        "capture", help="write one immutable gate-input manifest"
    )
    capture.add_argument("--output", required=True)
    capture.add_argument("--gate-id", required=True)
    capture.add_argument("--run-start", required=True)
    capture.add_argument("--command-file", required=True)
    capture.add_argument("--input-path", action="append", required=True)
    capture.set_defaults(func=command_capture)

    compare = subparsers.add_parser(
        "compare", help="verify that a prior passing gate has identical inputs"
    )
    compare.add_argument("--before", required=True)
    compare.add_argument("--before-sha256", required=True)
    compare.add_argument("--after", required=True)
    compare.set_defaults(func=command_compare)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
    except StateError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
