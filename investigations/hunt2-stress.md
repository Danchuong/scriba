# Hunt 2 — Extreme-Scale Stress (BMAD Render-Quality)

Scope: push every primitive + the animation engine to the size a hard CP
editorial actually hits (well beyond round-1 moderate data) and find where
geometry, viewBox, or output size breaks. All numbers are computed from the
emitted server SVG (transform stack applied), no browser. Render:
`SCRIBA_ALLOW_ANY_OUTPUT=1 .venv/bin/python render.py <p>.tex -o <out>.html`.

## Hand-off Brief

- **2 true defects**, **6 scaling-cost observations**, rest **ROBUST**.
- The renderer's core viewBox-honesty invariant (painted ⊆ viewBox) **held at
  every scale tested** — zero clipping across ~35 cases up to 250,000 cells and
  620,022 px intrinsic width. No NaN / infinite / collapsed viewBox anywhere.
- The two real defects are **primitive-local**, not engine-wide:
  1. **Bar** has no min-height floor → a nonzero value dwarfed by a spike emits
     a literal `height="0.00"` (invisible column).
  2. **Graph force layout** pins its canvas at a fixed 400×300 regardless of node
     count → node overlap onsets at ~40 nodes and produces exactly-coincident
     nodes by 75+. Tree layout (which grows its canvas) is the robust reference.
- The remaining "big" findings are **scaling cost, not correctness**: geometry
  stays valid but a 500×500 grid (the documented cap) emits a **99.9 MB** HTML,
  and a 10,000-cell array yields a **620,022 px**-wide viewBox that exceeds
  browsers' ~32,767 px canvas limit.
- Guardrails that WORK: Array≤10000, Grid/Matrix/DPTable rows*cols≤250000,
  Graph≤100 (force), Hypercube bits≤5, NumberLine ticks≤1000, and a
  **100-frame animation cap (E1181)** that bounds manifest growth.

## Defect table (true rendering-quality defects)

| # | primitive | scale / input | defect | number | severity |
|---|-----------|---------------|--------|--------|----------|
| D1 | **Bar** | 40 cols, one value `100000` among 39×`2` (ratio 5e4:1) | 39/40 columns render `height="0.00"` — nonzero data paints an invisible/zero-area rect; no min-height floor | minCell **0.00 px**, **39** degenerate rects; height set is binary `{0.00, 140.0}` | **MEDIUM** |
| D2 | **Graph** (`layout=force`) | 40 → 100 nodes | force canvas fixed at 400×300 (viewBox 448×348) for *any* node count → nodes pack until centers coincide | onset **40 nodes** (6 overlap pairs); **100 nodes**: **112** overlap pairs, **69/100** nodes overlapping, **5** exactly-coincident pairs (minCenterDist **0.0**) | **HIGH** readability / MEDIUM overall (at/near the 100-node cap; `layout=stable` is the documented escape hatch) |

Evidence:
- **D1** root cause: `scriba/animation/primitives/bar.py:199-214` — `_bar_px_height`
  clamps to `[0, _PLOT_HEIGHT]` with **no lower floor**: `h = (2/100000)*140 =
  0.0028 → "0.00"`. Raw markup: `<rect x="8" y="148.00" width="36"
  height="0.00"/>` ×39. Contrast: **all-equal** 40 bars render fine (all 36 px)
  and a normal 40-col histogram is fine (min bar 2.83 px, visible).
- **D2** root cause: `scriba/animation/primitives/graph.py:60-61`
  (`_DEFAULT_WIDTH=400`, `_DEFAULT_HEIGHT=300`) + `:663-707` (uniform scale into
  the fixed drawable region). Node radius floors at 12 px, so density scales
  linearly into a non-growing box. Onset curve (fixed 448×348 throughout):

  | nodes | minCenterDist px | overlap pairs | nodes overlapping | coincident pairs |
  |------:|-----------------:|--------------:|------------------:|-----------------:|
  | 8 (K8) | 70.3 | 0 | 0 | 0 |
  | 25 | 52.0 | 0 | 0 | 0 |
  | 40 | 14.0 | 6 | 12 | 0 |
  | 50 | 2.0 | 16 | 26 | 0 |
  | 75 | 0.0 | 92 | 64 | 6 |
  | 100 | 0.0 | 112 | 69 | 5 |

## Scaling-cost table (geometry valid — no clip; output-size / dimension cost)

