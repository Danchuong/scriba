# Unified surface-language spec — `\trace`, `block[…]`, `color="state:…"` + `leader`

> Author-facing language spec unifying three JudgeZone feature requests (driver: CSES 1071
> number-spiral) into one consistent `.tex` surface. **No repo source modified.** Repo @ `main`
> `9062239`, scriba 0.22.1, `.venv/bin/python`. This document is the *surface / grammar* half of the
> work (how the author types it); the *model* and *audit* halves are owned by the other two agents.
>
> Sibling investigations (read first, cited throughout):
> `investigations/feat-trace-primitive.md`, `feat-label-state-colors.md`, `feat-grid-block-selector.md`.
>
> **Evidence grades.** *Confirmed* = read in source or **executed** this session · *Deduced* =
> logical consequence of confirmed facts · *Hypothesized* = design proposal, not yet built.
> Codebase claims carry `path:line`. Prior-art claims cite the DSL + feature by name (external).
> The load-bearing grammar claims (`state:` colon, `leader`/`bracket` accepted, `block`/`trace`
> baseline errors) were **run** via `scratchpad/us_colon_probe.py` — see §9.

---

## 1. Hand-off Brief (3 sentences)

Three additive surface constructs land one consistent `.tex` vocabulary onto the existing
`\annotate`/`\recolor` grammar with **zero** golden churn: a cross-primitive **`\trace{shape}{cells=…}`**
command (a rounded arrow threading cell centers), a 2D **`block[r0:r1][c0:c1]`** region selector (the
symmetric 2D twin of the 1D `range[lo:hi]`, usable in `\recolor`/`\highlight`/`\annotate`/`\reannotate`
with an opt-in `bracket=true` dashed outline), and a **`color="state:<name>"`** annotation-color form
plus an opt-in **`leader=true`** that makes a label's hue match its cell's `\recolor` state and force a
connector to it. The single most important surface finding — **executed, not assumed** — is that the
`state:` color *must be written quoted* (`color="state:current"`): a bare `state:current` tokenizes as
`state` · `:` · `current` and dies with **E1012** at the colon, whereas the quoted form lexes as one
string and arrives intact at the color validator (today it correctly reports **E1113** "unknown color",
which is exactly where the `state:` branch attaches). Everything else already parses today (`cells=[[r,c],…]`
is legal nested-list value grammar; `leader=`/`bracket=` are silently-accepted unknown keys), the name
clash `state:path` vs bare `path` is resolved *for free* by the mandatory `state:` namespace (they are
literally different strings), and the only genuinely new grammar is `block`'s two-range accessor and the
`\trace` command name — so the whole vocabulary is opt-in and additive.

---

## 2. Prior-art lessons (what to borrow, what to avoid)

Five sources, chosen because each already solved one of our three problems (path-arrow, region-select,
color-reference). Each lesson maps to a concrete decision below.

**L1 — Route arrows through *named anchors*, not raw coordinates (TikZ).**
TikZ draws a poly-arrow as `\draw[->,rounded corners] (a.center) -- (b.center) -- (c.center);` — the
path is a list of **node references**, and `rounded corners` rounds the bends while the vertices stay
pinned to the nodes. *Borrow:* `\trace` takes a list of **cell addresses** (`cells=[[r,c],…]`), not
pixels, and rounds joins via `stroke-linejoin:round` (feat-trace §4.2) — the vertex stays nailed to the
resolved cell center even as dynamic `_cell_width` grows (feat-trace §4). *Avoid:* TikZ's `to[out=..,in=..]`
Bézier-angle sugar — it is powerful but a foreign mini-language; scriba already has arc-Béziers for
`\annotate`, and a polyline is the honest shape for "thread these cells."

**L2 — A region is one selector that *expands* to members (Graphviz `cluster`, TikZ `fit`).**
Graphviz `subgraph cluster_0 { a b c }` draws one bounding box around a set; TikZ's `fit` library computes
an AABB over listed nodes. Both keep "the region" as a *single addressable thing* whose rendering is a
rectangle. *Borrow:* `block[r0:r1][c0:c1]` is one selector; for `\recolor` it **expands** to the cell
product (feat-block §3.2), for `\annotate` it resolves to a block AABB the `bracket` outline hugs
(feat-block §3.3). *Avoid:* Graphviz clusters double as layout constraints — ours is pure annotation, no
layout effect (block never moves cells).

**L3 — Color by *semantic class reference*, not by re-typing the hex (D2 `class`, Mermaid `classDef`).**
D2's `A.class: highlight` and Mermaid's `classDef done fill:#eee; class A,B done` let a mark *point at a
named style* so it stays in sync with the palette. *Borrow:* `color="state:current"` makes the label
**reference** the `\recolor` state token (`--scriba-state-current-*`) instead of re-declaring a near-blue —
so it is guaranteed identical to the cell and dark-adapts for free (feat-label §3 option ii). *Avoid:*
Mermaid's `linkStyle 3 stroke:#f00` (index-addressed inline hex) — brittle, non-semantic, and it is the
exact drift (`ARROW_STYLES` vs CSS token, feat-label §2b) we are trying not to widen.

