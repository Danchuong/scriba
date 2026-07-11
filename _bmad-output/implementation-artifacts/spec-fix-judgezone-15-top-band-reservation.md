# Spec-Fix: JudgeZone #15 — Top-Band Reservation (caption vs. above-pill)

**Agent:** bmad-15-topband
**Status:** DONE — fix GREEN, regression swept, zero golden corpus deltas identified.
**Investigation doc:** `_bmad-output/implementation-artifacts/investigations/judgezone-15-topband-caption-investigation.md`
**Sibling:** JudgeZone #7/#12 (`tests/unit/test_below_band_lanes.py`) — those fixes gave the **below**-cell band a shared reservation model (caret, pills, and caption all consult the same measured extent). This fix is the mirror image for the **top** band: Tree/Forest/Graph paint their `label=` caption ABOVE the content, and a `position=above` pill on a crown-ish node shares that same lane — no equivalent model existed for it before this fix.

## Contract

Every tenant of the top band — the `label=` caption and a `position=above`
annotation pill — must occupy a disjoint vertical interval, for any
primitive whose caption sits above its content (Tree, Forest, Graph).
Absent a caption, behavior must be byte-identical to the historical
single-frame formula (`ty = base_ty + arrow_above`, no inner content
shift).

Root cause (confirmed, see investigation doc Finding 2): pre-fix, the
caption painted through the *outer* transform (`ty = base_ty +
arrow_above`), so its absolute position grew linearly with
`arrow_above`; the pill painted through a *second*, nested
`translate(0, label_offset)` group, and because the pill's own natural
reach is `arrow_above` px above its anchor node, composing the two
transforms cancelled `arrow_above` out of the pill's absolute position
entirely — it always landed at `base_ty + label_offset`, regardless of
`arrow_above`. The caption had no such cancelling term, so a large
enough `arrow_above` pushed it down into the pill's fixed position.

Fix lives in a new shared helper, `_top_band_layout()` (`base.py`), so
all three current top-caption primitives inherit it from one edit
rather than three independent patches, and so any future top-caption
primitive gets the correct composition for free.

---

## Work Item 1 (PRIMARY) — `scriba/animation/primitives/base.py`

### Fix

New method, inserted directly after `_reserved_arrow_above()`
(`base.py:591-599`) and before `set_traces()`. Pure addition — no
existing `base.py` code was modified (`git diff --stat`: `base.py |
24 ++++++++++++++++++++++++`, 24 insertions, 0 deletions).

```python
    def _top_band_layout(
        self, base_ty: float, arrow_above: int, label_offset: int
    ) -> "tuple[float, int]":
        """Outer/inner ``ty`` split for a top-caption primitive (tree,
        forest, graph), so the caption band and the ``arrow_above`` pill
        lane stack in a fixed order instead of both anchoring at the outer
        frame's origin (JudgeZone #15).

        Without a caption (``label_offset == 0``) this is byte-identical to
        the historical shape: the outer frame absorbs ``base_ty +
        arrow_above`` and there is no inner content shift.

        With a caption, the caption paints at the outer frame using
        ``base_ty`` alone, so its position no longer drifts with
        ``arrow_above``; the pill lane instead folds into the inner content
        shift (``label_offset + arrow_above``), placing the caption band
        first and the pill lane immediately below it, ahead of the node
        content. Total reserved height is unchanged — this only reorders
        where each reservation is consumed.
        """
        if label_offset:
            return base_ty, label_offset + arrow_above
        return base_ty + arrow_above, 0
```

### Byte-stability guarantee

When `label_offset == 0` (no caption), the function returns `(base_ty +
arrow_above, 0)` — identical to every historical call site's inline
`ty = base_ty + arrow_above` with no inner group. This is asserted
directly by `test_no_caption_pill_path_byte_stable` in all three
consumer test classes (Work Item 3).

