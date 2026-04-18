"""Test that ScribaError is caught in main() and does not produce a raw traceback.

Wave 8 Round A — P1 F-01 regression guard.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


def _render_py() -> str:
    """Return the absolute path to render.py."""
    return str(Path(__file__).parent.parent.parent / "render.py")


def _run(tex_source: str, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    """Write tex_source to a temp file, run render.py on it, capture output."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".tex", mode="w", delete=False, encoding="utf-8") as f:
        f.write(tex_source)
        tmp_path = f.name

    cmd = [sys.executable, _render_py(), tmp_path] + (extra_args or [])
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Clean up temp files
    for p in [tmp_path, tmp_path.replace(".tex", ".html")]:
        try:
            Path(p).unlink()
        except FileNotFoundError:
            pass

    return result


# ---------------------------------------------------------------------------
# F-01: ScribaError should NOT produce a traceback, exit code should be 2
# ---------------------------------------------------------------------------

_BAD_TEX = textwrap.dedent(r"""
    \begin{animation}[id=test]
    \shape{arr}{Array}{}
    \end{animation}
""")
# This is invalid because Array requires size= or n= parameter → E1400


def test_scriba_error_no_traceback():
    """A ScribaError must not leak a Python traceback on stderr."""
    result = _run(_BAD_TEX)
    # Should not see 'Traceback (most recent call last)'
    assert "Traceback (most recent call last)" not in result.stderr, (
        f"Raw traceback leaked to stderr:\n{result.stderr}"
    )


def test_scriba_error_exit_code():
    """A ScribaError must exit with code 2 (user input fault)."""
    result = _run(_BAD_TEX)
    assert result.returncode == 2, (
        f"Expected exit 2 for ScribaError, got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )


def test_scriba_error_message_on_stderr():
    """The formatted error message must appear on stderr."""
    result = _run(_BAD_TEX)
    assert "error" in result.stderr.lower(), (
        f"Expected 'error' in stderr, got:\n{result.stderr}"
    )


def test_scriba_debug_reraises():
    """With SCRIBA_DEBUG=1, the full traceback should be visible."""
    import os
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".tex", mode="w", delete=False, encoding="utf-8") as f:
        f.write(_BAD_TEX)
        tmp_path = f.name

    env = os.environ.copy()
    env["SCRIBA_DEBUG"] = "1"
    result = subprocess.run(
        [sys.executable, _render_py(), tmp_path],
        capture_output=True,
        text=True,
        env=env,
    )
    for p in [tmp_path, tmp_path.replace(".tex", ".html")]:
        try:
            Path(p).unlink()
        except FileNotFoundError:
            pass

    assert "Traceback" in result.stderr, (
        "Expected traceback in debug mode, got:\n" + result.stderr
    )


def test_file_not_found_exits_1():
    """Missing input file must exit 1 with an error message on stderr."""
    result = subprocess.run(
        [sys.executable, _render_py(), "nonexistent_file_xyz.tex"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "error" in result.stderr.lower()
    assert "Traceback" not in result.stderr
