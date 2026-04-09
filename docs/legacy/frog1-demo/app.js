// ==========================================================
// Frog 1 — animated DP walkthrough
// heights = [30, 10, 60, 10, 60, 50]
// Expected: dp = [0, 20, 30, 20, 30, 40], path = 0→2→4→5
// ==========================================================

const HEIGHTS = [30, 10, 60, 10, 60, 50];
const N = HEIGHTS.length;

// --- Layout constants ---
const VB_W = 820,
  VB_H = 460;
const BAR_CENTERS = [90, 210, 330, 450, 570, 690]; // x centers
const BAR_W = 70;
const BAR_BASE_Y = 230; // y of ground
const BAR_MAX_PX = 170; // max bar pixel height
const MAX_H = 60; // max height in data
const pxOf = (h) => (h / MAX_H) * BAR_MAX_PX;
const barTopY = (h) => BAR_BASE_Y - pxOf(h);

const DP_ROW_Y = 290;
const DP_CELL_W = 90;
const DP_CELL_H = 56;
const DP_CELL_X = (i) => BAR_CENTERS[i] - DP_CELL_W / 2;

// ==========================================================
// Frame state definitions
// Each frame is a pure snapshot the renderer consumes.
// ==========================================================
// Fields:
//   dp:     array — computed values so far (undefined = empty)
//   pending: int | null — cell currently being computed
//   cands:  {A, B} | null — two candidates being compared
//     each cand: {fromIdx, cost, total, state: 'show'|'win'|'lose'}
//   frog:   int — current stone index
//   path:   array of stone indices — optimal path (shown at end)
//   total:  int | null — final answer shown as trophy
//   title:  string — step title
//   body:   string — markdown-like description (KaTeX inline)
// ==========================================================

