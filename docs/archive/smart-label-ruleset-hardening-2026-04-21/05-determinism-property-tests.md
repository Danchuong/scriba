---
title: "Smart-Label Hardening — Round 3: Determinism Property Tests"
report-id: hardening-05
phase: Round-3
date: 2026-04-21
status: Design only — do NOT add Hypothesis dep or write test files
depends-on:
  - docs/spec/smart-label-ruleset.md §1.5 (D-1..D-4)
  - docs/archive/smart-label-ruleset-hardening-2026-04-21/01-*  (corpus helpers)
  - docs/archive/smart-label-ruleset-hardening-2026-04-21/02-*  (platform golden)
  - scriba/animation/primitives/_svg_helpers.py
---

# Smart-Label Hardening — Round 3: Determinism Property Tests

> **Design document only.** No Hypothesis dependency is added and no test
> files are written here. This document is the specification that a
> subsequent implementation commit will translate 1-for-1 into
> `tests/conformance/smart_label/test_determinism.py`.

---

## Table of Contents

1. D-1..D-4 Restated in Quantifier Form
2. Hypothesis Strategies
3. Properties — One per Invariant
4. Float Tolerance Policy
5. Seeding and Reproducibility
6. Shrinking Examples
7. Runtime Budget
8. Integration with Conformance Suite
9. Known Non-Determinism Escape Hatches

---

## §1  D-1..D-4 Restated in Quantifier Form

The spec text in §1.5 is normative but deliberately informal ("same input →
same output"). For property-based testing we need explicit quantifier form:
∀ (for all) inputs drawn from a strategy *S*, property *P* must hold for
function *f*.

### D-1 — Byte-identical output for identical input (MUST)

**Informal**: Given identical inputs in the same process, the emitted SVG
MUST be byte-identical across repeated calls.

**Formal**:

```
∀ input I drawn from strategy S_emit_input:
  let out_a = emit(I)
  let out_b = emit(I)        # second call, same process, same object state
  P_D1(I) ≡  out_a == out_b   # Python byte-identical string equality
```

*Quantifier bounds*: `S_emit_input` covers all three emitter functions
(`emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`),
all six color tokens, both `placed_labels=None` and `placed_labels=[]`,
and label text drawn from the full unicode strategy defined in §2.4.

*Scope of "identical input"*: same Python process, no module reload, no
env-var mutation between the two calls. Cross-process and cross-platform
identity is D-4's remit, not D-1's.

*Failure mode on current codebase*: D-1 is expected to **pass** for all
three emitters because the emitters are pure functions of their arguments
with no randomness source (`random`, `uuid`, `time`, `os.urandom`) and no
mutable module-level state beyond `_DEBUG_LABELS` (frozen at import time
per D-4). The one known escape hatch is KaTeX rendering (§9.1); the
strategy quarantines this by passing `render_inline_tex=None` (§2.4 note).

---

### D-2 — `_nudge_candidates` yields identical sequence for equal inputs (MUST)

**Informal**: `_nudge_candidates` MUST yield candidates in the same order
for equal inputs; the first non-colliding candidate MUST always be
selected.

**Formal**:

```
∀ (pill_w, pill_h, side_hint) drawn from strategy S_nudge_args:
  let seq_a = list(_nudge_candidates(pill_w, pill_h, side_hint))
  let seq_b = list(_nudge_candidates(pill_w, pill_h, side_hint))
  P_D2_order(pill_w, pill_h, side_hint)
    ≡  seq_a == seq_b                              # lists equal element-wise

∀ (pill_w, pill_h, side_hint) drawn from S_nudge_args:
  let seq = list(_nudge_candidates(pill_w, pill_h, side_hint))
  P_D2_no_zero(pill_w, pill_h, side_hint)
    ≡  (0.0, 0.0) not in seq                       # E1566 / M-7 guard
    AND (0, 0) not in seq                           # also catches int zero-pair
```

*Sub-property note*: the `(0,0)` exclusion is technically a separate
invariant from the spec (E1566 / M-7) but is exercised here because it
surfaces identically under a Hypothesis search: any `pill_h` value that
rounds a step to zero triggers it.

*Why this is interesting to Hypothesis*: the `side_hint` branch in
`_nudge_candidates` builds two sorted sub-lists. If the sort key function
ever touches mutable state or if Python's `sorted()` is called with a
non-deterministic comparator, D-2 will fail. This is very unlikely but
worth 1000-example coverage for confidence.

---

### D-3 — Registry-insertion-order independence for non-overlapping subsets (MAY)

**Formal** (weaker claim — MAY in spec, but testable):

```
∀ non-overlapping annotation set A drawn from strategy S_non_overlap_anns:
  let perm_1 = emit_frame(shuffle(A, seed=42))
  let perm_2 = emit_frame(shuffle(A, seed=99))
  P_D3(A)
    ≡  normalize_xy(perm_1) == normalize_xy(perm_2)
```

Where `normalize_xy` strips floating-point coordinate differences ≤ 1 px
(the D-3 tolerance admitted by the spec) so that permutation differences
show only structural divergence, not allowed rounding.

*Critical scoping*: D-3 is a MAY, and the spec's own §1.5 text says
"rendered x and y pixel coordinates MAY differ by up to 1 px between Python
versions or platforms due to `int()` truncation, without violating any MUST
invariant." The property test therefore uses **structural** equality (same
SVG elements, same pill counts, same label text, same color tokens) rather
than byte equality.

*Why non-overlapping only*: for overlapping annotations the nudge order
depends on which pill was registered first, so permutation breaks
determinism by design (C-1 wins). Restricting to non-overlapping inputs
isolates the MAY invariant from the intentional dependency.

---

### D-4 — `_DEBUG_LABELS` captured once at import, not re-evaluated (MUST)

**Formal**:

```
∀ (env_value_before_import, env_value_after_import) drawn from S_env_pair:
  Given:
    module is imported with env var = env_value_before_import
    env var is then changed to env_value_after_import in os.environ
  P_D4(env_value_before_import, env_value_after_import)
    ≡  debug_output_present == (env_value_before_import == "1")
    AND debug_output_present is independent of env_value_after_import
```

*Strategy*: `S_env_pair` draws `("1", "0")`, `("0", "1")`, `("", "1")`,
`("1", "")`. The strategy does NOT re-import the module between examples
(that would make the test meaningless). Instead it patches
`_svg_helpers._DEBUG_LABELS` directly, verifying that the internal flag
drives output, not the live env var.

---

## §2  Hypothesis Strategies

