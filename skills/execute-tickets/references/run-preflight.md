# Run preflight protocol

Read this file in full before a new run's Git snapshot or before validating a
resume checkpoint. It owns required-input resolution, run admission, the
run-start snapshot, metrics initialization, and the ticket-state command
contract. Do not read final-gate instructions during this phase.

## Required inputs

For multiple repositories, first apply `multi-repository.md`: resolve and freeze
the feature's explicit repository set, protect each existing worktree/index, and
use an aggregate run-start snapshot. Keep admission and process documents in
their owning repository. The singular Git checks below apply to every member;
the run-start identity binds all members, including currently read-only ones.

Before execution, the orchestrator resolves:

1. The bundled `references/local-markdown-contract.md`, which owns the tracker layout,
   lifecycle, blocker acceptance, and minimum cold-start contract.
2. The target repository root and every applicable governing instruction, including any `AGENTS.md`.
3. The spec and ticket directories declared by `docs/agents/issue-tracker.md`,
   resolved through the bundled contract before locating feature files. Only
   without that document, use `.spec/<feature>/` and `.spec/<feature>/issues/`.
   Read `<spec-dir>/spec.md`, `<spec-dir>/implementation-ticket-admission.json`,
   and every ticket under `<tickets-dir>/` with scheduling metadata.
4. Relevant standards, domain documentation, ADRs, and repository tracker
   documents when present. Tracker documents are optional compatible overlays;
   their absence does not block. A conflict stops before Git state changes.
5. The user's explicit authorization to stage each accepted ticket. Staging changes the index but not Git history; never infer authorization when the user has not requested this execution model.

If an `execution-plan.md` exists, read it. It may add hard gates and stop conditions, but it must not silently replace the tickets' `Blocked by` edges.

## Preflight

Before a new run's Git snapshot or first ticket selection, run the bundled
`admission_state.py verify` command from `references/admission-preflight.md` and
require exact output `admitted-by-review` or `admitted-by-user`. Preserve that
value and any user dispositions as `admission_basis`; the orchestrator never
generates a receipt itself. That receipt is verified only at new run-start and
remains unchanged for the active run. On resume after checkpointed completion,
bounded verification repair, or execution authority repair changed declared
authority bytes, validate the original receipt plus retained before/after
transitions instead of re-entering write review or reconstructing admission from
prose.

The orchestrator performs these checks before starting a supervisor:

1. Record `git rev-parse HEAD`. HEAD must remain unchanged for the entire run.
2. For a new run, the orchestrator treats every path already staged by the user, including any process-document authority path, as part of this feature's accepted baseline, captures the complete index, and does not restrict staged paths to the feature spec tree or ask the user to classify them again. Execution never newly stages process documents, but it preserves this frozen user baseline. An empty index also satisfies this check. When resuming, the orchestrator requires the retained `.execute-tickets/<feature>/...` checkpoint to prove the exact staged diff belongs to this run; otherwise stop and ask the user.
3. Capture pre-existing tracked unstaged edits as file-level patch hashes and retain the protected working-copy content needed for exact restoration. An exact path accepted into the selected ticket's scope becomes ticket-owned and its complete final diff enters review; paths outside scope retain their frozen or later classified protected state.
4. Capture pre-existing untracked paths, content hashes, and restorable content. An exact path accepted into ticket scope becomes ticket-owned and is staged only after assurance; paths outside scope retain their frozen or later classified protected state and remain untracked. Require this feature's `spec.md`, admission receipt, and every implementation ticket to match the verified receipt at new run-start. On resume, require the unchanged run-start receipt plus retained completion/repair transitions to explain every later authority byte. Those process documents may be tracked, untracked, or excluded by `.gitignore`; a missing, unreadable, or unexplained authority file stops admission. Never require them to be tracked or staged.
5. Parse every ticket's exact `**Status:**` and `Blocked by` fields. Treat `done` as completed only when the same ticket file contains exactly one readable `## Completion record`. Select only `ready-for-agent`, and reject missing fields, duplicate ticket numbers, and cycles.
6. After selecting the current ticket, resolve its cold-start contract fields or unique section/check references. The supervisor owns current-code feasibility; the orchestrator checks evidence identity and reported gaps, not a duplicate semantic review. Confirm that the contract names the authoritative and superseded inputs, production owner, exact declared write scope or bounded discovery rule, slice-boundary proof, cross-ticket interfaces, behavior contract, applicable ordering/ownership decision, non-goals and state budget, acceptance sources, stable verification seam or direct check, every applicable verification witness, baseline verification preflight and applicable absence evidence under `admission-preflight.md`, ticket-scoped checks, uniquely owned feature final gates, reuse assessments, and stop conditions. A bug or regression also names its reproduction, evidence-backed causal model, falsifying check, and re-diagnosis condition. Target-runtime UI or live-app acceptance also names its exact interaction path, freshness action, and authenticity evidence. Apply `references/admission-preflight.md`; a semantic epic, missing ordering row, unrealizable verification witness, duplicate gate ownership, or stale preflight blocks before implementation. Do not let the supervisor reconstruct missing requirements from code, and do not preload future ticket bodies to perform this check.
7. Resume only from the retained immutable run-start snapshots and completion
   transition evidence plus the hash-valid integration-review-index rows under
   `.execute-tickets/<feature>/...`. Do not create a repository
   execution-state file, and do not accept one as completion evidence.
