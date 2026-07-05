# Scriba

**Status:** v0.26.1 · MIT · Python 3.10+

Scriba is a backend Python library that renders LaTeX problem statements and
competitive-programming editorials to self-contained HTML fragments. It is
LaTeX-first: drop a `.tex` source in, get out HTML plus the exact CSS/JS
asset basenames needed to display it.

## What is Scriba?

- **LaTeX-first rendering** for CP problem statements and editorials, with
  KaTeX math, Pygments code highlighting, lists, tables, sections, figures,
  `\href` / `\url` with XSS hardening, and `\begin{lstlisting}` code blocks.
- **Self-contained output contract:** every render produces an HTML fragment
  plus a namespaced set of required CSS and JS basenames and a block-data
  map — consumers decide how to serve the static assets.
- **`\begin{animation}` environment** (shipping since 0.2.0) for step-through
  editorial walkthroughs with 21 built-in primitives (arrays, grids, graphs,
  trees, DP tables, number lines, matrices/heatmaps, stacks, plane-2D,
  metric plots, the data-structure primitives code panel / hash map /
  linked list / queue / deque / variable watch, the subset-lattice
  Hypercube, multi-root Forest, the variable-height Bar, and the accumulating
  TraceTable). `\begin{diagram}` for inline
  static graph/tree figures is reserved under extension E5. See
  [`docs/spec/ruleset.md`](docs/spec/ruleset.md) for the full grammar and
  error catalog.

## What's new in v0.26.1

A polish patch on the 0.26.0 "teacher's board" release — **no rendered-output
change** (`SCRIBA_VERSION` stays 19; documents render byte-identically to
0.26.0). Completes the animation error catalog (E1491/E1492/E1183/E1184 added —
an internal registry, no user-facing message change) and sweeps every doc to
0.26.0 reality: 21 primitives, 23 inner commands (`environments.md` §3 now
documents all 23), 9 semantic states, 11 motion kinds, and the phantom `§9.2`
state names purged from the primitive pages.

<details>
<summary>v0.26.0 changelog</summary>

## What's new in v0.26.0 — the teacher's board

A 6-slice census of how CP teachers explain on a whiteboard / in a YouTube
lecture (`investigations/teaching-*.md`) closed the three axes scriba was thin
on, with **0 new motion kinds**:

- **Board-as-record** — **`\annotate{x}{strike=true}`** (cross out a rejected
  candidate but keep it visible), **`\note{id}{at=<compass>}`** (a free margin
  callout), the **TraceTable** primitive (the dry-run trace table: variables ×
  steps, rows accumulate), and a live **`\invariant{sum = ${s}}`** (interpolates
  per frame).
- **Deliberate layout + camera** — **`at=[row,col]`** on `\shape` arranges
  several shapes in a grid (array top / tree below / recurrence right);
  **`\zoom{target}`** magnifies one region for a step (camera twin of `\focus`).
- **Math as an evolving object** — the **Equation** primitive makes sub-terms
  (`E.term[id]`) and aligned lines (`E.line[i]`) addressable, so a teacher can
  tint a term and reveal a derivation line-by-line.
- **Board-wide spotlight** (`\focus{x}{scope=board}`) and **graph/tree
  `\trace`** (BFS/DFS follow-the-edges) round out the marker verbs.
- `SCRIBA_VERSION` 18→19 (the Equation `.scriba-term` CSS + the live-invariant
  runtime swap); everything else is byte-identical for documents that don't use
  it. Primitive count 19→21.

</details>

<details>
<summary>v0.25.0 changelog</summary>

## What's new in v0.25.0

- **Grammar-completeness vocabulary** (post-0.24 census closed the last
  three coverage gaps): the **Bar** primitive for variable-height columns
  (largest-rectangle, skyline, monotonic-stack-on-heights, sorting-as-bars);
  **Graph `positions=[(node,x,y),…]`** to pin nodes at author coordinates
  (FFT butterfly, planar and geometric graphs); and Plane2D
  **`rotate_point` / `rotate_segment` / `rotate_line`** for angular motion
  (rotating calipers, angular sweeps, Burnside rings).
- **Byte-identical for existing documents** — all three ride shipped motion
  (`value_change` / `position_move`), add no CSS or scriba.js, and emit no
  bytes unless used, so `SCRIBA_VERSION` stays 18.
- **Five Tier-D fixes** — BST `reparent` picks the right child side
  (opt-in `index`), the `plane2d.*` geometry helpers work in `\compute`,
  `${vals[i+1]}` raises a clean E1159 instead of pasting garbage, an
  out-of-range `\trace` vertex warns (E1115) instead of vanishing, and
  `\recolor{state=${s}}` gives a clean E1109.

