# Hunt 2 — Animation Transition Integrity

**Hunter slice:** correctness of the motion manifest and each transition (Next / Prev / Jump), computed statically from the emitted per-frame server SVG + the `tr`/`fs` transition records in the JSON island. No browser; no Playwright.

**Verdict up front: transitions are CLEAN on every integrity axis.** 0 HIGH, 0 MEDIUM. Across **25 scenes / 267 frames / 239 manifests / 1152 motion records**, there is **no off-canvas glide, no NaN/Infinity, no no-op record, no forward value/state flip-back, no jump≠step divergence**, and the reverse inversion is a clean involution (`inv(inv(M)) == M`) that always lands on server truth. The only residuals are mid-transition **animation-smoothness** artifacts (elements that *snap* instead of *tween*, plus one transient reverse colour-flash) — all LOW, all fs-snap-salvaged, three of them explicitly documented in the source.

---

## Hand-off Brief

- **What was checked (the 5 brief detectors), with numbers:**
  1. **from/to sanity** over all 1152 records: NaN/Inf `0`, no-op (`from==to`) `0`, off-canvas glide `0`/90 coord moves, bad-coord-parse `0`.
  2. **Reverse (Prev) inversion**: `inv(inv(M))==M` for all 239 manifests; reverse-reconstruct of frame N from `inv(frames[N+1].tr)` matched the real frame-N SVG on **1146/1152** records (6 transient exceptions, one scene).
  3. **fs-snap standalone**: forward `to` matched the DEST server render on **1152/1152** records — the 0.26.4/0.27.0 flip-back class is **absent**.
  4. **element_add/remove geometry**: every one of the 9 `element_add` records is salvaged; `element_remove` is structurally unreachable (see note).
  5. **multi-step JUMP == step**: `0` divergence — `snapToFrame` and every step's fs-snap both resolve to `frames[N].svg`.

- **The load-bearing invariant:** every manifest-bearing frame carries **`fs=1`** (239/239, `0` exceptions). `_html_stitcher.py:664-665` sets `fs` from `svg_changed`, and every captured transition necessarily alters the server SVG (state class, value text, node transform, element presence), so a manifest without a full-sync snapshot cannot occur. Because the runtime fs-snaps to the server frame after Next (`scriba.js:451-455`), after Prev (source-frame `fs`, `scriba.js:493`), and Jump snaps directly (`scriba.js:113-124`), **the settled geometry after any navigation is provably the server-rendered frame.** The WAAPI handlers only govern the ~180 ms in-between.

- **Corpus (10 of 11 motion kinds exercised):** recolor 787, value_change 129, position_move 85, annotation_add 67, highlight_off 30, highlight_on 29, element_add 9, annotation_recolor 8, cursor_move 5, annotation_remove 3. Scenes: stack, queue, array, linkedlist, bst_operations, splay, union_find, union_find_tree, kruskal_mst, dijkstra, bfs, binary_search, two_sum, kmp, dptable, hashmap, variablewatch, convex_hull_trick, convex_hull_andrew, elevator_rides, maxflow, tree, graph, linkedlist_reverse, + one authored case file (`case_cursor.tex`, cursor_move).

- **`element_remove` = 0 (by design, not a gap):** stack `pop`, queue `dequeue`, array `remove` are demoted to the recolor/fs-snap path by `_is_pure_removal` (`differ.py:31-48`, applied at `:108-125`). Verified on stack `pop=2` (f4) which emits only recolor+highlight_off, never `element_remove`. The kind is effectively vestigial for the shrink verbs in the DSL.

- **Reproduce:** `render.py <tex> -o <out>.html --no-inline-runtime --no-minify` (needs `SCRIBA_ALLOW_ANY_OUTPUT=1` to write to scratch), then the three probes in `scratchpad/hunt2-transition/` (`probe.py`, `reverse_check.py`, `from_check.py`) over the extracted JSON islands.

---

## Defect table

| Scene | Motion record | from → to | Defect | Number | Severity |
|---|---|---|---|---|---|
| binary_search | `A.cell[1]` recolor (f4→5) | `idle → done` | **Reverse flash.** Source SVG renders the cell `scriba-state-highlight` (from `\highlight{A.range[0:8]}`, tex:36), but the model `from` is `idle`. On **Prev** the inverse recolor swaps `done→idle` as a class edit, flashing the wrong colour for ~180 ms before the fs-snap restores `highlight`. | 6 recs (f4→5 ×5, f5→6 ×1); 1/25 scenes | LOW |
| stack, queue, bst, splay, union_find, union_find_tree, bfs, convex_hull_andrew | `element_add` on the **bare shape** (`s`,`q`,`T`,`G`,`Q`,`stk`,`plane`) | `null → idle` | **Dead clone.** Target is the shape name, not a `[data-target]` element, so the runtime clones nothing (`scriba.js:216`). Structural adds never fade in — they appear at the fs-snap. Documented (`differ.py:20-28`, F4). | 9/9 element_add records | LOW |
| stack, convex_hull_andrew, elevator_rides, graph, … | `highlight_on`/`highlight_off` | `→ true` / `→ null` | **Dead class.** Runtime toggles `.scriba-highlighted`, which the CSS marks `KNOWN-DEAD` (no rule, `scriba-scene-primitives.css`). The visible highlight is the server's `scriba-state-highlight` delivered by the fs-snap; highlight never tweens. | 20 flagged / 59 highlight recs | LOW |
| two_sum (f4→5), bfs (f14→15), linkedlist_reverse (f9→10) | none (`tr=null`, svg changed) | — | **Silent snap.** Identical `data-target`/`data-annotation` sets but SVG content grew (~150–400 B, e.g. a caption/label re-render); differ emits no manifest, frame snaps without a tween. Geometry correct. | 3 frames | LOW |

