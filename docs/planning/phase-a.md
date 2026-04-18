# Phase A — v0.2.0 Implementation Plan

> **Target:** `\begin{animation}` end-to-end with 3 base primitives + 2 extensions.
> **Effort:** ~3 weeks solo, ~2 weeks with 2 engineers.
> **Prerequisite:** v0.1.1-alpha shipped (TeX plugin complete, 71 tests passing).
> **Binds to:** [`environments.md`](../spec/environments.md),
> [`scene-ir.md`](../spec/scene-ir.md), [`starlark-worker.md`](../spec/starlark-worker.md),
> [`svg-emitter.md`](../spec/svg-emitter.md), [`animation-css.md`](../spec/animation-css.md).

---

## 1. Phase A scope

| Category | Deliverable | Spec |
|----------|-------------|------|
| Environment | `\begin{animation}` / `\end{animation}` | `environments.md` §2, §8.1 |
| Primitives | `Array`, `DPTable`, `Graph` | `06-primitives.md` §3, §5, §6 |
| Extension E2 | `\hl{step-id}{tex}` macro | `extensions/hl-macro.md` |
| Extension E5 | CSS `@keyframes` named slots | `extensions/keyframe-animation.md` |
| Infrastructure | SceneParser, Starlark worker, SVG emitter, CSS | `05-scene-ir.md`, `07-starlark-worker.md`, `08-svg-emitter.md`, `09-animation-css.md` |

**Explicitly NOT in Phase A:** `\begin{diagram}`, Grid, Tree, NumberLine, figure-embed,
Matrix, Stack, Plane2D, MetricPlot, Graph stable layout, `\substory`, `\fastforward`.

---

## 2. Architecture overview

```
LaTeX source with \begin{animation}...\end{animation}
        │
        ▼
┌─────────────────────┐
│  AnimationRenderer   │  name="animation", version=1, priority=10
│  .detect(source)     │  → regex carve-out scanner → list[Block]
│  .render_block(block)│
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  SceneParser         │  recursive-descent over 8 inner commands
│  (lexer → AST)       │  → AnimationIR (prelude + frames)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Starlark Host       │  SubprocessWorker("starlark")
│  .eval(source)       │  → bindings for ${interpolation}
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  SceneState          │  delta materializer
│  (per-frame state)   │  inherits prev frame, clears highlights
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Primitive Catalog   │  Array, DPTable, Graph
│  .declare(params)    │  → SVG layout (positions, sizes)
│  .emit_svg(state)    │  → SVG <g> groups per frame
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  SVG Emitter         │  per-frame SVG snapshots
│  + HTML Stitcher     │  → <figure> + <ol> + <li> filmstrip
└────────┬────────────┘
         │
         ▼
    RenderArtifact(html, css_assets, js_assets)
```

---

## 3. Week-by-week breakdown

### Week A1 — Scaffolding, detector, parser, Starlark worker

#### 3.1 Package scaffold

- Create `scriba/animation/` package structure:
  ```
  scriba/animation/
  ├── __init__.py          # exports AnimationRenderer
  ├── renderer.py          # AnimationRenderer class
  ├── detector.py          # \begin{animation} carve-out scanner
  ├── scene.py             # SceneState delta materializer
  ├── emitter.py           # HTML/SVG emitter
  ├── errors.py            # E10xx/E11xx error code table
  ├── parser/
  │   ├── __init__.py
  │   ├── lexer.py         # tokenizer
  │   ├── ast.py           # frozen dataclass command IR types
  │   ├── grammar.py       # recursive-descent parser
  │   └── selectors.py     # target selector parser
  ├── primitives/
  │   ├── __init__.py
  │   ├── base.py          # Primitive protocol
  │   ├── array.py
  │   ├── dptable.py
  │   └── graph.py
  ├── extensions/
  │   ├── __init__.py
  │   ├── hl_macro.py      # \hl{step-id}{tex}
  │   └── keyframes.py     # @keyframes named slots
  ├── starlark_host.py     # Python wrapper for Starlark worker
  ├── starlark_worker.py   # subprocess entrypoint (or .go)
  └── static/
      ├── scriba-animation.css
      └── scriba-scene-primitives.css
  ```
- Update `pyproject.toml`: add `scriba.animation` package data, static file globs.
- Bump version to `0.2.0.dev0`. Keep `SCRIBA_VERSION = 2`.
- Delete pre-pivot `scriba/diagram/` stub module and its tests.

#### 3.2 Carve-out detector

