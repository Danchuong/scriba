# Sweep: measure-mutate ordering (twin-drift)

- **Date:** 2026-07-02
- **Scope:** `scriba/animation/_html_stitcher.py`, `_frame_renderer.py`, `renderer.py`, `scene.py`, `primitives/base.py`, `primitives/_extent.py`, and representative primitives (`grid.py`, `array.py`, `stack.py`, `queue.py`). Investigate-only; no source modified.
- **Context / HEAD:** `369e80f` — *fix(stitcher): floor the arrow lane BEFORE measuring the scene viewBox*. That commit closed one instance of this family (viewBox measured before `_apply_min_arrow_above`). This sweep hunts the rest.
- **Repros:** run with `.venv/bin/python` from the scratchpad (`AnimationRenderer().render_block` + `detect_animation_blocks` + `RenderContext`), plus direct calls into the real stitcher helpers. Numbers below are observed output.

The shape of the bug family: a layout value is **measured** at one pipeline stage, the measured state is **mutated** at a later stage, and a **consumer** then trusts the stale measurement — or two consumers measure "the same layout" at different stages and disagree. The scene owns three measurement passes that must agree with the emit loop:

1. `compute_stable_viewbox(frames, primitives)` — the viewBox. Replays structural `apply_command` on **deep copies** (`_frame_renderer.py:210-231`).
2. `_build_reserved_offsets(frames, primitives)` — the per-primitive y stacking. Calls `set_annotations` + `bounding_box()` only, on the **real** primitives (`_html_stitcher.py:62-84`).
3. `_emit_frame_svg` — the actual paint. Pre-applies `apply_command` (`_frame_renderer.py:462-489`) **and** applies `set_state`/`set_value`/`set_label`/`prim.label` in the emit loop (`_frame_renderer.py:605-642`).

Any mutation that (2) and (3) treat differently, or that (1)/(2) never see but (3) applies, is a drift.

---

## Findings

### Finding A — Per-frame caption change (`\apply{p}{label=…}` / relabel) is unmeasured → caption clips past the viewBox or overlaps the next primitive

- **Severity:** HIGH
- **Grade:** Confirmed with repro output.

**Measure points (both miss the caption):**
- `compute_stable_viewbox` replays only `apply_command` + `set_annotations` on the deep copies (`_frame_renderer.py:213-231`). It never touches `self.label`.
- `_build_reserved_offsets` sets annotations and calls `bounding_box()` (`_html_stitcher.py:62-84`). It never touches `self.label`.

**Mutate point (only the emit loop applies it):**
- `_emit_frame_svg` sets the caption directly for a bare-shape `\apply{p}{label=…}`: `prim.label = str(label_val)` (`_frame_renderer.py:620-622`), and per-part relabels via `prim.set_label(suffix, …)` (`_frame_renderer.py:639-641`).
- Root cause of the asymmetry: the scene stores the label into `target_state.label` and **explicitly excludes it from `apply_params`** — `extra = {k: … for k in cmd.params if k not in ("value", "label")}` (`scene.py:706-719`). So the label never rides the `apply_command` channel that `compute_stable_viewbox` replays; it is a first-class per-target field the two measurement passes ignore.

**Consume point:**
- `bounding_box()` folds the caption into height and width: grid `h = th + self._below_lane_height() + self._caption_block_height(tw)` (`grid.py:349`), `core_w = max(tw, self._caption_block_width(tw))` (`grid.py:347`); the shared helpers live in `base.py:643-651` (`_caption_block_height`) and `base.py:629-641` (`_caption_block_width`). The viewBox and the reserved offsets are computed **without** the caption, so the emitted caption paints into space nobody reserved.

**Observed divergence:**
- *Clip (single / last primitive).* Grid, no caption in frame 1, `\apply{g}{label="…"}` in frame 2:
  - viewBox = **208×148** on every frame (identical for the captioned frame — proof it was never measured).
  - caption `<text>` absolute baseline = 12 (translate) + 143 = **151** → below the 148 viewBox floor by ~7px (≥11px with descender), and horizontally clipped (needs width 220).
  - Control — same caption declared in the prelude `\shape{g}{Grid}{…, label="…"}`: viewBox = **220×169**, caption baseline 151 ⊆ 169 (fits). The 169−148 = **21px** height and 220−208 = **12px** width are exactly the caption block the `\apply` path failed to reserve.
