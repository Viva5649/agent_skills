# Ticket supervisor protocol

Every fresh ticket supervisor reads the `Context boundary`,
`Supervisor status protocol`, `Execution mode routing`, and
`Assurance lane routing` sections before it starts, from the absolute
`references/supervisor-protocol.md` path received in its cold-start inputs.
Device/document details load only when applicable. The orchestrator reads its
`Context boundary` and `Supervisor status protocol` responsibilities and reuses
unchanged loaded sections; an update requires only the changed applicable
sections. This file owns those four sections.
The ticket lifecycle and Git transitions remain in `SKILL.md`.

## Context boundary

Keep the orchestrator thin so a long ticket graph does not accumulate implementation history in the main context.

- Resolve all ticket paths, but parse only their scheduling metadata (`ticket number`, `Status`, and `Blocked by`) before selection. Do not preload every ticket body into the orchestrator context.
- After selection, read only the current ticket's cold-start contract so the orchestrator can validate the supervisor's scope and verification traces. Do not read future ticket bodies.
- Start each supervisor, implementation worker, and discovery reviewer without inherited conversation history when the agent API supports it, for example with `fork_turns: "none"`. Closure continues the same per-axis reviewer under `review-policy.md`. Give absolute repository and input-file paths instead of pasting large specs, tickets, patches, or logs into prompts.
- Give the supervisor only the feature spec path, current ticket path, relevant
  standards paths, current repository, the resolved absolute
  `<execute-tickets-skill-root>`, the absolute `references/supervisor-protocol.md`
  path, and compact evidence for the current
  ticket's direct completed blockers, selected from their retained
  integration-review-index rows. For each consumed blocker, that evidence
  contains the exact ticket path and SHA-256, only the verbatim `Produces` rows
  named by this ticket's `Consumes`, the accepted-content index hash and
  completion outcome, and only the ordering/ownership rows those interfaces
  cite. Do not include transitive blockers or
  unrelated ticket sections. Keep each complete blocker ticket path as an
  on-demand fallback; the supervisor must not read the complete blocker ticket
  by default. It opens that ticket only when compact evidence is missing,
  internally inconsistent, or disagrees with the current ticket or repository,
  and then reports the mismatch instead of treating the extra prose as new
  authority.
- Keep raw command output, patches, and reviewer reports in the ignored run-artifact tree under `.execute-tickets/<feature>/...`. Return paths and SHA-256 values to the orchestrator instead of file bodies.
- Run package-focused commands in the assigned worker context and full ticket test, build, and device commands in the supervisor context. The orchestrator runs only bounded scheduling and Git-state commands.
- Limit every supervisor-to-orchestrator status envelope to 600 words. Reference existing ticket/evidence sections by absolute path, SHA-256 and heading/id instead of copying them. Commands may reference a uniquely resolved check id; include current exit codes, but replace successful raw output with a short result and keep failure output to at most the 80 diagnostic lines that identify the failure.
- Never return a supervisor's, worker's, or reviewer's reasoning transcript to the orchestrator. Worker handoffs return only to the supervisor under the bundled delegation schema. Reviewer findings remain in separate Standards and Spec report files; the envelope contains only each axis's status, finding count, unresolved finding IDs, report path, and report hash.
- After each accepted ticket, retain its immutable completion transition
  evidence and verified integration-review-index row under
  `.execute-tickets/<feature>/...` as the cold-start checkpoint. Resume only
  from those artifacts instead of reconstructing prior ticket conversations. A
  missing checkpoint stops resume safely; do not depend on automatic
  conversation compaction for correctness.

## Supervisor status protocol

For a feature with multiple registered repositories, apply `multi-repository.md`
to every envelope: use `NAME:path` in scope, changed paths, traces, and audit
rows; identify the aggregate snapshot and each member's hashes. The supervisor
receives every registered root and its applicable instructions. Commands retain
their ticket-declared working directory; the supervisor must not infer it from
the files changed. One supervisor still owns the entire ticket outcome.

Use these supervisor status names so the orchestrator can route mechanically:

