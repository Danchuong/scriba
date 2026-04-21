# Smart-Label Audit — Post-Phase-0-Quick-Wins Output (Legacy Engine)

**Branch rendered from:** `main @ 74939c1 + Phase 0 Quick Wins (uncommitted: QW-1..QW-7 + position-only label drop fix)`  
**Engine:** `legacy engine (default on main)`  
**Rendered:** 2026-04-21  
**Compare against (legacy pre-patch):** `../repros/` — rendered from `main` @ `74939c1` (v0.9.1 + 3 patches, no Phase 0 patch)

> **Re-rendered with Phase 0 Quick Wins applied** (uncommitted patches to
> `scriba/animation/primitives/_svg_helpers.py` and `scriba/animation/primitives/base.py`,
> covering QW-1..QW-7 + position-only label drop fix).
> No `SCRIBA_LABEL_ENGINE` override — default `legacy` engine on main.
> No `measure_and_fix.js` / Wave C DOM-mutation post-processing applied.

---

## Side-by-Side Comparison

| Repro | What the bug was | BEFORE (legacy, pre-patch) | AFTER (legacy + Phase 0 patch) |
|-------|-----------------|---------------------------|--------------------------------|
| Bug A — four arrows 2D | Four arrows all targeting the same cell caused collision-loop exhaustion; labels stacked on top of each other | [before](../repros/bug-A-four-arrows-2d.html) | [after](bug-A-four-arrows-2d.html) |
| Bug B — self-loop | `arrow_from == target` produced a degenerate Bezier; arrowhead pointed up-right instead of into the cell | [before](../repros/bug-B-self-loop.html) | [after](bug-B-self-loop.html) |
| Bug C — multiline overflow | Multi-line label: third `<tspan>` exited the pill background at the bottom | [before](../repros/bug-C-multiline-overflow.html) | [after](bug-C-multiline-overflow.html) |
| Bug D — position dropped | `position=above` annotations with no `arrow_from` were silently dropped; nothing appeared above the cells | [before](../repros/bug-D-position-dropped.html) | [after](bug-D-position-dropped.html) |
| Bug E — dense Plane2D | Five tightly-clustered points in Plane2D; pills overlapped with no repulsion | [before](../repros/bug-E-dense-plane2d.html) | [after](bug-E-dense-plane2d.html) |
| Bug F — long Plane2D label | Long label pill exceeded Plane2D viewBox width and clipped/overflowed | [before](../repros/bug-F-long-plane2d-label.html) | [after](bug-F-long-plane2d-label.html) |
| OK — simple annotations | Control case: two well-spaced annotations; should look identical before and after | [before](../repros/ok-simple-annotations.html) | [after](ok-simple-annotations.html) |

---

## Open side-by-side in browser

```bash
# macOS — open all BEFORE files in one window, AFTER files in another
open docs/archive/smart-label-audit-2026-04-21/repros/bug-A-four-arrows-2d.html \
     docs/archive/smart-label-audit-2026-04-21/repros/bug-B-self-loop.html \
     docs/archive/smart-label-audit-2026-04-21/repros/bug-C-multiline-overflow.html \
     docs/archive/smart-label-audit-2026-04-21/repros/bug-D-position-dropped.html \
     docs/archive/smart-label-audit-2026-04-21/repros/bug-E-dense-plane2d.html \
     docs/archive/smart-label-audit-2026-04-21/repros/bug-F-long-plane2d-label.html

open docs/archive/smart-label-audit-2026-04-21/repros-after/bug-A-four-arrows-2d.html \
     docs/archive/smart-label-audit-2026-04-21/repros-after/bug-B-self-loop.html \
     docs/archive/smart-label-audit-2026-04-21/repros-after/bug-C-multiline-overflow.html \
     docs/archive/smart-label-audit-2026-04-21/repros-after/bug-D-position-dropped.html \
     docs/archive/smart-label-audit-2026-04-21/repros-after/bug-E-dense-plane2d.html \
     docs/archive/smart-label-audit-2026-04-21/repros-after/bug-F-long-plane2d-label.html
```

Or open a single pair directly:
```bash
# Bug A
open docs/archive/smart-label-audit-2026-04-21/repros/bug-A-four-arrows-2d.html
open docs/archive/smart-label-audit-2026-04-21/repros-after/bug-A-four-arrows-2d.html
```

---

## File sizes

| File | Before (bytes, pre-patch) | After (bytes, Phase 0 patch) | Delta |
|------|--------------------------|------------------------------|-------|
| bug-A-four-arrows-2d.html | 447,535 | 447,537 | +2 |
| bug-B-self-loop.html | 440,054 | 440,054 | 0 |
| bug-C-multiline-overflow.html | 437,176 | 437,176 | 0 |
| bug-D-position-dropped.html | 433,853 | 436,987 | +3,134 |
| bug-E-dense-plane2d.html | 421,613 | 421,613 | 0 |
| bug-F-long-plane2d-label.html | 421,266 | 421,266 | 0 |
| ok-simple-annotations.html | 437,925 | 437,925 | 0 |

The minimal size changes reflect the Phase 0 patch scope: only QW-1..QW-7 and the
position-only label drop fix. Bug D grows by ~3 KB because previously-dropped
`position=above` labels now render and contribute SVG elements. No `measure_and_fix.js`
or Wave C DOM-mutation script is inlined — this is a pure legacy-engine render.
