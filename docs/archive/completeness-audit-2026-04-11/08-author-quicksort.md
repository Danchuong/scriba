# Completeness Audit 8/14 — Quicksort (Lomuto Partition)

## Scope

Author-persona audit: build a Quicksort animation on an 8-element array
`[3,7,1,9,4,2,8,5]` using Scriba v0.5.1 (HEAD `eb4f017`) without modifying
`scriba/` or `examples/`. Output a single `.tex`, compile, iterate, and
report friction.

Target behaviors to visualize:

1. Initial array
2. Pivot selection (highlight last element)
3. Two-pointer sweep (`i`, `j`); when `a[j] < pivot`, swap `a[i], a[j]`,
   increment `i`
4. Each swap visualized via arrow + state change
5. Final pivot placement swap (`a[i+1] <-> a[hi]`)
6. Recursive call compressed into a secondary sub-array

## Algorithm

Standard Lomuto partition, pivot = last element. For the chosen input,
the trace reaches these intermediate mutations:

```
[3,7,1,9,4,2,8,5]  initial, pivot=5
[3,7,1,9,4,2,8,5]  j=0, a[0]=3 < 5, i=0, swap(0,0)
[3,7,1,9,4,2,8,5]  j=1, a[1]=7 >= 5, skip
[3,1,7,9,4,2,8,5]  j=2, a[2]=1 < 5, i=1, swap(1,2)
[3,1,4,9,7,2,8,5]  j=4, a[4]=4 < 5, i=2, swap(2,4)
[3,1,4,2,7,9,8,5]  j=5, a[5]=2 < 5, i=3, swap(3,5)
[3,1,4,2,5,9,8,7]  place pivot: swap(4,7)
```

Pivot index returned: `p = 4`. Left recursion: `[3,1,4,2]`.

## Final .tex (inline)

File: `/tmp/completeness_audit/08-quicksort.tex`

```latex
\begin{animation}[id="quicksort-lomuto", label="Quicksort -- Lomuto Partition"]
\shape{a}{Array}{size=8, data=[3,7,1,9,4,2,8,5], labels="0..7", label="$arr$"}
\shape{L}{Array}{size=4, data=[3,1,4,2], labels="0..3", label="$\mathrm{left}=a[0..3]$ (recurse)"}

\step
\narrate{Lomuto partition tren mang 8 phan tu ...}

\step
\recolor{a.cell[7]}{state=highlight}
\narrate{Chon pivot $= a[7] = 5$ ...}

\step
\recolor{a.cell[0]}{state=current}
\narrate{Khoi tao $i = -1$, $j = 0$ ...}

\step
\recolor{a.cell[0]}{state=good}
\narrate{$j=0$: $a[0]=3 < 5$. Tang $i \to 0$ ...}

\step
\recolor{a.cell[1]}{state=current}
\narrate{$j=1$: $a[1]=7 \not< 5$. Bo qua ...}

\step
\recolor{a.cell[2]}{state=current}
\annotate{a.cell[1]}{label="swap", arrow_from="a.cell[2]", color=warn}
\narrate{$j=2$: $a[2]=1 < 5$. Swap ...}

\step
\apply{a.cell[1]}{value=1}
\apply{a.cell[2]}{value=7}
\recolor{a.cell[1]}{state=good}
\recolor{a.cell[2]}{state=idle}
\reannotate{a.cell[1]}{color=muted, arrow_from="a.cell[2]"}
\narrate{Sau swap ...}

... (analogous pairs of steps for j=4, j=5, j=6, plus pivot placement) ...

\step
\recolor{L.cell[0]}{state=current}
\recolor{L.cell[1]}{state=current}
\recolor{L.cell[2]}{state=current}
\recolor{L.cell[3]}{state=current}
\narrate{De quy trai ...}
\end{animation}
```

Full file saved at `/tmp/completeness_audit/08-quicksort.tex` (105 lines,
19 `\step` blocks). Elision above is only to keep this doc under 3000
words; the real file is complete.

## Compile result

First attempt: failed.

```
[E1051] at line 98, col 1: \shape must appear before the first \step
    \shape{L}{Array}{size=4, data=[3,1,4,2], ...}
```

Root cause: I had declared the recursive-subarray `L` inside the last
`\step` block to model "a new primitive appearing later in the scene".
Scriba disallows that: all shapes must be declared before the first
`\step`. Fix was mechanical — hoist the `L` declaration to the preamble
and only drive its states from within a later step. 1-line diff.

Second attempt: clean.

```
Rendered 1 block(s) -> /tmp/completeness_audit/08-quicksort.html
```

No warnings, no deprecation messages. Output: 277 KB HTML, 19 steps,
2 arrays visible throughout.

## Friction points

### (a) How do you visualize a swap?

**Not atomic.** There is no `\swap{a.cell[i]}{a.cell[j]}` command. Every
swap requires **two separate** `\apply` calls:

```latex
\apply{a.cell[1]}{value=1}
\apply{a.cell[2]}{value=7}
```

That means the author is responsible for reading the pre-swap state,
mentally tracking both values, and writing them back in the correct
order. Nothing in the system prevents you from writing
`\apply{a.cell[1]}{value=7}` twice and silently corrupting the array.

I also chose to split the swap across two `\step` blocks: step N shows
the intent (highlight + arrow labelled "swap"), step N+1 commits the
value change. This doubles the step count but it is the only way to
make the operation legible without dedicated before/after framing.

### (b) Pointers `i` and `j`

