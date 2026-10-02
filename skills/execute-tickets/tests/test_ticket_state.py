#!/usr/bin/env python3
"""Integration tests for ticket_state.py using a temporary Git repository."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ticket_state.py"
REVIEW_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_state.py"


def run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


class TicketStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        run("git", "init", "--quiet", cwd=self.repo)
        (self.repo / "app.py").write_text("print('base')\n", encoding="utf-8")
        run("git", "add", "app.py", cwd=self.repo)
        run(
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "commit", "--quiet", "-m", "initial", cwd=self.repo,
        )
        feature = self.repo / ".spec/example"
        (feature / "issues").mkdir(parents=True)
        self.spec = feature / "spec.md"
        self.spec.write_text("# Example spec\n", encoding="utf-8")
        self.ticket = feature / "issues" / "01-example.md"
        self.receipt = feature / "implementation-ticket-admission.json"
        self.record = Path(self.temp.name) / "completion-record.md"
        self.output = Path(self.temp.name) / "completion"
        self.write_record()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_ticket(self, status: str, *, extra: str = "") -> None:
        self.ticket.write_text(
            f"# 01 — Example\n\n**Status:** {status}\n{extra}", encoding="utf-8"
        )
        self.write_receipt()

    def write_receipt(self) -> None:
        def entry(path: Path) -> dict[str, object]:
            data = path.read_bytes()
            return {
                "path": path.relative_to(self.repo).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }

        payload = {
            "schema_version": 1,
            "feature": "example",
            "authority": [entry(self.spec), entry(self.ticket)],
        }
        self.receipt.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    def write_record(self, text: str | None = None) -> None:
        self.record.write_text(
            text
            or """## Completion record

- Execution mode: `direct`
- Assurance lane: `standard`
- Accepted implementation: `abc123`
- Verification:
  - `python -m unittest` — exit `0`; passed
- Reviews:
  - Standards — pass, 0 unresolved findings
  - Spec — pass, 0 unresolved findings
