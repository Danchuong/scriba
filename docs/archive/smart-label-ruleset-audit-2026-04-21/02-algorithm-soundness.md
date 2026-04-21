# Smart-Label Placement Algorithm — Soundness Audit

**Date**: 2026-04-21
**Subject**: `_nudge_candidates` and the collision-avoidance loop in
`scriba/animation/primitives/_svg_helpers.py`
**Spec reference**: `docs/spec/smart-label-ruleset.md` §2 (placement algorithm contract)
**Test class**: `tests/unit/test_smart_label_phase0.py::TestMW1EightDirectionGrid`

---

## Summary table

| # | Property | Status | Severity |
|---|----------|--------|----------|
| 1 | Termination | VERIFIED | — |
| 2 | Ordering stability | VERIFIED | — |
| 3 | Tie-break correctness | VERIFIED | — |
| 4 | Half-plane preference | VERIFIED | — |
| 5 | Step-size choice | UNSPECIFIED | LOW |
| 6 | Degenerate inputs | FALSIFIABLE (3 sub-cases) | MEDIUM / LOW |
| 7 | Registry append order | VERIFIED with caveat | LOW |
| 8 | Candidate coordinate system | VERIFIED | — |
| 9 | Clamp interaction | FALSIFIABLE | MEDIUM |
| 10 | Anchor correction | VERIFIED (with debug-capture caveat) | — |

---

## 1. Termination

**Status**: VERIFIED

The nudge loop is a bounded `for` loop over a finite generator:

```python
# _svg_helpers.py line 541 (emit_plain_arrow_svg) / line 882 (emit_arrow_svg)
for ndx, ndy in _nudge_candidates(float(pill_w), float(pill_h), side_hint=anchor_side):
    test = _LabelPlacement(...)
    if not any(test.overlaps(p) for p in placed_labels):
        candidate = test
        resolved = True
        break
if not resolved:
    # QW-2: all 32 candidates exhausted — keep last position.
    collision_unresolved = True
```

`_nudge_candidates` yields exactly 32 items (8 × 4) and returns. The generator
never loops indefinitely and the `for` loop carries a `break` on the success
path. If none of the 32 candidates is collision-free, `resolved` stays `False`
and the loop terminates naturally at generator exhaustion.

**Fallback path when all 32 collide**: `candidate` is never updated inside the
loop (the assignment `candidate = test` only executes when `not overlaps`).
Therefore `candidate` retains its value from the assignment at line 534/873:

```python
# emit_plain_arrow_svg line 534-535
candidate_y = final_y - l_font_px * 0.3
candidate = _LabelPlacement(x=final_x, y=candidate_y, ...)
```

The fallback position is the **natural (pre-nudge) position**, not the last
tested candidate. This is intentional and matches the QW-2 rule in
`docs/spec/smart-label-ruleset.md` §2: "fallback to last candidate" means
"last accepted candidate", which here is the initial one (since none was
accepted from the grid). The label is registered at the natural position and
`collision_unresolved = True` triggers the debug comment if
`SCRIBA_DEBUG_LABELS=1`.

**emit_position_label_svg** uses a different loop structure (lines 1301-1318):
a bounded `for _ in range(4)` that tries 4 fixed directions at a single step
size. It also terminates in at most 4 outer iterations × 4 inner directions =
16 calls. No infinite loop is possible.

---

## 2. Ordering stability

**Status**: VERIFIED

Potential non-determinism sources examined:

**`set` usage** (`_svg_helpers.py` line 191):
```python
preferred_set = set(_SIDE_HINT_PREFERRED[hint_key])
```
This `set` is used **only** as a membership predicate (`c[2] in preferred_set`),
not iterated. The filter lists `preferred` and `other` are built by iterating
`all_candidates`, which is a `list` assembled in a deterministic nested loop:

```python
for step in steps:           # (0.25h, 0.5h, 1.0h, 1.5h) — tuple, fixed
    for priority, (dx_sign, dy_sign) in enumerate(_COMPASS_8):  # tuple, fixed
        all_candidates.append((dx, dy, priority))
```

