# Editorial Principles v2 — Authoring Scriba Environments

> This is a taste document, not a mechanics document. For grammar, commands,
> primitives, states, and error codes, read
> [`environments.md`](../spec/environments.md). This file is about
> *when* and *why* to reach for `\begin{animation}`, and how to write it
> so the result feels inevitable rather than decorated.

The spirit is Tufte: **show the thing itself, label it honestly, remove
anything that is not doing work.** But the mechanics have changed. You are
no longer writing a DSL. You are writing LaTeX, and `animation` is a new
environment that sits alongside `tabular`, `equation`, and `tikzpicture`
in the same `.tex` file. Treat it with the same discipline.

> **v0.5.x status:** `\begin{animation}` is the production environment.
> `\begin{diagram}` is **reserved for extension E5** and is not a
> first-class IR in v0.5.x; a `\begin{diagram}` block is rendered as a
> single-frame `AnimationIR` in diagram mode (see `ruleset.md` §1.1). New
> authoring should prefer `\begin{animation}` with a single implicit
> frame until E5 lands.

## 1. First, ask whether you need a picture at all

A picture earns its place when **the reader cannot follow the prose without
it.** Not when the problem "looks empty." Not when you are worried the
learner is bored. Not to prove that Scriba exists.

Before you open `\begin{animation}`, try:

1. **A precise sentence.** "For each $i \ge 2$, we take the cheaper of
   jumping from $i-1$ or from $i-2$." Many problems are done at this line.
2. **A single display-math equation.** If the recurrence is the whole
   story, show the recurrence.
3. **A small table** inside a `tabular`. If the reader only needs to
   *read values*, they do not need an animation.
4. **A single-frame `\begin{animation}`** — one implicit frame, one
   figure. If the shape of the structure is what matters (a binary tree,
   a grid, an interval), you do not need multi-step frames.
5. **Only then** consider a multi-step `\begin{animation}`. Animations
   earn their place when *the change over time* is the point: filling a
   DP table, shrinking a binary search window, contracting a BFS
   frontier.

If you cannot write the caption for frame 1 without saying "this is just
the starting state," you probably do not need multiple frames — you
need a single-frame figure.

## 2. Single-frame vs multi-step animations: a clean split

| Use a single-frame animation when… | Use a multi-step animation when… |
|---|---|
| The structure is static and the reader only needs to *see it once*. | The structure *evolves* and the evolution is the lesson. |
| A single well-labelled figure would suffice on paper. | Each step adds a new invariant the reader must track. |
| You would otherwise draw it in TikZ as one picture. | You would otherwise make a GIF or a short screen recording. |
| Examples: recursion tree, input grid, interval layout, initial graph. | Examples: DP fill order, BFS frontier, binary search shrink, segment tree query walk. |

Default bias: **prefer fewer frames**. A static figure asks less of the
reader's attention and more of your own craft. Reach for multi-step
frames only when the reader would genuinely need to flip back and forth
between states to understand the algorithm.

## 3. Narration that earns its place

Each `\step` in an `animation` must contain exactly one `\narrate{...}`.
Treat that sentence as the single most important thing in the frame.

**Bad narration** repeats what the picture already shows:

> Now we fill in cell 3 with the value 5.

**Good narration** tells the reader *why* the frame matters:

> Cell 3 is the first time the "skip two" branch becomes cheaper than
> the "skip one" branch, so the argmin flips.

Good narration rules:

- **One sentence per frame.** If you need two, split the step or cut one.
- **State the invariant, not the pixels.** The SVG already shows the
  pixels.
- **Inline math belongs inside `\narrate{...}`.** Write `$dp[i]$`, not a
  textual substitute. The TeX plugin renders it in place.
- **Mix languages naturally when the problem set does.** The cookbook
  problems alternate Vietnamese and English inside narration; that is
  fine. Consistency with the surrounding problem statement beats
  monolingual purity.
- **No meta-narration.** Do not write "In this step…" or "As we can
  see…". Strip those openings until the sentence starts with content.

## 4. Primitive choice: pick the one the problem is actually about

Scriba ships 16 primitives across three groups:

