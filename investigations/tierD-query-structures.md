# Gap · Nhóm cấu-trúc-truy-vấn — Persistence · Sparse-table 2^k · 2D-Fenwick · BST-rotation/Order-statistics

**Investigation ID**: `tierD-query-structures`
**Ngày**: 2026-07-05 · scriba **0.24.0** (main @ `e185786`)
**Ràng buộc**: CHỈ điều tra — **không sửa source, không commit**.
**Probes**: `scratchpad/td-struct/*.tex` → render vào `.scriba_tmp/td-struct/` (đã gitignore).
**Grading**: `[Confirmed]` = chạy/đọc source phiên này · `[Deduced]` = suy ra từ source · `[Hypothesized]` = chưa kiểm.

---

## 1. Hand-off Brief (4 câu)

1. **Cả 4 mục lên hình được bằng bề mặt 0.24.0 hôm nay** — không mục nào cần máy-mới chỉ để render.
2. **Sparse-table 2^k** và **2D-Fenwick** là **RECIPE thuần**: DPTable-2D + `\annotate{arrow_from}` cho mũi tên "nhảy 2^k", và Matrix `block[..][..]` recolor+bracket cho vùng lowbit — chưa có editorial trong corpus nhưng đã chứng minh dựng được (render + kiểm SVG).
3. **BST-rotation KHÔNG phải recipe-sạch như nghi ban đầu**: glide (`position_move`) đã ship và đã dùng trong **2 example golden** (`splay.tex`, `bst_operations.tex`), NHƯNG `reparent` **luôn nối con vào cuối (phải nhất)** nên mỗi phép xoay **đặt sai bên đúng một node** — bug đang tồn tại trong chính 2 example đã ship → cần **MỞ-RỘNG nhỏ** (reparent có `index`/`side`).
4. **Persistence version-tree** đã **RECIPE-COVERED** cho editorial chuẩn (2 example ship: `persistent_segtree.tex`, `range_queries_copies.tex` — 1 segtree + recolor + value-layer, "chia sẻ" kể bằng màu/narrate); còn **shared-node vật lý / version-DAG cùng tồn tại** là câu hỏi **CẦN-EDITORIAL** (dựng được bằng Graph-DAG hand-build; primitive first-class mới là MÁY-MỚI).

---

## 2. Bằng chứng executed (probe phiên này) **[Confirmed]**

Tất cả 6 probe render **0 error**:

| Probe | File | Kết quả then chốt |
|---|---|---|
| BST right-rotate (non-root) | `bst_rotate.tex` | 3 `reparent` chạy OK; node glide qua `position_move` |
| Sparse-table RMQ doubling | `sparse_table.tex` | `arrow_from` vẽ **arc thật** + nhãn `jump 2^0/2^1/2^2`; SVG có `annotation-arrow`, `arc`, `arrowhead`, `marker-end` |
| 2D-Fenwick (Matrix block) | `fenwick2d_matrix.tex` | `\recolor{m.block[4:6][0:4]}` **nở ra đúng 8 cell** `m.cell[4..5][0..3]` state=current + `bracket` "responsible 2x4" |
| 2D-Fenwick (Grid per-cell) | `fenwick2d_grid.tex` | recolor 8 cell rời — được, nhưng **Grid không có block selector** (chỉ `g.cell[r][c]`, `g.all`) |
| Persistence Graph-DAG | `persist_graph_dag.tex` | DAG 10 node; `b` & `L0` **in-degree 2 = shared thật**; `\group` hull render trên Graph |
| Persistence multi-Tree | `persist_multitree.tex` | V0 full-tree + V1 path-tree + **2 `\link` bridge** cross-shape vẽ được |

**Chứng minh bug child-order bằng chính `_reingold_tilford` của project** (layout dùng thứ tự list `children_map[node]` để xếp trái→phải; `tree_layout.py:100`):

- Probe rời (right-rotate `x` tại `y`): mong muốn `y:[B,C]` (B trái) nhưng reparent cho `y:[C,B]` → **B x=370 (phải), C x=200 (trái) — ĐẢO bên**.
- Trên chính **`bst_operations.tex`** (golden): sau xoay, node `8` có con `[9,11]` → **9 x=257 (trái), 11 x=370 (phải)**; nhưng narrate dòng 162 khẳng định `8(11,9)` và in-order `10,7,11,8,9`. Render thật cho in-order `10,7,9,8,11` → **mâu thuẫn narrate, phá bất biến BST**.

