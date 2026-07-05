# Teaching Board Archetypes — can scriba compose the full-board pictures a CP teacher draws?

> BMAD investigation. **No repo source modified.** Read-only; probes written to scratchpad, rendered to a
> throwaway dir inside the repo (cwd-write restriction, then deleted). Repo @ `main` `5e7d75b`, scriba 0.21.1
> (docs target 0.25.0). Every `path:line` citation was read this session; every "Buildable" verdict except
> archetypes 4 was **rendered** and the emitted HTML parsed (no Playwright).
>
> Evidence grades: **[Confirmed]** = read in source / shipped example / rendered this session ·
> **[Deduced]** = logical consequence of confirmed facts · **[Hypothesized]** = design proposal, not built.

---

## 1. Hand-off Brief (3 sentences)

Of the six full-board compositions a CP teacher draws, **five are buildable today** with existing primitives —
recursion-tree unfolding (`Tree` + `add_node` per step), DP-fill-with-dependency-arrows (`\annotate{...}{arrow_from=another cell}`,
which **does** point cell→cell), graph-traversal-with-queue-beside (multi-primitive lockstep, shipped in example 9.3),
two-pointer/sliding-window (two binding carets + `\focus` window), and number-line binary-search jumps (`NumberLine`
ticks + caret) — each verified by a render probe. **The single most common CP-teaching artifact, the dry-run trace
table (variables as columns × execution steps as rows, filled line-by-line), has no first-class surface and is a
Confirmed gap**: `VariableWatch` is structurally a *name × current-value* panel — variables are rows, there is one
value slot per variable, and every write **overwrites** it (`variablewatch.py:103,148-149`), so it shows only the
current frame, never the accumulated history a dry-run needs. The least-awkward workaround is to hand-roll the table
on a `Grid` (one row per step, filled via persistent `\apply`); it genuinely accumulates line-by-line (rendered &
confirmed), but you burn row 0 as a fake header, hand-manage row indices, and hand-advance the "current" row every step.

---

## 2. Coverage Table

| Archetype | Verdict | How (primitives + path/§) or the gap |
|---|---|---|
| **Dry-run trace table** (vars = cols × steps = rows, filled line-by-line) | **Missing surface / Awkward hand-roll** | No dedicated surface. `VariableWatch` = variables-as-rows, single current-value column, **overwrite** (`variablewatch.py:103` single dict, `:148-149` assignment, `:297` rows=var_names, `:347` current value only). Hand-roll on `Grid` (rows=steps+1, cols=vars); persistent `\apply` + delta-inherited frames accumulate rows. **[Confirmed]** via probe A (frame *k* shows exactly *k* rows; frame 5 shows all 5). |
| **Recursion-tree unfolding** node-by-node | **Buildable** | `Tree` + `\apply{T}{add_node={id,parent}}` per `\step`; relabel via `\apply{T.node[id]}{value=…}`. Ref §7.5 (`SCRIBA-TEX-REFERENCE.md:1068,1118`), sparse-segtree worked example (`:1098-1113`). **[Confirmed]** probe E: node-groups grow 1→2→3→4. Reveal-variant also works (hidden→current, example 9.4 `:1600-1622`). |
| **DP table fill with dependency arrows** (cell[i][j] ← cell[i-1][j] …) | **Buildable** | `DPTable`(2-D) + `\annotate{dp.cell[i][j]}{arrow_from="dp.cell[i-1][j]"}`. **Arrows point cell→cell**; multiple arcs into one target auto-stagger. Ref §5.8 (`:476-489`). **[Confirmed]** probe C: 3 arcs, 6 bezier paths, 20 arrowheads, 0 errors. |
| **Graph traversal with queue/stack drawn beside** (BFS frontier) | **Buildable** | Multiple primitives in one `animation`, mutated in lockstep per `\step`: `Graph` + `Queue`/`Stack` + `Array`(visited). Shipped worked example 9.3 (`:1575-1598`): `enqueue`/`dequeue` + `\recolor` node/edge each step. **[Confirmed]** via shipped example (not separately re-rendered). |
| **Two-pointer / sliding window** (l,r pointers, window shaded) | **Buildable** | `Array` + two binding carets `\cursor{arr}{id=l, at="w.var[l]"}` / `id=r` that slide **independently** (ref §5.11 `:585-608`, "ideal for two-pointer/sliding-window"); window via `\focus{arr.range[l:r]}` (ephemeral, auto-resets) or `\recolor` range. **[Confirmed]** probe D: 2 carets, focus dimming, window values, 0 errors. |
| **Number-line / coordinate jumps** (binary-search mid, jumps) | **Buildable** | `NumberLine` ticks + `\recolor{nl.tick[i]}` for lo/hi/mid + caret on ticks (carets work on NumberLine, `:608`) + `\focus{nl.range[lo:hi]}` for shrinking space. **[Confirmed]** probe F: 48 tick recolors, mid caret, focus window, jumps 7→11→9, 0 errors. |