When a caption is present, the total reserved height is unchanged: pre-fix
the sum consumed across both transforms was `base_ty + arrow_above` (outer)
`+ label_offset` (inner) `= base_ty + arrow_above + label_offset`; post-fix
it is `base_ty` (outer) `+ (label_offset + arrow_above)` (inner) — the same
sum, just partitioned differently between the two transform depths. Only
the caption's *own* absolute position changes (it drops the `+
arrow_above` term); the pill's absolute position is provably invariant
under the repartition, since it is defined relative to the *sum* of both
transforms, not to either one individually — confirmed empirically below
(Work Item 4), where the pill band is bit-for-bit identical before and
after the fix in all three primitives.

---

## Work Item 2 (PRIMARY) — Consumers: `tree.py`, `forest.py`, `graph.py`

All three primitives share the identical structural change: compute
`label_offset` *before* the outer transform (previously computed after),
then call `_top_band_layout()` to get `(ty, content_shift)` instead of
inlining `ty = base_ty + arrow_above`, then gate the inner group on
`content_shift` instead of `label_offset`.

### `scriba/animation/primitives/tree.py` (`emit_svg`, `base_ty = r`)

**Before** (11 lines, opening block):

```python
        parts: list[str] = []
        # Offset by node radius so nodes at edge positions don't clip.
        # When annotations with arrows exist, shift content down by
        # arrow_above so curves have room above the tree.
        ty = r + arrow_above
        parts.append(
            f'<g data-primitive="tree" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({r + left_pad},{ty})">'
        )

        # Optional label / caption
        label_offset = 0
        if self.label is not None:
            content_w = float(self.width + 2 * r)
            label_offset = self._top_caption_band(content_w)
            self._emit_top_caption(
                parts,
                content_width=content_w,
                footprint_width=int(self.bounding_box().width),
                frame_radius=r,
                render_inline_tex=render_inline_tex,
            )

        # Shift edges + nodes below the label when present
        if label_offset:
            parts.append(f'<g transform="translate(0,{label_offset})">')
```

**After**:

```python
        # Optional label / caption geometry, computed before the outer
        # transform since ty depends on whether a caption will be painted.
        label_offset = 0
        if self.label is not None:
            content_w = float(self.width + 2 * r)
            label_offset = self._top_caption_band(content_w)

        parts: list[str] = []
        # Offset by node radius so nodes at edge positions don't clip. When
        # a caption is present, it paints at the outer frame (independent of
        # arrow_above) and the pill lane folds into the inner content shift
        # instead (see `_top_band_layout`); otherwise arrow_above is
        # absorbed by the outer frame directly, same as historically.
        ty, content_shift = self._top_band_layout(r, arrow_above, label_offset)
        parts.append(
            f'<g data-primitive="tree" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({r + left_pad},{ty})">'
        )

        if self.label is not None:
            self._emit_top_caption(
                parts,
                content_width=content_w,
                footprint_width=int(self.bounding_box().width),
                frame_radius=r,
                render_inline_tex=render_inline_tex,
            )

        # Shift edges + nodes below the label/pill lane when present
        if content_shift:
            parts.append(f'<g transform="translate(0,{content_shift})">')
```

The matching closing block changes `if label_offset:` to `if
content_shift:` before the final `</g>` pair. `git diff --stat`: 31 lines
changed.

### `scriba/animation/primitives/forest.py` (`emit_svg`, `base_ty = 0`)

Same shape, but Forest's outer transform has no `+r` term — its
`base_ty` argument to `_top_band_layout()` is `0` (the outer frame is
`left_pad`-only):

**Before** (opening block):

```python
        parts: list[str] = []
        parts.append(
            f'<g data-primitive="forest" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({left_pad},{arrow_above})">'
        )

        # Optional top-band caption (mirror Tree; content is shifted by
        # left_pad only, so frame_radius == left_pad centres it on the box).
        label_offset = 0
        if self.label is not None:
            content_w = float(self._envelope_width)
            label_offset = self._top_caption_band(content_w)
            self._emit_top_caption(
                parts,
                content_width=content_w,
                footprint_width=int(self.bounding_box().width),
                frame_radius=float(left_pad),
                render_inline_tex=render_inline_tex,
            )
        if label_offset:
            parts.append(f'<g transform="translate(0,{label_offset})">')
```

**After**:

```python
        # Optional top-band caption geometry, computed before the outer
        # transform since ty depends on whether a caption will be painted.
        label_offset = 0
        if self.label is not None:
            content_w = float(self._envelope_width)
            label_offset = self._top_caption_band(content_w)

        parts: list[str] = []
        # When a caption is present, it paints at the outer frame
        # (independent of arrow_above) and the pill lane folds into the
        # inner content shift instead (see `_top_band_layout`); otherwise
        # arrow_above is absorbed by the outer frame directly, same as
        # historically.
        ty, content_shift = self._top_band_layout(0, arrow_above, label_offset)
        parts.append(
            f'<g data-primitive="forest" data-shape="{_escape_xml(self.name)}"'
            f' transform="translate({left_pad},{ty})">'
        )

        # (mirror Tree; content is shifted by left_pad only, so
        # frame_radius == left_pad centres it on the box).
        if self.label is not None:
            self._emit_top_caption(
                parts,
                content_width=content_w,
                footprint_width=int(self.bounding_box().width),
                frame_radius=float(left_pad),
                render_inline_tex=render_inline_tex,
            )
        if content_shift:
            parts.append(f'<g transform="translate(0,{content_shift})">')
