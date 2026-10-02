#!/usr/bin/env python3
"""Read or complete one local implementation ticket.

Tickets are process documents. They are addressed by content hash rather than by
Git tracking, so this tool never requires the ticket to be tracked or staged.

`complete` is the single atomic completion transition: it freezes a baseline,
appends the bounded record, performs `ready-for-agent -> done`, proves that
nothing but the ticket changed, and retains the before/after content hashes as
durable completion evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import review_state
import repository_state
from tracker_paths import resolve_directory


READY = "ready-for-agent"
DONE = "done"
STATUS_PATTERN = re.compile(r"(?m)^\*\*Status:\*\*[ \t]*([^\r\n]+)[ \t]*$")
COMPLETION_PATTERN = re.compile(r"(?m)^## Completion record[ \t]*$")


class TicketStateError(RuntimeError):
    pass


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise TicketStateError("current directory is not inside a Git working tree")
    return Path(result.stdout.decode().strip()).resolve()


def resolve_ticket(repo: Path, value: str, tickets_dir: str | None) -> Path:
    candidate = Path(value)
    ticket = (candidate if candidate.is_absolute() else repo / candidate).resolve()
    try:
        relative = ticket.relative_to(repo)
    except ValueError as error:
        raise TicketStateError("ticket must be inside the repository") from error

    parts = relative.parts
    directory = resolve_directory(repo, tickets_dir, relative.parent.as_posix(), "--tickets-dir")
    default_layout = len(parts) == 4 and parts[0] == ".spec" and parts[2] == "issues"
    if (
        (tickets_dir is None and not default_layout)
        or ticket.parent != directory
        or ticket.suffix != ".md"
    ):
        raise TicketStateError(
            f"ticket must match {tickets_dir or '.spec/<feature>/issues'}/<ticket>.md"
        )
    if not ticket.is_file():
        raise TicketStateError(f"ticket does not exist: {relative}")
    return ticket


def read_ticket(ticket: Path) -> tuple[str, re.Match[str]]:
    text = ticket.read_text(encoding="utf-8")
    matches = list(STATUS_PATTERN.finditer(text))
    if len(matches) != 1:
        raise TicketStateError(
            f"ticket must contain exactly one '**Status:**' line; found {len(matches)}"
        )
    return text, matches[0]


def ticket_status(ticket: Path) -> str:
    _, match = read_ticket(ticket)
    return match.group(1).strip()


def read_completion_record(path: Path) -> str:
    try:
        record = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise TicketStateError(f"cannot read completion record: {error}") from error

    matches = list(COMPLETION_PATTERN.finditer(record))
    if len(matches) != 1 or matches[0].start() != 0:
        raise TicketStateError(
            "completion record must begin with exactly one '## Completion record' heading"
        )
    if not record[matches[0].end() :].strip():
        raise TicketStateError("completion record must contain acceptance evidence")
    return record.rstrip("\r\n") + "\n"


def append_record(text: str, record: str) -> str:
    if text.endswith("\n\n"):
        return text + record
    if text.endswith("\n"):
        return text + "\n" + record
    return text + "\n\n" + record


def atomic_write(ticket: Path, text: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{ticket.name}.", dir=ticket.parent
    )
    temporary = Path(temporary_name)
    try:
        os.chmod(temporary, stat.S_IMODE(ticket.stat().st_mode))
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as destination:
            destination.write(text)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, ticket)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def complete_ticket(ticket: Path, record_file: Path) -> str:
    record = read_completion_record(record_file)
    text, match = read_ticket(ticket)
    status = match.group(1).strip()
    if status == DONE:
        completion_matches = list(COMPLETION_PATTERN.finditer(text))
        if (
            len(completion_matches) == 1
            and text[completion_matches[0].start() :] == record
        ):
            return DONE
        raise TicketStateError(
            "done ticket contains a different or missing completion record"
        )
    if status != READY:
        raise TicketStateError(
            f"cannot complete ticket from status '{status}'; expected '{READY}'"
        )
    if COMPLETION_PATTERN.search(text):
        raise TicketStateError(
            "ready-for-agent ticket already contains a completion record"
        )

    updated = text[: match.start()] + f"**Status:** {DONE}" + text[match.end() :]
    atomic_write(ticket, append_record(updated, record))
    return DONE


def _records_without_ticket(
    records: list[dict[str, Any]], ticket_relative: str
) -> list[dict[str, Any]]:
    return [record for record in records if record["path"] != ticket_relative]


def validate_completion_delta(
    baseline: dict[str, Any], current: dict[str, Any], ticket_relative: str
) -> None:
    """Prove the completion transition changed nothing but the ticket."""
    if baseline["head"] != current["head"]:
        raise TicketStateError("HEAD changed during the completion transition")
    if baseline["index_entries_sha256"] != current["index_entries_sha256"]:
        raise TicketStateError("Git index changed during the completion transition")
    if baseline["staged_patch_sha256"] != current["staged_patch_sha256"]:
        raise TicketStateError("staged diff changed during the completion transition")
    if _records_without_ticket(
        baseline["tracked_unstaged"], ticket_relative
    ) != _records_without_ticket(current["tracked_unstaged"], ticket_relative):
        raise TicketStateError(
            "tracked files outside the ticket changed during the completion transition"
        )
    if _records_without_ticket(
        baseline["untracked"], ticket_relative
    ) != _records_without_ticket(current["untracked"], ticket_relative):
        raise TicketStateError(
            "untracked files outside the ticket changed during the completion transition"
        )


def complete_with_evidence(
    repo: Path, ticket: Path, record_file: Path, receipt: str, output_raw: str,
    snapshot_raw: str | None = None,
) -> str:
    """Atomically complete one ticket and retain content-hash transition evidence."""
    relative = ticket.relative_to(repo).as_posix()
    authority_paths = review_state.receipt_authority_paths(repo, receipt)
    if relative not in authority_paths:
        raise TicketStateError(
            f"ticket is not part of the receipt's authority set: {relative}"
        )

    record = read_completion_record(record_file)
    original_text, match = read_ticket(ticket)
    if match.group(1).strip() == DONE:
        # Idempotent replay: the retained evidence from the first run still holds.
        completion_matches = list(COMPLETION_PATTERN.finditer(original_text))
        if (
            len(completion_matches) == 1
            and original_text[completion_matches[0].start() :] == record
        ):
            if snapshot_raw:
                evidence = review_state.load_json_file(Path(output_raw) / "completion.json", "completion evidence")
                if evidence.get("accepted_snapshot_sha256") != review_state.snapshot_sha256(Path(snapshot_raw)):
                    raise TicketStateError("completion evidence belongs to a different accepted snapshot")
                handoff = Path(output_raw) / "handoff"
                review_state.load_snapshot(handoff)
                if evidence.get("handoff_snapshot_sha256") != review_state.snapshot_sha256(handoff):
                    raise TicketStateError("completion handoff was modified")
            return DONE
        raise TicketStateError(
            "done ticket contains a different or missing completion record"
        )

    output = Path(output_raw)
    try:
        review_state.ensure_output_excluded_from_candidates(output, repo)
    except review_state.StateError as error:
        raise TicketStateError(str(error)) from error
    if output.exists():
        raise TicketStateError(f"completion evidence already exists: {output}")

    accepted = None
    ticket_repository = None
    if snapshot_raw:
        accepted = review_state.load_snapshot(Path(snapshot_raw))
        if accepted.get("kind") != "repository-set":
            raise TicketStateError("--snapshot requires an accepted repository-set snapshot")
        accepted = repository_state.with_states(Path(snapshot_raw), accepted)
        repository_state.check_output(output, repository_state.identities(accepted))
        for name, item in accepted["repositories"].items():
            state = item["state"]
            if state.get("ticket_scope_paths") or state.get("ticket_tracked") or state.get("ticket_untracked"):
                raise TicketStateError("completion requires post-stage or validation-only repository snapshots")
            if Path(item["repo_root"]) == repo:
                ticket_repository = name
        if ticket_repository is None:
            raise TicketStateError("ticket repository is missing from the accepted repository set")
        expected_authority = review_state.snapshot_authority_paths(accepted["repositories"][ticket_repository]["state"])
        if not set(authority_paths).issubset(expected_authority):
            raise TicketStateError("accepted snapshot does not freeze the receipt authority")
        before_members = repository_state.collect_states(accepted)
        for name, (state, _) in before_members.items():
            changed = review_state.compare_snapshot(accepted["repositories"][name]["state"], state)
            if changed:
                raise TicketStateError(f"{name}: accepted completion input drifted: {', '.join(changed)}")
        before = before_members[ticket_repository][0]
    else:
        before, _ = review_state.collect_state(repo, None, authority_paths)
    complete_ticket(ticket, record_file)
    try:
        if accepted:
            after_members = repository_state.collect_states(accepted)
            after, after_files = after_members[ticket_repository]
            for name, (state, _) in after_members.items():
                if name != ticket_repository and review_state.compare_snapshot(before_members[name][0], state):
                    raise TicketStateError(f"{name}: repository changed during the completion transition")
        else:
            after, after_files = review_state.collect_state(repo, None, authority_paths)
        transitions = review_state.validate_authority(before, after, [relative])
        validate_completion_delta(before, after, relative)
    except Exception:
        # Keep "transitioned iff proved": restore the exact pre-transition bytes.
        atomic_write(ticket, original_text)
        raise

    output_owned = False
    try:
        output.mkdir(parents=True, exist_ok=False)
        output_owned = True
        handoff = output / "handoff"
        members = after_members if accepted else {None: (after, after_files)}
        for name, (state, files) in members.items():
            state["ticket_tracked_patch_sha256"] = review_state.sha256(b"")
            state["ticket_untracked_patch_sha256"] = review_state.sha256(b"")
            files["ticket-tracked.patch"] = b""
            files["ticket-untracked.patch"] = b""
            if accepted:
                state["scope_declared"] = True
            review_state.write_snapshot(
                Path(state["repo_root"]),
                repository_state.member_path(handoff, name) if accepted else handoff,
                state, files, [], [], None, [], [], [],
            )
        if accepted:
            repository_state.write_snapshot(handoff, repository_state.identities(accepted))
        evidence = {
            "ticket": relative,
            "status": DONE,
            "head": after["head"],
            "index_entries_sha256": after["index_entries_sha256"],
            "authority": after["authority"],
            "authority_transitions": transitions,
            "handoff_snapshot": str(handoff.resolve()),
            "handoff_snapshot_sha256": review_state.snapshot_sha256(handoff),
        }
        if accepted:
            evidence["accepted_snapshot_sha256"] = review_state.snapshot_sha256(Path(snapshot_raw))
            evidence["repositories"] = {
                name: {key: state[key] for key in ("repo_root", "head", "index_entries_sha256")}
                for name, (state, _) in after_members.items()
            }
        (output / "completion.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        atomic_write(ticket, original_text)
        if output_owned:
            shutil.rmtree(output, ignore_errors=True)
        raise
    return DONE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    show = subparsers.add_parser("show", help="print the ticket's exact status")
    show.add_argument("--ticket", required=True)
    show.add_argument("--tickets-dir", help="repository-relative feature ticket directory")

    complete = subparsers.add_parser(
        "complete",
        help="atomically append acceptance evidence, transition to done, and prove the delta",
    )
    complete.add_argument("--ticket", required=True)
    complete.add_argument("--record-file", required=True)
    complete.add_argument("--receipt", required=True)
    complete.add_argument("--output", required=True)
    complete.add_argument("--snapshot", help="accepted repository-set snapshot to bind to completion")
    complete.add_argument("--tickets-dir", help="repository-relative feature ticket directory")
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        repo = repository_root()
        ticket = resolve_ticket(repo, args.ticket, args.tickets_dir)
        if args.command == "show":
            print(ticket_status(ticket))
        else:
            print(
                complete_with_evidence(
                    repo,
                    ticket,
                    Path(args.record_file),
                    args.receipt,
                    args.output,
                    args.snapshot,
                )
            )
    except (OSError, UnicodeError, ValueError, TicketStateError, review_state.StateError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