- *Overlap (caption-bearing primitive not last).* Grid (2×2) with a late 3-line caption, Array stacked below:
  - Array rects sit at **[115..153] in BOTH frames** — the late caption reserved **zero** downstream space.
  - Caption wraps to 3 tspan lines at local y [101,114,127] → block bottom ≈ 12+127+4 = **143**, overlapping the array top (115) by **28px**. The last two caption lines paint on top of the array cells.

This is the exact clip/cover symptom of `369e80f`, triggered by a caption mutation instead of an arrow lane. It rides every cross-frame path (static, interactive widget + print, substory) because they all share the two measurement helpers.

---

### Finding B — `_build_reserved_offsets` omits the structural push/pop replay that `compute_stable_viewbox` performs → a growing primitive overlaps everything stacked below it

- **Severity:** HIGH (full inter-primitive overlap; borderline CRITICAL for multi-primitive scenes).
- **Grade:** Confirmed with repro output.

**Two consumers measure the same primitive at different structural states:**
- `compute_stable_viewbox` replays `apply_command` **cumulatively on deep copies** (`_frame_renderer.py:210-231`) → the viewBox is sized to the **grown** extent. Correct.
- `_build_reserved_offsets` performs **no** `apply_command` replay (`_html_stitcher.py:46-105`) — it measures `bounding_box()` on the real primitives, which are still at their **initial** structural state (prescan restored structure; `compute_stable_viewbox` mutated only copies). So downstream y offsets are stacked from the **pre-growth** height.

**Mutate point:** `_emit_frame_svg` pre-pass applies push/pop cumulatively per frame (`_frame_renderer.py:462-489`) → by the last frame the real primitive is fully grown.

**Consume point:** the emit loop pins downstream y from `reserved_offsets[shape_name]` (`_frame_renderer.py:588`) and does **not** re-accumulate (`_frame_renderer.py:661`), so the lower primitive stays at its pre-growth slot while the upper one grows into it.

**Observed divergence** — `\shape{s}{Stack}{items=[1]}` above `\shape{a}{Array}{values=[7,8,9]}`, `push 10/20/30`:
- `compute_stable_viewbox` → viewBox `0 0 208 256` (replays growth; correct).
- `_build_reserved_offsets` → `s:(0,12)`, `a:(0,84)` — array y = 12 + 52 (initial 1-item stack) + 20 gap. Stack bbox height at that measurement = **52**; after the pushes it is **172**.
- Rendered rects (static mode): stack `[21..55]→[21..95]→[21..135]→[21..175]` while the array stays pinned at `[85..123]`. Overlap grows **0 → 10 → 50 → 90px**. The viewBox (256) is tall enough, so there is no clip — the array simply renders **inside** the grown stack.
- Same scene in the default **interactive** mode: last print frame `stack[21..175] array[85..123]` → **90px overlap**. Affects the widget and print output identically.

Any timeline-growing primitive placed above another triggers this: Stack `push`, Queue `enqueue`, LinkedList append, Tree/Graph `add_node`. Nothing enforces "growing primitive must be last," so e.g. a BFS queue declared above its graph, or a call-stack above the array it drives, corrupts every post-growth frame. Distinct root cause from A: here the two measurement passes *disagree* (one replays structure, the other does not), rather than both missing a mutation.

---

## Cleared

