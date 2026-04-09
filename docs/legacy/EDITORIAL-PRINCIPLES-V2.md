# Editorial Principles v2 — Visualization-First

> Thay thế v1. v1 sai ở chỗ: prose-to-viz ratio ~1500:1, widget bị chôn ở §5, figure là "trang trí" chứ không "gánh lập luận". v2 đảo ngược: **visual gánh lập luận, prose chỉ là scaffolding**.

## Nguyên tắc cốt lõi (đọc cái này nếu không đọc gì khác)

1. **Hero viz above the fold.** Mở trang là thấy 1 visualization chạy trên **input thật của bài**, không phải toy example. Trước khi user scroll, họ phải thấy bài toán *trông* như thế nào.
2. **Visual load-bearing, không decorative.** Nếu xoá figure đi mà lập luận vẫn đứng được → figure đó sai. Figure phải là cái *duy nhất* giải thích được invariant đó.
3. **Predict-then-reveal.** Trước khi show kết quả step tiếp theo, cho user đoán ("next pop sẽ là ai?"). Dual coding + active recall.
4. **Synchronized code ↔ viz.** Khi highlight line `dist[v] = dist[u]+1`, node `v` trên graph cũng phải nhấp nháy. Không bao giờ tách rời.
5. **Small multiples > animation** cho invariants. Animation cho *process*, small multiples cho *so sánh trạng thái*.
6. **Prose ≤ 800 từ toàn bài.** Không phải mỗi section — toàn bài. Nếu cần giải thích dài, đó là dấu hiệu thiếu figure.
7. **≥3 visuals trước code block đầu tiên.** Code là cái cuối cùng, không phải cái đầu tiên.

## Template 8-section (visualization-first)

| # | Section | Format chính | Prose cap |
|---|---------|--------------|-----------|
| 1 | **Hero** | Hero viz chạy input thật + TL;DR card (3 dòng: độ phức tạp, kỹ thuật, key insight) | 40w |
| 2 | **Problem as picture** | Inline SVG figure restate đề bài bằng hình (không nhắc lại text đề) | 60w |
| 3 | **Why naive fails** | Small multiples: |state space| grow theo n (3 frames: n=3, n=5, n=9). Figure tự nó chứng minh TLE. | 80w |
| 4 | **Key insight** (1 figure, 1 câu) | 1 inline SVG khoanh tròn cái invariant cứu thuật toán. 1 câu caption. | 30w |
| 5 | **Interactive trace** | Widget chạy trên input thật bài, có predict-then-reveal, synchronized panels (graph ↔ queue ↔ code ↔ narration) | 150w |
| 6 | **Walkthrough** | Inline figures xen kẽ — mỗi đoạn prose ≤3 dòng phải kèm 1 figure | 300w |
| 7 | **Code** (with line-level viz hooks) | Code highlight sync với widget ở §5. User click line → widget seek tới step tương ứng | 80w |
| 8 | **Variants & traps** | Bảng small multiples: mỗi variant 1 mini-figure | 60w |

**Tổng prose cap: 800w.** Nếu vượt → xoá prose, thêm figure.

## Visual catalog bắt buộc có mặt

Mỗi bài *phải* có đủ 5 loại viz dưới đây, không được thiếu:

1. **Hero viz** — chạy input thật, above fold
2. **State-space small multiples** — chứng minh tại sao naive fail
3. **Invariant spotlight** — 1 figure tĩnh khoanh cái insight
4. **Interactive trace widget** — predict-then-reveal + synced panels
5. **Code-viz sync** — click line → viz seek

Thiếu bất cứ cái nào → bài chưa xong.

## Per-algorithm viz lookup

| Kỹ thuật | Canonical viz | Anti-pattern |
|----------|---------------|--------------|
| BFS/DFS | Graph + queue/stack panel + visited set, step-through trên input thật | Toy 5-node graph không phải input bài |
| DP (1D/2D) | Table fill với arrow từ source cells, backtrack path reveal | Chỉ show recurrence LaTeX |
| Segment tree | Tree + range highlight + lazy tag bubbles, push_down animation | Chỉ show array |
| Two pointers | Array với 2 cursor move, window highlight | Chỉ code |
| Binary search | Interval shrink animation, predicate plot | "Chia đôi" bằng chữ |
| Greedy | Sort animation + swap counterexample small multiples | "Đổi chỗ thì tệ hơn" bằng chữ |
| Graph shortest path | Distance labels update live, relaxation edge highlight | Adjacency list dump |
| Sparse segtree + lazy | Lazy-allocated nodes pop in, tag push_down tạo children | Static full tree |

## Anti-patterns (xoá ngay nếu thấy)

- ❌ **Toy example graph** không phải input bài. Swap Game phải chạy trên 9! state thật (hoặc projection của nó), không phải 5-node ABCDE.
- ❌ **Widget ghetto**: widget duy nhất nằm ở §5. Phải có figure từ §1.
- ❌ **Prose block >3 dòng không kèm figure**.
- ❌ **Code block trước khi có ≥3 visuals**.
- ❌ **Animation cho cái nên là small multiples** (vd: so sánh 3 approach → small multiples, không phải tab switch).
- ❌ **Figure caption dài hơn figure**.
- ❌ **LaTeX recurrence không kèm table fill viz**.

## Prose rules

- Câu ngắn. Mỗi câu ≤ 15 từ nếu được.
- Không "chúng ta thấy rằng", "dễ thấy", "rõ ràng". Xoá.
- Không nhắc lại đề bài. §2 đã có figure restate rồi.
- Không viết "animation trên đây cho thấy...". Figure tự nói.
- Active voice. "BFS pop A" không phải "A được pop bởi BFS".

## Budget enforcement

Khi viết xong, đếm:
- [ ] Tổng prose ≤ 800w?
- [ ] ≥5 loại viz trong catalog có đủ?
- [ ] Hero viz chạy trên input thật?
- [ ] ≥3 visuals trước code block đầu?
- [ ] Mỗi prose block >3 dòng có figure kèm?
- [ ] Widget có predict-then-reveal?
- [ ] Code ↔ viz có sync?

Thiếu 1 → chưa ship.

## Lý do đảo ngược (vì sao v1 sai)

v1 dựa trên convention của editorial text-based (Codeforces, cp-algorithms). Những convention đó ra đời khi HTML chỉ có text + static image. Giờ có SVG + JS + interactive, giữ convention cũ = lãng phí medium.

Mayer's multimedia principle: learning tốt hơn khi *words + pictures* hơn là *words alone* — nhưng chỉ khi pictures **load-bearing**. Decorative pictures còn tệ hơn không có (coherence principle).

Dual coding (Paivio): verbal + visual channel độc lập, dùng cả 2 = 2x bandwidth. Text-only = phí 1 channel.

Cognitive load (Sweller): CP editorial thường high intrinsic load. Extraneous load từ prose dài → quá tải. Figure giảm extraneous load vì nó thay thế working memory bằng external representation.

Bret Victor / Explorable Explanations: "reader should be able to *play* with the idea, not just read about it". Widget ở §5 = không play được cho tới khi đọc 4 section. Sai.

3Blue1Brown: mọi concept đều có 1 "canonical image". Nhiệm vụ editorial là tìm canonical image đó và dựng figure quanh nó, prose chỉ là chú thích.

---

**Rule of thumb cuối cùng:** Nếu in bài ra giấy đen trắng mà vẫn hiểu được → bạn viết editorial text-based, không phải editorial visualization-first. Phải sai.
