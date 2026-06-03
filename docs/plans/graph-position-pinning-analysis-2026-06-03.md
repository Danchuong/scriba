# Graph position-pinning across frames — feasibility analysis

**Date:** 2026-06-03
**Author:** investigation via Chrome CDP + source read
**Status:** analysis only — no code changed. Decision requested at the end.

## 1. Problem

When a Graph animation mutates **edges** across `\step`s (`add_edge` /
`remove_edge`) while the **node set stays constant**, every node teleports to a
new position each frame. The viewer reads this as chaotic ("rối"), because
nodes that did not logically change still move.

### Evidence (Chrome CDP, headless, frame-by-frame geometry)

Source (`layout="force", layout_seed=7`, undirected, nodes A,B,C,D fixed;
steps: recolor → add B-D → set_weight A-C → remove A-B):

| node | step0 (force init) | step1 (+B-D) | step3 (−A-B) |
|------|--------------------|--------------|--------------|
| A | (374,145) | (342,70)  | (353,73)  |
| B | (380,20)  | (361,136) | (329,205) |
| C | (380,280) | (356,247) | (373,233) |
| D | (20,280)  | (108,227) | (294,164) |

`layout="stable"` is better — a `set_weight`-only step keeps positions
identical (B stays (337,151) across step1→step2) — but `add_edge`/`remove_edge`
still reshuffle (B: (272,117)→(337,151)→(337,221)).

Conclusion: this is a **real design limitation**, not a config mistake.
(Separately, the rotated weight pills are *by design* — θ clamped to
[-90°,90°] so text is never upside-down; vertical edges land at 90° = sideways.
Not in scope here.)

## 2. Current architecture (how positions are produced)

1. **Construction** (`Graph.__init__`, `graph.py:711–791`): positions computed
   once from the initial `nodes`+`edges` via the chosen layout:
   - `fruchterman_reingold(nodes, edges, seed)` (`graph.py:395`) — seeded random
     init **then force iterations driven by edges**, so the edge set determines
     the final positions.
   - `compute_stable_layout(...)` (`graph_layout_stable.py:151`) — simulated
     annealing, 200 iterations.
   - `compute_hierarchical_layout(...)` for DAGs.
2. **Per-frame mutation** (`_frame_renderer.py` pre-pass) replays `apply_command`
   cumulatively onto the primitive for each frame.
   - `_add_edge_internal` / `_remove_edge_internal` (`graph.py:865–895`) append/pop
     an edge **and call `_relayout_with_warm_start()`**.
   - `_set_weight_internal` (`graph.py:897`) does **not** relayout (weight is not
     geometry) — this is why weight-only steps already stay put.
3. **Warm-start relayout** (`graph.py:931`): builds `old_positions` from the
   current `self.positions`, then calls `compute_stable_layout(...,
   initial_positions=old_positions)`. The optimizer **uses the warm start as a
   starting point but still runs all 200 SA iterations over every node**
   (`graph_layout_stable.py:245–256, 273–280`) — there is no freeze/anchor, so
   unchanged nodes drift.
4. **Animation** is already wired: `differ.py:218–236` emits a `position_move`
   transition whenever a node's `(x,y)` changes between frames, and the JS
   runtime tweens it (WAAPI). So *if* positions were pinned, the few that do move
   would still animate smoothly.

### Root cause (one sentence)

`_relayout_with_warm_start` re-optimizes **all** nodes on every topology change;
the warm start only seeds the annealer, it does not pin converged nodes.

## 3. What "position-pinning" means here

When the node set is unchanged between frame N and N+1:

- **Pinned nodes:** every node present in both frames keeps its exact `(x,y)`.
- **New nodes** (`add_node`, future): placed relative to neighbours without
  disturbing pinned nodes.
- **Removed nodes:** simply vanish; survivors do not reflow.
- **Edges** are just redrawn between the (unchanged) endpoints.

Net effect for the user's case: A,B,C,D never move; only the B–D line appears
and the A–B line disappears. Zero teleporting.

## 4. Design options

### Option A1 — Hard pin (recommended)
On mutation, **do not relayout existing nodes at all**. Keep `self.positions`
for every node already present; only compute a position for genuinely *new*
nodes (incremental placement near their first neighbour, then a local overlap
nudge that moves only the new node).

- **Pros:** maximally stable; trivial for the common case (edge-only mutation →
  zero movement); cheap (no global solve per frame).
- **Cons:** layout can become visually sub-optimal after many additions (no
  global rebalance); a newly dense node may sit awkwardly. Acceptable for
  editorial animations where the initial layout is hand-tuned via `seed`.

### Option A2 — Pin + local relax
Pin existing nodes as **fixed anchors**; run a *short* relaxation (e.g. ≤20
iterations) that is allowed to move **only new nodes / 1-hop neighbours**.

- **Pros:** new nodes settle nicely without global churn.
- **Cons:** more code (anchored solver); 1-hop neighbours still move a little
  (small, animates fine). Needs `compute_stable_layout` to accept a `frozen`
  set.

