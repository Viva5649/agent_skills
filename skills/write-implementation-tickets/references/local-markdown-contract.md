# Local Markdown implementation-ticket authoring contract

This bundled contract is the portable authoring boundary for
`write-implementation-tickets`. It is sufficient when a target repository has
no `docs/agents/` directory or issue-tracker document.

## Authority and repository overlays

- Apply every governing target-repository instruction that is present,
  including applicable `AGENTS.md`, coding standards, specifications, ADRs, and
  domain documents.
- Use `docs/agents/issue-tracker.md` as the authority for the placement and
  nesting of the feature's spec and ticket directories. This bundled contract
  owns the feature directory name substituted into the tracker's feature path
  placeholders. Treat the tracker's other rules as optional overlays. They may
  add stricter admission checks, evidence requirements, or stop conditions that
  are compatible with this contract.
- Stop before drafting when an overlay changes the status field,
  lifecycle states, transition owner, blocker meaning, or meaning of `done`
  below. Do not average the contracts or silently select one.
- Do not import unrelated tracker protocols. Triage roles and wayfinding states
  such as `claimed` or `resolved` are outside this contract.

## Spec and ticket directories

Before reading or writing feature files, the author reads the target repository's
`docs/agents/issue-tracker.md` when present and resolves two repository-relative
directories: `<spec-dir>` contains this feature's `spec.md` and
`implementation-ticket-admission.json`; `<tickets-dir>` contains this feature's
implementation tickets. The tracker may place tickets outside the spec directory.
The author stops if the tracker is unreadable, either directory is unspecified
or ambiguous, or a directory resolves outside the repository. The author never
guesses from existing directories or falls back merely because a declared path
is missing. Missing authoritative inputs still block; approved ticket outputs
may be created in the declared ticket directory.

For a new feature directory, the author sets `<feature>` to
`<YYYY-MM-DD>-<feature_name>`. `<YYYY-MM-DD>` is the current local calendar date
when the author first creates the directory; `<feature_name>` is the undated,
lowercase hyphenated feature slug. The author substitutes that same `<feature>`
value for either `<feature>` or `<feature-slug>` in the tracker's implementation-
ticket paths and passes it unchanged to `admission_state.py --feature`. The
tracker owns every surrounding path component and nesting decision. A tracker
path without either placeholder remains an exact repository-owned directory.

On resume, or when the user supplies an existing spec or ticket path, the author
reuses the existing feature directory name and admission value. The author does
not add, refresh, or migrate its date prefix.

Only when the tracker document is absent, the author uses `<spec-dir>` =
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
the feature and ordered blockers-first.

The author passes both resolved directories as `--spec-dir` and `--tickets-dir`
to every `admission_state.py` command, and passes `--tickets-dir` to
`review_manifest.py closure`. These arguments carry the author's reading of the
tracker; scripts validate paths rather than interpret Markdown. Omitting a
directory argument is allowed only without the tracker, using the fallback
above. The reviewer independently checks the resolved directories against the
tracker, and the author includes that document in the review input manifest.
Handoff names both directories and their tracker source (or its absence).

These files are process documents. Downstream execution addresses them by content
hash, so they may be tracked, untracked, or excluded by `.gitignore`; authoring
never requires them to be tracked or staged.

## Spec presentation block and authority bytes

A requirement's human-readable label and its behavior contract are different
things, so they do not share one hash boundary. `<spec-dir>/spec.md` may open
with a **presentation block**:

```markdown
---
display_title: <human-readable requirement label>
---

## 1. Authority and scope
```

- The allowed key set is exactly `display_title`, written as one flat
  `key: value` line.
- **Authority bytes** are everything after the closing `---`. Candidate
  manifests, review manifests, and the admission receipt compare
  `authority_sha256` over those bytes, not the whole file. Editing only
  `display_title` therefore leaves a verified receipt valid and starts no review.
- An unknown key, duplicate key, empty value, indented line, nested structure, or
  unterminated block makes the **whole file** authority again. The degradation
  always adds authority rather than removing it, so a malformed block can only
  cost one extra review, never skip one.
- Implementation tickets carry no presentation block. Every ticket byte is
  authority.

This only saves work when the label lives in one place. A duplicate title heading
inside the body is authority bytes, so renaming that heading still invalidates the
receipt. Keep the label in `display_title` and let the body start at its first
real section.

`display_title` is a label, not a requirement. Every observable behavior belongs
in the authority body, and no ticket cites `display_title` as an authoritative
input. The `<feature>` directory name also does not follow `display_title`: it is
fixed when the directory is first created, because tickets, blocker edges, and
the receipt path all key off it.

## Scheduling metadata

Each ticket contains exactly one status line near the top:

```markdown
**Status:** ready-for-agent
```

The only implementation-ticket states are:

| Status | Meaning |
| --- | --- |
| `ready-for-agent` | The ticket passed author self-review and its exact feature authority is covered by `admitted-by-review` or explicit `admitted-by-user` evidence, and is eligible when all declared blockers are accepted. |
| `done` | The orchestrator accepted and staged the ticket implementation, verification evidence, and one inline completion record in the same ticket. |

