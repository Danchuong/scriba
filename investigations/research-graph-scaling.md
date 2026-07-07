# Research — Graph Force-Layout Canvas Scaling (structural design)

**Status:** Concluded · Implementation-ready · **Discipline:** bmad-investigate (structural design)
**Repo:** scriba @ `__version__` 0.29.0 / `SCRIBA_VERSION` 24 (`scriba/_version.py:3,6`)
**Scope:** `scriba/animation/primitives/graph.py` force (Fruchterman-Reingold) layout — the fixed
400×300 canvas that overlaps nodes at scale (hunt2-stress.md D2). READ-ONLY research; no source edited.

---

## Hand-off Brief (15-second read)

The force layout solves and clamps every graph into a **hard-coded 400×300 canvas** (`graph.py:986-987`,
passed unchanged into `fruchterman_reingold` at `:1087-1130`). Fruchterman-Reingold's ideal spacing is
`k = √(area/n)` (`:592`); with `area` fixed, `k` collapses as `n` grows — at N=100 `k=34.6 < min_sep=36`
(`:651`), so nodes physically cannot fit and `_resolve_overlaps` (`:452-500`) just oscillates against the
clamp, leaving coincident nodes. **Tree solves this by growing its canvas with node count**
(`tree.py:198-199`). The fix ports that pattern: size the force canvas by **area per node**
(`area = max(400·300, 6300·N)`, 4:3 aspect preserved), floored at the default so small graphs stay
byte-identical, then relax the overlap post-pass to convergence. Probe-verified: **0 overlaps / 0
coincident at N=40 and N=100** across ring/dense/grid/tree topologies, **byte-identical ≤ N=19**, and — because
every force-graph golden in the corpus is **≤ 9 nodes** (the only N>9 are two `E1501` reject tests) — the
**golden blast is 0 re-bless**. R-32 pin-stability is preserved for free: positions and canvas are computed
once in `__init__` and no mutation re-solves (`:1304-1309`, `:1320-1321`, `:1342`).

**Implementation-ready. No spike needed.** One constant, one helper, one grow-line, one resolve-passes knob.

---

## 1. Current force-layout pipeline (Confirmed, path:line)

### 1.1 The mechanism that pins the canvas at 400×300

| Fact | Site | Value |
|---|---|---|
| Canvas constants | `graph.py:60-61` | `_DEFAULT_WIDTH=400`, `_DEFAULT_HEIGHT=300` |
| Instance canvas set to defaults | `graph.py:986-987` | `self.width=_DEFAULT_WIDTH; self.height=_DEFAULT_HEIGHT` |
| Node radius (shrinks with N, floors at 12) | `graph.py:990-996` | `max(12, min(20, int(min(w,h)/(2·N))))` — density measure, computed from the **default** box |
| FR called with the fixed canvas | `graph.py:1087-1099` (pinned seed), `:1100-1130` (auto-seed sweep) | `fruchterman_reingold(..., width=self.width, height=self.height, ...)` |
| Ideal inter-node distance | `graph.py:592-593` | `area=width*height; k=√(area/n)` — **area never grows ⇒ k collapses with n** |
| Iteration clamp | `graph.py:641-642` | `new_x∈[_PADDING, width-_PADDING]`, `new_y∈[_PADDING, solve_max_y]` |
| Collision separation | `graph.py:651` | `min_sep = 2·node_radius + _NODE_OVERLAP_GAP` = `2·12+12 = 36` at scale |
| Overlap post-pass (10 passes, clamped) | `graph.py:452-500`, called `:652` | pushes pairs `< min_sep` apart, re-clamped to the box; **early-exits when a pass moves nothing** (`:499-500`) |

**Why it overlaps (Confirmed, probe `probe_overlap.py`):** at fixed 400×300, `k/min_sep` falls below 1 as N
grows and `_resolve_overlaps` cannot separate nodes without violating the clamp:

| N | canvas | k | k/min_sep | overlap pairs | coincident |
|--:|--|--:|--:|--:|--:|
| 8 | 400×300 | 122.5 | 2.55 | 0 | 0 |
| 25 | 400×300 | 69.3 | 1.92 | 0 | 0 |
| 40 | 400×300 | 54.8 | 1.52 | 3 | 0 |
| 50 | 400×300 | 49.0 | 1.36 | 6 | 0 |
| 75 | 400×300 | 40.0 | 1.11 | 33 | **2** |
| 100 | 400×300 | 34.6 | **0.96** | 93 | **2** |

