---
name: execute-tickets
description: Implement and verify a feature by executing its prepared implementation tickets in dependency order. Use when the user asks to start or resume a multi-ticket implementation run across one or more repositories. Not for isolated edits without a ticket workflow.
compatibility: Requires Git, Python 3.10+, local Markdown tickets following the bundled contract, sub-agents, and the tdd and code-review skills.
---

# Execute Tickets

Execute one feature's agent-ready tickets serially. Preserve the quality benefit of one fresh context per ticket without requiring the user to open each task manually.

Resolve `<execute-tickets-skill-root>` to this `SKILL.md`'s absolute parent.
Run every bundled script from this root, never from a repository-local path.

## Progressive loading map

The orchestrator may record diagnostic timing under optional `references/run-metrics.md`; statistics are never a prerequisite for resolving inputs or proceeding.

Read the applicable sections when their phase begins. Do not preload later-phase
references merely because the skill triggered. Reuse unchanged sections already
read in this context; after truncation, read only the missing range. Each actor
loads its role and current decision rules, not another role’s full procedure.

| Phase or decision | Applicable sections | Owner |
| --- | --- | --- |
| When the feature names multiple repositories, before the first snapshot or resume | `references/multi-repository.md` | Orchestrator and each ticket supervisor |
| Before a new-run snapshot or resume validation | `references/local-markdown-contract.md`, `references/admission-preflight.md`, `references/run-preflight.md` and `references/review-budget.md` | Orchestrator |
| Before starting each fresh ticket supervisor | `references/supervisor-protocol.md` | Orchestrator and current ticket supervisor |
| Before selecting an assurance lane or classifying a finding | `references/review-policy.md` | Ticket supervisor |
| Before the first standard/high-risk review snapshot or reviewer dispatch | `references/review-mechanics.md` | Orchestrator and ticket supervisor |
| Before delegating first-pass implementation | `references/implementation-delegation.md` | Ticket supervisor and each implementation worker |
| When a protected path drifts, or before comparing ticket handoff state | `references/working-tree-drift.md` | Orchestrator and current ticket supervisor |
| When authority declares `## Reusable gate inputs` or permits historical runtime evidence after repairs | `references/reusable-gates.md` | Final-gate supervisor |
| Only after every implementation ticket is staged | `references/final-gate.md` | Orchestrator and final-gate supervisor |

On resume, load the run-preflight references first, validate the retained
checkpoint, then load only the reference for the phase being resumed. A missing
required execution reference or an unreadable execution contract stops before that phase.
Optional metrics instructions, tools, or data may be absent or unreadable: report
the gap once and continue, including closeout, without repairing or retrying statistics.

This skill combines two layers:

- The main agent is a thin orchestrator. It owns ticket selection, Git snapshot and index integrity, staging, and compact run state.
- One fresh ticket supervisor owns the complete implementation outcome, mode-selected verification, assurance-lane review, and bounded fix loop for exactly one ticket.

After `scope_accepted`, the ticket supervisor may implement directly or delegate
bounded first-pass vertical slices to fresh implementation workers. It remains
the only ticket owner and must integrate the complete delta and run full ticket-
scoped verification itself. Default to one worker; allow two in parallel only
under the bundled independence proof. End all workers before assurance review.
For discovery, the supervisor starts fresh Standards and Spec reviewers in
parallel; closure reuses each original reviewer under `review-policy.md`. The
supervisor fixes findings itself.

## Non-negotiable execution model

Use exactly one existing shared working tree per registered repository and
exactly one ticket supervisor at a time across the whole repository set.

The examples below show the single-repository command form. For a repository
set, apply `references/multi-repository.md` at every phase: qualify file paths,
retain each member's state and patches, and bind review, staging, completion,
and handoff to the aggregate snapshot. Never substitute one member's evidence
for the whole set. The spec/tickets define acceptance; this skill does not infer
build dependencies or add joint acceptance requirements.

Treat Git state as these layers independently in every registered repository:

| Layer | Meaning |
| --- | --- |
| `HEAD` | Fixed repository state from before this execution run |
| Git index | The complete user-staged baseline present before this execution run plus the cumulative accepted implementation output of tickets already accepted in this run |
| Working tree relative to the index | Current-ticket candidates on exact scope paths plus frozen pre-existing edits outside that scope |
| Process documents | The feature spec, admission receipt, and tickets. Content-addressed authority that execution never newly stages; any authority already staged at run-start remains in the frozen user baseline |

