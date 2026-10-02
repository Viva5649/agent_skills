# Review and convergence policy

This policy separates implementation technique from assurance cost. Read lane
routing when selecting assurance, finding rules when classifying a finding, and
the applicable convergence section before ticket or final review.

## Two independent decisions

Every implementation or repair declares both:

- `execution_mode`: `direct`, `test-after`, or `tdd`; this controls how the
  change is produced and tested.
- `assurance_lane`: `micro`, `standard`, or `high-risk`; this controls snapshot,
  review, and closure depth.

Do not infer one from the other. A deterministic regression may use `tdd` and
still qualify for `micro` assurance when the production change is only a safe
diagnostic. A small lifecycle edit is `high-risk` even when its diff is tiny.

Select one execution mode for the complete ticket. Any implementation work
package inherits that locked mode under `implementation-delegation.md`; workers
do not select package-local modes. End every worker before assurance review.

### Micro lane

Use `micro` only when every condition below is true:

- Authority and the expected result are explicit.
- The change does not alter public API or wire shape, return values, public error
  semantics, lifecycle or concurrency, resource ownership, security, privacy,
  persistence, routing, or externally observable product behavior.
- Production changes are limited to safe content-free logging, an internal
  rename/message/comment, a mechanical mapping already fixed by authority, or
  deletion of a demonstrably redundant branch.
- It adds no mutable state, lifecycle flag, retry, executor, cleanup owner,
  abstraction, test seam, or fake-only behavior.
- Verification selected by repair content below proves the changed responsibility.

The lane is:

1. Capture an exact pre-change snapshot.
2. Implement using the selected execution mode.
3. Run the checks selected by repair content below, the applicable deletion
   audit, and `git diff --check`.
4. Capture an immutable acceptance snapshot.
5. The orchestrator inspects the complete small delta and evidence. It verifies
   that every micro eligibility condition still holds.
6. Stage that exact verified snapshot through `review_state.py`.

There are zero reviewer rounds. This includes a post-review repair: after the
supervisor and orchestrator accept `repair_class: micro`, run the selected
checks, perform the applicable deletion audit, capture the repair snapshot, and
let the orchestrator inspect it. Do not dispatch either reviewer. If inspection
finds a disqualifying boundary, escalate the repair class before any closure
dispatch; never keep the micro label while running a dual-axis review. An
ordinary ticket still participates in the feature's initial final gate. The
inspection records each frozen finding ID as `closed-by-micro-inspection` with
its explicit authority, repair snapshot hash, and checks. A finding that still
needs Standards or Spec judgment is not micro and must escalate before repair
acceptance.

### Verification by repair content

Classify the actual repair before selecting checks; the original ticket's risk
lane does not make every later bookkeeping correction a production repair.

| Changed content | Verification owner and action |
| --- | --- |
| Production or test logic | Supervisor runs the focused behavior check and affected existing module gate; previously valid unrelated evidence remains usable. |
| Public documentation, comments or other mechanical content | Supervisor checks the changed contract/content and runs checks that consume it; no module rebuild merely because a source file's comment changed. |
| Summary, citation or disposition only, with trustworthy underlying evidence | Orchestrator compares the correction with the original result and unchanged candidate; no test run, staging or reviewer dispatch merely for that correction. |
| Required execution evidence is missing or invalid | Supervisor recovers the original complete evidence if possible; otherwise runs the smallest command proving the missing fact and retains its complete output. |

These rules do not silently waive an explicit command, fresh-execution or safety
gate. Use authority repair for an obsolete literal verifier. Gate reuse still
obeys `reusable-gates.md`; an unchanged summary is not a new final-gate attempt.
A build tool's valid `UP-TO-DATE`/cache result is not automatically missing
evidence: check selected tasks, inputs, outputs and exact required results.
Force execution only for a contractual freshness requirement, untrusted cache
or an unresolved evidence gap, narrowing the run where authority permits.