</details>

<details>
<summary>v0.24.0 changelog</summary>

## What's new in v0.24.0

- **New capabilities from the JudgeZone pass-3 census** (~230 problems
  unlocked with 3 new primitives, 3 new verbs, 0 new motion kinds):
  Hypercube (subset lattice), Forest (multi-root DSU with gliding
  unions), and Deque; `\link` / `\combine` cross-shape bridges and
  `\group` / `\ungroup` component hulls; `row[i]` / `col[j]` / `diag`
  selectors, Array `reorder`, Plane2D `move_*` + `circle`/`arc`/`wedge`,
  Tree `kind=heap` and char-edge/fail-link automata, Matrix value
  mutation, and antiparallel residual-edge curves.
- **Elements now glide** — `position_move` lands on the new seat instead
  of teleporting, so Tree reparents, Forest unions, sweep lines and
  sorting reorders animate smoothly (and reverse cleanly).
- **Hardening from a three-round adversarial test pass** — wrong-type
  params raise clean E-codes instead of tracebacks, `${...}` resolves in
  every generic selector, `\trace` on an unsupported primitive is loud
  (E1118), dark-mode edge contrast meets WCAG 3:1, and keyboard nav
  survives the first/last frame.

</details>

<details>
<summary>v0.23.1 changelog</summary>

## What's new in v0.23.1

- **LinkedList no longer shifts on insert/remove** — its bounding box
  follows a max-node-count envelope (grown by a structural prescan), so
  mid-timeline structure changes keep every node in place (R-32).
- v1.1 polish: carets can park on Array sentinels
  (`\cursor{a}{id=i, at="before"}`), `\playeach` works on NumberLine
  ticks, `\focus` typos warn instead of dimming the whole shape, `\ref`
  adds a dashed ring on the referenced element, and unknown `\playeach`
  keys fail fast (`E1496`).

</details>

<details>
<summary>v0.23.0 changelog</summary>

## What's new in v0.23.0

- **Every navigation direction now animates** — Prev/ArrowLeft tween by
  inverting the step's delta manifest; multi-step jumps snap and pulse
  exactly what changed (cap 8, `prefers-reduced-motion` honoured,
  `SCRIBA_NO_EMPHASIS=1` opt-out).
- **Named binding carets** — `\cursor{a}{id=i, at="w.var[i]"}`: multiple
  ▲ markers slide between cells, re-reading a VariableWatch value each
  frame. Legacy `\cursor` unchanged.
- **Narration welds to the frame** — `\ref{sel}{text}` tints a word with
  the referenced element's CURRENT state color each frame; `\focus{sel}`
  spotlights the active set; `\step[title=]` headings; `\invariant{...}`
  pinned predicate panel.
- **`\playeach`** — one auto-frame per element of a range/block (recolor
  sweep + caret + `${i}` narration), byte-identical to hand-written steps.
- **Array grows honestly** — `insert=`/`remove=` shift values on a fixed
  grid (positions never move), `sentinels=true` adds `a.before`/`a.after`
  slots for out-of-range iterators.
- `SCRIBA_VERSION` 15→16; new spec: `docs/spec/motion-ruleset.md` (A-0..A-8).

</details>

<details>
<summary>v0.22.2 changelog</summary>

## What's new in v0.22.2

- **`\trace`** — an arrow that follows a sequence of cells
  (`cells=[[2,0],[2,1],...]`): traversal/fill direction is SHOWN, not
  inferred from cell numbering; the interactive widget draws the arrow
  along its path on the step it appears.
- **`block[r0:r1][c0:c1]`** — the 2-D twin of `range` for Grid/DPTable-2D,
  with `bracket=true` for a dashed outline hugging the area.
- **`color="state:X"` + `leader=true`** — labels can carry the exact color
  of the state they describe (current/done/dim/good/error/path,
  dark-adapted, WCAG-AA inks) and connect to their cell with a dotted
  leader.
- `SCRIBA_VERSION` 14→15 (new CSS tokens change rendered bytes; the new
  commands are opt-in). See `CHANGELOG.md`.

</details>

<details>
<summary>v0.22.1 changelog</summary>

## What's new in v0.22.1

- **Exact label-math metrics** — annotation/caption/tick labels containing
  `$math$` are measured by a KaTeX advance-sum over the vendored font
  tables (p50 0.06% vs Chromium; the old heuristic sat at p50 43% and
  measured `$\to$` as 0px). Label foreignObjects grow instead of clipping,
  tall math (`\frac`, big-operator limits) gets adaptive line heights, and
  every FO div is font-pinned so painted widths match measured ones.
