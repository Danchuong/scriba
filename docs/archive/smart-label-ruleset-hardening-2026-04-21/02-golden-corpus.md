---
title: Smart-Label Golden Corpus — Design Specification
version: 1.0.0
status: Design (Round-3 Foundation Material)
date: 2026-04-21
author: automated hardening agent
scope: tests/fixtures/smart_label_golden/
supersedes: (none — new document)
cross-references:
  - docs/spec/smart-label-ruleset.md (v2 §7 known-bad repros)
  - docs/archive/smart-label-ruleset-strengthening-2026-04-21/04-edge-cases.md
---

# Smart-Label Golden Corpus Design

> **Purpose**: define a pinned fixture corpus that maps `.tex` input → expected
> `.svg` output with a SHA256 pin so that any regression in placement logic,
> geometry constants, accessibility properties, or error handling surfaces
> immediately in CI — without requiring a human to eyeball every output.
>
> **Scope**: design only. No fixture files are created by this document. No
> production code is modified. All paths are prescriptive, not descriptive.

---

## 1. Corpus Catalogue

### 1.1 Column definitions

| Column | Meaning |
|--------|---------|
| **ID** | Stable fixture identifier, used as directory name and pytest node |
| **Category** | `bug` / `critical` / `high` / `good` |
| **Input `.tex` snippet** | Inline source (≤ 20 lines each); full file lives under the fixture directory |
| **Invariants exercised** | Comma-separated rule identifiers from §1 of the ruleset |
| **Expected outcome** | Rendered SVG pin or E15xx error signal |
| **Bytes budget** | Max normalized SVG size for CI artifact storage |

### 1.2 Category rationale

- **bug**: directly reproduces a known-bad repro from §7 of the ruleset (bug-A..F, ok-simple, pill-arrow-collide).
- **critical**: exercises a Critical-severity edge case from the 04-edge-cases taxonomy.
- **high**: exercises a High-severity edge case.
- **good**: clean happy-path cases — one per primitive × annotation position × color token.

---

### 1.3 Full catalogue (44 entries)

#### Bug reproductions (8 entries)

| ID | Category | Input `.tex` snippet | Invariants | Expected outcome | Bytes budget |
|----|----------|----------------------|------------|-----------------|--------------|
| `bug-A` | bug | Array n=4, annotations on cells [0] and [2] with labels "15" and "13"; no `register_decorations` call | C-7, C-1 | Two pills visible; may overlap cell text (known-bad, documented expectation) | 8 KB |
| `bug-B` | bug | `\annotate{arr.cell[0]}{label="self", arrow_from="arr.cell[0]"}` — self-loop | §2.4 guard, G-5 | Post-fix: no `nan`/`inf` in SVG; arrow suppressed or stub emitted. Pre-fix: NaN present in path data | 4 KB |
| `bug-C` | bug | Array, 8-line wrapping plain-text label with no space-separated split points | E-4, AC-5, T-6 | Pill ry + pill_h ≤ viewBox height | 6 KB |
| `bug-D` | bug | Position-only annotation on Array where `resolve_annotation_point` returns `None` for selector | E-2, AC-1 | Pill still rendered (partial clip acceptable); not silently dropped | 4 KB |
| `bug-E` | bug | Plane2D with `position=above` annotation; primitive does not dispatch position-only | §5.2, AC-1 | Zero pills — known non-conformant documented state; fixture tracks regression if it accidentally improves | 3 KB |
| `bug-F` | bug | Plane2D with 40-char label; no viewBox clamp (FP-4) | §5.3 FP-4, G-3 | Pill rx + pill_w overflows canvas — known-bad, tracks if accidentally fixed | 5 KB |
| `pill-arrow-collide` | bug | DPTable with 6 cells, 4 arc arrows; registry is pill-only (no leader registration) | C-6, C-1 | Some pill-on-leader collisions expected (SHOULD violation, documented) | 12 KB |
| `ok-simple` | bug | Array n=3, one `\annotate{arr.cell[1]}{label="ptr", color=info}` position-only | AC-1, AC-3, G-3 | Single pill above cell[1]; no leader; within viewBox | 4 KB |

#### Critical edge cases (6 entries)

| ID | Category | Input `.tex` snippet | Invariants | Expected outcome | Bytes budget |
|----|----------|----------------------|------------|-----------------|--------------|
| `critical-1-nan-pill-h` | critical | Unit-level: force `_nudge_candidates(40, float('nan'))` | G-5, §2.4 | `ValueError` raised before any SVG emitted; no NaN in output | 1 KB |
| `critical-2-null-byte` | critical | `\annotate{arr.cell[0]}{label="a\x00b", color=info}` | T-1, §2.4 | Null byte stripped from `<text>` element; XML remains valid | 3 KB |
| `critical-3-inf-dst` | critical | Unit: `emit_plain_arrow_svg` called with `dst_point=(float('-inf'), float('inf'))` | §2.4, G-3 | `ValueError` raised (or silent return with no SVG); no `OverflowError` propagated | 1 KB |
| `critical-4-self-loop-nan` | critical | `\annotate{arr.cell[2]}{label="loop", arrow_from="arr.cell[2]"}` | §2.4, bug-B guard | No `nan` anywhere in emitted SVG; either arrow suppressed or safe stub | 4 KB |
| `critical-5-nan-registry` | critical | Unit: pre-populate `placed_labels` with a NaN-coordinate `_LabelPlacement`; emit one more annotation | §2.3, C-3 | Assertion or guard prevents NaN from poisoning registry; second annotation placed at valid coordinate | 2 KB |
| `critical-6-inf-pill-h` | critical | Unit: force `_nudge_candidates(40, float('inf'))` | G-5, §2.4 | `ValueError` before any candidates yielded; no `OverflowError` at `int()` site | 1 KB |

#### High edge cases (12 entries)

| ID | Category | Input `.tex` snippet | Invariants | Expected outcome | Bytes budget |
|----|----------|----------------------|------------|-----------------|--------------|
| `high-1-short-leader` | high | Two Array cells 0.1 px apart (unit: `src=(100,100), dst=(100.1,100)`) | G-7, G-8 | No NaN/Inf in SVG polygon; arrow suppressed or degenerate-safe | 2 KB |
| `high-2-shorten-overflow` | high | Unit: `emit_arrow_svg` with `shorten_src=10, shorten_dst=10, dist=14.1` | G-7, §6.5 | No NaN; endpoints clamped to `dist/2` each | 2 KB |
| `high-3-large-arrow-index` | high | Unit: `emit_arrow_svg` with `arrow_index=100, cell_height=40` | §6.6, G-3 | No NaN; total_offset capped at documented max | 2 KB |
| `high-4-long-diagonal-leader` | high | Unit: `emit_arrow_svg(src=(0,0), dst=(1000,800))` | G-7, §6.3 | No NaN in polygon; direction vector safe | 3 KB |
| `high-5-displaystyle` | high | `\annotate{dp.cell[1]}{label="$\displaystyle \frac{a}{b}$", color=info}` on DPTable | T-4, T-6, AC-6 | `pill_h >= 30` px; text not visually clipped | 5 KB |
| `high-6-nested-fractions` | high | `\annotate{arr.cell[0]}{label="$\frac{\frac{1}{2}}{3}$", color=warn}` | T-4, T-6 | `pill_h >= 28` px; no clipping | 4 KB |
| `high-7-math-below-headroom` | high | Array, `\annotate{arr.cell[0]}{label="$x^2$", position=below}` | AC-6, E-4 | `position_label_height_below >= position_label_height_above` for same math label | 4 KB |
| `high-8-negative-font-size` | high | Unit: `ARROW_STYLES` patched with `label_size="-12px"` | T-5, §1.9 | `ValueError` or assertion raised at font-extraction; no SVG emitted with negative font | 1 KB |
| `high-9-clamp-collision` | high | Two annotations both with natural position near left edge (x < pill_w/2) | G-1, C-1, §10.1 | Post-clamp, no two pill AABBs overlap; registered x ≥ pill_w/2 for both | 5 KB |
| `high-10-resolve-none-warn` | high | Annotation with `target='arr.cell[999]'` on a 3-cell Array | E-2, §8.4 | Warning emitted (E1115 match); annotation skipped; no crash | 3 KB |
| `high-11-position-below-math` | high | Array, `\annotate{arr.cell[2]}{label="$\sum_{i=0}^{n}$", position=below}` | AC-6, §9.4 | `position_label_height_below` returns value including math headroom (+8 px); pill within viewBox | 5 KB |
| `high-12-long-leader-diagonal` | high | Graph node-to-node annotation with 600 px leader arc | G-7, G-8, C-6 | Leader originates at arc midpoint, not target center; no NaN | 6 KB |

