---
name: write-implementation-tickets
description: Turn a repository specification into implementation tickets that an agent can execute independently. Use when the user asks to break a spec or feature into implementation tasks, prepare tickets for development, or turn requirements into an actionable implementation plan.
compatibility: Requires Git, Python 3.10+, ripgrep, sub-agents with fresh-context support, and local Markdown tickets in the repository tracker directories or the bundled .spec fallback.
---

# Write Implementation Tickets

Convert one repository spec into implementation tickets that a fresh executor can
implement and verify without conversation history or design guesswork.

Resolve `<write-implementation-tickets-skill-root>` to this `SKILL.md`'s
absolute parent. Never resolve bundled resources through a repository-local
skill path.

## Progressive loading map

Read each reference in full when its phase begins. Do not preload later-phase
references merely because the skill triggered.

| Phase | Read in full |
| --- | --- |
| Before resolving target-repository inputs | `references/local-markdown-contract.md`; optionally `references/authoring-timing.md` for diagnostic timing |
| Before building the implementation map or ticket graph | `references/ticket-boundaries-and-verification-preflight.md` |
| Before writing complete ticket contracts | `references/ticket-template.md` and `references/verification-realizability.md` |
| After final candidate ticket files are written, before reviewer dispatch | `references/author-review-protocol.md` and `references/repository-alignment-review.md` |
| After the review chain reaches an admission decision point and authority bytes are stable | `references/admission-and-handoff.md` |

On resume, load the local Markdown contract first, validate which phase has
durable evidence, then load only the references for the phase being resumed. A
missing or unreadable required execution reference stops before that phase. Optional timing instructions, tools, or data may be absent or unreadable: report the gap once and continue, including handoff, without repairing or retrying statistics.

This skill owns detailed ticket contents, the authoring template, graph
construction, admission checks, author self-review, and mandatory independent
repository-alignment review. The bundled
contract owns directory resolution, lifecycle, dependency metadata, and
minimum admission semantics. The repository tracker owns spec and ticket
directory placement and nesting; the bundled contract owns the feature
directory name. The tracker's other rules are optional compatible overlays.
When used
downstream, `execute-tickets` owns execution and
acceptance, but this authoring skill does not require it to be installed. Do not
invoke the generic `to-tickets` skill as an intermediate step; its lightweight
tracker-neutral output is not the bundled implementation-ticket contract.

Announce at the start: "I'm using the write-implementation-tickets skill to
prepare cold-start implementation tickets."

This skill separates authoring from review. The author reads the repository,
drafts the graph, resolves every authority-backed mechanical decision, writes
final ticket files, and fixes valid findings. One fresh read-only reviewer performs
the admission review. If it finds only authority-backed corrections that create
no new product or architecture decision, the author applies them once and uses
deterministic checks; no second model reviews the corrected wording.
Reviewers do not receive the authoring conversation or private implementation
map. They must not edit the repository.

## Required inputs

Resolve these inputs before drafting:

1. The bundled local Markdown contract.
2. The target repository root and every applicable governing instruction,
   including any `AGENTS.md` and standards files when present.
3. The feature's spec and ticket directory placement, resolved from
   `docs/agents/issue-tracker.md` when present, and the feature directory name,
   resolved from the bundled contract. Only when that document is absent, use
   `.spec/<feature>/` for the spec and `.spec/<feature>/issues/` for tickets.
4. One authoritative `<spec-dir>/spec.md`, read in full, plus domain
   documentation and relevant ADRs when present. Its optional presentation
   block holds a `display_title` label that no ticket cites as authority.
5. Existing implementation tickets and their inline completion records for the feature.
6. Current production owners, immediate callers, shared utilities, tests, and
   public documentation for the affected behavior.

The repository tracker owns both directories' placement and nesting; they need
not share a parent. The bundled contract owns the feature directory name.
Treat its other rules as optional compatible overlays. They may add stricter
admission checks, evidence requirements, or stop conditions.
If an overlay changes the status field, lifecycle states,
transition owner, blocker meaning, or meaning of `done`, stop before drafting;
do not average the contracts. Absence of `AGENTS.md`, `docs/agents/`, or a
repository issue-tracker document does not block authoring.

