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
protect statistical data only. Existing v2 logs remain readable without rewriting.

## Event contract

Write one JSON object in the ignored run-artifact tree, then append it with:

```bash
python3 <execute-tickets-skill-root>/scripts/metrics_state.py record \
  --output .execute-tickets/<feature>/run-metrics.jsonl \
  --event-file .execute-tickets/<feature>/metrics-event.json
```

`metrics_state.py validate` checks statistical data format only. It is optional
and must never be used before dispatch as a permission check. Duplicate or
out-of-order observations do not authorize, reject, or consume review rounds.
Record the observed result and duration only after execution evidence is verified.

Every event has exactly these fields (schema v2 is retained;
`final_repair_review` and `run_phase` add kinds, not new required fields):

```json
{
  "kind": "review_round",
  "ticket": "03",
  "phase": "discovery",
  "reason": "initial_ticket_review",
  "result": "pass",
  "scope_paths": [],
  "state_owners": ["RemoteQiLlmService"],
  "duration_ms": 1250
}
```

- `ticket` is the stable ticket number, or `null` for a feature-level gate or
  result.
- `scope_paths` contains sorted, unique, repository-relative paths actually
  owned by the event. Do not put inferred dependencies here.
- `state_owners` contains sorted, unique project identifiers from the ticket's
  ordering/ownership contract. Use `[]` when the ticket changes no state owner;
  do not invent an umbrella owner name merely to populate metrics.
- `duration_ms` is the orchestrator-observed elapsed wall time for the bounded
  action, calculated from machine-clock readings at its boundaries. When both
  boundaries are observable to the orchestrator, take the readings and record a
  measured duration; `null` is reserved for boundaries that were genuinely not
  observable or a lost segment, never an estimate from file modification times,
  and every such gap must surface in the closeout `phase_timings`
  `unmeasured_count` instead of passing silently.
  Use `0` only for an instantaneous result transition or reuse decision.

Record only core phase costs; do not introduce timers per read, command, worker
or review axis. Existing ticket-check diagnostics may remain. Before an explicit
pause/user wait, save elapsed time in the existing provisional event; after
resume, add only the resumed work before recording the single result event.
Capacity-driven scheduling waits (for example reviewer dispatch serialized by a
thread or agent limit) belong in the dispatch schedule evidence and stay out of
the event's execution `duration_ms`; when wait and execution cannot be
separated, the event records the combined span as measured and says so, instead
of presenting queued time as work.
Do not emit a partial review result or duplicate its observation. A lost segment
makes that event's duration null; elapsed idle time is not reconstructed.

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
- `review_round`: review snapshot preparation through verified dual-axis
  reports;
- `final_repair_review`: targeted two-axis dispatch through verified reports;
  this is separate from repair work and cumulative final review;
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
- non-overlapping workflow wall time from ticket scope, implementation, review,
  repair, acceptance, core run phases, and unenclosed feature-final spans;
- `phase_timings`: measured duration, event count and `unmeasured_count` grouped
  by ticket, kind and phase for those core spans, excluding nested ticket checks;
- `unmeasured_event_count` and `unmeasured_workflow_event_count`: explicit nulls
  and historical non-instantaneous zeros. The helper preserves the old log and
  flags these gaps instead of interpreting them as free work. Existing duration
  totals are measured subtotals when gaps exist, not complete run elapsed time.

Missing timing does not invalidate valid review results or reset their budget.
Zero instantaneous ticket results and verified reuse decisions remain valid.

If metrics became incomplete, do not emit a partial summary as though it were
complete; report the first metrics failure and available diagnostic artifact.
The summary deliberately contains `quality_proxy: false` and no quality score.
The final user-facing result leads with staged/verified outcome and acceptance
evidence; metrics appear only as workflow-cost diagnostics.
