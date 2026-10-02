# Multiple repositories in one execution run

Read this contract before admission/snapshots when the feature names more than
one Git repository. It changes Git ownership and evidence cardinality only.
The spec and tickets still define behavior, verification commands, working
directories, and acceptance. The orchestrator must not infer a build dependency
graph or invent a joint build/runtime requirement from the repository layout.

## Repository membership and ownership

The orchestrator resolves each ticket-declared repository name to an existing
absolute Git root, confirms staging authorization for every participating root,
and freezes the complete feature repository set at run-start. Repository names
use letters, digits, dots, underscores, or hyphens and start with a letter or
digit. Different names must identify different Git indexes. Resolve each root's
applicable instructions; keep one supervisor for the complete ticket, not one
supervisor per repository. Use the existing worktree in each repository.

The spec, admission receipt, and tickets may remain in one repository. Admission
still runs there; do not copy authority documents or create a receipt per code
repository. A repository being readable does not authorize writes. Every scope
entry names its repository and exact file as `NAME:path`, such as
`QIFramework:app/build.gradle` and `MLLM:src/engine.py`. Do not write
`QIFramework:MLLM/src/engine.py` for a file owned by the registered MLLM root.
An empty scope for a member protects all of its existing content; it does not
authorize arbitrary changes in that repository. Keep all run members registered
even when the current ticket writes only one of them.

Each root owns its HEAD, index, tracked worktree changes, untracked files,
authority hashes, and backups. Registered nested roots own their own contents;
the parent excludes their duplicate worktree view but retains its complete
index and staged patch. For a submodule this preserves the parent's gitlink and
separately freezes the child's HEAD and files. The run neither commits the child
nor updates the gitlink. Pre-existing pointer/checkout differences are captured,
not silently corrected. The tool asks Git for index locations, including a
submodule whose `.git` is a file. Overlapping tracked file ownership is rejected.
Unregistered nested repositories are not silently excluded or adopted.

## Capture and review

All examples use resolved absolute paths for artifacts or the existing ignored
run-artifact tree. The final artifact location must be outside every member or
ignored by every member that contains it. Never put an unignored artifact into
another member. Replace example roots with the user's actual roots.

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --repository QIFramework=/absolute/QIFramework \
  --repository MLLM=/absolute/MLLM \
  --receipt 'QIFramework:<spec-dir>/implementation-ticket-admission.json' \
  --output .execute-tickets/<feature>/run-start

python3 <execute-tickets-skill-root>/scripts/review_state.py assess \
  --repository QIFramework=/absolute/QIFramework \
  --repository MLLM=/absolute/MLLM \
  --scope-path QIFramework:app/build.gradle \
  --scope-path MLLM:src/engine.py

python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --handoff .execute-tickets/<feature>/run-start \
  --scope-path QIFramework:app/build.gradle \
  --scope-path MLLM:src/engine.py \
  --drift-output .execute-tickets/<feature>/<ticket>/handoff-drift \
  --output .execute-tickets/<feature>/<ticket>/pre

python3 <execute-tickets-skill-root>/scripts/review_state.py capture \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --output .execute-tickets/<feature>/<ticket>/review-1
```

Use the prior ticket's `completion/handoff` instead of `run-start` for subsequent
tickets. Baseline/handoff captures inherit the immutable repository membership,
authority, and path ownership. They reject a different declared repository set.
`--scope-path`, `--authority-path`, `--authority-transition-path`, `--receipt`,
and `--allow-path` use `NAME:path` in repository-set review commands. In
particular, do not copy the single-repository unqualified `--receipt` example
into this lane. Derive repository-qualified arguments once from the registered
roots and verified scope; reuse them through assessment and capture. Artifact
paths (`--output`, `--baseline`, `--snapshot`, `--handoff`, resolution/report
paths) are ordinary filesystem paths, not qualified code paths.

The aggregate `snapshot.json` binds each member's Git root, Git directory,
index location, and member snapshot SHA-256. Member snapshots and their existing
artifacts live under `repositories/NAME/`. The orchestrator retains the aggregate
snapshot hash in the run checkpoint and verifies it before trusting its members.

Reviewers receive the aggregate identity plus each member's own
`ticket-tracked.patch`, `ticket-untracked.patch`, new-file hashes, applicable
standards, and qualified scope. The existing Standards and Spec axes cover the
complete ticket; do not multiply review rounds by repository count. Keep
integrity-only artifacts private to the orchestrator, as in the single-repo
protocol. Reports, document-deletion audits, scope/repair metrics, blocker
evidence, and integration-review-index paths must use `NAME:path` to avoid
collisions. Every accepted index reference becomes a map from repository name
to index hash; keep unchanged members in the map. Final review uses the separate
cumulative `repositories/NAME/staged.patch` files, never one parent's gitlink
diff as a substitute for child changes.

`verify --snapshot <aggregate>` checks every member. A member-only PASS is not
an aggregate PASS. Drift in any member invalidates the aggregate review input;
the existing review policy still permits reuse of byte-identical reviewed paths.

## Protected drift

Use the existing `drift`, `reconcile`, and `--drift-resolution` commands against
the aggregate baseline. Reports contain one `repositories` entry per member and
an overall `clean`, `confirmation_required`, or `restart_required` status.
User decisions use qualified keys, for example
`{"decisions": {"MLLM:local-notes.txt": "preserve"}}`. The orchestrator classifies
every reported path before reconciliation. Strong drift in any member cannot
be preserved. Pass the aggregate `resolution.json` to later captures; it binds
the per-member resolutions and keeps preserved changes outside every index.

## Staging and interrupted staging

```bash
python3 <execute-tickets-skill-root>/scripts/review_state.py verify \
  --snapshot .execute-tickets/<feature>/<ticket>/review-N

