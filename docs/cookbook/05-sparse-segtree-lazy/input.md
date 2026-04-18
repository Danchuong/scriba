# Example 05 — Sparse segment tree with lazy propagation (animated)

> Showcase: sparse segment tree — node được **lazy-allocate** khi access lần đầu, cộng với lazy tag propagation. Bài toán "Monkey and Apple-trees" (F — trang trại táo) là case study.
>
> Đây là ví dụ phức tạp nhất trong cookbook và cũng là **canonical example** chứng minh rằng `\compute{...}` một mình đã đủ để chạy thuật toán đệ quy thật sự — không cần layer phụ nào.

## Problem context

Trục `[1..10^9]`. 2 loại query:
- `set(l, r, v)`: gán `v` cho mọi ô trong `[l, r]` (không cộng dồn, phá tag cũ)
- `sum(l, r)`: tổng ô trong `[l, r]`

Vì range `10^9` quá lớn, không dựng segtree đầy đủ. **Sparse segtree**: chỉ tạo node khi thực sự cần, mỗi node có `lazy` tag. `push_down` lúc đi xuống tạo 2 con on-demand.

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{animation}[id=sparse-segtree-lazy, label="Sparse segtree + lazy propagation"]
  \compute{
  # Input: 3 operations on range [0, 7] (small for visualization)
  ops = [
    ("set", 2, 5, 3),
    ("set", 4, 7, 2),
    ("sum", 3, 6),
  ]

  # Sparse segtree simulation — runs inline in Starlark.
  # resolve.AllowRecursion = true ở host nên recursive def hợp lệ.
  # Node = dict {"sum", "lazy", "type": "node"}; nodes là dict "[l,r]" -> node.
  nodes = {}
  checkpoints = []

  def key_of(lo, hi):
    return "[" + str(lo) + "," + str(hi) + "]"

  def get_or_create(lo, hi, parent_key):
    k = key_of(lo, hi)
    if k not in nodes:
      nodes[k] = {"type": "node", "sum": 0, "lazy": None}
      checkpoints.append({
        "type": "allocate",
        "node": k,
        "parent": parent_key,
      })
    return k

  def push_down(lo, hi):
    k = key_of(lo, hi)
    if nodes[k]["lazy"] == None or lo == hi:
      return 0
    mid = (lo + hi) // 2
    lk = get_or_create(lo, mid, k)
    rk = get_or_create(mid + 1, hi, k)
    v = nodes[k]["lazy"]
    nodes[lk] = {"type": "node", "sum": (mid - lo + 1) * v, "lazy": v}
    nodes[rk] = {"type": "node", "sum": (hi - mid) * v, "lazy": v}
    checkpoints.append({"type": "push_down", "node": k, "lazy": v})
    nodes[k] = {"type": "node", "sum": nodes[k]["sum"], "lazy": None}
    return 0

  def set_range(lo, hi, ql, qr, v):
    k = get_or_create(lo, hi, None)
    if qr < lo or hi < ql:
      return 0
    if ql <= lo and hi <= qr:
      nodes[k] = {"type": "node", "sum": (hi - lo + 1) * v, "lazy": v}
      checkpoints.append({
        "type": "apply_lazy",
        "node": k,
        "lazy": v,
        "sum": nodes[k]["sum"],
      })
      return 0
    push_down(lo, hi)
    mid = (lo + hi) // 2
    set_range(lo, mid, ql, qr, v)
    set_range(mid + 1, hi, ql, qr, v)
    lk = key_of(lo, mid)
    rk = key_of(mid + 1, hi)
    nodes[k] = {
      "type": "node",
      "sum": nodes[lk]["sum"] + nodes[rk]["sum"],
      "lazy": nodes[k]["lazy"],
    }
    return 0

  def sum_range(lo, hi, ql, qr):
    k = get_or_create(lo, hi, None)
    if qr < lo or hi < ql:
      return 0
    if ql <= lo and hi <= qr:
      return nodes[k]["sum"]
    push_down(lo, hi)
    mid = (lo + hi) // 2
    return sum_range(lo, mid, ql, qr) + sum_range(mid + 1, hi, ql, qr)

  range_lo = 0
  range_hi = 7
  for op in ops:
    if op[0] == "set":
      set_range(range_lo, range_hi, op[1], op[2], op[3])
    elif op[0] == "sum":
      result = sum_range(range_lo, range_hi, op[1], op[2])
      checkpoints.append({"type": "query_result", "value": result})

    trace = checkpoints
  }

  \shape{st}{Tree}{kind="sparse_segtree", range_lo=0, range_hi=7}

  \step
    \narrate{Trục $[0, 7]$. Chỉ root $[0,7]$ tồn tại ban đầu. Lazy sparse segtree.}

  \step
    \recolor{st.node["[0,7]"]}{state=current}
    \narrate{Pop $[0,7]$. Giao $[2,5]$ không phải full, phải đệ quy → \textbf{allocate 2 con}.}

  \step
    \recolor{st.node["[0,3]"]}{state=idle}
    \recolor{st.node["[4,7]"]}{state=idle}
    \narrate{Tạo 2 con on-demand. Cả 2 chưa có gì, $\text{sum}=0$, $\text{lazy}=\bot$.}

  \step
    \recolor{st.node["[0,3]"]}{state=current}
    \narrate{Xuống $[0,3]$: giao $[2,3]$ không full, allocate tiếp.}

  \step
    \recolor{st.node["[0,1]"]}{state=idle}
    \apply{st.node["[2,3]"]}{value=6, label="lazy=3"}
    \recolor{st.node["[2,3]"]}{state=good}
    \narrate{$[2,3]$ phủ hoàn toàn trong $[2,5]$ → \textbf{set lazy=3}, $\text{sum}=2 \cdot 3=6$. Không cần xuống tiếp.}

  \step
    \recolor{st.node["[4,7]"]}{state=current}
    \recolor{st.node["[6,7]"]}{state=idle}
    \apply{st.node["[4,5]"]}{value=6, label="lazy=3"}
    \recolor{st.node["[4,5]"]}{state=good}
    \narrate{Tương tự bên phải: $[4,5]$ phủ hoàn toàn → set lazy=3, sum=6.}

  \step
    \apply{st.node["[0,3]"]}{value=6}
    \apply{st.node["[4,7]"]}{value=6}
    \apply{st.node["[0,7]"]}{value=12}
    \narrate{Bubble-up sum: $[0,3].\text{sum}=6$, $[4,7].\text{sum}=6$, root $=12$. set(2,5)=3 hoàn tất.}

  \step
    \recolor{st.node["[4,5]"]}{state=current}
    \annotate{st.node["[4,5]"]}{label="push\_down", color=warn}
    \narrate{set(4,7)=2 cần xuống $[4,5]$. Nó có lazy=3 cũ → \textbf{push\_down}: tạo con $[4,4]$, $[5,5]$ với lazy=3.}

  \step
    \annotate{st.node["[0,7]"]}{label="sum = 14", color=good}
    \narrate{Sau cả 3 op: root sum = 14. Mỗi op $O(\log \text{range})$, node count $O(\text{ops} \cdot \log \text{range})$ thay vì $O(\text{range})$.}
