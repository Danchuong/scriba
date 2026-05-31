"""End-to-end CLI tests for ``render.py``.

These spawn the real CLI as a subprocess to exercise the full path:
argument parsing → boundary guards → render pipeline → file write. They
complement the in-process golden suite by covering ``main()`` itself.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RENDER_PY = _REPO_ROOT / "render.py"


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Invoke ``python render.py <args>`` with ``cwd`` as the working dir."""
    return subprocess.run(
        [sys.executable, str(_RENDER_PY), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.mark.e2e
def test_cli_renders_tex_smoke(tmp_path: Path) -> None:
    """A minimal ``.tex`` file renders to a self-contained HTML document."""
    src = tmp_path / "doc.tex"
    src.write_text("Hello $x^2$ world.\n", encoding="utf-8")

    result = _run_cli(tmp_path, "doc.tex", "-o", "doc.html")

    assert result.returncode == 0, result.stderr
    out = tmp_path / "doc.html"
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "world" in html


@pytest.mark.e2e
def test_cli_escapes_lang_flag(tmp_path: Path) -> None:
    """The operator-supplied ``--lang`` value is HTML-escaped (defense-in-depth)."""
    src = tmp_path / "doc.tex"
    src.write_text("Hi.\n", encoding="utf-8")

    result = _run_cli(
        tmp_path, "doc.tex", "-o", "doc.html", "--lang", '"><script>x</script>'
    )

    assert result.returncode == 0, result.stderr
    html = (tmp_path / "doc.html").read_text(encoding="utf-8")
    assert '<script>x</script>' not in html
    assert "&lt;script&gt;" in html


@pytest.mark.e2e
def test_cli_refuses_output_outside_cwd(tmp_path: Path) -> None:
    """H1 guard: ``-o`` pointing outside the cwd is rejected with exit 1."""
    src = tmp_path / "doc.tex"
    src.write_text("Hi.\n", encoding="utf-8")

    result = _run_cli(tmp_path, "doc.tex", "-o", "../escaped.html")

    assert result.returncode == 1
    assert "refusing to write outside cwd" in result.stderr
    assert not (tmp_path.parent / "escaped.html").exists()
