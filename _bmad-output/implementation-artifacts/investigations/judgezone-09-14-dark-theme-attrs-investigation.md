# Investigation: JudgeZone #9 + #14 — dark-mode CSS escapes and over-reach in the annotation/label decoration layer

## Hand-off Brief

1. **What happened.** Two independent, real defects, in opposite directions, both rooted in the same mechanism (an SVG presentation attribute baked in as a light-mode fallback, overridden by a stylesheet rule that either reaches too far or doesn't reach at all). Bug #9 (Confirmed, **over-reach**): the dark-mode rule that flips annotation label pills from white to dark also flips the `\annotate{bracket=true}` outline rect, because both share the `.scriba-annotation` parent class and the rule carries no attribute qualifier. Bug #14 (Confirmed, **escape**): the Plane2D line-label chip (pill rect + text) is emitted classless with hardcoded light attributes, and `scriba-plane2d.css` has zero fill rules for it in any scope.
2. **Where the case stands.** Concluded. No source files were modified — this is investigation-only. The structural audit (Ask 1) additionally found 16 more escaped emission sites beyond bug #14's own two, spread across Plane2D, Graph, MetricPlot, and CodePanel, plus a narrow, previously-invisible escape inside the *already-shipped* graph-weight-pill dark-mode fix itself.
3. **What's needed next.** Apply Fix A (#9) and Fix B (#14) below first — both are small, precedent-backed, and match the codebase's own established idioms exactly. The remaining 15 escapes (Fix C–F) share one of two fix shapes already proven safe elsewhere in this file (`[fill="white"]` attribute-scoping, or a new class + `[data-theme="dark"]`/`@media` pair) and can be swept as a follow-up batch using `tests/unit/test_contrast.py::TestGraphPillDarkMode` as the regression-test template.

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | JudgeZone #9 (HIGH, dark mode) + #14 (MED, dark mode) + Structural Ask 1 (theme-attribute audit) |
| Date opened      | 2026-07-10 |
| Status           | Concluded |
| System           | scriba @ 13eadc7 (0.34.0) |
| Evidence sources | source (`scriba-scene-primitives.css`, `scriba-plane2d.css`, `scriba-metricplot.css`, `scriba-embed.css`, `scriba-animation.css`, `scriba-standalone.css`, `base.py`, `plane2d.py`, `graph.py`, `metricplot.py`, `codepanel.py`, `_svg_helpers.py`, `_frame_renderer.py`, `_text_render.py`, `_types.py`, `array.py`, `dptable.py`, `queue.py`), `tests/unit/test_contrast.py`, `tests/unit/test_graph_typography.py`, 2 live renders via `render.py` |

## Problem Statement

**Bug #9 (HIGH):** `scriba-scene-primitives.css` (~line 890) has `[data-theme="dark"] .scriba-annotation > rect { fill: #1a1d1e; }` plus its `@media (prefers-color-scheme: dark)` twin (~line 901), intended to flip annotation label-pill backdrops to dark. It also catches the bracket rect from `\annotate{...}{bracket=true}` (emitted with `fill="none"` + dashed stroke), painting an opaque dark box over the annotated block in dark mode. Reporter's suggested fix: scope to `> rect[fill="white"]`, citing the graph-weight-pill rule (~line 915) as precedent — a rule whose own comment cites `.scriba-annotation > rect` as the pattern it mirrors.

Repro:
```latex
\begin{diagram}[id="t"]
\shape{g}{Grid}{rows=3, cols=3, data=[[1,2,3],[4,5,6],[7,8,9]]}
\annotate{g.block[0:1][0:1]}{label="block", bracket=true}
\end{diagram}
```

**Bug #14 (MED):** The Plane2D line-label chip is emitted class-less with hardcoded light attributes (`<rect fill="white" fill-opacity="0.85">` + `<text fill="#11181c">`), with no dark-mode CSS rule matching classless elements. Reporter suggests a class + dark pair, or an attribute-scoped rule, and asks whether `scriba-plane2d.css` already styles the chip.

Repro:
```latex
\begin{diagram}[id="t"]
\shape{S}{Plane2D}{xrange=[0,12], yrange=[0,13], lines=[{from=(0,0), to=(12,12), label="m=d"}]}
\end{diagram}
```

**Structural Ask 1:** Enumerate every SVG element the renderers emit with a hardcoded light-theme presentation attribute, classify each as (a) covered by a dark-mode selector, (b) theme-neutral by design, or (c) escaped, and produce an exhaustive emitter → light attr → dark rule (or ESCAPED) table across every shipped CSS file.

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| `scriba/animation/static/scriba-scene-primitives.css` (1252 lines, read in full across passes) | Available (Confirmed) | Central stylesheet; universal `.scriba-state-*` rules (203-268), annotation rules (527-729), graph-pill dark rules (890-936), dark-token blocks (39-42, 748-753, 817-822) |
| `scriba/animation/primitives/base.py` | Available (Confirmed) | Bracket-rect emitter (1577-1599), pill-backdrop emitter (779), `state_class()` (1705-1707), `ARROW_STYLES`/`STATE_COLORS` definitions, dead `DARK_THEME` import (41) |
| `scriba/animation/primitives/plane2d.py` | Available (Confirmed) | Line-label pill+text emitter (1843-1865), point-label text (1827-1841), `_emit_tick_labels` (1909-1955) |
| `scriba/animation/static/scriba-plane2d.css` (47 lines, read in full) | Available (Confirmed) | Zero fill rules for `.scriba-plane-labels text` or any rect; zero `data-theme`/`prefers-color-scheme` matches |
| `scriba/animation/primitives/graph.py` | Available (Confirmed) | Weight-pill tint branches (2420-2432), `_pill_tint_for_state`/`_pill_tint_for_edge_state` (234-257), group-label emitter (2075-2086) |
| `scriba/animation/primitives/metricplot.py` | Available (Confirmed) | Axis lines self-themed via `var(--scriba-fg, #11181c)`; tick-label text and xlabel/ylabel emission (510-607) |
| `scriba/animation/static/scriba-metricplot.css` (29 lines, read in full) | Available (Confirmed) | No screen-mode fill rule for tick/axis text; only `@media print` sets `#000 !important` |
| `scriba/animation/primitives/codepanel.py` | Available (Confirmed) | Panel chrome (270-407): background rect, per-line state group, header bar |
| `scriba/animation/primitives/_text_render.py` | Available (Confirmed) | `_render_svg_text` default `fill="#11181c"`, `css_class` optional; font-family branch for label/index classes (360-399) is unrelated to color |
| `scriba/animation/primitives/_svg_helpers.py`, `_frame_renderer.py` | Available (Confirmed, from prior pass) | `emit_plain_arrow_svg`/`emit_position_label_svg` pill sites; "note" annotation pill site — all direct children of a `.scriba-annotation`-classed `<g>` |
| `scriba/animation/static/scriba-embed.css` | Available (Confirmed) | 28 `data-theme`/`prefers-color-scheme` matches, all widget-chrome (`.scriba-widget`, `.scriba-controls`, `.scriba-frame`, `.scriba-step-counter`, etc.) — separate concern from primitive-content SVG |
| `scriba/animation/static/scriba-animation.css`, `scriba-standalone.css` | Available (Confirmed) | Zero `data-theme`/`prefers-color-scheme`/`fill`/`stroke` matches — irrelevant to theming |
| `tests/unit/test_contrast.py` | Available (Confirmed) | `TestGraphPillDarkMode` (333-447) is the exact regression-test template for the `[fill="white"]` attribute-scoping pattern; `TestArrowStylesLabelContrast` confirms `ARROW_STYLES[...]["label_fill"]` is tuned only against a white pill background |
| `tests/unit/test_graph_typography.py` | Available (Confirmed) | `test_tint_by_source_changes_pill_fill` (87-96) confirms the default (no tint flags) pill fill is the literal string `fill="white"` |
| 2 live renders (see Reproduction Plan) | Available (Confirmed) | Rendered via `render.py` from `.scriba_tmp/` inside the repo (the tool refuses paths outside cwd); raw HTML inspected byte-for-byte |

## Confirmed Findings

### Finding 1: Bug #9 is a real over-reach — one rule, two unrelated rect roles under the same parent class
**Evidence:** `scriba-scene-primitives.css:890` and `:901` (twin) — `[data-theme="dark"] .scriba-annotation > rect { fill: #1a1d1e; }`, no attribute qualifier. `base.py:1577-1599` emits the bracket as `<g class="scriba-annotation scriba-annotation-{color}" data-annotation="...-block-bracket"><rect ... fill="none" stroke="{ARROW_STYLES[...]['stroke']}" stroke-width="1.5" stroke-opacity="0.55" stroke-dasharray="4,3"/></g>`. Live render confirms verbatim:
```html
<g class="scriba-annotation scriba-annotation-info" data-annotation="g.block[0:1][0:1]-block-bracket">
<rect x="-3.0" y="-3.0" width="128.0" height="88.0" rx="6" ry="6" fill="none" stroke="#506882" stroke-width="1.5" stroke-opacity="0.55" stroke-dasharray="4,3"/>
```
**Detail:** `> rect` matches *any* direct-child rect regardless of its own attributes, and CSS specificity rules mean the stylesheet's `fill: #1a1d1e` always beats the presentation attribute `fill="none"` — there is no way for the bracket to "win" against this rule as currently written. The same `.scriba-annotation` group class is legitimately shared by four other rect sites (`base.py:779`, `_svg_helpers.py:~2235`, `_svg_helpers.py:~3787`, `_frame_renderer.py:1708`) that are all pill backdrops emitted with literal `fill="white"` and *should* flip — confirmed live in the same repro output:
```html
<rect x="41" y="-22" width="40" height="19" rx="4" ry="4" fill="white" fill-opacity="0.92" stroke="#506882" stroke-width="0.5" stroke-opacity="0.3"/>
```
So the rule is correct for 4 of 5 direct-child-rect roles and wrong for the 5th, which is exactly the shape an attribute qualifier fixes.

### Finding 2: Bug #14 is a real escape — the chip has no class and no matching rule in any scope
**Evidence:** `plane2d.py:1843-1865` emits the pill unconditionally as `<rect ... fill="white" fill-opacity="0.85"/>` with no `class=`, and the label text via `_render_svg_text(..., fill=THEME["fg"], ...)` with no `css_class` kwarg. Live render:
```html
<rect x="253.0" y="298.0" width="41" height="20" rx="4" fill="white" fill-opacity="0.85"/>
<text x="274" y="308" fill="#11181c" style="text-anchor:middle;font-size:10px">m=d</text>
```
`scriba-plane2d.css` (47 lines, read in full) has exactly one text rule, `.scriba-plane-labels text { font-family: ...; user-select: none; pointer-events: none; }` — no `fill`, and no rule of any kind for a `rect`. `grep -n "data-theme\|prefers-color-scheme"` returns zero matches in this file.
**Detail:** Both elements sit outside every dark-mode mechanism this codebase has (no matching class, no matching attribute selector, no `var()` self-theming). In dark mode the chip stays a solid white-on-dark island, and its text stays near-black-on-near-black-background once composited — this is the more severe of the two chip states, not merely mistinted.

### Finding 3: most primitives don't need primitive-specific dark CSS at all — a universal safety net explains why
**Evidence:** `scriba-scene-primitives.css:203-268`: `.scriba-state-idle > rect:not(.scriba-graph-pill), .scriba-state-idle > circle { fill: var(--scriba-state-idle-fill); ... }` and `.scriba-state-idle > text:not(.scriba-graph-weight) { fill: var(--scriba-state-idle-text); }`, repeated for `current`/`done`/`dim`/etc. These selectors carry **no `[data-primitive=...]` scoping at all** — they match any `<g class="scriba-state-*">`'s direct-child rect/circle/text anywhere in the document. `base.py:1705-1707`: `state_class(target_state) -> f"scriba-state-{target_state}"` is the single shared helper every primitive uses to build this class name.
**Detail:** This is why Array, Grid, DPTable, Stack, Queue, HashMap, LinkedList, Matrix, Graph/Tree nodes, NumberLine, and — as Finding 5 shows — most of CodePanel never needed dedicated per-primitive dark CSS: as long as an element is a direct child of a `<g class="scriba-state-X">`, the universal rule overrides whatever light-mode literal Python baked into its `fill=`/`stroke=` attribute, regardless of that literal's value. The escape surface in this codebase is concentrated precisely in the elements that sit *outside* this net — decoration, chips, ticks, and chrome that aren't wrapped in a per-cell state group.

### Finding 4: the graph weight-pill dark fix is real, deliberate, and well-tested — but has one narrow escape of its own
**Evidence:** `scriba-scene-primitives.css:910-914`ff: `[data-theme="dark"] .scriba-graph-pill[fill="white"] { fill: var(--scriba-state-idle-fill); }` plus a sibling-selector rule for the weight text (`.scriba-graph-pill[fill="white"] ~ .scriba-graph-weight`) and both `@media` twins. `tests/unit/test_contrast.py:333-447` (`TestGraphPillDarkMode`) is an entire test class dedicated to this rule: `test_dark_pill_rule_is_default_scoped_not_blanket` explicitly asserts the rule must carry `[fill="white"]` and must **never** be a bare `.scriba-graph-pill` selector ("would clobber tinted fills"); `test_light_mode_pill_rules_dark_scoped_only` walks every `.scriba-graph-pill[` line in the CSS and asserts each is dark-gated. `graph.py:2426-2432` shows three branches: `tint_by_edge=True` → `_pill_tint_for_edge_state(state)`; `tint_by_source=True` → `_pill_tint_for_state(src_state)`; else → literal `pill_fill = "white"`. `test_graph_typography.py:93` confirms `assert 'fill="white"' in svg_default` for the default (no-flags) case.
**Detail:** `_pill_tint_for_edge_state` (`graph.py:255-257`) is `_PILL_TINT_BY_EDGE_STATE.get(state, "#ffffff")`, and the dict's own `"idle"` entry (`graph.py:~243`) is `"#ffffff"` — not the string `"white"`. CSS attribute selectors do exact string matching, not color-equivalence matching, so `[fill="white"]` does **not** match `fill="#ffffff"`. This means: with `tint_by_edge=True` and an idle (or any unrecognized) edge state, the weight pill renders `fill="#ffffff"` — visually white, but invisible to the existing dark-mode rule. This is a genuine, narrow escape inside an already-shipped, already-tested fix, gated behind an opt-in flag that has no test coverage for this interaction (`test_graph_typography.py` only exercises `tint_by_source`, not `tint_by_edge`).

### Finding 5: CodePanel's per-line content is covered by the universal net; only its chrome frame is escaped
**Evidence:** `codepanel.py:326-329` wraps each line in `<g data-target="..." class="{state_class(line_state)}">` — confirmed via Finding 3's mechanism, this covers the per-line background rect (332-337) and both the line-number and code `<text>` elements (342-372) regardless of the hardcoded `_LINE_NUM_COLOR`/`_CODE_TEXT_COLOR` fallback values used for the idle case, because the stylesheet rule overrides the presentation attribute either way. The header label (393-407) passes `css_class="scriba-primitive-label"`, matched by `scriba-scene-primitives.css:504-510` (`fill: var(--scriba-label-color)`, itself `var(--scriba-fg-muted)`, a base token redefined under both dark scopes at lines 750-753/819-822). But four elements sit structurally *outside* any state-class `<g>` and carry no class of their own: the panel background+border rect (285-289, `fill="{_PANEL_BG}" stroke="{_PANEL_BORDER}"`), the empty-panel "no code" text (292-300, `fill="{THEME['fg_dim']}"`), the header title-bar background path (380-386, `fill="{THEME['bg_alt']}"`), and the header/code divider line (388-391, `stroke="{_PANEL_BORDER}"`).
**Detail:** This corrects a broader initial hypothesis — CodePanel is not "entirely unthemed." The code text itself (the part users actually read) is safe. What's escaped is the panel's window frame: an always-present, classless, light-hex rounded rect sitting behind every line of code, plus the always-present-when-labeled title bar above it. In a dark-themed page this renders as a light rectangular "window" around otherwise-correctly-themed text — visually large and easy to notice, even though the underlying mechanism gap is narrower than it first appears.

### Finding 6: the group-label (`\group`/hull) pill has zero CSS coverage in any theme, and its text color is tuned only for a white background
**Evidence:** `graph.py:2075-2086`:
```python
self._pending_group_labels.append(
    f'<g class="scriba-group-label" data-annotation='
    f'"{_escape_xml(key)}-label">'
    f'<rect x="{prx:.1f}" y="{pry:.1f}" width="{pw}"'
    f' height="{ph}" rx="4" fill="white" fill-opacity="0.92"'
    f' stroke="{stroke}" stroke-width="0.5"'
    f' stroke-opacity="0.4"/>'
    f'<text x="{tx:.1f}" y="{pry + ph / 2.0:.1f}"'
    f' fill="{style["label_fill"]}"'
    ...
)
```
`style = ARROW_STYLES.get(color, ARROW_STYLES["info"])` (`graph.py:2004`). `grep -rn "scriba-group-label\|group-label"` across every shipped CSS file returns zero matches. `tests/unit/test_contrast.py:144-150`: "Annotation labels are rendered on a white pill background... `_PILL_BG = "#ffffff"`... treating as pure white for contrast calculation" — `ARROW_STYLES[...]["label_fill"]` values are only ever validated (`TestArrowStylesLabelContrast`) against a white background.
**Detail:** This is the same `.scriba-annotation`-pill *shape* as bug #9's pill sites, but the group-label group uses a different, unstyled class (`scriba-group-label`, not `scriba-annotation`), so it inherits none of the (correct, for pills) dark behavior those other four sites get. Even if it were wrapped in `.scriba-annotation` to pick up the fixed rule, the text color would still need attention: `label_fill` values are dark, saturated hexes chosen for ≥4.5:1 contrast against literal white, with no guarantee of adequate contrast against a dark chip.

### Finding 7: MetricPlot's tick labels and two of its three axis labels have no screen-mode dark coverage — only `@media print`
**Evidence:** `metricplot.py:521-526` (X ticks), `:540-545` (left-Y ticks), `:560-565` (right-Y ticks, two-axis mode) all emit `<text ...>{label}</text>` with **no `fill` attribute at all** (SVG initial value, "black"). `:570-580` (xlabel) and `:582-593` (ylabel, left) call `_render_svg_text(...)` with no `css_class`, defaulting to `fill="#11181c"`. `:594-607` (ylabel, right, two-axis mode) passes `css_class="scriba-metricplot-right-axis-label"`, but `scriba-metricplot.css` (29 lines, read in full) only sets that class's fill inside `@media print { ... fill: #000 !important; }` — no screen rule in either dark scope. The axis *lines* immediately adjacent to each of these (`:515-518`, `:534-538`, `:554-558`) are self-themed via the literal presentation-attribute value `stroke="var(--scriba-fg, #11181c)"`, so the lines are fine; only the text is escaped.
**Detail:** The self-theming `var()`-as-attribute-value pattern already exists and works for this exact primitive's lines — it was simply never extended to the tick/axis-label text.

## Theme-Attribute Audit Table (Structural Ask 1)

Status legend: **COVERED** = a dark-mode rule (class, attribute-scoped, universal state-class net, or `var()` self-theming) reaches it · **ESCAPED** = hardcoded light literal, zero dark-mode rule reaches it · **OVER-REACH** = an existing dark rule incorrectly also paints an element that should stay neutral · **NEUTRAL** = theme-agnostic by design (user data or intentional state-signal color).

| # | Emitter (file:line) | Element | Light attr as emitted | Dark rule (or lack of one) | Status |
|---|---|---|---|---|---|
| 1 | `base.py:779` | trace-label pill `<rect>` | `fill="white" fill-opacity="0.92"` | `scriba-scene-primitives.css:890/901` `.scriba-annotation > rect` | COVERED |
| 2 | `base.py:1577-1599` | block-bracket `<rect>` | `fill="none" stroke=ARROW_STYLES[...] stroke-dasharray="4,3"` | same unscoped rule as #1 wrongly matches | **OVER-REACH — Bug #9** |
| 3 | `base.py:1577-1599` | block-bracket stroke color | `stroke="#506882"` (etc., ARROW_STYLES, tuned for white bg) | no per-color-class rect-stroke rule exists (only `<path>`/`<line>` strokes are covered, css:566-567) | ESCAPED (minor/secondary — thin, 0.55-opacity dashed line) |
| 4 | `_svg_helpers.py:~2235` (`emit_plain_arrow_svg`) | annotation pill `<rect>` | `fill="white" fill-opacity="0.92"` | same rule as #1 | COVERED |
| 5 | `_svg_helpers.py:~3787` (`emit_position_label_svg`) | annotation pill `<rect>` | `fill="white"` | same rule as #1 | COVERED |
| 6 | `_frame_renderer.py:1701-1712` (note annotation) | pill `<rect>` | `fill="white" fill-opacity="0.92"` | same rule as #1 | COVERED |
| 7 | `plane2d.py:1843-1865` | line-label pill `<rect>` | `fill="white" fill-opacity="0.85"` | none — `scriba-plane2d.css` has no rect rule | **ESCAPED — Bug #14** |
| 8 | `plane2d.py:1843-1865` | line-label `<text>` | `fill="#11181c"` (THEME["fg"]), classless | none — `.scriba-plane-labels text` has no fill rule | **ESCAPED — Bug #14** |
| 9 | `plane2d.py:1827-1841` | point-label `<text>` | `fill="#11181c"` (THEME["fg"]), classless | none | ESCAPED (same file/mechanism as #14, outside ticket's repro) |
| 10 | `plane2d.py:1930-1935` (`_emit_tick_labels`, X) | tick `<text>` | `fill="#687076"` (THEME["fg_muted"]), classless | none | ESCAPED |
| 11 | `plane2d.py:1946-1952` (`_emit_tick_labels`, Y) | tick `<text>` | `fill="#687076"`, classless | none | ESCAPED |
| 12 | `scriba-plane2d.css` structural lines/points/polygons | `line`/`circle`/`polygon` | `stroke="var(--scriba-border)"` / `var(--scriba-fg)` | self-theming `var()` | COVERED |
| 13 | `graph.py:2432` (default, no tint flags) | weight pill `<rect>` | `fill="white"` | `.scriba-graph-pill[fill="white"]` (css:910+) | COVERED |
| 14 | `graph.py:2430` (`tint_by_source=True`) | weight pill `<rect>` | `fill="#eff6ff"` etc. (state tint) | none — deliberately excluded so the tint signal survives | NEUTRAL (by design) |
| 15 | `graph.py:2427`, state="idle"/unmapped, `tint_by_edge=True` | weight pill `<rect>` | `fill="#ffffff"` (dict default) | `[fill="white"]` does not string-match `"#ffffff"` | **ESCAPED (new — leak in an existing "fixed" rule)** |
| 16 | `graph.py:2427`, other mapped edge states, `tint_by_edge=True` | weight pill `<rect>` | `fill="#dbeafe"` etc. (edge-state tint) | none — deliberate, same reasoning as #14 | NEUTRAL (by design) |
| 17 | `graph.py:2078-2081` (`\group` hull label) | group-label pill `<rect>` | `fill="white" fill-opacity="0.92"`, class `scriba-group-label` | none — zero CSS for this class anywhere | **ESCAPED** |
| 18 | `graph.py:2082-2085` (`\group` hull label) | group-label `<text>` | `fill={ARROW_STYLES[color]["label_fill"]}`, classless | none | **ESCAPED** |
| 19 | Graph/Tree node `circle`+`text`, edge `line` | `[data-target]`-scoped | `var(--scriba-state-*)` | universal state-class net / `[data-target]` idle-fallback | COVERED |
| 20 | `metricplot.py:515-518,534-538,554-558` | axis tick `line` | `stroke="var(--scriba-fg, #11181c)"` | self-theming `var()` | COVERED |
| 21 | `metricplot.py:521-526` (X ticks) | tick `<text>` | no `fill` attr (SVG default black) | none on screen; `@media print` only | **ESCAPED** |
| 22 | `metricplot.py:540-545` (left-Y ticks) | tick `<text>` | no `fill` attr | none on screen | **ESCAPED** |
| 23 | `metricplot.py:560-565` (right-Y ticks) | tick `<text>` | no `fill` attr | none on screen | **ESCAPED** |
| 24 | `metricplot.py:570-580` (xlabel) | `<text>`/FO via `_render_svg_text` | `fill="#11181c"`, no `css_class` | none | **ESCAPED** |
| 25 | `metricplot.py:582-593` (ylabel, left) | same | `fill="#11181c"`, no `css_class` | none | **ESCAPED** |
| 26 | `metricplot.py:594-607` (ylabel, right) | same, `css_class="scriba-metricplot-right-axis-label"` | class exists | only inside `@media print` | **ESCAPED (screen)** |
| 27 | `metricplot.py:742` (series line) | `<line>`/`<path>` | `fill`/`stroke={s.color}` | none — user/author-chosen | NEUTRAL (by design) |
| 28 | `scriba-metricplot.css` gridlines/marker | `line` | `stroke="var(--scriba-border)"`/`var(--scriba-fg)` | self-theming `var()` | COVERED |
| 29 | `codepanel.py:285-289` | panel background+border `<rect>` | `fill="{_PANEL_BG}" stroke="{_PANEL_BORDER}"`, classless | none | **ESCAPED** |
| 30 | `codepanel.py:292-300` | empty "no code" `<text>` | `fill="{THEME['fg_dim']}"`, classless | none | ESCAPED (edge case — empty panel only) |
| 31 | `codepanel.py:326-337` | per-line background `<rect>` | class `scriba-state-{state}` on parent `<g>` | universal state-class net | COVERED |
| 32 | `codepanel.py:342-355` | line-number `<text>` | same wrapper | universal state-class net | COVERED |
| 33 | `codepanel.py:357-372` | code `<text>` | same wrapper | universal state-class net | COVERED |
| 34 | `codepanel.py:380-386` | header title-bar `<path>` | `fill="{THEME['bg_alt']}"`, classless | none | **ESCAPED** |
| 35 | `codepanel.py:388-391` | header/code divider `<line>` | `stroke="{_PANEL_BORDER}"`, classless | none | **ESCAPED** |
| 36 | `codepanel.py:393-407` | header label `<text>`/FO | `css_class="scriba-primitive-label"` | css:504-510, `var(--scriba-label-color)` | COVERED |
| 37 | `array.py:610`, `dptable.py:487`, `queue.py:474,938` | index labels | `css_class="scriba-index-label idx"` | css:418-425, `var(--scriba-cell-index-color)` | COVERED |
| 38 | `base.py:1233,1256,1282` | primitive captions | `css_class="scriba-primitive-label"` | css:504-510 | COVERED |
| 39 | `[data-primitive] text` universal (all primitives) | glyph halo `stroke` | n/a — halo, not fill | `stroke: var(--scriba-halo, var(--scriba-bg))` | COVERED (self-theming) |
| 40 | `scriba-embed.css` widget chrome | `.scriba-widget`, `.scriba-controls`, `.scriba-frame`, etc. | various | full `[data-theme="dark"]` + `@media` twin pair (lines 249-273+) | COVERED (separate UI-shell concern) |

**Summary:** 40 rows surveyed. 16 rows are newly-found ESCAPED sites beyond the two ticketed bugs (#3 minor/secondary, #9–11, #15, #17–18, #21–26, #29–30, #34–35 — 17 ESCAPED total including bug #14's own #7/#8, 16 of them not in either original ticket). 1 row is the confirmed OVER-REACH (#2, bug #9). 4 rows are intentional NEUTRAL design choices (#14, #16, #27, and implicitly the light-mode base of every COVERED row). The remaining 19 rows are correctly COVERED, including — importantly — the per-line content of CodePanel and the structural lines of Plane2D/MetricPlot, which are safe by the same universal mechanism (Finding 3) that a naive per-primitive grep would miss.

## Deduced Conclusions

### Deduction 1: the family has exactly two defect shapes, and both trace to the same cascade fact
**Based on:** Findings 1, 2, 4, 6, 7.
**Reasoning:** Every Python emitter bakes a light-mode hex or `"white"`/`"none"` literal into a presentation attribute as a browser-safe fallback for contexts with no stylesheet. CSS presentation attributes have specificity 0, so *any* matching stylesheet rule always wins. Direction A (over-reach, bug #9): a rule's selector is broader than the semantic role it's meant to cover, so it also flips an element that should stay neutral. Direction B (escape, bug #14 and 16 others): no selector reaches the element at all — either it's classless, or its class exists but only has a rule in one scope (e.g. `@media print`), or the value itself doesn't string-match an exact-attribute selector (Finding 4's `"#ffffff"` vs `"white"`).
**Conclusion:** Every fix in this family is a selector-scoping problem, not a color-computation problem — no new rendering logic is ever required, only a more precise (A) or more present (B) CSS selector.

### Deduction 2: the escape surface concentrates in decoration/chrome, not core cell rendering, because only decoration bypasses the universal state-class net
**Based on:** Finding 3, Finding 5, audit rows 19/31-33/37-39 vs. rows 7-11/15/17-18/21-26/29-30/34-35.
**Reasoning:** Any element that is a direct child of a `<g class="scriba-state-*">` is automatically protected, regardless of what literal Python wrote into its `fill=`/`stroke=` attribute, because the universal rule's specificity and cascade position guarantee it wins. Every confirmed escape in this audit sits *outside* that structure: annotation-adjacent pills/chips that use a different, unstyled class (`scriba-group-label`); axis/tick text that isn't wrapped in any per-state group at all; panel chrome that's structural, not per-cell.
**Conclusion:** A future primitive is safe by default for its core cell/node content as long as it reuses `state_class()` / the shared state-class convention. Risk is introduced specifically when a primitive adds a *new* decoration concept (a chip, a chrome frame, a tick label, a hull label) — exactly the pattern behind both ticketed bugs and all 16 additional findings.

### Deduction 3: this is a recurring, previously-hit class of bug, not a one-off — the codebase has fixed this exact shape three times before
**Based on:** `scriba-scene-primitives.css:411-417` ("Bug A" comment: "`.scriba-index-label` previously had zero CSS, so the index labels... fell through to the SVG defaults"), `:498-503` ("Bug B" comment, same shape for `.scriba-primitive-label`), and `test_contrast.py:259-266` (`TestForeignObjectInkTheming` docstring: "sweep3-runtime HIGH: KaTeX math values render inside foreignObject divs whose inline style bakes the LIGHT state ink... a dark-mode math value sat at 1.06:1 on the idle cell (invisible)"), plus `test_contrast.py:227-234` (`TestDarkScopeTokenParity` docstring: "sweep3-runtime: 6 `--scriba-annotation-state-*` inks were missing from the twin, leaving sub-AA light inks on dark pills").
**Reasoning:** Bug A and Bug B were geometry bugs (wrong baseline/anchor) from a class referenced by an emitter but never given a CSS rule — the same "class exists in Python, rule missing in CSS" shape as this investigation's color escapes, just a different CSS property. The two "sweep3-runtime" incidents are the *exact* same defect family as this investigation (light ink invisible/sub-AA on a dark surface), already found and fixed twice, with regression tests (`TestForeignObjectInkTheming`, `TestDarkScopeTokenParity`) written specifically to keep them from recurring — but scoped narrowly to FO-div ink and custom-property-token parity, not to raw presentation-attribute escapes on `<rect>`/`<text>` elements in general.
**Conclusion:** The project already has the right instinct (write a targeted regression test per incident) but no *general* guard. Recommend generalizing `TestGraphPillDarkMode`'s pattern (Finding 4) into a repo-wide test that walks every `css_class`/literal-class string referenced by a primitive emitter and asserts it has at least one dark-mode rule, so the next new chip/chrome/tick-label doesn't have to be caught by manual audit again.

### Deduction 4: the minimal fix for both ticketed bugs is already fully precedented and tested elsewhere in this same file
**Based on:** Finding 1, Finding 4, `test_contrast.py:368-381` (`test_dark_pill_rule_is_default_scoped_not_blanket`).
**Reasoning:** The reporter's suggested fix for bug #9 (`> rect[fill="white"]`) is not a new pattern — it is byte-for-byte the same shape as `.scriba-graph-pill[fill="white"]`, which has its own dedicated test asserting the selector must be attribute-scoped and must never be a "blanket" rule. All five direct-child rect sites under `.scriba-annotation` are literal `"white"` (4 sites) or literal `"none"` (the bracket) — no sixth variant exists — so the exact-match attribute selector is both sufficient and complete for this group.
**Conclusion:** Apply the identical, already-validated pattern rather than inventing a new mechanism. Bug #14 has no prior class to attach the pattern to (the chip is currently classless), so it additionally needs one new class name on each of the two elements — see Recommended Fix Sketch.

## Source Code Trace

| Element | Detail |
| ------- | ------ |
| Bug #9 rule origin | `scriba-scene-primitives.css:890` and `:901` (twin) — `[data-theme="dark"] .scriba-annotation > rect { fill: #1a1d1e; }`, no attribute qualifier |
| Bug #9 trigger | `base.py:1577-1599` — bracket `<rect fill="none" .../>` is a direct child of the same `.scriba-annotation`-classed `<g>` as the pill rects |
| Bug #9 precedent (already correct) | `scriba-scene-primitives.css:910-936` — `.scriba-graph-pill[fill="white"]`, tested by `test_contrast.py:333-447` |
| Bug #14 origin | `plane2d.py:1843-1865` — pill `<rect>` and label `<text>` both emitted with no `class=`/`css_class` |
| Bug #14 gap confirmation | `scriba-plane2d.css` (47 lines) — no `fill` rule for `.scriba-plane-labels text`, no rule at all for any `rect` |
| Governing mechanism (why the fix is CSS-only) | `_types.py:115-124` — `DARK_THEME` dict is imported (`base.py:41`) but never referenced anywhere; dark-mode is 100% CSS-driven |
| Related, previously-fixed sibling bugs | `scriba-scene-primitives.css:411-417`, `:498-503` ("Bug A"/"Bug B" comments — missing-CSS-for-referenced-class, geometry not color); `test_contrast.py:227-266` (sweep3-runtime — missing-CSS-for-referenced-class, color) |
| New leak found in an existing "fixed" rule | `graph.py:~243,255-257` — `_PILL_TINT_BY_EDGE_STATE["idle"] = "#ffffff"`, string-mismatched against `[fill="white"]` |

## Reproduction Plan

Both repros rendered via `uv run python render.py <input> -o <output> --no-minify` from the repo root (0.34.0 / 13eadc7). `render.py` refuses to write outside the working directory, so both `.tex` inputs were placed under the repo's own gitignored `.scriba_tmp/` before rendering.

**1. Bug #9** (`\annotate{...}{label="block", bracket=true}` on a Grid block):
```html
<g class="scriba-annotation scriba-annotation-info" data-annotation="g.block[0:1][0:1]-block-bracket">
<rect x="-3.0" y="-3.0" width="128.0" height="88.0" rx="6" ry="6" fill="none" stroke="#506882" stroke-width="1.5" stroke-opacity="0.55" stroke-dasharray="4,3"/>
```
Under `[data-theme="dark"]`, this rect's computed `fill` is `#1a1d1e` (the stylesheet rule), not the `none` written in the markup — confirmed by selector inspection, not just by reading the CSS text, since `.scriba-annotation > rect` has no qualifier that would exclude it.

**2. Bug #14** (`Plane2D` with one `lines=[{..., label="m=d"}]`):
```html
<rect x="253.0" y="298.0" width="41" height="20" rx="4" fill="white" fill-opacity="0.85"/>
<text x="274" y="308" fill="#11181c" style="text-anchor:middle;font-size:10px">m=d</text>
```
Neither element carries a `class` attribute, and `scriba-plane2d.css` has zero `data-theme`/`prefers-color-scheme` matches — confirmed no rule anywhere in the loaded stylesheet set can reach either element.

**3. Additional escape found in the same repro** — Plane2D's tick labels, present in the same render, not mentioned in the original ticket:
```html
<text x="32.00" y="326.00" text-anchor="middle" style="font-size:10px" fill="#687076">0</text>
<text x="74.67" y="326.00" text-anchor="middle" style="font-size:10px" fill="#687076">2</text>
```
(6 sibling tick labels total in this repro, all classless, all `fill="#687076"`.)

## Recommended Fix Sketch

**Fix A — Bug #9 (HIGH, minimal, precedent-exact):** Add an exact-match attribute qualifier to both scopes, mirroring `.scriba-graph-pill[fill="white"]`:
```css
/* scriba-scene-primitives.css:890 */
[data-theme="dark"] .scriba-annotation > rect[fill="white"] { fill: #1a1d1e; }

/* scriba-scene-primitives.css:901 (media twin) */
:root:not([data-theme="light"]) .scriba-annotation > rect[fill="white"] { fill: #1a1d1e; }
```
No Python change needed. Verified safe: all 4 legitimate pill sites (`base.py:779`, `_svg_helpers.py:~2235,~3787`, `_frame_renderer.py:1708`) use the literal string `"white"`; the bracket (`base.py:1577-1599`) uses the literal string `"none"`; no other direct-child-rect variant exists under `.scriba-annotation`.

**Fix B — Bug #14 (MED, new classes + first dark pair for this file):** In `plane2d.py:1843-1865`, add a class to each element:
```python
f'<rect class="scriba-plane-label-pill" x="{pill_rx:.1f}" y="{pill_ry:.1f}" ...'
```
and pass `css_class="scriba-plane-label-text"` into the `_render_svg_text(...)` call for the same label. Then add to `scriba-plane2d.css` (its first dark-mode rule pair):
```css
[data-theme="dark"] .scriba-plane-label-pill { fill: var(--scriba-bg-code); }
[data-theme="dark"] .scriba-plane-label-text { fill: var(--scriba-fg); }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .scriba-plane-label-pill { fill: var(--scriba-bg-code); }
  :root:not([data-theme="light"]) .scriba-plane-label-text { fill: var(--scriba-fg); }
}
```
`--scriba-bg-code`/`--scriba-fg` are defined at `:root`/`[data-theme="dark"]` scope in `scriba-scene-primitives.css` (lines 39-42, 750-753, 819-822) and are globally available since both stylesheets load on the same page — no need to re-hardcode `#1a1d1e`/`#ecedee` in the second file. Apply the identical class+rule shape to the point-label text (row 9) and both tick-label blocks (rows 10-11) while this file is open, since they're the same emitter and same gap.

**Fix C (follow-up) — graph.py tint_by_edge leak (row 15):** Change `_PILL_TINT_BY_EDGE_STATE`'s `"idle"` entry (and the `.get(state, "#ffffff")` default) from `"#ffffff"` to `"white"` — a value-only change, zero visual difference in light mode, but now string-matches the existing `[fill="white"]` rule. Add a `tint_by_edge=True` case to `test_graph_typography.py` mirroring `test_tint_by_source_changes_pill_fill`.

**Fix D (follow-up) — graph.py group-label (rows 17-18):** Either (i) reuse `.scriba-annotation`'s now-fixed rule by adding that class alongside `scriba-group-label`, or (ii) give it its own attribute-scoped pair like Fix A. For the text, re-use `STATE_COLORS["idle"]["text"]`-style var-driven color instead of the white-only-tuned `ARROW_STYLES[...]["label_fill"]`, or add a dedicated dark override and a new `test_contrast.py` contrast case against the dark chip.

**Fix E (follow-up) — MetricPlot ticks/labels (rows 21-26):** Simplest fix, consistent with the primitive's own existing pattern for lines: change the tick `<text>` and `_render_svg_text` calls to emit `fill="var(--scriba-fg, #11181c)"` directly (self-theming, no CSS file change) rather than omitting `fill` or defaulting to a literal hex. For `ylabel_right`, either extend `scriba-metricplot.css`'s existing `@media print` rule's class with a screen dark-mode pair, or switch it to the same self-theming `var()` value.

**Fix F (follow-up) — CodePanel chrome (rows 29-30, 34-35):** Add a class to the panel background rect and header bar/divider (e.g. `scriba-codepanel-chrome`), then a `[data-theme="dark"]`/`@media` pair setting `fill`/`stroke` to `var(--scriba-bg-code)`/`var(--scriba-border)` (dark tokens already defined, same as Fix B). This is the highest-visual-area escape found in this audit and is recommended as the next priority after Fix A/B.

## Risk Notes

- **Fix A scope check (bug #9):** confirmed exhaustively — only 5 direct-child rects exist under `.scriba-annotation` codebase-wide (4× `"white"`, 1× `"none"`); adding `[fill="white"]` changes behavior for exactly zero currently-correct sites and fixes exactly one currently-broken site.
- **Residual, lower-severity issue left by Fix A alone:** the bracket's *stroke* color (`ARROW_STYLES[...]["stroke"]`, row 3) is tuned for contrast against a white background and has no dark-mode override of its own (only `<path>`/`<line>` strokes get per-color-class treatment, not `<rect>` strokes). After Fix A, the bracket will correctly stay `fill="none"` in dark mode, but its dashed outline color is unverified for dark-background contrast. Not blocking — low severity (thin, 55%-opacity dashed line) — but worth a follow-up contrast check.
- **`scriba-plane2d.css` is currently dark-mode-virgin:** Fix B is the first `data-theme`/`prefers-color-scheme` rule ever added to this file. Confirm the build/bundling step that concatenates or references stylesheets loads `scriba-scene-primitives.css` (which defines the `--scriba-bg-code`/`--scriba-fg` custom properties) on every page that can render a `Plane2D` shape, or the `var()` references in Fix B will fall through to no value.
- **`TestDarkScopeTokenParity`-style risk:** any new class-based dark pair (Fix B, D, F) must add both the `[data-theme="dark"]` rule and its `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` twin — the existing token-parity test only checks `--scriba-*` custom property declarations, not arbitrary selector/rule pairs, so a missing twin for any of these fixes would not be caught by any existing automated test today.

## Affected Tests

- `tests/unit/test_contrast.py` — extend `TestGraphPillDarkMode`'s pattern (or add a sibling test class) to cover Fix A (`.scriba-annotation > rect[fill="white"]` must exist, and no bare `.scriba-annotation > rect` dark rule must exist) and Fix C (`tint_by_edge` idle case must string-match).
- `tests/unit/test_graph_typography.py` — add a `tint_by_edge=True` case alongside the existing `test_tint_by_source_changes_pill_fill`.
- Any golden/byte-identity SVG fixtures for `\annotate{bracket=true}`, Plane2D line labels, Graph `\group`, MetricPlot axis labels, and CodePanel will need re-blessing once these fixes add new `class=` attributes or change fill values — consistent with this codebase's own changelog convention of flagging cache/golden invalidation per CSS or markup byte change (`scriba/_version.py`).
- No test today asserts on dark-mode rendering for Plane2D, CodePanel, or the graph group-label at all — these three primitives currently have zero dark-mode-specific test coverage, which is consistent with the audit's finding that they carry the bulk of the escapes.

## Side Findings

- (Confirmed) The light-mode pill/bracket literal `fill="white"` (`#ffffff`) does not match the codebase's own "chip surface" token `--scriba-bg-code` (`#f8f9fa` light / `#1a1d1e` dark) — a minor, cosmetic-only inconsistency (both render as near-white in light mode) predating this investigation and out of scope for either ticket.
- (Confirmed) `_types.py:115-124`'s `DARK_THEME` dict is dead code — imported at `base.py:41` but never referenced. All dark-mode behavior in this codebase is CSS-side; nothing about the Python-emitted literals themselves needs to change for correctness, only their `class=`/selector reachability.
- (Confirmed) The `:not(.scriba-graph-weight)` exclusion inside every universal `.scriba-state-* > text` rule (Finding 3) is deliberate, not incidental — it exists specifically so the sibling-selector-based weight-text mechanism (Finding 4) can govern that one text role without fighting the universal rule for specificity. This is a third distinct dark-mode mechanism (alongside class-pairs and attribute-scoping) worth naming explicitly in any future refactor of this system.
- (Confirmed) `scriba-embed.css`'s widget-chrome dark pairs (controls, narration, frame header, step counter/dots) are fully and symmetrically implemented — this layer is not part of the escape surface and needed no further audit.

## Conclusion

**Confidence:** High

**Verdict — Bug #9: CONFIRMED.** `scriba-scene-primitives.css:890` (+ `:901` twin) is an unscoped `.scriba-annotation > rect` dark-mode rule that also matches the `bracket=true` outline rect (`base.py:1577-1599`), which is emitted `fill="none"` and should stay transparent. Live-render evidence matches the report exactly. Fix: add `[fill="white"]` to both rule scopes — the exact pattern already shipped and tested for `.scriba-graph-pill`.

**Verdict — Bug #14: CONFIRMED.** The Plane2D line-label pill (`plane2d.py:1843-1865`) and its text are emitted class-less with hardcoded light attributes; `scriba-plane2d.css` has zero dark-mode rules of any kind. Live-render evidence matches the report exactly, and the same file's point-label text and both axis tick-label blocks share the identical, unticketed defect.

**Structural audit:** 40 emission sites surveyed. 17 are ESCAPED (2 are bug #14 itself; 15 are new — Plane2D point-label/ticks, Graph's `tint_by_edge` idle leak and its `\group` hull-label pill+text, MetricPlot's tick/axis-label text, and CodePanel's panel/header chrome). 1 is the OVER-REACH already covered by bug #9. 4 are intentional NEUTRAL design choices. 19 (including CodePanel's per-line code/line-number text and every core cell/node primitive) are correctly COVERED via a universal, non-primitive-scoped state-class mechanism that a naive per-file audit would have missed. The codebase has hit this general defect shape — a class referenced by an emitter with no matching CSS rule — three times before (two geometry bugs tagged "Bug A"/"Bug B" in the CSS, one prior color/theme sweep tagged "sweep3-runtime" in the test suite), so this is a recurring architectural gap, not a pair of isolated incidents; a generalized regression test (per Deduction 3) is recommended alongside the fixes.
