# Verification realizability contract

Read this contract before publishing acceptance tests, scans, or feature gates.
It prevents a command that can run from being mistaken for evidence that can
prove the ticket's claim through legal production behavior.

## Verification witness

The author first applies the product-contract boundary and verification tiers
in `ticket-boundaries-and-verification-preflight.md`. Witness completeness
applies to justified acceptance items, not every temporary state or internal
implementation step. Absence probes establish that checks detect missing
evidence; they do not require a new behavior red → green cycle for each edit.
Separate execution integrity (required tests ran, real inputs were read, failures
propagated) from the product oracle (the assertions prove the required behavior).
Inspect both, but do not equate either with mandatory production mutation tests.

For every named boundary test, lifecycle/resource proof, negative scan,
generated-consumer check, and other correctness-critical acceptance item, record
one verification witness with these fields:

| Field | Required evidence |
| --- | --- |
| Production producer | The exact production encoder, API, runtime operation, generated artifact, or compiled consumer that creates the observed value or state. |
| Legal fixture | Inputs accepted by that production producer. Hand-written wire fields, fake-only failures, forced state, comments, dead text, and test-only padding are not legal fixtures unless authority makes them part of the contract. |
| Reachability | Numeric bounds or a state/interleaving construction proving the legal fixture can reach the asserted boundary. |
| Oracle | Every result the authority permits for that input and interleaving, including legal races and operation-specific success no-ops. |
| Observation | The direct value, identity, count, ordering, generated file, compiled call, or side effect that distinguishes the claim from a weaker proxy. |
| Absence detector | Observed or validly reused evidence that missing required execution/input or a failed assertion cannot report success; cite shared evidence once. |

Routine compilation or formatting checks may state that a production witness is
not applicable, with the direct property the command verifies. They still need
a fail-loud command and expected result.

Do not accept a test name as evidence for these fields. Read the production
producer, its legal input limits, the fixture construction, and the assertion.
When exact bounds are available, calculate them. When ordering decides the
result, use the authoritative deterministic interleaving rather than a timing
assumption.

## Counterfactual preflight

First reuse relevant exact test-result validation, failure-propagation evidence,
or an existing red at the declared seam. Record the evidence and why it still
applies in `## Baseline verification preflight`. If an execution-integrity gap
remains, run the cheapest non-mutating failure probe for that gap and record its
expected and observed result. Do not create a separate probe per acceptance row
when the same runner/input check covers them.

Require a production mutation experiment only when an authoritative requirement
explicitly demands it or a concrete false-green risk cannot be resolved by
inspecting the production seam, fixture, assertions and existing results. Name
that basis, the smallest isolated experiment, and which changes invalidate it.
Do not mutate production merely to populate witness fields. Existing explicit
probe contracts remain binding until corrected through the owning authority
process; execution must not silently drop them.

Apply these rules where relevant:

- Run each named critical test through an absence-detecting invocation. For
  Gradle, use one exact `--tests class.method` selector per required method, or
  validate the produced JUnit XML against the exact required method set. Several
  selectors in one invocation form an include union and do not prove that each
  method exists.
- Scope a forbidden-production scan to production inputs. A rejection test may
  contain the forbidden literal it passes to production. Prove required
  operations independently; one alternation match is not several assertions.
- Inspect the generated and compiled consumer when the claim concerns generated
  API consumption. Searching the generator script, a comment, or dead text is
  not evidence that the consumer calls every required operation.
- Prefer independent commands or native bounded-output options over shell
  pipelines. When a pipeline is necessary, enable fail-loud pipeline semantics
  and prove that an upstream nonzero exit remains nonzero.
- Observe the exact property. A second successful operation proves reuse only
  when the requirement is usability; identity/history retention needs identity
  or lifecycle evidence, and exact-once cleanup needs a counted cleanup call.
  For resource checks, identify the resources owned by the operation. A
  process-wide count change alone proves neither a request leak nor its absence.

## Preparing expensive verification

Within the existing witness, distinguish the required product result, the
environment condition needed to exercise it, and supplementary measurements or
parameter calibration. Only authority makes an item a blocking acceptance
requirement, and the scope of each blocking item traces to its A-id or
acceptance authority; an existing large repository script does not authorize
its whole matrix as this feature's acceptance. When a named requirement
conflicts with code or model capability, the requirements owner decides; the
author does not self-exempt. Include every authority-permitted result in the oracle, including
an operation legitimately removing the environment condition that triggered it.

State each environment condition as the capability it must provide (interpreter and version,
JDK/SDK/NDK, dependency resolution, device, model source). An operating system, container
image, or offline-versus-online resolution mode chosen only for convenience is an execution
vehicle, not an acceptance condition: it binds acceptance only when authority names it or a
real production-boundary or tool-compatibility need requires it, and a vehicle with neither
basis must not be frozen as the only admissible environment. When an existing environment
carries the required capability, prefer it and record the actual vehicle with the run result.
An explicit authority-pinned environment or a genuine compatibility constraint stays binding
until its owning authority corrects it; running on a capable existing environment is not a
downgrade, and silently dropping either is not permitted. A reviewer applies the same trace:
an existing broad matrix alone, or a single enum/mapping change alone, without a requirement
source, adds no acceptance requirement on model output quality or task success for this
feature, and this rule never inverts into waiving a spec-named real-runtime acceptance item.

