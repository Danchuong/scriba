# Spec-Fix: JudgeZone #12 — Below-Cell Band Reservation (caret vs. caption)

**Agent:** fix-band (BMAD patcher)
**Status:** DONE — fix GREEN, regression swept, one real golden delta identified (not re-blessed, per scope).
**Investigation doc:** `_bmad-output/implementation-artifacts/investigations/judgezone-12-caret-caption-collision-investigation.md`
**Sibling:** JudgeZone #7 (`tests/unit/test_cursor_label_lane.py`) — anchored the caret's *origin* to the label lane. This fix is the mirror image: the *caption*'s placement never consulted the caret's *reach*.

## Contract

Every tenant of the below-cell band — index labels, the caret stack
(`▲` + id), a `position=below` annotation pill, and a `label=` caption —
must occupy a disjoint vertical interval. The caption's own top must
derive from the full occupied extent above it (a reservation), not a
constant that only ever accounted for annotation pills.

Root cause (confirmed): `caption_top` and the caret's apex both derive
from `resolve_below_baseline()`, but the caption's lane height
(`_below_lane_height()`) only measured annotation pills via
`annotation_below_overhang()` and never consulted `_cursor_extent_below()`
— so a bound R-38 caret's `▲` + id could paint inside the caption block.

Fix lives in the shared helper `_below_lane_height()` (`base.py`) so every
current and future tenant of the lane inherits it, rather than patching
each of the 5 confirmed-affected primitives (Array, Grid, DPTable, Queue,
Stack) independently.

---

## Work Item 1 (PRIMARY) — `scriba/animation/primitives/base.py`

### Fix

`scriba/animation/primitives/base.py:1105-1125` (`PrimitiveBase._below_lane_height`).

**Before** (pre-fix, `git show HEAD:...` — 12 lines):

```python
    def _below_lane_height(self) -> int:
        """Px reserved below ``resolve_below_baseline()`` for ``position=below``
        callout pills. 0 when nothing paints below the baseline (no-op for the
        common case). Shared by ``bounding_box``/caption placement of every
        primitive that opts into the lane.

        Exact painted extent below the baseline — includes downward collision
        nudges the retired ``position_below_lane_height`` formula never
        modelled."""
        baseline = self.resolve_below_baseline()
        if baseline is None:
            return 0
        return self.annotation_below_overhang(float(baseline))
```

**After** (current working tree — 21 lines):

```python
    def _below_lane_height(self) -> int:
        """Px reserved below ``resolve_below_baseline()`` for every tenant of
        the below-cell band — ``position=below`` callout pills AND a bound
        R-38 caret's ``▲`` + id. 0 when nothing paints below the baseline
        (no-op for the common case). Shared by ``bounding_box``/caption
        placement of every primitive that opts into the lane, so the
        caption's own top derives from the full occupied extent above it
        (a reservation) instead of only ever seeing the annotation pills.

        Exact painted extent below the baseline — includes downward collision
        nudges the retired ``position_below_lane_height`` formula never
        modelled. ``caret_reach`` is <= 0 (dropped by ``max``) whenever there
        is no bound caret, since ``_cursor_extent_below()`` is 0.0 and
        ``baseline`` is always positive — a caption-only frame is unaffected
        (JudgeZone #12)."""
        baseline = self.resolve_below_baseline()
        if baseline is None:
            return 0
        lane = self.annotation_below_overhang(float(baseline))
        caret_reach = math.ceil(self._cursor_extent_below() - float(baseline))
        return int(max(lane, caret_reach, 0))
```

Net diff: +14/-6 lines (docstring expanded to document the new term;
body adds `caret_reach` and folds it into the existing `lane` via `max`).
`math` was already imported at module scope (unused new import risk: none).

### Byte-stability guarantee

`caret_reach = ceil(_cursor_extent_below() - baseline)`. With no bound
cursor, `_cursor_extent_below()` returns `0.0` (base.py:932, confirmed
unconditional). `baseline` is always a positive float when not `None`
(cell geometry). So `caret_reach <= 0` whenever there is no caret, `max`
drops it, and `_below_lane_height()` returns exactly `lane` — identical to
pre-fix. This is asserted directly by
`TestNoCursorCaptionByteStable::test_caption_only_no_cursor_lane_unchanged`
and is why the fix is unconditional (not caption-gated): it costs nothing
for the overwhelming common case (no bound cursor on the shape at all).