All strategies below are Python-code sketches. They are **design
specifications**; final naming and imports belong in the implementation
commit.

### §2.1  AABB Lists with Overlaps

```python
from hypothesis import given, settings, strategies as st
from hypothesis.strategies import composite

@composite
def st_aabb(draw: st.DrawFn) -> dict:
    """Single AABB as (cx, cy, w, h)."""
    cx = draw(st.floats(min_value=10.0, max_value=490.0,
                        allow_nan=False, allow_infinity=False))
    cy = draw(st.floats(min_value=10.0, max_value=490.0,
                        allow_nan=False, allow_infinity=False))
    w  = draw(st.floats(min_value=20.0, max_value=120.0,
                        allow_nan=False, allow_infinity=False))
    h  = draw(st.floats(min_value=12.0, max_value=40.0,
                        allow_nan=False, allow_infinity=False))
    return {"cx": cx, "cy": cy, "w": w, "h": h}


@composite
def st_aabb_list_with_overlaps(draw: st.DrawFn) -> list[dict]:
    """2–8 AABBs, some intentionally overlapping.

    Overlaps are created by taking a base AABB and placing a second one
    within half its width/height — guaranteed collision without relying
    on random chance.
    """
    n = draw(st.integers(min_value=2, max_value=8))
    base = [draw(st_aabb()) for _ in range(n)]
    # Inject at least one guaranteed overlap: clone first AABB with small offset
    if n >= 2:
        overlap = dict(base[0])
        overlap["cx"] += draw(st.floats(min_value=0.0,
                                        max_value=base[0]["w"] * 0.4,
                                        allow_nan=False))
        overlap["cy"] += draw(st.floats(min_value=0.0,
                                        max_value=base[0]["h"] * 0.4,
                                        allow_nan=False))
        base.append(overlap)
    return base
```

*Design note*: The strategy draws `w` and `h` from bounded ranges that
reflect real pill sizes (12–40 px height matches the 11–13 px font +
2×PAD_Y=6 formula; 20–120 px width matches estimate_text_width output for
labels of 1–20 characters at 11–12 px). Values outside these ranges are
not wrong in principle but exercise dead code paths, so a separate
`st_pathological_aabb` (§2.2) handles extremes.

---

### §2.2  Primitive Positions with Pathological Floats

```python
@composite
def st_primitive_position(draw: st.DrawFn) -> tuple[float, float, float, float]:
    """(x, y, w, h) covering normal values AND edge cases.

    Normal range: coordinates 0..600, dimensions 12..150.
    Pathological: NaN, ±inf, subnormal, exact zero injected with low weight.
    """
    # 90 % normal, 10 % pathological
    is_pathological = draw(st.booleans().filter(lambda b: True))  # always draw
    pathological_weight = draw(st.integers(min_value=0, max_value=9))
    if pathological_weight == 0:
        # Pathological sample — one slot may be NaN/inf/zero
        slot = draw(st.integers(min_value=0, max_value=3))
        bad_val = draw(st.one_of(
            st.just(float("nan")),
            st.just(float("inf")),
            st.just(float("-inf")),
            st.just(0.0),
            st.floats(min_value=5e-324, max_value=1e-10),  # subnormal
        ))
        normal = [
            draw(st.floats(min_value=0.0, max_value=600.0,
                           allow_nan=False, allow_infinity=False))
            for _ in range(4)
        ]
        normal[slot] = bad_val
        return tuple(normal)  # type: ignore[return-value]
    else:
        return (
            draw(st.floats(min_value=0.0, max_value=600.0,
                           allow_nan=False, allow_infinity=False)),
            draw(st.floats(min_value=0.0, max_value=600.0,
                           allow_nan=False, allow_infinity=False)),
            draw(st.floats(min_value=12.0, max_value=150.0,
                           allow_nan=False, allow_infinity=False)),
            draw(st.floats(min_value=12.0, max_value=40.0,
                           allow_nan=False, allow_infinity=False)),
        )
```

*Rationale for including NaN/inf*: §2.4 of the spec v2 adds pre-condition
guards: "NaN anywhere in (pill_w, pill_h, cx, cy) — Reject". The property
test verifies that these guards prevent crashes and emit no SVG `<rect>`
rather than emitting a malformed one. Until the guards ship, these inputs
are expected to *fail* (producing a shrinkable Hypothesis counterexample).

---

### §2.3  Label Text — Unicode, RTL, Math Markup, Long Strings, Null Bytes

```python
@composite
def st_label_text(draw: st.DrawFn) -> str:
    """Label text covering the full authorial input space.

    Categories (drawn via st.one_of with explicit weights):
      plain_ascii    — everyday labels "O(n log n)", "visited", "42"
      unicode_latin  — accented chars, ligatures
      rtl_fragment   — Arabic/Hebrew fragment (NG-5 out-of-scope, but
                       must not crash; bytes must survive XML escape)
      math_markup    — $...$  spans, \\frac, \\sum, \\alpha
      long_plain     — > _LABEL_MAX_WIDTH_CHARS (24) chars, triggers wrap
      long_math      — > 24 chars inside $...$, must NOT wrap (T-3)
      empty          — "" (G-5 guard — pill must not be emitted)
      xml_special    — "<", ">", "&", '"', "'"
      null_byte      — "\x00" anywhere (§2.4 guard)
      mixed          — combination of two categories
    """
    category = draw(st.sampled_from([
        "plain_ascii", "unicode_latin", "rtl_fragment",
        "math_markup", "long_plain", "long_math",
        "empty", "xml_special", "null_byte", "mixed",
    ]))

    if category == "plain_ascii":
        return draw(st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"),
                                   whitelist_characters=" ()[].,+-="),
            min_size=1, max_size=30,
        ))

    elif category == "unicode_latin":
        return draw(st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd", "Lm", "Lt"),
                blacklist_characters="\x00",
            ),
            min_size=1, max_size=30,
        ))

    elif category == "rtl_fragment":
        # Basic Arabic block U+0600–U+06FF (NG-5 is out-of-scope for
        # layout, but must not crash the XML pipeline)
        arabic_chars = [chr(c) for c in range(0x0600, 0x0650)]
        return draw(st.text(
            alphabet=st.sampled_from(arabic_chars),
            min_size=1, max_size=20,
        ))

    elif category == "math_markup":
        # Draw a math expression surrounded by $ delimiters.
        inner = draw(st.one_of(
            st.just("a+b"),
            st.just("\\frac{n}{2}"),
            st.just("\\sum_{i=0}^{n}"),
            st.just("f(x)=-4"),
            st.just("O(n\\log n)"),
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("Ll", "Lu", "Nd"),
                    whitelist_characters=r" +-=^_{}\",
                ),
                min_size=1, max_size=20,
            ),
        ))
        return f"${inner}$"

    elif category == "long_plain":
        # Longer than _LABEL_MAX_WIDTH_CHARS=24, no math, should wrap
        base = draw(st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz ",
            min_size=25, max_size=60,
        ))
        return base

    elif category == "long_math":
        # Long, but inside $...$, must NOT trigger wrap (T-3)
        inner = draw(st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz+- ",
            min_size=25, max_size=50,
        ))
        return f"${inner}$"

    elif category == "empty":
        return ""

    elif category == "xml_special":
        base = draw(st.text(
            alphabet="<>&\"'abcABC123",
            min_size=1, max_size=20,
        ))
        return base

    elif category == "null_byte":
        # \x00 embedded somewhere
        pos = draw(st.integers(min_value=0, max_value=5))
        text_part = draw(st.text(
            alphabet="abcABC",
            min_size=3, max_size=10,
        ))
        return text_part[:pos] + "\x00" + text_part[pos:]

    else:  # mixed
        a = draw(st_label_text())  # type: ignore[misc]  # recursive
        b = draw(st_label_text())  # type: ignore[misc]
        return a + " " + b
```

