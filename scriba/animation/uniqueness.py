"""Cross-cutting uniqueness validations for animation IDs and shape names.

See FIX_PLAN Phase 3 W6.4 and Agent 14 red-team findings.

This module exposes three small check functions that other subsystems
call as a single-line guard. Each raises an :class:`AnimationError` with
a dedicated E-code so the renderer can surface a structured message
rather than a bare :class:`ValueError`:

* ``validate_shape_id_charset`` — ``E1017`` (invalid charset / too long)
* ``check_duplicate_shape_ids``  — ``E1018`` (duplicate within animation)
* ``check_duplicate_animation_ids`` — ``E1019`` (duplicate across document)

The allowed charset is deliberately stricter than Python identifiers
to avoid surprises in selector parsing, CSS/HTML attribute escaping,
and serialization of shape names into JSON keys.
"""

from __future__ import annotations

import re

from scriba.animation.errors import _animation_error

__all__ = [
    "validate_shape_id_charset",
    "check_duplicate_shape_ids",
    "check_duplicate_animation_ids",
]

# ASCII letter or underscore, followed by up to 62 additional ASCII
# letters/digits/underscores. Total max length 63 characters.
_VALID_SHAPE_ID_RE: re.Pattern[str] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")

# Maximum length is encoded in the regex but kept as a constant for
# explicit messaging in error payloads.
_MAX_SHAPE_ID_LEN: int = 63


def validate_shape_id_charset(
    shape_id: str,
    *,
    line: int | None = None,
    col: int | None = None,
) -> None:
    """Raise E1017 if *shape_id* contains disallowed characters or is too long.

    Allowed: ASCII letters, digits, underscore. Must start with a letter
    or underscore. Max length 63. This is stricter than Python
    identifiers (no non-ASCII) on purpose — shape ids travel through
    selector parsing, HTML attribute escaping, and JSON keys, and each
    of those surfaces has its own set of gotchas for unusual code
    points. Keeping the charset tight eliminates the entire class of
    "works in Python, breaks in the browser" bugs.

    Parameters
    ----------
    shape_id:
        The candidate identifier.
    line, col:
        Optional 1-indexed source location from the parser so error
        messages point at the offending token rather than the top of
        the file.
    """
    if not isinstance(shape_id, str) or not _VALID_SHAPE_ID_RE.match(shape_id):
        raise _animation_error(
            "E1017",
            detail=(
                f"shape id {shape_id!r} contains invalid characters "
                f"or exceeds {_MAX_SHAPE_ID_LEN} characters"
            ),
            hint="allowed: [a-zA-Z_][a-zA-Z0-9_]{0,62}",
            line=line,
            col=col,
        )


def check_duplicate_shape_ids(shape_ids: list[str]) -> None:
    """Raise E1018 on the first duplicate shape id in *shape_ids*.

    Each shape must have a unique id within its enclosing animation or
    substory. Duplicate ids make mutation commands ambiguous (which
    shape does ``\\apply{name}`` target?) and break the rename/refactor
    tooling that assumes a single source of truth per id.

    Parameters
    ----------
    shape_ids:
        List of shape names in declaration order. The caller is
        expected to pass names from a single animation scope — nested
        substories have their own list and their own call site.
    """
    seen: set[str] = set()
    for sid in shape_ids:
        if sid in seen:
            raise _animation_error(
                "E1018",
                detail=f"duplicate shape id {sid!r} within animation",
                hint=(
                    "each shape must have a unique id within its "
                    "enclosing animation/substory"
                ),
            )
        seen.add(sid)


def check_duplicate_animation_ids(animation_ids: list[str]) -> None:
    """Raise E1019 on the first duplicate animation id in *animation_ids*.

    Each ``\\begin{animation}[id=...]`` must be unique across the whole
    document. Duplicate ids collide at the HTML element level (two
    ``<div id="X">`` blocks) and break anchor links, cross-animation
    selectors, and deterministic scene-id generation.

    Parameters
    ----------
    animation_ids:
        List of ids collected from every ``\\begin{animation}[id=...]``
        in document order. IDs that were auto-generated from the block
        body (i.e. not explicitly authored) should be excluded by the
        caller — the check only applies to explicit ids.
    """
    seen: set[str] = set()
    for aid in animation_ids:
        if aid in seen:
            raise _animation_error(
                "E1019",
                detail=f"duplicate animation id {aid!r} within document",
                hint=(
                    "each \\begin{animation}[id=...] must have a unique "
                    "id across the whole document"
                ),
            )
        seen.add(aid)
