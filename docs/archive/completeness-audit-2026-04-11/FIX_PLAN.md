# Scriba Completeness Audit — Fix Plan

**Date:** 2026-04-11
**Source:** 14-agent completeness audit (`docs/archive/completeness-audit-2026-04-11/`)
**Scriba version:** v0.5.1 @ `eb4f017`
**Target:** v0.5.2 (quick wins) → v0.6.0 (completeness) → v0.7.0 (polish)

---

## Guiding principles

1. **Don't rush P0 (Tree/Graph mutation).** This is architectural — needs RFC first, not agents throwing code at it.
2. **Ship quick wins BEFORE design.** 162 LoC independent of the RFC work. Release as v0.5.2 immediately.
3. **Fix cookbook lies LAST, not first.** `h07_splay_amortized.tex` and `h08_persistent_segtree.tex` lie because primitives lack mutation — you cannot truthfully fix examples before fixing the primitives.
4. **Commit audit reports first.** Preserve the 14 reports and `summary.md` before any implementation work begins.

---

## Phase 0 — Preserve audit (5 minutes, immediate)

```bash
git add docs/archive/completeness-audit-2026-04-11/
git commit -m "docs(scriba): add 14-agent completeness audit report"
```

No design. No thinking. Just commit so the work is preserved across sessions.

---

## Phase 1 — v0.5.2 Quick Wins (1-2 days, ~250 LoC)

**No design work needed.** Every fix has a concrete `file_path:line_number` from the audit.

Spawn **3 agents in parallel** following the Wave 4A pattern. Each agent owns a distinct file boundary to avoid merge conflicts.

### Agent W5.1 — Parser quick wins (~40 LoC)

| Fix | Location | Unblocks |
|---|---|---|
| Bare-token fallthrough in `_read_param_brace` | `grammar.py:1449` | E1012 trigger; `\apply{stk}{pop}` works naturally |
| LBRACE branch in `_parse_param_value` | `grammar.py:1472-1513` | LinkedList `insert={dict}` currently unreachable |
| Unicode NFC normalize on identifiers | `parser/selectors.py:260` | NFD vs NFC asymmetry (Agent 14) |

**Tests:** regression tests for all three. Convex hull `.tex` should compile with bare `\apply{stk}{pop}` syntax.

**Source agents:** 01 (API consistency), 14 (red-team)

### Agent W5.2 — Emitter + primitives quick wins (~30 LoC)

| Fix | Location | Unblocks |
|---|---|---|
| Skip guard for bare-shape in selector validator | `emitter.py:330` | 1 line; kills `stk`/`pq`/`G` warning class |
| Truthiness check for `dequeue=false` | `queue.py:141` | 1 line; silent Queue bug |
| Wire `PrimitiveBase.set_label()` into emitter | `emitter.py` near line 445-446 | Currently dead API: parse stores into `ShapeTargetState.label`, emitter never reads it |

**Tests:** convex hull + dijkstra compiles with zero warnings. Queue dequeue tests cover `false`/`0`/`None`.

**Source agents:** 02 (dynamic-op gaps), 03 (emitter warnings), 01 (API consistency)

### Agent W5.3 — Error hints hoisted (~90 LoC)

| Fix | Location | Unblocks |
|---|---|---|
| Hoist `_fuzzy_suggest` to `errors.py` as `suggest_closest()` | `errors.py` | Cross-module reuse without circular imports |
| `_raise_unknown_enum` helper in `grammar.py` | `grammar.py` | Collapses 5 enum raise sites (E1004/E1006/E1109/E1112/E1113) to 1-liners with uniform fuzzy hints |
| New E1114 for unknown shape kwarg | `primitives/base.py` + per-primitive `ACCEPTED_PARAMS: ClassVar[frozenset[str]]` | Plane2D `xranges=` silent-drop (opt-in: empty frozenset = no check, preserves backward compat) |

**Tests:** typing `state=active` gives "did you mean `current`?" hint. Typing `xranges=[-1,8]` on Plane2D raises E1114 with "did you mean `xrange`?"