```

Closing block: `if label_offset:` → `if content_shift:`. `git diff
--stat`: 28 lines changed. `bounding_box()`'s height sum (`self.
_envelope_height + arrow_above + self._below_lane_height() + label_h`)
needed no change — the fix only reorders where reservations are
consumed, not the total.

### `scriba/animation/primitives/graph.py` (`emit_svg`, `base_ty = r`)

Identical structural pattern to Tree's (Graph shares the same `r +
left_pad` outer-frame shape). Same before/after transform as Tree's
Work Item 2 block above, applied at Graph's `emit_svg` opening block and
its matching `if label_offset:` → `if content_shift:` closing-block
change. `git diff --stat`: 28 lines changed.

---

## Work Item 3 (PRIMARY) — Tests: `tests/unit/test_top_band_lanes.py`

New file, 11 tests across 3 classes (`TestTreeTopBandDisjoint` (5),
`TestForestTopBandDisjoint` (3), `TestGraphTopBandDisjoint` (3)),
following the same shape as the JZ-12 precedent (`test_below_band_lanes.
py`): parse the real emitted SVG (transform attributes, `<rect>`/`<text
>`/`<tspan>` geometry), reconstruct each tenant's absolute painted band,
and assert every pair of tenants is disjoint.

### RED → GREEN

| Test | Pre-fix | Post-fix | Notes |
| --- | --- | --- | --- |
| `TestTreeTopBandDisjoint::test_pill_above_root_and_caption_disjoint` | FAIL | PASS | The reporter's exact repro shape. |
| `TestTreeTopBandDisjoint::test_wrapped_caption_still_disjoint_from_pill` | FAIL* | PASS | Long caption forcing `label_offset` past the 28px floor. *See note below — this test's failure was partly a test-authoring bug in this session's own new file, not only the product defect (see Errors and fixes). |
| `TestTreeTopBandDisjoint::test_deep_node_pill_no_reservation_needed` | PASS | PASS | Control: pill on a leaf node, `arrow_above == 0` — nothing to protect against, disjoint before and after by construction. |
| `TestTreeTopBandDisjoint::test_no_caption_pill_path_byte_stable` | PASS | PASS | Byte-stability guard: no caption → `outer_ty == r + arrow_above`, `inner_ty == 0.0`, unchanged by the fix. |
| `TestTreeTopBandDisjoint::test_caption_no_pill_path_matches_historical_formula` | PASS | PASS | Byte-stability guard: no annotation → `arrow_above == 0` → new and historical formulas coincide. |
| `TestForestTopBandDisjoint::test_pill_above_root_and_caption_disjoint` | FAIL | PASS | Forest analogue of the repro. |
| `TestForestTopBandDisjoint::test_no_caption_pill_path_byte_stable` | PASS | PASS | Byte-stability guard (`outer_ty == arrow_above`, Forest's `base_ty = 0`). |
| `TestForestTopBandDisjoint::test_caption_no_pill_path_matches_historical_formula` | PASS | PASS | Byte-stability guard (`outer_ty == 0.0`). |
| `TestGraphTopBandDisjoint::test_pill_above_top_node_and_caption_disjoint` | FAIL | PASS | Graph analogue, node pinned near the frame origin. |
| `TestGraphTopBandDisjoint::test_no_caption_pill_path_byte_stable` | PASS | PASS | Byte-stability guard (`outer_ty == r + arrow_above`). |
| `TestGraphTopBandDisjoint::test_caption_no_pill_path_matches_historical_formula` | PASS | PASS | Byte-stability guard (`outer_ty == r`). |

Pre-fix baseline: 4 failed, 7 passed. Post-fix (current working tree):

```
$ uv run pytest tests/unit/test_top_band_lanes.py -v
...
11 passed in 0.19s
```

**Note on `test_wrapped_caption_still_disjoint_from_pill`:** this test's
own `_caption_bands_abs()` helper initially approximated a multi-line
caption `<tspan>`'s band as `(y, y + font)`, treating the SVG baseline
`y` as the glyph's visual top — wrong for default (non-central) text
baseline positioning. This produced a false-positive failure
independent of whether the source fix was applied. Corrected by
importing `ASCENDER_RATIO`/`DESCENDER_RATIO` from `scriba.animation.
primitives.layout` and adding an `_alphabetic_band(y, font)` helper
(`y - ASCENDER_RATIO*font, y + DESCENDER_RATIO*font`) — the exact,
already-battle-tested formula `test_below_band_lanes.py` uses for the
same code path (its own JZ-12-authored `_alphabetic_band` helper).
After the correction, the test passes both because the source fix is
correct and because the test now measures the real painted band
accurately. See Errors and fixes for the full account.

---

## Work Item 4 — Regression sweep

### Repro before/after (real DSL-equivalent constructions, not just assertions)

Measured via direct primitive construction + `emit_svg()` (no
Playwright — static SVG parsing only, per task constraint), using the
exact reporter repro (Tree) and matching Forest/Graph analogues.

| Primitive | `arrow_above` | Caption band (pre-fix) | Pill band (pre/post, unchanged) | Caption band (post-fix) | Pre-fix overlap | Post-fix gap |
| --- | --- | --- | --- | --- | --- | --- |
| Tree (reporter's repro) | 18 | (48.5, 59.5) | (49.0, 69.0) | (30.5, 41.5) | 10.5px | 7.5px clear |
| Forest (analogue) | 12 | (22.5, 33.5) | (29.0, 63.0) | (10.5, 21.5) | 4.5px | 7.5px clear |
| Graph (analogue, top-pinned node) | 28 | (58.5, 69.5) | (49.0, 69.0) | (30.5, 41.5) | 10.5px | 7.5px clear |

Two things confirmed empirically here, matching the Work Item 1 byte-stability
argument exactly: (1) the pill's band is bit-for-bit identical pre- and
post-fix in all three primitives — the fix genuinely never moves the pill;
(2) the caption moves up by exactly `arrow_above` in each case (e.g. Tree:
48.5 → 30.5, a shift of 18, matching Tree's own `arrow_above` of 18) — the
fix removes exactly the term that was causing the drift, nothing more. The
post-fix gap is a constant 7.5px across all three because in each of these
repros `label_offset` is pinned at the historical 28px single-line floor
(short, non-wrapping captions), and the caption's own painted bottom edge
sits a fixed 7.5px inside that floor regardless of `arrow_above` — consistent
with `test_wrapped_caption_still_disjoint_from_pill` (Work Item 3) separately
confirming the fix also holds once a long caption pushes `label_offset`
past the 28px floor.

### Regression suite

```
$ uv run pytest tests/unit/test_below_band_lanes.py -q      # JZ-12 regression guard
22 passed in 0.19s

