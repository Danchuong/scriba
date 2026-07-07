# Hunt 2 — Cross-primitive composition (`\link` · `\focus` · `\zoom` · `\group` · board · RTL/CJK)

> BMAD render-quality hunt, round 2. Read-only source; scenes rendered server-side, geometry
> computed from the per-step `frames=[{svg:…}]` island (no browser). Repo @ `main` `0e8e09f` (0.28.0).
>
> Evidence grades: **[Confirmed]** = read in source this session (path:line) **and** a rendered
> number from the emitted SVG · **[Deduced]** = logical consequence of a confirmed fact ·
> **[Hypothesized]** = design claim, not built.
>
> Toolkit: `scratchpad/hunt2-crossprim/geom.py` — transform-aware SVG walker (composes nested
> `translate`/`scale`/`matrix`), `target_bbox`, `path_points`, point-in-polygon, overlap. Validated
> against the shipped c8 bridge (reproduced its `M104,12 Q122.2,72.9 166,119` path byte-for-byte).

---

## 1. Hand-off Brief (compressed conclusion)

Six scenes exercised the cross-shape verbs plus a multilingual set. **Three confirmed defects, all
in-slice; five feature areas clean.**

- **D1 — scene link/`\combine` labels float OFF the top of the canvas** instead of clamping to the
  board. The mid-bridge label placer is handed a `_SCENE_LABEL_VB = 8192` sentinel viewport
  (`_frame_renderer.py:1196`, used at `:1339-1342`) so it never clamps to the real board; when the
  natural label seat overlaps the bridged shapes it escapes *upward past y=0*. Two independent
  reproductions clip **10.5px** (side-by-side board) and **11.0px** (vertical crossing bridges) of a
  ~19px pill. **[Confirmed]** MEDIUM-HIGH.
- **D2 — `\focus` silently fails to dim Tree and Forest *nodes*** (edges dim, nodes do not). Root:
  the defocus regex `_DEFOCUS_G_RE` (`_frame_renderer.py:1065`) requires `class=` *immediately*
  after `data-target=`, but Tree (`tree.py:1033`) and Forest (`forest.py:597`) interpose
  `data-node-x`/`data-node-y`. **0/5 tree nodes, 0/5 forest nodes** ever get `scriba-defocused`,
  in every focus mode (own-complement *and* `scope=board` backgrounding). Graph/Array/Grid/Matrix/
  Queue/LinkedList dim correctly (contrast). **[Confirmed]** HIGH.
- **D3 — RTL bidi missing on every stage/decoration pill** (link label, `\note`, `\group` hull
  label, single-line `\annotate`). `_frame_renderer.py` has **zero** `_bidi_style` references and
  `_emit_label_single_line` (`_svg_helpers.py:1690-1704`) omits it (its multi-line sibling at `:1621`
  applies it). **4 of 5** Arabic `<text>` surfaces render bidi-naked; the exact string the
  `_bidi_style` docstring says "mis-mirrors and scrambles" (`نتيجة (result) = 42`) reaches them
  unstyled. Cells and shape captions are fine. **[Confirmed]** HIGH for RTL editorials.

**Clean:** `\zoom` (uniform 9px pad, no clip, byte-identical restore, note pins inside crop);
`\group` hull (exact enclosure, overlapping groups, group+link, 0.26.5 corner-node fix holds);
board composition (envelope top-alignment, wide-over-narrow centering, sparse→dense byte-identical
compaction, nothing off-canvas); `\focus` viewBox stability + byte-identical restore; RTL/CJK **in
cells** (bidi applied, content-sized, no clip).

---

## 2. Defect table

| # | Scene | Feature / verb | Defect | Number | Severity |
|---|-------|----------------|--------|--------|----------|
| D1a | side-by-side board, `\link{a.cell[3] <-> b.cell[0]}{label="near edge?"}` | bridge label placement | wide label escapes above board top | label y=**-1.0**, pill top y=**-10.5**, clipped **10.5px** above viewBox y=0 | MED-HIGH |
| D1b | vertical stack, two crossing `\link` labels | bridge label placement | 2nd label shoved off top | `RIGHT-map` y=**-1.5**, clipped **11.0px** above viewBox y=0 (vb `[0,0,270,166]`) | MED-HIGH |
| D2a | `\focus{t.node[2]}` (Tree, isolated) | focus complement dim | sibling nodes not dimmed | **0/5** nodes dim; **4/4** edges dim | HIGH |
| D2b | `\focus{f.node[1]}` (Forest) | focus complement dim | nodes not dimmed | **0/5** nodes dim; 2/2 edges dim | HIGH |
| D2c | `\focus{a.cell[0]}{scope=board}` w/ Tree as other shape | focus board-dim | backgrounded tree stays lit | **0/4** tree nodes dim on a "dark" board | HIGH |
| D3 | `\link`/`\note`/`\group`/`\annotate` labels w/ Arabic | RTL bidi | missing `unicode-bidi:plaintext` → RTL+Latin scramble | **4/5** Arabic `<text>` surfaces bidi-naked | HIGH (RTL) |