const STEPS = [
  // ---------- 1 ----------
  {
    dp: [],
    pending: null,
    cands: null,
    frog: 0,
    path: [],
    total: null,
    title: "STEP 1 — SETUP",
    body: "6 cột đá với chiều cao $h = [30, 10, 60, 10, 60, 50]$. Con ếch $🐸$ ở cột 1. Mỗi lần nhảy được +1 hoặc +2 cột, chi phí $= |h_i - h_j|$. Cần tìm tổng chi phí nhỏ nhất để đến cột 6.",
  },
  // ---------- 2 ----------
  {
    dp: [0],
    pending: null,
    cands: null,
    frog: 0,
    path: [],
    total: null,
    title: "STEP 2 — BASE CASE",
    body: "$dp[0] = 0$ — đã ở cột 1, chưa mất gì. Từ đây ta sẽ tính dần $dp[1], dp[2], \\ldots, dp[5]$ theo thứ tự.",
  },
  // ---------- 3 ----------
  {
    dp: [0, 20],
    pending: null,
    cands: null,
    frog: 1,
    path: [],
    total: null,
    title: "STEP 3 — dp[1] = 20",
    body: "Chỉ có 1 cách đến cột 2: từ cột 1. $dp[1] = dp[0] + |30 - 10| = 0 + 20 = 20$. Chưa có $\\min$ vì chưa có lựa chọn.",
  },
  // ---------- 4: dp[2] candidates ----------
  {
    dp: [0, 20],
    pending: 2,
    cands: {
      A: { fromIdx: 1, cost: 50, total: 70, state: "show" },
      B: { fromIdx: 0, cost: 30, total: 30, state: "show" },
    },
    frog: 1,
    path: [],
    total: null,
    title: "STEP 4 — dp[2]: HAI ỨNG VIÊN",
    body: "Để đến cột 3 có 2 cách. <b>A:</b> từ cột 2 → $dp[1] + |10 - 60| = 20 + 50 = 70$. <b>B:</b> từ cột 1 → $dp[0] + |30 - 60| = 0 + 30 = 30$. Ai thắng?",
  },
  // ---------- 5: dp[2] resolved ----------
  {
    dp: [0, 20, 30],
    pending: null,
    cands: {
      A: { fromIdx: 1, cost: 50, total: 70, state: "lose" },
      B: { fromIdx: 0, cost: 30, total: 30, state: "win" },
    },
    frog: 2,
    path: [],
    total: null,
    title: "STEP 5 — dp[2] = 30",
    body: "$\\min(70, 30) = 30$. Ứng viên A thua (gạch đỏ). <b>Ếch bỏ qua cột 2 hoàn toàn</b> — đây chính là chỗ greedy sai: greedy sẽ chọn đi cột 2 vì gần nhất, nhưng DP thấy đi thẳng từ 1 đến 3 rẻ hơn.",
  },
  // ---------- 6: dp[3] candidates ----------
  {
    dp: [0, 20, 30],
    pending: 3,
    cands: {
      A: { fromIdx: 2, cost: 50, total: 80, state: "show" },
      B: { fromIdx: 1, cost: 0, total: 20, state: "show" },
    },
    frog: 2,
    path: [],
    total: null,
    title: "STEP 6 — dp[3]: ZERO-COST JUMP",
    body: "<b>A:</b> $dp[2] + |60 - 10| = 30 + 50 = 80$. <b>B:</b> $dp[1] + |10 - 10| = 20 + 0 = 20$. Cột 2 và cột 4 <b>cao bằng nhau</b> → nhảy miễn phí!",
  },
  // ---------- 7: dp[3] resolved ----------
  {
    dp: [0, 20, 30, 20],
    pending: null,
    cands: {
      A: { fromIdx: 2, cost: 50, total: 80, state: "lose" },
      B: { fromIdx: 1, cost: 0, total: 20, state: "win" },
    },
    frog: 3,
    path: [],
    total: null,
    title: "STEP 7 — dp[3] = 20",
    body: "Ếch nhảy từ cột 2 (height 10) → cột 4 (height 10) hoàn toàn miễn phí. Tổng chi phí vẫn là 20. Đây là trực quan cho công thức $|h_i - h_j| = 0$ khi hai cột cao bằng nhau.",
  },
  // ---------- 8: dp[4] candidates ----------
  {
    dp: [0, 20, 30, 20],
    pending: 4,
    cands: {
      A: { fromIdx: 3, cost: 50, total: 70, state: "show" },
      B: { fromIdx: 2, cost: 0, total: 30, state: "show" },
    },
    frog: 3,
    path: [],
    total: null,
    title: "STEP 8 — dp[4]: LẠI ZERO-COST",
    body: "<b>A:</b> $dp[3] + |10 - 60| = 20 + 50 = 70$. <b>B:</b> $dp[2] + |60 - 60| = 30 + 0 = 30$. Cột 3 và cột 5 cũng cao bằng nhau (cùng 60)!",
  },
  // ---------- 9: dp[4] resolved ----------
  {
    dp: [0, 20, 30, 20, 30],
    pending: null,
    cands: {
      A: { fromIdx: 3, cost: 50, total: 70, state: "lose" },
      B: { fromIdx: 2, cost: 0, total: 30, state: "win" },
    },
    frog: 4,
    path: [],
    total: null,
    title: "STEP 9 — dp[4] = 30",
    body: "Ếch nhảy từ cột 3 → cột 5, lại miễn phí. Tại đây ta đã thấy <b>pattern</b>: đường tối ưu đi qua các cặp cột cùng độ cao để tận dụng jump zero-cost.",
  },
  // ---------- 10: dp[5] candidates ----------
  {
    dp: [0, 20, 30, 20, 30],
    pending: 5,
    cands: {
      A: { fromIdx: 4, cost: 10, total: 40, state: "show" },
      B: { fromIdx: 3, cost: 40, total: 60, state: "show" },
    },
    frog: 4,
    path: [],
    total: null,
    title: "STEP 10 — dp[5]: CUỐI CÙNG",
    body: "<b>A:</b> $dp[4] + |60 - 50| = 30 + 10 = 40$. <b>B:</b> $dp[3] + |10 - 50| = 20 + 40 = 60$. Jump dài (cột 4 → 6) đắt hơn vì chênh lệch lớn.",
  },
  // ---------- 11: dp[5] resolved ----------
  {
    dp: [0, 20, 30, 20, 30, 40],
    pending: null,
    cands: {
      A: { fromIdx: 4, cost: 10, total: 40, state: "win" },
      B: { fromIdx: 3, cost: 40, total: 60, state: "lose" },
    },
    frog: 5,
    path: [],
    total: null,
    title: "STEP 11 — dp[5] = 40",
    body: "$dp[5] = 40$. Đây là đáp án. Nhưng — <b>đi đường nào mới ra được 40?</b> Bảng $dp$ không trực tiếp trả lời. Phải lần ngược parent pointer.",
  },
  // ---------- 12: backtrack path ----------
  {
    dp: [0, 20, 30, 20, 30, 40],
    pending: null,
    cands: null,
    frog: 5,
    path: [0, 2, 4, 5],
    total: 40,
    title: "STEP 12 — ĐƯỜNG TỐI ƯU: 1 → 3 → 5 → 6",
    body: "Lần ngược: $dp[5]$ đến từ $dp[4]$, $dp[4]$ đến từ $dp[2]$, $dp[2]$ đến từ $dp[0]$. Path = cột 1 → 3 → 5 → 6. Tổng = $30 + 0 + 10 = 40$. <b>Animation cho bạn thấy path, code text không.</b>",
  },
];

