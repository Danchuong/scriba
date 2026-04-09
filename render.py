#!/usr/bin/env python3
"""Scriba animation renderer — drop a .tex file, get HTML output.

Usage:
    python render.py input.tex              # → output to input.html
    python render.py input.tex -o out.html  # → output to out.html
    python render.py input.tex --open       # → render and open in browser
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from importlib import resources as res
from pathlib import Path

from scriba.animation.detector import detect_animation_blocks
from scriba.animation.renderer import AnimationRenderer
from scriba.core.context import RenderContext


def load_css() -> str:
    """Load animation CSS files inline."""
    css_parts = []
    static = res.files("scriba.animation.static")
    for name in ["scriba-scene-primitives.css", "scriba-animation.css"]:
        try:
            css_parts.append((static / name).read_text())
        except Exception:
            pass
    # Also load TeX CSS if available
    try:
        tex_static = res.files("scriba.tex.static")
        for name in ["scriba-tex-content.css"]:
            css_parts.append((tex_static / name).read_text())
    except Exception:
        pass
    return "\n".join(css_parts)


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
  max-width: 960px;
  margin: 2rem auto;
  padding: 0 1rem;
  background: #fafafa;
  color: #212529;
}}
h1 {{ font-size: 1.5rem; margin-bottom: 1.5rem; }}
.theme-toggle {{
  position: fixed; top: 1rem; right: 1rem;
  padding: 0.4rem 0.8rem; cursor: pointer;
  border: 1px solid #ccc; border-radius: 4px; background: white;
}}
{css}
</style>
</head>
<body>
<button class="theme-toggle" onclick="
  document.documentElement.dataset.theme =
    document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
">Toggle theme</button>
<h1>{title}</h1>
{body}
</body>
</html>
"""


def render_file(input_path: Path, output_path: Path) -> None:
    source = input_path.read_text()
    title = input_path.stem

    renderer = AnimationRenderer()
    ctx = RenderContext(
        resource_resolver=lambda name: f"/static/{name}",
        theme="light",
    )

    blocks = detect_animation_blocks(source)
    if not blocks:
        print(f"No \\begin{{animation}} blocks found in {input_path}")
        sys.exit(1)

    html_parts = []
    for block in blocks:
        artifact = renderer.render_block(block, ctx)
        html_parts.append(artifact.html)

    body = "\n\n".join(html_parts)
    css = load_css()
    full_html = HTML_TEMPLATE.format(title=title, css=css, body=body)

    output_path.write_text(full_html)
    print(f"Rendered {len(blocks)} animation(s) → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Render .tex animation to HTML")
    parser.add_argument("input", type=Path, help="Input .tex file")
    parser.add_argument("-o", "--output", type=Path, help="Output .html file")
    parser.add_argument("--open", action="store_true", help="Open in browser")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}")
        sys.exit(1)

    output = args.output or args.input.with_suffix(".html")
    render_file(args.input, output)

    if args.open:
        webbrowser.open(f"file://{output.resolve()}")


if __name__ == "__main__":
    main()
