# Navigability Audit

**Document:** `docs/SCRIBA-TEX-REFERENCE.md` (1493 lines)
**Criterion:** NAVIGABILITY — can a reader (often an AI agent) find what they need FAST?

## Verdict: **MEDIUM** (score: Medium, trending toward High)

The document has a clean, mostly-logical numbered spine (overview → environments → commands → primitives → reference tables → examples → patterns → gotchas → limits → errors) and descriptive headings. Keyword search lands well in most cases because section titles embed the literal command/primitive token (`\annotate`, `Tree`, `\foreach`). The two structural weaknesses that drag the score below High are: (1) **no table of contents** at the top of a 1493-line single file, forcing every cold lookup to start with a full-document scroll or grep, and (2) **deliberate topic-splitting** where a single concept (interpolation, Tree node IDs) lives in two non-adjacent sections that neither cross-link nor agree perfectly. For the stated audience — an agent that may not have grep and is reading top-to-bottom — the missing TOC is the single highest-leverage defect.

---

## Structural Assessment

### What works

- **Consistent numbering.** Sections 0–15, with `N.M` subsections and a few `N.M.K` (e.g. §2.2.1, §7.4.1). The scheme never skips or doubles a number; depth never exceeds 3. This is a real asset for cross-references.
- **Descriptive, token-bearing headings.** §5.8 is literally `### 5.8 \annotate{target}{params...}`; §7.5 is `Tree`; §13.9 is `CodePanel line indices are 1-based`. A keyword search for `annotate`, `Tree`, or `CodePanel` lands on the right heading, not a body mention.
- **Logical macro-ordering.** Overview (§0–1) → LaTeX surface (§2) → environments (§3–4) → inner commands (§5) → states (§6) → primitives (§7) → selector table (§8) → examples (§9) → reference tables (§10–11) → patterns (§12) → gotchas (§13) → limits (§14) → error codes (§15). This is the canonical reference ordering the prompt asks for.
- **Several primitives are genuinely self-contained.** §7.5 Tree carries its selectors (L725), segtree topology diagram (L729-738), mutation ops (L757-771), and inline error codes (L773) all in one place. §7.4 Graph likewise co-locates construction params, dynamic edge mutation (L687-696), and node limits. This is the right pattern and shows the author *can* co-locate.
- **Reference tables are where you'd expect them** and are scannable: Visual States (§6, L616-626), Selector Quick Reference matrix (§8, L945-961), Annotation Colors (§11), Limits (§14), Error Codes (§15).

### What hurts

- **No TOC.** The body jumps from a 4-line intro (L1-6) straight into §0 (L8). For a top-to-bottom agent reader with no map, the only way to know §13.2 exists is to reach line 1355. There are no in-document anchors/links between related sections either, so even a reader who knows the structure can't "click through."
- **Concept-splitting across distant sections.** The same concept is documented twice, far apart, with no cross-link in *either* direction:
  - **Interpolation rules:** §5.11 (L482-557, the authoritative deep treatment with the `${i}` vs bare-`i` table and silent-failure note) **and** §13.2 (L1355-1386, a shorter restatement plus the single-iteration-`foreach` workaround). They overlap ~70% and frame the rule slightly differently (§5.11 says bare `i` is a literal key; §13.2 frames it as "reliable inside foreach, unreliable outside"). Neither links the other.
  - **Tree node IDs:** §7.5 (L725, shows `T.node[id]` / `T.node["[0,5]"]` and the segtree topology) **and** §8 (L940-943, the actual quoting *rule* — when to quote, integer coercion). An author in §7.5 sees the forms but not the rule; the rule only appears 215 lines later in §8.
- **§13 Gotchas straddle two roles.** Some gotchas are genuinely cross-cutting and belong in a dedicated list (§13.3 no `\documentclass`, §13.4 math delimiters, §13.6 Starlark int cap). But others are primitive-specific and duplicate or *should* live next to the primitive: §13.9 (CodePanel 1-based) → §7.11; §13.10 / §13.11 (Graph warnings) → §7.4; §13.1 (Stack/Queue recolor timing) → §7.8 / §7.14; §13.8 (annotation headroom) → §5.8. The reader working in §7.4 Graph gets no signal that two gotchas about Graph exist 770 lines away.
- **"Inner Commands (13 total)" vs "All 15 Primitives" counts in headings** are helpful, but the §5 commands and the §7 primitives are the two halves an author shuttles between constantly (a command always targets a primitive selector), and they are 400+ lines apart with the selector bridge (§8) sitting after the primitives rather than between commands and primitives.

