# Local Markdown implementation-ticket contract

This bundled contract is the portable execution boundary for `execute-tickets`.
It is sufficient even when a target repository has no `docs/agents/` directory
or issue-tracker document.

## Authority and repository overlays

- Apply the target repository's governing instructions, including every
  applicable `AGENTS.md`, coding standard, specification, ADR, and domain
  document.
- Use `docs/agents/issue-tracker.md` as the authority for the feature's spec and
  ticket directories. Treat its other rules as optional overlays. They may add
  stricter admission checks, evidence requirements, or stop conditions that
  are compatible with this contract.
- Stop before execution when a repository overlay changes the status field,
  lifecycle states, transition owner, or meaning of `done` below.
  Do not average the contracts or silently select one.
- Do not import unrelated tracker protocols. In particular, triage roles and
  wayfinding states such as `claimed` or `resolved` are outside this contract.

## Spec and ticket directories

Before a new run or resume, the orchestrator reads the target repository's
`docs/agents/issue-tracker.md` when present and resolves two repository-relative
directories: `<spec-dir>` contains this feature's `spec.md` and
`implementation-ticket-admission.json`; `<tickets-dir>` contains this feature's
implementation tickets. The tracker may place tickets outside the spec directory.
The orchestrator stops if the tracker is unreadable, either directory is
unspecified or ambiguous, or a directory resolves outside the repository.
Missing files in a declared directory block execution; the orchestrator never
searches another directory or falls back to `.spec` in that case.

Only when the tracker document is absent, the orchestrator uses `<spec-dir>` =
`.spec/<feature>` and `<tickets-dir>` = `.spec/<feature>/issues`:

```text
.spec/<feature>/
├── spec.md
├── implementation-ticket-admission.json
└── issues/
    ├── 01-<slug>.md
    └── NN-<slug>.md
```

Each implementation ticket is a Markdown file at exactly
`<tickets-dir>/<NN>-<slug>.md`. Ticket numbers are unique within
the feature.

The orchestrator passes both resolved directories as `--spec-dir` and
`--tickets-dir` to `admission_state.py verify`, and passes `--tickets-dir` to
`ticket_state.py show` and `complete`. These arguments carry the orchestrator's
reading of the tracker; scripts validate paths rather than interpret Markdown.
Omitting a directory argument is allowed only without the tracker, using the
fallback above. The orchestrator checks the directories against the authoring
handoff and, on resume, the retained authority paths; disagreement stops the run
before mutation. The orchestrator gives the resolved directories and their
tracker source (or its absence) to each fresh supervisor.

These files are process documents. They are the run's authority, not its
deliverable. A repository may keep them tracked, untracked, or excluded by
`.gitignore`; execution never requires them to be tracked and never newly stages
them. Any authority path already staged by the user at run-start remains in the
frozen staged baseline.

## Authority admission state

Before a new execution run starts, the feature's `spec.md`,
`implementation-ticket-admission.json`, and every implementation ticket must
match the content hashes recorded in the admission receipt. On resume, the
unchanged run-start receipt establishes the original path set and retained
repair/completion transitions establish every later path and byte. Authority integrity
is content-addressed whether or not Git tracks these paths.

For `spec.md` the receipt covers its **authority body**: a well-formed leading
presentation block, whose only allowed key is `display_title`, sits outside the
admitted bytes. Renaming that label therefore leaves admission valid, matching
the authoring skill — a requirement's human-readable name is not a requirement.
Any malformed block, and every ticket byte, stays authority.

The orchestrator freezes that authority set into every snapshot by passing
`--receipt` with the feature's admission receipt; `review_state.py` derives the
exact path set from the receipt — the spec, the receipt itself, and every
recorded ticket — and records each path's SHA-256, so the run-start set can never
disagree with what admission verified. The snapshot makes the stricter promise
that nothing moved during this run, so it freezes whole-file bytes and rejects
any authority byte that changes without an approved transition, presentation
label included. Stop before execution when a required authority file is missing,
unreadable, or disagrees with the receipt.