---

## Work Item 2 (PRIMARY) — Tests: `tests/unit/test_below_band_lanes.py`

New file, 254 lines. Parse helpers reuse the exact SVG-band extraction
functions from the sibling fix's `tests/unit/test_cursor_label_lane.py`
(`_caret_body`, `_caret_apex_y`, `_caret_id_xy`, `_central_band`,
`_hanging_band`, `_index_label_y_at`) plus new caption-line-band and
pairwise-disjointness helpers (`_caption_line_bands`, `_disjoint`,
`_assert_all_disjoint`).

Matrix on Array: `{labels present/absent} × caption × bound cursor
(multi-char id "idx")`, plus a single-char-id spot check via the repro
fixtures below. Spot checks on Grid (stubbed `_cursor_extent_below`, since
Grid's R-38 targeting is 2D-only — see Regression risks), DPTable, Queue,
Stack — same shared helper, same contract.

### RED → GREEN (verified this session by physically swapping in the
pre-fix `base.py` from `git show HEAD:...`, running the suite, then
restoring the fix — md5-verified round-trip, not just narrated)

**RED** (`base.py` at committed HEAD `13eadc7`, no fix): **7 failed, 1 passed**.

| Test | Failure |
|---|---|
| `TestArrayBelowBandMatrix::test_caret_caption_and_index_all_disjoint[labels]` | `caret_triangle (72.0, 80.0) overlaps caption_line_0 (76.2, 87.2)` — **3.8px** |
| `TestArrayBelowBandMatrix::test_caret_caption_and_index_all_disjoint[no_labels]` | `caret_triangle (46.0, 54.0) overlaps caption_line_0 (50.2, 61.2)` — **3.8px** |
| `TestArrayBelowBandMatrix::test_no_caption_cursor_reserves_caret_reach_only` | `_below_lane_height()` doesn't yet fold in `caret_reach` (formula mismatch, no SVG overlap — caption absent) |
| `TestSpotChecksOtherPrimitives::test_grid_lane_height_reserves_caret_reach` | same formula mismatch (stubbed `_cursor_extent_below`) |
| `TestSpotChecksOtherPrimitives::test_dptable_caret_caption_disjoint` | `caret_triangle (80.0, 88.0) overlaps caption_line_0 (76.2, 87.2)` — **7.2px** |
| `TestSpotChecksOtherPrimitives::test_queue_caret_caption_disjoint` | `caret_triangle (96.0, 104.0) overlaps caption_line_0 (100.2, 111.2)` — **3.8px** |
| `TestSpotChecksOtherPrimitives::test_stack_caret_caption_disjoint` | `caret_triangle (138.0, 146.0) overlaps caption_line_0 (134.2, 145.2)` — **7.2px** |

The 1 pre-fix pass is `TestNoCursorCaptionByteStable` — the byte-stability
guard, which must (and does) hold on both sides of the fix by design.

