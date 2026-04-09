// ==========================================================
// Swap Game v3 — visualization-first editorial
// Runs BFS on REAL 3x3 input: [3,1,2,4,5,6,7,8,9] → target
// ==========================================================

const NS = "http://www.w3.org/2000/svg";
const el = (n, a = {}, c = []) => {
  const e = document.createElementNS(NS, n);
  for (const [k, v] of Object.entries(a)) if (v != null) e.setAttribute(k, v);
  for (const ch of c) if (ch) e.appendChild(ch);
  return e;
};
const txt = (s, a = {}) => {
  const t = el("text", a);
  t.textContent = s;
  return t;
};

// ==========================================================
// Shared: mini 3x3 grid renderer
// ==========================================================
const CELL = 24;
const GAP = 2;
function gridSize(c = CELL) {
  return 3 * c + 2 * GAP;
}

function renderMiniGrid(host, state, opts = {}) {
  const c = opts.cell || CELL;
  const size = 3 * c + 2 * GAP;
  // clear
  while (host.firstChild) host.removeChild(host.firstChild);
  host.setAttribute("data-size", size);
  for (let i = 0; i < 9; i++) {
    const r = Math.floor(i / 3),
      col = i % 3;
    const x = col * (c + GAP);
    const y = r * (c + GAP);
    const rect = el("rect", {
      x,
      y,
      width: c,
      height: c,
      rx: 3,
      class:
        "cell-bg" +
        (opts.target && state[i] === i + 1 ? " target" : "") +
        (opts.highlight && opts.highlight.includes(i) ? " hl" : ""),
    });
    host.appendChild(rect);
    host.appendChild(
      txt(state[i], {
        x: x + c / 2,
        y: y + c / 2 + 5,
        class: "cell-txt",
        "font-size": Math.round(c * 0.55),
      }),
    );
  }
  return size;
}

// Standalone SVG helper for figures that need <svg> wrapper
function makeGridSvg(state, opts = {}) {
  const c = opts.cell || CELL;
  const size = 3 * c + 2 * GAP;
  const svg = el("svg", {
    viewBox: `0 0 ${size} ${size}`,
    width: opts.width || size,
    height: opts.height || size,
  });
  renderMiniGrid(svg, state, opts);
  return svg;
}

// ==========================================================
// Problem constants
// ==========================================================
const START = [3, 1, 2, 4, 5, 6, 7, 8, 9];
const TARGET = [1, 2, 3, 4, 5, 6, 7, 8, 9];
const EDGES = [
  [0, 1],
  [1, 2],
  [3, 4],
  [4, 5],
  [6, 7],
  [7, 8],
  [0, 3],
  [1, 4],
  [2, 5],
  [3, 6],
  [4, 7],
  [5, 8],
];
const keyOf = (s) => s.join("");
const swap = (s, i, j) => {
  const t = s.slice();
  [t[i], t[j]] = [t[j], t[i]];
  return t;
};
const eq = (a, b) => keyOf(a) === keyOf(b);

// After swap(0,1): [1,3,2,4,5,6,7,8,9]
const STATE_A = swap(START, 0, 1);