`steps` is a 4-tuple, `_COMPASS_8` is a module-level tuple. The enumerate
index `priority` is a tie-break key only; it does not affect list construction
order. The final `sorted(...)` call uses a deterministic key
`(_manhattan(c), c[2])`, both of which are floats/ints with no randomness.

**`dict` key order** (`_SIDE_HINT_PREFERRED`): dictionary key order is
insertion-order-guaranteed since Python 3.7. The repo targets Python 3.10+
(`sys.version: 3.10.20`). `_SIDE_HINT_PREFERRED` is a module-level literal
dict; lookup is by string key, not iteration. No ordering issue.

**Empirical confirmation**: calling `_nudge_candidates(40, 20)` twice yields
identical lists on the same process. The test `test_deterministic_order` in
`TestMW1EightDirectionGrid` (line 967) also locks this in at the test level.

---

## 3. Tie-break correctness

**Status**: VERIFIED

Spec contract (§2.1): *"Within the same Manhattan distance, candidates follow
the fixed priority: N, S, E, W, NE, NW, SE, SW."*

Empirical output at `pill_h=10` (steps produce distances 2.5, 5.0, 10.0, 15.0
for cardinals; 5.0, 10.0, 20.0, 30.0 for diagonals):

**Distance group 2.5 (step-1 cardinals only):**
```
index 0: (0.0, -2.5)   N
index 1: (0.0,  2.5)   S
index 2: (2.5,  0.0)   E
index 3: (-2.5, 0.0)   W
```
Order matches N → S → E → W exactly.

**Distance group 5.0 (step-2 cardinals + step-1 diagonals):**
```
index 4:  (0.0,  -5.0)  N
index 5:  (0.0,   5.0)  S
index 6:  (5.0,   0.0)  E
index 7:  (-5.0,  0.0)  W
index 8:  (2.5,  -2.5)  NE
index 9:  (-2.5, -2.5)  NW
index 10: (2.5,   2.5)  SE
index 11: (-2.5,  2.5)  SW
```
Within this distance group, cardinals precede diagonals (priority indices 0–3
sort before 4–7). The tie-break is implemented correctly as `priority_index`
in the `sorted` key `(_manhattan(c), c[2])`.

**Note on diagonal Manhattan**: diagonal candidates use `step × (1, 1)`, so
their Manhattan distance is `2 × step`, equal to a cardinal at `step × 2`. At
distance 5.0, step-2 cardinals (index 0–3) share a bucket with step-1 diagonals
(index 4–7). The sort correctly places cardinals before diagonals within the
bucket because `c[2]` (priority index) is 0–3 for cardinals and 4–7 for
diagonals.

---

## 4. Half-plane preference

**Status**: VERIFIED

When `side_hint="above"`, `_SIDE_HINT_PREFERRED["above"] = (0, 4, 5)` selects
compass indices N (0), NE (4), NW (5). These are exactly the three directions
with `dy_sign = -1` in `_COMPASS_8`. The preferred set has
3 directions × 4 steps = **12 candidates**; the other set has
5 directions × 4 steps = **20 candidates**.

Empirical output for `side_hint="above"` (pill_h=20):
```
First 4: [(0.0, -5.0), (0.0, -10.0), (5.0, -5.0), (-5.0, -5.0)]
```
All have `dy < 0`. The full preferred block occupies indices 0–11, all with
`dy < 0`. The first S-direction candidate (pure South, `dy > 0, dx == 0`)
appears at index 12, after all 12 preferred candidates.

```
Last upper-half index: 11
First S candidate index: 12
Result: VERIFIED — all upper-half before first S
```

**E and W are not in the preferred group for `"above"`**. They appear in the
other group at indices 13, 14, 16, 17, 21, 22, 26, 27. This matches the spec
comment at line 118: *"Neutral directions (E/W for above/below) are included
in the 'other' group that comes second."*

The test `test_side_hint_above_upper_first` (line 935) checks `candidates[:4]`
for `dy < 0`, which is a weaker assertion than the full block. The full block
guarantee (all 12 upper-half candidates precede any non-upper-half candidate)
is verified empirically here but not tested at the level of all 12.

---

## 5. Step-size choice

**Status**: UNSPECIFIED (no rationale documented in spec or code)

