# Gap: Inert Primitives — thao tác nhỏ trên primitive có sẵn (A1 / A2 / A3 / C2)

> BMAD case file. Evidence grade: **Confirmed** (có `path:line`) · **Deduced** (suy ra từ code đã đọc) · **Hypothesized** (chưa kiểm chứng bằng test/repro).
> HEAD tại thời điểm điều tra: `bf1bbf6` (commit vừa thêm `block[r0:r1][c0:c1]` cho Matrix).
> Phạm vi: chỉ các op NHỎ trên primitive ĐÃ TỒN TẠI. Không code, không sửa file nào ngoài case file này.

---

## Hand-off Brief (3 câu)

1. **Ba trong năm "gap" thực chất đã ship hoặc gần như miễn phí**: A1 (`\apply{tree.node}{value=...}`) chạy end-to-end hôm nay qua kênh value-layer generic (tree.py:722 ↔ scene.py:787 ↔ _frame_renderer.py:847), A3 lazy-tag dạng chữ dùng chính kênh đó, và C2 nhãn `f/c` mutable đã có sẵn (graph.py:1468 + `split_labels` graph.py:1602-1629) — cả ba chỉ thiếu **docs + golden test**, không cần verb/kind mới.
2. **Hai gap thật sự cần code là hình học**, không phải ngữ nghĩa: C2 cạnh antiparallel cong-lệch (graph.py vẽ `<line>` thẳng, hai cạnh đè nhau — M) và A2a `diag` (không biểu diễn được bằng `block` chữ nhật — S-M); còn `row[i]`/`col[j]` chỉ là **sugar** đặt đúng chỗ tại `_expand_selectors` (_frame_renderer.py:377-454).
3. **A2b là bẫy generality**: claim "`\recolor` đổi stroke thôi" **được xác nhận**, nhưng gap sâu hơn — Matrix còn không đổi được *value* ô (matrix.py:254); ma trận-lũy-thừa/Gauss/XOR-basis **không phải heatmap** nên câu trả lời đúng là dùng **Grid/DPTable** (fill do state sở hữu + value mutable sẵn), KHÔNG bơm fill-override vào Matrix (xung đột A-0.v + R-36 + matrix.md:413).

---

## Problem Statement

JudgeZone gửi feature-request pass 3: nhóm "inert primitives" — primitive tồn tại nhưng **thao tác định nghĩa hành vi của nó không diễn đạt được** trong ngôn ngữ lệnh (~18 lệnh). Bốn cụm:

- **A1 · Tree `set_node_value` (~26 bài)**: tree-DP overlay + rerooting cần đổi *value hiển thị* của node. Claim: `apply_command` chỉ add/remove/reparent nên bất khả.
- **A2a/A2b · Matrix `row[i]`/`col[j]`/`diag` + fill-recolor (~14 bài)**: M→M²→M⁴, Gauss, XOR linear basis cần atomic step = row/col; claim `\recolor` chỉ đổi stroke.
- **A3 · Segtree lazy-tag + `\pushdown` (~4 CSES + ~18 USACO)**: node segtree = scalar label, không có field tag thứ 2, không kênh parent→child.
- **C2 · Flow residual edges (~11-13 bài)**: cạnh forward + residual đè nhau thành 1 `<line>` thẳng; cần cong/lệch antiparallel + nhãn `f/c` mutable + layout 2 cột.

Ràng buộc kiến trúc (motion-ruleset): mọi motion phải là hàm thuần của **diff identity** (A-1), `kind` rút từ **registry đóng, đóng kín dưới nghịch đảo** (A-2), màu là **class-ref chứ không phải màu** (A-0.v), và tính năng là **additive/opt-in byte-stable** (A-0.vi). Mỗi verb mới = chi phí docs + parser + motion, nên ưu tiên mở rộng `\apply`/`\recolor` có sẵn.

---

## Evidence Inventory

### Kênh value-layer generic (nền tảng của A1, A3, C2-nhãn)

