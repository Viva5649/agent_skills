# Final gate protocol

Read this file in full only after every implementation ticket has been staged,
or when an explicitly validation-only ticket owns the same final gate. It owns
feature-level gate execution, integration review, final repairs, and the final
completion report. Do not load it during ordinary ticket implementation.

## Final gate

For a repository set, final snapshots and completion evidence bind every member
under `multi-repository.md`; reviewers receive separate per-member staged
patches. Gate commands, working directories, inputs, and expected results still
come only from spec/ticket authority. The orchestrator must not derive additional
acceptance requirements from submodule or build relationships.

After all implementation tickets are staged, use an explicitly validation-only ticket's supervisor when that ticket owns the final gate. Otherwise start one fresh read-only final-gate supervisor; do not accumulate the final build and cross-ticket review in the orchestrator context.

1. Capture a final state snapshot and build the authoritative gate inventory.
   Reject a duplicate gate id whose owner, command, expected result or evidence
   conditions differ. Apply bounded expensive-run preparation under
   `supervisor-protocol.md`. Run necessary builds and explicit prerequisite gates
   in their declared order. Consume the critical cross-ticket witness from its
   named owner, or have that owner run the smallest real producer-to-public-
   consumer proof once dependencies are ready. Count applicable results for their
   exact components; do not repeat them merely on entering final acceptance.
   For release/published-consumer gates, include the early release witness under
   `supervisor-protocol.md` here. Preserve explicit build prerequisites and
   retain the required artifacts before temporary-output cleanup.
2. The final-gate supervisor traces the cumulative implementation delta and
   accepted contracts to affected maintained documentation and related entry
   points. Start with the tickets' discovery inventory and completed updates;
   inspect changed contracts, newly composed boundaries and missing dispositions,
   including unchanged documents and paths absent from tickets. Reuse valid
   document checks instead of repeating discovery over unchanged scope. Check
   current API/error/default/example facts, enduring constraints, usable build
   and verification instructions, and affected references under repository
   policy. Reconcile record moves with still-valid responsibilities. Limit this
   to actual feature effects; do not require a fixed document set or unrelated
   repository cleanup. Record required updates or an evidence-backed no-impact
   reason in the owning tickets' existing Completion/deviations rows. Feed
   omissions into the same integration finding set and repair flow below.
   Complete and verify the incrementally retained compact
   `.execute-tickets/<feature>/integration-review-index.md` under
   `review-mechanics.md`. Add the snapshot, available results and pending gate
   IDs/owners, then freeze its SHA-256. This is the mandatory first-pass input for
   the assurance coverage decision below, before the remaining full matrix.
   When coverage cannot be reused, give fresh Standards and Spec reviewers the verified index, spec and authority;
   supply the immutable cumulative `staged.patch`, accepted reports, per-path
   hashes and gate evidence as on-demand paths. Review exact cross-ticket
   contracts, shared owners, lifecycle, public API/wire and delivery boundaries,
   not every already accepted ticket-local line. The capture produced the patch
   using `git diff --cached --binary --no-ext-diff --no-textconv --no-color`.
   Pending post-review gates remain unproved acceptance; their scheduling alone
   is not a code-review finding. Broken verification or missing prerequisites are.
3. Validate the selected `final_review` or `final_assurance` event with
   `review_budget.py` under `review-budget.md`. After both axes finish, or ticket
   coverage is verified, run the optional CE review below once, verify index/report hashes and HEAD/index/tree/
   snapshot identities, and freeze the combined finding set. Record the actual
   result, including CE blockers; reused coverage is not a new reviewer PASS.
   Batch accepted findings by original
   owner and compatible scope; the orchestrator routes serial repairs with fresh
   `<ticket>/final-fix-N/pre`, never the original ticket baseline. Complete focused
   checks, targeted assurance and necessary cumulative closure under
   `review-policy.md` before the full matrix. For closure, continue the original
   per-axis reviewers unless unavailable or lacking review context; never repeat
   integration or CE discovery. Update affected index rows and freeze a new index
   SHA-256 after each accepted repair. If only full gate results are missing from
   otherwise eligible single-owner closeout, proceed to those gates instead of
   dispatching a redundant cumulative review. Feature acceptance remains pending.