- Scan source for `\begin{animation}[options]` ... `\end{animation}`.
- Return `Block(kind="animation", ...)` with `metadata["options_raw"]`.
- Error codes: `E1002` (trailing text on begin), `E1003` (nested begin), `E1004` (unknown option key).
- Test cases (~12): happy path, edge cases, error paths.

#### 3.3 AnimationRenderer skeleton

- `name = "animation"`, `version = 1`, `priority = 10`.
- `detect()` delegates to detector.
- `render_block()` initially `NotImplementedError` — wired in Week A2.
- `assets()` returns CSS file references.

#### 3.4 Inner-command parser

**Lexer** (`parser/lexer.py`):
- Tokenize: brace-matched args, identifiers, numbers, strings, `%` comments,
  `${interp}`, `[list]`.

**AST** (`parser/ast.py`):
- Frozen dataclasses per `05-scene-ir.md`:
  - `ShapeCommand(name, type_name, params, position)`
  - `ComputeCommand(source, position)`
  - `StepCommand(label, position)`
  - `NarrateCommand(body, position)`
  - `ApplyCommand(selector, params, position)`
  - `HighlightCommand(selector, position)`
  - `RecolorCommand(selector, state, position)`
  - `AnnotateCommand(selector, params, position)`
  - `Selector(shape_name, accessors)`
- Container types: `FrameIR`, `AnimationIR`.

**Grammar** (`parser/grammar.py`):
- Recursive-descent following BNF in `environments.md` §2.1.
- Validates position constraints (e.g., `\shape` before first `\step`).
- Emits `ValidationError` with position + E-code.

**Selectors** (`parser/selectors.py`):
- Parse: `name.cell[i]`, `name.cell[i][j]`, `name.node[id]`, `name.edge[(u,v)]`,
  `name.range[i:j]`, `name.all`.
- Support `${expr}` interpolation placeholders.
- Extend for tuple-range `range[(i1,j1):(i2,j2)]` per Phase A risk register.

**Tests** (~30 cases): all 8 commands, every reachable error code.

#### 3.5 Starlark worker

- **Prototype spike** (4h): evaluate Go binary (`starlark-go`) vs pure Python
  (`google.starlark`). Record decision in `07-open-questions.md` Q21.
- **Worker implementation**: subprocess entrypoint following `katex_worker.js` pattern:
  - JSON-line protocol over stdin/stdout.
  - Ready signal: `"starlark-worker ready\n"` on stderr.
  - Resource limits: 5s wall clock, 10^8 step cap, 64MB memory.
  - Forbidden features: `while`, `import`, `class`, `lambda`, `try`.
- **Python host** (`starlark_host.py`): register worker in `SubprocessWorkerPool`
  as `"starlark"` with `mode="persistent"`. Expose `.eval(env_id, globals, source)`.
- **Tests** (~10 cases): basic eval, recursion, timeout, step cap, memory cap,
  forbidden keywords, print capture.

---

### Week A2 — Scene, primitives, emitter, CSS, wiring

#### 3.6 Scene materializer

- `SceneState`: mutable dict tracking per-shape state across frames.
- Delta application rules per `environments.md` §6.1:
  - Each frame inherits full state from previous frame.
  - `\highlight` ephemeral — cleared at each `\step`.
  - `\annotate` with `ephemeral=true` — cleared at each `\step`.
  - `\apply`, `\recolor` — persistent until overwritten.
  - Frame-local `\compute` bindings scoped to that frame only.
- Tests (~15 cases): persistence, ephemerality, frame inheritance, compute scoping.

#### 3.7 Primitives — Array, DPTable, Graph

**Primitive protocol** (`primitives/base.py`):
```
Primitive (Protocol):
    name: str
    declare(params, ctx) -> PrimitiveState
    addressable_parts(state) -> list[str]
    emit_svg(state, frame_state) -> str
```

**Array** (`primitives/array.py`):
- Params: `size`/`n`, `data`, `labels`, `label`.
- Selectors: `cell[i]`, `range[i:j]`, `all`.
- SVG: horizontal row of `<rect>` + `<text>`, uniform cell width.
- Layout: compute positions once at declaration, reuse across frames.

**DPTable** (`primitives/dptable.py`):
- Params: `n` (1D) or `rows`/`cols` (2D), `data`, `label`, `labels`.
- Selectors: `cell[i]` (1D), `cell[i][j]` (2D), `range[i:j]`, `all`.
- SVG: same as Array/Grid + arrow overlay layer for `\annotate` with `arrow_from=`.
- Arrows: cubic Bezier `<path>` between cells.

