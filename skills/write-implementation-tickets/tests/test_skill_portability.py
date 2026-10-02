import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_TEXT = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
CONTRACT_TEXT = (SKILL_ROOT / "references/local-markdown-contract.md").read_text(
    encoding="utf-8"
)
TEMPLATE_TEXT = (SKILL_ROOT / "references/ticket-template.md").read_text(
    encoding="utf-8"
)
REVIEW_CONTRACT_PATH = SKILL_ROOT / "references/repository-alignment-review.md"
AUTHOR_REVIEW_PROTOCOL_PATH = SKILL_ROOT / "references/author-review-protocol.md"
ADMISSION_HANDOFF_PATH = SKILL_ROOT / "references/admission-and-handoff.md"
BOUNDARY_CONTRACT_PATH = (
    SKILL_ROOT / "references/ticket-boundaries-and-verification-preflight.md"
)
REALIZABILITY_CONTRACT_PATH = (
    SKILL_ROOT / "references/verification-realizability.md"
)


class SkillPortabilityTest(unittest.TestCase):
    def test_skill_uses_bundled_contract_and_optional_repository_overlays(self) -> None:
        self.assertIn("<write-implementation-tickets-skill-root>", SKILL_TEXT)
        self.assertIn("references/local-markdown-contract.md", SKILL_TEXT)
        self.assertIn("optional compatible overlays", SKILL_TEXT)
        self.assertIn("does not block authoring", SKILL_TEXT)
        self.assertIn("docs/agents/issue-tracker.md", SKILL_TEXT)
        self.assertIn("spec and ticket directory placement", SKILL_TEXT)
        self.assertIn("feature directory name", SKILL_TEXT)
        self.assertNotIn("repository-local Markdown issue tracker", SKILL_TEXT)

    def test_tracker_owns_placement_while_skill_owns_new_feature_name(self) -> None:
        normalized = " ".join(CONTRACT_TEXT.split())

        self.assertIn("placement and nesting", normalized)
        self.assertIn("`<YYYY-MM-DD>-<feature_name>`", CONTRACT_TEXT)
        self.assertIn("current local calendar date", normalized)
        self.assertIn("either `<feature>` or `<feature-slug>`", normalized)
        self.assertIn("tracker owns every surrounding path component", normalized)
        self.assertIn("reuses the existing feature directory name", normalized)
        self.assertIn("does not add, refresh, or migrate its date prefix", normalized)

    def test_template_satisfies_shared_ticket_shape(self) -> None:
        self.assertEqual(1, TEMPLATE_TEXT.count("**Status:** ready-for-agent"))
        self.assertEqual(1, TEMPLATE_TEXT.count("**Blocked by:**"))
        self.assertIn(
            "**Blocked by:** <comma-separated ticket numbers, or exact `None`>",
            TEMPLATE_TEXT,
        )
        for heading in (
            "**What to build:**",
            "## Authoritative inputs",
            "## Production owner and scope",
            "## Slice boundary",
            "## Interfaces",
            "## Behavior contract",
            "## Ordering and ownership contract",
            "## Acceptance and verification",
            "## Reusable gate inputs",
            "## Non-goals and state budget",
            "## Stop conditions",
        ):
            self.assertIn(heading, TEMPLATE_TEXT)
        self.assertNotIn("**Status:** done", TEMPLATE_TEXT)
        self.assertNotIn("Status: resolved", TEMPLATE_TEXT)
        self.assertNotIn("## Completion record", TEMPLATE_TEXT)

    def test_semantic_epics_and_unsettled_ordering_are_rejected_before_publication(self) -> None:
        self.assertTrue(BOUNDARY_CONTRACT_PATH.is_file())
        boundary = BOUNDARY_CONTRACT_PATH.read_text(encoding="utf-8")
        normalized = " ".join(boundary.split())

        for invariant in (
            "independently accept or reject",
            "semantic epic",
            "one fresh supervisor context",
            "state owner",
            "cleanup owner",
            "expand–migrate–contract",
            "Linearization point",
            "Competing operation",
            "Resource owner",
            "Deterministic interleaving",
        ):
            self.assertIn(invariant, boundary)

        self.assertIn("prototype", normalized)
        self.assertIn("wayfinder", normalized)
        self.assertIn(
            "must not become `ready-for-agent` until the decision is recorded",
            normalized,
        )
        self.assertIn(
            "references/ticket-boundaries-and-verification-preflight.md",
            SKILL_TEXT,
        )

    def test_verification_is_preflighted_and_split_between_ticket_and_feature_gates(self) -> None:
        boundary = BOUNDARY_CONTRACT_PATH.read_text(encoding="utf-8")
        normalized_skill = " ".join(SKILL_TEXT.split())
        normalized_contract = " ".join(CONTRACT_TEXT.split())

        for heading in (
            "## Baseline verification preflight",
            "## Ticket-scoped checks",
            "## Feature final gates",
        ):
            self.assertIn(heading, TEMPLATE_TEXT)
        self.assertNotIn("## Mandatory gates", TEMPLATE_TEXT)

        for classification in (
            "`pass`",
            "`intentional-fail`",
            "`implementation-dependent`",
        ):
            self.assertIn(classification, boundary)

        self.assertIn("run only by the current ticket supervisor", TEMPLATE_TEXT)
        self.assertIn("run once after all implementation tickets", TEMPLATE_TEXT)
        self.assertIn("Baseline verification preflight", normalized_contract)
        self.assertIn("Ticket-scoped checks", normalized_contract)
        self.assertIn("Feature final gates", normalized_contract)
        self.assertIn("before candidate publication", normalized_skill.lower())
        self.assertIn("exact observed exit code or interaction result", normalized_skill)

    def test_verification_witness_requires_legal_and_absence_detecting_evidence(self) -> None:
        self.assertTrue(REALIZABILITY_CONTRACT_PATH.is_file())
        contract = REALIZABILITY_CONTRACT_PATH.read_text(encoding="utf-8")
        review = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        for invariant in (
            "Production producer",
            "Legal fixture",
            "Reachability",
            "Oracle",
            "Observation",
            "Absence detector",
            "include union",
            "generated and compiled consumer",
            "upstream nonzero exit",
        ):
            self.assertIn(invariant, contract)
        self.assertIn("Verification witness:", TEMPLATE_TEXT)
        self.assertIn("Counterfactual failure probe:", TEMPLATE_TEXT)
        self.assertIn("do not sample", review)
        self.assertIn("references/verification-realizability.md", SKILL_TEXT)

    def test_permitted_discovery_requires_scope_closure_and_reviewer_replay(self) -> None:
        boundary = BOUNDARY_CONTRACT_PATH.read_text(encoding="utf-8")
        review = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        author_review = AUTHOR_REVIEW_PROTOCOL_PATH.read_text(encoding="utf-8")

        self.assertIn("## Scope closure preflight", TEMPLATE_TEXT)
        self.assertIn("## Scope closure preflight", boundary)
        self.assertIn("declared-write", boundary)
        self.assertIn("read-only", boundary)
        self.assertIn("false-positive", boundary)
        self.assertIn("0 undisposed paths", TEMPLATE_TEXT)
        self.assertIn("blocker caller-topology assessment", CONTRACT_TEXT)
        self.assertIn("reruns every permitted-discovery command", author_review)
        self.assertIn("scope_closure:", review)
        self.assertIn("undisposed", review)

    def test_non_behavioral_ticket_decisions_do_not_require_user_approval(self) -> None:
        review = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        normalized = " ".join((SKILL_TEXT + review).split())

        self.assertIn("automatic authoring correction", normalized)
        self.assertIn(
            "ticket order, granularity, blocking edges, exact write scope, or verification",
            normalized,
        )
        self.assertIn(
            "observable behavior, public interface, production ownership, or runtime state semantics",
            normalized,
        )
        self.assertNotIn(
            "Ask the user to confirm granularity, blocking edges",
            SKILL_TEXT,
        )

    def test_publication_stops_are_consolidated_into_three_cases(self) -> None:
        author_review = AUTHOR_REVIEW_PROTOCOL_PATH.read_text(encoding="utf-8")
        normalized_skill = " ".join(SKILL_TEXT.split())
        normalized_review = " ".join(author_review.split())

        for case in (
            "The ticket contract has no unique answer",
            "An effective independent admission result is unavailable",
            "Admission cannot be bound to unique, stable authority inputs",
        ):
            self.assertIn(case, normalized_skill)
        self.assertIn("exactly one of three cases", normalized_skill)
        self.assertIn("at most one independent review", normalized_review)
        self.assertIn("terminal for the exact candidate", normalized_review)
        self.assertIn("author self-review is not a fallback", normalized_review)
        self.assertIn("not a fourth stop case", normalized_skill)

    def test_existing_markdown_edits_require_bounded_rewrite_authority(self) -> None:
        boundary = BOUNDARY_CONTRACT_PATH.read_text(encoding="utf-8")
        review = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        normalized = " ".join((SKILL_TEXT + boundary + review).split())

        self.assertIn("## Documentation edit contract", TEMPLATE_TEXT)
        self.assertIn("<surgical | whole-document>", TEMPLATE_TEXT)
        self.assertIn("Preserve by default", TEMPLATE_TEXT)
        self.assertIn("Required replacement outputs", TEMPLATE_TEXT)
        self.assertIn("path in declared write scope grants permission", normalized)
        self.assertIn("positive replacement output", normalized)
        self.assertIn("mixed", normalized)
        self.assertIn("Negative scans and write permission are not preservation proof", review)

    def test_skill_progressively_loads_phase_owned_references(self) -> None:
        self.assertLess(len(SKILL_TEXT.splitlines()), 500)
        for reference in (
            "references/local-markdown-contract.md",
            "references/ticket-boundaries-and-verification-preflight.md",
            "references/ticket-template.md",
            "references/verification-realizability.md",
            "references/author-review-protocol.md",
            "references/repository-alignment-review.md",
            "references/admission-and-handoff.md",
        ):
            self.assertIn(reference, SKILL_TEXT)

        self.assertIn("Do not preload later-phase", SKILL_TEXT)
        self.assertIn("before reviewer dispatch", SKILL_TEXT)
        self.assertIn("authority bytes are stable", SKILL_TEXT)
        self.assertNotIn("scripts/admission_state.py candidate", SKILL_TEXT)
        self.assertNotIn("prior report and manifest", SKILL_TEXT)

    def test_bundled_contract_declares_shared_execution_invariants(self) -> None:
        for invariant in (
            ".spec/<feature>/",
            "<tickets-dir>/<NN>-<slug>.md",
            "**Status:** ready-for-agent",
            "`ready-for-agent`",
            "`done`",
            "**Blocked by:**",
            "## Completion record",
            "same ticket",
            "The orchestrator is the only actor",
            "without conversation history or guessing",
        ):
            self.assertIn(invariant, CONTRACT_TEXT)
        self.assertIn("`claimed` or `resolved` are outside this contract", CONTRACT_TEXT)
        self.assertNotIn("execution record", CONTRACT_TEXT.lower())
        self.assertIn("Reusable gate inputs (optional)", CONTRACT_TEXT)
        self.assertIn(
            "An `always-run` assessment means the gate reruns normally",
            " ".join(CONTRACT_TEXT.split()),
        )

    def test_reusable_gate_template_is_conservative_and_optional(self) -> None:
        self.assertIn("Reuse assessment:", TEMPLATE_TEXT)
        self.assertIn("`always-run`", TEMPLATE_TEXT)
        self.assertIn("exact tracked repository-relative file or directory", TEMPLATE_TEXT)
        self.assertIn(
            "None — reusable within the same execute-tickets run.", TEMPLATE_TEXT
        )
        self.assertIn("Remove only this Reusable gate inputs section unless", TEMPLATE_TEXT)
        self.assertIn("If completeness cannot", SKILL_TEXT)
        self.assertIn("records an `always-run` reason", SKILL_TEXT)

    def test_evidence_failure_and_runtime_contracts_are_cold_start_safe(self) -> None:
        normalized_skill = " ".join(SKILL_TEXT.split())
        normalized_contract = " ".join(CONTRACT_TEXT.split())

        self.assertIn(
            "direct repository facts, evidence-backed inferences, and unknowns",
            normalized_skill,
        )
        self.assertIn(
            "never replaces a ticket-scoped check, feature final gate",
            normalized_skill,
        )
        self.assertIn("## Failure model", TEMPLATE_TEXT)
        self.assertIn("Decisive check:", TEMPLATE_TEXT)
        self.assertIn("Command or interaction:", TEMPLATE_TEXT)
        self.assertIn("Runtime authenticity (UI/live app only):", TEMPLATE_TEXT)
        self.assertIn("Failure model (bugs and regressions)", normalized_contract)
        self.assertIn("screenshot-only state", normalized_contract)

    def test_portable_eval_files_are_bundled(self) -> None:
        evals = json.loads((SKILL_ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        self.assertEqual("write-implementation-tickets", evals["skill_name"])
        for case in evals["evals"]:
            for relative_path in case["files"]:
                path = Path(relative_path)
                self.assertFalse(path.is_absolute())
                self.assertTrue((SKILL_ROOT / path).is_file(), relative_path)

        serialized = json.dumps(evals, ensure_ascii=False)
        for workspace_term in (
            "MLLM",
            "app-role-local-inference-split",
            "remote destroy",
            "engine module",
        ):
            self.assertNotIn(workspace_term, serialized)

    def test_overlay_free_fixture_has_no_repository_agent_documents(self) -> None:
        fixture = SKILL_ROOT / "evals/fixtures/sample-repo"
        self.assertTrue((fixture / ".spec/runtime-mode-key/spec.md").is_file())
        self.assertFalse((fixture / "AGENTS.md").exists())
        self.assertFalse((fixture / "docs/agents").exists())

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

    def test_authoring_requires_a_fresh_repository_alignment_reviewer(self) -> None:
        author_review = AUTHOR_REVIEW_PROTOCOL_PATH.read_text(encoding="utf-8")
        review_bundle = f"{SKILL_TEXT}\n{author_review}"
        for invariant in (
            "sub-agents",
            'fork_turns: "none"',
            "final ticket paths",
            "live working tree",
            "repository-alignment review",
        ):
            self.assertIn(invariant, review_bundle)
        self.assertRegex(
            review_bundle, r"does not receive the authoring\s+conversation"
        )

    def test_review_gate_has_no_same_context_fallback(self) -> None:
        author_review = AUTHOR_REVIEW_PROTOCOL_PATH.read_text(encoding="utf-8")
        review_contract = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        review_bundle = f"{author_review}\n{review_contract}"
        for invariant in (
            "read-only reviewer",
            "must not edit",
            "fresh reviewer",
            "does not fall back",
            "before handoff",
            "dispatch.json",
            "platform-returned reviewer identifier",
            "reused identifier",
        ):
            self.assertIn(invariant, review_bundle)

    def test_review_contract_is_bundled_and_mandatory(self) -> None:
        self.assertTrue(REVIEW_CONTRACT_PATH.is_file())
        review_text = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        for invariant in (
            "PASS",
            "FAIL",
            "INVALIDATED",
            "final ticket files",
            "repository evidence",
            "read-only",
            "review_manifest.py",
            "dispatch.json",
            "platform-returned reviewer identifier",
        ):
            self.assertIn(invariant, review_text)

    def test_author_corrections_do_not_start_a_second_review(self) -> None:
        review_text = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        author_review = AUTHOR_REVIEW_PROTOCOL_PATH.read_text(encoding="utf-8")
        for invariant in (
            "author_correction",
            "review_drift",
            "authority_blocked",
            "material_change",
            "PASS_WITH_CORRECTIONS",
            "There are no model closure rounds",
            "closure-valid",
        ):
            self.assertIn(invariant, review_text)

        self.assertIn("at most one independent review", author_review)
        self.assertIn("deterministic correction continuity", author_review)
        self.assertIn("Do not dispatch a closure reviewer", author_review)
        self.assertNotIn(
            "Then start a different fresh reviewer", author_review
        )

    def test_delta_round_keeps_reach_with_the_reviewer(self) -> None:
        review_text = REVIEW_CONTRACT_PATH.read_text(encoding="utf-8")
        author_review = AUTHOR_REVIEW_PROTOCOL_PATH.read_text(encoding="utf-8")
        for invariant in (
            "delta_reach",
            "determines the **reach**",
            "narrowed on the author's authority",
            "two delta admissions",
        ):
            self.assertIn(invariant, review_text)

        for invariant in (
            "review_manifest.py delta",
            "delta-valid",
            "It decides the reach itself",
            "does not pre-narrow the reviewed surface",
            "two consecutive delta admissions",
            "user-authority-change",
            "never authorizes the author",
        ):
            self.assertIn(invariant, author_review)

    def test_presentation_block_separates_label_from_authority(self) -> None:
        for invariant in (
            "display_title",
            "authority_sha256",
            "makes the **whole file** authority again",
            "label, not a requirement",
            "carry no presentation block",
        ):
            self.assertIn(invariant, CONTRACT_TEXT)

        self.assertIn("no front matter or presentation", TEMPLATE_TEXT)

    def test_ready_for_agent_requires_content_addressed_admission(self) -> None:
        for invariant in (
            "independent repository-alignment review",
            "fresh read-only reviewer",
            "PASS",
            "PASS_WITH_CORRECTIONS",
            "starts no second reviewer",
            "provisional",
            "does not take effect",
            "implementation-ticket-admission.json",
            "admitted-by-review",
            "admitted-by-user",
            "user does not calculate hashes",
        ):
            self.assertIn(invariant, CONTRACT_TEXT)

        self.assertNotIn("pending-review", CONTRACT_TEXT)
        self.assertNotIn("authoring-review", TEMPLATE_TEXT)

    def test_author_owns_admission_and_preserves_failed_review(self) -> None:
        admission = ADMISSION_HANDOFF_PATH.read_text(encoding="utf-8")
        for invariant in (
            "author—not the reviewer, user, or future",
            "closed-by-clarification",
            "rejected-as-review-drift",
            "accepted-risk",
            "review remained `FAIL`",
            "scripts/admission_state.py candidate",
            "scripts/admission_state.py admit",
            "author_corrections",
        ):
            self.assertIn(invariant, admission)

    def test_review_eval_fixture_contains_a_real_stale_interface(self) -> None:
        fixture = SKILL_ROOT / "evals/fixtures/review-repo"
        ticket = (
            fixture
            / ".spec/runtime-mode-review/issues/01-parse-runtime-mode.md"
        ).read_text(encoding="utf-8")
        source = (fixture / "src/runtime_mode.py").read_text(encoding="utf-8")
        spec = (fixture / ".spec/runtime-mode-review/spec.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("src/mode.py", ticket)
        self.assertIn("RuntimeMode.parse(str)", ticket)
        self.assertIn("def from_key", source)
        self.assertIn("RuntimeMode.from_key", spec)
        self.assertFalse((fixture / "src/mode.py").exists())

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

    def test_admission_handoff_publishes_only_after_a_verified_receipt(self) -> None:
        normalized_admission = " ".join(
            ADMISSION_HANDOFF_PATH.read_text(encoding="utf-8").split()
        )
        self.assertIn("verified receipt", normalized_admission)
        self.assertIn(
            "require exact output `admitted-by-review` or `admitted-by-user`",
            normalized_admission,
        )


if __name__ == "__main__":
    unittest.main()
