# Scriba v0.5.0 — Complete Ruleset Reference

> Single-source reference for all grammar rules, constraints, error codes, CSS contracts,
> HTML shape contracts, and validation limits that define Scriba's behavior.
> Generated from `environments.md`, `primitives.md`, `../planning/architecture-decision.md`,
> extension/primitive specs, and source code analysis.

---

## 1. Environment Grammar

### 1.1 Top-Level Environments

| Environment | Purpose | Frames |
|-------------|---------|--------|
| `\begin{animation}...\end{animation}` | Multi-frame step animation | N frames via `\step` |
| `\begin{diagram}...\end{diagram}` | Single static figure | 1 implicit frame |

**Constraints:**
- Nesting prohibited → `E1003`
- Must appear on own line → `E1002`
- Cannot appear inside `$...$`, `\[...\]`, `\begin{equation}`, `\begin{tabular}`, `\begin{lstlisting}`

### 1.2 Environment Options `[key=value,...]`

| Key | Type | Default | Scope |
|-----|------|---------|-------|
| `width` | dimension (`ex`, `%`) | `auto` | both |
| `height` | dimension (`ex`) | `auto` | both |
| `id` | ident `[a-z][a-z0-9-]*` | `scriba-{sha256[:10]}` | both |
| `label` | string | none | both |
| `layout` | `filmstrip` \| `stack` | `filmstrip` | animation only |
| `grid` | `on` \| `off` | `off` | diagram only |

Unknown key → `E1004`

### 1.3 Line Comments

The `%` character starts a line comment. Everything from `%` to the end of the line is ignored by the lexer. This follows LaTeX comment convention.

---

## 2. Inner Commands (14 total)

### 2.1 Base Commands (12)

| Command | Signature | Contexts | Persistence |
|---------|-----------|----------|-------------|
| `\shape` | `{name}{Type}{params}` | prelude only (animation), anywhere (diagram) | declaration |
| `\compute` | `{...Starlark...}` | prelude or step (animation), anywhere (diagram) | global or frame-local |
| `\step` | (no args) | animation only | starts new frame |
| `\narrate` | `{LaTeX text}` | animation step only | per-frame |
| `\apply` | `{target}{params}` | prelude or step | persistent |
| `\highlight` | `{target}` | step only (animation), anywhere (diagram) | ephemeral (animation), persistent (diagram) |
| `\recolor` | `{target}{state=...}` | both | persistent |
| `\reannotate` | `{target}{color=..., arrow_from=...}` | both | persistent |
| `\annotate` | `{target}{params}` | both | persistent (default), ephemeral if `ephemeral=true` |
| `\cursor` | `{targets}{index}` | prelude or step | persistent |
| `\foreach` | `{variable}{iterable}...body...\endforeach` | prelude or step | expands to body commands |
| `\endforeach` | (no args) | closes `\foreach` | — |

**`\foreach` iterable formats:**

| Format | Example | Meaning |
|--------|---------|---------|
| Range literal | `0..5` | Inclusive integer range `[0,1,2,3,4,5]` |
| Binding reference | `${name}` | Resolves to a list produced by `\compute` |
| List literal | `[1,2,3]` | Parsed via Python `literal_eval` |

### 2.2 Extension Commands (2)

| Command | Signature | Contexts | Spec |
|---------|-----------|----------|------|
| `\substory` | `[title=..., id=...]` | animation step only | E4 |
| `\endsubstory` | (no args) | closes `\substory` | E4 |

> **Note:** `\substory`/`\endsubstory` form a block construct (`SubstoryBlock` in the AST), not individual commands.

---

## 3. Target Selector Syntax

```
selector  ::= IDENT ("." accessor)*
accessor  ::= "cell" "[" idx "]" ("[" idx "]")?
            | "node" "[" node_id "]"
            | "edge" "[" "(" id "," id ")" "]"
            | "range" "[" idx ":" idx "]"
            | "tick" "[" idx "]"
            | "item" "[" idx "]"
            | "all"
            | IDENT "[" idx "]"
            | IDENT
idx       ::= NUMBER | "${" IDENT "}"
node_id   ::= NUMBER | STRING | IDENT | "${" IDENT "}"
```

### Per-Primitive Selectors

| Primitive | Whole | Parts |
|-----------|-------|-------|
| Array | `a` | `.cell[i]`, `.range[i:j]`, `.all` |
| Grid | `g` | `.cell[r][c]`, `.all` |
| DPTable | `dp` | 1D: `.cell[i]`, `.range[i:j]`, `.all`; 2D: `.cell[i][j]`, `.all` |
| Graph | `G` | `.node[id]`, `.edge[(u,v)]`, `.all` |
| Tree | `T` | `.node[id]`, `.node["[lo,hi]"]` (segtree), `.edge[(p,c)]`, `.all` |
| NumberLine | `nl` | `.tick[i]`, `.range[lo:hi]`, `.axis`, `.all` |
| Matrix | `m` | `.cell[r][c]`, `.all` |
| Stack | `s` | `.item[i]`, `.top`, `.all` |
| Plane2D | `p` | `.point[i]`, `.line[i]`, `.segment[i]`, `.polygon[i]`, `.region[i]`, `.all` |
| MetricPlot | `plot` | (whole shape only — series via `\apply` params) |
| CodePanel | `cp` | `.line[i]`, `.all` |
| HashMap | `hm` | `.bucket[i]`, `.all` |
| LinkedList | `ll` | `.node[i]`, `.link[i]`, `.all` |
| Queue | `q` | `.cell[i]`, `.front`, `.rear`, `.all` |
| VariableWatch | `vw` | `.var[name]`, `.all` |

