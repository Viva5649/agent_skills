# Text embedding planning replay

This is a compact replay fixture, not a claim that these files ran on hardware.
For this planning exercise, treat the supplied historical evidence as established.
The user requests an implementation-ticket proposal only, without creating tickets,
changing production code, running hardware or starting admission review.

## Confirmed delivery

Deliver the complete text embedding SDK in one release. Preserve existing Chat
behavior and shared runtime capacity. There is no independent release of runtime
type, model checking or numerical-reference tooling. No public model registry,
retry mechanism or second model implementation is requested.

## Product contract and existing ownership

- Runtime owns an immutable CHAT/EMBEDDING task. Runtime publishes LOADED only
  after its existing Engine has loaded a model compatible with that task.
  Binding the task and enforcing loaded-model compatibility establish one load
  invariant owned by Runtime. Existing lifecycle and cleanup ownership stays.
- Engine owns model interpretation, native resources and text-to-vector
  computation. The first supported model has dimensions 768/512/256/128. Shared
  Runtime code consumes model-neutral information from Engine; another supported
  dimension must not require a model-name branch in Runtime.
- The public request lifecycle accepts a batch for the loaded model, preserves
  raw text and input order, returns complete vectors and token usage once, rejects
  a concurrent batch and handles cancellation through the existing cleanup owner.
  This lifecycle consumes Engine's computation contract and needs separate
  cross-process acceptance. It fits its own fresh implementation context.
- The runtime load invariant fits one fresh context. Native computation has its
  own resource owner and produces the inference interface consumed by the public
  request lifecycle. No intermediate API/schema-only release is required.

## Established feasibility evidence

The earlier bounded experiment already proved: native CPU loading and full model
projection; independent same-model numerical references at all four dimensions;
runtime constructor binding through the real transport; maximum legal request and
response delivery. Model/library identities and raw results were retained.
Those findings remove the feasibility questions. They do not prove production
SDK binding, resource ordering or public callback behavior. Formal acceptance
still includes real SDK transport, native numerical results and a release consumer.

## Repository excerpt

`runtime.py` and `engine.py` show the existing production boundary. The planning
owner may use this excerpt to identify affected owners and interface changes.
The excerpt is deliberately small; do not infer an unseen repository or promise
executable tickets from missing full-repository inputs.
