#!/usr/bin/env python3
"""Scriba animation renderer -- drop a .tex file, get HTML output.

Usage:
    python render.py input.tex              # -> output to input.html
    python render.py input.tex -o out.html  # -> output to out.html
    python render.py input.tex --open       # -> render and open in browser
    python render.py input.tex --static     # -> legacy filmstrip mode
"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.renderer import AnimationRenderer
from scriba.animation.starlark_host import StarlarkHost
from scriba.core.context import RenderContext
from scriba.core.workers import SubprocessWorkerPool
from scriba.tex.renderer import TexRenderer


def _make_inline_tex_callback(
    tex_renderer: TexRenderer,
) -> callable:
    """Build a callback that extracts $...$ from text and renders via KaTeX."""
    import html as _html
    import re

    def render_inline_tex(text: str) -> str:
        if "$" not in text:
            return _html.escape(text, quote=False)
        placeholders: list[tuple[str, str]] = []

        def _stash(html_fragment: str) -> str:
            ph = f"\x00MATH{len(placeholders)}\x00"
            placeholders.append((ph, html_fragment))
            return ph

        def _math_sub(m: re.Match[str]) -> str:
            inner = m.group(1)
            if not inner.strip():
                return m.group(0)
            return _stash(tex_renderer._render_inline(inner))

        result = re.sub(r"\$([^\$]+?)\$", _math_sub, text)
        result = _html.escape(result, quote=False)
        for ph, html_fragment in placeholders:
            result = result.replace(_html.escape(ph, quote=False), html_fragment)
        return result

    return render_inline_tex


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scriba — {title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  max-width: 720px;
  margin: 2rem auto;
  padding: 0 1rem;
  background: #fafafa;
  color: #11181c;
}}
h1 {{ font-size: 1.4rem; margin-bottom: 1.5rem; font-weight: 600; }}

/* Widget container */
.scriba-widget {{
  border: 1px solid #dfe3e6;
  border-radius: 10px;
  background: #ffffff;
  overflow: hidden;
}}

/* Controls bar */
.scriba-controls {{
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 1rem;
  background: #f8f9fa;
  border-bottom: 1px solid #dfe3e6;
  user-select: none;
}}
.scriba-controls button {{
  background: #ffffff;
  border: 1px solid #dfe3e6;
  border-radius: 6px;
  padding: 0.3rem 0.7rem;
  font-size: 0.8rem;
  cursor: pointer;
  color: #11181c;
  transition: background 0.15s, border-color 0.15s;
}}
.scriba-controls button:hover {{ background: #f1f3f5; border-color: #c1c8cd; }}
.scriba-controls button:active {{ background: #e6e8eb; }}
.scriba-controls button:disabled {{ opacity: 0.35; cursor: default; }}
.scriba-step-counter {{
  font: 600 0.78rem ui-monospace, "SF Mono", monospace;
  color: #687076;
  min-width: 5rem;
  text-align: center;
}}

/* Progress dots */
.scriba-progress {{
  display: flex;
  gap: 4px;
  margin-left: auto;
}}
.scriba-dot {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #dfe3e6;
  transition: background 0.2s;
}}
.scriba-dot.active {{ background: #0090ff; }}
.scriba-dot.done {{ background: #c1c8cd; }}

/* Stage */
.scriba-stage {{
  padding: 1.25rem 1rem;
  display: flex;
  justify-content: center;
  min-height: 100px;
}}
.scriba-stage-svg {{ width: 100%; height: auto; }}

/* Narration */
.scriba-narration {{
  padding: 0.75rem 1rem;
  font-size: 0.92rem;
  line-height: 1.55;
  color: #11181c;
  border-top: 1px solid #e6e8eb;
  min-height: 2.5rem;
}}

/* SVG text positioning.
 *
 * Font FAMILY is set per-primitive (e.g. CodePanel uses monospace,
 * Graph uses sans-serif) so no global ``font`` rule appears below. But
 * text-anchor and dominant-baseline are positioning attributes, not font
 * attributes — we DO set them globally so cells styled via CSS match
 * cells styled inline (Stack/Queue/HashMap/LinkedList/Matrix already
 * emit ``style="text-anchor:middle;dominant-baseline:central"`` per element).
 *
 * Before Wave 8, the standalone ``render.py`` HTML template had zero
 * text-anchor rules. Every Array/Grid/DPTable cell value, index label,
 * and caption emitted by the CSS-only path fell through to the SVG
 * defaults (``text-anchor: start, dominant-baseline: alphabetic``) so
 * text inside rects drifted right and high. See Wave 8 centering audit. */
[data-primitive] [data-target] > text {{
  font-variant-numeric:  tabular-nums lining-nums slashed-zero;
  font-feature-settings: "tnum" 1, "lnum" 1, "zero" 1, "ss01" 1;
  font-synthesis-weight: none;
  text-anchor:           middle;
  dominant-baseline:     central;
}}
.scriba-index-label,
.idx {{
  font:              500 10px ui-monospace, monospace;
  fill:              #687076;
  text-anchor:       middle;
  dominant-baseline: hanging;
}}
.scriba-primitive-label {{
  text-anchor:       middle;
  dominant-baseline: central;
}}

/* β "Tonal Architecture" — signal-state text gets a weight bump so the
   500-weight baseline reads as "rest". Two states only — current and
   error — for the same reason as in scriba-scene-primitives.css. */
.scriba-state-current > text,
.scriba-state-error > text {{
  font-weight: 600;
}}

/* β "Tonal Architecture" — complete state + cell token set.
   scriba-scene-primitives.css holds the canonical copy; this block is
   the standalone-CLI mirror. test_css_font_sync.py::TestHaloCascadeParity
   enforces the halo portion; the full state/stroke/text rules below are
   mirrored by convention because the cookbook pipeline embeds this
   template instead of linking scriba-scene-primitives.css. */
:root {{
  /* Base tokens */
  --scriba-bg:                     #ffffff;
  --scriba-fg:                     #11181c;
  --scriba-fg-muted:               #687076;
  --scriba-border:                 #dfe3e6;

  /* Geometry */
  --scriba-cell-rx:                6px;
  --scriba-cell-stroke-width:      1;
  --scriba-cell-stroke-width-signal: 2;
  --scriba-edge-stroke-width:      1.5;

  /* State fills */
  --scriba-state-idle-fill:        #f8f9fa;
  --scriba-state-current-fill:     #0090ff;
  --scriba-state-done-fill:        #e6e8eb;
  --scriba-state-dim-fill:         #f1f3f5;
  --scriba-state-error-fill:       #f8f9fa;
  --scriba-state-good-fill:        #e6e8eb;
  --scriba-state-highlight-fill:   #f8f9fa;
  --scriba-state-path-fill:        #e6e8eb;

  /* State strokes */
  --scriba-state-idle-stroke:      #dfe3e6;
  --scriba-state-current-stroke:   #0b68cb;
  --scriba-state-done-stroke:      #c1c8cd;
  --scriba-state-dim-stroke:       #e6e8eb;
  --scriba-state-error-stroke:     #e5484d;
  --scriba-state-good-stroke:      #2a7e3b;
  --scriba-state-highlight-stroke: #0090ff;
  --scriba-state-path-stroke:      #c1c8cd;

  /* State text */
  --scriba-state-idle-text:        #11181c;
  --scriba-state-current-text:     #ffffff;
  --scriba-state-done-text:        #11181c;
  --scriba-state-dim-text:         #687076;
  --scriba-state-error-text:       #11181c;
  --scriba-state-good-text:        #11181c;
  --scriba-state-highlight-text:   #0b68cb;
  --scriba-state-path-text:        #687076;
}}

/* State class rules — applied to <g data-target="..."> wrappers. Non-signal
   states (idle/done/dim/path) use the 1px baseline stroke; signal states
   (current/error/good/highlight) use the 2px --scriba-cell-stroke-width-signal
   so meaning is legible from the stroke alone. β Tonal Architecture. */
.scriba-state-idle > rect,
.scriba-state-idle > circle {{
  fill: var(--scriba-state-idle-fill);
  stroke: var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-cell-stroke-width);
}}
.scriba-state-idle > line {{
  stroke: var(--scriba-state-idle-stroke);
  stroke-width: var(--scriba-edge-stroke-width);
}}
.scriba-state-idle > text {{ fill: var(--scriba-state-idle-text); }}

.scriba-state-current > rect,
.scriba-state-current > circle {{
  fill: var(--scriba-state-current-fill);
  stroke: var(--scriba-state-current-stroke);
  stroke-width: var(--scriba-cell-stroke-width-signal);
}}
.scriba-state-current > line {{
  stroke: var(--scriba-state-current-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 1);
}}
.scriba-state-current > text {{ fill: var(--scriba-state-current-text); }}

.scriba-state-done > rect,
.scriba-state-done > circle {{
  fill: var(--scriba-state-done-fill);
  stroke: var(--scriba-state-done-stroke);
  stroke-width: var(--scriba-cell-stroke-width);
}}
.scriba-state-done > line {{
  stroke: var(--scriba-state-done-stroke);
  stroke-width: var(--scriba-edge-stroke-width);
}}
.scriba-state-done > text {{ fill: var(--scriba-state-done-text); }}

.scriba-state-dim > rect,
.scriba-state-dim > circle {{
  fill: var(--scriba-state-dim-fill);
  stroke: var(--scriba-state-dim-stroke);
  stroke-width: var(--scriba-cell-stroke-width);
}}
.scriba-state-dim > line {{
  stroke: var(--scriba-state-dim-stroke);
  stroke-width: var(--scriba-edge-stroke-width);
}}
.scriba-state-dim > text {{ fill: var(--scriba-state-dim-text); }}
.scriba-state-dim {{ opacity: 0.5; filter: saturate(0.3); }}

.scriba-state-error > rect,
.scriba-state-error > circle {{
  fill: var(--scriba-state-error-fill);
  stroke: var(--scriba-state-error-stroke);
  stroke-width: var(--scriba-cell-stroke-width-signal);
}}
.scriba-state-error > line {{
  stroke: var(--scriba-state-error-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 1);
}}
.scriba-state-error > text {{ fill: var(--scriba-state-error-text); }}

.scriba-state-good > rect,
.scriba-state-good > circle {{
  fill: var(--scriba-state-good-fill);
  stroke: var(--scriba-state-good-stroke);
  stroke-width: var(--scriba-cell-stroke-width-signal);
}}
.scriba-state-good > line {{
  stroke: var(--scriba-state-good-stroke);
  stroke-width: calc(var(--scriba-edge-stroke-width) + 1);
}}
.scriba-state-good > text {{ fill: var(--scriba-state-good-text); }}

.scriba-state-highlight > rect,
.scriba-state-highlight > circle {{
  fill: var(--scriba-state-highlight-fill);
  stroke: var(--scriba-state-highlight-stroke);
  stroke-width: var(--scriba-cell-stroke-width-signal);
}}
.scriba-state-highlight > line {{
  stroke: var(--scriba-state-highlight-stroke);
  stroke-width: var(--scriba-cell-stroke-width-signal);
}}
.scriba-state-highlight > text {{ fill: var(--scriba-state-highlight-text); }}

.scriba-state-path > rect,
.scriba-state-path > circle {{
  fill: var(--scriba-state-path-fill);
  stroke: var(--scriba-state-path-stroke);
  stroke-width: var(--scriba-cell-stroke-width);
}}
.scriba-state-path > line {{
  stroke: var(--scriba-state-path-stroke);
  stroke-width: var(--scriba-edge-stroke-width);
}}
.scriba-state-path > text {{ fill: var(--scriba-state-path-text); }}

/* Primitive rect base — border-radius and round caps come from CSS so
   Python emission only has to set x/y/width/height and the state class. */
[data-primitive="array"] > [data-target] > rect,
[data-primitive="grid"] > [data-target] > rect,
[data-primitive="dptable"] > [data-target] > rect,
[data-primitive="stack"] > [data-target] > rect,
[data-primitive="queue"] > [data-target] > rect,
[data-primitive="matrix"] > [data-target] > rect {{
  rx: var(--scriba-cell-rx);
  stroke-linecap: round;
  stroke-linejoin: round;
}}

/* Text halo — paint-order: stroke fill draws the stroke as a halo BEHIND
   the fill, so glyphs that overflow their container (e.g. segtree node
   labels like "[0,3]=11" inside a 22-pixel-radius circle) stay readable
   in the surrounding whitespace. The halo color matches the container
   state fill when the text is inside a stateful container, and matches
   the page background for floating labels. See Wave 9 research.
   Wrapped in ``@media (forced-colors: none)`` so Windows High Contrast
   mode can strip the halo cleanly. */
@media (forced-colors: none) {{
  [data-primitive] text {{
    paint-order:     stroke fill markers;
    stroke:          var(--scriba-halo, var(--scriba-bg));
    stroke-width:    3;
    stroke-linejoin: round;
    stroke-linecap:  round;
  }}

  .scriba-state-idle      > text {{ --scriba-halo: var(--scriba-state-idle-fill); }}
  .scriba-state-current   > text {{ --scriba-halo: var(--scriba-state-current-fill); }}
  .scriba-state-done      > text {{ --scriba-halo: var(--scriba-state-done-fill); }}
  .scriba-state-dim       > text {{ --scriba-halo: var(--scriba-state-dim-fill); }}
  .scriba-state-error     > text {{ --scriba-halo: var(--scriba-state-error-fill); }}
  .scriba-state-good      > text {{ --scriba-halo: var(--scriba-state-good-fill); }}
  .scriba-state-highlight > text {{ --scriba-halo: var(--scriba-state-highlight-fill); }}
  .scriba-state-path      > text {{ --scriba-halo: var(--scriba-state-path-fill); }}

  .scriba-index-label,
  .idx,
  .scriba-primitive-label,
  .scriba-graph-weight {{
    --scriba-halo: var(--scriba-bg);
    stroke-width:  2;
  }}

  .scriba-tree-nodes text,
  .scriba-graph-nodes text {{
    stroke-width: 4;
  }}
}}

/* State-change transitions (animation v1) */
[data-target] > rect,
[data-target] > circle {{
  transition: fill 180ms ease-out, stroke 180ms ease-out, stroke-width 180ms ease-out;
}}
[data-target] > line {{
  transition: stroke 180ms ease-out, stroke-width 180ms ease-out, opacity 200ms ease-out;
}}
[data-target] > text {{
  transition: fill 180ms ease-out, stroke 180ms ease-out;
}}

/* Frame transition */
.scriba-stage svg, .scriba-narration {{
  transition: opacity 0.2s ease;
}}

/* Static filmstrip layout (legacy) */
.scriba-animation {{ max-width: 100%; }}
.scriba-frames {{
  list-style: none;
  display: flex;
  gap: 1.5rem;
  overflow-x: auto;
  padding: 1rem 0;
  scroll-snap-type: x mandatory;
}}
.scriba-frame {{
  flex: 0 0 auto;
  min-width: 280px;
  max-width: 560px;
  border: 1px solid #dfe3e6;
  border-radius: 8px;
  background: #ffffff;
  scroll-snap-align: start;
  overflow: hidden;
}}
.scriba-frame-header {{
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border-bottom: 1px solid #dfe3e6;
}}
.scriba-step-label {{
  font: 600 0.72rem ui-monospace, monospace;
  color: #687076;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

/* Theme toggle */
.theme-toggle {{
  position: fixed; top: 1rem; right: 1rem;
  padding: 0.35rem 0.7rem; cursor: pointer;
  border: 1px solid #dfe3e6; border-radius: 6px; background: white;
  font-size: 0.8rem;
}}

/* Accessibility — reduced motion */
@media (prefers-reduced-motion: reduce) {{
  [data-target] > rect,
  [data-target] > circle,
  [data-target] > line,
  [data-target] > text {{
    transition-duration: 0ms !important;
  }}
}}

/* Print — force the browser to preserve tonal fills so cookbook prints
   render with the β palette instead of bare outline rects. */
@media print {{
  .scriba-stage-svg,
  .scriba-stage-svg * {{
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  [data-target] > rect,
  [data-target] > circle,
  [data-target] > line,
  [data-target] > text {{
    transition: none !important;
  }}
}}

/* Dark mode — β slate dark variant. Full token flip so state class
   rules above keep resolving against live values regardless of theme. */
[data-theme="dark"] {{
  --scriba-bg:                     #151718;
  --scriba-fg:                     #ecedee;
  --scriba-fg-muted:               #9ba1a6;
  --scriba-border:                 #313538;

  /* State fills */
  --scriba-state-idle-fill:        #1a1d1e;
  --scriba-state-current-fill:     #0090ff;
  --scriba-state-done-fill:        #2b2f31;
  --scriba-state-dim-fill:         #202425;
  --scriba-state-error-fill:       #1a1d1e;
  --scriba-state-good-fill:        #2b2f31;
  --scriba-state-highlight-fill:   #1a1d1e;
  --scriba-state-path-fill:        #2b2f31;

  /* State strokes */
  --scriba-state-idle-stroke:      #313538;
  --scriba-state-current-stroke:   #70b8ff;
  --scriba-state-done-stroke:      #4c5155;
  --scriba-state-dim-stroke:       #2b2f31;
  --scriba-state-error-stroke:     #ff6369;
  --scriba-state-good-stroke:      #65ba74;
  --scriba-state-highlight-stroke: #0090ff;
  --scriba-state-path-stroke:      #4c5155;

  /* State text */
  --scriba-state-idle-text:        #ecedee;
  --scriba-state-current-text:     #ffffff;
  --scriba-state-done-text:        #ecedee;
  --scriba-state-dim-text:         #9ba1a6;
  --scriba-state-error-text:       #ecedee;
  --scriba-state-good-text:        #ecedee;
  --scriba-state-highlight-text:   #70b8ff;
  --scriba-state-path-text:        #9ba1a6;
}}
[data-theme="dark"] body {{ background: #151718; color: #ecedee; }}
[data-theme="dark"] .scriba-widget {{ background: #1a1d1e; border-color: #313538; }}
[data-theme="dark"] .scriba-controls {{ background: #202425; border-color: #313538; }}
[data-theme="dark"] .scriba-controls button {{ background: #2b2f31; border-color: #313538; color: #ecedee; }}
[data-theme="dark"] .scriba-controls button:hover {{ background: #313538; }}
[data-theme="dark"] .scriba-step-counter {{ color: #9ba1a6; }}
[data-theme="dark"] .scriba-narration {{ color: #ecedee; border-color: #2b2f31; }}
[data-theme="dark"] .scriba-dot {{ background: #313538; }}
[data-theme="dark"] .idx {{ fill: #9ba1a6; }}
[data-theme="dark"] .scriba-frame {{ background: #1a1d1e; border-color: #313538; }}
[data-theme="dark"] .scriba-frame-header {{ background: #202425; border-color: #313538; }}
[data-theme="dark"] .scriba-step-label {{ color: #9ba1a6; }}
[data-theme="dark"] .theme-toggle {{ background: #2b2f31; color: #ecedee; border-color: #313538; }}
</style>
{katex_css}
</head>
<body>
<button class="theme-toggle" onclick="
  var t = document.documentElement.dataset.theme;
  document.documentElement.dataset.theme = t === 'dark' ? 'light' : 'dark';
">Toggle theme</button>
<h1>{title}</h1>
{body}
</body>
</html>
"""


