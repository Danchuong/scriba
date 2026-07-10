# Investigation: JudgeZone #12 — bound `\cursor` caret collides with a shape's `label=` caption

## Hand-off Brief

1. **What happened.** (Confirmed) On an `Array` carrying both `labels=` (index row) and `label=` (caption), a bound `\cursor` caret overlaps the caption exactly as reported — and the bug is **broader** than the report assumed. It is not gated on `labels=` at all: removing the index row (Control B) does not fix it, because the caret and the caption both anchor to the *same* shared value (`resolve_below_baseline()`), and neither knows the other exists. The 0.26.4 fix for report #7 taught the caret to clear the index-label row; it never taught the caption to clear the caret, and the caption's own placement code was written (with an explicit "index row → callout lane → caption" comment) around a three-tenant model that structurally excludes the caret.
2. **Where the case stands.** Concluded (root cause + fix site both Confirmed; verified against the live-rendered SVG down to the pixel, formula-traced end to end). No source files were modified — this is investigation-only.
3. **What's needed next.** Implement the fix sketch below (§ Recommended Fix Sketch) at `scriba/animation/primitives/base.py:1105-1117` (`_below_lane_height`) — a single shared-helper change that closes the gap for Array **and** its four confirmed siblings (Grid, DPTable, Queue, Stack) in one edit, without touching each primitive's file individually.

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | JudgeZone #12 (MED, caret vs. caption collision) + Structural Ask 3 (below-cell band tenant inventory) |
| Date opened      | 2026-07-10 |
| Status           | Concluded |
| System           | scriba @ 13eadc7 (0.34.0) |
| Evidence sources | source (`primitives/base.py`, `array.py`, `grid.py`, `dptable.py`, `queue.py`, `stack.py`, `layout.py`, `_types.py`, `_svg_helpers.py`), `CHANGELOG.md` (0.26.4, 0.31.0, 0.32.0 entries), 4 live renders of hand-written `.tex` repros (main repro + 3 controls) |

## Problem Statement

**Bug #12:** `\shape{a}{Array}{values=[...], labels="0..2", label="a caption line..."}` plus a bound `\cursor{a}{id=cab, at=..., ...}` renders the caret's triangle and multi-character id text overlapping the caption text. History: report #7 (caret vs. index digits) was fixed in 0.26.4 by dropping the caret below the index-label lane — but that landing zone is exactly where the caption lives. Reporter's two proposed fixes: (1) caption yields — place the caption below the caret lane when a bound caret exists, growing the below-extent reservation the way annotations already do; (2) register caret stacks + captions in the 0.31.0 shared obstacle model, with lane order index labels → caret → caption.

