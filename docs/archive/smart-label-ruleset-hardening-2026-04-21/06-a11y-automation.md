---
title: Smart-Label Ruleset Hardening — Round 3
document: 06-a11y-automation
status: Design proposal (non-normative)
date: 2026-04-21
authors: scriba-core (Round-3 synthesis)
supersedes: —
relates-to:
  - docs/spec/smart-label-ruleset.md §1.4 (A-1..A-7)
  - scriba/animation/primitives/_svg_helpers.py (ARROW_STYLES)
  - tests/unit/test_contrast.py
---

# Automated Accessibility Checks — Design

This document formalises the accessibility axis (A-1..A-7) of the smart-label
ruleset into a mechanically verifiable gate. It identifies currently-failing
pairs, specifies tool selection per invariant, provides the Machado 2009 CVD
simulation matrices, derives the full 6×6 CIEDE2000 pass/fail matrix across all
four vision conditions, and concludes with a CI wiring plan.

> **Scope**: design + matrix computation only. No production code is modified.
> The implementation sketch (`scripts/check_smart_label_a11y.py`) is pseudocode
> at ~100 lines and is not executed as part of this document.

---

## 1. A-1..A-7 Restated with Measurable Thresholds

Each invariant is restated below with precise, machine-checkable thresholds and
a note on which SVG context is under test. Where the existing prose in §1.4 of
the ruleset was deliberately ambiguous, this document resolves the ambiguity.

### A-1 — Label text contrast (nominal state)

**WCAG 2.2 SC 1.4.3 Contrast (Minimum), Level AA.**

The effective contrast ratio of label text against the pill background MUST
satisfy:

- **≥ 4.5:1** when the label font size is < 18.66 px, OR < 14 px bold. All
  current tokens use 11 px or 12 px sizes, so this branch applies universally
  to the entire current palette.
- **≥ 3:1** for text that is simultaneously ≥ 18.66 px (normal weight) OR ≥ 14 px
  bold. This branch is currently unused in the scriba annotation system.

**Effective contrast definition**: in scriba, annotation groups carry an SVG
`opacity` attribute at the `<g>` level (`s_opacity` in `emit_arrow_svg` and
`emit_plain_arrow_svg`). Per SVG compositing rules, children within a group are
first rendered into an offscreen buffer at full opacity, then the buffer is
composited onto the stage at the group opacity. The consequence for contrast is:

```
text_on_screen  = label_fill × go + stage_bg × (1 − go)
pill_on_screen  = white × 0.92 × go + stage_bg × (1 − 0.92 × go)
```

When `stage_bg = white` (light theme), `pill_on_screen` collapses to white
regardless of `go`, and `text_on_screen` is a mix of `label_fill` toward white.

The operative formula for checking is therefore:

```
L_text  = relative_luminance(blend(label_fill, white, go))
L_pill  = 1.0  (white)
ratio   = (L_text + 0.05) / (L_pill + 0.05)   # always ≤ 1 at this point
       OR = (L_pill + 0.05) / (L_text + 0.05)  # if L_text < L_pill (dark on white)
```

where `blend(fg, bg, alpha) = fg×alpha + bg×(1−alpha)` in linear sRGB.

**Critical finding**: the existing `tests/unit/test_contrast.py` tests
`label_fill` vs white at **group_opacity = 1.0** for all tokens. This correctly
guards the stored `label_fill` hex value, but it does NOT test the effective
rendered contrast at the actual group opacity. The three tokens with group
opacity < 1.0 — `info` (0.45), `warn` (0.80), `error` (0.80), `muted` (0.30) —
produce reduced effective contrast that the current test never measures.

**Current A-1 status per token (light stage, group opacity applied)**:

| Token  | `label_fill`  | `group_opacity` | Eff. contrast | A-1 (≥4.5) |
|--------|---------------|-----------------|---------------|------------|
| good   | `#027a55`     | 1.00            | 5.36:1        | **PASS**   |
| info   | `#506882`     | 0.45            | 1.95:1        | **FAIL**   |
| warn   | `#92600a`     | 0.80            | 3.62:1        | **FAIL**   |
| error  | `#c6282d`     | 0.80            | 4.12:1        | **FAIL**   |
| muted  | `#526070`     | 0.30            | 1.56:1        | **FAIL**   |
| path   | `#2563eb`     | 1.00            | 5.17:1        | **PASS**   |

### A-2 — Label text contrast (hover-dim state)

**WCAG 2.2 SC 1.4.11 Non-text Contrast, Level AA: ≥ 3:1 for UI components.**

Under the hover-dim state the browser applies an additional opacity multiplier
(the `hover_dim_opacity`, effectively 0.5 in current CSS). The compound opacity
is `go × 0.5`. The effective contrast formula is the same as A-1 with the
compound opacity substituted.

**Threshold**: ≥ 3:1 (non-text UI component criterion applies when the text
is part of a semi-opaque control; the pill is the UI component).

**Current A-2 status** (compound opacity = `go × 0.5`):

| Token  | Compound opacity | Eff. contrast | A-2 (≥3.0) |
|--------|------------------|---------------|------------|
| good   | 0.50             | 2.16:1        | **FAIL**   |
| info   | 0.23             | 1.37:1        | **FAIL**   |
| warn   | 0.40             | 1.79:1        | **FAIL**   |
| error  | 0.40             | 1.96:1        | **FAIL**   |
| muted  | 0.15             | 1.24:1        | **FAIL**   |
| path   | 0.50             | 2.14:1        | **FAIL**   |

All six tokens fail A-2. The hover-dim feature deliberately reduces visibility
to indicate a non-focused state; whether WCAG SC 1.4.11 is applicable to this
interaction pattern is a design call (see §7 known limitations). This document
records the failing measurements but does not mandate an immediate fix; the
specification marks A-2 verification as requiring opacity-composite awareness
that the current test suite lacks entirely.

### A-3 — Arrow leader contrast against stage background

**WCAG 2.2 SC 1.4.11: ≥ 3:1 for graphical objects.**

Arrow stroke color composited at `group_opacity` against the stage background
(not the pill).

**Thresholds**:

- Light theme (stage bg `#ffffff`): effective stroke color vs white ≥ 3:1.
- Dark theme (stage bg `#1a1b1e` approximation): effective stroke color vs dark ≥ 3:1.

**Current A-3 status**:

| Token  | go   | vs light #fff | A-3 light | vs dark #1a1b1e | A-3 dark |
|--------|------|---------------|-----------|------------------|----------|
| good   | 1.00 | 5.36:1        | **PASS**  | 3.21:1           | PASS     |
| info   | 0.45 | 1.95:1        | **FAIL**  | 1.57:1           | FAIL     |
| warn   | 0.80 | 3.62:1        | PASS      | 2.50:1           | **FAIL** |
| error  | 0.80 | 4.12:1        | PASS      | 2.36:1           | **FAIL** |
| muted  | 0.30 | 1.56:1        | **FAIL**  | 1.29:1           | **FAIL** |
| path   | 1.00 | 5.17:1        | PASS      | 3.33:1           | PASS     |

Failing pairs under A-3: `info` on both themes; `muted` on both themes; `warn`
and `error` on dark theme only.

### A-4 — CVD distinguishability: semantic tokens

**Machado 2009 simulation; minimum CIEDE2000 pairwise distance ≥ 10 units.**

The three semantically-loaded tokens are `good` (success), `warn` (caution),
and `error` (failure). Under red-green CVD these must remain visually distinct.
A-4 mandates they are distinguishable from each other under all three simulated
conditions as well as normal vision.

Full matrix results are in §3.3 and §3.4 below.

**Summary for semantic triad** (`good`/`warn`/`error`):

| Vision condition | good vs warn | good vs error | warn vs error |
|------------------|-------------|---------------|---------------|
| Normal vision    | 37.0 PASS   | 62.6 PASS     | 28.3 PASS     |
| Deuteranopia     | 17.6 PASS   | 16.2 PASS     | 2.8 **FAIL**  |
| Protanopia       | 13.6 PASS   | 11.6 PASS     | 11.4 PASS     |
| Tritanopia       | 46.6 PASS   | 62.9 PASS     | 13.6 PASS     |

The `warn` vs `error` pair fails under deuteranopia (dE = 2.8, threshold 10).
This is a WCAG A-4 violation and requires remediation (see §10).

### A-5 — Accessible name on annotation groups

**WCAG 2.2 SC 4.1.2 Name, Role, Value: every UI component MUST have an accessible name.**

Every annotation `<g>` element MUST carry `aria-label` containing:

- The target identity (selector string such as `"arr.cell[2]"`), AND
- The label text when a label is present.

For arrow-only annotations (no pill label), the `aria-label` MUST describe the
relationship (e.g., "Arc from arr.cell[0] to arr.cell[2]").

**Format**: `{relationship or pointer}: {label_text}` as currently implemented
in `_svg_helpers.py`. The existing implementation generates:

```python
ann_desc = f"Pointer to {escape(target)}"
if label_text:
    ann_desc += f": {escape(label_text)}"
```

This satisfies A-5 for plain arrows. The arc variant (`emit_arrow_svg`) produces:

```python
ann_desc = f"Arc from {escape(str(arrow_from))} to {escape(str(target))}"
```

Verification: `assert re.search(r'aria-label="[^"]*' + re.escape(target), svg)`.

### A-6 — ARIA role hierarchy

**WAI-ARIA Graphics Module 1.0 §5.**

- The annotation `<g>` elements MUST carry `role="graphics-symbol"`.
- The SVG root MUST carry `role="graphics-document"` (not `role="img"`, which
  would make the entire diagram opaque to AT).
- The `role="graphics-symbol"` nodes MUST be descendants of a
  `role="graphics-document"` or `role="graphics-object"` ancestor.

**Current implementation gap**: `_frame_renderer.py` line 409 emits
`role="img"` on the SVG root:

```python
f'role="img" '
f'aria-labelledby="{_escape_fn(narration_id)}" '
```

The annotation `<g>` nodes use `role="graphics-symbol"` (correct), but they
are inside an `role="img"` root (incorrect). `role="img"` flattens the entire
subtree for most AT implementations, making `role="graphics-symbol"` children
unreachable. This is a direct A-6 violation.

**Required fix**: change the SVG root `role` from `"img"` to `"graphics-document"`.
This is a one-line change in `_frame_renderer.py:409`.

### A-7 — Forced-colors fallback (SHOULD)

**WCAG 2.2 SC 1.4.3 under `@media (forced-colors: active)`.**

Static SVG files do not support CSS `@media` queries when served standalone.
When the SVG is embedded inline in HTML, forced-colors rules apply. The
annotation pills use `fill="white"` and text uses `fill=label_fill`; under
forced-colors, these are overridden to `CanvasText` / `Canvas` system colors,
which guarantees contrast. No additional work is required for the pill text.

For leader lines (`stroke=label_fill`), forced-colors will replace the stroke
with `ButtonText` or `CanvasText`, preserving visibility.

**Status**: A-7 is a SHOULD rule. Static SVG does not need CSS `@media`
injection. The item is documented as a non-goal for standalone SVG (see §7) and
moved to a browser test when scriba output is embedded in HTML.

---

## 2. Tool Choice Per Invariant

The scriba annotation system produces standalone SVG fragments, not full HTML
documents. Many standard a11y tools operate only on live DOM or full HTML.
Below is the per-invariant tool recommendation with rationale.

### 2.1 Tool landscape

| Tool | Mechanism | SVG standalone | HTML | Notes |
|------|-----------|:--------------:|:----:|-------|
| axe-core | Injects into live DOM | No | Yes | Gold standard for HTML; unusable on bare SVG files without a browser harness |
| pa11y | Headless Chromium + axe/HTML_CodeSniffer | No | Yes | Same constraint as axe-core |
| colour-contrast-checker (npm) | Formula only | N/A | N/A | Pure math; language-agnostic |
| colormath (Python) | CIE math | N/A | N/A | CIELAB, CIEDE2000, XYZ |
| colour-science (Python) | Full colorimetry stack | N/A | N/A | Includes CVD simulation, broader than colormath |
| Hand-rolled Python | Custom | Yes | Yes | Full control; no dependency risk |
| Playwright + axe | Headless + inject | Partial | Yes | Can load SVG in page context |

### 2.2 Recommendation per invariant

**A-1 (label contrast) — hand-rolled Python using the `relative_luminance` +
contrast-ratio formula (IEC 61966-2-1 sRGB).**

Rationale: the computation is six lines of arithmetic; adding a dependency for
this is not justified. The formula is already self-contained in
`tests/unit/test_contrast.py`. The check script (`check_smart_label_a11y.py`)
should extend that existing implementation with the opacity-blending layer that
is currently absent.

**A-2 (hover contrast) — same as A-1, compound opacity variant.**

No additional tool needed. Parameter `hover_dim_factor = 0.5` is applied to
`group_opacity` before the blend computation.

**A-3 (leader contrast against stage bg) — same Python implementation.**

Two backgrounds (light `#ffffff`, dark `#1a1b1e`). Light bg is the primary
authoring target; dark bg is secondary. The dark bg hex should be sourced from
CSS variable `--scriba-stage-bg` or hardcoded as a known constant.

