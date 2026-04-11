"""Carve-out detector for ``\\begin{animation}...\\end{animation}`` blocks.

Scans a TeX source string and returns :class:`Block` instances for every
top-level animation environment found.  Nested environments raise
:class:`NestedAnimationError`; unclosed environments raise
:class:`UnclosedAnimationError`.

Blocks inside ``\\begin{lstlisting}...\\end{lstlisting}`` are skipped so
that code listings containing the literal text ``\\begin{animation}`` are
not falsely detected.
"""

from __future__ import annotations

import re

from scriba.animation.errors import (
    NestedAnimationError,
    UnclosedAnimationError,
    animation_error,
)
from scriba.core.artifact import Block

__all__ = ["detect_animation_blocks", "detect_diagram_blocks"]

# Matches \begin{lstlisting} ... \end{lstlisting} (greedy-safe via DOTALL).
_LSTLISTING_RE = re.compile(
    r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}",
    re.DOTALL,
)

# Matches \begin{animation} with optional [...] options on the same line.
_BEGIN_RE = re.compile(
    r"\\begin\{animation\}(\[[^\]]*\])?",
)

_END_RE = re.compile(
    r"\\end\{animation\}",
)


def _mask_lstlisting(source: str) -> str:
    """Replace lstlisting bodies with spaces so offsets stay stable."""
    result = list(source)
    for m in _LSTLISTING_RE.finditer(source):
        for i in range(m.start(), m.end()):
            result[i] = " "
    return "".join(result)


def _parse_options_raw(options_bracket: str | None) -> str | None:
    """Extract the raw options string from ``[key=val,...]``."""
    if options_bracket is None:
        return None
    # Strip leading '[' and trailing ']'
    return options_bracket[1:-1].strip() or None


def detect_animation_blocks(source: str) -> list[Block]:
    """Find all ``\\begin{animation}...\\end{animation}`` blocks in *source*.

    Returns a list of :class:`Block` instances sorted by ``start`` offset.
    Each block's ``raw`` is the exact substring
    ``source[block.start : block.end]``.

    Raises
    ------
    UnclosedAnimationError
        If a ``\\begin{animation}`` has no matching ``\\end{animation}``.
    NestedAnimationError
        If a ``\\begin{animation}`` appears inside another animation block.
    """
    masked = _mask_lstlisting(source)

    blocks: list[Block] = []
    open_start: int | None = None
    open_options_raw: str | None = None

    # Interleave begin/end matches in source order.
    begins = list(_BEGIN_RE.finditer(masked))
    ends = list(_END_RE.finditer(masked))

    events: list[tuple[int, str, re.Match[str]]] = []
    for m in begins:
        events.append((m.start(), "begin", m))
    for m in ends:
        events.append((m.start(), "end", m))
    events.sort(key=lambda e: e[0])

    for offset, kind, match in events:
        if kind == "begin":
            if open_start is not None:
                raise NestedAnimationError(position=offset)
            open_start = match.start()
            open_options_raw = _parse_options_raw(match.group(1))
        elif kind == "end":
            if open_start is None:
                # Stray \end{animation} — SF-8 (RFC-002): ALWAYS an error.
                # There is no strict-mode opt-out for this case; the
                # document is structurally malformed.
                raise animation_error(
                    "E1007",
                    detail=(
                        "stray \\end{animation} without a matching "
                        "\\begin{animation}"
                    ),
                )
            block_end = match.end()
            raw = source[open_start:block_end]
            metadata: dict[str, str | None] = {
                "options_raw": open_options_raw,
            }
            blocks.append(
                Block(
                    start=open_start,
                    end=block_end,
                    kind="animation",
                    raw=raw,
                    metadata=metadata,
                )
            )
            open_start = None
            open_options_raw = None

    if open_start is not None:
        raise UnclosedAnimationError(position=open_start)

    return blocks


# ---------------------------------------------------------------------------
# Diagram detection
# ---------------------------------------------------------------------------

_DIAGRAM_BEGIN_RE = re.compile(
    r"\\begin\{diagram\}(\[[^\]]*\])?",
)

_DIAGRAM_END_RE = re.compile(
    r"\\end\{diagram\}",
)


def detect_diagram_blocks(source: str) -> list[Block]:
    """Find all ``\\begin{diagram}...\\end{diagram}`` blocks in *source*."""
    masked = _mask_lstlisting(source)
    blocks: list[Block] = []
    open_start: int | None = None
    open_options_raw: str | None = None

    begins = list(_DIAGRAM_BEGIN_RE.finditer(masked))
    ends = list(_DIAGRAM_END_RE.finditer(masked))

    events: list[tuple[int, str, re.Match[str]]] = []
    for m in begins:
        events.append((m.start(), "begin", m))
    for m in ends:
        events.append((m.start(), "end", m))
    events.sort(key=lambda e: e[0])

    for offset, kind, match in events:
        if kind == "begin":
            open_start = match.start()
            open_options_raw = _parse_options_raw(match.group(1))
        elif kind == "end":
            if open_start is None:
                continue
            block_end = match.end()
            raw = source[open_start:block_end]
            blocks.append(
                Block(
                    start=open_start,
                    end=block_end,
                    kind="diagram",
                    raw=raw,
                    metadata={"options_raw": open_options_raw},
                )
            )
            open_start = None
            open_options_raw = None

    return blocks
