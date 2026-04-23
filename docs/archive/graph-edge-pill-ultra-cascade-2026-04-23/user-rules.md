# Graph Edge-Pill — User Rules

> Những nguyên tắc mà user đã nêu trong quá trình thiết kế/audit edge-pill
> placement. Đây là "north star" cho mọi demo, thử nghiệm, algorithm change.
> Không được bỏ bất kỳ rule nào khi làm demo hay đề xuất phương án thay thế.
> Breaking rule nào phải nêu rõ và giải thích trade-off.

**Last updated**: 2026-04-23
**Context**: conversation quanh GEP v1.2 cascade + ultra + spacing experiments

---

## U-01 · Pill MUST rotate theo chiều edge (GEP R-25) **[HARD RULE]**

Pill rectangle được `transform: rotate(θ, cx, cy)` theo `edge.theta`.

- `θ = atan2(y2-y1, x2-x1)` (degrees)
- Pill rotates — visual grammar "pill ôm edge"
- **Không được** render pill axis-aligned khi demo/prototype "ý tưởng mới" — đây là invariant của ruleset.
- Áp dụng cho cả: current placement, alternative techniques, optimal stacks, mockups.

**Rationale**: pill rotation là identity visual của scriba graph primitive. Đổi = đổi toàn bộ visual language, không phải local optimization.

---

## U-02 · Text phải đọc xuôi (upright) qua flip

Khi pill rotate:
- Nếu `cos(θ) >= 0`: text rotate theo pill (`transform: rotate(θ, cx, cy)`)
- Nếu `cos(θ) < 0` (edge chạy phải→trái): text rotate `θ + 180` để đọc xuôi

Không bao giờ để text hiển thị lộn ngược.

---

## U-03 · Mục tiêu là **clarity pedagogical**, không phải elegance thuật toán

> "mục tiêu phải là sự rõ ràng để người ta dễ dàng (cực dễ dàng quan sát)"

Moi lựa chọn phải đánh giá theo: người học có nhìn vô hiểu liền không?

- On-stroke > off-stroke: pill nằm trên stroke → mắt biết ngay thuộc edge nào
- Không silent failure: nếu pill collide mà vẫn vẽ đè → xấu
- Overlap là sin lớn nhất; disconnection (pill xa khỏi edge) là sin thứ hai

---

## U-04 · On-stroke preferred, off-stroke là last-resort

Priority order cho vị trí pill:

1. **Origin** (midpoint trên stroke)
2. **Along-shift** (±budget dọc stroke)
3. **Saturate** (tại `±budget` exact, dọc stroke) — vẫn on-stroke
4. **Perp** (off-stroke, nhưng gần edge) — chỉ khi cả 3 trên fail
5. **Leader / Callout** — last resort, với dashed leader rõ ràng

Rule U-01 vẫn áp dụng ở mọi stage. Pill luôn rotate.

---

## U-05 · Giữ layout, không tự ý đổi graph

Khi demo/prototype, dùng cùng dataset user đã nêu. Không tự ý:
- Đổi K5 sang DAG khác
- Đổi node positions / radius
- Đổi số lượng edges

> Quote: "demo hình khó giống cái kia đi, sao đổi luôn hình rồi"

Nếu muốn show layout-level alternative → show cả hai (before/after) trên cùng một dataset, không replace dataset.

---

## U-06 · Deterministic edge ordering

Thứ tự process edge phải deterministic → same input luôn cho same output. Không random.

Ordering hiện tại (GEP-04): sort edges theo `(min_node_id, max_node_id)` trước khi chạy cascade.

---

## U-07 · Node-radius trimming

Endpoint của edge phải bắt đầu / kết thúc **trên bề mặt node circle**, không phải tại tâm.

- `ux = (nb.cx - na.cx) / L, uy = (nb.cy - na.cy) / L`
- `p1 = (na.cx + ux * node_r, na.cy + uy * node_r)`
- `p2 = (nb.cx - ux * node_r, nb.cy - uy * node_r)`

Pill budget tính trên edge đã trim, không trên full centerline.

---

## U-08 · AABB stepping — rotated pill box

Pill có rotation → bounding box swell. Step size phải dùng rotated AABB:

```
aabb_w = pill_w · |cos θ| + pill_h · |sin θ|
aabb_h = pill_w · |sin θ| + pill_h · |cos θ|

step_along = aabb_w + 2
step_perp  = aabb_h + 2
```

**Không được** dùng pill_w thẳng cho step — sẽ underestimate trên edge nghiêng.

---

## U-09 · Along-shift budget

Budget cho along-shift phải account cho node radius 2 đầu:

```
budget = max(0, edge_trimmed_length / 2 - pill_w / 2 - node_r)
```

Nếu budget = 0 → edge quá ngắn cho pill, bỏ qua stage along-shift.