### Option A3 — Whole-timeline layout (compute once, reuse)
Compute one layout from the **union of all edges across all frames** (the
final/maximal topology), then use those same coordinates for every frame
(showing/hiding edges per frame).

- **Pros:** dead simple; perfectly stable; no per-frame solve. The graph already
  replays cumulatively, so the final state is known.
- **Cons:** early frames use the "final" spacing (may look slightly loose before
  edges exist); needs the renderer to compute the union topology up front and
  pass it to the primitive. Changes where layout is decided (scene-level, not
  primitive-level).

### Option A4 — Strengthen the existing warm start
Keep `_relayout_with_warm_start` but freeze any node whose neighbourhood is
unchanged, and lower iterations.

- **Pros:** smallest diff; reuses the SA path.
- **Cons:** half-measure — "neighbourhood unchanged" is fiddly; still some drift;
  doesn't fully solve the complaint.

## 5. Recommendation

**A1 (hard pin) as the default for mutation animations, with A3 available for
authors who want a globally-balanced static frame.** Rationale:

- The dominant use case (this bug report) is *edge-only* mutation on a fixed node
  set → A1 gives literally zero movement, which is exactly what's wanted.
- A1 is the smallest behavioural change that fully fixes the complaint and is
  cheap (no per-frame global solve).
- A3 is a good *opt-in* for "grow the graph" stories where global balance matters
  more than minimal motion. It can be added later without conflicting with A1.

A2 is the "nice to have" middle ground; defer unless A1's new-node placement
proves ugly in practice.

## 6. Implementation sketch (A1)

Touch points:

- `graph.py:_relayout_with_warm_start` — split into two paths:
  - **node set unchanged** → return early, keep `self.positions` verbatim
    (only refresh edge geometry, which `emit_svg` already derives from positions).
  - **nodes added/removed** → keep existing coords; place only new nodes
    (helper `_place_new_node(node, neighbours)` → centroid of placed neighbours
    + small radial offset; then a single-node overlap nudge).
- `graph_layout_stable.py:compute_stable_layout` — add an optional
  `frozen: set[str]` param; skip perturbation for frozen nodes (needed only if
  A2 is later adopted; A1 doesn't call the annealer on mutation at all).
- New surface for control. Two candidates (pick in §9):
  - implicit: pinning becomes the **default mutation behaviour** (no new param);
  - explicit: `\shape{G}{Graph}{..., relayout="pin"|"reflow"}` (default `pin`).
- `differ.py` — no change (it already diffs `(x,y)` and emits `position_move`).
- `_frame_renderer.py` — no change (replay path unchanged).

## 7. Risks & tradeoffs

- **Golden churn:** every Graph animation that mutates topology will re-render to
  new bytes → regenerate `tests/golden` + likely a `SCRIBA_VERSION` bump (cache
  invalidation), same as the 0.18.0 cycle.
- **Determinism:** A1 is *more* deterministic (no SA on mutation). Good.
- **Overlap:** pinned nodes can't be pushed apart, so a new node must be placed
  into existing free space; the single-node nudge must not move pinned nodes
  (cap displacement, or accept mild overlap and warn).
- **viewBox stability:** pinning keeps nodes inside the original bounds, so the
  stage size stays constant across frames (a side benefit — today the viewBox is
  already max-across-frames since 0.17.0).
- **Backwards behaviour:** if pinning becomes default, existing
  edge-mutation goldens change meaning (less motion). If gated behind a param,
  no surprise but authors must opt in.

## 8. Testing strategy

- **CDP geometry assertions** (reuse `.demo/cdp_probe.py`): for an edge-only
  mutation animation, assert every node's `(x,y)` is **identical** across all
  frames; assert edges appear/disappear as expected. This is the exact harness
  that found the bug.
- Unit tests on `_relayout_with_warm_start`: node-set-unchanged → positions
  object is unchanged (identity/value equality).
- `position_move` differ test: edge-only mutation emits **no** `position_move`
  transitions (only edge add/remove).
- New-node placement: add_node keeps all prior nodes fixed; the new node lands in
  a non-overlapping spot.

## 9. Open decisions (need your call)

1. **Default vs opt-in:** make pinning the default mutation behaviour, or gate it
   behind a `relayout="pin"|"reflow"` param (default to which)?
2. **Scope now:** ship A1 only, or A1 + A3 (opt-in whole-timeline) together?
3. **Versioning:** accept the golden re-render + `SCRIBA_VERSION` bump that
   pinning implies?

## 10. Effort estimate

- **A1, opt-in param:** ~half a day — early-return in `_relayout_with_warm_start`,
  `_place_new_node` helper, one param, unit + CDP tests, golden regen.
- **A1 default:** same code, larger golden/doc churn + version bump.
- **A3 opt-in:** +~half a day (scene-level union-topology pass + plumb positions).
- **A2 anchored solver:** +~1 day (frozen-set annealing + tuning).
