# Tier-D · Tổ-hợp / Lý-thuyết trò-chơi — Grundy·Nim-XOR · Catalan reflection · Burnside ring

> **BMAD investigation.** Không sửa source, không commit. scriba `main @ e185786` (0.24.0),
> venv `.venv/bin/`. Nhiệm vụ: thử dựng 3 chủ đề tổ-hợp bằng **lệnh hiện có**, render thật, phân
> loại RECIPE / MỞ-RỘNG / MÁY-MỚI / CẦN-EDITORIAL. Toàn bộ 7 probe đã **render 0 lỗi + chụp ảnh
> xác minh thị giác** phiên này (`.../scratchpad/td-combi/`).
>
> **Thang bằng chứng:** **[Render]** = đã build + render + screenshot phiên này (mạnh nhất) ·
> **[Source]** = đọc thẳng source/docs · **[Deduced]** = hệ quả logic · **[Hypo]** = đề xuất chưa build.

---

## 1. Hand-off Brief (5 câu)

**Cả 3 chủ đề đều là RECIPE thuần — không cần primitive mới, không cần verb mới, không đụng parser.**
Chìa khoá là `\compute{}` chạy Starlark đủ mạnh để tính **toàn bộ phần toán host-side**: đã xác nhận
bằng render rằng bitwise `^ >> &`, đệ quy (`gcd`), `pow`, và list-comprehension đều chạy — nên mex,
XOR nhiều-đống, phản-chiếu lattice, và tổng Burnside `Σ k^gcd(n,d)` chỉ là vài dòng Starlark rồi bơm
ra DPTable/VariableWatch/Plane2D. Ba "substrate" ánh xạ sạch: **Grundy → DPTable(state→Grundy) +
VariableWatch(mex)**; **Nim-XOR → DPTable 2D (đống×bit + hàng XOR) tô theo parity**; **Catalan →
Plane2D segments (đường + phản chiếu 2 màu + đường chéo)**, với Grid `\trace` là bản đẹp hơn cho
đường Dyck *trong hộp*. Chỉ **Burnside phần "vòng tròn quay"** có nhược điểm thị giác (không phải
blocker): `\compute(gcd,pow)` + VariableWatch đếm ra `orbits=14` chuẩn xác, nhưng **Graph layout
không tạo được vòng đều** (C₆ ra khối méo, cạnh chồng) nên vòng phải vẽ bằng **Plane2D toạ độ tay**,
và phép quay chỉ "trượt dây cung" (`move_point`) chứ không có chuyển-động-cung — đây là điểm
EXTENSION-nice-to-have duy nhất. Phát hiện phụ đáng gắn cờ: **`${list[i+1]}` (subscript số học trong
`\foreach`) im lặng trả về *cả list* rồi crash `TypeError` sâu trong primitive** thay vì báo E-code —
workaround sạch là precompute list endpoint theo từng vòng (chỉ dùng `${list[i]}`).

---

## 2. Bảng phân loại (verdict)

| # | Chủ đề | Verdict | Substrate hiện có | Chi phí thêm | Confidence |
|---|--------|---------|-------------------|--------------|------------|
| 1a | **Grundy / mex** (Sprague-Grundy) | **RECIPE** | DPTable 1D + VariableWatch + `\compute(mex)` | 0 | **Cao** [Render] |
| 1b | **Nim-XOR nhị phân** | **RECIPE** | DPTable 2D (đống×bit) + recolor 2-vòng theo parity | 0 | **Cao** [Render] |
| 2 | **Catalan reflection** | **RECIPE** | Plane2D `add_line`+`add_segment` (2 màu); Grid `\trace` cho đường Dyck | 0 | **Cao** [Render] |
| 3a | **Burnside — đếm quỹ đạo** | **RECIPE** | `\compute(gcd,pow)` + VariableWatch (+ bất kỳ ring nào) | 0 | **Cao** [Render] |
| 3b | **Burnside — vòng tròn + phép quay (hình)** | **RECIPE có nhược** → EXTENSION nhỏ nếu muốn đẹp | Plane2D circle + `move_point` (trượt dây cung) | 0 để dùng; S nếu thêm arc-motion | **Trung bình** [Render] |

