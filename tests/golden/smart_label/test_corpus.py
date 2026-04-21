"""Corpus test runner for the smart-label golden fixtures.

Iterates every fixture directory under tests/golden/smart_label/,
executes its input.py, normalizes the resulting SVG, and compares
the SHA256 against expected.sha256.

On mismatch the test prints an actionable unified diff and the rebase
command required to update the pin.

Known-failing fixtures (those with a known_failing.json sidecar where
``"known_failing": true``) follow the XFAIL protocol from §3.3 of the
golden-corpus design doc:
  - If actual SHA matches expected (bug still present): xfail (expected).
  - If actual SHA does NOT match (behaviour changed): fail with XFAIL_IMPROVED.

Usage:
    pytest tests/golden/smart_label/ -v

Update mode (human review required before commit):
    SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/smart_label/ -v
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterator

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CORPUS_ROOT = Path(__file__).parent
_REPO_ROOT = _CORPUS_ROOT.parent.parent.parent


def _iter_fixture_dirs() -> Iterator[Path]:
    """Yield every fixture directory (those containing input.py)."""
    for fixture_dir in sorted(_CORPUS_ROOT.iterdir()):
        if fixture_dir.is_dir() and (fixture_dir / "input.py").exists():
            yield fixture_dir


def _fixture_id(fixture_dir: Path) -> str:
    return fixture_dir.name


def _read_known_failing(fixture_dir: Path) -> tuple[bool, str]:
    """Return (is_known_failing, reason) from known_failing.json if present."""
    kf_path = fixture_dir / "known_failing.json"
    if not kf_path.exists():
        return False, ""
    data = json.loads(kf_path.read_text(encoding="utf-8"))
    return bool(data.get("known_failing", False)), data.get("reason", "")


# ---------------------------------------------------------------------------
# Normalizer import helper
# ---------------------------------------------------------------------------


def _get_normalizer():  # type: ignore[return]
    """Import the SVG normalizer, isolated from broken package star-imports."""
    sys.path.insert(0, str(_REPO_ROOT))

    # Monkey-patch missing _place_pill stub so package can load cleanly
    # while Stream A's refactor is still in-progress.
    try:
        import scriba.animation.primitives._svg_helpers as _helpers_module

        if not hasattr(_helpers_module, "_place_pill"):
            _helpers_module._place_pill = None  # type: ignore[attr-defined]
    except Exception:
        pass

    from tests.helpers.svg_normalize import normalize, sha256_of

    return normalize, sha256_of


# ---------------------------------------------------------------------------
# Fixture execution
# ---------------------------------------------------------------------------


def _run_fixture(fixture_dir: Path) -> str:
    """Execute input.py and return the OUTPUT variable as a raw SVG string."""
    input_py = fixture_dir / "input.py"
    # Inject __file__ so fixture scripts can use Path(__file__).parent.
    namespace: dict = {"__file__": str(input_py)}
    exec(  # noqa: S102
        compile(input_py.read_text(encoding="utf-8"), str(input_py), "exec"),
        namespace,
    )
    output = namespace.get("OUTPUT")
    if output is None:
        raise RuntimeError(
            f"input.py in {fixture_dir} did not set OUTPUT"
        )
    return output


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------

_FIXTURE_DIRS = list(_iter_fixture_dirs())
_FIXTURE_IDS = [_fixture_id(d) for d in _FIXTURE_DIRS]

_UPDATE_GOLDEN = os.environ.get("SCRIBA_UPDATE_GOLDEN") == "1"


@pytest.mark.parametrize("fixture_dir", _FIXTURE_DIRS, ids=_FIXTURE_IDS)
def test_golden_fixture(fixture_dir: Path) -> None:
    """Run one golden fixture and compare against the pinned SHA256."""
    normalize, sha256_of = _get_normalizer()

    expected_svg_path = fixture_dir / "expected.svg"
    expected_sha_path = fixture_dir / "expected.sha256"

    if not expected_svg_path.exists():
        pytest.skip(f"No expected.svg in {fixture_dir.name} — fixture not yet seeded")
    if not expected_sha_path.exists():
        pytest.skip(f"No expected.sha256 in {fixture_dir.name} — fixture not yet pinned")

    # Read pinned SHA256 (first token on first line, sha256sum -c format).
    raw_pin_line = expected_sha_path.read_text(encoding="utf-8").strip().splitlines()[0]
    expected_sha = raw_pin_line.split()[0]

    # Check known-failing status.
    is_known_failing, kf_reason = _read_known_failing(fixture_dir)

    # Execute fixture.
    raw_svg = _run_fixture(fixture_dir)
    normalized = normalize(raw_svg)
    actual_sha = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    if _UPDATE_GOLDEN:
        # Write new expected.svg and expected.sha256 (human review gate applies).
        expected_svg_path.write_text(normalized, encoding="utf-8")
        expected_sha_path.write_text(
            f"{actual_sha}  expected.svg\n", encoding="utf-8"
        )
        print(
            f"\n[GOLDEN UPDATE] {fixture_dir.name} — "
            "human review required before commit"
        )
        return  # pass unconditionally in update mode

    if actual_sha == expected_sha:
        if is_known_failing:
            # Bug still present as expected — xfail with informational message.
            pytest.xfail(
                f"[known_failing] {fixture_dir.name}: output matches known-bad "
                f"golden (bug still present). Reason: {kf_reason}"
            )
        # Nominal green path: idempotency check.
        normalized_twice = normalize(normalized)
        sha_twice = hashlib.sha256(normalized_twice.encode("utf-8")).hexdigest()
        assert sha_twice == actual_sha, (
            f"Normalizer is not idempotent for fixture '{fixture_dir.name}'. "
            "normalize(normalize(svg)) != normalize(svg)"
        )
        return

    # SHA mismatch — either a regression or the bug was fixed.
    if is_known_failing:
        # Output changed from the known-bad golden — may indicate a fix!
        expected_lines = expected_svg_path.read_text(encoding="utf-8").splitlines(
            keepends=True
        )
        actual_lines = normalized.splitlines(keepends=True)
        diff = "".join(
            difflib.unified_diff(
                expected_lines,
                actual_lines,
                fromfile=f"expected/{fixture_dir.name}/expected.svg",
                tofile=f"actual/{fixture_dir.name}/expected.svg",
                n=4,
            )
        )
        rebase_cmd = (
            f"SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/smart_label/ "
            f"-k {fixture_dir.name!r} -v"
        )
        pytest.fail(
            f"[XFAIL_IMPROVED] {fixture_dir.name}: output changed from "
            f"known-bad golden. The bug may have been fixed.\n"
            f"Expected (known-bad): {expected_sha}\n"
            f"Actual:              {actual_sha}\n\n"
            f"Diff:\n{diff}\n\n"
            f"If the bug is fixed, run:\n  {rebase_cmd}\n"
            "then promote known_failing to false and update the CHANGELOG."
        )

    # Ordinary regression — unexpected SHA change in a non-known-failing fixture.
    expected_lines = expected_svg_path.read_text(encoding="utf-8").splitlines(
        keepends=True
    )
    actual_lines = normalized.splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile=f"expected/{fixture_dir.name}/expected.svg",
            tofile=f"actual/{fixture_dir.name}/expected.svg",
            n=4,
        )
    )
    rebase_cmd = (
        f"SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/smart_label/ "
        f"-k {fixture_dir.name!r} -v"
    )
    pytest.fail(
        f"SHA256 mismatch for fixture '{fixture_dir.name}'.\n"
        f"Expected: {expected_sha}\n"
        f"Actual:   {actual_sha}\n\n"
        f"Diff:\n{diff}\n\n"
        f"To update the pin (requires human review):\n  {rebase_cmd}"
    )