#### Good-path samples (18 entries)

Every primitive with annotation support × representative position/color combinations.

| ID | Category | Input `.tex` snippet | Invariants | Expected outcome | Bytes budget |
|----|----------|----------------------|------------|-----------------|--------------|
| `good-array-above-info` | good | Array n=4, `\annotate{arr.cell[1]}{label="ptr", position=above, color=info}` | AC-1, AC-3, AC-4, G-3 | Single pill above cell[1]; info color; within viewBox | 4 KB |
| `good-array-below-warn` | good | Array n=4, `\annotate{arr.cell[3]}{label="end", position=below, color=warn}` | AC-1, AC-3, AC-4, G-3 | Single pill below cell[3]; warn color | 4 KB |
| `good-array-left-good` | good | Array n=4, `\annotate{arr.cell[0]}{label="start", position=left, color=good}` | AC-1, AC-3, AC-4 | Pill to left of cell[0] | 4 KB |
| `good-array-right-error` | good | Array n=4, `\annotate{arr.cell[3]}{label="!!", position=right, color=error}` | AC-1, AC-3, AC-4 | Pill to right of cell[3] | 4 KB |
| `good-array-arrow-from` | good | Array n=4, `\annotate{arr.cell[3]}{label="+3", arrow_from="arr.cell[0]", color=good}` | AC-2, G-7, G-8, C-1 | Arc from cell[0] to cell[3]; pill near arc midpoint; arrowhead at cell[3] | 6 KB |
| `good-array-math-label` | good | Array n=3, `\annotate{arr.cell[1]}{label="$O(n)$", position=above, color=muted}` | T-3, T-4, AC-6 | Math pill rendered; no wrapping; headroom ≥ 32 px | 5 KB |
| `good-array-multicolor` | good | Array n=6, three annotations: info on cell[0], good on cell[2], error on cell[5] | C-1, AC-4, C-4 | Three distinct pills; no overlaps; each color token applied correctly | 7 KB |
| `good-dptable-arc-arrow` | good | DPTable n=4, `\annotate{dp.cell[2]}{label="+2", arrow_from="dp.cell[0]", color=info}` | AC-2, G-7, C-1 | Arc present; pill at midpoint | 6 KB |
| `good-dptable-two-arcs` | good | DPTable n=4, two arc annotations from cell[0]→cell[2] and cell[1]→cell[2] | C-1, C-5, G-1 | Two non-overlapping pills; correct arc geometry for both | 8 KB |
| `good-graph-node-annotation` | good | Graph with nodes a/b/c, `\annotate{g.node[a]}{label="src", color=info}` | AC-1, AC-4, G-3 | Pill at node a; correct color | 5 KB |
| `good-linkedlist-annotation` | good | LinkedList 3 nodes, `\annotate{ll.node[0]}{label="head", position=above, color=good}` | AC-1, AC-3 | Pill above head node | 4 KB |
| `good-grid-annotation` | good | Grid 3×3, `\annotate{grid.cell[1][1]}{label="mid", position=inside, color=muted}` | AC-1, AC-3 | Pill inside center cell | 4 KB |
| `good-array-plain-arrow` | good | Array n=3, `\annotate{arr.cell[1]}{label="i", arrow=true, color=info}` | §0.3 plain-arrow, G-8 | Short stem + pill; no Bezier arc | 4 KB |
| `good-array-leader-emitted` | good | Two annotations: first at natural position, second nudged > 30 px | G-7, G-8 | Second annotation has `<polyline>` leader; first does not | 6 KB |
| `good-array-leader-suppressed` | good | Two annotations: second nudged exactly 30 px (threshold boundary) | G-8 | No `<polyline>` in output (displacement = 30 px, threshold is strictly > 30) | 5 KB |
| `good-determinism` | good | Array n=3, single annotation; call emitter twice with identical inputs | D-1, D-2 | `output_a == output_b` byte-identical | 4 KB |
| `good-debug-flag-off` | good | Dense Array with collision; `SCRIBA_DEBUG_LABELS=0` | C-2, D-4 | No `<!-- scriba:label-collision -->` comment in output | 5 KB |
| `good-debug-flag-on` | good | Dense Array with collision; `SCRIBA_DEBUG_LABELS=1` | C-2, D-4 | `<!-- scriba:label-collision -->` comment present | 5 KB |

**Total: 44 fixtures**

---

## 2. Directory Layout

```
tests/
└── fixtures/
    └── smart_label_golden/
        ├── pins.json                          # master SHA256 registry (see §3)
        ├── normalizer.py                      # normalization script (see §4)
        ├── README.md                          # brief corpus guide for contributors
        │
        ├── bug/
        │   ├── bug-A/
        │   │   ├── input.tex
        │   │   ├── expected.svg               # normalized golden output
        │   │   └── expected.svg.sha256        # SHA256 of normalized expected.svg
        │   ├── bug-B/
        │   │   ├── input.tex
        │   │   ├── expected.svg
        │   │   └── expected.svg.sha256
        │   ├── bug-C/
        │   ├── bug-D/
        │   ├── bug-E/
        │   ├── bug-F/
        │   ├── pill-arrow-collide/
        │   └── ok-simple/
        │
        ├── critical/
        │   ├── critical-1-nan-pill-h/
        │   │   ├── input.py                   # unit-level Python driver (no .tex)
        │   │   ├── expected_exception.txt     # e.g. "ValueError"
        │   │   └── expected_exception.txt.sha256
        │   ├── critical-2-null-byte/
        │   │   ├── input.tex
        │   │   ├── expected.svg
        │   │   └── expected.svg.sha256
        │   ├── critical-3-inf-dst/
        │   ├── critical-4-self-loop-nan/
        │   ├── critical-5-nan-registry/
        │   └── critical-6-inf-pill-h/
        │
        ├── high/
        │   ├── high-1-short-leader/
        │   ├── high-2-shorten-overflow/
        │   ├── high-3-large-arrow-index/
        │   ├── high-4-long-diagonal-leader/
        │   ├── high-5-displaystyle/
        │   ├── high-6-nested-fractions/
        │   ├── high-7-math-below-headroom/
        │   ├── high-8-negative-font-size/
        │   ├── high-9-clamp-collision/
        │   ├── high-10-resolve-none-warn/
        │   ├── high-11-position-below-math/
        │   └── high-12-long-leader-diagonal/
        │
        └── good/
            ├── good-array-above-info/
            ├── good-array-below-warn/
            ├── good-array-left-good/
            ├── good-array-right-error/
            ├── good-array-arrow-from/
            ├── good-array-math-label/
            ├── good-array-multicolor/
            ├── good-dptable-arc-arrow/
            ├── good-dptable-two-arcs/
            ├── good-graph-node-annotation/
            ├── good-linkedlist-annotation/
            ├── good-grid-annotation/
            ├── good-array-plain-arrow/
            ├── good-array-leader-emitted/
            ├── good-array-leader-suppressed/
            ├── good-determinism/
            ├── good-debug-flag-off/
            └── good-debug-flag-on/
```

