#!/usr/bin/env python3
"""Verify an implementation-ticket admission receipt against current authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from manifest_lib import authority_sha256, record_authority
from tracker_paths import resolve_directory


SCHEMA_VERSION = 1
ADMISSION_FILENAME = "implementation-ticket-admission.json"
OPENING_TYPES = {"exhaustive", "delta"}
MAX_DELTA_GENERATION = 2
DISPOSITIONS = {
    "accepted-risk",
    "closed-by-clarification",
    "rejected-as-review-drift",
}


class AdmissionError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AdmissionError(f"cannot read admission receipt: {path}: {error}") from error
    if not isinstance(payload, dict):
        raise AdmissionError("admission receipt must be a JSON object")
    return payload


def repository_root(value: str) -> Path:
    root = Path(value).resolve()
    if not root.is_dir():
        raise AdmissionError(f"repository does not exist: {root}")
    return root


def normalize_feature(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise AdmissionError("feature must be one non-empty path segment")
    path = Path(value)
    if path.is_absolute() or len(path.parts) != 1 or value in {".", ".."}:
        raise AdmissionError("feature must be one non-empty path segment")
    return value


def validate_hash(value: object, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AdmissionError(f"{label} must be a lowercase SHA-256")


def authority_paths(
    root: Path, feature: str, spec_dir: str | None, tickets_dir: str | None
) -> list[str]:
    feature_root = resolve_directory(root, spec_dir, f".spec/{feature}", "--spec-dir")
    spec = feature_root / "spec.md"
    issues = resolve_directory(root, tickets_dir, f".spec/{feature}/issues", "--tickets-dir")
    if not spec.is_file() or not issues.is_dir():
        raise AdmissionError("feature authority is incomplete")
    tickets = sorted(path for path in issues.glob("*.md") if path.is_file() and path != spec)
    if not tickets:
        raise AdmissionError("feature must contain at least one implementation ticket")
    return sorted(
        [spec.relative_to(root).as_posix()]
        + [path.relative_to(root).as_posix() for path in tickets]
    )


def validate_authority(
    root: Path, feature: str, authority: object, spec_dir: str | None, tickets_dir: str | None
) -> None:
    if not isinstance(authority, list) or not authority:
        raise AdmissionError("admission authority must be a non-empty list")
    records: dict[str, dict[str, Any]] = {}
    for raw in authority:
        if not isinstance(raw, dict):
            raise AdmissionError("authority entries must be objects")
        relative = raw.get("path")
        if not isinstance(relative, str) or relative in records:
            raise AdmissionError("authority paths must be unique repository-relative files")
        validate_hash(raw.get("sha256"), f"authority hash for {relative}")
        if "authority_sha256" in raw:
            validate_hash(raw.get("authority_sha256"), f"authority body hash for {relative}")
        if not isinstance(raw.get("size"), int) or raw["size"] < 0:
            raise AdmissionError(f"authority size for {relative} must be non-negative")
        records[relative] = raw
    if sorted(records) != authority_paths(root, feature, spec_dir, tickets_dir):
        raise AdmissionError("authority path set changed")
    for relative, record in records.items():
        if authority_sha256(root / relative) != record_authority(record):
            raise AdmissionError(f"changed authority input: {relative}")


def validate_decision(payload: dict[str, Any]) -> str:
    decision = payload.get("decision")
    review = payload.get("review")
    dispositions = payload.get("user_dispositions")
    if not isinstance(review, dict) or not isinstance(dispositions, list):
        raise AdmissionError("admission decision evidence is incomplete")
    status = review.get("status")
    findings = review.get("unresolved_findings")
    corrections = review.get("author_corrections", [])
    if (
        not isinstance(findings, list)
        or any(not isinstance(item, str) or not item for item in findings)
        or len(set(findings)) != len(findings)
    ):
        raise AdmissionError("unresolved findings must be unique non-empty strings")
    if (
        not isinstance(corrections, list)
        or any(not isinstance(item, str) or not item for item in corrections)
        or len(set(corrections)) != len(corrections)
    ):
        raise AdmissionError("author corrections must be unique non-empty strings")
    disposed = []
    for raw in dispositions:
        if not isinstance(raw, dict):
            raise AdmissionError("user disposition entries must be objects")
        if raw.get("disposition") not in DISPOSITIONS:
            raise AdmissionError("unsupported user disposition")
        if not isinstance(raw.get("reason"), str) or not raw["reason"].strip():
            raise AdmissionError("user disposition reason must be non-empty")
        finding = raw.get("finding")
        if not isinstance(finding, str) or not finding:
            raise AdmissionError("user disposition finding must be non-empty")
        disposed.append(finding)

    if decision == "admitted-by-review":
        if findings or dispositions:
            raise AdmissionError(
                "review admission requires no unresolved findings or user dispositions"
            )
        if status == "PASS" and corrections:
            raise AdmissionError("plain PASS cannot record author corrections")
        if status == "PASS_WITH_CORRECTIONS" and not corrections:
            raise AdmissionError("PASS_WITH_CORRECTIONS requires author corrections")
        if status not in {"PASS", "PASS_WITH_CORRECTIONS"}:
            raise AdmissionError("review admission requires a passing review status")
    elif decision == "admitted-by-user":
        if status != "FAIL":
            raise AdmissionError("user admission requires a failed review")
        if corrections:
            raise AdmissionError("user admission cannot record author corrections")
        if sorted(disposed) != sorted(findings) or len(set(disposed)) != len(disposed):
            raise AdmissionError("user admission must dispose every unresolved finding once")
    else:
        raise AdmissionError("unsupported admission decision")
    return str(decision)


def validate_lineage(review: dict[str, Any]) -> None:
    """Check a receipt's review lineage, accepting receipts written before it existed."""
    if "opening_type" not in review:
        return
    opening = review.get("opening_type")
    base = review.get("base_exhaustive_report_sha256")
    generation = review.get("delta_generation")
    if (
        opening not in OPENING_TYPES
        or not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation < 0
    ):
        raise AdmissionError("admission receipt has an unreadable review lineage")
    validate_hash(base, "base exhaustive report hash")
    if generation > MAX_DELTA_GENERATION:
        raise AdmissionError("receipt records an over-budget delta generation")


def command_verify(args: argparse.Namespace) -> None:
    root = repository_root(args.repo)
    receipt_path = Path(args.receipt).resolve()
    payload = read_json(receipt_path)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise AdmissionError("unsupported admission receipt schema")
    feature = normalize_feature(payload.get("feature"))
    spec_directory = resolve_directory(root, args.spec_dir, f".spec/{feature}", "--spec-dir")
    expected = (spec_directory / ADMISSION_FILENAME).resolve()
    if receipt_path != expected:
        raise AdmissionError("receipt must use the exact feature admission path")
    validate_hash(payload.get("candidate_manifest_sha256"), "candidate manifest hash")
    validate_hash(payload.get("decision_record_sha256"), "decision record hash")
    review = payload.get("review")
    if not isinstance(review, dict):
        raise AdmissionError("admission review must be an object")
    validate_hash(review.get("report_sha256"), "review report hash")
    validate_lineage(review)
    validate_authority(root, feature, payload.get("authority"), args.spec_dir, args.tickets_dir)
    print(validate_decision(payload))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--repo", required=True)
    verify.add_argument("--receipt", required=True)
    verify.add_argument("--spec-dir", help="repository-relative feature spec directory")
    verify.add_argument("--tickets-dir", help="repository-relative feature ticket directory")
    verify.set_defaults(handler=command_verify)
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
