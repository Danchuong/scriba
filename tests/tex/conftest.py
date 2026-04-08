"""TeX-suite-local helpers (snapshot loader, normalized HTML comparison)."""

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