**L4 — Namespacing kills the name clash; do not invent an alias (D2 keyword scoping).**
D2 distinguishes a *style* keyword from a *shape* named the same by scope/position, not by renaming.
Our clash is `path` the annotation color vs `path` the recolor state. *Borrow:* the `state:` prefix **is**
the namespace — `color=path` (bare) = annotation token; `color="state:path"` (quoted) = the state token.
No alias, no reserved-word gymnastics; two distinct strings, disambiguated by construction (feat-label §7 Q3).
*Avoid:* minting a synonym like `color=curblue` — it multiplies names users can't tell apart (feat-label §3 option i weakness).

**L5 — Draw-on is a property of the *path element*, reuse the mechanism you already animate (Manim `Create`/`TracedPath`).**
Manim animates any `VMobject` stroke with one `Create(mobject)` regardless of what the path *means*; the
animation keys on the geometry, not the semantics. *Borrow:* a `\trace` emits the same
`<g data-annotation><path/><polygon/></g>` shape the existing `stroke-dashoffset` JS already animates
(feat-trace §5) — zero JS change, and reduced-motion/print show the full static path for free. *Avoid:*
standing up the unwired CSS `@keyframes trail` preset (feat-trace §5.5) — a second, parallel animation
path is strictly more risk than reusing the one that already ships.

---

## 3. Grammar conventions (Confirmed this session — the rules the spec obeys)

Locked from source + execution so the three features stay 100% consistent with what exists:

| Convention | Rule | Evidence |
|---|---|---|
| **Arg names** | `snake_case` (never kebab). `arrow_from`, `prev_state`, `curr_state`. | Confirmed — `SCRIBA-TEX-REFERENCE.md:406,493`; new args follow: `dot`, not `start-dot`. |
| **Enums / bools** | **bare**: `color=good`, `state=done`, `arrow=true`, `ephemeral=true`. | Confirmed — `_grammar_commands.py:233-244`; probe `color=good` → OK. |
| **Strings** | **double-quoted**: `label="+5"`. | Confirmed — `_grammar_tokens.py:300-302`. |
| **Selector values** | **double-quoted**, re-parsed: `arrow_from="dp.cell[1]"`. | Confirmed — `_grammar_commands.py:245-255`. |
| **Values with `:` , spaces, brackets** | **must be quoted** or the lexer splits them. | **Confirmed (executed)** — bare `color=state:current` → **E1012** "expected IDENT, got COLON" (§9). |
| **Lists** | `[a,b]`; nested `[[r,c],…]`; tuples `(u,v)`. Nested lists are legal `ParamValue`. | Confirmed — `ast.py:38`, `_grammar_values.py:29-42`; probe `cells=[[0,0],[0,1]]` lexes. |
| **Selector brace-arg** | raw balanced string: `{g.block[0:1][0:1]}`. | Confirmed — `_grammar_tokens.py:163-204`. |
| **Unknown param keys** | **silently ignored** on `\annotate` (not rejected). | **Confirmed (executed)** — `leader=true`, `bracket=true` → OK today (§9). |

Consequence: `leader`/`bracket`/`dot`/`id` can be introduced with **no** parse-error churn — old sources
that never used them are byte-identical, and the new keys start being honored the moment the emit side reads them.

---

## 4. Final per-feature spec

### 4.1 `\trace{<shape>}{…}` — poly-cell arrow through cell centers

```latex
\trace{<shape>}{ cells=[[r,c],…] | cells=[i,…],
                 color=<info|warn|good|error|muted|path> | color="state:<name>",
                 label="<tex/text>",
                 arrowhead=<end|start|both|none>,
                 dot=<none|start>,
                 id=<ident>,
                 ephemeral=<true|false> }
```

| Param | Type | Default | Description |
|---|---|---|---|
| `cells` | list | *(required, ≥2)* | Ordered cell addresses the polyline threads, center→center. 2D items `[r,c]` for Grid/DPTable-2D/Matrix; bare-int items `i` for Array/DPTable-1D/NumberLine. `<2` items → **E1492**. |
| `color` | enum \| `"state:X"` | `info` | Annotation color token, or a quoted state-reference (§4.3). Reuses `VALID_ANNOTATION_COLORS`; invalid → **E1113**. |
| `label` | string | *(none)* | Optional pill at the **path midpoint** (routes through the smart-label engine, inherits wrap/dash/placement). |
| `arrowhead` | enum | `end` | `end` (tip at last cell), `start` (tip at first), `both`, `none`. Invalid → **E1494**. |
| `dot` | enum | `none` | `start` draws a small origin `<circle r=3>` at the first cell; `none` omits it. |
| `id` | ident | *(auto: positional)* | Stable trace handle for draw-on keying and a future `\retrace`/`\untrace`. Auto-assigned by declaration order when omitted. |
| `ephemeral` | bool | `false` | Persistent by default (mirrors `\annotate`); `true` clears it at the next `\step`. |

