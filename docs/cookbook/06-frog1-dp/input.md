# Example 06 — Frog 1 DP with candidate comparison

> Showcase: DP editorial với "candidate comparison" pedagogical pattern. Mỗi step $i$ show cả 2 candidate giá trị (từ $i-1$ và $i-2$), highlight cái win. Cuối cùng traceback path tối ưu.
>
> **Bài toán (AtCoder EDPC A)**: $N$ hòn đá với chiều cao $h_1, h_2, \dots, h_N$. Ếch ở đá 1 muốn tới đá $N$. Mỗi bước có thể nhảy tới $i+1$ hoặc $i+2$. Chi phí nhảy $i \to j$ là $|h_i - h_j|$. Tìm tổng chi phí nhỏ nhất.
>
> **DP**: $\text{dp}[i] = \min(\text{dp}[i-1] + |h_i - h_{i-1}|, \; \text{dp}[i-2] + |h_i - h_{i-2}|)$.

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{animation}[id=frog1-dp, label="Frog 1 — DP với 2 candidate"]
  \compute{
    heights = [10, 30, 40, 20, 50]
    n = len(heights)
    INF = 10**9
    dp = [INF] * n
    dp[0] = 0
    pred = [-1] * n
    trace = []
    trace.append({"type": "init", "cell": 0, "value": 0, "title": "BASE CASE",
                  "narration": "$\\text{dp}[1] = 0$ (ếch bắt đầu ở đá 1, chưa tốn chi phí)."})
    for i in range(1, n):
        options = []
        if i >= 1:
            cost = abs(heights[i] - heights[i-1])
            options.append({"src": i-1, "cost": cost, "total": dp[i-1] + cost})
        if i >= 2:
            cost = abs(heights[i] - heights[i-2])
            options.append({"src": i-2, "cost": cost, "total": dp[i-2] + cost})
        trace.append({"type": "candidates", "cell": i, "options": options,
                      "title": "dp[%d]" % (i+1),
                      "narration": "So sánh các candidate cho $\\text{dp}[%d]$." % (i+1)})
        best = 0
        for j in range(1, len(options)):
            if options[j]["total"] < options[best]["total"]:
                best = j
        dp[i] = options[best]["total"]
        pred[i] = options[best]["src"]
        trace.append({"type": "commit", "cell": i, "value": dp[i],
                      "winner_src": pred[i],
                      "title": "dp[%d] = %d" % (i+1, dp[i]),
                      "narration": "Chốt $\\text{dp}[%d] = %d$." % (i+1, dp[i])})
    # Traceback without while — bounded for with break
    path = [n - 1]
    for _ in range(n):
        last = path[-1]
        if last == 0:
            break
        path.append(pred[last])
    path = list(reversed(path))
    trace.append({"type": "traceback", "path": path, "title": "TRACEBACK",
                  "narration": "Lần ngược predecessor để dựng đường đi tối ưu."})
  }

  \shape{stones}{Array}{n=5, data=${heights}, label="h[i]"}
  \shape{dp}{DPTable}{n=5, label="dp[i]"}

  \step
    \narrate{$N = 5$ hòn đá. $h = [10, 30, 40, 20, 50]$. Tìm $\text{dp}[N]$ = chi phí nhỏ nhất tới đá cuối.}

  \step
    \apply{dp.cell[0]}{value=0}
    \recolor{dp.cell[0]}{state=done}
    \narrate{$\text{dp}[1] = 0$ (ếch bắt đầu ở đá 1, chưa tốn chi phí).}

  \step
    \recolor{dp.cell[1]}{state=current}
    \annotate{dp.cell[1]}{label="20", arrow_from=dp.cell[0], color=info}
    \narrate{Từ đá 2 chỉ có thể đến từ đá 1. Cost = $|30 - 10| = 20$.}

  \step
    \apply{dp.cell[1]}{value=20}
    \recolor{dp.cell[1]}{state=done}
    \narrate{Chỉ 1 option → $\text{dp}[2] = 20$.}

  \step
    \recolor{dp.cell[2]}{state=current}
    \annotate{dp.cell[2]}{label="30 (từ 2)", arrow_from=dp.cell[1], color=info}
    \annotate{dp.cell[2]}{label="30 (từ 1)", arrow_from=dp.cell[0], color=info}
    \narrate{Từ đá 3: (a) từ đá 2, tổng = $20 + 10 = 30$; (b) từ đá 1, tổng = $0 + 30 = 30$. Tie.}

  \step
    \apply{dp.cell[2]}{value=30}
    \recolor{dp.cell[2]}{state=done}
    \narrate{Cả 2 đều bằng 30. Ta pick option từ đá 2 (predecessor gần hơn, quy ước). $\text{dp}[3] = 30$.}

  \step
    \recolor{dp.cell[3]}{state=current}
    \annotate{dp.cell[3]}{label="50 (từ 3)", arrow_from=dp.cell[2], color=info}
    \annotate{dp.cell[3]}{label="30 (từ 2)", arrow_from=dp.cell[1], color=good}
    \narrate{Từ đá 4: (a) từ đá 3, total = $30+20=50$; (b) từ đá 2, total = $20+10=30$.}

  \step
    \apply{dp.cell[3]}{value=30}
    \recolor{dp.cell[3]}{state=done}
    \narrate{Nhảy xa hơn (từ đá 2) rẻ hơn! $\text{dp}[4] = 30$.}

  \step
    \recolor{dp.cell[4]}{state=current}
    \annotate{dp.cell[4]}{label="60 (từ 4)", arrow_from=dp.cell[3], color=info}
    \annotate{dp.cell[4]}{label="40 (từ 3)", arrow_from=dp.cell[2], color=good}
    \narrate{Từ đá 5: (a) từ đá 4, total = $30+30=60$; (b) từ đá 3, total = $30+10=40$.}

  \step
    \apply{dp.cell[4]}{value=40}
    \recolor{dp.cell[4]}{state=done}
    \narrate{$\text{dp}[5] = 40$. Đây là đáp án.}

  \step
    \recolor{dp.cell[0]}{state=good}
    \recolor{dp.cell[2]}{state=good}
    \recolor{dp.cell[4]}{state=good}
    \narrate{Lần ngược từ đá 5: $5 \leftarrow 3 \leftarrow 1$. Đường đi tối ưu: $1 \to 3 \to 5$ với chi phí $30 + 10 = 40$.}
