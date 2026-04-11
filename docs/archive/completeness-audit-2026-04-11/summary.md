# Scriba Completeness Audit — Summary
**Date:** 2026-04-11
**Scope:** Post-v0.5.1 completeness/polish audit (14 parallel agents)
**Prior audit:** `docs/archive/production-audit-2026-04-11/` (21 agents, correctness/security)
**Trigger:** Convex hull cookbook session surfaced API inconsistency, silent auto-fix, warning noise, and manual loop unroll tedium — suggesting structural gaps outside the prior correctness scope.

---

## TL;DR

Scriba v0.5.1 is **correct and secure** (prior audit confirmed) but **structurally incomplete** for its own stated use case. Two findings rise to **CRITICAL**:

1. **Tree and Graph primitives have zero dynamic mutation API.** Topology and node values are frozen at `\shape` time. Every cookbook example that claims to animate tree/graph evolution is an illusion — `h07_splay_amortized.tex` never rotates, `h08_persistent_segtree.tex` has static sum labels that narration contradicts. This blocks ~60% of CP editorial use cases (rotations, rebalancing, BFS/DFS growth, MST progression, union-find, segment tree updates).

2. **Silent auto-fix pervasive, strict mode unwired.** 14 silent-fix sites across the codebase. Half of the E1460-1509 catalog block is aspirational ("contract for when strict mode is wired"). Polygon auto-close is doubly broken: internal state disagrees with SVG render. Authors can't distinguish "my intent worked" from "Scriba silently rewrote my intent."

Beyond the two criticals, the audit found **52 additional findings** across 14 reports, with **3 HIGH-severity single-line fixes** that would immediately eliminate the entire `stk`/`pq` warning class, a Queue dequeue bug, and unlock currently-dead LinkedList syntax.

Score shift from prior audit (6.5/10 correctness) now drops a notch on the **feature completeness axis** (~5.5/10). Correctness and security remain solid; the gap is in what Scriba can honestly represent.

---

## Agent roster and severity

| # | Agent | Findings | Top severity |
|---|---|---|---|
| 01 | API consistency | 3 BREAKING, 4 CONFUSING, 3 COSMETIC | HIGH |
| 02 | Dynamic-op gaps | 5/11 primitives have no `apply_command` | HIGH |
| 03 | Emitter warnings | 35 logging sites; 10 BUG, 6 NOISE | HIGH |
| 04 | Silent auto-fix | 14 sites, 6 DANGEROUS | CRITICAL |
| 05 | Error hints | 1/70 raise sites has fuzzy hint | HIGH |
| 06 | Dijkstra sim | 12 friction points | HIGH |
| 07 | SegTree sim | Tree value layer missing | **CRITICAL** |
| 08 | Quicksort sim | No swap/pointer primitive | HIGH |
| 09 | Union-Find sim | Topology frozen at shape-time | **CRITICAL** |
| 10 | KMP sim | No cross-primitive arrows | MEDIUM |
| 11 | Widget QA | Two parallel CSS truths; no play/autoplay | HIGH |
| 12 | Cookbook matrix | 42% coverage; 3 primitives zero-coverage | MEDIUM |
| 13 | Onboarding | 45-90 min realistic time-to-first-render | HIGH |
| 14 | Red-team | 0 crashes; 3 HIGH silent-accept bugs | HIGH |

Total: **2 CRITICAL, 9 HIGH, 4 MEDIUM, 0 LOW-only reports**. No crashes, no security regressions, no sandbox escapes.

---

## Critical finding cluster: "The Static Primitive Problem"

Agents 2, 6, 7, 8, 9 independently discovered the same root cause at different levels of the stack:

- **Agent 2** (static analysis): Only 6/11 primitives implement `apply_command`. Array, NumberLine, Grid, Tree, Graph have no structural mutation surface at all. `PrimitiveBase.set_label()` exists but is never called — parse stores into `ShapeTargetState.label`, emitter never reads it. **Dead API.**

- **Agent 6** (Dijkstra sim): No `PriorityQueue` primitive (had to fake with Queue). Graph has no edge weights. `Array.labels="A,B,C,..."` silent-drops to numeric.

- **Agent 7** (SegTree sim): **CRITICAL**. `Tree{kind="segtree", show_sum=true}` bakes sums into `node_labels` at init (`tree.py:365-370`). `emit_svg` reads only the static dict (line 514). No DSL command to change a node's label/value post-init. **Every stateful tree animation currently lies in its narration.** Confirmed empirically with a probe: `\annotate` on Tree is a silent no-op. `h08_persistent_segtree.tex` has the same latent bug.