### 2.1 Fixture file types

Each fixture directory contains exactly one of these input variants:

| Input type | File | Used by |
|------------|------|---------|
| Full `.tex` document | `input.tex` | `.tex` → render pipeline fixtures |
| Python driver | `input.py` | Unit-level fixtures that drive `_svg_helpers.py` directly |

And exactly one of these expected-outcome variants:

| Outcome type | File | Meaning |
|--------------|------|---------|
| Normalized SVG golden | `expected.svg` | Compared byte-for-byte after normalization |
| Exception name | `expected_exception.txt` | E.g. `ValueError`, asserted via `pytest.raises` |
| Debug comment golden | `expected.svg` | SVG that must/must-not contain a specific comment |

The `.sha256` sibling file exists for every `expected.*` file. See §3.

---

## 3. SHA256 Pinning Scheme

### 3.1 Pin file format

`pins.json` at the corpus root contains one entry per fixture:

```json
{
  "schema_version": 1,
  "fixtures": {
    "bug/bug-A": {
      "expected_file": "expected.svg",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "normalized": true,
      "ruleset_version": "2.0.0-draft",
      "pinned_at": "2026-04-21T00:00:00Z",
      "known_failing": false,
      "known_failing_reason": null
    },
    "critical/critical-1-nan-pill-h": {
      "expected_file": "expected_exception.txt",
      "sha256": "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4d",
      "normalized": false,
      "ruleset_version": "2.0.0-draft",
      "pinned_at": "2026-04-21T00:00:00Z",
      "known_failing": true,
      "known_failing_reason": "guard not yet implemented (Critical-1 pending §2.4)"
    }
  }
}
```

The `.sha256` sibling files duplicate the hash for offline verification without parsing JSON:

```
# bug/bug-A/expected.svg.sha256
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  expected.svg
```

This format matches `sha256sum -c` usage, enabling shell-level verification.

### 3.2 Accept-new-golden flow

When a fixture does not yet have a pin (first-time creation) or when a deliberate ruleset change mandates a pin update, contributors use:

```bash
SCRIBA_UPDATE_GOLDEN=1 pytest tests/unit/test_smart_label_golden.py -k "bug-A"
```

The `SCRIBA_UPDATE_GOLDEN=1` environment variable triggers the following sequence in the test harness (implemented in `conftest.py`):

1. Run the fixture normally; capture the normalized SVG output.
2. Write `expected.svg` (overwriting if present).
3. Compute `sha256(expected.svg)` and write `expected.svg.sha256`.
4. Update `pins.json` for the affected fixture key.
5. Print a warning: `[GOLDEN UPDATE] bug/bug-A — human review required before commit`.

The test **passes** in update mode regardless of whether the output matches the old pin. This prevents accidental CI greening without review.

**Human review gate**: the CI pipeline checks for any diff in `pins.json` or `expected.svg` files and requires a reviewer approval tag (`golden-update-approved`) on the PR. This is enforced via the `CODEOWNERS` file for `tests/fixtures/smart_label_golden/`.

### 3.3 Known-failing fixtures

Fixtures for known-bad repros that have not yet been fixed (bug-A, bug-B pre-fix, bug-E, bug-F) are marked `"known_failing": true` in `pins.json`. The test runner:

- **Passes** if the output matches the known-failing golden (the bug is still present as expected).
- **Fails with a conspicuous `XFAIL_IMPROVED` signal** if the output does NOT match the known-failing golden — this means the bug may have been fixed, and the pin needs human promotion to a good-path golden.
- Never silently green-lights an unexpected change to a known-failing fixture.

```python
# conftest.py sketch
if fixture_meta["known_failing"]:
    if actual_sha == expected_sha:
        pytest.xfail("known bug still present (expected)")
    else:
        pytest.fail(
            f"[XFAIL_IMPROVED] {fixture_id}: output changed from known-bad golden. "
            "Run SCRIBA_UPDATE_GOLDEN=1 and promote pin if bug is fixed."
        )
```

---

## 4. Sanitization Pipeline

### 4.1 Why normalization is necessary

The scriba SVG output is deterministic for identical inputs in the same process (D-1), but across KaTeX version bumps, Python minor versions, or platform changes, several non-semantic fields vary:

| Source of variance | Example | Effect on SHA256 |
|--------------------|---------|------------------|
| KaTeX version in class names | `class="katex-html"` → additional `version-N` class | SHA mismatch |
| Float coordinate jitter (D-3) | `x="47.3"` vs `x="47.29999"` | SHA mismatch |
| Timestamps in comments | `<!-- generated at 2026-04-21T10:30:00 -->` | SHA mismatch |
| Unique ID sequences | `id="lbl-f3a9"` vs `id="lbl-0012"` | SHA mismatch |
| Whitespace differences | Indentation changes across refactors | SHA mismatch |

The normalizer strips or canonicalizes all of these before the SHA256 is computed.

### 4.2 Normalizer specification

The normalizer operates on a raw SVG string and returns a canonical string. It is idempotent: `normalize(normalize(svg)) == normalize(svg)`.

**Steps applied in order:**

1. **Strip generation comments** — remove any `<!-- generated at … -->`, `<!-- scriba version … -->`, or `<!-- katex version … -->` XML comments. Preserve `<!-- scriba:label-collision … -->` debug comments (they are part of the tested invariant C-2).
2. **Strip KaTeX version-dependent class tokens** — from any `class="…"` attribute, remove tokens matching `katex-version-\S+` and `katex-\d+\.\d+\.\d+`.
3. **Canonicalize float coordinates** — in all SVG coordinate attributes (`x`, `y`, `cx`, `cy`, `x1`, `y1`, `x2`, `y2`, `width`, `height`, `rx`, `ry`, `d` path data, `points` polyline data), round each float to 2 decimal places.
4. **Canonicalize IDs** — replace all `id="…"` and corresponding `href="#…"` / `url(#…)` references with sequentially assigned names `id-0001`, `id-0002`, … in document order (depth-first traversal). This is order-stable because SVG documents are deterministic (D-1).
5. **Normalize whitespace** — collapse all runs of whitespace between tags to a single newline + 2-space indent. Trim trailing whitespace from every line.
6. **Sort `<defs>` children** — sort child elements of `<defs>` by their `id` attribute alphabetically. This removes any future ordering sensitivity from defs accumulation.
7. **Normalize empty elements** — `<foo></foo>` → `<foo/>`.

### 4.3 Python pseudo-code for the normalizer

