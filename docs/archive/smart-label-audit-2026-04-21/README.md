# Smart-Label Audit — 2026-04-21

Research trên 4 trục để chẩn đoán smart-labeling (annotation labels) không ổn định.

> **Status**: audit findings shipped as Phase 0 (QW-1..QW-7, position-only
> emit) + MW-1 (8-direction grid). Normative contract cho feature hiện tại
> nằm ở **[`../../spec/smart-label-ruleset.md`](../../spec/smart-label-ruleset.md)** — đọc file
> đó thay vì bắt đầu từ audit này nếu bạn muốn sửa code. Audit giữ lại làm
> reference cho root-cause analysis và MW-2/3/4 roadmap.

## Files

| File | Nội dung |
|------|----------|
| `01-usage-survey.md` | Khảo sát `\annotate` trong examples + tests. 9 mẫu dùng thực, 6 repro có severity cao. |
| `02-placement-algorithm.md` | Audit 8 điểm yếu của nudge/collision loop. So sánh với nhánh `backup/pre-reset-20260421-151848` (Phase 7). |
| `03-katex-foreignobject.md` | Audit KaTeX `<foreignObject>`. 7 điểm yếu + 6 failure modes. |
| `04-recommendations.md` | Kế hoạch: 7 quick wins (≤1h), 4 medium wins (1 ngày), 3 redesign options. Prioritized action order. |

## Top Findings

**Severity cao (ưu tiên sửa):**

1. **W1 — forced-UP fallback** (`_svg_helpers.py:379–385, 699–706`): khi 4 hướng nudge đều collide, code cứ push UP vô điều kiện, không check collision, gây cascade lỗi cho labels sau.
2. **W6 — width estimate sai cho math** (`_svg_helpers.py:82–90`): `_label_width_text` chỉ strip `$`, raw LaTeX macros (`\frac`, `\sum`) đếm 0.62 em/char → sai số 25–35% với expr phức tạp.
3. **W4 — leader line cắm vào pill center** (`_svg_helpers.py:739–743`): đè lên text, không có `intersect_pill_edge`.
4. **W5 — bbox registry lệch vs rendered pill** (`_svg_helpers.py:393–395`): clamp áp dụng sau khi registered → labels sau check overlap sai.
5. **Position-only label bị drop im lặng** trên Array/DPTable (`base.py:395–396`): `\annotate{...}{position=above}` không có `arrow_from` → không emit gì.
6. **Per-primitive registry** — không share `placed_labels` giữa primitives → cross-primitive collision bị bỏ qua.

**Phase 7 (đã reset) đã giải quyết:**
- 48-candidate grid thay 4-direction.
- `intersect_pill_edge` cho leader.
- ViewBox auto-grow.
- Z-layer partition (FIXED/FLEXIBLE/NUDGEABLE).
- Global `LabelOrchestrator`.
- Repulsion solver fallback (`_repulsion.py`).

**Phase C (DOM measure-and-fix trong JS)** fragile — nên drop.

## Recommended Next Step

Xem `04-recommendations.md` — làm QW-1/QW-2/QW-3 trước (~55 min) để chặn cascade bug, rồi QW-5 (math width factor ~30 min). Medium-term: MW-1 (8-direction grid). Dài hạn: LR-1 (re-land Wave A+B từ backup, skip C.3–C.5).