Keep one authoritative result entry per check/attempt in existing run artifacts;
matrices, dispositions and the integration index reference that entry rather
than copying its diagnosis. Preserve frozen reports, raw logs and their hashes.
Correct stale summaries in the existing disposition and link to the authoritative
entry. If hashed review input actually changes, follow snapshot integrity and
repair assurance; do not bypass hash verification. A correction revealing a
false acceptance or requiring unresolved contract judgment is not bookkeeping:
apply the ordinary finding/repair rules. A mere record correction cannot close
an unproved product requirement.

### Standard lane

Use `standard` for ordinary production, test, build, configuration, or public
documentation changes that are not micro and do not meet a high-risk trigger.
Each review round is one immutable snapshot reviewed by Standards and Spec
reviewers. Discovery starts fresh; closure reuses the original per-axis reviewer. Incremental rounds may limit each reviewer to changed paths and
boundary interactions when prior passing reports and exact prior/current
per-path hashes are supplied.

### High-risk lane

Use `high-risk` when a change affects any of:

- public API, wire compatibility, or externally visible error/result semantics;
- lifecycle, concurrency, cancellation, retry, cleanup/resource ownership, or
  persistence/data integrity;
- security, privacy, identity, authorization, routing, or cross-process failure
  handling;
- a completed blocker's interface or another ticket's state owner.

The lane uses the same two review axes, with deterministic interleaving or
boundary tests where applicable. Diff size never lowers this lane.

An assurance lane may escalate when new evidence appears. It may not downgrade
after implementation starts merely to avoid review.

## Finding classification and disposition

Classify every finding on three independent dimensions before editing:

```yaml
scope_relation: current_delta | repair_regression | untouched_existing | out_of_scope
authority_status: authority_backed | authority_blocked
repair_class: micro | non_micro
```

- `current_delta` identifies a defect in bytes owned by the current ticket. Once
  exact scope is accepted, this includes the complete final diff of pre-existing
  tracked unstaged or untracked content on those scope paths;
  `repair_regression` identifies behavior caused by a review repair;
  `untouched_existing` identifies a real pre-existing defect outside those bytes;
  `out_of_scope` identifies a requested actor, behavior, owner, or acceptance
  condition absent from the current authority/scope.
- `authority_backed` names the exact contract, ADR, ticket acceptance item, or
  repository Standard that makes the finding actionable, in the finding
  evidence; `authority_blocked` means the required observable result is
  undefined or authoritative sources disagree. The evidence states which case
  applies; both stop the same way.
- `micro` and `non_micro` describe the actual repair boundary, not severity and
  not diff size. `non_micro` covers every repair that needs a dual-axis
  closure, whether it is localized or cross-cutting.

`review-drift` is not an authority class. It is the disposition for
`scope_relation: out_of_scope`.

The supervisor first traces a failing observation to the product contract and
the affected operation's resource owner. Temporary state, environmental
variation, or a proxy metric difference alone is not a production defect. A
process-wide FD count decrease does not establish a request leak, and a flat
net count does not establish its absence. Diagnose attribution before changing
production or the verifier; retain required direct evidence and gates.

Reviewers may require another test only by identifying an unproved contract and
a concrete production path in the final candidate, not merely because more
testing is possible. When the implementation structurally eliminates a failure
path, reviewers verify that elimination and affected behavior regressions; they
do not demand injection of the removed failure. Record that evidence against
the original finding/witness. This closes only the removed mechanism, not an
independently required product failure case. If a literal ticket verifier names
the obsolete mechanism, use the existing authority repair before acceptance.

A verifier defect is not an authority conflict when authoritative behavior and
the expected result are explicit but a test, fixture, regex, scan, or command
mechanically rejects that result. Treat the verifier as the defective current
delta, repair it without weakening the acceptance meaning, and rerun the gate.
This exception does not cover an illegal production fixture, unreachable
boundary, incomplete legal oracle, weak proxy observation, or check that still
succeeds when its named evidence is absent. Those defects change or fail to
prove the acceptance contract and require an execution authority repair or a
material decision before repair.

