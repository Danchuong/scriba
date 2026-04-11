"""Exception hierarchy for Scriba.

See ``docs/scriba/01-architecture.md`` §Exception hierarchy.
"""

from __future__ import annotations

_DOCS_BASE_URL = "https://scriba.ojcloud.dev/errors"


class ScribaError(Exception):
    """Base exception for all Scriba failures.

    All Scriba exceptions carry an optional machine-readable ``code`` and
    a structured location (``line``/``col``). When a ``source_line`` is
    supplied the renderer prints a carat-pointer snippet beneath the
    location header for easier debugging.
    """

    code: str | None = None

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        line: int | None = None,
        col: int | None = None,
        hint: str | None = None,
        source_line: str | None = None,
    ) -> None:
        self._raw_message = message
        self.line = line
        self.col = col
        self.hint = hint
        self.source_line = source_line
        if code is not None:
            self.code = code
        super().__init__(str(self))

    def __str__(self) -> str:
        parts: list[str] = []

        # Error code prefix
        if self.code:
            parts.append(f"[{self.code}]")

        # Location
        if self.line is not None:
            loc = f"at line {self.line}"
            if self.col is not None:
                loc += f", col {self.col}"
            parts.append(loc + ":")
        elif parts:
            # Have code but no line — just append colon to code
            parts[-1] += ":"

        parts.append(self._raw_message)
        result = " ".join(parts)

        # Source snippet: when callers supply the offending source line
        # we underline the column with a carat. Keeps backward compat
        # (rendering is unchanged when source_line is None).
        if self.source_line is not None:
            snippet = self.source_line.rstrip("\n")
            result += f"\n      {snippet}"
            if self.col is not None and self.col >= 0:
                # Render a carat pointer under the offending column.
                # ``col`` is 0-indexed relative to source_line.
                result += "\n      " + (" " * self.col) + "^"

        # Hint
        if self.hint:
            result += f"\n  hint: {self.hint}"

        # Docs URL
        if self.code:
            result += f"\n  -> {_DOCS_BASE_URL}/{self.code}"

        return result


class RendererError(ScribaError):
    """Raised by a Renderer when render_block() cannot produce output."""

    def __init__(
        self,
        message: str,
        *,
        renderer: str | None = None,
        code: str | None = None,
        line: int | None = None,
        col: int | None = None,
        hint: str | None = None,
        source_line: str | None = None,
    ) -> None:
        self.renderer = renderer
        super().__init__(
            message,
            code=code,
            line=line,
            col=col,
            hint=hint,
            source_line=source_line,
        )


class WorkerError(ScribaError):
    """Raised when a subprocess worker fails (crash, timeout, bad JSON)."""

    def __init__(
        self,
        message: str,
        *,
        stderr: str | None = None,
        code: str | None = None,
        line: int | None = None,
        col: int | None = None,
        hint: str | None = None,
        source_line: str | None = None,
    ) -> None:
        self.stderr = stderr
        super().__init__(
            message,
            code=code,
            line=line,
            col=col,
            hint=hint,
            source_line=source_line,
        )


class ScribaRuntimeError(ScribaError):
    """Raised when a required external runtime dependency is missing or broken.

    Typical causes: ``node`` not on PATH, or the ``katex`` npm module cannot
    be resolved by the Node.js runtime that Scriba will spawn.
    """

    def __init__(
        self,
        message: str,
        *,
        component: str | None = None,
        code: str | None = None,
        line: int | None = None,
        col: int | None = None,
        hint: str | None = None,
        source_line: str | None = None,
    ) -> None:
        self.component = component
        super().__init__(
            message,
            code=code,
            line=line,
            col=col,
            hint=hint,
            source_line=source_line,
        )


class ValidationError(ScribaError):
    """Raised on structurally invalid input (NUL bytes, unmatched braces)."""

    def __init__(
        self,
        message: str,
        *,
        position: int | None = None,
        code: str | None = None,
        line: int | None = None,
        col: int | None = None,
        hint: str | None = None,
        source_line: str | None = None,
    ) -> None:
        self.position = position
        super().__init__(
            message,
            code=code,
            line=line,
            col=col,
            hint=hint,
            source_line=source_line,
        )
