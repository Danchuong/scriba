"""Integration tests verifying Hard-to-Display cookbook coverage.

For each of the 9 covered HTD problems, this module asserts:
- The .tex source file exists and is non-trivial (>10 lines)
- The _expected.html golden file exists and is non-empty
- The _expected.html contains expected Scriba widget class names
- The .tex source uses the documented primitives
"""

from __future__ import annotations

from pathlib import Path

import pytest

COOKBOOK_DIR = Path(__file__).resolve().parents[2] / "examples" / "cookbook"

# (file_stem, expected_tex_primitives, expected_html_markers)
HTD_PROBLEMS: list[tuple[str, int, list[str], list[str]]] = [
    (
        "h01_zuma_interval_dp",
        1,
        ["DPTable", "Array", r"\substory"],
        ["scriba-widget"],
    ),
    (
        "h02_dp_optimization",
        2,
        ["DPTable", "NumberLine"],
        ["scriba-widget"],
    ),
    (
        "h04_fft_butterfly",
        4,
        ["Plane2D", "Array"],
        ["scriba-widget"],
    ),
    (
        "h05_mcmf",
        5,
        ["Graph", 'layout="stable"'],
        ["scriba-widget"],
    ),
    (
        "h06_li_chao",
        6,
        ["Plane2D"],
        ["scriba-widget"],
    ),
    (
        "h07_splay_amortized",
        7,
        ["Tree", "MetricPlot"],
        ["scriba-widget"],
    ),
    (
        "h08_persistent_segtree",
        8,
        ["Tree", "segtree"],
        ["scriba-widget"],
    ),
    (
        "h09_simulated_annealing",
        9,
        ["Graph", "MetricPlot"],
        ["scriba-widget"],
    ),
    (
        "h10_hld",
        10,
        ["Tree", "Array"],
        ["scriba-widget"],
    ),
]


@pytest.fixture(params=HTD_PROBLEMS, ids=[p[0] for p in HTD_PROBLEMS])
def htd_problem(
    request: pytest.FixtureRequest,
) -> tuple[str, int, list[str], list[str]]:
    return request.param


class TestHTDTexSourceExists:
    """Verify .tex source files exist and are non-trivial."""

    def test_tex_file_exists(self, htd_problem: tuple[str, int, list[str], list[str]]) -> None:
        stem, _num, _prims, _markers = htd_problem
        tex_path = COOKBOOK_DIR / f"{stem}.tex"
        assert tex_path.exists(), f"Missing .tex source: {tex_path}"

    def test_tex_file_nontrivial(self, htd_problem: tuple[str, int, list[str], list[str]]) -> None:
        stem, _num, _prims, _markers = htd_problem
        tex_path = COOKBOOK_DIR / f"{stem}.tex"
        lines = tex_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) > 10, (
            f"{stem}.tex has only {len(lines)} lines; expected >10"
        )


class TestHTDExpectedHtmlExists:
    """Verify _expected.html golden files exist and contain widget markup."""

    def test_expected_html_exists(
        self, htd_problem: tuple[str, int, list[str], list[str]]
    ) -> None:
        stem, _num, _prims, _markers = htd_problem
        html_path = COOKBOOK_DIR / f"{stem}_expected.html"
        assert html_path.exists(), f"Missing _expected.html: {html_path}"

    def test_expected_html_nonempty(
        self, htd_problem: tuple[str, int, list[str], list[str]]
    ) -> None:
        stem, _num, _prims, _markers = htd_problem
        html_path = COOKBOOK_DIR / f"{stem}_expected.html"
        content = html_path.read_text(encoding="utf-8")
        assert len(content) > 100, (
            f"{stem}_expected.html is too small ({len(content)} bytes)"
        )

    def test_expected_html_has_widget_class(
        self, htd_problem: tuple[str, int, list[str], list[str]]
    ) -> None:
        stem, _num, _prims, _markers = htd_problem
        html_path = COOKBOOK_DIR / f"{stem}_expected.html"
        content = html_path.read_text(encoding="utf-8")
        # Older golden files use class="widget", newer ones use "scriba-widget"
        assert (
            "scriba-widget" in content or 'class="widget"' in content
        ), f"{stem}_expected.html missing widget class marker"


class TestHTDTexPrimitives:
    """Verify .tex files use the documented primitives."""

    def test_tex_contains_expected_primitives(
        self, htd_problem: tuple[str, int, list[str], list[str]]
    ) -> None:
        stem, _num, primitives, _markers = htd_problem
        tex_path = COOKBOOK_DIR / f"{stem}.tex"
        content = tex_path.read_text(encoding="utf-8")
        for prim in primitives:
            assert prim in content, (
                f"{stem}.tex missing expected primitive: {prim}"
            )


class TestHTDProblem3Partial:
    """Problem #3 (4D Knapsack) is intentionally not covered."""

    def test_h03_tex_does_not_exist(self) -> None:
        """No .tex source for 4D Knapsack -- partial by design."""
        assert not (COOKBOOK_DIR / "h03_4d_knapsack.tex").exists()

    def test_h03_expected_html_does_not_exist(self) -> None:
        """No golden file for 4D Knapsack -- partial by design."""
        assert not (COOKBOOK_DIR / "h03_4d_knapsack_expected.html").exists()


class TestHTDCoverageSummary:
    """Aggregate coverage check."""

    def test_nine_of_ten_covered(self) -> None:
        covered = 0
        for stem, _num, _prims, _markers in HTD_PROBLEMS:
            tex = COOKBOOK_DIR / f"{stem}.tex"
            html = COOKBOOK_DIR / f"{stem}_expected.html"
            if tex.exists() and html.exists():
                covered += 1
        assert covered == 9, f"Expected 9/10 covered, got {covered}/10"
