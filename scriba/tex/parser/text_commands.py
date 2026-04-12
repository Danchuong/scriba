"""Inline text-style commands and the nine size commands.

See ``docs/scriba/02-tex-plugin.md`` §3 for the HTML output contract.
"""

from __future__ import annotations

import re

# (command, opening tag, closing tag) — wrapped via balanced-brace expansion
# repeated until no further matches are found, so nesting works.
_BRACE_COMMANDS: tuple[tuple[str, str, str], ...] = (
    ("textbf", "<strong>", "</strong>"),
    ("textit", "<em>", "</em>"),
    ("emph", "<em>", "</em>"),
    ("texttt", '<code class="scriba-tex-code-inline">', "</code>"),
    ("underline", "<u>", "</u>"),
    ("sout", "<s>", "</s>"),
    ("textsc", '<span class="scriba-tex-smallcaps">', "</span>"),
    # Old Polygon-style aliases.
    ("bf", "<strong>", "</strong>"),
    ("it", "<em>", "</em>"),
    ("tt", '<code class="scriba-tex-code-inline">', "</code>"),
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


def _replace_balanced(text: str, command: str, open_tag: str, close_tag: str) -> str:
    """Replace ``\\command{...}`` with ``open_tag...close_tag`` recursively.

    The brace body itself may contain further commands so we keep iterating
    until a fixed point is reached.
    """
    pattern = re.compile(r"\\" + re.escape(command) + r"\{")
    while True:
        m = pattern.search(text)
        if not m:
            return text
        start = m.start()
        body_start = m.end()
        depth = 1
        i = body_start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            # Unbalanced — leave as-is and stop scanning to avoid infinite loop.
            return text
        body = text[body_start:i]
        text = text[:start] + open_tag + body + close_tag + text[i + 1 :]


def apply_text_commands(text: str) -> str:
    """Convert ``\\textbf{...}`` and friends to inline HTML."""
    for command, open_tag, close_tag in _BRACE_COMMANDS:
        text = _replace_balanced(text, command, open_tag, close_tag)
    return text


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