> **Kết luận tổng:** không có mục nào cần MÁY-MỚI hay CẦN-EDITORIAL. Nhóm này rẻ nhất trong Tier-D —
> tất cả là **công thức tác giả** (author recipe), giá trị nằm ở việc chốt pattern chuẩn để editorial
> viết, không phải ở code engine.

---

## 3. Mục 1 — Game mex/Grundy + Nim-XOR

### 3.1 Điều được yêu cầu
Sprague-Grundy: mỗi trạng thái = mex của tập Grundy con; Nim = XOR các đống. Cần: bảng
trạng-thái→Grundy, tính mex, XOR các số nhị phân.

### 3.2 Probe đã chạy
- `g1_grundy.tex` — game trừ `{1,2,3}`: DPTable 1D `n=9` + VariableWatch. **[Render]**
- `g2_nim_binary.tex` — 3 đống `1,4,6` trong DPTable 2D `rows=4,cols=4` (3 hàng đống + 1 hàng XOR),
  tô xanh/đỏ theo parity cột. **[Render]**

### 3.3 Bằng chứng
- **Starlark tính toán được toàn bộ** [Render]: `\compute` với `def mex(s): for m in range(len(s)+1): if m not in s: return m`
  cho ra Grundy `[0,1,2,3,0,1,2,3,0]` (đúng chu kỳ `n mod 4`) — đọc thẳng trong HTML. XOR bằng toán
  tử `^` chạy (`3^5^6=0`), và `>>`,`&` cho ra bit từng đống. Docs liệt kê Starlark cho `def/for/đệ
  quy/comprehension` (`SCRIBA-TEX-REFERENCE.md:350-354`); bitwise không bị cấm và đã xác nhận bằng render.
- **DPTable là bảng trạng-thái chuẩn** [Source]: `§7.3` (`:927`) — "fill cells via `\apply{dp.cell[i]}{value=...}`",
  hỗ trợ `labels` index và `\annotate{arrow_from=}` cho mũi tên transition (mex kéo từ các state con).
- **Nim-XOR nhị phân** [Render]: ảnh `shot_g2_nim_binary.png` chuẩn sách giáo khoa — `1=0001,4=0100,6=0110`,
  hàng XOR `0011` tô **xanh cột parity chẵn / đỏ cột parity lẻ**, VariableWatch `xor=3`.
- **Hypercube KHÔNG hợp cho Nim-XOR** [Deduced từ Source]: `§7.16` (`:1375`) — Hypercube là *lattice
  con* (Hasse theo popcount) cho bitmask-DP/SOS/inclusion-exclusion, không phải XOR *kích thước đống*.
  Bảng-bit DPTable 2D mới là đúng công cụ. (Hypercube vẫn hữu ích nếu bài là "XOR/OR trên tập con".)

### 3.4 Recipe chốt
```latex
% Grundy: state -> mex
\shape{dp}{DPTable}{n=9, labels="0..8", label="$G(n)$"}
\shape{vars}{VariableWatch}{names=["n","mex","xor"]}
\compute{
  def mex(s):
      for m in range(len(s)+1):
          if m not in s: return m
      return len(s)
  g = [0]*9
  for n in range(1,9):
      g[n] = mex([g[n-k] for k in [1,2,3] if n-k >= 0])
  x = 0
  for p in [3,5,6]: x = x ^ p
}
\step
\foreach{n}{1..8}
  \apply{dp.cell[${n}]}{value=${g[n]}}
\endforeach
```

### 3.5 Kết luận
**RECIPE. Confidence Cao [Render].** Cả mex-Grundy lẫn Nim-XOR-nhị-phân dựng được ngay, không thêm gì.