(Absolute counts differ from hunt2-stress.md's 112/5 at N=100 because the probe uses a ring+chords
generator vs the stress harness's; the **regime matches** — clean ≤25, onset at 40, coincident at 75+.)

### 1.2 R-32 / A1 pin-stability (Confirmed — positions solved ONCE, never re-solved)

- Positions computed once in `__init__` (`graph.py:1005-1130`); the node set is immutable (no
  `add_node`/`remove_node`).
- `_add_edge_internal` (`:1285-1309`) appends an edge, invalidates the addressable cache, and **does not
  move any node** — explicit A1 comment `:1304-1309`.
- `_remove_edge_internal` (`:1311-1321`) pops an edge, **no re-solve** (`:1320-1321`).
- `_set_weight_internal` (`:1323-1342`) — "No relayout" (`:1342`).

Consequence: whatever canvas/positions `__init__` produces are frozen for the primitive's life. The fix
runs entirely inside `__init__`, so R-32 holds **by construction** (proof in §4).

### 1.3 How the viewBox derives from the canvas (Confirmed — the coupling that makes the fix work)

- `bounding_box()` is a **pure function of `self.width/height/r`**: `content_w = self.width + 2·r`
  (`graph.py:1548`), `height = self.height + 2·r + …` (`:1561`).
- The scene viewBox is the **max `bounding_box()` across frames** (`_frame_renderer.py:438`
  `_compute_viewbox`, reads `prim.bounding_box()` at `:462/:545`, max-extent at `:732`).
- Node x∈`[_PADDING, self.width-_PADDING]` ⇒ circle right edge ≤ `self.width+2r-_PADDING < content_w` ⇒
  **painted ⊆ viewBox** holds at any canvas size (Deduced from the clamp bounds + the formula).

So **growing `self.width/self.height` automatically grows the viewBox and keeps content inside it** — no
separate viewBox edit is required. This is the same `self.width/self.height` the node-label-overflow fix
keys off (bmad-rq-nodefit.md B1/A1), i.e. the two fixes share one substrate.

### 1.4 Seed selection & isolated lane (must be preserved)

- Auto-seed sweep (`graph.py:1100-1130`): when no seed is pinned, tries `_AUTO_SEED_COUNT=8` seeds, scores
  each with `score_layout`, keeps lowest `(score, seed)`.
- `score_layout` (`graph_layout_score.py:82-172`) is **canvas-relative**: `border_margin` (`:139`) and
  `canvas_area` (`:162`) normalize against the passed `width/height`, so scoring stays meaningful when the
  canvas grows.
- Isolated (degree-0) nodes are excluded from the solve and placed in a reserved bottom lane
  (`graph.py:503-533`, `:561-590`); `solve_max_y` reserves `_ISOLATED_LANE_BAND` (`:159`, `:588-590`).
  A grown height widens both the connected region and the lane — no special handling needed.

---

## 2. Tree — the reference pattern (Confirmed, `tree.py`)

```
node_count = len(self.nodes)                                              # tree.py:196
depth      = self._compute_max_depth()                                    # tree.py:197
self.width  = max(_DEFAULT_WIDTH,  node_count * _MIN_H_GAP + 2*_PADDING)  # tree.py:198
self.height = max(_DEFAULT_HEIGHT, (depth + 1) * _LAYER_GAP + 2*_PADDING) # tree.py:199
self._node_radius = max(12, min(20, int(min(self.width,self.height)/(2*N)))) # tree.py:202-208 (AFTER grow)
```

**Transferable pattern:** canvas = `max(default, <grows-with-node-count>)`, floored at the default so
small trees stay unchanged; positions solved in the grown box. hunt2-stress.md confirms it is robust
(127-node binary tree, minGap 86 px, 0 overlap).

**Why Graph must differ from Tree literally:** Tree lays out in 1-D rows (width ∝ leaf count, height ∝
depth), so it scales each axis independently. Force layout is **2-D isotropic** — nodes fill area, not a
row — so Graph must scale **area** (both axes together, aspect preserved), not a single linear dimension.

**Precedent inside graph.py itself:** the hierarchical branch **already grows the canvas** after laying
out (`graph.py:1073-1084`: `self.width = max(self.width, int(max_x+pad))`). The force branch is the only
layout that never grows. The fix makes force consistent with both Tree and Graph-hierarchical.

---

## 3. Structural design (implementation-ready)

### 3.1 Canvas-size formula

```python
# graph.py, constants block (near :66)
_FR_AREA_PER_NODE = 6300   # px² of canvas per node for the force layout.
# Force nodes fill AREA, so the canvas must scale with N to hold them above the
# collision separation. 6300 is stress-calibrated: N=25 ran overlap-free at
# 120000/25 = 4800 px²/node (hunt2-stress.md), and 6300 adds ~1.3x margin for
# clustered topologies (trees/bipartite). Below N≈20 the max() floor makes this
# INERT (canvas stays 400x300) so existing graphs are byte-identical.
_FR_RESOLVE_PASSES = 10    # names the current graph.py:458 default (keeps the guard readable)
```

```python
# graph.py, new module-level helper (near map_manual_positions, ~:708)
def _grow_force_canvas(n: int) -> tuple[int, int]:
    """Force-layout canvas sized so N nodes never pack below the collision
    separation. Area scales with node count; the 4:3 default aspect ratio is
    preserved; floored at the default so small graphs stay byte-identical
    (mirrors Tree's max()-floored grow, tree.py:198-199)."""
    default_area = _DEFAULT_WIDTH * _DEFAULT_HEIGHT
    area = max(default_area, _FR_AREA_PER_NODE * n)
    aspect = _DEFAULT_WIDTH / _DEFAULT_HEIGHT          # 4:3
    w = max(_DEFAULT_WIDTH,  round(math.sqrt(area * aspect)))
    h = max(_DEFAULT_HEIGHT, round(math.sqrt(area / aspect)))
    return w, h
```

Grown sizes (probe `probe_final.py` §A): N=19→400×300 (inert), N=20→410×307, N=40→580×435,
N=100→917×687.

### 3.2 Exact edit sites

| # | Site | Change |
|---|------|--------|
| E1 | `graph.py:~66` (constants) | add `_FR_AREA_PER_NODE = 6300`, `_FR_RESOLVE_PASSES = 10` |
| E2 | `graph.py:~708` (helpers) | add `_grow_force_canvas(n)` (above) |
| E3 | `graph.py:1087` (immediately **before** `fr_edges = …`) | insert the grow — see below |
| E4 | `graph.py:536-545` (`fruchterman_reingold` signature) + `:652` | add `passes: int = _FR_RESOLVE_PASSES`, forward to `_resolve_overlaps(..., passes=passes)` (default keeps every existing caller byte-identical) |
| E5 | `graph.py:1092-1098` and `:1110-1116` (the FR calls) | pass `passes=_overlap_passes` |

```python
# E3 — graph.py:1087, before "fr_edges = ...". All of manual (returns :1009),
# stable (:1032), hierarchical (:1084) have already returned by here, so
# self.width/height are still the defaults and self._node_radius was already
# computed from the default box (:990-996) — the glyph stays fixed; only the
# spacing and viewBox grow (matches bmad-rq-nodefit.md: do NOT change radius).
self.width, self.height = _grow_force_canvas(len(self.nodes))
_grew = (self.width, self.height) != (_DEFAULT_WIDTH, _DEFAULT_HEIGHT)
# Relax the overlap post-pass to convergence only when the canvas grew; the
# 10-pass cap oscillates on dense clusters at scale (see §3.4). Gated on _grew
# so byte output is untouched below threshold.
_overlap_passes = max(_FR_RESOLVE_PASSES, len(self.nodes)) if _grew else _FR_RESOLVE_PASSES
```

### 3.3 Why the FR simulation is NOT re-clamped (the core of the fix)

`fruchterman_reingold` already takes `width`/`height` and threads them consistently through **every**
box-dependent step: `k=√(area/n)` (`:592`), random init (`:596-600`), the iteration clamp (`:641-642`),
and `_resolve_overlaps` (`:652`). Passing the **grown** dimensions means `k` grows back to its known-good
value (√(6300)≈79 for all grown N, vs 34.6 at N=100 today), the init spreads wider, and every clamp
widens in lockstep. **No internal change to `fruchterman_reingold` is needed beyond the `passes`
forward** — the caller supplying a bigger box is the entire mechanism. This is exactly why Tree/hierarchical
work: they solve in a box already sized for the content.

### 3.4 The second knob — resolve to convergence (Confirmed necessary at N≥75)

Growing the canvas alone (native 10 passes) drops N=100 from 93 overlaps/2 coincident to **2 overlaps/0
coincident** — the catastrophic regime is gone, but a handful of near-touches remain because
`_resolve_overlaps` runs only 10 passes and dense clusters need more relaxation (residual pairs are
`< 2r=24`, i.e. resolve never reached even the collision line, let alone the 36 target). Raising the pass
budget to `max(10, N)` clears them (probe `probe_final.py` §C): **0/0 at N=40 and N=100 for
ring+chords, dense (3·E edges), grid, and tree.**

Raising the cap is **byte-safe for small graphs**: `_resolve_overlaps` early-exits the instant a pass
moves nothing (`graph.py:499-500`), and the gate `if _grew` keeps `_overlap_passes = 10` whenever the
canvas is inert. Probe `probe_final.py` §B confirms passes=10 vs passes=200 give **identical** positions
for N=9 and N=25 graphs.

> **Pathological note (honest):** a degenerate 97-leaves-on-3-hubs star at N=100 retains ~6 near-touches
> at `_FR_AREA_PER_NODE=6300` because FR piles all leaves onto their hub; `7500` clears it (probe
> `probe_conv2.py`). Such stars are absent from CP editorials. The constant is a single tunable — raise it
> if a RED test adopts such a topology. **No configuration ever regressed to a *coincident* node** — the
> 0.0-distance catastrophe is fully eliminated at any grown size.

### 3.5 Perf at the 100-node cap + optional refinement

Auto-seed at N=100 with E1-E5 (heavy resolve inside all 8 candidates): **~2.7 s** (probe `probe_final.py`
§D). Real graphs (≤9 nodes) are `_grew=False` → passes=10 → **unchanged** (<50 ms). Pinned-seed N=100 skips
the sweep (1 FR + 1 resolve) → ~0.4 s. 2.7 s is a one-time cost at the absolute `_MAX_NODES=100` cap, which
is already documented as expensive (`graph.py:133-145` DoS note).

**Optional perf refinement (validated, ~1.5 s):** the 8-seed sweep selects by `score_layout`, which
**ignores overlaps** — so resolving all 8 candidates is wasted work. Decouple: run the sweep at native 10
passes (selection byte-unchanged), then apply **one** heavy `_resolve_overlaps(winner_connected,
passes=max(10,N))` on the winning layout, gated on `_grew`. Probe `probe_decouple.py`: 0/0 at N=40/100,
N=100 down to ~1.5 s. Prefer E1-E5 (surgical: one param) unless the cap-case latency matters; the decoupled
form is the logically-cleaner structure.

---

## 4. R-32 + byte proof, threshold, golden blast

### 4.1 R-32 pin-stability (preserved by construction)

- **Across edge mutations:** the grow and the solve both run once in `__init__` (E3 sits inside it); no
  mutation path touches `self.width/height` or `self.positions` (`graph.py:1304-1309`, `:1320-1321`,
  `:1342`). So positions are identical before/after any `add_edge`/`remove_edge`. RED test in §6.
- **Across frames:** `bounding_box()` is a pure function of the (now frozen) `self.width/height/r`
  (`:1548/:1561`), so the per-frame viewBox is invariant — the grown canvas does not wobble frame to frame.

### 4.2 Byte-identity below threshold (provable)

For `n` with `6300·n ≤ 120000` ⇒ `_grow_force_canvas` returns exactly `(400,300)` (the `max()` floor) and
`_grew=False` ⇒ `_overlap_passes=10`. Every FR argument is then identical to today ⇒ **byte-identical
output**. Threshold: `6300·n > 120000 ⇔ n ≥ 20`. So:

- **N ≤ 19 → byte-identical** (canvas 400×300, passes 10, same seed sweep, same positions).
- **N ≥ 20 → bytes change** (grown canvas + convergent resolve).

(With the tighter `_FR_AREA_PER_NODE=4800` the threshold is N≥26; 6300 is recommended for topology margin.)

### 4.3 Golden blast estimate — **0 re-bless** (corpus-scanned)

`scan_goldens.py` parsed **640 `.tex`** across `tests/` + `examples/` → 112 Graph shapes, 74 on the
force/auto path (no manual `positions`). Node-count distribution of those 74:

```
N:  0  1  2  3  4  5  6  7  9 | 101
   ─────────────────────────────────
    2  2 15 26  7  4 10  4  2 |   2
```

The **only** force graphs with N>9 are `neg_E1501_graph_node_cap.tex` and `prim_graph_over100_E1501.tex`
(N=101) — **negative tests that assert `E1501` rejects the graph before any layout runs** (`graph.py:828-839`).
They are unaffected by a layout change. **Every force-graph golden that actually renders is ≤ 9 nodes**, far
below the N=20 threshold ⇒ **zero goldens re-bless**. The fix is inert on the entire shipped corpus and
engages only for new, large graphs.

### 4.4 SCRIBA_VERSION / `__version__`

No existing golden changes bytes, but the **rendered-output function changes for N≥20 inputs**. Per the
project's byte-shape rule (`_version.py:1` "Bumped on HTML output shape changes"; every prior geometry
change bumped `SCRIBA_VERSION`), recommend **`SCRIBA_VERSION` 24 → 25** and `__version__` MINOR bump
(0.29.0 → 0.30.0; additive layout-geometry, no author-facing API removed). This is a softer case than a
corpus-moving change (nothing re-blesses), but bumping keeps consumer caches correct for large graphs and
is consistent with precedent. If this fix ships **together** with bmad-rq-nodefit (shared `self.width`
substrate), a single combined bump covers both.

