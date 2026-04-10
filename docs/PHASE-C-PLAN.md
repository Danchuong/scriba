# Phase C — v0.4.0 Implementation Plan

> **Target:** `Plane2D` (P3) + `MetricPlot` (P4) + `Graph layout=stable` (P5) + `\substory` (E4) + `\fastforward` (E3) + docs site + integration examples.
> **Effort:** ~5 weeks solo, ~3 weeks with 2 engineers.
> **Prerequisite:** v0.3.0 complete (all 8 primitives + DiagramRenderer + interactive widget).
> **Binds to:** [`04-roadmap.md`](04-roadmap.md) §6,
> [`primitives/plane2d.md`](primitives/plane2d.md),
> [`primitives/metricplot.md`](primitives/metricplot.md),
> [`primitives/graph-stable-layout.md`](primitives/graph-stable-layout.md),
> [`extensions/substory.md`](extensions/substory.md),
> [`extensions/fastforward.md`](extensions/fastforward.md).

---

## 1. Phase C scope

| Category | Deliverable | Spec |
|----------|-------------|------|
| Primitive P3 | **Plane2D** — 2D coordinate plane with lines/points/segments/polygons/regions | `primitives/plane2d.md` |
| Primitive P4 | **MetricPlot** — compile-time SVG line chart tracking scalars across frames | `primitives/metricplot.md` |
| Primitive P5 | **Graph layout=stable** — SA joint-optimization for fixed node positions | `primitives/graph-stable-layout.md` |
| Extension E3 | **`\fastforward`** — bulk Starlark iteration with sampled frames | `extensions/fastforward.md` |
| Extension E4 | **`\substory`** — inline nested drilldown frames | `extensions/substory.md` |
| Docs site | Astro Starlight site from `docs/scriba/` | `04-roadmap.md` §6.2 |
| Integration | `examples/plain-html/`, `examples/nextjs/`, `examples/astro/`, `examples/mdbook/` | `04-roadmap.md` §6.2 |
| Cookbook | 9 HARD-TO-DISPLAY editorial rewrites | `cookbook/` |

---

## 2. Priority order

Phase C has 8 deliverables. Ordered by dependency chain and engineering risk.

### Tier 1 — Core infrastructure (required by other deliverables)

| # | Deliverable | Effort | Why first |
|---|-------------|--------|-----------|
| 1 | **`\fastforward` (E3)** | 3 days | Required by MetricPlot + SA demos; touches parser, Starlark host, scene materializer |
| 2 | **`\substory` (E4)** | 2 days | Touches parser + emitter + scene; better to stabilize grammar changes early |

After these: parser extended with 2 new commands, Starlark worker has elevated step cap + seeded RNG.

### Tier 2 — New primitives (independent of each other, parallel-safe)

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 3 | **Plane2D (P3)** | 4 days | Most complex new primitive; geometry helpers, math→SVG transform, 3-layer SVG |
| 4 | **MetricPlot (P4)** | 3 days | Compile-time line chart; depends on `\fastforward` for SA demos |
| 5 | **Graph layout=stable (P5)** | 3 days | SA layout optimizer; pure Python, self-contained |

After these: all 11 primitives/modes working, 9/10 HARD-TO-DISPLAY covered.

### Tier 3 — Docs site + integration + cookbook

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 6 | **Docs site** | 3 days | Astro Starlight from `docs/scriba/`, auto-generated error catalog + primitive reference |
| 7 | **Integration examples** | 2 days | plain-html, nextjs, astro, mdbook |
| 8 | **9 cookbook editorials** | 3 days | One per HARD-TO-DISPLAY problem; real content validation |

### Tier 4 — Verification

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 9 | **Full verification** | 2 days | All tests, axe-core accessibility, render all demos, version bump |

---

## 3. Deliverable specs

### 3.1 `\fastforward` (E3)

**New files:**
- `scriba/animation/extensions/fastforward.py` — parser integration, Starlark iteration loop, snapshot sampling
- `scriba/animation/starlark_rng.py` — seeded RNG object (`random`, `randint`, `uniform`, `shuffle`, `choice`)