---

## Findings Table

| # | Issue | Location | Severity | Fix |
|---|-------|----------|----------|-----|
| 1 | No table of contents in a 1493-line single file; top-to-bottom agent has no map | Top of file (L1-7) | **HIGH** | Add a linked TOC after the intro (L6), one line per §0–15 with anchors |
| 2 | Interpolation documented twice, far apart, with subtly different framing and no cross-link | §5.11 (L482-557) + §13.2 (L1355-1386) | **HIGH** | Make §5.11 canonical; reduce §13.2 to the workaround only + a link back to §5.11 |
| 3 | Tree node-ID *quoting rule* separated from Tree primitive | §7.5 (L725) ↔ §8 (L940-943) | **MEDIUM** | Add a one-line pointer in §7.5 to §8 quoting rule; or inline the quoting rule snippet |
| 4 | Primitive-specific gotchas isolated in §13, no back-pointer from the primitive | §13.1, §13.8, §13.9, §13.10, §13.11 | **MEDIUM** | Add a "Gotchas: see §13.x" line to each affected primitive/command; or move them inline |
| 5 | Selector bridge (§8) sits *after* primitives instead of between commands (§5) and primitives (§7) | §8 (L936) | **LOW** | Acceptable as-is, but cross-link §5 intro and §7 intro to §8 |
| 6 | No task-oriented index ("how do I draw a DP arrow?", "how do I add a graph edge at runtime?") | absent | **MEDIUM** | Add a short "Index by Task" table mapping common author intents → section |
| 7 | No in-document anchor links between any related sections | throughout | **MEDIUM** | Once a TOC exists, add inline `(see §N.M)` links at the split points (findings 2-4) |
| 8 | Error codes appear inline (e.g. §7.5 L773, §13.9 E1115) *and* in §15 table, with no link between them | §7.x, §13.x, §15 | **LOW** | Acceptable redundancy; optionally link inline codes to §15 |

---

## Five Simulated Author Lookups

Assumptions: the author/agent is reading the file fresh, may use keyword scan but has no TOC. "Jumps" = distinct scroll-or-search hops to reach the complete answer.

### Lookup 1 — "How do I draw a DP transition arrow?"
- Scan for "arrow" → lands on §5.8 `\annotate` (L340), specifically the `arrow_from=` block (L392-405) with the exact DP-recurrence example (L402-404). **Answer found, 1 jump.**
- But the dedicated copy-paste snippet is in §12 "DP transition arrows" (L1294-1298), 950 lines later, and color tokens are in §11 (L1271-1281). A complete answer (arrow + color choice + copy-paste) is **3 locations**.
- **Verdict: Mildly frustrating.** The primary answer is fast and correct, but the author doesn't know §12 has a ready snippet or §11 has the color list unless they keep scanning. A "see §11, §12" pointer in §5.8 would close it.

### Lookup 2 — "What visual states exist?"
- Scan for "state" → §6 Visual States (L614-626) is a clean table of all 9 states with colors and meaning, plus the `current` vs `path` convention note (L630). **Answer found, 1 jump. Not frustrating.** This is the doc at its best — a single descriptive heading, a complete table.

### Lookup 3 — "How do I add a graph edge at runtime?"
- Scan for "edge" or "Graph" → §7.4 Graph (L660). The "Dynamic edge mutation" block (L687-696) gives `\apply{G}{add_edge={from=..., to=...}}` with weight variant and error code E1471. **Answer found, 1 jump. Not frustrating.** Co-located correctly. (A second copy-paste flow-network example sits in §12 L1316, but the primary answer is complete on its own.)