**Generic indexed accessor (`IDENT "[" idx "]"`):** For extended primitives such as Stack and
Plane2D, selectors like `s.item[0]`, `p.point[1]`, or `p.line[i]` use the `IDENT "[" idx "]"`
production. This produces a `NamedAccessor` where the identifier is the element kind and the
index selects a specific element of that kind.

**Bare IDENT as node_id:** In `node[...]` selectors, a bare identifier (e.g. `G.node[A]`) is
treated as a string node ID. This is equivalent to `G.node["A"]` but more concise.

Interpolation: `${name}` resolved from Starlark bindings at build time.

### 3.1 Command Grammar BNF

The complete formal grammar for the body of `\begin{animation}` and `\begin{diagram}` environments.

#### Top-Level Structure

```
animation       ::= options? prelude step_block*

(* Diagram mode is reserved for future implementation. *)

options         ::= "[" option_list "]"
option_list     ::= option ("," option)*
option          ::= IDENT "=" option_value
option_value    ::= STRING | IDENT | NUMBER

prelude         ::= (shape_cmd | compute_cmd | apply_cmd | recolor_cmd
                     | reannotate_cmd | annotate_cmd | cursor_cmd
                     | foreach_block)*
step_block      ::= step_cmd command*
command         ::= compute_cmd | narrate_cmd | apply_cmd | highlight_cmd
                  | recolor_cmd | reannotate_cmd | annotate_cmd
                  | cursor_cmd | foreach_block | substory_block
```

#### Shape Declaration

```
shape_cmd       ::= "\shape" brace_arg brace_arg param_brace?
                  (* \shape{name}{Type}{params} *)
```

`\shape` is only valid in the prelude (before the first `\step`). In diagram mode it may appear anywhere.

#### Step Command

```
step_cmd        ::= "\step" NEWLINE
```

`\step` must be on its own line with no trailing content.

#### Mutation Commands

```
apply_cmd       ::= "\apply" "{" selector "}" param_brace
highlight_cmd   ::= "\highlight" "{" selector "}"
recolor_cmd     ::= "\recolor" "{" selector "}" param_brace
                  (* param_brace must contain state= and/or color= *)
reannotate_cmd  ::= "\reannotate" "{" selector "}" param_brace
                  (* param_brace must contain color= *)
annotate_cmd    ::= "\annotate" "{" selector "}" param_brace
cursor_cmd      ::= "\cursor" "{" target_list "}" "{" cursor_params "}"
                  (* target_list is comma-separated accessor prefixes *)
                  (* cursor_params: index [, prev_state=..., curr_state=...] *)
narrate_cmd     ::= "\narrate" "{" latex_text "}"
compute_cmd     ::= "\compute" "{" starlark_source "}"
```

#### Parameter List

```
param_brace     ::= "{" param_list "}"
param_list      ::= param ("," param)* ","?
param           ::= IDENT "=" param_value
param_value     ::= NUMBER | STRING | IDENT | BOOL | interp_ref
                  | list_value | tuple_value
list_value      ::= "[" (param_value ("," param_value)*)? "]"
tuple_value     ::= "(" (param_value ("," param_value)*)? ")"
interp_ref      ::= "${" IDENT ("[" subscript "]")* "}"
subscript       ::= NUMBER | IDENT
BOOL            ::= "true" | "false"
```

#### Value Types

```
NUMBER          ::= [0-9]+ ("." [0-9]+)?
STRING          ::= '"' [^"]* '"'
IDENT           ::= [a-zA-Z_] [a-zA-Z0-9_]*

state_enum      ::= "idle" | "current" | "done" | "dim"
                  | "error" | "good" | "path"
color_enum      ::= "info" | "warn" | "good" | "error"
                  | "muted" | "path"
position_enum   ::= "above" | "below" | "left" | "right" | "inside"
```

#### Foreach Block

```
foreach_block   ::= "\foreach" "{" variable "}" "{" iterable "}"
                    foreach_body
                    "\endforeach"
variable        ::= IDENT
iterable        ::= range_lit | interp_ref | list_literal
range_lit       ::= NUMBER ".." NUMBER
list_literal    ::= "[" (param_value ("," param_value)*)? "]"
foreach_body    ::= (recolor_cmd | reannotate_cmd | apply_cmd
                     | highlight_cmd | annotate_cmd | cursor_cmd
                     | foreach_block)+
```

The body must contain at least one command. Nesting `\foreach` inside `\foreach` is permitted. Commands `\step`, `\shape`, `\substory`, and `\endsubstory` are not allowed inside `\foreach`.

#### Cursor Command

```
cursor_cmd      ::= "\cursor" "{" target_list "}" "{" cursor_params "}"
target_list     ::= accessor_prefix ("," accessor_prefix)*
accessor_prefix ::= IDENT "." IDENT
cursor_params   ::= index ("," cursor_opt)*
cursor_opt      ::= "prev_state" "=" state_enum
                  | "curr_state" "=" state_enum
index           ::= NUMBER | interp_ref
```

**Syntax:**

```tex
\cursor{shape.accessor}{index}
\cursor{shape.accessor}{index, prev_state=dim, curr_state=current}
\cursor{h.cell, dp.cell}{index}
```

**Defaults:** `prev_state=dim`, `curr_state=current`

**Semantics:**

For each target prefix in the target list:

1. Find the element currently in `curr_state` on that prefix.
2. Set it to `prev_state` (dim it).
3. Set `prefix[index]` to `curr_state` (highlight new position).

