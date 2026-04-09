# Scriba Static Figure Ruleset (D2-first edition)

> Bộ quy tắc cho **hình ảnh tĩnh** (figure không có step/animation). Companion với `ANIMATION-RULESET.md`. **D2 là backend duy nhất** — cùng compiler engine, cùng IR, cùng Layer 2, chỉ bỏ `step` và `narrate`.

---

## Phần 0 — Khi nào dùng static, khi nào dùng animation

| Static | Animation |
|---|---|
| Reader cần **so sánh** 2+ trạng thái cạnh nhau | Reader cần **theo dõi** 1 trạng thái biến đổi |
| Concept là **không gian** (layout, structure) | Concept là **thời gian** (sequence, causality) |
| Output sẽ in PDF | Web only |
| Reader scan, không đọc tuần tự | Reader đọc tuần tự, có narration |
| Invariant qua các bước | Process |
| Small multiples (3 panel n=2,3,4) | Step-through 1 panel n=4 |
| "Đây là segment tree trông như thế nào" | "BFS chạy như thế nào trên segment tree" |
| Reference figure ("xem hình 3.2") | Walkthrough widget |

**Rule of thumb**: 2 mắt cùng lúc → static. 1 mắt qua thời gian → animation.

CP editorial **80% là static** (figure restate đề, complexity comparison, invariant proof). Animation chỉ 20% (algorithm trace, recursion unfold).

**Tufte**: small multiples > animation cho việc *so sánh*. Eye + working memory đối chiếu N panel cạnh nhau dễ hơn nhớ N frame liên tiếp.

---

## Phần 1 — Bốn nguyên tắc bất biến (riêng cho static)

Bổ sung trên top 4 nguyên tắc của Animation Ruleset:

1. **Print-safe.** Render được sang PDF với CMYK-friendly, font embedded, không phụ thuộc dark mode.
2. **Self-contained.** Figure hiểu được mà không cần đọc prose. Caption + label + legend đủ.
3. **Composable.** N figure nhỏ merge thành 1 lớn (small multiples) bằng 1 directive.
4. **Density wins.** Tufte data-ink ratio: mọi pixel mang information. Decoration → cắt.

---

## Phần 2 — Cùng D2-first architecture, đơn giản hơn

```
.scriba file
     ↓
Layer 1 parser → Static Frame IR (1 frame, không phải dãy Step[])
     ↓
Layer 2 @compute (Starlark, AllowRecursion=true) — same as Animation
     ↓
D2 emitter: walk IR → emit D2 source string
     ↓
spawn d2 subprocess (1 lần per figure, không phải N lần)
     ↓
SVG (no JS, no controller, no narration overlay)
     ↓
[optional] Print pipeline: SVG → CMYK PDF
```

**Khác biệt với animation:**

- IR là **1 frame** thay vì `Step[]`. Reducer chỉ chạy 1 lần.
- D2 source không có `steps:` block. Pure static layout.
- Output không có step controller JS, không có narration `<g>`.
- Có print export pipeline (CMYK PDF).
- Thêm 5 layout primitive cho composition (small_multiples, ...).

**Layer 2 dùng chung với Animation.** Starlark `@compute` block (với `AllowRecursion=true`) là escape hatch duy nhất cho logic phức tạp, shared giữa static figure và animated walkthrough.

---

## Phần 3 — Figure script syntax

```scriba
figure "swap-game-state-space" {
  ref "fig:state-space"
  caption "State space của Swap Game theo kích thước grid."
  layout small_multiples columns=3 gap=24

  panel "2×2 grid" {
    bubble Bubble(value=24, label="$4!$")
  }
  panel "2×3 grid" {
    bubble Bubble(value=720, label="$6!$")
  }
  panel "3×3 grid" {
    bubble Bubble(value=362880, label="$9!$", color=danger)
  }
}
```

Compile ra: 1 D2 source với 3 sub-container (mỗi panel là 1 D2 grid container con), invoke `d2`, emit 1 SVG fragment + caption + figure number `Hình 3.2`.