Conversation history, a loose plan, or a parent issue may help locate the work,
but it is not a durable behavior source. If an observable requirement exists
only in conversation, record it in the spec, an ADR, or another user-approved
repository source before publishing tickets. Do not turn an unrecorded
assumption into `ready-for-agent` work.

If the spec combines independent subsystems that can deliver and be reviewed
without shared state or ownership, propose separate specs before ticketing. Do
not split one lifecycle or state model merely because several technical layers
are involved.

`execute-tickets` never invokes this skill from an active execution run. Its
run-start receipt freezes the authoring baseline; execution owns later
checkpointed corrections to the spec and unfinished tickets. A separate user
request to re-author after that run is a new authoring operation, not an
execution repair.

## Authoring process

### 1. Establish authority and terminology

Read the spec, ADRs, completed blocker evidence, domain documentation, and
relevant current code. Resolve conflicts by authority:

1. Current spec or superseding ADR.
2. Recorded user-approved decision.
3. Current production interface and invariants.
4. Tests that express business intent.

Name superseded sources explicitly. Reuse the project's identifiers and domain
terms; do not invent smoother synonyms. For each required behavior, write:

`[Actor] performs [action] on [object] when [condition], producing [observable result].`

If the sources disagree about observable behavior or the real owner is unclear,
stop and ask the user. Ticket authoring must expose the conflict rather than
average it.

Before slicing tickets, ask the user for the delivery and release granularity
preference: which deliverables may ship independently and which must ship as
one batch. A granularity decision that arrives after tickets are reviewed is a
user-authority change that forces a new exhaustive review epoch over every
affected ticket, so an unasked preference is expensive rework, not a neutral
omission.

### 2. Build the implementation map

Read
`<write-implementation-tickets-skill-root>/references/ticket-boundaries-and-verification-preflight.md`
in full before building the map. It owns semantic-ticket admission,
lifecycle/concurrency ordering, scope closure, and baseline preflight.

Codebase exploration is mandatory for implementation tickets. Read each
affected declaration, its production callers, obvious shared utilities, and the
tests at the stable production seam. For API/wire migrations, include existing
generated consumers and verifier scripts under the scope-closure contract.

Build a private implementation map with one row per required behavior:

| Field | Required evidence |
| --- | --- |
| Source | Exact spec section, ADR, or recorded user decision |
| Actor and owner | Real production owner and calling actor |
| Write scope | Exact repository-relative files already known |
| Permitted discovery | A rule deciding whether an additional file may enter scope |
| Scope closure witness | Exact discovery command, authoring baseline, one disposition per discovered path, and an empty undisposed set |
| Documentation edit contract | For an existing Markdown target: `surgical` or explicitly authorized `whole-document`, exact authorized sections/responsibilities, current authority, and required replacement outputs |
| Consumes | Existing or blocker-produced interface with exact identifier/type |
| Produces | Interface or observable contract later tickets consume |
| Verification | Stable behavior seam or existing deterministic check, plus the applicable production producer, legal fixture, reachability, complete oracle, direct observation, and absence detector |
| Constraints | Non-goals, state budget, compatibility, ticket-scoped checks, feature final gates, baseline preflight, and reusable-gate assessment |

Keep direct repository facts, evidence-backed inferences, and unknowns distinct
in the map. For each inference that could change observable behavior, ownership,
an interface, write scope, production state, or verification, name the cheapest
decisive check available within authoring authority. A repository read, existing
command, or bounded prototype may settle the inference, but it never replaces a
ticket-scoped check, feature final gate, or independent review. Stop when a consequential
unknown remains; do not turn it into a `ready-for-agent` assumption.

For a bug or regression, also map the reproducible failure, current causal
model and supporting evidence, the cheapest check that can falsify that model,
and the condition that returns the work to diagnosis. Do not derive a write
scope from an untested cause or ticket a second symptom workaround after the
evidence breaks the causal model.