python3 <execute-tickets-skill-root>/scripts/review_state.py stage \
  --baseline .execute-tickets/<feature>/<ticket>/pre \
  --snapshot .execute-tickets/<feature>/<ticket>/review-N \
  --output .execute-tickets/<feature>/<ticket>/staging
```

The orchestrator stages only after the ticket's required assurance and declared
checks pass. The tool validates all members and prepares their temporary indexes
before replacing any live index. It retains `staging.json` and the expected
post-stage `accepted/` aggregate before the first replacement. Each replacement
uses that repository's existing index lock and rechecks its reviewed state.
Unchanged members retain their index. The command reports success only after
every live member matches the accepted aggregate.

Git provides no atomic replacement across independent indexes. If a later
replacement fails, preserve the actual indexes, evidence, and uncompleted
ticket; never reset the earlier member or unlock dependants. Rerun the exact
same stage command with the same output directory only after the cause is
resolved. The tool accepts each member only in its frozen reviewed state or
its frozen accepted state, skips completed replacements, and rejects any other
drift before continuing. Actual state comparison is the proof of a replacement;
the tool does not keep a second mutable progress flag.
Missing/corrupt staging evidence stops automatic continuation; report the
per-repository state and ask the user rather than adopting it as a new baseline.

## Completion and handoff

The orchestrator records every member's accepted index hash in the existing
completion record, using this multi-repository form for that field:

```markdown
- Accepted implementation:
  - QIFramework: `<index hash>`
  - MLLM: `<index hash>`
```

Keep the existing verification and review fields. The orchestrator checks the
record against the stage result and uses the existing completion command from
the repository containing the ticket, adding:

```bash
--snapshot .execute-tickets/<feature>/<ticket>/staging/accepted
```

`ticket_state.py` ticket/receipt paths remain relative to that command's
repository; they are not `NAME:path`. The tool checks every frozen accepted
member before changing the ticket, proves that only the ticket changed, records
all member HEAD/index identities in `completion.json`, and retains an aggregate
`completion/handoff` from its post-transition collection. Only the orchestrator
may then append the integration-review-index row and unlock dependants. Never
omit `--snapshot` for multi-repository completion. A validation-only ticket
passes its unchanged, empty-scope aggregate pre snapshot instead; it does not
stage an empty implementation. The skill runs only spec/ticket-declared checks
and does not define additional joint acceptance.

Resume validates the same aggregate repository membership, hashes, completion
evidence, and integration-review-index map. A legacy single-repository
checkpoint cannot prove another repository's history and is rejected as a
multi-repository baseline. Keep that checkpoint and all user changes; ask for
explicit re-baselining/admission of uncovered work. Never rewrite old completed
tickets or pretend previously unreviewed content was accepted.

Single-repository invocations and snapshots remain supported. The gate input
cache remains a single-repository facility: when an existing authoritative gate
has a complete eligible input set in one member, run its helper from that root
using `run-start/repositories/NAME`. A manifest that cannot cover its declared
inputs still follows the existing rerun rule. Repository membership alone never
authorizes reusing a result or changes the gate's requirements.