All four rows are **fs-snap-salvaged**: the settled frame after the transition is the correct server SVG in every case.

---

## Reverse-integrity findings

- **Structural inversion is exact.** `_invertRec` (`scriba.js:367-373`) swaps `from/to` and maps the kind via `_INV_KIND` (add↔remove, highlight_on↔off; recolor/value_change/position_move/cursor_move/annotation_recolor self-inverse). `inv(inv(M)) == M` held for **all 239 manifests** — no orphaned add/remove, no kind drift.
- **Reverse lands on server truth.** Prev feeds the **source** frame's `fs` (`scriba.js:493`); since `fs=1` universally, Prev fs-snaps to `frames[N].svg` after applying `inv(M)`. Reverse-reconstruct (apply `inv(frames[N+1].tr)`, compare each record's landing state/coord to the real frame-N SVG) matched on **1146/1152** records.
- **The 6 misses are the binary_search reverse-flash** — a divergence between the model `from` and the *rendered* source state, not a landing-geometry error. It corrupts only the ~180 ms intermediate on Prev; the fs-snap settles correctly. Root cause is the range-highlight overlay: `\highlight{A.range[a:b]}` paints member cells `scriba-state-highlight` in the SVG while the differ's per-cell `state` axis still reads `idle`, so the manifest's recolor `from` is blind to the overlay.
- **Coord kinds invert perfectly.** cursor_move/position_move `from`/`to` are byte-exact to the server-rendered apex/transform in both frames (e.g. `case_cursor` f1 `to=340.0` ↔ SVG apex `340.0`; f0 `from=30.0` ↔ apex `30.0`), so the swap glides Prev back along the identical path. 0/90 off-canvas.

## fs-snap standalone findings

- **Forward flip-back: 0 / 1152.** For every `value_change` and `recolor`, the manifest `to` equals the DEST server render (value text via `data-role="value"` / last `<text>`; state via `scriba-state-*`). The runtime stamp (`scriba.js:183`) and the fs-snap agree — no value flips back on arrival. The class that produced 0.26.4/0.27.0 is not present in this corpus.
- **Math values are pulse-only** (`toVal.indexOf('$')===-1` guard, `scriba.js:183`) — never stamped as a literal, so no `$\max(0,i)$` flash; excluded from the flip-back check correctly.
- **Every fs=1 snapshot is self-consistent**: re-rendering each step's DEST SVG and reading the value/state/apex it pins matched what the transition claims to arrive at (1152/1152 for `to`).

---

## Conclusion

**Transition integrity is CLEAN.** The manifest + runtime are architected so that Next, Prev, and Jump all resolve to the exact server-rendered frame via the universal `fs=1` full-sync snapshot; the per-kind WAAPI handlers are pure in-between decoration and cannot corrupt the settled state. Static reconstruction confirms this on 1152 records: zero off-canvas, NaN, no-op, or forward flip-back; a clean reverse involution; jump≡step.

The residual imperfections are **animation smoothness, not integrity**, and rank LOW:
- One transient **reverse colour-flash** (6 records, binary_search) where a `\highlight{range}` overlay outruns the model-state `from` — the single finding that shows a visibly-wrong intermediate, and only on Prev, and only for ~180 ms.
- Two documented **snap-instead-of-tween** classes (bare-shape `element_add`; dead `.scriba-highlighted`) — structural adds and highlights appear at the snap rather than fading.
- Three **silent-snap** content changes the differ doesn't model as motion.

**No HIGH or MEDIUM defect. No fix is required for correctness.** If polish is wanted, the highest-value single change is making the range-highlight overlay participate in the recolor `from` (or emitting the overlay state as the cell's rendered `from`) so Prev stops flashing `idle` under a highlighted range.

**Confidence: HIGH.** Evidence is Confirmed (path:line + parsed numbers) for the invariant, the flip-back nulls, the coord exactness, and the reverse involution; the reverse-flash root cause is Confirmed against `binary_search.tex:36` and the per-frame rendered state classes. The only caveat is corpus scope: `cursor_move` rests on 5 records from one authored case file (existing editorials use the legacy recolor-hop `\cursor`), and `element_remove` is unexercised because the DSL demotes every shrink verb — both are structural facts of the emitter, not blind spots.
