# Byte-identity ở tầng ASSET chung (scriba.js CORE + shared CSS)

> **Điều tra thuần — KHÔNG sửa source, KHÔNG commit.** Repo @ `main` (18443bb),
> scriba 0.23.1 → SCRIBA_VERSION **18** (`scriba/_version.py:6`). Driver: hunt-regression
> phát hiện claim "feature-free doc byte-identical" vỡ ở tầng asset (không phải marker
> primitive rò — cái đó gate ĐÚNG, 0 rò). Probe: `scratchpad/bmad-assets/`.
> Cấp bằng chứng: **[V]** = đã đọc code/đo trực tiếp · **[D]** = suy luận từ [V] · **[G]** = giả định.

---

## Hand-off Brief (đọc cái này trước)

- **Câu hỏi:** claim-accuracy hay nên GATE asset per-feature?
- **Trả lời: (a) — chỉ sửa CLAIM/doc. Không gate.** Hợp đồng cache THẬT được viết trong spec
  là `nguồn giống + SCRIBA_VERSION giống ⇒ HTML byte-identical` (`docs/spec/svg-emitter.md:787-789`,
  `docs/spec/environments.md:34`). Nó **không hề hứa** byte-identity XUYÊN version. Bump 17→18 CHÍNH LÀ
  cơ chế hợp đồng dùng để nói "bytes đã dịch, xoay cache" — nên việc glide/`.scriba-link` đổi byte cho
  doc feature-free là ĐÚNG hợp đồng, không phải vi phạm.
- **Claim overreach ở đâu:** câu "group-free/link-free documents byte-identical" ĐÚNG ở tầng
  **markup/primitive, TRONG cùng v18** (0 marker rò — hunt-regression xác nhận; `\group` = inline attr,
  `\link` gate ở overlay-emit) nhưng cách đọc "asset bytes không đổi 17→18" thì SAI — và chưa bao giờ là hợp đồng.
- **Đính chính phụ:** brief nói "`.scriba-link`/`.scriba-group` CSS". Thực tế **chỉ `.scriba-link`** chạm
  shared CSS; **`.scriba-group` có 0 dòng CSS** (dùng inline presentation attr, `_version.py:180-186` xác nhận).
- **Confidence: CAO** cho (a). Xem §5.

---

## 1. Cơ chế inline hiện tại — cả JS và CSS đều VÔ ĐIỀU KIỆN, MỖI widget/trang

### 1a. JS — CORE slice nguyên khối, verbatim [V]

- Inline script được dựng bởi `_build_inline_script` (`scriba/animation/_script_builder.py:102-114`),
  gọi từ `_html_stitcher.py:637` khi `inline_runtime=True` (mặc định).
- Nó **cắt nguyên vùng sentinel** `// __SCRIBA_CORE_START__` .. `// __SCRIBA_CORE_END__`
  (`scriba.js:25-462`) bằng một `str.split` duy nhất (`_script_builder.py:72`), bọc `W`/`frames` quanh nó.
  Đây là thiết kế CHỐNG-DRIFT có chủ đích: module "authors NO runtime JS anymore" (`_script_builder.py:8-14`).
- **Đo:** CORE slice = **22,462 B**, nhúng vào MỌI animated widget bất kể doc dùng motion-kind nào.
  11 nhánh kind đều hiện diện: `recolor, value_change, position_move, cursor_move, annotation_add/remove/recolor,
  element_add/remove, highlight_on/off`. Glide rewrite (W2) nằm trong handler `position_move` DÙNG CHUNG
  (`scriba.js:217-230`) — nên nó đổi byte cho cả 91 doc animated. [V]

### 1b. CSS — base sheet nguyên khối, luôn khai báo [V]

- `AnimationRenderer.render` khai báo **vô điều kiện** `scriba-animation.css` + `scriba-scene-primitives.css`
  (`renderer.py:727-730`). **Đo:** `scriba-scene-primitives.css` = **49,059 B** luôn inline.
- `.scriba-link > path` (W3) nằm NGAY TRONG base sheet đó (`scriba-scene-primitives.css:610-622`,
  566 B kèm comment / 149 B phần rule) → thêm nó đổi byte cho cả 105 doc (animated + diagram đều ship base). [V]
- `.scriba-group`: **0 dòng CSS** (grep 0 match trong `static/`). Chỉ token `--scriba-link` (4 chỗ) bị tái dùng
  làm `--scriba-widget-focus-ring` (`css:103`) → token KHÔNG gỡ được; chỉ rule `.scriba-link > path` mới gate được. [V]

### 1c. "Doc tối giản nhúng bao nhiêu asset thừa" [V/D]

- 1 doc Array-recolor tối giản nhúng **~22.5KB JS CORE + ~49KB base CSS ≈ 71.5KB** shared asset, gần như
  toàn bộ không liên quan tới 1 primitive của nó. **Nhưng đây là "dead-weight luôn hiện diện", KHÁC vấn đề
  byte-IDENTITY.** Cái đổi 17→18 cho doc feature-free chỉ là: glide (JS, 91 doc) + `.scriba-link` (CSS, 105 doc). [D]

## 2. Cơ chế gate sẵn có — có TIỀN LỆ, nhưng key theo SHAPE không theo VERB [V]

- `_PRIMITIVE_CSS` (`renderer.py:66-69`) = `{Plane2D→scriba-plane2d.css, MetricPlot→scriba-metricplot.css}`;
  chỉ nhúng khi `shape.type_name` hiện diện, lặp qua `ir.shapes` (`renderer.py:733-736`, và bản diagram 1051-1054).
