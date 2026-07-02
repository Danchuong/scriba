# Case: pill-placement-space — pill đè nội dung trong khi không gian ngang bỏ trống

**Mở:** 2026-07-02 · symptom-driven (screenshot user: grid 5×5 frame 5, pill arc 3 dòng đè cells 2/3/8/9, hai dải trống trái/phải grid không dùng) · 3 research agents · Status: **DIAGNOSED — chờ duyệt phương án**

## Hand-off Brief

Pill của arc annotation đứng nguyên tại natural anchor (đỉnh bow của arc — rơi vào TÂM grid với arrow chéo) và che 4 cells, vì (1) cells không phải obstacle → mọi term điểm mù với việc che nội dung, (2) vùng tìm kiếm ±2.5×pill_h không với tới mép grid, (3) wrap char-mode 24 ký tự tạo pill "tháp" 3 dòng, (4) auto side-hint không bao giờ đề xuất trái/dưới. Nền móng để fix đã sẵn: leader vô hạn độ dài + h_pads exact (pill ra ngoài mép được reserve tự động) + `side=` documented.

## Confirmed — toán học của đúng frame trong screenshot

- Grid 5×5: CELL 60×40, GAP 2 → footprint 308×208. src `cell[0][3]`=(216,20), dst `cell[3][1]`=(92,146); dx=−124, dy=126, dist≈176.8.
- 2D arc: `arc=0.05+(1−176.8/1000)·0.20=0.2146`; `offset=max(0.2146·176.8, 20)=37.95`; perp=(−0.713,−0.701) — trỏ **up-left vào tâm grid**; q=(127,56); `label_ref=(121,50)` (`_svg_helpers.py:2143-2165`).
- Pill 3 dòng (char-mode 24 chars, `_LABEL_MAX_WIDTH_CHARS`, label 40 codepoints) = **148×45** → centred (121,50) phủ x[55,187]×y[27,73] = đúng cells 2/3/8/9. (`pill_dimensions` char mode: arc `:2273`, plain `:1913`.)
- Obstacle tuple cho pill này = **rỗng tuyệt đối**: Grid `resolve_obstacle_segments`=[] stub (`grid.py:331`); `resolve_obstacle_boxes` **dead code 0 call sites** (`grid.py:327`, `_protocol.py:97`); scene_segments không truyền (`grid.py:301`); cell-AABB blocker chỉ tồn tại ở nhánh `position=below` (`base.py:896-912`). → P1/P5 mù; chỉ P2 (displacement 2.0/px) hoạt động → natural thắng mọi nudge.
- Vùng tìm: 49 candidates (natural + 8 hướng × 6 bước, max 2.5×pill_h=112.5px — comment "32 nudges" STALE) < half-grid 155px → **dải trống ngoài mép nằm ngoài không gian tìm kiếm** (`_nudge_candidates:937`).
- Auto side-hint (R-22, `:2293-2308`) chỉ có thể ra `above`/`right`/None — **không bao giờ `left`/`below`** → arrow xuống-trái bị bias ngược dải trống trái.
- Score terms đầy đủ (P1..P7, `_score_candidate:727-793`): duy nhất P7 (edge_occlusion 40.0) là "content occlusion" nhưng chỉ cho SEGMENTS; **không tồn tại term phạt che cell** — spec smart-label không có rule tương ứng (lỗ spec).

## Nền móng sẵn có (không cần xây lại)

- Leader: không cap độ dài, origin = curve-mid B(0.5) thật, endpoint = perimeter pill (`:2410-2446`, R-27c) — "pill xa + leader trỏ về" nửa render đã tổng quát.
- `annotation_h_pads` exact: pill bước ra ngoài mép → bbox nở đúng số px painted, honesty test 4 phía giữ nguyên hiệu lực. Margin scene (căn giữa frame) KHÔNG mượn được — kênh chính danh là h_pads (phân tích coupling: đo trong content-frame, không vòng lặp).
- `side=` đã documented (REFERENCE:407) — user override được half-plane nhưng reach hiện tại vô hiệu hóa nó ở case này.
- `cell_metrics` mang đủ grid extent (origin, cols, cell_width) nhưng Grid **không truyền** (`grid.py:301`) và các field đó unused (TODO `:410-415`).

## Phương án (xếp hạng, structural)

1. **W1 — cells thành SHOULD-obstacles (cốt lõi):** hook opt-in `resolve_self_content_rects()` default `[]` trên PrimitiveBase; Grid/Array/DPTable/Matrix override trả cell AABBs; merge vào obstacle set cho CẢ arc lẫn position pills (`base.py:831` vùng); kind mới `content_cell` weight nhẹ (P1+P5 bắt đầu nhìn thấy cells). Chi phí 5×5: ~2.4k float ops/pill — không đáng kể; scale tuyến tính. KHÔNG đụng scorer. (Loại trừ: revive `resolve_obstacle_boxes` protocol-wide = rộng hơn cần; synthesize trong scorer = đụng hot path; MUST-blocker mở rộng = chỉ chặn src/dst, không fix 4 cells bị che.)
2. **W2 — adaptive wrap cho arc/plain:** truyền `wrap_px` tại 2 call sites (seam `pill_dimensions` có sẵn) = f(grid extent từ cell_metrics, fallback cap) → label này thành 1–2 dòng rộng thay vì tháp 3 dòng. Grid phải bắt đầu truyền cell_metrics (sửa luôn thiếu sót stagger-flip).
3. **W3 — side-hint đủ 4 hướng:** R-22 suy `left`/`below` từ vector thay vì chỉ above/right (đổi spec R-22 + contract tests).
4. **W4 — edge candidates (chỉ nếu W1–W3 chưa đủ):** thêm ~8 candidates chủ đích tại mép grid ± pill_w/2 (tính từ cell_metrics) thay vì tăng mù bán kính — deterministic, bounded.
5. Spec: thêm rule content-occlusion mới vào smart-label-ruleset (đóng lỗ spec) + sửa comment "32 nudges" stale.

**Dự đoán case user sau W1+W2:** pill 1–2 dòng, bị content-obstacles đẩy khỏi cells trong reach hiện có → đậu lane trên grid (trống, đã reserve exact) hoặc mép phải-trên; hết che nội dung mà không cần W4.
