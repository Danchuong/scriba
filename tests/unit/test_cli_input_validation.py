"""Tests for Wave 8 Round B CLI ergonomics fixes (F-02 through F-06).

Each test targets one finding from docs/archive/scriba-wave8-audit-2026-04-18/01-cli-ergonomics.md.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _render_py() -> str:
    return str(Path(__file__).parent.parent.parent / "render.py")


def _run(
    tex_source: str,
    extra_args: list[str] | None = None,
    input_suffix: str = ".tex",
) -> subprocess.CompletedProcess:
    """Write tex_source to a temp file and run render.py on it."""
    with tempfile.NamedTemporaryFile(
        suffix=input_suffix, mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(tex_source)
        tmp_path = f.name

    cmd = [sys.executable, _render_py(), tmp_path] + (extra_args or [])
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Clean up temp files (both .tex and any .html output)
    for p in [tmp_path, tmp_path.replace(input_suffix, ".html")]:
        try:
            Path(p).unlink()
        except FileNotFoundError:
            pass

    return result


_PLAIN_TEX = r"Hello world, no animation block here."
_SIMPLE_ANIM = (
    r"\begin{animation}[id=test]" + "\n"
    r"\shape{a}{Array}{size=3}" + "\n"
    r"\step" + "\n"
    r"\end{animation}"
)


# ---------------------------------------------------------------------------
# F-02: all error/warning messages go to stderr
# ---------------------------------------------------------------------------

class TestF02StderrMessages:
    """Error and warning messages must not appear on stdout."""

    def test_file_not_found_on_stderr(self):
        result = subprocess.run(
            [sys.executable, _render_py(), "nonexistent_xyz_123.tex"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr.lower() or "error" in result.stderr.lower()
        assert "not found" not in result.stdout.lower()

    def test_file_not_found_not_on_stdout(self):
        result = subprocess.run(
            [sys.executable, _render_py(), "nonexistent_xyz_123.tex"],
            capture_output=True,
            text=True,
        )
        # stdout should be empty (no diagnostic leaking there)
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# F-03: wrong file extension
# ---------------------------------------------------------------------------

class TestF03WrongExtension:
    """Clearly wrong extensions must exit 2; unknown non-.tex extensions warn."""

    @pytest.mark.parametrize("ext", [".pdf", ".docx", ".html", ".doc", ".rtf"])
    def test_clearly_wrong_extension_exits_2(self, ext: str):
        result = _run(_PLAIN_TEX, input_suffix=ext)
        assert result.returncode == 2, (
            f"Expected exit 2 for {ext!r}, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    @pytest.mark.parametrize("ext", [".pdf", ".docx", ".html"])
    def test_clearly_wrong_extension_message_on_stderr(self, ext: str):
        result = _run(_PLAIN_TEX, input_suffix=ext)
        assert "error" in result.stderr.lower(), (
            f"Expected error message on stderr for {ext!r}, got: {result.stderr}"
        )

    @pytest.mark.parametrize("ext", [".pdf", ".docx", ".html"])
    def test_clearly_wrong_extension_nothing_on_stdout(self, ext: str):
        result = _run(_PLAIN_TEX, input_suffix=ext)
        assert result.stdout.strip() == "", (
            f"Expected no stdout for wrong extension {ext!r}, got: {result.stdout}"
        )

    def test_unknown_extension_warns_but_continues(self):
        """A .txt file should warn on stderr but still attempt rendering (exit 0)."""
        result = _run(_PLAIN_TEX, input_suffix=".txt")
        assert result.returncode == 0, (
            f"Expected exit 0 for .txt, got {result.returncode}.\nstderr: {result.stderr}"
        )
        assert "warning" in result.stderr.lower(), (
            f"Expected a warning on stderr for .txt, got: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# F-04: no \begin{animation} block — must warn on stderr
# ---------------------------------------------------------------------------

class TestF04NoAnimationBlock:
    """Plain .tex with no animation block must emit a warning on stderr."""

    def test_no_animation_block_warns_on_stderr(self):
        result = _run(_PLAIN_TEX)
        assert result.returncode == 0, (
            f"Expected exit 0 for plain TeX, got {result.returncode}.\nstderr: {result.stderr}"
        )
        assert "warning" in result.stderr.lower(), (
            f"Expected warning on stderr, got:\n{result.stderr}"
        )
        assert "animation" in result.stderr.lower(), (
            f"Expected 'animation' in warning message, got:\n{result.stderr}"
        )

    def test_file_with_animation_block_no_spurious_warning(self):
        result = _run(_SIMPLE_ANIM)
        # The warning must NOT appear when there's a valid animation block
        assert "no \\begin{animation}" not in result.stderr
        assert "did you forget" not in result.stderr.lower()


# ---------------------------------------------------------------------------
# F-05: --output would overwrite input file
# ---------------------------------------------------------------------------

class TestF05OutputOverwritesInput:
    """--output resolving to the same path as input must exit 2."""

    def test_output_equals_input_exits_2(self):
        with tempfile.NamedTemporaryFile(
            suffix=".tex", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(_PLAIN_TEX)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, _render_py(), tmp_path, "-o", tmp_path],
                capture_output=True,
                text=True,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        assert result.returncode == 2, (
            f"Expected exit 2 for output==input, got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    def test_output_equals_input_error_on_stderr(self):
        with tempfile.NamedTemporaryFile(
            suffix=".tex", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(_PLAIN_TEX)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, _render_py(), tmp_path, "-o", tmp_path],
                capture_output=True,
                text=True,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        assert "overwrite" in result.stderr.lower() or "error" in result.stderr.lower(), (
            f"Expected overwrite error on stderr, got:\n{result.stderr}"
        )

    def test_output_different_file_allowed(self):
        with (
            tempfile.NamedTemporaryFile(
                suffix=".tex", mode="w", delete=False, encoding="utf-8"
            ) as fin,
            tempfile.NamedTemporaryFile(
                suffix=".html", delete=False
            ) as fout,
        ):
            fin.write(_PLAIN_TEX)
            tmp_in = fin.name
            tmp_out = fout.name

        try:
            result = subprocess.run(
                [sys.executable, _render_py(), tmp_in, "-o", tmp_out],
                capture_output=True,
                text=True,
            )
        finally:
            for p in [tmp_in, tmp_out]:
                Path(p).unlink(missing_ok=True)

        # Should not exit 2 due to the collision guard
        assert result.returncode != 2 or "overwrite" not in result.stderr.lower()


# ---------------------------------------------------------------------------
# F-06: E1116 undeclared shape must raise AnimationError (exit 2), not warn
# ---------------------------------------------------------------------------

class TestF06E1116Promoted:
    """E1116 must propagate as AnimationError, not a suppressed UserWarning."""

    _UNDECLARED_SHAPE_TEX = (
        r"\begin{animation}[id=teste1116]" + "\n"
        r"\shape{a}{Array}{size=3}" + "\n"
        r"\step" + "\n"
        r"\apply{barbar.cell[0]}{value=1}" + "\n"  # 'barbar' never declared
        r"\step" + "\n"
        r"\end{animation}"
    )

    def test_undeclared_shape_exits_nonzero(self):
        result = _run(self._UNDECLARED_SHAPE_TEX)
        assert result.returncode != 0, (
            "Expected non-zero exit for undeclared shape reference.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_undeclared_shape_exits_2(self):
        result = _run(self._UNDECLARED_SHAPE_TEX)
        assert result.returncode == 2, (
            f"Expected exit 2 (ScribaError), got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )

    def test_undeclared_shape_e1116_on_stderr(self):
        result = _run(self._UNDECLARED_SHAPE_TEX)
        assert "E1116" in result.stderr, (
            f"Expected E1116 in stderr, got:\n{result.stderr}"
        )

    def test_undeclared_shape_no_traceback(self):
        result = _run(self._UNDECLARED_SHAPE_TEX)
        assert "Traceback (most recent call last)" not in result.stderr, (
            f"Raw Python traceback leaked:\n{result.stderr}"
        )

    def test_undeclared_shape_no_userwarning(self):
        """Must not surface as a Python UserWarning (which can be suppressed)."""
        result = _run(self._UNDECLARED_SHAPE_TEX)
        assert "UserWarning" not in result.stderr, (
            f"E1116 still surfacing as UserWarning:\n{result.stderr}"
        )

    def test_highlight_undeclared_shape_exits_2(self):
        tex = (
            r"\begin{animation}[id=hle1116]" + "\n"
            r"\shape{a}{Array}{size=3}" + "\n"
            r"\step" + "\n"
            r"\highlight{ghost.cell[0]}" + "\n"  # 'ghost' never declared
            r"\step" + "\n"
            r"\end{animation}"
        )
        result = _run(tex)
        assert result.returncode == 2
        assert "E1116" in result.stderr

    def test_annotate_undeclared_shape_exits_2(self):
        tex = (
            r"\begin{animation}[id=anne1116]" + "\n"
            r"\shape{a}{Array}{size=3}" + "\n"
            r"\step" + "\n"
            r"\annotate{ghost.cell[0]}{oops}" + "\n"  # 'ghost' never declared
            r"\step" + "\n"
            r"\end{animation}"
        )
        result = _run(tex)
        assert result.returncode == 2
        assert "E1116" in result.stderr
