# Reusing final-gate evidence

This protocol covers deterministic result reuse and authority-permitted retention
of historical runtime evidence after repairs within one `execute-tickets` run.
Neither substitutes for the assurance lane selected by review policy.

Classify each gate's deterministic reuse assessment from its declaration:

- `always-run`: external/uncertain inputs, or no complete deterministic manifest;
- `reusable`: one complete repository-only input manifest is declared — exact
  tracked files, or exact module directories plus every consumed root build,
  dependency, lock, packaging, and documentation input.

The first final-gate pass runs every feature final gate. Reuse is considered only
after a repair. Ticket-writing workflows should emit deterministic declarations
for expensive reusable gates by default; omission safely means
`always-run`. Execution never invents a manifest from changed files. Runtime
evidence may instead be retained only under the explicit contract below; do not
label external state `None` or pass it through `gate_state.py`.

## Historical runtime evidence after repairs

The owning gate declaration may explicitly permit retaining an earlier actual
runtime result after later repairs. The author names the acceptance claim,
evidence and relevant production/test/build/deployment/model inputs, invalidating
changes, and whether current deployment or fresh interaction must be proved.
Keep this condition in the existing gate declaration, not a new status schema.
Without that condition, an `always-run` runtime gate runs normally. A current-state
or fresh-interaction requirement always runs; silence is not permission to retain.

Before retaining evidence, the final-gate supervisor verifies all of these:

- The result is an actual PASS from this run with complete raw evidence and
  matching hashes, build/model/runtime identity and acceptance criteria.
- The authoritative boundary still covers the claim: production, caller,
  assertions, build, packaging, deployment and model/backend/configuration inputs
  consumed by that gate remain applicable. Inspect shared inputs as well as the
  changed paths; a `G4-only` label or an unchanged summary is not proof.
- No later unexplained failure of the same gate exists, and no required fresh
  runtime observation is being replaced. A relevant input change or an unknown
  identity/boundary requires normal execution.

Record the authority, prior result/raw hashes, applicable input comparison and
reason in the existing final-gate result and integration index. Emit the existing
`gate/reused` event. Describe the original conditions and time; do not fabricate
fresh `runtime_observations` or claim the current device is unchanged. Retention
proves what the original execution demonstrated, not a fresh environment state.
Do not add a device fingerprint service, inferred dependency cache or new ledger.

If later authority explicitly permits reevaluating retained raw evidence under
a changed oracle, the verification owner runs the changed validator and writes a
separate result binding the new authority, validator and original raw hashes.
Preserve the original exit code and failure. Missing newly required evidence
remains unproved; changing an oracle does not authorize suppressing a real
failure. Record reevaluation as an executed gate, not reuse of an original FAIL.

## Deterministic eligibility

A gate is reusable only when an authoritative ticket or execution plan contains
one explicit declaration in this shape:

```markdown
## Reusable gate inputs

### `<stable-gate-id>`

- Gate: `<stable-gate-id; resolves the Feature final gates command>`
- Inputs:
  - `<exact tracked repository-relative file or directory>`
- External state: `None — reusable within the same execute-tickets run.`
```

Treat the declaration as optional optimization metadata, not as permission to
weaken a feature final gate. Resolve the exact command and working directory
from `## Feature final gates` using the same stable gate id, owner and reuse
assessment. Existing declarations with a repeated `Command` remain supported
only when it equals that authoritative command. Write the resolved exact command
to the existing command artifact for `gate_state.py`; do not pass an id as shell text.
`always-run` gates do not declare reusable inputs. Whether the declared inputs
are exact files or complete module directories, the safety decision is always
made from the same exact manifest; it never infers transitive inputs.
Each input path must cover every repository file that can affect the command,
including production source, tests, build logic, packaging metadata, lockfiles,
and public documentation when the command consumes it.

The gate is not reusable when any of these is true:

- the declaration is absent, incomplete, ambiguous, or disagrees with the
  feature final gate command;
