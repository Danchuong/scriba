"""AnimationRenderer — Renderer protocol implementation for animation blocks.

Wires detection, parsing, scene materialisation, primitive SVG emission,
and HTML stitching into the :class:`Renderer` protocol defined in
:mod:`scriba.core.renderer`.

Pipeline (end-to-end):
    block.raw → SceneParser().parse() → AnimationIR
    → StarlarkHost.eval() for \\compute blocks → bindings
    → SceneState.apply_prelude() → initial state with shapes
    → For each frame: SceneState.apply_frame() → per-frame state
    → Collect primitive emit_svg() + narration
    → emit_animation_html() → final HTML
    → RenderArtifact(html, css_assets, js_assets)
"""

from __future__ import annotations

import hashlib
import html as _html
import logging
import re
from importlib.resources import files
from pathlib import Path
from typing import Any

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.emitter import FrameData, SubstoryData, emit_animation_html, emit_html, scene_id_from_source
from scriba.animation.errors import FrameCountError
from scriba.animation.extensions.hl_macro import process_hl_macros
from scriba.animation.extensions.keyframes import generate_keyframe_styles
from scriba.animation.parser.ast import (
    AnimationIR,
    ShapeCommand,
    SubstoryBlock,
)
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives import (
    ArrayPrimitive,
    DPTablePrimitive,
    Graph,
    GridPrimitive,
    MatrixPrimitive,
    MetricPlot,
    NumberLinePrimitive,
    Plane2D,
    Stack,
    Tree,
)
from scriba.animation.scene import FrameSnapshot, SceneState
from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.errors import RendererError, ValidationError

__all__ = ["AnimationRenderer", "DiagramRenderer"]

logger = logging.getLogger(__name__)

_FRAME_WARN_THRESHOLD = 30
_FRAME_ERROR_THRESHOLD = 100

# ---------------------------------------------------------------------------
# Primitive catalog
# ---------------------------------------------------------------------------

PRIMITIVE_CATALOG: dict[str, Any] = {
    "Array": ArrayPrimitive,
    "DPTable": DPTablePrimitive,
    "Graph": Graph,
    "Grid": GridPrimitive,
    "Heatmap": MatrixPrimitive,
    "Matrix": MatrixPrimitive,
    "MetricPlot": MetricPlot,
    "NumberLine": NumberLinePrimitive,
    "Plane2D": Plane2D,
    "Stack": Stack,
    "Tree": Tree,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_ENV_BEGIN_RE = re.compile(
    r"\\begin\{animation\}(\[[^\]]*\])?\s*\n?",
)
_ENV_END_RE = re.compile(
    r"\s*\\end\{animation\}\s*$",
)


def _strip_environment(raw: str) -> tuple[str, str]:
    """Strip ``\\begin{animation}[opts]`` and ``\\end{animation}`` delimiters.

    Returns ``(body, options_bracket)`` where *options_bracket* is the
    ``[key=val,...]`` string including brackets, or empty string.
    """
    begin_m = _ENV_BEGIN_RE.match(raw)
    opts_str = begin_m.group(1) or "" if begin_m else ""
    body_start = begin_m.end() if begin_m else 0

    end_m = _ENV_END_RE.search(raw, body_start)
    body_end = end_m.start() if end_m else len(raw)

    return raw[body_start:body_end], opts_str


def _scene_id(raw: str) -> str:
    """Deterministic scene ID from block source."""
    digest = hashlib.sha256(raw.encode()).hexdigest()[:10]
    return f"scriba-{digest}"


def _render_narration(
    text: str | None,
    scene_id: str,
    ctx: RenderContext,
) -> str:
    """Render narration text through hl macros and optional TeX."""
    if text is None:
        return ""
    processed = process_hl_macros(
        text,
        scene_id=scene_id,
        render_inline_tex=ctx.render_inline_tex,
    )
    if ctx.render_inline_tex is not None:
        return ctx.render_inline_tex(processed)
    return _html.escape(processed, quote=False)


def _resolve_params(
    params: dict[str, Any],
    bindings: dict[str, Any],
) -> dict[str, Any]:
    """Resolve ${interpolation} references in shape parameters."""
    from scriba.animation.parser.ast import InterpolationRef

    resolved: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, InterpolationRef):
            result = bindings.get(value.name, value.name)
            for sub in value.subscripts:
                if isinstance(sub, int) and isinstance(result, (list, tuple)):
                    result = result[sub]
                elif isinstance(sub, str) and isinstance(result, dict):
                    result = result[sub]
            resolved[key] = result
        elif isinstance(value, list):
            resolved[key] = [
                _resolve_single(v, bindings) for v in value
            ]
        else:
            resolved[key] = value
    return resolved


