# Cầu nối liên-shape (`\link` / `\combine`) — một máy, ba nhu cầu

> Design investigation (BMAD). **Không sửa source repo.** Driver: JudgeZone pass 3 — team lead
> gộp A2c (dot-product highlight nhân ma trận), C3 (dual-primitive synced highlight, ~6–8 bài) và
> C1 (sweep-line choreography, ~15–20 bài) thành **một họ: cross-shape linkage**.
> Repo @ `main` `bf1bbf6`, đọc trực tiếp trong phiên này. `motion-ruleset.md` / `smart-label-ruleset.md`
> nhắm mốc v0.23.0-dev (một số Code ref còn `pending`).
>
> Thang bằng chứng: **[Confirmed]** = đọc thẳng trong source phiên này (có path:line) ·
> **[Deduced]** = hệ quả logic của fact đã confirm · **[Hypothesized]** = đề xuất thiết kế, chưa dựng.
>
> Phụ thuộc chính: **A4** (`investigations/gap-motion-identity.md`) — **ĐÃ CHỐT**: element-identity thắng,
> **KHÔNG phá R-32** (R-32 ràng buộc *envelope primitive bất biến*, không cấm phần tử trượt **trong** envelope).
> Cơ chế: tái dùng `position_move` (**0 kind mới**); Plane2D sweep = `\apply{p.line[i]}{to_x=4.0}` (**0 verb mới**);
> sửa hình học `position_move` ends-at-old → glide-to-new (**1 handler**). Với C1 (§6): coi sweep glide **đã chạy**. Xem §9.

---

## 1. Hand-off Brief (kết luận nén)

Giả thuyết "3 item = 1 họ" **đúng 2/3**. A2c và C3 **cùng một máy** — một *cầu* liên-shape: hai đầu
mút resolve ở **hai shape khác nhau**, vẽ một `<path>` ở **tầng stage (trên mọi shape)**. C1 (sweep-line)
**KHÔNG cùng họ**: nó không cần đường nối liên-shape nào — sự "đồng bộ 3 shape theo cùng tiến trình sự
kiện" **đã có sẵn miễn phí** vì mỗi `\step` là một snapshot toàn cục (A-0.i/.ii), còn cây kim sweep là
**line native của plane2d** (`plane2d.py:271,395,852` **[Confirmed]**). C1 là **RECIPE + phụ thuộc A4**,
không phải feature; cầu chỉ là *đường* tuỳ chọn cho C1, không bắt buộc.

Về data model (§4): đề xuất **MỘT** entry mới `LinkEntry` (hai/nhiều selector + color + ephemeral),
soi gương `AnnotationEntry` — vốn **đã mang hai selector** `target` + `arrow_from` (`scene.py:122-130`
**[Confirmed]**) nhưng bị khoá về một shape ở tầng bucketing. **MỘT** verb `\link` phủ cả tĩnh (C3, persistent)
lẫn động (A2c, `ephemeral=true`), đúng như `\annotate` đã phủ persistent + ephemeral; `\combine{srcs}{into=}`
là sugar/alias của cùng entry, **không** cần verb thứ 20 (§4.3). Hệ hiện có **đúng 18 lệnh** **[Confirmed]**.

Về emit (§5): đây là **máy mới thật** nhưng **bị chặn biên** — một *tầng annotation cấp-scene* chèn một
`<g><path/></g>` vào đúng khe `_frame_renderer.py:886→888` (sau vòng lặp shape, trước `</svg>`, top-of-z)
**[Confirmed]**; nó **tái dùng** resolver per-shape (`resolve_annotation_point`) và dữ liệu offset đã chảy
sẵn qua kênh `scene_segments`/`self_offset` (nay chỉ dùng để né obstacle) — chứ không dựng hệ toạ độ mới.

Về motion (§7): cầu **tĩnh/ephemeral** là *decoration cưỡi `annotation_add`/`_remove`/`_recolor` — 0 dòng
runtime, 0 version bump* (soi tiền lệ `\trace`: `differ.py:246-270` **[Confirmed]**). Chỉ cầu **persistent-mà-di-chuyển**
mới cần một kind `link_move` (một handler, một bump) — **hoãn** đến khi có bài thật cần (YAGNI; giống
`cursor_move` chỉ thêm khi caret thật sự cần: `differ.py:311-315` **[Confirmed]**).

