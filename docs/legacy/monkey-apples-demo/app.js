// ==========================================================
// Monkey and Apple-trees — Segtree lazy propagation widget
// Demonstrates sparse segtree + lazy on range [0, 7]
// ==========================================================

const SVG_NS = "http://www.w3.org/2000/svg";
function el(name, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined) continue;
    node.setAttribute(k, v);
  }
  for (const c of children) if (c) node.appendChild(c);
  return node;
}
function text(content, attrs = {}) {
  const t = el("text", attrs);
  t.textContent = content;
  return t;
}

// ==========================================================
// Tree structure — full binary tree over [0, 7], 15 nodes
// Node id 1 = root (binary heap numbering)
// ==========================================================
const NODES = {
  1: { range: [0, 7], level: 0 },
  2: { range: [0, 3], level: 1 },
  3: { range: [4, 7], level: 1 },
  4: { range: [0, 1], level: 2 },
  5: { range: [2, 3], level: 2 },
  6: { range: [4, 5], level: 2 },
  7: { range: [6, 7], level: 2 },
  8: { range: [0, 0], level: 3 },
  9: { range: [1, 1], level: 3 },
  10: { range: [2, 2], level: 3 },
  11: { range: [3, 3], level: 3 },
  12: { range: [4, 4], level: 3 },
  13: { range: [5, 5], level: 3 },
  14: { range: [6, 6], level: 3 },
  15: { range: [7, 7], level: 3 },
};

// Layout: 4 levels, root at top
const VB_W = 820,
  VB_H = 460;
const LEVEL_Y = [50, 140, 230, 320];
const NODE_W = 84,
  NODE_H = 52;

// x positions by level (spread across width)
const LEVEL_X = {
  0: [VB_W / 2],
  1: [VB_W * 0.28, VB_W * 0.72],
  2: [VB_W * 0.14, VB_W * 0.38, VB_W * 0.62, VB_W * 0.86],
  3: [
    VB_W * 0.06,
    VB_W * 0.18,
    VB_W * 0.3,
    VB_W * 0.42,
    VB_W * 0.58,
    VB_W * 0.7,
    VB_W * 0.82,
    VB_W * 0.94,
  ],
};
// Map node id -> (x, y)
const NODE_POS = {};
for (const [idStr, info] of Object.entries(NODES)) {
  const id = +idStr;
  const level = info.level;
  // Index within its level
  const firstAtLevel = Math.pow(2, level); // 1, 2, 4, 8
  const idx = id - firstAtLevel;
  NODE_POS[id] = { x: LEVEL_X[level][idx], y: LEVEL_Y[level] };
}

// Parent-child edges
const EDGES = [];
for (let id = 1; id <= 7; id++) {
  EDGES.push([id, id * 2]);
  EDGES.push([id, id * 2 + 1]);
}

