# Annotation Reflow Flash — Mechanics Archaeology
**Date:** 2026-04-23  
**Bug:** Between step 1 and step 2 of `examples/algorithms/dp/convex_hull_trick.html`,
the `\annotate{dp.cell[1]}` arrow + label pops in with no fade, the `dp` array grows
vertically to accommodate it, and the `h` array jumps downward.

---

## 1. Pipeline stages table

| Stage | File : line | Input → Output | Key decisions |
|---|---|---|---|
| **Parse** | `parser/_grammar_commands.py:208-256` | TeX source → `AnnotateCommand` (frozen dataclass) | Selector parsed; `arrow_from`, `label`, `color`, `ephemeral`, `position` extracted |
| **Scene state machine** | `scene.py:646-682` (`_apply_annotate`) | `AnnotateCommand` → `AnnotationEntry` appended to `SceneState.annotations` | Persistent vs ephemeral flag; shape existence guard; 500-annotation cap |
| **Snapshot** | `scene.py:239-260` | `SceneState` → `FrameSnapshot` (frozen) | `annotations: tuple[AnnotationEntry, ...]` carried verbatim into snapshot |
| **FrameData conversion** | `renderer.py:253-264` (`_snapshot_to_frame_data`) | `FrameSnapshot` → `FrameData` | `AnnotationEntry` → plain `dict` with keys `target`, `label`, `arrow_from`, `color`, `position`, `ephemeral` |
| **Viewbox pre-scan** | `_html_stitcher.py:136-149` (`emit_interactive_html`) | All `FrameData.annotations` → max viewbox string | `compute_viewbox()` called once per frame; outer SVG viewbox = per-frame max — **stable across all frames** |
| **min_arrow_above pre-scan** | `_html_stitcher.py:384-403` | All annotations per primitive → `prim._min_arrow_above` | Guarantees each primitive's `translate` offset (arrow headroom) is the **same in every frame** — the explicit fix for the jump bug |
| **Per-frame SVG emit** | `_frame_renderer.py:463-540` (`_emit_frame_svg`) | `FrameData` + primitives → `<svg>` string | `set_annotations()` → `bounding_box()` → `translate(x, y_cursor)` → `emit_svg()` |
| **Differ** | `differ.py:246-300` (`_diff_annotations`) | `prev.annotations` vs `curr.annotations` → `TransitionManifest` | New annotation ⇒ `annotation_add` transition kind |
| **HTML stitcher** | `_html_stitcher.py:429-546` | Frame SVGs + manifests → `<div class="scriba-widget">` + `<script>` | JSON frame array; transition manifest per frame pair |
| **JS runtime** | `_script_builder.py:209-280` (`animateTransition`, `annotation_add` branch) | DOM + transition manifest → animated DOM mutations | Path stroke-draw animation; arrowhead/label fade-in; **phase 1 executes before phase 2** |

---

## 2. Annotation lifecycle

### 2a. Parse → AnnotateCommand

`_grammar_commands.py:208-256` (`_parse_annotate`):

```
\annotate{dp.cell[1]}{label="$+h[1]^2$", arrow_from="dp.cell[0]", color=info}
```

1. `tok = self._advance()` — consumes `\annotate` token.
2. `target_str = self._read_brace_arg(tok)` → `"dp.cell[1]"`.
3. `params = self._read_param_brace()` → `{label: "$+h[1]^2$", arrow_from: "dp.cell[0]", color: "info"}`.
4. `sel = parse_selector(target_str)` → `Selector(shape_name="dp", accessor=CellAccessor(indices=(1,)))`.
5. `arrow_from` string parsed into a second `Selector`.
6. Returns `AnnotateCommand(line, col, sel, label="$+h[1]^2$", position="above", color="info", arrow=False, ephemeral=False, arrow_from=<Selector dp.cell[0]>)`.

### 2b. AnnotateCommand → AnnotationEntry

`scene.py:646-682` (`_apply_annotate`):

```python
# scene.py:671-682
self.annotations.append(
    AnnotationEntry(
        target=target_str,          # "dp.cell[1]"
        text=cmd.label or "",       # "$+h[1]^2$"
        ephemeral=cmd.ephemeral,    # False  → persists into all future frames
        arrow_from=arrow_from_str,  # "dp.cell[0]"
        color=cmd.color or "info",
        position=cmd.position or "above",
        arrow=cmd.arrow,
    )
)
```

