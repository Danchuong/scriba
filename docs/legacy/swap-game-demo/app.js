// ==========================================================
// Swap Game tutorial — widgets
// §1 problem grids · §2 halo · §5 ring diagram · §6 BFS trace · §7 replay
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

// Sample grids used across the whole tutorial
const START = [
  [2, 1, 3],
  [7, 5, 9],
  [8, 4, 6],
];
const TARGET = [
  [1, 2, 3],
  [4, 5, 6],
  [7, 8, 9],
];

// ==========================================================
// §1 — Sample problem grids (HTML, not SVG)
// ==========================================================
function buildProblemStatement() {
  const host = document.getElementById("problemStatement");
  if (!host) return;

  const mkGrid = (data, extraClass = "") => {
    const wrap = document.createElement("div");
    const label = document.createElement("div");
    label.className = "sample-label";
    label.textContent = extraClass === "target" ? "target" : "start (sample)";
    const g = document.createElement("div");
    g.className = "sample-grid " + extraClass;
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) {
        const cell = document.createElement("div");
        cell.className = "cell";
        const mismatch = !extraClass && data[r][c] !== TARGET[r][c];
        if (mismatch) cell.classList.add("mismatch");
        cell.textContent = data[r][c];
        g.appendChild(cell);
      }
    }
    wrap.appendChild(g);
    wrap.appendChild(label);
    return wrap;
  };

  host.appendChild(mkGrid(START));
  const arrow = document.createElement("div");
  arrow.className = "sample-arrow";
  arrow.textContent = "→";
  host.appendChild(arrow);
  host.appendChild(mkGrid(TARGET, "target"));
}

