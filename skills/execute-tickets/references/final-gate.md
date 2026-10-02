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

1. Capture a final state snapshot, build the authoritative gate inventory, and
   apply the bounded expensive-run preparation in `supervisor-protocol.md`
   (required target, parameters, result writer/parser and admissible prior
   evidence), then run each uniquely owned feature final gate once. Reject a duplicate gate id
   whose owner, command, expected result, or reuse assessment differs. Classify
   gates from explicit authority as `always-run` or `reusable`; never infer
   dependencies from changed files. After repairs, apply
   `references/reusable-gates.md`: deterministic reuse requires exact `reusable`
   from the helper; historical runtime retention requires the gate's explicit
   authority and the protocol's evidence checks. Otherwise rerun the gate.
   When an authoritative gate requires fresh UI, browser, desktop, device, or live-app verification, the
   final-gate supervisor repeats the real target-runtime interaction and records
   fresh `runtime_observations`; a prior screenshot, cached result, forced state,
   or stale renderer cannot satisfy that gate. A ticket-declared `adb` real-device
   gate follows `supervisor-protocol.md`: detect and run it directly when a usable
   physical device is connected, and block only when no eligible device is in
   state `device`; do not ask for a second execution permission. The orchestrator records every
   execution and every verified reuse as a separate `gate` event, preserving the
   reason for rerun, reuse, or failure.
2. Complete and verify the incrementally retained compact
   `.execute-tickets/<feature>/integration-review-index.md` defined by
   `references/review-mechanics.md`. Add the final snapshot and final-gate rows
   without rereading complete prior ticket or report bodies, then freeze its
   SHA-256. It is the mandatory first-pass input for the one integration
   discovery review. Give the fresh reviewers the complete
   immutable `staged.patch`, accepted ticket reports, exact per-path hashes, and
   gate evidence only as on-demand paths. Reviewers inspect exact boundary hunks
   and directly relevant reports; they do not linearly read the complete patch
   or every historical report. The complete patch remains available, but the
   review focuses on cross-ticket contracts, shared state and cleanup owners,
   lifecycle linearization, public API/wire compatibility, and delivery closure
   instead of redoing ordinary ticket-local review. The capture produced the
   patch from:

   ```bash
   git diff --cached --binary --no-ext-diff --no-textconv --no-color
   ```

3. For closure continue the original per-axis reviewers under review-policy;
   replacement is only for unavailability or lost review context. Give both reviewers the verified index path/hash plus the on-demand evidence
   paths and snapshot identity. Freeze the finding set when both finish, then
   verify the integration-review-index hash, HEAD, Git index, working tree, and
   snapshot still match. Before dispatch, validate the intended `final_review`
   event with `review_budget.py` against the independent ledger in
   `references/review-budget.md`; record it only after both reports
   finish. A rejected transition prevents dispatch.
4. Batch findings by owning ticket/state owner and compatible scope. Capture a
   fresh `<ticket>/final-fix-N/pre` for each serial repair; never reuse the
   ticket's original baseline or hide repair inside the final-audit ticket.
   Bind each targeted review to this failed final round and its original owner
   ticket via `final_repair_review`; validate its budget before dispatch and
   retain the frozen finding IDs with its reports.
   After each verified repair snapshot and gate rerun/reuse decision, update
   only the affected integration-review-index rows and freeze a new index
   SHA-256 before closure review or the single-owner closeout below.
5. Apply the repair assurance lanes and bounded final closure in
   `references/review-policy.md`: one integration discovery review, one closure, and at most
   one regression closure. If every frozen finding closes by verified micro
   inspection, finish after required gates without another final-review dispatch.
   A non-micro repair may also finish through the single-owner targeted closeout
   in `review-policy.md` only when every eligibility condition is proved. The
   orchestrator verifies evidence identities and records that closeout in the
   existing integration index; otherwise dispatch cumulative closure within the
   remaining budget. Preserve original FAIL reports and actual dispositions. If that budget
   fails with unresolved findings, stop with evidence instead of
   starting another integration-discovery Final-N cycle.

A final repair batch follows `supervisor-protocol.md` for the order between
bounded intermediate diagnosis and stable-candidate acceptance: intermediate
edits do not trigger the whole gate set, a localized selector PASS is not a gate
PASS, and the candidate's required gates and closure run under the original
`always-run` / `reusable` and fresh-runtime contract only once the candidate is
ready for acceptance. While any known issue still blocks that round's full
acceptance, its existing failure evidence stands and the suite is not
re-triggered on an unrelated sub-fix, as defined in `supervisor-protocol.md`. Explicit prerequisite gates keep their declared order.

Completion means the requested feature is fully staged and verified against its
current authoritative acceptance. In both ticket completion records and the
final report, distinguish these three facts without adding a new status schema:

- Implementation: accepted/staged work and any implementation still outstanding.
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

Lead with these outcomes and material limits. Reference existing result entries
rather than creating another full result ledger. Never claim committed, pushed,
deployed or target-runtime verified without direct evidence. Do not use counts
of tickets, agents, reviewers, commands, tests, files, or steps as a quality proxy.
Before that report, finish the unenclosed `run_phase/closeout` timer under
`run-metrics.md`, record the actual outcome, and run `metrics_state.py summary`
once on a best-effort basis when the metrics log remained valid. Any statistics
failure leaves completion unchanged; do not delay closeout to repair or retry it.
Otherwise report the metrics gap without
estimating missing events. Present valid scope, review, repair, gate, and duration
values only as workflow-cost diagnostics; preserve `quality_proxy: false` and
never convert them into a score.
