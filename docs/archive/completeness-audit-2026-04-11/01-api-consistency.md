# 01 — API Consistency Audit (Completeness)

**Agent:** 1/14 &nbsp;·&nbsp; **Date:** 2026-04-11 &nbsp;·&nbsp; **HEAD:** eb4f017

## Scope

Catalog every parameter accepted by each primitive's `apply_command` and by
its `\shape{}{}{}` constructor, then audit for consistency in:

1. bare token vs `key=value` syntax
2. string vs dict payloads
3. boolean coercion (`true`/`on`/`1`)
4. pluralization (`add_point` vs `points`)
5. verb/noun ordering
6. `\shape` constructor vs `\apply` argument shape

Read-only audit; no source modifications.

Primitives covered: Array, NumberLine, Plane2D, Grid, Tree, Graph, Stack,
Queue, Dict/HashMap, LinkedList, MetricPlot, Matrix, DPTable, VariableWatch
(the cwd ships Grid as `grid.py`; there is no `Grid2D`. `Dict` is
`HashMap`.).

The core fact governing everything below is the parser contract at
`scriba/animation/parser/grammar.py:1449-1452`: every param inside
`{...}` **must** be an `IDENT EQUALS value` pair. A bare identifier
(`pop`, `dequeue`) raises **E1012** at line 1728 before any primitive
sees it. Also, `_parse_param_value` (`grammar.py:1472-1513`) has **no
branch for nested `{...}` dict literals** — a `LBRACE` falls through to
the final `E1005` raise.

---

## Inventory table

### `apply_command` surface (primitives that override it)

| Primitive   | Param key(s)                       | Value shape(s)                                   | Source |
|-------------|-------------------------------------|--------------------------------------------------|--------|
| Stack       | `push`                              | str `"A"` or dict `{label, value}`               | `scriba/animation/primitives/stack.py:137, 141-149` |
| Stack       | `pop`                               | int N (required `=N`; bare token rejected at parser) | `stack.py:138, 151-154` |
| Queue       | `enqueue`                           | scalar (any non-None)                            | `scriba/animation/primitives/queue.py:129, 132-139` |
| Queue       | `dequeue`                           | bool-ish flag (`dequeue=true`)                   | `queue.py:130, 141-144` |
| LinkedList  | `insert`                            | scalar (append) **or** dict `{index, value}`     | `scriba/animation/primitives/linkedlist.py:130, 133-140` |
| LinkedList  | `remove`                            | int index                                        | `linkedlist.py:131, 142-145` |
| HashMap     | `value` (on `bucket[i]` target)     | scalar                                           | `scriba/animation/primitives/hashmap.py:127-145` |
| Plane2D     | `add_point`                         | tuple `(x,y)` / `(x,y,label)` or dict            | `scriba/animation/primitives/plane2d.py:268-269, 186-199` |
| Plane2D     | `add_line`                          | tuple `(label, slope, intercept)` or `(label, {a,b,c})` or dict | `plane2d.py:271-272, 201-228` |
| Plane2D     | `add_segment`                       | nested list `[[x1,y1],[x2,y2]]` or dict          | `plane2d.py:274-275, 230-241` |
| Plane2D     | `add_polygon`                       | list of points or dict `{points}`                | `plane2d.py:277-278, 243-254` |
| Plane2D     | `add_region`                        | dict `{polygon, fill}`                           | `plane2d.py:280-281, 256-261` |
| MetricPlot  | `<series_name>` (dynamic)           | numeric                                          | `scriba/animation/primitives/metricplot.py:224, 234-244` |
| VariableWatch | `value` (on `var[n]`) or `<var_name>` (bulk) | scalar                                | `scriba/animation/primitives/variablewatch.py:115, 122-138` |

### `apply_command` surface — implicit via scene/emitter

