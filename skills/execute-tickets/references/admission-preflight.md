# Ticket admission and verification preflight

Read this contract before accepting a ticket's `scope_ready` envelope. It lets
execution reject an oversized or under-decided ticket before production edits,
and keeps focused ticket checks separate from cumulative feature gates.

## Authority admission

Before a new run-start snapshot and its first ticket selection, require the fixed
`<spec-dir>/implementation-ticket-admission.json` path resolved through the
local Markdown contract and run:

```bash
python3 <execute-tickets-skill-root>/scripts/admission_state.py verify \
  --repo <repository-root> \
  --spec-dir "<spec-dir>" \
  --tickets-dir "<tickets-dir>" \
  --receipt "<spec-dir>/implementation-ticket-admission.json"
```

Require exact output `admitted-by-review` or `admitted-by-user`. The verifier
recomputes the current `spec.md` authority body and complete ticket path set. A
missing receipt, new or removed ticket, changed authority byte, unreadable or
over-budget delta review lineage, malformed disposition, or receipt outside the
fixed feature path blocks before implementation. A presentation-only spec rename
does not block, because `display_title` sits outside the admitted bytes. The
orchestrator does not repair or regenerate admission.

After run-start succeeds, the receipt remains the frozen authoring baseline.
Later orchestrator-owned `ready-for-agent -> done` transitions and bounded
verification or authority repairs legitimately change spec or unfinished-ticket
bytes; retained run-start, repair, and completion checkpoints prove those
transitions. The receipt is never replaced during an active run and execution
never calls `write-implementation-tickets`. Resume validates the run-start
receipt plus every later before/after authority checkpoint instead of requiring
the old receipt to describe corrected bytes.

For `admitted-by-user`, preserve the failed review status and its dispositions
in `admission_basis` and give them to the current supervisor. This is valid
authority, not a reviewer `PASS`. A later decisive production check may still
invalidate the ticket assumption and trigger the ordinary stop condition.

## Execution authority repair

Use **execution authority repair** when current spec,
ADR, completed-blocker evidence, production declarations/callers, and existing
tests uniquely prove that an incomplete ticket contract is wrong while the
accepted behavior stays unchanged. Eligible corrections include ticket order
or blocking edges, behavior-preserving ticket granularity, an omitted exact production
or test-only scope path, a discovery disposition, a stale test/fixture/regex/
scan/command path, missing verification witness text, or a spec clarification
that only writes down an answer already fixed by a recorded user decision or
ADR. Convenience alone is not evidence. At least one stable source outside the
proposed repair delta must uniquely determine the expected result; code proves
implementation facts but cannot by itself choose new product behavior, and a
modified test, fixture, regex, scan, or command cannot approve itself.

The repair is ineligible when it would change observable behavior, public
interface, production ownership, or runtime state semantics such as lifecycle,
concurrency, retry/recovery, cleanup/resource ownership, routing, or externally
visible ordering; modify a `done` ticket or completed blocker contract; accept
unresolved review risk; or require destructive, credential,
external, Git-history, or device authority outside the ticket-declared bounded
`adb` real-device verification lane. The supervisor reports that exact
material boundary instead of choosing for the user. After the decision owner
records an exact material choice, execute may update the spec and affected
unfinished tickets through this same checkpointed repair; it still does not
return to write review.

The actors execute this sequence:

1. The fresh ticket supervisor emits `blocked` with
   `blocker_class: authority_backed_ticket_defect`, exact authority/repository
   evidence, affected current and named unstarted tickets, and the smallest
   contract correction. It makes no production, test, build, or public-document
   edit. An unstarted ticket is affected only when its exact scheduling, slice,
   scope, or verification field must change, or its exact `Consumes` row
   references a corrected `Produces` row or verification owner. Do not expand
   the set by ticket-number adjacency or transitive guesswork.
2. The orchestrator keeps that supervisor so the actor with the live code
   context owns the diagnosis. It freezes the current HEAD, index, working tree,
   unchanged run-start receipt, spec, and affected ticket bytes in an ignored
   `authority-repair-N/pre` checkpoint and retains recoverable process-document
   copies. Completed ticket and integration-review evidence must already verify.
3. The orchestrator applies the supervisor's exact behavior-preserving
   correction to only the named unfinished tickets and, when eligible, the spec.
   A ticket-boundary repair may add, remove, or rename only unfinished ticket
   files while retaining the current ticket path as the first resumable slice;
   it updates every affected `Blocked by`, `Consumes`, and `Produces` reference.
   It does not invoke `write-implementation-tickets`, dispatch an authoring
   reviewer, or regenerate admission. A material choice is applied only after
   the decision owner records its exact result.
