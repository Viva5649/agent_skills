---
name: execute-tickets
description: Implement and verify a feature by executing its prepared implementation tickets in dependency order. Use when the user asks to start or resume a multi-ticket implementation run across one or more repositories. Not for isolated edits without a ticket workflow.
compatibility: Requires Git, Python 3.10+, local Markdown tickets following the bundled contract, sub-agents, and the mattpocock-tdd and mattpocock-code-review skills.
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
`Context boundary`, `Ticket implementation sequence`, `Supervisor status protocol`, `Execution mode routing`, and
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

Start one supervisor without inherited conversation history. Pass absolute
paths and bounded evidence under `supervisor-protocol.md` / Context boundary,
including the verified admission receipt and `admission_basis`. The supervisor
reads its ticket in full and follows Ticket implementation sequence and the
status/mode sections. The orchestrator validates the resulting bounded envelope;
it does not repeat the supervisor's semantic review.

| Decision | Owning reference |
| --- | --- |
| Current authority, slice boundary, scope closure and preflights before `scope_ready` | `references/admission-preflight.md` |
| Implementation, final witness, checks, audits and live-runtime evidence | `references/supervisor-protocol.md` |
| Optional first-pass worker scope and integration | `references/implementation-delegation.md` |
| Affecting outside-scope changes or authorized temporary prerequisite repairs | `references/working-tree-drift.md` |
| Verifier/finding classification, repair and assurance | `references/review-policy.md` and `references/review-mechanics.md` |

A failing ticket-scoped check blocks acceptance, not repair. Missing scope or
literal verifier defects follow the existing authority/verification repair
contracts; the changed verifier cannot approve itself. Material behavior,
interface or owner choices need their authority decision. Keep the same
supervisor and frozen run-start receipt during checkpointed repairs; do not
invoke write review or the commit-oriented `/implement` closeout.

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
  --scope-path <ticket-file-2>
```

Extract exact scope once from the verified ticket and approved discovery
dispositions. Reuse that list through assess, capture and metrics with existing
structured output and subprocess argument arrays; do not regenerate path lists
for each command or add a separate persistent scope ledger.

The first ticket compares `run-start` while creating `pre`; every later ticket replaces that handoff with the prior ticket's `completion/handoff`. The `pre` snapshot freezes HEAD, the index, the complete existing worktree diff, each pre-existing changed file's patch hash, every untracked file hash, restorable content for protected dirty tracked and untracked paths, the approved ticket scope, and every authority content hash. Run-start derives the initial authority set from `--receipt`; later snapshots inherit the current set and hash-bound authority lineage from their handoff or baseline. Do not reintroduce the original path set after a recorded path-set repair. Scope-path content is the ticket's starting candidate; outside-scope content is protected; authority bytes may change only through a recorded verification, execution-authority, or completion transition. Follow `references/working-tree-drift.md` for any handoff change; the clean path reuses the same state collection and adds no repository scan. The supervisor may now implement directly or dispatch bounded implementation workers only after `scope_accepted`.

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
artifacts, `mattpocock-code-review` adaptation, reviewer inputs, separated reports, and
post-review snapshot verification for this index-based workflow.
Before dispatching reviewers, follow `references/review-budget.md`: validate the
intended five-field event with `review_budget.py` against the independent retained
review ledger, then record the actual result after verified reports. Preserve
this feature's budget across pauses and resumes. Statistics never affect execution:
no metrics file, result, count, duration, or command exit code may control dispatch,
repair, staging, completion, or recovery. Record metrics only on a best-effort basis.
Record this review's statistics under `references/run-metrics.md` §Event contract.

### 5. Fix findings without losing the review boundary

The same supervisor owns repairs under `references/review-policy.md`; it
classifies scope relation, authority and repair class before editing. Preserve
frozen findings and route out-of-scope, untouched and authority-blocked results
through that policy. Do not delegate review repairs to a new worker.

Any repository edit invalidates the prior snapshot. Rerun affected verification,
capture `review-N` and provide verified per-path hashes and prior reports under
`references/review-mechanics.md`. Byte-identical production is not re-audited for
a test-only or documentation-only fix; report-only corrections do not require
another snapshot. Closure checks frozen findings, the repair delta and directly
impacted boundaries, not late discovery.

Micro repairs use step 3's verified orchestrator inspection and retain each
finding's `closed-by-micro-inspection` disposition. Non-micro repairs follow the
one discovery, one closure and optional regression-closure budget. Check the
independent review ledger before dispatch; exhausted assurance blocks the ticket
and descendants while independent frontier work may continue serially.
Statistics remain optional. Stage only a candidate with completed assurance.

### 6. Stage the accepted ticket

Bind `final_acceptance_snapshot` to the existing immutable directory used by the
accepted micro inspection or the last passing Standards/Spec round, or its
verified protected-state rebinding under `references/working-tree-drift.md`.
Do not recapture a cosmetically named final snapshot. Immediately before staging,
verify that same snapshot again. Then let the orchestrator stage exactly its
accepted tracked and untracked patches:

```bash
final_acceptance_snapshot=.execute-tickets/<feature>/<ticket>/review-N

python3 <execute-tickets-skill-root>/scripts/review_state.py verify \
  --snapshot "$final_acceptance_snapshot"

python3 <execute-tickets-skill-root>/scripts/review_state.py stage \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --snapshot "$final_acceptance_snapshot" \
  --output .execute-tickets/<feature>/<ticket>/staging
```

The script refuses to stage when HEAD, the index, any snapshot artifact, or the accepted ticket candidate has drifted. It rebuilds a temporary index from the frozen run `HEAD`, applies the frozen cumulative `staged.patch`, then the complete final diffs for ticket-owned tracked and untracked scope paths. It proves that the remaining tracked and untracked worktree content exactly matches the frozen or classified protected outside-scope state, runs `git diff --cached --check`, and only then atomically replaces the live index through an owned index lock. It never copies a mutable live index as the candidate base or passes filenames through Git pathspec matching.

Before verifying the accepted snapshot, follow `references/run-metrics.md`
§Event contract for acceptance timing when metrics are available. After staging:

- Every final tracked or untracked candidate on a ticket-owned scope path must be staged.
- Every tracked unstaged file outside scope must retain its frozen or classified protected state.
- Every untracked file outside scope must retain its frozen or classified protected state and remain untracked.
- `git diff --cached --check` must pass.

Treat the returned index hash, or repository-to-index-hash map, as the accepted-content identity. Do not unlock dependants yet. Close the ticket through the inline completion protocol below, then end the ticket supervisor; the next ticket always gets a fresh supervisor.

The staging output retains the accepted snapshot and its authority lineage.
Reuse the same command/output to recover interrupted staging; it accepts only
the frozen before or after state, never a new baseline inferred from the index.

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
     --snapshot .execute-tickets/<feature>/<ticket>/staging/accepted \
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

When every required gate passes and the index still matches the pre snapshot, the orchestrator uses the same inline completion protocol in step 7, passing that verified empty-scope snapshot to `complete --snapshot` instead of a staging snapshot. A validation-only ticket has no accepted implementation delta, but its `done` status and evidence still enter the durable checkpoint through the atomic completion transition. When such a ticket's own scope declares it the owner of a feature final gate, it runs that gate here under the Final gate protocol below; do not run a second synthetic final gate.

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
of creating a second synthetic final-gate run. During integration discovery,
invoke available `ce-code-review` once under that reference, then close its
blocking findings before feature acceptance. Do not add CE review to individual
tickets. After targeted repair review,
apply the single-owner closeout criteria before scheduling cumulative closure. Do not load or execute that
protocol during ordinary ticket implementation.
