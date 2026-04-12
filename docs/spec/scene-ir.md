# 05 — Scene IR (Intermediate Representation)

> Status: **locked foundation spec** for Scriba v0.3. This file is the single source of
> truth for the internal Scene IR datatypes emitted by `SceneParser` and consumed by
> the Starlark host, primitive catalog, SVG emitter, and HTML stitcher.
>
> Cross-references: [`environments.md`](environments.md) §10.3 for the
> parser-to-IR contract, §3 for the 8 inner commands, §4 for target selector syntax,
> §6 for frame semantics. [`03-diagram-plugin.md`](../guides/diagram-plugin.md) §4 step 6 for
> `DiagramIR`. [`09-animation-plugin.md`](../guides/animation-plugin.md) §4 for `AnimationIR`
> and `FrameIR`. [`primitives.md`](primitives.md) for the primitive catalog that
> interprets `ShapeCommand` parameters.
>
> Type safety: Scene IR types are Pydantic v2 `BaseModel` subclasses throughout (see
> [`oss/O4-quality-bar.md`](../oss/O4-quality-bar.md) §4). Parsed values are validated at
> IR boundaries, not inside rendering code.

---

## 1. Overview

The Scene IR is the **typed, frozen intermediate representation** that sits between the
`SceneParser` (which walks the LaTeX environment body) and the downstream rendering
pipeline (Starlark host, primitive catalog, SVG emitter, HTML stitcher). Every
`\begin{animation}` or `\begin{diagram}` environment is parsed into exactly one Scene IR
value, which is then consumed read-only by all subsequent stages.

```text
LaTeX source
     │
     ▼
 SceneParser
     │
     ▼
 Scene IR  ──────────────────────────────────────────────────┐
  (AnimationIR / DiagramIR)                                  │
     │                                                       │
     ├── Starlark host: reads ComputeCommand.source          │
     │   ↓ bindings                                          │
     ├── Primitive catalog: reads ShapeCommand.params        │
     │   ↓ instantiated shapes                               │
     ├── Scene materializer: reads mutation commands,        │
     │   builds SceneState per frame                         │
     │   ↓ per-frame SceneState                              │
     ├── SVG emitter: reads SceneState + options             │
     │   ↓ SVG strings                                       │
     └── HTML stitcher: reads options + narration bodies     │
         ↓ final RenderArtifact                              │
                                                             │
```

Design invariants:

1. **Immutable after construction.** All IR types are frozen (Pydantic `model_config = ConfigDict(frozen=True)`). Downstream stages never mutate the IR; they build new data structures (`SceneState`) from it.
2. **Source positions preserved.** Every command node carries `line: int` and `col: int` fields so error messages can point at the offending source location.
3. **Serializable.** IR values round-trip through `model_dump()` / `model_validate()` for snapshot testing and debugging.
4. **Mode-agnostic commands.** The 8 command IR types are shared between `AnimationIR` and `DiagramIR`. The container types (`AnimationIR` vs `DiagramIR`) enforce mode-specific constraints (e.g., animation allows `\step` and `\narrate`; diagram forbids both).

---

## 2. Module layout

```text
scriba/animation/parser/
├── ast.py          ← Command IR types (§3) and container IR types (§4–§6)
├── lexer.py        ← Tokenizer (not covered in this spec)
├── grammar.py      ← Recursive-descent parser (not covered in this spec)
└── selectors.py    ← Selector parser (not covered in this spec)
```

All IR types are defined in `scriba/animation/parser/ast.py` and re-exported from
`scriba.animation.parser`.

---

## 3. Command IR types

Each of the 8 inner commands from [`environments.md`](environments.md) §3
is represented by a frozen dataclass. All command types share a common base.

### 3.1 Base fields

Every command IR type includes:

| Field   | Type  | Description                                           |
|---------|-------|-------------------------------------------------------|
| `line`  | `int` | 1-based line number in the environment body.          |
| `col`   | `int` | 1-based column number of the command's leading `\`.   |