**GREEN** (fix restored, md5-confirmed identical to the working copy):
**15 passed** (`test_below_band_lanes.py`'s 8 + sibling
`test_cursor_label_lane.py`'s 7, run together — the sibling fix's tests
are unaffected, confirming the shared-helper edit didn't regress report #7).

---

## Work Item 3 — Regression sweep

### Repro before/after (real DSL renders, not just unit tests)

4 fixtures rendered via
`SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py <tex> -o <out.html>`
— `jz12_repro.tex` (labels + caption + multi-char id `cab`),
`jz12_ctrlA_nocaption.tex` (no caption — nothing to protect),
`jz12_ctrlB_nolabels.tex` (caption, no index labels),
`jz12_ctrlC_singlechar.tex` (single-char id `c`, otherwise = repro).
Bands extracted with the same helpers as the unit tests.

| Fixture | viewBox h (pre→post) | Collisions pre-fix | Collisions post-fix |
|---|---|---|---|
| `jz12_repro` (labels+caption+`cab`) | 192 → **223** (+31) | triangle/cap0 3.8px, id/cap0 1.7px, id/cap1 7.3px | **none** |
| `jz12_ctrlA_nocaption` (no caption) | 188 → **189** (+1) | none | none |
| `jz12_ctrlB_nolabels` (caption, no labels) | 166 → **197** (+31) | triangle/cap0 3.8px, id/cap0 1.7px, id/cap1 7.3px | **none** |
| `jz12_ctrlC_singlechar` (single-char id `c`) | 192 → **223** (+31) | triangle/cap0 3.8px, id/cap0 1.7px, id/cap1 7.3px | **none** |

Confirms the bug (and fix) are independent of `labels=` presence and of
id length (`c` vs. `cab` — identical overlap magnitudes). `ctrlA` (no
caption) is the control: **zero collisions either side**, and the
viewBox still grows by 1px post-fix — this is the unconditional-reservation
side effect (see Regression risks), not a caption interaction.

### Golden corpus — corrected finding

An earlier text-grep pass (pre-compaction, this session) predicted 8
corpus files would shift (`dptable`, `kmp`, `binary_search`, `frog`,
`necessary_roads`, `range_queries_copies`, `elevator_rides`,
`test_reference_advanced`) based on "files combining `\cursor` and a
caption on the same shape." **This was wrong** and is superseded here.
Those files' `\cursor{shape.cell}{index}` calls use the legacy
2-argument positional form, which only highlights/colors a cell — it
never calls `set_cursors()`, never registers an R-38 bound caret, and is
invisible to `_cursor_extent_below()` (confirmed: zero occurrences of
`cursor[` or `aria-roledescription="cursor"` in `kmp.html` despite 27
`\cursor{...}` source invocations). The fix is a hard no-op for all 8.

**Verified instead via an isolated `git worktree add --detach ... HEAD`**
checkout (immune to the shared/dirty working tree — see Errors and
fixes below): unpatched golden suite = **108 passed**. With only this
session's `base.py` fix copied in = **107 passed, 1 failed**.

The one real regression: `tests/golden/examples/corpus/anim_clarity_showcase.tex`,
which uses the modern ID-bound caret form (`\cursor{a}{id=i, ...}`) on
two independent Array widgets, **neither of which has a caption**:

| Widget | Shape | viewBox (pre→post) | Downstream cascade |
|---|---|---|---|
| `id="ac"` ("Two-pointer...") | Array `a`, cursors `i`+`j`, no labels | 518×223 → 518×**224** | none observed |
| `id="sw"` ("Quét..." ) | Array `f`, cursor `k`, no labels | 332×183 → 332×**184** | `variablewatch` shape below it: `translate(62,102.5)` → `translate(62,103.0)` |

Both grow by exactly +1px, matching `jz12_ctrlA_nocaption`'s control
case exactly (no-caption, caret-reach rounds up past the bare baseline by
1px via `ceil`). Full uncapped diff of the rendered HTML (both widgets,
all steps, both the static SVGs and the embedded interactive-widget JS
`frames` array) confirmed via `diff` that **viewBox height and the one
downstream `translate` y are the only things that differ** — no text,
color, structural, or attribute changes anywhere else.

**Conclusion:** exactly one golden file needs re-blessing —
`anim_clarity_showcase` — for a pure +1px geometry shift with zero
content/structure impact. Per scope, **not re-blessed here**; that is
this file's finding to hand back, not an action taken.

---

## GitNexus impact analysis (run before editing, and re-verified this
session per repo `CLAUDE.md`'s mandate to surface HIGH/CRITICAL risk)

`impact(target="_below_lane_height", direction="upstream", file_path="scriba/animation/primitives/base.py", repo="scriba")`:

**risk CRITICAL, impactedCount 35** (23 direct, 12 at depth 2; 15 affected
execution processes; resolved to the exact target
`Method:...PrimitiveBase._below_lane_height#0`, run twice — pre- and
this-session — same result both times).

**This is real, not a name-collision false positive** — the assessment I
was carrying forward pre-compaction ("likely a method-name-collision
over-approximation") was wrong and is retracted here, replaced with a
mechanistic check: `grep -rn '_below_lane_height()' scriba/animation/primitives/*.py`
shows it is called directly from **17 primitive files**
(array, bar, codepanel, dptable, forest, graph, grid, hashmap, hypercube,
linkedlist, matrix, numberline, queue, stack, tracetable, tree,
variablewatch) — every one of which overrides `resolve_below_baseline()`
to return a real (non-`None`) baseline. The R-38 bound-cursor machinery
(`_cursor_extent_below()`/`emit_cursors_under`) is itself **generic and
base-class-provided** — it works for any primitive whose cell selectors
resolve through `resolve_annotation_point`/`resolve_label_anchor`, which
is the same general addressing mechanism `position=` pills use. Only
NumberLine and Stack need bespoke overrides for non-standard cell
addressing; nothing else special-cases it. So the fix's `caret_reach`
term is structurally reachable from all 17 callers, not just the 5
primitives (Array, Grid, DPTable, Queue, Stack) this task scoped tests to.

**Mitigating evidence** (why this is not treated as blocking):

1. The fix is a provable byte-stable no-op for any primitive/frame with
   zero bound cursors — the overwhelming majority of real usage (see
   byte-stability guarantee above).
2. Empirically, across the **entire** golden corpus (108 fixture tests,
   isolated-worktree-verified), only the one file above changes — no
   hashmap/linkedlist/graph/tree/bar/codepanel/hypercube/forest/tracetable
   fixture currently combines a bound cursor with a below-lane baseline
   deep enough to move the `max()`.

**Residual, honestly-scoped risk:** the 12 primitives outside this task's
tested set (bar, codepanel, forest, graph, hashmap, hypercube, linkedlist,
matrix, tracetable, tree, variablewatch, and numberline's own bespoke
cursor path) are reachable by the same code path but **untested by this
work** — this was out of the task's explicit scope ("Array... plus spot
checks on Grid, Queue, Stack, DPTable"). A future `\cursor`+caption
combination on one of those 12 could hit the same class of latent
under-reservation this fix closes for the 5 tested primitives, or could
newly grow a diagram's layout the way `anim_clarity_showcase` did. Flagging
for team-lead's call: extend the test matrix to all 17 callers, or accept
given the corpus evidence.

---

## Regression risks

- **Unconditional-reservation cascading growth** — confirmed real, not
  theoretical. `_below_lane_height()` grows by the caret's rounding
  remainder even with **no caption present** (`jz12_ctrlA_nocaption`:
  +1px; `anim_clarity_showcase`: +1px on two independent widgets). Since
  this feeds `bounding_box()`, it can shift the position of *other*
  shapes stacked below a primitive in a multi-primitive `\diagram`/story
  scene — confirmed exactly once, in `anim_clarity_showcase`'s `variablewatch`
  shape (`translate` y +0.5px). This is a broader surface than direct
  caption-collision and is the mechanism behind the one golden delta.
- **Grid 2D-cell-addressing DSL gap** (pre-existing, unrelated to this
  fix, discovered while writing the Grid spot check): the base class's
  default `_cursor_cell_suffix` only ever emits a flat `cell[N]`; Grid's
  R-38 targeting is 2D-only (`cell[row][col]`), so no scalar-index
  `\cursor` binding can resolve a Grid cell today — it soft-drops before
  painting. The Grid spot check exercises the fix directly by stubbing
  `_cursor_extent_below`, not through a real DSL-level Grid caret (none
  is currently reachable). Not this fix's bug to carry; noted for whoever
  owns the Grid cursor-targeting gap.
- **12 untested-but-reachable primitives** — see GitNexus section above.

## Errors and fixes (worth recording for sibling agents sharing this tree)

- **RTK hook corrupts redirected `git diff` output** — the user's global
  RTK CLI-proxy hook transparently rewrites `git diff ... > file.patch`
  into a lossy custom summary, not a real unified diff; unusable with
  `git apply`. Worked around with direct `cp` + `md5` checksum
  verification for all backup/restore/RED-vs-GREEN swaps in this task —
  immune to hook-level text reformatting, and every swap in this doc was
  md5-verified both ways.
- **Shared/dirty working tree** — this repo had several sibling BMAD
  agents committing uncommitted WIP to shared files
  (`scriba-scene-primitives.css`, `graph.py`, `plane2d.py`, etc.)
  concurrently with this task's testing. A same-tree golden-suite run
  is unreliable (observed swings from 30→107 failures between runs
  minutes apart, entirely from others' WIP). Fixed by testing against an
  isolated `git worktree add --detach <path> HEAD` checkout — physically
  separate from the shared tree, immune to concurrent mutation — for the
  authoritative 108→107 golden result. Confirmed independently: a full
  `tests/unit` run in the (still-shared) main tree shows 3 unrelated
  failures (`test_group_label_obstacle`, `test_primitive_css_centering`,
  a flaky `test_recursive_dos` timing test that passes in isolation),
  all traced to other agents' in-progress `graph.py`/`plane2d.py`/CSS
  edits, none touching `base.py` or this fix's test file.

## Scope compliance

Touched only: `scriba/animation/primitives/base.py` (the
`_below_lane_height` region, lines 1105-1125) and
`tests/unit/test_below_band_lanes.py` (new file). No CSS, `plane2d.py`,
`tex/renderer.py`, `parser/*`, `_svg_helpers.py`, `_text_render.py`,
`animation/renderer.py`, `_frame_renderer.py`, or any of the 5 primitive
files themselves touched. No golden re-bless (`SCRIBA_UPDATE_GOLDEN` never
set), no version bump, no CHANGELOG edit, no commit.

---

## Sweep wave (wave 2)

**Agent:** sweep-band (BMAD sweep). **Status:** DONE — fix GREEN, no new
golden deltas. Closes the "12 untested-but-reachable primitives" residual
risk this artifact's wave-1 GitNexus section flagged for team-lead's call
above ("extend the test matrix to all 17 callers, or accept given the
corpus evidence") — this wave extends it.

Scope: the 11 named primitives outside wave 1's tested set (bar,
codepanel, forest, graph, hashmap, hypercube, linkedlist, matrix,
tracetable, tree, variablewatch — no `Formula*` primitive class exists, so
the mandate's "+ any formula shapes" catch-all is empty), plus a 4th
tenant on Array that wave 1 tested only pairwise: a `position=below`
annotation pill combined with caption + bound caret + index labels.

### Work Item 1 — Support matrix (code-verified, not doc-inferred)

Two independent grep sweeps across all of `scriba/animation/primitives/*.py`:

| Capability | Gate | Primitives |
|---|---|---|
| Caption / callout-lane (`label=` reserves a below-band) | overrides `resolve_below_baseline()` | All 17: array, bar, codepanel, dptable, forest, graph, grid, hashmap, hypercube, linkedlist, matrix, numberline, queue, stack, tracetable, tree, variablewatch |
| Bound R-38 caret paint (`\cursor{shape}{id=..., at=...}`) | calls `emit_cursors_under()` | Only 6: array, dptable, grid, numberline, queue, stack (Deque shares queue.py) |

**Every one of the 11 sweep-scope primitives has caption support and zero
cursor support.** Confirms and generalizes wave-1's Matrix/LinkedList/HashMap
claim to the full 11 — none of them call `emit_cursors_under`, and none
wire a `_cursor_cell_suffix` an R-38 binding could resolve against. Cross-
checked against docs §5.11's supported-shapes list (`docs/SCRIBA-TEX-REFERENCE.md:613-712`):
none of the 11 appear there either — code and docs agree.

Since the support matrix has **zero primitives satisfying "supports BOTH
bound cursors AND captions"** among the 11, there is no shape in this
sweep's scope where a real combo probe can even be constructed — the
combo-probe step (mandate item 2) degenerates to proving the fix is an
inert no-op for all 11, which Work Item 3 pins permanently.

**One flag, not fixed (outside this sweep's named 11 + no formula shapes
exist):** `numberline.py` is the 12th primitive in wave-1's "17 callers"
disclosure and satisfies **both** gates (`resolve_below_baseline()` docstring:
*"Y where `position=below` pills start"*; calls `emit_cursors_under`) — it
is structurally the same shape of risk as Array. It is not in this sweep's
named scope, so it was not probed or tested here, but Work Item 2's fix
(a single shared call site) applies to it automatically, same as it does
to Array. Flagging for team-lead's call, mirroring wave-1's own
Grid-2D-addressing-gap disclosure pattern rather than silently expanding
scope.

> **RESOLVED by team-lead (2026-07-10, same day):** NumberLine probed
> directly (render: caret triangle 62–70, id glyph ≈74.5–87.5, caption
> ≈95.3–109 — disjoint, ~7.5px clearance; scratchpad
> `jz12_numberline.tex`) and pinned permanently as
> `TestSpotChecksOtherPrimitives::test_numberline_caret_caption_disjoint`
> (22/22 green). All 12 wave-1-disclosed callers are now either
> combo-tested (Array, Grid via stub, DPTable, Queue, Stack, NumberLine)
> or pinned no-cursor-no-op (the sweep's 11). Family closed.

### Work Item 2 (PRIMARY) — Two real bugs found and fixed via one shared-helper edit

Probed the 4th tenant (mandate item 4) on Array — `position=below` pill +
bound caret + caption + index labels together, both same-cell and
different-cell placements. Both configurations overlapped pre-fix:

| Probe | Overlap found |
|---|---|
| Pill on the **same** cell as the caret | `caption_line_0 (107.2, 118.2)` overlaps `below_pill (105.0, 124.0)` — 13.2px |
| Pill on a **different** cell than the caret | `caret_triangle (72.0, 80.0)` overlaps `below_pill (76.0, 95.0)` — 4.0px |

Root cause, both bugs trace to the same single call site —
`emit_annotation_arrows`'s `below_baseline=self.resolve_below_baseline()`
(the sole `below_baseline=` construction in the codebase; confirmed via
`grep -rn "below_baseline=" scriba/animation/primitives/*.py`):

- **Same-cell:** `array.py`'s paint order is caption → caret → pill.
  `_below_lane_height()`'s caption-height measurement runs through a
  *scratch* pass (`annotation_below_overhang` → `_measure_emit`) **before**
  the real paint call populates `_cursor_obstacle_boxes` for this frame
  (F2's same-column obstacle nudge). The caption never sees the pill's
  actual F2-nudged position, so it starts too early.
- **Different-cell:** F2's obstacle box is deliberately narrow — it spans
  only the caret's own column (`base.py`'s `emit_cursors_under`, `_Obstacle(...,
  x=cx, width=2.0*_CURSOR_HALF_W, ...)`). A pill on any *other* cell is
  never nudged and paints at the raw baseline, which sits inside the
  caret's own triangle+id band. This breaks the established Y-only
  (column-agnostic) disjointness contract this file's own docstring states
  — justified because a bound caret can **slide** between cells across
  steps, sweeping through every column's x at some point in the animation,
  so its Y-band must stay clear of every column's pill, not just its own.

**Fix** — `scriba/animation/primitives/base.py`, two edits:

1. New method, inserted between `resolve_below_baseline()` and
   `_below_lane_height()` (current lines 1106-1128):

   ```python
       def _cursor_aware_below_baseline(self) -> "float | None":
           """``resolve_below_baseline()``, pushed down to clear this frame's
           bound R-38 caret stack (``▲`` + id) when one resolves.
           ...
           """
           baseline = self.resolve_below_baseline()
           if baseline is None:
               return None
           return max(float(baseline), self._cursor_extent_below())
   ```

2. The one call site (line 1677) changed from
   `below_baseline=self.resolve_below_baseline(),` to
   `below_baseline=self._cursor_aware_below_baseline(),`.

This reuses the existing, self-contained `_cursor_extent_below()` (no new
resolution logic — the same helper wave-1's `_below_lane_height` fix
already folds in) and fixes both bugs simultaneously because the one call
site backs both the real paint pass and the scratch measurement pass.

**Byte-stability guarantee (same shape as wave-1's own):**
`_cursor_extent_below()` is 0.0 with no bound caret, and `baseline` is
always a positive float when not `None`, so `max(baseline,
_cursor_extent_below())` reduces to `baseline` — identical to pre-fix —
whenever there is no caret. This is why the 11-primitive support-matrix
finding (Work Item 1) makes the fix provably inert for all of them:
asserted directly by `TestSweepScopeNoCursorSupport` (Work Item 3).

**Probe verification** (`probe_triple_tenant2.py`, scratchpad) — pre-fix
both configurations overlap as tabulated above; post-fix both are `ALL
DISJOINT`, and `bounding_box` height grows 131→161px (+30px), which is
the caption correctly being pushed down to clear the now-properly-nudged
pill+caret stack — the same class of legitimate growth wave-1's own
Regression risks section already establishes as the expected cost of an
accurate reservation.

### GitNexus impact analysis (run before editing, per repo `CLAUDE.md`)

`impact(target="emit_annotation_arrows", direction="upstream", repo="scriba", summaryOnly=true)`:
**risk CRITICAL, impactedCount 32** (20 direct, 16 execution processes
affected, 2 modules) — expected for a hub function nearly every
primitive's `emit_svg` calls through. Not treated as blocking, for the
same structural reason wave-1's own CRITICAL finding on
`_below_lane_height` wasn't: the edit is at the one `below_baseline=`
construction site, gated by the same byte-stability guarantee above, and
Work Item 3's 11-primitive sweep is the direct empirical check that the
CRITICAL fan-out doesn't translate into behavior change for any primitive
without cursor support.

### Work Item 3 — Tests extended: `tests/unit/test_below_band_lanes.py`

+2 new imports block entries (11 primitive classes) and two new test
classes, 254 → 391 lines:

- **`TestSweepScopeNoCursorSupport`** — parametrized across all 11
  sweep-scope primitives. Constructs each with a long (wrapping) caption,
  once with no cursor and once with `set_cursors([...])` declared, and
  asserts the emitted SVG is **byte-identical**, with no
  `aria-roledescription="cursor"` markup and no `cursor[idx]` data
  attribute either way. This is the permanent pin for Work Item 1's
  finding and generalizes wave-1's own `TestNoCursorCaptionByteStable`
  beyond Array.
- **`TestArrayFourTenantDisjoint`** — parametrized `same_cell` /
  `different_cell`, promoting `probe_triple_tenant2.py`'s validated logic
  into a permanent regression test: caption + bound caret + index labels +
  a `position=below` pill, asserting all four bands pairwise-disjoint via
  the existing `_assert_all_disjoint` helper.

**Verification:**
`uv run pytest tests/unit/test_below_band_lanes.py tests/unit/test_cursor_label_lane.py tests/unit/test_multicursor.py -q -p no:cacheprovider`
→ **61 passed** (was 48 before this wave; +13 = 11 no-op pins + 2
four-tenant variants).

### Work Item 4 — Golden corpus (definitive, clean-room-isolated result)

The shared working tree made direct measurement misleading: running
`tests/golden/examples/ -q` in-place gave **107 failed, 1 passed**,
regardless of whether this wave's fix was applied, reverted, or `base.py`
was stashed back to committed HEAD entirely (three states, identical
count). Content-level inspection of a sample failure (`weird_algorithm`)
showed the divergence was a CSS dark-mode halo rule change stamped
*"wave-2 theme-attr sweep"* — unrelated sibling-agent theme work, not
Y-position logic. A second contamination source was found the same way:
`base.py`'s current working copy also carries an unrelated, unfinished
`ARROW_STYLES.get(...)` → `resolve_arrow_style(...)` refactor (defined in
`_svg_helpers.py`, itself dirty) from a different sibling agent — both
sources are outside this task's touched-files list and outside this
mandate's forbidden-files list (`_svg_helpers.py` explicitly so).

**Isolated the true signal** using wave-1's own documented technique
(`git worktree add --detach ... HEAD`), going one step further than a
worktree copy of the live (still-contaminated) `base.py`: reconstructed a
**clean-room `base.py`** — pristine committed HEAD with *only* wave-1's
documented `_below_lane_height` diff (from this artifact's own
Before/After blocks above) and *only* this wave's two edits applied on
top, string-matched and verified to contain zero occurrences of
`resolve_arrow_style`. Result:

| `base.py` state (isolated worktree, pristine HEAD elsewhere) | Result |
|---|---|
| Untouched (no JZ-12 code at all) | **108 passed** |
| Wave-1 diff + wave-2 diff only (clean-room) | **107 passed, 1 failed** |

The one failure is `anim_clarity_showcase` — **the same single file, same
`"sw"` widget, same exact +1px viewBox delta (`332×183 → 332×184`)** this
artifact's own wave-1 section already found, documented, and explicitly
deferred re-blessing on above ("not re-blessed here; that is this file's
finding to hand back, not an action taken"). Diffed the failure output
directly to confirm: no new content, structural, or geometry divergence
beyond that pre-existing, already-accepted delta.

**Conclusion: this wave's fix is a no-op on the golden corpus.** It adds
zero new deltas beyond wave-1's own already-known one. Per mandate scope,
still not re-blessed here — that remains wave-1's finding to hand back,
unchanged by this wave.

### Scope compliance (wave 2)

Touched only: `scriba/animation/primitives/base.py` (added
`_cursor_aware_below_baseline`, lines 1106-1128; changed one call site,
line 1677) and `tests/unit/test_below_band_lanes.py` (extended, +137
lines). No `_svg_helpers.py`, `_text_render.py`, `tex/renderer.py`,
`_frame_renderer.py`, or CSS touched, despite finding unrelated
in-progress edits to two of those files from other agents while
diagnosing the golden corpus (Work Item 4) — left untouched, not this
task's to fix. No golden re-bless, no version bump, no CHANGELOG edit, no
commit. Isolated worktree removed after use
(`git worktree remove --force`); main tree's `git status` for both owned
files confirmed clean of any other stray changes before and after.
