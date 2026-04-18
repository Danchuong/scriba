# RFC-001 — Tree / Graph / Plane2D Mutation API

| | |
|---|---|
| **Status** | Accepted — **design only; not yet implemented** |
| **Author** | Wave 5 orchestration (research grounded in `scriba` v0.5.2 @ `90d1527`) |
| **Date** | 2026-04-11 |
| **Target release** | v0.6.0 |
| **Phase** | Completeness audit — Phase 2 (design) |
| **Unblocks** | W6.1 Tree mutation, W6.2 Graph mutation, W6.5 Plane2D dynamic ops |
| **Supersedes** | — |
| **Audit references** | `docs/archive/completeness-audit-2026-04-11/{02,06,07,09}-*.md` |

## 1. Motivation

The completeness audit found that **8 of 11 primitives have no structural `add`** and **10 of 11 have no real `remove`** (Agent 2, §Coverage matrix). As a direct consequence:

- `h07_splay_amortized.tex` and `h08_persistent_segtree.tex` in the cookbook **lie** — narration claims values/labels change across frames, but Tree's value layer is frozen at `\shape` construction time (Agent 7, F1 CRITICAL).
- `h06_li_chao.tex` and `convex_hull_andrew.tex` fake deletion using `\recolor{...}{state=dim}`, which is pedagogically misleading — the algorithm deletes a point, the visual pretends it didn't (Agent 2, §HIGH-1).
- Dijkstra, Prim, Kruskal, Bellman-Ford, Floyd-Warshall cannot be faithfully animated because Graph has no edge mutation and no weighted edges (Agent 6, §F4 HIGH).
- Union-Find, BST insert/delete, BFS tree construction require `Tree.reparent` (Agent 9, §FR1).

This RFC locks the design decisions for the Phase 3 implementation wave (W6.1, W6.2, W6.5).

## 2. Non-goals

- **Cross-frame tween / endpoint interpolation** — deferred to v0.7 (see §7).
- **Graph node mutation** (`add_node`/`remove_node` on Graph) — deferred to v0.7. v0.6 covers edges only, per Agent 2 finding 2 HIGH-3 ("nodes are fixed at layout time, edges alone are tractable").
- **Tree `apply_command` with `op=` string dispatch** — rejected in favor of kwarg-keyed dispatch matching `Plane2D.apply_command` precedent at `primitives/plane2d.py:285-302`.
- **Plane2D stable-ID rewrite** — indices remain positional, with tombstone-in-place semantics (see §5, Q6).

## 3. Summary of locked decisions

| # | Question | Decision |
|---|---|---|
| Q1 | Layout stability across mutations | Tree: recompute Reingold-Tilford every frame (deterministic — `tree.py:108-234`). Graph: route mutation through `compute_stable_layout` with a new `initial_positions` kwarg |
| Q2 | `hidden` state: first-class or overloaded? | **First-class** — add `"hidden"` to `VALID_STATES` (`constants.py:16-18`) |
| Q3 | Tree value layer | Tree `emit_svg` honors `get_value(suffix)` — `tree.py:514` override path. Pre-answered by FIX_PLAN option (b) |
| Q4 | Tree `apply_command` operation set | `add_node`, `remove_node` (error on non-leaf unless `cascade=true`), `reparent` |
| Q5 | Graph `apply_command` operation set | `add_edge(weight)`, `remove_edge`, `set_weight`; node mutation deferred. Add `show_weights` flag and 3-tuple edge syntax |
| Q6 | Index / ID stability on `remove_*` | Tree/Graph already stable by id (node labels ARE the keys). Plane2D = tombstone-in-place |
| Q7 | Cross-frame tween | Defer to v0.7 |

## 4. API specification

### 4.1 Tree

```latex
% Structural mutation
\apply{T}{add_node={id="X", parent="Y"}}
\apply{T}{remove_node="X"}                  % error E14xx if X has children
\apply{T}{remove_node={id="X", cascade=true}}
\apply{T}{reparent={node="X", parent="Y"}}

% Value / label layer — already reachable via the existing \apply-with-suffix path
\apply{T.node["X"]}{value="42"}             % wired through set_value (W5.2 set_label delivered the parallel path)
\apply{T.node["X"]}{label="dirty"}          % wired through set_label
```