- **`_annotation_extent` / `_extent_above_cache` vs `_min_arrow_above` (the flagged cache).** Invalidated only in `set_annotations` (`base.py:351-352`), but safe: the extent is measured by `_measure_emit` → `emit_annotation_arrows` into a scratch buffer **without** the `translate(left_pad, arrow_above)` wrapper that `emit_svg` applies (`grid.py:265`), so the measured extent lives in the pre-shift frame and is invariant to the floor. Repro: `annotation_height_above()` = 0 before and after `set_min_arrow_above(500)` + forced recompute; `bounding_box().height` delta equals the floor exactly (124 → 624). `_reserved_arrow_above = max(natural, floor)` (`base.py:456-458`) composes them without feeding the floor back into the measurement. No feedback loop.
- **`set_value` / `set_state` / `set_label` not invalidating the extent cache.** Within a frame the order is `set_annotations` (invalidate, `_frame_renderer.py:577-578`) → `bounding_box()` (measure+cache, line 580) → `set_value`/`set_state`/`set_label` (lines 632-641) → `emit_svg()` (reuse cache, line 652). `bounding_box` and `emit_svg` read the **same** cached extent, so they stay mutually consistent (measured == painted for that frame). `set_value` changes displayed **text**, not cell geometry — cell widths are pinned to their cross-frame max by `_prescan_value_widths` (`_frame_renderer.py:45-112`) *before* any measurement — and `set_state` is a CSS class. No geometry drift.
- **`_prescan_value_widths` timing.** It applies every frame's `set_value`, then restores display state while width fields stay at their monotonic max (`_frame_renderer.py:98-112`). Both consumers see the identical prescanned widths (`compute_stable_viewbox` deep-copies *after* prescan; `_build_reserved_offsets` measures the same prescanned primitives), so value-width does **not** drift between them. This is the existing fix for the value-width family, working as intended.
- **Per-frame x-centring vs reserved y (Finding D candidate).** `x_offset = (vb_width - bw) // 2` uses the per-frame bbox width while y uses the reserved max (`_frame_renderer.py:588-589`). It can only wobble horizontally, never clip (viewBox width is the cross-frame max). In practice width is stable: capacity primitives fix their footprint (Queue `enqueue` growth → `translate_x` constant at 12, **0px** jitter across 4 frames), and a grid left-pill moved width by 1px. Cosmetic at most; LOW.
- **Diagram path** (`emit_diagram_html`, `_html_stitcher.py:789-831`). Single frame, and it passes **no** reserved_offsets, so `_emit_frame_svg` self-accumulates y from actual per-frame bboxes (`_frame_renderer.py:547-555, 661-662`); `compute_stable_viewbox([frame], …)` replays that one frame's structure. Immune to cross-frame B; only theoretically exposed to A if a lone diagram frame both declares and re-captions the same shape (not a cross-frame scenario).
- **Substory + print-substory paths** (`emit_substory_html` `_html_stitcher.py:380-400`; print substory `:590-611`). Post-`369e80f` they call the identical `_apply_min_arrow_above` → `compute_stable_viewbox` → `_build_reserved_offsets` → `_emit_frame_svg` trio as the parent, and the widget and print substory now measure identically. They introduce no *additional* drift, but they **inherit** A and B verbatim.
- **`_apply_min_arrow_above` ordering** (`_html_stitcher.py:265, 499, 387, 597`). Now runs before `compute_stable_viewbox` at all four call sites (the `369e80f` fix); the deepcopy carries the floor. Verified consistent across parent + substory + print-substory. Closed.

---

## Verdict

The `369e80f` fix closed the specific arrow-lane-floor ordering, but the measure-mutate / twin-drift family is **not fully closed**. Two confirmed divergences remain in the shared measurement helpers, both the same "two consumers measure the same layout at different points of the mutation pipeline" shape as the shipped bug. **Finding A:** per-frame caption mutations (`\apply{p}{label=…}` and per-part relabel) are applied only in the emit loop and seen by neither `compute_stable_viewbox` nor `_build_reserved_offsets`, reproducing the exact caption clip (viewBox 148 vs painted 151) and next-primitive overlap (28px) symptoms. **Finding B:** `_build_reserved_offsets` lacks the cumulative push/pop replay that `compute_stable_viewbox` has, so any timeline-growing primitive above another overlaps it (measured 90px in the final frame, static and interactive). The cache, prescan, x-centring, diagram, and substory paths audited clean. Closing the family means teaching both measurement passes the mutations the emit loop performs — apply per-frame labels when probing bounding boxes, and replay structural `apply_command` inside `_build_reserved_offsets` (mirroring `compute_stable_viewbox`) — or, more robustly, deriving the viewBox and the reserved offsets from a single replay so they can never disagree.

---

## Structural Fix Design (2026-07-02)

### Design summary