4. On the reviewed stable candidate, run each uniquely owned feature final gate once,
   completing the remaining components of the inventory. Apply
   `reusable-gates.md` after repairs: exact helper `reusable` permits deterministic
   reuse; declared runtime conditions govern PASS retention or raw reevaluation.
   Otherwise execute the affected gate. Fresh UI/browser/desktop/device/live-app
   requirements need actual interactions and fresh `runtime_observations`; cached
   results or screenshots cannot replace them. For an authorized `adb` gate,
   detect and use an eligible physical device directly under
   `supervisor-protocol.md`; block only when no eligible device is in state
   `device`, without requesting execution permission again. Record every actual
   execution or verified reuse as a separate existing `gate` event with reason.
5. If acceptance fails, establish product, verifier, orchestration or environment/
   evidence cause under `reusable-gates.md`. Preserve FAIL and run only the checks
   needed for attribution and repair while known blockers remain. A production,
   test or build repair needs current assurance even after early review PASS.
   Freeze the new authority-backed failure IDs and original owner in the existing
   index, then use `review-policy.md` and `review-budget.md` for targeted repair
   and bounded closure. Do not relabel early PASS as FAIL, restart discovery or
   extend budgets. Once the repaired candidate has current assurance, execute or
   validly retain affected acceptance evidence; incomplete evidence blocks completion.
6. After required gates have valid outcomes, the final-gate supervisor reconciles
   tested artifacts, the staged candidate and affected documents' current facts.
   Unchanged document bytes do not prove that "unverified" or "awaiting acceptance"
   still applies. Recheck step 2's documentation outcomes and gate-dependent
   handoffs against the final candidate and actual results. The orchestrator
   routes surgical updates to the document owner or the affected behavior's
   repair supervisor under the documentation repair rule below; distinguish
   proved, deferred and historical conditions. Batch compatible gate-result
   updates for the same owner in one repair after the needed results arrive;
   contract/instruction updates should already be complete. Pure factual updates
   use their applicable assurance, checks and protected staging, without repeating
   unaffected device gates or cumulative code review. Update affected index rows
   and snapshot hashes. Required documentation still missing blocks completion.
7. Apply bounded final closeout under `review-policy.md`: verified all-micro
   inspection, eligible single-owner targeted closeout, or required cumulative
   closure within the existing three-round budget. Code review and gate evidence
   must both remain valid. Preserve actual reports and dispositions; an exhausted
   budget with unresolved findings stops with evidence, never another Final-N cycle.

A final repair batch follows `supervisor-protocol.md` for the order between
bounded intermediate diagnosis and stable-candidate acceptance: intermediate
edits do not trigger the whole gate set, a localized selector PASS is not a gate
PASS, and the candidate's required gates and closure run under the original
`always-run` / `reusable` and fresh-runtime contract only once the candidate is
ready for acceptance. While any known issue still blocks that round's full
acceptance, its existing failure evidence stands and the suite is not
re-triggered on an unrelated sub-fix, as defined in `supervisor-protocol.md`. Explicit prerequisite gates keep their declared order.

## Reuse ticket assurance when integration is already covered

The final-gate supervisor checks coverage before dispatching the integration
discovery review. Reuse is allowed only when all of these facts are proved:

- The run has exactly one implementation ticket and no other ticket activity.
  Its accepted Standards/Spec reports, or eligible micro inspection, are valid
  and every finding has a verified disposition.
- The final staged candidate matches that accepted candidate, including any
  accepted micro repairs. The snapshot, per-path hashes, authority and executable
  verification plan still match the evidence used for acceptance.
- The complete cumulative `staged.patch`, including the user-staged run-start
  baseline, is covered by the retained assurance. An empty baseline needs no
  separate proof; a nonempty baseline needs explicit bound coverage. Being
  unchanged does not make an unreviewed baseline reviewed.
- The retained evidence covers every affected owner, lifecycle, public API/wire,
  build and delivery boundary. There is no newly composed or uncovered boundary,
  unresolved contract judgment or documentation omission from step 2.

Record the coverage decision, accepted snapshot/report hashes, baseline coverage
and any uncovered boundary in the existing integration index; freeze its hash.
The orchestrator verifies these identities without repeating semantic review.
Missing evidence takes the normal integration review route. One ticket or a
zero-finding report alone is insufficient. Do not start another review to prove
that the previous review can be reused.

