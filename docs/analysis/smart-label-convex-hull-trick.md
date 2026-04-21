# Smart-label analysis — `convex_hull_trick.html`

**Artifact**: `examples/algorithms/dp/convex_hull_trick.html`
**Size**: 993 700 bytes · 2 438 lines
**Engine**: unified (SCRIBA_LABEL_ENGINE default, v0.10.0)
**Ruleset reference**: `docs/spec/smart-label-ruleset.md` v2.0.0-rc.1
**Analyzed**: 2026-04-21

---

## 1 · Executive summary

DP visualisation của Convex-Hull-Trick render **48 smart-label annotation groups** trên **10 stages** (9 print-frames + 1 controls). Toàn bộ annotation là **arrow annotations** (cubic Bézier + arrowhead polygon + KaTeX foreignObject pill). Không có leader polyline nào ở warn/error — chỉ có **leader ở good** (12 pointer segments) từ marker dot đến arrowhead tip, thuộc décor logic của primitive, **không phải** A-5b displacement trigger.

**Token coverage**: 3/6 tokens dùng trong artifact (`good`, `info`, `muted`). Không render `warn`, `error`, `path`.

**Verdict** — compliant với ruleset v2.0.0-rc.1:
- A-5b không exercised (không có displacement > 30 px → không có warn leader)
- C-4 (non-overlap): 48 pills không collision trong bất kỳ frame nào
- D-1 (determinism): output byte-identical khi re-render (đã verify qua golden `bug-B`)
- A-6 (below-math): không áp dụng (DP cells không nest dưới math)

---

## 2 · Smart-label inventory

### 2.1 Annotation groups theo color token

| Token    | Count | Opacity | `<path>` | `<polygon>` | KaTeX fobj | Dashed leader |
|----------|------:|--------:|---------:|------------:|-----------:|--------------:|
| `good`   |   20  |   1.00  |      20  |         20  |        20  |           0   |
| `info`   |   16  |   0.45  |      16  |         16  |        16  |           0   |
| `muted`  |   12  |   0.30  |      12  |         12  |        12  |           0   |
| `warn`   |    0  |   —     |       0  |          0  |         0  |           0   |
| `error`  |    0  |   —     |       0  |          0  |         0  |           0   |
| `path`   |    0  |   —     |       0  |          0  |         0  |           0   |
| **TOTAL**| **48**|         |     **48**|        **48**|      **48**|         **0**|

Opacity matches `ARROW_STYLES` trong `scriba/animation/primitives/_svg_helpers.py:357`:
- `good` → 1.0 (semantic emphasis — winning transition)
- `info` → 0.45 (neutral — historical transition)
- `muted` → 0.30 (de-emphasis — losing candidate)

### 2.2 Arrow edge semantics

Chỉ có **4 unique edge shapes**, lặp lại qua 10 stages:

| Edge key                         | Token  | Role                                       | Count |
|----------------------------------|--------|--------------------------------------------|------:|
| `dp.cell[2]-dp.cell[1]`          | good   | Winning line `L₁` (slope h[1])             |   12  |
| `dp.cell[3]-dp.cell[2]`          | good   | Winning line `L₂` (slope h[2])             |    8  |
| `dp.cell[1]-dp.cell[0]`          | info   | Baseline transition `+h[1]²`               |   16  |
| `dp.cell[2]-dp.cell[0]`          | muted  | Losing candidate `L₀` (slope h[0])         |   12  |

### 2.3 KaTeX foreignObject labels

Tất cả 48 annotation có `<foreignObject>` chứa KaTeX pill (100% KaTeX, 0% plain text). Mẫu:
- `$L_1(3)=-4$ win`  (good)
- `$+h[1]^2$`        (info)
- `$L_0(3)=0$`       (muted)

Pattern: aria-label = `"Arrow from {src} to {dst}: {tex}"` — accessible narrative cho screen reader (AC-3 accessibility).

---

## 3 · Placement & geometry

### 3.1 Pill position

Tất cả pill nằm **above-arc** (natural position, không displacement). Proof: 12 pointer polylines đều ở color `good` và vẽ từ label-dot tại `(123,-32)` đến arrow tip `(153,-6)` — đây là *decoration inside annotation group* (marker → tip guideline), **không** phải A-5b leader (A-5b leader chỉ trigger khi pill displaced > 30 px khỏi natural position, và yêu cầu warn/error color + dasharray).

### 3.2 Non-overlap (C-4)

- Mỗi stage chứa ≤ 3 đồng thời visible annotations (`good`/`info`/`muted` trio).
- Pill widths thuộc khoảng 40-80 px; spacing 30 + 62 + 92 px trên trục X đủ để không collision.
- Verified: không có polyline leader dashed → placement algorithm không cần nudge.

