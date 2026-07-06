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
        # A-9: the single-step arrival pulse now excludes self-announcing kinds,
        # so it feeds _pulseTargets (identity-filtered), not the old unfiltered
        # _manifestTargets. See TestSelfAnnounceExclusion for the semantics.
        assert "_emphasize(_pulseTargets(tr))" in body, (
            "after a tween settles, the changed identities that did NOT already "
            "self-announce get a delta-pulse"
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
            "_pulseTargets",
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

    def test_self_announcing_table_is_byte_identical(self) -> None:
        pat = re.compile(r"var _SELF_ANNOUNCING=\{[^}]*\}")
        assert pat.search(_ASSET).group(0) == pat.search(_INLINE).group(0)


# ---------------------------------------------------------------------------
# A-9 — delta-emphasis excludes self-announcing motion kinds
# ---------------------------------------------------------------------------
#
# On the animated SINGLE-STEP path the pulse must fire only on identities that
# did NOT already self-announce via their own handler motion (a glided caret
# that then scale-throbs reads as a jolt). Exclusion is by IDENTITY, collected
# across ALL records of the step, so a target that glided AND recolored is
# excluded whole. The multi-step JUMP path is exempt (a snap plays no per-kind
# motion, so the pulse is the sole arrival signal) and is left unchanged.

# The 7 kinds whose single-step handler already plays a per-element transform /
# draw-on / opacity — the element self-announces.
_SELF_ANNOUNCING_KINDS = (
    "value_change", "element_add", "element_remove", "position_move",
    "annotation_add", "annotation_remove", "cursor_move",
)
# The 4 silent kinds — instant class swaps the eye can miss; the pulse is the
# real "this changed" signal, so they KEEP it.
_SILENT_KINDS = ("recolor", "highlight_on", "highlight_off", "annotation_recolor")


@pytest.mark.parametrize("src", _SOURCES.values(), ids=list(_SOURCES))
class TestSelfAnnounceExclusion:
    def test_self_announcing_set_named(self, src: str) -> None:
        assert "var _SELF_ANNOUNCING={" in src, (
            "a named closed set is the single source of truth (mirrors _INV_KIND)"
        )

    def test_self_announcing_membership(self, src: str) -> None:
        # regex-extract the {…} literal (like test_inv_kind_omits_self_inverse_kinds)
        m = re.search(r"_SELF_ANNOUNCING=\{([^}]*)\}", src)
        assert m, "_SELF_ANNOUNCING object literal not found"
        table = m.group(1)
        for k in _SELF_ANNOUNCING_KINDS:
            assert f"{k}:" in table, (
                f"{k} self-announces via its handler — it must be excluded"
            )
        for k in _SILENT_KINDS:
            assert f"{k}:" not in table, (
                f"{k} is a silent instant swap — its pulse is the real signal, "
                "so it must NOT be in _SELF_ANNOUNCING (keeps the pulse)"
            )

    def test_pulse_targets_two_pass_by_identity(self, src: str) -> None:
        body = _fn(src, "_pulseTargets")
        # pass 1: any identity under ANY self-announcing kind (test the record's
        # KIND tr[i][4], mark the record's IDENTITY tr[i][0]).
        assert "_SELF_ANNOUNCING[tr[i][4]]" in body, (
            "pass 1 must test each record's KIND against the self-announcing set"
        )
        assert "glided[tr[i][0]]" in body, (
            "pass 1 must mark the record's IDENTITY as glided"
        )
        # pass 2: emit the changed identities NOT glided — exclusion is keyed on
        # identity, so a target that glided AND recolored is excluded whole (the
        # report's per-record `continue` would wrongly re-emit it via recolor).
        assert "glided[id]" in body, (
            "pass 2 must skip any identity collected in pass 1"
        )
        assert "out.push(id)" in body

    def test_finish_uses_pulse_targets(self, src: str) -> None:
        body = _fn(src, "animateTransition")
        assert "_emphasize(_pulseTargets(tr))" in body, (
            "the single-step arrival pulse must feed the identity-filtered set"
        )
        assert "_emphasize(_manifestTargets(tr))" not in body, (
            "the old unfiltered all-targets pulse must be gone"
        )

    def test_manifest_targets_removed(self, src: str) -> None:
        assert "function _manifestTargets(" not in src, (
            "_manifestTargets is orphaned by _pulseTargets — remove it, don't "
            "leave dead code the byte-lock would still green-light"
        )

    def test_jump_path_still_pulses_all_changed(self, src: str) -> None:
        # A >1-step jump snaps with NO per-kind motion, so the pulse is the sole
        # arrival signal — it stays the unfiltered _changedTargets union.
        body = _fn(src, "show")
        assert "_emphasize(_changedTargets(from,i))" in body, (
            "the jump path must remain unchanged (union, no kind filter)"
        )

    def test_reduced_motion_optout_still_gate(self, src: str) -> None:
        # A-8: the emphasis gates are untouched; only its argument narrowed.
        body = _fn(src, "_emphasize")
        assert "_canAnim" in body, "reduced-motion must still suppress emphasis"
        assert "data-scriba-no-emphasis" in body, "opt-out attr must still gate"

    def test_jump_path_excludes_faded_annotations(self, src: str) -> None:
        # A-9 jump clause: a jump snaps with no per-kind motion for cells /
        # nodes / carets, so their pulse is the sole arrival signal and is kept.
        # But snapToFrame still fades genuinely-new annotations in via
        # _fadeInNewAnnotations, so an added/removed annotation self-announces
        # through that fade — exclude it from the jump pulse (two-pass by
        # identity, mirroring _pulseTargets).
        body = _fn(src, "_changedTargets")
        assert "annotation_add" in body and "annotation_remove" in body, (
            "the jump union must skip the annotation kinds that fade on a snap"
        )
        assert "faded[" in body, (
            "jump exclusion must be keyed on identity across the span (two-pass)"
        )
        # element_add / cursor_move / value_change / position_move do NOT fade on
        # a jump (only [data-annotation] elements fade) — they must NOT be
        # excluded there, or a jumped-to new cell/moved caret shows nothing.
        for keep in ("element_add", "cursor_move", "value_change", "position_move"):
            assert keep not in body, (
                f"{keep} does not self-announce on a jump — it must stay in the "
                "jump union (the pulse is its only arrival cue)"
            )


# ---------------------------------------------------------------------------
# A-9 — behavioral oracle: the two-pass set computation
# ---------------------------------------------------------------------------
#
# A faithful Python port of scriba.js ``_pulseTargets`` / ``_changedTargets``,
# exercised on the real showcase manifest + synthetic cases. The
# source-inspection tests above pin the JS shape (so this port cannot silently
# drift from the runtime); this proves the SEMANTICS that shape produces.

_SELF_ANNOUNCING_SET = frozenset(_SELF_ANNOUNCING_KINDS)


def _pulse_targets(tr: list[list[str]]) -> list[str]:
    """Mirror of scriba.js ``_pulseTargets``: two-pass exclusion by identity."""
    glided = {rec[0] for rec in tr if rec[4] in _SELF_ANNOUNCING_SET}
    seen: set[str] = set()
    out: list[str] = []
    for rec in tr:
        ident = rec[0]
        if ident in glided or ident in seen:
            continue
        seen.add(ident)
        out.append(ident)
    return out


def _changed_targets(frames_tr: list[list[list[str]]]) -> list[str]:
    """Mirror of scriba.js ``_changedTargets``: union over the skipped frames,
    two-pass excluding ``annotation_add`` / ``annotation_remove`` (which
    self-announce via ``_fadeInNewAnnotations`` on the snap). Snap-silent kinds
    (cells / nodes / carets — recolor / value_change / position_move /
    cursor_move / element_*) are KEPT: a jump plays no motion for them, so the
    pulse is their sole arrival signal."""
    faded = {rec[0] for tr in frames_tr for rec in tr
             if rec[4] in ("annotation_add", "annotation_remove")}
    seen: set[str] = set()
    out: list[str] = []
    for tr in frames_tr:
        for rec in tr:
            if rec[0] in faded or rec[0] in seen:
                continue
            seen.add(rec[0])
            out.append(rec[0])
    return out


# The flagship showcase step, extracted verbatim from
# tests/golden/examples/corpus/anim_clarity_showcase.html.
_SHOWCASE_TR = [
    ["a.cell[2]", "state", "idle", "current", "recolor"],
    ["w.var[i]", "value", "0", "2", "value_change"],
    ["a.cursor[i]-solo", "position", "92.0,46.0", "216.0,46.0", "cursor_move"],
]


class TestPulseTargetsBehavior:
    def test_showcase_pulses_only_the_silent_recolor(self) -> None:
        # cursor_move (already glided) and value_change (already scale-bounced)
        # are dropped; the silent recolor cell keeps its pulse — the real signal.
        assert _pulse_targets(_SHOWCASE_TR) == ["a.cell[2]"]

    def test_cursor_move_absent_sibling_recolor_present(self) -> None:
        tr = [
            ["p", "state", "a", "b", "recolor"],
            ["q", "position", "0,0", "1,1", "cursor_move"],
        ]
        out = _pulse_targets(tr)
        assert "p" in out, "a silent recolor sibling must still pulse"
        assert "q" not in out, "a self-announcing caret glide must not pulse"

    def test_glided_and_recolored_identity_excluded_whole(self) -> None:
        # One identity carrying BOTH a self-announcing and a silent kind in the
        # same step is excluded (the eye tracked it through the glide). A
        # per-record skip would wrongly re-emit it via its recolor record; the
        # two-pass keyed on identity does not.
        tr = [
            ["x", "state", "a", "b", "recolor"],
            ["x", "position", "0,0", "1,1", "position_move"],
        ]
        assert _pulse_targets(tr) == []

    def test_all_silent_kinds_still_pulse(self) -> None:
        tr = [
            ["c1", "state", "a", "b", "recolor"],
            ["c2", "hl", "0", "1", "highlight_on"],
            ["c3", "hl", "1", "0", "highlight_off"],
            ["c4", "astate", "x", "y", "annotation_recolor"],
        ]
        assert _pulse_targets(tr) == ["c1", "c2", "c3", "c4"]

    def test_jump_keeps_snap_kinds_drops_faded_annotations(self) -> None:
        # A-9 jump clause: a snap plays no per-kind motion for cells / nodes /
        # carets, so a cursor_move / element_add identity spanned by a >=2-step
        # jump MUST still pulse (contrast _pulse_targets, which drops cursor_move
        # on the single-step path where it glides). But a newly-added annotation
        # fades in via _fadeInNewAnnotations, so it is DROPPED to avoid the
        # fade+pulse double.
        frames_tr = [
            [["q", "position", "0,0", "1,1", "cursor_move"],
             ["e", "el", None, "v", "element_add"]],
            [["note[n1]-solo", "annot", None, "note", "annotation_add"]],
            [["p", "state", "a", "b", "recolor"]],
        ]
        out = _changed_targets(frames_tr)
        assert out == ["q", "e", "p"], (
            "cursor_move / element_add / recolor snap with no motion on a jump — "
            "the pulse is kept; the faded-in annotation is dropped"
        )
        # single-step contrast: on ONE step cursor_move glides AND element_add
        # fades (both self-announce in _applyTransition), so _pulse_targets drops
        # both — whereas the jump keeps them (a snap plays neither motion).
        assert _pulse_targets(frames_tr[0]) == []

    def test_jump_annotation_excluded_even_if_recolored_in_span(self) -> None:
        # Same two-pass lesson on the jump path: a trace added in one skipped
        # frame and recolored in another is excluded WHOLE (the fade already
        # self-announced it) — a per-record skip would re-emit it via recolor.
        frames_tr = [
            [["t.trace[0]", "annot", None, "x", "annotation_add"]],
            [["t.trace[0]", "astate", "a", "b", "annotation_recolor"]],
        ]
        assert _changed_targets(frames_tr) == []
