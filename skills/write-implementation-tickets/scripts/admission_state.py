#!/usr/bin/env python3
"""Create and verify content-addressed implementation-ticket admission records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from manifest_lib import authority_sha256, file_record, is_within, record_authority, sha256
from manifest_lib import repository_root as resolve_repository_root
from tracker_paths import resolve_directory


SCHEMA_VERSION = 1
ADMISSION_FILENAME = "implementation-ticket-admission.json"
DECISIONS = {"admitted-by-review", "admitted-by-user"}
REVIEW_STATUSES = {"PASS", "PASS_WITH_CORRECTIONS", "FAIL"}
OPENING_TYPES = {"exhaustive", "delta"}
MAX_DELTA_GENERATION = 2
DISPOSITIONS = {
    "accepted-risk",
    "closed-by-clarification",
    "rejected-as-review-drift",
}


class AdmissionError(RuntimeError):
    pass


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdmissionError(f"cannot read {label}: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise AdmissionError(f"{label} must be a JSON object")
    return payload


def repository_root(value: str) -> Path:
    try:
        return resolve_repository_root(value)
    except ValueError as error:
        raise AdmissionError(str(error)) from error


def normalize_feature(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise AdmissionError("feature must be one non-empty path segment")
    path = Path(value)
    if path.is_absolute() or len(path.parts) != 1 or value in {".", ".."}:
        raise AdmissionError("feature must be one non-empty path segment")
    return value


def authority_paths(
    root: Path, feature: str, spec_dir: str | None, tickets_dir: str | None
) -> list[str]:
    feature_root = resolve_directory(root, spec_dir, f".spec/{feature}", "--spec-dir")
    spec = feature_root / "spec.md"
    issues = resolve_directory(root, tickets_dir, f".spec/{feature}/issues", "--tickets-dir")
    if not spec.is_file():
        raise AdmissionError(f"missing feature spec: {spec}")
    if not issues.is_dir():
        raise AdmissionError(f"missing feature issues directory: {issues}")
    tickets = sorted(path for path in issues.glob("*.md") if path.is_file() and path != spec)
    if not tickets:
        raise AdmissionError("feature must contain at least one implementation ticket")
    return sorted(
        [spec.relative_to(root).as_posix()]
        + [path.relative_to(root).as_posix() for path in tickets]
    )


def file_records(root: Path, paths: list[str]) -> list[dict[str, object]]:
    return [file_record(root, relative) for relative in paths]


def validate_hash(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AdmissionError(f"{label} must be a lowercase SHA-256")
    return value


def validate_authority(
    root: Path, feature: str, raw_records: object, spec_dir: str | None, tickets_dir: str | None
) -> list[dict[str, object]]:
    if not isinstance(raw_records, list) or not raw_records:
        raise AdmissionError("admission authority must be a non-empty list")
    records: list[dict[str, object]] = []
    seen = set()
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise AdmissionError("authority entries must be objects")
        relative = raw.get("path")
        if not isinstance(relative, str) or relative in seen:
            raise AdmissionError("authority paths must be unique repository-relative files")
        seen.add(relative)
        validate_hash(raw.get("sha256"), f"authority hash for {relative}")
        if "authority_sha256" in raw:
            validate_hash(
                raw.get("authority_sha256"), f"authority body hash for {relative}"
            )
        if not isinstance(raw.get("size"), int) or raw["size"] < 0:
            raise AdmissionError(f"authority size for {relative} must be non-negative")
        records.append(raw)

    expected_paths = authority_paths(root, feature, spec_dir, tickets_dir)
    if sorted(seen) != expected_paths:
        raise AdmissionError("authority path set changed")
    for record in records:
        relative = str(record["path"])
        if authority_sha256(root / relative) != record_authority(record):
            raise AdmissionError(f"changed authority input: {relative}")
    return sorted(records, key=lambda item: str(item["path"]))


def validate_decision(
    decision: object,
    review_status: object,
    unresolved_findings: object,
    author_corrections: object,
    user_dispositions: object,
) -> tuple[str, str, list[str], list[str], list[dict[str, str]]]:
    if decision not in DECISIONS:
        raise AdmissionError("unsupported admission decision")
    if review_status not in REVIEW_STATUSES:
        raise AdmissionError("unsupported review status")
    if (
        not isinstance(unresolved_findings, list)
        or any(not isinstance(item, str) or not item for item in unresolved_findings)
        or len(set(unresolved_findings)) != len(unresolved_findings)
    ):
        raise AdmissionError("unresolved findings must be unique non-empty strings")
    if (
        not isinstance(author_corrections, list)
        or any(not isinstance(item, str) or not item for item in author_corrections)
        or len(set(author_corrections)) != len(author_corrections)
    ):
        raise AdmissionError("author corrections must be unique non-empty strings")
    if not isinstance(user_dispositions, list):
        raise AdmissionError("user dispositions must be a list")

    dispositions: list[dict[str, str]] = []
    for raw in user_dispositions:
        if not isinstance(raw, dict):
            raise AdmissionError("user disposition entries must be objects")
        finding = raw.get("finding")
        disposition = raw.get("disposition")
        reason = raw.get("reason")
        if not isinstance(finding, str) or not finding:
            raise AdmissionError("user disposition finding must be non-empty")
        if disposition not in DISPOSITIONS:
            raise AdmissionError(f"unsupported user disposition: {disposition}")
        if not isinstance(reason, str) or not reason.strip():
            raise AdmissionError("user disposition reason must be non-empty")
        dispositions.append(
            {"finding": finding, "disposition": str(disposition), "reason": reason}
        )

    if decision == "admitted-by-review":
        if unresolved_findings or dispositions:
            raise AdmissionError(
                "review admission requires no unresolved findings or user dispositions"
            )
        if review_status == "PASS" and author_corrections:
            raise AdmissionError("plain PASS cannot record author corrections")
        if review_status == "PASS_WITH_CORRECTIONS" and not author_corrections:
            raise AdmissionError("PASS_WITH_CORRECTIONS requires author corrections")
        if review_status == "FAIL":
            raise AdmissionError("review admission requires a passing review status")
    else:
        if review_status != "FAIL":
            raise AdmissionError("user admission requires a failed review")
        if author_corrections:
            raise AdmissionError("user admission cannot record author corrections")
        disposed = [item["finding"] for item in dispositions]
        if sorted(disposed) != sorted(unresolved_findings) or len(set(disposed)) != len(
            disposed
        ):
            raise AdmissionError("user admission must dispose every unresolved finding once")

    return (
        str(decision),
        str(review_status),
        list(unresolved_findings),
        list(author_corrections),
        dispositions,
    )


def read_lineage(payload: dict[str, Any]) -> tuple[str, str, int] | None:
    """Read a receipt's review lineage, or None for a receipt written before it existed."""
    review = payload.get("review")
    if not isinstance(review, dict) or "opening_type" not in review:
        return None
    opening = review.get("opening_type")
    base = review.get("base_exhaustive_report_sha256")
    generation = review.get("delta_generation")
    if (
        opening not in OPENING_TYPES
        or not isinstance(base, str)
        or not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation < 0
    ):
        raise AdmissionError("existing receipt has an unreadable review lineage")
    return str(opening), base, generation