Replace the two independent measurement passes — `compute_stable_viewbox` (replays structure on deep copies) and `_build_reserved_offsets` (measures the real primitives at their initial state) — with **one shared replay** (`measure_scene_layout`) that steps the frame timeline on a single set of deep copies, applying every mutation the emit loop will apply that changes `bounding_box()` (structural `apply_command`, the caption `self.label`/per-part `set_label`, and per-frame `set_annotations`), and captures per-frame checkpoints. The **global max** of those checkpoints becomes the viewBox and the **per-primitive max bbox** becomes the y-stacking envelope, so the two consumers derive from the same numbers and cannot drift by construction — this closes Finding A (captions now reserved by both) and Finding B (structural growth now replayed for the offsets too). Real primitives stay untouched (R-32.4 purity, strict improvement — the measurement no longer mutates them at all), the 369e80f floor-before-measure ordering is preserved (the deep copies inherit `_min_arrow_above`), and it is net cheaper (one measurement loop and one deepcopy instead of two loops).

Prototype validated in scratchpad (`probe_unified.py`): Stack-push-above-Array moved the Array's reserved y from `84` (under the initial 52 px stack → 90 px overlap) to `204` (under the grown 172 px stack → no overlap) with viewBox unchanged at 256; a Grid gaining a late caption grew the viewBox from `146×140` to `247×140` while the real `g.label` stayed `None`.

### Definitive mutation inventory

Every per-frame thing the emit loop does that can move `bounding_box()`, and whether each measurement pass currently sees it. Paths are `scriba/animation/…`.

| Mutation (emit loop) | Applied at | Changes bbox? | `compute_stable_viewbox` sees it? | `_build_reserved_offsets` sees it? | Verdict |
|---|---|---|---|---|---|
| Structural `apply_command` pre-pass (push/pop/enqueue/add_node/add_edge) | `_frame_renderer.py:462-489` (mutates **real** prims) | YES — grows extent (Stack height, Queue width, Tree/Graph topology) | YES — replayed on copies `_frame_renderer.py:210-231` | **NO** — never replays `apply_params` (`_html_stitcher.py:62-84`) | **Finding B root cause** |
| Bare-shape caption `prim.label = str(label_val)` | `_frame_renderer.py:620-622` | YES — caption block folds into w & h (`grid.py:347,349`; helpers `base.py:629-651`) | **NO** — replays only `apply_params`; label is excluded from that channel | **NO** — measures `bounding_box()` only | **Finding A root cause** |
| Per-part relabel `prim.set_label(suffix,…)` | `_frame_renderer.py:639-641` | Primitive-dependent (Grid cell: no — probe confirmed; value-cell prims can widen) | **NO** | **NO** | **Finding A root cause** |
| `set_annotations(prim_anns)` (arrow lane above/below + h-pads; invalidates `_extent_above_cache` `base.py:352`) | `_frame_renderer.py:577-578` | YES | YES — `compute_viewbox(sim, annotations=…)` `_frame_renderer.py:231` | YES — `_html_stitcher.py:68-69` | consistent |
| `_min_arrow_above` floor (`set_min_arrow_above`, consumed in `_reserved_arrow_above` `base.py:450-458`) | `_apply_min_arrow_above` `_html_stitcher.py:193-221`, run before the viewBox at all 4 sites | YES — floors the arrow lane | YES — deepcopy inherits the int, runs post-floor | YES — measures reals post-floor | consistent (369e80f) |
| `set_value(suffix,str(val))` (display text; widths pinned to monotonic max) | `_frame_renderer.py:632-634`; widths pre-pinned by `_prescan_value_widths` `_frame_renderer.py:45-112` | width only, and pinned to cross-frame max **before** any measurement | both see prescanned max (deepcopy is post-prescan; reals are prescanned) | same | consistent (cleared) |
| `set_state(suffix,state)` | `_frame_renderer.py:629` | NO — CSS class | n/a | n/a | inert |
| `prim._highlighted = …` | `_frame_renderer.py:642` | NO | n/a | n/a | inert |

Only two rows drift: structural `apply_command` (B) and the caption label channel (A). Both are exactly the "measure at stage X, mutate at stage Y" shape of 369e80f.

