"""Reverse & jump tweening + delta-emphasis — runtime wiring pins.

Source-inspection contract (the runtime has no JS test rig), asserted
against BOTH the canonical asset ``static/scriba.js`` AND the inline
``<script>`` emitted by ``_build_inline_script``. The inline runtime is a
verbatim slice of the asset, so pinning both proves the derivation carries
the feature (same anti-drift discipline as ``test_runtime_unified``).

Covers the animation-clarity Tier-1/2 runtime wiring:

- ① reverse step: ``_invertManifest``/``_INV_KIND`` + a Prev/ArrowLeft tween
  path in ``show`` that feeds the *inverse* of ``frames[cur].tr``;
- forward dead-wiring fixes: the ``annotation_recolor`` handler branch and
  the ``-position-`` key-schism fallback (``_annEl``) for pill annotations;
- ② delta-emphasis: ``_emphasize`` — capped, reduced-motion-gated, opt-out;
- ③ cursor slide: the ``cursor_move`` handler (ends at the *new* seat);
- the ``value_change`` null-guard so an inverted ``from=null`` record never
  stamps the literal ``"null"`` into a cell (pulse only).
"""

from __future__ import annotations

import re
from importlib.resources import files

import pytest

from scriba.animation._script_builder import _build_inline_script

_ASSET = (files("scriba.animation") / "static" / "scriba.js").read_text("utf-8")
_INLINE = _build_inline_script("pin-scene", "[]")

_SOURCES = {"asset": _ASSET, "inline_emitted": _INLINE}


