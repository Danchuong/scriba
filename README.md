# Scriba

**Status:** v0.38.0 · MIT · Python 3.10+

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

## What's new in v0.38.0 — Stack caption honesty + live-controls clearance

**Two fixes where the real mechanism differed from the report.** A Stack's
caption painted exactly `arrow_above` px past the declared viewBox — not a
prescan gap, but a coordinate double-count in `stack.py`, the **last of 7
sibling primitives** still missing the house `- arrow_above` correction
(one-line fix, annotation-free Stacks byte-identical). And the floating
prev/next chip's clearance was rem-based while the chip's box is px-based —
matching only at 16px root font; new `--scriba-pill-*` tokens tie both to
one `calc()` chain so chrome and content can never share pixels again.
107 goldens re-bless, print frames untouched (`SCRIBA_VERSION` 33).

<details>
<summary>v0.37.0 changelog</summary>

## What's new in v0.37.0 — displaced below-pill leaders reach their anchor

**No more orphaned pills.** A `position=below` pill on an internal Tree node
(or a top-row Grid/Matrix/DPTable cell, or a Graph/Hypercube top node) gets
correctly pushed below everything it would collide with — but its leader
stayed a ~10px stub rooted in another row's territory, so the pill floated
in blank canvas pointing at nothing. Past a snug-gap threshold the leader
now spans **anchor edge → pill edge**, the convention `leader=true` always
used. 6 family members fixed, 9 snug combos pinned byte-identical, 16 new
lane tests, zero golden churn (`SCRIBA_VERSION` 32).

</details>

<details>
<summary>v0.36.0 changelog</summary>

## What's new in v0.36.0 — invariant theorem box, top-band reservation, panel unification