Execution must not add process documents to the accepted baseline.
`review_state.py stage` refuses to newly stage any declared authority path, but
preserves authority already present in the user's run-start index. A
`ready-for-agent -> done` transition changes the document on disk and is proved
by a recorded content-hash transition instead of a new staged diff.

If execution exposes an authority gap, block the affected ticket before editing
the spec or ticket contract. When stable evidence outside the proposed repair
uniquely proves a behavior-preserving correction in the spec or an unfinished
ticket, use the execution-authority-repair transaction below. A material
authority gap returns to its decision owner; after that owner records the exact
choice, execute applies it through the same transaction. The active run never
calls write or replaces its run-start admission receipt.

A verification-only contract repair is not a behavior-authority change. It applies when
the authoritative behavior and expected result are already explicit, but a test,
fixture, regex, scan path, or command in the current ticket mechanically rejects
that same required result. The supervisor diagnoses the contradiction; the
orchestrator may then change only the current ticket's verification text and
record that edit as an approved authority transition against the current
ticket baseline:

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --output .execute-tickets/<feature>/<ticket>/contract-repair \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --authority-transition-path "<tickets-dir>/<ticket>.md"
```

The capture requires the declared path to have actually changed, keeps `HEAD`,
the index, and every other authority file byte-identical, and records the
before/after SHA-256 pair. Use that snapshot as the new current-ticket baseline
before the supervisor continues. This repair must not change observable
behavior, acceptance sources,
scope, non-goals, state budget, `Blocked by`, or a completed blocker's contract.
Record the corrected command and reason in the completion record; do not ask the
user for this bounded repair.

Execution authority repair is the second bounded execution-time authority
transition. It applies when current spec, ADR,
completed-blocker evidence, production declarations/callers, or existing tests
uniquely prove an unfinished ticket omitted a ticket-order edge, exact production
or test-only scope path, discovery disposition, verifier artifact, or mechanical
verification detail while accepted behavior remains unchanged. It also permits
a spec clarification when a recorded user decision or ADR already determines
the same behavior. A stable source outside the proposed repair must determine
the result; code alone cannot choose new product behavior and a changed verifier
cannot authorize itself.

The supervisor with the live code context diagnoses the defect and returns its
exact smallest correction. The orchestrator freezes the current run state and
affected process documents, applies that correction only to the spec and named
unfinished tickets, and records every changed path through
`review_state.py capture --authority-transition-path`. It does not invoke
`write-implementation-tickets`, dispatch an authoring reviewer, or rewrite the
receipt. It then reruns only affected deterministic admission checks, captures
a new current-ticket `pre` snapshot when scope changed, and resumes the same
supervisor. Completed-ticket bytes, the receipt, HEAD, index, accepted
implementation content, and protected outside-scope state remain byte-identical.
Failure restores the retained process documents or leaves the run stopped at
the repair checkpoint; no half-recorded transition may continue.

When a behavior-preserving ticket-boundary correction changes the unfinished
ticket path set, the orchestrator retains the current ticket path, passes the
complete post-repair authority set with repeated `--authority-path`, and declares
every added or removed path with `--authority-transition-path`. Added paths
record a null before-hash, removed paths a null after-hash, and renames declare
both sides. The next snapshot carries the resulting set; the frozen receipt and
completed-ticket paths remain unchanged.

This transaction never autonomously decides observable behavior, public
interfaces, production ownership, runtime state semantics, unresolved review risk, or new
destructive, credential, external, Git-history, or device authority outside the
ticket-declared bounded `adb` real-device verification lane. Those are material
decisions and remain stop conditions until their owner records an exact answer;
once recorded, execute updates current authority directly without returning to
write review.

## Scheduling metadata

Each ticket contains exactly one status line near the top:

```markdown
**Status:** ready-for-agent
```

The only implementation-ticket states are:

| Status | Meaning |
| --- | --- |
| `ready-for-agent` | The ticket is eligible when its exact feature authority has a valid `admitted-by-review` or `admitted-by-user` receipt and all declared blockers are accepted. |
| `done` | The orchestrator accepted and staged the ticket implementation, and recorded verification evidence plus one inline completion record in the same ticket. |

Each ticket also contains one `**Blocked by:**` field. `None` means the ticket
has no blocker. Otherwise the field names every ticket number whose accepted
interface or evidence this ticket consumes.

A blocker is complete only when both of these are true:

1. Its ticket status is `done`.
2. The same ticket file contains exactly one readable `## Completion record`
   identifying the accepted-content index hash and verification/assurance outcome.

