#!/usr/bin/env python3
"""Create, append to, and summarize deterministic execute-tickets metrics."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 3
EVENT_FIELDS = {
    "kind",
    "ticket",
    "phase",
    "reason",
    "result",
    "scope_paths",
    "state_owners",
    "duration_ms",
}
EVENT_KINDS = {
    "run_phase",
    "ticket_scope",
    "ticket_phase",
    "review_round",
    "repair",
    "gate",
    "ticket_result",
    "final_review",
    "final_repair_review",
    "final_assurance",
    "wait",
}
PHASES = {
    "preparation",
    "resume",
    "closeout",
    "scope_accepted",
    "implementation",
    "acceptance",
    "ticket_checks",
    "discovery",
    "closure",
    "regression_closure",
    "repair_micro",
    "repair_non_micro",
    "feature_final",
    "integration_review",
    "waiting",
}
RESULTS = {
    "pass",
    "fail",
    "blocked",
    "reused",
}
TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class StateError(ValueError):
    """Raised when a metrics state or requested mutation is invalid."""


def _git_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise StateError("run metrics must be initialized from a Git working tree")
    return Path(result.stdout.strip()).resolve()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _require_external_output(path: Path) -> None:
    """Allow an in-repository metrics log only when Git ignores it."""
    repository = _git_root()
    if path != repository and not _is_within(path, repository):
        return
    try:
        relative = path.relative_to(repository)
    except ValueError:
        raise StateError("metrics output must be outside the Git working tree") from None
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative.as_posix()],
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if ignored.returncode != 0:
        raise StateError(
            "metrics output inside the working tree must be ignored by Git: "
            + relative.as_posix()
        )


def _write_atomic(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(contents)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None:
            temporary_path = Path(temporary_name)
            if temporary_path.exists():
                temporary_path.unlink()


def _require_token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise StateError(
            f"{label} must be a lowercase token using letters, digits, underscores, or hyphens"
        )
    return value


def _require_enum(value: Any, label: str, allowed: set[str]) -> str:
    token = _require_token(value, label)
    if token not in allowed:
        raise StateError(f"unsupported {label}: {token}")
    return token


def _validate_string_list(value: Any, label: str, *, paths: bool = False) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise StateError(f"{label} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise StateError(f"{label} must not contain duplicates")
    if value != sorted(value):
        raise StateError(f"{label} must be sorted")
    if paths:
        for item in value:
            candidate = Path(item)
            if candidate.is_absolute() or ".." in candidate.parts:
                raise StateError(f"{label} must contain safe repository-relative paths")
    return value


def _validate_event(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise StateError("event must be a JSON object")
    if set(raw) != EVENT_FIELDS:
        missing = sorted(EVENT_FIELDS - set(raw))
        extra = sorted(set(raw) - EVENT_FIELDS)
        raise StateError(f"event fields differ from schema; missing={missing}, extra={extra}")

    kind = _require_enum(raw["kind"], "event kind", EVENT_KINDS)
    phase = _require_enum(raw["phase"], "event phase", PHASES)
    # Reasons are diagnostic labels; only kind-specific rules below constrain them.
    reason = _require_token(raw["reason"], "event reason")
    result = _require_enum(raw["result"], "event result", RESULTS)

    ticket = raw["ticket"]
    if ticket is not None and (
        not isinstance(ticket, str) or not ticket or not re.fullmatch(r"[A-Za-z0-9._-]+", ticket)
    ):
        raise StateError("event ticket must be null or a stable ticket identifier")

    scope_paths = _validate_string_list(raw["scope_paths"], "event scope_paths", paths=True)
    state_owners = _validate_string_list(raw["state_owners"], "event state_owners")
    if kind == "run_phase":
        expected_reason = {
            "preparation": "new_run", "resume": "resume", "closeout": "final_closeout",
        }.get(phase)
        if (
            ticket is not None or expected_reason is None or reason != expected_reason
            or result not in {"pass", "blocked"} or scope_paths or state_owners
        ):
            raise StateError("run_phase requires an unscoped preparation, resume or closeout event")
    if kind == "ticket_scope":
        if ticket is None:
            raise StateError("ticket_scope events require a ticket")
        if phase != "scope_accepted":
            raise StateError("ticket_scope events must use the scope_accepted phase")
        if result not in {"pass", "blocked"}:
            raise StateError("ticket_scope result must be pass or blocked")
    if kind == "ticket_phase":
        if ticket is None:
            raise StateError("ticket_phase events require a ticket")
        expected_reason = {
            "implementation": "implementation_work",
            "acceptance": "protected_staging",
        }.get(phase)
        if expected_reason is None or reason != expected_reason:
            raise StateError("ticket_phase must use an implementation or acceptance phase/reason")
        if result not in {"pass", "blocked"}:
            raise StateError("ticket_phase result must be pass or blocked")
    if kind == "review_round":
        expected_reason = {
            "discovery": "initial_ticket_review",
            "closure": "accepted_findings",
            "regression_closure": "repair_regression",
        }.get(phase)
        if ticket is None or expected_reason is None or reason != expected_reason:
            raise StateError("review_round phase/reason is invalid")
        if result not in {"pass", "fail"}:
            raise StateError("review_round result must be pass or fail")
    if kind == "repair":
        if ticket is None or phase not in {"repair_micro", "repair_non_micro"}:
            raise StateError("repair events require a ticket and repair phase")
        if reason not in {"review_finding", "test_failure"}:
            raise StateError("repair reason must be review_finding or test_failure")
        if result not in {"pass", "blocked"}:
            raise StateError("repair result must be pass or blocked")
    if kind == "gate":
        if phase not in {"ticket_checks", "feature_final"}:
            raise StateError("gate events must use a ticket_checks or feature_final phase")
        if result not in {"pass", "fail", "reused"}:
            raise StateError("gate result must be pass, fail, or reused")
    if kind == "ticket_result":
        if ticket is None or phase != "acceptance":
            raise StateError("ticket_result events require a ticket and the acceptance phase")
        if result not in {"pass", "blocked"}:
            raise StateError("ticket_result result must be pass or blocked")
    if kind == "final_review":
        if (
            ticket is not None
            or phase != "integration_review"
            or reason
            not in {"integration_risk", "accepted_findings", "repair_regression"}
        ):
            raise StateError("final_review phase/reason is invalid")
        if result not in {"pass", "fail", "blocked"}:
            raise StateError("final_review result must be pass, fail, or blocked")
    if kind == "final_repair_review":
        if (
            ticket is None
            or phase not in {"discovery", "closure"}
            or reason not in {"standard", "high_risk"}
            or result not in {"pass", "fail"}
        ):
            raise StateError("final_repair_review requires owner ticket, review phase and lane")
    if kind == "final_assurance":
        if ticket is not None or phase != "integration_review" or reason != "ticket_coverage" or result not in {"reused", "fail", "blocked"}:
            raise StateError("final_assurance requires ticket coverage and its actual outcome")
    if kind == "wait":
        if ticket is not None or phase != "waiting" or reason not in {"user_wait", "service_outage", "capacity_wait"} or result != "pass" or scope_paths or state_owners:
            raise StateError("wait requires an unscoped waiting interval and its known cause")

    duration_ms = raw["duration_ms"]
    if duration_ms is not None and (
        isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or duration_ms < 0
    ):
        raise StateError("event duration_ms must be a non-negative integer or null")

    return {
        "kind": kind,
        "ticket": ticket,
        "phase": phase,
        "reason": reason,
        "result": result,
        "scope_paths": scope_paths,
        "state_owners": state_owners,
        "duration_ms": duration_ms,
    }


def _is_workflow(event: dict[str, Any]) -> bool:
    return event["kind"] in {
        "run_phase", "ticket_scope", "ticket_phase", "review_round", "repair",
        "final_review", "final_repair_review", "final_assurance",
    } or (event["kind"] == "gate" and event["phase"] == "feature_final")


def _observations(records: list[dict[str, Any]]) -> tuple[list, list, dict, list]:
    events, fragments, interrupted = [], [], []
    opened: dict[str, dict[str, Any]] = {}
    seen = set()
    for raw in records:
        if not isinstance(raw, dict) or "record_type" not in raw:
            events.append(_validate_event(raw))
            continue
        kind = raw["record_type"]
        fields = {"record_type", "timer_id", "timestamp_ms"}
        fields |= {"event"} if kind == "timer_start" else {"result", "interruption"}
        if kind not in {"timer_start", "timer_end"} or set(raw) != fields:
            raise StateError("timer fields differ from schema")
        timer_id = raw["timer_id"]
        if not isinstance(timer_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", timer_id):
            raise StateError(
                "timer_id must start with an ASCII letter or digit and contain only "
                "ASCII letters, digits, underscores, or hyphens"
            )
        stamp = raw["timestamp_ms"]
        if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp < 0:
            raise StateError("timer timestamp_ms must be a non-negative integer")
        if kind == "timer_start":
            if timer_id in seen:
                raise StateError("timer_id already used")
            event = raw["event"]
            if not isinstance(event, dict) or set(event) != EVENT_FIELDS - {"result", "duration_ms"}:
                raise StateError("timer event must contain only event metadata")
            _validate_event({**event, "result": "reused" if event["kind"] == "final_assurance" else "pass", "duration_ms": None})
            # Nested check diagnostics are allowed; workflow and wait spans are exclusive.
            if (_is_workflow(event) or event["kind"] == "wait") and any(
                _is_workflow(start["event"]) or start["event"]["kind"] == "wait"
                for start in opened.values()
            ):
                raise StateError("overlapping workflow or wait timers")
            seen.add(timer_id)
            opened[timer_id] = raw
            continue
        if timer_id not in opened:
            raise StateError("timer is not open")
        start = opened.pop(timer_id)
        if stamp < start["timestamp_ms"]:
            raise StateError("timer clock moved backwards")
        reason, result = raw["interruption"], raw["result"]
        event = {**start["event"], "result": result,
                 "duration_ms": stamp - start["timestamp_ms"]}
        if reason is None:
            events.append({**_validate_event(event), "_timed": True})
        else:
            if not isinstance(reason, str) or reason not in {"user_wait", "capacity_wait", "service_outage", "unknown"} or result is not None:
                raise StateError("interrupted timer cannot claim an outcome")
            if reason in {"service_outage", "unknown"}:
                event["duration_ms"] = None
            fragments.append(event)
            interrupted.append({"timer_id": timer_id, "reason": reason,
                                "started_at_ms": start["timestamp_ms"], "observed_at_ms": stamp})
    fragments.extend({**start["event"], "result": None, "duration_ms": None}
                     for start in opened.values())
    return events, fragments, opened, interrupted


def _read_jsonl(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path.is_file():
        raise StateError(f"metrics file does not exist: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise StateError("metrics file is empty")
    try:
        header = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise StateError(f"invalid metrics header JSON: {error.msg}") from error
    expected_header = {"record_type", "schema_version", "feature", "run_start_id", "quality_proxy"}
    if not isinstance(header, dict) or set(header) != expected_header:
        raise StateError("metrics header fields differ from schema")
    if header["record_type"] != "run" or header["schema_version"] not in {2, SCHEMA_VERSION}:
        raise StateError("unsupported metrics schema")
    if header["quality_proxy"] is not False:
        raise StateError("metrics must not claim to be a quality proxy")
    _require_token(header["feature"], "feature")
    if not isinstance(header["run_start_id"], str) or not header["run_start_id"]:
        raise StateError("run_start_id must be a non-empty string")

    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines[1:], start=2):
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise StateError(f"invalid event JSON at line {line_number}: {error.msg}") from error
    _observations(events)
    return header, events


def _json_line(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def _require_canonical_output(path: Path, feature: str) -> None:
    if path.name != "run-metrics.jsonl" or path.parent.name != feature:
        raise StateError(
            "metrics output must use the exact feature metrics path: "
            f"<artifact-root>/{feature}/run-metrics.jsonl"
        )


def init_metrics(args: argparse.Namespace) -> None:
    output = Path(args.output).expanduser().resolve()
    _require_external_output(output)
    feature = _require_token(args.feature, "feature")
    _require_canonical_output(output, feature)
    if output.exists():
        raise StateError(f"metrics file already exists: {output}")
    if not args.run_start_id:
        raise StateError("run_start_id must be a non-empty string")
    header = {
        "record_type": "run",
        "schema_version": SCHEMA_VERSION,
        "feature": feature,
        "run_start_id": args.run_start_id,
        "quality_proxy": False,
    }
    _write_atomic(output, _json_line(header))
    print("initialized")


def _event_from_file(path: str) -> dict[str, Any]:
    try:
        event = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read event file: {error}") from error
    if isinstance(event, dict):
        for field in ("scope_paths", "state_owners"):
            values = event.get(field)
            if isinstance(values, list) and all(isinstance(value, str) for value in values):
                event[field] = sorted(values)
    return _validate_event(event)


def validate_event(args: argparse.Namespace) -> None:
    output = Path(args.output).expanduser().resolve()
    _require_external_output(output)
    header, _ = _read_jsonl(output)
    _require_canonical_output(output, header["feature"])
    _event_from_file(args.event_file)
    print("valid")


def record_event(args: argparse.Namespace) -> None:
    output = Path(args.output).expanduser().resolve()
    _require_external_output(output)
    header, events = _read_jsonl(output)
    _require_canonical_output(output, header["feature"])
    event = _event_from_file(args.event_file)
    contents = _json_line(header) + "".join(_json_line(existing) for existing in events)
    contents += _json_line(event)
    _write_atomic(output, contents)
    print("recorded")


def time_event(args: argparse.Namespace) -> None:
    stamp = time.time_ns() // 1_000_000
    output = Path(args.output).expanduser().resolve()
    _require_external_output(output)
    header, records = _read_jsonl(output)
    _require_canonical_output(output, header["feature"])
    record = {"record_type": "timer_start" if args.command == "start" else "timer_end",
              "timer_id": args.timer_id, "timestamp_ms": stamp}
    if args.command == "start":
        event = _event_from_file(args.event_file)
        if event["duration_ms"] is not None:
            raise StateError("start requires duration_ms: null; result is only a placeholder")
        record["event"] = {key: value for key, value in event.items()
                           if key not in {"result", "duration_ms"}}
    else:
        record.update(result=args.result if args.command == "end" else None,
                      interruption=args.reason if args.command == "interrupt" else None)
    records.append(record)
    _observations(records)
    header["schema_version"] = SCHEMA_VERSION
    _write_atomic(output, _json_line(header) + "".join(_json_line(item) for item in records))
    print("recorded")


def summarize(args: argparse.Namespace) -> None:
    input_path = Path(args.input).expanduser().resolve()
    header, records = _read_jsonl(input_path)
    _require_canonical_output(input_path, header["feature"])
    events, fragments, opened, interrupted = _observations(records)
    by_kind = Counter(event["kind"] for event in events)
    by_phase = Counter(event["phase"] for event in events)
    by_reason = Counter(event["reason"] for event in events)
    by_result = Counter(event["result"] for event in events)
    ticket_scope: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["kind"] == "ticket_scope":
            ticket_scope[event["ticket"]] = {
                "scope_path_count": len(event["scope_paths"]),
                "state_owners": event["state_owners"],
            }
    operation_duration_ms = workflow_duration_ms = 0
    unmeasured_event_count = unmeasured_workflow_event_count = 0
    phase_timings: dict[tuple[str, str, str], dict[str, Any]] = {}
    wait_duration_ms: Counter[str] = Counter()
    for event in events + fragments:
        duration = event["duration_ms"] or 0
        # Old non-instantaneous zeros cannot prove that the work took no time.
        unmeasured = event["duration_ms"] is None or (
            duration == 0 and event["kind"] != "ticket_result" and event["result"] != "reused"
            and event["result"] is not None and not event.get("_timed")
        )
        if event["kind"] == "wait":
            wait_duration_ms[event["reason"]] += duration
            unmeasured_event_count += unmeasured
            continue
        operation_duration_ms += duration
        unmeasured_event_count += unmeasured
        if _is_workflow(event):
            workflow_duration_ms += duration
            unmeasured_workflow_event_count += unmeasured
            key = (event["ticket"] or "", event["kind"], event["phase"])
            row = phase_timings.setdefault(key, {
                "ticket": event["ticket"], "kind": event["kind"], "phase": event["phase"],
                "event_count": 0, "duration_ms": 0, "unmeasured_count": 0,
            })
            row["event_count"] += event["result"] is not None
            row["duration_ms"] += duration
            row["unmeasured_count"] += unmeasured
    result = {
        "schema_version": header["schema_version"],
        "feature": header["feature"],
        "run_start_id": header["run_start_id"],
        "quality_proxy": False,
        "event_count": len(events),
        "total_duration_ms": operation_duration_ms,
        "operation_duration_ms": operation_duration_ms,
        "workflow_duration_ms": workflow_duration_ms,
        "wait_duration_ms": dict(sorted(wait_duration_ms.items())),
        "open_timer_ids": sorted(opened),
        "interrupted_spans": interrupted,
        "unmeasured_event_count": unmeasured_event_count,
        "unmeasured_workflow_event_count": unmeasured_workflow_event_count,
        "phase_timings": [phase_timings[key] for key in sorted(phase_timings)],
        "by_kind": dict(sorted(by_kind.items())),
        "by_phase": dict(sorted(by_phase.items())),
        "by_reason": dict(sorted(by_reason.items())),
        "by_result": dict(sorted(by_result.items())),
        "ticket_scope": dict(sorted(ticket_scope.items())),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)

    initialize = subcommands.add_parser("init", help="create a new metrics JSONL file")
    initialize.add_argument("--output", required=True)
    initialize.add_argument("--feature", required=True)
    initialize.add_argument("--run-start-id", required=True)
    initialize.set_defaults(action=init_metrics)

    record = subcommands.add_parser("record", help="append one validated event")
    record.add_argument("--output", required=True)
    record.add_argument("--event-file", required=True)
    record.set_defaults(action=record_event)

    validate = subcommands.add_parser("validate", help="validate metrics data only; never review permission")
    validate.add_argument("--output", required=True)
    validate.add_argument("--event-file", required=True)
    validate.set_defaults(action=validate_event)

    for name in ("start", "end", "interrupt"):
        timer = subcommands.add_parser(name, help="record a measured phase boundary")
        timer.add_argument("--output", required=True)
        timer.add_argument("--timer-id", required=True,
                           help="case-sensitive [A-Za-z0-9][A-Za-z0-9_-]*; reuse exact spelling")
        if name == "start":
            timer.add_argument("--event-file", required=True)
        elif name == "end":
            timer.add_argument("--result", required=True)
        else:
            timer.add_argument("--reason", required=True,
                               choices=("user_wait", "capacity_wait", "service_outage", "unknown"))
        timer.set_defaults(action=time_event)

    summary = subcommands.add_parser("summary", help="summarize metrics without scoring quality")
    summary.add_argument("--input", required=True)
    summary.set_defaults(action=summarize)
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        args.action(args)
    except (OSError, StateError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