Exact paths are implementation evidence, not observable requirements. List every
known write path. When a path cannot be known until a scoped search, declare the
search condition and inclusion rule; never use a directory, glob, "as needed",
or "related files" as write scope.

Run every permitted-discovery command against the current authoring baseline.
Classify each repository-relative result exactly once as a declared write path,
an exact read-only input, or a named false positive with a reason. Require the
set of undisposed results to be empty. Also inspect each blocker's exact write
scope and `Produces` contract for a known caller-topology change and place every
such known future caller in this ticket's declared scope before approval. Do
not defer a currently knowable caller to execution merely because the command
will run again after blockers complete.

When a ticket modifies existing Markdown, default its documentation edit mode to
`surgical`. Name the exact headings, fenced-block responsibilities, or facts
that authority permits the executor to delete, rewrite, or move; everything
else is preserve-by-default. An exact write-scope path permits editing bytes but
does not authorize a whole-document rewrite. Use `whole-document` only when a
spec, ADR, or recorded user approval explicitly requires it. If an existing
responsibility still applies, require a positive replacement output and target
location; a stale-token negative scan is not preservation evidence.

Choose a technical detail autonomously only when current code and authoritative
sources establish one valid choice without changing observable behavior. Ask
the user before choosing between multiple plausible owners or interfaces,
changing a public interface, adding mutable state, sharing cleanup ownership,
adding retry/recovery behavior, or introducing a new production seam.

For lifecycle, concurrency, cancellation, retry, cleanup/resource ownership,
routing, or cross-process ordering, apply the bundled ordering-decision
contract. Resolve every actor/thread, state owner, resource owner, linearization
point, competing operation, failure owner, observable result, and deterministic
interleaving before drafting. Use a small runnable `/prototype` or deterministic
latch test when discussion cannot answer one ordering question, then record the
verdict in the spec or a superseding ADR. If the destination or migration states
remain too foggy to bound, return the effort to `/wayfinder`. A ticket must not
become the first authority for either decision.

### 3. Draft tracer-bullet tickets

Apply the product-contract boundary in
`references/ticket-boundaries-and-verification-preflight.md` before splitting:
temporary implementation states do not create independent behavior acceptance.

Create narrow vertical slices:

- Each ticket delivers one complete, observable or deterministically verifiable
  result across every layer it needs.
- Each ticket fits one fresh supervisor context and earns an independent review
  gate.
- Fold required setup, configuration, tests, and documentation into the ticket
  whose result needs them.
- Split tickets only when a reviewer could accept one and reject its neighbor
  without leaving the accepted repository inconsistent.
- Give each ticket only genuine blocking edges. A blocker must produce an
  interface, contract, migration state, or evidence that the dependant consumes.

Apply the bundled independent-rejection test and require each ticket to include
the template's slice-boundary proof. Reject a semantic epic before presenting
the proposal: multiple independently acceptable results, independently
changeable lifecycle/state/cleanup owners, or a combined expand + migrate +
contract effort belong in separate tickets. Layer count, file count, and diff
size never decide the split. Keep one invariant across multiple technical layers
when neither half can remain coherent and green on its own.

Do not create horizontal schema/API/UI/test tickets for one behavior. A
prefactor ticket is allowed only when current structure prevents the behavior
slice from landing independently; name the production reason and keep the
prefactor behavior-preserving.

For a mechanical wide refactor that cannot remain green as one slice, use
expand–migrate–contract: add the new form beside the old, migrate callers in
independently green batches, then delete the old form after every batch
completes. Declare the exact compatibility interface between those tickets.

### 4. Write complete ticket contracts

Read
`<write-implementation-tickets-skill-root>/references/ticket-template.md` in
full and read
`<write-implementation-tickets-skill-root>/references/verification-realizability.md`
in full before drafting acceptance. Instantiate the template once per ticket.
Define behavior once per A-id and command/working-directory once per check or
gate id. Other sections use uniquely resolvable references under the template;
implementation steps do not introduce another behavior oracle. Execution-integrity
evidence may be shared; production mutation experiments are exceptional under
`references/verification-realizability.md`, not a required witness per A-id.
Every published ticket must satisfy the bundled contract, the bundled template,
the verification-realizability contract, and every applicable compatible
repository overlay.

