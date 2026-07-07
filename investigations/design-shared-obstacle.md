# Design — Shared-Obstacle Decoration Model (structural fix for the direct-emit class)

> BMAD design (read-only on source; probes in scratch; only this doc written).
> Repo @ `main` `11f8f62`, scriba **0.26.4**, `SCRIBA_VERSION = 21`
> (`scriba/_version.py:3,6`). Every `path:line` was read this session. Every
> **Confirmed** verdict is backed by source **and** a rendered geometry proof —
> server SVG rendered with `.venv/bin/python render.py <p>.tex -o _<p>.html`,
> element y/x-bands parsed numerically (baseline rules: default `svg text` =
> `central`, `.scriba-index-label` = `hanging`). **No Playwright.**
>
> **Grading:** *Confirmed* = source cite + rendered numeric band. *Deduced* =
> source cite + mechanical inference. *Hypothesized* = design projection.
>
> **Predecessor:** `investigations/audit-decoration-obstacle-class.md` proved the
> class (10 direct-emit surfaces bypass the pill placer). The seed **caret** case
> is already fixed (commit `37299be`, `_cursor_apex_origin` `base.py:653`, reusing
> `resolve_below_baseline()`). This doc designs the fix for the **remaining**
> surfaces and turns the audit's "end-state" into a phased, implementable plan.

---

## 0. Scope — what is left after the caret fix

The caret (rows 1/1b/1d) is landed. The **remaining confirmed / latent** direct-emit
surfaces, all re-rendered and re-measured this session at `11f8f62` (bands unchanged
from the audit):

| Surface | Sev | Emit site | Status @ 0.26.4 (rendered proof) |
|---|---|---|---|
| `\group` title pill | MED | `graph.py:1708-1731`, flush `:2220` | pill `y[-2.6,16.4]` over node2 circle `y[0,40]` = **16.4 px (41 %)**, x fully inside — Confirmed |
| `\note` pill | MED | `_frame_renderer.py:1036` (`_emit_scene_notes`) | note n2 `y[31,50]` over cell-4 value "50" `y[25,39]` = **8 px**, x290 ∈ `[271,324]` — Confirmed |
| `\trace` stroke | MED | `base.py:583-588` (`emit_traces_under`) | path `y=20`, sw2.5 → band `[18.75,21.25]` dead-center of value `[13,27]` = **2.5 px** (halo-mitigated) — Confirmed |
| `\trace` mid-label | MED | `base.py:601-625` | grid-clamp only; near-miss over cell backgrounds — Confirmed latent |
| `\link`/`\combine` bridge | MED | `_frame_renderer.py:967-990` (`_emit_scene_links`) | bridge `M104,12 Q122.2,72.9 166,119`, top-of-z — Confirmed latent |
| `\link`/`\combine` mid-label | MED | `_frame_renderer.py:972-981` | label "map" `y[63.7,74.7]` in array-A index lane (near-miss) — Confirmed latent |
| strike diagonal | LOW | `base.py:1289-1294` | crosses own glyph **by design** — Confirmed intended |
| R-35 block bracket | LOW | `base.py:1313-1323` | dashed edges abut adjacent cell borders (cosmetic) — Confirmed latent |

---

## PART 1 — Placer infrastructure inventory (what already exists to reuse)

The pill placer exposes **two capabilities** a decoration needs. The audit's
"end-state" — *every direct-emit decoration is a `_place_pill` client for its text
and an `_Obstacle` contributor for its geometry* — decomposes exactly into these two
calls plus two resolvers.

### 1.1 Capability (a) — place TEXT so it dodges obstacles

**Public entry: `emit_position_label_svg(...)`** — `_svg_helpers.py:3502`.
```
emit_position_label_svg(
    lines,                       # output buffer (append-in-place)
    ann,                         # {"label": str, "color": token, "position": "above|below|left|right|inside", "target": key}
    anchor_point,                # (x, y) = element CENTER (see resolve_label_anchor)
    *, cell_height, render_inline_tex,
    placed_labels,               # list[_LabelPlacement] — SHARED, append-only registry
    primitive_obstacles,         # tuple[_Obstacle, ...] — content + segments to dodge
    cell_width, below_baseline, is_range,
)
```
When `placed_labels is not None`, **every** pill routes through `_place_pill`
(`:3607-3639`): it computes the natural position from `position`, scores it against
the obstacle set, and **appends the chosen placement to `placed_labels` itself**
(`:3634`). This is the exact call the annotation control uses (§1.3). *Confirmed.*