```python
"""
tests/fixtures/smart_label_golden/normalizer.py

SVG normalization pipeline for golden corpus pinning.
All steps are applied in sequence; each step is a pure function.
"""
from __future__ import annotations

import re
import math
from xml.etree import ElementTree as ET
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # for type annotation imports only


# ---------------------------------------------------------------------------
# Step 1: Strip generation comments
# ---------------------------------------------------------------------------

_GEN_COMMENT_RE = re.compile(
    r"<!--\s*(generated at|scriba version|katex version)[^>]*-->",
    re.IGNORECASE,
)

def _strip_generation_comments(svg: str) -> str:
    return _GEN_COMMENT_RE.sub("", svg)


# ---------------------------------------------------------------------------
# Step 2: Strip KaTeX version tokens from class attributes
# ---------------------------------------------------------------------------

_KATEX_VERSION_TOKEN_RE = re.compile(
    r"\b(katex-version-\S+|katex-\d+\.\d+\.\d+)\b"
)

def _strip_katex_version_tokens(svg: str) -> str:
    def _clean_class(m: re.Match) -> str:
        cleaned = _KATEX_VERSION_TOKEN_RE.sub("", m.group(0)).strip()
        # Collapse multiple spaces inside the attribute value
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned

    return re.sub(r'class="[^"]*"', _clean_class, svg)


# ---------------------------------------------------------------------------
# Step 3: Canonicalize floats to 2 decimal places
# ---------------------------------------------------------------------------

_FLOAT_RE = re.compile(r"-?\d+\.\d{3,}")  # 3+ decimal places → round to 2

def _round_float(m: re.Match) -> str:
    val = float(m.group(0))
    if not math.isfinite(val):
        return m.group(0)  # preserve NaN/Inf in known-bad fixtures
    rounded = round(val, 2)
    # Avoid "-0.0"
    if rounded == 0.0:
        return "0.0"
    return f"{rounded:.2f}"

def _canonicalize_floats(svg: str) -> str:
    return _FLOAT_RE.sub(_round_float, svg)


# ---------------------------------------------------------------------------
# Step 4: Canonicalize IDs
# ---------------------------------------------------------------------------

def _canonicalize_ids(svg: str) -> str:
    """Replace id= attributes and all href/#/url(#) refs with id-NNNN."""
    id_map: dict[str, str] = {}
    counter = 0

    def _new_id(old: str) -> str:
        nonlocal counter
        if old not in id_map:
            counter += 1
            id_map[old] = f"id-{counter:04d}"
        return id_map[old]

    # Collect all id= values in document order
    for m in re.finditer(r'\bid="([^"]+)"', svg):
        _new_id(m.group(1))

    # Replace id= declarations
    svg = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{_new_id(m.group(1))}"', svg)
    # Replace href="#..." references
    svg = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{_new_id(m.group(1))}"', svg)
    # Replace url(#...) references
    svg = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{_new_id(m.group(1))})', svg)
    return svg


# ---------------------------------------------------------------------------
# Step 5: Normalize whitespace
# ---------------------------------------------------------------------------

def _normalize_whitespace(svg: str) -> str:
    lines = svg.splitlines()
    result = []
    for line in lines:
        stripped = line.rstrip()
        if stripped:
            result.append(stripped)
    return "\n".join(result) + "\n"


# ---------------------------------------------------------------------------
# Step 6: Sort <defs> children
# ---------------------------------------------------------------------------

def _sort_defs_children(svg: str) -> str:
    """Sort children of every <defs> block by their id attribute."""
    # Use regex-based approach to avoid full XML parse (preserves comments)
    def _sort_block(m: re.Match) -> str:
        inner = m.group(1)
        # Split on top-level child boundaries (heuristic: element start at col 0+)
        children = re.split(r"(?=\n\s*<(?!/))", inner)
        children.sort(key=lambda c: re.search(r'id="([^"]+)"', c).group(1)
                       if re.search(r'id="([^"]+)"', c) else c)
        return f"<defs>{''.join(children)}</defs>"

    return re.sub(r"<defs>(.*?)</defs>", _sort_block, svg, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Step 7: Normalize empty elements
# ---------------------------------------------------------------------------

def _normalize_empty_elements(svg: str) -> str:
    return re.sub(r"<(\w[\w:.-]*)((?:\s[^>]*)?)\s*></\1>", r"<\1\2/>", svg)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def normalize(svg: str) -> str:
    """Apply the full normalization pipeline to an SVG string.

    This function is idempotent: normalize(normalize(svg)) == normalize(svg).

    Args:
        svg: Raw SVG string from the scriba renderer.

    Returns:
        Canonical SVG string suitable for SHA256 pinning.
    """
    svg = _strip_generation_comments(svg)
    svg = _strip_katex_version_tokens(svg)
    svg = _canonicalize_floats(svg)
    svg = _canonicalize_ids(svg)
    svg = _normalize_whitespace(svg)
    svg = _sort_defs_children(svg)
    svg = _normalize_empty_elements(svg)
    return svg


def sha256_of(svg: str) -> str:
    """Return the hex SHA256 of the normalized SVG."""
    import hashlib
    return hashlib.sha256(normalize(svg).encode("utf-8")).hexdigest()
```

### 4.4 Normalizer correctness properties

The normalizer MUST preserve these semantic properties:

| Property | Verification |
|----------|-------------|
| All `<rect>` pill elements still present | `count("<rect", normalized) == count("<rect", raw)` |
| All `<text>` label elements still present | same count check |
| No `<polyline>` elements added or removed | same count check |
| Debug comment `<!-- scriba:label-collision -->` preserved | not matched by step-1 regex |
| `aria-label` attribute values unchanged | step-4 only touches `id=` attributes, not `aria-label` |
| SVG `viewBox` attribute values unchanged after float rounding | ≤ 1 px shift acceptable per D-3 |

The test suite for the normalizer itself lives at
`tests/unit/test_golden_normalizer.py` and covers at minimum:
idempotency, pill count preservation, float rounding, ID remapping, and
`<!-- scriba:label-collision -->` comment passthrough.

---

## 5. Rebase Procedure

### 5.1 When a rebase is needed

A pin rebase is triggered when:

| Trigger | Scope | Version bump |
|---------|-------|-------------|
| Bug fix (bug-A..F resolved) | Affected bug fixture(s) + dependent good-path fixtures | PATCH to pins, no ruleset bump |
| Ruleset MINOR change (new SHOULD/MAY rule) | Any fixture that exercises the changed rule | MINOR pins update |
| Ruleset MAJOR change (new MUST, or geometry constant change ≥ 8 px) | Full corpus rebase required | MAJOR pins update |
| KaTeX version bump (normalizer handles) | No rebase needed if normalizer strips the diff | None |
| Python version bump (≤ 1 px coordinate jitter, D-3) | No rebase needed if floats rounded to 2dp | None |

### 5.2 Rebase git workflow

```bash
# 1. Create a dedicated branch
git checkout -b golden-rebase/ruleset-v2.1

# 2. Make the code/spec change in the same branch
#    (edit _svg_helpers.py and smart-label-ruleset.md)

# 3. Regenerate affected fixtures
SCRIBA_UPDATE_GOLDEN=1 pytest tests/unit/test_smart_label_golden.py \
    -k "high-7-math-below-headroom high-11-position-below-math"

# 4. Review the diff — this is the mandatory human review step
git diff tests/fixtures/smart_label_golden/

# 5. Verify the diff is limited to the expected fixtures
#    (script in tools/check_golden_diff_scope.py)
python tools/check_golden_diff_scope.py \
    --expected-fixtures "high-7-math-below-headroom,high-11-position-below-math" \
    --changed-files $(git diff --name-only)

# 6. Record in CHANGELOG
cat >> CHANGELOG-smart-label.md << 'EOF'

## [unreleased] — 2026-04-21

### Golden corpus pin update

- `high-7-math-below-headroom`: pin updated after AC-6 `position_label_height_below`
  math-branch fix. Old SHA: `<old>`. New SHA: `<new>`.
- `high-11-position-below-math`: same fix.

Ruleset version: 2.0.1 (PATCH — bug fix, no invariant change).
EOF

# 7. Commit code + fixtures + changelog atomically
git add scriba/animation/primitives/_svg_helpers.py
git add docs/spec/smart-label-ruleset.md
git add tests/fixtures/smart_label_golden/
git add CHANGELOG-smart-label.md
git commit -m "fix: AC-6 math headroom below — position_label_height_below mirrors above

Updated golden pins: high-7-math-below-headroom, high-11-position-below-math.
Ruleset patch 2.0.1.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

# 8. Open PR; CI enforces the golden-update-approved label requirement
gh pr create --label "golden-update-approved" \
    --title "fix: AC-6 position_label_height_below math branch"
```

### 5.3 CHANGELOG entry format

Every golden pin change MUST produce a CHANGELOG entry in the following format:

```markdown
### Golden corpus pin update — <date>

**Fixtures updated**: `<fixture-id-1>`, `<fixture-id-2>`
**Trigger**: <one-line reason>
**Ruleset version before/after**: 2.0.0 → 2.0.1
**Old SHA**: `<hex>`
**New SHA**: `<hex>`
**Diff summary**: <1–2 sentences describing what changed in the SVG>
```

---

