# Case: FP-2 — isolated placement registries (content labels vs annotation pills)

> **STATUS: CLOSED 2026-07-03** — Plane2D unified `register_decorations` + content rects; Graph exposes nodes/weight pills (0d20670). Overlap repro: NONE. Guard: `tests/unit/test_content_label_registry.py`.

> **STATUS: OPEN (design)** — 2026-07-03. Structural-fix research only; no source
> touched. Confirmed user-facing bug (browser-measured): Plane2D point-label vs
> line-label overlap **11.0 × 9.0 px**. Lint E1570-B (FP-2) flags 5 isolated
> `list[_LabelPlacement] = []` registries across 4 primitives.

## Hand-off Brief

Five annotation/label placement registries (`graph.py:1279`, `numberline.py:323`,
`plane2d.py:698`, `plane2d.py:1029`, `queue.py:283`) are each created fresh and
never shared, so within a single primitive/frame two labels place blind to each
other; the browser-confirmed failure is Plane2D's **point content-label** (which
has *no* registry at all) overprinting the **line content-label** (`:1029`) by
11×9 px. The architectural root cause is that the two label *species* — always-on
**content labels** (Plane2D points/lines, Graph edge weights) vs per-frame
**annotation pills** (`\annotate`, dispatched by `base.emit_annotation_arrows`
with its own `placed` list at `base.py:877`) — have **no channel to join or seed a
common registry**, and the four FP-2 primitives never override the one existing
content→annotation channel (`resolve_self_content_rects`, `base.py:563/856`) that
`array`/`dptable`/`grid`/`matrix` do use. The fix is a per-primitive unified
content-label registry (fixes content-vs-content) plus exposing content labels as
pure `resolve_self_content_rects` obstacles (fixes content-vs-annotation on both
the emit and measure paths), landed in a lint-sanctioned `register_decorations`
method — **not** a scene-wide mutable registry, which would break the 0.01 px
measure-parity contract.

## Case Info