| Status | Meaning |
| --- | --- |
| `scope_ready` | The supervisor has read the ticket, replayed scope closure, selected its execution mode and assurance lane, and declared its exact candidate file scope and verification commands; the orchestrator must assess scope ownership before implementation starts. |
| `implementation_ready` | All implementation workers ended; the supervisor integrated the complete delta, finished ticket-scoped verification, and rebuilt every correctness-critical witness against the final candidate as a legal-fixture/oracle matrix; the orchestrator may freeze an assurance snapshot. |
| `review_complete` | The assurance lane's required reviewers finished against one snapshot; the orchestrator must verify that snapshot before fixes or acceptance. Micro assurance does not emit this status. |
| `drift_detected` | A tracked or untracked path outside the accepted ticket scope changed and can affect the current ticket, or safe isolation is unclear. Harmless outside-scope changes remain outside the ticket delta/index and do not emit this status. |
| `blocked` | The supervisor cannot proceed within the current ticket. `blocker_class` tells the orchestrator whether to run execution authority repair, request a material decision, or stop with evidence. |

The supervisor must wait after `scope_ready`, `implementation_ready`, `review_complete`, and `drift_detected`. It must not edit the working tree again until the orchestrator captures or verifies the requested snapshot, or reconciles the exact drift report, and explicitly returns the result.
There is no separate acceptance declaration. The orchestrator judges acceptance
from evidence: a final `review_complete` whose reports pass with every finding
disposed on a verified snapshot, or a `micro_input_valid` inspection, releases
protected staging directly; `review_state.py verify` and `stage` recheck that
same snapshot byte-for-byte immediately before the index changes.
An implementation-worker handoff is not a supervisor status and never goes to
the orchestrator. Only the ticket supervisor emits the five statuses above.

Use this bounded envelope shape; omit fields that do not apply to the current status.
`checks.duration_ms` is optional diagnostic data: omit it or use `null` when
unmeasured. The orchestrator must not reject an envelope, delay progression, or
rerun a check to obtain or repair timing. Check results and evidence remain required:

```yaml
status: scope_ready | implementation_ready | review_complete | drift_detected | blocked
ticket: <exact ticket number>
ticket_contract: <valid, or the exact missing/conflicting contract field>
admission_basis: <run-start admitted-by-review/admitted-by-user evidence plus ordered approved authority-transition ids and hashes>
execution_mode: direct | test-after | tdd
execution_mode_reason: <ticket requirement and production-path evidence for this mode>
assurance_lane: micro | standard | high-risk
assurance_lane_reason: <review-policy eligibility or risk trigger>
test_seam: <stable public production seam, only for test-after or tdd>
snapshot: <absolute path and identity hashes, only for a snapshot already captured at this status>
changed_paths: [<repository-relative path>]
scope_paths: [<exact repository-relative file path>]
scope_trace:
  <exact repository-relative path>: <declared write-scope entry or permitted-discovery evidence>
scope_closure_trace:
  - command: <exact permitted-discovery command, or None>
    authoring_baseline: <recorded authoring baseline>
    execution_baseline: <current HEAD and completed-blocker basis>
    dispositions:
      <repository-relative path>: <declared-write | permitted-write | read-only | false-positive, with reason when required>
    result: <exactly 0 undisposed paths, or exact no-discovery result>
verification_trace:
  - acceptance: <ticket acceptance identifier>
    source: <spec, ADR, or recorded user-approved requirement>
    command: <exact shell command or target-runtime interaction protocol>
verification_witness_trace:
  - acceptance: <correctness-critical acceptance identifier>
    producer: <exact production producer>
    legal_fixture: <production-valid input construction>
    reachability: <numeric bound or deterministic interleaving>
    oracle: <all authority-permitted results>
    observation: <direct value, identity, count, ordering, artifact, or side effect>
    absence_detector: <observed or validly reused execution-integrity/red evidence and applicability>
document_edit_contract:
  mode: <surgical | whole-document>
  authority: <ticket section and current authority>
  authorized_changes: [<exact heading/fenced-block responsibility or fact>]
document_deletion_audit:
  status: <pass | not_applicable>
  artifact: <absolute path>
  sha256: <SHA-256>
preflight_trace:
  - id: <ticket check or feature gate id>
    classification: <pass | intentional-fail | implementation-dependent>
    command: <exact non-mutating preflight>
    expected: <recorded baseline result>
    observed: <current result and blocker trace; or shared prerequisite failure evidence, masked check IDs and resumption condition>
checks:
  - command: <exact command>
    exit_code: <integer>
    duration_ms: <optional measured non-negative integer or null>
    result: <short result or bounded failure tail>
    log: <absolute path and SHA-256>
runtime_observations:
  - acceptance: <ticket acceptance identifier>
    target_runtime: <real app, browser, desktop, or device environment>
    interaction: <exact path exercised>
    freshness: <refresh or reset action>
    observed_result: <directly observed state, output, or side effect>
    authenticity: <evidence excluding mock, cache, screenshot-only state, forced state, or stale renderer>
    artifact: <supporting artifact path and SHA-256, or exact None>
reviews:
  standards: <status, finding IDs, report path, SHA-256>
  spec: <status, finding IDs, report path, SHA-256>
drift_report: <report path, SHA-256, status, and exact changed paths>
blocker_class: <none | authority_backed_ticket_defect | material_decision | evidence_unavailable | execution_defect>
blocker: <exact stop condition and affected descendants>
```