---

## 3. Bridge findings (`\link` / `\combine`)

**Anchor model [Confirmed].** Each endpoint resolves via the owning primitive's
`resolve_annotation_point` (`_frame_renderer.py:1167-1190`) — the *annotation* anchor (top-centre of
a cell), **not** a facing-edge choice. A single perpendicular sag (`_LINK_SAG_*`, `:1162-1164`) bows
the quadratic. Consequence: for two vertically-stacked arrays the bridge anchors **top-to-top** and
the leader re-enters the source cell's own box (c8: sampled point `(107.9, 24)` lies inside
`a.cell[1]` `[75,133]×[13,51]`). Defensible (reuses the annotation resolver, 0 new coordinate
system) but not edge-aware — noted, not filed as a defect on its own.

**D1 — label off-canvas [Confirmed].** The real defect is the *label placer*, not the path. Natural
mid-curve seat is `0.25·P0 + 0.5·C + 0.25·P1`; when it overlaps the bridged shapes the placer
(`_place_pill`) is given `viewbox_min_y = -8192 … 8192` (`_SCENE_LABEL_VB`, `:1339-1342`) so its
displacement scorer picks the *nearest clear* seat with no board clamp. On a side-by-side board the
nearest clear seat is **above** the cells → `y=-1.0` (pill top `-10.5`, board top `0`), 10.5px
clipped (SVG `overflow:hidden` cuts it). Reproduced again independently in a vertical crossing-bridge
scene (`y=-1.5`, 11px). Had the placer used the real viewBox it would have taken the on-canvas seat
*below* the cells (board height 111 / 166 had room). Hits explicit `\link{…}{label=…}` on any
horizontal board (the canonical dot-product / Euler-tour layout) and any multi-bridge frame.

**Multiple bridges [Confirmed clean-ish].** Crossing is *not* avoided (simple arcs) — two bridges
`a[0]↔b[3]` and `a[3]↔b[0]` cross near `(103,49)`, which is expected/acceptable. Anti-collision on
the *labels* works (pill-overlap 0px²) — but it achieves separation partly by the D1 off-canvas
escape, so the two are coupled.

**`\combine` [Confirmed].** Canonical matrix-multiply `\combine{m.row[0], n.col[0]}{into=
"c.cell[0][0]"}` across three side-by-side matrices: both bridges converge exactly on the target
top-centre `(212,24)`; row anchor at row mid-height, col anchor at col edge. Works; the doc example
carries no label so it dodges D1, but an authored `label=` on a horizontal combine would hit it.

---

## 4. Focus / Zoom / Group findings

**`\focus` — D2 [Confirmed].** `_apply_defocus` (`_frame_renderer.py:1086-1153`) rewrites
`<g data-target="X" class="Y"` → adds `scriba-defocused`, driven by
`_DEFOCUS_G_RE = <g data-target="([^"]+)" class="([^"]*)"` (`:1065`). That regex demands `class=`
**adjacent** to `data-target=`. Emit-order census:

| Primitive | complement targets | dimmed | verdict |
|---|---|---|---|
| Array / Grid / Matrix / Queue / LinkedList / **Graph** | n | n | OK |
| **Tree** | 8 (4 node + 4 edge) | 4 (edges only) | **nodes miss** |
| **Forest** | node+edge | edges only | **nodes miss** |

Only Tree (`tree.py:1033`) and Forest (`forest.py:597`) emit
`<g data-target="…" data-node-x="…" data-node-y="…" class="…">` — the interposed attrs defeat the
regex, so **no** tree/forest node ever dims, in any mode (own-complement, and `scope=board` where the
tree is a backgrounded other shape: 0/4 dimmed). Because edges *do* dim, the frame looks "half
working" and an author is unlikely to notice the spotlight failed. viewBox is stable across
focus/restore and restore is **byte-identical** to the pre-focus frame — that part is clean.

**`\zoom` — clean [Confirmed].** `\zoom{a.cell[5]}`: crop viewBox `[314,4,76,56]`, target bbox
`[323,13,381,51]`, clip L/R/T/B = **0/0/0/0**, padding a uniform **9/9/9/9px**; next step restores to
the exact full-board viewBox. Neighbours are cropped at the edge (expected). Zoom + corner `\note`:
the note lands at `(52.5,13.5)` **inside** the cropped viewBox `[4,4,76,56]` — the documented
"pin note inside the magnified frame" behaviour holds.

**`\group` hull — clean [Confirmed].** (Coordinate note: hull `<path>` is emitted *inside* the
graph's `translate` group, so raw path bytes are local; my first pass mis-compared local hull to
global nodes and produced false "not enclosed" flags — corrected by routing the path through the
transform-aware parser.)
- **G1 exact enclosure:** group `{1,2,3}` — nodes 1,2,3 centres inside hull, nodes 4,5 outside. Exact.
- **G2 overlapping groups** sharing node 3: node 3 inside **both** hulls; labels `Left(279,254)` /
  `Right(140,143)` 177.6px apart (no collision).