**Address forms — 1D vs 2D** *(Deduced from feat-trace §3.3, §4)*. The command carries raw index tuples;
each primitive family maps them to a selector suffix and resolves the **center**:

| Target primitive | `cells=` item form | Suffix | Center source | Grade |
|---|---|---|---|---|
| Grid | `[r,c]` | `cell[r][c]` | `resolve_label_anchor` = center | Confirmed `grid.py:197-211` |
| DPTable-2D | `[r,c]` | `cell[r][c]` | center | Confirmed `dptable.py:591-607` |
| Matrix | `[r,c]` | `cell[r][c]` | center (+ header offsets) | Confirmed `matrix.py:292-308` |
| DPTable-1D | `i` | `cell[i]` | center | Confirmed `dptable.py:591-607` |
| Array | `i` | `cell[i]` | center (Array overrides anchor) | Confirmed `array.py:428-441` |
| NumberLine | `i` | `tick[i]` | **needs `resolve_trace_point` override** (default anchor is tick-top) | Confirmed `numberline.py:173-195` |

**Geometry / z-order / draw-on** *(feat-trace §4-5)*: polyline `M…L…L…` with `stroke-linejoin:round`;
inline `<polygon>` arrowhead (reuse `_svg_helpers.py:2809-2835`); emitted **before the cell loop** so it
sits *under* the digits; draw-on rides the existing `annotation_add` transition (`data-annotation="trace:{id}-solo"`),
static-full under reduced-motion/print.

**1D example (DP reconstruction):**
```latex
\shape{dp}{DPTable}{size=6, data=[0,3,5,6,9,12], labels="dp[0]..dp[5]"}
\step
\trace{dp}{cells=[0,2,3,5], color=path, arrowhead=end, label="reconstruct"}
```

**2D example (Grid spiral shell):**
```latex
\trace{g}{cells=[[2,0],[2,1],[2,2],[1,2],[0,2]], color=good, arrowhead=end, label="odd shell"}
```

**`path=` corner shorthand — deferred to v2** *(recommend)*. `path=[[2,0],[2,2],[0,2]]` (corners only,
auto-interpolating the collinear cells between consecutive corners) is pure parse-time sugar over `cells=`
and can fast-follow; `cells=` fully covers CSES 1071. Ship `cells=` in v1.

### 4.2 `block[r0:r1][c0:c1]` — 2D region selector (+ `bracket=true`)

A **selector**, not a command — usable anywhere a Grid/DPTable-2D/Matrix cell selector is:

```latex
\recolor{g.block[0:1][0:1]}{state=done}                 % fills the 2×2 region
\highlight{g.block[0:1][0:1]}                            % ephemeral variant (same expansion)
\annotate{g.block[0:2][0:2]}{label="$(m-1)^2$", bracket=true, color=info}
\reannotate{g.block[0:2][0:2]}{color=good}              % re-target/recolor the block annotation
```

- **Inclusive both ends** on both axes (matches `range[lo:hi]`, `_frame_renderer.py:381`). `block[0:1][0:1]` = the 2×2.
- **`\recolor`/`\highlight`/`\cursor`** expand to the cell product `cell[r][c]` for `r∈r0..r1, c∈c0..c1`
  (feat-block §3.2) — expanded suffixes are already valid, so state/set logic is unchanged. Out-of-bounds
  or reversed (`r0>r1`) → the existing **soft E1115** warning + drop (mirror range; feat-block §7.2). **No new E-code.**
- **`\annotate`/`\reannotate`** keep the raw `block[…]` target; the emitter resolves block **center**
  (anchor) + block **AABB** (feat-block §3.3).
- **`bracket=true`** (only meaningful on an `\annotate` of a `block[…]` target) paints a **no-fill dashed
  rounded rect** hugging the region (inset ~3px, radius ~6px, stroke = annotation color @0.55 opacity,
  dash `4,3`), emitted *after* the cells so it never occludes digits; label pill defaults **above**,
  block AABB as its obstacle (feat-block §3.5). Default off → **zero golden churn**.

**Interpolation works for free** — `block[${r0}:${r1}][${c0}:${c1}]` resolves via the generic
`fields(acc)` walk in `scene._resolve_selector` (feat-block §8 Q1, Confirmed).

### 4.3 `color="state:<name>"` (label↔state color) + `leader=true`

**`color="state:<name>"`** — a quoted annotation color that **references** a `\recolor` state's own tokens
so the label is guaranteed to match the cell and dark-adapts for free (feat-label §3 option ii).

- **Surface (Confirmed, executed): the value MUST be quoted.** `color="state:current"` → lexes as one
  string, reaches the color validator (§9). Bare `color=state:current` → **E1012** at the colon. This is
  the single hard surface rule for this feature.
- **`<name>` ∈ `VALID_STATES`** (`current`, `done`, `dim`, `error`, `good`, `path`, `idle`, `highlight`).
  Invalid suffix → **E1113** ("invalid annotation color") — the same catalog entry that already fires for
  a bad plain color, so no new code (E1114 is *taken* — shape kwargs, `errors.py:182`).
