# error-message-quality — lỗi cú pháp verb mới rơi xuống parser generic (E1012 cryptic)

**Evidence legend**: **Confirmed** = đọc trong code hoặc repro bằng probe; **Deduced** = suy ra từ Confirmed; **Hypothesized** = đề xuất chưa build.

**Status**: Concluded (điều tra — KHÔNG sửa source) · **Confidence: HIGH**
**Base**: `main @ 18443bb` · **Probe**: `scratchpad/bmad-err/probe.py` + `results.json` (24 near-miss, chạy qua `SceneParser().parse()`)

---

## Hand-off Brief (3 câu)

Lỗi cú pháp "gần đúng" trên các verb mới (`\combine`, `\group`, `\apply`) khi tham số trong ngoặc-param là **selector không quote** hoặc **list thiếu ngoặc `[]`** đều bắn ra **E1012 "expected IDENT, got DOT/NUMBER"** — một lỗi token generic không nhắc tên verb, không nói cách sửa — vì bộ đọc param dùng chung `_read_param_brace()` tokenize giá trị và chết ở dấu `.`/số **TRƯỚC KHI** validator riêng của verb (đã có sẵn message tốt) kịp chạy. CA gốc `\combine{...}{into=a.cell[2]}` được xác nhận bắn E1012 (caret đúng chỗ, col 38), trong khi lẽ ra phải là E1497 "into phải quote" — E1497 **đã tồn tại và đã tài liệu hoá đúng quy tắc quote** nhưng không bao giờ nổ. Đây là 1 lớp gồm **3 message cryptic cùng cơ chế** (+ 2 borderline); fix gọn nhất là **1 guard chung trong `_read_param_brace`** (0 churn catalog), và `\cursor` đã cho sẵn khuôn "miễn nhiễm" (đọc param thô bằng `_read_brace_arg`).

---

## 1. CA gốc — xác nhận (Confirmed)

**Input**: `\combine{a.cell[0], a.cell[1]}{into=a.cell[2]}` (quên quote quanh giá trị `into=`).

**Output thật** (probe `combine_into_unquoted`):
```
[E1012] at line 3, col 38: expected IDENT, got DOT
      \combine{a.cell[0], a.cell[1]}{into=a.cell[2]}
                                           ^
  -> https://scriba.ojcloud.dev/errors/E1012
```
Caret ở col 38 = đúng dấu `.` đầu tiên của `.cell[2]`. **Caret đúng chỗ nhưng message không chỉ cách sửa** — khớp mô tả BUG-5.

**Vì sao rơi E1012 thay vì E1497** (Confirmed bằng trace code):
- `_parse_combine` đọc param bằng `_read_param_brace()` tại `scriba/animation/parser/_grammar_commands.py:392`; check `into` hợp lệ nằm **ngay sau đó** ở `:393-403` (E1497).
- Trong `_read_param_brace` (`scriba/animation/parser/_grammar_tokens.py:258-266`): đọc `into` (IDENT) → `=` (EQUALS) → `_parse_param_value()`. Value lexer gặp `a` là IDENT nên **trả về chuỗi `"a"`** (`_grammar_tokens.py:304-310`) và dừng — nó KHÔNG nuốt `.cell[2]`.
- Vòng lặp param quay lại (`:258` `while peek != RBRACE`): token kế là `.` (DOT), không phải COMMA/RBRACE → gọi `key_tok = self._expect(TokenKind.IDENT)` (`:262`) → **E1012 "expected IDENT, got DOT"** ném từ `_expect` (`_grammar_tokens.py:72-79`).
- ⇒ `_read_param_brace()` (dòng 392) chết **trước** khi luồng trả về để combine kịp chạy check `into_raw` (dòng 393). **Validator của verb bị preempt bởi lexer token dùng chung.** (Deduced từ 4 Confirmed trên, được probe xác nhận.)

**Đối chứng (Confirmed)**: `\combine{...}{into="a.cell[2]"}` (có quote) parse OK; `\combine{...}{color=good}` (thiếu into) bắn đúng **E1497** kèm ví dụ. Nghĩa là combine validator tốt — nó chỉ không bao giờ thấy input unquoted.

---

## 2. Cơ chế kiến trúc chung (Confirmed + Deduced)