- **Agent 8** (Quicksort sim): Array has no `\swap`. No pointer primitive. Two-pointer algorithms express meaning in narration, not in the SVG.

- **Agent 9** (Union-Find sim): **CRITICAL**. `scene.py::apply_prelude` registers shapes exactly once. Tree and Graph cannot re-parent. `h07_splay_amortized.tex` "animates splay" by **never actually rotating anything** — just recolors a static 7-node tree. Graph workaround for union-find required pre-declaring the entire superset of parent pointers across the whole animation, all initially dimmed.

**Impact table** (algorithms Scriba cannot honestly represent today):

| Category | Blocked algorithms |
|---|---|
| Tree rotations | Splay, AVL, Red-Black, Treap |
| Tree structure | BST insert/delete, B-tree split/merge |
| Segment tree | Lazy propagation, point update (values change) |
| Graph growth | BFS/DFS tree construction, topological sort |
| Graph mutation | MST (Kruskal/Prim progression), Union-Find path compression |
| Incremental graph | Bridge-finding, SCC, cycle detection |
| Array ops | Sort algorithms (all — no swap), partition, rotation |

**Fix shape:** Universal `apply_command` contract across Array/Tree/Graph with:
- `add_node`, `remove_node`, `reparent` (Tree/Graph)
- `add_edge`, `remove_edge` (Graph)
- `set_value`, `set_label` (all — wire the dead API)
- `swap` (Array)

Each primitive's existing layout algorithm already assumes it re-runs per-frame, so the infrastructure is there; just the mutation surface is missing.

---

## Critical finding cluster: "Silent auto-fix / strict mode unwired"

Agent 4 found **14 silent-fix sites, 6 classified DANGEROUS**:

- **SF-1** (Plane2D polygon auto-close): Internal `polygons[i].points` list is left open while SVG `<polygon>` element closes natively. Internal state disagrees with render. Off-by-one on future polygon-vertex selectors.
- **SF-3** (degenerate/off-viewport line E1461): Silent drop + silent `continue` shift subsequent `line[i]` indices.
- **SF-4** (log-scale zero clamp E1484): `val = 1e-9` substitution falsifies plots.
- **SF-6** (stable-layout fallback E1501-1503): Author explicitly requested stability, silently downgraded.
- **SF-8** (stray `\end{animation}` dropped): Asymmetric with `UnclosedAnimationError` which DOES raise.
- **SF-9** (substory prelude silent drop): `\highlight`/`\apply`/`\recolor` inside `\substory` before first `\step` silently discarded. Contrast top-level prelude which raises E1053.

**Root cause:** The `errors.py:397-405` `FrameCountWarning` docstring anticipates a `warnings_collector` on `RenderContext`. It was never built. Half the E1460-1509 block is documented "contract for when strict mode is wired" but strict mode is not wired.

**Fix shape:** Build `RenderContext.warnings_collector` → promote SF-1/3/4/6/8/9 to strict `AnimationError` with `strict=False` opt-out → surface collected warnings in the render report so authors can see what happened without tailing logs.

Cross-reference from Agent 14 (red-team): confirmed that KaTeX `\def\x{\x\x}\x` macro bomb raises `ParseError: Too many expansions` but Scriba swallows it — CLI reports "Rendered 1 block(s)" and exits 0. Same silent-accept class. Needs the same warnings_collector surface.

---

## One-line and small-diff HIGH-severity fixes

These are quick wins that agents identified as unblocking multiple findings simultaneously:

| Fix | Location | LoC | Unblocks |
|---|---|---|---|
| Skip guard for bare-shape in selector validator | `emitter.py:330` | 1 | `stk` + `pq` warnings (Agents 3, 6) |
| `dequeue=false` truthiness check | `queue.py:141` | 1 | Silent Queue bug (Agent 1) |
| Bare-token fallthrough in `_read_param_brace` | `grammar.py:1449` | ~15 | `pop`/`dequeue` bare tokens, E1012 trigger (Agent 1) |
| `LBRACE` branch in `_parse_param_value` | `grammar.py:1472-1513` | ~20 | LinkedList `insert={dict}` now unreachable (Agent 1) |
| Hoist `_fuzzy_suggest` to errors.py + 4 call sites | `errors.py` + `grammar.py` | ~30 | 4 HIGH E-codes get "did you mean" (Agent 5) |
| E1114 unknown shape kwarg | `primitives/base.py` `__init__` | ~20 | Plane2D `xranges` silent-drop (Agent 5, Agent 6) |
| Unique-id check for animations | new `uniqueness.py` | ~40 | Duplicate id DOM collision (Agent 14) |
| Unique-id check for shapes | same | ~20 | `\shape{a}{Array}{size=3}` override silent (Agent 14) |
| Starlark wall-clock 3s → 1s + cumulative budget | `starlark_worker.py:402` | ~10 | 1M-cell comprehension at edge (Agent 14) |
| Unicode NFC normalize on identifiers | `parser/selectors.py:260` | ~5 | NFD vs NFC asymmetry (Agent 14) |

