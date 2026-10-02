#!/usr/bin/env python3
"""Portable-package checks for execute-tickets."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class SkillPortabilityTest(unittest.TestCase):
    def test_skill_uses_bundled_contract_and_resolved_script_root(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        run_preflight = (
            SKILL_ROOT / "references" / "run-preflight.md"
        ).read_text(encoding="utf-8")

        self.assertIn("references/local-markdown-contract.md", skill)
        self.assertIn("references/run-preflight.md", skill)
        self.assertIn("references/supervisor-protocol.md", skill)
        self.assertIn("references/final-gate.md", skill)
        self.assertIn("references/review-mechanics.md", skill)
        self.assertIn("references/review-policy.md", skill)
        self.assertIn("references/reusable-gates.md", skill)
        self.assertIn("references/admission-preflight.md", skill)
        self.assertIn("references/run-metrics.md", skill)
        self.assertIn("references/implementation-delegation.md", skill)
        self.assertIn("references/working-tree-drift.md", skill)
        self.assertIn("<execute-tickets-skill-root>/scripts/review_state.py", skill)
        self.assertIn("<execute-tickets-skill-root>/scripts/ticket_state.py", skill)
        self.assertIn("scripts/admission_state.py verify", (
            SKILL_ROOT / "references" / "admission-preflight.md"
        ).read_text(encoding="utf-8"))
        self.assertIn("<execute-tickets-skill-root>/scripts/gate_state.py", (
            SKILL_ROOT / "references" / "reusable-gates.md"
        ).read_text(encoding="utf-8"))
        metrics = (SKILL_ROOT / "references" / "run-metrics.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("<execute-tickets-skill-root>/scripts/metrics_state.py", metrics)
        self.assertIn("quality_proxy: false", metrics)
        self.assertIn("--record-file", skill)
        self.assertIn("--receipt", skill)
        self.assertIn("--receipt", run_preflight)
        combined_protocol = skill + run_preflight
        self.assertNotIn("--require-index-path", combined_protocol)
        self.assertNotIn("--allowed-staged-prefix", combined_protocol)
        self.assertNotIn("--authority-path", combined_protocol)
        self.assertNotIn("ticket_ready_for_acceptance", combined_protocol)
        self.assertNotIn(".spec/<feature>/execution-state.md", combined_protocol)
        self.assertNotIn(".spec/<feature>/execution/<ticket>", combined_protocol)
        self.assertNotIn(".agents/skills/execute-tickets", combined_protocol)

    def test_protected_drift_uses_conservative_automatic_dispositions(self) -> None:
        drift = (
            SKILL_ROOT / "references" / "working-tree-drift.md"
        ).read_text(encoding="utf-8")
        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(drift.split())

        self.assertIn("confirmation_required", drift)
        self.assertIn("restart_required", drift)
        self.assertIn("`restore`", drift)
        self.assertIn("`preserve`", drift)
        self.assertIn("--drift-resolution", drift)
        self.assertIn("completion/handoff/", drift)
        self.assertIn("there is no extra full snapshot", normalized)
        self.assertIn("remain in the working tree and out of the index", normalized)
        self.assertIn("workflow-attributable accidental write", normalized)
        self.assertIn("defaults to `preserve`", normalized)
        self.assertIn("Do not investigate provenance as a precondition", normalized)
        self.assertIn("Provenance ambiguity by itself is never", normalized)
        self.assertIn("Only ask the user", normalized)
        self.assertIn("drift_detected", supervisor)

    def test_skill_progressively_loads_phase_owned_references(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertLess(len(skill.splitlines()), 500)
        self.assertIn("Do not preload later-phase", skill)
        self.assertIn("Before a new-run snapshot or resume validation", skill)
        self.assertIn("Before starting each fresh ticket supervisor", skill)
        self.assertIn("Only after every implementation ticket is staged", skill)
        self.assertNotIn("## Execution mode routing", skill)
        self.assertNotIn("Start the one integration discovery review", skill)

        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        final_gate = (
            SKILL_ROOT / "references" / "final-gate.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Execution mode routing", supervisor)
        self.assertIn("integration discovery review", final_gate)

    def test_implementation_delegation_is_bounded_and_supervisor_owned(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        delegation = (
            SKILL_ROOT / "references" / "implementation-delegation.md"
        ).read_text(encoding="utf-8")
        mechanics = (
            SKILL_ROOT / "references" / "review-mechanics.md"
        ).read_text(encoding="utf-8")
        policy = (
            SKILL_ROOT / "references" / "review-policy.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(delegation.split())
        normalized_mechanics = " ".join(mechanics.split())

        self.assertNotIn(
            "do not add a separate implementation worker beneath it",
            skill,
        )
        self.assertIn("Delegate only after `scope_accepted`", delegation)
        self.assertIn("one complete vertical slice", normalized)
        self.assertIn("Default to one write-capable worker", delegation)
        self.assertIn("at most two workers", delegation)
        self.assertIn(
            "worker's exact package scope but inside the broader accepted ticket scope blocks the ticket",
            normalized,
        )
        self.assertIn("Only the supervisor emits `implementation_ready`", delegation)
        self.assertIn(
            "do not dispatch an implementation worker after review begins",
            normalized_mechanics,
        )
        self.assertIn("The ticket supervisor performs every actionable", policy)

    def test_ticket_admission_rejects_semantic_epics_and_unsettled_ordering(self) -> None:
        admission = (
            SKILL_ROOT / "references" / "admission-preflight.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(admission.split())

        for invariant in (
            "semantic epic",
            "one fresh supervisor context",
            "state owner",
            "cleanup owner",
            "Linearization point",
            "Competing operation",
            "Resource owner",
            "Deterministic interleaving",
        ):
            self.assertIn(invariant, admission)
        self.assertIn("independent-rejection test", normalized)
        self.assertIn("blocks before implementation", normalized)
        self.assertIn("applies that exact split through execution authority repair", normalized)
        self.assertNotIn("return the ticket to authoring", normalized)

    def test_execution_revalidates_preflight_and_keeps_gate_tiers_distinct(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        final_gate = (
            SKILL_ROOT / "references" / "final-gate.md"
        ).read_text(encoding="utf-8")
        admission = (
            SKILL_ROOT / "references" / "admission-preflight.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "local-markdown-contract.md"
        ).read_text(encoding="utf-8")
        normalized_skill = " ".join(skill.split())
        normalized_admission = " ".join(admission.split())
        normalized_contract = " ".join(contract.split())

        for classification in (
            "`pass`",
            "`intentional-fail`",
            "`implementation-dependent`",
        ):
            self.assertIn(classification, admission)
        self.assertIn("Ticket-scoped checks", normalized_contract)
        self.assertIn("Feature final gates", normalized_contract)
        self.assertIn("Before `scope_ready`", normalized_admission)
        self.assertIn("run only the ticket-scoped checks", normalized_skill)
        self.assertIn(
            "run each uniquely owned feature final gate once",
            " ".join(final_gate.split()),
        )
        self.assertIn("duplicate gate id", normalized_admission)
        self.assertIn("completed blocker", normalized_admission)

    def test_execution_replays_scope_closure_after_blockers(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        admission = (
            SKILL_ROOT / "references" / "admission-preflight.md"
        ).read_text(encoding="utf-8")
        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "local-markdown-contract.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join((skill + admission + supervisor + contract).split())

        self.assertIn("scope_closure_trace:", supervisor)
        self.assertIn("After all blockers complete", skill)
        self.assertIn("declared-write", normalized)
        self.assertIn("permitted-write", normalized)
        self.assertIn("read-only", normalized)
        self.assertIn("false-positive", normalized)
        self.assertIn("0 undisposed paths", normalized)
        self.assertIn("without permitted discovery", normalized)

    def test_first_ticket_pre_compares_the_run_start_snapshot(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        run_preflight = (
            SKILL_ROOT / "references" / "run-preflight.md"
        ).read_text(encoding="utf-8")
        drift = (
            SKILL_ROOT / "references" / "working-tree-drift.md"
        ).read_text(encoding="utf-8")

        self.assertIn("--handoff .execute-tickets/<feature>/run-start", skill)
        self.assertIn("first ticket's `--handoff`", run_preflight)
        self.assertIn("For the first ticket", drift)
        self.assertIn("silently absorbed into the first `pre`", drift)

    def test_execution_requires_admission_and_revalidates_verification_witnesses(self) -> None:
        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        admission = (
            SKILL_ROOT / "references" / "admission-preflight.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "local-markdown-contract.md"
        ).read_text(encoding="utf-8")
        for invariant in (
            "implementation-ticket-admission.json",
            "admitted-by-review",
            "admitted-by-user",
            "complete ticket path set",
            "Production producer",
            "Legal fixture",
            "Reachability",
            "Oracle",
            "Observation",
            "Absence detector",
            "unrealizable acceptance contract",
        ):
            self.assertIn(invariant, admission)
        self.assertIn("verification_witness_trace:", supervisor)
        self.assertIn("admission_basis:", supervisor)
        self.assertIn("checkpointed", contract)

    def test_markdown_deletions_are_audited_and_passed_to_existing_reviewers(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        mechanics = (
            SKILL_ROOT / "references" / "review-mechanics.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join((skill + supervisor + mechanics).split())

        self.assertIn("document_deletion_audit:", supervisor)
        self.assertIn("document-deletion-audit.md", normalized)
        self.assertIn("heading section", normalized)
        self.assertIn("fenced code block", normalized)
        self.assertIn("`replaced` means", supervisor)
        self.assertIn("`superseded` means", supervisor)
        self.assertIn("any `unexplained` unit blocks `implementation_ready`", normalized)
        self.assertIn("Standards reviewer brief", normalized)
        self.assertIn("without modifying the Standards reviewer implementation", mechanics)
        self.assertIn("Audit drift invalidates both reports", mechanics)
        self.assertIn("complete patch", mechanics)
        self.assertIn("positive replacement output", mechanics)
        self.assertIn("Do not infer failure from line count", normalized)

    def test_bundled_contract_owns_done_transition_without_docs_agents(self) -> None:
        contract = (
            SKILL_ROOT / "references" / "local-markdown-contract.md"
        ).read_text(encoding="utf-8")

        self.assertIn("no `docs/agents/` directory", contract)
        self.assertIn("`ready-for-agent -> done`", contract)
        self.assertIn("The orchestrator is the only actor", contract)
        self.assertIn("## Completion record", contract)
        self.assertIn("same ticket", contract)
        self.assertNotIn("execution record", contract.lower())
        normalized_contract = " ".join(contract.split())
        self.assertIn(
            "must match the content hashes recorded in the admission receipt",
            normalized_contract,
        )
        self.assertIn("never newly stages them", normalized_contract)
        self.assertIn("already staged by the user at run-start", normalized_contract)
        self.assertNotIn("must never enter the accepted baseline", normalized_contract)
        self.assertNotIn("must match the Git index byte-for-byte", normalized_contract)
        self.assertIn("A conflict stops before Git state changes.", (
            SKILL_ROOT / "references" / "run-preflight.md"
        ).read_text(encoding="utf-8"))

    def test_review_policy_bounds_convergence_and_preserves_micro_safety(self) -> None:
        policy = (
            SKILL_ROOT / "references" / "review-policy.md"
        ).read_text(encoding="utf-8")
        normalized_policy = " ".join(policy.split())

        self.assertIn("one discovery review", policy)
        self.assertIn("one closure review", policy)
        self.assertIn("at most one regression closure", policy)
        self.assertIn("at most three ticket-review rounds", normalized_policy)
        self.assertNotIn("`soft_limit: 3`", policy)
        self.assertNotIn("`hard_limit: 5`", policy)
        self.assertIn("`review-drift` is not an authority class", policy)
        self.assertIn("There are zero reviewer rounds", policy)
        self.assertIn("at most three cumulative feature-review rounds", policy)
        self.assertIn(
            "A new run-start does not reset this feature-level budget",
            normalized_policy,
        )
        self.assertIn("there is no `final_closure` fourth phase", normalized_policy)
        self.assertIn(
            "Continue other frontier tickets by default",
            " ".join(policy.split()),
        )

    def test_final_review_is_integration_oriented_without_hiding_the_full_patch(self) -> None:
        final_gate = (
            SKILL_ROOT / "references" / "final-gate.md"
        ).read_text(encoding="utf-8")
        mechanics = (
            SKILL_ROOT / "references" / "review-mechanics.md"
        ).read_text(encoding="utf-8")
        normalized_final_gate = " ".join(final_gate.split())
        normalized_mechanics = " ".join(mechanics.split())

        for boundary in (
            "Consumes/Produces",
            "shared state",
            "cleanup ownership",
            "linearization",
            "public API",
            "wire compatibility",
            "delivery closure",
        ):
            self.assertIn(boundary, mechanics)
        self.assertIn("complete staged.patch remains available", normalized_mechanics)
        self.assertIn("ticket acceptance reports", normalized_mechanics)
        self.assertIn("integration-review-index.md", mechanics)
        self.assertIn("## Ticket `<number>`", mechanics)
        self.assertIn("First-pass inputs", mechanics)
        self.assertIn("On-demand evidence paths", mechanics)
        self.assertIn("must not linearly read the complete patch", normalized_mechanics)
        self.assertIn("mandatory first-pass input", normalized_final_gate)
        self.assertIn("not behavior authority", normalized_mechanics)
        self.assertIn("Any final repair invalidates the frozen index", mechanics)
        self.assertIn("freeze a new index SHA-256", normalized_final_gate)
        self.assertIn("integration discovery review", normalized_final_gate)
        self.assertIn("must not re-audit byte-identical ticket-local", normalized_mechanics)
        self.assertIn("new P0/P1", normalized_mechanics)

    def test_review_and_blocker_inputs_are_context_bounded(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        mechanics = (
            SKILL_ROOT / "references" / "review-mechanics.md"
        ).read_text(encoding="utf-8")
        run_preflight = (
            SKILL_ROOT / "references" / "run-preflight.md"
        ).read_text(encoding="utf-8")
        normalized_supervisor = " ".join(supervisor.split())
        normalized_mechanics = " ".join(mechanics.split())

        self.assertIn("direct completed blockers", skill)
        self.assertIn("only the verbatim `Produces` rows", normalized_supervisor)
        self.assertIn("Do not include transitive blockers", normalized_supervisor)
        self.assertIn(
            "must not read the complete blocker ticket by default",
            normalized_supervisor,
        )
        self.assertIn("mismatch fallback", " ".join(run_preflight.split()))
        self.assertIn("incrementally writes", mechanics)
        self.assertIn("does not reconstruct accepted rows", normalized_mechanics)
        self.assertIn("orchestrator-only integrity artifact bodies", normalized_mechanics)
        self.assertIn("Reviewers must not read `unstaged.patch`", normalized_mechanics)
        self.assertIn("reviewer content artifact paths", normalized_mechanics)
        self.assertIn("never orchestrator-only integrity artifact bodies", skill)
        self.assertIn("integration-review index", skill)

    def test_metrics_are_diagnostic_and_cannot_block_or_pass_acceptance(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        metrics = (SKILL_ROOT / "references" / "run-metrics.md").read_text(
            encoding="utf-8"
        )
        normalized_skill = " ".join(skill.split())
        normalized_metrics = " ".join(metrics.split())

        self.assertIn("quality_proxy: false", metrics)
        self.assertIn("statistics never affect execution", normalized_metrics)
        self.assertNotIn("metrics_state.py validate", skill)
        self.assertIn(
            "accepts only `<artifact-root>/<feature>/run-metrics.jsonl`",
            normalized_metrics,
        )
        self.assertIn("does not block implementation", normalized_metrics)
        self.assertIn("report the metrics gap", normalized_metrics)
        self.assertNotIn(
            "A required metrics transition cannot be appended",
            normalized_skill,
        )
        self.assertIn("do not soften the blocker", normalized_skill)

    def test_scope_owns_existing_worktree_content_and_verifier_repairs_are_autonomous(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "local-markdown-contract.md"
        ).read_text(encoding="utf-8")
        policy = (
            SKILL_ROOT / "references" / "review-policy.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "Ticket scope, not pre-existing worktree cleanliness, defines",
            skill,
        )
        self.assertNotIn(
            "It stops before implementation when one exact scope path is already",
            skill,
        )
        self.assertIn(
            "A failing ticket-scoped check blocks acceptance, not repair.",
            skill,
        )
        self.assertNotIn("- A hard gate in the ticket or execution plan fails.", skill)
        self.assertIn("verification-only contract repair", contract)
        self.assertIn("--authority-transition-path", contract)
        self.assertIn(
            "A verifier defect is not an authority conflict when",
            policy,
        )

    def test_non_behavioral_authority_defects_are_repaired_inside_execute(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        admission = (
            SKILL_ROOT / "references" / "admission-preflight.md"
        ).read_text(encoding="utf-8")
        policy = (
            SKILL_ROOT / "references" / "review-policy.md"
        ).read_text(encoding="utf-8")
        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join((skill + admission + policy + supervisor).split())

        self.assertIn("execution authority repair", normalized)
        self.assertIn("run-start receipt unchanged", normalized)
        self.assertIn("same supervisor", normalized)
        self.assertIn("ticket order", normalized)
        self.assertIn("test-only scope", normalized)
        self.assertIn("resume the same ticket", normalized)
        self.assertIn("blocker_class: <none | authority_backed_ticket_defect", normalized)
        self.assertIn("Every non-`blocked` envelope uses `blocker_class: none`", normalized)
        self.assertIn(
            "observable behavior, public interface, production ownership, or runtime state semantics",
            normalized,
        )
        self.assertNotIn("fresh repository-alignment review", normalized)
        self.assertNotIn("automatic authoring repair", normalized)

    def test_pause_block_and_stop_conditions_are_consolidated_into_six_cases(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())

        self.assertIn(
            "Route every pause, single-ticket block, or whole-run stop through these six cases",
            normalized,
        )
        for case in (
            "A ticket-scope-outside change can affect the current ticket",
            "The ticket contract cannot be executed uniquely and safely",
            "Implementation checks or assurance review cannot converge",
            "Ticket-declared `adb` real-device evidence is unavailable",
            "The execution baseline or recovery evidence cannot be trusted",
            "The next action exceeds current ticket authority",
        ):
            self.assertIn(case, normalized)
        self.assertIn("not additional stop cases and not permission questions", normalized)

    def test_decisive_checks_and_real_runtime_evidence_do_not_weaken_gates(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        supervisor = (
            SKILL_ROOT / "references" / "supervisor-protocol.md"
        ).read_text(encoding="utf-8")
        contract = (
            SKILL_ROOT / "references" / "local-markdown-contract.md"
        ).read_text(encoding="utf-8")
        normalized_skill = " ".join((skill + supervisor).split())
        normalized_contract = " ".join(contract.split())

        self.assertIn("runtime_observations:", supervisor)
        self.assertIn("directly observed facts, evidence-backed inferences", skill)
        self.assertIn(
            "never replaces a ticket-scoped check, feature final gate",
            normalized_skill,
        )
        self.assertIn("It does not add a second symptom workaround", normalized_skill)
        self.assertIn("screenshot-only state", normalized_skill)
        self.assertIn("adb devices -l", normalized_skill)
        self.assertIn("require no second permission prompt", normalized_skill)
        self.assertIn("no eligible physical device is in state `device`", normalized_skill)
        self.assertIn("may install, replace, or uninstall the exact APK/package", normalized_skill)
        self.assertIn("normal removal of that package's data", normalized_skill)
        self.assertIn("does not authorize operations on unrelated applications", normalized_skill)
        self.assertIn("Failure model (bugs and regressions)", normalized_contract)
        self.assertIn("target runtime also names the interaction path", normalized_contract)

    def test_protocol_layer_carries_no_host_repository_scoped_rule(self) -> None:
        # A rule scoped to one host repository belongs to that repository's own
        # instructions. The leak this guards read "For this repository, ...".
        documents = [
            SKILL_ROOT / "SKILL.md",
            *sorted((SKILL_ROOT / "references").glob("*.md")),
        ]
        self.assertGreater(len(documents), 1, documents)
        for document in documents:
            with self.subTest(document=document.name):
                normalized = " ".join(document.read_text(encoding="utf-8").split()).lower()
                for phrase in ("this repo", "our repo"):
                    found = normalized.find(phrase)
                    excerpt = normalized[max(0, found - 70) : found + 70]
                    self.assertEqual(-1, found, f"{document.name}: ...{excerpt}...")

    def test_bundled_scripts_are_callable_outside_a_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for script in (
                "admission_state.py",
                "gate_state.py",
                "metrics_state.py",
                "review_budget.py",
                "review_state.py",
                "ticket_state.py",
            ):
                result = subprocess.run(
                    [sys.executable, str(SKILL_ROOT / "scripts" / script), "--help"],
                    cwd=directory,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)

    def test_protocol_layer_carries_no_monitoring_integration(self) -> None:
        # Monitoring is withdrawn from this Skill until the monitor package's own
        # design settles. Until then no protocol document may resolve a monitor,
        # append an Observation event, or carry monitoring-warning semantics.
        self.assertFalse((SKILL_ROOT / "references/monitoring-appends.md").exists())
        self.assertFalse((SKILL_ROOT / "references/monitoring-policy.md").exists())
        documents = [
            SKILL_ROOT / "SKILL.md",
            *sorted((SKILL_ROOT / "references").glob("*.md")),
        ]
        self.assertGreater(len(documents), 1, documents)
        for document in documents:
            with self.subTest(document=document.name):
                normalized = " ".join(document.read_text(encoding="utf-8").split())
                for form in (
                    "<monitor>",
                    "spec_monitor.py",
                    "start-monitor-spec",
                    "monitoring warning",
                    "Observation append",
                    "monitoring-appends.md",
                    "monitoring-policy.md",
                    "append-contract.md",
                ):
                    found = normalized.find(form)
                    excerpt = normalized[max(0, found - 70) : found + 70]
                    self.assertEqual(-1, found, f"{document.name}: ...{excerpt}...")

    def test_authority_byte_boundary_matches_the_authoring_skill(self) -> None:
        bundled = SKILL_ROOT / "scripts" / "manifest_lib.py"
        bundled_tests = SKILL_ROOT / "tests" / "test_manifest_lib.py"
        self.assertTrue(bundled.is_file())
        self.assertTrue(bundled_tests.is_file())
        admission = (SKILL_ROOT / "scripts" / "admission_state.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "from manifest_lib import authority_sha256, record_authority", admission
        )
        preflight = (SKILL_ROOT / "references" / "admission-preflight.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("authority body", preflight)
        self.assertIn("presentation-only spec rename", preflight)

        sibling_root = SKILL_ROOT.parent / "write-implementation-tickets"
        if not (sibling_root / "scripts" / "manifest_lib.py").is_file():
            self.skipTest("authoring skill is not installed beside this one")
        self.assertEqual(
            (sibling_root / "scripts" / "manifest_lib.py").read_bytes(),
            bundled.read_bytes(),
            "a divergent authority boundary would admit bytes execution refuses",
        )
        self.assertEqual(
            (sibling_root / "tests" / "test_manifest_lib.py").read_bytes(),
            bundled_tests.read_bytes(),
            "both skills must hold the boundary to the same refused block shapes",
        )


if __name__ == "__main__":
    unittest.main()
