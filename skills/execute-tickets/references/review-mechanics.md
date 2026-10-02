# Immutable working-tree review mechanics

Read this file before a standard/high-risk ticket review. The Git index contains
the accepted feature baseline, so commit-range review is the wrong input.

Before capturing Review 1, require every implementation worker to have ended.
The ticket supervisor must have inspected every worker's complete delta,
integrated package boundaries, and personally run the complete ticket-scoped
checks. A worker handoff or focused PASS is not review input and cannot satisfy
`implementation_ready`. Do not run implementation workers and reviewers at the
same time.

## Snapshot artifacts

For a repository set, use `multi-repository.md`: all patch/manifest paths below
are per-member `repositories/NAME/` paths, file references are `NAME:path`, and
the review identity binds the aggregate plus every member snapshot hash. Both
review axes cover the complete ticket with each repository's own standards.
The integration-review index records a repository-to-index-hash map and separate
cumulative patch paths; a parent gitlink diff never substitutes for child code.

After `implementation_ready`, capture against the ticket's exact pre baseline:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --output .execute-tickets/<feature>/<ticket>/review-N \
  --baseline .execute-tickets/<feature>/<ticket>/pre
```

When a prior drift disposition classified protected external state, also pass its
`--drift-resolution <resolution.json>`. The command rejects HEAD/index drift.
An ordinary protected-path change that cannot affect the ticket is automatically
preserved outside the review delta and Git index without pausing review. Route an
affecting or non-isolatable change through `references/working-tree-drift.md`;
after reconciliation, rerun every check that can observe the external path and
capture a fresh snapshot. Reviewer
content input is:

- `ticket-tracked.patch`: complete index-to-final diffs for dirty tracked scope
  paths, including content that was already unstaged when scope was accepted;
- `ticket-untracked.patch`: immutable full patches for final untracked scope files;
- `ticket-untracked.json`: those scope-file paths and hashes;
- for a ticket that changed existing Markdown, the supervisor's
  `document-deletion-audit.md` and its verified SHA-256;
- current ticket/spec/standards and live repository context.

For that audit, the orchestrator verifies the envelope SHA-256 before dispatch,
each reviewer hash-checks the file before reading it, and the orchestrator
recomputes the hash after review. Audit drift invalidates both reports just like
snapshot drift.

`unstaged.patch`, `status.txt`, and the full untracked manifest are
orchestrator-only integrity artifact bodies. The orchestrator verifies them
before and after review and gives reviewers only the verified snapshot identity,
protected path summary, and relevant hashes. Reviewers must not read `unstaged.patch` or
use protected outside-scope content as review input; `ticket-tracked.patch` and
`ticket-untracked.patch` already contain the complete current-ticket candidate.

An empty tracked patch may still have scope-owned untracked files. Earlier staged
ticket lines may appear only as patch context. Reviewers assess the complete
candidate on exact scope paths; pre-existing content outside scope is context
only and remains protected.

## Adapt the code-review skill

Reuse the installed `/code-review` skill's Standards discovery, smell baseline,
Spec axis, reviewer briefs, and separate reports, but do not invoke its
commit-oriented flow as a black box.

- Do not resolve a fixed-point ref or run three-dot diff/`git log`.
- Identify the review by ticket, run HEAD, pre-ticket index hash, and snapshot
  hashes.
- Treat tracked delta or a non-empty new-file manifest as non-empty review input.
- Replace commit-diff prompt inputs with the reviewer content artifact paths
  above; do not pass orchestrator-only integrity artifact bodies.
- Never use `git diff <fixed-point>...HEAD`; it cannot see this staged/unstaged
  execution model.

For discovery the waiting supervisor starts fresh read-only Standards and Spec
reviewers in parallel; closure follows `review-policy.md` reviewer continuity.
It gives both the reviewer content artifact paths, repository root,
ticket/spec/standards inputs, verified snapshot identity, protected path
summary, and instructions to hash-check every new file. Findings must concern
the current ticket delta; full live files are context only.

When existing Markdown changed, add this explicit task to the Standards reviewer
brief without modifying the Standards reviewer implementation: compare every
row of `document-deletion-audit.md` with the ticket's documentation edit
contract, current authority, complete patch, and live replacement. Report a
finding when `replaced` does not preserve the original responsibility,
`superseded` lacks authority proving that responsibility or fact no longer
exists, a mixed unit was not split, or the patch contains an unrecorded deleted
or wholly replaced heading section or fenced code block. Do not infer failure
from line count, fenced-block count, or Mermaid count.

The Spec reviewer checks final scope trace, `Consumes`/`Produces`, acceptance,
non-goals, state budget, and stop conditions. For each correctness-critical
check it also verifies the legal production producer and fixture, reachability,
complete oracle, direct observation, and applicable absence evidence against the
final test/scan implementation and retained logs under `admission-preflight.md`.
Inspect behavioral assertions separately from execution integrity; do not demand
one production mutation or probe replay per branch merely to fill the matrix. It must not turn an untraceable
implementation preference into a requirement or infer a witness from a green
command alone.
Both reviewers apply `review-policy.md` to distinguish contract violations from
temporary-state or proxy-observation differences. Requests for more tests must
identify an unproved contract and concrete production path in the final candidate;
reviewers use structural elimination evidence when that path no longer exists.
For an existing-Markdown change, it also verifies that every still-current
responsibility promised by the documentation edit contract has the ticket's
positive replacement output and is present in the final candidate.

For closure and regression-closure briefs, include the frozen finding IDs,
prior/current per-path hashes, and exact repair hunks. Reviewers may keep an
original finding open only by citing its original unmet oracle. A new repair
regression must cite an explicit frozen authority statement and demonstrate
that the defect disappears when the repair delta is removed; a defect already
present in the discovery snapshot is late discovery and cannot be opened in
closure. Do not dispatch a closure brief at all for an accepted micro repair.

For record-only corrections, apply verification-by-repair-content in
`review-policy.md`; preserve frozen reports and use the existing disposition.
Evidence references do not require reproducing the same diagnosis in every
matrix/report, and a trustworthy raw result does not need another command run
merely because its summary was wrong.

Reports stay in the ignored run-artifact tree. The supervisor emits `review_complete` with
separate statuses, finding IDs, report paths, and hashes, then waits. The
orchestrator runs:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py verify \
  --snapshot .execute-tickets/<feature>/<ticket>/review-N
```

