# Ticket boundary, ordering, scope, and verification preflight contract

Read this contract before proposing a ticket graph. It prevents two expensive
authoring failures: publishing a semantic epic as one ticket, and leaving a
lifecycle or concurrency decision for the implementation supervisor to invent.
It also prevents a bounded discovery rule from being mistaken for proof that
the declared scope is complete, and defines the baseline verification preflight
used after the graph is drafted.

## Semantic ticket boundary

A ticket is one acceptance unit, not a count of files, modules, or layers. A
vertical slice may cross API, adapter, service, persistence, UI, test, and
documentation layers when those changes produce one result that must land
together. File count and diff size are evidence for context planning, never a
mechanical split rule.

Before proposing a ticket, the author traces its result to the final product
behavior, a necessary interface consumed by a dependant, required migration
compatibility, or an explicit prerequisite evidence gate. A temporary codec,
placeholder, or incomplete wiring does not earn independent behavior acceptance
merely because it can compile. Keep required safety and prerequisite checks.

For results that meet this product-contract boundary, apply the independent-rejection test:

> Could a reviewer independently accept or reject one required result while
> the other result remains a coherent, green repository state?

If yes, those results are separate tickets with an explicit `Consumes` /
`Produces` edge when one depends on the other. A proposed ticket is a
**semantic epic** and must be split when any of these is true:

- it contains two independently reviewable observable results;
- it changes two lifecycle, state, or cleanup owners whose contracts can be
  accepted independently;
- it asks the implementation supervisor both to choose a public API or wire
  contract and to implement that undecided contract;
- it combines compatibility expansion, caller migration, old-contract removal,
  and delivery closure even though those states can remain green separately;
- its behavior, ownership, boundary interactions, and verification cannot be
  reasoned about within one fresh supervisor context using only the declared
  cold-start inputs.

Do not split one lifecycle or state model merely because it crosses technical
layers. Keep the slice intact when one owner and one invariant require an atomic
change and a reviewer could not accept either half independently.

For a wide migration, prefer **expand–migrate–contract**:

1. The expand ticket introduces the new contract beside the old contract and
   produces the compatibility interface.
2. Each migrate ticket moves one independently green caller batch and consumes
   that interface.
3. The contract ticket removes the old contract only after every caller batch
   is accepted and completes delivery/documentation closure.

If the destination, owner, or migration states are still too foggy to draw
these boundaries, return the effort to the `wayfinder` flow. Do not disguise a
decision map as one implementation ticket.

Every published ticket records a concise slice-boundary proof:

- the single acceptance unit;
- the lifecycle, state, and cleanup owners it changes;
- why no required result can be independently rejected and split;
- why its declared inputs fit one fresh supervisor context;
- the condition that would return the ticket to authoring for a split.

## Ordering and ownership decision

Lifecycle, concurrency, cancellation, retry, recovery, cleanup, resource
ownership, routing, and cross-process ordering work requires a durable ordering
decision in the spec or a superseding ADR before ticket publication. A ticket
may quote and trace that decision; the ticket itself must not become the first
authority for the behavior.

The authoritative decision identifies each operation using these fields:

| Field | Required meaning |
| --- | --- |
| Actor / thread | The caller, component, callback, or thread that performs the operation |
| Operation / object | The exact create, publish, load, unload, release, cancel, drain, detach, destroy, retry, or equivalent operation and resource |
| Condition | The state and input under which the operation starts |
| State owner | The one component that decides the relevant phase or admission state |
| Resource owner | The one component that retains and releases the resource |
| Linearization point | The exact event after which competing operations must observe this operation as accepted |
| Competing operation | Every operation that can overlap and the required before/after result |
| Failure owner | The component that detects failure, retains retry state when retry is authorized, and executes recovery |
| Observable result | The externally visible state, output, callback, wire ordering, or capacity effect |
| Deterministic interleaving | The latch, barrier, runnable prototype, or boundary test that proves the required ordering |