**Structural Ask 3:** inventory all tenants of the below-cell vertical band for Array-like shapes (index labels, caret stacks, captions, `position=below` annotation pills, plus traces/group brackets if present). For each: which code computes its y, which reservation mechanism grows the viewBox, whether it is registered in the 0.31.0 shared obstacle model. Produce a lane-map + who-knows-about-whom matrix, and identify exactly where the 0.26.4 caret-drop fix lives and why it used a fixed offset instead of a reservation.

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| `scriba/animation/primitives/base.py:247-254` | Available (Confirmed) | Caret geometry constants: `_CURSOR_GAP=6.0`, `_CURSOR_H=8.0`, `_CURSOR_HALF_W=5.0`, `_CURSOR_ID_FONT_PX=11`, `_CURSOR_ID_DY=11.0`, `_CURSOR_FAN_PITCH=14.0`. |
| `scriba/animation/primitives/base.py:813-833` (`_cursor_apex_origin`) | Available (Confirmed) | The 0.26.4 fix site itself — docstring cites "JudgeZone #7" by name. Anchors the caret apex to `max(cell_bottom, resolve_below_baseline())`. |
| `scriba/animation/primitives/base.py:835-930` (`emit_cursors_under`) | Available (Confirmed) | Paints the `▲` + id text; registers `_cursor_obstacle_boxes` (MUST severity) for the annotation-pill placer only. |
| `scriba/animation/primitives/base.py:932-956` (`_cursor_extent_below`) | Available (Confirmed) | Self-contained recomputation of the caret's deepest y, for `bounding_box()` to grow into. Independent of paint order (does **not** need `emit_cursors_under` to have run first). |
| `scriba/animation/primitives/base.py:518-563` (`_annotation_extent`, `annotation_below_overhang`) | Available (Confirmed) | Measures **only** `self._annotations` (pill extent). Never reads `_cursor_obstacle_boxes` or `_trace_obstacle_segments`. |
| `scriba/animation/primitives/base.py:1097-1117` (`resolve_below_baseline` default, `_below_lane_height`) | Available (Confirmed) | The shared reservation the caption's `caption_top` is built from — caret-blind by construction. |
| `scriba/animation/primitives/base.py:1179-1286` (`_emit_caption`) | Available (Confirmed) | Single-line vs. multi-line/tspan branches, different y-offset formulas, different baseline conventions (central vs. default alphabetic). |
| `scriba/animation/primitives/base.py:1440-1466` (obstacle join inside `emit_annotation_arrows`) | Available (Confirmed) | Confirms `_cursor_obstacle_boxes`/`_trace_obstacle_segments` are joined **only** for pill placement, never for caption placement. |
| `scriba/animation/primitives/array.py:495-664,666-696,818-858` | Available (Confirmed) | Array's `emit_svg` caption block, `bounding_box`, `resolve_below_baseline`, `_index_stack_items` — the exact call site of the bug, with an explicit "index row → callout lane → caption" design comment that predates caret support. |
| `scriba/animation/primitives/grid.py:275,379-393,412-422` | Available (Confirmed) | Verbatim same formula shape and call order as Array. |
| `scriba/animation/primitives/dptable.py:324-407` | Available (Confirmed) | `_caption_top_y()` doubles as `resolve_below_baseline()` — caret and caption share one anchor value with no cross-clearance. |
| `scriba/animation/primitives/queue.py:310-384,490-534` | Available (Confirmed) | Bottom-anchored variant (`caption_top = bbox.height − caption_height − arrow_above`); same blind spot via a different formula shape. |
| `scriba/animation/primitives/stack.py:245-300,418-449` | Available (Confirmed) | Same bottom-anchored shape as Queue; comment at 443-448 shows the caret was already hardened against covering *stack cells*, but not against the caption. |
| `scriba/animation/primitives/layout.py` (full) | Available (Confirmed) | `ASCENDER_RATIO=0.80`, `DESCENDER_RATIO=0.20`, `LINE_BOX_RATIO=1.00`, `stack_bottom` — used to hand-verify every y below. |
| `CHANGELOG.md:100-150` (0.31.0), `:341-367` (0.26.4), `:74-89` (0.32.0) | Available (Confirmed) | 0.26.4 = report #7 fix + explicit "deferred" note naming `\trace`/`\group`/`\note` as future-exposed; 0.31.0 = obstacle-model unification **and** first-time caret wiring for Stack/Queue, same release; 0.32.0 = same-family fix for Deque. |
| 4 live renders (see Reproduction Plan) | Available (Confirmed) | Main repro + 3 controls, rendered via `render.py` (0.34.0 / 13eadc7), raw SVG inspected for exact `y`/`points`/`dy` values. |

## Confirmed Findings

### Finding 1: the bug reproduces exactly as reported — and is worse, because the caption actually wraps to two lines
**Evidence:** live render of the exact repro (`jz12_repro.html`) — caption text `<text ... x="98" y="85" ...><tspan x="98" dy="0">a caption line under the </tspan><tspan x="98" dy="13">array</tspan></text>`, caret `<polygon points="98.0,72.0 93.0,80.0 103.0,80.0" .../><text x="98.0" y="91.0" ... dominant-baseline:central>cab</text>`.
**Detail:** The reporter's hand-calc assumed a single-line caption at y=81. In the real 3-cell-wide array, "a caption line under the array" does not fit on one line and lands on the multi-line/tspan branch (`base.py:1268-1286`, `y0 = top_y + _CAPTION_FONT_PX`), not the single-line branch (`base.py:1246-1267`, `top_y + _CAPTION_FONT_PX//2 + 2`). The qualitative collision the reporter describes (overlapping both the triangle band and the id-text band) is confirmed either way, but the actual overlap geometry differs from their hand-calc — see the measured table below.