### Lookup 4 — "Why does `${i}` not work in my selector?" (interpolation)
- Scan for "interpolation" or "foreach" → likely lands first on §5.11 (L482) *or* §13.2 (L1355) depending on which the search hits. Both look authoritative.
- If the author lands on §13.2 first, they get the "reliable inside foreach" framing and the workaround but **miss** the `${i}` vs bare-`i` mechanics table (L488-493) and the silent-failure explanation (L495-501) that actually answer *why*. If they land on §5.11, they get the mechanics but miss the single-iteration-wrapper workaround (L1377-1385).
- **Verdict: Frustrating, 2 jumps minimum** to get the complete picture — and the reader has no signal a second section exists. This is the worst split in the document because the two halves are *complementary*, not redundant, yet neither references the other.

### Lookup 5 — "What's the node-ID syntax for a segment tree node?" (Tree node ids)
- Scan for "Tree" → §7.5 (L713). Shows `T.node["[0,5]"]` and the topology diagram (L729-738), and states node IDs are range strings (L738). Looks complete.
- But the **rule** for *when* to quote vs use a bare integer (`T.node[8]` vs `T.node["[0,5]"]`, integer coercion) is only in §8 (L940-943), 215 lines later. An author who stops at §7.5 will know segtree IDs are quoted strings but won't learn that integer-declared tree nodes must be *unquoted* (`T.node[8]`, not `T.node["8"]`).
- **Verdict: Frustrating for the edge case, 2 jumps.** The common segtree case is answered in §7.5; the general quoting rule requires finding §8 with no pointer.

**Lookup scorecard:** 3 of 5 are fast and self-contained (states, graph edge, the primary annotate path). 2 of 5 (interpolation, Tree node-id rule) require a second hop to an unsignposted section. The failures cluster exactly on the deliberately-split topics.

---

## Prioritized Navigation Improvements

1. **(HIGH) Add a linked Table of Contents** immediately after the intro (insert before L8). One row per top-level section 0–15 with anchor links. This single change converts every cold lookup from "scroll/grep 1493 lines" to "one click." For the AI-agent audience reading top-to-bottom, it's the difference between knowing the map and discovering sections by accident.

2. **(HIGH) Consolidate interpolation into one canonical home.** Keep §5.11 (L482-557) as the authoritative treatment. Reduce §13.2 to *only* the "compute-bound scalar outside foreach is unreliable + single-iteration-wrapper workaround" content (L1374-1386), and open it with `See §5.11 for the full ${i} interpolation rules.` Add the reciprocal pointer at the end of §5.11. This fixes Lookup 4.

3. **(MEDIUM) Add an "Index by Task" table** (a second small table right under the TOC) mapping author intents to sections, e.g.:
   - "Draw an arrow between cells" → §5.8 (`arrow_from`), §12
   - "Add/remove a graph edge at runtime" → §7.4
   - "Loop over indices / interpolate `${i}`" → §5.11
   - "Segment-tree node IDs" → §7.5 + §8 quoting rule
   - "What state colors exist" → §6
   - "Why is my command silently dropped" → §5.11, §13.2, E1115 (§15)
   This directly serves the prompt's "findable by the task the author is doing" requirement and routes around the splits.

4. **(MEDIUM) Cross-link the split/scattered topics** once anchors exist:
   - §7.5 Tree → add `(node-ID quoting rule: see §8)` next to the selectors line (L725).
   - Each primitive/command with a gotcha → add a trailing `Gotchas: §13.x` line (Graph §7.4 → §13.10/§13.11; CodePanel §7.11 → §13.9; Stack/Queue → §13.1; annotate §5.8 → §13.8).
   - §5 intro and §7 intro → `Selectors are documented in §8.`

5. **(LOW) Leave §13 as a gotchas section but de-duplicate the primitive-specific ones** by either (a) moving the primitive-specific gotchas inline next to their primitive and keeping §13 for cross-cutting rules only, or (b) keeping §13 as the canonical home but adding the back-pointers from improvement 4. Option (b) is lower-risk and preserves the "one place to skim all the traps" value of §13.

6. **(LOW) Add anchor links from inline error-code mentions to §15** so a reader who hits `E1471` in §7.4 or `E1115` in §13.9 can jump to the one-line meaning.