| Mắt xích | Vị trí | Grade |
|---|---|---|
| `\apply` tách `value=` khỏi params, lưu vào `target_state.value` | scene.py:787-788, 817-824 | **Confirmed** |
| `\apply` chuyển mọi `k=v` khác (trừ value/label) vào `apply_params` | scene.py:794-801 | **Confirmed** |
| Emit thật gọi `prim.set_value(suffix, val)` cho mọi target có value | _frame_renderer.py:845-847 | **Confirmed** |
| `set_value`/`get_value` generic, validate qua `validate_selector` | base.py:366-379 | **Confirmed** |
| Differ sinh `value_change` khi `prev_val != curr_val` | differ.py:181-192 | **Confirmed** |
| Runtime `value_change`: tìm `<text>` dưới `[data-target]`, set `textContent` + scale-pulse | scriba.js:149-161 (:157 textContent) | **Confirmed** |
| Registry kind ĐÓNG, `value_change` tự-nghịch qua swap from/to | motion-ruleset A-2:59-74; scriba.js:326-332 | **Confirmed** |
| Reduced-motion/snap: SVG server lúc nghỉ đã là đích (A-8) | scriba.js:367,387-389,430 | **Confirmed** |

### Selector expansion (nền tảng của A2a)

| Sự kiện | Vị trí | Grade |
|---|---|---|
| `block[r0:r1][c0:c1]` → tích ô `cell[r][c]` tại emit, generic mọi primitive | _frame_renderer.py:377-454 (nhánh block :420-426) | **Confirmed** |
| `resolve_effective_state` KHÔNG mở rộng block (chỉ merge highlight) | base.py:1052-1061 | **Confirmed** |
| Dispatch là chuỗi `if/elif` inline (range/block/all/top), không phải bảng dữ liệu | _frame_renderer.py:390-452 | **Confirmed** |
| Parser: `\apply` cho `value=` + `k=v` tùy ý đi qua; `\recolor` CHỈ nhận `state`/`color` | _grammar_tokens.py:262-265; _grammar_commands.py:93-101, 132-185 | **Confirmed** |
| `block` là selector hạng nhất (accessor), parser không biết primitive nên không biết C/R | selectors.py:100-124, 175-186; _grammar_commands.py:93-101 | **Confirmed** |
| Không tồn tại `row`/`col`/`diag` accessor ở bất kỳ đâu | grep toàn `scriba/animation/` (Agent) | **Deduced** |

### Matrix (A2a/A2b)

| Sự kiện | Vị trí | Grade |
|---|---|---|
| Fill ô luôn = `interpolate_color(t, stops)` (literal colorscale) | matrix.py:490, 506 | **Confirmed** |
| State class chỉ sở hữu stroke/stroke-width, "fill CANNOT be owned by CSS" | matrix.py:485-489 | **Confirmed** |
| Không có set_value path; data tĩnh | matrix.py:254 | **Confirmed** |
| Emit luôn đọc `self.data[r][c]` / `_format_value(val)`, không đọc `get_value` | matrix.py:478, 516 | **Confirmed** |
| `block` mới chỉ vào validate + annotation resolver, KHÔNG vào emit state | matrix.py:296-302, 313-326, 365-380 | **Confirmed** |
| Doc: state = **border-stroke only**, "colorscale fill is never overridden by state classes" | docs/primitives/matrix.md:342-344, 413 | **Confirmed** |
| Doc claim `\apply{m.cell}{value=0.7}` cập nhật value + recompute fill (DRIFT — code không có path) | docs/primitives/matrix.md:264-268 vs matrix.py:254,516 | **Confirmed (conflict)** |
| `row[i]`/`col[j]` được liệt kê là "planned/unwired" trong doc Matrix | docs/primitives/matrix.md:244-245 | **Confirmed** |

### Grid / DPTable (đối chứng cho A2b)

| Sự kiện | Vị trí | Grade |
|---|---|---|
| Grid emit đọc `get_value` override (như tree.py:722) | grid.py:333 (fallback :334-336) | **Confirmed** |
| Grid rect KHÔNG có `fill` → nền do class `scriba-state-*` sở hữu (recolor đổi được nền) | grid.py:351-355; _types.py:148-149 | **Confirmed** |
| DPTable đọc `get_value` (1D :442, 2D :506); rect không fill (:455-459, :524-528) | dptable.py | **Confirmed** |
| DPTable có `block` + `range`; cả hai đều thiếu `row`/`col` | dptable.py:71-77, 79; grid.py:89-95 | **Confirmed** |
| Runtime KHÔNG bao giờ ghi `fill` (không `setAttribute('fill')`/`.style.fill`) | scriba.js Part-1 Q3 (grep toàn file) | **Confirmed** |

