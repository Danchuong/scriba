# Investigation: JudgeZone #15 — `position=above` pill on a Tree's ROOT node overlaps the Tree caption (top lane not in the reservation model)

## Hand-off Brief

1. **What happened.** (Confirmed, algebraically and empirically.) The reporter's repro is accurate once corrected for a missing `root=` param (the literal text in the brief omits it; the `\shape` call does not parse without it). On `Tree`, an `\annotate{...}{position=above}` pill on the root node overlaps the `label=` caption whenever the annotation's reserved lane (`arrow_above`) is tall enough to push the caption down into the pill's fixed position. The reporter's framing — this is the mirror of the already-fixed bottom-band family (#7/#12) — is exactly right: the bottom lane got a shared reservation model; the top lane (caption-above ⇄ above-pill) never did. The defect is **not** Tree-specific: `Forest` and `Graph` share the identical top-caption helper pair (`_top_caption_band`/`_emit_top_caption`) and the identical double-translate structure, and both reproduce the same collision under the same conditions.
2. **Where the case stands.** Concluded — root cause confirmed, fix implemented and verified (this assignment combined investigation with a structural fix, unlike the read-only #12/#13 precedents). See `_bmad-output/implementation-artifacts/spec-fix-judgezone-15-top-band-reservation.md` for the fix itself (new `base.py` helper `_top_band_layout`, consumed by `Tree`/`Forest`/`Graph`'s `emit_svg`), its tests, and its regression sweep.
3. **What's needed next.** Nothing further for the confirmed scope. Two adjacent, out-of-scope observations are recorded below (§ Out-of-scope Observations) for a future ticket: a pre-existing Forest wrap-width measurement divergence unrelated to this bug, and a `\group`-label top-band gap that was not exercised by any repro and was left untouched per the fix's minimal-surface mandate.

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | JudgeZone #15 (MED, top-band pill vs. caption collision) |
| Date opened      | 2026-07-11 |
| Status           | Concluded |
| System           | scriba @ 13eadc7 (0.34.0) |
| Evidence sources | source (`primitives/base.py`, `tree.py`, `forest.py`, `graph.py`, `layout.py`, `_types.py`, `_svg_helpers.py`), 3 live constructions of the reporter's repro + Forest/Graph analogues via direct Python-API rendering (no browser/Playwright — static SVG string parsing only, per task constraint), `tests/unit/test_below_band_lanes.py` (JZ-12 precedent pattern) |

## Problem Statement

**Bug #15:** on a `Tree` carrying both `label="a caption line on top"` (top-band caption) and a bound `\annotate{t.node[1]}{label="pill above root", position=above, ...}` where `node[1]` is the tree's root, the pill and the caption paint at overlapping y-ranges. Repro (as amended, `root=` restored):

```
\begin{animation}[id="t", label="x"]
\shape{t}{Tree}{root="1", nodes=["1","2","3"], edges=[("1","2"),("1","3")], label="a caption line on top"}
\step[title="one"]
\annotate{t.node[1]}{label="pill above root", position=above, color=good}
\narrate{pill vs caption.}
\end{animation}
```

History: report #7/#12 fixed the analogous **bottom**-lane collision (caret/pills vs. bottom captions) by routing every bottom-lane tenant through a shared reservation model (`_below_lane_height`, `resolve_below_baseline`). Tree, Forest, and Graph are the three primitives whose caption sits **above** the content instead of below it — for them, an above-pill and the caption are both top-lane tenants, and no equivalent shared model exists for that lane. The reporter's two candidate framings — "this is the mirror of #7/#12" and "the top lane needs the same reservation treatment" — are both confirmed correct.

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| `scriba/animation/primitives/base.py:495-517` (`annotation_height_above`) | Available (Confirmed) | Exact painted px an above-pill reaches above `y=0`, measured by running the real annotation emitter into a scratch buffer (closed-form Bézier extrema). Universal across every primitive with above-pills. |
| `scriba/animation/primitives/base.py:591-599` (`_reserved_arrow_above`) | Available (Confirmed) | `max(annotation_height_above(), _min_arrow_above)` — the value every primitive's `emit_svg`/`bounding_box` calls `arrow_above`. |
| `scriba/animation/primitives/base.py:1345-1352` (`_top_caption_band`) | Available (Confirmed) | Returns `max(_TOP_CAPTION_BAND=28, _TOP_CAPTION_TOP_Y=9 + caption_block_height)` — the reserved height for a top-band caption. Zero awareness of `arrow_above`/`_reserved_arrow_above()` — **this is the root cause's other half.** |
| `scriba/animation/primitives/base.py:1354-1375` (`_emit_top_caption`) | Available (Confirmed) | Paints the caption at fixed local `top_y=_TOP_CAPTION_TOP_Y=9`, inside whatever transform the caller has open at the point it's called — the caller's transform nesting is what actually determines the caption's absolute position. |
| `scriba/animation/primitives/_types.py:179` (`_PRIMITIVE_LABEL_Y=14`), `base.py:204` (`_CAPTION_FONT_PX=LABEL_FONT_PX=11`), `base.py:218-221` (`_TOP_CAPTION_BAND=28`, `_TOP_CAPTION_TOP_Y=9`) | Available (Confirmed) | The concrete constants behind the algebra below. |
| `scriba/animation/primitives/tree.py` `emit_svg` (pre-fix, opening block) | Available (Confirmed) | Outer transform `ty = r + arrow_above`; caption painted inside that outer group; THEN a nested inner `<g transform="translate(0,label_offset)">` wraps nodes/edges/pills only when a caption is present. Two independent transform depths for caption vs. content. |
| `scriba/animation/primitives/graph.py` `emit_svg` (pre-fix, opening block) | Available (Confirmed) | Byte-identical structural shape to Tree's (`ty = r + arrow_above`, same nested-group pattern). |
| `scriba/animation/primitives/forest.py` `emit_svg` (pre-fix, opening block) | Available (Confirmed) | Same nested-group pattern, but the outer transform has no `+r` term (`ty = arrow_above` — Forest's outer frame is `left_pad`-only, no per-node radius offset). |
| `Matrix`, `LinkedList`, `HashMap`, `Array`, `Grid`, `DPTable`, `Queue`, `Stack`, `Deque`, `NumberLine`, `Hypercube`, `Bar` | Available (Confirmed, by grep) | All caption-below primitives, or caption-less — not exposed to this bug class. Tree/Forest/Graph are the complete affected set (grep-confirmed: only these three call `_top_caption_band`/`_emit_top_caption`). |
| 3 live Python-API renders (main repro + Forest analogue + Graph analogue) | Available (Confirmed) | Constructed directly via each primitive's public API + `emit_svg()`, not through the CLI/HTML pipeline (no `_html_stitcher.py`/`renderer.py` involvement needed to reproduce — confirms the defect lives entirely inside the three primitives' own SVG emission, consistent with the constraint that those two files were off-limits this session). |

## Confirmed Findings

### Finding 1: the bug reproduces exactly as reported, and by the same mechanism, on all three top-caption primitives
**Evidence:** Tree repro (root cause construction) — caption band measured at `(48.5, 59.5)`, pill band measured at `(49.0, 69.0)`: **10.5px overlap**. Forest analogue (root-equivalent node, same shape of repro) — caption band `(22.5, 33.5)`, pill band `(29.0, 63.0)`: **4.5px overlap**. Graph analogue (a graph node pinned to the top of the layout) — caption band `(58.5, 69.5)`, pill band `(49.0, 69.0)`: **10.5px overlap**.
**Detail:** All three primitives share the identical `_top_caption_band`/`_emit_top_caption` pair from `base.py`, and all three wrap their content in the same "outer transform carries `arrow_above`, inner transform carries `label_offset`" nesting. The overlap magnitude differs (10.5 / 4.5 / 10.5) only because the three repros' pill heights and caption block heights differ slightly — the mechanism producing the overlap is the same formula in all three cases (see Finding 2).

### Finding 2: root cause — an outer/inner double-translate whose composition cancels `arrow_above` out of the pill's position but not the caption's
**Evidence:** pre-fix `tree.py`/`graph.py`: outer `ty = r + arrow_above`; the caption is emitted while only the outer transform is open, so its absolute position is `r + arrow_above + top_y_local`. The inner group `translate(0, label_offset)` opens only afterward, wrapping nodes/edges/annotation pills; a pill's own natural reach is defined (by `annotation_height_above()`) as extending `arrow_above` px above its anchor node's local `y=0`. Composing the two transforms: pill absolute-y = `(r + arrow_above) + label_offset + (-arrow_above) = r + label_offset` — the `arrow_above` terms cancel exactly, leaving the pill's absolute position **invariant to `arrow_above`**. The caption's absolute position has no such cancelling term: it is `r + arrow_above + top_y_local`, which grows linearly with `arrow_above`.
**Detail:** This is the crux of the bug. `label_offset` (from `_top_caption_band`) is sized tightly enough that the caption's own bottom edge, measured from the *inner* frame's would-be origin, sits right at the pill's fixed position (`r + label_offset`) — that sizing is exactly correct when `arrow_above == 0`. But because the caption is painted through the *outer* transform only, every non-zero `arrow_above` pushes the caption an additional `arrow_above` px down past that already-tight boundary, directly into the pill, which never moved. The bug is not that either reservation is wrong in isolation — `label_offset` correctly sizes the caption block, and `arrow_above` correctly sizes the pill lane — it is that the two reservations are consumed through different transform depths, so their sum is not what either measurement assumed.

### Finding 3: `bounding_box()` already accounts for both terms — this is a pure ordering/overlap bug, not a clipping bug
**Evidence:** each primitive's `bounding_box()` computes total height using `arrow_above + label_offset + <content height>` (the two terms are additive, never dropped). The viewBox in all three repros is already tall enough to contain both the caption and the pill without clipping either.
**Detail:** Same class of defect as JZ-12 Finding 3 (the bottom-lane precedent): the box-sizing math was always correct; the defect is entirely about *where within* an already-sufficiently-tall box each element starts painting. This matters for the fix: no `bounding_box()` change was needed anywhere — only re-ordering which transform depth carries which term (see spec-fix doc).

### Finding 4: the collision is gated on the caption being present, not on which node carries the pill
**Evidence:** the inner `translate(0, label_offset)` group is emitted `if label_offset:` — i.e. only when `self.label is not None`. Without a caption, `label_offset == 0`, there is no inner group, and the pill's absolute position is `r + arrow_above` directly (matching the historical, pre-#7/#12-family single-group shape). The reporter's repro targets the root node specifically because the root is the node most likely to sit at the top of a Tree's layout, close enough to the caption for a modest `arrow_above` to cause visible overlap — but the underlying defect fires for **any** node whose pill's vertical reach, combined with the caption's own bottom edge, exceeds `label_offset`'s built-in slack. The bug is a top-lane-vs-caption problem, not specifically a "root node" problem — the ticket's title is accurate as a common trigger, not as the full scope.
**Detail:** This matches the reporter's own framing that the fix should be general ("for ANY primitive whose caption sits on top"), not a root-node special case. The implemented fix (see spec-fix doc) does not special-case the root node or any particular target — it changes how `arrow_above` and `label_offset` compose, universally, whenever a caption is present.

### Finding 5: Tree, Forest, and Graph are a closed set — no fourth primitive shares this defect
**Evidence:** grep across `scriba/animation/primitives/*.py` for callers of `_top_caption_band`/`_emit_top_caption` returns exactly three call sites: `tree.py`, `forest.py`, `graph.py`. Every other primitive with caption support (Array, Grid, DPTable, Queue, Stack, Deque, Matrix, LinkedList, HashMap, NumberLine, Hypercube, Bar) places its caption in the **below**-content band (already covered by the #7/#12 reservation model) or has no caption support at all.
**Detail:** Confirms the tenant inventory below is exhaustive for this ticket's scope — no fourth primitive needed a parallel fix.

## Tenant Inventory — Top Band (mirrors JZ-12's below-band lane-map, Structural Ask framing)

Top-of-content region, Tree/Forest/Graph (identical shape across all three; column call-sites are Tree's):

| Tenant | Computes its y via | Reservation mechanism | Caption-aware (pre-fix)? | Pill-aware (pre-fix)? |
| --- | --- | --- | --- | --- |
| `position=above` annotation pill | `emit_annotation_arrows` placer, anchored at the node's local `y=0`, reaching up `arrow_above` px | `annotation_height_above()` / `_reserved_arrow_above()` (`base.py:495-599`) — exact painted extent, universal across all primitives | **No** — its own reach is fixed regardless of whether a caption exists (pre-fix) | N/A |
| Top-band caption (`label=`) | `top_y = _TOP_CAPTION_TOP_Y` (local, fixed), positioned by whichever transform is open when `_emit_top_caption` is called | `_top_caption_band()` (`base.py:1345-1352`) — sized to the caption's own block height only | N/A | **No** — this is the bug (`_top_caption_band` takes no `arrow_above` input) |
| Node/edge content | node-local coordinates, shifted by the inner `translate(0, label_offset)` when a caption is present | N/A (not a reservation consumer, just shifted) | Yes (that's what `label_offset` is for) | Yes (indirectly, via the same shift) |

Post-fix, the pill row's "Caption-aware?" becomes **Yes** and the caption row's "Pill-aware?" becomes **Yes** — both now consumed through `_top_band_layout()`, which places the caption at the outer frame (independent of `arrow_above`) and folds the pill lane into the inner content shift (`label_offset + arrow_above`) whenever a caption is present. See the spec-fix doc for the exact mechanism and its byte-stability proof for the no-caption case.

## Out-of-scope Observations

Two adjacent issues were noticed during this investigation and are recorded here, not fixed, per the fix's minimal-surface mandate (only the confirmed #15 collision was in scope):

1. **Forest wrap-width divergence (pre-existing, unrelated to #15).** Forest's caption wrap width is computed from `self._envelope_width`, a value assembled from a scratch layout pass; a hand-measurement against the real rendered pipeline showed a small divergence between the scratch estimate and the actual painted footprint width in at least one tested configuration. This affects caption *word-wrap point* selection only (which words land on which line), not the top-band collision this ticket is about, and it existed identically before and after this fix (the fix does not touch `_envelope_width` or any wrap-width computation). Flagged for a future ticket, not actioned here.
2. **`\group` labels have no top-band reservation story.** `\group` label placement (a distinct annotation-like decoration, not the primitive's own `label=` caption) was not exercised by any of the three confirmed repros and has its own, separate placement code path. Whether a grouped/bracketed region's label can collide with a top-band caption or an above-pill was not tested in this investigation (no repro combined `\group` with a top-band caption + above-pill) and is left as an open question for whoever owns `\group` label placement next.

## Scope Compliance

This investigation and its accompanying fix (see spec-fix doc) touched only `scriba/animation/primitives/base.py`, `tree.py`, `forest.py`, `graph.py`. No changes were made to `scriba/animation/_html_stitcher.py`, `scriba/animation/static/scriba-scene-primitives.css` (both owned by a concurrent, unrelated fix in the same working tree), `scriba/tex/renderer.py`, or any `_grammar_values.py` file. All verification in this investigation was done via direct Python-API construction of each primitive and static parsing of the resulting SVG strings — no Playwright or other browser automation was used, per this task's constraint.
