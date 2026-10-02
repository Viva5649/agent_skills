# Runtime mode configuration key

## Observable behavior

- `SettingsLoader` accepts `runtimeMode` values `local` and `remote` and rejects
  any other value with `ValueError`.
- During one compatibility release, `SettingsLoader` accepts `oldMode` only when
  `runtimeMode` is absent and emits `DeprecationWarning`.
- When both keys are present, `runtimeMode` is authoritative.
- `Worker` consumes the normalized `runtime_mode`; it does not inspect either
  public configuration key.
- The operator documentation shows `runtimeMode` as the supported key.

## Migration constraint

The repository must remain green after every implementation ticket. Remove
`oldMode` compatibility only after all internal callers and documentation use
`runtimeMode`. Preserve each completed migration ticket as historical evidence.

## Verification

From the repository root, run
`PYTHONPATH=src python3 -m unittest discover -s tests -v` after every ticket.
