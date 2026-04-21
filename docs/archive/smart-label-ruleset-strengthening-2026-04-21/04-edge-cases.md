# Smart-Label Edge-Case Taxonomy

**Date**: 2026-04-21  
**Author**: automated deep-audit  
**Scope**: `scriba/animation/primitives/_svg_helpers.py` — `emit_arrow_svg`,
`emit_plain_arrow_svg`, `emit_position_label_svg`, `_nudge_candidates`,
`_wrap_label_lines`, `_label_width_text`, `_LabelPlacement`  
**Empirical basis**: all "Current behavior" entries were verified by running
minimal Python snippets in `.venv` against the live codebase
(`source .venv/bin/activate && python -c "..."`).  
**Goal**: every entry in this taxonomy must be addressed with an explicit
expected-behavior statement in the normative ruleset before the ruleset is
considered stable.

---

## How to read this document

Each sub-section has a table with five columns:

| Column | Meaning |
|--------|---------|
| **Input** | The exact degenerate / adversarial value |
| **Current behavior** | Empirically verified outcome today |
| **Correct behavior** | What the ruleset should mandate (SPEC = already specified, PROPOSED = gap) |
| **Severity** | Low / Medium / High / Critical (only for PROPOSED gaps) |
| **Pytest one-liner** | Minimal regression-catching assertion |

Severity scale:

- **Critical** — author-visible misbehavior or data corruption (wrong SVG
  accepted as correct, placement loop hangs, output contains `NaN`/`Infinity`)
- **High** — crash or exception where none is expected, or spec invariant
  broken silently
- **Medium** — wrong output that is not a crash (misregistered AABB, off-canvas
  pill, invisible pill) and is visually detectable
- **Low** — aesthetic / marginal issue (slightly wrong pill size, no visible
  artifact in typical use)

---

## 1. Dimension degenerates

These affect `_nudge_candidates(pill_w, pill_h)` and the pill-sizing arithmetic
in all three emit functions.

### 1.1 `pill_h = 0`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_nudge_candidates(40, 0)` | Returns 32 candidates all equal to `(0.0, -0.0)` / `(0.0, 0.0)`. Zero-displacement grid is useless for collision avoidance. No exception raised. | **PROPOSED**: guard `if pill_h <= 0: return` at top of `_nudge_candidates`, or substitute a fallback step (e.g. 8 px). Callers must assert `pill_h > 0` before invoking. | Medium | `assert list(_nudge_candidates(40, 0)) == []` (after guard added) |
| `emit_*` with `l_font_px = 0` (forces `pill_h = PILL_PAD_Y*2 = 6`) | No crash; pill height = 6 px; invisible text rendered at `fi_y`; SVG is syntactically valid but visually broken. | **PROPOSED**: `ARROW_STYLES` must never produce `label_size` that parses to 0 px. Add an assertion: `assert l_font_px > 0` at the top of the font-extraction block. | Medium | `assert l_font_px > 0` in any path that calls emit (unit-verify via patching `ARROW_STYLES`) |

### 1.2 `pill_h < 0`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_nudge_candidates(40, -10)` | Returns 32 candidates with **inverted** signs: step-1 N becomes `(0, +2.5)` instead of `(0, -2.5)`. Half-plane hints are mirrored. No exception. | **PROPOSED**: guard `if pill_h <= 0: return` or raise `ValueError("pill_h must be positive")`. Negative pill heights cannot arise from the current constant set but can from external patching. | Medium | `pytest.raises(ValueError, _nudge_candidates, 40, -10)` (after guard added) |

### 1.3 `pill_h = NaN`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_nudge_candidates(40, float('nan'))` | Returns 32 candidates all `(nan, nan)`. When these are applied as nudge offsets, all resulting `_LabelPlacement` entries have `NaN` coordinates. `NaN.overlaps(any)` always returns `True` (IEEE 754 comparison semantics), so **all 32 candidates fail** the overlap check and `collision_unresolved = True`. The label falls back to its natural position, which may itself have NaN coordinates. | **PROPOSED**: guard `if not math.isfinite(pill_h): raise ValueError(...)` upstream at pill-sizing. `NaN` pill heights cannot arise from current code but can from patched or future external `label_size` values. | Critical | `pytest.raises(ValueError, _nudge_candidates, 40, float('nan'))` (after guard) |

### 1.4 `pill_h = Infinity`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_nudge_candidates(40, float('inf'))` | Returns 32 candidates with mix of `±inf` and `nan` (e.g. `inf * 0 = nan` for diagonal directions). Emitters calling `int(final_x + ndx)` on an `±inf` candidate raise `OverflowError` when they attempt `int(inf)`. | **PROPOSED**: guard `if not math.isfinite(pill_h): raise ValueError(...)`. `Infinity` pill heights cannot arise from current code but can from external patching or future `_label_size_px` helper bugs. | Critical | `pytest.raises(ValueError, _nudge_candidates, 40, float('inf'))` (after guard) |

### 1.5 `pill_w = 0`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_nudge_candidates(0, 20)` | Works correctly — `pill_w` is structurally unused in the body (IR-3 from `01-invariant-gaps.md`). Steps are computed from `pill_h` only. | **SPEC** (docstring acknowledges this): no behavior change needed. `pill_w` is an API placeholder for future aspect-aware steps. | — | `assert len(list(_nudge_candidates(0, 20))) == 32` |

### 1.6 `pill_w < 0`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_nudge_candidates(-60, 20)` | Works correctly — `pill_w` unused. No behavioral difference from `pill_w = 0`. | **SPEC**: same as 1.5 — `pill_w` is ignored. | — | `assert list(_nudge_candidates(-60, 20)) == list(_nudge_candidates(0, 20))` |

### 1.7 `pill_w > viewBox_w` (pill wider than canvas)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| 100-char label in 600 px wide canvas: `pill_w ≈ 694 px`. `fi_x` clamped to `pill_w // 2 = 347`. `pill_rx` clamped to `0`. Pill overflows the right edge by `694 - 600 = 94 px`. | Only the **left-edge clamp** fires (QW-3). The pill renders from `x=0` to `x=694`, overflowing the right edge of the SVG canvas. | **PROPOSED**: add a right-edge x-clamp: `clamped_x = min(clamped_x, viewBox_w - pill_w / 2)`. Requires passing `viewBox_w` to emitters. Alternatively, the ruleset must explicitly state that right-edge overflow is acceptable (out-of-scope). See §3.4 / §2.3 in `smart-label-ruleset.md`. | Medium | `assert pill_rx + pill_w <= viewBox_w` (requires viewBox_w parameter to be added) |

### 1.8 `pill_h > viewBox_h` (pill taller than canvas)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `position_label_height_above` with a 50-line wrapping label: `pill_h` grows with line count but no y-axis clamp exists. Label may render partially off the top or bottom edge. | No y-axis clamp in any emit function. The `translate(0, arrow_above)` on the outer group compensates for space above y=0 but does not prevent bottom-edge overflow. | **PROPOSED**: document that y-axis clamp is out of scope (current `§2.3` says so), OR add a y-axis clamp to close the gap. | Medium | `assert pill_ry >= 0 and pill_ry + pill_h <= viewBox_h` (needs viewBox_h) |