**Gốc rễ 1 — hai đường đọc param, một fragile một robust:**
- **Fragile**: `_read_param_brace()` tokenize `{key=value,...}` bằng value-lexer. Bất kỳ giá trị nào chứa `.` hoặc `[]` mà **không quote** đều làm vòng lặp gãy ở `_expect(IDENT)` (`_grammar_tokens.py:262`) → **E1012**; giá trị mở đầu bằng token lạ → **E1005** (`_grammar_tokens.py:333`). Verb dùng đường này: **`\combine`** (into=), **`\group`** (id=/nodes=), **`\apply`** (reorder=/insert=/move_line=), và mọi verb param-hoá khác.
- **Robust (khuôn mẫu fix có sẵn)**: **`\cursor`** đọc brace-param thứ 2 bằng `_read_brace_arg()` **thô** (`_grammar_commands.py:625`) rồi tự split `key=value` trên chuỗi và validate bằng E1183. Vì `_read_brace_arg` tái dựng token verbatim, nó **dung nạp `.`/`[]`** → `\cursor{a.cell}{id=i, at=a.var[0]}` (at= unquoted) **parse OK** (probe `cursor_at_unquoted`), dù comment `_grammar_commands.py:377` bảo "into= giống cursor at=". Cursor đã tự miễn nhiễm.

**Gốc rễ 2 — không có lớp catch-generic-trong-ngữ-cảnh-verb**: dispatch verb ở `grammar.py` gọi thẳng `_parse_combine/_parse_group/_parse_apply`; các hàm này gọi `_read_param_brace()` mà **không bọc try/except** để dịch E1012 token-level thành E-code của verb. Không có điểm trung tâm nào biết "đang parse param của verb X" khi E1012 nổ ⇒ hoặc thêm guard tại chỗ chung (`_read_param_brace`), hoặc bọc per-verb. (Confirmed: đọc `_parse_combine` :372-413, `_parse_apply` :103-111, `_parse_group` :464+.)

---

## 3. Khảo sát lớp — 24 near-miss (Confirmed via probe `results.json`)

Phân loại: **CRYPTIC** = E-code generic (E1012/E1010/E1005/E1001), **không** nhắc verb, **không** hint. **GOOD** = E-code có ví dụ/hint và nhắc verb.

| # | Input (rút gọn) | E-code thật | Nhắc verb? | Hint? | Loại |
|---|---|---|---|---|---|
| 1 | `\combine{..}{into=a.cell[2]}` **(SEED)** | **E1012** `expected IDENT, got DOT` | ✗ | ✗ | **CRYPTIC** |
| 2 | `\apply{a}{reorder=3,1,2,0}` (thiếu `[]`) | **E1012** `expected IDENT, got NUMBER` | ✗ | ✗ | **CRYPTIC** |
| 3 | `\group{G}{nodes=[..], id=g.x}` (id dotted) | **E1012** `expected IDENT, got DOT` | ✗ | ✗ | **CRYPTIC** |
| 4 | `\apply{a.cell[}{state=current}` (selector hở) | E1010 `Selector parse error … got EOF` | ✗ | ✗ | borderline (có "selector"+pos, thiếu verb+fix) |
| 5 | `\combine{a.cell[0]}{into="a.cell[1]}` (thiếu `"` đóng) | E1001 `unclosed string` | ✗ | ✗ | borderline (có "string", thiếu verb+fix) |
| 6 | `\combine{..}{color=good}` (thiếu into) | E1497 + ví dụ | ✓ | (ví dụ) | GOOD |
| 7 | `\combine{}{into="..."}` (rỗng sources) | E1497 + ví dụ | ✓ | (ví dụ) | GOOD |
| 8 | `\link{a.cell[0] b.node[1]}` (thiếu mũi tên) | E1497 + ví dụ + echo got | ✓ | (ví dụ) | GOOD |
| 9 | `\link{a.cell[0]}` (1 endpoint) | E1497 + ví dụ | ✓ | (ví dụ) | GOOD |
| 10 | `\link{a<->b<->c}` (3 endpoint) | E1497 + ví dụ | ✓ | (ví dụ) | GOOD |
| 11 | `\link{..}{color=fuchsia}` (enum sai) | E1113 + valid-set | ✗ | (valid-set) | GOOD-ish |
| 12 | `\group{G}{nodes=[..]}` (thiếu id) | E1506 + ví dụ | ✓ | (ví dụ) | GOOD |
| 13 | `\group{G}{id=c1}` (thiếu nodes) | E1506 + ví dụ | ✓ | (ví dụ) | GOOD |
| 14 | `\group{Z}{..}` (shape chưa khai báo) | E1507 | ✓ | ✓ | GOOD |
| 15 | `\group{G}{nodes=["zzz"],id=c1}` (node lạ) | E1507 | ✓ | ✓ | GOOD |
| 16 | `\foreach{i}{..}` thiếu `\endforeach` | E1172 `unclosed \foreach` | ✓ | ✗ | GOOD-ish |