**Graph** (`primitives/graph.py`):
- Params: `nodes`, `edges`, `directed`, `layout`, `layout_seed`, `label`.
- Selectors: `node[id]`, `edge[(u,v)]`, `all`.
- SVG: edges layer (`<line>` or `<path>`) + nodes layer (`<circle>` + `<text>`).
- Layout: deterministic seeded Fruchterman-Reingold in pure Python.
- Directed edges: `<marker>` arrowheads via `<defs>`.

**Snapshot tests** (~18): every addressable part of each primitive under every state class.

#### 3.8 SVG emitter + HTML stitcher

**SVG emitter** (`emitter.py`):
- Produce per-frame SVG from SceneState + primitive SVG outputs.
- ViewBox: computed from primitive bounding boxes, 16px padding, centered.
- Shared `<defs>`: deduplicate arrow markers across frames via `<use>`.
- State classes: stamp `scriba-state-{state}` on `<g data-target="...">`.
- Scene ID: `"scriba-" + sha256(env_body)[:10]`.

**HTML stitcher** (also in `emitter.py`):
- Frozen HTML shape from `environments.md` §8.1:
  ```html
  <figure class="scriba-animation" data-scriba-scene="{id}" data-frame-count="{N}">
    <ol class="scriba-frames">
      <li class="scriba-frame" id="{id}-frame-{i}" data-step="{i}">
        <header class="scriba-frame-header">
          <span class="scriba-step-label">Step {i} / {N}</span>
        </header>
        <div class="scriba-stage">
          <svg class="scriba-stage-svg" viewBox="..." role="img">...</svg>
        </div>
        <p class="scriba-narration">{narration with inline KaTeX}</p>
      </li>
    </ol>
  </figure>
  ```

#### 3.9 CSS

**`scriba-scene-primitives.css`**:
- Base cell, node, edge, tick styles using `--scriba-*` variables.
- Wong CVD-safe state classes per `09-animation-css.md`.

**`scriba-animation.css`**:
- `.scriba-animation` filmstrip grid layout.
- `.scriba-frame:target` outline for URL fragment navigation.
- `@media (max-width: 640px)` vertical stack fallback.
- `@media print` vertical stack + hide controls.
- Dark mode via `[data-theme="dark"]`.
- Verify contrast with axe-core CLI.

#### 3.10 Wiring

- `AnimationRenderer.render_block()`: parser → Starlark host → scene → primitives → emitter.
- `\narrate{...}` body routed through `ctx.render_inline_tex` (fallback to escaped text
  with `data-scriba-tex-fallback="true"` if callback is `None`).
- Frame-count limits: warning at 30 (`E1180`), error at 100 (`E1181`).
- Register `AnimationRenderer` in Pipeline alongside `TexRenderer`.

**End-to-end tests** (~8 fixtures):
- Binary search animation
- Knapsack DP
- Two-pointer
- BFS on tiny graph
- Prelude-only `\shape` (no steps)
- Frame-local `\compute`
- Narration with inline LaTeX
- Narration without `TexRenderer`

---

### Week A2.5 — Extensions: `\hl` macro + `@keyframes` slots

#### 3.11 `\hl{step-id}{tex}` macro (Extension E2)

- Parse `\hl{step-id}{tex}` calls from narration bodies.
- Resolve `step-id` to the enclosing `scriba-frame` element ID.
- Integrate with `TexRenderer` KaTeX trust config.
- Emit: `<span class="scriba-hl" data-hl-step="{step-id}">{KaTeX output}</span>`.
- CSS: `:target ~ .scriba-frames .scriba-hl[data-hl-step]` sibling-selector — activates
  highlight without JavaScript.
- XSS: extend the 4-case XSS test suite for the new macro.
- Tests (~10 cases): basic, multi-term, step-id not found, XSS in tex arg, nested `\hl`.
- Snapshot tests (~4): highlight activation states.

#### 3.12 CSS `@keyframes` named slots (Extension E5)

- Named-slot registry: `rotate`, `orbit`, `pulse`, `trail`, `fade-loop`.
- Slot resolution at emit time: collect declared slots from primitive SVG output,
  inline into each frame's `<style>` with `scriba-{scene-id}-{slot}` name prefix
  (avoids cross-frame leakage in email clients).
- Utility classes: `scriba-anim-rotate`, `scriba-anim-pulse`, etc.
- Tests (~8 cases): each preset emitted, name prefix applied, unknown slot error,
  duplicate deduplicated.
- Snapshot tests (~2): FFT twiddle-factor rotation, pulse overlay.

---

