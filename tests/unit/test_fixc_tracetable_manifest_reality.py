"""Fix C — F3: pin the ACTUAL TraceTable append behaviour in the real pipeline.

investigations/hunt-runtime-static.md (F3) claimed TraceTable row-appends emit
"zero manifest records", contradicting docs SCRIBA-TEX-REFERENCE.md s7.20 which
promised "the append rides the shipped element_add transition (the new row fades
in) and the current->idle advance rides recolor".

Arbitration (verified by rendering, see the module tests below): NO accumulation
primitive animates per-element. A ``\\apply{t}{row=[...]}`` lands
``apply_params`` on the BARE shape target ``t`` (exactly like ``\\apply{s}{push
=v}`` on a Stack), and the bare target persists across frames, so the differ's
``element_add`` (which keys on a target *newly appearing*) fires at most once
(empty -> first element) and never for subsequent appends. The row is delivered
by a full frame snap (``tr:null`` -> ``snapToFrame`` innerHTML swap), byte-for-
byte identical to how Stack / Queue / LinkedList deliver their growth.

The honest fix is therefore documentation: s7.20 and the primitive docstring now
describe the frame-snap reality. This test PINS that reality so a future change
that silently reintroduces the false "each append animates" promise is caught,
and demonstrates TraceTable is consistent with Stack.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scriba.animation.detector import detect_animation_blocks  # noqa: E402
from scriba.animation.renderer import AnimationRenderer  # noqa: E402
from scriba.animation.starlark_host import StarlarkHost  # noqa: E402
from scriba.core.context import RenderContext  # noqa: E402
from scriba.core.workers import SubprocessWorkerPool  # noqa: E402
from scriba.tex.renderer import TexRenderer  # noqa: E402

_TT = (
    '\\begin{animation}[id="tt", label="trace"]\n'
    "\\shape{t}{TraceTable}{columns=[i, sum]}\n"
    "\\step\n\\apply{t}{row=[0, 3]}\n\\narrate{Row 0.}\n"
    "\\step\n\\apply{t}{row=[1, 4]}\n\\narrate{Row 1.}\n"
    "\\step\n\\apply{t}{row=[2, 8]}\n\\narrate{Row 2.}\n"
    "\\end{animation}\n"
)

_STACK = (
    '\\begin{animation}[id="st", label="stack"]\n'
    "\\shape{s}{Stack}{items=[]}\n"
    "\\step\n\\apply{s}{push=3}\n\\narrate{Push 3.}\n"
    "\\step\n\\apply{s}{push=4}\n\\narrate{Push 4.}\n"
    "\\step\n\\apply{s}{push=8}\n\\narrate{Push 8.}\n"
    "\\end{animation}\n"
)


def _manifests(source: str) -> list[str]:
    """Return the per-frame ``tr:`` payload strings from the inline runtime."""
    wp = SubprocessWorkerPool()
    sh = StarlarkHost(wp)
    tr = TexRenderer(worker_pool=wp, enable_copy_buttons=False)
    ctx = RenderContext(
        resource_resolver=lambda n: f"/static/{n}",
        theme="light",
        metadata={"output_mode": "interactive", "minify": False},
        render_inline_tex=lambda t: tr.render_inline_text(t),
    )
    try:
        renderer = AnimationRenderer(starlark_host=sh)
        art = renderer.render_block(detect_animation_blocks(source)[0], ctx)
    finally:
        sh.close()
        wp.close()
    return [m.group(1) for m in re.finditer(r",tr:(\[.*?\]|null),fs:\d", art.html, re.S)]


def test_tracetable_appends_hard_snap_no_per_row_record() -> None:
    trs = _manifests(_TT)
    assert len(trs) == 3, trs
    # No frame emits an animated transition — every append hard-snaps.
    assert trs == ["null", "null", "null"], trs
    # Specifically: no per-row element_add / recolor is fabricated.
    for payload in trs:
        assert "element_add" not in payload
        assert "recolor" not in payload


def test_tracetable_matches_stack_snap_behaviour() -> None:
    """TraceTable's append manifest is identical in shape to Stack's push
    manifest — both accumulation surfaces deliver growth by frame snap."""
    assert _manifests(_TT) == _manifests(_STACK) == ["null", "null", "null"]
