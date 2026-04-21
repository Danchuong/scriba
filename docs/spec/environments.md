# 04 — Animation & Diagram Environments Spec

> Status: **locked foundation spec** for Scriba v0.3. This file is the single source of truth for the `\begin{animation}` and `\begin{diagram}` LaTeX environments. Wave-3 implementation docs (parser, Starlark host, primitives, SVG emitter, CSS, error catalog) MUST bind to the names, grammar, selectors, HTML shape, and error codes defined here verbatim. Contradictions go to `07-open-questions.md`, not into the code.
>
> Cross-references: [`01-architecture.md`](architecture.md) for the `Pipeline`/`Renderer` contract, [`02-tex-plugin.md`](../guides/tex-plugin.md) for how `TexRenderer` already carves out regions, and [`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md) for the problems that motivated these environments.

## 1. Overview

Scriba v0.3 ships two new LaTeX environments that let problem authors embed algorithmic visualizations directly in problem statements without leaving LaTeX:

- `\begin{animation} ... \end{animation}` — a **sequence of N frames**. Each frame is a self-contained SVG stage plus a narration paragraph. Authors use 12 TikZ-style inner commands to declare primitive shapes, mutate state across frames, and attach narration. In **interactive mode** (default), the renderer emits a widget with step controller, keyboard navigation, and a small inline script. In **static mode**, it expands into a pure filmstrip `<ol>` with zero runtime JS that works in email, print, PDF, RSS, and Codeforces embed. See §8 for mode selection.
- `\begin{diagram} ... \end{diagram}` — a **single static figure**. Same primitive vocabulary minus `\step` and `\narrate`. Intended for standalone illustrations (trees, grids, graphs, DP tables shown at a single moment in time).

Both environments plug into the existing `scriba.core.pipeline.Pipeline` from [`01-architecture.md`](architecture.md) as two additional `Renderer` implementations registered alongside `TexRenderer`:

```python
from scriba import Pipeline, RenderContext
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer, DiagramRenderer

pipeline = Pipeline(renderers=[
    AnimationRenderer(worker_pool=pool),  # name="animation", version=1
    DiagramRenderer(worker_pool=pool),    # name="diagram",   version=1
    TexRenderer(worker_pool=pool),        # name="tex",       version=1
])
```

`AnimationRenderer` and `DiagramRenderer` MUST come **before** `TexRenderer` in the priority list, so that the Pipeline's first-wins overlap rule (see `01-architecture.md` §`Pipeline.render`) carves out `\begin{animation}` / `\begin{diagram}` regions before `TexRenderer.detect()` ever sees them. Outside those regions, everything else continues to be handled by `TexRenderer`. Inside them, the TeX plugin is only invoked through `RenderContext.render_inline_tex` to render the contents of each `\narrate{...}` and any `$...$` inside command parameters.

### Philosophy

1. **Dual output modes.** In **interactive mode** (default), the renderer emits a widget with step controller, keyboard navigation, and a small (~2KB) inline script — suitable for ojcloud tenant and any web platform. In **static mode**, the output is fully static HTML/SVG/CSS with zero runtime JavaScript — an `<ol>` of pre-rendered `<svg>` frames that works in email, RSS, print, PDF, and Codeforces embed. See §8 for mode selection.
2. **LaTeX-native authoring.** Authors stay in the `.tex` mental model: environments, commands, brace-delimited arguments. No YAML, no JSON, no mini-DSL with its own parser.
3. **Build-time determinism.** `\compute{...}` (Starlark) runs once at build time inside a `SubprocessWorkerPool` worker. No randomness, no I/O, no time. Identical source + identical Scriba version produce byte-identical HTML — the consumer's content-hash cache (see `01-architecture.md` §Versioning) continues to work.
4. **Accessible by construction.** Each frame is semantic HTML (`<figure>`, `<ol>`, `<li>`, `<p>`). Narration is real text, not baked into an image. Screen readers walk frames in order.
5. **Print-friendly.** The filmstrip layout falls back to a vertical stack under `@media print` so that a 12-frame binary-search animation prints as 12 labelled figures down the page.

### Scope boundaries

This spec defines the **environment grammar, inner command set, Starlark host contract, HTML output shape, CSS class contract, and error catalog**. It does **not** define: the internal Scene IR datatypes (that is `05-scene-ir.md`), the primitive shape catalog (`primitives.md`), the Starlark worker wire protocol (`07-starlark-worker.md`), the SVG emitter (`08-svg-emitter.md`), or the CSS stylesheet contents (`09-animation-css.md`). Those six downstream docs all bind to this file.

## 2. Environment grammar

Both environments are recognized as LaTeX environments at the top level of a Scriba source. They **do not nest** inside one another, inside `lstlisting`, inside `$...$`, or inside `\begin{tabular}`. They may appear anywhere a top-level paragraph may appear.

### 2.1 BNF

```
document        ::= (text | env)*
env             ::= animation_env | diagram_env

animation_env   ::= "\begin{animation}" opt_options NEWLINE
                    anim_body
                    "\end{animation}"

diagram_env     ::= "\begin{diagram}" opt_options NEWLINE
                    diag_body
                    "\end{diagram}"

opt_options     ::= "" | "[" option_list "]"
option_list     ::= option ("," option)*
option          ::= IDENT "=" option_value
option_value    ::= IDENT | NUMBER | DIMENSION | STRING

anim_body       ::= (comment | decl_cmd)* step_block+
diag_body       ::= (comment | decl_cmd)*

decl_cmd        ::= shape_cmd | compute_cmd | apply_cmd
                  | highlight_cmd | recolor_cmd | annotate_cmd

step_block      ::= "\step" NEWLINE
                    (comment | step_cmd)*
                    narrate_cmd?
                    (comment | step_cmd)*

step_cmd        ::= apply_cmd | highlight_cmd | recolor_cmd | annotate_cmd

shape_cmd       ::= "\shape" brace_arg brace_arg param_brace
compute_cmd     ::= "\compute" compute_brace
apply_cmd       ::= "\apply" brace_arg param_brace
highlight_cmd   ::= "\highlight" brace_arg
recolor_cmd     ::= "\recolor" brace_arg param_brace
annotate_cmd    ::= "\annotate" brace_arg param_brace
narrate_cmd     ::= "\narrate" brace_arg

brace_arg       ::= "{" balanced_text "}"
param_brace     ::= "{" param_list "}"
param_list      ::= "" | param ("," param)*
param           ::= IDENT "=" param_value
param_value     ::= NUMBER | STRING | IDENT | INTERP | LIST
INTERP          ::= "${" IDENT ("[" expr "]")* "}"
LIST            ::= "[" param_value ("," param_value)* "]"

comment         ::= "%" (any char except newline) NEWLINE
```

Where `balanced_text` is a sequence of characters with matched braces (standard LaTeX brace matching), and `compute_brace` is the same but with a single outer `{ ... }` enclosing Starlark source (see §5).

### 2.2 Whitespace and lines

- `\begin{animation}` and `\end{animation}` (likewise for `diagram`) MUST each appear on their own line. Text that precedes `\begin` or follows `\end` on the same line is a parse error (`E1002`). Rationale: trivial and deterministic carve-out regex.
- Inside the body, LaTeX whitespace rules apply: runs of spaces collapse, a blank line is a paragraph break (but there are no paragraphs inside the body; blank lines are simply ignored between commands).
- `%` starts a line comment that runs to the next newline. Comments are legal at the top of the body, between commands, between parameters of the same command (on a new line), and inside a `\step` block. Comments are **not** legal inside a `\compute{...}` body — Starlark has its own `#` comment syntax.
- The `\step` command starts a new frame. Everything between one `\step` and the next (or the closing `\end{animation}`) belongs to the preceding frame. `\step` MUST appear at the start of a line.

### 2.3 Nesting

- Environments do not nest. `\begin{animation}` inside another `\begin{animation}` is `E1003`. `\begin{diagram}` inside `\begin{animation}` is `E1003`.
- Environments may not appear inside `$...$`, `\[...\]`, `\begin{equation}`, `\begin{tabular}`, or `\begin{lstlisting}`. Because `AnimationRenderer` and `DiagramRenderer` run **before** `TexRenderer`, the carve-out happens at the outer level; if an author writes `\begin{animation}` inside a `lstlisting` block, the animation renderer still claims it (the two detectors fight, and the first-wins rule in the Pipeline gives the animation the region). This is intentional: code blocks that contain literal `\begin{animation}` text must escape the backslash (e.g., `\char92 begin{animation}`). Documented as a known limitation in §13.

### 2.4 Environment options

Both environments accept an optional `[key=value,...]` block immediately after `\begin{animation}` / `\begin{diagram}`:

| Key       | Type                   | Default      | Applies to          | Meaning                                                                 |
|-----------|------------------------|--------------|---------------------|-------------------------------------------------------------------------|
| `width`   | dimension (`ex`, `%`)  | `auto`       | animation, diagram  | Hint for stage viewBox width. `auto` lets the primitive choose.         |
| `height`  | dimension (`ex`)       | `auto`       | animation, diagram  | Hint for stage viewBox height.                                          |
| `id`      | ident                  | auto-hashed  | animation, diagram  | Stable scene id used in `data-scriba-scene`. Must be `[a-z][a-z0-9-]*`. |
| `label`   | string                 | none         | animation, diagram  | `aria-label` for the outer `<figure>`.                                  |
| `layout`  | `filmstrip`\|`stack`   | `filmstrip`  | animation only      | Default viewport layout. Print always falls back to `stack`.            |
| `grid`    | `on`\|`off`            | `off`        | diagram only        | Show debug grid (authoring aid only; never in production output).       |

Unknown keys are `E1004` (error, not warning — keep options forward-compatible by versioning, not by silent acceptance).

## 3. Inner commands

There are **12 inner command entries** in this section (including paired
block constructs `\foreach`/`\endforeach` and `\substory`/`\endsubstory`,
which are counted as one each since they form a single block in the AST).
The base 8 commands from v0.3 (`\shape`, `\compute`, `\step`, `\narrate`,
`\apply`, `\highlight`, `\recolor`, `\annotate`) are supplemented by 4
new commands in v0.5: `\reannotate`, `\cursor`, `\foreach` (+ `\endforeach`),
and `\substory` (+ `\endsubstory`). Each entry is listed with its full
signature, allowed context, parameter grammar, error codes, and a one-line
example. Parameter lists use `key=value` pairs inside the final brace
group. Parameter values may be bare idents, numbers, double-quoted
strings, Starlark-computed values via `${name}` / `${name[i]}`
interpolation, or bracketed lists `[a,b,c]`.

### 3.1 `\shape{name}{Type}{params...}`

Declares a primitive instance bound to an identifier inside the current environment's scope.

- **Contexts:** animation, diagram.
- **Signature:** `\shape{<ident>}{<TypeName>}{<param_list>}`
- **Required:** `name` (first brace), `Type` (second brace). `name` must match `[a-z][a-zA-Z0-9_]*` and must be unique within the environment (`E1101` on duplicate).
- **Type** is one of the 16 primitive type names: `Array`, `Grid`, `DPTable`, `Graph`, `Tree`, `NumberLine`, `Matrix`, `Heatmap`, `Stack`, `Plane2D`, `MetricPlot`, `CodePanel`, `HashMap`, `LinkedList`, `Queue`, `VariableWatch`. (`Heatmap` is an alias for `Matrix` — both resolve to the same underlying class, registered via `@register_primitive("Matrix", "Heatmap")`.) Unknown type is `E1102`.
- **Parameters** are primitive-specific (see `primitives.md`). Common ones: `size=`, `rows=`, `cols=`, `data=`, `indices=`, `directed=`, `domain=`.
- **Position constraint:** in `animation`, all `\shape` declarations MUST appear before the first `\step` (`E1051`). In `diagram`, order is free.
- **Error codes:** `E1101` duplicate name; `E1102` unknown type; `E1103` missing required param for that type; `E1104` param type mismatch.
- **Example:** `\shape{dp}{Array}{size=7, labels="0..6"}`

### 3.2 `\compute{...Starlark...}`

Runs a Starlark block inside the environment's scope. Bindings defined in the block become available for later `${interpolation}` in parameter values.

- **Contexts:** animation, diagram. (The user explicitly confirmed `diagram` keeps `\compute`.)
- **Signature:** `\compute{<starlark_source>}`
- **Ordering:** may appear multiple times; bindings accumulate. Later `\compute` blocks see earlier bindings. In `animation`, `\compute` may appear either before the first `\step` (global precompute) or inside a `\step` block (per-frame compute). Per-frame bindings are scoped to that frame only and are dropped at the next `\step`; global bindings persist.
- **Starlark host:** see §5.
- **Error codes:** `E1150` Starlark parse error; `E1151` Starlark runtime error; `E1152` timeout (>5s wall clock); `E1153` step-count cap exceeded (>10^8 ops); `E1154` forbidden feature used (`while`, `import`, `class`, `lambda`, `try`).
- **Example:** `\compute{ dp = [0]*7 \n for i in range(1,7): dp[i] = min(dp[i-1]+a[i-1], dp[i-2]+a[i-2] if i>=2 else 10**9) }`

### 3.3 `\step`

Starts a new frame. Implicit frame boundary: everything from `\step` to the next `\step` or `\end{animation}` is one frame. The very first `\step` closes the "prelude" region (where `\shape` and global `\compute` live) and opens frame 1.

- **Contexts:** animation only. In `diagram` it is `E1050`.
- **Signature:** `\step` (no arguments)
- **Position constraint:** MUST be on its own line. Text on the same line after `\step` is `E1052`.
- **Error codes:** `E1050` `\step` in diagram; `E1052` trailing text; `E1180` warning if frame count > 30; `E1181` error if frame count > 100.
- **Example:** `\step`

### 3.4 `\narrate{LaTeX text with $math$}`

Attaches narration text to the current frame. The brace body is LaTeX and is rendered by calling `RenderContext.render_inline_tex`, which the Pipeline auto-populates with a closure over the registered `TexRenderer` (see `01-architecture.md` §`RenderContext`). Inline math (`$x$`) and the TeX plugin's inline text commands all work.

- **Contexts:** animation only.
- **Signature:** `\narrate{<balanced_latex>}`
- **Cardinality:** **exactly one** `\narrate` per `\step`. Zero emits an empty `<p class="scriba-narration" aria-hidden="true"></p>` (no error code). Two or more in the same step is `E1055` (error).
- **Position constraint:** may appear anywhere inside the `\step` block; emission order is: state mutations first (apply/highlight/recolor/annotate), narration last.
- **Content:** any LaTeX the `TexRenderer` accepts. Authors may mix English and Vietnamese (see cookbook `06-frog1-dp/input.md`).
- **Error codes:** `E1055` duplicate narrate; `E1056` narrate outside `\step`.
- **Example:** `\narrate{Bước 1: khởi tạo $dp[0] = 0$.}`

### 3.5 `\apply{target}{params...}`

Sets a value or attribute on a cell, node, or edge. Used to push data into primitives mid-animation.

- **Contexts:** animation, diagram.
- **Signature:** `\apply{<target_selector>}{<param_list>}`
- **Target:** see §4.
- **Parameters:** primitive-specific but a common core: `value=<any>`, `label=<string>`, `tooltip=<string>`, `arrow_to=<target>` (for graph/tree edges). Unknown param for that primitive is `E1105`.
- **Persistence:** `\apply` is **persistent** — the value sticks on all later frames until overwritten.
- **Error codes:** `E1106` unknown target selector; `E1107` type mismatch (e.g., `value=` with a non-numeric on an `Array` declared numeric).
- **Example:** `\apply{dp.cell[0]}{value=0}`

### 3.6 `\highlight{target}`

Marks a target as the "current focus" of the frame. Ephemeral: cleared automatically at the next `\step`.

- **Contexts:** animation, diagram. In `diagram` it is persistent (there is only one frame).
- **Signature:** `\highlight{<target_selector>}`
- **Parameters:** none. Highlight is a single semantic state, rendered via the `scriba-state-highlight` SVG class.
- **Error codes:** `E1108` unknown target.
- **Example:** `\highlight{dp.cell[3]}`

### 3.7 `\recolor{target}{state=..., color=..., arrow_from=...}`

Changes the **persistent visual state** of a target and/or recolors annotations on it. Persists across frames until overwritten.

- **Contexts:** animation, diagram.
- **Signature:** `\recolor{<target_selector>}{state=<state_name>, color=<color_token>, arrow_from=<selector>}`
- **Parameters:**
  - `state` — optional, sets the visual state of the target. Allowed values: `idle`, `current`, `done`, `dim`, `error`, `good`, `path`. Any other value is `E1109`.
  - `color` — optional, recolors annotation(s) on the target. Valid values: `info`, `warn`, `good`, `error`, `muted`, `path`.
  - `arrow_from` — optional, filters which annotation to recolor by source selector.
  - At least one of `state` or `color` must be present (`E1109`).
- **Rendering:** When `state` is provided, adds the class `scriba-state-<state>` to the targeted SVG element, replacing any previously applied state class for the same target. The Wong CVD-safe palette defined in §9 maps each state to a color pair (fill + stroke) via CSS variables.
- **Deprecation:** The `color=` and `arrow_from=` parameters on `\recolor` are deprecated as of v0.5.0. They still work but emit a `DeprecationWarning`. Use `\reannotate` (§3.9) instead for annotation recoloring.
- **Error codes:** `E1109` unknown state or missing `state`; `E1110` unknown target.
- **Examples:**
  - `\recolor{dp.cell[3]}{state=done}`
  - ~~`\recolor{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}`~~ — use `\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}` instead.

### 3.8 `\annotate{target}{params...}`

Attaches an auxiliary label, arrow, or badge to a target. Persistent by default; pass `ephemeral=true` to restrict to the current frame only.

- **Contexts:** animation, diagram.
- **Signature:** `\annotate{<target_selector>}{<param_list>}`
- **Parameters (locked core):** `label=<string>`, `position=<above|below|left|right|inside>` (default `above`), `color=<info|warn|good|error|muted|path>` (default `info`), `arrow=<bool>` (default `true` for graph/tree, `false` otherwise), `ephemeral=<bool>` (default `false`), `arrow_from=<selector>` (optional, default none — specifies source target for arrow annotations, used for DPTable/Array transition arrows).
- **Error codes:** `E1111` unknown target; `E1112` unknown position; `E1113` unknown color token.
- **Example:** `\annotate{dp.cell[2]}{label="min", color=info}`
- **Placement contract:** pill geometry, collision avoidance, viewBox headroom,
  and known limitations are normative in [smart-label-ruleset.md](smart-label-ruleset.md).

### 3.9 `\reannotate{target}{color=..., arrow_from=...}`

Recolors existing annotation(s) on a target. This is the primary command for changing annotation colors after they have been placed with `\annotate`.

- **Contexts:** animation, diagram.
- **Signature:** `\reannotate{<target_selector>}{color=<color_token>, arrow_from=<selector>}`
- **Parameters:**
  - `color` — required. Valid values: `info`, `warn`, `good`, `error`, `muted`, `path`.
  - `arrow_from` — optional, filters which annotation to recolor by source selector.
- **Persistence:** persistent — the new color sticks until overwritten.
- **Error codes:** `E1109` unknown color token; `E1110` unknown target.
- **Example:** `\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}`

> **Note:** `color=` and `arrow_from=` on `\recolor` are deprecated as of v0.5.0. They still work but emit a `DeprecationWarning`. Use `\reannotate` instead.

### 3.10 `\cursor{targets}{index, prev_state=..., curr_state=...}`

Moves a "current" marker through one or more arrays/primitives. Finds the element currently in `curr_state`, sets it to `prev_state`, then sets the element at `index` to `curr_state`. A convenience macro that replaces 2–3 `\recolor` calls per step.

- **Contexts:** animation prelude or step, diagram.
- **Signature:** `\cursor{<target_list>}{<index>, prev_state=<state>, curr_state=<state>}`
- **Target list:** comma-separated accessor prefixes, e.g., `h.cell, dp.cell`.
- **Parameters:**
  - `index` — required. The new cursor position. Supports `${var}` interpolation.
  - `prev_state` — optional, default `dim`. State to assign to the previously current element.
  - `curr_state` — optional, default `current`. State to assign to the new element.
- **Behavior:** For each accessor prefix in the target list: (1) find the element currently in `curr_state`, (2) set it to `prev_state`, (3) set `prefix[index]` to `curr_state`. If no element is currently in `curr_state` (first cursor call), steps 1–2 are skipped.
- **Error codes:** `E1106` unknown target selector.
- **Examples:**
  - `\cursor{a.cell}{1}`
  - `\cursor{h.cell, dp.cell}{3}`
  - `\cursor{a.cell}{2, prev_state=done, curr_state=good}`

### 3.11 `\foreach{variable}{iterable}...\endforeach`

Loops over a range, list literal, or computed binding, expanding the enclosed body commands once per iteration. Reduces repetitive `\recolor` / `\apply` sequences.

- **Contexts:** animation prelude or step, diagram.
- **Signature:** `\foreach{<ident>}{<iterable>}` ... body ... `\endforeach`
- **Iterable formats:**
  - Range: `0..4` (expands to 0, 1, 2, 3, 4)
  - List literal: `[1,3,5]`
  - Computed binding: `${evens}` (a Starlark list from `\compute`)
- **Body:** one or more inner commands (`\recolor`, `\reannotate`, `\apply`, `\highlight`, `\annotate`, `\cursor`, or nested `\foreach`). The loop variable is available via `${variable}` interpolation inside the body. Commands `\step`, `\shape`, `\substory`, and `\endsubstory` are NOT allowed inside `\foreach`.
- **Nesting:** `\foreach` may be nested inside `\foreach`, up to depth 3 (`E1170` if exceeded).
- **Error codes:** `E1170` nesting exceeds max depth (3); `E1171` empty body; `E1172` unclosed `\foreach` (EOF before `\endforeach`); `E1173` invalid iterable.
- **Example:**
  ```latex
  \foreach{i}{0..4}
    \recolor{a.cell[${i}]}{state=done}
  \endforeach
  ```

### 3.12 `\substory` / `\endsubstory`

Embeds a nested linear frame sequence inside a single parent filmstrip frame, enabling inline drilldowns for recursive sub-computations. See the full extension spec at [`substory.md`](../extensions/substory.md).

- **Contexts:** animation only, inside a `\step` block. Not allowed in the prelude or in `\begin{diagram}` (`E1362`).
- **Signature:** `\substory[title="...", id=...]` ... inner prelude + steps ... `\endsubstory`
- **Nesting:** substories may nest up to depth 3 (`E1360` if exceeded).
- **Scope:** shapes and `\compute` bindings inside a substory are substory-local and destroyed at `\endsubstory`. Mutations to parent-scope shapes are ephemeral (`E1363` warning).
- **Frame budget:** substory frames count toward the parent animation's 100-frame hard limit (`E1364`).
- **Error codes:** `E1360`–`E1369`. See [`substory.md`](../extensions/substory.md) §7 for the full catalog.
- **Example:**
  ```latex
  \substory[title="Sub-problem: dp[3][4]"]
    \shape{sub}{Array}{size=2, data=["R","B"]}
    \step
    \highlight{sub.all}
    \narrate{Trace the sub-computation.}
  \endsubstory
  ```

## 4. Target selector syntax

Selectors identify the SVG element (or group) that a command should mutate. Every selector starts with a `\shape` name and optionally walks into its sub-parts.

### 4.1 BNF

```
selector    ::= IDENT ( "." accessor )*
accessor    ::= "cell" "[" index "]" ( "[" index "]" )?
              | "node" "[" node_id "]"
              | "edge" "[" "(" node_id "," node_id ")" "]"
              | "range" "[" index ":" index "]"
              | "all"
              | IDENT             (* primitive-defined sub-part, e.g. "axis", "label" *)
index       ::= NUMBER | INTERP
node_id     ::= NUMBER | STRING | INTERP
```

### 4.2 Per-primitive selector examples

| Primitive    | Whole shape | Addressable parts                                                                                         |
|--------------|-------------|-----------------------------------------------------------------------------------------------------------|
| `Array`      | `a`         | `a.cell[0]`, `a.cell[${i}]`, `a.range[0:3]`, `a.all`                                                      |
| `Grid`       | `g`         | `g.cell[0][0]`, `g.cell[${r}][${c}]`, `g.all`                                                             |
| `DPTable`    | `dp`        | `dp.cell[${i}]` (1D) or `dp.cell[${i}][${j}]` (2D), `dp.range[0:n]`, `dp.all`                             |
| `Graph`      | `G`         | `G.node[${u}]`, `G.edge[(${u},${v})]`, `G.all`                                                            |
| `Tree`       | `T`         | `T.node[0]` (root), `T.node[${i}]`, `T.edge[(${p},${c})]`, `T.all`                                        |
| `NumberLine` | `nl`        | `nl.tick[${i}]`, `nl.range[${lo}:${hi}]`, `nl.axis`, `nl.all`                                             |

### 4.3 Interpolation

`${name}` inside an index or node id is replaced with the Starlark binding of that name at the time the command is expanded (build time). `${name[i]}` and chained subscripts also work. Examples:

```latex
\compute{ steps = [(0,1),(1,2),(2,3)] }
\apply{dp.cell[${steps[0][1]}]}{value=0}  % -> dp.cell[1]
```

Unknown binding is `E1155`; out-of-range subscript is `E1156`; non-integer where an integer is required is `E1157`.

## 5. `\compute{...}` Starlark host

Scriba embeds Starlark (`go.starlark.net` semantics) executed out-of-process via a persistent `SubprocessWorker` registered in the Pipeline's `SubprocessWorkerPool` under the name `"starlark"`. The worker script's location and wire protocol are the concern of `07-starlark-worker.md`; this section defines the **language contract** that authors see.

### 5.1 Allowed features

| Feature                            | Status      | Notes                                                           |
|------------------------------------|-------------|-----------------------------------------------------------------|
| `def` (named functions)            | allowed     | **Recursive calls allowed.** The host runs with `resolve.AllowRecursion = true` so that recursive algorithms (tree DP, segtree, divide-and-conquer) work naturally. |
| `for` loops                        | allowed     |                                                                 |
| `if` / `elif` / `else`             | allowed     |                                                                 |
| List/dict/set comprehensions       | allowed     |                                                                 |
| Arithmetic (`+ - * / // % **`)     | allowed     |                                                                 |
| Integer, float, string, bool       | allowed     | Ints are arbitrary precision per Starlark spec.                 |
| Lists, dicts, tuples               | allowed     |                                                                 |
| String methods (`.split`, `.join`) | allowed     | Per Starlark stdlib.                                            |
| `while`                            | **forbidden** | Use `for _ in range(N): ... if cond: break`. Error `E1154`.    |
| `import` / `load`                  | **forbidden** | All host APIs are pre-injected. Error `E1154`.                 |
| `try` / `except`                   | **forbidden** | Starlark does not support it; explicit `E1154` if attempted.   |
| `class`                            | **forbidden** | Use dicts or tuples. Error `E1154`.                            |
| `lambda`                           | **forbidden** | Use `def`. Error `E1154`.                                      |
| I/O, time, random, env             | **forbidden** | No `print` to stdout in production; see §5.3.                  |

### 5.2 Pre-injected host API

The worker pre-binds exactly this set of names into the global environment before executing the author's block. Authors MUST NOT rebind them.

```text
len, range, min, max, enumerate, zip, abs, sorted,
list, dict, tuple, set, str, int, float, bool,
reversed, any, all, sum, divmod,
print  # debug sink — captured into artifact.inline_data["debug"] only, never emitted
```

`print(*args)` in a `\compute` block is routed to the worker's captured debug channel. In production builds it is a no-op visible only on `RenderContext.metadata["debug"] == True`. In unit tests, asserting `print` output is an explicit affordance.

### 5.3 Scope rules

- Bindings defined at the top level of a `\compute` block persist into the environment's shared scope and are visible to every later command **and** every later `\compute` in the same environment.
- Bindings defined inside a function body (`def`) are local to that function.
- A `\compute` block inside a `\step` creates **frame-local** bindings that are dropped at the next `\step`. Global and frame-local scopes shadow via standard lexical rules (frame wins).
- Interpolation `${name}` in any later command resolves against the merged scope `global ∪ frame_local`.

### 5.4 Determinism and sandboxing

- **No randomness.** `random` is not injected.
- **No time.** `time` / `now()` is not injected.
- **No I/O.** The worker runs with stdin/stdout reserved for the JSON protocol; filesystem access is unavailable because Starlark's `load()` is disabled.
- **Deterministic dict iteration.** Starlark dicts iterate insertion order by spec; the host does not re-shuffle.
- **Timeout:** 5 seconds wall clock per `\compute` block. Exceeded → kill worker, raise `WorkerError`, surface as `E1152`.
- **Step cap:** 10^8 Starlark operations per block, enforced via the interpreter's step counter. Exceeded → `E1153`.
- **Memory cap:** 64 MB per block (enforced by the worker process's rlimit). Exceeded → worker is killed, `E1151`.

### 5.5 Wire model

The Starlark worker conforms to the same `SubprocessWorkerPool` pattern as `katex_worker.js` (see `01-architecture.md` §`SubprocessWorkerPool` and `services/tenant/backend/app/utils/katex_worker.py:46` for the reference cadence). Requests are one-per-line JSON: `{"op":"eval","env_id":"<hash>","globals":{...},"source":"..."}`. Responses are one-per-line JSON: `{"ok":true,"bindings":{...},"debug":[...]}` or `{"ok":false,"code":"E11xx","message":"...","line":N,"col":M}`. Implementer assigns the exact schema in `07-starlark-worker.md`; it MUST stay compatible with the rules here.

## 6. `\begin{animation}` specifics

### 6.1 Frame semantics

Frames are **delta-based**, not snapshot-based. Each frame inherits the full state of the previous frame and applies its own commands on top. This is what lets authors write a 30-step animation in 30 lines instead of 900.

Concretely, the renderer maintains a `SceneState` dict keyed by target selector:

```text
SceneState = {
  "dp.cell[0]": {"value": 0, "state": "done", "annotations": [...]},
  "dp.cell[1]": {"value": None, "state": "idle", "annotations": []},
  ...
}
```

At the start of frame k:
1. Start from the state at the end of frame k-1 (for frame 1: from the prelude state after all pre-`\step` commands).
2. Clear any target whose state includes `highlight` (highlight is ephemeral).
3. Drop any annotation whose `ephemeral=true`.
4. Apply the frame's commands in source order.
5. Render the resulting `SceneState` as SVG.

### 6.2 Narration cardinality

Each `\step` **SHOULD** have exactly one `\narrate`. Zero → empty narration paragraph emitted with `aria-hidden="true"` (no error code). Two or more → `E1055` error (the intent is ambiguous; authors should merge them).

### 6.3 Frame count limits

- **Soft limit:** 30 frames per `\begin{animation}`. Crossing it emits `E1180` (warning, not error). Rationale: a 30-step filmstrip is the largest thing that reads pleasantly on a laptop screen at `layout=filmstrip`.
- **Hard limit:** 100 frames. Crossing it is `E1181` (error, no HTML emitted). Rationale: cache bloat and download size — 100 SVG stages for one problem is enough to double the problem-statement bundle.

### 6.4 Prelude ordering

Everything before the first `\step` is the **prelude**: `\shape` declarations, global `\compute` blocks, and optionally `\apply` / `\recolor` / `\annotate` commands that set initial state. `\highlight` is **not** allowed in the prelude (`E1053`) — highlights are always per-frame.

## 7. `\begin{diagram}` specifics

Diagram is a single-frame environment. The lifecycle is:

1. Parse body in source order.
2. Execute every `\compute` block into the environment's scope.
3. Execute every `\shape` → `\apply` → `\recolor` → `\annotate` command in source order. `\highlight` is allowed and is persistent (treated as a permanent visual emphasis on the one frame).
4. Emit a single `<figure class="scriba-diagram">` wrapping one `<svg>` stage.

Constraints:

- `\step` is forbidden (`E1050`).
- `\narrate` is forbidden (`E1054`). If the author wants explanatory text alongside the diagram, they use normal LaTeX paragraphs before/after the environment.
- `\compute` is allowed (user-locked decision) for precomputing data like sorted arrays or tree layouts before rendering.
- `width` / `height` / `id` / `label` options apply. `layout` and `grid` do not (conservative choice: `grid=on` is accepted but is authoring-only — it emits a faint grid over the stage).

## 8. HTML output contract (CRITICAL)

Downstream consumers (tenant-frontend, static-site generators, email templates) will bind to the exact HTML shape below. Wave-3 implementation MUST emit this shape verbatim. Class names, data attributes, element order, and nesting are frozen.

### 8 Output modes

`AnimationRenderer` supports two output modes controlled by `RenderContext.metadata["output_mode"]`:

| Mode | Default | JS | Use case |
|------|---------|-----|----------|
| `"interactive"` | Yes | ~2KB inline `<script>` | ojcloud tenant, any web platform |
| `"static"` | No | None | Email, RSS, PDF, Codeforces embed |

**Interactive mode** renders a single widget with:
- Step controller (Prev / Step N of M / Next)
- Keyboard navigation (Arrow keys, Space)
- Progress dots
- Frame transitions (opacity fade)
- All frames stored as data, only one visible at a time

The visual target for interactive mode is `demo_expected.html`.

**Static mode** renders the filmstrip layout from §8.1 (all frames visible, no JS).

Consumers choose the mode via `RenderContext`:
```python
ctx = RenderContext(
    resource_resolver=...,
    theme="light",
    metadata={"output_mode": "interactive"},  # or "static"
)
```

When `output_mode` is not set, default is `"interactive"`.

### 8.1 Animation output (static mode)

```html
<figure class="scriba-animation"
        data-scriba-scene="{scene-id}"
        data-frame-count="{N}"
        data-layout="filmstrip"
        aria-label="{optional label}">
  <ol class="scriba-frames">
    <li class="scriba-frame"
        id="{scene-id}-frame-1"
        data-step="1">
      <header class="scriba-frame-header">
        <span class="scriba-step-label">Step 1 / N</span>
      </header>
      <div class="scriba-stage">
        <svg class="scriba-stage-svg"
             viewBox="0 0 {W} {H}"
             xmlns="http://www.w3.org/2000/svg"
             role="img"
             aria-labelledby="{scene-id}-frame-1-narration">
          <!-- primitive-rendered SVG, one <g data-target="dp.cell[0]"> per addressable part -->
        </svg>
      </div>
      <p class="scriba-narration" id="{scene-id}-frame-1-narration">
        <!-- output of RenderContext.render_inline_tex("Bước 1: khởi tạo $dp[0]=0$.") -->
      </p>
    </li>
    <li class="scriba-frame" id="{scene-id}-frame-2" data-step="2">
      <!-- ... -->
    </li>
    <!-- ... remaining N-2 frames ... -->
  </ol>
</figure>
```

Notes:

- `scene-id` comes from the `id=` option or, if absent, from `"scriba-" + sha256(env_body)[:10]`.
- `data-step` is 1-indexed. `data-frame-count` matches the number of `<li>` children.
- Each `<g>` inside the SVG MUST carry `data-target="<selector>"` so that the CSS contract in §9 can address it generically (without per-scene class explosion).
- `role="img"` + `aria-labelledby` point each frame's SVG at its own narration paragraph, making the figure accessible to screen readers.
- In static mode, there is no `<button>`, no `data-step-current`, no step controller. The animation is a pure filmstrip. In interactive mode (default), the renderer wraps this in a `.scriba-widget` with controls — see §8.

### 8.2 Diagram output

```html
<figure class="scriba-diagram"
        data-scriba-scene="{scene-id}"
        aria-label="{optional label}">
  <div class="scriba-stage">
    <svg class="scriba-stage-svg"
         viewBox="0 0 {W} {H}"
         xmlns="http://www.w3.org/2000/svg"
         role="img">
      <!-- <g data-target="..."> groups, identical convention to animation -->
    </svg>
  </div>
</figure>
```

### 8.3 Narration rendering

Each `\narrate{...}` body is passed to `ctx.render_inline_tex(body)` at render time. The result is a string of HTML (KaTeX MathML + sanitized inline tags) that the Pipeline promises is safe to splice into a `<p>` container. No other Scriba plugin is consulted.

### 8.4 Inline math in all user-authored text (v0.6.1+)

As of v0.6.1, all user-visible text sites pass through `ctx.render_inline_tex` when a TeX renderer is available, so `$...$` inline math works everywhere — not just in `\narrate`. The complete list of KaTeX-enabled text sites:

1. `\narrate{...}` body (original, §8.3)
2. `\annotate{...}{label="$...$"}` — annotation labels
3. Plane2D point labels
4. Plane2D line labels
5. MetricPlot `xlabel`
6. MetricPlot `ylabel` and `ylabel_right`
7. MetricPlot legend series names
8. Graph edge weights
9. CodePanel `caption` label

When `ctx.render_inline_tex is None`, all sites fall back to HTML-escaped plain text.

## 9. CSS contract

Implementation ships two static files under `scriba/animation/static/`:

- `scriba-animation.css` — `.scriba-animation`, `.scriba-frames`, `.scriba-frame`, `.scriba-step-label`, `.scriba-narration`, and all state classes.
- `scriba-diagram.css` — `.scriba-diagram` and any diagram-only overrides.

Both files reference shared primitive styles from `scriba-scene-primitives.css` via `@import` so that cell/node/edge base styles are defined once.

### 9.1 Layout classes

- `.scriba-animation` — container. Default layout:
  ```css
  .scriba-animation .scriba-frames {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: minmax(18rem, 1fr);
    gap: var(--scriba-frame-gap, 1rem);
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    padding-block: 0.5rem;
  }
  .scriba-animation .scriba-frame { scroll-snap-align: start; }
  ```
- `@media (max-width: 640px)` and `@media print` switch to `grid-auto-flow: row` (vertical stack).
- `.scriba-frame` — padded card with `border: 1px solid var(--scriba-border)` and `border-radius: var(--scriba-radius)`. Uses `counter-increment` for the step label.
- `.scriba-frame:target` — highlight if URL fragment matches (`#scriba-abc123-frame-3` jumps to that frame and styles it with `outline: 2px solid var(--scriba-link)`).
- `.scriba-narration` — typography inherited from `scriba-tex-content.css`. Narration paragraphs must not break across columns when `layout=filmstrip`.

### 9.2 State classes on SVG targets

```text
.scriba-state-idle        default fill + stroke
.scriba-state-current     Wong "blue"   (#0072B2)
.scriba-state-done        Wong "green"  (#009E73)
.scriba-state-dim         50% opacity, desaturated
.scriba-state-error       Wong "vermillion" (#D55E00)
.scriba-state-good        Wong "bluish-green" (#009E73) alt tone
.scriba-state-path        Wong "blue"   (#2563eb) — element is part of a highlighted traversal path (e.g., shortest path, optimal solution trace)
.scriba-state-hidden      not rendered — element is present in the document model but invisible. Used for pre-declared nodes/points that become visible in later frames. See docs/guides/hidden-state-pattern.md
.scriba-state-highlight   Wong "yellow" (#F0E442) fill + 2px current-color stroke
```

The Wong palette is chosen because it is CVD-safe (protan, deutan, tritan). Colors are exposed via CSS variables so that the consumer can override them per theme:

```css
:root {
  --scriba-state-idle-fill:      var(--scriba-bg-code);
  --scriba-state-idle-stroke:    var(--scriba-border);
  --scriba-state-current-fill:   #0072B2;
  --scriba-state-current-stroke: #0072B2;
  --scriba-state-done-fill:      #009E73;
  --scriba-state-done-stroke:    #009E73;
  --scriba-state-dim-fill:       color-mix(in oklch, var(--scriba-fg) 10%, transparent);
  --scriba-state-dim-stroke:     color-mix(in oklch, var(--scriba-fg) 20%, transparent);
  --scriba-state-error-fill:     #D55E00;
  --scriba-state-error-stroke:   #D55E00;
  --scriba-state-good-fill:      #009E73;
  --scriba-state-good-stroke:    #009E73;
  --scriba-state-path-fill:      #2563eb;
  --scriba-state-path-stroke:    #2563eb;
  --scriba-state-hidden-fill:    transparent;
  --scriba-state-hidden-stroke:  transparent;
  --scriba-state-highlight-fill: #F0E442;
  --scriba-state-highlight-stroke: currentColor;
}
```

Dark mode via `[data-theme="dark"]` (matching `02-tex-plugin.md`). The Wong hues work in both themes without remapping; only `--scriba-state-idle-*` and `--scriba-state-dim-*` change.

### 9.3 CSS variables namespace

All variables introduced by the animation/diagram plugin are namespaced `--scriba-*` and extend the set defined in `01-architecture.md` §"CSS variable naming convention". No new top-level namespace is created.

## 10. Parser implementation notes (for W2/W3)

### 10.1 Detection

`AnimationRenderer.detect(source)` and `DiagramRenderer.detect(source)` each scan the source with an anchored multi-line regex:

```python
ANIMATION_RE = re.compile(
    r"(?ms)^\\begin\{animation\}(\[[^\]\n]*\])?\s*\n(.*?)\n\\end\{animation\}\s*$",
)
DIAGRAM_RE = re.compile(
    r"(?ms)^\\begin\{diagram\}(\[[^\]\n]*\])?\s*\n(.*?)\n\\end\{diagram\}\s*$",
)
```

The `(?ms)` flags give multi-line anchors and `.` matching newlines. Because the body of `\compute{...}` may contain nested braces, the regex uses a **lazy** body capture and a **line-anchored** closing tag. This means the detector does not try to count braces inside the body; it just trusts that `\end{animation}` appears on its own line. Any author who writes `\end{animation}` as a literal string inside a narration must escape it (`\textbackslash end\{animation\}`), which is the same restriction LaTeX itself imposes.

### 10.2 Priority and overlap

- `AnimationRenderer.priority = 10` (high).
- `DiagramRenderer.priority = 10` (high).
- `TexRenderer.priority = 100` (lower).

Priority is the order passed to `Pipeline(renderers=[...])`. Per `01-architecture.md` §`Pipeline.render`, earlier renderers win overlap resolution. Therefore animation/diagram carve-out happens first, and `TexRenderer` never sees the environment body. This preserves the Pipeline's "detect-then-render-with-placeholders" contract with zero changes to core code.

### 10.3 Body parsing

After `detect()` returns a `Block`, `render_block(block, ctx)` hands `block.raw` to an internal `SceneParser` that walks the 12 commands and emits an internal `SceneIR` (defined in `05-scene-ir.md`). The `SceneIR` is then fed to the Starlark host (for `\compute` evaluation), then to the primitive catalog (for `\shape` instantiation and SVG layout), then to the SVG emitter (for per-frame rendering), then to the HTML stitcher (for the `<figure>` / `<ol>` / `<li>` wrapping).

The `SceneParser` is a small recursive-descent parser over the 12 commands. It does not use the LaTeX parser from `scriba.tex.parser` because the inner grammar is simpler and more rigid; sharing would leak TeX-specific quirks (optional args, catcodes) into a context that does not need them. Narration bodies are the one exception: they are passed verbatim to `ctx.render_inline_tex`.

### 10.4 No overlap with math / code

`AnimationRenderer` and `DiagramRenderer` only match at the top level (their regexes are line-anchored on `^\\begin`), so a `\begin{animation}` that appears inside a `lstlisting` block still matches and wins — which is the documented limitation from §2.3. To write a literal `\begin{animation}` inside a code block, authors escape the backslash: `\char92 begin{animation}`.

## 11. Error catalog

All animation/diagram errors use codes in `E1001..E1299`. The ranges are reserved now; individual codes may be added during W3 implementation but MUST stay within their range. Each code is surfaced on `RendererError.code` (W3 will add a `code: str | None = None` field to `RendererError` via a minor-version bump of `SCRIBA_VERSION`; see `07-open-questions.md` for the binding note).

### 11.1 Parse errors (`E1001..E1049`)

| Code  | Meaning                                                           | Hint                                                         |
|-------|-------------------------------------------------------------------|--------------------------------------------------------------|
| E1001 | Unbalanced braces in command argument                             | Count `{` and `}` in the offending command.                  |
| E1002 | `\begin{...}` / `\end{...}` not on its own line                   | Move to its own line; whitespace-only trailer is fine.       |
| E1003 | Nested environment                                                | Animation and diagram do not nest.                           |
| E1004 | Unknown environment option                                        | Supported keys: §2.4.                                        |
| E1005 | Malformed option value                                            | Use `key=value` with ident / number / string.                |
| E1006 | Unknown inner command                                             | Must be one of the 12 from §3.                                |
| E1007 | Missing required brace argument                                   | See §3 signature.                                            |
| E1008 | Stray text at top level of body (outside any command)             | Wrap inside a command or remove.                             |

### 11.2 Semantic / syntax errors (`E1050..E1099`)

| Code  | Meaning                                                           | Hint                                                         |
|-------|-------------------------------------------------------------------|--------------------------------------------------------------|
| E1050 | `\step` or `\narrate` inside `\begin{diagram}`                    | Use `\begin{animation}` for step-based content.              |
| E1051 | `\shape` after first `\step` in `animation`                       | All shapes must be declared in the prelude.                  |
| E1052 | Trailing content on `\step` line                                  | `\step` takes no argument.                                   |
| E1053 | `\highlight` in animation prelude                                 | Highlights are per-frame.                                    |
| E1054 | `\narrate` in `diagram`                                           | Use surrounding LaTeX text instead.                          |
| E1055 | More than one `\narrate` in a single `\step`                      | Merge them into one narration.                               |
| E1056 | `\narrate` outside a `\step`                                      | Narrations belong to a frame.                                |
| E1057 | Empty `animation` (no `\step`)                                    | Add at least one `\step`.                                    |

### 11.3 Semantic (target / type) errors (`E1100..E1149`)

| Code  | Meaning                                                           | Hint                                                         |
|-------|-------------------------------------------------------------------|--------------------------------------------------------------|
| E1101 | Duplicate `\shape` name                                           | Names must be unique per environment.                        |
| E1102 | Unknown primitive type                                            | See `primitives.md`.                                      |
| E1103 | Missing required primitive parameter                              | Error message names the parameter.                           |
| E1104 | Primitive parameter type mismatch                                 |                                                              |
| E1105 | Unknown parameter on `\apply`                                     |                                                              |
| E1106 | Target selector references unknown shape                          |                                                              |
| E1107 | Value type mismatch on `\apply`                                   |                                                              |
| E1108 | `\highlight` target unknown                                       |                                                              |
| E1109 | Unknown state in `\recolor`, or missing both state and color      | Must be one of: idle, current, done, dim, error, good, path. At least one of state or color required. |
| E1110 | `\recolor` target unknown                                         |                                                              |
| E1111 | `\annotate` target unknown                                        |                                                              |
| E1112 | Unknown annotation position                                       | above/below/left/right/inside.                               |
| E1113 | Unknown annotation color token                                    | info/warn/good/error/muted/path.                                  |

### 11.4 Compute errors (`E1150..E1179`)

| Code  | Meaning                                                           | Hint                                                         |
|-------|-------------------------------------------------------------------|--------------------------------------------------------------|
| E1150 | Starlark parse error                                              | Line/col on the exception.                                   |
| E1151 | Starlark runtime error                                            | Includes traceback.                                          |
| E1152 | Starlark timeout (>5s)                                            | Optimize or split work across multiple `\compute`.           |
| E1153 | Step-count cap (>10^8 ops) exceeded                               | Reduce loop bounds.                                          |
| E1154 | Forbidden feature used (`while`, `import`, `class`, `lambda`, `try`) | See §5.1.                                                 |
| E1155 | Interpolation references unknown binding                          |                                                              |
| E1156 | Interpolation subscript out of range                              |                                                              |
| E1157 | Interpolation value is not an integer where one is required       |                                                              |

### 11.5 Frame count (`E1180..E1199`)

| Code  | Meaning                                                           |
|-------|-------------------------------------------------------------------|
| E1180 | Soft warning: frame count > 30.                                   |
| E1181 | Hard error: frame count > 100.                                    |
| E1182 | Hard error: narration missing on a step and strict mode enabled.  |

### 11.6 Render errors (`E1200..E1249`)

| Code  | Meaning                                                           |
|-------|-------------------------------------------------------------------|
| E1200 | SVG layout failed for a primitive.                                |
| E1201 | Inline TeX renderer (`ctx.render_inline_tex`) raised.             |
| E1202 | Scene hash collision (extremely unlikely; report bug).            |

Remaining codes in `E1058..E1099`, `E1114..E1149`, `E1158..E1179`, `E1183..E1199`, `E1203..E1249`, and `E1250..E1299` are **reserved** for future expansion. Wave-3 implementation adds codes only after consulting this file and `07-open-questions.md`.

## 12. Complete worked examples

### 12.1 Simple animation — binary search

```latex
\begin{animation}[id=bsearch-demo, label="Binary search over a sorted array"]
\shape{a}{Array}{size=8, data=[1,3,5,7,9,11,13,15], labels="0..7"}

\step
\apply{a.cell[0]}{value=1}  % target value we search for is 7
\recolor{a.range[0:8]}{state=idle}
\highlight{a.cell[3]}
\narrate{We search for $7$. Start with $\text{lo}=0$, $\text{hi}=7$, so $\text{mid}=3$ and $a[\text{mid}]=7$.}

\step
\recolor{a.cell[3]}{state=good}
\annotate{a.cell[3]}{label="found!", color=good}
\narrate{$a[3] = 7$, tức là chúng ta đã tìm thấy giá trị cần tìm.}
\end{animation}
```

Rendered HTML (abridged):

```html
<figure class="scriba-animation"
        data-scriba-scene="bsearch-demo"
        data-frame-count="2"
        data-layout="filmstrip"
        aria-label="Binary search over a sorted array">
  <ol class="scriba-frames">
    <li class="scriba-frame" id="bsearch-demo-frame-1" data-step="1">
      <header class="scriba-frame-header">
        <span class="scriba-step-label">Step 1 / 2</span>
      </header>
      <div class="scriba-stage">
        <svg class="scriba-stage-svg" viewBox="0 0 480 64" role="img"
             aria-labelledby="bsearch-demo-frame-1-narration"
             xmlns="http://www.w3.org/2000/svg">
          <g data-target="a.cell[0]" class="scriba-state-idle"><!-- ... --></g>
          <g data-target="a.cell[3]" class="scriba-state-highlight"><!-- ... --></g>
          <!-- ... remaining cells ... -->
        </svg>
      </div>
      <p class="scriba-narration" id="bsearch-demo-frame-1-narration">
        We search for <span class="katex">…</span>. Start with
        <span class="katex">…</span>, so <span class="katex">…</span>
        and <span class="katex">…</span>.
      </p>
    </li>
    <!-- ... frame 2 with a.cell[3] in state=good and a "found!" annotation ... -->
  </ol>
</figure>
```

### 12.2 Animation with `\compute` — Frog DP (cookbook 06)

```latex
\begin{animation}[id=frog1-dp]
\compute{
  h = [2, 9, 4, 5, 1, 6, 10]
  n = len(h)
  INF = 10**9
  dp = [INF] * n
  dp[0] = 0
  for i in range(1, n):
      cand = dp[i-1] + abs(h[i] - h[i-1])
      if i >= 2:
          cand = min(cand, dp[i-2] + abs(h[i] - h[i-2]))
      dp[i] = cand
}

\shape{stones}{NumberLine}{domain=[0,6], ticks=7, labels=${h}}
\shape{dp}{Array}{size=${n}, labels="dp[0]..dp[${n-1}]"}

\step
\apply{dp.cell[0]}{value=${dp[0]}}
\recolor{dp.cell[0]}{state=done}
\highlight{stones.tick[0]}
\narrate{Khởi tạo: $dp[0] = 0$.}

\step
\apply{dp.cell[1]}{value=${dp[1]}}
\recolor{dp.cell[1]}{state=done}
\highlight{stones.tick[1]}
\narrate{Từ tảng $0$ nhảy sang tảng $1$: $dp[1] = dp[0] + |h_1 - h_0| = 7$.}

\step
\apply{dp.cell[2]}{value=${dp[2]}}
\recolor{dp.cell[2]}{state=done}
\highlight{stones.tick[2]}
\narrate{Có thể nhảy từ tảng $0$ hoặc tảng $1$. Chọn phương án nhỏ hơn.}

\step
\apply{dp.cell[3]}{value=${dp[3]}}
\recolor{dp.cell[3]}{state=done}
\highlight{stones.tick[3]}
\narrate{$dp[3] = \min(dp[2] + 1, dp[1] + 4)$.}

\step
\recolor{dp.range[0:${n}]}{state=done}
\annotate{dp.cell[${n-1}]}{label="answer", color=good}
\narrate{Kết quả cuối cùng: $dp[${n-1}] = ${dp[n-1]}$.}
\end{animation}
```

Rendered HTML — identical shape to §12.1 but with 5 `<li class="scriba-frame">` children. Each SVG stage contains two `<g data-target="stones">` and `<g data-target="dp">` roots.

### 12.3 Static diagram — binary tree

```latex
\begin{diagram}[id=bst-demo, label="A small binary search tree"]
\shape{T}{Tree}{root=8, nodes=[8,3,10,1,6,14,4,7,13]}
\recolor{T.node[8]}{state=current}
\annotate{T.node[8]}{label="root", position=above, color=info}
\recolor{T.range[1:4]}{state=dim}
\annotate{T.edge[(3,6)]}{label="left-heavy", color=warn, arrow=true}
\end{diagram}
```

Rendered HTML:

```html
<figure class="scriba-diagram" data-scriba-scene="bst-demo"
        aria-label="A small binary search tree">
  <div class="scriba-stage">
    <svg class="scriba-stage-svg" viewBox="0 0 480 280" role="img"
         xmlns="http://www.w3.org/2000/svg">
      <g data-target="T.edge[(8,3)]"><!-- line --></g>
      <g data-target="T.edge[(8,10)]"><!-- line --></g>
      <g data-target="T.edge[(3,1)]" class="scriba-state-dim"><!-- ... --></g>
      <g data-target="T.edge[(3,6)]" class="scriba-state-dim">
        <line .../>
        <g class="scriba-annotation scriba-annotation-warn">
          <path d="..." /><text>left-heavy</text>
        </g>
      </g>
      <g data-target="T.node[8]" class="scriba-state-current"><!-- circle + text --></g>
      <!-- remaining nodes ... -->
    </svg>
  </div>
</figure>
```

## 13. Out of scope for v0.3

The following are explicitly **not** part of this spec. Attempting to implement any of them in W3 requires an ADR and a bump to this document.

- **Lit widgets, Motion One, hover-to-advance, scroll-to-step synchronization.** The interactive widget now includes an inline JS runtime with a step controller (prev/next buttons) and frame-to-frame WAAPI transitions driven by the differ's transition manifests. However, Lit, Motion One, hover-to-advance, and scroll-to-step synchronization remain out of scope.
- **Nested environments.** Animations inside animations, diagrams inside animations, environments inside `\begin{tabular}`: all forbidden.
- **Custom primitive plug-ins.** Only the 16 registered primitives are usable via `\shape`. Third-party primitive packages are a v0.4+ concern.
- **Live re-compute.** `\compute` runs once at build time. There is no way to reactively recompute when a consumer toggles a prop. If the consumer wants that, they render the same source twice with different `RenderContext.metadata` keys and swap the results at the HTML level.
- **Bidirectional click-to-scroll.** Clicking on narration does not scroll the SVG; clicking on an SVG cell does not jump to a narration line. The only navigation is the `:target` CSS selector driven by the URL fragment, which lets `#scene-id-frame-7` scroll to and highlight frame 7.
- **i18n of `\narrate`.** One language per environment. Authors needing two languages write two `\begin{animation}` blocks and gate each on `RenderContext.metadata["locale"]` at the consumer layer.
- **SVG → PNG rasterization inside Scriba.** The output is SVG only. Consumers needing raster (OG images, PDF print) run their own rasterizer on the emitted SVG.
- **Custom theme primitives.** Only the CSS variables defined in §9.3 and `01-architecture.md`. No author-provided color pickers, no per-environment palette override.
- **Conservative ambiguity resolution:** where this spec is silent — for example, on whether `\compute` may mutate a previously-defined global binding by reassignment across multiple blocks — the implementation MUST take the conservative option (reassignment allowed, but the new value only applies to commands after the redefining `\compute`; no retroactive re-rendering). Record the concrete choice in `07-open-questions.md` rather than divining it from this file.

---

**End of spec.** Wave-3 implementers: bind to this file, bump `AnimationRenderer.version` / `DiagramRenderer.version` whenever any HTML shape in §8 or any class name in §9 changes, and open `07-open-questions.md` entries for every ambiguity you hit. Do not edit this file in place after it ships — amend via a dated appendix so that Wave-3 reviewers can diff against the frozen version.