4. The orchestrator captures every changed, added, or removed spec/ticket path
   as an approved authority transition against the checkpoint. When the path set
   changes, it supplies the complete post-repair set with repeated
   `--authority-path` arguments and declares both sides of a rename with
   `--authority-transition-path`. It proves that the receipt and all
   unlisted process documents are byte-identical, and proves HEAD, index,
   accepted implementation content,
   completed ticket bytes, completion checkpoints, and protected outside-scope
   state are unchanged. Any missing proof stops the repair without inferring
   state from prose.
5. The orchestrator appends the transition to `admission_basis`, reruns only the
   affected deterministic scope/preflight checks, discards any old unaccepted
   scope snapshot, captures a new `pre` snapshot from the corrected exact scope,
   and tells the same supervisor to resume the same ticket. Its dependants remain
   blocked until the repaired ticket completes normally.

The recovery target is explicit: resume the same ticket, not the next ticket and
not a rewritten completed blocker.

If correction or transition verification fails, the
orchestrator restores the retained old process-document bytes, verifies their
hashes and the unchanged run state, and records the repair attempt as failed.
If exact restoration cannot be proved, the run remains stopped on the repair
checkpoint; it never continues with a half-admitted candidate.

Ticket-scoped checks and execute's assurance lane still decide acceptance.
Execution authority repair removes write recursion; it does not weaken scope
isolation, verification, assurance, or staging. A correction discovered after
production edits begin must first end workers/reviewers and freeze the current
candidate. It may continue only when the corrected contract covers the existing
candidate without retroactively authorizing an already modified out-of-scope
path; otherwise stop and recover before restarting that ticket.

## Admission depth and reuse

The supervisor checks current authority, completed blockers, exact scope, key
interfaces/owners and whether acceptance is feasible. It reads the production
seam and directly relevant declarations needed to decide these questions, then
replays applicable declared non-mutating discovery/preflight probes, sharing evidence under the rules below. Reuse
admitted behavior, ordering and witness definitions when those inputs agree;
expand only an observed difference, missing evidence or concrete risk. The
orchestrator verifies identities, scope ownership and the supervisor's reported
differences; it does not perform a second code/semantic admission review.

An unknown affecting behavior, public interface, ownership, scope or verification
feasibility still blocks before implementation. Detailed helper bodies and
mechanical caller migration may be read immediately before their edits; lack of
a complete internal implementation plan is not itself an admission failure.
Declared prerequisite/safety gates remain mandatory. Planned fixtures do not
need implementation or final behavior execution to produce `scope_ready`.

For API/wire/output migrations, the supervisor includes the declared generated
or published consumers and existing verifier scripts when inspecting the
consumed interface. A legacy consumer still compiling does not prove the new
shape. Resolve a missing generator/script write path through execution authority
repair before editing; do not change it outside scope or leave a known gap for
final review.

Resolve check/gate IDs and section references in declared inputs before execution.
A command and its working directory have one definition; reusing its ID does not
waive its check. Existing expanded tickets remain valid when their definitions
agree; do not rewrite active tickets just to adopt compact formatting.

## Slice-boundary admission

Check the ticket's slice-boundary proof against the current spec and consumed
blocker interfaces; investigate changed boundaries or a concrete contradiction
instead of re-deriving an unchanged authoring decision. Apply the **independent-rejection
test**:

> Could a reviewer independently accept or reject one required result while the
> remaining result is still a coherent, green repository state?

If yes, the ticket is a **semantic epic** and blocks before implementation. The
supervisor must name the independently acceptable units and their required
`Consumes` / `Produces` edge. The orchestrator applies that exact split through
execution authority repair while retaining the current ticket path, then the
same supervisor resumes the first slice. It must not implement the easiest part,
add an internal batch plan, or invoke write review. If the split exposes an
unsettled behavior, owner, or public interface, obtain that decision first and
then apply the split directly.

Also reject a ticket when it changes independently separable lifecycle, state,
or cleanup owners; asks implementation to choose a public API or wire contract;
combines expand, caller migration, old-contract removal, and delivery closure;
or cannot be reasoned about within one fresh supervisor context from its
declared cold-start inputs.

Do not reject one vertical invariant merely because it crosses many files or
technical layers. The decisive question is whether either half could be
accepted independently without leaving the repository inconsistent.

## Ordering and ownership admission

Before admitting new waits, use counts, cleanup guards or retries, compare the
declared obligation with the existing lower resource owner's guarantee. A
synchronous wait also needs its actual thread, completion condition, enclosing
caller budget and timeout result. Reuse admitted evidence when it agrees with
the real call path. A callback alone is not a reason to wait; lower-level drain
safety does not remove independent business cleanup obligations. Route a
conflicting or redundant ticket requirement through the existing authority
repair/material-decision rules, rather than adding protection or silently
removing an explicit contract.