These fields are used exclusively for error reporting and are never consulted by
rendering logic.

### 3.2 `ShapeCommand`

Produced by `\shape{name}{Type}{params...}`.

```python
class ShapeCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
    name: str                        # e.g. "dp", "stones", "T"
    type_name: str                   # e.g. "Array", "Graph", "Tree"
    params: dict[str, ParamValue]    # e.g. {"size": 7, "labels": "0..6"}
```

| Field       | Type                      | Constraints                                                |
|-------------|---------------------------|------------------------------------------------------------|
| `name`      | `str`                     | Matches `[a-z][a-zA-Z0-9_]*`. Unique per environment (`E1101`). |
| `type_name` | `str`                     | One of the 6 built-in primitives (`E1102` on unknown).     |
| `params`    | `dict[str, ParamValue]`   | Primitive-specific. See [`primitives.md`](primitives.md). Missing required param is `E1103`; type mismatch is `E1104`. |

`ParamValue` is a union type:

```python
ParamValue = int | float | str | bool | list["ParamValue"] | InterpolationRef
```

Where `InterpolationRef` represents an unresolved `${name}` or `${name[i]}` reference
that will be resolved against Starlark bindings at evaluation time.

### 3.3 `ComputeCommand`

Produced by `\compute{...Starlark...}`.

```python
class ComputeCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
    source: str    # raw Starlark source, whitespace-preserved
```

| Field    | Type  | Constraints                                                          |
|----------|-------|----------------------------------------------------------------------|
| `source` | `str` | The verbatim Starlark source between the outer braces. Not parsed or validated at IR level; validation happens in the Starlark worker (errors `E1150`..`E1157`). |

### 3.4 `StepCommand`

Produced by `\step`.

```python
class StepCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
```

No additional fields. `StepCommand` is a pure delimiter that marks frame boundaries.
Forbidden in diagram mode (`E1050`). Trailing text on the same line is `E1052`.

### 3.5 `NarrateCommand`

Produced by `\narrate{LaTeX text}`.

```python
class NarrateCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
    body: str    # raw LaTeX, passed to ctx.render_inline_tex
```

| Field  | Type  | Constraints                                                            |
|--------|-------|------------------------------------------------------------------------|
| `body` | `str` | Balanced LaTeX text. Passed verbatim to `RenderContext.render_inline_tex`. Not parsed at IR level. |

Forbidden in diagram mode (`E1054`). At most one per `\step` block (`E1055`).
Must be inside a `\step` block (`E1056`).

### 3.6 `ApplyCommand`

Produced by `\apply{target}{params...}`.

```python
class ApplyCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
    target: Selector               # parsed target selector
    params: dict[str, ParamValue]  # e.g. {"value": 0, "label": "min"}
```

| Field    | Type                    | Constraints                                                  |
|----------|-------------------------|--------------------------------------------------------------|
| `target` | `Selector`              | Parsed per §4 selector grammar. Unknown shape is `E1106`.    |
| `params` | `dict[str, ParamValue]` | Common: `value`, `label`, `tooltip`. Unknown param is `E1105`; type mismatch is `E1107`. |

Persistence: `\apply` mutations are **persistent** across frames until overwritten.

### 3.7 `HighlightCommand`

Produced by `\highlight{target}`.

```python
class HighlightCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
    target: Selector    # parsed target selector
```

| Field    | Type       | Constraints                                  |
|----------|------------|----------------------------------------------|
| `target` | `Selector` | Unknown target is `E1108`.                   |

No parameters. In animation mode, highlight is **ephemeral** (cleared at next `\step`).
In diagram mode, highlight is persistent (single frame). Forbidden in animation
prelude (`E1053`).

### 3.8 `RecolorCommand`

Produced by `\recolor{target}{state=..., color=..., arrow_from=...}`.

```python
class RecolorCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
    target: Selector                    # parsed target selector
    state: str | None = None            # one of the 7 locked states
    annotation_color: str | None = None # recolor annotation(s) on target
    annotation_from: str | None = None  # filter by source selector
```

