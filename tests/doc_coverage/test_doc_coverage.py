"""Doc-coverage regression suite.

Renders every ``corpus/*.tex`` snippet through the *same* pipeline path that
``render.py`` uses (``render_file``), and asserts the outcome matches the
DOCUMENTED contract recorded in the matching ``<id>.expect`` file.

See ``tests/doc_coverage/README.md`` for the corpus format and ``REPORT.md``
for the coverage tally and the catalogue of known doc/code mismatches.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

# Make the repo-root ``render.py`` importable regardless of where pytest is
# invoked from (tests run with cwd == repo root, but be defensive).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from render import render_file  # noqa: E402

from scriba.core.errors import ScribaError  # noqa: E402

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


# --------------------------------------------------------------------------- #
# Known doc/code mismatches.
#
# Each ``.expect`` holds the DOCUMENTED contract.  The ids below are cases the
# code currently violates that documentation — real findings surfaced by the
# corpus generators.  We mark them ``xfail(strict=True)`` so the suite stays
# GREEN today but a future fix that aligns code with the docs will XPASS and
# force us to remove the entry.
# --------------------------------------------------------------------------- #
# All four originally-surfaced doc/code mismatches were fixed (E1433 tree
# cycle, E1320 \hl-outside-narrate, E1012 step-label charset, E1012 env-option
# unit suffix), so there are no known-failing entries. New mismatches go here
# as {test_id: reason} to xfail(strict) them until fixed.
KNOWN_BUGS: dict[str, str] = {}


def _expected_outcome(expect_path: Path) -> tuple[str, str | None]:
    """Parse an ``.expect`` file's first line into ``(kind, code)``.

    ``kind`` is ``"ok"`` or ``"error"``; ``code`` is the ``E####`` string for
    errors, otherwise ``None``.
    """
    first_line = expect_path.read_text(encoding="utf-8").splitlines()[0].strip()
    if first_line == "ok":
        return ("ok", None)
    parts = first_line.split()
    if len(parts) == 2 and parts[0] == "error" and parts[1].startswith("E"):
        return ("error", parts[1])
    raise ValueError(f"Unparseable .expect line in {expect_path}: {first_line!r}")


def _render(tex_path: Path, tmp_path: Path) -> tuple[str, str | None]:
    """Render ``tex_path`` via the render.py pipeline.

    Returns ``("ok", None)`` on success or ``("error", "E####")`` when a coded
    Scriba exception is raised.  Unexpected exceptions propagate (test error).
    """
    output_path = tmp_path / (tex_path.stem + ".html")
    # render_file prints progress/warnings; swallow it so test output stays clean.
    sink = io.StringIO()
    try:
        with redirect_stdout(sink), redirect_stderr(sink):
            render_file(tex_path, output_path)
    except ScribaError as exc:
        return ("error", exc.code)
    return ("ok", None)


def _corpus_ids() -> list[str]:
    return sorted(p.stem for p in CORPUS_DIR.glob("*.tex"))


def _params() -> list[object]:
    params: list[object] = []
    for test_id in _corpus_ids():
        marks = []
        if test_id in KNOWN_BUGS:
            marks.append(
                pytest.mark.xfail(strict=True, reason=KNOWN_BUGS[test_id])
            )
        params.append(pytest.param(test_id, marks=marks, id=test_id))
    return params


@pytest.mark.e2e
@pytest.mark.parametrize("test_id", _params())
def test_doc_coverage(test_id: str, tmp_path: Path) -> None:
    tex_path = CORPUS_DIR / f"{test_id}.tex"
    expect_path = CORPUS_DIR / f"{test_id}.expect"

    expected_kind, expected_code = _expected_outcome(expect_path)
    actual_kind, actual_code = _render(tex_path, tmp_path)

    if expected_kind == "ok":
        assert actual_kind == "ok", (
            f"{test_id}: expected ok, got error {actual_code}"
        )
    else:
        assert actual_kind == "error", (
            f"{test_id}: expected error {expected_code}, but render succeeded"
        )
        assert actual_code == expected_code, (
            f"{test_id}: expected {expected_code}, got {actual_code}"
        )
