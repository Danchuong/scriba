# Graph/Theme cluster — consolidated implementation plan (PICKUP ENTRY POINT)

Status: **research complete, NOT implemented** (paused for a machine update).
Baseline: 0.29.0 / `SCRIBA_VERSION` 24. Three research briefs feed this:
`research-graph-pill-dark.md`, `research-nodelabel-fit.md`, `research-graph-scaling.md`.

Target release: **0.30.0 / `SCRIBA_VERSION` 24 → 25** (one combined bump — all four
pieces are byte-changes; the graph-canvas + nodefit-B share the `self.width`
substrate so a single marker covers them).

## The four pieces, sequenced low→high risk

| # | Piece | Risk | SVG golden blast | Ships alone? | Source brief |
|---|-------|------|------------------|--------------|--------------|
| 1 | **graph-pill dark** (CSS-only attr selector `[fill="white"]`, tint-preserving) | LOW | 0 SVG (107 uniform CSS delta) | yes | research-graph-pill-dark.md |
| 2 | **nodefit A** — fold `cross_frame_max_label_width` into `bounding_box`/viewBox (fixes frame-CLIP) | LOW | ~1 (`test_reference_tex_heavy`) | yes (no canvas dep) | research-nodelabel-fit.md |
| 3 | **graph-canvas scaling** — `_grow_force_canvas(N)` at graph.py:1087 (fixes node overlap at scale) | LOW-MED | 0 (corpus force-graphs ≤9 nodes) | yes | research-graph-scaling.md |
| 4 | **nodefit B** — pitch grow (`min_sep`/`_MIN_H_GAP`/`_H_PITCH`) to label width (fixes node-node COLLISION) | MED | ~0-1 | needs #3's canvas substrate | research-nodelabel-fit.md |

**Spike status:** none. nodelabel-fit flagged B as "needs a spike (canvas coupling
+ FDL determinism)"; research-graph-scaling RESOLVES it — the canvas grow is
implementation-ready, probe-verified deterministic, and is the exact substrate B's
bigger `min_sep` needs (else `_resolve_overlaps` re-clamps the spread). So #3 lands
first, then #4 consumes it.

## Shared substrate (build once, in PrimitiveBase)

`self._node_label_wmax: dict[str,int]` + `note_node_label(key,text,14)` +
`cross_frame_max_label_width(key)`. Monotonic per-node max painted label width;
seeded from base ids/labels at `__init__`; each primitive's `set_value` notes it,
so the EXISTING `_prescan_value_widths` (`_frame_renderer.py:326`) drives it to the
cross-frame max BEFORE viewbox. Survives the prescan snapshot-restore (separate
field, like Queue `_cell_width`). Both A (measure) and B (pitch) read the SAME map
→ R-32 holds. (Graph nodes DO render per-frame `value=` — the wide DP-state labels
— so Graph needs the scan too, confirmed: `value="dist[v]=infinity"` tw=96 clips 8px.)

## Recommended landing order

1. **#1 graph-pill dark** — standalone CSS, mirrors the 0.29.0 dim pattern. 4 rules
   after css:867. RED → `test_contrast.py` (4 tests).
2. **#2 nodefit A + the shared substrate** — A fixes the confirmed HIGH frame-clip,
   ships without any canvas dependency (grows `bounding_box().width` via
   left_pad/right_reach, independent of `self.width`). Radius UNCHANGED.
3. **#3 graph-canvas scaling** — 1 constant + `_grow_force_canvas` helper + 1
   grow-line + `passes=max(10,N)`. 0 corpus churn.
4. **#4 nodefit B** — pitch grow, on top of #3's canvas. Fixes node-node collision.

Could be one 0.30.0 release (all four) or split #1+#2 (low-risk, ships now) from
#3+#4 (the graph-layout pair). Either way: **combined `SCRIBA_VERSION` 24→25**.

## Verification strategy (the de-risking piece — automatable, not eyeballed)

Each brief specifies an invariant checker over the corpus; combine into one gate:
- **INV-1** no node-node overlap (graph-scaling §7)
- **INV-2** no exactly-coincident nodes
- **INV-3** every painted node-label extent ⊆ viewBox (nodelabel-fit §5)
- **INV-4** no adjacent-node label overlap
- **contrast** default graph-pill dark text ≥4.5:1; tinted pills keep their hex (graph-pill-dark RED)

Run INV-1..4 GREEN before AND after (they must already hold on the corpus, and keep
holding on the re-blessed set) — so the ~1-2 SVG re-blesses are proven correct by
invariant, not by reading files.

## Byte / golden summary

- graph-pill dark: 107 corpus goldens re-bless by ONE identical CSS delta (SVG untouched).
- nodefit A: ~1 SVG re-bless (`test_reference_tex_heavy`, "Bellman-Ford" tw=92>40).
- graph-canvas: 0 (corpus force-graphs ≤9 nodes).
- nodefit B: ~0-1 (pitch only trips on wide labels).

Deferred still (out of this cluster): the math-`$…$` graph-weight inline-color
residual (dark, sub-AA, needs `!important`/graph.py — rare), and the 4 LOW
transition-window polish items.