**Total LoC for all quick wins: ~162.** Would eliminate ~95% of the emitter log spam (Agent 3 estimate) and close 10 of the 52 non-critical findings immediately.

---

## Non-functional findings

### UX / Widget (Agent 11)
- **W1 MEDIUM**: `scriba/animation/static/*.css` (593 lines of focus rings, reduced-motion, print, dark-mode tokens) is **orphan**. Cookbook render path uses `render.py`'s inline `HTML_TEMPLATE` instead. Two parallel CSS truths. Fix: reconcile.
- **W2 MEDIUM**: Shipped inline CSS has no `prefers-reduced-motion` block. Unconditional `.scriba-stage svg, .scriba-narration { transition: opacity .2s ease; }`. Reduced-motion users still see fades.
- **Play / Pause / autoplay do not exist** despite prior assumption. Only Prev/Next manual stepping. No scrubbable progress bar. No Home/End keyboard. No aria-label on nav buttons.

### Cookbook coverage (Agent 12)
- 13 files, 1182 lines, 114 steps, 42% matrix coverage.
- **3 primitives have zero cookbook examples**: Queue, HashMap, LinkedList.
- **4 topics entirely missing**: Sort, Binary search, BFS/DFS, String algorithms.
- Heavy skew to Array + DP + Tree. 10 prioritized new examples proposed that would lift coverage to ~70%.

### Onboarding (Agent 13)
- README hello world pushes `Pipeline + RenderContext + SubprocessWorkerPool` at CP authors instead of `render.py --open`.
- No README links to: tutorial, cookbook, error codes doc, CLI.
- 3 stale TODOs at v0.5.1 release (mirror URL in README, clone URL in CONTRIBUTING, "NotImplementedError until later phases land" in `examples/minimal.py`).
- `examples/cookbook/` has no README/INDEX — 30 flat files no difficulty tags.
- Time-to-first-render: 10 min best, 45-90 min realistic, 2-4 hr worst.
- **Quick wins <2 hours total**: README "Quickstart for authors" section, cookbook README, fix 3 stale TODOs.

### Security / adversarial (Agent 14)
**Good news first**: no crashes, no hangs, no sandbox escape, no XSS (double-escaped), dangerous URIs render as plain text. Frame/foreach/annotation caps all fire cleanly. 10 KB identifiers, 50 shapes, 100 KB narrate, 40-level nested `\text{}`, nested closures, recursive functions all accepted without incident.

**Bad news**: 3 HIGH-severity **silent-accept** bugs (not crashes):
1. **Duplicate animation id** — two `\begin{animation}[id="dup"]` both emit `<div id="dup">`. Second widget's JS attaches to first widget's DOM.
2. **Duplicate shape id** — `\shape{a}{Array}{size=3}` then `\shape{a}{Array}{size=5}` silently overrides.
3. **Starlark 1M-cell comprehension** completes in ~3.1s, right at the 3s wall-clock edge. Per-block isolation good; cumulative .tex-file budget not enforced.

Plus 4 MEDIUM and 4 LOW — all silent-accepts, all would be caught by the strict-mode work from Agent 4's cluster.

---

## Proposed Wave 5 fix plan

Based on all 14 reports, proposed priorities for a hypothetical v0.6 release:

### P0 — Blockers (must-fix for v0.6 to be honestly usable for CP editorials)

1. **Tree.apply_command with add_node / remove_node / reparent / set_value / set_label**
   *Effort:* moderate (needs stable node-ID story, layout re-run per frame)
   *Unblocks:* Agents 7, 9; h07/h08 cookbook truthfulness

2. **Graph.apply_command with add_edge / remove_edge / set_weight / set_label**
   *Effort:* moderate (similar to Tree)
   *Unblocks:* Agents 6, 9; Dijkstra, Kruskal, Prim, union-find cookbooks

3. **Strict mode wiring — RenderContext.warnings_collector + surface in report**
   *Effort:* small to moderate
   *Unblocks:* Agent 4 entire cluster + Agent 14 silent-accept bugs + KaTeX error swallowing

4. **Universal uniqueness check for animation-id and shape-id**
   *Effort:* trivial (~60 LoC new module)
   *Unblocks:* Agent 14 HIGH findings