Implementation steps name the responsible actor, exact symbol or file, action,
condition, and expected result. They are not minute-by-minute instructions and
do not include commit steps or a new red → green obligation for each internal
step. An intermediate result is not automatically an acceptance behavior.
Inline code only when a prototype or approved decision-rich state machine,
schema, reducer, or type shape is more precise than prose.

Do not choose the final `direct`, `test-after`, or `tdd` execution mode. The
implementation owner selects it after checking the live production path.
Instead, give that owner the facts needed to route mechanically:

- whether observable behavior or a public contract changes;
- the stable production seam and exact expected result;
- whether the work is a regression, lifecycle, state, concurrency, retry,
  persistence, integrity, or security change;
- the exact acceptance commands or interaction protocols and their expected
  results, separated into ticket-scoped checks and feature final gates.

For browser, desktop UI, device, or other live-app behavior, name the exact
interaction path in the real target runtime before prescribing tool use. The
ticket must name the refresh or reset action and the direct observation that
distinguishes success from a mock, cached result, screenshot-only state, forced
state, or stale renderer. Builds, tests, logs, and screenshots may support that
acceptance item but do not replace the real-runtime observation when the
authoritative requirement demands it. If the runtime is genuinely unavailable,
the ticket names the owner that stops and the evidence it reports; it does not
substitute a weaker check and call the behavior verified. Declare first-failure
captures and bounded diagnosis under `references/verification-realizability.md`.

For every named boundary test, lifecycle/resource proof, negative scan,
generated-consumer check, or other correctness-critical acceptance item,
instantiate the bundled verification witness. A test name or runnable command
does not prove that a legal production fixture reaches the asserted boundary,
that the oracle accepts every legal race or no-op, that the observation measures
the exact property, or that the command fails when required evidence is absent.
Return an unrealizable witness to authoring rather than adding fake-only data or
weakening the expected result.

For every ticket that modifies existing Markdown, include the template's
`## Documentation edit contract`. Split mixed content: stale facts may be
superseded only by current authority, while responsibilities that still exist
must have an explicit replacement acceptance. Do not authorize deleting a
whole section merely because one fact inside it is obsolete.

Assign every command to exactly one verification tier. The current ticket
supervisor owns `## Ticket-scoped checks`; the final-gate supervisor owns
`## Feature final gates` after all implementation tickets are accepted. Declare
each feature final gate exactly once in the graph or execution plan. Do not copy
a whole-repository build into each ticket's scoped checks merely because it is
important at feature closure.

For every feature final gate, attempt to prove a deterministic repository-only
input boundary. When every source, test, build, packaging, lockfile, and consumed
document input is exact and the outcome has no device, network, clock,
credential, mutable cache, ignored/generated-file, or other external
dependency, classify it `reusable` and add the template's
optional `## Reusable gate inputs` section. Reference the feature final gate id
instead of copying its command. If completeness cannot be proved, keep the gate, classify it
`always-run`, and the author records an `always-run` reason; omit only the
reusable-input section.

For authority-permitted historical runtime evidence after repairs, use `ticket-template.md`; freshness requirements still run.

Before candidate publication, perform the bundled baseline verification preflight for
every ticket-scoped check and feature final gate. Account for shared-prerequisite
masking under the bundled preflight contract without claiming masked checks pass.
Run applicable exact `pass` and `intentional-fail` commands; run the declared cheapest non-mutating probe for an
`implementation-dependent` command. Classify an expensive cumulative gate as
`implementation-dependent` when the preflight question is its command syntax,
target existence, retained-interface exclusions, or runtime prerequisites rather
than the not-yet-built feature result. Record the exact preflight command,
expected result, exact observed exit code or interaction result, and bounded
diagnostic signature in the ticket. A malformed regex, stale path, missing
target, wrong red signature, or contradiction with a retained interface returns
the ticket to authoring. Do not pre-run an expensive whole-repository build when
a smaller probe decides the baseline question.

