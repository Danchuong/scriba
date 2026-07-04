# Motion Identity & Reorder — cái gì có identity, và phần tử có được phép bay không (A4 `\move` + A5 `\reorder`)

> Thẩm định thiết kế (design synthesis). **Không sửa source.** Repo @ `main`, scriba 0.23.1,
> `SCRIBA_VERSION = 17` (`scriba/_version.py:6`). Companion của **A-rules**
> (`docs/spec/motion-ruleset.md`, phase 0.23.0) và **R-32** (`docs/spec/ruleset.md` §8.9).
> Câu hỏi trung tâm của JudgeZone feature-request pass 3: **cái gì mang identity, và một
> phần tử có identity có được phép đổi vị trí (bay/trượt) giữa hai frame không?**
>
> Cấp độ bằng chứng: **[Confirmed]** = đọc thẳng trong source phiên này (path:line) ·
> **[Deduced]** = hệ quả logic của fact đã Confirmed · **[Hypothesized]** = đề xuất thiết
> kế, chưa build.

---

## 1. Hand-off Brief (kết luận trước)

**Đường thắng: Path 2 — ELEMENT-IDENTITY, và nó KHÔNG phá R-32.** Lý do gốc: R-32
(`ruleset.md:926-945`) ràng buộc **envelope/bounding-box của primitive là bất biến qua các
frame** — *không* phải "mọi cell bất động". Một phần tử có `data-target` ổn định được phép
**trượt trong lòng envelope đã reserve**; tiền lệ đã ship là `cursor_move` (một caret trượt
giữa các cell của một Array mà bbox vẫn cố định — R-38) và `position_move` (node Tree trượt
sau reparent — `differ.py:218-236`). Cả A4 (sweep line trượt trong viewport) lẫn A5 (cell
lướt giữa các slot đã reserve) đều là **chuyển động INTRA-envelope → bbox không đổi → R-32
giữ nguyên**. Path 1 (value-permute, mô hình insert/remove của Array R-42) **bị bác cho vai
trò tổng quát**: nó không áp dụng được cho A4 (sweep line là hình học, không phải cascade
value) và làm rỗng ý nghĩa sư phạm của A5 (không thấy phần tử bay — mất chính điểm của sort
viz).

