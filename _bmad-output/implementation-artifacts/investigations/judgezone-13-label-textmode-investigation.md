# Investigation: JudgeZone #13 — annotation labels have no text-mode story for `_`, `\_`, or `\texttt{}`

## Hand-off Brief

1. **What happened.** (Confirmed, but not the mechanism the reporter guessed.) Three of the four stacked defects are exact, byte-for-byte confirmed: the aria/title builder mis-reads a bare `_` as a math subscript operator (#2), an escaped `\_` paints a literal backslash (#3), and `\texttt{...}` paints verbatim outside math while its aria stays garbled even inside math (#4). The fourth (#1, pill under-sizing) is real but **not** caused by the reporter's own hypothesis — there is zero subscript logic anywhere in the width ruler. The actual mechanism is a generic multi-line word-wrap bug: the painter re-adds a trailing space to every non-final wrapped line that the ruler never measured. It fires on **any** annotation label that wraps to 2+ lines, with or without an underscore in it.
2. **Where the case stands.** Concluded (root cause + fix site confirmed for all four). No source files were modified — this is investigation-only, per the read-only constraint on this task.
3. **What's needed next.** Implement the fix sketch below (§ Recommended Fix Sketch), in the stated order. Fix 1 (`_svg_helpers.py:1635-1637` + the `pill_dimensions`/`_wrap_label_lines` measurement call) is the highest-value, most broadly-applicable change — it fixes every multi-line pill, not just underscore-bearing ones. Fixes 2-4 are the "labels are a TEXT field" architectural fix the reporter asked for, scoped to `_latex_to_speech` (`_svg_helpers.py:1038`) and `strip_math_markup` (`_text_render.py:190`).

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | JudgeZone #13 (MED) + Structural Ask 4 (measure == paint == announce invariant) |
| Date opened      | 2026-07-10 |
| Status           | Concluded |
| System           | scriba @ 13eadc7 (0.34.0) |
| Evidence sources | source (`_text_metrics.py`, `_svg_helpers.py`, `_text_render.py`, `scripts/build_text_font.py`, `scriba-scene-primitives.css`), `tests/unit/test_pill_math_wrap.py`, `tests/helpers/painted_extent.py`, fontTools introspection of the shipped `Inter-subset.woff2` (hmtx + GSUB), 4 live renders of the reporter's repro + variants |

## Problem Statement

**Bug #13**, four stacked defects, all reproduced on 0.34.0 with `\annotate{a.cell[0]}{label="upper_bound = begin(): nothing ≤ 3", position=above, color="state:error"}`:

1. Width under-reserve with raw `_`: pill rect measured narrower than the painted line-1 run, padding visually collapsing. Reporter's hypothesis: an `_`→subscript interpretation somewhere in the measuring path shaves the advance.
2. aria/title mis-parse: accessible name reads `_bound` as a math subscript ("upper subscript bound") for a plain-text label.
3. `\_` (escaped) paints a literal backslash in the SVG text path instead of being unescaped to `_`.
4. `\texttt{...}` in a label is painted verbatim (raw TeX string) outside math; only works inside `$...$` via KaTeX, and even then the aria stays garbled.

**Structural Ask 4:** map the three consumers of a label string — width ruler, SVG painter, aria/title builder — for `_`, `\_`, `\texttt{}`, `$...$` segments, and Vietnamese diacritics. Identify every divergence. Assess feasibility of a property test asserting `painted tspan width + 2×padding ≤ rect width` AND `aria contains the literal string`.

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| `scriba/animation/primitives/_text_metrics.py` (full file) | Available (Confirmed) | The width ruler. No subscript/underscore-splitting logic anywhere. `measure_label_line` (line 222), `measure_text_run` (208), `ShippedFontMeasurer.measure_run` (142). |
| `scriba/animation/primitives/_svg_helpers.py` (full file) | Available (Confirmed) | Houses the painter AND the aria/title builder. `_LABEL_PILL_PAD_X=6`/`_LABEL_PILL_MAX_W_PX=132` (102, 97); `_label_has_math` (883); `_SUBSCRIPT_RE`/`_latex_to_speech` (1033-1038); `pill_dimensions` (1398); `_emit_pill_label_text` (1561); `_wrap_label_lines` (1719); `ARROW_STYLES` (1943); `emit_position_label_svg` (3525). |
| `scriba/animation/primitives/_text_render.py` (lines 137-266) | Available (Confirmed) | `_escape_xml` (137), `_INLINE_MATH_RE` (152), `strip_math_markup` (190) — the non-KaTeX paint transform. |
| `scriba/animation/static/scriba-scene-primitives.css` | Available (Confirmed) | `font-feature-settings: "tnum" 1, "lnum" 1, "zero" 1, "ss01" 1` appears at lines 402 and 455 only, scoped to `[data-primitive=array/grid/dptable]` and graph/tree node `text`. `.scriba-annotation > text` (534-539) declares no such features. |
| `scripts/build_text_font.py` (full file, 118 lines) | Available (Confirmed) | Bakes the tnum/lnum/zero/ss01 GSUB substitutions into `inter_advances.json` **unconditionally**, per-codepoint, regardless of which CSS consumer actually requests those features. |
| `tests/unit/test_pill_math_wrap.py` | Available (Confirmed) | Existing pill-sizing/wrap test suite. Contains `test_scriba_sans_pill_covers_painted_text` (217-230) — almost exactly the reporter's proposed invariant, but scoped to the single-line case only. |
| `tests/helpers/painted_extent.py` | Available (Confirmed) | The repo's closest thing to a "painted-width oracle." Docstring states explicitly: "Text is not measured; every annotation label sits inside its measured pill rect" — a deliberate exemption, not an oversight. |
| fontTools hmtx/GSUB dump of `scriba/animation/vendor/inter/Inter-subset.woff2` | Available (Confirmed) | Cross-checked `inter_advances.json` against the real shipped font. `_` (U+005F) advance is 934/2048 em — ordinary, unshaved. `tnum` lookup 0 substitutes digits **and** `parenleft/parenright/colon/comma/period/hyphen/equal/space/…` to tabular-width alternates. |
| 4 live renders (see Reproduction Plan) | Available (Confirmed) | `render.py` executed against the reporter's repro + 3 escape/texttt variants; raw HTML inspected for `<rect>`, `<tspan>`, `aria-label`. |

## Verdict Table

| # | Defect | Verdict | Evidence (file:line) | Repro measurement |
| - | ------ | ------- | --------------------- | ------------------ |
| 1 | Width under-reserve with raw `_` | **PARTIAL** — symptom confirmed, reporter's hypothesis refuted, real (different) cause found | `_svg_helpers.py:1719-1824` (`_wrap_label_lines`, rstrips before storing) + `1635-1637` (`_emit_pill_label_text`, re-adds trailing space at paint time, never re-measured) | Rendered `<rect ... width="134">`; wrapped/measured line 1 = `"upper_bound = begin():"` → 122px (`pill_w=122+12=134`, exact match); **painted** line 1 = `"upper_bound = begin(): "` (with reinjected trail) → 125px. Usable text budget = 134−12 = 122px; painted run overflows it by 3px. |
| 2 | aria/title mis-parse (subscript) | **CONFIRMED**, exact match | `_svg_helpers.py:1033` (`_SUBSCRIPT_RE`), `:1038` (`_latex_to_speech`), called at `:3672` for this repro's call site (`emit_position_label_svg`) | Rendered `aria-label="upper subscript bound = begin(): nothing ≤ 3"` — byte-for-byte match to reporter's claim. |
| 3 | `\_` paints literal backslash | **CONFIRMED**, exact match | `_text_render.py:190` (`strip_math_markup`, `if "$" not in text: return text` early-return) | Rendered tspan = `"upper\_bound = begin(): "` — literal `\` present. Rect grew 134→138 (+4px), exactly the backslash glyph's own advance (738/2048 em ≈ 4px @ 11px) — ruler and painter stay internally consistent here; this is a content/semantics bug, not an added measure≠paint gap. |
| 4 | `\texttt{}` verbatim / aria garbled | **CONFIRMED**, both sub-claims | Paint (non-math): same early-return as #3. Paint (math): `_svg_helpers.py` foreignObject/KaTeX branch, confirmed via `scriba-annot-fobj` in output. Aria (both): `_latex_to_speech`'s generic `\cmd`-strip step has no dedicated `\texttt{...}` rule. | Non-math tspan = `"\texttt{upper\_bound} = "` (raw). Math variant renders correctly visually (real `KaTeX_Typewriter` `@font-face` confirmed in `katex.min.css`). **Both** variants' aria = `"textttupper\ subscript bound = ..."` — identical garbling regardless of whether paint is correct. |

## Confirmed Findings

### Finding 1: the reporter's stated mechanism for defect #1 does not exist in code
**Evidence:** `_text_metrics.py` (full file) contains no subscript-detection or `_`-splitting logic at all. `_` (codepoint 0x5F) has advance 934/2048 em in `inter_advances.json`, independently verified against the real `hmtx` table in the shipped `Inter-subset.woff2` via fontTools — an exact match, an ordinary (unshaved) glyph width. The only subscript-aware regex in the entire label pipeline, `_SUBSCRIPT_RE` (`_svg_helpers.py:1033`), lives inside `_latex_to_speech` — the aria builder — and is never called from the measure or paint path.
**Detail:** This directly refutes the reporter's hypothesis. It does not refute the reporter's *observed symptom* (an under-sized pill) — see Finding 2.

### Finding 2: the real cause of defect #1 is a generic wrap/trail divergence, unrelated to `_`
**Evidence:** `_wrap_label_lines` (`_svg_helpers.py:1719-1824`) calls `.rstrip()` on every wrapped line before it is returned (lines 1806, 1811, 1818, 1823) — these rstripped lines are exactly what `pill_dimensions` (1398-1449) measures via `measure_label_line(ln, l_font_px, text_face="scriba-sans")` (1440-1443) to compute `pill_w`. But `_emit_pill_label_text` (1561-1645), the painter, re-adds a literal space to every *non-final* line at emission time: `trail = "" if li == num_lines - 1 else " "` (1636-1637) — a space the measurer never saw.
**Detail:** Direct invocation confirms the exact mechanism on the repro string: `measure_label_line("upper_bound = begin():", 11, text_face="scriba-sans")` → 122 (matches `pill_w=134` exactly, since 122+2×6=134). `measure_label_line("upper_bound = begin(): ", 11, text_face="scriba-sans")` (the painted string, trail included) → 125. The pill's usable text budget (134−12=122px) is already fully consumed by the rstripped line *before* the painter's own trailing space is added — the actual painted run is 3px over budget on line 1. This bug is **generic**: `pill_dimensions` is "the single source of truth ... used by every pill emitter (arc, plain-arrow, position)" per its own docstring (1404-1405), so it fires on any label — with or without `_` — that wraps to 2+ lines. The reporter's repro happens to wrap to exactly 2 lines (`"upper_bound = begin(): "` / `"nothing ≤ 3"`), which is why they saw it.
**Residual gap:** the reporter's own browser measurement (tspan w=130.1) is ~5px above this investigation's code-computed painted width (125px). That residual is architecturally consistent with the plain-text pill's white halo stroke (`stroke="white" stroke-width="3" stroke-linejoin="round" paint-order="stroke fill"`, confirmed present verbatim in the rendered `<text>` element) inflating a real browser's ink bounding box beyond pure glyph-advance — a live-rendering effect no static/Python-side analysis can confirm or measure, consistent with this task's own note that headless glyph measurement isn't available here.

### Finding 3: a second, smaller, code-confirmed measure≠paint divergence exists independently of the wrap bug
**Evidence:** `build_text_font.py:42-93` — `_feature_substitutions()` collects **every** GSUB single-substitution for the `tnum`/`lnum`/`zero`/`ss01` features and `main()` bakes the substituted advance into `inter_advances.json` unconditionally, for every codepoint that has one. A direct fontTools GSUB dump of the shipped `Inter-subset.woff2` shows the `tnum` lookup substitutes not just digits but also `parenleft`, `parenright`, `colon`, `comma`, `period`, `hyphen`, `equal`, `space`, and others to tabular-width alternates. `scriba-scene-primitives.css` scopes `font-feature-settings: "tnum" 1, "lnum" 1, "zero" 1, "ss01" 1` to cell/node text only (lines 396-408, 450-462); `.scriba-annotation > text` (534-539) declares no such feature settings.
**Detail:** Annotation-pill text therefore paints **default** (non-substituted) glyphs for colon/parens/equals/space/etc., while the single shared advance table stores the **tnum-substituted** width for those same codepoints — the table was built assuming the CSS reality of cell text, then reused wholesale for annotation text where that reality doesn't hold. For this specific repro string the net effect is small (this investigation's earlier fontTools delta sum came to roughly a few tenths of a pixel), but it is a real, code-provable, generalizable divergence — a label with more tnum-affected punctuation would show a larger gap. It is orthogonal to and additive with Finding 2's trail bug, not a duplicate of it.

### Finding 4: defect #2 (aria subscript) is an unconditional whole-string transform, not a math-scoped one
**Evidence:** `_latex_to_speech` (`_svg_helpers.py:1038-1083`) is applied to the raw label text at three call sites — `emit_plain_arrow_svg` (2053), the arc/link annotation emitter (2818), and `emit_position_label_svg` (3672, this repro's path) — with **no** gating on `_label_has_math()` (883-885) at any of them. `_label_has_math` exists and is used elsewhere (e.g. deciding whether to emit `aria-description`, 3673-3675) but never used to scope `_latex_to_speech` itself.
**Detail:** Live render confirms `aria-label="upper subscript bound = begin(): nothing ≤ 3"` exactly. The mechanism generalizes: **any** raw `_X` or `_{...}` substring in **any** non-math label gets spoken as a subscript, regardless of whether the author ever intended math notation.

### Finding 5: defects #3 and #4's paint bug share one root cause — `strip_math_markup`'s early return
**Evidence:** `_text_render.py:190` — `strip_math_markup`'s first line is `if "$" not in text: return text`. For a label with no `$` at all, the string is returned completely unmodified before painting (`_escape_xml(strip_math_markup(ln_text))`, `_svg_helpers.py:1640`).
**Detail:** This is why `\_` renders as a literal backslash (the unescape logic that turns `\_`→`_` only exists inside the math-segment branch of `strip_math_markup`) and why `\texttt{upper\_bound}` renders as the raw command name plus braces plus escaped underscore — none of it is TeX-interpreted, because the function never looks past the top-level `"$" not in text` gate for a label with no math delimiters.

### Finding 6: defect #4's aria garbling is independent of paint correctness, and has one specific missing rule
**Evidence:** Both the non-math (`\texttt{upper\_bound} = ...`) and math-wrapped (`$\texttt{upper\_bound}$ = ...`) variants render an **identical** garbled aria: `"textttupper\ subscript bound = ..."`. `_latex_to_speech` has dedicated regex rules for subscript/superscript (`_SUBSCRIPT_RE`/`_SUPERSCRIPT_RE`, 1033/1035) and for fixed-replacement commands (`_LATEX_SPEECH_MAP`), but no rule for brace-argument commands like `\texttt{...}`. Its generic backslash-strip pass (a `re.sub(r"\\([a-zA-Z]+)", ...)`-shaped step) strips the leading `\` off `\texttt`, leaving bare `texttt` glued directly onto the brace-stripped argument.
**Detail:** Confirms the math-wrapped variant is not "fixed" by KaTeX at all from the aria's perspective — `_latex_to_speech` runs on the whole raw label string (including the `$...$` delimiters and the command inside them) independently of whatever KaTeX does for visual rendering.

### Finding 7: Vietnamese diacritics show no divergence across any of the three consumers (plain text, no markup)
**Evidence:** Direct invocation with `s = "Được rồi: 3 phần tử"`: `measure_label_line(s, 11, text_face="scriba-sans")` → 99 (real number, full subset coverage, no heuristic fallback — corroborated by the existing `test_vietnamese_fully_covered_no_heuristic` and `test_nfc_decomposed_equals_precomposed` in `test_pill_math_wrap.py:174-207`); `_escape_xml(strip_math_markup(s))` → unchanged; `_latex_to_speech(s)` → unchanged; `_label_has_math(s)` → `False`.
**Detail:** All three consumers agree because none of their transform regexes (subscript, command-strip, math-delimiter-split) match anything in plain Vietnamese prose. Divergence in this repo's diacritics handling would only be a risk *inside* a `$...$` math segment mixing diacritics with LaTeX commands — out of scope for this ticket's repro, not evidended here.

## Divergence Map (Structural Ask 4)

| Construct | Ruler (`_text_metrics.py`) | Painter (`_svg_helpers.py` tspan path via `_text_render.strip_math_markup`) | Announce (`_svg_helpers.py:_latex_to_speech`) |
| --------- | -------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------- |
| raw `_` | Literal char, ordinary advance (934/2048 em) | Literal char, painted as-is | **Diverges** — `_SUBSCRIPT_RE` reads it as a math subscript operator → "subscript X" |
| `\_` (escaped) | Literal 2-char sequence, advances summed as-is | **Diverges** — literal backslash painted (`strip_math_markup` no-ops outside `$...$`) | Backslash stripped by the generic command-strip pass, but the surviving `_` still hits `_SUBSCRIPT_RE` — double-wrong |
| `\texttt{...}` outside `$...$` | Measured as literal TeX source (braces/backslash counted as ordinary chars) | **Diverges** — painted verbatim, raw command + braces visible | **Diverges** — command name glued to argument after backslash-strip + brace-strip, no verbatim rule |
| `$\texttt{...}$` (math-wrapped) | Routed to `measure_inline_math` (KaTeX metrics) — correct | Routed to real KaTeX, `KaTeX_Typewriter` face (genuine `@font-face`, confirmed in `katex.min.css`) — correct | **Still diverges** — same missing verbatim rule; runs on the whole label including the math segment |
| Multi-line wrap (any content) | Measures the **rstripped** wrapped line | **Diverges** — re-adds an unmeasured trailing space to every non-final line | N/A (announce operates on the whole unwrapped label, not per-line) |
| Vietnamese diacritics, plain text | Full subset coverage, exact advance-sum, NFC/NFD-invariant | Passthrough, unaffected | Passthrough, unaffected — **no divergence found** |

## Deduced Conclusions

### Deduction 1: defect #1 is not a `_`/subscript bug at all — it is a pre-existing multi-line pill sizing bug the reporter's string happened to trigger
**Based on:** Findings 1, 2.
**Reasoning:** The reporter's own proposed fix for #1 ("`_` literal everywhere") is already true in the measure and paint code paths — `_` was never the problem. The actual bug (trailing-space reinjection unaccounted for at wrap time) has nothing to do with underscores; it reproduces on any wrapped label.
**Conclusion:** Fixing "`_`-as-subscript" (which doesn't exist) would do nothing for defect #1. The fix belongs in `_wrap_label_lines`/`pill_dimensions`'s per-line measurement, not in any underscore-specific code.

### Deduction 2: defects #2, #3, and #4's aria half share one architectural cause — `_latex_to_speech` treats the *entire* label as LaTeX source
**Based on:** Findings 4, 6, and the Divergence Map.
**Reasoning:** `_latex_to_speech` and `strip_math_markup` both apply LaTeX-interpretation logic (subscript/superscript reading, command-stripping, brace-stripping) with only `strip_math_markup` — not `_latex_to_speech` — gated on the presence of `$`. Scoping `_latex_to_speech`'s transforms to run only *inside* `$...$` segments (mirroring the split `_label_has_math`/`strip_math_markup` already do) fixes defect #2 outright and half of #3/#4's aria garbling, because non-math text would then pass through completely literally.
**Conclusion:** This is the single highest-leverage code change in the report — one architectural fix (math-segment scoping) resolves the aria half of three of the four defects simultaneously.

## Source Code Trace

| Element | Detail |
| ------- | ------ |
| Defect #1 root cause | `_svg_helpers.py:1806,1811,1818,1823` (`.rstrip()` in `_wrap_label_lines`) vs. `:1636-1637` (`trail = "" if li == num_lines - 1 else " "` in `_emit_pill_label_text`) — two different strings for the same line, one measured, the other painted |
| Defect #1 secondary cause | `scripts/build_text_font.py:88-93` (unconditional tnum/lnum/zero/ss01 bake) vs. `scriba-scene-primitives.css:396-408,450-462` (feature-settings scoped to cell/node only) vs. `:534-539` (`.scriba-annotation > text`, no feature-settings) |
| Defect #2 root cause | `_svg_helpers.py:1033` (`_SUBSCRIPT_RE`) applied unconditionally inside `_latex_to_speech` (`:1038-1083`), called at `:3672` with no `_label_has_math` gate |
| Defect #3/#4 paint root cause | `_text_render.py:190` (`strip_math_markup`, `if "$" not in text: return text`) |
| Defect #4 aria root cause | `_latex_to_speech`'s generic backslash-strip step (inside `1038-1083`) has no `\texttt{...}`-shaped (command-with-brace-argument) extraction rule, unlike its dedicated `_SUBSCRIPT_RE`/`_SUPERSCRIPT_RE` handling |
| Where math *is* handled consistently | `measure_inline_math` (ruler) and the real KaTeX/`foreignObject` path (paint) both correctly render `$\texttt{...}$` — confirmed via `KaTeX_Typewriter-Regular.woff2` having a genuine, non-fallback `@font-face` in `katex.min.css` |
| Existing near-miss test | `tests/unit/test_pill_math_wrap.py:217-230` (`test_scriba_sans_pill_covers_painted_text`) encodes the reporter's exact invariant but only for `lines == [label]` (single line) |

## Reproduction Plan

All four repros rendered via `SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py <input> -o <output> --no-minify` from the repo root (0.34.0 / 13eadc7).

**1. Raw underscore** (`label="upper_bound = begin(): nothing ≤ 3"`):
```html
<rect x="1" y="-39" width="134" height="32" .../>
<text ... stroke="white" stroke-width="3" .../>
  <tspan x="68" dy="-6.5">upper_bound = begin(): </tspan>
  <tspan x="68" dy="13">nothing ≤ 3</tspan>
aria-label="upper subscript bound = begin(): nothing ≤ 3"
```
Confirms defect #2 exactly. Confirms defect #1's *symptom* (see Finding 2 for the real mechanism — `pill_dimensions` measured the rstripped `"upper_bound = begin():"` at 122px, but the painted tspan text with the reinjected trailing space measures 125px).

**2. Escaped underscore** (`label="upper\_bound = ..."`):
```html
<rect ... width="138" .../>
  <tspan ...>upper\_bound = begin(): </tspan>
aria-label="upper\ subscript bound = begin(): nothing ≤ 3"
```
Confirms defect #3: literal backslash painted. Rect grows exactly 4px (134→138) — the backslash glyph's own advance, so the sizing pipeline stays self-consistent even though the *content* is wrong.

**3. `\texttt{}` outside math**:
```html
  <tspan ...>\texttt{upper\_bound} = begin(): </tspan>
aria-label="textttupper\ subscript bound = begin(): nothing ≤ 3"
```
Confirms defect #4's non-math paint claim (fully verbatim) and aria claim.

**4. `$\texttt{}$` inside math**:
```html
<foreignObject class="scriba-annot-fobj">...</foreignObject>  <!-- real KaTeX, KaTeX_Typewriter face -->
aria-label="textttupper\ subscript bound = begin(): nothing ≤ 3"
```
Confirms defect #4's "works visually via KaTeX, aria still garbled" claim — identical aria string to variant 3, proving the garbling is independent of paint correctness.

## Recommended Fix Sketch

1. **(Highest priority — fixes defect #1's real cause, all annotation shapes)** In `pill_dimensions`/`_wrap_label_lines` (`_svg_helpers.py:1398-1449`, `1719-1824`), measure each non-final wrapped line **with** the trailing space the painter is going to add, instead of the rstripped line — e.g. change the per-line measurement in `pill_dimensions` to mirror `_emit_pill_label_text`'s own `trail` logic (measure `ln + (" " if li < len(label_lines) - 1 else "")`). Smaller and more surgical than changing the painter, and preserves the "copied text stays worded" UX behavior the trailing space exists for (comment at 1635).
2. **(Fixes defect #2, and half of #3/#4's aria)** Scope `_latex_to_speech` (`_svg_helpers.py:1038`) to only apply its subscript/superscript/command-strip transforms *inside* `$...$` segments — split on `_MATH_DELIM_RE`/`_INLINE_MATH_RE` first (mirroring `_label_has_math`/`strip_math_markup`'s own pattern), run the existing transform only on the math fragments, and leave everything else byte-identical.
3. **(Fixes defect #3)** In `strip_math_markup` (`_text_render.py:190`), unescape recognized escapes (`\_`, `\$`, etc.) as an unconditional first pass, before the `"$" not in text` early return — don't gate escape-handling behind math-delimiter presence.
4. **(Fixes defect #4's remaining aria garbling; nice-to-have for non-math paint)** Add a dedicated `\texttt\{([^}]*)\}` extraction rule in `_latex_to_speech`, applied before the generic command-strip pass, that speaks the literal argument (after its own `\_`→`_` unescape) instead of falling through to generic stripping. For the paint "nice-to-have": rather than building a new monospace metrics table, auto-promote bare `\texttt{...}` occurrences outside any existing `$...$` into an implicit math segment before wrap/measure/paint — this reuses the already-correct KaTeX pipeline (`KaTeX_Typewriter` has a real `@font-face`; `measure_inline_math` already has its metrics) with zero new font work. Guard against double-wrapping text already inside an explicit `$...$`.

**Ordering rationale:** fix 1 is independent of the others and has the broadest blast radius (every multi-line annotation pill, not just underscore-bearing ones) — land it first regardless of the rest. Fixes 2+3 share the same "math-segment scoping" principle and should land together. Fix 4 is the smallest and layers cleanly on top of 2+3.

## Property-Test Feasibility

Infrastructure exists and is close, but has one specific, well-understood gap:

- `tests/unit/test_pill_math_wrap.py::TestScribaSansTextFace::test_scriba_sans_pill_covers_painted_text` (217-230) already asserts almost exactly the reporter's proposed invariant — `pill_w >= painted + 2 * _LABEL_PILL_PAD_X - 0.5` — but only for the single-line case (`lines == [label]`), where `trail` is structurally always `""` (Finding 2's mechanism can't fire when there's only one line). No sibling test re-derives "painted" for the *multi-line* case, so the wrap-vs-paint gap in Finding 2 had no test that could have caught it.
- `tests/helpers/painted_extent.py`'s `painted_extent()` is the closest thing to a headless painted-geometry oracle in the repo, but its own docstring states outright: "Text is not measured; every annotation label sits inside its measured pill rect" — it deliberately trusts `pill_dimensions()`'s self-report for anything inside a `<text>`/`<tspan>` rather than independently re-measuring it. This is precisely why the existing "everything painted stays inside the bbox" test (`test_math_pill_painted_within_bbox`, same file, 110-118) could not have caught defect #1 — it exempts the one thing that actually overflowed.
- No real headless-browser glyph-rendering oracle exists in the repo, and none is needed: the entire measurement stack is a closed-form, deterministic, exact-advance-table Python function (`ShippedFontMeasurer`) — the same function tests and production both call. A faithful property test doesn't need a browser; it needs to simulate the *painter's* exact string transform (rstrip + conditional trail-space + `strip_math_markup`) and re-measure **that** string, rather than trusting `pill_dimensions()`'s internal return value.
- **Recommended test shape:** for each wrapped line except the last, assert `measure_label_line(ln + " ", font_px, text_face="scriba-sans") + 2 * _LABEL_PILL_PAD_X <= pill_w`; for the last line, assert the same without the added space. Run this over both `_MIXED_MATH_LABEL`-style and plain-text multi-line fixtures already present in the same file. This would have failed against the exact repro and pins fix 1 above. The aria half (`"aria contains the literal string"`) is separately and trivially testable today — `_latex_to_speech(raw_label) == raw_label` for any label with no `$...$` is a one-line assertion once fix 2 lands, and is false today (demonstrated by Finding 4/7's contrast).

## Affected Tests

- `tests/unit/test_pill_math_wrap.py` — extend `TestScribaSansTextFace` with the multi-line trail-inclusive invariant described above; add plain-text (non-math) cases alongside the existing Vietnamese/math ones.
- `tests/unit/test_link_label_obstacle.py`, `tests/unit/test_note_command.py` — both share `pill_dimensions`/`_wrap_label_lines` per the commit history (e59d263, b119f0a); worth a sweep once fix 1 lands to confirm no byte-identical goldens silently shift for already-passing multi-line cases.
- New aria coverage: no existing test asserts `_latex_to_speech` is a no-op on non-math text containing `_`, `\_`, or `\cmd{...}` — this is the exact coverage gap that let defects #2/#3/#4's aria half ship unnoticed.

## Regression Risks

- **Fix 2 (math-scoping `_latex_to_speech`) must preserve legitimate math subscript speech.** Labels like `$dp_i$` or `$dp_{i-1}$` must still announce "dp subscript i" — the fix should scope the *existing* `_SUBSCRIPT_RE`/`_SUPERSCRIPT_RE` machinery to run only on math fragments (which is where it belongs and already works correctly), not remove or weaken it.
- **Fix 1 (trail-aware measurement) must not remove the trailing-space UX feature.** The comment at `_svg_helpers.py:1635` ("non-final lines keep a trailing space so copied text stays worded") describes an intentional behavior for copy-paste. The fix should make the *measurement* account for it, not delete it from the painter.
- **Fix 3 (unconditional `\_`→`_` unescape) should be checked against any fixture relying on a literal backslash-then-underscore surviving as-is** — unlikely given the reporter's expectation and the "labels are a TEXT field" framing, but worth a quick grep of existing golden fixtures before landing.
- **Fix 4's auto-promotion of bare `\texttt{...}` into implicit math** must only trigger outside any pre-existing `$...$` span, to avoid double-wrapping (`$\texttt{$\texttt{x}$}$`-shaped corruption) when an author already wrote the math delimiters themselves.

## Side Findings

- (Confirmed, out of scope for JZ-13, flagged for a separate ticket) `color="state:error"` — present verbatim in the reporter's own repro — does not resolve to the `error` style bucket. `ARROW_STYLES.get(color, ARROW_STYLES["info"])` appears at 5 call sites (`_svg_helpers.py:2044, 2786, 2812, 3215, 3577`); `ARROW_STYLES`'s keys are the bare bucket names (`info`/`warn`/`good`/`error`/`muted`/`path`), so a `state:`-prefixed value never matches any key and silently falls through to the `info` default. Confirmed via the repro's own render: the pill paints `fill="#506882"`/`font-weight:500` (the `info` bucket's styling), not the `error` bucket's expected styling. This affects every annotation using a `state:`-prefixed color, independent of and unrelated to the four text-mode defects above — noted here only so it isn't mistaken for a fifth symptom of this ticket.

## Conclusion

**Confidence:** High

**Verdict:** 2 of 4 defects (#2, #3) and both halves of a 3rd (#4) are **CONFIRMED** exactly as reported, with clean, isolated root causes. Defect #1 is **PARTIAL** — the reported symptom (under-sized pill) is real and reproduces exactly, but the reporter's own hypothesis (an `_`→subscript interpretation in the ruler) is refuted outright; no such logic exists anywhere in the measure/paint path. The actual cause is an unrelated, pre-existing multi-line word-wrap bug (a paint-time trailing space the width ruler never measures) that happens to fire on this repro because the label wraps to two lines — it would fire identically on a two-line label containing no underscore at all. A second, smaller, code-confirmed divergence (tnum-feature advances baked into the shared measurer table but never requested by annotation CSS) compounds it slightly. The reporter's structural framing — "a label is a TEXT field; `_`/`\_`/`\texttt{}` should be interpreted identically by the ruler, the painter, and the aria builder, everywhere outside `$...$`" — is the correct fix direction for defects #2-#4, and this investigation's fix sketch implements exactly that principle by scoping `_latex_to_speech` and `strip_math_markup`'s transforms to math segments only.