`ephemeral=False` means the entry **carries forward** from the `SceneState.annotations` list into every subsequent `FrameSnapshot` until explicitly cleared by a matching annotation removal. No ephemeral clearing happens at step boundaries unless `ephemeral=true` is set.

### 2c. AnnotationEntry → FrameSnapshot → FrameData

`scene.py:253-260` — the snapshot just copies `tuple(self.annotations)`.

`renderer.py:253-264` — each `AnnotationEntry` becomes a plain dict:
```python
{
    "target": "dp.cell[1]",
    "label": "$+h[1]^2$",
    "ephemeral": False,
    "arrow_from": "dp.cell[0]",
    "color": "info",
    "position": "above",
}
```

### 2d. FrameData.annotations → `_emit_frame_svg`

`_frame_renderer.py:463-472`:

```python
prim_anns = [
    a
    for a in frame.annotations
    if a.get("target", "").startswith(shape_name + ".")
]
if hasattr(prim, "set_annotations"):
    prim.set_annotations(prim_anns)   # base.py:304-306
```

This stores the list into `prim._annotations`. Immediately after:

```python
bbox = prim.bounding_box()   # _frame_renderer.py:474
```

`bounding_box()` reads `self._annotations` to compute arrow headroom.

### 2e. set_annotations + bounding_box → translate group

```python
svg_parts.append(f'<g transform="translate({x_offset},{y_cursor})">')  # _frame_renderer.py:479
# ...
y_cursor += bh + _PRIMITIVE_GAP                                         # _frame_renderer.py:540
```

`y_cursor` accumulates, so the `dp` height (with annotation headroom) directly controls the `translate` Y of every primitive that follows (`h`, etc.).

### 2f. emit_svg → arrow SVG

`array.py:199-353` (`emit_svg`):

1. `arrow_height_above(effective_anns, ...)` → `arrow_above` pixels.
2. If `arrow_above > 0`: emits `<g transform="translate(0, {arrow_above})">` — shifts cells down inside the primitive.
3. `emit_annotation_arrows(...)` called if `effective_anns` is non-empty. This invokes `emit_arrow_svg` in `_svg_helpers.py` which produces the Bezier `<path>`, arrowhead `<polygon>`, and label `<text>` elements, grouped under `<g data-annotation="...">`.

---

## 3. Per-primitive `set_annotations` + `bounding_box` behavior

All primitives use `PrimitiveBase.set_annotations` (`base.py:304-306`), which is a plain assignment: `self._annotations = annotations`. There is no per-class override.

### Array (`array.py`)

`bounding_box()` at `array.py:355-399`:

```python
computed = arrow_height_above(
    effective_anns, self.resolve_annotation_point, cell_height=CELL_HEIGHT
)
pos_above = position_label_height_above(effective_anns, cell_height=CELL_HEIGHT)
arrow_above = max(computed, pos_above, getattr(self, "_min_arrow_above", 0))
h += arrow_above
```

- Base height: `CELL_HEIGHT` (46 px) + optional index-label/caption stack below.
- With a single `arrow_from` annotation: `arrow_above` is typically 40–80 px (Manhattan-distance formula in `_svg_helpers.py:2625-2651`).
- Math labels (contains `$...$`) add 32 px headroom instead of the default 24 px (`_svg_helpers.py:2655-2658`). `"$+h[1]^2$"` triggers this path.

### DPTable (`dptable.py`)

`bounding_box()` at `dptable.py:313-353`:

```python
computed = arrow_height_above(
    self._annotations, self.resolve_annotation_point, cell_height=CELL_HEIGHT
)
pos_above = position_label_height_above(self._annotations, cell_height=CELL_HEIGHT)
arrow_above = max(computed, pos_above, getattr(self, "_min_arrow_above", 0))
h += arrow_above
```

Behavior identical to Array. The `dp` shape in the TeX IS a DPTable (or Array — both follow this pattern).

### Queue (`queue.py`)

Has `_arrow_height_above(self, annotations)` method at `queue.py:245-252`, used by both `bounding_box()` and the `min_arrow_above` pre-scan. Pattern is the same.

### Tree / Graph / Plane2D

`tree.py:549-556`, `graph.py:1056-1063`: same `arrow_height_above(self._annotations, ...)` call in `bounding_box()`. Plane2D (`plane2d.py`) overrides `bounding_box()` more substantially but follows the same annotation-headroom pattern.

