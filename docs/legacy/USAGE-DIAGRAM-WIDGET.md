# Usage: tái tạo `mock-diagram-widget.html` bằng Scriba

> File này phân tích từng lớp của `mock-diagram-widget.html` và chỉ rõ **tác giả phải viết gì trong markdown nguồn** để Scriba (sau khi implement xong theo spec `03-diagram-plugin.md` + `08-usage-example.md`) emit ra cấu trúc HTML tương đương. Không có JS thủ công. Không có tính toạ độ SVG. Không có debug CSS.

---

## 0. Tóm tắt sự đánh đổi

| Layer | Hiện trong mock | Sau khi dùng Scriba |
|---|---|---|
| Segment tree SVG (nodes, edges, array strip) | 200 dòng JS build từng `<circle>` thủ công | 1 code fence D2 ~30 dòng |
| Step state machine (cumulative visible) | JS `STEPS` array + class toggling | D2 `steps:` keyword |
| Description per step (với KaTeX math) | `<p data-step="N">` + `renderMathInElement` | `# @scriba steps:` comment block |
| Crossfade frames | CSS `.frame.active { opacity: 1 }` + JS toggle | **Đã đóng gói** trong `scriba-diagram-steps.js` |
| Controls (first/prev/play/next/last) + keyboard | 80 dòng JS | **Đã đóng gói** trong asset JS |
| Progress bars | `<div class="bar">` + JS | **Đã đóng gói** |
| Theme toggle light/dark | CSS vars + button | CSS vars giữ nguyên; Scriba không ép theme |
| Coordinate bugs (viewBox clip, arrow hụt, node lệch) | Phải tự debug | **Biến mất**. D2 layout engine (dagre/elk) quản |

Tất cả những gì tác giả cần viết đều là **nội dung**, không phải presentation.

---

## 1. Tác giả viết cái gì?

File `problems/segtree-range-sum.md`:

````markdown
# Segment tree — Range sum query

Mảng $a = [2, 5, 1, 4, 9, 3]$. Truy vấn: $\text{sum}(1, 4) = ?$

```d2
# @scriba steps:
#   1: "Mảng $a = [2, 5, 1, 4, 9, 3]$ với segment tree lưu tổng đoạn. Truy vấn $\\text{sum}(1,4) = ?$"
#   2: "Tại gốc $[0,5]$, đoạn truy vấn $[1,4]$ giao **một phần** → đệ quy xuống cả hai con."
#   3: "Xuống trái $[0,2]$: $[1,1]$ phủ hoàn toàn → **lấy 5**; $[2,2]$ → **lấy 1**; $[0,0]$ ngoài khoảng → **bỏ qua**."
#   4: "Xuống phải $[3,5]$: $[3,4]$ phủ hoàn toàn → **lấy 13** (khỏi đi sâu); $[5,5]$ bỏ qua."
#   5: "Ba nút đóng góp: $[1,1]$, $[2,2]$, $[3,4]$. Các nhánh còn lại không cần chạm → đây là lý do $O(\\log n)$."
#   6: "Kết quả: $5 + 1 + 13 = 19$. Cây 11 nút, chỉ đọc **3** nút để trả lời."

vars: {
  d2-config: {
    layout-engine: dagre
    theme-id: neutral-default
  }
}

# --- baseline tree shape ---
n1: "[0,5]\n24"
n2: "[0,2]\n8"
n3: "[3,5]\n16"
n4: "[0,1]\n7"
n5: "[2,2]\n1"
n6: "[3,4]\n13"
n7: "[5,5]\n3"
n8: "[0,0]\n2"
n9: "[1,1]\n5"
n12: "[3,3]\n4"
n13: "[4,4]\n9"

n1 -> n2
n1 -> n3
n2 -> n4
n2 -> n5
n3 -> n6
n3 -> n7
n4 -> n8
n4 -> n9
n6 -> n12
n6 -> n13

# --- per-step highlighting ---
steps: {
  1: {
    # initial: everything idle (baseline styling)
  }
  2: {
    n1.style.fill: "#dbeafe"
    n1.style.stroke: "#2563eb"
    n2.style.stroke: "#2563eb"
    n3.style.stroke: "#2563eb"
  }
  3: {
    n4.style.stroke: "#2563eb"
    n9.style.fill: "#d1fae5"
    n9.style.stroke: "#059669"
    n5.style.fill: "#d1fae5"
    n5.style.stroke: "#059669"
    n8.style.opacity: 0.45
  }
  4: {
    n6.style.fill: "#d1fae5"
    n6.style.stroke: "#059669"
    n7.style.opacity: 0.45
  }
  5: {
    # fade everything except the 3 contributors
    n1.style.opacity: 0.35
    n2.style.opacity: 0.35
    n3.style.opacity: 0.35
    n4.style.opacity: 0.35
    n7.style.opacity: 0.35
    n8.style.opacity: 0.35
    n12.style.opacity: 0.35
    n13.style.opacity: 0.35
  }
  6: {
    # same as step 5 — result screen
  }
}
```