Include every facade or reacquisition path that can reach the same state owner.
An instance-local lock is not a cross-facade ordering decision unless authority
establishes that the instance is the shared owner. Include both sides of a
process or wire boundary when admission and execution occur in different
components.

Before adding a wait, use count, cleanup guard or retry, trace the existing
resource owner's guarantee and identify the independent caller-visible
obligation the addition protects. A lower owner that already drains work before
unload does not by itself require the caller to wait for that drain too. Preserve
separate business cleanup obligations. For a new synchronous wait, identify its
thread, awaited completion, enclosing caller budget and timeout result through
the real call path. An asynchronous callback alone does not justify blocking.
Record this reasoning in the existing ownership decision and state budget; do
not add another review or proof form. If current authority requires a conflicting
guarantee, resolve that decision with its owner before publishing the ticket.

When discussion cannot settle an interleaving, use the `prototype` skill or a
small deterministic latch test to answer exactly one ownership or ordering
question. Record the verdict in the spec or ADR and link that authority from the
ticket. Prototype code is evidence, not the behavior contract.

If any material row is missing, contradictory, or admits multiple plausible
owners, the proposed ticket must not become `ready-for-agent` until the decision
is recorded. Return the unresolved decision to the spec owner, `prototype`, or
`wayfinder` as appropriate.

## Scope closure preflight

After drafting exact scope and before candidate publication, run every ticket's exact
permitted-discovery command against the current authoring baseline. Normalize
each result to one repository-relative path and assign it exactly one
disposition:

| Disposition | Required meaning |
| --- | --- |
| `declared-write` | The ticket already names the exact create, modify, or delete path. |
| `read-only` | The ticket names the exact path as an input that the executor must not modify. |
| `false-positive` | The search matches the exact path, but a recorded reason proves it is outside this ticket's behavior and owner. |

Require this set difference to be empty:

```text
discovered paths - declared write paths - read-only paths - named false positives
```

Record the exact command, authoring baseline, per-path disposition and reason,
and exact result `0 undisposed paths` in the ticket. A command failure,
duplicate disposition, missing reason, or nonempty difference returns the
ticket to authoring. Compilation, tests, verification preflight, and an
execution-time stop condition do not establish authoring scope closure.

For API, wire or output-shape migrations, the author treats existing generated
consumers, published-coordinate smoke consumers and acceptance scripts as
callers of the affected seam. Inspect their actual consumer shape and both the
required positive use and isolation/rejection assertions, not only a generator
label or an old passing command. Assign each affected generator/script an exact
write path in the migration ticket, or name its owning ticket and explicit
Consumes/Produces edge. Do not defer known consumer migration to final review.
This is bounded scope discovery over existing callers/gates, not another review
or a repository-wide search for hypothetical verifiers.

For a ticket with blockers, inspect each blocker's exact write scope and
`Produces` contract for a known caller-topology change. Add each knowable future
caller to the dependant's declared scope before candidate publication. The execution owner
still reruns discovery after blockers complete and fails closed on any new
unclassified path; the authoring witness covers the current baseline and known
blocker delta, not unknown future repository drift.

When a ticket has no permitted discovery, record that exact scope was
established without discovery and that any additional write path returns to the
owning execution flow. Do not manufacture a search only to populate the table.

## Documentation edit contract

Keep this contract only for a ticket that modifies existing Markdown. The
default mode is `surgical`: list the exact heading sections, fenced-code-block
responsibilities, or facts that current authority permits the implementation
owner to delete, rewrite, or move. Every existing part outside that list is
preserve-by-default. An exact Markdown path in declared write scope grants
permission to edit that file; it does not grant permission to redesign the
whole document.

Use `whole-document` only when a current spec, ADR, or recorded user approval
explicitly requires a whole-document replacement. Broad phrases such as
"remove stale content", "rebuild this section", "align the docs", or a
negative token scan do not imply whole-document authority.

For each authorized change, distinguish its responsibility:

- If the responsibility still exists, require a positive replacement output,
  its target heading or fenced block, and an acceptance item that proves the
  output exists. This becomes `replaced` during execution audit.
- If the responsibility or fact no longer exists, cite the exact current
  authority proving that absence. This may become `superseded` during execution
  audit.

Split a mixed heading or block into separately authorized responsibilities.
Do not call the whole unit superseded because only one fact inside it is stale.
Do not use line counts, fenced-block counts, or Mermaid counts as a quality or
preservation proxy; the protected unit is the responsibility, and every actual
deletion is reconciled against the final patch during execution.

## Baseline verification preflight

The author assigns each stable behavior to the production boundary that proves
it directly. Other layers verify only their distinct mapping or invariants;
they do not repeat the same end-to-end scenarios. For unfinished dependencies,
use the existing `Consumes` / `Produces` and verification tiers to name the later
ticket or final-gate owner and the behavior still unverified. Intermediate
checks prove only what is currently required to continue. Do not defer an
explicit prerequisite gate or label a future behavior as passed.

After drafting the graph and before candidate publication, declare the smallest
feasibility preflight for every ticket check and feature gate. Share an exact
prerequisite probe by check ID when several commands depend on it; do not default
to their full acceptance commands. The author records one of:

- `pass` — the exact command is expected to pass on the authoring baseline;
- `intentional-fail` — the exact command is the established red seam and must
  fail with one named signature before implementation;
- `implementation-dependent` — the exact command or target cannot yet exercise
  the future behavior, or is an expensive cumulative gate whose baseline
  question can be decided without executing the complete build, so a separate
  exact probe validates every currently decidable path, target, shell fragment,
  retained legacy exclusion, and runtime prerequisite.

Run the exact command for `pass` and `intentional-fail`. For
`implementation-dependent`, run the declared cheapest non-mutating probe. Do
not pre-run every expensive whole-repository build merely to satisfy this
preflight; use the smallest command that can expose a malformed regex, stale
path, missing target, impossible runtime prerequisite, or contradiction with a
required retained interface. This exception applies only to the recorded
`implementation-dependent` probe; a check classified `pass` or
`intentional-fail` still runs its exact command unless a shared prerequisite
failure demonstrably prevents it from reaching its target. Record that failure's
check ID and evidence, every masked check ID, and the condition for running the
masked checks. A masked check has no observed pass/fail of its own. Continue
independent checks. Publication requires all currently decidable feasibility
facts; only a declared unfinished dependency may defer implementation-dependent
observations. Unknown feasibility, unrelated failure, or a required safety or
prerequisite gate still prevents admission. This is an observation in the
existing preflight entry, not a new classification or a waiver.

Before finalizing a check command, the author reads the real declarations of the
existing interfaces, targets, and retained boundaries it references, plus the
relevant callers or existing verifiers. A reference to a nonexistent interface
or target, or a scan that wrongly excludes a required-retained interface, is a
currently decidable authoring error: the author corrects it directly instead of
leaving it for the execution supervisor.

Record the exact preflight command or interaction, expected result, observed
exit/result, and bounded diagnostic signature in the ticket. A claimed `pass`
that fails, an `intentional-fail` with the wrong signature, or an
`implementation-dependent` probe that cannot establish its declared facts
returns the ticket to authoring. It does not become an implementation-time
authority question.

The preflight proves that the verification contract is coherent on the
authoring baseline. It never replaces the ticket-scoped check, feature final
gate, behavior test, target-runtime observation, or assurance review required
after implementation.

For every correctness-critical item covered by
`verification-realizability.md`, baseline coherence also includes a legal
production fixture, reachable boundary or interleaving, complete legal oracle,
direct observation, and absence evidence under `verification-realizability.md`.
Reuse applicable evidence or run the smallest probe for an identified gap;
behavior assertions do not require a mutation experiment per acceptance item. A command that exits successfully while a
named test, required operation, generated consumer, upstream producer result,
or independent assertion is absent is not an admissible check even when its
ordinary baseline invocation succeeds.