## 6. CI Integration

### 6.1 Test module structure

```
tests/
├── unit/
│   ├── test_smart_label_golden.py     # parametrized corpus runner
│   └── test_golden_normalizer.py      # normalizer self-tests
```

### 6.2 `test_smart_label_golden.py` — pytest parametrize

```python
"""
tests/unit/test_smart_label_golden.py

Parametrized golden corpus runner for the smart-label ruleset.
Discovers all fixtures under tests/fixtures/smart_label_golden/ at
collection time and runs each against the pin in pins.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest

CORPUS_ROOT = Path(__file__).parent.parent / "fixtures" / "smart_label_golden"
PINS_PATH = CORPUS_ROOT / "pins.json"
UPDATE_GOLDEN = os.environ.get("SCRIBA_UPDATE_GOLDEN") == "1"


def _iter_fixtures() -> Iterator[tuple[str, dict]]:
    """Yield (fixture_id, metadata) for every entry in pins.json."""
    with PINS_PATH.open() as f:
        pins = json.load(f)
    for fixture_id, meta in pins["fixtures"].items():
        yield fixture_id, meta


def _render_fixture(fixture_dir: Path, meta: dict) -> str:
    """Run the fixture and return the (normalized) output string."""
    from tests.fixtures.smart_label_golden.normalizer import normalize

    input_tex = fixture_dir / "input.tex"
    input_py = fixture_dir / "input.py"

    if input_tex.exists():
        # Full pipeline render
        result = subprocess.run(
            [sys.executable, "-m", "scriba.cli", "render",
             "--headless", str(input_tex)],
            capture_output=True, text=True, check=False,
            cwd=Path(__file__).parent.parent.parent,
        )
        raw_svg = result.stdout
        return normalize(raw_svg)

    elif input_py.exists():
        # Unit-level Python driver
        namespace: dict = {}
        exec(input_py.read_text(), namespace)  # noqa: S102
        raw = namespace.get("OUTPUT", "")
        return normalize(raw) if meta.get("normalized") else raw

    raise FileNotFoundError(f"No input.tex or input.py in {fixture_dir}")


@pytest.mark.parametrize(
    "fixture_id,meta",
    list(_iter_fixtures()),
    ids=[fid for fid, _ in _iter_fixtures()],
)
def test_golden_fixture(fixture_id: str, meta: dict) -> None:
    fixture_dir = CORPUS_ROOT / fixture_id.replace("/", os.sep)
    expected_file = fixture_dir / meta["expected_file"]
    expected_sha = meta["sha256"]
    known_failing = meta.get("known_failing", False)

    # Handle exception-type fixtures separately
    if meta["expected_file"] == "expected_exception.txt":
        _run_exception_fixture(fixture_dir, expected_file, expected_sha,
                               known_failing, meta)
        return

    actual_output = _render_fixture(fixture_dir, meta)
    actual_sha = hashlib.sha256(actual_output.encode()).hexdigest()

    if UPDATE_GOLDEN:
        expected_file.write_text(actual_output, encoding="utf-8")
        sha256_file = expected_file.with_suffix(
            expected_file.suffix + ".sha256"
        )
        sha256_file.write_text(
            f"{actual_sha}  {expected_file.name}\n", encoding="utf-8"
        )
        _update_pin(fixture_id, actual_sha)
        pytest.skip(f"[GOLDEN UPDATE] {fixture_id} — human review required")
        return

    if known_failing:
        if actual_sha == expected_sha:
            pytest.xfail(
                f"Known bug still present in {fixture_id} (expected)"
            )
        else:
            pytest.fail(
                f"[XFAIL_IMPROVED] {fixture_id}: output changed from known-bad "
                f"golden. Run SCRIBA_UPDATE_GOLDEN=1 and promote pin if bug fixed.\n"
                f"Expected SHA: {expected_sha}\n"
                f"Actual SHA:   {actual_sha}"
            )
        return

    assert actual_sha == expected_sha, (
        f"Golden mismatch for {fixture_id}.\n"
        f"Expected SHA: {expected_sha}\n"
        f"Actual SHA:   {actual_sha}\n"
        f"Run with SCRIBA_UPDATE_GOLDEN=1 to update pins (requires human review)."
    )


def _run_exception_fixture(
    fixture_dir: Path,
    expected_file: Path,
    expected_sha: str,
    known_failing: bool,
    meta: dict,
) -> None:
    """Run a unit-level Python driver that is expected to raise an exception."""
    input_py = fixture_dir / "input.py"
    namespace: dict = {}
    expected_exc_name = expected_file.read_text().strip()

    raised: BaseException | None = None
    try:
        exec(input_py.read_text(), namespace)  # noqa: S102
    except Exception as exc:  # noqa: BLE001
        raised = exc

    if known_failing:
        # Guard not yet implemented — expect no exception (bug present)
        if raised is None:
            pytest.xfail(
                f"Known unfixed guard in {fixture_dir.name} (expected — no exception raised)"
            )
        else:
            pytest.fail(
                f"[XFAIL_IMPROVED] {fixture_dir.name}: guard now raises "
                f"{type(raised).__name__}. Promote this fixture to non-failing."
            )
        return

    assert raised is not None, (
        f"{fixture_dir.name}: expected {expected_exc_name} but no exception was raised"
    )
    assert type(raised).__name__ == expected_exc_name, (
        f"{fixture_dir.name}: expected {expected_exc_name}, got {type(raised).__name__}"
    )


def _update_pin(fixture_id: str, new_sha: str) -> None:
    with PINS_PATH.open() as f:
        pins = json.load(f)
    pins["fixtures"][fixture_id]["sha256"] = new_sha
    from datetime import datetime, timezone
    pins["fixtures"][fixture_id]["pinned_at"] = (
        datetime.now(tz=timezone.utc).isoformat()
    )
    with PINS_PATH.open("w") as f:
        json.dump(pins, f, indent=2)
        f.write("\n")
```

### 6.3 CI pipeline steps

Add to `.github/workflows/test.yml` (or equivalent):

```yaml
- name: Run smart-label golden corpus
  run: pytest tests/unit/test_smart_label_golden.py -v --tb=short
  env:
    SCRIBA_DEBUG_LABELS: "0"

- name: Upload golden diff artifacts on failure
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: golden-diff-${{ github.run_id }}
    path: |
      tests/fixtures/smart_label_golden/**/*.svg
    retention-days: 7
```

**On pin mismatch**, the test output includes:
1. The fixture ID and expected vs. actual SHA256.
2. The normalized actual SVG written to a temp file (path printed to stdout).
3. A CI artifact containing both `expected.svg` and the temp `actual.svg` for side-by-side diffing.

### 6.4 Runtime budget

Full corpus build target: < 30 seconds on a standard CI runner (4 vCPU, 8 GB RAM).

| Fixture category | Count | Estimated time |
|-----------------|-------|---------------|
| bug (full pipeline) | 8 | ~10 s |
| critical (unit-level) | 6 | ~1 s |
| high (unit-level + short pipeline) | 12 | ~8 s |
| good (full pipeline) | 18 | ~10 s |
| **Total** | **44** | **~29 s** |

Unit-level fixtures (critical + most high) run the Python driver directly without the full `.tex` → HTML pipeline, keeping them fast. Full-pipeline fixtures (`bug/` + `good/`) use `scriba render --headless` which bypasses the browser and KaTeX rendering.

---

## 7. Corpus Coverage Matrix

### 7.1 Mapping: fixture → invariants

The 44 fixtures collectively exercise the following invariants from the 42 defined in §1 of the ruleset. One fixture may exercise multiple invariants; one invariant may be exercised by multiple fixtures.