---

## 5. Alternatives evaluated & REJECTED

| Alternative | Why rejected |
|---|---|
| **Shrink radius / clamp nodes tighter** | Radius already floors at `_NODE_MIN_RADIUS=12` (`_types.py`); below that, nodes and labels are illegible (bmad-rq-nodefit.md shows labels already overflow at r=12). And it cannot fix coincident nodes: fitting N nodes at *any* r>0 needs area — a packing limit the fixed box violates at N≥~83 regardless of radius. |
| **Raise resolve passes only, no canvas grow** | Physically impossible at fixed 400×300: N=100 has `k=34.6 < min_sep=36`, so there is no room — resolve oscillates against the clamp and leaves coincident nodes (probe: 93/2 unchanged by extra passes). Area is *necessary*; passes are only the secondary polish. |
| **Different layout algo for large N** (grid/circular pack) | Discards FR's edge-aware readability, adds a whole new code path + new goldens + a visual discontinuity at the switchover. Grow-canvas reuses the *proven* FR solver unchanged — far smaller surface. |
| **Grow the node *circle* to fit** | Orthogonal (that is the label-fit concern) and already rejected in bmad-rq-nodefit.md §Fix: growing radius ripples into edge-endpoint math (`_shorten_line_to_circle`), arrow geometry (`:997-999`), group-hull inflate, and cursor/annotation anchoring — plus all goldens. Not this fix's job. |
| **Lower `_MAX_NODES` below the overlap onset (~40)** | Regressive — removes the ability to draw legitimate 40-100-node graphs. `layout="stable"` (cap 20) already exists as the small-graph escape hatch; the request is to make *force* scale, not to forbid it. |
| **Post-hoc uniform rescale of the packed layout** (à la `map_manual_positions`, `:657-707`) | Rescaling a *converged* packed layout preserves the packing *ratios* — overlapping nodes stay overlapping, just bigger. The solve must happen *in* the larger space (bigger `k`) to actually spread. |