// ==========================================================
// SVG builder helpers
// ==========================================================
const SVG_NS = "http://www.w3.org/2000/svg";
function el(name, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined) continue;
    node.setAttribute(k, v);
  }
  for (const c of children) node.appendChild(c);
  return node;
}
function text(content, attrs = {}) {
  const t = el("text", attrs);
  t.textContent = content;
  return t;
}

// ==========================================================
// Build the static SVG skeleton (everything that exists in any frame).
// Per-step render just toggles classes + text.
// ==========================================================
function buildSkeleton(host) {
  const svg = el("svg", {
    viewBox: `0 0 ${VB_W} ${VB_H}`,
    role: "img",
    "aria-label": "Frog 1 DP visualization",
  });

  // --- title row ---
  svg.appendChild(
    text("Stones (heights)", {
      x: 20,
      y: 22,
      class: "section-label",
      style: "font: 600 12px ui-monospace, monospace; fill: var(--muted);",
    }),
  );
  svg.appendChild(
    text("dp[i] — min cost to reach stone i", {
      x: 20,
      y: DP_ROW_Y - 12,
      class: "section-label",
      style: "font: 600 12px ui-monospace, monospace; fill: var(--muted);",
    }),
  );

  // --- ground line ---
  svg.appendChild(
    el("line", {
      x1: 20,
      y1: BAR_BASE_Y,
      x2: VB_W - 20,
      y2: BAR_BASE_Y,
      stroke: "var(--border)",
      "stroke-width": 2,
    }),
  );

  // --- bars ---
  for (let i = 0; i < N; i++) {
    const cx = BAR_CENTERS[i];
    const h = pxOf(HEIGHTS[i]);
    const g = el("g", { class: "bar", "data-bar": i });
    g.appendChild(
      el("rect", {
        x: cx - BAR_W / 2,
        y: BAR_BASE_Y - h,
        width: BAR_W,
        height: h,
        rx: 4,
      }),
    );
    g.appendChild(
      text(String(HEIGHTS[i]), {
        class: "h-label",
        x: cx,
        y: BAR_BASE_Y - h - 8,
      }),
    );
    g.appendChild(
      text(`stone ${i + 1}`, {
        class: "i-label",
        x: cx,
        y: BAR_BASE_Y + 16,
      }),
    );
    svg.appendChild(g);
  }

  // --- optimal path overlay (drawn behind frog) ---
  const pathG = el("g", { id: "optimalPathG" });
  pathG.appendChild(
    el("path", {
      id: "optimalPath",
      class: "optimal-path",
      d: "", // filled at backtrack frame
    }),
  );
  svg.appendChild(pathG);

  // --- frog ---
  const frog = el("g", {
    class: "frog",
    id: "frog",
    transform: `translate(${BAR_CENTERS[0]}, ${barTopY(HEIGHTS[0]) - 22})`,
  });
  frog.appendChild(el("circle", { cx: 0, cy: 0, r: 18 }));
  frog.appendChild(text("🐸", { class: "emoji", x: 0, y: 1 }));
  svg.appendChild(frog);

  // --- dp cells ---
  for (let i = 0; i < N; i++) {
    const g = el("g", { class: "dp-cell", "data-dp": i });
    const cx = BAR_CENTERS[i];
    g.appendChild(
      el("rect", {
        x: cx - DP_CELL_W / 2,
        y: DP_ROW_Y,
        width: DP_CELL_W,
        height: DP_CELL_H,
        rx: 8,
      }),
    );
    g.appendChild(
      text(`dp[${i}]`, {
        class: "label",
        x: cx,
        y: DP_ROW_Y + 16,
      }),
    );
    g.appendChild(
      text("", {
        class: "value",
        x: cx,
        y: DP_ROW_Y + 40,
      }),
    );
    svg.appendChild(g);
  }

  // --- candidate badges (two, repositioned per step) ---
  for (const slot of ["A", "B"]) {
    const g = el("g", { class: "candidate", id: `cand${slot}` });
    g.appendChild(el("rect", { x: -65, y: -18, width: 130, height: 36 }));
    g.appendChild(text("", { x: 0, y: 0 }));
    svg.appendChild(g);
  }

  // --- arrows from dp source to candidate ---
  for (const slot of ["A", "B"]) {
    svg.appendChild(
      el("path", {
        class: "arrow",
        id: `arrow${slot}`,
        d: "",
      }),
    );
  }

  // --- total badge ---
  const totalG = el("g", {
    class: "total-badge",
    id: "totalBadge",
    transform: `translate(${VB_W - 90}, 40)`,
  });
  totalG.appendChild(el("rect", { x: -60, y: -24, width: 120, height: 48 }));
  totalG.appendChild(text("", { x: 0, y: 0 }));
  svg.appendChild(totalG);

  host.appendChild(svg);
  return svg;
}

