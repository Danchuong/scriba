# Gap B1 — DSU / Forest / Contraction: rừng đa-gốc, hợp cây, và co cụm thành super-node

> Điều tra thiết kế (BMAD). **Không sửa source repo.** Cây @ `main`, scriba `0.23.1`
> (`scriba/_version.py:3`), `SCRIBA_VERSION = 17` (`scriba/_version.py:6`). Driver:
> JudgeZone pass 3 — B1 là gap đơn lẻ lớn nhất (~40+ bài). Companion: `investigations/
> feat-grid-block-selector.md` (cùng driver JudgeZone), `investigations/anim-unified-motion-model.md`
> (A-rules motion — teammate gap-motion-identity), RFC-001 `docs/rfc/001-tree-graph-mutation.md`.
>
> Thang bằng chứng: **[Confirmed]** = đọc trực tiếp trong source phiên này · **[Deduced]** =
> hệ quả logic của fact đã confirm · **[Hypothesized]** = đề xuất thiết kế, chưa build/verify.

---

## 1. Hand-off Brief (4 câu)

Cả 40+ bài của B1 quy về **một** nhu cầu chung — "cho thấy các phần tử nào đang cùng một
thành phần, và thành phần đó lớn dần / nhập vào nhau" — nhưng nhu cầu đó **tách thành ba
hình dạng khác nhau** mà không một primitive hiện có nào phủ trọn: (a) *hợp cây trên rừng
đa-gốc* (DSU thuần, path compression) cần layout nhiều gốc mà Tree single-root
(`tree.py:160`) không có; (b) *tô cụm trên đồ thị nền cố định* (Kruskal / SCC-detect /
block / 2-SAT) cần vẽ bao quanh một tập node **mà không đổi node-set** — Graph cố tình khoá
node-set (`graph.py:1038-1043` "the node set never changes for a Graph"); (c) *co cụm thành
super-node* (condensation DAG) cần thu nhỏ node-set — thứ RFC-001 đã **chủ đích hoãn** sang
v0.7 (`docs/rfc/001-tree-graph-mutation.md:28`, §7). Phán quyết: **KHÔNG** thêm `add_node`/
`contract` vào Graph (phá invariant có chủ đích + phá A1-pinning + R-32); thay vào đó một
**giải pháp lai 3-phase, dẫn đầu bằng overlay-group presentation** — Phase 1 `\group`
(decoration tô-cụm, rẻ nhất, phủ Kruskal/SCC/block/2-SAT, **độc lập motion**), Phase 2
`Forest` primitive (nhà sạch cho 27 bài DSU, thay cho hack virtual-root đang ship), Phase 3
contraction-như-shape-thứ-hai (không co in-place). B3 (trie/automaton) là **Tree mở rộng**
(Tree đã có node-growth `tree.py:294`; chỉ thiếu edge-label + link-class thứ hai), **không**
phải primitive mới.

---

## 2. Problem — 40+ bài cần gì, chia theo hình dạng

Phân rã B1 (con số theo brief team-lead) và ánh xạ **cần gì**:

| Nhóm | ~Bài | Thao tác lõi | Cần visual gì | Primitive tự nhiên |
|---|---|---|---|---|
| **DSU / union-find thuần** | 27 | `union(a,b)` = gộp 2 set; `find(x)` + path compression = reparent | Rừng con-trỏ-cha đa-gốc; nén đường = node nhảy thẳng lên root | **Forest** (đa-gốc) |
| **Kruskal MST** | ~4 | union **trên đồ thị trọng số nền**; DSU là phụ trợ | Tô cụm lớn dần trên **graph gốc cố định** (accept→merge, reject→cycle) | **Overlay-group** trên Graph |
| **SCC condensation** (Tarjan/Kosaraju) | 7 | tìm SCC → **co** mỗi SCC thành 1 super-node → DAG condensation | (i) tô SCC trên graph nền; (ii) DAG super-node | Overlay-group + shape-thứ-hai |
| **Block-cut tree** | 6 | tìm biconnected component (block) + khớp nối → cây block ⇄ cut-vertex | (i) tô block trên nền; (ii) cây lưỡng-phân block/cut | Overlay-group + Tree/Graph |
| **2-SAT** | ~few | implication graph → SCC → check x, ¬x khác SCC | Tô SCC trên implication graph | Overlay-group trên Graph |

