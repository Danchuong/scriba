# A2 — Spec vs. Reference Gap Analysis

**Date:** 2026-04-24
**Reference:** `docs/SCRIBA-TEX-REFERENCE.md` (956 lines)
**Spec corpus:** 14 files in `docs/spec/` (~10k lines)

---

## Executive Summary

- **12 author-facing gaps** identified: items present in spec files but absent or incomplete in the reference. Severity HIGH → LOW.
- **Author-vs-internal split:** 8 of 14 spec files are almost entirely internal (architecture, scene-ir, svg-emitter, animation-css, leader-line, graph-edge-pill-ruleset, smart-label-ruleset, starlark-worker). 3 items from those do leak author-facing surface (env flags, `grid=` option, output_mode) and are flagged.
- **`error-codes.md`** is 90% author-facing. Reference §5.3 mentions `E1005` for duplicate labels but omits 14 other codes authors routinely encounter.
- **`environments.md`** reveals one missing env option (`grid=on|off`) and clarifies that `\compute` is valid inside `\step` blocks (frame-local scoping) — reference does not explain.
- **`starlark-worker.md`** reveals 7 builtins missing from pre-injected list (`isinstance`, `repr`, `round`, `chr`, `ord`, `pow`, `map`, `filter`) and confirms `range()` has 10^6-element cap not documented anywhere.

---

## Q1 — `error-codes.md`: Top 15 Author-Relevant Codes

| Code | Meaning for author |
|------|-------------------|
| E1001 | Unclosed `\begin{animation}` or unbalanced braces |
| E1003 | Nested `\begin{animation}` / `\begin{diagram}` — not allowed |
| E1004 | Unknown option key in `[id=..., label=..., ...]` bracket |
| E1005 | Invalid option/parameter value (type mismatch or bad label format) |
| E1006 | Unknown backslash command name |
| E1017 | Shape name invalid chars or >63-char limit |
| E1018 | Duplicate `\shape` name within one animation |
| E1019 | Duplicate `id=` across two `\begin{animation}` in same file |
| E1051 | `\shape` declared after first `\step` |
| E1055 | More than one `\narrate` in a single step |
| E1109 | Unknown state in `\recolor` (or neither `state=` nor `color=` given) |
| E1114 | Unknown keyword parameter on `\shape` declaration |
| E1150–E1155 | Starlark compute errors (syntax, runtime, timeout, step cap, forbidden, memory) |
| E1170–E1173 | `\foreach` errors (depth, empty body, unclosed, bad iterable) |
| E1248 | Label placement degraded — 32 candidates exhausted, pill may overlap |

Reference currently documents E1005 (§5.3), E1180/E1181 (§14), E1437 (§8 Plane2D). All others absent.

---

## Q2 — `environments.md`: Missing Options

Reference §10 lists 5 keys (`id`, `label`, `width`, `height`, `layout`). Spec adds:

| Key | Type | Default | Applies to | Meaning |
|-----|------|---------|------------|---------|
| `grid` | `on`\|`off` | `off` | diagram only | Debug grid overlay (authoring aid; suppressed in production) |

Spec also clarifies `id` constraint (`[a-z][a-z0-9-]*`, lowercase + digits + hyphens) and unknown-key → `E1004`.

`environments.md §8` documents output modes via `RenderContext.metadata["output_mode"]`:
- `"interactive"` (default) — step controller + keyboard nav + ~2KB JS
- `"static"` — zero JS, pure filmstrip `<ol>`, usable in email/PDF/Codeforces embed

Consumer-set, not author, but borderline. Worth footnote in §10.

---

## Q3 — `tex-ruleset.md` + `ruleset.md`: Missing Syntax

**From `tex-ruleset.md`:**