### Tree / Segtree (A1/A3)

| Sự kiện | Vị trí | Grade |
|---|---|---|
| `apply_command` chỉ add_node/remove_node/reparent | tree.py:232-271 | **Confirmed** |
| Node emit: value-layer override đè label tĩnh; comment ghi rõ phục vụ `\apply{T.node["X"]}{value=...}` | tree.py:719-727 | **Confirmed** |
| Node emit MỘT `<text>` + MỘT `<circle>` (không có field/badge thứ 2) | tree.py:736-759 | **Confirmed** |
| Segtree label = `str(node_id)` (+ optional sum), scalar | tree.py:200-205 | **Confirmed** |
| `_values` là 1 chuỗi/suffix (một slot value duy nhất mỗi target) | base.py:375 | **Confirmed** |

### Graph (C2)

| Sự kiện | Vị trí | Grade |
|---|---|---|
| Cạnh vẽ `<line>` thẳng center→center trong 1 vòng lặp | graph.py:1428-1681 (emit :1669-1680) | **Confirmed** |
| Không có logic cong/lệch/antiparallel; forward+residual giữ 2 tuple riêng nhưng ĐÈ cùng đoạn | graph.py:1084-1088 (distinct), :1437-1438 (cùng tọa độ) | **Confirmed** |
| Arrowhead qua `<marker>`; đã có sẵn marker `scriba-arrow-rev` CHƯA dùng | graph.py:1457, 1675; _frame_renderer.py:358-363 | **Confirmed** |
| Nhãn cạnh mutable qua `value=` (đọc `get_value`); `label=` bị bỏ qua khi emit | graph.py:1465-1474 (:1468 get_value) | **Confirmed** |
| Sẵn `split_labels` render "3/5" bold/dim + `tint_by_edge` tô pill theo state | graph.py:1602-1629, 1594-1595 | **Confirmed** |
| Không có layout bipartite; gần nhất là hierarchical `orientation="LR"` | graph_layout_hierarchical.py (LR :230,235-237); graph.py:647-662 | **Confirmed** |

---

## Phân tích từng item

### A1 · Tree `set_node_value` — VERDICT: **KHÔNG PHẢI GAP (đã ship)**. Chỉ thiếu docs + test. Cost **S**.

**Evidence → bác claim.** Claim "không đổi được value hiển thị của node" **sai**. `apply_command` (tree.py:232-271) đúng là chỉ lo cấu trúc, NHƯNG value hiển thị đi qua kênh **khác, generic**, không qua `apply_command`:

`\apply{T.node[5]}{value="dp=7"}` → scene.py:787-788 lưu `value` vào `target_state.value` → _frame_renderer.py:845-847 gọi `prim.set_value("node[5]", "dp=7")` → base.py:375 lưu `_values["node[5]"]` → tree.py:722 `override = self.get_value(...)` đè `display_label` → render `<text>` (tree.py:736-748). Comment tại tree.py:720-721 nói thẳng: *"Wave 6 Agent 7 F1 CRITICAL fix — enables segtree sum updates via `\apply{T.node["X"]}{value="..."}`"*. **Confirmed** end-to-end.

- `validate_selector("node[5]")` pass vì `node[5]` ∈ `addressable_parts()` (tree.py:521-527, 529-532). **Confirmed**.
- Rerooting: `reparent` đã tồn tại (tree.py:411-476) → đổi cạnh + value cùng lúc = tree-DP rerooting biểu diễn được ngay. **Deduced**.

**Thiết kế.** Không cần API mới. Value **thay toàn bộ** label; muốn hiện "id + dp" thì tác giả gói trong chuỗi value (`value="5 · dp=7"`). Đủ tổng quát.

