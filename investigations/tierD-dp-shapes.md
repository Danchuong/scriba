# Tier D — Nhóm DP-shape: Điều tra khả năng dựng animation

> **BMAD Investigation Case File**
> Investigator: DP-shapes (BMAD Tier-D)
> Ngày: 2026-07-05 · Repo: `scriba` @ `e185786` (0.24.0) · venv: `.venv/bin/python`
> Phạm vi: **chỉ điều tra + render probe**. KHÔNG sửa source, KHÔNG commit.
> Probe: `…/scratchpad/td-dp/*.tex` → render vào `.scriba_tmp/tddp/*.html` (gitignored).

---

## 0. Tóm tắt điều hành

Bốn mục DP-shape được thử dựng bằng lệnh **hiện có của 0.24.0**, render thật, kiểm chứng
bằng markup SVG/HTML (không chỉ exit code).

- **3/4 mục là RECIPE-HÔM-NAY**: CHT/lower-envelope, broken-profile frontier, digit-DP
  flag-grid — dựng được ngay hôm nay, không cần primitive mới.
- **1 mục là gap thật — MÁY-MỚI**: histogram/phân phối **cột chiều-cao-biến-thiên** (convolution
  trượt). Scriba **không có** primitive bar/histogram; `MetricPlot` là line-chart *tích luỹ*
  điểm theo trục step (không vẽ lại phân phối tại chỗ), `Grid` chỉ ép được "tháp gạch" thô.
  Trùng khớp với gap "bar-height" mà một điều tra viên khác đã xác nhận (task #70, completed).
- **1 phát hiện phụ (drift doc↔code)**: helper `plane2d.lower_envelope` (và cả `hull`,
  `intersect`, …) mà `plane2d.md §6` + acceptance test 12.1 hứa gọi được trong `\compute`
  **thực tế không inject vào host Starlark** → `\compute` raise `E1151 NameError`. Hàm Python
  đã tồn tại và đúng — chỉ thiếu dây nối. Đây là **MỞ-RỘNG-NHỎ** rẻ.

### Bảng mục × phân-loại × cost

| # | Mục (số anim ước tính) | Phân loại | Cost | Blocker? |
|---|------------------------|-----------|------|----------|
| 1 | CHT / D&C lower-envelope + per-x winner (~10) | **RECIPE-HÔM-NAY** | 0 | Không |
| 1b| ↳ helper `plane2d.*` gọi được trong `\compute` | MỞ-RỘNG-NHỎ | S (½–1 ngày) | Không (né được) |
| 2 | Variable-height convolving histogram (~10) | **MÁY-MỚI** | M–L | **Có (gap thật)** |
| 2b| ↳ choreography convolution (2 phân phối trượt/lật) | CẦN-EDITORIAL | — | Câu hỏi thiết kế |
| 3 | Broken-profile frontier (~7) | **RECIPE-HÔM-NAY** | 0 | Không |
| 4 | Digit-DP flag-grid (~5) | **RECIPE-HÔM-NAY** | 0 | Không |

Cost: S ≈ nhỏ/khu trú · M ≈ một primitive mới gọn · L ≈ primitive + choreography.

---

## 1. Sổ bằng chứng (evidence ledger)

Thang điểm: **[A]** = quan sát trực tiếp trên output đã render · **[B]** = đọc code/spec ·
**[C]** = suy luận từ doc.

| ID | Probe / lệnh | Kết quả | Grade |
|----|--------------|---------|-------|
| E1 | `p1c_cht_core.tex` render | OK — 5×`scriba-plane-line`, 3×`scriba-plane-segment`, **3×`position_move`** (sweep glide, không teleport) | [A] |
| E2 | `p1_cht.tex` / `p1b` (`\compute{plane2d.lower_envelope(...)}`) | **FAIL `E1151`: `name 'plane2d' is not defined`** — cả khi `\compute` đặt sau `\shape` | [A] |
| E3 | `python -c "plane2d_compute.lower_envelope([...])"` | OK → `[((2,1),-inf,2.0), ((1,3),2.0,2.667), ((-2,11),2.667,inf)]` (đúng 3 mảnh) | [A] |
| E4 | `starlark_worker.py:667-673` | namespace = `_ALLOWED_BUILTINS` + globals; **không có** chỗ inject `plane2d` | [B] |
| E5 | `p2a_metricplot_dist.tex` `--dump-frames` | Frame1 polyline **4 điểm** `48,133,218,304`; Frame2 polyline **8 điểm** `48,84,…,304` — phân phối mới **bị nối thêm bên phải**, KHÔNG vẽ lại tại x=0..3 | [A] |
| E6 | `p2b_grid_bricks.tex` render | OK — recolor `g.block[..][c:c]` chạy; nhưng cần `\recolor{g.all}{idle}` + repaint mọi cột mỗi frame; chiều cao = số ô nguyên, trần = `rows` | [A] |
| E7 | grep 18 primitive + `SCRIBA-TEX-REFERENCE.md` | **Không có** primitive `Bar`/`Histogram`; "bar" duy nhất = header-bar của `label` | [A][B] |
| E8 | `p3_broken_profile.tex` render | OK — trace `<path>` **răng cưa** `M30,104 L216,104 L216,146 L340,146`; frame sau bước gãy dời sang `x=278` (frontier tiến); staircase 38×`done`/4×`current` | [A] |
| E9 | `p3` (bản đầu, cells có `[3,6]` trên grid cols=6) | Trace **soft-drop im lặng** (điểm out-of-range) → 0 path. *Lỗi toạ độ của probe, không phải giới hạn primitive.* | [A] |
| E10| `p4_digit_dp.tex` render | OK — DPTable-2D `cell[i][j]` fill giá trị; **2×`scriba-annotation-arrow`** (arrow_from); recolor nhánh 30×`current`/25×`done` | [A] |

---

## 2. Mục 1 — CHT / D&C lower-envelope + per-x winner  →  RECIPE-HÔM-NAY

**Bối cảnh.** Tập đường thẳng; bao dưới (lower envelope) là hàm min từng khoảng x; con trỏ x
quét chỉ ra đường thắng.

**Cách dựng (đã render — `p1c_cht_core.tex`):**
- `Plane2D` + nhiều `\apply{p}{add_line=("…", slope, intercept)}` — vẽ các đường.
- Bao dưới vẽ bằng chuỗi `add_segment=((x0,y0),(x1,y1))` recolor `state=good` (polyline đậm).
- Con trỏ quét = **đường dọc** `add_line=("sweep", {a=1,b=0,c=x0})`, trượt bằng
  `\apply{p}{move_line={i=4, to_x=…}}` — differ phát `position_move` nên **glide** (E1).
- Mỗi `\step`: recolor đường thắng `state=current`, các đường khác `state=dim`
  (đúng công thức acceptance test `plane2d.md §12.1`).

**Bằng chứng:** E1 — 5 đường, 3 mảnh envelope, 3 lần glide của sweep.

**Bẫy đã gặp (ghi cho builder):** chỉ số **theo từng họ**. Sweep là `line[4]` (4 đường dốc
`line[0..3]`); `add_segment` KHÔNG đẩy chỉ số line. `move_line` chỉ áp cho đường **dọc**
(dốc → `E1467`).

**Phân loại: RECIPE-HÔM-NAY (cost 0).**
**Conclusion / Confidence: Dựng được đầy đủ hôm nay — CAO** (render trực tiếp).

### 2b. Phát hiện phụ — helper `plane2d.*` không gọi được trong `\compute` → MỞ-RỘNG-NHỎ

`plane2d.md §6.6` và acceptance test 12.1 trình bày `plane2d.lower_envelope(lines)` như
đường chính để tính envelope. Thực tế `\compute` raise **`E1151 name 'plane2d' is not
defined`** (E2), kể cả khi `\shape{Plane2D}` khai trước. Hàm Python có sẵn và **đúng** (E3);
host Starlark chỉ nạp `_ALLOWED_BUILTINS` + globals, không inject namespace primitive nào (E4).

- **Ảnh hưởng:** KHÔNG chặn mục 1 — tác giả tự tính envelope trong `\compute` (số học
  Starlark thuần) hoặc precompute toạ độ mảnh rồi `add_segment`.
- **Đề xuất tối thiểu:** đưa module `plane2d_compute` vào dict `globals` truyền cho worker
  (có điều kiện khi có shape `Plane2D`, hoặc vô điều kiện — vô hại), whitelist truy cập
  thuộc tính. Hàm đã có unit test → chủ yếu là dây nối + test. **Cost S (½–1 ngày).**
- Hoặc rẻ hơn nữa: **sửa doc** cho khớp code (bỏ lời hứa helper) nếu chưa muốn wiring.

---

## 3. Mục 2 — Variable-height convolving histogram  →  MÁY-MỚI (GAP THẬT)

**Bối cảnh.** 2 phân phối/histogram cuộn (convolution): cột cao–thấp đổi chiều cao, một
phân phối **trượt/lật** qua phân phối kia; tích chập = tổng tích chồng lấn.

**Thử 1 — `MetricPlot` (`p2a`): KHÔNG hợp.** `MetricPlot` là **line-chart tích luỹ**: mỗi
`\apply` *nối thêm* 1 điểm theo trục = step. Nạp phân phối `[2,5,3,1]` (4 điểm) ở frame 1,
rồi `[1,4,6,2]` ở frame 2 → frame 2 có **8 điểm** dàn full-width (E5), phân phối mới **bị đẩy
sang phải** chứ không vẽ lại tại chỗ. Không có cách "clear + redraw N cột mỗi frame". ⇒ không
thể mô tả một phân phối cố-định-vị-trí biến hình theo thời gian.

**Thử 2 — `Grid` "tháp gạch" (`p2b`): ép được nhưng thô.** Biểu diễn cột cao `h` tại cột `c`
bằng recolor `h` ô đáy (`\recolor{g.block[R-h:R-1][c:c]}{state=…}`). Render OK (E6) nhưng:
- chiều cao **chỉ số nguyên**, **trần = `rows`** (không có cột 3.5, không mượt);
- mỗi frame phải `\recolor{g.all}{idle}` rồi **sơn lại mọi cột** (churn lớn);
- **không glide** chiều cao (ô đổi màu, không "mọc/rụt");
- **không overlay** 2 phân phối trượt chồng nhau (một ô chỉ một màu).

**Không có primitive bar/histogram** trong 18 primitive (E7). `Array`/`NumberLine` cũng
không mã hoá chiều cao.

**Phân loại: MÁY-MỚI.** Cần primitive dạng `BarChart`/`Histogram`:
- `bars=[…]`, `\apply{h.bar[i]}{height=…}` **glide** chiều cao (như `move_*`/`reorder` đã có ở
  Array/Plane2D — cùng hạ tầng `position_move`);
- trục hoành cố định vị trí bin; giá trị thực (không chỉ nguyên).
- **Cost M** cho bar động cơ bản.

### 3b. Choreography convolution → CẦN-EDITORIAL

Riêng convolution (2 phân phối, một cái **lật** rồi **trượt** offset, tô vùng chồng lấn, cột
kết quả cộng dồn) vượt quá "bar động". **Câu hỏi editorial cho builder/PM:**
1. Convolution vẽ **2 hàng bar** (f cố định, g trượt-lật) + **1 hàng kết quả**, hay overlay
   trên cùng trục?
2. "Trượt" cần offset liên tục (glide mượt) hay từng nấc số nguyên (đủ cho editorial CP)?
3. Có cần tô **vùng tích chồng lấn** + nhãn tổng tích tại mỗi offset không?
→ Quyết định phạm vi này đẩy cost giữa **M** (chỉ bar động) và **L** (bar + choreography trượt/lật).

**Conclusion / Confidence: Gap thật, cần primitive mới — CAO** (E5+E6+E7, và trùng task #70).

---

## 4. Mục 3 — Broken-profile frontier  →  RECIPE-HÔM-NAY

**Bối cảnh.** DP mặt cắt (broken profile) trên lưới: biên "gãy" răng cưa tiến qua các ô.

**Cách dựng (đã render — `p3_broken_profile.tex`):**
- `Grid rows×cols`; vùng đã xử lý = `\recolor{g.block[…][…]}{state=done}` (bậc thang ô `done`),
  ô đang xét `state=current`.
- **Biên gãy = `\trace{g}{cells=[[r,c],…], color=good, label="frontier"}`** — vẽ **polyline
  răng cưa tự-vẽ** dọc tâm ô. Frame sau đổi cells → điểm gãy dời phải (frontier tiến).

**Bằng chứng:** E8 — path răng cưa `M30,104 L216,104 L216,146 L340,146` (một bậc xuống tại
x=216), frame kế bậc dời sang x=278; staircase `done`/`current` đúng.

**Bẫy đã gặp (quan trọng):** `\trace` **soft-drop im lặng cả trace** nếu **một** điểm cells
out-of-range (E9 — probe đầu để `col=6` trên grid `cols=6`, hợp lệ 0..5). Builder phải giữ
mọi `[r,c]` trong biên. (Xác nhận trace hỗ trợ Grid: `base.py:supports_trace`,
`emit_traces_under` — E7/hint.)

**Phân loại: RECIPE-HÔM-NAY (cost 0).**
**Conclusion / Confidence: Dựng được hôm nay (Grid block-recolor + trace) — CAO.**

---

## 5. Mục 4 — Digit-DP flag-grid  →  RECIPE-HÔM-NAY

**Bối cảnh.** Bảng trạng thái digit-DP (vị trí × tight-flag × …), tô theo nhánh.

**Cách dựng (đã render — `p4_digit_dp.tex`):**
- `DPTable{rows=pos, cols=state}` (2-D); hàng = vị trí chữ số, cột = trạng thái
  (tight / các bucket free). Fill `\apply{dp.cell[i][j]}{value="…"}`.
- Tô nhánh: `\recolor{dp.cell[i][j]}{state=current}` (giữ tight) vs `state=done` (đi free).
- Chuyển trạng thái: `\annotate{dp.cell[i][j]}{arrow_from="dp.cell[i-1][j']", …}` — cung
  Bezier có mũi tên.

**Bằng chứng:** E10 — cell 2-D fill giá trị, 2 cung `arrow_from`, recolor 2 nhánh.

**Phân loại: RECIPE-HÔM-NAY (cost 0).**
**Conclusion / Confidence: Dựng được hôm nay (DPTable-2D + recolor + arrow_from) — CAO.**
*Lưu ý:* digit-sum × tight × leading-zero là **3 chiều**; DPTable là 2-D → gộp
(tight,leading-zero) vào một trục cột. Nếu editorial cần cả 3 chiều tách bạch → cân nhắc
nhiều DPTable song song (vẫn RECIPE, chỉ nhiều shape hơn).

---

## 6. Hand-off Brief (cho builder tiếp nhận)

**Làm được ngay, không chờ ai (RECIPE-HÔM-NAY):**
- **CHT (#1):** `Plane2D` + `add_line` (dốc) + `add_line {a,b,c}` (dọc) + `move_line{to_x}`
  (glide) + `add_segment` cho envelope + recolor `current`/`dim`. Nhớ: chỉ số **theo họ**,
  sweep là đường dọc.
- **Broken-profile (#3):** `Grid` + `\recolor{…block…}{done}` (bậc thang) +
  `\trace{cells=[…]}` (frontier răng cưa). Nhớ: **mọi `[r,c]` phải trong biên**, kẻo trace
  bị soft-drop im lặng.
- **Digit-DP (#4):** `DPTable{rows,cols}` 2-D + `\apply{cell[i][j]}{value}` + recolor nhánh +
  `\annotate{arrow_from}`. Gộp cờ phụ vào trục cột.

**Cần quyết định trước khi build:**
- **Histogram (#2) — MÁY-MỚI:** đề xuất primitive `BarChart`/`Histogram` với bar **glide chiều
  cao** (tái dùng hạ tầng `position_move`). **Cost M** cơ bản. TRƯỚC đó cần chốt **3 câu hỏi
  editorial ở §3b** (2 hàng hay overlay? trượt mượt hay theo nấc? tô vùng chồng lấn?) — quyết
  định đẩy cost lên **L** nếu làm cả choreography convolution.

**Win rẻ, tuỳ chọn:**
- **#1b:** wire `plane2d_compute` vào globals của `\compute` (**cost S**) — mở khoá
  `lower_envelope`/`hull`/`intersect` mà doc đã hứa; hàm + test đã có. Hoặc sửa doc cho khớp.

**Không cần làm:** không có mục nào trong nhóm này cần primitive mới **ngoài** histogram (#2).

---

## 7. Phụ lục — Probe files

Tất cả tại `…/scratchpad/td-dp/` (source `.tex`) → render `.scriba_tmp/tddp/*.html` (gitignored):

| File | Mục | Vai trò |
|------|-----|---------|
| `p1c_cht_core.tex` | 1 | CHT chạy được: lines + envelope segments + sweep glide |
| `p1_cht.tex`, `p1b_cht_reorder.tex` | 1b | Chứng minh `plane2d.*` không inject (E1151) |
| `p2a_metricplot_dist.tex` | 2 | Chứng minh MetricPlot tích luỹ (không morph tại chỗ) |
| `p2b_grid_bricks.tex` | 2 | Grid "tháp gạch" — ép được nhưng thô |
| `p3_broken_profile.tex` | 3 | Grid block-recolor + trace frontier răng cưa |
| `p4_digit_dp.tex` | 4 | DPTable-2D + recolor nhánh + arrow_from |

Lệnh render: `.venv/bin/python render.py <in.tex> -o .scriba_tmp/tddp/<out>.html`
(dump state: thêm `--dump-frames`).