Data-flow note (why the label is a separate channel): the scene stores the caption into `ShapeTargetState.label` and **excludes it from `apply_params`** (`scene.py:706-710,719`); the renderer surfaces it as a distinct `"label"` key on the target dict (`renderer.py:282-283`), sibling to `"apply_params"` (`renderer.py:284-285`). The emit loop reads both keys; the two measurement passes read `"apply_params"` (viewbox) or neither (offsets). The shared replay must read **both**.

### Proposed architecture

**New function — one pass, both outputs. Lives in `_frame_renderer.py`** (it already owns `compute_viewbox`, the deepcopy/`_ctx`-detach dance, `_apply_param_list`, `_normalize_bbox`, and the `_PADDING`/`_PRIMITIVE_GAP` constants; `_html_stitcher` already imports from it).

```python
def measure_scene_layout(
    frames: list[Any],
    primitives: dict[str, Any],
) -> tuple[str, dict[str, tuple[float, float]]]:
    """Single shared replay of the frame timeline on ONE set of deep copies.

    Applies every mutation the emit loop applies that changes bounding_box()
    — structural apply_command, the caption (self.label + per-part set_label),
    and per-frame annotations — and records per-frame checkpoints.  Returns:
      * viewbox      "0 0 W H"  — global max over all checkpoints
      * reserved     {shape: (0.0, y_cursor)} — y-stacking from the per-primitive
                     MAX bbox height across all checkpoints
    Real primitives are never mutated (R-32.4).  Must run AFTER
    _apply_min_arrow_above (the copies inherit _min_arrow_above; 369e80f order).
    """
```

Rewire the two existing helpers to the single source (keeps their names/imports alive, zero churn on any code that references them):

```python
# _frame_renderer.py
def compute_stable_viewbox(frames, primitives):      # diagram + any external caller
    return measure_scene_layout(frames, primitives)[0]

# _html_stitcher.py  (or delete and inline at the 4 sites)
def _build_reserved_offsets(frames, primitives):
    return measure_scene_layout(frames, primitives)[1]
```

**Before (each of the 4 full pipelines — static / interactive / interactive-substory / print-substory):**

```python
_prescan_value_widths(frames, primitives)      # unchanged
_apply_min_arrow_above(frames, primitives)     # unchanged — floor first (369e80f)
viewbox          = compute_stable_viewbox(frames, primitives)   # deepcopy pass #1
reserved_offsets = _build_reserved_offsets(frames, primitives)  # real-prim pass #2 (drifts)
# … _emit_frame_svg(frame, primitives, …, reserved_offsets=reserved_offsets)
```

**After:**

```python
_prescan_value_widths(frames, primitives)      # unchanged
_apply_min_arrow_above(frames, primitives)     # unchanged — floor first (369e80f)
viewbox, reserved_offsets = measure_scene_layout(frames, primitives)  # one pass, agrees
# … _emit_frame_svg(frame, primitives, …, reserved_offsets=reserved_offsets)
```

**Inside `measure_scene_layout` (pseudocode):**

```python
detach _ctx on reals;  sim = {n: deepcopy(p)};  restore _ctx      # as compute_stable_viewbox today
for p in sim: p._extent_above_cache = None                        # EDGE E3: _NO_EXTENT identity
max_bbox = {}; max_w = max_h = 0
def capture():                       # one row = _PADDING + Σ(h) + gaps ; per-prim max bbox
    total = _PADDING; first = True; row_w = 0
    for n, p in sim.items():
        _,_,w,h = _normalize_bbox(p.bounding_box())
        max_bbox[n] = componentwise_max(max_bbox.get(n), w, h)
        total += (0 if first else _PRIMITIVE_GAP) + h; first = False; row_w = max(row_w, w)
    max_w = max(max_w, row_w + 2*_PADDING); max_h = max(max_h, total + _PADDING)
capture()                            # initial (pre-frame) extent
for frame in frames:
    for n, p in sim.items():
        set_annotations(prim_anns_for(frame, n))                  # arrow lane (invalidates cache)
        for target_key, td in expand(frame.shape_states[n]).items():
            apply_command(td["apply_params"]) via _apply_param_list  # structural (B)
            if td.get("label") is not None:                          # caption (A)
                if target_key == n: p.label = str(td["label"])       #   bare-shape → self.label
                else:               p.set_label(suffix, str(td["label"]))  # per-part relabel
    capture()
reserved = {}; y = _PADDING
for n in primitives:                 # declaration order (R-32.6)
    reserved[n] = (0.0, y); y += max_bbox[n].height + _PRIMITIVE_GAP
return f"0 0 {max_w} {max_h}", reserved
```