def _resolve_single(value: Any, bindings: dict[str, Any]) -> Any:
    """Resolve a single parameter value."""
    from scriba.animation.parser.ast import InterpolationRef

    if isinstance(value, InterpolationRef):
        result = bindings.get(value.name, value.name)
        for sub in value.subscripts:
            if isinstance(sub, int) and isinstance(result, (list, tuple)):
                result = result[sub]
            elif isinstance(sub, str) and isinstance(result, dict):
                result = result[sub]
        return result
    return value


def _instantiate_primitive(
    shape: ShapeCommand,
    bindings: dict[str, Any],
) -> Any:
    """Create a primitive instance from a shape declaration."""
    factory_cls = PRIMITIVE_CATALOG.get(shape.type_name)
    if factory_cls is None:
        raise ValidationError(
            f"unknown primitive type {shape.type_name!r}",
            code="E1102",
        )
    resolved_params = _resolve_params(shape.params, bindings)

    if shape.type_name in ("Graph", "Tree", "Stack", "Plane2D", "MetricPlot"):
        return factory_cls(shape.name, resolved_params)

    factory = factory_cls()
    return factory.declare(shape.name, resolved_params)


def _snapshot_to_frame_data(
    snap: FrameSnapshot,
    total_frames: int,
    scene_id: str,
    ctx: RenderContext,
    substories: list[SubstoryData] | None = None,
) -> FrameData:
    """Convert a FrameSnapshot into a FrameData for the emitter."""
    shape_states: dict[str, dict[str, dict]] = {}
    for shape_name, targets in snap.shape_states.items():
        shape_states[shape_name] = {}
        for target_key, ts in targets.items():
            entry: dict[str, Any] = {"state": ts.state}
            if ts.value is not None:
                entry["value"] = ts.value
            if ts.label is not None:
                entry["label"] = ts.label
            if ts.apply_params is not None:
                entry["apply_params"] = ts.apply_params
            shape_states[shape_name][target_key] = entry

    # Mark highlighted targets (additive — does not replace state)
    for hl_target in snap.highlights:
        parts = hl_target.split(".", 1)
        if len(parts) == 2:
            sname = parts[0]
            if sname in shape_states:
                if hl_target in shape_states[sname]:
                    shape_states[sname][hl_target]["highlighted"] = True
                else:
                    # Target not in state map yet — only set highlighted flag
                    shape_states[sname][hl_target] = {"highlighted": True}

    annotations = [
        {
            "target": a.target,
            "label": a.text,
            "ephemeral": a.ephemeral,
            "arrow_from": a.arrow_from,
            "color": a.color,
        }
        for a in snap.annotations
    ]

    narration_html = _render_narration(snap.narration, scene_id, ctx)

    return FrameData(
        step_number=snap.index,
        total_frames=total_frames,
        narration_html=narration_html,
        shape_states=shape_states,
        annotations=annotations,
        substories=substories,
    )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class AnimationRenderer:
    """Renderer implementation for ``\\begin{animation}`` environments.

    Implements the ``Renderer`` protocol from :mod:`scriba.core.renderer`.
    """

    name: str = "animation"
    version: int = 1
    priority: int = 10

    def __init__(
        self,
        *,
        starlark_host: Any | None = None,
    ) -> None:
        self._starlark_host = starlark_host
        # Populated by _materialise; available after render_block().
        self.last_snapshots: list[FrameSnapshot] = []

    # ---- Renderer protocol ----

    def detect(self, source: str) -> list[Block]:
        """Scan *source* for animation environments."""
        return detect_animation_blocks(source)

    def render_block(
        self,
        block: Block,
        ctx: RenderContext,
    ) -> RenderArtifact:
        """Parse, materialise scenes, and emit HTML for one animation block."""
        ir = self._parse(block)

        scene_id = (
            ir.options.id
            if ir.options.id is not None
            else _scene_id(block.raw)
        )

        # Instantiate primitives from shape declarations
        primitives = self._instantiate_primitives(ir)

        # Run the scene state machine (includes substory processing)
        frames = self._materialise(ir, ctx, scene_id)

        # Count all frames including substory frames for budget
        frame_count = len(frames)
        total_with_substories = frame_count + self._count_substory_frames(frames)
        if total_with_substories > _FRAME_ERROR_THRESHOLD:
            raise FrameCountError(total_with_substories)
        if total_with_substories > _FRAME_WARN_THRESHOLD:
            logger.warning(
                "animation %s has %d frames (>%d); consider splitting",
                scene_id,
                total_with_substories,
                _FRAME_WARN_THRESHOLD,
            )

        # Produce final HTML via the emitter
        output_mode = ctx.metadata.get("output_mode", "interactive")
        minify = ctx.metadata.get("minify", True)
        html = emit_html(
            scene_id, frames, primitives, mode=output_mode,
            render_inline_tex=ctx.render_inline_tex,
            minify=minify,
        )

        # Collect CSS assets
        css_assets: set[str] = {
            "scriba-animation.css",
            "scriba-scene-primitives.css",
        }

        # Add primitive-specific CSS when those primitives are present
        _PRIMITIVE_CSS: dict[str, str] = {
            "Plane2D": "scriba-plane2d.css",
            "MetricPlot": "scriba-metricplot.css",
        }
        for shape in ir.shapes:
            css_name = _PRIMITIVE_CSS.get(shape.type_name)
            if css_name is not None:
                css_assets.add(css_name)

        return RenderArtifact(
            html=html,
            css_assets=frozenset(css_assets),
            js_assets=frozenset(),
            block_id=scene_id,
            data={"frame_count": frame_count},
        )

    def assets(self) -> RendererAssets:
        """Return the always-on CSS files for animation blocks."""
        static = files("scriba.animation").joinpath("static")
        css_files: set[Path] = set()
        for name in (
            "scriba-animation.css",
            "scriba-scene-primitives.css",
            "scriba-plane2d.css",
            "scriba-metricplot.css",
        ):
            path = Path(str(static / name))
            if path.exists():
                css_files.add(path)
        return RendererAssets(
            css_files=frozenset(css_files),
            js_files=frozenset(),
        )

    # ---- private ----

    def _parse(self, block: Block) -> AnimationIR:
        """Parse a block into AnimationIR using the real SceneParser.

        Strips the ``\\begin{animation}[opts]`` / ``\\end{animation}``
        delimiters and passes the options string to the parser separately
        via the body content (the parser expects ``[opts]\\n...body...``).
        """
        raw = block.raw
        # Extract the body between \begin{animation}[...] and \end{animation}
        body, opts_str = _strip_environment(raw)
        # Re-prefix the options bracket so the parser can see [id=..., ...]
        parse_input = opts_str + "\n" + body if opts_str else body
        return SceneParser().parse(parse_input)

    @staticmethod
    def _count_substory_frames(frames: list[FrameData]) -> int:
        """Count total substory frames recursively."""
        count = 0
        for frame in frames:
            if frame.substories:
                for sub in frame.substories:
                    count += len(sub.frames)
                    count += AnimationRenderer._count_substory_frames(sub.frames)
        return count

    def _instantiate_primitives(self, ir: AnimationIR) -> dict[str, Any]:
        """Create primitive instances from shape declarations.

        Resolves interpolation references using prelude compute bindings.
        """
        bindings: dict[str, Any] = {}
        if self._starlark_host is not None:
            for cb in ir.prelude_compute:
                result = self._starlark_host.eval(bindings, cb.source)
                if isinstance(result, dict):
                    bindings.update(result)

        primitives: dict[str, Any] = {}
        for shape in ir.shapes:
            primitives[shape.name] = _instantiate_primitive(
                shape, bindings,
            )
        return primitives

    def _materialise(
        self, ir: AnimationIR, ctx: RenderContext, scene_id: str,
    ) -> list[FrameData]:
        """Run the delta state machine, process substories, return FrameData."""
        state = SceneState()
        state.apply_prelude(
            shapes=ir.shapes,
            prelude_commands=ir.prelude_commands,
            prelude_compute=ir.prelude_compute,
            starlark_host=self._starlark_host,
        )

        total_frames = len(ir.frames)
        frame_data_list: list[FrameData] = []
        snapshots: list[FrameSnapshot] = []

        for frame_ir in ir.frames:
            snap = state.apply_frame(frame_ir, starlark_host=self._starlark_host)
            snapshots.append(snap)

            # Process substories for this frame
            substory_data: list[SubstoryData] | None = None
            if frame_ir.substories:
                substory_data = []
                for sub_block in frame_ir.substories:
                    sub_data = self._materialise_substory(
                        state, sub_block, ctx, scene_id, depth=1,
                    )
                    substory_data.append(sub_data)

            fd = _snapshot_to_frame_data(
                snap, total_frames, scene_id, ctx,
                substories=substory_data,
            )
            frame_data_list.append(fd)

        self.last_snapshots = snapshots
        return frame_data_list

    def _materialise_substory(
        self,
        state: SceneState,
        substory: SubstoryBlock,
        ctx: RenderContext,
        scene_id: str,
        depth: int,
    ) -> SubstoryData:
        """Materialise a substory block into SubstoryData."""
        # Instantiate substory-local primitives
        sub_primitives: dict[str, Any] | None = None
        if substory.shapes:
            bindings: dict[str, Any] = {}
            sub_primitives = {}
            for shape in substory.shapes:
                sub_primitives[shape.name] = _instantiate_primitive(
                    shape, bindings,
                )

        sub_snapshots = state.apply_substory(
            substory, starlark_host=self._starlark_host,
        )
        sub_total = len(sub_snapshots)
        sub_frames: list[FrameData] = []
        for i, sub_snap in enumerate(sub_snapshots):
            # Check for nested substories in substory frames
            nested_data: list[SubstoryData] | None = None
            if i < len(substory.frames) and substory.frames[i].substories:
                nested_data = []
                for nested_block in substory.frames[i].substories:
                    nd = self._materialise_substory(
                        state, nested_block, ctx, scene_id, depth=depth + 1,
                    )
                    nested_data.append(nd)

            fd = _snapshot_to_frame_data(
                sub_snap, sub_total, scene_id, ctx,
                substories=nested_data,
            )
            sub_frames.append(fd)

        return SubstoryData(
            title=substory.title,
            substory_id=substory.substory_id or f"substory{depth}",
            depth=depth,
            frames=sub_frames,
            primitives=sub_primitives,
        )