### 3.1 Cái được phép ở Layer 1

- `figure "id" { ... }` block — đơn vị cao nhất
- `caption "..."` — text + LaTeX
- `ref "fig:..."` — anchor cho cross-reference
- Shape declaration (cùng vocab với Animation)
- `layout` directives: `single`, `small_multiples`, `side_by_side`, `inset`, `stack_vertical`, `grid`
- `panel "title" { ... }`
- Annotation directives: `highlight`, `annotate`, `region`, `path`, `zoom`
- `raw_d2 { ... }` escape hatch
- Variable interpolation từ `@compute`

### 3.2 Cái KHÔNG được phép

Y hệt Animation L1: không expression, không loop, không condition. `for_each` cho phép trên list từ `@compute`.

---

## Phần 4 — Layout primitives (compile xuống D2 grid container)

5 layout đủ cho 95% CP editorial.

### 4.1 `single`

1 shape, không decoration.

```scriba
figure "segtree" {
  layout single
  caption "Segment tree trên array $[2,5,1,4,9,3]$."
  tree st = SegTree(array=[2,5,1,4,9,3])
}
```
↓ D2 source:
```d2
st: { ... tree topology ... }
```

### 4.2 `small_multiples` (Tufte's most important pattern)

```scriba
figure "complexity" {
  layout small_multiples columns=3
  caption "State space theo $n$."

  panel "2×2" { bubble Bubble(value=24) }
  panel "2×3" { bubble Bubble(value=720) }
  panel "3×3" { bubble Bubble(value=362880) }
}
```
↓ D2 source:
```d2
container: {
  grid-columns: 3
  panel_2x2: { ... }
  panel_2x3: { ... }
  panel_3x3: { ... }
}
```

**Auto-applied rules:**
- Compiler enforce shared axis nếu plot
- Same color palette per panel
- Y-axis label chỉ panel ngoài cùng trái
- Panel title nhất quán

### 4.3 `side_by_side` (2-3 panel + auto connector)

```scriba
figure "swap-problem" {
  layout side_by_side connector=arrow
  panel "Input"  { grid Grid(3,3, data=[3,1,2, 4,5,6, 7,8,9]) }
  panel "Target" { grid Grid(3,3, data=[1,2,3, 4,5,6, 7,8,9]) }
}
```
↓ D2 source:
```d2
container: {
  grid-columns: 2
  Input: { ... }
  Target: { ... }
}
Input -> Target: ""
```

`connector` opts: `arrow` (default), `none`, `equals`, `arrow_double`.

### 4.4 `inset`

```scriba
figure "tree-zoom" {
  layout inset position=top_right size=0.35
  main { tree t = Tree(root=root_node) }
  inset { tree z = t.subtree(7) }
}
```

D2 không có inset native. Compile bằng cách đặt 2 D2 container, container con có position absolute via `near:` hint. Hơi awkward, accept tradeoff.

### 4.5 `stack_vertical` / `grid`

`stack_vertical` = `grid-rows: N grid-columns: 1`. `grid rows×cols` general.

---

## Phần 5 — Composition rules

### 5.1 Mỗi figure là unit độc lập

`figure { }` block compile ra 1 D2 source độc lập, 1 SVG fragment. Composition diễn ra **bên trong** figure (qua `panel`), không phải giữa các figure.

### 5.2 Cross-reference

```scriba
figure "fig-segtree" { ref "fig:segtree"; ... }

# Trong prose:
"Như đã thấy ở Hình \ref{fig:segtree}, segment tree có $O(n)$ node."
```

Compiler thay `\ref{fig:segtree}` bằng "Hình 3.2" (auto-numbered) và emit anchor link.

### 5.3 Inline vs block

- **Block figure**: full content width, có caption, có figure number
- **Inline figure**: nhỏ, in-line với prose, không caption, không number

```scriba
figure inline "mini-swap" {
  layout single
  grid Grid(1, 2, data=[3, 1])
}
```