- **Base (6):** `Array`, `Grid`, `DPTable`, `Graph`, `Tree`, `NumberLine`.
- **Extended (5):** `Matrix` / `Heatmap`, `Stack`, `Plane2D`, `MetricPlot`, `Graph` with `layout=stable`.
- **Data-structure (5):** `CodePanel`, `HashMap`, `LinkedList`, `Queue`, `VariableWatch`.

Choose the one that matches *the problem's mental model*, not the one
that is easiest to draw.

- 1-D DP over a line of stones/positions → `Array`.
- 2-D DP (knapsack, LCS, edit distance) → `DPTable`, not `Grid`. A
  `DPTable` lets you address cells by `(i, j)` semantically and supports
  row/column highlighting.
- 2-D spatial problems (BFS on a maze, flood fill) → `Grid`.
- Recursion trees, binary trees, segment trees → `Tree`.
- Adjacency-list graphs, shortest paths, SCC → `Graph`.
- Binary search on the answer, sweep-line thresholds → `NumberLine`.
- Numerical matrix heatmaps (transition matrices, distance maps) → `Matrix` / `Heatmap`.
- LIFO push/pop walks (parenthesis matching, recursion simulation) → `Stack`.
- Cartesian geometry (points, lines, polygons, regions) → `Plane2D`.
- Time-series metrics (loss curves, convergence plots) → `MetricPlot`.
- Source code with line-by-line highlight → `CodePanel`.
- Hash buckets and collisions → `HashMap`.
- Pointer-based sequences → `LinkedList`.
- FIFO queues → `Queue`.
- Ambient scalar state (variables that change over frames) → `VariableWatch`.

If you find yourself faking one primitive with another (drawing a tree
inside a `Grid`, faking a `NumberLine` with a 1×N `Grid`), stop and
switch primitives. The spec gives you 16; use the right one.

## 5. Semantic state discipline

The seven `\recolor` states (`idle`, `current`, `done`, `dim`, `good`,
`error`, `path`) are a small vocabulary on purpose. Do not reinvent
colors. Do not stack decorations. Use states for what they mean:

- `current` — "this is the cell/node/edge being examined in this frame."
  One or two per frame, almost never more.
- `done` — "this value is finalized and will not change."
- `good` — "this is a positive / optimal choice or accepted candidate."
- `path` — "this belongs to the chosen solution chain."
- `error` — "this path was tried and rejected." Use sparingly.
- `dim` — "this exists but is out of scope for the current frame."
- `idle` — everything else (the starting / default state).

`highlight` is **not** a `\recolor` state. It is an ephemeral decoration
applied by the `\highlight{target}` command and only lasts for the frame
that emits it.

Frames should look calm. If every cell is in a different state, nothing
is highlighted. If the reader's eye does not know where to land in under
a second, the frame is overloaded.

Prefer `\recolor{...}{state=done}` for persistence and
`\highlight{...}` for ephemerality. Do not use `\recolor` to fake a
highlight: the reader will think the state is permanent.

## 6. Frame budget: soft 30, hard 100

The spec warns at 30 frames and errors at 101. Treat those as guardrails,
not targets.

- **Under 8 frames:** good default. Matches how a teacher walks through
  an example at a whiteboard.
- **8–15 frames:** fine for a full DP fill or a BFS on a small grid.
  Make sure each frame says something the previous one did not.
- **15–30 frames:** only if the problem genuinely has 15–30 distinct
  moments. If three consecutive frames all say "and then we filled the
  next cell the same way," cut them. Use one frame with narration
  like "frames 4 through 9 repeat the same pattern; we skip to the
  first interesting one."
- **Over 30 frames:** the Scriba warning is telling you something. You
  are probably animating *data*, not *algorithm structure*. Step back
  and ask what the lesson is. Split into two smaller animations, or
  switch to a single-frame figure plus prose.

A 50-frame animation is a video. If you want a video, make a video.
Scriba is for the dense, re-readable, printable moments of insight.

## 7. Don't fight the compiler: use `\compute` when you can

`\compute{...}` runs Starlark at build time. Use it to generate the
values you would otherwise hand-type. Hand-typed frame values drift
the moment you change the input.

**Avoid this:**

```tex
\step \apply{dp.cell[0]}{value=0} \narrate{…}
\step \apply{dp.cell[1]}{value=20} \narrate{…}
\step \apply{dp.cell[2]}{value=30} \narrate{…}
\step \apply{dp.cell[3]}{value=30} \narrate{…}
```

