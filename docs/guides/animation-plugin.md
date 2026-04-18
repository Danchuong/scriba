# 09 — `scriba.animation.AnimationRenderer`

> Plugin spec. Binds verbatim to [`architecture.md`](../spec/architecture.md) (`Renderer`, `Block`, `RenderArtifact`, `RenderContext`, `RendererAssets`, `ValidationError`) and to [`environments.md`](../spec/environments.md), which is the single source of truth for the `\begin{animation}` grammar, inner command set, target selectors, Starlark host contract, frame semantics, HTML output shape, CSS class contract, and error catalog. Sibling shim: [`diagram-plugin.md`](diagram-plugin.md) (reserved for extension E5 in v0.5.x).

## 1. Purpose

`AnimationRenderer` is the Scriba plugin that turns a `\begin{animation} ... \end{animation}` LaTeX environment into either an **interactive widget** (default) or a **static filmstrip of N frames**. In interactive mode, the output includes an inline JS runtime with prev/next step controller buttons; the differ computes frame-to-frame transition manifests and the runtime applies CSS class changes and WAAPI animations between steps. In static mode, the output is an `<ol class="scriba-frames">` whose children are `<li class="scriba-frame">` elements with pure markup — no JavaScript, no buttons. The static filmstrip renders identically in browsers, email clients, RSS readers, PDF print, and screen readers; navigation uses the `:target` CSS selector driven by the URL fragment (`#{scene-id}-frame-7`).

Concrete goals:

1. Claim every top-level `\begin{animation}[opts]\n ... \n\end{animation}` region at priority `10`, before `TexRenderer.detect()` sees it.
2. Parse the body with the shared `SceneParser` over the 8 inner commands from `environments.md` §3.
3. Evaluate every `\compute{...}` block in the shared Starlark subprocess worker, tracking global vs frame-local scope.
4. Maintain a delta-based `SceneState` across frames: each frame inherits the previous frame's state, drops ephemeral overlays (`\highlight`, `\annotate{ephemeral=true}`), and applies its own commands on top.
5. Render each frame's final `SceneState` as one inline `<svg>` via the shared SVG emitter.
6. Delegate every `\narrate{...}` body to `ctx.render_inline_tex(body)` for KaTeX + inline TeX processing, inserting the resulting HTML inside a `<p class="scriba-narration">`.
7. Return a `RenderArtifact` whose `html` is the full `<figure class="scriba-animation">`, whose `css_assets` includes `scriba-animation.css` and `scriba-scene-primitives.css`. In interactive mode, the JS runtime is embedded inline in the HTML (not a separate asset file), so `js_assets` remains empty.

Non-goals:

- Auto-advance, hover-to-step, or scroll-sync behaviors. The interactive widget includes a step controller with prev/next buttons and an inline JS runtime that drives frame-to-frame transitions via WAAPI, but auto-play and scroll-sync remain out of scope per `environments.md` §13.
- Parsing or detecting code fences, Markdown, or any format other than the LaTeX environment.
- Author-configurable transition timing or easing curves. The built-in differ produces frame-to-frame transition manifests (serialized as `tr:` in the JS frames array) covering `recolor`, `value_change`, `element_add`, `element_remove`, `highlight_on`, and `highlight_off`; the JS runtime applies CSS class changes and WAAPI animations automatically. A `fs:` (full-sync) flag handles structural DOM changes, and `prefers-reduced-motion` disables animations. When a frame exceeds 150 transitions, the runtime sets `skip_animation` and applies changes instantly. Custom timing controls beyond these defaults require an ADR.
- Rasterization to PNG, OG image generation, GIF export. The output is SVG-in-HTML only.
- Per-frame interactivity or client-side state. Each `<li>` is inert markup.

`AnimationRenderer` and `DiagramRenderer` are siblings in the `scriba.animation` package and share the parser, primitive catalog, Starlark worker registration, and SVG emitter. See [`diagram-plugin.md`](diagram-plugin.md) §12 for the shared-core boundary.

## 2. Public API

