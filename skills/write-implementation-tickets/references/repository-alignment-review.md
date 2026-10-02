# Repository-alignment authoring review contract

This review is the final admission gate for implementation tickets. A first
candidate begins with one independent exhaustive review of the final ticket files
against the authoritative repository sources and live working tree. A later
authority change to an already-passing feature may instead open one bounded delta
round. One stable authority version gets at most one reviewer. When that reviewer
finds only corrections whose exact answer is already fixed by authority, the
author applies them once and deterministic continuity checks replace another
model review. Author self-review cannot replace the opening reviewer, and no
round may be narrowed on the author's authority.

## Roles and isolation

- The author owns ticket drafting, automatic authoring corrections, routing of
  material user decisions, finding classification, deterministic manifest
  checks, and handoff.
- The one review uses a fresh read-only reviewer without inherited
  conversation history, for example with `fork_turns: "none"`.
- The exhaustive reviewer receives no prior report. A delta reviewer receives
  only its base report and deterministic changed-input evidence.
- No reviewer receives the authoring conversation, proposal summary, private
  implementation map, or an author-written claim that a finding is resolved.
- A reviewer must not edit, stage, delete, rename, or create repository files.
  The reviewer writes its report and initial manifest. All review artifacts remain under
  `/tmp/write-implementation-tickets/<feature>/review-<N>/`.

If a required fresh reviewer cannot be started, stop before publication. The
author does not fall back to a same-context or author self-review.

## Author-owned dispatch evidence

Immediately after starting each reviewer, the author writes
`/tmp/write-implementation-tickets/<feature>/review-<N>/dispatch.json`. The
reviewer must not create or edit it. Record at least:

```json
{
  "schema_version": 1,
  "review": 1,
  "review_type": "exhaustive",
  "reviewer": "<platform-returned reviewer identifier>",
  "context": {"fork_turns": "none"},
  "ticket_paths": ["<tickets-dir>/<ticket>.md"],
  "base_review": null
}
```

For a delta round, set `review_type` to `delta`
and `base_review` to the base exhaustive report path and SHA-256, and record the
`delta.json` path. Every round must record a different
platform-returned reviewer identifier. Missing, late, reviewer-authored, or
duplicate-identifier dispatch evidence rejects that round.

## Review types and inputs

### Exhaustive Review 1

Give the initial reviewer only paths to:

1. The absolute repository root.
2. Applicable governing instructions and standards.
3. The feature spec and relevant ADR/domain documents.
4. Every final ticket under `<tickets-dir>/`, plus the resolved spec and ticket
   directories and `docs/agents/issue-tracker.md` when present. The reviewer
   independently checks both directories against that document; only its
   absence permits the `.spec/<feature>` and `.spec/<feature>/issues` defaults.
5. Exact completed-blocker evidence consumed by those tickets.
6. This review contract and the bundled authoring contract.

The reviewer reads the final ticket files and repository evidence from disk,
discovers the exact relevant declarations, immediate callers, shared utilities,
tests, public documentation, and build files, and freezes one complete finding
set. A `FAIL` is valid only after every required exhaustive check ran.

### Delta round

A delta round replaces a full exhaustive re-review when a previously passing or
admitted chain is followed by an authority byte change. Give a different fresh
reviewer paths and hashes for:

1. The repository, governing instructions, spec, and final tickets.
2. The base exhaustive report and manifest.
3. The current manifest and the author-generated `delta.json`.
4. The exact diff of every changed input path.
5. This review contract and the bundled authoring contract.

Do not give it the authoring conversation, the private implementation map, or any
author claim that the change is immaterial. The point of the round is that an
independent reader — not the person who made the edit — decides how far the change
travels.

The delta reviewer determines the **reach** of the changed bytes itself: which
ticket `Authoritative inputs`, acceptance items, scope-closure dispositions,
`Consumes`/`Produces` contracts, ordering contracts, and non-goals depend on the
changed content, directly or through a blocker edge. It then runs the full
exhaustive checks over that reach. Conclusions for authority-identical regions
outside the reach carry over from the base exhaustive report.

