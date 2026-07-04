# Docs Author Audit — `docs/SCRIBA-TEX-REFERENCE.md`

**Vai:** tác giả editorial mới, chưa từng thấy scriba, chỉ được phát đúng 1 file `docs/SCRIBA-TEX-REFERENCE.md` (v0.23.1, 2005 dòng).
**Phương pháp:** thực nghiệm — đọc 1 lần như người mới, rồi VIẾT + RENDER thật 4 bài editorial chỉ từ REFERENCE. Không đọc code, không đọc spec khác.
**Chứng cứ:** 4 scenario + 8 probe render thật bằng `.venv/bin/python render.py`. Grade mỗi finding: **Confirmed** (vấp thật / render thật / E-code thật) · Deduced · Hypothesized.

---

## Hand-off Brief (3 câu)

1. **Tổng quát chưa? — Gần đủ nhưng KHÔNG "muốn gì làm nấy":** cả 4 bài (two-pointer Array, BFS Grid, DP 2D, heap sift-down) đều dựng được, nhưng có **2 lỗ hổng im lặng chặn thật** — (a) không loop được recolor một **tập ô 2D tính toán** vì `${list[i]}` trong *selector index* âm thầm biến thành cả list rồi rớt lệnh (E1115), và (b) **binding caret** — đúng tính năng doc quảng cáo cho two-pointer — **không vẽ gì và không cảnh báo gì** nếu set VariableWatch bằng dạng `bulk`.
2. **Gọn chưa? — Chưa:** khoảng **30–40% là maintainer-leak** tác giả không cần (16 ref ruleset `R-/A-/GEP`, 7 nhãn `(since 0.x.y)`, 10 link ra `spec/`, prose cơ chế nội bộ `differ/emitter/byte-for-byte/SA layout`); riêng §5 (621 dòng) + §9 (276 dòng) chiếm 45% doc và phình nhất.
3. **Nghịch lý self-containment:** doc tự nhận *"Read this one file"* (dòng 3) nhưng trỏ ra `spec/` **10 lần** — gồm cả `spec/error-codes.md` mà tác giả THỰC SỰ phải mở khi trúng E-code ngoài 30 cái được liệt kê ở §15.

**Kết:** doc là một *reference tra cứu* tốt (Index-by-task + bảng per-primitive rất mạnh), nhưng chưa phải *authoring guide* an toàn: hai cái bẫy im lặng ở trên khiến người mới render ra kết quả SAI mà tưởng đúng. Vá 2 bẫy đó (thêm ~20 dòng) + cắt leak (bớt ~200 dòng) là được cả tổng quát lẫn gọn.

---

## Method / artifacts (đường dẫn tuyệt đối để chạy lại)

Scratchpad: `/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/7681f32d-4d54-4c44-ae5a-5a3123c0d2b6/scratchpad/`

| File | Bài | Trạng thái render |
|---|---|---|
| `da_a.tex` | (a) Two-pointer two-sum: caret + `\ref` + `\focus` + `\step[title]` + `\invariant` | render sạch 0 warning **sau khi** đổi bulk→targeted watch set |
| `da_b.tex` | (b) BFS flood trên Grid: `block`+`bracket`, `\trace`, `\playeach` sweep, `\invariant` | render sạch **sau khi** bỏ recolor-loop 2D, chuyển sang hand-write |
| `da_c.tex` | (c) Unique-Paths DP 2D: nested-foreach fill, `arrow_from` chuỗi phụ thuộc + traceback, math label | render sạch 0 warning |
| `da_d.tex` | (d) Max-heap extract-max + sift-down: `diagram`(Tree) + `animation`(Array), carets, arrows, simulated swap | render sạch 0 warning |
| `da_probe2/3/4/5.tex` | pin binding-caret bulk-vs-targeted + declare-once | probe |
| `pg_double/range/sel1d/val.tex`, `pdp.tex`, `pg_listiter.tex` | pin quy tắc `${...}` trong index vs value vs iterable | probe |
| `ptree.tex` | Tree node `value=` (undocumented) | probe |

Lệnh render đúng theo §0.1 là **positional** (`render.py file.tex` → ghi `file.html` cạnh nguồn). Cờ `-o` mà team-lead đưa **không có trong doc** và bị renderer từ chối ghi ngoài cwd.

---

## Nhật ký vấp (stumble log) — có trích dẫn