## Completion transition

For multiple repositories, `multi-repository.md` supplies the aggregate snapshot
and repository-to-index-hash map for the existing completion protocol. The
orchestrator must pass the accepted aggregate through `ticket_state.py complete
--snapshot`; a member-only check cannot authorize completion. The bounded
`Accepted implementation` field lists each repository and its index hash instead
of one scalar hash. Verification requirements remain spec/ticket-owned.

The orchestrator is the only actor that changes an implementation ticket from
`ready-for-agent` to `done`. A supervisor finishing implementation, tests, or
review does not change ticket state by itself.

The orchestrator performs the transition only after protected implementation
staging succeeds and a bounded completion record is ready in the ignored
run-artifact tree.
It uses the single atomic command
`ticket_state.py complete --ticket <path> --record-file <path> --receipt <path>
--output <evidence-dir>` rather than editing the ticket freehand. The command
freezes an internal baseline, appends the record, performs
`ready-for-agent -> done`, proves that HEAD, the index, the working tree, and
every other authority file are byte-identical while the current ticket actually
changed, and retains the before/after SHA-256 pair as durable evidence.
Repeating it with the identical record is idempotent; a failed proof restores
the exact pre-transition ticket bytes. Any other state or a conflicting record
stops completion.

The orchestrator unlocks dependants only after that retained transition
evidence exists, `ticket_state.py show` prints exactly `done`, and the inline
record names the accepted-content index hash. The transition never enters the
Git index.

The inline completion record proves acceptance; it does not create behavior.
The spec, ADRs, and the completed ticket's declared `Produces` contract remain
the authority consumed by dependant tickets. Raw logs, patches, snapshots, and
review reports stay in the ignored run-artifact tree.

Use this exact bounded record shape. `Deviations` may clarify execution facts but
must not change observable behavior:

```markdown
## Completion record

- Execution mode: `<direct|test-after|tdd>`
- Assurance lane: `<micro|standard|high-risk>`
- Accepted implementation: `<accepted-content index hash>`
- Verification:
  - `<exact command>` — exit `<code>`; `<bounded result>`
- Reviews:
  - Standards — `<pass/fail and unresolved finding count, or not required: micro lane>`
  - Spec — `<pass/fail and unresolved finding count, or not required: micro lane>`
- Deviations: `<None or bounded clarification>`
```

Do not persist log paths or hashes, patch or snapshot hashes, reviewer report paths,
or reviewer report bodies in the ticket.

## Cold-start admission contract

Before a ticket becomes `ready-for-agent`, a fresh executor must be able to
implement and verify it without conversation history or guessing. Headings may
vary, but the ticket must contain:

- **What to build:** the bounded observable result and owning actor.
- **Authoritative inputs:** the exact spec, ADR, completed-blocker evidence, and
  repository sources that establish the contract, including superseded inputs.
- **Scope:** the production owner and exact files, or a bounded discovery rule
  that decides whether each additional path may enter scope.
- **Scope closure preflight:** the exact permitted-discovery command or an
  explicit no-discovery result, authoring baseline, per-path dispositions, and
  `0 undisposed paths`. Execution reruns each command after blockers complete.
- **Slice boundary:** one acceptance unit, every changed lifecycle/state/cleanup
  owner, the independent-rejection result, fresh-context fit, and a split
  trigger. A semantic epic is not executable merely because its paths are exact.
- **Interfaces:** exact `Consumes` and `Produces` rows for every cross-ticket
  dependency, or an explicit `None`.
- **Behavior contract:** reference each acceptance A-id defining its actor,
  action, object, condition and observable result. Unique section/check references
  satisfy the fields below when they resolve in declared inputs. Missing, cyclic
  or conflicting references do not. Existing consistent expanded tickets remain valid.