---

## 6. RED test specs (all FAIL on 0.29.0)

Location: `tests/unit/test_graph_scaling.py` (new). Assert on `Graph(...).positions` +
`_node_radius` — no browser, no rendering.

1. **`test_force_no_overlap_at_scale[40]` / `[100]`** — build `Graph{g}{nodes=[0..N-1], edges=<ring+chords>}`
   (default force, auto-seed). Assert **min pairwise center distance ≥ 2·g._node_radius** (no circle
   intersection) **and 0 coincident pairs** (`min_dist > 0`). *Today:* N=40 overlaps, N=100 coincident → FAIL.
   *After:* 0/0 → PASS.
2. **`test_small_graph_byte_identical`** — for each of a few ≤9-node corpus graphs (e.g. `graph.tex`,
   `bfs.tex`, `dijkstra.tex`), assert `g.width==400 and g.height==300` and `g.positions` equals a frozen
   snapshot captured on 0.29.0. Guards the inert-below-threshold property. *After:* PASS (unchanged).
3. **`test_positions_stable_across_edge_mutation`** (R-32) — build graph, snapshot `positions`, run
   `apply_command({"add_edge":…})` then `apply_command({"remove_edge":…})`, assert `positions` unchanged.
   Passes today; the test locks that the grow (also `__init__`-only) does not regress it.
