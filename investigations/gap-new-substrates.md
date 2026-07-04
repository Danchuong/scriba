# Gap · Substrate mới thuần — Hypercube · Circle/arc · Automaton · Deque/Heap

> **BMAD investigation.** Không sửa source. JudgeZone pass 3, nhóm "missing structures": *không có
> substrate nào cả* cho một lớp bài. Case file này chỉ xét **primitive mới thuần** (không đụng
> xung đột rule — các teammate khác lo). Repo @ `main` `bf1bbf6`, scriba ~0.21.1. Mọi trích dẫn
> `path:line` đọc trực tiếp phiên này; 4 claim load-bearing về parser đã **chạy thật** (§3).
>
> **Thang bằng chứng:** **[Confirmed]** = đọc thẳng source / chạy phiên này · **[Deduced]** = hệ quả
> logic của fact đã confirmed · **[Hypothesized]** = đề xuất thiết kế, chưa build/chưa verify.

---

## 1. Hand-off Brief (4 câu)

Bốn substrate được yêu cầu chia làm hai lớp chi phí rất khác nhau: **B4 (circle/arc/wedge trong
Plane2D)** là *mở rộng element-kind* trên một pattern đã có sẵn 5 lần — rẻ nhất, rủi ro thấp nhất,
zero layout mới, zero parser mới; còn **B2 (Hypercube)** là *primitive mới + layout mới + có thể
+verb mới* — coverage cao nhất (~30-45 bài) nhưng nhiều bề mặt mới nhất. Hai phát hiện executed
quan trọng nhất: selector `subset[10]` (thập phân) **parse được ngay không cần sửa gì** (đi qua
nhánh generic-indexed của `selectors.py:116-124), còn `subset[0b1010]` (nhị phân) **fail E1010** —
nghĩa là Hypercube dùng được liền nếu chấp nhận index thập phân, chỉ literal `0b` mới tốn parser
work dùng chung (rủi ro regression toàn bộ primitive). Với Automaton, `edge[(0,"c")]` **parse được**
thành EdgeAccessor còn `edge[(0,'c')]` **fail** — char-edge dùng nháy kép/`bare ident` là free,
nháy đơn thì không; và verdict `gap-dsu-forest` đã chốt **Automaton = Tree mở rộng, không primitive
mới** — tôi xác nhận trie/AC ép thẳng vào Reingold-Tilford (là cây), chỉ suffix-automaton là ca biên
(transition-DAG buộc lấy link-tree làm spine + jitter khi mọc), xem §6. Deque **không phải** "Queue +
2 op" vì model index tuyến tính của Queue
(`front_idx`/`rear_idx` chỉ tăng) không cho phép `push_front`; và Heap thì Tree **đã có** tham số
`kind` nên `kind=heap` chỉ-tree là rẻ, phần Array song song mới là phần đắt nên **đề xuất tiếp tục
defer**.

---

## 2. Hợp đồng một primitive phải thoả (baseline chi phí)

Mọi substrate mới đều kế thừa `PrimitiveBase(abc.ABC)` và phải trả về đúng contract. Đây là mẫu số
chung để quy đổi "S/M/L" thành LOC.

### 2.1 Bốn method abstract — bắt buộc **[Confirmed]**
`base.py:717-755` khai báo đúng **4** `@abc.abstractmethod` — một lớp con không implement đủ thì
không instantiate được:

| Method | base.py | Vai trò |
|--------|---------|---------|
| `addressable_parts()` | `:718` | Liệt kê mọi selector suffix hợp lệ của frame hiện tại |
| `validate_selector(suffix)` | `:722` | True nếu suffix trỏ tới part tồn tại |
| `bounding_box()` | `:726` | Footprint (đã cộng caption + lane annotation) |
| `emit_svg(...)` | `:730` | Fragment SVG của frame |

`resolve_annotation_point` có **default trả None** (`base.py:757`) nên về kỹ thuật là optional,
nhưng không có nó thì shape *không nhận annotation/pill* — thực tế mọi primitive đều override.

### 2.2 Sáu method smart-label protocol — advisory (warn-on-register) **[Confirmed]**
`_protocol.py:31-38` liệt kê 6 tên bắt buộc; `_protocol.py:137-167` cho biết ở chế độ v0.10.x nếu
thiếu chỉ **`warnings.warn`, vẫn đăng ký** (`fail-on-register` để dành sau 2026-05-05,
`_protocol.py:11-14`). Phần lớn 6 method này đã có **default trong `PrimitiveBase`**
(`annotation_height_above` `:401`, `_measure_emit` `:482`, `emit_annotation_arrows` `:1063`…) nên
lớp con **thừa hưởng miễn phí**. Nghĩa là "cái giá thật" của một primitive mới ≈ 4 abstract method +
`resolve_annotation_point` + regex selector + `__init__` + emit — phần annotation/caption/pill là
boilerplate gọi helper kế thừa.

### 2.3 Hạ tầng dùng lại được từ PrimitiveBase (không phải viết lại) **[Confirmed]**
`base.py`: state machine (`set_state/get_state` `:344-364`), annotation engine
(`set_annotations` `:392`, `emit_annotation_arrows` `:1063`), traces (`set_traces` `:507`,
`emit_traces_under` `:525`), cursors (`set_cursors` `:606`, `emit_cursors_under` `:624`), caption
(`_emit_caption` `:903`, `_caption_block_*` `:875-902`), highlight (`_is_highlighted` `:1044`),
h-pad pill (`_h_label_pad` `:843`), obstacle stub. Một primitive mới chỉ cần **cắm** geometry của nó
vào các hook này.

### 2.4 LOC baseline một primitive "đúng chuẩn" **[Confirmed]**
`wc -l`: các primitive gọn-nhất-nhưng-đầy-đủ là `hashmap.py`=403, `codepanel.py`=427,
`variablewatch.py`=428, `stack.py`=445 (12-14 method/file). → **1 primitive from-scratch ≈ 400-450
LOC**, trong đó ~40% là boilerplate gọi helper kế thừa; một layout function mới ≈ 60-120 LOC.

### 2.5 R-card một primitive mới phải tuân **[Confirmed]**
`smart-label-ruleset.md` là catalogue R-01..R-35 chủ yếu về *đặt nhãn không đè hình*. Với primitive
mới, các R-card ràng buộc trực tiếp:
- **R-02 / R-18** (`:266`, `:277`): AABB của target/mark phải đăng ký làm no-placement zone → primitive
  nên trả `register_decorations`/`resolve_obstacle_boxes` thật (không để stub `[]` như
  `stack.py:439-445`) nếu muốn nhãn tránh geometry.
- **R-31** (`:1228`): "mọi line-segment emit ra **MUST** đăng ký obstacle" → Hypercube edges,
  Automaton links, plane2d segment đều phải feed `resolve_obstacle_segments` (Plane2D đã làm ở
  `plane2d.py:1236-1343`).
- **R-13** (`:136`): token phải có differentiator **phi-màu** (dash) → trực tiếp áp cho *fail-link
  gạch đứt* của Automaton và bất kỳ lớp cạnh thứ hai nào.
- **R-15** (`:1013`): `<title>` là con đầu của mỗi `<svg>` — mức emitter, tự thoả.

---

## 3. Bằng chứng executed (parser probe) **[Confirmed — chạy phiên này]**

Chạy `parse_selector` (`scriba/animation/parser/selectors.py`) trên 4 chuỗi:

| Selector | Kết quả | Ý nghĩa |
|----------|---------|---------|
| `L.subset[10]` | **OK → NamedAccessor** | Index **thập phân** đi qua nhánh generic-indexed `selectors.py:116-124`, tạo `NamedAccessor(name="subset[10]")`. Hypercube dùng được **không sửa parser**. |
| `L.subset[0b1010]` | **FAIL E1010** "expected ']', got 'b'" @pos 10 | `_parse_number` (`selectors.py:253-276`) chỉ đọc `.isdigit()`; gặp `b` sau `0` là dừng → literal `0b` **không** được hỗ trợ. |
| `a.edge[(0,"c")]` | **OK → EdgeAccessor** | Tuple-edge + node-id chuỗi nháy kép parse sẵn (`selectors.py:155-165`, `_parse_node_id` `:207-221`). Automaton char-edge nháy kép là **free**. |
| `a.edge[(0,'c')]` | **FAIL E1010** "expected identifier" | Nháy **đơn** không được `_parse_string` nhận (`selectors.py:235-251` chỉ nhận `"`). |

Ghi chú thêm **[Confirmed]** `selectors.py:266-275`: index **âm bị chặn ngay parse-time** (E1010) —
liên quan Deque/Hypercube nếu ai định dùng offset âm.

---

## 4. B4 · Circle / arc / wedge trong Plane2D — **rẻ nhất, pattern-follow**

### 4.1 Model hiện có **[Confirmed]**
`plane2d.py:82-87` + `:175-179`: 5 element-kind, mỗi kind là **list các dict thuần**, lưu song song:
`points / lines / segments / polygons / regions`. Không có circle/arc/wedge (`grep` §absence rỗng;
lưu ý `wedge` xuất hiện ở `_math_metrics.py:112` nhưng đó là **glyph ∧ KaTeX**, không phải sector —
tránh đặt trùng tên).

### 4.2 Checklist thêm **1** kind (vd `circle`) — 14 điểm chạm **[Confirmed, đọc plane2d.py]**
| # | Điểm chạm | plane2d.py | Ghi chú |
|---|-----------|-----------|---------|
| 1 | regex `_CIRCLE_RE` | mẫu `:62-66` | 1 dòng |
| 2 | list `self.circles=[]` | mẫu `:175-179` | 1 dòng |
| 3 | vòng populate từ params | mẫu `:182-191` | 1 dòng |
| 4 | `ACCEPTED_PARAMS += "circles"` | `:121-137` | 1 dòng |
| 5 | `SELECTOR_PATTERNS` | `:109-116` | 1 dòng |
| 6 | `_total_elements()` cộng thêm | `:218-225` | cap E1466 |
| 7 | `_add_circle_internal` | mẫu `:242-269` | parse `{cx,cy,r}` + cảnh báo ngoài viewport |
| 8 | `_remove_circle_internal` tombstone | mẫu `:426-494` | `_TOMBSTONE` `:72` |
| 9 | `apply_command` nhánh add+remove | `:392-422` | dynamic ops |
| 10 | `addressable_parts` vòng | `:498-516` | skip tombstone |
| 11 | `validate_selector` nhánh | `:518-547` | |
| 12 | `resolve_annotation_point` nhánh | `:551-624` | anchor = tâm |
| 13 | `_emit_circles` + dispatch trong `emit_svg` | mẫu `:822-850`, gọi ở `:671-676` | ~20 dòng |
| 14 | `register_decorations` (nếu có label) + obstacles | `:965`, `:1232` | R-02/R-31 |

### 4.3 Cảnh báo hình học **[Deduced]**
Content vẽ trong group `scale({sx},{sy})` với `sy` âm và `|sx|≠|sy|` khi `aspect="auto"`
(`plane2d.py:161-169`, `:666-670`). → `<circle>` bán kính **math-unit** (vd bán kính closest-pair =
khoảng cách) sẽ **méo thành ellipse** khi `aspect="auto"`. Ba lối: (a) yêu cầu `aspect="equal"`
(mặc định, `:154`) → tròn thật; (b) emit `<ellipse>` với `rx=r, ry=r` để scale tự lo; (c) emit ngoài
transform, tự `math_to_svg` tâm + scale bán kính. **Point hiện tại né bằng bán kính pixel cố định**
(`_emit_points` `:836-837` dùng `r_px/scale_factor` + `vector-effect="non-scaling-stroke"`) — nhưng
đó là bán kính *pixel*, không phải bán kính *math* mà closest-pair cần. Đây là quyết định thiết kế
cần chốt trước.

### 4.4 Selector family & motion
- `p.circle[i]`, `p.arc[i]`, `p.wedge[i]` — đồng dạng `point[i]` (đi nhánh regex riêng, **không**
  cần selector parser mới). **[Deduced]**
- Motion: `\recolor{p.circle[0]}{...}` chạy qua state machine sẵn có; growth/shrink của bán kính =
  đổi giá trị dict qua `\apply` → re-emit, giống mọi element khác. **[Deduced]**

### 4.5 Bài thật unlock
Closest-pair (đường tròn bán kính δ), rotating calipers (cạnh + góc), angle mark (wedge/sector),
đường tròn ngoại/nội tiếp. Task ước ~3-9 bài.

### 4.6 Cost **[Deduced]**
`+~50-70 LOC/kind × 3 = 150-220 LOC` **thêm vào** `plane2d.py` (đã 1353 dòng — đã vượt xa chuẩn
800/file). Không primitive mới, không layout mới, goldens cũ **byte-stable** (thuần additive).
→ **Cost S-M · Risk THẤP**. Rủi ro duy nhất: file plane2d.py phình thêm (nên cân nhắc tách
`plane2d_emit.py` khi thêm 3 kind).

---

## 5. B2 · Subset-lattice / Hypercube — **coverage cao nhất, nhiều bề mặt mới nhất**

### 5.1 Vì sao cần substrate (motivation) **[Confirmed]**
DPTable index bằng **số nguyên** thuần: `cell[i]` (1D) / `cell[r][c]` (2D) (`dptable.py:98-99`).
Bitmask DP (TSP, SOS, inclusion-exclusion, Möbius) cần trạng thái là **tập con** với quan hệ
*submask/superset* và chiều *bit*. Nhét vào DPTable thì `cell[10]` mất hết cấu trúc kề bit —
`0b1010` chỉ còn là "ô số 10". Hypercube làm bit-adjacency thành first-class.

### 5.2 Model dữ liệu **[Hypothesized]**
`\shape{L}{Hypercube}{bits=4}` → `2^bits` node, mỗi node = một subset (int 0..2^n-1). Lưu:
`self.bits:int`, `self.states: list[dict]` (index = giá trị subset, `{label, value, popcount}`),
edges **suy ra** từ bits (không lưu tay): submask-edge = xoá 1 bit set. `ACCEPTED_PARAMS =
{bits, data, label, layout}`. `bits` là int truyền thẳng qua `\shape` params (validate bằng
`_validate_accepted_params` `base.py:313`).

### 5.3 Selector family **[Confirmed nhánh parse + Hypothesized ngữ nghĩa]**
- `L.subset[10]` (thập phân) — **parse OK ngay** (§3, NamedAccessor). **Khuyến nghị canonical dùng
  thập phân** để zero parser change.
- `L.subset[0b1010]` (nhị phân) — **fail E1010** (§3). Muốn hỗ trợ phải sửa `_parse_number`
  (`selectors.py:253-276`, ~5-8 dòng nhận tiền tố `0b`) — **nhưng parser này dùng chung MỌI
  primitive** → phải chạy lại toàn bộ golden, rủi ro regression. **Đề xuất: hoãn `0b`, chỉ thêm khi
  có nhu cầu tác giả thật.**
- `L.dim[k]` hoặc `L.level[p]` (tầng popcount) — mới, đi nhánh generic-indexed **free**. **[Deduced]**

### 5.4 Layout — câu hỏi lõi **[Hypothesized]**
Hai phương án, **không** tái dùng được `_reingold_tilford` (nó cần cây thật `children_map`,
`tree_layout.py:100-121`; hypercube là DAG lưới):
- **(A) Hasse theo tầng popcount** — hàng ngang = popcount 0..n, trong hàng xếp theo thứ tự Gray/số.
  Đọc submask-edge tốt (luôn đi xuống 1 tầng), giống lattice toán học. **Khuyến nghị.**
- **(B) Hypercube projection** (chiếu n-cube 2D) — đẹp với n≤3, rối chéo nhau khi n≥4.

Số node/edge (quyết định `bits` max) **[Deduced]** — cube n có `n·2^(n-1)` cạnh:

| bits | node | edge (Hasse) | Đánh giá render |
|------|------|--------------|-----------------|
| 4 | 16 | 32 | Thoải mái |
| 5 | 32 | 80 | Chật, còn đọc được ở layout Hasse |
| 6 | 64 | 192 | Quá tải nhãn — chỉ nên highlight-subset, ẩn cạnh |

→ **Khuyến nghị hard-cap `bits ≤ 5`** (song song với `_ELEMENT_CAP` của Plane2D `:53`), n=6 chỉ cho
chế độ "sweep một chiều, ẩn phần còn lại".

### 5.5 `\sweep{L}{dim=2}` (SOS fold) — verb mới hay `\playeach`? **[Confirmed ràng buộc]**
`\playeach` là frame-macro *chỉ* nhận `range[lo:hi]` hoặc `block[r0:r1][c0:c1]`, else **raise**
(`_grammar_playeach.py:118-123`). Sweep theo chiều bit **không** phải range/block → hai lối:
- Mở rộng `\playeach` nhận selector-kind mới `dim[k]` (sửa `_grammar_playeach.py`), hoặc
- Thêm verb `\sweep` riêng (dispatch mới trong grammar).
Cả hai đều là **parser + renderer work thật** (~100-180 LOC). Motion khi fold: mỗi bước tô các cặp
`(subset, subset|bit)` theo chiều `k` — chạy trên state machine sẵn có, chỉ cần bộ sinh cặp.
**Đề xuất: pha 1 KHÔNG có `\sweep`** — tô tay bằng `\recolor{L.subset[i]}` qua `\foreach`; thêm
`\sweep` ở pha 2 nếu coverage chứng minh cần.

### 5.6 R-card compliance
R-31 (edges → obstacle segment, `:1228`), R-13 (nếu phân biệt submask vs superset edge bằng dash,
`:136`), R-02 (subset được annotate → AABB no-placement, `:266`).

### 5.7 Bài thật unlock & Cost
TSP bitmask, SOS/superset-sum, inclusion-exclusion, Möbius trên lattice, subset-sum DP. Task ước
**~30-45 bài** (coverage lớn nhất nhóm). **Cost L**: primitive mới ~350-450 + layout Hasse ~80-120
+ (hoãn) 0b ~5-8 + (hoãn) `\sweep` ~100-180. Pha-1-khả-thi (thập phân + Hasse + tô-tay) ≈ **M**.

---

## 6. B3 · Automaton — XÁC NHẬN hướng Tree-mở-rộng (không primitive mới)

> **Verdict `gap-dsu-forest` [đã chốt]:** Automaton = Tree mở rộng, **KHÔNG** primitive mới. Mục này
> rút gọn thành xác nhận/phản biện từ góc primitive-mới của tôi (layout + clone), đã verify source.

### 6.1 Xác nhận 3 tiền đề của verdict **[Confirmed]**
- **Rào char-edge là của Graph, không của Tree.** `graph.py:695` ép `float(e[2])` cho phần tử thứ 3
  của edge → char `'a'` chết ở `float('a')`. Tree edge là cặp trần `(parent, child)`, **không có phần
  tử thứ 3** (`tree.py:163-165`) → không dính barrier. Nhưng cũng **chưa có chỗ lưu label cạnh** (emit
  chạy `for parent, child in self.edges` `tree.py:111`, chỉ có `node_labels`, không `edge_labels`) →
  `edge_labels` là field **additive mới**, đúng như verdict. **Selector để địa chỉ-hoá** char-edge thì
  **đã free sẵn**: probe §3 cho `a.edge[(0,"c")]` **parse được** thành `EdgeAccessor` (`selectors.py:155-165`,
  nháy kép OK; nháy đơn `edge[(0,'c')]` **fail E1010**) → trỏ tới một cạnh gán ký tự **không tốn parser
  work**, phần mới duy nhất là field lưu `edge_labels`. (Trên Tree path — không dính barrier `float()` của Graph.)
- **Link-class thứ 2 tự động loại khỏi layout.** RT chỉ ăn `children_map` (`tree.py:135`, `:278`).
  Fail/suffix-link **không** add vào `children_map` → RT không thấy → tự loại khỏi layout, chỉ vẽ
  overlay kiểu annotation-arrow. Xác nhận đúng.
- **Node-growth + reparent đã có sẵn.** `_add_node_internal` (`tree.py:294`) append edge + children_map
  + relayout; `reparent` (`apply_command:263`, `_reparent_internal:411`) splice node giữa 2 node → đủ
  để biểu diễn thêm-node và clone-splice mà không thêm cơ chế mutation nào.

### 6.2 Angle 1 — Trie/Aho-Corasick "BFS-depth trái→phải" có ép vào layout Tree được không? → **CONFIRM** **[Deduced]**
Trie **là cây có gốc** (goto-edge: mỗi node đúng 1 parent) → `_reingold_tilford` lay out **trực tiếp**
từ `children_map`, **không cần layout mới**. Fail-link (AC) không vào `children_map` → overlay. Khác
biệt duy nhất: RT là **top-down** (gốc trên, depth→y, `tree_layout.py:223`), còn quy ước automaton hay
vẽ **trái→phải** (depth→x) — đây chỉ là **transpose x/y**: hoặc chấp nhận top-down (đọc tốt cho trie),
hoặc thêm param `orientation="horizontal"` hoán vị sau layout (additive nhỏ). **Không phải blocker.**

### 6.3 Angle 2 — Suffix-automaton CLONE có gì đặc biệt? → **PARTIAL / caveat** **[Deduced]**
Hai điểm strain thật với khung Tree:
1. **Đồ thị transition là DAG, không phải cây.** Clone sao chép transitions → một state có **nhiều
   in-transition** (nhiều "parent"). RT đòi cây thật (1 parent/node). → **Không thể** lấy transition-spine
   (xếp theo `len`) làm xương sống RT. Lối thoát *trong* khung Tree: lấy **cây suffix-link** (link pointer
   LÀ cây) làm spine cho RT, transitions thành overlay class thứ 2. Điều này **đảo vai** — xương sống là
   link-tree chứ không phải trục `len` trái→phải như brief gốc tưởng. Chấp nhận được nhưng là quy ước
   bắt buộc phải ghi rõ.
2. **Jitter khi mọc (chi phí motion chính).** `_relayout` (`tree.py:275`) gọi lại RT toàn cục; RT chuẩn
   hoá `min_px/max_px` trên **toàn bộ** node (`tree_layout.py:207-222`) → thêm 1 node là **mọi x dịch**
   → node cũ nhảy chỗ mỗi lần clone/add. **Không** riêng automaton — dính mọi Tree mọc dần (sparse_segtree,
   và cả B2 Hypercube nếu mọc). Muốn animate clone mượt cần layout **ổn định/incremental** (Graph có
   `graph_layout_stable.py`; Tree chưa) — là hạng mục **M riêng**, độc lập với char-edge.

### 6.4 Kết luận B3 **[Deduced]**
**Đồng ý verdict Tree-mở-rộng** cho ~12 bài — đa số (trie, Aho-Corasick, KMP-automaton) **là cây**, RT
ăn thẳng; chỉ thiếu `edge_labels` (additive) + overlay fail-link gạch đứt (R-13 `:136`, R-31 cho cả 2
lớp cạnh). **Suffix-automaton là ca biên**: buộc dùng link-tree làm spine (không phải trục `len`), và
growth cần layout ổn định để khỏi jitter. **Cost char-edge + fail-link overlay: S-M** (~60-120 LOC thêm
vào `tree.py`, **không** layout mới, **không** primitive mới). **Layout ổn định (nếu muốn clone mượt):
M riêng, defer** tới khi có bài suffix-automaton thật.

---

## 7. Minor · Deque + Heap

### 7.1 Deque — **KHÔNG phải "Queue + 2 op"** **[Confirmed]**
Model Queue (`queue.py`): mảng cố định `cells=[""]*capacity` (`:131`), `front_idx=0`,
`rear_idx=len(data)` (`:140-141`). `enqueue` ghi tại `rear_idx` rồi **tăng** (`:173-180`), `dequeue`
xoá `front` rồi **tăng** `front_idx` (`:188-191`). **Cả hai con trỏ chỉ TĂNG** → đây là queue tuyến
tính (amortized), **không phải vòng (circular buffer)**. Hệ quả **[Deduced]**: `push_front` cần chèn
*bên trái* `front_idx` — mảng không có chỗ; và sau khi `rear_idx` chạm `capacity` thì hết enqueue
được dù đã dequeue. → Deque đòi **đổi model**: (a) circular buffer (mod capacity), hoặc (b) neo
giữa: khởi tạo `front_idx`/`rear_idx` ở giữa, `push_front` giảm `front_idx` xuống 0, `push_back`
tăng `rear_idx` tới capacity (headroom bất đối xứng). Rendering window cũng phải đổi (Queue vẽ
`0..capacity` cứng `:347`).

**Selector/Cost:** giữ `cell[i]`, thêm state `front/back` (Queue đã có `front/rear` `:59-60`).
**Cost M**: primitive mới ~300 LOC, **hoặc** generalize Queue ~120-180 LOC (thêm circular + 2 op +
window trượt). Coverage: ít (sliding-window-maximum deque, 0-1 BFS). **Đề xuất: gộp vào lần
generalize Queue khi có bài circular-buffer thật, không tách sớm.**

### 7.2 Heap panel — **đề xuất TIẾP TỤC DEFER phần Array** **[Confirmed cơ sở]**
Tree **đã có** tham số `kind` (`tree.py:95`, `:100-102` xử lý `segtree`/`sparse_segtree`). Heap là
**cây nhị phân đầy đủ** → `kind="heap"` với layout complete-binary-tree (node i → con 2i+1, 2i+2)
tái dùng thẳng `_reingold_tilford` (`tree_layout.py:100`) hoặc đơn giản hơn. **Cost S** (~40-80 LOC,
thêm `_init_heap` cạnh `_init_segtree` `:183`).

Phần **Array song song** (heap-as-array kề heap-as-tree) mới là phần đắt: cần hai view đồng bộ index
↔ node, **Cost M** (~150-250 LOC). Tier-4 pass trước đã defer heap. **Quan điểm [Deduced]:** nên
**ship `kind="heap"` chỉ-tree ngay** (rẻ, mở khoá heapify/priority-queue viz) nhưng **giữ defer phần
Array-pairing** cho tới khi editorial chứng minh bài cần *nhìn cả hai view cùng lúc* (hiếm — đa số
bài chỉ cần một). Không nên build panel kép đầu cơ.

---

## 8. Thứ tự đề xuất trong nhóm (ROI, evidence-based)

| # | Substrate | Cost | Coverage | Layout mới? | Parser mới? | Gate/Ghi chú |
|---|-----------|------|----------|-------------|-------------|--------------|
| 1 | **B4 circle/arc/wedge** | S-M | ~3-9 | Không | Không | — |
| 2 | **Heap `kind=heap` (chỉ-tree)** | S | heapify/pq | Không (RT) | Không | Defer Array-pairing |
| 3 | **B3 Automaton (char-edge + fail-overlay)** | S-M | ~12 | Không (RT — trie/AC là cây) | Không (nháy kép) | Verdict đã chốt = Tree-mở-rộng; suffix-automaton + stable-layout defer (M riêng) |
| 4 | **B2 Hypercube (pha-1: thập phân+Hasse+tô-tay)** | M | **~30-45** | Có (Hasse) | Không (né 0b) | Hoãn `0b`+`\sweep` |
| 5 | **Deque** | M | ít | Không | Không | Gộp vào generalize Queue |

**Lý do xếp hạng [Deduced]:** (1) B4 rẻ nhất, rủi ro thấp nhất, pattern đã lặp 5 lần — làm trước để
"nóng máy" và mở khoá hình học ngay. (2) Heap-tree gần như free (Tree có `kind` sẵn) — quick win,
nhưng chốt defer Array. (3) **B3 leo hạng** sau verdict: từ "primitive mới M-L" xuống "Tree-mở-rộng
S-M" — chỉ thêm `edge_labels` + overlay fail-link, RT ăn thẳng trie/AC, ~12 bài, rủi ro thấp; phần
suffix-automaton + stable-layout tách ra defer. (4) B2 coverage áp đảo (~30-45 bài, gấp ~3× phần còn
lại **cộng lại**) nên đầu tư lớn nhất, nhưng là substrate **duy nhất có layout mới** → xếp sau 3 việc
rẻ-an-toàn; **chia pha** (thập phân + Hasse + tô-tay) để né hai món đắt-rủi-ro (parser `0b` dùng chung,
verb `\sweep`). **Đòn bẩy:** nếu team ưu tiên coverage-thô hơn rủi ro, kéo B2 lên #3 (đổi chỗ B3) —
cả hai đều không chặn nhau. (5) Deque ít bài, model đòi đổi (§7.1) → gộp vào lần generalize Queue.

---

## 9. Open questions / dependencies

1. **[Đã chốt — verdict gap-dsu-forest]** Automaton = Tree mở rộng (không primitive mới); trie/AC ăn
   thẳng RT, chỉ thiếu `edge_labels` + overlay fail-link (§6). Câu hỏi *còn mở*: có build **layout ổn
   định/incremental** cho Tree (như `graph_layout_stable.py`) để clone/growth khỏi jitter không (§6.3) —
   M riêng, dùng chung cho suffix-automaton + sparse_segtree + Hypercube-mọc; đề xuất defer tới bài thật.
2. **[Chốt trước khi build B4]** Circle bán kính math-unit dưới `aspect="auto"` xử lý thế nào — ép
   `aspect=equal`, hay `<ellipse>` scale-theo-transform, hay emit-ngoài-transform (§4.3)?
3. **[Chốt trước khi build B2]** Hard-cap `bits` = 5? Layout mặc định Hasse-popcount (§5.4)? Có chấp
   nhận pha-1 chỉ index thập phân, hoãn `0b` + `\sweep` (§5.3, §5.5)?
4. **[Policy dùng chung]** Sửa `_parse_number` (`selectors.py:253`) cho `0b` đụng **mọi** primitive →
   cần chạy full golden. Có đáng cho riêng Hypercube không, hay đợi ≥2 use-case?
5. **[Kiến trúc]** `plane2d.py` đã 1353 dòng; thêm 3 kind nên tách emit ra `plane2d_emit.py` để giữ
   chuẩn <800/file (§4.6).