The step multipliers `(0.25, 0.5, 1.0, 1.5)` applied to `pill_h` produce
these Manhattan distances:

| Step | Cardinal dist | Diagonal dist |
|------|-------------|--------------|
| 0.25 | 0.25 h | 0.50 h |
| 0.50 | 0.50 h | 1.00 h |
| 1.00 | 1.00 h | 2.00 h |
| 1.50 | 1.50 h | 3.00 h |

The distinct Manhattan levels covered are: `0.25, 0.5, 1.0, 1.5, 2.0, 3.0`
(in units of `pill_h`). Ratios between adjacent levels: 2.0, 2.0, 1.5, 1.33,
1.50 — non-uniform. The progression is not geometric.

At `pill_h = 20 px`, the minimum non-zero step is `5 px` and the maximum is
`30 px`. A diagonal at step-4 produces a 42-pixel displacement — large enough
to clear most realistic label clusters. However, the step from 1.0h to 1.5h
is only 50% growth (vs 100% for the previous two steps), meaning the two
largest step sizes have diminishing separation.

**Comparison with alternatives**:

*Pure geometric doubling* `(0.25, 0.5, 1.0, 2.0)`: covers Manhattan levels
`0.25, 0.5, 1.0, 1.5, 2.0, 4.0`. Max displacement at `pill_h=20` is 40 px
(cardinal step-4) or 57 px (diagonal step-4). Better tail coverage.

*`(0.3, 0.6, 1.0, 1.6)` near-geometric*: almost identical coverage to current
but with slightly more aggressive fine-grain (0.3h vs 0.25h) and coarser tail
(1.6h vs 1.5h). No clear advantage.

**Recommendation**: document the rationale in `_svg_helpers.py` at line 170.
If the design intent is "try small nudges first before large ones", the current
choice is reasonable. If the intent is "guarantee escape from a cluster of
width up to W", a geometric progression provides better coverage guarantees.
Neither is wrong; the gap is documentation, not code.

---

## 6. Degenerate inputs

### 6a. `pill_h = 0` — FALSIFIABLE (silent corruption)

**Status**: FALSIFIABLE (severity: MEDIUM)

When `pill_h = 0`, `steps = (0, 0, 0, 0)` and all 32 candidates are `(0.0, 0.0)`.
The generator yields 32 identical tuples, all zero-displacement:

```
pill_h=0 => 32 candidates, first few: [(0.0, -0.0), (0.0, -0.0), ...]
```

In the nudge loop each test `_LabelPlacement` has zero height. Two zero-height
pills with the same center do not technically overlap (the AABB test uses strict
`<` for the gap condition, not `<=`):

```python
# _LabelPlacement.overlaps line 87-92
return not (
    self.x + self.width / 2 < other.x - other.width / 2
    or ...
    or self.y + self.height / 2 < other.y - other.height / 2
    ...
)
```

With `height = 0`: `self.y + 0 < other.y - 0` → `self.y < other.y`. If both
labels have the same y, this is `False`, so `not False = True` → they DO
overlap. But with zero nudge candidates the loop finds nothing and keeps the
natural position. No exception is raised and the emitter proceeds to render an
invisible (zero-height) pill. The label text is still emitted but its `pill_rx`
calculation `int(fi_y - 0 - font*0.3)` produces a non-zero value; the rect is
emitted with height 0, which is valid SVG but visually wrong.

**Root cause**: `pill_h = 0` only occurs if `_LABEL_PILL_PAD_Y = 0` and
`line_height = 0` (i.e. `l_font_px = 0`). These are constants, so the degenerate
case requires a malformed `label_size` style entry in `ARROW_STYLES`. This is
unlikely in production but could surface if `ARROW_STYLES` is externally
patched in tests.

**Repro**:
```python
from scriba.animation.primitives._svg_helpers import _nudge_candidates
candidates = list(_nudge_candidates(0, 0))
# Returns 32 copies of (0.0, 0.0) — no useful candidates
assert all(dx == 0 and dy == 0 for dx, dy in candidates)  # passes
```