`_emit_frame_svg` is unchanged: it still takes `reserved_offsets`, still uses the per-frame bbox only for x-centring (`_frame_renderer.py:588-589`), and still self-accumulates when `reserved_offsets is None` (diagram + direct-call tests). Selector expansion (`_expand_selectors`) should be applied in the replay for parity with the emit loop's `top`/`all`/`range` handling.

**Call sites to convert (4 full pipelines):** `_html_stitcher.py` — `emit_animation_html` (273+277), `emit_substory_html` (389+397), `emit_interactive_html` (505+509), print-substory inside `emit_interactive_html` (602+608). **Left as-is:** `emit_diagram_html` (813) stays on the `compute_stable_viewbox` wrapper — single frame, `reserved_offsets=None`, immune per the Cleared section (adopting the tuple form there is optional and harmless).

**Cost.** Today: 1 deepcopy set + `(F+1)·P` bbox calls (viewbox) + `F·P` bbox calls (offsets) ≈ `(2F+1)·P`. After: 1 deepcopy set + `(F+1)·P` bbox calls total. Net ≈ **−F·P bounding_box() calls** (the entire second pass removed), same single deepcopy — e.g. a 10-frame / 3-primitive scene drops from ~63 to ~33 bbox calls (~48%). No deepcopy added; strictly cheaper.

### Edge cases & resolutions

1. **Label excluded from `apply_params` (`scene.py:709`).** The replay reads the sibling `"label"` key on each target dict (surfaced by `renderer.py:283`), not `apply_params` — applying `p.label = …` for a bare-shape target (`target_key == shape_name`) and `p.set_label(suffix, …)` otherwise, exactly mirroring emit `_frame_renderer.py:620-622` / `639-641`.
2. **Does the label write invalidate the annotation cache?** No — and it does not need to. Probe confirmed `set_label`/`self.label` leave `_extent_above_cache` untouched, but the caption block (`_caption_lines`→`_caption_block_{width,height}`, `base.py:617-651`) reads `self.label` **fresh every `bounding_box()` call** with no cache, so a re-measure after setting the label already reflects it (probe: Grid 122×82 → 223×129 after `prim.label`). The only cache in play (`_extent_above_cache`) is annotation-only and is already invalidated by the per-frame `set_annotations` the replay calls (`base.py:352`). No new invalidation required.
3. **`_NO_EXTENT` sentinel breaks under `deepcopy` (new hazard, found via probe).** `_NO_EXTENT = object()` (`base.py:27`) is compared by identity (`cached is not _NO_EXTENT`, `base.py:389`); `deepcopy` mints a fresh `object()`, so a clone whose cache holds the sentinel returns garbage → `AttributeError: 'object' has no attribute 'min_y'`. Today's `compute_stable_viewbox` survives only because the floor/prescan pre-passes end with `set_annotations([])` (cache→`None`) before it clones. The shared replay must not rely on that accident: reset `p._extent_above_cache = None` on every clone right after deepcopy (one line; shown in pseudocode).
4. **Per-frame value width (`_prescan_value_widths`).** Prescan pins each width-tracking field to its cross-frame monotonic max on the reals **before** the replay, so the clones inherit the max and per-frame `set_value` can only render a value **≤** that width; x-centring uses the actual per-frame bbox width (`_frame_renderer.py:589`) which is `≤` the viewBox max width, so it can wobble horizontally but never clip. The replay need not apply `set_value`. Unchanged from the Cleared analysis.
5. **`apply_command` suffix variance.** Stack/Queue take `apply_command(params)` (no `target_suffix`); Grid/Array have none. Reuse the existing `inspect`-based `accepts_suffix` + `_apply_param_list` already shared by `compute_stable_viewbox` and `_emit_frame_svg` — no per-primitive special-casing.
6. **Queue horizontal growth / Graph `add_edge`.** Queue `enqueue` grows width, not height, so downstream y-stacking is unaffected (only the viewBox width grows, already captured); `add_edge` adds no node, so the Graph bbox is unchanged. Correct by construction — these do not churn.
7. **Purity.** The replay mutates only clones, so unlike today's `_build_reserved_offsets` (which set annotations on the reals then cleared them) it never touches the reals — R-32.4 is satisfied without a restore step.

