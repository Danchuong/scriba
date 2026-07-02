# Sweep: CSS ↔ DOM contract

Scope: every shippable CSS sheet vs every class/token the Python + JS emitters
produce, both directions. Entry point audited is `render.py` (the sole HTML
producer — see Bundle matrix). Read-only investigation; nothing in the repo was
modified. Top findings browser-verified with headless Chromium.

Probes rendered into scratchpad with `.venv/bin/python render.py`:
`mp_probe.tex` (examples/primitives/metricplot.tex), `p2d_probe.tex`
(examples/primitives/plane2d.tex), `number_spiral.tex`.

---

## Bundle matrix (which CSS ships in which output mode)

`render.py` builds the `<style>` blob by hand — it does **not** use
`core/pipeline.py` (no production code instantiates `Pipeline(`; there is no
`__main__`/console-script). The principled asset collector in
`pipeline.py:291-321` (which unions `renderer.assets()` + `artifact.css_assets`)
is therefore **dead in shipping** — only exercised by tests.

`load_css` (`scriba/core/css_bundler.py:19-38`) routes `scriba-tex*` → `tex/static`, everything else → `animation/static`.

| CSS sheet | Interactive (default) | `--static` filmstrip | `--no-inline-runtime` | Bundled by |
|---|:--:|:--:|:--:|---|
| scriba-scene-primitives.css | ✅ always | ✅ | ✅ | `render.py:249-254` (hardcoded) |
| scriba-animation.css | ✅ always | ✅ | ✅ | `render.py:249-254` |
| scriba-embed.css | ✅ always | ✅ | ✅ | `render.py:249-254` |
| scriba-standalone.css | ✅ always | ✅ | ✅ | `render.py:249-254` |
| scriba-tex-content.css | ⬜ only if TeX gap | ⬜ | ⬜ | `render.py:259-260` via `_wrap_tex` css_assets (`render.py:202-204`) |
| scriba-tex-pygments-light.css | ⬜ only if TeX gap | ⬜ | ⬜ | same (artifact `css_assets`) |
| scriba-tex-pygments-dark.css | ⬜ only if TeX gap | ⬜ | ⬜ | same |
| katex.min.css (fonts inlined) | ⬜ only if math | ⬜ | ⬜ | `render.py:278-280` (`inline_katex_css`) |
| **scriba-metricplot.css** | ❌ **NEVER** | ❌ | ❌ | — not in `css_parts`; artifact `css_assets` ignored |
| **scriba-plane2d.css** | ❌ **NEVER** | ❌ | ❌ | — same |

Root cause of the two ❌ rows: `render.py`'s block loop (`render.py:206-236`)
collects `artifact.css_assets` **only** for TeX gaps (`_wrap_tex`). For
animation/diagram artifacts it appends `artifact.html` and throws the
artifact's `css_assets` away — even though `AnimationRenderer.render_block`
correctly declares `scriba-plane2d.css` / `scriba-metricplot.css` when those
primitives are present (`scriba/animation/renderer.py:517-534`), and
`AnimationRenderer.assets()` lists all four (`renderer.py:540-556`). Those
declarations only feed `Pipeline`, which nothing ships through.

Inline `<style>` rescue? None for primitives. The only emitted `<style>` is the
`@keyframes` block from `keyframes.py:83` (itself unwired — see F3). Pygments
spans are produced by `HtmlFormatter(classprefix="tok-")`
(`scriba/tex/highlight.py:132`) wrapped in `.highlight`, so the pygments sheets'
`.scriba-tex-content .highlight .tok-*` selectors do match.

---

## Findings

### F1 — HIGH · Confirmed (browser-verified): metricplot gridlines are invisible
- **css side**: `scriba/animation/static/scriba-metricplot.css:2-7`
  `.scriba-metricplot-gridline-h, .scriba-metricplot-gridline-v { stroke: var(--scriba-border,#d0d7de); stroke-width:.5; opacity:.6 }` — sheet **never bundled by render.py** (Bundle matrix).
