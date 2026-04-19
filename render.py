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
import base64
import html
import json
import mimetypes
import os
import sys
import webbrowser
from pathlib import Path

from scriba.animation.renderer import AnimationRenderer
from scriba.animation.starlark_host import StarlarkHost
from scriba.core.context import RenderContext
from scriba.core.errors import ScribaError
from scriba.core.workers import SubprocessWorkerPool
from scriba.core.css_bundler import inline_katex_css, load_css
from scriba.tex.renderer import TexRenderer


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="{lang}" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scriba — {title}</title>
<style>
{css}
</style>
</head>
<body>
<button class="theme-toggle" data-scriba-action="theme-toggle">Toggle theme</button>
<h1>{title}</h1>
{body}
{inline_theme_script}</body>
</html>
"""

# Minimal inline bootstrap for the theme-toggle button when no external
# scriba.js is loaded (inline-runtime mode).  In external-runtime mode,
# scriba.js handles the delegated click via data-scriba-action.
_INLINE_THEME_SCRIPT = """\
<script>
document.addEventListener('click',function(e){
  var btn=e.target.closest('[data-scriba-action="theme-toggle"]');
  if(btn){var t=document.documentElement.dataset.theme;document.documentElement.dataset.theme=(t==='dark'?'light':'dark');}
});
</script>
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


def _resolve_resource(input_dir: Path, name: str) -> str:
    """Resolve a resource name to a data URI if the file exists locally."""
    candidate = (input_dir / name).resolve()
    input_dir_resolved = input_dir.resolve()
    if not candidate.is_relative_to(input_dir_resolved):
        return f"/static/{name}"
    if candidate.is_file():
        mime_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
    return f"/static/{name}"


