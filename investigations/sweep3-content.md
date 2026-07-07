# Sweep 3-C — Value-channel content torture

Scope: adversarial *content* in `value=` / `label=` / ids across primitives
(scriba 0.30.0). Read-only on source; probes under `_sweep3_content/*.tex`,
rendered from repo root with `.venv/bin/python render.py <p>.tex -o
./_sweep3_content/<p>.html`. Verification is numeric parsing of the emitted
**static** SVG (JS `<script>` frame blobs are excluded — see Method) against
the repo oracle `measure_value_text` (`_text_metrics.py:207`).

Reservation model (confirmed by reading source before probing):
- Cell surfaces size to `measure_value_text` and paint the value; the plain
  `<text>` fast path (`_text_render.py:276`) never clips, the `$math$`
  `<foreignObject>` slow path clips with `overflow:hidden;text-overflow:ellipsis`
  when `clip_overflow` (default True) — `_text_render.py:387-388`.
- `measure_value_text` for a `$math$` string returns
  `max(measure_label_line, base(strip_math_markup))` — covers both the KaTeX FO
  paint and the stripped-text fallback, so under-reservation needs *both* models
  to under-predict.
- Node-label surfaces (graph/tree/forest/matrix labels) pass
  `clip_overflow=False` → spill, never clip.

---

## Findings

### F1 — HIGH — Matrix `data=` constructor crashes (raw traceback) on any non-float cell
**Probe:** `p04` (adversarial numerics), `_x_matrix_empty`, `_x_matrix_space`, `_t` (`1e9`).
**Numbers / repro:**
- `\shape{m}{Matrix}{rows=1,cols=2,data=["abc",2]}` → `ValueError: could not
  convert string to float: 'abc'` — **raw Python traceback, exit 1**.
- `data=[""]` → `ValueError: ... : ''`; `data=[" "]` → `... : ' '`;
  `data=[1e9,2]` → `... : 'e9'` (the number lexer `_NUMBER_RE`,
  `parser/lexer.py:98`, has no scientific-notation rule, so `1e9` tokenizes as
  NUMBER `1` + IDENT `e9`, and `float('e9')` throws).
**Mechanism:** `matrix.py:227` `flat = [float(v) for v in raw_data]` (and the 2-D
twin `matrix.py:224`) are **unguarded**. Matrix validates *shape* (E1422) and
*colorscale* (E1421) but has no numeric-cell validation.
**Why it's a defect (not just "fail loud"):** the sibling numeric surface **Bar
validates the identical input cleanly** — `bar.py:171-192` raises E1488/E1489/
**E1490** ("Bar 'data' contains a non-numeric entry 'abc'"), and even
`1e9`→`'e9'` yields a clean E1490. Matrix's own **apply**-path is also guarded —
`\apply{m.cell[0][0]}{value="abc"}` raises a clean **E1107**
(`_frame_renderer.py:_validate_numeric_value_channels`). Only Matrix's
constructor `data=` is unguarded, so it uniquely emits a stack trace that leaks
internal file paths instead of the documented E-code contract.
**Reachability (axis 10):** high — an empty-string placeholder is a plausible
authoring habit (DPTable legitimately uses `data=["","",...]`), and scientific
notation is a natural thing to try in a `show_values` heatmap. `_x_dptable_mathlong`
confirms DPTable accepts `""` fine; a user porting that to Matrix gets a crash.
**Fix shape (for the owner):** mirror `bar.py`'s E1490 guard in `matrix.py`
before the `float()` comprehensions.

### F2 — LOW — Stale `_VALUE_LESS_HINTS["graph"]` contradicts `graph.renders_value`
**Probe:** `_gn`, `_gn2` (`\apply{g.node[a]}{value=5}`).
**Numbers:** node `a` renders `5` (value overrides id) with **no E1105**, and the
value **persists across steps** (frame0 `['5','b']`, frame1 `['5','b']` — no
flip-back). This is correct/intended: `graph.renders_value` returns True for
`node[`/`edge[` (`graph.py:1569-1580`, "mirrors Tree/Forest node-value display").
**Defect:** the hint string `_frame_renderer.py:92-95` still says *"value= is
edge-scoped on Graph; node values are not rendered — apply value= to an
edge[(u,v)] instead."* That is now false and would misdirect an author if ever
surfaced. Doc-in-code only; the E1105 **channel itself is honest** (see clean list).

### F3 — LOW — Graph node label with a pathological long token overflows viewBox + overlaps neighbor
**Probe:** `p03` (`\apply{g.node[n1]}{value=<58-char token>}`).
**Numbers:** `measure_text(token)=428px`; the two nodes sit ~105px apart
(circles at (116,165) and (146,64), r=20). The n1 label paints as a single
centered `<text>` spanning **x=[-98, 330]** inside `viewBox="0 0 906 619"` — the
left ~98px is **outside x=0** and the label covers node n2. Node labels are
`clip_overflow=False` (spill by design), and the viewBox grew right (to 906) but
not left. Nodefit reserves pitch from label width but does not re-center a node
pinned near the left edge under an extreme label.
**Reachability:** low — 58-char single-token node labels are not realistic
editorial content; short ids/values are the norm.