// ==========================================================
// Step definitions — hand-built trace
// Each step: { allocated: {id: {freq, lazy}}, highlight: {id: 'walk'|'apply'|'push'|'contained'|'skip'|'new'}, opLabel, title, body }
// ==========================================================
const STEPS = [
  // -------- Step 1: INIT --------
  {
    allocated: { 1: { freq: 0, lazy: 0 } },
    highlight: {},
    opLabel: "",
    title: "STEP 1 — INIT",
    body: "Cây sparse: chỉ có root [0,7] được cấp phát. Tất cả 14 node còn lại chưa tồn tại (mờ). Tổng số cây chín = 0.",
  },

  // -------- Step 2: range_set(2, 5, 1) starts --------
  {
    allocated: { 1: { freq: 0, lazy: 0 } },
    highlight: { 1: "walk" },
    opLabel: "range_set([2, 5], 1) — đánh dấu các cây 2..5 chín đỏ",
    title: "STEP 2 — BẮT ĐẦU range_set(2, 5)",
    body: "Gọi range_set từ root [0,7]. Kiểm tra: [0,7] <b>không nằm trọn</b> trong [2,5] → phải <b>push_down</b> và recurse xuống 2 con.",
  },

  // -------- Step 3: push_down at root creates children 2, 3 --------
  {
    allocated: {
      1: { freq: 0, lazy: 0 },
      2: { freq: 0, lazy: 0 },
      3: { freq: 0, lazy: 0 },
    },
    highlight: { 1: "walk", 2: "new", 3: "new" },
    opLabel: "range_set([2, 5], 1)",
    title: "STEP 3 — TẠO CON L [0,3] VÀ R [4,7]",
    body: "push_down ở root tạo 2 con L=[0,3] và R=[4,7] (cả 2 đều rỗng, lazy=0). Giờ recurse vào từng con.",
  },

  // -------- Step 4: descend to L, then apply lazy at LR [2,3] --------
  {
    allocated: {
      1: { freq: 0, lazy: 0 },
      2: { freq: 0, lazy: 0 },
      3: { freq: 0, lazy: 0 },
      4: { freq: 0, lazy: 0 },
      5: { freq: 2, lazy: 1 },
    },
    highlight: { 1: "walk", 2: "walk", 4: "skip", 5: "apply" },
    opLabel: "range_set([2, 5], 1)",
    title: "STEP 4 — APPLY LAZY TẠI [2,3]",
    body: "Ở L [0,3]: con trái LL [0,1] <b>rời</b> với [2,5] → bỏ qua. Con phải LR [2,3] <b>nằm trọn</b> trong [2,5] → <b>treo lazy=1, freq=2</b>, dừng. KHÔNG đi xuống tạo LRL, LRR.",
  },

  // -------- Step 5: descend to R, apply lazy at RL [4,5] --------
  {
    allocated: {
      1: { freq: 0, lazy: 0 },
      2: { freq: 0, lazy: 0 },
      3: { freq: 0, lazy: 0 },
      4: { freq: 0, lazy: 0 },
      5: { freq: 2, lazy: 1 },
      6: { freq: 2, lazy: 1 },
      7: { freq: 0, lazy: 0 },
    },
    highlight: { 1: "walk", 3: "walk", 6: "apply", 7: "skip" },
    opLabel: "range_set([2, 5], 1)",
    title: "STEP 5 — APPLY LAZY TẠI [4,5]",
    body: "Ở R [4,7]: con trái RL [4,5] <b>nằm trọn</b> → <b>treo lazy=1, freq=2</b>. Con phải RR [6,7] <b>rời</b> → bỏ qua. Cả update chỉ chạm 5 node — không xuống lá.",
  },

  // -------- Step 6: set complete, recompute freq up --------
  {
    allocated: {
      1: { freq: 4, lazy: 0 },
      2: { freq: 2, lazy: 0 },
      3: { freq: 2, lazy: 0 },
      4: { freq: 0, lazy: 0 },
      5: { freq: 2, lazy: 1 },
      6: { freq: 2, lazy: 1 },
      7: { freq: 0, lazy: 0 },
    },
    highlight: {},
    opLabel: "Sau range_set: total = 4 cây chín",
    title: "STEP 6 — UPDATE XONG",
    body: 'Recompute freq từ dưới lên: L.freq=0+2=2, R.freq=2+0=2, root.freq=2+2=4. <b>Lazy vẫn còn ở LR và RL</b> như "nợ" chờ push xuống. Cây chỉ có 7 node — tiết kiệm hơn tạo full 15 node.',
  },

  // -------- Step 7: range_sum(3, 6) starts --------
  {
    allocated: {
      1: { freq: 4, lazy: 0 },
      2: { freq: 2, lazy: 0 },
      3: { freq: 2, lazy: 0 },
      4: { freq: 0, lazy: 0 },
      5: { freq: 2, lazy: 1 },
      6: { freq: 2, lazy: 1 },
      7: { freq: 0, lazy: 0 },
    },
    highlight: { 1: "walk" },
    opLabel: "range_sum([3, 6]) — đếm cây chín trong [3, 6]",
    title: "STEP 7 — BẮT ĐẦU range_sum(3, 6)",
    body: "Gọi range_sum từ root. [0,7] không trọn trong [3,6] → recurse xuống L và R.",
  },

  // -------- Step 8: push_down at LR creates children with lazy --------
  {
    allocated: {
      1: { freq: 4, lazy: 0 },
      2: { freq: 2, lazy: 0 },
      3: { freq: 2, lazy: 0 },
      4: { freq: 0, lazy: 0 },
      5: { freq: 2, lazy: 1 }, // lazy not reset in this problem (only set=1)
      6: { freq: 2, lazy: 1 },
      7: { freq: 0, lazy: 0 },
      10: { freq: 1, lazy: 1 },
      11: { freq: 1, lazy: 1 },
    },
    highlight: { 2: "walk", 5: "push", 10: "new", 11: "new" },
    opLabel: "range_sum([3, 6])",
    title: "STEP 8 — PUSH_DOWN TẠI LR",
    body: 'Ở L: con LL [0,1] rời → bỏ qua. Con LR [2,3] không trọn (chỉ có 3 thuộc [3,6]) → phải <b>push_down</b>. Lazy=1 được truyền xuống 2 con mới sinh: LRL [2,2] (freq=1, lazy=1), LRR [3,3] (freq=1, lazy=1). Đây là lúc lazy "trả nợ".',
  },

  // -------- Step 9: sum complete, highlight contributing nodes --------
  {
    allocated: {
      1: { freq: 4, lazy: 0 },
      2: { freq: 2, lazy: 0 },
      3: { freq: 2, lazy: 0 },
      4: { freq: 0, lazy: 0 },
      5: { freq: 2, lazy: 1 },
      6: { freq: 2, lazy: 1 },
      7: { freq: 0, lazy: 0 },
      10: { freq: 1, lazy: 1 },
      11: { freq: 1, lazy: 1 },
      14: { freq: 0, lazy: 0 },
      15: { freq: 0, lazy: 0 },
    },
    highlight: { 11: "contained", 6: "contained", 14: "contained" },
    opLabel: "Kết quả: 1 + 2 + 0 = 3 cây chín",
    title: "STEP 9 — TRUY VẤN XONG: KẾT QUẢ = 3",
    body: "Các node đóng góp (xanh): LRR [3,3]=1 (3 chín), RL [4,5]=2 (4,5 chín), RRL [6,6]=0 (6 chưa chín). <b>Tổng = 3</b>. Cây cuối có 11 node thay vì 15 — sparse!",
  },
];