For `drift_detected`, the supervisor reports only exact observed paths, the
ticket input or boundary they may affect, and stops writing. The orchestrator
reads `references/working-tree-drift.md`, produces the bounded report, and owns
reconciliation. Do not use this status merely to investigate who changed an
unrelated path. A worker package write
outside its assignment but still inside the accepted ticket scope remains a
delegation breach and uses `blocked`; it is not protected external drift.

Every non-`blocked` envelope uses `blocker_class: none`. For `blocked`, set
`blocker_class: authority_backed_ticket_defect` only when the
execution authority repair predicates in `admission-preflight.md` all hold.
Missing test-only scope, an exact caller omitted from write scope, or a verifier
artifact path fixed by stable authority outside the proposed repair may use that
class. The modified test, fixture, regex, scan, or command cannot be its own only
authority. A public behavior, owner, state, retry, or ordering choice uses
`material_decision`; missing runtime or irreproducible evidence uses
`evidence_unavailable`; an exhausted in-scope implementation or review defect
uses `execution_defect`.

Every envelope from `scope_ready` through `review_complete` retains explicit
`execution_mode` and `assurance_lane` values. Unchanged admission basis, reasons,
seam, scope and planned traces may reference the current ticket or frozen evidence
by absolute path, SHA-256 and section/id. The orchestrator verifies the identity
and resolves the reference; missing, ambiguous, cyclic or stale references block.
Use existing ticket/snapshot/report artifacts, not a new reference registry.
Expand differences and new results only. References replace duplication, not
required evidence or final-candidate verification; neither actor repeats the
other actor’s semantic review when the evidence agrees.
Every `scope_ready` envelope sets `ticket_contract: valid` and resolves every
exact scope path, its authority, verification command and planned witness through
the corresponding trace or verified section reference. Unchanged declared scope
may reference the complete declared-scope section once; discovery additions
require exact dispositions. Planned witness references must cover every
applicable correctness-critical item. A supervisor that cannot produce a required trace emits `blocked` instead
of completing the missing design itself. Omit `runtime_observations` from
`scope_ready`; include it from `implementation_ready` onward only when an
acceptance item requires direct UI, browser, desktop, device, or live-app
evidence.
`snapshot` follows real capture timing: at `scope_ready` this ticket's `pre`
snapshot is not yet captured, so omit the field and never name a future
snapshot. At `implementation_ready`, it may carry the actual `pre` identity the
orchestrator returned; it must not claim an assurance or review snapshot that has
not been captured. `review_complete` binds the exact snapshot its reviewers
inspected. `drift_detected` and `blocked` reference only snapshot identities
already obtained and applicable to that report, and omit the field otherwise.

When existing Markdown is in scope, retain or reference `document_edit_contract`
from `scope_ready` onward. Omit `document_deletion_audit` from `scope_ready`; include
its final status, artifact path, and SHA-256 from `implementation_ready` onward.
If either applicable field is missing, emit `blocked`.

The `verification_witness_trace` in `scope_ready` is a plan. Before
`implementation_ready`, rebuild it from the final candidate: use one entry for
each behaviorally distinct legal fixture, authority-permitted race, and
operation-specific success no-op required by acceptance; name the final test or command, complete
oracle, direct observation and retained execution log. Reference shared, applicable
absence evidence under `admission-preflight.md` rather than requiring a new
counterfactual failure for every branch. Do not copy the planned trace forward,
collapse distinct legal branches into one broad fixture, or cite a green command
without proving required execution and inspecting its behavioral assertions. If this final matrix cannot be produced, emit `blocked`
instead of relying on discovery review to find the missing witness.
If the final implementation structurally eliminates a failure path, apply
`review-policy.md`: record elimination evidence and affected behavior checks
instead of forcing that removed path. Independently required product failure
cases and literal verifier-contract corrections retain their existing gates.

