# Investigation: Smart-label mispositioning & caption clipping in the apartments-window diagram

## Hand-off Brief

1. **What happened.** In the `apartments-window` diagram, `position=below` pill labels render *on top of* the cell body, the long Array caption is clipped at the figure edge, and the `range[1:4]` above-label `(C) ghép` is dropped entirely — three independent defects in the smart-labeling / bbox path. *(Confirmed, all three traced to `path:line`.)*
2. **Where the case stands.** Concluded. Each defect has a Confirmed root cause and a proposed minimal fix; no remaining evidence gap.
3. **What's needed next.** Adversarial review of the fix directions (`bmad-review-adversarial-general`), then implement via `bmad-quick-dev` — defects (2) and (3) are near-trivial; defect (1) needs a small coordinate-contract decision.

## Case Info

| Field            | Value                                                                        |
| ---------------- | ---------------------------------------------------------------------------- |
| Ticket           | N/A                                                                          |
| Date opened      | 2026-06-29                                                                   |
| Status           | Concluded                                                                    |
| System           | scriba @ main (0.20.0), Python 3.14, render via `render.py`                  |
| Evidence sources | Source code, rendered repro (`.demo/apt_window_diagram.html`), user screenshot |

## Problem Statement

User rendered a `diagram` block (`.demo/apt_window_diagram.tex`) — an Array of 5 apartment sizes `[30,40,45,50,60]` with a sliding-window explanation. Observed in the rendered output:

1. `position=below` annotations on `cell[0]` (`(A) quá nhỏ: bỏ căn hộ`) and `cell[4]` (`(B) quá lớn: bỏ ứng viên`) overlap the cell bodies (text drawn over the dim cells `30`/`60`); the long Vietnamese text also overflows horizontally into neighbour cells.
2. The Array's long caption `label="kích thước căn hộ y nằm đâu so với ứng viên x=45, cửa sổ [x-k,x+k]=[40,50]"` is clipped at the right edge of the figure.
3. The `range[1:4]` above-annotation `(C) ghép` does not appear at all.

## Evidence Inventory

| Source                        | Status    | Notes                                                                 |
| ----------------------------- | --------- | --------------------------------------------------------------------- |
| Repro `.tex` + rendered `.html` | Available | `.demo/apt_window_diagram.tex`, `.demo/apt_window_diagram.html`        |
| User screenshot               | Available | Shows (A)/(B) over cells, caption cut at "…y nằm", `(C) ghép` absent   |
| Source: `array.py`            | Available | Anchor resolution, caption render, bbox                               |
| Source: `base.py`            | Available | `emit_annotation_arrows` position-only routing                        |
| Source: `_svg_helpers.py`     | Available | `emit_position_label_svg`, height helpers, `_place_pill`              |
| Source: `_frame_renderer.py`  | Available | `compute_viewbox` / `compute_stable_viewbox`                          |

## Confirmed Findings

### Finding 1 — Position-only labels anchor at the cell TOP edge (y=0), not the cell center

**Evidence:** `scriba/animation/primitives/array.py:408-425` — `_cell_center` / `resolve_annotation_point` returns `y = 0` (commented "top edge of cell — arrows curve above"). `scriba/animation/primitives/base.py:494-498` passes this point verbatim as `anchor_point` to `emit_position_label_svg`.

**Detail:** Cell rects are drawn top-anchored, body spanning `y ∈ [0, CELL_HEIGHT]` (`array.py:272-282`, `y=0, height=CELL_HEIGHT`). `CELL_HEIGHT = 40`, `_arrow_cell_height = 40`.

### Finding 2 — `emit_position_label_svg` assumes `anchor_point` is the cell CENTER

