#!/usr/bin/env python3
"""Capture and verify exact repository files used by an authoring review."""

import argparse
import json
import sys
from pathlib import Path

from manifest_lib import file_record, is_within, record_authority, repository_root
from tracker_paths import resolve_directory


SCHEMA_VERSION = 1


def read_manifest(value: str) -> tuple[Path, dict[str, dict[str, object]]]:
    manifest_path = Path(value).resolve()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read manifest: {manifest_path}: {exc}") from exc

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported manifest schema")
    repository = payload.get("repository")
    if not isinstance(repository, str) or not repository:
        raise ValueError("manifest repository must be a non-empty path")
    root = repository_root(repository)
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("manifest must contain at least one reviewed file")

    indexed = {}
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("manifest file entries must be objects")
        relative = item.get("path")
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ValueError("manifest contains an invalid repository-relative path")
        if relative in indexed:
            raise ValueError(f"manifest contains duplicate input: {relative}")
        resolved = (root / relative).resolve()
        if not is_within(resolved, root):
            raise ValueError(f"manifest path escapes repository: {relative}")
        indexed[relative] = item

    return root, indexed


def ticket_path(root: Path, value: str, tickets_dir: str | None) -> str:
    requested = Path(value)
    parts = requested.parts
    directory = resolve_directory(root, tickets_dir, requested.parent.as_posix(), "--tickets-dir")
    default_layout = len(parts) == 4 and parts[0] == ".spec" and parts[2] == "issues"
    if (
        requested.is_absolute()
        or ".." in parts
        or (tickets_dir is None and not default_layout)
        or (root / requested).resolve().parent != directory
        or requested.suffix != ".md"
    ):
        raise ValueError(
            "closure ticket must match <tickets-dir>/<ticket>.md "
            "(default: .spec/<feature>/issues/<ticket>.md)"
        )
    return requested.as_posix()


def capture(args: argparse.Namespace) -> None:
    root = repository_root(args.repo)
    output = Path(args.output).resolve()
    if is_within(output, root):
        raise ValueError("manifest output must remain outside the repository")

    files = []
    seen = set()
    for raw_path in args.path:
        requested = Path(raw_path)
        if requested.is_absolute():
            raise ValueError(f"review input must be repository-relative: {raw_path}")

        resolved = (root / requested).resolve()
        if not is_within(resolved, root):
            raise ValueError(f"review input must be repository-relative: {raw_path}")
        if not resolved.is_file():
            raise ValueError(f"review input is not a regular file: {raw_path}")

        relative = resolved.relative_to(root).as_posix()
        if relative in seen:
            raise ValueError(f"duplicate review input: {relative}")
        seen.add(relative)
        files.append(file_record(root, relative))

    payload = {
        "schema_version": SCHEMA_VERSION,
        "repository": str(root),
        "files": sorted(files, key=lambda item: item["path"]),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("captured")


def verify(args: argparse.Namespace) -> None:
    root, files = read_manifest(args.manifest)
    errors = []
    for relative, item in files.items():
        resolved = (root / relative).resolve()
        if not resolved.is_file():
            errors.append(f"missing reviewed input: {relative}")
            continue

        actual = file_record(root, relative)
        if actual["authority_sha256"] != record_authority(item):
            errors.append(f"changed reviewed input: {relative}")

    if errors:
        raise ValueError("; ".join(errors))
    print("valid")


def continuous_manifests(
    before_value: str, after_value: str
) -> tuple[Path, dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    before_root, before_files = read_manifest(before_value)
    after_root, after_files = read_manifest(after_value)
    if before_root != after_root:
        raise ValueError("review repository changed")
    if set(before_files) != set(after_files):
        raise ValueError("review input set changed; exhaustive review required")
    return before_root, before_files, after_files


def changed_paths(
    before_files: dict[str, dict[str, object]], after_files: dict[str, dict[str, object]]
) -> list[str]:
    return sorted(
        relative
        for relative in before_files
        if record_authority(before_files[relative]) != record_authority(after_files[relative])
    )


def closure(args: argparse.Namespace) -> None:
    before_root, before_files, after_files = continuous_manifests(args.before, args.after)

    tickets = set()
    for raw_path in args.ticket:
        relative = ticket_path(before_root, raw_path, args.tickets_dir)
        if relative in tickets:
            raise ValueError(f"duplicate closure ticket: {relative}")
        if relative not in before_files:
            raise ValueError(f"closure ticket is not a reviewed input: {relative}")
        tickets.add(relative)

    unexpected = sorted(set(changed_paths(before_files, after_files)) - tickets)
    if unexpected:
        raise ValueError(
            "non-ticket review input changed; exhaustive review required: "
            + ", ".join(unexpected)
        )

    print("closure-valid")


def delta(args: argparse.Namespace) -> None:
    before_root, before_files, after_files = continuous_manifests(args.before, args.after)
    output = Path(args.output).resolve()
    if is_within(output, before_root):
        raise ValueError("delta output must remain outside the repository")

    changed = changed_paths(before_files, after_files)
    if not changed:
        raise ValueError(
            "no authority change; verify the existing receipt instead of opening a review"
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "repository": str(before_root),
        "changed": [
            {
                "path": relative,
                "before_authority_sha256": record_authority(before_files[relative]),
                "after_authority_sha256": record_authority(after_files[relative]),
            }
            for relative in changed
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("delta-valid")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    capture_parser = commands.add_parser("capture")
    capture_parser.add_argument("--repo", required=True)
    capture_parser.add_argument("--output", required=True)
    capture_parser.add_argument("--path", action="append", required=True)
    capture_parser.set_defaults(handler=capture)

    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--manifest", required=True)
    verify_parser.set_defaults(handler=verify)

    closure_parser = commands.add_parser("closure")
    closure_parser.add_argument("--before", required=True)
    closure_parser.add_argument("--after", required=True)
    closure_parser.add_argument("--ticket", action="append", required=True)
    closure_parser.add_argument("--tickets-dir", help="repository-relative feature ticket directory")
    closure_parser.set_defaults(handler=closure)

    delta_parser = commands.add_parser("delta")
    delta_parser.add_argument("--before", required=True)
    delta_parser.add_argument("--after", required=True)
    delta_parser.add_argument("--output", required=True)
    delta_parser.set_defaults(handler=delta)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
