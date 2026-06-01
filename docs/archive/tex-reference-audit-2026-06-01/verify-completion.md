# TeX Reference — Completion Verification (post Phase 5–7)

**Date:** 2026-06-01
**Target:** `docs/SCRIBA-TEX-REFERENCE.md` (now 1686 lines, was 1635 at re-audit)
**Plan:** `docs/plans/tex-reference-completion-plan-2026-06-01.md`
**Method:** Re-checked the CURRENT doc against the completion plan's Phase 5–7
targets, the prior re-audit (`verify-reaudit.md`), and ground truth
(`00-ground-truth.md`). Re-validated every TOC anchor and every in-body `§N.M`
cross-reference, scanned for duplicate table rows, spot-checked the four new
tables against ground truth, and re-rendered all seven §9 examples.

Commits under review:
- `fc805ee` Phase 5 — field-clarity & completeness tail
- `d8d115d` Phase 6 — consistency & noise tail
- `cc2a7b8` Phase 7 — disambiguation & navigability tail

---

## 1. Targeted-item confirmation (Phase 5–7)

### Phase 5 — field-clarity & completeness tail — ALL PRESENT

| Item | Status | Evidence |
|---|---|---|
| Plane2D ctor element-shape cross-links | **CLOSED** | §7.9 construction table L928–933 now gives each ctor row an explicit shape (`add_line` form `(label,slope,intercept)`/`(label,{a,b,c})`, `add_segment` `((x1,y1),(x2,y2))`, `add_polygon` `[(x,y),…]`, `add_region` `{polygon,fill?}`), plus the cross-link line L936 "Element shapes are identical to the dynamic `add_*` operations below." Matches GT §A.9 / §B.2–3. |
| Stack `items` dict form `{label,value?}` | **CLOSED** | §7.8 L910 "each entry is a string **or** a `{label, value?}` dict"; push dict form L911 `push={label="C", value=3}`. Matches GT §A.8. |
| Queue direct cell-set `\apply{q.cell[i]}{value=}` | **CLOSED** | §7.14 L1065 "Set a specific cell's text directly with `\apply{q.cell[i]}{value=...}`." Matches GT §A.14 (per-cell value via `set_value`). |
| MetricPlot E1481/E1483/E1485/E1486/E1487 note | **CLOSED** | §7.10 L999 documents all five: ≤8 (E1481), ≤1000 pts/series (E1483), unique names (E1485), same-axis-share-scale (E1487), degenerate fixed range (E1486). Matches GT §A.10. |

### Phase 6 — consistency & noise tail — ALL PRESENT

| Item | Status | Evidence |
|---|---|---|
| §8 `.all` column filled | **CLOSED** | Selector matrix L1100–1116: Stack (L1108), CodePanel (L1109), HashMap (L1110), LinkedList (L1111), VariableWatch (L1113), MetricPlot (L1116) all carry `.all`. Matches GT (all 15 expose `all`). |
| §7.4 redundant `G.node["A"]` removed | **CLOSED** | `grep 'G.node["A"]'` → 0 hits in the doc body; §7.4 selector line L753 now `G.node[id]` only. |
| `(supported since v0.8.2)` stripped | **CLOSED** | `grep` → 0 matches. |
| `(R-32)` stripped | **CLOSED** | `grep` → 0 matches; §13.8 heading L1584 clean. |
| §15 add E1005/E1113/E1320/E1433–E1436/E1437/E1471/E1472 (+E1159/E1321/E1467) | **CLOSED** | §15 rows L1658–1666: E1159, E1321, E1467, E1005, E1113, E1320, E1433–E1436, E1437, E1471/E1472 all present. E1004/E1052 (cited in §5.3) covered by the L1668 catch-all pointer to `spec/error-codes.md`. |

### Phase 7 — disambiguation & navigability tail — ALL PRESENT

| Item | Status | Evidence |
|---|---|---|
| §4 animation-vs-diagram capability table | **CLOSED** | §4 L263–269 table (Frames / `\step`+`\narrate` / shapes / playback / use-for); `\step`/`\narrate` in diagram → E1050/E1054, consistent with §15 L1639–1640. |
| §8 indexing-conventions table | **CLOSED** | L1133–1141: 0-based (Array/Grid/DPTable/Matrix/Plane2D/LinkedList/Queue/HashMap), Stack 0-based `item[0]`=bottom, CodePanel 1-based `line[0]`→E1115. Matches GT §A. |
| §8 `label` glossary (4 meanings) | **CLOSED** | L1143–1154: `\shape` caption / `\annotate` pill / `\step[label=]` frame id / `\begin{animation}[label=]` aria-label, plus a `labels`-vs-`label` note. Matches GT §B.6 + D.3. |
| Per-primitive gotcha back-pointers | **CLOSED** | Stack §7.8 L913 → §13.1; Queue §7.14 L1069 → §13.1; CodePanel §7.11 L1014 → §13.9. |

---

## 2. Previously-OPEN items — all CLOSED

