"""Frozen tag and attribute whitelists for sanitizing Scriba HTML output.

Base whitelist is from ``docs/scriba/01-architecture.md`` §Sanitization.
SVG additions come from ``docs/scriba/03-diagram-plugin.md`` §11.

Scriba does not run bleach itself — it exposes these constants so the
consumer can sanitize once at the edge.
"""

from __future__ import annotations

from typing import Mapping


ALLOWED_TAGS: frozenset[str] = frozenset({
    # Text formatting
    "p", "br", "strong", "b", "em", "i", "u", "s", "del", "sub", "sup", "small", "span",
    # Headings
    "h1", "h2", "h3", "h4", "h5", "h6",
    # Lists
    "ul", "ol", "li",
    # Links and media
    "a", "img",
    # Code
    "pre", "code",
    # Tables
    "table", "thead", "tbody", "tr", "th", "td",
    # Block
    "div", "blockquote", "hr", "figure", "figcaption", "footer",
    # Interactive
    "button",
    # MathML (KaTeX output)
    "math", "semantics", "mrow", "mi", "mo", "mn", "ms", "mtext", "mspace",
    "msub", "msup", "msubsup", "mfrac", "msqrt", "mroot",
    "mover", "munder", "munderover",
    "mtable", "mtr", "mtd", "mstyle", "menclose", "mpadded", "mphantom", "merror",
    "annotation", "annotation-xml",
    # SVG (base KaTeX set)
    "svg", "path", "line", "rect", "circle", "g", "defs", "use", "clipPath",
    "polyline", "text", "marker",
    # SVG additions for diagram plugin (03-diagram-plugin.md §11.1)
    "polygon", "ellipse", "tspan", "mask", "pattern",
    "foreignObject", "desc", "title",
})


ALLOWED_ATTRS: Mapping[str, frozenset[str]] = {
    "*": frozenset({
        "class", "id", "title", "lang", "dir", "role",
        "aria-hidden", "aria-label", "aria-labelledby", "aria-describedby",
        "tabindex",
    }),
    "div": frozenset({
        "class", "id", "style",
        "data-step", "data-step-current", "data-step-count", "data-step-mode",
    }),
    "figure": frozenset({
        "class", "id",
        "data-step", "data-step-current", "data-step-count", "data-step-mode",
    }),
    "span": frozenset({"class", "id", "style"}),
    "a": frozenset({"href", "target", "rel", "title"}),
    "img": frozenset({"src", "alt", "width", "height", "loading", "style"}),
    "pre": frozenset({"class", "data-code", "data-language"}),
    "code": frozenset({"class", "data-language"}),
    "button": frozenset({"type", "class", "data-code", "data-step-target", "aria-label"}),
    "table": frozenset({"class"}),
    "th": frozenset({"class", "colspan", "rowspan", "scope"}),
    "td": frozenset({"class", "colspan", "rowspan"}),
    # KaTeX MathML attributes
    "math": frozenset({"xmlns", "display"}),
    "annotation": frozenset({"encoding"}),
    "annotation-xml": frozenset({"encoding"}),
    "mo": frozenset({
        "fence", "stretchy", "symmetric", "lspace", "rspace",
        "minsize", "maxsize", "accent",
    }),
    "mspace": frozenset({"width"}),
    "mtable": frozenset({
        "columnalign", "rowalign", "columnspacing", "rowspacing",
        "columnlines", "rowlines", "frame",
    }),
    "mtr": frozenset({"columnalign", "rowalign"}),
    "mtd": frozenset({"columnalign", "rowalign"}),
    "menclose": frozenset({"notation"}),
    "mstyle": frozenset({"displaystyle", "scriptlevel", "mathvariant"}),
    # SVG — merged base (01) + diagram additions (03 §11.2)
    "svg": frozenset({
        "viewBox", "xmlns", "xmlns:xlink", "width", "height",
        "fill", "focusable", "preserveAspectRatio",
    }),
    "path": frozenset({
        "d", "fill", "stroke", "stroke-width", "stroke-dasharray",
        "stroke-linecap", "stroke-linejoin",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "clip-path", "mask",
        "marker-start", "marker-mid", "marker-end",
        "data-step",
    }),
    "line": frozenset({
        "x1", "y1", "x2", "y2",
        "stroke", "stroke-width", "stroke-linecap", "stroke-dasharray",
        "opacity", "stroke-opacity",
        "marker-start", "marker-mid", "marker-end",
        "data-step",
    }),
    "rect": frozenset({
        "x", "y", "width", "height", "rx", "ry",
        "fill", "stroke", "stroke-width",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "clip-path", "mask",
        "data-step",
    }),
    "circle": frozenset({
        "cx", "cy", "r",
        "fill", "stroke", "stroke-width",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "data-step",
    }),
    "ellipse": frozenset({
        "cx", "cy", "rx", "ry",
        "fill", "stroke", "stroke-width",
        "fill-opacity", "stroke-opacity", "opacity",
        "transform", "data-step",
    }),
    "g": frozenset({
        "transform", "fill", "stroke", "clip-path", "mask", "opacity",
        "data-step", "data-scriba-action",
    }),
    "defs": frozenset(),
    "use": frozenset({"href", "xlink:href", "x", "y", "width", "height"}),
    "clipPath": frozenset({"id"}),
    "mask": frozenset({"id"}),
    "pattern": frozenset({"id", "x", "y", "width", "height", "patternUnits"}),
    "polyline": frozenset({
        "points", "fill", "stroke", "stroke-width",
        "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
        "fill-opacity", "stroke-opacity", "opacity",
        "marker-start", "marker-mid", "marker-end",
        "data-step",
    }),
    "polygon": frozenset({
        "points", "fill", "stroke", "stroke-width",
        "stroke-linecap", "stroke-linejoin",
        "fill-opacity", "stroke-opacity", "opacity",
        "data-step",
    }),
    "text": frozenset({
        "x", "y", "fill", "font-family", "font-size", "font-weight",
        "text-anchor", "dominant-baseline",
        "opacity", "transform", "data-step",
    }),
    "tspan": frozenset({
        "x", "y", "dx", "dy", "fill", "font-family", "font-size", "font-weight",
        "text-anchor",
    }),
    "marker": frozenset({
        "id", "viewBox", "refX", "refY",
        "markerWidth", "markerHeight", "orient",
    }),
    "foreignObject": frozenset({
        "x", "y", "width", "height", "transform", "data-step",
    }),
    "desc": frozenset(),
    "title": frozenset(),
}