Resolve only decisive unknowns before a full expensive matrix: whether the
condition can be sustained, whether the actual result writer is observable and
its parser accepts legal output, and whether required serial waits and operations
fit the total budget. Reuse evidence or the smallest bounded probe; one readable
snapshot does not prove a sustained condition. The author performs non-mutating
checks now. If proof requires deployment, load generation or an unfinished
fixture, assign it to the already-authorized verification owner before the full
matrix; do not implement the entire fixture during authoring or add a universal
preflight ticket. An unresolved explicit safety prerequisite remains blocking.

In the existing check/gate definition, the author identifies the smallest
required target/selector, required parameter/environment sources, the actual
result writer/artifact and its parser/oracle. Distinguish required execution
from an explicitly consumed blocker result and an exact user waiver. Neither a
blocker PASS nor a cheaper subset replaces a gate requiring fresh runtime
evidence or a full suite. Keep final-gate reuse under its declared protocol.
The same ownership rule applies to a new or changed acceptance entry: statically
decidable runner/build-wiring, parameter, result-location, and assertion defects
belong to this ticket's implementation owner and are resolved before the ticket
completes, and a new class compiling is not observed entry
launch; when the launch observation itself needs a future device, build, or
unfinished dependency, assign it a named owner and condition at the earliest
feasible stage instead of turning every ticket into a hidden device gate, and
reuse valid existing launch evidence. Entry responsibility changes no explicit
ticket check or feature final gate contract.

For an existing verifier being changed, the implementation owner traces the
actual observation through its assertion and failure cleanup before the costly
run. Reuse prior evidence and the same witness rather than adding a pre-review
stage or a mutation suite:

- Identity, order and uniqueness require the corresponding comparisons of
  actual values; valid hash shape or equal counts alone cannot prove them.
- A role, registry or authorization claim reads the installed/runtime boundary
  required by authority; a script's own constant or PASS label is not evidence.
- After starting a background fixture/process, each reachable early failure
  uses the existing owner to release/wait for it, including failed reads/scans.

Inspect only the required changed seam. Do not introduce production
instrumentation, fake failure states or extra tests merely to fill this list.
Record the result by reference in the existing witness; later roles reuse it
unless the relevant producer, assertion or cleanup path changes.

## Target-runtime failure evidence

For real-runtime acceptance, the author names first-failure captures using
existing full logs/results and runtime conditions, plus a diagnostic question
and bounded attempts or duration. Do not add production instrumentation just to
satisfy a witness. Changed model sources, configurations or environments prove
only those conditions and cannot substitute for the original path. A later
success on identical code/conditions does not erase a failure; closure needs an
established cause with appropriate repair/reverification or explicit user
disposition. Take evidence before subsequent runs overwrite it; stop diagnosis
at its bound or when repeated failure adds no discriminating evidence.

## Unrealizable acceptance

If a legal production fixture cannot reach the asserted boundary, or the
authority permits an outcome the oracle rejects, return the ticket to authoring.
Do not add non-contract padding, fake-only failure behavior, timing sleeps, weak
proxy assertions, or broader success text to make the check green.

Move a shared proof to another production producer only when the authoritative
requirement is producer-independent and that producer has a legal reachable
fixture. Otherwise surface an authority gap or conflict. Changing which
observable behavior is required is not a verification-only repair.

When a production guard already excludes the legal input path for a boundary
assertion, record the structural exclusion proof and the public behavior that
still requires verification. The exclusion covers only the specific branch
proven unreachable, never the remaining reachable branches: observations that
authority already declares for them, such as actual receipt or event counting,
stay in the witness without a further authorization step. Retained observations
are limited to what the original authority already declared for reachable
branches; do not create an upstream actual-receipt or event-counting
requirement for an excluded downstream path. A producer send does not prove the
consumer received it, and structural exclusion does not prove another branch is
necessarily reachable. State the guard/order
conditions the exclusion relies on, re-verify when related structure changes, and
restore a branch's original observations when a legal path becomes reachable. Do
not weaken the guard, fabricate an input to reach the assertion, or dispatch a
device run for a path proven unreachable. An exclusion record does not waive a
product failure behavior or standalone verifier that authority separately
requires; send that requirement-versus-capability
conflict to its requirements/authority owner for an explicit decision.

## Review completeness

Author self-review and the exhaustive repository-alignment reviewer inspect
every applicable witness row; they do not sample a few commands or infer the
row from a test name. A missing legal fixture, reachability proof, complete
oracle, direct observation, or absence detector is a ticket defect even when
the command itself exits zero.