For lifecycle, concurrency, cancellation, retry/recovery, cleanup/resource
ownership, routing, or cross-process ordering, require a spec or superseding ADR
that establishes every applicable row below:

| Field | Admission evidence |
| --- | --- |
| Actor / thread | Exact caller, callback, component, or thread |
| Operation / object | Exact resource operation and object |
| Condition | Starting state and input |
| State owner | Component that decides admission or phase |
| Resource owner | Component that retains and releases the resource |
| Linearization point | Event after which competing operations observe acceptance |
| Competing operation | Required before/after result for every overlap |
| Failure owner | Detector, retained retry-state owner, decision maker, and recovery executor |
| Observable result | State, output, callback, wire ordering, or capacity effect |
| Deterministic interleaving | Latch, barrier, prototype result, or boundary test |

Trace facade reacquisition and both sides of a wire/process boundary when they
can reach the same state. An instance-local lock does not prove cross-facade
ordering unless the authority identifies that instance as the shared owner.

A missing or contradictory actor, state owner, cleanup owner, Resource owner,
Linearization point, Competing operation, failure owner, observable result, or
Deterministic interleaving blocks before implementation. The supervisor cannot
invent the missing decision in `scope_ready`; it obtains the exact answer from
the decision owner, then execute records that answer in the spec and unfinished
tickets through execution authority repair without invoking write review.

## Scope closure revalidation

After the current ticket's blockers complete and before `scope_ready`, the
supervisor reruns every exact permitted-discovery command recorded by authoring
against the current repository. Normalize each command result to one
repository-relative path and assign exactly one execution disposition:

| Disposition | Execution meaning |
| --- | --- |
| `declared-write` | The ticket already names the path in exact write scope. |
| `permitted-write` | The path satisfies the ticket's bounded permitted-discovery rule and appears in the proposed `scope_paths`. |
| `read-only` | The path is a named input that execution must not modify. |
| `false-positive` | A recorded reason proves the match is outside this ticket's behavior and owner. |

Record the exact command, authoring baseline, current completed-blocker basis,
all discovered paths and dispositions, and exact result `0 undisposed paths` in
`scope_closure_trace`. A command failure, duplicate or missing disposition,
missing false-positive reason, discovered write path absent from `scope_paths`,
or nonempty undisposed set blocks before edits. When stable authority uniquely
proves a missing exact path, use execution authority repair; otherwise return the
scope gap to its decision owner and apply the recorded answer through the same
repair. A ticket without permitted discovery records that exact
scope was established without discovery and performs no synthetic scan.

## Exact scope snapshot coverage

Before edits, `assess` and the initial ticket `pre` capture reject every exact
scope path that Git would leave untracked and ignored, naming the paths. This
includes a path that does not exist yet when creating it would match an ignore
rule. `collect_untracked` uses `--others --exclude-standard`, so such a path can
never enter the reviewed untracked delta or the protected staged index.
Force-adding the path or changing Git ignore rules is not a permitted repair.
`git check-ignore` does not report tracked paths, so a tracked file matching an
ignore pattern and a declared path Git would not ignore keep their existing
behavior, and ignored authority and run-artifact paths remain outside delivery
scope. In a repository set the owning member runs the check on its own scope
paths.

## Baseline verification revalidation

Before `scope_ready`, the supervisor accounts for every declared non-mutating
preflight. Run its exact command unless a proven shared prerequisite failure
masks the check. A preflight used solely to establish execution integrity may
reuse applicable absence evidence under the next section; that reuse does not
waive a baseline behavior/build check or any post-implementation check.
For a masked check, reference the failed prerequisite, direct dependency evidence,
and the condition for running it in the existing `preflight_trace.observed`.
Do not invent an exit code, claim it passed, or rerun several commands that can
only hit the same known failure. Independent checks still run.

Only a completed blocker's consumed interface change that the current ticket
already owns may explain a migration failure and allow implementation to
continue. Other failures follow the drift/authority rules below. Missing
feasibility evidence and explicit safety/prerequisite gates still block. After
repairing the prerequisite, execute every masked required check at its declared
verification stage before acceptance; masking never waives a check. The authoring
classification has one of these meanings:

- `pass` — the declared preflight succeeds on the accepted baseline;
- `intentional-fail` — it fails with the exact recorded red signature;
- `implementation-dependent` — the declared probe establishes every currently
  decidable path, target, retained-interface exclusion, and runtime prerequisite.

