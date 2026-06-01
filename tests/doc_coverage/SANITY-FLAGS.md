# Doc-coverage HTML render-sanity flags

**Date:** 2026-06-01
**Checker:** `tests/doc_coverage/check_render_sanity.py` (`sanity_check(html, test_id) -> list[str]`)
**Corpus:** `tests/doc_coverage/corpus/*.html` (300 `ok` snippets, gitignored)

## Summary

**8 / 300 files flagged; 292 / 300 clean.**

| Category | Files flagged | Verdict |
|----------|--------------:|---------|
| Duplicate `id=` in SVG (double `<defs>` arrow markers) | 7 | Real render defect (minor) |
| `katex-error` marker present | 1 | Expected (negative test for bad KaTeX) |
| Forbidden value tokens (`NaN`/`Infinity`/`undefined`/`None`) | 0 | — |
| `InterpolationRef` / `\x00HL` / `&lt;span` / `[object Object]` | 0 | — |
| Leaked `[E####]` in visible text | 0 | — |
| viewBox not 4 finite positives | 0 | — |
| Malformed SVG XML | 0 | — |
| Blank stage SVG | 0 | — |
| Text far outside viewBox (>50%) | 0 | — |

## Flags by prefix

### `prim_graph_` (5 of 47 flagged)
- `prim_graph_directed_true` — svg#0 duplicate id(s): `scriba-arrow-fwd`, `scriba-arrow-rev`
- `prim_graph_layout_hierarchical` — svg#0 duplicate id(s): `scriba-arrow-fwd`, `scriba-arrow-rev`
- `prim_graph_orientation_lr` — svg#0 duplicate id(s): `scriba-arrow-fwd`, `scriba-arrow-rev`
- `prim_graph_orientation_tb` — svg#0 duplicate id(s): `scriba-arrow-fwd`, `scriba-arrow-rev`
- `prim_graph_stable_directed_warns_ok` — svg#0 duplicate id(s): `scriba-arrow-fwd`, `scriba-arrow-rev`

### `cmd_` (1 of 32 flagged)
- `cmd_shape_bool_lowercase` — svg#0 duplicate id(s): `scriba-arrow-fwd`, `scriba-arrow-rev`

### `latex_` (1 of 69 flagged)
- `latex_diagram_basic` — svg#0 duplicate id(s): `scriba-arrow-fwd`, `scriba-arrow-rev`

### `neg_` (1 of 5 flagged)
- `neg_E1200_bad_katex` — forbidden substring `katex-error` appears 1x in content

### Clean prefixes
`prim_tbl_` (0/36), `prim_lin_` (0/29), `prim_plot_` (0/47), `annot_` (0/35).

## Flag detail and verdicts

### Duplicate-id defect (7 files) — real render bug, low severity
Every flagged file renders a **directed graph** (or a diagram that contains one).
The stage `<svg>` emits the arrow-marker `<defs>` block **twice**: once at the
SVG root and once inside the `translate(...)` content group. Both copies use the
same `id="scriba-arrow-fwd"` / `id="scriba-arrow-rev"`. Duplicate IDs in one
document are invalid SVG/HTML; only the first marker is referenceable, so the
second `<defs>` is dead weight. All 7 share the identical root cause (directed
graph double-`<defs>` emission). Confirmed: each flagged svg#0 contains exactly
2 `<defs>` blocks.

Recommendation for Phase 3: file a `KNOWN_BUGS`-style strict-xfail keyed on the
directed-graph double-`<defs>` emission, and a follow-up code fix to emit the
marker defs once per SVG.

### `katex-error` (1 file) — expected negative test
`neg_E1200_bad_katex.tex` intentionally feeds malformed KaTeX
(`label="$\frac{1}{$"`). KaTeX renders a `<span class="katex-error">` marker
(the E1200 warning path). This is the designed behaviour of that negative
snippet, not a regression. Phase 3 should exempt this snippet from the
`katex-error` assertion (it is a `neg_` test whose intent is precisely to leave
the marker in place).

## Heuristics implemented

