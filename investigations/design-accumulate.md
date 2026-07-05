# Design — Accumulation Surfaces (dry-run trace table + live invariant)

> DESIGN investigation. **No repo source modified** (this doc + throwaway probe only; probe rendered
> to a repo `_probe_tmp/` then deleted, cwd-write restriction). Repo @ `main` `5e7d75b`, scriba 0.21.1,
> SCRIBA_VERSION = 18. Every `path:line` was read this session; the invariant `${}` leak and the Grid
> hand-roll were **rendered** this session (probe below). NO Playwright.
>
> Grades: **[Confirmed]** = read in source / rendered this session · **[Deduced]** = logical consequence ·
> **[Design]** = proposal, not built.

---

## 1. Problem + confirmed constraint

Two "record values as they evolve" surfaces are missing. Both are the **highest-value CP-teaching artifacts**
(see `investigations/teaching-board-archetypes.md` §3.1 and `investigations/teaching-lecture-tempo.md` G1).

**(a) Accumulating dry-run trace table** — variables as COLUMNS, execution steps as ROWS, filled line-by-line;
headers pinned, table grows downward, past rows persist. **No first-class surface exists.**

- `VariableWatch` is structurally the *transpose*: variables are ROWS, one current-value COLUMN, and every
  write **overwrites** — `variablewatch.py:103` (`self._values: dict[str,str]`, one slot per var), `:148-149`
  (`self._values[varname] = str(...)` replaces), `:297`+`:347` (SVG emits one row per var name, current value
  only). No history list, no per-step append. **[Confirmed]**
- `Grid` is a **fixed** `rows×cols` matrix declared up front (`grid.py:127-160`), addressed `cell[r][c]`, with
  **no column headers** (`ACCEPTED_PARAMS = {rows, cols, data, label}`, `grid.py:120-125`). **[Confirmed]**
- `Matrix` is the only header-bearing table (`row_labels`/`col_labels`, `matrix.py:162-163,255-297`) but it
  **forces a colorscale heatmap** (`matrix.py:241-250`, default `viridis`, `E1421` otherwise) — every value
  tinted by magnitude, visual noise on a text trace — **and it is static** ("matrix data is static, no
  `set_value` path", `matrix.py:279`), so it cannot accumulate rows at all. **[Confirmed]**

**(b) Live invariant** — a pinned predicate whose value updates per step ("running sum = 12" where 12 changes).
`\invariant` is prelude-only, static, and does **not** interpolate `${}`:

- Parsed to `ir.invariants`, a tuple of raw strings (`parser/ast.py:533`, `grammar.py:230,269`); prelude-only,
  `E1058` after the first `\step` (`errors.py:164`, `grammar.py:307-318`). **[Confirmed]**
- Rendered **once** as static chrome — `_render_invariant` (`renderer.py:238-252`) runs `$math$`/`\textbf` but
  **never** `_interpolate_narration`; `_html_stitcher.py:623` "Static across all frames, so emitted ONCE".
- **[Confirmed, rendered this session]** `\invariant{Running sum = ${s}}` with `\compute{s=0}` emits the literal
  `<p class="scriba-invariant" role="note">Running sum = ${s}</p>`. The `${s}` leaks.
- By contrast **narration IS interpolated per-frame**: `scene.apply_frame` calls
  `self._interpolate_narration(frame_ir.narrate_body)` (`scene.py:340` → `:715-747`) against the live per-frame
  bindings, stores `frame.narration_html`, and the runtime swaps it per frame from a JSON island
  (`scriba.js:115-116,409`; stitcher JSON `{svg, narration, substory}` at `_html_stitcher.py:597`). **[Confirmed]**

**The core mechanic both need (already in the engine):** the frame pre-pass re-applies each frame's
`apply_params` through `prim.apply_command(...)` (`_frame_renderer.py:832-859`), walking one stateful primitive
frame-by-frame in source order, so structural mutations **accumulate** — frame *k* holds *k* appends. This is the
"delta-inherited frames" model (`apply_params` are ephemeral per frame, `scene.py:343-347`). It is exactly how
`LinkedList` insert, `Tree` add_node, `Queue` enqueue, `Stack` push already grow. **[Confirmed]**

---

## 2. Approaches + trade-offs

### A. `history=true` on VariableWatch (least new vocabulary)
The same `\apply{w}{i=3}` that drives the live panel also snapshots a row into an accumulating table.
- **+** one param, binds live panel ↔ trace (kills duplication), no new noun.
- **−** VariableWatch is name×value (vars as ROWS); a trace is steps×vars (vars as COLUMNS). `history` would
  **transpose the entire render** — `emit_svg` branches wholesale into a differently-shaped surface: two
  primitives wearing one name. Worse, the "snapshot a row" trigger is ambiguous: the panel only sees `\apply`,
  not `\step`; N applies in one step = N rows or 1? There is no per-step hook. The snapshot-per-step semantic
  does not map onto the apply-driven model. **Structurally muddy — rejected.**

### B. Dedicated `TraceTable` primitive (chosen)
`\shape{t}{TraceTable}{columns=[i, "a[i]", sum]}` + append op `\apply{t}{row=[0, 3, 3]}`.
- **+** shape matches the artifact exactly (pinned columns × growing rows); append is unambiguous (one `\apply`
  = one row); rides the `LinkedList` structural-prescan/envelope model precisely; auto-advancing current row
  removes the manual cursor bookkeeping; first-class pinned headers.
- **−** one new primitive noun. But it reuses **all** machinery — `PrimitiveBase`, structural `apply_command`,
  the structural prescan, delta-frame accumulation, state classes, `element_add` reveal — with **zero new
  motion vocabulary** and **zero shared-asset change**. scriba's grammar is deliberately primitive-rich (24
  primitives); a primitive shaped like the #1 CP artifact is justified.