### Finding 2: root cause — caption and caret share one anchor, and neither reservation mechanism knows about the other's reach
**Evidence:** `array.py:632`: `caption_top = int(self.resolve_below_baseline() + lane_h + _STACK_GAP)`. `base.py:829-833`: caret apex origin = `max(cell_bottom, resolve_below_baseline())`. Both read the *identical* `resolve_below_baseline()` value. `lane_h` (`array.py:631` → `base.py:1105-1117` → `base.py:554-563`) is derived exclusively from `_annotation_extent()` (`base.py:518-536`), which only measures `self._annotations` — never `_cursor_obstacle_boxes`.
**Detail:** The caret grows down from the shared anchor by a small fixed amount (`_CURSOR_GAP` + `_CURSOR_H` + `_CURSOR_ID_DY` + half the id font size ≈ 30px). The caption grows down from the *same* anchor by `lane_h` (0, absent any `\annotate`/`\link`/`\note` pill) `+ _STACK_GAP` (8px) before it even starts painting its own ~24px multi-line block. Because the caret's ~30px reach is not one of the inputs to `lane_h`, the caption starts only 8px past the shared anchor while the caret is still painting through roughly the 6-to-36px range past that same anchor — they interleave.

### Finding 3: `bounding_box()` already grows correctly for the caret — this is a pure z-order/overlap bug, not a clipping bug
**Evidence:** `array.py:693`: `bottom = max(bottom, self._cursor_extent_below())`, applied **after** `bottom` already includes the caption's height (`array.py:686-689`). The viewBox is always tall enough to contain both elements without clipping either one.
**Detail:** This is an important distinction for the fix: the defect is entirely about *where within* an already-sufficient box the caption starts painting, not about insufficient page height. `_cursor_extent_below()` is the exact number needed to fix this — it already exists and is already correct for box-sizing; it is simply never consulted when the caption's own `top_y` is computed.

### Finding 4: the defect is not gated on `labels=` — Control B refutes the reporter's implied scope
**Evidence:** Control B (`label=` present, `labels=` removed) — caret moves up (`46,72`→`46` triangle apex vs `72` in the main repro) exactly as `resolve_below_baseline()` shrinks from 66 to 40+... (see measured table); the caption moves up by the identical amount; **the overlap persists unchanged**, both interval widths landing at exactly the same 3.8px and 7.3px figures as the main repro (see below).
**Detail:** This proves the collision is anchor-relative, not lane-relative. Any Array with a caret **and** a caption collides, whether or not an index-label row is present. The bug title/reporter framing ("index-label lane" adjacent) undersells the actual blast radius — this is a general "caption is blind to the caret" defect.

### Finding 5: the vertical overlap is invariant to caret-id string length — Control C confirms the "widens" language is horizontal-only
**Evidence:** Control C (`id=c` instead of `id=cab`) — `<polygon points="98.0,72.0 93.0,80.0 103.0,80.0"/>`, `<text x="98.0" y="91.0" ...>c</text>`, caption `y="85"`/`dy="13"` — every y-coordinate is byte-identical to the main repro.
**Detail:** Only the horizontal glyph width of the id text changes with id length. The reporter's "multi-char ids widen the strike-through" is accurate but describes a horizontal effect layered on top of a vertical collision that exists regardless of id length (even `id=c` collides, at the exact same 3.8px/7.3px magnitudes).

### Finding 6: the 0.26.4 fix explicitly targeted index/tick digits, not captions — by design, not oversight
**Evidence:** `base.py:816-828` (`_cursor_apex_origin` docstring): *"...unless the target reserves a below-label lane — an Array `labels=` index row or a NumberLine's tick-label band — in which case the caret clears that lane so its id never lands on the index/tick digits (JudgeZone #7 / decoration-obstacle audit)."* `CHANGELOG.md:357-362`: *"Bound `\cursor` caret collided with the index-label lane (report #7)... The caret now anchors to `max(cell_bottom, resolve_below_baseline())` — the same below-lane `position=below` pills reserve — so it drops clear of the labels."*
**Detail:** `resolve_below_baseline()` was already a "known quantity" at the time of the #7 fix — it is what `position=below` pills use — so the fix reused it as a convenient anchor. But the caption's own vertical extent was never one of the things `resolve_below_baseline()` (or the lane grown below it) was designed to account for. Reusing it for the caret was correct for the labels-vs-caret problem it was solving; it silently inherited caption-blindness because the caption was never a party to that anchor's contract.