**Quan sát then chốt [Deduced]:** "union" (rừng, cây nhập nhau) và "contraction" (đồ thị co
cụm) **là 2 nhu cầu khác nhau** đúng như team-lead nghi ngờ — và chúng ánh xạ sang **2 phase
khác nhau**. Chỉ 27 bài DSU thuần thực sự cần một cấu trúc **rừng đa-gốc**. 17+ bài còn lại
(Kruskal/SCC/block/2-SAT) chạy **trên một đồ thị nền cố định** và chỉ cần *nhìn thấy cụm* —
đó là bài toán **presentation**, không phải bài toán mutate-cấu-trúc.

---

## 3. Evidence (Confirmed, path:line)

### 3.1 Graph: node-set cố định là invariant CÓ CHỦ ĐÍCH

- **[Confirmed]** Node-set chốt lúc dựng: `graph.py:667` `self.nodes = list(params.get("nodes", []))`;
  không có đường mutate. `apply_command` chỉ nhận `add_edge`/`remove_edge`/`set_weight`
  (`graph.py:956-1008`) — **không** `add_node`/`remove_node`.
- **[Confirmed]** Comment A1-pinning tại `graph.py:1038-1043`: *"the node set never changes for
  a Graph (no add_node/remove_node), so an edge mutation must NOT move any node — nodes keep
  their construction-time coordinates … This keeps multi-step edge mutations visually stable
  instead of re-solving the whole layout each frame."* Dẫn `docs/plans/graph-position-pinning-analysis-2026-06-03.md`.
- **[Confirmed]** Cache addressable dựa trên bất-biến này: `graph.py:1103-1108` *"Graph topology
  is fixed at construction — no mutation path exists — so the cache is valid for the lifetime
  of the primitive."*
- **[Confirmed]** RFC-001 hoãn có chủ đích: `docs/rfc/001-tree-graph-mutation.md:28` *"Graph node
  mutation (add_node/remove_node on Graph) — deferred to v0.7 … nodes are fixed at layout time,
  edges alone are tractable"*; bảng §7 lặp lại (`:277`).
- **[Confirmed]** Edge ép float: `graph.py:695` `parsed_edges.append((e[0], e[1], float(e[2])))`
  → cạnh nhãn-ký-tự (trie) sẽ throw. (Chốt cho B3.)

**→ Kết luận [Deduced]:** thêm `add_node`/`contract` vào Graph là **đâm thẳng vào một invariant
được ba lớp code + một RFC bảo vệ**. Co-cụm in-place phá A1-pinning (node-set đổi ⇒ phải
re-solve layout ⇒ mọi node nhảy) và phá R-32 (bbox reflow).

### 3.2 Tree: single-root, reparent = cơ chế "union" đã có, nhưng edge-model quá mỏng

- **[Confirmed]** Đúng một gốc: `tree.py:160` `self.root: str | int = str(root)`; layout lấy
  đúng một root: `tree.py:135-140` `_reingold_tilford(self.root, self.children_map, …)`.
  Rừng N cây rời **không** biểu diễn native được — Reingold-Tilford cần một apex.
- **[Confirmed]** `reparent` **đã ship** (RFC-001 W6.1): `tree.py:411-476` `_reparent_internal`
  — dời một subtree sang cha mới, có cycle-check (`_is_ancestor`, `tree.py:398-409`), rồi
  `_relayout()` (deterministic Reingold-Tilford mỗi mutation, `tree.py:275-285`). Đây **chính
  là** phép "hợp hai cây" ở mức con-trỏ.
- **[Confirmed]** `add_node` grow-only đã có: `tree.py:294-320` — nối leaf mới vào cha. (Chốt cho B3: trie grow chạy.)
- **[Confirmed]** Edge-model = 2-tuple trần `(parent, child)`, **không nhãn, không trọng số,
  không link-class thứ hai**: `tree.py:163-165` `[(str(e[0]), str(e[1])) for e in raw_edges]`;
  `children_map` chỉ giữ quan hệ cha→con (`tree.py:108-113`). Không có chỗ cho char-label
  (trie) hay fail/suffix-link (Aho-Corasick / suffix-automaton).