**Motion.** `value_change` (differ.py:181-192) → scriba.js:157 set `textContent` + scale-pulse (:159-160, đây chính là proto-emphasis A-3). **Inverse**: `value_change` tự-nghịch qua swap from/to (scriba.js:327-332) → reverse/jump chạy sẵn. Không kind mới. Với value dạng `$math$`: scriba.js:152-156 bỏ qua tween text (KaTeX là `foreignObject`) nhưng lúc nghỉ SVG server vẫn đúng (A-8, scriba.js:387-389). **Confirmed**.

**Cost S** — chỉ viết docs (mục "mutate node value") + golden test cho Tree (test cho segtree-sum đã dùng chính path này). Đây là đòn bẩy lớn nhất: mở khóa ~26 bài với gần-0 dòng code.

---

### A3 · Segtree lazy-tag + `\pushdown` — VERDICT: **SPLIT**. Tag-dạng-chữ FREE (S); badge có cấu trúc (M, hoãn); `\pushdown` **KHÔNG thêm verb**.

**(a) Lazy-tag dạng chữ — FREE hôm nay (Cost S, docs/test).**
Node segtree tôn trọng value override (tree.py:722), nên `\apply{st.node["[0,7]"]}{value="12 (+3)"}` hiện sum + tag ngay bây giờ. **Confirmed** (cùng cơ chế A1). Đủ cho phần lớn minh họa lazy-propagation.

**(b) Badge có cấu trúc (field thứ 2 tách biệt) — Cost M, đề nghị HOÃN.**
Node hiện emit đúng MỘT `<text>` + MỘT `<circle>` (tree.py:736-759), và `_values` chỉ 1 slot/suffix (base.py:375) → không có chỗ cho field-2 tách biệt. Muốn badge riêng cần **sub-part addressable mới** `node[id].tag` (thêm vào `addressable_parts` + emit `<text>`/pill nhỏ thứ 2). Nó **cưỡi kind có sẵn**: `value_change` cho chữ tag, `element_add/remove` cho badge xuất/ẩn — KHÔNG kind mới, inverse đóng kín. Chỉ dựng nếu corpus chứng minh tag-dạng-chữ không đủ.

**(c) `\pushdown` — KHÔNG phải verb mới. Là sugar trên `\apply`.**
Ngữ nghĩa pushdown = (i) xóa tag ở cha (value→sum-only) + (ii) đặt tag vào 2 con + (iii) cập nhật sum 2 con = **3 `\apply` value-change trong 1 `\step`**. Tác giả viết trực tiếp (hoặc `\foreach` 2 con). Thêm verb `\pushdown` = chi phí docs+parser+scene cho pure sugar, nghịch với ethos additive (motion-ruleset A-0.vi:34, :244-248; các R-card đều reuse-first). **Đề nghị: không dựng.**

**Motion.** "Đẩy xuống 2 con" = 2 `value_change` (differ.py:181-192 tự sinh). Inverse (kéo lên) chạy free qua inverse manifest (A-2). **Deduced**.

**Cost:** (a) S · (b) M-hoãn · (c) 0. 

---

### A2a · Matrix `row[i]`/`col[j]`/`diag` — VERDICT: `row`/`col` là **sugar tại `_expand_selectors`** (S); `diag` cần **enumerator mới** (S-M). Không verb/kind mới.

**Evidence.** `block` đã chạy end-to-end trên Matrix: expansion generic tại _frame_renderer.py:420-426 sinh tích `cell[r][c]`, và Matrix.validate_selector nhận block (matrix.py:296-302) nên không cảnh báo E1115. **Confirmed** (Agent xác nhận; test recolor-block hiện chỉ có cho Grid tại tests/unit/test_block_selector.py:44-50, Matrix chỉ được test annotation — **Deduced** gap test).

Hệ quả then chốt: `row[i] ≡ block[i:i][0:C-1]`, `col[j] ≡ block[0:R-1][j:j]`. Tức **năng lực đã có** — tác giả gõ được `\recolor{M.block[i:i][0:C-1]}{state=current}` ngay hôm nay. `row`/`col` thuần **sugar ergonomic**.

