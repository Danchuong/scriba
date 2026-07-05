# Case File: Dark-mode edge/border contrast dưới ngưỡng WCAG

## Hand-off Brief (đọc 15 giây)

Ở dark-mode, viền/cạnh idle của Tree, Forest, Deque (cả ô đầy lẫn slot dự trữ gạch nối) và Array đều lấy màu từ token CSS `--scriba-state-idle-stroke` = `#313538` (rgb 49,53,56), cho contrast **1.45:1** trên nền `#151718` — dưới ngưỡng WCAG 1.4.11 non-text 3:1, gần như vô hình. Hypercube trông "sáng" (13.93:1) **không phải** vì thiết kế khác, mà vì nó vẽ cạnh bằng thuộc tính inline `stroke="#dfe3e6"` (lấy `THEME["border"]`) trên một `<line>` không có class trạng thái → không có rule CSS nào override → nó **không đổi theo theme**, kẹt ở màu light và tình cờ nổi bật trên nền tối. Cạnh mờ là lựa chọn thiết kế toàn cục (cả light lẫn dark đều 1.2–1.45:1), nên đây là vấn đề a11y hệ thống + một bug theming riêng ở Hypercube, không phải "W4 không đồng nhất".

## Case Info

- **Commit:** 18443bb (main), 2026-07-05
- **Scope:** `scriba/animation/static/scriba-scene-primitives.css`, `scriba/animation/primitives/_types.py`, các primitive edge-emitter (forest/tree/array/queue/hypercube).
- **Phương pháp:** đọc CSS/emit + render 1 doc 5 primitive qua `render.py`, đo `getComputedStyle` thật bằng chrome-headless-shell (Playwright), tính CR bằng công thức WCAG relative-luminance (cùng công thức tái tạo đúng số 1.45 và 13.93 của browser).
- **Artifacts:** `scratchpad/bmad-dm/edge_audit.tex|html`, `measure.py`, `dark_full.png`, `light_full.png`.
- **Status:** Concluded. **KHÔNG sửa source** (temp render đã xoá, `git status` sạch).

## Vấn đề

Hunt-visual báo: stroke cạnh dark `rgb(49,53,56)` trên nền `rgb(21,23,24)` = CR 1.45 (<3:1). Nghịch lý: Hypercube dùng cạnh sáng `rgb(223,227,230)` = CR 13.93. Cần: token thủ phạm, đo lại CR, blast radius, đề xuất thống nhất, có nên làm trong 0.24.0.

## Bằng chứng đã xác nhận (Confirmed)

**Token màu (định nghĩa):**
- `THEME["border"] = "#dfe3e6"` (light) — `scriba/animation/primitives/_types.py:107`
- `DARK_THEME["border"] = "#313538"` (dark) — `_types.py:118`
- `STATE_COLORS["idle"]["stroke"] = "#dfe3e6"` — `_types.py:81` (giá trị inline giống `THEME["border"]`)
- CSS light `:root`: `--scriba-border: #dfe3e6` (`scriba-scene-primitives.css:43`), `--scriba-state-idle-stroke: #dfe3e6` (`:123`)
- CSS dark: `--scriba-bg: #151718`, `--scriba-border: #313538`, `--scriba-state-idle-stroke: #313538` trong khối `[data-theme="dark"]` (`:715,:717,:724`) VÀ khối `@media (prefers-color-scheme: dark)` (`:784,:786,:790`)
- Nền ô dark: `--scriba-state-idle-fill: #1a1d1e` (`:723`)