**Parse-OK bất ngờ (không phải lỗi parse-time, validate ở render)**: `nodes=[a,b]` unquoted (idents → string), `move_line=0` (scalar), `cursor at=a.var[0]` unquoted, `foreach{i}{}` iterable rỗng. ⇒ Các case này KHÔNG nằm trong lớp cryptic parse-time.

**Kết tinh**: lớp cryptic parse-time = **các giá trị param là selector-không-quote / list-thiếu-ngoặc đi qua `_read_param_brace`** → **cùng nổ E1012** (rows 1–3). Sources của `\combine`/endpoints của `\link` đọc thô nên **an toàn** (không cần quote) — đó chính là cái bẫy khiến tác giả tưởng `into=` cũng không cần quote.

---

## 4. Xếp hạng tần suất × độ-cryptic (Deduced)

1. **`\combine{..}{into=SEL}` unquoted (SEED)** — **RẤT CAO**. Lý do: tác giả vừa gõ selector unquoted 2 lần (sources của combine + endpoints kiểu link đều unquoted), rồi tự nhiên gõ `into=a.cell[2]` unquoted. Quy tắc "into= phải quote" là **bẫy bất nhất** ngay trong cùng 1 verb. Cryptic tối đa (E1012).
2. **`\apply{..}{reorder=…}` thiếu `[]`** (hoặc list-param khác) — **CAO**. Quên `[]` quanh danh sách là lỗi phổ biến; message "expected IDENT, got NUMBER" hoàn toàn không gợi ý "cần `[...]`".
3. **`\group`/param dotted-unquoted (id=, nodes= thiếu ngoặc)** — **TRUNG BÌNH**. id thường là bare-word nên hiếm có dấu `.`; nhưng `nodes=` thiếu `[]` cùng cơ chế.
4. **selector hở E1010 / thiếu quote đóng E1001** — **THẤP-TB**. Message đã bán-rõ (có "selector"/"string"); thiếu tên verb + gợi ý fix.

---

## 5. Fix direction — nhóm theo cơ chế + chi phí + rủi ro test-pin (Hypothesized; căn cứ Confirmed)

**Rủi ro test-pin = THẤP (Confirmed)**: `grep "expected IDENT" tests/` → **0 hit**; không test/golden nào pin *message text* của E1012 cho input param-selector. Test `_PRODUCTION_RAISED_CODES` (`tests/core/test_strict_mode.py:694`) chỉ là **catalog-parity** (mỗi E-code phải có trong `ERROR_CATALOG` + spec) — nó pin *code*, không pin *message theo input*. Các test đang nhắc E1012 (`tests/unit/test_animation_parser.py:475` "missing LBRACE after \shape", step-label charset, env-option bracket) là **E1012 hợp lệ, đi đường khác** (`_read_brace_arg`/bracket parser, KHÔNG qua vòng `_read_param_brace:262`) ⇒ fix khu trú sẽ không đụng chúng.

**Nhóm A — 1 guard chung trong `_read_param_brace` (KHUYẾN NGHỊ; 1 site, 0 churn catalog):**
Tại `_grammar_tokens.py:262`, khi `_expect(IDENT)` sắp fail mà token gây lỗi là **DOT / LBRACKET** (nối tiếp một value vừa đọc) hoặc **NUMBER/STRING** (list thiếu ngoặc), thay message + thêm `hint`: ví dụ *"giá trị param `<key>=` trông như selector/list chưa quote — hãy quote hoặc bọc `[]`, vd `into=\"a.cell[2]\"`, `reorder=[3,1,2,0]`"*. Giữ nguyên code E1012 (hoặc đổi sang code param-mới) nhưng **message + hint** thì cải thiện được ngay — vì message text KHÔNG bị catalog pin, thêm `hint=` không cần code mới. Phủ **cả 3 CRYPTIC (rows 1–3) + mọi verb param-hoá tương lai** tại 1 chỗ. Message nêu được **tên key** (`_read_param_brace` biết key vừa parse) dù không nêu tên verb — vẫn đủ actionable.