def _snapshot_to_dict(snap: object) -> dict:
    """Convert a FrameSnapshot to a plain dict for JSON serialisation."""
    states: dict[str, str] = {}
    for _shape_name, targets in snap.shape_states.items():
        for target_key, ts in targets.items():
            parts = [ts.state]
            if ts.value is not None:
                parts.append(f"v={ts.value}")
            if ts.label is not None:
                parts.append(f"l={ts.label}")
            states[target_key] = ", ".join(parts)

    annotations = [
        {"target": a.target, "text": a.text, "color": a.color}
        for a in snap.annotations
    ]

    # Convert bindings values to JSON-safe types
    safe_bindings: dict[str, object] = {}
    for k, v in snap.bindings.items():
        try:
            json.dumps(v)
            safe_bindings[k] = v
        except (TypeError, ValueError):
            safe_bindings[k] = repr(v)

    return {
        "step": snap.index,
        "states": states,
        "annotations": annotations,
        "narrate": snap.narration or "",
        "bindings": safe_bindings,
    }


def render_file(
    input_path: Path,
    output_path: Path,
    *,
    output_mode: str = "interactive",
    dump_frames: bool = False,
    minify: bool = True,
) -> None:
    source = input_path.read_text()
    title = input_path.stem

    from scriba.animation.detector import detect_diagram_blocks
    from scriba.animation.renderer import DiagramRenderer

    # Wire up KaTeX for inline math in narration text.
    worker_pool = SubprocessWorkerPool()
    starlark_host = StarlarkHost(worker_pool)

    anim_renderer = AnimationRenderer(starlark_host=starlark_host)
    diag_renderer = DiagramRenderer(starlark_host=starlark_host)
    tex_renderer = TexRenderer(worker_pool=worker_pool)
    inline_tex_cb = _make_inline_tex_callback(tex_renderer)

    ctx = RenderContext(
        resource_resolver=lambda name: f"/static/{name}",
        theme="light",
        metadata={"output_mode": output_mode, "minify": minify},
        render_inline_tex=inline_tex_cb,
    )

    anim_blocks = detect_animation_blocks(source)
    diag_blocks = detect_diagram_blocks(source)

    if not anim_blocks and not diag_blocks:
        print(f"No \\begin{{animation}} or \\begin{{diagram}} blocks found in {input_path}")
        sys.exit(1)

    html_parts = []
    all_snapshots = []
    for block in anim_blocks:
        artifact = anim_renderer.render_block(block, ctx)
        html_parts.append(artifact.html)
        all_snapshots.extend(anim_renderer.last_snapshots)
    for block in diag_blocks:
        artifact = diag_renderer.render_block(block, ctx)
        html_parts.append(artifact.html)

    starlark_host.close()
    worker_pool.close()

    if dump_frames:
        dump = {"frames": [_snapshot_to_dict(s) for s in all_snapshots]}
        print(json.dumps(dump, indent=2))

    body = "\n\n".join(html_parts)

    # Include KaTeX CSS for math rendering in narration (CDN for font support).
    katex_css = '\n<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.css">'

    full_html = HTML_TEMPLATE.format(title=title, body=body, katex_css=katex_css)

    output_path.write_text(full_html)
    total = len(anim_blocks) + len(diag_blocks)
    print(f"Rendered {total} block(s) -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Render .tex animation to HTML")
    parser.add_argument("input", type=Path, help="Input .tex file")
    parser.add_argument("-o", "--output", type=Path, help="Output .html file")
    parser.add_argument("--open", action="store_true", help="Open in browser")
    parser.add_argument(
        "--static",
        action="store_true",
        help="Use legacy filmstrip mode instead of interactive widget",
    )
    parser.add_argument(
        "--dump-frames",
        action="store_true",
        help="Print a JSON summary of each frame's state to stdout for debugging",
    )
    parser.add_argument(
        "--no-minify",
        action="store_true",
        help="Disable HTML minification (useful for debugging output)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}")
        sys.exit(1)

    output = args.output or args.input.with_suffix(".html")
    output_mode = "static" if args.static else "interactive"
    render_file(
        args.input, output,
        output_mode=output_mode,
        dump_frames=args.dump_frames,
        minify=not args.no_minify,
    )

    if args.open:
        webbrowser.open(f"file://{output.resolve()}")


if __name__ == "__main__":
    main()
