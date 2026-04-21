# Smart-Label System — Formal API Contracts

**Date**: 2026-04-21
**Author**: automated deep-read
**Scope**: Every public and semi-public function/class in the smart-label pipeline:
`scriba/animation/primitives/_svg_helpers.py` and the `estimate_text_width` helper
from `scriba/animation/primitives/_text_render.py`.
**Precursor documents**:
- `docs/spec/smart-label-ruleset.md` — normative spec (I-1 … I-10)
- `docs/archive/smart-label-ruleset-audit-2026-04-21/01-invariant-gaps.md` — round 1 findings (gap table)
- `docs/archive/smart-label-ruleset-audit-2026-04-21/02-algorithm-soundness.md` — algorithm soundness audit

Invariant references below use the spec numbering I-1 … I-10 plus the implicit
rules IR-1 … IR-6 identified in the round 1 audit.

---

## Table of Contents

1. `estimate_text_width`
2. `_label_width_text`
3. `_wrap_label_lines`
4. `_LabelPlacement` (dataclass + `overlaps`)
5. `_nudge_candidates`
6. `arrow_height_above`
7. `arrow_height_below` (implicit / absent — see hazard section)
8. `position_label_height_above`
9. `position_label_height_below`
10. `emit_arrow_marker_defs`
11. `emit_plain_arrow_svg`
12. `emit_arrow_svg`
13. `emit_position_label_svg`
14. `intersect_pill_edge` (absent — see §15)
15. `_headroom_for_labels` (absent — see §15)
16. Signature hazards
17. API asymmetries
18. Dead parameters
19. Proposed uniform `_place_pill` API surface (MW-3)

---

## 1. `estimate_text_width`

**Source**: `scriba/animation/primitives/_text_render.py`

### Signature

```python
def estimate_text_width(text: str, font_size: int = 14) -> int:
```

### Purpose

Return the estimated rendered pixel width of `text` at `font_size` using
Unicode-aware per-codepoint heuristics (CJK full-width = 1.0 em, ASCII/Latin
= 0.62 em, combining marks = 0 em, ZWJ emoji clusters = 1.0 em).

### Preconditions

- `text` is a valid Python `str` (may be empty; must not be `None`).
- `font_size` is a positive integer, typically 10 – 16. Formally: `font_size >= 1`.
- `font_size` must not be `NaN` or `±inf` (the type annotation enforces `int`
  but callers must not pass a float masquerading as an int via `# type: ignore`).
- Semantic bound: `font_size <= 10000`; values beyond this are meaningless
  and the result is treated as a heuristic anyway.

### Postconditions

- Return type is `int`.
- Return value is `>= 0`. Specifically: `estimate_text_width("", n) == 0`
  for all valid `n`.
- Monotone in text length: adding characters never decreases the estimate
  (because per-codepoint widths are non-negative).
- Monotone in font size: `estimate_text_width(t, n1) <= estimate_text_width(t, n2)`
  when `n1 <= n2`.
- Deterministic: same `(text, font_size)` inputs produce identical results
  across calls in the same process. No randomness, no global state read.
- The estimate is approximate; callers must add pill-padding on top.

### Invariants preserved

- I-7: Width estimation for plain text (the non-math branch of
  `_label_width_text`). Contributes to the lower bound on pill_w that keeps
  text legible.

### Side effects

None. Purely functional; no mutation.

### Errors raised

No exceptions under normal inputs. A malformed surrogate-pair `str` (e.g.
produced by `str.encode('surrogatepass')`) may cause `unicodedata.category`
to raise `ValueError` on some Python builds. Callers must not pass raw bytes
decoded with `surrogatepass`.

### Complexity

O(n) where n = len(text). The ZWJ look-ahead at most doubles the constant
factor in pathological ZWJ-heavy emoji strings.

### Thread-safety

Fully re-entrant. No module-level mutable state is read or written.

### Examples

```python
estimate_text_width("abc", 11)       # → 21   (3 * 0.62 * 11 ≈ 20.5 → 21)
estimate_text_width("你好", 12)      # → 24   (2 * 1.0 * 12)
estimate_text_width("", 11)          # → 0
```

---

## 2. `_label_width_text`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def _label_width_text(text: str) -> str:
```

### Purpose

Derive a width-estimation proxy string from `text`. For plain text returns
the string unchanged. For math labels (containing `$...$`) strips LaTeX
command tokens and brace characters, then appends a 15 % character-count
suffix so that `estimate_text_width` applied to the result approximates the
true KaTeX-rendered width.

### Preconditions

- `text` is a valid Python `str`. Empty string is allowed.
- No constraint on content; any Unicode is accepted.
- The function is expected to be called only with the `label_text` from an
  annotation dict, so in practice `text` is a human-readable label possibly
  with `$...$` delimiters.

### Postconditions

- Return type is `str`.
- If `text` is empty, return `""`.
- If `text` contains no `$...$` fragments, the return value equals `text`
  unchanged (identity postcondition for plain labels).
- If `text` contains `$...$` fragments:
  - The return value has no `$` delimiters, no `\command` tokens (matched
    by `\\[a-zA-Z]+`), and no `{` or `}` characters.
  - `len(return_value) >= len(stripped_text)`, where `stripped_text` is the
    result after stripping tokens and braces (the suffix is appended, never
    removed).
  - Specifically: `len(return_value) == len(stripped) + max(1, int(len(stripped) * 0.15))`.
  - Edge case: if all characters are LaTeX commands / braces, `stripped` may
    be `""`. In this case `return_value` has length `max(1, 0) = 1`
    (a single character from `stripped[:1]`, which is `""[:1] == ""`), so
    `return_value == ""`. The 1.15x factor is effectively lost. See hazard
    §16-H3.
- Deterministic: same input → same output.

### Invariants preserved

- I-7: Ensures `estimate_text_width(_label_width_text(label), px)` never
  under-estimates the rendered math-pill width by more than an acceptable
  heuristic margin.

### Side effects

None.

### Errors raised

None under valid inputs. `_MATH_DELIM_RE` and `_LATEX_CMD_RE` are compiled
module-level patterns; no re-compilation occurs per call.

### Complexity

O(n) where n = len(text).

### Thread-safety

Fully re-entrant. Uses only module-level compiled regexes (immutable).

### Examples

```python
_label_width_text("hello")             # → "hello"
_label_width_text("$\\alpha + 3$")     # → "  + 3  +" (stripped "  + 3", 15% extra = 1 char)
                                        # exact result depends on stripping; width > naive
_label_width_text("")                  # → ""
_label_width_text("$\\frac{a}{b}$")   # → "ab" + "a" (stripped "ab", +15% ≈ 1 extra char)
```

---

## 3. `_wrap_label_lines`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def _wrap_label_lines(text: str, max_chars: int = _LABEL_MAX_WIDTH_CHARS) -> list[str]:
```

where `_LABEL_MAX_WIDTH_CHARS = 24`.

### Purpose

Split `text` into multiple lines at natural break characters (space, comma,
`+`, `=`) without splitting inside `$...$` math regions. Returns a list of
one or more lines. Hyphen (`-`) is unconditionally excluded from the split
character set to avoid breaking math expressions.

### Preconditions

- `text` is a valid Python `str` (may be empty).
- `max_chars >= 1`. Formally the function works for `max_chars == 0` (every
  token becomes its own line), but this is not a supported use case.
