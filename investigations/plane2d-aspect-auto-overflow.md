# Plane2D `aspect="auto"` — circle/arc/wedge bán kính lớn tràn viewBox

- **Repo / commit**: scriba @ `18443bb` (main) · **Ngày**: 2026-07-05 · **Investigator**: BMAD (aspect=auto overflow)
- **Scope**: CHỈ điều tra — không sửa source, không commit.
- **Nguồn**: hunt-visual (đánh dấu LOW / by-design edge). Case tiền nhiệm: `investigations/gap-new-substrates.md §4.3` (viết *trước* khi circle/arc/wedge tồn tại).
- **Artifacts**: `.scriba_tmp/bmad-aspect/{auto_r4,auto_r1,equal_r4}.{tex,html}`, screenshot `scratchpad/bmad-aspect/shot_*.png`, script đo `scratchpad/bmad-aspect/{measure,summ}.py`.
- **Thang bằng chứng**: `[Confirmed]` đọc code · `[Measured]` số đo Chrome/Playwright · `[Deduced]` suy luận · `[Ref]` chuẩn ngoài (matplotlib).

---

## Hand-off Brief (TL;DR)

Circle/arc/wedge được emit dưới dạng `<circle r=math-unit>` **bên trong** group `transform="translate scale(sx,sy)"` (honest-ellipse, quyết định §4.3). `bounding_box()` của Plane2D **cố định = width×height suy từ xrange/yrange**, KHÔNG bao giờ nới theo nội dung. Vì vậy circle có `r` vượt nửa-khoảng-range (vd `r=4` trong `yrange=[-2,2]`) vẽ ra ellipse cao **512px** trong viewBox **344px**, **tràn 84px trên + 84px dưới**, và bị **clip cứng tại biên SVG** (`overflow:hidden` mặc định) — đè qua dải tick-label và trục, "trông gãy".

**Kết luận**: **Chủ yếu by-design + MỘT bất nhất chẩn đoán có thật (bug nhẹ)**. Việc viewBox không nới là *nhất quán* (mô hình "range cố định" giống matplotlib khi set xlim/ylim). NHƯNG:
1. `_warn_center_offscreen` chỉ kiểm **tâm** — circle tâm-trong-range mà bán kính tràn thì **im lặng tuyệt đối** (không warning), trong khi point ngoài range thì có E1463. Đây là lỗ hổng bất nhất point-vs-circle.
2. scriba tự mô tả là "clip như matplotlib tại axes" nhưng **không có clipPath tại plot-rect** — nó chỉ dựa vào clip của SVG ngoài (rộng hơn plot một vành `_PAD=32`), nên nội dung tràn *bò qua vùng tick-label* thay vì bị cắt gọn ở mép plot như matplotlib thật `[Ref]`.

**Đề xuất 0.24.0**: lối (a) — mở rộng cảnh báo sang bán kính (E1463 khi `cx±r / cy±r` vượt range). Blast golden = **0**, khớp cách point cảnh báo, rẻ. Lối (b) nới viewBox: **bác** (blast lớn + sai mô hình). Lối (c) chỉ doc: luôn làm kèm (a). **Confidence: High.**

---

## 1. Tái hiện + số đo `[Measured]`

3 case render qua pipeline thật (`render.py --static`), đo bằng Chrome headless (Playwright MCP treo vì runtime 480KB → dùng `playwright.sync_api` + Chrome hệ thống).

| Case | aspect | r | yrange | transform `scale` | circle render (px) | tràn viewBox | clip? |
|------|--------|---|--------|-------------------|--------------------|--------------|-------|
| `auto_r4` | auto | 4 | [-2,2] | `(42.67, -64.0)` | **341 × 512** (ellipse) | **top 84 / bottom 84** | **CÓ** (`overflow:hidden`) |
| `auto_r1` | auto | 1 | [-2,2] | `(42.67, -64.0)` | 85 × 128 | không (dư mỗi bên ~108) | không |
| `equal_r4` | equal | 4 | [-2,2] | `(42.67, -37.25)` | 341 × 298 | **top 30.5 / bottom 30.5** | **CÓ** |