- **[Confirmed]** Hidden node/edge bị skip khi emit: `tree.py:678-685` (edge chạm hidden bị bỏ),
  `tree.py:713-715` (node hidden bị bỏ) — **nhưng** vẫn chiếm bbox (RFC-001 §4.4
  `:244` *"hidden elements still contribute to the primitive's bounding box"*).

### 3.3 Workaround đang ship — bằng chứng gap sống

- **[Confirmed]** `examples/algorithms/graph/union_find_tree.tex` — **rừng-DSU chạy HÔM NAY**
  bằng **virtual-root Tree**: khai báo `root="R"` với 7 cạnh `(R,A)…(R,G)`, rồi
  `\recolor{T.node[R]}{state=hidden}`. `union(A,B)` = `\apply{T}{reparent={node="B",parent="A"}}`
  (cạnh `(R,B)` biến mất vì B không còn là con của R). Path compression = reparent D từ C lên A.
  **⇒ Capability DSU đã có, không bị chặn.** Nhược điểm: R ẩn nhưng vẫn chiếm bbox (§3.2) → có
  một apex-ma cố định trên đỉnh; mọi cây treo dưới một điểm vô hình.
- **[Confirmed]** `examples/algorithms/graph/union_find.tex` — biến thể con-trỏ-cha trên Graph:
  `directed=true, edges=[]`, rồi `add_edge`(child→parent). Nén đường = `remove_edge`+`add_edge`.
  Chạy, truthful, nhưng "cụm" chỉ đọc được qua mũi tên (force-layout), không có bao cụm.
- **[Confirmed]** `examples/algorithms/graph/kruskal_mst.tex` — **đây là gap rõ nhất**: đồ thị
  trọng số 6-node/9-cạnh `layout="stable"`, nhưng **DSU component chỉ tồn tại trong narration
  text** (`\narrate{… Union → {A,B,C} …}`) + một Array `picked[]` phụ. Không có bao cụm trực
  quan nào — người xem **không thấy** node nào cùng set trừ khi đọc chữ. Đây là chỗ overlay-group
  đem lại giá trị lớn nhất.

### 3.4 Bài học ổn định layout — envelope đơn điệu (R-42 / LinkedList)

- **[Confirmed]** `_envelope_n` = MAX số node từng đạt, đơn điệu không co: `linkedlist.py:123-129`
  *"bbox width follows the MAX node count ever reached, never the live count — a mid-timeline
  insert/remove must not shift the whole structure horizontally"*; grow ở `linkedlist.py:174`;
  bbox dùng max ở `linkedlist.py:243`.
- **[Confirmed]** `_structural_prescan = True` (`linkedlist.py:87`) — replay các apply insert/remove
  lúc build-time để `_envelope_n` chạm max trước khi frame đầu được đo (A-6, `motion-ruleset.md:152-170`).
- **[Confirmed]** R-42 (Array sentinels) là prior-art chuẩn nhất: bbox nới thêm hằng số
  `2·(cw+gap)` **mọi frame bất kể live** ⇒ *"envelope is frame-invariant and R-32 centering
  holds by construction"* (`smart-label-ruleset.md:661-693`). Slot addressable **từ t0**.
- **[Confirmed]** Array slot-identity reflow: `array.py:206-222` — insert/remove dịch slot nhưng
  **vị trí cố định** ⇒ differ phát `value_change` cascade, *"no new motion kind, no JS"*, R-32
  giữ nguyên; grid không grow quá `size` khai báo (E1403).

**→ [Deduced]:** bất kỳ cấu trúc grow/reflow nào (Forest hợp cây) **phải** đặt trước envelope-max
(prescan replay các union) để bbox bất-biến theo frame, đúng công thức R-42/LinkedList.

### 3.5 Motion substrate — cái gì miễn phí, cái gì cần teammate

- **[Confirmed]** Registry kind **đóng, có nghịch đảo**: `motion-ruleset.md:59-80` (A-2) —
  `annotation_add/remove/recolor`, `element_add/remove`, `position_move`, `value_change`, …
  Feature mới *"ship only as the triple {emit, JS handler, inverse}"*; **"a new data structure
  should need zero new motion vocabulary"** (`motion-ruleset.md:232`).
