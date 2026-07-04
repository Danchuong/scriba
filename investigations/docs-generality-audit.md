# Scriba language-surface generality audit

**Scope**: orthogonality + coverage of the command/selector/rule surface (can a
user "do whatever they want"?), **not** docs prose quality (owned by two other
agents). Source of truth = **code** (`scriba/animation/`), cross-checked against
the 111-file example corpus and the design investigations. Repo `main @ eda4f7d`
(0.23.1), venv `.venv/bin/python`. No source was modified.

Grading: **Confirmed** = read in code (path:line given); **Hypothesized** =
inferred from adjacent code. Matrix legend: `✓` supported+rendered · `s`
soft/partial (parses but degrades or geometry-limited) · `–` unsupported
(parser accepts → silent no-op, or selector rejected) · `n/a` not applicable.

---

## Hand-off Brief (3 sentences)

1. **Yes, the surface is fundamentally general and orthogonal**: every mutation
   command is dispatched into *primitive-agnostic* scene collections keyed by
   selector string (`scene.py:619-636`), every selector-consuming command shares
   one `parse_selector` algebra (`selectors.py`), and the four highest-traffic
   capabilities — `\apply` value, `\recolor` state, `\highlight`, `\focus`,
   `\annotate` point, `\ref` — work on **all 16** primitives.
2. **The gaps are all emit-side opt-in drift on the newest decorations, not
   architectural**: `\trace`, `\cursor`-binding, `state=hidden`, and
   `block[..]`/bracket are wired into only a subset of primitives while the
   parser accepts them everywhere, producing silent no-ops.
3. **Big gaps worth fixing: 2** (Matrix missing `block[..]` despite being a
   designed-in "for free" 2-D primitive; `state=hidden` silently no-ops on 13 of
   16 primitives) — **plus 1 genuine "learn-twice" wart** (`\cursor` hosts two
   unrelated mechanisms under one keyword); everything else is either YAGNI
   (trace/cursor on graphs, where edges already carry `state=path`) or a
   low-value consistency polish.

---

## 1. Orthogonality matrix — capability × primitive

Columns (16 logical primitives): **Arr**=Array · **Grd**=Grid · **DP1**=DPTable-1D
· **DP2**=DPTable-2D · **Mtx**=Matrix · **NL**=NumberLine · **Stk**=Stack ·
**Que**=Queue · **LL**=LinkedList · **HM**=HashMap · **VW**=VariableWatch ·
**CP**=CodePanel · **Gph**=Graph · **Tr**=Tree · **P2**=Plane2D · **MP**=MetricPlot.

| Capability | Arr | Grd | DP1 | DP2 | Mtx | NL | Stk | Que | LL | HM | VW | CP | Gph | Tr | P2 | MP | Grade / source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `\apply` value | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | s | ✓ | ✓ | ✓ | ✓ | Conf `scene.py:755` |
| `\recolor` state (8) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Conf `scene.py:803`, `base.py:1304` |
| `state=hidden` (skip) | – | – | – | – | – | – | – | – | – | – | – | – | ✓ | ✓ | ✓ | – | Conf grep+`css` |
| `\highlight` (ephem) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Conf `scene.py:853`, `differ.py:113` |
| `\focus` (defocus) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Conf `_frame_renderer.py:564` |
| `\annotate` point | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Conf 16× `resolve_annotation_point` |
| `\annotate` range/block | ✓ | ✓ | ✓ | ✓ | **–** | ✓ | – | – | – | – | – | – | – | – | – | – | Conf `array/grid/dptable/matrix/numberline` |
| `bracket` (span glyph) | s | ✓ | s | ✓ | – | s | – | – | – | – | – | – | – | – | – | – | Conf `base.py:1191` (block); range=Hyp |
| `leader` (leader line) | ✓ | ✓ | ✓ | ✓ | ✓ | s | – | – | – | – | – | – | ✓ | ✓ | s | – | Conf grep; absent-cells Hyp |
| `color=state:` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Conf `_grammar_commands.py:330` |
| `\trace` (polyline) | ✓ | ✓ | ✓ | ✓ | **–** | ✓ | – | – | – | – | – | – | – | – | – | – | Conf grep `emit_traces_under` |
| `\cursor` legacy (hop) | ✓ | s | ✓ | s | s | ✓ | ✓ | ✓ | ✓ | ✓ | – | – | – | – | – | – | Conf `scene.py:954`+valsel |
| `\cursor` binding (caret) | ✓ | ✓ | ✓ | ✓ | **–** | ✓ | **–** | **–** | – | – | – | – | – | – | – | – | Conf grep `emit_cursors_under` |
| `\ref` target (narration) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Conf `ref_macro.py:118` |
| insert/remove (reflow) | ✓ | – | – | – | – | – | ✓ | ✓ | ✓ | – | – | – | ✓ | ✓ | ✓ | – | Conf grep insert/remove |
| sentinels (before/after) | ✓ | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | Conf `array.py:303` |