- **G3 group + link** on the same graph both emit and coexist.
- **G4 title vs corner node** (0.26.5 fix): label clears all nodes, no viewBox clip. **Holds.**

---

## 5. Board composition findings — clean [Confirmed]

- **Envelope top-alignment:** row-0 shapes `a/g/m` all at group `translate-y = 12.0`. Content-top
  differences (graph's first node 19px lower) are *internal* padding, not a board bug.
- **Wide over narrow:** size-10 array over size-2 array — both column-**centred** to Δcx = **0.0**;
  neither off-canvas.
- **Sparse compaction (spec line 373):** `at=[0,0]+at=[5,7]` vs `at=[0,0]+at=[1,1]` — same viewBox
  `288×124` **and** the shape-b group is at `translate(154,72)` in both; with a shared id the two
  SVGs are **byte-identical**. Claim holds exactly.
- **2×3 mixed board (Array+Graph+Matrix+Tree+Queue+Stack):** nothing off-canvas; heterogeneous
  inter-shape edge-gaps (a|g=216 vs g|m=111.5) are the expected result of per-column centring of
  different-width shapes, not a spacing defect.

---

## 6. Multilingual / RTL findings

**Design [Confirmed].** RTL uses `unicode-bidi:plaintext` (`_text_render.py:41-51`) so the UA
resolves base direction from the first strong char (UAX#9); the docstring names the exact failure
without it — `نتيجة (result) = 42` "mis-mirrors and scrambles". Complex-script width is a **safe
over-estimate** (`_text_metrics.py:44-140`, W1301) — never clips, may over-pad.

**D3 — bidi coverage gap [Confirmed].** One scene with Arabic on every pill surface; count of
`<text>` carrying `unicode-bidi:plaintext`:

| Surface | bidi? | emit site |
|---|---|---|
| shape caption `scriba-primitive-label` | **yes** | `_svg_helpers.py:1621` |
| `\annotate` pill (single-line) | **no** | `_svg_helpers.py:1690-1704` (`_emit_label_single_line`) |
| `\link` / `\combine` bridge label | **no** | `_frame_renderer.py:1347-1350` |
| `\group` hull label | **no** | `graph.py` group-label emit |
| `\note` callout pill | **no** | `_frame_renderer.py:1538 / 1552` |

`_frame_renderer.py` has **0** `_bidi_style` refs, so every stage pill it emits is naked; the
annotation path is *inconsistent* (multi-line applies it at `:1621`, single-line at `:1690` does
not). Total `unicode-bidi:plaintext` in the frame = **1** of 5 Arabic surfaces. Pure-RTL strings
(e.g. a bare `نتيجة` group label) survive by luck (a lone RTL run reverses correctly under an LTR
base); **mixed RTL+Latin+digits** — the realistic editorial pill — scrambles.

**Bounded [Confirmed].** RTL/CJK **inside cells** is fine: `a.cell` with `نتيجة` carries bidi=yes;
a CJK cell `结果长文字` content-sizes to 80px (≈70px text) with no clip and needs no bidi (LTR-run).
So D3 is strictly the stage/decoration pill layer.

---

## 7. Conclusion + Confidence

Cross-primitive composition is structurally sound — anchors resolve, hulls enclose, zoom crops and
restores, boards pack and compact per spec. The three defects are **peripheral-layer** bugs (label
placement, a dim-regex, a bidi-style omission) rather than coordinate-system failures, and each has a
single narrow root cause:

- **D1** `_SCENE_LABEL_VB=8192` → clamp the placer to the real viewBox (or bias the escape downward).
- **D2** `_DEFOCUS_G_RE` too strict → allow attrs between `data-target` and `class`
  (`<g data-target="([^"]+)"[^>]*?class="([^"]*)"`), or re-emit the class adjacent for Tree/Forest.
- **D3** thread `_bidi_style` through the four `_frame_renderer.py` / `_emit_label_single_line` pill
  emits.

**Confidence: HIGH** for D2 and D3 (each read at the emit site *and* reproduced with rendered SVG
counts; D2's Graph-vs-Tree contrast and D3's 4/5 count are unambiguous). **HIGH** for D1's numbers,
**MEDIUM** on its severity label (the pill is ~55% clipped but still partly visible; readability, not
data-loss). Clean verdicts (zoom, group, board, focus-restore, in-cell RTL/CJK) are each backed by a
rendered geometric assertion, not inspection alone.

**Not exhausted:** smooth-zoom is out of v1 by design (not tested); `\combine` label pass-through
(does the grammar accept `label=`? — I confirmed explicit `\link` labels clip, did not confirm
combine forwards a label); Indic/Thai/Khmer shaping correctness beyond width (the over-estimate only
guarantees no-clip, not correct glyph shaping — same pill-bidi gap would apply).
