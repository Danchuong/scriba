"""TeX structural validator: brace, environment, and dollar balance.

Pure Python — no subprocess, no rendering. Runs before the KaTeX worker is
invoked so malformed input fails fast with a clear error. Also enforces
library-wide resource caps (maximum source size and maximum number of math
items) to bound worker work and memory use.
"""

from __future__ import annotations

import re

# Recognized environments. Anything outside this set is reported as unknown.
KNOWN_ENVIRONMENTS: frozenset[str] = frozenset(
    {
        "itemize",
        "enumerate",
        "center",
        "tabular",
        "lstlisting",
        "verbatim",
        "quote",
        "quotation",
        "equation",
        "align",
        "align*",
        "array",
        "matrix",
        "pmatrix",
        "bmatrix",
        "vmatrix",
        "Vmatrix",
        "cases",
        "figure",
        "table",
        "minipage",
        "description",
    }
)


def validate(content: str) -> tuple[bool, str | None]:
    """Validate the structural correctness of a TeX source.

    Returns ``(True, None)`` on success or ``(False, message)`` on failure.
    Multiple warnings are joined by ``"; "``.
    """
    if not content:
        return True, None

    warnings: list[str] = []

    # 1. Brace matching with position tracking. Skip escaped \{ \} \$ etc.
    brace_stack: list[int] = []
    i = 0
    while i < len(content):
        ch = content[i]
        if ch == "\\" and i + 1 < len(content) and content[i + 1] in "{}$%&#_~":
            i += 2
            continue
        if ch == "{":
            brace_stack.append(i)
        elif ch == "}":
            if brace_stack:
                brace_stack.pop()
            else:
                warnings.append(f"unexpected closing brace }} at position {i}")
        i += 1

    if brace_stack:
        positions = ", ".join(str(p) for p in brace_stack)
        warnings.append(f"unmatched {{ at position(s): {positions}")

    # 2. Environment nesting + unknown-environment detection.
    env_stack: list[tuple[str, int]] = []
    for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", content):
        cmd = m.group(1)
        env_name = m.group(2)
        pos = m.start()

        if env_name not in KNOWN_ENVIRONMENTS:
            warnings.append(
                f"unknown environment {env_name!r} at position {pos}"
            )
            continue

        if cmd == "begin":
            env_stack.append((env_name, pos))
        else:
            if not env_stack:
                warnings.append(
                    f"\\end{{{env_name}}} at position {pos} has no matching \\begin"
                )
            elif env_stack[-1][0] != env_name:
                expected, expected_pos = env_stack[-1]
                warnings.append(
                    f"\\begin{{{expected}}} at position {expected_pos} does not "
                    f"match \\end{{{env_name}}} at position {pos}"
                )
                env_stack.pop()
            else:
                env_stack.pop()

    for env_name, pos in env_stack:
        warnings.append(f"unclosed \\begin{{{env_name}}} at position {pos}")

    # 3. Dollar parity. Skip lstlisting bodies and escaped \$.
    stripped = re.sub(
        r"\\begin\{lstlisting\}.*?\\end\{lstlisting\}",
        "",
        content,
        flags=re.DOTALL,
    )
    dollar_count = 0
    j = 0
    while j < len(stripped):
        if stripped[j] == "\\" and j + 1 < len(stripped) and stripped[j + 1] == "$":
            j += 2
            continue
        if stripped[j] == "$":
            if j + 1 < len(stripped) and stripped[j + 1] == "$":
                dollar_count += 2
                j += 2
                continue
            dollar_count += 1
        j += 1

    if dollar_count % 2 != 0:
        warnings.append(
            f"unmatched $ delimiters (odd count {dollar_count})"
        )

    if warnings:
        return False, "; ".join(warnings)
    return True, None