```python
# scriba/animation/renderer.py
from __future__ import annotations

from typing import Any

from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.errors import RendererError, ValidationError


class AnimationRenderer:
    """Render `\\begin{animation}` environments to a static SVG filmstrip."""

    name: str = "animation"
    version: int = 1
    priority: int = 10  # must run before TexRenderer (priority 100)

    def __init__(
        self,
        *,
        starlark_host: Any | None = None,
    ) -> None:
        """
        starlark_host:
            Optional in-process Starlark host. When ``None``, the renderer
            uses the default host from ``scriba.animation.starlark_host``.
            Passing an explicit host lets callers share one Starlark
            environment with ``DiagramRenderer`` in the same Pipeline.
        """

    def detect(self, source: str) -> list[Block]: ...

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact: ...

    def assets(self) -> RendererAssets: ...
```

`AnimationRenderer` is stateless per render call. Instance state is limited to construction-time configuration and a handle to the shared worker pool. Two concurrent `render_block` calls on the same instance are safe: the `SceneParser` is reconstructed per call, the Starlark worker serializes through `SubprocessWorker._lock`, and the SVG emitter never touches instance state.

## 3. `detect()` contract

```python
ANIMATION_RE = re.compile(
    r"(?ms)^\\begin\{animation\}(\[[^\]\n]*\])?\s*\n(.*?)\n\\end\{animation\}\s*$",
)
```

`detect(source)` scans with `ANIMATION_RE.finditer(source)` and returns one `Block` per match:

- `block.start` — byte offset of `\b` in `\begin{animation}`.
- `block.end` — byte offset one past the closing `}` of `\end{animation}`.
- `block.kind = "animation"`.
- `block.raw` — the matched substring, verbatim.
- `block.metadata["options_raw"]` — the optional `[key=value,...]` capture group, or `None`.
- `block.metadata["body"]` — the inner body with whitespace preserved (so line numbers in error messages are accurate).

The regex is deliberately line-anchored. Per `environments.md` §2.2, `\begin{animation}` and `\end{animation}` must each live on their own line (enforced as `E1002`). The lazy body capture does not attempt to count braces inside `\compute{...}`; it relies on the closing-tag anchor. Authors who need to write literal `\end{animation}` inside narration or compute must escape the backslash (`\char92end{animation}`), a documented known limitation in `environments.md` §13.

The detector is separate from and does not interact with `DiagramRenderer.detect()`. The Pipeline's `(start, priority, list-index)` overlap resolver handles any pathological overlap between the two environment families; in practice, a `\begin{animation}` region and a `\begin{diagram}` region cannot overlap because neither nests inside the other.

## 4. Parse contract

After `detect()`, `render_block` hands `block.raw` to the shared `SceneParser` with animation mode enabled (allowing `\step` and `\narrate`). The parser walks the 8 commands from `environments.md` §3 and emits an ordered `AnimationIR` carrying:

- `options: AnimationOptions` — validated `[key=value,...]` header.
- `prelude: tuple[Command, ...]` — everything before the first `\step`: `\shape`, global `\compute`, and optionally `\apply` / `\recolor` / `\annotate` for initial state. `\highlight` in the prelude is `E1053`.
- `frames: tuple[FrameIR, ...]` — one `FrameIR` per `\step` block, each holding its commands and at most one `\narrate` body.

Parse pipeline:

1. **Option lexer.** Parse `[key=value,...]` into `AnimationOptions`. Valid keys per `environments.md` §2.4: `width`, `height`, `id`, `label`, `layout` (`filmstrip` | `stack`). Unknown keys raise `E1004`.
2. **Command lexer.** Walk line-by-line. Strip `% ...` comments. Ignore blank lines. `\step` must appear at the start of a line (`E1052` on trailing text).
3. **Brace reader.** Balanced-brace scanner over each argument (`E1001` on imbalance).
4. **Parameter list parser.** Final brace group parsed as `key=value` pairs, same grammar as `DiagramRenderer` (see `03-diagram-plugin.md` §4).
5. **Frame splitter.** The first `\step` closes the prelude; subsequent `\step` lines delimit frames. `\narrate` outside any `\step` is `E1056`. More than one `\narrate` per `\step` is `E1055`.
6. **Constraint checks.**
   - `\shape` after the first `\step` → `E1051`.
   - `\highlight` in prelude → `E1053`.
   - `\step` or `\narrate` missing → `E1057` on zero frames, `E1150` on zero narrations (warning).
   - Frame count > 30 → `E1180` (warning). Frame count > 100 → `E1181` (error, no HTML emitted).

The resulting `AnimationIR` is a frozen dataclass; subsequent stages consume it read-only. See [`scene-ir.md`](../spec/scene-ir.md) for the full field layout.

