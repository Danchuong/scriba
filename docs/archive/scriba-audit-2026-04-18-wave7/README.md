# Scriba Audit Wave 7 — 2026-04-18

Six-domain follow-up audit after Wave 5 (`scriba-audit-2026-04-17`) shipped.
Targets gaps surfaced during Wave 6 verification (worker hard-crash) and
domains not covered originally (i18n, browser compat, CSP migration plan,
KaTeX edges, memory leaks across long sessions).

All findings empirical: PoC `.tex` files rendered, RSS measured via `ps`,
fd counts via `lsof`, browsers checked against caniuse baseline.

## Reports

1. [01-katex-edges.md](01-katex-edges.md) — KaTeX macros, `\$` escapes, math regex bugs
2. [02-ipc-concurrency.md](02-ipc-concurrency.md) — SIGXCPU root cause + thread safety
3. [03-memory-leaks.md](03-memory-leaks.md) — RSS over 1000 renders, lru_cache scope
4. [04-browser-compat.md](04-browser-compat.md) — Safari/Firefox ESR fallbacks
5. [05-i18n-unicode.md](05-i18n-unicode.md) — UTF-8 BOM, CJK width, Vietnamese idents
6. [06-csp-hardening.md](06-csp-hardening.md) — strict CSP migration plan (Wave 5 M4)

## Critical Findings — Severity Matrix

| ID | Severity | Class | File | Effort |
|---|---|---|---|---|
| **W7-C1** `katex_macros` discarded by JS worker (silent red text) | 🔴 critical | correctness | `scriba/tex/katex_worker.js:71` | trivial (3 lines) |
| **W7-C2** SIGXCPU kills worker hard — no graceful E1152 | 🔴 critical | IPC robustness | `starlark_host.py:113`, `starlark_worker.py` | small |
| **W7-H1** `\$` in narrate creates phantom math region (≥2 escapes) | 🟠 high | correctness | `scriba/tex/renderer.py:342` | small |
| **W7-H2** `_cumulative_elapsed` module-level — not thread-safe | 🟠 high | concurrency | `starlark_worker.py:533` | small |
| **W7-H3** `render.py` reads/writes without `encoding="utf-8"` | 🟠 high | i18n | `render.py:106,212` | trivial (2 lines) |
| **W7-H4** UTF-8 BOM passes through, breaks first `\section` | 🟠 high | i18n | `render.py:106` | trivial (`utf-8-sig`) |
| **W7-H5** `estimate_text_width` ignores CJK fullwidth + ZWJ emoji | 🟠 high | i18n | `primitives/base.py:133` | small |
| **W7-H6** `matchMedia.addEventListener` no fallback (Safari ≤13) | 🟠 high | browser | `emitter.py:1089` | trivial |
| **W7-H7** `CSS.escape` 5 unguarded calls — TypeError on old browsers | 🟠 high | browser | `emitter.py:1138,1188,1212,1219,1227` | small |
| **W7-H8** SVG `orient="auto-start-reverse"` breaks Firefox ESR ≤88 | 🟠 high | browser | `emitter.py:342`, `graph.py:219` | small |
| **W7-M1** Cumulative budget leaks across renders sharing `StarlarkHost` | 🟡 medium | resource | `starlark_host.py:152` | small |
| **W7-M2** Unknown KaTeX cmds bypass E1200 scan (color-attr instead) | 🟡 medium | docs/UX | `tex/renderer.py:56` | small |
| **W7-M3** `$$...$$` in narrate degrades to inline + literal `$` | 🟡 medium | correctness | `tex/renderer.py:342` | small |
| **W7-M4** Lexer `_IDENT_RE` ASCII only — Vietnamese ids misparse silently | 🟡 medium | i18n | `parser/lexer.py:89` | small |
| **W7-M5** `<html lang="en">` hardcoded | 🟡 medium | a11y/i18n | `render.py:32` | trivial |
| **W7-M6** narrate `<p>` missing `dir="auto"` (Arabic/Hebrew bidi) | 🟡 medium | i18n | `emitter.py:1065` | trivial |
| **W7-M7** `slugify` strips all CJK/Arabic → duplicate `id=` | 🟡 medium | i18n | `tex/parser/environments.py:20` | small |
| **W7-M8** `font-synthesis-weight: none` no shorthand fallback | 🟡 medium | browser | `scriba-scene-primitives.css:356` | trivial |
| **W7-M9** `:where()` 12 selectors — silent style drop on Safari ≤13.1 | 🟡 medium | browser | various CSS | small |
| **W7-M10** `forced-colors: none` ignored on FF ≤88 / Safari ≤15 | 🟡 medium | browser | CSS | trivial |
| **W7-M11** `DOMParser` + `importNode` Safari 14.0 `data-*` loss | 🟡 medium | browser | emitter.js | small |
| **W7-M12** Inline `<script>` + `onclick` block strict CSP (Wave 5 M4) | 🟡 medium | security | `emitter.py:1071`, `render.py:42` | medium |
| **W7-M13** 60KB inline JS = 48.5KB frame data + 11.7KB runtime | 🟡 medium | architecture | `emitter.py` | medium |
| **W7-L1** `lru_cache` holds ~16MB KaTeX permanent (bounded — by design) | 🔵 low | hygiene | `css_bundler.py:16` | none (intentional) |
| **W7-L2** `re.compile` in hot `_expand_selectors` — 512 re cache OK | 🔵 low | perf | `emitter.py:367` | trivial |
| **W7-L3** WorkerError on crash carries no E-code (should be E1199) | 🔵 low | docs | `core/workers.py` | trivial |
| **W7-L4** Lexer column counts codepoints not graphemes | 🔵 low | i18n | `parser/lexer.py` | small |
| **W7-L5** Non-ASCII `\step[label=...]` falls back to `frame-N` silently | 🔵 low | i18n | grammar | small |
| **W7-L6** `_wrap_label_lines` never wraps CJK (no spaces) | 🔵 low | i18n | `primitives/base.py` | small |
| **W7-L7** Preamble + `%` comments leak into TeX region `<p>` output | 🔵 low | docs | `tex/renderer.py` | small |
| **W7-L8** `graph.py:696` `html_escape(str(u))` missing `quote=True` | 🔵 low | XSS-adjacent | `graph.py:696` | trivial |
| **W7-L9** scroll-snap, `font-display`, `closest`, logical props — fine | 🔵 low | browser | CSS | none |

