# Investigation: JudgeZone #16 — Below-Pill Leader Stub on Displaced Targets

**Agent:** bmad-16-leader
**Status:** ROOT CAUSE CONFIRMED — see companion spec-fix doc for fix, tests, and regression evidence.
**Spec-fix doc:** `_bmad-output/implementation-artifacts/spec-fix-judgezone-16-leader-span.md`
**Sibling:** JudgeZone #12/#15 (`spec-fix-judgezone-12-below-band-reservation.md`,
`spec-fix-judgezone-15-top-band-reservation.md`) — those fixes gave the
below/top band a shared reservation model that correctly displaces a
below/above pill away from the anchor when another tenant (caret lane,
caption, index row) claims that vertical space. This bug lives one layer
downstream: the *displacement* those fixes compute is correct — the
reporter confirms it ("displacement itself is CORRECT... ONLY the leader
is broken") — but the *leader line* connecting the displaced pill back to
its anchor was never taught to follow the displacement.

## Verdict

Confirmed, single-line root cause: `_svg_helpers.py:3836` (pre-fix), inside
`emit_position_label_svg`'s automatic leader block (R-07/R-08):

```python
_lead_oy = float(below_baseline) if (below_baseline is not None and position == "below") else ay
```

This unconditionally roots the leader's Y-origin at `below_baseline` — the
shape-*global* below-lane coordinate — whenever a `position="below"` pill
has a `below_baseline` at all, regardless of how far that lane sits from
the *specific* annotated target. For a single-row layout (Array, Bar,
DPTable's 1D mode) the lane sits just past that target's own index/caption
stack, so rooting there is correct — a short, legitimate connector. For a
non-bottom-row or internal target in a taller structure (Tree's internal
nodes, Grid/Matrix/DPTable's 2D-mode top rows, Graph/Hypercube's top
nodes), `below_baseline` is the bottom of the *whole* structure — another
row's territory, unrelated to this target — so the leader roots dozens to
hundreds of pixels away from the anchor, and the `_line_rect_intersection`
clip (which clips the line to the pill's boundary) immediately truncates
almost the entire run, leaving only the ~10px sliver between the clip
point and the pill edge. That sliver *is* the reported stub.

## Reproduction

Confirmed on a minimal repro matching the bug report's shape:

```
\shape{t}{Tree}{root="A", nodes=["A","B","C","D","E"], edges=[("A","B"),("A","C"),("B","D"),("B","E")]}
\annotate{t.node["B"]}{label="a below pill on an internal node", position=below, color=good}
```

Rendered at `/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/b6b798d6-92ae-4dfa-9982-9f3f2f1a33de/scratchpad/jz16/repro.tex` +
`repro.html`: leader `(115,300)→(114,310)`, pill rect `y=310` — a 10px
stub touching only the pill's top edge, matching the reporter's own
numbers (anchor bottom y≈126, pill y≈303, leader `(424,300)→(423,310)`,
same ~10px-stub shape). Direct-construction probe confirms the numbers
analytically for `t.node[B]`: `ay=150` (true anchor), `below_baseline=300`
— pre-fix, `_lead_oy` was pinned at 300, ~150px from the anchor that
should have been the leader's start.

## Root cause: order of computation

Trace of where a below-pill's final geometry is decided, in call order:

1. `PrimitiveBase.emit_annotation_arrows` (`base.py:1436`, the sole caller
   of `emit_position_label_svg`) resolves `target_box =
   self.resolve_annotation_box(target)` (`base.py:1676-1678`) — the
   target's own AABB — and `_cursor_aware_below_baseline()`
   (`base.py:1701`, pre-fix) — the shape-global below-lane Y. Both are
   passed down as `cell_width=` and `below_baseline=`.
2. Inside `emit_position_label_svg`, the `position == "below"` placement
   branch (`_svg_helpers.py:3726-3734`) computes the pill's *final* Y using
   `below_baseline` when present: `final_y = below_baseline +
   _LABEL_LANE_GAP + pill_h / 2`. This is the correct, already-fixed (JZ-12/
   15) displacement — not part of this bug.
3. The R-07/R-08 automatic-leader block (`_svg_helpers.py:3814-3846`, gated
   on `_pill_spans_neighbours = cell_width is not None and pill_w >
   cell_width + 1.0`) computes the leader's origin *independently* of step
   2's placement math, via the buggy `_lead_oy` line quoted above — it does
   not consult how far `below_baseline` actually sits from `ay` or from the
   target's own box before deciding to use it.

So the reporter's hypothesis — "stub length is CONSTANT — leader computed
before/independent of the reservation pass that moves the pill" — is
correct in effect, though the precise mechanism is not a temporal
ordering bug (both quantities are computed in the same call, from the
same already-displaced `below_baseline`) but a **missing distance check**:
the leader-origin formula assumes `below_baseline` is always "close
enough" to the anchor to look intentional, an assumption JZ-12/15 never
had to hold (they only needed the pill's own final position, not a
leader's visual plausibility).

## Working-vs-broken path comparison

Two leader mechanisms coexist in `emit_position_label_svg`, and only one
is broken:

- **R-07/R-08 automatic leader** (`_svg_helpers.py:3814-3846`, unconditional,
  fires whenever `_pill_spans_neighbours`): solid line, `stroke-width="0.75"
  stroke-opacity="0.45"`, no dot. **This is the broken path** — the
  `_lead_oy` formula quoted above.
- **R-37 explicit `leader=true` connector** (`_svg_helpers.py:3880-3902`,
  opt-in via the annotation's `leader=true` key): dotted line
  (`stroke-dasharray="2,3"`) plus an anchor `<circle r="2">` dot,
  unconditionally rooted at the raw, unclipped anchor point `(ax, ay)`.
  **This path is correct today** and is the "already-working" geometry the
  reporter refers to ("`leader=true` pills elsewhere already span
  correctly").

The fix converges the broken path onto the working path's origin
convention (the raw anchor) — but only when the lane is "displaced" from
the target; see Family-surface probe table below. Notably, the R-07/R-08
code *already* falls back to `ay` today whenever `position != "below"` or
`below_baseline is None` (the trailing `else: ay` in the buggy line) — so
the correct behavior is not new geometry to invent, it is the existing
`else` branch, broadened to also fire for "below" pills whose lane is far
from the target.

### Above/side pills: structurally never part of the broken family

Two items from the original Phase-1 family-surface list resolve by direct
code reading, no probing required:

- **`position="above"` pills** never relocate to a shared lane at all — by
  design there is no "above lane" (comment at `_svg_helpers.py:3714-3723`).
  Every above-pill placement is anchor-relative, so the buggy condition
  (`below_baseline is not None and position == "below"`) is structurally
  `False` for them; they already use `else: ay` unconditionally, today.
- **`position="left"`/`"right"` (side) pills** (`_svg_helpers.py:3735-3740`):
  same reasoning — always anchor-relative, never baseline-relocated.

Both families are confirmed **not broken** and require no fix.

## Family-surface probe table

Discriminating test: compare the target's own box bottom edge
(`resolve_annotation_box(target).y + .height`) against `below_baseline`.
An earlier hypothesis compared the raw anchor `ay` against `cell_height`
instead; it misclassified Bar (`ay` is the bar's *top* edge, not a
center — Bar doesn't override `resolve_label_anchor`, so it inherits the
generic anchor convention) and DPTable's 1D mode. Switching to the box
bottom edge — unambiguous regardless of a primitive's anchor convention —
fixed both misclassifications and produced a clean split:

| Case | anchor `ay` | `below_baseline` | target box bottom | gap | classification |
|---|---|---|---|---|---|
| Array cell | — | snug | — | 0 | snug |
| Bar (any bar, any height) | top edge | snug | = baseline always | 16 | snug |
| DPTable 1D cell | — | snug | — | 34 | snug |
| Tree leaf node | — | snug | — | 10 | snug |
| Grid bottom-row cell | — | snug | — | 0 | snug |
| Matrix bottom-row cell | — | snug | — | 0 | snug |
| DPTable 2D bottom-row cell | — | snug | — | 16 | snug |
| Graph bottom node | — | snug | — | 0 | snug |
| Hypercube bottom node | — | snug | — | 0 | snug |
| **Tree internal node** (`t.node[B]`) | 150.0 | 300.0 | 170.0 | **130** | **displaced** |
| **Grid top-row cell** (`g.cell[0][0]`) | 20.0 | 124.0 | 40.0 | **84** | **displaced** |
| **Matrix top-row cell** (`m.cell[0][0]`) | 12.0 | 99.0 | 24.0 | **75** | **displaced** |
| **DPTable 2D top-row cell** (`dp.cell[0][0]`) | 20.0 | 182.0 | 40.0 | **142** | **displaced** |
| **Graph top node** (`G.node[A]`) | 20.0 | 300.0 | 40.0 | **260** | **displaced** |
| **Hypercube top node** (`L.subset[7]`) | 28.0 | 258.0 | 48.0 | **210** | **displaced** |

Worst snug case: 34px (DPTable 1D). Best displaced case: 75px (Matrix top
row). 41px of clean margin — `_LEADER_SNUG_GAP = 50` (spec-fix doc) sits in
the middle of that gap.

**Forest** is a partial family member: it has a `resolve_below_baseline()`
override (so its below-pills do relocate to a shared lane) but **no**
`resolve_annotation_box()` override, so `cell_width` is never fed to
`emit_position_label_svg` and `_pill_spans_neighbours` never fires — no
automatic leader is drawn for Forest at all, snug or displaced. This is a
pre-existing, separately-tested convention (`test_primitive_codepanel.py`
documents the identical shape for CodePanel: *"gets lane mode but NO
leader (no resolve_annotation_box)"*), not a bug this investigation
surfaces — see spec-fix doc's Forest pin test.

## Threshold contract search

Grepped `docs/` for `leader`. Two hits, both for the **opt-in `leader=true`
key** (R-37), not the automatic R-07/R-08 leader this bug concerns:
`docs/SCRIBA-TEX-REFERENCE.md:476` (parameter table entry) and `:1697`
(the `color="state:X"` + `leader=true` worked example). Neither documents
a "snug vs. displaced" contract for the automatic leader — no existing
documented threshold to conform to or contradict.

One adjacent, *different* mechanism exists in the same file:
`_LEADER_DISPLACEMENT_THRESHOLD = 20.0` (`_svg_helpers.py:134`, R-07 per
`tests/unit/test_w3_batch1.py`), consumed by `emit_arrow_svg` — the
**arrow-annotation** renderer (`arrow_from=`/`arrow=true` pills), a
completely different function and annotation type than
`emit_position_label_svg`'s **position-only** pills (no arrow). That
threshold decides *whether to draw a leader at all* on an arc/arrow pill
when its visual gap from the natural position exceeds a scale-relative
formula (`visual_gap >= natural_gap + pill_h`); it does not decide a
leader's *origin point*, and it does not apply to `position="below"` pills
without an arrow. It is not reused or extended by this fix — a new,
purpose-specific constant (`_LEADER_SNUG_GAP`, spec-fix doc) is warranted
rather than overloading a threshold that governs a different decision on a
different code path. Both constants now coexist in `_svg_helpers.py`,
documented distinctly.

## Out of scope (explicit)

- **Forest's zero-leader behavior** — pre-existing, matches the
  CodePanel-documented convention; left alone (see above).
- **`emit_arrow_svg` / arrow annotations** (`arrow_from=`, `arrow=true`) —
  a different annotation type with its own, already-thresholded leader
  logic (`_LEADER_DISPLACEMENT_THRESHOLD`); the bug report and repro are
  specifically position-only pills (no arrow), and this mechanism was not
  found to share the defect.
- **R-37's `leader=true` explicit connector** — already correct (the
  convergence target for this fix), untouched.

## Handoff

Fix, tests (RED→GREEN), GitNexus impact analysis, and golden-corpus
verification are in the companion spec-fix doc:
`_bmad-output/implementation-artifacts/spec-fix-judgezone-16-leader-span.md`.
