# Implementation delegation

Read this file in full before a ticket supervisor dispatches an implementation
worker. Delegation reduces first-pass coding context; it does not split ticket
authority or create another acceptance owner.

## Contents

- [Invariants](#invariants)
- [Admit one work package](#admit-one-work-package)
- [Dispatch a fresh worker](#dispatch-a-fresh-worker)
- [Bound concurrency](#bound-concurrency)
- [Require a bounded handoff](#require-a-bounded-handoff)
- [Integrate before `implementation_ready`](#integrate-before-implementation_ready)

## Invariants

- Keep one active ticket supervisor and one shared working tree.
- Keep the supervisor as the only owner of the ticket contract, execution mode,
  integration, ticket-scoped verification, review convergence, and acceptance
  handoff.
- Delegate only after `scope_accepted` and before `implementation_ready`.
- Keep the Git index and `HEAD` read-only for supervisors, workers, and reviewers.
- Treat a worker result as a package handoff, never as a supervisor status or
  ticket acceptance result.
- End every implementation worker before capturing the first assurance snapshot.
  Never overlap implementation workers with Standards or Spec reviewers.
- Let the same supervisor classify and repair review findings. Do not dispatch an
  implementation worker after review begins.

## Admit one work package

Use the smallest number of workers that materially reduces supervisor coding or
diagnostic context. Implement directly when delegation setup costs more than the
bounded slice, including ordinary micro-lane work.

Before dispatch, write a complete package contract:

```yaml
package_id: <stable identifier within the ticket>
acceptance: <one named ticket acceptance slice>
execution_mode: <the ticket's direct, test-after, or tdd mode>
scope_paths: [<exact accepted ticket-scope path>]
inputs_outputs: <production inputs, produced result, and package dependency>
production_seam: <stable seam or direct mechanical path>
verification_witness: <producer, legal fixture, reachability, oracle, observation, applicable shared absence evidence>
focused_check: <exact command or target-runtime interaction>
depends_on: [<earlier package id, or empty>]
```

Require every `scope_paths` entry to be an exact subset of the orchestrator-
accepted ticket scope. Keep the production seam and expected result fixed by the
ticket/spec. A package cannot invent a new test seam, owner, interface, state, or
behavior merely to become delegable.

One package owns one complete vertical slice. Under `tdd`, give one worker the
failing behavior test and its production fix so it can complete one red → green
slice. Never split tests and production code for the same behavior across workers.
All packages inherit the ticket's single locked execution mode; delegation is not
a fourth mode and workers do not select or change it.
The inherited mode applies to the stable target behavior. One failing behavior
test may cover continuous implementation and wiring within the package; the
worker does not create separate reds for helpers or intermediate states. The
supervisor must not split a behavior merely to create more test/fix packages.

If the package fields are missing only because the implementation is tightly
coupled, let the supervisor implement directly. If they are missing because two
outcomes can be accepted or rejected independently, owners/interfaces remain
unsettled, or the acceptance cannot close under one ticket contract, emit
`blocked`. Use execution authority repair for an authority-backed ticket split;
when the split exposes an unsettled owner or interface, obtain that exact decision
first and then update the unfinished tickets directly. Do not use workers to
conceal a semantic epic or invoke write review.

## Dispatch a fresh worker

Start each worker without inherited conversation history when supported, for
example with `fork_turns: "none"`. Use the worker agent role when the agent API
provides one. Give it only absolute paths and the package-local contract:

- repository root and applicable repository instructions;
- feature spec, current ticket, and completed-blocker interface evidence needed
  by this package;
- this reference path;
- exact package contract and assigned scope paths;
- relevant standards and retained focused-check environment facts.

Tell every worker that it is not alone in the shared working tree. Require it to
preserve other agents' edits, never revert another package, and adapt its change
to already-present accepted or package-local work. Also require it to:

- read the declaration/export, immediate production callers, shared utilities,
  and relevant tests before editing;
- edit only assigned exact paths;
- keep raw logs in the ignored run-artifact tree under the current ticket's `.execute-tickets` directory;
- run only the focused package check, not feature final gates;
- leave all changes unstaged;
- avoid spawning another agent or reviewer;
- if a changed path outside the accepted ticket scope affects this ticket or
  safe isolation is unclear, stop writing and report the exact path without
  restoring, deleting, or adopting it; harmless external changes remain protected
  and do not stop work, under `working-tree-drift.md`;
- stop when it needs another path, behavior, owner, interface, state, completed-
  blocker change, or authority decision.

Workers must not edit the feature spec, ticket, admission receipt, completion
record, review report, or execution checkpoint. They must not run `git add`,
`git reset`, `git restore --staged`, `git commit`, `git stash`, `git checkout`,
or another command that changes `HEAD` or the index.

## Bound concurrency

Default to one write-capable worker at a time. A supervisor may run two workers
in parallel only after proving every condition below before dispatch:

- their exact write-path sets are disjoint;
- they do not share a lifecycle, resource, cleanup, or mutable-state owner;
- they do not jointly define or modify one interface;
- neither consumes the other's unfinished output;
- neither source discovery, build, nor focused check reads the other's in-
  progress mutable output;
- their commands do not write the same generated file, cache, fixture, snapshot,
  or other shared artifact.

Use serial workers when any condition is unknown. Treat lifecycle, concurrency,
cleanup ownership, cross-process routing, and cross-layer interface changes as
non-parallel unless the ticket provides stronger explicit evidence. A whole-
module build that can observe another worker's unfinished source is not a safe
parallel focused check even when assigned files differ.

Keep the maximum active shapes separate:

- implementation: orchestrator + one supervisor + at most two workers;
- review: orchestrator + one supervisor + Standards reviewer + Spec reviewer.

Use additional packages serially and sparingly. Reassess the semantic-ticket
boundary before dispatching repeatedly; agent count is not evidence that one
ticket contract is coherent.

## Require a bounded handoff

Require each worker to return this package-local envelope to the supervisor:

```yaml
package_id: <stable identifier>
acceptance: <ticket acceptance identifier>
scope_paths: [<assigned exact path>]
changed_paths: [<actual changed path>]
checks:
  - command: <focused command>
    exit_code: <integer>
    result: <bounded result or diagnostic tail>
    log: <absolute path and SHA-256>
unresolved_assumptions: [<exact assumption, or empty>]
stop_reason: <scope, authority, interface, witness conflict, or None>
```

Do not return a reasoning transcript. Keep successful raw output in the retained
log and bound failure output to the diagnostic lines that establish the failure.

## Integrate before `implementation_ready`

After every worker ends, require the supervisor to:

1. Compare assigned and actual changed paths. A write outside the worker's exact
   package scope but inside the broader accepted ticket scope blocks the ticket;
   do not silently absorb the ownership breach. A changed path outside the
   accepted ticket scope emits `drift_detected` only when that change can affect
   the ticket or safe isolation is unclear. A harmless outside-scope change
   remains outside the ticket delta/index and does not stop integration or
   trigger provenance investigation.
2. Confirm `HEAD`, index, ticket, spec, receipt, and the frozen or classified
   protected outside-ticket state cannot affect this ticket. Harmless ordinary
   changes are automatically preserved; affecting or non-isolatable changes use
   the orchestrator-owned protocol.
3. Read the complete worker delta instead of trusting the handoff or green check.
4. Validate package inputs/outputs, production seam, verification witness, and
   boundary interactions with earlier package work.
5. Finish ordinary in-scope integration defects directly. Stop on a scope,
   authority, owner, interface, or completed-blocker conflict.
6. Run the complete ticket-scoped checks, deletion audit, and required target-
   runtime interaction itself after all workers have ended.

Only the supervisor emits `implementation_ready`. A package-focused PASS cannot
replace any ticket-scoped check, feature final gate, runtime observation, or
assurance lane.

After the assurance snapshot is captured, keep all implementation workers
ended. The same supervisor fixes contract-backed and Standards-backed review
findings, reruns affected verification, and submits the next snapshot. Do not
reconstruct the frozen finding set in a fresh implementation worker.