**Parser changes:**
- `SceneParser`: add `\fastforward` as 9th inner command alongside `\step`
- Grammar: `fastforward_block ::= "\fastforward" "{" total_iters "}" "{" ff_params "}" ff_narrate_cmd?`
- Expands to N sequential `\step` frames at compile time

**Starlark host changes:**
- Elevated step cap: 10^9 ops (vs 10^8 regular `\compute`)
- `SCRIBA_FASTFORWARD=1` env var for worker
- Inject `rng` object only during `\fastforward` execution
- Call author's `iterate(scene, rng)` function N times
- Snapshot scene dict at every `sample_every` intervals

**Key parameters:**
- `total_iters`: 1 to 10^6 (E1340 if exceeded)
- `sample_every`: >= 1; `floor(total_iters/sample_every)` <= 100 (E1341)
- `seed`: mandatory (E1342)
- `label`: optional, default `"ff"`

**Error codes:** E1340–E1349

### 3.2 `\substory` (E4)

**New files:**
- `scriba/animation/extensions/substory.py` — parser block, scope save/restore, nested frame emitter

**Parser changes:**
- `SceneParser`: add `\substory` / `\endsubstory` as paired commands (10th + 11th)
- Position constraint: only inside a `\step` block
- Max nesting depth: 3 (E1360)

**Scene changes:**
- Substory-local shapes: created at `\substory`, destroyed at `\endsubstory`
- Parent shape state: saved at `\substory`, restored at `\endsubstory`
- Mutations to parent-scope shapes inside substory are ephemeral (E1363 warning)

**Emitter changes:**
- Nested `<section class="scriba-substory">` + `<ol class="scriba-substory-frames">` inside parent `<li>`
- Hierarchical frame IDs: `{scene-id}-frame-{P}-substory-{S}-frame-{F}`
- Substory frames count toward 100-frame budget (E1364)

**CSS additions to `scriba-animation.css`:**
- `.scriba-substory` with left border indent
- Depth-based indent: `data-substory-depth="1|2|3"`
- Print: expand all substories vertically
- Responsive: collapse to vertical at `max-width: 640px`

**Error codes:** E1360–E1369

### 3.3 Plane2D (P3)

**New files:**
- `scriba/animation/primitives/plane2d.py` — Plane2D primitive class
- `scriba/animation/primitives/plane2d_compute.py` — geometry helpers for Starlark
- `scriba/animation/static/scriba-plane2d.css` — plane-specific styles

**Architecture — 3-layer SVG:**
1. **Grid/axes layer** — in SVG coords directly (no transform)
2. **Geometric content layer** — `<g class="scriba-plane-content" transform="translate(tx,ty) scale(sx,sy)">` — math→SVG transform with Y-flip
3. **Text labels layer** — in SVG coords (outside transform to avoid upside-down text)

**Math→SVG transform:**
```
sx =  (width - 2*pad) / (xrange[1] - xrange[0])
sy = -(height - 2*pad) / (yrange[1] - yrange[0])   # negative = Y-flip
tx =  pad + (-xrange[0]) * sx
ty =  (height - pad) + yrange[0] * (height - 2*pad) / (yrange[1] - yrange[0])
```

**Element types:**
- Points: `<circle>` inside transform group; `<text>` label outside
- Lines: clipped to viewport via Liang-Barsky, rendered as `<line>`
- Segments: `<line>` with round caps
- Polygons: `<polygon>` with auto-close
- Regions: `<polygon>` with semi-transparent fill, no stroke

**Apply commands:**
- Modify existing: `\apply{p.line[0]}{slope=1.5, intercept=0.5}`
- Add new: `\apply{p}{add_point=(1,2)}`, `\apply{p}{add_line=(...)}`, etc.
- Element cap: 500 per frame (E1466)

**Starlark helpers (plane2d namespace):**
- `plane2d.intersect(line1, line2)` — line intersection
- `plane2d.cross(a, b, c)` — signed 2D cross product
- `plane2d.hull(points)` — Andrew's monotone chain convex hull
- `plane2d.half_plane(line, point)` — which side of a line
- `plane2d.clip_line_to_viewport(slope, intercept, xrange, yrange)` — viewport clipping
- `plane2d.lower_envelope(lines)` — CHT lower envelope

**Error codes:** E1460–E1469

### 3.4 MetricPlot (P4)

