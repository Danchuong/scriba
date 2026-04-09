# Editorial Writing Principles — Cân bằng beginner và expert

> Nguyên tắc viết lời giải bài CP cho `ojcloud`. Mục tiêu: 1 trang HTML phục vụ cả người mới
> (chưa từng nghe technique) lẫn người có kinh nghiệm (chỉ cần code + complexity trong 30s).
>
> Tổng hợp từ research về CLRS, Sedgewick, K&R, Skiena, USACO Guide, cp-algorithms,
> Codeforces editorials, Stripe docs, Diátaxis framework, và Rust Book.

---

## Triết lý cốt lõi

**Một con đường tuyến tính, hai cửa thoát.**

- **Một con đường**: nội dung đọc top-to-bottom được, không tab, không nested collapse, không "chọn nhánh đọc". Người mới đọc thẳng từ trên xuống không phải quyết định gì.
- **Hai cửa thoát cho expert**:
  1. **TL;DR card** ở đầu — read-and-leave trong 10 giây
  2. **Anchor links** — nhảy thẳng tới `#code`, `#complexity`, `#pitfalls`

Đây là pattern **Stripe / Vercel / React.dev** dùng. KHÔNG split thành 2 file (như Rust Book + Rust by Example) vì 1 bài CP quá nhỏ — duy trì 2 file là overkill.

---

## 7 nguyên tắc viết (rút từ pedagogy research)

### 1. Idea trước, code giữa, why sau
Mirror cp-algorithms: *"Sort by x, sweep a multiset by y. [code]. Correctness: ..."* — ai hiểu sau câu đầu thì dừng. Đừng bắt expert đọc phần "vì sao đúng" trước khi cho họ code.

### 2. TL;DR box kiểu Skiena
4 dòng cố định ở đầu mỗi editorial:
```
Kỹ thuật:    BFS trên không gian trạng thái
Độ phức tạp: O(9! · 24) time, O(9!) space
Insight:     Mỗi hoán vị 3×3 = 1 node, mỗi swap = 1 edge
→ Jump to code  → Jump to complexity
```
Expert đọc 4 dòng này, match với guess của họ, là leave được.

### 3. Thay proof bằng trace trên n=5
Sedgewick's rule: với 90% bài CP, 1 worked example trên input nhỏ thay được 1 chứng minh hình thức. Nếu không trace được trên n=5, lời giải đang sai chỗ nào đó.

### 4. Mỗi figure phải kiếm được chỗ đứng
Vẽ figure khi nó **thay thế 1 paragraph**, không phải khi nó **trang trí 1 paragraph**. Segment tree, graph traversal, sweep line — vẽ. Một biến đếm tăng dần — không vẽ.

### 5. Đánh dấu "skip được" rõ ràng
CLRS dùng dấu ★. Ta dùng:
- Section nền nhạt + chip `Cho người mới` cho phần optional
- Section bình thường cho phần core
- Expert nhìn 1 phát biết section nào là load-bearing

### 6. Cap section ở ~400 chữ trước khi có code/figure ngắt
CPH (Laaksonen) rhythm. Wall of text dài là antipattern #1 trong editorial. Mỗi 8-12 dòng prose phải có code, figure, hoặc bullet list ngắt.

### 7. Đừng define cái chưa motivate
K&R rule: vấn đề phải đến trước công cụ. Đừng giới thiệu "monotonic deque" trước khi cho người đọc thấy O(n²) failed. Đừng nói "BFS" trước khi cho họ thấy "tại sao DFS sai".

---

## Template cố định — 11 sections

Áp dụng mechanically cho mọi bài. Không re-think structure mỗi lần.

| # | Heading (VI) | Mục đích | Length | Phục vụ | Widget? | Expert có thể skip? |
|---|---|---|---|---|---|---|
| 0 | **TL;DR box** (sticky đầu trang) | 4 dòng: kỹ thuật / độ phức tạp / insight / anchors | 40-60w | Cả hai | Không | — |
| 1 | **Đề bài tóm tắt** | 1 đoạn restate input/output/constraint | 60-100w | Cả hai | Không | ✓ |
| 2 | **Quan sát chìa khóa** | 1 ý duy nhất unlock được bài | 80-120w | Cả hai | Không | ✗ |
| 3 | **Tiếp cận ngây thơ** *(Cho người mới)* | Cách brute force + tại sao TLE/WA | 100-150w | Beginner | Không | ✓ |
| 4 | **Ý tưởng thuật toán** *(Cho người mới)* | Narrative dẫn từ insight đến algorithm | 200-350w | Beginner | **Có (1)** | ✓ |
| 5 | **Hình dung** *(Cho người mới)* | Animation/widget cho khái niệm khó nhất | caption 40w | Beginner | **Có (1)** | ✓ |
| 6 | **Chứng minh / Vì sao đúng** | Sketch correctness / invariant | 120-200w | Cả hai | Không | Một phần |
| 7 | **Cài đặt** | Pseudocode steps + edge case checklist | 150-250w | Cả hai | Không | ✗ |
| 8 | **Code C++** | 1 reference impl, annotated theo block | 60-120 LOC | Cả hai | Không | ✗ |
| 9 | **Độ phức tạp** | Time + space + 1 dòng tại sao | 40-60w | Cả hai | Không | ✗ |
| 10 | **Bẫy thường gặp** | 3-5 bullet gotchas | 60-100w | Cả hai | Không | ✗ |
| 11 | **Bài tương tự** | 3-5 link bài liên quan với difficulty tag | 30-50w | Cả hai | Không | ✗ |