When that return is caused before production edits by an omitted exact
production or test-only scope path, stale verifier artifact path, or another
uniquely determined ticket contract defect, the orchestrator runs execution
authority repair from `admission-preflight.md`, records the changed process
documents as approved authority transitions, keeps the run-start receipt
unchanged, and resumes the same supervisor without calling write review. The
expected result must come from stable authority outside the
repair delta; the modified test, fixture, regex, scan, or command cannot approve
itself. Do not ask for ticket order, scope, test additions, or mechanical
verification corrections that existing authority uniquely determines.

Apply these rules mechanically:

| Classification | Disposition |
| --- | --- |
| `out_of_scope` | Mark `review-drift`; retain the frozen report/hash and record withdrawal or correction in the existing disposition against the same candidate. Obtain the original reviewer's judgment when needed; do not start another review round or rewrite historical evidence. No product edit or test rerun; hashed-input changes still follow snapshot integrity. |
| `authority_blocked` | Stop before editing and request the missing product/contract decision. |
| Authority-backed verifier defect | Fix the verifier automatically, rerun the affected gate, and use the bundled verification-only contract repair when the faulty text is in the current ticket. |
| `repair_regression` with usable authority | Fix automatically within the owning scope. |
| `current_delta` and `authority_backed` | Fix automatically, selecting assurance from the real risk. |
| `untouched_existing` P0/P1 | Block acceptance and assign an owner; do not hide it as backlog. |
| `untouched_existing` P2/P3 | Record as backlog and do not block this ticket or final closure. |

A finding is actionable only when it cites the exact current delta or repair
regression and a contract, ADR, ticket acceptance item, or repository Standard.
Do not write code to satisfy an inference that has no authority.
Once agreed checks pass, the supervisor proceeds without expanding verification
unless relevant changes, failure evidence, or a specific unresolved risk justify
it. Outstanding ticket checks, assurance review, and final gates still apply.
The ticket supervisor performs every actionable ticket-review repair itself.
Do not dispatch an implementation worker after the first assurance snapshot or
ask a fresh worker to reconstruct the frozen finding set.

## Ticket review convergence

A review round means one immutable snapshot examined by both axes. Micro
assurance uses zero rounds. Standard and high-risk tickets use at most three
ticket-review rounds:

1. **Review 1 — one discovery review.** Fresh Standards and Spec reviewers
   inspect the complete immutable current-ticket delta and its declared
   boundaries. When both reports finish, freeze the complete finding set.
2. **Review 2 — one closure review.** The supervisor batches all actionable
   in-scope findings, applies one coherent repair delta, reruns affected
   ticket-scoped checks, performs the deletion audit, and captures a new
   snapshot. The original reviewers inspect only frozen finding IDs, changed paths,
   their directly impacted boundaries, and immediate repair regressions.
3. **Review 3 — at most one regression closure.** Run it only when Review 2
   proves an original finding is still open or the repair introduced a new
   regression in its directly impacted boundary. It cannot open ordinary
   findings in untouched byte-identical regions.

A closure is not another discovery. Keeping an original finding open requires
the reviewer to cite the original unmet oracle. A new `repair_regression` must
cite the exact repair hunk, directly impacted boundary, and explicit frozen
authority, then show the counterfactual: removing the repair delta removes the
defect. If the same defect exists in the discovery snapshot, it is late
discovery and cannot be opened in closure. A stronger proof with no explicit
authority is `review-drift` or `authority_blocked`, not a repair requirement.

Repair assurance routes mechanically. An accepted micro repair exits through
the micro orchestrator inspection above and consumes no closure round. Only a
`non_micro` repair may dispatch the next dual-axis closure.

Each closure must reduce unresolved findings, close an original so only its
immediate repair regression remains, or withdraw a drift finding. The same
finding ID returning unchanged in two consecutive rounds is no progress. Before
adding another mechanism, repeat the deletion audit and remove unsupported
repair complexity.