- Callers must NOT pass `text` that has already had `$...$` stripped; the
  math-guard depends on balanced `$` delimiters.
- Callers should only invoke this function when `_label_has_math(text)` is
  `False`; the three emitters enforce this by checking math before calling
  (IR-2). If called on a math label, the `$` toggle logic still prevents
  splitting inside math spans, but the returned line may still exceed
  `max_chars` for very long math expressions.

### Postconditions

- Return type is `list[str]` with `len >= 1`.
- If `len(text) <= max_chars`, return `[text]` (no-split shortcut).
- Every returned line has `len <= max_chars + len(longest_indivisible_token)`.
  If a single token exceeds `max_chars` it is placed on its own line and
  cannot be split further.
- The concatenation of all returned lines (with no separator) equals `text`
  with trailing whitespace stripped from each line, but split-point characters
  are preserved at the end of tokens (before the strip). In practice,
  `"".join(lines).strip() == text.strip()` does not hold exactly because
  trailing whitespace is stripped per-line; however all non-whitespace content
  is preserved.
- `-` characters are never split on, inside or outside math regions.
- No content from inside a `$...$` region is used as a split point.
- Deterministic: same `(text, max_chars)` → same output.

### Invariants preserved

- I-8: Math labels are not wrapped (callers check `_label_has_math` first).
  When called on plain text, `-` is unconditionally excluded from split chars,
  consistent with I-8's "hyphen never split" guarantee.

### Side effects

None.

### Errors raised

None.

### Complexity

O(n) where n = len(text).

### Thread-safety

Fully re-entrant. No module-level mutable state.

### Examples

```python
_wrap_label_lines("short")                    # → ["short"]
_wrap_label_lines("a + b + c + d", 8)         # → ["a + b +", "c + d"]
_wrap_label_lines("$f(x)=-4$", 5)             # → ["$f(x)=-4$"]  (math guard + no hyphen)
_wrap_label_lines("hello world", 10)          # → ["hello", "world"]
```

---

## 4. `_LabelPlacement` (dataclass + `overlaps`)

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
@dataclass(slots=True)
class _LabelPlacement:
    x: float        # geometric center x
    y: float        # geometric center y  (= text-anchor y − l_font_px × 0.3)
    width: float    # pill width in pixels
    height: float   # pill height in pixels

    def overlaps(self, other: "_LabelPlacement") -> bool: ...
```

### Purpose

Immutable-by-convention value object that represents the axis-aligned bounding
box (AABB) of a placed annotation pill, stored in center-space coordinates.
`overlaps` returns `True` when two AABBs share any interior area (zero-gap
AABB contact returns `False`; see hazard §16-H1 / spec I-2 gap).

### Preconditions (`_LabelPlacement` construction)

- `x`, `y` are finite floats (not `NaN`, not `±inf`).
- `width >= 0`, `height >= 0`. Zero-dimension pills are legal (see IR-3 in
  the soundness audit for `pill_h = 0` edge case) but produce degenerate
  collision geometry.
- `x` and `y` represent the **geometric center** of the pill, not its
  top-left corner. Specifically:
  - `y` must satisfy `y = text_anchor_y − l_font_px × 0.3` (I-3).
  - `x` must be the post-clamp center (I-4): `x >= width / 2` after QW-3
    clamping is applied.

### Preconditions (`overlaps`)

- `other` is a valid `_LabelPlacement` with finite coordinates.
- Both `self` and `other` are in the same coordinate space (SVG user units,
  no translate applied — the `placed_labels` registry stores pre-translate
  values, per I-10).

### Postconditions (`overlaps`)

- Returns `bool`.
- `self.overlaps(other) == other.overlaps(self)` (symmetric).
- `self.overlaps(self) == True` when `width > 0` and `height > 0`.
- Two pills with zero separation (exactly touching edges) return `False`
  (strict inequality in the AABB test). This is a documented spec divergence:
  spec I-2 claims "≥ 2 px AABB separation" but the implementation enforces
  zero separation. See §17 asymmetry note A-1.
- Deterministic: same inputs → same bool, byte-identical.

### Invariants preserved

- I-2: Overlap detection gate for the nudge loop (with the caveat that the
  2 px padding stated in the spec is not currently enforced).
- I-3: The `y` coordinate convention is enforced by construction at every
  call site; `overlaps` itself is unaware of the convention.
- I-10: Each instance is created per-label, never mutated after registration.
  `slots=True` prevents attribute injection.

### Side effects

None. `@dataclass(slots=True)` makes instances immutable in practice.

### Errors raised

None for valid inputs. If `width` or `height` is `NaN`, the comparison
operators will produce `False` for all comparisons, causing `overlaps` to
return `True` unconditionally — a silent failure mode.

### Complexity

`overlaps`: O(1). Construction: O(1).

### Thread-safety

Instances are value objects; concurrent reads are safe. The `placed_labels`
list that holds them must not be mutated from multiple threads simultaneously.

### Examples

```python
a = _LabelPlacement(x=50.0, y=20.0, width=40.0, height=16.0)
b = _LabelPlacement(x=80.0, y=20.0, width=40.0, height=16.0)
a.overlaps(b)   # False — gap of 10 px between right edge of a and left edge of b
                # (50+20=70; 80-20=60; 70>60 so overlapping... let's recalc)
                # a: [30,70], b: [60,100] → a.right=70 > b.left=60 → overlaps True

c = _LabelPlacement(x=150.0, y=20.0, width=40.0, height=16.0)
a.overlaps(c)   # False — [30,70] vs [130,170], no intersection
```

---

## 5. `_nudge_candidates`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def _nudge_candidates(
    pill_w: float,
    pill_h: float,
    side_hint: Literal["above", "below", "left", "right"] | None = None,
) -> Iterator[tuple[float, float]]:
```

### Purpose

Generate at most 32 `(dx, dy)` displacement candidates in order of increasing
Manhattan distance from the origin, for use in the collision-avoidance nudge
loop. When `side_hint` is given, candidates in the matching half-plane are
emitted first. The generator never yields `(0, 0)`; callers must check the
initial position before invoking the generator.

### Preconditions

- `pill_w` is a finite non-negative float. The parameter is **structurally
  unused** for step sizing (see §18 dead-parameter note D-1) but must be
  passed for API compatibility.
- `pill_h` is a finite positive float. When `pill_h <= 0`, all 32 candidates
  degenerate to `(0.0, 0.0)` — the generator still yields 32 items but they
  are all zero-displacement (see hazard §16-H2 and audit §6a).
- `side_hint` is one of `"above"`, `"below"`, `"left"`, `"right"`, or
  `None`. An unrecognized string silently coerces to `None` (line 183).

### Postconditions

- Yields exactly 32 `(float, float)` tuples (8 compass directions × 4 step
  sizes). The generator always exhausts after exactly 32 items.
- No `(0, 0)` is ever yielded (all step multipliers are `> 0` when
  `pill_h > 0`).
- Output is deterministic: same `(pill_w, pill_h, side_hint)` → same
  sequence of tuples, byte-identical, across calls in the same process.
- When `side_hint is None` or unrecognized: tuples are sorted by
  `(manhattan_distance, priority_index)` where priority is N=0, S=1, E=2,
  W=3, NE=4, NW=5, SE=6, SW=7.
