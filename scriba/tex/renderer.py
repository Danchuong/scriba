"""TexRenderer — implements the Renderer protocol for TeX-flavored sources.

See ``docs/scriba/02-tex-plugin.md`` §Public API for the locked signature.
"""

from __future__ import annotations

import html as _html
import logging
import os
import re
import shutil
import subprocess
from importlib.resources import files
from pathlib import Path
from typing import Literal, Mapping

from scriba.core.artifact import Block, RenderArtifact, RendererAssets
from scriba.core.context import RenderContext
from scriba.core.errors import RendererError, ValidationError, WorkerError
from scriba.core.workers import SubprocessWorker, SubprocessWorkerPool
from scriba.tex.parser.code_blocks import extract_lstlisting
from scriba.tex.parser.dashes_quotes import apply_typography
from scriba.tex.parser.environments import (
    apply_center,
    apply_epigraph,
    apply_sections,
    apply_urls,
)
from scriba.tex.parser.escape import PlaceholderManager, html_escape_text
from scriba.tex.parser.images import apply_includegraphics
from scriba.tex.parser.lists import apply_lists
from scriba.tex.parser.math import (
    extract_math,
    render_math_batch,
    restore_dollar_literals,
)
from scriba.tex.parser.tables import apply_tabular
from scriba.tex.parser.text_commands import apply_size_commands, apply_text_commands
from scriba.tex.validate import validate as _validate


logger = logging.getLogger(__name__)

MAX_SOURCE_SIZE = 1_048_576
"""Maximum raw source bytes accepted by TexRenderer (1 MiB)."""


