"""Unit tests for scriba.animation.primitives.graph_layout_score."""

from __future__ import annotations

from scriba.animation.primitives.graph_layout_score import score_layout


WIDTH = 400
HEIGHT = 300


class TestScoreLayout:
    def test_crossing_free_beats_crossing_heavy(self) -> None:
        # Square A,B,C,D with edges along the perimeter -> no crossings.
        clean_pos = {
            "A": (100, 100),
            "B": (300, 100),
            "C": (300, 200),
            "D": (100, 200),
        }
        edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")]
        clean = score_layout(clean_pos, edges, WIDTH, HEIGHT)

        # Same positions but edges drawn as the two diagonals + cross-pairs so
        # the segments intersect.
        crossing_pos = clean_pos
        crossing_edges = [("A", "C"), ("B", "D")]  # the two diagonals cross
        crossing = score_layout(crossing_pos, crossing_edges, WIDTH, HEIGHT)

        assert crossing > clean

    def test_centered_beats_border_hugging(self) -> None:
        edges = [("A", "B"), ("B", "C")]
        # Nodes comfortably inside the canvas, spread out.
        centered = {
            "A": (120, 150),
            "B": (200, 100),
            "C": (280, 150),
        }
        # Nodes jammed against the borders.
        border = {
            "A": (21, 21),
            "B": (200, 21),
            "C": (379, 279),
        }
        assert score_layout(centered, edges, WIDTH, HEIGHT) < score_layout(
            border, edges, WIDTH, HEIGHT
        )

    def test_deterministic_same_input_same_score(self) -> None:
        pos = {"A": (100, 100), "B": (300, 200), "C": (150, 250)}
        edges = [("A", "B"), ("B", "C")]
        assert score_layout(pos, edges, WIDTH, HEIGHT) == score_layout(
            pos, edges, WIDTH, HEIGHT
        )

    def test_weighted_3tuples_handled(self) -> None:
        pos = {"A": (100, 100), "B": (300, 200)}
        weighted = [("A", "B", 5.0)]
        plain = [("A", "B")]
        # The weight must be ignored: identical geometry -> identical score.
        assert score_layout(pos, weighted, WIDTH, HEIGHT) == score_layout(
            pos, plain, WIDTH, HEIGHT
        )

    def test_edge_with_missing_endpoint_skipped(self) -> None:
        pos = {"A": (100, 100), "B": (300, 200)}
        # Edge ("B", "Z") references missing Z -> skipped, must not raise.
        edges = [("A", "B"), ("B", "Z")]
        score = score_layout(pos, edges, WIDTH, HEIGHT)
        assert isinstance(score, float)

    def test_no_edges_no_crossings(self) -> None:
        pos = {"A": (100, 100), "B": (300, 200)}
        # No edges => no crossing/border/spread connected nodes => score 0.
        assert score_layout(pos, [], WIDTH, HEIGHT) == 0.0
