"""SVG emitter and HTML stitcher — Wave 3 final rendering stage.

Takes per-frame data and primitive instances, produces either an
interactive widget (default) or a static filmstrip HTML output.

The emitter is stateless and safe for concurrent use.

Wave E3: split into two sub-modules:
  - ``_frame_renderer`` — SVG-per-frame rendering
  - ``_html_stitcher``  — HTML stitching (interactive, filmstrip, diagram)
This module re-exports everything so all existing import paths continue to work.
"""

from __future__ import annotations

import hashlib
import re as _re

from scriba.animation.parser._idents import is_ident as _is_ident
from dataclasses import dataclass
from typing import Any

from scriba.animation._frame_renderer import *  # noqa: F401, F403
from scriba.animation._frame_renderer import (
    _validate_expanded_selectors as _validate_expanded_selectors,
    compute_viewbox,
    emit_shared_defs,
)
from scriba.animation._html_stitcher import *  # noqa: F401, F403
from scriba.animation._html_stitcher import (
    _escape_js as _escape_js,
    emit_animation_html,
    emit_html,
    emit_interactive_html,
    emit_substory_html,
)
from scriba.animation._minify import *  # noqa: F401, F403
from scriba.animation._script_builder import *  # noqa: F401, F403
from scriba.core.errors import ValidationError

__all__ = [
    "FrameData",
    "SubstoryData",
    "compute_viewbox",
    "emit_animation_html",
    "emit_html",
    "emit_interactive_html",
    "emit_shared_defs",
    "emit_substory_html",
    "scene_id_from_source",
    "validate_frame_labels_unique",
]

# Regex for a label that is safe to embed in an HTML id token. The
# parser (``grammar._try_parse_step_options``) already enforces this
# shape for ``\\step[label=...]`` values, but the emitter double-checks
# before using a label as a frame identifier so that programmatically
# constructed ``FrameData`` instances with free-form labels (used by
# older tests that repurposed ``FrameData.label`` as an aria-label
# string) fall back gracefully to the index-based ``frame-N`` id.
#
# The leading class is Unicode-aware (``[^\W\d]`` — a Unicode letter or
# underscore, never a digit), mirroring the parser's ``isidentifier()``
# gate. Unicode letters are valid XML ``NameStartChar`` and valid HTML id
# chars, so a non-ASCII label (e.g. Vietnamese ``đáp``) is a usable anchor
# rather than being silently downgraded to ``frame-N`` (SCRIBA-TEX-REFERENCE
# §5.3). Spaces / punctuation outside ``._-`` remain unsafe.
class _LabelIdMatcher:
    """Regex-shaped facade over the shared XID matcher (extra chars ``.-``).

    Python's \\w excludes combining marks, so the previous
    ``^[^\\W\\d][\\w.-]*$`` regex downgraded Thai/Devanagari \\step labels
    to the frame-N fallback while accepting precomposed Vietnamese.
    """

    @staticmethod
    def match(text: str):
        return _is_ident(text, extra=".-") or None


_LABEL_ID_RE = _LabelIdMatcher()

# ---------------------------------------------------------------------------
# Layout constants (kept here for direct backward-compat; also live in
# _frame_renderer where they are actually used)
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# FrameData
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SubstoryData:
    """Nested substory rendering data."""

    title: str
    substory_id: str
    depth: int
    frames: list["FrameData"]
    primitives: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class FrameData:
    """Per-frame rendering data consumed by the emitter."""

    step_number: int
    total_frames: int
    narration_html: str  # already rendered (KaTeX or escaped)
    shape_states: dict[str, dict[str, dict]]  # shape_name -> target -> state
    annotations: list[dict]  # annotation data
    traces: list[dict] | None = None  # \trace decorations (R-37)
    ref_marks: list[str] | None = None  # \ref'd targets to ring (R-39 v1.1)
    cursors: list[dict] | None = None  # \cursor binding carets (R-38)
    label: str | None = None
    substories: list[SubstoryData] | None = None
    title: str | None = None  # \step[title="..."] caption (§5.3)
    focus: tuple[str, ...] = ()  # \focus{sel} spotlight targets (R-40)
    focus_scope: str = "shape"  # \focus scope: "shape" (default) | "board"
    links: list[dict] | None = None  # \link / \combine cross-shape bridges (§4)
    groups: list[dict] | None = None  # \group overlay hulls on a Graph (§6 Ph1)
    notes: list[dict] | None = None  # \note free stage-level callouts (DECORATE)
    zoom_target: str | None = None  # \zoom{sel} per-frame camera crop (Viewport)


