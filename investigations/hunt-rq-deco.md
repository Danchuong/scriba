# Hunt: Render-Quality — Decoration Placement

**Hunter:** BMAD render-quality, DECORATION slice (pills, arrows, brackets, notes,
traces, carets, group hulls, links, strike).
**Repo state:** `main` @ 0.27.0 (brief cited 0.26.5; the shared-obstacle pass
landed in 0.26.5 / aff3ef5, caret index-lane drop in 0.26.4 / 37299be).
**Method:** render server SVG (`render.py … --no-minify`, `SCRIBA_ALLOW_ANY_OUTPUT=1`),
flatten nested `translate()` transforms to stage-absolute coords, compute AABB /
band / segment overlaps numerically. No Playwright. Probe + battery:
`scratchpad/deco/probe.py`, cases `scratchpad/deco/_*.tex`.

---

## Hand-off Brief

- **The 0.26.5 shared-obstacle pass HOLDS.** Every decoration it routed through
  the placer (`\group` title, `\note`, `\trace` label, `\link` label) dodges the
  content it floats over in realistic docs (0 px), and dodges siblings of its own
  kind (0 px). The 0.26.4 caret index/tick-lane drop also holds (35–39 px clear).
  Residual overlap appears **only** on fully-tiled boards where nothing is clear
  (SHOULD soft-penalty picks least-bad) — expected, low severity.
- **The remaining defects are all in the ONE decoration the pass deliberately did
  NOT route through the placer: the direct-emit `\cursor` caret.** `aff3ef5`'s own
  message says "the caret was fixed in 37299be" — but 37299be fixed only the
  index-lane drop. The caret is still painted directly (`emit_cursors_under`,
  `base.py:792`), is never an obstacle, and never dodges. Two collisions fall out.
- **Novel vs. the prior `audit-decoration-obstacle-class.md`:** that audit tested
  multi-cursor **adjacent** (row 1c: "52 px gap, no caret↔caret") but never
  **coincident** carets. Two `\cursor`s on the **same** index render **byte-identical** —
  100 % overlap. This is the sibling the audit missed. (Row 1d, caret-vs-below-pill,
  was audit-Confirmed MED and never fixed — I verify it persists and reads worse.)
- **Annotation pills + arrows are rock-solid** — the placer-routed control surface
  (audit row 12) shrugs off every stress I threw at it (6 pills on a 2-cell array,
  4 pills same cell, dense DP arrows): 0 px throughout.

---

## Decoration × collision table

| # | Decoration | vs what | overlap | severity | recent-fix regression? |
|---|------------|---------|---------|----------|------------------------|
| **A** | **Same-cell coincident carets** (`\cursor id=i` + `id=j` @ same index) | each other | **byte-identical coords → 100 %** (both `<polygon 92,72…>`, both `<text x=92 y=91>`); 3 carets all at (104,84)/(104,103) | **HIGH** | No — sibling the audit's row 1c (adjacent-only) missed; direct-emit caret never routed through placer |
| **B** | **Caret id** vs **same-cell `position=below` pill** | below-pill body+text | **7.0 px min-overlap**; caret id `i` y[94–108] x[162–170] **fully inside** pill y[88–107] x[126–206]; pill drawn after with `fill=white fill-opacity=0.92` → **id hidden** | **HIGH** (audit graded MED) | No — audit row 1d "Confirmed", never in fix scope; 0.26.4 index-drop moved caret INTO the below lane, deepening it |
| **C** | **`\group` hull** (convex) | non-member nodes | swallows non-members in **17/30 seeds** (seed 6: nodes 5,6 inside the {1,2,3,4} hull) | **MED** (inherent) | No — new; convex-hull-over-force-layout, not a placement-emitter bug |
| **D** | **Graph self-loop** edge `(1,1)` | — | degenerate **zero-length** `<line x1=153 y1=88 x2=153 y2=88>` + stray arrowhead, 32 px off node1 center (185,120) | **LOW** | No — new; edge-render completeness |
| E | Group title pill vs node (soft residual) | hull-corner node | 3.7 px worst / 40 seeds | LOW | No — 0.26.5 fix HOLDS; SHOULD-penalty leak |
| F | `\note` pill vs cell (soft residual) | cell value | 19 px on a **fully-tiled** 4×6 grid (nowhere clear); 0 px when board has room | MED | No — 0.26.5 fix HOLDS; nowhere-to-go |
| G | `\trace` label vs cell (soft residual) | cell value | 11 px on a **fully-tiled** 4×4 grid; 0 px on sparse | LOW | No — 0.26.5 fix HOLDS; nowhere-to-go |

**Clean (no collision found):** annotation pills — `above/below/left/right`,
`range`, `block` bracket — dense (6 pills / 2-cell array), same-cell (4 pills),
pill-vs-pill, pill-vs-caption **all 0 px**; arrows — long-range arc clears cell
value glyphs, arrowhead in-bounds, antiparallel curves **separate 17–27 px**;
strike crosses its own glyph **by design**; range/block bracket hug the block,
label sits above.

---

