# Example 09 — Zuma interval DP với palindrome merge

> Showcase: interval DP trên chuỗi với "palindrome merge" insight — khi `s[l] == s[k]`, vùng trong `dp[l+1][k-1]` collapse "free" và hai đầu ghép với phần đuôi. Visualize bằng DPTable 2D + arrows chỉ cha → con DP.
>
> **Bài toán (Codeforces 607B — Zuma)**: Cho dãy $N$ viên ngọc màu $s_1, s_2, \dots, s_N$. Mỗi lượt được chèn thêm 1 viên vào vị trí bất kỳ. Nếu có $\geq 2$ viên cùng màu liền kề thì chúng biến mất (cascading). Tìm số lần chèn **ít nhất** để xoá sạch dãy.
>
> **Interval DP**:
> - $dp[l][l] = 1$ (một viên cần 1 lần chèn)
> - Nếu $s[l] = s[l+1]$: $dp[l][l+1] = 1$ (cặp đôi chỉ cần 1 chèn)
> - Default: $dp[l][r] = 1 + dp[l+1][r]$
> - Nếu $s[l] = s[l+1]$: $dp[l][r] = \min(\cdot, dp[l+2][r])$
> - Palindrome merge: với mọi $k \in [l+2, r]$ và $s[k] = s[l]$:
>   $$dp[l][r] = \min\bigl(dp[l][r],\; dp[l+1][k-1] + dp[k+1][r]\bigr)$$

Instance: $s = \text{ABCCBA}$, $N = 6$. Đáp án $dp[0][5] = 1$.

## What the author writes

The author writes this LaTeX environment directly in their problem statement:

```latex
\begin{animation}[id=zuma, label="Zuma — interval DP với palindrome merge"]
  \compute{
  s = "ABCCBA"
  n = len(s)
  INF = 10**9

  # 2D table as list of lists
  dp = [[INF for _ in range(n)] for _ in range(n)]
  trace = []
  trace.append({"type": "init",
                "title": "KHỞI TẠO",
                "narration": "Bảng $dp[l][r]$ kích thước $6 \\times 6$, khởi tạo $+\\infty$ ở tam giác trên."})

  # Length 1 — base case
  for i in range(n):
    dp[i][i] = 1
  trace.append({"type": "base_case",
                "cells": [(i, i) for i in range(n)],
                "title": "BASE CASE (len 1)",
                "narration": "$dp[i][i] = 1$: mỗi viên lẻ cần 1 lần chèn để tạo cặp và biến mất."})

  # Length 2..n
  for length in range(2, n + 1):
    trace.append({"type": "length_step", "length": length,
                  "title": "LENGTH %d" % length,
                  "narration": "Duyệt mọi đoạn có độ dài $%d$." % length})
    for l in range(0, n - length + 1):
      r = l + length - 1

      # Default extend
      best = 1 + dp[l + 1][r]
      reason = "default_extend"
      src_a = (l + 1, r)
      src_b = None

      # Pair merge: s[l] == s[l+1]
      if s[l] == s[l + 1]:
        if l + 2 > r:
          cand = 1
        else:
          cand = dp[l + 2][r]
        if cand < best:
          best = cand
          reason = "pair_merge"
          src_a = (l + 2, r) if l + 2 <= r else None
          src_b = None

      # Palindrome merge
      for k in range(l + 2, r + 1):
        if s[k] == s[l]:
          left = 0 if l + 1 > k - 1 else dp[l + 1][k - 1]
          right = 0 if k + 1 > r else dp[k + 1][r]
          cand = left + right
          if cand == 0:
            cand = 1
          if cand < best:
            best = cand
            reason = "palindrome_merge"
            src_a = (l + 1, k - 1) if l + 1 <= k - 1 else None
            src_b = (k + 1, r) if k + 1 <= r else None

      dp[l][r] = best
      trace.append({"type": reason,
                    "cell": (l, r),
                    "value": best,
                    "src_a": src_a,
                    "src_b": src_b,
                    "substr": s[l:r + 1],
                    "title": "dp[%d][%d] = %d (%s)" % (l, r, best,
                              "\"" + s[l:r + 1] + "\""),
                    "narration": "Đoạn $s[%d..%d]$ = \"%s\" → $dp[%d][%d] = %d$."
                                 % (l, r, s[l:r + 1], l, r, best)})

    trace.append({"type": "final", "cell": (0, n - 1), "value": dp[0][n - 1]})
  }

  \shape{gems}{Array}{n=6, data=["A","B","C","C","B","A"], label="s"}
  \shape{dp}{DPTable}{rows=6, cols=6, label="dp[l][r]"}

  \step
    \narrate{$N = 6$, $s = \text{ABCCBA}$. Cần tìm số lần chèn ít nhất để xoá sạch.}

  \step
    \apply{dp.cell[0][0]}{value=1}
    \apply{dp.cell[1][1]}{value=1}
    \apply{dp.cell[2][2]}{value=1}
    \apply{dp.cell[3][3]}{value=1}
    \apply{dp.cell[4][4]}{value=1}
    \apply{dp.cell[5][5]}{value=1}
    \recolor{dp.cell[0][0]}{state=done}
    \recolor{dp.cell[1][1]}{state=done}
    \recolor{dp.cell[2][2]}{state=done}
    \recolor{dp.cell[3][3]}{state=done}
    \recolor{dp.cell[4][4]}{state=done}
    \recolor{dp.cell[5][5]}{state=done}
    \narrate{$dp[i][i] = 1$: mỗi viên lẻ cần 1 lần chèn để tạo cặp và biến mất.}

  \step
    \apply{dp.cell[0][1]}{value=2}
    \annotate{dp.cell[0][1]}{label="default", arrow_from=dp.cell[1][1], color=info}
    \recolor{dp.cell[0][1]}{state=done}
    \narrate{$dp[0][1]$ = "AB" ($A \neq B$): default extend $= 1 + dp[1][1] = 2$.}

  \step
    \apply{dp.cell[1][2]}{value=2}
    \recolor{dp.cell[1][2]}{state=done}
    \narrate{$dp[1][2]$ = "BC": default extend = 2.}

  \step
    \apply{dp.cell[2][3]}{value=1}
    \recolor{gems.cell[2]}{state=good}
    \recolor{gems.cell[3]}{state=good}
    \recolor{dp.cell[2][3]}{state=done}
    \narrate{$dp[2][3]$ = "CC": pair merge. $s[2] = s[3] = C$ → cặp đôi chỉ cần \textbf{1 lần chèn}.}

  \step
    \apply{dp.cell[3][4]}{value=2}
    \apply{dp.cell[4][5]}{value=2}
    \recolor{dp.cell[3][4]}{state=done}
    \recolor{dp.cell[4][5]}{state=done}
    \narrate{$dp[3][4]$ = "CB", $dp[4][5]$ = "BA": default extend, đều = 2.}

  \step
    \apply{dp.cell[0][2]}{value=2}
    \apply{dp.cell[1][3]}{value=2}
    \apply{dp.cell[2][4]}{value=2}
    \apply{dp.cell[3][5]}{value=2}
    \recolor{dp.cell[0][2]}{state=done}
    \recolor{dp.cell[1][3]}{state=done}
    \recolor{dp.cell[2][4]}{state=done}
    \recolor{dp.cell[3][5]}{state=done}
    \narrate{Length 3: tất cả đoạn "ABC", "BCC", "CCB", "CBA" → $dp = 2$.}

  \step
    \apply{dp.cell[1][4]}{value=1}
    \annotate{dp.cell[1][4]}{label="inner dp[2][3]=1", arrow_from=dp.cell[2][3], color=good}
    \recolor{dp.cell[1][4]}{state=done}
    \narrate{$dp[1][4]$ = "BCCB": palindrome merge! $s[1] = s[4] = B$, inner $dp[2][3] = 1$ (CC). Ghép hai đầu vào quá trình xoá inner → \textbf{1 lần chèn}.}

  \step
    \apply{dp.cell[0][3]}{value=2}
    \apply{dp.cell[2][5]}{value=2}
    \recolor{dp.cell[0][3]}{state=done}
    \recolor{dp.cell[2][5]}{state=done}
    \narrate{Length 4 khác: "ABCC", "CCBA" → default = 2.}

  \step
    \apply{dp.cell[1][5]}{value=2}
    \apply{dp.cell[0][4]}{value=2}
    \recolor{dp.cell[1][5]}{state=done}
    \recolor{dp.cell[0][4]}{state=done}
    \narrate{Length 5: "BCCBA", "ABCCB" → $dp = 2$.}

  \step
    \apply{dp.cell[0][5]}{value=1}
    \annotate{dp.cell[0][5]}{label="inner dp[1][4]=1", arrow_from=dp.cell[1][4], color=good}
    \recolor{dp.cell[0][5]}{state=good}
    \recolor{gems.cell[0]}{state=good}
    \recolor{gems.cell[1]}{state=good}
    \recolor{gems.cell[2]}{state=good}
    \recolor{gems.cell[3]}{state=good}
    \recolor{gems.cell[4]}{state=good}
    \recolor{gems.cell[5]}{state=good}
    \narrate{$dp[0][5]$ = "ABCCBA": palindrome merge cascade. $s[0] = s[5] = A$, inner $dp[1][4] = 1$ (BCCB). \textbf{Đáp án: chỉ cần 1 lần chèn} để xoá sạch "ABCCBA".}
\end{animation}
```