If no element is currently in `curr_state` (first cursor call), step 1-2 are skipped.

**Example — before and after:**

```tex
% Before: 3 lines per step
\recolor{h.cell[0]}{state=dim}
\recolor{h.cell[1]}{state=current}
\recolor{dp.cell[1]}{state=current}

% After: 1 line
\cursor{h.cell, dp.cell}{1}
```

`\cursor` supports `${var}` interpolation inside `\foreach`:

```tex
\foreach{i}{1..5}
  \cursor{h.cell, dp.cell}{${i}}
\endforeach
```

#### Substory Block

```
substory_block  ::= "\substory" substory_opts? NEWLINE
                    substory_prelude
                    substory_step+
                    "\endsubstory" NEWLINE
substory_opts   ::= "[" substory_opt ("," substory_opt)* "]"
substory_opt    ::= ("title" | "id") "=" option_value
substory_prelude::= (shape_cmd | compute_cmd)*
substory_step   ::= step_cmd (compute_cmd | narrate_cmd | apply_cmd
                     | highlight_cmd | recolor_cmd | reannotate_cmd
                     | annotate_cmd | cursor_cmd | foreach_block
                     | substory_block)*
```

Both `\substory` and `\endsubstory` must be on their own line. Maximum nesting depth is 3. Substory mutations are ephemeral (parent state is saved and restored).

#### Brace Argument (Balanced Text)

```
brace_arg       ::= "{" balanced_text "}"
balanced_text   ::= (CHAR | brace_arg | "\\" IDENT | interp_ref)*
```

Brace arguments support arbitrary nesting of `{...}` pairs. The parser tracks brace depth and collects all content until the matching closing brace.

---

## 4. Recolor States (Locked Set)

| State | Color (Wong CVD-safe) | Hex |
|-------|----------------------|-----|
| `idle` | neutral gray | `#f6f8fa` |
| `current` | blue | `#0072B2` |
| `done` | green | `#009E73` |
| `dim` | 50% opacity | — |
| `error` | vermillion | `#D55E00` |
| `good` | sky blue | `#56B4E9` |
| `path` | blue | `#dbeafe` (stroke `#2563eb`) |

> **Note:** `highlight` is not a valid `\recolor` state. It is ephemeral and applied only
> via the `\highlight` command. The CSS class `.scriba-state-highlight` exists (see §10.1)
> but cannot be set through `\recolor`.

#### Annotation recoloring (`\reannotate`)

Use `\reannotate` to recolor annotations on a target:

- `color` — required. Valid values: `info`, `warn`, `good`, `error`, `muted`, `path`.
- `arrow_from` — optional, filters which annotation to recolor by source selector.
- Example: `\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}`

> **Deprecation:** `color=` and `arrow_from=` on `\recolor` are deprecated as of v0.5.0.
> They still work but emit a `DeprecationWarning`. Use `\reannotate` instead.

Unknown state → `E1109`

---

## 5. Primitives Catalog (16 types)

### 5.1 Base Primitives (6)

| Type | Required Params | Optional |
|------|----------------|----------|
| `Array` | `size` or `n` | `data`, `labels`, `label` |
| `Grid` | `rows`, `cols` | `data`, `label` |
| `DPTable` | `n` (1D) or `rows`+`cols` (2D) | `data`, `labels`, `label` |
| `Graph` | `nodes`, `edges` | `directed`, `layout`, `layout_seed`, `label` |
| `Tree` | `root` (or auto for segtree) | `nodes`, `edges`, `data`, `kind`, `label` |
| `NumberLine` | `domain=[min,max]` | `ticks`, `labels`, `label` |

### 5.2 Extended Primitives (5)

| Type | Required Params | Key Features |
|------|----------------|-------------|
| `Matrix`/`Heatmap` | `rows`, `cols`, `data` | colorscale (`viridis`/`magma`/`plasma`/`greys`/`rdbu`), `show_values`, `vmin`/`vmax` |
| `Stack` | (none; all optional) | `orientation`, `max_visible`, `items`, `cell_width`, `cell_height`, `gap`, `label`; push/pop delta semantics |
| `Plane2D` | `xrange`, `yrange` | lines/points/segments/polygons/regions, geometry helpers |
| `MetricPlot` | `series` (via `\shape`) | up to 8 series, Wong palette, auto axes, log scale, two-axis mode |
| `Graph layout=stable` | (same as Graph) | SA joint-optimization, fixed positions across frames |

### 5.3 Data-Structure Primitives (5)

| Type | Required Params | Key Features |
|------|----------------|-------------|
| `CodePanel` | `source` or `lines` | Line-by-line highlight, 1-based `.line[i]` selectors, monospace rendering |
| `HashMap` | `capacity` | Bucket-based hash table, `.bucket[i]` selectors, key:value display per bucket |
| `LinkedList` | `data` | Singly-linked node chain, `.node[i]`/`.link[i]` selectors, insert/remove ops |
| `Queue` | (none; `capacity` optional, default 8) | Fixed-capacity FIFO, `.cell[i]`/`.front`/`.rear` selectors, enqueue/dequeue ops |
| `VariableWatch` | `names` | Two-column name-value table, `.var[name]` selectors, per-variable state coloring |

### 5.3 Graph Layout Modes

| Mode | Algorithm | Deterministic |
|------|-----------|---------------|
| `force` (default) | Spring-electric | Yes (seeded) |
| `circular` | Even spacing on circle | Yes |
| `bipartite` | Two-column | Yes |
| `hierarchical` | Top-down layered | Yes |
| `stable` | SA joint-optimization across all frames | Yes (seeded) |