- an input would need a glob, inferred dependency, generated or ignored file,
  environment value not fixed by the command, or repository-external path;
- the outcome depends on a device, network service, clock, mutable cache,
  credential, user session, or other external state;
- the command is executed from somewhere other than the repository root, or a
  material environment assignment is not part of the recorded command text.

In every ineligible or uncertain case, run the feature final gate normally. Do not
ask an agent to infer a safer input set from the changed files.

## Evidence boundary

Keep all reuse evidence in the ignored run-artifact tree, for example:

```text
.execute-tickets/<feature>/final-gates/<gate-id>/attempt-N/
├── command.txt
├── inputs.json
├── gate.log
└── pass.json
```

`pass.json` is bounded orchestration evidence. It records the gate id, exact
command, exit code `0`, log path and raw SHA-256, input-manifest path and raw
SHA-256, and the final review snapshot identity current when the command passed.
It is not a repository deliverable and does not replace the inline ticket
completion record.

## First successful execution

1. Create a new attempt directory and write the exact command to `command.txt`.
2. Capture the declared repository inputs before running the command:

   ```bash
python3 <execute-tickets-skill-root>/scripts/gate_state.py capture \
     --output .execute-tickets/<feature>/final-gates/<gate-id>/attempt-N/inputs.json \
     --gate-id <gate-id> \
     --run-start .execute-tickets/<feature>/run-start \
     --command-file .execute-tickets/<feature>/final-gates/<gate-id>/attempt-N/command.txt \
     --input-path <tracked-file-or-directory>
   ```

   Repeat `--input-path` for every declared path. The helper expands directories
   from the stage-0 Git index and rejects missing, empty, overlapping, globbed,
   unmerged, submodule, unstaged, or non-ignored untracked inputs. It also rejects
   an in-repository output path that Git does not ignore, and refuses to overwrite an existing manifest.
3. If capture fails, the optimization is unavailable. Run the feature final gate,
   but do not create reusable PASS evidence for that execution.
4. Run the exact command from the repository root and retain its complete log.
   Only exit code `0` creates PASS evidence. Record the raw manifest hash printed
   by `capture` and independently compute the raw log hash.

## A later final-gate attempt

Before deciding whether to skip the command:

1. Require one retained PASS from this run. Verify that its recorded exit code is
   `0`, its log and manifest still exist, and both raw hashes still match.
2. Create a new attempt directory, write the currently required exact command,
   and run `capture` again with the current declaration and the same retained
   run-start snapshot.
3. If fresh capture succeeds, compare it to the retained passing manifest:

   ```bash
python3 <execute-tickets-skill-root>/scripts/gate_state.py compare \
     --before .execute-tickets/<feature>/final-gates/<gate-id>/<passing-attempt>/inputs.json \
     --before-sha256 <raw-sha256-recorded-with-the-pass> \
     --after .execute-tickets/<feature>/final-gates/<gate-id>/<current-attempt>/inputs.json
   ```

4. Reuse the prior PASS only when `compare` exits `0` and prints exact output
   `reusable`. Record the prior PASS identity and the fresh manifest identity in
   the current final-gate result. Every other output, nonzero exit, missing file,
   hash mismatch, or helper failure means the command must run.
5. If the feature final gate runs and fails, that failure is current. Never fall
   back to an older PASS. A later retry must start a new attempt and satisfy this
   protocol again.

The helper requires the same repository, HEAD, retained run-start snapshot,
gate id, normalized command, declared paths, and exact indexed Git objects. An
unrelated tracked documentation or completion-record change therefore does not
invalidate a gate whose declaration excludes it; a source, test, build, API,
packaging, or consumed-document change does.

## Assurance remains separate

Gate reuse never waives the selected assurance lane. Micro repairs still require
their immutable acceptance snapshot and orchestrator inspection; standard and
high-risk repairs still require their targeted review rounds. The inline
`## Completion record` is orchestration metadata and is not a gate input unless
the authoritative command actually consumes that ticket file.