## Before an expensive build or runtime gate

Resolve decisive feasibility gaps using the existing witness and the smallest
authorized probe before the full matrix: sustained environment conditions,
actual writer/parser visibility and required serial time within the total
budget. Reuse applicable evidence; do not turn this into another review or
require a probe when the facts are already known. Deployment or load generation
belongs to its authorized verification owner, not a non-mutating authoring
preflight.

The supervisor executing the gate checks its existing verification trace once:
required target/selector, parameter/environment sources, actual result writer
and artifact, parser/oracle, explicitly consumed blocker evidence and user
waivers. Resolve missing required parameters and mismatched result locations
before launch. Do not default to an entire class/suite when authority requires
a narrower target; do not silently narrow a contract that requires the suite.
Consume prior runtime evidence only when the contract assigns that proof to the
blocker or explicitly permits historical retention after repairs under
`reusable-gates.md`; a fresh-runtime gate still runs. Deterministic reuse keeps
its manifest/external-state rules. Use scope/authority repair for a defective literal
command, not an ad-hoc weaker substitute.

When changing a verifier, its implementation owner uses the existing witness to
trace observations, comparisons and reachable failure cleanup before the costly
run: compare actual values/order/uniqueness when required, read role/registry
from the declared installed/runtime boundary, and ensure failures after starting
a background fixture release/wait through its existing owner. Matching shapes,
counts or self-reported labels is not proof of these properties. Inspect the
changed path and reuse existing artifacts; do not add a pre-review round,
production instrumentation or a mutation matrix. Reference this check in the
existing witness. Other roles do not repeat it without relevant change or a
concrete gap. Run the declared acceptance after repairing a discovered defect;
this inspection never substitutes for it.

A ticket that adds or changes a verification entry names its runnability owner
in the existing verification trace. Runner, build wiring, parameter, result
location and assertion defects, and the initialization, connection, or parameter
preconditions a named entry needs to start on its own, when decidable now belong
to this ticket's implementation owner before completion. Startup execution and legal-input
reachability that need a future device or an unfinished dependency belong to the
named earliest applicable owner after that dependency is ready and before the
full expensive matrix; that owner may be a later ticket, or the final-gate owner
when the original contract satisfies the dependency only there. Do not require
the author to build the whole fixture early or probe every ticket on hardware.
The supervisor follows the real path to confirm the new entry starts and its
legal input reaches the declared condition, and reuses applicable direct
evidence instead of probing known facts again. After a source repair, before a
gate result represents it, the supervisor confirms the artifact actually
installed or run already carries that repair. The existing build input, artifact,
and install records are reused to bind that repair to the installed/run identity;
only when they cannot establish the correspondence does it rebuild the relevant
artifact. A source edit or an earlier build-success message alone does not prove
that correspondence, and the hash is not required to change every time, a full
rebuild is not forced, and not every ticket moves to hardware early. When a declared dependency is
still outstanding, retain its deferred owner, condition, and unproved items
under the existing contract above instead of probing hardware to re-confirm
that known blocker; resume at the named owner and stage above only when new
facts appear or the dependency completes, and explicit ticket-scoped or safety
prerequisite gates are never deferred. A minimal probe proves only its
covered range; it never replaces ticket-scoped checks or feature final gates.

## Target-runtime failures and diagnosis

First distinguish an unmet environment prerequisite from a product failure
under valid conditions, and check whether the oracle rejected a result allowed
by authority. If a required sustained condition breaks, stop the affected
observation through the fixture owner's existing cleanup and report that
component unproved; do not run out the timeout or widen it as a substitute for
diagnosis. A product violation under valid conditions remains a defect. Select
the next bounded probe only when it discriminates a stated question. Proven
unreachability or an exhausted diagnostic bound returns the exact unproved
requirement to its decision owner; it does not authorize weakening acceptance.

