# Run-cost metrics

The orchestrator records deterministic execution-cost facts for one
`execute-tickets` run. These facts diagnose ticket shape and workflow cost;
statistics never affect execution. They are never a quality score, acceptance
substitute, review permission, or recovery authority.

## Ownership and storage

- The orchestrator owns the metrics log, timestamps each bounded operation, and
  appends events only after validating the corresponding immutable evidence.
- Supervisors and reviewers report outcomes and artifact identities; they do
  not edit the metrics log.
- Store the JSONL log in the ignored run-artifact tree at
  `.execute-tickets/<feature>/run-metrics.jsonl`.
- This log contains optional observations only. Review budgets belong exclusively
  to `references/review-budget.md`, with no dependency on this log.
- Never stage, commit, or use the metrics log as a review input that can satisfy
  a ticket behavior, assurance lane, or feature final gate.
- This reference is optional; if it is missing or unreadable, skip statistics and
  continue execution under the required execution contracts.
- Any metrics failure (missing script/log, malformed data, validation, I/O,
  initialization, recording, or summary failure) is surfaced once with available
  stderr and marks the cost summary incomplete. It does not block implementation,
  review, staging, or ticket completion; it also cannot turn a failed check or
  review into a pass. Continue the acceptance workflow from its already frozen
  evidence, stop appending to the suspect log, and report the metrics gap in the
  final result instead of reconstructing or estimating missing events. Never gate
  execution on a metrics exit code, use a metrics command in an acceptance chain
  (`&&` or unguarded `set -e`), retry statistics before continuing, or wait for a
  statistics repair. This applies to all errors, without a transition exception.

Attempt to initialize the optional log once, after the immutable run-start snapshot exists and
before starting the first ticket supervisor:

```bash
python3 <execute-tickets-skill-root>/scripts/metrics_state.py init \
  --output .execute-tickets/<feature>/run-metrics.jsonl \
  --feature <feature> \
  --run-start-id <run-start-snapshot-identity>
```

The helper accepts only `<artifact-root>/<feature>/run-metrics.jsonl` and refuses
to overwrite a prior log. Resume may continue a valid retained log; if it is absent
or invalid, continue execution with metrics marked incomplete. These storage checks
protect statistical data only. Existing v2 logs remain readable without rewriting;
the first timer command upgrades only their header to v3 and preserves old records.

## Event contract

For an existing command/report with reliable machine-clock boundaries, reuse
those timestamps and write one result event. Do not rerun it for timing. Append with:

```bash
python3 <execute-tickets-skill-root>/scripts/metrics_state.py record \
  --output .execute-tickets/<feature>/run-metrics.jsonl \
  --event-file .execute-tickets/<feature>/metrics-event.json
```

`metrics_state.py validate` checks statistical data format only. It is optional
and must never be used before dispatch as a permission check. Duplicate or
out-of-order observations do not authorize, reject, or consume review rounds.
Record the observed result and duration only after execution evidence is verified.

Result events keep the same eight fields in v2 and v3. Timer boundary records
described below are separate from result events:

```json
{
  "kind": "review_round",
  "ticket": "03",
  "phase": "discovery",
  "reason": "initial_ticket_review",
  "result": "pass",
  "scope_paths": [],
  "state_owners": ["RuntimeController"],
  "duration_ms": 1250
}
```

- `ticket` is the stable ticket number, or `null` for a feature-level gate or
  result.
- `scope_paths` contains unique, repository-relative paths actually
  owned by the event. Do not put inferred dependencies here.
- `state_owners` contains unique project identifiers from the ticket's
  ordering/ownership contract. Use `[]` when the ticket changes no state owner;
  do not invent an umbrella owner name merely to populate metrics.
- The helper sorts both incoming lists before validation and recording; callers
  need not sort them. It leaves the input file unchanged and applies no list
  normalization to retained history. Duplicates, unsafe paths, invalid types and
  corrupt retained logs still fail validation; normalization does not repair
  historical evidence.
- `duration_ms` is the orchestrator-observed elapsed wall time for the bounded
  action, calculated from machine-clock readings at its boundaries. When both
  boundaries are observable to the orchestrator, take the readings and record a
  measured duration; `null` is reserved for boundaries that were genuinely not
  observable or a lost segment, never an estimate from file modification times,
  and every such gap must surface in the closeout `phase_timings`
  `unmeasured_count` instead of passing silently.
  Use `0` only for an instantaneous result transition or reuse decision.

Record only core phase costs; do not introduce timers per read, command, worker
or review axis. Existing ticket-check and CE stage diagnostics may remain; keep
their references rather than counting them again in workflow time.

### Persistent phase timers

When no existing producer measures the whole phase, use `start` immediately
before it and `end` after its evidence is verified. The event file uses the eight
fields above with `duration_ms: null`; `result` is only a schema-valid placeholder
at start and is not recorded as an outcome. Use a unique timer ID per segment:

Timer IDs are case-sensitive and preserve their spelling. Start with an ASCII
letter or digit, then use ASCII letters of either case, digits, underscores or
hyphens (`[A-Za-z0-9][A-Za-z0-9_-]*`). Reuse the exact ID for `end` or `interrupt`.

```bash
python3 <execute-tickets-skill-root>/scripts/metrics_state.py start \
  --output .execute-tickets/<feature>/run-metrics.jsonl \
  --timer-id ticket-03-review-1 \
  --event-file .execute-tickets/<feature>/metrics-event.json
python3 <execute-tickets-skill-root>/scripts/metrics_state.py end \
  --output .execute-tickets/<feature>/run-metrics.jsonl \
  --timer-id ticket-03-review-1 --result pass
```

The helper captures timestamps itself in the same log. A start record contains
`record_type: timer_start`, `timer_id`, `timestamp_ms` and six-field event metadata
(no result or duration). An end record contains `record_type: timer_end`,
`timer_id`, `timestamp_ms`, `result` and `interruption`. Normal ends set
`interruption: null`; interrupted ends set `result: null`. The helper rejects
duplicate IDs/ends, backwards timestamps and overlapping workflow/wait timers;
nested ticket-check timers remain diagnostics. Do not also `record` the same
timed result. No second ledger, daemon or heartbeat is required.

Before a planned user/capacity wait, call `interrupt --output <log> --timer-id
<id> --reason user_wait` (or `capacity_wait`). This preserves measured work up to
the boundary without claiming completion. If useful, start a separate unscoped
`wait/waiting` timer with that reason and end it on return; waits never contribute
to operation or workflow time. Resume preparation is its own span, then start a
new segment of the interrupted phase. End only the segment that actually finishes
with its verified result. Do not replay the phase.

On unexpected interruption, including model-service loss, never end an old open
timer at resume as though the agent worked throughout. Call `interrupt` with
`service_outage` when established, otherwise `unknown`; the entire lost segment
has unknown duration. Preserve it and start resumed work separately. The helper
cannot detect the outage onset; only authoritative host/command/message timing
can establish a separate outage interval, recorded as `wait/waiting/service_outage`.
Do not subtract a guessed outage from wall time. Summary leaves even an unclosed
timer unknown, with no elapsed-time contribution and no fabricated review result.

When queue time cannot be separated from an observed running span, retain the
combined measurement and state that limit. Timing never gates execution; apply
the same fail-open rule to timer errors, surface stderr once and continue.

The orchestrator also records three unenclosed `run_phase` spans with null ticket
and empty scope/state-owner lists:

- `preparation/new_run`: input resolution through run-start/admission preparation,
  ending immediately before the first supervisor dispatch. Capture the start
  clock before input reads; append after the canonical ledger is initialized.
  If blocked before initialization, retain the event in the existing artifact
  tree and report it directly; do not fabricate run-start or a second ledger.
- `resume/resume`: resumed work through checkpoint validation, ending before the
  next supervisor/action dispatch; never include the preceding paused interval.
- `closeout/final_closeout`: final assurance and gates satisfied (or the terminal
  block established) through final evidence/index disposition, handoff checks and
  report preparation. End before metrics summary/report delivery. It includes
  single-owner targeted closeout when used, but excludes preceding repair,
  review, gate and ticket acceptance spans. Do not add it to every ticket stop.

Use these non-overlapping ticket workflow spans so the summary covers the full
wall clock without double-counting nested checks:

- `ticket_scope`: fresh supervisor dispatch through `scope_accepted` or scope
  block, including cold-start reading, assessment, and pre snapshot. End at
  the actual acceptance/block dispatch, not a timestamp taken before report
  formatting. Send acceptance as soon as required checks pass, then record cost;
- `ticket_phase/implementation`: `scope_accepted` through the verified
  implementation snapshot or implementation block, including ticket checks and
  deletion audit;
- `review_round`: the preceding implementation/repair span's end through verified
  dual-axis reports, including snapshot preparation not already counted in that
  preceding span. Never overlap the two timers. For micro assurance, keep snapshot
  inspection in implementation/repair and emit no reviewer event;
- `final_repair_review`: targeted two-axis dispatch through verified reports;
  this is separate from repair work and cumulative final review;
- `final_review` or `final_assurance`: final coverage/review preparation through
  verified reports/coverage and the one available CE review, excluding prerequisite
  gates. Only the chosen route is timed; nested CE timings are not added again;
- `repair`: verified failing review through the next verified repair snapshot
  or block, including classification, editing, checks, and snapshot capture;
- `ticket_phase/acceptance`: accepted assurance evidence through protected
  staging, completion record, integration-index row, and `ticket_result`.

Ticket-check gates remain nested diagnostic timings and are excluded from
workflow wall time. A feature-final gate with no enclosing ticket phase is a
workflow span. Do not substitute only command runtime for an implementation or
repair span. Preparation, resume and final closeout are outside ticket spans and
use the core run-phase events above.
Reuse scope/state-owner values already resolved from frozen inputs when creating
events; do not regenerate path arrays or delay scope acceptance to polish metrics.