## 5. `render_block()` contract

```python
def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
    # 1. Parse body to AnimationIR.
    ir = self._parser.parse(block.raw, block.metadata, mode="animation")

    # 2. Evaluate the prelude's global \compute blocks in the Starlark worker.
    #    Bindings populate the global scope dict.
    global_scope = self._run_compute_blocks(ir.prelude_compute, ctx)

    # 3. Instantiate shapes; apply prelude state mutations to the initial
    #    SceneState.
    scene_state = self._build_initial_state(ir.shapes, ir.prelude_commands, global_scope)

    # 4. For each frame, derive a new SceneState by inheritance + commands.
    rendered_frames: list[RenderedFrame] = []
    for i, frame_ir in enumerate(ir.frames, start=1):
        frame_scope = self._run_compute_blocks(frame_ir.compute, ctx, parent=global_scope)
        merged_scope = {**global_scope, **frame_scope}

        next_state = self._inherit_state(scene_state)     # drop ephemeral overlays
        self._apply_commands(next_state, frame_ir.commands, merged_scope)

        svg = self._emitter.render(next_state, ir.options)
        narration_html = self._render_narration(frame_ir.narrate_body, ctx)
        rendered_frames.append(RenderedFrame(index=i, svg=svg, narration=narration_html))

        scene_state = next_state  # become the inherited base for frame i+1

    # 5. Wrap in the frozen animation HTML shell.
    html = self._wrap_figure(rendered_frames, ir.options)

    return RenderArtifact(
        html=html,
        css_assets=frozenset({"scriba-animation.css", "scriba-scene-primitives.css"}),
        js_assets=frozenset(),
    )
```

### 5.1 Delta-based state propagation

The core invariant of animation rendering is that **frame k inherits everything from frame k-1, then applies its own deltas**. Concretely, per `environments.md` §6.1, at the start of each frame:

1. Start from the end-of-previous-frame `SceneState` (or the prelude state for frame 1).
2. Clear any target whose state class includes `highlight` (highlights are ephemeral).
3. Drop any annotation whose `ephemeral=true`.
4. Apply the frame's commands in source order: `\apply` / `\highlight` / `\recolor` / `\annotate` (persistent) / `\annotate{ephemeral=true}`.
5. Render the resulting `SceneState` as SVG.

`SceneState` is a mutable dict keyed by target selector string, with values holding `{value, state, annotations, label, tooltip}`. `_inherit_state` performs a deep copy and then steps 2–3 above in one pass. `_apply_commands` mutates the local copy and never touches the parent.

### 5.2 Narration rendering

```python
def _render_narration(self, body: str | None, ctx: RenderContext) -> str:
    if body is None:
        # E1150 warning already raised at parse time if strict=False.
        return '<p class="scriba-narration" aria-hidden="true"></p>'

    if ctx.render_inline_tex is None:
        # Degraded mode: no TeX renderer registered.
        escaped = html.escape(body, quote=False)
        return (
            f'<p class="scriba-narration" data-scriba-tex-fallback="true">'
            f'{escaped}</p>'
        )

    try:
        inner = ctx.render_inline_tex(body)
    except Exception as exc:
        raise RendererError(
            f"inline TeX renderer failed: {exc}",
            renderer="animation",
            code="E1201",
        ) from exc

    return f'<p class="scriba-narration">{inner}</p>'
```

`ctx.render_inline_tex` is populated automatically by the Pipeline's default tex-inline provider (see `scriba/core/pipeline.py` `_default_tex_inline_provider`) whenever a `TexRenderer` is registered. This is the **only** place `AnimationRenderer` calls back into another plugin. No other Scriba renderer is consulted.

### 5.3 Frame count limits

- **Soft limit (30 frames).** `E1180` warning. Rationale: the `filmstrip` layout only reads pleasantly up to ~30 frames on a laptop screen. Warnings are logged but do not abort emission unless `strict=True`.
- **Hard limit (100 frames).** `E1181` error. Rationale: 100 inline SVG stages per problem statement doubles the rendered HTML size and blows out the content-hash cache. No HTML is emitted on this error.

Both limits are enforced during the frame-splitter pass (§4 step 5), before any SVG rendering happens.

## 6. Shape-to-SVG dispatch