### V1 — [CONFIRMED, HIGH] Binding caret im lặng không vẽ khi set watch bằng `bulk`
- **Tôi viết (theo doc §5.11 dòng 601–605):** `\cursor{a}{id=i, at="w.var[i]", color="state:current"}` và set giá trị con trỏ bằng dạng bulk `\apply{w}{i=0, j=5}` (dạng doc §7.15 dòng 1363 nói là tương đương targeted).
- **Kết quả:** **0 caret** trong output, **0 warning** — full stderr chỉ có dòng `Rendered ...` dù chạy `PYTHONWARNINGS=always` (probe `da_probe4.tex` scene `pb-bulk`: `caret refs = 0`).
- **Minimal pair chứng minh:** cùng cấu trúc, chỉ khác cách set watch → `pb-bulk` (`\apply{w}{i=2}`) = 0 caret; `pt-targeted` (`\apply{w.var[i]}{value=2}`) = caret vẽ + trượt. Cả hai đều **hiện số "2" ở panel watch** (bulk-set vẫn populate panel), nhưng chỉ targeted mới cho caret đọc được.
- **Doc gây hiểu nhầm:**
  - §7.15 dòng 1363: *"targeted `\apply{vars.var[name]}{value=X}`, **or** bulk `\apply{vars}{i=3, j=5}`"* — trình bày 2 dạng như tương đương. **Không tương đương** với binding-caret.
  - §5.11 dòng 610/614: *"the quoted binding re-reads the VariableWatch value each frame"* + *"unresolvable or out-of-range binding … soft-drops … **with an info warning**"*. Thực tế bulk-set không phải out-of-range, nó **im hoàn toàn**, sai với lời hứa "info warning".
  - Ví dụ caret ở §5.11 **không hề nói phải set watch bằng dạng nào** — người mới chọn bulk (tự nhiên hơn cho two-pointer) là trúng bẫy.
- **Workaround (đã Confirmed render sạch trong `da_a.tex`):** luôn set watch cho caret bằng targeted `\apply{w.var[i]}{value=N}`.

### V2 — [CONFIRMED, HIGH] `${list[i]}` trong *selector index* âm thầm biến thành cả list → E1115 rớt lệnh
- **Tôi viết (dựng BFS layer / recolor tập ô tính toán):** `\foreach{i}{0..2} \recolor{a.cell[${idx[i]}]}{state=good}`.
- **Kết quả:** selector thành `a.cell[[1, 3, 5]]` → **E1115 UserWarning "does not match", lệnh bị bỏ**, render vẫn "thành công" (probe `pg_sel1d.tex`). Với Grid 2D y hệt: `g.cell[[0,0,1]][[0,1,0]]` (probe `pg_range.tex`).
- **Đối chứng — dạng value thì CHẠY:** `\apply{a.cell[${i}]}{value=${vals[i]}}` → giá trị 10/20/30 vào đúng ô (probe `pg_val.tex`). Đây đúng là ví dụ duy nhất doc minh hoạ (§5.12 dòng 669–683) — subscript **chỉ ở value position**.
- **Quy tắc thực (doc không nêu):** `${loopvar}` phân giải mọi nơi (selector index *và* value); `${list[expr]}` **chỉ** phân giải ở **value position**, còn trong selector index thì gộp thành cả list rồi rớt.
- **Hệ quả cho generality:** không có cách *loop-driven* nào recolor một **tập ô 2D bất kỳ đã tính toán** (BFS layer chéo, vùng DP). Trong `da_b.tex` tôi buộc phải **hand-write từng `\recolor{g.cell[r][c]}`**.
- **Cái CHẠY (Confirmed, `pdp.tex` + `da_c.tex`):** fill full bảng DP 2D bằng nested-foreach với **loop-var trong selector** + **double-subscript trong value**: `\foreach{i}{0..2}\foreach{j}{0..3} \apply{dp.cell[${i}][${j}]}{value=${dp[i][j]}}` → 6/6 giá trị vào đúng.

### V3 — [CONFIRMED, MED] Foreach iterable dạng subscript `${layers[k]}` → E1173 (abort cả render)
- `\foreach{t}{${layer_idx[1]}}` → **E1173** "cannot resolve iterable '${layer_idx[1]}'", **dừng toàn bộ render** (probe `da_probe_grid.tex`). Iterable phải là range / bare `${list}` / literal.
- **Loud (khác V1/V2 im lặng)** — hint tốt. Nhưng doc §5.12 (dòng 627) liệt kê iterable hợp lệ mà không nói subscript bị cấm; người mới đoán sai. Workaround: bind ra scalar frame-local `\compute{ cur = layer_idx[1] }` rồi `\foreach{t}{${cur}}` (Confirmed chạy).

