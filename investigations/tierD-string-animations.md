# Tier D — Nhóm String: two-row offset-slide (KMP/Z) + Manacher center-expand

- **Điều tra viên:** BMAD investigator (nhóm String)
- **Repo/version:** scriba @ `e185786` (0.24.0 vừa release)
- **Ngày:** 2026-07-05
- **Phạm vi:** CHỈ điều tra + case file này. Không sửa source, không commit.
- **Câu hỏi campaign:** Tier A/B/C của JudgeZone census đã ship. Tier D = animation đặc thù từng bài ("land with their editorials"). Nhóm String gồm 2 cụm: (1) two-row string offset-slide + failure-jump (~7 bài KMP/Z), (2) Manacher center-expand + mirror (~4 bài). Câu hỏi: dựng được bằng surface 0.24.0 hiện có không, hay cần máy mới?

---

## 1. Tóm tắt điều hành

**Cả hai cụm đều là RECIPE-HÔM-NAY — dựng được ngay bằng lệnh 0.24.0, 0 verb mới.** Tôi đã render probe thật cho từng cụm và chụp từng frame để kiểm chứng. Bằng chứng quan trọng nhất:

- **KMP two-row-slide:** hai Array cùng bề rộng xếp chồng **thẳng hàng cell-cell tuyệt đối**; cú **failure-jump trượt vật lý** của pattern đạt được bằng `reorder` (xoay vòng) trên một pattern-array đã pad blank — pattern "ABABC" **glide** từ slot 0–4 sang 2–6 đúng như ý đồ; `\link` nối cột so sánh giữa hai hàng; binding-caret `i/j` bám con trỏ và **rebind sạch qua reorder**. Ước đạt ~85–90% ý đồ.
- **Manacher:** `\highlight{S.range[c-r:c+r]}` mở rộng cửa sổ đối xứng; hai binding-caret đánh dấu hai đầu L/R; `\link{S.cell[i] <-> S.cell[i']}` vẽ cung cặp đối xứng và cung **gương i'=2C−i**; `\annotate` đánh dấu tâm C. Ước đạt ~85%.

**Điểm neo lịch sử:** `reorder` **mới ship trong chính 0.24.0** (§7.1 reference). Đây là verb mở khóa cú "trượt gliding" — editorial KMP đang ship (`examples/algorithms/string/kmp.tex`) được viết TRƯỚC khi có reorder nên **không hề trượt**: nó xếp 3 Array tĩnh (P size 9, F size 9, T size 19 — thậm chí **không thẳng hàng**) rồi chỉ `\recolor` + `\cursor` hop + `\annotate`. Tier D two-row-slide chỉ khả thi kể từ release này.

| Cụm | Phân loại | Cost | Verb mới? | Chặn bởi editorial |
|---|---|---|---|---|
| Two-row offset-slide + failure-jump (KMP/Z, ~7) | **(a) RECIPE-HÔM-NAY** (+ tùy chọn (b) ergonomic) | 0 (recipe) / S (nếu làm sugar `shift=k`) | Không | Câu hỏi #1 (KMP/Z-block vs two-pointer) — đổi *recipe*, không đổi *máy* |
| Manacher center-expand + mirror (~4) | **(a) RECIPE-HÔM-NAY** | 0 | Không | Câu hỏi #4 (raw vs #-transformed; có show mirror-reuse không) — đổi *data + số step* |

Phù hợp triết lý campaign (recipe > extension > new-machinery): **cả hai dừng ở recipe.**

---

## 2. Phương pháp

1. Đọc `docs/SCRIBA-TEX-REFERENCE.md` (2038 dòng) — nắm chính xác surface: Array (§7.1, có `reorder` từ 0.24.0), `\cursor` hop + binding-caret (§5.11), `\link`/`\combine` (§5.19), `\annotate`/`\trace` (§5.8–5.9), `range[i:j]` selector (§8), VariableWatch (§7.15).
2. Đọc prior-art: `examples/algorithms/string/kmp.tex` (= golden `tests/golden/examples/corpus/kmp.tex`, byte-identical) — editorial KMP đang ship.
3. Dựng probe thật cho từng cụm, render bằng `.venv/bin/python render.py`, rồi **chụp từng frame** interactive bằng Playwright (venv) để kiểm chứng bằng mắt.
4. Xác minh điểm nghi ngờ (caret "?" sau reorder) bằng cách chụp lại sau khi glide settle.

**Probe paths** (trong `.../scratchpad/td-str/`):
- `kmp_slide.tex` → `kmp_slide.html` (+ `_static`), frames `kmp_f0..f4.png`, `kmp_f3_settled.png`
- `manacher.tex` → `manacher.html` (+ `_static`), frames `man_f0..f4.png`

---