### 5.4 Tree Variants (`kind=`)

| Kind | Required | Auto-built |
|------|----------|-----------|
| (default) | `root`, `nodes`/`edges` | No |
| `segtree` | `data` | Yes, nodes labeled `[lo,hi]` |
| `sparse_segtree` | `range_lo`, `range_hi` | Yes, dynamic nodes |

### 5.5 Plane2D Full Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `xrange` | `[min, max]` | `[-5.0, 5.0]` | Horizontal viewport range |
| `yrange` | `[min, max]` | `[-5.0, 5.0]` | Vertical viewport range |
| `grid` | `bool` or `"fine"` | `true` | Grid lines. `true` = integer grid, `"fine"` = 0.2-interval sub-grid |
| `axes` | `bool` | `true` | Show X/Y axes with arrowheads and tick labels |
| `aspect` | `"equal"` \| `"auto"` | `"equal"` | `"equal"` computes height from width to preserve aspect ratio |
| `width` | `int` | `320` | SVG width in pixels |
| `height` | `int` | `320` | SVG height in pixels (overridden by `aspect="equal"` when not explicit) |
| `points` | list | `[]` | Initial points: `[x, y]`, `[x, y, "label"]`, or `{"x":..., "y":..., "label":...}` |
| `lines` | list | `[]` | Initial lines (see line formats below) |
| `segments` | list | `[]` | Initial segments: `[[x1,y1],[x2,y2]]` or `{"x1":..., "y1":..., "x2":..., "y2":...}` |
| `polygons` | list | `[]` | Initial polygons: list of `[x,y]` vertex pairs (auto-closed) |
| `regions` | list | `[]` | Initial shaded regions: `{"polygon": [...], "fill": "rgba(...)"}` |

**Line formats:**

- Slope-intercept: `["label", slope, intercept]`
- General form `ax + by = c`: `["label", {"a": a, "b": b, "c": c}]`
- Dict form: `{"label": "...", "slope": m, "intercept": b}`

**Dynamic additions via `\apply`:**

| `\apply` key | Value | Description |
|--------------|-------|-------------|
| `add_point` | point spec | Add a point dynamically |
| `add_line` | line spec | Add a line dynamically |
| `add_segment` | segment spec | Add a segment dynamically |
| `add_polygon` | polygon spec | Add a polygon dynamically |
| `add_region` | region spec | Add a shaded region dynamically |

Element cap: 500 per frame → `E1466`

### 5.6 MetricPlot Full Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `series` | list (required) | — | 1--8 series. Each is a string name or `{"name":..., "color":..., "axis":..., "scale":...}` |
| `xlabel` | `str` | `"step"` | X-axis label |
| `ylabel` | `str` | `"value"` | Left Y-axis label |
| `ylabel_right` | `str` | `None` | Right Y-axis label (two-axis mode) |
| `grid` | `bool` | `true` | Show background grid lines |
| `width` | `int` | `320` | SVG width in pixels |
| `height` | `int` | `200` | SVG height in pixels |
| `show_legend` | `bool` | `true` | Show series legend |
| `show_current_marker` | `bool` | `true` | Show vertical dashed line and dots at current step |
| `xrange` | `"auto"` or `[min, max]` | `"auto"` | X-axis range (auto = `[0, N-1]`) |
| `yrange` | `"auto"` or `[min, max]` | `"auto"` | Left Y-axis range (auto = data min/max with 10% padding) |
| `yrange_right` | `"auto"` or `[min, max]` | `"auto"` | Right Y-axis range (two-axis mode) |

**Series config object keys:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | (required) | Series identifier -- must be unique |
| `color` | `str` | `"auto"` | Custom hex color or `"auto"` for Wong palette assignment |
| `axis` | `"left"` \| `"right"` | `"left"` | Which Y-axis to bind to (enables two-axis mode) |
| `scale` | `"linear"` \| `"log"` | `"linear"` | Axis scale; all series on the same axis must share the same scale → `E1487` |

Data is fed per-frame via `\apply{plot}{series_name=value, ...}`. Max 1000 points per series → `E1483`.

### 5.7 Stack Full Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `capacity` or `n` | `int` | (required) | Maximum stack capacity |
| `items` | list | `[]` | Initial items: strings or `{"label": "...", "value": ...}` |
| `orientation` | `"vertical"` \| `"horizontal"` | `"vertical"` | Stack growth direction |
| `max_visible` | `int` | `10` | Max items shown before overflow indicator (`+N more`) |
| `label` | `str` | `None` | Caption text below/beside the stack |

**`\apply` operations:**

| `\apply` key | Value | Description |
|--------------|-------|-------------|
| `push` | `"label"` or `{"label": "...", "value": ...}` | Push one item onto the top |
| `pop` | `int` | Remove N items from the top |

**`.top` selector:** Maps to the last (most recently pushed) item. Recolor/highlight on `.top` applies to `item[len-1]`.

### 5.8 Matrix Full Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rows` | `int` | (required) | Number of rows |
| `cols` | `int` | (required) | Number of columns |
| `data` | list (flat or 2D) | all zeros | Cell values for colorscale mapping |
| `colorscale` | `str` | `"viridis"` | Color mapping function |
| `show_values` | `bool` | `false` | Display numeric values inside cells |
| `cell_size` | `int` | `24` | Cell size in pixels |
| `vmin` | `float` | auto (data min) | Minimum value for colorscale normalization |
| `vmax` | `float` | auto (data max) | Maximum value for colorscale normalization |
| `row_labels` | `list[str]` | `None` | Labels displayed to the left of each row |
| `col_labels` | `list[str]` | `None` | Labels displayed above each column |
| `label` | `str` | `None` | Caption text below the matrix |

