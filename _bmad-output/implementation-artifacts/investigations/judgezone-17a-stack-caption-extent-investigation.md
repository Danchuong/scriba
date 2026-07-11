# Investigation: JudgeZone #17 Finding A — Stack Caption Escapes the Cross-Frame Extent at Max Depth

**Agent:** bmad-17a-extent
**Status:** ROOT CAUSE CONFIRMED, FIXED — see companion spec-fix doc for fix, tests, and regression evidence.
**Spec-fix doc:** `_bmad-output/implementation-artifacts/spec-fix-judgezone-17a-caption-extent.md`
**Sibling:** JudgeZone #17 Finding B (live controls chip content clearance) — owned by
concurrent agent `bmad-17b-chrome`, `scriba-embed.css`/`_html_stitcher.py` chrome
regions. Not touched by this investigation; see Scope fences below.
**Also sibling of:** the 0.30 viewBox-honesty contract (declared viewBox must bound
everything actually painted) and JudgeZone #15 (`spec-fix-judgezone-15-top-band-reservation.md`,
`_top_band_layout()`'s documented fix for the analogous TOP-caption/arrow-lane
double-anchor bug in tree/forest/graph). This finding is the BOTTOM-caption
counterpart of that same bug family, isolated to one primitive: Stack.

## Verdict

**CONFIRMED, with an exact trigger config** — not a cross-frame timeline-prescan
defect as the reporter's own theory proposed, but a single-frame, self-contained
double-count in `stack.py`'s caption placement arithmetic. It requires only:

- a `Stack` with a `label=` (caption), and
- **any** annotation that reserves nonzero space above the content frame
  (`position="above"`, or any other annotation shape that makes
  `_reserved_arrow_above() > 0`).

Caption line count, `max_visible`, and stack depth are **not** part of the
mechanism — they are correlates in the reporter's own repro, not causes. See
Reframing note below.

## Trigger config (exact)

```
\shape{s}{Stack}{max_visible=8, label="<any caption>"}
...
\apply{s}{push=...}   # any number of pushes, including up to max_visible
\annotate{s.item[N]}{label="...", position=above}
```

The bug fires the instant `_reserved_arrow_above() > 0` for that Stack, on
whichever frame the annotation is visible. Wrapping the caption to 2 lines is
**not required** — a single-line caption reproduces identically (see Empirical
proof). Confirmed non-triggers: a `Stack` with a caption and **no** annotation
at all (§Reframing note); a `Stack` with only `position="below"`/`"left"`/`"right"`
annotations (these never populate `_reserved_arrow_above`, see Code trace).

## Code trace

### The double-count

`scriba/animation/primitives/stack.py`, pre-fix:

- `bounding_box()` (lines 263–297) computes the declared viewBox height by
  accumulating content height, then caption height, then
  `arrow_above = self._reserved_arrow_above(); h += arrow_above`, then the
  below-lane reservation. **`arrow_above` is an additive term inside
  `bbox.height`.**
- `emit_svg()` (lines 299–465) recomputes the identical
  `arrow_above = self._reserved_arrow_above()` at line 334, then — if
  `arrow_above > 0 or left_pad > 0` — opens `<g transform="translate({left_pad},
  {arrow_above})">` at line 339. Every subsequent paint call in `emit_svg`
  (content, caption, cursors, annotation arrows) executes **inside** this
  group, in **local** coordinates that are already shifted down by
  `arrow_above` once the group closes at line 463.
- The caption emission (pre-fix, lines ~426–441) computed:

  ```python
  top_y=int(bbox.height - self._caption_block_height(content_w))
  ```

  This is a **local** coordinate, inside the `translate(_, arrow_above)`
  group. But `bbox.height` already has `arrow_above` baked in as an additive
  term. So the caption's **absolute** bottom edge works out to:

  ```
  abs_bottom = arrow_above (the group shift)
             + top_y                                  (local coordinate)
             + caption_height
             = arrow_above + (bbox.height - caption_height) + caption_height
             = arrow_above + bbox.height
  ```

  i.e. the caption paints **exactly `arrow_above` px past the declared
  viewBox height**, independent of caption line count, `max_visible`, or
  below-lane content — those terms all cancel out of the derivation above.