- When `side_hint` is recognized: all preferred-half-plane candidates appear
  before any other-half-plane candidates, internally sorted by the same key.
  Specifically:
  - `"above"`: candidates with `dy < 0` (N, NE, NW — 12 items) precede all
    other 20 candidates.
  - `"below"`: candidates with `dy > 0` (S, SE, SW — 12 items) precede all
    other 20.
  - `"left"`:  candidates with `dx < 0` (W, NW, SW — 12 items) precede all
    other 20.
  - `"right"`: candidates with `dx > 0` (E, NE, SE — 12 items) precede all
    other 20.
- Step sizes (when `pill_h > 0`):
  `(0.25h, 0.5h, 1.0h, 1.5h)` per direction.
  At `pill_h = 20 px`: minimum cardinal displacement = 5 px,
  maximum diagonal displacement ≈ 42 px.

### Invariants preserved

- I-2: Supplies the candidate set to the nudge loop that enforces
  non-overlap in all three emitters.
- IR-3 (audit finding): `pill_w` is accepted for future API symmetry but
  currently produces no effect.

### Side effects

None. Pure generator; no external state mutated.

### Errors raised

None for valid inputs. Zero or negative `pill_h` produces degenerate
output (all zeros) without raising.

### Complexity

O(1) construction; O(1) per `next()` call; O(32) to exhaust. The sorting
step is O(32 log 32) = O(1) effectively.

### Thread-safety

Each call returns an independent generator object. Multiple concurrent calls
with different arguments are safe.

### Examples

```python
list(_nudge_candidates(40.0, 20.0))[:4]
# → [(0.0, -5.0), (0.0, -10.0), (0.0, -20.0), (0.0, -30.0)]
# first 4 are all-N at increasing steps? No — at pill_h=20 distance groups
# interleave. Actual first 4 by Manhattan: (0,-5), (0,5), (5,0), (-5,0)

list(_nudge_candidates(40.0, 20.0, side_hint="above"))[:4]
# All have dy < 0: e.g. (0,-5), (0,-10), (5,-5), (-5,-5)

list(_nudge_candidates(40.0, 0.0))
# → 32 copies of (0.0, 0.0)  — degenerate; pill_h=0 guard not yet implemented
```

---

## 6. `arrow_height_above`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def arrow_height_above(
    annotations: list[dict[str, Any]],
    cell_center_resolver: Callable[[str], tuple[float, float] | None],
    cell_height: float = CELL_HEIGHT,
    layout: Literal["horizontal", "2d"] = "horizontal",
) -> int:
```

### Purpose

Compute the maximum vertical pixel extent above `y = 0` that all arc-style
arrows (those with `arrow_from`) and plain-pointer annotations (those with
`arrow = True`) in `annotations` require, including label headroom. Used by
primitives to determine the `translate(0, N)` offset that shifts their content
down to make room for upward-curving arrows.

### Preconditions

- `annotations` is a list of annotation dicts (may be empty). Individual
  entries may be missing any key; missing keys default to `None` / `""`.
- `cell_center_resolver` is a callable that maps a selector string to
  `(x, y)` SVG coordinates or `None` if the selector cannot be resolved.
  The callable must not raise; it must return `None` for unresolvable selectors.
- `cell_height` is a positive finite float. Default is `CELL_HEIGHT` (40 px).
  `cell_height <= 0` is not supported and will produce a negative base_offset.
- `layout` is one of `"horizontal"` or `"2d"`. Any other string is treated
  as `"horizontal"` (implicit fallback via the `if layout == "2d":` branch).
- `cell_center_resolver` must return the same coordinates that will be passed
  to `emit_arrow_svg` at render time; if they differ, the computed headroom
  will be incorrect.

### Postconditions

- Return type is `int`.
- Return value is `>= 0`.
- When `annotations` is empty, or contains no entries with `arrow_from` or
  `arrow=True`, returns `0`.
- When any arc-style annotation's `cell_center_resolver` returns `None` for
  either endpoint, that annotation is skipped silently.
- The returned value is the maximum over all arc annotations of
  `int(total_offset)` (horizontal layout) or `int(extent_above)` (2d layout),
  plus `_LABEL_HEADROOM` (24 px) for plain text labels or `32 px` for math
  labels (I-9), plus the `plain_height` contribution from `arrow=True`
  annotations.
- For plain-pointer annotations: `plain_height = _PLAIN_ARROW_STEM (18 px)
  + _LABEL_HEADROOM (24 px if any has a label)`, contributing the minimum
  headroom for the stem and its label.
- Deterministic: same `(annotations, cell_height, layout)` with a
  deterministic resolver → same result.

### Invariants preserved

- I-1: Provides the headroom value that primitives must pass to
  `translate(0, N)` so that pills fit inside the declared viewBox.
- I-9: Math labels increase headroom to 32 px via `_label_has_math`.

### Side effects

None. Does not mutate `annotations` or the resolver's internal state.

### Errors raised

Propagates any exception from `cell_center_resolver`. Callers must ensure
the resolver is exception-safe.

### Complexity

O(A²) in the number of arrow annotations A (the inner `arrow_index` counting
loop is O(A) per annotation). For the typical case of a handful of arrows this
is negligible. Could be O(A log A) with a pre-grouping step.

### Thread-safety

Re-entrant provided `cell_center_resolver` is re-entrant.

### Examples

```python
arrow_height_above([], resolver, cell_height=40)    # → 0

arrow_height_above(
    [{"arrow_from": "arr.cell[0]", "target": "arr.cell[3]"}],
    resolver,
    cell_height=40,
)
# → int(base_offset) where base_offset = min(48, max(20, sqrt(dist)*2.5))

arrow_height_above(
    [{"arrow_from": "a", "target": "b", "label": "$O(n^2)$"}],
    resolver,
    cell_height=40,
)
# → above_no_label + 32   (math label → 32 px extra headroom, not 24)
```

---

## 7. `arrow_height_below`

**Source**: not found in `_svg_helpers.py` or any re-export in `base.py`.

### Status

**Absent.** A symmetric `arrow_height_below` does not exist in the current
codebase. The `__all__` list in `_svg_helpers.py` does not include it. The
round 1 audit noted (under I-9) that `position_label_height_below` exists for
position-only labels but there is no `arrow_height_below` counterpart for
arc arrows that curve below `y = max_y`.

### Implications for contract

Currently, arc-style arrows in all primitives curve **above** the source and
destination cells. The `emit_arrow_svg` horizontal layout always sets
`mid_y_val = int(min(y1, y2) - total_offset)`, meaning the curve bows upward.
Arrows that could bow downward (e.g. in a `layout="2d"` primitive where the
perpendicular component is downward) could in principle require bottom-edge
headroom, but no primitive currently declares a bottom-expansion for arc arrows.

### Recommendation

Document the absence explicitly. If a future primitive introduces downward-arcing
arrows, `arrow_height_below` should be added as a symmetric counterpart with
the same signature shape as `arrow_height_above`.

---

## 8. `position_label_height_above`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def position_label_height_above(
    annotations: list[dict[str, Any]],
    *,
    l_font_px: int = 11,
    cell_height: float = CELL_HEIGHT,
) -> int:
```

### Purpose

Compute the maximum extra pixel headroom needed above `y = 0` to accommodate
all `position="above"` pill labels among the position-only annotations (those
with a `label` but without `arrow_from` or `arrow=True`).

