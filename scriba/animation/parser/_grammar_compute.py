"""Compute/interpolation binding mixin for SceneParser.

Extracted from grammar.py (Wave F6). Internal module — not part of the
public API.  Methods access SceneParser instance state via the MRO.
"""

from __future__ import annotations

import re as _re
import warnings as _warnings_mod
from typing import TYPE_CHECKING

from .ast import ComputeCommand
from .lexer import Token

if TYPE_CHECKING:
    pass


class _ComputeMixin:
    """Compute-block parser and static interpolation-binding checker."""

    if TYPE_CHECKING:
        _known_bindings: set[str]
        _error_recovery: bool

        def _advance(self) -> Token: ...
        def _read_raw_brace_arg(self, cmd_tok: Token) -> str: ...

    _ASSIGNMENT_RE = None  # lazy-initialised regex

    def _parse_compute(self) -> ComputeCommand:
        tok = self._advance()
        body = self._read_raw_brace_arg(tok).strip()
        # Best-effort extraction of top-level bindings for static interpolation
        # checks.  Failures silently fall through — Starlark binding analysis
        # is runtime-accurate only, so this is intentionally loose.
        try:
            self._collect_compute_bindings(body)
        except Exception:  # noqa: BLE001 — best effort, never fail parse
            pass
        return ComputeCommand(tok.line, tok.col, body)

    def _collect_compute_bindings(self, body: str) -> None:
        """Add top-level Starlark assignments in *body* to the symbol table.

        Only very simple, unambiguous forms are recognised:

            name = ...
            name1, name2 = ...
            def name(...):
            for name in ...:

        Anything more sophisticated (conditional binding, nested scopes,
        comprehensions) is ignored.  Because missing bindings only trigger
        a warning, false negatives are safer than false positives.
        """
        if _ComputeMixin._ASSIGNMENT_RE is None:
            _ComputeMixin._ASSIGNMENT_RE = _re.compile(
                r"""^[ \t]*            # leading indent
                (?:
                    def[ \t]+(?P<fn>[A-Za-z_]\w*)      # def name(...)
                    |
                    for[ \t]+(?P<for>[A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)[ \t]+in
                    |
                    (?P<lhs>[A-Za-z_]\w*(?:[ \t]*,[ \t]*[A-Za-z_]\w*)*)
                    [ \t]*=(?!=)                       # single =, not ==
                )
                """,
                _re.VERBOSE,
            )
        for raw_line in body.splitlines():
            # Strip comments after '#'
            line = raw_line.split("#", 1)[0]
            m = _ComputeMixin._ASSIGNMENT_RE.match(line)
            if not m:
                continue
            if m.group("fn"):
                self._known_bindings.add(m.group("fn"))
                continue
            if m.group("for"):
                for part in m.group("for").split(","):
                    name = part.strip()
                    if name.isidentifier():
                        self._known_bindings.add(name)
                continue
            lhs = m.group("lhs")
            if lhs:
                for part in lhs.split(","):
                    name = part.strip()
                    if name.isidentifier():
                        self._known_bindings.add(name)

    def _check_interpolation_binding(
        self,
        name: str,
        line: int,
        col: int,
    ) -> None:
        """Warn if *name* is referenced by ``${name}`` without a known binding.

        Called lazily from ``\\apply`` / ``\\highlight`` / selector parsing.
        Emits a plain ``UserWarning`` so tests can filter on message shape.
        Skipped entirely when the parser is in error-recovery mode — we
        don't want secondary warnings cluttering a multi-error report.
        """
        if self._error_recovery:
            return
        if not name or not name.isidentifier():
            return
        if name in self._known_bindings:
            return
        _warnings_mod.warn(
            f"${{{name}}} at line {line}, col {col}: "
            f"no compute-scope binding named {name!r} found before this point; "
            "runtime expansion may fail if the binding is not defined",
            UserWarning,
            stacklevel=3,
        )
