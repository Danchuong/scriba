# Scriba Comprehensive Audit — 2026-04-17

Six-domain audit of scriba covering Starlark sandbox, runtime/a11y, CSS/theming,
performance, security, and test coverage. All reports empirical (PoCs run
against live system, contrast ratios computed from hex, render times measured
via `time` and cProfile).

## Reports

1. [01-starlark-compute.md](01-starlark-compute.md) — sandbox escape vectors, resource limits, IPC lifecycle
2. [02-runtime-a11y.md](02-runtime-a11y.md) — keyboard/focus, ARIA, multi-widget, embed mode
3. [03-css-theming.md](03-css-theming.md) — dark mode parity, contrast (WCAG), responsive
4. [04-performance.md](04-performance.md) — scaling, hot paths, output bloat
5. [05-security.md](05-security.md) — XSS, path traversal, injection, CSP
6. [06-coverage-deadcode.md](06-coverage-deadcode.md) — coverage %, dead code, error-code drift

## Critical Findings — Severity Matrix

| ID | Severity | Class | File | Effort |
|---|---|---|---|---|
| **C1** Cumulative Starlark budget never wired | 🔴 critical | resource limit | `starlark_host.py:eval` | small (4 lines) |
| **C2** XSS via filename in `<title>` and `<h1>` | 🔴 critical | XSS | `render.py:34,44` | trivial (1 line) |
| **C3** `current` state fails WCAG AA contrast (3.26:1) — comment claims "AA verified" | 🔴 critical | a11y | `scriba-scene-primitives.css` | small |
| **H1** Path traversal via `-o` flag (`-o /etc/foo.html`) | 🟠 high | filesystem | `render.py:219` | small |
| **H2** C-level list allocation bypasses SIGALRM (1.84s, 9M ints) | 🟠 high | resource limit | `starlark_worker.py` | small |
| **H3** Substory arrow-key event bubbles to parent widget | 🟠 high | UX | `emitter.py:1342` | trivial (1 line) |
| **H4** Widget container missing `aria-label` (silent on Tab focus) | 🟠 high | a11y | `emitter.py:1053` | trivial (2 lines) |
| **H5** Annotation arrowheads + label pills not dark-mode styled | 🟠 high | theming | `scriba-annotations.css` | small |
| **H6** No `prefers-color-scheme` support — manual toggle only | 🟠 high | theming | CSS root | small |
| **M1** Touch targets ~30px (WCAG 2.5.5 = 44px) | 🟡 medium | a11y | `scriba-embed.css:51` | trivial |
| **M2** 11 ms wasted re-minifying already-minified KaTeX CSS per render (56% of total!) | 🟡 medium | perf | `css_bundler.py` | trivial (lru_cache) |
| **M3** RecursionError discloses internal worker path | 🟡 medium | infoleak | `starlark_worker.py:527` | small |
| **M4** Inline `<script>` + `onclick` block strict CSP | 🟡 medium | embed | `emitter.py` | medium |
| **M5** 15 E-codes raised but missing from `error-codes.md` catalog | 🟡 medium | docs | `errors.py` ↔ spec | small |
| **M6** Progress dots missing `aria-hidden`, double-announced | 🟡 medium | a11y | `emitter.py` | trivial |
| **M7** `prefers-reduced-motion` snapshotted once at init, not reactive | 🟡 medium | a11y | `emitter.py:1086` | small |
| **L1** Dead code: `validation_error_from_selector` (~55 lines), `eval_raw` (~22 lines) | 🔵 low | hygiene | `errors.py:644`, `starlark_host.py:197` | trivial |
| **L2** Cell-selector regex duplicated across 6 primitives | 🔵 low | DRY | various primitives | small |
| **L3** Stage `--scriba-stage-bg` defined but unused | 🔵 low | dead CSS | css | trivial |
| **L4** Controls bar overflow-clipped at 320px ≥6 steps (no `flex-wrap`) | 🔵 low | responsive | `scriba-embed.css` | trivial |

## Top 10 Fix Order

### Round A — Security (no design debate, do now)
1. **C2** Escape filename in render.py title/h1 (1-line `html.escape`)
2. **H1** CWD-anchored output path validation
3. **C1** Wire `consume_cumulative_budget` into `StarlarkHost.eval`
4. **H2** Whitelist-cap `list` builtin in worker (cap result size)

### Round B — A11y + UX (high-value, low-effort)
5. **H3** Stop substory arrow-key bubbling — `if(e.target.closest('.scriba-substory-widget'))return;`
6. **H4** Add `aria-label` and `role="region"` to widget container
7. **C3** Fix `current` state contrast — darker blue or larger text-stroke; remove false "AA verified" comment

### Round C — Theming + Perf
8. **H5** + **H6** Dark-mode arrowheads/pills + add `@media (prefers-color-scheme: dark)` selector
9. **M2** `@functools.lru_cache` `inline_katex_css` and `load_css` (56% render-time reduction)
10. **M5** Backfill missing E-codes in `error-codes.md` (E1017–E1019, E1057, E1114, E1200, E1433–E1437, E1471–E1474)

### Round D — Hygiene (defer)
- **L1** Delete dead `validation_error_from_selector` + flag `eval_raw` for human review
- **L2** Consolidate cell-selector regex
- **L3** Remove `--scriba-stage-bg`
- **L4** Add `flex-wrap` to controls bar

## What Held Up Well

- Starlark sandbox: 70+ exploit attempts blocked (imports, dunder chains, format-string escape, `exec`, `__subclasses__`, deep recursion, lambda/walrus/async — all caught E1154)
- KaTeX `trust: false` confirmed; XSS via narrate/labels blocked
- No pickle anywhere; subprocess uses list argv (no shell injection)
- Multi-widget pages: SHA-256-namespaced IDs prevent collision
- IPC lifecycle: no orphan workers, no pipe deadlocks, clean crash recovery
- 84.72% test coverage overall (above 75% threshold)
- 81/81 CSS custom properties consistently namespaced `--scriba-*`
- Render perf at realistic scale (3-10 frames, N≤500): 3-23 ms — fine

## Methodology Note

Every "🔴 critical" claim has a working PoC reproducible from the linked report.
Contrast ratios computed from `STATE_COLORS` hex values per WCAG formula.
Render times measured 5-run median via `time` + cProfile.