### Finding 7: the same architectural gap repeats verbatim across every primitive that combines caption support with caret support
**Evidence:** `array.py:632` (top-anchored: `resolve_below_baseline()+lane_h+STACK_GAP`); `grid.py:383` (identical shape: `th+_below_lane_height()+_CAPTION_CLEAR_GAP`); `dptable.py:335,379-383` (`resolve_below_baseline()` *is* `_caption_top_y()` — an even tighter coupling with no cross-clearance term at all); `queue.py:518-522` and `stack.py:439` (bottom-anchored: `caption_top = bbox.height − caption_block_height [− arrow_above]`, where `bbox.height` already folds in `max(..., _cursor_extent_below())` **before** the caption's own height is added — algebraically this still produces overlap whenever the caret's reach exceeds the caption's own clearance term, just via a different arithmetic path).
**Detail:** This is not an Array-specific bug. Five primitives (Array, Grid, DPTable, Queue, Stack) share the identical root defect — none of their caption-placement formulas take `_cursor_extent_below()` as an input, regardless of whether their formula is expressed top-down (add clearance, then paint caption) or bottom-up (subtract the caption's own height from a total that happens to already be caret-aware for box-sizing purposes only). `Matrix`, `LinkedList`, and `HashMap` support captions but have **zero** `\cursor`/caret code (grep-confirmed for Matrix and LinkedList; HashMap likewise) — they are not exposed to this bug class at all. `Deque` also carries caret support (`CHANGELOG.md:82-84`, 0.32.0, "same family the Stack/Queue fix closed") but was not independently rendered in this investigation; flagged as likely-same-family in the regression risks below.

### Finding 8: the 0.31.0 shared obstacle model only ever feeds the pill *placer* — never the caption's own reservation
**Evidence:** `base.py:1453-1466` (inside `emit_annotation_arrows`): `_cursor_obstacle_boxes` and `_trace_obstacle_segments` are joined into `_prim_seg_obs`, consumed only to steer where a `position=below` **pill** lands. `base.py:554-563` (`annotation_below_overhang`) and `518-536` (`_annotation_extent`) — the function chain the caption's `lane_h` comes from — never reference either obstacle list; they only ever measure the *pills'* own already-placed extent.
**Detail:** This is exactly why option 2 ("register caret + caption in the shared obstacle model") is not a small extension of existing plumbing. The obstacle lists exist and are correct for their one consumer (the pill placer). Making the caption obstacle-aware means adding a **second** consumer of that data, or extending `_below_lane_height()` to query it directly — the model was never built with more than one consumer in mind.

## Lane-Map + Who-Knows-About-Whom Matrix (Structural Ask 3)

Band tenants, bottom-cell region, Array (identical shape confirmed in Grid/DPTable/Queue/Stack; column call-sites are Array's):

| Tenant | Computes its y via | Reservation / viewBox-growth mechanism | In 0.31.0 obstacle model? | Caption-aware? | Caret-aware? |
| --- | --- | --- | --- | --- | --- |
| Index-label row | `_index_stack_items()` + `resolve_below_baseline()` (`array.py:818-858`) | Fixed geometry (`CELL_HEIGHT+INDEX_LABEL_OFFSET`); always painted first, nothing yields to it | No (not a decoration, it's the anchor everything else is defined relative to) | N/A (caption is always placed after it by construction) | Yes — this is the *only* pairing the 0.26.4 fix solved |
| `position=below` annotation pills | `emit_annotation_arrows` placer, using `resolve_below_baseline()` as the lane top (`base.py:1379+`) | `_annotation_extent()` → `annotation_below_overhang()` → `_below_lane_height()` (`base.py:518-563,1105-1117`) | **Yes** — dodges `_cursor_obstacle_boxes`, `_trace_obstacle_segments`, hull/trace label obstacles at placement time | Indirectly — if a pill grows to dodge a caret, `_annotation_extent()` picks that up, and the caption (which adds `lane_h`) inherits the clearance | Yes, via the obstacle join (`base.py:1460-1466`) |
| Bound `\cursor` caret (`▲` + id) | `_cursor_apex_origin()` (`base.py:813-833`), anchored to `max(cell_bottom, resolve_below_baseline())` | `_cursor_extent_below()` grows `bounding_box()` only (`array.py:693`); registers `_cursor_obstacle_boxes` for the pill placer only (`base.py:835-930`) | **Yes**, as a MUST obstacle — but only consumed by the pill placer | **No** — this is the bug | N/A |
| `\trace` scan stroke/pill | `emit_traces_under()` (`base.py:618-708`) | Registers `_trace_obstacle_segments`; no dedicated "extent below" measure exists for it | **Yes**, as a SHOULD obstacle — pill placer only | **No** — same blind spot as the caret, just never reported because traces are less commonly combined with captions | N/A |
| Caption (`label=`) | `caption_top = resolve_below_baseline() + lane_h + _STACK_GAP` (`array.py:632`) | `_caption_block_height()` folded into `bounding_box()` (`array.py:687-689`) | **No** — never a client of the obstacle model, never registers anything, never queries it | — | **No** |

**Reading the matrix:** the index-label row is the one universally-respected anchor. Pills are the *only* tenant that is fully obstacle-aware in both directions (dodges others, and its own grown extent is measured). The caret and the trace stroke are each half-wired — they can push pills out of the way, but nothing pushes *them* out of the way, and nothing they do reaches the caption. The caption is the *least* wired tenant — zero participation in the obstacle model in either direction — which is exactly why it is the one that visibly collides today; it is simply the tenant most likely to be painted last while claiming a position computed with the least information.

**Cross-primitive corroboration** (which primitives are structurally exposed to this exact bug class):

| Primitive | Caption support | Caret (`\cursor`) support | Exposed to JZ#12's bug class? |
| --- | --- | --- | --- |
| Array | Yes | Yes | **Yes — rendered & measured (this investigation)** |
| Grid | Yes | Yes | Yes — code-confirmed, verbatim same formula (`grid.py:383` vs `array.py:632`) |
| DPTable | Yes | Yes | Yes — code-confirmed, tighter coupling (shared anchor value, `dptable.py:335,379-383`) |
| Queue | Yes | Yes | Yes — code-confirmed, bottom-anchored variant (`queue.py:518-522`) |
| Stack | Yes | Yes | Yes — code-confirmed, bottom-anchored variant (`stack.py:439`) |
| Deque | Unconfirmed | Yes (`CHANGELOG.md:82-84`) | Likely — not independently verified in this pass |
| NumberLine | Yes | Yes | Likely (grep-confirmed caption+cursor refs both present) — not code-traced in this pass |
| Matrix | Yes | **No** | No — no `\cursor` code exists on Matrix at all |
| LinkedList | Yes | **No** | No |
| HashMap | Yes | **No** | No |

## Deduced Conclusions

### Deduction 1: this is a design-scope gap, not a regression — the caption's placement formula was never designed to think about the caret
**Based on:** Findings 2, 6.
**Reasoning:** The comments at `array.py:522-524` and `array.py:625-627` state the intended stacking order as "index row → callout lane → caption" — a three-tenant model written before caret support existed on Array in this form. The caret was later grafted on as something that "rides the same decoration band as traces" (`array.py:646`), painted and reserved-for independently, but never folded back into the caption's own formula.
**Conclusion:** The bug is best framed as "the caption's placement formula has an incomplete input set," not "the caret's placement formula is wrong." The caret's own behavior (anchoring to `resolve_below_baseline()`) is exactly what the #7 fix intended and remains correct for the index-label case (Control A confirms a clean gap there).

### Deduction 2: the gap is structural and cross-primitive, and it grew during the same release that started closing it elsewhere
**Based on:** Findings 7, 8, and the CHANGELOG evidence.
**Reasoning:** 0.31.0 shipped the trace/group obstacle-model unification **and**, in the same release, wired `\cursor` onto Stack and Queue for the first time (`CHANGELOG.md:131-138`). Both of those changes improved pill-vs-decoration awareness; neither touched caption placement. So the caption-vs-caret gap wasn't just left open on Array — it was actively extended to two more primitives in the very release that made the surrounding obstacle model more sophisticated everywhere else.
**Conclusion:** A fix scoped only to Array's `emit_svg` would leave 4+ known siblings with the identical defect. The structurally cheap intervention point is the one function all of them route through for their reservation math — see below.

### Deduction 3: option 2 (full obstacle-model registration) is feasible but is solving a bigger problem than bug #12 asks for; a narrower reuse of existing, already-correct machinery closes the reported bug and its whole known sibling class today
**Based on:** Findings 3, 8.
**Reasoning:** `_cursor_extent_below()` (`base.py:932-956`) already computes exactly the number needed — self-contained, order-independent, already used correctly by every affected primitive's `bounding_box()`. The missing step is not new measurement code; it's one more read of a number that already exists, in one more place.
**Conclusion:** Recommend the narrow fix (§ Recommended Fix Sketch) as the minimal, highest-leverage change. Full obstacle-model registration (threading `_cursor_obstacle_boxes`/`_trace_obstacle_segments` into `_below_lane_height()` generically) is the more complete long-term answer — it would also close the trace-stroke-vs-caption gap this investigation surfaced as a side effect (Finding 8) — but is not required to close ticket #12.

## Source Code Trace

| Element | Detail |
| ------- | ------ |
| Error origin (Array) | `scriba/animation/primitives/array.py:632` — `caption_top = int(self.resolve_below_baseline() + lane_h + _STACK_GAP)`, blind to `self._cursor_extent_below()` |
| Shared root cause | `scriba/animation/primitives/base.py:1105-1117` (`_below_lane_height`) — the one function all affected primitives' caption math is ultimately built from; reads only `annotation_below_overhang()` |
| Caret geometry (correct, for box-sizing only) | `scriba/animation/primitives/base.py:932-956` (`_cursor_extent_below`), consumed at `array.py:693`, `grid.py:422`, `queue.py:375`, `stack.py:283` |
| 0.26.4 fix site (report #7) | `scriba/animation/primitives/base.py:813-833` (`_cursor_apex_origin`) — docstring names JudgeZone #7 explicitly |
| 0.26.4 own "deferred" note | `CHANGELOG.md:364-367` — "Other direct-emit decorations (`\group` title pill, corner `\note`, `\trace` stroke) can still overlap content... tracked for a follow-up." Captions are not named but are the same unaddressed class. |
| 0.31.0 obstacle-model unification | `CHANGELOG.md:131-135`; consumer code `base.py:1453-1466` inside `emit_annotation_arrows` |
| 0.31.0 caret wiring for Stack/Queue | `CHANGELOG.md:136-138` |
| 0.32.0 sibling fix (Deque) | `CHANGELOG.md:82-84` |
| Sibling call sites needing the analogous fix | `grid.py:383`; `dptable.py:335`; `queue.py:518-522`; `stack.py:439` |

## Reproduction Plan

All renders via `SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py <input> -o <output>` from the repo root (0.34.0 / 13eadc7). Font-metric assumption used throughout: `layout.py`'s own constants — `ASCENDER_RATIO=0.80`, `DESCENDER_RATIO=0.20` (glyph box = `[baseline − 0.80·font_px, baseline + 0.20·font_px]` for default/alphabetic baseline text) and a symmetric `±0.5·font_px` box for `dominant-baseline:central` text (SVG central-baseline vertically centers the em box on the given y).

**1. Main repro** (`values=[10,20,30], labels="0..2", label="a caption line under the array"`, `id=cab`):
```html
<text class="scriba-index-label idx" x="160" y="56" ... font-size:10px">2</text>
<text class="scriba-primitive-label" x="98" y="85" ... font-size:11px">
  <tspan x="98" dy="0">a caption line under the </tspan><tspan x="98" dy="13">array</tspan>
</text>
<polygon points="98.0,72.0 93.0,80.0 103.0,80.0" fill="#506882"/>
<text x="98.0" y="91.0" fill="#506882" font-size="11" dominant-baseline:central>cab</text>
```
Hand-derivation (matches byte-for-byte): `resolve_below_baseline()` = `stack_bottom([index TextBox font=10, hanging], start_y=56, gap=8)` = 66. Caret: apex = 66+6=**72**; base = 72+8=**80**; id text y = 80+11=**91**. Caption: `caption_top` = 66+0(no pills)+8=74; multi-line `y0` = 74+11=**85**; line 2 baseline = 85+13=**98**.

| Element | Glyph/shape interval (y) | Overlap vs. |
| --- | --- | --- |
| Caret triangle | [72, 80] | Caption line 1 glyph [76.2, 87.2] → **3.8px overlap** (80 − 76.2) |
| Caret id text "cab" (central, font 11) | [85.5, 96.5] | Caption line 1 glyph [76.2, 87.2] → 1.7px sliver overlap; Caption line 2 glyph [89.2, 100.2] → **7.3px overlap** (96.5 − 89.2, the worst collision) |

**2. Control A — no caption** (`labels="0..2"`, no `label=`):
```html
<polygon points="92.0,72.0 87.0,80.0 97.0,80.0" .../><text x="92.0" y="91.0" ...>cab</text>
```
Triangle/id-text y unchanged (72-80 / 91) — confirms the caret-vs-index-label path (0.26.4's actual fix target) remains clean on its own; no caption present, so no overlap. Index digit row at y=56 sits a clear 16px above the triangle apex.

**3. Control B — no `labels=`, caption still present** (refutes the labels-gated framing):
```html
<text class="scriba-primitive-label" x="98" y="59" ...><tspan x="98" dy="0">a caption line under the </tspan><tspan x="98" dy="13">array</tspan></text>
<polygon points="98.0,46.0 93.0,54.0 103.0,54.0" .../><text x="98.0" y="65.0" ...>cab</text>
```
`resolve_below_baseline()` drops to 40 (no index row → `float(CELL_HEIGHT)`, `array.py:855`). Caret: apex 40+6=46, base 54, id y=65. Caption: top=40+8=48, line1 y0=59, line2=72.
Overlap: triangle [46,54] vs. caption line 1 [50.2,61.2] → **3.8px** (identical to the main repro); id text [59.5,70.5] vs. caption line 2 [63.2,74.2] → **7.3px** (identical to the main repro). **The overlap magnitude is exactly invariant to `labels=`** — only its absolute screen position shifts. This is the strongest possible confirmation that the bug is anchor-relative, not lane-relative.

**4. Control C — single-char id** (`id=c` instead of `id=cab`, `labels=` + caption both present):
```html
<polygon points="98.0,72.0 93.0,80.0 103.0,80.0" .../><text x="98.0" y="91.0" ...>c</text>
<text class="scriba-primitive-label" x="98" y="85" ...><tspan x="98" dy="0">a caption line under the </tspan><tspan x="98" dy="13">array</tspan></text>
```
Every y-coordinate is byte-identical to the main repro. Only the horizontal glyph width of the id text differs. Confirms the vertical collision is independent of id length; "multi-char ids widen the strike-through" is a real but strictly horizontal, additional effect.

## Regression Risk Notes

- **Shapes without a caption:** zero risk. `_caption_lines(...)` gates the entire caption block (`array.py:630`); if there is no `label=`, `caption_top` is never computed and the proposed fix's extra `max()` term is simply never evaluated for that shape/frame.
- **Shapes without a caret:** zero risk, by the same byte-stability invariant `_cursor_extent_below()` already documents ("Returns `0.0` when there is no caret, so every non-cursor primitive and frame is byte-identical" — `base.py:936-937`). The proposed fix's new term evaluates to 0 whenever `self._cursors` is empty.
- **Matrix / LinkedList / HashMap:** **not at risk** — confirmed zero `\cursor` code in any of the three (grep-confirmed for Matrix and LinkedList in this investigation). The task's framing ("Matrix/Grid cursors") should be corrected: Matrix has no caret feature at all; **Grid** is the one that shares Array's exact exposure.
- **Grid / DPTable / Queue / Stack (and likely Deque, NumberLine):** currently exposed to the identical bug (Finding 7); the recommended shared-helper fix (below) closes all of them in one edit, but any snapshot/golden fixture that already combines a caret **and** a caption on one of these shapes will see its caption shift down and must be re-blessed.
- **`position=below` pills:** low risk. Pills are already obstacle-aware (dodge `_cursor_obstacle_boxes` at placement time via the 0.31.0 unification), so in the common case where a pill already yielded to a caret, `_annotation_extent()` already reflects the grown extent and the proposed fix's new term will rarely be the larger of the two `max()` operands. The one edge case worth a visual spot-check post-fix: a caret on one cell and a `position=below` pill anchored to a spatially distant cell (no actual horizontal overlap today) — the fix would still grow `_below_lane_height()` to clear the caret's full vertical reach even though that specific pill never needed it, which is a cosmetic (extra whitespace), not correctness, regression, but would still change any golden fixture with that exact combination.
- **Trace strokes vs. captions:** out of scope for this ticket's minimal fix (the proposed fix reads `_cursor_extent_below()` specifically, not a generic obstacle union), but Finding 8 shows the identical blind spot exists for `\trace` today. Worth a follow-up ticket; not blocking #12.

## Recommended Fix Sketch

**Option 1 (reporter's framing), realized as a single shared-helper change rather than five per-primitive patches:**

`scriba/animation/primitives/base.py:1105-1117` (`_below_lane_height`) — currently:
```python
def _below_lane_height(self) -> int:
    baseline = self.resolve_below_baseline()
    if baseline is None:
        return 0
    return self.annotation_below_overhang(float(baseline))
```
Change to also clear the caret's own measured reach past the same baseline:
```python
def _below_lane_height(self) -> int:
    baseline = self.resolve_below_baseline()
    if baseline is None:
        return 0
    lane = self.annotation_below_overhang(float(baseline))
    caret_reach = math.ceil(self._cursor_extent_below() - float(baseline))
    return int(max(lane, caret_reach, 0))
```
This is the single point every affected primitive's caption math routes through, either directly (Array `array.py:631-632`, Grid `grid.py:383`, DPTable `dptable.py:335`) or via `bounding_box()` (Queue `queue.py:380`, Stack `stack.py:290`) — so it closes Array's reported bug and all four confirmed siblings in one edit. Verified against the main repro's numbers: `caret_reach = ceil(96.5 − 66) = 31`; new `caption_top = 66+31+8=105`; new caption line-1 glyph `[107.2,118.2]` clears the caret's `[72,96.5]` range with an ~11px margin — no overlap, and `_STACK_GAP`'s intended clearance is preserved (the caption now starts exactly `_STACK_GAP` px past the caret's bottom, matching how pills already get their own 8px gap from their reserved lane).

**Option 2 (full shared obstacle-model registration) — structural feasibility assessment:** feasible, but strictly larger in scope than option 1. It requires either (a) a new "extent" query analogous to `_cursor_extent_below()` for every obstacle kind (traces currently have none), or (b) reworking `_below_lane_height()`/`annotation_below_overhang()` to walk the same `_prim_seg_obs`-style obstacle union `emit_annotation_arrows` already assembles (`base.py:1440-1480`) instead of re-deriving caret reach independently. Worth doing eventually — it would also close the trace-stroke-vs-caption gap this investigation found as a side effect (Finding 8) — but is not necessary to close ticket #12; option 1 (as sketched above) already reuses `_cursor_extent_below()`, an existing and already-correct piece of that same obstacle machinery, so it captures most of option 2's practical benefit for carets specifically at a fraction of the implementation cost.

## Affected Tests

- Any existing golden/snapshot fixture with a bound `\cursor` **and** a `label=` caption on Array, Grid, DPTable, Queue, or Stack will shift (caption moves down) and needs re-blessing.
- New regression coverage should assert the non-overlap invariant directly (e.g. caption's topmost painted y ≥ caret's bottommost painted y + some minimum gap) for at least one shape from each of the two formula families (top-anchored: Array/Grid/DPTable; bottom-anchored: Queue/Stack), plus the `labels=`-absent case (Control B's shape) to lock in that the fix is anchor-relative, not lane-gated.
- Worth adding a no-caret/no-caption control to whatever suite already snapshots these primitives, specifically to pin the byte-stability invariant (`_cursor_extent_below()==0` when `self._cursors` is empty) so a future change to this helper can't silently regress the common case.

## Side Findings

- (Confirmed) The `\trace` scan stroke shares the caption-blindness gap the caret has (Finding 8) — never reported because it's evidently a rarer combination, but structurally identical. Worth its own ticket.
- (Confirmed) `array.py:625-627`'s own comment states the caption should be "the bottom-most element (not buried between the index row and the position=below pills)" — that intent is honored relative to pills and the index row, but the comment was written before (or without considering) caret support, and nothing in the codebase updated it to include the caret in the "bottom-most" ordering guarantee.
- (Confirmed) Deque was not independently rendered in this investigation (out of the task's stated Array-like-shapes scope) but per `CHANGELOG.md:82-84` shares the exact caret-wiring lineage of Stack/Queue and should be assumed same-family until checked.

## Conclusion

**Confidence:** High

**Verdict: CONFIRMED**, and broader in scope than the original report. The collision reproduces exactly as described and is measurable and reproducible: a **3.8px** overlap between the caret triangle and the caption's first line, and a **7.3px** overlap between the caret's id text and the caption's second line, in the exact repro given. Critically, Control B shows these same two overlap magnitudes recur byte-for-byte with `labels=` removed — the bug is not "caret vs. index-label lane, caption included incidentally," it is a general "caption never consults the caret's measured extent" defect, rooted in the caption's placement formula (`array.py:632` and its verbatim/analogous siblings in `grid.py`, `dptable.py`, `queue.py`, `stack.py`) reading only `resolve_below_baseline() + annotation-pill-derived lane_h`, never `_cursor_extent_below()` — even though the latter already exists, is already correct, and is already used (just one call site later, for `bounding_box()` only) by every one of those same primitives.