## 3. Cụm 1 — Two-row string offset-slide + failure-jump (KMP/Z, ~7 bài)

### 3.1 Ý đồ animation
Hai hàng ký tự: **text ở trên, pattern ở dưới**, trượt lệch offset nhau. Khi mismatch, pattern **nhảy vật lý sang phải** theo failure function (KMP: shift = j − F[j−1]; Z: nhảy theo z-box). Con mắt phải thấy pattern *trượt* để tái căn.

### 3.2 Bằng chứng theo cấp độ

**[XÁC NHẬN] Hai Array cùng size xếp chồng thẳng hàng cell-cell.**
Probe khai báo `T` (size 12) và `P` (size 12, pattern pad blank ở đuôi). Frame 3 (`kmp_f2.png`): `T[4]=A` (viền đỏ) nằm **chính xác phía trên** `P[4]=C` (viền đỏ), mọi cột 0..11 khớp trục dọc. → Vấn đề "offset 2 array không thẳng hàng" **KHÔNG xảy ra** miễn hai array cùng `size` + cùng metric cell. (Editorial đang ship dùng P size 9 / T size 19 nên lệch — đó là lựa chọn cũ, không phải giới hạn.)

**[XÁC NHẬN] Cú failure-jump = trượt gliding, dựng bằng `reorder` xoay vòng trên array pad-blank.**
Cơ chế: pattern nhúng trong array rộng bằng text, phần thừa để blank (`""`). Trượt phải k = xoay phải k (`reorder` là hoán vị đầy đủ 0..n−1; xoay là hoán vị hợp lệ; blank cuộn về đầu, vô hình). Probe frame 4 (`kmp_f3.png`): sau `\apply{P}{reorder=[10,11,0,1,2,3,4,5,6,7,8,9]}`, "ABABC" **đã glide từ slot 0–4 sang 2–6**, slot 0–1 thành blank, vẫn thẳng hàng dưới `T[2..6]`. Narration "pattern GLIDE sang offset 2" khớp hình. → Đây chính là cú "offset-slide" mà Tier D muốn, **đạt bằng verb có sẵn**.
Vì `reorder` glide theo identity-per-slot (§7.1, đã có test `test_array_reorder.py`), chuyển động mượt như một sorting-pass — không cần suy đoán.

**[XÁC NHẬN] `\link` nối cột so sánh giữa hai hàng.**
Frame 3: `\link{T.cell[4] <-> P.cell[4]}{label="so sanh"}` vẽ **cầu dọc** ngay cột đang so sánh — giải quyết nhu cầu "cột dóng hàng" tốt hơn cả một caret. Cross-shape bridge (§5.19) làm đúng việc này.

**[XÁC NHẬN] Binding-caret `i` (text) và `j` (pattern) bám con trỏ, rebind sạch qua reorder.**
`\cursor{T}{id=i, at="w.var[i]"}` + `\cursor{P}{id=j, at="w.var[j]"}`. Nghi vấn: frame 4 chụp sớm thấy caret `i` hiện "?". **Đã bác bỏ**: chụp lại sau settle 3.5s (`kmp_f3_settled.png` + dump nhãn) cho `i→2, j→0` sạch. → "?" chỉ là artifact **giữa lúc glide**, KHÔNG phải lỗi compose caret+reorder.

**[SUY LUẬN] Hai caret nằm ở hai band riêng (i dưới text, j dưới pattern).**
Binding-caret parking trong band ngay **dưới** cell nó trỏ (§5.11). Với layout text-trên/pattern-dưới: caret `i` rơi vào khe giữa hai hàng, caret `j` rơi xuống dưới cùng — **không** có một caret dùng chung "giữa hai hàng". Đây đúng là điểm campaign đã lường ("caret không park giữa 2 hàng"). Nhưng thực nghiệm cho thấy `\link` cột thay thế tốt hơn caret chung, nên đây **không phải blocker**.

**[SUY LUẬN] Chi phí authoring của recipe: viết tay hoán vị xoay mỗi lần trượt.**
Mỗi cú trượt cần một `reorder=[...]` là hoán vị đầy đủ của toàn array — cơ học nhưng dài dòng khi có nhiều lần nhảy. Đổi lại là cú glide. Phương án thay thế (viết lại value từng cell) đơn giản hơn nhưng **teleport, mất chuyển động trượt** → không đạt ý đồ.

### 3.3 Phân loại & kết luận