**`\invariant` grows up.** The blue side-bar becomes a quiet **theorem box**
on house tokens — no caption, no hardcoded language anywhere (the chrome IS
the signifier); inline `$...$` gets `\displaystyle` so `\max`/`\sum` read at
full operator size; `overflow-wrap` ends mid-parenthesis wrapping; N stacked
`\invariant` lines share one box. **Top band joins the reservation model**
(JudgeZone #15): Tree/Forest/Graph captions no longer collide with
`position=above` pills, `\group` hulls, `\link` bows or antiparallel edge
bows over the crown — the mirrored sibling of the bottom-band model, closed
with 25 lane tests. And the three HTML emitters are **single-source** for
every shell panel now (9 inline duplications unified; narration gains the
same mobile overflow guard). 107 goldens re-bless (`SCRIBA_VERSION` 31).

</details>

<details>
<summary>v0.35.0 changelog</summary>

## What's new in v0.35.0 — JudgeZone #9–#14: five family contracts + sweep wave

**Six external bug reports, closed as five structural families** — each fixed
at the shared emitter/CSS layer behind a permanent enforcement test, then
swept across the whole surface (seven more sibling defects found and fixed
the same way). Dark mode stops painting `bracket=true` outlines as opaque
boxes and the Plane2D chip/labels/ticks get their first dark rules;
`${5 \choose 3}$` in a narration renders as math instead of re-pairing every
later `$` off-by-one (interpolation fires only on identifier-shaped
`${name}`); bound carets, captions, index rows and `position=below` pills
share one reservation model; labels obey **measure == paint == announce**
(wrapped pill padding restored, snake_case stops announcing "subscript",
`\_`/`\texttt{}` behave, `color="state:X"` resolves real state hues); and
static diagrams stop leaking the internal widget id as the hover tooltip
(`label=` → `<title>`, else omitted — with a corpus-wide conformance test).
110 goldens re-bless (`SCRIBA_VERSION` 30).

</details>

<details>
<summary>v0.34.0 changelog</summary>

## What's new in v0.34.0 — annotation labels adopt the house text oracle

**Annotation pills speak one typeface** (JudgeZone report #8). An
`\annotate`/`\link`/`\note` label mixing inline math and text used to pair
KaTeX serif math with `ui-monospace` bold text inside one small pill; text
runs now paint **"Scriba Sans"** — the shipped Inter subset cells, values and
equations already use, with **full Vietnamese coverage** — and are measured by
the same exact advance table (float sum, NFC-correct: decomposed input
measures identically to precomposed). `good`/`path` labels clamp 700 → 600 so
the static master stays synthesis-free (measured == painted, pinned by
`font-synthesis: none`), the wrap ruler packs with the painted face, and raw
math symbols outside `$...$` take a conservative floor. Reviewed by two
3-agent adversarial rounds; non-annotation surfaces proven byte-identical.
~107 goldens re-bless (`SCRIBA_VERSION` 29).

</details>

<details>
<summary>v0.33.0 changelog</summary>

## What's new in v0.33.0 — sweep-3 addendum

**Two accessibility/text polish fixes from the independent cross-validation
pass.** SVG **tooltips no longer garble math narration** — the `<title>`
fallback used to concatenate each KaTeX island's raw TeX with its visual text
(`Add edge D \to A  D → A  D → A`); it now carries the visual text once
(40 corpus docs clean up). And the step counter drops an **orphan
`aria-atomic`** that had no `aria-live` to act on. 93 goldens re-bless by one
attribute (+ the title cleanups); `SCRIBA_VERSION` 28.

</details>

<details>
<summary>v0.32.0 changelog</summary>

## What's new in v0.32.0 — sweep-3 residual closure

**The render-quality campaign converges.** The last two open residuals are
fixed — **`\cursor` now paints on Deque** (its own `emit_svg` had missed the
0.31.0 Queue wiring) and **`\link` labels carry the house halo** so the
mid-bridge text stays legible over the dashed bridge — and the four remaining
LOW polish items are formally closed as documented design decisions
(KNOWN-DEAD `.scriba-highlighted`, fs-snap structural adds, `tr=null` content
snaps, the Prev reverse-flash). Zero corpus re-bless (`SCRIBA_VERSION` 27).
Four sweep rounds, four releases: every verified render, visualization, and
code defect found by the campaign is fixed and pinned by a test.

</details>

<details>
<summary>v0.31.0 changelog</summary>

## What's new in v0.31.0 — sweep-3 fix wave

**Four hunters probed the fresh 0.30.0 surface, decoration stacks, hostile
value content, and the runtime contract — 12 defects, all fixed structurally,
all byte-inert on the corpus.** The headline: **KaTeX math values now theme in
dark mode** — the FO ink was baked to the light palette inline and sat at
1.06:1 (invisible) on a dark idle cell; it now routes through the state text
tokens (light pixel-identical, dark flips free), including the default-pill
math edge weight. A **Tree node born mid-scene with a wide value** no longer
clips the viewBox or jumps the layout (the prescan reserves the final pitch
via the timeline-max clone); the **isolated-node lane packs by label halves**;
**trace/group title pills and annotation pills finally see each other** in the
shared-obstacle model; **`\cursor` works on Stack/Queue** as documented;
`\annotate` on `q.front`/`q.rear` anchors instead of vanishing; **`\note`
renders `$math$`** and isolates RTL; and **Matrix/NumberLine constructors fail
loud** (E1423/E1455) instead of leaking raw tracebacks. All 107 goldens
re-bless by one identical CSS delta (`SCRIBA_VERSION` 26).

</details>

<details>
<summary>v0.30.0 changelog</summary>

## What's new in v0.30.0 — graph/theme cluster

**The focused cycle 0.29.0 promised: graph dark-mode pill + the node-label layout
family, fixed structurally and byte-inert on the whole shipped corpus.** The graph
edge-weight **pill now themes in dark mode** without touching the state-tint
signal: the default pill emits the literal `fill="white"` while every tint emits a
hex, so a CSS attribute selector flips only the default chip (3.71:1 sub-AA text
on a 12.48:1 bright island → 14.47:1 on a chip that blends into the stage). **Node
labels fit:** a monotonic per-node cross-frame-max label map on `PrimitiveBase`
(seeded from static ids, grown by the existing prescan replay) now drives both the
viewBox — a wide `dist[v]=infinity` label grows the frame instead of clipping —
and the pitch — Tree leaves, Hypercube rows, Forest columns/seams and the Graph
overlap post-pass all spread wide labels apart instead of letting them collide.
And the **force layout finally scales its canvas with node count** (area-per-node,
floored at 400×300 so N ≤ 16 is byte-identical): 0 overlaps / 0 coincident nodes
at N=100 across six probe topologies, where the fixed box left 93 overlapping and
2 coincident pairs. All 107 goldens re-bless by one identical CSS delta; no SVG
geometry changed anywhere (`SCRIBA_VERSION` 25).

</details>

<details>
<summary>v0.29.0 changelog</summary>

## What's new in v0.29.0 — render-quality sweep, round 2

**A second numeric sweep on new angles — and mostly a clean bill of health.** Four
hunters probed what round 1 didn't: animation transitions, theme/accessibility,
extreme scale, and cross-primitive composition. The engine came back **sound** —
transitions always settle on the correct frame (no flip-back), geometry never runs
away or clips even at 25-node graphs and 100-step animations, and `\zoom`/`\group`/
board layout/RTL-in-cells are all clean. Five fixable defects fell out and were
fixed structurally: **`\focus`** now dims Tree/Forest *nodes* (a regex missed the
`data-node-x/y` attributes so a focused tree only half-dimmed); **RTL pills** carry
bidi isolation so Arabic/Hebrew labels stop scrambling; a **`\link` label** can no
longer float off the top of the board; a **`Bar`** value that is tiny beside a huge
one keeps a 2px minimum height instead of vanishing; and the **`dim` state** dropped
a group `opacity: 0.5` that had been silently halving its contrast to ~1.9:1 on
every dim cell (the muted palette alone already de-emphasises at ≥4.5:1). Four are
byte-identical for every existing document; the dim fix re-blesses each page's
inline stylesheet by one identical delta (`SCRIBA_VERSION` 24). The graph
dark-mode pill and the node-label layout family are deferred to a focused cycle.

</details>

<details>
<summary>v0.28.0 changelog</summary>

## What's new in v0.28.0 — render-quality sweep

**Four families of render defects, found by a numeric sweep and fixed structurally.**
A fleet of hunters rendered realistic + stress documents and measured the emitted
SVG geometry (no browser) to catch places where a primitive painted more than it
reserved. **Coincident markers:** two `\cursor` carets — or a queue's front/rear
pointers — meeting on one cell rendered byte-identical and stacked into a blob;
they now fan apart, and a caret pushes a same-cell `below` pill out of its way.
**Value-width reservation:** a wide `\apply{a.cell[i]}{value=…}` on an `Array` (or a
`Matrix` `show_values` value) clipped the cell because the box never grew to the
painted width — it does now. **The measurement oracle:** `∞ → ≤ √` and friends were
charged a flat 0.62em and under-measured up to 56%, clipping arrow chains; they now
take their true KaTeX advance. **Viewport extent:** a lopsided `Plane2D` domain
collapsed the plot (or blew the viewBox to ~32000px), and a too-tall `\note` spilled
silently off the bottom — both are bounded now, the note warning the new **E1126**.
Six goldens re-bless; every other document is byte-identical (`SCRIBA_VERSION` 23).
The Graph/Tree node-label overflow family is deferred to a focused next cycle.

</details>

<details>
<summary>v0.27.0 changelog</summary>

## What's new in v0.27.0

**Graph nodes can hold a value now.** Shortest-path and traversal editorials label
each node with a number — Dijkstra distances, BFS levels, DSU rank — and until now
the graph was the one substrate that couldn't carry it (authors hand-built a side
array and a node→index mapping). `\apply{g.node[X]}{value=...}` now renders the
value on the node, mirroring how `Tree`/`Forest` already do it (compose `"A:7"` to
keep the name). Byte-identical for every existing document; no version bump.

Plus value-channel hardening from the same research: a non-numeric `value=` on
`Bar`/`Matrix` fails loudly (**E1107**) instead of a silent flip-back, and a couple
of dishonest-manifest edge cases (`Plane2D` point value, invalid-selector
`value=`) are closed.

</details>

<details>
<summary>v0.26.5 changelog</summary>

## What's new in v0.26.5

The two structural classes the report #6/#7 sibling audits surfaced, both closed:
- **Decorations dodge content.** `\group` titles, `\note` callouts and
  `\trace`/`\link` labels were emitted straight onto the canvas, bypassing the
  smart-label placer, so they could sit on top of cells and nodes. Their text now
  routes through the same placement engine annotation pills use (dodging content),
  and lines that can't move register as obstacles so other labels avoid them.
- **`\apply value=` on a value-less part fails loudly.** A Stack item, Graph node,
  NumberLine tick, or CodePanel line renders no per-element value, but `value=` was
  accepted then animated by the runtime and reverted at settle — a flip-back flash
  and a silent no-op. It now raises **E1105** with a steering hint (Graph edges
  keep `value=`).

`SCRIBA_VERSION` 21→22 (one corpus doc's trace label dodged; strokes unchanged).

</details>

<details>
<summary>v0.26.4 changelog</summary>

## What's new in v0.26.4

Two more legibility fixes from the JudgeZone reports, each fixed structurally
(the sibling class swept, not just the reported case):
- **A watch-row label no longer flashes into a number.** `value_change` wrote the
  incoming value onto the FIRST text of the row — the NAME ("j" → "0") — then
  snapped back. The value node is now renderer-tagged (`data-role="value"`) and
  the runtime targets it explicitly; the same bug in HashMap is fixed and
  LinkedList (value-first) is covered by the tag.
- **A bound `\cursor` caret no longer overlaps the index digits.** With
  `labels="0..k"` the caret (▲ + id) drew on top of the index row; it now drops
  below the label lane (reusing the reservation `position=below` pills already
  use). No-label frames are byte-identical.

`SCRIBA_VERSION` 20→21 (the value node's `data-role` attribute is the only SVG
change). Sibling audits flag remaining direct-emit decoration overlaps (`\group`/
`\note`/`\trace`) for a follow-up shared-obstacle pass.

</details>

<details>
<summary>v0.26.3 changelog</summary>

## What's new in v0.26.3

The flagship `\cursor` glide no longer **twitches**. Delta-emphasis (the
transient pulse that flags "this changed" on a step) was double-firing on
elements that already announced their own change through motion — a bound caret
would glide smoothly, then scale-throb, reading as a jolt. The pulse now
**skips the 7 self-announcing motion kinds** (glides/fades/value-bounces) and
keeps firing only on the 4 silent ones (instant colour/state swaps) where it is
the real arrival cue. Runtime-only (`scriba.js`); no SVG/geometry change, the
static zero-JS filmstrip is byte-identical. New motion-ruleset invariant A-9.
`SCRIBA_VERSION` 19→20.

</details>

<details>
<summary>v0.26.2 changelog</summary>

## What's new in v0.26.2

A hardening patch — **no rendered-output change for a valid document**
(`SCRIBA_VERSION` stays 19; the whole 104-example corpus renders byte-identically
to 0.26.1 in interactive and static mode). Closes the **silent-swallow** hazard
class (typo'd or unsupported params that were accepted, dropped, and rendered
clean — an author shipped a frame claiming an update that never happened):
unknown `\apply` params now raise **E1105**, unknown keys on the 9
decoration/stage commands raise **E1123** (with did-you-mean), Tree pairs-form
`nodes=` raises **E1104**, `tex=`+`lines=` raises **E1530**, double `\zoom`
raises **E1124**. Plus adversarial-sweep fixes: strike no longer floats over
hidden cells or recurses on a bare shape, `\note` wraps to the board, `at=`
compacts empty tracks (no more 2,000,000px viewBox), and `\invariant` now prints
in the zero-JS filmstrip. Driven by two full BMAD sweeps (8 hunters). Flagged by
the JudgeZone pipeline: "protect authors at author time, not reader time".

</details>

<details>
<summary>v0.26.1 changelog</summary>

## What's new in v0.26.1

A polish patch on the 0.26.0 "teacher's board" release — **no rendered-output
change** (`SCRIBA_VERSION` stays 19; documents render byte-identically to
0.26.0). Completes the animation error catalog (E1491/E1492/E1183/E1184 added —
an internal registry, no user-facing message change) and sweeps every doc to
0.26.0 reality: 21 primitives, 23 inner commands (`environments.md` §3 now
documents all 23), 9 semantic states, 11 motion kinds, and the phantom `§9.2`
state names purged from the primitive pages.

</details>

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