**Evidence:** `scriba/animation/primitives/_svg_helpers.py:3038-3046`:
```
ax, ay = anchor_point
position == "below":  final_y = ay + cell_height/2 + pill_h/2 + gap
position == "above":  final_y = ay - cell_height/2 - pill_h/2 - gap
```
The `± cell_height/2` term only makes sense if `ay` is the cell *center*. Combined with Finding 1 (`ay = 0` = top), for `position=below` the pill center lands at `0 + 20 + pill_h/2 + gap`.

**Detail (quantified):** single-line pill `pill_h ≈ 19` (`line_height=13` + `pad_y*2=6`), `gap = max(4, 40*0.1) = 4` → pill center `final_y ≈ 0 + 20 + 9.5 + 4 = 33.5`, pill span `y ∈ [24, 43]`. Cell body is `[0, 40]`. **The pill sits inside the cell body** (deficit ≈ `cell_height/2 = 20 px`). For `position=above` the sign happens to push the pill into the reserved arrow headroom above `y=0`, so the same off-by-half-cell error is masked.

### Finding 3 — Below-zone is already occupied by the index-label + caption stack, which are not registered obstacles

**Evidence:** `array.py:246-250` places the index-label/caption vstack at `start_y = CELL_HEIGHT + INDEX_LABEL_OFFSET = 40 + 16 = 56`. `array.py:429-435` `resolve_obstacle_boxes` / `resolve_obstacle_segments` are stubs returning `[]`. The placement registry `placed` (`base.py:452`) only contains other pills.

**Detail:** Even if Finding 2 were corrected so the below-pill cleared the cell (center ≈ `40 + 9.5 + 4 = 53.5`), it would then collide with the index row at `y≈56`. The collision-avoidance engine (`_place_pill` / legacy nudge loop) cannot push it clear because neither the cells nor the index/caption text are obstacles. So defect (1) is two stacked problems: **(1a)** half-cell anchor deficit (primary, causes the visible overlap); **(1b)** below-zone contention with the index/caption rows.

### Finding 4 — Long position-label pill is never x-clamped in the no-obstacle path → horizontal overflow

**Evidence:** `_svg_helpers.py:3093-3126` — the legacy (no `primitive_obstacles`) branch nudges only vertically/by `placed` overlap and does **not** clamp `final_x` to `[pill_w/2, …]`. The x-clamp (`clamped_x = max(final_x, pill_w/2)`) exists only in the `primitive_obstacles` branch (`:3086`). Our diagram has no segment obstacles (`_prim_seg_obs = ()`), so it takes the legacy branch.

**Detail:** For `cell[0]`, `final_x = ax = cw//2 = 30`. `(A) quá nhỏ: bỏ căn hộ` produces a wide pill centered at x=30 → spills past the left figure edge (clipped) and rightward over `cell[1]`.

### Finding 5 — `range[a:b]` annotation targets do not resolve → label silently dropped

**Evidence:** `array.py:408-418` `_cell_center` matches only `_CELL_RE` (`cell[i]`); there is no branch for `_RANGE_RE` (imported at `array.py:69` but unused in anchor resolution). `base.py:492-493`: `dst_point = self.resolve_annotation_point(target)`; the `if dst_point is not None:` guard at `:493` fails for `scale.range[1:4]` → `emit_position_label_svg` is never called.

**Detail:** `validate_selector` (`array.py:185-188`) *accepts* `range[lo:hi]`, so the annotation passes parsing/validation but is dropped at render time — no warning. This is why `(C) ghép` vanishes with no error.

### Finding 6 — Caption width is excluded from the Array bounding box → viewBox too narrow → centered non-wrapping caption clipped

**Evidence:** `array.py:316-332` renders the caption with `fo_width=total_width` and `center_x = total_width//2`, where `total_width = _total_width() = size*cell_width + (size-1)*gap` (`array.py:439-442`) — the cell-row width only. `bounding_box()` returns `width = _total_width()` (`array.py:369, 406`); the caption contributes to height only (`array.py:384-396`). `_frame_renderer.py:150-163` `compute_viewbox` sets `vb_width = max(prim bbox width) + 2*PADDING`. The caption is plain text → non-wrapping centered SVG `<text>` (`_svg_helpers` text path), so any caption wider than the row extends past both viewBox edges and is clipped by the SVG viewport (`_frame_renderer.py:505-510`, `max-width:vb_width`).

