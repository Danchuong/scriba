"""GEP-20 (Phase 7) — simulated annealing refine for edge-pill placements.

Post-cascade global optimiser. Takes the output of the on-stroke → along-
shift → perp → leader cascade (Phases 1-4) and perturbs each pill's
position along (+/- ux, uy) and (+/- perp_x, perp_y) axes to reduce:

    Energy = Σ pair_overlap² + Σ dist_from_origin · w_anchor

where ``pair_overlap`` is the AABB overlap area between two pills and
``dist_from_origin`` is the Euclidean distance from the SA-refined
position back to the pill's cascade-chosen origin.  ``w_anchor`` pulls
pills back toward the cascade solution — without it SA would happily
send a pill to the corner of the canvas just to eliminate a tiny
overlap.

Locked-perp invariant (U-14 / GEP-11): candidates marked
``locked_perp=True`` (on-stroke pills that the cascade promoted via
along-shift without needing perp) are restricted to move ONLY along
``(ux, uy)``; the perpendicular delta is forced to 0.  This preserves
the on-stroke binding for those pills while still letting SA slide them
along the edge.

Determinism (U-06): the entire schedule — iteration count, temperature
cooling, neighbour perturbation, Metropolis dice — is driven by a
seeded ``random.Random`` instance.  Same input + same seed ⇒ byte-
identical output list.

Scope: Phase 7 is opt-in via Graph(``global_optimize=True``) and the
emit_svg integration will land in v2.1; this module is the isolated
primitive that provides the contract and is exercised directly by the
unit tests.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


__all__ = ["_PillCandidate", "_simulated_annealing_refine"]


@dataclass(frozen=True, slots=True)
class _PillCandidate:
    """Snapshot of a cascade-placed pill fed to SA refine.

    Positional fields:
        x, y             — current placement (cascade output).
        origin_x, origin_y — cascade anchor used for the dist_from_origin
                           energy term; SA pulls back toward this point.
        ux, uy           — unit along-edge axis; SA perturbs ``+/- α·(ux, uy)``.
        perp_x, perp_y   — unit perpendicular axis; SA perturbs
                           ``+/- β·(perp_x, perp_y)`` unless ``locked_perp``.
        pill_w, pill_h   — rendered pill dimensions (used for future OBB
                           checks; the AABB check uses the pre-rotated
                           aabb_w/aabb_h fields).
        aabb_w, aabb_h   — axis-aligned bounding box dimensions of the
                           rotated pill plus stroke-width pad.
        locked_perp      — True for on-stroke pills (U-14 lock).  SA
                           restricts motion to the along axis only.
    """

    x: float
    y: float
    origin_x: float
    origin_y: float
    ux: float
    uy: float
    perp_x: float
    perp_y: float
    pill_w: float
    pill_h: float
    aabb_w: float
    aabb_h: float
    locked_perp: bool = False


def _overlap_area(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> float:
    """AABB overlap area, zero when disjoint."""
    dx = min(ax + aw / 2, bx + bw / 2) - max(ax - aw / 2, bx - bw / 2)
    dy = min(ay + ah / 2, by + bh / 2) - max(ay - ah / 2, by - bh / 2)
    if dx <= 0 or dy <= 0:
        return 0.0
    return dx * dy


def _clamp(v: float, lo: float, hi: float) -> float:
    """Clamp *v* into ``[lo, hi]``; degenerate range (``lo >= hi``) returns *lo*."""
    if lo >= hi:
        return lo
    return max(lo, min(hi, v))


def _energy(
    positions: list[tuple[float, float]],
    cands: list[_PillCandidate],
    anchor_weight: float,
) -> float:
    """Total energy over all pairs + origin anchors."""
    n = len(positions)
    total = 0.0
    for i in range(n):
        xi, yi = positions[i]
        ci = cands[i]
        for j in range(i + 1, n):
            xj, yj = positions[j]
            cj = cands[j]
            o = _overlap_area(
                xi, yi, ci.aabb_w, ci.aabb_h,
                xj, yj, cj.aabb_w, cj.aabb_h,
            )
            total += o * o
        dx = xi - ci.origin_x
        dy = yi - ci.origin_y
        total += math.hypot(dx, dy) * anchor_weight
    return total


def _simulated_annealing_refine(
    candidates: list[_PillCandidate],
    *,
    canvas_w: float,
    canvas_h: float,
    seed: int = 42,
    max_iter: int = 80,
    anchor_weight: float = 0.1,
    along_step: float = 3.0,
    perp_step: float = 3.0,
    t0: float = 10.0,
    alpha: float = 0.92,
) -> list[tuple[float, float]]:
    """Return SA-refined ``(x, y)`` per candidate, preserving input order.

    Empty input returns empty; a single candidate short-circuits to its
    current position (no pair-overlap to minimise).  The algorithm
    otherwise runs a fixed-budget Metropolis schedule seeded by ``seed``.

    Motion per step:
        * draw a random candidate index i
        * draw α ∈ [-along_step, +along_step]; δ_along = α · (ux_i, uy_i)
        * if ``locked_perp`` is False:
              draw β ∈ [-perp_step, +perp_step]; δ_perp = β · (perp_x, perp_y)
          else:
              δ_perp = (0, 0)
        * candidate_pos ← current_pos + δ_along + δ_perp, clamped to
          canvas-less-half-pill bounds so the pill never crosses the
          viewbox edge.
        * ΔE = energy(new) − energy(current)
        * accept with probability min(1, exp(−ΔE / T))
        * after each iteration T *= alpha

    Returns the best-ever positions found (not the last-accepted) so the
    result is robust against late-schedule regressions.
    """
    n = len(candidates)
    if n == 0:
        return []
    if n == 1:
        return [(candidates[0].x, candidates[0].y)]

    rng = random.Random(seed)

    positions: list[tuple[float, float]] = [(c.x, c.y) for c in candidates]
    best_positions: list[tuple[float, float]] = list(positions)
    current_e = _energy(positions, candidates, anchor_weight)
    best_e = current_e

    t = t0
    for _ in range(max_iter):
        i = rng.randrange(n)
        ci = candidates[i]
        a_scale = rng.uniform(-along_step, along_step)
        # Always draw the perp magnitude so the RNG stream is identical
        # regardless of which candidates are locked. Without this, toggling
        # locked_perp on one pill shifts all subsequent draws and perturbs
        # every downstream pill's trajectory (stream-stability issue).
        b_draw = rng.uniform(-perp_step, perp_step)
        b_scale = 0.0 if ci.locked_perp else b_draw

        dx = a_scale * ci.ux + b_scale * ci.perp_x
        dy = a_scale * ci.uy + b_scale * ci.perp_y
        cx, cy = positions[i]
        nx = cx + dx
        ny = cy + dy

        nx = _clamp(nx, ci.aabb_w / 2, canvas_w - ci.aabb_w / 2)
        ny = _clamp(ny, ci.aabb_h / 2, canvas_h - ci.aabb_h / 2)

        trial = list(positions)
        trial[i] = (nx, ny)
        trial_e = _energy(trial, candidates, anchor_weight)

        dE = trial_e - current_e
        accept = dE < 0 or rng.random() < math.exp(-dE / max(t, 1e-9))
        if accept:
            positions = trial
            current_e = trial_e
            if trial_e < best_e:
                best_e = trial_e
                best_positions = list(trial)

        t *= alpha

    return best_positions