Array, NumberLine, Grid, Tree, Graph, Matrix, DPTable, CodePanel **do not
override `apply_command`**. They support only the universal
`value=...`/`label=...` channel that `Scene._apply_apply`
(`scriba/animation/scene.py:524-541`) stores onto `ShapeTargetState` and
then `set_value`/`set_label` replays. There is no way from LaTeX to
mutate their topology (add a tree edge, add a graph node, grow an
array) after declaration.

### `\shape{}{}{}` constructor params (selected)

| Primitive   | Required           | Common optional                                     | Source |
|-------------|--------------------|-----------------------------------------------------|--------|
| Array       | `size` **or** `n`  | `data`, `labels`, `label`                           | `array.py:67, 88, 103-104` |
| DPTable     | (`n`) or (`rows`+`cols`) | `data`, `labels`, `label`                      | `dptable.py:70-72, 128, 146-147` |
| Grid        | `rows`, `cols`     | `data`, `label`                                     | `grid.py:105-106, 138, 145` |
| Matrix      | `rows`, `cols`     | `data`, `colorscale`, `show_values`, `cell_size`, `vmin`, `vmax`, `row_labels`, `col_labels`, `label` | `matrix.py:137-138, 166, 190-197` |
| NumberLine  | `domain`           | `ticks`, `labels`, `label`                          | `numberline.py:75, 94, 120, 123` |
| Stack       | —                  | `items`, `orientation`, `max_visible`, `label`      | `stack.py:89-90, 99, 102-113` |
| Queue       | —                  | `capacity`, `data`, `label`                         | `queue.py:77, 86, 92` |
| LinkedList  | —                  | `data`, `label`                                     | `linkedlist.py:86, 98` |
| HashMap     | `capacity`         | `label`                                             | `hashmap.py:75, 92` |
| Graph       | —                  | `nodes`, `edges`, `directed`, `layout`, `label`     | `graph.py:209, 233, 237-238, 270` |
| Tree        | —                  | `root`, `edges`, `data`, `range_lo`, `range_hi`, `kind`, `label`, `show_sum`, `nodes` | `tree.py:315, 325, 350, 376-377`, and 263-265, 324 (SegTree variant) |
| Plane2D     | —                  | `xrange`, `yrange`, `width`, `height`, `aspect`, `grid`, `axes`, `points`, `lines`, `segments`, `polygons`, `regions` | `plane2d.py:90-138` |
| MetricPlot  | `series`           | `xlabel`, `ylabel`, `ylabel_right`, `grid`, `width`, `height`, `show_legend`, `show_current_marker`, `xrange`, `yrange`, `yrange_right` | `metricplot.py:115, 169-190` |
| VariableWatch | (var list)       | `label`                                             | `variablewatch.py` ctor |

---

## Inconsistencies

### I1. Bare-token rejection forces `=1` suffix on flag commands  &nbsp;— **BREAKING**

The parser (`grammar.py:1449-1452`) requires `IDENT EQUALS value` for
every param. The natural authoring forms are all parse errors:

| Author writes                          | Result | Workaround in cookbook |
|----------------------------------------|--------|------------------------|
| `\apply{stk}{pop}`                     | E1012  | `pop=1` — `examples/cookbook/convex_hull_andrew.tex:112, 164, 174, 222` |
| `\apply{q}{dequeue}`                   | E1012  | `dequeue=true` — `examples/primitives/test_queue.tex:17,24,34` |
| `\apply{ll}{remove}` (implied last)    | E1012  | must pass `remove=<idx>` |

This is exactly the friction that triggered the audit. Stack's
`apply_command` already coerces with `int(pop_val)`
(`stack.py:152`); it would accept a bare `True` as `1` just fine —
the whole failure is in the parser layer.

**Severity: BREAKING** — E1012 is a hard parse error; authors either
learn the idiom or abandon the command.

### I2. `pop` is numeric, `dequeue` is boolean  &nbsp;— **CONFUSING**

Two LIFO/FIFO primitives split on the same operation:

| Primitive | Remove-one-element idiom | Source |
|-----------|-------------------------|--------|
| Stack     | `pop=N` (int count)     | `stack.py:138, 152` |
| Queue     | `dequeue=true` (bool)   | `queue.py:130, 141-144` |
| LinkedList| `remove=<idx>` (int)    | `linkedlist.py:131, 142-145` |