The report must contain a `delta_reach` section naming what the reviewer judged
reachable and what it judged unreachable, with the evidence for each exclusion.
Without it, "I only reviewed the affected part" is unfalsifiable and the round is
rejected. When the reach cannot be bounded — the diff touches shared definitions,
terminology used across tickets, or anything that would require reading the whole
graph anyway — return `INVALIDATED` and require exhaustive review rather than
guessing a smaller surface. A change that is itself a `material_change` also
returns `INVALIDATED`.

## Freeze and compare review inputs

The exhaustive reviewer captures the exact tickets and repository files outside
the repository:

```bash
python <write-implementation-tickets-skill-root>/scripts/review_manifest.py capture \
  --repo <repository-root> \
  --output /tmp/write-implementation-tickets/<feature>/review-1/inputs.json \
  --path "<spec-dir>/spec.md" \
  --path "<tickets-dir>/<ticket>.md" \
  --path <each-exact-reviewed-repository-file>
```

After a `PASS_WITH_CORRECTIONS`, the author applies only the reviewer's exact
authority-backed corrections and captures the current manifest over the same
input path list. The author then runs:

```bash
python <write-implementation-tickets-skill-root>/scripts/review_manifest.py closure \
  --tickets-dir "<tickets-dir>" \
  --before /tmp/write-implementation-tickets/<feature>/review-<N-1>/inputs.json \
  --after /tmp/write-implementation-tickets/<feature>/review-<N>/inputs.json \
  --ticket "<tickets-dir>/<changed-ticket>.md"
```

Pass one exact `--ticket` for every corrected ticket. Require exact output
`closure-valid`. This is a deterministic path-and-hash continuity check, not a
review round. It allows unchanged authority bytes and rejects repository change,
input-set change, changed non-ticket authority input or changes outside the
listed tickets. The author still must apply every frozen correction; continuity
alone does not prove its semantic completion. The author then reruns
only the affected ticket preflight/lint and verifies the corrected manifest.
No reviewer inspects the corrected wording again.

A delta round reuses the same `capture` command and the same exact path list as
its base exhaustive manifest, then runs `review_manifest.py delta` instead of
`closure`. That command proves the path set is unchanged and emits the exact
changed set; it does not decide what the changes mean. Only `authority_sha256`
participates in these comparisons, so editing the spec presentation block is not
drift.

If the correction reaches outside the prescribed ticket paths or requires a new
behavior, interface, owner, or runtime-state decision, this route is invalid.
End the current request and report the exact boundary. Only a later explicit
user-requested authority change may open a new exhaustive epoch under
`author-review-protocol.md`; do not recursively review the wording edit.

## Exhaustive required checks

Review the ticket graph as one unit:

1. **Authority and coverage:** every behavior, acceptance item, constraint, and
   non-goal traces to the spec, ADR, completed blocker, or recorded approved
   source; every observable spec requirement is covered. No ticket treats the
   spec presentation block's `display_title` as an authoritative source — every
   observable requirement must come from the authority body.
2. **Repository alignment:** every claim about an existing path, symbol,
   signature, type, owner, caller, utility, test seam, document, or build target
   matches the live working tree.
3. **Scope closure:** every known write path is exact and every permitted-
   discovery rule is bounded. Rerun every exact discovery command against the
   live working tree, normalize its repository-relative result set, and compare
   it with the ticket's exclusive declared-write, read-only, and named-false-
   positive dispositions. Verify the blocker caller-topology assessment against
   each blocker's write scope and `Produces`. Any command failure, duplicate
   disposition, missing reason, or undisposed path is a ticket defect. Merely
   confirming that the command exists or the declared scope looks plausible is
   not exhaustive review evidence.
4. **Documentation edit contract:** every ticket that modifies existing
   Markdown defaults to `surgical`, names the exact authorized sections or
   responsibilities, and preserves everything else by default. `whole-document`
   has explicit spec/ADR/user authority rather than path-scope inference. Every
   still-current responsibility has a positive replacement output and
   acceptance; mixed stale/current units are split rather than broadly marked
   superseded. Negative scans and write permission are not preservation proof.
5. **Slice boundary:** each ticket has one acceptance unit, names every changed
   lifecycle/state/cleanup owner, passes the independent-rejection test, and
   fits one fresh supervisor context. Reject a semantic epic; do not split one
   invariant merely because it crosses technical layers.
   First apply the product-contract boundary: reject temporary-state acceptance
   and per-step red → green obligations without a distinct stable behavior.