**Tổng**: ~1500-2000 chữ prose + code + tối đa **1 widget** (2 cho bài cực khó).

**Hard cap**: 2500 chữ. Vượt thì cut sections 3 và 6 trước, **không bao giờ** cut 2, 7, 8, 9.

---

## Expert Mode (trên cùng 1 trang)

- **TL;DR card** sticky góc trên (desktop) hoặc top (mobile)
- **Anchor chips** ngay dưới TL;DR: `#insight #code #complexity #pitfalls`
- **Visual cues**:
  - Section core (0, 2, 7, 8, 9): nền trắng, accent bar bên trái
  - Section "Cho người mới" (3, 4, 5, 6): nền `--surface-2` nhạt, chip nhãn ở góc
- Toggle **"Chế độ chuyên gia"** trên đầu — collapse hết section gắn nhãn `beginner`

## Beginner Mode

- Linear top-to-bottom, không cần toggle gì cả (mọi section open by default)
- Mỗi khái niệm define ngay khi xuất hiện lần đầu
- **Đúng 1 animation** cho khái niệm khó nhất ở section 5
- Code (section 8) chia làm 3-5 block, mỗi block có 1 câu "Khối này làm gì"

---

## Don'ts checklist

1. ❌ Đừng dump 200 dòng C++ giữa đoạn explanation. Code chỉ ở section 8.
2. ❌ Đừng animate cái 1 figure tĩnh thể hiện được.
3. ❌ Đừng viết proof trước intuition. Section 6 đứng SAU section 4, không phải trước.
4. ❌ Đừng restate đề bài nguyên văn. Tóm tắt thôi.
5. ❌ Đừng dùng quá 2 widget/editorial.
6. ❌ Đừng giấu code sau collapse. Expert phải scroll 1 phát thấy code ngay.
7. ❌ Đừng nhồi nhiều solution vào 1 editorial. Pick 1 canonical, link alternatives ở cuối.
8. ❌ Đừng dùng `"It is easy to see that..."` / `"Hiển nhiên..."` mà không có example đi kèm.
9. ❌ Đừng nested collapse (collapse trong collapse). Reader sẽ bỏ.
10. ❌ Đừng define jargon (DP, monotonic, invariant) mà không có tooltip hoặc 1 dòng giải thích.

---

## Điều bạn KHÔNG cần làm

- ❌ Viết lại từ đầu nếu bài mới có cấu trúc giống bài cũ — copy template, sửa nội dung
- ❌ Tạo widget cho mọi bài — nhiều bài chỉ cần 1 figure tĩnh
- ❌ Viết phần "alternative approaches" trong editorial chính — link riêng nếu cần
- ❌ Dịch sang nhiều ngôn ngữ — Vietnamese only, English chỉ cho tên kỹ thuật

---

## Khi nào justify 1 widget interactive (tốn công viết JS)

1 widget được chấp nhận **chỉ khi cả 3 điều kiện đúng**:

1. Khái niệm cốt lõi của bài là **process / transformation** (BFS expansion, DP fill, segment tree update) — không phải state tĩnh
2. Có **≥ 4 step** rõ ràng, mỗi step thay đổi visible state
3. **Static figure không truyền tải được** — nếu 1 ảnh vẽ tay đủ rồi, không cần widget

Bài nào không qua được 3 điều kiện này thì dùng **figure tĩnh** (SVG/PNG) thay vì widget. Tiết kiệm thời gian + reader load nhanh hơn.

---

## Worked example: CSES Swap Game (template applied)

Để tham chiếu khi viết bài mới — đây là cấu trúc đầy đủ apply template lên 1 bài thật:

> **0. TL;DR box**
> ```
> Kỹ thuật:    BFS trên không gian trạng thái
> Độ phức tạp: O(9! · 12) time, O(9!) space
> Insight:     Mỗi hoán vị 3×3 = 1 node, mỗi swap = 1 cạnh, BFS unit-weight
> → #code   → #complexity   → #pitfalls
> ```
>
> **1. Đề bài tóm tắt** (60w)
> Lưới 3×3 chứa các số 1..9 lộn xộn. Mỗi bước được swap 2 ô kề ngang/dọc. Tìm số swap nhỏ nhất để về `[1..9]`. Sample: bảng `[[2,1,3],[7,5,9],[8,4,6]]` cần 4 swap.
>
> **2. Quan sát chìa khóa** (90w)
> Chỉ có $9! = 362{,}880$ trạng thái — đủ nhỏ để duyệt hết. Mỗi state có đúng **12 neighbors** (6 cặp ngang + 6 cặp dọc). Mọi swap có cost = 1 → bài toán shortest path trên đồ thị unit-weight → BFS.
>
> **3. Tiếp cận ngây thơ** *(Cho người mới)* (120w)
> Brute force: thử mọi dãy swap có thể. Mỗi bước có 12 lựa chọn → $12^k$ states cho $k$ swap → bùng nổ. Greedy "fix nhiều ô nhất" cũng sai vì swap đôi khi phải "lùi 1 bước để tiến 2 bước". Phải dùng cách thông minh hơn.
>
> **4. Ý tưởng thuật toán** *(Cho người mới)* (300w)
> Tưởng tượng mỗi grid là 1 chấm trên giấy. Vẽ đường nối 2 chấm nếu chúng khác nhau đúng 1 swap kề. Bài toán trở thành: tìm đường đi ngắn nhất từ chấm `start` đến chấm `target` trên giant graph này. Vì mọi cạnh có cost = 1, BFS bảo đảm shortest path: lần đầu pop ra 1 node = khoảng cách nhỏ nhất tới node đó. Layer 0 = start, layer 1 = 12 neighbors, layer 2 = ..., target nằm ở layer $k$ thì đáp án = $k$.
>
> **5. Hình dung** *(Cho người mới)* — 1 widget
> Interactive 5-node BFS trace (queue + visited + current animate qua từng step). Justify: BFS expansion là process có nhiều step, queue thay đổi mỗi step, không vẽ tĩnh được. → Đáp ứng 3 điều kiện widget.
>
> **6. Chứng minh** (150w)
> BFS invariant: khi pop 1 node ra khỏi queue, distance của nó đã là shortest. Vì sao? Quy nạp theo layer. Nếu mọi node ở layer $\le k$ đã được pop với đúng distance, thì khi pop node $u$ ở layer $k+1$, mọi đường ngắn hơn $k+1$ phải đi qua 1 node đã visited rồi → contradiction. → BFS đúng.
>
> **7. Cài đặt** (200w)
> Encode grid 3×3 thành 1 số nguyên base-9 (9 chữ số). Pre-compute 12 swap pair indices. Init queue với `(start, 0)`, set visited. Vòng lặp: pop, check target, generate 12 neighbors, push những cái chưa visited với dist+1. Edge cases: input đã = target (return 0), buffer vis size = $9^9$.
>
> **8. Code C++** — code cũ từ usaco.guide với annotation theo block
>
> **9. Độ phức tạp** (50w)
> Time: $O(9! \cdot 12)$ — mỗi state vào queue đúng 1 lần, generate 12 neighbors. Space: $O(9!)$ cho visited array. Thực tế chỉ cần ~10,000 state trước khi gặp target.
>
> **10. Bẫy thường gặp** (80w)
> - Quên mark visited NGAY LÚC PUSH (không phải lúc POP) → queue phình
> - Sinh sai 12 cặp kề (lẫn cặp `(2,3)` vào hàng ngang)
> - Encode ngược (đọc grid row-major nhưng decode column-major)
> - Dùng `map<string,int>` thay vì array → chậm 10×
>
> **11. Bài tương tự**
> - 15-puzzle (bigger state space, cần A*)
> - CSES Grid Paths (BFS đơn giản hơn)
> - Codeforces 8-puzzle variants

---

## File checklist khi viết bài mới

```
problem-name/
├── index.html        — markdown structure 11 sections theo template
├── styles.css        — copy từ swap-game-demo, tweak nếu cần
├── app.js            — chỉ chứa widget nếu section 5 cần
└── (code.cpp)        — optional, embed thẳng vào index.html section 8
```

Trước khi commit, kiểm:
- [ ] TL;DR ≤ 60 chữ, có 4 trường (kỹ thuật / O(...) / insight / anchors)
- [ ] Section 2 ≤ 120 chữ, có đúng 1 idea
- [ ] Có ≤ 1 widget (≤ 2 cho bài siêu khó)
- [ ] Code section 8 reachable trong 1 scroll từ TL;DR
- [ ] Section "Cho người mới" có visual cue (chip + nền nhạt)
- [ ] Tổng prose ≤ 2000 chữ (hard cap 2500)
- [ ] Không có nested collapse
- [ ] Không có wall of text > 12 dòng không ngắt

---

**TL;DR của TL;DR**: viết theo template fixed, đặt TL;DR card + anchor cho expert ở đầu, đánh dấu phần "Cho người mới" rõ ràng để expert collapse được, dùng widget chỉ khi static figure không đủ. Đừng re-design structure mỗi bài.
