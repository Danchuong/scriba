# Plan — Fix Graph `layout_seed` ergonomics & layout quality

**Date:** 2026-06-03
**Goal:** Stop authors from having to "guess an integer" for decent graph
layouts. Kill the three root issues: (1) force layout hugs the canvas border,
(2) disconnected nodes get flung to a corner, (3) the only knob is a magic seed.
**Context:** see `docs/analysis/layout-seed-analysis-2026-06-03.md`.
**Rules:** no code in this plan. **Commit after every phase.** Each phase lists
its agent count. Phases ship in order (each builds on the previous).

---

## Phase 1 — Docs-first authoring guidance
**Agents: 1**

Cheapest, highest-leverage: redirect authors to patterns that avoid the problem
before any code changes.

- Rewrite the Graph layout section of `docs/SCRIBA-TEX-REFERENCE.md`:
  - Promote "declare all nodes **and** edges up front, animate with `\recolor`/
    state instead of `add_edge`/`remove_edge`" as the default recommendation.
  - Recommend `layout="stable"` for small graphs (≤20 nodes).
  - Demote `layout_seed` to an explicitly **optional, cosmetic/reproducibility**
    knob — not something most authors need.
- Add a short "Graph layout — best practices" callout box.
- **Verify:** docs links/anchors valid; the reference's own examples still render
  via `render.py`; no stale claims about seeds.
- **Commit:** `docs(graph): author guidance for stable layouts; demote layout_seed`.

---

## Phase 2 — Isolated-node placement
**Agents: 2** (1 implementer · 1 reviewer/tester)

Disconnected nodes are the most visible defect and the lowest-risk fix.

- Detect nodes with no incident edges at construction and place them in a tidy
  reserved lane/row instead of letting repulsion fling them to a corner.
- Keep behaviour deterministic and seed-respecting.
- **Verify:**
  - Unit test: a graph with an isolated node places it in the reserved lane, not
    a corner.
  - CDP geometry check (reuse the `.demo/cdp_probe.py` approach): isolated node is
    within the central band, not on a border.
  - Regenerate affected goldens; full suite green.
- **Commit:** `fix(graph): place isolated nodes in a lane instead of corner-fling`.

---

## Phase 3 — Layout-quality scorer + auto-seed selection
**Agents: 3** (1 scorer · 1 auto-seed integration · 1 reviewer/tester)

Removes the magic-integer guess for the default case.

- Build a pure layout-quality scorer: penalise border-hugging, edge crossings,
  and poor aspect/spread balance. Deterministic, no rendering needed.
- Auto-seed: when the author does **not** pin `layout_seed`, try N candidate
  seeds at build time, score each, keep the best. An explicit `layout_seed`
  always wins (reproducibility preserved).
- Bound the cost (small N; document the build-time tradeoff; respect existing
  node-count guards).
- **Verify:**
  - Scorer unit tests on hand-crafted good/bad layouts.
  - Determinism: same graph → same chosen seed every run.
  - Before/after CDP comparison on a few sample graphs shows fewer border nodes /
    crossings.
  - Goldens regenerated; suite green; build-time perf noted.
- **Commit:** `feat(graph): auto-select best layout seed via quality scorer`.

---

## Phase 4 — Author warning for isolated nodes
**Agents: 1**

Turn a silent cosmetic surprise into actionable guidance.

- Emit a soft warning when a Graph has isolated nodes at construction, pointing to
  "declare edges up front or use `layout=stable`". Non-fatal; document the code.
- **Verify:** unit test asserts the warning fires once for an isolated-node graph
  and not for a fully-connected one; negative snippets unaffected.
- **Commit:** `feat(graph): warn on isolated nodes at construction`.

---

## Phase 5 — Release
**Agents: 1**

- Bump `SCRIBA_VERSION` (rendered bytes changed) and the SemVer `__version__`.
- Update `CHANGELOG.md` (Changed/Fixed entries for Phases 1–4).
- Final full golden regen + whole-suite green; build sdist + wheel; `twine check`.
- **Commit:** `chore(release): <new version>` (PyPI upload left to the user).

---

## Agent budget

| Phase | Theme | Agents |
|------|-------|-------:|
| 1 | Docs guidance | 1 |
| 2 | Isolated-node placement | 2 |
| 3 | Scorer + auto-seed | 3 |
| 4 | Isolated-node warning | 1 |
| 5 | Release | 1 |
| **Total** | | **8** |

## Cross-cutting checks (every phase)
- Reuse the Chrome-CDP geometry probe to validate layout claims (no Playwright).
- Run unit + tex + doc_coverage + golden suites; regenerate goldens only after
  reviewing the diff is attributable to the change.
- Commit at the end of the phase only when its suite is green.

## Out of scope
- Semantic layout knobs (`compact`/`spread`) — revisit after Phase 3 if auto-seed
  proves insufficient.
- Directed-graph / hierarchical layout quality (separate track).
- Changing the force algorithm itself (FR stays; we only choose better seeds and
  handle isolated nodes).