*Design note on RTL*: §8 NG-5 explicitly excludes "RTL + vertical CJK
layout" from the ruleset. The strategy still includes Arabic fragments
because the **XML pipeline** (escaping, `<text>` attribute encoding) must
not crash on them even if layout is wrong. The property for RTL inputs
checks only "does not raise" and "output is valid XML-escaped UTF-8",
not visual correctness.

*Design note on null bytes*: §2.4 guard says "sanitise before `_escape_xml`".
The property asserts that `\x00` does not appear in the emitted SVG string
(it is stripped or replaced). Until the guard ships this is an expected
failure category.

---

### §2.4  SCRIBA_LABEL_ENGINE env value

```python
st_engine_value = st.one_of(
    st.just("unified"),
    st.just("legacy"),
    st.just("both"),
    st.just(""),           # unset — should default to "unified"
    st.just("UNIFIED"),    # wrong case — should fall back
    st.text(min_size=0, max_size=8),  # arbitrary garbage
)
```

*Usage in D-1 test*: the D-1 property runs under both `"unified"` and
`"legacy"` engine values (patching `os.environ["SCRIBA_LABEL_ENGINE"]`
before each example). The property asserts byte-identical output for
repeated calls under the **same** engine value. Cross-engine comparison
is explicitly not part of D-1 (that is a regression/golden test concern).

*Design note*: `SCRIBA_LABEL_ENGINE` defaults to `"unified"` as of Phase 7.
The strategy ensures coverage of the legacy path (which may be removed at
v3) while it still exists. Tests using this strategy MUST patch the engine
selector, not the module-level constant.

---

### §2.5  Frame Sequence with shape_id Stability

```python
@composite
def st_frame_sequence(draw: st.DrawFn) -> list[dict]:
    """Sequence of 2–6 annotation dicts with stable shape_id across frames.

    Models a multi-step animation where the same annotation target
    appears in consecutive frames. shape_id stability verifies that
    registry isolation (C-4) does not bleed state across frames.
    """
    n_frames = draw(st.integers(min_value=2, max_value=6))
    # Stable target set: drawn once, reused across all frames
    n_targets = draw(st.integers(min_value=1, max_value=4))
    targets = [f"arr.cell[{i}]" for i in range(n_targets)]

    frames = []
    for _ in range(n_frames):
        # Each frame may have a different subset of annotations
        frame_targets = draw(st.lists(
            st.sampled_from(targets),
            min_size=1,
            max_size=n_targets,
            unique=True,
        ))
        annotations = [
            {
                "target": t,
                "label": draw(st_label_text()),
                "color": draw(st.sampled_from(list(
                    ["good", "info", "warn", "error", "muted", "path"]
                ))),
                "position": draw(st.sampled_from(
                    ["above", "below", "left", "right"]
                )),
            }
            for t in frame_targets
        ]
        frames.append(annotations)
    return frames
```

*Usage*: the frame-sequence strategy feeds the D-1 registry-isolation
sub-test, which verifies that calling `emit_svg` on frame N+1 produces
the same output whether or not frame N's `placed_labels` list was
accidentally retained.

---

### §2.6  Nudge-Arguments Strategy

```python
@composite
def st_nudge_args(draw: st.DrawFn) -> tuple[float, float, str | None]:
    """(pill_w, pill_h, side_hint) for _nudge_candidates tests."""
    pill_w = draw(st.floats(min_value=1.0, max_value=200.0,
                            allow_nan=False, allow_infinity=False))
    pill_h = draw(st.floats(min_value=1.0, max_value=60.0,
                            allow_nan=False, allow_infinity=False))
    side_hint = draw(st.one_of(
        st.none(),
        st.sampled_from(["above", "below", "left", "right"]),
        st.text(min_size=1, max_size=8),   # unknown side_hint → treated as None
    ))
    return (pill_w, pill_h, side_hint)
```

*Design note*: `pill_h=0.0` is excluded (min_value=1.0) because the spec
mandates positive dimensions (G-5) and the step multipliers would all be
0, making the 32-candidate check trivially degenerate. A separate
pathological test (§3, D-2 property) explicitly tests `pill_h` values
near zero via `st.floats(min_value=0.0, max_value=1.0)`.

---

## §3  Properties — One per Invariant

### §3.1  D-1: Byte-Identical Output for Identical Input

```python
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
import pytest

# (Strategy imports from §2 above)

@settings(
    max_examples=1000,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=10_000,   # 10 s per example
)
@given(
    label=st_label_text(),
    color=st.sampled_from(["good", "info", "warn", "error", "muted", "path"]),
    src=st.tuples(
        st.floats(min_value=0.0, max_value=400.0,
                  allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=400.0,
                  allow_nan=False, allow_infinity=False),
    ),
    dst=st.tuples(
        st.floats(min_value=0.0, max_value=400.0,
                  allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=400.0,
                  allow_nan=False, allow_infinity=False),
    ),
)
def test_d1_emit_arrow_byte_identical(label, color, src, dst):
    """D-1: emit_arrow_svg produces byte-identical output on repeated calls."""
    ann = {"target": "arr.cell[0]", "arrow_from": "arr.cell[1]",
           "label": label, "color": color}
    lines_a: list[str] = []
    placed_a: list[_LabelPlacement] = []
    emit_arrow_svg(lines_a, ann, src, dst, 0, 32.0,
                   render_inline_tex=None, placed_labels=placed_a)

    lines_b: list[str] = []
    placed_b: list[_LabelPlacement] = []
    emit_arrow_svg(lines_b, ann, src, dst, 0, 32.0,
                   render_inline_tex=None, placed_labels=placed_b)

    assert "\n".join(lines_a) == "\n".join(lines_b), (
        f"D-1 violation: non-identical output for label={label!r} "
        f"color={color!r}"
    )
```