The orchestrator is the only actor allowed to change the index. Ticket supervisors, implementation workers, and reviewers must not run `git add`, `git reset`, `git restore --staged`, `git commit`, `git stash`, `git checkout`, or any other command that changes HEAD or the index. Ticket scope, not pre-existing worktree cleanliness, defines which implementation paths the supervisor owns. Existing tracked unstaged or untracked content on an exact scope path joins the ticket candidate. A changed path outside scope that cannot affect the current ticket's implementation, verification, review input, or protected staging remains in the working tree and outside the index; its provenance is not a continuation condition. A worker owns only its assigned exact subset of the accepted ticket scope.

Do not commit. Do not create branches or worktrees. Do not run ticket supervisors in parallel.

## Phase contracts

Before taking the new-run or resume snapshot, follow
`references/run-preflight.md`; it owns required inputs, admission, run-start
identity, independent review-budget initialization, optional metrics, and the ticket-state command contract.

Before each fresh ticket supervisor starts, that supervisor reads the
`Context boundary`, `Supervisor status protocol`, `Execution mode routing`, and
`Assurance lane routing` sections of the `references/supervisor-protocol.md` path
received as a cold-start input.
The orchestrator also reads it before the first supervisor and may reuse its
loaded copy only while the skill package remains unchanged.

## Serial scheduling loop

Repeat until all tickets are completed or a stop condition fires.

### 1. Select one ticket

Build the frontier mechanically: tickets with `**Status:** ready-for-agent` whose listed blockers have `**Status:** done` and an inline completion record.

Select the lowest-numbered frontier ticket unless `execution-plan.md` declares a different blockers-first order. If the frontier is empty while incomplete tickets remain, stop and report the exact unresolved blockers or dependency cycle.

Ticket selection is mechanical. Do not ask the user for permission to follow the
admitted ticket order, continue to the next unique frontier ticket, or run a
conditional ticket whose recorded condition is now true.

Do not mark an implementation ticket completed merely because its supervisor finished. Only the orchestrator can complete it after staging and recording the accepted result. An explicitly validation-only ticket follows the separate completion rule below.

### 2. Declare and assess the ticket scope before implementation

When metrics are available, start `ticket_scope` timing before supervisor dispatch
under `references/run-metrics.md` §Event contract.

Start it without inherited conversation history. Give the supervisor absolute paths to only these cold-start inputs:

1. Applicable repository instructions and relevant standards, when present.
2. The feature spec, verified admission receipt, and bounded `admission_basis`.
3. The current ticket path; the supervisor reads that ticket in full.
4. Compact evidence from the retained integration-review-index rows for the
   current ticket's direct completed blockers: the exact blocker identity and
   ticket hash, only the `Produces` rows consumed by this ticket, the
   accepted-content index hash and completion outcome, and only the
   ordering/ownership evidence cited by those rows. Keep the complete blocker
   ticket path as mismatch fallback, not as a default read input.
5. The repository root, from which the supervisor reads current code and tests as needed.
6. The resolved absolute `<execute-tickets-skill-root>` and the absolute path to
   `references/supervisor-protocol.md`.

Tell the supervisor explicitly:

- Before `scope_ready`, it validates current authority, compact completed-blocker evidence, exact scope, key consumed/produced interfaces, owners, and acceptance feasibility. It reads the relevant production seam and caller declarations needed to decide those boundaries; detailed internal implementation reading happens before editing the corresponding code. It reuses admitted definitions when current evidence agrees, rather than repeating authoring review. It reads a complete blocker ticket only when the compact evidence is missing, internally inconsistent, or disagrees with the current ticket or repository; the resulting mismatch produces `blocked`, not a silently expanded context. It applies the independent-rejection and ordering admission rules, then accounts for every declared non-mutating baseline preflight before `scope_ready`, using the evidence-reuse and proven-shared-prerequisite rules in `admission-preflight.md`. A missing requirement, semantic epic, unresolved ordering/authority conflict, stale `Consumes`/`Produces` interface, unexplained preflight drift, or absent verification seam produces `blocked`; the supervisor does not repair the ticket by inventing a design.
- After all blockers complete, it reruns every exact permitted-discovery command against the current repository, normalizes each result to one repository-relative path, and records every path as `declared-write`, `permitted-write`, `read-only`, or a reasoned `false-positive` in `scope_closure_trace`. A command failure, duplicate or missing disposition, discovered write path absent from `scope_paths`, or any undisposed path produces `blocked` or an execution authority repair before edits. A ticket without permitted discovery records that exact scope needs no discovery replay.
- It selects `direct`, `test-after`, or `tdd` using the execution-mode rules and independently selects `micro`, `standard`, or `high-risk` using `references/review-policy.md`. It then emits `scope_ready` with `ticket_contract: valid`, both routing decisions and evidence, exact verification commands, applicable test seam, and every repository-relative file it may create or modify. Scope entries are exact file paths: directories, globs, and “as needed” entries are invalid.
- It maps every exact scope path to either the ticket's declared write scope or concrete evidence that the path satisfies the ticket's permitted-discovery rule. A path without that trace emits `blocked`. When stable authority outside the proposed repair uniquely proves the missing production or test-only scope, set `blocker_class: authority_backed_ticket_defect` so the orchestrator runs execution authority repair; implementation convenience or a new behavior choice does not qualify.
- When an existing Markdown path is in scope, it validates the ticket's documentation edit contract and carries its `surgical` or explicitly authorized `whole-document` mode in `scope_ready`. Path scope alone never authorizes a whole-document rewrite.
- Its routing reasons distinguish directly observed facts, evidence-backed inferences, and unknowns. Each material inference names the cheapest decisive check within the ticket's authority; an unknown that could change behavior, ownership, an interface, scope, state, or verification produces `blocked`.
- It maps every ticket-scoped check and target-runtime interaction protocol to a named acceptance item and authoritative behavior source. It records each admission preflight in `preflight_trace`, including a completed blocker's exact `Produces` contract when that contract explains an expected baseline difference. After `scope_accepted`, it runs the cheapest decisive check for the highest-risk ticket-backed assumption as early as the selected execution mode permits. It may narrow a command to reproduce or falsify during diagnosis, but that check never replaces a ticket-scoped check, feature final gate, required behavior test, or assurance review.
- For every applicable correctness-critical acceptance item, it checks the
  admitted witness against current seam/blocker changes and replays declared
  non-mutating probes. `verification_witness_trace` references unchanged
  producer/fixture/oracle definitions and reports differences and probe results;
  it does not redesign every fixture before implementation. An illegal fixture, unreachable boundary,
  incomplete oracle, weak proxy, or false-green command produces `blocked`
  before edits; it is not repaired as a mechanical verifier typo.