### V4 — [CONFIRMED, LOW] "declare once" caret TỰ trượt — mâu thuẫn nội bộ trong doc
- Khai báo caret **1 lần** ở step 1, các step sau chỉ đổi watch (targeted) mà **không** re-issue → caret vẫn tự trượt 1→3→5 (probe `da_probe5.tex`, 6 caret refs, 2 slide).
- Doc §5.11 vừa nói *"re-reads i every step and slides"* (tự động) vừa nói *"a later `\cursor` with the same `id` **moves it**"* (thủ công) — mâu thuẫn khiến tôi tưởng phải re-issue mỗi step (viết dư trong `da_a.tex`). Thực tế re-issue là không cần.

### V5 — [CONFIRMED, LOW] Doc tả caret là "▲ glyph" nhưng render ra `<polygon>`
- §5.11 nói *"draws a small `▲` caret glyph"* → tôi grep ký tự `▲` để verify, ra **0** (ký tự `▲` duy nhất nằm trong 1 comment CSS) và suýt kết luận sai là "caret hỏng". Thực tế caret là `<polygon>` dưới `data-annotation="a.cursor[i]-solo"`. Mô tả bằng glyph literal dễ gây nhầm khi verify.

### V6 — [CONFIRMED, MED] Bài "khó" (heap) phải mô phỏng nhiều thứ bề mặt không có
- **Không có Heap primitive** → mô phỏng bằng Array (giá trị) + Tree (cấu trúc). OK nhưng phải tự tính index `2i+1/2i+2`.
- **Không có toán tử swap** → 1 swap = 2 lần `\apply{a.cell[i]}{value=}`; đọc ra như "2 lần ghi đè", reverse-tween không thể hiện "đổi chỗ".
- **Tree không animate được giá trị:** node hiển thị = *id* cố định (§7.5 không có op set value); heap có giá trị di chuyển → Tree chỉ dùng làm **diagram tĩnh**. (Probe `ptree.tex` gợi ý `\apply{h.node[9]}{value=3}` CÓ THỂ đổi nhãn — nhưng **không có trong doc**, xem Open Q3.)
- **Array `remove` không có "logical size":** sau `remove=6`, caret bound tới index 6 vẫn **đậu trên ô rỗng đã xoá** (không soft-drop) — con trỏ không dừng ở biên vùng sống.

### V7 — [DEDUCED, LOW] Vị trí `\playeach` so với `\step` không rõ
- Doc gọi `\playeach` là "step-level frame macro" và desugar thành nhiều `\step`, nhưng ví dụ (dòng 845) đứng một mình. Tôi đặt nó **bên trong** một `\step` (có sẵn recolor + narrate) → render **không lỗi**, sinh 4 frame (`da_b.tex`, 11 frame tổng). Chạy được nhưng doc nên nói rõ nó thay cho một `\step` hay lồng trong step.

### V8 — [CONFIRMED, LOW] Self-containment thủng ở chính chỗ tác giả cần nhất
- Fill DP 2D (V2) — pattern nested-foreach — doc **không show inline**, chỉ trỏ `examples/integration/test_reference_dptable.tex` (dòng 331) mà tác giả chỉ-có-reference **không thấy được**.
- §15 liệt 30 E-code rồi *"Full catalog … `spec/error-codes.md`"* — nhưng tôi trúng **E1173, E1159-path, E1115** khi thử; error là thứ author gặp thường xuyên nhất, đây là chỗ doc nên DÀY hơn chứ không mỏng đi.

---

## Bảng section-by-section: giữ / cắt / chuyển

Trục: **CẦN-CHO-TÁC-GIẢ (giữ)** vs **MAINTAINER-LEAK (chuyển spec/Appendix)**. Dòng = số dòng hiện tại.