### TDD plan

RED first, reusing the caption⊆viewBox idiom and `_frames()`/translate-Y regex from `tests/unit/test_scene_layout_floor_order.py` and the per-frame translate-Y extractor from `tests/conformance/test_r32_annotation_stable_layout.py`.

- **`tests/unit/test_scene_layout_caption_reserve.py`** (Finding A):
  - `test_late_caption_fits_viewbox`: Grid, frame 1 no caption, frame 2 `\apply{g}{label="…long multiword…"}`. For the captioned frame parse `viewBox="0 0 (\d+) (\d+)"` and the last `scriba-primitive-label` `y`; assert `translate_y + caption_baseline + descender ≤ viewBox_h`. Fails on HEAD (painted 151 > viewBox 148).
  - `test_late_caption_no_overlap_next_primitive`: captioned Grid above an Array; assert the Array's `translate-Y ≥ Grid translate-Y + Grid caption-block bottom` (the new no-overlap-between-primitives assertion). Fails on HEAD (array pinned at 115, caption bottom 143 → 28 px overlap).
- **`tests/unit/test_scene_layout_growth_reserve.py`** (Finding B):
  - `test_growing_stack_above_array_no_overlap`: `\shape{s}{Stack}{items=[1]}` above `\shape{a}{Array}{values=[7,8,9]}`, push 10/20/30; render static **and** interactive. Add a shared `assert_no_primitive_overlap(svg)` helper: for consecutive stacked `<g translate>` groups, `y[i+1] ≥ y[i] + max_height[i]`. Fails on HEAD (array y=84 inside grown stack → up to 90 px overlap); passes after (array y=204, prototype-confirmed).
  - `test_reserved_offsets_stable_across_frames`: the downstream primitive's translate-Y is identical in every frame (guards against reintroducing per-frame accumulation).
- **Extend `tests/conformance/test_r32_annotation_stable_layout.py`**: add `test_r32X_downstream_y_stable_growing_primitive_above` mirroring the existing `test_r322_downstream_y_stable_*` but triggered by structural `push` instead of annotation growth — same "one stable y across frames" contract, new trigger.

Existing tests that pin current behaviour (verify GREEN, extend, or regenerate):
- **Stay green (contract preserved/strengthened):** `tests/unit/test_scene_layout_floor_order.py` (caption⊆viewBox after floor), `tests/conformance/test_r32_annotation_stable_layout.py` (`r321` intra-bbox, `r322` downstream-y for annotation growth, `r324` purity, `r326` determinism). Confirm these still pass.
- **Unaffected (fix touches neither):** `tests/unit/test_animation_emitter.py` exact `compute_viewbox` strings (224×64 / 324×144 / 424×324 — `compute_viewbox` is not modified); every per-primitive exact-bbox pin (`test_primitive_{queue,linkedlist,hashmap,variablewatch,stack,graph,numberline}.py` — `bounding_box()` is not modified); `test_primitive_layout.py::TestPixelReproduction`; direct-call `_emit_frame_svg(reserved_offsets=None)` tests.
- **Regenerate after human diff review (byte-for-byte goldens, `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/`):** only the small predicted-churn set below.

### Blast radius & risks

**Code:** one new function in `_frame_renderer.py`; `compute_stable_viewbox` and `_build_reserved_offsets` become thin wrappers; 4 call sites in `_html_stitcher.py` rewired to the tuple form. No change to `compute_viewbox`, to any primitive, or to `_emit_frame_svg`'s signature/paint logic.