---

## 3. Confirmed Gaps

### 3.1 GAP — No first-class dry-run trace table; `VariableWatch` has no history (overwrite-only)

**The single most common CP-teaching artifact is the one thing the board-archetype set cannot draw natively.**

**Evidence the panel overwrites (never accumulates)** — all **[Confirmed]**:
- `variablewatch.py:103` — `self._values: dict[str, str] = {vn: "----" for vn in self.var_names}`. One value slot **per variable**, not per step.
- `variablewatch.py:148-149` — `self._values[varname] = str(params["value"])`. A write **replaces** the slot; there is no list, no per-frame append.
- `variablewatch.py:297` + `:347` — the SVG emits one row **per variable name**, each showing `self._values.get(vn)` — the *current* value only. Variables are ROWS; the value is a single COLUMN. This is the transpose of a dry-run table (which needs vars as COLUMNS and one new ROW per step).
- Shipped examples confirm the intended semantics: `examples/primitives/variablewatch.tex:8,17` writes `vars.var[i]=0` then `=3` — the same row overwrites 0→3; you never see both. `examples/fixtures/pass/01_variablewatch_shrink.tex` is literally a **regression test for the value column when a value is replaced by a shorter one across steps** — proof that a step overwrites the prior value in place.
- No investigation file anywhere proposes a trace *table* or a watch *history* (`grep -rli` over `investigations/` = 0 hits; `feat-trace-primitive.md` is about the `\trace` poly-cell **arrow**, §5.9 — an overlay, it accumulates nothing).

**What cannot be drawn natively:** a table that shows, *in one frame*, every past `(i, j, sum, note)` row a loop has produced — the "watch the state evolve line by line" board every CP teacher fills as they trace code. VariableWatch can show the current row; stepping back/forward changes it in place. To see all rows at once you must leave VariableWatch entirely.

**Least-awkward workaround (rendered & Confirmed — probe A):** hand-roll on a `Grid`.

```latex
\shape{tbl}{Grid}{rows=6, cols=4, label="Trace: sum over a=[3,1,4,1,5]"}
% Row 0 = fake header (Grid has no col_labels):
\apply{tbl.cell[0][0]}{value="i"} \apply{tbl.cell[0][1]}{value="a[i]"}
\apply{tbl.cell[0][2]}{value="sum"} \apply{tbl.cell[0][3]}{value="note"}
\recolor{tbl.row[0]}{state=done}
\step                                    % one execution line per \step
\apply{tbl.cell[1][0]}{value="0"} \apply{tbl.cell[1][1]}{value="3"}
\apply{tbl.cell[1][2]}{value="3"} \apply{tbl.cell[1][3]}{value="+3"}
\recolor{tbl.row[1]}{state=current}
\narrate{Iteration i=0: sum=3.}
\step
\recolor{tbl.row[1]}{state=idle}         % manually retire the prior "current" row
\apply{tbl.cell[2][0]}{value="1"} ...    % fill row 2 …
\recolor{tbl.row[2]}{state=current}
% … one \step per row …
```