For the first failure, retain the existing full diagnostic log, exit/result and
runtime conditions needed by the ticket (such as build, model source/config and
cache state) before another run can overwrite them. Respect credential/privacy
rules; use existing logging boundaries rather than adding production
instrumentation solely for evidence.

Before a subsequent diagnostic run, name the question it discriminates, the
additional evidence to capture and the ticket's attempt/time limit. If the
ticket lacks a limit, record the smallest bounded attempt within existing
authority; do not start an open-ended run-until-pass loop. Stop that diagnosis
when its bound is reached or another failure adds no new discriminating evidence,
and report the unresolved behavior. Continue independent authorized work.

A different model source, configuration or environment proves only that changed
condition and cannot replace the original acceptance path. A later pass on the
same code/conditions does not erase a prior failure: closure requires an
established cause with appropriate repair/reverification, or an explicit user
disposition. Capture the failure evidence before deciding that a retry is an
acceptance result. None of this grants additional device or external authority.

Inside an existing final repair batch, the original repair owner runs the
smallest authorized check that answers the current failure and continues bounded
repairs and diagnosis while that question stays open. An intermediate edit does
not automatically trigger the whole final gate set, open a new review round, or
reset the diagnostic budget, and independent components do not escort every
intermediate candidate when they cannot answer the current question. Explicit
prerequisite gates keep their declared order and are never deferred. Only when
the candidate is ready for acceptance does the repair owner complete the ticket's
original checks, snapshot, and assurance for that candidate, after which the
final-gate supervisor runs the gates and closure required for it under the
original contract (`final-gate.md`). A localized selector PASS is not a gate
PASS; `always-run` / `reusable` and fresh-runtime requirements keep their original
meaning, with no added prior-PASS retention. When a final failure round still
has any known, already-attributed issue that blocks its full acceptance, the
orchestrator does not re-dispatch the entire acceptance suite because one
sub-problem was repaired. It keeps that round's existing failure evidence as the
attribution, and the repair owner runs only the targeted check that answers its
own fix or attribution; the orchestrator routes any conflict through the existing
execution authority repair or a user disposition. Full acceptance runs only after
every such blocking issue is repaired or explicitly dispositioned under the
original authority and the candidate is ready. This hold does not stop the
targeted runs needed for attribution, repair, or independently authorized work,
and it is not a global stop; the original FAIL, the explicit prerequisite-gate
order, `always-run` / `reusable` / fresh-runtime, and the diagnostic budget are
all preserved. When diagnosis
exceeds its scope, authority, or bound, stop through
the existing stop/report path instead of continuing to declare that it is still
diagnosing.

## Ticket-declared `adb` real-device verification

Do not ask the user to authorize an `adb` verification already required by the
ticket. Before the device gate, run `adb devices -l` and select an eligible
physical device whose state is exactly `device` and whose serial, ABI, and SDK
meet the ticket's declared conditions. If several qualify and the ticket does
not name a serial, select the lexicographically first serial; run all only when
authority explicitly requires multiple devices or ABIs.

The bounded device lane may install, replace, or uninstall the exact APK/package
produced or used by the current ticket. Resolve that identity mechanically from
the ticket, build output, or manifest; do not ask again when the result is
unique. Uninstall's normal removal of that package's data is part of the
authorized uninstall operation. The lane may also create a ticket-specific
directory under `/data/local/tmp/`, push only the declared test artifacts, set
the permissions needed to execute those artifacts, run the exact ticket cases,
and retain the commands, exit codes, output, and `runtime_observations`. These
operations are normal ticket verification and require no second permission
prompt.

If no eligible physical device is in state `device`, emit `blocked` with
`blocker_class: evidence_unavailable` and report the exact observed states.
`offline`, `unauthorized`, emulator-only, an empty list, or a device that misses
the ticket's declared conditions all mean no usable real device. Resume the gate
directly after a usable device appears; do not substitute a host test, prior
PASS, or emulator result.

This bounded lane does not authorize operations on unrelated applications,
direct `pm clear` or other application-data changes, system-setting changes,
unrelated device paths, root/remount/reboot, credentials, or external services.
Those operations need their own explicit authority.

## Implementation and deletion audits

When applicable repository instructions require these audits, the ticket
supervisor owns them, including the integrated deltas of delegated workers.
They do not add a reviewer round or authorize out-of-scope cleanup.