### C. Extend Grid with `col_labels` + append-row (reuse Grid)
Give Grid first-class headers (decouple from Matrix's heatmap) plus append semantics.
- **+** reuses Grid.
- **−** Grid's contract is a **fixed** `rows×cols` grid (R-32 via a *fixed* count). Bolting "append past
  `rows=N`" changes fixed→growing and forces the envelope-prescan onto a currently-simple primitive; Grid's
  2-D `cell[r][c]` addressing fights a trace's `row[k]`/header model; and changing Grid's growth contract
  risks byte-stability for existing Grid users. **Two modes bolted onto one noun — rejected.**

**Verdict:** B. It is the only option whose *shape* is the artifact (pinned columns × growing rows), it rides
existing machinery end-to-end with no new motion kinds and no version bump, and it keeps every primitive
coherent (no VariableWatch transpose, no Grid dual-contract).

---

## 3. The chosen design

### 3.1 `TraceTable` — syntax

```latex
% Declaration (prelude, before first \step) — columns are the pinned header row.
\shape{t}{TraceTable}{columns=[i, "a[i]", sum, note], label="Dry run: sum over a"}

\step
\apply{t}{row=[0, 3, 3, "+3"]}          % append one data row; it becomes the CURRENT row
\narrate{Iteration i=0: sum=3.}
\step
\apply{t}{row=[1, 1, 4, "+1"]}          % appended below; row[0] auto-demotes to idle
\narrate{Iteration i=1: sum=4.}
\step
\apply{t}{row=[2, 4, 8, "+4"]}
\recolor{t.cell[2][2]}{state=good}       % optional: emphasise the value that changed
\narrate{Iteration i=2: sum=8.}
```

**Params** (`ACCEPTED_PARAMS = {columns, label}`):
- `columns` (**required**): list of header strings; its length is the fixed column count. Pinned as chrome
  above the body, never scrolls, not a data row.
- `label` (optional): caption, identical to every other primitive.
- No `rows` / `max_rows` author param — the row envelope is auto-discovered by the prescan (§3.3).

**Append op** — `\apply{t}{row=[...]}`: appends one data row (length must equal the column count). Cells accept
strings or numbers (stringified like Grid). This is a **shape-level** apply (target `t`, no suffix), routed to
`apply_command(params)` exactly like `\apply{ll}{insert=...}` and `\apply{T}{add_node=...}`
(`_frame_renderer.py:613-617`).

**Selectors** (standard `set_state` path — `\recolor`/`\focus`/`\annotate`, NOT apply):
| Selector | Meaning |
|---|---|
| `t.row[k]` | data row *k* (0-based, header excluded) |
| `t.cell[k][j]` | data row *k*, column *j* |
| `t.col[j]` | column *j* down all data rows (emphasis) |
| `t.all` | all data cells |

**Auto-advancing current row (derived, not stored):** at emit time the newest data row — index `len(rows)-1`
in the current frame — renders `state=current` by default; older rows render `idle`. This is a pure function of
"is this the last row this frame?", so across frames the previous current row naturally becomes idle and the new
row appears — the differ emits a free `recolor` (retire prior line) + `element_add` (reveal new line). An
explicit `\recolor{t.row[k]}{done}` overrides the default. **This collapses workaround steps 2–3 (manual row
index + manual current/idle cursor) to nothing.**

### 3.2 Motion-kind analysis (rides existing kinds — 0 new vocabulary)
- **Append row** → structural `apply_command` grows the row list → next frame a new `<g data-target="t.row[k]">`
  exists → the differ emits **`element_add`** → runtime fade-in (`scriba.js:191-216`). **Identical kind** to
  `LinkedList` insert / `Tree` add_node / `Queue` enqueue.
- **Current→idle auto-advance** → the prior row's class changes across frames → **`recolor`** (existing).
- **Optional in-cell value emphasis** → **`value_change`** / **`recolor`** (existing).
- **New motion kind: NONE.** Honors the closed motion registry (A-2 "0 new motion vocabulary").

### 3.3 Growth envelope / R-32 (the accumulating-table stability story)
The surface grows in ROWS, so — like `LinkedList` grows in NODES — the bbox must track the **max extent ever
reached**, never the live count. Direct reuse of the `LinkedList`/`Bar` prescan model:

- `class TraceTable(PrimitiveBase): _structural_prescan = True` (opt into the replay, `linkedlist.py:87`).
- Store data rows in `self.values: list[list]` (a list of row-tuples). The prescan snapshots/restores `values`
  for free (`_frame_renderer.py:82-83,140-142`), so frame 0 renders with **zero** data rows after the replay.
- `self._envelope_rows: int` grows monotonically — in `apply_command` on each append **and** during the
  structural prescan replay — so it reaches the timeline maximum before frame 0 is measured (mirrors
  `_envelope_n`, `linkedlist.py:129,174,243`; deliberately kept across the prescan restore).
- Per-column widths grow monotonically to fit the widest cell in each column across the whole timeline (grown
  inside `apply_command`; the prescan replays `apply_command`, so widths reach their max too — mirrors Grid's
  monotonic `_cell_width`, `grid.py:170-177,183-187`).
- `bounding_box()` height = header band + `_envelope_rows × row_height` + caption/below lanes; width =
  Σ column widths + padding. **A pure function of the envelope + column count, never of the live row count** →
  the stage viewBox is invariant across frames (R-32), exactly as `bar.py:327-347` and `linkedlist.py:242-259`.

The frame pre-pass then re-appends one row per frame during the real walk (`_frame_renderer.py:832-859`); frame
*k* contains *k* rows inside a bbox already sized for the maximum. The table grows downward into pre-reserved
space; nothing reflows.

### 3.4 E-codes (fresh E1520 band — highest used today is E1519)
| Code | Class | Trigger |
|---|---|---|
| **E1520** | Validation | `TraceTable` missing/empty `columns`. hint: `\shape{t}{TraceTable}{columns=[i, j, sum]}` |
| **E1521** | Validation | appended `row` length ≠ column count. hint: supply exactly N values, one per column |
| **E1522** | Validation | `columns` count out of range (1..64) |

Out-of-range `t.row[k]`/`t.cell[k][j]` selectors follow the shipped **soft-drop** contract
(`validate_selector` → False; annotate degrades to None), matching Grid (`grid.py:198-213,236-249`).

### 3.5 Byte-stability + SCRIBA_VERSION
**No bump.** `TraceTable` is a new primitive riding shipped motion with **no CSS rule and no scriba.js change** —
the exact profile the policy already shipped bump-free: 0.25.0 added Bar and kept SCRIBA_VERSION = 18 because
"opt-in and emit NO new SVG bytes for documents that don't use them … Bar rides the shipped `value_change`
motion" (`_version.py:208-218`; contract "identical source + identical SCRIBA_VERSION → identical HTML",
`:227-228`). Documents that never say `TraceTable` emit byte-identical output. **[Deduced from precedent]**

