#!/usr/bin/env python3
"""Integration tests for independent execute-tickets review budgets."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_budget.py"


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


class ReviewBudgetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run("git", "init", "--quiet", cwd=self.repo)
        self.ledger = self.root / "runtime-v4" / "review-budget.jsonl"

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
        history = self.root / "verified-review-history.json"
        history.write_text("[]")
        return self.tool(
            "init",
            "--output",
            str(output or self.ledger),
            "--feature",
            "runtime-v4",
            "--run-start-id",
            "run-start-sha256:abc123",
            "--history-file", str(history),
            check=check,
        )

    def write_event(self, name: str, **overrides: object) -> Path:
        event: dict[str, object] = {
            "kind": "review_round",
            "ticket": "03",
            "phase": "discovery",
            "reason": "initial_ticket_review",
            "result": "pass",
        }
        event.update(overrides)
        path = self.root / f"{name}.json"
        path.write_text(json.dumps(event), encoding="utf-8")
        return path

    def record(self, event: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.tool(
            "record",
            "--output",
            str(self.ledger),
            "--event-file",
            str(event),
            check=check,
        )

    def validate(self, event: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.tool(
            "validate",
            "--output",
            str(self.ledger),
            "--event-file",
            str(event),
            check=check,
        )

    def test_init_rejects_epoch_log_that_would_reset_review_budget(self) -> None:
        reset_log = self.root / "runtime-v4" / "epoch-2" / "review-budget.jsonl"

        rejected = self.init(output=reset_log, check=False)

        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("exact feature review path", rejected.stderr)
        self.assertFalse(reset_log.exists())

        self.init()
        reset_log.parent.mkdir()
        reset_log.write_bytes(self.ledger.read_bytes())
        event = self.write_event("epoch-reset")
        for command in ("validate", "record"):
            with self.subTest(command=command):
                rejected = self.tool(
                    command,
                    "--output",
                    str(reset_log),
                    "--event-file",
                    str(event),
                    check=False,
                )
                self.assertNotEqual(0, rejected.returncode)
                self.assertIn("exact feature review path", rejected.stderr)

    def test_statistics_failures_cannot_change_review_permission(self) -> None:
        self.init()
        metrics = self.ledger.with_name("run-metrics.jsonl")
        stats_script = SCRIPT.with_name("metrics_state.py")
        for index, failure in enumerate(("missing", "malformed", "unwritable")):
            with self.subTest(failure=failure):
                if failure == "malformed":
                    metrics.write_text("broken JSON\n")
                elif failure == "unwritable":
                    metrics.unlink()
                    metrics.mkdir()
                failed_stats = run(
                    sys.executable, str(stats_script), "summary", "--input",
                    str(metrics), cwd=self.repo, check=False,
                )
                self.assertNotEqual(0, failed_stats.returncode)
                if failure == "unwritable":
                    blocked_parent = self.root / "blocked-artifact-root"
                    blocked_parent.write_text("a file prevents directory creation")
                    failed_write = run(
                        sys.executable, str(stats_script), "init", "--output",
                        str(blocked_parent / "runtime-v4" / "run-metrics.jsonl"),
                        "--feature", "runtime-v4", "--run-start-id",
                        "run-start-sha256:abc123", cwd=self.repo, check=False,
                    )
                    self.assertNotEqual(0, failed_write.returncode)
                event = self.write_event(failure, ticket=str(index))
                self.assertEqual("valid\n", self.validate(event).stdout)
                self.record(event)
                self.assertNotEqual(0, self.validate(event, check=False).returncode)

        # The deployed budget helper works even when the metrics script is absent.
        package = self.root / "scripts"
        package.mkdir()
        for name in ("review_budget.py", "review_state.py"):
            shutil.copyfile(SCRIPT.with_name(name), package / name)
        event = self.write_event("no-metrics-script", ticket="04")
        accepted = run(
            sys.executable, str(package / SCRIPT.name), "validate", "--output",
            str(self.ledger), "--event-file", str(event), cwd=self.repo,
        )
        self.assertEqual("valid\n", accepted.stdout)

    def test_resume_uses_verified_history_without_metrics(self) -> None:
        discovery = self.write_event("prior-discovery", result="fail")
        repair = self.write_event(
            "prior-repair", kind="repair", phase="repair_non_micro",
            reason="review_finding", result="pass",
        )
        history = self.root / "verified-review-history.json"
        history.write_text(json.dumps([json.loads(p.read_text()) for p in (discovery, repair)]))
        args = (
            "--output", str(self.ledger), "--feature", "runtime-v4",
            "--run-start-id", "retained-run-start", "--history-file", str(history),
        )
        valid_history = history.read_text()
        history.write_text("{}")
        self.assertNotEqual(0, self.tool("init", *args, check=False).returncode)
        self.assertFalse(self.ledger.exists())
        history.write_text(valid_history)
        self.tool("init", *args)
        self.assertNotEqual(0, self.validate(discovery, check=False).returncode)
        closure = self.write_event("closure", phase="closure", reason="accepted_findings")
        self.assertEqual("valid\n", self.validate(closure).stdout)
        self.record(closure)
        retained = self.ledger.read_bytes()
        history.write_text("[]")
        self.assertNotEqual(0, self.tool("init", *args, check=False).returncode)
        self.assertEqual(retained, self.ledger.read_bytes())


    def test_review_rounds_require_exact_phase_order_and_reason(self) -> None:
        self.init()
        discovery = self.write_event("discovery", result="fail")
        repair_one = self.write_event(
            "repair-one",
            kind="repair",
            phase="repair_non_micro",
            reason="review_finding",
            result="pass",
        )
        closure = self.write_event(
            "closure",
            phase="closure",
            reason="accepted_findings",
            result="fail",
        )
        repair_two = self.write_event(
            "repair-two",
            kind="repair",
            phase="repair_non_micro",
            reason="review_finding",
            result="pass",
        )
        regression = self.write_event(
            "regression",
            phase="regression_closure",
            reason="repair_regression",
            result="pass",
        )
        for event in (discovery, repair_one, closure, repair_two, regression):
            self.assertEqual("valid\n", self.validate(event).stdout)
            self.assertEqual("recorded\n", self.record(event).stdout)

        original = self.ledger.read_bytes()
        duplicate = self.write_event("duplicate", result="pass")
        rejected = self.record(duplicate, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("duplicate review phase", rejected.stderr)
        self.assertEqual(original, self.ledger.read_bytes())

        wrong_reason = self.write_event(
            "wrong-reason",
            ticket="04",
            reason="accepted_findings",
        )
        rejected = self.record(wrong_reason, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("phase/reason is invalid", rejected.stderr)
        self.assertEqual(original, self.ledger.read_bytes())


    def test_micro_repair_rejects_another_reviewer_round(self) -> None:
        self.init()
        discovery = self.write_event("discovery", result="fail")
        repair = self.write_event(
            "repair",
            kind="repair",
            phase="repair_micro",
            reason="review_finding",
            result="pass",
        )
        for event in (discovery, repair):
            self.assertEqual("recorded\n", self.record(event).stdout)

        original = self.ledger.read_bytes()
        closure = self.write_event(
            "closure",
            phase="closure",
            reason="accepted_findings",
            result="pass",
        )
        rejected = self.validate(closure, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("repair_micro must finish without another reviewer round", rejected.stderr)
        self.assertEqual(original, self.ledger.read_bytes())

        rejected = self.record(closure, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertEqual(original, self.ledger.read_bytes())


    def test_final_review_rounds_have_one_deterministic_three_phase_budget(self) -> None:
        self.init()
        discovery = self.write_event(
            "final-discovery",
            kind="final_review",
            ticket=None,
            phase="integration_review",
            reason="integration_risk",
            result="fail",
        )
        self.assertEqual("recorded\n", self.record(discovery).stdout)

        duplicate = self.record(discovery, check=False)
        self.assertNotEqual(0, duplicate.returncode)
        self.assertIn("duplicate final review phase", duplicate.stderr)

        closure = self.write_event(
            "final-closure",
            kind="final_review",
            ticket=None,
            phase="integration_review",
            reason="accepted_findings",
            result="fail",
        )
        missing_repair = self.record(closure, check=False)
        self.assertNotEqual(0, missing_repair.returncode)
        self.assertIn("requires a completed non-micro repair", missing_repair.stderr)

        repair_one = self.write_event(
            "final-repair-one",
            kind="repair",
            phase="repair_non_micro",
            reason="review_finding",
            result="pass",
        )
        self.assertEqual("recorded\n", self.record(repair_one).stdout)
        self.assertEqual("recorded\n", self.record(closure).stdout)

        repair_two = self.write_event(
            "final-repair-two",
            kind="repair",
            phase="repair_non_micro",
            reason="review_finding",
            result="pass",
        )
        regression = self.write_event(
            "final-regression",
            kind="final_review",
            ticket=None,
            phase="integration_review",
            reason="repair_regression",
            result="fail",
        )
        self.assertEqual("recorded\n", self.record(repair_two).stdout)
        self.assertEqual("recorded\n", self.record(regression).stdout)

        exhausted_targeted = self.write_event(
            "exhausted-targeted", kind="final_repair_review", reason="high_risk",
        )
        rejected = self.validate(exhausted_targeted, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("cumulative final review budget is exhausted", rejected.stderr)

        fourth = self.write_event(
            "final-fourth",
            kind="final_review",
            ticket=None,
            phase="integration_review",
            reason="final_closure",
            result="pass",
        )
        rejected = self.record(fourth, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("final_review phase/reason is invalid", rejected.stderr)


    def test_closure_requires_a_completed_non_micro_repair(self) -> None:
        self.init()
        discovery = self.write_event("discovery", result="fail")
        self.assertEqual("recorded\n", self.record(discovery).stdout)

        original = self.ledger.read_bytes()
        closure = self.write_event(
            "closure",
            phase="closure",
            reason="accepted_findings",
            result="pass",
        )
        rejected = self.record(closure, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("requires a completed non-micro repair", rejected.stderr)
        self.assertEqual(original, self.ledger.read_bytes())


    def test_final_repair_budget_uses_completed_owner_and_failed_final_round(self) -> None:
        self.init()
        targeted = self.write_event(
            "targeted", kind="final_repair_review", reason="high_risk", result="fail"
        )
        self.assertNotEqual(0, self.validate(targeted, check=False).returncode)
        accepted = self.write_event(
            "accepted", kind="ticket_result", phase="acceptance", reason="ticket_completed"
        )
        final = self.write_event(
            "final", kind="final_review", ticket=None, phase="integration_review",
            reason="integration_risk", result="fail",
        )
        self.record(accepted)
        self.record(final)
        invented_owner = self.write_event(
            "invented", kind="final_repair_review", ticket="03-final-fix-2", reason="high_risk"
        )
        self.assertNotEqual(0, self.validate(invented_owner, check=False).returncode)
        self.record(targeted)
        closure = self.write_event(
            "targeted-closure", kind="final_repair_review", phase="closure", reason="high_risk"
        )
        self.assertNotEqual(0, self.validate(closure, check=False).returncode)
        repair = self.write_event(
            "repair", kind="repair", phase="repair_non_micro", reason="review_finding"
        )
        self.record(repair)
        self.record(closure)
        before = self.ledger.read_bytes()
        for retry in (targeted, closure):
            self.assertNotEqual(0, self.record(retry, check=False).returncode)
            self.assertEqual(before, self.ledger.read_bytes())
        cumulative = self.write_event(
            "cumulative", kind="final_review", ticket=None, phase="integration_review",
            reason="accepted_findings",
        )
        self.record(cumulative)
        self.assertNotEqual(0, self.validate(targeted, check=False).returncode)
        events = [json.loads(line) for line in self.ledger.read_text().splitlines()[1:]]
        self.assertEqual(2, sum(e["kind"] == "final_repair_review" for e in events))


    def test_failed_standard_final_repair_cannot_reset_lane_or_release_final_closure(self) -> None:
        self.init()
        for event in (
            self.write_event("accepted", kind="ticket_result", phase="acceptance", reason="ticket_completed"),
            self.write_event("final", kind="final_review", ticket=None, phase="integration_review", reason="integration_risk", result="fail"),
            self.write_event("targeted", kind="final_repair_review", reason="standard", result="fail"),
            self.write_event("repair", kind="repair", phase="repair_non_micro", reason="review_finding"),
        ):
            self.record(event)
        before = self.ledger.read_bytes()
        for attempt in (
            self.write_event("retry", kind="final_repair_review", phase="closure", reason="standard"),
            self.write_event("relabel", kind="final_repair_review", reason="high_risk"),
            self.write_event("release", kind="final_review", ticket=None, phase="integration_review", reason="accepted_findings"),
        ):
            self.assertNotEqual(0, self.validate(attempt, check=False).returncode)
            self.assertNotEqual(0, self.record(attempt, check=False).returncode)
            self.assertEqual(before, self.ledger.read_bytes())


    def test_final_micro_inspection_closes_failed_batch_without_another_review(self) -> None:
        self.init()
        for ticket in ("03", "04"):
            self.record(self.write_event(
                "accepted-" + ticket, kind="ticket_result", ticket=ticket,
                phase="acceptance", reason="ticket_completed",
            ))
        self.record(self.write_event(
            "final", kind="final_review", ticket=None, phase="integration_review",
            reason="integration_risk", result="fail",
        ))
        self.record(self.write_event(
            "failed-targeted", kind="final_repair_review", reason="high_risk", result="fail",
        ))
        self.record(self.write_event(
            "micro-inspection", kind="repair", phase="repair_micro", reason="review_finding",
        ))
        extra_review = self.write_event(
            "extra-review", kind="final_repair_review", phase="closure", reason="high_risk",
        )
        self.assertNotEqual(0, self.validate(extra_review, check=False).returncode)
        cumulative = self.write_event(
            "cumulative", kind="final_review", ticket=None, phase="integration_review",
            reason="accepted_findings",
        )
        # All-micro closure uses verified inspection, not another cumulative reviewer.
        self.assertNotEqual(0, self.validate(cumulative, check=False).returncode)
        repair = self.write_event(
            "other-owner-repair", kind="repair", ticket="04", phase="repair_non_micro",
            reason="review_finding",
        )
        self.record(repair)
        self.record(self.write_event(
            "other-owner-review", kind="final_repair_review", ticket="04", reason="standard",
        ))
        self.assertEqual("valid\n", self.validate(cumulative).stdout)
        self.record(repair)
        self.assertNotEqual(0, self.validate(cumulative, check=False).returncode)
        events = [json.loads(line) for line in self.ledger.read_text().splitlines()[1:]]
        self.assertEqual("fail", next(e for e in events if e["kind"] == "final_repair_review")["result"])


    def test_final_closure_retains_reviewed_non_micro_repair_after_micro_inspection(self) -> None:
        self.init()
        repair = self.write_event(
            "repair", kind="repair", phase="repair_non_micro", reason="review_finding",
        )
        self.record(repair)
        self.record(self.write_event(
            "accepted", kind="ticket_result", phase="acceptance", reason="ticket_completed",
        ))
        self.record(self.write_event(
            "final", kind="final_review", ticket=None, phase="integration_review",
            reason="integration_risk", result="fail",
        ))
        closure = self.write_event(
            "closure", kind="final_review", ticket=None, phase="integration_review",
            reason="accepted_findings", result="fail",
        )
        # A repair predating the failed review cannot qualify its closure.
        rejected = self.validate(closure, check=False)
        self.assertIn("requires a completed non-micro repair", rejected.stderr)
        self.assertNotEqual(0, rejected.returncode)
        self.record(repair)
        self.record(self.write_event(
            "targeted", kind="final_repair_review", reason="standard",
        ))
        self.record(self.write_event(
            "micro", kind="repair", phase="repair_micro", reason="review_finding",
        ))
        before = self.ledger.read_bytes()
        self.assertEqual("valid\n", self.validate(closure).stdout)
        self.assertEqual(before, self.ledger.read_bytes())
        self.assertEqual("recorded\n", self.record(closure).stdout)
        self.assertTrue(self.ledger.read_bytes().startswith(before))
        events = [json.loads(line) for line in self.ledger.read_text().splitlines()[1:]]
        self.assertEqual(2, sum(e["kind"] == "final_review" for e in events))
        self.assertEqual(1, sum(e["kind"] == "final_repair_review" for e in events))
        # The same historical repair cannot authorize the next failed round.
        regression = self.write_event(
            "regression", kind="final_review", ticket=None, phase="integration_review",
            reason="repair_regression",
        )
        self.assertNotEqual(0, self.validate(regression, check=False).returncode)



if __name__ == "__main__":
    unittest.main()
