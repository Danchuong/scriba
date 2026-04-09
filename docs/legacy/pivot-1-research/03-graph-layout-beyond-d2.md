# Graph Layout Beyond D2: Complementing Scriba's Renderer Pool

**Status:** Research
**Date:** 2026-04-08
**Scope:** Evaluate graph layout engines to add alongside D2 for cases D2 cannot handle well.

---

## Executive Summary

D2 (Terrastruct) is an excellent default for Scriba: declarative text IR, build-time SVG, clean aesthetics, and strong support for small-to-medium hierarchical graphs and trees. But D2's layout engines (`dagre` for OSS, `ELK` and `TALA` via plugin) are all **Sugiyama-style hierarchical**. They have no force-directed mode, no planarity preservation, no incremental layout, and start to choke past ~100 nodes. Scriba's algorithm catalog (suffix automaton, max-flow residual graphs, planar separators, SCC back-edges) routinely crosses that line.

**Recommendation: add exactly two engines alongside D2.**

1. **Graphviz** (CLI binary, `dot`/`neato`/`fdp`/`sfdp`/`circo`/`twopi`) — the workhorse second tier. Covers force-directed (`sfdp` scales to 10k+ nodes), circular (`circo`), radial (`twopi`), and orthogonal routing. Build-time, subprocess-invoked, same shape as D2 in the pipeline. Handles ~80% of what D2 can't.
2. **ELK.js** (Node.js) — the precision tier for the remaining 20%: compound nested clusters, orthogonal edge routing with hyperedge bundling, layered layout with port constraints, and the only credible option for **incremental layout with position stability** via `org.eclipse.elk.alg.layered.layering.strategy` + pinned coordinates. Runs in-process in Node, no subprocess, no binary.

D2 stays the default. Graphviz handles "big or non-hierarchical." ELK handles "compound, ported, or incremental." Everything else (Cytoscape, G6, Sigma, vis, Dagre, Mermaid, WebCola, ngraph, Gephi Lite) is either runtime-only, interactive-first, or a subset of what these three already provide — rejected below with cause.

---

## Comparison Matrix

Legend: ✅ strong, ⚠️ partial/caveats, ❌ missing or unsuitable.

| Engine | Layouts | SSR / Build-time | Output | Incremental | Compound | Edge routing | License | Size / deps | CLI subprocess |
|---|---|---|---|---|---|---|---|---|---|
| **D2** (current) | Sugiyama (dagre/ELK/TALA) | ✅ Go binary | SVG | ❌ | ✅ | ortho, spline | MPL-2.0 | 1 binary | ✅ |
| **Graphviz** | dot, neato, fdp, sfdp, circo, twopi, osage, patchwork | ✅ C binary | SVG/DOT/JSON | ❌ | ✅ (`subgraph cluster_*`) | ortho, spline, polyline | EPL-1.0 (permissive) | 1 binary | ✅ |
| **ELK.js** | Layered, Force, Stress, MrTree, Radial, Disco, Rectpacking | ✅ pure JS | ELK JSON (→ SVG via renderer) | ⚠️ via fixed positions | ✅ deep nesting, ports | ortho, splines, polyline | EPL-2.0 | ~1.2 MB min, zero runtime deps | ❌ in-process |
| Dagre | Sugiyama only | ✅ pure JS | JSON coords | ❌ | ⚠️ flat clusters | ortho | MIT | ~150 KB | ❌ |
| Mermaid.js | Sugiyama (dagre) | ⚠️ needs headless browser or mermaid-cli | SVG | ❌ | ⚠️ | ortho | MIT | large | ⚠️ via mermaid-cli |
| Cytoscape.js | cose, cola, dagre, klay, breadthfirst, circle, concentric, grid | ⚠️ needs jsdom | Canvas/SVG via ext | ✅ runtime only | ✅ | bezier, taxi, segments | MIT | ~900 KB + layout exts | ❌ |
| ngraph.forcelayout | Force (Barnes-Hut) | ✅ pure JS | coords only | ✅ native | ❌ | ❌ (coords only) | BSD-3 | small | ❌ |
| Sigma.js | Rendering only (layouts via graphology) | ❌ WebGL | WebGL | ✅ via worker | ❌ | straight | MIT | large | ❌ |
| Vis.js Network | Barnes-Hut, hierarchical | ❌ Canvas | Canvas | ✅ | ⚠️ | bezier | Apache-2.0/MIT | large | ❌ |
| Gephi Lite | Exploratory UI | ❌ | interactive | — | — | — | GPL-3 | app | ❌ |
| WebCola | Constraint-based, overlap removal | ✅ pure JS | coords/SVG | ⚠️ | ⚠️ | straight/routed | MIT | ~200 KB | ❌ |
| G6 (AntV) | Dagre, Force, Circular, Concentric, Grid, Radial, Fruchterman | ⚠️ needs canvas-node | Canvas/SVG | ✅ | ✅ | polyline, arc, quad | MIT | ~2 MB | ❌ |