### Preconditions

- `annotations` is a list of annotation dicts (may be empty).
- `l_font_px >= 1`. Values `<= 0` will produce negative `line_height` and
  thus meaningless headroom values.
- `cell_height > 0` (finite positive float).
- The `l_font_px` and `cell_height` passed here must match the values used
  inside `emit_position_label_svg` for consistent headroom computation.

### Postconditions

- Return type is `int`.
- Return value is `>= 0`.
- When no position-only annotations have `position="above"` (or default
  `position` is absent, which also yields `"above"`), returns `0`.
- The returned value equals `max(0, ceil(-pill_ry) + headroom_extra)` where:
  - `pill_ry = final_y - pill_h/2 - l_font_px*0.3`
  - `final_y = -cell_height/2 - pill_h/2 - gap` (gap = max(4, cell_height*0.1))
  - `pill_h = (l_font_px + 2) + 2 * _LABEL_PILL_PAD_Y` (single-line estimate)
  - `headroom_extra = 32` if any matching annotation contains math, else `24`
- Uses single-line pill height as a conservative estimate; multi-line labels
  require more headroom but this function provides a lower bound.
- Deterministic.

### Invariants preserved

- I-1: Headroom value ensures `translate(0, N)` shifts content down enough
  for pills to remain within the viewBox.
- I-6: Ensures position-only labels have declared headroom so they can emit.
- I-9: Math labels receive 32 px extra headroom.

### Side effects

None.

### Errors raised

None.

### Complexity

O(A) in the number of annotations.

### Thread-safety

Re-entrant.

### Examples

```python
position_label_height_above([], l_font_px=11, cell_height=40)
# → 0

position_label_height_above(
    [{"label": "pivot", "position": "above", "target": "arr.cell[2]"}],
    l_font_px=11,
    cell_height=40,
)
# → some int > 0 reflecting pill height + gap + 24 px headroom

position_label_height_above(
    [{"label": "$O(n)$", "position": "above", "target": "arr.cell[0]"}],
    l_font_px=11,
    cell_height=40,
)
# → larger int (32 px extra for math)
```

---

## 9. `position_label_height_below`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def position_label_height_below(
    annotations: list[dict[str, Any]],
    *,
    l_font_px: int = 11,
    cell_height: float = CELL_HEIGHT,
) -> int:
```

### Purpose

Compute the extra pixel height needed below the nominal cell bottom edge
(`y = cell_height`) to accommodate all `position="below"` pill labels.

### Preconditions

Same as `position_label_height_above` with `position="below"` labels. The
`l_font_px` and `cell_height` must match those used in `emit_position_label_svg`.

### Postconditions

- Return type is `int`.
- Return value is `>= 0`.
- When no position-only annotations have `position="below"`, returns `0`.
- The returned value equals `max(0, ceil(pill_bottom - cell_height))` where:
  - `pill_bottom = cell_height/2 + pill_h + gap + l_font_px*0.3`
  - `pill_h = (l_font_px + 2) + 2 * _LABEL_PILL_PAD_Y`
  - `gap = max(4, cell_height * 0.1)`
- **Known gap**: the function does NOT branch on math content (unlike
  `position_label_height_above` and `arrow_height_above`). Math labels
  receive the same headroom as plain text for `position="below"`, violating
  the spirit of I-9. See §17 asymmetry note A-2.
- Deterministic.

### Invariants preserved

- I-1: Partial. Does not fully honor I-9 for math labels (see above).
- I-6: Ensures position-only labels below the cell have declared headroom.

### Side effects

None.

### Errors raised

None.

### Complexity

O(A).

### Thread-safety

Re-entrant.

### Examples

```python
position_label_height_below([], l_font_px=11, cell_height=40)
# → 0

position_label_height_below(
    [{"label": "end", "position": "below", "target": "arr.cell[5]"}],
    l_font_px=11,
    cell_height=40,
)
# → positive int (pill extends below nominal bottom edge)
```

---

## 10. `emit_arrow_marker_defs`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def emit_arrow_marker_defs(
    lines: list[str],
    annotations: list[dict[str, Any]],
) -> None:
```

### Purpose

**Deprecated no-op.** Originally intended to emit `<defs><marker>` elements
for SVG arrowhead markers. Since arrowheads are now rendered as inline
`<polygon>` elements inside each annotation `<g>`, no `<marker>` defs are
needed. The function body is `pass`. It is retained for call-site
compatibility (called unconditionally in `base.py:emit_annotation_arrows`)
and is scheduled for removal after 1.0.0.

### Preconditions

- `lines` is a mutable `list[str]` (the SVG output buffer). Not None.
- `annotations` is a `list[dict]`. Not None.

### Postconditions

- `lines` is unchanged (no elements appended, no elements removed).
- `annotations` is unchanged.
- Returns `None`.
- The function is idempotent: calling it N times has no more effect than
  calling it once.

### Invariants preserved

None actively. It preserves I-5 by not emitting any output.

### Side effects

None.

### Errors raised

None.

### Complexity

O(1).

### Thread-safety

Re-entrant (no-op).

### Examples

```python
buf = ["<g>"]
emit_arrow_marker_defs(buf, [{"arrow_from": "a", "target": "b"}])
assert buf == ["<g>"]  # no change
```

---

