# Smart-Label Bug Repros

Generated: 2026-04-21  
Open each link in a browser. Advance animation steps with the arrow buttons or keyboard.

---

## Bug reproductions

- **[A — 4 arrows into one 2D cell](file:///Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/smart-label-audit-2026-04-21/repros/bug-A-four-arrows-2d.html)**  
  Collision loop exhaustion: 4 orthogonal arrows targeting `cell[1][1]` in a 3×3 DPTable. The 4th label (and sometimes 3rd) exhaust all 4 compass nudge directions and fall through to the forced-`up` fallback, stacking labels vertically with overlapping leader lines.  
  _Start here — most dramatic visual._

- **[B — Self-loop arrow (src == dst)](file:///Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/smart-label-audit-2026-04-21/repros/bug-B-self-loop.html)**  
  `arrow_from="F.cell[3]"` targeting `F.cell[3]`: `dist=0` → degenerate Bezier goes left and returns to the same point; arrowhead points up-right instead of down into the cell. Looks like a comma/squiggle beside the cell.

- **[C — Multi-line label overflows pill](file:///Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/smart-label-audit-2026-04-21/repros/bug-C-multiline-overflow.html)**  
  48-char label wraps to 3 lines. The third `<tspan>` at `fi_y + 26` sits below the pill background's bottom edge by ~6 px — text visibly exits the colored pill rectangle.

- **[D — position= annotation silently dropped on Array](file:///Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/smart-label-audit-2026-04-21/repros/bug-D-position-dropped.html)**  
  Three `position=above` annotations on Array cells with no `arrow_from` / `arrow=true`. `emit_annotation_arrows` hits `if not arrow_from: continue` and silently discards all three. The labels `ptr`, `mid`, `end` never appear in the output.

- **[E — Dense Plane2D cluster, pills all overlap](file:///Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/smart-label-audit-2026-04-21/repros/bug-E-dense-plane2d.html)**  
  5 points within ±0.1 math-units of origin (≈5 SVG px apart). `_emit_text_annotation` has no collision avoidance; all 5 pills land at nearly identical coordinates and fully overlap each other.

- **[F — Long Plane2D label exceeds viewBox](file:///Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/smart-label-audit-2026-04-21/repros/bug-F-long-plane2d-label.html)**  
  Label `"This is a very long annotation label..."` on a 280 px-wide canvas computes `pill_w ≈ 504 px`. No clamping in `_emit_text_annotation`; the pill `<rect>` and text extend well beyond the SVG viewBox right boundary and are clipped by the browser.

---

## Control case (healthy)

- **[OK — Two well-spaced annotations](file:///Users/mrchuongdan/Documents/GitHub/scriba/docs/archive/smart-label-audit-2026-04-21/repros/ok-simple-annotations.html)**  
  Short labels `pick` and `best` on separate, well-separated Array cells. Collision avoidance has plenty of room; both pills render correctly with clean arcs. Use this to calibrate your eye before viewing the bugs.

---

## Suggested viewing order

1. Open `ok-simple-annotations.html` first to see what healthy output looks like.
2. Then `bug-D-position-dropped.html` — the most subtle bug (nothing renders, no error).
3. Then `bug-A-four-arrows-2d.html` — step to frame 2 to see the stacking collision.
4. Then `bug-B-self-loop.html` — step to frame 2 to see the degenerate arrow.
5. Then `bug-C-multiline-overflow.html` — inspect the label pill bottom edge closely.
6. Then `bug-E-dense-plane2d.html` and `bug-F-long-plane2d-label.html` for the Plane2D issues.
