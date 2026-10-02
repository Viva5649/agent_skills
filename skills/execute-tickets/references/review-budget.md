# Review budget

The orchestrator enforces `review-policy.md` through `review_budget.py` and the
independent `.execute-tickets/<feature>/review-budget.jsonl`. This ledger contains
execution decisions, never cost measurements. No review-budget command reads or imports metrics.
Read this contract during run initialization/resume and before review dispatch.

## Ownership and recovery

The orchestrator is the sole writer. Use the same ledger across pauses, resumes,
and new run-start snapshots for this feature. Never use `epoch-N`, `chain-N`, an
alternate artifact root, or a copied/empty ledger to renew exhausted rounds.

For a proven new feature, write `[]` to `review-history.json`. For a legacy run
without this ledger, reconstruct the ordered five-field events below from verified
review reports, repair dispositions, and integration-index evidence. Include prior
ticket completion and failed rounds, not just the latest outcomes. Never read,
import, repair, or infer history from `run-metrics.jsonl`. Missing metrics imply
nothing about review use. If retained execution evidence cannot establish history,
block only the dependent reviewer dispatch and report that missing evidence.

Initialize once after the run-start snapshot exists:

```bash
python3 <execute-tickets-skill-root>/scripts/review_budget.py init \
  --output .execute-tickets/<feature>/review-budget.jsonl \
  --feature <feature> \
  --run-start-id <run-start-snapshot-identity> \
  --history-file .execute-tickets/<feature>/review-history.json
```

`init` refuses an existing ledger. On resume retain it and reconcile any verified
result whose append was interrupted before dispatching further review; do not
repeat completed work because an append failed. If the ledger is damaged, preserve
it as evidence and reconstruct the canonical ledger from the same verified reports.
Do not use metrics availability, counts, durations, or exit codes for any decision.

## Event contract

Write an event with exactly these fields:

```json
{"kind":"review_round","ticket":"03","phase":"discovery","reason":"initial_ticket_review","result":"pass"}
```

Before each `review_round`, `final_review`, or `final_repair_review` dispatch:

```bash
python3 <execute-tickets-skill-root>/scripts/review_budget.py validate \
  --output .execute-tickets/<feature>/review-budget.jsonl \
  --event-file .execute-tickets/<feature>/review-event.json
```

Either permitted review result can be provisional; `validate` checks permission
without appending. After verifying the reports, replace it with the actual result
and run the same command with `record` instead of `validate`. Also record verified
`repair` dispositions and `ticket_result` completion outcomes, which subsequent
review eligibility uses. Their phases/reasons/results follow `review-policy.md`:
`repair_micro` or `repair_non_micro`, `review_finding` or `test_failure`, pass/blocked;
`ticket_result` uses `acceptance`, `ticket_completed`, pass/blocked. Only feature
`final_review` uses a null ticket. No duration, scope, or owner-count fields belong
in this ledger. Records are appended after evidence verification, before optional
metrics recording. A budget error requires resolving the execution-history issue
before the dependent reviewer dispatch; it never triggers a statistics repair.

`review_budget.py record` rejects an invalid ticket-review transition. Each
ticket may have at most one `discovery`, one `closure`, and one
`regression_closure`, in that order. Their reasons are respectively
`initial_ticket_review`, `accepted_findings`, and `repair_regression`. After a
`repair_micro` event, another `review_round` for that ticket is invalid; the
repair must finish through orchestrator inspection. If inspection finds a
micro disqualifier, record only the final escalated repair class, not a
premature micro event.

Single-owner targeted closeout under `review-policy.md` records only the review
events that actually ran: retain final FAIL and targeted PASS, with the verified
closeout/dispositions in the existing integration index. Do not append an unused
cumulative PASS, add an event kind/result, or derive feature acceptance from a
metrics summary. Resume uses the index plus its retained evidence. This does
not reset or extend any review budget.

Final review uses the same deterministic three-phase budget. It records exactly
one `integration_risk` discovery, then only after a failing predecessor and a
completed non-micro repair may record one `accepted_findings` closure and one
`repair_regression` closure. Duplicate reasons, out-of-order phases,
`final_closure`, and any fourth final-review event are invalid transitions.

Final targeted repairs use the original completed owner ticket, not a synthetic
repair id and not that ticket's ordinary `review_round` budget. The latest failing
`final_review` plus that owner determines one batch from its frozen report IDs;
keep those IDs and snapshot hashes in the existing repair reports. Merge the
owner's compatible findings before repair. `discovery` with reason `standard`
allows one round; `high_risk` allows one additional `closure` only after a failed
first round and a subsequent completed non-micro repair. Changing lane, paths,
finding grouping or supervisor does not reset the batch. `validate` and `record`
reject uncompleted owner IDs, extra rounds and cumulative final closure with a
failed/unreviewed targeted batch. A later `repair_micro/pass` represents verified
inspection closing that owner’s remaining frozen IDs and permits no extra targeted
review; it does not rewrite its FAIL report. A new non-micro repair invalidates
that owner’s earlier targeted PASS until the required current review succeeds.
For cumulative closure, the completed non-micro repair must occur after its
required failing final review; a later verified micro repair does not erase
that history. Check current targeted assurance separately, so a later unreviewed
non-micro repair still blocks closure. Repairs before that failing review do not
qualify the next round.
All-micro final closure uses inspection plus required gates, with no new
`final_review` event; mixed owners may enter cumulative closure after each batch
is closed. A passing/blocked latest final review, or exhausted third final round,
permits no new targeted batch.