At implementation checkpoints, the supervisor audits additions or changes since the previous checkpoint. After the selected verification passes and before code review or handoff, it performs a deletion audit against the final diff and affected lifecycle contracts, including retained code participating in those contracts.

Both audits cover:

- mutable field, lock, lifecycle or phase flag;
- identity guard, duplicate state check, retry, or cleanup branch;
- private helper or abstraction;
- fake-only failure path.

For each audit object, the supervisor identifies:

1. The explicit requirement or plan ID.
2. The real production caller and thread or interleaving that exercises it.
3. Why existing state or a single resource owner is insufficient.

The supervisor reuses valid audit conclusions and revisits them when relevant code, dependencies, ownership, or assumptions change. Reuse does not waive tests required to run again, prerequisite evidence gates, or safety verification.

Unsupported direct calls, hypothetical concurrency, and "defensive robustness" are not production justifications. Within authorized scope, the supervisor removes unjustified additions and structures made unnecessary by the change, preserves unrelated existing code, and resolves any unclear required contract through the existing scope and authority-repair/material-decision rules.

## Markdown document-deletion audit

Apply this section whenever the ticket modifies an existing Markdown file.
At `scope_ready`, replay the ticket's `## Documentation edit contract` and set
`document_edit_contract.mode`. Default to `surgical`. Accept `whole-document`
only when the ticket cites a current spec, ADR, or recorded user approval that
explicitly authorizes the whole-document replacement. An accepted scope path
authorizes editing bytes, not redesigning the whole document.

Before `implementation_ready`, compare the final candidate with the pre
snapshot and write
`.execute-tickets/<feature>/<ticket>/document-deletion-audit.md`. Audit only
each deleted or wholly replaced Markdown heading section and each fenced code
block, regardless of fence language. Do not use deleted line count, fenced-block
count, or Mermaid count as an acceptance proxy. Multiple fenced blocks may
share one row only when they are under the same heading, have the same original
responsibility, and share one disposition and authority.

Use this table:

| Path | Unit | Original responsibility | Disposition | Authority | Replacement |
| --- | --- | --- | --- | --- | --- |
| `<repository-relative .md path>` | `<heading path or fenced block under heading>` | `<what the unit was responsible for>` | `<replaced | superseded>` | `<exact current source>` | `<exact target path and heading/block, or None>` |

`replaced` means the responsibility still exists; `Replacement` must point to
content in the final candidate that continues that responsibility.
`superseded` means the responsibility or fact no longer exists; `Authority`
must prove that absence from current spec, ADR, recorded user approval, or
current code contract. Split a unit that mixes current and obsolete
responsibilities. Missing actual deletions, a replacement that does not carry
the responsibility, an authority-free supersession, or any `unexplained` unit
blocks `implementation_ready`.

Hash the completed artifact and report `status: pass`. When the final diff has
no deleted or wholly replaced heading section or fenced block, still write the
artifact with `status: not_applicable` and the inspected Markdown paths. This
audit does not replace positive documentation acceptance in the ticket.

## Execution mode routing

The ticket supervisor selects exactly one execution mode after reading the ticket, surrounding code, immediate callers, shared utilities, and relevant existing tests, but before editing or running ticket checks. The orchestrator does not infer complexity from ticket size or file count. It mechanically rejects a `scope_ready` envelope that omits the mode, its evidence, or the exact verification commands.

Apply these rules in priority order to stable acceptance behaviors. Unfinished
wiring, placeholders, and missing future dependencies are not themselves new
regressions. Intermediate steps need only the checks required to continue;
the named later ticket or final-gate owner verifies deferred product behavior.
The supervisor must not waive current ticket acceptance, safety invariants, or
explicit prerequisite evidence gates because the feature is unfinished. A
defective ticket follows existing authority repair, not silent check omission.

### `tdd`

Select `tdd` when any of these conditions is true:

- The ticket explicitly requires test-first development or a regression test.
- The ticket fixes a reproducible bug through a stable production seam.
- The ticket adds or changes a business rule, validation rule, parser or serializer behavior, error semantics, state transition, lifecycle or resource ownership, concurrency, retry or recovery behavior, persistence, data integrity, or security behavior.
- The ticket contains multiple independent acceptance behaviors that each require a new test.
- A runnable example is needed to resolve uncertainty about the required production behavior.