6. **Interfaces and graph:** every `Consumes` entry matches its `Produces`
   contract; every blocking edge is real; numbering is blockers-first and the
   graph is acyclic.
7. **Ordering and ownership:** every applicable lifecycle/concurrency contract
   cites durable authority and resolves actor/thread, state and resource owners,
   linearization point, competing operations, failure owner, observable result,
   and deterministic interleaving evidence, including cross-facade and wire
   boundaries.
   Compare proposed waits, cleanup guards and retries with the lower owner's
   existing guarantee and the enclosing caller's budget. Require an independent
   business obligation for duplicate protection; do not strengthen a redundant
   guarantee merely by requesting more tests. Preserve explicit business cleanup
   contracts and surface authority conflicts through the existing finding rules.
8. **Verification:** every acceptance item has a stable seam or deterministic
   check, exact command, and expected result, directly or through a unique
   declared-input reference. Reject conflicting duplicate definitions or unresolved
   references; do not demand inline copies of an already defined contract. Every command is assigned to the
   ticket-scoped or feature-final tier; each feature final gate has one owner,
   one reuse assessment, and no duplicate execution hidden in ticket checks.
   Check that later verification has a named ticket/final-gate owner, distinct
   layer checks do not duplicate end-to-end scenarios, and explicit prerequisite
   evidence or safety gates are not deferred as unfinished-product work.
   Every baseline preflight classification and observed result, including a
   proven shared-prerequisite failure and resumption condition, matches the live
   authoring baseline; a malformed scan, stale target, or wrong red signature is
   a ticket defect. For every applicable correctness-critical item, verify the
   production producer, legal fixture, reachability, complete legal oracle,
   direct observation, and observed or validly reused absence evidence under
   `verification-realizability.md`; do not require a mutation per item. Do not infer these
   from a test name or a green command, and do not sample only part of the
   witness set. For migrations, confirm that existing generated/published
   consumers and their positive/negative oracles have an exact migration owner.
   Expensive checks name the required target, result writer and parser under the
   verification-realizability contract; do not add a separate review stage. Judge each
   blocking item and gate environment prerequisite by that contract's requirement-source
   and environment-capability rule, and route a finding that asserts an unsupported
   requirement as `review_drift` under the existing disposition below: do not edit, keep
   the terminal `FAIL` for user disposition, and never recast the finding as another gate.
9. **Architecture and state budget:** proposed state, locks, retries, cleanup,
   abstractions, public seams, and test seams have an explicit requirement and
   owner.
10. **Cold start:** a fresh executor can implement each ticket using only its
   declared inputs and completed blockers.

Do not report a sourced future `Produces` symbol merely because it does not yet
exist. Do reject an invented future interface without authoritative support.

## Finding classification and disposition

The reviewer classifies every finding before returning. The decisive question
is whether the correction merely writes down the one answer already fixed by
authority, or creates a new answer:

| Classification | Meaning and disposition |
| --- | --- |
| `author_correction` | A current ticket claim contradicts exact authority or repository evidence, and that evidence fixes one correction without changing accepted observable behavior, public interface, production ownership, or runtime-state semantics. The reviewer names the exact ticket, source, and smallest correction. This includes precise wording, paths, symbols, order, blocking edges, exact scope, or verification text when none requires a new decision. Return `PASS_WITH_CORRECTIONS`; the author applies the frozen set once and does not request another review. |
| `review_drift` | The finding requests an actor, behavior, owner, or constraint absent from current authority or ticket scope. Do not edit. Keep it unresolved in a terminal `FAIL` for user disposition rather than asking another reviewer to improve the same bytes. |
| `authority_blocked` | The required observable result or owner is undefined, or authoritative sources disagree. Stop and surface the missing or conflicting sources for a user decision before editing; do not average them. |
| `material_change` | Closing the finding would change observable behavior, a public interface, production ownership, or runtime state semantics such as lifecycle, concurrency, retry/recovery, cleanup/resource ownership, routing, or externally visible ordering. Return to user approval and then start one exhaustive review for the updated authority version. A graph or scope correction is not material by itself when exact authority already determines it. |

`PASS_WITH_CORRECTIONS` is allowed only when every finding is an
`author_correction`. If any finding belongs to another class, return `FAIL` and
freeze the complete unresolved set. The author may reject a purported
`author_correction` when applying it exposes ambiguity or wider reach, but may
not promote a `FAIL` to a passing result.