## 11. `emit_plain_arrow_svg`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def emit_plain_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    dst_point: tuple[float, float],
    render_inline_tex: Callable[[str], str] | None = None,
    placed_labels: list[_LabelPlacement] | None = None,
    _debug_capture: dict[str, Any] | None = None,
) -> None:
```

### Purpose

Emit a short straight-stem pointer annotation (`arrow=True`) into `lines`.
A vertical line of length `_PLAIN_ARROW_STEM` (18 px) drops from the label
toward the target cell, terminating in a downward-pointing polygon arrowhead
at `dst_point`. If `ann["label"]` is set, a collision-aware pill is placed
above the stem start.

### Preconditions

- `lines` is a mutable `list[str]` (SVG output buffer). Must not be `None`.
  Markup is appended; caller is responsible for inserting `lines` at the
  correct position in the final SVG.
- `ann` is a dict with optional keys:
  - `"target"` (`str`): identifier for accessibility annotation; any string.
  - `"color"` (`str`): one of `{"good", "info", "warn", "error", "muted",
    "path"}`. Unknown values silently fall back to `"info"` (IR-6).
  - `"label"` (`str`): the label text. Empty string suppresses label emission.
  - `"side"` or `"position"` (`str`): `side_hint` for nudge half-plane
    preference. Unrecognized values are silently ignored.
- `dst_point` is a 2-tuple of finite floats `(x, y)` in SVG coordinates.
  `x` and `y` must be finite (not NaN, not ±inf). The arrowhead tip is
  placed at `(int(x), int(y))`.
- `render_inline_tex`: if not `None`, must accept a label string containing
  `$...$` delimiters and return a valid HTML string for embedding in a
  `<foreignObject>`. Must not raise for any non-empty string. May return
  `None` or `""` to fall back to plain SVG `<text>`.
- `placed_labels`: if not `None`, must be the **same list** shared across
  all `emit_plain_arrow_svg` and `emit_arrow_svg` calls for the same frame.
  The list must only contain `_LabelPlacement` entries from the current frame
  (no stale entries from previous frames — I-10). If `None`, collision
  avoidance is disabled.

### Postconditions

- `lines` receives 3 to ~10 new string elements (depending on label
  presence, multi-line, math, collision debug):
  1. `<g class="scriba-annotation scriba-annotation-{color}" ...>` open tag.
  2. `<line .../>` (the vertical stem).
  3. `<polygon .../>` (the arrowhead).
  4. (When `label_text`): optionally a debug comment if collision unresolved
     and `SCRIBA_DEBUG_LABELS=1` (I-5).
  5. (When `label_text`): `<rect .../>` (pill background).
  6. (When `label_text`): `<text>` or `<foreignObject>` (label text).
  7. `</g>` close tag.
- Invariant I-3 is maintained: if `placed_labels` is not `None`, the
  appended `_LabelPlacement` entry has
  `y == text_render_y - l_font_px * 0.3` (to within float precision before
  `int()` truncation at render time).
- Invariant I-4 is maintained: the registered `x` is `max(final_x, pill_w/2)`.
  Known caveat from audit §9: when a nudge candidate moves the label to
  `x < 0` before clamping, the post-clamp position may collide with a
  previously registered left-edge label. This is a known soundness violation
  (see §17 asymmetry note A-3).
- Invariant I-5: debug comments are gated by `_DEBUG_LABELS`.
- When `placed_labels is not None`, exactly one `_LabelPlacement` is appended
  to `placed_labels` (for the final label position, whether naturally placed
  or nudged or unresolved). If the label is empty, nothing is appended.
- The SVG group uses `role="graphics-symbol"` and `aria-label` for
  accessibility.
- Deterministic given deterministic `render_inline_tex` and
  `dst_point` as finite integers (sub-integer float values are truncated
  with `int()`).

### Invariants preserved

- I-2, I-3, I-4, I-5, I-7, I-8, I-10 (when `placed_labels` is properly
  initialized and shared).

### Side effects

- Mutates `lines` (appends SVG strings).
- Mutates `placed_labels` (appends one `_LabelPlacement` when label is
  non-empty and `placed_labels is not None`).
- Populates `_debug_capture` dict with `"final_y"`, `"l_font_px"`,
  `"pill_w"`, `"pill_h"` keys when `_debug_capture is not None`. Note:
  `final_y` in the capture reflects the **pre-nudge** position; use
  `placed_labels[-1].y + l_font_px * 0.3` to recover the post-nudge
  render y.

### Errors raised

- Propagates any exception raised by `render_inline_tex`. The function
  wraps the callback in a bare `except Exception` and falls back to plain
  `<text>`, so `render_inline_tex` exceptions are silently swallowed and
  do not propagate.

### Complexity

- O(P) where P = len(placed_labels) at the time of the call (the inner
  `any(candidate.overlaps(p) for p in placed_labels)` scan is O(P) per
  candidate; at most 32 candidates → O(32 × P) = O(P)).
- O(W) in label text length W for width estimation.

### Thread-safety

Not re-entrant on the same `lines` or `placed_labels` list. Single-threaded
use only, consistent with scriba's single-threaded render model (I-10).

### Examples

```python
lines: list[str] = []
placed: list[_LabelPlacement] = []

emit_plain_arrow_svg(
    lines,
    {"target": "arr.cell[3]", "color": "good", "label": "pivot"},
    dst_point=(120.0, 60.0),
    placed_labels=placed,
)
# lines now contains ~7 SVG strings; placed has 1 entry

emit_plain_arrow_svg(
    lines,
    {"target": "arr.cell[4]", "color": "info", "label": "curr"},
    dst_point=(160.0, 60.0),
    placed_labels=placed,  # same list — enables collision avoidance
)
# If second pill naturally overlaps first, nudge fires; placed has 2 entries

emit_plain_arrow_svg(
    lines,
    {"target": "arr.cell[0]", "color": "warn"},  # no label
    dst_point=(20.0, 60.0),
    placed_labels=placed,
)
# No pill emitted; placed still has 2 entries (no label → no registration)
```

---

## 12. `emit_arrow_svg`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def emit_arrow_svg(
    lines: list[str],
    ann: dict[str, Any],
    src_point: tuple[float, float],
    dst_point: tuple[float, float],
    arrow_index: int,
    cell_height: float,
    render_inline_tex: Callable[[str], str] | None = None,
    layout: Literal["horizontal", "2d"] = "horizontal",
    shorten_src: float = 0.0,
    shorten_dst: float = 0.0,
    placed_labels: list[_LabelPlacement] | None = None,
    _debug_capture: dict[str, Any] | None = None,
) -> None:
```

### Purpose

Emit a cubic Bézier arrow annotation connecting `src_point` to `dst_point`
with an inline polygon arrowhead at the destination. Optionally emits a
collision-aware pill label near the curve midpoint. Handles both the standard
horizontal upward-arc layout (Array, DPTable) and the perpendicular-to-line
2D layout (Graph, Tree, Plane2D).

### Preconditions

- `lines` is a mutable `list[str]` (SVG output buffer). Not None.
- `ann` has the same optional keys as in `emit_plain_arrow_svg`, plus:
  - `"arrow_from"` (`str`): source selector string. Used only for the
    accessibility `aria-label` and the `data-annotation` key.
- `src_point` and `dst_point` are 2-tuples of finite floats. Neither may be
  `NaN` or `±inf`. The distance between them need not be non-zero; when
  `src_point == dst_point` (self-loop), `dist` is clamped to `1.0` by the
  `or 1.0` guard, preventing division by zero. The arrow will degenerate
  visually in this case (see spec §5 bug-B).
- `arrow_index` is a non-negative integer (0-based count of arrows already
  targeting `ann["target"]` before this one in the current frame). Used for
  stagger: `total_offset = base_offset + arrow_index * cell_height * 0.3`.
  Passing a negative value is not supported and will reduce `total_offset`.
- `cell_height` is a positive finite float.
- `layout` is `"horizontal"` or `"2d"`. Other strings fall through to the
  horizontal branch.
- `shorten_src` and `shorten_dst` are non-negative floats. Values larger
  than `dist/2` will push endpoints past each other; the result is visually
  degenerate but no exception is raised.
- `placed_labels`: same constraint as in `emit_plain_arrow_svg`.
- `render_inline_tex`: same constraint as in `emit_plain_arrow_svg`.

### Postconditions

- `lines` receives:
  1. `<g ...>` open.
  2. `<path d="M... C... ... ..." ...>` (the Bézier curve with embedded
     `<title>`).
  3. `<polygon .../>` (arrowhead).
  4. (When `label_text` and `placed_labels` and displacement > 30 px):
     `<circle>` anchor dot + `<polyline>` dashed leader (IR-1 / spec I-11).
  5. (When `label_text`): optional debug comment, pill `<rect>`, text.
  6. `</g>` close.
- Label placement follows the same center-correction invariant as
  `emit_plain_arrow_svg` (I-3, I-4).
- Leader line is emitted if and only if the label was nudged more than
  30 px from its natural anchor position (IR-1). The 30 px threshold is
  a magic number; see §17 asymmetry note A-4.
- When `placed_labels is not None` and `label_text` is non-empty, exactly
  one `_LabelPlacement` is appended.
- `ann["label"]` is not modified; the function is non-destructive on its
  input dict.
- Deterministic given finite, identical inputs.

### Invariants preserved