Python interface (`primitives/tree.py`):

```python
def apply_command(self, params: dict[str, Any]) -> None:
    if "add_node" in params:
        spec = params["add_node"]                 # dict {"id", "parent"}
        self._add_node_internal(spec["id"], spec["parent"])
        return
    if "remove_node" in params:
        spec = params["remove_node"]
        if isinstance(spec, (str, int)):
            self._remove_node_internal(spec, cascade=False)
        else:
            self._remove_node_internal(spec["id"], cascade=spec.get("cascade", False))
        return
    if "reparent" in params:
        spec = params["reparent"]
        self._reparent_internal(spec["node"], spec["parent"])
        return
```

Each internal mutation updates `self.nodes`, `self.edges`, `self.children_map`, `self.node_labels`, then re-runs `reingold_tilford(self.root, self.children_map, width=self.width, height=self.height)`. Deterministic — same tree shape → same positions. No warm-start bookkeeping required.

Value layer wire-up in `Tree.emit_svg` (`tree.py:514`):

```python
# Current: display_label = self.node_labels.get(node_id, str(node_id))
override = self.get_value(self._node_key(node_id))
display_label = override if override is not None else self.node_labels.get(node_id, str(node_id))
```

Errors:
- `E1433` — `remove_node` on a non-leaf without `cascade=true`. Hint: `"pass cascade=true to drop descendants, or \\apply{T}{reparent=...} them first"`.
- `E1434` — `remove_node` on the root with `cascade=false`. (Root removal without cascade is structurally meaningless.)
- `E1435` — `reparent` creates a cycle. Cycle check uses ancestor walk in `children_map`.
- `E1436` — `add_node` where `parent` does not exist.

### 4.2 Graph

```latex
% Weighted-edge construction (new 3-tuple form)
\shape{G}{Graph}{
  nodes=["A","B","C"],
  edges=[("A","B",4), ("A","C",2), ("B","C",1)],  % 3-tuple = weighted
  directed=false,
  show_weights=true,
}

% Structural mutation
\apply{G}{add_edge={from="A", to="D", weight=5}}
\apply{G}{remove_edge={from="A", to="B"}}
\apply{G}{set_weight={from="A", to="B", value=7}}
```

Python interface (`primitives/graph.py`):

```python
def apply_command(self, params: dict[str, Any]) -> None:
    if "add_edge" in params:
        spec = params["add_edge"]
        self._add_edge_internal(spec["from"], spec["to"], spec.get("weight"))
        return
    if "remove_edge" in params:
        spec = params["remove_edge"]
        self._remove_edge_internal(spec["from"], spec["to"])
        return
    if "set_weight" in params:
        spec = params["set_weight"]
        self._set_weight_internal(spec["from"], spec["to"], spec["value"])
        return
```

Edge storage changes from `list[tuple[str|int, str|int]]` to `list[tuple[str|int, str|int, float|None]]` with a migration helper in `__init__` that accepts both 2-tuples (weight=None) and 3-tuples.

`show_weights` gates an extra `<text>` per edge at midpoint in `Graph.emit_svg` (`graph.py:364-395`). Typography uses `THEME["fg_muted"]` with `text-anchor="middle"`.

Layout stability — when `apply_command` mutates edges, Graph re-runs layout via a new code path:

```python
def _relayout_with_warm_start(self) -> None:
    from scriba.animation.primitives.graph_layout_stable import compute_stable_layout
    result = compute_stable_layout(
        [str(n) for n in self.nodes],
        [[(str(u), str(v)) for u, v, _w in self.edges]],  # single-frame edge set
        seed=self.layout_seed,
        initial_positions={str(n): self.positions[n] for n in self.nodes},  # NEW kwarg
        width=self.width,
        height=self.height,
        node_radius=self._node_radius,
    )
    if result is not None:
        self.positions = {n: (round(result[str(n)][0]), round(result[str(n)][1])) for n in self.nodes}
    # else: fall back to current force layout (stable_layout returned None for size guards)
```

`graph_layout_stable.compute_stable_layout` gains a new kwarg:

```python
def compute_stable_layout(
    nodes: list[str],
    frame_edge_sets: list[list[tuple[str, str]]],
    seed: int = 42,
    lambda_weight: float = 0.3,
    width: int = 400,
    height: int = 300,
    node_radius: int = 16,
    initial_positions: dict[str, tuple[float, float]] | None = None,  # NEW
) -> dict[str, tuple[float, float]] | None:
    ...
    if initial_positions is not None:
        # Normalize SVG coordinates back to [0,1] for SA
        positions = {
            node: (
                (initial_positions[node][0] - pad) / max(width - 2 * pad, 1),
                (initial_positions[node][1] - pad) / max(height - 2 * pad, 1),
            )
            for node in nodes
        }
    else:
        positions = {node: (rng.random(), rng.random()) for node in nodes}
```

Cache key (`compute_cache_key`) does **not** consider `initial_positions` — the SA output is deterministic from the edge set + seed. Warm-start accelerates convergence but the fixed-point is the same.

Errors:
- `E1471` — `add_edge` where `from` or `to` is not in `nodes`.
- `E1472` — `remove_edge` where the edge does not exist.
- `E1473` — `set_weight` on a non-existent edge.
- `E1474` — weighted/unweighted mix in `edges` list (some 2-tuples, some 3-tuples).

### 4.3 Plane2D — tombstone semantics for existing `remove_*`

The existing `apply_command` in `plane2d.py:285-302` is add-only. W6.5 adds the complementary removes:

```latex
\apply{P}{remove_point=2}          % tombstones points[2]
\apply{P}{remove_segment=0}
\apply{P}{remove_line=1}
\apply{P}{remove_polygon=0}
```

Internal change — replace the slot with a sentinel, do **not** reindex:

```python
_TOMBSTONE = object()

def _remove_point_internal(self, idx: int) -> None:
    if 0 <= idx < len(self.points) and self.points[idx] is not _TOMBSTONE:
        self.points[idx] = _TOMBSTONE
    else:
        raise animation_error("E1437", f"Plane2D '{self.name}' has no point[{idx}]")
```

`addressable_parts` skips tombstones; `validate_selector` returns False for tombstoned indices; `emit_svg` point loop skips them. Later-frame selectors like `P.point[5]` remain valid as long as `points[5]` was not the one tombstoned.

**Cost of tombstones accumulating**: bounded by number of remove operations per render; a future `\apply{P}{compact=true}` can reclaim space but is out of scope for v0.6.

### 4.4 `hidden` state (cross-cutting)

`scriba/animation/constants.py:16-18`:

```python
VALID_STATES = frozenset({
    "idle", "current", "done", "dim", "error", "good", "highlight", "path",
    "hidden",  # NEW — element is not rendered at all
})
```

`scriba/animation/primitives/base.py:48-57` — `STATE_COLORS` gets no new entry; callers must special-case the key. A helper:

```python
def is_hidden(state_name: str) -> bool:
    return state_name == "hidden"
```

Each primitive's `emit_svg` adds an early-return in the per-part loop:

```python
# tree.py, inside the node loop at ~line 506
state = self.get_state(self._node_key(node_id))
if state == "hidden":
    continue
```

Bounding box behavior: `hidden` elements **still contribute** to the primitive's bounding box. This keeps visual layout stable across a `hidden` toggle (no viewport jumps). A future `strict_hidden` option could exclude them from the bbox, but it is out of scope for v0.6.

## 5. Answers to the seven FIX_PLAN questions

**Q1 — Stable node IDs / warm-start** → Tree is deterministic by `children_map`; no warm-start needed. Graph warm-starts via `compute_stable_layout(initial_positions=...)` — see §4.2.

**Q2 — `hidden` state** → First-class. See §4.4.

**Q3 — Tree value layer** → Option (b): `Tree.emit_svg` reads `get_value(suffix)` with fallback to `self.node_labels`. See §4.1.

**Q4 — Tree minimum viable set** → `add_node`, `remove_node` (error on non-leaf unless `cascade=true`), `reparent`. Value/label layer is reachable via the existing `\apply{T.node[X]}{value=...}` path (W5.2 already wired set_label through the emitter, set_value uses the same mechanism).

**Q5 — Graph minimum viable set** → `add_edge` (with weight), `remove_edge`, `set_weight`. Plus `show_weights: bool = False` constructor flag and 3-tuple edge syntax. Node mutation deferred to v0.7.