**Detail:** Independently confirms the prior general-purpose agent's finding. Same caption-width-ignored pattern likely affects `grid.py` / `dptable.py` (see `scriba-scene-primitives.css:462-473` shared center-anchored caption convention) — Side Finding, not verified here.

## Source Code Trace

| Element       | Detail                                                                                                   |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| Defect 1 origin | `_svg_helpers.py:3044-3046` (below offset) × `array.py:416` (anchor `y=0`); contention `array.py:246,429` |
| Defect 1 trigger | any `position=below` position-only annotation on an Array                                               |
| Defect 4 origin | `_svg_helpers.py:3093-3126` (legacy branch, no x-clamp)                                                 |
| Defect 5 origin | `array.py:408-418` (`_cell_center` lacks `_RANGE_RE`), guard `base.py:493`                              |
| Defect 6 origin | `array.py:369,406,439-442` (`_total_width` excludes caption); `_frame_renderer.py:150-163`             |
| Related files | `array.py`, `base.py`, `_svg_helpers.py`, `_frame_renderer.py`, `_html_stitcher.py:745-775`            |

## Conclusion

**Confidence: High.** All three reported symptoms have Confirmed, deterministic root causes traced to `path:line`; defect (1) decomposes into a primary half-cell anchor error plus a secondary below-zone contention.

- **(1) Below-labels overlap cells** — anchor point is the cell *top* (`y=0`) but `emit_position_label_svg` offsets as if it were the cell *center*, so `position=below` lands `cell_height/2 ≈ 20 px` short, inside the cell body. Secondary: the below-zone is already filled by the non-obstacle index/caption stack.
- **(4) Horizontal overflow** — the no-obstacle placement branch never x-clamps the pill, so a wide label spills past the figure edge.
- **(5) `(C) ghép` dropped** — `range[a:b]` targets are validated but not resolved to an anchor; the `dst_point is None` guard silently skips emission.
- **(6) Caption clipped** — caption width is excluded from `bounding_box`, so `compute_viewbox` sizes the viewBox to the cell-row width and the centered non-wrapping caption is clipped.

## Recommended Next Steps

### Fix direction

- **Defect 5 (anchor for range)** — in `array.py` `_cell_center`/`resolve_annotation_point`, add a `_RANGE_RE` branch returning the geometric center of cells `lo..hi`: `x = (left_of(lo) + right_of(hi)) / 2`, `y = 0` (keep top-edge convention). Smallest, highest-value fix; restores `(C) ghép`.
- **Defect 1a (below anchor)** — make the position-label vertical contract unambiguous. Option A: resolve the anchor to the cell *center* (`y = CELL_HEIGHT/2`) for position-only labels. Option B: in `emit_position_label_svg`, treat `ay` as the top edge and use `final_y = ay + cell_height + pill_h/2 + gap` for `below` (and `ay - pill_h/2 - gap` for `above`). Pick one and document it — Option A is less invasive to `above` arrows.
- **Defect 1b (below-zone contention)** — register the index-label/caption stack (and optionally cell rects) as obstacles via `resolve_obstacle_boxes`, OR offset below-labels past `CELL_HEIGHT + INDEX_LABEL_OFFSET + caption height` when index/caption are present.
- **Defect 4 (x-clamp)** — apply the same `clamped_x = max(final_x, pill_w/2)` (and a right-edge clamp once a viewbox width is threaded in) in the legacy no-obstacle branch.
- **Defect 6 (caption width in bbox)** — in `array.py` compute `caption_w = estimate_text_width(self.label, _FONT_SIZE_CAPTION) + 2*_CELL_HORIZONTAL_PADDING`; return `width = max(_total_width(), caption_w)` from `bounding_box()`; center the caption on `bbox_width/2` with `fo_width=bbox_width`. No CSS change.

