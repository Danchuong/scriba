# Spec-Fix: JudgeZone #9 + #14 — Theme-Attribute Contract (structural)

**Agent:** fix-theme (BMAD patcher)
**Status:** DONE — all 6 fixes GREEN, full targeted suite green (709 passed, 0 failed), enforcement test permanent. No commit, no golden re-bless, no version bump, per scope.
**Investigation doc:** `_bmad-output/implementation-artifacts/investigations/judgezone-09-14-dark-theme-attrs-investigation.md`
**Bugs closed:** JudgeZone #9 (annotation-bracket over-reach), #14 (Plane2D line-label escape), plus 18 sibling ESCAPED sites from the same 40-row audit table (19 total FIXED_SITES rows).

## Contract

Quoted verbatim from `tests/unit/test_theme_attr_contract.py`'s module docstring — this is the structural deliverable, not just a bugfix:

> Every SVG element emitted with a hardcoded light-theme presentation
> attribute (`fill=`/`stroke=` as a literal XML attribute) must be either
>
> (a) matched by a dark-mode rule in BOTH scopes (`[data-theme="dark"]` and
> its `@media (prefers-color-scheme: dark)` twin), or
> (b) whitelisted as theme-neutral, with a comment explaining why.

SVG presentation attributes have CSS specificity 0, so any matching selector always overrides them — the two defect shapes this closes are **OVER-REACH** (a dark rule's selector is too broad and paints something it shouldn't — bug #9) and **ESCAPE** (no selector reaches the element at all — bug #14 and its 18 siblings).

## Enforcement tests (the permanent guardrail)

New file: `tests/unit/test_theme_attr_contract.py` (396 lines, all `@pytest.mark.unit`):

| Test class | Methods | What it checks |
|---|---|---|
| `TestThemeAttrContractFixedSites` | `test_site_marker_present_in_source`, `test_site_dark_rule_present_in_both_scopes`, `test_value_normalized_site_reuses_existing_dark_rule` | Parametrized over `FIXED_SITES` (19 rows): each site's emitter carries its new class/attr marker, and each `dark_rule`/`value_normalize` site's CSS selector is dual-scoped |
| `TestAnnotationRectOverReachFixed` | `test_bare_unscoped_annotation_rect_dark_rule_is_gone`, `test_attr_scoped_annotation_rect_dark_rule_present_both_scopes` | Bug #9 regression lock: asserts the old unscoped `.scriba-annotation > rect {` rule is gone and the `[fill="white"]`-scoped replacement is dual-scoped |
| `TestGraphTintByEdgeIdleColor` | `test_idle_tint_value_is_white_not_hex`, `test_pill_tint_for_edge_state_fallback_is_white_not_hex` | Fix C regression lock: idle-state tint literal is `"white"`, never `"#ffffff"` |
| `TestNoUnaccountedHardcodedWhiteFill` | `test_white_fill_literal_count_matches_baseline`, `test_hex_white_fill_literal_count_matches_baseline` | Mechanical scanner, parametrized over 8 emitter files: counts literal `fill="white"` / `fill="#ffffff"` occurrences against an explicit baseline (`_EXPECTED_WHITE_FILL_COUNTS` / `_EXPECTED_HEX_WHITE_FILL_COUNTS`) — **any future hardcoded white fill added to these files must be classified (dark rule or `NEUTRAL_SITES` whitelist) or this test fails** |

Plus one sibling test in the pre-existing `tests/unit/test_graph_typography.py`: `test_tint_by_edge_idle_pill_fill_is_white_not_hex`.

This is the structural piece: the table (`FIXED_SITES` + `NEUTRAL_SITES`) and the mechanical scanner generalize past today's known sites — a new hardcoded light-theme fill added to any of graph.py, plane2d.py, metricplot.py, codepanel.py, `_svg_helpers.py`, base.py, `_frame_renderer.py`, `_text_render.py` in the future must be accounted for or the count assertion breaks the build.

## Per-site fixes (A–F)

### Fix A — bug #9: annotation bracket rect over-reach

`scriba/animation/static/scriba-scene-primitives.css:890` and `:901`

Before: `[data-theme="dark"] .scriba-annotation > rect { ... }` (and its `@media` twin) — unscoped, so it painted every `<rect>` under `.scriba-annotation`, including the bracket's outline rect (`fill="none"`), which should never receive a dark fill.

After (both lines, both scopes):
```css
[data-theme="dark"] .scriba-annotation > rect[fill="white"] { fill: #1a1d1e; }
/* ...and the @media (prefers-color-scheme: dark) twin at line 901 */
```
Narrowed to the attribute-exact selector so only the pill backdrop (which genuinely carries `fill="white"`) is targeted. No Python change — CSS-only fix. Audit row 2.

### Fix B — bug #14 + 4 siblings: Plane2D label/tick chrome

`scriba/animation/primitives/plane2d.py` — `_emit_labels` (def at line 1816) and `_emit_tick_labels` (def at line 1911); new CSS in `scriba/animation/static/scriba-plane2d.css:55-61` (first-ever dark rules in this file — previously zero `[data-theme="dark"]`/`@media` coverage).

Emitter changes (all attribute-order-preserving — class added without moving any pre-existing attribute):
- Line 1834, 1859: point-label and line-label `<text>` gains `css_class="scriba-plane-label-text"`.
- Line 1851: line-label pill `<rect ...>` gains `class="scriba-plane-label-pill"` — appended at the end of the tag (after `fill-opacity="0.85"`, before `/>`) rather than after `<rect ` so the pre-existing `test_line_labels_no_overlap` regex (`r'<rect x="[^"]*" y="([^"]*)"'`, which requires `x=` immediately after `<rect `) keeps matching.
- Lines 1933, 1951 (both inside `_emit_tick_labels`): x-tick and y-tick `<text>` gain `class="scriba-plane-tick-label"`.

New CSS (both scopes):
```css
[data-theme="dark"] .scriba-plane-label-pill { fill: var(--scriba-bg-code, #1a1d1e); }
[data-theme="dark"] .scriba-plane-label-text { fill: var(--scriba-fg, #ecedee); }
[data-theme="dark"] .scriba-plane-tick-label { fill: var(--scriba-fg-muted, #9ba1a6); }
/* + the @media (prefers-color-scheme: dark) twin, identical selectors */
```
Audit rows 7, 8, 9, 10, 11.

### Fix C — graph `tint_by_edge` idle-state string-match leak

`scriba/animation/primitives/graph.py:243` (`_PILL_TINT_BY_EDGE_STATE["idle"]`) and `:257` (`_pill_tint_for_edge_state`'s fallback in `.get(state, "white")`).

Before: `"idle": "#ffffff"` — same color as the CSS's `.scriba-graph-pill[fill="white"]` rule, but attribute-selector matching is exact-string, so `#ffffff` never matched.

After: `"idle": "white"` — value-normalize only, no new CSS. Reuses the pre-existing dual-scoped `.scriba-graph-pill[fill="white"]` rule from `test_contrast.py::TestGraphPillDarkMode`. Audit row 15.

### Fix D — `\group` hull-label pill + text

`scriba/animation/primitives/graph.py` — `_emit_group_hulls` (def at line 1951); new class at line 2082 (`f'<text class="scriba-group-label-text"'`); new CSS in `scriba/animation/static/scriba-scene-primitives.css:944-948`.

The pill `<rect>` already carried the parent `scriba-group-label` class, so only the CSS selector was new (`.scriba-group-label > rect[fill="white"]`); the label `<text>` needed both a new class and new CSS since the existing `ARROW_STYLES` label-fill literals don't map onto the `--scriba-annotation-*` var() tokens for most states.

```css
[data-theme="dark"] .scriba-group-label > rect[fill="white"] { fill: var(--scriba-bg-code, #1a1d1e); }
[data-theme="dark"] .scriba-group-label-text { fill: var(--scriba-fg, #ecedee); }
/* + @media twin */
```
Audit rows 17, 18.

### Fix E — MetricPlot 6 tick/axis-label sites (self-theming var())

`scriba/animation/primitives/metricplot.py` — all inside `_emit_axes` (def at line 476): x-tick labels (line 525), left-y-tick (545), right-y-tick (566) get `fill="var(--scriba-fg-muted, #687076)"`; xlabel (576), left ylabel (588), right ylabel (602) get `fill="var(--scriba-fg, #11181c)"` as a `_render_svg_text()` kwarg.

Before: bare SVG default (no explicit `fill=` at all — inherits black text-color from the browser/renderer default, invisible against a dark background).

After: the `var()` reference is baked directly into the emitted attribute value, same pattern already used by this file's axis *lines* (`stroke="var(--scriba-fg, #11181c)"`, lines 493/499/507/518/538/559/724 — pre-existing, unchanged). No CSS file touched — the fix is entirely in the Python emitter; the fallback literal (`#687076` / `#11181c`) is what light mode renders when the custom property isn't defined. Audit rows 21–26.

**Regression risk flagged:** in **light mode**, MetricPlot's 3 tick-label sites shift from the SVG/browser default black to `#687076` (a muted gray) — this is an intentional, correct fix (previously invisible-in-dark-mode text now has an explicit, theme-aware color in both modes), but it is a visible pixel change in light-mode goldens too.

### Fix F — CodePanel 4 chrome sites

`scriba/animation/primitives/codepanel.py` — all inside `emit_svg` (def at line 254): panel bg/border `<rect>` (line 286) and header title-bar `<path>` (383) and header/divider `<line>` (392) all get `class="scriba-codepanel-chrome"`; the empty-panel "no code" `<text>` (294) gets its own `class="scriba-codepanel-empty-text"` since it's the fg-muted tone rather than the panel's bg/border tones.

New CSS in `scriba/animation/static/scriba-scene-primitives.css:955-965`:
```css
[data-theme="dark"] .scriba-codepanel-chrome {
  fill: var(--scriba-bg-code, #1a1d1e);
  stroke: var(--scriba-border, #313538);
}
[data-theme="dark"] .scriba-codepanel-empty-text { fill: var(--scriba-fg-muted, ...); }
/* + @media twin, identical selectors */
```
Audit rows 29, 30, 34, 35.

## Impact analysis (GitNexus `impact()`, direction=upstream, fresh run this session)

All 6 touched Python symbols, all **risk: LOW**, `epistemic: exact`:

| Symbol | File | Impacted count | Callers (depth 1) |
|---|---|---|---|
| `_pill_tint_for_edge_state` | graph.py | 1 | `Graph.emit_svg` |
| `_emit_group_hulls` | graph.py | 1 | `Graph.emit_svg` |
| `_emit_labels` | plane2d.py | 1 | `Plane2D.emit_svg` |
| `_emit_tick_labels` | plane2d.py | 2 | `Plane2D._emit_labels` (d1) → `Plane2D.emit_svg` (d2) |
| `_emit_axes` | metricplot.py | 1 | `MetricPlot.emit_svg` |
| `emit_svg` | codepanel.py | 0 | none in the static call graph (top of its own chain — invoked polymorphically by the frame renderer, not captured as a direct static call) |

No HIGH/CRITICAL risk anywhere — all 6 edits are leaf-level emitter changes (attribute/class additions or value swaps) with a single-level call chain up to each primitive's own `emit_svg`. Nothing downstream of `emit_svg` is affected because none of these edits change function signatures, return types, or control flow — only literal string content inside already-returned SVG strings.

## Repro: before/after evidence

Verified via real renders of the scratchpad repro files (`bug09_bracket.tex`, `bug14_plane2d.tex`), using an isolated `git worktree add --detach <path> HEAD` for the pre-fix baseline (chosen over `git stash` specifically because the shared working tree has other agents' concurrent uncommitted work — the worktree never touches the main tree, so it's safe to use alongside them; removed cleanly afterward).

**bug09_bracket** (BEFORE → AFTER): the annotation `<rect fill="white" fill-opacity="0.92" stroke="#506882" stroke-width="0.5" stroke-opacity="0.3"/>` is byte-identical before/after (confirms Fix A is CSS-only, no emitter change for this bug). The CSS diff shows the selector narrowing exactly as Fix A specifies, plus the bundled Fix D/F CSS blocks appearing (global stylesheet, not this repro's target, but present in the bundle regardless).

**bug14_plane2d** (BEFORE → AFTER): every tick `<text>` gains `class="scriba-plane-tick-label"`; the pill `<rect>` gains `class="scriba-plane-label-pill"` at the end of the tag; the label `<text>` gains `class="scriba-plane-label-text"`. Every pre-existing attribute value (fill, x, y, stroke, coordinates, text-anchor, style) is byte-identical before/after — confirms Fix B only adds classes, changes no visual output in light mode.

Both diffs contain one unrelated line, `<title>t</title>` removal — this belongs to a sibling agent's concurrent JudgeZone #10 fix (accessible-name policy, `_frame_renderer.py`'s `<title>` region, explicitly fenced from this patch) and is correctly **not** part of this patch's diff.

## Audit-table reconciliation

The investigation doc's 40-row audit table is the ground truth. Direct enumeration of that table yields **19 rows marked ESCAPED** (rows 3, 7, 8, 9, 10, 11, 15, 17, 18, 21, 22, 23, 24, 25, 26, 29, 30, 34, 35) plus 1 row marked OVER-REACH (row 2, bug #9).

`FIXED_SITES` in the enforcement test has exactly 19 entries = row 2 (OVER-REACH) + 18 of the 19 ESCAPED rows. **Row 3** (the bracket annotation's *stroke* color, in `base.py`) is the one ESCAPED row deliberately **not** fixed — it's out of scope per team-lead's work-item list (#9 + 15 named siblings only), and it lives in `base.py`, a fenced file. It is explicitly whitelisted in `NEUTRAL_SITES` with that reasoning, not silently dropped.

**Flagging a discrepancy in the (separate, already-concluded) investigation doc's own prose**, for transparency: its summary line and conclusion paragraph state "17"/"16"/"15" ESCAPED sites in different places, but a direct count of its own 40-row table gives 19. This is that source document's own internal arithmetic inconsistency — not introduced by this patch, and not mine to silently edit (it's a different, already-concluded artifact). This spec's reconciliation above uses the directly-counted, verifiable number (19) as ground truth.

The other 21 rows of the 40-row table are COVERED (already dark-scoped, most via the universal `.scriba-state-*` net that automatically protects any element that is a direct child of a state-class `<g>` regardless of its own literal `fill=`/`stroke=`) or NEUTRAL (intentional per-state color tints, user-supplied data colors) — no action needed.

## Goldens expected to shift

Not re-blessed (out of scope), but flagged for whoever owns that step:

- **MetricPlot** (Fix E): light-mode goldens for any example with tick/axis labels will shift — 3 tick-label sites move from browser-default black to explicit `#687076`. This is intentional and correct, not a side effect to suppress.
- **Plane2D** (Fix B): no pixel shift in light mode (class-only addition, verified byte-identical attribute values above) — goldens should NOT need re-blessing unless a golden literally asserts on absence of a `class=` attribute.
- **Graph `\group`** (Fix D), **CodePanel** (Fix F): same as Plane2D — class-only additions, no light-mode pixel shift expected.
- **Annotation bracket** (Fix A): CSS-only, no SVG output change at all — no golden shift possible from this fix.
- Dark-mode-rendered goldens (if any exist) for Plane2D, Graph `\group`, MetricPlot, and CodePanel will change by design — these primitives had zero dark-mode-specific test coverage before this patch, per the investigation doc's own "Affected Tests" finding.

## Regression risks

1. MetricPlot's light-mode tick/axis-label color shift (Fix E) — intentional, flagged above, will fail any golden that pixel-diffs those labels.
2. The investigation doc's own ESCAPED-count inconsistency (documented above transparently, not corrected in place — it's a different artifact).
3. No other behavioral change: Fixes A, C, D, F are class/value additions that don't alter light-mode pixels (verified via before/after render diffs); Fix B is class-only (same verification).

## Handoffs

None required. All 6 fixes stayed within owned scope (`scriba-scene-primitives.css`, `scriba-plane2d.css`, `plane2d.py`, `graph.py`, `metricplot.py`, `codepanel.py`, plus test files). The only fenced-file-adjacent finding — row 3's bracket stroke color in `base.py` — needed no edit at all; it's correctly whitelisted as deliberately out-of-scope, not a deferred fix. `_svg_helpers.py`'s three `fill="white"` occurrences (rows 4, 5, and a private-helper detail of row 4) and `_frame_renderer.py`'s one occurrence (row 6) required no code edit either — both already COVERED by Fix A's CSS scoping; the only work there was accurate baseline accounting inside this patch's own test file.

## Verification

- Regression found and fixed during this work: an earlier Fix B edit broke `test_primitive_plane2d.py::TestLineLabelCollision::test_line_labels_no_overlap` by inserting the new `class=` attribute before `x=` on the pill `<rect>`, which broke that test's brittle regex. Fixed by moving `class=` to the end of the tag (SVG attribute order is not semantically meaningful) rather than editing the test.
- Final full targeted-suite run (all graph/plane2d/metricplot/codepanel test files + `test_contrast.py` + the new/changed theme files): **709 passed, 0 failed**, 9 pre-existing warnings (all unrelated `UserWarning`s from oversized-radius/log-scale/polygon-auto-close fixtures, not from this patch).
- No full suite run, no golden-example run, per explicit scope instruction.
- No commit made. No version bump. No `CHANGELOG` entry.

## Sweep wave (wave 2)

**Agent:** sweep-theme
**Status:** DONE — all 4 targets swept, 2 new escapes found and fixed, 2 targets confirmed clean (no action needed), enforcement extended by 2 new test classes + 1 regression test. 352 passed, 1 pre-existing unrelated warning, 0 failed on the full touched-area rerun. No commit, no golden re-bless, no version bump, per scope.

Wave 1 fixed the 19 audit-table sites plus the mechanical white-fill scanner. This wave's brief: hunt residual escapes wave 1's audit table didn't cover — different channels (white halo strokes, tex-emitted HTML/CSS, other CSS bundle files, inline `style=` attributes) rather than more rows of the same table.

### Target (a) — animation `stroke="white"` halo strokes

Complete and verified **before** this wave-2 session's visible portion began (163/163 green). No further changes this session. See the git history for `_svg_helpers.py`, `_frame_renderer.py`, `scriba-scene-primitives.css`, and the white-stroke scanner additions to `test_theme_attr_contract.py`.

### Target (b) — tex emitters + tex CSS

Two independent findings, both fixed and verified.

**(b1) CSS structural gap — `@media` twin missing entirely.** `scriba/tex/static/scriba-tex-content.css` and `scriba/tex/static/scriba-tex-pygments-dark.css` were entirely `[data-theme="dark"]`-guarded with **zero** `@media (prefers-color-scheme: dark)` twin — the same defect class as the pre-existing "H6 fix" in `scriba-embed.css`, just never applied to the tex CSS files. A host page that renders via `TexRenderer.assets()` directly (not through `render.py`'s own `HTML_TEMPLATE`, which hardcodes `data-theme="light"`) and never sets `data-theme` would silently ignore OS dark preference. Fixed by duplicating every rule 1:1 under `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) ... }`, mirroring `scriba-embed.css`'s own H6 block verbatim in structure. `.katex-error` (`scriba-tex-content.css:178-183`) was already `var(--scriba-error)`-driven and needed no change — checked, not touched.

**(b2) KaTeX's own inline color fallback — literal hex in a class-less `style=` attribute.** KaTeX emits `<span style="color:#cc0000">` as its built-in fallback for an unrecognized-but-not-fully-invalid command, when `trust=false, strict=false` — which is scriba's actual default (`strict_math: bool = False`, `scriba/tex/renderer.py:216`), so this is the default lenient-math-error path, not an opt-in edge case. This is distinct from the `.katex-error` class-based `ParseError` path (already correct, see b1) — this fallback carries no class at all, so no CSS selector can reach it. Contrast check: `#cc0000` on `--scriba-bg-code` (`#1a1d1e`) is **2.88:1**, below WCAG AA's 4.5:1 minimum for normal text; on the light background it's 5.89:1 (passes). Considered and rejected a CSS attribute-substring-selector fix (`[style*="color:#cc0000"] { ... !important }`) — zero precedent for that pattern anywhere in the codebase, and fragile to KaTeX output-formatting drift. Fixed instead with the `var()` self-theming pattern (this task's third sanctioned pattern): `scriba/tex/renderer.py` gained `_KATEX_COLOR_FALLBACK_SUB_RE` and `_theme_katex_color_fallback()` (defined just after the pre-existing `_KATEX_COLOR_FALLBACK_RE`, ~line 70), called from `_render_source` immediately after the existing `_scan_katex_errors(text, ctx)` line (~line 667), so the E1200 warning scan sees the untouched original text first. Swaps the literal for `var(--scriba-error)` — the same token `.katex-error` already uses, so both error-rendering paths now share one color source.

GitNexus impact (`mcp__gitnexus__impact`, target `_render_source`, direction upstream, `repo="scriba"`, `file_path="scriba/tex/renderer.py"`): **risk LOW**, impactedCount 3, direct 1, processes_affected 0, modules_affected 2 (Unit, Tex). Cleared before editing; no HIGH/CRITICAL risk to flag.

New test: `tests/tex/test_tex_renderer_coverage.py::test_katex_unknown_command_fallback_uses_themed_color` — renders `r"$\thisisnotarealcommand$"` through a real `TexRenderer`/`Pipeline`, asserts `"color:#cc0000"` is absent and `"color:var(--scriba-error)"` is present.

### Target (c) — `scriba-embed.css` / `scriba-standalone.css` / `scriba-animation.css` / `scriba-metricplot.css`

One new escape found and fixed; the other three files checked clean.

**`scriba-standalone.css` — same `@media`-twin gap as (b1).** Two `[data-theme="dark"]` rules (`body`, `.theme-toggle`) with zero `@media` twin. This file styles only `render.py`'s own standalone `HTML_TEMPLATE`, which hardcodes `data-theme="light"` on `<html>` — so the gap is inert for that one template today. Fixed anyway: `load_css()` is a generic asset loader with nothing restricting this file to that template, the fix is two trivial rule duplications with zero risk of regressing the reachable path, and leaving a known instance of the same bug class undocumented-and-unfixed one file over from where it was just fixed elsewhere would be an inconsistent result for this sweep to hand off. Fixed by adding the `@media` twin, same H6 structure.

**`scriba-embed.css`** — re-verified the pre-existing H6 fix is complete: 12 `[data-theme="dark"]` rules, 12 twin rules, 1:1 selector match. No gap. No change.

**`scriba-animation.css`** and **`scriba-metricplot.css`** — both clean, both theme-neutral by construction rather than by omission: every color is a `var(--scriba-state-*|--scriba-border|--scriba-fg, <fallback-hex>)` reference into tokens that are themselves already fully dual-scoped in `scriba-scene-primitives.css` (verified: `--scriba-state-highlight-fill`, `--scriba-border`, `--scriba-fg` all present in both the `[data-theme="dark"]` block and its `@media` twin, lines ~748-839). The literal hex after the comma is a CSS `var()` fallback for the pathological case this CSS file is loaded without `scriba-scene-primitives.css` — not a hardcoded escape. `scriba-metricplot.css`'s `@media print` block (lines 14-28) hardcodes `#000`/`#ccc` regardless of theme — already self-documented in-file (line 19-20: "In dark-mode + print-color-adjust:exact, var(--scriba-fg) resolves to near-white... producing invisible axes... Force print-safe dark") — a textbook instance of the contract's own carve-out (b), already correctly whitelisted by comment before this sweep ever started. No change needed to either file.

### Target (d) — inline `style="...color/background..."` in Python emitters

No new escapes beyond (b2) above, which already covers the one real hit (KaTeX's inline `style="color:#cc0000"` fallback — a tex-emitter finding that is simultaneously a target-(b) and target-(d) site; documented once, under (b), to avoid double-counting).

Ruled out, no fix needed:
- **`scriba/tex/parser/images.py`**'s `apply_includegraphics` `style_attr` (lines 103-105) — can only ever contain `scale`/`scale_origin`/`width`/`height` (pure sizing, confirmed by reading `_parse_options`, lines ~60-76). No color capability exists in this code path at all.
- **`svg_style_attrs(state_name)` / `STATE_COLORS`** (`scriba/animation/primitives/_types.py:80-97`) — initially the largest open question (shared helper, ~16 primitive consumers: queue, grid, tree, plane2d, linkedlist, graph, stack, tracetable, variablewatch, codepanel, hashmap, forest, dptable, array, numberline, hypercube). Ruled out after tracing the full mechanism: the module's own comment documents these hex values as "the inline fallback when CSS custom properties are not yet applied (test snapshots, raw emitter output, non-browser consumers)... must stay in lockstep with `scriba-scene-primitives.css` :root" — i.e., intentional, documented fallback layering. Confirmed every real consumer pairs the fill/stroke/text output with a `scriba-state-{name}` class on the wrapping element (via the shared `state_class()` helper in `base.py:1734`, or — in `plane2d.py`'s case, the one consumer that doesn't call `state_class()` — direct f-string interpolation of the identical `scriba-state-{state}` class name), and `.scriba-state-{name} > rect/circle/line/text` selectors in `scriba-scene-primitives.css` (lines 203+) already override every inline value via `var(--scriba-state-*)`, with that variable system fully dual-scoped (confirmed above, target c). This is pre-existing, correct, load-bearing infrastructure — the exemplar the wave-1 fix pattern was modeled after, not an escape.
- Broad regex sweep, `grep -rnE 'style=.*(color|background|fill)\s*:' scriba/animation scriba/tex --include="*.py"` (excluding test files) — one hit, and it's the comment documenting the (b2) fix itself. No other `style=` construction in either emitter tree carries a color/background/fill declaration; the remaining `style=` sites found in the broader unfiltered grep are typography/layout only (`font-size`, `text-anchor`, `dominant-baseline`, `font-weight`, `overflow`, `text-overflow`).

### Enforcement / scanner extensions

| Addition | Location | What it checks |
|---|---|---|
| `TestTexCssDarkTwinParity` | `tests/unit/test_theme_attr_contract.py:527-550` | Parametrized over the 3 tex CSS files; asserts `[data-theme="dark"]` selector-prefix count == `@media` twin count per file (regression lock for b1) |
| `TestAnimationStaticCssDarkTwinParity` | `tests/unit/test_theme_attr_contract.py` (new, appended after the above) | Same assertion, parametrized over all 4 target-(c) files (`scriba-embed.css`, `scriba-standalone.css`, `scriba-animation.css`, `scriba-metricplot.css`). 0==0 passes for the two files with no dark rules at all — this doubles as a forward-looking regression guard: any future dark-scoped rule added to either file without its `@media` twin now fails immediately |
| `test_katex_unknown_command_fallback_uses_themed_color` | `tests/tex/test_tex_renderer_coverage.py` | Regression lock for b2: real render of an unknown KaTeX command must not contain `color:#cc0000` and must contain `color:var(--scriba-error)` |

No `NEUTRAL_SITES` additions this wave — every finding either got a structural CSS/Python fix, or was already correctly self-documented as theme-neutral before this sweep started (`scriba-metricplot.css`'s `@media print` block).

### Goldens expected to shift

Confirmed empirically, not just inferred: `uv run pytest tests/golden/examples/test_example_html.py -q --no-header --tb=no -p no:cacheprovider` → **107 failed, 1 passed** (the 1 pass is the non-parametrized `test_corpus_is_non_empty` guard; all 107 corpus golden pairs byte-differ).

Root cause: `scriba-scene-primitives.css` (target a's file) sits in `render.py`'s unconditional `_BASE_CSS` bundle, which is inlined into every page's `<style>` block — so target (a)'s own additions already guaranteed universal shift regardless of anything done this wave; target (b)/(c)'s CSS growth (tex CSS `@media` twins, `scriba-standalone.css`'s new block) compounds the same shift for pages that include those bundles. This was **not** re-blessed (`SCRIBA_UPDATE_GOLDEN=1`, explicitly out of scope) — flagged here for whoever owns that step, matching wave 1's own precedent of documenting-not-fixing goldens (its MetricPlot light-mode tick-label shift, Fix E above).

Scope of the shift is bounded and confirmed, not assumed: `tests/golden/animation/*.html` (consumed by `tests/integration/test_animation_transitions.py`) and `tests/golden/smart_label/*` (consumed by `tests/golden/smart_label/test_corpus.py`) do **not** embed the CSS bundle at all (`grep` for `<style>`/CSS filenames returns zero hits in both directories) — these are fragment-level snapshots, unaffected by any CSS-bundle change from any wave.

### Verification

`uv run pytest tests/tex/ tests/core/test_pipeline.py tests/unit/test_theme_attr_contract.py tests/unit/test_contrast.py tests/unit/test_css_bundler_cache.py tests/unit/test_css_font_sync.py -q -p no:cacheprovider` → **352 passed, 1 warning** (the warning is `test_pipeline_close_idempotent_even_if_renderer_raised`'s pre-existing, intentional `RuntimeWarning` from a fixture that deliberately raises — unrelated to this wave).

No commit made. No version bump. No `CHANGELOG` entry.
