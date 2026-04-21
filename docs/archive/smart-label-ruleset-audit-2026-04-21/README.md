# Smart-Label Ruleset Audit — 2026-04-21

Deep parallel audit of `docs/spec/smart-label-ruleset.md` across 10 axes,
performed by 10 opus agents running in parallel. Target: validate the
ruleset as shipped (Phase 0 QW-1..QW-7 + MW-1) and produce a concrete
action list before any further MW work.

## Start here

- **[00-synthesis.md](00-synthesis.md)** — executive summary, P0/P1/P2
  action list, numeric scorecard, revised MW roadmap, ruleset deltas.

## Per-axis reports

| # | File | Lines | What |
|---|------|-------|------|
| 1 | [01-invariant-gaps.md](01-invariant-gaps.md) | 450 | I-1..I-10 per-invariant audit, implicit rules, dead code. 2 HIGH gaps (I-2 pad mismatch, position-only uses different algorithm). |
| 2 | [02-algorithm-soundness.md](02-algorithm-soundness.md) | 604 | 10 formal properties of `_nudge_candidates`. 7 VERIFIED, 1 UNSPECIFIED, 2 FALSIFIABLE (MEDIUM clamp race). |
| 3 | [03-primitive-coverage.md](03-primitive-coverage.md) | 395 | 15-primitive capability matrix. 2 fully wired, 6 headroom-missing, 3 orphans, 4 dark. |
| 4 | [04-test-coverage.md](04-test-coverage.md) | ~500 | 73 % line+branch coverage (gate 75 %). Invariant ↔ test mapping + uncovered-path list. |
| 5 | [05-math-width-audit.md](05-math-width-audit.md) | 490 | 20-label empirical study. QW-5 1.15× multiplier is backwards — recommend 0.90×. |
| 6 | [06-visual-regression.md](06-visual-regression.md) | 392 | 52 files × 610 frames classified. Only 12.7 % of pill frames clean. |
| 7 | [07-mw-roadmap-feasibility.md](07-mw-roadmap-feasibility.md) | 576 | MW-2/3/4 precise specs, cost, ordering. Recommends inverted order: MW-3 → MW-2 → MW-4a. |
| 8 | [08-prior-art.md](08-prior-art.md) | 782 | 10 libraries compared. 3 concrete ports recommended (Vega occupancy, Mapbox anchors, d3fc argmin). |
| 9 | [09-performance.md](09-performance.md) | 561 | Microbench + profile. `_nudge_candidates` sort dominates. 3.1× + 27× easy wins in MW-2. |
| 10 | [10-accessibility.md](10-accessibility.md) | 763 | WCAG contrast, CVD, screen-reader audit. 4/6 tokens FAIL after opacity compositing. |

## Supporting artifacts

| Path | Contents |
|------|----------|
| `math-samples/` | 20 `.tex` math-label test inputs + `results.json` from audit #5 |
| `repros/rendered/` | 52 rendered HTML from audit #6 |
| `repros/screenshots/` | 475 PNG screenshots + `manifest.json` |

## How to use this audit

1. Read `00-synthesis.md` end to end. ~15 min.
2. For each P0 item (A1..A5), open the cited per-axis report and read the
   referenced section for the repro + rationale.
3. Ship P0 as a batch. Re-run audit #6 visual regression to confirm
   improvement.
4. Start MW-3, following the revised roadmap in synthesis.
5. Update `docs/spec/smart-label-ruleset.md` per synthesis §"What changes
   in the ruleset itself" after each MW ships.

## Scope deliberately excluded

See `00-synthesis.md` §"What this audit did NOT cover". Temporal coherence,
interactive features, two-pass KaTeX measurement, cross-primitive registry,
and priority-weighted culling are out of scope for this audit round.

## Status

All 10 agents completed. Synthesis written. Ruleset not yet patched —
ruleset deltas ship with P0 batch.
