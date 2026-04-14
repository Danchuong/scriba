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

from scriba.animation.renderer import AnimationRenderer
from scriba.animation.starlark_host import StarlarkHost
from scriba.core.context import RenderContext
from scriba.core.workers import SubprocessWorkerPool
from scriba.core.css_bundler import inline_katex_css, load_css
from scriba.tex.renderer import TexRenderer


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scriba — {title}</title>
<style>
{css}
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

    from scriba.animation.detector import detect_animation_blocks, detect_diagram_blocks
    from scriba.animation.renderer import DiagramRenderer

    # Build renderers.
    worker_pool = SubprocessWorkerPool()
    starlark_host = StarlarkHost(worker_pool)

    anim_renderer = AnimationRenderer(starlark_host=starlark_host)
    diag_renderer = DiagramRenderer(starlark_host=starlark_host)
    tex_renderer = TexRenderer(worker_pool=worker_pool, enable_copy_buttons=False)

    # Wire up inline TeX callback for narration/labels.
    # TexRenderer.render_inline_text() is the mini-pipeline: math via
    # KaTeX, text commands, size commands, smart quotes, dashes, HTML
    # escape — everything except block-level processing.
    def _inline_tex(text: str) -> str:
        return tex_renderer.render_inline_text(text)

    ctx = RenderContext(
        resource_resolver=lambda name: f"/static/{name}",
        theme="light",
        metadata={"output_mode": output_mode, "minify": minify},
        render_inline_tex=_inline_tex,
    )

    # 1. Detect animation and diagram blocks (they carve out regions).
    anim_blocks = detect_animation_blocks(source)
    diag_blocks = detect_diagram_blocks(source)

    # 2. Merge and sort all special blocks by start position.
    special_blocks: list[tuple[int, int, str, object]] = []
    for b in anim_blocks:
        special_blocks.append((b.start, b.end, "animation", b))
    for b in diag_blocks:
        special_blocks.append((b.start, b.end, "diagram", b))
    special_blocks.sort(key=lambda t: t[0])

    # 3. Render in source order: TeX gaps + animation/diagram blocks.
    html_parts: list[str] = []
    all_snapshots: list[object] = []
    cursor = 0

    for start, end, kind, block in special_blocks:
        # Render the TeX gap before this block.
        if start > cursor:
            gap_source = source[cursor:start]
            if gap_source.strip():
                from scriba.core.artifact import Block as CoreBlock
                gap_block = CoreBlock(start=0, end=len(gap_source),
                                      kind="tex", raw=gap_source)
                gap_artifact = tex_renderer.render_block(gap_block, ctx)
                html_parts.append(gap_artifact.html)

        # Render the special block.
        if kind == "animation":
            artifact = anim_renderer.render_block(block, ctx)
            html_parts.append(artifact.html)
            all_snapshots.extend(anim_renderer.last_snapshots)
        else:
            artifact = diag_renderer.render_block(block, ctx)
            html_parts.append(artifact.html)

        cursor = end

    # Render trailing TeX after the last special block.
    if cursor < len(source):
        trailing = source[cursor:]
        if trailing.strip():
            from scriba.core.artifact import Block as CoreBlock
            gap_block = CoreBlock(start=0, end=len(trailing),
                                  kind="tex", raw=trailing)
            gap_artifact = tex_renderer.render_block(gap_block, ctx)
            html_parts.append(gap_artifact.html)

    starlark_host.close()
    worker_pool.close()

    if dump_frames:
        dump = {"frames": [_snapshot_to_dict(s) for s in all_snapshots]}
        print(json.dumps(dump, indent=2))

    body = "\n\n".join(html_parts)

    # Build CSS bundle from source files
    css_parts = [
        load_css(
            "scriba-scene-primitives.css",
            "scriba-animation.css",
            "scriba-standalone.css",
        ),
    ]

    # Add Pygments syntax highlighting CSS
    css_parts.append(load_css("scriba-tex-pygments-light.css"))

    # Inline KaTeX CSS with embedded fonts (no CDN dependency)
    css_parts.append(inline_katex_css())

    css = "\n".join(css_parts)

    full_html = HTML_TEMPLATE.format(title=title, body=body, css=css)

    output_path.write_text(full_html)
    block_count = len(anim_blocks) + len(diag_blocks)
    tex_gaps = len([p for p in html_parts if p]) - block_count
    print(f"Rendered {block_count} block(s) + {tex_gaps} TeX region(s) -> {output_path}")


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