// ==========================================================
// Build widget
// ==========================================================
function buildSegtreeWidget() {
  const host = document.getElementById("segtreeWidget");
  if (!host) return;

  const svgHostDiv = document.createElement("div");
  svgHostDiv.className = "segtree-svg-host";
  const svg = el("svg", {
    viewBox: `0 0 ${VB_W} ${VB_H}`,
    role: "img",
    "aria-label": "Segment tree lazy propagation demo",
  });

  // Op label at bottom (above controls)
  svg.appendChild(
    text("", {
      class: "op-label",
      id: "opLabel",
      x: VB_W / 2,
      y: VB_H - 10,
    }),
  );

  // Edges first
  for (const [parent, child] of EDGES) {
    const p = NODE_POS[parent];
    const c = NODE_POS[child];
    svg.appendChild(
      el("line", {
        class: "seg-edge",
        "data-edge": `${parent}-${child}`,
        x1: p.x,
        y1: p.y + NODE_H / 2,
        x2: c.x,
        y2: c.y - NODE_H / 2,
      }),
    );
  }

  // Nodes
  for (const [idStr, info] of Object.entries(NODES)) {
    const id = +idStr;
    const { x, y } = NODE_POS[id];
    const g = el("g", {
      class: "seg-node",
      "data-node": id,
      transform: `translate(${x}, ${y})`,
    });
    g.appendChild(
      el("rect", {
        x: -NODE_W / 2,
        y: -NODE_H / 2,
        width: NODE_W,
        height: NODE_H,
      }),
    );
    g.appendChild(
      text(`[${info.range[0]},${info.range[1]}]`, {
        class: "range",
        x: 0,
        y: -10,
      }),
    );
    g.appendChild(
      text("0", {
        class: "freq",
        "data-freq-for": id,
        x: 0,
        y: 11,
      }),
    );

    // Lazy badge (orange circle with "L" in top-right corner)
    const lazy = el("g", {
      class: "lazy-badge",
      "data-lazy-for": id,
      transform: `translate(${NODE_W / 2 - 6}, ${-NODE_H / 2 + 6})`,
    });
    lazy.appendChild(el("circle", { r: 8 }));
    lazy.appendChild(text("L", { x: 0, y: 0 }));
    g.appendChild(lazy);

    svg.appendChild(g);
  }

  svgHostDiv.appendChild(svg);
  host.appendChild(svgHostDiv);

  // Controls
  const controls = document.createElement("div");
  controls.className = "controls";
  controls.innerHTML = `
    <button data-action="first" aria-label="First">⏮</button>
    <button data-action="prev" aria-label="Prev">◀</button>
    <button data-action="play" aria-label="Play">▶ Play</button>
    <button data-action="next" aria-label="Next">▶</button>
    <button data-action="last" aria-label="Last">⏭</button>
    <span class="counter">Step <span class="cur">1</span> / ${STEPS.length}</span>
  `;
  host.appendChild(controls);

  const narration = document.createElement("div");
  narration.className = "narration";
  narration.innerHTML = `
    <div class="nar-title" id="segTitle">STEP 1</div>
    <div class="nar-body" id="segBody"></div>
  `;
  host.appendChild(narration);

  // ----- Render -----
  function render(step) {
    for (const idStr of Object.keys(NODES)) {
      const id = +idStr;
      const g = svg.querySelector(`[data-node="${id}"]`);
      g.classList.remove("hidden", "walk", "apply", "push", "contained", "skip", "new");

      const alloc = step.allocated[id];
      if (!alloc) {
        g.classList.add("hidden");
      } else {
        const hl = step.highlight[id];
        if (hl) g.classList.add(hl);
      }

      // Update freq text
      const freqEl = g.querySelector(`[data-freq-for="${id}"]`);
      freqEl.textContent = alloc ? String(alloc.freq) : "0";

      // Lazy badge
      const lazyBadge = g.querySelector(`[data-lazy-for="${id}"]`);
      lazyBadge.classList.toggle("show", !!(alloc && alloc.lazy));
    }

    // Edges: hide edges where child is not allocated
    for (const [parent, child] of EDGES) {
      const edge = svg.querySelector(`[data-edge="${parent}-${child}"]`);
      const parentAlloc = step.allocated[parent];
      const childAlloc = step.allocated[child];
      edge.classList.toggle("hidden", !parentAlloc || !childAlloc);
    }

    svg.querySelector("#opLabel").textContent = step.opLabel;
  }

  // ----- Controller -----
  let cur = 1;
  let timer = null;
  const total = STEPS.length;
  const titleEl = document.getElementById("segTitle");
  const bodyEl = document.getElementById("segBody");
  const curSpan = host.querySelector(".counter .cur");
  const prevBtn = host.querySelector('[data-action="prev"]');
  const nextBtn = host.querySelector('[data-action="next"]');
  const firstBtn = host.querySelector('[data-action="first"]');
  const lastBtn = host.querySelector('[data-action="last"]');
  const playBtn = host.querySelector('[data-action="play"]');

  function setStep(n) {
    n = Math.max(1, Math.min(total, n));
    cur = n;
    curSpan.textContent = n;
    const s = STEPS[n - 1];
    titleEl.textContent = s.title;
    bodyEl.innerHTML = s.body;
    render(s);
    prevBtn.disabled = n === 1;
    firstBtn.disabled = n === 1;
    nextBtn.disabled = n === total;
    lastBtn.disabled = n === total;
    if (n === total) stopPlay();
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
    if (cur === total) setStep(1);
    playBtn.classList.add("playing");
    playBtn.textContent = "⏸ Pause";
    timer = setInterval(() => {
      if (cur >= total) stopPlay();
      else setStep(cur + 1);
    }, 2600);
  }

  firstBtn.addEventListener("click", () => {
    stopPlay();
    setStep(1);
  });
  prevBtn.addEventListener("click", () => {
    stopPlay();
    setStep(cur - 1);
  });
  nextBtn.addEventListener("click", () => {
    stopPlay();
    setStep(cur + 1);
  });
  lastBtn.addEventListener("click", () => {
    stopPlay();
    setStep(total);
  });
  playBtn.addEventListener("click", () => {
    timer ? stopPlay() : startPlay();
  });

  setStep(1);
}

