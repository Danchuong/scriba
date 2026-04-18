"""Inline text-style commands and the nine size commands.

See ``docs/scriba/02-tex-plugin.md`` §3 for the HTML output contract.

Note: :func:`apply_text_commands` and its helpers were moved to
:mod:`scriba.core.text_utils` in v0.9.0 to fix a cross-layer import
violation. They are re-exported here so that existing callers of
``scriba.tex.parser.text_commands.apply_text_commands`` continue to work.
"""

from __future__ import annotations

import re

# Re-export from canonical location in scriba.core.
from scriba.core.text_utils import (  # noqa: F401
    _BRACE_COMMANDS,
    _replace_balanced,
    apply_text_commands,
)

# Nine size commands → CSS class names. Order matters: longer names first
# so the regex does not match e.g. ``\Large`` while looking for ``\large``.
SIZE_COMMANDS: tuple[str, ...] = (
    "scriptsize",
    "normalsize",
    "LARGE",
    "Large",
    "large",
    "Huge",
    "huge",
    "small",
    "tiny",
)


def apply_size_commands(text: str) -> str:
    """Convert size commands to ``<span class="scriba-tex-size-...">``.

    Two forms supported:

    1. Brace form: ``\\large{X}`` → ``<span class="scriba-tex-size-large">X</span>``
    2. Switch form: trailing run of text after the bare command, terminated
       by another size command, end-of-string, or another backslash command.
    """
    # Brace form first (handles e.g. ``\large{stuff}``).
    for cmd in SIZE_COMMANDS:
        cls = f"scriba-tex-size-{cmd}"
        text = _replace_balanced(text, cmd, f'<span class="{cls}">', "</span>")

    # Switch form: ``\large foo`` consumes ``foo`` until the next size cmd
    # or another backslash command. Implemented as one combined regex over
    # all nine commands so order isn't fragile.
    #
    # NOTE: The [^\\] in the body group stops at ANY backslash, not just
    # known TeX commands. This is intentional — by the time size commands
    # run, text commands (\\textbf, \\emph, etc.) have already been expanded
    # to HTML tags (which use ``<``/``>`` not ``\``). So any remaining ``\``
    # genuinely marks the start of another TeX command and is a correct
    # termination point.
    cmd_alt = "|".join(re.escape(c) for c in SIZE_COMMANDS)
    switch_re = re.compile(
        r"\\(" + cmd_alt + r")\b\s*"
        r"((?:(?!\\(?:" + cmd_alt + r")\b)[^\\])*)"
    )

    def _switch_sub(m: re.Match[str]) -> str:
        cmd = m.group(1)
        body = m.group(2).rstrip()
        cls = f"scriba-tex-size-{cmd}"
        return f'<span class="{cls}">{body}</span>'

    return switch_re.sub(_switch_sub, text)