| Field              | Type              | Constraints                                                     |
|--------------------|-------------------|-----------------------------------------------------------------|
| `target`           | `Selector`        | Unknown target is `E1110`.                                      |
| `state`            | `str \| None`     | Must be one of: `idle`, `current`, `done`, `dim`, `error`, `good`, `path`. Unknown state is `E1109`. Optional if `annotation_color` is present. |
| `annotation_color` | `str \| None`     | Recolors annotation(s) on the target. Valid values: `info`, `warn`, `good`, `error`, `muted`, `path`. Maps to `color=` in LaTeX syntax. |
| `annotation_from`  | `str \| None`     | Filters which annotation to recolor by source selector string. Maps to `arrow_from=` in LaTeX syntax. |

At least one of `state` or `annotation_color` must be present (`E1109`).

Persistence: **persistent** across frames until overwritten.

### 3.9 `AnnotateCommand`

Produced by `\annotate{target}{params...}`.

```python
class AnnotateCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    line: int
    col: int
    target: Selector               # parsed target selector
    label: str | None = None       # annotation text
    position: str = "above"        # above | below | left | right | inside
    color: str = "info"            # info | warn | good | error | muted | path
    arrow: bool = False            # True for graph/tree by default
    ephemeral: bool = False        # drop at next \step if True
    arrow_from: Selector | None = None  # source target for transition arrows
```

| Field        | Type              | Default   | Constraints                                    |
|--------------|-------------------|-----------|-------------------------------------------------|
| `target`     | `Selector`        | required  | Unknown target is `E1111`.                      |
| `label`      | `str \| None`     | `None`    | Annotation text.                                |
| `position`   | `str`             | `"above"` | Must be: `above`, `below`, `left`, `right`, `inside`. Unknown is `E1112`. |
| `color`      | `str`             | `"info"`  | Must be: `info`, `warn`, `good`, `error`, `muted`, `path`. Unknown is `E1113`. |
| `arrow`      | `bool`            | `False`   | `True` for graph/tree edges by default.         |
| `ephemeral`  | `bool`            | `False`   | When `True`, dropped at the next `\step`.       |
| `arrow_from` | `Selector \| None`| `None`    | Source target for DPTable transition arrows.    |

---

## 4. Selector type

The `Selector` type represents a parsed target selector per
[`environments.md`](environments.md) §4.

```python
class Selector(BaseModel):
    model_config = ConfigDict(frozen=True)

    shape_name: str                          # e.g. "dp", "G", "T"
    accessor: SelectorAccessor | None = None # None means "whole shape"
```

`SelectorAccessor` is a union of accessor variants:

```python
class CellAccessor(BaseModel):
    model_config = ConfigDict(frozen=True)
    indices: tuple[IndexExpr, ...]   # 1 index for 1D, 2 for 2D

class NodeAccessor(BaseModel):
    model_config = ConfigDict(frozen=True)
    node_id: IndexExpr               # number, string, or interpolation

class EdgeAccessor(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: IndexExpr
    target: IndexExpr

class RangeAccessor(BaseModel):
    model_config = ConfigDict(frozen=True)
    lo: IndexExpr
    hi: IndexExpr

class AllAccessor(BaseModel):
    model_config = ConfigDict(frozen=True)

class NamedAccessor(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str                         # e.g. "axis"

SelectorAccessor = (
    CellAccessor | NodeAccessor | EdgeAccessor |
    RangeAccessor | AllAccessor | NamedAccessor
)
```

`IndexExpr` is a union of literal values and interpolation references:

```python
IndexExpr = int | str | InterpolationRef
```

`InterpolationRef` represents `${name}` or `${name[i][j]...}`:

```python
class InterpolationRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str                        # binding name
    subscripts: tuple[IndexExpr, ...] = ()  # chained subscripts
```

### 4.1 Selector resolution

Selectors are resolved **after** Starlark evaluation. The resolution pipeline:

1. Replace every `InterpolationRef` with its concrete value from the merged scope (`global ∪ frame_local`).
2. Unknown binding raises `E1155`. Out-of-range subscript raises `E1156`. Non-integer where integer required raises `E1157`.
3. Validate that `shape_name` matches a declared `\shape` name. Unknown shape raises `E1106`.
4. Validate that the accessor is legal for that primitive type (e.g., `.cell[i]` on `Array` but not on `Graph`). Invalid accessor raises `E1106`.

---

## 5. Environment options

Both `AnimationIR` and `DiagramIR` carry a typed options object parsed from the
`[key=value,...]` header.

### 5.1 `AnimationOptions`

```python
class AnimationOptions(BaseModel):
    model_config = ConfigDict(frozen=True)

    width: str | None = None         # dimension or "auto"
    height: str | None = None        # dimension or "auto"
    id: str | None = None            # scene id, must match [a-z][a-z0-9-]*
    label: str | None = None         # aria-label for <figure>
    layout: Literal["filmstrip", "stack"] = "filmstrip"
```

### 5.2 `DiagramOptions`

```python
class DiagramOptions(BaseModel):
    model_config = ConfigDict(frozen=True)

    width: str | None = None
    height: str | None = None
    id: str | None = None
    label: str | None = None
    grid: Literal["on", "off"] = "off"   # authoring aid only
```

Unknown keys in either options type raise `E1004`.

---

## 6. Container IR types

### 6.1 `FrameIR`

Represents a single `\step` block within an animation. One `FrameIR` per `\step`.

```python
class FrameIR(BaseModel):
    model_config = ConfigDict(frozen=True)

    commands: tuple[Command, ...]        # ApplyCommand | HighlightCommand |
                                         # RecolorCommand | AnnotateCommand
                                         # in source order
    compute: tuple[ComputeCommand, ...]  # frame-local \compute blocks
    narrate_body: str | None = None      # raw LaTeX from \narrate, or None
    line: int                            # line of the opening \step
```

| Field          | Type                       | Description                                            |
|----------------|----------------------------|--------------------------------------------------------|
| `commands`     | `tuple[Command, ...]`      | State-mutation commands in source order: `\apply`, `\highlight`, `\recolor`, `\annotate`. |
| `compute`      | `tuple[ComputeCommand, ...]`| Frame-local `\compute` blocks. Bindings are scoped to this frame only (per `environments.md` §5.3). |
| `narrate_body` | `str \| None`              | The raw LaTeX body of the `\narrate` command, or `None` if absent (`E1150` warning). |
| `line`         | `int`                      | Line number of the `\step` that opens this frame.      |

`Command` is the union type for frame-level mutation commands:

```python
Command = ApplyCommand | HighlightCommand | RecolorCommand | AnnotateCommand
```

### 6.2 `AnimationIR`

Top-level IR for a `\begin{animation}` environment.

```python
class AnimationIR(BaseModel):
    model_config = ConfigDict(frozen=True)

    options: AnimationOptions
    shapes: tuple[ShapeCommand, ...]              # all \shape declarations
    prelude_compute: tuple[ComputeCommand, ...]   # global \compute blocks
    prelude_commands: tuple[Command, ...]          # prelude state mutations
    frames: tuple[FrameIR, ...]                    # one per \step
    source_hash: str                               # sha256(block.raw)[:10]
```

| Field              | Type                            | Description                                          |
|--------------------|---------------------------------|------------------------------------------------------|
| `options`          | `AnimationOptions`              | Validated `[key=value,...]` header.                  |
| `shapes`           | `tuple[ShapeCommand, ...]`      | All `\shape` declarations from the prelude. Order preserved. |
| `prelude_compute`  | `tuple[ComputeCommand, ...]`    | Global `\compute` blocks from the prelude. Bindings persist across all frames. |
| `prelude_commands` | `tuple[Command, ...]`           | `\apply`, `\recolor`, `\annotate` from the prelude (initial state). `\highlight` in prelude is `E1053`. |
| `frames`           | `tuple[FrameIR, ...]`           | Ordered frames, one per `\step`. At least 1 required (`E1057`). Max 100 (`E1181`). |
| `source_hash`      | `str`                           | First 10 hex chars of SHA-256 of `block.raw`. Used for auto-generated scene id when `id=` option is absent. |