Eligible reuse omits only the initial integration Standards/Spec dispatch. CE
still runs once when available, all required gates remain, and documentation
reconciliation still applies. Record `final_assurance/integration_review/ticket_coverage`
with `reused` when coverage and CE leave no blocker, `fail` for
actionable CE findings, or `blocked` for incomplete required evidence. Record no
`final_review/integration_risk` event for this route. The reuse event consumes
the same discovery slot and anchors later CE/runtime repairs under
`review-budget.md`; it cannot create another discovery opportunity.

On resume, verify the retained coverage decision and its bound candidate. Later
repairs require their own assurance; they do not inherit the initial reuse claim.
Use the same targeted repair, micro inspection and bounded closure rules as a
reviewed discovery. If cumulative closure is required without original final
reviewers, dispatch fresh reviewers only for the frozen findings and repair
boundaries, with the retained ticket reports; do not reopen discovery.

## Documentation repair scope

Documentation reconciliation is required even when the graph has no dedicated
documentation ticket. The final-gate supervisor remains read-only. For each
omission caused by the accepted feature delta, it names the affected behavior's
original owning ticket and records the exact document/reference paths, sections,
stable authority, required output and checks in that ticket's existing
integration-review-index Completion/deviations row. Include the bounded edit
contract and preservation/replacement responsibilities for existing Markdown.

An unfinished ticket's missing scope uses execution authority repair. For a
completed ticket, the orchestrator validates and freezes this repair entry with
the index hash, accepts only those documentation paths as the final-fix scope,
and captures a fresh `<ticket>/final-fix-N/pre` before the repair supervisor
edits. This is a documentation-only scope trace for that final repair, not a
rewrite of the completed ticket, its admission or historical checkpoint. The
entry must cite existing accepted behavior, this workflow's documentation
completion requirement and any applicable repository policy. It cannot
authorize new product, interface or architecture decisions, unrelated cleanup,
or overwriting protected work. Ambiguous decisions follow the existing
material-decision boundary.

Use the same scope assessment, surgical edit/deletion audit, assurance, protected
staging, snapshot verification and review budget as other final repairs. Retain
repair evidence and current hashes in the existing index without rewriting prior
PASS/FAIL evidence. Merely listing a document or passing a code gate does not
prove that the required content and references were updated.

## Optional feature review with `ce-code-review`

The final-gate supervisor resolves `ce-code-review` from the session skill
catalog or configured skill locations. If absent, record an unavailable-skill
skip in the existing final-review evidence and continue. If present, read its
resolved `SKILL.md` and invoke it once in report-only `mode:agent`, after the
initial integration Standards/Spec reports or verified ticket coverage, and
before findings are frozen.
This is a feature-level review, never a per-ticket check or an extra final gate.

Give CE the verified final snapshot's immutable cumulative `staged.patch`, the
integration-review index, feature spec, applicable standards, accepted ticket
evidence, available prerequisite results and explicitly pending final gates.
CE reviews the candidate and executable verification plan before the full matrix;
pending runtime proof is not a claim of feature acceptance. For multiple repositories, supply every
member's staged patch and verified identity under `multi-repository.md`.
Explicitly replace CE's ref-based scope discovery and ref-only scope-signal
helper with these verified snapshot inputs; never substitute its default
branch/HEAD-to-working-tree diff, which would include protected user edits.
If the installed scope helper cannot size supplied patches, pass supported
`depth:full` rather than estimating its signals. Keep CE's remaining review and
validation stages, including criteria mapping. Use the verified changed-path
manifest and patch as reviewer-selection risk inputs; unavailable helper facts
remain unknown, and declared packs still come from the existing CE config.
Apply the integration scope and finding policy in `review-mechanics.md`;
live files are context only, and HEAD/index stay read-only.

Retain CE's complete receipt as a separate report in the existing ignored
final-review artifacts, copying its returned receipt there when needed. Record
its path, SHA-256, reviewed snapshot identity and coverage. Failed, incomplete
or scope-mismatched CE output blocks feature acceptance; only absence permits
skipping. The orchestrator verifies the receipt and snapshot before repair.

Freeze source-qualified CE finding IDs with the integration findings and apply
`review-policy.md` to the combined set. For each original owning ticket, the
orchestrator starts a repair supervisor with that ticket, frozen finding IDs and
step 3's fresh `final-fix-N/pre`; the completed ticket's ended supervisor need
not remain alive. That repair supervisor implements the authorized serial batch.
Rerun or validly reuse affected gates and verify every blocking ID through the existing repair
assurance and final closeout rules. CE does not apply fixes or reopen discovery
during closure. Resume reuses verified CE evidence and actual repair dispositions;
it does not reset the final-review budget. The final report names CE's result or
skip and any unresolved findings without relabelling historical FAIL as PASS.