| primitive | scale | viewBox (px) | render | HTML | note |
|-----------|-------|--------------|-------:|-----:|------|
| Grid / DPTable | 500×500 = 250k cells (**CAP**) | 31022×21022 | 5.38 s | **99.9 MB** | catastrophic byte size; geometry valid, cells 60×38 |
| Matrix | 500×500 = 250k (**CAP**) | 12523×12523 | 4.87 s | **74.6 MB** | 25 px cells; valid, no clip |
| Grid / DPTable | 200×200 = 40k | 12422×8422 | 0.65 s | 15.8 MB | >5 MB flag |
| Array | 10000 (**CAP**) | **620022**×64 | 0.31 s | 4.2 MB | intrinsic width ≫ browser ~32,767 px canvas cap |
| Array | 5000 | 310022×64 | 0.27 s | 2.3 MB | — |
| NumberLine | 1000 ticks (**CAP**) | **40064**×80 | 0.41 s | 916 KB | intrinsic width ≫ 32,767 px |
| Animation (sort) | 100 frames (**CAP** E1181) | 1262×64 (invariant) | 2.1 s | 1.3 MB | ~13 KB/frame; 200 frames rejected |
| Animation (BFS) | 60 frames, 8×8 grid | 518×358 (invariant) | 1.6 s | 2.0 MB | 120 SVGs, frame 60 correct |

Ladder (bytes scale ~linearly with cell count; render CPU is cheap, byte size is
the bottleneck): Grid/DPTable 50²=1.4 MB → 100²=4.3 MB → 200²=15.8 MB → 500²=99.9 MB.
Array 40=498 KB → 1000=852 KB → 5000=2.3 MB → 10000=4.2 MB.

Baseline floor is ~380 KB (inlined KaTeX CSS+fonts) present in every file; the
SVG payload is the part that scales.

## Robust at extreme scale (zero clip, zero degeneracy, zero overlap)

- **Tree** — complete binary **127 nodes** (vb 6458×528, minGap 86 px), **40-ary
  flat** (vb 2158×348, minGap 52 px), **depth-25 caterpillar** (vb 1424×1684,
  minGap 62 px). Canvas **grows with node count** → never overlaps. This is the
  model the graph force layout should follow.
- **Hypercube** bits=5 / 32-node fully-populated lattice — vb 584×422, minGap 56 px.
- **Matrix / Grid / DPTable cell geometry** — cells stay non-degenerate (38 px /
  22 px) and never clip, even at 250k cells; only the byte size grows.
- **Array** cell geometry — 38 px cells all the way to 10,000.
- **LinkedList 30 / HashMap 30 / Stack 25 / NumberLine** — non-degenerate at scale.
- **Bar** — normal 40-col and **all-equal 40** (all 36 px) are fine; only the
  spike-ratio input breaks it (D1).
- **Graph ≤25 nodes + K8** — force layout converges cleanly (minGap 52–70 px);
  K8's 28 edges cross heavily but that is inherent to a non-planar complete graph,
  not a layout defect (node positions are clean).
- **Long animations** — viewBox is **invariant across all frames**; frame 100 /
  frame 60 render correctly (0 degenerate, 0 NaN); the 100-frame cap (E1181)
  bounds manifest growth (200-step input correctly rejected).
- **viewBox honesty** — painted ⊆ viewBox held on **every** case (worst "clip"
  was −12 to −56 px, i.e. always inside with margin).

## Conclusion + Confidence

At extreme scale the scriba engine is **geometrically sound**: the viewBox
never runs away, collapses, or clips, and cell/node primitives stay
non-degenerate — the caps and the 100-frame limit hold. The two genuine defects
are localized primitive-layout issues:

1. **Bar** needs a min-height floor so a nonzero value never paints a 0 px column
   (`bar.py:199-214`).
2. **Graph force layout** needs a canvas that scales with node count (like Tree)
   or a radius/spacing that shrinks further; today it overlaps from ~40 nodes and
   coincides at ≥75 while still under its own 100-node cap (`graph.py:60-61`,
   `:663-707`).

The scaling-cost items (99.9 MB grid, 620k-px array width) are within documented
caps but a real hard editorial could hit them; worth a soft advisory or a
tighter practical cap, but not correctness bugs.

**Confidence: High.** Every number is derived from the emitted SVG geometry via
a transform-aware parser; both defects are reproduced with raw markup and traced
to specific source lines. Overlap onset was bisected (25→40→50→75→100). Scaling
ladder measured at 8 points. Only unmeasured axis: true browser rendering of the
620k-px / 99.9 MB outputs (out of scope — no browser), asserted from the numeric
intrinsic dimensions vs. the well-known ~32,767 px engine limit.