**Goldens (`tests/golden/examples/corpus/`, 105 byte-for-byte pairs, harness `tests/golden/examples/test_example_html.py`):** churn only where a **vertically-growing** primitive is stacked **above** another, or a caption is applied mid-timeline.
- Predicted to churn: **`test_reference_datastruct.html`** — Stack `push` B/C/D/E growing above a VariableWatch (downstream y shifts down; correct).
- Predicted NOT to churn (verify): `stack`, `queue`, `04_stack_shrink`, `bst_operations` (single grower / grower is the only or last shape); `convex_hull_andrew`, `test_reference_segtree` (grower is **last** — nothing below to shift; viewBox already covered by `compute_stable_viewbox`); `bfs`, `bfs_grid_editorial`, `queue` (Queue `enqueue` grows **width**, not height); `maxflow`, `dinic`, `union_find` (Graph `add_edge` adds no node → bbox unchanged).
- Caption (Finding A): **zero** corpus churn — no corpus `.tex` applies a mid-timeline `\apply{…}{label=…}` or `\relabel` (grep-confirmed).
- Adjacent gates to re-run (not expected to break; a caption pushed inside the now-correct viewBox can only reduce overflow): `tests/doc_coverage/check_render_sanity.py` (`_check_text_bounds`/`_check_viewbox`), `tests/golden/smart_label/` SHA fixtures, `tests/property/test_smart_label_determinism.py`.

**Spec updates (R-32):** `docs/spec/svg-emitter.md` §"Annotation envelope reservation (R-32)" (lines 150-167) — reserved offsets now derive from the **same replay** as the viewBox and reserve **structural growth and captions**, not annotations only; note the single-pass source and that real primitives are never mutated. `docs/spec/ruleset.md` §8.9 (referenced there) — update the enumerated reserved-offset inputs if it lists them. Reaffirm the 369e80f floor-before-measure invariant (unchanged).

**Risks:** (1) the `_NO_EXTENT`/deepcopy hazard — mitigated by the clone cache reset (E3); a regression test that clones a primitive with a populated annotation cache would pin it. (2) Determinism — preserved: same deepcopy order, same `inspect`/`_apply_param_list` dispatch, declaration-order stacking (R-32.6). (3) Any future test asserting exact downstream y for a grower-above scene will churn with the offsets — mitigated by adding the structural `r32X` case so the intended values are pinned. (4) Performance — strictly fewer bbox calls, one deepcopy; no regression. (5) `_expand_selectors` must be mirrored in the replay for `top`/`all`/`range` targets or per-part relabels on those selectors would be missed (low frequency, but include it).

### Step-by-step landing order

1. **RED.** Add `tests/unit/test_scene_layout_caption_reserve.py` and `tests/unit/test_scene_layout_growth_reserve.py` (with the shared `assert_no_primitive_overlap` helper) plus the `r32X` structural case. Confirm they fail on HEAD with the documented numbers (caption painted 151 > viewBox 148; array y=84 overlapping the grown stack).
2. **GREEN — implement.** Add `measure_scene_layout` to `_frame_renderer.py` (deepcopy + `_ctx` detach/restore + `_extent_above_cache=None` reset; per-frame `set_annotations` + `apply_command` + caption/label, over `_expand_selectors`; capture global-max viewBox and per-primitive-max bbox; build reserved from the per-primitive max).
3. **Rewire.** `compute_stable_viewbox` → `return measure_scene_layout(...)[0]`; `_build_reserved_offsets` → `return measure_scene_layout(...)[1]` (or inline).
4. **Convert the 4 call sites** in `_html_stitcher.py` to `viewbox, reserved_offsets = measure_scene_layout(frames, primitives)`, keeping `_apply_min_arrow_above` immediately before. Leave `emit_diagram_html` on the wrapper.
5. **Verify.** New tests pass; `test_scene_layout_floor_order.py` and `test_r32_annotation_stable_layout.py` stay green; `compute_viewbox` + primitive-bbox unit tests unaffected. Run `impact({target:"measure_scene_layout"/"compute_stable_viewbox"/"_build_reserved_offsets", direction:"upstream"})` and `detect_changes()` per project CLAUDE.md before committing.
6. **Regenerate goldens** for the predicted-churn set (start with `test_reference_datastruct`), human-review the diff is only a downstream y-shift / caption reservation, commit goldens separately.
7. **Update spec** (`svg-emitter.md` R-32 §, `ruleset.md` §8.9) and note the sweep closure in this case file.