**Key quantity:** for the `dp.cell[1]`→`dp.cell[0]` arc with math label `"$+h[1]^2$"`:

- `h_dist` ≈ `CELL_WIDTH + CELL_GAP` ≈ 48 px (adjacent cells, Manhattan).
- `arrow_above` ≈ `max(CELL_HEIGHT * 0.6, sqrt(48) * scale)` + 32 px math headroom ≈ 27.6 + 32 = **~60 px total**.

Without annotations, `dp` height = `CELL_HEIGHT` = 46 px.  
With annotation, `dp` height = 46 + 60 = **~106 px** — a 60 px increase.

---

## 4. Frame switcher / playback internals

### How the JS runtime switches frames

`_script_builder.py:108-116` (`snapToFrame`):

```javascript
function snapToFrame(i) {
    _cancelAnims();
    cur = i;
    stage.innerHTML = frames[i].svg;   // raw innerHTML replace — NO CSS transition
    narr.innerHTML  = frames[i].narration;
    // ...
    _updateControls(i);
}
```

`stage.innerHTML` replace is a **synchronous, instant DOM swap** — the old SVG is destroyed and the new one inserted in one microtask. No CSS `transition` is applied to the stage `<div>` or the `<svg>` element itself. The only CSS transitions are on `[data-target] > rect/circle/line/text` elements (180 ms ease-out, `scriba-scene-primitives.css:759-768`), but those are inert during a full innerHTML replacement.

### Animated transition path

`_script_builder.py:282-325` (`animateTransition`):

```javascript
function animateTransition(toIdx) {
    // phase1: annotation_add, highlight_on
    // phase2: everything else
    for (var i=0; i<phase1.length; i++) _applyTransition(phase1[i], parsed, pending);
    if (phase1.length>0 && phase2.length>0) {
        setTimeout(_runPhase2, _dur(DUR_STAGGER));  // 50 ms gap
    } else { _runPhase2(); }
}
```

For `annotation_add` (`_script_builder.py:209-280`):

1. The `<g data-annotation="...">` node is cloned from the parsed target SVG.
2. If the annotation group contains a `<path>` element: **stroke-draw animation** via `strokeDasharray`/`strokeDashoffset` (`DUR_PATH_DRAW = 120 ms`). Arrowhead polygon and label text start at `opacity=0` and fade in at 70% draw progress.
3. If no `<path>` (pure position-label): standard `animate([{opacity:0},{opacity:1}])` at `DUR = 180 ms`.

`animateTransition` is only called when navigating **forward by one step** and `_canAnim` is true (`_script_builder.py:326-332`). Backward navigation always uses `snapToFrame`.

### `_canAnim` guard

```javascript
var _canAnim = (typeof Element.prototype.animate === 'function') && !_motionMQ.matches;
```

When `prefers-reduced-motion: reduce` is set, `_canAnim = false` and all transitions fall through to `snapToFrame` (instant swap). CSS also zeroes all `transition-duration` values (`scriba-scene-primitives.css:774-801`).

### Full-sync flag (`fs`)

When `_needs_sync[i]` is true (SVG content differs between frames), after all WAAPI animations complete the runtime calls `_finish(true)` which does `stage.innerHTML = frames[toIdx].svg` — a final sync to canonical state. This means even animated transitions end with a full DOM swap.

---

## 5. Obstacle resolution coupling

`_frame_renderer.py:442-461` — the pre-scan loop that computes `_prim_offsets` and `scene_segments` calls `prim.bounding_box()` **before** `set_annotations()` is called on that primitive in the main emit loop:

```python
# Pre-scan (lines 442-461): bounding_box() called WITHOUT annotations set
for _sn, _prim in primitives.items():
    _bbox = _prim.bounding_box()     # uses whatever _annotations are currently on prim
    ...
    _prim_offsets[_sn] = (float(_x_off), float(_pre_y))
    _pre_y += _bh + _PRIMITIVE_GAP

# Build scene_segments from resolve_obstacle_segments()
for _sn, _prim in primitives.items():
    ...
    for _seg in _seg_fn():           # called before set_annotations for that prim
        _scene_seg_list.append(...)

# Main emit loop (lines 463-540): THEN set_annotations() is called
for shape_name, prim in primitives.items():
    prim.set_annotations(prim_anns)  # NOW annotations are set
    bbox = prim.bounding_box()       # re-computed WITH annotations
```