### P1 — Quick HIGH-severity wins (~162 LoC total)

5. **Emitter selector validator fix** — 1 line eliminates `stk`/`pq` warning class
6. **Queue dequeue=false bug** — 1 line
7. **Parser bare-token fallthrough** — ~15 LoC; enables `\apply{stk}{pop}` naturally
8. **Parser dict-literal branch** — ~20 LoC; unlocks LinkedList `insert={dict}`
9. **E1114 unknown shape kwarg** — ~20 LoC
10. **Fuzzy hints for E1004/E1006/E1109/E1112** — ~30 LoC
11. **Unicode NFC normalize on identifiers** — ~5 LoC

### P2 — Systemic cleanup

12. **Reconcile orphan CSS** (`static/*.css` vs `render.py` inline template) — single source of truth
13. **Add `prefers-reduced-motion` support** to shipped CSS
14. **`PrimitiveBase.ACCEPTED_PARAMS` frozenset** for kwarg validation (opt-in, per-primitive)
15. **Demote 6 NOISE / 6 DEBUG logging sites** in emitter/scene
16. **Promote 10 BUG sites** to proper E-codes

### P3 — Polish (defer to v0.7)

17. **New primitives**: PriorityQueue, pointer annotations, inline `\compare`, `\swap`
18. **Cookbook additions**: 10 prioritized examples (BFS, Dijkstra, Kruskal, KMP, mergesort, BST, sieve, binary search, union-find, LinkedList reverse)
19. **README restructure**: "Quickstart for authors" section, cookbook README, fix 3 stale TODOs, add CLI doc
20. **Widget hardening**: play/pause, scrubbable progress, aria-labels, keyboard Home/End
21. **Playwright dev dependency** for real-browser widget tests

### Deferred / out of scope

- Cross-browser matrix testing (Agent 11 scoped but Playwright not installed)
- i18n / RTL label support (only LOW priority from Agent 14)
- Performance benchmarks at 500/1000 frames (Wave 4B already handled recursion DoS)

---

## Comparison with prior audit

| Axis | Prior (21 agents) | This (14 agents) |
|---|---|---|
| Correctness | 6.5/10 → 9/10 after Wave 1-4B | Unchanged |
| Security | 7/10 → 9/10 after Wave 1-4B | Unchanged + Agent 14 confirms no regressions |
| **Feature completeness** | Not scored | **5.5/10** (Static Primitive Problem) |
| **Author ergonomics** | Not scored | **6/10** (API consistency, silent fixes, warnings) |
| **UX / onboarding** | Not scored | **6/10** (orphan CSS, README, missing CLI docs) |
| **Cookbook coverage** | Not scored | **4.2/10** (42% matrix coverage) |

The prior 21-agent audit was almost entirely a **static analysis** pass — grammar formalism, error catalog, supply chain, parser fuzz, sandbox red-team. It was thorough for what it was, but it never asked: **"can an author actually build a real CP editorial with this tool?"** That question is what the 5 author-simulation agents (6/7/8/9/10) in this audit answered, and the answer is **partially** — current primitives are great for coloring and highlighting, weak for evolution.

---

## Recommendation

**Do NOT rush a v0.5.2 patch**. The critical findings (Tree/Graph mutation, strict mode) are architectural and need design work. The quick wins (~162 LoC) are worth a v0.5.2 but should be grouped with their design-level companions.

**Suggested roadmap:**

- **v0.5.2** (quick wins only): Items P1.5-P1.11 + P2.15-P2.16 (~250 LoC, 1-2 weeks)
- **v0.6.0** (completeness wave): Items P0.1-P0.4 + P2.12-P2.14 + P3.19 (~1500 LoC + design docs, 4-6 weeks)
- **v0.7.0** (polish wave): Items P3.17-P3.21 (new primitives, widget, Playwright)

Before spawning Wave 5 fix agents, recommend:
1. Read all 14 individual reports (they have concrete file:line citations)
2. Write design RFCs for P0.1 (Tree mutation) and P0.2 (Graph mutation) — these need human decisions about stable node IDs, layout re-run semantics, `hidden` vs `dim` state, cross-frame tweening
3. Then spawn implementation agents in waves similar to prior 4A/4B pattern

---

**All 14 reports deliverable at:** `docs/archive/completeness-audit-2026-04-11/0N-slug.md`
**Generator transcripts archived for follow-up:** agent IDs recorded in individual report footers
**Adversarial test artifacts:** `/tmp/completeness_audit/*.{tex,html,log}` (5 author sims + 14 red-team inputs) — not committed, available for reference until /tmp is cleared.