**Cơ chế emit + override (vì sao 4 primitive tối mà Hypercube sáng):**
- Cả hai đều emit **cùng** màu inline `#dfe3e6`: Forest qua `svg_style_attrs("idle")["stroke"]` (`forest.py:538,548`); Hypercube qua `THEME["border"]` (`hypercube.py:352,358-362`).
- Khác biệt là CSS cascade (rule CSS luôn thắng presentation-attribute inline):
  - Forest bọc `<line>` trong `<g class="scriba-state-idle">` → khớp rule `.scriba-state-idle > line { stroke: var(--scriba-state-idle-stroke) }` (`scriba-scene-primitives.css:204-207`) → đổi theo theme → dark = `#313538`.
  - Tree `<line>` nằm trong `class="scriba-state-idle"` **và** trong `.scriba-tree-edges` → khớp cả rule trên lẫn `:where([data-primitive="tree"] .scriba-tree-edges > [data-target]) > line` (`:458-463`) → dark `#313538` (`tree.py:915-921`).
  - Array/Deque: ô là `<rect>` trong `class="scriba-state-idle"` → rule `.scriba-state-idle > rect { stroke: var(--scriba-state-idle-stroke) }` (`:197-202`) → dark `#313538` (`array.py:535,559`; `queue.py:867,872` — slot dự trữ chỉ thêm `stroke-dasharray`, cùng stroke).
  - Hypercube `<line>` **không** có class trạng thái, **không** trong `.scriba-tree/graph-edges` → **không rule CSS nào khớp** (đã xác nhận không có selector `hypercube` nào trong CSS) → presentation-attr inline `#dfe3e6` thắng → **kẹt ở màu light**, không đổi theo theme.

**Đo lại CR thật trong browser (chrome-headless-shell, `data-theme="dark"`, nền `#151718`):**

| Primitive | stroke đo được | CR vs nền #151718 | Ghi chú |
|---|---|---|---|
| Tree edge | rgb(49,53,56) `#313538` | **1.45** | sw 1.5px |
| Forest edge | rgb(49,53,56) | **1.45** | sw 1.5px |
| Deque ô đầy | rgb(49,53,56) | **1.45** | vs cell-fill #1a1d1e = 1.37 |
| Deque slot dự trữ | rgb(49,53,56) dashed(4,3) | **1.45** | cùng token, chỉ khác nét gạch |
| Array ô | rgb(49,53,56) | **1.45** | vs cell-fill = 1.37 |
| Hypercube edge | rgb(223,227,230) `#dfe3e6` | **13.93** | không theme-aware |

→ Xác nhận đúng 1.45 và 13.93. Ngưỡng WCAG 1.4.11 (non-text) = 3:1; tất cả trừ Hypercube đều **trượt**.

**Light-mode (thách thức tiền đề — đo thật):** Tree, Array **và** Hypercube đều = `#dfe3e6`, CR **1.22** vs nền. Ở light, Hypercube **không** phải ngoại lệ — mọi cạnh đều mờ như nhau (xem `light_full.png` vs `dark_full.png`).

## Kết luận suy ra (Deduced)

1. **Token thủ phạm = `--scriba-state-idle-stroke`** (dark `#313538`), trùng giá trị với `--scriba-border`. Đây là CSS custom property theme-switchable, dùng chung cho idle stroke của MỌI ô/cạnh/viền node.
2. **"Nghịch lý Hypercube" là bug theming dark-only, không phải khác biệt thiết kế.** Hypercube emit cạnh không theme-aware (inline attr trên line không class). Ở light nó đồng nhất (1.22) với các primitive khác; chỉ ở dark nó không switch nên kẹt `#dfe3e6` và tình cờ đạt 13.93. Con số 13.93 là **tình cờ, không phải chủ đích**.
3. **Cạnh mờ là thiết kế toàn cục (Radix "Tonal Architecture", viền slate-6), không riêng dark.** Cả light (1.22:1) lẫn dark (1.45:1) đều dưới 3:1. Vấn đề contrast là hệ thống, không phải regression riêng của dark.
4. **`DARK_THEME` dict là "dormant"** — chỉ được import/re-export (`base.py:41`), **không** bị index (`DARK_THEME[...]`) trong bất kỳ đường emit nào → không golden nào bake giá trị của nó. **Fix phải ở phía CSS**, không phải Python dict (sửa dict chỉ để đồng bộ tài liệu, 0 tác động golden/render).
5. **`test_contrast.py` chỉ gác text-contrast AA ở light** (STATE_COLORS text-vs-fill ≥4.5, ARROW_STYLES) — **không** có kiểm tra dark, **không** có kiểm tra non-text (stroke vs nền). Đó là lý do defect này lọt lưới.

## Blast radius (chính xác)