- **Name-clash resolution (`state:path` vs `path`)** — the `state:` prefix is a mandatory namespace, so the
  two are **different strings by construction**: bare `color=path` = annotation `path` token (blue
  `#0b68cb`); `color="state:path"` = the recolor `path` state's text token (grey `#5e6669`). No alias needed.
- **Applies to** `\annotate`, `\reannotate`, and `\trace` (all validate `color` against the same set).
- **Legibility mapping** *(feat-label §3)*: `current`→its saturated fill (`#0070d5`, AA on white);
  `good`/`error`→their border; `done`/`dim`/`idle`→a dark/muted neutral (their faint tint is illegible on
  the white pill). Free dark variants come from `--scriba-state-*` already having them.

```latex
\recolor{g.cell[3][0]}{state=current}
\annotate{g.cell[3][0]}{label="$m^2=16$", color="state:current", leader=true}   % label blue matches cell
```

**`leader=true`** — an opt-in boolean that **forces** a connector (dotted `<line>` + `<circle>` dot) from
the pill perimeter to the target, ignoring the automatic gate (feat-label §4). Default `false` → no churn.

| Param | Type | Default | Description |
|---|---|---|---|
| `leader` | bool | `false` | Force a leader line from the pill to the target cell, even when the auto-gate would not fire. Drawn as a dotted `<line>` (recolors via `.scriba-annotation-{color} > line`, so it dark-adapts) + a dot at the cell anchor. |

- **Applies to** `\annotate` (arc, position, and plain-arrow paths) and `\reannotate`. On `\trace` it is
  accepted but low-value (the trace pill already sits *on* the path midpoint) — recommend leaving it off there.

---

## 5. Selector matrix — after the `block` extension

The symmetry rule: **`range[lo:hi]` is the 1D span; `block[r0:r1][c0:c1]` is its 2D twin.** 1D primitives
carry `range`; 2D primitives (which have no meaningful 1D range) gain `block`. Added column in **bold**.

| Primitive | Cell/Item | Tick | Range (1D span) | **Block (2D region)** | All | Trace `cells=` form |
|---|---|---|---|:---:|---|---|
| Array | `.cell[i]` | — | `.range[i:j]` | **—** | `.all` | `[i,…]` |
| Grid | `.cell[r][c]` | — | — | **`.block[r0:r1][c0:c1]`** | `.all` | `[[r,c],…]` |
| DPTable-1D | `.cell[i]` | — | `.range[i:j]` | **—** | `.all` | `[i,…]` |
| DPTable-2D | `.cell[r][c]` | — | — (none today) | **`.block[r0:r1][c0:c1]`** | `.all` | `[[r,c],…]` |
| NumberLine | — | `.tick[i]` | `.range[lo:hi]` | **—** | `.all` | `[i,…]` (→`tick[i]`) |
| Matrix | `.cell[r][c]` | — | — | **`.block[r0:r1][c0:c1]`** | `.all` | `[[r,c],…]` |

- **Grid / DPTable-2D / Matrix** get `block`; **Array / DPTable-1D / NumberLine** do **not** (1D — a
  `block[…]` on them expands to `cell[r][c]` which their `validate_selector` rejects → correct soft E1115
  "not supported here", feat-block §3.2 Deduced). No 2D primitive gains `range`; no 1D primitive gains `block`.
- `block` is inclusive both axes; `range` semantics unchanged.

---

## 6. Error-code table (final)

| Code | Feature | Condition | Stage | Status | Evidence |
|---|---|---|---|---|---|
| **E1490** | trace | `\trace` references an undeclared shape | scene apply | new (band free) | Confirmed band empty §9 / `errors.py:412-420` |
| **E1491** | trace | a `cells=` index is not addressable on the target | scene/emit | new — upgrades today's silent skip | feat-trace §8 |
| **E1492** | trace | fewer than 2 points in `cells=` | parse | new | feat-trace §8 |
| **E1493** | trace | target primitive is not cell-addressable (no `resolve_trace_point`) | scene apply | new | feat-trace §8 |
| **E1494** | trace | unknown `arrowhead` enum | parse | new | feat-trace §8 |
| **E1113** | trace / state-color | invalid `color` (plain **or** `state:` suffix) | parse | **reuse** (do not mint E1114 — taken) | **Confirmed (executed)** §9; `errors.py:181` |
| **E1012** | state-color | *(author error)* bare, unquoted `state:current` — colon split | lex | existing — surfaces the "quote it" mistake | **Confirmed (executed)** §9 |
| **E1115** | block | block OOB / reversed on `\recolor`/`\highlight` (soft warn, dropped) | expand/validate | **reuse** (mirror range) — zero churn | Confirmed `_frame_renderer.py:447`; feat-block §7.2 |
| *(silent)* | block | block OOB on `\annotate` (no anchor → no paint) | emit | existing behavior, consistent | feat-block §7.2 |
| *E1413–E1419* | block | *(reserved)* hard "Grid/DPTable block bounds out of range", only if strictness later wanted | — | reserved, not used v1 | Confirmed band free `errors.py:271-284` |

