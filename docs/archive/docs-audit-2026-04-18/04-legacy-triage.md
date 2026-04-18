# Legacy Docs Triage

Audit date: 2026-04-18
Scope: docs/legacy/ — all files and subdirectories

## Summary

| Classification | Count | Items |
|---|---|---|
| DELETE | 7 | mock-diagram-widget.html, frog1-demo.zip, frog1-demo/, monkey-apples-demo/, swap-game-demo/, swap-game-demo-ver2/, swap-game-demo-ver3/ |
| ARCHIVE-MOVE | 6 | ANIMATION-RULESET.md, STATIC-FIGURE-RULESET.md, EDITORIAL-PRINCIPLES.md, EDITORIAL-PRINCIPLES-V2.md, USAGE-DIAGRAM-WIDGET.md, pivot-1-research/ (as folder) |
| MERGE | 1 | PHASE2_DECISIONS.md |
| KEEP | 1 | README.md |

**Totals: 7 delete, 6 archive-move, 1 merge, 1 keep**

---

## Triage Table

| File/folder | Last update | Classification | Reason | Target (if merge/move) |
|---|---|---|---|---|
| `README.md` | 2026-04-12 | KEEP | Accurate meta-index that explains the pivot and scope of the whole legacy/ dir; linked from main docs/README.md. | — |
| `ANIMATION-RULESET.md` | 2026-04-09 | ARCHIVE-MOVE | 624-line D2-first design doc; not a current spec but preserves motion grammar rationale not fully captured in docs/spec/ruleset.md or docs/guides/editorial-principles.md. Historical value for future animation extensions. | `docs/archive/legacy-2026-04-09/ANIMATION-RULESET.md` |
| `STATIC-FIGURE-RULESET.md` | 2026-04-09 | ARCHIVE-MOVE | 576-line companion to ANIMATION-RULESET; static/animation decision matrix and Tufte density principles have editorial value beyond current guides. docs/guides/how-to-use-diagrams.md covers the LaTeX mechanics but not the philosophical rationale. | `docs/archive/legacy-2026-04-09/STATIC-FIGURE-RULESET.md` |
| `EDITORIAL-PRINCIPLES.md` | 2026-04-09 | ARCHIVE-MOVE | v1 editorial template (11-section, prose-first); superseded by V2 and then by docs/guides/editorial-principles.md; kept for lineage per README; no unique content absent in successors. | `docs/archive/legacy-2026-04-09/EDITORIAL-PRINCIPLES.md` |
| `EDITORIAL-PRINCIPLES-V2.md` | 2026-04-09 | ARCHIVE-MOVE | v2 visualization-first template (8-section, viz-load-bearing); its principles are partially reflected in docs/guides/editorial-principles.md but the per-algorithm viz lookup table and anti-pattern catalog are not duplicated. Worth archiving not deleting. | `docs/archive/legacy-2026-04-09/EDITORIAL-PRINCIPLES-V2.md` |
| `PHASE2_DECISIONS.md` | 2026-04-09 | MERGE | 17 concrete TDD contract decisions (D-01–D-17) for the v0.1 TeX plugin — batch KaTeX dispatch, snapshot normalization, Pipeline error contracts, SubprocessWorkerPool lifecycle. These decisions are still in force; the current spec files (docs/spec/architecture.md, docs/guides/tex-plugin.md) do not contain this rationale. Should be folded into a "Design decisions" appendix. | Merge into `docs/spec/architecture.md` (appendix) or create `docs/spec/design-decisions.md` |
| `USAGE-DIAGRAM-WIDGET.md` | 2026-04-09 | ARCHIVE-MOVE | Author guide for the old diagram widget; the widget runtime is gone. However, the segtree worked example (author markdown → Scriba output mapping) is non-trivially instructive and predates the equivalent cookbook entry. Archive not delete. | `docs/archive/legacy-2026-04-09/USAGE-DIAGRAM-WIDGET.md` |
| `mock-diagram-widget.html` | 2026-04-09 | DELETE | 22KB standalone HTML mock of the widget runtime; zero-JS static SVG has completely replaced the widget model; no unique content; a binary/HTML artefact with no doc value. | — |
| `frog1-demo.zip` | 2026-04-09 | DELETE | Zip archive of frog1-demo/; redundant with the unpacked frog1-demo/ folder already in tree; binary with no independent doc value. | — |
| `frog1-demo/` | 2026-04-09 | DELETE | HTML/JS demo (index.html 4.4K, app.js 19K, styles.css 9.6K) targeting the old widget runtime. The pedagogical content is now covered by docs/cookbook/06-frog1-dp/ (input.md + output.html). Fully superseded. | — |
| `monkey-apples-demo/` | 2026-04-09 | DELETE | HTML/JS demo (index.html 15.5K, app.js 16K, styles.css 18.5K) for the monkey/apples counting example. Superseded by docs/cookbook/08-monkey-apples/. | — |
| `swap-game-demo/` | 2026-04-09 | DELETE | Version 1 of swap-game HTML/JS demo (app.js 29K). Superseded by swap-game-demo-ver2, swap-game-demo-ver3, and ultimately docs/cookbook/07-swap-game/. | — |
| `swap-game-demo-ver2/` | 2026-04-09 | DELETE | Version 2 of swap-game demo (app.js 11.5K). Intermediate iteration; superseded by ver3 and cookbook. | — |
| `swap-game-demo-ver3/` | 2026-04-09 | DELETE | Version 3 of swap-game demo (app.js 18.3K). Final widget-era iteration; superseded by docs/cookbook/07-swap-game/. | — |
| `pivot-1-research/` | 2026-04-10 | ARCHIVE-MOVE | 11 research files (A1–A8, KATEX-BUNDLING, LIBRARY-RECOMMENDATIONS, README); proposed and rejected Lit 3 + Motion One + ELK.js + uPlot runtime-JS architecture (Pivot #2 rejected it 2026-04-09). README already says "decision trail only." KaTeX bundling analysis (KATEX-BUNDLING.md) still has operational relevance. Move whole folder; do not delete — the reasoning trail explains why several dead-end approaches were not taken. | `docs/archive/legacy-2026-04-09/pivot-1-research/` |

---

## Per-file Detail (non-trivial cases)

### PHASE2_DECISIONS.md — MERGE

Content: 17 entries (D-01–D-17) recording test-design and contract choices made during Phase 2 TDD:
- D-01: batch vs per-expression KaTeX dispatch (locked to batch, 10–50× speed reason)
- D-02: snapshot normalization strategy (strip + collapse whitespace, not byte-exact)
- D-03–D-07: worker lifecycle, Pipeline empty-renderers, render_inline_tex wiring, KeyError vs WorkerError
- D-08–D-09: error message format (substring match), XSS assertion on raw output not bleach
- D-10–D-17: detect() shape, assets() filenames, Document.versions, constructor keyword-only, close() idempotency, fixture sharing rationale

These decisions are live constraints on the test suite under `tests/`. They are not captured in any current doc. The file explicitly says it targets the v0.1 TeX plugin contract, which remains in force.

Recommended merge target: `docs/spec/architecture.md` as a new `## Appendix: Phase 2 TDD Contract Decisions` section, or a standalone `docs/spec/design-decisions.md` if the appendix would push architecture.md over 50KB (it is currently 40KB).

### pivot-1-research/ — ARCHIVE-MOVE

The 8 numbered research files (A1–A8) proposed a full JS runtime stack that was rejected wholesale. Their value is decision trail, not spec. However:

- `KATEX-BUNDLING.md` (175 lines) analyzes three bundling options for KaTeX (global npm, wheel vendor, bundled wheel). This is operational and partially relevant — the current `docs/planning/open-questions.md` references Q32 which this file feeds.
- `LIBRARY-RECOMMENDATIONS.md` (202 lines) is a synthesis summary; some recommendations (KaTeX, Graphviz subprocess, plane2d primitive) were cherry-picked into the current extensions. The cherry-picking rationale is not recorded elsewhere.
- `01-animatable-equations.md` (142 lines) contains the KaTeX vs MathJax vs Temml vs typst.ts comparison table that justified KaTeX selection; not duplicated in any current doc.

None of these should be deleted. Archive as a unit under `docs/archive/legacy-2026-04-09/pivot-1-research/`.

### ANIMATION-RULESET.md + STATIC-FIGURE-RULESET.md — ARCHIVE-MOVE (not DELETE)

Both are 600-line design documents with content that docs/spec/ruleset.md (55KB) does not fully cover:
- The four invariant principles (deterministic, build-time, source-locality, D2-only) are stated in ANIMATION-RULESET but not in ruleset.md as philosophical framing
- The static/animation decision matrix (2-eyes vs 1-eye-over-time, Tufte small multiples argument) in STATIC-FIGURE-RULESET is absent from docs/guides/how-to-use-diagrams.md
- The Django ↔ Scriba layering analogy in ANIMATION-RULESET explains the architectural shape in a way architecture.md does not

The syntax is obsolete (D2-first DSL, not LaTeX environments). The principles are not. Archive, do not delete.

### EDITORIAL-PRINCIPLES-V2.md — ARCHIVE-MOVE (not DELETE)

The per-algorithm viz lookup table (BFS/DFS, DP, segment tree, two-pointers, binary search, greedy, graph SP, sparse segtree+lazy) with canonical viz patterns and anti-patterns is not present in docs/guides/editorial-principles.md. That guide covers authoring philosophy for the new LaTeX model; V2 covers editorial design decisions per algorithm class. The anti-pattern catalog (toy example graph, widget ghetto, prose block without figure, code before 3 visuals) is actionable and unreplicated.

---

## Recommended Deletion Order (safe sequence)

Delete in this order to avoid confusion if any git bisect or archaeology occurs mid-cleanup:

1. `docs/legacy/frog1-demo.zip` — binary duplicate of frog1-demo/, safe to remove first
2. `docs/legacy/mock-diagram-widget.html` — standalone HTML, no references inbound
3. `docs/legacy/frog1-demo/` — superseded; cookbook/06-frog1-dp/ confirmed present
4. `docs/legacy/monkey-apples-demo/` — superseded; cookbook/08-monkey-apples/ confirmed present
5. `docs/legacy/swap-game-demo/` — oldest iteration; cookbook/07-swap-game/ confirmed present
6. `docs/legacy/swap-game-demo-ver2/` — intermediate iteration, no unique content
7. `docs/legacy/swap-game-demo-ver3/` — final widget iteration, superseded by cookbook

Do NOT delete until archive-moves are committed:
- ANIMATION-RULESET.md, STATIC-FIGURE-RULESET.md, EDITORIAL-PRINCIPLES.md, EDITORIAL-PRINCIPLES-V2.md, USAGE-DIAGRAM-WIDGET.md
- pivot-1-research/ (entire folder)

Do NOT delete until merge is complete:
- PHASE2_DECISIONS.md (merge into docs/spec/architecture.md or docs/spec/design-decisions.md first)

README.md stays in docs/legacy/ permanently as the orientation document for the archive.