Separately, record the completed scope-closure preflight in each ticket that
declares permitted discovery: the exact discovery command, authoring baseline,
one disposition for every observed path, the blocker caller-topology
assessment, and exact result `0 undisposed paths`. This preflight proves scope
completeness, not behavior verification. A command failure, duplicate
disposition, or any undisposed path returns the ticket to authoring.

Apply `references/verification-realizability.md` to correctness-critical checks.
Reuse execution-integrity evidence, inspect behavioral assertions, and probe only
concrete gaps. A command that cannot prove its claimed property returns to authoring.

Acceptance criteria trace to the spec, ADR, or recorded user decision. A ticket
is invalid if it contains placeholders such as `TBD`, `TODO`, "appropriate",
"as needed", "handle edge cases", "similar to ticket N", unnamed actors, or
undefined identifiers.

### 5. Author self-review before candidate publication

Review the whole graph with fresh eyes:

1. **Spec coverage:** every observable requirement maps to at least one
   acceptance item; no ticket adds unrequested behavior.
2. **Authority and evidence:** every acceptance item and technical constraint
   names its source; superseded inputs cannot decide current behavior; facts,
   inferences, and unknowns are separated; every consequential inference names
   a decisive check, and no consequential unknown remains.
3. **Interface consistency:** each dependant's `Consumes` exactly matches a
   blocker's `Produces`, including identifiers and types.
4. **Graph correctness:** every edge represents a real gate; ticket numbering
   is blockers-first; there are no cycles.