Two conventions, deliberately different: **trace mints a fresh band (E1490-E1494)** because it is a new
command whose failures have no existing home; **block reuses soft E1115** because it is a new *selector* and
every other selector's OOB is soft-E1115 — inventing a hard code there would be inconsistent. `state:`
reuses E1113 because that catalog entry already means "invalid annotation color."

---

## 7. Deliverable drafts (paste-ready)

### 7a. REFERENCE sections (format matches `SCRIBA-TEX-REFERENCE.md` §5.8/§5.9)

---
#### `\trace{shape}{params...}` *(new §5.x)*

Draws one rounded polyline through the **centers** of an ordered chain of cells, with an arrowhead at the
end. Cross-primitive (Grid, DPTable, Array, NumberLine, Matrix). Persistent by default; painted **under**
the cell values. Use it to *point a direction* a sequence of `\recolor`s can only imply — e.g. the fill
order of a spiral, a DP reconstruction chain, a traversal.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `cells` | list | *(required)* | Ordered addresses, ≥2. `[[r,c],…]` on 2D primitives; `[i,…]` on 1D. |
| `color` | enum \| `"state:X"` | `info` | `info`, `warn`, `good`, `error`, `muted`, `path`, or a quoted `"state:<name>"` (§11). |
| `label` | string | *(none)* | Pill at the path midpoint (supports `$…$`). |
| `arrowhead` | enum | `end` | `end`, `start`, `both`, `none`. |
| `dot` | enum | `none` | `start` marks the origin cell with a small dot. |
| `id` | ident | *(auto)* | Stable handle; auto-assigned by order when omitted. |
| `ephemeral` | bool | `false` | `true` clears the trace at the next `\step`. |

```latex
% 2D — thread the odd shell of a number spiral (values 5→9)
\trace{g}{cells=[[2,0],[2,1],[2,2],[1,2],[0,2]], color=good, arrowhead=end, label="odd shell"}

% 1D — DP reconstruction path
\trace{dp}{cells=[0,2,3,5], color=path, label="reconstruct"}
```

> **Gotchas.** (1) `cells` needs ≥2 entries (E1492). (2) A mistyped coordinate that is off-grid raises
> **E1491** — it does *not* silently vanish. (3) The trace is drawn *below* the digits by design; it
> never occludes values. (4) Under `prefers-reduced-motion`/print the full path shows immediately (the
> draw-on is progressive enhancement only).

---
#### `block[r0:r1][c0:c1]` region selector + `bracket=true` *(add to §8 Selectors and §5.8 Annotate)*

A 2D region selector for Grid, DPTable-2D, and Matrix — the area-valued twin of the 1D `range[i:j]`.
**Inclusive** on both axes: `g.block[0:1][0:1]` names the top-left 2×2.

- `\recolor{g.block[0:1][0:1]}{state=done}` — recolors every cell in the region.
- `\highlight{g.block[0:1][0:1]}` — ephemeral variant.
- `\annotate{g.block[0:2][0:2]}{label="…", bracket=true}` — with `bracket=true`, draws a dashed rounded
  outline hugging the region, label pill above. Use to name a region whose *meaning is its area* (e.g. an
  `$(m-1)^2$` counting block). Without `bracket`, the label anchors at the region center.

**`bracket=true`** (bool, default `false`) is 2D-only sugar on a `block[…]` annotate target; on a 1D
`range[…]` it is a no-op (the automatic span bracket already fires). Grid still has **no** 1D `.range`.

---
#### `color="state:<name>"` and `leader=true` *(add to §5.8, §5.9, §11)*

`color` accepts, besides the six plain tokens, a **quoted** `"state:<name>"` form that makes the label's
hue match a `\recolor` state so a callout on a `current`/`done`/`good`/… cell is color-consistent and
dark-adapts automatically.

- **Write it quoted:** `color="state:current"`. An unquoted `color=state:current` is a **syntax error**
  (E1012) because the `:` is tokenized separately.
- `<name>` is any `\recolor` state; an unknown one raises **E1113**.
- `state:path` (the recolor path state, grey) is distinct from the plain `path` color (blue) — the
  `state:` prefix disambiguates.

`leader=true` (bool, default `false`) forces a dotted connector from the label pill to its target cell,
even when the automatic leader gate would not fire — useful when a pill is pushed far from a dense grid.

```latex
\recolor{g.cell[3][0]}{state=current}
\annotate{g.cell[3][0]}{label="$m^2 = 16$", color="state:current", leader=true}
```

### 7b. Ruleset R-cards (draft — continues `ruleset.md`, next free is R-35; highest today is R-34)

> Format matches the `smart-label-ruleset.md` cards (`### R-NN — title` / **Normative** / **Since** /
> prose / **What/Why/Where-enforced** / refs). Assign contiguous **R-35, R-36, R-37**.