Compare the current result with the recorded baseline. A difference is accepted
only when a named completed blocker and its exact `Produces` contract explain
the new result and the current ticket explicitly consumes it. Record that trace
in `scope_ready`. Every other difference is contract drift: repair it directly
when authority fixes one answer, otherwise obtain the material decision and then
update the spec/tickets directly before edits.

A malformed regex, stale path, missing target, wrong failure signature, or a
scan that rejects an explicitly retained interface is a verification-contract
defect. Apply the existing bounded verification-only repair when authority
determines one correction. Do not reinterpret it as a product decision.

Preflight is admission evidence only. It never replaces the post-implementation
ticket-scoped check, feature final gate, behavior test, runtime observation, or
assurance review.

## Verification witness revalidation

For every named boundary test, lifecycle/resource proof, negative scan,
generated-consumer check, or other correctness-critical acceptance item, require
the ticket's verification witness before `scope_ready`:

| Field | Admission evidence |
| --- | --- |
| Production producer | Exact production encoder, API, operation, generated artifact, or compiled consumer that creates the observation. |
| Legal fixture | Inputs the production producer can legally accept; no unknown wire field, fake-only failure, comment, dead text, or forced state substitutes for it. |
| Reachability | Numeric bounds or deterministic interleaving that reaches the asserted condition. |
| Oracle | Every authority-permitted result, including legal races and operation-specific success no-ops. |
| Observation | Direct value, identity, count, ordering, generated file, compiled call, or side effect required by the claim. |
| Absence detector | Observed or validly reused evidence that required execution/input and failure propagation cannot be missing while reporting success. |

Validate the applicability of retained exact-result, failure-propagation or
relevant red evidence before replaying a probe. Reuse it when its producer,
fixture, oracle and execution check remain applicable; reference shared evidence
once. Run only a declared probe whose evidence is absent or invalidated, and use
a single execution when it also serves baseline preflight. Do not add
undeclared probes in scope admission. For applicable execution-integrity checks,
independently select
each named Gradle method or validate the exact JUnit method set; scope production
scans away from rejection fixtures; check generated/compiled consumers rather
than generator text; prove independent operations separately; and preserve an
upstream nonzero exit through any necessary pipeline.

Separately inspect product assertions at the production seam; execution
integrity alone does not prove behavior. Production mutation tests are not the
default absence detector: require an explicit authority or a concrete
false-green risk that existing seam/fixture/assertion/result inspection cannot
resolve. An existing literal mutation/replay requirement remains binding until
corrected through execution authority repair. A redundant internal edit does
not itself invalidate unrelated evidence; identify the affected witness input.

An impossible production fixture, incomplete legal oracle, or observation that
proves only a weaker property is an unrealizable acceptance contract and blocks
before edits. It is not a bounded verification-only repair: execute applies an
authority-backed contract correction directly, or obtains a material decision
and then updates the spec/tickets directly. A
mechanical typo in a command, regex, scan path, or fixture remains repairable
only when the original authoritative claim and its legal witness stay unchanged.

## Verification tiers

### Ticket-scoped checks

The current ticket supervisor runs only the ticket-scoped checks after
implementation and before assurance. Each check traces to a current-ticket
acceptance item and uses a focused production seam, module target, deterministic
scan, or required target-runtime interaction.

A ticket-scoped check must not contain a whole-feature build merely because that
build is important at closure. When authority genuinely requires that command
to prove this ticket independently, the ticket must state the narrower
acceptance fact that makes it ticket-scoped.

### Feature final gates

The final-gate supervisor runs each uniquely owned feature final gate once after
all implementation tickets are accepted. Build a gate inventory from the
owning tickets and `execution-plan.md`, without asking the orchestrator to load
future implementation bodies into its context.

Each gate has one stable id, one exact command or interaction, one owner, one
expected result, and one reuse assessment: `always-run` or `reusable`. A
duplicate gate id with a different owner, command, expected
result, or assessment is an authority conflict and stops before executing any
feature gate. Identical declarations still require exactly one named owner; do
not run the command once per ticket.

`reusable` reuse follows `reusable-gates.md` exactly.
`always-run` records the authoritative external-state or incomplete-boundary
reason and executes normally. The executor never upgrades an `always-run` gate
by inferring dependencies from changed files.
An explicit historical runtime evidence condition is a separate authority-backed
exception after repairs within this run. Validate its claim, evidence/input
boundary, invalidating changes and freshness requirement under `reusable-gates.md`;
do not reclassify the gate as repository-only `reusable`. Missing conditions or a
fresh/current-runtime requirement mean execution, not inferred permission.
