# Example 08 — Monkey and Apple-trees (sparse segtree + lazy)

> Showcase: bài toán kinh điển **"Monkey and Apple-trees"** (F — trang trại táo) viết lại trong Scriba. Một con khỉ đi trên hàng cây, mỗi ngày hoặc **làm chín** một dãy cây, hoặc hỏi **đếm số cây chín** trong một dãy. Đây là bản song song với example 05 nhưng tập trung vào semantic **frequency / đếm** và `range_set` kiểu "paint once" thay vì gán tổng.
>
> Cùng trục ý tưởng: sparse segtree + lazy, nhưng node-level state là `(freq, lazy)` chứ không phải `(sum, lazy)`, và trace được sinh ra từ một lần chạy thuật toán đệ quy ngay trong `@compute`.

## Problem context

Có `N` cây táo xếp thẳng hàng, đánh số `0..N-1`. Khỉ thực hiện hai loại thao tác:

- `range_set(l, r)` — tô chín toàn bộ dãy `[l, r]` (cây nào đã chín vẫn chín, idempotent).
- `range_sum(l, r)` — trả về số cây chín trong `[l, r]`.

`N` có thể tới `10^9`, nên không dựng full segtree. Ta dùng **sparse segtree**: mỗi node là một interval, chỉ cấp phát khi thực sự cần đi qua. `lazy=1` nghĩa là "cả interval này đã chín, chưa kịp đẩy xuống con".

Demo tĩnh đi kèm ở `docs/scriba/monkey-apples-demo/` chạy trên trục nhỏ `[0, 7]` với 2 thao tác:

