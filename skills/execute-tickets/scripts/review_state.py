#!/usr/bin/env python3
"""Freeze, verify, and stage one ticket's working-tree review boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class StateError(RuntimeError):
    pass


def git(
    repo: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> bytes:
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=process_env,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise StateError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise StateError("current directory is not inside a Git working tree")
    return Path(os.fsdecode(result.stdout.strip())).resolve()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> tuple[str, int, str, int]:
    info = path.lstat()
    mode = stat.S_IMODE(info.st_mode)
    if path.is_symlink():
        data = os.fsencode(os.readlink(path))
        return sha256(data), len(data), "symlink", mode
    if not path.is_file():
        raise StateError(f"untracked path is not a regular file or symlink: {path}")

    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size, "file", mode


def split_paths(raw: bytes) -> list[str]:
    return [os.fsdecode(item) for item in raw.split(b"\0") if item]


def repository_pathspecs(nested_paths: list[str] | None) -> list[str]:
    # Registered repositories own their contents; the parent still hashes its full index.
    return ["--", ".", *(f":(exclude,literal){path}" for path in nested_paths)] if nested_paths else []


def collect_untracked(
    repo: Path, env: dict[str, str] | None = None, nested_paths: list[str] | None = None
) -> list[dict[str, Any]]:
    paths = split_paths(
        git(
            repo,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            *repository_pathspecs(nested_paths),
            env=env,
        )
    )
    records: list[dict[str, Any]] = []
    for relative in sorted(paths):
        digest, size, kind, mode = file_sha256(repo / relative)
        records.append(
            {
                "path": relative,
                "sha256": digest,
                "size": size,
                "kind": kind,
                "mode": mode,
            }
        )
    return records


def diff(
    repo: Path, *extra: str, env: dict[str, str] | None = None,
    nested_paths: list[str] | None = None,
) -> bytes:
    return git(
        repo,
        "diff",
        "--binary",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--ignore-submodules=none",
        "--submodule=short",
        *extra,
        *repository_pathspecs(nested_paths),
        env=env,
    )


def diff_for_paths(
    repo: Path, paths: list[str], env: dict[str, str] | None = None
) -> bytes:
    if not paths:
        return b""
    return git(
        repo,
        "--literal-pathspecs",
        "diff",
        "--binary",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--",
        *paths,
        env=env,
    )


def normalize_repository_paths(
    repo: Path,
    raw_paths: list[str],
    *,
    singular: str,
    plural: str,
) -> list[str]:
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
                f"{singular} must be a repository-relative file: {raw_path!r}"
            )
        resolved = (repo / candidate).resolve(strict=False)
        try:
            resolved.relative_to(repo)
        except ValueError as error:
            raise StateError(f"{singular} escapes the repository: {raw_path!r}") from error
        normalized.append(candidate.as_posix())
    if len(set(normalized)) != len(normalized):
        raise StateError(f"{plural} must not contain duplicates")
    return sorted(normalized)


def normalize_scope_paths(repo: Path, raw_paths: list[str]) -> list[str]:
    return normalize_repository_paths(
        repo,
        raw_paths,
        singular="ticket scope path",
        plural="ticket scope paths",
    )


def normalize_authority_paths(repo: Path, raw_paths: list[str]) -> list[str]:
    return normalize_repository_paths(
        repo,
        raw_paths,
        singular="authority path",
        plural="authority paths",
    )


def receipt_authority_paths(repo: Path, raw_receipt: str) -> list[str]:
    """Derive the run's authority set from the admission receipt.

    The set is the receipt's recorded authority paths plus the receipt itself,
    so a capture can never freeze a set that disagrees with admission.
    """
    [receipt_path] = normalize_authority_paths(repo, [raw_receipt])
    try:
        payload = json.loads((repo / receipt_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(
            f"cannot read admission receipt: {receipt_path}: {error}"
        ) from error
    authority = payload.get("authority") if isinstance(payload, dict) else None
    if not isinstance(authority, list) or not authority:
        raise StateError("admission receipt does not record its authority paths")
    paths: list[str] = []
    for record in authority:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise StateError("admission receipt authority entries are malformed")
        paths.append(record["path"])
    return normalize_authority_paths(repo, sorted(set(paths) | {receipt_path}))


def authority_records(repo: Path, paths: list[str]) -> list[dict[str, Any]]:
    """Hash the spec, admission receipt, and tickets that govern this run.

    Authority integrity is content-addressed, so process documents never need to
    be tracked by Git. Tracking them is allowed but is not evidence by itself.
    """
    records: list[dict[str, Any]] = []
    for relative in paths:
        path = repo / relative
        if path.is_symlink() or not path.is_file():
            raise StateError(f"authority path is not a regular file: {relative}")
        digest, size, _, _ = file_sha256(path)
        records.append({"path": relative, "sha256": digest, "size": size})
    return records


def validate_authority(
    baseline: dict[str, Any],
    current: dict[str, Any],
    transition_paths: list[str],
) -> list[dict[str, Any]]:
    """Require byte-identical authority except for approved transitions."""
    before = {record["path"]: record for record in baseline.get("authority", [])}
    after = {record["path"]: record for record in current.get("authority", [])}
    changed_members = set(before) ^ set(after)
    undeclared_members = sorted(changed_members - set(transition_paths))
    if undeclared_members:
        raise StateError(
            "authority path set changed outside an approved transition: "
            + ", ".join(undeclared_members)
        )

    unknown = sorted(set(transition_paths) - (set(before) | set(after)))
    if unknown:
        raise StateError(
            "authority transition path is not part of either authority set: "
            + ", ".join(unknown)
        )

    drifted = sorted(
        path
        for path in set(before) & set(after)
        if after[path] != before[path] and path not in set(transition_paths)
    )
    if drifted:
        raise StateError(
            "authority content changed outside an approved transition: "
            + ", ".join(drifted)
        )

    inert = sorted(
        path
        for path in transition_paths
        if path in before and path in after and after[path] == before[path]
    )
    if inert:
        raise StateError(
            "declared authority transition did not change the file: " + ", ".join(inert)
        )

    return [
        {
            "path": path,
            "before_sha256": before.get(path, {}).get("sha256"),
            "after_sha256": after.get(path, {}).get("sha256"),
        }
        for path in sorted(transition_paths)
    ]


def tracked_unstaged_records(
    repo: Path, paths: list[str], env: dict[str, str] | None = None
) -> list[dict[str, str]]:
    return [
        {"path": path, "patch_sha256": sha256(diff_for_paths(repo, [path], env))}
        for path in sorted(paths)
    ]


def collect_state(
    repo: Path,
    env: dict[str, str] | None = None,
    authority_paths: list[str] | None = None,
    nested_paths: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    staged = diff(repo, "--cached", env=env)
    unstaged = diff(repo, env=env, nested_paths=nested_paths)
    combined = diff(repo, "HEAD", env=env, nested_paths=nested_paths)
    index_entries = git(repo, "ls-files", "--stage", "-z", env=env)
    status_output = git(
        repo, "status", "--short", "--untracked-files=all", *repository_pathspecs(nested_paths), env=env
    )
    tracked_paths = split_paths(
        git(repo, "diff", "--name-only", "--no-renames", "-z", *repository_pathspecs(nested_paths), env=env)
    )
    untracked = collect_untracked(repo, env, nested_paths)
    state = {
        "version": 5,
        "repo_root": str(repo),
        "nested_repository_paths": nested_paths or [],
        "head": os.fsdecode(git(repo, "rev-parse", "HEAD").strip()),
        "index_entries_sha256": sha256(index_entries),
        "staged_patch_sha256": sha256(staged),
        "unstaged_patch_sha256": sha256(unstaged),
        "combined_patch_sha256": sha256(combined),
        "status_sha256": sha256(status_output),
        "tracked_unstaged_paths": sorted(tracked_paths),
        "tracked_unstaged": tracked_unstaged_records(repo, tracked_paths, env),
        "untracked": untracked,
        "authority": authority_records(repo, authority_paths or []),
    }
    files = {
        "staged.patch": staged,
        "unstaged.patch": unstaged,
        "combined.patch": combined,
        "status.txt": status_output,
    }
    return state, files


def validate_backup_records(root: Path, records: Any) -> None:
    if not isinstance(records, list):
        raise StateError("backup manifest must contain one list")
    for record in records:
        if not isinstance(record, dict):
            raise StateError("backup manifest contains an invalid record")
        blob = record.get("blob")
        if not record.get("exists") or not isinstance(blob, str):
            continue
        expected_blob = (Path("blobs") / str(record.get("sha256"))).as_posix()
        if blob != expected_blob:
            raise StateError(f"invalid backup blob path: {blob}")
        blob_path = root / blob
        try:
            digest, size, kind, _ = file_sha256(blob_path)
        except OSError as error:
            raise StateError(f"cannot read backup blob: {blob}: {error}") from error
        if (
            digest != record.get("sha256")
            or size != record.get("size")
            or kind != "file"
        ):
            raise StateError(f"backup blob was modified: {blob}")


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        snapshot = json.loads((path / "snapshot.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read snapshot {path}: {error}") from error

    if snapshot.get("kind") == "repository-set":
        from repository_state import load_snapshot as load_repository_snapshot
        return load_repository_snapshot(path, snapshot)

    artifact_hashes = {
        "staged.patch": "staged_patch_sha256",
        "unstaged.patch": "unstaged_patch_sha256",
        "combined.patch": "combined_patch_sha256",
        "ticket-tracked.patch": "ticket_tracked_patch_sha256",
        "ticket-untracked.patch": "ticket_untracked_patch_sha256",
        "status.txt": "status_sha256",
    }
    for artifact, field in artifact_hashes.items():
        try:
            actual = sha256((path / artifact).read_bytes())
        except OSError as error:
            raise StateError(f"cannot read snapshot artifact {path / artifact}: {error}") from error
        if actual != snapshot.get(field):
            raise StateError(f"snapshot artifact was modified: {artifact}")

    version = snapshot.get("version")
    if version not in {4, 5}:
        raise StateError("snapshot uses an unsupported format")
    try:
        untracked = json.loads((path / "untracked.json").read_text(encoding="utf-8"))
        ticket_untracked = json.loads(
            (path / "ticket-untracked.json").read_text(encoding="utf-8")
        )
        authority = json.loads((path / "authority.json").read_text(encoding="utf-8"))
        approved_drift = (
            json.loads((path / "approved-drift.json").read_text(encoding="utf-8"))
            if version == 5
            else []
        )
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read snapshot manifest in {path}: {error}") from error
    if untracked != snapshot.get("untracked"):
        raise StateError("snapshot artifact was modified: untracked.json")
    if ticket_untracked != snapshot.get("ticket_untracked"):
        raise StateError("snapshot artifact was modified: ticket-untracked.json")
    if authority != snapshot.get("authority"):
        raise StateError("snapshot artifact was modified: authority.json")
    if approved_drift != snapshot.get("approved_drift", []):
        raise StateError("snapshot artifact was modified: approved-drift.json")
    snapshot.setdefault("approved_drift", [])
    if version == 5:
        try:
            backups = json.loads(
                (path / "backups.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise StateError(f"cannot read snapshot backups in {path}: {error}") from error
        if backups != snapshot.get("backups"):
            raise StateError("snapshot artifact was modified: backups.json")
        validate_backup_records(path, backups)
    else:
        snapshot.setdefault("backups", [])
    return snapshot


def untracked_by_path(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["path"]: record for record in state["untracked"]}


def tracked_unstaged_by_path(state: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {record["path"]: record for record in state["tracked_unstaged"]}


def path_is_ignored(repo: Path, relative: Path) -> bool:
    """Report whether Git excludes this path from the working tree."""
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative.as_posix()],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode == 0


def ensure_output_excluded_from_candidates(output: Path, repo: Path) -> None:
    """Keep run artifacts out of every ticket candidate.

    Artifacts may live inside the working tree only when Git ignores them, so they
    can never be collected as untracked scope content or reach the index.
    """
    resolved = output.resolve()
    try:
        relative = resolved.relative_to(repo)
    except ValueError:
        return
    if not path_is_ignored(repo, relative):
        raise StateError(
            "snapshot output inside the working tree must be ignored by Git: "
            + relative.as_posix()
        )


def reject_ignored_scope_paths(repo: Path, scope_paths: list[str]) -> None:
    """Reject exact scope paths that Git keeps untracked and ignored.

    `collect_untracked` uses `--others --exclude-standard`, so such a path can
    never enter the reviewed untracked delta or the protected staged index, even
    when it does not exist yet and would become ignored on creation. Reject it
    before edits instead of discovering the gap at review or staging;
    force-adding the path or changing `.gitignore` is not a permitted repair.
    `git check-ignore` does not report tracked paths, so a tracked file matching
    an ignore pattern and a future path Git would not ignore keep their existing
    behavior.
    """
    rejected = sorted(path for path in scope_paths if path_is_ignored(repo, Path(path)))
    if rejected:
        raise StateError(
            "ticket scope contains Git-ignored paths the snapshot cannot capture: "
            + ", ".join(rejected)
        )


def snapshot_sha256(path: Path) -> str:
    try:
        return sha256((path / "snapshot.json").read_bytes())
    except OSError as error:
        raise StateError(f"cannot hash snapshot {path}: {error}") from error


def write_blob(output: Path, source: Path, record: dict[str, Any]) -> str:
    blob = Path("blobs") / record["sha256"]
    destination = output / blob
    if destination.exists():
        return blob.as_posix()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if record["kind"] == "symlink":
        destination.write_bytes(os.fsencode(os.readlink(source)))
    else:
        shutil.copyfile(source, destination)
    return blob.as_posix()


def capture_backups(
    repo: Path,
    output: Path,
    state: dict[str, Any],
    scope_paths: list[str],
) -> list[dict[str, Any]]:
    """Retain only protected content that Git cannot reconstruct later."""
    scope = set(scope_paths)
    authority = {record["path"] for record in state.get("authority", [])}
    records: list[dict[str, Any]] = []

    for tracked in state["tracked_unstaged"]:
        relative = tracked["path"]
        if relative in scope or relative in authority:
            continue
        source = repo / relative
        record: dict[str, Any] = {
            "path": relative,
            "category": "tracked",
            "exists": source.exists() or source.is_symlink(),
        }
        if record["exists"]:
            digest, size, kind, mode = file_sha256(source)
            record.update(
                {
                    "sha256": digest,
                    "size": size,
                    "kind": kind,
                    "mode": mode,
                }
            )
            record["blob"] = write_blob(output, source, record)
        records.append(record)

    for untracked in state["untracked"]:
        relative = untracked["path"]
        if relative in scope or relative in authority:
            continue
        record = {
            **untracked,
            "category": "untracked",
            "exists": True,
        }
        record["blob"] = write_blob(output, repo / relative, record)
        records.append(record)
    return sorted(records, key=lambda record: (record["path"], record["category"]))


def compare_snapshot(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    fields = (
        "repo_root",
        "head",
        "index_entries_sha256",
        "staged_patch_sha256",
        "unstaged_patch_sha256",
        "combined_patch_sha256",
        "status_sha256",
        "tracked_unstaged_paths",
        "tracked_unstaged",
        "untracked",
        "authority",
    )
    return [field for field in fields if expected.get(field) != actual.get(field)]


def validate_against_baseline(
    baseline: dict[str, Any], current: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    if baseline["repo_root"] != current["repo_root"]:
        raise StateError("baseline belongs to a different repository")
    if baseline["head"] != current["head"]:
        raise StateError("HEAD changed after the ticket started")
    if baseline["index_entries_sha256"] != current["index_entries_sha256"]:
        raise StateError("Git index changed after the ticket started")
    if baseline["staged_patch_sha256"] != current["staged_patch_sha256"]:
        raise StateError("staged diff changed after the ticket started")
    scope_paths = set(baseline.get("ticket_scope_paths", []))
    before_tracked = tracked_unstaged_by_path(baseline)
    after_tracked = tracked_unstaged_by_path(current)
    if before_tracked and not scope_paths and not baseline.get("scope_declared"):
        raise StateError(
            "pre-ticket baseline already had tracked unstaged changes; capture it with exact --scope-path values"
        )
    if scope_paths or baseline.get("scope_declared"):
        protected_tracked = {
            path: record
            for path, record in before_tracked.items()
            if path not in scope_paths
        }
        changed_tracked = [
            path
            for path, record in protected_tracked.items()
            if after_tracked.get(path) != record
        ]
        ticket_tracked = sorted(set(after_tracked) & scope_paths)
        unexpected_tracked = sorted(
            set(after_tracked) - scope_paths - set(protected_tracked)
        )
    else:
        changed_tracked = [
            path
            for path, record in before_tracked.items()
            if after_tracked.get(path) != record
        ]
        ticket_tracked = sorted(set(after_tracked) - set(before_tracked))
        unexpected_tracked = []
    if changed_tracked:
        raise StateError(
            "pre-existing tracked unstaged files outside ticket scope changed: "
            + ", ".join(changed_tracked)
        )
    if unexpected_tracked:
        raise StateError(
            "ticket changed tracked paths outside its declared scope: "
            + ", ".join(unexpected_tracked)
        )

    before = untracked_by_path(baseline)
    after = untracked_by_path(current)
    if scope_paths or baseline.get("scope_declared"):
        protected_untracked = {
            path: record for path, record in before.items() if path not in scope_paths
        }
        changed = [
            path
            for path, record in protected_untracked.items()
            if after.get(path) != record
        ]
        ticket_untracked = [
            record for path, record in after.items() if path in scope_paths
        ]
        unexpected_untracked = sorted(
            set(after) - scope_paths - set(protected_untracked)
        )
    else:
        changed = [path for path, record in before.items() if after.get(path) != record]
        ticket_untracked = [
            record for path, record in after.items() if path not in before
        ]
        unexpected_untracked = []
    if changed:
        raise StateError(
            "pre-existing untracked files outside ticket scope changed or disappeared: "
            + ", ".join(changed)
        )
    if unexpected_untracked:
        raise StateError(
            "ticket created paths outside its declared scope: "
            + ", ".join(unexpected_untracked)
        )
    return ticket_tracked, ticket_untracked


def drift_changes(
    repo: Path,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify immutable run drift separately from user-reconcilable paths."""
    strong: list[dict[str, Any]] = []
    for field, label in (
        ("repo_root", "repository"),
        ("head", "HEAD"),
        ("index_entries_sha256", "Git index"),
        ("staged_patch_sha256", "staged diff"),
        ("authority", "authority"),
    ):
        if baseline.get(field) != current.get(field):
            strong.append(
                {
                    "kind": field,
                    "label": label,
                    "before": baseline.get(field),
                    "after": current.get(field),
                }
            )

    scope = set(baseline.get("ticket_scope_paths", []))
    before_tracked = {
        path: record
        for path, record in tracked_unstaged_by_path(baseline).items()
        if path not in scope
    }
    after_tracked = {
        path: record
        for path, record in tracked_unstaged_by_path(current).items()
        if path not in scope
    }
    changes: list[dict[str, Any]] = []
    for path in sorted(set(before_tracked) | set(after_tracked)):
        before = before_tracked.get(path)
        after = after_tracked.get(path)
        if before == after:
            continue
        exists = (repo / path).exists() or (repo / path).is_symlink()
        changes.append(
            {
                "path": path,
                "category": "tracked",
                "change": "deleted" if not exists else "modified",
                "before": before,
                "after": after,
            }
        )

    before_untracked = {
        path: record
        for path, record in untracked_by_path(baseline).items()
        if path not in scope
    }
    after_untracked = {
        path: record
        for path, record in untracked_by_path(current).items()
        if path not in scope
    }
    for path in sorted(set(before_untracked) | set(after_untracked)):
        before = before_untracked.get(path)
        after = after_untracked.get(path)
        if before == after:
            continue
        change = "created" if before is None else "deleted" if after is None else "modified"
        changes.append(
            {
                "path": path,
                "category": "untracked",
                "change": change,
                "before": before,
                "after": after,
            }
        )
    return strong, sorted(changes, key=lambda change: change["path"])