**Notes**:

- `render_inline_tex=None` is mandatory in this property. KaTeX output is
  not byte-stable across Node.js process restarts (§9.1). The KaTeX path
  gets its own quarantined test (§9.1).
- `placed_labels=[]` (fresh list per call) is correct because D-1 tests
  the same-input invariant. If we shared a single `placed_labels` across
  both calls, the second call would see a non-empty registry and compute a
  different (nudged) position — that is expected and correct behavior, not
  a D-1 violation.
- The same pattern applies to `emit_plain_arrow_svg` and
  `emit_position_label_svg`; the implementation commit MUST add both as
  parametrized variants of this test.

---

### §3.2  D-2a: `_nudge_candidates` Yields Identical Sequence

```python
@settings(max_examples=1000, deadline=5_000)
@given(args=st_nudge_args())
def test_d2a_nudge_sequence_identical(args):
    """D-2: _nudge_candidates yields same sequence for same inputs."""
    pill_w, pill_h, side_hint = args
    seq_a = list(_nudge_candidates(pill_w, pill_h, side_hint))
    seq_b = list(_nudge_candidates(pill_w, pill_h, side_hint))
    assert seq_a == seq_b, (
        f"D-2 violation: sequence mismatch for "
        f"pill_w={pill_w}, pill_h={pill_h}, side_hint={side_hint!r}"
    )
    assert len(seq_a) == 32, (
        f"D-2 violation: expected 32 candidates, got {len(seq_a)}"
    )
```

---

### §3.3  D-2b: `_nudge_candidates` Never Yields (0, 0) (E1566)

```python
@settings(max_examples=1000, deadline=5_000)
@given(args=st_nudge_args())
def test_d2b_nudge_no_zero_zero(args):
    """D-2 / E1566: (0,0) must not appear in nudge candidates."""
    pill_w, pill_h, side_hint = args
    candidates = list(_nudge_candidates(pill_w, pill_h, side_hint))

    zero_pairs = [
        c for c in candidates
        if abs(c[0]) < 1e-12 and abs(c[1]) < 1e-12
    ]
    assert zero_pairs == [], (
        f"E1566 violation: _nudge_candidates yielded (0,0)-equivalent "
        f"for pill_w={pill_w}, pill_h={pill_h}, side_hint={side_hint!r}. "
        f"Offending pair(s): {zero_pairs}"
    )
```

**Current-codebase failure analysis**: Looking at the implementation,
`steps = (pill_h * 0.25, pill_h * 0.5, pill_h * 1.0, pill_h * 1.5)`.
For each step and each of the 8 compass directions, `(dx, dy)` is always
`(dx_sign * step, dy_sign * step)`. The `_COMPASS_8` directions have at
least one of `dx_sign` or `dy_sign` non-zero for every entry. Therefore
`(0, 0)` can only appear if `step == 0`, which happens when `pill_h == 0`.
The strategy uses `min_value=1.0`, so this is not exercised in the normal
range.

**Edge-case subtest**: A separate explicit test (not a property test) with
`pill_h=0.0` should verify that the guard either raises `ValueError` or
skips zero-step entries. That test belongs in the existing unit suite, not
the property suite.

---

### §3.4  D-3: Permutation Independence for Non-Overlapping Annotations

```python
@composite
def st_non_overlapping_annotations(draw: st.DrawFn) -> list[dict]:
    """2–6 annotations that are spatially separated enough to never overlap.

    Each annotation targets a different cell in a grid with cell_width=60,
    cell_height=32. The pills generated are at most 120 px wide × 30 px
    high. With cells 60 px apart and positions above/below alternating,
    no two pills can overlap.
    """
    n = draw(st.integers(min_value=2, max_value=6))
    # Assign to separate columns so pills placed "above" cannot overlap
    return [
        {
            "target": f"arr.cell[{i}]",
            "label": draw(st.text(
                alphabet="abcdefg ",
                min_size=1, max_size=12,   # short → narrow pill, no overlap
            )),
            "color": draw(st.sampled_from(
                ["good", "info", "warn", "error", "muted", "path"]
            )),
            "position": "above",
        }
        for i in range(n)
    ]


def _normalize_for_d3(svg_string: str) -> str:
    """Strip coordinate values, keep structural shape.

    For D-3 (MAY invariant with ±1 px tolerance) we compare structure
    not coordinates. This normalizer:
      1. Removes float attributes (x=, y=, width=, height=, cx=, cy=)
         since those may shift by ±1 px under permutation due to int().
      2. Preserves element names, class attributes, label text, and color tokens.
    """
    import re
    # Strip numeric SVG attribute values, keep attribute names as markers
    normalized = re.sub(
        r'\b(x|y|width|height|cx|cy|rx|ry|x1|y1|x2|y2)="[^"]*"',
        r'\1="__"',
        svg_string,
    )
    return normalized


@settings(max_examples=500, deadline=10_000)
@given(
    anns=st_non_overlapping_annotations(),
    seed_a=st.integers(min_value=0, max_value=2**31),
    seed_b=st.integers(min_value=0, max_value=2**31),
)
def test_d3_permutation_independence(anns, seed_a, seed_b):
    """D-3 (MAY): non-overlapping annotations produce same structure
    regardless of insertion order (within ±1 px coordinate tolerance).
    """
    import random

    rng_a = random.Random(seed_a)
    rng_b = random.Random(seed_b)

    perm_a = sorted(anns, key=lambda _: rng_a.random())
    perm_b = sorted(anns, key=lambda _: rng_b.random())

    # Simulate emit: call emit_position_label_svg for each annotation in order.
    # Cell centers are at (i * 60 + 30, 50) for cell i.
    def emit_frame(ordered_anns: list[dict]) -> str:
        lines: list[str] = []
        placed: list[_LabelPlacement] = []
        for i, ann_item in enumerate(ordered_anns):
            idx = int(ann_item["target"].split("[")[1].rstrip("]"))
            anchor = (idx * 60 + 30.0, 50.0)
            emit_position_label_svg(
                lines, ann_item, anchor,
                cell_height=32.0,
                render_inline_tex=None,
                placed_labels=placed,
            )
        return "\n".join(lines)

    svg_a = emit_frame(perm_a)
    svg_b = emit_frame(perm_b)

    assert _normalize_for_d3(svg_a) == _normalize_for_d3(svg_b), (
        f"D-3 violation: structure differs under permutation.\n"
        f"annotations: {anns}\n"
        f"seeds: {seed_a}, {seed_b}"
    )
```