def read_exhaustive_epoch(payload: dict[str, Any]) -> tuple[int, str]:
    review = payload.get("review")
    if not isinstance(review, dict):
        raise AdmissionError("existing receipt has no review record")
    epoch = review.get("exhaustive_epoch", 0)
    reason = review.get("epoch_reason", "legacy")
    if (
        not isinstance(epoch, int)
        or isinstance(epoch, bool)
        or epoch < 0
        or not isinstance(reason, str)
        or not reason
    ):
        raise AdmissionError("existing receipt has an unreadable review epoch")
    return epoch, reason


def resolve_lineage(
    opening_type: object,
    base_hash: object,
    receipt_path: Path,
    epoch_reason: object,
) -> tuple[str, str, int, int, str]:
    if opening_type not in OPENING_TYPES:
        raise AdmissionError("review opening type must be exhaustive or delta")
    base = validate_hash(base_hash, "base exhaustive report hash")
    if opening_type == "exhaustive":
        if not receipt_path.is_file():
            if epoch_reason not in {None, "initial"}:
                raise AdmissionError("a first exhaustive review must use the initial epoch")
            return "exhaustive", base, 0, 0, "initial"
        if epoch_reason != "user-authority-change":
            raise AdmissionError(
                "opening another exhaustive epoch requires explicit "
                "user-authority-change authorization"
            )
        prior_payload = read_json(receipt_path, "existing admission receipt")
        prior_epoch, _ = read_exhaustive_epoch(prior_payload)
        return "exhaustive", base, 0, prior_epoch + 1, str(epoch_reason)

    if not receipt_path.is_file():
        raise AdmissionError("delta admission requires an existing verified receipt")
    if epoch_reason is not None:
        raise AdmissionError("a delta review inherits its exhaustive epoch reason")
    prior_payload = read_json(receipt_path, "existing admission receipt")
    prior = read_lineage(prior_payload)
    if prior is None:
        raise AdmissionError(
            "existing receipt records no review lineage; delta requires a fresh exhaustive base"
        )
    _, prior_base, prior_generation = prior
    if prior_base != base:
        raise AdmissionError(
            "delta base does not match the existing receipt lineage; "
            "the current request must stop until a later explicit "
            "user-authority-change opens another exhaustive epoch"
        )
    if prior_generation >= MAX_DELTA_GENERATION:
        raise AdmissionError(
            f"consecutive delta budget exhausted after {MAX_DELTA_GENERATION} rounds; "
            "the current request must stop until a later explicit "
            "user-authority-change opens another exhaustive epoch"
        )
    prior_epoch, prior_reason = read_exhaustive_epoch(prior_payload)
    return "delta", base, prior_generation + 1, prior_epoch, prior_reason


