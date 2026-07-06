# Hunt: Authoring traps on the 0.26.x new surfaces

Scope: wrong/edge **author input** on the surfaces that shipped in 0.26.x — `at=` board,
`\zoom`, `\note`, `strike=`, board-`\focus`, TraceTable, Equation, live `\invariant`,
graph/tree `\trace`. Question per case: does the author get a **helpful E-code**, a
**silent wrong render**, or a **traceback leak**? Plus: do the **documented examples**
render as described? Read-only on source; every row below was rendered through
`render.py` (author-facing, no `SCRIBA_DEBUG`). No playwright.

## Hand-off Brief

**No traceback ever leaked.** Across ~60 malformed/edge inputs, every failure path is a
clean `ScribaError` (`error [E1xxx] …`, exit 2) or a `UserWarning` (`[E11xx] …`, exit 0) —
`render.py`'s `main()` never saw a non-`ScribaError` escape. The error catalog is dense and
the messages are mostly good: `at=` malformation splits into three distinct E1540 wordings
(1-elem / negative / float / string), and E1541 (mixed) / E1542 (dup cell) both name the
offending shapes. **Robustness is strong; the traps are all in the *silent* lane, not the
crash lane.**

**The sharpest trap is `\note` overflow (HIGH).** A note whose rendered pill is wider than
the board is drawn **single-line, un-wrapped, anchored to its compass corner, and clipped by
the SVG viewport** (the stage `<svg>` has no `overflow:visible`) — with **no warning**. On the
standard single-Array board (~332px) a 54-char full-sentence note ("careful: off-by-one — the
window is half-open [lo, hi)") already loses 15% off the left edge; 85 chars loses 45%; a
long note on a small size-3 board (208px) loses 84%. The author's teaching message silently
truncates and there is zero feedback. The docs promise the note "paints inside the existing
viewBox" — for any note longer than the board it *cannot*, and it clips rather than wraps.

**Four MED silent-wrongs**, all "contradictory/edge input accepted with no diagnostic":
(1) **`at=` has no upper bound** — every empty grid track reserves 20px, so a large or
typo'd index silently balloons the canvas with two illegible shapes marooned in the corners;
`at=[100000,100000]` yields a **2,000,392 × 2,000,104px** viewBox, rc=0, no cap, no warning.
(2) **Two `\zoom` in one step is last-wins**, silently dropping the earlier target — even
though `\zoom` is documented as "the camera twin of `\focus`" and `\focus` *unions* multiple
targets in one step. (3) **`\annotate{shape}{…}` on a bare shape name is a silent no-op** for
*both* `strike=true` and `label=` — no visual, no warning — while `.all`/OOB warn E1119 and
`\zoom{a}`/`\focus{a}` happily accept the same bare shape. (4) **`Equation` with BOTH `tex=`
and `lines=`** is silently accepted (lines wins, tex vanishes) although the docs say "Exactly
one … is required (E1530)".

**Docs-vs-behavior (HUNT B): clean.** All 11 documented examples for the new sections render
**and match their described behavior** — Equation line-reveal sequences hidden→idle exactly
as written, the segtree recipe's tricky escaped-quote `arrow_from="st.node[\"[0,2]\"]"`
resolves both arcs, `\zoom` crops then auto-restores, `\note` re-issue replaces in place,
board-`\focus` dims more than shape-`\focus`. **No doc-bug found.**

Complementary to `hunt-runtime-static.md` (that hunt owns `\invariant` static/print honesty
and manifest records); this hunt owns **input traps + rendered geometry**. No overlap.

## Trap matrix (HUNT A — wrong/edge usage)

Verdict legend: **Confirmed** = rendered, cited proof. Behavior: `E-code` = clean author
error (exit 2); `warn` = UserWarning soft-drop (exit 0); `silent` = rc=0, no diagnostic.

| # | case | behavior | severity | verdict |
|---|------|----------|----------|---------|
| **A1 · `\zoom`** | | | | |
| 1 | `\zoom{}` (empty) | `E1010` "Selector parse error … expected identifier, got EOF" | LOW (cryptic, not zoom-specific) | Confirmed |
| 2 | `\zoom{a}` then `\zoom{b}` same step | **silent last-wins** — crops to `b` only, `\zoom{a}` dropped | **MED** | Confirmed → **F3** |
| 3 | `\zoom{a}` in prelude | `E1053` "…not allowed in the prelude (frame-only, ephemeral camera crop)" | none (good) | Confirmed |
| 4 | `\zoom{a.cell[99]}` OOB | `E1543` warn "no resolvable box; falling back to full-board" | none (good, matches doc) | Confirmed |
| 5 | `\zoom{ghost.cell[0]}` undeclared | `E1116` "\zoom references undeclared shape 'ghost'" | none (good) | Confirmed |
| **A2 · `at=`** | | | | |
| 6 | `at=[0]` (1 elem) | `E1540` "malformed at=[0]; must be a 2-element list [row,col]…" | none (good) | Confirmed |
| 7 | `at=[-1,0]` | `E1540` "row and col must be non-negative integers" | none (good) | Confirmed |
| 8 | `at=[0.5,1]` (float) | `E1540` "row and col must be non-negative integers" | none (good) | Confirmed |
| 9 | `at="0,0"` (string) | `E1540` "malformed at='0,0'; must be a 2-element list…" | none (good) | Confirmed |
| 10 | `at=[99,99]` sparse / `[100000,100000]` | **silent** 2372×2084 / **2,000,392×2,000,104px** viewBox; no cap/warn | **MED** | Confirmed → **F2** |
| 11 | two shapes same cell | `E1542` "duplicate placement: shapes 'a' and 'b' both declare at=[0,0]…" | none (good msg) | Confirmed |
| 12 | mixed (`at=` on one only) | `E1541` "mixed placement: shape(s) 'b' have no at=… all-or-nothing" | none (good msg) | Confirmed |
| **A3 · `\note`** | | | | |
| 13 | `\note{n1}` (missing text) | `E1120` "\note requires an id and text=…" | none (good) | Confirmed |
| 14 | `\note{n1}{text=""}` (empty text) | `E1120` (empty string treated as missing) | LOW (defensible) | Confirmed |
| 15 | dup id same frame | silent last-wins (2nd replaces 1st) | none (matches "re-issue=replace" doc) | Confirmed |
| 16 | `at=middle` (bad anchor) | `E1121` "unknown note anchor 'middle'; valid: bottom, bottom-left…" | none (good) | Confirmed |
| 17 | **very long text** | **silent off-canvas clip, no wrap, no warn** | **HIGH** | Confirmed → **F1** |
| 18 | `text="$O(n\log n)$"` (math) | renders KaTeX | none (good) | Confirmed |
| **A4 · `strike=`** | | | | |
| 19 | `strike` on `a.all` | `E1119` warn "no drawable extent; skipped" | none (loud no-op) | Confirmed |
| 20 | `strike` on whole shape `\annotate{a}{…}` | **silent no-op** (also drops `label=`; no warn) | **MED** | Confirmed → **F4** |
| 21 | `strike` on Equation `E.term[rec]` | `E1119` warn "no drawable extent" | LOW (defensible — term has no box) | Confirmed |
| 22 | `strike` on TraceTable `t.row[0]` | `E1119` warn "no drawable extent" | LOW (defensible) | Confirmed |
| 23 | `strike` + `ephemeral=true` | draws, clears next step | none (good) | Confirmed |
| **A5 · TraceTable** | | | | |
| 24 | `row=` wrong length mid-timeline | `E1521` "row has 2 value(s) but there are 3 column(s)" — **no line #** | LOW (msg lacks which `\apply`) | Confirmed |
| 25 | row with `$math$` values | renders | none | Confirmed |
| 26 | row with Vietnamese text | renders (viewBox 146×106, "lớp lẻ" present) | none | Confirmed |
| 27 | `columns=[]` (0 cols) | `E1520` "requires a non-empty 'columns' list" | none (good) | Confirmed |
| 28 | 65 columns | `E1522` "columns count (65) is out of range; valid: 1..64" | none (good) | Confirmed |
| 29 | `\recolor{t.row[99]}` OOB | `E1115` warn soft-drop | none (good) | Confirmed |
| 30 | `\apply{t}{row=…}` in prelude | renders as frame-0 data row | none (sensible) | Confirmed |
| **A6 · Equation** | | | | |
| 31 | dup `\term{rec}` across different lines | both addressable (`E.term[rec]` hits both) | none (matches doc) | Confirmed |
| 32 | `\term{}{x}` empty id | `E1532` "\term id '' is not an identifier" | none (good) | Confirmed |
| 33 | nested `\term{a}{\term{b}{x}}` | outer `term[a]` addressable; **inner `term[b]` silently NOT** (soft E1115 if used) | LOW-MED | Confirmed → **F6** |
| 34 | `\recolor{E.term[missing]}` | `E1115` warn soft-drop | none (good) | Confirmed |
| 35 | `lines=[]` empty | `E1530` "'lines' must be a non-empty list of strings" | none (good) | Confirmed |
| 36 | aligned line with no `&` | renders (single left segment) | none (defensible) | Confirmed |
| 37 | `\apply{E.line[99]}` OOB | `E1115` warn "invalid selector 'line[99]', ignoring set_value()" | none (good) | Confirmed |
| 38 | **`tex=` AND `lines=` both** | **silent**: lines wins, tex dropped, no warn | **MED** | Confirmed → **F5** |
| **A7 · live `\invariant`** | | | | |
| 39 | `${undefined_binding}` | renders `${undefined_binding}` **literally** (no warn) — but same as `\narrate` | LOW (consistent, pre-existing) | Confirmed → **F7** |
| 40 | `${s}` where s is a list | renders `s = [1, 2, 3]` (Python repr) | none (acceptable) | Confirmed |
| 41 | two `\invariant` | both stack (no E-code) | none (matches doc "lines stack") | Confirmed |
| 42 | `$math$` + `${sum}` mixed | KaTeX + `sum = 6` resolved | none (good) | Confirmed |
| **A8 · board-`\focus`** | | | | |
| 43 | `scope=board` with one shape | clean no-op (2 defocused = the focused cell's complement) | none (good) | Confirmed |
| 44 | `scope=board` in `\diagram` | `E1053` "…not allowed in the prelude" — misleading (no prelude in a diagram) | LOW (msg) | Confirmed |
| 45 | `scope=galaxy` (bad scope) | `E1122` "unknown focus scope 'galaxy'; valid: board, shape" | none (good) | Confirmed |

## Doc-example results (HUNT B — documented examples rendered verbatim)

All fragments wrapped in a minimal `animation` env; the only additions were shape decls for
shapes the fragment referenced but didn't declare (marked `% ADDED-WRAP`). Every example: **rc=0, no warning, behavior matches the doc's prose.**

| doc § | example | render | behavior verified |
|-------|---------|--------|-------------------|
| §7.21a | Equation tint one term | OK | `E.term[rec]` → current; siblings untouched |
| §7.21c | Equation reveal derivation | OK | `--dump-frames`: frame1 `{line[1]:idle, line[2]:hidden, term[rec]:current}`, frame2 `{line[1]:idle, line[2]:idle, term[rec]:current}` — line-by-line reveal **exactly as described** |
| §7.20 | TraceTable prefix-sum | OK | 2 data rows append; `t.cell[1][2]` → good |
| §5.16 | `\focus` shape vs board | OK | scope=shape frame = 2 defocused; scope=board frame = 5 defocused (dims the other shape too) |
| §5.17 | `\invariant` binsearch | OK | static + live panels stack; `${sum}` resolves per frame |
| §5.21 | `\note` re-issue | OK | n1 re-issued → shows "fixed" (not "careful"); n2 present |
| §5.22 | `\zoom` lean-in / pull-back | OK | per-frame viewBox `[128 4 76 56]` (crop to cell[2]) then `[0 0 332 64]` (full) |
| §12 | segtree lazy pushdown | OK | escaped-quote `arrow_from="st.node[\"[0,2]\"]"` **resolves** — 2 arc `<path>`s from `[0,2]`→children, no E1115 |
| §5.9 | `\trace` graph (BFS) | OK | polyline A→B→C→F + "BFS" label |
| §5.9 | `\trace` grid + Vietnamese | OK | 5-cell polyline + "lớp lẻ" label |
| §5.1 | `at=` grid board | OK | 3 arrays placed, viewBox 288×124 (2-col × 2-row) |

## Confirmed findings with repro

All repros: `.venv/bin/python render.py CASE.tex -o out.html` from repo root
(`SCRIBA_ALLOW_ANY_OUTPUT=1` only because the scratchpad is outside cwd).

### F1 — `\note` longer than the board silently clips off-canvas (no wrap, no warn) · **HIGH**
```latex
\begin{animation}[id="t"]
\shape{a}{Array}{size=5, data=[3,1,4,1,5]}     % ~332px board
\step
\note{n1}{text="careful: off-by-one — the window is half-open [lo, hi)", at=top-right}
\narrate{x}
\end{animation}
```
Rendered pill: `<rect x="…" width="380"/>` inside `viewBox="0 0 332 64"` → **56px (15%) off
the left edge**; the `<text>` is a single un-wrapped line; the stage `<svg class="scriba-stage-svg">`
carries no `overflow:visible`, so the excess is **clipped/invisible**. Anchor sets the
overflow direction (top-right → off-left; top-left → off-right, 919px pill at `x=8` in a
208px board = 78% clipped). rc=0, **no warning**. 85-char note → 45% clipped. The docs
(§5.21) say the note "paints inside the existing viewBox" — for any note wider than the board
it cannot, and it truncates the author's message silently. **Fix direction:** wrap the pill,
or clamp+ellipsize with a warning, or emit an E-code when the pill exceeds the board width.

### F2 — `at=[row,col]` has no upper bound → silent oversized/illegible board · **MED**
```latex
\shape{a}{Array}{size=3, data=[1,2,3], at=[0,0]}
\shape{b}{Array}{size=3, data=[4,5,6], at=[99,99]}   % or [100000,100000]
```
Each empty grid track reserves 20px, so viewBox scales linearly with the index and is
**uncapped**: `[1,1]`→412×124, `[10,10]`→592×304, `[99,99]`→**2372×2084**,
`[100000,100000]`→**2,000,392×2,000,104** (rc=0, 0.2s, no warning). Two 3-cell arrays sit in
opposite corners of a multi-megapixel canvas, illegible when scaled to a column; the SVG
ships `style="max-width:calc(2000392px * …)"`. `E1540` validates non-negative ints but there
is **no ceiling and no sparsity warning** — contrast the system's other caps (Graph 100 nodes
E1501, columns 1..64 E1522). A `\foreach`/`\compute`-generated or typo'd index silently
detonates the board. **Fix direction:** cap the board extent (or the empty-track count) with
an E-code, or collapse runs of empty tracks.

### F3 — two `\zoom` in one step: silent last-wins (vs `\focus` union) · **MED**
```latex
\shape{a}{Array}{size=5, data=[3,1,4,1,5]}
\shape{b}{Array}{size=5, data=[9,8,7,6,5]}
\step
\zoom{a}
\zoom{b}
```
`zoom{a}` alone → `viewBox="4 4 324 56"`; `zoom{b}` alone → `"4 64 324 56"`; **`zoom{a}` then
`zoom{b}` → `"4 64 324 56"`, byte-identical to `zoom{b}` alone** — `\zoom{a}` is silently
dropped. §5.22 calls `\zoom` "the camera twin of `\focus`", and §5.16 documents that multiple
`\focus` in one step **union**; an author expecting `\zoom` to frame the bounding box of both
regions gets only the last, with no warning and no documented rule. **Fix direction:** either
union the zoom targets (twin parity) or E-code a second `\zoom` in one step.

### F4 — `\annotate{shape}{…}` on a bare shape name is a silent no-op · **MED**
```latex
\annotate{a}{strike=true, color=error}   % whole-shape strike → nothing drawn, no warn
\annotate{a}{label="hi"}                 % same: no pill, no warn
```
Neither emits any `data-annotation` group nor any warning (scene annotations = `[]`), whereas
`\annotate{a.cell[1]}{label="hi"}` renders and `\annotate{a.all}`/`a.cell[9]` warn `E1119`.
The strike path (`scriba/animation/primitives/base.py:1197-1221`) only runs
`resolve_annotation_box` for targets that reach it; a bare-shape target is dropped upstream
before that, so — unlike `.all`/OOB — it produces **no E1119 and no visual**. Inconsistent
with `\zoom{a}`/`\focus{a}`, which resolve the same bare shape's box fine. The task's
"strike a whole shape" gesture therefore fails silently. **Fix direction:** either support
whole-shape annotation box (parity with zoom/focus) or warn E1119/E1115 like the sibling
targets.

### F5 — `Equation` accepts both `tex=` and `lines=`; silently drops `tex` · **MED**
```latex
\shape{E}{Equation}{tex="a=b", lines=["c &= d"]}
```
rc=0, **no warning**; the rendered mathml is the *lines* content (`c`, `d`) — `tex="a=b"`
vanishes. §7.21 states "Exactly one of `tex`/`lines` is required (**E1530**)"; supplying both
is contradictory input that should raise E1530 (or at least warn), not silently pick one.
**Fix direction:** raise E1530 when both are present.

### F6 — nested `\term{a}{\term{b}{x}}`: inner term silently non-addressable · **LOW-MED**
Only `scriba-term-a` is emitted; `\recolor{E.term[b]}` → `E1115` "does not match any
addressable part of 'E'". The KaTeX rewrite doesn't tag the inner `\term`, so a nested term
is silently un-addressable (degrades soft only if you try to use it). Edge usage; low blast
radius.

### F7 — live `\invariant` leaks an undefined `${}` literally · **LOW**
`\invariant{val = ${undefined_binding}}` renders `<p class="scriba-invariant">val =
${undefined_binding}</p>` — the raw placeholder is shown to the viewer, no warning. **But
`\narrate{… ${undefined_binding} …}` behaves identically** (also leaks literally), so this is
the pre-existing text-interpolation policy, not new to `\invariant`. Informational; consistent.

### Message-quality nits (LOW)
- `\zoom{}` → `E1010` "expected identifier, got EOF" — a raw selector-parser error; a
  `\zoom requires a target` hint (à la E1120 for `\note`) would be kinder.
- `E1521` (TraceTable row length) carries no line number, so a mid-timeline mismatch doesn't
  say *which* `\apply{t}{row=…}` is wrong (many E-codes do include `at line N`).
- `\focus` in a `\diagram` → `E1053` "…not allowed in the **prelude**" — misleading wording
  for a diagram author (a diagram has no prelude; compare E1054 for `\narrate`).

## Conclusion + Confidence

The 0.26.x surfaces are **crash-proof at the input boundary** — I could not produce a single
traceback leak; every malformed input is either a clean E-code or a soft warning, and the
error catalog is thorough and mostly well-worded. **The documented examples are all accurate**
(HUNT B: 11/11 render and behave as described, including the tricky escaped-quote segtree
`arrow_from`). The residual risk is entirely in the **silent lane**: one HIGH (`\note`
overflow silently truncates the author's message on ordinary-length notes) and four MED
silent-wrongs where contradictory/edge input is accepted with no diagnostic (`at=` uncapped
board, `\zoom` last-wins vs its `\focus` twin, bare-shape annotate no-op, Equation tex+lines).

**Confidence: High** for every row — all are Confirmed by direct render with cited viewBox
values, exact E-code strings, `--dump-frames` state, and one source cite
(`base.py:1197-1221`). Severity calls are the one judgment layer: F1 is HIGH because it
truncates real content at realistic lengths with zero feedback; the F2–F5 MEDs are "accepted
silently, defensible-by-design but trap-prone / doc-contradicting" rather than corrupt output.

### RETURN — counts by severity
- **CRITICAL (traceback leak): 0**
- **HIGH (silent wrong render): 1** — F1 `\note` overflow clip
- **MED (silent wrong / doc-contradicting): 4** — F2 `at=` uncapped board · F3 `\zoom` last-wins · F4 bare-shape annotate no-op · F5 Equation tex+lines
- **LOW: 3 + 3 nits** — F6 nested `\term` · F7 invariant `${}` leak · (14 empty-note) + zoom{} msg / E1521 no-line / focus-in-diagram msg
- **Doc bugs (HUNT B): 0** — all 11 documented new-surface examples render and match prose.

### Top 3 one-liners
1. **`\note` longer than the board width is silently clipped off-canvas** (no wrap, no warn) — a 54-char sentence loses 15% on a standard array board, a small board loses 84%.
2. **`at=[row,col]` is uncapped** — `at=[100000,100000]` silently yields a 2,000,392×2,000,104px viewBox (20px per empty track); a typo'd/computed index detonates the board with no warning.
3. **Two `\zoom` in one step is silent last-wins**, dropping the earlier target — even though its documented twin `\focus` *unions* multiple targets in one step.