There is no way to dequeue N items in one command, nor any reason pop
must be count-based when both tests and cookbooks only ever use
`pop=1`. Three primitives, three spellings of "remove one".

**Severity: CONFUSING** — all three shapes work individually, but
authors cannot guess one from another.

### I3. Nested dict payloads advertised but unparseable  &nbsp;— **BREAKING** (doc drift)

`apply_command` bodies document dict payloads:
- Stack `push={label:..., value:...}` (`stack.py:134, 141`)
- LinkedList `insert={index:..., value:...}` (`linkedlist.py:125, 134`)
- Plane2D `add_point={x:..., y:..., label:...}` (`plane2d.py:191-193`)
- Plane2D `add_region={polygon, fill}` (`plane2d.py:258-261`)
- `docs/primitives/linkedlist.md:73, 170` show `insert={"index": 1, "value": 5}`

But `_parse_param_value` (`grammar.py:1472-1513`) has **no LBRACE
branch**. A nested `{...}` in LaTeX source raises E1005. The only way
these payloads reach the primitive is via Python test code calling
`apply_command` directly (`tests/unit/test_primitive_linkedlist.py:153`).

Authors who read the public primitive docs and copy the examples get
E1005. This is a silent contract break between layer docs and parser.

**Severity: BREAKING** — documented syntax does not work from LaTeX.

### I4. `dequeue=true` and `grid=on` rely on accidental truthiness  &nbsp;— **COSMETIC** (drifts to CONFUSING)

The parser canonicalises `true`/`false` idents to Python booleans
(`grammar.py:1489-1492`). Any other identifier (e.g. `on`, `yes`,
`1`) passes through as either a string or an int. Observed behaviour:

- `grid=on`: stored as string `"on"` (`plane2d.py:99`). Truthy, so grid
  renders, but `self.grid == "fine"` fine-grid path
  (`plane2d.py:398`) is silently unreachable via `on`.
- `grid=true` / `grid=1` / `grid=fine`: all render grid; only `"fine"`
  enables the 0.2-step fine grid.
- MetricPlot `grid` is coerced via `bool(params.get("grid", True))`
  (`metricplot.py:172`), so **any truthy value works but `fine` is
  lost**. Different coercion than Plane2D.
- `axes=on` / `axes=1` — `bool(params.get("axes", True))` at
  `plane2d.py:100` collapses both to `True`.
- `dequeue=true` vs `dequeue=1` vs `dequeue=yes`: Queue's check is
  `if dequeue_val is not None` (`queue.py:141`), so any non-None
  scalar removes one element; `dequeue=false` also dequeues (!) because
  `False is not None`. Bug.

**Severity: COSMETIC** for grid/axes, **CONFUSING-to-BUG** for
`dequeue=false` silently dequeuing. The Queue bug is cookbook-shaped:
anyone writing `dequeue=false` to guard a branch gets silent corruption.

### I5. Pluralization split between constructor (plural) and apply (singular)  &nbsp;— **CONFUSING**

The `\shape` constructor uses **plural** collection names, `\apply`
uses **singular `add_*` verbs**:

| `\shape` ctor                       | `\apply` counterpart      |
|--------------------------------------|---------------------------|
| `points=[[x,y],...]`                 | `add_point=(x,y)`         |
| `lines=[...]`                        | `add_line=(...)`          |
| `segments=[...]`                     | `add_segment=[...]`       |
| `polygons=[...]`                     | `add_polygon=[...]`       |
| `regions=[...]`                      | `add_region={...}`        |
| Stack `items=[...]`                  | `push="A"` (no `add_item`)|
| Queue `data=[...]`                   | `enqueue="A"`             |
| LinkedList `data=[...]`              | `insert=...`              |
| Tree `edges=[...]`                   | (no add_edge at all)      |
| Graph `edges=[...]`, `nodes=[...]`   | (no add_edge/add_node)    |