### (Related, out-of-slice) NumberLine `ticks=[list]` → raw `TypeError`
`\shape{nl}{NumberLine}{...,ticks=[0,5,10]}` → `TypeError: int() argument must
be a string ... not 'list'` (`numberline.py:116 ticks = int(ticks)`). A
construction param, not a value-channel, so noted only: same unguarded-coercion
class as F1 (a plausible "ticks as positions" mistake yields a stack trace, not
an E1114-style type error).

---

## Clean list (probed, verified safe)

- **Math values (axis 1)** — `p01` Array, `_x_dptable_mathlong` DPTable,
  `_x_edge_math` edge weight. Reserved width = the surface's uniform max ≥ each
  cell's `measure_value_text` model: p01 all math FO widths = 86 ≥ per-cell
  models (34/74/29); DPTable math FO w=247 ≥ 74; edge math FO w=73 ≥ 61 (KaTeX
  present). `\sqrt` etc. are non-linear → over-estimating heuristic, and the
  `max(model, stripped-name)` in `measure_value_text` makes the stripped form
  ("sqrtn") dominate and over-cover. No clip on any math surface.
- **Combining / emoji / fullwidth (axis 2)** — `p02`. Vietnamese `đường đi`
  measures 58 (in-table, exact); Zalgo `ê̂́` = 8 (combining marks 0-width, NFC
  handled); `🔥` = 14, ZWJ `👨‍👩‍👧` = 14 (whole cluster 1em), fullwidth `１２３`
  = 42 (3×1em). All fit the uniform cell; VariableWatch grows to fit
  (`🔥🔥🔥🔥🔥`=70 in rectW=161). Non-math → plain `<text>`, never clips.
- **Long tokens (axis 3)** — `p03`. Array grows (rectW=438 for a 428px token),
  VariableWatch grows (592), DPTable grows (245). `\annotate` **char-wraps the
  full 58 chars with no ellipsis/truncation**; `\note` truncates **loudly**
  (`_x_note_overflow` → E1125 wider + E1126 taller, clamped to viewBox). Only the
  graph node case spills (F3).
- **Numerics (axis 4)** — `p04`. Zero `nan`/`inf`/`infinity` in any emitted SVG
  attribute; zero negative geometry attrs; Bar clamps negatives to ≥0 height,
  decimals round (`0.007`→`0.01`), 1e9 int renders full. Matrix fills valid.
- **Empty / space (axis 5)** — `p05`. `""` and `" "` on Array, VariableWatch,
  Queue, Graph produce clean empty/blank boxes — no crash, no stray artifacts;
  two empty-id graph nodes both render. (Matrix is the exception → F1.)
- **XML-hostile (axis 6)** — `p06`. `<b>x</b>`, `a&d`, `q<r>s`, `t"u`, hostile
  node ids `<n>`/`a&b`, annotate/label all escape to `&lt;`/`&amp;`/`&quot;` in
  text; every static frame is **XML-well-formed** (minidom parse, 0 failures);
  **zero** attributes contain a raw `<`; hostile ids never leak unescaped into
  `data-*` attrs. `_escape_xml` (`_text_render.py:137`) + `_render_mixed_html`.
- **Literal escapes (axis 7)** — `p07`. Backslash is correct in the **static**
  frames (`c\d` = one 0x5c). The apparent 1→2 doubling in later frames was a
  **false positive**: it lives inside the `<script>` backtick JSON blob
  (`_html_stitcher._escape_js`, line 129, `\`→`\\`) which the browser reverses
  at `JSON.parse`/backtick-eval. `\n` decodes to a real newline (cosmetic —
  collapses to whitespace in `<text>`); `\t` stays literal.
- **RTL (axis 8)** — `p08`. `unicode-bidi:plaintext` is applied to **every**
  RTL-bearing surface: Array cells (`مرحبا`, and the mixed
  `نتيجة (result) = 42`), VariableWatch values, `\annotate` pills, **and graph
  nodes** — full parity with the 0.29 pill fix. LTR strings stay bidi-naked.
  `_bidi_style` (`_text_render.py:41-51`). W1301 over-estimate warning fires once
  for Arabic (safe — never clips).
- **E-code honesty (axis 9)** — E1115 soft-drop **warns** and keeps rendering
  (`a.cell[99]`, `_frame_renderer.py:957`); E1105 **fail-loud** on an unknown
  `\apply` key (`bogus=` → lists valid keys); the **value-on-no-value-slot** gate
  (`_frame_renderer.py:99-153`) fires loudly for Stack `item[0]` and NumberLine
  `tick[0]` with actionable hints; graph node/edge `value=` is honored (F2 hint
  aside); apply-time numeric E1107 guards Matrix + Bar.

## Method notes
- **Always exclude `<script>` blocks** before parsing "rendered" SVG — the live
  runtime embeds each frame as a backtick/JSON-escaped string whose backslashes,
  quotes and even `<svg>`-looking substrings are escaped and would read as
  defects but are reversed by the browser. `harness._strip_scripts` does this;
  skipping it produced the F-avoided false positive in axis 7.
- Oracle: `measure_value_text` / `measure_text` from the repo, matched against
  emitted `<rect>` widths, `<foreignObject width>`, and `<text>` extents.