// ==========================================================
// §2 — Halo widget: start in center + 12 neighbors around
// ==========================================================
function buildHaloWidget() {
  const host = document.getElementById("haloWidget");
  if (!host) return;

  // All 12 adjacent pairs in a 3x3 grid
  const PAIRS = [];
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 2; c++)
      PAIRS.push([
        [r, c],
        [r, c + 1],
      ]); // horizontal
  }
  for (let c = 0; c < 3; c++) {
    for (let r = 0; r < 2; r++)
      PAIRS.push([
        [r, c],
        [r + 1, c],
      ]); // vertical
  }

  const applySwap = (grid, [[r1, c1], [r2, c2]]) => {
    const g = grid.map((row) => row.slice());
    [g[r1][c1], g[r2][c2]] = [g[r2][c2], g[r1][c1]];
    return g;
  };

  // SVG layout
  const W = 720,
    H = 560;
  const CX = W / 2,
    CY = H / 2;
  const CENTER_CELL = 36,
    CENTER_GAP = 4;
  const MINI_CELL = 18,
    MINI_GAP = 2;
  const CENTER_SIZE = CENTER_CELL * 3 + CENTER_GAP * 2;
  const MINI_SIZE = MINI_CELL * 3 + MINI_GAP * 2;
  const RADIUS = 210;

  const svg = el("svg", {
    class: "halo-svg",
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": "12 neighbors of start state",
  });

  // Center label
  svg.appendChild(
    text("START", {
      x: CX,
      y: CY - CENTER_SIZE / 2 - 12,
      class: "center-label",
    }),
  );

  // Edges layer (drawn first so minis sit on top)
  const edgesG = el("g", { id: "haloEdges" });
  svg.appendChild(edgesG);

  // Center grid
  const centerG = el("g", {
    class: "halo-center",
    transform: `translate(${CX - CENTER_SIZE / 2}, ${CY - CENTER_SIZE / 2})`,
  });
  centerG.appendChild(
    el("rect", {
      class: "bg",
      x: -6,
      y: -6,
      width: CENTER_SIZE + 12,
      height: CENTER_SIZE + 12,
      rx: 8,
    }),
  );
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      const x = c * (CENTER_CELL + CENTER_GAP);
      const y = r * (CENTER_CELL + CENTER_GAP);
      centerG.appendChild(
        el("rect", {
          class: "center-cell",
          "data-cell": `${r}-${c}`,
          x,
          y,
          width: CENTER_CELL,
          height: CENTER_CELL,
        }),
      );
      centerG.appendChild(
        text(String(START[r][c]), {
          class: "center-num",
          "data-cell-num": `${r}-${c}`,
          x: x + CENTER_CELL / 2,
          y: y + CENTER_CELL / 2 + 1,
        }),
      );
    }
  }
  svg.appendChild(centerG);

  // 12 mini grids around
  PAIRS.forEach((pair, idx) => {
    const angle = (idx / PAIRS.length) * 2 * Math.PI - Math.PI / 2;
    const mx = CX + Math.cos(angle) * RADIUS - MINI_SIZE / 2;
    const my = CY + Math.sin(angle) * RADIUS - MINI_SIZE / 2;

    // edge from center to mini
    const cx1 = CX;
    const cy1 = CY;
    const cx2 = mx + MINI_SIZE / 2;
    const cy2 = my + MINI_SIZE / 2;
    edgesG.appendChild(
      el("line", {
        class: "halo-edge",
        "data-edge": idx,
        x1: cx1,
        y1: cy1,
        x2: cx2,
        y2: cy2,
      }),
    );

    const mini = el("g", {
      class: "halo-mini",
      "data-pair": idx,
      transform: `translate(${mx}, ${my})`,
    });
    mini.appendChild(
      el("rect", {
        class: "bg",
        x: -3,
        y: -3,
        width: MINI_SIZE + 6,
        height: MINI_SIZE + 6,
      }),
    );
    const gridAfter = applySwap(START, pair);
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) {
        const x = c * (MINI_CELL + MINI_GAP);
        const y = r * (MINI_CELL + MINI_GAP);
        const swapped = pair.some(([sr, sc]) => sr === r && sc === c);
        mini.appendChild(
          el("rect", {
            class: "mini-cell" + (swapped ? " swapped" : ""),
            x,
            y,
            width: MINI_CELL,
            height: MINI_CELL,
          }),
        );
        mini.appendChild(
          text(String(gridAfter[r][c]), {
            class: "mini-num" + (swapped ? " swapped" : ""),
            x: x + MINI_CELL / 2,
            y: y + MINI_CELL / 2 + 1,
          }),
        );
      }
    }
    svg.appendChild(mini);

    // Hover handlers — highlight center cells + edge
    mini.addEventListener("mouseenter", () => activatePair(pair, idx));
    mini.addEventListener("mouseleave", () => deactivatePair());
    mini.addEventListener("focus", () => activatePair(pair, idx));
    mini.addEventListener("blur", () => deactivatePair());
    mini.setAttribute("tabindex", "0");
  });

  function activatePair(pair, idx) {
    for (const [r, c] of pair) {
      svg.querySelector(`[data-cell="${r}-${c}"]`)?.classList.add("swapped");
      svg.querySelector(`[data-cell-num="${r}-${c}"]`)?.classList.add("swapped");
    }
    svg.querySelector(`.halo-edge[data-edge="${idx}"]`)?.classList.add("active");
  }
  function deactivatePair() {
    svg
      .querySelectorAll(".center-cell.swapped, .center-num.swapped")
      .forEach((n) => n.classList.remove("swapped"));
    svg.querySelectorAll(".halo-edge.active").forEach((n) => n.classList.remove("active"));
  }

  host.appendChild(svg);

  const hint = document.createElement("div");
  hint.className = "halo-hint";
  hint.innerHTML = "↑ Hover hoặc tap vào bất kỳ bảng nhỏ nào để thấy cặp ô đã swap.";
  host.appendChild(hint);
}