---

## Phần 6 — Tufte data-ink rules

Compiler enforce. Fail → warning ở build time.

1. **Maximize data-ink, minimize non-data-ink.**
2. **No chartjunk.** Không 3D bar, không gradient, không drop shadow, không texture, không decorative icon.
3. **Erase to improve.** Gridlines mờ. Border mỏng. Tick chỉ ở data point.
4. **Small multiples > legend.** Thay vì 1 chart 5 màu + legend, 5 panel cùng style.
5. **Direct labeling > legend.** Label trực tiếp trên line.

### Compiler warnings

```
warning: data-ink ratio 0.12
  --> chapter3.scriba:47
help: remove background color, gridlines, decorative elements. target > 0.5.
```

```
warning: legend with 5 entries
  --> chapter3.scriba:55
help: consider small_multiples — direct labeling reduces eye-tracking burden.
```

---

## Phần 7 — Color và typography

### 7.1 Color rules

- **Semantic, không decorative**: color = state, không phải "make it pretty"
- **Colorblind-safe by default** (Wong palette)
- **Max 4 màu** trong 1 panel
- **Print-safe**: distinguishable khi greyscale (test build time)
- **No red-green** làm signal duy nhất

Default Wong 8-color palette:
```
black:  #000000   text/axis
orange: #E69F00   warn/highlight
sky:    #56B4E9   path/info
green:  #009E73   good/take
yellow: #F0E442   focus
blue:   #0072B2   primary
red:    #D55E00   danger
purple: #CC79A7   alt
```

D2 theme override: `theme "academic-print"` cho greyscale, `theme "editorial-light"` cho color web.

### 7.2 Typography

- 1 font family per figure
- 3 type sizes max: caption (12pt), label (10pt), data (14pt)
- Tabular numerals cho align
- No italic ngoài caption
- No bold ngoài focus

---

## Phần 8 — Caption rules

Caption là **một câu**, kết bằng dấu chấm.

Pattern: `"<Subject>. <Annotation>."`

❌ "Trong figure này, chúng ta có thể thấy rằng segment tree được xây dựng từ array..."
✅ "Segment tree trên array $[2,5,1,4,9,3]$. Mỗi node lưu tổng đoạn."

Self-contained: reader nhìn caption + figure là hiểu, không cần prose.

Compiler warning > 30 từ.

---

## Phần 9 — Primitive library (compile xuống D2)

Cùng 12 primitive với Animation Ruleset, không có operation thay đổi state qua thời gian. Plus 2 static-only:

| Primitive | Static-only? | D2 strategy |
|---|---|---|
| `Array`, `Grid`, `Graph`, `Tree`, `SegTree`, `FenwickTree`, `Stack`, `Queue`, `DPTable`, `Code` | shared | Same as Animation Ruleset Phần 6 |
| `Bubble(value, label)` | static-only | `circle` shape, log scale width/height |
| `Plot(type, data, ...)` | static-only, **deferred v0.4** | Embed pre-rendered SVG via `icon: data:image/svg+xml;...` |

**Plot deferred lý do**: D2 không có data-driven coordinate. v0.4 sẽ pipe Vega-Lite output vào D2 qua icon embed. v0.3 không support plot.

---

## Phần 10 — Static operation (5 1-liner)

```scriba
# 1. Permanent highlight
highlight a[2..5] color=accent

# 2. Annotation arrow with label
annotate arrow from a[3] to "pivot" label="i = 3"

# 3. Region marker
region rect over grid.cells[1..2, 0..2] label="window" color=info

# 4. Path overlay
path graph nodes=[1, 4, 7, 9] color=good label="shortest"

# 5. Inset zoom
zoom from grid.cell[5,5] scale=3 position=top_right
```

Mỗi op compile xuống 1-3 D2 statement với style attribute.

---

## Phần 11 — Print export pipeline

```bash
scriba export --format=pdf chapter3.scriba
```