---

## When D2 Is Not Enough — Failure Modes Mapped

**1. Suffix automaton with 200+ states.**
D2 via dagre takes seconds and produces a crossing-riddled mess; TALA is better but proprietary. **Fix: Graphviz `sfdp` + `-Goverlap=prism`.** sfdp is multilevel Barnes-Hut force-directed, designed for 1k–100k node graphs. Cites: `gvpr`/`sfdp` in Graphviz docs, Hu (2005) multilevel algorithm.

**2. Max-flow residual graph, 100+ nodes, back-edges with capacities.**
D2 collapses because Sugiyama doesn't know about reverse edges as a first-class concept. **Fix: Graphviz `neato` or `fdp`** for symmetric layout with edge labels, or ELK `force` when you need stable node placement across animation frames.

**3. Dinic level graph — BFS levels as horizontal bands.**
D2 does this reasonably, but has no port constraints, so edges within a layer jumble. **Fix: ELK `layered` with `org.eclipse.elk.layered.nodePlacement.strategy=NETWORK_SIMPLEX` and port sides pinned.** ELK's `layered` algorithm is the reference Sugiyama implementation with port support; D2 has no port concept at all.

**4. Tarjan SCC DFS stack with low-link back arrows.**
Need a layout that respects DFS discovery order on one axis and lets low-link arrows curve back cleanly. **Fix: Graphviz `dot` with `rank=same` subgraphs per DFS depth** + `constraint=false` on back-edges (documented pattern since Graphviz 2.x).

**5. Treap / splay rotation with stable position morph between frames.**
D2 re-lays out every frame. Node 5 jumps across the page. **Fix: ELK.js with `org.eclipse.elk.interactive=true` and `org.eclipse.elk.position` hints** — you feed previous-frame coordinates back in as soft constraints. Alternatively `ngraph.forcelayout` for pure physics-based incremental, but it produces only coords, no edge routing.

**6. Planar graph with preserved planarity.**
Neither D2 nor ELK guarantees planarity. **Fix: Graphviz has no planar embedder either — use `OGDF`-backed `gml2gv` + `dot`, or accept that for planar demos we hand-author coordinates in Scriba IR and bypass layout entirely.** This is the honest answer: no JS/CLI engine in this list does true planar embedding (Boyer-Myrvold). For Scriba's planar-separator demo we should ship a small hand-written planar embedder or generate coordinates offline with `networkx.planar_layout` (Python, build-time acceptable).

**7. Sparse segment tree incremental allocation.**
Already works in D2 via opacity tricks — **verified** that the same trick works in ELK (render full graph, hide un-allocated nodes by opacity) and Graphviz (same). No change needed.

---

## Recommended Renderer Pool & Selection Rules

```text
default                           → D2         (current, trees ≤ 30 nodes, hierarchical)
layout: force | nodes > 80        → Graphviz sfdp
layout: circular                  → Graphviz circo
layout: radial                    → Graphviz twopi
layout: planar                    → Graphviz dot + rank hints  (or offline networkx)
layout: layered + ports           → ELK layered
layout: compound (nested depth≥2) → ELK layered
animation: true (stable positions)→ ELK interactive mode
```

Selector lives in `scriba-ir` compiler. Each Scriba diagram declares `layout:` hint; compiler dispatches to one of three backends. Default remains D2 so existing content is untouched.

---

## Compile Pipeline Sketch

Scriba already has a subprocess pool for D2. Extend it:

```text
ScribaIR
   │
   ▼
Renderer Dispatcher  ── picks backend by `layout:` field
   │
   ├─► D2 backend       → `d2 - -` subprocess → SVG
   ├─► Graphviz backend → emit DOT → `dot -Tsvg` / `sfdp -Tsvg` subprocess → SVG
   └─► ELK backend      → emit ELK JSON → in-process `elk.layout()` → SVG renderer (elkjs-svg or custom)
```

Key design points:

- **Single shared worker pool** for D2 and Graphviz (both are external binaries, same spawn/timeout/cache logic). Reuse Scriba's existing content-hash cache — keyed by `(backend, version, ir-hash)` so cache invalidates when any binary upgrades.
- **ELK runs in-process** in the Node.js renderer worker. No subprocess, but it does block the event loop for ~100ms on medium graphs — put it behind the same worker pool using Node `worker_threads`.
- **SVG normalization pass** (already exists for D2) applies to all three backends so font-size, colors, and CSS classes are uniform. Graphviz SVG is notoriously noisy (inline styles, weird font refs) — normalization strips and rewrites via a small post-processor.
- **Backend version pinned** in `scriba.config.ts`: `{ d2: "0.6.x", graphviz: "12.x", elkjs: "0.9.x" }`. Version becomes part of cache key.

---

## Risks

1. **License.** Graphviz is EPL-1.0 (weak copyleft, binary-only use is fine). ELK.js is EPL-2.0 (same story, we import as a library — no source contamination as long as we don't modify ELK itself). Both compatible with Scriba shipping under MIT.
2. **Binary distribution.** Graphviz must be present on the build host. CI needs `apt-get install graphviz` or equivalent; local dev needs `brew install graphviz`. Already true for many users but worth a preflight check in Scriba CLI.
3. **Output format drift.** Graphviz SVG font metrics don't match D2's. Normalization pass must re-measure text or force a shared font stack. Plan: inject a single `--scriba-font` family via CSS class and strip all inline font attributes.
4. **ELK bundle size.** `elkjs` is ~1.2 MB minified. Only loaded by the compile pipeline, never shipped to browsers, so user-facing bundle stays zero-impact.
5. **Maintenance surface.** Three renderers = three upgrade paths. Mitigated by content-hash cache (upgrades don't break old diagrams) and backend-agnostic IR (no backend leaks into author content).
6. **No true planar embedding** in any of the three. Accept this; provide `layout: planar` as a hand-coordinate escape hatch.

---

## Implementation Tasks

1. **Abstract renderer interface.** Extract current D2 invocation behind `RendererBackend { name; render(ir): Promise<SVG> }`. Port D2 to it first, no behavior change. Add content-hash cache keyed on `(backend, version, ir)`.
2. **Graphviz backend.** IR → DOT emitter covering `layout: force|circular|radial|planar`. Subprocess wrapper mirroring D2's. SVG normalizer (strip inline fonts, unify stroke, add Scriba CSS classes). Preflight check for `dot` / `sfdp` on PATH.
3. **ELK backend.** IR → ELK JSON emitter covering `layout: layered|compound` and `animation: true` (position-stable mode). Use `elkjs` via `worker_threads`. Write minimal ELK-JSON → SVG renderer (or adopt `elkjs-svg` if license permits — check before importing).
4. **Dispatcher + IR extension.** Add `layout:` and `animation:` fields to Scriba IR schema. Implement selection rules from above. Fallback to D2 with a build warning when a backend is unavailable.
5. **Golden tests.** Add fixture diagrams for each failure mode (suffix automaton 200 states, Dinic 4 layers with ports, treap rotation with stable positions, max-flow residual) and snapshot SVG outputs. Run across all three backends in CI.

---

## Rejected Alternatives, Briefly

- **Mermaid.js** — same Sugiyama-only ceiling as Dagre, requires headless browser for SSR. No gain over D2.
- **Cytoscape.js / vis / Sigma / G6** — runtime-first interactive libraries. Needing jsdom or canvas-node at build time is fragile; none offer build-time SVG as a first-class output. Good for a future "interactive mode" but not for Scriba's static compile pipeline.
- **Dagre** — already inside D2.
- **ngraph.forcelayout** — produces coordinates only, no edge routing. Graphviz `sfdp` subsumes it.
- **WebCola** — constraint solver is elegant but slower than ELK for the same shapes, and the project is effectively unmaintained since 2020.
- **Gephi Lite** — exploratory GUI, not a library.

---

## References

- D2 docs: https://d2lang.com/tour/layouts
- Graphviz: https://graphviz.org/docs/layouts/ (sfdp: Hu 2005, "Efficient and high quality force-directed graph drawing")
- ELK: https://www.eclipse.org/elk/reference/algorithms.html
- ELK.js: https://github.com/kieler/elkjs
- Sugiyama layered algorithm reference implementation: ELK `layered`
- Boyer-Myrvold planarity: not available in any JS/CLI engine surveyed — mitigation documented above.