---

## 4. Mục 2 — Catalan reflection (phản chiếu đường lattice)

### 4.1 Điều được yêu cầu
Chứng minh Catalan bằng phản chiếu đường đi lưới qua đường chéo: đường lattice + phản chiếu + đường chéo.

### 4.2 Probe đã chạy
- `c1_catalan_plane.tex` — Plane2D: đường chéo `y=x+1` (`add_line`), đường "xấu" (đỏ) chạm chéo,
  và ảnh phản chiếu (xanh) bắt đầu từ `(-1,1)` — dựng bằng `\foreach` + `add_segment`. **[Render]**
- `c2_catalan_grid.tex` — Grid 5×5 + `\trace` vẽ đường Dyck (bậc thang) *trong hộp*. **[Render]**

### 4.3 Bằng chứng
- **Plane2D là substrate đúng cho *phản chiếu*** [Render]: André reflection đẩy ảnh sang toạ độ **âm**
  `(-1,1)`; hộp Grid 0-index không vẽ được, còn Plane2D `xrange=[-1.5,4.5]` vẽ tự nhiên. `add_line`,
  `add_segment`, recolor `p.segment[i]` đều chạy (`§7.9 :1187-1252`). Ảnh `shot_c1_catalan_plane.png`:
  đường chéo + bậc thang + đoạn phản chiếu đỏ ở gốc.
- **Grid `\trace` là bản đẹp hơn cho đường Dyck trong hộp** [Render]: ảnh `shot_c2_catalan_grid.png`
  cho bậc thang sạch, có dot bắt đầu + mũi tên + pill nhãn "Dyck path". `\trace` hỗ trợ Grid/DPTable/
  NumberLine (`§5.9 :520`); **KHÔNG hỗ trợ Plane2D → E1118** (`scene.py:1062`, docs `:525`) — nên trên
  Plane2D bắt buộc dùng `add_segment`, không dùng `\trace`.
- **Nhược thị giác cần workaround editorial** [Render]: hai đường (xấu + phản chiếu) **trùng nhau ở
  đuôi chung** sau điểm chạm đầu tiên (đúng bản chất song ánh: chúng chỉ khác ở tiền tố phản chiếu),
  nên đường xanh vẽ đè lên đỏ. Tác giả nên (a) chỉ vẽ *tiền tố khác nhau* đậm, hoặc (b) nhích một
  đường ~0.08 đơn vị. Đây là tinh chỉnh editorial, **không phải giới hạn công cụ**.

### 4.4 Kết luận
**RECIPE. Confidence Cao [Render].** Plane2D cho phản chiếu (cần toạ độ âm), Grid `\trace` cho đường
Dyck. Editorial nên kết hợp cả hai: `\trace` xây trực giác, Plane2D chứng minh song ánh.

---

## 5. Mục 3 — Burnside ring (bổ đề Burnside)

### 5.1 Điều được yêu cầu
Bổ đề Burnside: vòng phần tử + phép quay/đối xứng, đếm quỹ đạo `|orbits| = (1/|G|) Σ |Fix(g)|`.

### 5.2 Probe đã chạy
- `b1_burnside_graph.tex` — Graph cycle C₆ + VariableWatch(rot,fix,orbits) + `\compute(gcd,pow)`;
  bead chẵn xanh / lẻ đỏ. **[Render]**
- `b2_burnside_reorder.tex` — Array 6 bead, `reorder=[5,0,1,2,3,4]` = quay-1 (bead **trượt** giữ danh tính). **[Render]**
- `b3_burnside_circle.tex` — Plane2D 6 điểm trên đường tròn + `move_point` quay sang khe kế. **[Render]**