**New files:**
- `scriba/animation/primitives/metricplot.py` — MetricPlot primitive class
- `scriba/animation/static/scriba-metricplot.css` — chart styles + `@media print` overrides

**Key features:**
- Per-frame SVG line chart: data accumulates via `\apply{plot}{phi=3.2, cost=5.1}`
- Up to 8 series with Wong CVD-safe auto-colors + distinct dash patterns for print
- Auto or explicit axis ranges with 10% padding
- Per-series `scale="linear"|"log"` and `axis="left"|"right"` (two-axis mode)
- Current-step vertical marker with circle dots
- Legend at top-right (or below chart if overflow)
- `\fastforward` integration: reads series keys from scene dict snapshots

**Data mapping:**
```python
svg_x = pad_left + (x - xmin) / (xmax - xmin) * (W - pad_left - pad_right)
svg_y = (H - pad_bottom) - (y - ymin) / (ymax - ymin) * (H - pad_top - pad_bottom)
```

**Series color table (Wong palette):**

| Idx | Color | Hex | Dash |
|-----|-------|-----|------|
| 0 | Blue | #0072B2 | solid |
| 1 | Vermillion | #D55E00 | 6 3 |
| 2 | Green | #009E73 | 2 2 |
| 3 | Yellow | #F0E442 | 8 3 2 3 |
| 4 | Sky blue | #56B4E9 | 4 2 4 2 |
| 5 | Orange | #E69F00 | 10 4 |
| 6 | Bluish-green | #009E73 | 2 4 |
| 7 | Black | #000000 | 6 2 2 2 |

**Error codes:** E1480–E1489

### 3.5 Graph layout=stable (P5)

**New files:**
- `scriba/animation/primitives/graph_layout_stable.py` — SA optimizer

**Algorithm — Joint SA across all frames:**
1. Input: nodes V, per-frame edge sets E_0..E_T
2. Decision variables: node positions {(x_i, y_i)} in [0,1]^2
3. Objective: `O = sum_t[edge_crossings(E_t)] + lambda * sum_edges[distance_penalty]`
4. SA schedule: T0=10, alpha=0.97, 200 iterations, seeded PRNG
5. Denormalize to SVG coords after convergence

**Integration:**
- Computed ONCE during scene materialization (before SVG emission)
- Positions stored in Graph node registry, shared by all frames
- SVG emitter reads from registry — no per-frame recomputation
- `data-layout="stable"` attribute on root `<svg>`

**Fallback guards:**
- N > 20 nodes → E1501 + E1503 → fallback to `layout="force"`
- T > 50 frames → E1502 + E1503 → fallback to `layout="force"`

**Cache key:**
```python
cache_key = sha256(json.dumps({
    "nodes": sorted(nodes),
    "frames": [sorted(frame.edges) for frame in scene.frames],
    "layout_lambda": 0.3,
    "layout_seed": 42,
    "version": 1
}))
```
Note: cache key uses **ordered list of per-frame edge sets**, NOT union of all edges.

**Error codes:** E1500–E1509

---

## 4. Wave plan

### Wave C1 — 2 agents parallel (Tier 1: grammar extensions)

| Agent | Scope | Files | Effort |
|-------|-------|-------|--------|
| **fastforward** | `\fastforward` parser + Starlark iteration + RNG + snapshot sampling + tests | `extensions/fastforward.py`, `starlark_rng.py`, `parser/grammar.py` (delta), `tests/` | 3 days |
| **substory** | `\substory` parser + scope save/restore + nested emitter + CSS + tests | `extensions/substory.py`, `parser/grammar.py` (delta), `emitter.py` (delta), `scriba-animation.css` (delta), `tests/` | 2 days |

### Wave C2 — 3 agents parallel (Tier 2: new primitives)

| Agent | Scope | Files | Effort |
|-------|-------|-------|--------|
| **plane2d** | Plane2D primitive + geometry helpers + CSS + tests | `primitives/plane2d.py`, `primitives/plane2d_compute.py`, `static/scriba-plane2d.css`, `tests/` | 4 days |
| **metricplot** | MetricPlot primitive + CSS + tests | `primitives/metricplot.py`, `static/scriba-metricplot.css`, `tests/` | 3 days |
| **graph-stable** | SA optimizer + cache + Graph integration + tests | `primitives/graph_layout_stable.py`, `primitives/graph.py` (delta), `tests/` | 3 days |