**Nhóm B — tái dùng E-code của verb (bổ sung cho flagship combine; 0 churn catalog):**
Riêng `\combine`: bọc `_read_param_brace()` trong `_parse_combine` (`_grammar_commands.py:392`) bằng try/except, dịch E1012-do-into thành **E1497** — code **đã có trong catalog** (`errors.py:254`) và **đã ghi đúng** "combine needs … a quoted `into=\"...\"`". ⇒ Message flagship khớp tài liệu, chi phí ~5 dòng, 0 code mới.

**KHÔNG khuyến nghị — code mới chuyên biệt (vd E1499)**: tốn 3-4 site (raise + `ERROR_CATALOG` + `_PRODUCTION_RAISED_CODES` + spec markdown qua doc-coverage). Thừa: Nhóm A (hint) + Nhóm B (E1497) đã đủ.

**Chi phí tổng (Hypothesized)**: Nhóm A ~15-30 dòng ở 1 file (`_grammar_tokens.py`) + vài test RED pin message mới; Nhóm B ~5-10 dòng ở `_grammar_commands.py`. Không đụng catalog, không code mới. Rủi ro hồi quy: thấp (guard khu trú vào đúng nhánh value-continuation).

---

## 6. Kết luận + khuyến nghị release

- **CA gốc**: xác nhận — `\combine{..}{into=a.cell[2]}` bắn **E1012 "expected IDENT, got DOT"** (col 38), preempt E1497 do `_read_param_brace()` (`:392`) chết trước check into (`:393`).
- **Số message cryptic đáng nâng**: **3 lõi** (combine into=, apply list thiếu `[]`, group/param dotted — tất cả cùng E1012, cùng cơ chế) **+ 2 borderline** (E1010 selector, E1001 unclosed-string).
- **Gom nhóm fix**: đều 1 gốc ("token-lexer dùng chung nổ trước validator verb") ⇒ **1 guard chung** (`_read_param_brace`) trị cả lớp; tùy chọn tái dùng **E1497** cho message flagship của combine. `\cursor` là khuôn "đọc thô" đã miễn nhiễm nếu muốn refactor sâu hơn (chi phí cao hơn, không cần cho v1).
- **Confidence: HIGH** — repro tất định cả 3 case, throw-site + call-path + lý do preempt đều Confirmed, không test nào pin message cũ.
- **Release**: các verb này (reorder "since 0.24.0"; link/combine/group E1497/E1506/E1507) đang lên **0.24.0** ⇒ **gộp nâng message vào 0.24.0** (ship error tốt ngay từ ngày đầu dùng verb mới; thay đổi nhỏ, self-contained trong parser, rủi ro pin ~0). Không cần patch riêng.

**Reference (path:line)**
- Throw E1012: `scriba/animation/parser/_grammar_tokens.py:72-79` (trong `_expect`); site fail: `:262` (`key_tok = self._expect(IDENT)`).
- Value lexer trả IDENT sớm: `_grammar_tokens.py:304-310`; E1005 unexpected-token: `:333`.
- Combine: `_grammar_commands.py:392` (`_read_param_brace()`), `:393-403` (check into, E1497), E1497 sites `:355/:387/:399`.
- Cursor robust (khuôn): `_grammar_commands.py:625` (`_read_brace_arg`), validate at= E1183 `:709/:746`.
- Catalog: `scriba/animation/errors.py:130` (E1012), `:254` (E1497), `:263` (E1506), `:266` (E1507).
- Test-pin: `tests/core/test_strict_mode.py:694` (`_PRODUCTION_RAISED_CODES` — catalog-parity); `tests/unit/test_animation_parser.py:475` (E1012 hợp lệ, đường khác).
- Probe: `scratchpad/bmad-err/probe.py`, `scratchpad/bmad-err/results.json`.
