"""Integration tests verifying algorithm example coverage.

For each algorithm example, asserts:
- The .tex source file exists and is non-trivial (>10 lines)
- The .tex source uses the documented primitives
"""

from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"

# (relative_path, expected_primitives_in_tex)
ALGORITHM_EXAMPLES: list[tuple[str, list[str]]] = [
    ("algorithms/dp/interval_dp.tex", ["DPTable", "Array"]),
    ("algorithms/dp/dp_optimization.tex", ["DPTable", "NumberLine"]),
    ("algorithms/dp/convex_hull_trick.tex", ["Plane2D"]),
    ("algorithms/dp/frog.tex", ["Array"]),
    ("algorithms/graph/dijkstra.tex", ["Graph"]),
    ("algorithms/graph/kruskal_mst.tex", ["Graph"]),
    ("algorithms/graph/bfs.tex", ["Graph", "Tree"]),
    ("algorithms/graph/mcmf.tex", ["Graph"]),
    ("algorithms/graph/union_find.tex", ["Graph"]),
    ("algorithms/tree/bst_operations.tex", ["Tree"]),
    ("algorithms/tree/persistent_segtree.tex", ["Tree"]),
    ("algorithms/tree/hld.tex", ["Tree", "Array"]),
    ("algorithms/tree/splay.tex", ["Tree", "MetricPlot"]),
    ("algorithms/string/kmp.tex", ["Array"]),
    ("algorithms/misc/fft_butterfly.tex", ["Plane2D", "Array"]),
    ("algorithms/misc/simulated_annealing.tex", ["Graph", "MetricPlot"]),
    ("algorithms/misc/li_chao.tex", ["Plane2D"]),
    ("algorithms/misc/convex_hull_andrew.tex", ["Plane2D"]),
    ("algorithms/misc/linkedlist_reverse.tex", ["LinkedList"]),
]


@pytest.fixture(
    params=ALGORITHM_EXAMPLES,
    ids=[p[0].replace("/", "_").replace(".tex", "") for p in ALGORITHM_EXAMPLES],
)
def example(request: pytest.FixtureRequest) -> tuple[str, list[str]]:
    return request.param


class TestAlgorithmExamplesExist:
    """Verify .tex source files exist and are non-trivial."""

    def test_tex_file_exists(self, example: tuple[str, list[str]]) -> None:
        rel_path, _prims = example
        tex_path = EXAMPLES_DIR / rel_path
        assert tex_path.exists(), f"Missing .tex source: {tex_path}"

    def test_tex_file_nontrivial(self, example: tuple[str, list[str]]) -> None:
        rel_path, _prims = example
        tex_path = EXAMPLES_DIR / rel_path
        lines = tex_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) > 10, (
            f"{rel_path} has only {len(lines)} lines; expected >10"
        )


class TestAlgorithmPrimitives:
    """Verify .tex files use the documented primitives."""

    def test_tex_contains_expected_primitives(
        self, example: tuple[str, list[str]]
    ) -> None:
        rel_path, primitives = example
        tex_path = EXAMPLES_DIR / rel_path
        content = tex_path.read_text(encoding="utf-8")
        for prim in primitives:
            assert prim in content, (
                f"{rel_path} missing expected primitive: {prim}"
            )


class TestQuickstartExist:
    """Verify quickstart examples exist."""

    @pytest.mark.parametrize(
        "name",
        ["hello.tex", "binary_search.tex", "foreach_demo.tex"],
    )
    def test_quickstart_exists(self, name: str) -> None:
        path = EXAMPLES_DIR / "quickstart" / name
        assert path.exists(), f"Missing quickstart: {path}"


class TestPrimitiveExamplesExist:
    """Verify one demo per primitive type."""

    @pytest.mark.parametrize(
        "name",
        [
            "array", "codepanel", "diagram", "graph", "grid",
            "hashmap", "linkedlist", "matrix", "metricplot",
            "numberline", "plane2d", "queue", "stack",
            "substory", "tree", "variablewatch",
        ],
    )
    def test_primitive_demo_exists(self, name: str) -> None:
        path = EXAMPLES_DIR / "primitives" / f"{name}.tex"
        assert path.exists(), f"Missing primitive demo: {path}"


class TestCoverageSummary:
    """Aggregate coverage check."""

    def test_algorithm_count(self) -> None:
        algo_dir = EXAMPLES_DIR / "algorithms"
        tex_files = list(algo_dir.rglob("*.tex"))
        assert len(tex_files) >= 19, (
            f"Expected >=19 algorithm examples, got {len(tex_files)}"
        )

    def test_primitive_count(self) -> None:
        prim_dir = EXAMPLES_DIR / "primitives"
        tex_files = list(prim_dir.glob("*.tex"))
        assert len(tex_files) >= 16, (
            f"Expected >=16 primitive demos, got {len(tex_files)}"
        )
