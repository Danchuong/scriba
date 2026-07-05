# Investigation: Teaching Marker Verbs

## Hand-off Brief

A CP teacher's atomic marker gestures map almost entirely onto shipped scriba commands — 8 of 10
verbs are Covered by first-class surfaces (`\cursor`/`\focus`/`\highlight`, `\annotate arrow_from`,
`\link`, `\recolor`'s 9 states, `\group` hull, `\trace`, `value_change`, `element_add/remove`), each
with a rendering fixture in `tests/doc_coverage/corpus/`. The one hard **MISSING** verb is
**cross-out / strike / prune**: there is no strike-through visual anywhere — not in the 9 `VALID_STATES`,
not in the closed 11-kind motion registry, not in the scene CSS — so a teacher can *dim*, *redden*, or
*vanish* a discarded candidate but can never show it **struck-yet-still-on-the-board**, the exact
gesture used to say "we considered this and rejected it." The one **AWKWARD** verb is
trace-a-path over **graph/tree edges** (`\trace` is grid-only, E1118), which forces a per-edge
`recolor→path` or cursor-slide workaround.

## Case Info

- **Slice:** Marker verbs — the moment-to-moment gestures a teacher makes with the marker.
- **Method:** Read-only. Evidence-graded (Confirmed / Deduced / Hypothesized). Stronghold-first.
- **Strongholds:** `VALID_STATES` (9 states), the closed 11-kind runtime registry, the per-command
  `tests/doc_coverage/corpus/` roster, and two rendered probes.
- **Harness:** `.venv/bin/python render.py <probe>.tex -o <probe>.html` (render.py sandboxes output to cwd).

## Coverage Table

| Verb | Verdict | scriba surface (path:line) or the gap |
|---|---|---|
| **point-at** ("this element") | Covered | `\cursor` pin/hop §5.11 `docs/SCRIBA-TEX-REFERENCE.md:566`; `\highlight` §5.6 `:431`; `\focus` spotlight §5.16 `:720`. Fixtures `cmd_cursor_single`, `cmd_highlight_ephemeral`, `focus_spotlight`. |
| **trace-a-path** (follow edges / sweep) | **Awkward** | `\trace{shape}{cells=[...]}` self-drawing arrow §5.9 `:521` — but **cell/tick grids only** (Array/Grid/DPTable/NumberLine); any other primitive raises **E1118** `:525-527`. Graph/tree edge-following (the canonical BFS/DFS gesture) has **no first-class trace**; approximated by recoloring edges to `path` per step or sliding a `\cursor` pin. |
| **circle / box a region** | Covered | `\group{G}{nodes=[...]}` rounded hull §5.20 `:842` (**Graph only**); `\annotate{block}{bracket=true}` dashed outline §5.8 `:448`, §8 `:1499` (Grid/DPTable-2D/Matrix). Rendered `cmd_group_hull` → 9 hull `<path>`. Caveat: no fence for a 1-D Array `range` (bracket is block/2-D only). |
| **cross-out / strike / PRUNE** | **MISSING** | No strike state in `VALID_STATES` `scriba/animation/constants.py:27-30`; no strike/cross-out kind in the 11-kind registry `scriba/animation/static/scriba.js:152-324`; no `scriba-state-strike`/`.strike` in scene CSS. `\recolor{x}{state=strike}` → **E1109** (rendered). Only `line-through` in source is a **prose** disabled-link `scriba/tex/static/scriba-tex-content.css:461`, unusable in a scene. |
| **underline / emphasize a value** | Covered | `\highlight` ephemeral outline §5.6; `\focus` (`scriba-defocused` complement) §5.16 `:736`; emphasis channel A-3 `.scriba-emphasis` `docs/spec/motion-ruleset.md:82-101`. Caveat: literal **underline** is prose-only (`latex_fmt_underline`), not a scene gesture. |
| **draw an arrow BETWEEN two things** | Covered | `\annotate{tgt}{arrow_from="src"}` Bezier arc §5.8 `:451,:476`; `\link{A <-> B}` cross-shape bridge §5.19 `:816`; `\combine` converging arrows; `arrow=true` bare pointer. Fixtures `annot_annotate_arrow_from`, `cmd_link_bridge`. |
| **running side-note / live variable** | Covered | `\annotate{tgt}{label="i=3"}` pill §5.8 `:444`; `\invariant{text}` pinned panel §5.17 `:743`; `VariableWatch` `.var[name]` widget §7.15 `:1386`; per-frame `\narrate` §5.4. Fixtures `annot_annotate_label`, `invariant_panel`, `latex_sel_var`. |
| **tally / counter** (visible increment) | Covered | `value_change` kind `scriba/animation/static/scriba.js:160`; Array `\apply{cell}{value=N}` (rendered `prim_tbl_array_anim_value`, `value_change` present); `VariableWatch`; `Bar` magnitude §7.19. Caveat: no self-incrementing counter — author sets each value per `\step`. |
| **color-code by role** (unvisited/frontier/visited/done) | Covered | `\recolor{tgt}{state=X}`, 9 states §5.7 `:434`, §6 `:868`. All 9 fixtures `cmd_recolor_state_{idle,current,done,dim,error,good,highlight,path,hidden}`. Role map: `idle`=unvisited, `current`=frontier, `done`=visited, `path`/`good`=solution, `error`=invalid, `dim`=irrelevant, `hidden`=gone. |
| **erase-and-redraw** (mutate structure in place) | Covered | `element_add`/`element_remove` `scriba.js:191,198`, `position_move` `:217`, reparent. Graph/Tree `add_node`/`remove_node`(cascade)/`reparent` (`prim_graph_tree_*`, rendered `remove_node_cascade`); LinkedList insert/remove; Array reorder. Motion falls out of the identity diff, A-1 `docs/spec/motion-ruleset.md:42`. |

**Counts: 8 Covered · 1 Awkward · 1 Missing.**

## Confirmed Gaps

### GAP-1 (MISSING) — No cross-out / strike / prune gesture

**Evidence (all Confirmed):**
- `VALID_STATES = {idle, current, done, dim, error, good, highlight, path, hidden}` — `scriba/animation/constants.py:27-30`; enforced at parse `scriba/animation/parser/_grammar_commands.py:160`.
- Closed 11-kind runtime registry — `scriba/animation/static/scriba.js:152-324`: `recolor, value_change, highlight_on, highlight_off, element_remove, element_add, position_move, annotation_remove, annotation_add, annotation_recolor, cursor_move`. No strike/cross-out kind. Closure is a MUST (A-2, `docs/spec/motion-ruleset.md:59-74`).
- No `scriba-state-strike`/`.strike`/`line-through` in scene CSS (`scriba/animation/static/*.css`). The sole `line-through` in the repo is a **prose** disabled-hyperlink rule (`scriba/tex/static/scriba-tex-content.css:461`) — not addressable inside `\begin{animation}`.
- **Rendered probe** `prune_strike.tex` (`\recolor{T.node[B]}{state=strike}`) → `error [E1109] at line 6: unknown recolor state 'strike'; valid: current, dim, done, error, good, hidden, highlight, idle, path`.
- **Rendered probe** `prune_substitute.tex` → ok: the only expressible "prune" is `recolor` to `error` (red) / `dim` (faded) / `hidden` (invisible) — pure CSS class swaps, no mark drawn.

**What the teacher can't do:** show a candidate **struck through yet still visible** — the "crossed-out but on the board" state that records a considered-and-rejected branch (pruned recursion, discarded greedy choice, eliminated candidate) *while keeping it readable next to the survivors*. scriba forces a binary: keep it and only recolor it (`dim`/`error` — reads as "bad/faded", not "eliminated"), or remove it entirely (`hidden`/`remove_node` — the reasoning vanishes with it). No primitive draws a free diagonal/X over an element: `\trace` is grid-only and arrowheaded, `\annotate arrow_from`/`\link` need a source+target and draw arrows, and Plane2D `segment` lives in math-coordinates, not as an overlay on another shape's node.

### GAP-2 (AWKWARD) — No first-class path-trace over graph/tree edges

**Evidence (Confirmed):** `\trace` supports **cell/tick grids only**; on Graph/Tree/etc. it raises **E1118** — `docs/SCRIBA-TEX-REFERENCE.md:525-527`.

**What's awkward:** the single most common CP teaching sweep — "follow the edges" in a BFS/DFS traversal — has no dedicated verb. The author approximates it by recoloring each edge to `state=path` step-by-step, or sliding a `\cursor` pin node-to-node. Expressible, but hand-rolled per edge rather than one `\trace` call.

### Secondary caveats (not standalone gaps)
- **Box a 1-D Array range:** no fence primitive — `bracket` is block/2-D-only, `\group` is Graph-only. A window over `a.range[i:j]` can only be color-filled (`recolor`), not outlined.
- **Literal underline in-scene:** underline is a prose command (`\underline`), not a scene marker gesture; in-scene emphasis is outline/pulse/spotlight, not an underline stroke.
- **Auto-incrementing counter:** `value_change` animates a value the author sets each step; there is no self-ticking tally badge.

## Conclusion

scriba reproduces the teacher's marker vocabulary well: **8 of 10 verbs Covered** by first-class,
render-proven commands, **1 Awkward** (graph edge-trace), **1 Missing** (cross-out/prune). The premise
"scriba đáp ứng được" holds for the pointing/boxing/arrowing/labeling/coloring/mutating gestures, but
**fails cleanly for the prune gesture** — a real, high-frequency CP-teaching move (invalidating a
discarded branch while keeping it visible) that has no visual surface at all.

**Confidence: High.** GAP-1 is proven by four independent Confirmed sources plus a rendered E1109;
GAP-2 by an explicit documented error path. Coverage claims are each backed by a `doc_coverage/corpus`
fixture and, for the load-bearing cases, a local render.

## Reproduction / Verification

- Gap (rendered): `\recolor{X}{state=strike}` → E1109 (`unknown recolor state`); no valid state, kind, or CSS class draws a strike. Substitute limited to `recolor`→`error/dim/hidden`.
- Covered (rendered): `tests/doc_coverage/corpus/cmd_group_hull.tex` (hull), `prim_tbl_array_anim_value.tex` (value_change) both render ok.
- Probes: `scratchpad/prune_strike.tex`, `scratchpad/prune_substitute.tex`.

**Status: Concluded.**
