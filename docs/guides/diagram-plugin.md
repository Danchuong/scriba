# 03 — `scriba.animation.DiagramRenderer`

> **Status (v0.5.x):** `\begin{diagram}` is **reserved for extension E5**
> and is **not a first-class IR** in v0.5.x. The parser always produces
> `AnimationIR`; there is no `DiagramIR` type. A `\begin{diagram}` block
> is rendered as a single-frame animation in diagram mode (no `\step`
> allowed inside → `E1050`) and is treated as experimental surface area.
> New authoring should prefer `\begin{animation}` with a single implicit
> frame until E5 lands. See [`ruleset.md`](../spec/ruleset.md) §1.1 for
> the authoritative status notice.
>
> This document is retained because the `DiagramRenderer` shim still
> ships in `scriba/animation/renderer.py` for backward compatibility with
> legacy pipelines. Anywhere this file and
> [`ruleset.md`](../spec/ruleset.md) / [`environments.md`](../spec/environments.md)
> disagree, the ruleset wins and this file is the bug.

## 1. Purpose

`DiagramRenderer` is the Scriba plugin that turns a `\begin{diagram} ... \end{diagram}` LaTeX environment into a single static `<figure class="scriba-diagram">` containing one inline `<svg>` stage. It shares its parser, selector machinery, primitive catalog, Starlark host, and SVG emitter with `AnimationRenderer` (see [`animation-plugin.md`](animation-plugin.md)); the two plugins are sibling entry points over the same rendering core. The only difference visible to authors is that `diagram` is **single-frame** — `\step` and `\narrate` are forbidden — and the only difference visible to consumers is the emitted HTML shape (§8 below).

Concrete goals:

1. Claim every top-level `\begin{diagram}[opts]\n ... \n\end{diagram}` region at priority `10`, before `TexRenderer` sees it.
2. Parse the body with the recursive-descent `SceneParser` over the 12 inner commands from `environments.md` §3.
3. Evaluate every `\compute{...}` block in the shared Starlark subprocess worker.
4. Instantiate each `\shape{name}{Type}{params}` against the primitive catalog, and apply `\apply` / `\highlight` / `\recolor` / `\annotate` commands against the resulting `SceneState`.
5. Emit exactly one SVG stage via the shared SVG emitter, wrapped in the frozen `<figure class="scriba-diagram">` shell from `environments.md` §8.2.
6. Return a `RenderArtifact` whose `html` is the full `<figure>`, whose `css_assets` includes `scriba-diagram.css` and `scriba-scene-primitives.css`, and whose `js_assets` is **empty** — diagrams ship zero runtime JavaScript.

Non-goals:

- Frame semantics, delta propagation, narration, `\step` handling — all live in `AnimationRenderer`.
- Detecting or parsing raw ` ```d2 ` fenced blocks. The previous D2-first edition of this document is withdrawn; Scriba no longer ships a D2 code path. Diagrams are authored in LaTeX environments, not fences.
- Rendering anything inside a `\begin{tabular}`, `lstlisting`, or `$...$`. Per `environments.md` §2.3, those are top-level-only.

## 2. Public API

```python
# scriba/animation/renderer.py (actual location, alongside AnimationRenderer)
from __future__ import annotations

from typing import Any

from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.errors import RendererError, ValidationError