**Totals:** 2 critical, 8 high, 13 medium, 9 low = **32 findings**.

## Top 12 Fix Order

### Round A — Critical (no debate)
1. **W7-C1** Thread `request.macros` through `katex_worker.js` `renderOne(...)`
2. **W7-C2** Split `RLIMIT_CPU` soft/hard + install SIGXCPU handler in worker

### Round B — Correctness + i18n trivial wins
3. **W7-H1** + **W7-M3** Apply `_DOLLAR_LITERAL` normalisation in `_render_cell` and add `$$` handler
4. **W7-H3** + **W7-H4** `encoding="utf-8-sig"` for read, `encoding="utf-8"` for write in render.py
5. **W7-H5** Replace `len(text) * 0.62` with `unicodedata.east_asian_width()` + grapheme-aware count
6. **W7-M5** + **W7-M6** Add `lang` attribute (CLI arg `--lang vi`) and `dir="auto"` on narrate `<p>`

### Round C — Concurrency + budget hygiene
7. **W7-H2** + **W7-M1** Move `_cumulative_elapsed` into `StarlarkHost` instance, reset per `render_block`
8. **W7-M2** Augment `_KATEX_ERROR_RE` to also match `color:#cc0000` color-attr fallback

### Round D — Browser compat trivial wins
9. **W7-H6** `matchMedia` dual-register (`addEventListener` || `addListener`)
10. **W7-H7** Inline `CSS.escape` polyfill (3-line ternary fallback)
11. **W7-H8** Emit two `orient="auto"` markers (forward + reverse) instead of `auto-start-reverse`
12. **W7-M4** Allow Unicode in `_IDENT_RE` (`\w` with `re.UNICODE`) OR raise E1xxx with hint

### Round E — Defer (medium effort or design discussion needed)
- **W7-M12** + **W7-M13** External `scriba.js` migration (CSP nonce-free)
- **W7-M7** `slugify` CJK-aware (transliterate or hash fallback)
- **W7-M8/M9/M10/M11** CSS browser-fallback polish

### Round F — Hygiene
- **W7-L3** Add E1199 to `WorkerError(closed unexpectedly)`
- **W7-L8** `quote=True` in `graph.py:696` html_escape
- **W7-L7** Strip preamble + `%` in TeX region

## Methodology

Every finding has a working PoC. Browser compat checked against Safari 14
(stated floor) with explicit notes for slips below. Memory measured via
`ps -o rss` over 1000-render loops. IPC bug reproduced with
`returncode=-24` (SIGXCPU) confirmed.

## Confirmed OK

- KaTeX `trust: false` — `\href{javascript:}` blocked
- KaTeX `maxExpand: 100` — macro bombs caught
- `html.escape`, `_escape_xml`, `_escape_js` all sound
- NFC normalisation present (Wave 5.1)
- subprocess.Popen list argv (no shell injection)
- Worker process recycled at 50000-request threshold
- No fd leaks across 100 renders
- KaTeX `trust: false`, no narration bypass
- SVG `<title>` content escaped
- Backtick template literal escape covered
- `data-*` attributes properly escaped
- Worker subprocess RSS grew only +80 KB / 500 evals
- `tracemalloc` start/stop clean
- WAAPI / `MutationObserver` properly guarded
- No `<foreignObject>` / filter / mask / `<use>` in SVG output
