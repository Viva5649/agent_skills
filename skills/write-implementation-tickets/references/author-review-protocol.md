# Author review protocol

Read this file in full only after the final candidate ticket files are written.
Also read `references/repository-alignment-review.md` in full before dispatching
a reviewer. This file owns author-side review orchestration; the repository-
alignment contract owns reviewer inputs, required checks, finding classes, and
result shape.

## Choose the opening round

Use at most one independent review for one stable authority version. Choose its
type from evidence about authority bytes, not from how large the edit felt:

1. **No round.** Run
   `admission_state.py verify --repo <root> --receipt <spec-dir>/implementation-ticket-admission.json`
   with the resolved `--spec-dir` and `--tickets-dir`. Exact output
   `admitted-by-review` or `admitted-by-user` proves the existing receipt still
   covers the current bytes. Report that and stop.
2. **One `delta` round.** Use this when a durable base exhaustive `PASS` or
   `PASS_WITH_CORRECTIONS` report and manifest exist, the current path set
   matches that manifest, the receipt lineage has budget, and this command
   returns exact output `delta-valid`:

   ```bash
   python <write-implementation-tickets-skill-root>/scripts/review_manifest.py delta \
     --before /tmp/write-implementation-tickets/<feature>/review-<base>/inputs.json \
     --after /tmp/write-implementation-tickets/<feature>/review-<N>/inputs.json \
     --output /tmp/write-implementation-tickets/<feature>/review-<N>/delta.json
   ```

   An empty changed set belongs to tier 1. The delta reviewer receives the base
   report and manifest, current manifest, `delta.json`, and exact changed-path
   diffs. It decides the reach itself; the author does not pre-narrow the reviewed surface.
3. **One fresh exhaustive round.** Use this for a first candidate. A later
   changed input path set, material authority decision, missing base review, or
   unbounded delta reach may open a new exhaustive epoch only when it comes from
   an explicit later user-requested authority change. Exhausted delta budget is
   terminal for the current user request; it never authorizes the author to
   create `review-N+1`, `epoch-N`, or another chain automatically.

One base exhaustive admission supports at most two consecutive delta admissions.
The receipt records the count and exhaustive epoch. Opening another exhaustive
epoch over an existing receipt requires decision-record reason
`user-authority-change`; `/tmp` evidence never carries or resets this budget.

## Dispatch and evidence

Start the reviewer read-only and without inherited authoring context, for
example with `fork_turns: "none"`. Give it only the absolute repository root
and governing-instruction, bundled-contract, review-contract, spec, ADR/domain,
completed-blocker, and final-ticket paths. It reads the final ticket files and
live working tree itself and must not edit the repository.
The reviewer does not receive the authoring conversation or private map.
It reruns every permitted-discovery command and reports the required scope
counts before returning a passing status.

Immediately after dispatch, record the requested context mode, platform-returned
reviewer identifier, round type, and exact final ticket paths in
`/tmp/write-implementation-tickets/<feature>/review-<N>/dispatch.json`. Reject a
missing, late, reviewer-authored, or reused identifier.

The author waits without editing while review is active. The reviewer writes
`report.md` and the exact-input manifest outside the repository. Before routing
the result, run `review_manifest.py verify` and require exact output `valid`.

## Route the one result

- **`PASS`:** Confirm the reviewed ticket hashes still match, then create the
  admission candidate.
- **`PASS_WITH_CORRECTIONS`:** This status is valid only when every finding is
  an authority-backed author correction: the reviewer names the exact ticket,
  authoritative answer, and smallest correction, and no correction chooses new
  observable behavior, public interface, production owner, or runtime-state
  semantics. Apply exactly those corrections and rerun only their affected
  deterministic preflight or lint checks.

  Capture the current manifest over the original exact input paths and run the
  existing continuity check with every changed ticket:

  ```bash
  python <write-implementation-tickets-skill-root>/scripts/review_manifest.py closure \
    --tickets-dir "<tickets-dir>" \
    --before /tmp/write-implementation-tickets/<feature>/review-<N>/inputs.json \
    --after /tmp/write-implementation-tickets/<feature>/review-<N>/corrected-inputs.json \
    --ticket "<tickets-dir>/<changed-ticket>.md"
  ```

  Require exact output `closure-valid`, then verify the corrected manifest and
  create the admission candidate with every reviewer finding ID recorded as an
  `author_correction`. This is deterministic correction continuity, not another
  review round. **Do not dispatch a closure reviewer or ask another model to
  improve the corrected wording.**

  If correction changes a non-ticket authority input, the input path set, or a
  boundary wider than the reviewer prescribed, stop this route. Obtain the
  missing material decision when needed, then end the current request. A new
  exhaustive epoch requires a later explicit user-requested authority change
  under the opening-round rules; do not recursively review a wording repair.
- **`FAIL`:** Treat this result as terminal for the exact candidate. Do not
  automatically retry, start a closure reviewer, or ask another model to
  adjudicate the same bytes. Route `authority_blocked` or `material_change` to
  its decision owner. A user may explicitly admit the frozen unresolved set;
  otherwise only a later explicit user-requested authority change may open the
  next exhaustive epoch under the opening-round rules.
- **`INVALIDATED`:** Retain the invalidated report and end the current request.
  Do not automatically dispatch a replacement review for unstable inputs or
  unbounded delta reach. A later explicit user-requested authority change follows
  the opening-round rules; invalidation never resets the existing budget.

The chain reaches an admission decision point only with `PASS`, a deterministically
verified `PASS_WITH_CORRECTIONS`, or a terminal `FAIL` whose frozen unresolved
set may be presented for explicit user admission. Reviewer unavailability stops
before handoff; author self-review is not a fallback.
