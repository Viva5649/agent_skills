# Implementation ticket template

Replace every angle-bracket placeholder with repository evidence. Remove
instructional comments and sections that are explicitly inapplicable; never
leave a placeholder in a published ticket.

Each observable behavior is defined once under an acceptance A-id. Behavior
contract and implementation steps reference that id; they do not restate its
oracle. Define each exact command, working directory and execution criterion once
under its ticket check or feature gate id. Acceptance, baseline and reusable-input
sections reference that definition. Baseline-specific probes/results remain
separate facts; when a probe is identical, reference the existing command.
References must resolve uniquely within declared inputs, without cycles or hidden
conversation. Existing expanded tickets remain valid if their definitions agree;
do not migrate active/completed tickets just for this format.

A ticket starts at its `#` heading and carries no front matter or presentation
block, so every ticket byte is authority. Only `spec.md` may separate a
presentation label from its authority body.

```markdown
# <NN> — <Ticket title>

**What to build:** <Actor performs action on object when condition, producing
the bounded observable result.>

**Blocked by:** <comma-separated ticket numbers, or exact `None`>

**Status:** ready-for-agent

## Authoritative inputs

- Behavior: `<spec path and section>` establishes <exact behavior>.
- Architecture: `<ADR/domain/code source>` establishes <owner or interface>.
- Completed blocker: `<ticket/evidence path>` produces <consumed contract>, or
  `None — this ticket has no completed blocker input.`
- Superseded inputs: `<paths and obsolete claims>`, or
  `None — no earlier source is superseded by this ticket.`

## Production owner and scope

- Owner: `<exact production, build, documentation, or verification owner>`.
- Read-only repository inputs:
  - `<exact path or symbol needed to understand the current contract>`
- Declared write scope:
  - Create: `<exact repository-relative path>`
  - Modify: `<exact repository-relative path>`
  - Delete: `<exact repository-relative path and deletion condition>`
- Permitted discovery: `<condition and rule that authorizes each additional
  exact path>`, or `None — any additional write path returns the ticket to the
  owning execution flow.`
- Verification input substitutions: `<each verification input the execution
  temporarily replaces or overlays (native libraries, assets, build scripts,
  ABI/baseline files), its restore owner, and the post-restore identity
  check>`, or `None — execution touches only the declared write scope.`

## Scope closure preflight

When `Permitted discovery` applies, keep this section and table. When it is
`None`, replace the section body with
`None — exact scope was established without discovery; any additional write path returns to the owning execution flow.`

- Discovery command: `<exact command that emits repository-relative paths>`.
- Authoring baseline: `<exact repository state on which the command ran>`.
- Blocker caller-topology assessment: `<blocker write scopes and Produces contracts that
  can change caller topology, plus every known future caller disposition>`, or
  `None — this ticket has no blocker-produced caller delta.`

| Discovered path | Disposition | Reason |
| --- | --- | --- |
| `<exact repository-relative path>` | `<declared-write | read-only | false-positive>` | `<why this is the one valid disposition>` |

- Closure result: `0 undisposed paths`.

## Documentation edit contract

Remove this entire section unless the ticket modifies an existing Markdown
file.

- Mode: `<surgical | whole-document>`.
- Authority: `<current spec, ADR, code contract, or recorded user approval that
  authorizes these documentation changes; whole-document requires an explicit
  whole-document authority>`.
- Authorized changes:
  - `<exact file and heading/fenced-block responsibility or fact that may be
    deleted, rewritten, or moved>`.
- Preserve by default: `Every existing section and fenced code block outside
  the authorized changes above.`
- Required replacement outputs:
  - `<still-current responsibility -> exact target heading/fenced block and
    acceptance identifier>`, or
  - `None — every authorized deletion is superseded by the authority above.`

## Slice boundary

- Acceptance unit: `<the one bounded result this ticket delivers>`.
- Changed lifecycle/state/cleanup owners: `<exact owners>`, or
  `None — this ticket changes no lifecycle, state, or cleanup owner.`
- Independent rejection: `<why no required result can be independently accepted
  or rejected as a separate green ticket>`.
- Fresh-context fit: `<why the declared authority, scope, interfaces, ordering
  contract, and verification fit one fresh supervisor context>`.
- Split trigger: `<evidence discovered before editing that returns this ticket
  to authoring for a split>`.

## Interfaces

- Consumes:
  - `<ticket or current owner>` provides `<exact identifier, signature, type,
    schema, state, or evidence>`.
- Produces:
  - `<exact identifier, signature, type, schema, state, observable contract, or
    evidence>` for `<named dependant/caller>`.

If the ticket has no cross-ticket interface, state which existing interface it
uses and why no new interface is produced.

## Behavior contract

- `<A-id>` defines `<short behavior label>`. Source: `<spec/ADR/recorded decision>`.

## Ordering and ownership contract

Remove this entire section unless the ticket changes lifecycle, concurrency,
cancellation, retry/recovery, cleanup/resource ownership, routing, or
cross-process ordering. Cite a spec or superseding ADR; the ticket is not the
first authority for these decisions.

- Authority: `<spec/ADR path and section containing the complete ordering decision>`.

| Actor / thread | Operation / object | Condition | State owner | Resource owner | Linearization point | Competing operation and required order | Failure owner | Observable result | Deterministic interleaving |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `<exact actor/thread>` | `<operation and resource>` | `<starting state/input>` | `<owner>` | `<owner>` | `<exact accepted event>` | `<overlap and before/after result>` | `<detector/state/recovery executor>` | `<observable result>` | `<latch/prototype/boundary test>` |

## Failure model

Remove this entire section unless the ticket fixes a bug or regression.

- Reproduction: `<exact command or interaction and observed failure>`.
- Causal model: `<direct facts and evidence-backed inference connecting the
  failure to the named production owner>`.
- Decisive check: `<cheapest check that can falsify the causal model>`.
- Re-diagnosis condition: `<evidence that makes the implementation owner stop
  before adding another workaround and return to diagnosis>`.

## Implementation sequence

The author lists steps toward the acceptance behavior below, not separate
behavior contracts or new failing tests for each intermediate result. Reference
the applicable A-id rather than redefining its behavior or expected result.

1. `<Owner>` changes `<exact symbol/file>` when `<condition>`, producing
   `<intermediate result required by this ticket>`.
2. `<Caller or adapter>` consumes `<exact interface>` when `<condition>`,
   producing `<observable integration result>`.
3. `<Verification owner>` observes `<seam/check>` under `<input/state>`,
   proving `<acceptance behavior>`.

## Acceptance and verification

The author includes only product-contract results under the boundary/preflight
contract. Name the later ticket or final-gate owner for behavior awaiting an
unfinished dependency; do not make temporary behavior pass as a substitute.

### A1 — <Acceptance behavior>

- Behavior: `<Actor>` performs `<action>` on `<object>` when `<condition>`,
  producing `<observable result>`.
- Source: `<spec/ADR/recorded user-approved requirement>`.
- Seam or direct check: `<stable public production seam or deterministic
  existing check>`.
- Check: `<stable check/gate id and defining section or declared input path>`.
- Expected: `<specific pass result, output, state, or side effect>`.
- Runtime authenticity (UI/live app only): `<target runtime, refresh or reset
  action, direct success observation, and evidence distinguishing it from a
  mock, cached result, screenshot-only state, forced state, or stale renderer;
  first-failure captures using existing evidence, diagnostic question and bounded
  attempts/duration; changed conditions are diagnostic evidence for those conditions>`.
- Verification witness: `<for a named boundary test, lifecycle/resource proof,
  negative scan, generated-consumer check, or other correctness-critical item:
  production producer; legal fixture; numeric/state reachability; every legal
  oracle result; direct observation; and how absence is detected>`, or
  `Not applicable — <direct property proved by this mechanical check>`.

## Baseline verification preflight

Include one entry for every ticket-scoped check and feature final gate. The
author runs this preflight before candidate publication.

### `<check-or-gate-id>`

- Applies to: `<ticket-scoped | feature-final>`.
- Check: `<check-or-gate-id above; resolves its single command definition>`.
- Baseline expectation: `<pass | intentional-fail | implementation-dependent>`.
- Preflight command or interaction: `<exact distinct non-mutating baseline
  check, or reference to the check command when identical>`.
- Expected baseline result: `<exit code, failure signature, target/path result,
  or runtime prerequisite>`.
- Observed baseline result: `<exact observed exit code or interaction result and
  bounded diagnostic signature; if masked by a proven shared prerequisite failure, reference its evidence and the condition for running this check>`.
- Counterfactual failure probe: `<reference to applicable execution-integrity/red
  evidence, or cheapest non-mutating probe for a specific remaining gap>`, or
  `Not applicable — <why this check has no separate correctness witness>`.
- Observed failure-probe result: `<retained evidence/result and applicability,
  or exact nonzero exit, mismatch, or diagnostic from the new probe>`.

Shared evidence is referenced once. A production mutation experiment needs the
explicit requirement or concrete false-green risk, smallest experiment and
invalidation conditions required by `verification-realizability.md`.

## Ticket-scoped checks

These checks are run only by the current ticket supervisor before ticket
assurance. They must be focused enough to diagnose this ticket's acceptance
behavior without substituting for feature integration closure.

### `<stable-check-id>`

- Acceptance: `<A1 or another acceptance identifier>`.
- Working directory: `<exact repository-relative directory, qualified for multiple repositories>`.
- Command or interaction: `<exact focused command or target-runtime protocol;
  for expensive runs, the minimum required selector/target, parameter sources,
  result writer/artifact and parser, and explicitly consumed prior evidence>`.
- Expected: `<exit/result criterion and referenced A-ids; no second behavior oracle>`.

## Feature final gates

Each gate is declared by exactly one owning ticket or execution plan and must
run once after all implementation tickets are accepted. Use
`None — this ticket owns no feature final gate.` when inapplicable.

### `<stable-gate-id>`

- Owner: `<this ticket, named validation-only ticket, or execution plan>`.
- Working directory: `<exact repository-relative directory, qualified for multiple repositories>`.
- Command or interaction: `<exact cumulative build, integration, publication,
  delivery, or target-runtime protocol; identify the required selectors,
  parameter sources, result writer/artifact and parser before expensive runs>`.
- Expected: `<execution criterion plus A-id or authoritative feature result reference>`.
- Reuse assessment: `<reusable | always-run>`.
- Always-run reason: `<external/uncertain input or incomplete deterministic
  boundary>`, or `None — the complete reusable input boundary is declared below.`
- Historical runtime evidence after repairs (optional): `<explicit authority
  permitting retention within this run; acceptance claim, raw evidence and
  relevant production/test/build/deployment/model inputs, invalidating changes,
  and any current-state or fresh-interaction requirement>`. Omit without that
  authority; `always-run` then runs normally. This is not repository-only reuse
  and does not declare external state `None`.

State how the final-gate supervisor reports a genuinely unavailable device or
external dependency; do not substitute a weaker check and call it passed.

## Reusable gate inputs

Remove only this Reusable gate inputs section unless a feature final gate has a
provably complete repository-only input boundary and its reuse assessment is
`reusable`. Keep the Feature final gates entry and its
`always-run` reason when reuse cannot be proved.

### `<stable gate id>`

- Gate: `<stable gate id above; resolves the Feature final gates command>`
- Inputs:
  - `<exact tracked repository-relative file or directory>`
- External state: `None — reusable within the same execute-tickets run.`

## Non-goals and state budget

- Unchanged behavior/owners: `<exact adjacent contracts that must not change>`.
- Forbidden additions: `<mutable state, lock, retry, abstraction, cleanup
  owner, test seam, compatibility layer, or public interface not authorized>`.
- State budget: `<exact allowed new production fields/locks/executors/retry
  branches and their production justification>`.

## Stop conditions

- If `<authority, owner, interface, scope, seam, prerequisite, ticket-scoped
  check, feature final gate,
  condition>` occurs, `<named executor/orchestrator>` stops before
  `<prohibited action>` and returns the ticket to `<spec owner/user/execution
  flow>` with `<required evidence>`.
```