- I-2, I-3, I-4, I-5, I-7, I-8, I-10 (same as `emit_plain_arrow_svg`).
- IR-1: The 30 px leader threshold is honored as documented.

### Side effects

- Mutates `lines`.
- Mutates `placed_labels` (appends one entry when label non-empty and
  `placed_labels is not None`).
- Populates `_debug_capture` (pre-nudge `final_y`, `l_font_px`, `pill_w`,
  `pill_h`).

### Errors raised

Same behavior as `emit_plain_arrow_svg` regarding `render_inline_tex`
exceptions.

### Complexity

O(P) in `len(placed_labels)` for the same reason as `emit_plain_arrow_svg`.

### Thread-safety

Single-threaded use only.

### Examples

```python
lines: list[str] = []
placed: list[_LabelPlacement] = []

emit_arrow_svg(
    lines,
    ann={"target": "arr.cell[3]", "arrow_from": "arr.cell[0]",
         "color": "path", "label": "copy"},
    src_point=(20.0, 60.0),
    dst_point=(120.0, 60.0),
    arrow_index=0,
    cell_height=40.0,
    placed_labels=placed,
)
# lines has ~6 SVG strings; placed has 1 entry

# Second arrow to same target — staggered
emit_arrow_svg(
    lines,
    ann={"target": "arr.cell[3]", "arrow_from": "arr.cell[5]",
         "color": "info", "label": "prev"},
    src_point=(200.0, 60.0),
    dst_point=(120.0, 60.0),
    arrow_index=1,          # ← stagger index
    cell_height=40.0,
    placed_labels=placed,   # same list — cross-arrow collision avoidance
)
```

---

## 13. `emit_position_label_svg`

**Source**: `scriba/animation/primitives/_svg_helpers.py`

### Signature

```python
def emit_position_label_svg(
    lines: list[str],
    ann: dict[str, Any],
    anchor_point: tuple[float, float],
    cell_height: float = CELL_HEIGHT,
    render_inline_tex: Callable[[str], str] | None = None,
    placed_labels: list[_LabelPlacement] | None = None,
) -> None:
```

### Purpose

Emit a pill-only label for position-only annotations (annotations with a
`label` and a `position` key but neither `arrow_from` nor `arrow=True`).
Positions the pill adjacent to `anchor_point` according to `ann["position"]`
(`"above"`, `"below"`, `"left"`, `"right"`). No arrow or leader is emitted.

### Preconditions

- `lines` is a mutable `list[str]`. Not None.
- `ann` must have `"label"` as a non-empty string; if missing or empty, the
  function returns immediately (early exit, no-op).
- `ann["color"]`: same fallback rule as other emitters (unknown → `"info"`).
- `ann["position"]`: one of `"above"`, `"below"`, `"left"`, `"right"`.
  Unrecognized values fall through to the `else` branch which behaves
  identically to `"above"`. The fallback is silent.
- `anchor_point` is a 2-tuple of finite floats `(x, y)`. Not None.
- `cell_height` is a positive finite float.
- `placed_labels`: same shared-list constraint as other emitters.
- `render_inline_tex`: same constraint.

### Postconditions

- If `ann.get("label", "")` is empty: `lines` and `placed_labels` are
  unchanged. Returns immediately.
- Otherwise: `lines` receives:
  1. `<g ...>` open.
  2. `<rect .../>` (pill background).
  3. `<text>` or `<foreignObject>` (label text).
  4. `</g>` close.
  5. Optionally a debug comment before the `<g>` if collision unresolved and
     `SCRIBA_DEBUG_LABELS=1`.
- The pill is positioned offset from `anchor_point` by:
  - `"above"`: `final_y = ay - cell_height/2 - pill_h/2 - gap`
  - `"below"`: `final_y = ay + cell_height/2 + pill_h/2 + gap`
  - `"left"`:  `final_x = ax - pill_w/2 - gap`
  - `"right"`: `final_x = ax + pill_w/2 + gap`
  - where `gap = max(4.0, cell_height * 0.1)`.
- I-3 is maintained: registered `y = final_y - l_font_px * 0.3`.
- I-4 is maintained: registered `x = max(final_x, pill_w/2)`.
- **Nudge algorithm differs from the arrow emitters** (IR-4 / spec I-12):
  4 cardinal directions at step `pill_h + 2`, up to 4 outer iterations
  (16 total candidates). Does NOT use `_nudge_candidates`.
- When `placed_labels is not None` and label is non-empty, exactly one
  `_LabelPlacement` is appended.
- No leader line is ever emitted (no `displacement` check, unlike
  `emit_arrow_svg`).
- No `side_hint` is extracted from `ann` for the nudge direction preference
  (unlike the arrow emitters which read `ann.get("side")`).
- Deterministic given deterministic inputs.

### Invariants preserved

- I-3, I-4, I-5, I-6, I-7, I-8 (partial — math no-wrap applies).
- Does NOT preserve I-9 for `position="below"` (no math headroom branch in
  `position_label_height_below`).
- Does NOT use `_nudge_candidates` — I-12 (implicit rule from audit).

### Side effects

- Mutates `lines`.
- Mutates `placed_labels`.

### Errors raised

Same `render_inline_tex` exception behavior as other emitters.

### Complexity

O(P × 16) = O(P) in `len(placed_labels)` (up to 16 candidates × O(P) overlap
check each).

### Thread-safety

Single-threaded use only.

### Examples

```python
lines: list[str] = []
placed: list[_LabelPlacement] = []

emit_position_label_svg(
    lines,
    ann={"label": "start", "color": "good", "position": "above",
         "target": "arr.cell[0]"},
    anchor_point=(20.0, 40.0),
    cell_height=40.0,
    placed_labels=placed,
)
# lines has ~4 SVG strings; placed has 1 entry

emit_position_label_svg(
    lines,
    ann={"label": "", "position": "below", "target": "arr.cell[0]"},
    anchor_point=(20.0, 40.0),
    placed_labels=placed,
)
# Empty label → no-op; lines and placed unchanged
```

---

## 14. `intersect_pill_edge`

**Status**: **Absent** from the codebase. Not present in `_svg_helpers.py`,
`base.py`, or any file under `scriba/animation/primitives/`.

A grep for `intersect_pill_edge` in the repository returns no matches. This
function name was listed as a candidate in the contract request; it does not
currently exist in the smart-label system. If implemented in the future
(e.g. as part of MW-3 leader-line clamping to the pill boundary), it would
need a contract. A suggested contract shape is provided in §19 (proposed MW-3
API).

---

## 15. `_headroom_for_labels`

**Status**: **Absent** from the codebase as a standalone function. There is
no function named `_headroom_for_labels` in `_svg_helpers.py` or any imported
module. The concept of headroom computation is distributed across
`arrow_height_above`, `position_label_height_above`, and
`position_label_height_below`. The spec (`smart-label-ruleset.md` §1 I-1)
references `_headroom_for_labels` as if it were a unified function, but this
is a forward reference to a function that should exist post-MW-3 unification.

---

## 16. Signature Hazards

### H-1: `overlaps` has no `pad` parameter (I-2 spec mismatch)