`AnimationRenderer` uses the exact same primitive catalog as `DiagramRenderer` (see [`diagram-plugin.md`](diagram-plugin.md) §6 for the dispatch table). All 16 primitives — the six base primitives (`Array`, `Grid`, `DPTable`, `Graph`, `Tree`, `NumberLine`), the five extended primitives (`Matrix`/`Heatmap`, `Stack`, `Plane2D`, `MetricPlot`, `Graph` with `layout=stable`), and the five data-structure primitives (`CodePanel`, `HashMap`, `LinkedList`, `Queue`, `VariableWatch`) — emit the same `<g data-target="...">` groups with the same selector strings in both plugins. The only difference is that `AnimationRenderer` calls the emitter once per frame, producing N independent `<svg>` stages; `DiagramRenderer` calls it once.

The primitive layout (positions, sizes, graph/tree topology) is computed **once from the prelude state** and cached across frames. Per-frame rendering only re-applies state classes and annotation overlays on top of the frozen geometry; nothing about the SVG viewBox or element positions changes between frames. This guarantees that a 30-frame filmstrip does not re-layout the same `Tree` 30 times.

If an author wants geometry to change across frames (e.g., a growing array), they declare the final-size shape in the prelude and use `\apply{a.cell[i]}{value=...}` to reveal values one cell at a time. This is a documented pattern in the cookbook examples.

## 7. Starlark subprocess

`\compute{...}` blocks run in the shared Starlark worker (`worker_pool.get("starlark")`). The worker, protocol, language contract, determinism rules, and caps are identical to `DiagramRenderer` — see `03-diagram-plugin.md` §7 and `environments.md` §5. Animation adds one scope wrinkle: **frame-local vs global bindings**.

Per `environments.md` §5.3:

- A `\compute` block in the prelude populates the **global scope**. Global bindings persist across all frames and are visible to every later command.
- A `\compute` block inside a `\step` creates a **frame-local scope**. Frame-local bindings are dropped at the next `\step`. Interpolation `${name}` in a frame-local context resolves against `global ∪ frame_local`, with frame-local shadowing global.

`AnimationRenderer` implements this by sending two distinct Starlark eval requests per frame when needed: one for the frame's own `\compute` block (parent = global scope) and one merged scope dict passed into `_apply_commands` for interpolation. Global scope is computed once before the frame loop; frame-local scope is recomputed per frame.

Worker failures surface as `RendererError(code="E1150" | "E1151" | "E1152" | "E1153" | "E1154" | "E1155" | "E1156" | "E1157")` per `environments.md` §11.4.

## 8. HTML output shape

The emitted `RenderArtifact.html` matches `environments.md` §8.1 byte-for-byte:

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
          <!-- per-frame rendered primitives with state classes applied -->
        </svg>
      </div>
      <p class="scriba-narration" id="{scene-id}-frame-1-narration">
        <!-- output of ctx.render_inline_tex(...) -->
      </p>
    </li>
    <li class="scriba-frame" id="{scene-id}-frame-2" data-step="2"> ... </li>
    <!-- ... remaining frames ... -->
  </ol>
</figure>
```

Frozen contracts:

- `scene-id` from the `id=` option, or `"scriba-" + sha256(block.raw)[:10]` when absent. Must match `[a-z][a-z0-9-]*`.
- `data-frame-count` matches the number of `<li>` children.
- `data-step` is 1-indexed.
- `data-layout` is `"filmstrip"` by default; `"stack"` is the only other permitted value. Print media always falls back to `stack` via CSS (see `environments.md` §9.1).
- Each frame's `<svg>` has `role="img"` and `aria-labelledby` pointing at that frame's narration `<p>`, so screen readers speak the narration when they land on the figure.
- No `<button>`, no `data-step-current`, no controller element. The filmstrip is pure markup.
- The outer `<figure>` has `aria-label` set from the `label=` option when present; otherwise it is omitted (the child frames' `aria-labelledby` provides accessible names).

## 9. Assets

```python
def assets(self) -> RendererAssets:
    static = files("scriba.animation").joinpath("static")
    return RendererAssets(
        css_files=frozenset({
            Path(str(static / "scriba-animation.css")),
            Path(str(static / "scriba-scene-primitives.css")),
        }),
        js_files=frozenset(),
    )