## Obstacle-fix verification (measured clearances)

All the 0.26.4 / 0.26.5 fixes the brief asked me to confirm — they hold.

| Fix (audit row) | Case | pre-fix (audit) | now | clearance |
|-----------------|------|-----------------|-----|-----------|
| `\group` title pill vs hull-corner node (5) | Graph seed 2 | 16.4 px overlap | **0 px** | pill 4 px **above** node 2 |
| `\note` vs corner content (8) | 2 notes, 1-row array | occludes value | **0 px** | notes dodge into empty band below row |
| `\note`↔`\note` stack (8) | 6 notes, dense grid | — | **0 px** | no note-vs-note overlap |
| `\trace` mid-label vs cells (3) | grid diagonal | ~12 px into row | **0 px** | label lifts to y[-11] above grid |
| `\trace`↔`\trace` label (3) | 3 traces on 4×4 | — | **0 px** | siblings dodge |
| caret vs **Array index** lane (1) | `c1` labeled array | 6.5 px over digit | **0 px** | id y=103 vs index y=68 → **35 px** |
| caret vs **NumberLine tick** lane (1b) | `c4` ticks+labels | apex in ticks (y≈18) | **0 px** | id y=93 vs tick y=54 → **39 px** |
| `\link` mid-label vs bridged shapes (7) | `c8` two arrays | index-lane near-miss | **0 px** | label seats in inter-array gap y=69 |
| `\link`↔`\link` label (7) | 2 crossing bridges | — | **0 px** | labels 20 px apart |
| antiparallel edge separation (C2) | directed s-a-b-t residual | (one straight line) | — | pairs bow **17–27 px** apart |

---

## Root cause (bugs A & B — one shared cause)

`emit_cursors_under` (`scriba/animation/primitives/base.py:792`) paints each caret
**directly**:

- `cx = center[0]` (`base.py:814`) — every caret sits at the **cell center x with
  zero per-caret offset** ⇒ two carets on one cell coincide exactly (**bug A**).
  `test_caret_x_tracks_cell_center` locks this; no fan-out logic exists.
- `apex_y = _cursor_apex_origin(top, center) + _CURSOR_GAP` where
  `_cursor_apex_origin` returns `max(cell_bottom, resolve_below_baseline())`
  (`base.py:786-790`). Its own docstring: *"resolve_below_baseline() is the exact
  anchor `position=below` pills already use, so the caret joins the same callout
  lane."* The caret is thus dropped **into the very lane** a same-cell below-pill
  occupies — and neither dodges the other (**bug B**). Grep confirms `cursor` is
  **never** registered as an `_Obstacle` and never passes through `_place_pill`.

The 0.26.5 pass routed `\group`/`\note`/`\trace`/`\link` through `_place_pill`;
the caret was excluded. Both A and B are exactly what that exclusion leaves open.

---

## Reproductions

```
scratchpad/deco/_mc3.tex   bug A — cursor id=i + id=j both at=1  (byte-identical markup)
scratchpad/deco/_cbp.tex   bug B — cursor id=i at=2 + annotate below on cell[2]
scratchpad/deco/_gh6.tex   bug C — group{1,2,3,4} seed 6, nodes 5,6 inside hull
scratchpad/deco/_sl.tex    bug D — directed edge (1,1) self-loop
```

Bug A raw markup (both carets, same frame):
```
data-annotation="arr.cursor[i]-solo" …><polygon points="92.0,72.0 87.0,80.0 97.0,80.0"…/><text x="92.0" y="91.0"…>i
data-annotation="arr.cursor[j]-solo" …><polygon points="92.0,72.0 87.0,80.0 97.0,80.0"…/><text x="92.0" y="91.0"…>j
```

---

## Conclusion

The shared-obstacle work is sound: **every decoration it touched now dodges
content and its own siblings**, verified with 10 measured clearances. The
render-quality debt that remains is concentrated in the **one decoration it left
direct-emit — the `\cursor` caret** — which cannot dodge and is not dodged:

1. **Two carets on the same cell superimpose (byte-identical).** HIGH — this is a
   focus moment (two pointers *meet* / converge: binary-search `lo==hi`,
   two-pointer `i==j`), the exact instant legibility matters, and both id labels
   stack into one blob. **Novel** — the audit only checked adjacent carets.
2. **A caret and a same-cell `position=below` pill collide, id hidden behind the
   pill.** HIGH — audit-known (row 1d, graded MED) but never fixed; the 0.26.4
   index-drop pushed the caret deeper into the pill's lane. Persists in 0.27.0.

Secondary: convex `\group` hulls visually swallow non-member nodes (17/30 seeds,
inherent to convex-hull grouping), and directed self-loop edges render as a
degenerate zero-length line + stray arrowhead.

**Confidence: HIGH.** Bugs A/B are proven from rendered SVG bytes + traced to the
exact emit line, and align with the prior audit's own "direct-emit ⇒ collision"
thesis (A is the sibling it missed, B the row it never fixed). C/D are
reproducible across seeds/configs. All fix-verifications are numeric, not visual.
