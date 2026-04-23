# 03 — Plane2D + misc primitives param audit

**Date:** 2026-04-23
**Scope:** Plane2D, NumberLine, MetricPlot, Queue, Stack, LinkedList, VariableWatch, CodePanel
**Cross-check:** `docs/spec/primitives.md` §8–§10, `docs/SCRIBA-TEX-REFERENCE.md` §7

## Plane2D

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `xrange` | WORKS | `plane2d.py:152` | Keep |
| `yrange` | WORKS | `plane2d.py:153` | Keep |
| `grid` | WORKS | `plane2d.py:161` — `True`/`False`/`"fine"` | Keep |
| `axes` | WORKS | `plane2d.py:162` | Keep |
| `aspect` | WORKS | `plane2d.py:163-165` | Keep |
| `width` | WORKS | `plane2d.py:168` | Keep |
| `height` | WORKS | `plane2d.py:172-178` — silently clamped when `aspect=equal` | Document clamp |
| `points` | WORKS | `plane2d.py:191` → `_add_point_internal` | Keep |
| `lines` | WORKS | `plane2d.py:193` | Keep |
| `segments` | WORKS | `plane2d.py:195` | Keep |
| `polygons` | WORKS | `plane2d.py:197` | Keep |
| `regions` | WORKS | `plane2d.py:199` | Keep |
| `show_coords` | WORKS | `plane2d.py:202,987` | Keep |
| `xlabel` | LIES | `plane2d.py:122-126` — comment explicitly says "no rendered effect — tracked as v0.6.2 follow-up". Never read after assignment. | **Kill** or implement |
| `ylabel` | LIES | Same. | **Kill** or implement |
| `label` | LIES | Same comment block — accepted but never read; `base.py:213` sets default `None` and Plane2D never overwrites. | **Kill** or wire `self.label = params.get("label")` + render |

**Apply-only ops (correct by design):** `add_point`, `add_line`, `add_segment`, `add_polygon`, `add_region`, `remove_*` — all documented in SCRIBA-TEX-REFERENCE.md §7.9 with matching `apply_command` branches.

## NumberLine

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `domain` | WORKS | `numberline.py:89-103` | Keep |
| `ticks` | WORKS | `numberline.py:108-132` | Keep |
| `labels` | WORKS | `numberline.py:134` | Keep |
| `label` | WORKS | `numberline.py:137,284` | Keep |

Clean.

## MetricPlot

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `series` | WORKS | `metricplot.py:142` | Keep |
| `xlabel` | WORKS | `metricplot.py:196,545` | Keep |
| `ylabel` | WORKS | `metricplot.py:197,554` | Keep |
| `ylabel_right` | WORKS | `metricplot.py:198,563` — `two_axis=True` only | Document |
| `grid` | WORKS | `metricplot.py:199,394` | Keep |
| `width` | WORKS | `metricplot.py:200` | Keep |
| `height` | WORKS | `metricplot.py:201` | Keep |
| `show_legend` | WORKS | `metricplot.py:202,417` | Keep |
| `show_current_marker` | WORKS | `metricplot.py:203,411` | Document |
| `xrange` | WORKS | `metricplot.py:206,297` | Keep |
| `yrange` | WORKS | `metricplot.py:216,304` | Keep |
| `yrange_right` | WORKS | `metricplot.py:217,305` | Document |

**Undocumented but working:** `show_current_marker`, `yrange_right`, `ylabel_right`. Reference shows only `series`, `xlabel`, `ylabel`.

## Queue

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `capacity` | WORKS | `queue.py:119` | Keep |
| `data` | WORKS | `queue.py:134-141` | Keep |
| `label` | WORKS | `queue.py:128,390` | Keep |

Queue is always horizontal — no `orientation` param. Stack has one; Queue does not. Intentional asymmetry, undocumented.

## Stack

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `items` | WORKS | `stack.py:109` | Keep |
| `orientation` | WORKS | `stack.py:96,267/272` | Document |
| `max_visible` | WORKS | `stack.py:97,190` | Document |
| `label` | WORKS | `stack.py:106,321` | Keep |

**STRUCTURAL BUG:** Stack has no `ACCEPTED_PARAMS` frozenset. `base.py:211` skips validation when empty. Stack silently accepts unknown params — the only primitive among the eight that skips E1114. Fix: add `ACCEPTED_PARAMS = frozenset({"items","orientation","max_visible","label"})`.

**Undocumented:** `orientation`, `max_visible` not in SCRIBA-TEX-REFERENCE.md §7.8.

## LinkedList

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `data` | WORKS | `linkedlist.py:104` — also handles stringified JSON | Keep |
| `label` | WORKS | `linkedlist.py:116,444` | Keep |

Clean.

## VariableWatch

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `names` | WORKS | `variablewatch.py:83` — also comma-separated string | Keep |
| `label` | WORKS | `variablewatch.py:94,354` | Keep |

Clean.

## CodePanel

| Param | Category | Evidence (file:line) | Recommendation |
|---|---|---|---|
| `source` | WORKS | `codepanel.py:87` | Keep |
| `lines` | WORKS | `codepanel.py:90` — takes priority over `source` | Keep |
| `label` | WORKS | `codepanel.py:106,278` | Keep |

Clean.

## Cross-primitive summary

**LIES (3):**
- `Plane2D.xlabel` — accepted, never rendered (code comment admits).
- `Plane2D.ylabel` — same.
- `Plane2D.label` — accepted in `ACCEPTED_PARAMS`, never assigned to `self.label`.

**VESTIGIAL (0):** None.

**UNDOCUMENTED but working (5):**
- `MetricPlot.show_current_marker`
- `MetricPlot.yrange_right`
- `MetricPlot.ylabel_right`
- `Stack.orientation`
- `Stack.max_visible`

**STRUCTURAL BUG:** Stack missing `ACCEPTED_PARAMS` frozenset → no E1114 guard.

**Design asymmetry:** Queue fixed-horizontal, Stack has `orientation`. Not documented.