**Recommendation**: add a guard at line 170: `if pill_h <= 0: return` with a
fallback to a default step (e.g. 8 px), or assert `pill_h > 0` upstream before
calling `_nudge_candidates`.

### 6b. `pill_h` very large (pill_h > viewBox height) — UNSPECIFIED

When `pill_h > viewBox_height`, step-1 candidates at `0.25 × pill_h` may
already land outside the viewBox. The clamp only handles the x-axis (QW-3);
there is no y-axis clamp. A pill with `final_y + pill_h/2 > viewBox_height`
will render partially off the bottom edge. The `arrow_height_above` helper
mitigates this for labels above y=0, but there is no equivalent guard for
labels that grow below the bottom edge. This is a known gap noted in
`docs/spec/smart-label-ruleset.md` §2.3 and is out of scope for this audit.

### 6c. `side_hint` with invalid/empty string — VERIFIED (silent coerce)

```
_nudge_candidates(40, 20, side_hint='diagonal')  == _nudge_candidates(40, 20)
_nudge_candidates(40, 20, side_hint='')          == _nudge_candidates(40, 20)
```

Line 183 coerces: `hint_key = side_hint if side_hint in _SIDE_HINT_PREFERRED else None`.
Unknown hints silently fall back to the no-hint path. This is correct behaviour
and matches the docstring: *"When side_hint is None or unknown, all 32 candidates
are sorted by Manhattan distance."* No assertion or warning is emitted. This is
acceptable given the docstring is clear; a development-mode warning could help
catch typos in annotation dicts.

---

## 7. Registry append order

**Status**: VERIFIED with caveat

**Processing order** is defined in `base.py` `emit_annotation_arrows` (line 383):

```python
placed: list[_LabelPlacement] = []
for ann in annotations:          # line 383 — iterates self._annotations
    ...
    emit_plain_arrow_svg(..., placed_labels=placed)   # or
    emit_arrow_svg(..., placed_labels=placed)          # or
    emit_position_label_svg(..., placed_labels=placed)
```

`self._annotations` is set via `set_annotations` (line 299), which stores the
caller-supplied list directly:

```python
def set_annotations(self, annotations: list[dict[str, Any]]) -> None:
    self._annotations = annotations
```

No sorting or deduplication occurs. The registry is built in the same order as
the annotation list passed by the author.

**First-placed-wins confirmed empirically**: two annotations targeting the same
cell with the same natural label position:

```
Order [A, B]: A registered y=32.70, B registered y=12.40
Order [B, A]: B registered y=32.70, A registered y=12.40
```

When the order is reversed, the annotation that was first gets the natural y;
the second is nudged. This means **reordering `\annotate` calls in the source
changes the visual output** when any two labels share an overlapping natural
position.

**Caveat**: this is documented behaviour (first-placed-wins is the stated
policy in §2.2 "Registry is append-only"). However, it is not mentioned in any
user-facing spec or error message. Authors who encounter overlapping labels and
reorder their annotations to "fix" one overlap may inadvertently create another.
Adding a note to the Starlark `\annotate` documentation would help.

---

## 8. Candidate coordinate system

**Status**: VERIFIED

The `(dx, dy)` offsets yielded by `_nudge_candidates` are applied to the
**pill geometric center**, not to the top-left corner of the pill rect.

Evidence from `emit_plain_arrow_svg` (lines 531–551):

```python
candidate_y = final_y - l_font_px * 0.3          # geometric center y
candidate = _LabelPlacement(x=final_x, y=candidate_y, ...)

for ndx, ndy in _nudge_candidates(...):
    test = _LabelPlacement(
        x=final_x + ndx,      # center + dx
        y=candidate_y + ndy,  # center + dy
        ...
    )
```

The `_LabelPlacement` dataclass stores `(x, y)` as geometric center
coordinates (the `overlaps` method treats them this way: `self.x ± self.width/2`).
The pill rect's top-left is reconstructed from the center at render time:

```python
# line 578
pill_rx = max(0, int(fi_x - pill_w / 2))
pill_ry = int(fi_y - pill_h / 2 - l_font_px * 0.3)
```

**Consistency**: `emit_arrow_svg` (lines 873–908) and
`emit_position_label_svg` (lines 1289–1329) use the identical pattern. All
three functions are consistent: `(dx, dy)` are center-space offsets throughout.

