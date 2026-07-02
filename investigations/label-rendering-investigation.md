# Case: label-rendering — cụm bug render label trong scriba

## Hand-off Brief (rough — sẽ viết lại ở Outcome 5)

Sáu triệu chứng label sai/mất khi render doc tiếng Việt (Number Spiral editorial). Evidence Confirmed từ artifacts render phiên 2026-07-02. Đang truy root cause trong `scriba/animation/{labels,primitives,emitter}`.

## Case Info

- **Ngày mở:** 2026-07-02
- **Người mở:** Chuong (qua Claude)
- **Chế độ:** symptom-driven, multi-symptom cluster
- **Pause protocol:** user mandate "fix triệt để, nghiên cứu sâu" → chạy liền các Outcome, không dừng giữa chừng.

## Problem Statement (hypothesis của user — cần verify độc lập)

1. Grid `label=` trong **animation**: SVG text 1 dòng, neo đáy-phải, clip mất chữ ("Xoắn ốc số (hàng y xuố"), đè hàng cuối grid. Cùng label ở **diagram** wrap 3 tspan đúng.
2. Label chứa `$math$` đi path `foreignObject` 1 dòng cố định (673×20, `overflow:hidden`): label dài xén dọc (scrollH 34 > clientH 20), vỡ layout.
3. `display:flex` trong foreignObject nuốt space quanh inline math ("thử mathm²và").
4. `VariableWatch` `label="f = nền + d"` drop hoàn toàn khỏi HTML (0 match).
5. Animation env `label="Number Spiral: …"` drop; widget hardcode `aria-label="Animation"`.
6. tspan wrap strip space → copy-paste dính chữ ("sangphải", "tớim^2").

## Evidence Inventory

| # | Evidence | Grade | Nguồn |
|---|----------|-------|-------|
| E1 | `<text class="scriba-primitive-label" …><tspan>…cột x sang</tspan><tspan>phải.…</tspan>` — không space cuối dòng | Confirmed | number_spiral.html (plain-label build) |
| E2 | `<foreignObject x="0" y="203" width="673" height="20"><div style="display:flex;…overflow:hidden;text-overflow:ellipsis">` quanh caption có KaTeX | Confirmed | number_spiral.html (math-label build) |
| E3 | caption math-label: scrollWidth 673 = clientWidth, scrollHeight 34 > clientHeight 20 → xén dọc | Confirmed | đo headless Chromium |
| E4 | `grep -c 'f = nền + d'` = 0 trong HTML | Confirmed | number_spiral.html |
| E5 | `aria-label="Animation"` trên `role="region"` widget; label env 0 match | Confirmed | number_spiral.html |
| E6 | Animation grid label render 1 dòng, bbox w=312 tại x=640, hiển thị cắt tại biên SVG; diagram label wrap 3 tspan | Confirmed | screenshots anim_frame1.png + bbox eval |
| E7 | Diagram svg `aria-labelledby="spiral-overview-frame-1-narration"` — id không tồn tại | Confirmed | number_spiral.html |
| E8 | Label ngắn + math render KaTeX đúng nhưng mất space quanh math | Confirmed | short_label.png |

## Hypotheses

| # | Hypothesis | Status | Resolution |
|---|-----------|--------|------------|
| H1 | Animation vs diagram đi 2 code path label khác nhau (frame_renderer vs static?) | Open | |
| H2 | Math-label đi path foreignObject 1 dòng không wrap (thiết kế cho label ngắn) | Open | |
| H3 | `display:flex` gây collapse whitespace text-node | Open | |
| H4 | VariableWatch không implement render label | **Refuted** | Label RENDER ĐẦY ĐỦ: variablewatch.py:98 lưu, :394-403 emit qua `_emit_caption` (agent sweep, verified). Quan sát "0 match" ban đầu (E4) là **false negative của công cụ đo**: `grep 'f = nền + d'` chạy qua RTK/Rust-regex — `+` là quantifier, không literal. Grep lại không dùng `+`: chuỗi có trong HTML. Không thấy trên màn hình vì caption bị CLIP đáy widget animation (cùng class clip với grid label + hàng `val`) — chuyển triệu chứng sang class "animation clip". |
| H5 | Emitter hardcode aria-label, không đọc env label | Confirmed (sửa: không phải hardcode — là fallback else-branch; drop tại renderer.py:503-509 không forward) | Refutation pass: grep toàn codebase 0 consumer của `ir.options.label`; plumbing emit_html/emit_interactive_html đã sẵn nhưng không được gọi với label |
| H6 | Text-wrap engine split theo space rồi join không giữ space | Open | |