Truy vấn đi qua **3 nút**, trả về `5 + 1 + 13 = 19`. Độ phức tạp $O(\log n)$.
````

**Lưu ý:**
- Code fence `d2` là boundary mà `DiagramRenderer.detect()` scan qua regex `^```d2\n(?P<body>.*?)\n```$`.
- Comment `# @scriba steps:` là metadata mà Scriba parse để lấy description — D2 bỏ qua vì bắt đầu bằng `#`.
- D2 `steps:` block là native D2 syntax — D2 engine tự render ra N frame.
- Ngoài khối này tác giả viết markdown bình thường với `$…$` LaTeX — `TexRenderer` xử lý riêng.

**Toàn bộ fichier nguồn: ~60 dòng D2 + text.** So với mock hiện tại: ~650 dòng HTML/CSS/JS.

---

## 2. Pipeline biến nó thành gì?

Dòng chảy thực thi sau khi consumer gọi `pipeline.render(Document(source=md_text))`:

```
1. Pipeline.render()
   ├── TexRenderer.detect()        → tìm $…$ và $$…$$ blocks
   ├── DiagramRenderer.detect()    → tìm ```d2 fence, trả về Block
   │
   ├── for each Block in doc order:
   │     TexRenderer.render_block() → KaTeX subprocess → HTML math
   │     DiagramRenderer.render_block() → D2Engine.render()
   │                                     ├── parse `# @scriba steps:` comments
   │                                     ├── count steps (brace-balanced scan of `steps: { N: … }`)
   │                                     ├── N+1 subprocess calls to `d2 --bundle=false …`
   │                                     │     (1 baseline + N per-step slice)
   │                                     ├── stamp `data-step="k"` lên từng element
   │                                     └── emit DiagramEngineOutput{svg, frame_elements, total_steps=6}
   │
   └── splice artifacts back into source → final HTML
```

Artifact trả về là 1 `<figure class="scriba-diagram-widget">` **gần giống hệt** cấu trúc trong mock:

```html
<figure class="scriba-diagram-widget"
        data-step-current="1"
        data-step-total="6"
        tabindex="0"
        aria-label="D2 diagram: 6-step walkthrough">

  <div class="scriba-diagram-svg">
    <!-- 1 SVG master, mọi element có data-step="N" -->
    <svg viewBox="0 0 720 540" role="img">
      <g class="shape" data-step="1" id="n1">…</g>
      <g class="shape" data-step="2" id="n1-highlight">…</g>
      <g class="connection" data-step="1" id="n1-n2">…</g>
      …
    </svg>
  </div>

  <nav class="scriba-diagram-controls">
    <button data-action="first">⏮</button>
    <button data-action="prev">◀ Prev</button>
    <button data-action="play">▶ Play</button>
    <button data-action="next">Next ▶</button>
    <button data-action="last">⏭</button>
    <span class="scriba-diagram-step-counter"><span class="cur">1</span> / 6</span>
  </nav>

  <div class="scriba-diagram-progress">
    <div class="bar"></div><div class="bar"></div>…
  </div>

  <div class="scriba-diagram-description">
    <p class="step-title">STEP 1</p>
    <p data-step="1" class="active">Mảng <span class="katex">…</span>…</p>
    <p data-step="2">Tại gốc <span class="katex">…</span>…</p>
    …
  </div>