Compile path:
```
.scriba → Scriba IR → D2 source → d2 binary → SVG (web)
                                                ↓
                                         CMYK conversion
                                                ↓
                                         font embedding
                                                ↓
                                         Cairo PDF rendering
                                                ↓
                                         chapter3.pdf
```

### 11.1 Print mode features

- Pure SVG (no JS, no interactivity)
- Font embedded (Inter / Computer Modern)
- CMYK color space
- 300 DPI raster fallback
- Auto figure numbering với prefix `Hình 3.2:` ở caption
- Greyscale mode tự convert palette sang shape pattern (dot, hatch, solid)
- Caption font scale 1.1x cho readability print
- Border 0.5pt (web có thể 1pt)

### 11.2 Per-figure overrides

```scriba
figure "fig" {
  print {
    palette greyscale
    width 8cm
    caption_position above
  }
  ...
}
```

---

## Phần 12 — Anti-patterns (compiler warning/error)

| Anti-pattern | Severity | Fix |
|---|---|---|
| Caption > 30 từ | warning | Tách thành prose |
| Pie chart | error | Bar |
| 3D chart | error | 2D |
| > 4 màu trong 1 panel | warning | small_multiples |
| Legend > 4 entries | warning | direct_label |
| Drop shadow / gradient | warning | Xoá |
| Decorative icon | warning | Xoá |
| Red+green only signal | error | Add shape variation |
| `caption "Figure showing..."` | warning | Lead với subject |
| Inline figure > 80px width | warning | Promote block |
| Block figure không có caption | error | Add caption |
| `\ref{...}` không có `ref` matching | error | Add ref |
| ≥ 3 figure liên tiếp không prose | warning | Spread out |
| Y-axis bar không bắt đầu từ 0 | warning | Justify |

---

## Phần 13 — Walkthrough: port §2 và §3 swap-game-ver3

Áp dụng D2-first vào 2 figure mà ver3 dùng JS thủ công.

### §2 Problem figure

```scriba
figure "swap-problem" {
  ref "fig:problem"
  caption "Hoán đổi 2 ô kề (12 cặp khả dĩ) để đưa input về target."
  layout side_by_side connector=arrow

  panel "Input" {
    grid g = Grid(3, 3, data=[3,1,2, 4,5,6, 7,8,9])
  }
  panel "12 cặp kề" {
    grid g = Grid(3, 3, data=[1,2,3, 4,5,6, 7,8,9])
    overlay edges Edges.adjacent_pairs(g, style="dashed", color=accent)
  }
  panel "Target" {
    grid g = Grid(3, 3, data=[1,2,3, 4,5,6, 7,8,9], state=done)
  }
}
```

Compile xuống D2:

```d2
container: {
  grid-columns: 3
  Input: {
    g: {
      grid-rows: 3; grid-columns: 3
      c00: "3"; c01: "1"; c02: "2"
      c10: "4"; c11: "5"; c12: "6"
      c20: "7"; c21: "8"; c22: "9"
    }
  }
  CapKe: {
    g: {
      grid-rows: 3; grid-columns: 3
      c00: "1"; c01: "2"; ...
    }
    # 12 dashed edges
    g.c00 -> g.c01: "" { style.stroke-dash: 3 }
    g.c01 -> g.c02: "" { style.stroke-dash: 3 }
    ...
  }
  Target: { g: { ... state=done style ... } }
}
Input -> CapKe: ""
CapKe -> Target: ""
```

12 dòng Scriba → ~30 dòng D2 source → 1 d2 invocation → SVG. So với ver3 hiện tại 50 dòng JS + pixel coordinate: zero pixel, zero coordinate, zero arrow routing math.

### §3 State space comparison

```scriba
figure "state-space" {
  ref "fig:state-space"
  caption "State space bùng nổ theo $n!$. $9!$ vẫn vừa bộ nhớ ⇒ BFS được."
  layout small_multiples columns=3

  panel "2×2 grid" { bubble Bubble(value=24, label="$4!$") }
  panel "2×3 grid" { bubble Bubble(value=720, label="$6!$") }
  panel "3×3 grid" { bubble Bubble(value=362880, label="$9!$", color=danger) }
}
```