During authoring, the final-path candidate contains the required
`ready-for-agent` line so the reviewer can inspect the exact proposed handoff
bytes. That line is provisional and does not take effect until the author
writes and verifies `implementation-ticket-admission.json` over the current
`spec.md` and every ticket. Before that point, the candidate is neither
published nor eligible for execution.

Each ticket also contains exactly one `**Blocked by:**` field. `None` means the
ticket has no blocker. Otherwise the field names every ticket number whose
accepted interface or evidence this ticket consumes.

A blocker is complete only when both of these are true:

1. Its ticket status is `done`.
2. The same ticket file contains exactly one readable `## Completion record`
   identifying the accepted implementation and verification/review outcome.

Authoring records the edge and the exact consumed interface or evidence; it
does not infer completion from a worker finishing code or tests.

## Lifecycle handoff

`write-implementation-tickets` publishes only `ready-for-agent` tickets. It
does not change an implementation ticket to `done`.

The orchestrator is the only actor that changes `ready-for-agent` to `done`, and
only after it accepts and stages the implementation, verification, and required
evidence. This authoring contract defines the handoff semantics but does not
require a particular execution skill to be installed.

`write-implementation-tickets` does not add an empty completion section to a
`ready-for-agent` ticket. The execution owner appends the record during the
completion transition. The record proves acceptance but does not create behavior;
dependants consume the completed ticket's declared `Produces` contract.

## Cold-start admission contract

Before a ticket becomes `ready-for-agent`, a fresh executor must be able to
implement and verify it without conversation history or guessing. Headings may
vary, but the ticket must contain:

- **What to build:** the bounded observable result and owning actor.
- **Authoritative inputs:** the exact spec, ADR, completed-blocker evidence, and
  repository sources that establish the contract, including superseded inputs.
- **Scope:** the production owner and exact files, plus any bounded discovery
  rule that decides whether each additional path may enter scope.
- **Scope closure preflight (when discovery applies):** the exact discovery
  command and authoring baseline, one exclusive disposition for every observed
  repository-relative path as declared-write, read-only, or named false-
  positive, the blocker caller-topology assessment, and exact result
  `0 undisposed paths`. A successful build or verification preflight cannot
  substitute for this scope evidence.
- **Slice boundary:** one acceptance unit, every changed lifecycle/state/cleanup
  owner, the independent-rejection result, fresh-context fit, and the exact
  evidence that returns a semantic epic to authoring for a split. File or layer
  count is not a boundary rule.
- **Interfaces:** the exact current or blocker-produced contract consumed and
  the exact contract or evidence produced for each dependant.
- **Behavior contract:** reference each acceptance A-id defining its actor,
  action, object, condition and observable result. Unique section/check references
  satisfy the fields below when they resolve in declared inputs. Missing, cyclic
  or conflicting references do not. Existing consistent expanded tickets remain valid.
- **Ordering and ownership contract (when applicable):** a cited spec or
  superseding ADR identifies actor/thread, state owner, resource owner,
  linearization point, competing operations and required order, failure owner,
  observable result, and deterministic interleaving evidence for lifecycle,
  concurrency, cancellation, retry/recovery, cleanup, routing, or cross-process
  behavior. An unresolved row prevents `ready-for-agent` publication.
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
  baseline result, and observed result. The preflight runs before candidate
  publication and cannot replace post-implementation verification.
- **Ticket-scoped checks:** focused commands or target-runtime interactions run
  only by the current ticket supervisor before ticket assurance.
- **Feature final gates:** cumulative build, integration, publication, delivery,
  or target-runtime gates declared once by an owning ticket or execution plan
  and run once after all implementation tickets are accepted. Every gate records
  a reuse assessment and an `always-run` reason when no complete deterministic
  boundary exists. A runtime gate may separately declare authority-permitted
  retention of historical evidence after repairs within the same run: name its
  acceptance claim, raw evidence, relevant production/test/build/deployment/model
  inputs, invalidating changes and any current-state/fresh-interaction requirement.
  This never describes external state as `None` or weakens a fresh-runtime gate.
- **Reusable gate inputs (optional):** only for a `reusable` feature final
  gate, its stable id resolving the exact command, every exact tracked file or
  directory that can affect it, and an explicit declaration that no device,
  network, clock, credential, mutable cache, ignored/generated-file, or other
  external state affects the outcome. An `always-run` assessment means the gate
  reruns normally unless its runtime declaration explicitly permits historical
  retention and all those conditions hold. A later unexplained failure cannot
  be replaced by an older PASS; uncertain applicability requires execution.
- **Stop conditions:** ambiguities, ownership conflicts, missing seams, failed
  prerequisites, failed scope discovery, undisposed paths, and out-of-scope
  changes that stop execution.

## Admission decision receipt

Review outcome and execution admission are distinct. Reviewer reports remain
immutable `PASS`, `PASS_WITH_CORRECTIONS`, `FAIL`, or `INVALIDATED` history. The author alone creates the
candidate authority manifest and the fixed
`<spec-dir>/implementation-ticket-admission.json` receipt through the
bundled deterministic script.

