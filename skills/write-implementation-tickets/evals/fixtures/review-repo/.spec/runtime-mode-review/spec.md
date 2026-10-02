# Runtime mode review spec

## Behavior

`Settings.runtime_mode()` reads the `runtime_mode` configuration value and
returns the result of `RuntimeMode.from_key(value: str)`. Supported values are
`cpu` and `gpu`; any other value raises `ValueError`.

`Worker.configure(settings: Settings)` stores the resolved `RuntimeMode` for
later task execution. No compatibility alias, retry, cache, or additional
mutable state is required.

## Verification

Run:

```bash
python3 -m unittest tests.test_runtime_mode
```

The command must pass.