Plane2D is the only primitive whose shape ctor plural and apply verb
singular line up symmetrically. Every other collection primitive uses
a different verb for the mutation command than the noun for the
initial bundle. Authors cannot transfer a mental model from one
primitive to the next.

**Severity: CONFUSING** — no breakage, but constant context-switching.

### I6. Verb / noun ordering is `verb_noun` except for the stack/queue set  &nbsp;— **COSMETIC**

Plane2D uses `verb_noun`: `add_point`, `add_line`, `add_segment`,
`add_polygon`, `add_region`. LinkedList uses bare verbs `insert`,
`remove`. Stack/Queue use bare verbs `push`, `pop`, `enqueue`,
`dequeue`. There is no clear rule: "always `add_X`?" (no) /
"always bare verb?" (no). Plane2D is the outlier.

**Severity: COSMETIC** — everyone can learn it, but the ruleset reads
as if two authors never compared notes.

### I7. Collection primitives with no topology mutation at all  &nbsp;— **CONFUSING / completeness gap**

Array, Tree, Graph, Grid, Matrix, DPTable, NumberLine have **no
`apply_command` override** — any topology change (append to array,
add edge, grow grid) is impossible between frames. Authors work around
this by declaring max-sized primitives up front and animating cell
state, which is the right trade-off *if* documented. It is not. The
only hint is the absence of an `add_*` in per-primitive docs.

Graph (`graph.py`) and Tree (`tree.py`) are the most jarring: both
have rich edge lists in the ctor and zero edge mutation commands.

**Severity: CONFUSING** — authors start to type `\apply{g}{add_edge=...}`,
get E1012, and do not discover that the command is simply not
implemented vs. mis-spelled.

### I8. Shape ctor accepts `Array`'s `size` **or** `n`; others enforce just one  &nbsp;— **COSMETIC**

Array accepts both `size` and `n` (`array.py:67`). DPTable accepts
`n` **or** `rows`+`cols` (`dptable.py:70-72`). Grid/Matrix accept only
`rows`+`cols`. There is no rule for when `n` is allowed.

**Severity: COSMETIC** — minor friction on first use.

### I9. `insert` LinkedList accepts positional scalar OR dict  &nbsp;— **CONFUSING**

`linkedlist.py:133-140` interprets `insert=99` as "append 99" and
`insert={...}` as "insert at index" — but the dict form is
unreachable from LaTeX (see I3). So from an author's LaTeX-only
perspective, `insert` is append-only and there is **no way to insert
at a specific index**.

**Severity: BREAKING** — a documented primitive feature is unreachable.

### I10. `MetricPlot` namespace collision risk  &nbsp;— **CONFUSING**

MetricPlot uses *bare series names* as param keys
(`metricplot.py:234-235`): `\apply{plot}{phi=3.2, cost=5.1}`. If a
future apply-verb (e.g. `reset`, `grid`) is added, a series named
`reset` will silently shadow it. VariableWatch has the same pattern
(`variablewatch.py:131-138`). Queue (`enqueue`, `dequeue`) and Stack
(`push`, `pop`) reserve names, so this is asymmetric.

**Severity: COSMETIC today**, upgrades to CONFUSING as primitives grow.

---

## Normalization proposal

Each item lists: what to change, migration cost, and whether it is
parser-only or primitive-only.

### N1. Accept bare-token flags in `_parse_param_value`  *(fixes I1)*
Change `_read_param_brace` (`grammar.py:1445-1470`): after reading
IDENT, if the next token is not EQUALS but is COMMA or RBRACE, store
`params[ident] = True`.
- **Cost:** ~15 lines in one file; zero doc churn if we keep old forms
  working (additive).
- **Risk:** low. No existing parse succeeds that this would break.

### N2. Make `pop` / `dequeue` / `remove` accept bare token  *(depends on N1)*
After N1, Stack `pop` already int-coerces; Queue `dequeue` already
checks `is not None`. LinkedList `remove` must switch from
`int(remove_val)` to "if True, pop the tail" plus "if int, pop that
index".
- **Cost:** 5 lines in `linkedlist.py:142-145`.

