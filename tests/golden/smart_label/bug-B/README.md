# bug-B

## What this fixture guards

Regression guard for the self-loop annotation bug: when `arrow_from` equals
the target cell, the src and dst coordinates are identical (zero displacement).
This triggers division-by-zero in the direction-vector normalisation step,
which produces `NaN` in the arrowhead `<polygon>` coordinate data in the
pre-fix state.

## Invariants exercised

§2.4 (self-loop guard), G-5 (no NaN/Inf in SVG path/polygon coordinate data)

## Pre-fix vs post-fix

| State | Behaviour |
|-------|-----------|
| Pre-fix (current) | Arrow emitted with degenerate geometry; no NaN in path data because the Cubic Bezier fallback is used |
| Post-fix (target) | Arrow suppressed or safe stub; explicit guard at direction-vector normalisation |

**BLOCKER**: The ISSUE-below-math (AC-6) fix from Stream A had not yet landed
on main as of 2026-04-21. The `expected.sha256` captures the pre-fix rendered
output. This fixture is marked `known_failing: false` because the current
rendering matches the pinned expectation — it tracks whether the rendering
changes unexpectedly, not whether the bug is fixed.

## Rebase trigger notes

Rebase when:
- The AC-6 / self-loop guard fix lands on main: re-capture expected.svg,
  update SHA256, and set `known_failing: false` (fix is now the expected state).
- Any geometry constant or Bezier control-point formula changes.

Command to rebase:

```bash
SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/smart_label/ -k bug-B
git diff tests/golden/smart_label/bug-B/
```
