"""Phase 7 (GEP-20) — simulated annealing pill refine: RED tests.

Covers the contract of ``_simulated_annealing_refine`` in
``scriba/animation/primitives/_pill_refine.py``:

- Deterministic: same seed → bit-identical output.
- Empty / single-input → no-op.
- Locked-perp invariant: on-stroke pills never move perpendicular.
- Overlap reduction: a contrived overlapping pair gets teased apart.
- Budget: 50 candidates finish under 200ms on CI.

The SA module is intentionally pure — no Graph dependency — so the tests
exercise it directly with synthetic candidates.
"""

from __future__ import annotations

import math
import time

import pytest

from scriba.animation.primitives._pill_refine import (
    _PillCandidate,
    _simulated_annealing_refine,
)


def _cand(
    x: float,
    y: float,
    *,
    ux: float = 1.0,
    uy: float = 0.0,
    w: float = 40.0,
    h: float = 16.0,
    locked: bool = False,
) -> _PillCandidate:
    """Build a candidate with axis-aligned pill along (ux, uy)."""
    # Perp axis is (ux, uy) rotated 90° CCW → (-uy, ux)
    return _PillCandidate(
        x=x,
        y=y,
        origin_x=x,
        origin_y=y,
        ux=ux,
        uy=uy,
        perp_x=-uy,
        perp_y=ux,
        pill_w=w,
        pill_h=h,
        aabb_w=w,
        aabb_h=h,
        locked_perp=locked,
    )


@pytest.mark.unit
def test_empty_input_returns_empty() -> None:
    """No candidates → no-op."""
    out = _simulated_annealing_refine(
        [], canvas_w=800, canvas_h=600, seed=42
    )
    assert out == []


@pytest.mark.unit
def test_single_candidate_unchanged() -> None:
    """A single pill short-circuits and returns its origin exactly."""
    cand = _cand(100, 100)
    out = _simulated_annealing_refine(
        [cand], canvas_w=800, canvas_h=600, seed=42
    )
    # n==1 early-return guarantees bit-identical passthrough; no SA step runs.
    assert out == [(100.0, 100.0)]


@pytest.mark.unit
def test_determinism_same_seed_bit_identical() -> None:
    """Same input + same seed ⇒ identical output list."""
    cands = [
        _cand(100, 100),
        _cand(130, 100),  # overlaps by 10 on the x-axis
        _cand(200, 200),
    ]
    out1 = _simulated_annealing_refine(
        cands, canvas_w=800, canvas_h=600, seed=42, max_iter=80
    )
    out2 = _simulated_annealing_refine(
        cands, canvas_w=800, canvas_h=600, seed=42, max_iter=80
    )
    assert out1 == out2, "same seed must produce bit-identical output"


@pytest.mark.unit
def test_locked_perp_never_moves_perpendicular() -> None:
    """Candidate with ``locked_perp=True`` only moves along its edge axis."""
    cand = _cand(100, 100, ux=1.0, uy=0.0, locked=True)
    # Place a second overlapping pill to force SA to try moving.
    neighbour = _cand(120, 100)
    out = _simulated_annealing_refine(
        [cand, neighbour],
        canvas_w=800,
        canvas_h=600,
        seed=7,
        max_iter=60,
    )
    (nx, ny) = out[0]
    # Perp axis for ux=1,uy=0 is (0, 1) → y-coord must stay at origin_y.
    assert abs(ny - 100.0) < 1e-6, (
        f"locked_perp pill moved perpendicular: ny={ny} origin_y=100"
    )


@pytest.mark.unit
def test_overlap_reduction_for_colliding_pair() -> None:
    """SA must reduce the overlap area of a badly placed pair."""
    # Two identical pills stacked exactly — maximum overlap.
    a = _cand(100, 100)
    b = _cand(100, 100)

    def _overlap_area(ax: float, ay: float, bx: float, by: float, w: float, h: float) -> float:
        dx = max(0.0, w - abs(ax - bx))
        dy = max(0.0, h - abs(ay - by))
        return dx * dy

    before = _overlap_area(100, 100, 100, 100, 40, 16)
    out = _simulated_annealing_refine(
        [a, b], canvas_w=800, canvas_h=600, seed=1, max_iter=120
    )
    (ax, ay), (bx, by) = out
    after = _overlap_area(ax, ay, bx, by, 40, 16)
    assert after < before * 0.5, (
        f"SA failed to halve overlap: before={before}, after={after}"
    )


@pytest.mark.unit
def test_budget_50_candidates_under_200ms() -> None:
    """Reasonable-size refine must finish fast."""
    cands: list[_PillCandidate] = []
    for i in range(50):
        cands.append(_cand(50 + (i % 10) * 60, 50 + (i // 10) * 50))
    start = time.perf_counter()
    # Use the module default max_iter=80 (matches GEP-20 spec) so the
    # budget test enforces the documented contract.
    out = _simulated_annealing_refine(
        cands, canvas_w=800, canvas_h=600, seed=42
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert len(out) == 50
    assert elapsed_ms < 200, f"SA too slow: {elapsed_ms:.1f}ms for 50 cands"


@pytest.mark.unit
def test_locked_perp_does_not_shift_rng_stream() -> None:
    """Toggling ``locked_perp`` on one candidate must not perturb the RNG
    stream seen by OTHER candidates.

    Guards against a subtle determinism hazard: if the locked branch
    skipped the perp `rng.uniform` draw, every pill placed after a
    locked neighbour would receive a different random sequence, so
    A/B-comparing locked vs unlocked placements would entangle the two.
    The implementation normalises by always drawing the magnitude and
    zeroing it on lock; this test locks that contract.
    """
    # Pill 0 is a no-op neighbour far from pill 1 so pair energy is zero
    # regardless of where it moves. Only pill 1's x-coord is observable.
    locked = _cand(100, 100, locked=True)
    unlocked_ref = _cand(100, 100, locked=False)
    far = _cand(500, 500)
    out_locked = _simulated_annealing_refine(
        [locked, far], canvas_w=800, canvas_h=600, seed=99, max_iter=30
    )
    out_unlocked = _simulated_annealing_refine(
        [unlocked_ref, far], canvas_w=800, canvas_h=600, seed=99, max_iter=30
    )
    # The "far" pill sees identical RNG draws for its own randrange +
    # uniform calls in both runs, so its refined position must match.
    assert out_locked[1] == out_unlocked[1], (
        "locked_perp on an unrelated pill must not shift the RNG stream "
        "for other pills"
    )


@pytest.mark.unit
def test_canvas_clamp_keeps_pills_in_bounds() -> None:
    """Refined positions must stay inside the canvas viewbox.

    Uses two overlapping candidates so the SA loop actually runs (n>=2),
    exercising the clamp at lines 187-188 of `_pill_refine.py`. A single-
    candidate case would short-circuit to the origin and bypass clamp.
    """
    # Two stacked pills near the left edge — SA will try to separate them
    # along x, potentially pushing one candidate to negative coordinates
    # unless the clamp catches it.
    a = _cand(20, 20, w=40, h=16)
    b = _cand(20, 20, w=40, h=16)
    out = _simulated_annealing_refine(
        [a, b], canvas_w=800, canvas_h=600, seed=3, max_iter=80
    )
    for (nx, ny) in out:
        assert 20 <= nx <= 800 - 20, f"x={nx} out of clamp [20, 780]"
        assert 8 <= ny <= 600 - 8, f"y={ny} out of clamp [8, 592]"