**Source agent:** 05 (error hints)

### Release checklist

- [ ] All 3 agents merged
- [ ] CHANGELOG entry for v0.5.2
- [ ] `pyproject.toml` + `scriba/_version.py` bumped to 0.5.2
- [ ] `SCRIBA_VERSION` stays at 2 (no core contract change)
- [ ] Full test suite passes
- [ ] Tag `v0.5.2` + push + origin

---

## Phase 2 — RFCs (2-3 days, human work, 0 code)

**Do NOT spawn agents for this phase.** Agents don't have the context to make architectural decisions. Write RFCs yourself, or collaborate section by section.

### RFC-1: Tree/Graph Mutation API

**File:** `docs/rfc/001-tree-graph-mutation.md` (~200 lines target)

**Questions to lock:**

1. **Stable node IDs**: when reparenting, keep old positions? Warm-start Reingold-Tilford with hints, or full re-layout?
2. **`hidden` state**: first-class new state in `svg_style_attrs`, or overload `dim` with `opacity=0`?
3. **Tree value layer** — pick one of three options from Agent 7:
   - (a) `\relabel{T.node[id]}{text}` dedicated command
   - (b) `Tree.emit_svg()` honors `get_value(suffix)` like Array does — consistency win
   - (c) Metadata slot — separate label vs badge in Reingold-Tilford layout
   - **Recommended: (b)** — uniform with Array, minimal API surface addition, unlocks every stateful tree animation.
4. **Tree `apply_command` minimum viable set**: `add_node`, `remove_node`, `reparent`, `set_value`, `set_label`
5. **Graph `apply_command` minimum viable set**: `add_edge`, `remove_edge`, `set_weight`, `set_label`
6. **Index stability on remove**: after `\apply{G}{op=remove_edge, from=8, to=7}`, does edge `[3]` still refer to the same thing? Same question Agent 2 raised for Plane2D remove_point.
7. **Cross-frame tween**: defer to v0.7, or include in v0.6?

**Infrastructure already present**: `graph_layout_stable.py` (per Agent 9 finding) — just needs extending to accept initial-positions dict.

### RFC-2: Strict Mode Wiring

**File:** `docs/rfc/002-strict-mode.md` (~150 lines target)

**Questions to lock:**