| § | Dòng | Đánh giá | Hành động |
|---|---|---|---|
| Contents + **Index by task** | 38 | Rất cần — điều hướng tốt nhất của doc | **GIỮ** |
| §0 How to Render | 16 | Cần | **GIỮ + SỬA**: bỏ ngầm định, ghi rõ output ghi cạnh nguồn; hoặc tài liệu hoá `-o` (hiện `-o` không có, bị từ chối) |
| §1 File Structure | 19 | Cần | GIỮ |
| §2 LaTeX Commands | 127 | Phần lớn cần | GIỮ; **§2.2.2 Legacy Polygon alias** + `$$$` legacy (dòng 129) → nén xuống Appendix "legacy" |
| §3.1–3.2 Animation | ~35 | Cốt lõi | GIỮ |
| **§3.3 Playback (reverse & emphasis)** | ~9 | Doc tự nói *"not something you author — no command turns it on"* (dòng 250) | **CHUYỂN** → 1 dòng "runtime tự lo; xem motion-ruleset" |
| §4 Diagram | 24 | Cần | GIỮ |
| §5 Inner Commands | **621** | Chữ ký/param/ví dụ = cần; **rationale nội bộ = leak** | GIỮ lệnh; **CẮT/CHUYỂN**: Maintainer note §5.8 (dòng 444–447, doc tự dán nhãn), desugaring "byte-for-byte / A-5" của `\playeach` (dòng 848–863), các tag `R-36/38/39/40, A-4, motion-ruleset` rải trong `\cursor/\ref/\focus` |
| §6 Visual States | 20 | Bảng state = cần | GIỮ; **CẮT** con trỏ file CSS `scriba-scene-primitives.css` (dòng 917 — maintainer) |
| §7 Primitives | **445** | Lõi tra cứu — cần nhất | GIỮ; nén các `(since 0.x)` + callout `layout_seed` "advanced" (dòng 1003, 1061–1076) cho gọn |
| §8 Selectors | 92 | Thiết yếu | GIỮ; dọn 2 callout `block`/`state:` chèn giữa bảng (dòng 1395–1413) làm gãy bảng |
| §9 Complete Examples | **276** | Ví dụ tốt nhưng nặng | **TRIM**: Dijkstra full (~130 dòng, 1595–1732) → rút còn ~40 dòng hoặc chuyển `examples/`; giữ Hello/DP/BFS ngắn |
| §10 Env Options | 15 | Cần | GIỮ |
| §11 Annotation Colors | 13 | Cần | GIỮ |
| §12 Common Patterns | 49 | Cookbook hữu ích | GIỮ |
| §13 Gotchas | 116 | 13.1–13.7, 13.9 = vàng cho author | GIỮ phần đó; **CHUYỂN** §13.8 headroom internals (R-32, "scratch buffer", dòng 1904–1909) + phần cơ chế của §13.10 (SA optimizer) sang spec |
| §14 Limits | 21 | Cần | GIỮ |
| §15 Error Codes | 42 | **Cần và nên DÀY hơn** | **MỞ RỘNG**: thêm E1159, E1494/1495, E1322, E1494; bảng này là thứ author mở nhiều nhất |
| Appendix A | 13 | Mô hình ĐÚNG: cách ly đồ nội bộ | GIỮ — và dồn thêm leak ở trên vào đây |

**Marker leak đếm được (bằng chứng cho "chưa gọn"):** `(since 0.x.y)`×7 · `Removed in 0.x`×2 · ruleset `R-/A-/GEP`×16 · link `spec/*.md`×10 (4 file) · "Maintainer"×2 · từ cơ chế nội bộ (differ/emitter/prescan/scene machine/golden corpus/scratch buffer/SA layout/tombstone)×15 · "byte-for-byte/identical"×2 · env debug `SCRIBA_DEBUG_LABELS`/`SCRIBA_LABEL_ENGINE`.

---

## Generality gaps — xếp hạng (thứ tôi MUỐN làm mà bề mặt/doc không cho)

