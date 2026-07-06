# Audit — Direct-Emit Decoration / Obstacle-Bypass Class (Sibling of JudgeZone #7)

> BMAD sibling-audit (read-only on source; probes in scratch; only this doc written).
> Repo @ `main` `8988582`, scriba **0.26.4**, `SCRIBA_VERSION = 19`. Every `path:line` was
> read this session. Every **Confirmed** verdict is backed by source **and** a rendered
> geometry proof — server SVG rendered with `.venv/bin/python render.py <p>.tex -o _<p>.html`,
> element y/x-bands parsed numerically (baseline rules match `scriba-scene-primitives.css`:
> default `svg text` = `central` :400, `.scriba-index-label` = `hanging` :416). **No Playwright.**
>
> **The class (from JudgeZone #7, lead-confirmed):** a decoration that computes geometry from
> an anchor at a *fixed offset* and appends raw SVG to the output buffer, **without consulting
> the obstacle list that the smart-label pill placer uses** (`_place_pill` /
> `emit_position_label_svg`, fed `placed_labels` + `primitive_obstacles` of `_Obstacle`). The
> bound `\cursor` caret is the seed case; this audit enumerates **every other** such surface
> and numerically tests it for collision.

---

## 1. Hand-off Brief

**Counts.** 12 decoration surfaces audited → **10 direct-emit** (bypass the obstacle engine),
**1 emits no scene geometry** (`\ref`), **1 safe control** (annotation arrows/pills). Of the
10 direct-emit surfaces, **6 have a Confirmed rendered collision**, 3 are direct-emit + latent
(near-miss in the test layout, collision depends on selector geometry), 1 is by-design.

**Top findings (one-line each).**
- **The caret bug is not one bug — it is a primitive-family bug.** The same direct-emit caret
  (`base.py:653` `emit_cursors_under`) collides with the **Array index lane** (#7, id "i" over
  digit "2" by **6.5 px**, same column) **and** with the **NumberLine tick-label lane** (id "p"
  over tick "3" by **5.5 px**, same column) — and on NumberLine the triangle is additionally
  jammed **8 px into the tick marks**. Both HIGH (illegible-on-focus).
- **Three more decorations occlude content the same way:** `\group` title occludes ~16 px of a
  hull-corner node (MED); a corner `\note` occludes the lower half of the corner cell's value
  (MED); `\trace` runs dead-center through every cell-value glyph (MED, halo-mitigated).
- **The control proves the pattern:** in the *same frame* as a caret, a `position=below` pill on
  the *same cell* correctly dodges down into the callout lane (`below_baseline + 14`), clearing
  both the index digit and the caret — while the caret does not move. Same-cell, one dodges, one
  doesn't (`_c2.html`).
- **`\ref` has no dashed ring** — the mandate's premise is stale. `\ref` is a tint-only HTML
  `<span>` in narration; the ring is explicitly deferred (`ref_macro.py:23-25`). Nothing to collide.

**Caret-fix recommendation (per report #7 option 1/2).** Anchor the caret to the **bottom of the
below-label lane, not the cell bottom**, exactly as `position=below` pills already do. In
`emit_cursors_under` (`base.py:679`) replace the cell-bottom origin with
`max(cell_bottom, resolve_below_baseline())` before adding `_CURSOR_GAP`. `resolve_below_baseline()`
(`array.py:832`, `base.py:850`) already returns "the y below which below-pills clear the
index/caption stack" and is the exact anchor `emit_position_label_svg` uses (`_svg_helpers.py:3589`,
`below_baseline + _LABEL_LANE_GAP`). NumberLine needs the twin fix **plus** a `resolve_label_anchor`
override (see §4.2) because its caret math currently degenerates (center==top) and pushes the ▲
up into the ticks. The bounding-box reservation already exists (`_cursor_extent_below`,
`base.py:708`), so only the *placement origin* moves — no viewBox regression for the no-label case.

---

## 2. The obstacle engine (what "safe" means) — the baseline

The smart-label placer is `_place_pill` (`_svg_helpers.py:3372`): a weighted-scoring argmin over
candidate positions consuming a shared `placed_labels: list[_LabelPlacement]` and an
`extra_obstacles: tuple[_Obstacle, ...]`. The public entry `emit_position_label_svg`
(`_svg_helpers.py:3502`) routes **every** position pill through it (`:3607→3617`, passing
`placed_labels=placed_labels, extra_obstacles=primitive_obstacles`), with MUST/SHOULD severities
and a hard-block pass (`:747`). Two structural facts matter for this audit:

- **`position=below` pills are sent to a callout lane** past the whole index/caption stack:
  `final_y = below_baseline + _LABEL_LANE_GAP(14) + pill_h/2` (`_svg_helpers.py:3583-3589`). This
  is the lane the caret *should* be using and is not.
- **The control path threads the obstacle set** on every primitive: `emit_annotation_arrows`
  builds `_combined_obs` from primitive segments + own content cells + prior arrow strokes
  (`base.py:1186-1227`) and passes `placed_labels=placed, primitive_obstacles=…` into the plain
  arrow (`:1278-1285`), position pill (`:1363-1374`, with a **MUST** `target_cell` blocker at
  `:1351-1362`) and arc arrow (`:1398-1410`). This is the outlier-proving baseline.

A **direct-emit** decoration does none of this: it `parts.append("<polygon…>/<path…>/<rect…>/<line…>")`
with no `placed_labels`, no `_Obstacle`, no `_place_pill`, and — critically — never registers its
own geometry back into the obstacle set, so later placer-driven pills are blind to it too.

---

## 3. Decoration × routes-through-placer? × collision-found

| # | Decoration surface | Emit site (path:line) | Routes through placer? | Reserves a lane? | Collision found | Sev | Grade |
|---|---|---|---|---|---|---|---|
| 1 | **Bound `\cursor` caret** (▲ + id) | `base.py:686-705` (`emit_cursors_under`) | **No — direct** | bbox only (`_cursor_extent_below` :708) | **YES** — id over Array index digit | **HIGH** | Confirmed |
| 1b | same caret on **NumberLine** tick | `base.py:686-705` via `numberline.py:342` | **No — direct** | bbox only | **YES** — id over tick label + ▲ in ticks | **HIGH** | Confirmed |
| 1c | same caret, **multi-cursor** adjacent | `base.py:686-705` | **No — direct** | bbox only | No caret↔caret (52 px gap); each still hits own index | HIGH (per-cell) | Confirmed |
| 1d | caret vs **same-cell below-pill** | caret direct / pill via placer | pill: **yes**, caret: **no** | — | pill dodges, caret doesn't (asymmetry); pill leader clips id | MED | Confirmed |
| 2 | **`\trace` polyline** | `base.py:583-588` (`emit_traces_under`) | **No — direct** | no | **YES** — stroke dead-center of cell values | **MED** (halo-mitigated) | Confirmed |
| 3 | **`\trace` mid-label** pill | `base.py:601-625` | **No — direct** (grid-clamp only :611-615) | no | latent — near-miss over cell backgrounds | MED | Confirmed (latent) |
| 4 | **`\group` hull outline** | `graph.py:1693-1707` | **No — direct** | no (paints *under* nodes) | none — tint only, no occlusion | — | Confirmed safe-ish |
| 5 | **`\group` title label** | `graph.py:1708-1731` (flushed :2220) | **No — direct** | no | **YES** — occludes hull-corner node | **MED** | Confirmed |
| 6 | **`\link`/`\combine` bridge** | `_frame_renderer.py:967-990` (`_emit_scene_links`) | **No — direct**, top-of-z | no | latent — near-miss (over inter-shape lane) | MED | Confirmed (latent) |
| 7 | **bridge mid-label** | `_frame_renderer.py:972-981` | **No — direct** | no | latent — lands in a shape's index lane | MED | Confirmed (latent) |
| 8 | **`\note`** (8 compass anchors) | `_frame_renderer.py:1130-1141` (`_emit_scene_notes`) | **No — direct** | no (note↔note stacks :1090) | **YES** — occludes corner cell value | **MED** | Confirmed |
| 9 | **strike diagonal** | `base.py:1263-1273` | **No — direct** | no | crosses own value glyph **by design** | LOW | Confirmed (intended) |
| 10 | **R-35 block bracket** outline | `base.py:1313-1323` | **No — direct** (label→placer :1363) | no own lane | latent — outline abuts adjacent cell borders | LOW | Confirmed (latent) |
| 11 | **`\ref` dashed ring** | — (`ref_macro.py:130-140`, span only) | N/A — **no scene geometry** | N/A | none — ring deferred (:23-25) | — | Confirmed absent |
| 12 | **annotation arrows + pills** (CONTROL) | `base.py:1278-1410` → `_svg_helpers.py:3607` | **YES — placer** | via MUST/SHOULD obstacles | (dodges) | — | Confirmed safe |

Direct-emit surfaces = rows 1,1b,2,3,5,6,7,8,9,10 (**10**). `\group` hull outline (row 4) is
technically direct-emit but paints *under* content at fixed opacity 0.12 so it tints, never
occludes. `\ref` (row 11) emits no SVG. Control (row 12) is the safe baseline.

---

## 4. Confirmed collisions — numeric y/x-band overlap proof

All bands below are read from the rendered first frame (files in scratchpad `_c*.html`). Two
glyphs anchored at the **same x** with overlapping y-bands = superimposed = illegible.

### 4.1 Caret ▲+id vs Array index-label lane — the seed #7 — **HIGH**
`c1_caret_array.tex`: `Array size=5 labels="0..4"` + `\cursor{arr}{id=i, at=2}`. Cell 2 column **x=154**:

| element | source | y-band | x | overlap |
|---|---|---|---|---|
| cell value "30" | `array.py:569-581` central f14 | 13.0 – 27.0 | 154 | (in cell) |
| **index digit "2"** | `array.py:587-600` **hanging** f10 | **56.0 – 66.0** | 154 | — |
| **caret ▲** | `base.py:686-690` | **46.0 – 54.0** | 149–159 | **abuts 2 px above digit** |
| **caret id "i"** | `base.py:693-696` central f11 | **59.5 – 70.5** | 154 | **6.5 px over digit "2"** |
| primitive label | `base.py` central | 74.0 – 88.0 | 154 | — |

`caret id [59.5,70.5] ∩ index "2" [56,66] = [59.5,66] = 6.5 px`, identical x=154, and the caret
group is painted **after** the index labels (`array.py:587` then `:631`) so "i" occludes "2".
*Correction to #7's arithmetic:* the digit uses `dominant-baseline: hanging` (CSS :416), so its
true band is `[56,66]`, not the `[51,61]` a `central` assumption gives — the **id-over-digit**
overlap (6.5 px) is the dominant collision; the triangle sits 2 px clear above the hanging top
(it would touch a central digit). Illegibility is real either way.

### 4.2 Caret ▲+id vs NumberLine tick-label lane — same root cause, new primitive — **HIGH**
`c4_numberline_caret.tex`: `NumberLine domain=[0,6] ticks=7 labels="0..6"` + `\cursor{nl}{id=p, at=3}`.
Tick 3 column **x=200**:

| element | source | y-band | x | overlap |
|---|---|---|---|---|
| axis + tick line | `numberline.py` | 12.0 – 28.0 | 200 | — |
| **caret ▲** | `base.py:686-690` | **18.0 – 26.0** | 195–205 | **8 px inside the tick marks** |
| **caret id "p"** | `base.py:693-696` central f11 | **31.5 – 42.5** | 200 | **5.5 px over tick "3"** |
| **tick label "3"** | `numberline.py:300-312` central f10 | **37.0 – 47.0** | 200 | — |

`caret id [31.5,42.5] ∩ tick "3" [37,47] = [37,42.5] = 5.5 px`, same x=200. **Root cause of the
extra severity:** NumberLine does not override `resolve_label_anchor`, so `center == top ==
(x,12)` (tick top, `numberline.py:188`); the caret math `apex_y = center + (center−top) + gap =
12 + 0 + 6 = 18` (`base.py:679`) collapses — the ▲ lands *in* the ticks instead of below a row,
and the id lands in the number lane. Deduced-then-Confirmed by render.

### 4.3 `\group` title label vs hull-corner node — **MED**
`c7_group_hull.tex`: `Graph nodes=[1..5]` + `\group{g}{nodes=[1,2,3], label="component X"}`. Node 2
sits at the hull's top-left (`circle cx=20 cy=20 r=20` → y-band **[0,40]**). The group label pill
is placed at the hull bbox top-left with **no placer** (`graph.py:1715-1718`):

| element | source | y-band | x-band | overlap |
|---|---|---|---|---|
| node 2 circle | `graph.py` | 0.0 – 40.0 | 0 – 40 | — |
| node 2 value "2" | central f14 | 13.0 – 27.0 | 20 | — |
| **group label pill** | `graph.py:1708-1731` | **−2.6 – 16.4** | −1.2 – 85.8 | **16.4 px of the 40 px node occluded (top)** |
| group label text | `graph.py` | −0.1 – 13.9 | 42.3 | clips digit top 0.9 px |

The opaque-ish title pill covers the **top ~41 %** of node 2's circle (label pill `[−2.6,16.4] ∩
node [0,40] = 16.4 px`, x fully inside). Painted **over** nodes (flushed `:2220`, after nodes close
`:2216`). Confirmed.

### 4.4 Corner `\note` vs corner cell value — **MED**
`c9_note_corner.tex`: `Array size=5 labels="0..4"` + two `\note{…}{at=top-right}`. Array at scene
`translate(12,12)` (`_c9.html`); notes at scene-root viewBox coords (viewBox `0 0 332 111`; note n1
x = vx+vw−8−pw = 332−8−73 = **251** ✓). Top-right cell 4 value "50" in **scene** coords =
`(278+12, 13+12..27+12)` = **x 290, y 25–39**:

| element | source | y-band (scene) | x-band | overlap w/ "50" [25,39] |
|---|---|---|---|---|
| **note n1 "0-indexed"** | `_frame_renderer.py:1130-1141` | **8.0 – 27.0** | 251 – 324 | **2 px** (digit top); x290 ∈ band |
| **note n2 "second"** (stacked) | same, `stack_index=1` | **31.0 – 50.0** | 271 – 324 | **8 px** (lower half of digit) |

Note n2 occludes the **lower ~half** of cell 4's value "50" (`[31,50] ∩ [25,39] = 8 px`, x290 in
`[271,324]`), fill `white` opacity 0.92 → effectively opaque. **Note↔note stacking works** (n1
`[8,27]`, n2 `[31,50]`, gap = `_NOTE_STACK_GAP` 4 px, `:1090-1091,:1028-1032`) — but the stack
marches *down over successive content*, and nothing reserves the corner (documented:
`design-decorate.md:283` "overlap-with-content … no reservation in v1"). Confirmed.

### 4.5 `\trace` polyline vs cell-value glyphs — **MED (halo-mitigated)**
`c5_trace_array.tex`: `Array labels="0..4"` + `\trace{arr}{cells=[0,1,2,3,4]}`. Trace path (raw) =
`M30,20 L92,20 L154,20 L216,20 L278,20` — a horizontal stroke at **y=20**, i.e. the exact center
of every value glyph (`resolve_label_anchor` → cell center, `array.py:746-759`). Stroke width 2.5 →
band `[18.75,21.25]` ∩ value "30" `[13,27]` = **2.5 px dead-center**. Only the CSS paint-order halo
(`paint-order: stroke fill`) keeps digits legible; the trace geometry still crosses them and is
never registered as an obstacle, so later placer pills are blind to it. On a 1-D Array the trace
does **not** reach the index lane (y=20 vs 56). Confirmed.

### 4.6 strike diagonal vs own value glyph — **LOW (by design)**
`c10_strike.tex`: `\annotate{arr}{strike=true}` → one `<line>` `(2,0)→(310,40)` (`base.py:1263-1273`).
At the center column x=156 the line is at y≈20, crossing value "30" `[13,27]` through its middle;
it passes *above* left values and *below* right values, and stops at y=40 so the index lane
`[56,66]` is spared. Crossing the struck box's own glyph is the intended "strike-but-keep" gesture
(`base.py:1229-1234`). Confirmed intended; flagged only because a whole-shape strike is direct-emit
and unregistered (a later same-annotation pill won't dodge it).

### 4.7 Latent (direct-emit, near-miss in test layout)
- **`\link`/`\combine` bridge + mid-label** (`c8`): bridge `M104,12 Q122,72 166,119` (scene) between
  two vertically-stacked arrays; mid-label "map" at scene `(128.6, 62–76)` lands **in array A's
  index-label lane band** (scene y 68–78) but horizontally *between* two digits — a near-miss that
  becomes a hit for a different cell pair. Top-of-z over everything (`_frame_renderer.py:1520-1523`).
- **`\trace` mid-label** (`c6`): pill `[x72.5,111.5]×[y35,54]` sits 1 px above cell (1,1)'s value
  `[55,69]` and over the row-0/row-1 backgrounds; horizontal grid-clamp only (`base.py:611-615`).
- **R-35 block bracket** (`c11`): `Grid` + `bracket=true` → dashed rect `x[−3,125] y[−3,85]`, +3 px
  outset that lands the right/bottom edges **exactly on the border shared with adjacent cols/rows**
  (col 2 left edge = 125, row 2 top = 85). Cosmetic ambiguity, not illegibility.

---

## 5. Structural-fix recommendation

**Diagnosis.** Every row-1..10 surface computes a position from an anchor + fixed constant and
appends raw SVG. The obstacle engine that already exists for pills is simply never invoked. Two
remediation shapes:

**(A) Shared obstacle list (recommended as the end state).** Make every direct-emit decoration a
first-class citizen of the one obstacle set the placer already threads: (i) its *text* parts
(caret id, trace label, group title, bridge label, note body) go through `_place_pill` /
`emit_position_label_svg` so they *dodge* existing content, and (ii) its *geometry* is pushed as an
`_Obstacle` into the shared `placed_labels` / `primitive_obstacles` so later pills dodge *it*. This
scales: N decorations pack into whatever whitespace exists instead of each demanding a reserved band.
It is the same move that already tamed pill-vs-pill and pill-vs-segment collisions (`_svg_helpers.py`
W3-α+). Cost: the scene-level emitters (`_emit_scene_links`, `_emit_scene_notes`) run *after*
primitives at scene-assembly (`_frame_renderer.py:1520`), so they would need the per-primitive
`placed`/obstacle sets lifted to scene scope, or a second scene-level placement pass.

**(B) Per-decoration lane reservation.** Give each its own reserved band (like the below-pill
callout lane or `arrow_above`). Simpler locally, but lanes multiply and waste vertical space, and it
does nothing for *cross*-decoration collisions (caret-vs-note, bridge-vs-pill).

**Recommended split:** ship **(A)** as the structural target, but land the **caret** with the
**per-lane (B) move now** because it is a one-line origin change reusing infra that already exists:

> **Caret fix (report #7 option 1/2), Confirmed mechanism.** In `emit_cursors_under`
> (`base.py:679`), change the apex origin from the cell bottom to the below-lane bottom:
> ```
> lane = self.resolve_below_baseline()          # array.py:832 / base.py:850  (None → no lane)
> origin = center[1] + (center[1] - top[1])      # existing cell-bottom
> if lane is not None: origin = max(origin, lane) # clear the index/tick/caption stack
> apex_y = origin + _CURSOR_GAP
> ```
> This is exactly what `emit_position_label_svg` does for `position=below`
> (`_svg_helpers.py:3583-3589`, `below_baseline + _LABEL_LANE_GAP`), so the caret joins the same lane
> the below-pill in §4.1d already dodges into — no new machinery. `_cursor_extent_below`
> (`base.py:708`) already grows the bbox from the same resolvers, so the viewBox stays correct and
> the no-label frame is byte-identical (`resolve_below_baseline()` → `None`). **NumberLine also needs
> a `resolve_label_anchor` override** returning the tick center below the number lane, else the
> degenerate `center==top` (§4.2) keeps the ▲ in the ticks even after the origin move.

---

## 6. Conclusion + Confidence

The JudgeZone #7 caret collision is one instance of a **10-surface class**: decorations that draw
geometry at a fixed offset and never touch the obstacle engine the pill placer uses. Six collide in
a rendered frame; two of those (the caret on Array **and** on NumberLine) are HIGH illegible-on-focus
and share one root cause and one fix. The control (annotation pills) and the same-frame below-pill
dodge (§4.1d) prove these are outliers, not the norm. The clean structural target is a **shared
obstacle list** (A); the caret should land immediately via the **below-lane origin** move (B),
because that infra already exists and `_cursor_extent_below` already reserves the space.

**Confidence: HIGH** on the six Confirmed collisions (source `path:line` + rendered numeric bands,
same coordinate system for 1/1b/2/5/9; scene-transform-composed for 8; graph-local for 5). **HIGH**
on routing verdicts (grepped absence of `_place_pill`/`placed_labels`/`_Obstacle` in each emit
site). **MED** on the three latent rows (direct-emit is Confirmed; the *specific* overlap is
layout-dependent and shown as a near-miss, not forced). **HIGH** that `\ref` emits no ring
(`ref_macro.py:23-25`).

---

## 7. Raw data (rendered geometry, scratchpad `_c*.html`)

Probe: `scratchpad/probe.py <file.html> [xlo xhi]` — parses `<text>/<polygon>/<line>/<rect>` and
computes y-bands via the CSS baseline rules. Stress cases `scratchpad/c*_*.tex`.

```
CASE 1  caret vs Array index  (_c1.html, x=154)
  text  "30"  central f14   y 13.0–27.0   x154         (cell value)
  text  "2"   hanging f10    y 56.0–66.0   x154         (index digit)
  poly  ▲                    y 46.0–54.0   x149–159     (caret triangle)
  text  "i"   central f11    y 59.5–70.5   x154         (caret id)   → id ∩ digit = 6.5px

CASE 1b caret vs NumberLine tick  (_c4.html, x=200)
  poly  ▲                    y 18.0–26.0   x195–205     (in ticks 12–28)
  text  "p"   central f11    y 31.5–42.5   x200         (caret id)
  text  "3"   central f10    y 37.0–47.0   x200         (tick label) → id ∩ label = 5.5px

CASE 1d caret + same-cell below-pill  (_c2.html, x=154)
  text  "2"   hanging f10    y 56.0–66.0   x154         (index digit)
  text  "i"   central f11    y 59.5–70.5   x154         (caret id, UNMOVED → still 6.5px on digit)
  line  leader               y 66.0–76.0   x154         (pill leader clips id bottom 66–70.5)
  text  "below pill"         y 80.2–91.2   x154         (pill DODGED to callout lane — safe)

CASE 2  trace vs cell values  (_c5.html)
  path  M30,20 L…278,20      stroke y 18.75–21.25       (dead-center of value band 13–27)

CASE 3  group label vs node2  (_c7.html)
  circle node2  cx20 cy20 r20  y 0–40                    (node)
  rect  group-label pill      y −2.6–16.4  x−1.2–85.8    (occludes 16.4px of node top)
  text  "component X"         y −0.1–13.9  x42.3

CASE 4  note vs corner cell  (_c9.html, scene coords; array @ translate(12,12))
  cell4 "50" scene           y 25–39      x290           (corner value)
  note  n1 "0-indexed"       y 8–27       x251–324       (2px on digit top)
  note  n2 "second"          y 31–50      x271–324       (8px on digit lower half)

CASE 5  strike vs values  (_c10.html)
  line  (2,0)→(310,40)       at x156 → y≈20              (crosses center value "30" 13–27, by design)

CASE 6  block bracket  (_c11.html, Grid)
  rect  bracket dashed       x−3–125  y−3–85             (edges land on adjacent col2/row2 borders)
```
