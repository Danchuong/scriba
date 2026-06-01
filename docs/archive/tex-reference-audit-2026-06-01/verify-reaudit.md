# TeX Reference — Verification Re-Audit (post Phase 1–3)

**Date:** 2026-06-01
**Target:** `docs/SCRIBA-TEX-REFERENCE.md` (now 1635 lines, was 1493/1494)
**Method:** Re-checked the CURRENT doc against each of the 8 original criterion reports
(`01`–`08`) and the ground truth (`00-ground-truth.md`). Verified every TOC anchor
against the actual heading list, sampled the new per-primitive param tables against
ground truth, and checked the three landed commits (`57eb92b` Phase 1, `8a91c23`
Phase 2, `a30e4aa` Phase 3) did not introduce new defects.

Commits under review:
- `57eb92b` Phase 1 — correctness & consistency
- `8a91c23` Phase 2 — per-primitive param tables + field clarity
- `a30e4aa` Phase 3 — structure & signal-to-noise

> **Note on the audit vs. ground-truth conflict (E1320/E1321/E1467/E1159):** the
> original `04-correctness-freshness.md` (findings #2, #5) called E1320/E1321
> "phantom codes" and E1502-for-bipartite wrong. Since then, commit `756cedf`
> *registered* E1159/E1320/E1321/E1467 and `00-ground-truth.md` §C confirms all
> four are now real and raised. The current doc documents E1320/E1321/E1467/E1159
> as real codes, which is **correct against today's code and ground truth.** Those
> two correctness findings are therefore CLOSED (the doc now matches the code that
> the audit pre-dated).

---

## TOC / anchor resolution check

All 16 TOC links + the one in-body anchor link (`#appendix-a--…`, L1565) resolve to
real headings. Verified the tricky cases:

| TOC link | Heading | Resolves? |
|---|---|---|
| `#5-inner-commands-13-total` | `## 5. Inner Commands (13 total)` | ✓ |
| `#13-gotchas--known-limitations` | `## 13. Gotchas & Known Limitations` (`&` dropped → double hyphen) | ✓ |
| `#appendix-a--internal--forward-compat` | `## Appendix A — Internal / Forward-Compat` (em-dash + `/` dropped) | ✓ |
| all §0–§15 numeric anchors | match their `## N. Title` headings | ✓ |

All in-body `§N.M` cross-references (§0, §2, §5.2, §5.3, §5.7, §5.8, §5.10, §5.11,
§5.13, §6, §7, §7.5, §8, §12, §13.2, §15) point to sections that exist. `§6.5`
(L579) is an external `spec/ruleset.md §6.5` ref, not a dangling internal one.
**No broken anchors, no dangling §-refs.**

---

## Per-criterion status

### 1. Completeness (`01`)

| Finding | Status | Evidence |
|---|---|---|
| #1 `tooltip=` phantom param | **CLOSED** | `grep tooltip` → 0 hits; removed from §5.5 (L369–370) |
| #2 Graph `set_weight` missing | **CLOSED** | §7.4 L768 `set_weight={from,to,value}` |
| #3 Graph `seed` alias missing | **CLOSED** | §7.4 L736 "alias `seed`; `layout_seed` wins" |
| #4 CodePanel `source=` missing | **CLOSED** | §7.11 L995 `source` row |
| #5 Array `values=`/`n=` aliases | **CLOSED** | §7.1 L674–675 |
| #6 DPTable required-vs-optional | **CLOSED** | §7.3 L706–713 full param table w/ Required column |
| #7 Stack `push={label,value}` | **PARTIAL** | §7.8 documents `push="C"`/`pop=1` (L901); dict form still not shown |
| #8 Tree E1434 wording | **CLOSED** | §7.5 L850/L860 "root removal without cascade" — consistent now |
| #9 Plane2D `add_region` example | **CLOSED** | §7.9 L939 concrete dict example |
| #10 MetricPlot E1483 cap | **OPEN** | E1483 still absent from §14/§15 and §7.10 |
| #11 HashMap `capacity` required / no auto-hash | **CLOSED** | §7.12 L1008 Required=yes; L1011 "no push/delete op" |
| #12 VariableWatch ops undocumented | **CLOSED** | §7.15 L1065 targeted + bulk ops |
| #13 Queue direct cell-set / dequeue-truthy | **PARTIAL** | dequeue-truthy now noted (L1049); direct `cell[i]{value=}` set still not shown |
| #14 env options | n/a | no gap (was already fine) |

Completeness: 10 CLOSED / 2 PARTIAL / 1 OPEN.

### 2. Field clarity (`02`)

| Finding | Status | Evidence |
|---|---|---|
| #1 `add_region=...` placeholder | **CLOSED** | §7.9 L939 real dict |
| #2 `regions` element format | **CLOSED** | §7.9 dict form shown; region described as DICT-only |
| #3 `colorscale` false menu | **CLOSED** | §7.7 L888 "only `viridis` … any other name raises E1421" |
| #4 `tooltip=` not implemented | **CLOSED** | removed |
| #5 `add_line` tuple meaning | **CLOSED** | §7.9 L930–933 "element 0 is a label, NOT a coordinate" + `{a,b,c}` form |
| #6 `lines` element format | **PARTIAL** | construction table L919 still just "Inline batch of infinite lines"; the dynamic `add_line` forms are clear (L930) but the ctor `lines=` element shape is not cross-linked |
| #7 Matrix `data` flat/nested | **CLOSED** | §7.7 L882/L887 |
| #8 Grid `data` shape | **CLOSED** | §7.2 L693 |
| #9 Array `labels` vs `label` | **CLOSED** | §7.1 L677–678 explicit |
| #10 NumberLine `ticks` count | **CLOSED** | §7.6 L871 "number of tick marks (a count, not a spacing)" |
| #11 `polygons` element format | **PARTIAL** | dynamic `add_polygon` shown (L937); ctor `polygons=` row L921 still generic |
| #12 `points`/`segments` ctor format | **PARTIAL** | dynamic forms shown (L928–935); ctor rows L918/L920 generic |
| #13 MetricPlot per-series `color` | **CLOSED** | §7.10 L984 `"auto"` or CSS color |
| #14 `scale`/`axis` + E1487 | **PARTIAL** | axis/scale values documented (L984); the E1487 same-axis-must-share-scale rule still not stated |
| #15 Tree segtree `data` table | **CLOSED** | §7.5 L800–809 param table |
| #16 Matrix `vmin`/`vmax` | **CLOSED** | §7.7 L891 "clamp low/high; default data min/max" |
| #17 MetricPlot range "auto"/E1486 | **PARTIAL** | xrange/yrange auto documented (L964–965); E1486 degenerate-range still not stated |
| #18 Stack `items` dict form | **OPEN** | §7.8 L900 still says `items` (initial list) only |
| #19 env `id`/`label` types | **CLOSED** | §10 L1400–1401 typed table |
| #20 five table-less primitives | **CLOSED** | all of Queue/HashMap/LinkedList/VariableWatch/CodePanel now have param tables |

Field clarity: 12 CLOSED / 6 PARTIAL / 1 OPEN. Big lift on the CRITICAL items (all 4 closed).

### 3. Consistency (`03`)

| Finding | Status | Evidence |
|---|---|---|
| C1 E1501 two meanings | **CLOSED** | §15 L1615 now "Graph exceeds the 100-node hard limit (force layout)" — matches §7.4 L773 & §14 L1583 |
| C2 "§7.1 of the spec" dangling | **CLOSED** | string gone; §5.3 now points to §5.13 |
| C3 8 vs 9 states | **CLOSED** | §5.7 L376 lists all 9 incl. `highlight`; §6 agrees |
| C4 boolean casing | **CLOSED** | §5.1 L268 canonical lowercase note; remaining `=True` only in legit Python-ctor context (L163 `enable_copy_button=True`, L268 as a counter-example) |
| C5 "five families" vs "All six forms" | **OPEN (unchanged)** | §8 L1103 "five element-type families" still collides with L1114 "All six forms work" — the exact contradiction C5 flagged persists verbatim |
| C6 `${var}` reliability two ways | **CLOSED** | §13.2 retitled "resolves in foreach bodies, apply values, and selector indices" (L1493) and matches §5.11/§8; E1159 fail-loud documented |
| C7 `G.node["A"]` example | **PARTIAL** | §7.4 L743 still lists `G.node["A"]` beside `G.node[id]`; §8 quoting rule (L1074–1081) now resolves it but the §7.4 example line was not trimmed |
| C8 stable ≤50-frame cap | **CLOSED** | §14 L1584 "Graph stable layout: ≤20 nodes, ≤50 frames"; §7.4.1 references stable |

Consistency: 6 CLOSED / 1 PARTIAL / 1 OPEN.

### 4. Correctness / freshness (`04`)

| Finding | Status | Evidence |
|---|---|---|
| #1 Tree node-id quoting | **CLOSED** | §8 L1079–1081 splits Graph (strict) vs Tree (str-normalized, interchangeable) |
| #2 E1320/E1321 "phantom" | **CLOSED (resolved by code)** | codes now registered (`756cedf`); doc documents them correctly (§5.13 L616–617). Audit pre-dated the registration. |
| #3 `${var}` outside foreach | **CLOSED** | §13.2 rewritten; E1159 fail-loud (L1513–1514) matches ground-truth §D.2 |
| #4 `value=${i}` provenance | **PARTIAL** | subscript example correct (§5.11 L546–557); "(supported since v0.8.2)" tag (L521) still present, slightly misleading but harmless |
| #5 E1502 ≠ bipartite | **CLOSED** | no `bipartite`/`E1502` strings remain in the doc |
| #6 E1501 severity in §15 | **CLOSED** | §15 L1615 "Validation / Graph exceeds 100-node hard limit" |
| #7 CodePanel top header | **CLOSED (improved)** | §7.11 L996 "rendered as a top header bar (IDE-tab style), not a bottom caption" |
| #8 viewBox max-extent | n/a (was already correct) | unchanged |
| #9–12 (already correct) | n/a | unchanged |

Correctness: 7 CLOSED / 1 PARTIAL / 0 OPEN.

### 5. Self-sufficiency (`05`)

| Finding | Status | Evidence |
|---|---|---|
| #1 §5.8 "Read that document" imperative | **CLOSED** | reframed to "**Maintainer note** … Authors do not need it" (§5.8 L381–384); "read that document" string gone |
| #5 §15 error catalog closure | **PARTIAL** | §15 now points to `spec/error-codes.md` (rendered doc) not `.py` ✓; but several self-cited codes (E1004, E1005, E1052, E1113, E1320, E1437, E1471/2, E1433–6) are still cited in body and absent from the §15 table |
| #7 "§7.1 of the spec" orphan | **CLOSED** | replaced with §5.13 pointer |
| #2/#3/#4/#6/#8/#9 (OK-to-defer) | **CLOSED/no-change-needed** | §6 CSS pointer scoped; smart-label ref now maintainer-scoped |

Self-sufficiency: largely CLOSED; 1 PARTIAL (#5 self-citation closure).

### 6. Signal-to-noise (`06`)

| Finding | Status | Evidence |
|---|---|---|
| #1 §5.8 placement-engine internals (Hirsch/R-06/side_hint) | **CLOSED** | replaced by one author sentence (L398–399) + maintainer note; `side_hint`/Hirsch/R-06 strings gone |
| #2 `global_optimize` param row | **CLOSED** | removed from §7.4 table; one-liner pointer to Appendix A (L755) |
| #3 §13.11 duplicate no-op gotcha | **CLOSED** | old §13.11 folded; forward-compat flags collapsed into one line (L1563–1565) → Appendix A |
| #4 §13.12 dev env vars | **CLOSED** | moved to Appendix A (L1631–1632) |
| #5 `tint_by_source/edge` | **CLOSED (kept, demoted)** | now in "Additional construction params" sub-table (L752–753) |
| #6 §5.8 maintainer pointer | **CLOSED** | reframed |
| #7 `grid` no-op option | **PARTIAL** | added to Appendix A (L1630) **but the §10 options table still lists it** (L1405) — now documented in two places instead of moved |
| #8 "(R-32)" tag | **PARTIAL** | still present in §13.8 heading (L1544); gotcha kept (good), tag not stripped |
| #9 version inline notes | **PARTIAL** | "(supported since v0.8.2)" still at §5.11 L521 |

Signal-to-noise: 6 CLOSED / 3 PARTIAL. The appendix structure recommended by the audit was adopted.

### 7. Disambiguation (`07`)

| Finding | Status | Evidence |
|---|---|---|
| #1 `label` vs `labels` | **CLOSED** | §7.1 L677–678 explicit ("NOT a list" / "caption"); also field-clarity table |
| #2 `label` overload (4 meanings) | **PARTIAL** | each site is now clear (annotation pill L390, step id L320, env aria-label L1401, caption) but no single glossary cross-link enumerates the four |
| #3 indexing conventions table | **PARTIAL** | CodePanel 1-based (§13.9), Stack 0=bottom (§7.8 L902), Plane2D 0-based (§8 L1103) all stated, but no single consolidated indexing table as the audit recommended |
| #4 `\highlight` vs `\recolor{highlight}` | **CLOSED** | §6 L655 spells out ephemeral vs persistent "use sparingly, prefer `\highlight`" |
| #9 `\annotate` vs `\reannotate` | **CLOSED** | §5.9 L466–469 "Recolors an existing annotation … color= required (E1113)" |
| #10 diagram vs animation table | **PARTIAL** | §4 L251 still inline "Same primitives, no `\step`/`\narrate`"; no capability table |
| #13 `q.front/rear` vs `cell` | **CLOSED** | §7.14 L1052 "front/rear pointer cell" clarified |
| #5/#6/#7/#8/#11/#12 (GOOD) | unchanged | still good |

Disambiguation: 4 CLOSED / 4 PARTIAL. The CRITICAL #1 is closed; #2/#3/#10 cross-construct gaps remain.

### 8. Navigability (`08`)

| Finding | Status | Evidence |
|---|---|---|
| #1 No TOC | **CLOSED** | linked TOC added (L6–24), all anchors resolve |
| #2 Interpolation split §5.11/§13.2 | **CLOSED** | §13.2 retitled + cross-links §5.11 (L1516); §13.2 narrowed to the resolve-everywhere + E1159 rule |
| #3 Tree node-id rule split | **CLOSED** | §7.5 L802 "(str-normalized — see §8)"; §8 carries the rule |
| #4 Primitive gotchas isolated | **PARTIAL** | §13.10 → Appendix A link added; but per-primitive "Gotchas: §13.x" back-pointers (Stack/Queue §13.1, CodePanel §13.9, annotate §13.8) not added |
| #5 selector bridge placement | **PARTIAL/accept** | §8 still after §7; TOC mitigates |
| #6 Index-by-task | **CLOSED** | "Index by task" table added (L26–40) |
| #7 inline anchor links | **PARTIAL** | TOC + some `(see §N)` links added; not exhaustive at every split |
| #8 inline E-code → §15 links | **OPEN** | inline E-codes still not linked to §15 (low severity) |

Navigability: 4 CLOSED / 3 PARTIAL / 1 OPEN. The two HIGH findings (#1 TOC, #2 interpolation) are closed.

---

## NEW issues introduced by the edits

1. **`grid` diagram option now documented in TWO places (regression vs. intent).**
   Signal-to-noise #7 asked to *move* `grid` to the appendix. Phase 3 added it to
   Appendix A (L1630) **but left the original §10 options-table row** (L1405). The
   result is duplication, not relocation — a mild consistency wrinkle the edits
   created. (Not author-breaking; both rows say the same "accepted but ignored".)

2. **No broken anchors / no duplicated rows / no dangling §-refs.** All TOC links,
   the one in-body anchor link, and every internal §-reference resolve. The new
   per-primitive tables introduced no duplicate rows.

## Ground-truth cross-check of the new param tables (sample)

Sampled Array, Graph, Tree, NumberLine, Matrix, Plane2D, Stack, Queue against
`00-ground-truth.md`:

- **Array, Graph, Tree, NumberLine, Stack, Queue, DPTable, HashMap, LinkedList,
  VariableWatch, CodePanel** — param tables match ground truth (types, defaults,
  required-ness, allowed values, E-codes). ✓
- **Matrix `cell_size` default = `auto` (§7.7 L890) contradicts ground truth and
  source.** Source `matrix.py:105` `_DEFAULT_CELL_SIZE = 24`; ground-truth §A.7
  lists `cell_size | int | 24`. The doc says `auto`. This is a **pre-existing
  inaccuracy carried through** (present in `a57ea5a` as `_(auto)_`, restated by
  Phase 2 as `auto`), NOT newly introduced by these edits, and was not one of the
  original 8 findings — but it is a real factual error worth a one-line fix.
- **§8 selector table omits `.all` for Stack, HashMap, LinkedList, MetricPlot.**
  Ground truth gives `all` to all four; the per-primitive §7 sections also show
  `s.all`/`ll.all`. The §8 matrix "All" column is blank for these rows. Verified
  **pre-existing** (identical in `a57ea5a`), not introduced by the edits, and
  outside the original findings (completeness explicitly cleared selectors). Minor.

---

## Overall verdict

**Strong pass.** Across the 8 criteria there were ~80 distinct findings/sub-findings.
Counting the headline findings per criterion:

| Criterion | Closed | Partial | Open |
|---|---|---|---|
| 1 Completeness | 10 | 2 | 1 |
| 2 Field clarity | 12 | 6 | 1 |
| 3 Consistency | 6 | 1 | 1 |
| 4 Correctness | 7 | 1 | 0 |
| 5 Self-sufficiency | 3 | 1 | 0 |
| 6 Signal-to-noise | 6 | 3 | 0 |
| 7 Disambiguation | 4 | 4 | 0 |
| 8 Navigability | 4 | 3 | 1 |
| **Total** | **~52** | **~21** | **~4** |

**≈ 68% fully CLOSED, ≈ 27% PARTIAL, ≈ 5% OPEN.** Every CRITICAL/HIGH finding is
closed: the four phantom/wrong-fact items (`tooltip=`, `colorscale` menu,
`add_region=...`, Tree node-id quoting), the TOC, the interpolation split, the
E1501 double-meaning, the state-count and boolean-casing contradictions, and the
self-sufficiency imperative are all resolved. Remaining work is low-severity:
mostly cross-construct cross-links (disambiguation #2/#3/#10), ctor-vs-dynamic
element-shape parity for Plane2D (field-clarity #6/#11/#12), a few MetricPlot
constraint notes (E1483/E1486/E1487), and tag/version-note cleanup.

**Outstanding OPEN items to fix:** §8 "five families"/"All six forms" wording
collision (C5 — only fully-open consistency item), MetricPlot E1483 cap
(completeness #10), Stack `items` dict form (field-clarity #18).

**NEW issue to fix:** `grid` option duplicated across §10 and Appendix A — remove
the §10 row to complete the intended relocation. (Also worth fixing while nearby:
Matrix `cell_size` default `auto` → `24`, a pre-existing inaccuracy.)
