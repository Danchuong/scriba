"""Deterministic HTML render-sanity heuristics for the doc-coverage corpus.

This module inspects *rendered* Scriba HTML output for soundness without
importing the render pipeline. ``sanity_check`` returns a list of anomaly
description strings; an empty list means the output looks clean.

Design notes / calibration (see ``SANITY-FLAGS.md`` for the corpus survey):

* Each rendered ``.html`` inlines a large shared shell: a ``<style>`` block
  containing base64-encoded KaTeX web fonts (which embed literal ``NaN`` and
  ``stroke:none`` substrings) and a control ``<script>`` block (which embeds
  ``undefined`` and ``display:none``). Those are *legitimate* shell tokens, so
  forbidden-substring checks run only over the **content regions**: the inline
  ``<svg>`` elements plus the visible body text with ``<style>``/``<script>``
  stripped out.
* ``None``/``NaN``/``Infinity``/``undefined`` are flagged only as whole words in
  visible text or SVG attribute values, never as fragments of identifiers or
  legitimate CSS (e.g. ``display:none``, ``fill="none"``, ``stroke:none``).
* Error codes leak as the bracketed form scriba emits (``[E1115]``); a bare
  ``E1115`` mentioned in narration prose is legitimate and is not flagged.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter

__all__ = ["sanity_check"]

# --- region extraction --------------------------------------------------- #

_SVG_RE = re.compile(r"<svg\b.*?</svg>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style\b.*?</style>", re.DOTALL | re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.DOTALL | re.IGNORECASE)
_BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_VIEWBOX_RE = re.compile(r'viewBox="([^"]*)"', re.IGNORECASE)
_TRANSLATE_RE = re.compile(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)")
_NONLINEAR_TRANSFORM_RE = re.compile(r"rotate|scale|matrix|skew")
_GEOMETRY_RE = re.compile(
    r"<(?:rect|circle|line|path|polygon|polyline|ellipse|image)\b", re.IGNORECASE
)


def _svg_blocks(html: str) -> list[str]:
    """Return every inline ``<svg>...</svg>`` block (figure and widget)."""
    return _SVG_RE.findall(html)


def _visible_text(html: str) -> str:
    """Return visible body text with shell ``<style>``/``<script>``/``<svg>`` removed.

    Tags are dropped so attribute values inside control markup (e.g.
    ``aria-label``, ``class``) never reach the word-boundary checks.
    """
    match = _BODY_RE.search(html)
    body = match.group(1) if match else html
    body = _STYLE_RE.sub(" ", body)
    body = _SCRIPT_RE.sub(" ", body)
    body = _SVG_RE.sub(" ", body)
    return _TAG_RE.sub(" ", body)


def _strip_ns(tag: str) -> str:
    """Strip an XML namespace prefix from an element tag."""
    return tag.split("}", 1)[1] if "}" in tag else tag


# --- forbidden-substring heuristics -------------------------------------- #

# Plain substrings that should never appear in any content region.
_PLAIN_FORBIDDEN: tuple[str, ...] = (
    "InterpolationRef",
    "[object Object]",
    "\x00HL",  # null-byte highlight placeholder
    "&lt;span",
    "&lt;/span",
    "katex-error",
)

# Whole-word tokens that indicate a bad numeric/None value when they appear as
# visible text or as an attribute *value*, but not as part of an identifier or
# legitimate CSS keyword.
_WORD_FORBIDDEN: tuple[str, ...] = ("NaN", "Infinity", "undefined", "None")
_WORD_RE = {
    tok: re.compile(r"(?<![\w-])" + re.escape(tok) + r"(?![\w-])")
    for tok in _WORD_FORBIDDEN
}

# A value position: a token used as an attribute value (``="NaN"`` /
# ``x="NaN"``), a CSS value (``:NaN``), or surrounded by whitespace/punctuation
# in visible text. A bare ``none`` in ``fill="none"`` is excluded because the
# token list above does not contain ``none``.
_ECODE_BRACKET_RE = re.compile(r"\[E\d{3,4}\]")


def _check_forbidden(svgs: list[str], text: str) -> list[str]:
    anomalies: list[str] = []
    blob = "\n".join(svgs) + "\n" + text

    for token in _PLAIN_FORBIDDEN:
        count = blob.count(token)
        if count:
            label = repr(token) if "\x00" in token else token
            anomalies.append(
                f"forbidden substring {label!s} appears {count}x in content"
            )

    for token in _WORD_FORBIDDEN:
        count = len(_WORD_RE[token].findall(blob))
        if count:
            anomalies.append(
                f"forbidden value token '{token}' appears {count}x in content"
            )

    ecodes = _ECODE_BRACKET_RE.findall(text)
    if ecodes:
        uniq = sorted(set(ecodes))
        anomalies.append(
            f"leaked error code(s) {', '.join(uniq)} in visible body text"
        )
    return anomalies


# --- viewBox heuristics --------------------------------------------------- #


def _check_viewbox(svg: str, index: int) -> list[str]:
    match = _VIEWBOX_RE.search(svg[: svg.find(">") + 1] if ">" in svg else svg)
    if match is None:
        return [f"svg#{index} has no viewBox"]
    parts = match.group(1).split()
    if len(parts) != 4:
        return [f"svg#{index} viewBox has {len(parts)} values (expected 4): "
                f"{match.group(1)!r}"]
    try:
        min_x, min_y, width, height = (float(p) for p in parts)
    except ValueError:
        return [f"svg#{index} viewBox has non-finite values: {match.group(1)!r}"]
    anomalies: list[str] = []
    for name, value in (("min_x", min_x), ("min_y", min_y),
                        ("width", width), ("height", height)):
        if value != value or value in (float("inf"), float("-inf")):  # NaN/inf
            anomalies.append(f"svg#{index} viewBox {name} is non-finite: "
                            f"{match.group(1)!r}")
    if not anomalies and (width <= 0 or height <= 0):
        anomalies.append(
            f"svg#{index} viewBox has non-positive size "
            f"(width={width}, height={height}): {match.group(1)!r}"
        )
    return anomalies


# --- well-formed-XML + duplicate id heuristics --------------------------- #


def _check_wellformed(svg: str, index: int) -> tuple[list[str], ET.Element | None]:
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        return [f"svg#{index} is not well-formed XML: {exc}"], None
    ids = [el.attrib["id"] for el in root.iter() if "id" in el.attrib]
    duplicates = sorted(_id for _id, count in Counter(ids).items() if count > 1)
    if duplicates:
        return [f"svg#{index} has duplicate id(s): {', '.join(duplicates)}"], root
    return [], root


# --- non-empty-shape heuristic ------------------------------------------- #


def _check_non_empty(html: str, svgs: list[str]) -> list[str]:
    """Flag a stage SVG that was clearly meant to draw a shape but is blank.

    Only applies to outputs that include a ``scriba-stage-svg`` (shape-based
    renders). Pure text/KaTeX outputs have no stage SVG and are exempt.
    """
    stage_svgs = [s for s in svgs if "scriba-stage-svg" in s]
    if not stage_svgs:
        return []
    for svg in stage_svgs:
        if (
            "data-primitive" in svg
            or "data-target" in svg
            or _GEOMETRY_RE.search(svg)
            or "<text" in svg
        ):
            return []
    return ["stage svg present but contains no primitive/cell/node/geometry"]


# --- text-in-bounds heuristic -------------------------------------------- #

_OVERFLOW_THRESHOLD = 0.5  # fraction of a dimension beyond an edge


def _collect_text_points(
    el: ET.Element, tx: float, ty: float, points: list[tuple[float, float]],
    skip: bool = False,
) -> None:
    transform = el.attrib.get("transform", "")
    skip = skip or bool(_NONLINEAR_TRANSFORM_RE.search(transform))
    translate = _TRANSLATE_RE.search(transform)
    if translate:
        tx += float(translate.group(1))
        ty += float(translate.group(2))
    if _strip_ns(el.tag) == "text" and not skip:
        x = _as_float(el.attrib.get("x"))
        y = _as_float(el.attrib.get("y"))
        if x is not None and y is not None:
            points.append((tx + x, ty + y))
    for child in el:
        _collect_text_points(child, tx, ty, points, skip)


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _check_text_bounds(
    root: ET.Element, svg: str, index: int
) -> list[str]:
    match = _VIEWBOX_RE.search(svg[: svg.find(">") + 1] if ">" in svg else svg)
    if match is None:
        return []
    try:
        min_x, min_y, width, height = (float(p) for p in match.group(1).split())
    except ValueError:
        return []
    if width <= 0 or height <= 0:
        return []
    points: list[tuple[float, float]] = []
    _collect_text_points(root, 0.0, 0.0, points)
    anomalies: list[str] = []
    for x, y in points:
        over_x = max(min_x - x, x - (min_x + width), 0.0) / width
        over_y = max(min_y - y, y - (min_y + height), 0.0) / height
        overflow = max(over_x, over_y)
        if overflow > _OVERFLOW_THRESHOLD:
            anomalies.append(
                f"svg#{index} text at ({x:g},{y:g}) is "
                f"{overflow:.0%} outside viewBox {match.group(1)!r}"
            )
    return anomalies


# --- public entry point --------------------------------------------------- #


def sanity_check(html: str, test_id: str) -> list[str]:
    """Return anomaly description strings for ``html``; empty list = clean.

    ``test_id`` is the corpus snippet id, used only to prefix anomaly strings
    so callers can attribute them. The function is pure and side-effect free.
    """
    svgs = _svg_blocks(html)
    text = _visible_text(html)

    anomalies: list[str] = []
    anomalies.extend(_check_forbidden(svgs, text))
    anomalies.extend(_check_non_empty(html, svgs))

    for index, svg in enumerate(svgs):
        anomalies.extend(_check_viewbox(svg, index))
        wellformed, root = _check_wellformed(svg, index)
        anomalies.extend(wellformed)
        if root is not None:
            anomalies.extend(_check_text_bounds(root, svg, index))

    return [f"[{test_id}] {anomaly}" for anomaly in anomalies]