```markdown
### R-35 — `\trace` polyline: under-cells z-order & center anchor
**Normative:** MUST   **Since:** v0.23.0 (proposed)

**What.** `\trace{shape}{cells=…}` emits one `<path>` (rounded-join polyline) through each cell's
resolved *center* plus an inline `<polygon>` arrowhead, inside a `<g data-annotation="trace:{id}-solo">`.
The group MUST be emitted **before** the primitive's cell loop (so it paints beneath the digits) and MUST
read the dynamic `self._cell_width`, never the static `CELL_WIDTH`. Center resolution goes through
`resolve_trace_point` (default = `resolve_label_anchor`); NumberLine MUST override it to the tick center.
**Why.** The feature's value is pointing a *direction* without hiding the values it threads; a stroke over
the digits or a stale pitch would defeat both. Reusing the annotation `<g>` shape lets the shipped
`stroke-dashoffset` draw-on animate it with zero JS change and gives static-full output under
reduced-motion/print. **Where-enforced.** Build-time emit: base `emit_traces` inserted before the cell
loop in grid/dptable/array/numberline; differ emits `annotation_add` for new trace ids. Off-grid `cells`
index → E1491 (hard, not a silent skip). `<2` points → E1492.
**Code ref (proposed):** `primitives/base.py` (`emit_traces`, `resolve_trace_point`); `differ.py` (`_diff_traces`).
**Test ref (proposed):** `tests/unit/test_primitive_trace.py` (z-order + center per primitive).

### R-36 — `block[r0:r1][c0:c1]` region: inclusive expansion & dashed bracket
**Normative:** MUST   **Since:** v0.23.0 (proposed)

**What.** `block[r0:r1][c0:c1]` is inclusive on both axes and valid only on 2D cell primitives
(Grid, DPTable-2D, Matrix). `\recolor`/`\highlight`/`\cursor` MUST expand it to the cell product
`cell[r][c]` for `r∈r0..r1, c∈c0..c1`; `\annotate` MUST resolve it to the block center (anchor) and block
AABB (box), computed from each primitive's own `_cell_rect` so it tracks dynamic cell widths. With
`bracket=true`, `\annotate` MUST paint a no-fill dashed rounded rect (inset ~3px, radius ~6px, stroke =
annotation color @0.55, dash `4,3`) emitted **after** the cells. **Why.** A region whose meaning is its
area (an `$(m-1)^2$` block) has no name in the cell/`range` vocabulary; `block` is the symmetric 2D twin of
`range`. `fill="none"` guarantees the outline never masks values. **Where-enforced.** `_expand_selectors`
(recolor path); `resolve_annotation_point`/`_box`/`validate_selector` (annotate path). OOB/reversed →
soft E1115 (recolor) or no-anchor no-paint (annotate) — mirrors every other selector; **no new E-code**.
**Code ref (proposed):** `parser/selectors.py` (`_parse_block`), `_frame_renderer.py` (`block_re`),
`_svg_helpers.py` (`emit_block_bracket_svg`).
**Test ref (proposed):** `tests/unit/test_block_bracket.py`; expand + anchor tests per 2D primitive.

### R-37 — Label↔state color binding & forced leader
**Normative:** MUST   **Since:** v0.23.0 (proposed)

**What.** `\annotate`/`\reannotate`/`\trace` accept `color="state:<name>"` (name ∈ `VALID_STATES`), which
MUST bind the label's text/stroke to the state's own CSS token (`--scriba-state-<name>-*`) so it matches
the `\recolor`ed cell and inherits the dark variant. The value MUST be written quoted; an unquoted
`state:<name>` is a lexer error (E1012) and MUST NOT be special-cased. An unknown suffix reuses E1113.
`leader=true` MUST force a dotted `<line>`+dot connector from the pill perimeter to the target, bypassing
the automatic leader gate. **Why.** Before this, a label on a `current` cell could only borrow `info`
(a *different* blue) and a label on a `done` cell had no match at all; and a pill displaced from a dense
grid had no reliable tie-line. Referencing the state token (not re-typing a hex) keeps the two in sync and
resolves the `path`/`state:path` clash by namespace, not alias. **Where-enforced.** Parser color branch in
`_parse_annotate`/`_parse_reannotate`/`_parse_trace`; emit class `scriba-annotation-state-{name}`;
forced-leader block in the three emit paths. Default-off `leader` → zero golden churn.
**Code ref (proposed):** `parser/_grammar_commands.py` (color branch), `_svg_helpers.py` (state class + forced leader),
`static/scriba-scene-primitives.css` (`--scriba-annotation-state-*`).
**Test ref (proposed):** `tests/unit/test_parser_annotation_cmds.py`; contrast test ≥4.5:1 per state token.
```

### 7c. Acceptance example — CSES 1071 number spiral (all three features)