Nguồn gốc (source, `[Confirmed]`):
- `tree.py:660-662` — reparent **append** node vào cuối `children_map[new_parent]` (không có tham số vị trí).
- `tree.py:613-619` — reparent **root → E1433** ("cycle (root node)"): **không xoay được tại gốc thật** (phải dùng sentinel super-root).
- `differ.py:245` `kind="position_move"` — relayout sau mutation **tự phát glide** (miễn phí cho mọi phép xoay).

---

## 3. Bảng phân loại (Conclusion + Confidence)

| # | Mục | Phân loại | Confidence | Cost |
|---|---|---|---|---|
| 1 | **Sparse-table 2^k** (RMQ doubling) | **RECIPE** (hôm nay) | **HIGH** | 0 — chỉ viết editorial |
| 2 | **2D-Fenwick** (vùng lowbit) | **RECIPE** (Matrix `block`) | **HIGH** | 0; thêm Grid `block` = MỞ-RỘNG vặt |
| 3 | **Order-statistics** (rank/size overlay) | **RECIPE** (value-layer) | **HIGH** | 0 |
| 3′ | **BST/AVL/splay rotation** (motion) | **MỞ-RỘNG nhỏ** (child-order reparent) | **HIGH** | ~20-40 LOC `tree.py` + test/doc |
| 4 | **Persistence** — editorial copy-on-write | **RECIPE** (đã ship, "Covered") | **HIGH** | 0 |
| 4′ | **Persistence** — shared-node/version-DAG vật lý | **CẦN-EDITORIAL** (Graph dựng được; primitive = MÁY-MỚI) | **MED** | quyết định trước |

---

## 4. Mục 1 — Sparse-table 2^k (RMQ doubling) → **RECIPE** **[Confirmed]**

**Model**: DPTable-2D `rows=k (tầng), cols=i (chỉ số đầu)`, `cell[k][i] = min` trên `[i, i+2^k-1]`. Đệ quy: `sparse[k][i] = min(sparse[k-1][i], sparse[k-1][i+2^{k-1}])`.

**Dựng bằng gì**: `\apply{dp.cell[k][i]}{value=…}` để điền; **hai** `\annotate{dp.cell[k][i]}{arrow_from="dp.cell[k-1][i]"}` và `{arrow_from="dp.cell[k-1][i+2^{k-1}]"}` cho hai phụ thuộc. Mũi tên thứ hai **span ngang đúng 2^{k-1} cột** — chính là hình ảnh "nhảy 2^k". Nhãn `jump 2^k` đặt trên pill.

**Bằng chứng**: `sparse_table.tex` render arc + nhãn `jump 2^0/2^1/2^2` (SVG xác nhận). Đây đúng idiom "DP recurrence arrow" mà DPTable-2D hỗ trợ sẵn (§7.3, `arrow_from`).

**Truy vấn `[L,R]`**: `k=⌊log2(R-L+1)⌋`, gộp `sparse[k][L]` và `sparse[k][R-2^k+1]` (hai đoạn phủ chồng). Highlight bằng 2 `\recolor` + `\trace` hoặc 2 `arrow_from`.

**Conclusion**: RECIPE thuần, **không cần code**. Chỉ thiếu **editorial mẫu** trong corpus (hiện chưa có sparse-table doubling; `cookbook/05-sparse-segtree-lazy` là sparse *segment tree*, khác). **Confidence: HIGH.**

---

## 5. Mục 2 — 2D-Fenwick (BIT 2 chiều) → **RECIPE** **[Confirmed]**

**Model**: lưới `n×n`; ô `(i,j)` "phụ trách" hình chữ nhật `(i-lowbit(i), i] × (j-lowbit(j), j]`.

**Dựng bằng gì (khuyến nghị Matrix)**: `\recolor{m.block[r0:r1][c0:c1]}{state=current}` + `\annotate{m.block…}{bracket=true}`. Probe xác nhận **block nở ra từng cell** (`m.block[4:6][0:4]` → 8 cell `m.cell[4..5][0..3]`), nên vùng lowbit tô đúng như một khối, có viền bracket. `update(i,j)` nhảy `i += lowbit(i)` / `j += lowbit(j)`: minh hoạ bằng chuỗi block-recolor + `\trace`/`arrow_from` giữa các ô đại diện.