- For browser, desktop UI, device, or live-app acceptance, it forms the exact interaction hypothesis from the ticket before controlling the tool, exercises the declared real target-runtime path, refreshes or resets stale state, and records `runtime_observations` that distinguish the result from a mock, cache, screenshot-only state, forced state, or stale renderer. Builds, tests, logs, and screenshots are supporting evidence, not substitutes. Follow the first-failure capture and bounded diagnosis rules in `supervisor-protocol.md` before retrying. If the required runtime is unavailable, it follows the ticket's stop/report condition instead of claiming the path passed.
- For ticket-declared `adb` real-device verification, it runs `adb devices -l` first. If an eligible physical device is in state `device`, it executes the ticket's bounded verification directly without a conversational permission request. It may install, replace, or uninstall the exact APK/package produced or used by the current ticket, including the normal removal of that package's data caused by uninstall. It may also use the ticket-specific `/data/local/tmp/...` directory, push the declared test artifacts, set their required execute permissions, run the exact cases, and retain exit codes and output. The APK/package may be resolved mechanically from the ticket, build output, or manifest. If multiple devices qualify and the ticket names no serial, select the lexicographically first serial unless authority requires all of them. Emit `blocked` with `blocker_class: evidence_unavailable` only when no eligible physical device is usable. This lane does not authorize operations on unrelated applications, direct `pm clear` or other application-data changes, system-setting changes, unrelated device paths, root/remount/reboot, credentials, or external services.
- Before `scope_accepted`, it may run only the ticket's exact non-mutating admission preflights. It does not edit, run post-implementation ticket verification, or begin review until the orchestrator returns `scope_accepted`.
- It is the sole ticket owner for implementation outcome, ticket-scoped verification, assurance-lane review, and review fixes, but not scheduling, Git snapshots, or staging. After `scope_accepted`, it may delegate only first-pass vertical slices under `references/implementation-delegation.md`.
- If it delegates, it receives the resolved absolute path to `references/implementation-delegation.md`, reads it in full before dispatch, and passes that same path to every worker.
- It follows the selected execution mode; only `tdd` uses the `/tdd` loop, and only at a production seam already established by the ticket or spec. The loop covers a stable acceptance behavior, not every internal edit; apply the behavior-unit rules in `references/supervisor-protocol.md`.
- Before editing directly, it must read exports, immediate callers, and shared utilities. Every delegated worker performs the same read for its package paths.
- It must keep all changes within the current ticket.
- If it notices a changed path outside the accepted ticket scope, it first checks whether that path can affect the current ticket's implementation, verification, review input, interface, state/resource owner, or protected staging. If not, it leaves the path outside scope and the index and continues without investigating who changed it. It emits `drift_detected` and stops writing only when the path can affect the ticket or safe isolation cannot be proved; the orchestrator then follows `references/working-tree-drift.md`.
- It must run only the ticket-scoped checks, any deletion audit required by applicable repository instructions, and the bundled Markdown document-deletion audit when applicable. It must not run a feature final gate during ordinary ticket implementation.
- It must leave candidate changes unstaged.
- It must keep raw command output in the ignored run-artifact tree and report through the bounded status envelopes.
- Before `implementation_ready`, it must end every worker, verify each actual changed path is inside that worker's assigned exact subset, inspect the complete worker deltas, integrate their boundaries, and personally run the complete ticket-scoped checks, deletion audit, and required target-runtime interaction.
- Before `implementation_ready`, it must run a delta self-check against the recurrent self-inflicted review findings: existing behavior-bearing code deleted without a ticket requirement (for example a removed disable or guard call), parameters or branches with no production caller, and assertions that also pass when the probed condition is false (for example an already-released reference reported as a successful probe). Each hit is repaired before review dispatch. The self-check narrows the finding stream; it never replaces or shortens a review lane.
- Before `implementation_ready`, it must rebuild each correctness-critical `verification_witness_trace` against the final candidate as a legal-fixture/oracle matrix. Each behaviorally distinct legal input, race, or success no-op required by acceptance names its actual fixture, complete oracle, direct observation and retained log, with shared applicable absence evidence referenced under `admission-preflight.md`; a planned witness copied from `scope_ready` or one broad fixture standing in for distinct legal branches is invalid. Apply `references/review-policy.md` when the final implementation structurally eliminates a failure path; do not manufacture a fixture for a removed mechanism.
- Before `implementation_ready`, if existing Markdown changed, it must write and hash `.execute-tickets/<feature>/<ticket>/document-deletion-audit.md`, reconcile every deleted or wholly replaced heading section and fenced code block as `replaced` or `superseded`, and block on a missing, mixed, or unexplained unit. The exact audit contract lives in `references/supervisor-protocol.md`.
- It must emit `implementation_ready` and wait for the orchestrator to capture the assurance snapshot. A worker PASS or focused check never substitutes for this state.
- For standard/high-risk discovery it must spawn the two fresh read-only reviewers itself; closure continues the original per-axis reviewers after receiving the reviewer-content artifact paths and verified snapshot identity—never orchestrator-only integrity artifact bodies—and while no implementation worker is active. For micro assurance it waits while the orchestrator inspects the frozen delta and never spawns reviewers.
- After review begins, it must classify and fix actionable in-scope findings itself; it must not reconstruct the frozen finding set in a new implementation worker.
- It must stop if the ticket requires changing a completed blocker's contract or an out-of-scope lifecycle/state owner.

A failing ticket-scoped check blocks acceptance, not repair. The supervisor fixes an implementation defect within scope, or autonomously repairs a test, fixture, regex, scan, or verification command that mechanically contradicts an explicit authoritative expected result, then reruns the affected check. It asks the user only when observable behavior or authority is genuinely undefined or conflicting. When the defective verifier is literal text in the current ticket, the orchestrator follows the bundled verification-only contract repair, records that correction as an approved authority transition instead of staging it, captures a new ticket baseline, and continues without user approval.

When the same authority-backed defect requires an exact path or ticket field that
the current contract omitted, follow execution authority repair in
`references/admission-preflight.md`. The current supervisor supplies the exact
correction from its live code context; the orchestrator records a bounded
authority transition, keeps the run-start receipt unchanged, and resumes the
same supervisor without invoking write or an authoring reviewer. The changed
verifier cannot be its own only authority. An authority-backed ticket split may
change only unfinished ticket paths; the orchestrator retains the current ticket
path, records every added/removed path in the same transition, and continues the
active run without replacement admission.

That bounded repair never legalizes fake-only input, changes a reachable
boundary, removes an authority-permitted oracle outcome, substitutes a weaker
observation, or accepts a check that cannot detect missing evidence. Those are
acceptance-contract defects and require an execution authority repair or a
material decision; they never recurse into write review.