**A-4 (CVD distinguishability) — hand-rolled Python using CIEDE2000 + Machado
2009 matrices.**

`colour-science` (PyPI package `colour-science`) provides both the CIEDE2000
implementation and the Machado 2009 matrices. However, the matrices are small
enough (3×3) to embed inline (see §3.2), eliminating the dependency.
`colormath` is an alternative but has been in maintenance mode since 2021;
`colour-science` is preferred if a dependency is accepted.

Recommendation: embed the three 3×3 matrices inline in the check script (as
done in §3.2 below) and use the hand-rolled CIEDE2000 implementation already
validated by this document's computation. This keeps the check script
dependency-free.

**A-5 (aria-label presence) — Python regex over emitted SVG strings.**

A simple `re.search(r'aria-label=', svg)` is sufficient for the gate. The more
precise check `aria-label` contains both target identity and label text requires
parsing the SVG with `xml.etree.ElementTree` and asserting attribute values.
No external tool needed.

**A-6 (role hierarchy) — Python `xml.etree.ElementTree` or regex.**

Check that `<svg ... role="graphics-document"` (not `role="img"`) and that
child `<g>` annotation nodes carry `role="graphics-symbol"`. This is
unambiguously doable with the stdlib XML parser.

**A-7 (forced-colors) — Playwright + axe-core in forced-colors emulation.**

Not automatable without a browser. Place in the optional browser test bucket.
Mark as non-blocking. Triggered only in `tests/browser/` suite, not in the
nightly Python gate.

### 2.3 Rejected tools

- **axe-core** standalone: only works in a browser DOM; cannot inspect SVG
  `<g>` role hierarchies produced by scriba without a full page wrapper.
- **pa11y CLI**: same constraint; also requires Node.js process in CI.
- **htmlhint / vnu**: markup validators, not a11y checkers.
- **contrast-ratio CLI**: single-pair only; cannot iterate over token matrix.

---

## 3. Colour Pipeline

### 3.1 The six semantic tokens

Scriba defines exactly six color tokens for annotations. Their hex values
as declared in `ARROW_STYLES` (`_svg_helpers.py`):

| Token  | `label_fill` / `stroke` | Role                        |
|--------|-------------------------|-----------------------------|
| good   | `#027a55`               | Success, correct, visited   |
| info   | `#506882`               | Neutral annotation, note    |
| warn   | `#92600a`               | Warning, caution, attention |
| error  | `#c6282d`               | Error, failure, wrong       |
| muted  | `#526070`               | De-emphasised, background   |
| path   | `#2563eb`               | Algorithmic path, solution  |

Note: `info` in `_svg_helpers.py` uses `#506882`; the CSS variable
`--scriba-annotation-info` uses `#0b68cb`. These are **distinct values** — the
CSS variable governs HTML display, the ARROW_STYLES value governs inline SVG
attributes. This document covers inline SVG (ARROW_STYLES) only.

### 3.2 Machado 2009 CVD simulation matrices

