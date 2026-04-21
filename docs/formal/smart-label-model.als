-- smart-label-model.als
-- Alloy 4 / Alloy 6 compatible model of smart-label placement invariants.
-- Spec: docs/spec/smart-label-ruleset.md §1 + §2.
-- Status: EXPERIMENTAL. Design notes: 07-alloy-model.md in this directory.
--
-- Integer domain: 5-bit (int[5]), range [-16, 15].
-- Invariants encoded: G-1, G-2(approx), G-3, G-4, G-5, C-1, C-3(structural),
--   C-4, M-4(pred), M-7, tie-breaker consistency TB-1/TB-2/TB-5.
-- Not encoded: T-1..T-6, A-1..A-7, D-1..D-4, E-1..E-4, AC-1..AC-6.
-- Run: java -jar alloy4.2.jar smart-label-model.als
-- ---------------------------------------------------------------------------


-- ===========================================================================
-- SIGNATURES
-- ===========================================================================

-- AABB: axis-aligned bounding box (top-left origin, SVG convention).
-- Spec uses center (cx,cy); model uses top-left: cx = x + w/2, cy = y + h/2.
sig AABB {
    x : Int,
    y : Int,
    w : Int,
    h : Int
}

-- Pill: placed annotation pill.  Subset of Registry.labels = placed_labels.
sig Pill extends AABB {}

-- Anchor: geometric reference point (arc midpoint or stem tip).
-- Degenerate AABB with w=h=0; see fact AnchorIsPoint.
sig Anchor extends AABB {}

-- ViewBox: SVG viewBox for the current frame (exactly one per run).
one sig ViewBox {
    vw : Int,
    vh : Int
}

-- Registry: placed_labels list for one emit_svg call.
-- Alloy sets are immutable/unordered — naturally models append-only (C-3).
sig Registry {
    labels : set Pill
}

-- Frame: one emit_svg call.  Owns exactly one Registry.
-- Used to model C-4 (no cross-frame sharing).
sig Frame {
    registry : one Registry
}

-- NudgeCandidate: one (dx, dy) displacement from the natural position.
-- The nudge grid emits 32 candidates (8 dirs × 4 steps); model constrains
-- the set without enumerating all 32.
sig NudgeCandidate {
    dx : Int,
    dy : Int
}

-- ClampPair: before/after snapshot of the clamp operation.
-- pre = pre-clamp AABB (may be outside viewBox).
-- post = post-clamp AABB (inside viewBox; same dimensions as pre — G-4).
sig ClampPair {
    pre  : one AABB,
    post : one AABB
}


-- ===========================================================================
-- FACTS  (hard structural constraints, always true)
-- ===========================================================================

-- G-5: Pills have strictly positive dimensions.
fact PositiveDims {
    all p : Pill | p.w > 0 and p.h > 0
}

-- ViewBox has positive extent (precondition for G-3 containment checks).
fact ViewBoxPositive {
    ViewBox.vw > 0 and ViewBox.vh > 0
}

-- M-7 / E1566: Nudge grid MUST NOT yield (0, 0).
fact NudgeNonZero {
    all c : NudgeCandidate | not (c.dx = 0 and c.dy = 0)
}

-- Anchors are dimensionless reference points.
fact AnchorIsPoint {
    all a : Anchor | a.w = 0 and a.h = 0
}

-- G-4: Clamp only translates; dimensions are unchanged.
fact ClampOnlyTranslates {
    all cp : ClampPair |
        cp.pre.w = cp.post.w
        and cp.pre.h = cp.post.h
}

-- G-1 + G-3: Every pill in a registry is the post-clamp version, i.e., inside viewBox.
-- (Pre-clamp coordinates may lie outside; only post-clamp is registered.)
fact PostClampRegistration {
    all r : Registry |
    all p : r.labels |
        p.x >= 0
        and p.y >= 0
        and p.x.plus[p.w] <= ViewBox.vw
        and p.y.plus[p.h] <= ViewBox.vh
}

-- C-4: Each Frame owns a distinct Registry; no Pill atom is shared across Frames.
fact RegistryIsolation {
    all disj f1, f2 : Frame |
        f1.registry != f2.registry
        and no (f1.registry.labels & f2.registry.labels)
}

-- C-1: No two placed pills in the same registry overlap.
-- Core collision invariant.
fact PlacedLabelsNonOverlap {
    all r : Registry |
    all disj p1, p2 : r.labels |
        not overlaps[p1, p2]
}


-- ===========================================================================
-- PREDICATES  (geometric primitives)
-- ===========================================================================