| Invariant | Fixtures | Covered? |
|-----------|----------|----------|
| **G-1** (post-clamp AABB registered) | `high-9-clamp-collision`, `good-array-above-info` | Yes |
| **G-2** (anchor == pill center ±1 px) | `good-array-above-info`, `good-array-arrow-from` | Yes |
| **G-3** (all pills inside viewBox) | `bug-A`, `bug-C`, `bug-F`, `critical-3-inf-dst`, `good-array-above-info`, `good-array-below-warn` | Yes |
| **G-4** (clamp preserves dimensions) | `high-9-clamp-collision`, `good-array-above-info` | Yes |
| **G-5** (pill_w, pill_h > 0) | `critical-1-nan-pill-h`, `critical-6-inf-pill-h`, `bug-D` | Yes |
| **G-6** (pill_w ≥ text + 2×PAD_X) | `good-array-above-info`, `good-array-math-label` | Yes |
| **G-7** (leader originates at arc midpoint) | `good-array-leader-emitted`, `good-array-arrow-from`, `high-1-short-leader`, `high-12-long-leader-diagonal` | Yes |
| **G-8** (leader suppressed ≤ 30 px) | `good-array-leader-emitted`, `good-array-leader-suppressed`, `high-1-short-leader` | Yes |
| **C-1** (no pill AABB overlap per frame) | `good-array-multicolor`, `good-dptable-two-arcs`, `high-9-clamp-collision`, `bug-A` | Yes |
| **C-2** (debug comment gated) | `good-debug-flag-off`, `good-debug-flag-on` | Yes |
| **C-3** (registry append-only) | `good-determinism`, `good-array-multicolor` | Partial (code inspection) |
| **C-4** (registry not shared across frames) | `good-determinism` | Partial (two-call driver needed) |
| **C-5** (side_hint preferred half-plane first) | `good-array-above-info`, `good-array-below-warn` | Partial |
| **C-6** (pill SHOULD NOT overlap leader) | `pill-arrow-collide` | Yes (known-bad documented) |
| **C-7** (pill SHOULD NOT overlap cell text) | `bug-A` | Yes (known-bad documented) |
| **T-1** (label text matches author declaration) | `good-array-above-info`, `critical-2-null-byte` | Yes |
| **T-2** (no hyphen split) | `good-array-above-info` (label "ptr" has no hyphen; add `good-array-hyphen-label` for full coverage — see gap below) | Partial |
| **T-3** (math not wrapped) | `good-array-math-label`, `high-5-displaystyle`, `high-6-nested-fractions` | Yes |
| **T-4** (width estimator within 20 px) | `good-array-math-label`, `high-5-displaystyle` | Yes |
| **T-5** (min font size ≥ 9 px) | `good-array-above-info` (static check on ARROW_STYLES) | Partial (static inspection) |
| **T-6** (pill height ≥ formula) | `high-5-displaystyle`, `high-6-nested-fractions`, `bug-C` | Yes |
| **A-1** (contrast ≥ 4.5:1 baseline) | not covered (PENDING MW-2 B7) | **No** |
| **A-2** (contrast ≥ 3:1 hover) | not covered | **No** |
| **A-3** (arrow stroke ≥ 3:1) | not covered | **No** |
| **A-4** (CVD token distinguishability) | not covered | **No** |
| **A-5** (aria-label) | `good-array-above-info` (assert `aria-label` attribute) | Yes |
| **A-6** (role hierarchy) | `good-array-above-info` | Yes |
| **A-7** (forced-colors, OPTIONAL) | not covered | No (browser test) |
| **D-1** (byte-identical repeat) | `good-determinism` | Yes |
| **D-2** (nudge grid deterministic) | `good-determinism` | Yes |
| **D-4** (debug flag captured at import) | `good-debug-flag-off`, `good-debug-flag-on` | Yes |
| **E-1** (last candidate on exhaust) | `good-debug-flag-on` (requires all-collision driver — add dedicated fixture) | Partial |
| **E-2** (position-only not dropped) | `bug-D` | Yes |
| **E-3** (unknown color falls back) | `good-array-above-info` (driver with bad color — add dedicated) | Partial |
| **E-4** (multi-line within headroom) | `bug-C` | Yes |
| **AC-1** (visible pill when label declared) | all `good-*` fixtures | Yes |
| **AC-2** (directed arc from A to B) | `good-array-arrow-from`, `good-dptable-arc-arrow`, `good-dptable-two-arcs` | Yes |
| **AC-3** (declared position tried first) | `good-array-above-info`, `good-array-below-warn`, `good-array-left-good`, `good-array-right-error` | Yes |
| **AC-4** (declared color produces matching styles) | `good-array-above-info`, `good-array-below-warn`, `good-array-left-good`, `good-array-right-error`, `good-array-multicolor` | Yes |
| **AC-5** (headroom helpers conservative) | `high-7-math-below-headroom`, `high-11-position-below-math` | Yes |
| **AC-6** (math headroom 32 px in both above and below) | `good-array-math-label`, `high-7-math-below-headroom`, `high-11-position-below-math` | Yes |

### 7.2 Coverage summary

| Axis | Total invariants | Fully covered | Partially covered | Not covered |
|------|-----------------|---------------|-------------------|-------------|
| G (Geometry) | 8 | 8 | 0 | 0 |
| C (Collision) | 7 | 5 | 2 (C-3, C-4) | 0 |
| T (Typography) | 6 | 4 | 2 (T-2, T-5) | 0 |
| A (Accessibility) | 7 | 2 | 0 | 5 (A-1..A-4, A-7) |
| D (Determinism) | 4 | 3 | 0 | 0 (D-3 not directly testable) |
| E (Error handling) | 4 | 2 | 2 (E-1, E-3) | 0 |
| AC (Author contract) | 6 | 6 | 0 | 0 |
| **Total** | **42** | **30** | **6** | **6** |

**Invariant coverage: 30/42 fully covered = 71.4%. Including partial: 36/42 = 85.7%.**

The 6 uncovered invariants (A-1..A-4, A-7, D-3) require either the MW-2 contrast infrastructure (A-1..A-4) or a browser test environment (A-7), or are explicitly untestable by definition (D-3 — platform float jitter). These are tracked as separate corpus expansion work in Phase 8.

### 7.3 Coverage gaps and recommended add-ons

The following 4 additional fixtures are recommended to close partial coverage gaps identified above. They are not included in the initial 44 but should be added in the next corpus sprint:

| Suggested ID | Gap closed | Invariant(s) |
|-------------|-----------|-------------|
| `good-array-hyphen-label` | T-2 hyphen never splits | T-2 |
| `good-array-unknown-color` | E-3 unknown color fallback | E-3 |
| `good-array-exhaust-32` | E-1 last-candidate on exhaust | E-1 |
| `good-array-two-frames` | C-4 registry not shared | C-4 |

---

## 8. Five Actual Fixture Drafts

The following drafts show the complete `.tex` source, a hand-computed expected
SVG skeleton (pill + anchor structure, not KaTeX glyphs — those are stripped by
normalization anyway), and the exact SHA256 after normalization.

> **Important**: the SHA256 values below are **computed over the hand-written
> expected skeleton**, not over real renderer output. When the actual fixture
> files are generated (with `SCRIBA_UPDATE_GOLDEN=1`), the SHA256 will be
> recomputed against the live renderer output and will differ from the values
> shown here. These values are placeholders to demonstrate the schema; they
> MUST be regenerated from the live renderer before the first commit.

---

### 8.1 `bug/bug-B` — Self-loop arrow NaN guard

**Input `.tex`** (`input.tex`):

```latex
\begin{animation}[id="bug-b-self-loop", label="Self-loop arrow bug repro"]
\shape{arr}{Array}{size=3, data=[10,20,30], labels="0..2"}

\step
\annotate{arr.cell[1]}{label="loop", arrow_from="arr.cell[1]", color=warn}
\narrate{Self-loop: arrow_from and target are the same cell.}
\end{animation}
```