### 3.6 Live invariant — `${}` interpolation on the invariant surface
Extend the §13.2 interpolation scope to `\invariant`, resolved **per-frame** (a running value needs a per-frame
value — global-compute-only resolution would stay static and under-deliver the gap).

- **Where it's excluded today & why:** invariants are raw strings rendered once (`renderer.py:238-252,709-711`),
  never passed through `_interpolate_narration`. It was shipped "static v1" (`SCRIBA-TEX-REFERENCE.md:743-764`).
- **Change:** in `scene.apply_frame`, resolve each invariant body via the **existing** `_interpolate_narration`
  against the live per-frame bindings (`scene.py:340,715-747`) and store the resolved tuple on the
  `FrameSnapshot` (new field `invariants_html`). The stitcher emits per-frame `invariant` into the JSON island
  (parallel to `narration`, `_html_stitcher.py:597`), keeping frame[0]'s copy in the static
  `<p class="scriba-invariant">`. The runtime, right after `narr.innerHTML=frames[i].narration`, sets the
  invariant panel innerHTML from `frames[i].invariant` — a ~2-line parallel of the narration swap at the three
  sites (`scriba.js:67,115-116,404-410`), landing on the same after-settle beat.
- **Byte-stability (opt-in):** gate the per-frame path on whether **any** invariant contains `${`. None →
  emit exactly today's static panel, no JSON `invariant` key, JS path untaken → **byte-identical** for every
  existing invariant document. Some → opt-in.