Do not ask the supervisor to run the commit-oriented `/implement` closeout verbatim: its commit step and default `/code-review` diff are incompatible with this no-commit execution model. The supervisor produces the implementation directly or through bounded workers using the selected execution mode, integrates it, then uses the working-tree review protocol below.

Before running the deterministic scope assessment, the orchestrator rejects a `scope_ready` envelope unless the current ticket contract is valid, both routing decisions are supported, every permitted-discovery command was replayed with `0 undisposed paths`, every scope path has a declared-scope or permitted-discovery trace, and every verification command or interaction protocol traces to a ticket acceptance item and authoritative source. The orchestrator does not approve scope expansion merely because implementation would be easier with another file. It does run execution authority repair when stable accepted authority and current repository evidence uniquely prove a behavior-preserving omission.

The orchestrator then runs the deterministic scope assessment. It reports which
exact tracked unstaged and untracked paths become ticket-owned; overlap is not a
user decision and does not stop implementation. Only pre-existing paths outside
the accepted scope retain protected worktree ownership.

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py assess \
  --scope-path <ticket-file-1> \
  --scope-path <ticket-file-2>

python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --output .execute-tickets/<feature>/<ticket>/pre \
  --handoff .execute-tickets/<feature>/run-start \
  --drift-output .execute-tickets/<feature>/<ticket>/handoff-drift \
  --scope-path <ticket-file-1> \
  --scope-path <ticket-file-2> \
  --receipt "<spec-dir>/implementation-ticket-admission.json"
```

Extract exact scope once from the verified ticket and approved discovery
dispositions. Reuse that list through assess, capture and metrics with existing
structured output and subprocess argument arrays; do not regenerate path lists
for each command or add a separate persistent scope ledger.

The first ticket compares `run-start` while creating `pre`; every later ticket replaces that handoff with the prior ticket's `completion/handoff`. The `pre` snapshot freezes HEAD, the index, the complete existing worktree diff, each pre-existing changed file's patch hash, every untracked file hash, restorable content for protected dirty tracked and untracked paths, the approved ticket scope, and every authority content hash. `--receipt` derives the exact authority path set from the verified run-start receipt — the spec, the receipt itself, and every ticket — so execution cannot silently add authority files. Scope-path content is the ticket's starting candidate; outside-scope content is protected; authority bytes may change only through a recorded verification, execution-authority, or completion transition. Follow `references/working-tree-drift.md` for any handoff change; the clean path reuses the same state collection and adds no repository scan. The supervisor may now implement directly or dispatch bounded implementation workers only after `scope_accepted`.

Once required scope checks and the pre snapshot pass, send `scope_accepted`
immediately. When metrics are available, record `ticket_scope` and follow
`references/run-metrics.md` §Event contract for implementation and ticket-check
statistics; statistics must not keep the supervisor waiting.

### 3. Capture the current-ticket assurance input

After the supervisor emits `implementation_ready`, with every implementation
worker ended and the full ticket checks complete, the orchestrator captures an
immutable assurance snapshot against the pre-ticket baseline:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --output .execute-tickets/<feature>/<ticket>/review-1 \
  --baseline .execute-tickets/<feature>/<ticket>/pre
```

The command fails when the supervisor changed HEAD or the index. When it detects ordinary tracked or untracked drift outside scope, the orchestrator first checks whether the path can affect the current ticket. A harmless path is automatically preserved as protected external state, excluded from the ticket delta/index, and the capture is retried with the resulting `--drift-resolution`; this is internal bookkeeping, not a workflow pause, and requires no provenance investigation. Only an affecting or non-isolatable path pauses through `references/working-tree-drift.md`. Existing scope-path content may change and its complete final diff enters the assurance snapshot.

For a ticket that changed existing Markdown, the orchestrator also verifies the
reported document-deletion audit path/hash and supplies it as reviewer content.
The audit is evidence about deleted responsibilities; it does not replace the
complete patch or the ticket's positive documentation acceptance.

For micro assurance, the orchestrator now inspects the complete patch and checks,
revalidates every micro eligibility condition in `references/review-policy.md`,
verifies the snapshot, and either accepts it or escalates the lane. It does not
start reviewers. On acceptance it returns `micro_input_valid`; that verified
inspection is the acceptance evidence, and the orchestrator proceeds directly to
protected staging. Standard and high-risk assurance continue below.

