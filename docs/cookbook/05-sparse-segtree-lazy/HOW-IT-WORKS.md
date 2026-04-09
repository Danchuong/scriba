# How `05-sparse-segtree-lazy` works

## Bức tranh tổng thể

Đây là canonical example chứng minh **Starlark `\compute` đủ mạnh để chạy thuật toán đệ quy thật**. Không có layer phụ — author viết sparse segtree bằng Python-ish ngay trong LaTeX, pipeline chạy nó build-time, emit filmstrip SVG.

## Kiến trúc 2 tầng

```
L1 (LaTeX environment)     ← author-facing
     ↓
     \compute { ... }       ← Starlark, runs in sandbox subprocess
     ↓
     trace (list of dicts)  ← shared state
     ↓
     \step / \apply / \recolor / \narrate ← consume trace per frame
     ↓
     emitter → SVG filmstrip
```

## Tầng `\compute` — heavy lifting

Starlark host bật `resolve.AllowRecursion = true` nên 4 hàm đệ quy hợp lệ:

- `get_or_create(lo, hi, parent)` — lazy-allocate node khi access lần đầu, emit `{"type": "allocate"}` checkpoint
- `push_down(lo, hi)` — propagate lazy tag xuống 2 con, emit `{"type": "push_down"}`
- `set_range(lo, hi, ql, qr, v)` — range assign với lazy, emit `{"type": "apply_lazy"}` khi phủ hoàn toàn
- `sum_range(lo, hi, ql, qr)` — query, emit `{"type": "query_result"}`

State = `nodes` dict (key `"[lo,hi]"` → `{sum, lazy}`) + `checkpoints` list. Mỗi lần mutation, append checkpoint. Cuối `\compute`, assign `trace = checkpoints` để L1 tiêu thụ.

**Ràng buộc Starlark chấp nhận được**:

- Không `while` → workaround: `for _ in range(MAX): if cond: break`
- Không `class` → dùng dict với `"type"` tag làm tagged record
- Không `import`, `try/except`, stdlib → không cần cho thuật toán này
- Có `def`, recursion, dict/list mutation, tuple, slice

Deterministic: cùng input ops → cùng trace → cùng HTML (byte-identical cache).

## Tầng L1 — narrate + apply trace

Sau `\compute`, author viết 9 `\step` block, mỗi step:

1. `\shape{st}{Tree}{kind="sparse_segtree"}` — Tree primitive với sparse variant. Emitter biết sinh đủ node slots từ trace lúc build topology.
2. `\recolor{st.node["[l,r]"]}{state=...}` — set state class cho node theo frame (`current`, `idle`, `good`).
3. `\apply{st.node["[l,r]"]}{value=..., label="lazy=..."}` — update sum + badge hiển thị lazy tag.
4. `\annotate{...}{label="push_down", color=warn}` — ephemeral badge chỉ tồn tại frame này.
5. `\narrate{...}` — giải thích bằng prose với inline LaTeX qua `ctx.render_inline_tex`.

## "Allocate" pattern — on-demand node trong filmstrip tĩnh

Thách thức: sparse segtree node tồn tại **động**, nhưng filmstrip là SVG tĩnh. Giải pháp:

1. **Compiler scan trace trước**: xác định tất cả node xuất hiện ở bất kỳ step nào → pre-generate SVG topology chứa HẾT các node đó ngay từ frame 1.
2. **Mỗi frame set opacity per node**: node chưa `allocate` thì `opacity: 0`; khi checkpoint `{"type": "allocate", "node": k}` được tiêu thụ, frame N đổi `opacity: 1` cho node k.
3. **CSS transition** (nếu muốn hiệu ứng pop-in): dùng `@keyframes fade-loop` từ `extensions/keyframe-animation.md`, independent of step navigation.

Đây là trick cốt lõi của zero-JS filmstrip: "dynamic" về mặt semantic nhưng static về mặt DOM. Edge từ parent tương tự — pre-generate rồi toggle opacity.

## Lazy tag display — multi-part label

Mỗi node có label 3 phần: range `[l,r]`, sum value, lazy tag (badge nhỏ). Khi `\apply{node}{label="lazy=3"}`, Tree primitive emit `<g class="scriba-tree-node-lazy-badge">3</g>` cạnh node. Khi `push_down` xảy ra, frame sau lazy badge biến mất ở parent (opacity 0) và xuất hiện ở 2 con (opacity 1).

## Flow step 1 → 9

| Step | Checkpoint tiêu thụ | Visual |
|---|---|---|
| 1 | (prelude) | Chỉ root `[0,7]`, `sum=0`, `lazy=⊥` |
| 2 | `allocate [0,7]` (root, từ `set_range` gọi `get_or_create`) | Root highlight `current` |
| 3 | `allocate [0,3]` + `allocate [4,7]` | 2 con idle, edge từ root |
| 4 | `allocate [2,3]` subtree path | `[0,3]` thành current, recurse |
| 5 | `apply_lazy [2,3] = 3` | Lazy badge "3", sum=6, state=good |
| 6 | Tương tự `[4,5]` bên phải | Mirror |
| 7 | Bubble-up sum updates | Root sum = 12 |
| 8 | `push_down [4,5]` khi op 2 cần xuống | Warning annotate, lazy chảy xuống `[4,4]/[5,5]` |
| 9 | `query_result = 14` | Final root label |

Mỗi frame chỉ chứa **delta** so với frame trước, nhưng trace cho biết full state → emitter rebuild full SVG mỗi frame, sau đó dedup `<defs>` qua `<use>` ref (spec §8.1 nhắc tới technique này).

## Tại sao đây là "stress test" cho `\compute`

HARD-TO-DISPLAY genre bình thường: state fit vài dòng, không cần recursion. Example này **đảo ngược**:

- 4 mutually-recursive functions
- Mutable shared state (`nodes` dict + `checkpoints` list) — dễ race trong ngôn ngữ khác, Starlark single-threaded nên OK
- Độ phức tạp editorial thật (push_down + lazy propagation là error-prone)
- Node set là **dynamic** — editor không biết trước bao nhiêu node

Nếu `\compute` handle được case này, nó đủ dùng cho mọi editorial CP còn lại (DP recurrences, graph algorithms, binary search, v.v.).

## Liên hệ với Pivot #2 spec

Example này cần các feature mà spec Pivot #2 đã lock:

- `Tree` primitive với variant `kind="sparse_segtree"` — base spec §5
- `\apply` với `label=` + dynamic property — base spec §3
- `\annotate` ephemeral badge — base spec §3
- `\recolor` state class — base spec §9.2
- Starlark `\compute` với recursion + step cap 10^8 — base spec §5.2
- Deterministic trace → byte-identical HTML — cache contract

Không cần thêm extension/primitive nào của Pivot #2 (figure-embed, hl, substory, Plane2D, v.v.) — base spec đã đủ cho use case này. Đây cũng là lý do example này được đánh label "canonical": nó demonstrate **base spec** strength, không phải showcase feature mới.