### 5.3 Bằng chứng
- **Phần ĐẾM là RECIPE chắc chắn** [Render]: `gcd` đệ quy + `pow` chạy trong Starlark; với `n=6,k=2`
  ra `fix=[64,2,4,8,4,2]`, `orbits = 84//6 = 14` — hiển thị đúng trong VariableWatch
  (`shot_b1_burnside_graph.png`: `rot=2, fix_gcd=4, orbits=14`). Recursion cho phép `gcd` dù `import` bị
  cấm (`§5.2 :350-354`).
- **Vẽ "vòng đều": Graph KHÔNG làm được — phải Plane2D toạ độ tay** [Render]: `layout="stable"` cho C₆
  ra **khối méo, cạnh chồng chéo** (ảnh b1: node 0,1 trên — 5 trái — 2,3,4 dưới, không tròn). `§7.4`
  ghi rõ node **bị ghim vị trí lúc dựng** (`:1004-1009`), không có layout đa-giác-đều. Ngược lại
  `b3` (Plane2D toạ độ tròn tính tay) cho vòng tròn thật (`shot_b3_burnside_circle.png`).
- **Phép quay-là-chuyển-động: 3 cơ chế, đều render, đều có nhược** [Render]:
  | Cơ chế | Chuyển động | Hình dạng | Nhược |
  |--------|-------------|-----------|-------|
  | Graph color-shift (b1) | vị trí đứng yên, **màu** xoay | vòng méo | không có motion "quay" |
  | Array `reorder` (b2) | bead **trượt** giữ danh tính | **dải ngang**, không phải vòng | `§7.1 :906` — 1 lệnh/hoán vị, đẹp nhưng không tròn |
  | Plane2D `move_point` (b3) | bead trượt sang khe kế | vòng tròn thật | trượt **dây cung**, không theo **cung** (`§7.9 :1243`) |
- **Điểm gap thật (chỉ mỹ thuật)** [Deduced]: không có primitive "vòng đa-giác-đều tự-quay theo cung".
  Không chặn được nội dung Burnside (đếm vẫn đúng); chỉ là polish. Xếp EXTENSION-nice-to-have, size **S**.

### 5.4 Recipe chốt (phần đếm, luôn đúng)
```latex
\shape{vars}{VariableWatch}{names=["rot","fix_gcd","orbits"], label="Burnside"}
\compute{
  def gcd(a,b):
      if b == 0: return a
      return gcd(b, a % b)
  n, k = 6, 2
  fix = [pow(k, gcd(n,d)) for d in range(n)]
  total = 0
  for f in fix: total = total + f
  orbits = total // n            % = 14
}
```
Vòng vẽ bằng **Plane2D toạ độ tròn tính tay** (b3) nếu cần hình tròn; hoặc **Array `reorder`** (b2)
nếu chấp nhận dải ngang nhưng muốn chuyển-động-quay đẹp.

### 5.5 Kết luận
**Đếm: RECIPE, Confidence Cao [Render].** **Vòng+quay (hình): RECIPE-có-nhược, Confidence Trung bình
[Render]** — dùng được ngay qua Plane2D, nhưng "vòng đa-giác quay theo cung" là EXTENSION-S nếu
editorial đòi mỹ thuật cao. *Liên quan:* task census #70 ("rotation" gap) — nên đối chiếu verdict.

---

## 6. Phát hiện xuyên suốt (pattern bật RECIPE + 1 bug tiềm ẩn)

1. **[Render] `\compute` Starlark gánh toàn bộ toán tổ-hợp.** Bitwise `^ >> &`, đệ quy (`gcd`,`mex`),
   `pow`, comprehension đều chạy → mex/XOR/reflection/Burnside tính host-side rồi bơm ra shape. Đây là
   lý do cả nhóm rẻ.
2. **[Render/Source] `\recolor{X}{state=...}` — state là enum **literal lúc parse**, KHÔNG data-driven
   được qua `${}`.** `state=${colstate[j]}` bị chặn E1109 (`_grammar_commands.py:145`, `grammar.py:514`).
   *Pattern chuẩn:* precompute list chỉ số theo state, mỗi state một `\foreach` (giống ví dụ `even_indices`
   ở `§5.2`). Đã dùng trong g2 (good_cols/err_cols) và c1.