### JudgeZone #15 precedent — same bug family, opposite edge

`_top_band_layout()` (`base.py:601–619`) documents fixing the mirror-image
version of this exact bug class for TOP-anchored captions: a caption band and
an arrow-pill lane both anchoring at the outer frame origin, double-counting
the shift. This finding is the bottom-edge sibling, confined to Stack.

## Cross-primitive precedent matrix

Every primitive whose `top_y` (or equivalent) formula references `bbox.height`
directly is a structural candidate for this bug. Audited all 12 primitives with
a Layer-A caption (`_CAPTION_MIGRATED`):

| Primitive | `top_y` formula basis | `- arrow_above` (or equivalent) present pre-investigation? |
|---|---|---|
| `bar.py` (468–479) | `bbox.height`-relative | **Yes** — already fixed |
| `hashmap.py` (375–386) | `bbox.height`-relative | **Yes** — already fixed |
| `hypercube.py` (388–397) | `bbox.height`-relative | **Yes** — already fixed |
| `linkedlist.py` (482–493) | `bbox.height`-relative | **Yes** — already fixed |
| `queue.py` (515–529) | `bbox.height`-relative | **Yes** — already fixed (`_arrow_height_above`) |
| `variablewatch.py` (404–413) | `bbox.height`-relative | **Yes** — already fixed |
| **`stack.py` (426–441)** | `bbox.height`-relative | **No — sole outlier. This bug.** |
| `array.py` (610–638) | content-relative (`resolve_below_baseline() + lane_h + gap`) | N/A — never susceptible |
| `tracetable.py` (439–448) | content-relative (`_content_height(...) + lane_h + gap`) | N/A — never susceptible |
| `grid.py` | content-relative | N/A — never susceptible |
| `dptable.py` | content-relative | N/A — never susceptible |
| `matrix.py` | content-relative | N/A — never susceptible |
| `numberline.py` | content-relative | N/A — never susceptible |

Six of seven primitives using the `bbox.height`-relative formula already
carry the `- arrow_above` (or renamed equivalent) correction, with an
identical explanatory comment in `hashmap.py`/`linkedlist.py`/`variablewatch.py`:

```python
# minus arrow_above: the caption is emitted INSIDE the
# translate(_, arrow_above) group, so anchoring at raw
# bbox.height painted it arrow_above px PAST the bbox
# bottom, eating the inter-primitive gap.
```

`stack.py` was the sole primitive missing this correction — a regression or
oversight isolated to one file, not a fresh design flaw across the caption
system. The five content-relative primitives were never susceptible to this
bug class at all: their `top_y` is derived from the content's own resolved
baseline, never from the outer `bbox.height`, so there is no additive term to
double-count.

## Reframing note: not a cross-frame timeline-prescan bug

The reporter's own theory: *"the timeline-max prescan reserves the tallest
stack correctly, but the caption riding below is under-reserved... wrap seems
to happen after measurement."* This attributes the defect to the **cross-frame**
prescan step (the mechanism that measures every frame's Stack and reserves the
tallest one so the animation's viewBox doesn't jump between steps).

This investigation finds the actual mechanism is **entirely single-frame**:
reproducible with one static `Stack.emit_svg()` call, no animation timeline, no
prescan, no frame comparison involved at all (see Empirical proof, direct
construction). `bounding_box()` — the function the cross-frame prescan calls to
measure each frame — is **not defective**; it already includes `arrow_above`
correctly (confirmed unedited in this fix). The defect is entirely inside
`emit_svg()`'s caption placement, which uses that already-correct `bbox.height`
inconsistently with the coordinate space it emits into.

The reporter's max_visible/depth correlation is explained without invoking the
prescan: an annotation (`position=above`) is far more likely to appear on the
step where the stack is deepest (the "interesting" moment in a push/pop
narration), so `arrow_above > 0` and max-depth co-occur in real documents by
authoring habit, not by a depth-triggered mechanism. The identical −10px
overflow the reporter measured at both `max_visible=8` and separately at
`max_visible=3` is consistent with this: both scenes likely carry the same
(or same-sized) annotation, producing the same fixed `arrow_above`, independent
of stack depth — exactly what the derivation above predicts (`abs_bottom =
arrow_above + bbox.height`, with no depth or `max_visible` term at all).

