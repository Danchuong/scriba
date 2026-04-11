"""TeX-suite-local helpers (snapshot loader, normalized HTML comparison).

Snapshot update policy
----------------------
Snapshot files live under ``tests/tex/snapshots/<name>.html`` and are
compared against live ``Pipeline.render(...)`` output through
``assert_snapshot_match``. An empty snapshot file is treated as
"not yet locked" and fails the test (except for ``empty_input.html``,
which legitimately represents a pipeline-empty output).

When an intentional HTML output change lands (for example, a KaTeX
version bump, a new safelisted tag, or a deliberate semantic markup
change), authors must regenerate the affected snapshots rather than
edit them by hand:

1. Delete the outdated ``tests/tex/snapshots/<name>.html`` file(s).
2. Re-run ``uv run pytest tests/tex/test_tex_snapshots.py``. Each missing
   snapshot fails loudly with the path it expected.
3. Rebuild the snapshot by running the corresponding test input through
   the ``pipeline`` fixture (for example, via a one-shot REPL session:
   ``p.render(tex, ctx).html``).
4. Sanity-check the regenerated HTML against ``docs/scriba/02-tex-plugin.md``
   §3 — verify that expected tags, classes, and text are present and
   that no sensitive or stale data leaked in.
5. Write the new HTML back to the snapshot file and re-run the suite.

Never commit a snapshot change without a short note in the PR body
explaining *why* the HTML shape changed; silent snapshot updates hide
accidental behavioural regressions.
"""

from __future__ import annotations

import re
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _normalize(html: str) -> str:
    # Strip leading/trailing whitespace per line, drop blank lines, collapse
    # runs of whitespace between tags to a single space.
    lines = [line.strip() for line in html.splitlines()]
    joined = "\n".join(line for line in lines if line)
    joined = re.sub(r">\s+<", "> <", joined)
    return joined.strip()


def assert_snapshot_match(actual_html: str, name: str) -> None:
    """Compare ``actual_html`` to ``snapshots/<name>.html``.

    Empty snapshot files are treated as not-yet-locked and raise an
    ``AssertionError`` instructing the GREEN-phase agent to populate them
    after manually reviewing the output against ``02-tex-plugin.md`` §3.
    """
    path = SNAPSHOT_DIR / f"{name}.html"
    if not path.exists():
        raise AssertionError(f"snapshot file missing: {path}")
    expected = path.read_text(encoding="utf-8")
    if expected.strip() == "" and name != "empty_input":
        raise AssertionError(
            f"snapshot empty: {name}; populate after manual review against "
            "docs/scriba/02-tex-plugin.md §3"
        )
    assert _normalize(actual_html) == _normalize(expected), (
        f"snapshot mismatch for {name}\n"
        f"--- expected ---\n{expected}\n"
        f"--- actual ---\n{actual_html}\n"
    )