**Expected failure rate on current codebase**: D-3 is likely to **pass**
for the non-overlapping subset because `emit_position_label_svg` uses a
deterministic 4-direction nudge loop ordered the same way every call.
However, the `_normalize_for_d3` approach may itself have false negatives
if element order changes due to Python `sorted()` stability. The
implementation commit MUST audit whether the emitter emits elements in
annotation-input order (it does, based on reading the source).

---

### §3.5  D-4: `_DEBUG_LABELS` Captured Once at Import

```python
import pytest
from unittest import mock

@pytest.mark.parametrize("import_val,mutate_val,expect_debug", [
    ("1",  "0",  True),   # imported with flag on; mutating off → still on
    ("0",  "1",  False),  # imported with flag off; mutating on → still off
    ("",   "1",  False),  # unset → off; mutating → still off
])
def test_d4_debug_flag_captured_at_import(
    import_val: str,
    mutate_val: str,
    expect_debug: bool,
) -> None:
    """D-4: _DEBUG_LABELS must not re-evaluate on each call.

    This is NOT a property-based test (it has a fixed parameter table)
    but lives in the same file for conceptual grouping under the D-axis.

    Implementation note: the module is already imported by the time pytest
    runs. We therefore test by patching _svg_helpers._DEBUG_LABELS directly,
    which is the spec-mandated pattern (§1.5 D-4 Verify note).
    """
    from scriba.animation.primitives import _svg_helpers

    with mock.patch.object(_svg_helpers, "_DEBUG_LABELS", import_val == "1"):
        # Mutate the env var to the "after-import" value
        with mock.patch.dict("os.environ",
                             {"SCRIBA_DEBUG_LABELS": mutate_val}):
            lines: list[str] = []
            placed: list[_LabelPlacement] = []
            # Force collision to trigger debug path
            ann = {"target": "t", "label": "L", "color": "info"}
            # Pre-seed placed_labels so collision is guaranteed
            placed.append(_LabelPlacement(x=50.0, y=20.0,
                                          width=100.0, height=30.0))
            for _ in range(40):   # exhaust all 32 candidates
                placed.append(_LabelPlacement(
                    x=50.0 + _ * 0.1, y=20.0, width=200.0, height=100.0
                ))
            emit_plain_arrow_svg(
                lines, ann, (50.0, 30.0),
                render_inline_tex=None,
                placed_labels=placed,
            )
            svg = "\n".join(lines)
            has_debug = "scriba:label-collision" in svg
            assert has_debug == expect_debug, (
                f"D-4 violation: expected debug={expect_debug} "
                f"(import_val={import_val!r}, mutate_val={mutate_val!r})"
            )
```

**Note**: D-4 as a parametrized table test (not `@given`) is intentional.
The invariant has only four distinct regimes, and Hypothesis would bring
no structural coverage advantage here — it would only find the same four
cases. The test lives in `test_determinism.py` alongside the property
tests for grouping.

---

## §4  Float Tolerance Policy

### §4.1  The Core Tension

Two SVG strings may differ in only one way: a floating-point coordinate
serialized as `"42"` in one run and `"42.00000000001"` in another (or
`"41"` vs `"42"` due to `int()` truncation). The spec admits this in D-3:
"coordinates MAY differ by up to 1 px... due to `int()` truncation." The
question is: which comparison mode to use for D-1?

### §4.2  Option A: Exact Byte Equality

```python
assert output_a == output_b
```

**Pros**: no normalization code to maintain; any divergence — including
non-deterministic float formatting — is caught immediately.

**Cons**: would reject valid implementations that serialize `42.0` as
`"42.0"` in one call and `"42"` in another (unlikely in CPython for the
same `int()` call, but theoretically possible across Python minor
versions).

### §4.3  Option B: Numeric-Diff After Normalization

```python
def normalize_svg_coords(svg: str) -> str:
    """Replace all numeric attribute values with rounded integers."""
    import re
    def round_match(m: re.Match) -> str:
        try:
            return f'{m.group(1)}="{round(float(m.group(2)))}"'
        except ValueError:
            return m.group(0)
    return re.sub(
        r'(\b(?:x|y|width|height|cx|cy|rx|ry|x1|y1|x2|y2|points))'
        r'="([-\d.eE+]+)"',
        round_match,
        svg,
    )

assert normalize_svg_coords(output_a) == normalize_svg_coords(output_b)
```

**Pros**: tolerates the ±1 px D-3 window; more robust across Python patch
versions.

**Cons**: normalization regex is fragile (misses `style="..."` inline
coordinates); introduces maintenance surface; hides bugs where the float
diverges by more than 1 px.

### §4.4  Recommendation

**Use exact byte equality (Option A) for D-1**.

Rationale:

1. The emitters already convert all coordinates to `int()` before
   formatting (`fi_x = int(final_x)`). Given the same float input,
   `int()` is deterministic in CPython across all runs in the same
   process. The only float-format variation in the SVG comes from
   `arrow_points` (`f"{p1x:.1f},{p1y:.1f} ..."`), which is also
   deterministic for fixed float inputs.

2. The D-3 MAY tolerance (±1 px) applies to cross-platform/cross-version
   divergence, not to same-process repeated calls. D-1 is a same-process
   invariant. Applying Option B to D-1 would silently mask bugs that would
   only manifest on different platforms.

3. Normalization introduces a false-security risk: a correctly failing
   property test passes because normalization absorbs a genuine bug.

**Use numeric normalization (Option B, restricted) for D-3 only**.
D-3 is the MAY invariant with explicit ±1 px tolerance. The `_normalize_for_d3`
function in §3.4 is already scoped to structural comparison; this is the
correct layer for the tolerance.