\end{animation}
```

## Why this example stresses `\compute{...}`

| Layer | Purpose here |
|---|---|
| **Editorial script** (`\begin{animation}`) | Declarative step narration; `\apply` directives tiêu thụ trace. |
| **`\compute{...}` block** | Làm **toàn bộ heavy lifting**: định nghĩa 4 hàm đệ quy (`set_range`, `sum_range`, `push_down`, `get_or_create`), giữ `nodes` dict + `checkpoints` list, chạy thuật toán thật, emit ~60 dòng logic. |

Không còn layer thứ 3. Tác giả viết thuật toán sparse segtree ngay trong Starlark, return `trace`, editorial script render. Đây là **canonical case** cho thấy `\compute{...}` không chỉ là "precompute vài biến" — nó đủ mạnh để chạy real recursive algorithm với mutable state.

## Key rendering pattern: lazy node reveal

Sparse segtree nodes that are allocated on-demand are represented by pre-generating all nodes in the SVG output but rendering them with `state=dim` (visually hidden) until the step where they are allocated. At that point a `\recolor` command transitions the node to `state=idle`, producing a visual "pop-in" effect via the runtime CSS transition.

The parent-child edge is also pre-generated but invisible (`state=dim`) and revealed alongside the child node in the same frame.

## Expected output

Xem [`output.html`](./output.html). 9 step, 5 node allocate tuần tự, lazy tag hiển thị ở dưới node.

## Notes on complexity

Ví dụ này phức tạp hơn example 04 ở 4 điểm:

1. **Node count dynamic**: cây bắt đầu 1 node, tăng dần tới 9 node qua các step. Compiler generate đủ D2 nodes từ trace, set opacity per step.
2. **Lazy tag display**: mỗi node có label 3 phần: range, sum, lazy. Lazy hiển thị bằng badge nhỏ trên node khi != None.
3. **Push_down semantic**: lazy tag từ parent chảy xuống 2 con, rồi parent reset lazy. Animation: lazy badge fade ở parent, pop-in ở con.
4. **Recursion inline**: nhờ Starlark host bật `resolve.AllowRecursion = true`, ta có thể định nghĩa 4 hàm đệ quy ngay trong `\compute{...}`. Ràng buộc còn lại — không `while` (dùng `for _ in range(MAX): if cond: break`), không `import`, không `class` (dùng dict với `"type"` tag), không `try/except`, không stdlib — không cản được thuật toán này.
