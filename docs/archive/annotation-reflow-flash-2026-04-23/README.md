# Annotation-Induced Reflow Flash — Research Archive

**Date**: 2026-04-23
**Trigger**: `examples/algorithms/dp/convex_hull_trick.html` step 1 → step 2 flash/jump.
**Root symptom**: annotation spawn → dp primitive bbox grows → scene re-stacks → h array box pushes down abruptly (no transition). Plus annotation arrow + label pop-in abrupt.

## Confirmed mechanism

`scriba/animation/_frame_renderer.py:442-479` — per-frame vertical re-stacking. Every frame:

1. Pre-scan: for each shape `prim.set_annotations(...)` then `prim.bounding_box()` → accumulate `y_cursor += bh + GAP`.
2. Emit: `<g transform="translate(x_off, y_cursor)">`.

When `\annotate` added at step N, target prim's bbox grows → every prim below shifts down. Frame switcher swaps transforms with no CSS transition → instant snap.

Three layered flash effects:
- (a) annotation element pop-in (no opacity fade)
- (b) target primitive grows vertically
- (c) downstream primitives translate down

## Research agents (6 parallel + 1 synthesis)

| # | File | Topic |
|---|------|-------|
| 1 | `01-mechanics-archaeology.md` | Full trace parser → scene → frame_renderer → SVG → HTML playback |
| 2 | `02-cross-primitive-survey.md` | Catalog affected examples + Δ-transform diff across frames |
| 3 | `03-prior-art.md` | Manim, Motion Canvas, d3/observable, Excalidraw, Mermaid, Reveal |
| 4 | `04-approach-a-reserve-gutter.md` | Pre-scan all frames, freeze max envelope |
| 5 | `05-approach-b-group-transition.md` | CSS/SMIL transition on `<g transform>` |
| 6 | `06-approach-c-scene-level-layer.md` | Refactor: annotations outside prim bbox |
| 7 | `07-synthesis.md` | Decision + phase plan |

## Rules / constraints to preserve

- Determinism (replay byte-identical; same seed → same SVG).
- Reduced-motion accessibility contract.
- No regression on existing goldens without explicit sign-off.
- Obstacle resolution may depend on annotation bbox (see `resolve_obstacle_segments`).
- U-05 dataset-preserving analog: annotation presence/position must not change primitive intrinsic data.