### 1.9 `l_font_px` edge cases

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label_size = "1em"` (non-px unit) | Falls back to `l_font_px = 11` (default in the `else` branch). No warning. | **PROPOSED**: warn or raise on non-`px` `label_size` values. `ARROW_STYLES` currently only has `Npx` entries so this only matters for future styles. | Low | `assert l_font_px == 11` when `label_size` does not end in `'px'` |
| `label_size = "0px"` | `l_font_px = 0` → `pill_h = PILL_PAD_Y * 2 = 6`. Zero-height text anchor. Invisible label. | **PROPOSED**: enforce `l_font_px >= 1`; add assertion at font-extraction. | Medium | `assert l_font_px >= 1` in emit path |
| `label_size` negative (`"-12px"`) | `l_font_px = -12` → `pill_h < 0`. Negative pill height causes inverted AABB in `_LabelPlacement`. `overlaps` produces wrong results for negative heights. | **PROPOSED**: enforce `l_font_px >= 1`; negative font sizes should raise `ValueError`. | High | `pytest.raises(ValueError, ...)` when `l_font_px < 1` |

---

## 2. Label content degenerates

### 2.1 Empty and whitespace-only labels

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label=""` | `emit_plain_arrow_svg` skips pill (no rect or text emitted). `emit_position_label_svg` returns early at `if not label_text`. Arrow/stem still emitted. | **SPEC**: correct. The ruleset should state: "empty label suppresses pill but does not suppress the arrow." | — | `assert '<rect' not in ''.join(lines)` where `ann = {'label': ''}` |
| `label="   "` (whitespace) | Treated as non-empty (whitespace is truthy in Python). Pill is emitted with whitespace text. Width estimate uses `estimate_text_width('   ', 11)` = small non-zero value. SVG `<text>` renders visually blank with a pill background. | **PROPOSED**: strip label before truthy check. A whitespace-only label should behave the same as `label=""`. | Low | `assert '<rect' not in ''.join(lines)` when `label.strip() == ""` |
| `label=None` | `ann.get("label", "")` returns `""` — treated as empty label. No crash. | **SPEC**: correct fallback. | — | `assert '<rect' not in ''.join(lines)` when `ann` has no `'label'` key |