1. **Forbidden substrings** (over content regions only — see calibration):
   - Plain: `InterpolationRef`, `[object Object]`, `\x00HL` (null-byte highlight
     placeholder), `&lt;span` / `&lt;/span` (escaped-markup leak), `katex-error`.
   - Whole-word value tokens: `NaN`, `Infinity`, `undefined`, `None`
     (word-boundary matched so `display:none`, `fill="none"`, identifiers, etc.
     never match).
   - Leaked error code: bracketed `[E####]` in visible body text (the exact form
     scriba emits, e.g. `f"[E1115] ..."`).
2. **viewBox sanity:** every `<svg>` must declare a `viewBox` with exactly 4
   finite numbers and width > 0, height > 0 (rejects `0 0 0 0`, negative, NaN/inf).
3. **Well-formed SVG + duplicate id:** each inline `<svg>...</svg>` must parse as
   XML (`xml.etree.ElementTree`); duplicate `id=` values within one SVG are flagged.
4. **Non-empty shape output:** an SVG carrying `scriba-stage-svg` must contain at
   least one `data-primitive` / `data-target` / geometry element
   (`rect|circle|line|path|polygon|polyline|ellipse|image`) / `<text>`. Pure
   text/KaTeX outputs (no stage SVG) are exempt.
5. **Text in-bounds (heuristic):** translate-aware position of each `<text>`; flag
   only if it lands > 50% of a dimension beyond a viewBox edge. Subtrees under
   `rotate`/`scale`/`matrix`/`skew` transforms are skipped (can't cheaply resolve).

## Calibration decisions (false-positive avoidance)

- **Region scoping is the key decision.** Each `.html` inlines a ~400 KB shared
  shell: a `<style>` block with **base64-encoded KaTeX web fonts** (which embed
  literal `NaN` and `stroke:none` substrings) and a control `<script>` block
  (which embeds `undefined` and `display:none`). Naïve whole-file substring
  matching flags 256/300 on `NaN` alone. The checker therefore runs
  forbidden-substring checks only over **content regions**: the inline
  `<svg>...</svg>` blocks plus visible body text with `<style>`, `<script>`, and
  `<svg>` stripped and remaining tags removed. Verified: 0 occurrences of any
  forbidden value token survive in content regions across all 300 files.
- **`None`/`none` distinction.** `none` is a legitimate CSS/SVG value
  (`display:none`, `fill="none"`, `stroke="none"` — 245 legit occurrences inside
  SVGs, 300 files contain the substring somewhere). Only the capitalized Python
  sentinel `None` is treated as a forbidden value token, matched with word
  boundaries so `fill="none"` and class names are never flagged.
- **E-code form.** A bare `E1115` appears legitimately in narration prose
  (`neg_gotcha_codepanel_line0` says "line[0] warns (E1115)"). Scriba's actual
  leak format is the **bracketed** `[E1115]`, so the checker flags only `[E####]`
  in visible text. This passes the prose case and would catch a real leak.
- **Text-bounds threshold = 50%.** Transform-aware survey of all 402 SVGs shows
  the worst legitimate text overflow is ~0.25 (annotation labels sitting just
  above a shape, e.g. `annot_annotate_arrow_true`). A 0.5 threshold leaves
  comfortable headroom and produced 0 false positives.
- **Non-empty only for stage SVGs.** 47 files are pure text/KaTeX
  (`latex_code_*`, `latex_fmt_*`, `latex_math_*`, sections, lists, links). They
  have no `scriba-stage-svg` and are exempt; the check applies only to the 253
  shape-stage outputs (all of which are non-blank).

## Verification

All 5 heuristics were exercised against synthetic bad inputs (NaN coord, Infinity
text, undefined/None text, InterpolationRef, `[object Object]`, `\x00HL`,
`&lt;span`, bracketed E-code leak, `viewBox="0 0 0 0"`, negative/missing viewBox,
malformed XML, duplicate id, blank stage, text 400% out of bounds) — each fires.
Negative controls (`display:none`, `fill="none"`, `stroke="none"`, parenthesized
`(E1115)` prose, clean shape, pure text) stay clean.