The supervisor confirms the production seam and expected behavior from the ticket or spec before writing the first test. If neither source establishes the seam and expected result, the supervisor emits `blocked` and asks the user; it does not invent a seam merely to start TDD. The supervisor then works in one vertical red → green slice at a time. It does not write a batch of base-case tests before implementation.

The slice is one stable product behavior. Once its existing or new behavior
test fails, the implementation owner may implement, wire, and adjust multiple
internal steps until it passes. Files, helpers, and work packages do not each
require a new failing test. During implementation or review repair, an existing
failing test covering the gap is sufficient: fix and rerun it. Add a behavior
test only for a new stable behavior, an uncovered real regression, or a required
safety invariant without coverage; do not manufacture reds for temporary states
or retroactively recreate a failure merely to document the repair sequence.

For a bug or regression, `execution_mode_reason` states the reproduced failure,
the ticket's evidence-backed causal model, and the decisive check that could
falsify it. If new evidence breaks that model before editing, the supervisor
replaces `scope_ready`; if editing has started, it emits `blocked` and returns
the work to diagnosis. It does not add a second symptom workaround to preserve
the original plan.

An agreed behavior test does not change merely because production code fails it. The supervisor may change such a test only when the ticket or spec changed, the selected seam was proven wrong, or the fixture or test infrastructure was defective. The supervisor records that reason in the next status envelope.

### `test-after`

Select `test-after` only when all of these conditions are true:

- The ticket changes externally observable behavior through an existing stable production seam.
- The ticket and spec together completely establish the expected result.
- None of the `tdd` conditions applies.
- Implementing the behavior is direct enough that a failing test would not resolve design uncertainty.

The supervisor implements first, then adds at most one focused behavior test through the declared seam. If the supervisor identifies more than one independent acceptance behavior before editing, it switches to `tdd`. If it discovers that need only after editing started, it emits `blocked` so the ticket can be split; it does not pretend to apply TDD retroactively or grow an unplanned unit-test matrix.

### `direct`

Select `direct` only when all of these conditions are true:

- The ticket introduces no new externally observable production behavior or public contract.
- The ticket is mechanical, such as documentation, configuration, build metadata, naming, or wiring already exercised by existing verification.
- None of the `tdd` conditions applies.
- Existing compilation, static checks, tests, or ticket-mandated commands exercise the changed path.

The supervisor edits the declared files directly and runs the declared existing verification. It does not add a test merely to prove that implementation started.

If none of the three modes satisfies its stated conditions, the supervisor emits `blocked` with the missing requirement, seam, or verification evidence. It does not choose `tdd` merely because the route is unclear.

### Mode changes

Before the first production edit, the supervisor may only escalate `direct → test-after → tdd`; it never downgrades. It records the new mode and the concrete condition that caused escalation in a replacement `scope_ready` envelope and waits for `scope_accepted` again. After editing starts, the mode is locked. If a newly discovered condition requires a different mode, the supervisor emits `blocked` instead of reclassifying completed work or applying TDD retroactively. If any escalation requires another file, the supervisor lists that exact file in the replacement `scope_ready` envelope before touching it.

Execution mode controls implementation and ticket-scoped verification only. Assurance depth is selected independently through `references/review-policy.md`. Every combination still uses scope isolation, immutable snapshots, protected staging, completion evidence, and the bounded final gate; only the required reviewer rounds differ.
Execution mode is ticket-wide. Every delegated work package inherits the same
locked mode; delegation is not a fourth mode. Under `tdd`, one worker owns the
behavior test and production fix for one complete red → green vertical slice.
The locked mode governs the target behavior, not a per-edit testing ritual.

## Assurance lane routing

Select exactly one `micro`, `standard`, or `high-risk` lane before editing, using
`references/review-policy.md`. The orchestrator rejects `scope_ready` when the
lane or its concrete eligibility/risk evidence is missing. A lane may escalate
before staging when new evidence appears; it never downgrades after editing just
to avoid review.

The micro lane is a narrow optimization, not a small-diff exemption. It requires
an exact pre snapshot, verification selected by repair content under `review-policy.md`, applicable deletion audit,
`git diff --check`, one immutable acceptance snapshot, and complete orchestrator
inspection before protected staging. It uses zero reviewers. Standard and
high-risk lanes use the two review axes and bounded convergence policy.