**Q6 — Index stability on remove** → Tree and Graph are already ID-stable (`tree.py:417` uses `node[{id}]`, `graph.py:297` same). Plane2D uses positional `point[{i}]` and therefore needs tombstone-in-place. See §4.3.

**Q7 — Cross-frame tween** → Defer to v0.7. v0.6 snaps positions; pedagogically acceptable for a first cut.

## 6. Implementation roadmap

| Agent | File ownership | LoC estimate | Key tests |
|---|---|---|---|
| **W6.1 Tree mutation** | `primitives/tree.py`, `tests/unit/test_tree_mutation.py` (new) | ~400 | `add_node`, `remove_node` (leaf + cascade), `reparent`, value-layer override, `hidden` state skip |
| **W6.2 Graph mutation** | `primitives/graph.py`, `primitives/graph_layout_stable.py`, `tests/unit/test_graph_mutation.py` (new) | ~400 | `add_edge` w/ weight, `remove_edge`, `set_weight`, warm-start via `initial_positions`, `show_weights` rendering, 3-tuple edge parsing |
| **W6.5 Plane2D dynamic ops** | `primitives/plane2d.py`, `tests/unit/test_plane2d_remove.py` (new) | ~250 | Tombstone-in-place for 4 remove ops, `validate_selector` rejects tombstones, selector stability across removes, `hidden` state skip |
| **Cross-cutting** | `constants.py` (+1 state), `base.py` (+is_hidden helper) | ~15 | `hidden` state validation, backward compat for existing primitives |

No file overlap between W6.1, W6.2, W6.5 → they run in parallel worktrees following the Wave 5 pattern.

## 7. Deferred to v0.7

| Feature | Blocking? | Notes |
|---|---|---|
| Graph `add_node` / `remove_node` | No | Edge mutation covers the documented algorithms |
| Plane2D `compact=true` | No | Tombstones are bounded by explicit remove count per scene |
| Cross-frame endpoint tween | No | Snap-to-position is the v0.6 behavior |
| `T.subtree[id]` selector | No | Agent 7 F5 — authors can enumerate for now |
| `strict_hidden` bbox exclusion | No | Default behavior (bbox includes hidden) is safer for v0.6 |

## 8. SCRIBA_VERSION impact

The `Document` dataclass shape (`html`, `required_css`, `required_js`, `versions`, `block_data`, `required_assets`) is unchanged. However, **consumer caches keyed on primitive rendered output SHOULD invalidate** because:

1. New `hidden` state produces strictly different SVG (elements are absent).
2. Tree value layer override changes existing node text in segtree-style trees.
3. Graph 3-tuple edge parsing accepts inputs that previously raised `ValidationError`.

**Decision**: bump `SCRIBA_VERSION: int = 2 → 3` when v0.6.0 ships. This is the first break of the contract since v0.1.1 and matches the FIX_PLAN's Phase 5 release checklist.

## 9. References

- Agent 2 Dynamic-op gaps: `docs/archive/completeness-audit-2026-04-11/02-dynamic-op-gaps.md`
- Agent 6 Dijkstra author experience: `docs/archive/completeness-audit-2026-04-11/06-author-dijkstra.md` §F4, §FR2
- Agent 7 Segtree author experience: `docs/archive/completeness-audit-2026-04-11/07-author-segtree.md` §F1, §FR1
- Agent 9 Union-Find author experience: `docs/archive/completeness-audit-2026-04-11/09-author-union-find.md` §FR1, §FR2
- FIX_PLAN Phase 2 RFC-1 prompt: `docs/archive/completeness-audit-2026-04-11/FIX_PLAN.md` §"RFC-1: Tree/Graph Mutation API"
- `primitives/plane2d.py:285-302` — `apply_command` dispatch precedent
- `primitives/graph_layout_stable.py` — frame-aware simulated annealing; already anticipates mutation
- `primitives/tree.py:108-234` — Reingold-Tilford implementation (deterministic, iterative)
- `primitives/base.py:230-276` — `set_state`/`set_value`/`set_label` interface
- `animation/constants.py:16-18` — `VALID_STATES` frozenset

---

**Acceptance**: This RFC is accepted as of commit `90d1527` and unblocks W6.1/W6.2/W6.5. Changes to any locked decision after this point require a superseding RFC.