## Investigation Backlog

- [ ] Map code path: ai emit `scriba-primitive-label` (tspan path vs foreignObject path), điều kiện branch
- [ ] Vì sao animation Grid label 1 dòng không wrap còn diagram wrap
- [ ] VariableWatch label: có đọc param không, emit ở đâu
- [ ] Env label → emitter/aria; tìm chuỗi hardcode "Animation"
- [ ] tspan wrap: chỗ split/join space
- [ ] Kiểm tra test coverage hiện có quanh label

## Timeline

- 2026-07-02: render number_spiral.tex → 6 triệu chứng; thí nghiệm math-label ngắn/dài; mở case.

## Source Code Trace

### Symptom 5 — env label drop (H5: CONFIRMED, sửa lại chi tiết)

- Parser CAPTURE OK: `scriba/animation/parser/grammar.py:545` (`label=opts.get("label")`) → `AnimationOptions.label` (`scriba/animation/parser/ast.py:298`). KHÔNG chết ở parser.
- **Drop point: `scriba/animation/renderer.py:503-509`** — `render_block` chỉ đọc `ir.options.id`, không bao giờ forward `ir.options.label` vào `emit_html(...)`.
- Plumbing hạ nguồn ĐÃ TỒN TẠI nhưng chưa nối dây: `emit_html(label="" …)` (`_html_stitcher.py:686`) → forward `emit_interactive_html(label=…)` (`:730`, param `:410`) → dùng tại `:647` `_aria_label = _escape(label) if label else "Animation"` → tag `:656`.
- `grep ir.options.label` toàn codebase = 0 consumer. Docs intent: env label = aria-label cho figure (`docs/spec/environments.md:120`, REFERENCE `:1177,:1466`).
- Static filmstrip `emit_animation_html` + `emit_diagram_html` không có param label (cần thêm nếu muốn triệt để).
- Phân biệt 2 loại label: FRAME label (`\step[label=]` → FrameData.label, hoạt động, có test) vs ENV label (bug này).

### Symptom 7 (ARIA) — dangling aria-labelledby ở diagram (CONFIRMED)

- `scriba/animation/_frame_renderer.py:454` build `narration_id = … f"{frame_id}-narration"`, `:512` emit `aria-labelledby` **vô điều kiện**.
- Animation có `<p class="scriba-narration" id="…-narration">` nên hợp lệ; diagram (`emit_diagram_html` `_html_stitcher.py:745-781`) KHÔNG emit narration → dangling.
- Spec `docs/spec/environments.md:542-554` (§8.2): diagram svg `role="img"` **không có** aria-labelledby → fix = suppress/override cho diagram path.
- Diagram wrapper không có `id=` (chỉ `data-scriba-scene`, `_html_stitcher.py:774-781`) — **khớp spec §8.1/§8.2**, không phải bug; widget animation có id là do code path riêng (`:656`).

### Test coverage gap (ARIA)

- `tests/unit/test_filmstrip_aria.py`: chỉ cover FRAME-label trên static filmstrip. KHÔNG cover: env label → widget aria-label; emit_interactive_html label param; diagram dangling aria-labelledby.

### Baseline test suite (2026-07-02)

- `pytest -x`: 3474 passed; 1 fail `test_recursive_dos.py::test_graph_with_100_self_loops_completes` — flaky timing (pass khi chạy riêng, 2.17s); không liên quan.

## Follow-up: 2026-07-02 #2 — sweep bug class tương tự (3 agents)

### Agent D (parsed-but-unconsumed) — kết quả