Empirical confirmation:
```
final_y (text anchor y) = 70.50
l_font_px = 11
Registered y (candidate.y) = 67.20 = 70.50 - 11*0.3  ✓
pill_ry (top of rect) = 57.70 = 70.50 - 19/2 - 3.3   ✓
```

---

## 9. Clamp interaction

**Status**: FALSIFIABLE — confirmed repro

**Bug description**: QW-3 x-clamp (`clamped_x = max(final_x, pill_w / 2)`)
is applied **after** the nudge collision check passes, and the **registered**
AABB uses `clamped_x`, not `final_x`. When a nudge candidate moves the label
to a negative x (off the left edge), the collision check passes because the
negative-x position does not overlap any registered label. But the subsequent
clamp shifts the center to `pill_w / 2`, which may land exactly on top of a
previously registered label near the left edge.

**Confirmed repro** (constructed geometry):

```python
from scriba.animation.primitives._svg_helpers import _nudge_candidates, _LabelPlacement

pill_w = 60.0
pill_h = 20.0
# First label: clamped to x=30 (left edge label)
first = _LabelPlacement(x=30.0, y=100.0, width=60.0, height=20.0)

# Second label natural position also near left edge, overlapping first
nat_x2 = -10.0
nat_y2 = 100.0

for i, (ndx, ndy) in enumerate(_nudge_candidates(pill_w, pill_h)):
    raw_x = nat_x2 + ndx       # e.g. candidate 23: -10 + (-30) = -40.0
    raw_y = nat_y2 + ndy
    test = _LabelPlacement(x=raw_x, y=raw_y, width=pill_w, height=pill_h)
    if not test.overlaps(first):          # test at (-40, 100): no overlap [passes]
        clamped_x = max(raw_x, pill_w/2)  # max(-40, 30) = 30
        registered = _LabelPlacement(x=clamped_x, y=raw_y, ...)
        if registered.overlaps(first):    # (30, 100) overlaps (30, 100)!
            # PROBLEM: clamp moved nudged pill back into collision
            break
```

Output from systematic search:
```
REPRO: nat=(-10, 100), cand 23 (-30.0, 0.0)
  pre-clamp (-40.0, 100.0): OK
  post-clamp (30.0, 100.0): OVERLAPS first at (30.0, 100.0)
```

**End-to-end repro via emit**:
```python
placed = []
emit_plain_arrow_svg([], {'target': 'a', 'label': 'ptr', 'color': 'info'},
                     dst_point=(5.0, 60.0), placed_labels=placed)
# First registered: x=16.00

placed2 = [placed[0]]
emit_plain_arrow_svg([], {'target': 'b', 'label': 'ptr', 'color': 'info'},
                     dst_point=(-5.0, 60.0), placed_labels=placed2)
# Second registered: x=16.00, y=27.20
# placed2[0].overlaps(placed2[1]) == True  ← confirmed
```