def render_file(
    input_path: Path,
    output_path: Path,
    *,
    output_mode: str = "interactive",
    dump_frames: bool = False,
    minify: bool = True,
    lang: str = "en",
    inline_runtime: bool = True,
    asset_base_url: str = "",
    copy_runtime: bool = True,
) -> None:
    """Render a ``.tex`` animation file to HTML.

    Parameters
    ----------
    inline_runtime:
        When ``True`` (default in v0.8.x), all JS is inlined — fully
        self-contained HTML.  When ``False``, frame data goes into an
        inert JSON island and the runtime is referenced as an external
        ``scriba.<hash>.js`` asset.
    asset_base_url:
        URL prefix for the external runtime (e.g. a CDN path).  Only
        used when ``inline_runtime=False``.  When empty, the asset is
        referenced by filename only (expected next to the HTML).
    copy_runtime:
        When ``True`` (default) and ``inline_runtime=False``, copy
        ``scriba.<hash>.js`` next to the output HTML file.  Ignored when
        ``inline_runtime=True`` or ``asset_base_url`` is set.
    """
    source = input_path.read_text(encoding="utf-8-sig")
    title = html.escape(input_path.stem)  # C2: prevent XSS via malicious filename

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
        resource_resolver=lambda name: _resolve_resource(input_path.parent, name),
        theme="light",
        metadata={
            "output_mode": output_mode,
            "minify": minify,
            "inline_runtime": inline_runtime,
            "asset_base_url": asset_base_url,
        },
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

    # F-04: warn when the file has no animation or diagram blocks at all.
    if not anim_blocks and not diag_blocks:
        print(
            r"warning: no \begin{animation} or \begin{diagram} environment found."
            " Did you forget to wrap your content?",
            file=sys.stderr,
        )

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
            "scriba-embed.css",
            "scriba-standalone.css",
        ),
    ]

    # Add Pygments syntax highlighting CSS
    css_parts.append(load_css("scriba-tex-pygments-light.css"))

    # Opt-3: skip the ~380 KB KaTeX CSS+fonts blob when the document has no
    # math.  A document is math-free when it has no animation/diagram blocks
    # AND no bare $...$ or $$...$$ spans in the source TeX.
    #
    # We use the already-computed block lists (anim_blocks / diag_blocks) plus
    # a single regex scan of the source.  The regex matches any un-escaped
    # dollar sign: $$...$$ or $...$  (escaped \$ is excluded by negative
    # lookbehind). False positives (treating a literal $ as math) are safe
    # because they only cause us to include CSS we might not need — never
    # to drop CSS when it IS needed.
    import re as _re_opt3
    _has_math = bool(
        anim_blocks
        or diag_blocks
        or _re_opt3.search(r"(?<!\\)\$", source)
    )
    if _has_math:
        # Inline KaTeX CSS with embedded fonts (no CDN dependency)
        css_parts.append(inline_katex_css())

    css = "\n".join(css_parts)

    # In inline-runtime mode, attach the small theme-toggle bootstrap.
    # In external-runtime mode, scriba.js handles it via delegation.
    theme_script = _INLINE_THEME_SCRIPT if inline_runtime else ""

    full_html = HTML_TEMPLATE.format(
        title=title,
        body=body,
        css=css,
        lang=lang,
        inline_theme_script=theme_script,
    )

    output_path.write_text(full_html, encoding="utf-8")

    # Copy the external runtime asset next to the HTML when requested.
    if not inline_runtime and copy_runtime and not asset_base_url:
        from scriba.animation.runtime_asset import RUNTIME_JS_BYTES, RUNTIME_JS_FILENAME
        dest = output_path.parent / RUNTIME_JS_FILENAME
        dest.write_bytes(RUNTIME_JS_BYTES)
        print(f"Copied runtime -> {dest}")

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
    parser.add_argument(
        "--lang",
        default="en",
        help="BCP 47 language tag for HTML lang= attribute (e.g. 'vi', 'zh', 'ar')",
    )
    # Wave 8: external runtime flags (opt-in in v0.8.3; default flips in v0.9.0)
    parser.add_argument(
        "--inline-runtime",
        action="store_true",
        default=True,
        help=(
            "Inline the full JS runtime into the HTML (default; works on file://)."
            " Deprecated: will no longer be the default in v0.9.0."
        ),
    )
    parser.add_argument(
        "--no-inline-runtime",
        dest="inline_runtime",
        action="store_false",
        help=(
            "Use an external scriba.<hash>.js asset instead of inlining the"
            " runtime.  Requires the asset to be served alongside the HTML."
            " Enables a strict 'script-src self' CSP."
        ),
    )
    parser.add_argument(
        "--asset-base-url",
        default="",
        metavar="URL",
        help=(
            "URL prefix for the external scriba.<hash>.js asset"
            " (e.g. 'https://cdn.example.com/scriba/0.8.3')."
            " Only used with --no-inline-runtime."
        ),
    )
    parser.add_argument(
        "--copy-runtime",
        action="store_true",
        default=True,
        help=(
            "Copy scriba.<hash>.js next to the output HTML when using"
            " --no-inline-runtime (default: true unless --asset-base-url is set)."
        ),
    )
    parser.add_argument(
        "--no-copy-runtime",
        dest="copy_runtime",
        action="store_false",
        help="Do not copy scriba.<hash>.js next to the output HTML.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # F-03: reject clearly wrong file extensions
    _suffix = args.input.suffix.lower()
    _clearly_wrong = {".pdf", ".docx", ".doc", ".html", ".htm", ".odt", ".rtf"}
    if _suffix in _clearly_wrong:
        print(
            f"error: expected a .tex file, got '{args.input.suffix}' --"
            f" pass a LaTeX source file",
            file=sys.stderr,
        )
        sys.exit(2)
    elif _suffix not in (".tex", ".latex"):
        print(
            f"warning: input file has extension '{args.input.suffix}', not .tex --"
            f" attempting to render anyway",
            file=sys.stderr,
        )

    output = args.output or args.input.with_suffix(".html")

    # F-05: prevent --output from silently overwriting the input file
    if args.output and Path(args.output).resolve() == args.input.resolve():
        print(
            f"error: --output would overwrite the input file: {args.output}",
            file=sys.stderr,
        )
        sys.exit(2)

    # H1: prevent path traversal via -o flag unless opt-out env var is set
    if args.output and not os.environ.get("SCRIBA_ALLOW_ANY_OUTPUT"):
        resolved = Path(args.output).resolve()
        cwd = Path.cwd().resolve()
        try:
            resolved.relative_to(cwd)
        except ValueError:
            print(f"refusing to write outside cwd: {resolved}", file=sys.stderr)
            sys.exit(1)

    output_mode = "static" if args.static else "interactive"
    _debug = bool(os.environ.get("SCRIBA_DEBUG"))
    try:
        render_file(
            args.input, output,
            output_mode=output_mode,
            dump_frames=args.dump_frames,
            minify=not args.no_minify,
            lang=args.lang,
            inline_runtime=args.inline_runtime,
            asset_base_url=args.asset_base_url,
            copy_runtime=args.copy_runtime,
        )
    except ScribaError as exc:
        if _debug:
            raise
        print(f"error {exc}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        if _debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.open:
        webbrowser.open(f"file://{output.resolve()}")


if __name__ == "__main__":
    main()
