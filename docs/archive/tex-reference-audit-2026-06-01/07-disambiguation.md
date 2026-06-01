# Disambiguation Audit

**Doc audited:** `docs/SCRIBA-TEX-REFERENCE.md` (1493 lines)
**Criterion:** DISAMBIGUATION — where do two similar-looking constructs risk being confused because the doc fails to draw a clear line?
**Date:** 2026-06-01

## Verdict: MEDIUM

The doc disambiguates its two flagship confusion pairs very well: `arrow=true` vs `arrow_from=` has a dedicated vs-table (§5.8 L428–435), and `${i}` vs bare `i` has a worked vs-table plus a "silent failure mode" callout (§5.11 L482–515). `current` vs `path` (§6 L630) and `\compute` prelude-vs-step (§3.2/§5.2) are also well handled.

The score is held back by two structural gaps that produce silent wrong output:

1. **`label` is overloaded across four distinct meanings** (shape caption, annotation pill text, `\step` frame id, env aria-label) and **`label` vs `labels` sit adjacent in the same `\shape` line** (L639) with neither term ever defined. This is the single worst disambiguation hole.
2. **Indexing conventions (0-based vs 1-based vs `0=bottom`) are scattered** across §7.8, §7.9, §7.11 with the only consolidated note (§13.9) covering just CodePanel-vs-Array. No single indexing table exists.

`\highlight` vs `\recolor{state=highlight}` is documented but the explanation is buried in a State-table cell (§6 L626) rather than presented as a vs-treatment where authors actually choose between the two commands (§5.6/§5.7).

## Findings Table

| # | Confusable pair | Where documented | Disambiguation | Severity | One-line fix |
|---|---|---|---|---|---|
| 1 | `label` (caption) vs `labels` (axis tick labels) | Both appear unexplained in same line L639, L654; `labels` never has its own definition | **MISSING** | High | Add a "`label` vs `labels`" note in §7.1 / §8: `label`=single caption string, `labels`=per-cell/tick list |
| 2 | `label` overloaded: shape caption (§5.5/§7.x) vs annotation pill text (§5.8 L353) vs `\step[label=]` frame id (§5.3 L276) vs env aria-label (§10 L1263) | Four locations, no cross-link or glossary | **MISSING** | High | Add a glossary row or footnote enumerating the four `label` meanings by context |
| 3 | Indexing: 0-based (Array/Grid/Plane2D) vs 1-based (CodePanel) vs `0=bottom` (Stack) | Scattered: §7.8 L807, §7.9 L840, §7.11 L890, consolidated only partially in §13.9 L1421 (CodePanel vs Array/Grid only) | **PARTIAL** | High | Add one "Indexing conventions" table covering all primitives; cross-link from §8 selector table |
| 4 | `\highlight` (ephemeral) vs `\recolor{state=highlight}` (persistent) | §5.6 L334, §5.7 L337, and a cell in §6 L626 | **PARTIAL** | Medium | Add a one-line "when to use which" note at §5.6/§5.7 pointing to the §6 cell |
| 5 | `arrow=true` vs `arrow_from=selector` | §5.8 vs-table L428–435 | **GOOD** | — | None (model example for the rest of the doc) |
| 6 | `current` vs `path` states | §6 L630 "Semantic convention" note | **GOOD** | — | None |
| 7 | `${i}` vs bare `i`; `${arr[i]}` subscript | §5.11 vs-table L489–493, silent-failure callout L495–501, subscript L517–531 | **GOOD** | — | None |
| 8 | `\compute` in prelude (shared) vs in `\step` (frame-local) | §3.2 L204, §5.2 L238 | **GOOD** | Low | Optional: cross-link the two |
| 9 | `\annotate` vs `\reannotate` | §5.8 L340 vs §5.9 L437 | **PARTIAL** | Medium | Add one line: `\annotate` creates, `\reannotate` mutates an existing annotation (requires `color=`, E1113) |
| 10 | diagram vs animation environments | §3 L170 vs §4 L213 | **PARTIAL** | Medium | §4 says "no `\step`/`\narrate`" but no vs-table; add a 4-row capability table |
| 11 | Selector node-id quoting: unquoted ident vs unquoted int vs quoted | §8 L940–943 | **GOOD** | Low | None; the int-vs-quoted-int edge case (`G.node[1]` not `G.node["1"]`) is well covered |
| 12 | `${var}` reliable inside `\foreach` vs unreliable outside | §13.2 L1355–1386 | **GOOD** | — | None (but partially redundant with §5.11; see note below) |
| 13 | `q.front`/`q.rear` (pointer cells) vs `q.cell[i]` (data) | §7.14 L923–925 | **PARTIAL** | Low | Adequate; minor — clarify `front`/`rear` are pointer markers, not data cells |