**Grid vs Matrix**: **Grid KHÔNG có block selector** (`fenwick2d_grid.tex` phải recolor 8 cell rời — được nhưng dài dòng). Matrix có `block` (§7.7) → ưu tiên Matrix; nếu tác giả muốn Grid "không heatmap", thêm `g.block[..][..]` là **MỞ-RỘNG vặt** (copy selector từ Matrix), không bắt buộc.

**Conclusion**: RECIPE qua Matrix `block`. **Confidence: HIGH.** Lưu ý nhỏ: Matrix là heatmap (fill theo value) — với BIT nên `show_values=false` và điều khiển màu bằng `state` (probe cho thấy state override hoạt động).

---

## 6. Mục 3 — Order-statistics + BST rotation

### 6.1 Order-statistics (rank/select, subtree-size) → **RECIPE** **[Confirmed]**
Hiển thị `size[node]` để rank/select = **value-layer overlay**: `\apply{T.node[id]}{value="sz=3"}` (§7.5 nói rõ value-layer **sống sót qua reparent/add_node**, đúng kênh dùng cho subtree-size DP). Đường tìm kiếm rank = recolor path. Không cần code. **Confidence: HIGH.**

### 6.2 BST/AVL/splay **rotation** (motion) → **MỞ-RỘNG nhỏ** **[Confirmed]**

**Cái đã có (recipe-hôm-nay, đã ship)**: xoay = chuỗi `reparent`; relayout Reingold-Tilford + `position_move` cho node **glide thật** (không tô-màu-giả). `splay.tex` (zig-zig) và `bst_operations.tex` (right-rotation) đều dùng đúng pattern này và tự khẳng định "node thực sự dịch chuyển". Catalog `HARD-TO-DISPLAY.md:124` cũng ghi *"Rotations themselves are animatable (Tree primitive handles this fine)"*.

**Cái CÒN THIẾU (điểm mới của điều tra này)**: `reparent` **luôn append con vào phải nhất** → node "đáng lẽ thành con TRÁI" lại rơi sang PHẢI. Mỗi phép xoay đảo sai đúng một node; **hai example golden hiện đang render sai bên** so với chính narrate của chúng (mục 2). Không có recipe-workaround nào giữ được glide: khai báo lại cây mỗi frame → teleport (mất identity); `remove+add` cũng append. Vậy để **xoay đúng bên mà vẫn glide** cần code.

**Ràng buộc phụ**: `reparent` root → **E1433** → xoay tại gốc thật phải dùng **sentinel super-root** (đã kiểm; probe non-root chạy OK).

**Đề xuất MỞ-RỘNG (surgical)**:
- `reparent={node, parent, index=k}` hoặc `side="left"|"right"` — chèn vào vị trí thay vì append. Điểm chạm: `tree.py:_reparent_internal` (dòng append 660-662) + parse spec (~385-392); index ngoài range → clamp + warning (không cần E-code mới). Glide **miễn phí** (đã có `position_move`).
- (tuỳ chọn) cho `add_node` cùng tham số `index` để dựng cây có thứ tự trái/phải đúng ngay từ đầu.
- **Cost ~20-40 LOC** + test + 1 dòng doc §7.5. **ROI cao**: vá bug đang có trong 2 golden, mở khoá AVL/RB/Treap rotation trung thực.

**Conclusion**: glide = recipe-hôm-nay; **xoay-đúng-bên = MỞ-RỘNG nhỏ**. **Confidence: HIGH** (chứng minh bằng layout-fn của project + 2 example ship).

---

## 7. Mục 4 — Persistence version-tree

### 7.1 Editorial copy-on-write (chuẩn) → **RECIPE, đã COVERED** **[Confirmed]**
2 example ship: `persistent_segtree.tex` và `cses/range_queries_copies.tex`. Cách làm: **một** segtree (`kind=segtree`), kể chuyện path-copy bằng **recolor states** (`current`=path mới, `good`=node mới "sở hữu", `dim`=node **chia sẻ**) + **value-layer** cho tổng mới. `HARD-TO-DISPLAY-COVERAGE.md:22` đánh dấu **"Covered"**.