| Prior-OPEN item | Status | Evidence |
|---|---|---|
| C5 §8 "five families" / "All six forms" collision | **CLOSED** | The "All six forms work" string is gone. L1120 "five element-type families" and L1131 "All five families (plus `.all`)" are now internally consistent. |
| MetricPlot E1483 (§14 + §7.10) | **CLOSED** | §7.10 L999 and §14 L1625 both cite E1483 (≤1000 pts/series). |
| Stack `items` dict form (field-clarity #18) | **CLOSED** | §7.8 L910–911 (see Phase 5 above). |

---

## 3. Regression checks

- **TOC anchors:** all 16 numeric TOC links + the Appendix A link resolve to real
  headings (verified against the full `##`/`###` heading list). Tricky cases hold:
  `#5-inner-commands-13-total` ↔ `## 5. Inner Commands (13 total)` (parens dropped);
  `#13-gotchas--known-limitations` (`&` → double hyphen);
  `#appendix-a--internal--forward-compat` (em-dash + `/` dropped). **No broken anchors.**
- **Internal `§N.M` refs:** every reference resolves — §0, §2, §5.2, §5.3, §5.7,
  §5.8, §5.10, §5.11, §5.13, §6, §7, §7.5, §8, §12, §13.1, §13.2, §13.9, §15 all
  point at existing headings. `§6.5` (L589) is the external `spec/ruleset.md §6.5`,
  not an internal dangling ref. The three new back-pointers (§13.1 ×2, §13.9) and
  the two new table cross-links resolve. **No dangling §-refs.**
- **Duplicate rows:** none. `sort | uniq -d` surfaces only legitimately-repeated
  code-snippet lines and identical *table-header* rows (`| Param | Type | … |`)
  shared across multiple primitive tables — no duplicated table *data* rows.
- **New-table factual spot-check vs ground truth:**
  - Indexing table — 0-based set, Stack `item[0]`=bottom, CodePanel 1-based/E1115:
    matches GT §A.8/§A.11. ✓
  - `label` glossary — 4 meanings match GT §B.6 + §D.3. ✓
  - §8 `.all` column — GT gives `all` to all 15 primitives; every row now carries it. ✓
  - Animation-vs-diagram table — `\step`/`\narrate`-in-diagram → E1050/E1054 agrees
    with §15. ✓
- **Bonus fix verified:** the pre-existing Matrix `cell_size` inaccuracy (`auto`)
  flagged by the prior re-audit is now corrected to `24` (§7.7 L900), matching
  GT §A.7 (`matrix.py:105 _DEFAULT_CELL_SIZE = 24`).

---

## 4. §9 render check

Extracted all seven §9 latex blocks to `/tmp/texref-verify/ex9{1..7}.tex` and ran
`python3 render.py` from repo root:

| Example | Result | HTML |
|---|---|---|
| 9.1 Minimal Animation | OK | 440 KB |
| 9.2 Static Diagram | OK | 424 KB |
| 9.3 DP Editorial (Frog) | OK | 500 KB |
| 9.4 BFS + multiple primitives | OK | 456 KB |
| 9.5 foreach + compute | OK | 439 KB |
| 9.6 Hidden-state (BFS Tree) | OK | 440 KB |
| 9.7 Dijkstra (full) | OK | 840 KB |

All seven render with **exit 0 and zero warnings/errors** (logs scanned for
`warning|error|E1xxx|traceback` — clean). The Phase 5–7 edits were elsewhere;
nothing in §9 broke.

---

## 5. Final tally

Prior re-audit headline counts: **~52 CLOSED / ~21 PARTIAL / ~4 OPEN.**

Phase 5–7 drove every PARTIAL and OPEN item that the completion plan scoped to
CLOSED. Re-counting the headline findings:

| Criterion | Closed | Partial | Open |
|---|---|---|---|
| 1 Completeness | 13 | 0 | 0 |
| 2 Field clarity | 19 | 0 | 0 |
| 3 Consistency | 8 | 0 | 0 |
| 4 Correctness | 8 | 0 | 0 |
| 5 Self-sufficiency | 4 | 0 | 0 |
| 6 Signal-to-noise | 9 | 0 | 0 |
| 7 Disambiguation | 8 | 0 | 0 |
| 8 Navigability | 6 | 1 | 1 |
| **Total** | **~75** | **~1** | **~1** |

**≈ 97% fully CLOSED.** Of the prior ~25 PARTIAL+OPEN, all were resolved except
two LOW-severity navigability items that were explicitly **out of scope** for the
completion plan (never listed in Phases 5–7):

- **Navigability #5 (PARTIAL/accept):** §8 still physically follows §7 rather than
  preceding it. The TOC + Index-by-task mitigate; the plan deliberately did not
  reorder sections.
- **Navigability #8 (OPEN):** inline E-codes in body prose are still not
  hyperlinked to §15. Pure-convenience polish; not in the plan.

**Genuine remaining gap (carried, not newly introduced):** the diagram `grid`
option still appears in both §10 (L1445) and Appendix A (L1680). The prior
re-audit flagged this as a "remove the §10 row" cleanup, but it was **not** in the
Phase 5–7 plan. It is now a one-line pointer ("Accepted but ignored — see
Appendix A") rather than a full duplicate description, so it reads as a
cross-reference, not a contradiction. Low severity.

**Newly-introduced defects:** none. No broken anchors, no dangling §-refs, no
duplicated table rows, no factual drift in the four new tables, and all §9
examples still render clean.

**Verdict: complete pass.** Every CRITICAL/HIGH/MEDIUM finding is closed; all
plan-scoped LOW items are closed; the only residue is two out-of-scope
navigability conveniences and one pre-existing cosmetic `grid` cross-listing.
