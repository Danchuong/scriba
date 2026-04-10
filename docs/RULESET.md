# Scriba v0.5.0 — Complete Ruleset Reference

> Single-source reference for all grammar rules, constraints, error codes, CSS contracts,
> HTML shape contracts, and validation limits that define Scriba's behavior.
> Generated from `04-environments-spec.md`, `06-primitives.md`, `00-ARCHITECTURE-DECISION`,
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

---

## 2. Inner Commands (11 total)

### 2.1 Base Commands (8)

| Command | Signature | Contexts | Persistence |
|---------|-----------|----------|-------------|
| `\shape` | `{name}{Type}{params}` | prelude only (animation), anywhere (diagram) | declaration |
| `\compute` | `{...Starlark...}` | prelude or step (animation), anywhere (diagram) | global or frame-local |
| `\step` | (no args) | animation only | starts new frame |
| `\narrate` | `{LaTeX text}` | animation step only | per-frame |
| `\apply` | `{target}{params}` | prelude or step | persistent |
| `\highlight` | `{target}` | step only (animation), anywhere (diagram) | ephemeral (animation), persistent (diagram) |
| `\recolor` | `{target}{state=...}` | both | persistent |
| `\annotate` | `{target}{params}` | both | persistent (default), ephemeral if `ephemeral=true` |

### 2.2 Extension Commands (3)

| Command | Signature | Contexts | Spec |
|---------|-----------|----------|------|
| `\fastforward` | `{N}{sample_every=K, seed=S}` | animation step only | E3 |
| `\substory` | `[title=..., id=...]` | animation step only | E4 |
| `\endsubstory` | (no args) | closes `\substory` | E4 |

---

## 3. Target Selector Syntax

```
selector  ::= IDENT ("." accessor)*
accessor  ::= "cell" "[" idx "]" ("[" idx "]")?
            | "node" "[" node_id "]"
            | "edge" "[" "(" id "," id ")" "]"
            | "range" "[" idx ":" idx "]"
            | "tick" "[" idx "]"
            | "all"
            | IDENT ("[" idx "]")?
idx       ::= NUMBER | "${" IDENT "}"
node_id   ::= NUMBER | STRING | "${" IDENT "}"
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
| Stack | `s` | `.item[i]`, `.all` |
| Plane2D | `p` | `.point[i]`, `.line[i]`, `.segment[i]`, `.polygon[i]`, `.region[i]`, `.all` |
| MetricPlot | `plot` | (whole shape only — series via `\apply` params) |

Interpolation: `${name}` resolved from Starlark bindings at build time.

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
| `highlight` | yellow (ephemeral) | `#F0E442` |

Unknown state → `E1109`

---

## 5. Primitives Catalog (11 types)

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
| `Stack` | `capacity` or `n` | push/pop delta semantics, horizontal/vertical |
| `Plane2D` | `xrange`, `yrange` | lines/points/segments/polygons/regions, geometry helpers |
| `MetricPlot` | (series via `\apply`) | up to 8 series, Wong palette, auto axes, log scale, two-axis mode |
| `Graph layout=stable` | (same as Graph) | SA joint-optimization, fixed positions across frames |

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
reversed, any, all, sum, divmod, print
```

### 6.4 Resource Limits

| Limit | Regular `\compute` | `\fastforward` |
|-------|--------------------|----|
| Wall clock | 5s | 5s |
| Operations | 10^8 | 10^9 |
| Memory | 64 MB | 64 MB |

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

### 7.2 `\fastforward{N}{params}` (E3)

| Parameter | Required | Constraint |
|-----------|----------|-----------|
| `total_iters` | yes | 1 to 10^6 |
| `sample_every` | yes | ≥1; `floor(N/sample_every)` ≤ 100 → `E1341` |
| `seed` | yes | explicit → `E1342` |
| `label` | no | default `"ff"` |

- Requires `iterate(scene, rng)` in preceding `\compute` → `E1343`
- RNG methods: `random()`, `randint(lo,hi)`, `uniform(lo,hi)`, `shuffle(lst)`, `choice(lst)`

### 7.3 `\substory` / `\endsubstory` (E4)

- Animation steps only → `E1362`
- Max nesting depth: 3 → `E1364`
- Substory mutations ephemeral (parent state saved/restored)
- Rendered as nested `<section class="scriba-substory">` with own Prev/Next controls

### 7.4 `@keyframes` Slots (E5)

Named CSS animation presets: `rotate`, `orbit`, `pulse`, `trail`, `fade-loop`.
Inlined into frame `<style>` at build time.

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
<div class="scriba-widget" data-scriba-scene="{id}">
  <div class="scriba-stage">...</div>
  <div class="scriba-narration">...</div>
  <div class="scriba-substory-container">...</div>
  <div class="scriba-controls">
    <button class="scriba-prev">Prev</button>
    <span class="scriba-step-label">Step 1 / N</span>
    <button class="scriba-next">Next</button>
  </div>
  <div class="scriba-progress"><!-- dots --></div>
  <script>/* ~2KB controller */</script>
</div>
```