### 6.3 `DiagramIR`

Top-level IR for a `\begin{diagram}` environment.

```python
class DiagramIR(BaseModel):
    model_config = ConfigDict(frozen=True)

    options: DiagramOptions
    shapes: tuple[ShapeCommand, ...]              # all \shape declarations
    compute_blocks: tuple[ComputeCommand, ...]    # all \compute blocks
    commands: tuple[Command, ...]                  # state mutations in source order
    source_hash: str                               # sha256(block.raw)[:10]
```

| Field            | Type                           | Description                                          |
|------------------|--------------------------------|------------------------------------------------------|
| `options`        | `DiagramOptions`               | Validated `[key=value,...]` header.                  |
| `shapes`         | `tuple[ShapeCommand, ...]`     | All `\shape` declarations. Order preserved.          |
| `compute_blocks` | `tuple[ComputeCommand, ...]`   | All `\compute` blocks in source order.               |
| `commands`       | `tuple[Command, ...]`          | State-mutation commands in source order.             |
| `source_hash`    | `str`                          | First 10 hex chars of SHA-256 of `block.raw`.        |

Diagram-specific constraints enforced at parse time:

- `\step` → `E1050`.
- `\narrate` → `E1054`.
- `\highlight` is **allowed** and persistent (single-frame semantics).

---

## 7. `SceneState` (runtime, not IR)

`SceneState` is **not** part of the frozen IR. It is a mutable runtime dict built by the
scene materializer from the IR. It is documented here because the IR is designed to
produce it.

```python
# scriba/animation/scene.py

SceneState = dict[str, TargetState]

@dataclass
class TargetState:
    value: Any = None
    state: str = "idle"              # one of the 7 locked states
    annotations: list[Annotation] = field(default_factory=list)
    label: str | None = None
    tooltip: str | None = None

@dataclass
class Annotation:
    label: str | None
    position: str            # above | below | left | right | inside
    color: str               # info | warn | good | error | muted | path
    arrow: bool
    ephemeral: bool
    arrow_from: str | None   # resolved selector string, or None
```

Keys are resolved selector strings (e.g., `"dp.cell[0]"`, `"G.node[A]"`).

### 7.1 Delta application rules

Per [`environments.md`](environments.md) §6.1, the scene materializer
applies `AnimationIR` to produce one `SceneState` per frame:

1. **Initial state.** Instantiate shapes from `AnimationIR.shapes`. Apply
   `AnimationIR.prelude_commands` in source order. Evaluate
   `AnimationIR.prelude_compute` in the Starlark worker.
2. **Frame k (k >= 1).** Start from the `SceneState` at end of frame k-1 (or the
   initial state for frame 1).
   - Clear all targets whose state is `highlight`.
   - Drop all annotations where `ephemeral=True`.
   - Evaluate `FrameIR.compute` in the Starlark worker (frame-local scope).
   - Apply `FrameIR.commands` in source order against the merged scope
     (`global ∪ frame_local`).
3. **Render.** Pass the resulting `SceneState` + `AnimationOptions` to the SVG emitter.

For `DiagramIR`, the flow is single-pass: evaluate compute blocks, instantiate shapes,
apply commands, render once.

---

## 8. How downstream consumers use Scene IR

### 8.1 SceneParser → Scene IR

The `SceneParser` (`scriba/animation/parser/grammar.py`) walks the environment body
line by line and emits either an `AnimationIR` or `DiagramIR` depending on the mode
parameter:

```python
class SceneParser:
    def parse(
        self,
        raw: str,
        metadata: dict[str, Any],
        mode: Literal["animation", "diagram"] = "diagram",
    ) -> AnimationIR | DiagramIR:
        ...
```

The parser:

1. Lexes the `[key=value,...]` header into `AnimationOptions` or `DiagramOptions`.
2. Walks commands via the brace reader and command lexer.
3. Parses selectors via `selectors.py`.
4. Splits commands into prelude vs frames (animation) or flat list (diagram).
5. Validates constraints (shape before step, narrate cardinality, frame count limits).
6. Returns a frozen IR value.

All parse errors raise `RendererError(code="E1xxx")` with `line` and `col` from the
offending token.

### 8.2 Starlark host

The Starlark host reads `ComputeCommand.source` from:

- `AnimationIR.prelude_compute` (global scope).
- `FrameIR.compute` (frame-local scope).
- `DiagramIR.compute_blocks` (single flat scope).

It sends each source string to the Starlark subprocess worker and collects bindings.
The host never modifies the IR; it builds a scope dict that is passed alongside the IR
to subsequent stages.

### 8.3 Primitive catalog

The primitive catalog reads `ShapeCommand` values from `AnimationIR.shapes` or
`DiagramIR.shapes`. For each shape:

1. Look up `ShapeCommand.type_name` in the primitive registry (`E1102` on miss).
2. Resolve `InterpolationRef` values in `ShapeCommand.params` against the Starlark scope.
3. Validate required and optional parameters per [`primitives.md`](primitives.md).
4. Instantiate the primitive, computing layout (positions, sizes, topology) once.
5. Register addressable parts as valid selector targets for downstream command validation.

### 8.4 SVG emitter

The SVG emitter reads the materialized `SceneState` (built from the IR) and
`AnimationOptions` / `DiagramOptions` (from the IR). For each frame (animation) or
once (diagram):

1. Iterate over declared shapes in source order.
2. For each addressable part, read its `TargetState` from `SceneState`.
3. Emit `<g data-target="...">` groups with state classes applied.
4. Emit annotation overlays inside target groups.
5. Wrap in `<svg class="scriba-stage-svg" viewBox="...">`.

The emitter never reads the IR directly for command data; it only reads
`SceneState` (the materialized result of applying IR commands) and the options.

---

## 9. Type summary

| Type                | Module                  | Frozen | Description                                    |
|---------------------|-------------------------|--------|-------------------------------------------------|
| `ShapeCommand`      | `parser/ast.py`         | Yes    | `\shape{name}{Type}{params}`                   |
| `ComputeCommand`    | `parser/ast.py`         | Yes    | `\compute{...}`                                |
| `StepCommand`       | `parser/ast.py`         | Yes    | `\step`                                        |
| `NarrateCommand`    | `parser/ast.py`         | Yes    | `\narrate{...}`                                |
| `ApplyCommand`      | `parser/ast.py`         | Yes    | `\apply{target}{params}`                       |
| `HighlightCommand`  | `parser/ast.py`         | Yes    | `\highlight{target}`                           |
| `RecolorCommand`    | `parser/ast.py`         | Yes    | `\recolor{target}{state=..., color=..., arrow_from=...}` |
| `AnnotateCommand`   | `parser/ast.py`         | Yes    | `\annotate{target}{params}`                    |
| `Selector`          | `parser/ast.py`         | Yes    | Parsed target selector                         |
| `InterpolationRef`  | `parser/ast.py`         | Yes    | `${name}` / `${name[i]}` reference             |
| `AnimationOptions`  | `parser/ast.py`         | Yes    | `[key=value,...]` for animation                |
| `DiagramOptions`    | `parser/ast.py`         | Yes    | `[key=value,...]` for diagram                  |
| `FrameIR`           | `parser/ast.py`         | Yes    | One `\step` block with commands + narration    |
| `AnimationIR`       | `parser/ast.py`         | Yes    | Top-level IR for `\begin{animation}`           |
| `DiagramIR`         | `parser/ast.py`         | Yes    | Top-level IR for `\begin{diagram}`             |
| `SceneState`        | `scene.py`              | No     | Runtime mutable dict (not IR)                  |
| `TargetState`       | `scene.py`              | No     | Per-target runtime state (not IR)              |

