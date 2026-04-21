# docs/formal — Scriba Formal Models

Bounded exhaustive proofs for smart-label placement invariants.

## smart-label-model.als

**Tool:** Alloy 6 (Alloy Analyzer 4.2+ compatible)
**Spec:** `docs/spec/smart-label-ruleset.md` §1 + §2
**Design notes:** `docs/archive/smart-label-ruleset-hardening-2026-04-21/07-alloy-model.md`

### What it proves

11 `check` commands verified exhaustively at 5-bit integer scope (range [-16, 15],
up to 5 atoms per signature):

| Check | Invariant | Result |
|-------|-----------|--------|
| CHECK-1 | C-1: No two placed pills overlap | PASS |
| CHECK-2 | G-3: All pills inside viewBox | PASS |
| CHECK-3 | G-5: Pills have positive dimensions | PASS |
| CHECK-4 | G-4: Clamp preserves dimensions | PASS |
| CHECK-5 | C-4: Registries disjoint across frames | PASS |
| CHECK-6 | G-2 (approx): Anchor center inside pill AABB | PASS |
| CHECK-7 | M-7: Nudge grid excludes (0, 0) | PASS |
| CHECK-8 | G-4 (idempotence): Re-clamping in-range pill is no-op | PASS |
| CHECK-9 | TB-1: Non-overlap and existence are compatible | PASS |
| CHECK-10 | TB-2: Emit-and-clamp simultaneously satisfiable | PASS |
| CHECK-11 | TB-5: Zero-dim pills excluded from registries | PASS |

### Invariants NOT encoded

T-1..T-6 (text-fit), A-1..A-7 (anchor curves), D-1..D-4 (decoration),
E-1..E-4 (edge-case handling), AC-1..AC-6 (anti-collision heuristics).
These require continuous geometry beyond Alloy's integer domain.

### How to run

```bash
java -jar alloy4.2.jar docs/formal/smart-label-model.als
```

In the Alloy Analyzer GUI: **Execute > Check All** runs all 11 checks.
**Run > ShowTwoPills** (and the other `run` commands) generate illustrative instances.

### Integer scope note

The model uses 5-bit integers (`5 but 5 Int`), giving range [-16, 15]. Pixel
coordinates in production SVGs are much larger, but the invariants are
scale-independent: the proofs hold for any concrete pixel scale because all
constraints are relational (>=, <=, +) with no hardcoded pixel values.

### CI status

**Doc-only — not CI-gated.** The Alloy Analyzer requires a JVM and is not
installed in CI. The model is provided for design verification and audit
purposes only. A future task may add an optional `make formal-check` target.