### Diagnostic

- Set `SCRIBA_DEBUG_LABELS=1` and re-render to dump per-pill `natural_x/y`, `final_x/y`, `collision_unresolved` — confirms the below-pill `final_y` deficit and the dropped range label (no pill emitted) before/after the fix.

## Reproduction Plan

1. `python3 render.py .demo/apt_window_diagram.tex -o .demo/apt_window_diagram.html`
2. Open the HTML. Expect: `(A)`/`(B)` text over cells 0/4; caption cut at "…y nằm"; no `(C) ghép`.
3. Post-fix expected: `(A)`/`(B)` fully below cells & inside figure; full caption visible; `(C) ghép` centered above cells 1–3.

## Side Findings

- `grid.py` and `dptable.py` very likely share the caption-width-excluded-from-bbox pattern (Finding 6) — same center-anchored caption convention per `scriba-scene-primitives.css:462-473`. *(Hypothesized; not verified.)*
- `validate_selector` accepting `range[a:b]` while `resolve_annotation_point` ignoring it is a contract split — any primitive relying on this pair has the same silent-drop risk for range targets. *(Deduced from `array.py:185-188` vs `:408-418`.)*

## Follow-up: 2026-06-29 — Adversarial review corrections

Two independent skeptical reviewers re-traced the source. Material corrections to the fix directions:

### Finding 1a — fix corrected: SCOPED Option A, not global

- **Global Option A is REFUTED.** `_cell_center`/`resolve_annotation_point` (`array.py:416`) is *shared with arrow geometry* (`base.py:469, 506-507`); the `y=0` comment exists *"so arrows curve above"*. Changing it to `y=20` regresses every Array arrow. The case file's "Option A less invasive to arrows" was wrong.
- **`above` labels are internally consistent, not lucky.** Both `emit_position_label_svg` (`_svg_helpers.py:3043`) and `position_label_height_above` (`_svg_helpers.py:2792-2805`) treat `ay=0` as the *center*; the `arrow_above` translate (`array.py:219-220`) absorbs the negative coords. Only `below` (positive) lands in the cell.
- **Recommended:** give Array a **position-label-specific anchor = cell center (`y = CELL_HEIGHT/2 = 20`)**, separate from `resolve_annotation_point` (which keeps `y=0` for arrows). This aligns Array with the contract that `emit_position_label_svg`, `position_label_height_*`, and Plane2D *already* honor ("anchor = element center"). Companion required: bump the array below-reservation by `cell_height/2` (since `position_label_height_below` bakes `ay=0`), else the below pill clips at the bbox bottom.
- **Option B is REFUTED** (worst footprint): `emit_position_label_svg` is shared by Array, DPTable, Plane2D; `position_label_height_*` by 11 primitives. Plane2D uses a point-*center* anchor where the current `±cell_height/2` is already correct — Option B would push Plane2D point-labels a full cell away (visual regression).

### Finding 1b — confirmed; fix = register obstacles OR offset past y≈56

Below pill (even corrected, center≈53.5) collides with index/caption stack at `y≈56`. Fix: register the index/caption stack (and/or cell rects) as obstacles in `array.py:429-435`, or offset below-labels past `CELL_HEIGHT + INDEX_LABEL_OFFSET + caption_h`.

### Finding 4 — OVERSTATED / partially REFUTED

