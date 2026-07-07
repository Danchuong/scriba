# Sweep 3-A — nodefit / canvas adversarial findings

Adversarial probe of the 0.30.0 "nodefit" cluster (Graph/Tree/Forest/Hypercube
node-label fit + Graph force-canvas scaling). All verification is numeric parsing
of emitted print-frame SVG snapshots against the painted-extent invariants:

- **I1** every painted node-label extent `[Tx+cx ± tw/2] ⊆ [0, viewBox.W]`
- **I2** no two same-row (`|Δcy|<18`) labels overlap horizontally
- **I3** node circle AABBs `⊆ viewBox`
- **I4** viewBox + primitive translate frame-stable across all frames (R-32)

Widths measured with the repo's own oracle `scriba.animation.primitives.
_text_metrics.measure_value_text(text, font_px)` at the *painted* font (14px
graph/tree, 13px hypercube). Absolute coordinates fold in the scene wrapper
`translate(12,12)` + the primitive translate. Probes: `_sweep3_nodefit/*.tex`.
Harness: `scratchpad/nfcheck.py`. No browser used.

Both confirmed defects contradict an explicit 0.30.0 headline claim, so they are
residuals of the just-shipped cluster, not documented limitations:
> nodefit A — "the frame grows and content shifts **instead of clipping**"
> nodefit B — "Adjacent wide labels **no longer overlap** each other"

---

## CONFIRMED

### F2 — [HIGH] Tree `add_node` + wide `value=` on the new node renders OUTSIDE the viewBox (clipped/invisible)

**Probes:** `s6c_clip.tex` (full clip), `s6_sparse_addnode.tex` (milder → translate jump), `s6d_stdtree_addnode.tex` (standard tree, same clip), `s6b_control_novalue.tex` (control = clean).

**Evidence (`s6c_clip`, sparse_segtree, frame 3 adds `[751,1000]` + `value="XX=99999999999999999999"`):**
- All 3 frames share **one** viewBox `0 0 464 364` (confirmed for the print frames *and* the interactive stage — `distinct viewBoxes: ['0 0 464 364']`).
- Frame 3 paints node `[751,1000]` at `cx=462`, tree translate `x=32`, so the **circle AABB = [474, 514]** and the **label extends to x=599** — both entirely past the fixed `W=464`. The added node and its parent `[501,1000]` (dragged to the same column) render outside the frame → clipped / invisible.
- `s6d_stdtree_addnode` reproduces on a **plain standard Tree** (not segtree): node `99` + value 224px → circle `[502,542]`, label to `634`, vs `W=464`. So the defect is general to *any* Tree kind, not sparse-segtree-specific.
- `s6b_control_novalue` (identical structure, no value on the added node): **I1–I4 all clean** — isolating the wide *value*, not the structural `add_node`, as the cause.

**Milder manifestation (`s6_sparse_addnode`, 118px value on a left-side added node `[0,250]`):** viewBox stays 464 but the **tree translate jumps `x=32 → x=41` at frame 3** (`left_pad` 0→9). In the single-viewBox interactive widget the whole tree visibly shifts right 9px mid-scene — an I4 (R-32) frame-stability break. `s6b` control confirms no jump without the value.

**Mechanism (root cause, cited):**
- `_prescan_value_widths` (`scriba/animation/_frame_renderer.py:326`) runs the **value pass** first (`:370`–`:389`, `prim.set_value(suffix,…)`), then a **structural replay** (`:395`–`:415`) gated on `getattr(prim,"_structural_prescan",False)` (`:397`).
- **Tree does not declare `_structural_prescan`** (grep: only `forest.py`, `linkedlist.py`, `tracetable.py` do; `Tree._structural_prescan` is ABSENT). So `add_node` is never replayed during the prescan → at prescan time a mid-scene-added node **does not exist**.
- The value pass therefore calls `set_value` on a not-yet-existing selector: `Tree.set_value` (`tree.py:786`) → `super().set_value` **soft-drops** it (E1115, *visible in render stderr*: `invalid selector 'node[[751,1000]]', ignoring set_value()`); the guard `self.get_value(suffix)==value` (`tree.py:791`) is then False so **`note_node_label` is skipped** → `_node_label_wmax` under-counts → `_node_pitch`/`_layout_width` (`tree.py:744`/`:759`) and the frame-stable viewBox **under-reserve**.
- At frame render the node exists and the value lands, so `_nodefit_regrow` (`tree.py:770`, `self.width = need` `:783`) grows the tree **live**, past the already-frozen viewBox → clip (wide value) or translate jump (moderate value).
- **Ordering note:** merely adding `_structural_prescan=True` to Tree would not fix it — the value pass (`:370`) precedes the structural pass (`:395`), so the node is still absent when its label width is measured. A correct fix needs the width prescan to see post-structural state (e.g. run the value pass after the structural replay, or replay add_node ahead of the value pass).

**Why it slipped:** nodefit's frame-stability rests on "the prescan replays every frame's `value=` before the first viewbox read." That premise holds only for values on nodes that exist at construction; it silently fails for the value channel of a structurally-added node on a primitive without structural prescan.

---

### F1 — [MEDIUM] Isolated-lane wide `value=` labels overlap each other (halves-blind lane spacing)

**Probes:** `s4c_isolane_adj.tex` (animation), `s4d_diagram_lane.tex` (single-frame diagram — same result).

**Evidence (`s4c`, 12 degree-0 nodes, only adjacent `a5`,`a6` get a 109px value):**
- Parsed frame 2 (label-space centers): `a5 '555555555555'` cx=263 → `[208.5,317.5]`; `a6 '666666666666'` cx=311 → `[256.5,365.5]`.
- **I2 overlaps: a5↔a6 = 61px**, a4↔a5 = 14px, a6↔a7 = 14px. Labels are unreadable (the two 12-digit values merge). I1 clean (still inside the viewBox) — this is a readability defect, not a clip.
- `s4d_diagram_lane` reproduces in a static `diagram` (frames=1) with identical 61/14px overlaps → not settle- or animation-specific.
- Contrast `s4b_isolane_pack` (8 nodes *all* 82px): **clean** — the settle's canvas widening happens to give span 104 > 82. The bug needs a **many-node lane with few-but-wide labels** (small total overhang, tight span): overlaps whenever `(width−2·PADDING)/(count−1) < label_width`.

**Mechanism (cited):**
- `_settle_label_layout` (`graph.py:1602`) builds label `halves` (`:1621`) and passes them to `_resolve_overlaps` (`:1643`) — but **only for the connected subset** (`pos` excludes isolated nodes). It then calls `_place_isolated_lane(pos, isolated, self.width, self.height)` (`:1653`) with **no halves**.
- `_place_isolated_lane` (`graph.py:531`) spaces the lane purely by count: `span = (width − 2·_PADDING)/(count − 1)` (`:557`) — blind to label width. The initial force solve has the same halves-blind call (`graph.py:685`).
- The settle only widens the canvas by `overhang = Σ(w−2r)` (`:1626`), which is spread across all `count−1` gaps; when few nodes are wide in a many-node lane, per-gap growth is far below the full label pitch those wide labels need.
- Existing regression tests (`test_isolated_vs_connected_no_overlap_multi_seed`, `test_all_isolated_nodes_even_row`) check **circle** non-overlap, which still holds (circles are 48px apart, r=12) — so the label overlap passed CI unnoticed. This directly contradicts the nodefit-B claim "adjacent wide labels no longer overlap," which lists "the Graph force layout" as covered; the isolated lane is the uncovered sub-case.

**Trigger realism:** degree-0 nodes carrying wide per-node values — unreached-vertex `dist=∞`/large numbers in Dijkstra/BFS, DSU singleton ranks, isolated-vertex enumerations. Bounded but real.

---

## CLEAN (verified sound — negative results)

| Scenario | Probe | Result |
|---|---|---|
| 1. Force + wide `value=` on a **hidden** node (toggled across 4 frames) | `s1_force_hidden` | I1–I4 clean, vb 604×360 stable. Prescan reserves the hidden frame's wide value; no clip, no phantom shift. |
| 2. Manual `positions=` + wide value at left & right **extremes** (settle suppressed) | `s2_manual_extremes` | I1–I4 clean. `left_pad=15` fires even though `_force_relayout_ok=False`; `L '999999999999'` → `[12.5,109.5]`, `R 'dp=1234567'` → right edge 472 ≤ 484. **nodefit-A viewBox fold works independently of the settle.** |
| 3. `layout="stable"` + wide values on a ring | `s3_stable_wide` | I1–I4 clean. |
| 4. Isolated + connected, wide values (3 isolated, roomy canvas) | `s4_isolated` | I1–I4 clean (contrast F1 for the packed case). |
| 4b. 8 isolated nodes all-wide | `s4b_isolane_pack` | Clean — settle widening gives span 104 > label 82. |
| 5. `\group` hull + `\annotate` arrow **after** a wide-label settle re-spread | `s5_group_annotate` | Clean. Arrow start `(278,266)` sits exactly on node A's boundary toward E, end `(42,36)` on E's boundary; hull `y∈[246,314]` encloses settled centers `cy=280`. **Anchors track the moved positions**, not stale ones (`resolve_annotation_point`→`self.positions`, mutated by the settle before `emit_svg` reads it). |
| 6-control. `add_node` with no value | `s6b_control_novalue` | Clean — structural growth alone is frame-stable (isolates F2's cause). |
| 7. `\zoom` over a grown force canvas (N=24) and a grown-pitch Tree | `s7a_zoom_grown_graph`, `s7b_zoom_tree_pitch` | Non-zoom frames stable; the zoom frame crops to a sane 4px inset of the **grown** content (translate unchanged); content contained. |
| 8. Hypercube `bits=5` (32 nodes, 5-bit masks 41px > 2r) + wide values + caption | `s8_hypercube_b5` | I1–I4 clean. `subset[28] 'w=999999999'` (95px, rightmost) contained `[1093.5,1188.5]` in a pre-grown vb 1204; row `k=1` symmetric about center 598; B3 row pitch reflows; frame-stable. |
| 9. N=40 weighted + `show_weights=true` + wide node value on grown canvas | `s9_n40_weights` | I1–I4 clean (grown vb 803×522). |
| 10. Graph (settles wider) beside an Array | `s10_graph_array` | Clean. Graph tr `(20,20)`, Array wrapper `(78,372)`, and every array cell x identical across frames — the prescan pre-grows the graph before frame 0, so scene/stitcher offsets stay frame-stable. |

---

## Hypothesized / not reproduced (noted, lower confidence)

- **H1 [LOW] `auto_expand` scaled positions vs. unscaled label pad.** `emit_svg`
  paints nodes at `working_positions = self.positions · s` (`graph.py:2119`–`:2141`)
  when `auto_expand` + display weights scale by `s>1`, but `_h_label_pad`
  (`:1752`) / `bounding_box` / `resolve_annotation_point` all read the **unscaled**
  `self.positions`. A wide label on a scaled-out boundary node could exceed the
  reserved viewBox. Probed `s11_autoexpand` — `_find_min_scale` engaged at only
  `s=1.018`, absorbed by pad slack → **clean**. The mismatch is real in code but I
  could not force a large-enough `s` with the manual/force layouts tried; deferred
  as a distinct (non-nodefit) surface. If confirmed at larger `s` it would be an
  I1/I3 right-edge clip.

- **O1 [LOW, tangential] `\zoom{G.node[id]}` / `\zoom{T.node[id]}` silently falls
  back to full board.** Emits `E1543 "has no resolvable box"` because
  `resolve_annotation_box` returns a box only when the node carries a `position=
  below` pill (gated at `graph.py:1710`); a plain node is unzoomable. Not a
  nodefit defect (zoom-box gating), but it means node-level zoom over a grown
  canvas cannot be exercised and degrades quietly.

- **O2 [INFO] Hypercube reserve/paint font mismatch.** `note_node_label` measures
  at `_NODE_LABEL_FONT_PX=14` (`hypercube.py:256`) while text paints at 13px
  (`_NODE_FONT_SIZE`). Over-reserves → **safe** (no clip); a latent slack, not a
  bug. (The reverse — reserve<paint — would clip; this is the safe direction.)

---

## Compact summary (one line per finding)

- **HIGH** | Tree `add_node` + wide `value=` on the new node → node renders **outside** the fixed viewBox (clipped/invisible); moderate value → mid-scene translate jump | `_sweep3_nodefit/s6c_clip.tex`, `s6d_stdtree_addnode.tex`, `s6_sparse_addnode.tex` (control `s6b`) | circle AABB `[474,514]`/label→599 vs W=464; translate 32→41 @frame3 | Tree lacks `_structural_prescan` so prescan drops the added node's value (E1115) → viewBox under-reserves, `_nodefit_regrow` grows live: `_frame_renderer.py:326/370/397`, `tree.py:786/791/770`
- **MEDIUM** | Isolated-lane wide `value=` labels overlap (61px) — halves-blind lane spacing | `_sweep3_nodefit/s4c_isolane_adj.tex`, `s4d_diagram_lane.tex` | a5↔a6 overlap 61px, a4↔a5 & a6↔a7 14px; span 48.5 < label 109 | `_place_isolated_lane` gets no `halves`, spaces by count: `graph.py:1653` + `:557` (also initial solve `:685`); `_resolve_overlaps` halves-aware only for connected `:1643`
- **LOW (hyp.)** | `auto_expand` paints at scaled positions but reserves pad from unscaled → possible right clip at large `s` | `s11_autoexpand.tex` | engaged only at s=1.018 (clean); not reproduced | `graph.py:2119`–`2141` scaled vs `:1752` unscaled
- **LOW (tangential)** | `\zoom{G.node[id]}`/`{T.node[id]}` → E1543 full-board fallback (unzoomable plain node) | `s7a`/`s7b` | E1543 in stderr | `resolve_annotation_box` gated on below-pill `graph.py:1710`
- **INFO** | Hypercube reserves at 14px, paints at 13px (safe over-reserve) | `s8_hypercube_b5.tex` | tw 14px≥13px | `hypercube.py:256` vs `_NODE_FONT_SIZE`

**Clean:** s1 (force+hidden), s2 (manual extremes), s3 (stable), s4/s4b (roomy/all-wide lane), s5 (group+annotate anchor-tracking), s6b (add_node no-value control), s7 (zoom over grown), s8 (hypercube b5), s9 (N=40 weights), s10 (graph+array scene offsets). nodefit-A viewBox fold and the settle's connected-node re-spread + anchor tracking are sound where the value is visible at prescan time.