It works because `\apply`/`\recolor` are **persistent** and frames are **delta-inherited** (ref §3.2): rendered frame *k* contains exactly the first *k* data rows (probe A: sum column present = `[3]`,`[3,4]`,`[3,4,8]`,`[3,4,8,9]`,`[3,4,8,9,14]`), i.e. past rows stay filled while each new line appears. `Grid.row[i]` recolor (since 0.24.0) lets you emphasize the active line.

**Why it's still awkward (the cost of the missing surface)** — **[Confirmed]** from the recipe above:
1. **No column headers** — `Grid` has no `col_labels` (only `Matrix` does, `dptable.py`/§7.7); you sacrifice row 0 and it scrolls with the data instead of pinning.
2. **Manual row bookkeeping** — the author tracks "which row is next" by hand; there is no append-row op. A miscount silently writes the wrong line.
3. **Manual current-row cursor** — every step needs an explicit `\recolor{row[k]}{current}` **and** a `\recolor{row[k-1]}{idle}` to retire the previous line; no auto-advance.
4. **Fixed height** — `rows=N` is declared up front; the table can't grow past it.
5. **Duplication** — if the scene also shows a live `VariableWatch`, the current values live in two places with no binding between them.
6. **Matrix is not a substitute** — its `col_labels` would give headers, but it is a viridis heatmap: every value gets tinted by magnitude (§7.7 `colorscale` only `"viridis"`, E1421 otherwise), which is visual noise on a text trace.

**What a dedicated surface would need** — **[Hypothesized]**:
- A `TraceTable` primitive with **first-class column headers** (`columns=["i","a[i]","sum","note"]`) that pin above a scrolling/growing body.
- An **append-row op**: `\apply{trace}{row=[0, 3, 3, "+3"]}` writes the next line **and** auto-advances the "current" row (prior rows auto-dim) — collapsing steps 2–3 of the workaround into one command and removing the row-index bookkeeping.
- A **growing** row count (append past the initial height) rather than a fixed `rows=N`.
- Ideally, a **`history=true` mode on `VariableWatch`**: `\shape{w}{VariableWatch}{names=[…], history=true}` snapshots one row per `\step` instead of overwriting slot values — so the *same* `\apply{w}{i=3,j=5}` the author already writes to drive the live panel *also* builds the dry-run table, binding the two views and killing the duplication (item 5).

---

## 4. Conclusion + Confidence

The multi-primitive, delta-frame model makes scriba strong at whole-board CP compositions: **5 of 6** archetypes in
this slice are buildable with shipped primitives, four of them verified by fresh render probes and the fifth by a
shipped worked example. The one **Confirmed gap** is also the highest-value one — the **dry-run trace table**, the
artifact CP teachers reach for most. It is missing not because the renderer can't hold the pixels (a `Grid` hand-roll
proves it can accumulate rows), but because no primitive is *shaped* like a trace table: `VariableWatch` is a
current-value panel that overwrites, and `Grid` lacks headers, an append-row op, and an auto-advancing current row.
The gap is genuinely unexplored (no prior investigation touches it), so it is a clean feature target.

**Confidence: High.** The prime gap is confirmed three ways (source single-dict/overwrite, two shipped examples,
render behavior); the workaround and all five buildable verdicts were rendered this session (or are shipped examples)
with zero error codes in the emitted HTML.

### Probes (scratchpad, reproducible)
`probeA_trace_table.tex` (Grid dry-run accumulation) · `probeC_dp_arrows.tex` (cell→cell arrows) ·
`probeD_two_pointer.tex` (two carets + focus window) · `probeE_rectree.tex` (add_node unfold) ·
`probeF_numline.tex` (binary-search jumps). Render: `.venv/bin/python render.py <probe>.tex -o <out-in-cwd>.html [--static]`.
