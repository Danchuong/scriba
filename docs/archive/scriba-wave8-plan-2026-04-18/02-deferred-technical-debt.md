# Wave 8 — Deferred Technical Debt

Items intentionally not shipped in Wave 7 because they require coordinated release timing or downstream notice. Tracked here so they do not silently rot.

---

## D1 — Remove `eval_raw` Starlark surface

**Status:** deprecated, still present
**Trigger to remove:** next minor release with breaking-change budget (target v0.9.0)
**Effort:** small (delete + grammar update + a few error-message changes)

### Why it exists

`eval_raw` was the original mechanism for running user Starlark inside `\compute` blocks before the typed `\compute` API stabilised. It accepted an unrestricted code string and executed it under the sandbox.

### Why it must go

- Duplicated surface — every constraint added to `\compute` (budget, deny-list, return type) had to be re-implemented for `eval_raw`, and at least once was forgotten.
- Cannot be statically analysed — defeats the lexer's E12xx category checks.
- No real users left in any tracked corpus; tutorials migrated in v0.7.
- Removal collapses the Starlark host's request schema and removes one whole class of "did this go through the new path or the old path?" debugging.

### Removal plan

1. Mark with explicit `DeprecationWarning` on first use in v0.8.3 (already true since v0.7).
2. Add changelog entry: "v0.9.0 will remove `eval_raw`. Migrate to `\compute{...}`."
3. Delete handler, grammar token, host-side dispatch, and tests.
4. Keep one canary integration test that asserts `eval_raw` raises `E1xxx` with a migration hint.

### Risk

Low. No public docs reference it; only legacy fixture files outside `examples/` use it, and those are pinned to old versions.

---

## D2 — Inline CSS extraction (companion to Wave 8 architecture)

**Status:** scoped out of CSP migration deliberately
**Trigger:** when a strict CSS CSP becomes a real customer requirement
**Effort:** medium-large

`scriba.js` extraction handles `script-src`. CSS still ships inline per render, so `style-src 'self'` strict mode is still impossible without `'unsafe-inline'` for styles.

Reason for deferring:

- Per-render CSS is genuinely per-render (theme tokens, per-shape custom props).
- Splitting into "static + dynamic" requires a tokenisation pass that is non-trivial and risks visual regressions.
- No current customer requires `style-src 'self'` without `'unsafe-inline'`.

Revisit if/when a customer asks, or as part of Wave 9.

---

## D3 — Worker IPC schema versioning

**Status:** implicit (no version field on the wire)
**Trigger:** before any change that alters request/response shape
**Effort:** small

Today the worker subprocess and host agree on JSON shapes by convention. Wave 7 W7-C2 had to add an `id` correlation field on the SIGXCPU error path; future changes (e.g. adding `request.macros` lift to host-side, or returning structured warnings) will break old workers in mixed installs.

Plan:

- Add a `protocol_version: int` field to every request and every response.
- Worker rejects requests below its known floor with a clear error code.
- Host upgrades the version when it knows new fields exist.

Defer until the next on-the-wire change is needed; doing it speculatively burns the version namespace.

---

## D4 — Telemetry / structured logs

**Status:** absent
**Trigger:** when first real user reports a "Scriba is slow on my big doc" without enough context to diagnose
**Effort:** small for opt-in, medium to do well

No structured logging exists today. All diagnostics go through error codes (`E1xxx`) or `print` to stderr. Performance benchmarks (Wave 8 audit P6) will need at least frame-render timing per-block to be useful.

Minimum acceptable shape:

- Opt-in via env var or CLI flag, off by default.
- NDJSON to stderr or a path.
- Per-render: total ms, per-block ms, KaTeX cache hit ratio, Starlark cumulative budget used.
- No PII; no document content.

Defer until first real performance complaint, then build with that complaint as the validation case.
