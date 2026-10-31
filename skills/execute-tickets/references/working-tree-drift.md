# Protected working-tree drift

Read this file when `review_state.py` reports a tracked or untracked path outside
the accepted ticket scope, before an authorized temporary prerequisite repair,
and before the orchestrator captures the next
ticket's `pre` snapshot from a retained handoff. The first question is whether
the changed path can affect the current ticket. If it cannot, preserve it outside
the ticket delta/index and continue without investigating who changed it.

## Boundaries and owners

For a repository set, apply `multi-repository.md`: use the aggregate baseline,
per-repository reports, `NAME:path` decision keys, aggregate resolutions, and
aggregate completion handoff. A change in any member receives the same ownership
classification below; no member's protected state is exempt.

The orchestrator owns the protected-state record and every reconciliation
command. A ticket supervisor or worker does not stop merely because an
outside-scope path changed. It leaves an unrelated path outside scope and the
index and continues. It stops writing and reports the path only when the change
can affect the ticket's implementation, verification, review input, interface,
state/resource owner, or protected staging, or when that isolation is unclear.

Only ordinary unstaged working-tree paths are reconcilable:

- a tracked path outside the accepted ticket scope that was created, modified,
  deleted, or returned to the index version;
- a non-ignored untracked path outside the accepted ticket scope that was
  created, modified, or deleted.

`HEAD`, the Git index, the cumulative staged patch, and unexplained authority
content are strong drift. Stop the active run with exact evidence; do not
silently discard or preserve them. A behavior-preserving unfinished-ticket
authority defect may instead enter execution authority repair, but every other
intentional strong change requires a new run baseline or material authority. A
proposed ticket write path that lacks declared-scope or permitted-discovery
authority is not working-tree drift; route an authority-backed omission to
execution authority repair and every material change to its decision owner.

A worker write outside its assigned package but inside the accepted ticket
scope remains a delegation ownership breach. This protocol applies only to the
ticket's protected outside-scope state; it never turns an unassigned ticket
candidate into external work.

Git-ignored non-authority files do not appear in the untracked manifest and are
not covered by this protocol.

## Detect and classify

When a scope guard or snapshot reports protected drift, assess impact before
pausing work. For a path that cannot affect the current ticket, the orchestrator
records the exact state, defaults to `preserve`, and continues; this bookkeeping
does not emit `drift_detected`. End active write work and keep reviewers stopped
only for an affecting or non-isolatable path. The exact report is produced with:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py drift \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --output .execute-tickets/<feature>/<ticket>/drift-N
```

When a prior resolution already defines the approved protected state, add:

```bash
--drift-resolution .execute-tickets/<feature>/<ticket>/resolution-N/resolution.json
```

The report returns `clean`, `confirmation_required`, or `restart_required` and
lists exact paths, tracked/untracked category, created/modified/deleted state,
and before/after hashes. `confirmation_required` means the deterministic tool
needs a disposition record; it does not mean the user must supply it or that a
harmless change pauses the workflow. The
orchestrator classifies each path as:

- `restore` — a workflow-attributable accidental write that must return to the
  last frozen or previously classified protected state;
- `preserve` — an outside-scope change that must remain unstaged and outside the
  ticket delta: either harmless state or an explicitly authorized prerequisite
  repair handled below. Preservation does not establish harmlessness.

Use `preserve` automatically whenever the path is independent of the ticket's
authority, verification inputs, interfaces, state/resource owners, review input,
and staging result. Do not investigate provenance as a precondition for
continuing. If retained tool evidence already proves a workflow-attributable
accidental write and exact restoration is safe, the orchestrator may use
`restore` automatically; this cleanup also does not pause an otherwise
unaffected ticket. Mixed paths receive mixed dispositions.

Only ask the user when the outside-scope state can change the ticket result and
the current spec, ADRs, tests, and retained evidence do not determine one safe
handling, or when reconciliation needs new
destructive, irreversible, credential, external, or Git-history authority.
Provenance ambiguity by itself is never a reason to ask or pause.

Write the exact classified decision and its evidence in the ignored run-artifact
tree:

```json
{
  "decisions": {
    "README.md": "preserve",
    "local-notes.txt": "restore"
  }
}
```

## Authorized temporary prerequisite repairs

Permission to repair a baseline prerequisite does not add that repair to the
feature's delivery or staging scope. Before the write, the orchestrator records
the existing authorization, exact paths, before-state bytes/hashes, repair owner
and required keep/restore disposition in the existing run artifacts. The named
supervisor may make only that authorized repair; all other protected paths stay
read-only. If authority is missing, request only the missing repair or delivery
decision and continue independent work. Do not expand ticket scope merely to
make the guard accept a temporary patch.

After the repair, the orchestrator freezes its exact delta and resulting content,
records the affected checks, and uses the ordinary drift report and `preserve`
reconciliation. Keep it outside ticket patches and the index. A compilation or
verification dependency is affecting state, not harmless drift: rerun checks
that consume it and supply the narrow frozen dependency evidence under
`review-mechanics.md`. An existing authorization needs no repeat confirmation.
The drift resolution checks protected bytes, not correctness or acceptance.
After the required checks and review, only the orchestrator stages accepted
ticket paths. In the repair handoff, name the supervisor as repair owner and
the orchestrator as freeze, reconciliation and staging owner; do not leave
those operations ownerless or assign them to the supervisor.

This protocol isolates paths, not hunks. If temporary repair and ticket work
share a scope path and cannot be reliably isolated with the existing mechanism,
stop before staging or accepting that candidate. Preserve all bytes and report
the exact delivery conflict for a decision. Do not stage the whole path and
promise to remove temporary hunks later; continue independent work without
inventing a hunk-staging subsystem.

Report checks against a workspace containing the patch separately from evidence
that the delivery candidate works without it. If independent candidate proof is
required but unavailable, keep that result unproved under `final-gate.md`; do not
claim it builds without the patch or silently discard the user's retained work.

## Reconcile the exact report

The orchestrator runs:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py reconcile \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --report .execute-tickets/<feature>/<ticket>/drift-N/report.json \
  --decision .execute-tickets/<feature>/<ticket>/drift-N/decision.json \
  --output .execute-tickets/<feature>/<ticket>/resolution-N
```