**Cơ chế: TÁI DÙNG `position_move`, KHÔNG thêm kind thứ 12.** Substrate trượt-theo-identity
đã tồn tại đủ: primitive mọc một method `get_node_positions()` → `_inject_tree_positions`
duck-type nó vào `shape_states` (`emitter.py:202-228`, `hasattr` tại `:211`) → differ phát
`position_move` (`differ.py:218-236`) → runtime trượt `[data-target]` rồi fs-snap. Differ /
emitter / runtime **không cần đổi một dòng** cho đường dữ liệu này (đúng lý tưởng "zero new
motion vocabulary", `motion-ruleset.md:232`).

**Một chỉnh sửa runtime duy nhất (nên làm, và chính là cái bump A4/A5 vốn phải trả):** sửa
**hình học** của `position_move` từ *kết-thúc-ở-ghế-cũ* `[translate(from-to)→translate(0)]`
(`scriba.js:213-216`) sang *lướt-tới-ghế-mới* `[translate(0,0)→translate(to-from)]` (đúng
công thức `cursor_move`, `scriba.js:318-321`). Hiện `position_move` kết thúc ở ghế cũ và dựa
vào fs-snap để nhảy tới ghế mới — repo tự ghi nhận điều này (`differ.py:280`; A-4
`motion-ruleset.md:119-120` gọi là "visible lurch"). Với reparent nhỏ của Tree thì chấp nhận
được; với hoán vị lớn của A5 thì cú snap giữa-chừng phá tan payload "phần tử bay tới chỗ đã
sort". Sửa hình học này **cải thiện luôn Tree**, giữ registry đóng ở 11 kind (không bloat).

**Spec-diff:** KHÔNG viết lại normative text của R-32 (nó đúng — envelope invariance). Thay
vào đó: (a) thêm **note làm rõ** vào R-32 rằng nó ràng buộc *envelope*, không cấm phần tử di
chuyển trong envelope; (b) thêm **note companion** vào R-42 tách bạch SLOT-identity
(`cell[i]`, cố định, neo annotation) khỏi ELEMENT-identity (`item[k]`, gán ở t0, mang vị trí
di động) cho reorder; (c) mở rộng A-4 để nêu tên chuyển động theo cell/node-identity
(`position_move`) song song với marker-identity (`cursor_move`).

**Chi phí:** 1 bump `SCRIBA_VERSION 17→18` (sửa 1 handler + re-bless golden Tree/cursor) +
Python thuần additive per-primitive (lệnh mutate-in-place + `get_node_positions`). A4 có thể
ship **zero-bump** trên `position_move` nguyên trạng nếu cần gấp (moves nhỏ). **Confidence:
High** cho chẩn đoán R-32, **High** cho cơ chế substrate, **Medium** cho chi tiết hình học
plane2d (phụ thuộc ngữ nghĩa transform SVG trong nhóm scaled).

---

## 2. Problem — hai yêu cầu đâm vào một hiểu lầm về R-32

**A4 · Plane2D `\move`/set_position (~9-13 bài).** `plane2d.py:apply_command` (`:389-422`)
chỉ có `add_*` và `remove_*` (remove = tombstone, `:72-76`, `:438`). Không có lệnh nào
mutate toạ độ tại chỗ. Pattern sweep-line hiện tại buộc phải add line mới + remove line cũ →
**hai index khác nhau → hai `data-target` khác nhau → `element_add`+`element_remove` → NHẢY**,
không trượt. Đề xuất của họ: `\move{plane.line[sweep]}{to_x=4.0}` giữ nguyên identity để
tween trượt nó.

**A5 · Table/Array row-permute `\reorder` (~8 bài).** `array.py:apply_command` (`:200-221`)
insert/remove **dịch VALUE** trên grid max-N cố định; `cell[i]` luôn ở
`x = i*(cw+CELL_GAP)+row_dx` (`:393`) — vị trí là hàm thuần của index. Không primitive nào
hoán vị được hàng và cho chúng lướt. Suffix-array rank-doubling sort vì thế chỉ render được
bảng **ĐÃ** sort. Đề xuất: `\reorder{arr}{order=[3,0,1,4,2]}` — cells hoán vị + glide.

**Xung đột rule (lý do case này tồn tại) — và chỗ team-lead brief hiểu lệch một nấc.** Brief
mô tả R-32 là "slot-identity — positions never move". **Đọc source thì R-32 không nói vậy.**
R-32 (`ruleset.md:926-945`) là **Annotation Stable Layout**: bounding-box render của một
primitive phải **bất biến qua mọi frame**. R-32.1 (`:941-945`) ràng buộc *height/width của
primitive*, không ràng buộc vị trí từng phần tử con. "Slot bất động" chỉ là **lựa chọn thiết
kế cục bộ của Array** để đạt R-32 (giữ slot cố định, cascade value) — được ghi trong R-42
("`cell[i]` addresses the **position**", `smart-label-ruleset.md:682`), *không* phải một
invariant toàn cục cấm phần tử di chuyển. Chính R-42 còn ghi sentinel `a.after` "no element
identity is needed" (`:675`) — ngụ ý **element identity là một khái niệm riêng, tồn tại,
có thể cần đến**. (Ghi chú: R-32 *không* nằm trong `smart-label-ruleset.md`;
`smart-label-ruleset.md:1318` nói rõ nó ở `ruleset.md` §8.9.)

Hệ quả: câu "reorder glide = phần tử bay = phá thẳng R-32?" **được trả lời là KHÔNG** ngay
từ khâu đọc rule — miễn phần tử bay *trong lòng envelope đã reserve*. Đây là chốt của toàn
bộ thẩm định.

---

## 3. Evidence Inventory (mọi dòng [Confirmed] đọc trong phiên)

| # | Fact | Anchor | Grade |
|---|---|---|---|
| E1 | Motion = `compute_transitions(prev,curr)` → `Transition[target,prop,from,to,kind]`, dispatch stateless theo `kind`. | `differ.py:20-31,382-421`; `scriba.js:138` | Confirmed |
| E2 | Registry đóng, **11 kind** (10 ở 0.23.0 Phase A + `cursor_move` ở 0.23.1). `_INV_KIND` có 3 cặp tường minh (add/remove, on/off); `recolor/value_change/position_move/annotation_recolor/cursor_move` **tự-nghịch-đảo** qua swap from/to. | `differ.py:26-31`; `scriba.js:326-331`; A-2 `motion-ruleset.md:59-80`; `CHANGELOG.md:71,81` | Confirmed |
| E3 | **`position_move` ĐÃ trượt cell `[data-target]`** khi (x,y) của target đổi giữa frame ("Tree node movement after structural mutations"). | `differ.py:218-236`; handler `scriba.js:206-218` | Confirmed |
| E4 | `position_move` **kết thúc ở GHẾ CŨ**, dựa vào fs-snap để nhảy tới ghế mới. Repo tự ghi nhận. | `differ.py:280-283` (docstring); A-4 `motion-ruleset.md:119-120`; keyframes `scriba.js:213-216` kết ở `translate(0)`=DOM base=frame trước | Confirmed |
| E5 | **`cursor_move`** resolve `[data-annotation]`, glide `[translate(0,0)→translate(to-from)]` → **kết ở ghế MỚI**, giữ, rồi fs-snap. Tự-nghịch-đảo. Key `{shape}.cursor[{id}]-solo`. | `differ.py:273-316`; `scriba.js:308-324` | Confirmed |
| E6 | **Cơ chế bơm vị trí**: primitive có `get_node_positions()` → `_inject_tree_positions` duck-type (`hasattr`) ghi (x,y) vào `frame.shape_states` → differ phát `position_move`. Gọi bởi `emit_interactive_html`. Chỉ Tree implement (trả `{"{name}.node[{id}]":(x,y)}`). | `emitter.py:202-228` (`:211` hasattr); `_html_stitcher.py:483-484`; `tree.py:507-517` | Confirmed |
| E7 | Plane2D: `apply_command` chỉ add/remove-tombstone, **không** mutate toạ độ. Point/line có `data-target` ổn định (`{name}.point[i]`/`line[i]`) **nhưng nằm TRONG nhóm content `scale(sx,sy)`**. `bounding_box` cố định. Không có `get_node_positions`. | `plane2d.py:389-422,844,884,666-669,628-636`; grep count 0 | Confirmed |
| E8 | Array: insert/remove **dịch value** trên grid cố định → cascade `value_change`, "no new motion kind, no JS". `cell[i]` = SLOT (vị trí = hàm của index). Không có `get_node_positions`. | `array.py:200-221` (câu chốt `:214`), `:393`; grep count 0 | Confirmed |
| E9 | R-32 = **envelope/bbox invariance** (height/width của primitive bất biến; width nới đều qua prescan). R-32.5 = reduced-motion vẫn phải giữ R-32.1/.2. | `ruleset.md:926-993` (`:941-945`, `:963-966`) | Confirmed |
| E10 | R-42: `cell[i]` **addresses the position** (annotation bám slot qua reflow); sentinel `a.after` "no element identity is needed". | `smart-label-ruleset.md:661-693` (`:675`,`:682-683`) | Confirmed |
| E11 | A-6/prescan: layout-mutation qua prescan; envelope = max cross-frame, tính 1 lần ở build. LinkedList `_structural_prescan=True` để `_envelope_n` chạm max **trước** khi đo → cấu trúc mọc không làm nhảy frame sau. | `motion-ruleset.md:152-170`; `_frame_renderer.py:45,188,623-633`; `linkedlist.py:85,129,174,243` | Confirmed |
| E12 | A-8: reduced-motion/print — server SVG lúc nghỉ đã hiện đích; tắt tween chỉ mất phần nội suy. | `motion-ruleset.md:197-215`; `scriba.js:42,100-110` | Confirmed |
| E13 | Bump motion **đã tiêu** ở 0.23.0/0.23.1 (`SCRIBA_VERSION 15→16→17`). A4/A5 chạm runtime = bump mới. Matrix/DPTable cũng có `data-target` per-cell → substrate tổng quát được sang bảng 2D. | `_version.py:6`; `CHANGELOG.md:67-95`; `matrix.py:497`, `dptable.py:453,519` | Confirmed |

---

## 4. Hypotheses — phân xử ba đường

### H1 — VALUE-PERMUTE (giữ R-32 "tuyệt đối", reorder = chuỗi value-update). **REFUTED (cho vai trò tổng quát).**

Mô hình insert/remove của Array R-42 (E8, E10): slot cố định, value cascade, motion =
`value_change` (crossfade/bounce tại chỗ). Ưu: rẻ nhất, zero kind mới, zero bump, R-32 giữ
by construction. **Bác vì hai lẽ, dựa trên evidence:**

1. **Không áp dụng được A4.** Sweep line là **dịch chuyển hình học** của một `<line>`
   (E7), không phải một dãy ô mang value. Không có "value" nào để permute. Value-permute
   *không có cửa* cho A4.
2. **Làm rỗng A5.** Payload sư phạm của sort viz là **thấy phần tử di chuyển tới vị trí đã
   sort**. Value-permute cho ra kết quả cuối đúng nhưng phần tử **đứng yên, chỉ đổi số** —
   đúng cái brief cảnh báo "mất chính cái điểm của sort viz". Rank-doubling có O(log n) vòng,
   mỗi vòng một hoán vị lớn; crossfade tại chỗ không kể được câu chuyện "ai đi đâu".

Value-permute vẫn là **fallback hợp lệ khi tắt motion** (§5.6) — nhưng không phải substrate
chính.

### H2 — ELEMENT-IDENTITY (phần tử mang id ổn định, position là thuộc tính animate được). **CONFIRMED — đường thắng.**

Luận điểm, mỗi bước tựa evidence:

- **Không phá R-32 (E9).** R-32 ràng buộc *envelope*, không cấm phần tử di chuyển trong nó.
  A4 sweep trong viewport cố định (E7 `bounding_box` cố định) → bbox không đổi. A5 lướt giữa
  các slot đã tồn tại trong hàng → bbox không đổi. **Chuyển động INTRA-envelope ⇒ R-32.1
  giữ nguyên.** Không cần prescan-grow (khác insert/grow của A-6, E11) — đây là điểm khiến
  A4/A5 *dễ hơn* insert về mặt R-32.
- **Tiền lệ đã ship (E3, E5).** `cursor_move` cho caret trượt **bên trong** một Array bbox
  cố định (R-38); `position_move` cho node Tree trượt sau reparent. Cách đọc "SLOT cố định;
  ELEMENT trượt giữa các slot" **không phải phát minh mới** — nó là cách runtime đã hành xử.
- **Đóng nghịch đảo (E2).** Tái dùng `position_move` (self-inverse) → registry vẫn đóng ở
  11 kind → A-2 thoả, không cần kind thứ 12.
- **Tổng quát.** Cùng một substrate phủ: A4 (line[i] dịch), A5 (cell lướt), **và tương lai**
  — BST rotation (node Tree, đã dùng `position_move`), heap sift (hai cell hoán vị vị trí),
  Kruskal edge fly (edge có `data-target` dịch). Tất cả quy về "một phần tử có identity ổn
  định lướt tới ghế mới trong envelope đã reserve".
- **Degrade sạch (E12).** Tắt motion/print → snap tới server SVG đích = layout cuối đúng.

### H3 — Kind mới `element_move` (glide-to-new cho `[data-target]`, để `position_move` đóng băng). **REFUTED (như lựa chọn mặc định) — chỉ là fallback.**

`element_move` = resolve `[data-target]` (như `position_move`) + hình học glide-to-new (như
`cursor_move`), self-inverse. Ưu: additive theo A-2 (ship như triple `{emit, handler,
inverse}`), không đụng golden Tree. **Bác làm mặc định vì:** nó là **kind slide thứ ba gần
trùng lặp** (cùng `position_move`/`cursor_move` chỉ khác resolver/hình học) → phình registry,
đi ngược tinh thần "closed & minimal" của A-2. Hình học của `position_move` vốn *nên* là
glide-to-new (E4 xác nhận ends-at-old là khiếm khuyết, không phải chủ đích). **Sửa** tại chỗ
đúng hơn **nhân bản**. Giữ H3 làm fallback nếu việc re-bless golden Tree bị coi là quá rủi ro.

---

## 5. Thiết kế chi tiết — đường thắng (H2, tái dùng `position_move`)

### 5.1 Substrate (không đổi differ/emitter/runtime cho đường dữ liệu)

Cơ chế E6 đã đủ. Primitive chỉ cần hai thứ, **Python thuần additive**:
1. Một **lệnh mutate-in-place** đổi toạ độ mà **giữ nguyên index** (⇒ `data-target` bất biến
   ⇒ cùng identity ⇒ differ so (x,y) cũ/mới ⇒ `position_move`, không phải add+remove).
2. Method `get_node_positions() → {data_target_key: (x,y)}`.

`_inject_tree_positions` (E6) `hasattr`-duck-type nên **tự nhặt** bất kỳ primitive nào mọc
method này — Plane2D, Array, Matrix, DPTable (E13) đều lên tàu mà không sửa emitter.

### 5.2 Identity key — theo chuẩn sẵn có, không phát minh format mới

- **A4 / Tree / Graph:** phần tử *chính là* thứ di động. Dùng `data-target` sẵn có
  `{shape}.{part}[{i}]` (`p.line[2]`, `p.point[3]`). **Không key mới.**
- **A5 / Array:** có phân tầng. `cell[i]` = **SLOT** (E10: neo annotation, R-42). Để phần
  tử bay mà *vẫn* giữ ngữ nghĩa annotation-bám-slot, ELEMENT phải có identity **rời**:
  `{shape}.item[{k}]`, `k` gán ở t0 và không đổi. `\reorder` hoán vị item→slot; mỗi item lấy
  (x,y) = tâm slot mới → `position_move` trên `item[k]`. Slot `cell[i]` đứng yên (R-42 nguyên
  vẹn). Đây chính là câu trả lời cho "cái gì có identity?": **CẢ HAI, ở hai tầng** — đúng
  tinh thần A-0.ii (`data-target` cells vs `data-annotation` decorations là hai không gian
  identity tách biệt, `motion-ruleset.md:30`).

### 5.3 A4 — Plane2D (thiết kế cụ thể)

- **API tex:** *đừng* thêm verb top-level `\move` (tốn một verb mới). **Tái dùng `\apply`**:
  `\apply{p.line[i]}{to_x=4.0}`, `\apply{p.point[i]}{to=(x,y)}`. `apply_command` mutate dict
  phần tử tại chỗ, giữ index (E7). Rẻ hơn: 0 verb mới, chỉ thêm khoá `to_*` vào bộ dispatch
  `apply_command` sẵn có.
- **Toạ độ bơm — điểm tế nhị RIÊNG của plane2d.** `<g data-target>` của point/line nằm TRONG
  nhóm `scale(sx,sy)` (E7 `:666-669`), trong khi node Tree / cell Array nằm ở tầng SVG-px
  đỉnh. Một `translate(Δ px)` áp lên `<g>` con được diễn giải trong **hệ toạ độ local
  (đã scale)**. Vậy `get_node_positions` của Plane2D phải trả **toạ độ MATH (local)**, không
  phải output `math_to_svg`: khi đó `translate(Δmath)` bên trong `scale(sx,sy)` cho ra
  `Δmath·sx` px = đúng khoảng cách, và `sy<0` tự lo Y-flip. [**Deduced/Hypothesized** — phụ
  thuộc ngữ nghĩa CSS/WAAPI `transform` trên phần tử SVG trong nhóm scaled; cần kiểm chứng ở
  tích hợp.] Nếu không muốn phụ thuộc điều này, phương án thay thế là đưa `<g data-target>` ra
  ngoài nhóm scale (refactor lớn hơn) — không khuyến nghị.
- **bbox/prescan:** sweep trong viewport ⇒ bbox không đổi (E7) ⇒ **không cần prescan-grow**;
  chỉ cần `fs=1` (A-6) để server SVG đích chốt hình học cuối.

### 5.4 A5 — Array/Table reorder (thiết kế cụ thể)

- **API tex:** `\reorder{a}{order=[3,0,1,4,2]}` hoặc `\apply{a}{reorder=[...]}` (tái dùng
  `\apply` — rẻ hơn một verb). Ngữ nghĩa `order` cần chốt tường minh trong spec (gather
  `new[i]=old[order[i]]` vs scatter `new[order[i]]=old[i]`) để tránh mơ hồ.
- **Tầng element (5.2):** khai `item[k]` ở t0. `\reorder` cập nhật ánh xạ item→slot; mỗi
  item lấy (x,y) = tâm slot đích (SVG-px, vì cell Array ở tầng đỉnh — khác plane2d) →
  `position_move`. Value đi *theo* item (đó là điểm khác value-permute: value gắn identity di
  động, không cascade qua slot tĩnh).
- **Annotation:** neo trên `cell[i]` (slot) vẫn đứng yên (R-42). Nếu tác giả muốn annotation
  *bám phần tử bay*, họ neo trên `item[k]` — phân tầng cho họ chọn.
- **bbox/prescan:** hoán vị trong hàng ⇒ mọi đích là slot đã tồn tại ⇒ bbox không đổi ⇒
  không prescan-grow. Bề rộng cell đã là max cross-frame (E8 `_grow_cell_width` monotonic) ⇒
  vị trí slot bất biến ⇒ đích glide ổn định.

### 5.5 Chỉnh sửa runtime DUY NHẤT — sửa hình học `position_move`

Đổi keyframes handler (`scriba.js:213-216`) từ ends-at-old:
```
[ {transform:'translate(dx,dy)'}, {transform:'translate(0,0)'} ]   // dx=from-to  → kết ở GHẾ CŨ
```
sang glide-to-new (đúng công thức `cursor_move` `scriba.js:318-321`):
```
[ {transform:'translate(0,0)'}, {transform:'translate(to-from)'} ] // → kết ở GHẾ MỚI, fs-snap thành no-op
```
DOM base khi tween là frame trước (stage chưa snap tới đích cho tới `_finish`,
`scriba.js:385-398`) ⇒ base = ghế cũ ⇒ `[0 → (new-old)]` lướt cũ→mới sạch. Vì đích đã đúng,
fs-snap (A-6) trở thành *tinh chỉnh*, không còn là **teleport giữa chừng** như hiện nay (E4).
Sửa này **cải thiện luôn Tree/BST rotation**. Self-inverse vẫn giữ (khớp y hệt `cursor_move`
đã chứng minh, E2/E5).

> A4 có thể ship **trước** cả bước này trên `position_move` nguyên trạng (moves nhỏ mỗi step,
> lurch mờ). A5 (hoán vị lớn) **cần** hình học đã sửa để không teleport. Nếu muốn phasing:
> Phase 1 = A4 zero-bump; Phase 2 = sửa hình học (1 bump) + A5. Khuyến nghị làm 1 bump gộp.

### 5.6 Degrade (A-8/R-32.5, E12)

`_canAnim=false` (reduced-motion) hoặc print → `snapToFrame` hiển thị server SVG đích: line ở
intercept cuối, cells ở slot đã hoán vị. Mất nội suy, **layout cuối vẫn đúng**. Đây cũng là
lý do value-permute (H1) là fallback ngữ nghĩa hợp lệ khi không có motion — nhưng không thay
được substrate element-identity khi có motion.

---

## 6. Spec-diff đề xuất (câu chữ cụ thể)

**KHÔNG viết lại normative text của R-32** — nó đúng (envelope invariance). Thêm 3 mẩu:

**(a) Note làm rõ, gắn vào R-32 (`ruleset.md` §8.9):**
> *R-32 ràng buộc **reserved envelope** (bounding-box cực đại cross-frame của primitive),
> không ràng buộc vị trí của từng phần tử mang identity bên trong nó. Một phần tử có
> `data-target` ổn định ĐƯỢC PHÉP dịch chuyển giữa các frame (`position_move`) miễn toàn bộ
> tầm chuyển động nằm trong envelope đã reserve; cái phải bất biến là **envelope**, không phải
> phần tử. Tiền lệ: caret `cursor_move` (R-38) đã trượt bên trong một Array R-32-ổn-định.*

**(b) Note companion, gắn vào R-42 (`smart-label-ruleset.md`):**
> *`cell[i]` là **SLOT-identity** (vị trí cố định, neo annotation). Một visualization reorder/
> sort cần **thấy phần tử di chuyển** đưa vào một **ELEMENT-identity** rời (`item[k]`, gán ở
> t0) mang vị trí di động; `\reorder` hoán vị item→slot, mỗi item glide bằng `position_move`.
> Slot đứng yên (R-42 nguyên vẹn); element di chuyển. "Cái gì có identity" = **cả hai, ở hai
> tầng** — soi chiếu A-0.ii (`data-target` vs `data-annotation`).*

**(c) Mở rộng A-4 (`docs/spec/motion-ruleset.md`):** hiện A-4 chỉ đặt tên marker-identity
(decoration, `cursor_move`). Thêm một dòng nêu **cell/node-identity** (`data-target`,
`position_move`) là đối xứng: *SLOT là neo cố định; ELEMENT là identity di động; hai tầng
cùng tồn tại (Array: `cell`=slot cố định + `item`=element di động).* Ghi rõ hình học chuẩn
của cả `position_move` lẫn `cursor_move` là **glide-to-new-seat** (đồng nhất sau §5.5).

---

## 7. Cost + rủi ro

| Hạng mục | Chi phí | Rủi ro |
|---|---|---|
| Sửa hình học `position_move` (§5.5) | 1 dòng handler; **1 bump `SCRIBA_VERSION 17→18`** + re-bless golden Tree/cursor (E13: bump motion đã tiêu ở 0.23.x nên đây là bump mới) | **Medium** — đổi byte runtime ⇒ mọi trang interactive re-bless; phải xác nhận không scene nào lệ thuộc lurch cũ (không scene lành mạnh nào lệ thuộc) |
| A4 Plane2D: `\apply{..}{to_*}` + `get_node_positions` (math-local) | Python additive; 0 verb mới; 0 đổi differ/emitter/runtime | **Medium** — điểm toạ độ nhóm-scaled (§5.3) cần kiểm chứng tích hợp; ngoài ra low |
| A5 Array/Table: `\reorder`/`reorder=` + tầng `item[k]` | Python additive; tách slot/element trong emit | **Medium** — tầng identity mới trong Array; phải test annotation-bám-slot không hồi quy (R-42) + ngữ nghĩa `order` chốt rõ |
| Matrix/DPTable (2D) | Cùng substrate, thêm `get_node_positions` mỗi primitive | **Low** — đã có `data-target` per-cell (E13) |
| Nếu chọn fallback H3 (`element_move`) thay vì sửa `position_move` | Vẫn 1 bump; +1 kind (12) | **Low-Medium** — không đụng Tree, nhưng phình registry; đi ngược A-2 minimal |

**Rủi ro tổng quát cần canh (bài học `_envelope_n`, E11):** phần tử bay chỉ an toàn khi
**intra-envelope**. Nếu một feature tương lai cho phần tử bay RA NGOÀI bbox (ví dụ pop khỏi
hàng), nó phải **prescan-reserve** vùng đó trước (A-6) y như LinkedList reserve `_envelope_n`
— nếu không mọi frame sau nhảy. A4/A5 hiện tại **không** chạm rủi ro này (đều trong envelope).

---

## 8. Confidence

- **Chẩn đoán R-32 là envelope-invariance, không phải "cell bất động" (chốt của case): High.**
  Đọc thẳng `ruleset.md:941-945`; `cursor_move`/`position_move` đã là bằng chứng vận hành.
- **Substrate element-identity tái dùng được, zero đổi differ/emitter/runtime cho đường dữ
  liệu: High.** `_inject_tree_positions` duck-type `hasattr` (E6) đã Confirmed đường gọi.
- **`position_move` kết-thúc-ở-ghế-cũ và nên sửa thành glide-to-new: High.** Repo tự ghi
  nhận (E4, hai nguồn độc lập) + đọc keyframes.
- **Chi tiết toạ độ math-local của Plane2D (§5.3): Medium.** Phụ thuộc ngữ nghĩa transform
  SVG trong nhóm scaled; chưa chạy probe render phiên này — đánh dấu Deduced/Hypothesized.
- **Tầng `item[k]` cho A5: Medium.** Thiết kế nhất quán với A-0.ii nhưng chưa build; ngữ
  nghĩa `order` và tương tác annotation cần một vòng spec + test trước khi code.

---

## 9. Dependencies — Forest union-glide (trả lời gap-dsu-forest)

3 câu hỏi của gap-dsu-forest về **union = reparent** (`tree.py:411` `_reparent_internal` đã
có). Cả 3 củng cố verdict chính, **không phát sinh cost mới** ngoài fix hình học §5.5.

- **(i) union/reparent = 1 khối hay N `position_move` rời? → N rời, mỗi node một cái.
  [Confirmed]** Substrate per-target: `get_node_positions()` (`tree.py:507-517`) một entry/node
  → differ (`differ.py:218-236`) một `position_move`/node; registry không có kind "khối" (đóng
  11, A-2). `_reparent_internal` → `_relayout()` → `_reingold_tilford` **toàn cục**
  (`tree.py:275-285`) cấp lại toạ độ MỌI node → subtree **không** phải offset cứng (một
  Transition khối-cứng sẽ *sai* vì giãn cách nội bộ đổi dưới parent mới). *Hệ quả thị giác
  [Deduced/Hypothesized]:* N node cùng frame = chung `duration`/easing → đọc như **một khối bay
  liền mạch** vì đó là **một cụm chuyển động mạch lạc** (cùng hướng, không cắt nhau). **Cap
  KHÔNG nằm ở số node trong một subtree** — một cụm mạch lạc đọc sạch tới hàng chục node; cap
  nằm ở **số cụm phân kỳ đồng thời/frame**, giữ ≤ ~4–5 (giới hạn multiple-object-tracking của
  thị giác). Union = **1 cụm** → luôn sạch; step nào làm nhiều subtree bay khác hướng thì **tách
  step**.
- **(ii) identity key có chứa parent? reparent có phá identity? → Không chứa parent; KHÔNG phá.
  [Confirmed]** `_node_key(id)` = `f"node[{id}]"` (`tree.py:497-499`) **thuần id**, không
  parent/path; `node_id` chuẩn-hoá `str` ở construct/add/reparent (`tree.py:414-415`) nên **ổn
  định qua reparent**; `_reparent_internal` (`tree.py:411-476`) chỉ sửa `children_map`/`edges` →
  node giữ `data-target` → **glide, không pop**. **Ràng buộc Forest:** key **thuần id nội tại**,
  KHÔNG nhét `parent`/`root`/DSU-set — key theo root ⇒ mọi union phá identity toàn subtree.
- **(iii) `position_move` (sau fix glide-to-new §5.5) đủ cho union-glide, khỏi kind mới? → Đủ.
  [Confirmed đường dữ liệu / Deduced hình học]** Forest cưỡi đúng substrate Tree
  (`get_node_positions` → `_inject_tree_positions` `emitter.py:202-228` → `position_move`
  `differ.py:218-236`), zero đổi differ/emitter, registry giữ 11. Hình học hiện lurch
  (`scriba.js:213-216` + fs-snap; `differ.py:280`); fix §5.5 (công thức `cursor_move`
  `scriba.js:318-321`) biến thành union-glide sạch — **chung một fix với A4/A5, không thêm bump**
  (vẫn 17→18). Prescan A-6 (gap-dsu-forest nêu) chống bbox nhảy, độc lập kind.

**Chốt Forest phase 2:** reuse `position_move`, N-glide/node, **no block-kind** — MIỄN LÀ node
identity keyed **thuần id** (câu ii). Zero cost mới ngoài fix §5.5 đã tính trong bump 17→18.
