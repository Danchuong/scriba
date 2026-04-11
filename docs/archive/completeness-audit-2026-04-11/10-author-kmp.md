# Completeness Audit 10/14 — KMP Failure Function (Author Simulation)

## Scope

Simulate an editorial author building a KMP failure-function animation for
pattern `ABABCABAB` (9 chars) using only existing Scriba v0.5.1 primitives and
ruleset. Focus on string/array primitive ergonomics with two synchronized
pointers (`i` and `k`) and an incrementally built secondary array (`fail[]`).
No modifications to `scriba/` or `examples/`.

## Algorithm (reference)

```
f[0] = 0
i = 1, k = 0
while i < n:
    if P[i] == P[k]: k += 1; f[i] = k; i += 1
    elif k > 0:      k = f[k-1]           # fall back
    else:            f[i] = 0; i += 1
```

Trace on `ABABCABAB`:

| i | k (entry) | P[i] vs P[k] | action       | f[i] | k (exit) |
|---|-----------|--------------|--------------|------|----------|
| 0 | —         | —            | base         | 0    | 0        |
| 1 | 0         | B vs A       | mismatch,k=0 | 0    | 0        |
| 2 | 0         | A vs A       | match        | 1    | 1        |
| 3 | 1         | B vs B       | match        | 2    | 2        |
| 4 | 2         | C vs A       | mismatch     | —    | f[1]=0   |
| 4 | 0         | C vs A       | mismatch,k=0 | 0    | 0        |
| 5 | 0         | A vs A       | match        | 1    | 1        |
| 6 | 1         | B vs B       | match        | 2    | 2        |
| 7 | 2         | A vs A       | match        | 3    | 3        |
| 8 | 3         | B vs B       | match        | 4    | 4        |

Final `f = [0,0,1,2,0,1,2,3,4]`.

## Layout decision + rationale

Two independent `Array` primitives stacked vertically:

1. `pat` — size 9, `data=["A","B","A","B","C","A","B","A","B"]`, caption
   `pattern $P$`.
2. `fail` — size 9, `data=[0,0,0,0,0,0,0,0,0]`, caption `failure $f$`.

Rationale:

- Scriba `Array` cells accept arbitrary strings in `data`, so character labels
  are native — no special "char array" mode needed.
- Multi-shape scenes auto-stack vertically in document order, and both arrays
  have the same size (9) so cell columns visually align out of the box. The
  rendered cell width is dynamic (`max(CELL_WIDTH, max_content_w+12,
  max_label_w+8)`), and since content is a single char or single digit the
  widths match across both arrays without manual tuning.
- A single composite primitive (matrix / dptable) would misrepresent the data:
  `pat` is an immutable input and `fail` is the evolving output. Keeping them
  separate makes the state semantics obvious (`pat` cells go `idle → done`;
  `fail` cells go `idle → current → done` as values are committed).

Pointer strategy:

- `i` (scan pointer on `pat`) — use `\cursor{pat.cell}{i}`, which assigns
  `curr_state=current` and auto-dims the prior position.
- `k` (matched-prefix pointer, also on `pat`) — use `\highlight{pat.cell[k]}`,
  which paints a dashed gold overlay. `highlight` is ephemeral per step, so
  no manual cleanup. This gives two visually distinct markers on the same
  row without needing a dedicated pointer primitive.
- Mismatch fallback steps (`k = f[k-1]`) get their own `\step`, leaving `i`
  pinned and moving only the `k` highlight — the viewer sees the fallback
  explicitly.

## Final .tex (inline)

