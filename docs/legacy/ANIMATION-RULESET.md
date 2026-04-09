# Scriba Animation Ruleset (D2-first edition)

> Bộ quy tắc thiết kế cho animation layer của Scriba. **D2 là backend duy nhất** — Scriba compile mọi thứ xuống D2 source rồi để D2 lo render. Companion: `STATIC-FIGURE-RULESET.md`, `03-diagram-plugin.md`.
>
> **Mục tiêu**: vừa đơn giản như Django, vừa đủ mạnh cho ~99% editorial CP (qua Starlark với recursion ON), vừa deterministic, vừa debuggable, vừa phù hợp tác giả CP — và vừa **không phải tự render SVG**.

---

## Phần 0 — Bốn nguyên tắc bất biến

1. **Deterministic by construction.** Cùng source → cùng SVG, luôn luôn. Không random, không I/O, không network.
2. **Build-time only.** Scriba là compiler. Client chỉ chạy 1 script ~3KB toggle `data-step` visibility.
3. **Source-locality in errors.** Mọi lỗi dẫn về `file:line:col` trong source tác giả, không phải trong D2 source đã generate.
4. **D2 is the only renderer.** Scriba KHÔNG tự sinh SVG. Mọi shape compile xuống D2 source. D2 lo layout, theme, edge routing, SVG output. Đây là nguyên tắc kiến trúc trung tâm.

---

## Phần 1 — Triết lý: Django + D2 backend

Django giải quyết tension "đơn giản vs mạnh" bằng **layering**. Scriba copy y hệt, **plus một quyết định kiến trúc**: thay vì viết 12 SVG renderer riêng (như Manim, Motion Canvas, VisuAlgo), Scriba **chỉ là 1 transpiler từ Scriba IR sang D2 source**, rồi D2 lo phần còn lại.

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1 — EDITORIAL SCRIPT (declarative, non-TC)            │
│   · Scriba syntax — không phải D2                           │
│   · shape declarations, step blocks, narrate, predict       │
│   · Tác giả sống ở đây 90% thời gian                        │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2 — @compute (Starlark, bounded, deterministic)       │
│   · Precompute trace, DP table, BFS layers                  │
│   · Recursion ON (DFS, tree DP, sparse segtree OK)          │
│   · Không I/O, không while, không import, step cap 1e8      │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ COMPILER: Scriba IR → D2 source string                      │
│   · 1 file Scriba → 1 D2 source → 1 d2 subprocess call      │
│   · Stamp data-step, inject narration, optimize             │
└─────────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ D2 BINARY (subprocess)                                       │
│   · Layout (Dagre/ELK), theme, edge routing, SVG emission   │
│   · Native `steps:` keyword cho animation                   │
└─────────────────────────────────────────────────────────────┘
                          ▼
                    SVG + step controller JS