**Lower-level entry: `_place_pill(...)`** — `_svg_helpers.py:3372` (keyword-only):
```
_place_pill(*, natural_x, natural_y, pill_w, pill_h,
            placed_labels,               # obstacles are built from this…
            extra_obstacles=(),          # …PLUS this tuple (§1.2)
            viewbox_w, viewbox_h, viewbox_min_x=0, viewbox_min_y=0,
            side_hint=None) -> (placement, fits_cleanly)
```
Obstacles = `tuple(_lp_to_obstacle(p) for p in placed_labels) + extra_obstacles`
(`:3453-3455`); candidates = natural + 48 nudges + R-34 escape lanes, each clamped
then scored by `_pick_best_candidate` argmin (`:3474-3484`). **The caller must append
the returned placement to `placed_labels`** — `_place_pill` does not (C-3, `:3405-3407`).
Use this directly when the decoration has a raw pill (its own `<rect>`), not an
annotation `ann` dict — i.e. `\group` title, `\trace` label, `\note`. *Confirmed.*

### 1.2 Capability (b) — register own GEOMETRY as an obstacle others avoid

Build an **`_Obstacle`** (`_svg_helpers.py:165`, frozen) and include it in the
`extra_obstacles`/`primitive_obstacles` tuple threaded into (a):

- **AABB** (a pill, node circle, cell, hull corner):
  `_Obstacle(kind, x=cx, y=cy, width=w, height=h, severity)`.
  Kind weights (`_KIND_WEIGHT` `:305-319`): `content_cell` = 0.02 (a few-px graze is
  cheap; covering a full cell is expensive), `pill` = 1.0, `target_cell` = 3.0
  (**MUST** hard-block — never placed over the thing it labels).
- **Segment** (a trace stroke, link bridge, strike line):
  `_Obstacle(kind="segment", x=x0, y=y0, x2=x1, y2=y1, severity="SHOULD")`.
  Handled by the P7 edge-occlusion term (weight `_W_EDGE_OCCLUSION` = 40.0,
  `:339`); SHOULD-only, no hard-block. width/height unused for segments.

A registered obstacle only makes **other** placer clients dodge it; it does **not**
move the geometry that registered it. *Confirmed* (dataclass + weight table read).

### 1.3 The shared plumbing — `emit_annotation_arrows` (the CONTROL, base.py:1154)

The annotation path is the proof-of-pattern; a decoration should mirror it:
1. `_merged_segs = resolve_obstacle_segments()` (own) + translated cross-primitive
   `scene_segments` (`:1193-1205`).
2. `_prim_seg_obs` = segments → `_Obstacle` **+** `resolve_self_content_rects()` →
   `_Obstacle(kind="content_cell", SHOULD)` (`:1208-1226`). **This is the channel
   that turns a primitive's own content (cell values, nodes) into obstacles.**
3. `placed: list[_LabelPlacement] = []` built fresh per frame (`:1235`); per
   annotation `_combined_obs = _prim_seg_obs + prior_arrow_segments` (`:1241-1249`)
   threaded into every emit via `placed_labels=placed, primitive_obstacles=_combined_obs`
   (`:1305-1306`, `:1391-1392`, `:1428-1429`). *Confirmed.*

### 1.4 The two resolvers a decoration must consult

- **`resolve_self_content_rects() -> list[BoundingBox]`** — base default `[]`
  (`base.py:860`); **already overridden by Array** (cell values, `array.py:814`) and
  **Graph** (node circles + edge pills, `graph.py:1545`). This is the exact obstacle
  source a `\group`/`\trace`/`\note` fix reuses — no new geometry code. *Confirmed.*
- **`resolve_below_baseline() -> float | None`** — base default `None`
  (`base.py:872`); Array overrides (`:832`). The callout-lane y below the
  index/caption stack; the caret fix already reuses it (`_cursor_apex_origin`
  `base.py:670-673`). Relevant to `position=below` label placement. *Confirmed.*

### 1.5 The architectural seam — why the fix is PHASED (Deduced)

**Two tiers, by where the decoration is emitted:**

- **Per-primitive tier** (`\group` title, `\trace`): emitted *inside* the primitive's
  `emit_svg`, where `resolve_self_content_rects()` and a frame-local `placed` list are
  one call away. graph.py order: `_emit_group_hulls` (`:1885`, stashes labels) → nodes
  → `emit_traces_under` (`:2178`) → flush `_pending_group_labels` (`:2220`) →
  `emit_annotation_arrows` (`:2229`). The group label + trace are emitted **before**
  the annotation placer builds `placed`. Sharing one registry means lifting a
  frame-local `placed` to span hull-labels + traces + annotations, **or** each
  decoration building its own obstacle set from `resolve_self_content_rects()`
  (cheaper, no cross-decoration coupling). **Local, self-contained fix.**
