# CP Education Primitives Plan

> Addresses items from `deep-analysis-2026-04-10.md` §3 CP Education:
> Missing Queue/Deque, LinkedList, HashMap/Set, Code Panel, Variable Watch

---

## Architecture Summary

Each primitive needs:
1. **Python class** in `scriba/animation/primitives/` — implements Protocol (`addressable_parts`, `validate_selector`, `emit_svg`, `bounding_box`)
2. **Register** in `renderer.py` `PRIMITIVE_CATALOG` dict
3. **Export** in `primitives/__init__.py`
4. **Example** `.tex` file demonstrating the primitive
5. **Docs** update in `ruleset.md` and `06-primitives.md`

Template: Stack primitive (296 lines) is the simplest reference.

---

## 1. Queue Primitive

### Visual Design
```
  front →                          ← rear
  ┌────┬────┬────┬────┬────┬────┐
  │ 3  │ 7  │ 1  │ 4  │ 9  │    │
  └────┴────┴────┴────┴────┴────┘
   [0]   [1]  [2]  [3]  [4]  [5]
```

Horizontal row of cells with front/rear pointers. Similar to Array but with
enqueue/dequeue semantics and pointer arrows.

### Syntax
```latex
\shape{q}{Queue}{capacity=8, label="$Q$"}
```

### Selectors
- `q.cell[i]` — individual cell
- `q.front` — front pointer element
- `q.rear` — rear pointer element
- `q.all` — all cells

### Operations
- `\apply{q}{enqueue=5}` — add element to rear, advance rear pointer
- `\apply{q}{dequeue=true}` — remove front element, advance front pointer
- `\apply{q.cell[i]}{value=X}` — set cell value directly
- `\recolor{q.cell[i]}{state=current}` — standard state management

### SVG Layout
- Cells: horizontal `<rect>` + `<text>`, same as Array (60×40px)
- Front/rear pointers: `<polygon>` arrows above/below the cells
- Labels: "front" and "rear" text near arrows

### Implementation
- ~250 lines (simpler than Array — no annotations needed initially)
- File: `scriba/animation/primitives/queue.py`

---

## 2. LinkedList Primitive

### Visual Design
```
  ┌───┬───┐    ┌───┬───┐    ┌───┬───┐
  │ 3 │ ●─┼───→│ 7 │ ●─┼───→│ 1 │ ╱ │
  └───┴───┘    └───┴───┘    └───┴───┘
   node[0]      node[1]      node[2]
```

Each node is a box with value + pointer field. Arrows connect pointer to next node.

### Syntax
```latex
\shape{ll}{LinkedList}{data=[3,7,1], label="$list$"}
```

### Selectors
- `ll.node[i]` — individual node box
- `ll.link[i]` — the pointer/arrow from node[i] to node[i+1]
- `ll.all` — all nodes

### Operations
- `\apply{ll}{insert={index=1, value=5}}` — insert node, re-layout
- `\apply{ll}{remove=1}` — remove node, re-layout
- `\apply{ll.node[i]}{value=X}` — set node value
- `\recolor{ll.node[i]}{state=current}` — state management
- `\recolor{ll.link[i]}{state=current}` — highlight a pointer

### SVG Layout
- Nodes: two-part `<rect>` (value | pointer), 80×40px
- Links: `<line>` with arrowhead marker between nodes
- Horizontal flow, left-to-right
- Null terminator: diagonal line in last pointer field

### Implementation
- ~350 lines (more complex due to pointer visualization)
- File: `scriba/animation/primitives/linkedlist.py`

---

## 3. HashMap Primitive

### Visual Design
```
  HashMap (capacity=4)
  ┌─────┬──────────────────┐
  │  0  │  "cat"→3  "car"→7│
  ├─────┼──────────────────┤
  │  1  │                  │
  ├─────┼──────────────────┤
  │  2  │  "dog"→5         │
  ├─────┼──────────────────┤
  │  3  │  "fox"→1  "fig"→9│
  └─────┴──────────────────┘
```

Left column: bucket indices. Right column: chain of key→value pairs per bucket.

### Syntax
```latex
\shape{hm}{HashMap}{capacity=4, label="$map$"}
```

### Selectors
- `hm.bucket[i]` — bucket row
- `hm.entry[key]` — specific key-value entry (string key)
- `hm.all` — all buckets