- viewBox auto = `0 0 344 344`; `getComputedStyle(svg).overflow == "hidden"` `[Measured]` → circle tràn bị **trình duyệt cắt tại mép SVG**, không phải scriba tự clip.
- Screenshot `shot_auto_r4.png`: ellipse mờ khổng lồ, **cung trên/dưới bị xén phẳng** tại khung SVG, hai cung trái/phải luồn sát hàng tick `-3..3`. `shot_auto_r1.png`: ellipse gọn trong plot, bình thường.
- **Chốt quan trọng** (`equal_r4`): aspect=equal **vẫn tràn 30px** vì `r=4 > 2` (nửa yrange). ⇒ **thủ phạm là bán kính vượt range, KHÔNG phải aspect.** aspect=auto chỉ *phóng đại* mức tràn (yscale 64 vs equal 37).

## 2. Cơ chế & phân biệt bug-vs-by-design `[Confirmed]`

- `bounding_box()` `plane2d.py:1051-1059` → `BoundingBox(0,0, width, height+arrow+pos)`. **Không** duyệt point/circle/arc/wedge; frame = range±`_PAD`. Đúng cho *mọi* kind, không phải "quên circle".
- Content group `:1089-1093` bọc `translate(tx,ty) scale(sx,sy)`; `_emit_circles :1444-1467` phát `<circle cx cy r>` trong group ⇒ honest-ellipse `rx=r|sx|, ry=r|sy|` (comment `:1391-1400`).
- `_compute_transform :222-230`: `sx=(w-2·PAD)/xspan`, `sy=-(h-2·PAD)/yspan`.
- **Nhất quán point-vs-line-vs-circle**:
  - Line: **clip cứng** vào range (`_emit_lines :1301-1305` → `clip_line_to_viewport`). Không bao giờ tràn.
  - Point: **không clip** nhưng bán kính *pixel cố định* 4px (`:1251-1263`) → tràn tối đa 4px; **có** cảnh báo E1463 theo **vị trí** (`:283-293`).
  - Circle/arc/wedge: **không clip**, bán kính *math-unit* → tràn tùy `r`; cảnh báo `_warn_center_offscreen :469-487` **chỉ xét tâm** (`:492,498,504`).
- ⇒ **Bất nhất thật** [Deduced]: point cảnh báo theo extent-thực-tế của nó (chính là tâm), còn circle bỏ qua extent `cx±r, cy±r`. Circle `(0,0,r=4)` tâm-trong-range: **0 warning** dù tràn 84px. Đây là phần "bug" bào chữa được — *chẩn đoán*, không phải *render*.
- **Không có clipPath** trong plane2d.py (`grep = 0`). Nên "clip như matplotlib" là **nửa đúng**: có clip (của SVG ngoài) nhưng ở *mép viewBox*, không ở *mép plot-rect* → tràn đè lên dải tick.

## 3. Chuẩn tham chiếu — matplotlib `[Ref]`

Khi tác giả set `xlim/ylim` tường minh (đúng mô hình scriba: xrange/yrange luôn tường minh, default `[-5,5]`), matplotlib **KHÔNG autoscale** theo patch; `Circle` có `clip_on=True` mặc định ⇒ **clip vào hình chữ nhật axes (plot-rect)**, không tràn ra tick/margin. ⇒ Mô hình đúng-matplotlib = **clip cứng tại plot-rect** (tác giả tự lo range), **không** nới-viewBox-theo-nội-dung. scriba nên theo *mô hình clip*, nhưng hiện clip **sai ranh giới** (mép SVG thay vì mép plot).

## 4. Ba lối (đánh giá) — mở rộng §4.3