- **[Confirmed]** Identity = key trên `data-annotation`/`data-target` (A-0.ii,
  `motion-ruleset.md:30`). Annotation emit qua `data-annotation="{key}"` (`base.py:600,672`).
- **[Confirmed]** A-6: insert/reflow/grow phải qua prescan + mang `fs=1` để runtime snap về SVG
  server (`motion-ruleset.md:152-170`).
- **[Confirmed]** Companion investigation của teammate motion nói rõ *"two new primitives (⑧⑨)
  are pure scene-build additions that emit only existing kinds"* (`anim-unified-motion-model.md:§1`)
  — tức primitive mới **không** cần code runtime mới nếu chỉ phát kind cũ.

### 3.6 Helper tái dùng được (giảm cost)

- **[Confirmed]** `plane2d_compute.py:52` `hull(points) -> list[Point2D]` — Andrew monotone chain,
  sẵn sàng dựng bao lồi quanh cụm.
- **[Confirmed]** R-35 bracket-glyph (`base.py:1186-1208`): *"no-fill dashed rounded outline"* —
  `<rect rx=6 fill=none stroke-opacity=0.55 stroke-dasharray="4,3">` phát trong **group
  annotation riêng** `data-annotation="{target}-block-bracket"`, gate bởi `bracket=true` +
  `.block[`. Đây là **đúng cỗ máy** để tô bao cụm: chỉ đổi hình chữ-nhật→hull và key→`group[id]`.
- **[Confirmed]** Warm-start layout đã có: `graph_layout_stable.py:151-181`
  `compute_stable_layout(initial_positions=…)`, cap 20 node / 50 frame (`:31-32`).

---

## 4. Hypotheses (có status)

| # | Giả thuyết | Status |
|---|---|---|
| H1 | Graph node-set cố định là chủ đích (layout stability), không phải thiếu sót | **[Confirmed]** §3.1 (3 lớp code + RFC-001) |
| H2 | Contraction phá stability; overlay-group **không** (node-set nguyên vẹn) | **[Confirmed→Deduced]** §3.1 + §3.6 (annotation không vào layout) |
| H3 | Union (rừng) và Contraction (đồ thị co) là 2 nhu cầu khác nhau | **[Confirmed]** §2 — ánh xạ 2 phase khác nhau |
| H4 | DSU capability **đã** chạy hôm nay (virtual-root Tree) ⇒ Forest là ergonomics, không unlock | **[Confirmed]** §3.3 `union_find_tree.tex` |
| H5 | Overlay-group phủ được nhu cầu visual của Kruskal/SCC/block/2-SAT | **[Deduced]** §2 + §3.3 (gap kruskal là "cụm narration-only") |
| H6 | Forest reflow cần envelope đơn điệu + prescan (bài học R-42) | **[Deduced]** §3.4 |
| H7 | B3 = Tree mở rộng (edge-label + link-class), không cần Automaton primitive | **[Confirmed→Hypothesized]** §3.2 (Tree đã có growth; chỉ thiếu 2 thứ additive) |
| H8 | Overlay-group emit **chỉ kind cũ** (annotation_*) ⇒ không bump SCRIBA_VERSION | **[Deduced]** §3.5 (A-2 closed registry) |
| H9 | Forest **union animation** cần element-identity motion — chờ gap-motion-identity | **[Hypothesized]** §7 dependency |

---

## 5. So sánh phương án cho B1 (≥3)

Chấm trên 5 trục: **Coverage** (phủ bao nhiêu trong 40+), **Stability** (A1/R-32), **Motion**
(phụ thuộc teammate?), **Cost**, **API surface**.

