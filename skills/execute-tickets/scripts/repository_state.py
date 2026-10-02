"""Coordinate the existing Git boundary across explicitly named repositories."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import review_state as review


def repository_identity(root: Path) -> dict[str, str]:
    root = root.resolve()
    actual = Path(os.fsdecode(review.git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    if actual != root:
        raise review.StateError(f"repository path must name its Git root: {root}")
    git_dir = Path(os.fsdecode(review.git(root, "rev-parse", "--absolute-git-dir")).strip()).resolve()
    index = Path(os.fsdecode(review.git(root, "rev-parse", "--git-path", "index")).strip())
    return {
        "repo_root": str(root),
        "git_dir": str(git_dir),
        "index_path": str((root / index).resolve()),
    }


def parse_repositories(values: list[str]) -> dict[str, dict[str, str]]:
    repositories = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            raise review.StateError("--repository requires NAME=/absolute/repository/root")
        if name in repositories or not Path(path).is_absolute():
            raise review.StateError("repository names must be unique and roots must be absolute")
        repositories[name] = repository_identity(Path(path))
    if len({item["index_path"] for item in repositories.values()}) != len(repositories):
        raise review.StateError("repository names must identify distinct Git indexes")
    return dict(sorted(repositories.items()))


def split_paths(values: list[str], repositories: dict[str, Any]) -> dict[str, list[str]]:
    paths: dict[str, list[str]] = {name: [] for name in repositories}
    for value in values:
        name, separator, path = value.partition(":")
        if not separator or name not in paths or not path:
            raise review.StateError(f"path must name a registered repository as NAME:path: {value}")
        root = Path(repositories[name]["repo_root"])
        normalized = review.normalize_scope_paths(root, [path])[0]
        if any(normalized == nested or normalized.startswith(nested + "/") for nested in nested_paths(name, repositories)):
            raise review.StateError(f"path belongs to a nested repository; use its name: {value}")
        paths[name].append(path)
    return paths


def member_path(snapshot: Path, name: str) -> Path:
    return snapshot / "repositories" / name


def identities(snapshot: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        name: {key: item[key] for key in ("repo_root", "git_dir", "index_path")}
        for name, item in snapshot["repositories"].items()
    }


def validate_repositories(repositories: dict[str, Any]) -> None:
    for name, identity in repositories.items():
        if repository_identity(Path(identity["repo_root"])) != identity:
            raise review.StateError(f"repository identity changed: {name}")
        for relative in nested_paths(name, repositories):
            entries = review.git(Path(identity["repo_root"]), "--literal-pathspecs", "ls-files", "--stage", "-z", "--", relative)
            records = [entry for entry in entries.split(b"\0") if entry]
            if records and not (
                len(records) == 1
                and records[0].split(b"\t")[0].split()[0] == b"160000"
                and os.fsdecode(records[0].split(b"\t", 1)[1]) == relative
            ):
                raise review.StateError(f"repositories have overlapping tracked file ownership: {name}:{relative}")


def nested_paths(name: str, repositories: dict[str, Any]) -> list[str]:
    root = Path(repositories[name]["repo_root"])
    return sorted(
        Path(item["repo_root"]).relative_to(root).as_posix()
        for other, item in repositories.items()
        if other != name and Path(item["repo_root"]).is_relative_to(root)
    )


def load_snapshot(path: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    repositories = snapshot.get("repositories")
    if snapshot.get("version") != 1 or not isinstance(repositories, dict) or not repositories:
        raise review.StateError("invalid repository-set snapshot")
    for name, item in repositories.items():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or not isinstance(item, dict):
            raise review.StateError("invalid repository snapshot entry")
        if any(not isinstance(item.get(key), str) for key in ("repo_root", "git_dir", "index_path")):
            raise review.StateError(f"repository snapshot lacks identity: {name}")
        member = member_path(path, name)
        if review.snapshot_sha256(member) != item.get("snapshot_sha256"):
            raise review.StateError(f"repository snapshot was modified: {name}")
        state = review.load_snapshot(member)
        if state.get("kind") == "repository-set" or state["repo_root"] != item["repo_root"]:
            raise review.StateError(f"repository snapshot belongs to a different root: {name}")
    return snapshot


def write_snapshot(output: Path, repositories: dict[str, Any]) -> dict[str, Any]:
    snapshot = {
        "kind": "repository-set",
        "version": 1,
        "repositories": {
            name: {**identity, "snapshot_sha256": review.snapshot_sha256(member_path(output, name))}
            for name, identity in repositories.items()
        },
    }
    (output / "snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return snapshot


def verify(path: Path, snapshot: dict[str, Any]) -> None:
    validate_repositories(identities(snapshot))
    for name in snapshot["repositories"]:
        try:
            review.command_verify(argparse.Namespace(snapshot=str(member_path(path, name))))
        except review.StateError as error:
            raise review.StateError(f"{name}: {error}") from error


def capture(args: argparse.Namespace, repositories: dict[str, Any]) -> str:
    output = Path(args.output)
    if output.exists():
        raise review.StateError(f"repository snapshot already exists: {output}")
    for item in repositories.values():
        review.ensure_output_excluded_from_candidates(output, Path(item["repo_root"]))
    scopes = split_paths(args.scope_path, repositories)
    authority = split_paths(args.authority_path, repositories)
    transitions = split_paths(args.authority_transition_path, repositories)
    receipts = split_paths([args.receipt] if args.receipt else [], repositories)
    prefixes = split_paths(args.allowed_staged_prefix, repositories)
    source = args.baseline or args.handoff
    resolutions = resolution_paths(args.drift_resolution, Path(source), repositories) if args.drift_resolution and source else {}
    if args.drift_resolution and not source:
        raise review.StateError("a drift resolution requires a baseline snapshot")
    with tempfile.TemporaryDirectory(prefix="execute-tickets-capture-") as temporary:
        temporary_output = Path(temporary) / "snapshot"
        try:
            for name, item in repositories.items():
                child = argparse.Namespace(**vars(args))
                child.output = str(member_path(temporary_output, name))
                child.scope_path = scopes[name]
                child.scope_declared = True
                child.nested_repository_paths = nested_paths(name, repositories)
                child.authority_path = authority[name]
                child.authority_transition_path = transitions[name]
                child.receipt = receipts[name][0] if receipts[name] else None
                child.allowed_staged_prefix = prefixes[name]
                child.drift_resolution = resolutions.get(name)
                child.drift_output = str(temporary_output.parent / "drift" / name) if args.drift_output else None
                for field in ("baseline", "handoff"):
                    value = getattr(args, field)
                    setattr(child, field, str(member_path(Path(value), name)) if value else None)
                review.command_capture(child, Path(item["repo_root"]))
        except review.StateError:
            if args.handoff and args.drift_output:
                report = make_drift_report(Path(args.handoff), review.load_snapshot(Path(args.handoff)), args.drift_resolution)
                if report["status"] != "clean":
                    check_output(Path(args.drift_output), repositories)
                    review.write_drift_report(Path(args.drift_output), report)
            raise
        write_snapshot(temporary_output, repositories)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(temporary_output, output)
    return str(output / "snapshot.json")


def check_output(output: Path, repositories: dict[str, Any]) -> None:
    for item in repositories.values():
        review.ensure_output_excluded_from_candidates(output, Path(item["repo_root"]))


def resolution_paths(raw: str | None, baseline: Path, repositories: dict[str, Any]) -> dict[str, str]:
    if raw is None:
        return {}
    path = Path(raw)
    resolution = review.load_json_file(path, "repository-set drift resolution")
    if resolution.get("kind") != "repository-set" or resolution.get("baseline_snapshot_sha256") != review.snapshot_sha256(baseline):
        raise review.StateError("drift resolution belongs to a different repository-set baseline")
    if set(resolution.get("repositories", {})) != set(repositories):
        raise review.StateError("drift resolution has a different repository set")
    paths = {}
    for name, digest in resolution["repositories"].items():
        member = member_path(path.parent, name) / "resolution.json"
        if review.sha256(member.read_bytes()) != digest:
            raise review.StateError(f"drift resolution was modified: {name}")
        review.load_resolution(member, member_path(baseline, name))
        paths[name] = str(member)
    return paths


def make_drift_report(baseline_path: Path, snapshot: dict[str, Any], resolution: str | None) -> dict[str, Any]:
    resolutions = resolution_paths(resolution, baseline_path, snapshot["repositories"])
    retained = with_states(baseline_path, snapshot)
    current = collect_states(retained)
    reports = {}
    for name, item in retained["repositories"].items():
        before = item["state"]
        resolved = Path(resolutions[name]) if name in resolutions else None
        if resolved:
            before = review.baseline_with_approved_drift(before, review.load_resolution(resolved, member_path(baseline_path, name))["approved_changes"])
        reports[name] = review.make_drift_report(
            Path(item["repo_root"]), member_path(baseline_path, name), before,
            current[name][0], resolved,
        )
    statuses = {report["status"] for report in reports.values()}
    return {
        "kind": "repository-set", "version": 1,
        "baseline_snapshot_sha256": review.snapshot_sha256(baseline_path),
        "status": "restart_required" if "restart_required" in statuses else "confirmation_required" if "confirmation_required" in statuses else "clean",
        "repositories": reports,
    }


def reconcile(args: argparse.Namespace, snapshot: dict[str, Any]) -> str:
    baseline_path, output = Path(args.baseline), Path(args.output)
    check_output(output, identities(snapshot))
    if output.exists():
        raise review.StateError(f"drift resolution already exists: {output}")
    report = review.load_json_file(Path(args.report), "repository-set drift report")
    if report != make_drift_report(baseline_path, snapshot, args.drift_resolution):
        raise review.StateError("drift report is stale; inspect and classify the current paths again")
    if report["status"] == "restart_required":
        raise review.StateError("HEAD, index, staged baseline, or authority drift requires restart")
    decisions = review.load_json_file(Path(args.decision), "drift decision").get("decisions")
    expected = {f"{name}:{change['path']}" for name, member in report["repositories"].items() for change in member["changes"]}
    if not isinstance(decisions, dict) or set(decisions) != expected or any(value not in {"restore", "preserve"} for value in decisions.values()):
        raise review.StateError("drift decision must classify every NAME:path exactly once as restore or preserve")
    resolutions = resolution_paths(args.drift_resolution, baseline_path, identities(snapshot))
    hashes = {}
    with tempfile.TemporaryDirectory(prefix="execute-tickets-reconcile-") as temporary:
        for name, member in report["repositories"].items():
            report_path, decision_path = Path(temporary) / f"{name}-report.json", Path(temporary) / f"{name}-decision.json"
            report_path.write_text(json.dumps(member), encoding="utf-8")
            decision_path.write_text(json.dumps({"decisions": {change["path"]: decisions[f"{name}:{change['path']}"] for change in member["changes"]}}), encoding="utf-8")
            child = argparse.Namespace(
                baseline=str(member_path(baseline_path, name)), output=str(member_path(output, name)),
                report=str(report_path), decision=str(decision_path), drift_resolution=resolutions.get(name),
            )
            result = Path(review.command_reconcile(child))
            hashes[name] = review.sha256(result.read_bytes())
    resolution = {"kind": "repository-set", "version": 1,
                  "baseline_snapshot_sha256": review.snapshot_sha256(baseline_path), "repositories": hashes}
    (output / "resolution.json").write_text(json.dumps(resolution, indent=2) + "\n", encoding="utf-8")
    return str(output / "resolution.json")


def collect_states(snapshot: dict[str, Any]) -> dict[str, tuple[dict[str, Any], dict[str, bytes]]]:
    """Collect every member once, using its frozen authority and path ownership."""
    validate_repositories(identities(snapshot))
    states = {}
    for name, item in snapshot["repositories"].items():
        state = item["state"]
        states[name] = review.collect_state(
            Path(item["repo_root"]), None, review.snapshot_authority_paths(state),
            state.get("nested_repository_paths"),
        )
    return states


def with_states(path: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    return {**snapshot, "repositories": {
        name: {**item, "state": review.load_snapshot(member_path(path, name))}
        for name, item in snapshot["repositories"].items()
    }}


def write_staging_evidence(path: Path, evidence: dict[str, Any]) -> None:
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".staging-")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
            json.dump(evidence, destination, indent=2)
            destination.write("\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def stage(args: argparse.Namespace, snapshot: dict[str, Any]) -> dict[str, Any]:
    baseline_path, snapshot_path = Path(args.baseline), Path(args.snapshot)
    baseline = review.load_snapshot(baseline_path)
    if baseline.get("kind") != "repository-set" or identities(baseline) != identities(snapshot):
        raise review.StateError("staging requires the same repository set as its baseline")
    if not args.output:
        raise review.StateError("repository-set staging requires --output for durable evidence")
    output = Path(args.output)
    repositories = identities(snapshot)
    for item in repositories.values():
        review.ensure_output_excluded_from_candidates(output, Path(item["repo_root"]))
    allowed = split_paths(args.allow_path or [], repositories)
    binding = {
        "baseline": str(baseline_path.resolve()),
        "baseline_sha256": review.snapshot_sha256(baseline_path),
        "snapshot": str(snapshot_path.resolve()),
        "snapshot_sha256": review.snapshot_sha256(snapshot_path),
    }
    reviewed = with_states(snapshot_path, snapshot)
    if not any(item["state"]["ticket_tracked"] or item["state"]["ticket_untracked"] for item in reviewed["repositories"].values()):
        raise review.StateError("reviewed ticket has no changes to stage")
    if args.allow_path:
        for name, item in reviewed["repositories"].items():
            paths = set(item["state"]["ticket_tracked"]) | {record["path"] for record in item["state"]["ticket_untracked"]}
            if paths != set(allowed[name]):
                raise review.StateError(f"{name}: staging paths differ from the allowed set")
    accepted_path = output / "accepted"
    evidence_path = output / "staging.json"
    results = {}
    resuming = output.exists()
    if resuming:
        evidence = review.load_json_file(evidence_path, "staging evidence")
        if any(evidence.get(key) != value for key, value in binding.items()):
            raise review.StateError("staging evidence belongs to a different reviewed boundary")
        accepted = review.load_snapshot(accepted_path)
        if review.snapshot_sha256(accepted_path) != evidence.get("accepted_snapshot_sha256"):
            raise review.StateError("accepted staging snapshot was modified")
        if identities(accepted) != repositories:
            raise review.StateError("accepted staging snapshot has a different repository set")
        accepted = with_states(accepted_path, accepted)
        # Compare actual states with immutable before/after evidence; no duplicate
        # progress flag is needed to recover an interrupted index replacement.
        current = collect_states(reviewed)
        for name, (state, _) in current.items():
            if review.compare_snapshot(reviewed["repositories"][name]["state"], state) and review.compare_snapshot(accepted["repositories"][name]["state"], state):
                raise review.StateError(f"{name}: state matches neither reviewed nor accepted staging input")
    else:
        verify(snapshot_path, snapshot)

    with tempfile.TemporaryDirectory(prefix="execute-tickets-indexes-") as temporary:
        after = {}
        for name, item in reviewed["repositories"].items():
            state = item["state"]
            changed = bool(state["ticket_tracked"] or state["ticket_untracked"])
            if resuming and not review.compare_snapshot(accepted["repositories"][name]["state"], current[name][0]):
                results[name] = evidence["repositories"][name]
                continue
            if changed:
                results[name] = review.prepare_stage(
                    member_path(baseline_path, name), member_path(snapshot_path, name),
                    Path(temporary) / name, allowed[name] if args.allow_path else None,
                )
            else:
                results[name] = {"staged_paths": [], "index_sha256": state["index_entries_sha256"]}
            if resuming:
                if results[name] != evidence["repositories"][name]:
                    raise review.StateError(f"{name}: prepared index differs from retained staging evidence")
            else:
                env = {"GIT_INDEX_FILE": str(Path(temporary) / name)} if changed else None
                after[name] = review.collect_state(
                    Path(item["repo_root"]), env, review.snapshot_authority_paths(state),
                    state.get("nested_repository_paths"),
                )
                collected = after[name][0]
                scope = set(state["ticket_scope_paths"])
                if (
                    collected["head"] != state["head"]
                    or collected["index_entries_sha256"] != results[name]["index_sha256"]
                    or collected["authority"] != state["authority"]
                    or collected["tracked_unstaged"] != [record for record in state["tracked_unstaged"] if record["path"] not in scope]
                    or collected["untracked"] != [record for record in state["untracked"] if record["path"] not in scope]
                ):
                    raise review.StateError(f"{name}: worktree drifted while preparing the accepted index")
        if not resuming:
            output.mkdir(parents=True)
            for name, (state, files) in after.items():
                state["scope_declared"] = True
                state["ticket_tracked_patch_sha256"] = review.sha256(b"")
                state["ticket_untracked_patch_sha256"] = review.sha256(b"")
                files.update({"ticket-tracked.patch": b"", "ticket-untracked.patch": b""})
                review.write_snapshot(
                    Path(repositories[name]["repo_root"]), member_path(accepted_path, name),
                    state, files, [], [], None, [], [], [],
                )
            accepted = write_snapshot(accepted_path, repositories)
            evidence = {
                **binding,
                "accepted_snapshot_sha256": review.snapshot_sha256(accepted_path),
                "repositories": results,
            }
            write_staging_evidence(evidence_path, evidence)
            accepted = with_states(accepted_path, accepted)
        for name, item in reviewed["repositories"].items():
            temporary_index = Path(temporary) / name
            if temporary_index.exists():
                review.replace_index(Path(item["repo_root"]), item["state"], temporary_index)
    verify(accepted_path, review.load_snapshot(accepted_path))
    return {"repositories": results, "staging_evidence": str(evidence_path.resolve()),
            "accepted_snapshot": str(accepted_path.resolve())}

def dispatch(args: argparse.Namespace) -> tuple[bool, Any]:
    declared = getattr(args, "repository", [])
    snapshot = None
    retained = getattr(args, "snapshot", None) or getattr(args, "baseline", None) or getattr(args, "handoff", None)
    if retained:
        header = review.load_json_file(Path(retained) / "snapshot.json", "snapshot")
        if header.get("kind") == "repository-set":
            snapshot = review.load_snapshot(Path(retained))
    if not declared and snapshot is None:
        return False, None
    repositories = parse_repositories(declared) if declared else identities(snapshot)
    if snapshot and repositories != identities(snapshot):
        raise review.StateError("repository set differs from the retained snapshot")
    if declared and retained and snapshot is None:
        raise review.StateError("a single-repository checkpoint cannot become a repository-set baseline")
    validate_repositories(repositories)
    if args.command == "capture":
        return True, capture(args, repositories)
    if args.command == "assess":
        scopes = split_paths(args.scope_path, repositories)
        return True, {"repositories": {
            name: review.command_assess(
                argparse.Namespace(scope_path=scopes[name], nested_repository_paths=nested_paths(name, repositories)),
                Path(item["repo_root"]),
            )
            for name, item in repositories.items()
        }}
    if args.command == "verify":
        verify(Path(args.snapshot), snapshot)
        return True, "review snapshot still matches every registered repository"
    if args.command == "stage":
        return True, stage(args, snapshot)
    if args.command == "drift":
        check_output(Path(args.output), repositories)
        report = make_drift_report(Path(args.baseline), snapshot, args.drift_resolution)
        review.write_drift_report(Path(args.output), report)
        return True, str(Path(args.output) / "report.json")
    if args.command == "reconcile":
        return True, reconcile(args, snapshot)
    raise review.StateError(f"repository-set command is not supported: {args.command}")