**Prefer this:**

```tex
\compute{
    h = [10, 30, 40, 20]
    dp = [0, abs(h[1]-h[0])]
    for i in range(2, len(h)):
        dp.append(min(dp[i-1]+abs(h[i]-h[i-1]),
                      dp[i-2]+abs(h[i]-h[i-2])))
}
\step \apply{dp.cell[0]}{value=${dp[0]}} \narrate{…}
\step \apply{dp.cell[1]}{value=${dp[1]}} \narrate{…}
```

Now the animation is sourced from the same recurrence you wrote in the
prose. If the prose changes, the animation cannot silently contradict
it. If the input array changes, you regenerate and the frames track.

`\compute` has no I/O, no randomness, no clock, and a step-count cap.
That is a feature: the same source produces byte-identical HTML every
time, which is what makes the downstream content-hash cache correct.

## 8. Accessibility is not optional

Scriba is accessible by construction — but only if you hold up your
half of the contract.

- **Always set `label=`** on the `animation` environment. It becomes
  the `aria-label` on the outer `<figure>`. Write a label that describes
  *what is being visualized*, not *that it is a visualization*. Good:
  `label="BFS frontier on a 4×4 maze"`. Bad: `label="animation 1"`.
- **Write narration as a standalone description.** A screen reader will
  walk the `<ol>` frame by frame and read each `<p class="scriba-narration">`
  in order. A learner who cannot see the SVG should still understand
  the algorithm from the narration alone. Test this literally: read
  only the narration sentences aloud in order and ask whether you
  followed the logic.
- **Never encode meaning in color alone.** The state classes carry
  semantics (shape, border, thickness) as well as color. If you find
  yourself saying "the red cell is the current one," fix the sentence
  to reference the semantic state ("the highlighted cell"), not the
  color.
- **The stylesheet ships a CVD-safe palette.** Do not override it with
  inline color. If the default does not work for your problem, file an
  issue against the stylesheet, not a local workaround.
- **Respect `prefers-reduced-motion`.** The filmstrip has no runtime JS,
  so there is no motion to reduce; but if you use CSS transitions in a
  custom asset, wrap them in `@media (prefers-reduced-motion: no-preference)`.
- **Print.** The spec collapses the filmstrip to a vertical stack under
  `@media print`. Open your rendered HTML and print-preview it before
  you ship. If the animation does not make sense as a numbered list of
  figures on paper, it will not make sense on screen either.

## 9. Work with the spec, not around it

- **Do not reach for `innerHTML` tricks.** The interactive widget includes an inline JS runtime with a step controller and WAAPI transitions, but authors should not inject custom JavaScript or DOM manipulation. If you need behavior beyond what the built-in step controller and transition system provide, file an ADR.
- **Do not nest environments.** `\begin{animation}` inside
  `\begin{animation}` is an error (`E1003`). If you want to show two
  things evolving, use two animations in sequence with prose between
  them.
- **Do not inline state into prose.** Never try to "refer to frame 3 of
  animation A from the middle of a paragraph." The frame is a semantic
  unit. Reference it by `label`, not by index.
- **Leave options alone unless you need them.** `width`, `height`,
  `layout=stack`, and friends exist for real cases. Setting them to
  soothe a preview that looks slightly off is almost always the wrong
  move. Trust the primitive's default sizing.

## 10. The five-question checklist before you publish

Run through this list before committing a problem that uses an
`animation` environment:

1. **Does it replace prose, or does it duplicate prose?** If the reader
   can skip the figure and still understand the problem, cut the
   figure.
2. **Can a blind reader follow the algorithm from narration alone?**
3. **Does every frame advance the story?** If frame $k$ and frame $k-1$
   teach the same lesson, merge them.
4. **Would this still make sense printed on paper in grayscale?**
5. **Does the source compile byte-identically a second time?** If
   anything in your `\compute` depends on iteration order of a dict or
   a non-deterministic input, fix it. Determinism is not optional.

Pass all five and the figure has earned its place. Fail any one and go
back to the prose.

---

*Mechanics in [`environments.md`](../spec/environments.md).
Starter problems in [`cookbook/`](../cookbook/). Integration examples in
[`usage-example.md`](usage-example.md).*