def _fn(src: str, name: str) -> str:
    """Return the full source of ``function name(...)`` by brace-matching."""
    start = src.find(f"function {name}(")
    assert start != -1, f"function {name} not found"
    i = src.find("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[start : j + 1]
    raise AssertionError(f"unbalanced braces in {name}")


# ---------------------------------------------------------------------------
# ① reverse — the inverse manifest helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestInverseManifest:
    def test_invert_helpers_exist(self, src: str) -> None:
        assert "function _invertRec(" in src
        assert "function _invertManifest(" in src

    def test_invert_rec_swaps_from_to(self, src: str) -> None:
        # r = [target, prop, from, to, kind] -> [target, prop, to, from, inv]
        body = _fn(src, "_invertRec")
        assert "r[3],r[2]" in body, (
            "the inverse must swap from/to (r[3] before r[2]); got: " + body
        )
        assert "_INV_KIND[r[4]]||r[4]" in body, (
            "self-inverse kinds must fall back to the same kind"
        )

    def test_inv_kind_maps_appear_disappear_pairs(self, src: str) -> None:
        # the six kinds whose inverse is a *different* kind
        for a, b in [
            ("annotation_add", "annotation_remove"),
            ("annotation_remove", "annotation_add"),
            ("element_add", "element_remove"),
            ("element_remove", "element_add"),
            ("highlight_on", "highlight_off"),
            ("highlight_off", "highlight_on"),
        ]:
            assert f"{a}:'{b}'" in src, f"_INV_KIND must map {a} -> {b}"

    def test_inv_kind_omits_self_inverse_kinds(self, src: str) -> None:
        # recolor / value_change / position_move / annotation_recolor /
        # cursor_move are self-inverse under from/to swap — they must NOT be
        # remapped to another kind, they ride the ||r[4] fallback.
        m = re.search(r"_INV_KIND=\{([^}]*)\}", src)
        assert m, "_INV_KIND object literal not found"
        table = m.group(1)
        for k in ("recolor:", "value_change:", "position_move:",
                  "annotation_recolor:", "cursor_move:"):
            assert k not in table, (
                f"{k} is self-inverse and must not be in _INV_KIND"
            )


# ---------------------------------------------------------------------------
# ① reverse — show() directional routing + control wiring
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestShowRouting:
    def test_show_computes_signed_delta(self, src: str) -> None:
        assert "var d=i-cur" in _fn(src, "show")

    def test_forward_step_tweens_frames_tr(self, src: str) -> None:
        body = _fn(src, "show")
        assert "d===1" in body
        assert "animateTransition(i,frames[i].tr,frames[i].fs)" in body

    def test_reverse_step_tweens_inverted_manifest(self, src: str) -> None:
        body = _fn(src, "show")
        assert "d===-1" in body
        assert (
            "animateTransition(i,_invertManifest(frames[cur].tr),frames[cur].fs)"
            in body
        ), "Prev must feed the INVERSE of frames[cur].tr with the source fs"

    def test_jump_snaps_and_emphasizes(self, src: str) -> None:
        body = _fn(src, "show")
        assert "Math.abs(d)>1" in body
        assert "snapToFrame(i)" in body
        assert "_emphasize(_changedTargets(" in body, (
            "a >1-step jump must snap then pulse the union of changed targets"
        )

    def test_prev_click_animates(self, src: str) -> None:
        assert re.search(r"prev\.addEventListener\([^;]*show\(cur-1,true\)", src), (
            "the Prev button must route through show(cur-1,true) so it tweens"
        )

    def test_arrowleft_animates(self, src: str) -> None:
        assert re.search(r"ArrowLeft[^}]*show\(cur-1,true\)", src, re.S), (
            "ArrowLeft must animate backward, mirroring ArrowRight"
        )


# ---------------------------------------------------------------------------
# animateTransition generalized to (toIdx, manifest, fsFlag)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestAnimateTransitionSignature:
    def test_takes_manifest_and_fs_params(self, src: str) -> None:
        assert "function animateTransition(toIdx,manifest,fsFlag)" in src

    def test_reads_manifest_not_hardwired_tr(self, src: str) -> None:
        body = _fn(src, "animateTransition")
        assert "var tr=manifest;" in body, (
            "the manifest must come from the caller (forward OR inverse), "
            "not frames[toIdx].tr literally"
        )
        assert "var needsSync=!!fsFlag;" in body

    def test_finish_pulses_arrival(self, src: str) -> None:
        body = _fn(src, "animateTransition")
        assert "_emphasize(_manifestTargets(tr))" in body, (
            "after a tween settles, the changed identities get a delta-pulse"
        )


# ---------------------------------------------------------------------------
# forward dead-wiring: annotation_recolor + cursor_move + null-guard + fallback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestApplyTransitionBranches:
    def test_annotation_recolor_branch(self, src: str) -> None:
        body = _fn(src, "_applyTransition")
        assert "kind==='annotation_recolor'" in body
        # mirrors recolor but on the annotation group; colors are sanitized
        # (":" -> "-") exactly like Python's annotation_color_class.
        assert "scriba-annotation-" in body
        assert "replace(/:/g,'-')" in body

    def test_cursor_move_branch(self, src: str) -> None:
        body = _fn(src, "_applyTransition")
        assert "kind==='cursor_move'" in body
        # the caret ends at the NEW seat: translate(0,0) -> translate(delta)
        assert "translate(0,0)" in body

    def test_position_move_glides_to_new_seat(self, src: str) -> None:
        # v0.24.0: position_move now shares cursor_move's geometry — the tween
        # ENDS at the new seat so the fs-snap only reaffirms (no A-4 lurch).
        body = _fn(src, "_applyTransition")
        start = body.find("kind==='position_move'")
        assert start != -1, "position_move branch not found"
        branch = body[start:body.find("kind===", start + 1)]
        # delta is to-from (pt - pf), mirroring cursor_move's ct - cf
        assert "parseFloat(pt[0])-parseFloat(pf[0])" in branch
        assert "parseFloat(pt[1])-parseFloat(pf[1])" in branch
        # keyframes START at translate(0,0) (old seat) and END at
        # translate(delta) (new seat) — not the reverse (ends-at-old lurch)
        i0 = branch.find("translate(0,0)")
        idelta = branch.find("translate('+dx+'px,'+dy+'px)")
        assert 0 <= i0 < idelta, (
            "position_move must glide to the NEW seat: translate(0,0) first, "
            "translate(to-from) last (cures the A-4 ends-at-old lurch)"
        )

    def test_value_change_null_guard(self, src: str) -> None:
        body = _fn(src, "_applyTransition")
        assert "toVal!=null" in body, (
            "inverting value_change from=null yields to=null; guard the text "
            "write so it pulses only and never stamps the literal 'null'"
        )

    def test_key_schism_fallback(self, src: str) -> None:
        # differ composites a position-only pill as {base}-solo, but the SVG
        # keys it {base}-position-{above|below|left|right}. _annEl bridges it.
        assert "function _annEl(" in src
        body = _fn(src, "_annEl")
        assert "-position-" in body
        for side in ("above", "below", "left", "right"):
            assert f"'{side}'" in body, f"fallback must try the {side} side"

    def test_annotation_handlers_use_fallback(self, src: str) -> None:
        body = _fn(src, "_applyTransition")
        assert "_annEl(stage,target)" in body  # remove + recolor
        assert "_annEl(parsed,target)" in body  # add clones from destination


# ---------------------------------------------------------------------------
# ② delta-emphasis
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestEmphasis:
    def test_emphasize_exists(self, src: str) -> None:
        assert "function _emphasize(" in src

    def test_reduced_motion_and_opt_out_gated(self, src: str) -> None:
        body = _fn(src, "_emphasize")
        assert "_canAnim" in body, "reduced-motion must suppress emphasis"
        assert "data-scriba-no-emphasis" in body, "per-widget opt-out attr"

    def test_capped_at_eight(self, src: str) -> None:
        assert re.search(r"EMPH_CAP\s*=\s*8", src), "cap constant must be 8"
        assert "EMPH_CAP" in _fn(src, "_emphasize")

    def test_toggles_emphasis_class(self, src: str) -> None:
        body = _fn(src, "_emphasize")
        assert "scriba-emphasis" in body
        assert "classList.add('scriba-emphasis')" in body
        assert "classList.remove('scriba-emphasis')" in body

    def test_removal_is_generation_guarded(self, src: str) -> None:
        body = _fn(src, "_emphasize")
        assert "myGen=_gen" in body and "myGen!==_gen" in body, (
            "a superseding nav must orphan the pending class-removal"
        )


# ---------------------------------------------------------------------------
# anti-drift: the new functions are byte-identical asset == inline (R10)
# ---------------------------------------------------------------------------


class TestByteIdentical:
    @pytest.mark.parametrize(
        "name",
        [
            "show",
            "animateTransition",
            "_applyTransition",
            "_invertRec",
            "_invertManifest",
            "_manifestTargets",
            "_changedTargets",
            "_emphasize",
            "_annEl",
        ],
    )
    def test_core_fn_is_byte_identical(self, name: str) -> None:
        assert _fn(_ASSET, name) == _fn(_INLINE, name), (
            f"{name} drifted between the asset and its inline slice — the "
            "inline runtime must be DERIVED from scriba.js, never authored"
        )

    def test_inv_kind_table_is_byte_identical(self) -> None:
        pat = re.compile(r"var _INV_KIND=\{[^}]*\}")
        assert pat.search(_ASSET).group(0) == pat.search(_INLINE).group(0)