### 4. Run assurance-lane code review

Skip this section for an accepted micro snapshot.
Follow `references/review-mechanics.md` exactly. It defines the immutable
artifacts, `/code-review` adaptation, reviewer inputs, separated reports, and
post-review snapshot verification for this index-based workflow.
Before dispatching reviewers, follow `references/review-budget.md`: validate the
intended five-field event with `review_budget.py` against the independent retained
review ledger, then record the actual result after verified reports. Preserve
this feature's budget across pauses and resumes. Statistics never affect execution:
no metrics file, result, count, duration, or command exit code may control dispatch,
repair, staging, completion, or recovery. Record metrics only on a best-effort basis.
Record this review's statistics under `references/run-metrics.md` §Event contract.

### 5. Fix findings without losing the review boundary

The same supervisor classifies every finding before editing, using all three axes
from `references/review-policy.md`:

```yaml
scope_relation: current_delta | repair_regression | untouched_existing | out_of_scope
authority_status: authority_backed | authority_blocked
repair_class: micro | non_micro
```

`review-drift` is the disposition of an `out_of_scope` finding, not an authority
classification. Follow the disposition table in `references/review-policy.md`:
drift preserves frozen reports and records corrections in the existing disposition; blocked authority stops;
authorized current-delta defects and repair regressions are fixed autonomously;
untouched P0/P1 blocks, while untouched P2/P3 becomes backlog.
The supervisor performs every authorized ticket-review repair itself. It does
not dispatch an implementation worker after review has begun.

Any repository edit invalidates the prior snapshot. Rerun affected verification
and capture `review-N`; supply prior passing reports plus exact per-path hashes so
reviewers inspect only changed paths and boundary interactions. Do not re-audit
byte-identical production for a test-only or documentation-only fix. A
report-only drift correction needs neither tests nor a new snapshot.

A closure is not a second discovery. A new `repair_regression` must cite the
repair hunk, its directly impacted boundary, explicit frozen authority, and a
counterfactual showing that removing the repair delta removes the defect. If the
same defect exists in the discovery snapshot, it is late discovery and cannot
be opened in closure. An authority-free stronger proof is `review-drift` or
`authority_blocked`, not an automatic repair.

When the supervisor and orchestrator accept `repair_class: micro`, use the
micro snapshot path from step 3 for that repair: select checks by repair content under `review-policy.md`, perform the applicable deletion audit, capture and verify the snapshot, and let the
orchestrator inspect it. Do not dispatch either reviewer. If inspection finds a
micro disqualifier, escalate the repair class before any closure dispatch.
For an accepted micro repair, retain each frozen finding ID, explicit authority,
repair snapshot hash, and checks with disposition `closed-by-micro-inspection`.
A finding that still needs Standards or Spec judgment is not micro.

Non-micro ticket review uses one discovery review, one closure review, and at most one
regression closure. Review 1 freezes the finding set; later rounds inspect only
unresolved findings, the repair delta, immediate regressions, and directly
impacted boundaries. If Review 3 still lacks assurance, block the unresolved
ticket, preserve evidence, and continue independent frontier work serially.
Before repair, follow `references/run-metrics.md` §Event contract for its timing
and `repair` event when metrics are available.

Do not stage a candidate that has not completed its required assurance lane.

### 6. Stage the accepted ticket

Bind `final_acceptance_snapshot` to the existing immutable directory used by the
accepted micro inspection or the last passing Standards/Spec round. Do not
recapture a cosmetically named final snapshot. Immediately before staging,
verify that same snapshot again. Then let the orchestrator stage exactly its
accepted tracked and untracked patches:

```bash
final_acceptance_snapshot=.execute-tickets/<feature>/<ticket>/review-N

python3 <execute-tickets-skill-root>/scripts/review_state.py verify \
  --snapshot "$final_acceptance_snapshot"

python3 <execute-tickets-skill-root>/scripts/review_state.py stage \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --snapshot "$final_acceptance_snapshot"
```

The script refuses to stage when HEAD, the index, any snapshot artifact, or the accepted ticket candidate has drifted. It rebuilds a temporary index from the frozen run `HEAD`, applies the frozen cumulative `staged.patch`, then the complete final diffs for ticket-owned tracked and untracked scope paths. It proves that the remaining tracked and untracked worktree content exactly matches the frozen or classified protected outside-scope state, runs `git diff --cached --check`, and only then atomically replaces the live index through an owned index lock. It never copies a mutable live index as the candidate base or passes filenames through Git pathspec matching.