**Consequence:** `_prim_offsets` (used for cross-primitive pill avoidance) are computed from bbox values that may not reflect the final annotation state for that frame. For primitives whose `resolve_obstacle_segments()` returns non-empty lists (currently Array, DPTable, Queue all return `[]` stubs — see `array.py:426-428`, `dptable.py:506-508`), this discrepancy is harmless today. But moving annotations to a scene-level layer would break this pre-scan: obstacle offsets would be computed without annotation headroom, and cross-primitive pill placement could collide with arrow curves.

`resolve_obstacle_segments` callers: only `_frame_renderer.py:457-460`. No other caller exists in the codebase.

---

## 6. Viewbox / canvas sizing

### The stable-viewbox mechanism

`_html_stitcher.py:136-149` and `_html_stitcher.py:368-380` (same logic in both `emit_animation_html` and `emit_interactive_html`):

```python
for f in frames:
    vb_str = compute_viewbox(primitives, annotations=f.annotations)
    max_vb_width  = max(max_vb_width,  int(parts[2]))
    max_vb_height = max(max_vb_height, int(parts[3]))
base_vb = compute_viewbox(primitives)          # baseline without annotations
max_vb_width  = max(max_vb_width,  int(base_parts[2]))
max_vb_height = max(max_vb_height, int(base_parts[3]))
viewbox = f"0 0 {max_vb_width} {max_vb_height}"
```

This single `viewbox` string is passed to every `_emit_frame_svg` call. The outer `<svg viewBox="...">` therefore **never changes** between frames — the stage container stays the same pixel dimensions.

`compute_viewbox` (`_frame_renderer.py:114-155`) calls `prim.set_annotations(prim_anns)` then `prim.bounding_box()` for each primitive for each frame, accumulating the max total height. The result includes `_PADDING = 16 px` on all sides and `_PRIMITIVE_GAP = 50 px` between primitives.

### What grows inside a stable viewbox

Within the fixed viewbox, each frame's `<g transform="translate(x, y_cursor)">` recalculates `y_cursor` from scratch using that frame's annotation-aware `bounding_box()` values. So while the outer SVG box is stable, the `translate` of primitives lower in the stack **can still change** between frames if an upper primitive's height changes.

The `_min_arrow_above` mechanism (`_html_stitcher.py:384-403`) is meant to prevent this: it pre-computes the maximum `arrow_height_above` across all frames for each primitive, and stores it as a floor. Then `bounding_box()` uses `max(computed, pos_above, _min_arrow_above)` — so even frames with zero annotations include the same headroom, keeping `y_cursor` values identical across all frames.

**The flash bug arises when `_min_arrow_above` is not being applied correctly.** The `_min_arrow_above` pre-scan at `_html_stitcher.py:384-403` calls `prim._arrow_height_above(prim_anns)` — but Array and DPTable do NOT define `_arrow_height_above` as an instance method (only Queue does at `queue.py:245`). The check at line 163 `if hasattr(prim, "_arrow_height_above")` therefore evaluates to **False** for Array and DPTable, so `max_ah` stays at 0 and `set_min_arrow_above(0)` is a no-op. The floor is never set, so those primitives' translate offsets jump when annotations first appear.

---

## 7. Summary diagram