- The legacy branch **does** clamp left: `_svg_helpers.py:3130` `clamped_x = max(final_x, pill_w/2)`, plus unconditional post-branch clamps `:3145` (`pill_rx = max(0, …)`) and `:3147` (`fi_x = max(fi_x, pill_w//2)`). **"Spills past the left figure edge" is wrong** — `cell[0]`'s left edge is hard-clamped to 0.
- Real residual gaps: (a) **no right-edge clamp** (no viewbox width threaded; obstacles branch uses sentinel `_vb=8192`, `:3070-3072`); (b) the left clamp pushes an over-wide pill *rightward over `cell[1]`* — clamping cannot fix this; only **wrapping/shrinking** the pill can, since it is wider than one cell.

### Finding 5 — confirmed; wider than stated

The range branch is reached by plain (`base.py:469`) and arc (`base.py:506-507`) arrows and by `arrow_height_above` (`array.py:208-210`), so it **also enables arrow-to-range geometry**, not just `(C) ghép`. `y=0` for the range center is correct (consistent with top-edge contract). Regression risk ≈ 0 (no corpus/test uses range *annotations*; corpus `range[...]` is only `\recolor`/`\highlight`, a different path). **Add tests** for `arrow=true`→range and `arrow_from`=range, and check `arrow_height_above` doesn't under-reserve for a wide arc span.

### Finding 6 — defect confirmed; proposed fix REFUTED as written

- Renderer centers the whole group on `bw` (bbox width) and **ignores `bbox.x`** (`_frame_renderer.py:41, 579` `x_offset=(vb_width-bw)//2`). Centering the caption on `bbox_width/2` while the cell row stays at local `x=0` **left-shifts the row** by `(caption_w-total_width)/2` → row/caption misalignment.
- **Correct fix:** `width = max(_total_width(), caption_w)` (x stays 0) **and shift all cell content** (rects, values, index labels) right by `row_dx = (bbox_width - total_width)//2`, **and** center caption on `bbox_width//2`. Negative/symmetric-x is not an option (renderer ignores `bbox.x`, clips local negative x).
- **Sync hazard:** the caption-width formula must be applied identically in **both** `emit_svg` (`array.py:318`) and `bounding_box` (`array.py:369`) — the docstring at `array.py:371` already warns they must stay in sync.
- `estimate_text_width` (`_text_render.py:68-108`) is a heuristic (flat 0.62em for non-wide glyphs); can under-estimate mixed-Latin captions → keep a generous safety pad beyond `2*_CELL_HORIZONTAL_PADDING`.

### Golden-corpus regression scope (verified)

- **Defect 6 fix:** `tests/golden/examples/test_example_html.py` is byte-for-byte; **only long-caption arrays** rebaseline (a caption fitting within the row leaves width and `center_x` unchanged → no diff). Enumerate captioned fixtures (`test_array_arrows`, `increasing_array`, `two_sum_editorial`, `union_find_array`, `dijkstra`, `tutorial_en`, …) and human-review.
- **Defect 1 fix (scoped Option A):** keeps `resolve_annotation_point` y=0 → **arrows unchanged → array arrow goldens safe.** No array corpus uses position-only labels, so the defect-1 fix breaks **no** existing array golden.
- `tests/golden/smart_label/` is **not** affected (manual-SVG fixtures with hardcoded viewBox).
- Add unit cases: captioned-array `bounding_box().width` (`tests/unit/test_primitive_array.py`), below-label clears cell, range annotation emits a pill.

### Updated Conclusion

Confidence **High** on diagnosis. Fix is **non-trivial / multi-part** (case file under-stated this): scoped-Array-center anchor + below-reservation bump + obstacle registration (defect 1); range anchor branch + arrow-to-range tests (defect 5); bbox width + row/index re-centering applied in both emit paths + safety pad (defect 6); defect 4 reduced to optional right-clamp + wrap (not the primary cause of the visible overlap — defect 1a is).

### Tooling note

GitNexus MCP crashed mid-investigation (orphan `lbug.wal` 1.5MB without shadow → read-only replay hang). Quarantined the WAL and re-ran `gitnexus analyze` to rebuild a clean, current index. Impact analysis for this case was done manually via grep (recorded in the prior turn).
