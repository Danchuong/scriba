# Example 04 — Segment tree range sum query (animated)

> Showcase: `SegTree` primitive — shape tự compute tree topology từ array, cùng `query_path()` built-in. 6 step walkthrough range sum query trên array 6 phần tử. Đây là bài toán editorial cổ điển nhất của CP.

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{animation}[id=segtree-query, label="Segment tree range sum"]
  \compute{
    arr = [2, 5, 1, 4, 9, 3]
    ql = 1
    qr = 4
  }

  \shape{st}{Tree}{data=${arr}, kind="segtree", show_sum=true}
  \shape{src}{Array}{n=6, data=${arr}, label="a[i]"}

  \step
    \highlight{src.range[1:4]}
    \narrate{Array $a = [2, 5, 1, 4, 9, 3]$. Truy vấn $\text{sum}(1, 4) = ?$}

  \step
    \recolor{st.node["[0,5]"]}{state=current}
    \recolor{st.node["[0,2]"]}{state=current}
    \recolor{st.node["[3,5]"]}{state=current}
    \narrate{Tại gốc $[0,5]$, đoạn $[1,4]$ giao \textbf{một phần} → đệ quy xuống cả hai con.}

  \step
    \recolor{st.node["[0,2]"]}{state=current}
    \recolor{st.node["[1,1]"]}{state=good}
    \recolor{st.node["[2,2]"]}{state=good}
    \recolor{st.node["[0,0]"]}{state=dim}
    \narrate{Xuống $[0,2]$: $[1,1]$ phủ hoàn toàn → \textbf{lấy 5}; $[2,2]$ → \textbf{lấy 1}; $[0,0]$ ngoài khoảng → \textbf{bỏ qua}.}

  \step
    \recolor{st.node["[3,4]"]}{state=good}
    \recolor{st.node["[5,5]"]}{state=dim}
    \narrate{Xuống $[3,5]$: $[3,4]$ phủ hoàn toàn → \textbf{lấy 13} (khỏi đi sâu); $[5,5]$ bỏ qua.}

  \step
    \highlight{st.node["[1,1]"]}
    \highlight{st.node["[2,2]"]}
    \highlight{st.node["[3,4]"]}
    \narrate{Ba nút đóng góp: $[1,1]$, $[2,2]$, $[3,4]$. Đây là lý do $O(\log n)$.}

  \step
    \annotate{st.node["[0,5]"]}{label="sum = 19", color=good}
    \narrate{Kết quả: $5 + 1 + 13 = 19$. Cây 11 nút, chỉ đọc \textbf{3} nút.}
\end{animation}
```

**~45 dòng LaTeX** cho full 6-frame walkthrough.

## Key primitives

| Primitive | Cái nó làm |
|---|---|
| `SegTree(array=arr, show_sum=true)` | Compile sang D2 tree với 11 node, mỗi node label = `[l,r]\nsum`. Tree topology tự compute từ length của array. |
| `SegTree.query_path(arr, l, r)` | Built-in helper ở L2 Starlark. Return dict `{visited, taken, skipped, answer}` — tác giả không phải hand-code BFS trên tree. |
| `state=current / path / taken / skipped / dim` | Semantic state names compile sang D2 style (fill/stroke). Wong palette tự apply. |
| `Array(6, data=arr, highlight_range=[l,r])` | Array primitive với cell 1..4 auto-highlighted. |
| `focus=true` | Thêm ring animation (D2 style `stroke-dasharray` với ring halo). |

## Why L2 `@compute` here

`SegTree.query_path()` là hàm Starlark nằm trong package `scriba_trees`. Nó chạy thuật toán query segment tree thực sự trong sandbox deterministic, return data structure. Tác giả chỉ cần 1 dòng gọi helper, không phải manually enumerate 8 visited nodes.

Nếu không dùng helper, tác giả sẽ phải viết:
```scriba
recolor st.node("[0,5]") state=path
recolor st.node("[0,2]") state=path
...  # 8 dòng enumeration
```
→ verbose, dễ sai, không tái dụng.

## Expected output

Xem [`output.html`](./output.html).