After the regression closure, do not stage a candidate that still lacks required
assurance. Mark the ticket and its descendants blocked with snapshots, checks,
finding IDs, and the missing decision or unresolved defect. Continue other
frontier tickets by default when their blockers, contracts, and state owners are
genuinely independent; an execution plan may explicitly forbid that
continuation. Keep execution serial and aggregate unrelated blocked decisions
for one later user interaction. The canonical feature review ledger retains
these phases across pause, resume, and run-start changes; never create a new
chain or epoch to obtain another discovery/closure budget.

Ask the user immediately only for:

- an authority gap or conflict, undefined observable behavior, or competing
  product semantics;
- a public API, wire, or external error-contract decision;
- expansion into a completed blocker's contract or another ticket's state owner;
- new external, destructive, credential, Git-history, or device authority
  outside the ticket-declared bounded `adb` real-device verification lane.

These are the concrete project meaning of a material decision: observable
behavior, public interface, production ownership, or runtime state semantics.
Ticket order, a behavior-preserving exact scope correction, test-only scope, and
an authority-backed verifier repair are not material decisions.

Do not ask for normal in-scope finding repairs, contract-backed verifier repairs,
test additions required by an existing contract, execution-mode selection, or
the closure/regression-closure round that is still within budget.

## Reviewer continuity

Keep the Standards and Spec reviewer identities after discovery. For ticket,
final and targeted-repair closure, continue each original reviewer with the new
snapshot, frozen finding IDs, prior/current path hashes and exact repair hunks.
Do not pass implementation reasoning as review authority. Reuse context, not
stale PASS: both axes issue reports for the current immutable snapshot.

Replace an axis with a fresh read-only reviewer only when its original reviewer
is unavailable or cannot reliably recover the frozen review inputs. Give the
replacement the same bounded evidence and original oracle; record the reason
with the report. Replacement consumes the existing round and never resets the
budget or opens discovery. Micro repairs still dispatch zero reviewers.

## Incremental re-review

Any repository edit invalidates the prior snapshot. Capture a new snapshot, but
do not force reviewers to re-audit byte-identical paths. Supply the prior passing
report and exact prior/current per-path hashes:

- Production changes: inspect changed production paths, their boundary
  interactions, and affected verification.
- Non-micro test-only changes: inspect the changed tests and asserted contract;
  preserve passing production conclusions when production hashes are identical.
  Micro test-only repairs use orchestrator inspection and no reviewers.
- Public-documentation-only changes: inspect the changed documents and contract.
- Report-only drift correction: retain frozen reports and record the correction
  against the same candidate in the existing disposition; run no tests. If a
  hashed assurance input changes, follow snapshot integrity above.

If a required report or hash is unavailable, review the full relevant delta.

## Final review convergence

The final level has at most three cumulative feature-review rounds:

1. One integration discovery review. Reviewers receive the full staged feature
   patch, accepted ticket reports and exact hashes, ordering/ownership authority,
   and feature final-gate evidence. They inspect cross-ticket integration
   exhaustively while treating previously accepted byte-identical ticket-local
   logic as established evidence. They may still report a new P0/P1 anywhere in
   the full patch when necessary to establish an integration or lifecycle
   boundary. Freeze the finding set when both reports complete.
2. One closure review after accepted non-micro repairs are staged, unless the
   single-owner targeted closeout below applies. If all frozen
   findings are closed by verified micro inspection and required final gates
   pass, finish from that evidence without another reviewer round; retain the
   original FAIL reports and `closed-by-micro-inspection` dispositions.
3. At most one regression closure, only when round 2 proves an original finding
   is still open or a repair caused a new P0/P1 in its directly impacted boundary.

Batch the frozen findings before repair. Merge findings that share one owning
ticket, state owner, and compatible scope into one repair delta; different
tickets still execute serially. Classify each repair independently:

- `micro`: zero repair reviewers; use the micro acceptance snapshot.
- `standard`: at most one targeted two-axis repair round.
- `high-risk`: at most two targeted two-axis repair rounds.