The single-line-caption "clips descenders (−6…−9px)" symptom the reporter
separately reports is the same mechanism at a smaller magnitude: a smaller
`arrow_above` (e.g. from a shorter/simpler annotation) produces a
smaller-but-still-nonzero overflow, exactly proportional to whatever
`_reserved_arrow_above()` resolves to for that scene — not a distinct bug, not
evidence of wrap-timing at all.

## Empirical proof

### Direct construction (single frame, no timeline)

```python
s = Stack("s", {"items": [1, 2, 3], "label": "a caption long enough that it wraps onto a second display line every time"})
s.set_annotations([{"target": "s.item[2]", "label": "top marker", "position": "above"}])
```

Pre-fix: `bbox.height=189`, `arrow_above=18`, caption's real absolute bottom =
207 — overflow = 18, exactly `arrow_above`, exactly as derived above.

### Cross-frame timeline render (matches reporter's `max_visible=8` exactly)

To confirm the bug is not an artifact of single-instance construction, and to
directly test the reporter's own cross-frame framing, rendered a full 8-step
push timeline via the real pipeline (`render.py`, the same entry point the
golden-corpus test harness uses), with a `position=above` annotation added on
the final (max-depth) step:

```
\shape{s}{Stack}{max_visible=8, label="a caption that wraps into two lines under the stack"}
... 8x \apply{s}{push=...} ...
\annotate{s.item[7]}{label="top marker", position=above}   # only on step 8
```

Rendered once against pre-fix code (`git stash`) and once against the fixed
code, both via `SCRIBA_ALLOW_ANY_OUTPUT=1 python3 render.py <tex> -o <html>`:

| | outer viewBox | max-depth frame caption abs. bottom | overflow |
|---|---|---|---|
| Pre-fix | `254 502` | ≈518 | **≈16px past the 502 viewBox** |
| Post-fix | `254 502` (byte-identical) | ≈500 | within viewBox |

The outer viewBox is **byte-identical** between the two renders — direct
confirmation that `bounding_box()`/the cross-frame prescan is untouched and
was never the defective component. Every other frame in the same render (the
7 steps without the annotation) is **byte-identical** between pre-fix and
post-fix, confirming the fix is surgical: it only moves output for frames
where `arrow_above > 0`. A second control render of the same 8-step timeline
with **no** annotation at all (`arrow_above == 0` throughout) is byte-identical
pre-fix vs. post-fix across all 16 caption occurrences in the stitched
HTML — confirming the fix is a true no-op whenever the trigger ingredient
(a nonzero-`arrow_above` annotation) is absent, exactly as the derivation
predicts (subtracting 0 changes nothing).

Renders and analysis script retained at
`/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/b6b798d6-92ae-4dfa-9982-9f3f2f1a33de/scratchpad/jz17/`
(`repro8_annotated.tex`, `repro8_annotated-prefix.html`, `repro8_annotated-postfix.html`,
`analyze_frame.py`).

## Out of scope (explicit, per scope fences)

- **JudgeZone #17 Finding B** (live controls chip content clearance,
  `scriba-embed.css` / `_html_stitcher.py` chrome regions) — owned by
  concurrent agent `bmad-17b-chrome`. Confirmed via `git status` throughout
  this investigation that `scriba-embed.css` changes present in the working
  tree are not this agent's; this investigation's own diff touches only
  `stack.py` and `tests/unit/test_primitive_stack.py`.
- **`tex/*`** — not touched, not relevant to this finding.
- **The five content-relative primitives** (array, dptable, grid, matrix,
  numberline) and **tracetable** — confirmed never susceptible to this bug
  class; no fix needed, no test added for them.

## Handoff

Fix, tests (RED→GREEN), GitNexus impact analysis, golden-corpus
disambiguation, and full regression sweep are in the companion spec-fix doc:
`_bmad-output/implementation-artifacts/spec-fix-judgezone-17a-caption-extent.md`.
