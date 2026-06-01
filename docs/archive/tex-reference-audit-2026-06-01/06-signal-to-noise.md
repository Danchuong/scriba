# Signal-to-Noise Audit

**Document:** `docs/SCRIBA-TEX-REFERENCE.md` (1494 lines)
**Criterion:** Signal-to-noise — how much author-facing content is actually noise (no-ops, dev/debug flags, internal-spec jargon, maintainer trivia, niche params).
**Date:** 2026-06-01

## Verdict & Score

**Score: MEDIUM-HIGH (clean overall, with a few concentrated noise pockets).**

The document is mostly high-signal: the primitive catalog (§7), selectors (§8), examples (§9), and most gotchas (§13) are exactly what an author needs. The noise is **concentrated**, not pervasive — it clusters in three places: the §5.8 annotation placement internals (R-22 / `side_hint` / Hirsch-1982 / R-06 / GEP version notes), a handful of forward-compat / niche Graph params in §7.4, and three §13 gotchas that document no-ops or env vars an author can never use.

**Estimated noise fraction: ~6–8% of the document** (roughly 90–120 lines of true noise out of 1494), heavily weighted toward §5.8 and §13.11–13.12. The body would lose nothing for authors if these moved to an internal appendix.

## Findings

| # | Item (line) | Category | Why it's noise | Recommendation | Severity |
|---|-------------|----------|----------------|----------------|----------|
| 1 | `side_hint` auto-inference block + Hirsch-1982 + R-06 + "planned v0.12.0" (§5.8, L361–371) | (c) internal-spec jargon + version-planning | `side_hint` is an **internal computed value** (confirmed `_svg_helpers.py:492`), not an author key — the author key is `side=`. The citation "Hirsch 1982 NE-preference ladder", rule IDs R-22/R-06, and "planned v0.12.0" are placement-engine spec details. None of it changes what the author writes. | MOVE-TO-APPENDIX (keep one plain sentence: "when `side=` is omitted, placement is auto-inferred from arrow direction; left-to-right arcs default to a pill above the arc") | **High** — densest noise block; reads like spec leakage mid-reference |
| 2 | `global_optimize` param row (§7.4, L685) | (a) no-op / forward-compat | Confirmed pure no-op in `graph.py:680–691`: sets a field, emits a `UserWarning`, does nothing else. "SA post-refine (GEP-20)" is maintainer jargon. | DROP from the param table (or MOVE to appendix). An author should never type it. | **High** — actively harmful: invites use of a flag that only produces a warning |
| 3 | §13.11 `Graph(global_optimize=True)` is a no-op (L1433–1434) | (a) no-op | Documents the same no-op again as a "gotcha." A gotcha about a flag nobody should set is circular noise. | DROP (fold into appendix with #2) | **Medium** — duplicates #2; only exists because #2 exists |
| 4 | §13.12 `SCRIBA_DEBUG_LABELS` / `SCRIBA_LABEL_ENGINE` (L1436–1444) | (b) dev/debug env vars | Confirmed dev-only (`_svg_helpers.py:34`, consumed at import). "Never enable in production", "for engine development", "deprecated, removed in v3.0", file path `_svg_helpers.py` — all maintainer-facing. An editorial author never sets env vars. | MOVE-TO-APPENDIX (or DROP — these belong in `spec/smart-label-ruleset.md`, already cross-referenced at L344) | **High** — pure dev surface in an author reference |
| 5 | `tint_by_source` / `tint_by_edge` rows (§7.4, L683–684) | (d) niche params | Verified **functional** (`graph.py:1368–1376`), so not a no-op — but extremely niche (tinting edge-weight pills by node/edge state color). >95% of editorials never touch them. | KEEP but demote — acceptable in a param table; consider a one-line "advanced" note. Not worth removing. | **Low** |
| 6 | §5.8 callout: "Read [smart-label-ruleset.md] before changing `_svg_helpers.py` or any primitive's `emit_svg`" (L343–347) | (c) maintainer trivia | This instruction is for **code maintainers**, not `.tex` authors. "Before changing `_svg_helpers.py`" has zero meaning for someone writing editorials. | MOVE-TO-APPENDIX or trim to a bare "see spec for placement internals" pointer | **Medium** |
| 7 | `grid` diagram option "accepted but currently ignored" (§10, L1267) | (a) forward-compat placeholder | A documented no-op option. Telling an author about an option that does nothing is anti-signal. | DROP from the options table (move to appendix if retention matters) | **Medium** |
| 8 | "R-32" rule ID in §13.8 heading (L1414) | (c) internal-spec jargon | The gotcha itself (headroom reserved at per-scene max) is **genuinely useful** signal. Only the "(R-32)" tag is noise — authors don't reference rule IDs. | KEEP the gotcha; DROP the "(R-32)" tag | **Low** |
| 9 | "v0.8.2" / "since v0.10.0" / version inline notes (L492, L1442, etc.) | (c) version-planning | Scattered "supported since vX" notes. Mild noise — useful only if an author pins an old version, which is rare. | KEEP where it gates a feature an author might rely on; otherwise harmless | **Low** |
| 10 | E-code spec cross-refs scattered in body (E1004/E1005/E1052 in §5.3, etc.) | (c) borderline | Error codes are useful when the author hits one — §15 catalogs the author-facing set well. Inline E-codes in §5.3 label rules are slightly heavy but defensible (they tell you what a violation raises). | KEEP | **Low** |

## What is NOT noise (explicitly cleared)

- §13.1, 13.2, 13.6, 13.7, 13.9 — real author traps with worked WRONG/CORRECT pairs. **High signal, keep as-is.**
- §13.8 headroom gotcha — useful (only the R-32 tag is noise).
- §13.10 stable+directed warning — a real combination authors will hit.
- The `${i}` vs bare `i` interpolation section (§5.11) — the single most valuable bug-prevention content in the doc.
- `tint_by_source/tint_by_edge` are functional, not no-ops (verified) — only #2 `global_optimize` is a genuine no-op param.

## Prioritized Fixes

1. **DROP `global_optimize`** from the §7.4 param table and **delete §13.11** (findings #2, #3). It is the only param-table no-op and it is documented twice. Highest payoff, lowest risk.
2. **Strip §5.8 of placement-engine internals** (finding #1). Replace the `side_hint` / Hirsch-1982 / R-06 / "planned v0.12.0" block with one author-facing sentence about auto side inference. This is the densest noise in the doc.
3. **Move §13.12 env vars** (finding #4) to the appendix or delete (already covered by the `spec/smart-label-ruleset.md` cross-ref at L344).
4. **Drop the `grid` no-op option** from §10 (finding #7).
5. **Trim maintainer pointers** (finding #6) and **rule-ID tags** like "(R-32)" (finding #8).

## Proposed "Internal / Forward-Compat Appendix" Structure

Add a clearly-fenced appendix at the end (after §15) so the body stays purely author-facing:

```
## Appendix A — Internal, Dev-Only, and Forward-Compat (not for authoring)

> Nothing in this appendix affects the .tex an author writes. It exists for
> maintainers and for completeness. Authors can ignore it entirely.

### A.1 Forward-compat / no-op flags
- Graph `global_optimize` — accepted, emits UserWarning, no runtime effect
  (GEP-20, ships v2.1).  [was §7.4 / §13.11]
- diagram `grid` — accepted but ignored (placeholder).  [was §10]

### A.2 Dev / debug environment variables
- SCRIBA_DEBUG_LABELS, SCRIBA_LABEL_ENGINE — consumed at import in
  _svg_helpers.py; never set in production.  [was §13.12]

### A.3 Placement-engine internals (informative)
- side_hint auto-inference, R-22 / R-06 ordering, Hirsch-1982 NE ladder.
  Full spec: spec/smart-label-ruleset.md.  [was §5.8 internals]
```

This keeps the information discoverable for maintainers while removing it from the path an author reads when writing `.tex`.