### Wave C3 — 2 agents parallel (Tier 3: docs + integration)

| Agent | Scope | Files | Effort |
|-------|-------|-------|--------|
| **docs-site** | Astro Starlight project, sidebar from docs, error catalog, primitive reference | `docs-site/`, config | 3 days |
| **cookbook** | 9 HARD-TO-DISPLAY editorial .tex files + integration examples | `examples/`, `cookbook/` | 5 days |

### Wave C4 — 1 agent (wiring + verification)

| Agent | Scope |
|-------|-------|
| **verify** | Update PRIMITIVE_CATALOG (add Plane2D, MetricPlot), update PRIMITIVE_CATALOG layout dispatch for "stable", register fastforward/substory in parser, run all tests, render all demos, axe-core audit, version bump, verification report |

---

## 5. Key technical challenges

### 5.1 Plane2D — Math→SVG coordinate transform

The Y-flip (`scale(sx, -sy)`) means:
- All geometric shapes go INSIDE the transformed `<g>` group
- All `<text>` labels go OUTSIDE (in a separate `<g class="scriba-plane-labels">`)
- Label SVG positions are computed from math coords via `math_to_svg()` helper

Must test: point at origin, point at extreme corners, text not upside-down.

### 5.2 Graph layout=stable — SA quality

Risk: node overlap or bad aspect ratio with 200 iterations on N=20.

Mitigation:
- Seed sweep test: run SA with seeds 1–100, assert no node overlap (min distance > 2*radius)
- Visual regression suite for N=6, N=12, N=20
- Expose `layout_lambda` knob for authors to tune

### 5.3 `\fastforward` — Starlark worker elevated limits

Risk: 10^6 iterations hitting 5s wall clock.

Mitigation:
- Profile peak RSS at N=10^4 iterations
- Test that Starlark step cap of 10^9 is sufficient for simple iterate() callbacks
- Verify determinism: same seed + same source = byte-identical HTML

### 5.4 `\substory` — Scope isolation

Risk: substory mutations leaking to parent scope.

Mitigation:
- Deep-copy parent scene state at `\substory` open
- Restore at `\endsubstory`
- Test: parent shape state unchanged after substory with mutations

---

## 6. Exit criteria