### N3. Fix Queue `dequeue=false` silently dequeuing  *(fixes I4 bug)*
Change `queue.py:141` from `if dequeue_val is not None` to
`if dequeue_val`.
- **Cost:** 1 line. **Breaks** any test that passes `dequeue=0` or
  `dequeue=""` expecting a dequeue; `test_primitive_queue.py:141-154`
  uses `True` explicitly, so safe.

### N4. Add dict literal support to `_parse_param_value`  *(fixes I3, I9)*
Add an LBRACE branch that recursively calls `_read_param_brace` and
returns the dict.
- **Cost:** ~20 lines in `grammar.py`, plus grammar tests.
- **Risk:** medium — affects token scoping; interaction with the
  existing `_skip_tokens_past_brace` recovery path must be checked.

### N5. Unify boolean coercion for `grid`, `axes`, `directed`, similar  *(fixes I4 cosmetic half)*
Introduce `_coerce_bool(v)` in `base.py` that maps
`{True, "true", "on", "yes", 1, "1"}` → `True`;
`{False, "false", "off", "no", 0, "0", None}` → `False`;
other strings preserved as-is so Plane2D's `grid="fine"` still works.
- **Cost:** ~15 lines shared helper; ~6 call sites updated.

### N6. Document "this primitive has no topology apply verbs"  *(fixes I7)*
Add a block to each primitive doc (`docs/primitives/*.md`) stating
which `apply_command` verbs it supports, explicitly naming "none" for
Array/Tree/Graph/Grid/Matrix/DPTable/NumberLine.
- **Cost:** docs only; ~1 paragraph per file.

### N7. Add `add_edge` / `add_node` to Graph and Tree  *(fixes I7 for graphs)*
This is a real feature, not a rename. Out of scope for this audit but
worth flagging as the completeness gap most likely to keep biting
authors.
- **Cost:** ~60 lines each; layout recompute; separate PR.

### N8. Reserve MetricPlot / VariableWatch verb names  *(fixes I10)*
When registering series names in `metricplot.py:115` and var names in
VariableWatch ctor, raise E14xx if any collides with a hard-coded
reserved set `{"reset", "grid", "clear", "value", "label"}`.
- **Cost:** 10 lines each.

### N9. Align `\shape` ctor plurals with `\apply` verbs  *(fixes I5, I6)*
Option A (additive): accept `points=` in `\apply` as bulk-add sugar.
Option B (rename): introduce `add_point`/`add_line` as the canonical
verb across *all* collection primitives, deprecate bare `push`/`enqueue`.
- **Cost A:** small, 5 lines per primitive.
- **Cost B:** high — cookbook migration, back-compat window.
- **Recommendation:** A now, B never unless the ruleset is
  versioned.

### N10. Accept `n` as an alias for `size` uniformly, or remove it  *(fixes I8)*
Either add `n` alias to Grid/Matrix, or remove it from Array/DPTable.
- **Cost:** either ~10 lines added or a deprecation warning cycle.

---

## Severity summary

| Severity  | Count | Findings                             |
|-----------|-------|--------------------------------------|
| BREAKING  | 3     | I1, I3, I9                           |
| CONFUSING | 4     | I2, I5, I7, I10 (and I4 half)        |
| COSMETIC  | 3     | I6, I8, I4 (grid/axes half)          |

**Biggest author-visible wins:**
1. **N1 + N2** (bare-token flags) fixes the E1012 that triggered this
   audit; ~20 LoC, additive, no migration.
2. **N4** (dict literal parsing) unlocks already-documented LinkedList
   `insert={index,value}` and Plane2D dict payloads without changing
   any primitive code.
3. **N3** (Queue `dequeue=false` bug) is a 1-line correctness fix.

Everything else (N5–N10) is polish that can land incrementally without
breaking the cookbook.