- **Premise correction:** VariableWatch label KHÔNG dead (xem H4 — false negative do grep `+` metachar qua RTK). 13/13 primitives nhận `label` đều render (matrix đầy đủ trong agent log); MetricPlot/Plane2D không nhận `label` (E1114 — không phải dead).
- **Dead surface THẬT lớn hơn dự đoán — 5 env option keys chết:**
  - `label` — parsed (grammar.py:545 → ast.py:298), 0 reads; renderer.py:503-509 không forward vào emit_html (param sẵn ở _html_stitcher.py:686). Docs REFERENCE:1177 hứa "aria label" → documented-but-broken. **HIGH**.
  - `width` — parsed kỹ (có unit-suffix handling grammar.py:501-513!) → 0 reads; stage auto-size từ bbox (_frame_renderer.py:119-160). **MEDIUM**.
  - `height` — như width. **MEDIUM**.
  - `layout` — parsed (filmstrip|stack) → 0 reads; `data-layout="filmstrip"` hardcode (_html_stitcher.py:196,303). **MEDIUM**.
  - `grid` — trong VALID_OPTION_KEYS (constants.py:46) nhưng KHÔNG là field của AnimationOptions → accept rồi vứt im lặng tại grammar.py:533. **LOW/vestigial**.
  - Chỉ `id` sống (renderer.py:474-475, 794-795).
- Command params (\annotate ephemeral/position/color/arrow_from, \recolor, \step label): **tất cả live** (consumers cited).
- Fix direction: (a) forward `ir.options.label` (1 dòng + plumb static/diagram); (b) wire hoặc reject width/height/layout; (c) bỏ `grid` khỏi VALID_OPTION_KEYS.

### Agent A (math-never-wraps / flex / fixed-FO sweep) — kết quả

- **🔴 REGRESSION từ fix caption (ĐÃ SỬA cùng ngày):** Array không dùng `base._emit_caption` — bespoke caption (array.py:316-355 + bbox :404-407). `_caption_lines` wrap math ⇒ nhánh multi-line bespoke `_escape_xml` ⇒ raw `$...$` hiện chữ. Fix: migrate sang `_emit_caption`/`_caption_block_height` (commit "fix(array): route caption through shared Layer-A helper"); plain byte-stable (bespoke vốn là copy nguyên văn của base); goldens regen 22 files; suite 4050 xanh.
- **Pill "math never wraps" (3 render sites + 4 measurement mirrors):** `_svg_helpers.py:3201` (position pill), `:2155` (arc-arrow pill), `:1780` (plain-pointer pill) — math exempt khỏi cap wrap 132px, pill tự-size ⇒ pill math dài TRÀN NGANG qua cells/viewBox (leader-line + clamp giảm nhẹ, không triệt). Mirrors :2873/:2632/:2842+siblings/array.py:552 tự nhất quán (không clip, chỉ latent). Severity med. Liên đới trực tiếp triệu chứng "annotate label đè cells".
- **Fixed-FO cell/nhãn boxes (23 sites):** cell values clip/ellipsis chủ đích (low, chấp nhận). Đáng chú ý: graph.py:1619 + tree.py:741 — node math bị CLIP trong hộp 2r×2r trong khi node plain được overflow tự do (inconsistent, med); hashmap.py:362 entries dài (med); numberline.py:301 tick 40px (med); metricplot :561/:569/:579/:750 + plane2d :1014/:1109 + codepanel :400 — không truyền fo_width/height ⇒ default 80×30 clip (med).
- **Missing font_size ở FO path (14 sites):** subset HẠI THẬT (CSS `> text` set size cho plain nhưng không với FO div ⇒ math ~16px cạnh text 14/11/10px): array:282, dptable:397/:464, grid:278, graph:1611, tree:733, numberline:296. Còn lại thấp.
- **Flex khác:** duy nhất `_svg_helpers.py:1397` (pill FO) — an toàn hiện tại (inner = 1 span katex atomic, không có inter-item whitespace), sẽ vỡ nếu đổi sang mixed-node.

### Agent B (CSS direct-child / anchor / clip class) — kết quả