## Prioritized Fixes

### P1 — High severity, silent-wrong-output risk

1. **`label` vs `labels` note (Finding #1).** In §7.1 Array and §8 selector reference, add:
   > `label` = a single caption string shown beside the whole shape (supports `$...$`). `labels` = a per-element list of tick/index captions (e.g. `labels="0..7"`). They are unrelated; supplying `labels=` where you meant `label=` silently mislabels every cell.
   Confusion arises at the `\shape` line (L639) — the fix must live there or be cross-linked from there.

2. **Indexing conventions table (Finding #3).** Promote §13.9 into a full table in §8 (where selectors are chosen):
   | Primitive | First index | Note |
   |---|---|---|
   | Array, Grid, DPTable, Matrix, Plane2D, HashMap, LinkedList, Queue | `0` | 0-based |
   | Stack | `0` = **bottom**, `.top` = top | 0-based but semantically inverted |
   | CodePanel | `1` | 1-based; `line[0]` → E1115 drop |
   Currently an author reading §7.8 (Stack) or §7.9 (Plane2D) gets no warning that CodePanel differs, and §13.9 only contrasts CodePanel with Array/Grid — Stack's `0=bottom` and Plane2D are never tied into the same comparison.

3. **`label` overload glossary (Finding #2).** One footnote near §5.5 listing the four meanings, keyed by command context. Each individual site is correct; the hazard is purely cross-construct.

### P2 — Medium severity, mostly cross-link gaps

4. **`\annotate` vs `\reannotate` line (Finding #9).** §5.9 L437 says "Recolors an existing annotation" but never contrasts it head-to-head with `\annotate` (create). Add at §5.9 top: "Use `\annotate` to create an annotation, `\reannotate` to mutate one that already exists. `\reannotate` requires `color=` (E1113) and silently no-ops if the target has no annotation."

5. **diagram vs animation capability table (Finding #10).** §4 L213 says "Same primitives, no `\step` or `\narrate`" inline. A small table (frames? narration? `\highlight`/ephemeral? persistent commands?) would prevent authors from reaching for animation-only commands in a diagram (the E1050/E1054 errors at §15 are the symptom of this confusion).

6. **`\highlight` vs `\recolor{state=highlight}` cross-link (Finding #4).** The authoritative distinction lives in a State-table cell (§6 L626) — not findable from §5.6/§5.7 where authors pick the command. Add a one-liner at §5.6 and §5.7 pointing to §6, or a 2-row mini vs-table.

### P3 — Low / cleanup

7. **Redundancy between §5.11 and §13.2 (Finding #12).** Both cover `${var}` interpolation reliability but with *different* framing: §5.11 says bare `i` vs `${i}` (form), §13.2 says inside-vs-outside-`\foreach` (location). They are not contradictory but a reader hitting §13.2 may not realize §5.11 already covered the form distinction. Cross-link them.

## Notes

- The doc's strongest disambiguation pattern is the explicit two-column vs-table (Findings #5, #7). Replicating that shape for Findings #1, #2, #3, #9, #10 would raise the verdict to High.
- No disambiguation issue here is a correctness bug in the doc's *claims* — every individual definition is accurate. The gaps are purely structural: confusable constructs are documented in separate locations without a side-by-side line, so authors mix them up before they ever reach the (correct) clarifying text.