// ==========================================================
// Scroll spy
// ==========================================================
function initScrollSpy() {
  const chips = document.querySelectorAll(".chip-strip .chip");
  const targets = Array.from(chips)
    .map((chip) => {
      const id = chip.getAttribute("href").slice(1);
      return { chip, target: document.getElementById(id) };
    })
    .filter((t) => t.target);

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          chips.forEach((c) => {
            c.classList.toggle("active", c.getAttribute("href") === "#" + id);
          });
        }
      });
    },
    { rootMargin: "-30% 0px -55% 0px" },
  );

  targets.forEach(({ target }) => observer.observe(target));
}

// ==========================================================
// Expert toggle
// ==========================================================
function initExpertToggle() {
  const toggle = document.getElementById("expertToggle");
  if (!toggle) return;
  const saved = localStorage.getItem("expertMode") === "1";
  toggle.checked = saved;
  document.body.classList.toggle("expert", saved);
  toggle.addEventListener("change", () => {
    document.body.classList.toggle("expert", toggle.checked);
    toggle.setAttribute("aria-pressed", String(toggle.checked));
    localStorage.setItem("expertMode", toggle.checked ? "1" : "0");
  });
}

// ==========================================================
// Theme toggle
// ==========================================================
function initThemeToggle() {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
  });
}

// ==========================================================
// Bootstrap
// ==========================================================
function whenReady(fn) {
  if (document.readyState === "complete") fn();
  else window.addEventListener("load", fn);
}

whenReady(() => {
  buildSegtreeWidget();
  initScrollSpy();
  initExpertToggle();
  initThemeToggle();
});