- Deviations: None
""",
            encoding="utf-8",
        )

    def track_ticket(self) -> None:
        run("git", "add", ".spec/example/issues/01-example.md", cwd=self.repo)

    def tool(self, command: str, *directories: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        arguments = [
            sys.executable,
            str(SCRIPT),
            command,
            *directories,
            "--ticket",
            self.ticket.relative_to(self.repo).as_posix(),
        ]
        if command == "complete":
            arguments.extend(
                (
                    "--record-file",
                    str(self.record),
                    "--receipt",
                    self.receipt.relative_to(self.repo).as_posix(),
                    "--output",
                    str(self.output),
                )
            )
        return run(
            *arguments,
            cwd=self.repo,
            check=check,
        )

    def test_complete_transitions_ready_ticket_to_done(self) -> None:
        self.write_ticket("ready-for-agent")
        self.track_ticket()

        result = self.tool("complete")

        self.assertEqual("done", result.stdout.strip())
        completed = self.ticket.read_text(encoding="utf-8")
        self.assertIn("**Status:** done", completed)
        self.assertEqual(1, completed.count("## Completion record"))
        self.assertTrue(completed.endswith(self.record.read_text(encoding="utf-8")))
        self.assertEqual("done", self.tool("show").stdout.strip())

    def test_completion_binds_every_repository_and_rejects_child_drift(self) -> None:
        self.write_ticket("ready-for-agent")
        other = Path(self.temp.name) / "MLLM"
        run("git", "clone", "--quiet", str(self.repo), str(other), cwd=self.repo)
        pre, candidate, staging = (Path(self.temp.name) / name for name in ("pre", "candidate", "staging"))
        run(
            sys.executable, str(REVIEW_SCRIPT), "capture", "--output", str(pre),
            "--repository", f"QIFramework={self.repo}", "--repository", f"MLLM={other}",
            "--scope-path", "QIFramework:app.py", "--scope-path", "MLLM:app.py",
            "--receipt", "QIFramework:.spec/example/implementation-ticket-admission.json", cwd=self.repo,
        )
        for repo in (self.repo, other):
            (repo / "app.py").write_text("print('accepted')\n", encoding="utf-8")
        run(sys.executable, str(REVIEW_SCRIPT), "capture", "--output", str(candidate), "--baseline", str(pre), cwd=self.repo)
        run(sys.executable, str(REVIEW_SCRIPT), "stage", "--baseline", str(pre), "--snapshot", str(candidate), "--output", str(staging), cwd=self.repo)
        accepted = staging / "accepted"
        (other / "app.py").write_text("print('unreviewed')\n", encoding="utf-8")
        refused = self.tool("complete", "--snapshot", str(accepted), check=False)
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("ready-for-agent", self.ticket.read_text(encoding="utf-8"))
        (other / "app.py").write_text("print('accepted')\n", encoding="utf-8")
        completed = self.tool("complete", "--snapshot", str(accepted), check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)
        evidence = json.loads((self.output / "completion.json").read_text(encoding="utf-8"))
        self.assertEqual({"QIFramework", "MLLM"}, set(evidence["repositories"]))
        for name, repo in (("QIFramework", self.repo), ("MLLM", other)):
            entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=repo)
            self.assertEqual(hashlib.sha256(entries).hexdigest(), evidence["repositories"][name]["index_entries_sha256"])
        verified = run(sys.executable, str(REVIEW_SCRIPT), "verify", "--snapshot", str(self.output / "handoff"), cwd=self.repo, check=False)
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("done", self.tool("complete", "--snapshot", str(accepted)).stdout.strip())
        self.assertEqual("", run("git", "diff", "--cached", "--name-only", "--", ".spec", cwd=self.repo).stdout)

    def test_show_and_complete_use_tracker_ticket_directory(self) -> None:
        self.ticket = self.repo / "work/tickets/example/01-example.md"
        self.ticket.parent.mkdir(parents=True)
        self.spec = self.repo / "docs/specs/example/spec.md"
        self.spec.parent.mkdir(parents=True)
        self.spec.write_text("# Tracker spec\n", encoding="utf-8")
        self.receipt = self.spec.parent / "implementation-ticket-admission.json"
        tracker = self.repo / "docs/agents/issue-tracker.md"
        tracker.parent.mkdir(parents=True)
        tracker.write_text(
            "Spec: `docs/specs/<feature>/spec.md`\nTickets: `work/tickets/<feature>/`\n",
            encoding="utf-8",
        )
        self.write_ticket("ready-for-agent")
        directories = ("--tickets-dir", "work/tickets/example")
        index_before = run("git", "ls-files", "--stage", cwd=self.repo).stdout

        shown = self.tool("show", *directories, check=False)
        self.assertEqual(0, shown.returncode, shown.stderr)
        self.assertEqual("ready-for-agent\n", shown.stdout)
        missing = self.tool("complete", check=False)
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("--tickets-dir is required", missing.stderr)
        completed = self.tool("complete", *directories, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("done\n", completed.stdout)
        evidence = json.loads((self.output / "completion.json").read_text(encoding="utf-8"))
        self.assertEqual("work/tickets/example/01-example.md", evidence["ticket"])
        self.assertEqual(index_before, run("git", "ls-files", "--stage", cwd=self.repo).stdout)

    def test_complete_is_idempotent_for_the_same_record(self) -> None:
        self.write_ticket("ready-for-agent")
        self.track_ticket()

        first_result = self.tool("complete")
        first = self.ticket.read_bytes()
        second_result = self.tool("complete")

        self.assertEqual("done", first_result.stdout.strip())
        self.assertEqual("done", second_result.stdout.strip())
        self.assertEqual(first, self.ticket.read_bytes())

    def test_complete_rejects_done_ticket_without_the_supplied_record(self) -> None:
        self.write_ticket("done")
        self.track_ticket()
        first = self.ticket.read_bytes()

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("different or missing completion record", result.stderr)
        self.assertEqual(first, self.ticket.read_bytes())

    def test_complete_rejects_non_agent_ready_status(self) -> None:
        self.write_ticket("ready-for-human")
        self.track_ticket()

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("cannot complete ticket from status", result.stderr)
        self.assertIn("**Status:** ready-for-human", self.ticket.read_text(encoding="utf-8"))

    def test_multiple_status_lines_are_rejected(self) -> None:
        self.write_ticket("ready-for-agent", extra="\n**Status:** done\n")
        self.track_ticket()

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("exactly one", result.stderr)

    def test_missing_record_file_is_rejected_without_changing_ticket(self) -> None:
        self.write_ticket("ready-for-agent")
        self.track_ticket()
        self.record.unlink()
        first = self.ticket.read_bytes()

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("cannot read completion record", result.stderr)
        self.assertEqual(first, self.ticket.read_bytes())

    def test_malformed_record_heading_is_rejected_without_changing_ticket(self) -> None:
        self.write_ticket("ready-for-agent")
        self.track_ticket()
        self.write_record("## Result\n\n- Status: pass\n")
        first = self.ticket.read_bytes()

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must begin with exactly one '## Completion record'", result.stderr)
        self.assertEqual(first, self.ticket.read_bytes())

    def test_duplicate_record_heading_is_rejected_without_changing_ticket(self) -> None:
        self.write_ticket("ready-for-agent")
        self.track_ticket()
        self.write_record(
            "## Completion record\n\n- Deviations: None\n\n## Completion record\n"
        )
        first = self.ticket.read_bytes()

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must begin with exactly one '## Completion record'", result.stderr)
        self.assertEqual(first, self.ticket.read_bytes())

    def test_conflicting_existing_record_is_rejected_without_changing_ticket(self) -> None:
        self.write_ticket(
            "done",
            extra="\n## Completion record\n\n- Deviations: Different\n",
        )
        self.track_ticket()
        first = self.ticket.read_bytes()

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("different or missing completion record", result.stderr)
        self.assertEqual(first, self.ticket.read_bytes())

    def test_untracked_ticket_is_completed_as_a_process_document(self) -> None:
        self.write_ticket("ready-for-agent")

        result = self.tool("complete")

        self.assertEqual("done", result.stdout.strip())
        self.assertIn("## Completion record", self.ticket.read_text(encoding="utf-8"))
        self.assertEqual(
            "",
            run(
                "git", "ls-files", "--", ".spec/example/issues/01-example.md",
                cwd=self.repo,
            ).stdout,
        )

    def test_path_outside_project_ticket_layout_is_rejected(self) -> None:
        other = self.repo / "ticket.md"
        other.write_text("**Status:** ready-for-agent\n", encoding="utf-8")
        run("git", "add", "ticket.md", cwd=self.repo)

        result = run(
            sys.executable,
            str(SCRIPT),
            "complete",
            "--ticket",
            "ticket.md",
            "--record-file",
            str(self.record),
            "--receipt",
            ".spec/example/implementation-ticket-admission.json",
            "--output",
            str(self.output),
            cwd=self.repo,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must match .spec", result.stderr)

    def test_complete_writes_transition_evidence_and_leaves_the_index_alone(self) -> None:
        self.write_ticket("ready-for-agent")
        self.track_ticket()
        index_before = run("git", "ls-files", "--stage", cwd=self.repo).stdout

        result = self.tool("complete")

        self.assertEqual("done", result.stdout.strip())
        evidence = json.loads(
            (self.output / "completion.json").read_text(encoding="utf-8")
        )
        self.assertEqual(".spec/example/issues/01-example.md", evidence["ticket"])
        self.assertEqual("done", evidence["status"])
        [transition] = evidence["authority_transitions"]
        self.assertEqual(".spec/example/issues/01-example.md", transition["path"])
        self.assertNotEqual(transition["before_sha256"], transition["after_sha256"])
        self.assertEqual(
            hashlib.sha256(self.ticket.read_bytes()).hexdigest(),
            transition["after_sha256"],
        )
        authority_paths = [record["path"] for record in evidence["authority"]]
        self.assertIn(".spec/example/spec.md", authority_paths)
        self.assertIn(
            ".spec/example/implementation-ticket-admission.json", authority_paths
        )
        handoff = self.output / "handoff"
        self.assertTrue((handoff / "snapshot.json").is_file())
        self.assertEqual(
            hashlib.sha256((handoff / "snapshot.json").read_bytes()).hexdigest(),
            evidence["handoff_snapshot_sha256"],
        )
        verify = run(
            sys.executable,
            str(REVIEW_SCRIPT),
            "verify",
            "--snapshot",
            str(handoff),
            cwd=self.repo,
            check=False,
        )
        self.assertEqual(0, verify.returncode, verify.stderr)
        # The transition is a process-document change and never touches the index.
        self.assertEqual(
            index_before, run("git", "ls-files", "--stage", cwd=self.repo).stdout
        )

    def test_complete_rejects_a_ticket_missing_from_the_receipt_authority(self) -> None:
        self.write_ticket("ready-for-agent")
        payload = json.loads(self.receipt.read_text(encoding="utf-8"))
        payload["authority"] = [
            entry
            for entry in payload["authority"]
            if not entry["path"].endswith("01-example.md")
        ]
        self.receipt.write_text(json.dumps(payload) + "\n", encoding="utf-8")

        result = self.tool("complete", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("not part of the receipt's authority set", result.stderr)
        self.assertIn(
            "**Status:** ready-for-agent", self.ticket.read_text(encoding="utf-8")
        )
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