**Function**: `_LabelPlacement.overlaps`
**Hazard**: The spec invariant I-2 states "≥ 2 px AABB separation." The
implementation checks strict zero-gap overlap. Two pills touching edge-to-edge
register as non-overlapping and will both be rendered, potentially
indistinguishable visually.
**Risk**: MEDIUM (spec divergence; visual quality degradation under dense
annotations).
**Recommendation**: Add `def overlaps(self, other: _LabelPlacement, pad: float = 0.0) -> bool`
and call with `pad=2.0` at all three nudge-loop call sites.

### H-2: `pill_h = 0` degenerates `_nudge_candidates` silently

**Function**: `_nudge_candidates`
**Hazard**: When `pill_h = 0`, all 32 candidates are `(0.0, 0.0)`. The nudge
loop tries 32 identical no-op candidates and falls back to the natural
position. No error is raised; the emitter proceeds to render an invisible
(height=0) pill rect with text overlapping any nearby content.
**Risk**: LOW in production (requires patched `ARROW_STYLES`), MEDIUM in test
environments where styles may be mocked.
**Recommendation**: Add `if pill_h <= 0: return` (or `raise ValueError`) as
the first line of `_nudge_candidates`. Add a guard in the emitters:
`assert pill_h > 0` before calling `_nudge_candidates`.

### H-3: `_label_width_text` 1.15× factor lost for all-command math labels

**Function**: `_label_width_text`
**Hazard**: A math label composed entirely of LaTeX command tokens (e.g.
`$\frac\sum\int$`) produces an empty base string after stripping. The suffix
append computes `extra_len = max(1, int(0 * 0.15)) = 1` but `stripped[:1]`
is `""`, so the appended suffix is also `""`. The returned string is `""`,
and `estimate_text_width("", px) = 0`. The pill width collapses to
`2 * _LABEL_PILL_PAD_X = 12 px`, regardless of how wide the rendered math
actually is.
**Risk**: LOW (degenerate input unlikely in practice; valid KaTeX requires
operands).
**Recommendation**: When `stripped` is empty after processing, return a
fallback string of appropriate width (e.g. `"X" * 4`) to force a minimum
pill width.

### H-4: Positional float parameters in emitter signatures are easy to transpose

**Functions**: `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`
**Hazard**: `src_point: tuple[float, float]`, `dst_point: tuple[float, float]`,
`anchor_point: tuple[float, float]`, `shorten_src: float`, `shorten_dst: float`
are all floats or float tuples. Swapping `src_point` and `dst_point` produces
a visually mirrored arrow without any type error. Similarly, swapping
`shorten_src` and `shorten_dst` (e.g. passing `0.0` for one and `10.0` for
the other in the wrong order) produces subtly incorrect shortening.
**Risk**: LOW in current callers (only `base.py` dispatches these functions
and the order is stable), but HIGH during refactoring.
**Recommendation**: Convert `src_point`, `dst_point`, and `anchor_point` to
keyword-only parameters by adding a bare `*` before them (consistent with
`l_font_px` and `cell_height` in the height helpers).

### H-5: `_debug_capture` dict is typed as `dict[str, Any] | None` with no schema

**Functions**: `emit_arrow_svg`, `emit_plain_arrow_svg`
**Hazard**: Callers who use `_debug_capture` to test post-nudge state must
know that `final_y` in the dict is the **pre-nudge** value. The post-nudge
value requires `placed_labels[-1].y + l_font_px * 0.3`. This is documented in
the soundness audit (§10d) but not in the function docstring.
**Risk**: LOW for current tests (existing tests do not test through nudge with
debug capture), but HIGH when new tests are written naively.
**Recommendation**: Add to docstring: "`final_y` in `_debug_capture` reflects
the pre-nudge natural position. To obtain the post-nudge rendered y, use
`placed_labels[-1].y + l_font_px * 0.3`."

### H-6: `color` defaults differ from visual intent for annotation types

**Functions**: all three emitters
**Hazard**: All three emitters default `color = ann.get("color", "info")`.
The `"info"` style has `opacity="0.45"` and a slate stroke, which is
intentionally de-emphasized. An annotation author who omits `color` gets a
de-emphasized annotation that may look like a placeholder rather than an
intentional highlight.
**Risk**: LOW (documented in `ARROW_STYLES`), but a UX footgun.
**Recommendation**: Document the `"info"` default explicitly in each emitter
docstring and in the Starlark `\annotate` user documentation.

---

## 17. API Asymmetries

### A-1: `overlaps` enforces zero-gap, spec claims 2 px gap

**Scope**: `_LabelPlacement.overlaps` vs. spec I-2.
**Description**: The spec says "≥ 2 px AABB separation"; the code enforces
zero separation. This asymmetry means two pills can register as
non-overlapping yet be visually touching or indistinguishable at small font
sizes.
**Impact**: Visual quality (pills may touch). Existing tests verify nudge
fires but not the 2 px gap.
**Resolution path**: MW-3 `_place_pill` helper should normalize the pad value
and pass it consistently.

### A-2: `position_label_height_below` lacks math headroom branch

**Scope**: `position_label_height_below` vs. `position_label_height_above`
and `arrow_height_above`.
**Description**: `position_label_height_above` and `arrow_height_above` both
branch on `_label_has_math` to return 32 px extra (I-9). `position_label_height_below`
uses a flat computation with no math check, violating the symmetry that math
labels always receive 32 px headroom.
**Impact**: A `position="below"` math label may be clipped at the viewBox
bottom in primitives that compute their height with `position_label_height_below`.
**Resolution path**: Add the same `has_math` check to `position_label_height_below`
and update affected primitive `emit_svg` calls.

### A-3: Clamp-collision hazard is shared across all three emitters but
only documented in the soundness audit

**Scope**: QW-3 x-clamp logic in `emit_arrow_svg`, `emit_plain_arrow_svg`,
`emit_position_label_svg`.
**Description**: All three emitters perform the nudge check on the raw
(un-clamped) position and then clamp afterward. A label that passes the
collision check at a negative x can be clamped to exactly the same x as a
prior left-edge label, silently producing an overlap. The soundness audit
(§9) confirmed a repro for two labels near x=0.
**Impact**: MEDIUM. Requires two labels near the left boundary of the SVG.
**Resolution path**: MW-3 should check collisions on the clamped position
directly. Proposed fix from audit §9:
```python
clamped_x_test = max(final_x + ndx, pill_w / 2)
test = _LabelPlacement(x=clamped_x_test, y=candidate_y + ndy, ...)
```

### A-4: `emit_position_label_svg` uses 4-direction nudge; arrow emitters use 8-direction 32-candidate grid

**Scope**: `emit_position_label_svg` nudge loop (lines 1294–1318) vs.
`_nudge_candidates` used by `emit_arrow_svg` and `emit_plain_arrow_svg`.
**Description**: Position-only labels use a 4-direction (N, W, E, S)
single-step nudge with up to 4 outer iterations (max 16 candidates). Arrow
labels use an 8-direction 32-candidate grid with `side_hint` half-plane
ordering. The two algorithms have different coverage, different step sizes,
and different fallback behavior. This is IR-4 from the round 1 audit and
should be formalized as spec I-12.
**Impact**: Position-only labels are harder to nudge out of dense clusters
and cannot prefer a half-plane. They also use a step of `pill_h + 2` (not
`pill_h × [0.25, 0.5, 1.0, 1.5]`), so their first step is always coarser
than the arrow emitters' first step.
**Resolution path**: MW-3 pill placement helper should call `_nudge_candidates`
uniformly for all three annotation types.

