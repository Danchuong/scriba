# Example 11 — Manual step unroll for per-iteration frames

> Showcase: the **loop-to-step bridge pattern** for algorithms that need
> one frame per iteration. Scriba deliberately does not allow `\step`
> inside `\foreach` (see `ruleset.md §2.1`), so algorithms whose frame
> structure mirrors an inner loop — monotonic stacks, amortized walks,
> two-pointer sweeps — must be **manually unrolled**. This recipe shows
> the pattern on "next greater element" with a monotonic stack.

## Why `\step` is forbidden inside `\foreach`

A `\foreach` block expands to a flat sequence of mutation commands
**within a single step**, not to one step per iteration (→ `E1172`).
The design rationale is that the emitter cannot know the iteration
count at parse time for `${binding}` iterables, so it cannot reserve a
predictable number of frames. A bridge construct that composes
`\foreach` with `\step` is tracked for a future release.

Until then, algorithms with per-iteration frames follow this pattern:

1. Run the full algorithm inside a `\compute{}` block to pre-compute
   the complete event trace.
2. Manually write one `\step` per trace entry.
3. Inside each `\step`, use `\foreach` freely for **fanout** within
   that frame — for example, recoloring a whole range of cells at
   once, or iterating over the current stack contents to redraw them.

The compute block is the single source of truth for iteration
**count**; the editorial author is responsible for keeping the
hand-unrolled `\step` count in sync with the trace length. For small
algorithms (≤ 20 iterations) this is cheap. For larger walks, fall
back to `figure-embed` with a pre-rendered filmstrip.

## Worked example — next greater element

Given an array `a = [2, 1, 5, 6, 2, 3]`, compute `next_greater[i]` =
the nearest index `j > i` with `a[j] > a[i]` (or `-1`). A monotonic
decreasing stack produces this in O(n), with one pop or push per
visit.

```latex
\begin{animation}[id=nge-mono-stack, label="Next greater via monotonic stack"]
  \compute{
    a = [2, 1, 5, 6, 2, 3]
    n = len(a)
    nge = [-1] * n
    stack = []          # holds indices, a[stack[-1]] is monotonic decreasing
    events = []
    for i in range(n):
        # Pop while current beats top of stack.
        while stack and a[stack[-1]] < a[i]:
            top = stack[-1]
            stack = stack[:-1]
            nge[top] = i
            events.append({"op": "pop", "i": i, "popped": top, "stack": list(stack)})
        stack.append(i)
        events.append({"op": "push", "i": i, "stack": list(stack)})
  }

  \shape{arr}{Array}{size=6, data=${a}, label="a[i]"}
  \shape{s}{Stack}{orientation="horizontal", max_visible=6, label="mono-stack (indices)"}

  % Frame 0: i=0, push 0. Stack: [0].
  \step
    \recolor{arr.cell[0]}{state=current}
    \apply{s}{push="0"}
    \narrate{$i = 0$: stack empty, push index 0. Stack: $[0]$.}

  % Frame 1: i=1, a[1]=1 < a[0]=2, so no pop. Push 1. Stack: [0,1].
  \step
    \recolor{arr.cell[0]}{state=done}
    \recolor{arr.cell[1]}{state=current}
    \apply{s}{push="1"}
    \narrate{$i = 1$: $a[1]=1 < a[0]=2$, no pop. Push 1. Stack: $[0,1]$.}

  % Frame 2: i=2, a[2]=5 beats a[1]=1 and a[0]=2. Two pops then push.
  \step
    \recolor{arr.cell[1]}{state=done}
    \recolor{arr.cell[2]}{state=current}
    \apply{s}{pop=2}
    \apply{s}{push="2"}
    \annotate{arr.cell[1]}{label="nge=2", arrow_from=arr.cell[2], color=good}
    \annotate{arr.cell[0]}{label="nge=2", arrow_from=arr.cell[2], color=good}
    \narrate{$i = 2$: $a[2]=5$ pops indices 1 then 0 (both smaller). $\text{nge}[1]=\text{nge}[0]=2$. Push 2. Stack: $[2]$.}

  % Frame 3: i=3, a[3]=6 beats a[2]=5. One pop, then push.
  \step
    \recolor{arr.cell[2]}{state=done}
    \recolor{arr.cell[3]}{state=current}
    \apply{s}{pop=1}
    \apply{s}{push="3"}
    \annotate{arr.cell[2]}{label="nge=3", arrow_from=arr.cell[3], color=good}
    \narrate{$i = 3$: $a[3]=6$ pops index 2. $\text{nge}[2]=3$. Push 3. Stack: $[3]$.}

  % Frame 4: i=4, a[4]=2 < 6, no pop. Push.
  \step
    \recolor{arr.cell[3]}{state=done}
    \recolor{arr.cell[4]}{state=current}
    \apply{s}{push="4"}
    \narrate{$i = 4$: $a[4]=2 < 6$, no pop. Push 4. Stack: $[3,4]$.}

  % Frame 5: i=5, a[5]=3 beats a[4]=2. One pop, then push.
  \step
    \recolor{arr.cell[4]}{state=done}
    \recolor{arr.cell[5]}{state=current}
    \apply{s}{pop=1}
    \apply{s}{push="5"}
    \annotate{arr.cell[4]}{label="nge=5", arrow_from=arr.cell[5], color=good}
    \narrate{$i = 5$: $a[5]=3$ pops index 4. $\text{nge}[4]=5$. Push 5. Stack: $[3,5]$.}

  % Final frame: highlight any indices still on the stack — they have nge = -1.
  \step
    \recolor{arr.cell[5]}{state=done}
    \foreach{idx}{[3,5]}
      \recolor{arr.cell[${idx}]}{state=warn}
    \endforeach
    \narrate{End of walk. Indices remaining on the stack have no next greater: $\text{nge}[3]=\text{nge}[5]=-1$.}
\end{animation}
```

## Pattern checklist

- **One `\step` per inner-loop iteration you want visualized.** If the
  while-pop collapses multiple pops into a single visual frame (as in
  frame 2 above), call that out explicitly in the narration so the
  reader expects the compound transition.
- **Use `\foreach` for fanout within a step.** The final frame above
  uses `\foreach{idx}{[3,5]}` to recolor every remaining-on-stack
  index without writing N `\recolor` lines by hand. This is legal
  because the loop expands inside a single frame, not across frames.
- **Keep the `\compute` block authoritative.** Author-level state
  (`stack`, `nge`, `events`) is computed once. Hand-unrolled `\step`
  commands reference the computed values via `${...}` bindings or
  hard-coded numbers for narration.
- **If the iteration count is not known at authoring time**, fall back
  to `figure-embed` with a pre-generated filmstrip; Scriba does not
  support parametric step counts today.

## Related

- `ruleset.md §2.1` — the `\step` ∉ `\foreach` rule and rationale.
- `06-frog1-dp/` — a DP walk with fixed frame count (one per DP cell).
- `03-animated-bfs/` — BFS walkthrough using `\compute` + manual
  `\step` unroll.