### Operations
- `\apply{hm}{put={key="cat", value=3, bucket=0}}` — insert entry
- `\apply{hm}{remove={key="cat"}}` — remove entry
- `\recolor{hm.bucket[i]}{state=current}` — highlight bucket
- `\recolor{hm.entry[cat]}{state=current}` — highlight specific entry

### SVG Layout
- Bucket index: narrow `<rect>` column (40px wide)
- Chain area: wider `<rect>` with inline `<text>` entries
- Each entry: rounded mini `<rect>` with "key→val" text
- Vertical stack of buckets

### Implementation
- ~400 lines (most complex — variable-width chains)
- File: `scriba/animation/primitives/hashmap.py`

---

## 4. CodePanel Primitive

### Visual Design
```
  ┌──────────────────────────┐
  │  1  for i in range(n):   │
  │ →2    if dp[i] < dp[j]:  │  ← highlighted line
  │  3      dp[i] = dp[j]+1  │
  │  4  print(dp[n-1])       │
  └──────────────────────────┘
```

Source code display with line numbers. One line can be highlighted at a time
to show which code is executing at the current step.

### Syntax
```latex
\shape{code}{CodePanel}{source="
for i in range(n):
  if dp[i] < dp[j]:
    dp[i] = dp[j]+1
print(dp[n-1])
", label="Code"}
```

### Selectors
- `code.line[i]` — individual source line (1-based)
- `code.all` — all lines

### Operations
- `\recolor{code.line[2]}{state=current}` — highlight executing line
- `\recolor{code.line[1]}{state=done}` — mark line as completed
- No `\apply` — code content is static

### SVG Layout
- Monospace `<text>` elements, one per line
- Line numbers in gray on the left
- Background `<rect>` for the panel
- Highlighted line: colored background `<rect>` behind the text
- Fixed width, height = lines × line_height

### Implementation
- ~200 lines (simple — just text rendering with line highlighting)
- File: `scriba/animation/primitives/codepanel.py`

---

## 5. VariableWatch Primitive

### Visual Design
```
  ┌─────────┬────────┐
  │  i      │  3     │
  │  j      │  1     │
  │  min_val│  7     │
  │  result │  ----  │
  └─────────┴────────┘
```

Variable inspector panel showing name-value pairs. Values update as the
algorithm progresses.

### Syntax
```latex
\shape{vars}{VariableWatch}{names=["i","j","min_val","result"], label="Variables"}
```

### Selectors
- `vars.var[name]` — individual variable by name (string key)
- `vars.all` — all variables

### Operations
- `\apply{vars.var[i]}{value=3}` — set variable value
- `\apply{vars.var[result]}{value="done"}` — set to string
- `\recolor{vars.var[i]}{state=current}` — highlight changed variable

### SVG Layout
- Two-column table: name (left, gray) | value (right, colored by state)
- Each row: 60px height
- Fixed width: name_col=100px + value_col=100px
- State colors on value cell background

### Implementation
- ~180 lines (simplest — just a name-value table)
- File: `scriba/animation/primitives/variablewatch.py`

---

## 6. Implementation Order

| Phase | Primitive | Effort | Dependencies |
|-------|-----------|--------|-------------|
| 1 | VariableWatch | Small (~180 lines) | None |
| 2 | Queue | Small (~250 lines) | None |
| 3 | CodePanel | Small (~200 lines) | None |
| 4 | LinkedList | Medium (~350 lines) | None |
| 5 | HashMap | Medium (~400 lines) | None |

**Phases 1-3 are independent** — can be parallelized (3 agents).
**Phases 4-5 are independent** — can be parallelized (2 agents).

Total: ~1,380 lines across 5 new files.

---

## 7. Shared Changes

Each primitive needs:
1. Add class to `PRIMITIVE_CATALOG` in `renderer.py` (~1 line each)
2. Add import + export in `primitives/__init__.py` (~2 lines each)
3. Add to `ruleset.md` primitive table (~10 lines each)
4. Create example `.tex` file (~30 lines each)

Shared changes: ~65 lines total.

---

## 8. Risks

- **String-keyed selectors** (HashMap `entry[key]`, VariableWatch `var[name]`):
  Current selector parser expects integer indices. Need to extend selector
  parsing to handle string keys in brackets. This affects `parser/selectors.py`.

- **Variable-width rendering** (HashMap chains, CodePanel source):
  SVG width depends on content. Need dynamic width calculation.

- **Insert/remove operations** (LinkedList, Queue):
  These mutate the primitive's structure (add/remove nodes). Current primitives
  are mostly static-sized. Need to handle dynamic addressable_parts().