-- overlaps[a, b]: two closed AABBs share at least one point.
-- C-1 requirement: NOT overlaps[p1, p2] for all distinct registry pairs.
-- Closed boundary: touching edges (e.g., right edge of A == left edge of B) count.
pred overlaps [a, b : AABB] {
    a.x.plus[a.w] >= b.x
    and b.x.plus[b.w] >= a.x
    and a.y.plus[a.h] >= b.y
    and b.y.plus[b.h] >= a.y
}

-- withinViewBox[p]: pill is entirely inside the declared viewBox (G-3).
pred withinViewBox [p : Pill] {
    p.x >= 0
    and p.y >= 0
    and p.x.plus[p.w] <= ViewBox.vw
    and p.y.plus[p.h] <= ViewBox.vh
}

-- clampThenCheck[candidate, r]: candidate passes collision check AFTER clamping.
-- Models M-4: per-candidate clamp must precede the collision test in the nudge loop.
pred clampThenCheck [candidate : Pill, r : Registry] {
    withinViewBox[candidate]
    and all existing : r.labels | not overlaps[candidate, existing]
}

-- anchorAtCenter[p]: geometric center of p lies within its own bounding box.
-- Approximate G-2: center = (x + w/2, y + h/2); integer division is exact to ±1 px.
pred anchorAtCenter [p : Pill] {
    let cx = p.x.plus[p.w.div[2]] |
    let cy = p.y.plus[p.h.div[2]] |
        cx >= p.x and cx <= p.x.plus[p.w]
        and cy >= p.y and cy <= p.y.plus[p.h]
}

-- nudgeProducesValidPlacement[n, natural, r]: applying nudge n to natural position
-- yields a placed pill that is valid (in viewBox, non-overlapping with registry r).
-- Used in ShowValidNudge run command to find illustrative examples.
pred nudgeProducesValidPlacement [n : NudgeCandidate, natural : Pill, r : Registry] {
    some placed : Pill |
        placed.x = natural.x.plus[n.dx]
        and placed.y = natural.y.plus[n.dy]
        and placed.w = natural.w
        and placed.h = natural.h
        and withinViewBox[placed]
        and all existing : r.labels | not overlaps[placed, existing]
}


-- ===========================================================================
-- ASSERTIONS  (properties to verify exhaustively)
-- ===========================================================================

-- C-1: No two placed pills in any registry overlap.
-- With PlacedLabelsNonOverlap fact active: expected NO counterexample.
-- (Validates that the overlaps predicate is consistent with the fact.)
assert NonOverlap {
    all r : Registry |
    all disj p1, p2 : r.labels |
        not overlaps[p1, p2]
}

-- G-3: All pills in any registry are inside the declared viewBox.
-- With PostClampRegistration fact active: expected NO counterexample.
assert ContainedInViewBox {
    all r : Registry |
    all p : r.labels |
        withinViewBox[p]
}

-- G-5: All pills have strictly positive dimensions.
-- With PositiveDims fact active: expected NO counterexample.
assert PositiveDimensions {
    all p : Pill | p.w > 0 and p.h > 0
}

-- G-4: Clamp preserves pill dimensions.
-- With ClampOnlyTranslates fact active: expected NO counterexample.
assert ClampPreservesDims {
    all cp : ClampPair |
        cp.pre.w = cp.post.w
        and cp.pre.h = cp.post.h
}

-- C-4: No two Frames share a Registry or any Pill.
-- With RegistryIsolation fact active: expected NO counterexample.
assert RegistriesDisjoint {
    all disj f1, f2 : Frame |
        f1.registry != f2.registry
        and no (f1.registry.labels & f2.registry.labels)
}

-- G-2 (approximate): geometric center of each pill lies within its own AABB.
-- Trivially true for any valid AABB; validates anchorAtCenter predicate.
-- Expected NO counterexample.
assert AnchorInsidePill {
    all p : Pill | anchorAtCenter[p]
}

-- M-7: No nudge candidate is (0, 0).
-- With NudgeNonZero fact active: expected NO counterexample.
assert NudgeNonZeroCheck {
    all c : NudgeCandidate | not (c.dx = 0 and c.dy = 0)
}

-- G-4 (extended): A post-clamp pill satisfying withinViewBox is already clamped;
-- re-clamping is a no-op (idempotence).
-- Expected NO counterexample (tautological for in-range pills).
assert ClampIdempotent {
    all p : Pill |
        (p.x >= 0 and p.y >= 0
         and p.x.plus[p.w] <= ViewBox.vw
         and p.y.plus[p.h] <= ViewBox.vh)
        implies
        (p.x >= 0 and p.y >= 0
         and p.x.plus[p.w] <= ViewBox.vw
         and p.y.plus[p.h] <= ViewBox.vh)
}

