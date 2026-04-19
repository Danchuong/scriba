"""Regression tests for audit finding P1 — path traversal in _resolve_resource().

Audit finding: render.py lines 98-105.
Bug: ``candidate = input_dir / name`` performs no bounds check.
     A name like ``../../etc/passwd`` resolves outside ``input_dir`` and
     gets read + base64-encoded into the output HTML, leaking arbitrary
     files from the server filesystem.

Fix required: after resolving ``candidate``, assert that
``candidate.resolve()`` is a descendant of ``input_dir.resolve()``.
If the resolved path escapes, refuse to read the file and fall back to
the ``/static/<name>`` URL (exactly as if the file did not exist).

These tests call the current (unfixed) ``_resolve_resource`` directly and
assert the desired post-fix behaviour.  They will FAIL (RED) against the
current code and PASS once the fix is applied.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

# ``_resolve_resource`` is a module-level private function in render.py.
# We import it directly; if the function is later moved/renamed the import
# path must be updated together with the fix.
from render import _resolve_resource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a small directory tree for traversal tests.

    Returns
    -------
    input_dir : Path
        The simulated per-document input directory passed to
        ``_resolve_resource`` as ``input_dir``.
    secret_file : Path
        A file that lives *outside* ``input_dir`` (one level up).
    inside_file : Path
        A legitimate resource inside ``input_dir``.
    """
    input_dir = tmp_path / "project"
    input_dir.mkdir()

    secret_file = tmp_path / "secret.png"
    secret_file.write_bytes(b"\x89PNG\r\nSensitive data outside project dir")

    inside_file = input_dir / "logo.png"
    inside_file.write_bytes(b"\x89PNG\r\nLegitimate image data")

    return input_dir, secret_file, inside_file


# ---------------------------------------------------------------------------
# P1 — Tests that FAIL today (RED phase)
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestPathTraversalBlocked:
    """_resolve_resource() must refuse to read files outside input_dir.

    Audit finding P1: the fix must compare candidate.resolve() against
    input_dir.resolve() and return the /static/ fallback when the path
    escapes the sandbox.
    """

    def test_single_dotdot_segment_is_blocked(self, tmp_path: Path) -> None:
        """``../secret.png`` resolves outside input_dir and must be refused.

        Expected post-fix behaviour: return ``/static/../secret.png`` (the
        unresolved fallback URL) instead of reading the file.

        Fails today because _resolve_resource performs no bounds check.
        """
        input_dir, secret_file, _ = _make_tree(tmp_path)

        result = _resolve_resource(input_dir, "../secret.png")

        assert not result.startswith("data:"), (
            "_resolve_resource read a file outside input_dir via '../secret.png'. "
            "Expected a /static/ fallback URL but got a data URI."
        )

    def test_double_dotdot_segment_is_blocked(self, tmp_path: Path) -> None:
        """``../../etc/passwd``-style traversal must be refused.

        Even when no such file exists on this machine, the logic must still
        apply the path-bounds check *before* calling ``is_file()``.
        """
        input_dir = tmp_path / "a" / "b"
        input_dir.mkdir(parents=True)

        # Create a file two levels up to prove the traversal would read it.
        target = tmp_path / "canary.txt"
        target.write_text("CANARY")

        result = _resolve_resource(input_dir, "../../canary.txt")

        assert not result.startswith("data:"), (
            "_resolve_resource resolved '../../canary.txt' outside input_dir "
            "and returned a data URI. Expected a /static/ fallback."
        )

    def test_traversal_with_intermediate_valid_dir(self, tmp_path: Path) -> None:
        """``subdir/../../secret.png`` also escapes and must be refused.

        A traversal that first descends into a valid subdirectory and then
        climbs back out must still be caught.
        """
        input_dir, secret_file, _ = _make_tree(tmp_path)
        (input_dir / "subdir").mkdir(exist_ok=True)

        result = _resolve_resource(input_dir, "subdir/../../secret.png")

        assert not result.startswith("data:"), (
            "_resolve_resource followed a 'subdir/../../' path and read a file "
            "outside input_dir. Expected a /static/ fallback."
        )

    def test_absolute_path_is_blocked(self, tmp_path: Path) -> None:
        """An absolute path that escapes input_dir must be refused.

        ``input_dir / '/etc/passwd'`` on POSIX discards the input_dir
        prefix and resolves directly to ``/etc/passwd``.  The fix must
        detect that the result is not under input_dir.
        """
        input_dir, _, _ = _make_tree(tmp_path)

        # Use a file that actually exists on most POSIX systems.
        result = _resolve_resource(input_dir, "/etc/hosts")

        # We assert either: the file was not read (data: URI absent), or
        # the path was not under input_dir (static fallback returned).
        assert not result.startswith("data:"), (
            "_resolve_resource resolved an absolute path '/etc/hosts' and "
            "returned a data URI. Expected a /static/ fallback."
        )

    # ------------------------------------------------------------------
    # Negative: legitimate files INSIDE input_dir must still be served.
    # ------------------------------------------------------------------

    def test_legitimate_resource_inside_input_dir_is_served(
        self, tmp_path: Path
    ) -> None:
        """A file that genuinely resides inside input_dir must still be encoded.

        This test must PASS both before and after the fix — it is the
        non-regression guard that confirms the fix does not over-block.
        """
        input_dir, _, inside_file = _make_tree(tmp_path)

        result = _resolve_resource(input_dir, "logo.png")

        assert result.startswith("data:image/png;base64,"), (
            "_resolve_resource failed to serve a legitimate file inside input_dir. "
            f"Got: {result!r}"
        )
        # Verify the actual bytes are present
        encoded_part = result.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        assert b"Legitimate image data" in decoded

    def test_dotdot_does_not_return_data_uri_of_outside_file(
        self, tmp_path: Path
    ) -> None:
        """Cross-check: the returned value must not contain the secret content.

        Even if the path check is absent, the data URI must not encode the
        sensitive file's bytes.
        """
        input_dir, secret_file, _ = _make_tree(tmp_path)

        result = _resolve_resource(input_dir, "../secret.png")

        if result.startswith("data:"):
            # If it is a data URI, make sure it is NOT the secret file
            encoded_part = result.split(",", 1)[1]
            decoded = base64.b64decode(encoded_part)
            assert b"Sensitive data outside project dir" not in decoded, (
                "_resolve_resource encoded the secret file's content into the "
                "output. This is a path-traversal vulnerability."
            )