```

Both CSS files are always-on for any Pipeline that registers `AnimationRenderer`. `scriba-scene-primitives.css` is shared with `DiagramRenderer` — the Pipeline's asset aggregator (see `scriba/core/pipeline.py` step 6) namespaces basenames by owning renderer name, so both plugins can contribute the same file without collision. No separate JavaScript asset file is emitted; in interactive mode, the JS runtime (step controller and WAAPI transition driver) is embedded inline in the HTML output.

Custom-property variables (state colors, frame gap, stage padding) live in the `--scriba-*` namespace from `01-architecture.md` §"CSS variable naming convention", extended in `environments.md` §9. Dark mode is a single ancestor selector `[data-theme="dark"]`, consistent with `TexRenderer`.

## 10. Error codes

`AnimationRenderer` raises `RendererError(message, renderer="animation", code=...)` for every failure. Codes are drawn from [`error-codes.md`](../spec/error-codes.md):

| Range | Category | Notes |
|---|---|---|
| `E1001..E1013` | Parse / detection errors | Brace imbalance, misplaced `\begin`/`\end`, unknown option, selector/tokeniser errors, 1 MB source cap. |
| `E1050..E1056` | Diagram-specific / environment | `\step` in diagram, `\narrate` outside `\step`, `\highlight` in prelude, duplicate narration, etc. |
| `E1100..E1113` | Shape / target / annotation errors | Unknown primitive, unknown selector, unknown state or color token. |
| `E1150..E1155` | Starlark compute errors | Parse, runtime, timeout, step cap, forbidden construct, memory cap (see `error-codes.md`). |
| `E1170..E1173` | `\foreach` errors | Nesting, empty body, unclosed, iterable validation. |
| `E1180..E1182` | Frame / cursor | `E1180` soft warning (>30), `E1181` hard error (>100), `E1182` `\cursor` state validation. |
| `E1360..E1368` | Substory | Substory nesting, unclosed, misplaced. |
| `E1400..E1459` | Primitive parameter validation | Split from the legacy `E1103` bucket in v0.5.1 — one code per `(primitive, check)` pair. |
| `E1460..E1466` | Plane2D | Viewport, geometry, aspect, element cap. |
| `E1480..E1487` | MetricPlot | Series validation, point cap, log-scale clamp, axis consistency. |
| `E1500..E1505` | Graph layout | Stable layout convergence, node/frame caps, fallback, clamp, seed. |

`E1181` is always fatal. `E1180` is a logged warning that does not
abort rendering. The full catalog lives in [`error-codes.md`](../spec/error-codes.md).

## 11. Example

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
\narrate{Từ tảng $0$ nhảy sang tảng $1$: $dp[1] = dp[0] + |h_1 - h_0|$.}

% ... more frames ...
\end{animation}
```

Produces a `<figure class="scriba-animation">` wrapping an `<ol class="scriba-frames">` with one `<li class="scriba-frame">` per `\step`, each holding a `NumberLine` + `Array` SVG stage and a narration paragraph with KaTeX-rendered inline math. Full worked example in `environments.md` §12.2.

## 12. Relationship to `DiagramRenderer`

`AnimationRenderer` and `DiagramRenderer` live in a single `scriba.animation` package and share:

- The `SceneParser` (command lexer, brace reader, parameter parser, selector parser).
- The primitive catalog and layout routines.
- The SVG emitter.
- The Starlark worker registration logic.
- The `scriba-scene-primitives.css` stylesheet.

They diverge at:

- `detect()` regex (`\begin{animation}` vs `\begin{diagram}`).
- Permitted inner commands: animation allows `\step` and `\narrate`; diagram forbids both.
- Frame semantics: animation runs the inherit-and-apply loop per frame; diagram renders a single state.
- Scope model: animation distinguishes global vs frame-local Starlark scope; diagram has only global.
- HTML shell: `<figure class="scriba-animation"><ol class="scriba-frames">` vs `<figure class="scriba-diagram">`.
- Asset file: `scriba-animation.css` vs `scriba-diagram.css`.
- Plugin `name` / `version` / warning policy.

Any change that touches shared code is landed in one PR against `scriba/animation/*` and bumps **both** `AnimationRenderer.version` and `DiagramRenderer.version`.

---

**End of plugin spec.** Bind to this file + `environments.md` verbatim. Bump `AnimationRenderer.version` whenever the HTML shape in §8 or the class-name contract in `environments.md` §9 changes.