| # | Gap | Mức | Chặn gì | Workaround |
|---|---|---|---|---|
| 1 | **Không loop recolor được tập ô 2D tính toán** — `${list[i]}` trong selector index rớt thầm (E1115) | **HIGH** | BFS layer chéo, tô vùng DP, selection-sort positions | Hand-write từng `\recolor{cell[r][c]}`; hoặc loop bằng `${loopvar}` trực tiếp trên list index 1-D |
| 2 | **Binding caret im lặng no-op khi bulk-set watch** + không warning | **HIGH** | Chính use-case doc quảng cáo: two-pointer / sliding-window | Bắt buộc targeted `\apply{w.var[i]}{value=}` |
| 3 | **Quy tắc `${...}` bất đối xứng không được nêu** (value OK · selector index KHÔNG · iterable ERROR) | **HIGH** | Gốc rễ của #1 và nhiều nhầm lẫn | Thêm 1 box "Computed indexing rules" |
| 4 | **Không có swap op / Heap primitive** | MED | Heap/sort editorial; "đổi chỗ" đọc thành 2 ghi đè | 2× `\apply{cell}{value=}`; mô phỏng heap = Array+Tree |
| 5 | **Tree không animate được giá trị node** (display = id) | MED | Heap/BST có giá trị di chuyển | Tree chỉ làm diagram tĩnh; giá trị để ở Array |
| 6 | **2D DP fill pattern không show inline** (trỏ file ngoài) | MED | Người chỉ-có-reference không dựng được bảng DP tự tin | Show nested-foreach 4 dòng inline |
| 7 | **Array `remove` không có logical-size** → con trỏ đậu ô rỗng | LOW | Heap shrink, queue windows | Tránh trỏ tới ô đã xoá |

Ghi chú tổng quát TÍCH CỰC: 15 primitive + selector algebra + `\compute` Starlark + `arrow_from`/`trace`/`playeach`/`substory`/`focus`/`ref`/`hl`/`invariant` phủ **rất rộng** — array/grid/DP/graph/tree/geometry/plot đều dựng được. "Không muốn gì làm nấy" chỉ vì #1–#3 (indexing) và #4–#5 (thiếu vài primitive), không phải vì thiếu bề rộng.

---

## Đề xuất restructure + ước lượng độ dài

**Hiện tại: 2005 dòng.**

**Cắt (chuyển spec/Appendix, không mất thông tin author):**
- §3.3 playback, §5.8 maintainer note, `\playeach` desugaring internals, §13.8 headroom internals, con trỏ CSS, prose "byte-for-byte/differ/emitter", các tag `R-/A-/GEP` inline → **~ −150 dòng**
- Trim Dijkstra full ở §9 (giữ bản 40 dòng, link phần đầy đủ) → **~ −90 dòng**
- Gom `(since 0.x.y)` thành 1 mục "Version notes" hoặc bỏ → **~ −15 dòng**

**Thêm (vá 2 bẫy im lặng — đây mới là ROI thật):**
- Box **"Computed indexing rules"** (loopvar vs subscript vs iterable; bảng nào-chạy-ở-đâu) → **+12 dòng**
- Sửa ví dụ binding-caret: set watch bằng **targeted** + 1 câu cảnh báo bulk không nuôi caret → **+4 dòng**
- Show nested-foreach fill DP 2D inline → **+5 dòng**
- Mở rộng bảng E-code §15 (+8 code hay gặp) → **+10 dòng**

**Sau: ~1780 dòng, nhưng an toàn hơn hẳn** — ngắn hơn ~11% và (quan trọng hơn) chặn được 2 lỗi silent-wrong-output mà người mới chắc chắn dính. Ròng: conciseness là phụ; **generality/độ tin cậy mới là thắng lớn**.

---

## Open questions (≤5)

1. **Binding-caret bulk-set là bug code hay chủ ý?** Nếu bug → sửa để đọc được cả bulk. Nếu chủ ý → doc phải ghi rõ "caret chỉ đọc watch set bằng `\apply{w.var[i]}{value=}`" và soft-drop phải phát warning (hiện im hoàn toàn, sai §5.11 dòng 614).
2. **`${list[i]}` trong selector index — cấm có chủ đích hay bug?** Dù đằng nào, việc **rớt thầm lặng qua E1115** rất nguy hiểm; có nên nâng thành lỗi loud như iterable (E1173) không?
3. **Tree node có nhận `value=` để đổi nhãn không?** Probe `ptree.tex` gợi ý CÓ (node "9"→"3" ở frame 2), nhưng §7.5 không liệt op này. Nếu có thật → tài liệu hoá (mở khoá heap/BST animation); nếu là no-op → sao không warning?
4. **Dijkstra full example nên nằm inline hay `examples/`?** Quyết định này chi phối mục tiêu độ dài §9.
5. **`\playeach` có hợp lệ khi lồng trong `\step` (kèm recolor/narrate) không, hay phải đứng riêng?** Render được (V7) nhưng ý định không rõ.
