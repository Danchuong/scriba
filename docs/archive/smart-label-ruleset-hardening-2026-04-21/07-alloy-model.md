---
title: "Round-3 Foundation — Alloy Formal Model Design Notes"
status: EXPERIMENTAL
date: 2026-04-21
target-file: docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als
spec-ref: docs/spec/smart-label-ruleset.md §1 invariants, §2 placement algorithm
---

# 07 — Alloy Formal Model: Smart-Label Invariants

> **Status**: EXPERIMENTAL. This document and the accompanying `.als` file are not
> normative. Hypothesis property-based tests carry primary verification coverage.
> The Alloy model serves as a machine-checked reference for the geometric and
> collision invariants that are hardest to express in unit tests.
>
> **Appendix B pointer**: `docs/spec/smart-label-ruleset.md` Appendix B refers to
> `docs/formal/smart-label-model.als`. The model produced here is the first draft
> of that artefact, committed under the archive path during Round 3 hardening.
> When it matures it will be copied to `docs/formal/`.

---

## Table of Contents

1. [Motivation and Scope](#1-motivation-and-scope)
2. [Invariant Inventory: Encoded vs Deferred](#2-invariant-inventory-encoded-vs-deferred)
3. [Alloy Version and Toolchain](#3-alloy-version-and-toolchain)
4. [Bounded-Universe Design Rationale](#4-bounded-universe-design-rationale)
5. [Signature Design](#5-signature-design)
6. [Facts: Encoding the Invariants](#6-facts-encoding-the-invariants)
7. [Predicates: Geometric Primitives](#7-predicates-geometric-primitives)
8. [Assertions and `check` Commands](#8-assertions-and-check-commands)
9. [Tie-Breaker Consistency Analysis](#9-tie-breaker-consistency-analysis)
10. [Invariants That Cannot Be Encoded in Alloy](#10-invariants-that-cannot-be-encoded-in-alloy)
11. [How to Run the Model](#11-how-to-run-the-model)
12. [CI Integration Note](#12-ci-integration-note)
13. [Known Limitations and Future Work](#13-known-limitations-and-future-work)

---

## 1. Motivation and Scope

### 1.1 Why Alloy?

`docs/archive/smart-label-ruleset-strengthening-2026-04-21/06-spec-style.md §17`
concluded:

- **TLA+**: Not warranted. The placement algorithm is sequential, deterministic,
  and bounded (32 candidates, N annotations per frame). TLA+ is designed for
  concurrent systems with temporal properties across unbounded state sequences.
  None of those conditions apply here.
- **Alloy**: Feasible and useful. The structural invariants (AABB non-overlap,
  viewBox containment, registry isolation, clamp-idempotence) map directly to
  Alloy's relational model-finder. Alloy's bounded exhaustive search catches
  logic errors in the overlap predicate (off-by-one, wrong axis) that
  Hypothesis-based tests may miss for small instances.

### 1.2 What this model verifies

The model targets the **geometric and collision core** of the ruleset — the subset
of invariants that can be expressed as properties over finite sets of
axis-aligned bounding boxes and integers. Specifically:

| Target | Alloy concept |
|--------|---------------|
| `AABB` geometry | `sig AABB { x, y, w, h: Int }` with positivity facts |
| Non-overlap (C-1) | `assert NonOverlap` over all pairs in a `Registry` |
| ViewBox containment (G-3) | `assert ContainedInViewBox` |
| Clamp idempotence (G-4) | `assert ClampIdempotent` |
| Positive dimensions (G-5) | `fact PositiveDims` |
| Anchor consistency (G-2) | `assert AnchorConsistency` (approximate) |
| Registry append-only / isolation (C-3, C-4) | `assert RegistriesDisjoint` |
| Nudge non-zero (M-7) | `fact NudgeNonZero` on candidate set |
| Per-candidate clamp (M-4) | `pred clampThenCheck` |
| Tie-breaker consistency (§1.8) | `assert TieBreakerConsistency` |

### 1.3 What this model does NOT verify

Typography invariants (T-1 through T-6), accessibility contrast ratios (A-1 through
A-7), determinism invariants (D-1, D-2, D-4), and author contract invariants
(AC-1 through AC-6) are **not expressible** in Alloy because they require:
- String comparison and XML parsing (T-1, T-2, T-3)
- Floating-point colorimetry (A-1 through A-4)
- ARIA role hierarchies in SVG DOM structure (A-5, A-6)
- Byte-level output equality (D-1)
- Generator ordering semantics (D-2)
- Environment variable capture timing (D-4)

These are covered by the Python pytest suite and Hypothesis property tests.

---

## 2. Invariant Inventory: Encoded vs Deferred

### 2.1 Encoded invariants (8 of 42)

| Spec ID | Invariant | Alloy artefact | Notes |
|---------|-----------|----------------|-------|
| G-1 | Post-clamp AABB in registry | `fact PostClampRegistration` | Modelled structurally |
| G-2 | Anchor = geometric center ±1 px | `assert AnchorConsistency` | Integer approx; ±1 px tolerance needs `disj` |
| G-3 | No pill outside viewBox | `assert ContainedInViewBox` | Uses a `ViewBox` sig |
| G-4 | Clamp preserves dimensions | `assert ClampPreservesDims` | Checks w,h unchanged |
| G-5 | Positive dimensions | `fact PositiveDims` | Hard constraint in sig |
| C-1 | Strict non-overlap | `assert NonOverlap` | Core collision assertion |
| C-3 | Registry append-only | `assert RegistriesDisjoint` (partial) | Structural immutability |
| C-4 | Registry not shared | `assert RegistriesDisjoint` | Disjoint EmitCall registries |
| M-4 | Per-candidate clamp | `pred clampThenCheck` | Predicate, not asserted globally |
| M-7 | Nudge ≠ (0,0) | `fact NudgeNonZero` | Direct exclusion fact |

### 2.2 Partially encoded invariants (2)

| Spec ID | Invariant | Status | Reason |
|---------|-----------|--------|--------|
| G-2 | Anchor at center ±1 px | Approximate | 0.3× multiplier requires rational; modelled as integer scaled by 10 |
| C-3 | Append-only mutation | Structural only | Alloy has no mutation model; encoded as "entries of a Registry are immutable once a Registry atom exists" |

### 2.3 Unable-to-encode invariants (18)

Typography axis (T-1..T-6): require string semantics, KaTeX rendering, character-level
line-break logic. No Alloy equivalent.

Accessibility axis (A-1..A-7): require floating-point color blending, WCAG contrast
formulae, CVD simulation, and SVG ARIA role trees. No integer-relational equivalent.

Determinism axis (D-1..D-4): byte-equality (D-1) and generator ordering (D-2) require
sequence semantics with specific comparison operators not available in Alloy's relational
model. D-4 (env var capture timing) is a Python module import lifecycle concern.

### 2.4 Deferred invariants (12)

Error-handling axis (E-1..E-4) and author-contract axis (AC-1..AC-6) mix geometric
properties with prose preconditions (e.g. "headroom helpers MUST return conservative
values"). These could be partially encoded but the effort-to-gain ratio is low compared
to the Hypothesis property tests that already cover them. Deferred to a future model
revision if invariant redesign is needed.

---

## 3. Alloy Version and Toolchain

### 3.1 Version target

The model targets **Alloy Analyzer 4** (the Alloy 4 Analyzer, bundled in
`alloy4.2.jar`). The syntax `sig`, `pred`, `assert`, `fact`, `check`, `run`
is common across Alloy 4 and the Alloy 6 IDE. Where Alloy 6-specific syntax is
used (e.g., the `in` multiplicity shorthand), this is noted inline.

**Alloy 6 compatibility note**: Alloy 6 introduces `var` fields and temporal
operators (`always`, `eventually`). This model does not use them — all signatures
are static. The model is valid in both Alloy 4 (Analyzer) and Alloy 6 (new IDE).

### 3.2 Integer arithmetic warning

Alloy uses **bounded bit-vector integers**. The default scope is `Int` with 4-bit
integers, i.e., values in `[-8, 7]`. This is too small for SVG pixel coordinates
(viewBox may be 800×600 px or larger).

The model uses `int[5]` (5-bit, range `[-16, 15]`) which is sufficient to model
all the interesting counterexamples because:

- Overlap predicates only need to distinguish "overlapping" from "non-overlapping"
  configurations. The geometric structure of these cases is captured at small
  coordinate values.
- Clamp idempotence is a relational property, not a numeric one. It holds or
  fails identically at scale 8 as at scale 800.
- For the nudge grid liveness claim, 5-bit integers give enough room to represent
  pill dimensions (1..15) and viewBox boundaries (0..15) without overflow.

**Overflow risk**: Alloy integer arithmetic wraps around silently. Assertions
that sum two field values (e.g., `x + w <= vw`) must ensure no intermediate
overflow. The model uses 5-bit to ensure `x + w` stays in range for all checked
configurations.

### 3.3 Running the Analyzer

```bash
# Download Alloy 4 Analyzer (one-time):
curl -L -o alloy4.2.jar \
  https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v4.2/alloy4.2.jar

# Open the GUI:
java -jar alloy4.2.jar docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als

# Command-line execution (Alloy 6 CLI, requires alloy6.jar):
java -cp alloy6.jar edu.mit.csail.sdg.alloy4whole.ExampleUsingTheCompiler \
  docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als
```

The Alloy GUI highlights counterexamples graphically. Expected counterexample
output for the tie-breaker assertions is described in §9.

---

## 4. Bounded-Universe Design Rationale

### 4.1 Scope choice: `for 5`

All `check` commands use `for 5` (five atoms per top-level signature) unless
stated otherwise. This means:
- Up to 5 `Pill` atoms in a `Registry`
- Up to 5 `Frame` atoms per `Registry`
- Integers in range `[-16, 15]` (5-bit)

**Why 5 is sufficient**: The invariants of interest (non-overlap, viewBox
containment, registry isolation) have no monotonicity gap — they either hold
for all sizes or fail for some small configuration. Alloy's completeness
guarantee ensures: if no counterexample exists for scope 5, the assertion
holds for all structures of that bound. For overlap predicates with 2 operands,
scope 3 is already complete by the pigeonhole argument; scope 5 provides margin.

### 4.2 Scope choice: `int[5]`

5-bit integers give the range `[-16, 15]`. This is enough to:
- Represent a viewBox of width 15 and height 15
- Place pills with w,h in `[1, 7]` and centers in `[0, 14]`
- Run the nudge displacement in `[-8, 7]`

The geometry is qualitatively identical to a 1200×800 production viewBox. The
counterexamples (off-by-one in overlap predicate, clamp that changes dimensions)
will manifest at the same logical configurations regardless of absolute scale.

### 4.3 Scope for registry isolation

For `check RegistriesDisjoint`, we use `for 3 Frame` because the assertion is
about pairs of `Frame` atoms, and 3 frames produce `C(3,2) = 3` pairs, enough
to catch any sharing.

---

## 5. Signature Design

### 5.1 `sig AABB`

```alloy
sig AABB {
    x, y, w, h: Int
}
```

`x`, `y` are the **top-left corner** coordinates (SVG convention, origin top-left).
`w`, `h` are width and height (positive integers, enforced by `fact PositiveDims`).

The spec defines AABB with center coordinates `(cx, cy)`. The model converts to
top-left to simplify the overlap and containment predicates:

```
cx = x + w/2   (integer division, rounded)
cy = y + h/2
```

The conversion is stated explicitly in `pred anchorAtCenter` to keep the
invariant faithful to G-2.

### 5.2 `sig Pill` and `sig Anchor`

`Pill` extends `AABB` — it is a placed annotation pill. `Anchor` extends `AABB`
with a zero-dimension abstract representation of the target cell or arc midpoint.
Including `Anchor` allows the model to check that each `Pill` has an associated
geometric origin (G-7 leader liveness).

```alloy
sig Pill extends AABB {}
sig Anchor extends AABB {}
```

`Anchor` atoms represent natural positions (the arc midpoint or stem tip).
Their `w` and `h` fields are constrained to 0 by `fact AnchorIsPoint`, making
them degenerate AABBs used only as coordinate references.

### 5.3 `sig Registry`

```alloy
sig Registry {
    labels: set Pill
}
```

The `labels` set represents `placed_labels` — the append-only list of pills
registered during one `emit_svg` call. Alloy sets are inherently unordered and
immutable once an atom is chosen for a `check` scope, which naturally models
the append-only property.

### 5.4 `sig Frame`

```alloy
sig Frame {
    registry: one Registry
}
```

One `Frame` per `emit_svg` call. The `RegistriesDisjoint` assertion checks
that no two `Frame` atoms share a `Registry` atom or any `Pill` within their
registries, encoding C-4.

### 5.5 `sig ViewBox`

```alloy
sig ViewBox {
    vw, vh: Int
}
```

`vw` and `vh` are the declared viewBox width and height. Facts constrain
`vw > 0` and `vh > 0`. The viewBox is a global context object; in the model
exactly one `ViewBox` atom exists per `check` run (enforced by `one ViewBox`).

### 5.6 `sig NudgeCandidate`

```alloy
sig NudgeCandidate {
    dx, dy: Int
}
```

Represents one (dx, dy) offset from the natural position. `fact NudgeNonZero`
excludes the `(0, 0)` candidate (M-7 / E1566).

---

## 6. Facts: Encoding the Invariants

### 6.1 `fact PositiveDims` — G-5

```alloy
fact PositiveDims {
    all a: AABB | a.w > 0 and a.h > 0
}
```

Encodes: "Pill dimensions MUST satisfy `pill_w > 0` and `pill_h > 0`." Applied
to all AABB atoms including pills and anchors.

**Note**: `Anchor` atoms are constrained to `w = 0` and `h = 0` separately by
`fact AnchorIsPoint`, so they are exempt from `PositiveDims`. Alloy `extends`
does not automatically inherit facts, so `PositiveDims` uses `all a: AABB` which
includes the `Anchor` subset. The `AnchorIsPoint` fact overrides this only for
the anchor-specific invariant — but since `Anchor` is only used as a coordinate
reference and never enters `Registry.labels`, the dimension check on pills is
not contaminated.

**Implementation note**: In the actual `.als` file, `PositiveDims` is scoped to
`Pill` only:

```alloy
fact PositiveDims {
    all p: Pill | p.w > 0 and p.h > 0
}
```

### 6.2 `fact ViewBoxPositive`

```alloy
fact ViewBoxPositive {
    all v: ViewBox | v.vw > 0 and v.vh > 0
}
```

Ensures the viewBox has positive extent before any containment check.

### 6.3 `fact NudgeNonZero` — M-7 / E1566

```alloy
fact NudgeNonZero {
    all c: NudgeCandidate | not (c.dx = 0 and c.dy = 0)
}
```

Encodes: "`_nudge_candidates` MUST NOT yield `(0, 0)`." This is the M-7
precondition from §2.2.

### 6.4 `fact AnchorIsPoint`

```alloy
fact AnchorIsPoint {
    all a: Anchor | a.w = 0 and a.h = 0
}
```

Anchors are dimensionless points; this prevents them from appearing in overlap
checks as if they had extent.

### 6.5 Structural modelling of C-3 (append-only)

Alloy has no mutable state, so "append-only" cannot be encoded as a temporal
constraint. Instead, C-3 is modelled structurally: the `Registry.labels` set is
fixed at instantiation. No predicate or fact modifies it. The assertion
`RegistriesDisjoint` checks cross-frame isolation (C-4), which is the testable
consequence of C-3 at spec level.

---

## 7. Predicates: Geometric Primitives

### 7.1 `pred overlaps` — C-1 core

```alloy
pred overlaps [a, b: AABB] {
    -- Two closed rectangles overlap (share at least one point) iff their projections
    -- overlap on both axes. Strict non-intersection means NOT overlaps[a, b].
    (a.x).plus[a.w] >= b.x
    and (b.x).plus[b.w] >= a.x
    and (a.y).plus[a.h] >= b.y
    and (b.y).plus[b.h] >= a.y
}
```

**Design note**: The `.plus[]` Alloy built-in performs integer addition with
overflow semantics within the current bit-width. For the 5-bit integer domain,
`x + w <= 15` is maintained by the viewBox containment fact, so no overflow
occurs in the overlap predicate for any valid pill placement.

**Closed rectangles**: The spec says "strict non-intersection of closed
rectangles" (C-1). Closed means the edges are included in the rectangle. Two
axis-aligned closed rectangles with corners touching (e.g., right edge of A at
x=5 and left edge of B at x=5) DO overlap under this definition. The `>=`
operator above captures this correctly.

### 7.2 `pred withinViewBox` — G-3

```alloy
pred withinViewBox [p: Pill, v: ViewBox] {
    p.x >= 0
    and p.y >= 0
    and (p.x).plus[p.w] <= v.vw
    and (p.y).plus[p.h] <= v.vh
}
```

### 7.3 `pred clampThenCheck` — M-4

This predicate models the per-candidate clamp from §2.1 (M-4 normative note):
a candidate is accepted only if it passes the collision check AFTER clamping.

```alloy
pred clampThenCheck [candidate: Pill, registry: Registry, v: ViewBox] {
    -- The clamped version of candidate is within viewBox
    withinViewBox[candidate, v]
    -- And it does not overlap any pill already in the registry
    and all existing: registry.labels | not overlaps[candidate, existing]
}
```

The model cannot represent the clamp transformation itself (translating the
center into range) because that would require mutable state. Instead, we assert
that any pill in the registry satisfies `withinViewBox` (i.e., it was placed
post-clamp) and check that the accepted candidate also satisfies it.

### 7.4 `pred anchorAtCenter` — G-2 (approximate)

```alloy
-- Approximate G-2: anchor x matches pill center within ±1
-- Anchor cx is encoded as pill.x + pill.w/2 (integer division)
-- We check |anchor.x - pill_center_x| <= 1 and |anchor.y - pill_center_y| <= 1
pred anchorAtCenter [p: Pill] {
    let cx = (p.x).plus[p.w.div[2]] |
    let cy = (p.y).plus[p.h.div[2]] |
    -- We cannot check against actual anchor without anchor atom linkage;
    -- this predicate is used in the anchorConsistency assertion with explicit pairing
    cx >= p.x and cx <= (p.x).plus[p.w]
    and cy >= p.y and cy <= (p.y).plus[p.h]
}
```

**G-2 tolerance note**: The spec allows ±1 px. With integer division in Alloy,
`w/2` rounds toward zero. For odd widths, the center is off by 0.5 px, which
rounds to 0 or 1 depending on direction. The model treats this as acceptable:
`|cx_model - cx_rendered| <= 1` is always satisfied by integer division.

---

## 8. Assertions and `check` Commands

### 8.1 `assert NonOverlap` — C-1

```alloy
assert NonOverlap {
    all r: Registry |
        all disj p1, p2: r.labels |
            not overlaps[p1, p2]
}

check NonOverlap for 5 but 5 int
```

**Expected result**: This assertion is NOT automatically satisfied. It states
a desired property of any `Registry` built by a correct implementation. To make
the assertion checkable, the model must add a fact that constrains registries to
only contain non-overlapping pills. The `check` command here will find a
counterexample (two overlapping pills in a registry) which tells us: the
**implementation** must enforce C-1, not the model itself.

The value of the `check` is: if we add `fact PlacedLabelsNonOverlap { all r:
Registry | all disj p1,p2: r.labels | not overlaps[p1,p2] }`, then `check
NonOverlap` passes, confirming the fact correctly expresses the invariant.
This validates our `overlaps` predicate against edge cases (touching edges,
zero-size pills).

### 8.2 `assert ContainedInViewBox` — G-3

```alloy
assert ContainedInViewBox {
    all r: Registry |
    all v: ViewBox |
    all p: r.labels |
        withinViewBox[p, v]
}

check ContainedInViewBox for 5 but 5 int
```

**Expected result**: Counterexample found immediately (pills not constrained to
viewBox by default). This is intentional: the assertion verifies the predicate
logic is correct and that the implementation must enforce it. Combined with
`fact ClampedPillsInViewBox`, the assertion should pass.

### 8.3 `assert ClampPreservesDims` — G-4

```alloy
-- Model clamp as a function from pre-clamp to post-clamp AABB.
-- Since Alloy has no functions, we model it as a relation: PreClamp -> PostClamp.
sig ClampPair {
    pre: one AABB,
    post: one AABB
}

assert ClampPreservesDims {
    all cp: ClampPair |
        cp.pre.w = cp.post.w
        and cp.pre.h = cp.post.h
}

check ClampPreservesDims for 5 but 5 int
```

**Expected result**: With no additional facts, counterexamples exist (any
ClampPair where pre.w ≠ post.w). Add `fact ClampOnlyTranslates { all cp:
ClampPair | cp.pre.w = cp.post.w and cp.pre.h = cp.post.h }` and the
assertion passes, validating that our constraint correctly captures G-4.

### 8.4 `assert RegistriesDisjoint` — C-4

```alloy
assert RegistriesDisjoint {
    all disj f1, f2: Frame |
        f1.registry != f2.registry
        and no (f1.registry.labels & f2.registry.labels)
}

check RegistriesDisjoint for 3 Frame, 5 but 5 int
```

**Expected result**: With no facts, counterexample found. With `fact
UniqueRegistries { all disj f1, f2: Frame | f1.registry != f2.registry }` and
`fact NoPillSharing { all disj f1, f2: Frame | no (f1.registry.labels &
f2.registry.labels) }`, the assertion passes.

### 8.5 `assert TieBreakerConsistency` — §1.8

This assertion checks that the six tie-breakers in §1.8 are mutually
consistent — that is, no pair of tie-breakers requires simultaneously satisfying
contradictory properties.

The tie-breakers (abbreviated):
- TB-1: C-1 wins over AC-3 (non-overlap over declared position)
- TB-2: G-3 wins for clipping; AC-1 minimum (emit AND clamp)
- TB-3: T-4 wins for under-estimation (over-estimate ok; nudge resolves)
- TB-4: A-1 wins (contrast floor over opacity design)
- TB-5: G-5 wins (empty label → config error, no emission)
- TB-6: D-1 is compat-critical (byte-identical output)

Geometric tie-breakers TB-1, TB-2, and TB-5 are expressible in Alloy:

```alloy
-- TB-1: Non-overlap (C-1) takes priority over declared position (AC-3).
-- Consequence: a pill may appear in a position other than declared, but
--   the registry is always non-overlapping.
-- In the model: if two pills would overlap at the declared position, exactly
--   one of them is displaced. Both still exist in the registry.
assert TB1_C1_Wins {
    -- All registries that satisfy NonOverlap also have all pills present
    -- (AC-1: pill must appear). These are simultaneously satisfiable.
    all r: Registry |
        (all disj p1,p2: r.labels | not overlaps[p1,p2])
        -- implies at least one pill exists (AC-1 minimum)
        implies some r.labels
}

-- TB-2: Emit AND clamp. The model checks that G-3 (containment) and
--   AC-1 (pill exists) are simultaneously satisfiable.
assert TB2_EmitAndClamp {
    all v: ViewBox |
        some r: Registry |
            some p: r.labels |
                withinViewBox[p, v]
}

-- TB-5: G-5 wins — zero-dimension pills must not be in any registry.
--   PositiveDims fact already encodes this; we assert the consequence.
assert TB5_G5_Wins {
    all r: Registry | all p: r.labels | p.w > 0 and p.h > 0
}

check TieBreakerConsistency_TB1 for 5 but 5 int
check TieBreakerConsistency_TB2 for 5 but 5 int
check TieBreakerConsistency_TB5 for 5 but 5 int
```

**Expected results**: See §9 for detailed analysis.

---

## 9. Tie-Breaker Consistency Analysis

### 9.1 Expected outcomes

The six tie-breakers in §1.8 are expected to be **mutually consistent** — there
is no configuration where following all six simultaneously produces a
contradiction. This analysis explains why each geometric tie-breaker assertion
is expected to pass, and what a counterexample would mean.

| Tie-breaker | Assertion | Expected result | Counterexample meaning |
|-------------|-----------|-----------------|------------------------|
| TB-1: C-1 vs AC-3 | `TB1_C1_Wins` | PASS | Would mean non-overlap and pill existence are contradictory — impossible for finite viewBox with positive dimensions |
| TB-2: G-3 vs AC-1 | `TB2_EmitAndClamp` | PASS | Would mean no pill can exist inside a positive-dimension viewBox — clearly impossible |
| TB-5: G-5 vs AC-1 | `TB5_G5_Wins` | PASS (given `PositiveDims` fact) | Would mean PositiveDims fact is inconsistent with registry contents |

### 9.2 TB-3, TB-4, TB-6: non-geometric, expected consistent

TB-3 (T-4 over-estimation allowed; nudge resolves) is a SHOULD-strength policy
stating that over-estimating pill width is acceptable. It interacts with C-1 only
through the nudge grid — wider pills require more nudge, but the nudge always
terminates (32 candidates is finite). No contradiction possible.

TB-4 (A-1 wins over opacity design) is a contrast ratio constraint. It cannot
conflict with geometric invariants — contrast is a color property, geometry is
a position property. Independent axes. Consistent by construction.

TB-6 (D-1 byte-identical) is a determinism constraint. It conflicts with nothing
in the geometric or collision model. D-1 is ensured by the algorithm being
deterministic; it does not impose any geometric requirement.

### 9.3 Most interesting case: TB-1 vs TB-2

The tension between "non-overlap (C-1)" and "always emit (AC-1)" in a dense
scene with many pills looks like it could produce a contradiction. In practice:

- C-1 wins over declared position (AC-3), NOT over existence (AC-1).
- The spec says: emit at the last-attempted position when all 32 candidates
  are exhausted (E-1), even if that position overlaps.
- So C-1 is a **best-effort** MUST, not an absolute MUST when the nudge grid
  is exhausted. This is why the model includes E-1 in the deferred set.

The Alloy assertion TB1_C1_Wins checks: if C-1 IS satisfied (no overlap), then
AC-1 is also satisfied (some pill exists). This direction is trivially true and
is expected to PASS.

The reverse — "AC-1 satisfied ⟹ C-1 satisfied" — is FALSE in the exhausted-grid
case (E-1). The model does NOT assert this direction, which is correct.

---

## 10. Invariants That Cannot Be Encoded in Alloy

### 10.1 Typography axis (T-1..T-6)

Alloy operates over relational structures of atoms, sets, and integers. It has
no native string type, no character-level operations, and no regex matching.

- **T-1** (label text matches author declaration): requires string equality.
  Cannot be encoded.
- **T-2** (no hyphen line-break): requires string search for `-` character.
  Cannot be encoded.
- **T-3** (math labels not wrapped): requires detecting `$...$` span structure
  in a string. Cannot be encoded.
- **T-4** (estimator within 20 px): requires floating-point arithmetic and
  comparison against rendered text width. Cannot be encoded.
- **T-5** (font size ≥ 9 px): requires reading `ARROW_STYLES` dict values.
  Could be partially encoded as `all t: ColorToken | t.fontSize >= 9`, but
  Alloy would require a `ColorToken` sig with integer `fontSize` field. This
  is mechanically possible but adds a sig with no interaction with the
  geometric model, providing no additional assurance.
- **T-6** (pill height formula): requires multiply (`num_lines * font + 2*PAD_Y`).
  Alloy's integer multiply is available but the formula involves configuration
  constants not present in the geometric model. Deferred.

### 10.2 Accessibility axis (A-1..A-7)

All contrast and colorimetry assertions require:
- Floating-point sRGB color arithmetic (WCAG relative luminance formula uses
  gamma correction: `c/12.92` or `((c+0.055)/1.055)^2.4`).
- Alloy has no floating-point support whatsoever.

CVD simulation (A-4), ARIA role hierarchies (A-5, A-6), and forced-colors media
queries (A-7) all require DOM tree operations or browser rendering pipelines.
None are modelable in Alloy.

### 10.3 Determinism axis (D-1..D-4)

- **D-1** (byte-identical SVG): Alloy has no notion of serialized byte strings.
- **D-2** (nudge candidate order): Alloy's set operations are unordered.
  The `NudgeCandidate` sig models the SET of candidates, not their iteration
  ORDER. Ordering requires a sequence type (`seq`) which Alloy supports, but
  the model would need to encode the full Manhattan-distance sort key, adding
  significant complexity for marginal gain over the existing `TestQW2NudgeGrid`
  unit tests.
- **D-4** (env var captured once at import): a Python module lifecycle property.
  No formal encoding applies.

### 10.4 Error-handling and author-contract axes (E-1..E-4, AC-1..AC-6)

These invariants mix geometric properties with runtime preconditions:
- **E-1** (last-attempted position on exhaustion): requires reasoning about
  iteration state (which candidate was last), which is a sequence/temporal
  property outside Alloy's static relational model.
- **E-3** (unknown color falls back to `info`): a lookup table fallback; no
  geometric content.
- **AC-5** (headroom conservative): requires reasoning about the headroom
  helper's output vs. pill height for arbitrary annotation sets. Could be
  expressed as a Hypothesis property test but not an Alloy assertion without
  encoding the headroom formula.
- **AC-6** (math headroom symmetric): similar to AC-5.

---

## 11. How to Run the Model

### 11.1 Using the Alloy GUI (recommended for debugging)

1. Download Alloy Analyzer 4 from
   `https://github.com/AlloyTools/org.alloytools.alloy/releases/latest`
2. Run: `java -jar alloy4.2.jar`
3. Open file:
   `docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als`
4. Select `Execute → Check NonOverlap for 5 but 5 int` from the Execute menu.
5. Alloy will display either "No counterexample found" or a graphical
   counterexample showing the violating instance.

### 11.2 Using the Alloy CLI (for CI use)

Alloy does not ship an official command-line runner. Community options:

**Option A: `alloy-runner` (Gradle plugin)**
```bash
./gradlew alloyCheck --model=docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als
```

**Option B: Python `alloytools` wrapper**
```bash
pip install alloytools
alloy check docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als
```

**Option C: Alloy 6 compiler API (Java)**
```java
CompModule world = CompUtil.parseEverything_fromFile(A4Reporter.NOP, null, "smart-label-model.als");
A4Options opt = new A4Options();
for (Command cmd : world.getAllCommands()) {
    A4Solution sol = TranslateAlloyToKodkod.execute_command(A4Reporter.NOP, world.getAllReachableSigs(), cmd, opt);
    System.out.println(cmd.label + ": " + (sol.satisfiable() ? "SAT (counterexample)" : "UNSAT (passes)"));
}
```

### 11.3 Expected output format

For each `check` command, Alloy produces one of:

```
Executing "Check NonOverlap for 5 but 5 int"
   No counterexample found. NonOverlap may be valid. 6ms.
```

or

```
Executing "Check NonOverlap for 5 but 5 int"
   Counterexample found. NonOverlap is not valid. 3ms.
   [Graphical instance shown in GUI]
```

For assertions that encode DESIRED properties (TB-1, TB-2, TB-5) with the
supporting facts active, all `check` commands should output "No counterexample
found." For assertions that test the PREDICATE LOGIC without supporting facts
(e.g., bare `check NonOverlap`), counterexamples are expected and are used to
validate the predicate.

---

## 12. CI Integration Note

### 12.1 Current recommendation: NOT in critical CI path

The Alloy model is `[EXPERIMENTAL]` per the spec. It should not block the test
suite or block PRs. Recommended integration:

```yaml
# .github/workflows/alloy-model.yml
name: Alloy model check (non-blocking)
on:
  push:
    paths:
      - 'docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als'
      - 'docs/formal/smart-label-model.als'
  workflow_dispatch:

jobs:
  alloy-check:
    runs-on: ubuntu-latest
    continue-on-error: true   # non-blocking
    steps:
      - uses: actions/checkout@v4
      - name: Download Alloy
        run: |
          curl -L -o alloy4.2.jar \
            https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v4.2/alloy4.2.jar
      - name: Run checks
        run: |
          java -cp alloy4.2.jar edu.mit.csail.sdg.alloy4whole.RunAlloy \
            docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als
```

### 12.2 Promotion path to blocking CI

The model becomes blocking CI when:
1. All `check` commands pass consistently across Alloy 4 and Alloy 6.
2. The model is moved to `docs/formal/smart-label-model.als`.
3. The spec Appendix B is updated from `[EXPERIMENTAL]` to `[STABLE]`.
4. At least one round of formal review by a second engineer confirms the
   invariant encodings are faithful to the prose spec.

### 12.3 Relationship to Hypothesis property tests

Alloy and Hypothesis are complementary:

| Dimension | Alloy | Hypothesis |
|-----------|-------|------------|
| Coverage | Exhaustive for bounded scope | Random + shrinking |
| Arithmetic | Bounded integers (wrap-around risk) | Arbitrary precision |
| Strings | Not supported | Full Python types |
| Setup cost | High (learn Alloy syntax) | Low (pytest + strategy) |
| Debugging | Graphical counterexample | Minimal failing example |
| Best for | Proving structural properties | Catching implementation bugs |

The workflow is: Alloy validates the geometric model; Hypothesis validates the
Python implementation against randomly generated inputs.

---

## 13. Known Limitations and Future Work

### 13.1 Integer overflow

Alloy's bounded integers wrap around silently. The model uses `int[5]` (range
`[-16, 15]`) to keep sums like `x + w` within range. For production SVG
coordinates (up to 2000 px), this is a significant abstraction. Future work:
encode the model using abstract `Int` with explicit range constraints rather
than bit-vector integers.

### 13.2 No sequence semantics for nudge order

The `NudgeCandidate` sig models the SET of candidates, not their ordered iteration.
D-2 (deterministic iteration order) and C-5 (preferred half-plane first) cannot be
checked. Adding `seq NudgeCandidate` and encoding the sort key would allow this,
at the cost of ~50 additional model lines and significantly longer solve times.

### 13.3 No floating-point arithmetic

The 0.3× anchor offset (G-2), contrast ratios (A-1..A-4), and text width estimation
(T-4) all require floating-point or rational arithmetic. Alloy 6 does not support
these. An alternative: encode them as fixed-point integers (multiply by 100) at
the cost of readability. Deferred.

### 13.4 G-2 anchor precision

The current `anchorAtCenter` predicate uses integer division `w/2`, which is
off by 0.5 px for odd-width pills. The spec allows ±1 px tolerance. The model
respects this but cannot distinguish "exactly correct" from "correct within 1 px"
at the integer level. A future refinement could encode half-pixels as
`2*x + parity` to gain sub-pixel precision.

### 13.5 E-1 (last-attempted on exhaustion) is unmodelled

E-1 requires reasoning about "the 32nd candidate" specifically, which is an
iteration index — a temporal property. Future work: encode the nudge grid as
an ordered sequence and assert that when all 32 positions are checked and all
overlap, the placement is set to position 32, not position 0 (natural position).

---

*End of design notes. The companion `.als` file is at:*
`docs/archive/smart-label-ruleset-hardening-2026-04-21/smart-label-model.als`
