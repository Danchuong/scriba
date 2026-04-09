"""AnimationRenderer — Renderer protocol implementation for animation blocks.

Wires detection, parsing, scene materialisation, and HTML emission into the
:class:`Renderer` protocol defined in :mod:`scriba.core.renderer`.
"""

from __future__ import annotations

import hashlib
import html as _html
import logging
from importlib.resources import files
from pathlib import Path
from typing import Any

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.errors import FrameCountError
from scriba.animation.parser.ast import AnimationIR, FrameIR
from scriba.animation.scene import FrameSnapshot, SceneState
from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.errors import RendererError

__all__ = ["AnimationRenderer"]

logger = logging.getLogger(__name__)

_FRAME_WARN_THRESHOLD = 30
_FRAME_ERROR_THRESHOLD = 100


def _scene_id(raw: str) -> str:
    """Deterministic scene ID from block source."""
    digest = hashlib.sha256(raw.encode()).hexdigest()[:10]
    return f"scriba-{digest}"


def _escape_narration(
    text: str | None,
    ctx: RenderContext,
) -> str:
    """Render narration text: pass through ctx.render_inline_tex or escape."""
    if text is None:
        return ""
    if ctx.render_inline_tex is not None:
        return ctx.render_inline_tex(text)
    return _html.escape(text, quote=False)


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

        scene_id = ir.id_option or _scene_id(block.raw)
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

        html = self._emit_html(scene_id, snapshots, ctx)

        return RenderArtifact(
            html=html,
            css_assets=frozenset({"scriba-animation.css"}),
            js_assets=frozenset(),
            block_id=scene_id,
            data={"frame_count": frame_count},
        )

    def assets(self) -> RendererAssets:
        """Return the always-on CSS file for animation blocks."""
        static = files("scriba.animation").joinpath("static")
        css_path = Path(str(static / "scriba-animation.css"))
        return RendererAssets(
            css_files=frozenset({css_path}),
            js_files=frozenset(),
        )

    # ---- private ----

    def _parse(self, block: Block) -> AnimationIR:
        """Parse a block into AnimationIR.

        Attempts to use SceneParser from the parser sub-package.  If it
        is not yet implemented (Wave 1 stub), falls back to a minimal
        inline parser that extracts frames separated by ``\\step``.
        """
        try:
            from scriba.animation.parser.grammar import SceneParser

            return SceneParser().parse(block.raw)
        except (ImportError, NotImplementedError):
            return self._fallback_parse(block.raw)

    def _fallback_parse(self, raw: str) -> AnimationIR:
        """Minimal fallback parser when the full grammar is unavailable.

        Splits on ``\\step`` and extracts narration from free text.
        """
        import re

        # Strip \begin{animation}[...] and \end{animation}
        body_match = re.search(
            r"\\begin\{animation\}(?:\[[^\]]*\])?\s*\n?(.*?)\\end\{animation\}",
            raw,
            re.DOTALL,
        )
        if body_match is None:
            return AnimationIR()

        body = body_match.group(1)

        # Extract options
        opt_match = re.search(
            r"\\begin\{animation\}\[([^\]]*)\]",
            raw,
        )
        options: tuple[Any, ...] = ()
        if opt_match:
            from scriba.animation.parser.ast import Option

            raw_opts = opt_match.group(1)
            opts = []
            for pair in raw_opts.split(","):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    v = v.strip().strip('"').strip("'")
                    opts.append(Option(key=k.strip(), value=v))
            options = tuple(opts)

        # Split on \step to get frames
        parts = re.split(r"\\step\b", body)

        # First part is prelude (before first \step)
        prelude_text = parts[0].strip() if parts else ""

        frames: list[FrameIR] = []
        frame_parts = parts[1:] if len(parts) > 1 else []

        for i, part in enumerate(frame_parts):
            narration = part.strip() if part.strip() else None
            frames.append(
                FrameIR(
                    index=i + 1,
                    commands=(),
                    narration=narration,
                    compute_blocks=(),
                )
            )

        # If no \step found, treat entire body as one frame
        if not frames and body.strip():
            frames.append(
                FrameIR(
                    index=1,
                    commands=(),
                    narration=body.strip() if body.strip() else None,
                    compute_blocks=(),
                )
            )

        return AnimationIR(
            options=options,
            frames=tuple(frames),
        )

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

    def _emit_html(
        self,
        scene_id: str,
        snapshots: list[FrameSnapshot],
        ctx: RenderContext,
    ) -> str:
        """Emit the HTML skeleton per 04-environments-spec.md section 8.1."""
        frame_count = len(snapshots)

        frame_items: list[str] = []
        for snap in snapshots:
            narration_html = _escape_narration(snap.narration, ctx)
            narration_block = (
                f'      <p class="scriba-narration">{narration_html}</p>'
                if narration_html
                else '      <p class="scriba-narration"></p>'
            )
            frame_items.append(
                f'    <li class="scriba-frame" '
                f'id="{scene_id}-frame-{snap.index}" '
                f'data-step="{snap.index}">\n'
                f'      <header class="scriba-frame-header">\n'
                f'        <span class="scriba-step-label">'
                f"Step {snap.index} / {frame_count}</span>\n"
                f"      </header>\n"
                f'      <div class="scriba-stage">\n'
                f"        <!-- SVG placeholder -->\n"
                f"      </div>\n"
                f"{narration_block}\n"
                f"    </li>"
            )

        frames_html = "\n".join(frame_items)

        return (
            f'<figure class="scriba-animation" '
            f'data-scriba-scene="{scene_id}" '
            f'data-frame-count="{frame_count}">\n'
            f'  <ol class="scriba-frames">\n'
            f"{frames_html}\n"
            f"  </ol>\n"
            f"</figure>"
        )
