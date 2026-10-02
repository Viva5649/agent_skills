#!/usr/bin/env python3
"""Integration tests for deterministic final-gate input manifests."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = SKILL_ROOT / "scripts" / "gate_state.py"
REVIEW_SCRIPT = SKILL_ROOT / "scripts" / "review_state.py"


def run(
    *args: str,
    cwd: Path,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


class GateStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run("git", "init", "--quiet", cwd=self.repo)

        (self.repo / "src").mkdir()
        (self.repo / "src/main.txt").write_text("production v1\n", encoding="utf-8")
        (self.repo / "build.gradle").write_text("tasks.register('check')\n", encoding="utf-8")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/guide.md").write_text("guide v1\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text("src/ignored.tmp\n", encoding="utf-8")
        run("git", "add", ".", cwd=self.repo)
        run(
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--quiet",
            "-m",
            "initial fixture",
            cwd=self.repo,
        )

        self.run_start = self.root / "run-start"
        run(
            sys.executable,
            str(REVIEW_SCRIPT),
            "capture",
            "--output",
            str(self.run_start),
            cwd=self.repo,
        )
        self.command = self.root / "command.txt"
        self.command.write_text("./gradlew check\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def gate_tool(
        self, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return run(sys.executable, str(GATE_SCRIPT), *args, cwd=self.repo, check=check)

    def capture(
        self,
        name: str,
        *,
        inputs: list[str] | None = None,
        command: Path | None = None,
        gate_id: str = "full-build",
        check: bool = True,
        output: Path | None = None,
    ) -> tuple[Path, subprocess.CompletedProcess[str]]:
        target = output or self.root / f"{name}.json"
        arguments = [
            "capture",
            "--output",
            str(target),
            "--gate-id",
            gate_id,
            "--run-start",
            str(self.run_start),
            "--command-file",
            str(command or self.command),
        ]
        for input_path in inputs if inputs is not None else ["src/main.txt", "build.gradle"]:
            arguments.extend(["--input-path", input_path])
        return target, self.gate_tool(*arguments, check=check)

    def compare(
        self,
        before: Path,
        before_hash: str,
        after: Path,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self.gate_tool(
            "compare",
            "--before",
            str(before),
            "--before-sha256",
            before_hash,
            "--after",
            str(after),
            check=check,
        )

    @staticmethod
    def capture_result(result: subprocess.CompletedProcess[str]) -> dict[str, str]:
        return json.loads(result.stdout)

    def test_identical_inputs_are_reusable_after_unrelated_tracked_doc_change(self) -> None:
        before, before_result = self.capture("before")
        evidence = self.capture_result(before_result)

        (self.repo / "docs/guide.md").write_text("guide v2\n", encoding="utf-8")
        run("git", "add", "docs/guide.md", cwd=self.repo)
        after, _ = self.capture("after")

        compared = self.compare(before, evidence["manifest_sha256"], after)
        self.assertEqual("reusable\n", compared.stdout)

    def test_changed_indexed_input_is_not_reusable(self) -> None:
        before, before_result = self.capture("before")
        evidence = self.capture_result(before_result)
        (self.repo / "src/main.txt").write_text("production v2\n", encoding="utf-8")
        run("git", "add", "src/main.txt", cwd=self.repo)
        after, _ = self.capture("after")

        compared = self.compare(
            before, evidence["manifest_sha256"], after, check=False
        )
        self.assertNotEqual(0, compared.returncode)
        self.assertIn("changed: indexed inputs", compared.stderr)

    def test_changed_command_is_not_reusable(self) -> None:
        before, before_result = self.capture("before")
        evidence = self.capture_result(before_result)
        second_command = self.root / "second-command.txt"
        second_command.write_text("./gradlew clean check\n", encoding="utf-8")
        after, _ = self.capture("after", command=second_command)

        compared = self.compare(
            before, evidence["manifest_sha256"], after, check=False
        )
        self.assertNotEqual(0, compared.returncode)
        self.assertIn("changed: command", compared.stderr)

    def test_changed_declaration_is_not_reusable(self) -> None:
        before, before_result = self.capture("before", inputs=["src/main.txt"])
        evidence = self.capture_result(before_result)
        after, _ = self.capture("after", inputs=["src/main.txt", "build.gradle"])

        compared = self.compare(
            before, evidence["manifest_sha256"], after, check=False
        )
        self.assertNotEqual(0, compared.returncode)
        self.assertIn("input declarations", compared.stderr)

    def test_invalid_path_declarations_fail_closed(self) -> None:
        cases = (
            ("missing", ["missing.txt"], "does not exist"),
            ("outside", ["../outside.txt"], "repository-relative"),
            ("empty", [""], "repository-relative"),
            ("glob", ["src/*.txt"], "glob syntax"),
            (
                "overlap",
                ["src", "src/main.txt"],
                "must not overlap",
            ),
        )
        for name, inputs, message in cases:
            with self.subTest(name=name):
                output, result = self.capture(name, inputs=inputs, check=False)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(message, result.stderr)
                self.assertFalse(output.exists())

    def test_untracked_exact_input_is_rejected(self) -> None:
        (self.repo / "scratch.txt").write_text("scratch\n", encoding="utf-8")
        output, result = self.capture(
            "untracked", inputs=["scratch.txt"], check=False
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("does not expand to a tracked index entry", result.stderr)
        self.assertFalse(output.exists())

    def test_unstaged_tracked_input_is_rejected(self) -> None:
        (self.repo / "src/main.txt").write_text("unstaged\n", encoding="utf-8")
        output, result = self.capture(
            "unstaged", inputs=["src/main.txt"], check=False
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("differ between the working tree and index", result.stderr)
        self.assertFalse(output.exists())

    def test_unmerged_input_is_rejected(self) -> None:
        base = run(
            "git", "rev-parse", "HEAD:src/main.txt", cwd=self.repo
        ).stdout.strip()
        ours = run(
            "git", "hash-object", "-w", "--stdin", cwd=self.repo, input_text="ours\n"
        ).stdout.strip()
        theirs = run(
            "git", "hash-object", "-w", "--stdin", cwd=self.repo, input_text="theirs\n"
        ).stdout.strip()
        run("git", "update-index", "--force-remove", "src/main.txt", cwd=self.repo)
        run(
            "git",
            "update-index",
            "--index-info",
            cwd=self.repo,
            input_text=(
                f"100644 {base} 1\tsrc/main.txt\n"
                f"100644 {ours} 2\tsrc/main.txt\n"
                f"100644 {theirs} 3\tsrc/main.txt\n"
            ),
        )

        output, result = self.capture(
            "unmerged", inputs=["src/main.txt"], check=False
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unmerged index entry", result.stderr)
        self.assertFalse(output.exists())

    def test_nonignored_untracked_path_inside_directory_is_rejected(self) -> None:
        (self.repo / "src/scratch.txt").write_text("scratch\n", encoding="utf-8")
        output, result = self.capture("directory", inputs=["src"], check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("contains non-ignored untracked paths", result.stderr)
        self.assertIn("src/scratch.txt", result.stderr)
        self.assertFalse(output.exists())

    def test_ignored_untracked_path_inside_directory_does_not_change_manifest(self) -> None:
        before, before_result = self.capture("before", inputs=["src"])
        evidence = self.capture_result(before_result)
        (self.repo / "src/ignored.tmp").write_text("local cache\n", encoding="utf-8")
        after, _ = self.capture("after", inputs=["src"])

        compared = self.compare(before, evidence["manifest_sha256"], after)
        self.assertEqual("reusable\n", compared.stdout)

    def test_wrong_or_tampered_prior_manifest_hash_is_rejected(self) -> None:
        before, before_result = self.capture("before")
        evidence = self.capture_result(before_result)
        after, _ = self.capture("after")

        wrong = self.compare(before, "0" * 64, after, check=False)
        self.assertNotEqual(0, wrong.returncode)
        self.assertIn("does not match the retained evidence", wrong.stderr)

        before.write_bytes(before.read_bytes() + b" ")
        tampered = self.compare(
            before, evidence["manifest_sha256"], after, check=False
        )
        self.assertNotEqual(0, tampered.returncode)
        self.assertIn("does not match the retained evidence", tampered.stderr)

    def test_capture_requires_new_output_git_does_not_track(self) -> None:
        inside = self.repo / "gate-inputs.json"
        _, rejected = self.capture("inside", output=inside, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("must be ignored by Git", rejected.stderr)
        self.assertFalse(inside.exists())

        outside, _ = self.capture("outside")
        original = outside.read_bytes()
        _, duplicate = self.capture("duplicate", output=outside, check=False)
        self.assertNotEqual(0, duplicate.returncode)
        self.assertIn("already exists", duplicate.stderr)
        self.assertEqual(original, outside.read_bytes())


if __name__ == "__main__":
    unittest.main()