`\playeach` is **control-flow**, not a per-primitive capability: it desugars into
flat frames (cap 64, E1493) and composes with any primitive via `\apply`/`\recolor`
in its body — Conf `_grammar_playeach.py:8,27`. No orthogonality gap exists there.

### Orthogonality gaps, ranked by "real user hits soonest"

Ranking blends corpus primitive-frequency (Array 109 > Graph 31 > DPTable 27 >
Plane2D 23 > Tree 15 > Grid 9 > … > Matrix 2, CodePanel 2) with command-frequency
(`\recolor` 2731, `\apply` 1282, `\annotate` 389, `\highlight` 88, `\cursor` 82;
**`\trace`/`\focus`/`\cursor`-binding/`\playeach`/`\ref` = 0 corpus uses**).

1. **`state=hidden` silent no-op on 13/16 primitives** *(Confirmed)*. Parser
   accepts `state=hidden` for every primitive (`VALID_STATES`,
   `constants.py:27-32`), but only Graph/Tree/Plane2D skip-render it, and there is
   **no `scriba-state-hidden` CSS rule** (`scriba-scene-primitives.css` has
   idle/current/done/dim/error/good/highlight/path only). So
   `\recolor{a.cell[0]}{state=hidden}` on an Array sets a dead class and the cell
   stays visible. Highest rank: `hidden` is heavily used (bfs.tex recolors ~10
   nodes/edges hidden per frame) so a user *will* try it on an Array and be
   surprised. **Cheap, high-value.**