### 2.2 Math delimiter degenerates

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="$"` (single unmatched dollar) | `_label_has_math` returns `False` (`_MATH_DELIM_RE` requires non-empty body). Treated as plain text. Pill renders literal `$` character. | **SPEC**: correct — the regex `\$[^$]+?\$` intentionally rejects empty bodies. Ruleset should document: "a lone `$` is treated as plain text." | — | `assert not _label_has_math("$")` |
| `label="$$"` (empty math body) | `_label_has_math` returns `False`. Treated as plain text. | **SPEC**: correct. Ruleset should document: "empty math `$$` is treated as plain text." | — | `assert not _label_has_math("$$")` |
| `label="$a$$b$"` (two adjacent math regions) | `_label_has_math` returns `True` (matches `$a$`). `_label_width_text` processes both: strips `$` delimiters via regex → `"ab"`, appends 15% → `"aba"`. KaTeX render sees the full string `"$a$$b$"`. | **PROPOSED**: the `$...$` stripping in `_label_width_text` operates on overlapping regions due to the greedy `re.sub`. Two adjacent regions `$a$$b$` are stripped to `"ab"` (correct), but the width estimate may under-count since `$$` between regions is also stripped. KaTeX will attempt to render `$a$` then `$b$` as two separate math spans; behavior depends on KaTeX version. Ruleset should document expected behavior for adjacent math spans. | Low | `assert _label_has_math("$a$$b$") == True` and `_label_width_text("$a$$b$") == "aba"` |
| `label="$a"` (unmatched opening) | `_label_has_math` returns `False`. Treated as plain text. The `$` literal is rendered via `_escape_xml`. | **SPEC**: correct. | — | `assert not _label_has_math("$a")` |
| `label="a$b"` (unmatched closing) | `_label_has_math` returns `False`. Treated as plain text. | **SPEC**: correct. | — | `assert not _label_has_math("a$b")` |
| `label="$ $"` (space-only math body) | `_label_has_math` returns `True` (`$ $` matches `\$[^$]+?\$`). `_label_width_text` strips `$`, strips LaTeX commands, strips braces — leaves `" "`. Width estimate = `estimate_text_width(" ", 11)` ≈ 7 px. KaTeX renders a thin math mode space. | **PROPOSED**: document that a space-only math body `$ $` is treated as math (not rejected). This is consistent with TeX semantics but may surprise authors. | Low | `assert _label_has_math("$ $") == True` |

### 2.3 Backslash and escape degenerates

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="\\"` (single backslash) | `_wrap_label_lines` processes normally. `_escape_xml` does not escape `\`. SVG output contains a literal `\` in the `<text>` element, which is valid XML. | **SPEC**: correct — `\` is not a special XML character. | — | `assert "\\" in ''.join(emit_lines_for_label("\\"))` |
| `label="\\\\"` (two backslashes) | Same as above; both backslashes pass through `_escape_xml` unchanged. | **SPEC**: correct. | — | — |

### 2.4 Control characters and unusual Unicode

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="a\x00b"` (null byte) | Null byte is **not** escaped by `_escape_xml`. It passes through to the SVG `<text>` element. `\x00` in XML is technically illegal (XML 1.0 §2.2 forbids U+0000). Browsers may silently ignore or mangle the text node. | **Critical**: `_escape_xml` must reject or strip U+0000. Embed a check: `assert '\x00' not in label_text` before emitting, or strip null bytes in the preprocessing path. | Critical | `assert '\x00' not in ''.join(emit_lines)` |
| `label="a\nb"` (newline) | Newline is not a split character in `_wrap_label_lines`. Treated as part of the token. `_escape_xml` does not escape `\n`. The `<text>` element contains a literal newline, which in SVG collapses to a space in text content but may cause rendering quirks. In `foreignObject`/KaTeX path, the newline is inside raw HTML and may be visible. | **PROPOSED**: pre-process labels by replacing `\n`, `\r`, `\t` with a space before all text operations. | Medium | `assert '\\n' not in ''.join(emit_lines)` when `label` contains `\n` |
| `label="a\tb"` (tab) | Tab character passes through. `estimate_text_width` treats `\t` as a 0.62 em character. SVG renders it as a space. Width estimate is approximately correct. No crash. | **PROPOSED**: normalize tabs to spaces (or a fixed-width token) in the preprocessing path for accurate width estimation. | Low | `assert '\\t' not in ''.join(emit_lines)` after normalization |
| `label` with RTL characters (Arabic, Hebrew) | `_char_display_width` assigns 0.62 em to RTL characters (they are not CJK Wide/Fullwidth). Width estimate is reasonable for Latin-width characters but may under-estimate for Arabic presentation forms. `_wrap_label_lines` will split at spaces between Arabic words if total length > 24 chars. KaTeX renders Arabic as plain text (not RTL-aware). | **PROPOSED**: document that RTL text is not supported for math regions; `$...$` RTL math will likely render incorrectly in KaTeX. Plain RTL text will split at spaces and render LTR within the SVG `<text>` element. | Medium | `assert isinstance(_wrap_label_lines("مرحبا"), list)` (no crash) |
| `label` with emoji (`label="a 🎉 b"`) | `estimate_text_width` handles ZWJ sequences correctly (1.0 em per cluster). Non-ZWJ emoji (e.g. `🎉` = U+1F389) are treated as 0.62 em (they are not Wide/Fullwidth in Python's `unicodedata`). This **under-estimates** emoji width; emoji render at approximately 1 em in most fonts. `_label_has_math` returns `False` for emoji-only labels. | **PROPOSED**: classify non-ZWJ emoji (Unicode category `So`, block `Emoticons`) as 1.0 em in `_char_display_width`. | Low | `assert estimate_text_width("🎉", 12) == 12` (after fix) |
| `label` with 1000+ characters | `_wrap_label_lines` returns a single line of 1000 chars (no space between chars → no split point). `pill_w` becomes `estimate_text_width("a"*1000, 11) + 12 ≈ 6846 px`. SVG is valid but the pill overflows any realistic canvas. | **PROPOSED**: `_wrap_label_lines` must respect `max_chars` for labels with no split points. Add forced-break at `max_chars` for labels with no natural break points (same as CSS `overflow-wrap: break-word`). | Medium | `assert max(len(l) for l in _wrap_label_lines("x"*100)) <= _LABEL_MAX_WIDTH_CHARS` |
| `label` with one mega-word (no spaces, 50 chars) | Same as 1000+ chars — single unsplittable token. `_wrap_label_lines` returns `["abcdefg..."]` (50 chars). | **PROPOSED**: same forced-break rule. | Medium | `assert max(len(l) for l in _wrap_label_lines("x"*50)) <= 24` |

---

## 3. Position / anchor degenerates

### 3.1 Target at viewBox edges and corners

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `dst_point=(0.0, 50.0)` (left edge) | `emit_plain_arrow_svg`: `natural_x = 0.0`. QW-3 left-clamp: `fi_x = max(fi_x, pill_w//2)` shifts text right. `pill_rx = max(0, fi_x - pill_w//2) = 0`. Pill renders against left edge. AABB registered at `x = pill_w/2`. | **SPEC**: QW-3 is specified. Documented as correct behavior. | — | `assert placed[0].x >= pill_w / 2` |
| `dst_point=(viewBox_w, 50.0)` (right edge) | No right-edge clamp. If natural_x = `viewBox_w`, pill center at `viewBox_w`, pill overflows right by `pill_w/2`. | **PROPOSED**: add right-edge clamp symmetric with QW-3. | Medium | `assert placed[0].x <= viewBox_w - pill_w / 2` |
| `dst_point=(0.0, 0.0)` (top-left corner) | Both left-clamp and (missing) top-clamp apply. Left clamp fires for x. No y-clamp. Pill may extend above y=0 (compensated by outer `translate` in `emit_svg`). | **SPEC** for x-only clamp; **PROPOSED** for y-clamp. | Medium | `assert placed[0].x >= pill_w / 2` (x); add y assertion when y-clamp added |
| `dst_point` coincident with viewBox center (e.g. `(400.0, 300.0)`) | Normal operation. Natural placement positions pill above stem. No edge cases triggered. | **SPEC**: fully covered by existing rules. | — | Covered by existing regression tests |

### 3.2 Targets outside the viewBox

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `dst_point=(-100.0, -50.0)` (negative coords) | `natural_x = -100.0`, `natural_y = -50.0 - PLAIN_ARROW_STEM/2 - 2`. QW-3 clamps `fi_x` to `pill_w//2` (positive). But `pill_rx` = `max(0, fi_x - pill_w//2) = 0`. The pill renders at `x=0` (left edge). The arrow stem still points to `(-100, -50)` which is off-canvas. | **PROPOSED**: a target outside the viewBox should either (a) silently suppress the annotation (no SVG emitted), or (b) be flagged with a warning. The current behavior silently renders a misconnected arrow (stem goes off-canvas, pill is at left edge). | Medium | `assert arrow_off_canvas_suppressed_or_warned()` |
| `dst_point=(-inf, inf)` | `OverflowError` at `int(y2)` when computing `ix2 = int(x2)`. Python's `int(float('-inf'))` raises `OverflowError`. | **PROPOSED**: add a guard `if not (math.isfinite(x) and math.isfinite(y)):` before integer conversion; raise `ValueError` or silently return. | Critical | `pytest.raises((ValueError, OverflowError), emit_plain_arrow_svg, ...)` → after fix: no exception, silent return |

### 3.3 Anchor at extreme values

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `dst_point=(1e15, 1e15)` (large but finite) | No `OverflowError` in Python — `int(1e15)` is valid. SVG output contains large integer coordinates. No NaN/inf. Pill renders far off-canvas. | **PROPOSED**: clamp coordinates to within ±`viewBox_w`×`viewBox_h` before integer conversion. | Low | `assert abs(fi_x) < 1_000_000` (after clamp) |

---

## 4. Nudge grid degenerates

### 4.1 Grid exhausted (33rd annotation)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `placed_labels` pre-filled with natural position + all 32 nudge candidates occupied | `collision_unresolved = True`. Label registered at the **natural pre-nudge position** (fallback). This may overlap existing labels (confirmed empirically: `placed[-1].overlaps(placed[-2]) == True`). Debug comment emitted iff `SCRIBA_DEBUG_LABELS=1`. | **SPEC**: QW-2 mandates the fallback to natural position. The ruleset should clarify: "when all 32 candidates are exhausted, the label is registered at its natural position regardless of collisions. The debug comment is the only signal." MW-4 (force-based solver) is the roadmap item to close this. | — | `assert collision_unresolved_flag` when all 32 slots pre-occupied; `assert placed[-1].overlaps(some_existing)` does not raise |

### 4.2 `side_hint` degenerates

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `side_hint="invalid_string"` | `hint_key = None` (line 183: coerce to None if not in `_SIDE_HINT_PREFERRED`). Behaves identically to `side_hint=None`. No warning emitted. | **SPEC**: docstring says "When side_hint is None or unknown, all 32 candidates sorted by Manhattan distance." No change needed. **PROPOSED**: add a development-mode warning (`warnings.warn`) for unknown non-None hints to catch author typos. | Low | `assert list(_nudge_candidates(40, 20, side_hint='diagonal')) == list(_nudge_candidates(40, 20))` |
| `side_hint=""` (empty string) | Same coerce to `None`. Identical behavior. | **SPEC**: correct. | — | `assert list(_nudge_candidates(40, 20, side_hint='')) == list(_nudge_candidates(40, 20))` |
| `side_hint=None` (explicit) | Normal no-preference path. All 32 in Manhattan order. | **SPEC**: correct. | — | `assert len(list(_nudge_candidates(40, 20, side_hint=None))) == 32` |

### 4.3 `side_hint` at corner with conflicting position

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `side_hint=None` but pill natural position is at a canvas corner | Nudge will try all 32 offsets; many will be off-canvas. The first on-canvas collision-free candidate wins. The left-edge x-clamp (QW-3) may move the registered position post-acceptance. See §9 of `02-algorithm-soundness.md` for the clamp-collision repro. | **SPEC**: QW-3 documents the x-clamp. I-4 violation (clamp causes post-acceptance collision) is an open bug. | — | Covered by §9 repro test |

---

## 5. Registry degenerates

### 5.1 Empty registry

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `placed_labels=[]` | First annotation places at natural position without any collision check (the `any(candidate.overlaps(p) for p in [])` is `False`). Normal operation. | **SPEC**: correct. | — | `assert placed_labels == [placed[0]]` after first emit |

### 5.2 `placed_labels=None`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `emit_plain_arrow_svg(..., placed_labels=None)` | Collision-avoidance block is skipped (`if placed_labels is not None:` guard). Pill placed at natural position. No AABB registered. | **SPEC**: docstring says "When provided, the final placement is appended." `None` is explicitly supported as "no collision avoidance." | — | `assert len(output_lines) > 0` and `placed_labels is None` after call |

### 5.3 Duplicate entries in registry

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `placed_labels` contains two identical `_LabelPlacement(x=100, y=100, w=40, h=20)` entries | Both entries participate in collision detection. A new label at `(100, 100)` will detect overlap against **both** duplicates (same result since they are identical). Nudge fires. No crash. Performance is slightly degraded (duplicate comparisons). | **SPEC**: registry is append-only; no deduplication is promised. The current behavior is correct but the ruleset should note: "the registry does not deduplicate; callers are responsible for not inserting the same placement twice." | — | `assert sum(1 for p in placed_labels if p.x == 100.0) == 1` (if dedup added) |

### 5.4 `placed_labels` with `NaN` entries

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `placed_labels = [_LabelPlacement(x=nan, y=nan, width=40, height=20)]` | `nan_p.overlaps(any_p)` always returns `True` (IEEE 754: all comparisons with `NaN` are `False`; `not (False or False or ...) = True`). All 32 nudge candidates "overlap" the NaN entry. `collision_unresolved = True`. Label registered at natural position. No exception. Debug comment emitted iff `SCRIBA_DEBUG_LABELS=1`. | **Critical**: a single NaN entry poisons the registry — every subsequent label will report collision-unresolved and fall back to its natural position, causing all labels to be placed without collision avoidance. The ruleset must forbid NaN entries. Add assertion: `assert all(math.isfinite(p.x) and math.isfinite(p.y) for p in placed_labels)` at registry append. | Critical | `with pytest.raises(AssertionError): placed_labels.append(_LabelPlacement(x=nan, ...))` (after guard) |

### 5.5 Registry from previous frame not cleared

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Same `placed_labels` list reused across two frames | The second frame's collision avoidance treats first-frame placements as already-occupied. Labels from frame 2 may be displaced by ghost collisions with frame 1. No crash. | **SPEC**: I-10 mandates "Registry is not shared across primitive instances, steps, or frames." `base.py` creates a fresh list per `emit_annotation_arrows` call, so this can only occur via direct `emit_*` calls with a long-lived `placed_labels` argument. Ruleset should add: "callers using the emit functions directly MUST create a fresh `placed_labels = []` for each frame." | — | `assert id(placed_frame1) != id(placed_frame2)` in base.py's emit_annotation_arrows |

### 5.6 Two AABBs with identical centers

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_LabelPlacement(100,100,40,20).overlaps(_LabelPlacement(100,100,40,20))` | Returns `True` — they overlap. Nudge fires for the second annotation. | **SPEC**: correct. Identical-center pills should report overlap. | — | `assert _LabelPlacement(100,100,40,20).overlaps(_LabelPlacement(100,100,40,20))` |

---

## 6. Interaction degenerates

### 6.1 Self-loop leader (`arrow_from == target`)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `emit_arrow_svg(src_point=(100,50), dst_point=(100,50), ...)` | `dx = dy = 0`. `dist = sqrt(0) → guarded to 1.0`. Shortening: `x1 += 0/1 * shorten_src = x1`, `x2 -= 0/1 * shorten_dst = x2` — no movement. `h_dist = 0`. `base_offset = max(cell_h*0.5, sqrt(0)*2.5) = cell_h*0.5`. Bezier control points use `mid_x_f = x1` (same), `h_span = 0 < 4`, triggering the near-vertical h_nudge branch. **Arrow polygon direction vector**: `adx = ix2 - cx2 = 100 - (100 - h_nudge) = h_nudge`. After `int()` this is non-zero. Arrow polygon does not degenerate. **BUT**: the path `M{x1},{y1} C{cx1},{cy1} {cx2},{cy2} {x2},{y2}` has identical start and end, producing a loop-like curve. **NaN** appears in the SVG because `arrow_points` calculation uses `adx/ad` which involves `cx2` derived from `h_nudge` — if `h_nudge` is large, the direction vector may be abnormal. Empirically: `NaN` found in SVG output. | **Critical** (bug-B): self-loop is a known bug. Ruleset should state: "when `arrow_from == target`, `emit_arrow_svg` MUST be suppressed. `base.py` is responsible for detecting this before calling `emit_arrow_svg`." | Critical | `assert 'nan' not in ''.join(emit_arrow_svg_lines).lower()` when src == dst |

### 6.2 Leader length < 1 px

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `src=(100.0, 100.0)`, `dst=(100.1, 100.0)` (0.1 px apart) | `dist = 0.1`. Shorten guards (`if shorten_src > 0 and dist > 0`) use `dist` which is positive. After recompute: `dx = 0.1`, `dy = 0`. `dist = 0.1`. `h_dist = 0.1`. `base_offset = cell_h * 0.5`. Bezier with ~0 horizontal span uses h_nudge branch. Arrow polygon direction: `adx = ix2 - cx2`. Due to `int()` rounding, `ix2 - cx2` may be zero → `ad = 0 → guarded to 1.0`. Arrow polygon degenerates to a point but no NaN. **NaN and Inf** found in SVG output in empirical test with `(100.0, 100.0) → (100.1, 100.0)`. | **High**: short leaders (< 1 px after rounding) produce degenerate or NaN polygon. Add guard: `if dist < 1.0: suppress arrow or render a dot`. | High | `assert 'nan' not in ''.join(lines).lower() and 'inf' not in ''.join(lines).lower()` |

### 6.3 Leader length > viewBox diagonal

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `src=(0,0)`, `dst=(1000, 800)` (1280 px diagonal) | `base_offset = min(cell_h*1.2, sqrt(1800)*2.5) = min(48, 106) = 48`. Large `h_dist` saturates at `cell_h*1.2`. **NaN in SVG** found empirically — the `ad` direction vector from `cx2 → ix2` may produce zero magnitude for extreme control point geometry. | **High**: verify no NaN in SVG for any valid `src/dst` pair within a 4096×4096 canvas. Add a post-calculation guard: `if not math.isfinite(p1x) or ...` before emitting polygon. | High | `assert 'nan' not in ''.join(lines).lower()` for (0,0)→(1000,800) |

### 6.4 Two annotations on same target, same label

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Two `emit_plain_arrow_svg` calls with identical `target`, `label`, `dst_point` | First annotation: placed at natural position. Second annotation: natural position **same** as first, which is now in `placed_labels`. Nudge fires. Second label nudged to an adjacent slot. Both emitted with distinct `data-annotation` keys (`{target}-plain-arrow` — **same key for both**). SVG has duplicate `data-annotation` attributes. | **PROPOSED**: emit should generate a unique key per call (e.g. append a counter). Duplicate `data-annotation` values violate the implicit uniqueness assumption for JS tooling that queries them. | Low | `assert len(set(re.findall(r'data-annotation="([^"]+)"', svg))) == n_annotations` |

### 6.5 `arrow_from = target` zero-length with shorten values overrunning distance

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `shorten_src=10, shorten_dst=10`, `dist=14.1` (both shortenings sum > dist) | After shortening: `x1 = src + (dx/dist)*10`, `x2 = dst - (dx/dist)*10`. Since `2*10 > 14.1`, the endpoints **cross** (src moves past dst). The recomputed `dx`, `dy`, `dist` reflect this crossing. Bezier control points are computed from crossed endpoints, producing a backward-curving path. **NaN and Inf** found in SVG output. | **High**: add guard: `if shorten_src + shorten_dst >= dist: suppress arrow (or clamp shorten to dist/2 each)`. | High | `assert 'nan' not in ''.join(lines).lower()` when shorten_src + shorten_dst >= dist |

### 6.6 Excessive `arrow_index`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `arrow_index=100` | `total_offset = base_offset + 100 * cell_h * 0.3 = base_offset + 30 * cell_h`. For `cell_h=40`, offset = `1200 px`. The curve apex is 1200 px above the source. **NaN in SVG** confirmed empirically for large offsets. Control point y becomes very negative, which combined with `int()` overflow or Bezier direction computation may introduce NaN. | **High**: add guard `total_offset = min(total_offset, some_cap)` (e.g. `4 * cell_h` or `viewBox_h`). | High | `assert 'nan' not in ''.join(lines).lower()` when arrow_index=100 |

---

## 7. Math / KaTeX degenerates

### 7.1 Math label longer than viewBox

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="$" + "a+b+" * 24 + "$"` (~100 chars of math) | `_label_has_math` returns `True`. No wrapping (IR-2: math labels are never wrapped). `_label_width_text` estimates width ≈ 789 px. `pill_w ≈ 801 px`. Pill overflows any standard canvas. Only the left-edge x-clamp fires; right-edge overflow unhandled. | **PROPOSED**: for math labels, add a maximum `pill_w` cap (e.g. `viewBox_w * 0.9`). Or document explicitly that extremely wide math pills are out of scope (author responsibility). | Medium | `assert pill_w <= viewBox_w` (after cap) |

### 7.2 `\displaystyle` in narrow pill

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="$\displaystyle \frac{a}{b}$"` | `_label_width_text` strips `\displaystyle` and `\frac`, leaving `" ab "` (spaces + letters). Width estimate ≈ 27 px. Actual KaTeX rendering of `\displaystyle\frac{a}{b}` is taller (~40 px) and wider than estimated. Pill height = `l_font_px + 2 + PILL_PAD_Y*2 ≈ 19 px` — too short for the rendered fraction. | **High**: `\displaystyle` increases rendered height significantly. The `pill_h` formula does not account for it. A `\displaystyle` math label will be clipped by the pill rect. Add a `\displaystyle` detector: if present, multiply `pill_h` by at least 1.5. | High | `assert pill_h >= 30` when `"\displaystyle"` detected in math label |

### 7.3 Nested fractions (deep nesting)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="$\frac{\frac{\frac{...}{...}}{...}}{...}$"` (10 levels deep) | `_label_width_text` strips all `\frac` tokens and braces. Remaining content is only the leaf chars (`x` and `1` × 10). Width estimate ≈ small value. Actual KaTeX rendering of 10-level nested fractions is very tall (exponential height). Pill height = `l_font_px + 2 + 6 ≈ 19 px` — massively insufficient. | **High**: nested fractions overflow the pill rect. The 32 px math headroom expansion (I-9) applies to the outer translate, not the pill height itself. A pill_h formula aware of nesting depth is needed, or `\displaystyle`/deep-fraction detection should add extra height. | High | `assert pill_h >= 60` for 3+ level nesting (heuristic) |

### 7.4 `\text{}` inside math

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="$\text{hello}$"` | `_label_width_text`: strips `$`, strips `\text` (LaTeX command token), strips `{}`, leaves `"hello"`. Appends 15% → `"helloh"`. Width estimate ≈ 45 px. KaTeX renders `\text{hello}` in upright text mode at approximately the same width as the estimate. Reasonably accurate. | **SPEC**: `_label_width_text` handles this correctly within the 1.15× approximation margin. Ruleset should document: "`\text{}` content is measured after stripping the command token; the remaining content chars contribute to width." | — | `assert _label_width_text("$\\text{hello}$") == "helloh"` |

### 7.5 KaTeX render failure (invalid TeX)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `render_inline_tex` raises an exception for the label | `_emit_label_single_line` catches any `Exception` from `render_inline_tex` and falls back to plain SVG `<text>` with `_escape_xml`. The raw TeX source is rendered as plain text. | **SPEC**: correct. The try/except is already in place. Ruleset should document: "KaTeX render failure silently falls back to plain text; no warning is emitted." **PROPOSED**: add a warning (via `warnings.warn`) so authors know their TeX failed to parse. | Low | `assert "<text" in result` when `render_inline_tex` raises |

### 7.6 KaTeX render returns empty string or `None`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `render_inline_tex` returns `""` or `None` | `if html:` check at line 271 treats empty string and `None` as falsy. Falls back to plain SVG `<text>`. | **SPEC**: correct — the `if html:` guard handles this. Ruleset should note: "a renderer returning falsy triggers the same plain-text fallback as a renderer that raises." | — | `assert "<text" in result` when `render_inline_tex` returns `""` |

### 7.7 Pure-command math label (all chars stripped)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="$\,\!$"` (spacing commands only, no content chars) | `_label_width_text`: after stripping `$`, stripping `\,` and `\!`, stripping braces — remains `""` (empty). `extra_len = max(1, int(0 * 0.15)) = 1`. `result = "" + ""[:1] = ""`. `estimate_text_width("", 11) = 0`. `pill_w = 0 + 12 = 12 px`. Pill is 12 px wide, smaller than any text. KaTeX renders invisible spacing; pill is visually correct (tiny dot). | **PROPOSED**: minimum `pill_w` should be `2 * PILL_PAD_X = 12 px`, which is exactly what happens here. Document this floor explicitly in the spec. | Low | `assert pill_w >= 2 * _LABEL_PILL_PAD_X` |

---

## 8. Primitive-level degenerates

### 8.1 Primitive with `n=0` cells

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `ArrayPrimitive('arr', {'size': 0})` | Raises `AnimationError([E1400])` at construction: "Array requires 'size' or 'n' parameter" — actually the error is triggered when size ≤ 0. Cannot instantiate. | **SPEC**: error E1400 is correct. Cannot produce a 0-cell annotation target. | — | `pytest.raises(AnimationError, ArrayPrimitive, 'arr', {'size': 0})` |

### 8.2 Primitive larger than viewBox

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Very large array (n=1000 cells) or `viewBox_w` smaller than primitive rendering width | No validation; SVG is emitted with coordinates exceeding the declared viewBox. Browser clips at viewBox boundary. | **PROPOSED**: document that primitive dimensions are not validated against viewBox size. This is out of scope for the smart-label system (it's a primitive layout concern). | Low | Integration test only |

### 8.3 100 annotations on one cell

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| 100 `emit_plain_arrow_svg` calls all with `dst_point=(200.0, 200.0)` and distinct labels | 0.005 s (fast). After the 32nd annotation, all remaining annotations have `collision_unresolved=True` and fall back to the natural position. Empirically: 4753 overlapping pairs out of 4950 (96% collision rate). SVG contains many overlapping pills. | **SPEC**: QW-2 fallback is specified. No limit on annotations per cell is specified. **PROPOSED**: document the 32-candidate limit; after exhaustion, additional labels are unresolvable and overlap is expected. MW-4 (force-based solver) is the roadmap path. | Medium | `assert len(placed) == 100` (no crash); `assert overlapping_pairs > 0` (expected) |

### 8.4 Annotation on unknown selector

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `ann = {'target': 'arr.cell[999]', 'label': 'x', 'arrow': True}` on a 3-cell array | `resolve_annotation_point` returns `None`. `base.py` `emit_annotation_arrows` skips the annotation silently (`if dst_point is not None:` guard). **No warning emitted**. Label is dropped from SVG. | **Proposed**: a silent drop is surprising. Either emit `warnings.warn(f"[E1115] annotation target '{target}' not found, skipping")`, or raise `AnimationError`. E1115 already covers `set_state` invalid selectors; extend it to cover annotation targets. | Medium | `with pytest.warns(UserWarning, match='E1115')` when annotation target not found |

### 8.5 Annotation on target with `resolve_annotation_point` returning `None` (Plane2D bug-E)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `Plane2D` or other primitive that does not override `resolve_annotation_point` | `PrimitiveBase.resolve_annotation_point` returns `None` for all selectors. All annotations silently dropped. Bug-E from `smart-label-ruleset.md §5`. | **PROPOSED**: any primitive that supports `\annotate` must override `resolve_annotation_point`. Add an abstract method or a default that emits a loud warning. | High | `pytest.warns(UserWarning, match='resolve_annotation_point not implemented')` |

---

## 9. Frame / animation degenerates

### 9.1 Frame with zero annotations

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `emit_annotation_arrows(parts, [])` | Returns immediately. `arrow_height_above([], resolver)` returns 0. No translate added. | **SPEC**: correct. | — | `assert arrow_height_above([], lambda x: None) == 0` |

### 9.2 Frame with 500 annotations

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| 500 `emit_plain_arrow_svg` calls with distinct `dst_point` positions | 0.141 s empirically (500 × O(placed_labels) = O(n²) overlap checks). At n=500, the collision check is O(500²/2 ≈ 125,000) comparisons. Acceptable at 500. | **PROPOSED**: document the O(n²) complexity of the collision-avoidance loop. Recommend keeping annotation count per frame ≤ 50 for interactive renders. Add a developer warning when `len(placed_labels) > 100`. | Low | `assert elapsed < 1.0` for 500 annotations |

### 9.3 `arrow_height_above` returns non-zero headroom even when all resolvers return `None`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `arrow_height_above([{'arrow_from':'a','target':'b','label':'x'}], lambda x: None)` | Returns `24` (plain-text headroom) even though no arrow geometry was computed (`max_height = 0`). The `has_label` check fires before verifying that any arrow had valid coordinates. | **Medium**: this is a bug. `has_label` headroom should only be added when at least one arrow had non-None src and dst. Consequence: a frame with unresolvable arrow annotations still gets an unnecessary 24–32 px top translate. | Medium | `assert arrow_height_above([{'arrow_from':'a','target':'b','label':'x'}], lambda x: None) == 0` (after fix) |

### 9.4 `position_label_height_below` ignores math labels (I-9 partial gap)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `position_label_height_below([{'label': '$\\frac{a}{b}$', 'position': 'below'}])` | Returns `7` (plain pill height, same as non-math). Does not apply the 32 px math headroom expansion. `position_label_height_above` with the same label returns `79` (includes 32 px extra). Asymmetry confirmed empirically. | **High**: I-9 gap. `position_label_height_below` must mirror the math-headroom branch in `position_label_height_above`. | High | `assert position_label_height_below([{'label':'$x$','position':'below'}]) > position_label_height_below([{'label':'x','position':'below'}])` |

### 9.5 Ephemeral vs. persistent label mixing

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Annotations from step N persist into step N+1's `placed_labels` via incorrect caller code | `placed_labels` is a local variable inside `emit_annotation_arrows` (fresh per call). If a caller constructs it externally and reuses it, stale placements affect step N+1. | **SPEC**: I-10 forbids cross-frame sharing. Documented. This is caller error, not a system bug. | — | `assert len(placed_at_frame_start) == 0` (invariant at frame start) |

### 9.6 Re-annotate a cell after reaching the pill-count limit

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Adding annotation N+1 to a cell that already has 32 in the current frame | Same as 4.1 and 8.3 above: annotation falls back to natural position (possibly overlapping). | **SPEC**: QW-2 fallback. No per-cell limit is enforced. | — | Covered by §8.3 test |

---

## 10. Additional cross-cutting degenerates not in the original categories

### 10.1 I-4 Clamp-collision bug (already in `02-algorithm-soundness.md §9`)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Second label natural position near left edge (`x < pill_w/2`); nudge moves to negative x; post-clamp lands on first label | Confirmed repro: `placed2[0].overlaps(placed2[1]) == True` after two labels near x=0. | **High** (I-4 violation): fix is to run collision check against clamped position in nudge loop: `clamped_x_test = max(final_x + ndx, pill_w/2)`. | High | `assert not placed[-2].overlaps(placed[-1])` for near-left-edge annotations |

### 10.2 `data-annotation` key collisions

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Two `emit_plain_arrow_svg` calls with `target='x'` | Both emit `data-annotation="x-plain-arrow"`. The SVG has two elements with the same `data-annotation` value. | **PROPOSED**: append a per-frame counter or UUID suffix to ensure uniqueness: `data-annotation="{target}-plain-arrow-{index}"`. | Low | `assert len(set(re.findall(r'data-annotation="([^"]+)"', svg))) == n` |

### 10.3 I-2 zero-gap collision check (spec vs. implementation)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Two pills touching edge-to-edge (gap = 0 px) | `_LabelPlacement.overlaps` uses strict `<`/`>` comparisons, no pad. Zero-gap pills are registered as non-overlapping. They will render touching but not overlapping. | **PROPOSED** (from `01-invariant-gaps.md`): either (a) add `pad=2` to `overlaps()` to match the spec's "≥ 2 px AABB separation", or (b) remove the "≥ 2 px" claim from the ruleset. | Low | If option (a): `assert not _LabelPlacement(0,0,20,20).overlaps(_LabelPlacement(22,0,20,20))` should be `True` (2 px gap with pad=2) |

### 10.4 `estimate_text_width` with zero font size

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `estimate_text_width("hello", 0)` | Returns `0` (all character widths are `0.62 * 0 = 0`). `pill_w = 0 + 12 = 12 px`. | **PROPOSED**: same as §1.9 — `l_font_px = 0` should be rejected upstream. | Medium | Covered by §1.9 |

### 10.5 XML injection via `target` or `label`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label='<script>alert(1)</script>'` | `_escape_xml` converts `<` to `&lt;` and `>` to `&gt;`. The `<text>` element contains the escaped string. No XSS risk in SVG. | **SPEC**: correct. `_escape_xml` is called on all label text in the plain-text path. The `foreignObject`/KaTeX path uses `html` directly from `render_inline_tex`; that renderer is responsible for its own escaping. | — | `assert '<script>' not in ''.join(emit_lines)` |
| `target='x" onload="evil()'` | `_escape_xml` used on `ann_key = f"{target}-plain-arrow"` in `data-annotation` attribute. The `"` is escaped to `&quot;`. No attribute injection. | **SPEC**: correct. | — | `assert 'onload' not in ''.join(emit_lines)` |

### 10.6 Null byte in label SVG output (security)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label="a\x00b"` | `\x00` passes through `_escape_xml` unchanged. SVG `<text>` element contains U+0000. XML 1.0 §2.2 forbids U+0000. | **Critical**: strip or reject U+0000 (and other XML-illegal code points: U+0001–U+0008, U+000B, U+000C, U+000E–U+001F, U+FFFE, U+FFFF) in `_escape_xml` or in a pre-processing step. | Critical | `assert '\x00' not in ''.join(emit_lines)` |

---

## Summary table by severity

### Critical

| # | Case | Root cause |
|---|------|-----------|
| 1.3 | `pill_h = NaN` → NaN candidates, NaN AABB poisons registry | Missing `isfinite` guard in `_nudge_candidates` |
| 1.4 | `pill_h = Infinity` → `OverflowError` on integer conversion | Missing `isfinite` guard in `_nudge_candidates` |
| 5.4 | NaN entry in `placed_labels` → all subsequent labels collision-unresolved | No NaN guard at registry append |
| 6.1 | Self-loop (`arrow_from == target`) → NaN in SVG | Bug-B; no self-loop guard in `base.py` |
| 10.6 | Null byte in label → invalid XML (U+0000) | `_escape_xml` does not strip XML-illegal chars |
| 3.2 | Infinite `dst_point` → `OverflowError` | Missing `isfinite` guard before `int()` conversion |

### High

| # | Case | Root cause |
|---|------|-----------|
| 6.2 | Leader < 1 px → NaN/Inf in SVG polygon | No `dist < 1.0` guard |
| 6.3 | Leader > viewBox diagonal → NaN in SVG | Bezier direction vector degenerates for large offsets |
| 6.5 | `shorten_src + shorten_dst >= dist` → endpoints cross → NaN | No shorten-overflow guard |
| 6.6 | `arrow_index = 100` → extreme curve offset → NaN | No `total_offset` cap |
| 7.2 | `\displaystyle` → pill_h too short, text clipped | `pill_h` formula ignores display-math height |
| 7.3 | Deep nested fractions → pill_h massively under-estimated | Same as 7.2 |
| 9.4 | `position_label_height_below` ignores math labels | I-9 partial gap; below helper lacks math branch |
| 8.5 | Primitive with no `resolve_annotation_point` override silently drops all annotations | No abstract method / loud warning |
| 10.1 | Clamp-collision bug (near-left-edge) → I-4 violation | `collision_check` uses pre-clamp coordinates |
| 1.9 | `l_font_px < 0` → inverted AABB | No assertion on font size range |

### Medium

| # | Case | Root cause |
|---|------|-----------|
| 1.1 | `pill_h = 0` → 32 zero-displacement candidates | Missing guard in `_nudge_candidates` |
| 1.2 | `pill_h < 0` → inverted step signs | Missing guard in `_nudge_candidates` |
| 1.7 | `pill_w > viewBox_w` → right-edge overflow | Right-edge clamp absent (§2.3 known gap) |
| 1.8 | `pill_h > viewBox_h` → vertical overflow | y-axis clamp absent (§2.3 known gap) |
| 2.4 | Long label, no split points → pill_w > viewBox | `_wrap_label_lines` no forced-break fallback |
| 2.4 | Null byte passes through `_escape_xml` | Redundant with Critical 10.6 |
| 3.2 | Target outside viewBox → misconnected arrow silently emitted | No off-canvas target guard |
| 7.1 | Very long math label → pill overflows canvas | No `pill_w` cap for math |
| 8.3 | 100 annotations on one cell → 96% overlap rate | QW-2 fallback is specified; user-education gap |
| 8.4 | Unknown annotation target silently dropped | No warning at `dst_point is None` |
| 9.3 | `arrow_height_above` adds headroom even when all resolvers return `None` | `has_label` check precedes geometry validation |

### Low

| # | Case | Root cause |
|---|------|-----------|
| 2.1 | Whitespace-only label treated as non-empty | No `strip()` before truthiness check |
| 2.2 | Space-only math body `$ $` treated as math | Intentional; needs documentation |
| 2.4 | Emoji width underestimated | `_char_display_width` classifies emoji as 0.62 em |
| 2.4 | Tab/newline in label not normalized | No pre-processing step |
| 4.2 | Unknown `side_hint` silently coerced to `None` (no warn) | Typo-tolerance vs. diagnosability trade-off |
| 7.5 | KaTeX failure produces no warning | Silent fallback; add `warnings.warn` |
| 9.2 | O(n²) collision check; 500 annotations ≈ 0.14 s | Acceptable now; document the complexity |
| 10.2 | Duplicate `data-annotation` keys | No per-call counter |
| 10.3 | I-2 zero-gap vs. "≥ 2 px" spec inconsistency | Spec vs. code mismatch (choose one) |

---

## 11. Annotation dict structural degenerates

These test what happens when the annotation dictionary itself is missing expected keys or contains unexpected types.

### 11.1 Missing `target` key

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `ann = {'label': 'test', 'color': 'info'}` (no `target`) | `ann.get("target", "")` returns `""`. `ann_key = "-plain-arrow"`. `data-annotation="-plain-arrow"` is emitted. Arrow points at `dst_point` correctly. The annotation is ambiguous — multiple annotations with no `target` all get the same key. | **PROPOSED**: warn when `target` is empty string after `get`. The empty key causes collisions in `data-annotation`. | Low | `assert '-plain-arrow' not in ''.join(lines)` (after fix to require target) |

### 11.2 Missing `color` key

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `ann = {'target': 'x', 'label': 'test'}` (no `color`) | `ann.get("color", "info")` returns `"info"`. Info style applied. SVG uses `#506882` stroke. | **SPEC**: correct. `"info"` is the documented default. | — | `assert "#506882" in ''.join(lines)` |

### 11.3 Unknown `color` value

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `ann = {'target': 'x', 'label': 'test', 'color': 'INVALID_COLOR'}` | `ARROW_STYLES.get("INVALID_COLOR", ARROW_STYLES["info"])` returns info style. Fallback is silent. | **SPEC**: documented fallback to `"info"`. No warning emitted. **PROPOSED**: add development-mode warning for unknown color keys. | Low | `assert "#506882" in ''.join(lines)` for unknown color |

### 11.4 `side` vs `position` key for side hint (both accepted)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Annotation has `'side': 'above'` | `anchor_side = ann.get("side") or ann.get("position") or None` → `"above"`. Half-plane preference applies. | **SPEC**: both `side` and `position` are accepted as side-hint sources. Empirically verified: `side=above` and `position=above` produce identical placements. | — | `assert placed_side[0].y == placed_position[0].y` |
| Annotation has both `'side': 'above'` and `'position': 'below'` | `side` takes precedence due to `ann.get("side") or ...` short-circuit. `position=below` is ignored for the hint. | **PROPOSED**: document the priority explicitly: `side` overrides `position` for hint resolution. | Low | `assert placed[0].y < anchor_y` when both keys conflict |

### 11.5 `_debug_capture` stale `final_y` after nudge

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Nudge fires; `_debug_capture["final_y"]` read after call | `_debug_capture["final_y"]` stores the **initial** `final_y` (before nudge). The post-nudge render `final_y = placed[-1].y + l_font_px * 0.3`. The two values differ by `|ndy|`. Empirically: `debug["final_y"] = 70.5`, `actual = 38.7 + 11*0.3 = 42.0`. | **PROPOSED**: document in `_debug_capture` interface: "When nudge fires, `final_y` reflects the initial candidate, not the post-nudge position. Use `placed[-1].y + l_font_px * 0.3` to recover the actual render y after nudge." Tests using `_debug_capture` for I-3 invariant must not use the captured `final_y` when a collision was pre-populated. | Low | `assert dbg["final_y"] != placed[-1].y + l_font_px * 0.3` when nudge fires |

---

## 12. `_wrap_label_lines` edge cases

### 12.1 Token boundary behavior with split characters

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label` splits at space, comma, `+`, `=` but NOT at `-`, `/`, `*`, `\|`, tab | A tab character (`\t`) at position 5 in a 30-char label does not trigger a split. The label wraps at the next space. A label with only tabs and no spaces never wraps. | **PROPOSED**: add `\t` to the split-character set in `_wrap_label_lines`, or normalize tabs to spaces in a preprocessing step. | Low | `assert len(_wrap_label_lines("x"*12 + "\t" + "x"*12)) == 1` (currently; would be 2 after fix) |
| `label` with only `+` separators, no spaces | Wraps correctly at `+` when total > 24 chars. E.g. `"a+b+c+...+p"` wraps to two lines. | **SPEC**: correct. | — | `assert len(_wrap_label_lines("a+b+c+d+e+f+g+h+i+j+k+l+m+n+o+p")) == 2` |
| `label` with math region containing `+` | `in_math` guard prevents split at `+` inside `$...$`. E.g. `"$a+b+c+d+e+f+g$ = result value here at end"` splits at `=` and space, not inside `$...$`. | **SPEC**: correct. Invariant I-8 (extended). | — | `assert _wrap_label_lines("$a+b+c+d+e$=result value here at end")[0].startswith("$a+b+")` |

### 12.2 Label exactly at the character limit boundary

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `label` with exactly 24 characters (`_LABEL_MAX_WIDTH_CHARS`) | `len(text) <= max_chars` returns `True`. No wrapping. Returns `[text]`. | **SPEC**: correct. The ≤ comparison includes the limit. | — | `assert _wrap_label_lines("x" * 24) == ["x" * 24]` |
| `label` with exactly 25 characters, no split chars | `len(text) > max_chars` triggers wrapping path. No split chars found. Result: `[text]` (original string, un-split). | **PROPOSED**: document: "when no split characters exist and text exceeds `max_chars`, the entire label is returned as a single unsplit line." This is the mega-word case from §2.4. | Low | `assert _wrap_label_lines("x"*25) == ["x"*25]` |

### 12.3 `_wrap_label_lines` returns `[text]` as fallback

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Edge case where `lines` list ends up empty | The final `return lines if lines else [text]` guard ensures the caller always receives a non-empty list. Cannot produce `[]`. | **SPEC**: correct. No change needed. | — | `assert len(_wrap_label_lines("")) >= 1` |

### 12.4 `_wrap_label_lines` called with `max_chars=0`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_wrap_label_lines("hello", max_chars=0)` | `len("hello") <= 0` is `False`, enters wrapping path. Every character creates a new token boundary if it is a split char; for non-split chars all are accumulated. For `"hello"` (no split chars) returns `["hello"]`. | **PROPOSED**: `max_chars=0` should probably raise `ValueError` since a 0-char-wide column makes no geometric sense. Currently silently returns the original. | Low | `pytest.raises(ValueError, _wrap_label_lines, "hello", 0)` (after fix) |

---

## 13. `_LabelPlacement.overlaps` edge cases

### 13.1 Zero-area AABB (zero width or height)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_LabelPlacement(x=100, y=100, width=0, height=20).overlaps(_LabelPlacement(x=100, y=100, width=40, height=20))` | `self.x + 0/2 = 100 < other.x - 40/2 = 80` → `False`. `self.x - 0/2 = 100 > other.x + 40/2 = 120` → `False`. y comparisons: `100 + 10 = 110 < 100 - 10 = 90` → `False`. `100 - 10 = 90 > 100 + 10 = 110` → `False`. Result: `not (False or False or False or False) = True`. Zero-width pill at same center as normal pill reports overlap. | **SPEC**: correct. A zero-area point at the center of a pill is contained within it and should report overlap. | — | `assert _LabelPlacement(100,100,0,20).overlaps(_LabelPlacement(100,100,40,20)) == True` |
| `_LabelPlacement(x=100, y=100, width=0, height=0).overlaps(_LabelPlacement(x=200, y=200, width=0, height=0))` | `self.x + 0 = 100 < other.x - 0 = 200` → `True`. Returns `not True = False`. No overlap for points at different positions. | **SPEC**: correct. Two zero-area points at different positions do not overlap. | — | `assert not _LabelPlacement(100,100,0,0).overlaps(_LabelPlacement(200,200,0,0))` |

### 13.2 Negative-dimension AABB

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `_LabelPlacement(x=100, y=100, width=-40, height=20)` | The AABB center is stored at `(100, 100)` with a negative width. `self.x + (-40)/2 = 80`, `self.x - (-40)/2 = 120`. The effective "bounding interval" is `[80, 120]` — identical to a `width=40` pill at the same center. Overlap test behaves identically to a positive-width pill. | **PROPOSED**: `_LabelPlacement` dataclass should validate `width >= 0` and `height >= 0` at construction (e.g. via `__post_init__`). Negative dimensions only arise from external patching or future bugs. | Low | `pytest.raises(ValueError, _LabelPlacement, 100, 100, -40, 20)` (after validation) |

### 13.3 `overlaps` with I-2 zero-gap spec mismatch

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Two pills touching at `x=80` and `x=120` respectively (gap = 0): `_LabelPlacement(80, 100, 40, 20)` and `_LabelPlacement(120, 100, 40, 20)` | `self.x + 40/2 = 100 < other.x - 40/2 = 100` → `False` (strict `<`). Returns `not False = True`... wait: actually `100 < 100 = False`, but `100 > 100 = False`; the full expression: `not (False or False or ...)` = True → they DO overlap at exactly touching edges. | Actually: these two pills at x=80 and x=120 with width=40 each. `self.x+w/2 = 100`, `other.x-w/2 = 100`. `100 < 100 = False`. So these DO overlap (touching = overlapping per strict `<`). The 2 px gap rule from spec would make these non-overlapping at 0 px gap. | Low | `assert _LabelPlacement(80,100,40,20).overlaps(_LabelPlacement(120,100,40,20)) == True` (current); per spec with 2px pad: should be `True` at 0 gap, `False` at 2+ gap |

---

## 14. `emit_arrow_svg` layout mode degenerates

### 14.1 Unknown `layout` string

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `layout='unknown'` (not `"horizontal"` or `"2d"`) | Falls through to the horizontal `else` branch (default). SVG emitted correctly. NaN only appears if control-point math produces it (not for this specific case). For `(0,100)→(200,100)` with `layout='unknown'`: produces same Bezier as `layout='horizontal'`. | **PROPOSED**: log a warning for unknown layout values. The silent fallback is acceptable for now but could mask author typos. | Low | `assert lines_unknown == lines_horizontal` when src/dst differ |
| `layout='invalid'` with `src==dst` | Both the 2d perpendicular branch (skipped) and the horizontal branch are tried. The horizontal branch uses `h_span=0 < 4`, triggering the h_nudge path. Arrow polygon NaN is possible. Empirically: `NaN in SVG`. | **High**: same as §6.1 (self-loop). The fix for self-loop will fix this case too. | High | `assert 'nan' not in ''.join(lines).lower()` for src==dst with any layout |

### 14.2 `layout='2d'` with horizontal src/dst (same y, different x)

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `layout='2d'`, `src=(0,100)`, `dst=(200,100)` | `dx=200, dy=0`, `dist=200`. `perp_x = -0/200 = 0`, `perp_y = 200/200 = 1`. Curve bows downward (perp direction is `(0,1)`). Control points and label reference computed correctly. No NaN. | **SPEC**: correct for 2d layout. | — | `assert 'nan' not in ''.join(lines).lower()` for 2d horizontal |

### 14.3 `layout='2d'` with purely vertical src/dst

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `layout='2d'`, `src=(100,0)`, `dst=(100,200)` | `dx=0, dy=200`, `dist=200`. `perp_x = -200/200 = -1`, `perp_y = 0/200 = 0`. Curve bows left. Control points and label computed correctly. No NaN. | **SPEC**: correct for 2d layout. | — | `assert 'nan' not in ''.join(lines).lower()` for 2d vertical |

---

## 15. `arrow_height_above` and headroom degenerates

### 15.1 All annotations have no `arrow_from` and no `arrow=True`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `arrow_height_above([{'label':'test', 'target':'x'}], resolver)` | `arrow_anns = []`, `plain_anns = []`. Returns `0`. | **SPEC**: correct. | — | `assert arrow_height_above([{'label':'test'}], lambda x:(0,0)) == 0` |

### 15.2 Mix of `arrow=True` and `arrow_from` annotations

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Both `plain_anns` and `arrow_anns` non-empty | Returns `max(max_height + headroom, plain_height)` where `plain_height = _PLAIN_ARROW_STEM + _LABEL_HEADROOM`. | **SPEC**: the `max(max_height, plain_height)` at line 1086 correctly accounts for both types. | — | `assert arrow_height_above([{...arrow_from...}, {...arrow=True...}], resolver) >= _PLAIN_ARROW_STEM` |

### 15.3 `arrow_height_above` with resolver raising an exception

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Resolver function raises `RuntimeError` | Exception propagates out of `arrow_height_above`. Call site receives unhandled exception. | **PROPOSED**: the resolver is user-supplied and should be documented to return `None` on failure, not raise. If it raises, the exception propagates — add a try/except in `arrow_height_above` or document the resolver contract explicitly. | Low | `assert arrow_height_above([...], lambda x: (_ for _ in ()).throw(RuntimeError())) raises RuntimeError` |

### 15.4 `position_label_height_above` with annotations lacking `label` key

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `position_label_height_above([{'position': 'above', 'target': 'x'}])` (no `label`) | `_position_only_anns` filters to annotations with `a.get("label")` truthy. Missing `label` is filtered out. Returns `0`. | **SPEC**: correct. | — | `assert position_label_height_above([{'position':'above'}]) == 0` |

---

## 16. `emit_position_label_svg` degenerates

### 16.1 Unknown `position` value

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `ann = {'label': 'test', 'position': 'diagonal'}` | Falls through to the `else` branch which defaults to `above` placement (same as `position == "above"`). No warning. | **PROPOSED**: warn on unknown `position` values. Add "diagonal" and other unknown strings to the list of edge cases documented in the ruleset. | Low | `pytest.warns(UserWarning, match='unknown position')` (after fix) |

### 16.2 `position="left"` with `anchor_x < pill_w/2 + gap`

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| `anchor_point=(10.0, 100.0)`, `position="left"`, `pill_w=60` | `final_x = 10 - 60/2 - 4 = -24`. QW-3 clamp: `fi_x = max(-24, 60//2) = 30`. `pill_rx = max(0, 30 - 30) = 0`. Pill renders against left edge. Leader is absent (no secondary leader in `emit_position_label_svg`). | **PROPOSED**: `position="left"` with a near-left anchor is a known aesthetic problem (pill renders to the right of its natural position). The ruleset should document: "for `position=left`, QW-3 left-clamp may cause the pill to overlap the anchor or render on the wrong side." | Medium | `assert placed[0].x >= pill_w / 2` (clamp always fires) |

### 16.3 `emit_position_label_svg` uses 4-direction nudge vs. 8-direction for arrow emitters

| Input | Current behavior | Correct behavior | Severity | Pytest one-liner |
|-------|-----------------|-----------------|----------|-----------------|
| Position-only label with collision | `emit_position_label_svg` uses a 4-direction single-step loop (`nudge_dirs` = up/down/left/right × 1 step × 4 outer iterations = up to 16 checks). The arrow emitters use 32-candidate 8-direction grid. | **High** (from `01-invariant-gaps.md`): the asymmetry means position-only labels have weaker collision avoidance (only 4 directions, 1 step size). They are more likely to remain in collision. The ruleset must document this asymmetry or unify the algorithms (MW-3). | High | `assert len(nudge_dirs_position_label) == 32` (after MW-3 unification) |

---

## Reference: empirical verification commands

All outputs verified with `source .venv/bin/activate && python -c "..."` in the
project root. Key commands:

```python
# §1 dimension
list(_nudge_candidates(0, 0))           # 32 × (0,0)
list(_nudge_candidates(40, float('nan')))  # 32 × (nan,nan)
list(_nudge_candidates(40, float('inf')))  # mix of nan/inf

# §2 label content
_label_has_math("$$")          # False
_label_has_math("$ $")         # True
_wrap_label_lines("x"*1000)    # single 1000-char line
_label_width_text("$\\,\\!$")  # leaves "$\\,\\!\\" (spec gap)

# §3 positions
emit_plain_arrow_svg([], {'target':'x','label':'ptr','color':'info'},
                     (float('inf'), float('inf')))  # OverflowError

# §5 registry
nan_placed = [_LabelPlacement(float('nan'), float('nan'), 40, 20)]
nan_placed[0].overlaps(_LabelPlacement(100,100,40,20))  # True (IEEE 754)

# §6 interaction
emit_arrow_svg([],{'target':'a','arrow_from':'a','label':'x','color':'info'},
               (100,50),(100,50),0,40)   # NaN in SVG
emit_arrow_svg([],{'target':'b','arrow_from':'a','label':'x','color':'info'},
               (0,0),(1000,800),0,40)    # NaN in SVG

# §9 frame
arrow_height_above([{'arrow_from':'a','target':'b','label':'x'}],
                   lambda x: None)  # returns 24 (bug: should return 0)
position_label_height_below([{'label':'$x^2$','position':'below'}])  # 7 (I-9 gap)

# §12 wrap
_wrap_label_lines("x"*25)              # returns ["x"*25] — no forced break
_wrap_label_lines("", max_chars=0)     # returns [""] — no ValueError raised today

# §16 position-only
emit_position_label_svg([], {'label':'test','position':'diagonal'}, (100,100))  # silently falls back to above
```