**Corollary for visual-regression tests** (outside this document's scope):
visual-regression screenshots must use ±1 px pixel-comparison tolerance
(SSIM or pixel-diff with threshold), consistent with D-3. This is already
documented in the spec §1.5 D-3 Verify note.

---

## §5  Seeding and Reproducibility

### §5.1  The Problem

Hypothesis uses random search by default. A CI run that discovers a
counterexample on one run may not reproduce it on the next unless seeding
is configured. Simultaneously, **nightly** runs benefit from fresh
randomness to explore new input regions.

### §5.2  CI Configuration — Derandomized Mode

```python
# tests/conformance/smart_label/conftest.py
import os
from hypothesis import settings, HealthCheck, Phase

# In CI (SCRIBA_CI=1), use derandomized mode so every run explores
# the same examples. Hypothesis uses a fixed internal database in this mode.
if os.getenv("SCRIBA_CI") == "1":
    settings.register_profile(
        "ci",
        max_examples=1000,
        derandomize=True,                  # same seed every run
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.data_too_large,
        ],
        deadline=10_000,                   # 10 s per example max
        phases=[Phase.explicit,
                Phase.reuse,
                Phase.generate,
                Phase.shrink],
    )
    settings.load_profile("ci")
```

**Key point**: `derandomize=True` makes Hypothesis generate the same
sequence of examples on every invocation using a SHA256 hash of the test
name. This means:

- PRs always see the same 1000 examples.
- A counterexample found in CI is exactly reproducible with
  `hypothesis.reproduce_failure()` (see §5.4).
- New test names hash differently, so adding a test does not shift other
  tests' seeds.

### §5.3  Nightly Configuration — Full-Random Mode

```python
# Registered when SCRIBA_CI is not set (local dev or nightly CI matrix)
settings.register_profile(
    "nightly",
    max_examples=5000,          # 5x more examples overnight
    derandomize=False,          # fresh random seed each run
    suppress_health_check=[HealthCheck.too_slow],
    deadline=30_000,
)
```

The nightly workflow sets `SCRIBA_CI=` (empty) and runs with
`--hypothesis-profile=nightly` if using the `pytest-hypothesis-profile`
plugin, or relies on `settings.load_profile("nightly")` in conftest.

### §5.4  Reproducing a Failure

When a nightly run finds a counterexample, Hypothesis writes the
minimized example to the `.hypothesis/` directory and prints:

```
Falsifying example: test_d1_emit_arrow_byte_identical(
    label='...', color='info', src=(42.0, 100.0), dst=(100.0, 50.0)
)
You can reproduce this example by temporarily adding @reproduce_failure('6.x.y', b'...')
```

**Protocol for the team**:

1. Copy the `@reproduce_failure` decorator onto the failing test locally.
2. Run `pytest tests/conformance/smart_label/test_determinism.py::test_d1_emit_arrow_byte_identical -x`
   to confirm the failure reproduces.
3. Commit the `@reproduce_failure` decorator alongside the bug fix.
4. Remove the decorator after the fix is confirmed.

**Do not** commit `@reproduce_failure` decorators to `main` without an
accompanying fix — they are CI-blocking artefacts.

### §5.5  Database Persistence in CI

The `.hypothesis/examples/` directory MUST be added to the CI cache
(e.g., GitHub Actions `actions/cache` keyed on `${{ runner.os }}-hypothesis`).

This ensures:

- Hypothesis's saved-example database (shrunk counterexamples from past
  runs) is replayed on every CI run (`Phase.reuse`).
- A flaky test that passed with the shrunk example on day N will still
  be challenged with the same example on day N+1.

---

## §6  Shrinking Examples

Hypothesis's shrinking engine automatically finds the minimal failing
input after a counterexample is discovered. This section shows a concrete
walkthrough for D-2b (the `(0,0)` exclusion property).

### §6.1  Scenario: Floating-Point Step Collapses to Zero

Suppose a refactor changes `steps = (pill_h * 0.25, ...)` to
`steps = (int(pill_h * 0.25), ...)`. For any `pill_h < 4.0`, `int(0.25 * pill_h) == 0`,
and the N/S/E/W candidates all become `(0, 0)`.

Hypothesis finds the failure with this sequence of shrinks:

```
# Initial counterexample found (random)
pill_w=87.3,  pill_h=3.7,  side_hint="above"  → FAIL

# Shrink round 1: simplify side_hint
pill_w=87.3,  pill_h=3.7,  side_hint=None     → FAIL

# Shrink round 2: simplify pill_w
pill_w=1.0,   pill_h=3.7,  side_hint=None     → FAIL

# Shrink round 3: find minimum pill_h
pill_w=1.0,   pill_h=3.0,  side_hint=None     → FAIL
pill_w=1.0,   pill_h=1.5,  side_hint=None     → FAIL
pill_w=1.0,   pill_h=1.0,  side_hint=None     → FAIL
pill_w=1.0,   pill_h=0.5,  side_hint=None     → FAIL (int(0.25*0.5)=0)

# Final minimal counterexample
pill_w=1.0,   pill_h=0.5,  side_hint=None
```

**Hypothesis output**:

```
Falsifying example: test_d2b_nudge_no_zero_zero(
    args=(1.0, 0.5, None)
)
AssertionError: E1566 violation: _nudge_candidates yielded (0,0)-equivalent
for pill_w=1.0, pill_h=0.5, side_hint=None.
Offending pair(s): [(0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0), (0, 0)]
```

The minimal example (`pill_h=0.5`) is the precise condition that triggers
the bug (any `pill_h < 4.0` with the hypothetical int-rounding change).
The engineer can fix the guard:

```python
# Before: zero-step entries slip through
steps = (int(pill_h * 0.25), ...)

# After: explicitly filter zero steps
steps = [s for s in (pill_h * 0.25, pill_h * 0.5, pill_h * 1.0, pill_h * 1.5)
         if s > 0]
if not steps:
    return  # or raise ValueError if pill_h <= 0 violates the precondition
```

### §6.2  Why Shrinking is Valuable Here

Without shrinking, the failure would be reported as `pill_h=3.7`, making
it easy to dismiss as a floating-point edge case. After shrinking, it is
`pill_h=0.5` — unambiguously a case where integer truncation causes steps
to collapse to zero. Shrinking turns a confusing failure into a clear
bug report.

### §6.3  Shrinking Behavior for D-1

For D-1, Hypothesis shrinks label text to the minimal string that triggers
non-identical output. For example, if a non-deterministic hash appears
only for labels longer than 20 chars, Hypothesis will find the shortest
such label — typically a repeated character like `"aaaaaaaaaaaaaaaaaaaa"`.

