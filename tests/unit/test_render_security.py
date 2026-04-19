"""Unit tests for security fixes in scriba/cli.py (formerly render.py).

C2 — XSS via filename in <title> and <h1>  (scriba/cli.py)
H1 — Path traversal via -o flag            (scriba/cli.py)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_render_file_patcher():
    """Return a patcher that stubs out the heavy rendering pipeline so
    render_file() can be called in unit tests without a real TeX install."""
    return patch("scriba.cli.render_file", return_value=None)


# ---------------------------------------------------------------------------
# C2 — XSS via filename
# ---------------------------------------------------------------------------

class TestXSSEscaping:
    """html.escape() must be applied to input_path.stem before it reaches
    the HTML template (both <title> and <h1>)."""

    def test_plain_filename_unchanged(self, tmp_path: Path) -> None:
        """Normal filenames must not be mangled by escaping."""
        import html as html_module
        stem = "tutorial_en"
        assert html_module.escape(stem) == stem

    def test_angle_brackets_escaped(self, tmp_path: Path) -> None:
        """A filename containing < > must be escaped to &lt; &gt;."""
        import html as html_module
        stem = "<img src=x onerror=alert(1)>"
        escaped = html_module.escape(stem)
        assert "<img" not in escaped
        assert "&lt;img" in escaped

    def test_render_file_calls_html_escape_on_stem(self, tmp_path: Path) -> None:
        """render_file() must call html.escape() on input_path.stem.

        We spy on scriba.cli.html.escape and assert it is called with the raw stem.
        Coupled with test_angle_brackets_escaped above, this proves the XSS
        payload would be neutralised before reaching the template.
        """
        import scriba.cli as cli_mod  # noqa: PLC0415
        import html as stdlib_html

        malicious_stem = "<img src=x onerror=alert(1)>"
        escape_calls: list[str] = []
        original_escape = stdlib_html.escape

        def _spy_escape(s: str, quote: bool = True) -> str:
            escape_calls.append(s)
            return original_escape(s, quote)

        mock_input = MagicMock()
        mock_input.stem = malicious_stem
        mock_input.read_text.return_value = ""  # empty → no blocks, no TeX gaps
        mock_input.parent = tmp_path

        output_file = tmp_path / "out.html"

        with patch("scriba.cli.html.escape", side_effect=_spy_escape), \
             patch("scriba.cli.AnimationRenderer"), \
             patch("scriba.cli.StarlarkHost"), \
             patch("scriba.cli.SubprocessWorkerPool"), \
             patch("scriba.cli.TexRenderer") as mock_tex_cls, \
             patch("scriba.animation.detector.detect_animation_blocks", return_value=[]), \
             patch("scriba.animation.detector.detect_diagram_blocks", return_value=[]), \
             patch("scriba.cli.load_css", return_value=""), \
             patch("scriba.cli.inline_katex_css", return_value=""):
            mock_tex = mock_tex_cls.return_value
            mock_tex.render_inline_text.side_effect = lambda t: t
            cli_mod.render_file(mock_input, output_file)

        assert malicious_stem in escape_calls, (
            f"html.escape() was not called with the malicious stem {malicious_stem!r}. "
            f"Called with: {escape_calls}"
        )

    @pytest.mark.unit
    def test_ampersand_and_quotes_escaped(self) -> None:
        """Filenames with & and quotes are also escaped correctly."""
        import html as html_module
        for stem, expected_fragment in [
            ('foo&bar', 'foo&amp;bar'),
            ('"quoted"', '&quot;quoted&quot;'),
        ]:
            assert expected_fragment in html_module.escape(stem, quote=True)


# ---------------------------------------------------------------------------
# H1 — Path traversal via -o flag
# ---------------------------------------------------------------------------

class TestPathTraversal:
    """The -o / --output argument must be constrained to CWD unless
    SCRIBA_ALLOW_ANY_OUTPUT=1 is set."""

    def _run_main_with_args(
        self,
        tmp_path: Path,
        output_arg: str,
        env: dict[str, str] | None = None,
    ) -> int:
        """Call scriba.cli.main() with a synthetic argv and return the SystemExit code."""
        tex = tmp_path / "input.tex"
        tex.write_text("Hello.")

        argv = ["scriba", str(tex), "-o", output_arg]

        extra_env = dict(os.environ)
        extra_env.pop("SCRIBA_ALLOW_ANY_OUTPUT", None)
        if env:
            extra_env.update(env)

        with patch("sys.argv", argv), \
             patch.dict(os.environ, extra_env, clear=True), \
             patch("scriba.cli.render_file", return_value=None):
            import scriba.cli as cli_mod  # noqa: PLC0415
            try:
                cli_mod.main()
                return 0
            except SystemExit as exc:
                return int(exc.code) if exc.code is not None else 0

    @pytest.mark.unit
    def test_outside_cwd_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Passing -o /tmp/escape.html from a non-/tmp CWD must exit 1."""
        monkeypatch.chdir(tmp_path)
        outside = "/tmp/scriba_unit_test_escape.html"
        code = self._run_main_with_args(tmp_path, outside)
        assert code == 1

    @pytest.mark.unit
    def test_outside_cwd_error_message(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """The rejection message must contain 'refusing to write outside cwd'."""
        monkeypatch.chdir(tmp_path)
        outside = "/tmp/scriba_unit_test_escape.html"
        self._run_main_with_args(tmp_path, outside)
        captured = capsys.readouterr()
        assert "refusing to write outside cwd" in captured.err

    @pytest.mark.unit
    def test_inside_cwd_accepted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Passing -o <cwd>/out.html must succeed (exit 0)."""
        monkeypatch.chdir(tmp_path)
        inside = str(tmp_path / "out.html")
        code = self._run_main_with_args(tmp_path, inside)
        assert code == 0

    @pytest.mark.unit
    def test_env_var_opt_out_allows_outside_cwd(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SCRIBA_ALLOW_ANY_OUTPUT=1 must permit writing outside CWD (exit 0)."""
        monkeypatch.chdir(tmp_path)
        outside = "/tmp/scriba_unit_test_optout.html"
        code = self._run_main_with_args(
            tmp_path, outside, env={"SCRIBA_ALLOW_ANY_OUTPUT": "1"}
        )
        assert code == 0

    @pytest.mark.unit
    def test_no_output_flag_skips_check(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When -o is omitted the path traversal check is not applied."""
        monkeypatch.chdir(tmp_path)
        tex = tmp_path / "input.tex"
        tex.write_text("Hello.")
        # Default output (same dir as input) is always inside cwd; must not fail.
        with patch("sys.argv", ["scriba", str(tex)]), \
             patch.dict(os.environ, {}, clear=False), \
             patch("scriba.cli.render_file", return_value=None):
            import scriba.cli as cli_mod  # noqa: PLC0415
            try:
                cli_mod.main()
                code = 0
            except SystemExit as exc:
                code = int(exc.code) if exc.code is not None else 0
        assert code == 0

    @pytest.mark.unit
    def test_symlink_escape_rejected(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A symlink whose resolved path exits CWD must also be rejected.

        Path.resolve() follows symlinks, so .relative_to(cwd) will still
        catch symlink-based traversal attempts.
        """
        monkeypatch.chdir(tmp_path)
        link = tmp_path / "escape_link.html"
        try:
            link.symlink_to("/tmp/scriba_symlink_target.html")
        except OSError:
            pytest.skip("Cannot create symlink on this platform")

        code = self._run_main_with_args(tmp_path, str(link))
        # /tmp resolves outside tmp_path — should be rejected on macOS
        # (where /tmp -> /private/tmp, which is not under tmp_path).
        resolved = link.resolve()
        cwd = tmp_path.resolve()
        try:
            resolved.relative_to(cwd)
            # If the resolved path is somehow still within CWD, skip assertion
        except ValueError:
            assert code == 1