- **Phân loại: (a) RECIPE-HÔM-NAY.** Đủ lệnh; chỉ cần một doc pattern ("two-row aligned string: hai Array cùng size + pad blank + `reorder`-xoay để trượt + `\link` nối cột + caret i/j"). Nên đặt vào `docs/cookbook/` (cạnh 11/12).
- **Tùy chọn (b) MỞ-RỘNG-NHỎ, cost S — không bắt buộc:** thêm sugar `\apply{P}{shift=k}` = dịch value sống sang phải k kèm glide + blank-fill, gói lại phép xoay để tác giả khỏi viết tay hoán vị. Additive thuần, không đụng verb hiện có. Chỉ nên làm nếu ≥7 bài này thực sự nhiều cú nhảy.
- **Kết luận:** Dựng được ngay, ~85–90% ý đồ. **Độ tin cậy: CAO** (có probe render + chụp frame chứng minh cả căn hàng lẫn cú glide).

### 3.4 Chặn bởi editorial (câu hỏi phải hỏi bài trước khi build hàng loạt)
1. **Thuật toán nào?** ~7 bài này *shift một pattern như khối cứng* (KMP / Z-function) hay *đi hai con trỏ độc lập trên một chuỗi* (two-pointer / rolling-hash)?
   - Nếu KMP/Z-block → recipe reorder-slide ở trên khớp.
   - Nếu two-pointer → recipe **binding-caret two-pointer đã ship** phủ sẵn (không cần trượt gì cả).
   → Đổi *recipe*, không đổi *máy*.
2. KMP hay Z: cần show **bảng F/z-array** song song (như editorial hiện tại) hay chỉ cần hàng text + pattern trượt? (đổi số shape).
3. Có cần animate **giai đoạn build failure-function** riêng không, hay chỉ giai đoạn match? (đổi số step).

---

## 4. Cụm 2 — Manacher center-expand + mirror (~4 bài)

### 4.1 Ý đồ animation
Bán kính palindrome **mở dần từ tâm** (đối xứng hai phía). Dùng **gương** phản chiếu qua tâm phải-nhất (C) để khởi tạo bán kính cho vị trí mới i qua i'=2C−i, tránh so sánh lại.

### 4.2 Bằng chứng theo cấp độ

**[XÁC NHẬN] Cửa sổ đối xứng mở dần bằng `highlight{range[c-r:c+r]}`.**
Probe chuỗi `[a,b,a,c,a,b,a]`, tâm C=3. Frames 1→4 (`man_f0..f3.png`): highlight range nở `[3:3]→[2:4]→[1:5]→[0:6]`, `\recolor{...good}` tô dần đối xứng hai bên tâm. Frame `man_f3.png` (r=3): cả chuỗi xanh, palindrome full.

**[XÁC NHẬN] Hai đầu mở rộng L/R đánh dấu bằng binding-caret.**
`\cursor{S}{id=L, at="w.var[L]"}` + `\cursor{S}{id=R, ...}`. `man_f3.png`: caret L (xanh) dưới cell 0, caret R (đỏ) dưới cell 6 — đúng hai biên palindrome.

**[XÁC NHẬN] Cặp đối xứng + gương i'=2C−i vẽ bằng `\link`.**
`man_f3.png`: `\link{S.cell[0] <-> S.cell[6]}{label="S[0]=S[6]=a"}` là cung dóng qua đỉnh nối cặp đối xứng. Frame 5 (`man_f4.png`): vị trí mới i=4 (xanh current), pill `tam C=3` trỏ vào cell 3, và `\link{S.cell[4] <-> S.cell[2]}{label="guong: i'=2C-i=2"}` vẽ **cung gương** nối i↔i'. → Đúng phản chiếu Manacher.

**[SUY LUẬN] Không có "trục gương" tường minh tại tâm.**
Phản chiếu được truyền qua cung + pill "tam C", không phải một đường đối xứng dọc tại tâm. Đủ đọc, nhưng một guide-line tâm sẽ sạch hơn — **không bắt buộc**.

**[SUY LUẬN] `\highlight` là ephemeral (xóa ở step kế).**
Muốn cửa sổ palindrome **giữ nguyên** qua nhiều step thì dùng `\recolor{state}` thay vì `\highlight` (như probe đã làm), hoặc re-issue mỗi step. Chỉ là ghi chú authoring.

### 4.3 Phân loại & kết luận
- **Phân loại: (a) RECIPE-HÔM-NAY.** Mọi mảnh có sẵn và ghép trơn. Cần doc pattern ("Manacher: range nở đối xứng + caret L/R + `\link` gương + annotate tâm").
- **Kết luận:** Dựng được ngay, ~85% ý đồ. **Độ tin cậy: CAO** (probe render + chụp frame cả center-expand lẫn mirror).

### 4.4 Chặn bởi editorial
1. Dùng **chuỗi raw** (odd palindrome) hay **chuỗi #-transformed** `#a#b#a#` (thống nhất odd/even)? → đổi `data` của Array + độ dài, không đổi máy.
2. Có show **tối ưu mirror-reuse** (dùng lại z-box, `P[i]=min(P[i'], R−i)`) một cách tường minh không, hay chỉ naive center-expand? → đổi số step + số `\link`.
3. Số bài (~4) có bài nào cần **đếm/liệt kê tất cả palindrome** thay vì chỉ tìm dài nhất không? (đổi cách annotate kết quả).

