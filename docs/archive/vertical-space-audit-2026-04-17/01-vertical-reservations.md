# Report 1 — Vertical-Space Reservation Per Primitive

## `arrow_height_above()` in `base.py` — Edge Case Analysis

`base.py:1050–1054`: returns `0` immediately if `annotations` is empty or if no annotation has `arrow_from`. **No false positive from empty annotations.** However:

- `base.py:1060–1061`: if `src` or `dst` is `None` (unresolvable selector), arrow is silently skipped → contributes `0`. Correct.
- `base.py:1094-1095`: `_LABEL_HEADROOM = 24` is unconditionally added to `max_height` even when no arrow has a label. Inflates reservation.

### Critical: `_min_arrow_above`

`emitter.py:690–709` iterates all frames and sets `prim.set_min_arrow_above(max_ah)` (cross-frame max). After the loop it calls `prim.set_annotations([])`.

Result: in any frame, `_min_arrow_above` is the cross-frame max. `bounding_box()` is then called without current annotations but with `_min_arrow_above > 0`, **permanently adding space even when the current frame has no arrows**.

## Per-Primitive Table

| Primitive | `bounding_box()` top space | `emit_svg()` y-shift guard | Label/caption guard | Verdict |
|---|---|---|---|---|
| **array** | `arrow_above = _arrow_height_above(effective_anns)` then `h += arrow_above` (`array.py:364–365`) | `if arrow_above > 0` (`array.py:184`) | `if self.labels is not None` / `if self.label is not None` (`array.py:342–356`) | CORRECT |
| **base** | Abstract — delegates | — | — | N/A |
| **codepanel** | No arrow space | No arrow shift | `if self.label_text: height += 20` (`codepanel.py:124`) | CORRECT |
| **dptable** | `arrow_above = self._arrow_height_above(self._annotations)` → `max(computed, _min_arrow_above)` (`dptable.py:320–321, 507-512`) | `if arrow_above > 0` (`dptable.py:217`) | `elif self.label: h += INDEX_LABEL_OFFSET` (`dptable.py:317–318`) | **WASTEFUL** — Bug A source |
| **graph** | `arrow_above = self._arrow_height_above()` always added (`graph.py:612–617`) | Always: `ty = r + arrow_above` no guard (`graph.py:635,638`) | `if self.label is not None` (`graph.py:642`) | CORRECT — `arrow_above=0` when no arrows |
| **grid** | `arrow_above = arrow_height_above(...)` then `h += arrow_above` (`grid.py:315–320`) | `if arrow_above > 0` (`grid.py:207`) | Conditional | CORRECT structurally; jitters because no `_min_arrow_above` |
| **hashmap** | `arrow_above = arrow_height_above(...)` (`hashmap.py:213–218`) | `if arrow_above > 0` (`hashmap.py:243`) | `if self.label_text:` (`hashmap.py:210`) | CORRECT |
| **layout** | Delegates to children | — | — | CORRECT |
| **linkedlist** | `arrow_above = arrow_height_above(...)` (`linkedlist.py:221–225`) | `if arrow_above > 0` (`linkedlist.py:250`) | `if self.label_text:` (`linkedlist.py:219`) | CORRECT |
| **matrix** | No arrow space. `if self.label: h += 20` (`matrix.py:401–402`) | No arrow shift | `if self.label:` | CORRECT |
| **metricplot** | Fixed `width/height` (`metricplot.py:742`) | No arrow shift | — | CORRECT |
| **numberline** | `h += 16` only `if self.label` (`numberline.py:323–324`); `arrow_above` conditional (`numberline.py:327–332`) | `if arrow_above > 0` (`numberline.py:209`) | `if self.label:` | CORRECT structurally; jitters (no `_min_arrow_above`) |
| **plane2d** | `arrow_above = self._arrow_height_above()` always added (`plane2d.py:599–604`) | `if arrow_above > 0` (`plane2d.py:621`) | — | CORRECT |
| **queue** | `arrow_above = arrow_height_above(...)` (`queue.py:233–237`) | `if arrow_above > 0` (`queue.py:257`) | `if self.label_text:` (`queue.py:231`) | CORRECT structurally; jitters (no `_min_arrow_above`) |
| **stack** | No arrow space. `if self.label_text: h += 20` (`stack.py:197–198`) | No arrow shift | `if self.label_text:` | CORRECT |
| **tree** | `label_h = _LABEL_HEIGHT if self.label is not None else 0` (`tree.py:736`); `arrow_above` always added (`tree.py:735,741`) | Always: `ty = r + arrow_above` (`tree.py:759`) | `if self.label is not None:` (`tree.py:767`) | CORRECT — `arrow_above=0` when no arrows |
| **variablewatch** | `arrow_above` conditional (`variablewatch.py:203–208`) | `if arrow_above > 0` (`variablewatch.py:226`) | `if self.label_text:` (`variablewatch.py:200`) | CORRECT |

## DPTable Root Cause (tutorial_en.html top gap)

`emitter.py:690–709` computes `max_ah` over all frames (including frames that have arrows), then calls `prim.set_min_arrow_above(max_ah)`. In `dptable.py:507–512`:

```python
def _arrow_height_above(self, annotations):
    computed = arrow_height_above(annotations, self._cell_center, ...)
    return max(computed, getattr(self, "_min_arrow_above", 0))
```

`bounding_box()` at `dptable.py:320` calls `self._arrow_height_above(self._annotations)`. After `emitter.py:709` resets annotations to `[]`, `computed=0` but `_min_arrow_above` remains the cross-frame max. The `bounding_box()` used for the viewbox includes that height — pushing the SVG viewbox top down for all frames, even those without arrows. For step 1 of tutorial_en.html: 73 px blank above the table.

## Concrete Fix Proposals

1. **Decouple sizing from positioning**: make `bounding_box()` use `computed` only (per-frame), not `max(computed, _min_arrow_above)`. Keep `_min_arrow_above` only for stable `translate()` in `emit_svg`.

2. **Conditional `_LABEL_HEADROOM`** (`base.py:1094-1095`):
   ```python
   if any(a.get("label") for a in arrow_anns):
       max_height += _LABEL_HEADROOM
   ```

3. **Move `set_min_arrow_above`** in `emitter.py:707–709` to after viewbox computation, so `bounding_box()` during sizing is called only with per-frame annotations.