- `admitted-by-review` requires `PASS`, or deterministically closed
  `PASS_WITH_CORRECTIONS`, and no unresolved finding.
- `admitted-by-user` requires the user to approve one exact candidate manifest
  and dispose every unresolved finding once as `closed-by-clarification`,
  `rejected-as-review-drift`, or `accepted-risk`, with a reason.

The author writes this decision record outside the repository after the review
or explicit user approval:

```json
{
  "schema_version": 1,
  "candidate_manifest_sha256": "<lowercase SHA-256>",
  "decision": "admitted-by-review | admitted-by-user",
  "review_status": "PASS | PASS_WITH_CORRECTIONS | FAIL",
  "review_opening_type": "exhaustive | delta",
  "base_exhaustive_report_sha256": "<lowercase SHA-256>",
  "review_epoch_reason": "user-authority-change",
  "unresolved_findings": ["<finding id>"],
  "author_corrections": ["<finding id applied by the author>"],
  "user_dispositions": [
    {
      "finding": "<same unresolved finding id>",
      "disposition": "closed-by-clarification | rejected-as-review-drift | accepted-risk",
      "reason": "<non-empty user-approved reason>"
    }
  ]
}
```

`admitted-by-review` uses plain `PASS` with empty finding/correction/disposition
lists, or `PASS_WITH_CORRECTIONS` with a nonempty `author_corrections` list and
empty unresolved/disposition lists. The latter records the frozen correction
set that the author applied after deterministic continuity and affected-preflight
checks; it starts no second reviewer.
`admitted-by-user` uses `FAIL` and exactly one disposition per unresolved
finding, with no author corrections. The author obtains the candidate hash with a deterministic SHA-256
command; the user approves the candidate bytes and dispositions rather than
calculating the hash.

`review_opening_type` names how this chain opened. For `exhaustive`,
`base_exhaustive_report_sha256` is that chain's own exhaustive report hash and the
consecutive-delta count resets. Omit `review_epoch_reason` for the first
exhaustive review and every delta. When a receipt already exists, another
exhaustive review requires exact reason `user-authority-change`, which the author
may record only for an explicit later user-requested authority change. The
receipt increments `exhaustive_epoch`; budget exhaustion or an author-generated
repair never supplies this reason. For `delta`, the base hash is the hash of the base exhaustive
report the round inherited, and it must match the lineage already recorded in the
existing receipt. The author does not supply the count itself: `admit` derives
`delta_generation` from the existing receipt and refuses a third consecutive
delta, so miscounting cannot widen the budget.

The user decides; the user does not calculate hashes. The reviewer does not
create or rewrite admission. A downstream executor verifies the receipt once at
new run-start and must not refresh or replace it during that run. Any spec/ticket addition,
removal, or authority byte change invalidates the receipt and requires a new
author-owned candidate plus review- or user-backed decision. A change that leaves
every `authority_sha256` identical — editing only the spec presentation block —
leaves the receipt valid; re-run `verify` and continue without a new candidate or
review.

Authoring admission also requires an independent repository-alignment review of
the final ticket files. A fresh read-only reviewer with no authoring
conversation first validates the full graph against the authoritative sources
and live working tree. `PASS` admits unchanged ticket bytes.
`PASS_WITH_CORRECTIONS` is allowed only when every finding names one
authority-backed ticket correction and no new behavior, interface, owner, or
runtime-state decision. The author applies that frozen set once, uses exact
prior/current manifests plus affected preflights to prove continuity, and does
not dispatch another reviewer. The corrected manifest and final ticket hashes
must verify before handoff.

When a previously passing or admitted chain is followed by an authority byte
change, a different fresh reviewer may open a **delta** round instead of a full
exhaustive one. That reviewer receives the base exhaustive report and manifest,
the current manifest, and the exact diff of every changed input; it decides for
itself which ticket contracts those bytes can reach, re-runs the exhaustive checks
over that reach, and records the reach in its report. It returns `INVALIDATED` and
demands exhaustive review whenever the reach cannot be bounded. The author never
narrows the reach on the reviewer's behalf, and one base exhaustive passing review may
support at most two consecutive delta admissions. A material correction, changed
input set, exhausted delta budget, or missing base exhaustive passing review
ends the current request unless an explicit later user authority change starts a
new exhaustive epoch. An unresolved `FAIL`, `INVALIDATED`, reviewer repository
edit, or inability to start the required reviewer stops review-backed admission;
author self-review is not a fallback. A `FAIL` is terminal for those exact bytes
and does not start a closure review. After a
real review `FAIL`, the user may instead admit one later exact candidate through
the separate receipt path above. The report remains `FAIL`, and the receipt
records every user disposition rather than calling the review successful.

A clarification may make an existing contract explicit but must not silently
add behavior. When observable behavior changes, update the authoritative spec,
ADR, or recorded user-approved source before aligning the ticket. Preserve
completed tickets as historical evidence; record later contracts separately.
