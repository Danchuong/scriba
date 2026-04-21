# Synthesis — Smart-Label Ruleset Strengthening (Round 2) 2026-04-21

Seven opus agents re-examined the smart-label ruleset from first principles to
produce a normative, testable, versioned spec. This round is about **making
the ruleset document itself rock-solid** before any further code work. It
supersedes the informal v1 shipped at `docs/spec/smart-label-ruleset.md`.

> **Round 1** (`../smart-label-ruleset-audit-2026-04-21/`) found *operational*
> gaps (bugs, coverage, WCAG fails). This round closes *specification* gaps
> (ambiguity, under-specification, missing conformance surface).

---

## TL;DR

The current `smart-label-ruleset.md` is **informal-but-correct**. It states
the right ideas but leaves too much implicit:

- I-2 says "2 px gap" but code enforces 0 px (Round 1 A1).
- "MUST"/"SHOULD" used casually, not RFC 2119.
- No error codes, no test-assertion mapping, no conformance classes.
- No invariants for accessibility, determinism, author contract.
- "Primitive participates" is a prose sentence, not a callable interface.
- No versioning, no deprecation policy, no open-issue marker.

Seven agents produced **~6,600 lines** of foundation material. Consolidating
into v2 gives:

- **42 invariants** (up from 10), organised across 7 axes.
- **14 MUST / 8 SHOULD / 6 MAY** rules with RFC 2119 phrasing.
- **12 new error codes** E1560–E1571 reserved.
- **Hoare-triple-style contracts** for 14 functions, with 6 signature hazards
  and 6 API asymmetries named.
- **Formal Primitive Participation Contract** (6 required methods) +
  conformance matrix for 15 primitives + 17.5 h migration plan.
- **16-category edge-case taxonomy** (5 Critical NaN/crash, 12 High).
- **9 MUST / 2 SHOULD spec-style conventions** adopted from
  W3C/TC39/WHATWG/SVG 2.
- **18 non-goals** + **12-section versioning policy** (v1 → v3).

---

## Invariant inventory (42 total)

From `01-first-principles.md`. Axis counts:

| Axis | Count | Gate |
|------|-------|------|
| G — Geometry | 8 | All MUST |
| C — Collision | 7 | 5 MUST, 2 SHOULD (pill-vs-leader, pill-vs-cell-text pending MW-2) |
| T — Typography | 6 | All MUST |
| A — Accessibility | 7 | 6 MUST, 1 SHOULD (forced-colors) |
| D — Determinism | 4 | 3 MUST, 1 MAY (±1 px cross-platform) |
| E — Error handling | 4 | All MUST |
| AC — Author contract | 6 | All MUST |

**Headline additions over v1:**

- **G-4 clamp-translate-only** (replaces v1 I-2 ambiguity; resolves clamp-race).
- **A-1..A-7 accessibility invariants** (entirely new axis).
- **D-1..D-4 determinism invariants** (entirely new).
- **AC-6 math-headroom-symmetry** (closes v1 I-9 gap for position-below).

**Non-invariants moved out of normative scope** (12 items including nudge
step-size, candidate count 32, padding constants, corner radius, math
multiplier value) — these become configuration with defaults, not rules.

**Six invariant conflicts** documented with explicit tie-breakers, e.g.
C-1 (no overlap) vs AC-3 (position hint respected): **C-1 wins**.

---

## RFC 2119 rewrite

From `02-normative-rewrite.md`. Every rule now has:

- Normative keyword (MUST / SHOULD / MAY).
- Error code (new block E1560–E1579).
- Message template.
- Detection point (source file:line).
- Recovery strategy.
- Link to enforcement test.

**New error codes reserved**:

| Code | Meaning |
|------|---------|
| E1560 | Pill overlap detected post-nudge |
| E1561 | ViewBox does not contain pill AABB |
| E1562 | Clamp modified pill dimensions |
| E1563 | Pill dimension ≤ 0 |
| E1564 | Pill width less than text width |
| E1565 | Leader origin is pill center (must be edge) |
| E1566 | Registry mutation after frame finalise |
| E1567 | Pill height exceeds headroom |
| E1568 | Label text mismatched author declaration |
| E1569 | Effective contrast below WCAG AA |
| E1570 | Nudge candidate order non-deterministic |
| E1571 | Primitive emitted label without registry entry |

Existing E1112 / E1113 re-affirmed (addressable selector miss).

