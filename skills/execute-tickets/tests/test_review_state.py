#!/usr/bin/env python3
"""Integration tests for review_state.py using a temporary Git repository."""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_state.py"


def run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


class ReviewStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run("git", "init", "--quiet", cwd=self.repo)
        (self.repo / "README.md").write_text("# Fixture repository\n", encoding="utf-8")
        (self.repo / "settings.gradle").write_text(
            'rootProject.name = "fixture"\n', encoding="utf-8"
        )
        (self.repo / "gradle.properties").write_text("fixture=true\n", encoding="utf-8")
        run("git", "add", "README.md", "settings.gradle", "gradle.properties", cwd=self.repo)
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

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_repository_set_stages_each_repository_without_changing_history(self) -> None:
        other = self.root / "MLLM"
        run("git", "clone", "--quiet", str(self.repo), str(other), cwd=self.root)
        heads = {}
        for repo in (self.repo, other):
            heads[repo] = run("git", "rev-parse", "HEAD", cwd=repo).stdout
            (repo / "README.md").write_text("user staged baseline\n", encoding="utf-8")
            run("git", "add", "README.md", cwd=repo)
            (repo / "gradle.properties").write_text("protected=true\n", encoding="utf-8")

        pre = self.root / "multi-pre"
        self.tool(
            "capture", "--output", str(pre),
            "--repository", f"QIFramework={self.repo}",
            "--repository", f"MLLM={other}",
            "--scope-path", "QIFramework:settings.gradle",
            "--scope-path", "MLLM:engine.py",
        )
        (self.repo / "settings.gradle").write_text("// accepted QI change\n", encoding="utf-8")
        (other / "engine.py").write_text("value = 2\n", encoding="utf-8")
        review = self.capture("multi-review", baseline=pre)
        self.tool("verify", "--snapshot", str(review))
        result = self.tool(
            "stage", "--baseline", str(pre), "--snapshot", str(review),
            "--output", str(self.root / "staging"),
        )
        self.assertEqual({"QIFramework", "MLLM"}, set(json.loads(result.stdout)["repositories"]))
        for repo, expected in ((self.repo, "settings.gradle"), (other, "engine.py")):
            self.assertEqual(heads[repo], run("git", "rev-parse", "HEAD", cwd=repo).stdout)
            self.assertEqual(
                {"README.md", expected},
                set(run("git", "diff", "--cached", "--name-only", cwd=repo).stdout.splitlines()),
            )
            self.assertEqual("user staged baseline\n", run("git", "show", ":README.md", cwd=repo).stdout)
            self.assertEqual("gradle.properties\n", run("git", "diff", "--name-only", cwd=repo).stdout)
            self.assertEqual("protected=true\n", (repo / "gradle.properties").read_text(encoding="utf-8"))

    def test_submodule_content_is_reviewed_and_staged_without_changing_gitlink(self) -> None:
        run(
            "git", "-c", "protocol.file.allow=always", "submodule", "add", "--quiet",
            str(self.repo), "MLLM", cwd=self.repo,
        )
        run(
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "commit", "--quiet", "-m", "fixture submodule", cwd=self.repo,
        )
        child = self.repo / "MLLM"
        (child / "README.md").write_text("user's existing child commit\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=child)
        run("git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--quiet", "-m", "existing child commit", cwd=child)
        run("git", "add", "MLLM", cwd=self.repo)
        # Local ignore preferences must not hide a pre-existing staged gitlink
        # from the frozen index used to reconstruct the accepted parent index.
        run("git", "config", "submodule.MLLM.ignore", "all", cwd=self.repo)
        run("git", "config", "diff.submodule", "log", cwd=self.repo)
        gitlink = run("git", "ls-files", "--stage", "--", "MLLM", cwd=self.repo).stdout
        heads = {repo: run("git", "rev-parse", "HEAD", cwd=repo).stdout for repo in (self.repo, child)}
        (child / "README.md").write_text("candidate before admission\n", encoding="utf-8")
        (child / "gradle.properties").write_text("protected=true\n", encoding="utf-8")
        pre = self.root / "submodule-pre"
        self.tool(
            "capture", "--output", str(pre),
            "--repository", f"QIFramework={self.repo}", "--repository", f"MLLM={child}",
            "--scope-path", "QIFramework:settings.gradle", "--scope-path", "MLLM:README.md",
        )
        (self.repo / "settings.gradle").write_text("// candidate\n", encoding="utf-8")
        (child / "README.md").write_text("reviewed candidate\n", encoding="utf-8")
        review = self.capture("submodule-review", baseline=pre)
        (child / "README.md").write_text("unreviewed change while still dirty\n", encoding="utf-8")
        drifted = self.tool("verify", "--snapshot", str(review), check=False)
        self.assertNotEqual(0, drifted.returncode)
        self.assertIn("MLLM", drifted.stderr)
        (child / "README.md").write_text("reviewed candidate\n", encoding="utf-8")
        staged = self.tool("stage", "--baseline", str(pre), "--snapshot", str(review), "--output", str(self.root / "submodule-stage"), check=False)
        self.assertEqual(0, staged.returncode, staged.stderr)
        self.assertEqual("reviewed candidate\n", run("git", "show", ":README.md", cwd=child).stdout)
        self.assertEqual(gitlink, run("git", "ls-files", "--stage", "--", "MLLM", cwd=self.repo).stdout)
        for repo in (self.repo, child):
            self.assertEqual(heads[repo], run("git", "rev-parse", "HEAD", cwd=repo).stdout)
        self.assertEqual("gradle.properties\n", run("git", "diff", "--name-only", cwd=child).stdout)

    def tool(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return run(sys.executable, str(SCRIPT), *args, cwd=self.repo, check=check)

    def test_repository_error_reports_a_state_error_not_a_traceback(self) -> None:
        outside = self.root / "not-a-repository"
        outside.mkdir()
        result = self.tool(
            "capture", "--output", str(self.root / "rejected"),
            "--repository", f"QIFramework={self.repo}", "--repository", f"MLLM={outside}",
            check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("error: ", result.stderr)
        # An unhandled exception also exits 1, so stderr is the only signal that the
        # sys.modules alias in review_state.py still binds repository_state to one StateError.
        self.assertNotIn("Traceback", result.stderr)

    def test_repository_set_resumes_partial_staging_without_reaccepting_drift(self) -> None:
        other = self.root / "MLLM"
        run("git", "clone", "--quiet", str(self.repo), str(other), cwd=self.root)
        pre = self.root / "partial-pre"
        self.tool(
            "capture", "--output", str(pre),
            "--repository", f"QIFramework={self.repo}", "--repository", f"MLLM={other}",
            "--scope-path", "QIFramework:settings.gradle", "--scope-path", "MLLM:settings.gradle",
        )
        for repo in (self.repo, other):
            (repo / "settings.gradle").write_text("// accepted\n", encoding="utf-8")
        review = self.capture("partial-review", baseline=pre)
        stage_args = ("stage", "--baseline", str(pre), "--snapshot", str(review), "--output", str(self.root / "partial-stage"))
        lock = self.repo / ".git/index.lock"
        lock.write_bytes(b"another Git process owns this lock")
        failed = self.tool(*stage_args, check=False)
        self.assertNotEqual(0, failed.returncode)
        self.assertEqual("// accepted\n", run("git", "show", ":settings.gradle", cwd=other).stdout)
        self.assertEqual("", run("git", "diff", "--cached", "--name-only", cwd=self.repo).stdout)
        lock.unlink()
        (other / "settings.gradle").write_text("// unreviewed drift\n", encoding="utf-8")
        self.assertNotEqual(0, self.tool(*stage_args, check=False).returncode)
        self.assertEqual("", run("git", "diff", "--cached", "--name-only", cwd=self.repo).stdout)
        (other / "settings.gradle").write_text("// accepted\n", encoding="utf-8")
        resumed = self.tool(*stage_args, check=False)
        self.assertEqual(0, resumed.returncode, resumed.stderr)
        self.tool("verify", "--snapshot", str(self.root / "partial-stage/accepted"))
        for repo in (self.repo, other):
            self.assertEqual("// accepted\n", run("git", "show", ":settings.gradle", cwd=repo).stdout)
        narrowed = self.tool(*stage_args, "--allow-path", "QIFramework:settings.gradle", check=False)
        self.assertNotEqual(0, narrowed.returncode)
        self.assertIn("allowed set", narrowed.stderr)

    def test_repository_set_preserves_user_classified_drift_in_a_repository_without_scope(self) -> None:
        other = self.root / "MLLM"
        run("git", "clone", "--quiet", str(self.repo), str(other), cwd=self.root)
        (other / "gradle.properties").write_text("external=before\n", encoding="utf-8")
        pre = self.root / "drift-pre"
        self.tool(
            "capture", "--output", str(pre),
            "--repository", f"QIFramework={self.repo}", "--repository", f"MLLM={other}",
            "--scope-path", "QIFramework:settings.gradle",
        )
        (self.repo / "settings.gradle").write_text("// accepted\n", encoding="utf-8")
        (other / "gradle.properties").write_text("external=preserved\n", encoding="utf-8")
        refused = self.tool("capture", "--output", str(self.root / "refused"), "--baseline", str(pre), check=False)
        self.assertNotEqual(0, refused.returncode)
        report = self.drift("multi-drift", pre)
        payload = json.loads((report / "report.json").read_text(encoding="utf-8"))
        self.assertEqual("confirmation_required", payload["status"])
        self.assertEqual("gradle.properties", payload["repositories"]["MLLM"]["changes"][0]["path"])
        resolution = self.reconcile("multi-resolution", pre, report, {"MLLM:gradle.properties": "preserve"})
        review = self.capture("drift-review", baseline=pre, drift_resolution=resolution / "resolution.json")
        staging = self.root / "drift-stage"
        self.tool("stage", "--baseline", str(pre), "--snapshot", str(review), "--output", str(staging))
        self.assertEqual("", run("git", "diff", "--cached", "--name-only", cwd=other).stdout)
        self.assertEqual("external=preserved\n", (other / "gradle.properties").read_text(encoding="utf-8"))
        self.capture("next-pre", handoff=staging / "accepted", scope_paths=["MLLM:README.md"])

    def test_repository_set_rejects_staging_an_empty_implementation(self) -> None:
        other = self.root / "MLLM"
        run("git", "clone", "--quiet", str(self.repo), str(other), cwd=self.root)
        pre = self.root / "empty-pre"
        self.tool("capture", "--output", str(pre), "--repository", f"QIFramework={self.repo}", "--repository", f"MLLM={other}")
        review = self.capture("empty-review", baseline=pre)
        output = self.root / "empty-stage"
        result = self.tool("stage", "--baseline", str(pre), "--snapshot", str(review), "--output", str(output), check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("no changes to stage", result.stderr)
        self.assertFalse(output.exists())

    def test_repository_set_rejects_an_ignored_untracked_scope_path(self) -> None:
        other = self.root / "MLLM"
        run("git", "clone", "--quiet", str(self.repo), str(other), cwd=self.root)
        self.ignore_paths(other, "engine.py")
        (other / "engine.py").write_text("value = 1\n", encoding="utf-8")
        repositories = (
            "--repository", f"QIFramework={self.repo}",
            "--repository", f"MLLM={other}",
        )

        assessment = self.tool(
            "assess", *repositories, "--scope-path", "MLLM:engine.py", check=False
        )
        self.assertNotEqual(0, assessment.returncode)
        self.assertIn("engine.py", assessment.stderr)

        output = self.root / "multi-pre"
        capture = self.tool(
            "capture", "--output", str(output), *repositories,
            "--scope-path", "MLLM:engine.py", check=False,
        )
        self.assertNotEqual(0, capture.returncode)
        self.assertIn("engine.py", capture.stderr)
        self.assertFalse(output.exists())

    def test_staging_does_not_adopt_an_external_edit_during_index_preparation(self) -> None:
        other = self.root / "MLLM"
        run("git", "clone", "--quiet", str(self.repo), str(other), cwd=self.root)
        pre = self.root / "concurrent-pre"
        self.tool("capture", "--output", str(pre), "--repository", f"A={self.repo}", "--repository", f"B={other}", "--scope-path", "A:settings.gradle")
        (self.repo / "settings.gradle").write_text("// candidate\n", encoding="utf-8")
        review = self.capture("concurrent-review", baseline=pre)
        wrappers = self.root / "bin"
        wrappers.mkdir()
        wrapper = wrappers / "git"
        # The real Git process still runs. An independent writer edits B at the
        # first temporary-index operation, after the initial aggregate verify.
        wrapper.write_text(
            f"#!{sys.executable}\nimport os, sys\nfrom pathlib import Path\n"
            f"if 'read-tree' in sys.argv:\n    Path({str(other / 'README.md')!r}).write_text('external edit during staging\\n')\n"
            f"os.execv({shutil.which('git')!r}, ['git', *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "stage", "--baseline", str(pre), "--snapshot", str(review), "--output", str(self.root / "concurrent-stage")],
            cwd=self.repo, text=True, capture_output=True,
            env={**os.environ, "PATH": str(wrappers) + os.pathsep + os.environ["PATH"]},
        )
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("external edit during staging\n", (other / "README.md").read_text(encoding="utf-8"))
        for repo in (self.repo, other):
            self.assertEqual("", run("git", "diff", "--cached", "--name-only", cwd=repo).stdout)

    def capture(
        self,
        name: str,
        baseline: Path | None = None,
        scope_paths: list[str] | None = None,
        authority_paths: list[str] | None = None,
        authority_transition_paths: list[str] | None = None,
        drift_resolution: Path | None = None,
        handoff: Path | None = None,
        drift_output: Path | None = None,
    ) -> Path:
        output = self.root / name
        arguments = ["capture", "--output", str(output)]
        if baseline:
            arguments.extend(["--baseline", str(baseline)])
        if drift_resolution:
            arguments.extend(["--drift-resolution", str(drift_resolution)])
        if handoff:
            arguments.extend(["--handoff", str(handoff)])
        if drift_output:
            arguments.extend(["--drift-output", str(drift_output)])
        for scope_path in scope_paths or []:
            arguments.extend(["--scope-path", scope_path])
        for authority_path in authority_paths or []:
            arguments.extend(["--authority-path", authority_path])
        for transition_path in authority_transition_paths or []:
            arguments.extend(["--authority-transition-path", transition_path])
        self.tool(*arguments)
        return output

    def drift(
        self,
        name: str,
        baseline: Path,
        resolution: Path | None = None,
    ) -> Path:
        output = self.root / name
        arguments = [
            "drift",
            "--baseline",
            str(baseline),
            "--output",
            str(output),
        ]
        if resolution:
            arguments.extend(["--drift-resolution", str(resolution)])
        self.tool(*arguments)
        return output

    def reconcile(
        self,
        name: str,
        baseline: Path,
        report: Path,
        decisions: dict[str, str],
        resolution: Path | None = None,
    ) -> Path:
        decision = self.root / f"{name}-decision.json"
        decision.write_text(
            json.dumps({"decisions": decisions}, indent=2) + "\n",
            encoding="utf-8",
        )
        output = self.root / name
        arguments = [
            "reconcile",
            "--baseline",
            str(baseline),
            "--report",
            str(report / "report.json"),
            "--decision",
            str(decision),
            "--output",
            str(output),
        ]
        if resolution:
            arguments.extend(["--drift-resolution", str(resolution)])
        self.tool(*arguments)
        return output

    def write_ignored_feature(self) -> tuple[Path, Path]:
        """Create a feature whose process documents are excluded from Git."""
        gitignore = self.repo / ".gitignore"
        gitignore.write_text(".spec/\n", encoding="utf-8")
        run("git", "add", ".gitignore", cwd=self.repo)
        run(
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "commit", "--quiet", "-m", "ignore process documents", cwd=self.repo,
        )
        issues = self.repo / ".spec/example/issues"
        issues.mkdir(parents=True)
        spec = self.repo / ".spec/example/spec.md"
        ticket = issues / "01-example.md"
        spec.write_text("# spec\n", encoding="utf-8")
        ticket.write_text("**Status:** ready-for-agent\n", encoding="utf-8")
        return spec, ticket

    def ignore_paths(self, repo: Path, *patterns: str) -> None:
        """Commit Git ignore rules that hide fixture paths from untracked scans."""
        gitignore = repo / ".gitignore"
        gitignore.write_text("".join(f"{pattern}\n" for pattern in patterns), encoding="utf-8")
        run("git", "add", ".gitignore", cwd=repo)
        run(
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "commit", "--quiet", "-m", "ignore fixture paths", cwd=repo,
        )

    def write_receipt(self, spec: Path, ticket: Path) -> Path:
        """Record the feature's authority set in an admission receipt."""
        receipt = self.repo / ".spec/example/implementation-ticket-admission.json"

        def entry(path: Path) -> dict[str, object]:
            data = path.read_bytes()
            return {
                "path": path.relative_to(self.repo).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }

        receipt.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "feature": "example",
                    "authority": [entry(spec), entry(ticket)],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return receipt

    def test_capture_derives_the_authority_set_from_the_admission_receipt(self) -> None:
        spec, ticket = self.write_ignored_feature()
        self.write_receipt(spec, ticket)
        output = self.root / "run-start"

        self.tool(
            "capture",
            "--output",
            str(output),
            "--receipt",
            ".spec/example/implementation-ticket-admission.json",
        )

        authority = json.loads((output / "authority.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [
                ".spec/example/implementation-ticket-admission.json",
                ".spec/example/issues/01-example.md",
                ".spec/example/spec.md",
            ],
            [entry["path"] for entry in authority],
        )

    def test_capture_rejects_a_receipt_without_recorded_authority(self) -> None:
        self.write_ignored_feature()
        receipt = self.repo / ".spec/example/implementation-ticket-admission.json"
        receipt.write_text("{\"schema_version\": 1}\n", encoding="utf-8")

        result = self.tool(
            "capture",
            "--output",
            str(self.root / "run-start"),
            "--receipt",
            ".spec/example/implementation-ticket-admission.json",
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("does not record its authority paths", result.stderr)

    def test_review_sees_ticket_files_and_preserves_preexisting_untracked(self) -> None:
        readme = self.repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\naccepted ticket\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=self.repo)
        baseline_untracked = self.repo / "local-notes.txt"
        baseline_untracked.write_text("unrelated user input\n", encoding="utf-8")

        pre = self.capture("pre")
        readme.write_text(readme.read_text(encoding="utf-8") + "current ticket\n", encoding="utf-8")
        new_file = self.repo / "ticket-created.txt"
        new_file.write_text("new file\n", encoding="utf-8")

        review = self.capture("review", pre)
        unstaged = (review / "unstaged.patch").read_text(encoding="utf-8")
        ticket_untracked = json.loads((review / "ticket-untracked.json").read_text(encoding="utf-8"))

        self.assertIn("current ticket", unstaged)
        self.assertIn(" accepted ticket", unstaged)
        self.assertNotIn("+accepted ticket", unstaged)
        self.assertEqual(["ticket-created.txt"], [entry["path"] for entry in ticket_untracked])
        self.tool("verify", "--snapshot", str(review))

        self.tool("stage", "--baseline", str(pre), "--snapshot", str(review))
        self.assertEqual("", run("git", "diff", cwd=self.repo).stdout)
        self.assertIn("ticket-created.txt", run("git", "diff", "--cached", "--name-only", cwd=self.repo).stdout)
        self.assertIn("local-notes.txt", run("git", "ls-files", "--others", "--exclude-standard", cwd=self.repo).stdout)

    def test_supervisor_index_change_is_rejected(self) -> None:
        pre = self.capture("pre")
        readme = self.repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nsupervisor staged this\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=self.repo)

        result = self.tool(
            "capture",
            "--output",
            str(self.root / "review"),
            "--baseline",
            str(pre),
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("index changed", result.stderr)

    def test_assess_reports_existing_worktree_files_owned_by_ticket_scope(self) -> None:
        readme = self.repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nuser edit\n", encoding="utf-8")
        scratch = self.repo / "local-input.txt"
        scratch.write_text("user input\n", encoding="utf-8")

        result = self.tool(
            "assess",
            "--scope-path",
            "README.md",
            "--scope-path",
            "local-input.txt",
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        assessment = json.loads(result.stdout)
        self.assertEqual(
            ["README.md"], assessment["scope_owned_tracked_unstaged_paths"]
        )
        self.assertEqual(
            ["local-input.txt"], assessment["scope_owned_untracked_paths"]
        )

    def test_assess_rejects_an_ignored_untracked_scope_path(self) -> None:
        self.ignore_paths(self.repo, "local-input.txt")
        (self.repo / "local-input.txt").write_text("ignored user input\n", encoding="utf-8")

        result = self.tool("assess", "--scope-path", "local-input.txt", check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Git-ignored paths", result.stderr)
        self.assertIn("local-input.txt", result.stderr)

    def test_capture_rejects_an_ignored_untracked_scope_path(self) -> None:
        self.ignore_paths(self.repo, "local-input.txt")
        (self.repo / "local-input.txt").write_text("ignored user input\n", encoding="utf-8")
        output = self.root / "pre"

        result = self.tool(
            "capture", "--output", str(output), "--scope-path", "local-input.txt", check=False
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Git-ignored paths", result.stderr)
        self.assertIn("local-input.txt", result.stderr)
        self.assertFalse(output.exists())

    def test_scope_rejects_a_future_ignored_path(self) -> None:
        # A declared path that does not exist yet still escapes the snapshot when
        # creating it would make Git ignore it.
        self.ignore_paths(self.repo, "generated/")

        assessment = self.tool("assess", "--scope-path", "generated/new.txt", check=False)
        self.assertNotEqual(0, assessment.returncode)
        self.assertIn("generated/new.txt", assessment.stderr)

        output = self.root / "pre"
        capture = self.tool(
            "capture", "--output", str(output), "--scope-path", "generated/new.txt", check=False
        )
        self.assertNotEqual(0, capture.returncode)
        self.assertIn("generated/new.txt", capture.stderr)
        self.assertFalse(output.exists())

    def test_scope_snapshot_coverage_keeps_tracked_ignored_and_plain_future_paths(self) -> None:
        # A tracked path stays deliverable even when an ignore pattern matches it,
        # and a declared path Git would not ignore is not an ignored future file.
        self.ignore_paths(self.repo, "README.md")
        readme = self.repo / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "tracked ticket edit\n", encoding="utf-8"
        )

        pre = self.capture("pre", scope_paths=["README.md", "local-future.txt"])
        snapshot = json.loads((pre / "snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(["README.md", "local-future.txt"], snapshot["ticket_scope_paths"])

        readme.write_text(
            readme.read_text(encoding="utf-8") + "later ticket edit\n", encoding="utf-8"
        )
        review = self.capture("review", pre)
        ticket_patch = (review / "ticket-tracked.patch").read_text(encoding="utf-8")
        self.assertIn("later ticket edit", ticket_patch)

    def test_scope_stages_preexisting_tracked_edit_with_ticket_change(self) -> None:
        readme = self.repo / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\npreexisting edit\n",
            encoding="utf-8",
        )
        pre = self.capture("pre", scope_paths=["README.md"])
        readme.write_text(
            readme.read_text(encoding="utf-8") + "ticket edit\n",
            encoding="utf-8",
        )

        review = self.capture("review", pre)
        ticket_patch = (review / "ticket-tracked.patch").read_text(encoding="utf-8")
        self.assertIn("preexisting edit", ticket_patch)
        self.assertIn("ticket edit", ticket_patch)

        self.tool("stage", "--baseline", str(pre), "--snapshot", str(review))

        self.assertEqual("", run("git", "diff", cwd=self.repo).stdout)
        cached = run("git", "diff", "--cached", cwd=self.repo).stdout
        self.assertIn("preexisting edit", cached)
        self.assertIn("ticket edit", cached)

    def test_scope_stages_preexisting_untracked_and_preserves_outside_untracked(self) -> None:
        owned = self.repo / "local-input.txt"
        owned.write_text("preexisting input\n", encoding="utf-8")
        outside = self.repo / "local-notes.txt"
        outside.write_text("outside scope\n", encoding="utf-8")
        pre = self.capture("pre", scope_paths=["local-input.txt"])
        owned.write_text("preexisting input\nticket edit\n", encoding="utf-8")

        review = self.capture("review", pre)
        ticket_untracked = json.loads(
            (review / "ticket-untracked.json").read_text(encoding="utf-8")
        )
        self.assertEqual(["local-input.txt"], [entry["path"] for entry in ticket_untracked])

        self.tool("stage", "--baseline", str(pre), "--snapshot", str(review))

        staged = run("git", "diff", "--cached", "--name-only", cwd=self.repo).stdout
        untracked = run(
            "git", "ls-files", "--others", "--exclude-standard", cwd=self.repo
        ).stdout
        self.assertIn("local-input.txt", staged)
        self.assertIn("local-notes.txt", untracked)
        self.assertNotIn("local-input.txt", untracked)

    def test_scope_stages_only_ticket_delta_and_preserves_unrelated_worktree_edit(self) -> None:
        readme = self.repo / "README.md"
        settings = self.repo / "settings.gradle"
        self.assertTrue(settings.is_file())
        readme.write_text(readme.read_text(encoding="utf-8") + "\nuser edit\n", encoding="utf-8")
        pre = self.capture("pre", scope_paths=["settings.gradle"])

        settings.write_text(
            settings.read_text(encoding="utf-8") + "\n// ticket edit\n",
            encoding="utf-8",
        )
        review = self.capture("review", pre)

        self.assertIn("user edit", (review / "unstaged.patch").read_text(encoding="utf-8"))
        ticket_patch = (review / "ticket-tracked.patch").read_text(encoding="utf-8")
        self.assertIn("ticket edit", ticket_patch)
        self.assertNotIn("user edit", ticket_patch)

        stage = self.tool("stage", "--baseline", str(pre), "--snapshot", str(review), check=False)
        self.assertEqual(0, stage.returncode, stage.stderr)

        self.assertIn("user edit", run("git", "diff", cwd=self.repo).stdout)
        cached = run("git", "diff", "--cached", cwd=self.repo).stdout
        self.assertIn("ticket edit", cached)
        self.assertNotIn("user edit", cached)

    def test_scope_rejects_ticket_change_outside_declared_paths(self) -> None:
        readme = self.repo / "README.md"
        settings = self.repo / "settings.gradle"
        gradle_properties = self.repo / "gradle.properties"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nuser edit\n", encoding="utf-8")
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        gradle_properties.write_text(
            gradle_properties.read_text(encoding="utf-8") + "\nticket edit\n",
            encoding="utf-8",
        )

        result = self.tool(
            "capture",
            "--output",
            str(self.root / "review"),
            "--baseline",
            str(pre),
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "ticket changed tracked paths outside its declared scope: gradle.properties",
            result.stderr,
        )

    def test_drift_reports_scope_outside_changes_for_recorded_disposition(self) -> None:
        notes = self.repo / "local-notes.txt"
        notes.write_text("user notes\n", encoding="utf-8")
        pre = self.capture("pre", scope_paths=["settings.gradle"])

        settings = self.repo / "settings.gradle"
        settings.write_text(
            settings.read_text(encoding="utf-8") + "// ticket change\n",
            encoding="utf-8",
        )
        properties = self.repo / "gradle.properties"
        properties.write_text("ticket changed this outside scope\n", encoding="utf-8")
        notes.unlink()
        (self.repo / "unexpected.txt").write_text("created outside scope\n", encoding="utf-8")

        report = self.drift("drift", pre)
        payload = json.loads((report / "report.json").read_text(encoding="utf-8"))

        self.assertEqual("confirmation_required", payload["status"])
        self.assertEqual(
            ["gradle.properties", "local-notes.txt", "unexpected.txt"],
            [change["path"] for change in payload["changes"]],
        )
        self.assertNotIn("settings.gradle", [change["path"] for change in payload["changes"]])
        self.assertEqual([], payload["strong_drift"])

    def test_reconcile_restores_accidental_tracked_and_untracked_changes(self) -> None:
        readme = self.repo / "README.md"
        readme.write_text("# Fixture repository\n\nuser edit before ticket\n", encoding="utf-8")
        notes = self.repo / "local-notes.txt"
        notes.write_text("user notes before ticket\n", encoding="utf-8")
        pre = self.capture("pre", scope_paths=["settings.gradle"])

        readme.write_text("worker overwrote tracked file\n", encoding="utf-8")
        notes.unlink()
        unexpected = self.repo / "unexpected.txt"
        unexpected.write_text("worker output\n", encoding="utf-8")

        report = self.drift("drift", pre)
        resolution = self.reconcile(
            "resolution",
            pre,
            report,
            {
                "README.md": "restore",
                "local-notes.txt": "restore",
                "unexpected.txt": "restore",
            },
        )

        self.assertEqual(
            "# Fixture repository\n\nuser edit before ticket\n",
            readme.read_text(encoding="utf-8"),
        )
        self.assertEqual("user notes before ticket\n", notes.read_text(encoding="utf-8"))
        self.assertFalse(unexpected.exists())
        self.assertEqual(
            "worker overwrote tracked file\n",
            (resolution / "quarantine/README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "worker output\n",
            (resolution / "quarantine/unexpected.txt").read_text(encoding="utf-8"),
        )
        result = json.loads((resolution / "resolution.json").read_text(encoding="utf-8"))
        self.assertEqual(
            ["README.md", "local-notes.txt", "unexpected.txt"],
            result["restored_paths"],
        )
        self.assertEqual([], result["approved_changes"])

    def test_reconcile_rejects_a_stale_drift_report_before_restoring(self) -> None:
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        properties = self.repo / "gradle.properties"
        properties.write_text("first outside change\n", encoding="utf-8")
        report = self.drift("drift", pre)
        properties.write_text("changed again while awaiting user\n", encoding="utf-8")
        decision = self.root / "decision.json"
        decision.write_text(
            json.dumps({"decisions": {"gradle.properties": "restore"}}) + "\n",
            encoding="utf-8",
        )

        result = self.tool(
            "reconcile",
            "--baseline",
            str(pre),
            "--report",
            str(report / "report.json"),
            "--decision",
            str(decision),
            "--output",
            str(self.root / "resolution"),
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("drift report is stale", result.stderr)
        self.assertEqual("changed again while awaiting user\n", properties.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "resolution").exists())

    def test_approved_outside_drift_is_preserved_but_never_staged(self) -> None:
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        settings = self.repo / "settings.gradle"
        settings.write_text(
            settings.read_text(encoding="utf-8") + "// ticket change\n",
            encoding="utf-8",
        )
        readme = self.repo / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\nintentional external edit\n",
            encoding="utf-8",
        )
        external = self.repo / "external-notes.txt"
        external.write_text("intentional untracked input\n", encoding="utf-8")

        report = self.drift("drift", pre)
        resolution = self.reconcile(
            "resolution",
            pre,
            report,
            {
                "README.md": "preserve",
                "external-notes.txt": "preserve",
            },
        )
        review = self.capture(
            "review",
            pre,
            drift_resolution=resolution / "resolution.json",
        )

        approved = json.loads(
            (review / "approved-drift.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            ["README.md", "external-notes.txt"],
            [change["path"] for change in approved],
        )
        ticket_patch = (review / "ticket-tracked.patch").read_text(encoding="utf-8")
        self.assertIn("ticket change", ticket_patch)
        self.assertNotIn("intentional external edit", ticket_patch)
        self.assertEqual([], json.loads((review / "ticket-untracked.json").read_text(encoding="utf-8")))

        self.tool("stage", "--baseline", str(pre), "--snapshot", str(review))

        cached = run("git", "diff", "--cached", cwd=self.repo).stdout
        unstaged = run("git", "diff", cwd=self.repo).stdout
        untracked = run(
            "git", "ls-files", "--others", "--exclude-standard", cwd=self.repo
        ).stdout.splitlines()
        self.assertIn("ticket change", cached)
        self.assertNotIn("intentional external edit", cached)
        self.assertIn("intentional external edit", unstaged)
        self.assertIn("external-notes.txt", untracked)

    def test_capture_rejects_when_an_approved_external_path_changes_again(self) -> None:
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        readme = self.repo / "README.md"
        readme.write_text("first intentional external edit\n", encoding="utf-8")
        report = self.drift("drift", pre)
        resolution = self.reconcile(
            "resolution",
            pre,
            report,
            {"README.md": "preserve"},
        )
        readme.write_text("changed again after approval\n", encoding="utf-8")

        result = self.tool(
            "capture",
            "--output",
            str(self.root / "review"),
            "--baseline",
            str(pre),
            "--drift-resolution",
            str(resolution / "resolution.json"),
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("classified outside-scope state changed", result.stderr)
        self.assertFalse((self.root / "review").exists())

    def test_later_accidental_change_restores_the_last_approved_state(self) -> None:
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        readme = self.repo / "README.md"
        readme.write_text("intentional external state\n", encoding="utf-8")
        first_report = self.drift("first-drift", pre)
        first_resolution = self.reconcile(
            "first-resolution",
            pre,
            first_report,
            {"README.md": "preserve"},
        )

        readme.write_text("later accidental overwrite\n", encoding="utf-8")
        second_report = self.drift(
            "second-drift",
            pre,
            first_resolution / "resolution.json",
        )
        second_resolution = self.reconcile(
            "second-resolution",
            pre,
            second_report,
            {"README.md": "restore"},
            first_resolution / "resolution.json",
        )

        self.assertEqual("intentional external state\n", readme.read_text(encoding="utf-8"))
        result = json.loads(
            (second_resolution / "resolution.json").read_text(encoding="utf-8")
        )
        self.assertEqual(["README.md"], [change["path"] for change in result["approved_changes"]])
        review = self.capture(
            "review-after-second-resolution",
            pre,
            drift_resolution=second_resolution / "resolution.json",
        )
        self.tool("verify", "--snapshot", str(review))

    def test_reconcile_rejects_a_tampered_restore_backup_before_quarantine(self) -> None:
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        readme = self.repo / "README.md"
        readme.write_text("intentional external state\n", encoding="utf-8")
        first_report = self.drift("first-drift", pre)
        first_resolution = self.reconcile(
            "first-resolution",
            pre,
            first_report,
            {"README.md": "preserve"},
        )

        readme.write_text("later accidental overwrite\n", encoding="utf-8")
        second_report = self.drift(
            "second-drift",
            pre,
            first_resolution / "resolution.json",
        )
        resolution = json.loads(
            (first_resolution / "resolution.json").read_text(encoding="utf-8")
        )
        backup = next(
            record for record in resolution["backups"] if record["path"] == "README.md"
        )
        (first_resolution / backup["blob"]).write_text(
            "tampered backup\n", encoding="utf-8"
        )

        result = self.tool(
            "reconcile",
            "--baseline",
            str(pre),
            "--report",
            str(second_report / "report.json"),
            "--decision",
            str(self.root / "missing-decision.json"),
            "--output",
            str(self.root / "second-resolution"),
            "--drift-resolution",
            str(first_resolution / "resolution.json"),
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("backup blob was modified", result.stderr)
        self.assertEqual("later accidental overwrite\n", readme.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "second-resolution").exists())

    def test_drift_rejects_a_backup_path_outside_the_resolution(self) -> None:
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        readme = self.repo / "README.md"
        readme.write_text("intentional external state\n", encoding="utf-8")
        report = self.drift("first-drift", pre)
        resolution_path = self.reconcile(
            "first-resolution",
            pre,
            report,
            {"README.md": "preserve"},
        )
        resolution_file = resolution_path / "resolution.json"
        resolution = json.loads(resolution_file.read_text(encoding="utf-8"))
        resolution["backups"][0]["blob"] = "../outside-resolution"
        resolution_file.write_text(
            json.dumps(resolution, indent=2) + "\n", encoding="utf-8"
        )

        result = self.tool(
            "drift",
            "--baseline",
            str(pre),
            "--output",
            str(self.root / "second-drift"),
            "--drift-resolution",
            str(resolution_file),
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("invalid backup blob path", result.stderr)
        self.assertFalse((self.root / "second-drift").exists())

    def test_drift_reports_head_or_index_changes_as_restart_required(self) -> None:
        pre = self.capture("pre", scope_paths=["settings.gradle"])
        readme = self.repo / "README.md"
        readme.write_text("staged outside change\n", encoding="utf-8")
        run("git", "add", "README.md", cwd=self.repo)

        report = self.drift("drift", pre)
        payload = json.loads((report / "report.json").read_text(encoding="utf-8"))

        self.assertEqual("restart_required", payload["status"])
        self.assertIn(
            "index_entries_sha256",
            [change["kind"] for change in payload["strong_drift"]],
        )

    def test_next_ticket_pre_uses_handoff_comparison_without_absorbing_drift(self) -> None:
        handoff = self.capture("handoff")
        readme = self.repo / "README.md"
        readme.write_text("intentional change between tickets\n", encoding="utf-8")
        drift_output = self.root / "handoff-drift"

        first = self.tool(
            "capture",
            "--output",
            str(self.root / "pre-two"),
            "--handoff",
            str(handoff),
            "--drift-output",
            str(drift_output),
            "--scope-path",
            "settings.gradle",
            check=False,
        )

        self.assertNotEqual(0, first.returncode)
        self.assertIn("handoff requires a drift disposition", first.stderr)
        self.assertFalse((self.root / "pre-two").exists())
        report = json.loads((drift_output / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(["README.md"], [change["path"] for change in report["changes"]])

        resolution = self.reconcile(
            "handoff-resolution",
            handoff,
            drift_output,
            {"README.md": "preserve"},
        )
        pre_two = self.capture(
            "pre-two",
            scope_paths=["settings.gradle"],
            handoff=handoff,
            drift_resolution=resolution / "resolution.json",
            drift_output=self.root / "unused-drift",
        )

        snapshot = json.loads((pre_two / "snapshot.json").read_text(encoding="utf-8"))
        self.assertIn("README.md", snapshot["tracked_unstaged_paths"])
        self.assertEqual([], snapshot["approved_drift"])
        self.assertFalse((self.root / "unused-drift").exists())

    def test_review_drift_is_rejected_before_staging(self) -> None:
        pre = self.capture("pre")
        new_file = self.repo / "ticket-created.txt"
        new_file.write_text("reviewed\n", encoding="utf-8")
        review = self.capture("review", pre)
        new_file.write_text("changed after review\n", encoding="utf-8")

        verify = self.tool("verify", "--snapshot", str(review), check=False)
        self.assertNotEqual(0, verify.returncode)
        self.assertIn("review input drifted", verify.stderr)

        stage = self.tool(
            "stage",
            "--baseline",
            str(pre),
            "--snapshot",
            str(review),
            check=False,
        )
        self.assertNotEqual(0, stage.returncode)
        self.assertIn("refusing to stage drifted review input", stage.stderr)

    def test_snapshot_artifact_tamper_is_rejected(self) -> None:
        pre = self.capture("pre")
        readme = self.repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nreviewed change\n", encoding="utf-8")
        review = self.capture("review", pre)
        (review / "unstaged.patch").write_text("tampered patch\n", encoding="utf-8")

        verify = self.tool("verify", "--snapshot", str(review), check=False)
        self.assertNotEqual(0, verify.returncode)
        self.assertIn("snapshot artifact was modified", verify.stderr)

        stage = self.tool(
            "stage",
            "--baseline",
            str(pre),
            "--snapshot",
            str(review),
            check=False,
        )
        self.assertNotEqual(0, stage.returncode)
        self.assertIn("snapshot artifact was modified", stage.stderr)

    def test_version_four_snapshot_remains_readable(self) -> None:
        snapshot_path = self.capture("legacy")
        snapshot = json.loads(
            (snapshot_path / "snapshot.json").read_text(encoding="utf-8")
        )
        snapshot["version"] = 4
        snapshot.pop("approved_drift")
        snapshot.pop("backups")
        (snapshot_path / "snapshot.json").write_text(
            json.dumps(snapshot, indent=2) + "\n",
            encoding="utf-8",
        )
        (snapshot_path / "approved-drift.json").unlink()
        (snapshot_path / "backups.json").unlink()

        result = self.tool("verify", "--snapshot", str(snapshot_path), check=False)

        self.assertEqual(0, result.returncode, result.stderr)

    def test_existing_index_lock_is_preserved(self) -> None:
        pre = self.capture("pre")
        readme = self.repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nreviewed change\n", encoding="utf-8")
        review = self.capture("review", pre)
        index_path_output = run("git", "rev-parse", "--git-path", "index", cwd=self.repo).stdout.strip()
        index_path = Path(index_path_output)
        if not index_path.is_absolute():
            index_path = self.repo / index_path
        index_lock = Path(f"{index_path}.lock")
        index_lock.write_text("owned by another process", encoding="utf-8")

        stage = self.tool(
            "stage",
            "--baseline",
            str(pre),
            "--snapshot",
            str(review),
            check=False,
        )

        self.assertNotEqual(0, stage.returncode)
        self.assertIn("locked by another process", stage.stderr)
        self.assertEqual("owned by another process", index_lock.read_text(encoding="utf-8"))

    def test_failed_preflight_does_not_change_live_index(self) -> None:
        pre = self.capture("pre")
        before = json.loads((pre / "snapshot.json").read_text(encoding="utf-8"))
        readme = self.repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\ntrailing whitespace   \n", encoding="utf-8")
        review = self.capture("review", pre)

        stage = self.tool(
            "stage",
            "--baseline",
            str(pre),
            "--snapshot",
            str(review),
            check=False,
        )
        self.assertNotEqual(0, stage.returncode)
        self.assertIn("temporary index", stage.stderr)
        index_entries = run("git", "ls-files", "--stage", "-z", cwd=self.repo).stdout.encode()
        self.assertEqual(before["index_entries_sha256"], hashlib.sha256(index_entries).hexdigest())
        self.assertIn("trailing whitespace", run("git", "diff", cwd=self.repo).stdout)

    def test_literal_pathspec_does_not_stage_preexisting_untracked_file(self) -> None:
        victim = self.repo / "victim.txt"
        victim.write_text("must remain untracked\n", encoding="utf-8")
        pre = self.capture("pre")
        special = self.repo / ":(glob)*"
        special.write_text("ticket file with pathspec magic\n", encoding="utf-8")
        review = self.capture("review", pre)

        self.tool("stage", "--baseline", str(pre), "--snapshot", str(review))

        staged = run("git", "diff", "--cached", "--name-only", cwd=self.repo).stdout.splitlines()
        untracked = run("git", "ls-files", "--others", "--exclude-standard", cwd=self.repo).stdout.splitlines()
        self.assertIn(":(glob)*", staged)
        self.assertNotIn("victim.txt", staged)
        self.assertIn("victim.txt", untracked)

    def test_allowed_paths_reject_unexpected_completion_metadata(self) -> None:
        pre = self.capture("pre")
        expected = self.repo / ".spec/example/issues/01-example.md"
        unexpected = self.repo / "unexpected.txt"
        expected.parent.mkdir(parents=True)
        expected.write_text("**Status:** done\n", encoding="utf-8")
        unexpected.write_text("not completion metadata\n", encoding="utf-8")
        review = self.capture("review", pre)

        stage = self.tool(
            "stage",
            "--baseline",
            str(pre),
            "--snapshot",
            str(review),
            "--allow-path",
            ".spec/example/issues/01-example.md",
            check=False,
        )

        self.assertNotEqual(0, stage.returncode)
        self.assertIn("outside the allowed set: unexpected.txt", stage.stderr)
        self.assertEqual("", run("git", "diff", "--cached", cwd=self.repo).stdout)

    def test_completion_metadata_allowlist_can_contain_only_the_ticket(self) -> None:
        pre = self.capture("pre")
        ticket = self.repo / ".spec/example/issues/01-example.md"
        ticket.parent.mkdir(parents=True)
        ticket.write_text(
            "**Status:** done\n\n## Completion record\n\n- Deviations: None\n",
            encoding="utf-8",
        )
        review = self.capture("review", pre)

        stage = self.tool(
            "stage",
            "--baseline",
            str(pre),
            "--snapshot",
            str(review),
            "--allow-path",
            ".spec/example/issues/01-example.md",
        )

        self.assertEqual(0, stage.returncode, stage.stderr)
        self.assertEqual(
            ".spec/example/issues/01-example.md",
            run(
                "git", "diff", "--cached", "--name-only", cwd=self.repo
            ).stdout.strip(),
        )

    def test_two_tickets_accumulate_in_cached_diff_and_keep_second_delta_isolated(self) -> None:
        readme = self.repo / "README.md"

        pre_one = self.capture("pre-one")
        readme.write_text(readme.read_text(encoding="utf-8") + "\nticket one\n", encoding="utf-8")
        (self.repo / "ticket-one.txt").write_text("one\n", encoding="utf-8")
        review_one = self.capture("review-one", pre_one)
        self.tool("stage", "--baseline", str(pre_one), "--snapshot", str(review_one))

        pre_two = self.capture("pre-two")
        readme.write_text(readme.read_text(encoding="utf-8") + "ticket two\n", encoding="utf-8")
        (self.repo / "ticket-two.txt").write_text("two\n", encoding="utf-8")
        review_two = self.capture("review-two", pre_two)
        second_patch = (review_two / "unstaged.patch").read_text(encoding="utf-8")
        self.assertIn("+ticket two", second_patch)
        self.assertNotIn("+ticket one", second_patch)
        self.tool("stage", "--baseline", str(pre_two), "--snapshot", str(review_two))

        cached = run("git", "diff", "--cached", cwd=self.repo).stdout
        cached_names = run("git", "diff", "--cached", "--name-only", cwd=self.repo).stdout
        self.assertIn("+ticket one", cached)
        self.assertIn("+ticket two", cached)
        self.assertIn("ticket-one.txt", cached_names)
        self.assertIn("ticket-two.txt", cached_names)
        self.assertEqual("", run("git", "diff", cwd=self.repo).stdout)


    def test_capture_accepts_staged_paths_within_explicit_allowed_prefix(self) -> None:
        issues = self.repo / ".spec/example/issues"
        issues.mkdir(parents=True)
        (self.repo / ".spec/example/spec.md").write_text("# spec\n", encoding="utf-8")
        (issues / "01-example.md").write_text("**Status:** ready-for-agent\n", encoding="utf-8")
        run("git", "add", ".spec/example", cwd=self.repo)

        output = self.root / "run-start"
        result = self.tool(
            "capture",
            "--output",
            str(output),
            "--allowed-staged-prefix",
            ".spec/example/",
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        staged = (output / "staged.patch").read_text(encoding="utf-8")
        self.assertIn(".spec/example/spec.md", staged)
        self.assertIn(".spec/example/issues/01-example.md", staged)

    def test_capture_rejects_staged_paths_outside_explicit_allowed_prefix(self) -> None:
        (self.repo / ".spec/example").mkdir(parents=True)
        (self.repo / ".spec/example/spec.md").write_text("# spec\n", encoding="utf-8")
        readme = self.repo / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8") + "\nstaged production code\n",
            encoding="utf-8",
        )
        run("git", "add", ".spec/example/spec.md", "README.md", cwd=self.repo)

        result = self.tool(
            "capture",
            "--output",
            str(self.root / "run-start"),
            "--allowed-staged-prefix",
            ".spec/example/",
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "index contains staged paths outside the allowed prefix: README.md",
            result.stderr,
        )
        self.assertFalse((self.root / "run-start").exists())

    def test_capture_accepts_a_gitignored_in_repository_checkpoint(self) -> None:
        gitignore = self.repo / ".gitignore"
        gitignore.write_text(".execute-tickets/\n", encoding="utf-8")
        run("git", "add", ".gitignore", cwd=self.repo)
        run(
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "commit", "--quiet", "-m", "ignore run artifacts", cwd=self.repo,
        )
        inside = self.repo / ".execute-tickets/example/run-start"

        self.tool("capture", "--output", str(inside))

        self.assertTrue((inside / "snapshot.json").is_file())
        # The checkpoint must stay invisible to Git so it can never become a candidate.
        self.assertEqual("", run("git", "status", "--short", cwd=self.repo).stdout)
        snapshot = json.loads((inside / "snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual([], snapshot["untracked"])

    def test_capture_rejects_an_unignored_in_repository_checkpoint(self) -> None:
        inside = self.repo / "run-artifacts/run-start"

        result = self.tool("capture", "--output", str(inside), check=False)

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "snapshot output inside the working tree must be ignored by Git: "
            "run-artifacts/run-start",
            result.stderr,
        )
        self.assertFalse((inside / "snapshot.json").exists())

    def test_capture_accepts_ignored_authority_and_records_content_hashes(self) -> None:
        spec, ticket = self.write_ignored_feature()
        self.assertEqual("", run("git", "status", "--short", cwd=self.repo).stdout)

        output = self.capture(
            "run-start",
            authority_paths=[
                ".spec/example/spec.md",
                ".spec/example/issues/01-example.md",
            ],
        )

        authority = json.loads((output / "authority.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [
                ".spec/example/issues/01-example.md",
                ".spec/example/spec.md",
            ],
            [entry["path"] for entry in authority],
        )
        digests = {entry["path"]: entry["sha256"] for entry in authority}
        self.assertEqual(
            hashlib.sha256(spec.read_bytes()).hexdigest(),
            digests[".spec/example/spec.md"],
        )
        self.assertEqual(
            hashlib.sha256(ticket.read_bytes()).hexdigest(),
            digests[".spec/example/issues/01-example.md"],
        )

    def test_capture_rejects_missing_authority_path(self) -> None:
        result = self.tool(
            "capture",
            "--output",
            str(self.root / "run-start"),
            "--authority-path",
            ".spec/example/spec.md",
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "authority path is not a regular file: .spec/example/spec.md",
            result.stderr,
        )
        self.assertFalse((self.root / "run-start").exists())

    def test_capture_rejects_authority_edited_during_a_ticket(self) -> None:
        spec, _ = self.write_ignored_feature()
        pre = self.capture(
            "pre",
            scope_paths=["README.md"],
            authority_paths=[".spec/example/spec.md"],
        )

        spec.write_text("# spec rewritten mid-run\n", encoding="utf-8")

        result = self.tool(
            "capture",
            "--output",
            str(self.root / "review"),
            "--baseline",
            str(pre),
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "authority content changed outside an approved transition: "
            ".spec/example/spec.md",
            result.stderr,
        )

    def test_verify_detects_authority_drift(self) -> None:
        spec, _ = self.write_ignored_feature()
        snapshot = self.capture(
            "run-start", authority_paths=[".spec/example/spec.md"]
        )
        self.tool("verify", "--snapshot", str(snapshot))

        spec.write_text("# tampered\n", encoding="utf-8")

        result = self.tool("verify", "--snapshot", str(snapshot), check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("review input drifted: authority", result.stderr)

    def test_capture_records_an_approved_authority_transition(self) -> None:
        _, ticket = self.write_ignored_feature()
        before = hashlib.sha256(ticket.read_bytes()).hexdigest()
        completion_pre = self.capture(
            "completion-pre",
            authority_paths=[".spec/example/issues/01-example.md"],
        )

        ticket.write_text(
            "**Status:** done\n\n## Completion record\n\n- Deviations: None\n",
            encoding="utf-8",
        )
        completion = self.capture(
            "completion",
            baseline=completion_pre,
            authority_transition_paths=[".spec/example/issues/01-example.md"],
        )

        snapshot = json.loads((completion / "snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [
                {
                    "path": ".spec/example/issues/01-example.md",
                    "before_sha256": before,
                    "after_sha256": hashlib.sha256(ticket.read_bytes()).hexdigest(),
                }
            ],
            snapshot["authority_transitions"],
        )
        pre_snapshot = json.loads(
            (completion_pre / "snapshot.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            pre_snapshot["index_entries_sha256"], snapshot["index_entries_sha256"]
        )

    def test_capture_records_an_approved_authority_path_set_transition(self) -> None:
        spec, ticket = self.write_ignored_feature()
        pre = self.capture(
            "path-set-pre",
            authority_paths=[
                ".spec/example/spec.md",
                ".spec/example/issues/01-example.md",
            ],
        )
        replacement = ticket.with_name("02-example.md")
        ticket.rename(replacement)

        changed = self.capture(
            "path-set-changed",
            baseline=pre,
            authority_paths=[
                ".spec/example/spec.md",
                ".spec/example/issues/02-example.md",
            ],
            authority_transition_paths=[
                ".spec/example/issues/01-example.md",
                ".spec/example/issues/02-example.md",
            ],
        )

        snapshot = json.loads((changed / "snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [
                {
                    "path": ".spec/example/issues/01-example.md",
                    "before_sha256": hashlib.sha256(
                        b"**Status:** ready-for-agent\n"
                    ).hexdigest(),
                    "after_sha256": None,
                },
                {
                    "path": ".spec/example/issues/02-example.md",
                    "before_sha256": None,
                    "after_sha256": hashlib.sha256(replacement.read_bytes()).hexdigest(),
                },
            ],
            snapshot["authority_transitions"],
        )
        self.assertEqual(
            [
                ".spec/example/issues/02-example.md",
                ".spec/example/spec.md",
            ],
            [record["path"] for record in snapshot["authority"]],
        )

    def test_capture_rejects_an_undeclared_authority_path_set_transition(self) -> None:
        self.write_ignored_feature()
        pre = self.capture(
            "path-set-pre",
            authority_paths=[".spec/example/spec.md"],
        )
        result = self.tool(
            "capture",
            "--output",
            str(self.root / "path-set-changed"),
            "--baseline",
            str(pre),
            "--authority-path",
            ".spec/example/spec.md",
            "--authority-path",
            ".spec/example/issues/01-example.md",
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "authority path set changed outside an approved transition",
            result.stderr,
        )

    def test_capture_rejects_an_inert_declared_authority_transition(self) -> None:
        self.write_ignored_feature()
        completion_pre = self.capture(
            "completion-pre",
            authority_paths=[".spec/example/issues/01-example.md"],
        )

        result = self.tool(
            "capture",
            "--output",
            str(self.root / "completion"),
            "--baseline",
            str(completion_pre),
            "--authority-transition-path",
            ".spec/example/issues/01-example.md",
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "declared authority transition did not change the file: "
            ".spec/example/issues/01-example.md",
            result.stderr,
        )

    def test_stage_refuses_to_put_a_process_document_in_the_index(self) -> None:
        issues = self.repo / ".spec/example/issues"
        issues.mkdir(parents=True)
        ticket = issues / "01-example.md"
        ticket.write_text("**Status:** ready-for-agent\n", encoding="utf-8")
        run("git", "add", ".spec/example/issues/01-example.md", cwd=self.repo)
        run(
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "commit", "--quiet", "-m", "track ticket", cwd=self.repo,
        )
        pre = self.capture(
            "pre",
            scope_paths=[".spec/example/issues/01-example.md"],
            authority_paths=[".spec/example/issues/01-example.md"],
        )

        ticket.write_text("**Status:** done\n", encoding="utf-8")
        snapshot = self.capture(
            "accepted",
            baseline=pre,
            authority_transition_paths=[".spec/example/issues/01-example.md"],
        )

        result = self.tool(
            "stage", "--baseline", str(pre), "--snapshot", str(snapshot), check=False
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "refusing to stage process-document authority: "
            ".spec/example/issues/01-example.md",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