- **Content-based cells** — DPTable/Grid cells widen to their widest value
  across the whole timeline (frame-stable, no breathing); Matrix floors
  `cell_size` under `show_values`. No-KaTeX fallbacks paint a stripped
  `max(y,x)` instead of raw `$\max(y,x)$`, and are measured as painted.
- `SCRIBA_VERSION` 13→14 — rendered bytes change; caches keyed on output
  must invalidate. See `CHANGELOG.md` for the full list.

</details>

<details>
<summary>v0.22.0 changelog</summary>

## What's new in v0.22.0

- **Exact text metrics** — cell/node text is measured against a shipped,
  pinned 34 KB Inter subset ("Scriba Sans", full Vietnamese coverage) using
  the font's own advance table: browser deltas drop from 5–30% to <1%,
  tabular-nums honoured, stdlib-only runtime.
- **One runtime source** — the inline widget `<script>` (and the standalone
  theme toggle) are derived from `scriba.js` by sentinel slicing; a
  generation-token guard kills the orphaned-transition race; rapid
  Next/Prev never swallows frames.
- **Every-script rung 0** — Thai/Devanagari identifiers parse (combining
  marks), spaceless scripts wrap cluster-safely, RTL text renders in
  logical order (`unicode-bidi:plaintext`, `dir="auto"`), complex-script
  widths warn once (`W1301`) that they are safe over-estimates. CJK is
  exact at 1em by construction.
- **Layout cannot drift** — viewBox + stacking offsets come from one shared
  timeline replay; content labels join one registry per primitive; the
  smart-label lint backlog is zero and gated there.

</details>

<details>
<summary>v0.21.0 changelog</summary>

## What's new in v0.21.0

- **Annotation & caption legibility across all primitives** — long `label=`
  captions wrap and fold into every primitive's bounding box (no more clipping
  at the figure edge); `range[a:b]` and `position=below` annotation targets that
  were silently dropped now render on all data-structure primitives;
  `position=below` labels sit in a leader-connected callout lane, wide
  `left`/`right` pills reserve horizontal space, competing above-labels stack
  (ranges get a span bracket), and cross-primitive obstacle avoidance is
  restored. Rendered output bytes differ (`SCRIBA_VERSION` 8→9) — caches keyed
  on rendered output MUST invalidate.
- **(v0.20.0)** Compact embed widget — overlay step controls, tidy spacing, overlap-safe annotations.
- **(v0.19.0)** Graph layout stability — node pinning, isolated-node lane, auto-seed.
- **(v0.18.0)** Render-content fixes — narration interpolation, captions, recolor, shared defs.
- **(v0.17.0)** Fail-loud validation, render fixes, reference overhaul.
- **(v0.16.0)** Embedder font-scale knob + boundary validation.
- See [`CHANGELOG.md`](CHANGELOG.md) for the full history.

</details>

<details>
<summary>v0.8.2 changelog</summary>

- **Position-aware auto-ID generation.** Duplicate animation/diagram
  blocks with identical content now produce distinct HTML element IDs.
- **Duplicate block ID warning.** The pipeline emits
  `CollectedWarning(code="E1019", severity="dangerous")` when two
  blocks share the same `block_id`.

</details>

<details>
<summary>v0.8.0 changelog</summary>

- **Fixed state styling regression.** Cell/node/edge state colors
  (`current`, `error`, `good`, `highlight`, etc.) were silently overridden
  by primitive base selectors due to a CSS specificity conflict. Primitive
  base selectors now use `:where()` to zero their qualifying specificity,
  so `.scriba-state-*` rules always win.

</details>

<details>
<summary>v0.7.0 changelog</summary>

- **Fully portable HTML output.** `render.py` now produces single-file,
  offline-ready HTML. All CSS (scene primitives, animation, widget chrome,
  Pygments syntax highlighting), KaTeX math fonts (20 woff2 files,
  base64-encoded), and `\includegraphics` images (data URIs) are inlined.
  Zero CDN dependencies — just open the `.html` in any browser.
- **CSS deduplication.** The ~470-line inline CSS block in `render.py` was
  replaced by a new `scriba.core.css_bundler` module that reads CSS from
  source `.css` files at render time. Single source of truth for all
  styling.
- **`traversable_to_path()` helper.** Centralised the
  `Path(str(traversable))` anti-pattern across 3 files into a documented
  helper in `scriba.core.artifact`, ready for future `as_file()` upgrade.
- **`text_outline=` parameter removed.** The per-call text outline parameter
  on primitives, deprecated in v0.6.0, is removed. Use the CSS halo
  cascade instead.

</details>

<details>
<summary>v0.6.0 changelog</summary>