---

## U-10 · Side-preferred perp order (Option 2)

Khi phải đi vào stage perp (U-04 bước 4), thứ tự probe:

```
(+1·step, +2·step, -1·step, -2·step)
```

Ưu tiên **cùng một bên** trước khi đổi bên. Tránh flicker giữa 2 bên khi re-run.

---

## U-11 · Saturate probe (Option 5)

Giữa along-shift và perp, thêm stage 1.5: thử pill tại **đúng** `±budget`. Lý do: along-shift-by-step có thể không cover hair-thin collision 0.5-1px ngay tại biên budget. Saturate catches these cases → giữ pill on-stroke.

---

## U-12 · Commit theo từng milestone nhỏ

User thích commit atomic, có nội dung rõ ràng. Không batch nhiều thứ unrelated vào 1 commit.

- GEP v1.2 algorithm: commit riêng
- Docs/archive: commit riêng
- Test updates: commit cùng source change liên quan

---

## U-14 · Pill center MUST nằm trên edge stroke (on-stroke default) **[HARD RULE]**

Pill center `(x, y)` phải trùng trên đường thẳng từ `ep.x1,ep.y1` đến `ep.x2,ep.y2` **by default**.

- Along-shift: `(x, y) = (mx + t·cosθ, my + t·sinθ)` với `t ∈ [-budget, +budget]` → vẫn on-stroke ✔
- Saturate (U-11): `t = ±budget` → vẫn on-stroke ✔
- Perp (U-10): off-stroke, chỉ được dùng khi cả origin + along + saturate đều fail
- Leader (U-04 last-resort): off-stroke có dashed line back to midpoint

**Vi phạm thường gặp**: global pass (SA/force-directed) để perp offset free → pill drift khỏi stroke dù không có collision forcing. Không được. SA phải:

- Pill ở on-stroke state (origin/along/sat): lock `perp = 0`, chỉ di chuyển along stroke
- Pill ở off-stroke state (perp/leader): được di chuyển cả 2 chiều nhưng energy phải có **strong pull** kéo trở về on-stroke nếu unblock

**Rationale**: center-on-stroke là phần của visual identity — pill "ôm" edge. Đây cùng gia đình với U-01 (rotate theo edge): pill không chỉ nghiêng theo edge mà còn nằm trên nó.

---

## U-15 · Auto-expansion (upstream spacing) là một phần của OPTIMAL

Khi compute optimal placement, layout scale `s` là **một lever hợp lệ**. Không cố định `s = 1.0` nếu pill không fit.

### Công thức per-edge

```
aabb_w(e) = pw·|cos θ| + ph·|sin θ|          // rotated AABB dọc edge
min_tl(e) = aabb_w(e) + 2·node_r + margin    // tl cần để pill on-stroke fit
scale(e)  = min_tl(e) / tl_original(e)
```

Per-edge lower bound: `s_min_analytic = max(1.0, max over e of scale(e))`.

Đây là **necessary condition** cho mỗi edge fit pill riêng, nhưng **không sufficient** cho pill-pill clearance ở dense zones (center K5).

### Binary search

Để đảm bảo 0 fallback sau cascade:

```
lo = s_min_analytic, hi = s_min_analytic · 1.8
while hi - lo > 0.02:
  mid = (lo + hi) / 2
  run cascade on scaled graph
  if fallback_count == 0: hi = mid
  else:                   lo = mid
return hi
```

### Trade-off

- Scale càng lớn → pill càng rõ → canvas càng to
- OPTIMAL chọn `s` nhỏ nhất thoả fallback = 0

Nếu canvas bound (ví dụ layout fixed), scale tối đa = bound_scale. Khi `s_min > bound_scale` → buộc phải dùng leader (U-04 last-resort).

---

## U-13 · Archive artifacts vào folder riêng theo ngày

Format: `docs/archive/<topic>-<YYYY-MM-DD>/`

Mỗi folder:
- `README.md` — mô tả session + kết luận
- Artifacts (demo HTML, data JSON, notes)

Không rải artifacts vào `/tmp` permanent hoặc root repo.

---

## Enforcement checklist

Trước khi show demo/propose alternative:

- [ ] Pill có `transform: rotate(θ, cx, cy)` — U-01
- [ ] Text flip theo cos(θ) sign — U-02
- [ ] Pill center on-stroke theo default, off-stroke chỉ khi bị block — U-14
- [ ] Dataset không đổi so với conversation trước — U-05
- [ ] Deterministic (seeded) nếu có random — U-06
- [ ] AABB collision dùng rotated box — U-08
- [ ] Budget account cho node_r — U-09
- [ ] Commit atomic — U-12

Miss rule nào → phải tự call ra rõ ràng trong response, không silent.
