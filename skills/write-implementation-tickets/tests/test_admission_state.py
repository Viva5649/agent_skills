import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts/admission_state.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AdmissionStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.feature = self.repo / ".spec/demo"
        self.issues = self.feature / "issues"
        self.issues.mkdir(parents=True)
        (self.feature / "spec.md").write_text("# Demo spec\n", encoding="utf-8")
        (self.issues / "01-first.md").write_text("# Ticket 01\n", encoding="utf-8")
        (self.issues / "02-second.md").write_text("# Ticket 02\n", encoding="utf-8")
        self.candidate = self.root / "candidate.json"
        self.decision_record = self.root / "decision.json"
        self.review_report = self.root / "report.md"
        self.review_report.write_text("# Review\n\nResult: FAIL\n", encoding="utf-8")
        self.receipt = self.feature / "implementation-ticket-admission.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def capture_candidate(self, *directories: str) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            "candidate",
            "--repo",
            str(self.repo),
            "--feature",
            "demo",
            "--output",
            str(self.candidate),
            *directories,
        )

    def write_decision(
        self,
        *,
        decision: str,
        review_status: str,
        findings: list[str],
        dispositions: list[dict[str, str]],
        author_corrections: list[str] | None = None,
        opening_type: str = "exhaustive",
        base_report: str | None = None,
        review_epoch_reason: str | None = None,
    ) -> None:
        record = {
            "schema_version": 1,
            "candidate_manifest_sha256": sha256(self.candidate),
            "decision": decision,
            "review_status": review_status,
            "review_opening_type": opening_type,
            "base_exhaustive_report_sha256": base_report
            or sha256(self.review_report),
            "unresolved_findings": findings,
            "author_corrections": author_corrections or [],
            "user_dispositions": dispositions,
        }
        if review_epoch_reason is not None:
            record["review_epoch_reason"] = review_epoch_reason
        self.decision_record.write_text(
            json.dumps(record),
            encoding="utf-8",
        )

    def admit(self, *directories: str) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            "admit",
            "--candidate",
            str(self.candidate),
            "--decision-record",
            str(self.decision_record),
            "--review-report",
            str(self.review_report),
            "--output",
            str(self.receipt),
            *directories,
        )

    def test_admission_uses_tracker_directories_instead_of_existing_defaults(self) -> None:
        spec_dir = self.repo / "docs/specs/demo"
        tickets_dir = self.repo / "work/tickets/demo"
        spec_dir.mkdir(parents=True)
        tickets_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Tracker spec\n", encoding="utf-8")
        (tickets_dir / "01-first.md").write_text("# Tracker ticket\n", encoding="utf-8")
        tracker = self.repo / "docs/agents/issue-tracker.md"
        tracker.parent.mkdir(parents=True)
        tracker.write_text(
            "Spec: `docs/specs/<feature>/spec.md`\n"
            "Tickets: `work/tickets/<feature>/`\n", encoding="utf-8"
        )
        directories = ("--spec-dir", "docs/specs/demo", "--tickets-dir", "work/tickets/demo")
        self.receipt = spec_dir / "implementation-ticket-admission.json"

        captured = self.capture_candidate(*directories)
        self.assertEqual(0, captured.returncode, captured.stderr)
        self.write_decision(
            decision="admitted-by-review", review_status="PASS", findings=[], dispositions=[]
        )
        admitted = self.admit(*directories)
        self.assertEqual(0, admitted.returncode, admitted.stderr)
        verified = self.run_script(
            "verify", "--repo", str(self.repo), "--receipt", str(self.receipt), *directories
        )
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-review\n", verified.stdout)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(
            ["docs/specs/demo/spec.md", "work/tickets/demo/01-first.md"],
            [item["path"] for item in receipt["authority"]],
        )

    def test_review_pass_admits_exact_authority(self) -> None:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")
        self.write_decision(
            decision="admitted-by-review",
            review_status="PASS",
            findings=[],
            dispositions=[],
        )

        admitted = self.admit()

        self.assertEqual(0, admitted.returncode, admitted.stderr)
        self.assertEqual("admitted-by-review\n", admitted.stdout)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual("demo", receipt["feature"])
        self.assertEqual(
            [
                ".spec/demo/issues/01-first.md",
                ".spec/demo/issues/02-second.md",
                ".spec/demo/spec.md",
            ],
            [item["path"] for item in receipt["authority"]],
        )
        verified = self.run_script(
            "verify", "--repo", str(self.repo), "--receipt", str(self.receipt)
        )
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-review\n", verified.stdout)

    def test_review_with_author_corrections_admits_corrected_authority(self) -> None:
        (self.issues / "01-first.md").write_text("# Corrected ticket\n", encoding="utf-8")
        self.assertEqual(0, self.capture_candidate().returncode)
        self.review_report.write_text(
            "# Review\n\nResult: PASS_WITH_CORRECTIONS\n", encoding="utf-8"
        )
        self.write_decision(
            decision="admitted-by-review",
            review_status="PASS_WITH_CORRECTIONS",
            findings=[],
            author_corrections=["R1-001"],
            dispositions=[],
        )

        admitted = self.admit()

        self.assertEqual(0, admitted.returncode, admitted.stderr)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual("PASS_WITH_CORRECTIONS", receipt["review"]["status"])
        self.assertEqual(["R1-001"], receipt["review"]["author_corrections"])
        self.assertEqual(0, self.verify_receipt().returncode)

    def test_review_with_author_corrections_requires_a_correction_id(self) -> None:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.write_decision(
            decision="admitted-by-review",
            review_status="PASS_WITH_CORRECTIONS",
            findings=[],
            dispositions=[],
        )

        admitted = self.admit()

        self.assertNotEqual(0, admitted.returncode)
        self.assertIn("requires author corrections", admitted.stderr)

    def test_tracker_prevents_silent_fallback_for_either_directory(self) -> None:
        tracker = self.repo / "docs/agents/issue-tracker.md"
        tracker.parent.mkdir(parents=True)
        tracker.write_text(
            "Spec: `.spec/<feature>/spec.md`\nTickets: `.spec/<feature>/issues/`\n",
            encoding="utf-8",
        )
        for arguments, missing_option in (
            ((), "--spec-dir"),
            (("--spec-dir", ".spec/demo"), "--tickets-dir"),
            (("--tickets-dir", ".spec/demo/issues"), "--spec-dir"),
        ):
            with self.subTest(missing_option=missing_option, arguments=arguments):
                result = self.capture_candidate(*arguments)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(missing_option, result.stderr)
                self.assertFalse(self.candidate.exists())

    def test_shared_directory_does_not_count_the_spec_as_a_ticket(self) -> None:
        directories = ("--spec-dir", ".spec/demo", "--tickets-dir", ".spec/demo")
        missing_ticket = self.capture_candidate(*directories)
        self.assertNotEqual(0, missing_ticket.returncode)
        self.assertIn("at least one implementation ticket", missing_ticket.stderr)

        (self.feature / "01-first.md").write_text("# Ticket beside spec\n", encoding="utf-8")
        captured = self.capture_candidate(*directories)
        self.assertEqual(0, captured.returncode, captured.stderr)
        manifest = json.loads(self.candidate.read_text(encoding="utf-8"))
        self.assertEqual(
            [".spec/demo/01-first.md", ".spec/demo/spec.md"],
            [item["path"] for item in manifest["authority"]],
        )

    def test_user_may_admit_failed_review_with_complete_dispositions(self) -> None:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.write_decision(
            decision="admitted-by-user",
            review_status="FAIL",
            findings=["R12-002"],
            dispositions=[
                {
                    "finding": "R12-002",
                    "disposition": "closed-by-clarification",
                    "reason": "The final text clarifies the existing return boundary.",
                }
            ],
        )

        admitted = self.admit()

        self.assertEqual(0, admitted.returncode, admitted.stderr)
        self.assertEqual("admitted-by-user\n", admitted.stdout)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual("FAIL", receipt["review"]["status"])
        self.assertEqual(
            "closed-by-clarification",
            receipt["user_dispositions"][0]["disposition"],
        )
        verified = self.run_script(
            "verify", "--repo", str(self.repo), "--receipt", str(self.receipt)
        )
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-user\n", verified.stdout)

    def test_admit_rejects_authority_drift_after_user_approval(self) -> None:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.write_decision(
            decision="admitted-by-user",
            review_status="FAIL",
            findings=["R12-002"],
            dispositions=[
                {
                    "finding": "R12-002",
                    "disposition": "closed-by-clarification",
                    "reason": "Approved clarification.",
                }
            ],
        )
        (self.issues / "02-second.md").write_text("# Changed after approval\n", encoding="utf-8")

        admitted = self.admit()

        self.assertNotEqual(0, admitted.returncode)
        self.assertIn("changed authority input", admitted.stderr)
        self.assertFalse(self.receipt.exists())

    def test_user_admission_requires_one_disposition_per_finding(self) -> None:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.write_decision(
            decision="admitted-by-user",
            review_status="FAIL",
            findings=["R12-002"],
            dispositions=[],
        )

        admitted = self.admit()

        self.assertNotEqual(0, admitted.returncode)
        self.assertIn("must dispose every unresolved finding", admitted.stderr)

    def test_verify_rejects_a_new_ticket_absent_from_the_receipt(self) -> None:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")
        self.write_decision(
            decision="admitted-by-review",
            review_status="PASS",
            findings=[],
            dispositions=[],
        )
        self.assertEqual(0, self.admit().returncode)
        (self.issues / "03-late.md").write_text("# Late ticket\n", encoding="utf-8")

        verified = self.run_script(
            "verify", "--repo", str(self.repo), "--receipt", str(self.receipt)
        )

        self.assertNotEqual(0, verified.returncode)
        self.assertIn("authority path set changed", verified.stderr)

    def test_admit_rejects_output_outside_the_feature(self) -> None:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")
        self.write_decision(
            decision="admitted-by-review",
            review_status="PASS",
            findings=[],
            dispositions=[],
        )

        admitted = self.run_script(
            "admit",
            "--candidate",
            str(self.candidate),
            "--decision-record",
            str(self.decision_record),
            "--review-report",
            str(self.review_report),
            "--output",
            str(self.root / "wrong.json"),
        )

        self.assertNotEqual(0, admitted.returncode)
        self.assertIn("exact feature admission path", admitted.stderr)


    def admit_review_pass(self, **decision_kwargs: object) -> subprocess.CompletedProcess[str]:
        self.assertEqual(0, self.capture_candidate().returncode)
        self.write_decision(
            decision="admitted-by-review",
            review_status="PASS",
            findings=[],
            dispositions=[],
            **decision_kwargs,
        )
        return self.admit()

    def verify_receipt(self) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            "verify", "--repo", str(self.repo), "--receipt", str(self.receipt)
        )

    def test_renaming_the_presentation_label_keeps_the_receipt_valid(self) -> None:
        spec = self.feature / "spec.md"
        spec.write_text(
            "---\ndisplay_title: Old label\n---\n\n## 1. Authority\n\nThe worker exits 2.\n",
            encoding="utf-8",
        )
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")
        self.assertEqual(0, self.admit_review_pass().returncode)

        spec.write_text(
            "---\ndisplay_title: 需求看板\n---\n\n## 1. Authority\n\nThe worker exits 2.\n",
            encoding="utf-8",
        )

        verified = self.verify_receipt()
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-review\n", verified.stdout)

    def test_authority_body_change_still_invalidates_the_receipt(self) -> None:
        spec = self.feature / "spec.md"
        spec.write_text(
            "---\ndisplay_title: Label\n---\n\n## 1. Authority\n\nThe worker exits 2.\n",
            encoding="utf-8",
        )
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")
        self.assertEqual(0, self.admit_review_pass().returncode)

        spec.write_text(
            "---\ndisplay_title: Label\n---\n\n## 1. Authority\n\nThe worker exits 3.\n",
            encoding="utf-8",
        )

        verified = self.verify_receipt()
        self.assertNotEqual(0, verified.returncode)
        self.assertIn("changed authority input", verified.stderr)

    def test_malformed_presentation_block_stays_authority(self) -> None:
        spec = self.feature / "spec.md"
        spec.write_text(
            "---\ndisplay_title: Label\nowner: platform\n---\n\nThe worker exits 2.\n",
            encoding="utf-8",
        )
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")
        self.assertEqual(0, self.admit_review_pass().returncode)

        spec.write_text(
            "---\ndisplay_title: Renamed\nowner: platform\n---\n\nThe worker exits 2.\n",
            encoding="utf-8",
        )

        verified = self.verify_receipt()
        self.assertNotEqual(0, verified.returncode)
        self.assertIn("changed authority input", verified.stderr)

    def test_delta_lineage_increments_until_the_budget_is_exhausted(self) -> None:
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")
        base = sha256(self.review_report)
        self.assertEqual(0, self.admit_review_pass().returncode)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual("exhaustive", receipt["review"]["opening_type"])
        self.assertEqual(0, receipt["review"]["delta_generation"])

        for generation in (1, 2):
            (self.feature / "spec.md").write_text(
                f"# Demo spec\n\nRevision {generation}\n", encoding="utf-8"
            )
            admitted = self.admit_review_pass(opening_type="delta", base_report=base)
            self.assertEqual(0, admitted.returncode, admitted.stderr)
            receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
            self.assertEqual("delta", receipt["review"]["opening_type"])
            self.assertEqual(generation, receipt["review"]["delta_generation"])

        (self.feature / "spec.md").write_text("# Demo spec\n\nRevision 3\n", encoding="utf-8")
        exhausted = self.admit_review_pass(opening_type="delta", base_report=base)
        self.assertNotEqual(0, exhausted.returncode)
        self.assertIn("consecutive delta budget exhausted", exhausted.stderr)
        self.assertIn("current request must stop", exhausted.stderr)
        self.assertIn("user-authority-change", exhausted.stderr)

        reset = self.admit_review_pass()
        self.assertNotEqual(0, reset.returncode)
        self.assertIn("explicit user-authority-change", reset.stderr)

        reset = self.admit_review_pass(
            review_epoch_reason="user-authority-change"
        )
        self.assertEqual(0, reset.returncode, reset.stderr)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(0, receipt["review"]["delta_generation"])
        self.assertEqual(1, receipt["review"]["exhaustive_epoch"])
        self.assertEqual(
            "user-authority-change", receipt["review"]["epoch_reason"]
        )

    def test_delta_requires_a_matching_base_and_an_existing_receipt(self) -> None:
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")

        missing = self.admit_review_pass(opening_type="delta")
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("requires an existing verified receipt", missing.stderr)
        self.assertFalse(self.receipt.exists())

        self.assertEqual(0, self.admit_review_pass().returncode)
        (self.feature / "spec.md").write_text("# Demo spec\n\nRevised\n", encoding="utf-8")

        wrong_base = self.admit_review_pass(opening_type="delta", base_report="b" * 64)
        self.assertNotEqual(0, wrong_base.returncode)
        self.assertIn("does not match the existing receipt lineage", wrong_base.stderr)

    def test_admit_rejects_an_unknown_review_opening_type(self) -> None:
        self.review_report.write_text("# Review\n\nResult: PASS\n", encoding="utf-8")

        admitted = self.admit_review_pass(opening_type="closure")

        self.assertNotEqual(0, admitted.returncode)
        self.assertIn("must be exhaustive or delta", admitted.stderr)


if __name__ == "__main__":
    unittest.main()
