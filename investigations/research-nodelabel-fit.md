# Research — Node-Label Fit Pipeline (implementation-ready spec)

**Status:** Concluded · **Discipline:** bmad-investigate (design, not implement) · **Repo:** scriba @ `__version__` 0.29.0 / `SCRIBA_VERSION` 24
**Extends:** `investigations/bmad-rq-nodefit.md` (settled: GROW THE LAYOUT, keep the circle — not ellipsis/shrink).
**Scope:** turn the settled grow-layout design into an implementation-ready spec: the single source of truth, exact per-primitive
edits (re-verified against 0.29.0 — line numbers drifted from the prior report's 0.27.0/v22), the canvas-design contract,
the byte/R-32 proof + real golden blast, RED tests, and an automatable golden invariant.

> ⚠️ **Version drift:** the prior report cited 0.27.0/v22 line numbers (graph.py:1548, tree.py:862, hypercube.py:166, …).
> Code moved to 0.29.0/v24. **Every citation below is re-verified against the current tree.** SCRIBA_VERSION verdict updates
> 22→23 (prior) to **24→25** (current).

---

## Hand-off Brief (15-second read)

Node labels paint as a bare `<text text-anchor="middle" x="cx">` with `clip_overflow=False` (Graph graph.py:2271, Tree
tree.py:1018, Forest forest.py:582, Hypercube hypercube.py:384), sourced from **base id/label OR the per-frame `value=`
override** (`display_label = get_value(node) or base`). The circle radius is fixed (`_NODE_RADIUS=20`, only scaled *down* by
node count), and both the viewBox (`bounding_box`) and the node pitch (`min_sep`/`_MIN_H_GAP`/`_H_PITCH`) are **label-blind**.
The established fix (this spec): a **monotonic per-node cross-frame-max label-width map** on `PrimitiveBase`, seeded at
`__init__` with base labels and grown during the existing `_prescan_value_widths` pass (mirroring VariableWatch
`_value_col_width`, Queue `_cell_width`, Bar `_envelope_max`, Forest `_envelope_width` — all of which already do exactly this
for their own widths). It feeds **(A) the bounding_box/viewBox** (measure, low-risk, mirrors `_h_label_pad`/caption fold — no
position change, no relayout, ships alone, fixes the confirmed frame-clip) and **(B) the node pitch** (layout, coupled with a
canvas grow, fixes node-node collision). The radius is **unchanged** → edge-endpoint math, arrow geometry, hull inflate, and
cursor anchoring are all untouched. Real byte-golden blast: **~1 doc** (not the prior report's 97/61/3 — those counted
*usage*, not *re-bless*). `SCRIBA_VERSION` 24→**25**, `__version__` 0.29.0→**0.30.0**.

---

## 1. The single source of truth — `cross_frame_max_label_width`

**The 6–10 line mechanism** (mirrors the emitter's established cross-frame floor patterns):

1. New `PrimitiveBase` state: `self._node_label_wmax: dict[str, int] = {}` — a **monotonic** per-node-key max painted label
   width in px. New helpers: `note_node_label(node_key, text, font_px=14)` grows `_node_label_wmax[node_key] =
   max(existing, measure_value_text(text, font_px))`; `cross_frame_max_label_width(node_key) -> int` reads it (0 default).
2. **Seed base labels at `__init__`:** each primitive, right after it builds its nodes, calls `note_node_label(key, base_label)`
   for every node. This makes the static-id case (Graph `"Bellman-Ford"`, Tree/Forest node labels) known immediately —
   **no prescan needed for base labels.**
3. **Grow value= labels during the prescan:** each primitive overrides `set_value(suffix, value)` to call `super().set_value(...)`
   then, if `suffix` names a node, `note_node_label(node_key, value)`. The existing `_prescan_value_widths` (`_frame_renderer.py:326`)
   already replays **every frame's** `value=` into `set_value` **before viewbox computation** — so the map reaches the
   cross-frame max. It survives the prescan's snapshot-restore because only `_values` is snapshotted/restored
   (`_frame_renderer.py:361-362,418-421`); `_node_label_wmax` is a separate field, exactly like Queue's `_cell_width`.
4. **One value feeds both consumers:** `bounding_box` (A, measure) and the layout solver (B, pitch) both read
   `cross_frame_max_label_width`. Because it is the *same* monotonic field, fully grown before either is read, measurement
   and layout agree → **no per-frame reflow (R-32 holds).**

**Why this is the established pattern, not a new invention** (evidence):
- `set_min_arrow_above` / `_reserved_arrow_above` (base.py:929-936, 577-585): the stitcher (`_html_stitcher.py:159-184`) scans
  all frames, computes each primitive's max annotation extent, and pins it as a floor so the translate offset is frame-stable.
  **This is the R-32 cross-frame-floor precedent the task says to mirror.**
- `_prescan_value_widths` (`_frame_renderer.py:326-431`) is the *value-channel* twin of that pass: it replays every frame's
  `value=` into `set_value` **specifically so "the cumulative max width is known before viewbox computation"** (its docstring,
  lines 330-332). VariableWatch (`_value_col_width`, variablewatch.py:117-133), Queue (`_cell_width`, queue.py:247-257), Bar
  (`_envelope_max`, bar.py:271-272) and Forest (`_envelope_width`, forest.py:415-419) already grow a monotonic width field
  across it and read it in `bounding_box`. `cross_frame_max_label_width` is the same mechanism generalized to a **per-node** map.

**Signature (proposed, on `PrimitiveBase`):**
```python
def note_node_label(self, node_key: str, text: str, font_px: int = _NODE_LABEL_FONT_PX) -> None:
    """Grow the monotonic cross-frame-max painted width for one node label.
    Seeded at __init__ (base id/label) and by each set_value during the prescan;
    read by bounding_box (measure) AND the layout solver (pitch) so both agree."""
    w = measure_value_text(str(text), font_px)          # size what you paint
    if w > self._node_label_wmax.get(node_key, 0):
        self._node_label_wmax[node_key] = w

def cross_frame_max_label_width(self, node_key: str) -> int:
    return self._node_label_wmax.get(node_key, 0)
```
`_NODE_LABEL_FONT_PX = 14` — the constant painted at graph.py:2278 / tree.py / forest.py / hypercube.py (`font_size="14"`).

**Where per-frame `value=` is known at layout time:** it is NOT known at `__init__` (values arrive per-frame). It becomes known
during `_prescan_value_widths`, which runs in the stitcher **before** `compute_viewbox` and before any frame is measured
(`_html_stitcher.py:229` then downstream viewbox). So: base labels → seed at `__init__`; value labels → grow at prescan; both
land in the map before the first `bounding_box`/relayout read. This is the exact ordering `_apply_min_arrow_above`
(`_html_stitcher.py:237`, "floor-before-measure") already relies on.

---

## 2. Per-primitive exact edits

**Two consumers, different risk.** **A (measure / viewBox)** is read-only w.r.t. positions — it mirrors the existing
`_h_label_pad` + caption fold and fixes the *confirmed frame-clip*. **B (pitch / positions)** re-runs the layout solver and is
coupled to a canvas grow — it fixes *node-node collision*. A can ship without B. Both consume the §1 map.

**Radius is UNCHANGED in every edit below** → these sites stay byte-identical and untouched: edge-endpoint shorten
(`_shorten_line_to_circle`, graph.py:1973/1984 region; tree edges), arrow geometry (`_arrow_shorten = float(self._node_radius)`
graph.py:999, `_arrow_cell_height`), group-hull inflate (`_node_radius + _GROUP_PAD`), cursor/annotation anchoring
(`resolve_annotation_box` graph.py:1514-1523, `_annotation_cell_metrics` graph.py:1525-1537). **This is the whole reason to
grow layout, not radius.**

### A — Measure (viewBox honesty) — LOW risk, mirrors `_h_label_pad`

Add a `PrimitiveBase._node_label_pad()` helper returning `(left_overhang:int, right_overhang:int)`:
```python
def _node_label_pad(self) -> tuple[int, int]:
    """Overhang of the widest painted node label beyond the content frame [0, content_w],
    using the cross-frame-max map. (0, 0) when every label fits -> byte-identical footprint."""
    # per primitive: painted_x(node) and content_w supplied by the caller-side fold below
```
Because `painted_x` and `content_w` are per-primitive, the fold is written at each `bounding_box`, keyed off the shared map.

| # | File:line (0.29.0) | Exact change |
|---|--------------------|--------------|
| **A1 Graph** | `graph.py:1539-1562` `bounding_box`; painted_x = `r + left_pad + cx` (translate at graph.py:1841) | After `left_pad, right_reach = self._h_label_pad()` (1553): compute, over `self.positions`, `lbl_L = max(0, max_n( (cross_frame_max_label_width(node_n)/2) - (r + cx_n) ))` and `lbl_R = max(0, max_n( (r + cx_n) + w_n/2 - (self.width + 2*r) ))`; fold `left_pad = max(left_pad, ceil(lbl_L))`, `right_reach = max(right_reach, self.width + 2*r + ceil(lbl_R))`. Keep ints so inert=byte-stable (comment at 1552 already relies on this). Emit's `translate(r + left_pad, …)` (1841) then shifts content right by the grown left_pad automatically — no separate emit edit. |
| **A2 Tree** | `tree.py:862-882` `bounding_box`; `content_w = self.width + 2*r` (869) | Same fold; painted_x = `r + cx` (tree translate mirrors graph). Defensive — Tree's canvas already widens (`node_count*_MIN_H_GAP`), so this only trips for a very wide outer-leaf label. |
| **A3 Forest** | `forest.py:415-419` `_grow_envelope` (+ `bounding_box:482`) | Fold node-label overhang into `_envelope_width` inside `_grow_envelope` (Forest already reports the monotonic envelope, not live layout — the cleanest host). Forest is `_structural_prescan=True` (forest.py:106) so `_grow_envelope` is already re-run across the prescan. |
| **A3 Hypercube** | `hypercube.py:166-186` `_compute_layout` + `273-291` `bounding_box` | `content_w` (174) = `widest * _H_PITCH`; add `+ max(0, max_row_label_overhang)` where overhang uses the per-row centered `cx` (183) and the map. Also add a real `left_pad` for the leftmost-in-row label (today `_h_label_pad` gives 0 for label overflow — only pills). |

**A alone fully fixes the confirmed frame-clip** (Graph 3-4/7 nodes; Hypercube `subset[i]` spill), with **no position change and
no relayout**, because the viewBox simply grows to contain `painted_x ± w/2`.

### B — Pitch (node-node collision) — HIGHER risk, coupled to canvas (§3)

| # | File:line (0.29.0) | Exact change |
|---|--------------------|--------------|
| **B1 Graph** | `graph.py:651` `min_sep = 2.0*node_radius + _NODE_OVERLAP_GAP` (inside the force layout, feeding `_resolve_overlaps:452`) | `min_sep = max(2.0*node_radius, max_label_width) + _NODE_OVERLAP_GAP` (uniform) or per-pair `(w_i+w_j)/2 + _NODE_OVERLAP_GAP` in `_resolve_overlaps`'s inner loop (452-500). `max_label_width` = max over nodes of `cross_frame_max_label_width`. **Must couple with a canvas grow (§3)** — `_resolve_overlaps` clamps x to `[_PADDING, width-_PADDING]` (492/496) and the FDL clamps to `width-_PADDING` (641), so a bigger `min_sep` with a fixed `self.width=400` is clamped straight back. Needs a **relayout after the prescan** (positions are baked in `__init__:1006-1125`, before the map is grown) — cheapest: re-run only the `_resolve_overlaps` post-pass with the grown `min_sep` + grown canvas; do NOT re-run the seeded FDL (non-determinism/expense). |
| **B2 Tree** | `tree_layout.py:100-226` `_reingold_tilford`; `tree.py:198` `self.width`, `tree.py:444-454` `_relayout` | RT gives each **leaf** `subtree_width = 1.0` (line 165) then normalizes prelim_x across `usable_width = width - 2*_PADDING` (210-214) → leaf pitch = `usable_width / n_leaves` ≈ `_MIN_H_GAP`. Two coupled edits: (a) grow `self.width` (198) from `sum_i max(_MIN_H_GAP, w_i + gap)` instead of `node_count*_MIN_H_GAP`; (b) optionally pass per-leaf `label_units_i = max(1.0, w_i/_MIN_H_GAP)` into `_reingold_tilford` so a wide leaf claims proportional span (Pass A line 165). Recompute in `_relayout` (444) reading the map — Tree already re-runs RT on structural change, so extend `_relayout` + trigger it from the `set_value` override. **Tree self-contains its canvas** (`self.width` flows to `bounding_box`/viewBox), so no external clamp — Tree needs no §3 canvas contract, only its own `self.width` grow. |
| **B3 Forest** | `forest.py:365` `_reingold_tilford(...)` per tree + `_grow_envelope:415` | Same per-leaf spacing as B2, applied per sub-tree; envelope already monotonic. |
| **B3 Hypercube** | `hypercube.py:63` `_H_PITCH`; `166-186` `_compute_layout` | Per-row pitch `row_pitch = max(2*_NODE_RADIUS, max_row_label_width) + _H_GAP`; recompute `content_w`/`cx` (174-184) from it. `_compute_layout` re-run needed after prescan (values arrive per-frame) — call it from the `set_value` override or lazily on first `bounding_box`. Hypercube self-contains its canvas (`content_w` → `bounding_box`), no §3 clamp. |

**Relayout trigger (B, all four):** the `set_value` override marks `self._layout_dirty = True` after growing the map; the next
`bounding_box`/`emit_svg`/`get_node_positions` recomputes positions once if dirty (memoized). This keeps the FDL/RT off the
per-`set_value` hot path while guaranteeing the post-prescan geometry reflects the cross-frame max. (Graph is the only one that
must NOT re-run its *seeded* solver — it re-runs only `_resolve_overlaps`.)

---

## 3. Contract with `graph-canvas-scaling` (sibling design)

Only **Graph** has an externally-fixed canvas (`self.width=400`, `self.height=300`, graph.py:986-987) whose bound is enforced
by `_resolve_overlaps`'s `[_PADDING, width-_PADDING]` clamp (graph.py:492/496/641). Tree/Forest/Hypercube own their canvas
(`self.width`/`content_w` flow straight to `bounding_box`), so **B2/B3 are self-contained** and need no contract.

**For Graph B1, the two designs must agree on one number.** Contract:

- **node-fit (this design) provides:** the per-node monotonic map via `cross_frame_max_label_width(node)`, and the
  label-aware `min_sep` target (`max(2r, w) + gap`, or per-pair `(w_i+w_j)/2 + gap`).
- **canvas-scaling (sibling) provides:** a `self.width`/`self.height` large enough that `min_sep`-spaced nodes are NOT hit by
  the `width - _PADDING` clamp, and it must **consume the same map** — a canvas grown from node *count* × pitch (label-blind)
  under-provisions for wide labels and the clamp compresses the spread back (the exact failure the prior report flagged).
- **shared invariant:** *the canvas reserves exactly what the pitch spreads.* Both read the identical `_node_label_wmax`. If
  the sibling design computes canvas width as e.g. `f(n) + Σ extra_label_width`, `extra_label_width` MUST be
  `Σ max(0, w_i - 2r)` from this map, not a re-measure (or the two diverge and R-32 breaks).
- **A needs no contract:** the viewBox fold (§2 A1) grows `bounding_box().width` via `left_pad`/`right_reach` independent of
  `self.width` and of positions. So **A can ship before the canvas design exists**; B1 lands with it.

---

## 4. R-32 + byte proof, threshold, real golden blast

### Inertness / byte proof
Both consumers reduce to `max(2r, w)` (B) or `max(existing_pad, overhang)` (A). Let `r_eff = self._node_radius`
(20, or less when scaled down by node count) and `tw` = widest painted node label.

- **B (pitch):** `min_sep = max(2*r_eff, tw) + gap`. If `tw ≤ 2*r_eff`, this is *literally* `2*r_eff + gap` — the **identical
  float expression** as today (graph.py:651) → identical positions → identical bytes. Same for `_MIN_H_GAP` (Tree) and
  `_H_PITCH` (Hypercube).
- **A (viewBox):** `_node_label_pad` overhang = `max(0, tw/2 - (r_eff + cx_gap))`. A label inside the circle
  (`tw ≤ 2*r_eff`) is inside the frame → overhang `= 0` (**int 0**) → `left_pad`/`right_reach` unchanged → identical
  `bounding_box` → identical bytes. (The added code must yield int `0`, not `0.0`, in the inert case — the existing comment at
  graph.py:1552 already depends on this property for the pill pads.)

**Sufficient inertness threshold (clean, single number):** `max node label width ≤ 2 * _node_radius`
(≈ **40 px at r=20**, dropping to 24 px at the r=12 floor for ≥16-node graphs). Below it, **both A and B are byte-identical**.

**Trip threshold (what changes a byte):**
- B trips when some adjacent pair has `(w_i + w_j)/2 + gap > current_pitch` (52 Graph `2r+12` / 50 Tree / 56 Hypercube).
- A trips when some node's painted extent `[painted_x - tw/2, painted_x + tw/2]` exceeds `[0, content_w]` in any frame —
  position-dependent, so not a single `tw`; the `≤ 2r` bound is the position-independent *sufficient* condition for no-change.

### Confirmed live at 0.29.0 (fresh probe, translate(r) correctly applied — not the raw-parser error)
`scratchpad/research-nodelabel-fit/probe_dp.tex`, force layout seed 3, `\apply{G.node[a]}{value="dist[v]=infinity"}`:
`tw("dist[v]=infinity")=96`, painted_x = `r + cx` = `20 + 20 = 40` → extent **[-8.0, 88.0]** vs viewBox `[0, 464]` →
**CLIP-L by 8 px**. The frame-clip harm is live; A1 (fold left_overhang 8 → left_pad) fixes it exactly.

### Real byte-golden blast — **~1 doc** (major correction to the prior 97/61/3)
The byte-for-byte golden corpus is `tests/golden/examples/corpus/*.tex` (107 docs, each with a sibling `.html`, asserted
byte-equal by `tests/golden/examples/test_example_html.py`). A measured scan (shipped "Scriba Sans" metric,
`scratchpad/research-nodelabel-fit/scan2.py`) of every Graph/Tree/Forest/Hypercube shape-instance's base ids **and** node/subset
`value=` applies:

| Primitive | shape-instances in byte-goldens | **trip (label > 2r) = re-bless** |
|-----------|-------------------------------|-----------------------------------|
| Graph | 31 | **1** — `test_reference_tex_heavy.tex` node `"Bellman-Ford"` tw=92 > 40 (also `"Dijkstra"` ~62) |
| Tree | 15 | 0 |
| Forest | 0 | 0 |
| Hypercube | 0 | 0 |

- The prior report's **97 Graph / 61 Tree / 3 Hypercube** count docs that *use* the primitive across the broader corpora, **not**
  docs that re-bless. Real re-bless from the byte-golden corpus: **1 Graph doc** (a wide *base* label; A1 handles it with no
  prescan). Node/subset `value=` applies exist in only 2 relevant byte-goldens (`bst_operations.tex` value `"7"`,
  `07_prescan_no_pollution.tex`) — both **short** (≤ 2r) → inert.
- `tests/doc_coverage/corpus` (422 .tex / 303 .html) asserts render **kind/code**, not bytes
  (`tests/doc_coverage/test_doc_coverage.py:107-114`) → **not a byte-golden** → inert unless a doc changes error status (the fix
  never does). So it does not re-bless.
- **The harm is real but under-exercised by the shipped corpus** — a strong argument for the fix: it closes a latent
  author-facing defect (wide DP-state editorials clip/collide today) at a cost of **~1 golden re-bless**.
- Guard `tests/unit/test_layout_constant_sync.py` pins `_NODE_RADIUS`/`_MIN_H_GAP`/`_H_PITCH`/`_NODE_OVERLAP_GAP` — update it
  alongside any B edit (constants gain a `max(…, label)` wrapper, not a new literal).

### Version
`SCRIBA_VERSION` 24 → **25** (any rendered-byte change forces it — project DNA-3; every prior geometry bump did the same,
`scriba/_version.py`). `__version__` 0.29.0 → **0.30.0** (SemVer MINOR: additive layout geometry, no author-facing API removed).

---

## 5. RED tests + golden-verification invariant

### RED unit tests (must FAIL on 0.29.0, PASS after A+B). Primitive-level, "size-what-you-paint", NO playwright.
Helper: `painted_x(prim, node) = translate_x + cx` where `translate_x = r + left_pad` (graph.py:1841) / `r` (tree/forest) /
`left_pad` (hypercube:311); `tw = measure_value_text(display_label, 14)`; frame = `[0, bounding_box().width]`.

1. `test_graph_wide_value_label_within_viewbox` — 5-node force graph, `\apply` a wide `value=` (`"dist[v]=infinity"`, tw=96) to
   an edge-clamped node; assert `painted_x - tw/2 ≥ 0` and `painted_x + tw/2 ≤ bbox.width` for **every** node in **every** frame.
   *FAILS today:* CLIP-L 8 px (confirmed above). *A1 fixes.*
2. `test_graph_adjacent_labels_no_collision` — wide labels on two force-adjacent nodes; assert
   `|painted_x_i - painted_x_j| ≥ (tw_i + tw_j)/2` (no horizontal label overlap). *FAILS today (min_sep label-blind). B1+§3 fixes.*
3. `test_tree_dense_siblings_no_label_collision` — flat root + 8 wide-label children; assert adjacent-sibling label extents
   disjoint. *FAILS today (pitch floors to `_MIN_H_GAP=50`). B2 fixes.*
4. `test_hypercube_wide_value_within_viewbox` — `bits=3`, wide `value=` on `subset[i]`; assert every subset label extent
   ⊆ `[0, bbox.width]`. *FAILS today (`content_w = widest*_H_PITCH`, zero label reserve). A3 fixes.*
5. `test_short_labels_byte_identical` (the inertness guard) — node ids `"S"`/`"A"`, binary masks `"011"`, weight-only edges:
   assert the rendered SVG is **byte-identical** to a captured 0.29.0 baseline (the `≤ 2r` inert case). *PASSES today and after.*

### Automatable golden-verification invariant (confirm the re-bless set is correct, not eyeballed)
A per-golden structural checker, runnable over the whole byte corpus after re-blessing:

```
INVARIANT nodefit(html):
  for each frame, for each primitive P in {Graph,Tree,Forest,Hypercube}:
    W = viewBox.width of P's SVG
    for each node n with painted label L:
      x = painted_x(P, n);  w = measure_value_text(L, 14)
      assert 0 <= x - w/2  and  x + w/2 <= W            # (I1) no frame clip
    for each adjacent node pair (i, j) sharing a row/level:
      assert |x_i - x_j| >= (w_i + w_j)/2                # (I2) no label overlap
```
Parse `painted_x` from the emitted `<g transform="translate(...)">` chain + `<text x>` (accounting for the group translate —
the raw `<circle cx>` alone under-counts by `r`, the documented prior-report pitfall). I1 + I2 holding on every re-blessed
golden proves the new bytes are *correct*, converting the re-bless from a judgement call into a checked invariant. Ship it as
`tests/conformance/test_nodefit_invariant.py` parametrized over the corpus.

---

## Confidence

- **Source-of-truth mechanism — HIGH.** The map is a direct generalization of four shipped, tested monotonic-width fields
  (VariableWatch/Queue/Bar/Forest) grown by the *existing* `_prescan_value_widths` pass; the R-32 floor pattern
  (`set_min_arrow_above`) is the cited precedent. No new emitter phase needed.
- **A (viewBox) edits — HIGH, implementation-ready.** Read-only w.r.t. positions, mirrors `_h_label_pad`/caption fold, int-0
  inert, fixes the confirmed clip (reproduced at 0.29.0). Ships independently of the canvas design.
- **B (pitch) edits — MEDIUM, one spike.** The relayout-after-prescan trigger and the Graph "re-run only `_resolve_overlaps`,
  not the seeded FDL" boundary are sound but unproven end-to-end; recommend a **spike on Graph B1 + canvas coupling** to confirm
  determinism and that the `width-_PADDING` clamp is fully relieved before committing golden re-bless. Tree/Forest/Hypercube B
  are self-contained (own canvas) and lower-risk.
- **Real golden blast — HIGH.** Measured directly against the 107-doc byte corpus with the shipped metric: **1 Graph doc**.
- **Overall: implementation-ready for A; B needs one Graph+canvas spike** (jointly with the graph-canvas-scaling design).