### A-5: `emit_position_label_svg` does not extract `side_hint` from `ann`

**Scope**: `emit_position_label_svg` vs. `emit_arrow_svg` and
`emit_plain_arrow_svg`.
**Description**: The arrow emitters read `ann.get("side") or ann.get("position")
or None` to determine `anchor_side` for the nudge half-plane preference. 
`emit_position_label_svg` does not read these fields for nudge preference; it
uses fixed cardinal directions regardless of the `position` key. For a
`position="above"` label, the nudge could move it below the anchor (South
direction) even though the author expressed intent to place it above.
**Impact**: LOW in common cases (4 labels seldom cluster enough to require
nudging), but notable when multiple position-only labels share the same cell.
**Resolution path**: In MW-3, pass `side_hint=position` to `_nudge_candidates`
within the unified helper.

### A-6: Leader line threshold (30 px) is only in `emit_arrow_svg`, not in the other two emitters

**Scope**: `emit_arrow_svg` (displacement > 30 check, lines 934–949) vs.
`emit_plain_arrow_svg` and `emit_position_label_svg` (no secondary leader ever).
**Description**: When `emit_arrow_svg` nudges a label more than 30 px from
its natural position, it emits a dashed polyline from the curve midpoint to
the pill center. Neither `emit_plain_arrow_svg` nor `emit_position_label_svg`
have this behavior. A heavily nudged plain-pointer or position label is
silently disconnected from its target with no visual indication.
**Impact**: LOW for position-only labels (their natural position is close to
the target anyway). MEDIUM for plain-pointer labels that may be nudged far
from the target in dense annotation clusters.
**Resolution path**: MW-3 could optionally emit a short dashed line for any
label displaced more than the threshold, regardless of annotation type.

---

## 18. Dead Parameters

### D-1: `pill_w` in `_nudge_candidates`

**Function**: `_nudge_candidates(pill_w, pill_h, side_hint=None)`
**Status**: Structurally unused. The parameter is documented with "retained
for API symmetry in case callers want aspect-aware steps in the future," but
the body computes all steps exclusively from `pill_h`.
**Evidence**: Line 170: `steps = (pill_h * 0.25, pill_h * 0.5, pill_h * 1.0, pill_h * 1.5)`.
The identifier `pill_w` does not appear in the function body.
**Recommendation**: Either
(a) Add `# noqa: ARG001` or `_ = pill_w` to suppress linter warnings and
    add a comment that it is an intentional reserved parameter, or
(b) Deprecate the parameter and schedule removal, replacing all call sites
    with `_nudge_candidates(pill_h, side_hint=...)`. Option (b) is cleaner
    but requires a deprecation cycle. Do not remove without one since
    `_nudge_candidates` is re-exported in `__all__`.

---

## 19. Proposed Uniform API Surface: `_place_pill` (MW-3)

The three emitters share an identical inner sequence:

1. Compute `pill_w` from `_label_width_text` + `estimate_text_width` + padding.
2. Compute `pill_h` from line count × line height + padding.
3. Construct the initial `_LabelPlacement` at `(natural_x, natural_y - l_font_px * 0.3)`.
4. If collision with any entry in `placed_labels`, run nudge grid.
5. Apply QW-3 x-clamp.
6. Append post-clamp `_LabelPlacement` to `placed_labels`.
7. Optionally emit debug comment.
8. Return `(fi_x, fi_y, pill_w, pill_h, pill_rx, pill_ry, collision_unresolved)`.

This sequence is duplicated verbatim (with the A-4 algorithmic divergence) in
all three emitters. MW-3 should extract it into:

```python
def _place_pill(
    *,
    natural_x: float,
    natural_y: float,
    pill_w: float,
    pill_h: float,
    l_font_px: float,
    placed_labels: list[_LabelPlacement],
    side_hint: Literal["above", "below", "left", "right"] | None = None,
    overlap_pad: float = 0.0,
) -> tuple[int, int, int, int, int, int, bool]:
    """Resolve final pill placement via nudge grid and viewBox clamp.

    Parameters
    ----------
    natural_x, natural_y:
        Initial text-anchor coordinates (before center-correction).
    pill_w, pill_h:
        Pre-computed pill dimensions in pixels.
    l_font_px:
        Font size used for the center-correction offset (l_font_px * 0.3).
    placed_labels:
        Shared registry of already-placed labels for this frame.
        Mutated in-place: the accepted placement is appended.
    side_hint:
        Optional half-plane preference for the nudge grid.
    overlap_pad:
        AABB separation pad (px) for overlap checks.
        Pass 2.0 to enforce I-2's "≥ 2 px" guarantee.

    Returns
    -------
    (fi_x, fi_y, pill_w_int, pill_h_int, pill_rx, pill_ry, collision_unresolved)
        fi_x, fi_y      — SVG text-anchor coordinates (int).
        pill_w_int      — pill width rounded to int.
        pill_h_int      — pill height rounded to int.
        pill_rx, pill_ry — top-left corner of pill rect (int, clamped).
        collision_unresolved — True if all candidates were exhausted.
    """
```

**Contract for `_place_pill`**:

Preconditions:
- `natural_x`, `natural_y` are finite floats.
- `pill_w > 0`, `pill_h > 0` (positive; use `max(1, ...)` guards upstream).
- `l_font_px >= 1`.
- `placed_labels` is the frame-local list (not shared across frames).
- `side_hint` is one of the four recognized strings or `None`.
- `overlap_pad >= 0`.

Postconditions:
- Exactly one `_LabelPlacement` is appended to `placed_labels`.
- The appended entry has `x = max(fi_x, pill_w/2)` and
  `y = fi_y - l_font_px * 0.3` (I-3, I-4).
- `fi_x`, `fi_y` are the render-time text-anchor coordinates.
- `pill_rx = max(0, fi_x - pill_w/2)`, `pill_ry = fi_y - pill_h/2 - l_font_px*0.3`.
- `collision_unresolved` is `True` iff all 32 nudge candidates overlapped.
- Deterministic given deterministic `placed_labels` state.

With `_place_pill` in place, every emitter reduces its label-placement block
to:

```python
fi_x, fi_y, pill_w_i, pill_h_i, pill_rx, pill_ry, coll = _place_pill(
    natural_x=natural_x,
    natural_y=natural_y,
    pill_w=pill_w,
    pill_h=pill_h,
    l_font_px=l_font_px,
    placed_labels=placed_labels,
    side_hint=side_hint,
    overlap_pad=2.0,   # enforce I-2
)
```

This eliminates asymmetries A-3, A-4, A-5 (by centralizing the nudge call),
closes the D-1 dead-parameter by inlining `pill_w` properly, and makes I-2
enforceable by default.

**What `_place_pill` does NOT do** (remains the caller's responsibility):
- Emit SVG for the pill rect, text, or leader.
- Compute `pill_w` and `pill_h` (callers call `estimate_text_width` +
  `_label_width_text` first).
- Emit debug comments (`collision_unresolved` is returned for the caller to
  gate on `_DEBUG_LABELS`).
- Handle the `render_inline_tex` branching (the emitter's responsibility after
  receiving `fi_x`, `fi_y`, etc.).

---

*End of API contracts document.*
*Next document in this series: `04-test-gaps.md` (proposed test additions to
close the gaps identified in §16–§18).*