- **Wave 8 — vstack layout.** Array, DP-table, and related primitives now
  compose their caption, index labels, and cells through a shared
  `scriba/animation/primitives/layout.py` vstack helper.
- **Wave 9 — CSS-first text halo cascade.** Every `[data-primitive] text`
  element now inherits `paint-order: stroke fill markers` with a
  `--scriba-halo` CSS variable that each state class overrides.
- **RFC-001 — structural mutation ops.** Tree, Graph, and Plane2D primitives
  gained safe structural ops (`add_node`, `remove_node`, `reparent`).
- **RFC-002 — strict mode and document warnings.** Pipeline surfaces
  non-fatal issues on `Document.warnings`. See
  [`docs/guides/strict-mode.md`](docs/guides/strict-mode.md).
- **Examples reorganized.** 53 `.tex` examples across `examples/quickstart/`,
  `examples/algorithms/`, `examples/cses/`, and `examples/primitives/`.
  See [`docs/cookbook/README.md`](docs/cookbook/README.md).

</details>

## Install

```bash
pip install scriba-tex
```

Scriba shells out to a small Node.js worker for KaTeX math, so the host
environment needs Node.js 18+ on PATH:

```bash
# System prerequisite — Node.js only
apt-get install nodejs   # or: brew install node
```

KaTeX `0.16.11` is vendored inside the wheel (at
`scriba/tex/vendor/katex/katex.min.js`), so **no separate
`npm install -g katex` step is required**. `pip install scriba-tex` is all
you need once Node is present.

## Using Scriba with an AI assistant

To have an AI write `.tex` for Scriba, give it one file:
**[`docs/SCRIBA-TEX-REFERENCE.md`](docs/SCRIBA-TEX-REFERENCE.md)**.

It's self-contained — all commands, all 21 primitives, all selectors,
all gotchas. No other spec files needed.

Prompt template:
> Read `SCRIBA-TEX-REFERENCE.md`. Write a Scriba `.tex` file that
> animates [algorithm]. Use only commands and primitives documented
> in that file.

## Hello world

```python
from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer

pool = SubprocessWorkerPool()
pipeline = Pipeline([TexRenderer(worker_pool=pool, pygments_theme="one-light")])

ctx = RenderContext(
    resource_resolver=lambda name: f"/cdn/problems/1/{name}",
    theme="light", dark_mode=False, metadata={}, render_inline_tex=None,
)

doc = pipeline.render(r"\section{Hello} Let $x^2$ be the square.", ctx)
print(doc.html)          # HTML fragment
print(doc.required_css)  # namespaced CSS keys
pipeline.close()
```

## Standalone CLI

For quick rendering without writing Python, use `render.py` directly:

```bash
python render.py input.tex                # → input.html
python render.py input.tex -o out.html    # → custom output path
python render.py input.tex --open         # → render and open in browser
```

Output is a **single, fully portable HTML file** — all CSS, KaTeX math
fonts, syntax highlighting, and images (via `\includegraphics`) are
inlined as data URIs. No internet connection or external files needed.
Just open the `.html` file in any browser.

For legacy filmstrip mode (static frames, no JavaScript):

```bash
python render.py input.tex --static
```

## Sanitize before embedding

Scriba does **not** sanitize its output — consumers must pass it through a
vetted sanitizer before embedding in a page. Scriba ships an allowlist that
matches its output contract:

```python
import bleach
from bleach.css_sanitizer import CSSSanitizer
from scriba import ALLOWED_TAGS, ALLOWED_ATTRS

css = CSSSanitizer(allowed_css_properties=("transform","transform-origin","width","height"))
safe = bleach.clean(doc.html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
                    css_sanitizer=css, strip=True)
```

## Serving static assets

Assets ship inside the Python package. Copy them at deploy time:

```python
from importlib.resources import files
import shutil
shutil.copytree(str(files("scriba.tex.static")), "./public/scriba", dirs_exist_ok=True)
```

Then include them alongside the rendered fragment:

```html
<link rel="stylesheet" href="/cdn/katex/katex.min.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-content.css">
<link rel="stylesheet" href="/public/scriba/scriba-tex-pygments-light.css">
<script defer src="/public/scriba/scriba-tex-copy.js"></script>

<article class="scriba-tex-content">{{ doc.html }}</article>
```

> **Note:** This section applies to the **Pipeline API** (library usage),
> where you serve assets yourself. If you use `render.py` instead, the
> output HTML is fully self-contained — all CSS, KaTeX fonts (base64), and
> Pygments highlighting are inlined. No separate asset serving needed.

## Documentation

Full architecture, contracts, and roadmap live under the project docs tree:
<https://github.com/Danchuong/scriba/tree/main/docs>

## License

MIT. See [`LICENSE`](LICENSE).