The helper owns the allowed `kind`, `phase`, and `result` enums. A `reason` is a
free lowercase token except where a kind pins it (ticket phases, review rounds,
and repairs); the typical values below are conventions, not an enum. Use these
mappings:

| Event | `kind` | `phase` | Typical `reason` | `result` |
| --- | --- | --- | --- | --- |
| New-run preparation | `run_phase` | `preparation` | `new_run` | `pass` or `blocked` |
| Resume preparation | `run_phase` | `resume` | `resume` | `pass` or `blocked` |
| Final run closeout | `run_phase` | `closeout` | `final_closeout` | `pass` or `blocked` |
| Ticket admission accepted | `ticket_scope` | `scope_accepted` | `declared_contract` | `pass` or `blocked` |
| Ticket implementation | `ticket_phase` | `implementation` | `implementation_work` | `pass` or `blocked` |
| Ticket-scoped check | `gate` | `ticket_checks` | `implementation_change` or `test_failure` | `pass` or `fail` |
| Ticket review 1 | `review_round` | `discovery` | `initial_ticket_review` | `pass` or `fail` |
| Ticket closure | `review_round` | `closure` | `accepted_findings` | `pass` or `fail` |
| Optional third review | `review_round` | `regression_closure` | `repair_regression` | `pass` or `fail` |
| Repair | `repair` | `repair_micro` or `repair_non_micro` | `review_finding` or `test_failure` | `pass` or `blocked` |
| Ticket acceptance and closeout | `ticket_phase` | `acceptance` | `protected_staging` | `pass` or `blocked` |
| First feature gate run | `gate` | `feature_final` | `initial_gate_execution`, `always_run`, or `external_state` | `pass` or `fail` |
| Repaired feature gate decision | `gate` | `feature_final` | `invalidated_inputs`, `reusable_inputs_unchanged`, `always_run`, or `external_state` | `pass`, `fail`, or `reused` |
| Ticket closure | `ticket_result` | `acceptance` | `ticket_completed` | `pass` or `blocked` |
| Final targeted repair review | `final_repair_review` | `discovery` or `closure` | `standard` or `high_risk` | `pass` or `fail` |
| Final integration review | `final_review` | `integration_review` | `integration_risk`, `accepted_findings`, or `repair_regression` | `pass`, `fail`, or `blocked` |
| Reused ticket assurance plus CE | `final_assurance` | `integration_review` | `ticket_coverage` | `reused`, `fail`, or `blocked` |
| Known wait | `wait` | `waiting` | `user_wait`, `service_outage`, or `capacity_wait` | `pass` (interval observed, not acceptance) |

While metrics remain available, record an event for every row that occurs. A reused feature gate still gets an
event with `result: reused`; this is what distinguishes avoided work from an
omitted command. Failed or blocked work is recorded on a best-effort basis; recording never delays
the stop report.

## Optional roll-up

At the end of a completed or blocked run, create a deterministic summary when
the log remained valid:

```bash
python3 <execute-tickets-skill-root>/scripts/metrics_state.py summary \
  --input .execute-tickets/<feature>/run-metrics.jsonl
```

Report, without interpreting them as quality:

- ticket scope path count and declared state owners;
- review-round count and duration;
- repair count by repair phase and reason;
- ticket-check and feature-gate executions, reuse, invalidations, and duration;
- all recorded operation duration, including nested diagnostics;
- known wait duration grouped by cause, excluded from operation/workflow totals;
- `open_timer_ids` and `interrupted_spans`, including unknown lost segments;
- non-overlapping workflow wall time from ticket scope, implementation, review,
  repair, acceptance, core run phases, and unenclosed feature-final spans;
- `phase_timings`: measured duration, event count and `unmeasured_count` grouped
  by ticket, kind and phase for those core spans, excluding nested ticket checks;
- `unmeasured_event_count` and `unmeasured_workflow_event_count`: explicit nulls
  and historical non-instantaneous zeros. The helper preserves the old log and
  flags these gaps instead of interpreting them as free work. Existing duration
  totals are measured subtotals when gaps exist, not complete run elapsed time.

Timer fragments contribute measured duration or an explicit gap, never a completed
event/reviewer count. `final_assurance` is coverage reuse, not a reviewer round.
Missing boundaries are valid incomplete observations, not corrupt statistics;
continue measuring later work and label the subtotal incomplete. Do not reconstruct
missing historical phases or claim the subtotal covers uninstrumented work.

Missing timing does not invalidate valid review results or reset their budget.
Zero instantaneous ticket results and verified reuse decisions remain valid.

If metrics became incomplete, do not emit a partial summary as though it were
complete; report the first metrics failure and available diagnostic artifact.
The summary deliberately contains `quality_proxy: false` and no quality score.
The final user-facing result leads with staged/verified outcome and acceptance
evidence; metrics appear only as workflow-cost diagnostics. State the gap plainly,
for example: "Execution timing is incomplete; verified acceptance is unaffected."
Use that last clause only when acceptance has actually passed; otherwise report
the remaining acceptance blocker separately. Do not describe missing timings as
missing test or review evidence.