class TexRenderer:
    """Render a TeX-flavored problem statement to a self-contained HTML fragment."""

    name: str = "tex"
    version: int = 1
    priority: int = 100

    def __init__(
        self,
        *,
        worker_pool: SubprocessWorkerPool,
        pygments_theme: Literal[
            "one-light", "one-dark", "github-light", "github-dark", "none"
        ] = "one-light",
        enable_copy_buttons: bool = True,
        katex_macros: Mapping[str, str] | None = None,
        katex_worker_path: str | Path | None = None,
        katex_worker_timeout: float = 10.0,
        katex_worker_max_requests: int = 50_000,
        node_executable: str = "node",
        strict_math: bool = False,
    ) -> None:
        self._worker_pool = worker_pool
        self._pygments_theme = pygments_theme
        self._enable_copy_buttons = enable_copy_buttons
        self._katex_macros = dict(katex_macros) if katex_macros else None
        self._katex_worker_timeout = katex_worker_timeout
        self._katex_worker_max_requests = katex_worker_max_requests
        self._node_executable = node_executable
        self._strict_math = strict_math
        self._closed = False

        if katex_worker_path is None:
            resolved = files("scriba.tex").joinpath("katex_worker.js")
            self._katex_worker_path = Path(str(resolved))
        else:
            self._katex_worker_path = Path(katex_worker_path)

        # Ensure NODE_PATH is set so the worker can find a globally installed
        # ``katex`` package. We only set it if the parent env doesn't already
        # carry one — never overwrite a deliberate operator setting.
        if "NODE_PATH" not in os.environ:
            global_root = self._discover_node_global_root()
            if global_root:
                os.environ["NODE_PATH"] = global_root

        worker = SubprocessWorker(
            name="katex",
            argv=[self._node_executable, str(self._katex_worker_path)],
            ready_signal="katex-worker ready",
            max_requests=self._katex_worker_max_requests,
            default_timeout=self._katex_worker_timeout,
        )
        worker_pool.register("katex", worker=worker)

    @staticmethod
    def _discover_node_global_root() -> str | None:
        npm = shutil.which("npm")
        if not npm:
            return None
        try:
            result = subprocess.run(
                [npm, "root", "-g"],
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        if result.returncode != 0:
            return None
        path = result.stdout.strip()
        return path or None

    # ----- Renderer protocol -----

    def detect(self, source: str) -> list[Block]:
        if len(source.encode("utf-8", errors="ignore")) > MAX_SOURCE_SIZE:
            raise ValidationError(
                f"tex source exceeds maximum size "
                f"({MAX_SOURCE_SIZE} bytes)"
            )
        return [Block(start=0, end=len(source), kind="tex", raw=source)]

    def render_block(self, block: Block, ctx: RenderContext) -> RenderArtifact:
        html_text = self._render_source(block.raw, ctx)
        css = {"scriba-tex-content.css"}
        if self._pygments_theme in ("one-light", "github-light"):
            css.add("scriba-tex-pygments-light.css")
        elif self._pygments_theme in ("one-dark", "github-dark"):
            css.add("scriba-tex-pygments-dark.css")
        js: set[str] = set()
        if self._enable_copy_buttons:
            js.add("scriba-tex-copy.js")
        return RenderArtifact(
            html=html_text,
            css_assets=frozenset(css),
            js_assets=frozenset(js),
        )

    def assets(self) -> RendererAssets:
        static = files("scriba.tex").joinpath("static")
        css: set[Path] = {Path(str(static / "scriba-tex-content.css"))}
        if self._pygments_theme in ("one-light", "github-light"):
            css.add(Path(str(static / "scriba-tex-pygments-light.css")))
        elif self._pygments_theme in ("one-dark", "github-dark"):
            css.add(Path(str(static / "scriba-tex-pygments-dark.css")))
        js: set[Path] = set()
        if self._enable_copy_buttons:
            js.add(Path(str(static / "scriba-tex-copy.js")))
        return RendererAssets(
            css_files=frozenset(css), js_files=frozenset(js)
        )

    def validate(self, content: str) -> tuple[bool, str | None]:
        return _validate(content)

    def close(self) -> None:
        self._closed = True

    def __enter__(self) -> "TexRenderer":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ----- private API -----

    def _render_cell(self, raw: str) -> str:
        """Render raw TeX from inside a tabular cell to safe HTML.

        Runs the same passes as the main pipeline but in a smaller, local
        scope: inline math via the KaTeX worker, text-style commands,
        dashes and smart quotes, HTML escape. Math output is temporarily
        stashed in placeholders so HTML-escape and regex passes don't
        mangle the KaTeX markup.
        """
        if not raw.strip():
            return ""

        # 1. Inline math first → safe HTML span → placeholder.
        cell_placeholders: list[tuple[str, str]] = []

        def _stash(html: str) -> str:
            ph = f"\x00CELL{len(cell_placeholders)}\x00"
            cell_placeholders.append((ph, html))
            return ph

        def _math_sub(m: re.Match[str]) -> str:
            inner = m.group(1)
            if not inner.strip():
                return m.group(0)
            return _stash(self._render_inline(inner))

        text = re.sub(r"\$([^\$]+?)\$", _math_sub, raw)

        # 2. Escape literals before HTML escape.
        text = text.replace("\\$", "$").replace("\\&", "&")

        # 3. HTML-escape free text (math is already stashed).
        text = _html.escape(text, quote=False)

        # 4. Text commands and size commands (operate on escaped text;
        #    they emit fixed safe wrappers).
        text = apply_text_commands(text)
        text = apply_size_commands(text)

        # 5. Typography (dashes, smart quotes).
        text = apply_typography(text)

        # 6. Restore math placeholders.
        for ph, html in cell_placeholders:
            text = text.replace(ph, html)
        return text

    def _render_inline(self, tex: str) -> str:
        """Render a bare inline math fragment to HTML."""
        if not tex.strip():
            return ""
        worker = self._worker_pool.get("katex")
        request: dict = {
            "type": "single",
            "math": tex.strip(),
            "displayMode": False,
        }
        if self._katex_macros:
            request["macros"] = dict(self._katex_macros)
        try:
            response = worker.send(request, timeout=self._katex_worker_timeout)
        except WorkerError as e:
            if self._strict_math:
                raise
            logger.warning("KaTeX inline failed, escaping: %s", e)
            return html_escape_text(tex)
        html = response.get("html")
        if html is None:
            if self._strict_math:
                raise RendererError(
                    f"katex error: {response.get('error')}", renderer="tex"
                )
            return html_escape_text(tex)
        return f'<span class="scriba-tex-math-inline">{html}</span>'

    # ----- main pipeline -----

    def _render_source(self, source: str, ctx: RenderContext) -> str:
        if not source:
            return ""

        placeholders = PlaceholderManager()
        slug_counts: dict[str, int] = {}

        # 0. Extract lstlisting and tabular FIRST so their bodies are not
        #    interpreted as TeX (cells use ``&``, code uses ``$``, both
        #    would otherwise collide with math/cell parsing).
        text = extract_lstlisting(
            source,
            placeholders,
            theme=self._pygments_theme,
            enable_copy_button=self._enable_copy_buttons,
        )
        text = apply_tabular(text, placeholders, cell_renderer=self._render_cell)

        # 0b. Resolve images before HTML escaping so the resolver sees the
        #     real filename and we can entity-escape the URL exactly once.
        text = apply_includegraphics(
            text,
            placeholders,
            resource_resolver=ctx.resource_resolver,
        )

        # 1. Extract math next so we don't HTML-escape KaTeX output later.
        text, math_items = extract_math(text, placeholders)

        # 2. HTML-escape free text. Math placeholders contain only NULs and
        #    ASCII so they survive escape unchanged.
        text = _html.escape(text, quote=False)

        # 3. Restore the dollar-literal sentinel.
        text = restore_dollar_literals(text)

        # 4. Apply text-style commands BEFORE the regex-driven environments
        #    so things like ``\textbf{<script>}`` see escaped angle brackets.
        text = apply_text_commands(text)
        text = apply_size_commands(text)

        # 5. URL/href first so escaping inside text doesn't break the regex.
        #    The regex matches the raw braces; user input is escaped via
        #    apply_urls itself.
        text = apply_urls(text)

        # 6. Block environments.
        text = apply_epigraph(text)
        text = apply_lists(text)
        text = apply_center(text)
        text = apply_sections(text, slug_counts)

        # 7. Typography (dashes, smart quotes, ties, line breaks).
        text = apply_typography(text)

        # 8. Math rendering — done here so we can fail fast on worker errors
        #    after all the cheap work is finished.
        if math_items:
            try:
                worker = self._worker_pool.get("katex")
                substitutions = render_math_batch(
                    math_items,
                    worker=worker,
                    macros=self._katex_macros,
                    strict=self._strict_math,
                    timeout=self._katex_worker_timeout,
                )
            except WorkerError as e:
                if self._strict_math:
                    raise
                logger.warning("KaTeX batch failed, escaping: %s", e)
                substitutions = {
                    item.placeholder: html_escape_text(item.math)
                    for item in math_items
                }
            for placeholder, html in substitutions.items():
                text = text.replace(placeholder, html)

        # 9. Restore inline placeholders. Block placeholders stay as opaque
        #    sentinels so the paragraph wrapper does not try to peek inside
        #    their nested HTML (e.g. ``<div class="highlight"><pre>...``).
        text = placeholders.restore_inline(text)

        # 10. Paragraph wrapping. Insert blank lines around top-level block
        #     elements so each one gets its own paragraph slot. Block
        #     placeholders are surrounded by blank lines so each becomes a
        #     standalone paragraph that bypasses ``<p>`` wrapping.
        text = re.sub(
            r"(<(h2|h3|h4)\b[^>]*>.*?</\2>)",
            r"\n\n\1\n\n",
            text,
            flags=re.DOTALL,
        )
        text = re.sub(
            r"(<(ul|ol|blockquote|table|figure)\b[^>]*>.*?</\2>)",
            r"\n\n\1\n\n",
            text,
            flags=re.DOTALL,
        )
        for token in placeholders.block_tokens:
            text = text.replace(token, f"\n\n{token}\n\n")
        paragraphs = [
            p.strip() for p in re.split(r"\n\n+", text) if p.strip()
        ]
        if not paragraphs:
            return ""
        wrapped = "".join(
            self._wrap_paragraph(p, placeholders) for p in paragraphs
        )
        return wrapped

    _BLOCK_PREFIX_RE = re.compile(
        r"^\s*<(h2|h3|h4|ul|ol|div|blockquote|table|pre|figure)\b"
    )

    def _wrap_paragraph(
        self, text: str, placeholders: PlaceholderManager
    ) -> str:
        """Wrap inline text in ``<p>`` but emit block elements bare."""
        # Block placeholder paragraphs render their HTML directly.
        if text in placeholders.block_tokens:
            return placeholders.restore_blocks(text)
        if self._BLOCK_PREFIX_RE.match(text):
            return placeholders.restore_blocks(text)
        return f'<p class="scriba-tex-paragraph">{placeholders.restore_blocks(text)}</p>'