**Condition for triggering**: requires two labels near the left edge (`x < 0` or
`x < pill_w / 2`) where the second label's nudge search finds a candidate that
passes to negative x. In practice this needs the annotation target to be very
close to the left boundary of the SVG. It is unlikely in normal use but is a
formal soundness violation of I-4 ("Clamp never moves the pill off the
registered AABB").

**Fix**: run the collision check against the **clamped** position, not the raw
nudge position:

```python
# Replace the test in the nudge loop:
clamped_x_test = max(final_x + ndx, pill_w / 2)
test = _LabelPlacement(x=clamped_x_test, y=candidate_y + ndy, ...)
if not any(test.overlaps(p) for p in placed_labels):
    candidate = test
    ...
```

This ensures that the position checked equals the position registered.

---

## 10. Anchor correction (I-3)

**Status**: VERIFIED (with debug-capture caveat)

Spec I-3: *"candidate_y = final_y - l_font_px × 0.3 at construction;
final_y = candidate.y + l_font_px × 0.3 at render."*

### 10a. emit_arrow_svg (natural position)

Lines 873–899:
```python
candidate_y = final_y - l_font_px * 0.3          # construction
candidate = _LabelPlacement(x=final_x, y=candidate_y, ...)
# ... (nudge may update candidate) ...
final_y = candidate.y + l_font_px * 0.3           # render
```

Empirical:
```
final_y=36.0, l_font_px=12
registered y=32.40, expected=36.0 - 12*0.3 = 32.40  ✓
```

### 10b. emit_plain_arrow_svg (natural position)

Lines 532–557 — identical pattern:
```
final_y=70.5, l_font_px=11
registered y=67.20, expected=70.5 - 11*0.3 = 67.20  ✓
```

### 10c. emit_plain_arrow_svg / emit_arrow_svg (after nudge)

When nudge fires, `candidate` is updated to the accepted test position:
```python
candidate = test  # test has y=candidate_y + ndy
```
The reconstruct `final_y = candidate.y + l_font_px * 0.3` correctly gives the
post-nudge text anchor y. The invariant holds because `candidate.y` is always
set as `(some_y) - l_font_px * 0.3` (original construction) or as
`candidate_y + ndy` (nudge update), and the render line reconstructs
`final_y = candidate.y + l_font_px * 0.3`.

Empirical (nudge triggered):
```
registered y=38.70
actual final_y after nudge = 38.70 + 11*0.3 = 42.00  ✓
```

**Debug-capture ambiguity**: `_debug_capture["final_y"]` is populated at line
523/859 from the **initial** `final_y`, before any nudge. After nudge, the
actual render `final_y` is `candidate.y + l_font_px * 0.3`. Tests using
`_debug_capture` to verify I-3 after a nudge will see a stale `final_y` value
and must use `placed[-1].y + l_font_px * 0.3` to reconstruct the true post-nudge
final_y. The existing test `TestQW1PillYCenterRegistration` is correct because
it tests the path without nudge (no collision pre-populated).

### 10d. emit_position_label_svg

Lines 1289–1321 — same construction pattern:
```python
candidate_y = final_y - l_font_px * 0.3
candidate = _LabelPlacement(x=final_x, y=candidate_y, ...)
# nudge loop (different structure — 4 fixed dirs, up to 4 outer iterations)
final_y = candidate.y + l_font_px * 0.3
```

Empirical (no nudge):
```
registered y = 63.20
final_y (float) = 63.20 + 11*0.3 = 66.50
int(66.50) = 66  (= SVG text y attribute)  ✓
```

The SVG `<text y="">` attribute is `int(final_y)` = 66, while the registered
y is the float 63.20. The invariant holds at the float level; the int()
truncation is only relevant for pixel rendering, not collision geometry.

### 10e. Position-only label nudge path (I-3 + emit_position_label_svg)

Note: `emit_position_label_svg` does not use `_nudge_candidates`. Its nudge
loop uses four hard-coded directional steps (line 1294):

```python
nudge_dirs = [
    (0, -nudge_step), (-nudge_step, 0),
    (nudge_step, 0),  (0, nudge_step),
]
```

where `nudge_step = pill_h + 2`. This is a 4-direction, single-step scheme
(not the 32-candidate grid). The I-3 invariant is upheld within this loop
because `candidate.y` is always written as `candidate.y + ndy` (center
offset), and the render path at line 1321 reconstructs `final_y` the same way.

---

## Appendix: Empirical verification script

The following script was run in the project venv to produce all empirical data
in this audit. Reproduce with:

```
source .venv/bin/activate
python -c "..."  # see individual sections above
```

Key commands used:
- `list(_nudge_candidates(40, 10))` — full candidate enumeration
- `_nudge_candidates(40, 20, side_hint='above')` — half-plane ordering
- `_nudge_candidates(0, 0)` — degenerate pill_h=0
- `emit_plain_arrow_svg(..., dst_point=(-5.0, 60.0), ...)` — clamp repro
- `emit_plain_arrow_svg(..., _debug_capture=debug)` — I-3 anchor values

All 32 candidates at `pill_h=10` confirmed to be monotonically non-decreasing
in Manhattan distance, with N before S before E before W at each distance
level. The clamp-collision bug at §9 was reproduced systematically across 6
distinct natural positions.