Pass the prior `--drift-resolution` when classifying a later change
against an already approved protected state. The command re-collects the current
state before writing. A changed path or hash makes the report stale; discard the
old decision and classify the fresh report again.

For `restore`, the command first moves the current path into the resolution's
`quarantine/` tree, then restores the last protected bytes, kind, and mode. A
tracked path that was clean at the baseline comes from the unchanged Git index.
A pre-existing dirty tracked or untracked path comes from content retained in
the baseline or prior resolution. A newly created untracked path remains only
in quarantine. If an older snapshot lacks required retained content, stop
reconciliation and report the exact missing recovery input; never guess or
restore it to `HEAD`.

For `preserve`, the command leaves the path unchanged, records its exact current
state and disposition evidence, and retains the content needed if a later accidental
change must return to this newly approved state. The resolution does not add the
path to ticket scope.

## Continue the ticket

Pass the accepted resolution to every later candidate capture for this ticket:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --output .execute-tickets/<feature>/<ticket>/review-N \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --drift-resolution .execute-tickets/<feature>/<ticket>/resolution-N/resolution.json
```

The snapshot embeds the approved outside-scope state. `ticket-tracked.patch`,
`ticket-untracked.patch`, and protected staging still contain only exact ticket
scope paths. The accepted external paths remain in the working tree and out of
the index. Any later change to an approved path requires a fresh state record.
If it is still independent of the ticket, preserve it again and continue
without a workflow pause.

If reconciliation occurs after ticket checks or review began, the ticket
supervisor reruns checks whose inputs can observe the changed external path.
An external path that no ticket check, review input, interface, or state owner
can observe is harmless and needs no rerun.
Any change to assurance inputs invalidates the old review for the new candidate;
capture and review again under the existing assurance policy. Protected-state
changes with unchanged assurance inputs use the bounded rebinding below. A drift
disposition prevents a scope-drift stop, but it does not turn a failing build,
contract mismatch, or verification result into a pass.

## Rebind a passing review after harmless protected-state drift

After a verified passing review, the orchestrator may retain that review only
when every changed protected path is independent of the ticket's implementation,
checks, standards, reviewer context, interfaces, and state/resource owners. It
records the path-specific evidence in the existing drift disposition. An
uncertain dependency or changed assurance input is ineligible; do not use
rebinding to avoid review budget or revive a FAIL.

Reconcile against the original ticket `pre`, retaining any earlier resolution,
then run:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py rebind \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --snapshot .execute-tickets/<feature>/<ticket>/review-N \
  --drift-resolution .execute-tickets/<feature>/<ticket>/resolution-N/resolution.json \
  --output .execute-tickets/<feature>/<ticket>/review-rebound-N
```

The tool requires identical HEAD, index, staged baseline, authority, exact scope,
ticket manifests and ticket patches, and freezes only the reconciled protected
state. Its `review_rebinding` links the original snapshot/hash and changed
protected paths. Loading the rebound snapshot verifies that source and content
identity again. This proves the declared byte boundary, not semantic
independence; the orchestrator still owns the path-impact assessment above.

The orchestrator keeps the original reports/hashes and disposition, binds
`final_acceptance_snapshot` to the rebound snapshot, verifies it, and uses it for
ticket staging or final acceptance. It records the relationship in the existing acceptance/integration
evidence, not a new PASS or reviewer-round event. The review budget is unchanged.
For repository sets, use aggregate paths; every member must satisfy the same
rule. For a final or validation-only review captured without a review baseline,
use that original review snapshot as both `--baseline` and the first `--snapshot`;
reconcile against it and retain the same baseline for later rebindings. Frozen
integration inputs and reports still must be unchanged. Missing source evidence
blocks reuse.

## Compare run-start and ticket handoffs in each `pre` capture

For the first ticket, use `.execute-tickets/<feature>/run-start` as the handoff.
This prevents repository, index, authority, or protected working-tree changes
during scope admission from being silently absorbed into the first `pre`.

`ticket_state.py complete` writes `completion/handoff/` from the state it
already collected to prove the completion transition. It does not perform a
second repository scan. After the next supervisor declares exact scope, the
orchestrator combines comparison and `pre` capture in one command:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --output .execute-tickets/<feature>/<next-ticket>/pre \
  --handoff .execute-tickets/<feature>/<completed-ticket>/completion/handoff \
  --drift-output .execute-tickets/<feature>/<next-ticket>/handoff-drift \
  --scope-path <next-ticket-path-1>
```

When the handoff is unchanged, the same state collection writes `pre`; there is
no extra full snapshot or verification run. When it changed, the command writes
the report without creating `pre`; this requires a disposition record, not
necessarily a user prompt or workflow pause. Harmless paths are automatically
preserved, then the orchestrator reruns the same `capture` with the resulting
`--drift-resolution`. The new `pre` now freezes intentional external changes as
protected state and preserves restored paths at the handoff state.