Phased (§8): **A4** (dep — **đã chốt**) → **P1 C3 `\link` tĩnh** (tổng quát nhất/chi phí) → **P2 A2c `\combine`
ephemeral** (tái dùng entry+emit của P1) → **P3 C1 = doc recipe** (không máy mới; sweep glide do A4 cấp, 0 verb).

---

## 2. Phán quyết giả thuyết: XÁC NHẬN A2c+C3, TÁCH C1

| Item | Bản chất | Cần *đường nối* liên-shape? | Cùng "máy cầu"? | Cơ chế thật sự cần |
|---|---|---|---|---|
| **A2c** `\combine{m.row[i],m.col[j]}{into=c.cell[i][j]}` | 2 nguồn (1–2 shape) → 1 đích (shape khác), vẽ liên kết **đổi mỗi frame** | **Có** | **Có** (động/ephemeral) | LinkEntry ephemeral + emit cấp-scene + rides `annotation_add/_remove` |
| **C3** dual-primitive synced (tree↔array Euler, grid↔graph) | mapping **cố định suốt animation**; recolor vế trái → sáng vế phải | **Có** | **Có** (tĩnh/persistent) | LinkEntry persistent + (tuỳ chọn) mirror-recolor ở scene-apply |
| **C1** sweep-line (Geometry + Mo's) | 1 line chạy + event-queue + status-set, **3 shape đồng nhịp** | **Không** (đường nối là *tuỳ chọn*) | **Không** | `\step` (đồng bộ toàn cục sẵn) + **A4** (`\apply{p.line[i]}{to_x=}` = `position_move` glide, 0 verb/kind mới) + kỷ luật authoring |

**Kết luận [Deduced].** "Cầu" là một họ **hai thành viên** (A2c động + C3 tĩnh) chia nhau đúng *một* máy mới:
**resolver hai-đầu-mút cấp-scene + emit overlay cấp-stage**. C1 là thứ thứ ba, **rẻ hơn và khác loại** — một
*recipe* đã được frame-model thoả mãn, cưỡi A4; cầu chỉ *phục vụ* C1 như đường trang trí tuỳ chọn (nối điểm
sweep ↔ ô event-queue ↔ ô status-set) chứ C1 không *đòi* nó. Đây là điểm tinh chỉnh so với giả thuyết gốc:
thiết kế **một** lần (cầu) dùng **hai** nơi (A2c, C3); nơi thứ ba (C1) tiêu thụ A4 + docs, không tiêu thụ cầu.

---

## 3. Substrate đã xác nhận (nền của mọi luận điểm)

### 3.1 Stage compose = **nối chuỗi phẳng, không có tầng overlay** — nhưng khe chèn tồn tại
- Đa-shape lắp trong `_emit_frame_svg` (`_frame_renderer.py:623`); vòng lặp mỗi shape một `<g>`
  (`:766`), bọc `<g transform="translate({x_offset},{y_cursor})">` (`:806`), đóng `</g>` (`:884`). **[Confirmed]**
- **Không có** `<g>` overlay cấp-stage; SVG là concat các nhóm shape. Vì z-order = thứ tự tài liệu, khe
  đúng để chèn `<path>`/`<line>` **cắt ngang các shape** là **sau `:886` (hết vòng lặp) và trước `:888`
  (`</svg>`)** — chèn ở đó nằm **trên toàn bộ nhóm shape**. Khe này có sẵn `vb_width`, `_prim_offsets`,
  `_PADDING`, `_PRIMITIVE_GAP` trong scope. **[Confirmed]**
- Hai post-pass sau đó (`_apply_defocus` `:893`, `_apply_ref_marks` `:894`) chỉ regex viết lại class trên
  `<g data-target=…>` sẵn có; **không** thêm phần tử, và không đụng `<g transform>` bọc-shape (chúng vô danh).
  Nên một `<path>` chèn ở khe trên là an toàn. **[Confirmed]**

### 3.2 Toạ độ: render **local**, offset qua `<g>`; chỉ **Y** được lưu, **X** phải tính lại
- Primitive render ở toạ độ **shape-local** (bbox/emit_svg giả định gốc 0,0); `<g transform>` dịch sang
  **stage-global**. **[Confirmed]** `_frame_renderer.py:793,865-871`.
- Y lấy từ `reserved_offsets` (`:801`, tính ở `measure_scene_layout` `:317-321`, stitcher giữ ở
  `_html_stitcher.py:219`). **X luôn tính lại** `(vb_width - bw)//2` (`:802`) — **X không được lưu** (trong
  `reserved_offsets` thành phần x = `0.0`, `:320`; `_prim_offsets` là biến local không return, `:740-751`).
  **[Confirmed]** → **Gotcha cho cầu:** để đặt đầu mút ở stage-global phải **tự tính lại X** đúng công thức
  đó và **không** tin thành phần x đã lưu.
- Đã có kênh chảy sẵn toạ độ shape-lạ: `scene_segments` gắn scene-offset mỗi primitive (`:755-763`), truyền
  qua `prim.emit_svg(..., self_offset=…)` (`:862-869`); base gộp ở `base.py:1105-1114`. Nay **chỉ dùng để né
  obstacle**, chưa dùng làm đầu mút — nghĩa là *dữ liệu offset cần cho cầu đã chảy vào, chỉ chưa được dùng*. **[Confirmed]**

### 3.3 Annotation spine **khoá-một-shape ở đúng 3 chỗ**; model & differ thì **đã shape-agnostic**
- `AnnotationEntry` frozen (`scene.py:118-130`): `target, text, ephemeral, arrow_from, color, position,
  arrow, bracket, leader`. **Không** field `id/key/shape/kind`; identity **suy ra lúc diff** =
  `(target, arrow_from or "solo")` (`differ.py:243`). Model **đã mang hai selector** (`target`+`arrow_from`)
  → *về mặt dữ liệu* đã đủ để trỏ hai shape. **[Confirmed]**
- **Khoá-một-shape thực thi ở 3 điểm, đều cục bộ:**
  1. **Bucketing** theo tiền tố shape của `target`: `_html_stitcher.py:160`, `_frame_renderer.py:294-295`
     & `:770-771` — `if a.get("target","").startswith(shape_name + ".")`. **[Confirmed]**
  2. **Resolve hai đầu mút bằng cùng `self`**: `base.py:1253-1254`
     (`src=self.resolve_annotation_point(arrow_from)`, `dst=self.resolve_annotation_point(target)`); selector
     ở shape khác → `None` → soft-drop `:1255-1256`. `resolve_annotation_point` mặc định `None` (`base.py:764`),
     mỗi primitive override chỉ map cell/node **của chính nó**. **[Confirmed]**
  3. **Offset** chỉ có Y lưu (đã nói §3.2). **[Confirmed]**
- **Differ đã shape-blind**: `_diff_annotations` (`differ.py:319-374`) so khoá chuỗi mờ, không hề soi shape;
  key composite `f"{key[0]}-{key[1]}"` (`:336`); kind `annotation_add` (`:347`), `annotation_remove` (`:357`),
  `annotation_recolor` (`:370`). Một annotation liên-shape sẽ **diff đúng** không cần sửa. **[Confirmed]**
- Lifecycle: persistent mặc định, ephemeral nếu cờ; ephemeral bị xoá đầu mỗi `\step`
  (`scene.py:259`: `self.annotations = [a for a in self.annotations if not a.ephemeral]`). **[Confirmed]**

### 3.4 `\trace` = **tiền lệ gần nhất** (đường nối đa-đỉnh, cưỡi `annotation_add`, 0 JS)
- `_diff_traces` (`differ.py:246-270`): key `f"{target}.trace[{id}]-solo"` (`:253`); trace mới → `annotation_add`
  (`:261-264`), mất → `annotation_remove` (`:266-269`) — **không** move/recolor. Runtime *draw-on* qua
  stroke-dashoffset, **0 thay đổi JS** (R-37 `smart-label-ruleset.md:549`). **[Confirmed]**
- Nhưng `\trace` **intra-shape** (đa *cell* trong **một** `{shape}`). Cầu khác ở **scope**: hai `data-target`
  ở **hai shape**, nên khoá `{shape}.` không đặt được — cần key **cấp-stage không tiền-tố-shape** (§7). **[Confirmed]**
- `emit_cursors_under` (`base.py:624`) vẽ caret `<polygon>` từ band dưới hàng, key `{shape}.cursor[{id}]-solo`,
  cưỡi `annotation_add/_remove` + `cursor_move` (`base.py:631`). ⇒ A4-caret là **polygon nhỏ**, **không** phải
  line full-height — nên cây kim sweep của C1 dùng **line native plane2d**, không dùng caret. **[Confirmed]**

### 3.5 Đếm verb & năng lực plane2d
- **Đúng 18 lệnh** (grep parser, phiên này): `annotate, apply, compute, cursor, endforeach, endsubstory,
  focus, foreach, highlight, invariant, narrate, playeach, reannotate, recolor, shape, step, substory, trace`.
  `\link`+`\combine` = #19, #20 → +11% bề mặt verb. **[Confirmed]**
- Plane2d **đã có line**: `_add_line_internal` (`plane2d.py:271`), param `add_line`/`remove_line` (`:395/:411`),
  `_emit_lines` (`:852`), line dọc + clip viewport (`:872-875`), kind emit `plot_line` (`:1306`). ⇒ cây kim
  sweep là **line có sẵn**, dời = re-emit ở x mới + `fs=1` resync (A-6). **[Confirmed]**

---

## 4. Q1 — Cầu là GÌ trong data model?

### 4.1 Một entry `LinkEntry`, hai front-end authoring
**[Hypothesized]** Đáy chung là **một** frozen dataclass mới, soi gương `AnnotationEntry`:

```
LinkEntry(frozen): endpoints: tuple[str, ...]   # ["m.row[i]","m.col[j]"] hoặc ["T.subtree[v]","a.range[..]"]
                   into: str | None             # đích của \combine (A2c); None cho \link đối xứng
                   color: str = "info"; ephemeral: bool = False
                   mapping: str | None = None    # id mapping tĩnh (C3) để mirror-recolor
```

- **C3 = mapping TĨNH (phương án a):** `\link{T.subtree[v] <-> a.range[in[v]:out[v]]}` khai một lần ở prelude →
  LinkEntry **persistent** (sống qua frame, không bị `scene.py:259` xoá). Tần suất ~6–8 bài. "Mọi recolor vế
  trái tự áp vế phải" là **khuếch đại ngữ nghĩa** (1 hành vi authoring → 2 hiệu ứng) — rẻ nhất là để
  `apply_frame` **mở rộng** rule mirror lúc scene-apply (một `\recolor T.subtree[v]` sinh thêm `\recolor
  a.range[..]`), chứ không phải một máy vẽ mới. **[Hypothesized]**
- **A2c = verb ĐỘNG (phương án b):** cặp nguồn→đích đổi mỗi frame → LinkEntry **ephemeral** (xoá mỗi `\step`
  y hệt highlight, `scene.py:259`). **[Hypothesized]**
- ⇒ Chọn **(c) cả hai**, nhưng **thống nhất về một entry type** — không phải hai máy. Static/dynamic chỉ là
  cờ `ephemeral` + có/không `mapping`, đúng mô hình `\annotate` đã phủ persistent+ephemeral bằng một cờ.

### 4.2 Chi phí verb & tổng quát
- `\combine` args (`{[[..],[..]]}{into="..."}`) **parse hôm nay 0 thay đổi lexer/value**: list lồng đã hợp lệ
  (`ast.py:38` `ParamValue` tự-tham-chiếu, đã được `\trace` chứng minh bằng execution
  `feat-trace-primitive.md:91-100`), `into="…"` là param string thường. **[Deduced]**
- Thêm cả `\link` **và** `\combine` = 20 verb. Khuyến nghị **một verb `\link`** phủ cả hai; `\combine{srcs}{into=}`
  chỉ là **alias/sugar** dựng cùng `LinkEntry` (endpoints=srcs, into=…, ephemeral=true) — giữ ngân sách ở **19**.
  Chỉ tách `\combine` thành verb riêng nếu ecgônômi authoring ma-trận thật sự đòi (hoãn quyết đến P2). **[Hypothesized]**

### 4.3 Chấm điểm Q1
| Tiêu chí | Kết |
|---|---|
| Tần suất bài thật | C3 ~6–8, A2c một họ ma-trận → **đủ để đáng một máy**, nhưng **một** verb là đủ |
| Chi phí verb mới | +1 verb (`\link`), sugar cho `\combine` → **+5.5% bề mặt**, không +11% |
| Tổng quát | Một `LinkEntry` phủ cả tĩnh (mapping) lẫn động (ephemeral) — **cao** |

---

## 5. Q2 — Liên kết VẼ thế nào? (đây là máy mới thật, nhưng bị chặn biên)

**[Hypothesized]** Một **tầng annotation cấp-scene** (mới), khác hẳn spine per-shape:

1. **Resolver hai-đầu-mút cấp-scene.** Với mỗi endpoint, tra shape sở hữu → gọi `resolve_annotation_point`
   **của primitive đó** (tái dùng, không viết lại), rồi cộng offset stage: **Y** từ `reserved_offsets`
   (`_html_stitcher.py:219`), **X** tính lại `(vb_width-bw)//2` (`_frame_renderer.py:802` — gotcha §3.2).
   Đây là chỗ *phá* khoá-một-shape ở `base.py:1253-1254` một cách có kiểm soát: thay "cùng `self`" bằng
   "resolver có bảng `shape→primitive`". **[Hypothesized]**
2. **Bucketing riêng.** LinkEntry **không** đi qua filter tiền-tố-shape (`_html_stitcher.py:160`,
   `_frame_renderer.py:294-295`,`:770-771`) — nó là entry **cấp-scene**, gom vào một rổ scene, không rổ shape. **[Hypothesized]**
3. **Emit overlay.** Sinh **một** `<g data-annotation="link[{from}|{to}]-solo"><path .../></g>` và append ở khe
   `_frame_renderer.py:886→888` (top-of-z, §3.1). Đường nối = Bezier/polyline giữa các đầu mút stage-global. **[Hypothesized]**

**Chi phí (trung thực): "máy mới" = 1 resolver-dispatcher cấp-scene + 1 hàm emit + 1 rổ bucket.** Nhưng nó
**tái dùng** (a) toàn bộ resolver per-shape đã có, (b) dữ liệu offset **đã chảy sẵn** qua `scene_segments`/
`self_offset` (`base.py:1105-1114`; nay chỉ né obstacle). Không dựng hệ toạ độ mới, không đụng runtime
(§7). So với việc "thêm một primitive" thì rẻ hơn; so với "cưỡi spine per-shape" thì **không** cưỡi được vì
spine khoá-một-shape ở 3 chỗ (§3.3). Kết: **đáng làm một lần, dùng cho A2c+C3.** **[Deduced]**

---

## 6. Q3 — C1 sweep-line cần GÌ mới? — **RECIPE, không feature**

**[Deduced]** `\step` **đã** làm mỗi frame là snapshot toàn cục đồng bộ **mọi** shape (A-0.i/.ii,
`motion-ruleset.md:29-30`). Nên "3 shape đồng nhịp theo tiến trình sự kiện" là **miễn phí** — không cần máy mới.

**Phác closest-pair sweep bằng lệnh hiện có + A4** (pseudo-authoring):

```
\shape{P}{Plane2D}{points=[...]}          # điểm + cây kim sweep (line native, plane2d.py:271/395)
\shape{Q}{Array}{data=[...]}              # event-queue: hoành độ đã sort
\shape{S}{Array}{data=[]}                 # status-set (theo tung độ), ordered
# mỗi sự kiện = MỘT \step:
\step: \apply{P.line[i]}{to_x=e.x}        # dời cây kim tới e.x = position_move GLIDE (A4, 0 verb/kind mới)
       \highlight{Q.cell[k]}              # sự kiện hiện tại trên queue
       \apply{S}{...insert e...}          # cập nhật status-set
       \highlight{S.cell[j-1]}, \highlight{S.cell[j+1]}   # 2 hàng xóm để so k/c cặp
```

**Đúng chỗ thiếu (trung thực), cập nhật theo A4 đã chốt:**
- **(a) Cây kim mượt — ĐÃ ĐÓNG bởi A4.** Verdict A4: `\apply{p.line[i]}{to_x=…}` cưỡi `position_move` (0 verb/kind
  mới), sửa hình học ends-at-old → glide-to-new (1 handler, **trong scope A4**). Sweep intra-viewport **không đổi
  bbox** nên R-32 không bị đe doạ. ⇒ C1 **không** cần thêm gì cho cây kim ngoài A4. **[Confirmed via A4 verdict]**
- **(b) Đường nối điểm-sweep ↔ ô-queue ↔ ô-status.** Đây mới là chỗ cầu (A2c/C3) *có thể* giúp — nhưng **tuỳ
  chọn**, không bắt buộc để C1 chạy. **[Deduced]**
- **(c) Kỷ luật authoring.** "1 `\step` = 1 event", status-set = một Array/Tree thường, event-queue sort trước.
  Đây là **pattern trong docs**, không phải feature. **[Hypothesized]**

⇒ **C1 xuất xưởng dưới dạng RECIPE doc, cưỡi A4 (đã chốt).** Với A4 đã cấp sweep glide (0 verb mới), **cả ba
"chỗ thiếu" đều không phải máy mới**: (a) do A4, (b) tuỳ chọn = cầu, (c) là docs. C1 **không** nằm trong feature
cầu; cầu là *nâng cấp tuỳ chọn*. Backbone Geometry + Mo's thành lập được **ngay khi A4 xong, chưa cần cầu**. **[Deduced]**

---

## 7. Q4 — Motion / A-rules

- **Không phải emphasis (A-3).** Emphasis là salience thoáng qua, để SVG nghỉ **byte-identical** và **không**
  ghi state persistent (`motion-ruleset.md:82-96`). Đường nối là **decoration thật, nằm trong SVG nghỉ**
  (measured==painted) → là *decoration*, không phải emphasis. **[Deduced]**
- **Cầu tĩnh/ephemeral KHÔNG cần kind mới.** Soi `\trace` (`differ.py:246-270`): xuất hiện/biến mất cưỡi
  **`annotation_add`/`annotation_remove`** sẵn có; recolor cưỡi `annotation_recolor`. Runtime **structure-driven**
  (A-0.i) chỉ thấy `data-annotation` + `<path>`, **không** biết "cái này cắt hai shape" → animate **miễn phí**,
  measured==painted (A-0.iv `motion-ruleset.md:32`, R-30 `smart-label-ruleset.md:1205`): server viết đúng bytes
  của path, `fs=1` snap tới, WAAPI draw-on chỉ là mỹ phẩm. **Thoả A-2 (registry đóng) mà 0 kind mới, 0 bump.** **[Deduced]**
  - A2c *ephemeral* → xoá + thêm lại mỗi `\step` (`scene.py:259`) → thuần add/remove (fade), **cũng miễn phí**. **[Deduced]**
- **Chỉ cầu persistent-mà-DI-CHUYỂN mới cần `link_move`.** Nếu một link persistent có đầu mút đổi cell và muốn
  path **tái-neo liên tục** (không fade-out/in) thì cần một kind `link_move` (một handler + inverse + một bump) —
  đúng lý do `cursor_move` phải thêm (`differ.py:311-315`; `position_move` kết thúc ở ghế **cũ**, R-38
  `smart-label-ruleset.md:578`). **Khuyến nghị HOÃN** (YAGNI): chưa bài nào trong A2c/C3 đòi path di chuyển liên
  tục — A2c ephemeral đã đủ, C3 mapping cố định. **[Hypothesized]**
- **Mở rộng data-annotation contract = đúng MỘT thứ:** một namespace key **cấp-stage, không tiền-tố-shape**,
  ví dụ `link[{from}|{to}]-solo` (khác `{shape}.trace[..]`). Differ đã shape-blind (`differ.py:336`) nên diff key
  `link[..]` **0 sửa**. Đây là "structure contract → runtime free" của bài học D-rules: geometry server-authored
  + key ổn định ⇒ diff/animate hiện có lo hết (R-37 `:549`, R-38 `:571`, R-40 `:647`). **[Deduced]**
- **A-8 reduced-motion:** SVG nghỉ đã hiện đường nối → tắt animation chỉ mất phần vẽ-dần. Miễn phí. **[Deduced]**

---

## 8. Đề xuất phased

| Phase | Nội dung | Máy mới? | Bump? | Phụ thuộc |
|---|---|---|---|---|
| **P0** | **A4** — marker=identity + slide (`cursor_move`, + line-slide cho plane2d) | có (runtime) | **1 bump** (gộp) | — (gap-motion-identity) |
| **P1** | **C3 `\link` tĩnh** — `LinkEntry` persistent + resolver cấp-scene + emit overlay; mirror-recolor ở scene-apply (tuỳ chọn) | có (Python cấp-scene) | **0** (additive; trừ khi ship CSS `.scriba-link*`) | substrate §3 |
| **P2** | **A2c `\combine` ephemeral** — tái dùng `LinkEntry`+emit của P1; thêm xoá-ephemeral + dạng 2-nguồn-1-đích | không (mở rộng P1) | **0** | P1 |
| **P3** | **C1 sweep-line = RECIPE doc** — pattern "1 `\step` = 1 event"; cây kim = line plane2d; cầu là tuỳ chọn | **không** | **0** | **A4** (P0) |
| ~~P4~~ | ~~`link_move` (cầu persistent di chuyển)~~ | có (1 handler) | 1 bump | **HOÃN** tới khi có bài thật |

**Vì sao P1 (C3) trước:** tổng quát nhất trên chi phí — mapping tĩnh chạm đủ 3 điểm khoá (§3.3) một lần, và
"khuếch đại recolor" cho ROI cao nhất/bài. A2c (P2) chỉ là ephemeral hoá cùng entry. C1 (P3) tách hẳn, chờ A4.

**Ngân sách bump:** theo `motion-ruleset.md:246` ("spend one bump") — nếu cầu ship CSS state-class `.scriba-link*`
thì **gộp** vào đúng bump runtime-motion của A4 (P0), để corpus re-bless **một lần**.

---

## 9. Dependencies

- **A4 (BẮT BUỘC cho C1, TUỲ CHỌN cho cầu):** `gap-motion-identity.md` — marker=decoration có identity, slide
  `cursor_move` (`differ.py:273-316` **[Confirmed]** đã có cho caret; cần tổng quát cho **line plane2d** để sweep
  mượt). Cầu **tĩnh/ephemeral KHÔNG cần A4**; chỉ *cầu di chuyển* (P4, đã hoãn) mới cần motion generalization.
- **Substrate offset (ĐÃ CÓ, tái dùng):** `reserved_offsets` Y (`_html_stitcher.py:219`), X tính lại
  (`_frame_renderer.py:802`), kênh `scene_segments`/`self_offset` (`base.py:1105-1114`). Không phải làm mới.
- **Differ (ĐÃ CÓ, 0 sửa):** shape-blind (`differ.py:319-374`).
- **Version:** batch CSS cầu vào bump motion của A4 (`motion-ruleset.md:243-249`).

---

## 10. Rủi ro / câu hỏi mở

1. **Gotcha X-offset (CAO).** X stage-global **không lưu**, phải tính lại `(vb_width-bw)//2` và `bw` chỉ sống
   thoáng trong vòng lặp render (`_frame_renderer.py:802`). Resolver cấp-scene phải chạy **trong/sau** vòng lặp
   để có `bw`, hoặc measure_scene_layout phải trả thêm X thật. **Cần chốt trước khi code.** **[Confirmed gotcha]**
2. **Reflow R-32 (TRUNG BÌNH).** Đường nối cấp-stage vẽ *trên* shape, không vào `bounding_box()` → không nới
   envelope → không đe doạ R-32; nhưng nếu endpoint neo vào cell **dời** giữa scene thì path phải theo — với
   tĩnh/ephemeral (re-author mỗi frame + `fs=1`) là an toàn. **[Deduced]**
3. **Ngữ nghĩa mirror-recolor C3 (TRUNG BÌNH).** Mở rộng ở `apply_frame` có nguy cơ vòng lặp/nhân đôi nếu mapping
   hai chiều `<->`; cần định nghĩa hướng khuếch đại (trái→phải) rõ. **[Hypothesized]**
4. **Số đầu mút A2c.** `\combine` 2-nguồn-1-đích: vẽ 2 path hội tụ về `into`, hay 1 path chữ V? Ảnh hưởng key
   (`link[a+b|c]`) và diff. Chốt ở P2. **[Hypothesized]**
5. **`\combine` = verb riêng hay sugar?** Giữ 19 verb (sugar) trừ khi authoring ma-trận đòi. Chốt cuối P2. **[Hypothesized]**