## Completion report

### Collect existing evidence

When a handoff or closeout needs several artifact identities, build its explicit
input list from the existing check results, reports and snapshot outputs. Reuse
identities already returned by those tools. For remaining aggregation, invoke
the bundled helper once rather than retyping hashes or parsing outcomes in prose:

```bash
python3 <execute-tickets-skill-root>/scripts/evidence_summary.py \
  --artifact G1 <existing-gate-result.json> \
  --artifact G2-initial <retained-failure-result.json> \
  --artifact G2-repaired <current-gate-result.json> \
  --artifact standards <existing-standards-report.md> \
  --output .execute-tickets/<feature>/final/evidence-summary.json
```

Use only the run's actual entries, including retained failures and pending
results when present. The helper reads those exact files, records their paths
and SHA-256, and copies scalar top-level JSON `status`, `result`, `exit_code` and
`verdict` fields into `reported` without interpretation. Text reports and JSON
without those fields have empty `reported`; read their original outcome when
needed. It refuses missing/malformed inputs, duplicate IDs and output overwrite.
Its successful exit means collection succeeded, not that the gates passed.

The supervisor still matches required gate IDs/components to the original
results, checks candidate applicability and closes failures under the existing
protocol. The summary is a derived reference list, not a new acceptance ledger
or a completeness/reuse decision. Reference it from the existing integration
index/completion evidence; keep raw results authoritative and do not duplicate
their bodies. If inputs change, collect only the affected handoff's explicit
list into a new output. A collection error calls for correcting that input or
using the original evidence, never rerunning a passed gate to rebuild a summary.

### Report the outcome

Completion means the requested feature is fully staged and verified against its
current authoritative acceptance. In both ticket completion records and the
final report, distinguish these three facts without adding a new status schema:

- Implementation: accepted/staged work and any implementation still outstanding,
  including required documentation updates or the inspected no-impact reason.
  Reference the existing index outcomes; documentation synchronization is a
  completion condition regardless of whether it had a separate ticket.
- Acceptance: required check/gate IDs proved, failed, or unproved, with references
  to the authoritative result entries and the runtime conditions they cover.
- Delivery: whether committing, publishing, deployment or other required delivery
  was actually observed, remains outstanding, or was never part of this run.

A ticket's `done` does not imply feature acceptance or delivery. A gate with an
unproved required component is not PASS; name the proved and unproved components
rather than hiding the gap in `PASS (qualified)`. Record an explicit user waiver
with its source and exact scope; waived is not passed and later owners must not
restore the waived requirement as a blocker without a new authority decision.
Do not treat permission to continue implementation as a waiver of other gates.
A successful diagnostic run on a substituted model source, configuration or
environment proves only those conditions. Apply `supervisor-protocol.md` to
prior failures; a later success alone does not close them.

When verification consumed a preserved temporary prerequisite patch, name its
authorization, paths/hashes and affected check IDs. Distinguish the passing
workspace with that patch from the staged delivery candidate without it. If the
contract requires independent candidate verification, missing proof blocks that
claim; neither workspace PASS nor permission to keep the patch unstaged waives
it. Keep the patch outside delivery unless the user explicitly changes that
boundary. Review consumes only the frozen dependency evidence allowed by
`review-mechanics.md`, never the whole protected worktree.

Lead with these outcomes and material limits. Reference existing result entries
rather than creating another full result ledger. Never claim committed, pushed,
deployed or target-runtime verified without direct evidence. Do not use counts
of tickets, agents, reviewers, commands, tests, files, or steps as a quality proxy.
For pause/resume reports and handoff-summary freshness, follow
`run-preflight.md` / Progress and resume reports. These reports reference the
same authoritative acceptance results; they do not create another state ledger.

Before that report, finish the unenclosed `run_phase/closeout` timer under
`run-metrics.md`, record the actual outcome, and run `metrics_state.py summary`
once on a best-effort basis when the metrics log remained valid. Any statistics
failure leaves completion unchanged; do not delay closeout to repair or retry it.
Otherwise report the metrics gap without
estimating missing events. Present valid scope, review, repair, gate, and duration
values only as workflow-cost diagnostics; preserve `quality_proxy: false` and
never convert them into a score.