// ==========================================================
// Render a step onto the skeleton
// ==========================================================
function render(step, svg) {
  // --- dp cells ---
  for (let i = 0; i < N; i++) {
    const g = svg.querySelector(`[data-dp="${i}"]`);
    const val = step.dp[i];
    const valueText = g.querySelector(".value");
    g.classList.remove("pending", "filled");
    if (step.pending === i) {
      g.classList.add("pending");
      valueText.textContent = "?";
    } else if (val !== undefined) {
      g.classList.add("filled");
      valueText.textContent = String(val);
    } else {
      valueText.textContent = "";
    }
  }

  // --- bars: highlight current + optimal path ---
  for (let i = 0; i < N; i++) {
    const bar = svg.querySelector(`[data-bar="${i}"]`);
    bar.classList.remove("highlight", "optimal");
    if (step.path.includes(i)) bar.classList.add("optimal");
    else if (i === step.frog) bar.classList.add("highlight");
  }

  // --- frog position ---
  const frog = svg.querySelector("#frog");
  const fx = BAR_CENTERS[step.frog];
  const fy = barTopY(HEIGHTS[step.frog]) - 22;
  frog.setAttribute("transform", `translate(${fx}, ${fy})`);

  // --- candidates ---
  for (const slot of ["A", "B"]) {
    const g = svg.querySelector(`#cand${slot}`);
    const arrow = svg.querySelector(`#arrow${slot}`);
    g.classList.remove("show", "win", "lose");
    arrow.classList.remove("show", "win", "lose");

    if (!step.cands || !step.cands[slot]) continue;

    const c = step.cands[slot];
    // Anchor candidate badges above the stone being resolved — either the
    // cell currently pending, or the most recently filled cell after resolve.
    const anchorIdx = step.pending !== null ? step.pending : step.dp.length - 1;
    const tx = BAR_CENTERS[anchorIdx];
    const ty = 70;
    const offsetX = slot === "A" ? -80 : 80;
    g.setAttribute("transform", `translate(${tx + offsetX}, ${ty})`);
    g.classList.add("show");

    // Text content
    const formula = `dp[${c.fromIdx}]+${c.cost}=${c.total}`;
    g.querySelector("text").textContent = formula;

    // State class — classList.add("") throws DOMException, so skip neutral
    if (c.state !== "show") g.classList.add(c.state);

    // Arrow from source dp cell to candidate badge
    const sourceCellCx = BAR_CENTERS[c.fromIdx];
    const sourceCellCy = DP_ROW_Y;
    const targetBadgeCx = tx + offsetX;
    const targetBadgeCy = ty + 18;
    const midY = (sourceCellCy + targetBadgeCy) / 2;
    const d = `M ${sourceCellCx} ${sourceCellCy} C ${sourceCellCx} ${midY}, ${targetBadgeCx} ${midY}, ${targetBadgeCx} ${targetBadgeCy}`;
    arrow.setAttribute("d", d);
    arrow.classList.add("show");
    if (c.state === "win") arrow.classList.add("win");
    else if (c.state === "lose") arrow.classList.add("lose");
  }

  // --- optimal path overlay ---
  const pathEl = svg.querySelector("#optimalPath");
  if (step.path.length > 1) {
    // Build path through bar tops
    let d = "";
    for (let k = 0; k < step.path.length; k++) {
      const idx = step.path[k];
      const x = BAR_CENTERS[idx];
      const y = barTopY(HEIGHTS[idx]) - 22;
      d += (k === 0 ? "M " : " L ") + x + " " + y;
    }
    pathEl.setAttribute("d", d);
    // Force reflow to restart dashoffset animation
    pathEl.classList.remove("show");
    void pathEl.getBoundingClientRect();
    pathEl.classList.add("show");
  } else {
    pathEl.classList.remove("show");
    pathEl.setAttribute("d", "");
  }

  // --- total badge ---
  const totalG = svg.querySelector("#totalBadge");
  totalG.classList.toggle("show", step.total !== null);
  if (step.total !== null) {
    totalG.querySelector("text").textContent = `= ${step.total}`;
  }
}