1. **`RenderContext.warnings_collector` shape** — list of `(E_code, message, source_line)` tuples? dict keyed by code?
2. **Opt-in vs opt-out**: default `strict=False` backward-compatible; `strict=True` promotes all warnings to errors?
3. **Per-warning opt-out**: `strict_except=["E1462"]` to tolerate polygon auto-close specifically?
4. **Surface destination**: render report dict, stderr, both?
5. **KaTeX error swallowing** (Agent 14 finding #3e/#3f): which path does KaTeX `ParseError` take to reach the collector?
6. **Cleanup list**: 14 silent-fix sites from Agent 4 — which to promote, which to keep?

**Infrastructure already anticipated**: `FrameCountWarning` docstring at `errors.py:397-405` already describes the collector shape — it was designed, never built.

---

## Phase 3 — v0.6.0 Implementation Wave (1-2 weeks)

**Only after RFCs are locked.** Spawn **5 agents in parallel** with worktree isolation (Wave 4A pattern).

### Agent W6.1 — Tree mutation (~400 LoC)

- Implement `Tree.apply_command` with ops from RFC-1
- Warm-start Reingold-Tilford on mutation
- Cross-reference Agent 2 findings for stable index semantics
- Tests: reparent, add_node, remove_node, set_value, set_label
- Honor `get_value(suffix)` in `emit_svg` per RFC-1 option (b)
- Wire `_annotations` dict into emit path (Agent 7 F2)

**File ownership:** `scriba/animation/primitives/tree.py`, `tests/unit/test_tree_mutation.py` (new)

### Agent W6.2 — Graph mutation (~400 LoC)

- Implement `Graph.apply_command` with `add_edge`/`remove_edge`/`set_weight`/`set_label`
- Extend `graph_layout_stable.py` to accept initial-positions dict
- Add `hidden` edge state per RFC-1 (distinct from `dim`)
- Add edge weight rendering (Agent 6 HIGH finding)
- Tests: add/remove/reparent, directed cases, weighted edges

**File ownership:** `scriba/animation/primitives/graph.py`, `scriba/animation/primitives/graph_layout_stable.py`, `tests/unit/test_graph_mutation.py` (new)

### Agent W6.3 — Strict mode infrastructure (~300 LoC)

- Build `RenderContext.warnings_collector` per RFC-2
- Promote 6 DANGEROUS sites from Agent 4:
  - SF-1: polygon auto-close
  - SF-3: off-viewport line silent drop
  - SF-4: log-scale zero clamp
  - SF-6: stable-layout fallback
  - SF-8: stray `\end{animation}` dropped
  - SF-9: substory prelude silent drop
- Wire KaTeX ParseError into collector
- Surface warnings into render report (addition to `Document` dataclass?)

**File ownership:** `scriba/core/context.py`, `scriba/animation/errors.py`, `scriba/animation/scene.py`, `scriba/animation/primitives/plane2d.py`, `scriba/animation/primitives/metricplot.py`, `scriba/tex/*.py` (KaTeX surface)

### Agent W6.4 — Uniqueness checks + red-team fixes (~200 LoC)

- New module `scriba/animation/uniqueness.py` (Agent 14 recommendation)
- Duplicate animation id check → new E1019
- Duplicate shape id check → new E1018
- Shape id charset check → new E1017
- Starlark wall-clock 3s → 1s default
- Cumulative Starlark budget at host side (not just per-block)
- `\def` macro disable in KaTeX (Agent 14 finding #3b, LOW but trivial)

**File ownership:** `scriba/animation/uniqueness.py` (new), `scriba/animation/errors.py`, `scriba/animation/starlark_worker.py`, `scriba/tex/renderer.py`

### Agent W6.5 — Plane2D dynamic ops (~250 LoC)

- Implement `remove_point`, `remove_segment`, `remove_line`, `remove_polygon` per Agent 2 HIGH priority
- Settle index stability per RFC-1 (same decision as Tree/Graph)
- Fix polygon internal state ≠ SVG disagreement (Agent 4 SF-1 root cause)
- Tests: convex hull can actually remove popped points

**File ownership:** `scriba/animation/primitives/plane2d.py`, `tests/unit/test_plane2d_remove.py` (new)

### After merge

- Integration test: all existing cookbook examples still compile
- Tag `v0.6.0-alpha1`, publish RC for manual QA
- Let 1-2 real cookbook authors test before GA

---

## Phase 4 — Cookbook Truth Pass (3-4 days)

**Only after Phase 3 merges.** The mutation API must exist before examples can truthfully use it.

### Truth pass 1: Fix lying examples

- **`h07_splay_amortized.tex`** — rewrite using `Tree.reparent` API. Show actual rotations, not static recolor.
- **`h08_persistent_segtree.tex`** — rewrite using `Tree.set_value`. Sum labels must change across frames.
- **Verify** via grep: `[0,7]=` must contain multiple distinct values across frames, not just one.

### Truth pass 2: Add canonical examples (Agent 12 gaps)

Spawn **4 agents in parallel**, each responsible for 1-2 examples:

| Agent | Examples | Primitives exercised |
|---|---|---|
| W7.1 | Dijkstra + Kruskal | Graph (weights, mutation), Array, Queue |
| W7.2 | BST insert/delete + BFS tree | Tree (mutation), Queue |
| W7.3 | KMP + Binary search | Array (dual view), pointers |
| W7.4 | Union-Find (truthful) + LinkedList reverse | Graph (reparent), LinkedList |

**Target:** cookbook matrix coverage from 42% → ~70% (Agent 12 estimate).

### Truth pass 3: Widget + CSS reconciliation

- Merge orphan `scriba/animation/static/*.css` into `render.py` inline template — single source of truth (Agent 11 W1)
- Add `prefers-reduced-motion` block to shipped CSS (Agent 11 W2)
- Add `aria-label` to Prev/Next buttons (Agent 11 W3)
- **Defer play/autoplay to v0.7** — requires interaction timing design

---

## Phase 5 — v0.6.0 Release

- Quick wins from Phase 1 already shipped as v0.5.2
- Architecture fixes (Phase 3) + cookbook truth (Phase 4) ship as v0.6.0
- Bump `SCRIBA_VERSION: int = 2 → 3` because Tree/Graph contract changed — consumer caches must invalidate
- CHANGELOG entry with breaking changes:
  - Tree/Graph now accept `apply_command` (additive, non-breaking)
  - Strict mode available as `strict=False` default (opt-in, non-breaking)
  - `SCRIBA_VERSION` bump (breaking for cache consumers only)
- Tag `v0.6.0`, push with tags, announce

---

## Why this order is optimal

| Concern | Rationale |
|---|---|
| **Risk management** | Quick wins ship first → validate process + build momentum without risking architectural work |
| **Design quality** | Tree/Graph and strict mode are load-bearing — RFC first prevents throw-away implementations |
| **Cookbook credibility** | Fixing lying examples requires mutation API to exist. Rushing examples without API = more lies |
| **Agent efficiency** | Phase 3 splits 5 agents by file ownership boundary (Tree / Graph / errors / uniqueness / Plane2D) → zero merge conflicts |
| **Cumulative effort** | ~250 LoC (v0.5.2) + ~1500 LoC (v0.6) + cookbook rewrites ≈ 3-4 weeks end-to-end |
| **User experience** | v0.5.2 → v0.6.0 progression is cleaner than one big v0.6.0 release |

---

## Effort estimate

| Phase | Duration | LoC | Agents |
|---|---|---|---|
| 0. Preserve audit | 5 min | 0 | 0 |
| 1. v0.5.2 quick wins | 1-2 days | ~250 | 3 parallel |
| 2. RFCs | 2-3 days | 0 (design) | 0 |
| 3. v0.6.0 implementation | 1-2 weeks | ~1500 | 5 parallel |
| 4. Cookbook truth pass | 3-4 days | ~800 | 4 parallel |
| 5. v0.6.0 release | 1 day | minimal | 0 |
| **Total** | **3-4 weeks** | **~2550** | **12 (across 3 waves)** |

---

## Starting options

### Option (α) — Recommended: ship quick wins first

1. Commit audit reports (Phase 0, 5 min)
2. Spawn 3 Wave 5 agents in parallel for Phase 1 quick wins (~2 hours wall time)
3. After merge, release v0.5.2
4. **Then** write RFCs for Phase 2

**Why α wins:**
- Quick wins have concrete `file_path:line_number`, no thinking needed
- Validates that the 14-agent audit is actually actionable, not just talk
- RFC writing is sharper after practicing the fix process once
- Cleaner user-facing progression (v0.5.2 → v0.6.0) vs one big v0.6.0

### Option (β) — Design-first

1. Commit audit reports
2. Write RFC-1 and RFC-2 immediately (skip quick wins)
3. Spawn Wave 6 with full architectural fixes + quick wins bundled

**Trade-off:** slower to ship first improvement, but only one release to announce. Risk: RFC quality lower because you haven't practiced the fix cycle on easier stuff first.

### Option (γ) — Incremental

1. Commit audit reports
2. Ship fixes one at a time as individual PRs, no wave orchestration
3. Write RFCs inline with implementation

**Trade-off:** slowest overall, but lowest context-switching cost per PR. Good if you want to pause between fixes.

---

## Recommendation

**Start with option (α).** Three Wave 5 agents for quick wins, then RFCs, then Wave 6, then cookbook truth pass. This is the sequence that balances risk, momentum, and architectural quality.

The minimum commitment to see real progress: **Phase 0 + Phase 1** (1-2 days) — ships v0.5.2 with ~10 fixes, validates the audit was actionable, and preserves momentum without any design-level commitment.
