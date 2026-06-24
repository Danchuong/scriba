# Investigation: Scriba Animation — Unbounded Render Height When Embedded

## Hand-off Brief

1. **What happened.** Confirmed: the interactive-widget SVG is emitted with a `viewBox` but **no `width`/`height`** (`scriba/animation/_frame_renderer.py:497-502`); combined with `.scriba-stage-svg { width:100%; height:auto }` (`scriba/animation/static/scriba-embed.css:110-113`), a `viewBox`-only SVG is force-**upscaled** to the container width, so a small 240×452 scene renders ~2.9× too tall in any non-fixed-size column.
2. **Where the case stands.** Root cause is Confirmed (deterministic, derivable from constants). All four external claims independently verified in this repo's source; no contradicting evidence found.
3. **What's needed next.** Implement **Fix A** (intrinsic SVG size via `style="max-width:{vb_width}px"`) + **Fix C** (CSS `max-height` guard) as a patch — hand to `bmad-quick-dev`.

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | N/A (external bug report) |
| Date opened      | 2026-06-24 |
| Status           | Concluded |
| System           | scriba repo (main @ 1bf7a17); `scriba/animation/*` |
| Evidence sources | Source code, external bug report (hypothesis) |

## Problem Statement

External report: animations embedded outside the playground render massively oversized (small 3-primitive scene upscaled ~3×, taller than viewport). Claims to verify: (1) SVG carries only `viewBox`, no `width`/`height`; (2) CSS `width:100%; height:auto` causes upscaling; (3) parsed `width`/`height` `AnimationOptions` are ignored by renderer; (4) no height cap anywhere. The report is treated as a hypothesis until independently confirmed.

## Confirmed Findings

### Finding 1: SVG emitted with viewBox only — no width/height

**Evidence:** `scriba/animation/_frame_renderer.py:497-502`
```python
svg_parts: list[str] = [
    f'<svg class="scriba-stage-svg" viewBox="{viewbox}" '
    f'role="img" '
    f'aria-labelledby="{_escape_fn(narration_id)}" '
    f'xmlns="http://www.w3.org/2000/svg">'
```
No `width=`/`height=` attribute is present. `vb_width` is computed at `_frame_renderer.py:512` (`int(vb_parts[2])`), so the natural width is already in scope at emit time. **Claim 1 confirmed.**

### Finding 2: CSS forces the viewBox-only SVG to full container width

**Evidence:** `scriba/animation/static/scriba-embed.css:110-113`
```css
.scriba-stage-svg { width: 100%; height: auto; }
```
A `viewBox`-only SVG has no intrinsic pixel size, so `width:100%` resolves to the container width and `height:auto` derives height from the aspect ratio. This **upscales** (never shrinks) the drawing. **Claim 2 confirmed.**

### Finding 3: Parsed width/height options are never threaded to the emitter

**Evidence:**
- `scriba/animation/parser/ast.py:295-296` — `AnimationOptions.width: str | None` and `.height: str | None` exist.
- `scriba/animation/constants.py:45-47` — `VALID_OPTION_KEYS` includes `"width"`, `"height"` (so they are parsed/validated).
- `scriba/animation/renderer.py:476-478` — only `ir.options.id` is read; the `emit_html(...)` call (`renderer.py:503-510`) passes `scene_id, frames, primitives, mode, …` — **no width/height**.
- `scriba/animation/_html_stitcher.py:406-414` (`emit_interactive_html`) and `:688-697` (`emit_html`) — neither signature has a `width`/`height` parameter.

The options are accepted by the parser and then dropped. Authors have **no escape hatch** to constrain size. **Claim 3 confirmed.**

### Finding 4: No height cap exists anywhere

**Evidence:** `grep -rniE 'max-height|aspect-ratio|object-fit|max-width' scriba/animation/static/` → **zero matches**. `.scriba-widget` (`scriba-embed.css:30-35`) sets `border/border-radius/background/overflow:hidden` — no `max-width`/`max-height`. `.scriba-stage` (`scriba-embed.css:104-108`) adds `padding:1.25rem 1rem` + `min-height:100px` (adds height, never bounds it). **Claim 4 confirmed.**

### Finding 5: viewBox derivation constants match the report exactly

**Evidence (all confirmed verbatim):**
- `_frame_renderer.py:27-28` — `_PADDING=16`, `_PRIMITIVE_GAP=50`
- `primitives/_types.py:129-132` — `CELL_WIDTH=60`, `CELL_HEIGHT=40`, `CELL_GAP=2`, `INDEX_LABEL_OFFSET=16`
- `primitives/array.py:51,52,59` — `_FONT_SIZE_INDEX=10`, `_FONT_SIZE_CAPTION=11`, `_STACK_GAP=9`
- `primitives/variablewatch.py:33-35` — `_MIN_NAME_COL_WIDTH=100`, `_MIN_VALUE_COL_WIDTH=100`, `_ROW_HEIGHT=40`
- `_frame_renderer.py:160-161` — `vb_width = max_width + 2*_PADDING`; `vb_height = total_height + 2*_PADDING` (vertical stack adds `_PRIMITIVE_GAP` between primitives, `_frame_renderer.py:147`).

