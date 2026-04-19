"""E2E test fixtures.

Rebuilds the ``examples/quickstart/hello.html`` artifact once per session
so the rendered output reflects the current code under test (not a stale
checked-in HTML file).  Tests then load it via ``file://`` URL — Scriba is
a static HTML generator, no dev server required.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HELLO_TEX = ROOT / "examples" / "quickstart" / "hello.tex"
HELLO_HTML = ROOT / "examples" / "quickstart" / "hello.html"


@pytest.fixture(scope="session")
def hello_html_url() -> str:
    """Build hello.html and return a file:// URL for Playwright to load."""
    if not HELLO_TEX.exists():
        pytest.skip(f"missing fixture source: {HELLO_TEX}")
    subprocess.run(
        ["uv", "run", "python", "render.py", str(HELLO_TEX), "-o", str(HELLO_HTML)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    return HELLO_HTML.as_uri()