5. **Scope closure:** write path exactness, discovery-rule baseline execution,
   one-of-three disposition, blocker-caller assessment, and undisposed-set
   emptiness per [scope-closure-preflight](references/ticket-boundaries-and-verification-preflight.md#scope-closure-preflight).
6. **Verification:** acceptance seam, command, and expected result
   ([acceptance-and-verification](references/ticket-template.md#acceptance-and-verification));
   bug failure model ([failure-model](references/ticket-template.md#failure-model));
   live-app target-runtime evidence; command assignment
   ([feature-final-gates](references/ticket-template.md#feature-final-gates));
   baseline classification
   ([baseline-verification-preflight](references/ticket-boundaries-and-verification-preflight.md#baseline-verification-preflight));
   gate reuse ([reusable-gate-inputs](references/ticket-template.md#reusable-gate-inputs));
   verification witness
   ([verification-witness](references/verification-realizability.md#verification-witness));
   shared evidence and prerequisite masking per the bundled preflight contract.
7. **Slice and ordering:** every ticket passes the independent-rejection test;
   applicable lifecycle/concurrency work cites a complete ordering decision.
8. **Documentation edits:** surgical edit contract default, whole-document mode
   authority, replacement outputs, and preserve-by-default per
   [documentation-edit-contract](references/ticket-boundaries-and-verification-preflight.md#documentation-edit-contract).
9. **State and architecture:** every mutable field, lock, retry, abstraction,
   cleanup owner, and test seam has a stated production requirement; remove
   unsupported structure.
10. **Cold start:** a fresh executor with only the declared inputs can implement
   and verify the ticket without conversation history.
11. **Placeholder and terminology scan:** no vague instruction, undefined name,
   or invented alias remains.

Fix failures before presenting the breakdown. This check improves the proposal
but does not replace the independent repository-alignment review.

### 6. Publish deterministic candidates or request a material decision

Present a numbered proposal as a progress update. For each ticket show:

- title and `Blocked by`;
- observable result;
- production owner and write scope;
- permitted-discovery scope-closure outcome;
- documentation edit mode, authorized changes, and required replacement outputs when existing Markdown is in scope;
- `Consumes` and `Produces`;
- verification seam, ticket-scoped checks, feature final gates, and baseline
  preflight outcome;
- any decision that still requires user approval.

Across authoring, review, and admission, classify every publication stop into
exactly one of three cases:

- **The ticket contract has no unique answer.** Current authority conflicts or
  leaves multiple reasonable choices for observable behavior, public interface,
  production ownership, or runtime state semantics, including a legal
  production fixture or the semantic ticket boundary. Ask only for that missing
  product or architecture decision.
- **An effective independent admission result is unavailable.** A required
  fresh read-only reviewer cannot be started, or the one review ends in `FAIL`.
  Reviewer unavailability waits for reviewer capability and never falls back to
  author self-review. A terminal `FAIL` requires changed authority followed by
  one fresh review, or explicit user disposition of every unresolved risk.
- **Admission cannot be bound to unique, stable authority inputs.** Reviewed
  authority bytes changed, or the tracker, spec/ticket directories, or another
  required authority input cannot be uniquely identified. Such changes trigger
  review/admission again only inside the current exhaustive epoch: an unchanged
  `authority_sha256` set needs only a fresh `verify`, and a changed one may open
  one delta round while budget remains. Exhausted delta budget or another need
  for exhaustive review ends the current user request; only a later explicit
  user-requested authority change may open a new exhaustive epoch. Ask only when
  an owner must choose the authoritative source or the change introduces a new
  material decision.

Do not ask the user to approve ticket order, granularity, blocking edges, exact
write scope, or verification when the spec, ADRs, current production evidence,
the independent-rejection test, scope closure, and `Consumes` / `Produces`
relationships determine one answer. Treat a uniquely determined correction to
those fields as an **automatic authoring correction**: apply it, rerun the
affected preflight, and continue to the one review without pausing for permission.
When the reviewer has already returned `PASS_WITH_CORRECTIONS`, apply only its
frozen correction set, run deterministic continuity/preflight checks, and stop
reviewing; another model must not polish or re-adjudicate those corrections.
Honor an explicit request to preview without writing, but do not turn the normal
progress update into a confirmation gate.

Omitted files, tests, commands, ticket order, granularity, blocking edges,
production/test-only scope, scope closure, and verification are automatic
authoring corrections whenever existing authority determines one answer; they
are not a fourth stop case. The three-case classification does not enlarge the
workflow's authority: a next action that itself needs new destructive,
irreversible, credential, device, external, or Git-history authority still
requires explicit authorization. Do not publish files while a required material
decision remains open.

When no material decision remains, write one file per ticket under
`<tickets-dir>/<NN>-<slug>.md`, numbered in dependency order. Set
exactly one `**Status:** ready-for-agent` line only after the ticket passes the
self-review. These are the final ticket paths the reviewer reads from disk, but
they are not published or eligible for handoff until an exact admission decision
covers `spec.md` and every ticket. The status line is provisional candidate
content during this gate and does not take effect by itself.
Preserve completed tickets as historical evidence; use a
superseding ticket or revision instead of rewriting them.

### 7. Run the mandatory independent repository-alignment review

After the final candidate tickets are written, read
`<write-implementation-tickets-skill-root>/references/author-review-protocol.md`
and
`<write-implementation-tickets-skill-root>/references/repository-alignment-review.md`
in full. Follow the author protocol to dispatch one exhaustive fresh read-only
reviewer, or one evidence-backed delta reviewer for a later authority version,
preserve exact-input evidence, and route its single result. An all-correction
result closes through deterministic checks and never dispatches another
reviewer. This gate has no same-context fallback and must reach its declared
admission decision point before admission or handoff.

A first candidate opens exhaustive. When a feature with a verified receipt
changes, run `admission_state.py verify` first — a receipt that still verifies
means no authority byte moved and no reviewer is needed. The author protocol owns
the round choice after a real authority change; narrowing the reviewed surface is
always the reviewer's call, never the author's.

### 8. Bind review outcome to an admission decision

After the review protocol reaches its admission decision point and authority
bytes are stable, read
`<write-implementation-tickets-skill-root>/references/admission-and-handoff.md`
in full. It owns the separation between reviewer outcome and execution
admission, author-generated candidate hashes, review- or user-backed receipt
creation, receipt verification, and the final handoff report.

Do not implement the tickets, change ticket status after publication, stage
files, commit, or invoke `execute-tickets` unless the user separately requests
that execution workflow and grants its required staging authorization.