### 9.4 Substory HTML (inside interactive widget)

```html
<section class="scriba-substory" data-substory-id="{id}" data-substory-depth="{d}"
         aria-label="Sub-computation: {title}">
  <div class="scriba-substory-widget" data-scriba-frames='[...]'>
    <div class="scriba-substory-stage">...</div>
    <div class="scriba-substory-narration">...</div>
    <div class="scriba-substory-controls">
      <button>Prev</button>
      <span>Sub-step 1 / M</span>
      <button>Next</button>
    </div>
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

### 10.2 Key CSS Custom Properties

```css
--scriba-cell-size: 46px;
--scriba-cell-rx: 5px;
--scriba-node-r: 22px;
--scriba-frame-gap: 1rem;
--scriba-narration-font-size: 0.92rem;
```

### 10.3 Responsive Breakpoints

| Media Query | Behavior |
|-------------|----------|
| `@media (max-width: 640px)` | Vertical stack layout |
| `@media print` | Vertical stack, expand all substories |
| `@media (prefers-reduced-motion: reduce)` | Disable transitions |

### 10.4 Dark Mode

Via `[data-theme="dark"]`. Wong palette works in both themes. Only `idle` and `dim` states remap.

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
| E1008 | Stray text at body top level |

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
| E1057 | Empty animation (no `\step`) |
| E1058 | Duplicate `\step` label |

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

### Compute Errors (E1150–E1179)

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

### `\fastforward` Errors (E1340–E1349)

| Code | Meaning |
|------|---------|
| E1340 | total_iters > 10^6 |
| E1341 | Sampled frames > 100 |
| E1342 | Missing seed |
| E1343 | Missing `iterate()` function |
| E1344 | Non-deterministic callback |
| E1345 | `\fastforward` in prelude/diagram |

### `\substory` Errors (E1360–E1369)

| Code | Meaning |
|------|---------|
| E1360 | Max nesting depth exceeded |
| E1362 | `\substory` outside `\step` |
| E1364 | Nesting depth > 3 |
| E1365 | `\endsubstory` without `\substory` |

### Matrix Errors (E1420–E1429)

| Code | Meaning |
|------|---------|
| E1422 | Invalid colorscale / vmin >= vmax |
| E1423 | Data shape mismatch |
| E1424 | NaN in data (warning) |

### Graph Layout Errors (E1500–E1509)

| Code | Meaning |
|------|---------|
| E1501 | `layout=stable` with N > 20 nodes |
| E1502 | `layout=stable` with T > 50 frames |

---

## 12. Determinism Contract

**Identical source + identical Scriba version = byte-identical HTML**

- No randomness in `\compute` (no `random` module)
- No I/O or time-dependent operations
- Dict iteration is insertion-order (Starlark spec)
- Seeded RNG for `\fastforward` (seed mandatory)
- `layout_seed` for Graph/Tree (deterministic layout)
- Optional CI check: `SCRIBA_CHECK_DETERMINISM=1`

---

## 13. Validation Limits Summary

| Constraint | Limit | Error Code |
|-----------|-------|------------|
| Frames (soft) | 30 | E1180 (warning) |
| Frames (hard) | 100 | E1181 (error) |
| Starlark ops (regular) | 10^8 | E1153 |
| Starlark ops (fastforward) | 10^9 | E1153 |
| Starlark wall clock | 5s | E1152 |
| Starlark memory | 64 MB | E1151 |
| Fastforward total_iters | 10^6 | E1340 |
| Fastforward sampled frames | 100 | E1341 |
| Substory nesting depth | 3 | E1364 |
| Graph stable nodes | 20 | E1501 (warning) |
| Graph stable frames | 50 | E1502 (warning) |
| Matrix cells | 10,000 | — |

---

## 14. Cross-References

| Document | Content |
|----------|---------|
| `04-environments-spec.md` | Locked base spec (grammar, commands, HTML shape, CSS) |
| `06-primitives.md` | 6 base primitive specs |
| `00-ARCHITECTURE-DECISION-2026-04-09.md` | Pivot #2 rationale (10 additions) |
| `extensions/hl-macro.md` | E2 spec |
| `extensions/fastforward.md` | E3 spec |
| `extensions/substory.md` | E4 spec |
| `extensions/keyframe-animation.md` | E5 spec |
| `extensions/figure-embed.md` | E1 spec |
| `primitives/matrix.md` | P1 spec |
| `primitives/stack.md` | P2 spec |
| `primitives/plane2d.md` | P3 spec |
| `primitives/metricplot.md` | P4 spec |
| `primitives/graph-stable-layout.md` | P5 spec |
| `09-animation-css.md` | CSS stylesheet spec |