> **Grade: Hypothesized (acceptance target).** Lines using `\shape`/`\recolor`/plain `\annotate` parse
> today; the `\trace`, `block[…]`, and `color="state:…"` lines are the forward target this spec defines.
> This is the doc a later acceptance test renders. The 4×4 window is a valid CSES-1071 spiral prefix
> (corner of shell *m* = *m²*; shells alternate fill direction).

```latex
\begin{animation}[id="spiral-1071", label="CSES 1071 number spiral: mirrored shell fill"]
\shape{g}{Grid}{rows=4, cols=4,
  data=[[1, 2, 9, 10],
        [4, 3, 8, 11],
        [5, 6, 7, 12],
        [16,15,14,13]],
  label="Number spiral (n=4)"}
\narrate{Each shell $m$ fills between $(m-1)^2+1$ and $m^2$. Odd and even shells fill in \emph{mirror} directions.}

\step
% --- Shell 3 (odd, values 5..9): traced upward/rightward ---
\recolor{g.cell[2][0]}{state=current}
\trace{g}{cells=[[2,0],[2,1],[2,2],[1,2],[0,2]], color=good, arrowhead=end, dot=start,
          label="odd shell $\to$ up", id="shell3"}
\narrate{Shell 3 is odd: fill runs \textbf{up-and-right}, $5 \to 9$.}

\step
% --- Shell 4 (even, values 10..16): the (m-1)^2=9 block is already filled; trace the mirror ---
\annotate{g.block[0:2][0:2]}{label="$(m-1)^2 = 9$ filled", bracket=true, color=info}
\trace{g}{cells=[[0,3],[1,3],[2,3],[3,3],[3,2],[3,1],[3,0]], color=path, arrowhead=end,
          label="even shell $\to$ down (mirror)", id="shell4"}
\narrate{Shell 4 is even: fill runs \textbf{down-and-left}, the mirror of shell 3.}

\step
% --- Corner of shell 4 is m^2 = 16; label it in the cell's own colour with a forced leader ---
\recolor{g.cell[3][0]}{state=current}
\annotate{g.cell[3][0]}{label="$m^2 = 16$", color="state:current", leader=true}
\narrate{The shell closes at its corner $m^2 = 16$.}
\end{animation}
```

Feature coverage: **`\trace`** (odd shell + even-shell mirror, distinct `id`s, `dot=start`), **`block[…]`**
(`\recolor` of the current shell run + `\annotate{…}{bracket=true}` naming the `$(m-1)^2$` region),
**`color="state:current"` + `leader=true`** (the corner callout matching its cell).

---

## 8. Ergonomics findings (3 author snippets; where it felt awkward, the spec moved)

**S1 — DP dependency chain (fits cleanly).**
```latex
\trace{dp}{cells=[0,2,3,5], color=path, arrowhead=end, label="argmax chain"}
```
Reads well: a 1D int list, one command replaces four staggered `\annotate{…}{arrow_from=…}` arcs and does
not clutter the cells with pills. **Finding:** keep `arrowhead=end` the default — a reconstruction chain is
directional. No spec change.

**S2 — BFS wavefront (exposed a real boundary; spec clarified, not stretched).**
First attempt: `\trace{g}{cells=[[0,1],[1,0],[1,2],[2,1]], …}` to show a frontier ring — **awkward**,
because a wavefront is an *unordered set of equidistant cells*, and `\trace` is a *path* (its polyline
implies an order and would zig-zag meaninglessly across the ring). The ergonomic tool is state, not trace:
```latex
\foreach{c}{${frontier}}          % frontier = list of [r,c]
  \recolor{g.cell[${c[0]}][${c[1]}]}{state=current}
\endforeach
```
and, when the frontier is a rectangular band, `\recolor{g.block[r0:r1][c0:c1]}{state=current}`.
**Finding (kept in the REFERENCE gotchas):** `\trace` is for *ordered paths*, not sets — document the
boundary rather than overload the command. This is why `cells` is ordered and `bracket` (a region, not a
path) is the set-shaped tool. No new syntax; the spec's *division of labor* (trace=path, block=region,
recolor=membership) is the ergonomic answer.

**S3 — Binary-search window (the features compose; existing machinery already covers 1D).**
```latex
% 1D array: the window is a range; mid gets the state-matched callout
\recolor{a.range[2:6]}{state=dim}
\recolor{a.cell[4]}{state=current}
\annotate{a.cell[4]}{label="mid", color="state:current", leader=true}
```
For a *2D* search space the window becomes `\annotate{g.block[lo_r:hi_r][lo_c:hi_c]}{bracket=true}`.
**Finding:** the 1D window needs **no new feature** — `range` + the existing span bracket already do it;
the only gap the features close is the *color match* on `mid` (S3 uses `state:current`, previously
impossible). Confirms A/B are the right-sized fix and validates the range↔block symmetry (§5). No spec change.

---

## 9. Probe log — `scratchpad/us_colon_probe.py` (executed this session)

`SceneParser().parse(body)` on `main` @ 9062239, `.venv/bin/python`. Verbatim results:

