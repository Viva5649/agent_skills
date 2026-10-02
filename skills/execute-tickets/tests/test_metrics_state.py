#!/usr/bin/env python3
"""Integration tests for append-only execute-tickets run metrics."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "metrics_state.py"


def run(
    *args: str, cwd: Path, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


class MetricsStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run("git", "init", "--quiet", cwd=self.repo)
        self.metrics = self.root / "runtime-v4" / "run-metrics.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def tool(
        self, command: str, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return run(
            sys.executable,
            str(SCRIPT),
            command,
            *args,
            cwd=self.repo,
            check=check,
        )

    def init(self, *, output: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.tool(
            "init",
            "--output",
            str(output or self.metrics),
            "--feature",
            "runtime-v4",
            "--run-start-id",
            "run-start-sha256:abc123",
            check=check,
        )

    def write_event(self, name: str, **overrides: object) -> Path:
        event: dict[str, object] = {
            "kind": "review_round",
            "ticket": "03",
            "phase": "discovery",
            "reason": "initial_ticket_review",
            "result": "pass",
            "scope_paths": [],
            "state_owners": ["RuntimeController"],
            "duration_ms": 1250,
        }
        event.update(overrides)
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(event), encoding="utf-8")
        return path

    def record(self, event: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.tool(
            "record",
            "--output",
            str(self.metrics),
            "--event-file",
            str(event),
            check=check,
        )

    def validate(self, event: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.tool(
            "validate",
            "--output",
            str(self.metrics),
            "--event-file",
            str(event),
            check=check,
        )

    def test_records_reasoned_events_and_summarizes_cost_without_quality_score(self) -> None:
        initialized = self.init()
        self.assertEqual("initialized\n", initialized.stdout)

        scope = self.write_event(
            "scope",
            kind="ticket_scope",
            phase="scope_accepted",
            reason="declared_contract",
            result="pass",
            scope_paths=["src/Runtime.kt", "tests/RuntimeTest.kt"],
            state_owners=["RuntimeController"],
            duration_ms=0,
        )
        implementation = self.write_event(
            "implementation",
            kind="ticket_phase",
            phase="implementation",
            reason="implementation_work",
            result="pass",
            duration_ms=5000,
        )
        review = self.write_event("review")
        ticket_gate = self.write_event(
            "ticket-gate",
            kind="gate",
            phase="ticket_checks",
            reason="implementation_change",
            result="pass",
            duration_ms=300,
        )
        gate = self.write_event(
            "gate",
            kind="gate",
            ticket=None,
            phase="feature_final",
            reason="invalidated_inputs",
            result="pass",
            state_owners=[],
            duration_ms=2500,
        )
        acceptance = self.write_event(
            "acceptance",
            kind="ticket_phase",
            phase="acceptance",
            reason="protected_staging",
            result="pass",
            duration_ms=1000,
        )
        ticket_result = self.write_event(
            "ticket-result",
            kind="ticket_result",
            phase="acceptance",
            reason="ticket_completed",
            result="pass",
            duration_ms=0,
        )
        for event in (
            scope,
            implementation,
            review,
            ticket_gate,
            gate,
            acceptance,
            ticket_result,
        ):
            with self.subTest(event=event.stem):
                self.assertEqual("recorded\n", self.record(event).stdout)

        summary = json.loads(
            self.tool("summary", "--input", str(self.metrics)).stdout
        )
        for field, expected in (
            ("event_count", 7),
            ("total_duration_ms", 10050),
            ("operation_duration_ms", 10050),
            ("workflow_duration_ms", 9750),
        ):
            with self.subTest(field=field):
                self.assertEqual(expected, summary[field])
        self.assertEqual(1, summary["by_reason"]["invalidated_inputs"])
        self.assertEqual(2, summary["ticket_scope"]["03"]["scope_path_count"])
        self.assertEqual(["RuntimeController"], summary["ticket_scope"]["03"]["state_owners"])
        self.assertFalse(summary["quality_proxy"])
        self.assertNotIn("quality_score", summary)

    def test_metrics_record_observations_without_deciding_review_permission(self) -> None:
        self.init()
        event = self.write_event("observed-review")
        self.record(event)
        # Statistics may observe a repeated event; they cannot authorize or veto it.
        self.assertEqual("valid\n", self.validate(event).stdout)
        self.assertEqual("recorded\n", self.record(event).stdout)
        summary = json.loads(self.tool("summary", "--input", str(self.metrics)).stdout)
        self.assertEqual(2, summary["event_count"])

    def test_core_timings_report_gaps_without_double_counting_checks(self) -> None:
        self.init()
        for phase, reason, duration in (
            ("preparation", "new_run", 120),
            ("resume", "resume", 80),
        ):
            self.record(self.write_event(
                phase, kind="run_phase", ticket=None, phase=phase,
                reason=reason, state_owners=[], duration_ms=duration,
            ))
        self.record(self.write_event(
            "implementation", kind="ticket_phase", phase="implementation",
            reason="implementation_work", duration_ms=4000,
        ))
        self.record(self.write_event(
            "check", kind="gate", phase="ticket_checks",
            reason="implementation_change", duration_ms=300,
        ))
        # An old zero-duration review is unknown, not evidence of free review.
        self.record(self.write_event("discovery", result="fail", duration_ms=0))
        self.record(self.write_event(
            "repair", kind="repair", phase="repair_non_micro",
            reason="review_finding", duration_ms=None,
        ))
        self.record(self.write_event(
            "closure", phase="closure", reason="accepted_findings", duration_ms=500,
        ))
        self.record(self.write_event(
            "acceptance", kind="ticket_phase", phase="acceptance",
            reason="protected_staging", duration_ms=100,
        ))
        self.record(self.write_event(
            "result", kind="ticket_result", phase="acceptance",
            reason="ticket_completed", duration_ms=0,
        ))
        self.record(self.write_event(
            "closeout", kind="run_phase", ticket=None, phase="closeout",
            reason="final_closeout", state_owners=[], duration_ms=50,
        ))

        summary = json.loads(self.tool("summary", "--input", str(self.metrics)).stdout)
        self.assertEqual(5150, summary["operation_duration_ms"])
        self.assertEqual(4850, summary["workflow_duration_ms"])
        self.assertEqual(2, summary["unmeasured_event_count"])
        self.assertEqual(2, summary["unmeasured_workflow_event_count"])
        rows = {(r["ticket"], r["kind"], r["phase"]): r for r in summary["phase_timings"]}
        self.assertEqual(120, rows[(None, "run_phase", "preparation")]["duration_ms"])
        self.assertEqual(1, rows[("03", "review_round", "discovery")]["unmeasured_count"])
        self.assertEqual(1, rows[("03", "repair", "repair_non_micro")]["unmeasured_count"])
        self.assertNotIn(("03", "gate", "ticket_checks"), rows)

    def test_init_rejects_unignored_repository_output_and_existing_metrics_file(self) -> None:
        inside = self.repo / "run-metrics.jsonl"
        rejected = self.init(output=inside, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("must be ignored by Git", rejected.stderr)
        self.assertFalse(inside.exists())

        self.init()
        original = self.metrics.read_bytes()
        duplicate = self.init(check=False)
        self.assertNotEqual(0, duplicate.returncode)
        self.assertIn("already exists", duplicate.stderr)
        self.assertEqual(original, self.metrics.read_bytes())

    def test_ticket_scope_allows_an_explicit_empty_state_owner_list(self) -> None:
        self.init()
        scope = self.write_event(
            "documentation-scope",
            kind="ticket_scope",
            ticket="docs-01",
            phase="scope_accepted",
            reason="declared_contract",
            result="pass",
            scope_paths=["docs/guide.md"],
            state_owners=[],
            duration_ms=0,
        )

        self.assertEqual("recorded\n", self.record(scope).stdout)
        summary = json.loads(
            self.tool("summary", "--input", str(self.metrics)).stdout
        )
        self.assertEqual([], summary["ticket_scope"]["docs-01"]["state_owners"])

    def test_record_rejects_invalid_or_ambiguous_event_without_changing_log(self) -> None:
        self.init()
        original = self.metrics.read_bytes()
        invalid = self.write_event(
            "invalid",
            reason="free form reason",
            scope_paths=["src/Runtime.kt", "src/Runtime.kt"],
        )

        rejected = self.record(invalid, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("event reason", rejected.stderr)
        self.assertEqual(original, self.metrics.read_bytes())

    def test_record_refuses_a_manually_created_repository_local_log(self) -> None:
        self.init()
        inside = self.repo / "run-metrics.jsonl"
        inside.write_bytes(self.metrics.read_bytes())
        event = self.write_event("valid")

        rejected = self.tool(
            "record",
            "--output",
            str(inside),
            "--event-file",
            str(event),
            check=False,
        )
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("must be ignored by Git", rejected.stderr)
        self.assertEqual(self.metrics.read_bytes(), inside.read_bytes())


if __name__ == "__main__":
    unittest.main()
