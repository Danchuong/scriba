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
import sys
import webbrowser
from pathlib import Path

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


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
  color: #212529;
}}
h1 {{ font-size: 1.4rem; margin-bottom: 1.5rem; font-weight: 600; }}

/* Widget container */
.scriba-widget {{
  border: 1px solid #d0d7de;
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
  background: #f6f8fa;
  border-bottom: 1px solid #d0d7de;
  user-select: none;
}}
.scriba-controls button {{
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  padding: 0.3rem 0.7rem;
  font-size: 0.8rem;
  cursor: pointer;
  color: #212529;
  transition: background 0.15s, border-color 0.15s;
}}
.scriba-controls button:hover {{ background: #f0f0f0; border-color: #bbb; }}
.scriba-controls button:active {{ background: #e4e4e4; }}
.scriba-controls button:disabled {{ opacity: 0.35; cursor: default; }}
.scriba-step-counter {{
  font: 600 0.78rem ui-monospace, "SF Mono", monospace;
  color: #6c757d;
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
  background: #d0d7de;
  transition: background 0.2s;
}}
.scriba-dot.active {{ background: #0072B2; }}
.scriba-dot.done {{ background: #009E73; }}

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
  color: #212529;
  border-top: 1px solid #f0f0f0;
  min-height: 2.5rem;
}}

/* SVG text */
svg text {{
  font: 700 14px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  text-anchor: middle;
  dominant-baseline: central;
}}
.idx {{
  font: 500 10px ui-monospace, monospace;
  fill: #6c757d;
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
  border: 1px solid #d0d7de;
  border-radius: 8px;
  background: #ffffff;
  scroll-snap-align: start;
  overflow: hidden;
}}
.scriba-frame-header {{
  padding: 0.5rem 1rem;
  background: #f6f8fa;
  border-bottom: 1px solid #d0d7de;
}}
.scriba-step-label {{
  font: 600 0.72rem ui-monospace, monospace;
  color: #6c757d;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

/* Theme toggle */
.theme-toggle {{
  position: fixed; top: 1rem; right: 1rem;
  padding: 0.35rem 0.7rem; cursor: pointer;
  border: 1px solid #ccc; border-radius: 6px; background: white;
  font-size: 0.8rem;
}}

/* Dark mode */
[data-theme="dark"] body {{ background: #0d1117; color: #e6edf3; }}
[data-theme="dark"] .scriba-widget {{ background: #161b22; border-color: #30363d; }}
[data-theme="dark"] .scriba-controls {{ background: #1c2128; border-color: #30363d; }}
[data-theme="dark"] .scriba-controls button {{ background: #21262d; border-color: #30363d; color: #e6edf3; }}
[data-theme="dark"] .scriba-controls button:hover {{ background: #30363d; }}
[data-theme="dark"] .scriba-step-counter {{ color: #7d8590; }}
[data-theme="dark"] .scriba-narration {{ color: #e6edf3; border-color: #21262d; }}
[data-theme="dark"] .scriba-dot {{ background: #30363d; }}
[data-theme="dark"] .idx {{ fill: #7d8590; }}
[data-theme="dark"] .scriba-frame {{ background: #161b22; border-color: #30363d; }}
[data-theme="dark"] .scriba-frame-header {{ background: #1c2128; border-color: #30363d; }}
[data-theme="dark"] .scriba-step-label {{ color: #7d8590; }}
[data-theme="dark"] .theme-toggle {{ background: #21262d; color: #e6edf3; border-color: #30363d; }}
</style>
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


def render_file(
    input_path: Path,
    output_path: Path,
    *,
    output_mode: str = "interactive",
) -> None:
    source = input_path.read_text()
    title = input_path.stem

    from scriba.animation.detector import detect_diagram_blocks
    from scriba.animation.renderer import DiagramRenderer

    anim_renderer = AnimationRenderer()
    diag_renderer = DiagramRenderer()
    ctx = RenderContext(
        resource_resolver=lambda name: f"/static/{name}",
        theme="light",
        metadata={"output_mode": output_mode},
    )

    anim_blocks = detect_animation_blocks(source)
    diag_blocks = detect_diagram_blocks(source)

    if not anim_blocks and not diag_blocks:
        print(f"No \\begin{{animation}} or \\begin{{diagram}} blocks found in {input_path}")
        sys.exit(1)

    html_parts = []
    for block in anim_blocks:
        artifact = anim_renderer.render_block(block, ctx)
        html_parts.append(artifact.html)
    for block in diag_blocks:
        artifact = diag_renderer.render_block(block, ctx)
        html_parts.append(artifact.html)

    body = "\n\n".join(html_parts)
    full_html = HTML_TEMPLATE.format(title=title, body=body)

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
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}")
        sys.exit(1)

    output = args.output or args.input.with_suffix(".html")
    output_mode = "static" if args.static else "interactive"
    render_file(args.input, output, output_mode=output_mode)

    if args.open:
        webbrowser.open(f"file://{output.resolve()}")


if __name__ == "__main__":
    main()
