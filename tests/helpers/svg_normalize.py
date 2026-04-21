"""SVG normalization pipeline for golden corpus SHA256 pinning.

All normalization steps are pure functions applied in sequence.
The pipeline is idempotent: normalize(normalize(svg)) == normalize(svg).

Steps (in order):
  1. Strip generation comments (<!-- generated at … -->, etc.)
  2. Strip KaTeX version-dependent class tokens
  3. Canonicalize float coordinates to 2 decimal places
  4. Canonicalize id= attributes and href/url(#) references
  5. Normalize whitespace (strip trailing, collapse blank lines)
  6. Sort <defs> children by id attribute
  7. Normalize empty elements (<foo></foo> → <foo/>)
"""
from __future__ import annotations

import hashlib
import math
import re


# ---------------------------------------------------------------------------
# Step 1: Strip generation comments
# ---------------------------------------------------------------------------

_GEN_COMMENT_RE = re.compile(
    r"<!--\s*(generated at|scriba version|katex version)[^>]*-->",
    re.IGNORECASE,
)


def _strip_generation_comments(svg: str) -> str:
    """Remove version/timestamp XML comments; preserve debug label-collision comments."""
    return _GEN_COMMENT_RE.sub("", svg)


# ---------------------------------------------------------------------------
# Step 2: Strip KaTeX version tokens from class attributes
# ---------------------------------------------------------------------------

_KATEX_VERSION_TOKEN_RE = re.compile(
    r"\b(katex-version-\S+|katex-\d+\.\d+\.\d+)\b"
)


def _strip_katex_version_tokens(svg: str) -> str:
    """Remove katex-version-X and katex-X.Y.Z tokens from class attributes."""

    def _clean_class(m: re.Match) -> str:
        cleaned = _KATEX_VERSION_TOKEN_RE.sub("", m.group(0)).strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned

    return re.sub(r'class="[^"]*"', _clean_class, svg)


# ---------------------------------------------------------------------------
# Step 3: Canonicalize floats to 2 decimal places
# ---------------------------------------------------------------------------

# Match numbers with 3 or more decimal places (including optional leading minus).
_FLOAT_LONG_RE = re.compile(r"-?\d+\.\d{3,}")


def _round_float(m: re.Match) -> str:
    val = float(m.group(0))
    if not math.isfinite(val):
        # Preserve NaN/Inf in known-bad fixtures so they remain detectable.
        return m.group(0)
    rounded = round(val, 2)
    if rounded == 0.0:
        return "0.0"
    return f"{rounded:.2f}"


def _canonicalize_floats(svg: str) -> str:
    """Round any float with ≥3 decimal places to exactly 2."""
    return _FLOAT_LONG_RE.sub(_round_float, svg)


# ---------------------------------------------------------------------------
# Step 4: Canonicalize IDs
# ---------------------------------------------------------------------------


def _canonicalize_ids(svg: str) -> str:
    """Replace id= attributes and all href/#/url(#) refs with id-NNNN sequentially."""
    id_map: dict[str, str] = {}
    counter = 0

    def _new_id(old: str) -> str:
        nonlocal counter
        if old not in id_map:
            counter += 1
            id_map[old] = f"id-{counter:04d}"
        return id_map[old]

    # First pass: collect all id= values in document order so mapping is stable.
    for m in re.finditer(r'\bid="([^"]+)"', svg):
        _new_id(m.group(1))

    # Second pass: replace declarations.
    svg = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{_new_id(m.group(1))}"', svg)
    # Replace href="#..." references.
    svg = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{_new_id(m.group(1))}"', svg)
    # Replace url(#...) references.
    svg = re.sub(r'url\(#([^)]+)\)', lambda m: f'url(#{_new_id(m.group(1))})', svg)
    return svg


# ---------------------------------------------------------------------------
# Step 5: Normalize whitespace
# ---------------------------------------------------------------------------


def _normalize_whitespace(svg: str) -> str:
    """Strip trailing whitespace per line and remove consecutive blank lines."""
    lines = svg.splitlines()
    result: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped:
            result.append(stripped)
    return "\n".join(result) + "\n"


# ---------------------------------------------------------------------------
# Step 6: Sort <defs> children by id attribute
# ---------------------------------------------------------------------------


def _sort_defs_children(svg: str) -> str:
    """Sort children of every <defs> block alphabetically by their id attribute."""

    def _sort_block(m: re.Match) -> str:
        inner = m.group(1)
        # Split on top-level child boundaries.
        children = re.split(r"(?=\n\s*<(?!/))", inner)
        children.sort(
            key=lambda c: (re.search(r'id="([^"]+)"', c).group(1)
                           if re.search(r'id="([^"]+)"', c) else c)
        )
        return f"<defs>{''.join(children)}</defs>"

    return re.sub(r"<defs>(.*?)</defs>", _sort_block, svg, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Step 7: Normalize empty elements
# ---------------------------------------------------------------------------


def _normalize_empty_elements(svg: str) -> str:
    """Replace <foo></foo> with self-closing <foo/>."""
    return re.sub(r"<(\w[\w:.-]*)((?:\s[^>]*)?)\s*></\1>", r"<\1\2/>", svg)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def normalize(svg: str) -> str:
    """Apply the full normalization pipeline to an SVG string.

    The pipeline is idempotent: normalize(normalize(svg)) == normalize(svg).

    Args:
        svg: Raw SVG string, e.g. from the scriba renderer.

    Returns:
        Canonical SVG string suitable for SHA256 pinning.
    """
    svg = _strip_generation_comments(svg)
    svg = _strip_katex_version_tokens(svg)
    svg = _canonicalize_floats(svg)
    svg = _canonicalize_ids(svg)
    svg = _normalize_whitespace(svg)
    svg = _sort_defs_children(svg)
    svg = _normalize_empty_elements(svg)
    return svg


def sha256_of(svg: str) -> str:
    """Return the hex SHA256 of the normalized form of *svg*.

    Args:
        svg: Raw or already-normalized SVG string.

    Returns:
        64-character lowercase hex digest.
    """
    return hashlib.sha256(normalize(svg).encode("utf-8")).hexdigest()