</figure>
```

Khác biệt so với mock hiện tại:

| Mock tự làm | Scriba output |
|---|---|
| Nhiều SVG frame riêng, crossfade `opacity` giữa div.frame | 1 SVG master, mọi element gắn `data-step`; JS chỉ toggle `visibility` dựa trên step current |
| Toạ độ tính tay (NODES `x,y`) | D2 dagre/elk layout, hết lệch |
| Array strip vẽ JS (cellW, stripStartX) | D2 shape `array: { cells: [...] }` hoặc grid container |
| KaTeX load qua CDN + auto-render trong body | Scriba `TexRenderer` đã replace math bằng `<span class="katex">` **tại build-time** — client không cần chạy KaTeX |
| Controls build thủ công trong HTML, event listener inline | Asset `scriba-diagram-steps.js` tự wire lên mọi `.scriba-diagram-widget` trên page |
| Theme toggle làm riêng | CSS vars `--node-path-stroke` etc đã ở dạng CSS custom property trong `scriba-diagram.css` → consumer chỉ cần override ở `:root[data-theme="dark"]` |

---

## 3. Consumer nhúng vào site thế nào?

Nội dung lấy từ `08-usage-example.md`, chỉ phần liên quan widget:

```html
<!-- layout.html của consumer -->
<link rel="stylesheet" href="/static/scriba/scriba-tex-content.css">
<link rel="stylesheet" href="/static/scriba/scriba-diagram.css">

{{ rendered_problem_html | safe }}

<script defer src="/static/scriba/scriba-diagram-steps.js"></script>
```

`scriba-diagram-steps.js` là **auto-init**: trên `DOMContentLoaded` nó `querySelectorAll('.scriba-diagram-widget')` và gắn controller cho mỗi widget. Consumer không cần gọi hàm gì.

Toàn bộ HTML đã render được cache trong DB:

```python
# routes/problems.py — pseudo
@bp.route("/problem/<slug>")
def show(slug):
    row = db.get(slug)
    if row.html_cache:
        return render_template("problem.html", html=row.html_cache)

    pipeline = current_app.extensions["scriba"]["pipeline"]
    doc = Document(source=row.markdown_source)
    result = pipeline.render(doc, ctx=RenderContext(mode="html"))

    row.html_cache = result.html
    db.save(row)
    return render_template("problem.html", html=result.html)
```

Render 1 lần, sau đó serve nguyên từ DB. Khi tác giả edit markdown → invalidate cache → render lại.

---

## 4. Những thứ tác giả KHÔNG cần viết nữa

Đây là danh sách explicit những dòng code biến mất khỏi tay tác giả sau khi có Scriba:

- ❌ `document.createElementNS(svgNS, "circle")` — bất kỳ SVG build tay nào
- ❌ `NODES = [{ id: 1, x: 360, y: 48 }, …]` — toạ độ thủ công
- ❌ `EDGES = [[1,2], [1,3], …]` — list edge thủ công (đã ở trong D2 source)
- ❌ `buildFrame(stepIdx)` — render function
- ❌ State class toggling logic (`state[n.id]` → CSS class)
- ❌ Crossfade CSS (`.frame { opacity: 0 } .frame.active { opacity: 1 }`)
- ❌ Step controller IIFE (`initWidget`)
- ❌ Keyboard handler (`widget.addEventListener("keydown", …)`)
- ❌ Progress bar logic
- ❌ KaTeX auto-render script tag
- ❌ Bất kỳ CSS nào liên quan đến node shape, edge stroke, layout (D2 theme đảm nhận)

Tác giả chỉ cần viết:

- ✅ D2 source mô tả topology (~15 dòng node + edge khai báo)
- ✅ D2 `steps:` block với delta styling per step (~20 dòng)
- ✅ `# @scriba steps:` comments cho description (~8 dòng)
- ✅ Markdown prose xung quanh (bất kỳ bao nhiêu)

**Tổng: ~45 dòng nội dung thật, 0 dòng presentation.**

---

## 5. Mức độ fidelity so với mock

Không phải 100%. Một số thứ mock hiện tại có mà Scriba (v0.3) sẽ không tái tạo chính xác được:

| Feature mock | Scriba v0.3 | Workaround |
|---|---|---|
| Query brace trên đầu SVG "query sum(1,4) = ?" | Không có native, nhưng D2 có `top-label` hoặc container caption | Gắn `near: top-center` label trong D2 |
| Focus ring dashed vàng quanh node "current" | D2 không có dashed ring tinh chỉnh | `style.stroke-dash` hoặc SVG post-processing hook (deferred v0.4) |
| Array strip đồng bộ highlight với tree | D2 grid container + step styling | Cùng file D2, khai báo `array: grid-rows: 1 { a0; a1; …; a5 }` và style trong `steps:` |
| Legend (Idle/Visited/Taken/Skipped) | Nằm ngoài widget, là HTML tĩnh | Tác giả viết `<div class="legend">` bên cạnh, không phải việc của Scriba |
| Theme toggle button | Nằm ngoài widget | Consumer tự làm bằng `document.documentElement.dataset.theme = …` |
| Tiếng Việt description với KaTeX | Có — TexRenderer xử lý `$…$` trong description strings | Escape `\\text` thành `\\\\text` trong YAML-like comment |