| Phương án | Coverage | Stability | Motion | Cost | API surface |
|---|---|---|---|---|---|
| **A. Forest primitive ĐƠN LẺ** | 27 DSU; **trượt** Kruskal/SCC/block (chúng ở trên graph nền, không phải rừng) | Tốt nếu prescan-envelope (§3.4); layout riêng | **Phụ thuộc** motion cho union-glide | **M** | primitive mới `Forest` + union/find sugar |
| **B. Graph node-ops (`add_node`/`contract`)** | Về lý thuyết phủ SCC/contraction | **PHÁ** A1-pinning + R-32 + RFC-001 §2 (đổi node-set ⇒ re-solve ⇒ mọi node nhảy) | Nặng (element_add/remove + relayout mỗi frame) | **L** + rủi ro cao | phá vỡ invariant 3-lớp; **REJECT** |
| **C. Overlay-group presentation ĐƠN LẺ** | Kruskal/SCC-detect/block/2-SAT (~17); **thiếu** path-compression rừng của DSU thuần | **Xuất sắc** — node-set nguyên vẹn, annotation không vào layout, A1/R-32 giữ | **Độc lập** (annotation_* kind cũ, A-2) | **S–M** | 1 decoration `\group` + reuse R-35 |
| **D. LAI: C (Ph1) + A (Ph2) + shape-thứ-hai (Ph3)** ⭐ | **Toàn bộ 40+** | Xuất sắc (mỗi phase giữ invariant tương ứng) | Ph1 độc lập; chỉ Ph2 chờ motion | **S→M→M** phân kỳ | `\group` + `Forest` + `\contract` sugar |

**Vì sao D thắng [Deduced]:** không phương án đơn lẻ nào phủ cả 3 hình dạng ở §2. Overlay
(C) rẻ và phủ rộng nhu cầu *"thấy cụm"* nhưng không kể được câu chuyện con-trỏ-cha (path
compression) — thứ 27 bài DSU dạy. Forest (A) kể sạch câu chuyện đó nhưng vô dụng cho Kruskal
(cụm nằm trên đồ thị trọng số, không phải rừng). B phá invariant, loại. Lai D cho **mỗi hình
dạng đúng nhà của nó**, và quan trọng: **xếp phase theo cost tăng dần + coverage/frame-per-cost
giảm dần**, nên có thể dừng sau Ph1 vẫn thắng lớn.

---

## 6. Thiết kế — giải pháp lai 3-phase

### Phase 1 — `\group`: decoration tô-cụm (cost **S–M**) — LÀM TRƯỚC

Decoration presentation-only vẽ bao quanh một **tập node đã đặt tên** trên Graph/Tree, tô nhẹ
nội thất, tùy chọn dim cạnh xuyên biên. **Node-set không đổi** ⇒ A1-pinning (`graph.py:1038`)
giữ, R-32 giữ, **zero relayout**.

**API [Hypothesized]:**
```latex
\group{G}{id="c1", nodes=["A","B","C"], style=hull, state=good, label="comp 1"}
\apply{G.group[c1]}{add_node="D"}          % Kruskal: cụm lớn dần
\apply{G.group[c1]}{merge="c2"}            % union: gộp c2 vào c1 (c2 biến mất)
\recolor{G.group[c1]}{state=done}
```

**Spec-diff:**
- `graph.py` / `tree.py`: thêm `resolve_group_hull(node_ids) -> list[Point2D]` gọi
  `plane2d_compute.hull` trên `self.positions` (inflate `node_radius + pad`). Fallback style
  `bbox` (rounded-rect) cho ≤2 node (hull suy biến, §`plane2d_compute.py:60`).
- `base.py`: mở rộng nhánh R-35 bracket-glyph (`base.py:1186`) — hiện gate `.block[`; thêm
  gate `.group[` phát `<polygon>` (hull) thay `<rect>`, cùng thẩm mỹ dashed
  (`stroke-opacity=0.55, dasharray="4,3"`), key `data-annotation="{shape}.group[{id}]"`.
- **Motion:** ride `annotation_add` / `annotation_recolor` / `annotation_remove` (A-2 closed
  registry). `merge` = `annotation_remove(c2)` + `annotation_recolor(c1)` với hull tính lại từ
  node-set mới của c1. **KHÔNG kind mới, KHÔNG bump SCRIBA_VERSION** (`motion-ruleset.md:245`).
- **bbox:** group là annotation ⇒ tối đa là SHOULD-obstacle của scorer, **không** đổi content
  bbox ⇒ byte-stable khi vắng mặt (mẫu opt-in như R-42).

**Phủ:** Kruskal (đúng gap `kruskal_mst.tex`), SCC-detect, block-detect, 2-SAT-SCC. ~17 bài
nhận **nhu cầu visual chính**. Ship được **ngay, không chờ teammate motion**.