| Lối | Nội dung | Đúng-đắn | Blast golden | Phức tạp |
|-----|----------|----------|--------------|----------|
| **(a) ĐỀ XUẤT** | Mở rộng cảnh báo: E1463 (hidden) khi `cx±r`/`cy±r` (và endpoint arc/wedge) vượt range | Vá đúng bất nhất point-vs-circle; tác giả biết để đổi range/aspect | **0** — cảnh báo nằm ở `Document.warnings`, **0 golden** render circle hiện có; E1463 chỉ ở unit test | Thấp (~5-8 dòng, sửa `_warn_center_offscreen`) |
| **(b) Nới viewBox theo circle** | `bounding_box()` gộp extent nội dung | **Sai mô hình** (matplotlib không nới khi lim tường minh); phá bất biến "range=frame"; point/line clip mà circle nới ⇒ bất nhất mới | **Rất lớn** (mọi primitive dùng bounding_box → viewBox) | Cao |
| **(c) Giữ nguyên + doc** | Ghi chú "r vượt range ⇒ tràn; dùng aspect=equal hoặc chỉnh range" | Không vá silent-overflow | 0 | Rất thấp |
| **(d) tùy chọn tương lai** | Thêm `clipPath` tại plot-rect (matplotlib-parity: cắt gọn mép plot, không bò qua tick) | Đúng-matplotlib nhất, "trông có chủ đích" | Trung bình (đổi golden khi nội dung vượt range — hiện 0 golden) | Trung bình |

**Khuyến nghị**: (a) + (c) cho 0.24.0. (b) bác. (d) để ngỏ cho bản sau nếu muốn parity thật.

## 5. Phát hiện phụ

- **[Measured] aspect=equal KHÔNG tròn thật**: `equal_r4` scale `(42.67, -37.25)` — `|sx|≠|sy|` (~14% lệch), render 341×298 (ellipse). Do `height = width·yspan/xspan` (`:174-180`) tính *trước* rồi mới trừ `2·PAD` ở cả tử width & height khi lấy scale (`:227-228`) ⇒ padding phá đẳng tỉ với range không-vuông. Bug tiềm ẩn **riêng**, đáng mở case khác (không thuộc phạm vi aspect=auto).
- **[Confirmed] style idle**: circle idle `stroke="#dfe3e6"` = `THEME["border"]` qua `svg_style_attrs('idle')` — **theme-derived, dùng chung mọi element idle**, KHÔNG phải hardcode riêng circle (task mô tả hơi lệch). `fill="none"` (không phải rgba 0.15). Chỉ **wedge** có hardcode thật `fill="rgba(0,114,178,0.15)"` (`:1513`). scriba là single-theme (`THEME` một dict) nên "not theme-aware" chưa thành vấn đề tới khi có dark-mode.

## 6. Conclusion + Confidence

- **Bug hay by-design?** → **By-design về render** (frame=range nhất quán, giống matplotlib set-lim) **+ bug nhẹ về chẩn đoán** (cảnh báo center-only bỏ sót overflow bán kính — bất nhất với point). Cộng thêm imperfection: tự nhận "clip như matplotlib" nhưng clip ở mép SVG chứ không mép plot.
- **Fix hướng nào**: lối **(a)** (cảnh báo theo extent) là vá đúng-bản-chất, blast=0; kèm **(c)** doc. **Không** làm (b).
- **Confidence: High** — số đo Chrome khớp giải tích (84px = `(4−2)·64px − 12px margin`), code đọc trực tiếp, blast=0 xác nhận bằng grep golden.
- **Vào 0.24.0?** — **Có, nên** (chỉ là warning + doc, rủi ro ~0, đóng bất nhất point-vs-circle). (d) clipPath và equal-mode-distortion để bản sau.

---

## Phụ lục — trích dẫn

| Chủ đề | plane2d.py |
|--------|-----------|
| `bounding_box` cố định width×height | `:1051-1059` |
| `_compute_transform` (sx, sy) | `:222-230` |
| aspect=equal height formula | `:174-180` |
| content group transform | `:1089-1093` |
| `_emit_circles` (honest-ellipse) | `:1444-1467` |
| comment "aspect decision" | `:1391-1400` |
| `_warn_center_offscreen` (center-only) | `:469-487` |
| point off-viewport warn (theo vị trí) | `:283-293` |
| line clip vào viewport | `:1301-1305` |
| point bán kính pixel cố định | `:1251-1263` |
| wedge fill hardcode | `:1513` |
| KHÔNG có clipPath | grep = 0 |