Record targeted rounds as `final_repair_review` under `review-budget.md`, using the
original completed ticket number. The batch is fixed by that owner and the most
recent failing cumulative final review, whose frozen reports supply its finding
IDs. Merge compatible findings for the same owner; incompatible scope blocks
for resolution rather than minting a new batch ID. Do not relabel the same
repair, split its findings or use a synthetic ticket number to restart budget.
The first round fixes `standard` or `high_risk`; only a failing high_risk first
round with a subsequent verified non-micro repair permits targeted closure.
Use `review_budget.py` to validate before dispatch and record the verified outcome
after both axes finish. Optional cost recording under `run-metrics.md` never
controls progression. Block cumulative closure while any targeted batch lacks
either current targeted PASS
or a subsequent verified micro inspection closing its remaining frozen IDs.
Record that inspection as `repair/repair_micro/pass`, preserving original report
statuses; it closes the findings without a targeted closure reviewer. A mixed
batch of owners still uses cumulative closure for its non-micro repairs. On resume,
recover any missing budget records from verified execution evidence under
`review-budget.md`; never infer assurance or prior budget use from statistics.

### Single-owner targeted closeout

The orchestrator may omit the next cumulative closure only after the initial
integration discovery and the required targeted Standards and Spec review.
It verifies all of the following from the complete frozen finding set of the
same failing final round, every subsequent repair and the retained reports:

- Every finding requiring repair and every actual repair belongs to one original
  completed ticket. No second owner, split batch or synthetic ticket hides work.
- Both targeted axes PASS on the complete repair candidate, explicitly close
  every actionable frozen finding and cover all affected integration boundaries.
  Other frozen findings have valid explicit dispositions. No contract judgment,
  new failure or unreviewed cross-ticket interaction remains.
- The current staged content is exactly the accepted repair candidate; other
  accepted bytes remain unchanged. No later production/test/build, authority or
  verification-command change invalidates that candidate or its conclusions.
- Every required gate has passing evidence, valid reuse under its own contract,
  or an exact user disposition. The index, report and artifact identities verify.

One file, one ticket label, a targeted PASS, or exhausted review budget alone is
not eligibility. Multiple owners, uncovered interactions, missing evidence or
later changes use normal repair and cumulative closure within the existing
budget; never fall back to an obsolete targeted PASS. If a later non-micro repair
invalidates targeted PASS and the existing budget permits no further targeted
review, block; remaining cumulative rounds cannot replace missing targeted
assurance. All-micro repairs retain their existing independent closeout path.

When eligible, the orchestrator verifies identity, finding dispositions and gate
results without re-performing semantic review. In the existing integration index
record `closed-by-targeted-review` with the failed final-round identity, original
owner, frozen finding dispositions and targeted report/repair/gate hashes. Keep
original final FAIL reports and the actual `final_repair_review` PASS events;
do not invent a cumulative PASS event or new metrics enum. Resume verifies that
record against current accepted content/evidence; if it cannot, do not infer
completion from the last targeted event. No additional reviewer dispatch occurs.

### Cumulative closure when required

Repair review rounds inspect only the repair delta and cited boundary. They are
not new integration discovery reviews. The final closure may verify only the frozen
finding IDs, repair regressions, and new P0/P1 inside directly impacted
boundaries. A newly noticed untouched-region P2/P3 becomes backlog and does not
block closure.

If a repair batch does not pass inside its targeted-review budget, block it
before protected staging; cumulative closure never substitutes for missing
repair-delta assurance. Each cumulative closure uses both axes with the prior
reports and exact repair/path hashes.

If the optional regression closure still fails, stop with bounded evidence. Do
not start Final-4, Final-5, or another unbounded integration-review cycle.
Before every final-review dispatch, validate the intended event with
`review_budget.py` under `references/review-budget.md`; the tool rejects duplicate or out-of-order final phases and
there is no `final_closure` fourth phase. A new run-start does not reset this
feature-level budget.
