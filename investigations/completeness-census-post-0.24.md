# Census · Sau khi xong Tier D, scriba CÒN THIẾU GÌ? — tổng phổ visualization CP

> **BMAD investigation.** Không sửa source, không commit. Câu hỏi độc lập với danh sách JudgeZone
> A/B/C/D: quét **toàn cảnh** các họ bài competitive-programming được cộng đồng minh hoạ, đối chiếu
> năng lực **scriba 0.24.0** (18 primitive · 21 lệnh · motion glide · 3 layout), tìm **họ bài / kiểu
> hình** scriba VẪN chưa vẽ được mà KHÔNG nằm trong request. Repo @ `main` `e185786` (release 0.24.0).
> Năng lực đọc trực tiếp `docs/SCRIBA-TEX-REFERENCE.md` (target v0.24.0); 4 probe render + 3 grep
> source đã **chạy thật** phiên này (§3). Probe: `scratchpad/td-census/`.
>
> **Thang bằng chứng:** **[Confirmed]** = đọc thẳng source / render thật phiên này · **[Deduced]** =
> hệ quả logic của fact đã confirmed · **[Hypothesized]** = đề xuất thiết kế, chưa build/verify.

---

## 1. Hand-off Brief (5 câu)

Sau khi Tier D (KMP/Manacher, task #66–68) và bó **tierD-dp-shapes** đang mọc (#72–76) hạ cánh,
scriba phủ **~85%** kiểu hình visualization CP điển hình *đúng dạng cộng đồng kỳ vọng* — phần lớn
họ bài còn lại chỉ **thiếu doc-recipe chứ không thiếu machinery**. Ba **gap THẬT** (cần build, không
recipe được) nằm ngoài mọi request và **chưa ai trong team đụng tới**: (1) **kênh giá-trị-thành-chiều-cao**
(bar/histogram động) — không primitive nào mã hoá scalar bằng chiều cao cột (MetricPlot chỉ vẽ
polyline `metricplot.py:417,605`, Array là ô-text cố định); (2) **motion quay/góc** — `move_line`
chỉ trượt đường dọc, đường xiên fail **E1467** (render thật §3), không có verb `rotate`, nên rotating
calipers / angular sweep không glide được; (3) **toạ độ node thủ công cho Graph** — `ACCEPTED_PARAMS`
không có khoá `positions` (`graph.py:721-736`), layout luôn tự quyết, nên FFT-butterfly / graph
hình-học / planar không đặt được đỉnh. Đáng chú ý: census độc lập này **trùng khớp** với việc team
vừa spin-up #73 (variable-height histogram) và #72 (CHT envelope) — tức gap bar-height đang được
JudgeZone tự phát hiện và kéo vào request, xác nhận chéo mức ưu tiên của nó. Hai "nghi ứng viên" của
team lại **recipe được** (đã render kiểm chứng): bố cục **bipartite 2-cột** làm bằng
`layout="hierarchical", orientation="LR"` (probe cho 2 cột sạch cx=30 / cx=370), và **Gantt/interval-lane**
làm bằng Plane2D segments xếp theo hàng y — cả hai chỉ thiếu doc, không thiếu tính năng.

---

## 2. Phương pháp & mẫu số năng lực 0.24.0

**Đọc để chốt năng lực [Confirmed]:** `docs/SCRIBA-TEX-REFERENCE.md` §5 (21 inner command), §6 (9 visual
state), §7 (18 primitive), §12 (recipe đa-bước: traceback, flow-network, segtree-lazy, sweep-line).
Grep source xác nhận đúng 21 lệnh và không có lệnh thứ 22 nào tên `rotate/angle/spin`.

**Kênh biểu diễn scriba có (để phán "vẽ được"):**
- **Cấu trúc/topology:** 18 primitive phủ mảng, lưới, cây (segtree/sparse/heap/automata), đồ thị,
  DP table, hypercube (bitmask), forest (DSU), plane2d (điểm/đường/đoạn/đa giác/vùng/tròn/cung/quạt).
- **Trạng thái:** 9 state màu (`current/done/dim/error/good/path/hidden/highlight/idle`) + annotate/pill/arrow.
- **Motion (glide, giữ danh tính):** Array `reorder` (hoán vị sorting-pass), Plane2D `move_point/line/segment`,
  Forest `union` (cây gộp trôi vào chỗ), Tree `reparent`, generic `value_change`. → **[Confirmed]** §7.
- **Liên-shape:** `\link`/`\combine` (bắc cầu subtree↔range, row+col→cell), `\group` (bao SCC/component trên Graph).
- **Layout:** force / stable / hierarchical(TB·LR) cho Graph; Reingold-Tilford cho Tree/Forest; Hasse cho Hypercube.

**Ba trục scriba KHÔNG có (nguồn của mọi gap thật):** (a) kênh *chiều cao = giá trị*; (b) motion *quay
theo góc*; (c) *đặt toạ độ tuyệt đối* cho node đồ thị. Mọi gap §5 quy về một trong ba trục này.

---

## 3. Bằng chứng executed (phiên này) — 4 render + 3 grep **[Confirmed]**

| # | Probe | Lệnh | Kết quả | Kết luận |
|---|-------|------|---------|----------|
| P1 | `rotate_line.tex` | `move_line{to_x}` trên đường xiên slope=1 | **FAIL E1467** "line is not vertical (slope=1.0); to_x only repositions a vertical sweep line" | Motion quay/góc **là gap thật** — không glide được đường xiên, hint chỉ cho add/remove (teleport). |
| P2 | `bipartite.tex` | Graph `hierarchical`+`LR`, 6 node L/R | Render OK — trái cx=**30**, phải cx=**370** (2 cột sạch) | Bipartite matching **recipe được**, không phải gap layout. |
| P3 | `gantt.tex` | Plane2D 3 `segments` ở y=3/2/1 | Render OK, 3 lane phân biệt theo hàng y | Gantt/interval-lane **recipe được** qua Plane2D segment. |
| P4 | `barheight.tex` | Array `[2,5,1,3,7]` + MetricPlot 1 series | Render OK nhưng ra **ô-text + polyline**, không cột | Bar-height **là gap thật** — không kênh chiều cao. |
| G1 | grep `metricplot.py` | ACCEPTED_PARAMS + render style | Params `series/…/width/height`, **không** `bar/kind/type`; render chỉ `<line>`/polyline (`:417,:605`) | MetricPlot là line-chart, **không** bar-chart. |
| G2 | grep `graph.py` | `ACCEPTED_PARAMS` (`:721-736`) | 15 khoá, **không** `positions/pos/coords`; `pos` (`:447`) là biến layout nội bộ | Graph **không nhận toạ độ thủ công**. |
| G3 | grep commands | tên 21 inner command | đúng 21, **không** verb `rotate/angle/spin` | Không có motion quay ở tầng lệnh. |

Tham chiếu doc chốt thêm **[Confirmed]**: `move_line` chỉ đường dọc (§7.9, E1467); Graph "positions
decided once, from nodes and edges declared" (§7.4); Matrix op duy nhất là `cell value apply`, **không**
`reorder`/`swap_rows` như Array (§7.7 vs §7.1); Tree op = add/remove_node · reparent · add/remove_link,
**không** `rotate` (§7.5).

---

## 4. Census theo chủ đề CP (topic × phủ? × gap gì × coverage × recipe/extension/machinery)

Ký hiệu phủ: **C** = vẽ được (kể cả recipe có sẵn doc) · **R** = recipe được nhưng thiếu doc ·
**P** = một phần (thiếu dạng chuẩn/motion) · **G** = gap thật (cần build) · **★req** = đang nằm trong
request (Tier D / #72–76).

### 4.1 Strings
| Chủ đề | Phủ | Primitive dùng | Gap | Coverage |
|--------|:---:|----------------|-----|:--------:|
| Suffix array + LCP | C | Array `reorder` (rank-doubling glide) + Grid | — | cao |
| Suffix automaton / Aho-Corasick / trie | C | Tree automata (char-edge + `links`), 0.24.0 | — | cao |
| KMP prefix-func / Z-function | ★req | Array + `\cursor` | Tier D #66 | cao |
| Manacher | ★req | NumberLine/Array + cursor | Tier D #67 | TB |
| Rolling hash | R | Array + VariableWatch | thiếu doc | TB |

→ **Không gap ngoài request.**

### 4.2 Trees
| Chủ đề | Phủ | Primitive | Gap | Coverage |
|--------|:---:|-----------|-----|:--------:|
| Segment tree (+lazy) | C | Tree `segtree` + recipe §12 | — | cao |
| Fenwick / BIT | R | Array + range-highlight + annotate-arc | thiếu doc (cây trách-nhiệm vẽ bằng cung) | cao |
| Sparse table | C | Grid/DPTable (bảng 2^k) | — | TB |
| LCA (binary lifting / Euler+sparse) | R | Tree + Grid(jump) + `\link` | thiếu doc | cao |
| Euler tour | C | `\link` subtree↔range (đúng use-case doc) | — | TB |
| HLD (heavy-light) | P/R | Tree(chain recolor) + Array + `\link` | không có "chain" chuyên dụng | TB |
| Centroid decomposition | R | Tree recolor + Forest(cây phân rã) | thiếu doc | TB |
| DSU | C | Forest `union` glide, 0.24.0 | — | cao |

→ **Không gap thật; HLD chỉ P nhưng recipe được.**

### 4.3 Graphs
| Chủ đề | Phủ | Primitive | Gap | Coverage |
|--------|:---:|-----------|-----|:--------:|
| BFS/DFS/Dijkstra/Bellman/Floyd | C | Graph + recolor + `\trace` + DPTable | — | rất cao |
| Max-flow (residual) | C | Graph antiparallel + f/c pill, 0.24.0 | — | cao |
| Bipartite matching (Kuhn/HK/Hungarian) | **R** | Graph `hierarchical`+`LR` (probe P2: 2 cột sạch) | **chỉ thiếu doc** | cao |
| SCC / Tarjan / 2-SAT | C | Graph + `\group` (bao SCC), 0.24.0 | — | cao |
| MST Kruskal/Prim | C | Graph + `\group` + Forest | — | cao |
| Eulerian path/circuit | R | Graph edge-recolor theo thứ tự + `\trace` | thiếu doc | TB |
| Min-cut | R | `\group` hai phía + edge-recolor | thiếu doc | TB |
| **FFT/NTT butterfly network** | **G** | (Graph không pin được lattice bit-reversal) | **toạ độ thủ công** (G2) | thấp |
| Graph hình-học / grid-embedded / planar | **G** | (node phải nằm đúng toạ độ thật) | **toạ độ thủ công** (G2) | thấp–TB (gộp) |

→ **Gap thật: đặt toạ độ node thủ công** (nền của butterfly + graph hình-học + planar).

### 4.4 Geometry
| Chủ đề | Phủ | Primitive | Gap | Coverage |
|--------|:---:|-----------|-----|:--------:|
| Convex hull (Graham/Andrew/incremental) | C | Plane2D points + polygon mọc dần | — | cao |
| Closest pair (sweep + δ) | C | sweep pattern §12 + circle, 0.24.0 | — | TB |
| Line-segment intersection (Bentley-Ottmann) | R | sweep-line + status set | thiếu doc | TB |
| Half-plane intersection | P/R | Plane2D `add_region` (author tính polygon) | không có boolean-intersect | TB |
| **Rotating calipers / angular sweep / angular sort** | **G/P** | Plane2D (segment teleport được) | **motion quay theo góc** (P1: E1467) | TB–thấp |
| Voronoi / Delaunay | P | Plane2D polygon + circumcircle | flip tăng dần phức tạp | thấp |

→ **Gap thật: motion quay/góc** (calipers, radial sweep). Nửa-recipe cho half-plane/Voronoi.

### 4.5 Math / Number Theory
| Chủ đề | Phủ | Primitive | Gap | Coverage |
|--------|:---:|-----------|-----|:--------:|
| Sieve Eratosthenes | C | Grid/Array recolor bội số | — | cao |
| **FFT/NTT butterfly** | **G** | — | (xem §4.3, toạ độ thủ công) | thấp |
| Matrix exponentiation | R | Matrix `cell value apply` (bình phương lặp) | thiếu doc | TB |
| **Gaussian elimination / RREF** | **P** | Matrix cell-apply | **không** row-swap/scale **glide** (Matrix thiếu `reorder` mà Array có) | TB–thấp |
| CRT / ext-Euclid / Möbius | R | VariableWatch + NumberLine/Array | thiếu doc | TB |

→ **Gap thật: FFT butterfly** (thấp); **Gaussian row-op glide** (một phần, TB–thấp).

### 4.6 DP
| Chủ đề | Phủ | Primitive | Gap | Coverage |
|--------|:---:|-----------|-----|:--------:|
| Knapsack/LIS/LCS/edit/interval | C | DPTable / Grid | — | rất cao |
| Bitmask / SOS DP | C | Hypercube, 0.24.0 | — | TB |
| Tree DP | C | Tree `value` channel | — | cao |
| Digit DP | R/★req | DPTable/Grid | thiếu doc (#75 đang probe) | TB |
| Broken-profile DP | P/★req | Grid frontier recolor | (#74 đang probe) | TB |
| CHT / Li Chao | P/★req | Plane2D lines + point-query | envelope-winner không auto (#72 đang probe) | TB |
| **DP-value-as-bar / histogram DP** | **G/★req** | — | **kênh chiều cao** (P4); #73 đang probe | cao |

→ Bar-height (#73) và CHT (#72) **đang được kéo vào request** — trùng census độc lập này.

### 4.7 Data structures (khác)
| Chủ đề | Phủ | Primitive | Gap | Coverage |
|--------|:---:|-----------|-----|:--------:|
| Monotonic stack/deque (cấu trúc) | C | Stack / Deque, 0.24.0 | — | cao |
| Monotonic stack **trên cột chiều cao** | **G** | (heights vẽ bằng chiều cao) | **kênh chiều cao** (P4) | cao |
| **Treap / splay / AVL / cartesian tree** | **P** | Tree `reparent` (teleport) | **rotation glide** (xoay pivot mượt) | TB–thấp |
| Link-cut tree | P | Tree + `links` | preferred-path/access phức tạp | thấp (YAGNI) |
| Wavelet tree | R | Tree + Array mỗi tầng | thiếu doc | thấp |
| Persistent (segtree/array versioned) | P/R | nhiều shape song song | không có kênh version-diff | thấp–TB |
| Mo's algorithm | R | Array + 2 cursor | thiếu doc | TB |

→ **Gap thật: rotation glide** (treap/BBST); bar-height trùng monotonic-stack-on-heights.

---

## 5. Top gap NGOÀI request — xếp theo coverage (real-gap trước)

| # | Gap | Loại | Bao nhiêu bài / họ điển hình | Thiếu gì | Machinery ước lượng |
|---|-----|:----:|------------------------------|----------|---------------------|
| **1** | **Kênh giá-trị-thành-chiều-cao (bar/histogram động)** | **G** | Largest-rectangle-in-histogram, monotonic-stack-on-heights, trapping-rain-water, skyline, **sorting-as-bars** (idiom nổi tiếng nhất), counting/frequency bars, DP-value-as-height | Primitive mã hoá scalar → chiều cao cột, cập nhật động + glide | Primitive mới `BarChart`/`Histogram`, hoặc `mode="bar"` cho MetricPlot. **M** (~400–450 LOC theo baseline gap-new-substrates §2.4). **⚠ #73 đang probe** |
| **2** | **Motion quay / theo góc** | **G/P** | Rotating calipers, angular/radial sweep, angular sort (convex hull), xoay vector/hình học, "pivot the line" | `move_line` nhận slope-target + `rotate_segment/point{center,deg}` glide, hoặc verb `\rotate` chung | Mở rộng motion trên Plane2D (element giữ danh tính sẵn). **M**. Chưa ai đụng |
| **3** | **Toạ độ node thủ công cho Graph** | **G** | FFT butterfly, graph hình-học (điểm ở toạ độ thật), planar embedding, bipartite có back-edge, mạng phân tầng tuỳ biến | Param `positions={id:(x,y)}` bỏ qua layout engine | `pos` đã là dict nội bộ (`graph.py:447`); chỉ cần expose param + validate. **S–M**. Chưa ai đụng |
| **4** | **Matrix row/col-op glide** | **P** | Gaussian elimination, RREF, row-reduction, hoán vị hàng ma trận | `reorder`/`swap_rows` cho Matrix (đúng như Array `reorder` §7.1) | Port motion `reorder` sang Matrix. **S**. Chưa ai đụng |
| **5** | **Rotation glide cho cây (treap/BBST)** | **P** | Treap, splay, AVL, red-black, cartesian tree | `rotate={node,dir}` (sugar trên `reparent` + glide pivot) | Sugar + motion trên Tree. **S–M**. Chưa ai đụng |
| **6** | **CHT / Li-Chao lower-envelope** | **P/R** | Convex hull trick, Li Chao, kinetic | Envelope-winner auto-highlight (giờ author tự tính) | Chủ yếu doc + helper nhỏ. **S**. **⚠ #72 đang probe** |
| **7** | **Persistent / multi-version diff view** | **P/R** | Persistent segtree/array, version tree | Kênh so-version (giờ dựng bằng nhiều shape) | Recipe-nặng. **S–M** nếu build. Coverage thấp |

**Ba gap load-bearing chưa ai đụng: #2 (quay/góc), #3 (toạ độ thủ công/butterfly), + phần chưa-vào-request
của #1 (bar-height, dù #73 đang tới).** #4/#5 là port motion rẻ. #6 gần như chỉ-doc.

---

## 6. Recipe được (chỉ thiếu DOC, KHÔNG build) — đã kiểm/để đối chiếu

Bipartite 2-cột (P2) · Gantt/interval-lane (P3) · Fenwick/BIT · LCA table · Eulerian · min-cut ·
half-plane (author tính polygon) · rolling hash · Mo's · wavelet · centroid · HLD · matrix-expo ·
digit DP. → Nhóm này KHÔNG phải gap năng lực; đưa vào cookbook là đủ.

## 7. YAGNI (hiếm trong editorial CP — đừng build vội)

Planar embedding (layout khó, hiếm) · Voronoi/Delaunay incremental-flip (hiếm) · link-cut tree
(rất nâng cao, hiếm) · persistent diff-view (thấp). Có thể để cho recipe/parital khi cần.

---

## 8. Ước lượng % phủ

Liệt kê ~51 họ bài được animate phổ biến (§4). Phân loại: **~38 phủ hẳn (C/R)** ≈ 75% *ngay hôm nay*;
**~6 đang trong request** (KMP, Manacher, digit, broken-profile, CHT, bar-height — Tier D + #72–76);
**~6 gap/partial thật ngoài request** (butterfly, graph-hình-học/planar, quay-góc/calipers, matrix-row-glide,
treap-rotation, persistent) — trong đó ~3 load-bearing. Voronoi/link-cut = đuôi YAGNI.

- **Hôm nay (0.24.0):** ~75% phủ *đúng dạng idiom*.
- **Sau Tier D + bó #72–76 hạ cánh:** **~85%**.
- **Residual ~15%** dồn vào đúng ba trục scriba không có: **chiều cao-giá trị**, **quay-góc**, **toạ độ
  thủ công** — cộng đuôi YAGNI. Không có họ bài "phổ biến-và-hoàn-toàn-không-vẽ-được" nào ngoài ba trục này.

---

## 9. Kết luận + Độ tin cậy

**Kết luận:** Sau Tier D, scriba **không còn họ bài phổ biến nào bị bỏ trắng** — ~85% kiểu hình CP vẽ
được đúng dạng, phần lớn phần còn lại chỉ thiếu **doc-recipe**. Ba gap THẬT cần build, xếp theo coverage
và đều **ngoài mọi request hiện tại**: **(1) kênh chiều cao = giá trị** (bar/histogram — coverage cao
nhất, nhưng #73 vừa bắt đầu kéo vào request), **(2) motion quay/theo góc** (calipers/angular sweep —
chưa ai đụng), **(3) toạ độ node thủ công cho Graph** (FFT-butterfly/planar/graph-hình-học — chưa ai
đụng, machinery rẻ nhất vì `pos` đã là dict nội bộ). Hai "ứng viên" mà team nghi (bipartite layout,
Gantt) hoá ra **recipe được** — đã render kiểm chứng, chỉ cần cookbook. Đề xuất ưu tiên build:
**#3 (S–M, unlock butterfly + planar + geometric)** rẻ nhất-đổi-nhiều-nhất; **#1 (M)** nếu muốn idiom
sorting/histogram kinh điển; **#4/#5 (S)** là port motion `reorder`/rotation rẻ. YAGNI: planar-auto,
Voronoi, link-cut.

**Độ tin cậy:** **Cao** cho ba gap thật — mỗi cái có bằng chứng executed (E1467 render; ACCEPTED_PARAMS
đọc thẳng; MetricPlot polyline-only) *và* tham chiếu doc. **Trung bình-cao** cho con số ~85% (phụ thuộc
cách đếm "họ bài" và định nghĩa "đúng idiom" — biên độ ±5–7%). **Trung bình** cho xếp hạng coverage của
#4–#7 (ước lượng số bài, chưa đo trên tập đề thật). Chưa build/verify bất kỳ primitive/motion đề xuất
nào — toàn bộ §5 machinery là **[Hypothesized]**.

---

## Phụ lục — Probe files (scratchpad/td-census/)

`rotate_line.tex` (E1467) · `bipartite.tex` (2 cột) · `gantt.tex` (segment-lane) · `barheight.tex`
(text+polyline, không cột). Grep: `graph.py:721-736` (no positions) · `metricplot.py:127-139,417,605`
(line-only) · commands (không `rotate`).