# ============================================================================
# DiagramRenderer — static single-frame figures
# ============================================================================

_DIAGRAM_ENV_BEGIN_RE = re.compile(
    r"\\begin\{diagram\}(\[[^\]]*\])?\s*\n?",
)
_DIAGRAM_ENV_END_RE = re.compile(
    r"\s*\\end\{diagram\}\s*$",
)


class DiagramRenderer:
    """Renderer for ``\\begin{diagram}...\\end{diagram}`` environments.

    Produces a static ``<figure class="scriba-diagram">`` with a single SVG.
    Reuses the same parser, primitives, and emitter as AnimationRenderer.

    Key differences:
    - ``\\step`` is forbidden (E1050)
    - ``\\narrate`` is forbidden (E1054)
    - ``\\highlight`` is persistent (not ephemeral)
    - Output is a static figure with no controls
    """

    name = "diagram"
    version = 1
    priority = 10

    def __init__(self, *, starlark_host: Any | None = None) -> None:
        self._starlark_host = starlark_host

    def detect(self, source: str) -> list[Block]:
        from scriba.animation.detector import detect_diagram_blocks

        return detect_diagram_blocks(source)

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
        raw = block.raw
        begin_m = _DIAGRAM_ENV_BEGIN_RE.match(raw)
        opts_str = begin_m.group(1) or "" if begin_m else ""
        body_start = begin_m.end() if begin_m else 0
        end_m = _DIAGRAM_ENV_END_RE.search(raw, body_start)
        body_end = end_m.start() if end_m else len(raw)
        body = raw[body_start:body_end]

        # Validate: no \narrate in diagram (check before parsing to avoid
        # the parser raising E1056 for narrate-outside-step)
        if re.search(r"\\narrate\b", body):
            raise ValidationError(
                "\\narrate is not allowed in diagram",
                code="E1054",
            )

        parse_input = opts_str + "\n" + body if opts_str else body
        ir = SceneParser().parse(
            parse_input, allow_highlight_in_prelude=True,
        )

        # Validate: no \step in diagram
        if ir.frames:
            raise ValidationError(
                "\\step is not allowed in diagram",
                code="E1050",
            )

        scene_id = scene_id_from_source(raw)
        if hasattr(ir, "options") and hasattr(ir.options, "id") and ir.options.id:
            scene_id = ir.options.id

        # Instantiate primitives
        primitives = AnimationRenderer._instantiate_primitives(
            self, ir
        )

        # Apply all prelude commands as a single frame
        state = SceneState()
        state.apply_prelude(
            shapes=ir.shapes,
            prelude_commands=ir.prelude_commands,
            prelude_compute=getattr(ir, "prelude_compute", []),
            starlark_host=self._starlark_host,
        )
        snap = state.snapshot(index=1, narration=None)

        frame = _snapshot_to_frame_data(snap, 1, scene_id, ctx)
        minify = ctx.metadata.get("minify", True)
        html = emit_html(
            scene_id, [frame], primitives, mode="diagram",
            render_inline_tex=ctx.render_inline_tex,
            minify=minify,
        )

        return RenderArtifact(
            html=html,
            css_assets=frozenset({"scriba-animation.css", "scriba-scene-primitives.css"}),
            js_assets=frozenset(),
            block_id=scene_id,
            data={},
        )

    def assets(self) -> RendererAssets:
        static = files("scriba.animation").joinpath("static")
        css_files: set[Path] = set()
        for name in ("scriba-animation.css", "scriba-scene-primitives.css"):
            css_files.add(Path(str(static / name)))
        return RendererAssets(
            css_files=frozenset(css_files),
            js_files=frozenset(),
        )