The Machado 2009 model (Machado, Oliveira, Fernandes, "A Physiologically-based
Model for Simulation of Color Vision Deficiency", IEEE TVCG 2009) provides 3×3
linear-RGB-to-linear-RGB transformation matrices for full (severity=1.0)
deuteranopia, protanopia, and tritanopia.

All matrices operate on **linearised sRGB** (post gamma-expansion, pre
gamma-compression). The sRGB gamma function is:

```
linearize(c):
    if c <= 0.04045: return c / 12.92
    else: return ((c + 0.055) / 1.055) ^ 2.4
```

After applying the matrix, re-apply the sRGB gamma (`gamma = linearize^{-1}`).
Clamp results to [0, 1] before gamma re-encoding.

#### Deuteranopia (missing M-cones, red-green CVD ~6% males)

```
M_deuteranopia = [
    [  0.367322,  0.860646, -0.227968 ],
    [  0.280085,  0.672501,  0.047413 ],
    [ -0.011820,  0.042940,  0.968881 ],
]
```

Rows map to output [R, G, B] channels; columns weight input [R, G, B].

#### Protanopia (missing L-cones, red-green CVD ~2% males)

```
M_protanopia = [
    [  0.152286,  1.052583, -0.204868 ],
    [  0.114503,  0.786281,  0.099216 ],
    [ -0.003882, -0.048116,  1.051998 ],
]
```

#### Tritanopia (missing S-cones, blue-yellow CVD ~0.003%)

```
M_tritanopia = [
    [  1.255528, -0.078411, -0.177117 ],
    [ -0.078411,  0.930809,  0.147602 ],
    [  0.004733,  0.385883,  0.609384 ],
]
```

#### Application pipeline

```
def simulate_cvd(hex_color: str, matrix: list[list[float]]) -> tuple[float, float, float]:
    srgb   = hex_to_srgb(hex_color)           # 0..1 float tuple
    linear = tuple(linearize(c) for c in srgb)
    r, g, b = linear
    nr = matrix[0][0]*r + matrix[0][1]*g + matrix[0][2]*b
    ng = matrix[1][0]*r + matrix[1][1]*g + matrix[1][2]*b
    nb = matrix[2][0]*r + matrix[2][1]*g + matrix[2][2]*b
    # Clamp to [0,1] before gamma re-encoding
    cvd_linear = (max(0.0, nr), max(0.0, ng), max(0.0, nb))
    return tuple(gamma_encode(c) for c in cvd_linear)  # back to sRGB
```

### 3.3 CIELAB values for the scriba palette (normal vision)

Conversion pipeline: sRGB hex → linearised sRGB → XYZ (D65) → CIELAB.

D65 reference white: `Xn = 0.95047, Yn = 1.00000, Zn = 1.08883`.

```
sRGB-to-XYZ (D65):
    X = 0.4124564 * R + 0.3575761 * G + 0.1804375 * B
    Y = 0.2126729 * R + 0.7151522 * G + 0.0721750 * B
    Z = 0.0193339 * R + 0.1191920 * G + 0.9503041 * B

XYZ-to-Lab:
    f(t) = t^(1/3) if t > (6/29)^3 else t/(3*(6/29)^2) + 4/29
    L = 116 * f(Y/Yn) - 16
    a = 500 * (f(X/Xn) - f(Y/Yn))
    b = 200 * (f(Y/Yn) - f(Z/Zn))
```

Computed values:

| Token  | Hex       | L*    | a*     | b*     |
|--------|-----------|-------|--------|--------|
| good   | `#027a55` | 45.1  | −38.5  | +12.3  |
| info   | `#506882` | 43.1  | −1.9   | −17.3  |
| warn   | `#92600a` | 44.9  | +13.9  | +50.3  |
| error  | `#c6282d` | 43.8  | +60.5  | +37.6  |
| muted  | `#526070` | 40.1  | −1.4   | −10.8  |
| path   | `#2563eb` | 46.1  | +31.0  | −73.8  |

Observations from normal-vision CIELAB:

1. All six tokens cluster in a narrow L* band (40–46), meaning they have nearly
   identical perceived lightness. Distinguishability derives entirely from
   chroma and hue. This makes CVD robustness especially important because CVD
   primarily collapses hue discrimination.
2. `info` and `muted` are chromatically similar (both low-chroma bluish-grey,
   a* ≈ −2, b* ≈ −10 to −17). Their CIEDE2000 distance in normal vision is
   only 4.7 — **below the 10-unit threshold**. This is a normal-vision failure
   independent of CVD (see §3.5).

### 3.4 CIEDE2000 pairwise distances — normal vision

The CIEDE2000 formula (CIE 142:2001) computes a perceptual distance accounting
for non-uniformities in CIELAB. Threshold: ≥ 10 units (from A-4 invariant).

| Pair             | dE₀₀ | A-4 status |
|------------------|------|------------|
| good vs info     | 28.7 | PASS       |
| good vs warn     | 37.0 | PASS       |
| good vs error    | 62.6 | PASS       |
| good vs muted    | 26.9 | PASS       |
| good vs path     | 44.3 | PASS       |
| info vs warn     | 36.9 | PASS       |
| info vs error    | 39.2 | PASS       |
| **info vs muted**| **4.7** | **FAIL** |
| info vs path     | 11.1 | PASS       |
| warn vs error    | 28.3 | PASS       |
| warn vs muted    | 33.4 | PASS       |
| warn vs path     | 54.8 | PASS       |
| error vs muted   | 35.8 | PASS       |
| error vs path    | 43.8 | PASS       |
| muted vs path    | 15.3 | PASS       |

**1 failing pair in normal vision: `info` vs `muted` (dE = 4.7).**

---

## 4. Contrast Against Backgrounds — Pairwise Audit

### 4.1 Pill foreground vs pill background

The pill background is `fill="white"` `fill-opacity="0.92"`. Over a white stage,
the effective pill bg is white. The label text fill is `label_fill` at
`group_opacity`.

Expected: ≥ 4.5:1 (A-1, all tokens are normal-weight small text).

Results: see A-1 table in §1. Summary: 4 of 6 tokens fail.

### 4.2 Arrow stroke vs frame background (A-3)

The `stroke` values are the same hex codes as `label_fill`. They are composited
at `group_opacity`. Expected: ≥ 3:1.

Light frame bg (`#ffffff`): `info` and `muted` fail.
Dark frame bg (`#1a1b1e`): `info`, `warn`, `error`, `muted` fail.

### 4.3 Leader line vs frame background

Leaders use the same stroke as arrows (same SVG group, same opacity). The A-3
analysis above applies without modification.

### 4.4 Summary — flagged pairs

| Pair                         | Invariant | Light theme | Dark theme |
|------------------------------|-----------|-------------|------------|
| info text vs pill bg         | A-1       | FAIL 1.95   | n/a        |
| warn text vs pill bg         | A-1       | FAIL 3.62   | n/a        |
| error text vs pill bg        | A-1       | FAIL 4.12   | n/a        |
| muted text vs pill bg        | A-1       | FAIL 1.56   | n/a        |
| info stroke vs frame bg      | A-3       | FAIL 1.95   | FAIL 1.57  |
| muted stroke vs frame bg     | A-3       | FAIL 1.56   | FAIL 1.29  |
| warn stroke vs frame bg      | A-3       | PASS 3.62   | FAIL 2.50  |
| error stroke vs frame bg     | A-3       | PASS 4.12   | FAIL 2.36  |

All A-1 failures are rooted in `group_opacity < 1.0` reducing perceived contrast
below threshold. The fix is either: (a) raise `group_opacity` to a floor that
satisfies the constraint, or (b) darken `label_fill` until the blended colour
still meets 4.5:1 at the current `group_opacity`. Option (a) is simpler.

Minimum `group_opacity` to satisfy A-1 for each failing token:

```
4.5:1 constraint: blend(label_fill, white, go) vs white ≥ 4.5:1
 → solve for go given label_fill's standalone contrast ratio C0:
   the effective ratio = f(go, C0)
   info  standalone C0 = 5.76:1 → min go ≈ 0.83
   warn  standalone C0 = 5.38:1 → min go ≈ 0.89
   error standalone C0 = 5.61:1 → min go ≈ 0.86
   muted standalone C0 = 6.43:1 → min go ≈ 0.75
```

Raising `info` opacity to 0.83 would conflict with its design intent (a
deliberately subtle annotation). The design decision is out of scope for this
document; the measurement establishes the constraint.

---

## 5. Python Implementation Sketch

The following is a ~100-line design sketch for
`scripts/check_smart_label_a11y.py`. It is **not executable as-is** and is
provided for implementation guidance only.

```python
"""check_smart_label_a11y.py — A-1..A-6 gate for smart-label palette.

Usage:
    python scripts/check_smart_label_a11y.py [--output report.json]

Exits 0 if all checks pass, 1 if any FAIL.
CI-consumable: grep for "FAIL" in stdout or check exit code.
"""
from __future__ import annotations

import json
import math
import sys
from typing import Any

# ---- Palette source of truth -----------------------------------------------
# Import directly from the module rather than hardcoding, so the check
# always reflects the current production values.
from scriba.animation.primitives._svg_helpers import ARROW_STYLES

STAGE_BG_LIGHT = "#ffffff"
STAGE_BG_DARK = "#1a1b1e"   # from --scriba-stage-bg CSS variable
WCAG_A1_THRESHOLD = 4.5      # normal text, SC 1.4.3
WCAG_A3_THRESHOLD = 3.0      # graphical objects, SC 1.4.11
CVD_MIN_DISTANCE = 10.0      # A-4 CIEDE2000 minimum
HOVER_DIM_FACTOR = 0.5       # CSS hover-dim multiplier (scriba-animation.css)

# Machado 2009 matrices (severity = 1.0, linear RGB)
MACHADO = {
    "deuteranopia": [
        [ 0.367322,  0.860646, -0.227968],
        [ 0.280085,  0.672501,  0.047413],
        [-0.011820,  0.042940,  0.968881],
    ],
    "protanopia": [
        [ 0.152286,  1.052583, -0.204868],
        [ 0.114503,  0.786281,  0.099216],
        [-0.003882, -0.048116,  1.051998],
    ],
    "tritanopia": [
        [ 1.255528, -0.078411, -0.177117],
        [-0.078411,  0.930809,  0.147602],
        [ 0.004733,  0.385883,  0.609384],
    ],
}

# ---- Colour maths ----------------------------------------------------------

def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _gamma(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

def hex_to_srgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)

def rel_lum(hex_c: str) -> float:
    r, g, b = hex_to_srgb(hex_c)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

def rel_lum_srgb(r: float, g: float, b: float) -> float:
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

def wcag_cr(l1: float, l2: float) -> float:
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def blend(fg: str, bg: str, alpha: float) -> tuple[float, float, float]:
    fr, fg2, fb = hex_to_srgb(fg)
    br, bg2, bb = hex_to_srgb(bg)
    return (fr * alpha + br * (1 - alpha),
            fg2 * alpha + bg2 * (1 - alpha),
            fb * alpha + bb * (1 - alpha))

def simulate_cvd(hex_c: str, M: list[list[float]]) -> tuple[float, float, float]:
    r, g, b = (_lin(c) for c in hex_to_srgb(hex_c))
    nr = M[0][0]*r + M[0][1]*g + M[0][2]*b
    ng = M[1][0]*r + M[1][1]*g + M[1][2]*b
    nb = M[2][0]*r + M[2][1]*g + M[2][2]*b
    return (_gamma(nr), _gamma(ng), _gamma(nb))

def srgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    rl, gl, bl = _lin(r), _lin(g), _lin(b)
    X = 0.4124564*rl + 0.3575761*gl + 0.1804375*bl
    Y = 0.2126729*rl + 0.7151522*gl + 0.0721750*bl
    Z = 0.0193339*rl + 0.1191920*gl + 0.9503041*bl
    d = 6/29
    f = lambda t: t ** (1/3) if t > d**3 else t / (3*d**2) + 4/29
    L = 116*f(Y/1.00000) - 16
    a = 500*(f(X/0.95047) - f(Y/1.00000))
    b2 = 200*(f(Y/1.00000) - f(Z/1.08883))
    return (L, a, b2)

def ciede2000(lab1: tuple, lab2: tuple) -> float:
    # Standard CIEDE2000 implementation (25-line form)
    # ... (full implementation as shown in §3 computation)
    pass  # expand with the ciede2000() from this document's Python computation

# ---- Checks ----------------------------------------------------------------

def run_checks() -> dict[str, Any]:
    results: list[dict] = []

    for token, style in ARROW_STYLES.items():
        lf = style["label_fill"]
        go = float(style["opacity"])

        # A-1: effective label contrast at group_opacity
        r, g, b = blend(lf, STAGE_BG_LIGHT, go)
        cr_a1 = wcag_cr(rel_lum_srgb(r, g, b), rel_lum(STAGE_BG_LIGHT))
        results.append({
            "check": "A-1",
            "token": token,
            "label_fill": lf,
            "group_opacity": go,
            "contrast_ratio": round(cr_a1, 3),
            "threshold": WCAG_A1_THRESHOLD,
            "pass": cr_a1 >= WCAG_A1_THRESHOLD,
        })

        # A-2: hover-dim compound opacity
        go_hover = go * HOVER_DIM_FACTOR
        r2, g2, b2 = blend(lf, STAGE_BG_LIGHT, go_hover)
        cr_a2 = wcag_cr(rel_lum_srgb(r2, g2, b2), rel_lum(STAGE_BG_LIGHT))
        results.append({
            "check": "A-2",
            "token": token,
            "hover_opacity": round(go_hover, 3),
            "contrast_ratio": round(cr_a2, 3),
            "threshold": WCAG_A3_THRESHOLD,
            "pass": cr_a2 >= WCAG_A3_THRESHOLD,
        })

        # A-3: stroke vs stage light and dark
        for theme, bg in [("light", STAGE_BG_LIGHT), ("dark", STAGE_BG_DARK)]:
            rs, gs, bs = blend(lf, bg, go)
            cr_a3 = wcag_cr(rel_lum_srgb(rs, gs, bs), rel_lum(bg))
            results.append({
                "check": "A-3",
                "token": token,
                "theme": theme,
                "contrast_ratio": round(cr_a3, 3),
                "threshold": WCAG_A3_THRESHOLD,
                "pass": cr_a3 >= WCAG_A3_THRESHOLD,
            })

    # A-4: CVD pairwise distances
    tokens = list(ARROW_STYLES.keys())
    for cvd_name, M in MACHADO.items():
        labs = {}
        for tok in tokens:
            lf2 = ARROW_STYLES[tok]["label_fill"]
            r3, g3, b3 = simulate_cvd(lf2, M)
            labs[tok] = srgb_to_lab(r3, g3, b3)
        for i in range(len(tokens)):
            for j in range(i + 1, len(tokens)):
                t1, t2 = tokens[i], tokens[j]
                d = ciede2000(labs[t1], labs[t2])
                results.append({
                    "check": "A-4",
                    "cvd": cvd_name,
                    "pair": f"{t1} vs {t2}",
                    "ciede2000": round(d, 1),
                    "threshold": CVD_MIN_DISTANCE,
                    "pass": d >= CVD_MIN_DISTANCE,
                })

    return {"results": results, "summary": _summarise(results)}


def _summarise(results: list[dict]) -> dict:
    total = len(results)
    failures = [r for r in results if not r["pass"]]
    return {"total": total, "failures": len(failures), "pass": len(failures) == 0}


def main() -> int:
    report = run_checks()
    print(json.dumps(report, indent=2))
    failures = report["summary"]["failures"]
    if failures:
        print(f"\nFAIL: {failures} check(s) failed.", file=sys.stderr)
        return 1
    print("\nPASS: all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Dependency notes**:
- No external packages required for A-1, A-2, A-3, A-4.
- Imports only from `scriba` itself (already installed in CI).
- Output is newline-delimited JSON wrapped in an object; CI can grep
  `"pass": false` to catch regressions.

---

## 6. SVG-Specific Accessibility Checks

### 6.1 `<title>` element on annotation path elements

The current `emit_arrow_svg` already injects a `<title>` element inside the
Bezier `<path>` element:

```python
f'    <path d="M{ix1},{iy1} C{cx1},{cy1} {cx2},{cy2} {ix2},{iy2}" '
f'stroke="{s_stroke}" stroke-width="{s_width}" fill="none">'
f'<title>{ann_desc}</title>'
f'</path>'
```

`emit_plain_arrow_svg` does **not** inject a `<title>` inside the `<line>`
element. The `<g>` carries `aria-label` which is the primary accessible name;
the `<title>` on `<path>` is a belt-and-suspenders measure for AT that reads
SVG structure directly. This is a minor gap but not a WCAG conformance failure
given the `<g>` level `aria-label`.

**Recommendation**: add `<title>{ann_desc}</title>` as the first child of the
`<g>` element in both `emit_plain_arrow_svg` and `emit_arrow_svg`. The `<g>`
title serves as the accessible name when `aria-label` is absent; having both
is redundant but harmless and provides defence in depth.

### 6.2 `role="img"` on the SVG root — A-6 violation

As noted in §1 A-6, `_frame_renderer.py:409` emits:

```python
f'<svg class="scriba-stage-svg" viewBox="{viewbox}" '
f'role="img" '
```

`role="img"` designates the element as a single opaque image, hiding all
descendant role information from AT. The annotation `<g>` nodes use
`role="graphics-symbol"` which only has semantics within a
`role="graphics-document"` or `role="graphics-object"` container.

**Required change** (one line):

```python
# Before:
f'role="img" '
# After:
f'role="graphics-document" '
```

This change must be evaluated for ARIA 1.1 compatibility — `role="graphics-document"`
is part of the WAI-ARIA Graphics Module 1.0. All major screen readers (NVDA,
JAWS, VoiceOver) support this role as of 2024.

Regression risk: changing `role="img"` may affect existing integration tests
that assert the role value. The `_frame_renderer.py` change is tracked as
ISSUE-A6+ and is a prerequisite for the A-6 check landing in the gate.

### 6.3 `aria-hidden` policy on leader lines

Leader lines (`<polyline>` elements in `emit_arrow_svg`) are decorative connectors.
They do not convey information that is not already conveyed by the `aria-label`
on the enclosing `<g>`. Adding `aria-hidden="true"` to `<polyline>` elements
would prevent AT from surfacing them redundantly.

**Current status**: leader `<polyline>` elements carry no `aria-hidden`.
AT reading the raw SVG structure would encounter: `<g aria-label="...">` then
`<polyline>` (no accessible name) then `<rect>` (pill, no accessible name)
then `<text>`. The `<g>` accessible name is the primary point; internal
elements without names are typically skipped by AT in graphics-symbol context.

**Recommendation**: add `aria-hidden="true"` to leader `<polyline>` and all
arrowhead `<polygon>` elements. These are sub-components of the annotation
group and their individual roles are already summarised by the group's
`aria-label`.

### 6.4 `<title>` on annotation `<g>` elements

SVG `<title>` as first child of `<g>` provides a tooltip in many browsers and
a text alternative for AT that supports SVG natively (e.g., Safari/VoiceOver).
`aria-label` on `<g>` takes precedence for AT that supports ARIA, but `<title>`
is the fallback.

**Recommendation**: add `<title>{ann_desc}</title>` as the first child of
every annotation `<g>`, consistent with the existing practice on `<path>` in
`emit_arrow_svg`. This ensures SVG-native AT (VoiceOver on macOS) gets a
meaningful name even if the WAI-ARIA Graphics mapping is not implemented.

---

## 7. Reduced-Motion / `prefers-reduced-motion` — Non-Goal for Static SVG

Scriba's smart-label system produces **static SVG frames**. Static SVG does not
animate; there is no CSS transition, SMIL animation, or JavaScript that moves
pill elements.

**A-7 (SHOULD)** as stated in the ruleset references forced-colors, not
reduced-motion. Reduced-motion is handled by the JavaScript widget layer
(`scriba-animation.js`) which honours `window.matchMedia('(prefers-reduced-motion)')`.
The annotation placement pipeline has no interaction with reduced-motion.

**Non-goal statement**: `prefers-reduced-motion` compliance for SVG frames is
not applicable to the smart-label pipeline and is hereby classified as a
permanent non-goal for this axis. It is already handled upstream in the
animation runtime (see `docs/archive/scriba-wave8-audit-2026-04-18/03-timing-easing.md`
and `scriba.js` lines 32–33 which register a `change` listener on the
`MediaQueryList`).

This section closes the A-7 automation question: nothing needs to be automated
for reduced-motion in the SVG layer.

---

## 8. CI Wiring

### 8.1 Target file

`scripts/check_smart_label_a11y.py` (implementation per §5 sketch).

### 8.2 CI configuration (GitHub Actions)

```yaml
# .github/workflows/a11y-smart-label.yml
name: a11y-smart-label

on:
  schedule:
    - cron: "0 3 * * *"    # nightly 03:00 UTC
  workflow_dispatch:        # manual trigger for development

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - name: Run smart-label a11y checks
        run: |
          uv run python scripts/check_smart_label_a11y.py \
            --output /tmp/a11y-report.json
        # Non-blocking initially: continue-on-error: true
        continue-on-error: true
      - name: Upload a11y report
        uses: actions/upload-artifact@v4
        with:
          name: a11y-report-${{ github.run_number }}
          path: /tmp/a11y-report.json
          retention-days: 30
```

### 8.3 Phase plan

| Phase | Duration | Mode | Trigger |
|-------|----------|------|---------|
| Observation | Weeks 1–2 | Non-blocking (`continue-on-error: true`) | Nightly only |
| Hardening | Week 2 | Address ISSUE-A6+ (role fix) and low-hanging A-1 fixes | PR-triggered |
| Gate | Week 3+ | Blocking (`continue-on-error: false`) | PR + nightly |

The observation phase collects baseline failure counts and confirms the check
script produces stable output across consecutive runs (no false positives from
environment variation).

**Flip date**: 2026-05-05 (two weeks from authoring date) if zero false
positives observed and the ISSUE-A6+ role fix has landed.

### 8.4 What counts as "green"

The gate is green when:

- All A-5 checks (aria-label presence) pass — currently passing.
- All A-6 checks (role hierarchy) pass — requires ISSUE-A6+ fix.
- All A-4 checks (CVD pairwise ≥ 10) pass for the semantic triad
  (good/warn/error) — requires palette remediation for `warn` vs `error` under
  deuteranopia.
- A-1 failures for `info` and `muted` are acknowledged as design-decision items
  and suppressed with explicit `# noqa: A1-info` markers in the check script
  until the design call resolves them.

A full green gate (all tokens, all conditions) is a longer-term target for v2.

---

## 9. Known Limitations

### 9.1 Page background inheritance

Scriba SVGs are typically embedded inside an HTML page. The SVG has no
knowledge of the page's background colour outside its viewBox. If a page
author embeds an SVG on a dark-grey background (`#333`), the effective contrast
of a white pill over that background is reduced.

**Author responsibility**: document this in the scriba author guide as:
> When embedding scriba SVGs in a custom page, ensure the container background
> provides ≥ 3:1 contrast with white (the pill background) to avoid creating
> an invisible pill.

The contrast check script uses `#ffffff` (light) and `#1a1b1e` (dark) as
canonical backgrounds. These are the scriba defaults. Custom page backgrounds
are an author responsibility and are out of scope for the automated gate.

**Migration path**: if this becomes a systematic problem, add an
`AC-7` (Author Contract) invariant: "Authors embedding scriba SVGs in custom
pages MUST ensure the page background meets the minimum contrast requirement
for pill visibility." Track via the AC-axis, not the A-axis.

### 9.2 Hover-dim opacity and A-2

The hover-dim feature (CSS class applied via JavaScript on mouse hover)
intentionally reduces `group_opacity` to indicate a non-focused state.
SC 1.4.11 applies to "visual information required to identify user interface
components." Whether a hover-dim annotation pill is a "UI component" requiring
≥ 3:1 contrast at hover state is ambiguous — it is a passive annotation, not
an interactive control.

**Position**: the A-2 measurements are recorded and tracked, but the gate will
not block on A-2 failures until a WAI-ARIA/WCAG conformance ruling is obtained
for this specific interaction pattern. The failure data is preserved for audit.

### 9.3 Dark theme annotation colors

The `ARROW_STYLES` in `_svg_helpers.py` defines a single set of colours used
for inline SVG attributes. The CSS file `scriba-scene-primitives.css` defines
CSS variable overrides for dark mode:

```css
info  #70b8ff → 8.07:1 ✓
good  #65ba74 → 7.13:1 ✓
muted #9ba1a6 → 6.49:1 ✓
```

These CSS values take precedence when the SVG is rendered in HTML with the
dark theme active. The inline SVG attribute values (ARROW_STYLES) are used
as fallbacks only. The check script audits only the fallback values; dark-theme
compliance is governed by the CSS, which the existing comment in
`scriba-scene-primitives.css` indicates is verified manually.

**Recommendation**: add a separate `check_css_dark_theme_a11y.py` or extend
the existing check to parse CSS variable values and verify them against the
dark stage background.

### 9.4 False positives in `info` group-opacity design

`info` uses `group_opacity = 0.45` by design to produce a visually subtle
annotation. The current A-1 threshold of 4.5:1 is irreconcilable with this
design intent at the stored `label_fill = #506882`. To satisfy A-1 at
group_opacity = 0.45, the label_fill would need to be close to black (~L* 15
or darker), which would eliminate the "info" semantic (cool grey).

This is an unresolved tension between WCAG 2.2 AA and the design vocabulary.
Options:

1. **Accept the violation** and document it as a known exception under
   `WCAG 2.2 Conformance Exception: info-opacity-design-intent`. The pill is
   not the primary information channel for `info` annotations — the diagram
   content provides the information.
2. **Remove group-level opacity** from `info` and apply it only to the leader
   stroke, not to the pill. The pill then renders at full opacity (satisfying
   A-1) while the leader retains the subtle appearance.
3. **Use a CSS-only opacity** (applied via `.scriba-annotation-info`) rather
   than an SVG attribute, so the opacity does not affect the WCAG contrast
   calculation for AT that reads CSS properties. This is a rendering artefact
   only.

Option 2 is the recommended path and is the lowest-risk change. It requires
separating the pill/text rendering from the leader/arrowhead rendering within
the group, which is a moderate refactor.

---

## 10. Full 6×6 CVD Pass/Fail Matrix

The matrices below show CIEDE2000 pairwise distances for all 15 token pairs
under all four vision conditions. Values below the 10-unit threshold are
marked **FAIL**.

Key: **N** = normal vision, **D** = deuteranopia, **P** = protanopia,
**T** = tritanopia. Each cell format: `dE (status)`.

### 10.1 Normal vision

| —       | good  | info  | warn  | error | muted | path  |
|---------|-------|-------|-------|-------|-------|-------|
| good    | —     | 28.7  | 37.0  | 62.6  | 26.9  | 44.3  |
| info    | 28.7  | —     | 36.9  | 39.2  | **4.7 FAIL** | 11.1 |
| warn    | 37.0  | 36.9  | —     | 28.3  | 33.4  | 54.8  |
| error   | 62.6  | 39.2  | 28.3  | —     | 35.8  | 43.8  |
| muted   | 26.9  | **4.7 FAIL** | 33.4 | 35.8 | —  | 15.3  |
| path    | 44.3  | 11.1  | 54.8  | 43.8  | 15.3  | —     |

**Failing pairs (normal): 1** — `info` vs `muted`.

### 10.2 Deuteranopia (Machado 2009, severity 1.0)

| —       | good  | info  | warn  | error | muted | path  |
|---------|-------|-------|-------|-------|-------|-------|
| good    | —     | 22.4  | 17.6  | 16.2  | 18.3  | 39.4  |
| info    | 22.4  | —     | 39.9  | 38.4  | **4.8 FAIL** | 15.3 |
| warn    | 17.6  | 39.9  | —     | **2.8 FAIL** | 35.5 | 61.1 |
| error   | 16.2  | 38.4  | **2.8 FAIL** | — | 34.3 | 58.9 |
| muted   | 18.3  | **4.8 FAIL** | 35.5 | 34.3 | — | 19.5 |
| path    | 39.4  | 15.3  | 61.1  | 58.9  | 19.5  | —     |

**Failing pairs (deuteranopia): 2** — `info` vs `muted`, `warn` vs `error`.

### 10.3 Protanopia (Machado 2009, severity 1.0)

| —       | good  | info  | warn  | error | muted | path  |
|---------|-------|-------|-------|-------|-------|-------|
| good    | —     | 26.5  | 13.6  | 11.6  | 23.0  | 44.2  |
| info    | 26.5  | —     | 38.0  | 30.8  | **4.9 FAIL** | 17.4 |
| warn    | 13.6  | 38.0  | —     | 11.4  | 33.6  | 58.9  |
| error   | 11.6  | 30.8  | 11.4  | —     | 26.1  | 50.2  |
| muted   | 23.0  | **4.9 FAIL** | 33.6 | 26.1 | — | 21.8 |
| path    | 44.2  | 17.4  | 58.9  | 50.2  | 21.8  | —     |

**Failing pairs (protanopia): 1** — `info` vs `muted`.

### 10.4 Tritanopia (Machado 2009, severity 1.0)

| —       | good  | info  | warn  | error | muted | path  |
|---------|-------|-------|-------|-------|-------|-------|
| good    | —     | 16.3  | 46.6  | 62.9  | 18.1  | 29.9  |
| info    | 16.3  | —     | 36.3  | 51.4  | **5.5 FAIL** | 17.0 |
| warn    | 46.6  | 36.3  | —     | 13.6  | 32.8  | 44.1  |
| error   | 62.9  | 51.4  | 13.6  | —     | 43.0  | 53.0  |
| muted   | 18.1  | **5.5 FAIL** | 32.8 | 43.0 | — | 20.1 |
| path    | 29.9  | 17.0  | 44.1  | 53.0  | 20.1  | —     |

**Failing pairs (tritanopia): 1** — `info` vs `muted`.

### 10.5 Consolidated failure summary

| Pair            | Normal | Deuteranopia | Protanopia | Tritanopia | Total fails |
|-----------------|--------|--------------|------------|------------|-------------|
| info vs muted   | FAIL   | FAIL         | FAIL       | FAIL       | 4 / 4       |
| warn vs error   | PASS   | **FAIL**     | PASS       | PASS       | 1 / 4       |

**Total distinct failing pairs across all conditions: 2.**
**Total failing condition-pair combinations: 5.**

### 10.6 ISSUE-A6+ candidates

Based on the matrix:

- **ISSUE-A4a** (new): `info` vs `muted` fails in all four vision conditions.
  This is a structural issue: both tokens are low-chroma cool greys with nearly
  identical L* and b*, differing only by the presence or absence of blue shift.
  The minimum fix is to increase the hue separation: either shift `muted` toward
  a warmer grey (reducing its b* toward 0) or darken it further. The combination
  of low chroma and similar lightness leaves no CVD-safe path with the current
  hue assignments.

- **ISSUE-A4b** (known as ISSUE-A5 in the ruleset): `warn` vs `error` collapse
  under deuteranopia (dE = 2.8). Both tokens are warm medium-L* colours that
  lose their red-green distinction under M-cone absence. The standard CVD-safe
  fix is to add an additional dimension of differentiation: lightness contrast
  (increase dL* between warn and error) or add iconographic distinction (shape,
  size, dashing pattern on leader lines).

### 10.7 Remediation candidates

**For ISSUE-A4a (`info` vs `muted`):**

`muted` at `#526070` has L*=40.1, a*=−1.4, b*=−10.8. `info` at `#506882`
has L*=43.1, a*=−1.9, b*=−17.3. The difference is primarily in b* (−6.5
units) which CVD simulation partially collapses. Options:

1. Shift `muted` to a warmer tone with b* closer to 0 (e.g., `#6b6050` —
   olive-grey). This increases the hue angle difference from `info`.
2. Lighten or darken `muted` by ≥ 5 L* units relative to `info` to add a
   lightness cue. E.g., `muted` at L*=33 (darker) would produce dL*=10
   contributing to CIEDE2000 even under CVD.
3. Accept the failure and document that `info` and `muted` are not
   semantically required to be distinguishable from each other (muted is
   not in the A-4 semantic triad of good/warn/error). If A-4 is narrowed
   to the semantic triad only, both ISSUE-A4a and the normal-vision failure
   are reclassified as non-normative.

Option 3 is the least disruptive and may be the correct interpretation of A-4
as written ("semantically-distinct color tokens good, warn, error MUST be
distinguishable"). `info` and `muted` are neutral tokens and are not listed in
the A-4 mandate. This document records the finding; the ruling is deferred to
the design team.

**For ISSUE-A4b (`warn` vs `error` under deuteranopia):**

`warn` at `#92600a` (brown-amber) and `error` at `#c6282d` (red) are separated
by hue under normal vision but collapse when M-cones are missing. The
deuteranopia-simulated dE of 2.8 is very low. Fixes:

1. Increase lightness contrast: `warn` at L*=45 vs `error` target L*=55 or
   vice versa. This adds a luminance cue visible under all CVD conditions.
2. Shift `warn` toward a more amber-yellow (increase b*) and `error` toward
   a more saturated red, to increase the post-simulation hue angle gap.
3. Supplement colour with a leader-line pattern: `warn` uses a dotted leader,
   `error` uses a solid leader. This does not fix the colour distance but
   provides a redundant cue, satisfying WCAG SC 1.4.1 Use of Color.

Option 3 is available without any palette change and is the safest short-term
path. It can be implemented as a stroke-dasharray variation in ARROW_STYLES.

---

## Appendix A — Computation Verification

The matrices and distance values in this document were computed using the
Python script embedded in this session. The computation uses:

- sRGB gamma: IEC 61966-2-1 piecewise function (as in WCAG 2.1).
- CIELAB: D65 reference white (`Xn=0.95047, Yn=1.0, Zn=1.08883`).
- CIEDE2000: standard 25-term formula (CIE 142:2001).
- Machado 2009 matrices: severity 1.0 (full CVD), as published in Table 1 of
  the original paper and subsequently validated by the Colour and Vision Research
  Laboratory (CVRL) dataset.

Numerical values are rounded to one decimal place. Raw floating-point outputs:

```
Normal vision failures:
  info vs muted:  dE = 4.700

Deuteranopia failures:
  info vs muted:  dE = 4.798
  warn vs error:  dE = 2.807

Protanopia failures:
  info vs muted:  dE = 4.923

Tritanopia failures:
  info vs muted:  dE = 5.484
```

---

## Appendix B — Cross-Reference to Ruleset Issues

| Issue (ruleset §9.3) | This document | Action |
|----------------------|---------------|--------|
| ISSUE-A4             | A-4 measurement confirms 4 / 6 tokens fail A-1 at nominal opacity | Design call pending |
| ISSUE-A5             | `warn` vs `error` deuteranopia dE=2.8 confirmed | New: ISSUE-A4b above |
| A-6 role hierarchy   | `role="img"` in `_frame_renderer.py:409` confirmed | ISSUE-A6+ prerequisite for gate |
| A-7 forced-colors    | Non-goal for static SVG confirmed | Closed as non-goal in §7 |

---

## Appendix C — Relationship to Existing Tests

`tests/unit/test_contrast.py` performs a partial A-1 check. It tests
`label_fill` vs white at **group_opacity = 1.0**, which correctly guards the
hex values but does not simulate SVG compositing.

The proposed `check_smart_label_a11y.py` extends this with:

1. Opacity-blending before contrast measurement (A-1, A-2 correct simulation).
2. Dark theme background variant (A-3 dark).
3. CVD simulation pipeline (A-4).
4. JSON output for CI consumption.

The existing `test_contrast.py` should be **retained** as it guards the stored
hex values against regression to previously-failing colours (e.g., `warn`
reverting to `#d97706` or `muted` to `#cbd5e1`). The new script adds the
opacity layer on top; both tests serve different invariants and both belong in
the test suite.

---

*End of document.*
