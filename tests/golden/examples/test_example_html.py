"""Golden regression test for the rendered example corpus.

``tests/golden/examples/corpus/`` holds a self-contained, version-controlled
snapshot of the example pairs: every ``<name>.tex`` ships with its expected
``<name>.html``. Rendering the ``.tex`` through ``render.py`` must reproduce
the committed ``.html`` byte-for-byte. This locks the current ``.tex -> .html``
rendering behaviour so a refactor cannot silently change output.

The corpus is owned by the tests (kept here, not in ``examples/`` where the
HTML is a gitignored build artifact), so the baseline survives clones and CI.

Each example is rendered in its **own subprocess** (mirroring real CLI usage).
In-process batch rendering leaks global state between examples and produces
spurious diffs; subprocess isolation matches the committed output for all
pinned examples. To stay fast, all examples are rendered concurrently in a
session-scoped fixture (threads blocking on subprocesses), then each test just
compares bytes.

Usage:
    pytest tests/golden/examples/ -v

Refresh the corpus from examples/ (when example .tex files change):
    python tests/golden/examples/sync_corpus.py

Update the golden .html in place (human review the diff before committing!):
    SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/ -v
"""
from __future__ import annotations

import difflib
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_CORPUS = _HERE / "corpus"
_REPO_ROOT = _HERE.parents[2]
_RENDER = _REPO_ROOT / "render.py"
_UPDATE = os.environ.get("SCRIBA_UPDATE_GOLDEN") == "1"


def _iter_pairs() -> list[tuple[Path, Path]]:
    """Every ``.tex`` in the corpus that has a sibling ``.html`` golden."""
    return [
        (tex, tex.with_suffix(".html"))
        for tex in sorted(_CORPUS.glob("*.tex"))
        if tex.with_suffix(".html").exists()
    ]


def _pair_id(pair: tuple[Path, Path]) -> str:
    return pair[0].stem


_PAIRS = _iter_pairs()


def _render(tex: Path, out: Path) -> None:
    """Render ``tex`` to ``out`` in an isolated subprocess."""
    env = {**os.environ, "SCRIBA_ALLOW_ANY_OUTPUT": "1"}
    result = subprocess.run(
        [sys.executable, str(_RENDER), str(tex), "-o", str(out)],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"render.py failed for {tex} (exit {result.returncode}):\n{result.stderr}"
        )


@pytest.fixture(scope="session")
def rendered() -> dict[str, bytes | Exception]:
    """Render the whole corpus concurrently once; return {id: bytes | error}.

    Subprocess renders are I/O-bound from the pool's view (each thread blocks
    on its subprocess), so a thread pool gives full parallelism across cores
    without a new dependency. Each example still gets its own process, so the
    global-state leak that affects in-process batch rendering never applies.
    """
    workers = min(len(_PAIRS), (os.cpu_count() or 4))

    def _one(pair: tuple[Path, Path]) -> tuple[str, bytes | Exception]:
        tex, _ = pair
        try:
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "out.html"
                _render(tex, out)
                return _pair_id(pair), out.read_bytes()
        except Exception as exc:  # surfaced per-test below
            return _pair_id(pair), exc

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(_one, _PAIRS))


@pytest.mark.slow
@pytest.mark.parametrize("pair", _PAIRS, ids=[_pair_id(p) for p in _PAIRS])
def test_example_matches_golden(
    pair: tuple[Path, Path], rendered: dict[str, bytes | Exception]
) -> None:
    tex, golden = pair

    if _UPDATE:
        _render(tex, golden)
        pytest.skip(f"regenerated golden: {_pair_id(pair)}")

    actual = rendered[_pair_id(pair)]
    if isinstance(actual, Exception):
        raise actual

    expected = golden.read_bytes()
    if actual == expected:
        return

    diff = "\n".join(
        difflib.unified_diff(
            expected.decode("utf-8", "replace").splitlines(),
            actual.decode("utf-8", "replace").splitlines(),
            fromfile=f"golden/{golden.name}",
            tofile="rendered",
            lineterm="",
            n=2,
        )
    )
    snippet = "\n".join(diff.splitlines()[:60])
    pytest.fail(
        f"{_pair_id(pair)}: rendered HTML differs from committed golden.\n"
        f"Rebase with: SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/ -k '{tex.stem}'\n\n"
        f"{snippet}"
    )


def test_corpus_is_non_empty() -> None:
    """Guard against the glob silently finding nothing."""
    assert len(_PAIRS) >= 100, f"expected the example corpus, found {len(_PAIRS)} pairs"