$ uv run pytest tests/unit/ -k "tree or forest or graph" -q  # broader existing suite
642 passed, 3810 deselected, 5 warnings in 10.43s
```

The 5 warnings are pre-existing and unrelated to this fix (graph
nodes-with-no-edges lane placement, one invalid-selector warning in a
`test_nodefit.py` case) — none touch top-band caption or annotation
placement.

### Golden corpus — scan methodology and result

The fix changes output only when a Tree/Forest/Graph shape has **both**
`label=` set **and** a `position=above` annotation targeting that same
shape's node at any step. A precise Python regex scan (not a bare
`grep`, which produced a false positive on an earlier pass — see Errors
and fixes) over `tests/golden/examples/corpus/*.tex` found:

```
files with a labeled Tree/Forest/Graph shape: 7
candidates (same-shape position=above on a labeled shape): 0
```

Zero golden fixtures exercise the combination this fix changes output
for — the entire golden corpus is expected to render byte-identical
before and after this fix. This was not verified by running the golden
suite itself (out of scope per task constraint — targeted tests only);
it was verified by static scan of the fixture source, cross-checked
against `_apply_min_arrow_above()`'s scoping (`_html_stitcher.py:160-
192`, read-only, not modified), which confirmed `arrow_above` is scoped
strictly per-shape (filtered by `target.startswith(shape_name + ".")`),
never influenced by other shapes' annotations in the same scene —
validating that the scan's per-shape, cross-step matching is the
correct and sufficient scope for this fix's blast radius.

---

## GitNexus impact analysis

Run before editing each function, and re-run after, per this repo's
`CLAUDE.md` mandate.

| Symbol | File | Pre-edit | Post-edit |
| --- | --- | --- | --- |
| `Tree.emit_svg` | `tree.py` | LOW, impactedCount 0 | LOW, impactedCount 0 |
| `Forest.emit_svg` | `forest.py` | LOW, impactedCount 0 | LOW, impactedCount 0 |
| `Graph.emit_svg` | `graph.py` | LOW, impactedCount 0 | LOW, impactedCount 0 |
| `PrimitiveBase._top_band_layout` (new) | `base.py` | N/A (didn't exist) | "Target not found" — brand-new symbol, GitNexus index not yet refreshed |

No HIGH or CRITICAL risk at any point. `_top_band_layout` not resolving
post-edit is expected (index staleness for a symbol added this session)
and is not a gap in the safety check: its only three callers are the
exact three `emit_svg` methods above, each independently confirmed LOW
both before and after.

`detect_changes(scope="all")` was also run and returned an elevated
risk finding, but this was traced to the concurrent agent
("fix-invariant")'s unrelated, uncommitted changes to
`_html_stitcher.py`/`renderer.py` in the same shared working tree —
confirmed via `git status --porcelain=v1 -uno`, which shows exactly 7
modified files, only 4 of which (`base.py`, `forest.py`, `graph.py`,
`tree.py`) belong to this fix. This is the same shared/dirty-working-
tree hazard the JZ-12 spec-fix doc already flagged for sibling agents;
the correct mitigation (used here) is to assess risk via direct
per-symbol `impact()` calls on exactly the symbols this fix touches,
not via a whole-tree `detect_changes` scan.

---

## Regression risks

- **Low overall risk.** The change is a pure reordering of which
  transform depth carries `arrow_above` vs. `label_offset`; total
  reserved height is unchanged (Work Item 1's byte-stability argument),
  confirmed empirically (Work Item 4: pill bands bit-for-bit identical
  pre/post-fix).
- **Byte-stability for the no-caption and no-pill paths is covered by
  dedicated regression-guard tests** (`test_no_caption_pill_path_byte_
  stable`, `test_caption_no_pill_path_matches_historical_formula`, all
  three primitives) — both pass unchanged before and after this fix, by
  design.
- **Zero golden corpus impact**, per the scan above — no fixture
  combines a labeled Tree/Forest/Graph shape with a same-shape
  `position=above` annotation.
- **Not independently verified:** any primitive outside Tree/Forest/
  Graph. Confirmed by grep that only these three call `_top_caption_
  band`/`_emit_top_caption` — no other primitive is exposed to this
  helper or this bug class.
- **Not addressed (explicitly out of scope):** the Forest wrap-width
  measurement divergence and the `\group`-label top-band gap noted in
  the investigation doc's Out-of-scope Observations — neither is
  touched by this fix, and neither regresses because of it (both are
  pre-existing, independent of `_top_band_layout`).

---

## Errors and fixes (worth recording for sibling agents sharing this tree)

- **Test-file band-approximation bug, self-caught, not a product bug.**
  This session's own new `_caption_bands_abs()` helper in `test_top_
  band_lanes.py` initially used `(y, y + font)` for multi-line/`<tspan>`
  caption bands, which treats the SVG baseline as the glyph's visual
  top — wrong for default (non-central) baseline text. This produced a
  false-positive failure in `test_wrapped_caption_still_disjoint_from_
  pill` even though the source fix was already correct. Fixed by
  importing `ASCENDER_RATIO`/`DESCENDER_RATIO` from `scriba.animation.
  primitives.layout` and adding an `_alphabetic_band()` helper matching
  the one already battle-tested in `test_below_band_lanes.py` (the
  JZ-12 precedent file) for the identical code path. Lesson: when
  porting a band-disjointness test pattern to a new lane, port the
  exact baseline-approximation helper too, not a simplified
  reconstruction of it.
- **`detect_changes(scope="all")` mixed in a concurrent agent's
  unrelated changes**, reporting an elevated risk that had nothing to
  do with this fix. Resolved by cross-checking `git status --porcelain=
  v1 -uno` (exactly 7 modified files, only 4 belonging to this fix) and
  re-running `impact()` directly on the three specific symbols changed
  — clean LOW results for all three. Same hazard the JZ-12 spec-fix doc
  already documented; recorded again here since this session hit it
  independently in a differently-shared working tree.
- **An early, informal `grep`-based golden-corpus check produced a
  false-positive candidate** (a broken shell pipeline mis-extracted a
  shape ID as the literal word "shape"). Replaced with a precise Python
  regex scan using proper capture groups; the one former false positive
  (`test_reference_edge_cases.tex`) was manually re-checked and
  confirmed to have no `position=above` annotation anywhere in the
  file — the scan's zero-candidate result is real, not an artifact of
  a looser check.

---

## Scope compliance

Files modified by this fix, confirmed via `git diff --stat`:

- `scriba/animation/primitives/base.py` (+24/-0 — new `_top_band_layout` helper only)
- `scriba/animation/primitives/tree.py` (31 lines changed)
- `scriba/animation/primitives/forest.py` (28 lines changed)
- `scriba/animation/primitives/graph.py` (28 lines changed)
- `tests/unit/test_top_band_lanes.py` (new file, 11 tests)

Explicitly NOT touched, per task constraints:

- `scriba/animation/_html_stitcher.py` — owned by the concurrent agent "fix-invariant" this session; read-only referenced (`_apply_min_arrow_above`, lines 160-192) to validate the golden-corpus scan's scoping assumption, never edited.
- `scriba/animation/static/scriba-scene-primitives.css` — owned by the same concurrent agent.
- `scriba/tex/renderer.py`, any `_grammar_values.py` — out of scope per task constraints.
- No version bump, no `CHANGELOG.md` edit, no commit, no golden re-bless.
- No Playwright/browser MCP tools used anywhere in this investigation or fix — all verification via direct Python-API primitive construction, static SVG string parsing, and `pytest`.
- Test runs were targeted only (`test_top_band_lanes.py`, `test_below_band_lanes.py`, and a `tree|forest|graph` keyword-filtered subset of `tests/unit/`) — the full golden corpus suite was not run; its impact was assessed by static scan instead, per task constraints.

---

## Sweep wave

Follow-up sweep closing the JZ-15 family's residuals: every other decoration
that can rise above the topmost content row on Tree/Forest/Graph, the Forest
wrap-width divergence flagged (not actioned) by the original investigation,
and a completeness check confirming no other primitive is silently exposed
to this bug class. Four work items; all four resolved (three fixed/pinned,
one deferred with a written root cause).

### Tenant × primitive matrix

| Decoration | Tree | Forest | Graph | Verdict |
|---|---|---|---|---|
| `\annotate` pill, `position=above` | pre-existing JZ-15 fix | pre-existing JZ-15 fix | pre-existing JZ-15 fix | Re-confirmed clean (primary fix, not this wave) |
| `\annotate ... arrow_from=True` | n/a | n/a | n/a | **PINNED** — arrow-to-target is a paint detail *inside* the same pill already measured by `annotation_height_above()`; no independent reach, no new reservation needed |
| `\cursor` | n/a | n/a | n/a | **NOT APPLICABLE** — DSL command isn't supported on Tree/Forest/Graph (Array/Stack/Queue only; confirmed via grep — zero occurrences of `set_cursors`/multicursor machinery in any of the three files) |
| `\group` hull/title-pill | n/a (Graph-only concept) | n/a | **FIXED** | `_group_extent_above()` |
| `\link` bow | **FIXED** | n/a (Tree-only concept) | n/a | `_link_extent_above()` |
| Antiparallel directed-edge bow | n/a | n/a | **FIXED** (defensive; analytically bounded safe already, see test class docstring) | `_antiparallel_extent_above()` |
| `\note{at=top-left/top-right}` | clean (`base_ty=r` pushes caption band down clear of the note) | **COLLIDES**, ~14px overlap | clean (`base_ty=r`) | Different mechanism (scene-level obstacle placer, not the top-band model) — out of a primitives-only fence, logged to `deferred-work.md` |

### Fixes made

All three follow the fix pattern established by the primary JZ-15 fix: a
primitive-specific `_xxx_extent_above() -> int` that returns 0 early when the
decoration is absent, applies the same visibility/state filtering as the real
emitter, tracks `worst = min(worst, y)` from `0.0`, and returns
`int(math.ceil(-worst)) if worst < 0 else 0`. Wired into
`arrow_above = max(self._reserved_arrow_above(), ..., self._xxx_extent_above())`
at both `bounding_box()` and `emit_svg()`.

- **`\group` hull/title-pill (Graph).** `_group_extent_above()` defined
  `scriba/animation/primitives/graph.py:1966`; wired at `graph.py:1817`
  (`bounding_box()`) and `graph.py:2219` (`emit_svg()`).
- **Tree `\link` bow.** `_link_extent_above()` defined
  `scriba/animation/primitives/tree.py:1009`; wired at `tree.py:1038`
  (`bounding_box()`) and `tree.py:1074` (`emit_svg()`).
- **Graph antiparallel directed-edge bow.** `_antiparallel_extent_above()`
  defined `scriba/animation/primitives/graph.py:2002`; wired at
  `graph.py:1818` (`bounding_box()`) and `graph.py:2220` (`emit_svg()`). Fixed
  defensively rather than left alone: the bow's fixed-constant reach
  (`ctrl_off = 2 * _ANTIPARALLEL_CURVE_OFFSET = 24`) vs. the unconditional
  node-y floor (`_PADDING = 20`) gives a worst-case exceedance of only
  `ceil(24 - 20) = 4px` against the caption lane's ~6.5px slack — never
  reachable in practice, but fixed anyway so the margin is an explicit,
  code-enforced reservation rather than a coincidence between constants that
  could silently invert if either is retuned later (see
  `TestGraphAntiparallelTopBandDisjoint`'s class docstring for the full
  derivation).

### Pins added (no code change; verified already-safe)

- **`arrow_from=True`** — architectural pin. It's a rendering detail of an
  `\annotate` pill (bezier stub + arrowhead painted inside the pill's own
  bounds), not an independent decoration class; `annotation_height_above()`
  already measures the pill's actual painted extent regardless of this flag.
  No new test class added — the primary fix's existing pill-disjoint tests
  already exercise plain pills through the same measurement path.
- **`\cursor`** — scope pin. Confirmed not a Tree/Forest/Graph feature at
  all (`forest.py`'s 5 `cursor` hits are its unrelated internal
  `x_cursor` root-placement variable, not the `\cursor` DSL command).

### Other top-band tenants — `\note` finding

Forest's caption legitimately sits ~20px higher than Tree/Graph's
(`_top_band_layout(0, ...)` vs. `_top_band_layout(r, ...)` — Forest has no
root-circle radius to push its outer transform down), which breaks an
assumption of roughly-fixed caption-band position baked into the *other*,
separate placement mechanism: `_scene_content_obstacles()`/`_place_pill()` in
`scriba/animation/_frame_renderer.py`, governing `\note`/`\link` cross-shape
bridges. Root-caused and reproduced (14px overlap, exact repro + coordinates
in the entry below); fix belongs outside `primitives/*.py`, so outside this
sweep's fence, and outside JZ-15's top-band reservation model itself (that
model is confirmed to govern only decorations painted *inside* a primitive's
own bbox — `\annotate` pills, `\group`, Tree `\link`, Graph antiparallel bows
— all four confirmed disjoint from captions above). Logged in full to
`_bmad-output/implementation-artifacts/deferred-work.md` under
"2026-07-11 — from JudgeZone #15 sweep wave (other top-band tenants)".

### Forest wrap-width verdict: DEFER

Reproduced end-to-end (real `emit_svg()` output), root-caused, and found to
be a **shared Tree/Forest/Graph `base.py`-pattern**, not Forest-specific as
the original investigation's Out-of-scope Observations first flagged — a
correction/sharpening of that framing, not a new independent bug. All three
primitives lock in the caption's word-wrap point (`_caption_lines`, via
`content_width=content_w`) *before* `\annotate` pill right-reach
(`_h_label_pad()`/`annotation_h_pads()`) is folded into the final
`footprint_width` used to center the caption — so when right-reach alone
exceeds the base content width, the caption can wrap a line earlier than the
final box needs. Cosmetic only (the box is always ≥ what it needs; only the
line-break choice is occasionally suboptimal), never a collision/clipping
bug. Verified on Forest (`content_w=320` vs. `bounding_box().width=415`,
wrap breaks after "wide" instead of the better "here") and confirmed the same
mechanism on Tree (`content_w=440` vs. `bbox.width=462`). Real fix reorders
`bounding_box()`/`emit_svg()` in all three files to compute `right_reach`
before the wrap decision — a shared-helper-level signature/ordering change
with a corpus-wide golden blast radius, sized beyond a sweep tack-on, same
call as the original investigation. Logged in full to `deferred-work.md`
under "2026-07-11 — from JudgeZone #15 sweep wave (Forest wrap-width
divergence, root-caused)".

### Completeness check: Tree/Forest/Graph confirmed complete and exclusive

Grepped every primitive for caption-on-top emission
(`grep -ln "self\.label\s*[:=]" scriba/animation/primitives/*.py`, 17 hits)
and classified each:

- **Tree, Forest, Graph** — the only three that call
  `_top_band_layout`/`_top_caption_band`/`_emit_top_caption` with a
  shiftable content frame independent of the caption's fixed outer frame.
  Complete top-band tenant set, per the matrix above.
- **14 bottom-anchored captions** (bar, array, equation, dptable, grid,
  hashmap, linkedlist, numberline, queue, matrix, stack, tracetable,
  variablewatch, hypercube) — `bounding_box()` height is built by
  *sequentially summing* `arrow_above + content + below_lane_height +
  caption_block_height` (e.g. `matrix.py`:
  `top_y=self._total_height() + self._below_lane_height() + _CAPTION_CLEAR_GAP`).
  An above-pill (top of box) and a below-caption (bottom of box) can never
  spatially overlap by construction — architectural proof, not a spot-check.
- **CodePanel** — `self.label` is a title-bar header, not the shared Layer-A
  caption block (no `_emit_caption(` call in the file anywhere). Its entire
  panel (background + header + content) lives inside one unconditional
  `<g transform="translate(left_pad, arrow_above)">` (`codepanel.py:281-282`)
  — the whole panel shifts down together; no fixed-vs-shiftable split exists
  to break. Immune by a different but equally solid construction.
- **MetricPlot, Plane2D** — no primitive-level `self.label` field at all
  (MetricPlot has only `xlabel`/`ylabel`/`ylabel_right` axis labels; Plane2D
  only has per-point/per-line/per-segment data labels). Out of scope, no
  caption to collide.

**Verdict: Tree/Forest/Graph are the complete and only set of primitives
needing the top-band reservation fix. No other primitive is silently exposed
to the JZ-15 bug class.**

### Regression tests added

All in `tests/unit/test_top_band_lanes.py` (25 tests total in the file now;
11 pre-existing from the primary fix + 14 added this wave):

- `TestGraphGroupTopBandDisjoint` (4): label/caption disjoint, no-caption
  stays in viewBox, extent matches an unlabeled hull's real apex, extent is 0
  without any `\group`.
- `TestTreeLinkTopBandDisjoint` (5): bow/caption disjoint, no-caption stays
  in viewBox, extent matches the bow's real apex, extent is 0 without any
  `\link`, extent is 0 when the bow points down (pins the safe direction used
  by the pre-existing `test_bounding_box_identical` fixture in
  `test_tree_links_charedges.py`).
- `TestGraphAntiparallelTopBandDisjoint` (5): bow/caption disjoint at the
  `_NODE_MIN_RADIUS` density floor, no-caption stays in viewBox, extent
  matches the curve geometry directly, extent is 0 without a reciprocal edge
  pair, extent is 0 when undirected.

Targeted regression re-run after the full wave (`test_top_band_lanes.py` +
`test_below_band_lanes.py` + a `tree or forest or graph` keyword-filtered
subset of `tests/unit/`): **47 passed** in the first two files; **591
passed** in the keyword subset, with one unrelated flaky failure
(`test_recursive_dos.py::TestCyclicGraphBaseline::test_graph_with_100_self_loops_completes`,
a wall-clock timing budget of 5.0s tripped to 5.19s under this session's
concurrent-agent machine load; passed 3/3 in isolation at 3.7-4.7s — not a
correctness regression, not touched by this wave's changes). Two unrelated
pre-existing collection errors skipped
(`test_graph_mutation.py`, `test_parser_hypothesis.py` — both fail at import
with `ModuleNotFoundError: No module named 'hypothesis'`, an environment gap
predating this session).

### Expected golden shifts: none, proven per fix

Rather than a blanket golden-suite diff (noisy this session — a concurrent
agent has unrelated in-flight changes to shared files), each fix's impact
was isolated by proof: monkeypatch the new `_xxx_extent_above()` method to
log `(extent, old_max_without_it)` on every call while rendering the real
fixtures that exercise it via `render_file()`. If `extent` never exceeds
`old_max_without_it`, `arrow_above` is provably unchanged, hence the
rendered SVG is provably byte-identical — no HTML diffing needed.

- **`\group`**: only fixture in the golden or doc_coverage corpus using
  `\group{` is `tests/doc_coverage/corpus/cmd_group_hull.tex` (verified via
  `grep -rl '\group{'` across both corpora's `.tex` sources) — 7 calls to
  `_group_extent_above()` across its animation steps, **0 changed**.
- **`\link`**: only fixture using `\link{` is
  `tests/doc_coverage/corpus/cmd_link_bridge.tex` — 4 calls, **0 changed**.
- **Antiparallel bow**: 19 directed-graph fixtures (12 from
  `tests/golden/examples/corpus/`, 7 from `tests/doc_coverage/corpus/`) — **0
  changed** across every call in every fixture.

Every real fixture in both corpora that can reach any of the three new
methods is accounted for; none shifts. No golden re-bless needed or performed.

### Sweep-wave scope compliance

- Modified: `scriba/animation/primitives/graph.py`,
  `scriba/animation/primitives/tree.py` (both already listed in Scope
  compliance above — this wave's additions land in the same files as the
  primary fix), `tests/unit/test_top_band_lanes.py` (14 new tests appended),
  `_bmad-output/implementation-artifacts/deferred-work.md` (2 new entries),
  this file (this section).
- Not touched: `scriba/animation/primitives/forest.py` (no fix needed there
  this wave — Forest's two findings are both deferred, not fixed),
  `_html_stitcher.py`, `scriba-scene-primitives.css`, any `tex/*` file, per
  the same fence as the primary fix.
- No version bump, no `CHANGELOG.md` edit, no commit, no golden re-bless, no
  Playwright/browser MCP tools. Tests run were targeted only, per the same
  constraint as the primary fix.