Before verifying the accepted snapshot, follow `references/run-metrics.md`
§Event contract for acceptance timing when metrics are available. After staging:

- Every final tracked or untracked candidate on a ticket-owned scope path must be staged.
- Every tracked unstaged file outside scope must retain its frozen or classified protected state.
- Every untracked file outside scope must retain its frozen or classified protected state and remain untracked.
- `git diff --cached --check` must pass.

Treat the returned index hash, or repository-to-index-hash map, as the accepted-content identity. Do not unlock dependants yet. Close the ticket through the inline completion protocol below, then end the ticket supervisor; the next ticket always gets a fresh supervisor.

### 7. Append the completion record and close the ticket

The orchestrator performs this step only after the implementation ticket's accepted content has been staged and the post-stage invariants above pass. The supervisor has ended its write phase and no reviewer is active.

1. Prepare the bounded completion record in the ignored run-artifact tree, then
   run the single atomic completion transition. The command freezes an internal
   baseline, appends the record, performs `ready-for-agent -> done`, proves that
   `HEAD`, the index, the working tree, and every other authority file are
   byte-identical while the current ticket actually changed, and retains the
   before/after content hashes as durable evidence. It must print `done`:

   ```bash
   python3 <execute-tickets-skill-root>/scripts/ticket_state.py complete \
     --tickets-dir "<tickets-dir>" \
     --ticket "<tickets-dir>/<ticket>.md" \
     --record-file .execute-tickets/<feature>/<ticket>/completion-record.md \
     --receipt "<spec-dir>/implementation-ticket-admission.json" \
     --output .execute-tickets/<feature>/<ticket>/completion
   ```

2. Do not stage this transition. `review_state.py stage` refuses to newly stage
   any declared authority path; authority already staged at run-start remains
   unchanged in the frozen user baseline. The retained
   `completion/completion.json` records the transition's before/after SHA-256
   pair and a `completion/handoff/` snapshot from the transition's existing
   post-state collection as durable completion evidence. A failed proof restores
   the exact pre-transition ticket bytes and stops with the ticket incomplete.

The completion record distinguishes implementation/staging, acceptance, and
   delivery facts under `references/final-gate.md`, with evidence references and
   exact user dispositions. It is not a second copy of gate results.

3. Run `ticket_state.py show` and require exact output `done`. Require `git diff --cached --check` to pass. Verify that the ticket contains exactly one completion record naming the same accepted-content index hash and the passing assurance outcome. A ticket that began in micro says both review axes were not required; a post-review micro repair retains the prior reports and records each frozen finding's `closed-by-micro-inspection` disposition and repair snapshot instead of relabelling the prior reports as PASS.
4. Append exactly one compact row for the accepted ticket to
   `.execute-tickets/<feature>/integration-review-index.md`. Build it from
   the current ticket and retained bounded envelopes while they are already in
   context; do not reread prior ticket or report bodies. The row records ticket
   path/hash, accepted-content index hash, accepted path hashes, cross-ticket
   `Consumes`/`Produces`, shared state/resource/cleanup owners and ordering rows,
   review outcome/report path/hash, deviations, and owned final-gate declarations.
   Verify the row against retained artifacts and record the new index SHA-256.
5. Only after all checks and the compact-row append pass does the orchestrator
   add the ticket to the completed set and allow its dependants into the
   frontier. If any write, approved authority transition, index-row append, or
   verification fails, stop with the ticket incomplete; do not unlock
   dependants.

6. Record the ticket's `ticket_result` event before selecting another frontier
   ticket. A blocked ticket also receives a result event before its descendants
   remain blocked.

The inline record is orchestration metadata, not part of the production review input. The retained transition evidence proves that this post-review delta contains only the status transition and its bounded evidence, and that it never reached the accepted baseline.

### 8. Complete an explicitly validation-only ticket

A ticket is validation-only only when its own scope explicitly requires an empty production/test/build/public-documentation change set, such as a `Final Audit` ticket. Do not infer this classification merely because a supervisor happened to make no changes.

For a validation-only ticket:

1. Capture its pre snapshot from the current cumulative index.
2. Start a fresh read-only ticket supervisor to run the ticket's audits and its uniquely owned feature final gates.
3. Let that supervisor follow the final-gate protocol when it owns the same
   feature final gate: reviewers read the verified integration-review index
   first and receive the cumulative `staged.patch` and historical reports only
   as on-demand evidence paths. A validation-only ticket that does not own that
   gate follows its own explicitly declared review inputs.