- ⇒ Tiền lệ gate CSS per-feature CÓ, nhưng nó key theo **primitive shape hiện diện**. `\link`/`\combine` là
  **overlay verb (annotation bridge), KHÔNG phải shape** — không nằm trong `ir.shapes`. Nên gate `.scriba-link`
  cần hook phát hiện KHÁC (kiểu "IR này có emit phần tử `.scriba-link` không?"), nhiều ống nước hơn ca Plane2D. [D]
- JS: CORE là 1 slice sentinel nguyên khối theo thiết kế; tách handler per-feature = TÁI TẠO đúng cái dual-runtime
  drift mà `_script_builder.py` sinh ra để diệt (`_script_builder.py:8-14`). [V]

## 3. Hợp đồng cache THẬT — key theo `(source, SCRIBA_VERSION)`, KHÔNG xuyên-version [V]

- `docs/spec/svg-emitter.md:787-789`: *"...content-hash cache in `tenant-backend`: **identical source + identical
  Scriba version = identical HTML = identical cache key.**"*
- `docs/spec/environments.md:34`: *"Identical source + identical Scriba version produce byte-identical HTML —
  the consumer's content-hash cache continues to work."*
- Consumer thật duy nhất trong repo: `pipeline.py:330` `versions={"core": SCRIBA_VERSION}` (đóng vào cache key).
- ⇒ Không consumer nào kỳ vọng byte-identity XUYÊN 17→18. Bump = tín hiệu hợp đồng "mọi cache key xoay". [V]
  Glide + `.scriba-link` đổi byte cho doc feature-free **nằm trong** hợp đồng, vì version đã bump. [D]

## 4. Đánh giá 3 lối

| | Giá trị thực | Chi phí | Rủi ro | Phán |
|---|---|---|---|---|
| **(a) Chỉ sửa claim/doc** | CAO — khớp hợp đồng thật; 0 consumer cần byte-identity xuyên-version | ~0 (chỉ chữ) | Không | **CHỌN** |
| **(b) Gate `.scriba-link` CSS** | THẤP — tiết kiệm ~149–566 B/trang cho doc link-free; khôi phục "CSS byte-identity xuyên-version" mà KHÔNG ai cần | TRUNG — hook phát hiện overlay-verb (không phải shape), file CSS gated mới, test; **và bản thân việc tách lại đổi byte ⇒ 1 bump nữa** | THẤP-TRUNG | Không |
| **(c) Gate JS glide/handler** | THẤP — CORE 22.5KB gần như toàn generic; nhánh per-kind chỉ vài trăm B; gzip/minify đã gộp | CAO — phá slice chống-drift, module JS per-feature, SRI/hash mỗi biến thể, test khổng lồ | CAO — tái tạo đúng drift `_script_builder.py` diệt | Không |

## 5. Kết luận + Confidence

**Khuyến nghị: (a) — chỉ sửa CLAIM.** Không gate CSS, không gate JS. Lý do: hợp đồng byte-identity mà một
consumer THẬT (`tenant-backend` content-hash cache) dựa vào được spec viết rõ là `(source, SCRIBA_VERSION)`,
và bump 17→18 đã honour nó. "Asset byte-identity xuyên-version" không phải mục tiêu, chưa bao giờ được hứa; gate
(b)/(c) tốn công + tự đẻ thêm bump để mua một thuộc tính không ai tiêu thụ. Byte-identity DUY NHẤT quan trọng
(markup không rò feature giữa doc, TRONG cùng version) đã ĐÚNG — hunt-regression xác nhận 0 marker rò.

**Confidence: CAO.** Cơ chế inline (§1) đọc trực tiếp; hợp đồng cache (§3) là spec normative viết thẳng công thức;
tiền lệ gate (§2) đọc trực tiếp. Điểm mềm duy nhất **[G]**: giả định không có consumer ngoài repo diff CSS theo byte
TRONG cùng version (nếu có, chỉ khi đó (b) mới có giá trị — nhưng vẫn phải kèm 1 bump).

## 6. Fix direction (nếu team-lead chọn (a))

1. **Phát biểu lại claim** trong commit/CHANGELOG thành, đại ý:
   *"Tại SCRIBA_VERSION 18, doc không dùng `\link`/`\group` không mang MARKUP `\link`/`\group` (gating overlay
   chính xác, 0 marker rò). Shared inline runtime (`scriba.js` CORE) và shared stylesheet
   (`scriba-scene-primitives.css`) CÓ đổi byte 17→18 — đó chính là lý do SCRIBA_VERSION bump; hợp đồng cache là
   `(source, SCRIBA_VERSION)`, không consumer nào dựa vào byte-identity xuyên-version."*
2. Đính chính chỗ nào nói "`.scriba-group` CSS" → `\group` không có CSS (inline attr).
3. (Tùy chọn, ghi làm micro-opt tương lai, KHÔNG làm bây giờ) Nếu về sau có consumer cần diff CSS per-version:
   tách `.scriba-link > path` thành file gated theo cùng khuôn `_PRIMITIVE_CSS`, key theo overlay-verb hiện diện.
   Chấp nhận: bản thân việc tách kèm 1 SCRIBA_VERSION bump.

---
*Bằng chứng cốt lõi: `_script_builder.py:72,102-114` · `renderer.py:66-69,727-736` · `scriba.js:25,217-230,462` ·
`scriba-scene-primitives.css:103,610-622` · `docs/spec/svg-emitter.md:787-789` · `docs/spec/environments.md:34` ·
`pipeline.py:330` · `_version.py:158-186`.*