// ==========================================================
// §2 Problem figure — fill in grids + edge overlay
// ==========================================================
function buildProblemFig() {
  for (const g of document.querySelectorAll('[data-grid="start"]')) renderMiniGrid(g, START);
  for (const g of document.querySelectorAll('[data-grid="target"]'))
    renderMiniGrid(g, TARGET, { target: true });
  // edges grid: show abstract numbers + edge overlays
  const edgesG = document.querySelector('[data-grid="edges"]');
  if (edgesG) {
    renderMiniGrid(edgesG, [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  }
  // draw 12 edges on top
  const overlay = document.getElementById("edgeOverlay");
  if (overlay) {
    const off = { x: 0, y: 0 }; // relative to the parent <g translate>
    for (const [i, j] of EDGES) {
      const ri = Math.floor(i / 3),
        ci = i % 3;
      const rj = Math.floor(j / 3),
        cj = j % 3;
      const x1 = ci * (CELL + GAP) + CELL / 2;
      const y1 = ri * (CELL + GAP) + CELL / 2;
      const x2 = cj * (CELL + GAP) + CELL / 2;
      const y2 = rj * (CELL + GAP) + CELL / 2;
      overlay.appendChild(el("line", { x1, y1, x2, y2, class: "edge-line" }));
    }
  }
}

// ==========================================================
// §4 Insight figure — BFS layers 0/1/2 from start
// ==========================================================
function buildInsightFig() {
  const host = document.getElementById("insightLayers");
  if (!host) return;
  // Layer 0: start. Layer 1: A (the one on optimal path) + 2 others. Layer 2: target.
  const layers = [
    { depth: 0, states: [{ s: START, px: 60 }], color: "start" },
    {
      depth: 1,
      states: [
        { s: STATE_A, px: 60 },
        { s: swap(START, 1, 2), px: 150 },
        { s: swap(START, 0, 3), px: 240 },
      ],
      color: "mid",
    },
    {
      depth: 2,
      states: [{ s: TARGET, px: 60 }],
      color: "target",
    },
  ];
  const COLX = [90, 280, 480];
  const NODE_W = 70,
    NODE_H = 70;

  // depth labels
  COLX.forEach((x, i) => {
    host.appendChild(txt(`depth ${i}`, { x, y: 220, class: "layer-depth" }));
  });

  // nodes + path
  const layer1A = { cx: COLX[1], cy: 60 };
  const layer0 = { cx: COLX[0], cy: 100 };
  const layer2 = { cx: COLX[2], cy: 100 };

  // path edges (start → A → target)
  host.appendChild(
    el("line", {
      x1: layer0.cx + 25,
      y1: layer0.cy,
      x2: layer1A.cx - 25,
      y2: layer1A.cy + 10,
      class: "layer-edge path",
    }),
  );
  host.appendChild(
    el("line", {
      x1: layer1A.cx + 25,
      y1: layer1A.cy + 10,
      x2: layer2.cx - 25,
      y2: layer2.cy,
      class: "layer-edge path",
    }),
  );
  // non-path edges from start to other layer-1 siblings (dashed/faded)
  host.appendChild(
    el("line", {
      x1: layer0.cx + 28,
      y1: layer0.cy,
      x2: COLX[1] - 28,
      y2: 110,
      class: "layer-edge",
    }),
  );
  host.appendChild(
    el("line", {
      x1: layer0.cx + 28,
      y1: layer0.cy,
      x2: COLX[1] - 28,
      y2: 160,
      class: "layer-edge",
    }),
  );
  // "… 12 total" caption at layer-1 column
  host.appendChild(
    txt("… (12 total)", {
      x: COLX[1],
      y: 195,
      class: "layer-lbl",
    }),
  );

  function plaque(cx, cy, state, cls) {
    // plaque rect is 56x56 centered at (cx, cy)
    // inner grid: cell=14 → raw size 3*14+4 = 46. Centered inside by offset 5.
    const g = el("g", {
      transform: `translate(${cx - 28}, ${cy - 28})`,
    });
    g.appendChild(
      el("rect", {
        x: 0,
        y: 0,
        width: 56,
        height: 56,
        rx: 6,
        class: "layer-node " + (cls || ""),
      }),
    );
    const grid = el("g", { transform: "translate(5,5)" });
    renderMiniGrid(grid, state, { cell: 14, target: eq(state, TARGET) });
    g.appendChild(grid);
    host.appendChild(g);
  }
  plaque(layer0.cx, layer0.cy, START, "start");
  plaque(layer1A.cx, 60, STATE_A);
  plaque(layer1A.cx, 110, swap(START, 1, 2));
  plaque(layer1A.cx, 160, swap(START, 0, 3));
  plaque(layer2.cx, 100, TARGET, "target");
}

// ==========================================================
// §6 Walkthrough mini-grids
// ==========================================================
function buildWalkFigs() {
  const map = {
    walk0: START,
    walk1: STATE_A,
    walk1b: STATE_A,
    walk2: TARGET,
  };
  for (const [k, s] of Object.entries(map)) {
    for (const g of document.querySelectorAll(`[data-grid="${k}"]`)) {
      renderMiniGrid(g, s, k === "walk2" ? { target: true } : {});
    }
  }
}

// ==========================================================
// §1 Hero viz — animated solution playback
// ==========================================================
function buildHero() {
  const host = document.getElementById("heroViz");
  if (!host) return;
  const SOLUTION = [START, STATE_A, TARGET];
  const HL = [
    [0, 1], // first swap
    [1, 2], // second swap
    [],
  ];
  const svg = el("svg", {
    viewBox: "0 0 220 220",
    width: 220,
    height: 220,
  });
  const gridG = el("g", { transform: "translate(26, 26)" });
  svg.appendChild(gridG);
  host.appendChild(svg);
  const label = document.getElementById("heroSwapLabel");

  let i = 0;
  function frame() {
    renderMiniGrid(gridG, SOLUTION[i], {
      cell: 52,
      highlight: HL[i],
      target: i === 2,
    });
    if (label) {
      label.textContent = i < 2 ? `Swap ${i + 1} / 2` : "Sorted ✓ (2 swaps, optimal)";
    }
  }
  frame();
  let timer = setInterval(() => {
    i = (i + 1) % SOLUTION.length;
    frame();
  }, 1600);

  document.getElementById("heroReplay").addEventListener("click", () => {
    clearInterval(timer);
    i = 0;
    frame();
    timer = setInterval(() => {
      i = (i + 1) % SOLUTION.length;
      frame();
    }, 1600);
  });
}

// ==========================================================
// §5 BFS widget — interactive, runs on real input
// ==========================================================
function buildBfsWidget() {
  const host = document.getElementById("bfsWidget");
  if (!host) return;

  // Pre-compute neighbors of START in EDGE order
  const N0 = EDGES.map(([i, j]) => ({
    state: swap(START, i, j),
    edge: [i, j],
  }));
  // Neighbors of A (STATE_A) in EDGE order — target is swap(1,2) on A
  const NA = EDGES.map(([i, j]) => ({
    state: swap(STATE_A, i, j),
    edge: [i, j],
  }));
  const TARGET_IDX_IN_NA = EDGES.findIndex(([i, j]) => {
    const t = swap(STATE_A, i, j);
    return eq(t, TARGET);
  });

  const STEPS = [
    {
      title: "STEP 1 — INIT",
      body: "<code>queue = [(start, d=0)]</code>, <code>seen = {start}</code>. Chưa có gì xảy ra, chỉ khởi tạo.",
      current: null,
      queue: [{ state: START, d: 0 }],
      codeLines: [6, 7],
      predict: null,
    },
    {
      title: "STEP 2 — POP start",
      body: "Pop phần tử đầu queue: <code>(3,1,2,…)</code> ở <code>d=0</code>. Queue rỗng tạm thời.",
      current: { state: START, d: 0 },
      queue: [],
      codeLines: [9],
      predict: null,
    },
    {
      title: "STEP 3 — CHECK TARGET",
      body: "<code>start ≠ target</code>. Không return. Chuyển sang expand.",
      current: { state: START, d: 0 },
      queue: [],
      codeLines: [10],
      predict: null,
    },
    {
      title: "STEP 4 — EXPAND (12 neighbors)",
      body: "Duyệt qua 12 edge, sinh 12 state mới. Tất cả chưa có trong <code>seen</code> ⇒ push hết vào queue với <code>d=1</code>. Queue giờ có 12 phần tử.",
      current: { state: START, d: 0 },
      queue: N0.map((n) => ({ state: n.state, d: 1 })),
      codeLines: [11, 12, 13, 14, 15, 16, 17],
      predict: null,
    },
    {
      title: "STEP 5 — POP neighbor #1",
      body: "Pop đầu queue: <code>(1,3,2,…)</code> (kết quả của swap(0,1)) ở <code>d=1</code>. 11 phần tử còn lại.",
      current: { state: STATE_A, d: 1 },
      queue: N0.slice(1).map((n) => ({ state: n.state, d: 1 })),
      codeLines: [9],
      predict: null,
    },
    {
      title: "STEP 6 — BẠN ĐOÁN XEM",
      body: "Chúng ta sắp expand state <code>(1,3,2,4,5,6,7,8,9)</code>. Một trong 12 neighbor của nó chính là target. <strong>Edge nào?</strong>",
      current: { state: STATE_A, d: 1 },
      queue: N0.slice(1).map((n) => ({ state: n.state, d: 1 })),
      codeLines: [11],
      predict: {
        prompt: "Swap nào trên (1,3,2,…) cho ra (1,2,3,…)?",
        options: [
          { label: "edge (0,1) — 2 ô trên cùng", idx: 0 },
          { label: "edge (1,2) — ô giữa & phải trên", idx: 1 },
          { label: "edge (3,4) — hàng giữa trái", idx: 2 },
          { label: "edge (0,3) — cột 1", idx: 6 },
        ],
        correct: TARGET_IDX_IN_NA,
        explain: "Swap ô (0,1)=3 với ô (0,2)=2 → hàng đầu thành 1,2,3. Đó chính là target.",
      },
    },
    {
      title: "STEP 7 — PUSH target",
      body: "Expand A. Khi tới edge (1,2): swap cho <code>(1,2,3,4,5,6,7,8,9)</code> = target. Chưa có trong seen ⇒ push với <code>d=2</code>.",
      current: { state: STATE_A, d: 1 },
      queue: [
        ...N0.slice(1).map((n) => ({ state: n.state, d: 1 })),
        { state: TARGET, d: 2, isTarget: true },
      ],
      codeLines: [15, 16, 17],
      predict: null,
    },
    {
      title: "STEP 8 — ...cho tới khi pop target",
      body: "BFS tiếp tục pop các state ở depth 1 (không có state nào trong đó = target). Cuối cùng pop <code>(1,2,3,…)</code> ở <code>d=2</code>. <code>s == target</code> ⇒ <strong>return 2</strong>. Hoàn tất.",
      current: { state: TARGET, d: 2, done: true },
      queue: [],
      codeLines: [10],
      predict: null,
    },
  ];

  // Build DOM
  host.innerHTML = `
    <div class="widget-grid">
      <div class="widget-panel">
        <h3>Current state</h3>
        <div class="current-state" id="curState"></div>
        <div class="meta-row"><span class="k">depth</span><span class="v" id="curDepth">—</span></div>
        <div class="meta-row"><span class="k">seen size</span><span class="v" id="seenSize">0</span></div>
      </div>
      <div class="widget-panel">
        <h3>Queue (FIFO →)</h3>
        <div class="queue-list" id="queueList"></div>
      </div>
    </div>
    <div class="controls">
      <button data-a="first">⏮</button>
      <button data-a="prev">◀ Prev</button>
      <button data-a="next" class="primary">Next ▶</button>
      <button data-a="last">⏭</button>
      <span class="counter">Step <span id="curStep">1</span> / ${STEPS.length}</span>
    </div>
    <div class="predict hidden" id="predictBox"></div>
    <div class="narration">
      <div class="nar-title" id="narTitle"></div>
      <div class="nar-body" id="narBody"></div>
    </div>
  `;

  const curStateHost = host.querySelector("#curState");
  const curDepth = host.querySelector("#curDepth");
  const seenSize = host.querySelector("#seenSize");
  const queueList = host.querySelector("#queueList");
  const curStepLbl = host.querySelector("#curStep");
  const narTitle = host.querySelector("#narTitle");
  const narBody = host.querySelector("#narBody");
  const predictBox = host.querySelector("#predictBox");

  // seen sizes per step (precomputed)
  const SEEN_SIZES = [1, 1, 1, 13, 13, 13, 14, 14];

  function render(n) {
    const s = STEPS[n];
    curStepLbl.textContent = n + 1;
    narTitle.textContent = s.title;
    narBody.innerHTML = s.body;

    // current state svg
    while (curStateHost.firstChild) curStateHost.removeChild(curStateHost.firstChild);
    if (s.current) {
      const svg = makeGridSvg(s.current.state, {
        cell: 32,
        target: eq(s.current.state, TARGET),
      });
      curStateHost.appendChild(svg);
      curDepth.textContent = "d = " + s.current.d;
    } else {
      const svg = makeGridSvg(START, { cell: 32 });
      svg.style.opacity = 0.35;
      curStateHost.appendChild(svg);
      curDepth.textContent = "—";
    }
    seenSize.textContent = SEEN_SIZES[n];

    // queue
    queueList.innerHTML = "";
    const maxShow = 12;
    s.queue.slice(0, maxShow).forEach((q, i) => {
      const item = document.createElement("div");
      item.className =
        "queue-item" + (i === 0 ? " head" : "") + (q.isTarget ? " target-found" : "");
      const svg = makeGridSvg(q.state, {
        cell: 14,
        target: eq(q.state, TARGET),
      });
      item.appendChild(svg);
      const d = document.createElement("div");
      d.className = "d";
      d.textContent = "d=" + q.d;
      item.appendChild(d);
      queueList.appendChild(item);
    });
    if (s.queue.length > maxShow) {
      const more = document.createElement("div");
      more.className = "queue-item";
      more.style.justifyContent = "center";
      more.style.minWidth = "40px";
      more.innerHTML =
        '<div class="d" style="font-size:10px">+' + (s.queue.length - maxShow) + "</div>";
      queueList.appendChild(more);
    }

    // predict box
    if (s.predict) {
      predictBox.classList.remove("hidden");
      predictBox.innerHTML = `
        <div><strong>🔮 ${s.predict.prompt}</strong></div>
        <div class="predict-options">
          ${s.predict.options
            .map((o) => `<button data-idx="${o.idx}">${o.label}</button>`)
            .join("")}
        </div>
        <div class="predict-result" id="predictResult"></div>
      `;
      const result = predictBox.querySelector("#predictResult");
      predictBox.querySelectorAll("button").forEach((b) => {
        b.addEventListener("click", () => {
          const idx = Number(b.dataset.idx);
          if (idx === s.predict.correct) {
            result.textContent = "✓ Đúng! " + s.predict.explain;
            result.className = "predict-result right";
          } else {
            result.textContent = "✗ Chưa đúng. Thử lại, hoặc next để xem đáp án.";
            result.className = "predict-result wrong";
          }
        });
      });
    } else {
      predictBox.classList.add("hidden");
      predictBox.innerHTML = "";
    }

    // code sync
    document
      .querySelectorAll("#codeBlock span[data-line]")
      .forEach((sp) => sp.classList.remove("active"));
    (s.codeLines || []).forEach((ln) => {
      const sp = document.querySelector(`#codeBlock span[data-line="${ln}"]`);
      if (sp) sp.classList.add("active");
    });
  }

  let cur = 0;
  const total = STEPS.length;
  function go(n) {
    cur = Math.max(0, Math.min(total - 1, n));
    render(cur);
    host.querySelector('[data-a="prev"]').disabled = cur === 0;
    host.querySelector('[data-a="first"]').disabled = cur === 0;
    host.querySelector('[data-a="next"]').disabled = cur === total - 1;
    host.querySelector('[data-a="last"]').disabled = cur === total - 1;
  }
  host.querySelector('[data-a="first"]').addEventListener("click", () => go(0));
  host.querySelector('[data-a="prev"]').addEventListener("click", () => go(cur - 1));
  host.querySelector('[data-a="next"]').addEventListener("click", () => go(cur + 1));
  host.querySelector('[data-a="last"]').addEventListener("click", () => go(total - 1));
  go(0);

  // Expose for code-click sync: map code line → step
  const LINE_TO_STEP = {
    6: 0,
    7: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 3,
    13: 3,
    14: 3,
    15: 6,
    16: 6,
    17: 6,
  };
  document.querySelectorAll("#codeBlock span[data-line]").forEach((sp) => {
    sp.addEventListener("click", () => {
      const ln = Number(sp.dataset.line);
      if (LINE_TO_STEP[ln] != null) go(LINE_TO_STEP[ln]);
    });
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
  buildProblemFig();
  buildInsightFig();
  buildWalkFigs();
  buildHero();
  buildBfsWidget();
});