```
TeX source
  │
  ▼  _grammar_commands.py:208-256
AnnotateCommand (frozen dataclass: target, label, arrow_from, color, position, ephemeral)
  │
  ▼  scene.py:646-682  _apply_annotate()
AnnotationEntry appended to SceneState.annotations  (persistent if ephemeral=False)
  │
  ▼  scene.py:239-260  snapshot()
FrameSnapshot.annotations: tuple[AnnotationEntry, ...]
  │
  ▼  renderer.py:253-264  _snapshot_to_frame_data()
FrameData.annotations: list[dict]   (plain dicts, emitter-facing)
  │
  ├──► _html_stitcher.py:136-149  max-viewbox pre-scan
  │      compute_viewbox(prim, annotations=f.annotations)
  │         → prim.set_annotations()  → prim.bounding_box()   (all frames)
  │      → stable outer SVG viewbox string (never changes per frame)
  │
  ├──► _html_stitcher.py:384-403  min_arrow_above pre-scan
  │      for each prim: max over frames of prim._arrow_height_above(anns)
  │      → prim.set_min_arrow_above(max_ah)   ← BROKEN for Array/DPTable
  │         (hasattr check fails; floor stays 0)
  │
  ▼  _html_stitcher.py:433  _emit_frame_svg(frame, primitives, viewbox, ...)
     │
     ├── pre-scan _prim_offsets  (_frame_renderer.py:442-461)
     │     prim.bounding_box() called WITHOUT per-frame annotations
     │
     └── main emit loop (_frame_renderer.py:463-540)
           prim.set_annotations(prim_anns)      ← annotations set HERE
           bbox = prim.bounding_box()            ← height includes arrow headroom
           y_cursor used for translate(x, y)     ← SHIFTS when height changes
           prim.emit_svg(...)
             → emit_annotation_arrows(...)
               → emit_arrow_svg()  →  <path> + <polygon> + <text>
                 in <g data-annotation="...">

  ▼  differ.py:246-300  _diff_annotations()
     annotation absent in frame N, present in frame N+1
     → Transition(kind="annotation_add", target="dp.cell[1]-dp.cell[0]")

  ▼  _html_stitcher.py:519-535  compute_transitions embedded in frame JSON
     frames[i].tr = [[target, prop, from, to, "annotation_add"], ...]

  ▼  _script_builder.py:282-325  animateTransition() in browser
     annotation_add → phase1 → stroke-draw animation on <path>
     BUT: parent <g transform="translate(...)"> for dp and h arrays
          has ALREADY JUMPED (y_cursor recomputed from annotation-aware
          bounding_box) — the translate snap is synchronous innerHTML,
          not animated.
```

---

## Landmines

**L1 — `_arrow_height_above` method guard fails for Array and DPTable.**
`_html_stitcher.py:163` checks `hasattr(prim, "_arrow_height_above")`. Array (`array.py`) and DPTable (`dptable.py`) call `arrow_height_above()` as a module-level function, not an instance method. So the `hasattr` test returns `False`, `max_ah` stays 0, and `set_min_arrow_above(0)` is called — which is a no-op since 0 is the default. The `_min_arrow_above` floor intended to stabilize the translate offset is silently never set for the two most common annotation targets. This is the **root cause** of the vertical jump.

**L2 — Pre-scan `_prim_offsets` uses stale bbox.**
In `_emit_frame_svg`, `_prim_offsets` (used for cross-primitive obstacle avoidance) are computed from `bounding_box()` called without per-frame annotations set (`_frame_renderer.py:444-449`). Then the main emit loop sets annotations and re-calls `bounding_box()` at line 474. The two calls can return different heights for the same primitive. If `resolve_obstacle_segments()` ever returns real data for annotation-affected primitives, pill placements will be offset by the annotation headroom delta.

**L3 — `compute_viewbox` leaves annotations dirty on primitives.**
`compute_viewbox` (`_frame_renderer.py:133-155`) calls `prim.set_annotations(prim_anns)` but never resets annotations to `[]` when it finishes iterating. If called outside the pre-scan context where `set_annotations([])` is explicitly called afterward (`_html_stitcher.py:169-170`), the primitive carries the last-frame annotations into the first call of `_emit_frame_svg`. This is currently safe only because the emit loop immediately calls `set_annotations` again.

**L4 — Transition target key is a synthetic composite string.**
`differ.py:263` constructs `composite = f"{key[0]}-{key[1]}"` (e.g. `"dp.cell[1]-dp.cell[0]"`). The JS runtime uses this as `[data-annotation="..."]`. If target or `arrow_from` contain a hyphen the composite becomes ambiguous and the `querySelector` could fail silently, leaving the annotation un-animated.

**L5 — Obstacle pre-scan runs before `set_annotations` in the emit loop.**
This is documented in §5 above but bears repeating: the two passes inside `_emit_frame_svg` use different annotation states for the same frame. If a future primitive returns obstacle segments that depend on annotation-inflated dimensions, the scene-level obstacle set will be wrong for that frame.

**L6 — Full innerHTML sync (`fs:1`) fires after every animated transition.**
`_html_stitcher.py:534` sets `_needs_sync = True` whenever `svg_html` differs between frames — which is almost always (any state change changes the SVG). This means the WAAPI stroke-draw animation for the annotation arrow is immediately followed by a full `stage.innerHTML` swap, potentially causing a visual flicker if the browser hasn't composited the WAAPI frame yet before the swap.