4. **`test_grown_canvas_viewbox_contains_nodes`** — at N=40 and N=100, assert every node circle AABB
   `[cx-r, cx+r]×[cy-r, cy+r] ⊆ [0, bounding_box().width]×[0, bounding_box().height]` (painted ⊆ viewBox, no
   clip).
5. **`test_grow_threshold`** — assert `_grow_force_canvas(19)==(400,300)` and `_grow_force_canvas(20)[0]>400`.
   Pins the byte threshold so a future constant change is caught.

---

## 7. Golden-verification strategy (automatable invariant, not eyeballing)

A single parametrized property test over the **whole** graph corpus, replacing manual inspection of
rendered files. For each Graph instance (instantiate from each golden `.tex`; no browser):

- **INV-1 no node-node overlap:** `min` pairwise center distance `≥ 2·_node_radius` ⇒ `overlap_pairs == 0`.
- **INV-2 no coincident nodes:** `min` center distance `> 0`.
- **INV-3 viewBox contains content:** every node circle AABB, every edge endpoint, and every `\group` hull
  extent ⊆ `[0,bounding_box().width]×[0,bounding_box().height]` (the painted ⊆ viewBox honesty invariant
  that hunt2-stress.md confirmed held engine-wide).
- **INV-4 (couples with nodefit):** each node-label painted extent `cx ± tw/2` ⊆ viewBox — enable once
  bmad-rq-nodefit's measured-label reserve lands.