2. **Matrix has no `block[..][..]` (and no range, trace, cursor-binding)**
   *(Confirmed)*. `matrix.py:282` matches only `cell[r][c]` then `all`; but
   `feat-grid-block-selector.md:390` puts Matrix in the "Y" column ("any 2-D
   primitive whose `cell[r][c]` is addressable — Grid, DPTable-2D, **Matrix** —
   gets block-recolor for free"). This is **spec→code drift**, not a design
   choice. A user doing Gaussian elimination / block-matrix multiply reaches for
   `M.block[0:2][0:2]` and hits E1115. Low corpus count (Matrix=2) tempers the
   rank, but it is the natural home for the feature. **Cheap, medium-value.**
3. **`\cursor` legacy is 1-D-only and degrades on 2-D / string-keyed primitives**
   *(Confirmed `scene.py:981`)*. `new_key = f"{prefix}[{index}]"` appends a single
   int index, so Grid/DPTable-2D (`cell[i][j]` needs two) and Graph/Tree
   (string node ids) soft-degrade. Mostly fine — the legacy hop's real job is a
   1-D "current pointer" — but a user animating a 2-D DP fill who tries
   `\cursor{dp.cell}{...}` gets nothing. Medium rank (82 corpus uses, ~all Array).
4. **`\trace` and `\cursor`-binding stop at Grid-family** *(Confirmed grep)*.
   Both opt in only for Array/Grid/DPTable/NumberLine. Matrix is the only
   *cell-grid* omission that matters (see #2). Stack/Queue were named in-scope for
   the caret (`anim-multicursor.md:244`) but are unwired. **Low rank: 0 corpus
   uses of either feature** — this is latent surface, not a lived pain yet.
5. **`bracket` requires a `block[..]` target** *(Confirmed `base.py:1191`)*. So
   bracket inherits the Matrix gap and is unavailable on any 1-D-only primitive
   except as a range-span (Hypothesized). Lowest rank (niche param).

**Non-gaps (verified, do NOT "fix"):** `\trace`/`\cursor`-binding on **Graph/Tree**
— graphs render paths by recoloring real **edges** (`bfs.tex:36` `\recolor{G.edge[(A,B)]}{state=good}`,
plus `state=path`), so a polyline overlay is redundant; `feat-trace-primitive.md`
never lists Graph and its boundary error E1493 ("not cell-addressable") treats it
as out-of-domain, not unfinished.

---

## 2. Minimum concepts a user must learn + consolidation

**Concept budget (Confirmed inventory):**

| Axis | Count | Items |
|---|---|---|
| Commands (`\`) | **18** | shape, compute, step, narrate, invariant, apply, highlight, focus, recolor, reannotate, annotate, trace, cursor, foreach, playeach, substory, hl, ref (`grammar.py:284-415`) |
| Selector accessor forms | **~11** | cell[i], cell[i][j], range[lo:hi], block[r:r][c:c], node[id], edge[(a,b)], tick[i], item[i], var/bucket/line/point… (named), all, generic `name[i]` (`selectors.py:98-124`) |
| Cell states | **9** | idle, current, done, dim, error, good, highlight, path, hidden (`constants.py:27`) |
| Annotation colors | **6 + 6** | info/warn/good/error/muted/path, plus `state:{current,done,dim,good,error,path}` (`constants.py:35,44`) |
| Positions | **5** | above, below, left, right, inside (`constants.py:49`) |
| Common params | **~20** | value, label, state, color, position, arrow, arrow_from, ephemeral, bracket, leader, dot, arrowhead, id, at, prev_state, curr_state, insert, remove, push/pop |

The **core path is small** (~20 concepts: `\shape/\step/\apply/\recolor/\annotate/\narrate`
+ cell/range/all + 5 states + 3-4 colors) — this is what the whole `weird_algorithm.tex`
uses. The other ~55 concepts are a genuine long tail (trace, cursor-binding,
reannotate, invariant, hl, ref, playeach, substory, bracket, leader, sentinels,
positions, `state:` colors) that a beginner never touches.

**"Learn-twice" / special-case analysis:**

| Pair | Verdict | Detail |
|---|---|---|
| `\cursor` legacy **vs** binding | **Genuine wart — consolidate in docs** | One keyword, two mechanisms discriminated by presence of `id=` (`_grammar_commands.py:423`). Legacy = a state-hop that mutates `shape_states` (`scene.py:969-984`); binding = a persistent named caret glyph that adds no state churn (`scene.py:986`, code literally calls it "a *different animal*"). Legacy `\cursor{a.cell}{3}` is exactly sugar for two `\recolor` (dim the old `current`, set index-3 `current`). |
| `\recolor{color=}` **vs** `\reannotate` | **Already handled** | `\recolor` with `color=`/`arrow_from=` emits a `DeprecationWarning` pointing at `\reannotate` (`_grammar_commands.py:147,169`). Consolidation is in flight — docs should just teach `\reannotate`. |
| `\highlight` (cmd) **vs** `state=highlight` | **Naming collision, not a dup** | Ephemeral overlay (`scene.py:853`, cleared next step) vs persistent state (`scene.py:808`). Same word, two lifetimes. |
| `\highlight` **vs** `\focus` | **Complementary, keep both** | Brighten-target vs dim-complement; both ephemeral (`anim-unified-motion-model.md:150`). |
| `\hl` **vs** `\ref` | **Distinct referents, keep both** | Narration macros: `\hl{step-id}{tex}` cross-refs a *frame* (`hl_macro.py`); `\ref{selector}{text}` tints a word to a *cell's state* (`ref_macro.py`). Neither is a shape-decoration command. |
| `\annotate` **vs** `\reannotate` | **Create vs update, keep both** | `\annotate` appends (`scene.py:915`); `\reannotate` mutates matching entries (`scene.py:830`). INSERT/UPDATE split. |

**Consolidation proposal (no compat break — keep every alias):** exactly **one**
item needs action beyond finishing the already-started `\reannotate` migration —
teach `\cursor` as two clearly-named features ("cursor **hop**" = the 1-D
`\recolor` shorthand; "cursor **pin**" = the `id=`/`at=` caret) rather than one
command with a hidden mode switch. The `\recolor{color=}` path is already
deprecation-aliased; docs teaching only `\reannotate` completes "one way to do it".

---

## 3. Generalization rules — do they hold uniformly?

### 3a. Selector algebra × command (does every command take every form?)

**Yes at the grammar layer** — every selector-consuming command
(`apply/recolor/reannotate/highlight/focus/annotate`) funnels through the *same*
`parse_selector` (`_grammar_commands.py:95,105,117,187,237,314`), so the algebra is
uniform across commands; per-primitive differences live only in `validate_selector`.

**Two bespoke-syntax exceptions** *(Confirmed)* — the two zero-usage newcomers do
**not** use the selector algebra for their targets:

| Command | Target syntax | Deviation |
|---|---|---|
| `\trace` | `cells=[[r,c],…]` param list (`_grammar_commands.py:260`) | coordinate pairs, not a `range`/`block` selector |
| `\cursor` | comma-split raw prefixes + `at=int\|"shape.var[x]"` (`_grammar_commands.py:390,522`) | not a full `Selector`; `at=` is int-or-var only |

This is the root of "trace/cursor feel different" — they invented their own
addressing instead of reusing `range`/`block`/`cell`.

### 3b. Color / state uniformity

Two palettes coexist *(Confirmed `constants.py`)*: **cell states** (9, used by
`\recolor`/`\cursor`) and **annotation colors** (6, used by
`\annotate`/`\trace`/`\reannotate`/`\cursor`-binding). They overlap on
good/error/path/dim/current/done but each has exclusives (states add
idle/highlight/hidden; annotations add info/warn/muted). The `color="state:X"`
bridge (`constants.py:44`) lets an annotation borrow a target's state ink — a
deliberate, well-placed seam (design rule **D-5**). Verdict: **consistent enough**,
but it *is* two vocabularies the user learns.

### 3c. Ephemeral vs persistent

Clean and uniform *(Confirmed `anim-unified-motion-model.md:50`, A-0.iii)*:
highlight+focus are always ephemeral; annotate/trace/cursor default persistent with
an `ephemeral=true` opt-in (`_grammar_commands.py:307,354`). **One wart**:
`\highlight` has *no* persistent form and *no* `ephemeral=` flag — it is hardwired
ephemeral, the lone asymmetry in the lifecycle model.

### "I thought X worked everywhere" surprises (consistency gaps)

1. `state=hidden` accepted by the parser on all primitives but honored by 3 (§1 #1).
2. `M.block[..]` looks like `G.block[..]` but Matrix rejects it (§1 #2).
3. `\trace`/`\cursor{id=}` parse against any shape but render on 5 primitives.
4. `\cursor{grid.cell}{i}` (legacy) accepts a 2-D shape but the single index can't
   address a `cell[i][j]`.

All four share one root cause: **the parser is generous, the emitter is selective,
and the gap degrades silently instead of erroring.**

---

## 4. Verdict + roadmap

**Verdict:** the surface is **general and orthogonal by construction** — a unified
selector algebra, a primitive-agnostic scene-state model (`scene.py:619`), and a
single decoration list/emitter (design rule D-1). It is **not yet uniformly
*complete*** on the newest decorations, but the shortfalls are a handful of
unwired emit hooks, not missing abstractions. For the working corpus (Array/DP/Graph/
Tree/Plane2D heavy), a user can already "do what they want"; the surprises are
concentrated in low-traffic, recently-added surface.

### (a) Fill these — ranked by value ÷ effort

| # | Gap | Fix | Effort | Value |
|---|---|---|---|---|
| 1 | `state=hidden` silent no-op (13 primitives) | Add `.scriba-state-hidden{display:none}` CSS fallback **or** reject `hidden` in `validate_selector` for non-supporting primitives (fail-fast) | XS | High (kills a footgun on the #2 state) |
| 2 | Matrix `block[..]` + block-recolor/annotate/bracket | Add `_SUFFIX_BLOCK_RE` + `_block_center` to `matrix.py`, mirroring `grid.py:197` — designed-in per `feat-grid-block-selector.md:390` | S | Medium |
| 3 | Matrix `\trace` | Wire `emit_traces_under` into `matrix.py.emit_svg` (cell geometry already exists) | XS | Low-Med |
| 4 | trace/cursor use bespoke coords | Let `\trace cells=` and `\cursor at=` also accept `range`/`block`/`cell` selectors (reuse `parse_selector`) | M | Med (restores algebra uniformity) |
| 5 | `\cursor`-binding on Stack/Queue | Wire `emit_cursors_under` + slot geometry (in-scope per `anim-multicursor.md:244`) | M | Low (0 uses) |

### (b) Leave alone — YAGNI (stated plainly)

- **`\trace`/`\cursor` on Graph/Tree** — edges already carry `state=path`
  (`bfs.tex:36`); a polyline overlay would be a worse duplicate. Don't build it.
- **`\cursor`-binding 2-D (Grid/DPTable-2D)** — explicitly deferred to v2
  (`anim-multicursor.md:247`); no corpus problem needs a 2-D caret yet.
- **sentinels (`before`/`after`) beyond Array** — an Array-insertion visual; other
  ADTs reflow fine without it (`array.py:303`).
- **insert/remove on Grid/Matrix/DPTable/NumberLine** — fixed-geometry grids;
  structural reflow is meaningless there.
- **`\apply` value on CodePanel** — code lines are declared once; leave `s`.

### (c) Design rules for future surface (extend existing D-/A- ruleset)

- **D-6 (proposed) — Emit-parity or hard-error, never silent no-op.** Any
  decoration whose geometry is `Point|Rect|Path` (D-3) MUST be rendered by every
  primitive whose `validate_selector` accepts the target, **or** the parser/emitter
  MUST raise (E14xx). This converts every `–`/`s` cell above into `✓` or a loud
  error. Directly closes the `state=hidden`, Matrix-`block`, and trace/cursor
  drifts as a *class*.
- **A-8 (proposed) — One target grammar.** New commands MUST address targets via
  `parse_selector` (the full algebra), not bespoke coordinate params. Retrofit
  `\trace`/`\cursor` (§3a). Extends A-7 ("no parallel target grammar",
  `anim-unified-motion-model.md:121`).
- **N-1 (proposed) — One keyword, one mechanism.** A command keyword MUST NOT host
  two semantically different behaviors discriminated by a param (the `\cursor`
  hop-vs-pin split). Dual-behavior features get distinct keywords/aliases.

---

## Open questions (≤5)

1. **The "50-problem set" is not in the repo.** No doc/example references it; the
   real coverage anchor is the **105-file byte-golden corpus**
   (`unified-decoration-model.md:142`) + 111 examples. Is the 50-set an external
   or aspirational list I should pull in for ranking, or should the 105-corpus +
   primitive-frequency stand as the ranking basis (what I used)?
2. **Is `state=hidden` deliberately Graph/Tree/Plane2D-only?** If yes, D-6 says the
   parser should *reject* it elsewhere; if it's meant to be universal, it needs the
   CSS fallback. Which intent?
3. **Should Matrix reach full 2-D parity with Grid/DPTable-2D** (block + trace +
   annotate-range), or is Matrix intentionally a display-only "math matrix" where
   `cell[i][j]` recolor is the whole intended surface?
4. **bracket/leader per-primitive coverage** (matrix rows 8-9) is my lowest-
   confidence area — several cells are Hypothesized from token presence. Worth a
   render-level spot check if these params are meant to be first-class.
5. **Is the `\cursor` legacy hop worth keeping** given it is exact sugar for two
   `\recolor`, or should docs demote it to an example and steer users to
   `\recolor` + `\cursor`-pin (N-1)?

---

### Appendix — architecture facts underpinning the verdict (Confirmed)

- Command dispatch is primitive-agnostic: `scene.py:619-636` routes each command
  to a handler that writes to shared collections (`shape_states`, `annotations`,
  `highlights`, `focus`, `traces`, `cursors`) keyed by selector string. No
  `isinstance(primitive, …)` branching anywhere in application.
- Per-element diff model is uniform: `differ.py:25` tracks
  `state|value|label|add|remove|highlighted` for every primitive's cells.
- Gating is exactly two-layered: parse-time grammar (`_grammar_commands.py`) and
  emit-time `validate_selector` (16 implementations) + `emit_svg` opt-in.
- All 16 primitives implement `resolve_annotation_point` (annotate point is
  universal); only 5 call `emit_traces_under`/`emit_cursors_under` (trace/cursor
  are selective).