## Vì sao Zuma khó hiển thị

Theo `cookbook/HARD-TO-DISPLAY.md` (entry #1), bài toán interval DP có merge không phải là vấn đề **cấu trúc** — DPTable 2D triangle và arrows cha → con đều là primitive có sẵn. Cái khó là **insight semantic**: khi `s[l] == s[k]`, phần con `dp[l+1][k-1]` "biến mất không mất công", và đoạn này tạo thành palindrome-like merge với phần đuôi `dp[k+1][r]`. Đó là một **bước nhảy nhận thức** chứ không phải một phép tính số học đơn giản — người đọc phải hiểu rằng hai viên cùng màu ở hai đầu có thể "kẹp" phần giữa lại và đợi nó tự clear.

Example này giảm nhẹ khó khăn đó bằng 3 thủ thuật:

1. **Instance ABCCBA**: palindrome có cặp `CC` ở giữa (pair merge trivial), rồi `BCCB` dùng palindrome merge với inner `CC → 1`, rồi `ABCCBA` merge tiếp với inner `BCCB → 1`. Cascading 3 lớp, mỗi lớp đều minh hoạ một case khác nhau của recurrence.
2. **Arrows cha → con** trên DPTable: mỗi bước `palindrome_merge` vẽ 2 mũi tên rõ ràng từ `dp[l][r]` ngược về `dp[l+1][k-1]` (inner) và `dp[k+1][r]` (tail). Người đọc không cần tưởng tượng — hai nguồn dữ liệu hiển thị tường minh.
3. **Badge "merges free"** trên dải gems: tại bước palindrome merge, dải con tương ứng được annotate trực tiếp trên array `s`, link visual giữa "vùng chuỗi gốc" và "ô DP".

Scriba vẫn không vẽ được **animation cascading** của việc xoá ngọc thực sự (đây là bài Zuma gốc — ngọc nổ, rớt, ghép). Animation vật lý của game loop nằm ngoài phạm vi editorial widget và là non-goal rõ ràng; prose bên ngoài có thể bổ sung metaphor.

## Pedagogical points

| Point | Cách example này thể hiện |
|---|---|
| Base case length 1 | Batch highlight 6 ô đường chéo trong 1 step |
| Pair merge trivial | `dp[2][3] = 1` (CC) — highlight pair gems + arrow rỗng |
| Default extend | `dp[0][1], dp[1][2], dp[3][4], dp[4][5]` — 1 mũi tên dọc |
| Palindrome merge 1 lớp | `dp[1][4]` (BCCB) — 2 mũi tên + badge |
| Palindrome merge cascade | `dp[0][5]` (ABCCBA) kế thừa kết quả `dp[1][4] = 1` |

## Trade-off — Scriba làm được gì cho Zuma

| Component | Scriba support |
|---|---|
| 2D upper-triangular DP table | ✅ `DPTable(n, n)` primitive |
| Cumulative state giữa các step | ✅ delta replay từ step 1 |
| Arrows giữa ô bảng (cha → con) | ✅ `annotate arrow from ... to ...` |
| Batch update đường chéo | ✅ `for_each c in event.cells` |
| Narration với LaTeX | ✅ KaTeX inline |

| Scriba làm kém | Workaround |
|---|---|
| Animation ngọc nổ + rớt (Zuma physics) | ❌ Non-goal, prose bên ngoài |
| Highlight đồng thời nhiều `k` candidate trên 1 ô | ⚠ Hiện chỉ show winner k, không show loser k |
| Recursive merge view (tree of calls) | ❌ Cần `CallTree` primitive, chưa có |

## Expected output

Xem [`output.html`](./output.html). 16 step: Initial → base case → length 2..6 → final. Keyboard <kbd>←</kbd> <kbd>→</kbd> nav, <kbd>Space</kbd> play, <kbd>Home</kbd>/<kbd>End</kbd> jump.