def expected_receipt_path(root: Path, feature: str, spec_dir: str | None) -> Path:
    directory = resolve_directory(root, spec_dir, f".spec/{feature}", "--spec-dir")
    return (directory / ADMISSION_FILENAME).resolve()


def command_candidate(args: argparse.Namespace) -> None:
    root = repository_root(args.repo)
    feature = normalize_feature(args.feature)
    output = Path(args.output).resolve()
    if is_within(output, root):
        raise AdmissionError("candidate manifest output must remain outside the repository")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "repository": str(root),
        "feature": feature,
        "authority": file_records(root, authority_paths(root, feature, args.spec_dir, args.tickets_dir)),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("candidate")


def load_candidate(
    path: Path, spec_dir: str | None, tickets_dir: str | None
) -> tuple[Path, str, list[dict[str, object]]]:
    payload = read_json(path, "candidate manifest")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise AdmissionError("unsupported candidate manifest schema")
    root = repository_root(str(payload.get("repository", "")))
    feature = normalize_feature(payload.get("feature"))
    authority = validate_authority(root, feature, payload.get("authority"), spec_dir, tickets_dir)
    return root, feature, authority


def command_admit(args: argparse.Namespace) -> None:
    candidate_path = Path(args.candidate).resolve()
    decision_path = Path(args.decision_record).resolve()
    report_path = Path(args.review_report).resolve()
    root, feature, authority = load_candidate(candidate_path, args.spec_dir, args.tickets_dir)
    if not report_path.is_file():
        raise AdmissionError(f"review report is not a file: {report_path}")
    output = Path(args.output).resolve()
    if output != expected_receipt_path(root, feature, args.spec_dir):
        raise AdmissionError("receipt output must use the exact feature admission path")

    record = read_json(decision_path, "decision record")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise AdmissionError("unsupported decision record schema")
    candidate_hash = sha256(candidate_path)
    if record.get("candidate_manifest_sha256") != candidate_hash:
        raise AdmissionError("decision record does not approve this candidate manifest")
    decision, review_status, findings, corrections, dispositions = validate_decision(
        record.get("decision"),
        record.get("review_status"),
        record.get("unresolved_findings"),
        record.get("author_corrections", []),
        record.get("user_dispositions"),
    )
    opening_type, base_report, generation, exhaustive_epoch, epoch_reason = resolve_lineage(
        record.get("review_opening_type"),
        record.get("base_exhaustive_report_sha256"),
        output,
        record.get("review_epoch_reason"),
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "feature": feature,
        "decision": decision,
        "candidate_manifest_sha256": candidate_hash,
        "decision_record_sha256": sha256(decision_path),
        "authority": authority,
        "review": {
            "status": review_status,
            "report_sha256": sha256(report_path),
            "unresolved_findings": findings,
            "author_corrections": corrections,
            "opening_type": opening_type,
            "base_exhaustive_report_sha256": base_report,
            "delta_generation": generation,
            "exhaustive_epoch": exhaustive_epoch,
            "epoch_reason": epoch_reason,
        },
        "user_dispositions": dispositions,
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(decision)


def verify_receipt(
    root: Path, receipt_path: Path, spec_dir: str | None, tickets_dir: str | None
) -> str:
    payload = read_json(receipt_path, "admission receipt")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise AdmissionError("unsupported admission receipt schema")
    feature = normalize_feature(payload.get("feature"))
    if receipt_path.resolve() != expected_receipt_path(root, feature, spec_dir):
        raise AdmissionError("receipt must use the exact feature admission path")
    validate_hash(payload.get("candidate_manifest_sha256"), "candidate manifest hash")
    validate_hash(payload.get("decision_record_sha256"), "decision record hash")
    validate_authority(root, feature, payload.get("authority"), spec_dir, tickets_dir)
    review = payload.get("review")
    if not isinstance(review, dict):
        raise AdmissionError("admission review must be an object")
    validate_hash(review.get("report_sha256"), "review report hash")
    lineage = read_lineage(payload)
    if lineage is not None:
        _, base, generation = lineage
        validate_hash(base, "base exhaustive report hash")
        if generation > MAX_DELTA_GENERATION:
            raise AdmissionError("receipt records an over-budget delta generation")
        read_exhaustive_epoch(payload)
    decision, _, _, _, _ = validate_decision(
        payload.get("decision"),
        review.get("status"),
        review.get("unresolved_findings"),
        review.get("author_corrections", []),
        payload.get("user_dispositions"),
    )
    return decision


def command_verify(args: argparse.Namespace) -> None:
    root = repository_root(args.repo)
    print(verify_receipt(root, Path(args.receipt).resolve(), args.spec_dir, args.tickets_dir))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    candidate = commands.add_parser("candidate")
    candidate.add_argument("--repo", required=True)
    candidate.add_argument("--feature", required=True)
    candidate.add_argument("--output", required=True)
    candidate.set_defaults(handler=command_candidate)

    admit = commands.add_parser("admit")
    admit.add_argument("--candidate", required=True)
    admit.add_argument("--decision-record", required=True)
    admit.add_argument("--review-report", required=True)
    admit.add_argument("--output", required=True)
    admit.set_defaults(handler=command_admit)

    verify = commands.add_parser("verify")
    verify.add_argument("--repo", required=True)
    verify.add_argument("--receipt", required=True)
    verify.set_defaults(handler=command_verify)
    for command in (candidate, admit, verify):
        command.add_argument("--spec-dir", help="repository-relative feature spec directory")
        command.add_argument("--tickets-dir", help="repository-relative feature ticket directory")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except (AdmissionError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