## Result contract

The reviewer writes `report.md` beside `inputs.json` and returns:

```yaml
status: PASS | PASS_WITH_CORRECTIONS | FAIL | INVALIDATED
review: <positive integer>
review_type: exhaustive | delta
base_review: <null, or prior report path and SHA-256>
report: <absolute path and SHA-256>
manifest: <absolute path and SHA-256>
reviewed_tickets:
  - path: <repository-relative final ticket path>
    sha256: <reviewed content SHA-256>
delta_reach:
  - changed_input: <repository-relative changed path>
    reachable: [<ticket path and section this change can affect>]
    unreachable: [<ticket path and section, plus the evidence that excludes it>]
scope_closure:
  - ticket: <repository-relative ticket path with permitted discovery>
    discovered: <nonnegative integer>
    declared_write: <nonnegative integer>
    read_only: <nonnegative integer>
    false_positive: <nonnegative integer>
    undisposed: [<repository-relative paths, empty for PASS>]
resolved_findings: [<finding IDs closed or withdrawn in this round>]
unresolved_findings: [<finding IDs still open, including repair regressions>]
author_corrections: [<finding IDs the author must apply without another review>]
findings:
  - id: <stable finding id>
    ticket: <repository-relative path and section>
    claim: <exact ticket claim>
    authority: <spec, ADR, blocker, or contract evidence>
    repository_evidence: <exact path, symbol, caller, test, or command evidence>
    required_action: <smallest correction or required user decision>
```

- `PASS` requires `unresolved_findings` and every scope-closure `undisposed`
  list to be empty, and requires one scope summary for every ticket with
  permitted discovery.
- `PASS_WITH_CORRECTIONS` requires a nonempty `author_corrections` list, no
  unresolved finding, and every finding classified as `author_correction` with
  an exact authority source and smallest prescribed ticket change.
- `FAIL` freezes the complete unresolved finding set.
- A `delta` round omits `delta_reach` only when it returns `INVALIDATED`. Any
  `delta` `PASS` or `FAIL` without one entry per changed input is rejected, and
  its scope summaries cover every ticket inside the reach.
- `INVALIDATED` means a required input changed, disappeared, could not be
  proved identical before acceptance, or — for a delta round — that the reach
  could not be bounded.

Before accepting any round, the author runs `review_manifest.py verify` on its
current manifest and requires exact output `valid`.

## Convergence and admission

One stable authority version allows one opening round: exhaustive or delta.
There are no model closure rounds. `PASS_WITH_CORRECTIONS` closes only through
the deterministic manifest-continuity and affected-preflight checks described
above. A `FAIL` is terminal for those exact bytes and requires user disposition
or a changed authority version; it is not an invitation to ask another reviewer
for a more agreeable answer.

Consecutive delta chains are bounded separately: one base exhaustive passing review
supports at most two delta admissions, after which the next authority change
ends the current user request. Only an explicit later user-requested authority
change may open a new exhaustive epoch. Each delta round only sees its own diff's reach, so
without that bound a long series of small edits would never re-examine what those
edits add up to.

A changed manifest input set, changed non-ticket authority input, or wider
boundary invalidates the author-correction route and ends the current request.
A later explicit user-requested authority change may open the next exhaustive
epoch under `author-review-protocol.md`. Any repository edit by a reviewer rejects its result.

Review-backed admission requires one of: an exhaustive `PASS`; a delta `PASS`
with `delta_reach`, `delta-valid` continuity against its base exhaustive report,
and remaining delta budget; or an exhaustive/delta
`PASS_WITH_CORRECTIONS` followed by `closure-valid` deterministic continuity,
successful affected preflights, a current manifest that verifies as `valid`,
and final ticket bytes matching that corrected manifest. A corrected delta also
requires the same `delta_reach`, continuity, and budget as a plain delta `PASS`.
The correction path records every `author_correction` finding ID in the receipt
and starts no additional reviewer.

A later user admission does not alter this result contract. The report remains
`FAIL`; the authoring flow separately binds the user's explicit dispositions to
one exact candidate manifest. Reviewers do not create, edit, or describe that
receipt as reviewer approval.
