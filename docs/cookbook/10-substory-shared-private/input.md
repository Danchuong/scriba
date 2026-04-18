# Example 10 — Substory with shared and private primitives

> Showcase: the **substory shared/private pattern**. A parent animation
> declares shapes that are visible to both the outer steps and any
> substory. A substory declares its own private shapes that exist only
> for the duration of that sub-computation. When the substory closes,
> parent shape state is fully restored and private shapes disappear.
>
> **Problem**: Given an array `a = [3, 1, 4, 1, 5]`, find the minimum
> and maximum values. Use a sub-linear divide-and-conquer approach where
> each recursive call is shown as a substory.

## Pattern: shared vs private shapes

| Shape declared in | Visible inside substory | Mutations revert on close |
|---|---|---|
| Parent animation prelude | Yes | Yes — parent state is saved/restored |
| Substory prelude (`\substory` ... first `\step`) | No (private) | N/A — shape ceases to exist |

This separation lets you "point at" parent data from inside a substory
(the highlight unwinds cleanly) while keeping substory-internal scratch
shapes from polluting the parent's display.

## What the author writes

```latex
\begin{animation}[id="substory-shared-private",
                  label="Min/Max via divide-and-conquer substories"]
\shape{a}{Array}{size=5, data=[3,1,4,1,5], labels="0..4", label="$a$"}
\shape{result}{VariableWatch}{names=["min","max"], label="result"}

\step
\narrate{We want the minimum and maximum of $a = [3,1,4,1,5]$.
         We will split the array into left and right halves and solve
         each half as a sub-computation.}

\step
\recolor{a.cell[0]}{state=current}
\recolor{a.cell[1]}{state=current}
\recolor{a.cell[2]}{state=current}
\narrate{Left half: $a[0..2] = [3,1,4]$. Running sub-computation.}
\substory[title="Left half min/max: a[0..2]", id="left-half"]
\shape{sub}{Array}{size=3, data=[3,1,4], labels="0..2", label="$a[0..2]$"}

\step
\recolor{sub.cell[0]}{state=current}
\narrate{Candidate min = 3, max = 3. Start scanning.}

\step
\recolor{sub.cell[0]}{state=done}
\recolor{sub.cell[1]}{state=current}
\narrate{$a[1] = 1 < 3$. Update min = 1.}

\step
\recolor{sub.cell[1]}{state=done}
\recolor{sub.cell[2]}{state=current}
\narrate{$a[2] = 4 > 3$. Update max = 4.}

\step
\recolor{sub.all}{state=done}
\narrate{Left half result: min = 1, max = 4.}

\endsubstory

\step
\apply{result.var[min]}{value=1}
\apply{result.var[max]}{value=4}
\recolor{a.cell[0]}{state=dim}
\recolor{a.cell[1]}{state=dim}
\recolor{a.cell[2]}{state=dim}
\narrate{Left half done. Parent array state is restored (no blue cells
         from inside the substory leak out). We record min=1, max=4.}

\step
\recolor{a.cell[3]}{state=current}
\recolor{a.cell[4]}{state=current}
\narrate{Right half: $a[3..4] = [1,5]$. Running sub-computation.}
\substory[title="Right half min/max: a[3..4]", id="right-half"]
\shape{sub}{Array}{size=2, data=[1,5], labels="3..4", label="$a[3..4]$"}

\step
\recolor{sub.cell[0]}{state=current}
\narrate{Candidate min = 1, max = 1. Start scanning.}

\step
\recolor{sub.cell[0]}{state=done}
\recolor{sub.cell[1]}{state=current}
\narrate{$a[4] = 5 > 1$. Update max = 5. Min unchanged.}

\step
\recolor{sub.all}{state=done}
\narrate{Right half result: min = 1, max = 5.}

\endsubstory

\step
\apply{result.var[max]}{value=5}
\recolor{a.cell[3]}{state=dim}
\recolor{a.cell[4]}{state=dim}
\narrate{Right half done. Global max is now 5 (larger than left-half max).
         Final answer: min = 1, max = 5.}
\end{animation}
```

## How the shared/private split works

### Shared shapes (`a`, `result`)

Both `a` (the main array) and `result` (the variable watch) are declared
in the parent prelude, so they exist for the entire animation lifetime.
Inside each substory they are visible and can be recolored -- but any
changes are reverted when `\endsubstory` closes. This is what lets the
outer `\step` after each substory see a clean parent array (all cells
`idle`/`dim`) even though the substory turned some cells `current` or
`done` internally.

### Private shapes (`sub`)

Each substory declares its own `sub` array in its own prelude (between
`\substory` and the first `\step` inside it). This shape is entirely
private: it does not appear in the parent frame, it does not conflict
with the other substory's `sub` shape (they are scoped separately), and
it vanishes when `\endsubstory` closes.

Because both substories happen to use the same name `sub`, this also
demonstrates that private shape names are **substory-scoped** -- there
is no name collision between the two substories.

## Pattern checklist

- **Declare shared context in the parent prelude.** Anything that
  persists across the whole animation (running result, the original
  input array, a code panel) belongs in the parent prelude.
- **Declare scratch state in the substory prelude.** Temporary shapes
  that exist only for the sub-computation (a sub-array, a local stack,
  a candidate variable) go between `\substory` and the first inner
  `\step`. They will not be visible before or after the substory.
- **Mutations to parent shapes inside a substory unwind automatically.**
  You do not need to manually undo them; the renderer saves and restores
  parent state around every substory block.
- **Reference parent `\compute` bindings freely.** Bindings set in the
  parent prelude (e.g., `heights`, `n`) are accessible inside the
  substory via `${...}` interpolation.
- **Keep nesting depth at most 3.** A substory may itself contain
  substories (up to depth 3 total, → `E1360`). Beyond depth 1, label
  headers clearly so the reader knows which level they are on.

## Constraints summary

| Constraint | Error |
|---|---|
| `\substory` outside a `\step` | E1362 |
| Nesting depth > 3 | E1360 |
| `\substory` or `\endsubstory` not on their own line | E1368 |
| `\endsubstory` without matching `\substory` | E1365 |
| Unclosed `\substory` (EOF or parent step boundary reached) | E1361 |
| Substory with zero inner `\step` blocks | E1366 (warning) |

## Related

- `examples/primitives/substory.tex` -- minimal single-substory example.
- `docs/tutorial/getting-started.md §11` -- tutorial introduction to `\substory`.
- `spec/ruleset.md §7.2` -- full `\substory` spec (E4).
- `11-loop-to-step-manual-unroll.md` -- companion pattern: when you
  need per-iteration frames in the *outer* animation rather than
  per-iteration sub-computations.