- **Scene tier** (`\note`, `\link`/`\combine`): emitted by module functions
  `_emit_scene_notes(frame, viewbox, parts)` (`_frame_renderer.py:1036`) and
  `_emit_scene_links(frame, primitives, stage_offsets, parts, …)` (`:928`) at scene
  assembly (`:1524`, `:1532`), **after every `prim.emit_svg`**. They receive
  `parts`/`viewbox`/`primitives`/`stage_offsets` but **no `placed_labels` and no
  obstacle set**. Routing them through the placer needs a *scene-level obstacle set*:
  gather each `prim.resolve_self_content_rects()`, translate by `stage_offsets`, feed
  as `extra_obstacles`. **This is the "second placement pass" — the bigger lift.**

---

## PART 2 — Per-decoration verdict

Mechanisms: **(a)** route TEXT through the placer · **(b)** register GEOMETRY as an
obstacle · **(c)** both · **(d)** leave (by-design / cosmetic).

| # | Decoration | Verdict | Minimal structural change | Repro (0.26.4, rendered) | Golden impact |
|---|---|---|---|---|---|
| 1 | **`\group` title pill** | **(a)** | In `_emit_group_hulls` (`graph.py:1715-1719`), replace `prx=minx / pry=miny-ph-4` with `_place_pill(natural_x=minx+pw/2, natural_y=miny-ph/2-4, pill_w=pw, pill_h=ph, placed_labels=<frame list>, extra_obstacles=<node AABBs from resolve_self_content_rects()>, viewbox_min_*=−vb)`; emit rect/text at the returned center; append placement. Node circles are already exposed (`graph.py:1545`). | `_c7`: pill `y[-2.6,16.4]` over node2 `y[0,40]` = 16.4 px; text x42.3 | **0 corpus goldens** (grep `scriba-group-label` in `tests/golden/**/*.html` = 0). `test_group_verb.py` behavioral (hull-regex, no coord assert `:82`) → survives. |
| 2 | **`\note` pill** | **(a)** | In `_emit_scene_notes`, build a scene obstacle set (loop `primitives` → `resolve_self_content_rects()` shifted by `stage_offsets`), pass the compass `(x,y)` from `_note_anchor_xy` as `natural_*`, let `_place_pill` push it off content. Keep note↔note stacking as the natural seed (already correct, `:1018-1032`). Needs `primitives`+`stage_offsets` handed to `_emit_scene_notes` (today it only gets `frame,viewbox,parts` `:1036`). | `_c9`: note n2 `y[31,50]` over "50" `y[25,39]` = 8 px, x290 ∈ `[271,324]` | **0 corpus goldens** (grep `note[` = 0). `test_note_command.py` behavioral (inside-viewbox `:118`, key/color present) → survives if note stays in viewBox. |
| 3 | **`\trace` mid-label** | **(a)** | Replace the grid-clamp (`base.py:611-615`) with `_place_pill(natural=(midx,midy-ph-8), extra_obstacles=resolve_self_content_rects() + own-stroke-segments)`; append to a frame `placed`. | latent (`_c6`); on `decoration_spiral` labels sit among grid cells | **≤1 corpus golden** (`decoration_spiral.tex`) IF the label relocates — the one real geometry-move. |
| 4 | **`\trace` stroke** | **(b)** | Keep the polyline as-is (it threads cell CENTERS — a path *between* cells cannot dodge; the paint-order halo is the by-design legibility guard). **Add**: append each `(pts[i]→pts[i+1])` segment as `_Obstacle(kind="segment", SHOULD)` into the frame obstacle set so later annotation/note pills dodge it. Stroke byte-identical. | `_c5`: stroke `y=20` band `[18.75,21.25]` in value `[13,27]` = 2.5 px | **0 stroke shift** — `decoration_spiral` stroke byte-identical; only a co-located pill moves. |
| 5 | **`\link`/`\combine` bridge** | **(b)** | Sample the quadratic `M..Q..` into segments; push as scene-level `_Obstacle(kind="segment")` so notes/pills dodge the bridge. Path byte-identical. | `_c8`: bridge over inter-shape lane, top-of-z | **0 corpus goldens** (grep `link[` = 0). |
| 6 | **`\link`/`\combine` mid-label** | **(a)** | Same scene-obstacle-set dependency as `\note` (#2). Route the `t=0.5` label through `_place_pill`. | `_c8`: "map" `y[63.7,74.7]` in array-A index lane (near-miss) | **0 corpus goldens**. |
| 7 | **strike diagonal** | **(d)** | Leave. Crosses its own struck glyph intentionally (strike-but-keep, `base.py:1266`). Optional (b): register as segment so a *sibling* pill dodges — not required. | `_c10`: crosses own value by design | **0** (no change). |
| 8 | **R-35 block bracket** | **(d)** | Leave (LOW, cosmetic edge-abut; its *label* already routes through the placer `base.py:1363`). Optional (b): register the outline rect. | `_c11`: edges abut adjacent borders | **0** (no change). |

**Note the asymmetry the mandate flagged:** #4 (stroke) and #5 (bridge) are **(b)-only** —
they are paths *between* anchors and physically cannot "dodge," so the fix is to make
*others* avoid them, not to move them. #1/#2/#3/#6 are TEXT that *can* relocate, so they
are **(a)**. Forcing one mechanism on both would be wrong.

---

## PART 3 — Phasing + impact

Ordered by (severity × cheapness):

### Phase 1 — cheap × high-value: `\group` title + `\note`, mechanism (a)
The two MED confirmed content-occlusions with the clearest "text should dodge" semantics.
- **`\group` is the cheapest**: fully local to `graph.py`; node obstacles already exposed
  by `resolve_self_content_rects()`. One placement call, no plumbing changes.
- **`\note` needs the scene-obstacle-set plumbing** (hand `primitives`+`stage_offsets` to
  `_emit_scene_notes`, gather content rects). Moderate but self-contained; once built it
  **also serves `\link` label (#6) in Phase 2**, so it is the right next investment.
- **Golden character: ~0 byte-golden corpus shift.** The byte-golden corpus
  (`tests/golden/examples/corpus/`, 107 docs) contains **0** `\group`, **0** `\note`,
  **0** `\link` docs (measured). Unit tests for both are behavioral → survive. The only
  geometry that moves is inside the **new RED tests** added with the fix.

### Phase 2 — structural: the shared scene-level obstacle pass
Route `\link`/`\combine` label (#6) and `\trace` mid-label (#3) through the placer; register
the `\trace` stroke (#4) and bridge (#5) as segment obstacles. Resolves the *cross*-decoration
collisions (bridge-vs-pill, note-vs-trace) the per-lane approach never could.
- **Golden character: exactly 1 corpus doc moves** — `decoration_spiral.tex` (the only
  byte-golden `\trace`), and only its two trace-label `<rect>/<text>` coordinate pairs;
  the grid cells, values, and trace **strokes stay byte-identical** (stroke is (b)-only).

### Phase 3 — leave
strike (#7) and R-35 bracket (#8): (d). No change.

### Recommendation
**Ship Phase 1 (`\group` + `\note`) as one release; defer Phase 2.** `\group` alone is
a candidate for an even smaller first cut (zero plumbing), but bundling `\note` amortizes
the scene-obstacle-set work that Phase 2's `\link` reuses.

### SCRIBA_VERSION + golden-gate expectation
- **Bump `SCRIBA_VERSION` 21 → 22** when Phase 1 lands, on the documented principle
  ("Bumped on HTML output shape changes", `_version.py:8-11`): the output shape for
  `\group`/`\note` inputs changes when they would collide. **No version string is embedded
  in golden HTML** (verified — grep for version tokens in a golden = none), so a bump does
  **not** cascade-shift the 107 goldens.
- **The golden gate is NOT "0 geometry" and NOT "all goldens re-bless."** It is:
  > **Every existing byte-golden corpus doc is byte-identical** (none use `\group`/`\note`),
  > **and** if any doc *did* use them near content, **only that decoration's own pill x/y
  > moves — nothing else** (grid, values, strokes, other pills frozen).
- This is closer to the **caret's 0-shift** than the mandate's prior assumed: the corpus
  simply does not exercise group/note, so Phase 1 re-blesses ~nothing. The **guaranteed
  non-zero move is Phase 2's `decoration_spiral`** (trace label) — that is the doc where
  "geometry MOVES, only the decoration's own position" is literally demonstrable.
  *(Correction to the mandate's framing, evidence-graded: Confirmed by corpus grep.)*

---

## PART 4 — RED-first test plan

Model directly on **`tests/unit/test_cursor_label_lane.py`** (the caret fix's own test):
numeric band non-overlap (RED, fails today) + an exact byte snapshot for the
no-collision case (GREEN, must never move). Reuse its `_central_band`/`_hanging_band`
helpers and the audit's `scratchpad/probe.py` band math.

### 4.1 Per-decoration non-overlap assertions (RED today → GREEN after fix)

- **`\group`** — `test_group_label_dodges_corner_node` (new
  `tests/unit/test_group_label_obstacle.py`): build the `_c7` Graph
  (`nodes=[1..5], group nodes=[1,2,3] label="component X"`), parse the
  `scriba-group-label` `<rect>` band and node-2 circle band, assert
  `rect_y_top >= node_circle_bottom` **or** x-separation. **RED now**:
  `[-2.6,16.4] ∩ [0,40] = 16.4`.
- **`\note`** — `test_note_dodges_corner_value` (extend `test_note_command.py`):
  build the `_c9` scene (Array `data=[10..50] labels="0..4"` + two `\note{…}{at=top-right}`),
  parse note-n2 `<rect>` band and cell-4 value "50" band, assert non-overlap.
  **RED now**: `[31,50] ∩ [25,39] = 8`.
- **`\trace` label** — `test_trace_label_dodges_cell_value`: a layout where the mid-vertex
  label sits over a value; assert the pill band clears it. **RED** in the tuned layout.
- **`\trace` stroke-as-obstacle** — `test_annotation_pill_dodges_trace_stroke`: Array +
  `\trace` over the row + an annotation/`position=below` pill on a traced cell; assert the
  pill's band clears the trace segment (`[18.75,21.25]`). **RED now** — the pill is blind
  to the stroke because it is never registered. This is the (b) proof.

### 4.2 Byte-identity guards (must stay GREEN — the no-collision control)

Mirror `TestNoLabelArrayByteIdentity` (`test_cursor_label_lane.py:141-169`):
- **`\group`** label placed with **no** node under its natural corner → assert the
  `<rect>/<text>` markup is byte-identical to the pre-fix snapshot (the placer must be a
  no-op when the natural position is already clear).
- **`\note`** in an empty corner of a tall board → note `<rect>` byte-identical.
- **`\trace` stroke** touching no pill → the `<path d="…">` is byte-identical after (b)
  registration (registering an obstacle must never move the registrant).

### 4.3 Corpus regression gate

- After **Phase 1**: `pytest tests/golden/examples/` passes with **zero** re-bless
  (proves no corpus doc shifted — the group/note plumbing is inert on the corpus).
- After **Phase 2**: exactly `decoration_spiral.html` re-blesses; assert (a normalizer diff
  test) that the diff touches only `data-annotation="g.trace[…]"` label `<rect>/<text>`
  coordinates — grid cells, values, and trace `<path>` bytes unchanged.

---

## 5. Conclusion + Confidence

The remaining direct-emit surfaces split cleanly by mechanism, and the infrastructure to
fix them **already exists and is already threaded by the annotation control**: two entry
points (`emit_position_label_svg` / `_place_pill`), one obstacle type (`_Obstacle`), and
two resolvers (`resolve_self_content_rects`, `resolve_below_baseline`) that Array and Graph
already implement. The fix is not an engine rewrite — it is making four decorations call the
placer the annotation path already calls.

- **Phase-1 set (recommended): `\group` title + `\note`, both mechanism (a).** `\group` is
  zero-plumbing; `\note` builds the scene-obstacle pass that Phase 2 reuses.
- **Predicted golden shift: 0 corpus docs in Phase 1** (corpus has no `\group`/`\note`/`\link`);
  **1 corpus doc in Phase 2** (`decoration_spiral`, trace label only — stroke frozen).
  Geometry **moves**, but only the decoration's own pill; everything else is byte-identical.
- **SCRIBA_VERSION 21 → 22** on the output-shape-change principle; golden gate =
  "corpus byte-identical except co-located-decoration pills," not "0 geometry" and not
  "full re-bless."

**Confidence: HIGH** on the placer API inventory (every entry/resolver read this session
with `path:line`), on the four current collisions (source + rendered numeric bands,
re-measured at `11f8f62`), and on the golden-impact counts (direct corpus greps:
group=0, note=0, link=0, trace=1, cursor=1 `.html`). **HIGH** that the mechanism split
(a vs b) is correct — the stroke/bridge physically cannot dodge, confirmed by their
between-anchors geometry. **MED** on the exact size of Phase 2's `decoration_spiral` diff
(depends on whether the placer relocates that specific label — Deduced, not yet rendered
post-fix, since implementation is out of scope).
