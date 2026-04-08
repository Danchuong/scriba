"""Structural validation helper for TeX sources.

See ``docs/scriba/02-tex-plugin.md`` §10 for the locked validator cases.
"""

from __future__ import annotations


def validate(content: str) -> tuple[bool, str | None]:
    """Return ``(True, None)`` on success or ``(False, message)`` on failure."""
    raise NotImplementedError