**Thiết kế — đặt sugar ở đâu?** Tại **`_expand_selectors`** (_frame_renderer.py:377-454), THÊM nhánh `elif` cạnh block, đọc `prim.cols`/`prim.rows` (matrix.py:245-246) để phát `cell[i][c]`/`cell[r][j]`. **Không đặt ở parser**: parser chỉ có chuỗi selector, không có primitive nên không biết C/R (_grammar_commands.py:93-101). Cần thêm `row`/`col` vào dispatch selectors.py:100-124 + `validate_selector` mỗi primitive để `_validate_expanded_selectors` không cảnh báo. **Lợi ích kép**: đặt ở site generic → Grid/DPTable-2D **hưởng cùng lúc** (đúng nơi các bài Gauss/XOR cần — xem A2b).

**`diag` cần enumerator mới (không phải sugar block).** Đường chéo `(0,0),(1,1),…` là tập con `r==c`, KHÔNG có `block[...]` chữ nhật nào chọn được (block luôn là tích đầy đủ, _frame_renderer.py:424-426). Cần nhánh `elif` riêng zip `cell[i][i]`, độ dài `min(rows,cols)`; anti-diag tương tự `cell[i][C-1-i]`. Vẫn cưỡi `recolor`/`value_change`. **Confirmed** (bản chất hình học).

**Motion.** Tất cả cưỡi `recolor` (differ.py:170-179) / `value_change`. Inverse: recolor tự-nghịch (scriba.js:327). Không kind mới.

**Xung đột.** Trên **Matrix**, recolor chỉ đổi **stroke** (xem A2b) → row/col/diag trên Matrix cho nhấn-viền, không nhấn-nền. Chính vì thế nên đặt ở site generic để **Grid/DPTable** (nơi recolor sở hữu nền) là đích thực dụng. R-35 (smart-label:468-501) hiện định nghĩa **chỉ block** → thêm row/col/diag là mở rộng họ selector R-35, cần cập nhật doc để `check_ruleset_sync.py` không gãy.

**Cost:** `row`/`col` **S**; `diag`/anti-diag **S-M** (thêm accessor + validate + doc R-35).

---

### A2b · Matrix fill-recolor — VERDICT: **claim ĐÚNG, và gap sâu hơn**. Đừng bơm fill vào Matrix; **route sang Grid/DPTable**. Cost để đúng-spec **S-M**.

**Verify claim "recolor đổi STROKE thôi" → CONFIRMED.**
- matrix.py:490,506: fill luôn là literal `interpolate_color(t,stops)`, độc lập state.
- matrix.py:485-489: state class chỉ sở hữu stroke; "fill CANNOT be owned by CSS".
- docs/primitives/matrix.md:342-344, 413: state = **border-stroke only**, "colorscale fill is never overridden by state classes".
- scriba.js: runtime **không bao giờ** ghi fill (không `setAttribute('fill')`/`.style.fill`) → dù muốn cũng không tween-fill được ô Matrix.

**Gap sâu hơn claim: Matrix còn không đổi được VALUE ô.** matrix.py:254 ("no set_value path"), emit luôn đọc `self.data[r][c]` (matrix.py:478,516), không đọc `get_value`. Mà M→M²→M⁴ **cần đổi giá trị ô** — nên Matrix "inert" gấp đôi (khóa cả fill lẫn value). **Confirmed**.

**Phân tích fill vs colorscale (câu hỏi hoà giải).**
Với heatmap thật, fill LÀ thông tin — đè state-fill lên = **mất dữ liệu heatmap**. Đó chính là lý do thiết kế chọn stroke-only (matrix.md:342). Vậy với heatmap thật, **giữ nguyên** nhấn-bằng-viền là đúng, tôn trọng A-0.v (color=token-ref, motion-ruleset:33) + R-36 (smart-label:503-532).

Nhưng M²/Gauss/XOR-basis **không phải heatmap** — chúng là lưới số. Primitive đúng là **Grid** (grid.py:333 value override; grid.py:351-355 rect không-fill → nền do state sở hữu; recolor đổi nền + runtime `recolor` tween chạy) hoặc **DPTable-2D** (dptable.py:442/506 value; :71-77 block; giá trị luôn hiện). Cả hai **đã** làm recolor-fill + value-mutation + block; cộng thêm row/col/diag (A2a tại site generic) là có atomic row/col-step luôn. **Confirmed** (Agent C + doc contrast matrix.md:26,28).