8. When the repository uses Gradle, probe `./gradlew --version` once in the same execution environment intended for gates. If the probe fails only because the sandbox cannot create Gradle cache/lock files, obtain the approved Gradle execution environment once and reuse it for this run. Do not count the sandbox-only probe as a gate attempt or rediscover the same permission failure in every supervisor.

On resume, compare the current repository with the latest verified handoff;
validate older checkpoints as historical authority transitions, not as snapshots
that should equal today's index. Reuse the orchestrator's verified results in
the supervisor handoff. Include the resolved command working directory and any
already authorized execution environment; a fresh supervisor must not repeat a
known sandbox-cache failure. New permissions still require their own authority.
Record new-run preparation or resume elapsed time as an optional `run_phase`
event under `run-metrics.md`, without delaying the next supervisor/action dispatch. If
preflight blocks before ledger initialization, retain that event in the existing
run-artifact tree and report its measured time without inventing a run-start.

## Known external blocker recovery

When a retained blocker record or checkpoint shows a known external dependency
(device, service, credential, or user-selected target), the orchestrator reads
the recorded failure reason, target, authorized commands, and exact recovery
condition before re-dispatching that ticket's full admission. It performs only
the smallest authorized external recovery check from that record: whether the
required device is available, whether the declared endpoint has the necessary
reachability, or whether the user has supplied the replacement device/address
decision or new credential authorization. It does not duplicate the supervisor's
code-feasibility review.

If the condition is unchanged, keep the ticket blocked with its evidence and
continue independent frontier work; do not re-dispatch a supervisor to reread the
same code, and do not add a polling service. When the condition is verified
recovered, hand that stage to the owner that resumes it and still complete the
retained checkpoint, authority, workspace, and required-check verification; a
successful external probe is not a behavior acceptance PASS. Consume a user
device/address change through the existing authority process first: record the
decision, then run the same minimal recovery check against the new target. A
recorded decision does not substitute for actual availability of the relied-upon
conditions, so do not resume full admission before the new target is checked.
After a rejected credential operation, do not retry or use an alternate channel
without new valid authorization; prior-target evidence cannot replace new-target
evidence. A new run without a known external blocker follows the normal flow; do
not add a global environment preflight.

## Run-artifact tree

This run keeps every snapshot, log, patch, report, metrics event, and checkpoint
in one durable run-artifact tree at `.execute-tickets/<feature>/...`.

Git must exclude that tree. Before the first capture, require
`git check-ignore --quiet .execute-tickets` to succeed. The bundled scripts
enforce the same rule and refuse to write an in-repository artifact path that Git
does not ignore, because an unignored artifact would be collected as untracked
scope content and could reach the index.

If the path is not yet ignored, add it to `.git/info/exclude`, which is local to
the clone and changes no tracked file. Do not edit a tracked `.gitignore` to
satisfy this requirement, because that is a production change outside every
ticket scope. If the user forbids both, use an absolute path outside the
repository for the whole run and keep it identical across resume.

The tree is orchestration state, never a deliverable. It holds no authority: the
spec, receipt, and tickets remain the only authority, addressed by content hash.

Use the bundled state tool for steps 1–4. Store snapshots in that ignored
run-artifact tree so the snapshots cannot become ticket changes:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --output .execute-tickets/<feature>/run-start \
  --receipt "<spec-dir>/implementation-ticket-admission.json"