These reproduce the report's `viewBox = "0 0 240 452"` for the repro scene. **Claim (§3 derivation) confirmed.**

## Deduced Conclusions

### Deduction 1: Rendered height is unbounded and proportional to container width

**Based on:** Findings 1, 2, 4.

**Reasoning:** A viewBox-only SVG under `width:100%; height:auto` renders at `rendered_height = container_width × (vb_H / vb_W)`. With `vb_W/vb_H = 240/452` (aspect ≈ 1.88) and no `max-height`/`max-width` anywhere, height grows linearly with column width with no upper bound.

**Conclusion:** At 700px column → ~1318px tall (≈2.9× upscale); at 480px → ~904px. Matches the reported symptom. This is **forced upscaling of a small narrow drawing**, not a font-size bug — every element magnifies by the same factor.

### Deduction 2: The playground "works" only by accident

**Based on:** Report §2 (playground renders in a fixed-size dockview panel with `overflow-auto`).

**Reasoning:** The fixed panel clips/scrolls, hiding the unbounded height. A plain document column has no such bound. The protection is host-side and accidental — not a Scriba-owned guarantee. (Confirmed in source for scriba; the playground/host file is outside this repo, graded Deduced.)

## Hypothesized Paths

### Hypothesis 1 (report's premise): "animation too big / oversized"

**Status:** Confirmed (refined).

**Resolution:** The premise is correct but the *mechanism* is upscaling of a viewBox-only SVG, not oversized intrinsic geometry. The 240px-wide drawing is intrinsically compact; the bug is the missing intrinsic size letting CSS blow it up. An earlier host-side "shrink the fonts" framing would have been wrong — refuted by Finding 5 (geometry is small).

## Source Code Trace

| Element       | Detail |
| ------------- | ------ |
| Error origin  | `scriba/animation/_frame_renderer.py:497-502` (SVG open tag, no width/height) |
| Trigger       | Any embed of `emit_interactive_html`/`emit_html` output in a container without a fixed width/overflow bound |
| Condition     | `.scriba-stage-svg { width:100%; height:auto }` upscales a viewBox-only SVG to container width |
| Related files | `static/scriba-embed.css:30-35,104-113`; `renderer.py:476-510`; `_html_stitcher.py:406,688`; `parser/ast.py:295-296`; `constants.py:45-47` |

## Conclusion

**Confidence:** High — root cause Confirmed in source, behavior deterministically derivable, all four external claims independently verified, no contradicting evidence.

**Root cause:** The widget SVG is emitted with `viewBox` but no intrinsic `width`/`height`. Under the package CSS `width:100%; height:auto`, the browser upscales the small (e.g. 240×452) drawing to the full container width, producing unbounded height (`width × vb_H/vb_W`). Compounded by: parsed `width`/`height` options being dropped (no author escape hatch) and zero `max-height`/`max-width`/`aspect-ratio` guards in the package.

## Recommended Next Steps

### Fix direction (ranked)

- **Fix A — give the SVG an intrinsic size (primary, low risk).** At `_frame_renderer.py:497`, add `style="max-width:{vb_width}px"` (or explicit `width`/`height`) to the `<svg>` open tag; `vb_width` already computed at `:512` (move the parse above the tag). `width:100%` can then only shrink, never upscale → repro renders at natural 240×452. Keep `.scriba-stage-svg` as-is. Add `max-width` to `.scriba-widget` (`scriba-embed.css:30-35`).
- **Fix C — CSS height guard (defensive, minimal).** `scriba-embed.css:110` add `max-height:80vh`; `:104` add `overflow:auto` to `.scriba-stage`. With an intrinsically-sized SVG, `max-height` shrinks proportionally (aspect preserved). Bounds even deep stacks.
- **Fix D — tighten vertical rhythm (cosmetic).** `_PRIMITIVE_GAP` 50→~24, `_PADDING` 16→12, optionally `_ROW_HEIGHT` 40→28. Removes dead space; does not bound height alone.
- **Fix B — honor parsed width/height (semantic, medium).** Thread `ir.options.width/height` through `emit_html`/`emit_interactive_html` onto `.scriba-widget` as `max-width`/`max-height; overflow:auto`. Additive, backward-compatible.

**Release plan:** A + C in a patch (bounds height, backward-compatible); D + B in next minor.

### Diagnostic / verification

Render any scene with ≥2 stacked primitives inside `<div style="width:700px">…</div>` (no dockview/overflow wrapper). Observe SVG height ≈ `700 × vb_H/vb_W`. Apply Fix A → confirm it renders at natural `vb_W × vb_H` regardless of container width. Add a unit assertion that the emitted `<svg>` carries an intrinsic-size attribute.

## Side Findings

- `.scriba-widget` has `overflow:hidden` (`scriba-embed.css:34`) but height is `auto`, so it never clips vertically — the clip is horizontal only. Confirms the widget does not self-bound height.
- `constants.py:46` also lists `"grid"` in `VALID_OPTION_KEYS` (not in `AnimationOptions` dataclass shown) — tangential; out of scope.
- Host-side stopgap already deployed (report §6): `.scriba-stage-svg { max-width: min(100%,300px) }` — width cap only; a 1.88-aspect scene is still ~565px tall. Real fix is package-side (A/C/D).