3. **[Render] BUG tiềm ẩn — `${list[i+1]}` (subscript số học trong `\foreach`) im lặng trả về *cả
   list*.** Docs `§5.12` (`:621-627`) chỉ định nghĩa `${list[i]}` (loop var) và `${list[k]}` (compute
   binding/literal); số học `i+1` không có trong bảng, và ở vị trí value/param nó **không fail-loud** —
   trả nguyên container rồi crash `TypeError: float() argument ... not 'list'` sâu trong
   `plane2d.py:348` thay vì một E-code. *Workaround sạch:* precompute list endpoint theo vòng
   (`bx1,by1,bx2,by2`) để thân loop chỉ đụng `${list[i]}`. **Gắn cờ robustness:** nên nâng thành
   E1159-style fail-loud, nhưng ngoài scope investigation này.
4. **[Render/Source] Double-subscript `${m[i][j]}` chạy ở `value=`** (docs `§5.2 :393`) **nhưng KHÔNG
   trong tuple toạ độ lồng của `add_segment`** — phải làm phẳng thành list 1-D. (Cùng gốc với #3.)

---

## 7. Khuyến nghị

- **Ship 3 recipe này dưới dạng editorial/cookbook, không đụng engine.** Ưu tiên: Grundy+Nim (giá trị
  cao, 0 rủi ro) → Catalan (Plane2D+Grid) → Burnside-đếm.
- **Burnside vòng-quay:** quyết định editorial trước code. Nếu chấp nhận (a) vòng Plane2D tĩnh +
  color-shift, hoặc (b) dải Array `reorder` trượt — thì **0 chi phí**. Chỉ khi đòi "đa-giác đều tự
  quay theo cung" mới cần EXTENSION-S (thêm helper toạ-độ-tròn hoặc arc-tween cho `move_point`).
- **Câu hỏi cho engine owner (không chặn nhóm này):** #3 — có nên biến `${list[i±k]}` số học thành
  fail-loud (E1159) không? Hiện là latent trap crash opaque.

---

## 8. Phụ lục — Probe & tái lập

Thư mục: `/private/tmp/.../scratchpad/td-combi/`. Render:
`SCRIBA_ALLOW_ANY_OUTPUT=1 .venv/bin/python render.py <probe>.tex -o <probe>.html`;
screenshot: `.venv/bin/python shot.py` (Playwright headless, tiến tới frame cuối).

| Probe | Chủ đề | Kết quả render | Screenshot |
|-------|--------|----------------|------------|
| `g1_grundy.tex` | Grundy/mex + XOR | OK, Grundy `[0,1,2,3,0,1,2,3,0]` đúng | `shot_g1_grundy.png` |
| `g2_nim_binary.tex` | Nim-XOR nhị phân | OK, xor=3, parity xanh/đỏ | `shot_g2_nim_binary.png` |
| `c1_catalan_plane.tex` | Catalan reflection (Plane2D) | OK, chéo+2 đường | `shot_c1_catalan_plane.png` |
| `c2_catalan_grid.tex` | Đường Dyck (Grid `\trace`) | OK, bậc thang sạch | `shot_c2_catalan_grid.png` |
| `b1_burnside_graph.tex` | Burnside đếm (Graph) | OK, orbits=14; vòng méo | `shot_b1_burnside_graph.png` |
| `b2_burnside_reorder.tex` | Quay = Array `reorder` | OK, trượt giữ danh tính | `shot_b2_burnside_reorder.png` |
| `b3_burnside_circle.tex` | Vòng tròn + `move_point` | OK, vòng tròn thật | `shot_b3_burnside_circle.png` |

Tất cả 7 probe: **render 0 lỗi, 0 pageerror Playwright.**