---

## 6. Starlark Compute Host

### 6.1 Allowed Features

`def`, `for`, `if/elif/else`, comprehensions, arithmetic, all basic types (int, float, string, bool, list, dict, tuple, set), string methods.

### 6.2 Forbidden Features → `E1154`

`while`, `import`/`load`, `try`/`except`, `class`, `lambda`

### 6.3 Pre-Injected API

```
len, range, min, max, enumerate, zip, abs, sorted,
list, dict, tuple, set, str, int, float, bool,
reversed, any, all, sum, divmod, print,
isinstance, repr, round, map, filter,
chr, ord, pow
```

### 6.4 Resource Limits

| Limit | Value |
|-------|-------|
| Wall clock | 5s |
| Operations | 10^8 |
| Memory | 64 MB |
| Recursion depth | ~1000 (Python default `sys.getrecursionlimit()`) |

> **Note on recursion:** `def` and recursion are allowed (unlike `while`, which is banned).
> However, deeply recursive functions are bounded by Python's default recursion limit (~1000
> stack frames). Exceeding this limit raises `E1158`. The 10^8 operation cap and 5s wall clock
> also apply, so even tail-recursive patterns that stay within the stack limit will be halted
> if they exceed the operation or time budget.

### 6.5 Scope Rules

- Top-level assignments → global (persist across frames)
- Inside `\step` → frame-local (dropped at next `\step`)
- Frame scope shadows global scope
- `${name}` interpolation resolves against `global ∪ frame_local`

---

## 7. Extension Specs

### 7.1 `\hl{step-id}{tex}` (E2)

- Inside `\narrate{...}` only → `E1320`
- Zero JS: uses CSS `:target` selector
- Step ID must match `\step[label=...]` or implicit `step{N}` → `E1321`

### 7.2 `\substory` / `\endsubstory` (E4)

- Animation steps only → `E1362`
- Max nesting depth: 3 → `E1360`
- Substory mutations ephemeral (parent state saved/restored)
- Rendered as nested `<section class="scriba-substory">` with own Prev/Next controls

### 7.3 `@keyframes` Slots (E5)

Named CSS animation presets: `rotate`, `orbit`, `pulse`, `trail`, `fade-loop`.
Inlined into frame `<style>` at build time.

### 7.4 _(reserved)_

### 7.5 `\begin{figure-embed}` (E1)

SVG/PNG pass-through with DOMPurify sanitization. Requires `alt`, `caption`, `credit`.

---

## 8. Frame Lifecycle (Animation)

Each frame inherits full state from previous frame, then:

1. Clear highlights (ephemeral)
2. Drop annotations with `ephemeral=true`
3. Apply frame's commands in source order
4. Clear `apply_params` after snapshot (ephemeral per-frame)
5. Restore frame-local compute bindings

### Frame Count Limits

| Threshold | Action |
|-----------|--------|
| > 30 frames | Warning `E1180` |
| > 100 frames | Error `E1181` (no output) |

### Narration Rules

- Exactly one `\narrate` per `\step`
- Zero → warning (empty `<p>` with `aria-hidden="true"`)
- Two+ → error `E1055`

---

## 9. HTML Output Shape

### 9.1 Output Modes

| Mode | JS | Use case |
|------|----|----|
| `interactive` (default) | ~2KB inline `<script>` | Web platforms |
| `static` | None | Email, RSS, PDF, Codeforces |
| `diagram` | None | Static single-frame `<figure class="scriba-diagram">` (no controls) |

### 9.2 Animation HTML (Static)

```html
<figure class="scriba-animation" data-scriba-scene="{id}" data-frame-count="{N}">
  <ol class="scriba-frames">
    <li class="scriba-frame" id="{id}-frame-1" data-step="1">
      <header class="scriba-frame-header">
        <span class="scriba-step-label">Step 1 / N</span>
      </header>
      <div class="scriba-stage">
        <svg class="scriba-stage-svg" viewBox="0 0 W H" role="img">
          <!-- <g data-target="selector" class="scriba-state-*"> -->
        </svg>
      </div>
      <p class="scriba-narration">...</p>
    </li>
  </ol>
</figure>
```

### 9.3 Interactive Widget HTML

```html
<div class="scriba-widget" id="{id}">
  <div class="scriba-controls">
    <button class="scriba-btn-prev" disabled>Prev</button>
    <span class="scriba-step-counter">Step 1 / N</span>
    <button class="scriba-btn-next">Next</button>
    <div class="scriba-progress"><!-- dots --></div>
  </div>
  <div class="scriba-stage">...</div>
  <p class="scriba-narration">...</p>
  <div class="scriba-substory-container">...</div>
  <script>/* ~2KB controller */</script>
</div>
```

**Keyboard navigation:** The widget sets `tabindex="0"` at initialization.

| Key | Action |
|-----|--------|
| `ArrowRight` or `Space` | Advance to next frame |
| `ArrowLeft` | Go to previous frame |

### 9.4 Substory HTML (inside interactive widget)