- **dom side**: `scriba/animation/primitives/metricplot.py:447-461` emits
  `<line class="scriba-metricplot-gridline-h" x1=… y1=… x2=… y2=…/>` with **no inline `stroke`** (unlike the axes/ticks/marker lines at 483-499 / 508-510 / 707-712, which all carry `stroke="var(--scriba-fg,#11181c)"`).
- **browser**: in `mp_probe.html`, 22 gridline elements, computed `stroke = none` (SVG default) → they do not paint. For contrast, `.scriba-metricplot-marker` computes `rgb(17,24,28)` (inline) and `.scriba-metricplot-legend-label` computes fill `rgb(17,24,28)` (styled by shipped scene-primitives). Decisive bundle check: the gridline rule body `stroke: var(--scriba-border, #d0d7de)` appears **0** times in the output.
- **user-visible effect**: every metricplot renders with **no grid** — exactly today's family (CSS that can never match the emitted DOM, unbundled). Print overrides (`.scriba-metricplot-line/-legend-label/-right-axis-label` in the `@media print` block, lines 14-29) are also lost, a secondary print-fidelity regression.

### F2 — LOW/MED · Confirmed (browser-verified): plane2d axis labels lose their monospace font
- **css side**: `scriba/animation/static/scriba-plane2d.css:43-47`
  `.scriba-plane-labels text { font-family: var(--scriba-font-mono, ui-monospace, monospace); user-select:none; pointer-events:none }` — sheet never bundled.
- **dom side**: `scriba/animation/primitives/plane2d.py:984` emits `<g class="scriba-plane-labels">…<text>`.
- **browser**: in `p2d_probe.html`, `.scriba-plane-labels text` computes
  `font-family: -apple-system, "system-ui", …, sans-serif` (the body default) — **not monospace**.