```tex
\begin{animation}[id="kmp-failure", label="KMP failure function for ABABCABAB"]
\shape{pat}{Array}{size=9, data=["A","B","A","B","C","A","B","A","B"], labels="0..8", label="pattern $P$"}
\shape{fail}{Array}{size=9, data=[0,0,0,0,0,0,0,0,0], labels="0..8", label="failure $f$"}

\step
\narrate{KMP failure function: $f[i]$ is the length of the longest proper
prefix of $P[0..i]$ that is also a suffix. We build $f$ left to right with
two pointers: $i$ scans $P$, $k$ tracks the current matched prefix length.}

\step
\recolor{pat.cell[0]}{state=done}
\recolor{fail.cell[0]}{state=done}
\narrate{Base case: $f[0] = 0$.}

\step
\cursor{pat.cell}{1}
\highlight{pat.cell[0]}
\recolor{fail.cell[1]}{state=current}
\narrate{$i=1$, $k=0$. B vs A, mismatch with $k=0$: $f[1]=0$, advance $i$.}

\step
\recolor{fail.cell[1]}{state=done}
\cursor{pat.cell}{2}
\highlight{pat.cell[0]}
\recolor{fail.cell[2]}{state=current}
\narrate{$i=2$, $k=0$. A vs A, match: $k \leftarrow 1$, $f[2]=1$.}

\step
\apply{fail.cell[2]}{value=1}
\recolor{fail.cell[2]}{state=done}
\cursor{pat.cell}{3}
\highlight{pat.cell[1]}
\recolor{fail.cell[3]}{state=current}
\narrate{$i=3$, $k=1$. B vs B, match: $k \leftarrow 2$, $f[3]=2$.}

\step
\apply{fail.cell[3]}{value=2}
\recolor{fail.cell[3]}{state=done}
\cursor{pat.cell}{4}
\highlight{pat.cell[2]}
\recolor{fail.cell[4]}{state=current}
\narrate{$i=4$, $k=2$. C vs A, mismatch: $k \leftarrow f[1] = 0$.}

\step
\cursor{pat.cell}{4}
\highlight{pat.cell[0]}
\recolor{fail.cell[4]}{state=current}
\narrate{Still $i=4$, now $k=0$. C vs A, mismatch with $k=0$: $f[4]=0$.}

\step
\recolor{fail.cell[4]}{state=done}
\cursor{pat.cell}{5}
\highlight{pat.cell[0]}
\recolor{fail.cell[5]}{state=current}
\narrate{$i=5$, $k=0$. A vs A, match: $k \leftarrow 1$, $f[5]=1$.}

\step
\apply{fail.cell[5]}{value=1}
\recolor{fail.cell[5]}{state=done}
\cursor{pat.cell}{6}
\highlight{pat.cell[1]}
\recolor{fail.cell[6]}{state=current}
\narrate{$i=6$, $k=1$. B vs B, match: $k \leftarrow 2$, $f[6]=2$.}

\step
\apply{fail.cell[6]}{value=2}
\recolor{fail.cell[6]}{state=done}
\cursor{pat.cell}{7}
\highlight{pat.cell[2]}
\recolor{fail.cell[7]}{state=current}
\narrate{$i=7$, $k=2$. A vs A, match: $k \leftarrow 3$, $f[7]=3$.}

\step
\apply{fail.cell[7]}{value=3}
\recolor{fail.cell[7]}{state=done}
\cursor{pat.cell}{8}
\highlight{pat.cell[3]}
\recolor{fail.cell[8]}{state=current}
\narrate{$i=8$, $k=3$. B vs B, match: $k \leftarrow 4$, $f[8]=4$.}

\step
\apply{fail.cell[8]}{value=4}
\recolor{fail.cell[8]}{state=done}
\recolor{pat.all}{state=path}
\recolor{fail.all}{state=path}
\narrate{Final $f = [0,0,1,2,0,1,2,3,4]$; longest proper prefix-suffix of
ABABCABAB has length 4 (ABAB).}
\end{animation}
```

Full file at `/tmp/completeness_audit/10-kmp.tex`.

## Compile result

First-try clean compile:

```
$ uv run python render.py /tmp/completeness_audit/10-kmp.tex \
    -o /tmp/completeness_audit/10-kmp.html
Rendered 1 block(s) -> /tmp/completeness_audit/10-kmp.html
```

- No warnings, no errors.
- Output: 237 KB HTML, 13 steps total.
- Log file: `/tmp/completeness_audit/10-kmp.log` (single success line).

Zero iteration cycles required — the `frog1_dp.tex` cookbook pattern
translated directly, and `\highlight` worked as a second pointer without any
fights with the `curr_state` machinery of `\cursor`.

## Friction points

1. **No cross-primitive arrow annotations.** `\annotate{fail.cell[i]}{
   arrow_from="pat.cell[k]"}` would be the natural way to draw a "k compares
   to i" arc, but `arrow_from` is resolved inside a single primitive
   (`_cell_center` only matches `self.shape_name`). I wanted to show the
   "compare" relationship visually and had to fall back to prose in
   `\narrate`.
2. **No built-in labeled pointer variable outside VariableWatch.** There is
   no dedicated "pointer" primitive — I reuse `\cursor` (current-state) and
   `\highlight` (dashed overlay). It works, but semantically both markers are
   "a cell is highlighted" rather than "a named pointer lives here". A
   reader has to be told in `\narrate` which mark is `i` and which is `k`.