1. `range_set(2, 5)` — tô chín các cây 2..5.
2. `range_sum(3, 6)` — đếm cây chín trong 3..6 (kết quả = 3: các cây 3, 4, 5).

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{animation}[id=monkey-apples, label="Monkey and Apple-trees — sparse segtree + lazy"]
  \compute{
  # Small range for visualization; real problem uses 10^9.
  range_lo = 0
  range_hi = 7

  # Khỉ đi 2 ngày: tô chín, rồi hỏi.
  ops = [
    ("set", 2, 5),
    ("sum", 3, 6),
  ]

  # --------------------------------------------------
  # Sparse segtree state
  #   nodes["[l,h]"] = {"type": "node", "freq": int, "lazy": int}
  #   lazy = 1 nghĩa là interval đã được paint, chưa đẩy xuống con.
  # --------------------------------------------------
  nodes = {}
  trace = []

  def key_of(lo, hi):
    return "[" + str(lo) + "," + str(hi) + "]"

  def width(lo, hi):
    return hi - lo + 1

  def get_or_create(lo, hi, parent_key):
    k = key_of(lo, hi)
    if k not in nodes:
      nodes[k] = {"type": "node", "freq": 0, "lazy": 0}
      trace.append({
        "type": "allocate",
        "node": k,
        "parent": parent_key,
      })
    return k

  def apply_paint(lo, hi):
    # "Treo" lazy=1 ở node này, freq = toàn bộ độ rộng.
    k = key_of(lo, hi)
    nodes[k] = {"type": "node", "freq": width(lo, hi), "lazy": 1}
    trace.append({
      "type": "apply_lazy",
      "node": k,
      "freq": width(lo, hi),
    })
    return 0

  def push_down(lo, hi):
    k = key_of(lo, hi)
    if nodes[k]["lazy"] == 0 or lo == hi:
      return 0
    mid = (lo + hi) // 2
    lk = get_or_create(lo, mid, k)
    rk = get_or_create(mid + 1, hi, k)
    # Truyền lazy xuống 2 con — cả 2 đều chín hoàn toàn.
    nodes[lk] = {"type": "node", "freq": width(lo, mid), "lazy": 1}
    nodes[rk] = {"type": "node", "freq": width(mid + 1, hi), "lazy": 1}
    trace.append({"type": "push_down", "node": k})
    # Parent vẫn giữ freq đã tính, nhưng lazy có thể giữ nguyên
    # (paint idempotent — không sao nếu push lại).
    return 0

  def set_range(lo, hi, ql, qr):
    k = get_or_create(lo, hi, None)
    if qr < lo or hi < ql:
      trace.append({"type": "skip", "node": k})
      return 0
    if ql <= lo and hi <= qr:
      apply_paint(lo, hi)
      return 0
    trace.append({"type": "walk", "node": k})
    push_down(lo, hi)
    mid = (lo + hi) // 2
    set_range(lo, mid, ql, qr)
    set_range(mid + 1, hi, ql, qr)
    lk = key_of(lo, mid)
    rk = key_of(mid + 1, hi)
    nodes[k] = {
      "type": "node",
      "freq": nodes[lk]["freq"] + nodes[rk]["freq"],
      "lazy": nodes[k]["lazy"],
    }
    trace.append({"type": "recompute", "node": k, "freq": nodes[k]["freq"]})
    return 0

  def sum_range(lo, hi, ql, qr):
    k = get_or_create(lo, hi, None)
    if qr < lo or hi < ql:
      return 0
    if ql <= lo and hi <= qr:
      trace.append({"type": "contained", "node": k, "freq": nodes[k]["freq"]})
      return nodes[k]["freq"]
    trace.append({"type": "walk", "node": k})
    push_down(lo, hi)
    mid = (lo + hi) // 2
    left_val = sum_range(lo, mid, ql, qr)
    right_val = sum_range(mid + 1, hi, ql, qr)
    return left_val + right_val

  # Kick off with root.
  get_or_create(range_lo, range_hi, None)

  for op in ops:
    if op[0] == "set":
      set_range(range_lo, range_hi, op[1], op[2])
      elif op[0] == "sum":
        result = sum_range(range_lo, range_hi, op[1], op[2])
        trace.append({"type": "query_result", "value": result})
  }

  \shape{st}{Tree}{kind="sparse_segtree", range_lo=0, range_hi=7}

  \step
    \narrate{Cây sparse: chỉ root $[0,7]$ được cấp phát. 14 node còn lại chưa tồn tại (mờ). Tổng cây chín = 0.}

  \step
    \recolor{st.node["[0,7]"]}{state=current}
    \narrate{Gọi $\texttt{range\_set}$ từ root. $[0,7]$ \textbf{không nằm trọn} trong $[2,5]$ → phải push\_down và recurse xuống 2 con.}

  \step
    \recolor{st.node["[0,3]"]}{state=idle}
    \recolor{st.node["[4,7]"]}{state=idle}
    \narrate{push\_down ở root tạo 2 con $L=[0,3]$ và $R=[4,7]$ (cả 2 đều rỗng, $\text{lazy}=0$).}

  \step
    \recolor{st.node["[0,3]"]}{state=current}
    \recolor{st.node["[0,1]"]}{state=dim}
    \apply{st.node["[2,3]"]}{value=2, label="lazy=1"}
    \recolor{st.node["[2,3]"]}{state=good}
    \narrate{Ở $L=[0,3]$: con trái $LL=[0,1]$ \textbf{rời} với $[2,5]$ → skip. Con phải $LR=[2,3]$ \textbf{nằm trọn} trong $[2,5]$ → \textbf{treo lazy=1, freq=2}, dừng. KHÔNG xuống lá $[2,2]$, $[3,3]$.}

  \step
    \recolor{st.node["[4,7]"]}{state=current}
    \recolor{st.node["[6,7]"]}{state=dim}
    \apply{st.node["[4,5]"]}{value=2, label="lazy=1"}
    \recolor{st.node["[4,5]"]}{state=good}
    \narrate{Ở $R=[4,7]$: con trái $RL=[4,5]$ \textbf{nằm trọn} → \textbf{treo lazy=1, freq=2}. Con phải $RR=[6,7]$ \textbf{rời} → skip. Cả update chỉ chạm 5 node mới.}

  \step
    \apply{st.node["[0,3]"]}{value=2}
    \apply{st.node["[4,7]"]}{value=2}
    \apply{st.node["[0,7]"]}{value=4}
    \narrate{Recompute từ dưới lên: $L.\text{freq}=0+2=2$, $R.\text{freq}=2+0=2$, $\text{root}.\text{freq}=4$. \textbf{Lazy vẫn còn ở $[2,3]$ và $[4,5]$} như món nợ chờ push xuống. Cây chỉ có 7 node.}

  \step
    \recolor{st.node["[0,7]"]}{state=current}
    \narrate{Gọi $\texttt{range\_sum}([3, 6])$ từ root. $[0,7]$ không trọn trong $[3,6]$ → recurse xuống $L$ và $R$.}

  \step
    \recolor{st.node["[0,3]"]}{state=current}
    \recolor{st.node["[2,3]"]}{state=current}
    \apply{st.node["[2,2]"]}{value=1, label="lazy=1"}
    \apply{st.node["[3,3]"]}{value=1, label="lazy=1"}
    \narrate{Ở $L$: $[0,1]$ rời → skip. $[2,3]$ không trọn (chỉ $3 \in [3,6]$) → \textbf{push\_down}: lazy=1 truyền xuống $[2,2]$ và $[3,3]$ vừa sinh ($\text{freq}=1$ mỗi node). Đây là lúc lazy "trả nợ".}

  \step
    \recolor{st.node["[3,3]"]}{state=good}
    \recolor{st.node["[4,5]"]}{state=good}
    \apply{st.node["[6,6]"]}{value=0}
    \recolor{st.node["[6,6]"]}{state=good}
    \narrate{Node đóng góp (xanh): $[3,3]=1$ (cây 3 chín), $[4,5]=2$ (cây 4, 5 chín), $[6,6]=0$ (cây 6 chưa chín). \textbf{Tổng $= 1 + 2 + 0 = 3$}. Cây cuối 11 node, tiết kiệm so với full 15 node.}
