# Admission and handoff protocol

Read this file in full only after the author review protocol reaches an
admission decision point and the current spec and ticket bytes are stable. This
file owns content-addressed admission and the final authoring report.

Keep reviewer outcome and execution admission separate. A reviewer report stays
`PASS`, `PASS_WITH_CORRECTIONS`, `FAIL`, or `INVALIDATED`; never rewrite a
failed report to represent a later user decision. Admission is exactly one of:

- `admitted-by-review` — the review is `PASS`, or it is
  `PASS_WITH_CORRECTIONS` and the author applied its frozen correction set with
  deterministic continuity and preflight checks; neither path has an unresolved
  finding;
- `admitted-by-user` — the user explicitly approves one candidate manifest and
  disposes every unresolved finding as `closed-by-clarification`,
  `rejected-as-review-drift`, or `accepted-risk`, with a non-empty reason.

After ticket bytes stop changing, the author—not the reviewer, user, or future
executor—uses the bundled deterministic command to hash the current `spec.md`
and every ticket:

```bash
python3 <write-implementation-tickets-skill-root>/scripts/admission_state.py candidate \
  --repo <repository-root> \
  --feature <feature> \
  --spec-dir "<spec-dir>" \
  --tickets-dir "<tickets-dir>" \
  --output /tmp/write-implementation-tickets/<feature>/admission-candidate.json
```

For review admission, the author records `PASS` with no correction IDs, or
`PASS_WITH_CORRECTIONS` with every reviewer finding ID in
`author_corrections`; both use no unresolved findings and bind the final
candidate-manifest SHA-256. For user admission, present the
candidate manifest, exact changed paths and before/after hashes, unresolved
finding IDs, and proposed dispositions. Only an explicit user approval of those
exact bytes authorizes the author to write the decision record. A vague
"continue" or approval followed by any authority edit is not admission.

The decision record uses `review_status: PASS | PASS_WITH_CORRECTIONS | FAIL`
and `author_corrections: []`. `PASS_WITH_CORRECTIONS` requires a nonempty list;
plain `PASS` and user admission require an empty list.

The author then creates the content-addressed receipt at the fixed feature path:

```bash
python3 <write-implementation-tickets-skill-root>/scripts/admission_state.py admit \
  --spec-dir "<spec-dir>" \
  --tickets-dir "<tickets-dir>" \
  --candidate /tmp/write-implementation-tickets/<feature>/admission-candidate.json \
  --decision-record /tmp/write-implementation-tickets/<feature>/admission-decision.json \
  --review-report /tmp/write-implementation-tickets/<feature>/review-<N>/report.md \
  --output "<spec-dir>/implementation-ticket-admission.json"
```

The command revalidates every authority byte before writing. Run its `verify`
subcommand with the same `--spec-dir` and `--tickets-dir` and require exact output
`admitted-by-review` or
`admitted-by-user`. Any later spec/ticket addition, removal, or authority byte
edit invalidates the receipt and requires a new candidate and admission decision.

`verify` is also the cheapest first move after any later edit to a feature file.
It compares `authority_sha256`, so an edit confined to the spec presentation block
leaves a verified receipt intact: report that the receipt still covers the current
bytes and start no review. Only a `verify` failure means authority actually moved.

The decision record and receipt carry the chain's review lineage. `admit`
requires `opening_type` to be `exhaustive` or `delta`; for `delta` it also
requires `base_exhaustive_report_sha256` to match the lineage recorded in the
existing receipt at the same path, and it rejects a `delta_generation` above 2.
The first `exhaustive` opening records epoch 0. Another exhaustive opening over
an existing receipt resets the delta generation only when the decision record
contains `review_epoch_reason: user-authority-change`; it then increments
`exhaustive_epoch`. The author may use that reason only for a later explicit user
authority change, never because review budget ran out or another model suggested
more polish. This is where the budget is enforced, because `/tmp` review evidence
may be cleaned while the receipt persists.

The author does
not stage the receipt. These are process documents: downstream execution
revalidates them by content hash and never requires them to be tracked or staged,
so they may stay untracked or `.gitignore`-excluded.

## Handoff

Optionally summarize measured time under `authoring-timing.md` when available.
Missing instructions, tools, data, or a failed summary never delay handoff;
report the timing gap once alongside the authoring outcome.

Report:

- the resolved spec and ticket directories and their tracker source, or the
  absence of the tracker that selected the `.spec` fallback;
- the created ticket paths;
- the blockers-first frontier;
- which spec sections each ticket covers;
- the verified repository-alignment review chain, its opening round type, each
  reviewer identifier and context mode, `dispatch.json`, report, and manifest
  paths and hashes, `delta.json` and the reviewer's `delta_reach` when a delta
  round was used, remaining consecutive-delta budget, deterministic correction-
  continuity result when used, the recorded `author_corrections`, and final
  corrected-ticket hashes;
- when no round was needed because `verify` still returned a verified receipt,
  state exactly that: the current bytes were already covered and no reviewer ran;
- the admission receipt path and hash, exact decision
  (`admitted-by-review` or `admitted-by-user`), and every user disposition when
  applicable;
- that no unresolved decision remains, or the exact decision that prevented
  publication;
- that implementation and Git state were not changed.

Lead with the authoring outcome, the strongest direct evidence that the current
ticket bytes passed admission, and any material limitation. Do not imply that
the feature itself was implemented, runtime-verified, committed, or deployed,
and do not use ticket, reviewer, command, or file counts as a proxy for quality.

Do not report the tickets as published or `ready-for-agent` unless the current
spec/ticket bytes match a verified admission receipt. For user admission, state
truthfully that the review remained `FAIL` and the user admitted the exact bytes;
do not describe it as a review `PASS`.

When the user wants to execute the complete approved graph and the installed
`execute-tickets` skill is available, recommend it.