3. **No composite string primitive.** A `String` primitive with per-character
   selectors and twin pointer slots would replace the `pat` Array plus
   cursor/highlight juggling. Today `Array{data=["A","B",...]}` works fine
   but is cosmetically a row of boxes, not a typeset string.
4. **Repetitive per-cell narration.** The 9-char pattern expanded to 12
   substantive `\step` blocks (1 intro + 1 base + 9 iterations + 1 fallback
   sub-step + 1 finale). The fallback case forced an extra step because
   `k = f[k-1]` and the re-compare must be separate frames. For a 20-char
   pattern with many fallbacks this would balloon to 40+ steps. A
   `\substory` block per character (or a compute-driven loop that walks the
   state machine) would cut the authoring time in half.
5. **No "compare highlight" state.** I wanted a color that means "these two
   cells are being compared right now". The existing states (`current`,
   `done`, `path`, etc.) don't capture "comparison pair". Using
   `\cursor` + `\highlight` on two cells of the same array is the best
   approximation but it conflates "cursor position" with "comparison".
6. **Character values don't auto-center nicely with labels.** Not a problem
   here — dynamic cell width handles single chars and single digits
   identically — but if the pattern contained wider strings (e.g. words in a
   word-level KMP), the `fail` digit row would be much narrower and the two
   arrays would stop aligning column-wise.

## Feature requests

1. **Cross-primitive `arrow_from`.** Let `\annotate{fail.cell[i]}{
   arrow_from="pat.cell[k]"}` resolve against any shape by fully-qualifying
   the prefix. This would light up KMP, two-pointer problems, hash-table
   probing, linked-list pointer walks, graph adjacency visuals, etc.
2. **Dual-array sync / grouping.** A `\group{pat, fail}` or
   `layout=stacked` option that guarantees both primitives render with
   identical per-cell widths so columns align even when content widths
   differ. Cheap version: a `cell_width=` override on `Array`.
3. **Named pointer primitive / attribute.** Something like
   `\pointer{i}{pat.cell[4]}` that draws a labeled tick mark above the cell
   with the pointer's name. This would make `i` and `k` visually distinct
   without needing two different recolor states and without relying on
   dashed-overlay conventions the reader has to learn.
4. **`String` primitive.** A variant of Array whose default rendering is
   typeset glyphs with thin separators rather than outlined boxes, so
   `pat` reads like `A B A B C A B A B` with index ticks beneath. Selectors
   stay `.cell[i]` for parity.
5. **`compare` state or `\compare{a}{b}{color}` command.** Paints a matched
   style on both cells for one step (ephemeral), so match vs mismatch is
   visually unambiguous without co-opting `current` + `highlight`.
6. **Compute-driven step expansion.** A `\loop` or `\trace` helper that
   takes an algorithm closure / Starlark worker output and emits one step
   per iteration, eliminating the 9× `\step` copy-paste for incremental
   array construction. The existing Starlark worker infra (per
   `docs/spec/starlark-worker.md`) already computes DP tables; letting the
   cookbook author drive step emission from that same computation would be
   the biggest ergonomics win.

## Author effort

- Research & reading: ~10 min (array primitive source, ruleset §`\cursor` /
  `\highlight`, `frog1_dp.tex` reference).
- Algorithm trace + layout decision: ~5 min.
- Writing the .tex: ~10 min (13 steps, copy-paste with small index edits).
- Compile + verify: <1 min, clean first try.

Total: ~25 min. The fact that the `frog1_dp.tex` cookbook existed with a
two-array DP pattern was decisive — it provided a direct template. An author
starting cold would likely spend 60+ min figuring out that `\cursor` +
`\highlight` was the canonical two-pointer idiom.

## Severity summary

| # | Issue                                         | Severity | Blocker? |
|---|-----------------------------------------------|----------|----------|
| 1 | No cross-primitive `arrow_from`               | Medium   | No       |
| 2 | No dedicated pointer primitive                | Low      | No       |
| 3 | No `String` primitive (cosmetic)              | Low      | No       |
| 4 | Per-step narration boilerplate for long input | Medium   | No       |
| 5 | No compare / pair state                       | Low      | No       |
| 6 | Column alignment fragile under mixed widths   | Low      | No       |

**Overall:** Scriba handles the KMP failure-function animation cleanly with
existing primitives. Nothing blocks authoring; the friction is
ergonomic / cosmetic, concentrated in (a) cross-primitive arrows and (b)
scaling to longer patterns without boilerplate. The `\cursor` + `\highlight`
combo is the canonical two-pointer idiom today and works, but it's an
undocumented convention the author has to discover.