Verification failure invalidates both reports. On success, return
`review_input_valid`; the supervisor fixes findings or, when both axes pass
with every finding disposed, that final `review_complete` on the verified
snapshot is itself the acceptance evidence and the orchestrator proceeds to
protected staging. Never average the axes.
The same supervisor fixes actionable findings; do not dispatch an implementation
worker after review begins.

## Adapt the final review as an integration review

After targeted repair review, apply the single-owner targeted closeout in
`review-policy.md` before scheduling cumulative closure. It never omits initial
integration discovery. The existing index records the verified closeout and
retains original failing reports; summaries do not fabricate another PASS.


The final review is not another line-by-line ticket review. During serial ticket
completion, the orchestrator incrementally writes
`.execute-tickets/<feature>/integration-review-index.md` from the current
ticket and retained bounded envelopes while those inputs are already in context.
It does not reconstruct accepted rows by rereading complete prior tickets or
reports. Before reviewer dispatch, the final-gate supervisor adds final snapshot
and gate-result rows, verifies the complete index, and freezes its SHA-256. It
contains:

- final snapshot, HEAD, index, and cumulative `staged.patch` path/hash;
- one changed-path manifest, grouped by accepted ticket;
- each cross-ticket `Consumes`/`Produces` edge and its accepted path hashes;
- each shared state/resource/cleanup owner and applicable ordering row;
- per-ticket completion outcome, review status, finding IDs/dispositions,
  report path/hash, and recorded deviation, without copying report prose;