// ==========================================================
// §5 — Ring diagram (static): BFS layer expansion
// ==========================================================
function buildRingDiagram() {
  const host = document.getElementById("ringDiagram");
  if (!host) return;

  const W = 640,
    H = 360;
  const CX = W / 2,
    CY = H / 2 + 10;
  const RADII = [0, 55, 100, 140, 180];
  const LAYER_COUNTS = [1, 12, 114, 1086, 8722];

  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": "BFS layer expansion diagram",
  });

  // arrow marker
  const defs = el("defs");
  const marker = el("marker", {
    id: "ringArrow",
    viewBox: "0 0 10 10",
    refX: 9,
    refY: 5,
    markerWidth: 6,
    markerHeight: 6,
    orient: "auto",
  });
  marker.appendChild(
    el("path", {
      d: "M 0 0 L 10 5 L 0 10 z",
      fill: "var(--ok-stroke)",
    }),
  );
  defs.appendChild(marker);
  svg.appendChild(defs);

  // Rings
  for (let k = 1; k < RADII.length; k++) {
    svg.appendChild(
      el("circle", {
        class: `ring ring-${k}`,
        cx: CX,
        cy: CY,
        r: RADII[k],
      }),
    );
  }

  // Layer labels + counts on a radial line
  for (let k = 0; k < RADII.length; k++) {
    const lx = CX - RADII[k] - 16;
    svg.appendChild(
      text(`layer ${k}`, {
        class: "ring-label",
        x: CX,
        y: CY - RADII[k] - 8,
        "text-anchor": "middle",
      }),
    );
    svg.appendChild(
      text(`${LAYER_COUNTS[k].toLocaleString()} states`, {
        class: "ring-count",
        x: CX,
        y: CY - RADII[k] + 14,
      }),
    );
  }

  // Decorative dots for intermediate layers
  const dots = [
    { k: 1, count: 6 },
    { k: 2, count: 10 },
    { k: 3, count: 12 },
  ];
  for (const { k, count } of dots) {
    for (let i = 0; i < count; i++) {
      const ang = (i / count) * 2 * Math.PI + k * 0.3;
      svg.appendChild(
        el("circle", {
          class: "dot inner",
          cx: CX + Math.cos(ang) * RADII[k],
          cy: CY + Math.sin(ang) * RADII[k],
          r: 3,
        }),
      );
    }
  }

  // Start dot (center)
  svg.appendChild(
    el("circle", {
      class: "dot start",
      cx: CX,
      cy: CY,
      r: 6,
    }),
  );

  // Target dot on layer 4
  const tAng = Math.PI * 0.35;
  const tx = CX + Math.cos(tAng) * RADII[4];
  const ty = CY + Math.sin(tAng) * RADII[4];
  svg.appendChild(
    el("circle", {
      class: "dot target",
      cx: tx,
      cy: ty,
      r: 8,
    }),
  );
  svg.appendChild(
    text("target", {
      x: tx + 12,
      y: ty + 4,
      style: "font: 600 11px ui-monospace, monospace; fill: var(--ok-stroke);",
    }),
  );
  svg.appendChild(
    text("start", {
      x: CX,
      y: CY + 22,
      style: "font: 600 11px ui-monospace, monospace; fill: var(--accent);",
      "text-anchor": "middle",
    }),
  );

  // Arrow from start to target passing through layers
  const pathD = `M ${CX} ${CY} Q ${CX + 80} ${CY + 30}, ${tx} ${ty}`;
  svg.appendChild(
    el("path", {
      class: "path-arrow",
      d: pathD,
    }),
  );

  host.appendChild(svg);
}