There is **no pointer primitive** on arrays. `\cursor` moves a named
cursor along a target list, but it only recolors one cell at a time
with `prev_state`/`curr_state`; it does not draw a labelled caret
under the array, and there is no way to say "the `i` pointer lives
here and the `j` pointer lives there" simultaneously.

I fell back to:

- `state=current` for `j` (the walking pointer)
- `state=good` for cells `0..i` (the "less-than-pivot" region)
- Prose in `\narrate` to tell the reader which index is `i` and which
  is `j`

This is lossy. A reader who scrubs through silent frames cannot tell
that one `current` cell represents `j` and the adjacent `good` block
represents the `<pivot` region maintained by `i`. `\annotate` with
arrows could simulate pointers, but annotations sit above the array
and are for *inter-cell* relationships, not *which-cell-am-I-on*
labels. I tried adding an arrow from `j` to `i` and it read as a swap
arrow, not a pointer label.

### (c) Comparison visualization

There is **no `compare_highlight`** or paired-comparison primitive. The
Array primitive exposes `\recolor`, `\apply`, `\annotate`, `\highlight`,
and `\cursor`, none of which express "these two cells are being
compared right now". I could not find a way to visually yoke `a[j]`
and `a[hi]` (the pivot) together during each comparison. The only
workable idiom is: leave the pivot at `state=highlight` permanently and
drive `j` through `state=current`. That does render, but the "compare"
semantic lives entirely in the narration, not in the animation.

### (d) Step count for 8 elements

19 steps, 105 lines of `.tex`. Breakdown:

- 1 intro
- 1 pivot select
- 1 pointer init
- 4 non-swap inner-loop steps (each skip or no-op swap is 1 step)
- 4 swap intents × 2 steps each (intent + commit) = 8 steps
- 2 pivot-placement steps
- 1 recursion frame
- + `narrate`-only wrappers

For a textbook-simple 8-element Lomuto trace, that is verbose. If the
input had been 16 elements it would exceed 40 steps. There is no
`\foreach`-based escape hatch that I could see for "loop body with
conditional swap", because `\apply` needs literal values per cell and
`\compute` bindings are evaluated per-step, not threaded across iterations.
An author writing a Quicksort explainer essentially has to unroll the
loop by hand, which is exactly the foreach-unroll friction flagged on
the convex-hull run.

## Feature requests

1. **`\swap{a.cell[i]}{a.cell[j]}`** — atomic two-cell swap that reads
   current values and writes them back transposed. Eliminates the
   class of bugs where the author hand-writes the wrong pair of
   `\apply` calls. Would also cut swap visualization from 2 steps to
   1 while preserving the "intent then commit" feel via an optional
   `transition=highlight` or `via=arrow` flag.

2. **Pointer annotations on arrays** — something like
   `\pointer{p1}{a}{index=3, label="i"}` that renders a labelled caret
   (^) under the array and can be moved with
   `\move{p1}{index=4}`. This is orthogonal to `state=current` and
   would let authors show `i` and `j` simultaneously without
   hand-rolling arrows.

3. **Inline compare primitive** — `\compare{a.cell[j]}{a.cell[hi]}`
   that transiently tints both cells and optionally draws a thin
   comparator line between them for the duration of a single step.
   Would make binary-search, heap-sift, partition, and merge-sort
   animations dramatically more legible.

4. **Loop-body state machine or templated swap sequence** — extend
   `\foreach` to accept compute-bound conditionals so a partition
   sweep can be written once. Even a small `\if` + `\swap` would
   remove the hand-unroll.

5. **Deferred `\shape` declarations** — allow declaring a shape inside
   a `\step` with the semantic "appears from this step onward".
   Required for "recursion visualizer" and "new frame appears" idioms.
   The current E1051 is a legitimate guardrail, but it forces all
   recursive-call frames to be pre-declared at idle, which clutters
   step 1.

## Author effort

- Reading existing `foreach_demo.tex` + `frog1_dp.tex` to learn array
  idioms: ~3 minutes.
- Checking `array.py` for supported operations (no swap, no pointer,
  no compare): ~2 minutes.
- Writing initial `.tex`: ~8 minutes.
- First compile + E1051 fix: ~1 minute, 1-line change.
- Second compile: clean.
- Total: ~15 minutes for a 19-step, single-array-with-recursion
  animation. Most of the time was spent hand-unrolling the swap
  sequences and picking states that could carry "pointer" semantics.

## Severity summary

| Issue | Severity | Notes |
|---|---|---|
| No `\swap` primitive; manual paired `\apply` | HIGH | Correctness hazard; authors can silently corrupt state |
| No pointer primitive for `i`/`j` | HIGH | Core idiom for any two-pointer algorithm is missing |
| No inline compare visualization | MEDIUM | Degrades binary-search / partition / merge explainers |
| Shape-before-step guardrail (E1051) for recursive frames | MEDIUM | Fine as a rule, but forces pre-declaration of all recursive sub-arrays |
| Step verbosity for unrolled loops | MEDIUM | 19 steps for 8 elements; doesn't scale |
| Foreach can't express conditional-swap loop body | MEDIUM | Related to item 1; blocks the obvious refactor |
| No deprecation warnings, no silent fixes hit this run | LOW | `\apply`/`\recolor`/`\reannotate` behaved cleanly |

**Overall:** The animation *can* be built, and on the second try it
compiled cleanly with no warnings, which is an improvement over the
convex-hull run. But Quicksort — the canonical "simplest interesting
array algorithm" — exposes that Scriba's Array primitive currently
models **cells and colors**, not **operations and pointers**. The two
most common array idioms in an algorithms course (swap, two-pointer)
are not first-class, and the workarounds push authors toward verbose,
bug-prone hand-unrolls.