- **Opened:** 2026-07-03
- **Repro:** `scratchpad/fp2_demo.tex` — `\shape{p}{Plane2D}{xrange=[0,10],yrange=[0,10],grid=true,axes=true}` + `add_line=("y = x",1.0,0.0)` + `add_point=(9.05,9.9,"P(9.05, 9.9)")` in a `diagram` env.
- **Measured:** `scratchpad/fp2_measure.py` (render_file static → headless chromium `getBoundingClientRect`) → `'P(9.05, 9.9)'` at x750.0 w72.0 vs `'y = x'` at x731.0 w30.0 → **overlap 11.0×9.0 px**; only **1** `<rect>` pill in `.scriba-plane-labels` (the line's) — the point label is bare `<text>` with zero avoidance.

---

## Root cause

### Git archaeology — birth of each registry

`git log -L <line>,<line>:<file>` on each site:

| Site | Born | Commit | Species |
|------|------|--------|---------|
| `graph.py:1279` `placed_edge_labels` | 2026-04-13 | `e47a645` feat(graph): edge label collision avoidance with background pills | **(a) CONTENT** — edge-weight pills |
| `numberline.py:323` `placed` | 2026-04-13 | `4ea8036` feat(animation): smart annotation labels with pills, collision avoidance, hover | **(b) ANNOTATION** — bespoke tick-geometry arrow path |
| `plane2d.py:1029` `placed_labels` | 2026-04-13 | `7106685` feat(plane2d): text annotations, adaptive ticks, line label collision | **(a) CONTENT** — line labels |
| `plane2d.py:698` `text_placed` | 2026-04-21 | `eafe2b3` refactor: migrate plane2d to _place_pill (closes FP-1..FP-5) | **(b) ANNOTATION** — position-only `\annotate` text pills |
| `queue.py:283` `placed` | 2026-07-02 | `90877a1` feat(animation)!: exact painted-extent annotation reservation | **(b) ANNOTATION** — bespoke slot-pointer arrow path |

**What the shared mechanism looked like at each birth, and why the author didn't use it:**

- **The three 2026-04-13 births** predate every join point. At that time the only
  sharing convention was the per-call `placed_labels` contract documented in
  `_svg_helpers.py:6-14` ("Callers MUST initialize one `placed_labels` … and pass
  the **same list** to every call … within that frame"). There was **no**
  `base.emit_annotation_arrows` owning a frame registry yet, and **no**
  `resolve_self_content_rects` (`base.py:563`, a later W1 addition whose default is
  `[]`). Each new placement feature therefore minted its own list because there was
  no primitive-level home to join. Content-label geometry (edge-perpendicular
  rotated pills at `graph.py:1410-1448`; line-clip anchors at `plane2d.py:1042-1056`)
  was also deliberately kept apart from arrow-annotation geometry, which routes
  through `emit_arrow_svg`.
- **`plane2d.py:698` (2026-04-21, eafe2b3)** is the clearest "had it, didn't use
  it." That commit migrated `text_anns` onto the canonical `emit_position_label_svg`
  path, but created a **fresh** `text_placed = []` at the call site — even though the
  *same* `emit_svg` already owns an arrow-annotation `placed` (via
  `emit_annotation_arrows`, `plane2d.py:684-691` → `base.py:877`) **and** a line-label
  `placed_labels` (`:1029`) in the sibling `_emit_labels`. Three registries in one
  primitive's single frame, none shared.
- **`queue.py:283` (2026-07-02, 90877a1)** split arrows (bespoke `placed`) from pills
  (`emit_annotation_arrows`' `placed`) because the exact-painted-extent redesign gave
  arrows tick/cell geometry the shared engine handled differently — a parity-driven
  split, not an oversight, but still two ships.

**The architectural root cause.** `base.emit_annotation_arrows` builds its `placed`
registry *internally* (`base.py:877`) and self-seeds only from
`resolve_self_content_rects` as SHOULD `content_cell` obstacles (`base.py:854-868`).
But **the four FP-2 primitives never override `resolve_self_content_rects`** — only
`array.py:493`, `dptable.py:307`, `grid.py:195`, `matrix.py:294` do. So the *one*
existing content→annotation channel is unused by exactly the primitives whose
content labels are most prominent, and there is no per-primitive unified registry to
carry content-vs-content avoidance either.

### Flow map — Plane2D `emit_svg` (`plane2d.py:639`), the confirmed bug

Emit order:

1. **Layer 1** grid `_emit_grid` + axes `_emit_axes` (`:661-662`).
2. **Layer 2** (transform group) regions, polygons, lines, segments, points — *geometry only* (`_emit_lines :870`, `_emit_points :840`); labels are not emitted here.
3. **Layer 3** `_emit_labels` (`:983`), outside the transform:
   - tick labels (`:987`);
   - **POINT labels** (`:991-1015`): emitted at a fixed offset `(sx+_LABEL_OFFSET, sy-_LABEL_OFFSET)` via `_render_svg_text` — **no registry, no pill, no nudge, no viewBox clamp**;
   - **LINE labels** (`:1017-1114`): own `placed_labels` (`:1029`), nudge-down loop (`:1067-1076`) + viewBox clamp (`:1079-1084`) + background pill (`:1095`).
4. **Layer 4** annotations (`:681-711`): `arrow_anns` → `emit_annotation_arrows` → internal `placed` (`base.py:877`); `text_anns` → fresh `text_placed` (`:698`).

So Plane2D holds **three isolated registries plus one no-registry path**. The
browser-confirmed failure is the **point label (no registry) vs line label
(`:1029`)** — both content, both in `_emit_labels`, neither aware of the other.
`fp2_measure.py` confirms the point label is bare text (0 pills) and overlaps the
line pill 11×9 px.

### Flow map — Graph `emit_svg` (`graph.py:1217`)

- `placed_edge_labels` (`:1279`) → edge-weight pills; consumed by `_nudge_pill_placement` (`:1476`), appended (`:1497`); also uses `node_aabbs` (`:1320`) as MUST obstacles **for weights only**.
- `emit_annotation_arrows` (`:1646`) → internal `placed` (`base.py:877`). No link to `placed_edge_labels`; Graph does **not** override `resolve_self_content_rects`, so annotation pills see neither edge-weight pills nor nodes. Two ships passing.
- **Why the weight didn't render in the quick diagram probe:** `display_weight` (`graph.py:1397-1401`) stays `None` unless a dynamic `\apply` value is set **or** `show_weights` is true — and `show_weights` defaults **False** (`graph.py:747`). A bare weighted edge in a `diagram` env with no `show_weights=true` emits **no** weight pill; hence "only 2 texts, weight absent." Not a placement bug — a display-gate default. (When `show_weights=true`, the two registries are then genuinely isolated.)

### Flow map — NumberLine (`numberline.py:224`) / Queue (`queue.py:266`)

- **NumberLine:** `arrow_anns` → bespoke tick-geometry `emit_arrow_svg` with local `placed` (`:323-337`); `pill_anns` → `emit_annotation_arrows` → base `placed` (`:877`). Two registries. NumberLine does **not** override `_measure_emit` (only `array`, `queue`, `base` do) → the measure path routes *all* annotations through the base `emit_annotation_arrows` geometry, diverging from the bespoke emit-path arrow geometry — an adjacent measure-parity gap (FP-5-flavoured).
- **Queue:** `_emit_queue_annotations` (`:266`): arrows → local `placed` (`:283`); pills → `emit_annotation_arrows` → base `placed` (`:877`). Two registries, but Queue **does** override `_measure_emit` (`:314`) to call the same `_emit_queue_annotations`, so its reserved-lane parity is preserved.

---

## Chosen design + rejected options

### Chosen: per-primitive unified content registry (A) + content-as-obstacle (C)

Blend A and C, split cleanly by *what is measured*:

1. **Content-vs-content → one per-primitive mutable registry (A).** Inside each
   primitive's label emission, create a single `placed: list[_LabelPlacement]` and
   have *every* content label join it in deterministic emit order. For Plane2D
   `_emit_labels`: ticks → points → lines share one list; **point labels gain the
   nudge + viewBox clamp** the line labels already have (`:1067-1084`). This directly
   closes the 11×9 px bug. For Graph: edge-weight pills keep `placed_edge_labels`.
2. **Content-vs-annotation → `resolve_self_content_rects` obstacles (C).** Each
   FP-2 primitive overrides `resolve_self_content_rects` to return the AABBs of its
   placed content labels (point-label boxes, line pills, edge-weight pills + nodes).
   `base.emit_annotation_arrows` **already** folds these into the scorer as SHOULD
   `content_cell` obstacles on *both* paths (`base.py:854-868`), so annotation pills
   avoid content labels without any mutable list crossing the content/annotation
   boundary.
3. **Annotation-vs-annotation** stays as-is (`base.py:877` already shared per frame);
   collapse each primitive's bespoke arrow `placed` (`numberline:323`, `queue:283`)
   and Plane2D `text_placed` (`:698`) into that same frame registry.

**Lint home.** House the unified registry in a method named `register_decorations`
(or `dispatch_annotations`) — the two names the linter allow-lists
(`lint_smart_label.py:260`) — so FP-2 clears **without** suppression.

**Why the A/C split (not A's literal "seed").** A's phrasing is "content labels seed
[the annotation registry], annotations append." Seeding the annotation *mutable list*
from content on the emit path would make annotation placement depend on content that
the **measure path never sees** (measure runs each primitive in isolation via
`_measure_emit`, `base.py:393`), so measured ≠ painted. Using `resolve_self_content_rects`
(a **pure** function of primitive state, recomputed identically on both paths) gets
the same "annotations avoid content" outcome **with** parity by construction. Content
labels are viewBox-clamped and never extend the reserved annotation lane, so the
emit-only content registry is safe to leave unmeasured.

**Determinism / R-32.** Emit order is already canonical (points by index, lines by
index, edges by `_edge_key` sort at `graph.py:1351-1357`). Content placement is a pure
function of frame geometry with no cross-frame state → cannot oscillate; the annotation
floor `_min_arrow_above` (`base.py:456`) is untouched.

### Rejected

- **(B) Full scene registry threaded into `emit_svg` like `scene_segments`** — what
  the E1570-B message literally suggests ("shared placed_labels registry passed from
  the frame caller"). Rejected: (i) **measure-hostile** — `scene_segments` is built
  once in `_frame_renderer.py:619-629` and threaded **emit-only** (`:713-718`); the
  measure path (`_measure_emit`) has no scene registry, so any placement dependence on
  it breaks the 0.01 px pin. (ii) **Wrong grain** — the confirmed bug is *intra*-primitive
  (point vs line in one Plane2D); a scene registry is cross-primitive overkill.
  (iii) **High blast radius** across every `emit_svg` signature. Cross-primitive label
  overlap is already mitigated by vertical stacking (`_PRIMITIVE_GAP`,
  `_frame_renderer.py:617`) and, for annotations, by the existing `scene_segments`
  obstacle channel (`base.py:838-847`).
- **(A) alone (per-primitive registry, no obstacle channel)** — leaves Graph
  weight-vs-`\annotate` and Plane2D line-vs-`\annotate` broken (annotations never see
  content).
- **(C) alone (obstacles only)** — content labels never enter the scorer, so it cannot
  fix **content-vs-content** — i.e. it does not fix the confirmed bug.

---

## Measure-parity analysis

- **Measure path:** `annotation_height_above` (`base.py:354`) → `_annotation_extent`
  (`:378`) → `_measure_emit` (`:435`) → `emit_annotation_arrows` into a scratch buffer
  → `measure_painted_extent`. Pinned **painted ⊆ bbox at ±0.01 px** by
  `tests/unit/test_painted_within_bbox.py` (`_EPS=0.01`, `_EPS_X=0.01`) and
  **reserved ≈ painted at ±1.5 px** by `tests/unit/test_annotation_extent_exact.py`
  (`_TOL=1.5`).
- **Coverage gap (important):** both tests instantiate **only** `ArrayPrimitive`,
  `DPTablePrimitive`, `GridPrimitive` — **none** of the four FP-2 primitives. So the
  0.01 px contract does **not** currently cover Plane2D/Graph/NumberLine/Queue content
  labels. Changing their content-label placement will **not** trip these tests today —
  but that also means the honesty guarantee is *absent* exactly where this fix lands.
- **Parity invariant.** Whatever the emit path feeds the scorer, the measure path must
  feed identically. `resolve_self_content_rects` satisfies this **by construction**: it
  is pure (state-only), consulted on both `emit_svg → emit_annotation_arrows` and
  `_measure_emit → emit_annotation_arrows` (`base.py:856`). `scene_segments` is
  emit-only and already tolerated as a bounded nudge outside the reserved lane
  (`base.py:363-367`). Therefore the fix routes content→annotation avoidance through
  `resolve_self_content_rects`, **never** through an emit-only mutable seed.
- **Action:** the fix must **add** Plane2D + Graph to `test_painted_within_bbox` /
  `test_annotation_extent_exact` so the obstacle channel is pinned going forward, and
  assert `resolve_self_content_rects` idempotence (same AABBs on repeated calls).

---

## TDD plan

1. **RED — the fp2 repro (integration).** New test renders `fp2_demo.tex`
   (add_line "y=x" slope 1 + add_point P(9.05,9.9)); parse the two labels' rects and
   assert **overlap area == 0** (today 11×9). Two viable variants: browser
   (`render_file` static + playwright `getBoundingClientRect`, mirroring
   `fp2_measure.py`) or CI-friendly (parse `.scriba-plane-labels` local coords +
   `estimate_text_width`). Also assert the point label now emits a pill/registered box.
2. **RED — per-primitive unit pins.**
   - *Plane2D:* point label + line label sharing an anchor → their `_LabelPlacement`
     boxes are disjoint (`overlaps()==False`).
   - *Graph:* `show_weights=true` + `\annotate` on the same edge → weight-pill AABB and
     annotation-pill AABB disjoint. Plus a **documented** (not "fixed") pin: bare
     weighted edge in a diagram with no `show_weights` emits **0** weight pills
     (`graph.py:1397-1401`).
   - *NumberLine / Queue:* arrow annotation + position pill at adjacent targets → disjoint
     (currently separate registries `:323`/`:283` vs `base:877`).
3. **Measure-parity pins.** Add Plane2D + Graph cases to `test_painted_within_bbox`
   and `test_annotation_extent_exact`; assert `resolve_self_content_rects` purity.
4. **Golden churn prediction (of 105 corpus goldens, `tests/golden/examples/corpus/`).**
   - *Plane2D — WILL rebaseline* (line labels now nudge around point labels; point labels
     now pilled/clamped): `plane2d_lines` (5 pts + 5 labeled lines — strongest),
     `test_plane2d_edges` (59 pts + 8 labeled lines — strongest), `test_plane2d_dense`
     (16+4), `test_plane2d_animation` (8+2), `plane2d_ticks` (19+1), `plane2d` (2+1),
     `test_reference_extended` (5+1) ≈ **7 files**. `li_chao` (6 lines, 0 points) stays
     byte-stable unless seeding order changes.
   - *Graph — WILL rebaseline* (annotation pills now avoid weight pills via new
     `resolve_self_content_rects`): `dijkstra` (weights+3 annotate), `dijkstra_editorial`
     (weights+2), `kruskal_mst` (weights+3) = **3 files**. `show_weights`-only goldens
     (`diagram_intro`, `gep_v2_smoke`, `mcmf`, `test_reference_graph_tree`) stay
     byte-stable **iff** `placed_edge_labels` semantics are preserved.
   - *smart_label goldens* (`tests/golden/smart_label/`, `test_corpus.py`): audit for
     NumberLine/Queue arrow+pill scenes before landing steps 6.
5. **Lint tests churn.** `tests/unit/test_lint_smart_label.py` `test_live_scan_detects_10_primitive_fp_pairs` (`:510`) and `test_live_scan_fp_counts_match_r3_audit` (`:541`, `"FP-2": 4`) must be updated as each primitive's registry moves into `register_decorations`/`dispatch_annotations` (FP-2 count 4 → 0).

---

## Blast radius

| Change | Scope | Risk |
|--------|-------|------|
| `plane2d._emit_labels`: unify point+line registry, add point nudge/clamp | 1 method | Medium — churns ~7 goldens; **must reuse line-label viewBox clamp so point labels can't leave the plot** |
| `plane2d`: route `text_placed` (`:698`) into frame registry; override `resolve_self_content_rects` (points + line pills) | Plane2D | Medium |
| `graph`: override `resolve_self_content_rects` (weight pills + nodes); expose weights to annotation scorer | Graph | Medium — churns 3 goldens |
| `numberline`/`queue`: collapse bespoke `placed` into pill registry; **watch NumberLine `_measure_emit` gap** | 2 primitives | Low-Med — NumberLine may need a `_measure_emit` override to keep extent-exact honest |
| `base.emit_annotation_arrows`: (only if a seed param is chosen) optional `placed_labels=None` | fan-out to all primitives | HIGH by fan-out, behaviour-preserving when unseeded — **prefer the obstacle channel and avoid touching base at all** |
| Lint + measure-parity tests | tests | Expected, mechanical |

**Key risks.** (a) Point-label nudge escaping the plot → reuse the existing line-label
clamp (`plane2d.py:1079-1084`). (b) The temptation to *seed* the annotation mutable
list from content breaks measure parity — use `resolve_self_content_rects` (pure)
instead; this is the whole reason C beats A's literal "seed." (c) NumberLine's latent
measure-vs-emit arrow-geometry divergence surfaces once NumberLine joins
`test_annotation_extent_exact`.

---

## Landing order

1. Land RED repro (fp2 overlap==0) + per-primitive unit pins (all RED).
2. **Plane2D content-vs-content** — unified `register_decorations` registry in
   `_emit_labels` (points + lines share; point nudge + clamp). fp2 test → GREEN;
   rebaseline ~7 Plane2D goldens. *(Highest user value — closes the confirmed bug.)*
3. **Plane2D content-vs-annotation** — route `text_placed` (`:698`) into the frame
   registry; override `resolve_self_content_rects` (points + line pills).
4. **Graph** — override `resolve_self_content_rects` (weights + nodes); rebaseline 3
   goldens. Keep `placed_edge_labels` semantics byte-stable for weight-only goldens.
5. **NumberLine + Queue** — collapse bespoke arrow `placed` into the frame registry;
   add NumberLine `_measure_emit` override if extent parity regresses.
6. **Pin forward** — add Plane2D + Graph to `test_painted_within_bbox` /
   `test_annotation_extent_exact`; update `test_lint_smart_label` expected counts
   (FP-2 → 0); confirm E1570-B clears with registries in `register_decorations`.

---

## Appendix — probes (scratchpad, read-only)

- `fp2_demo.tex` — Plane2D repro (add_line + add_point).
- `fp2_measure.py` — `render_file` static → headless chromium; prints per-label rects
  and overlap. Output: point `'P(9.05, 9.9)'` x750 w72 vs line `'y = x'` x731 w30 →
  **overlap 11.0 × 9.0 px**, 1 pill in `.scriba-plane-labels`.
- Chromium: `~/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell`.