- [ ] `Plane2D` renders Li Chao lower-envelope (HARD-TO-DISPLAY #6) with correct geometry
- [ ] `MetricPlot` overlays phi/cost curves across a Splay Tree animation (HARD-TO-DISPLAY #7)
- [ ] `Graph layout=stable` holds node positions fixed across 10-augmentation MCMF (HARD-TO-DISPLAY #5)
- [ ] `\substory` renders as nested `<ol>` inside parent frame; no JS
- [ ] `\fastforward{1000}{sample_every=33, seed=42}` produces exactly 30 frames; deterministic
- [ ] Docs site deployed with search, versioned sidebar, dark/light toggle
- [ ] Each integration example has working Playwright smoke test
- [ ] All 9 HARD-TO-DISPLAY cookbook editorials build and pass axe-core
- [ ] `README.md` passes `markdown-link-check`
- [ ] All tests passing; no CRITICAL/HIGH from code review
- [ ] Version bumped to `0.4.0`

---

## 7. Test budget

| Category | Count | Location |
|----------|-------|----------|
| `\fastforward` parser + expansion | ~15 | `tests/unit/test_fastforward.py` |
| `\fastforward` Starlark iteration | ~10 | `tests/integration/test_fastforward_starlark.py` |
| Seeded RNG | ~8 | `tests/unit/test_starlark_rng.py` |
| `\substory` parser + scope | ~15 | `tests/unit/test_substory.py` |
| `\substory` HTML output | ~8 | `tests/integration/test_substory_html.py` |
| Plane2D primitive | ~20 | `tests/unit/test_primitive_plane2d.py` |
| Plane2D geometry helpers | ~15 | `tests/unit/test_plane2d_compute.py` |
| MetricPlot primitive | ~15 | `tests/unit/test_primitive_metricplot.py` |
| Graph layout=stable SA | ~12 | `tests/unit/test_graph_layout_stable.py` |
| Graph stable cache key | ~5 | `tests/unit/test_graph_stable_cache.py` |
| Cookbook E2E | ~9 | `tests/integration/test_cookbook_hard_to_display.py` |
| Docs site smoke | ~3 | `tests/e2e/test_docs_site.py` |
| Integration examples | ~4 | `tests/e2e/test_integration_examples.py` |
| **Total new** | **~139** | |

---

## 8. Version changes

| Field | Before (v0.3.0) | After (v0.4.0) |
|-------|-----------------|----------------|
| `__version__` | `"0.3.0"` | `"0.4.0"` |
| `SCRIBA_VERSION` | `2` | `2` (unchanged) |
| `AnimationRenderer.version` | `1` | `1` (unchanged) |
| `DiagramRenderer.version` | `1` | `1` (unchanged) |
| Primitives/modes | 8 types | 10 types (+ Plane2D, MetricPlot) + 1 layout mode (stable) |
| Inner commands | 8 | 11 (+ `\fastforward`, `\substory`, `\endsubstory`) |
| Error code ranges | E1001–E1299, E1420–E1449 | + E1340–E1349, E1360–E1369, E1460–E1469, E1480–E1489, E1500–E1509 |

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| SA layout quality (node overlap, bad aspect) | **High** | Seed sweep + visual regression; expose `layout_lambda` knob |
| SA cache key collision (same union, different frames) | **High** | Cache key hashes ordered per-frame edge sets, NOT union |
| `\fastforward` 10^6 iters hitting 5s wall clock | Medium | Profile; most CP iterate() callbacks are O(N) with N<=100 |
| Plane2D SVG size with N>=30 lines | Medium | Clip to viewport; de-duplicate axis SVG via `<use>` |
| `\substory` scope leak (mutations persist) | Medium | Deep-copy + restore; comprehensive scope isolation tests |
| Phase C scope (5 weeks solo) | Medium | If SA stalls, ship as `layout="stable-beta"`. Split: eng-1 primitives, eng-2 docs+cookbook |
| Docs site Astro build complexity | Low | Use Starlight starter template; minimal customization |

---

## 10. HARD-TO-DISPLAY coverage after Phase C

| # | Problem | Primitive(s) | Status |
|---|---------|-------------|--------|
| 1 | Zuma interval DP | DPTable + Array + `\substory` | **Covered** (Phase C) |
| 2 | DP optimization trick | DPTable + NumberLine | Covered (Phase B) |
| 3 | 4D Knapsack | — | **Partial** (cognitive limit, documented) |
| 4 | FFT butterfly | Plane2D + `@keyframes` | **Covered** (Phase C) |
| 5 | MCMF dense graph | Graph layout=stable + Matrix | **Covered** (Phase C) |
| 6 | Li Chao / CHT | Plane2D + geometry helpers | **Covered** (Phase C) |
| 7 | Splay amortized | Tree + MetricPlot | **Covered** (Phase C) |
| 8 | Persistent segtree | Tree (segtree) | Covered (Phase B) |
| 9 | Simulated Annealing | Graph + MetricPlot + `\fastforward` | **Covered** (Phase C) |
| 10 | Heavy-Light Decomposition | Tree + Array | Covered (Phase B) |

**9/10 covered after Phase C** (Problem #3 documented as partial).

---

## 11. Cross-references

| Document | Relationship |
|----------|--------------|
| [`04-roadmap.md`](04-roadmap.md) §6 | Phase C milestone |
| [`primitives/plane2d.md`](primitives/plane2d.md) | P3 spec |
| [`primitives/metricplot.md`](primitives/metricplot.md) | P4 spec |
| [`primitives/graph-stable-layout.md`](primitives/graph-stable-layout.md) | P5 spec |
| [`extensions/fastforward.md`](extensions/fastforward.md) | E3 spec |
| [`extensions/substory.md`](extensions/substory.md) | E4 spec |
| [`PHASE-A-PLAN.md`](PHASE-A-PLAN.md) | Phase A (predecessor) |
| [`PHASE-B-PLAN.md`](PHASE-B-PLAN.md) | Phase B (predecessor) |