---

## 5. Đề xuất mở rộng (chỉ tùy chọn — recipe đã đủ ship)

| # | Đề xuất | Loại | Cost | Lý do |
|---|---|---|---|---|
| E1 | Sugar `\apply{a}{shift=k}` — dịch value sống ±k kèm glide + blank-fill (gói `reorder`-xoay) | additive | **S** | Bỏ việc viết tay hoán vị mỗi cú KMP-shift; chỉ đáng nếu nhiều lần nhảy |
| E2 | Caption shape cập nhật theo frame (vd "offset 0"→"offset 2") | additive | S | Hiện caption tĩnh; nay phải narrate. Nhỏ, cosmetic |
| E3 | Manacher: guide-line trục gương tại tâm (annotate dạng đường dọc) | additive | S–M | Sạch hơn cho mirror; không bắt buộc |

Không đề xuất verb/primitive mới nào (MÁY-MỚI = 0). Triết lý "0 verb mới nếu tránh được" được giữ.

---

## 6. Hand-off Brief

**Cho người sẽ build Tier D nhóm String:**

- **Bắt đầu bằng recipe, không phải code:** cả 11 bài (7+4) dựng bằng 0.24.0. Viết 2 cookbook pattern:
  1. *Two-row aligned string + reorder-slide* — mẫu: `.../scratchpad/td-str/kmp_slide.tex`. Chốt: (a) hai Array **cùng `size`** (pattern pad blank ở đuôi) để thẳng hàng; (b) trượt = `reorder` xoay phải (hoán vị đầy đủ, blank cuộn về đầu); (c) `\link{T.cell[i] <-> P.cell[j]}` nối cột so sánh; (d) caret `i/j` binding qua VariableWatch, rebind sạch qua reorder.
  2. *Manacher center-expand + mirror* — mẫu: `.../scratchpad/td-str/manacher.tex`. Chốt: `range` nở đối xứng (dùng `\recolor` nếu muốn giữ, `\highlight` nếu ephemeral) + caret L/R + `\link` cặp đối xứng và cung gương i↔i' + annotate tâm.
- **Trước khi build hàng loạt, hỏi bài** (Mục 3.4 câu #1 là quan trọng nhất): 7 bài đó là **pattern-shift (KMP/Z)** hay **two-pointer**? Nếu two-pointer thì đã có recipe caret sẵn, khỏi làm gì thêm.
- **Cân nhắc E1 (`shift=k`)** chỉ khi đếm ra nhiều cú nhảy khiến việc viết tay `reorder` thành gánh nặng thật.
- **Đã bác bỏ 1 nghi vấn:** caret hiện "?" sau reorder chỉ là mid-glide, không phải bug — đừng tốn công "sửa".
- **Prior-art cần biết:** `examples/algorithms/string/kmp.tex` là editorial KMP *tĩnh* (không trượt) viết trước reorder. Tier D là bản *có trượt*; có thể coi bản tĩnh là fallback reduced-motion.

**Rủi ro còn lại:** thấp. Rủi ro duy nhất là editorial-dependent (bài dùng thuật toán gì) — không phải rủi ro machinery.

---

## 7. Phụ lục — chỉ mục bằng chứng

| File | Nội dung |
|---|---|
| `.../scratchpad/td-str/kmp_slide.tex` | Probe two-row-slide (5 frame) |
| `.../scratchpad/td-str/kmp_f2.png` | Frame mismatch: 2 hàng thẳng cột, `\link` "so sanh", failure pill |
| `.../scratchpad/td-str/kmp_f3.png` | Frame sau slide: "ABABC" glide slot 0–4 → 2–6 (**bằng chứng cốt lõi**) |
| `.../scratchpad/td-str/kmp_f3_settled.png` | Bác bỏ caret "?": sau settle → i=2, j=0 |
| `.../scratchpad/td-str/manacher.tex` | Probe center-expand + mirror (5 frame) |
| `.../scratchpad/td-str/man_f3.png` | r=3 full palindrome + caret L/R + `\link` cặp đối xứng |
| `.../scratchpad/td-str/man_f4.png` | Mirror i'=2C−i qua `\link` + pill tâm C |
| `examples/algorithms/string/kmp.tex` | Prior-art: editorial KMP tĩnh (3 Array, không trượt) |
| `docs/SCRIBA-TEX-REFERENCE.md` §7.1, §5.11, §5.19 | reorder / binding-caret / link — verb nền của recipe |
| `docs/cookbook/HARD-TO-DISPLAY.md` | Xác nhận KMP/Manacher KHÔNG nằm trong 10 ca "thù địch" |