# ---------------------------------------------------------------------------
# Scene ID helper
# ---------------------------------------------------------------------------


def scene_id_from_source(source: str, *, position: int = 0) -> str:
    """Deterministic scene ID: ``scriba-`` + first 10 hex of SHA-256.

    Including *position* (byte offset in the document) ensures two blocks
    with identical content at different locations produce distinct IDs.
    """
    key = f"{position}:{source}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:10]
    return f"scriba-{digest}"


# ---------------------------------------------------------------------------
# Frame ID + label helpers
# ---------------------------------------------------------------------------


def _is_id_safe_label(label: str | None) -> bool:
    """Return True when *label* can be embedded in an HTML id attribute.

    Parser-produced labels from ``\\step[label=...]`` always satisfy
    this; the check exists so that programmatically constructed
    ``FrameData`` with free-form aria-label text (legacy usage) do not
    inadvertently produce broken ids.
    """
    if not label:
        return False
    return _LABEL_ID_RE.match(label) is not None


def _frame_id(scene_id: str, frame: FrameData) -> str:
    """Return the frame id token.

    Labeled frames resolve to ``{scene_id}-{label}``; unlabeled (or
    unsafe-labeled) frames fall back to ``{scene_id}-frame-{step}``.
    The namespace includes ``scene_id`` so that two scenes in the same
    document cannot collide on the same label.
    """
    if _is_id_safe_label(frame.label):
        return f"{scene_id}-{frame.label}"
    return f"{scene_id}-frame-{frame.step_number}"


def validate_frame_labels_unique(frames: list[FrameData]) -> None:
    """Raise ``ValidationError`` E1005 if two frames share the same label.

    Only identifier-safe labels participate in the uniqueness check —
    non-id-safe labels never become frame ids so a duplicate amongst
    them is harmless.  The error message names both offending frames by
    ``step_number`` so the user can locate them even though the emitter
    does not have direct access to source line numbers.
    """
    seen: dict[str, int] = {}
    for frame in frames:
        label = frame.label
        if not _is_id_safe_label(label):
            continue
        assert label is not None  # narrowed by _is_id_safe_label
        if label in seen:
            first_step = seen[label]
            raise ValidationError(
                f"duplicate \\step label {label!r}: "
                f"first used at step {first_step}, "
                f"reused at step {frame.step_number}",
                code="E1005",
            )
        seen[label] = frame.step_number


# ---------------------------------------------------------------------------
# Tree position injection
# ---------------------------------------------------------------------------


def _inject_tree_positions(frame: FrameData, primitives: dict[str, Any]) -> None:
    """Copy node ``(x, y)`` positions from Tree primitives into *frame.shape_states*.

    Called after ``_emit_frame_svg`` so that ``apply_command`` mutations
    (reparent, add_node, etc.) have already updated ``Tree.positions``.
    The differ then compares positions between consecutive frames and
    emits ``position_move`` transitions for smooth animation.
    """
    for shape_name, prim in primitives.items():
        if not hasattr(prim, "get_node_positions"):
            continue
        node_positions = prim.get_node_positions()
        if not node_positions:
            continue
        shape_dict = frame.shape_states.get(shape_name)
        if shape_dict is None:
            shape_dict = {}
            frame.shape_states[shape_name] = shape_dict
        for target, (x, y) in node_positions.items():
            entry = shape_dict.get(target)
            if entry is None:
                # Node exists in the tree but has no state changes this
                # frame — create a minimal entry with position only.
                shape_dict[target] = {"state": "idle", "x": x, "y": y}
            else:
                entry["x"] = x
                entry["y"] = y
