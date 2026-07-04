"""Playeach parser mixin for SceneParser. Extracted from grammar.py.

Internal module — not part of the public API. Methods access SceneParser
instance state (``self._tokens``, ``self._pos``, …) via the MRO.

``\\playeach{shape.range[lo:hi]}{actions}`` (and its 2-D ``block`` twin) is a
**step-level frame macro** (Phase C, item ⑥). Unlike ``\\foreach`` — which
expands *inside one frame* into a flat command list — ``\\playeach`` expands
into **one real ``FrameIR`` per swept element** at parse time. This is the
A-5 rule (``docs/spec/motion-ruleset.md``): a frame macro MUST desugar to the
same ``FrameIR`` sequence a hand-authored ``\\step`` list would produce, so
every downstream consumer (scene / differ / emitter / runtime) is unaware the
frames came from a macro.

Design (v1):

* Selector MUST be ``range`` (1-D) or ``block`` (2-D) with **literal integer**
  bounds — the frame count is fixed at build. Anything else is **E1494**.
* Actions are a ``key=value`` brace with three recognised keys:
  ``state=<state>`` (per-element ``\\recolor`` to a persistent state),
  ``cursor=<id>`` (a 1-D R-38 binding-caret that follows the sweep), and
  ``narrate="<template>"`` (per-frame narration; the loop index ``${i}`` — or
  ``${r}``/``${c}`` for a block — is substituted at build time, every other
  ``${…}`` is left for the scene-time compute interpolation).
* At least one of ``state``/``cursor`` MUST be present (**E1495**); ``cursor``
  is 1-D only, so ``cursor`` + ``block`` is also **E1495**.
* The expansion is capped at ``_MAX_PLAYEACH_FRAMES`` frames (**E1493**) — a
  per-element frame is far heavier than a per-element command, so the ceiling
  is tighter than ``\\foreach``'s iterable cap.

An undeclared shape is **not** checked here: the generated ``\\recolor`` /
``\\cursor`` commands travel the ordinary scene path and surface the normal
**E1116** at materialise time, which is exactly what keeps them
indistinguishable from hand frames.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from scriba.animation.constants import VALID_STATES
from scriba.core.errors import ValidationError

from .ast import (
    BlockAccessor,
    CellAccessor,
    CursorCommand,
    FrameIR,
    RangeAccessor,
    RecolorCommand,
    Selector,
    TickAccessor,
)
from .lexer import Token, TokenKind
from .selectors import parse_selector

# A per-element FRAME is much heavier than a per-element command (each is a
# full render), so ``\\playeach`` gets a tighter ceiling than ``\\foreach``'s
# 10k iterable cap. 64 comfortably covers a full array/DP-row sweep while
# staying well under the renderer's 100-frame hard limit (E1181).
_MAX_PLAYEACH_FRAMES = 64


@dataclass(frozen=True, slots=True)
class PlayeachExpansion:
    """Transient carrier for the frames a ``\\playeach`` desugars into.

    Never stored in the IR — the top-level parse loop consumes it immediately,
    flushing any pending frame and splicing ``frames`` into the frame stream.
    """

    frames: tuple[FrameIR, ...]


class _PlayeachMixin:
    if TYPE_CHECKING:
        _tokens: list[Token]
        _pos: int

        def _advance(self) -> Token: ...
        def _read_brace_arg(self, tok: Token) -> str: ...
        def _read_param_brace(self) -> dict: ...
        def _source_line_at(self, line: int) -> str | None: ...
        def _raise_unknown_enum(self, *a, **k) -> None: ...

    def _parse_playeach(self) -> PlayeachExpansion:
        """Parse ``\\playeach{selector}{actions}`` → an expansion of N frames."""
        tok = self._advance()  # consume \playeach

        selector_raw = self._read_brace_arg(tok).strip()
        sel = parse_selector(
            selector_raw,
            line=tok.line,
            col=tok.col,
            source_line=self._source_line_at(tok.line),
        )
        params = self._read_param_brace()

        _extra = set(params) - {"state", "cursor", "narrate"}
        if _extra:
            raise ValidationError(
                f"unknown \\playeach action key(s) {sorted(_extra)}; "
                "valid: state, cursor, narrate",
                position=tok.col,
                code="E1496",
                line=tok.line,
                col=tok.col,
                source_line=self._source_line_at(tok.line),
            )

        state, cursor_id, narrate_tmpl = self._playeach_actions(tok, params)
        acc = sel.accessor
        if isinstance(acc, RangeAccessor):
            frames = self._expand_range(tok, sel, acc, state, cursor_id, narrate_tmpl)
        elif isinstance(acc, BlockAccessor):
            frames = self._expand_block(tok, sel, acc, state, cursor_id, narrate_tmpl)
        else:
            raise self._playeach_error(
                tok,
                "E1494",
                f"\\playeach selector must be a range or block, got {selector_raw!r}",
                hint="use \\playeach{shape.range[lo:hi]}{...} or "
                "\\playeach{shape.block[r0:r1][c0:c1]}{...}",
            )
        return PlayeachExpansion(frames=tuple(frames))

    # ------------------------------------------------------------------
    # Action validation
    # ------------------------------------------------------------------

    def _playeach_actions(
        self, tok: Token, params: dict
    ) -> tuple[str | None, str | None, str | None]:
        """Extract and validate ``state`` / ``cursor`` / ``narrate`` actions."""
        state = params.get("state")
        if state is not None:
            state = str(state)
            if state not in VALID_STATES:
                self._raise_unknown_enum(
                    "playeach state",
                    state,
                    VALID_STATES,
                    code="E1109",
                    line=tok.line,
                    col=tok.col,
                )

        cursor_id = params.get("cursor")
        cursor_id = str(cursor_id) if cursor_id is not None else None

        narrate_tmpl = params.get("narrate")
        narrate_tmpl = str(narrate_tmpl) if narrate_tmpl is not None else None

        if state is None and cursor_id is None:
            raise self._playeach_error(
                tok,
                "E1495",
                "\\playeach requires at least one per-element action "
                "(state= or cursor=)",
                hint='e.g. \\playeach{a.range[1:5]}{state=done, cursor=w}',
            )
        return state, cursor_id, narrate_tmpl

    # ------------------------------------------------------------------
    # 1-D range expansion
    # ------------------------------------------------------------------

    def _expand_range(
        self,
        tok: Token,
        sel: Selector,
        acc: RangeAccessor,
        state: str | None,
        cursor_id: str | None,
        narrate_tmpl: str | None,
    ) -> list[FrameIR]:
        lo, hi = self._literal_bounds(tok, acc.lo, acc.hi)
        count = hi - lo + 1
        self._check_frame_cap(tok, count)
        shape = sel.shape_name
        # NumberLine addresses per-element parts as tick[i]; every other
        # cell primitive uses cell[i] (v1.1 — closes the playeach case
        # file's deferred NumberLine gap)
        _stype = getattr(self, "_shape_types", {}).get(shape)
        _is_tick = _stype == "NumberLine"
        frames: list[FrameIR] = []
        for i in range(lo, hi + 1):
            commands: list = []
            if state is not None:
                _acc = (
                    TickAccessor(index=i)
                    if _is_tick
                    else CellAccessor(indices=(i,))
                )
                commands.append(
                    RecolorCommand(
                        tok.line,
                        tok.col,
                        Selector(shape_name=shape, accessor=_acc),
                        state=state,
                    )
                )
            if cursor_id is not None:
                commands.append(
                    CursorCommand(
                        targets=(shape,),
                        index=0,
                        cursor_id=cursor_id,
                        at=str(i),
                        color="info",
                        line=tok.line,
                        col=tok.col,
                    )
                )
            narrate_body = (
                narrate_tmpl.replace("${i}", str(i))
                if narrate_tmpl is not None
                else None
            )
            frames.append(
                FrameIR(
                    line=tok.line,
                    commands=tuple(commands),
                    narrate_body=narrate_body,
                )
            )
        return frames

    # ------------------------------------------------------------------
    # 2-D block expansion
    # ------------------------------------------------------------------

    def _expand_block(
        self,
        tok: Token,
        sel: Selector,
        acc: BlockAccessor,
        state: str | None,
        cursor_id: str | None,
        narrate_tmpl: str | None,
    ) -> list[FrameIR]:
        if cursor_id is not None:
            raise self._playeach_error(
                tok,
                "E1495",
                "\\playeach cursor= is a 1-D construct and cannot ride a "
                "2-D block sweep",
                hint="drop cursor= for block, or sweep a 1-D range instead",
            )
        r_lo, r_hi = self._literal_bounds(tok, acc.row_lo, acc.row_hi)
        c_lo, c_hi = self._literal_bounds(tok, acc.col_lo, acc.col_hi)
        count = (r_hi - r_lo + 1) * (c_hi - c_lo + 1)
        self._check_frame_cap(tok, count)
        shape = sel.shape_name
        frames: list[FrameIR] = []
        for r in range(r_lo, r_hi + 1):
            for c in range(c_lo, c_hi + 1):
                commands: list = []
                if state is not None:
                    commands.append(
                        RecolorCommand(
                            tok.line,
                            tok.col,
                            Selector(
                                shape_name=shape,
                                accessor=CellAccessor(indices=(r, c)),
                            ),
                            state=state,
                        )
                    )
                narrate_body = None
                if narrate_tmpl is not None:
                    narrate_body = narrate_tmpl.replace("${r}", str(r)).replace(
                        "${c}", str(c)
                    )
                frames.append(
                    FrameIR(
                        line=tok.line,
                        commands=tuple(commands),
                        narrate_body=narrate_body,
                    )
                )
        return frames

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _literal_bounds(self, tok: Token, lo: object, hi: object) -> tuple[int, int]:
        """Require literal integer bounds and lo <= hi; else E1494."""
        if not isinstance(lo, int) or not isinstance(hi, int):
            raise self._playeach_error(
                tok,
                "E1494",
                "\\playeach range/block bounds must be literal integers "
                "(the frame count is fixed at build time)",
                hint="write literal bounds, e.g. range[1:5]; a computed count "
                "cannot be a frame macro",
            )
        if hi < lo:
            raise self._playeach_error(
                tok,
                "E1494",
                f"\\playeach range is empty: hi ({hi}) < lo ({lo})",
                hint="the upper bound is inclusive and must be >= the lower bound",
            )
        return lo, hi

    def _check_frame_cap(self, tok: Token, count: int) -> None:
        if count > _MAX_PLAYEACH_FRAMES:
            raise self._playeach_error(
                tok,
                "E1493",
                f"\\playeach would expand to {count} frames, exceeding the "
                f"maximum of {_MAX_PLAYEACH_FRAMES}",
                hint="split the sweep across multiple \\playeach blocks or "
                "narrow the range",
            )

    def _playeach_error(
        self, tok: Token, code: str, detail: str, *, hint: str | None = None
    ) -> ValidationError:
        return ValidationError(
            detail,
            position=tok.col,
            code=code,
            line=tok.line,
            col=tok.col,
            hint=hint,
            source_line=self._source_line_at(tok.line),
        )