- **Documentation edit contract:** for every existing Markdown write path,
  `surgical` or explicitly authorized `whole-document` mode, authority, preserved
  responsibilities, and required replacement outputs.
- **Ordering and ownership contract (when applicable):** cited spec or ADR
  authority identifies actor/thread, state owner, resource owner, linearization
  point, competing operations, failure owner, observable result, and
  deterministic interleaving evidence for lifecycle, concurrency, cancellation,
  retry/recovery, cleanup, routing, or cross-process behavior.
- **Failure model (bugs and regressions):** the reproducible failure,
  evidence-backed causal model and production owner, decisive falsifying check,
  and condition that returns the work to diagnosis before another workaround.
- **Non-goals and state budget:** behavior, owners, mutable state, retries,
  abstractions, test seams, and adjacent contracts the ticket must not add.
- **Acceptance and verification:** an authority source and stable production
  seam or deterministic direct check for every acceptance item, plus exact
  commands or interaction protocols and expected results.
  UI, browser, device, or live-app acceptance that must run in the target
  runtime also names the interaction path, refresh or reset action, and direct
  observation that distinguishes success from a mock, cache, screenshot-only
  state, forced state, or stale renderer.
- **Verification witness (when applicable):** every named boundary test,
  lifecycle/resource proof, negative scan, generated-consumer check, or other
  correctness-critical item names its production producer, legal fixture,
  reachability, complete legal oracle, direct observation, and observed or validly reused absence evidence under the owning verification contract.
- **Baseline verification preflight:** every ticket-scoped check and feature
  final gate declares `pass`, `intentional-fail`, or
  `implementation-dependent`, plus the exact non-mutating preflight, expected
  baseline result, and observed authoring result. Before `scope_ready`, the
  supervisor runs it or records applicable evidence reuse/proven shared-prerequisite
  masking under `admission-preflight.md`; only a named completed blocker's
  `Produces` contract may explain changed behavior. Masked checks remain unproved
  until executed after the prerequisite repair.
- **Ticket-scoped checks:** focused verification run only by the current ticket
  supervisor before ticket assurance.
- **Feature final gates:** cumulative verification declared once by an owning
  ticket or execution plan and run once after all implementation tickets are
  accepted. Every gate has a stable id, exact command/interaction, expected
  result, owner, and `always-run` or `reusable` assessment.
- **Reusable gate inputs (optional):** complete input boundaries for each gate
  assessed `reusable`; omit this section when every gate is `always-run`.
- **Stop conditions:** ambiguities, ownership conflicts, missing seams, failed
  prerequisites, proposed scope expansions without one authority-backed answer, and
  protected working-tree drift that requires a recorded disposition before
  execution continues.

## Admission decision receipt

`implementation-ticket-admission.json` separates immutable reviewer outcome
from execution admission:

- `admitted-by-review` records `PASS`, or `PASS_WITH_CORRECTIONS` with the
  reviewer's frozen correction IDs, and no unresolved finding.
- `admitted-by-user` preserves the failed review and records one explicit user
  disposition and reason for every unresolved finding.

The authoring owner creates the candidate manifest and receipt. A fresh reviewer
may admit exact bytes with `PASS`, or admit author-corrected bytes with
`PASS_WITH_CORRECTIONS` when the receipt records the reviewer's frozen
correction IDs; the user may instead admit an unresolved
candidate explicitly but does not calculate hashes. The execute orchestrator
does not generate or reinterpret a receipt. Any spec/ticket path-set or byte
change before a new run-start invalidates admission. After run-start capture,
checkpointed completion, bounded verification repair, and execution authority
repair may change declared process-document paths and bytes. The run-start
receipt remains unchanged; resume uses it for the original authority path set
and retained repair/completion transitions for every later path and byte.

A clarification may make an existing contract explicit but must not silently
add behavior. When observable behavior changes, update the authoritative spec,
ADR, or recorded user-approved source before aligning the ticket. Preserve
completed tickets as historical evidence; record later contracts separately.