## 4. Dependencies and risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Starlark worker choice (Go vs Python) | Medium | Prototype spike in Week A1 (4h). Decision recorded in Q21. |
| Per-frame SVG size bloat on 30-frame animations | Medium | Share `<defs>` via `<use>` references; measure after primitives land. |
| `\hl` KaTeX trust config + XSS interaction | Low | Extend XSS test suite; security-reviewer agent pre-commit. |
| `@keyframes` leaking across frames in email clients | Low | Scope keyframe names with per-scene hash prefix; test Apple Mail + Gmail. |
| Parser budget underestimated | Medium | Week A1 extended to accommodate tuple-range selector grammar. |

---

## 5. External dependencies

| Dependency | Version | Required by | Notes |
|------------|---------|-------------|-------|
| Python | 3.10+ | All | Already required by v0.1.1 |
| Node.js | 18+ | KaTeX worker (existing) | No new Node dependency |
| Starlark runtime | TBD (spike) | `\compute{}` execution | Go binary or Python package |
| Pygments | 2.17–2.19 | Code highlighting (existing) | No change |

---

## 6. Exit criteria

- [ ] `\begin{animation}` renders end-to-end with Array, DPTable, Graph in staging.
- [ ] `\hl{step-id}{tex}` highlights correct KaTeX term via `:target` CSS — zero JS.
- [ ] `@keyframes rotate` preset emitted correctly for an FFT twiddle-factor example.
- [ ] `\narrate{...}` with inline LaTeX routes through `ctx.render_inline_tex`.
- [ ] Starlark worker survives 5,000 requests without leak.
- [ ] Frame-count limits enforced: `E1180` (>30 warning), `E1181` (>100 error).
- [ ] CSS passes axe-core contrast checks in light and dark themes.
- [ ] Filmstrip collapses to vertical on `@media print` and `@media (max-width: 640px)`.
- [ ] `AnimationRenderer.version = 1` recorded in `Document.versions`.
- [ ] Interactive output mode is the default; static mode available via `output_mode` metadata.
- [ ] No CRITICAL or HIGH issues from code-reviewer + security-reviewer agents.
- [ ] Ojcloud tenant backend pinned to `scriba==0.2.0a1`.
- [ ] Tag `0.2.0rc1` → `0.2.0` final after maintainer approval.

---

## 7. Test budget summary

| Category | Count | Location |
|----------|-------|----------|
| Detector | ~12 | `tests/unit/test_animation_detector.py` |
| Parser | ~30 | `tests/unit/test_animation_parser.py` |
| Starlark worker | ~10 | `tests/integration/test_starlark_worker.py` |
| Scene materializer | ~15 | `tests/unit/test_animation_scene.py` |
| Primitive snapshots | ~18 | `tests/integration/snapshots/animation/` |
| End-to-end | ~8 | `tests/integration/test_animation_end_to_end.py` |
| `\hl` macro | ~14 | `tests/unit/test_hl_macro.py` + snapshots |
| `@keyframes` | ~10 | `tests/unit/test_keyframes.py` + snapshots |
| **Total** | **~117** | |

---

## 8. Version changes at Phase A completion

| Field | Before (v0.1.1) | After (v0.2.0) |
|-------|-----------------|----------------|
| `__version__` | `"0.1.1-alpha"` | `"0.2.0"` |
| `SCRIBA_VERSION` | `2` | `2` (unchanged) |
| `TexRenderer.version` | `1` | `1` (unchanged) |
| `AnimationRenderer.version` | N/A | `1` (new) |
| `Document.versions` | `{"core": 2, "tex": 1}` | `{"core": 2, "tex": 1, "animation": 1}` |

---

## 9. Cross-references

| Document | Relationship |
|----------|--------------|
| [`roadmap.md`](roadmap.md) §4 | Phase A milestone definition |
| [`implementation-phases.md`](implementation-phases.md) | Week-by-week task breakdown (source of truth for task list) |
| [`environments.md`](../spec/environments.md) | Locked grammar, HTML shape, CSS contract, error codes |
| [`scene-ir.md`](../spec/scene-ir.md) | Scene IR datatype definitions |
| [`primitives.md`](../spec/primitives.md) | Primitive catalog (Array, DPTable, Graph for Phase A) |
| [`starlark-worker.md`](../spec/starlark-worker.md) | Starlark worker wire protocol |
| [`svg-emitter.md`](../spec/svg-emitter.md) | SVG emitter specification |
| [`animation-css.md`](../spec/animation-css.md) | CSS stylesheet specification |
| [`extensions/hl-macro.md`](../extensions/hl-macro.md) | E2 spec |
| [`extensions/keyframe-animation.md`](../extensions/keyframe-animation.md) | E5 spec |
| [`open-questions.md`](open-questions.md) Q21 | Starlark host choice (Go vs Python) |
