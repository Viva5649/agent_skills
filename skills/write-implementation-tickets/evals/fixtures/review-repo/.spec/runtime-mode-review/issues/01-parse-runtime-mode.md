# 01 — Parse and apply runtime mode

**What to build:** `Settings` parses `runtime_mode` and `Worker` stores the
resolved mode.

**Blocked by:** None

**Status:** ready-for-agent

## Authoritative inputs

- Behavior: `.spec/runtime-mode-review/spec.md#behavior` establishes the
  parsing and worker configuration behavior.
- Architecture: `src/mode.py` establishes `RuntimeMode.parse(str)`.
- Completed blocker: `None — this ticket has no completed blocker input.`
- Superseded inputs: `None — no earlier source is superseded by this ticket.`

## Production owner and scope

- Owner: `Settings.runtime_mode()` and `Worker.configure(Settings)`.
- Read-only repository inputs:
  - `src/mode.py::RuntimeMode.parse(str)`
  - `src/worker.py::Worker.configure(Settings)`
- Declared write scope:
  - Modify: `src/settings.py`
  - Modify: `src/worker.py`
  - Modify: `tests/test_runtime_mode.py`
- Permitted discovery: `None — any additional write path returns the ticket to
  the owning execution flow.`

## Slice boundary

- Acceptance unit: `Settings` resolves one configured runtime mode and
  `Worker.configure(Settings)` stores that resolved value.
- Changed lifecycle/state/cleanup owners: `None — this ticket changes no
  lifecycle, state, or cleanup owner.`
- Independent rejection: parsing without storing does not deliver the spec's
  required configured-worker result, and storing without parsing has no value
  to consume.
- Fresh-context fit: the three declared write paths, one existing parser
  interface, and one focused test command establish the complete change.
- Split trigger: evidence that parsing or worker storage requires a new public
  contract or a different production owner returns this ticket to authoring.

## Interfaces

- Consumes:
  - `src/mode.py` provides `RuntimeMode.parse(str) -> RuntimeMode`.
- Produces:
  - `Settings.runtime_mode() -> RuntimeMode` for `Worker.configure(Settings)`.

## Behavior contract

- `Settings` parses `runtime_mode` when configuration is read, producing the
  selected `RuntimeMode`; `Worker` stores that mode during configuration.
  Source: `.spec/runtime-mode-review/spec.md#behavior`.

## Implementation sequence

1. `Settings` changes `src/settings.py::runtime_mode()` to call
   `RuntimeMode.parse(str)`.
2. `Worker.configure(Settings)` consumes `Settings.runtime_mode()` and stores
   the result.
3. `tests/test_runtime_mode.py` observes valid and invalid configuration.

## Acceptance and verification

### A1 — Runtime mode is resolved and stored

- Source: `.spec/runtime-mode-review/spec.md#behavior`.
- Seam or direct check: `Worker.configure(Settings)`.
- Command or interaction: `python3 -m unittest tests.test_runtime_mode`.
- Expected: both runtime-mode tests pass.

## Baseline verification preflight

### `runtime-mode-focused`

- Applies to: `ticket-scoped`.
- Command or interaction: `python3 -m unittest tests.test_runtime_mode`.
- Baseline expectation: `intentional-fail`.
- Preflight command or interaction: `python3 -m unittest tests.test_runtime_mode`.
- Expected baseline result: exit code `1` with two behavioral assertion failures:
  `Worker.mode` is the string `gpu` rather than `RuntimeMode.GPU`, and the
  unsupported value `remote` does not raise `ValueError`.
- Observed baseline result: exit code `1`, `Ran 2 tests`, `FAILED (failures=2)`;
  both failures match the expected behavioral gaps, with no import error.

## Ticket-scoped checks

### `runtime-mode-focused`

- Acceptance: `A1`.
- Command or interaction: `python3 -m unittest tests.test_runtime_mode`.
- Expected: exit code `0` with both tests passing.

No external dependency is required.

## Feature final gates

None — this ticket owns no feature final gate.

## Non-goals and state budget

- Unchanged behavior/owners: task execution remains unchanged.
- Forbidden additions: compatibility aliases, retries, caches, new production
  owners, or public interfaces not established by the spec.
- State budget: no new production field beyond `Worker.mode` already present.

## Stop conditions

- If the declared parser interface or owner does not match current code, the
  executor stops before editing and returns the ticket to the authoring flow
  with the conflicting paths and symbols.