```

**Hệ quả của "D2-first":**

- Compiler Scriba ước tính ~1500 LoC Python (so với ~8000 nếu mỗi primitive có renderer riêng)
- Không có per-shape SVG renderer phải maintain
- Theme thống nhất qua D2 theme system
- Layout engine duy nhất (Dagre/ELK), battle-tested
- Bug surface 1× thay vì 12×
- Implementation timeline: tuần thay vì tháng

### Bảng map Django ↔ Scriba

| Django | Scriba |
|---|---|
| `models.py` | `scriba.shapes` (Array, Grid, Graph, Tree, ...) — dataclass khai báo |
| `templates/*.html` | `.scriba` editorial script |
| `urls.py` | `editorial_registry.py` |
| `INSTALLED_APPS` | `INSTALLED_SCRIBA_APPS` (scriba_graphs, scriba_dp, ...) |
| `MIDDLEWARE` | `SCRIBA_MIDDLEWARE` (theme, a11y, optimize, writer) |
| Custom template tags | Scriba directives |
| `QuerySet` | `Q()` lazy query over IR state |
| `manage.py` | `scriba` CLI |

---

## Phần 2 — Step semantic core

Layer 1 và Layer 2 compile xuống **Scriba IR**, sau đó IR compile xuống **D2 source**. Hai compile step rõ ràng. IR là single source of truth giữa Layer 1 author syntax và D2 emitter.

### 2.1 Step và Delta

```
Step {
  index:        int                 # 0-based, compiler gán
  source_loc:   {file, line, col}   # nơi tác giả viết step block
  deltas:       Delta[]             # mutation có thứ tự
  narration:    InlineText | null   # text + LaTeX
  pause_until:  "auto" | "click"
  label:        string | null
}

Delta {
  target:     Selector              # "node.u", "cell[3,4]", "edge(a,b)"
  property:   string                # "fill", "stroke", "opacity", "label"
  op:         "set" | "unset"
  value:      JSON
  provenance: {file, line, col}     # CRITICAL: nơi delta được ghi
}
```

**Provenance trên mọi delta** là feature distinctive vs D2 raw. Compiler giữ provenance từ Scriba source xuyên qua quá trình compile, gắn lên SVG element dạng `data-src="file.scriba:47:15"` (strip ở production build). Khi tác giả hỏi "tại sao node 3 màu đỏ ở step 7?", browser dev tool inspect element → 1 lookup → file:line.

D2 raw không có cái này — D2 step diff không track ai ghi cái gì.

### 2.2 Frame là pure fold

```
frame[N] = fold(frame[N-1], step[N].deltas)
```

Pure, total, không side effect. Hệ quả:

- `frame[K]` tính được trong `O(K)` từ `frame[0]`, hoặc `O(1)` nếu cached
- Forward + backward scrub bit-identical
- Compiler precompute tất cả frame ở build time, runtime chỉ toggle visibility — **không có clock**, không có drift

### 2.3 Compile xuống D2: cách `Step[]` thành D2 `steps:`

```
Scriba IR Steps          →          D2 source
─────────────────────                ─────────────────────
Step 1, deltas: []                   steps: {
Step 2, deltas: [                      1: {}
  set node.u fill=accent               2: {
  set node.v stroke=accent               u.style.fill: "#dbeafe"
]                                         v.style.stroke: "#2563eb"
Step 3, deltas: [                      }
  unset node.u fill                    3: {
  set node.v fill=good                   u.style.fill: null
]                                         v.style.fill: "#d1fae5"
                                       }
                                     }
```

Compiler là 1 pure function `IR → D2 string`. Test bằng golden file: cùng IR → cùng D2 source.

---

## Phần 3 — Layer 1: Editorial Script

Tác giả viết `.scriba` file. Cú pháp Mustache-weak: declarative, không expression, không loop, không condition.

```scriba
scene "BFS swap game" {
  import graph from scriba_graphs
  import code  from scriba_code
  theme "neutral-default"
}

shapes {
  grid current  = Grid(3, 3, data=[3,1,2, 4,5,6, 7,8,9])
  queue q       = Queue(capacity=12)
  code listing  = Code(lang="python", src="@bfs.py")
}

step "Init" {
  push q <- current
  highlight code listing lines=[6, 7]
  narrate "Khởi tạo queue với state đầu."
}

step "Pop start, expand 12 neighbors" {
  pop q -> cursor
  for_each n in @compute.neighbors(cursor)
    push q <- n
  highlight code listing lines=[11, 12, 13]
  narrate "Pop $(3,1,2,\dots)$, sinh 12 neighbor."
}
```

### 3.1 Cái được phép ở Layer 1

- Shape declarations
- `step "title" { ... }` blocks
- Built-in directives: `push`, `pop`, `highlight`, `recolor`, `move`, `arrow`, `fade`, `narrate`, `predict`, `morph`
- `for_each x in expr` — inline iteration directive (chỉ trên list từ @compute, không phải general loop)
- Variable interpolation: `${var}`
- Custom directives từ apps (registered `@scriba.directive`)
- `raw_d2 { ... }` escape hatch (xem §3.4)

### 3.2 Cái KHÔNG được phép

- Arithmetic, expression, condition, assignment
- Function definition
- General loops
- Bất kỳ computation nào

Nếu cần → mở `@compute` block.

### 3.3 Layer 1 compile thế nào

Mỗi shape declaration mapping 1-1 sang D2 declaration:

| Scriba | D2 source generated |
|---|---|
| `grid g = Grid(3, 3, data=[1,2,3,4,5,6,7,8,9])` | `g: { grid-rows: 3; grid-columns: 3; c00: "1"; c01: "2"; ... }` |
| `array a = Array(8, data=[5,2,8,1,9,3,7,4])` | `a: { grid-columns: 8; c0: "5"; c1: "2"; ... }` |
| `tree t = Tree(root=r, children_of={...})` | `r -> r.l; r -> r.r; r.l -> r.l.l; ...` |
| `graph g = Graph(nodes=[a,b,c], edges=[(a,b),(b,c)])` | `a -> b; b -> c` |
| `stack s = Stack(capacity=5)` | `s: { grid-columns: 1; grid-rows: 5; ... }` |
| `code k = Code(lang="python", src="...")` | `k: \|python\n...\|` (D2 v0.6+ native) |

Step block compile sang D2 `steps:` block với delta thành property mutation:

```scriba
step "Highlight u" {
  recolor graph.node(u) state=visited
}
```
↓
```d2
steps: {
  N: {
    g.u.style.fill: "#dbeafe"
    g.u.style.stroke: "#2563eb"
  }
}
```

### 3.4 Escape hatch: `raw_d2` block

5% case mà Scriba primitive không cover (ví dụ: sketch mode, custom container, D2 feature mới chưa map). Tác giả viết D2 raw inline:

```scriba
shapes {
  graph g = Graph(...)

  raw_d2 {
    annotation: "see paper [1]" {
      shape: text
      style.font-color: "#888"
      near: g.bottom
    }
  }
}
```

Compiler **không parse** `raw_d2` block, chỉ pass-through vào D2 source. Provenance vẫn được track ở mức block. Nếu D2 fail parse, error message dẫn về `raw_d2` block trong Scriba source.

**Khi nào dùng**: chỉ khi không có cách nào dùng primitive Scriba. Code review nên flag mọi `raw_d2` để verify chưa có way thay thế.

---

## Phần 4 — Layer 2: @compute (Starlark)

Khi cần precompute (BFS trace, DP table, sort steps, DFS, tree DP, sparse segtree, backtracking), mở `@compute` ngay trong file editorial. Starlark — Python-like syntax, sandboxed, deterministic, nhưng **đủ mạnh cho ~99% editorial CP**.

```scriba
@compute {
  edges = [(0,1),(1,2),(3,4),(4,5),(6,7),(7,8),
           (0,3),(1,4),(2,5),(3,6),(4,7),(5,8)]

  start = (3,1,2,4,5,6,7,8,9)
  target = (1,2,3,4,5,6,7,8,9)

  def swap(s, i, j):
    t = list(s)
    t[i], t[j] = t[j], t[i]
    return tuple(t)

  layer1 = [swap(start, i, j) for (i, j) in edges]
  layer2 = [swap(s, i, j) for s in layer1 for (i, j) in edges]
  found = [s for s in layer2 if s == target][0]
}
```

**Allowed**: arithmetic, comparison, boolean, list/tuple/dict/comprehension, `def`, **recursion** (DFS, tree DP, sparse segtree, backtracking), `for`/`if` statement, whitelist stdlib (`len`, `range`, `zip`, `enumerate`, `sorted`, `min`, `max`, `sum`, `abs`, ...).

**Forbidden**: `import`, `open`, `while`, global reassignment, attribute access to dunders, `print`, `time`, `random`, `os`.

**Data flow một chiều**: `@compute` produce binding → Layer 1 consume. Không feedback.

### 4.1 Starlark host config

Compiler cấu hình Starlark interpreter (starlark-go) với:

```go
resolve.AllowRecursion    = true     // DFS, tree DP, sparse segtree, backtracking
resolve.AllowGlobalReassign = false  // no `while`, no mutable top-level rebinding
thread.SetMaxExecutionSteps(1e8)     // bounded termination guarantee
```

**Tại sao bật recursion, tắt `while`:**

- **Recursion ON** → cover DFS / tree DP / sparse segtree / backtracking / divide & conquer — ~99% editorial CP trace làm được thuần Starlark.
- **`while` OFF** (via `AllowGlobalReassign=false`) → ép tác giả dùng bounded-for idiom, đảm bảo termination hiển nhiên.
- **Step cap 1e8** → hard ceiling cho mọi pathological case, build fail rõ ràng thay vì hang.

### 4.2 Starlark idioms

Một số pattern thay thế khi Python quen tay không map 1-1:

**(a) `while cond` → bounded-for + break**
```python
for _ in range(MAX_ITERS):
    if not cond:
        break
    # body
```
Tác giả phải chọn `MAX_ITERS` rõ ràng (thường `len(input) * 4` hoặc hằng số CP biết trước). Termination hiển nhiên từ source.

**(b) Mutate-in-iter → snapshot list**
```python
for x in list(lst):   # snapshot trước khi mutate
    if should_remove(x):
        lst.remove(x)
```
Starlark không cho mutate container trong lúc iterate; snapshot bằng `list(...)` là idiom chuẩn.

**(c) Class → dict với `"type"` tag**
```python
def make_node(val, left=None, right=None):
    return {"type": "node", "val": val, "left": left, "right": right}

def is_leaf(n):
    return n["type"] == "node" and n["left"] == None and n["right"] == None
```
Không có `class` — dùng constructor function trả dict, tag bằng field `"type"` cho dispatch.

**(d) `try/except` → explicit guard**
```python
# thay vì try: x = d[k] except KeyError: x = default
x = d[k] if k in d else default
```
Không có exception handling — validate trước khi access.

---

## Phần 5 — Primitive library (compile xuống D2)

12 shape primitive. Mỗi cái compile xuống D2 source theo template cố định.

| Primitive | D2 strategy |
|---|---|
| `Array(n, data)` | `grid-columns: n` container với cell labeled |
| `Grid(rows, cols, data)` | `grid-rows: r; grid-columns: c` |
| `Graph(nodes, edges, directed)` | Node + edge declarations, dagre/elk layout |
| `Tree(root, children_of)` | Parent → child edges, ELK tree layout |
| `SegTree(array)` | Compile sang tree với label = sum range, position theo level |
| `FenwickTree(n)` | Custom container với lowbit edge highlighting |
| `Stack(cap)` | `grid-columns: 1; grid-rows: cap` |
| `Queue(cap)` | `grid-rows: 1; grid-columns: cap` |
| `Deque(cap)` | Same as Queue, with end markers |
| `DPTable(rows, cols)` | `Grid` + transition arrows từ predecessor cells |
| `IntervalSet()` | Horizontal grid với tick labels (semantic số học mất) |
| `Code(lang, src)` | D2 v0.6+ native `\|<lang>...\|` shape, line highlight via overlay rect |
| `Bubble(value, label)` | `circle` shape với width/height = log scale |

**Plot deferred**: line/bar/scatter chart không có trong v0.3 vì D2 không có data-driven coordinate. v0.4 sẽ embed Vega-Lite output qua `icon: data:image/svg+xml;...`.

### 5.1 Top 5 operation 1-liner

```scriba
highlight a[l..r] color=accent           # range highlight
arrow from grid.cell[2,3] to tree.node(7) label="transition"
push stack s <- value
recolor graph.node(u) state=visited
step "Relax (u,v)" { highlight code lines=[13,14]; recolor node v fill=accent }
```

Mỗi cái compile xuống 1-3 D2 statement.

---

## Phần 6 — Q() query layer

Lazy chainable query over IR state. Đây là feature distinctive — không tool nào có cho animation.

```scriba
@compute {
  visited_early = Q(graph.nodes).where(visited_before=5)
  mst_edges = Q(graph.edges).in_mst()
  changed = Q(dp_table.cells).changed_since(prev_frame)
}

step "Highlight frontier" {
  recolor visited_early state=done
  highlight mst_edges color=accent
}
```

**Q evaluation**: lazy. Chỉ evaluate khi pass vào directive. Compile thời điểm pass: Q expand thành list selectors, mỗi selector thành 1 D2 delta trong step block.

---

## Phần 7 — Extension points

| Type | Cơ chế | Ví dụ |
|---|---|---|
| Custom directive | `@scriba.directive` decorator | `swap_cells(grid, i, j)` registered, callable trong L1 |
| App | Python package với `INSTALLED_SCRIBA_APPS` entry | `scriba_graphs`, `scriba_dp`, `scriba_strings` |
| Middleware | Ordered list processing frame | `ThemeMiddleware`, `A11yContrastMiddleware` |
| Signal | Lifecycle hooks | `pre_render`, `post_frame`, `step_emitted` |
| Management command | Auto-discovered từ `<app>/management/commands/` | `scriba lint`, `scriba new` |

---

## Phần 8 — Determinism guarantees

| Property | Guarantee | Enforcement |
|---|---|---|
| Pure output | Same source + apps + theme + D2 version → same SVG | Content-addressable hash, golden file CI |
| No I/O in L1+L2 | Không file, network, time | Starlark sandbox |
| Bounded compute | L2 luôn terminate | Step cap 1e8 + no `while` + no global reassign |
| Error locality | `file:line:col` everywhere | Provenance trong IR + D2 SourceMap |
| Seek determinism | Forward = backward bit-identical | Frames precomputed, không runtime compute |

---

## Phần 9 — Non-goals

1. Không continuous tween (CSS handle ở client)
2. Không real-time interaction ngoài next/prev/seek/predict
3. Không client-side compute
4. Không AI generation
5. Không visual editor
6. Không backward compat across major versions
7. **Không tự render SVG** — luôn qua D2
8. Không Plot ở v0.3 (deferred v0.4 qua Vega-Lite embed)

---

## Phần 10 — Walkthrough: bubble sort editorial

**`bubble.scriba`:**

```scriba
scene "Bubble sort, n=8" {
  import array from scriba_arrays
  import code  from scriba_code
  theme "editorial-light"
}

@compute {
  initial = [5, 2, 8, 1, 9, 3, 7, 4]

  def bubble_sort_trace(arr):
    a = list(arr)
    trace = []
    n = len(a)
    for i in range(n):
      for j in range(n - i - 1):
        before = list(a)
        if a[j] > a[j+1]:
          a[j], a[j+1] = a[j+1], a[j]
          trace.append({"i": j, "j": j+1, "before": before, "after": list(a)})
    return trace

  trace = bubble_sort_trace(initial)
}

shapes {
  array a = Array(8, data=initial)
  code src = Code(lang="python", src="@bubble.py")
}

step "Initial" {
  narrate "Array $[5,2,8,1,9,3,7,4]$. Sort tăng dần."
  highlight code src lines=[1, 2]
}

for_each swap in trace {
  step "Compare a[${swap.i}], a[${swap.j}]" {
    highlight array a range=[swap.i, swap.j]
    highlight code src lines=[5]
    narrate "$a[${swap.i}] = ${swap.before[swap.i]}$ vs $a[${swap.j}] = ${swap.before[swap.j]}$."
  }
  step "Swap" {
    morph array a <- swap.after
    highlight code src lines=[6]
  }
}

step "Sorted" {
  recolor array a state=done
  narrate "Hoàn tất. ${len(trace)}$ swap."
}
```

**Compile flow:**

```
bubble.scriba (~45 dòng tổng)
       ↓
Layer 2: Starlark evaluate bubble_sort_trace([5,2,8,1,9,3,7,4]) → list of swaps, bind `trace`
       ↓
Layer 1: expand `for_each swap in trace { step ... }` → N step IR objects
       ↓
Compiler: emit D2 source ~80 dòng (1 array shape + N steps)
       ↓
spawn d2 subprocess → SVG ~5KB
       ↓
Post-process: stamp data-step + inject narration → final HTML widget
```

Tác giả viết ~45 dòng tổng trong 1 file. D2 lo hết SVG. Scriba lo data flow + IR + D2 emission + post-process.

---

## Phần 11 — Error message template

```
error: <category>
  --> <file>:<line>:<col>
   |
 N | <source line with ^^^ pointing>
   |
help: <concrete fix>
```

**L1 reach too high:**
```
error: arithmetic in editorial script
  --> bfs.scriba:47:15
   |
47 |   push q <- nodes[i + 1]
   |                   ^^^^^
help: move to @compute block:
      @compute { next_node = nodes[i + 1] }
      step { push q <- next_node }
```

**L2 reach too high:**
```
error: `while` not allowed in @compute
  --> bfs.scriba:12:3
   |
12 |   while q:
   |   ^^^^^
help: use bounded-for idiom instead:
      for _ in range(MAX_ITERS):
          if not q: break
          # body
```

**Unknown selector:**
```
error: selector "node.99" not introduced
  --> bfs.scriba:67:12
help: did you mean "node.9"? available at this step: node.1..node.13
```

**D2 backend error (rare, but if D2 fails):**
```
error: D2 layout failed
  --> bfs.scriba:23:3 (compiled to graph block)
   |
23 |   graph g = Graph(nodes=[a,b,c], edges=[(a,a)])
   |
help: D2 rejected self-loop on node 'a'.
      original D2 error: "self-edges not supported in dagre layout"
      try layout_engine="elk" in scene config.
```

Provenance lookup: compiler giữ source map từ D2 source line ↔ Scriba source line, nên D2 error luôn dẫn được về Scriba file:line.

---

## Phần 12 — Implementation roadmap

Vì D2-first, roadmap rút gọn so với "12 native renderer":

- [ ] **Phase 0**: IR dataclasses (`Step`, `Delta`, `Frame`, `Provenance`). Reducer `fold`. Hand-written IR test.
- [ ] **Phase 1**: L1 parser (Lark hoặc handwritten) → IR. Hỗ trợ shape decl, step block, narrate.
- [ ] **Phase 2**: D2 emitter — IR → D2 source string. Pure function, golden file test.
- [ ] **Phase 3**: D2 subprocess integration (đã có trong `03-diagram-plugin.md`). Wire IR-emit → D2 → SVG.
- [ ] **Phase 4**: Source map — track Scriba source ↔ D2 source ↔ SVG element. Powers debug + provenance.
- [ ] **Phase 5**: Runtime JS `scriba-steps.js` ~3KB.
- [ ] **Phase 6**: L2 Starlark integration (`starlark-go` với `AllowRecursion=true`, `AllowGlobalReassign=false`, step cap 1e8).
- [ ] **Phase 7**: Q() lazy query layer over IR.
- [ ] **Phase 9**: Apps system, middleware, signals, CLI.
- [ ] **Phase 10**: Error message polish + structured diagnostics.
- [ ] **Phase 11**: DP traceback primitive (distinctive).
- [ ] **Phase 12**: Code-viz sync (line highlight wire to step).
- [ ] **Phase 13**: Predict-then-reveal interactive primitive.

Phase 0-5 là MVP — sau phase 5 đã render được editorial cơ bản. Phase 6 trở đi là power user feature.

**Estimate**: phase 0-5 = ~3 tuần (1 dev). Full v0.3 (phase 0-13) = ~8 tuần. So với mixed approach: ~16 tuần.

---

## Phần 13 — TL;DR

**Bốn câu:**

1. **Scriba là Django cho animation, với D2 là backend duy nhất.** 2 layer: L1 = editorial script (template), L2 = `@compute` Starlark (recursion ON, `while` OFF, step cap 1e8). D2 là engine render dưới hood — Scriba không tự sinh SVG.

2. **IR là dãy `Step` với provenance trên mọi delta.** Compile xuống D2 `steps:` block. Source map giữ link Scriba source ↔ D2 source ↔ SVG element.

3. **12 primitive compile xuống D2 grid container, edge declaration, hoặc native code shape.** Plot deferred v0.4 (D2 không có).

4. **Q() lazy query** là feature distinctive — biến "mọi node thoả state X" từ imperative loop thành declarative query, compile xuống batch D2 deltas.

**Three golden rules cho tác giả:**

- Cần `if`/arithmetic trong editorial → mở `@compute` Starlark block
- Cần loop không-biết-trước-cận → dùng bounded-for + break idiom thay `while`
- Cần recursion (DFS, tree DP, sparse segtree, backtracking) → viết thẳng trong `@compute`, recursion đã bật

**Three golden rules cho compiler:**

- Mọi error có `file:line:col` qua source map
- Mọi frame precompute build time, runtime không có compute
- Mọi shape compile xuống D2 — không có exception, không có native renderer

---

## Phần 14 — Open questions

1. Starlark-go vs starlark-rust vs Python reference?
2. D2 version pinning strategy (D2 v0.6 vs v0.7+)?
3. Source map format (sourcemap.io standard hay custom)?
4. `raw_d2` escape hatch — opt-in flag hay default allowed?
5. Plot strategy ở v0.4: Vega-Lite embed vs implement minimal plot trong D2-compatible format?
6. Theme inheritance: D2 theme + Scriba CSS overlay, hay chỉ D2 theme?
7. Q() query plan: lazy expand ở compile-time hay runtime side?
8. Incremental rebuild key: per-step hay per-scene hay per-file?

Ghi vào `07-open-questions.md` để team decide trước phase 1.

---

**Hết ruleset.**