\end{animation}
```

**Tổng: ~70 dòng LaTeX (~20 dòng `\step` + ~25 dòng `\compute` DP).** Toàn bộ thuật toán DP + traceback nằm inline trong `\compute`, không cần stdlib helper riêng cho bài này.

## Vì sao không dùng stdlib helper

Thiết kế ban đầu từng định ship `scriba.algorithms.dp.frog_jump_trace()` như một helper per-problem. Nhưng stdlib-per-problem **không scale**: mỗi dạng DP (knapsack, LIS, LCS, interval DP, digit DP, bitmask DP, ...) sẽ cần một helper riêng, rồi mỗi variant lại sinh thêm một helper nữa. Core package sẽ phình to vô hạn.

Thay vào đó, Scriba chỉ cần **2 layer**:
- **L1**: editorial script (`scene`, `step`, `narrate`, `apply_tag`, `recolor`, ...).
- **L2**: `@compute` block với Starlark — chạy thuật toán + sinh event trace.

Starlark hiện đã bật `AllowRecursion=true`, nhưng đa số DP chỉ cần bounded `for` loop + `break`, không cần recursion. Bài Frog 1 ở trên là ví dụ: DP + traceback full-fit trong ~25 dòng `@compute`, general cho bất kỳ $k$-jump variant nào bằng cách chỉnh vòng `if i >= k`.

Tác giả có variant lạ → viết thẳng trong `@compute`, không chờ PR vào core.

## `match` directive

`match event.type { ... }` là directive mới giới thiệu trong example này. Nó compile-time unroll:
- Compiler đọc `trace` ở build time, biết event.type là gì
- Chỉ emit IR delta cho branch phù hợp
- Không có runtime switch/case trong JS controller

Tương đương Python:
```python
for event in trace:
    if event["type"] == "init":
        ...
    elif event["type"] == "candidates":
        ...
