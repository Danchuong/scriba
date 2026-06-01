# Consistency Audit

**Target:** `docs/SCRIBA-TEX-REFERENCE.md` (1494 lines)
**Criterion:** Internal contradictions only — does the doc contradict itself? (Not checked against code.)

## Verdict

**Score: Medium consistency.**

The document is largely self-consistent in its core syntax (selector forms, command names, the §5 "13 total" and §7 "15 Primitives" counts both check out exactly). However, several genuine internal contradictions exist, two of which are likely to actively mislead an author writing `.tex`:

- A **broken cross-reference** ("§7.1 of the spec", L288) that does not resolve within the doc and collides with the doc's own §7.1 (Array).
- The same **error code (E1501)** is defined two contradictory ways.
- The **`\recolor` state list disagrees with itself** (8 states in §5.7 vs the 9th, `highlight`, declared a valid `\recolor` state in §6).
- **Boolean casing** flips between `true`/`false` (every `.tex` example) and `True`/`False` (§13.10–13.11 prose).

None are catastrophic, but the E1501 and §7.1 cross-ref issues are the ones most likely to confuse. Hence Medium, not High.

## Findings

| # | Contradiction | Location A | Location B | Severity | Canonical / Fix |
|---|---------------|-----------|-----------|----------|-----------------|
| C1 | **E1501 has two contradictory meanings.** §7.4 and §14 say E1501 = exceeding the ≤100-node limit for **force** layout. §15 defines E1501 = "Too many nodes for **stable** layout — falling back to force layout." Same code, opposite layout, opposite behavior (hard limit vs. silent fallback). | L698, L1462 (force, ≤100, hard) | L1493 (stable, fallback) | HIGH | Pick one. L698/L1462 are stated twice and tie E1501 to the force-layout cap; make §15 L1493 read "Too many nodes for force layout (>100)" to match. |
| C2 | **Dangling / wrong cross-reference "§7.1 of the spec".** L288 cites "(§7.1 of the spec)" for `\hl` cross-references, but this doc has no §7.1 about `\hl` — its own §7.1 is "Array". No external spec §7.1 is otherwise referenced; the doc elsewhere points `\hl` rules to §5.13 (L274) and §5.3 (L610). | L288 | §5.13 L578, §5.3 L610, §7.1 L636 (Array) | HIGH | Replace "§7.1 of the spec" with "§5.13" (the `\hl` section). The "of the spec" wording is a leftover from an external doc. |
| C3 | **`\recolor` valid-state list: 8 vs 9.** §5.7 lists exactly 8 states (`idle, current, done, dim, error, good, path, hidden`) and presents it as the complete set. §6 adds a 9th, `highlight`, and explicitly says it is "also accepted by `\recolor{X}{state=highlight}` as a persistent variant." | L338 (8 states) | L626 (`highlight` accepted by `\recolor`) | HIGH | §6 is canonical (it documents the extra behavior deliberately). Update §5.7 to either list `highlight` or add "see §6 for the additional `highlight` state." |
| C4 | **Boolean literal casing inconsistent.** Every `.tex` example uses lowercase `true`/`false` (e.g. L219, L356, L666, L767). §13.10–13.11 prose and headings use Python-style `True`/`False` for the *same* params: `Graph(layout="stable", directed=True)`, `directed=True`, `global_optimize=True`, `Graph(global_optimize=True)`. Within §13.10 itself, the heading says `directed=True` but the body says `directed=true`. | L219/L356/L666/L685 (`true`/`false`) | L1430, L1433, L1434 (`True`); L1431 body uses `true` | MEDIUM | Lowercase `true`/`false` is canonical for `.tex` source (it's what every example uses). Rewrite §13.10–13.11 headings/prose to `directed=true`, `global_optimize=true`. (L127 `enable_copy_button=True` is a Python constructor arg, not `.tex` — leave it.) |
| C5 | **Plane2D: "five families" vs "All six forms".** L965 says Plane2D "has five element-type families." Three lines later L976 says "All six forms work with…". The intervening table (L967–974) lists 6 rows, but the 6th (`.all`) is an aggregate selector, not an element-type family — so both numbers describe the same table differently. | L965 ("five") | L976 ("All six") | MEDIUM | Reconcile wording: keep "five element-type families" and change L976 to "All five element selectors plus `.all` work with…" (or "All six selector forms"). The numbers aren't wrong, the phrasing collides. |
| C6 | **`${var}` reliability described two opposite ways.** §5.2 (L233) and §8 (L963) state `${name}` interpolation works "inside any index" unconditionally; §5.11 examples use `${dp_vals[i]}` etc. freely. §13.2 (L1355–1375) says `${var}` outside `\foreach` is "UNRELIABLE", "may fail", silent no-op. A reader of §5.2/§8 alone would believe interpolation is universal. | L233, L963 (unconditional) | L1355–1375 (unreliable outside foreach) | MEDIUM | §13.2 is the precise/canonical rule. Add a one-line caveat at §8 L963 ("reliable inside `\foreach`; see §13.2 for the deferred-resolution limitation outside it") so the quick-reference doesn't contradict the gotcha. |
| C7 | **Graph node-ID selector form shown two ways without a stated rule at first appearance.** §4 (L220) and §9 examples use `G.node[A]` (unquoted); §7.4 selector line (L674) shows both `G.node[id]` AND `G.node["A"]` side-by-side without saying when each applies. The disambiguating rule only appears later in §8 (L940–943). | L220/L674 (`G.node[A]` and `G.node["A"]` shown together) | L940–943 (the actual rule) | LOW | Not a true contradiction (§8 resolves it), but §7.4 L674 listing `G.node["A"]` for a plain identifier "A" contradicts §8's rule that quotes are only for IDs with special chars. Drop `G.node["A"]` from L674 or add "(quote only when the ID has special chars — see §8)". |
| C8 | **Stable-layout frame cap appears only once.** §14 L1463 lists "Graph stable layout: ≤20 nodes, **≤50 frames**." The ≤50-frame cap for stable layout is never mentioned in §7.4 / §7.4.1 where stable layout is described, and the general frame limit (§3.2 L202, §14 L1454) is "30 soft / 100 hard." Not strictly contradictory (different scope), but a reader following §3.2 would not know stable-layout scenes cap at 50. | L1463 (≤50 frames, stable) | L202, L1454 (30/100 general) | LOW | Add the ≤50-frame stable-layout note to §7.4.1's stable row, or footnote it in §14 to clarify it overrides the 100-hard limit for stable scenes. |

## Prioritized Fixes

1. **C1 (E1501):** Rewrite §15 L1493 to define E1501 as the force-layout >100-node limit, matching L698/L1462. (One code, one meaning.)
2. **C2 (§7.1 cross-ref):** Change "§7.1 of the spec" (L288) → "§5.13". Self-referential and currently points at the Array section.
3. **C3 (state count):** Add `highlight` (or a pointer to §6) to the §5.7 state list so §5.7 and §6 agree on 8-vs-9.
4. **C4 (boolean casing):** Lowercase `True`→`true` in §13.10–13.11 headings/prose for `.tex` params.
5. **C5 (Plane2D five/six):** Align the "five families" / "six forms" wording at L965/L976.
6. **C6 (`${var}` reliability):** Cross-link §8 L963 to the §13.2 caveat.
7. **C7 / C8 (LOW):** Tidy the `G.node["A"]` example at L674 and surface the stable-layout ≤50-frame cap near §7.4.1.

## Counts that DO check out (verified, no contradiction)

- §5 "Inner Commands (13 total)" → exactly 13 subsections 5.1–5.13. ✓
- §7 "All 15 Primitives" → exactly 15 subsections 7.1–7.15 (Matrix/Heatmap is one entry, two names — correctly framed as an alias, L783). ✓
- Annotation color tokens: §5.8 (L355), §5.9 (L444), §11 (L1273) all list the same 6 (`info, warn, good, error, muted, path`). ✓
- Frame limits 30 soft / 100 hard: §3.2 L202 and §14 L1454 agree. ✓
- `\hl` error codes E1320/E1321 (L587–588) used consistently. ✓
