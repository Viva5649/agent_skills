#!/usr/bin/env python3
"""Validate and retain review budgets independently of optional cost metrics."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from review_state import StateError, ensure_output_excluded_from_candidates, repository_root


EVENT_FIELDS = {"kind", "ticket", "phase", "reason", "result"}


def _validate_event(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != EVENT_FIELDS:
        raise StateError("review event fields differ from schema")
    if any(not isinstance(raw[key], str) for key in ("kind", "phase", "reason", "result")):
        raise StateError("review event kind/phase/reason/result must be strings")
    ticket = raw["ticket"]
    if ticket is not None and (not isinstance(ticket, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", ticket)):
        raise StateError("event ticket must be null or a stable ticket identifier")
    kind, phase, reason, result = (raw[key] for key in ("kind", "phase", "reason", "result"))
    if kind == "review_round":
        reasons = {"discovery": "initial_ticket_review", "closure": "accepted_findings", "regression_closure": "repair_regression"}
        if ticket is None or reasons.get(phase) != reason or result not in {"pass", "fail"}:
            raise StateError("review_round phase/reason is invalid")
    elif kind == "repair":
        if ticket is None or phase not in {"repair_micro", "repair_non_micro"} or reason not in {"review_finding", "test_failure"} or result not in {"pass", "blocked"}:
            raise StateError("repair requires a ticket, repair phase, reason and result")
    elif kind == "ticket_result":
        if ticket is None or phase != "acceptance" or reason != "ticket_completed" or result not in {"pass", "blocked"}:
            raise StateError("ticket_result requires a completed ticket result")
    elif kind == "final_review":
        if ticket is not None or phase != "integration_review" or reason not in {"integration_risk", "accepted_findings", "repair_regression"} or result not in {"pass", "fail", "blocked"}:
            raise StateError("final_review phase/reason is invalid")
    elif kind == "final_repair_review":
        if ticket is None or phase not in {"discovery", "closure"} or reason not in {"standard", "high_risk"} or result not in {"pass", "fail"}:
            raise StateError("final_repair_review requires owner ticket, review phase and lane")
    else:
        raise StateError("unsupported review event kind")
    return raw


def _validate_transition(events: list[dict[str, Any]], event: dict[str, Any]) -> None:
    if event["kind"] == "final_repair_review":
        final_index = next(
            (i for i in range(len(events) - 1, -1, -1) if events[i]["kind"] == "final_review"),
            None,
        )
        if final_index is None or events[final_index]["result"] != "fail":
            raise StateError("targeted repair review requires a current failing final review")
        if events[final_index]["reason"] == "repair_regression":
            raise StateError("cumulative final review budget is exhausted")
        ticket = event["ticket"]
        if not any(
            item["kind"] == "ticket_result" and item["ticket"] == ticket
            and item["result"] == "pass"
            for item in events[:final_index]
        ):
            raise StateError("targeted repair must use the original completed owner ticket")
        # The final round and real owner determine the batch; callers cannot reset it by naming one.
        prior = [
            (i, item) for i, item in enumerate(events[final_index + 1 :], final_index + 1)
            if item["kind"] == "final_repair_review" and item["ticket"] == ticket
        ]
        if not prior:
            if event["phase"] != "discovery":
                raise StateError("targeted repair review must start with discovery")
            return
        previous_index, previous = prior[-1]
        if (
            len(prior) != 1 or previous["reason"] != "high_risk"
            or event["reason"] != "high_risk" or previous["result"] != "fail"
            or event["phase"] != "closure"
        ):
            raise StateError("targeted repair review budget exhausted or lane changed")
        repairs = [
            item for item in events[previous_index + 1 :]
            if item["kind"] == "repair" and item["ticket"] == ticket
        ]
        if not repairs or repairs[-1]["phase"] != "repair_non_micro" or repairs[-1]["result"] != "pass":
            raise StateError("targeted closure requires a subsequent completed non-micro repair")
        return

    if event["kind"] == "final_review":
        prior_reviews = [
            existing for existing in events if existing["kind"] == "final_review"
        ]
        if any(existing["reason"] == event["reason"] for existing in prior_reviews):
            raise StateError(f"duplicate final review phase: {event['reason']}")
        required_reason = {
            "accepted_findings": "integration_risk",
            "repair_regression": "accepted_findings",
        }.get(event["reason"])
        if required_reason is None:
            return
        matches = [
            review for review in prior_reviews if review["reason"] == required_reason
        ]
        if not matches or matches[-1]["result"] != "fail":
            raise StateError(
                f"{event['reason']} requires a prior failing {required_reason} final review"
            )
        prior_index = events.index(matches[-1])
        batch_results = {}
        for item in events[prior_index + 1 :]:
            if item["kind"] == "final_repair_review":
                batch_results[item["ticket"]] = item["result"]
            elif item["kind"] == "repair":
                if item["ticket"] in batch_results:
                    batch_results[item["ticket"]] = (
                        "pass" if item["phase"] == "repair_micro" and item["result"] == "pass"
                        else "unreviewed"
                    )
        if any(result != "pass" for result in batch_results.values()):
            raise StateError("final closure requires targeted PASS or verified micro inspection")
        if not any(
            item["kind"] == "repair"
            and item["phase"] == "repair_non_micro" and item["result"] == "pass"
            for item in events[prior_index + 1 :]
        ):
            raise StateError(
                f"{event['reason']} requires a completed non-micro repair"
            )
        return

    if event["kind"] != "review_round":
        return

    ticket = event["ticket"]
    prior_reviews = [
        existing
        for existing in events
        if existing["kind"] == "review_round" and existing["ticket"] == ticket
    ]
    if any(existing["phase"] == event["phase"] for existing in prior_reviews):
        raise StateError(f"duplicate review phase for ticket {ticket}: {event['phase']}")

    required_prior = {
        "closure": "discovery",
        "regression_closure": "closure",
    }.get(event["phase"])
    if required_prior is not None:
        matches = [review for review in prior_reviews if review["phase"] == required_prior]
        if not matches or matches[-1]["result"] != "fail":
            raise StateError(
                f"{event['phase']} requires a prior failing {required_prior} review"
            )
        prior_index = events.index(matches[-1])
        repairs = [
            existing
            for existing in events[prior_index + 1 :]
            if existing["kind"] == "repair" and existing["ticket"] == ticket
        ]
        if any(repair["phase"] == "repair_micro" for repair in repairs):
            raise StateError("repair_micro must finish without another reviewer round")
        if not repairs or repairs[-1]["result"] != "pass":
            raise StateError(f"{event['phase']} requires a completed non-micro repair")


def _events(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise StateError("review history must be an ordered event array")
    events: list[dict[str, Any]] = []
    for item in raw:
        event = _validate_event(item)
        _validate_transition(events, event)
        events.append(event)
    return events


def _require_path(path: Path, feature: str) -> None:
    if not isinstance(feature, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", feature):
        raise StateError("feature must be a lowercase token")
    if path.name != "review-budget.jsonl" or path.parent.name != feature:
        raise StateError("review output must use the exact feature review path: <artifact-root>/<feature>/review-budget.jsonl")
    ensure_output_excluded_from_candidates(path, repository_root())


def _read(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise StateError("review ledger is empty")
    header = json.loads(lines[0])
    if not isinstance(header, dict) or set(header) != {"record_type", "schema_version", "feature", "run_start_id"}:
        raise StateError("review header fields differ from schema")
    if header["record_type"] != "review_budget" or header["schema_version"] != 1:
        raise StateError("unsupported review ledger schema")
    if not isinstance(header["run_start_id"], str) or not header["run_start_id"]:
        raise StateError("review run_start_id must be non-empty")
    _require_path(path, header["feature"])
    return header, _events([json.loads(line) for line in lines[1:]])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="initialize from verified review evidence; never from metrics")
    initialize.add_argument("--output", required=True)
    initialize.add_argument("--feature", required=True)
    initialize.add_argument("--run-start-id", required=True)
    initialize.add_argument("--history-file", required=True, help="ordered five-field events from retained reports; [] only for a proven new feature")
    for name in ("validate", "record"):
        action = commands.add_parser(name)
        action.add_argument("--output", required=True)
        action.add_argument("--event-file", required=True)
    args = parser.parse_args()
    try:
        path = Path(args.output).expanduser().resolve()
        if args.command == "init":
            _require_path(path, args.feature)
            if path.exists():
                raise StateError(f"review ledger already exists: {path}")
            if not args.run_start_id:
                raise StateError("run-start-id must be non-empty")
            events = _events(json.loads(Path(args.history_file).read_text(encoding="utf-8")))
            header = {"record_type": "review_budget", "schema_version": 1, "feature": args.feature, "run_start_id": args.run_start_id}
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                stream.write("".join(json.dumps(item, sort_keys=True) + "\n" for item in [header, *events]))
                stream.flush()
                os.fsync(stream.fileno())
            print("initialized")
        else:
            _, events = _read(path)
            event = _validate_event(json.loads(Path(args.event_file).read_text(encoding="utf-8")))
            _validate_transition(events, event)
            if args.command == "record":
                with path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, sort_keys=True) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            print("recorded" if args.command == "record" else "valid")
        return 0
    except (OSError, ValueError, StateError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
