# Regression fixtures

Two buckets:

| Dir | Expected outcome |
|---|---|
| `pass/`           | `render.py` MUST succeed. One `.tex` per pinned-bug regression guard. |
| `expected-fail/`  | `render.py` MUST fail with the pinned error. Any success = regression. |

See `manifest.toml` for per-file metadata (bug class, error code, original fix commit).

## Build

```bash
./examples/build.sh --fixtures          # run both buckets, report pass/fail
```

Single file:

```bash
uv run python render.py examples/fixtures/pass/01_variablewatch_shrink.tex -o /tmp/out.html
```

## Adding a fixture

1. Write minimal `.tex` that reproduces the bug pre-fix.
2. Put in `pass/` if fix makes it render, `expected-fail/` if spec says it must error.
3. Add row to `manifest.toml`.
4. Run `./examples/build.sh --fixtures` — must report `failed=0`.