D2:
```d2
container: {
  grid-columns: 3
  panel_2x2: {
    label: "2×2 grid"
    bubble: "4!" { shape: circle; width: 36; height: 36; style.fill: "#dbeafe" }
  }
  panel_2x3: {
    label: "2×3 grid"
    bubble: "6!" { shape: circle; width: 72; height: 72; style.fill: "#dbeafe" }
  }
  panel_3x3: {
    label: "3×3 grid"
    bubble: "9!" { shape: circle; width: 140; height: 140; style.fill: "#fde2e2" }
  }
}
```

12 dòng Scriba → ~25 dòng D2 → SVG. Bubble size compiler tự compute từ `log(value)`.

**Tổng cộng**: 24 dòng Scriba thay 85 dòng JS hand-written, không có pixel math, không có arrow routing.

---

## Phần 14 — Bảng so sánh static vs animation

| Aspect | Animation Ruleset | Static Ruleset |
|---|---|---|
| Top-level unit | `scene { ... }` với N step | `figure { ... }` không step |
| Time | First-class | Không có |
| L1 vocab | shape, step, narrate, predict, push, pop | shape, panel, layout, caption, annotate, highlight, region, path |
| L2 (Starlark) | Same | Same |
| Q() | Over animation state | Over data |
| IR | `Step[]` với deltas + provenance | `Frame` đơn lẻ |
| D2 source emitted | Có `steps:` block | Không có `steps:` block |
| Output | SVG + step controller JS + narration | SVG only |
| Print export | No (web only) | Yes (CMYK PDF) |
| Runtime JS | step controller ~3KB | 0 |
| Composition | Sequential (compose A + B) | Spatial (small_multiples) |

---

## Phần 15 — Determinism & errors

Cùng guarantees với Animation Ruleset:

- Pure output (same source → same SVG via same D2 version)
- No I/O in L1+L2
- Bounded compute in L2 (recursion allowed via `AllowRecursion=true`)
- Source map (Scriba ↔ D2 ↔ SVG)

Error template y hệt. Plus:

```
error: print export failed for figure
  --> chapter3.scriba:47
help: figure uses color "#ff00ff" which has no greyscale equivalent.
      add print { palette greyscale } block, or use Wong palette.
```

---

## Phần 16 — TL;DR

**Bốn câu:**

1. **Static = Animation trừ time, plus print export.** Cùng D2 backend, cùng IR engine, cùng L2.

2. **5 layout primitive**: `single`, `small_multiples`, `side_by_side`, `inset`, `grid`. Compile xuống D2 grid container.

3. **Tufte rules là default**: data-ink, no chartjunk, direct label, max 4 màu. Compiler enforce.

4. **Plot deferred v0.4** (D2 không có data-driven coordinate). v0.3 chỉ structural figure.

**Three golden rules cho tác giả:**

- Caption "in figure above..." → caption sai. Self-contained.
- Cần 5+ màu hoặc legend dài → small_multiples.
- Cần "step 1, step 2..." → animation, mở `ANIMATION-RULESET.md`.

**Three golden rules cho compiler:**

- Enforce data-ink ratio
- Enforce print-safe palette
- Enforce caption length, ref consistency, figure numbering

---

## Phần 17 — Open questions

1. IR sharing với animation: `Frame` là `Step` với 0 delta hay type riêng?
2. Plot pipeline ở v0.4: Vega-Lite embed vs custom?
3. Auto-numbering: per-chapter (3.2) hay per-document (12)?
4. Print pipeline: Cairo (deterministic) vs headless Chrome (font tốt hơn)?
5. `inset` layout: D2 `near:` hint có đủ không?
6. Inline figure size cap: hard limit hay warning?
7. Theme inheritance D2 ↔ Scriba CSS overlay: 1 file hay 2?

---

**Hết ruleset.**
