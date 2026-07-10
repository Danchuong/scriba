# JudgeZone 2026-07-08 batch (#9–#14) — structural closure summary

**Date:** 2026-07-10 · **Tree:** uncommitted on main (no version bump/CHANGELOG
yet — release is a separate step) · **Process:** 5 investigation agents →
5 patcher agents (wave 1) → 5 sweep agents (wave 2) → consolidation.

## Verdict per reported bug (final-tree repro renders)

| Bug | Verdict | Structural fix (contract) |
|---|---|---|
| #9 dark bracket occlusion | CONFIRMED → FIXED | Theme-attr contract: dark pill rule scoped `[fill="white"]` both scopes |
| #14 plane2d chip dark | CONFIRMED → FIXED | `scriba-plane-label-pill/-text` classes + dark pair + media twin |
| #11 `${` narrate shred | CONFIRMED (root cause RELOCATED: tex/renderer.py shield, not lexer) → FIXED | `${...}` = interp ⟺ identifier-shaped; math falls through; E1161 for structured values |
| #12 caret vs caption | CONFIRMED (independent of labels=/id-length) → FIXED | `_below_lane_height()` folds `_cursor_extent_below()`; band tenants disjoint by reservation |
| #13 label `_` family | 1 PARTIAL (real cause: unmeasured trailing space) + 3 CONFIRMED → FIXED | measure == paint == announce; one interpretation, 3 consumers |
| #10 diagram title leak | CONFIRMED (worse: leaks even with label=; + silent-step leak) → FIXED | Accessible-name policy: label/title/narration or NO `<title>`; id never |

## Structural asks (reporter's 5) — all delivered

1. **Theme-attr audit:** 40-site audit; 19 sites fixed wave 1; sweep found 3
   more (tex CSS media-twin gap ×2 files, KaTeX `#cc0000` inline WCAG fail,
   standalone.css twin). Enforcement: `test_theme_attr_contract.py`
   (table + mechanical scanner + twin-parity classes).
2. **`${` grammar contract:** identifier-shape gate at the shield
   (tex/renderer.py) + E1161 fail-loud for structured values + sweep closed
   the REVERSE risk (label=/note= now shield `${ident}` before `$`-pairing,
   same regex). Blast surface mapped: only narrate/invariant ever corrupted.
3. **One reservation model for below-cell band:** shared-helper fix covers
   Array/Grid/DPTable/Queue/Stack/NumberLine; sweep found + fixed 2 more
   4th-tenant bugs (`position=below` pill vs caret, same+cross cell) via
   `_cursor_aware_below_baseline()`; 11 no-cursor primitives pinned no-op.
   `test_below_band_lanes.py` = the lane contract.
4. **measure==paint==announce:** wave 1 fixed the annotation-pill channel
   (4 defects + `state:X` color resolver); sweep found + fixed the `value=`
   channel (same signature, 4 shared fns). Hypothesis property tests +
   multiline invariants pin it.
5. **Accessible-name policy:** shared `<title>` builder fixed (diagram +
   silent-step); corpus-level conformance test
   (`tests/conformance/test_r15_accessible_name_policy.py`, 215 asserts);
   R-15 spec text + svg-emitter.md synced; E1050/E1054 guidance updated.

## Sweep-wave discoveries beyond the reports (all fixed structurally)

- Reverse interp corruption in label=/note= (mirror of #11) + a 2nd exposure
  via the JZ-13 fast path.
- 2 below-band 4th-tenant overlaps (13.2px, 4.0px).
- `value=` channel painted/measured raw `\_`/`\texttt{}` (3/4 combos).
- KaTeX unknown-command fallback: hardcoded `#cc0000` = 2.88:1 on dark
  (default path) → `var(--scriba-error)`.
- Animation silent-step `<title>` id leak (not in original report).
- docs/graph-stable-layout.md `${range(25)}` example was silently
  non-functional → corrected idiom.

## Verification

- Full tree suite (everything, goldens included): GREEN — 6063+ passed,
  0 failed. Two cross-agent interactions surfaced and were fixed by the
  lead during consolidation, both test-side: (1) a pinned literal in
  `test_group_label_obstacle.py` gained the new `scriba-group-label-text`
  class; (2) `test_primitive_css_centering.py::test_all_scriba_classes_have_rules`
  assumed every class rule lives in scriba-scene-primitives.css — outdated
  once per-primitive sheets legitimately own rules (plane2d dark pair);
  the guard now aggregates all `scriba/animation/static/*.css` (a
  structural widening of the guard itself, message updated).
- Golden corpora: examples 107 re-blessed ×2 rounds (diff shapes reviewed:
  shared-CSS growth, MetricPlot var() fills, net −38 title leaks → 0
  remaining, +1px anim_clarity, class attrs); smart_label 3 re-blessed
  (class-only, human-reviewed); animation fixtures untouched. All golden
  suites: 110 passed + 1 xfailed.
- 6/6 original repros re-rendered on the final tree and verified.
- detect_changes: 62 changed source symbols / 13 files — exactly the agents'
  owned scope. risk_level critical = expected hub fan-out (label pipeline,
  frame renderer), mitigated by the suites above.

## Deferred (logged in deferred-work.md)

- `\includegraphics alt=` option key (documented contract, feature-sized).
- `\note text=` stray backslash before `${x}` (cosmetic, upstream plumbing).
- Corpus coverage gap: no golden exercises `\_`/`\texttt` inside `values=`
  (unit/property tests cover it; corpus fixture optional).

## Release checklist when requested (AGENTS.md)

Rendered bytes changed corpus-wide ⇒ SCRIBA_VERSION 29→30 + ledger docstring +
`test_zoom.py::test_scriba_version_unchanged`, CHANGELOG entry, README/docs
sync, then PyPI (`scriba-tex`, key.env).

## Artifacts index

- investigations/judgezone-{09-14,10,11,12,13}-*.md (5)
- spec-fix-judgezone-{09-14,10,11,12,13}-*.md (5, each with wave-2 section)