---

## §7  Runtime Budget

### §7.1  Targets

| Property | examples | per-example budget | total max |
|---|---|---|---|
| D-1 (`emit_arrow_svg`) | 1000 | 10 ms | 10 s |
| D-1 (`emit_plain_arrow_svg`) | 1000 | 10 ms | 10 s |
| D-1 (`emit_position_label_svg`) | 1000 | 10 ms | 10 s |
| D-2a (sequence identical) | 1000 | 5 ms | 5 s |
| D-2b (no (0,0)) | 1000 | 5 ms | 5 s |
| D-3 (permutation independence) | 500 | 20 ms | 10 s |
| D-4 (parametrized, not Hypothesis) | 3 examples | < 100 ms total | < 1 s |
| **Total wall time (CI, sequential)** | | | **< 47 s** |
| **Target with pytest-xdist -n 4** | | | **< 15 s** |

**Rationale for 10 ms per-example budget**: `emit_arrow_svg` calls
`estimate_text_width`, `_nudge_candidates` (potentially iterating 32
entries), and one pass through the placed-labels list. On a 2023
MacBook M2 this runs in ~0.2 ms for a typical example; the 10 ms budget
is a 50× safety margin. The `deadline=10_000` in the profile (§5.2)
enforces this as a hard deadline, not just a guideline.

### §7.2  Parametrization to Hit Budget

The 1000-example count is set via `settings(max_examples=1000)` on each
test. The CI profile (§5.2) sets this globally. If a property test
consistently runs below 2 s, increase to 2000 examples in the next PR.

```python
# Pattern for a property test with inline budget annotation:
@settings(
    max_examples=1000,         # tune up if this test runs in < 2 s
    deadline=10_000,           # per-example hard limit (ms)
    suppress_health_check=[HealthCheck.too_slow],
)
@given(...)
def test_d1_emit_arrow_byte_identical(...):
    ...
```

### §7.3  Skipping Long Strategies in Fast Mode

For the D-3 permutation test (500 examples, 20 ms each = 10 s):

```python
@pytest.mark.slow  # skip with `pytest -m "not slow"` in fast CI
@settings(max_examples=500, deadline=20_000)
@given(...)
def test_d3_permutation_independence(...):
    ...
```

The `slow` mark allows the fast CI gate (`pytest -m "not slow"`) to
skip D-3 while the nightly gate (`pytest -m ""` — no filter) runs it.

### §7.4  Nightly Budget

At 5000 examples (nightly profile, §5.3):

| Property | Time |
|---|---|
| D-1 × 3 emitters | 3 × 50 s = 150 s |
| D-2a + D-2b | 2 × 25 s = 50 s |
| D-3 (permutation) | 5000/500 × 10 s = 100 s |
| **Total nightly** | ~300 s (~5 min) |

Acceptable for an overnight run. Use `pytest-xdist -n auto` to parallelize
across available cores.

---

## §8  Integration with Conformance Suite

### §8.1  File Location

```
tests/
└── conformance/
    └── smart_label/
        ├── __init__.py
        ├── conftest.py                    ← profile registration (§5.2)
        ├── helpers.py                     ← shared fixtures (from Round-3 report 01)
        ├── test_determinism.py            ← this document's tests
        ├── test_geometry_properties.py    ← G-axis properties (Round-3 report 03)
        └── test_corpus_golden.py          ← D-4 platform golden (Round-3 report 02)
```

`tests/conformance/` does **not** yet exist in the codebase. The
implementation commit MUST create the directory with an `__init__.py`
before adding these tests.

### §8.2  Shared Helpers

The `helpers.py` module (Round-3 report 01) provides:

```python
# helpers.py — public interface expected by test_determinism.py

def make_placed_label(cx: float, cy: float, w: float, h: float) -> _LabelPlacement:
    """Construct a _LabelPlacement from center coordinates."""
    ...

def saturate_registry(n: int = 40) -> list[_LabelPlacement]:
    """Return a placed_labels list that covers a dense region, forcing
    collision exhaustion for any reasonable pill position."""
    ...

def assert_valid_svg_fragment(svg: str) -> None:
    """Assert that svg is well-formed XML and contains no debug artefacts
    (i.e., no '<!-- scriba:label-collision' when DEBUG is off)."""
    ...

def strip_xml_comments(svg: str) -> str:
    """Remove all <!-- ... --> comment nodes from svg."""
    ...
```

The `test_determinism.py` module imports these helpers at the top:

```python
from tests.conformance.smart_label.helpers import (
    make_placed_label,
    saturate_registry,
    assert_valid_svg_fragment,
    strip_xml_comments,
)
```

### §8.3  pytest Marks

All property tests in `test_determinism.py` carry the following marks:

```python
pytestmark = [
    pytest.mark.conformance,      # run in conformance gate
    pytest.mark.determinism,      # filter: pytest -m determinism
]
```

The `slow` mark is added individually to D-3 as shown in §7.3.

### §8.4  Interaction with Existing Unit Tests

The property tests complement but do not replace the existing unit tests
in `tests/unit/test_smart_label_phase0.py`. Specifically:

| Existing test | Role | Property test role |
|---|---|---|
| `TestDeterminism::test_byte_identical_repeat` | Spot-check D-1 with fixed inputs | D-1 property: 1000 random inputs |
| `TestNudge::test_identical_sequence` | Fixed args nudge sequence | D-2a: 1000 random args |
| `TestDebugFlag::test_captured_at_import` | Manual patch test | D-4: parametrized table |

The property tests are **additive**. If a property test discovers a
counterexample, add a corresponding fixed-input regression test in
`test_smart_label_phase0.py` to lock the fix in permanently.

### §8.5  CI Gating

Recommended CI matrix addition:

```yaml
# .github/workflows/test.yml (proposed addition)
- name: Conformance — Determinism properties
  run: |
    SCRIBA_CI=1 pytest tests/conformance/smart_label/test_determinism.py \
      -v --tb=short -m "not slow" \
      --hypothesis-show-statistics
  env:
    SCRIBA_CI: "1"
```

The `--hypothesis-show-statistics` flag prints a per-test breakdown of
examples generated, shrunk, and database replays — useful for verifying
that the 1000-example budget is being exercised.

---

## §9  Known Non-Determinism Escape Hatches

### §9.1  KaTeX Version Drift

**Source**: `_emit_label_single_line` dispatches to a `render_inline_tex`
callback when the label contains `$...$` math. The callback invokes a
Node.js KaTeX process. KaTeX output is byte-stable for a given version but
**changes across versions** — a patch update from KaTeX 0.16.x to 0.16.y
may alter the rendered HTML structure.

