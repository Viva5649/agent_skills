"""Evidence summaries retain source outcomes without making acceptance decisions."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/evidence_summary.py"


class EvidenceSummaryTest(unittest.TestCase):
    def test_mixed_outcomes_and_report_are_preserved_without_aggregate_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = {
                "failed.json": {"status": "FAIL", "exit_code": 1},
                "repaired.json": {"status": "PASS", "exit_code": 0},
                "pending.json": {"status": "pending"},
                "nested.json": {"checks": [{"status": "PASS"}]},
            }
            args = []
            for name, record in records.items():
                path = root / name
                path.write_text(json.dumps(record), encoding="utf-8")
                args.extend(["--artifact", name, str(path)])
            report = root / "review.md"
            report.write_text("# Review\nPASS\n", encoding="utf-8")
            args.extend(["--artifact", "review", str(report)])
            output = root / "summary.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), *args, "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(output.read_text())
            self.assertEqual(set(summary), {"artifacts"})
            for artifact in summary["artifacts"]:
                raw = Path(artifact["path"]).read_bytes()
                self.assertEqual(artifact["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(
                [row["reported"] for row in summary["artifacts"]],
                [*list(records.values())[:3], {}, {}],
            )
            self.assertEqual(
                json.loads(result.stdout)["sha256"],
                hashlib.sha256(output.read_bytes()).hexdigest(),
            )

    def test_invalid_input_cannot_publish_a_partial_or_overwrite_existing_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "good.json"
            good.write_text('{"status":"PASS"}')
            bad = root / "bad.json"
            bad.write_text('{"status":')
            output = root / "summary.json"
            cases = [
                ["--artifact", "good", str(good), "--artifact", "missing", str(root / "missing.json")],
                ["--artifact", "bad", str(bad)],
                ["--artifact", "same", str(good), "--artifact", "same", str(good)],
            ]
            for args in cases:
                with self.subTest(args=args):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), *args, "--output", str(output)],
                        capture_output=True, text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
            output.write_text("retained evidence\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--artifact", "good", str(good), "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "retained evidence\n")


if __name__ == "__main__":
    unittest.main()
