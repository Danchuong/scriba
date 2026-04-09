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
from scriba.animation.emitter import FrameData, emit_animation_html
from scriba.animation.errors import FrameCountError
from scriba.animation.extensions.hl_macro import process_hl_macros
from scriba.animation.extensions.keyframes import generate_keyframe_styles
from scriba.animation.parser.ast import AnimationIR, ShapeCommand
from scriba.animation.parser.grammar import SceneParser
from scriba.animation.primitives import ArrayPrimitive, DPTablePrimitive, Graph
from scriba.animation.scene import FrameSnapshot, SceneState
from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.errors import RendererError, ValidationError

__all__ = ["AnimationRenderer"]

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
            f"[E1102] unknown primitive type {shape.type_name!r}",
        )
    resolved_params = _resolve_params(shape.params, bindings)

    if shape.type_name == "Graph":
        return factory_cls(shape.name, resolved_params)

    factory = factory_cls()
    return factory.declare(shape.name, resolved_params)


def _snapshot_to_frame_data(
    snap: FrameSnapshot,
    total_frames: int,
    scene_id: str,
    ctx: RenderContext,
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
            shape_states[shape_name][target_key] = entry

    annotations = [
        {
            "target": a.target,
            "label": a.text,
            "ephemeral": a.ephemeral,
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

        # Run the scene state machine
        snapshots = self._materialise(ir)

        frame_count = len(snapshots)
        if frame_count > _FRAME_ERROR_THRESHOLD:
            raise FrameCountError(frame_count)
        if frame_count > _FRAME_WARN_THRESHOLD:
            logger.warning(
                "animation %s has %d frames (>%d); consider splitting",
                scene_id,
                frame_count,
                _FRAME_WARN_THRESHOLD,
            )

        # Build FrameData list for the emitter
        frames = [
            _snapshot_to_frame_data(snap, frame_count, scene_id, ctx)
            for snap in snapshots
        ]

        # Produce final HTML via the real emitter
        html = emit_animation_html(scene_id, frames, primitives)

        # Collect CSS assets
        css_assets: set[str] = {
            "scriba-animation.css",
            "scriba-scene-primitives.css",
        }

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
        for name in ("scriba-animation.css", "scriba-scene-primitives.css"):
            css_files.add(Path(str(static / name)))
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

    def _materialise(self, ir: AnimationIR) -> list[FrameSnapshot]:
        """Run the delta state machine and collect per-frame snapshots."""
        state = SceneState()
        state.apply_prelude(
            shapes=ir.shapes,
            prelude_commands=ir.prelude_commands,
            prelude_compute=ir.prelude_compute,
            starlark_host=self._starlark_host,
        )

        snapshots: list[FrameSnapshot] = []
        for frame in ir.frames:
            snap = state.apply_frame(frame, starlark_host=self._starlark_host)
            snapshots.append(snap)

        return snapshots