- **SCRIBA_VERSION: bump 18→19.** Touching `scriba.js` changes the shared runtime hash for every widget — that
  is precisely what a bump signals (the 17→18 runtime-glide precedent, `_version.py:141-149,188-199`). Non-`${}`
  invariants stay **markup**-byte-identical; the runtime asset changes for all, as every runtime release does.
- **Sequencing recommendation:** ship `TraceTable` first (no bump); batch the live-invariant JS change into the
  next runtime-touching release so it shares an unavoidable bump rather than forcing its own.

### 3.7 TDD plan (RED first)
Unit (`tests/unit/test_tracetable.py`) — write failing first:
1. `test_columns_required_raises_e1520` — `\shape{t}{TraceTable}{}` → E1520.
2. `test_row_length_mismatch_raises_e1521` — 4 columns, `row=[1,2,3]` → E1521.
3. `test_append_accumulates_rows` — 3 steps each append a row; frame *k* emits exactly *k* `data-target="t.row[*]"` groups (delta accumulation).
4. `test_newest_row_is_current_prior_idle` — after 2 appends, `row[1]` class = current, `row[0]` = idle (auto-advance), no manual `\recolor`.
5. `test_headers_pinned_and_not_addressable` — header cells emit above the body; `t.row[0]` addresses the first *data* row, not the header.
6. `test_structural_prescan_reaches_timeline_max_before_frame0` — mirror `tests/unit/test_linkedlist_envelope.py`: bbox height/width at frame 0 already sized for the max rows (viewBox invariant across frames).
7. `test_column_width_monotonic` — a wide value in a late row does not shrink earlier frames' width.
8. `test_recolor_cell_and_col` — `\recolor{t.cell[k][j]}` and `t.col[j]` set state; out-of-range soft-drops.

Live invariant (`tests/unit/test_invariant.py`, extend):
9. `test_invariant_interpolates_per_frame` — `\invariant{sum=${s}}` with `\compute{s=3}`…`{s=8}` → panel shows `sum=3`…`sum=8` (RED today: renders literal `${s}`, proven by probe).
10. `test_static_invariant_byte_identical` — an invariant with no `${}` emits the exact pre-change static HTML and no JSON `invariant` key (byte-stability gate).

Fixtures: `tests/fixtures/pass/NN_tracetable_accumulate.tex` (golden HTML: rows grow, headers pinned, viewBox constant).

### 3.8 Implementation sketch (files)
- **New** `scriba/animation/primitives/tracetable.py` (~350–450 lines, modeled on `grid.py` + `linkedlist.py`):
  `TraceTable(PrimitiveBase)`, `_structural_prescan = True`, `apply_command({"row": [...]})` appends +
  grows `_envelope_rows`/column widths, `validate_selector`/`resolve_annotation_point`/`bounding_box`/
  `emit_svg` (pinned header band + data rows + auto-advance current row), `set_annotations`, obstacle stubs.
