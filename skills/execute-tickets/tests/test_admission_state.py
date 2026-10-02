import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts/admission_state.py"


def load_manifest_lib():
    module_spec = importlib.util.spec_from_file_location(
        "manifest_lib_under_test", SKILL_ROOT / "scripts/manifest_lib.py"
    )
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


MANIFEST_LIB = load_manifest_lib()


def file_record(root: Path, relative: str, *, authority: bool = True) -> dict[str, object]:
    path = root / relative
    data = path.read_bytes()
    record: dict[str, object] = {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }
    if authority:
        # Reuse the production boundary. A second implementation here would be an oracle
        # that disagrees with the code it exists to check.
        record["authority_sha256"] = MANIFEST_LIB.authority_sha256(path)
    return record


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
        self.receipt = self.feature / "implementation-ticket-admission.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_spec(self, *, display_title: str | None, body: str = "# Demo spec\n") -> None:
        block = f"---\ndisplay_title: {display_title}\n---\n" if display_title else ""
        (self.feature / "spec.md").write_text(block + body, encoding="utf-8")

    def run_verify(self, *directories: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "verify",
                "--repo",
                str(self.repo),
                "--receipt",
                str(self.receipt),
                *directories,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def write_receipt(
        self, *, authority: bool = True, review: dict[str, object] | None = None
    ) -> None:
        self.receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "feature": "demo",
                    "decision": "admitted-by-user",
                    "candidate_manifest_sha256": "a" * 64,
                    "decision_record_sha256": "b" * 64,
                    "authority": [
                        file_record(
                            self.repo,
                            (self.issues / "01-first.md").relative_to(self.repo).as_posix(),
                            authority=authority,
                        ),
                        file_record(
                            self.repo,
                            (self.feature / "spec.md").relative_to(self.repo).as_posix(),
                            authority=authority,
                        ),
                    ],
                    "review": {
                        "status": "FAIL",
                        "report_sha256": "c" * 64,
                        "unresolved_findings": ["R12-002"],
                        **(review or {}),
                    },
                    "user_dispositions": [
                        {
                            "finding": "R12-002",
                            "disposition": "closed-by-clarification",
                            "reason": "The user approved these exact authority bytes.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_verify_accepts_exact_user_admission(self) -> None:
        self.write_receipt()

        verified = self.run_verify()

        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-user\n", verified.stdout)

    def test_verify_accepts_review_admission_with_author_corrections(self) -> None:
        self.write_receipt()
        payload = json.loads(self.receipt.read_text(encoding="utf-8"))
        payload["decision"] = "admitted-by-review"
        payload["review"]["status"] = "PASS_WITH_CORRECTIONS"
        payload["review"]["unresolved_findings"] = []
        payload["review"]["author_corrections"] = ["R1-001"]
        payload["user_dispositions"] = []
        self.receipt.write_text(json.dumps(payload), encoding="utf-8")

        verified = self.run_verify()

        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-review\n", verified.stdout)

    def test_verify_checks_authority_in_both_tracker_directories(self) -> None:
        self.feature = self.repo / "docs/specs/demo"
        self.issues = self.repo / "work/tickets/demo"
        self.feature.mkdir(parents=True)
        self.issues.mkdir(parents=True)
        (self.feature / "spec.md").write_text("# Tracker spec\n", encoding="utf-8")
        (self.issues / "01-first.md").write_text("# Tracker ticket\n", encoding="utf-8")
        tracker = self.repo / "docs/agents/issue-tracker.md"
        tracker.parent.mkdir(parents=True)
        tracker.write_text(
            "Spec: `docs/specs/<feature>/spec.md`\nTickets: `work/tickets/<feature>/`\n",
            encoding="utf-8",
        )
        self.receipt = self.feature / "implementation-ticket-admission.json"
        self.write_receipt()
        directories = ("--spec-dir", "docs/specs/demo", "--tickets-dir", "work/tickets/demo")

        verified = self.run_verify(*directories)
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-user\n", verified.stdout)
        wrong = self.run_verify(
            "--spec-dir", "docs/specs/demo", "--tickets-dir", ".spec/demo/issues"
        )
        self.assertNotEqual(0, wrong.returncode)
        self.assertIn("authority path set changed", wrong.stderr)
        missing = self.run_verify("--spec-dir", "docs/specs/demo")
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("--tickets-dir is required", missing.stderr)
        (self.issues / "02-late.md").write_text("# Unadmitted ticket\n", encoding="utf-8")
        changed = self.run_verify(*directories)
        self.assertNotEqual(0, changed.returncode)
        self.assertIn("authority path set changed", changed.stderr)

    def test_verify_rejects_changed_authority(self) -> None:
        self.write_receipt()
        (self.issues / "01-first.md").write_text("# Changed\n", encoding="utf-8")

        verified = self.run_verify()

        self.assertNotEqual(0, verified.returncode)
        self.assertIn("changed authority input", verified.stderr)

    def test_verify_rejects_an_unadmitted_ticket(self) -> None:
        self.write_receipt()
        (self.issues / "02-late.md").write_text("# Late ticket\n", encoding="utf-8")

        verified = self.run_verify()

        self.assertNotEqual(0, verified.returncode)
        self.assertIn("authority path set changed", verified.stderr)

    def test_verify_ignores_a_presentation_only_spec_rename(self) -> None:
        self.write_spec(display_title="Original label")
        self.write_receipt()

        self.assertEqual(0, self.run_verify().returncode)

        self.write_spec(display_title="Renamed label")
        verified = self.run_verify()

        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-user\n", verified.stdout)

    def test_verify_rejects_a_spec_body_change_under_the_same_block(self) -> None:
        self.write_spec(display_title="Stable label")
        self.write_receipt()
        self.write_spec(display_title="Stable label", body="# Demo spec\n\nNew requirement.\n")

        verified = self.run_verify()

        self.assertNotEqual(0, verified.returncode)
        self.assertIn("changed authority input", verified.stderr)

    def test_verify_accepts_a_receipt_written_before_authority_digests(self) -> None:
        self.write_receipt(authority=False)

        verified = self.run_verify()

        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-user\n", verified.stdout)

    def test_verify_accepts_delta_lineage_within_budget(self) -> None:
        self.write_receipt(
            review={
                "opening_type": "delta",
                "base_exhaustive_report_sha256": "d" * 64,
                "delta_generation": 2,
            }
        )

        verified = self.run_verify()

        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("admitted-by-user\n", verified.stdout)

    def test_verify_rejects_unusable_review_lineage(self) -> None:
        for review, expected in (
            (
                {
                    "opening_type": "delta",
                    "base_exhaustive_report_sha256": "d" * 64,
                    "delta_generation": 3,
                },
                "over-budget delta generation",
            ),
            (
                {
                    "opening_type": "narrowed",
                    "base_exhaustive_report_sha256": "d" * 64,
                    "delta_generation": 1,
                },
                "unreadable review lineage",
            ),
            (
                {
                    "opening_type": "delta",
                    "base_exhaustive_report_sha256": "not-a-hash",
                    "delta_generation": 1,
                },
                "base exhaustive report hash",
            ),
        ):
            with self.subTest(opening=review["opening_type"], expected=expected):
                self.write_receipt(review=review)

                verified = self.run_verify()

                self.assertNotEqual(0, verified.returncode)
                self.assertIn(expected, verified.stderr)

    def test_verify_rejects_incomplete_user_dispositions(self) -> None:
        self.write_receipt()
        payload = json.loads(self.receipt.read_text(encoding="utf-8"))
        payload["user_dispositions"] = []
        self.receipt.write_text(json.dumps(payload), encoding="utf-8")

        verified = self.run_verify()

        self.assertNotEqual(0, verified.returncode)
        self.assertIn("must dispose every unresolved finding", verified.stderr)

    def test_verify_rejects_receipt_outside_the_feature(self) -> None:
        self.write_receipt()
        wrong = self.root / "admission.json"
        wrong.write_bytes(self.receipt.read_bytes())
        self.receipt = wrong

        verified = self.run_verify()

        self.assertNotEqual(0, verified.returncode)
        self.assertIn("exact feature admission path", verified.stderr)


if __name__ == "__main__":
    unittest.main()