def make_drift_report(
    repo: Path,
    baseline_path: Path,
    baseline: dict[str, Any],
    current: dict[str, Any],
    resolution_path: Path | None = None,
) -> dict[str, Any]:
    strong, changes = drift_changes(repo, baseline, current)
    status = (
        "restart_required"
        if strong
        else "confirmation_required"
        if changes
        else "clean"
    )
    return {
        "version": 1,
        "baseline_snapshot": str(baseline_path.resolve()),
        "baseline_snapshot_sha256": snapshot_sha256(baseline_path),
        "drift_resolution": str(resolution_path.resolve()) if resolution_path else None,
        "drift_resolution_sha256": (
            sha256(resolution_path.read_bytes()) if resolution_path else None
        ),
        "status": status,
        "scope_paths": baseline.get("ticket_scope_paths", []),
        "strong_drift": strong,
        "changes": changes,
    }


def write_drift_report(output: Path, report: dict[str, Any]) -> None:
    if output.exists():
        raise StateError(f"drift report already exists: {output}")
    output.mkdir(parents=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read {label}: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise StateError(f"{label} must contain one JSON object")
    return payload


def backup_by_path(snapshot: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (record["category"], record["path"]): record
        for record in snapshot.get("backups", [])
    }


def load_resolution(path: Path, baseline_path: Path) -> dict[str, Any]:
    resolution = load_json_file(path, "drift resolution")
    if resolution.get("version") != 1:
        raise StateError("drift resolution uses an unsupported format")
    if resolution.get("baseline_snapshot") != str(baseline_path.resolve()):
        raise StateError("drift resolution belongs to a different baseline")
    if resolution.get("baseline_snapshot_sha256") != snapshot_sha256(baseline_path):
        raise StateError("drift resolution baseline snapshot was modified")
    approved = resolution.get("approved_changes")
    if not isinstance(approved, list):
        raise StateError("drift resolution has no approved change list")
    validate_backup_records(path.parent, resolution.get("backups"))
    return resolution


def baseline_with_approved_drift(
    baseline: dict[str, Any], approved: list[dict[str, Any]]
) -> dict[str, Any]:
    effective = dict(baseline)
    tracked = tracked_unstaged_by_path(baseline)
    untracked = untracked_by_path(baseline)
    for change in approved:
        target = tracked if change["category"] == "tracked" else untracked
        after = change["after"]
        if after is None:
            target.pop(change["path"], None)
        else:
            target[change["path"]] = after
    effective["tracked_unstaged"] = [tracked[path] for path in sorted(tracked)]
    effective["tracked_unstaged_paths"] = sorted(tracked)
    effective["untracked"] = [untracked[path] for path in sorted(untracked)]
    return effective


def quarantine_path(repo: Path, output: Path, relative: str) -> str | None:
    source = repo / relative
    if not (source.exists() or source.is_symlink()):
        return None
    destination = output / "quarantine" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return destination.relative_to(output).as_posix()


def restore_backup(
    repo: Path,
    snapshot_path: Path,
    backup: dict[str, Any],
) -> None:
    target = repo / backup["path"]
    if not backup["exists"]:
        return
    blob = snapshot_path / backup["blob"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if backup["kind"] == "symlink":
        os.symlink(os.fsdecode(blob.read_bytes()), target)
    else:
        shutil.copyfile(blob, target)
        os.chmod(target, backup["mode"])


def restore_change(
    repo: Path,
    desired_state_path: Path,
    desired_state: dict[str, Any],
    output: Path,
    change: dict[str, Any],
) -> str | None:
    relative = change["path"]
    quarantined = quarantine_path(repo, output, relative)
    before = change["before"]
    if before is None:
        if change["category"] == "tracked":
            (repo / relative).parent.mkdir(parents=True, exist_ok=True)
            git(
                repo,
                "--literal-pathspecs",
                "checkout-index",
                "--force",
                "--",
                relative,
            )
        return quarantined

    backup = backup_by_path(desired_state).get((change["category"], relative))
    if backup is None:
        raise StateError(
            "baseline does not retain content required to restore: " + relative
        )
    restore_backup(repo, desired_state_path, backup)
    return quarantined


def command_drift(args: argparse.Namespace) -> str:
    baseline_path = Path(args.baseline)
    baseline = load_snapshot(baseline_path)
    repo = Path(baseline["repo_root"])
    output = Path(args.output)
    ensure_output_excluded_from_candidates(output, repo)
    current, _ = collect_state(repo, None, snapshot_authority_paths(baseline), baseline.get("nested_repository_paths"))
    resolution_path = Path(args.drift_resolution) if args.drift_resolution else None
    desired = baseline
    if resolution_path:
        desired = baseline_with_approved_drift(
            baseline,
            load_resolution(resolution_path, baseline_path)["approved_changes"],
        )
    report = make_drift_report(
        repo,
        baseline_path,
        desired,
        current,
        resolution_path,
    )
    write_drift_report(output, report)
    return str(output / "report.json")


def command_reconcile(args: argparse.Namespace) -> str:
    baseline_path = Path(args.baseline)
    baseline = load_snapshot(baseline_path)
    repo = Path(baseline["repo_root"])
    output = Path(args.output)
    ensure_output_excluded_from_candidates(output, repo)
    if output.exists():
        raise StateError(f"drift resolution already exists: {output}")

    report_path = Path(args.report)
    report = load_json_file(report_path, "drift report")
    resolution_path = Path(args.drift_resolution) if args.drift_resolution else None
    desired_state_path = baseline_path
    desired_state = baseline
    if resolution_path:
        prior_resolution = load_resolution(resolution_path, baseline_path)
        desired_state = baseline_with_approved_drift(
            baseline, prior_resolution["approved_changes"]
        )
        desired_state["backups"] = prior_resolution["backups"]
        desired_state_path = resolution_path.parent
    current, _ = collect_state(repo, None, snapshot_authority_paths(baseline), baseline.get("nested_repository_paths"))
    fresh = make_drift_report(
        repo,
        baseline_path,
        desired_state,
        current,
        resolution_path,
    )
    if report != fresh:
        raise StateError("drift report is stale; inspect and classify the current paths again")
    if fresh["strong_drift"]:
        raise StateError("HEAD, index, staged baseline, or authority drift requires restart")

    decision_path = Path(args.decision)
    decision = load_json_file(decision_path, "drift decision")
    decisions = decision.get("decisions")
    if not isinstance(decisions, dict):
        raise StateError("drift decision must contain a 'decisions' object")
    change_by_path = {change["path"]: change for change in fresh["changes"]}
    if set(decisions) != set(change_by_path):
        raise StateError("drift decision must classify every reported path exactly once")
    invalid = sorted(
        path
        for path, disposition in decisions.items()
        if disposition not in {"restore", "preserve"}
    )
    if invalid:
        raise StateError("drift decision has an invalid disposition: " + ", ".join(invalid))

    backups = backup_by_path(desired_state)
    missing = sorted(
        change["path"]
        for change in fresh["changes"]
        if decisions[change["path"]] == "restore"
        and change["before"] is not None
        and (change["category"], change["path"]) not in backups
    )
    if missing:
        raise StateError(
            "baseline does not retain content required to restore: " + ", ".join(missing)
        )

    output.mkdir(parents=True)
    restored: list[str] = []
    quarantine: dict[str, str] = {}
    for path in sorted(change_by_path):
        if decisions[path] != "restore":
            continue
        quarantined = restore_change(
            repo,
            desired_state_path,
            desired_state,
            output,
            change_by_path[path],
        )
        restored.append(path)
        if quarantined:
            quarantine[path] = quarantined

    after, _ = collect_state(repo, None, snapshot_authority_paths(baseline), baseline.get("nested_repository_paths"))
    remaining = make_drift_report(
        repo,
        baseline_path,
        desired_state,
        after,
        resolution_path,
    )
    preserved = [
        change for change in fresh["changes"] if decisions[change["path"]] == "preserve"
    ]
    if remaining["strong_drift"] or remaining["changes"] != preserved:
        raise StateError("reconciliation did not produce the classified protected worktree state")

    resolution_backups = capture_backups(
        repo,
        output,
        after,
        baseline.get("ticket_scope_paths", []),
    )
    (output / "backups.json").write_text(
        json.dumps(resolution_backups, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    approved = make_drift_report(repo, baseline_path, baseline, after)["changes"]
    resolution = {
        "version": 1,
        "baseline_snapshot": str(baseline_path.resolve()),
        "baseline_snapshot_sha256": snapshot_sha256(baseline_path),
        "report_sha256": sha256(report_path.read_bytes()),
        "decision_sha256": sha256(decision_path.read_bytes()),
        "restored_paths": restored,
        "approved_changes": approved,
        "quarantine": quarantine,
        "backups": resolution_backups,
    }
    (output / "resolution.json").write_text(
        json.dumps(resolution, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return str(output / "resolution.json")


def assess_staged_prefixes(repo: Path, raw_prefixes: list[str]) -> None:
    prefixes: list[str] = []
    for raw in raw_prefixes:
        candidate = Path(raw)
        if (
            not raw
            or candidate.is_absolute()
            or raw in {".", ".."}
            or ".." in candidate.parts
        ):
            raise StateError(
                f"allowed staged prefix must be a repository-relative path: {raw!r}"
            )
        prefixes.append(candidate.as_posix())
    staged = sorted(
        split_paths(
            git(repo, "diff", "--cached", "--name-only", "--no-renames", "-z")
        )
    )
    outside = sorted(
        path
        for path in staged
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)
    )
    if outside:
        raise StateError(
            "index contains staged paths outside the allowed prefix: "
            + ", ".join(outside)
        )


def build_untracked_patch(repo: Path, records: list[dict[str, Any]]) -> bytes:
    chunks: list[bytes] = []
    for record in records:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--no-index",
                "--binary",
                "--no-ext-diff",
                "--no-textconv",
                "--no-color",
                "--",
                "/dev/null",
                record["path"],
            ],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise StateError(
                f"cannot capture untracked file {record['path']}: {stderr}"
            )
        chunks.append(result.stdout)
    return b"".join(chunks)


def apply_cached_patch(
    repo: Path, env: dict[str, str], patch: bytes, label: str
) -> None:
    if not patch:
        return
    result = subprocess.run(
        ["git", "apply", "--cached", "--binary", "--whitespace=nowarn", "-"],
        cwd=repo,
        input=patch,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**os.environ, **env},
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise StateError(f"cannot apply reviewed {label} to temporary index: {stderr}")


def write_snapshot(
    repo: Path,
    output: Path,
    state: dict[str, Any],
    files: dict[str, bytes],
    ticket_tracked: list[str],
    ticket_untracked: list[dict[str, Any]],
    baseline_path: Path | None,
    scope_paths: list[str],
    authority_transitions: list[dict[str, Any]],
    approved_drift: list[dict[str, Any]],
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (output / name).write_bytes(content)
    backups = (
        capture_backups(repo, output, state, scope_paths)
        if baseline_path is None
        else []
    )
    (output / "untracked.json").write_text(
        json.dumps(state["untracked"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "ticket-untracked.json").write_text(
        json.dumps(ticket_untracked, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "authority.json").write_text(
        json.dumps(state["authority"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "approved-drift.json").write_text(
        json.dumps(approved_drift, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "backups.json").write_text(
        json.dumps(backups, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    snapshot = dict(state)
    snapshot["baseline_snapshot"] = str(baseline_path.resolve()) if baseline_path else None
    snapshot["ticket_scope_paths"] = scope_paths
    snapshot["ticket_tracked"] = ticket_tracked
    snapshot["ticket_untracked"] = ticket_untracked
    snapshot["authority_transitions"] = authority_transitions
    snapshot["approved_drift"] = approved_drift
    snapshot["backups"] = backups
    (output / "snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def command_capture(args: argparse.Namespace, repo: Path | None = None) -> str:
    repo = repo or repository_root()
    output = Path(args.output)
    ensure_output_excluded_from_candidates(output, repo)
    if args.baseline and args.handoff:
        raise StateError("capture accepts either a review baseline or a ticket handoff")
    authority_paths = normalize_authority_paths(repo, args.authority_path)
    if args.receipt:
        authority_paths = sorted(
            set(authority_paths) | set(receipt_authority_paths(repo, args.receipt))
        )
    transition_paths = normalize_authority_paths(repo, args.authority_transition_path)
    scope_paths = normalize_scope_paths(repo, args.scope_path)
    ticket_tracked: list[str] = []
    ticket_untracked: list[dict[str, Any]] = []
    authority_transitions: list[dict[str, Any]] = []
    approved_drift: list[dict[str, Any]] = []
    baseline_path: Path | None = None
    baseline: dict[str, Any] | None = None
    handoff_path: Path | None = None
    handoff: dict[str, Any] | None = None
    if args.baseline:
        baseline_path = Path(args.baseline)
        baseline = load_snapshot(baseline_path)
        if not authority_paths:
            authority_paths = [
                record["path"] for record in baseline.get("authority", [])
            ]
    elif args.handoff:
        handoff_path = Path(args.handoff)
        handoff = load_snapshot(handoff_path)
        if handoff["repo_root"] != str(repo):
            raise StateError("ticket handoff belongs to a different repository")
        handoff_authority = snapshot_authority_paths(handoff)
        if authority_paths and authority_paths != handoff_authority:
            raise StateError("capture authority set differs from the ticket handoff")
        authority_paths = handoff_authority
    elif transition_paths:
        raise StateError("an authority transition requires a baseline snapshot")
    nested_paths = (baseline or handoff or {}).get(
        "nested_repository_paths", getattr(args, "nested_repository_paths", [])
    )
    reject_ignored_scope_paths(repo, scope_paths)
    state, files = collect_state(repo, None, authority_paths, nested_paths)
    if getattr(args, "scope_declared", False) or (baseline and baseline.get("scope_declared")):
        state["scope_declared"] = True
    if args.allowed_staged_prefix:
        assess_staged_prefixes(repo, args.allowed_staged_prefix)
    if handoff is not None and handoff_path is not None:
        handoff_report = make_drift_report(repo, handoff_path, handoff, state)
        if args.drift_resolution:
            resolution = load_resolution(Path(args.drift_resolution), handoff_path)
            effective_handoff = baseline_with_approved_drift(
                handoff, resolution["approved_changes"]
            )
            resolved_report = make_drift_report(
                repo,
                handoff_path,
                effective_handoff,
                state,
                Path(args.drift_resolution),
            )
            if resolved_report["strong_drift"]:
                raise StateError("ticket handoff has immutable run drift")
            if resolved_report["changes"]:
                raise StateError(
                    "classified ticket-handoff state changed; create a fresh drift report"
                )
        elif handoff_report["status"] != "clean":
            if not args.drift_output:
                raise StateError("ticket handoff drift requires --drift-output")
            drift_output = Path(args.drift_output)
            ensure_output_excluded_from_candidates(drift_output, repo)
            write_drift_report(drift_output, handoff_report)
            raise StateError(
                "handoff requires a drift disposition before the next ticket starts"
            )
    elif args.drift_output:
        raise StateError("--drift-output requires a ticket handoff")

    if baseline is not None:
        if scope_paths and scope_paths != baseline.get("ticket_scope_paths", []):
            raise StateError("review capture scope differs from the pre-ticket scope")
        scope_paths = baseline.get("ticket_scope_paths", [])
        authority_transitions = validate_authority(baseline, state, transition_paths)
        if args.drift_resolution:
            resolution = load_resolution(Path(args.drift_resolution), baseline_path)
            approved_drift = resolution["approved_changes"]
            effective_baseline = baseline_with_approved_drift(
                baseline, resolution["approved_changes"]
            )
            current_report = make_drift_report(
                repo,
                baseline_path,
                effective_baseline,
                state,
                Path(args.drift_resolution),
            )
            if current_report["strong_drift"]:
                raise StateError("classified outside-scope state has immutable run drift")
            if current_report["changes"]:
                raise StateError(
                    "classified outside-scope state changed; create a fresh drift report"
                )
        else:
            effective_baseline = baseline
        ticket_tracked, ticket_untracked = validate_against_baseline(
            effective_baseline, state
        )
    elif args.drift_resolution and handoff is None:
        raise StateError("a drift resolution requires a baseline snapshot")
    ticket_tracked_patch = diff_for_paths(repo, ticket_tracked)
    ticket_untracked_patch = build_untracked_patch(repo, ticket_untracked)
    state["ticket_tracked_patch_sha256"] = sha256(ticket_tracked_patch)
    state["ticket_untracked_patch_sha256"] = sha256(ticket_untracked_patch)
    files["ticket-tracked.patch"] = ticket_tracked_patch
    files["ticket-untracked.patch"] = ticket_untracked_patch
    write_snapshot(
        repo,
        output,
        state,
        files,
        ticket_tracked,
        ticket_untracked,
        baseline_path,
        scope_paths,
        authority_transitions,
        approved_drift,
    )
    return str(output / "snapshot.json")


def command_assess(args: argparse.Namespace, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repository_root()
    scope_paths = normalize_scope_paths(repo, args.scope_path)
    reject_ignored_scope_paths(repo, scope_paths)
    state, _ = collect_state(repo, nested_paths=getattr(args, "nested_repository_paths", []))
    scope = set(scope_paths)
    return {
        "scope_paths": scope_paths,
        "pre_existing_tracked_unstaged_paths": state["tracked_unstaged_paths"],
        "pre_existing_untracked_paths": [
            record["path"] for record in state["untracked"]
        ],
        "scope_owned_tracked_unstaged_paths": sorted(
            set(state["tracked_unstaged_paths"]) & scope
        ),
        "scope_owned_untracked_paths": sorted(
            record["path"]
            for record in state["untracked"]
            if record["path"] in scope
        ),
    }


def snapshot_authority_paths(snapshot: dict[str, Any]) -> list[str]:
    return [record["path"] for record in snapshot.get("authority", [])]


def command_verify(args: argparse.Namespace) -> str:
    snapshot_path = Path(args.snapshot)
    expected = load_snapshot(snapshot_path)
    repo = Path(expected["repo_root"])
    actual, _ = collect_state(repo, None, snapshot_authority_paths(expected), expected.get("nested_repository_paths"))
    changed = compare_snapshot(expected, actual)
    if changed:
        raise StateError("review input drifted: " + ", ".join(changed))
    return "review snapshot still matches HEAD, index, working tree, untracked files, and authority"


def prepare_stage(
    baseline_path: Path,
    snapshot_path: Path,
    temporary_index: Path,
    allow_paths: list[str] | None = None,
) -> dict[str, Any]:
    baseline = load_snapshot(baseline_path)
    reviewed = load_snapshot(snapshot_path)
    repo = Path(reviewed["repo_root"])
    authority_paths = snapshot_authority_paths(reviewed)

    actual, _ = collect_state(repo, None, authority_paths, reviewed.get("nested_repository_paths"))
    changed = compare_snapshot(reviewed, actual)
    if changed:
        raise StateError("refusing to stage drifted review input: " + ", ".join(changed))
    effective_baseline = baseline_with_approved_drift(
        baseline, reviewed.get("approved_drift", [])
    )
    expected_ticket_tracked, expected_ticket_untracked = validate_against_baseline(
        effective_baseline, reviewed
    )
    if expected_ticket_tracked != reviewed.get("ticket_tracked", []):
        raise StateError("review snapshot ticket-tracked manifest is inconsistent")
    if expected_ticket_untracked != reviewed.get("ticket_untracked", []):
        raise StateError("review snapshot ticket-untracked manifest is inconsistent")

    paths = sorted(
        set(expected_ticket_tracked)
        | {record["path"] for record in expected_ticket_untracked}
    )
    if not paths:
        raise StateError("reviewed ticket has no changes to stage")
    staged_authority = sorted(set(paths) & set(authority_paths))
    if staged_authority:
        raise StateError(
            "refusing to stage process-document authority: " + ", ".join(staged_authority)
        )
    if allow_paths is not None:
        allowed_paths = set(allow_paths)
        unexpected_paths = sorted(set(paths) - allowed_paths)
        if unexpected_paths:
            raise StateError(
                "reviewed ticket contains paths outside the allowed set: "
                + ", ".join(unexpected_paths)
            )
        missing_paths = sorted(allowed_paths - set(paths))
        if missing_paths:
            raise StateError(
                "reviewed ticket is missing paths from the required set: "
                + ", ".join(missing_paths)
            )

    scope_paths = set(baseline.get("ticket_scope_paths", []))
    protected_tracked = [
        record
        for record in effective_baseline["tracked_unstaged"]
        if record["path"] not in scope_paths
    ]
    protected_untracked = {
        record["path"]: record
        for record in effective_baseline["untracked"]
        if record["path"] not in scope_paths
    }
    temporary_env = {"GIT_INDEX_FILE": str(temporary_index)}

    git(repo, "read-tree", reviewed["head"], env=temporary_env)
    apply_cached_patch(
        repo,
        temporary_env,
        (snapshot_path / "staged.patch").read_bytes(),
        "accepted staged patch",
    )
    apply_cached_patch(
        repo,
        temporary_env,
        (snapshot_path / "ticket-tracked.patch").read_bytes(),
        "ticket tracked patch",
    )
    apply_cached_patch(
        repo,
        temporary_env,
        (snapshot_path / "ticket-untracked.patch").read_bytes(),
        "untracked patch",
    )
    check_result = subprocess.run(
        ["git", "diff", "--cached", "--check"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**os.environ, **temporary_env},
    )
    if check_result.returncode != 0:
        raise StateError("git diff --cached --check failed in temporary index")
    remaining_tracked_paths = split_paths(
        git(
            repo,
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            *repository_pathspecs(reviewed.get("nested_repository_paths")),
            env=temporary_env,
        )
    )
    remaining_tracked = tracked_unstaged_records(
        repo, remaining_tracked_paths, temporary_env
    )
    if remaining_tracked != protected_tracked:
        raise StateError(
            "temporary index did not preserve tracked worktree paths outside ticket scope"
        )
    if (
        untracked_by_path({"untracked": collect_untracked(repo, temporary_env, reviewed.get("nested_repository_paths"))})
        != protected_untracked
    ):
        raise StateError(
            "temporary index did not preserve untracked paths outside ticket scope"
        )

    temporary_entries = git(repo, "ls-files", "--stage", "-z", env=temporary_env)
    if sha256(temporary_entries) == baseline["index_entries_sha256"]:
        raise StateError("temporary staging did not change the index")

    return {"staged_paths": paths, "index_sha256": sha256(temporary_entries)}


def replace_index(repo: Path, reviewed: dict[str, Any], temporary_index: Path) -> None:
    """Replace only this repository's index while holding its Git index lock."""
    authority_paths = snapshot_authority_paths(reviewed)
    index_path = Path(os.fsdecode(git(repo, "rev-parse", "--git-path", "index").strip()))
    if not index_path.is_absolute():
        index_path = repo / index_path
    if not index_path.exists():
        raise StateError(f"Git index does not exist: {index_path}")

    index_lock = Path(f"{index_path}.lock")
    lock_owned = False
    try:
        with index_lock.open("xb") as destination:
            lock_owned = True
            live_before_replace, _ = collect_state(
                repo, {"GIT_OPTIONAL_LOCKS": "0"}, authority_paths, reviewed.get("nested_repository_paths")
            )
            changed = compare_snapshot(reviewed, live_before_replace)
            if changed:
                raise StateError(
                    "refusing to replace the index after review input drifted: "
                    + ", ".join(changed)
                )
            with temporary_index.open("rb") as source:
                shutil.copyfileobj(source, destination)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(index_lock, index_path)
        lock_owned = False
    except FileExistsError as error:
        raise StateError(f"Git index is locked by another process: {index_lock}") from error
    finally:
        if lock_owned and index_lock.exists():
            index_lock.unlink()



def command_stage(args: argparse.Namespace) -> dict[str, Any]:
    reviewed = load_snapshot(Path(args.snapshot))
    with tempfile.TemporaryDirectory(prefix="execute-tickets-index-") as temp_dir:
        temporary_index = Path(temp_dir) / "index"
        result = prepare_stage(
            Path(args.baseline), Path(args.snapshot), temporary_index, args.allow_path
        )
        replace_index(Path(reviewed["repo_root"]), reviewed, temporary_index)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="write an immutable review snapshot")
    capture.add_argument("--output", required=True)
    capture.add_argument("--repository", action="append", default=[])
    capture.add_argument("--baseline")
    capture.add_argument("--scope-path", action="append", default=[])
    capture.add_argument("--allowed-staged-prefix", action="append", default=[])
    capture.add_argument("--authority-path", action="append", default=[])
    capture.add_argument("--receipt")
    capture.add_argument("--authority-transition-path", action="append", default=[])
    capture.add_argument("--drift-resolution")
    capture.add_argument("--handoff")
    capture.add_argument("--drift-output")
    capture.set_defaults(func=command_capture)

    assess = subparsers.add_parser(
        "assess", help="report existing worktree files owned by a ticket scope"
    )
    assess.add_argument("--repository", action="append", default=[])
    assess.add_argument("--scope-path", action="append", required=True)
    assess.set_defaults(func=command_assess)

    drift = subparsers.add_parser(
        "drift", help="report protected paths that require a recorded disposition"
    )
    drift.add_argument("--baseline", required=True)
    drift.add_argument("--output", required=True)
    drift.add_argument("--drift-resolution")
    drift.set_defaults(func=command_drift)

    reconcile = subparsers.add_parser(
        "reconcile", help="restore or preserve protected paths from recorded dispositions"
    )
    reconcile.add_argument("--baseline", required=True)
    reconcile.add_argument("--report", required=True)
    reconcile.add_argument("--decision", required=True)
    reconcile.add_argument("--output", required=True)
    reconcile.add_argument("--drift-resolution")
    reconcile.set_defaults(func=command_reconcile)

    verify = subparsers.add_parser("verify", help="verify that a review snapshot did not drift")
    verify.add_argument("--snapshot", required=True)
    verify.set_defaults(func=command_verify)

    stage = subparsers.add_parser("stage", help="stage exactly one verified ticket delta")
    stage.add_argument("--baseline", required=True)
    stage.add_argument("--snapshot", required=True)
    stage.add_argument("--allow-path", action="append")
    stage.add_argument("--output", help="durable staging evidence directory for a repository set")
    stage.set_defaults(func=command_stage)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        from repository_state import dispatch
        handled, result = dispatch(args)
        if not handled:
            result = args.func(args)
        print(json.dumps(result) if isinstance(result, dict) else result)
    except (StateError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # Without this alias repository_state's top-level `import review_state` loads a second
    # copy of this module, so its StateError is a different class and main() stops catching it.
    sys.modules["review_state"] = sys.modules[__name__]
    raise SystemExit(main())