**Đề nghị hoà giải (ưu tiên):**
1. **Không** bổ sung state-fill cho Matrix (xung đột 3 nguồn normative: A-0.v, R-36, matrix.md:413). 
2. **Route** ~14 bài ma-trận-thuật-toán sang **Grid/DPTable-2D** (chỉ là docs + ví dụ corpus).
3. Dựng `row`/`col`/`diag` tại `_expand_selectors` (A2a) → Grid/DPTable nhận atomic row/col ngay.
4. **Nếu** cần honor matrix.md:264-268 (spec đã hứa value mutation): sửa **drift** bằng cách cho `emit_svg` đọc `get_value` như grid.py:333 rồi **tính lại `t` từ value mới** → fill vẫn theo colorscale (nhất quán, không xung đột fill-ownership), M² hiển thị được trên chính heatmap. Đây là thay đổi Matrix **duy nhất** đáng làm vì nó khớp code với spec đã ship. Cost **S-M**. Motion: `value_change` (có sẵn) + fill dịch theo SVG server lúc nghỉ (runtime không tween fill nhưng snap về truth, A-8).
5. Overlay tint (giữ heatmap + phủ màu state bán trong suốt) = emit mới + gần như kind mới (fill-overlay) + inverse → **nặng, không xứng** khi Grid/DPTable đã giải xong. Chỉ cân nhắc nếu tương lai cần "heatmap + nhấn ô" đồng thời.

**Cost:** route sang Grid/DPTable = **S** (docs); vá drift value trên Matrix = **S-M**; overlay = **L, không đề nghị**.

---

### C2 · Flow residual edges — VERDICT: **SPLIT**. Nhãn `f/c` đã ship (S); antiparallel cong-lệch mới (M); bipartite (M, hoãn/dùng LR).

**(a) Nhãn `f/c` mutable — ĐÃ CHẠY (Cost S, expose/docs).**
`\apply{G.edge[(u,v)]}{value="3/5"}` → get_value tại graph.py:1468 đè nhãn tĩnh; `split_labels` render "3/5" bold/dim (graph.py:1602-1629); `tint_by_edge` tô pill theo state cạnh (graph.py:1594-1595). **Confirmed**. Lưu ý: dùng `value=` chứ **không** `label=` (label bị bỏ khi emit). Motion `value_change`, tự-nghịch. Có thể chỉ cần bật `split_labels`/`tint_by_edge` mặc định + docs.

**(b) Cạnh antiparallel cong-lệch — GAP THẬT (Cost M).**
graph.py vẽ `<line>` thẳng (graph.py:1669-1680); forward (u→v) + residual (v→u) là 2 tuple riêng (graph.py:1084-1088) nhưng đọc cùng tọa độ (graph.py:1437-1438) → **đè thành 1 đoạn thẳng**. Cần: (i) pre-pass phát hiện cặp antiparallel trên `self.edges`; (ii) đổi `<line>` → `<path>` Bézier bậc 2 với offset vuông góc; (iii) sửa khối đặt weight-pill ~120 dòng (graph.py:1444-1568) vốn giả định đoạn thẳng (midpoint, theta, AABB, nudge). Arrowhead OK trên path (đã có `scriba-arrow-rev` chưa dùng, _frame_renderer.py:363). **Confirmed** cấu trúc.
Đây là **thay đổi hình học tĩnh** (không cross-frame) → **không kind mới, không vấn đề inverse**; lúc nghỉ SVG server hiện cạnh đã lệch (A-8). Chi phí nằm ở toán pill-placement, không ở motion.

**(c) Layout bipartite 2 cột — Cost M, hoãn.**
Không có layout bipartite native; `hierarchical` + `orientation="LR"` (graph_layout_hierarchical.py:230,235-237) xếp s→t thành cột trái→phải, thường ĐỦ cho flow. Bipartite thật = module layout mới. **Đề nghị**: thử LR trước, chỉ dựng bipartite nếu LR không đủ.

**Cost tổng C2:** nhãn **S** (xong) + antiparallel **M** + bipartite **M/hoãn**. Chỉ antiparallel là must-build.

---

## Conflicts