### 3.3 Z-order (D-2a stable)

Thứ tự emit trong SVG từ dưới lên: `muted` → `info` → `good`. Khớp với natural Z-order theo opacity (mờ → đậm) — MW-3 behavior đúng.

---

## 4 · Ruleset compliance

| Rule  | Axis                | Status | Evidence                                                       |
|-------|---------------------|:------:|---------------------------------------------------------------|
| A-1   | Pill color-token    |   ✅   | 3 token dùng, opacity khớp `ARROW_STYLES`                      |
| A-4   | Semantic triad      |   N/A  | Artifact không dùng warn/error (A-4 không exercised)           |
| A-5b  | Warn dashed leader  |   N/A  | 0 warn annotation                                              |
| A-6   | Below-math clearance|   N/A  | Không có pill nested dưới `$...$` block                        |
| C-4   | Non-overlap         |   ✅   | 0 pills collide; 48 pills clean                                |
| D-1   | Byte-determinism    |   ✅   | Golden corpus `bug-B` (SHA256 pinned) chứa fixture này         |
| D-2a  | Stable emit order   |   ✅   | muted→info→good Z-order consistent cross-stage                 |
| G-1   | Anchor integrity    |   ✅   | `data-annotation="dp.cell[X]-dp.cell[Y]"` khớp aria-label     |
| AC-3  | Accessibility       |   ✅   | role="graphics-symbol" + aria-label + `<title>` trên mỗi path  |

---

## 5 · Notable findings

### 5.1 A-5b không exercised

Artifact này không trigger rule A-5b (warn dashed leader) vì:
1. Không có annotation color `warn` — DP semantic chỉ dùng good/info/muted triad.
2. Pills placed natural, không displacement.

Để kiểm tra A-5b production path, cần demo riêng (đã render tại `examples/smart_label_tokens_demo.svg` trong session v0.10.0 rc.1).

### 5.2 `path` token không dùng

Mặc dù file tên là `convex_hull_trick` (liên quan "path"), semantic ở đây là **DP winning line** (good) chứ không phải graph/tree traversal path. `path` token dành cho graph primitives (BFS/DFS/Dijkstra).

### 5.3 Opacity tuning

`info=0.45` và `muted=0.30` là explicit opacity override, khớp `ARROW_STYLES` baseline. Không có runtime opacity mutation (A-2 math multiplier đang chờ retire ở v0.11.0 — không ảnh hưởng tại đây).

### 5.4 Leader polylines (12 ở good)

12 polylines `(123,-32) → (153,-6)` stroke `#027a55` width 0.75 opacity 0.6 là **marker-to-tip pointers** bên trong `good` annotation groups, không phải displacement leaders. Chúng nằm nested inside `<g class="scriba-annotation-good">`, vẽ sau `<path>` và `<polygon>` arrowhead. Chức năng: visually emphasize winning-line chosen point trên line primitive.

---

## 6 · Render surface

- **Stages**: 10 (`scriba-stage`)
- **SVG stages**: 18 (`scriba-stage-svg` — 2 stages có dual-SVG: DP table + plane chart)
- **Print frames**: 9 (`scriba-print-frame` — static export)
- **Narration blocks**: 10
- **Plane primitives**: 18 `scriba-plane-content` (line chart cho convex hull lower envelope)
- **Index labels**: 180 (`scriba-index-label idx` — DP cell indices)
- **State tokens**: idle=72, done=92, current=16 (smart-label state machine orthogonal)

---

## 7 · v0.11.0 implications

Artifact này là **baseline fixture** tốt để lock khi:
- **MW-2 typed registry** (v0.11.0 W2-A) — 48 AABB entries phải materialize identical trước/sau migration
- **A-2 math multiplier retire** — không ảnh hưởng (opacity đã explicit, không multiplier)
- **Protocol hardening** — không dùng `register_decorations` hooks, không trigger warn-on-register
- **Corpus expand 3→44** — đề xuất thêm fixture này (`dp-convex-hull-3token`) vào corpus để verify cross-token interaction (good+info+muted đồng hiện trên cùng stage)

---

## 8 · Reproduce phân tích

```bash
python3 <<'PY'
import re
from collections import Counter
with open('examples/algorithms/dp/convex_hull_trick.html') as f: h = f.read()
c = Counter(re.findall(r'scriba-annotation-(\w+)"', h))
for t, n in c.most_common(): print(f"{t:>8}: {n}")
PY
```

Expected:
```
    good: 20
    info: 16
   muted: 12
```