- **Fix CSS-only nâng token dark** (đổi `--scriba-state-idle-stroke` + `--scriba-border` ở CẢ khối `[data-theme="dark"]` `:717,:724` VÀ `@media` `:786,:790`): CSS được nhúng nguyên văn vào mọi HTML standalone → **107/112 golden HTML đổi byte** (đã xác nhận: chuỗi `--scriba-state-idle-stroke:      #313538` có mặt trong đúng 107 file golden). **0 golden SVG** (3 file) bị ảnh hưởng. **0 test vỡ về mặt logic** — chỉ là refresh cơ học `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden`.
- **Light KHÔNG đụng** (khối dark tách riêng) → không regression contrast light; 2 test pin `#dfe3e6` (`test_primitive_numberline.py:142`, `test_primitive_graph.py:847`) khẳng định giá trị **inline light** → vẫn xanh.
- **Fix Hypercube theme-aware** (đổi `hypercube.py:352` sang phát qua state-class/CSS var như Forest): **0 golden hiện có đổi** (corpus không có primitive hypercube nào). Cần kiểm tra vài unit test hypercube (nếu có assert `stroke="#dfe3e6"`). Rủi ro thấp.
- CSS custom property **cho phép tách dark/light** hoàn toàn → nâng chỉ-dark là khả thi và sạch.

## Nguyên tắc thống nhất & Fix direction

**Cả hai giá trị hiện tại đều KHÔNG đúng:** 1.45 (Tree/Forest/Deque/Array) quá mờ (trượt 3:1); 13.93 (Hypercube) quá chói, cạnh tranh với text/fill của node. Giá trị "đúng" cho một cạnh cấu trúc phụ: xám trung tính đạt ~3.0–3.5:1 — đủ đọc cấu trúc, không lấn node.

- **Đề xuất chính (surgical, cho đúng vấn đề đã báo):** nâng dark `--scriba-state-idle-stroke` + `--scriba-border` lên bậc slate-9/10 dark. Ứng viên cụ thể **`#62696d`** cho **CR ≈ 3.22:1** vs `#151718` (tính bằng đúng công thức WCAG đã tái tạo khớp 1.45/13.93). Token dùng chung nên viền node idle cũng rõ hơn — có lợi, không "ồn" như 13.93. Kèm theo:
  - Sửa **Hypercube theme-aware** (`hypercube.py:352`) để nó nhận cùng token → thôi là ngoại lệ (nếu không, sau khi nâng token, Hypercube vẫn kẹt `#dfe3e6` và lại chói hơn phần còn lại).
  - Cập nhật `DARK_THEME["border"]` cho đồng bộ lockstep (0 tác động golden).
  - Thêm guard dark non-text 3:1 vào `test_contrast.py` để chống tái phát.
- **Tuỳ chọn mở rộng (a11y đầy đủ):** nâng cả viền **light** cho đạt 3:1 — thay đổi thẩm mỹ lớn, golden cả 2 theme; nên tách patch a11y riêng, có review thiết kế.

## Confidence & khuyến nghị phát hành

**Confidence: High** — root cause xác nhận bằng đọc code + CSS cascade + đo browser deterministic; mọi số khớp.

- **Không nên** nhồi việc nâng token dark vào 0.24.0 nếu 0.24.0 không phải bản a11y: 107 golden churn + đổi tông màu nền tảng nên đi trong **một patch a11y/dark-contrast chuyên biệt** (có review thẩm mỹ + guard test mới).
- **Nên** tách **fix Hypercube theme-aware** thành thay đổi nhỏ độc lập (0 golden, low-risk) — có thể vào 0.24.0 một mình để xoá bug theming, ngay cả trước khi quyết định giá trị contrast cuối cùng.

## Giả thuyết (trạng thái)

- H1 "token edge dùng chung" — **Confirmed** (`--scriba-state-idle-stroke`).
- H2 "Hypercube dùng token/thiết kế khác" — **Refuted**; thực chất là inline `THEME["border"]` không theme-aware (`hypercube.py:352`), chỉ lệch ở dark.
- H3 "đây là regression riêng dark" — **Refuted**; light cũng 1.22:1, là thiết kế cạnh-mờ toàn cục.