1. **Spec↔Code drift (Matrix value):** docs/primitives/matrix.md:264-268 hứa `\apply{m.cell}{value=0.7}` cập nhật value + recompute fill, nhưng matrix.py:254/478/516 **không có set_value path** → value bị nuốt lặng. Chặn A2b; phải chọn: vá code (đọc get_value) HOẶC sửa doc. **Confirmed**.
2. **Fill-override Matrix ↔ 3 nguồn normative:** thêm state-fill cho Matrix nghịch A-0.v (motion-ruleset:33), R-36 (smart-label:503-532), matrix.md:413. → Không làm. **Confirmed**.
3. **`\pushdown` verb ↔ ethos additive:** verb mới cho pure sugar nghịch motion-ruleset A-0.vi:34 + thiết kế reuse-first của mọi R-card. → Biểu diễn bằng nhiều `\apply`. **Confirmed**.
4. **R-35 chỉ định nghĩa block:** smart-label:468-501 hiện chỉ có block; thêm `row`/`col`/`diag` phải mở rộng R-35 + cập nhật doc để `check_ruleset_sync.py` khớp. Yêu cầu wiring, không phải mâu thuẫn logic. **Confirmed**.
5. **`\recolor` strict, `\apply` mở:** `\recolor` chỉ nhận `state`/`color` (_grammar_commands.py:132-185) — mọi `k=v` khác bị bỏ; nên value/tag phải qua `\apply`, không qua `\recolor`. Không phải lỗi, là ràng buộc định tuyến. **Confirmed**.
6. **Thiếu test Matrix-block recolor:** năng lực có (generic) nhưng chỉ Grid được test (tests/unit/test_block_selector.py:44-50); Matrix block chỉ test annotation. **Deduced** — rủi ro hồi quy im lặng.

---

## Đề nghị thứ tự + Confidence

Sắp theo **đòn bẩy/chi phí** (giá trị mở khóa ÷ cost):

| # | Việc | Cost | Đòn bẩy | Confidence |
|---|---|---|---|---|
| 1 | **A1** docs + golden test Tree value (0 dòng code core) | S | ~26 bài | **Cao** — Confirmed end-to-end (tree.py:722 ↔ _frame_renderer.py:847 ↔ differ.py:181 ↔ scriba.js:157) |
| 2 | **C2(a)** bật/tài liệu nhãn `f/c` mutable (`value=`, `split_labels`, `tint_by_edge`) | S | ~11-13 bài | **Cao** — Confirmed (graph.py:1468,1602-1629) |
| 3 | **A3(a)** docs + test lazy-tag dạng chữ segtree | S | ~4 CSES + phần USACO | **Cao** — cùng path A1 |
| 4 | **A2a** `row`/`col`/`diag` tại `_expand_selectors` (+ selectors.py + validate + R-35 doc) | S–M | Gauss/XOR trên Grid/DPTable | **Cao** cho row/col (Confirmed site); **Cao** cho diag-cần-mới (Deduced hình học) |
| 5 | **A2b** route ~14 bài sang Grid/DPTable (docs) + vá drift value Matrix (đọc get_value) | S / S–M | ~14 bài | **Cao** claim + route (Confirmed); vá drift **Trung bình** (cần chọn hướng với maintainer) |
| 6 | **C2(b)** cạnh antiparallel cong-lệch (`<path>` + offset + sửa pill geometry) | M | chất lượng ~11-13 bài flow | **Cao** cost, **Trung bình** phạm vi pill-math |
| 7 | **A3(b)** badge tag có cấu trúc `node[id].tag` | M | chỉ khi tag-chữ không đủ | **Trung bình** — Deduced, chờ tín hiệu corpus |
| 8 | **C2(c)** layout bipartite (hoặc dùng hierarchical LR trước) | M | phụ | **Thấp/hoãn** — thử LR trước |

**Nguyên tắc xuyên suốt:** mục 1-3 và 5-route là **docs/test**, gần-0 code, mở khóa đa số bài ngay. Chỉ **A2a-diag**, **C2(b)-antiparallel**, và (tùy) **A3(b)-badge** là code thật; **không mục nào cần verb mới hay kind motion mới** — tất cả cưỡi `value_change`/`recolor`/`element_add|remove` sẵn có, đóng kín dưới nghịch đảo (A-2). Đúng kỳ vọng motion-ruleset: "a new data structure should need zero new motion vocabulary".