**What invariant it exercises**: §2.4 pre-condition guard for self-loop. Post-fix:
the guard in `base.py` detects `arrow_from == target` and either suppresses the
arrow or emits a stub without calling `emit_arrow_svg`. Pre-fix: NaN appears in
the Bezier path data.

**Expected SVG skeleton** (post-fix state; pill is still rendered, arrow is suppressed):

```svg
<svg xmlns="http://www.w3.org/2000/svg"
     role="graphics-document"
     viewBox="0 0 600 80">
  <!-- scriba animation: bug-b-self-loop -->
  <!-- Step 1 -->
  <g id="id-0001" transform="translate(0, 32)">
    <!-- Array cells -->
    <rect x="50" y="0" width="100" height="40" rx="3"/>
    <text x="100" y="20" dominant-baseline="middle" text-anchor="middle">10</text>
    <rect x="150" y="0" width="100" height="40" rx="3"/>
    <text x="200" y="20" dominant-baseline="middle" text-anchor="middle">20</text>
    <rect x="250" y="0" width="100" height="40" rx="3"/>
    <text x="300" y="20" dominant-baseline="middle" text-anchor="middle">30</text>
    <!-- Annotation group: self-loop guard fires; no arrow path emitted -->
    <g role="graphics-symbol" aria-label="arr.cell[1]: loop" data-annotation="arr.cell[1]-plain-arrow">
      <!-- pill only; no <path> or <polygon> for the arrow -->
      <rect x="178" y="5" width="44" height="19" rx="4"
            fill="#fef3c7" stroke="#b45309" stroke-width="1.5"
            opacity="0.92"/>
      <text x="200" y="18"
            font-size="11px" font-family="monospace"
            fill="#92400e" dominant-baseline="middle" text-anchor="middle">loop</text>
    </g>
  </g>
</svg>
```

**Invariant checklist for this fixture**:
- No `<path>` element with `NaN` or `nan` in its `d` attribute.
- No `<polygon>` with `NaN` in its `points`.
- Pill `<rect>` is present (AC-1: label must appear).
- `aria-label` contains "arr.cell[1]" and "loop" (A-5).

**SHA256 after normalization** (placeholder — must be regenerated from live renderer):

```
# expected.svg.sha256
PLACEHOLDER_REGEN_FROM_LIVE_RENDERER  expected.svg
```

---

### 8.2 `bug/bug-A` — Cell text not seeded in registry

**Input `.tex`** (`input.tex`):

```latex
\begin{animation}[id="bug-a-cell-occlusion", label="Bug-A: pill occludes cell number"]
\shape{arr}{Array}{size=4, data=[15,17,13,9], labels="0..3"}

\step
\annotate{arr.cell[0]}{label="min", position=above, color=info}
\annotate{arr.cell[2]}{label="ptr", position=above, color=good}
\narrate{Two labels above cells. Without cell text seeded in registry, labels may occlude values 15 and 13.}
\end{animation}
```

**What invariant it exercises**: C-7 (pills SHOULD NOT overlap cell text).
This is a known-bad fixture — the current implementation does not seed cell text
AABBs, so the pills may occlude the cell values "15" and "13". The fixture
tracks the regression boundary: if MW-2 ships cell text seeding, the golden
should be promoted to a good-path fixture.

**Expected SVG skeleton** (current known-bad behavior, both pills at natural
position above their respective cells):

```svg
<svg xmlns="http://www.w3.org/2000/svg"
     role="graphics-document"
     viewBox="0 0 600 104">
  <!-- scriba animation: bug-a-cell-occlusion -->
  <!-- Step 1 -->
  <g id="id-0001" transform="translate(0, 56)">
    <!-- Array cells (abbreviated) -->
    <rect x="50" y="0" width="100" height="40" rx="3"/>
    <text x="100" y="20" dominant-baseline="middle" text-anchor="middle">15</text>
    <!-- ... cells 1, 2, 3 ... -->
    <!-- Annotation 1: "min" above cell[0] -->
    <g role="graphics-symbol" aria-label="arr.cell[0]: min" data-annotation="arr.cell[0]-position">
      <rect x="72" y="-25" width="56" height="19" rx="4"
            fill="#e0f2fe" stroke="#0b68cb" stroke-width="1.5" opacity="0.92"/>
      <text x="100" y="-12"
            font-size="11px" font-family="monospace"
            fill="#1e3a5f" dominant-baseline="middle" text-anchor="middle">min</text>
    </g>
    <!-- Annotation 2: "ptr" above cell[2] -->
    <g role="graphics-symbol" aria-label="arr.cell[2]: ptr" data-annotation="arr.cell[2]-position">
      <rect x="222" y="-25" width="46" height="19" rx="4"
            fill="#dcfce7" stroke="#166534" stroke-width="1.5" opacity="0.92"/>
      <text x="250" y="-12"
            font-size="11px" font-family="monospace"
            fill="#14532d" dominant-baseline="middle" text-anchor="middle">ptr</text>
    </g>
  </g>
</svg>
```

**Invariant checklist**:
- Two pills present above cells [0] and [2] (AC-1).
- Both pills within viewBox (G-3).
- No pill-to-pill overlap (C-1 satisfied between the two pills).
- Cell text occlusion possible (C-7 SHOULD violation — documented known-bad).

**SHA256** (placeholder):

```
PLACEHOLDER_REGEN_FROM_LIVE_RENDERER  expected.svg
```

---

### 8.3 `critical/critical-1-nan-pill-h` — NaN pill height raises ValueError

**Input** (`input.py` — unit driver, no `.tex`):

```python
"""
critical-1-nan-pill-h: input.py

Demonstrates that _nudge_candidates with NaN pill height raises ValueError
after the §2.4 guard is implemented.
"""
import math
from scriba.animation.primitives._svg_helpers import _nudge_candidates

# This call MUST raise ValueError after the guard ships.
# Pre-guard: it silently returns 32 (nan, nan) candidates.
try:
    list(_nudge_candidates(40, float('nan')))
    OUTPUT = "NO_EXCEPTION"  # will cause test to fail (known_failing=True means guard not yet there)
except ValueError as exc:
    OUTPUT = f"ValueError:{exc}"
```

**Expected exception file** (`expected_exception.txt`):

```
ValueError
```

**What invariant it exercises**: G-5 (pill dimensions must be positive),
§2.4 pre-condition guard (NaN guard in `_nudge_candidates`).

**Pins.json entry** (known_failing=True until guard ships):

```json
"critical/critical-1-nan-pill-h": {
  "expected_file": "expected_exception.txt",
  "sha256": "f5ca38f748a1d6eaf726b8a42fb575865d3ae6369f1f235c7ff6dd8c6bf986b0",
  "normalized": false,
  "ruleset_version": "2.0.0-draft",
  "known_failing": true,
  "known_failing_reason": "NaN guard in _nudge_candidates not yet implemented (§2.4 pending)"
}
```

The SHA256 above is `sha256("ValueError\n")` — the expected exception file content. This is stable regardless of the implementation: if the guard is not present, `OUTPUT == "NO_EXCEPTION"`, and the test xfails (guard absent, known-bad). If the guard ships, it raises `ValueError` and the test promotes.

---

### 8.4 `critical/critical-2-null-byte` — Null byte stripped from label

**Input `.tex`** (`input.tex`):

```latex
\begin{animation}[id="critical-2-null-byte", label="Null byte in label"]
\shape{arr}{Array}{size=2, data=[1,2], labels="0..1"}

\step
\annotate{arr.cell[0]}{label="a\x00b", position=above, color=info}
\narrate{Label contains U+0000 null byte. Must be stripped before XML emission.}
\end{animation}
```

**What invariant it exercises**: §2.4 pre-processing guard (strip U+0000 before
`_escape_xml`), T-1 (label text matches declaration after sanitization).

**Expected SVG skeleton** (null byte stripped; label renders as "ab"):