### Phase 2 — `Forest`: primitive rừng đa-gốc (cost **M**)

Nhà sạch cho 27 bài DSU + dạy path-compression. **Thay** hack virtual-root (`union_find_tree.tex`)
vốn để lại apex-ma (§3.2).

**Tiểu-phương án đã cân [Deduced]:**
- **2a (KHUYẾN NGHỊ):** `Forest` = N cây Reingold-Tilford đóng gói ngang. Tái dùng
  `_reingold_tilford` per-cây (đã deterministic, `tree.py:275-285`) + packing ngang +
  envelope-max đơn điệu (`_envelope_n` mẫu `linkedlist.py:129`) + `_structural_prescan=True`
  (`linkedlist.py:87`) replay union lúc build ⇒ bbox bất-biến (R-42). `union(a,b)` = gắn root
  này dưới root kia (đúng semantics `reparent`, `tree.py:411`). `find` path = recolor.
- **2b:** chỉ "bless" virtual-root pattern thành first-class + sửa cosmetics apex-ma bằng
  `strict_hidden` (RFC-001 §7 `:281` đã liệt kê defer). Rẻ hơn (S) nhưng vẫn là một-cây, khó mở
  rộng union-by-rank/size hiển thị. Dùng nếu Ph2 bị bóp cost.

**API [Hypothesized]:**
```latex
\shape{F}{Forest}{nodes=["A".."G"]}        % 7 cây đơn, mỗi node tự là root
\apply{F}{union={a="B", b="A"}}            % desugar → attach root(B) dưới root(A)
\apply{F}{reparent={node="D", parent="A"}} % path compression (đã có ở Tree)
```

**Spec-diff:** primitive mới `Forest(PrimitiveBase)`, `_structural_prescan=True`, `roots: list`,
`_relayout()` = pack N `_reingold_tilford` + envelope-max width; `apply_command` nhận `union`
(sugar) + `reparent`/`add_node` (mượn thẳng logic Tree). **Emit chỉ kind cũ** (`position_move`
cho subtree glide + `fs=1`, `element_add` cho node mới) ⇒ **không** bump version.

### Phase 3 — Contraction như shape-thứ-hai (cost **M–L**, ưu tiên thấp nhất)

Cho SCC-condensation / block-cut **DAG kết quả**: tác giả khai báo **Graph thứ hai** (đồ thị
condensation), + sugar `\contract` map group→nhãn super-node để narration cross-ref. **Co
in-place node-set giữ nguyên trạng thái DEFERRED** (khớp RFC-001 §2/§7).

**API [Hypothesized]:**
```latex
\contract{G}{group=c1, into="scc1", to="H"}   % ghi chú: cụm c1 của G ↔ node scc1 của H
\shape{H}{Graph}{nodes=["scc1","scc2","scc3"], edges=[...], directed=true}  % DAG condensation
```
Không đụng layout G (chỉ metadata cross-ref + có thể một mũi tên annotation G→H). ~7 SCC + 6
block-cut, vốn đã được Ph1 (overlay) + một Graph khai-tay phủ phần lớn ⇒ Ph3 là polish.

---

## 7. B3 — trie / Aho-Corasick / suffix-automaton: **Tree mở rộng, KHÔNG primitive mới**

**Verdict [Confirmed→Hypothesized]:** Tree đã có 2/3 thứ B3 cần:
1. **Node growth** — `_add_node_internal` (`tree.py:294`) đã chạy; trie là cây grow-only.
2. **Single-root** — trie/automaton đúng một gốc (khớp `tree.py:160`).

Tree **thiếu** đúng 2 thứ, cả hai **additive** (không phá golden):
- **Edge-label (char trên cạnh):** edges hiện là 2-tuple trần (`tree.py:163`). Thêm
  `edge_labels: dict[(u,v), str]` + render nhãn ở trung điểm cạnh. Không đụng layout.
- **Link-class thứ hai (fail/suffix link):** `children_map` chỉ có cha-con (`tree.py:108`).
  Thêm một **lớp cạnh phụ** `links=[(u,v,"fail")]` **loại khỏi** Reingold-Tilford (fail-link
  không định hình layout, chỉ vẽ chồng — thường cung cong đứt nét). Đây là lớp overlay giống
  hệt cách annotation-arrow đã vẽ chồng lên cây (`tree.py:762-773`).