- Register in `scriba/animation/primitives/__init__.py`; add E1520–E1522 to `scriba/animation/errors.py`.
- Doc: new §7.x in `docs/SCRIBA-TEX-REFERENCE.md` (twin of the VariableWatch/Grid table section).
- **Live invariant** (separate PR): `scene.py` (per-frame resolve + snapshot field), `parser/ast.py`
  (`FrameSnapshot.invariants_html`), `renderer.py`/`_html_stitcher.py` (per-frame JSON, gated), `static/scriba.js`
  (swap), `_version.py` 18→19.

---

## 4. Recipe-today baseline (why the design wins)

Today the trace table is hand-rolled on a `Grid` (rendered & confirmed this session; probe parses, EXIT=0):

```latex
\shape{tbl}{Grid}{rows=4, cols=3, label="Trace: sum"}
\apply{tbl.cell[0][0]}{value="i"} \apply{tbl.cell[0][1]}{value="a"} \apply{tbl.cell[0][2]}{value="sum"}
\recolor{tbl.row[0]}{state=done}                 % burn row 0 as a fake header
\step
\apply{tbl.cell[1][0]}{value="0"} \apply{tbl.cell[1][1]}{value="3"} \apply{tbl.cell[1][2]}{value="3"}
\recolor{tbl.row[1]}{state=current}
\step
\recolor{tbl.row[1]}{state=idle}                 % manually retire the prior current row
\apply{tbl.cell[2][0]}{value="1"} \apply{tbl.cell[2][1]}{value="1"} \apply{tbl.cell[2][2]}{value="4"}
\recolor{tbl.row[2]}{state=current}
```

| Cost of the hand-roll (`teaching-board-archetypes.md` §3.1) | `TraceTable` |
|---|---|
| Burn row 0 as a fake header; it scrolls with data | `columns=[...]` — pinned chrome |
| Manual row-index bookkeeping (miscount = silent wrong line) | `\apply{t}{row=[...]}` appends; index is automatic |
| Manual `\recolor{row[k]}{current}` + `\recolor{row[k-1]}{idle}` every step | newest row auto-current, prior auto-idle |
| `rows=N` fixed up front; can't grow past it | grows via the structural-prescan envelope |
| No binding to a live `VariableWatch` (values in two places) | trace is the first-class running-value surface |
| 3 `\apply` + 2 `\recolor` per step, hand-indexed | 1 `\apply{t}{row=[...]}` per step |

And for the live invariant, today `\invariant{Running sum = ${s}}` renders the literal `${s}`
(**rendered proof this session**); the design resolves it per step against the same `\compute` binding narration
already uses.

---

## 5. Return summary

- **Chosen:** a dedicated **`TraceTable`** primitive (pinned `columns` header × downward-growing rows via
  append `\apply{t}{row=[...]}`, auto-advancing current row), plus **`${}` interpolation on `\invariant`**
  resolved per-frame.
- **Rationale (1¶):** Only a purpose-shaped primitive matches the artifact (columns×growing-rows) while reusing
  the engine wholesale — it rides the `LinkedList` structural-prescan envelope for R-32 stability, the shipped
  `element_add`/`recolor` motions for growth, and the Bar new-primitive precedent for a **no-bump, byte-clean**
  ship; extending VariableWatch would transpose it into a second surface and extending Grid would fracture its
  fixed contract. The live invariant simply routes the invariant body through the narration interpolator it
  already sits beside, gated so static invariants stay byte-identical.
- **Syntax:** `\shape{t}{TraceTable}{columns=[i, "a[i]", sum]}` + `\apply{t}{row=[0, 3, 3]}`; selectors
  `t.row[k]`, `t.cell[k][j]`, `t.col[j]`, `t.all`. Invariant: `\invariant{Running sum = ${s}}` (now live).
- **Cost:** TraceTable **M**; live invariant **M**.
- **Risk:** TraceTable **Low** (rides proven Grid/LinkedList machinery); live invariant **Low–Med** (byte-gate
  must be exact; runtime swap is a 2-line narration parallel).
- **New motion kind?** **No** (append = `element_add`, advance = `recolor` — closed registry preserved).
- **New primitive or extend?** **New primitive** (TraceTable) for the table; **extend** the invariant surface
  for the live value.
- **SCRIBA_VERSION bump?** TraceTable **No** (Bar precedent). Live invariant **Yes, 18→19** (scriba.js swap);
  recommend batching it into the next runtime release.
- **Value/cost self-score:** TraceTable **5/5** (the #1 CP artifact, M cost, low risk, no bump).
  Live invariant **3/5** (real but peripheral gap; the bump/JS touch caps it).