4. Verify the pre snapshot still matches HEAD, index, working tree, and pre-existing untracked files.
5. Record the commands, exact results, review findings, and unchanged index hash.

When every required gate passes and the index still matches the pre snapshot, the orchestrator uses the same inline completion protocol in step 7. A validation-only ticket has no accepted implementation delta, but its `done` status and evidence still enter the durable checkpoint through the atomic completion transition. When such a ticket's own scope declares it the owner of a feature final gate, it runs that gate here under the Final gate protocol below; do not run a second synthetic final gate.

### 9. Stop conditions

Route every pause, single-ticket block, or whole-run stop through these six
cases:

- **A ticket-scope-outside change can affect the current ticket.** Preserve an
  unrelated path outside the ticket delta/index and continue without
  investigating who changed it. Pause through
  `references/working-tree-drift.md` only when the path can affect
  implementation, verification, review input, an interface or state/resource
  owner, or protected staging, or when safe isolation cannot be proved.
- **The ticket contract cannot be executed uniquely and safely.** This includes
  multiple reasonable behavior/owner/interface/runtime answers, hidden context,
  a semantic epic, an unrealizable or incomplete verification witness, an
  untraceable write path, a stale `Consumes`/`Produces` interface, or a required
  completed-blocker/other-owner change. When current authority uniquely proves a
  behavior-preserving correction, run execution authority repair and resume the
  same ticket. Ask only when the correction needs a new material decision.
- **Implementation checks or assurance review cannot converge within their
  bounded repair budget.** This includes an exhausted ticket-scoped check,
  implementation-worker ownership breach, an uncloseable review finding, or a
  regression closure without required assurance or convergence progress. Block
  the affected ticket and descendants, retain the exact failure evidence, and
  continue only genuinely independent frontier tickets. A new run-start or
  artifact directory does not reset this terminal review evidence.
- **Ticket-declared `adb` real-device evidence is unavailable.** Run
  `adb devices -l` first. With an eligible physical device in state `device`,
  execute the bounded install/replace/uninstall or push/run verification lane
  directly without asking. Only the absence of a usable physical device emits
  `blocked` with `blocker_class: evidence_unavailable`; resume that gate when a
  device becomes usable.
- **The execution baseline or recovery evidence cannot be trusted.** This
  includes unexplained `HEAD`/index/authority changes, missing or mismatched
  spec/ticket/receipt bytes, unattributable review-input drift, a missing or
  mismatched checkpoint/integration-review-index row, or an execution authority
  repair whose old bytes cannot be proved restored. Recover automatically when
  retained checkpoint and hash evidence determine one exact state. Otherwise
  stop the whole run rather than accepting or executing unproved content.
- **The next action exceeds current ticket authority.** Do not perform an
  unrelated application or device operation, direct application-data or system
  setting change, root/remount/reboot, credential access, external-service
  call, destructive or irreversible action, or Git-history rewrite without
  explicit authority. The ticket-declared bounded `adb` lane above is already
  authorized and is not part of this case.

A stop or pause is a state classification, not automatically a permission
request. The orchestrator continues the next unique frontier ticket, reconciles
classifiable working-tree drift, applies contract-backed verifier repair, and
runs execution authority repair without asking and without calling write. It asks only at the material
decision boundary defined in `references/review-policy.md` or when required
evidence/authority cannot be obtained inside the authorized execution model.
Missing files, tests, commands, scope entries, or verification text that current
authority uniquely determines are automatic repair inputs, not additional stop
cases and not permission questions.

After one ticket blocks, continue other frontier tickets by default when their
blockers, contracts, interfaces, and state owners are genuinely independent. An
execution plan may explicitly forbid that continuation. Execution remains
serial; never use continuation to edit the blocked ticket's owner indirectly.
When no independent frontier remains, record the blocked ticket/final result and
attempt the optional metrics summary when its log is valid, without delaying the stop.
If metrics are incomplete, report that gap alongside the execution outcome. Metrics explain
workflow cost; they do not soften the blocker or turn incomplete acceptance into
success.

## Final gate

Only after every implementation ticket is staged, read
`references/final-gate.md` in full and follow it. An explicitly
validation-only ticket that owns the same final gate uses that protocol instead
of creating a second synthetic final-gate run. After targeted repair review,
apply the single-owner closeout criteria before scheduling cumulative closure. Do not load or execute that
protocol during ordinary ticket implementation.