- **Cơ chế bug "Grid label animation lệch+clip" GIẢI XONG (High confidence):** diagram và animation cùng `_emit_frame_svg`; khác biệt duy nhất: `set_min_arrow_above(max_ah)` chỉ được gọi ở animation/interactive (`_html_stitcher.py:216-236, :456-480`), không bao giờ ở `emit_diagram_html`. Reservation đó làm `arrow_above>0` mọi frame ⇒ grid mở inner `<g transform>` (grid.py:243-244) ⇒ caption tụt 2 cấp dưới `[data-primitive]` ⇒ CSS `[data-primitive] > .scriba-primitive-label` (css:467) trượt ⇒ `text-anchor` về `start` mặc định SVG ⇒ caption single-line vẽ từ center_x sang phải (bbox x≈640 vs center≈505) tràn/clip. Không rule text-anchor fallback nào khác tồn tại (verified toàn static/*.css).
- **Nhánh single-line plain của `_emit_caption` (base.py:566) là nhánh DUY NHẤT không inline anchor** (math path + multi-line path đã inline). Cùng bệnh: array.py:328 (đã chết theo migration Array — giờ mọi caption qua base).
- **9 primitives cùng triệu chứng** (grid, array, dptable, matrix, stack, queue, numberline, hashmap*, variablewatch*, linkedlist* — *chỉ frame có arrow sống). **Miễn nhiễm:** tree/graph (transform nằm TRÊN chính element `[data-primitive]`, caption vẫn direct child), codepanel (inline `text_anchor="start"` chủ đích).
- **Selector fragile khác:** css:453 numberline `> [data-target]`, css:379 cell text (an toàn nhờ descendant hop), css:486 annotation.
- **Fix direction (2 nhát, độc lập, nên làm cả 2):** (1) inline `text_anchor="middle"` + `dominant_baseline="central"` tại base.py:566; (2) CSS child → descendant `[data-primitive] .scriba-primitive-label` (template sẵn: index-label css:401).
- Ghi chú: watch label "f = nền + d" + hàng `val` bị cắt đáy widget = cùng chuỗi hệ quả nesting/clip trong animation (xem H4).

### Follow-up #3 — "dư space phía trên" trong animation (user report, đo thực nghiệm)

- **User đúng: lane trống KHÔNG được frame nào dùng.** Đo headless mọi frame (viewBox 342×518): cells top y=127; annotation cao nhất f3=229, f4=188, f5=146 — tất cả DƯỚI mép cells. Vùng reserve 114px (grid `translate(0,114)`, diagram chỉ 58) = 0% sử dụng.
- **Nguồn con số 114:** `arrow_height_above` (`_svg_helpers.py:2637-2776`) là **safe upper bound cố ý** ("must be monotone non-decreasing"): arc-peak uncapped (mirror perfect-arrows `_arc*euclid`) + `headroom_extra` 24 (plain) + `nudge_margin ≈ 1 pill_h` (~48 với pill 3 dòng frame 5). `_html_stitcher` lấy max qua mọi frame → `set_min_arrow_above` → áp cho cả 5 frame.
- **Vì sao thực tế 0 dùng:** placement engine (nudge/_pick_best) đặt pill GIỮA grid (đè cells — chính symptom #1) và arc 2d của arrow 10→15 không vượt lên trên hàng 0. **Reservation và placement là 2 hệ độc lập không đối soát** → dự phòng chết + pill vẫn đè nội dung: một sự bất đồng bộ, hai triệu chứng.
- Fix direction: reservation đọc bbox placement THẬT (sau nudge) per frame, hoặc post-trim lane theo bbox thực; max-over-frames giữ để chống layout shift nhưng trừ phần không dùng.

### Follow-up #4 — thiết kế exact reservation (agents R + P; chờ C)

**Baseline định lượng (đo browser, corpus):** number_spiral grid: reserve 114 / dùng 0; test_dptable_arrows: 96/59 (thừa 37); test_label_overlap_1d: 116/88 (thừa 28); kmp: 70/**74** (**THIẾU 4px** — âm!). Heuristic fail 2 chiều. Baseline: `overreserve_baseline.json` (scratchpad).

**Agent P (geometry/seam) — facts:**
- Arc = quad→cubic bezier; control points closed-form, pure (`_compute_control_points` :1976, ArrowGeometry :1949). Extrema closed-form khả thi (quadratic roots); sampler `_bezier_point` :1565 có sẵn.
- Pill final rect chính xác tại `_svg_helpers.py:2289-2290` (arc pill) / `:3214-3324` (position pill); sub-steps pure, orchestrators side-effect (extract được).
- **Placement KHÔNG phụ thuộc reservation** (zero reads arrow_above trong placement; clamp dùng sentinel 8192, không viewBox thật) → exact reservation không gây feedback loop primitive-level. Caveat: collision-nudge phụ thuộc scene_segments (build sau offsets) → chỉ natural extent là scene-independent.
- Determinism sạch (RNG chỉ trong SA-refine chưa wired; sort có tie-break).
- Seams: (a-lite) thay ruột `arrow_height_above` bằng công thức THẬT (capped stagger, real base_offset, natural pill top `label_ref_y − pill_h/2`); (a-full) extract pure `_resolve_label_rect` dùng chung emit+measure; (b) emit-returns-bbox: FATAL ordering flaw (bbox cần trước emit); (c) two-pass: wasteful.

**Agent R (pipeline map) — facts:**
- `arrow_height_above` = seam tiêu thụ duy nhất: stitcher scan ×2 (`_html_stitcher.py:214-238`, `:454-480`, chỉ scan arrow_height_above, cell_h=getattr('_cell_height',46)) + bounding_box/emit_svg 14 primitives (pattern `max(computed, pos_above, _min_arrow_above)`).
- 2 amplifiers: cross-frame max (`set_min_arrow_above`) + `_build_reserved_offsets` component-wise max bbox height (`:76-85`) → tallest frame inflate mọi frame + `compute_stable_viewbox` (:166-233) bake vào viewBox uniform.
- **6/14 primitives không đọc `_min_arrow_above`** (tree, plane2d, linkedlist, graph, variablewatch, hashmap — setter là no-op).
- Tests: KHÔNG pin exact 114/58. Pins: deltas (+24 label/+32 math/+8 below-math), R32-1 invariant `h_bare==h_annotated` sau set_min (GIỮ ĐƯỢC nếu giữ floor mechanism), 2 formula-replication asserts cho `position_label_height_above` (`test_smart_label_phase0.py:815-822,838-844` — sẽ update), horizontal ratchet `test_pill_within_bbox.py`.
- cell_height nguồn không nhất quán (stitcher 46 default vs primitives đủ kiểu) — reconcile khi sửa.
- Horizontal siblings (`position_label_h_extents`/`_h_label_pad`/array `_bbox_width`) ít lệch hơn (dùng real anchors + real pill width) nhưng cùng family — exact hóa cùng đợt để nhất quán.

### Follow-up #4 (tiếp) — Agent C (contracts/history) + DESIGN chốt

**Agent C facts:** (1) Origin upper-bound = commit 8ec08ca v0.20.0: arc capped cũ under-reserve → pill đè primitive trên khi siết gap 50→20/pad 16→12 — exact PHẢI ≥ painted peak mọi input. (2) Docs NORMATIVE: `docs/spec/ruleset.md` §8.9 (R-32) quy định max-over-frames uniform là SPEC → exact chỉ đổi CON SỐ, giữ semantics. (3) Test blast: chỉ 2 golden suites vỡ (regen); R-32 suite là relative — survive. (4) **2 guard gaps:** không test nào assert painted ≤ reserved (dọc) — chính là lỗ kmp −4px; không test non-overlap pixel giữa primitives. (5) Substory không set_min_arrow_above (gap). (6) Land phải: bump SCRIBA_VERSION 9→10, regen goldens, update docs; svg-emitter.md có stale padding=16 (code 12). (7) Không cache nào tồn tại — solver chạy pre-pass sẽ x2 nếu không memo.

### DESIGN — "Exact Painted-Extent Reservation" (đề xuất, chờ user duyệt)

Nguyên tắc: **một nguồn sự thật hình học** — extent tính từ CHÍNH các hàm geometry mà emit dùng (không công thức song song, không hằng đoán).

- **Phase 0 — guard tests trước (RED có sẵn):** property test painted ≤ reserved (parse arc extrema + pill rects + arrowhead + halo từ SVG emit, so với arrow_above) trên corpus + hypothesis — hiện FAIL thật với ca kmp −4px; test non-overlap 2 primitives stacked.
- **Phase 1 — pure measurer + swap ruột:** extract `_resolve_arc_pill_rect` pure từ `_emit_label_and_pill` (emit gọi lại chính nó — không drift); thêm `_cubic_y_extrema` closed-form trên ArrowGeometry THẬT (capped stagger); `annotation_painted_extent(...)` → 4 phía (thay cả family `position_label_height_*`/`h_extents` cùng nguồn); `arrow_height_above` giữ signature, ruột = `ceil(−extent.top)`; reconcile cell_height (stitcher getattr('_cell_height',46) → `_arrow_cell_height` thật); wire substory set_min.
- **Phase 2 — invariant by construction:** placement nhận reserved_top làm HARD BOUND — nudge candidates vượt lên trên reserve bị loại (đi ngang/xuống/leader thay thế) → painted ≤ reserved thành bất biến cấu trúc, hết vĩnh viễn chiều "thiếu" mà không đoán 2.5×pill_h.
- **Phase 3 — land:** SCRIBA_VERSION 10; regen 2 golden suites; docs §8.9/§13.8 giữ semantics (sửa câu mô tả estimator), fix stale padding note; update 2 formula-replication asserts + QW-7 delta nếu exact cho số khác hằng cũ; memo extent per (prim, frame) trong pre-pass; đo perf build corpus trước/sau.
- **Nghiệm thu:** re-run `measure_overreserve.py`: waste ≈ 0 (±3px stroke pad), zero ca âm; number_spiral 114→~0; suite + R-32 xanh.
- **Quan hệ:** độc lập với structural-lift plan (Layer A caption — Array migration 2026-07-02 là một mảnh của nó); constraint "DO NOT change formulas" của plan đó thuộc đợt lift additive, không ràng effort này.

### Follow-up #4 — LANDED (Phase 0 + 1): Exact Painted-Extent Reservation

**Kiến trúc chốt (khác design ban đầu một bậc tốt hơn):** thay vì mirror công thức (drift risk vĩnh viễn), reservation **đo chính output của emit**: `PrimitiveBase.annotation_height_above()` chạy `_measure_emit()` (mặc định = `emit_annotation_arrows` với `_annotation_cell_metrics()` hook) vào scratch buffer rồi đo bằng `_extent.py::measure_painted_extent` — closed-form cubic Bézier extrema (nghiệm quadratic của B'(t)=0), stroke folded. Reserved ≡ painted by construction.

- Phase 0: `tests/helpers/painted_extent.py` (parser ĐỘC LẬP, sampling dày — double-blind với production) + `tests/unit/test_painted_within_bbox.py` (honesty 4 phía; RED tái tạo kmp self-loop **6.2px trên bbox**) .
- Phase 1: `_extent.py` mới; base method + cache (invalidate tại `set_annotations` — mutation point duy nhất); 14 primitives swap `max(exact, _min_arrow_above)` (bỏ pos_above term — extent phủ position pills); 6 non-readers (tree/graph/plane2d/linkedlist/variablewatch/hashmap) giờ TÔN TRỌNG floor (hết jitter); stitcher scan ×2 → `_apply_min_arrow_above` helper (fix luôn cell_h getattr('_cell_height',46) sai nguồn); substory wired lần đầu; Queue custom path extract `_emit_queue_annotations` + override `_measure_emit`; cell_metrics hooks (array/dptable/graph/tree/queue) — spy tests bắt được 2 lệch nguồn tiềm ẩn này trước khi thành bug.
- Tightness: `tests/unit/test_annotation_extent_exact.py` — reserved == painted ±1.5px, so bằng parser độc lập.
- **Nghiệm thu:** browser Chromium trên goldens mới: dptable_arrows 96→**59=painted**, label_overlap_1d 116→**88=painted**, kmp 70→**74** (hết âm 4px), number_spiral grid 114→**0** — **waste = 0.0 mọi case**. Ảnh đối chứng overlap_old/new.png: nội dung pixel-identical, chỉ cắt phần trắng chết. Suite **4071 pass**; R-32 conformance nguyên vẹn (semantics max-over-frames GIỮ — chỉ con số exact); goldens regen 49 files; SCRIBA_VERSION 9→10; REFERENCE §13.8 cập nhật.
- **Còn lại (phase kế):** Phase 2 hard-bound nudge (chặn candidate vượt lane — chiều "thiếu" từ cross-primitive scene_segments, hiếm, đang được honesty test canh); exact hóa chiều NGANG (`_h_label_pad` family — hiện lệch 0.2px stroke bleed, `_EPS_X=0.5` đánh dấu trong test); dọn `arrow_height_above` legacy (giờ chỉ tests dùng).

## Follow-up: 2026-07-02 — scope thu hẹp theo user

User chốt scope: **chỉ fix render `$math$` trong label** (symptom 2+3). Symptom 1, 4, 5, 6, 7 → backlog (findings giữ nguyên làm tài liệu). Hai agent điều tra symptom 4/5 bị user stop — phần env-label/ARIA đã ghi ở Source Code Trace phía trên.

### Root cause (Confirmed) — math trong shape label

1. `scriba/animation/primitives/base.py:476-477` (trước fix) — `_caption_lines`: `if _label_has_math(s): return [s]` — math caption không bao giờ wrap → 1 dòng dài.
2. `base.py:520-533` (trước fix) — nhánh single-line gọi `_render_svg_text(..., fo_width=footprint_width, fo_height=20)` không `font_size` → hộp cố định footprint×20, chữ KaTeX cỡ kế thừa (to hơn 11px caption).
3. `scriba/animation/primitives/_text_render.py:289-300` (trước fix) — FO div `display:flex;align-items:center;justify-content:…;line-height:1;overflow:hidden` → (a) flex biến mỗi text-node/span thành flex item, **nuốt whitespace** giữa chúng; (b) label dài wrap bên trong flex item → content 34px trong hộp 20px → **xén dọc**; (c) `css_class` bị bỏ qua ở FO path (fast path `<text>` thì có).
4. Phát hiện kéo theo khi fix: `<text>` fast path không inline `text-anchor` — CSS `[data-primitive] > .scriba-primitive-label` không phủ mọi context nhúng → dòng plain lệch phải từ center_x (họ hàng với symptom 1 animation — root cause chung "phụ thuộc CSS direct-child").

### Fix (đã land)

- `_text_render.py` `_render_svg_text` FO path: bỏ flex → inline flow + `white-space:nowrap` + `line-height:{h}px` (center dọc, giữ space); `class` đặt lên `<foreignObject>` (khớp selector + tooling).
- `base.py`: `_caption_lines` wrap luôn cả math (`_wrap_label_lines` vốn `$…$`-safe, đo qua `_label_width_text` strip-$ + 1.15x); `_caption_block_width` đo math qua `_label_width_text`; `_caption_block_height` dùng `_MATH_CAPTION_LINE_H=18`/dòng cho block math (KaTeX strut ~15px @11px); `_emit_caption` nhánh mới: math + callback → mỗi dòng 1 `_render_svg_text` box (`text_anchor="middle"`, `dominant_baseline="central"`, `font_size=11`); không callback → fallback tspan wrap như plain.
- Plain label: byte-stable (mọi thay đổi gate sau `_has_math`/`_label_has_math`).

### Verification

- TDD: `tests/unit/test_caption_math_wrap.py` — 18 tests (RED→GREEN).
- Headless Chromium đo: FO scrollH=clientH=18 (hết xén), display:block (hết flex), 3 dòng center-y 217/235/253 (stack đúng 18px), KaTeX render, space quanh math nguyên. Screenshot `diagram_fixed2.png`.
- Impact: CRITICAL hub (`_render_svg_text` 19 callers, `_caption_lines` 25 flows) — guard bằng full suite + fixtures (đang chạy).

## Conclusion

**Confidence: High** (root cause Confirmed từng dòng, repro deterministic, fix verified bằng test + đo browser). Scope đã fix: math-in-label. Backlog còn: symptom 1 (animation label lệch/clip — nghi cùng họ "CSS direct-child không áp trong animation context", có manh mối mới từ mục 4), symptom 4 (VariableWatch label drop), symptom 5 (env label → renderer.py:503-509, fix 1 dòng + plumbing), symptom 6 (tspan strip space khi copy), symptom 7 (dangling aria-labelledby — `_frame_renderer.py:512` thiếu guard).