// ==========================================================
// §6 — BFS trace widget: 5-node graph, step-through
// Nodes: A B C D E   Start=A  Target=E
// Edges: A-B, A-C, B-D, C-D, D-E
// ==========================================================
function buildTraceWidget() {
  const host = document.getElementById("traceWidget");
  if (!host) return;

  const NODES = {
    A: { x: 100, y: 150, dist: 0 },
    B: { x: 220, y: 80, dist: 1 },
    C: { x: 220, y: 220, dist: 1 },
    D: { x: 340, y: 150, dist: 2 },
    E: { x: 460, y: 150, dist: 3 },
  };
  const EDGES = [
    ["A", "B"],
    ["A", "C"],
    ["B", "D"],
    ["C", "D"],
    ["D", "E"],
  ];
  const ADJ = {};
  for (const n of Object.keys(NODES)) ADJ[n] = [];
  for (const [a, b] of EDGES) {
    ADJ[a].push(b);
    ADJ[b].push(a);
  }

  // Trace steps — hand-built to make each moment legible
  // Each step: { current, queue, visited, dist, exploring, skip, title, body }
  // exploring = edge currently being examined (highlighted warn color)
  // skip = {from, to, reason}
  const STEPS = [
    {
      current: null,
      queue: ["A"],
      visited: new Set(["A"]),
      dist: { A: 0 },
      exploring: null,
      skip: null,
      title: "STEP 1 — INIT",
      body: "Khởi tạo: queue = [A], visited = {A}, dist[A] = 0. Target = E.",
    },
    {
      current: "A",
      queue: [],
      visited: new Set(["A"]),
      dist: { A: 0 },
      exploring: null,
      skip: null,
      title: "STEP 2 — POP A",
      body: "Lấy đầu queue: <b>A</b>. A ≠ E. Giờ duyệt neighbor của A.",
    },
    {
      current: "A",
      queue: ["B", "C"],
      visited: new Set(["A", "B", "C"]),
      dist: { A: 0, B: 1, C: 1 },
      exploring: null,
      skip: null,
      title: "STEP 3 — PUSH B, C",
      body: "Neighbor của A: B và C. Cả 2 chưa visited → thêm vào queue và visited. dist[B] = dist[C] = 1. Queue = [B, C].",
    },
    {
      current: "B",
      queue: ["C"],
      visited: new Set(["A", "B", "C"]),
      dist: { A: 0, B: 1, C: 1 },
      exploring: null,
      skip: null,
      title: "STEP 4 — POP B",
      body: "Pop <b>B</b>. Neighbor của B: A và D. A đã visited → skip.",
    },
    {
      current: "B",
      queue: ["C", "D"],
      visited: new Set(["A", "B", "C", "D"]),
      dist: { A: 0, B: 1, C: 1, D: 2 },
      exploring: null,
      skip: null,
      title: "STEP 5 — PUSH D",
      body: "D chưa visited → push D, dist[D] = dist[B] + 1 = 2. Queue = [C, D].",
    },
    {
      current: "C",
      queue: ["D"],
      visited: new Set(["A", "B", "C", "D"]),
      dist: { A: 0, B: 1, C: 1, D: 2 },
      exploring: null,
      skip: { from: "C", to: "D", reason: "D đã visited — skip!" },
      title: "STEP 6 — POP C, TRY D (⚠ DUPLICATE)",
      body: "Pop <b>C</b>. Neighbor: A (visited), D (<b>đã visited</b>!). <b>Không push D</b>. Đây chính là lúc visited set cứu BFS: nếu không có visited, D sẽ được push 2 lần → queue phình ra vô tận.",
    },
    {
      current: "D",
      queue: [],
      visited: new Set(["A", "B", "C", "D"]),
      dist: { A: 0, B: 1, C: 1, D: 2 },
      exploring: null,
      skip: null,
      title: "STEP 7 — POP D",
      body: "Pop <b>D</b>. Neighbor: B (v), C (v), E (chưa). Push E.",
    },
    {
      current: "D",
      queue: ["E"],
      visited: new Set(["A", "B", "C", "D", "E"]),
      dist: { A: 0, B: 1, C: 1, D: 2, E: 3 },
      exploring: null,
      skip: null,
      title: "STEP 8 — PUSH E",
      body: "dist[E] = dist[D] + 1 = 3. Queue = [E].",
    },
    {
      current: "E",
      queue: [],
      visited: new Set(["A", "B", "C", "D", "E"]),
      dist: { A: 0, B: 1, C: 1, D: 2, E: 3 },
      exploring: null,
      skip: null,
      title: "STEP 9 — POP E = TARGET ✓",
      body: "Pop <b>E</b>. E = target! Trả về dist[E] = <b>3</b>. BFS kết thúc. Lưu ý: ta tìm được shortest path <em>mà không cần kiểm tra mọi đường</em> — invariant của BFS đảm bảo điều này.",
    },
  ];

  // Build SVG
  const W = 760,
    H = 340;
  const svgHost = document.createElement("div");
  svgHost.className = "trace-svg-host";
  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": "BFS trace on 5-node graph",
  });

  // arrow marker
  const defs = el("defs");
  const marker = el("marker", {
    id: "traceArrow",
    viewBox: "0 0 10 10",
    refX: 9,
    refY: 5,
    markerWidth: 5,
    markerHeight: 5,
    orient: "auto",
  });
  marker.appendChild(
    el("path", {
      d: "M 0 0 L 10 5 L 0 10 z",
      fill: "var(--muted)",
    }),
  );
  defs.appendChild(marker);
  svg.appendChild(defs);

  // edges layer
  const edgesG = el("g", { id: "edgesG" });
  for (const [a, b] of EDGES) {
    edgesG.appendChild(
      el("line", {
        class: "trace-edge",
        "data-edge": `${a}-${b}`,
        x1: NODES[a].x,
        y1: NODES[a].y,
        x2: NODES[b].x,
        y2: NODES[b].y,
      }),
    );
  }
  svg.appendChild(edgesG);

  // nodes
  for (const [name, pos] of Object.entries(NODES)) {
    const g = el("g", {
      class: "trace-node",
      "data-node": name,
      transform: `translate(${pos.x}, ${pos.y})`,
    });
    if (name === "E") g.classList.add("target");
    g.appendChild(el("circle", { r: 26 }));
    g.appendChild(text(name, { x: 0, y: 2 }));
    // distance label above node
    g.appendChild(
      text("", {
        class: "trace-dist",
        "data-dist-for": name,
        x: 0,
        y: -36,
      }),
    );
    svg.appendChild(g);
  }

  // Duplicate-skip flash
  const skipFlash = el("g", { class: "skip-flash", id: "skipFlash" });
  skipFlash.appendChild(
    el("rect", {
      x: 540,
      y: 20,
      width: 200,
      height: 44,
      rx: 8,
    }),
  );
  skipFlash.appendChild(
    text("⚠ duplicate skipped", {
      x: 640,
      y: 46,
    }),
  );
  svg.appendChild(skipFlash);

  // Queue panel — right side, horizontal
  const Q_X = 560,
    Q_Y = 230,
    Q_SLOT = 42,
    Q_GAP = 6;
  svg.appendChild(
    text("QUEUE (FIFO →)", {
      class: "trace-queue-label",
      x: Q_X,
      y: Q_Y - 14,
    }),
  );
  svg.appendChild(
    text("front ←", {
      class: "queue-caption",
      x: Q_X + 10,
      y: Q_Y + Q_SLOT + 14,
      "text-anchor": "start",
    }),
  );
  svg.appendChild(
    text("→ back", {
      class: "queue-caption",
      x: Q_X + 4 * (Q_SLOT + Q_GAP) - 10,
      y: Q_Y + Q_SLOT + 14,
      "text-anchor": "end",
    }),
  );

  // Pre-create queue slots
  const queueG = el("g", { id: "queueSlots" });
  for (let i = 0; i < 4; i++) {
    const slot = el("g", {
      class: "queue-slot",
      "data-slot": i,
      transform: `translate(${Q_X + i * (Q_SLOT + Q_GAP)}, ${Q_Y})`,
    });
    slot.appendChild(el("rect", { x: 0, y: 0, width: Q_SLOT, height: Q_SLOT }));
    slot.appendChild(text("", { x: Q_SLOT / 2, y: Q_SLOT / 2 + 2 }));
    queueG.appendChild(slot);
  }
  svg.appendChild(queueG);

  svgHost.appendChild(svg);
  host.appendChild(svgHost);

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
    <div class="nar-title" id="traceTitle">STEP 1</div>
    <div class="nar-body" id="traceBody"></div>
  `;
  host.appendChild(narration);

  // Render function
  function render(step) {
    // Nodes state
    for (const name of Object.keys(NODES)) {
      const g = svg.querySelector(`[data-node="${name}"]`);
      g.classList.remove("visited", "current", "inqueue");
      if (name === step.current) g.classList.add("current");
      else if (step.queue.includes(name)) g.classList.add("inqueue");
      else if (step.visited.has(name)) g.classList.add("visited");

      // dist label
      const distEl = svg.querySelector(`[data-dist-for="${name}"]`);
      distEl.textContent = step.dist[name] !== undefined ? `d=${step.dist[name]}` : "";
    }

    // Queue slots
    for (let i = 0; i < 4; i++) {
      const slot = svg.querySelector(`[data-slot="${i}"]`);
      const node = step.queue[i];
      if (node) {
        slot.classList.add("active");
        slot.querySelector("text").textContent = node;
      } else {
        slot.classList.remove("active");
        slot.querySelector("text").textContent = "";
      }
    }

    // Skip flash
    const skipEl = svg.querySelector("#skipFlash");
    skipEl.classList.toggle("show", !!step.skip);
  }

  // Controller
  let cur = 1;
  let timer = null;
  const total = STEPS.length;
  const titleEl = document.getElementById("traceTitle");
  const bodyEl = document.getElementById("traceBody");
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
    if (window.renderMathInElement) {
      window.renderMathInElement(bodyEl, {
        delimiters: [{ left: "$", right: "$", display: false }],
      });
    }
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
    }, 2400);
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
// §7 — Replay widget: 4 optimal swaps on the 3x3 grid
// ==========================================================
function buildReplayWidget() {
  const host = document.getElementById("replayWidget");
  if (!host) return;

  const MOVES = [
    {
      swap: [
        [0, 0],
        [0, 1],
      ],
      note: "swap <b>2 ↔ 1</b> — hàng 1 xong",
    },
    {
      swap: [
        [2, 0],
        [2, 1],
      ],
      note: "swap <b>8 ↔ 4</b> — đưa 4 về cột 0",
    },
    {
      swap: [
        [1, 0],
        [2, 0],
      ],
      note: "swap <b>7 ↔ 4</b> — cột 0 xong",
    },
    {
      swap: [
        [1, 2],
        [2, 2],
      ],
      note: "swap <b>9 ↔ 6</b> — target ✓",
    },
  ];

  // Precompute positions per move state
  const initialPos = () => {
    const p = {};
    for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) p[START[r][c]] = { r, c };
    return p;
  };
  const gridOf = (pos) => {
    const g = [
      [0, 0, 0],
      [0, 0, 0],
      [0, 0, 0],
    ];
    for (const [n, { r, c }] of Object.entries(pos)) g[r][c] = +n;
    return g;
  };
  const POSITIONS = [initialPos()];
  {
    let cur = initialPos();
    for (const mv of MOVES) {
      const next = { ...cur };
      const g = gridOf(cur);
      const [a, b] = mv.swap;
      const na = g[a[0]][a[1]];
      const nb = g[b[0]][b[1]];
      next[na] = { r: b[0], c: b[1] };
      next[nb] = { r: a[0], c: a[1] };
      POSITIONS.push(next);
      cur = next;
    }
  }

  // Steps: pre-move (highlight which cells will swap) + post-move (show state)
  // Keep it simple: 5 snapshots = 1 start + 4 after-move, with swap highlight carried forward.
  const STEPS = [
    {
      posIdx: 0,
      moveCount: 0,
      swapHi: null,
      title: "STEP 1 — START",
      body: "Bảng đầu. Các ô vàng đang sai vị trí.",
    },
    {
      posIdx: 1,
      moveCount: 1,
      swapHi: [
        [0, 0],
        [0, 1],
      ],
      title: "STEP 2 — MOVE 1",
      body: MOVES[0].note,
    },
    {
      posIdx: 2,
      moveCount: 2,
      swapHi: [
        [2, 0],
        [2, 1],
      ],
      title: "STEP 3 — MOVE 2",
      body: MOVES[1].note,
    },
    {
      posIdx: 3,
      moveCount: 3,
      swapHi: [
        [1, 0],
        [2, 0],
      ],
      title: "STEP 4 — MOVE 3",
      body: MOVES[2].note,
    },
    {
      posIdx: 4,
      moveCount: 4,
      swapHi: [
        [1, 2],
        [2, 2],
      ],
      title: "STEP 5 — MOVE 4 = TARGET ✓",
      body: MOVES[3].note + " · Tổng: <b>4 swaps</b>.",
    },
  ];

  // Layout
  const W = 620,
    H = 320;
  const CELL = 72,
    GAP = 8;
  const BOARD_X = 40,
    BOARD_Y = 40;
  const COUNTER_X = 470,
    COUNTER_Y = 150;
  const cellCx = (r, c) => BOARD_X + c * (CELL + GAP) + CELL / 2;
  const cellCy = (r, c) => BOARD_Y + r * (CELL + GAP) + CELL / 2;

  const svgHost = document.createElement("div");
  svgHost.className = "replay-svg-host";
  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": "4-swap optimal solution replay",
  });

  // 9 cells, keyed by number, moved via transform
  for (let n = 1; n <= 9; n++) {
    const g = el("g", { class: "replay-cell", "data-num": n });
    g.appendChild(
      el("rect", {
        x: -CELL / 2,
        y: -CELL / 2,
        width: CELL,
        height: CELL,
        rx: 10,
      }),
    );
    g.appendChild(text(String(n), { x: 0, y: 2 }));
    svg.appendChild(g);
  }

  // Move counter
  const counterG = el("g", { class: "replay-counter", id: "replayCounter" });
  counterG.appendChild(
    text("0", {
      id: "replayCounterNum",
      x: COUNTER_X,
      y: COUNTER_Y,
    }),
  );
  counterG.appendChild(
    text("/ 4 swaps", {
      class: "label",
      x: COUNTER_X,
      y: COUNTER_Y + 28,
    }),
  );
  svg.appendChild(counterG);

  svgHost.appendChild(svg);
  host.appendChild(svgHost);

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
  narration.innerHTML = `<div class="nar-body" id="replayBody"></div>`;
  host.appendChild(narration);

  function render(step) {
    const pos = POSITIONS[step.posIdx];
    const grid = gridOf(pos);
    for (let n = 1; n <= 9; n++) {
      const g = svg.querySelector(`[data-num="${n}"]`);
      const { r, c } = pos[n];
      g.setAttribute("transform", `translate(${cellCx(r, c)}, ${cellCy(r, c)})`);
      g.classList.remove("correct", "wrong", "swap");
      const isSwap = step.swapHi && step.swapHi.some(([sr, sc]) => sr === r && sc === c);
      if (isSwap) g.classList.add("swap");
      else if (grid[r][c] === TARGET[r][c]) g.classList.add("correct");
      else g.classList.add("wrong");
    }
    const counter = svg.querySelector("#replayCounter");
    counter.querySelector("#replayCounterNum").textContent = String(step.moveCount);
    counter.classList.toggle("done", step.moveCount === 4);
  }

  // Controller
  let cur = 1;
  let timer = null;
  const total = STEPS.length;
  const bodyEl = document.getElementById("replayBody");
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
    bodyEl.innerHTML = "<b>" + s.title + "</b> — " + s.body;
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
    }, 1800);
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
// Bootstrap
// ==========================================================
function whenReady(fn) {
  if (document.readyState === "complete") fn();
  else window.addEventListener("load", fn);
}

whenReady(() => {
  buildProblemStatement();
  buildHaloWidget();
  buildRingDiagram();
  buildTraceWidget();
  buildReplayWidget();

  // Theme toggle
  const btn = document.getElementById("themeToggle");
  if (btn) {
    btn.addEventListener("click", () => {
      const root = document.documentElement;
      root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    });
  }
});
