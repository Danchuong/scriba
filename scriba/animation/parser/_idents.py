"""One identifier charset for the whole pipeline (XID-style, stdlib only).

Every identifier surface (lexer tokens, selector parts, VariableWatch
names, ``\\foreach`` bindings, ``\\step`` label ids) converged on
``[^\\W\\d]\\w*`` in the 0.21.1 Unicode pass — which fixed Vietnamese
(precomposed letters are category Lo/Ll) but silently kept rejecting any
script that spells with combining marks: **Python's ``\\w`` does not
match Mn/Mc**, so Thai ``ค่า`` or Devanagari ``खोज`` died mid-identifier.

This module is the single replacement: UAX-31-shaped rules built on
``unicodedata.category`` —

- start:    any Letter (L*) or ``_``
- continue: Letter, decimal digit (Nd), combining mark (Mn/Mc), or ``_``
  (plus caller-supplied extras like ``.-`` for label ids)

Pure stdlib, deterministic, and fast enough for the lexer (identifiers
are short; category lookup is a C-level table hit).
"""

from __future__ import annotations

import unicodedata

__all__ = ["is_ident_start", "is_ident_continue", "match_ident_end", "is_ident"]


def is_ident_start(ch: str) -> bool:
    return ch == "_" or unicodedata.category(ch).startswith("L")


def is_ident_continue(ch: str, extra: str = "") -> bool:
    if ch == "_" or ch in extra:
        return True
    cat = unicodedata.category(ch)
    return cat.startswith("L") or cat in ("Mn", "Mc", "Nd")


def match_ident_end(text: str, pos: int = 0, *, extra: str = "") -> int | None:
    """End index of the identifier starting at *pos*, or None."""
    if pos >= len(text) or not is_ident_start(text[pos]):
        return None
    i = pos + 1
    n = len(text)
    while i < n and is_ident_continue(text[i], extra):
        i += 1
    return i


def is_ident(text: str, *, extra: str = "") -> bool:
    """True when the WHOLE string is one identifier."""
    end = match_ident_end(text, 0, extra=extra)
    return end == len(text) and end > 0