\end{animation}
```

## Pedagogical insights the demo teaches

1. **Sparse = on-demand allocation.** Trục $[0, 10^9]$ không dựng nổi; chỉ mỗi node thực sự được thăm mới tồn tại. Số node tỉ lệ $O(\text{ops} \cdot \log \text{range})$.
2. **Lazy là lời hứa, không phải kết quả.** `lazy=1` ở $[2,3]$ nghĩa là "cả khoảng này đã chín" — nhưng con của nó ($[2,2]$, $[3,3]$) chưa tồn tại. Chỉ khi nào query đi xuyên qua thì mới push_down.
3. **Paint idempotent khác set-value.** Khác example 05, ở đây `set` không "ghi đè giá trị", nó chỉ bật cờ chín. Vì thế `push_down` không cần reset lazy ở parent — đẩy xuống không sao cả, vẫn là 1.
4. **Recompute freq từ dưới lên.** Sau mỗi lần recurse, parent cập nhật `freq = left.freq + right.freq`, nhưng **lazy vẫn nguyên**. Đây là điểm mà người mới hay nhầm: lazy không reset sau recompute.
5. **Số node mở rộng qua từng query.** Step 1 có 1 node. Step 6 có 7. Step 9 có 11. Visualization theo dõi tăng trưởng sparse.

## Trade-off table

| Cách tiếp cận | Memory | Update/Query | Phù hợp khi |
|---|---|---|---|
| Full segtree `O(4N)` | $O(N)$ | $O(\log N)$ | $N \le 10^6$ |
| **Sparse segtree + lazy** | $O(\text{ops} \cdot \log \text{range})$ | $O(\log \text{range})$ | $N$ tới $10^9$, số ops vừa phải |
| Dynamic segment tree (pointer) | Tương tự sparse | $O(\log \text{range})$ | Khi không biết trước `range_hi` |
| Offline coordinate compression | $O(\text{ops})$ | $O(\log \text{ops})$ | Khi được phép batch toàn bộ ops |

Sparse segtree thắng khi: (1) trục quá lớn để array hóa, và (2) bạn phải trả lời online, không batch được.

## Expected output

Xem [`output.html`](./output.html). 9 step, node pop-in khi allocate, lazy badge cam hiển thị khi `lazy=1`, node đóng góp query cuối nhuộm xanh. Điều hướng bằng <kbd>←</kbd> <kbd>→</kbd> hoặc controller dưới SVG.

## Notes

- Ví dụ này dùng cùng host `@compute` setting như example 05: `resolve.AllowRecursion = true`, không `while`, không `import`, không `class`, node biểu diễn bằng dict với `"type"` tag. 4 hàm đệ quy (`get_or_create`, `push_down`, `set_range`, `sum_range`) viết trực tiếp, không layer phụ.
- Điểm khác biệt chính so với 05: state là `(freq, lazy∈{0,1})` thay vì `(sum, lazy=value)`, và `sum_range` chỉ cộng, không set.
- `output.html` là kỳ vọng render thủ công để pin-down ngữ nghĩa — không phải kết quả compile thật.