```
FAIL annotate color=state:current  (BARE colon)  [E1012] expected IDENT, got COLON
FAIL annotate color="state:current" (QUOTED)     [E1113] unknown annotation color 'state:current'; valid: …
OK   annotate color=good           (BARE plain)
OK   annotate leader=true          (new key — silently accepted)
FAIL recolor g.block[0:1][0:1]     (block sel)    [E1010] expected ']', got ':'
FAIL annotate g.block[…] bracket=true            [E1010] expected ']', got ':'
FAIL trace cells=[[0,0],[0,1]]     (new cmd)      [E1006] unknown command \trace; valid commands: …
```
Plus `parse_selector("g.block[0:1][0:1]")` → **E1010** "expected ']', got ':'".

What each line proves:
- **E1012 vs E1113** — the whole surface decision for feature C: bare `state:` dies at the lexer; quoted
  `state:` survives to the color validator (E1113 is exactly where the `state:` branch attaches). *Confirmed.*
- **`color=good` OK / `leader=true` OK** — plain colors unaffected; unknown keys ignored → additive, no churn. *Confirmed.*
- **`block` E1010 / `trace` E1006** — both are genuinely new grammar (block needs `_parse_block`; trace
  needs the command name) — nothing today accidentally accepts them. *Confirmed.*

---

## 10. Open questions (≤5, for a product/user decision)

1. **`state:` quoting — accept the quote requirement, or add lexer sugar?** The honest, low-risk spec is
   "write `color="state:current"` (quoted)". Making a bare `state:current` parse would need the value lexer
   to special-case a `IDENT:IDENT` run — a wider change with collision risk. *Recommend: require the quote,
   document E1012 as the "quote it" hint. (Confirmed this is the only viable no-lexer-change path, §9.)*

2. **`dot=start|none` vs the investigation's `startdot=true`.** This spec picks `dot=<none|start>` (extensible
   to `dot=both`, reads as an enum like `arrowhead`). *Recommend: `dot` enum. Confirm before locking the arg name.*

3. **`path=` corner shorthand — v1 or v2?** Pure parse-time sugar over `cells=`; the spiral needs only
   `cells=`. *Recommend: v2 fast-follow.*

4. **`done`/`dim`/`idle` `state:` label hue.** Their identifying tint is illegible on the white pill, so
   `color="state:done"` maps to a dark/muted neutral, not the faint tint. *Recommend: map to the state
   *text* token (dark neutral); accept that `state:done` ≈ `muted` visually — the value is the guaranteed
   binding, not a novel hue.*

5. **R-card numbering.** This spec assigns **R-35/R-36/R-37** (contiguous after R-34). The feat-trace
   investigation floated "R-40". *Recommend: R-35..R-37 (no gap); the sync gate (`check_ruleset_sync.py`)
   only needs the doc and ruleset to agree, not a specific number.*

---

## 11. Evidence ledger

| Claim | Grade | Anchor |
|---|---|---|
| Bare `color=state:current` → E1012 (colon splits value) | **Confirmed (executed)** | §9 `us_colon_probe.py`; `_grammar_tokens.py:289-310`, `lexer.py:36,328` |
| Quoted `color="state:current"` → parses, hits color validator (E1113 today) | **Confirmed (executed)** | §9; `_grammar_commands.py:233-242` |
| `leader=true`/`bracket=true` silently accepted (unknown keys ignored) | **Confirmed (executed)** | §9 |
| `block[…]` → E1010; `\trace` → E1006 (both genuinely new) | **Confirmed (executed)** | §9; `selectors.py:334`, `grammar.py:340-347` |
| Args are snake_case; enums/bools bare; strings/selectors quoted; nested lists legal | Confirmed | `SCRIBA-TEX-REFERENCE.md:406`; `ast.py:38`; `_grammar_values.py:29-42` |
| E1490–E1499 empty (between MetricPlot E1480-89 and Graph E1500+) | Confirmed | `errors.py:412-420`; grep |
| E1114 is taken (shape kwargs) → `state:` must reuse E1113 | Confirmed | `errors.py:182-187` |
| E1113 = "invalid or missing annotation color" (dual home) | Confirmed | `errors.py:181` |
| Block OOB is soft E1115 like every other selector | Confirmed | `_frame_renderer.py:447`; feat-block §7.2 |
| Grid/DPTable/Matrix = 2D (get block); Array/DPTable-1D/NumberLine = 1D (keep range) | Confirmed | `SCRIBA-TEX-REFERENCE.md:1124-1140`; feat-block §6 |
| Trace center anchors per primitive; NumberLine needs override | Confirmed | `grid.py:197-211`, `array.py:428-441`, `numberline.py:173-195` |
| Highest R-card today is R-34 → next free R-35 | Confirmed | grep `docs/spec/*.md` |
| `\trace`/`block`/`bracket`/`state:`/`leader` designs | Hypothesized | feat-* investigations + §4 |
| CSES-1071 acceptance `.tex` (forward target, not yet renderable) | Hypothesized | §7c |
```