**Ambiguous-language audit**: every informal "always / never / should / must"
in v1 flagged with proposed RFC 2119 upgrade.

---

## API contracts

From `03-api-contracts.md`. 14 functions / classes under formal
pre/post-condition contracts.

**6 signature hazards named (H-1..H-6)**:

- H-1 `overlaps()` has no `pad` param — **I-2 is unenforceable from code**.
- H-2 `pill_h = 0` degenerates nudge grid to 32 zero-offset candidates.
- H-3 All-LaTeX math label collapses width estimator to empty string.
- H-4 Positional float tuples for `src_point/dst_point` invite transposition.
- H-5 `_debug_capture["final_y"]` is pre-nudge (test trap).
- H-6 Default `color="info"` has opacity 0.45 (UX footgun).

**6 API asymmetries named (A-1..A-6)**:

- A-1 Spec I-2 says 2 px, code enforces 0 px.
- A-2 `position_label_height_below` missing math branch.
- A-3 All three emitters share clamp-race bug.
- A-4 `emit_position_label_svg` uses 4-dir/16-cand, not 8-dir/32-cand.
- A-5 `emit_position_label_svg` ignores position as side-hint.
- A-6 30 px leader threshold only in `emit_arrow_svg`.

**MW-3 helper contract proposed**:

```python
_place_pill(
    *, natural_x, natural_y, pill_w, pill_h, l_font_px,
    placed_labels, side_hint, overlap_pad=0.0,
) -> tuple[int, int, int, int, int, int, bool]
```

Closes A-3, A-4, A-5. Makes I-2 enforceable via `overlap_pad=2.0`.
Dead `pill_w` param in `_nudge_candidates` deprecated.

---

## Primitive participation contract

From `05-primitive-contract.md`. Currently "primitive participates in
smart-labeling" is a prose claim in v1 §6. Round 2 defines it as a formal
interface:

**Required methods (6)**:

| Method | Grade | Status |
|--------|-------|--------|
| `resolve_annotation_point(selector) -> (x, y) \| None` | MUST | Exists, audit found inside-bbox failures |
| `emit_svg(..., placed_labels)` | MUST | Needs `placed_labels` kwarg (MW-2) |
| `annotation_headroom_above(annotations)` | MUST | **NEW** — collapses scattered `max(...)` blocks |
| `annotation_headroom_below(annotations)` | MUST | **NEW** |
| `register_decorations(registry)` | MUST post-MW-2, SHOULD stub now | **NEW** |
| `dispatch_annotations(...)` | SHOULD | Documents Plane2D override |

**Conformance matrix (15 primitives × 9 columns)**:

- **Fully conformant**: 0 / 15
- **Closest**: Array, DPTable (both miss only headroom-below math)
- **Dark** (no smart-label integration at all): Stack, Matrix, MetricPlot,
  CodePanel → must either conform or opt-out explicitly.

**6 forbidden patterns (FP-1..FP-6)** with citations:

- FP-1 direct `<text>` emission outside registry (Plane2D `_emit_text_annotation`).
- FP-2 isolated second `placed_labels` list (Graph, Plane2D).
- FP-3 hardcoded glyph widths (`char_width=7` in Plane2D).
- FP-4 no viewBox clamp after pill placement (bug-F).
- FP-5 `arrow_from`-only filter (Queue, NumberLine).
- FP-6 direct `emit_arrow_svg` bypass (Queue, NumberLine).

**Migration plan**: 14 primitives × effort estimate = **17.5 agent-hours total**.
Ordering: Grid/Tree/LinkedList/HashMap/VariableWatch (0.5 h each, two-line
headroom fix) → Queue/NumberLine (1.5 h, orphan loop replacement) →
MetricPlot (4 h, requires anchor semantics definition) → Plane2D (3 h, most
pattern violations).

---

## Edge-case taxonomy

From `04-edge-cases.md`. 16 categories, ~147 table rows, **5 Critical + 12
High** severity gaps empirically confirmed.

**Critical (crash / data corruption)**:

1. `pill_h = NaN` → 32 `(nan,nan)` candidates, `overlaps()` always returns
   `True` (IEEE 754), **poisons entire registry**.
2. `dst_point = (±inf, ±inf)` → `OverflowError` at `int()` conversion.
3. Self-loop (`arrow_from == target`, bug-B) → NaN in SVG path `d=`.
4. Null byte `\x00` in label → passes `_escape_xml`, breaks XML 1.0 §2.2.
5. `arrow_index = 100` or leader > viewBox diagonal → NaN Bezier direction.