```html
<section class="scriba-substory" data-substory-id="{id}" data-substory-depth="{d}"
         aria-label="Sub-computation: {title}">
  <div class="scriba-substory-widget" data-scriba-frames='[...]'>
    <div class="scriba-controls scriba-substory-controls">
      <button class="scriba-btn-prev" disabled>Prev</button>
      <span class="scriba-step-counter">Sub-step 1 / M</span>
      <button class="scriba-btn-next">Next</button>
      <div class="scriba-progress"><!-- dots --></div>
    </div>
    <div class="scriba-stage">...</div>
    <div class="scriba-narration">...</div>
  </div>
</section>
```

### 9.5 Diagram HTML

```html
<figure class="scriba-diagram" data-scriba-scene="{id}">
  <div class="scriba-stage">
    <svg class="scriba-stage-svg" viewBox="0 0 W H" role="img">...</svg>
  </div>
</figure>
```

---

## 10. CSS Contract

### 10.1 State Classes (Wong CVD-Safe Palette)

| Class | Fill | Stroke |
|-------|------|--------|
| `.scriba-state-idle` | `--scriba-state-idle-fill` (#f6f8fa) | `--scriba-state-idle-stroke` |
| `.scriba-state-current` | `--scriba-state-current-fill` (#0072B2) | `--scriba-state-current-stroke` |
| `.scriba-state-done` | `--scriba-state-done-fill` (#009E73) | `--scriba-state-done-stroke` |
| `.scriba-state-dim` | 50% opacity | desaturated |
| `.scriba-state-error` | `--scriba-state-error-fill` (#D55E00) | `--scriba-state-error-stroke` |
| `.scriba-state-good` | `--scriba-state-good-fill` (#56B4E9) | `--scriba-state-good-stroke` |
| `.scriba-state-highlight` | `--scriba-state-highlight-fill` (#F0E442) | `--scriba-state-highlight-stroke` |
| `.scriba-state-path` | `--scriba-state-path-fill` (#dbeafe) | `--scriba-state-path-stroke` (#2563eb) |

### 10.2 Key CSS Custom Properties

```css
/* Base tokens */
--scriba-fg:                     #212529;
--scriba-fg-muted:               #6c757d;
--scriba-bg:                     #ffffff;
--scriba-bg-code:                #f6f8fa;
--scriba-border:                 #d0d7de;
--scriba-link:                   #0969da;
--scriba-radius:                 6px;

/* Frame layout */
--scriba-frame-gap:              1rem;
--scriba-frame-padding:          1rem;
--scriba-frame-border:           1px solid var(--scriba-border);
--scriba-frame-radius:           var(--scriba-radius);

/* Stage (SVG container) */
--scriba-stage-padding:          1.5rem 1rem;
--scriba-stage-bg:               var(--scriba-bg-code);

/* Narration */
--scriba-narration-font-size:    0.92rem;
--scriba-narration-line-height:  1.55;
--scriba-narration-padding:      0.75rem 1rem;

/* Step label */
--scriba-step-label-font:        600 0.72rem ui-monospace, ...;
--scriba-step-label-color:       var(--scriba-fg-muted);

/* Primitive geometry */
--scriba-cell-size:              46px;
--scriba-cell-rx:                5px;
--scriba-cell-stroke-width:      1.5;
--scriba-node-r:                 22px;
--scriba-node-stroke-width:      2;
--scriba-edge-stroke-width:      1.5;
--scriba-tick-stroke-width:      1.5;
--scriba-tick-length:            8px;

/* Primitive typography */
--scriba-cell-font:              700 14px inherit;
--scriba-cell-index-font:        500 10px ui-monospace, monospace;
--scriba-cell-index-color:       var(--scriba-fg-muted);
--scriba-node-font:              700 14px inherit;
--scriba-label-font:             600 11px ui-monospace, monospace;
--scriba-label-color:            var(--scriba-fg-muted);

/* Annotation */
--scriba-annotation-font:        600 11px ui-monospace, monospace;
--scriba-annotation-arrow-width: 2.0;

/* Annotation color tokens */
--scriba-annotation-info:        #0072B2;
--scriba-annotation-warn:        #E69F00;
--scriba-annotation-good:        #009E73;
--scriba-annotation-error:       #D55E00;
--scriba-annotation-path:        #2563eb;
--scriba-annotation-muted:       var(--scriba-fg-muted);

/* Widget (interactive wrapper) */
--scriba-widget-shadow:          0 1px 3px rgba(0,0,0,.05), 0 8px 24px rgba(0,0,0,.05);
--scriba-widget-radius:          12px;
--scriba-widget-focus-ring:      2px solid var(--scriba-link);

/* Progress bar */
--scriba-progress-height:        3px;
--scriba-progress-bg:            var(--scriba-border);
--scriba-progress-fill:          var(--scriba-link);
```

### 10.3 Responsive Breakpoints

| Media Query | Behavior |
|-------------|----------|
| `@media (max-width: 640px)` | Vertical stack layout |
| `@media print` | Vertical stack, expand all substories |
| `@media (prefers-reduced-motion: reduce)` | Disable transitions |

### 10.4 Dark Mode

Via `[data-theme="dark"]`. Wong palette works in both themes. Only `idle` and `dim` states remap.
Dark mode overrides these base tokens: `--scriba-fg`, `--scriba-fg-muted`, `--scriba-bg`,
`--scriba-bg-code`, `--scriba-border`, `--scriba-link`, plus `idle`/`dim`/`highlight` state tokens.

### 10.5 Plane2D CSS Classes

| Class | Scope | Description |
|-------|-------|-------------|
| `.scriba-plane-grid` | `<g>` | Container for grid lines |
| `.scriba-plane-axes` | `<g>` | Container for X/Y axis lines and arrowheads |
| `.scriba-plane-content` | `<g>` | Transformed group for geometric elements (math-to-SVG) |
| `.scriba-plane-point` | `<g>` | Individual point wrapper (contains `<circle>`) |
| `.scriba-plane-line` | `<g>` | Individual line wrapper (contains `<line>`) |
| `.scriba-plane-segment` | `<g>` | Individual segment wrapper (contains `<line>`) |
| `.scriba-plane-polygon` | `<g>` | Individual polygon wrapper (contains `<polygon>`) |
| `.scriba-plane-region` | `<g>` | Individual shaded region wrapper (contains `<polygon>`) |
| `.scriba-plane-labels` | `<g>` | Container for tick labels and element labels |

CSS transitions on point `circle` (`fill`, `stroke`) and line/segment `line` (`stroke`) at 150ms ease.
Grid uses `--scriba-border`; axes use `--scriba-fg`. Labels use `--scriba-font-mono`.

### 10.6 MetricPlot CSS Classes

| Class | Scope | Description |
|-------|-------|-------------|
| `.scriba-metricplot` | root | Top-level container |
| `.scriba-metricplot-grid` | `<g>` | Background grid container |
| `.scriba-metricplot-gridline-h` | `<line>` | Horizontal grid lines |
| `.scriba-metricplot-gridline-v` | `<line>` | Vertical grid lines |
| `.scriba-metricplot-axes` | `<g>` | Axes container (lines, ticks, labels) |
| `.scriba-metricplot-xticks` | `<g>` | X-axis tick marks and labels |
| `.scriba-metricplot-yticks` | `<g>` | Left Y-axis tick marks and labels |
| `.scriba-metricplot-yticks-right` | `<g>` | Right Y-axis tick marks and labels (two-axis mode) |
| `.scriba-metricplot-right-axis` | `<line>` | Right Y-axis line |
| `.scriba-metricplot-right-axis-label` | `<text>` | Right Y-axis label text |
| `.scriba-metricplot-series` | `<g>` | Container for all series polylines |
| `.scriba-metricplot-series-{i}` | `<g>` | Individual series wrapper (0-indexed) |
| `.scriba-metricplot-line` | `<polyline>` | Series data polyline |
| `.scriba-metricplot-step-marker` | `<g>` | Current-step marker container |
| `.scriba-metricplot-marker` | `<line>` | Vertical dashed marker line |
| `.scriba-metricplot-step-dot` | `<circle>` | Dot on each series at current step |
| `.scriba-metricplot-legend` | `<g>` | Legend container |
| `.scriba-metricplot-legend-label` | `<text>` | Legend text label |

Grid lines: `stroke: --scriba-border`, `stroke-width: 0.5`, `opacity: 0.6`.
Print media: lines forced to `stroke: #000`.

---

## 11. Error Code Catalog

### Parse Errors (E1001–E1049)

| Code | Meaning |
|------|---------|
| E1001 | Unclosed `\begin{animation}` |
| E1002 | `\begin`/`\end` not on own line |
| E1003 | Nested animation/diagram |
| E1004 | Unknown environment option key |
| E1005 | Malformed option value |
| E1006 | Unknown inner command |
| E1007 | Missing required brace argument |
| E1008 | Stray text at body top level _(reserved)_ |
| E1009 | Selector syntax error (malformed selector expression) |
| E1010 | Unexpected token in selector |
| E1011 | Unterminated string in selector |
| E1012 | Expected token not found |
| E1013 | Source exceeds maximum size of 1 MB |

### Semantic Errors (E1050–E1099)

| Code | Meaning |
|------|---------|
| E1050 | `\step` in diagram |
| E1051 | `\shape` after first `\step` |
| E1052 | Trailing content on `\step` line |
| E1053 | `\highlight` in animation prelude |
| E1054 | `\narrate` in diagram |
| E1055 | Multiple `\narrate` per `\step` |
| E1056 | `\narrate` outside `\step` |
| E1057 | Empty animation (no `\step`) _(reserved)_ |
| E1058 | Duplicate `\step` label _(reserved)_ |

### Target/Type Errors (E1100–E1149)

| Code | Meaning |
|------|---------|
| E1101 | Duplicate `\shape` name |
| E1102 | Unknown primitive type |
| E1103 | Missing required primitive parameter |
| E1104 | Parameter type mismatch |
| E1105 | Unknown `\apply` parameter |
| E1106 | Unknown target selector |
| E1107 | Value type mismatch |
| E1108 | `\highlight` unknown target |
| E1109 | Unknown `\recolor` state |
| E1110 | `\recolor` unknown target |
| E1111 | `\annotate` unknown target |
| E1112 | Unknown annotation position |
| E1113 | Unknown annotation color |

### Compute Errors (E1150–E1159)

| Code | Meaning |
|------|---------|
| E1150 | Starlark parse error |
| E1151 | Starlark runtime error |
| E1152 | Timeout (>5s) |
| E1153 | Step-count cap exceeded |
| E1154 | Forbidden feature (`while`, `import`, `class`, `lambda`, `try`) |
| E1155 | Unknown interpolation binding |
| E1156 | Subscript out of range |
| E1157 | Non-integer subscript |
| E1158 | Recursion depth exceeded (~1000 frames) |

### Foreach Errors (E1170–E1179)

| Code | Meaning |
|------|---------|
| E1170 | `\foreach` nesting exceeds max depth (3) |
| E1171 | `\foreach` with empty body |
| E1172 | Unclosed `\foreach` (EOF before `\endforeach`) |
| E1173 | Invalid iterable in `\foreach` (not a range, list, or binding) |
| E1174 | `\foreach` variable name conflicts with existing binding _(reserved)_ |

### Frame Count (E1180–E1199)

| Code | Meaning |
|------|---------|
| E1180 | Warning: >30 frames |
| E1181 | Error: >100 frames |
| E1182 | Missing narration (strict mode) |

### Render Errors (E1200–E1249)

| Code | Meaning |
|------|---------|
| E1200 | SVG layout failed |
| E1201 | Inline TeX renderer error |
| E1202 | Scene hash collision |

### `\hl` Errors (E1320–E1329)

| Code | Meaning |
|------|---------|
| E1320 | `\hl` outside `\narrate` |
| E1321 | Unknown step_id |
| E1322 | TexRenderer not registered |
| E1323 | `\hl` in diagram |
| E1324 | Cross-block step_id |

### `\substory` Errors (E1360–E1369)

| Code | Meaning |
|------|---------|
| E1360 | Max nesting depth exceeded (depth > 3) |
| E1361 | Unclosed `\substory` (EOF or parent `\step` reached before `\endsubstory`) |
| E1362 | `\substory` outside `\step` |
| E1363 | _(reserved for future use)_ |
| E1364 | _(reserved for future use)_ |
| E1365 | `\endsubstory` without `\substory` |
| E1366 | Substory has zero `\step` blocks (warning) |
| E1367 | _(reserved for future use)_ |
| E1368 | Text on the same line as `\substory` or `\endsubstory` |

### Matrix Errors (E1420–E1429)

| Code | Meaning |
|------|---------|
| E1422 | Invalid colorscale / vmin >= vmax |
| E1423 | Data shape mismatch |
| E1424 | NaN in data (warning) |
| E1425 | Matrix cell count exceeds 10,000 |

### Plane2D Errors (E1460–E1469)

| Code | Meaning |
|------|---------|
| E1460 | `xrange` or `yrange` has equal endpoints (degenerate viewport) |
| E1461 | Line has no intersection with viewport (warning) |
| E1462 | Polygon not closed — auto-closed by emitter (warning) |
| E1463 | Point or segment partially/fully outside viewport (warning) |
| E1464 | `plane2d.*` helper raised a Starlark runtime error |
| E1465 | `aspect` is not `"equal"` or `"auto"` |
| E1466 | More than 500 elements in a single frame |

### MetricPlot Errors (E1480–E1489)

| Code | Meaning |
|------|---------|
| E1480 | No series declared (empty `series` list) |
| E1481 | More than 8 series |
| E1482 | Fewer than 2 data points in current frame (warning) |
| E1483 | More than 1000 points in a single series |
| E1484 | Log scale with non-positive value; clamped to epsilon (warning) |
| E1485 | Duplicate series name |
| E1486 | `xrange=[a,a]` — degenerate zero-width x range |
| E1487 | Two series on the same axis declare different `scale` values |

### Graph Layout Errors (E1500–E1509)

| Code | Meaning |
|------|---------|
| E1500 | SA optimizer did not converge (warning) |
| E1501 | `layout=stable` with N > 20 nodes (warning; falls back to force) |
| E1502 | `layout=stable` with T > 50 frames (warning; falls back to force) |
| E1503 | Fell back from `layout=stable` to `layout=force` (warning) |
| E1504 | `layout_lambda` out of range `[0.01, 10]`; clamped (warning) |
| E1505 | `layout_seed` is not a non-negative integer |

---

## 12. Determinism Contract

**Identical source + identical Scriba version = byte-identical HTML**

- No randomness in `\compute` (no `random` module)
- No I/O or time-dependent operations
- Dict iteration is insertion-order (Starlark spec)
- `layout_seed` for Graph/Tree (deterministic layout)
- Optional CI check: `SCRIBA_CHECK_DETERMINISM=1`

---

## 13. Validation Limits Summary

| Constraint | Limit | Error Code |
|-----------|-------|------------|
| Frames (soft) | 30 | E1180 (warning) |
| Frames (hard) | 100 | E1181 (error) |
| Starlark ops | 10^8 | E1153 |
| Starlark wall clock | 5s | E1152 |
| Starlark memory | 64 MB | E1151 (surfaces as E1151) |
| Substory nesting depth | 3 | E1360 |
| Foreach nesting depth | 3 | E1170 |
| Graph stable nodes | 20 | E1501 (warning) |
| Graph stable frames | 50 | E1502 (warning) |
| Matrix cells | 10,000 | E1425 |
| Foreach iterable length | 10,000 | E1173 |
| Source size | 1 MB | E1013 |
| Plane2D elements per frame | 500 | E1466 |
| MetricPlot points per series | 1,000 | E1483 |

---

## 14. Cross-References

| Document | Content |
|----------|---------|
| `environments.md` | Locked base spec (grammar, commands, HTML shape, CSS) |
| `primitives.md` | 6 base primitive specs |
| `../planning/architecture-decision.md` | Pivot #2 rationale (10 additions) |
| `extensions/hl-macro.md` | E2 spec |
| `extensions/substory.md` | E4 spec |
| `extensions/keyframe-animation.md` | E5 spec |
| `extensions/figure-embed.md` | E1 spec |
| `primitives/matrix.md` | P1 spec |
| `primitives/stack.md` | P2 spec |
| `primitives/plane2d.md` | P3 spec |
| `primitives/metricplot.md` | P4 spec |
| `primitives/graph-stable-layout.md` | P5 spec |
| `animation-css.md` | CSS stylesheet spec |