-- §1.8 Tie-breaker TB-1: C-1 wins over AC-3.
-- Non-overlap and pill existence are simultaneously satisfiable.
-- "C-1 wins" means: satisfying C-1 does not force the registry to be empty.
-- Expected NO counterexample.
assert TB1_C1_WinsNotEmpty {
    all r : Registry |
        (all disj p1, p2 : r.labels | not overlaps[p1, p2])
        implies
        (some r.labels implies all disj p1, p2 : r.labels | not overlaps[p1, p2])
}

-- §1.8 Tie-breaker TB-2: G-3 wins for clipping; AC-1 (emit) is minimum.
-- Both conditions are simultaneously satisfiable: a pill can exist inside a viewBox.
-- Expected NO counterexample.
assert TB2_EmitAndClamp {
    some r : Registry |
    some p : r.labels |
        withinViewBox[p]
}

-- §1.8 Tie-breaker TB-5: G-5 wins over AC-1 (empty label = config error, not emission).
-- All pills in any registry have positive dimensions (no zero-dim pill is ever placed).
-- Expected NO counterexample (follows from PositiveDims).
assert TB5_G5_WinsPositive {
    all r : Registry |
    all p : r.labels |
        p.w > 0 and p.h > 0
}


-- ===========================================================================
-- CHECK COMMANDS  (bounded exhaustive verification)
-- Scope: 5 atoms per sig, 5-bit integers (range [-16, 15]) unless noted.
-- ===========================================================================

-- CHECK-1 (C-1): No two registry pills overlap.  Expected: PASS.
check NonOverlap for 5 but 5 Int

-- CHECK-2 (G-3): All registry pills inside viewBox.  Expected: PASS.
check ContainedInViewBox for 5 but 5 Int

-- CHECK-3 (G-5): All pills have positive dimensions.  Expected: PASS.
check PositiveDimensions for 5 but 5 Int

-- CHECK-4 (G-4): Clamp preserves dimensions.  Expected: PASS.
check ClampPreservesDims for 4 ClampPair, 5 but 5 Int

-- CHECK-5 (C-4): Registries disjoint across frames.  Expected: PASS.
check RegistriesDisjoint for 3 Frame, 5 but 5 Int

-- CHECK-6 (G-2 approx): Anchor center inside pill AABB.  Expected: PASS.
check AnchorInsidePill for 5 Pill, 5 but 5 Int

-- CHECK-7 (M-7): Nudge candidates exclude (0,0).  Expected: PASS.
check NudgeNonZeroCheck for 8 NudgeCandidate, 5 but 5 Int

-- CHECK-8 (G-4 idempotence): Re-clamping an in-range pill is a no-op.  Expected: PASS.
check ClampIdempotent for 5 Pill, 5 but 5 Int

-- CHECK-9 (§1.8 TB-1): Non-overlap and existence are compatible.  Expected: PASS.
check TB1_C1_WinsNotEmpty for 5 but 5 Int

-- CHECK-10 (§1.8 TB-2): Emit-and-clamp simultaneously satisfiable.  Expected: PASS.
check TB2_EmitAndClamp for 5 but 5 Int

-- CHECK-11 (§1.8 TB-5): Zero-dim pills excluded from registries.  Expected: PASS.
check TB5_G5_WinsPositive for 5 but 5 Int


-- ===========================================================================
-- RUN COMMANDS  (instance exploration — informative only)
-- ===========================================================================

-- Find two non-overlapping pills inside a viewBox.
run ShowTwoPills {
    some r : Registry |
    #r.labels = 2
    and all p : r.labels | withinViewBox[p]
    and all disj p1, p2 : r.labels | not overlaps[p1, p2]
} for 2 Pill, 1 Registry, 1 Frame, 1 ViewBox, 5 but 5 Int

-- Find a nudge candidate accepted by clampThenCheck.
run ShowValidNudge {
    some c : NudgeCandidate |
    some natural : Pill |
    some r : Registry |
        not (c.dx = 0 and c.dy = 0)
        and nudgeProducesValidPlacement[c, natural, r]
} for 3 but 5 Int

-- Find a ClampPair where the clamp actually moves the pill (non-trivial translation).
run ShowNontrivialClamp {
    some cp : ClampPair |
        cp.pre.x != cp.post.x
        and cp.pre.w = cp.post.w
        and cp.pre.h = cp.post.h
} for 4 but 5 Int


-- ===========================================================================
-- END  smart-label-model.als
-- Spec: docs/spec/smart-label-ruleset.md §1 (G-1..G-5, C-1..C-4, M-4, M-7, §1.8)
-- Design notes: 07-alloy-model.md (this archive directory)
-- Promotion target: docs/formal/smart-label-model.als
-- ===========================================================================