**⇒ B3 = Tree + `edge_labels` + `links` (secondary edge layer).** Chung gốc-rễ với B1: "Tree
edge-model quá mỏng". Cost **M**, tách khỏi B1 nhưng nên gộp lịch vì cùng chạm `tree.py` edge
path. **KHÔNG** dựng `Automaton` primitive (Graph ép float-weight `graph.py:695` mới là thứ
chặn char-edge trên Graph; Tree không có rào đó).

---

## 8. Dependencies — chờ gì từ gap-motion-identity

> Teammate `gap-motion-identity` phân xử A-rules / element-identity motion
> (`investigations/anim-unified-motion-model.md`). **Không tự quyết motion ở đây; chỉ nêu yêu cầu.**

- **Ph1 `\group`: KHÔNG phụ thuộc.** Emit `annotation_add/recolor/remove` — kind đã đóng-nghịch-đảo
  (A-2, `motion-ruleset.md:59-80`). Ship độc lập.
- **Ph2 `Forest` union-glide: PHỤ THUỘC.** Khi `union` reparent một subtree, subtree cần **giữ
  identity** (A-0.ii, cùng `data-target` qua các frame) và **glide** dưới envelope đã đặt trước
  (A-6). **Yêu cầu gửi teammate:** (i) một subtree (nhiều node đổi cha, di chuyển đội hình) là
  **một** motion hay **N** `position_move`? (ii) element-identity có bảo toàn khi node đổi parent
  không? (iii) xác nhận `position_move` + `fs=1` snap đủ cho subtree-move, không cần kind mới.
  **Render tĩnh của Forest chạy được không cần câu trả lời**; chỉ *animation của phép hợp* mới chờ.
- **Ph3:** chỉ metadata/annotation cross-ref ⇒ không phụ thuộc.

---

## 9. Cost tổng hợp & thứ tự

| Phase | Deliverable | Cost | Phủ thêm | Motion dep | Version bump |
|---|---|---|---|---|---|
| **1** ⭐ | `\group` overlay decoration | **S–M** | ~17 (Kruskal/SCC/block/2-SAT) | Không | Không |
| **2** | `Forest` primitive (2a) | **M** | 27 DSU (sạch, thay hack) | **Có** (union-glide) | Không |
| **3** | `\contract` + shape-thứ-hai | **M–L** | polish 13 (SCC/block DAG) | Không | Không |
| **B3** | Tree `edge_labels` + `links` | **M** | ~12 (trie/AC/SAM) | Không | Không (additive) |

**Khuyến nghị lịch:** Ph1 trước (rẻ nhất, phủ rộng nhất, độc lập motion) → B3 (song song, cùng
chạm tree.py edge path) → Ph2 (khi gap-motion-identity chốt union-glide) → Ph3 (khi cần DAG
condensation đầy đủ). Có thể **dừng sau Ph1+B3** vẫn giải quyết phần lớn JudgeZone pass 3.

---

## 10. Confidence

- **CAO** trên chẩn đoán gap và ánh xạ 3-hình-dạng (§2): mọi khẳng định trọng yếu là [Confirmed]
  đọc trực tiếp source + 3 example đang ship chứng minh cả cái chạy lẫn cái thiếu (§3.3).
- **CAO** rằng overlay-group giữ A1/R-32 và không cần kind mới (§3.1, §3.5, §3.6 — cỗ máy R-35
  đã tồn tại nguyên).
- **TRUNG BÌNH** trên cost Ph2 (Forest): packing đa-cây + envelope là [Deduced] từ R-42/LinkedList,
  chưa prototype; risk chính là animation union-glide (đang chờ teammate).
- **TRUNG BÌNH** trên B3: [Confirmed] Tree có growth + single-root; [Hypothesized] rằng
  edge-label + link-layer là đủ cho suffix-automaton (chưa dựng thử một bài SAM đầy đủ).
- **Rủi ro đã loại:** phương án B (Graph node-ops) bị 3 lớp code + RFC bác — không phải phán đoán,
  là fact (§3.1).