```

Use this exact `run-start` snapshot as the first ticket's `--handoff` while
creating its `pre` snapshot. Every later ticket uses the prior ticket's
`completion/handoff`; `references/working-tree-drift.md` owns both comparisons.

`--receipt` derives the exact authority set from the verified admission
receipt: `spec.md`, the receipt itself, and every recorded ticket path. The
check records each path's SHA-256 and rejects a missing or unreadable authority
file, and the derived set can never disagree with what admission verified. It
does not require Git to track these process documents. Carry the same authority set
through every later capture so any unapproved authority edit is detected as
drift. `staged.patch` may be empty or contain any documentation, code,
configuration, or spec content that the user staged
before the run. The run-start snapshot freezes that complete baseline, every
ticket snapshot preserves it, and the final gate reviews it as part of the
cumulative staged patch. `unstaged.patch` is the immutable pre-existing
working-tree baseline. Protected dirty tracked and untracked content needed for
restoration is retained in `backups.json` and content-addressed `blobs/`.
Pre-existing untracked files are recorded in `untracked.json`; a `.gitignore`-excluded process document appears in neither
manifest and is governed only by its recorded authority hash. When
resuming, use the retained temporary checkpoint to account for the exact staged
accepted-ticket output, and keep the same receipt-derived authority check.

After a new run-start capture succeeds, initialize or recover the independent
`.execute-tickets/<feature>/review-budget.jsonl` under `references/review-budget.md`.
The orchestrator retains its verified execution history across resumes and new
run-start identities; exhausted budgets cannot be reset by another artifact path.
Legacy recovery uses review reports, repair dispositions, and integration evidence,
never metrics. Separately attempt metrics initialization/continuation under
`references/run-metrics.md`; any statistics failure marks metrics incomplete and
execution continues. Missing metrics never block resume.

Also initialize
`.execute-tickets/<feature>/integration-review-index.md` with the feature and
run-start identity. The orchestrator appends one compact ticket row only after
that ticket's accepted implementation content is staged and its completion transition
is verified. The completion record is authority metadata and is never newly staged.
It uses the current ticket and retained bounded envelopes already in context;
it never reconstructs the row by loading prior complete ticket or report
bodies. On resume, require the index to contain exactly one hash-valid row for
each checkpointed completed ticket and no row for an incomplete ticket.

## Inline completion record

After protected implementation staging succeeds, render the exact bounded record
defined by the bundled contract to
`.execute-tickets/<feature>/<ticket>/completion-record.md`. The record proves
acceptance but cannot change behavior; raw logs, patches, snapshots, and reviewer
reports remain in the ignored run-artifact tree. For the next ticket, select compact evidence only
from its direct completed blockers' retained integration-review-index rows:
exact blocker path/hash, consumed verbatim `Produces`, accepted-content index
hash and completion outcome, and cited ordering/ownership rows. Preserve the
complete blocker ticket as mismatch fallback, but do not make its full body a
normal cold-start input.

Use the ticket numbers and project terminology exactly. Do not invent aliases for domain actors or states.

## Implementation ticket states

The bundled `references/local-markdown-contract.md` is authoritative for directory
resolution, the `ready-for-agent -> done` lifecycle, transition owner, and
blocker-acceptance rule. Use the bundled deterministic state command instead of
editing the Markdown status freehand:

```bash
python3 <execute-tickets-skill-root>/scripts/ticket_state.py show \
  --tickets-dir "<tickets-dir>" \
  --ticket "<tickets-dir>/<ticket>.md"

python3 <execute-tickets-skill-root>/scripts/ticket_state.py complete \
  --tickets-dir "<tickets-dir>" \
  --ticket "<tickets-dir>/<ticket>.md" \
  --record-file .execute-tickets/<feature>/<ticket>/completion-record.md \
  --receipt "<spec-dir>/implementation-ticket-admission.json" \
  --output .execute-tickets/<feature>/<ticket>/completion
```

Require exact output `done`. Any invalid transition, malformed status field, or
path outside the bundled layout stops completion. The tool never requires the
ticket to be tracked by Git.

These records are orchestration metadata, not production output. Do not modify them between a ticket's pre snapshot and successful staging because that would change the frozen ticket boundary. Keep interim review results in the ignored run-artifact tree and update the records after the ticket is staged. The completion transition retains `completion/handoff/` from its existing post-state collection; combine that comparison with the next ticket's `pre` capture under `references/working-tree-drift.md`. An unchanged handoff adds no repository scan. Ordinary changed paths use that contract's conservative automatic classification and are never silently absorbed into the next ticket.