**Giới hạn (kể, không show)**: chỉ thấy **một hình cây** tại một thời điểm; V0/V1/V2 **không cùng hiện** cạnh nhau; "shared node" là **màu + narrate**, không phải một node vật lý thuộc hai cây.

### 7.2 Shared-node vật lý / version-DAG cùng tồn tại → **CẦN-EDITORIAL** **[Confirmed dựng được]**
Đây là phần "khó" team-lead nghi (structural sharing). **Dựng được hôm nay, không cần máy-mới**, theo 2 đường:
- **Graph-DAG** (`persist_graph_dag.tex`): liệt kê mọi node vật lý qua các version + mọi con-trỏ; root V1 trỏ vào subtree V0 → `b`, `L0` **in-degree 2 = chia sẻ thật, vẽ 1 lần**. `\group` bọc từng version. Render OK. **Giá**: hand-enumerate (q update → +3q node), layout `hierarchical` **generic — không canh tầng theo range như segtree**, không scale.
- **Multi-Tree + `\link`** (`persist_multitree.tex`): mỗi version một Tree; `\link` bắc cầu vào subtree chia sẻ. Render 2 bridge OK. **Giá**: "chia sẻ" là mũi tên tham chiếu, node vẫn vẽ 1 lần **mỗi cây** (không phải 1 node trong 2 layout).

**Câu hỏi editorial (cần team quyết)**:
1. Editorial recolor-trên-1-segtree (đã ship, "Covered") **đã đủ** cho persistent segtree chưa? Nếu đủ → **đóng**, chỉ thêm sparse-table/fenwick.
2. Nếu muốn **thấy structural-sharing vật lý** (Chairman-tree, wavelet, version-DAG rollback): chấp nhận **Graph-DAG hand-build** (rẻ, xấu layout) hay đầu tư **primitive `VersionDAG`/`PersistentTree`** (layout canh tầng + auto path-copy = **MÁY-MỚI**, đắt)?

**Conclusion**: RECIPE cho editorial chuẩn; **CẦN-EDITORIAL** cho sharing vật lý. **Confidence: HIGH** (render được) / **MED** cho hướng nên đi (phụ thuộc quyết định biên tập).

---

## 8. Thứ tự đề xuất theo ROI

1. **Sparse-table + 2D-Fenwick** — cost 0, chỉ viết editorial mẫu. **ROI cao nhất**, làm ngay.
2. **child-order reparent** (mục 3′) — MỞ-RỘNG ~20-40 LOC, **vá bug 2 golden đang render sai bên**, mở AVL/RB/Treap trung thực. ROI cao, rủi ro thấp (thay đổi cục bộ + `position_move` sẵn có).
3. **Persistence sharing vật lý** (4′) — **quyết định editorial trước**; nếu chỉ cần dạy copy-on-write thì đã xong; primitive first-class defer.

---

## 9. Open questions / dependencies

- **[Editorial]** Persistent segtree: recolor-story đã đủ hay cần version-DAG vật lý? (chặn mục 4′).
- **[Design]** child-order reparent: chọn `index=k` (tổng quát) hay `side="left|right"` (đọc dễ cho nhị phân)? Đề xuất **`index`** (tổng quát, cây bậc >2) + tài liệu ví dụ nhị phân.
- **[Nhỏ]** Có nên copy `block` selector sang Grid để 2D-Fenwick không phải mượn Matrix-heatmap? (MỞ-RỘNG vặt, optional).
- **[Xác nhận]** Sentinel super-root cho xoay-tại-gốc: nên thành **idiom tài liệu hoá** trong §7.5 (kèm cảnh báo E1433), không cần code.

---

## Phụ lục — Probe artifacts (không commit)

`scratchpad/td-struct/`: `bst_rotate.tex`, `sparse_table.tex`, `fenwick2d_matrix.tex`, `fenwick2d_grid.tex`, `persist_graph_dag.tex`, `persist_multitree.tex`.
Render: `.venv/bin/python render.py <probe> -o .scriba_tmp/td-struct/<x>.html [--dump-frames]`.
Golden liên quan (đọc, không sửa): `examples/algorithms/tree/{splay,bst_operations,persistent_segtree}.tex`, `examples/cses/range_queries_copies.tex`, `docs/cookbook/HARD-TO-DISPLAY{,-COVERAGE}.md`.