```python
@pytest.mark.parametrize("tex", _all_graph_goldens())   # glob tests/**/**.tex with a Graph shape
def test_graph_golden_invariants(tex):
    for g in graphs_in(tex):
        r = g._node_radius
        pts = list(g.positions.values())
        assert min_pairwise_dist(pts) >= 2*r          # INV-1 + INV-2
        bb = g.bounding_box()
        assert all(0 <= x-r and x+r <= bb.width and 0 <= y-r and y+r <= bb.height
                   for (x, y) in pts)                  # INV-3
```

Because the fix re-blesses **zero** existing goldens, this suite must be **GREEN on the current corpus
both before and after** the change (today's ≤9-node graphs already satisfy INV-1..3). Any future large-N
golden added to the corpus is then held to the same machine-checked bar — no visual review of 100 files.
Also update whatever constant-sync guard covers graph layout constants (bmad-rq-nodefit.md cites
`tests/unit/test_layout_constant_sync.py`) to include `_FR_AREA_PER_NODE`.

---

## 8. Confidence

**HIGH.** Every load-bearing claim is Confirmed against source (`path:line`) or a deterministic probe:
the fixed-canvas defect regime and its `k/min_sep` root cause; R-32 by construction; the viewBox coupling
via `bounding_box`; the Tree/hierarchical grow precedent; byte-inertness below N=20 (canvas `max()` floor +
resolve early-exit, verified identical positions); the 0/0 result at N=40/100 across four topologies; and
the **0-golden-blast** corpus scan (all force-graph goldens ≤9 nodes; the two N=101 files are `E1501`
reject tests). One honestly-flagged residual (pathological hub-stars at N=100 need `_FR_AREA_PER_NODE`
7500), tunable via one constant and never producing a coincident node. Implementation-ready.

**Probes (scratch, reproducible):** `research-graph-scaling/{scan_goldens,probe_overlap,probe_passes,probe_robust,probe_conv2,probe_final,probe_decouple}.py`.