**High (wrong output, no crash)**:

- `\displaystyle` / nested fractions: `pill_h ≈ 19`, rendered ≈ 40 px (2× gap).
- `position_label_height_below` math-branch missing (spec I-9 partial).
- `emit_position_label_svg` 4-dir vs arrow emitters 8-dir (A-4).
- I-4 clamp-collision bug empirically reproduced.
- `arrow_height_above` returns 24 px even when all resolvers None.

**v2 ruleset must add guards** (pre-condition checks) for: NaN in pill/point
tuple, infinite coordinates, null bytes in label, self-loop, empty
`_label_width_text` input.

---

## Spec style adoption

From `06-spec-style.md`. Compared W3C CSS Text L3, ECMAScript 2027,
WHATWG HTML Living Standard, SVG 2, RFC 7230, JSON Schema 2020-12.

**9 MUST conventions adopted**:

1. Hierarchical section numbering + stable anchors.
2. ECMAScript algorithm step style (`Let / Assert / Return`).
3. Conformance classes (Author / Primitive / Emitter / Renderer).
4. `<dfn>` + cross-reference for every §0 term.
5. `ISSUE` blocks for open questions.
6. `NOTE` vs normative prose distinction.
7. Test-assertion mapping table (WPT-style).
8. Python type-annotation schema blocks for shared shapes.
9. RFC 2119 dependency declaration in §0.1 preamble.

**2 SHOULD**: non-normative example marking, feature-at-risk notation
(`[AT RISK]`).

**1 SKIP**: per-section changelog (git log + version annotations sufficient).

**Formal encoding verdict**:
- **TLA+**: No. Algorithm sequential + deterministic + bounded.
- **Alloy**: Yes, feasible. ~150-line model of AABB/viewBox/registry
  invariants → `docs/formal/smart-label-model.als` as optional artefact.
  Hypothesis property-based tests carry primary coverage.

**Three before/after rewrites** produced (I-2, nudge grid, debug flag) —
showing the new style end-to-end.

---

## Non-goals + versioning

From `07-non-goals-versioning.md`.

**18 non-goals (NG-1..NG-18)** grouped by rationale:
- *Architectural out-of-scope*: temporal coherence (NG-1), drag-adjust (NG-2),
  3D (NG-3), live dashboard (NG-8), cross-scene registry (NG-4).
- *Deferred*: browser typography metrics (NG-10 → LR-2), priority culling (NG-9).
- *Conflicts with core design*: per-pill style overrides (NG-17 — breaks WCAG
  token closure), cross-primitive registry at spec level (NG-18).

Every NG has a "Potential re-scoping" clause stating the conditions under
which it could become in-scope.

**12-section versioning policy**:

- **B.1 Scheme**: v1 = Phase 0 + MW-1 + P0 patches. v1.1 = MW-3. v2 =
  MW-2 + a11y §9. v3 = LR-1 (Wave A+B re-land).
- **B.2 Stability**: `[STABLE]`, `[EXPERIMENTAL]`, `[AT RISK]`,
  `[DEPRECATED]`. I-2 is `[AT RISK]` until A1 pad-semantics decision.
- **B.3 Deprecation**: 2 minor notice + `DeprecationWarning` (gated by
  `SCRIBA_WARN_DEPRECATED=1`) + major-bump removal. `SCRIBA_LABEL_ENGINE=
  legacy` eligible for removal at v3.
- **B.4 Compat**: MUST → SHOULD is always major. I-* labels reserved forever.
  Geometry constants `(pad_x=6, pad_y=3, line_gap=2)` are STABLE — altering
  them is major.
- **B.12 Author-visible-impact**: **N = 8 px** ≈ 0.75 em as the threshold.
  Any change that shifts a rendered pill by ≥ 8 px is a MAJOR break.
  `tools/measure_label_shift.py` is the measurement authority.

Plus stability table (§-by-§), YAML front-matter proposal, five opening
normative blockquotes (RFC 2119 / living-standard / stability-level /
open-issues / feedback).

---

## Revised v2 ruleset outline

The seven reports converge on this structure for `docs/spec/
smart-label-ruleset.md` v2:

```
(Front-matter: version, status, editors, last-modified, git-sha)

§0.1 RFC 2119 declaration
§0.2 Conformance classes (Author / Primitive / Emitter / Renderer)
§0.3 Terminology (30+ dfn'd terms)

§1 Invariants
  §1.1 Geometry           G-1..G-8
  §1.2 Collision          C-1..C-7
  §1.3 Typography         T-1..T-6
  §1.4 Accessibility      A-1..A-7
  §1.5 Determinism        D-1..D-4
  §1.6 Error handling     E-1..E-4
  §1.7 Author contract    AC-1..AC-6
  §1.8 Invariant conflicts + tie-breakers

§2 Placement algorithm (Let/Assert/Return step style)
  §2.1 `_nudge_candidates`
  §2.2 `_place_pill` (MW-3, AT RISK)
  §2.3 Pre-conditions + NaN/inf guards

§3 Geometric constants (STABLE table)

§4 Error codes (E1560–E1579, full table)

§5 Primitive Participation Contract
  §5.1 Required interface (6 methods)
  §5.2 Conformance matrix
  §5.3 Forbidden patterns (FP-1..FP-6)
  §5.4 Migration plan

§6 Environment flags (lifecycle table)

§7 Known-bad repros (A..H)

§8 Non-goals (NG-1..NG-18)

§9 Roadmap + open issues (ISSUE blocks)
  MW-2 / MW-3 / MW-4 / LR-1

§10 Versioning policy
  Stability markers, deprecation, compat, author-visible-impact threshold

§11 Change procedure

Appendix A: Test-assertion map (WPT-style)
Appendix B: Alloy model pointer (`docs/formal/smart-label-model.als`)
Appendix C: Acknowledgements (10+7 agent audits)
```

**Target size**: 1200–1700 lines. Current v1 is ~450.

---

## Conflicts across the 7 reports

Zero hard conflicts. Three soft tensions requiring explicit author call:

1. **Invariant count**: agent 1 proposes 42, agent 2 normative rewrite
   assumes ~14 MUST. **Resolution**: 42 invariants, but only 36 are MUST —
   5 SHOULD, 1 MAY. 14 MUST rules in agent 2 are a sub-set (the ones with
   active error codes).

2. **E1560 vs E1550**: agent 2 chose E1560+ citing E1500–E1505 occupied.
   Verify: agent 2 correct, keep E1560–E1579 block.

3. **Alloy model placement**: agent 6 proposes `docs/formal/smart-label-model.als`.
   Agent 7 does not discuss formal artefacts. **Resolution**: include as
   optional Appendix B reference, `[EXPERIMENTAL]` stability.

---

## Action list

**P0 — write v2 ruleset** (this round's deliverable):

1. Rewrite `docs/spec/smart-label-ruleset.md` following the §0..§11 outline
   above. Source material from the 7 reports. Target 1200–1700 lines.
2. Add YAML front-matter + stability markers.
3. Add RFC 2119 preamble + conformance classes.
4. Replace v1 I-1..I-10 with 42-invariant structure.
5. Add §4 error-code table E1560–E1579.
6. Add §5 Primitive Participation Contract + conformance matrix.
7. Add §10 versioning policy.
8. Add Appendix A test-assertion map (stub — tests land in P1 code round).
9. Update `docs/spec/error-codes.md` to reserve E1560–E1579.
10. Update `docs/README.md` index entry with v2 note.

**P1 — code (unchanged from Round 1)**: A1..A5 P0 patches + MW-2/3/4
roadmap. Separate PR. This round only touches docs.

**P2 — optional**: write Alloy model `docs/formal/smart-label-model.als`
(4–6 h). Stub Hypothesis property tests for D-1..D-4 determinism axis.

---

## Acknowledgements

| # | Agent | Output lines | Focus |
|---|-------|-------------:|-------|
| 1 | First-principles invariants | 1120 | 42 invariants, 7 axes |
| 2 | RFC 2119 normative rewrite | 906 | 14/8/6 MUST/SHOULD/MAY, E1560+ |
| 3 | API contract spec | 1585 | Hoare triples, 6 hazards, 6 asymmetries |
| 4 | Edge-case taxonomy | 705 | 16 categories, 5 Critical |
| 5 | Primitive participation | 1298 | 6-method interface, 15-primitive matrix |
| 6 | Spec style audit | 1331 | W3C/TC39/WHATWG conventions, Alloy verdict |
| 7 | Non-goals + versioning | 871 | 18 NG, 12-section versioning policy |
| | **Total** | **7816** | |

Seven parallel opus agents, ~8 k lines of foundation material.
Now consolidate into v2.