// ==========================================================
// Widget controller
// ==========================================================
function initWidget() {
  const widget = document.querySelector(".scriba-diagram-widget");
  const host = document.getElementById("svgHost");
  const progress = document.getElementById("progressBars");
  const total = STEPS.length;
  widget.dataset.stepTotal = total;
  widget.querySelector(".step-counter .total").textContent = total;

  const svg = buildSkeleton(host);

  const counter = widget.querySelector(".step-counter .cur");
  const titleEl = document.getElementById("stepTitle");
  const bodyEl = document.getElementById("stepBody");
  const firstBtn = widget.querySelector('[data-action="first"]');
  const prevBtn = widget.querySelector('[data-action="prev"]');
  const nextBtn = widget.querySelector('[data-action="next"]');
  const lastBtn = widget.querySelector('[data-action="last"]');
  const playBtn = widget.querySelector('[data-action="play"]');
  let timer = null;

  // Build progress bars
  for (let i = 0; i < total; i++) {
    const bar = document.createElement("div");
    bar.className = "bar-seg";
    progress.appendChild(bar);
  }
  const bars = progress.querySelectorAll(".bar-seg");

  function setStep(n) {
    n = Math.max(1, Math.min(total, n));
    widget.dataset.stepCurrent = n;
    counter.textContent = n;
    const step = STEPS[n - 1];
    titleEl.textContent = step.title;
    bodyEl.innerHTML = step.body;
    // Re-run KaTeX on the description
    if (window.renderMathInElement) {
      window.renderMathInElement(bodyEl, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
      });
    }
    render(step, svg);
    bars.forEach((b, i) => b.classList.toggle("done", i < n));
    firstBtn.disabled = n === 1;
    prevBtn.disabled = n === 1;
    nextBtn.disabled = n === total;
    lastBtn.disabled = n === total;
    if (n === total) stopPlay();
  }
  function cur() {
    return parseInt(widget.dataset.stepCurrent, 10);
  }
  function stopPlay() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    playBtn.classList.remove("playing");
    playBtn.textContent = "▶ Play";
  }
  function startPlay() {
    if (cur() === total) setStep(1);
    playBtn.classList.add("playing");
    playBtn.textContent = "⏸ Pause";
    timer = setInterval(() => {
      if (cur() >= total) stopPlay();
      else setStep(cur() + 1);
    }, 2200);
  }

  firstBtn.addEventListener("click", () => {
    stopPlay();
    setStep(1);
  });
  prevBtn.addEventListener("click", () => {
    stopPlay();
    setStep(cur() - 1);
  });
  nextBtn.addEventListener("click", () => {
    stopPlay();
    setStep(cur() + 1);
  });
  lastBtn.addEventListener("click", () => {
    stopPlay();
    setStep(total);
  });
  playBtn.addEventListener("click", () => {
    timer ? stopPlay() : startPlay();
  });

  widget.addEventListener("keydown", (e) => {
    switch (e.key) {
      case "ArrowLeft":
        stopPlay();
        setStep(cur() - 1);
        e.preventDefault();
        break;
      case "ArrowRight":
        stopPlay();
        setStep(cur() + 1);
        e.preventDefault();
        break;
      case "Home":
        stopPlay();
        setStep(1);
        e.preventDefault();
        break;
      case "End":
        stopPlay();
        setStep(total);
        e.preventDefault();
        break;
      case " ":
        timer ? stopPlay() : startPlay();
        e.preventDefault();
        break;
    }
  });

  setStep(1);
}

// Theme toggle
document.getElementById("themeToggle").addEventListener("click", () => {
  const root = document.documentElement;
  root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
});

// Wait for KaTeX auto-render to be available before init (so first-frame math renders)
function whenReady(fn) {
  if (document.readyState === "complete") fn();
  else window.addEventListener("load", fn);
}
whenReady(initWidget);