class DiagramRenderer:
    """Render `\\begin{diagram}` environments to a self-contained SVG figure.

    Status: reserved for extension E5. Retained as a backward-compat shim
    that routes diagram blocks through the shared AnimationRenderer core.
    """

    name: str = "diagram"
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
            Passing an explicit host lets callers share a single Starlark
            environment across ``DiagramRenderer`` and ``AnimationRenderer``
            in the same Pipeline.
        """

    def detect(self, source: str) -> list[Block]: ...

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact: ...

    def assets(self) -> RendererAssets: ...
```

`DiagramRenderer` is stateless per render call. Two concurrent `render_block` calls on the same instance are safe: the `SceneParser` is reconstructed each call, the Starlark worker serializes through `SubprocessWorker._lock`, and the SVG emitter never touches instance state.

## 3. `detect()` contract

```python
DIAGRAM_RE = re.compile(
    r"(?ms)^\\begin\{diagram\}(\[[^\]\n]*\])?\s*\n(.*?)\n\\end\{diagram\}\s*$",
)
```

`detect(source)` scans with `DIAGRAM_RE.finditer(source)` and returns one `Block` per match:

- `block.start` — byte offset of the `\b` in `\begin{diagram}`.
- `block.end` — byte offset one past the closing `}` of `\end{diagram}`.
- `block.kind = "diagram"`.
- `block.raw` — the matched substring, verbatim (including the `\begin` and `\end` lines).
- `block.metadata["options_raw"]` — the optional `[key=value,...]` capture group, or `None`.
- `block.metadata["body"]` — the inner body, with leading/trailing whitespace preserved so that later error messages can report accurate line numbers.

The regex is deliberately line-anchored (`^...$` with `(?ms)`) so that `\begin{diagram}` and `\end{diagram}` each occupy their own line (enforced as `E1002` in the catalog). The lazy `.*?` body capture avoids brace counting; nested `\compute{ ... }` braces survive because the detector trusts the line-anchored closing tag. Authors who need to write a literal `\end{diagram}` inside narration (not applicable here — narration is forbidden in diagrams per `E1054`) or inside a `\compute` block must escape the backslash.

Returned blocks are guaranteed non-overlapping by construction (`DIAGRAM_RE` is non-overlapping with itself). The Pipeline resolves overlap between diagram blocks and `\begin{animation}` blocks via `(start, priority, list-index)`; both plugins run at priority `10` so the tie-breaker is the order passed to `Pipeline(renderers=[...])`.

## 4. Parse contract

After `detect()`, `render_block` hands `block.raw` (minus the already-matched `\begin`/`\end` lines) to an internal `SceneParser`. The parser is a small recursive-descent walker over exactly the 12 inner commands from `environments.md` §3: `\shape`, `\compute`, `\apply`, `\highlight`, `\recolor`, `\annotate`, `\step`, `\narrate`, `\reannotate`, `\cursor`, `\foreach`, `\substory`. In the diagram context, `\step` (`E1050`) and `\narrate` (`E1054`) are parse-time errors.

The parse pipeline:

1. **Option lexer.** Parse the optional `[key=value,...]` header into a `DiagramOptions` frozen dataclass. Unknown keys raise `RendererError` with code `E1004`.
2. **Command lexer.** Walk the body line by line. A command starts with `\` followed by one of the 8 command names; everything else on that line (up to its closing brace) is the command. Comments (`% ...` to end of line) are stripped. Blank lines are ignored.
3. **Brace reader.** Each brace argument is read via a balanced-brace scanner (standard LaTeX rules). Unbalanced braces raise `E1001`. The scanner is TikZ-flavored: it understands nested `{...}` but never interprets `$`, `&`, or `\` specially inside the brace body.
4. **Parameter list parser.** The final brace of `\shape` / `\apply` / `\recolor` / `\annotate` is parsed as a `param_list`: `key=value` pairs separated by commas, values being idents, numbers, double-quoted strings, `${interp}` references, or `[list, ...]`. Grammar in `environments.md` §2.1.
5. **Command AST.** The result is an ordered `tuple[Command, ...]` of frozen dataclasses, one per recognized command, each carrying its source line/column for error reporting.
6. **Scene IR build.** The command list is lowered to the shared `AnimationIR` (see [`scene-ir.md`](../spec/scene-ir.md)) with exactly one implicit frame — `DiagramRenderer` does not have its own IR type in v0.5.x.

The SceneParser is **not** reused from `scriba.tex.parser`. The inner grammar is simpler and more rigid than LaTeX, and sharing would leak TeX quirks (optional args, catcodes, math mode) into a context that does not need them. Only `\narrate` bodies in the animation plugin cross the boundary, and `DiagramRenderer` never sees `\narrate` at all.

## 5. `render_block()` contract

```python
def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
    # 1. Parse body to AnimationIR (single implicit frame). Raises RendererError(code="E1xxx") on parse failure.
    ir = self._parser.parse(block.raw, block.metadata)

    # 2. Run every \compute block through the shared Starlark worker.
    #    Bindings accumulate into a single scope dict.
    scope = self._run_compute_blocks(ir.compute_blocks, ctx)

    # 3. Instantiate shapes against the primitive catalog.
    #    Each shape resolves its parameters against `scope` (for ${interp}).
    scene = self._build_scene(ir.shapes, scope)

    # 4. Apply state mutations in source order. \highlight is persistent here
    #    (diagram has no frame boundary to clear it on).
    self._apply_commands(scene, ir.commands, scope)

    # 5. Render the scene to a single <svg> via the shared SVG emitter.
    svg = self._emitter.render(scene, ir.options)

    # 6. Wrap in the frozen diagram HTML shell.
    html = self._wrap_figure(svg, ir.options)

    return RenderArtifact(
        html=html,
        css_assets=frozenset({"scriba-diagram.css", "scriba-scene-primitives.css"}),
        js_assets=frozenset(),
    )
```

Each step raises `RendererError(message, code=...)` with codes drawn from [`error-codes.md`](../spec/error-codes.md):

- Parse / detection errors: `E1001..E1013`.
- Diagram-specific semantic errors: `E1050` (`\step` forbidden), `E1054` (`\narrate` forbidden), `E1053` (`\highlight` in prelude — not applicable here since diagram has no prelude/step split).
- Shape / target / annotation errors: `E1100..E1113`.
- Primitive parameter validation (post-v0.5.1 split): `E1400..E1459`.
- Primitive-specific errors: `E1460..E1505` (Plane2D, MetricPlot, Graph layout).
- Compute errors surfaced from the Starlark worker: `E1150..E1155`.

Starlark worker failures are surfaced through the shared Starlark host and re-raised as `RendererError(code="E1150" | "E1151" | "E1152" | ...)` — see [`error-codes.md`](../spec/error-codes.md) for the full mapping.

`render_block` MUST NOT mutate `block`, `ctx`, or any shared instance state other than the worker pool (which is itself thread-safe).

## 6. Shape-to-SVG dispatch

Each primitive type from `environments.md` §3.1 compiles to a fixed SVG template maintained in `scriba.animation.primitives`. The dispatch table below is the authoritative mapping for v0.3. Templates live in a single module so animation and diagram share them.

| Scriba type | SVG root | Addressable parts emitted as `<g data-target="...">` | Layout strategy |
|---|---|---|---|
| `Array` | `<g data-primitive="array">` | `a.cell[i]`, `a.range[lo:hi]`, `a.all` | Horizontal row of `<rect>`+`<text>` pairs, uniform width from `size=`. |
| `Grid` | `<g data-primitive="grid">` | `g.cell[r][c]`, `g.all` | `rows × cols` matrix of rect+text, uniform cell size. |
| `DPTable` | `<g data-primitive="dptable">` | `dp.cell[i]` (1D) or `dp.cell[i][j]` (2D), `dp.range[...]`, `dp.all` | Same as `Array` / `Grid` plus optional transition arrows. |
| `Graph` | `<g data-primitive="graph">` | `G.node[u]`, `G.edge[(u,v)]`, `G.all` | Force-directed layout computed in Python at build time (no runtime layout); supports `directed=true`. |
| `Tree` | `<g data-primitive="tree">` | `T.node[i]`, `T.edge[(p,c)]`, `T.all` | Reingold-Tilford layered layout, computed at build time. |
| `NumberLine` | `<g data-primitive="numberline">` | `nl.tick[i]`, `nl.range[lo:hi]`, `nl.axis`, `nl.all` | Single horizontal axis with tick marks at integer positions over `domain=`. |

The `Graph` and `Tree` primitives are the only ones that perform non-trivial layout. Both run **in-process** in Python, not via the D2 subprocess. The previous D2-first edition of this plugin spec routed graph and tree layout through `d2 --layout=dagre`; that path is **removed** in v0.3. Reasons: (1) adding a D2 binary dependency for two primitives doubles the runtime footprint for tenants that do not use them; (2) build-time cold-start of D2 is ~50ms per invocation and diagrams may appear dozens of times per problem statement; (3) the editorial-problem domain rarely needs graphs beyond ~20 nodes, which in-process Reingold-Tilford and a simple spring layout handle comfortably.

If a future v0.4 re-introduces D2 for very large graphs, it will be an optional engine parameter (`layout_engine="d2"`), registered through `SubprocessWorkerPool.register("d2", ...)`, and will stay behind a feature flag. It is **not** in scope for v0.3.

## 7. Starlark subprocess

Every `\compute{...}` block evaluates in a persistent Starlark worker registered on the shared `SubprocessWorkerPool` under the name `"starlark"`. The worker follows the exact same subprocess protocol as `scriba/tex/katex_worker.js`: newline-delimited JSON on stdin/stdout, a `ready_signal` line on stderr before the first request, transparent respawn on crash, and a `max_requests` ceiling. See `environments.md` §5 for the locked language contract (allowed features, injected API, determinism rules, 5-second timeout, 10^8 step cap, 64 MB memory cap) and `07-starlark-worker.md` for the wire schema.

`DiagramRenderer` calls `worker_pool.get("starlark")` lazily on first `\compute` invocation. Each call sends one JSON request:

```json
{"op": "eval", "env_id": "<sha256 of block.raw[:10]>", "globals": {...}, "source": "<starlark>"}
```

and receives one response:

```json
{"ok": true,  "bindings": {...}, "debug": [...]}
```

or on failure:

```json
{"ok": false, "code": "E11xx", "message": "...", "line": N, "col": M}
```

Diagram compute scope is a single flat dict (no frame-local vs global distinction — diagrams have no frames). Later `\compute` blocks see earlier bindings via the `globals` field on the request.

## 8. HTML output shape

The emitted `RenderArtifact.html` matches `environments.md` §8.2 byte-for-byte:

```html
<figure class="scriba-diagram"
        data-scriba-scene="{scene-id}"
        aria-label="{optional label}">
  <div class="scriba-stage">
    <svg class="scriba-stage-svg"
         viewBox="0 0 {W} {H}"
         xmlns="http://www.w3.org/2000/svg"
         role="img">
      <!-- one <g data-target="..."> per addressable part, state classes applied -->
    </svg>
  </div>
</figure>
```

Frozen contracts:

- `scene-id` comes from the `id=` option, or `"scriba-" + sha256(block.raw)[:10]` when absent. Must match `[a-z][a-z0-9-]*`.
- Every addressable part of every shape is emitted as a `<g data-target="{selector}">` group. The selector string matches exactly the grammar in `environments.md` §4, and is the same string an author would write in `\recolor{...}`.
- State classes (`scriba-state-idle` / `-current` / `-done` / `-dim` / `-error` / `-good` / `-highlight`) are applied to the `<g>` element, not to inner shapes, so the CSS contract in `environments.md` §9 matches with a single selector per state.
- Annotations emit a nested `<g class="scriba-annotation scriba-annotation-{color}">` inside the target group.
- `role="img"` is set unconditionally. Diagrams have no `aria-labelledby` (no narration exists); an `aria-label` on the outer `<figure>` is the only accessible name.

## 9. Assets

```python
def assets(self) -> RendererAssets:
    static = files("scriba.animation").joinpath("static")
    return RendererAssets(
        css_files=frozenset({
            Path(str(static / "scriba-diagram.css")),
            Path(str(static / "scriba-scene-primitives.css")),
        }),
        js_files=frozenset(),
    )
```

`scriba-diagram.css` and `scriba-scene-primitives.css` are always-on for any Pipeline that registers `DiagramRenderer`, regardless of whether a diagram was actually detected. This matches `TexRenderer`'s unconditional `scriba-tex-content.css` behavior and keeps consumer asset manifests stable across cache hits and misses. There is no JavaScript asset — diagrams are entirely static.

The two CSS files share the `--scriba-*` custom-property namespace defined in `01-architecture.md` §"CSS variable naming convention" and extended in `environments.md` §9. Consumers override colors by redefining those variables on `[data-theme="dark"]` (or any other theme selector); no per-plugin theme plumbing exists.

## 10. Error codes

`DiagramRenderer` raises `RendererError(message, renderer="diagram", code=...)` for every failure. Codes are drawn from the ranges locked in `environments.md` §11:

| Range | Category | Notes |
|---|---|---|
| `E1001..E1013` | Parse / detection errors | Unbalanced braces, misplaced `\begin`/`\end`, unknown options, stray top-level text, source size cap. |
| `E1050..E1056` | Diagram-specific | `\step` (`E1050`), `\narrate` (`E1054`), `\highlight` in prelude (`E1053`), etc. |
| `E1100..E1113` | Shape / target / annotation errors | Unknown primitive, invalid selector, unknown state or color token. |
| `E1150..E1155` | Starlark compute errors | Parse, runtime, timeout, step cap, forbidden construct, memory cap. |
| `E1400..E1459` | Primitive parameter validation | Split from the legacy `E1103` bucket (see [`error-codes.md`](../spec/error-codes.md)). |
| `E1460..E1505` | Primitive-specific | Plane2D, MetricPlot, Graph layout errors. |

Warnings (e.g. `E1180` frame count — not applicable here) are suppressed
unless `strict=True` is set on the surrounding AnimationRenderer. See
[`error-codes.md`](../spec/error-codes.md) for the authoritative catalog.

## 11. Example

```latex
\begin{diagram}[id=bst-demo, label="A small binary search tree"]
\shape{T}{Tree}{root=8, nodes=[8,3,10,1,6,14,4,7,13]}
\recolor{T.node[8]}{state=current}
\annotate{T.node[8]}{label="root", position=above, color=info}
\recolor{T.range[1:4]}{state=dim}
\annotate{T.edge[(3,6)]}{label="left-heavy", color=warn, arrow=true}
\end{diagram}
```

Produces the HTML fragment in `environments.md` §12.3 — a single `<figure class="scriba-diagram">` wrapping one inline `<svg>` with `<g data-target="T.node[8]">`, `<g data-target="T.edge[(3,6)]">`, and so on.

## 12. Relationship to `AnimationRenderer`

`DiagramRenderer` and `AnimationRenderer` share, in a single `scriba.animation` package:

- The `SceneParser` (inner command lexer, brace reader, param parser).
- The primitive catalog and layout routines.
- The SVG emitter.
- The Starlark worker registration logic.
- The `scriba-scene-primitives.css` stylesheet.

They diverge only at:

- `detect()` regex (`\begin{diagram}` vs `\begin{animation}`).
- Permitted inner commands (`\step` / `\narrate` forbidden in diagram).
- The frozen HTML shell (`<figure class="scriba-diagram">` vs `<figure class="scriba-animation"><ol class="scriba-frames">`).
- Their `name` / `version` / error warning policies.

Any change that affects both plugins is landed in one PR against `scriba/animation/*` and bumps **both** `DiagramRenderer.version` and `AnimationRenderer.version`. See `09-animation-plugin.md` for the animation-side contract.

---

**End of plugin spec.** Bind to this file + `environments.md` verbatim. Bump `DiagramRenderer.version` whenever the HTML shape in §8 or the class-name contract in `environments.md` §9 changes.