---

## 10. Validation order

The parser validates constraints in this order, failing fast on the first error:

1. **Option validation.** Unknown keys (`E1004`), malformed values (`E1005`).
2. **Command lexing.** Unknown commands (`E1006`), missing brace args (`E1007`), stray text (`E1008`), unbalanced braces (`E1001`).
3. **Mode constraints.** `\step` in diagram (`E1050`), `\narrate` in diagram (`E1054`).
4. **Ordering constraints.** `\shape` after `\step` (`E1051`), `\step` trailing text (`E1052`), `\highlight` in prelude (`E1053`), `\narrate` outside `\step` (`E1056`), duplicate `\narrate` (`E1055`).
5. **Shape validation.** Duplicate name (`E1101`), unknown type (`E1102`), missing required param (`E1103`), param type mismatch (`E1104`).
6. **Selector validation.** Unknown shape in target (`E1106`), unknown target for highlight (`E1108`), recolor (`E1110`), annotate (`E1111`).
7. **State/color validation.** Unknown recolor state or missing both state and color (`E1109`), unknown annotation position (`E1112`), unknown annotation color (`E1113`).
8. **Frame count validation.** Zero frames (`E1057`), soft limit >30 (`E1180` warning), hard limit >100 (`E1181` error).
9. **Narration validation.** Missing narration (`E1150` warning in strict), missing narration strict (`E1182` error).

Note: `\apply` parameter validation (`E1105`, `E1107`) and interpolation resolution
(`E1155`, `E1156`, `E1157`) happen **after** Starlark evaluation, not during parsing,
because parameter values may depend on computed bindings.

---

## 11. Example: IR from a simple animation

Given this source:

```latex
\begin{animation}[id=demo, label="Demo"]
\compute{ dp = [0, 7, 4] }
\shape{a}{Array}{size=3, data=${dp}}

\step
\recolor{a.cell[0]}{state=done}
\highlight{a.cell[1]}
\narrate{Initialize $dp[0] = 0$.}

\step
\recolor{a.cell[1]}{state=done}
\annotate{a.cell[1]}{label="7", color=good}
\narrate{Compute $dp[1] = 7$.}
\end{animation}
```

The parser emits:

```python
AnimationIR(
    options=AnimationOptions(id="demo", label="Demo", layout="filmstrip"),
    shapes=(
        ShapeCommand(line=3, col=1, name="a", type_name="Array",
                     params={"size": 3, "data": InterpolationRef(name="dp")}),
    ),
    prelude_compute=(
        ComputeCommand(line=2, col=1, source="dp = [0, 7, 4]"),
    ),
    prelude_commands=(),
    frames=(
        FrameIR(
            line=5, narrate_body="Initialize $dp[0] = 0$.",
            compute=(),
            commands=(
                RecolorCommand(line=6, col=1,
                    target=Selector(shape_name="a",
                        accessor=CellAccessor(indices=(0,))),
                    state="done"),
                HighlightCommand(line=7, col=1,
                    target=Selector(shape_name="a",
                        accessor=CellAccessor(indices=(1,)))),
            ),
        ),
        FrameIR(
            line=10, narrate_body="Compute $dp[1] = 7$.",
            compute=(),
            commands=(
                RecolorCommand(line=11, col=1,
                    target=Selector(shape_name="a",
                        accessor=CellAccessor(indices=(1,))),
                    state="done"),
                AnnotateCommand(line=12, col=1,
                    target=Selector(shape_name="a",
                        accessor=CellAccessor(indices=(1,))),
                    label="7", color="good"),
            ),
        ),
    ),
    source_hash="a1b2c3d4e5",
)
```

---

**End of Scene IR spec.** All downstream specs (`primitives.md`, `07-starlark-worker.md`,
`08-svg-emitter.md`, `03-diagram-plugin.md`, `09-animation-plugin.md`) bind to the types
defined here. Adding a new field to any IR type is a MINOR version bump. Removing or
renaming a field is a MAJOR version bump.