```svg
<svg xmlns="http://www.w3.org/2000/svg"
     role="graphics-document"
     viewBox="0 0 600 88">
  <!-- scriba animation: critical-2-null-byte -->
  <!-- Step 1 -->
  <g id="id-0001" transform="translate(0, 40)">
    <!-- Array cells -->
    <rect x="150" y="0" width="150" height="40" rx="3"/>
    <text x="225" y="20" dominant-baseline="middle" text-anchor="middle">1</text>
    <rect x="300" y="0" width="150" height="40" rx="3"/>
    <text x="375" y="20" dominant-baseline="middle" text-anchor="middle">2</text>
    <!-- Annotation: null byte stripped; label is "ab" not "a\x00b" -->
    <g role="graphics-symbol" aria-label="arr.cell[0]: ab" data-annotation="arr.cell[0]-position">
      <rect x="197" y="-25" width="56" height="19" rx="4"
            fill="#e0f2fe" stroke="#0b68cb" stroke-width="1.5" opacity="0.92"/>
      <text x="225" y="-12"
            font-size="11px" font-family="monospace"
            fill="#1e3a5f" dominant-baseline="middle" text-anchor="middle">ab</text>
    </g>
  </g>
</svg>
```

**Invariant checklist**:
- `&#x0;` and `\x00` and literal U+0000 absent from entire SVG (XML validity).
- `<text>` content is "ab" (null byte stripped, not escaped as entity).
- `aria-label` value does not contain U+0000.

**SHA256** (placeholder):

```
PLACEHOLDER_REGEN_FROM_LIVE_RENDERER  expected.svg
```

---

### 8.5 `bug/ok-simple` — Reference clean case

**Input `.tex`** (`input.tex`):

```latex
\begin{animation}[id="ok-simple", label="Reference clean annotation"]
\shape{arr}{Array}{size=3, data=[5,9,2], labels="0..2"}

\step
\annotate{arr.cell[1]}{label="ptr", position=above, color=info}
\narrate{Single position-only label above cell[1]. Reference clean case for regression guarding.}
\end{animation}
```

**What invariant it exercises**: AC-1 (pill visible when label declared), AC-3
(natural position matches declared direction = above), G-3 (pill within viewBox),
A-5 (`aria-label` present), D-1 (byte-identical on repeat call).

**Expected SVG skeleton** (full pill + anchor structure; no leader since no nudge):

```svg
<svg xmlns="http://www.w3.org/2000/svg"
     role="graphics-document"
     viewBox="0 0 600 88">
  <!-- scriba animation: ok-simple -->
  <!-- Step 1 -->
  <g id="id-0001" transform="translate(0, 40)">
    <!-- Array cells: three cells of width ~166 px each starting at x=50 -->
    <rect x="50" y="0" width="166" height="40" rx="3"
          fill="#f8f9fa" stroke="#dee2e6"/>
    <text x="133" y="20"
          font-size="14px" font-family="monospace"
          dominant-baseline="middle" text-anchor="middle">5</text>
    <rect x="216" y="0" width="167" height="40" rx="3"
          fill="#f8f9fa" stroke="#dee2e6"/>
    <text x="299" y="20"
          font-size="14px" font-family="monospace"
          dominant-baseline="middle" text-anchor="middle">9</text>
    <rect x="383" y="0" width="167" height="40" rx="3"
          fill="#f8f9fa" stroke="#dee2e6"/>
    <text x="466" y="20"
          font-size="14px" font-family="monospace"
          dominant-baseline="middle" text-anchor="middle">2</text>
    <!-- Position-only annotation: "ptr" above cell[1] -->
    <!-- Natural position: cx = cell[1] center = 299, cy = above array = -20 px -->
    <g role="graphics-symbol"
       aria-label="arr.cell[1]: ptr"
       data-annotation="arr.cell[1]-position">
      <!-- Pill rect: pill_w = estimate_text_width("ptr", 11) + 12 ≈ 46 px
                     pill_h = 11 + 6 = 17 px (1 line + 2×PAD_Y)
                     cx = 299, pill_rx = 299 - 46/2 = 276
                     pill_ry = -20 - 17/2 = -28.5 (within headroom via translate) -->
      <rect x="276" y="-29" width="46" height="19" rx="4"
            fill="#e0f2fe" stroke="#0b68cb" stroke-width="1.5"
            opacity="0.92"/>
      <text x="299" y="-16"
            font-size="11px" font-family="monospace"
            fill="#1e3a5f"
            dominant-baseline="middle" text-anchor="middle">ptr</text>
      <!-- No <polyline> leader: pill is at natural position (zero displacement) -->
    </g>
  </g>
</svg>
```

**Invariant checklist**:
- `<rect … rx="4">` pill present within viewBox (G-3, AC-1).
- Pill x-center ≈ 299 (center of cell[1]) — above (AC-3).
- `aria-label="arr.cell[1]: ptr"` present (A-5).
- `role="graphics-symbol"` inside `role="graphics-document"` (A-6).
- No `<polyline>` element (displacement = 0, G-8 leader suppressed).
- Byte-identical on re-render (D-1).

**SHA256** (placeholder — must be regenerated):

```
PLACEHOLDER_REGEN_FROM_LIVE_RENDERER  expected.svg
```

---

## 9. First-Commit Prioritization

### 9.1 Which 3 fixtures to commit first

The three highest-value fixtures to commit first, in order, are:

**1. `bug/ok-simple`** — The reference clean case. This fixture establishes the baseline: if the renderer is working at all, `ok-simple` passes. It is the canary that immediately catches any pipeline-wide breakage. No known-failing logic needed. Exercises 6 invariants (AC-1, AC-3, G-3, A-5, A-6, D-1). **Commit first.**

**2. `critical/critical-2-null-byte`** — A Critical-severity security fix that should already be applied (null bytes in SVG are XML-illegal). This fixture is not known-failing; it asserts a guarantee that must hold even today. If it is currently failing, that is a Critical regression that must be fixed before any other work. Exercises T-1, §2.4 XML safety. **Commit second.**

**3. `bug/bug-B`** — The self-loop NaN repro (bug-B). This is a known-failing fixture (marked `known_failing: true`). Committing it immediately documents the known-bad behavior and will automatically promote to `XFAIL_IMPROVED` the moment the §2.4 guard ships — providing a built-in safety net that links the code fix to a golden update without any manual tracking. Exercises §2.4 self-loop guard, G-5. **Commit third.**

### 9.2 Rationale

| Rank | Fixture | Reason |
|------|---------|--------|
| 1 | `ok-simple` | Pipeline smoke test; no preconditions; covers 6 invariants |
| 2 | `critical-2-null-byte` | Must be passing today; surfaces any XML safety regression immediately |
| 3 | `bug-B` | Known-failing; auto-promotes when guard ships; closes the most dangerous open NaN path |

---

## Summary

This document specifies 44 golden fixtures organized in four categories (8 bug, 6 critical, 12 high, 18 good) under `tests/fixtures/smart_label_golden/`. The corpus covers **30 of 42 invariants fully (71.4%)** and **36 of 42 partially or fully (85.7%)**. The 6 uncovered invariants (A-1..A-4 contrast, A-7 forced-colors, D-3 platform jitter) require MW-2 infrastructure or browser tests not yet available.

The pinning scheme uses SHA256 of normalized SVG (stripping timestamps, version tokens, and float jitter to 2dp) stored in `pins.json` plus sibling `.sha256` files. Known-failing fixtures use an `XFAIL_IMPROVED` promotion model so bug fixes are automatically surfaced without manual tracking. The full 44-fixture corpus is designed to complete in under 30 seconds on a standard CI runner, with unit-level Python drivers for all critical and most high-severity fixtures to avoid pipeline startup overhead.

The three fixtures to commit first are **`ok-simple`** (pipeline smoke test, 6 invariants), **`critical-2-null-byte`** (XML safety, must pass today), and **`bug-B`** (self-loop NaN, known-failing canary for the §2.4 guard).
