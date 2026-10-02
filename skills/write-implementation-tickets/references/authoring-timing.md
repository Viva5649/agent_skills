# Core authoring timing

Timing is optional diagnostic work. When available, the author measures only
these non-overlapping phases with the machine clock:

| Phase | Start | End |
| --- | --- | --- |
| `authoring` | Before resolving inputs | Reviewer dispatch; includes exploration, graph, drafting and self-review |
| `review` | Reviewer dispatch | Returned report and input-manifest verification finish |
| `handoff` | Review verification finishes | Corrections, admission, handoff checks and final report preparation finish |

When an existing receipt still verifies and no review is needed, switch directly
from `authoring` to `handoff` at that decision. Do not invent a zero-cost review.
If blocked earlier, finish the current phase and report the actual outcome.
Time the whole review round, including ordinary tool/reviewer waits; do not time
individual tickets, commands, self-checks or reviewer substeps.

Once the feature directory name is resolved, keep one JSON array in the existing
`/tmp/write-implementation-tickets/<feature>/timing.json`. Use the authoring
start observed before input resolution. Append an entry when a phase begins:

```json
{"phase":"authoring","started_at_ms":1788652800000,"ended_at_ms":null,"duration_ms":null}
```

The example timestamp is illustrative; read the actual UTC epoch milliseconds
from a clock tool or `python3 -c 'import time; print(time.time_ns() // 1000000)'`.
At the phase boundary, update only that entry with the observed end and use
Python or another deterministic calculator for `ended_at_ms - started_at_ms`.
Keep earlier entries on later invocations. Before an explicit pause/user wait,
finish the active entry; on resume append a new entry for the resumed phase,
including its recovery preparation. Do not charge the paused interval.

If a boundary was lost through interruption or the clock result is unreliable,
leave the unavailable time/duration `null`. Never fill missing time with 0,
file modification times, or a guessed duration. An unfinished entry is a timing
gap, not evidence that the phase finished. This array carries no admission,
review-budget or execution status authority.

During handoff, optionally close the last entry and use Python to group this array by the
three phase names: sum measured `duration_ms`, count entries with null duration,
and report the known durations and gaps with the artifact path. A phase that
never ran is "not run", not a measured zero. No additional review or test is
required for timing. Missing or unreadable timing instructions, unavailable tools,
malformed data, and clock/read/write/summary failures are reported once; stop
optional timing and continue authoring, review, admission, resume, and handoff.
Never gate execution on statistics, delay delivery, retry or repair timing, or
reconstruct missing history.