1. **Legacy text-formatting aliases** (`\bf{}`, `\it{}`, `\tt{}`) — Polygon compat. Reference §2.2 omits.
2. **Size commands** (`\tiny`, `\scriptsize`, `\small`, `\normalsize`, `\large`, `\Large`, `\LARGE`, `\huge`, `\Huge`). Both brace and switch forms. Reference §2 has nothing.
3. **Triple-dollar math** (`$$$...$$$`) as display alias (Polygon legacy).
4. **Curly-quote typography** (` ``text'' ` → `"text"`, `` `text' `` → `'text'`). Reference §2.8 lacks.
5. **`katex_macros`** — documented as allowed alternative to `\newcommand` for math-only macros. Reference §2.9 lists `\newcommand`/`\def` as unsupported but doesn't mention escape hatch.
6. **`\begin{lstlisting}` themes** — four themes (`one-light`, `one-dark`, `github-light`, `github-dark`, `none`) and copy button. Reference §2.5 only shows `[language=Python]`.
7. **Validation-only environments** (`verbatim`, `quote`, `figure`) pass through without transformation. Reference §2.9 says unsupported but doesn't distinguish parse-error from silent pass-through.
8. **`\href` safe URL schemes and disabled-link fallback** — non-http/https/mailto/ftp/relative → `<span class="scriba-tex-link-disabled">`. Reference §2.7 doesn't mention.

**From `ruleset.md`:**

9. **`\compute` inside `\step` (frame-local scoping)** — `ruleset.md §6.5` + `environments.md §3.2` make clear `\compute` may appear inside a `\step`, producing bindings only visible in that frame (dropped at next `\step`). Reference §5.2 implies prelude-only. **HIGH severity.**
10. **`CodePanel` 1-based line indexing** — ruleset §3 callout. Reference §7.11 says "1-indexed" but buries it; should be §13.x gotcha.
11. **`Queue` `.front` / `.rear`** selectors — listed in ruleset §3. Reference §7.14 and §8 show only `.cell[i]`.
12. **`Graph` additional parameters** — `auto_expand`, `split_labels`, `tint_by_source`, `tint_by_edge`, `global_optimize`, `orientation` (`"LR"`/`"TB"` for hierarchical). Reference §7.4 lists only `directed`, `layout`, `layout_seed`, `show_weights`.

---

## Q4 — `primitives.md`: Author-Facing Contracts

1. **`bounding_box()` purity (R-32.4)** — user consequence: annotation headroom reserved at per-scene max for ALL frames. Annotation only in frame 5 of 10-frame animation pushes all 10 frames upward. Should be §13 gotcha.
2. **`Matrix` full parameters** — `colorscale`, `show_values`, `vmin`/`vmax`, `row_labels`, `col_labels`, `cell_size`. Reference §7.7 only mentions basics.
3. **`Plane2D` full parameters** — `aspect`, `lines`, `segments`, `polygons`, `regions`, `points` as initial params; `add_segment`/`add_polygon`/`add_region` apply ops. Reference §7.9 covers basics.
4. **`MetricPlot` full parameters** — `show_legend`, `grid`, `xrange`, `yrange`, `width`, `height`, per-series `axis`/`scale`/`color`, two-axis mode. Reference §7.10 partial.
5. **`Tree` mutation ops** — `add_node`, `remove_node` with `cascade=true`, `reparent`. `E1433–E1436`. Absent entirely from reference.

---

## Q5 — `starlark-worker.md`: Missing Builtins & Constraints

Reference §5.2 lists:
```
len, range, min, max, enumerate, zip, abs, sorted, list, dict, tuple, set,
str, int, float, bool, reversed, any, all, sum, divmod, print
```

Actual list in `starlark-worker.md §7.3` adds:
```
isinstance, repr, round, chr, ord, pow, map, filter
```

All 7 allowed/intentional. `isinstance` especially useful. Absent from reference.

`starlark-worker.md §3.4` documents `range()` replaced with `_safe_range`, caps at **1,000,000 elements**, raises `E1173` on overflow. Reference §14 has no range cap.

`match` and walrus `:=` correctly listed as forbidden (E1154). Spec also forbids `hash()`, `.format()` with attribute fields, dunder chains — edge cases unlikely to trigger.

---

## Q6 — Internal-Mostly Specs: Author-Facing Leaks

| Spec file | Verdict | Leak |
|-----------|---------|------|
| `architecture.md` | INTERNAL | None |
| `scene-ir.md` | INTERNAL | None |
| `svg-emitter.md` | INTERNAL | None |
| `animation-css.md` | INTERNAL | None |
| `smart-label-ruleset.md` | MOSTLY INTERNAL | Env flags `SCRIBA_DEBUG_LABELS`, `SCRIBA_LABEL_ENGINE`. Reference §5.8 mentions in block-quote; consider promoting to §13.x gotcha |
| `graph-edge-pill-ruleset.md` | INTERNAL | `auto_expand`, `split_labels`, `tint_by_source`, `tint_by_edge` on `\shape{G}{Graph}` — author-facing params (GEP v2.0 Phase 5/6). Same as Q3-item 12 |
| `leader-line.md` | INTERNAL | Visual consequence: pill can render far from arrow, connected by leader. 1-sentence note in §5.8: "When collision avoidance displaces a pill far from its arrow, a leader line is automatically emitted" |

---

## Q7 — `\hl{label}{text}` Cross-Reference

Reference §5.3 is substantial and accurate: HTML `id` scheme, `data-label` attr, `E1005` on duplicates, character constraints, CSS `:target`, 3-labeled-steps example. Complete for authoring.

`ruleset.md §7.1` adds:
- **`E1320`** (`\hl` must appear inside `\narrate{…}` only) and **`E1321`** (step ID mismatch) — absent.
- Implicit step-id form `step{N}` (auto-generated for unlabeled steps) — ruleset says `\hl` can target these, reference §5.3 says opposite ("cannot be targeted by `\hl`"). **Documentation inconsistency to resolve.**

---

## Consolidated Gap Table

| Severity | Topic | Source | Recommended addition | Rationale |
|---|---|---|---|---|
| HIGH | `\compute` frame-local scoping | `ruleset.md §6.5`, `environments.md §3.2` | §5.2: note inside-step bindings are frame-local, dropped next step | Authors computing intermediate values don't know bindings don't persist |
| HIGH | Missing builtins: `isinstance, repr, round, chr, ord, pow, map, filter` | `starlark-worker.md §7.3` | §5.2: extend pre-injected list | Authors avoid useful fns thinking unavailable |
| HIGH | `range()` element cap 10^6 | `starlark-worker.md §3.4` | §14: add "Starlark range() max 1M elements (E1173)" | Silent E1151→E1173 shift undocumented |
| HIGH | Tree mutation ops (add_node/remove_node/cascade/reparent) | `error-codes.md §E1433-E1436`, `primitives.md §7` | §7.5 Tree: add mutation subsection | Only way to mutate Tree during animation; absent |
| MEDIUM | `grid=on\|off` env option | `environments.md §2.4` | §10: add grid row (diagram only) | Authors using diagram may want debug grid |
| MEDIUM | `id` value constraint `[a-z][a-z0-9-]*` | `environments.md §2.4`, `ruleset.md §1.2` | §10: annotate id row | Uppercase/underscore in id → E1004 with no hint |
| MEDIUM | Queue `.front` / `.rear` | `ruleset.md §3` | §8 selector table: add | Exist and useful; invisible otherwise |
| MEDIUM | Graph flow-network params (`tint_by_source/edge`, `split_labels`, `auto_expand`) | `ruleset.md §5.4`, `primitives.md §6.1` | §7.4: add "Flow network visual controls" subsection | Dual-value flow/capacity patterns |
| MEDIUM | Matrix params (`colorscale`, `vmin/vmax`, row/col_labels) | `ruleset.md §5.9` | §7.7: expand params | Heatmap colorscale control |
| MEDIUM | Size commands (`\tiny`…`\Huge`) | `tex-ruleset.md §2.3` | §2: add Size subsection | Undocumented; can't vary text size |
| LOW | Legacy text aliases (`\bf`, `\it`, `\tt`) | `tex-ruleset.md §2.2` | §2.2: footnote | Polygon-sourced content compat |
| LOW | `\hl` errors E1320/E1321 + step{N} form inconsistency | `ruleset.md §7.1` | §5.3: add error table + resolve step{N} discrepancy | Misplaced `\hl` error unknown |
| LOW | Annotation headroom reflow (R-32) | `primitives.md §2.6`, `ruleset.md §8.9` | §13: gotcha "annotations reserve headroom for full scene" | Explains vertical layout shifts |
| LOW | MetricPlot params (`show_legend`, two-axis, per-series config) | `ruleset.md §5.7` | §7.10: expand params | Dual-axis charts |