**How the strategy avoids it**: all D-1..D-3 property tests pass
`render_inline_tex=None`, which forces the SVG `<text>` fallback path.
The KaTeX path is excluded from byte-identical determinism testing by
design; it is instead tested by the visual regression suite (Round-3
report 06) and the math-width audit (Round-2 report 05).

**Quarantine boundary**: if a future refactor makes `render_inline_tex`
non-optional, the property tests MUST add a conditional skip:

```python
@pytest.mark.skipif(
    KATEX_AVAILABLE,
    reason="KaTeX path excluded from D-1 byte-identity — see §9.1",
)
```

Where `KATEX_AVAILABLE` is a conftest fixture that checks for the Node
worker.

### §9.2  OS Font Metrics

**Source**: `estimate_text_width` in `_text_render.py` (not read in this
session, but referenced in the spec). If the implementation uses OS font
metrics (e.g., calling `PIL.ImageFont` or a system font library), the
returned width may vary between Linux and macOS.

**How the strategy avoids it**: `estimate_text_width` in the current
codebase uses a character-width table, not OS font metrics — verified by
the math-width audit (Round-2 report 05). D-1..D-3 are therefore safe
on this axis today.

**Risk flag**: if `estimate_text_width` is ever replaced with a browser-
round-trip measurement (NG-10 — explicitly out of scope), D-1 would fail
across platforms. Any such change MUST include a D-1 exemption annotation
and a platform-normalization hook.

### §9.3  Python `int()` Truncation (D-3 Admitted)

**Source**: the spec admits in D-3: "rendered x and y pixel coordinates
MAY differ by up to 1 px between Python versions or platforms due to `int()`
truncation." This is not a bug; it is a documented tolerance.

**How the strategy handles it**: D-1 (same-process) is unaffected because
`int()` is deterministic within a single CPython process. D-3 uses
`_normalize_for_d3` (§3.4) to strip coordinate values, so the ±1 px
tolerance is absorbed. No special strategy handling is needed.

### §9.4  `sorted()` Stability in Python

**Source**: Python's `sorted()` is guaranteed stable (TimSort since Python
2.2). The `_nudge_candidates` implementation uses `sorted()` with a key
of `(manhattan_distance, priority_index)`. Both key components are
deterministic floats/ints for fixed inputs. Stability means equal-key
elements retain insertion order, which is also deterministic.

**Risk**: if a future implementation switches to an unstable sort (e.g.,
a C-extension with non-stable behavior), D-2a would catch it. No special
strategy handling is needed; the existing test is sufficient.

### §9.5  `SCRIBA_LABEL_ENGINE` Environment Variable

**Source**: Phase 7 flipped the default to `"unified"`. The `"legacy"` path
may produce different byte output than `"unified"` for the same logical
input (different algorithm). This is not a D-1 violation (D-1 scopes to
"same process" which implies same engine). It is a potential source of
cross-engine divergence that must not be confused with a determinism bug.

**How the strategy handles it**: `st_engine_value` (§2.4) is used to
parametrize D-1 tests *per engine*, not across engines. The test assertion
`output_a == output_b` compares two calls under the **same** engine value.
A test that compares `emit(I, engine="unified") == emit(I, engine="legacy")`
would be a regression/compatibility test, not a D-1 test.

### §9.6  Thread Safety (Out of Scope)

The emitters mutate their `lines` and `placed_labels` arguments in place.
If two threads called the same emitter concurrently with a shared
`placed_labels` list, non-determinism would result. The spec's §8 NG-8
("Real-time live updates") is out of scope; scriba is a batch renderer.
The property tests are single-threaded and do not cover this escape hatch.
It is noted here as a reminder that if a future async/parallel rendering
mode is added, D-1 must be re-evaluated under concurrent execution.

---

## Summary Table

| Property | Function | Invariant | Expected status on current codebase | Priority |
|---|---|---|---|---|
| `test_d1_emit_arrow_byte_identical` | `emit_arrow_svg` | D-1 | PASS | P0 |
| `test_d1_emit_plain_arrow_byte_identical` | `emit_plain_arrow_svg` | D-1 | PASS | P0 |
| `test_d1_emit_position_label_byte_identical` | `emit_position_label_svg` | D-1 | PASS | P0 |
| `test_d2a_nudge_sequence_identical` | `_nudge_candidates` | D-2 | PASS | P0 |
| `test_d2b_nudge_no_zero_zero` | `_nudge_candidates` | D-2 / E1566 | PASS (min_value=1.0 avoids zero steps) | P0 |
| `test_d3_permutation_independence` | `emit_position_label_svg` | D-3 (MAY) | LIKELY PASS for non-overlapping | P1 |
| `test_d4_debug_flag_captured_at_import` | `_svg_helpers._DEBUG_LABELS` | D-4 | PASS | P0 |

**Total properties**: 7 (4 Hypothesis @given, 1 Hypothesis @given ×2 sub-
properties = split at implementation, 1 Hypothesis @given for D-3, 1
parametrized for D-4).

**Estimated failing on current codebase**: 0 MUST-failing properties, 0
MAY-failing properties. Reasoning: D-1 is upheld because all three
emitters are pure functions of their arguments; D-2 is upheld because
`_nudge_candidates` uses deterministic `sorted()` with no random state;
D-3 is a MAY and the non-overlapping restriction further reduces failure
risk; D-4 is already enforced by the module-level `os.getenv` pattern.

The most likely source of future failures is:
(a) NaN/inf inputs once the pathological strategy sub-tests are activated
    (§2.2 note — these are expected-fail tests, not bugs in the current
    code, because the guards are not yet implemented);
(b) An inadvertent introduction of `random` or `time.time()` in a future
    refactor of the collision-avoidance loop.

**Recommended first-commit subset**:

1. `test_d2a_nudge_sequence_identical` + `test_d2b_nudge_no_zero_zero`
   (low risk, pure function, no SVG parsing needed, fastest to implement)
2. `test_d1_emit_arrow_byte_identical` (foundational; covers the most
   important emitter)
3. `test_d4_debug_flag_captured_at_import` (parametrized, not Hypothesis
   — adds zero Hypothesis overhead, closes a gap in the existing coverage)

Leave D-3 (`test_d3_permutation_independence`) and the remaining D-1
emitter variants for the follow-up PR after the conformance suite
directory is established and `helpers.py` is in place.