Mục 1 (query brace) và 3 (array strip sync) là **test case hay** cho spec v0.3 — nếu D2 không làm được thì phải bổ sung vào `07-open-questions.md`.

---

## 6. Bugs sẽ biến mất

Đối chiếu với `swap-game-demo-ver3` (tay viết), các bug sau sẽ **không thể** xuất hiện nếu viết bằng Scriba/D2:

- **Arrow hụt 5px không chạm grid** → D2 tự route edge endpoint tới bounding box của shape.
- **viewBox clip content** → D2 tính canvas sau layout, không có viewBox thủ công.
- **Mini grid không center trong plaque** → D2 container tự pad + center child.
- **Fan edges vẽ sai topology** → edge khai báo `a -> b`, không vẽ tay.
- **Label y-position đè rect** → layout engine tránh overlap.
- **Spacing inconsistent giữa figures** → 1 D2 theme thống nhất.
- **Missing `<defs><marker>`** → D2 tự emit arrowhead marker.
- **Hero viz min-height clip caption** → không có hero viz theo nghĩa "widget nhỏ" — Scriba widget là 1 khối, consumer chọn kích thước qua CSS max-width.

Các bug sẽ **vẫn có thể** xuất hiện (không phải Scriba lỗi, là giới hạn fundamental):

- **Layout engine chọn chỗ node không như ý** — phải chỉnh bằng D2 hint (`near:`, `direction:`, grid container).
- **Step delta styling sai** — nếu tác giả viết `steps: { 2: { n1.style.fill: "#..." } }` mà quên, D2 vẫn render step 2 giống step 1.
- **Description math syntax lỗi** — KaTeX error sẽ propagate qua `TexRenderer`, hiển thị error box thay vì im lặng.

---

## 7. Checklist khi port `mock-diagram-widget.html` sang Scriba

Khi package v0.3 ship xong, port file mock hiện tại theo các bước:

1. [ ] Trích 11 node + 10 edge thành D2 declarations (thay cho `NODES` array).
2. [ ] Trích 6 `STEPS` JS objects thành D2 `steps: { 1:{…} 2:{…} … 6:{…} }`.
3. [ ] Trích 6 description `<p data-step="N">` thành `# @scriba steps:` comment block.
4. [ ] Xoá toàn bộ `<style>`, `<script>`, KaTeX CDN tag.
5. [ ] Thêm `<link href="/static/scriba/scriba-diagram.css">` + `<script src="/static/scriba/scriba-diagram-steps.js">` vào layout.
6. [ ] Chạy `pipeline.render(Document(source=md))` → verify output HTML match mock về structure (không cần match pixel).
7. [ ] Diff behaviour: controls hoạt động? keyboard nav? progress bars? theme toggle (CSS vars)?
8. [ ] Ghi lại bất kỳ deviation nào vào test suite `tests/fidelity/segtree.py`.

Nếu checklist pass sạch → package đã đủ để **thay thế** toàn bộ cách làm editorial hiện tại ở `swap-game-demo-ver3/`, `monkey-apples-demo/`, `frog1-demo/`.

---

## 8. TL;DR

- **Tác giả viết**: ~45 dòng D2 + markdown, 0 dòng JS, 0 dòng CSS.
- **Scriba xử lý**: D2 subprocess → SVG master → `data-step` tagging → widget HTML shell + ship CSS/JS.
- **Consumer chỉ cần**: 2 link tag + inject `result.html` vào template.
- **Bugs hiện tại biến mất**: tất cả bug toạ độ, viewBox, arrow routing, layout inconsistency.
- **Bugs còn lại**: chỉ content-level (layout engine chọn sai chỗ, delta styling thiếu) — fix bằng cách sửa D2 source, không phải debug SVG.

Mấu chốt: Scriba không phải "thư viện SVG". Nó là **build-time compiler** từ markdown-with-diagrams sang HTML-with-widget. Một khi tác giả đã quen syntax D2, việc viết editorial mới giống viết văn hơn là code front-end.