- **why the rest of plane2d.css doesn't matter**: grid/axes lines carry inline
  `stroke="{THEME[...]}"` (`plane2d.py:742,752,806,824`) → verified visible
  (`rgb(223,227,230)`); and `.scriba-plane-point circle` transitions are supplied
  by shipped scene-primitives (verified computed `transition: fill 0.18s …`, i.e.
  180 ms, not plane2d.css's 150 ms). So plane2d.css is ~90% redundant; the label
  font is the one genuine loss. Also `--scriba-font-mono` is read-but-never-defined
  (falls back to `ui-monospace` — but moot, sheet unshipped).
- **user-visible effect**: plane coordinate labels render in the prose sans-serif instead of mono. Cosmetic but wrong.

### F3 — LOW · Confirmed: dead `.scriba-anim-*` rules + read-but-undefined `--scriba-anim-name`
- **css side (shipped)**: `scriba/animation/static/scriba-animation.css:17-21`
  (`.scriba-anim-rotate/-pulse/-orbit/-fade-loop/-trail`) and the matching
  reduced-motion block `:57-70`, all reading `var(--scriba-anim-name)`.
- **dom side**: **no emitter**. The only code that would apply these classes is
  the `keyframes` extension, which has **no production caller** — referenced only
  by `scriba/animation/extensions/__init__.py` (re-export) and
  `tests/unit/test_keyframes.py`. And even it never sets an inline
  `--scriba-anim-name`: `get_animation_class` returns the class name only
  (`keyframes.py:92`), while the scoped `@keyframes` name is `"{scene_id}-{preset}"`
  (`keyframes.py:77`). So the property is never defined and the rules never attach.
- **effect**: dead rules; `--scriba-anim-name` is a read-with-no-definition that only
  feeds this dead feature. (My mechanical scan under-reported these because the same
  rule text also lives as a string literal inside `keyframes.py` `UTILITY_CSS`.)

### F4 — LOW · Confirmed: dead `.scriba-substory-frame` / `.scriba-substory-frames`
- **css side (shipped)**: `scriba/animation/static/scriba-animation.css:33` (`.scriba-substory-frames`) and `:44` (`.scriba-substory-frame`).
- **dom side**: `grep "substory-frame"` across `scriba/` + `examples/` (py+js) = **0** emitters. The live substory uses `.scriba-substory-container` (`_html_stitcher.py:703`) and `.scriba-substory-widget` (`_html_stitcher.py:429`).
- **effect**: stale legacy selectors, no match.

### F5 — LOW · Confirmed: dead `.katex-fallback`
- **css side (shipped-with-TeX)**: `scriba/tex/static/scriba-tex-content.css:197` `.scriba-tex-content .katex-fallback { … }`.
- **dom side**: no emitter anywhere in `scriba/`. KaTeX render failures surface as `<span class="katex-error">` (handled at `scriba/tex/renderer.py:56-74`), never `katex-fallback`.
- **effect**: stale selector; a real KaTeX error is actually styled only by KaTeX's inline color, not by this sheet.

### Non-findings deliberately checked (emitted classes with no rule → all benign)
`scriba-metricplot-{grid,axes,series,xticks,yticks,legend,step-marker,…}` and
`scriba-plane-content` are bare `<g>` grouping wrappers (no styling needed).
`scriba-annot-label` carries an inline `style="…color:…"` (`_svg_helpers.py:1552`),
`scriba-ll-arrowhead` carries inline `fill=` (`linkedlist.py:284`),
`scriba-substory-widget` is a JS querySelector hook (`scriba.js:75`,
`_script_builder.py:133/329`), `scriba-tex-size-*` is matched by prefix in
tex-content.css. None are missing styling.

---

## Dead tokens (custom properties: defined in a shipped `:root`, 0 `var()` reads repo-wide)

Confirmed by grepping `var(--<name>` across the whole tree — 0 reads each. No
user-visible effect; they bloat the sheet and mislead maintainers. Several are
values that are **hardcoded elsewhere instead of read through the token**, others
are knobs for features that were never wired.

**scriba-scene-primitives.css**
- `--scriba-stage-padding` (`:54`) — the known suspect. Confirmed dead; `.scriba-stage` padding is hardcoded `0.875rem` in `scriba-embed.css:106`.
- `--scriba-cell-size` (`:68`), `--scriba-node-r` (`:72`), `--scriba-tick-length` (`:76`) — geometry applied via computed SVG attributes, not CSS vars.
- `--scriba-widget-shadow` (`:102`), `--scriba-widget-radius` (`:103`) — widget chrome is hardcoded in scriba-embed.css.
- `--scriba-progress-height` (`:107`), `--scriba-progress-bg` (`:108`), `--scriba-progress-fill` (`:109`) — for a progress **bar** that doesn't exist (the widget uses progress **dots**, styled by `.scriba-dot*`).

**scriba-tex-content.css** (only in TeX documents)
- `--scriba-diagram-dim-opacity` (`:43`), `--scriba-diagram-transition` (`:44`), `--scriba-diagram-active-fill` (`:45`,`:85`), `--scriba-diagram-active-stroke` (`:46`,`:86`) — a diagram-interaction theming set that nothing reads (diagram styling lives in scene-primitives under different token names).

Read-but-undefined (silent fallback): `--scriba-anim-name` (dead feature, F3) and `--scriba-font-mono` (plane2d.css:44, has `ui-monospace` fallback, sheet unshipped anyway). `--scriba-state-` "read" at `tree.py:734` is a scan artifact (f-string `var(--scriba-state-{state}…)`), not a real undefined var.

---

## Cleared (contract holds; prior fixes verified still good)

- **e010438 (tex scope) holds**: `number_spiral_fresh.html` has 3 `.scriba-tex-content` wrappers and 1 `.highlight` block; the content + pygments sheets are bundled (via artifact `css_assets`, `render.py:259-260`).
- **87616ab (pygments light+dark pair) holds — browser-verified**: C++ `.tok-k` keyword computes `rgb(166,38,164)` (One Light) in light theme and `rgb(198,120,221)` (One Dark) after toggling `data-theme="dark"`. Both sheets ship together; the dark sheet's `[data-theme="dark"]` guard works. `classprefix="tok-"` (`highlight.py:132`) makes all `.tok-*` selectors match the emitted spans — the ~50 `.tok-*` "dead" hits from a naive static scan are false positives (Pygments is the runtime emitter).
- **KaTeX classes** (`.katex`, `.katex-html`, `.mord`, `.mbin`, …) are matched by pre-rendered KaTeX HTML; katex.min.css ships only when the doc has math (`render.py:272-280`) — consistent.
- **JS-hook / template classes, not dead**: `.active` & `.done` set by `scriba.js:57,67`; `.copied` by `scriba-tex-copy.js:69`; `.theme-toggle` emitted by `render.py:43`; `.scriba-substory-widget` is a querySelector hook.
- **`.scriba-frame*` filmstrip classes** are live in `--static` mode (`_html_stitcher.py:250/317/319`); `.scriba-hl` emitted by `hl_macro.py:156`.
- **plane2d overall renders correctly** except the label font (F2): grid/axes visible via inline strokes, point transitions via scene-primitives.
- **Copy-button surface** (`.scriba-tex-copy-btn`, `.copied`, `--scriba-copy-btn-*`) is conditionally inert in render.py output (it passes `enable_copy_buttons=False`, `render.py:150`; button emitted at `code_blocks.py:54` only when enabled) but live for library consumers — not dead.

---

## Verdict

One **HIGH** bug of exactly today's family: **metricplot gridlines are invisible**
because `scriba-metricplot.css` is never bundled by `render.py` and the gridline
`<line>`s (uniquely among metricplot elements) carry no inline stroke —
browser-verified `stroke: none`. The same root cause (render.py hardcodes 4
animation sheets and discards animation/diagram `artifact.css_assets`, while the
correct `Pipeline` bundler is unused) also produces a **minor** plane2d
label-font regression (F2). Cleanest fix: have `render.py` collect
animation/diagram `artifact.css_assets` the same way it already does for TeX
(or, minimally, add the two sheets to `css_parts`). Secondary cleanup: remove the
dead `.scriba-anim-*` rules + `--scriba-anim-name` (F3, an unwired extension),
the two `.scriba-substory-frame(s)` selectors (F4), `.katex-fallback` (F5), and
the 13 dead custom-property definitions.

---

## Structural Fix Design (2026-07-02)

Read-only design pass. Nothing in `scriba/` was modified. All claims below were
probed with `.venv/bin/python` in scratchpad (see "Empirical proof").

### Design summary

Two source bugs, one root cause: **`render.py` throws away the `css_assets`
that animation/diagram artifacts declare**, shipping a hardcoded 4-sheet base
instead. `AnimationRenderer.render_block` already declares
`scriba-metricplot.css` / `scriba-plane2d.css` conditionally
(`renderer.py:522-530`), but render.py's block loop (`render.py:218-224`) only
appends `artifact.html` and drops `artifact.css_assets`. The TeX path was fixed
this way in e010438 (`render.py:202-204`, `259-260`); the fix is to give
animation/diagram artifacts the **same** treatment. A second, independent bug
surfaced while verifying: **`DiagramRenderer.render_block` never declares
primitive CSS at all** (`renderer.py:825-830` hardcodes only the 2 base sheets),
so even a corrected render.py would still starve the 6 `\begin{diagram}`+Plane2D
corpus docs. Both must be fixed together.

**Empirical proof (scratchpad `probe_css_assets.py`):**
- `AnimationRenderer.render_block(metricplot.tex).css_assets` = `['scriba-animation.css', 'scriba-metricplot.css', 'scriba-scene-primitives.css']` — sheet **declared**.
- `AnimationRenderer.render_block(plane2d.tex).css_assets` includes `scriba-plane2d.css`.
- `DiagramRenderer.render_block(plane2d_ticks.tex).css_assets` = `['scriba-animation.css', 'scriba-scene-primitives.css']` — **plane2d.css missing** (companion bug).
- `render.py` output for `metricplot.tex`: gridline rule (`stroke-width: 0.5`) appears **0** times → sheet not shipped, matches F1.

### Chosen architecture: (c) hardcoded base + artifact-declared extras

Keep the 4 base sheets hardcoded in render.py and additionally collect
animation/diagram `artifact.css_assets` into the **same** accumulator that
already carries TeX assets, subtract the base, and append the sorted remainder.
This is option (c), which converges with a *disciplined* reading of (a): one
`css_assets: set[str]` union fed to `load_css`, but with the base kept
render.py-owned.

**Why the base cannot be fully artifact-derived (pure-(a) rejected).** Of the 4
base sheets, only `scriba-scene-primitives.css` + `scriba-animation.css` are
declared by renderers (`renderer.py:517-520`, `assets()` `540-556`).
`scriba-embed.css` (widget chrome) and `scriba-standalone.css` (full-page
document chrome) are **declared by no renderer** — they are CLI-standalone-page
concerns. Forcing `AnimationRenderer`/`DiagramRenderer` to declare them would
pollute the library/`Pipeline` contract for embedders who supply their own page
chrome. So the base stays hardcoded; artifacts contribute only the primitive
extras.

**Why not (b) route through `core/pipeline.py`.** `Pipeline.render` is the
"principled" collector (namespaced union at `pipeline.py:280-321`) but it is the
wrong single entry for this CLI:
- **TeX gaps would stop rendering.** `Pipeline` escapes inter-block text as
  literal HTML (`pipeline.py:216,220` `_html.escape(...)`). render.py runs the
  full `TexRenderer` on every gap (KaTeX, `lstlisting`→pygments, tables) and
  wraps each in `.scriba-tex-content` (`render.py:206-236`). `Pipeline` has no
  TeX *block* renderer registered, so gaps would render as escaped plaintext — a
  severe regression.
- render.py would still own all page assembly regardless: `HTML_TEMPLATE`,
  `--no-minify`, Opt-3 `inline_katex_css()` (`render.py:272-280`), the theme
  script, `--lang`, XSS filename escape, `-o` path-traversal guard, and external
  runtime copy. `Pipeline` returns a `Document` (html + namespaced asset *names*
  + a `required_assets` path map), not a finished page.
- The namespaced keys (`"animation/scriba-metricplot.css"`) don't match
  `load_css`'s bare-name API and would need stripping.
Net: (b) is a large re-architecture with real regression risk and no benefit for
this bug. Leave `Pipeline` as the library/embedder entry; keep render.py on (c).

**`load_css` resolution covers the new names unchanged.** `css_bundler.py:32-37`
routes `scriba-tex*` → `scriba.tex/static`, else → `scriba.animation/static`.
`scriba-metricplot.css` and `scriba-plane2d.css` do **not** start with
`scriba-tex`, and both physically live in `scriba/animation/static/` (confirmed
by `ls`). So they resolve correctly with **no `css_bundler` change**.

### Exact wiring changes

**A. `scriba/animation/renderer.py` — make both renderers declare primitive CSS.**
1. Hoist the primitive→CSS map out of `AnimationRenderer.render_block`
   (`renderer.py:523-526`) to a module constant so both renderers share it:
   ```python
   _PRIMITIVE_CSS: dict[str, str] = {
       "Plane2D": "scriba-plane2d.css",
       "MetricPlot": "scriba-metricplot.css",
   }
   ```
   `AnimationRenderer.render_block` then references the constant (behaviour
   unchanged; `renderer.py:527-530` loop stays).
2. `DiagramRenderer.render_block` (`renderer.py:825-830`): build css_assets
   conditionally instead of the hardcoded 2-set — `ir` (and thus `ir.shapes`) is
   already in scope at `renderer.py:787`:
   ```python
   css_assets = {"scriba-animation.css", "scriba-scene-primitives.css"}
   for shape in ir.shapes:
       name = _PRIMITIVE_CSS.get(shape.type_name)
       if name is not None:
           css_assets.add(name)
   return RenderArtifact(html=html, css_assets=frozenset(css_assets), ...)
   ```
   Primitive type_names verified: `@register_primitive("MetricPlot")`
   (`metricplot.py:99`), `@register_primitive("Plane2D")` (`plane2d.py:94`).

**B. `render.py` — collect animation/diagram css_assets like TeX.**
1. `render.py:199` — broaden the accumulator (rename `tex_css_assets` →
   `extra_css_assets`; it already receives TeX assets via `_wrap_tex`,
   `render.py:202-204`).
2. `render.py:218-224` — in the animation/diagram branch, after appending
   `artifact.html`, add `extra_css_assets.update(artifact.css_assets)` on both
   the `kind == "animation"` and diagram paths.
3. Define the base constant near `render.py:248`:
   ```python
   _BASE_CSS = ("scriba-scene-primitives.css", "scriba-animation.css",
                "scriba-embed.css", "scriba-standalone.css")
   ```
   Keep `css_parts = [load_css(*_BASE_CSS)]` (byte-identical to today's
   `render.py:248-255`).
4. Replace `render.py:259-260` with a base-subtracted, sorted append of the
   unified set:
   ```python
   extras = extra_css_assets.difference(_BASE_CSS)
   if extras:
       css_parts.append(load_css(*sorted(extras)))
   ```
   The base subtraction is essential: animation artifacts always declare
   `scriba-animation.css` + `scriba-scene-primitives.css`, which are already in
   the base — without the subtraction they'd be concatenated twice.
   (Strictly-equivalent fallback: keep TeX and widget assets as two separate
   appends. Both are deterministic; the single union is preferred because it is
   exactly the "one `css_assets` set → `load_css`" end-state the case file wants.)

No emitter/DOM change and no JS change: gridline `<line>`s already carry the
`scriba-metricplot-gridline-*` class (`metricplot.py:447-461`); the fix is purely
that the matching sheet now ships. (Axes/ticks/markers carry inline
`stroke="var(--scriba-fg…)"`, `metricplot.py:483-510`, which is why only the
gridlines vanished.)

### Ordering & dedup

- **Determinism for goldens:** `sorted(extras)` — identical discipline to the
  e010438 TeX fix (`render.py:260`). Cascade order becomes base → extras → KaTeX.
- **Cascade correctness:** primitive selectors (`.scriba-metricplot-*`,
  `.scriba-plane-*`) never overlap TeX (`.scriba-tex-content *`) or base
  selectors, so relative order among extras is cosmetic. The `var(--scriba-border)`
  / `var(--scriba-fg)` tokens the primitive sheets read are defined in the base
  `:root` (ships first) — and CSS custom properties resolve at computed-value
  time regardless of declaration order, so there is no ordering hazard either way.
- **Dedup:** handled by `extra_css_assets.difference(_BASE_CSS)`; `load_css`
  itself does not dedup (it concatenates its args verbatim).
- **KaTeX unchanged:** `inline_katex_css()` still appended last, only when
  `_has_math` (`render.py:272-280`). Untouched.
- **TeX-only docs stay byte-identical:** for a doc with no widget primitive the
  unified `sorted(extras)` argument list equals today's `sorted(tex_css_assets)`,
  so the emitted bytes are unchanged (verified by construction). Only
  widget-bearing docs gain a sheet.

### Conditionality matrix (output mode × sheets shipped)

CSS collection runs in render.py *after* the block loop and depends only on
`artifact.css_assets` (driven by `ir.shapes`), never on `output_mode` — so the
fix behaves identically across modes. `✅new` = now ships (was the bug); `—` = unchanged.

| Output mode | base 4 | metricplot.css (doc has MetricPlot) | plane2d.css (doc has Plane2D) | tex sheets | katex |
|---|:--:|:--:|:--:|:--:|:--:|
| interactive (default) | ✅ | ✅new | ✅new | if TeX gap | if math |
| `--static` filmstrip | ✅ | ✅new | ✅new | if TeX gap | if math |
| `--no-inline-runtime` | ✅ | ✅new | ✅new | if TeX gap | if math |
| diagram-only (`\begin{diagram}`) | ✅ | ✅new¹ | ✅new¹ | if TeX gap | if math² |
| math-free / diagram-free (Opt-3) | ✅ | n/a³ | n/a³ | if TeX gap | — |

¹ Requires the `DiagramRenderer` companion fix (change A.2); without it these
stay ❌ — this is the 6 `\begin{diagram}`+Plane2D corpus docs.
² Any doc with an animation/diagram block already sets `_has_math=True`
(`render.py:273-277`), so a widget doc always shipped KaTeX; unchanged.
³ A math-free/widget-free doc has no MetricPlot/Plane2D by definition; extras
stay empty and the Opt-3 KaTeX skip is preserved. **No output-mode regression.**

Conditionality is real, not always-on: the sheet ships only when a `shape` of
that type is present (`renderer.py:527-530` for animation; change A.2 for
diagram), verified empirically above.

### Cleanup commit spec (separate `chore:` commit, land AFTER the fix)

All 5 selector groups + 13 tokens re-verified: **0 `var()` reads** for every
token, **0 emitters/JS hooks** for every selector (only matches are the sheets
themselves, `keyframes.py`'s `UTILITY_CSS` string literal for the unwired
extension, and gitignored `examples/**/*.html` build artifacts), and **0 tests**
assert any of them present. Safe to delete.

Dead selector groups:
1. `scriba/animation/static/scriba-animation.css:15-21` — `.scriba-anim-rotate/-pulse/-orbit/-fade-loop/-trail` utility block (F3).
2. `scriba-animation.css:57-64` — the same 5 selectors inside the
   `@media (prefers-reduced-motion)` block. **Delete only the `.scriba-anim-*`
   selectors; KEEP `.scriba-frame:target .scriba-hl { transition:none }` at
   `:66-69`** — that rule is live.
3. `scriba-animation.css:33-43` — `.scriba-substory-frames` (F4).
4. `scriba-animation.css:44` — `.scriba-substory-frame`, plus its `@media print`
   (`:47-48`) and `@media (max-width:640px)` (`:52`) references (F4).
5. `scriba/tex/static/scriba-tex-content.css:197` — `.scriba-tex-content .katex-fallback` block (F5).

Dead tokens (custom-property definitions):
- `scriba-scene-primitives.css` `:root`: `--scriba-stage-padding` (`:54`),
  `--scriba-cell-size` (`:68`), `--scriba-node-r` (`:72`),
  `--scriba-tick-length` (`:76`), `--scriba-widget-shadow` (`:102`),
  `--scriba-widget-radius` (`:103`), `--scriba-progress-height` (`:107`),
  `--scriba-progress-bg` (`:108`), `--scriba-progress-fill` (`:109`) — 9.
- `scriba-tex-content.css`: `--scriba-diagram-dim-opacity` (`:43`),
  `--scriba-diagram-transition` (`:44`), `--scriba-diagram-active-fill`
  (`:45` light, `:85` dark), `--scriba-diagram-active-stroke` (`:46` light,
  `:86` dark) — 4 names (6 lines). Total 13 names.
- Leave `--scriba-anim-name` / `--scriba-font-mono` alone: they are
  *read-but-undefined* fallbacks that disappear naturally once the F3 rules and
  (already-unshipped) plane2d label rule stop referencing them; nothing to delete.

**Golden impact of the cleanup is corpus-wide.** `scene-primitives.css` +
`animation.css` are in the base-4 that ships in **every** page, and
`tex-content.css` ships in every TeX-bearing page. Deleting lines from them
changes the base `<style>` bytes → **all 105 corpus goldens regenerate**. This
is mechanical (only removals) but must be isolated from the fix so the fix's
review stays clean — hence a **separate** commit, landed second.

### TDD plan (RED first)

Idiom: `tests/unit/test_render_page_assembly.py` renders via `render_file` and
asserts on the page string. New cases (all currently FAIL, PASS after the fix):

1. **metricplot bundled (animation path)** — `render_file` a doc with
   `\shape{m}{MetricPlot}{...}`; assert the gridline rule is present, e.g.
   `assert ".scriba-metricplot-gridline-h" in page and "stroke-width: 0.5" in page`.
   RED today (grep count 0, proven above).
2. **plane2d label font bundled** — doc with `\shape{p}{Plane2D}{...}`; assert
   `".scriba-plane-labels text" in page` and
   `"font-family: var(--scriba-font-mono" in page`.
3. **diagram-path plane2d bundled** — `render_file` a `\begin{diagram}` with a
   Plane2D; assert `".scriba-plane-labels text" in page`. Pins the
   `DiagramRenderer` companion fix (change A.2); RED even after only the render.py
   change.
4. **renderer-level unit (fast, no render_file)** — in
   `tests/unit/test_animation_renderer.py`: `DiagramRenderer().render_block(<Plane2D
   diagram>).css_assets` contains `"scriba-plane2d.css"`. Directly pins A.2.
5. **negative guard** — a plain Array animation doc must NOT ship metricplot/plane2d
   (`"scriba-metricplot-gridline-h" not in page`), locking conditionality.
6. **Optional browser check** — headless Chromium (path in task) on the rendered
   metricplot page: `getComputedStyle(gridline).stroke !== 'none'` (currently
   `none`, per F1). Supplements the string assertions; the string checks are the
   primary signal per the file's idiom.

**Existing tests that pin the current bundle:**
- `tests/unit/test_css_font_sync.py:159-165` `bundled_css` reconstructs the base-4
  via `load_css(...)` directly. It asserts the halo/font cascade, not sheet
  count → **not broken** by the fix (base list unchanged). No update needed.
- `tests/integration/test_animation_end_to_end.py:433` `test_pipeline_css_assets`
  and `tests/integration/test_phase_b_render.py:367` assert only
  animation+scene-primitives on the `Pipeline`/artifact path (Array source) →
  unaffected. Good place to *add* a metricplot assertion for the `Pipeline` path.
- `tests/unit/test_primitive_metricplot.py:240-247` asserts gridline *classes in
  the SVG* (emission), not the bundle → unaffected.
- **No test asserts "metricplot.css NOT shipped by render.py,"** so nothing needs
  its polarity flipped.

**Predicted golden churn (fix commit):** only docs containing the primitives —
MetricPlot corpus {metricplot, simulated_annealing, splay, test_reference_extended,
weird_algorithm} = 5; Plane2D corpus {convex_hull_andrew, convex_hull_trick,
fft_butterfly, li_chao, plane2d, plane2d_annotations, plane2d_lines, plane2d_ticks,
test_plane2d_animation, test_plane2d_dense, test_plane2d_edges,
test_reference_extended} = 12; union (test_reference_extended overlaps) =
**16 goldens** regenerate via `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/`.
The other 89 are byte-identical (base list unchanged). The mirror
`examples/primitives/{metricplot,plane2d}.html` are gitignored build artifacts —
no golden action. Each of the 16 diffs should be purely *additive* `<style>`
rules — review that they contain nothing else.

### Blast radius & landing order

- **`render.py` `render_file`** — the sole shipping HTML producer; touches every
  page's `<style>`. Change is additive + conditional + base-subtracted, so
  non-widget pages are byte-identical. Risk: LOW.
- **`renderer.py`** — `_PRIMITIVE_CSS` hoist is behaviour-preserving for
  `AnimationRenderer`; `DiagramRenderer.render_block` gains conditional
  css_assets, which also flows into `Pipeline.required_css` (library/embedder
  path) — a strict superset, no removals. Risk: LOW.
- No change to emitters, primitives' SVG, `css_bundler`, or any JS.

**Landing order:**
1. **Commit A `fix(render):`** renderer.py (A.1 hoist + A.2 DiagramRenderer) +
   render.py (B.1–B.4) + the 6 new/updated tests + regenerate the **16** widget
   goldens. Review = 16 additive diffs.
2. **Commit B `chore(css):`** delete the 5 dead selector groups + 13 dead tokens
   + regenerate **all 105** goldens (base-sheet byte shift). Review = pure removals.

Fix-first keeps A's review to 16 additive files; doing cleanup first would churn
those same 16 twice. Both are independently revertable.