- each final-gate id, result, evidence path/hash, and reuse decision.

Use this fixed compact ticket section; repeat list entries only when the ticket
actually owns more than one item:

```markdown
## Ticket `<number>`
- Ticket: `<path>` — SHA-256 `<hash>`
- Accepted: index `<hash>`; paths `<path>=<hash>, ...`
- Interfaces: `<consumer Consumes> -> <blocker Produces verbatim row + source hash>, ...`
- Owners/order: `<state/resource/cleanup owner + ordering-row source hash>, ...`
- Review: `Standards <status, finding ids/dispositions, report path/hash>; Spec <...>`
- Completion/deviations: `<outcome>; <None or bounded facts>`
- Final gates: `<id, owner, command/interaction hash, reuse class>, ...`
```

Before dispatch, verify that the index has one ticket section for every
completed ticket and includes every cross-ticket edge, shared owner, and final
gate exactly once with matching retained identities and hashes. An omission or
mismatch blocks final review. Do not copy patch hunks, full reports, or command
logs into the index.
The index is verified routing evidence, not behavior authority. It preserves
verbatim interface/ordering rows and their source hashes; it cannot add a
requirement, weaken a ticket, or resolve a mismatch.

Give discovery reviewers these immutable inputs in two tiers; closure reuses
the original per-axis reviewers with the new identities and repair evidence:

First-pass inputs:

- the integration review index;
- the feature spec, superseding ADRs, and applicable ordering/ownership tables;
- final-gate inventory and results.

On-demand evidence paths:

- the complete staged feature patch and final snapshot identity;
- every ticket's accepted per-path hashes, ticket acceptance reports, Standards
  and Spec reports, and bounded completion record;
- final-gate logs and reusable-input evidence.

Each reviewer reads the index first, forms an integration-boundary checklist,
then reads only the exact path sections or hunks from `staged.patch` needed for
those boundaries. It loads a historical report body only when an indexed edge,
owner, deviation, gate result, or finding requires that evidence. It must not
linearly read the complete patch or every historical report merely because the
paths are available. The complete staged.patch remains available for direct
inspection, and reviewers may inspect any relevant line; earlier ticket reports
are evidence, not a mechanism for hiding code. Reviewers focus on integration
boundaries that a ticket-local review cannot prove. An integration finding must
name the affected producer/consumer or shared owner, exact conflicting contract
and boundary evidence; calling a local preference “integration” does not qualify:

- exact `Consumes/Produces` compatibility and migration-state handoffs;
- shared state, shared admission, and cleanup ownership across tickets or
  facade reacquisition paths;
- lifecycle linearization and deterministic interleavings across threads,
  callbacks, endpoints, wire/process boundaries, and repairs;
- public API and wire compatibility, externally visible result/error semantics,
  routing, and cross-process failure handling;
- cumulative build, publication, packaging, runtime, documentation, and
  delivery closure.

Reviewers must not re-audit byte-identical ticket-local implementation merely to
open ordinary style or local-spec findings already covered by passing ticket
reports. They may inspect any line needed to establish a boundary and may report
a new P0/P1 anywhere in the full patch when integration evidence exposes a race,
resource leak, contract break, or data/security defect. New integration-specific
P2/P3 findings are allowed; unrelated ticket-local P2/P3 findings become backlog
instead of reopening accepted tickets.

The Standards and Spec axes remain separate. Standards assesses cross-ticket
architecture, ownership, and delivery consistency; Spec assesses cumulative
observable behavior, interfaces, ordering authority, non-goals, and feature-gate
evidence. Freeze both reports' combined finding set before any repair.

Any final repair invalidates the frozen index together with the prior snapshot.
Update only the affected ticket/path/edge/owner and gate-result rows from the new
verified evidence, then freeze a new index SHA-256 before closure review or
verified single-owner closeout. Keep
the prior index and hash as discovery evidence; never silently reuse it.
