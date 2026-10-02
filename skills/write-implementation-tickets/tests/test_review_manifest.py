import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts/review_manifest.py"


class ReviewManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / "src").mkdir()
        (self.repo / "src/owner.py").write_text("OWNER = 'current'\n", encoding="utf-8")
        self.ticket_path = Path(".spec/demo/issues/01-demo.md")
        (self.repo / self.ticket_path).parent.mkdir(parents=True)
        (self.repo / self.ticket_path).write_text("# Ticket\n", encoding="utf-8")
        self.manifest = self.root / "review-inputs.json"
        self.next_manifest = self.root / "closure-inputs.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def capture(
        self, output: Path | None = None, *extra_paths: str
    ) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            "capture",
            "--repo",
            str(self.repo),
            "--output",
            str(output or self.manifest),
            "--path",
            self.ticket_path.as_posix(),
            "--path",
            "src/owner.py",
            *(item for path in extra_paths for item in ("--path", path)),
        )

    def test_capture_and_verify_unchanged_inputs(self) -> None:
        captured = self.capture()
        self.assertEqual(0, captured.returncode, captured.stderr)
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(1, payload["schema_version"])
        self.assertEqual(
            [".spec/demo/issues/01-demo.md", "src/owner.py"],
            [item["path"] for item in payload["files"]],
        )

        verified = self.run_script("verify", "--manifest", str(self.manifest))
        self.assertEqual(0, verified.returncode, verified.stderr)
        self.assertEqual("valid\n", verified.stdout)

    def test_verify_rejects_changed_input(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / "src/owner.py").write_text("OWNER = 'changed'\n", encoding="utf-8")

        verified = self.run_script("verify", "--manifest", str(self.manifest))
        self.assertNotEqual(0, verified.returncode)
        self.assertIn("changed", verified.stderr)

    def test_verify_rejects_missing_input(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / self.ticket_path).unlink()

        verified = self.run_script("verify", "--manifest", str(self.manifest))
        self.assertNotEqual(0, verified.returncode)
        self.assertIn("missing", verified.stderr)

    def test_capture_rejects_paths_outside_repository(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")

        captured = self.run_script(
            "capture",
            "--repo",
            str(self.repo),
            "--output",
            str(self.manifest),
            "--path",
            str(outside),
        )
        self.assertNotEqual(0, captured.returncode)
        self.assertIn("repository-relative", captured.stderr)

    def test_capture_rejects_manifest_inside_repository(self) -> None:
        captured = self.run_script(
            "capture",
            "--repo",
            str(self.repo),
            "--output",
            str(self.repo / "manifest.json"),
            "--path",
            self.ticket_path.as_posix(),
        )
        self.assertNotEqual(0, captured.returncode)
        self.assertIn("outside the repository", captured.stderr)

    def test_verify_rejects_manifest_without_repository(self) -> None:
        self.manifest.write_text(
            json.dumps({"schema_version": 1, "files": []}), encoding="utf-8"
        )

        verified = self.run_script("verify", "--manifest", str(self.manifest))
        self.assertNotEqual(0, verified.returncode)
        self.assertIn("manifest repository", verified.stderr)

    def test_closure_accepts_only_the_named_ticket_change(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / self.ticket_path).write_text("# Corrected ticket\n", encoding="utf-8")
        self.assertEqual(0, self.capture(self.next_manifest).returncode)

        compared = self.run_script(
            "closure",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--ticket",
            self.ticket_path.as_posix(),
        )

        self.assertEqual(0, compared.returncode, compared.stderr)
        self.assertEqual("closure-valid\n", compared.stdout)

    def test_closure_uses_tracker_ticket_directory_without_loosening_allowlist(self) -> None:
        self.ticket_path = Path("work/tickets/demo/01-demo.md")
        ticket = self.repo / self.ticket_path
        ticket.parent.mkdir(parents=True)
        ticket.write_text("# Ticket\n", encoding="utf-8")
        tracker = self.repo / "docs/agents/issue-tracker.md"
        tracker.parent.mkdir(parents=True)
        tracker.write_text("Tickets: `work/tickets/<feature>/`\n", encoding="utf-8")
        self.assertEqual(0, self.capture().returncode)
        ticket.write_text("# Corrected ticket\n", encoding="utf-8")
        self.assertEqual(0, self.capture(self.next_manifest).returncode)
        arguments = (
            "closure", "--before", str(self.manifest), "--after", str(self.next_manifest)
        )

        compared = self.run_script(
            *arguments, "--tickets-dir", "work/tickets/demo", "--ticket", str(self.ticket_path)
        )
        self.assertEqual(0, compared.returncode, compared.stderr)
        self.assertEqual("closure-valid\n", compared.stdout)
        missing = self.run_script(*arguments, "--ticket", str(self.ticket_path))
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("--tickets-dir is required", missing.stderr)
        outside = self.run_script(
            *arguments, "--tickets-dir", "work/tickets/demo", "--ticket", "src/owner.py"
        )
        self.assertNotEqual(0, outside.returncode)
        self.assertIn("closure ticket must match", outside.stderr)

    def test_closure_accepts_unchanged_inputs_for_review_drift(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        self.assertEqual(0, self.capture(self.next_manifest).returncode)

        compared = self.run_script(
            "closure",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--ticket",
            self.ticket_path.as_posix(),
        )

        self.assertEqual(0, compared.returncode, compared.stderr)
        self.assertEqual("closure-valid\n", compared.stdout)

    def test_closure_rejects_a_changed_repository_input(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / "src/owner.py").write_text("OWNER = 'changed'\n", encoding="utf-8")
        self.assertEqual(0, self.capture(self.next_manifest).returncode)

        compared = self.run_script(
            "closure",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--ticket",
            self.ticket_path.as_posix(),
        )

        self.assertNotEqual(0, compared.returncode)
        self.assertIn("non-ticket review input changed", compared.stderr)

    def test_closure_rejects_a_changed_input_set(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / "src/new_boundary.py").write_text("BOUNDARY = True\n", encoding="utf-8")
        self.assertEqual(
            0,
            self.capture(self.next_manifest, "src/new_boundary.py").returncode,
        )

        compared = self.run_script(
            "closure",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--ticket",
            self.ticket_path.as_posix(),
        )

        self.assertNotEqual(0, compared.returncode)
        self.assertIn("review input set changed", compared.stderr)

    def test_closure_rejects_a_different_repository(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        other_repo = self.root / "other-repo"
        other_repo.mkdir()
        payload["repository"] = str(other_repo)
        self.next_manifest.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

        compared = self.run_script(
            "closure",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--ticket",
            self.ticket_path.as_posix(),
        )

        self.assertNotEqual(0, compared.returncode)
        self.assertIn("review repository changed", compared.stderr)

    def test_closure_rejects_a_non_ticket_allowlist_path(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / "src/owner.py").write_text("OWNER = 'changed'\n", encoding="utf-8")
        self.assertEqual(0, self.capture(self.next_manifest).returncode)

        compared = self.run_script(
            "closure",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--ticket",
            "src/owner.py",
        )

        self.assertNotEqual(0, compared.returncode)
        self.assertIn("closure ticket must match", compared.stderr)


    def write_spec(self, body: str) -> str:
        spec = Path(".spec/demo/spec.md")
        (self.repo / spec).write_text(body, encoding="utf-8")
        return spec.as_posix()

    def test_delta_reports_the_exact_changed_set(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / "src/owner.py").write_text("OWNER = 'next'\n", encoding="utf-8")
        self.assertEqual(0, self.capture(self.next_manifest).returncode)
        delta_output = self.root / "delta.json"

        result = self.run_script(
            "delta",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--output",
            str(delta_output),
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("delta-valid\n", result.stdout)
        payload = json.loads(delta_output.read_text(encoding="utf-8"))
        self.assertEqual(["src/owner.py"], [item["path"] for item in payload["changed"]])
        self.assertNotEqual(
            payload["changed"][0]["before_authority_sha256"],
            payload["changed"][0]["after_authority_sha256"],
        )

    def test_delta_rejects_an_unchanged_authority_set(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        self.assertEqual(0, self.capture(self.next_manifest).returncode)

        result = self.run_script(
            "delta",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--output",
            str(self.root / "delta.json"),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("no authority change", result.stderr)
        self.assertFalse((self.root / "delta.json").exists())

    def test_delta_rejects_a_changed_input_set(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        extra = self.write_spec("# Spec\n")
        self.assertEqual(0, self.capture(self.next_manifest, extra).returncode)

        result = self.run_script(
            "delta",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--output",
            str(self.root / "delta.json"),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("review input set changed", result.stderr)

    def test_delta_rejects_output_inside_the_repository(self) -> None:
        self.assertEqual(0, self.capture().returncode)
        (self.repo / "src/owner.py").write_text("OWNER = 'next'\n", encoding="utf-8")
        self.assertEqual(0, self.capture(self.next_manifest).returncode)

        result = self.run_script(
            "delta",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--output",
            str(self.repo / "delta.json"),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("outside the repository", result.stderr)

    def test_presentation_label_change_is_not_drift(self) -> None:
        spec = self.write_spec(
            "---\ndisplay_title: Old label\n---\n\n## 1\n\nThe worker exits 2.\n"
        )
        self.assertEqual(0, self.capture(self.manifest, spec).returncode)
        (self.repo / spec).write_text(
            "---\ndisplay_title: 需求看板\n---\n\n## 1\n\nThe worker exits 2.\n",
            encoding="utf-8",
        )

        verified = self.run_script("verify", "--manifest", str(self.manifest))
        self.assertEqual(0, verified.returncode, verified.stderr)

        self.assertEqual(0, self.capture(self.next_manifest, spec).returncode)
        closed = self.run_script(
            "closure",
            "--before",
            str(self.manifest),
            "--after",
            str(self.next_manifest),
            "--tickets-dir",
            ".spec/demo/issues",
            "--ticket",
            self.ticket_path.as_posix(),
        )
        self.assertEqual(0, closed.returncode, closed.stderr)
        self.assertEqual("closure-valid\n", closed.stdout)

    def test_malformed_presentation_block_remains_authority(self) -> None:
        spec = self.write_spec(
            "---\ndisplay_title: Old label\nowner: platform\n---\n\nThe worker exits 2.\n"
        )
        self.assertEqual(0, self.capture(self.manifest, spec).returncode)
        (self.repo / spec).write_text(
            "---\ndisplay_title: Renamed\nowner: platform\n---\n\nThe worker exits 2.\n",
            encoding="utf-8",
        )

        verified = self.run_script("verify", "--manifest", str(self.manifest))

        self.assertNotEqual(0, verified.returncode)
        self.assertIn("changed reviewed input", verified.stderr)


if __name__ == "__main__":
    unittest.main()