```

Nhưng là compile-time, không phải runtime.

## Cái Scriba làm được tốt cho Frog 1

| Component | Scriba support |
|---|---|
| DP table fill với value per cell | ✅ `Array` + `apply_tag value=...` |
| Candidate comparison (2 arrow từ nguồn → đích) | ✅ `annotate arrow from X to Y label="..."` |
| Winner highlight (xanh) vs loser (mờ) | ✅ `highlight arrow ... color=good` vs dim |
| Traceback path | ✅ `recolor` qua cell trong `event.path` |
| Narration per step với LaTeX | ✅ native |
| Step controller + keyboard nav | ✅ runtime JS |

## Cái Scriba làm kém cho Frog 1

Theo discussion "bài nào Scriba không describe nổi":

| Component | Scriba support | Workaround |
|---|---|---|
| Stones as vertical bars với chiều cao khác nhau | ❌ `Array` render bằng ô vuông, không phải bar | Chờ `Plot` v0.4, hoặc `raw_d2` escape hatch |
| Frog icon (🐸) nhảy từ stone này sang stone khác | ❌ Không có icon primitive | `raw_d2 { image: ... }` + teleport step-by-step (không smooth) |
| Smooth parabola motion của frog nhảy | ❌ Scriba là discrete frame | Không có workaround — explicit non-goal |

**Trade-off**: editorial mất "charm" của frog metaphor nhưng giữ nguyên **load-bearing visualization** (DP table + candidate arrows + traceback). Theo nguyên tắc V2 editorial ("visual gánh lập luận, không decoration"), mất metaphor là acceptable.

Tác giả có thể thêm prose "hình dung con ếch nhảy từ đá 1 sang đá 2..." bên ngoài widget — metaphor nằm ở prose, không phải visual.

## Generated event trace (output của `@compute` block)

```python
# Trace produced by the @compute block above, với heights=[10,30,40,20,50]
[
    {
        "type": "init",
        "cell": 0,
        "value": 0,
        "title": "BASE CASE",
        "narration": "$\\text{dp}[1] = 0$ (ếch bắt đầu ở đá 1, chưa tốn chi phí)."
    },
    {
        "type": "candidates",
        "cell": 1,
        "options": [
            {"src": 0, "cost": 20, "total": 20}  # |30-10| = 20
        ],
        "title": "dp[2] — 1 CANDIDATE",
        "narration": "Từ đá 2 chỉ có thể đến từ đá 1. Cost = $|30 - 10| = 20$."
    },
    {
        "type": "commit",
        "cell": 1,
        "value": 20,
        "winner_src": 0,
        "title": "dp[2] = 20",
        "narration": "Chỉ 1 option → $\\text{dp}[2] = 20$."
    },
    {
        "type": "candidates",
        "cell": 2,
        "options": [
            {"src": 1, "cost": 10, "total": 30},  # dp[2]+|40-30| = 20+10 = 30
            {"src": 0, "cost": 30, "total": 30}   # dp[1]+|40-10| = 0+30 = 30
        ],
        "title": "dp[3] — 2 CANDIDATES",
        "narration": "Từ đá 3: (a) từ đá 2, tổng = $20 + 10 = 30$; (b) từ đá 1, tổng = $0 + 30 = 30$. Tie."
    },
    {
        "type": "commit",
        "cell": 2,
        "value": 30,
        "winner_src": 1,
        "title": "dp[3] = 30",
        "narration": "Cả 2 đều bằng 30. Ta pick option từ đá 2 (predecessor gần hơn, quy ước). $\\text{dp}[3] = 30$."
    },
    {
        "type": "candidates",
        "cell": 3,
        "options": [
            {"src": 2, "cost": 20, "total": 50},  # dp[3]+|20-40| = 30+20 = 50
            {"src": 1, "cost": 10, "total": 30}   # dp[2]+|20-30| = 20+10 = 30
        ],
        "title": "dp[4] — 2 CANDIDATES",
        "narration": "Từ đá 4: (a) từ đá 3, total = $30+20=50$; (b) từ đá 2, total = $20+10=30$."
    },
    {
        "type": "commit",
        "cell": 3,
        "value": 30,
        "winner_src": 1,
        "title": "dp[4] = 30",
        "narration": "Nhảy xa hơn (từ đá 2) rẻ hơn! $\\text{dp}[4] = 30$."
    },
    {
        "type": "candidates",
        "cell": 4,
        "options": [
            {"src": 3, "cost": 30, "total": 60},  # dp[4]+|50-20| = 30+30 = 60
            {"src": 2, "cost": 10, "total": 40}   # dp[3]+|50-40| = 30+10 = 40
        ],
        "title": "dp[5] — 2 CANDIDATES",
        "narration": "Từ đá 5: (a) từ đá 4, total = $30+30=60$; (b) từ đá 3, total = $30+10=40$."
    },
    {
        "type": "commit",
        "cell": 4,
        "value": 40,
        "winner_src": 2,
        "title": "dp[5] = 40",
        "narration": "$\\text{dp}[5] = 40$. Đây là đáp án."
    },
    {
        "type": "traceback",
        "path": [0, 2, 4],
        "title": "TRACEBACK",
        "narration": "Lần ngược từ đá 5: $5 \\leftarrow 3 \\leftarrow 1$. Đường đi tối ưu: $1 \\to 3 \\to 5$ với chi phí $30 + 10 = 40$."
    }
]
```

**10 event → 10 step** trong widget. `@compute` block tự generate narration với LaTeX ngay trong Starlark, tác giả chỉ viết template một lần.

## Expected output

Xem [`output.html`](./output.html). Mở browser, bấm Next để xem từng bước candidate comparison + commit + traceback.
