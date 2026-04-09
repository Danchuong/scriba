// ==========================================================
// Swap Game v2 — single widget (BFS trace) + scroll spy + expert toggle
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
// BFS trace widget — 5-node graph A,B,C,D,E
// ==========================================================
function buildTraceWidget() {
  const host = document.getElementById("traceWidget");
  if (!host) return;

  const NODES = {
    A: { x: 100, y: 150 },
    B: { x: 220, y: 80 },
    C: { x: 220, y: 220 },
    D: { x: 340, y: 150 },
    E: { x: 460, y: 150 },
  };
  const EDGES = [
    ["A", "B"],
    ["A", "C"],
    ["B", "D"],
    ["C", "D"],
    ["D", "E"],
  ];

  // Hand-built BFS trace
  const STEPS = [
    {
      current: null,
      queue: ["A"],
      visited: new Set(["A"]),
      dist: { A: 0 },
      skip: false,
      title: "STEP 1 — INIT",
      body: "Khởi tạo: queue = [A], visited = {A}, dist[A] = 0. Mục tiêu: tìm đường ngắn nhất từ A đến E.",
    },
    {
      current: "A",
      queue: [],
      visited: new Set(["A"]),
      dist: { A: 0 },
      skip: false,
      title: "STEP 2 — POP A",
      body: "Lấy đầu queue: <b>A</b>. A ≠ E. Giờ duyệt neighbor của A: B và C.",
    },
    {
      current: "A",
      queue: ["B", "C"],
      visited: new Set(["A", "B", "C"]),
      dist: { A: 0, B: 1, C: 1 },
      skip: false,
      title: "STEP 3 — PUSH B, C",
      body: "Cả 2 chưa visited → thêm vào queue và visited. dist[B] = dist[C] = 1. Queue = [B, C].",
    },
    {
      current: "B",
      queue: ["C"],
      visited: new Set(["A", "B", "C"]),
      dist: { A: 0, B: 1, C: 1 },
      skip: false,
      title: "STEP 4 — POP B",
      body: "Pop <b>B</b>. Neighbor: A (đã visited → skip), D (chưa). Sẽ push D.",
    },
    {
      current: "B",
      queue: ["C", "D"],
      visited: new Set(["A", "B", "C", "D"]),
      dist: { A: 0, B: 1, C: 1, D: 2 },
      skip: false,
      title: "STEP 5 — PUSH D",
      body: "dist[D] = dist[B] + 1 = 2. Queue = [C, D].",
    },
    {
      current: "C",
      queue: ["D"],
      visited: new Set(["A", "B", "C", "D"]),
      dist: { A: 0, B: 1, C: 1, D: 2 },
      skip: true,
      title: "STEP 6 — POP C, TRY D ⚠ DUPLICATE",
      body: "Pop <b>C</b>. Neighbor: A (v), D (<b>đã visited!</b>). <b>KHÔNG push D nữa</b>. Đây chính là lúc visited cứu BFS — nếu không có visited, D sẽ bị push 2 lần và queue phình ra vô tận.",
    },
    {
      current: "D",
      queue: [],
      visited: new Set(["A", "B", "C", "D"]),
      dist: { A: 0, B: 1, C: 1, D: 2 },
      skip: false,
      title: "STEP 7 — POP D",
      body: "Pop <b>D</b>. Neighbor: B (v), C (v), E (chưa). Sẽ push E.",
    },
    {
      current: "D",
      queue: ["E"],
      visited: new Set(["A", "B", "C", "D", "E"]),
      dist: { A: 0, B: 1, C: 1, D: 2, E: 3 },
      skip: false,
      title: "STEP 8 — PUSH E",
      body: "dist[E] = dist[D] + 1 = 3. Queue = [E].",
    },
    {
      current: "E",
      queue: [],
      visited: new Set(["A", "B", "C", "D", "E"]),
      dist: { A: 0, B: 1, C: 1, D: 2, E: 3 },
      skip: false,
      title: "STEP 9 — POP E = TARGET ✓",
      body: "Pop <b>E</b>. E = target! Trả về dist[E] = <b>3</b>. BFS kết thúc, đáp án = 3.",
    },
  ];

  const W = 700,
    H = 320;
  const svgHostDiv = document.createElement("div");
  svgHostDiv.className = "trace-svg-host";
  const svg = el("svg", {
    viewBox: `0 0 ${W} ${H}`,
    role: "img",
    "aria-label": "BFS trace on 5-node graph",
  });

  // edges
  for (const [a, b] of EDGES) {
    svg.appendChild(
      el("line", {
        class: "trace-edge",
        x1: NODES[a].x,
        y1: NODES[a].y,
        x2: NODES[b].x,
        y2: NODES[b].y,
      }),
    );
  }
  // nodes
  for (const [name, pos] of Object.entries(NODES)) {
    const g = el("g", {
      class: "trace-node",
      "data-node": name,
      transform: `translate(${pos.x}, ${pos.y})`,
    });
    if (name === "E") g.classList.add("target");
    g.appendChild(el("circle", { r: 24 }));
    g.appendChild(text(name, { x: 0, y: 2 }));
    g.appendChild(
      text("", {
        class: "trace-dist",
        "data-dist-for": name,
        x: 0,
        y: -34,
      }),
    );
    svg.appendChild(g);
  }

  // Skip flash
  const skipFlash = el("g", { class: "skip-flash", id: "skipFlash" });
  skipFlash.appendChild(el("rect", { x: 530, y: 14, width: 160, height: 36 }));
  skipFlash.appendChild(text("⚠ duplicate skipped", { x: 610, y: 36 }));
  svg.appendChild(skipFlash);

  // Queue panel
  const Q_X = 540,
    Q_Y = 230,
    Q_SLOT = 38,
    Q_GAP = 6;
  svg.appendChild(
    text("QUEUE (FIFO →)", {
      class: "trace-queue-label",
      x: Q_X,
      y: Q_Y - 12,
    }),
  );
  for (let i = 0; i < 4; i++) {
    const slot = el("g", {
      class: "queue-slot",
      "data-slot": i,
      transform: `translate(${Q_X + i * (Q_SLOT + Q_GAP)}, ${Q_Y})`,
    });
    slot.appendChild(el("rect", { x: 0, y: 0, width: Q_SLOT, height: Q_SLOT }));
    slot.appendChild(text("", { x: Q_SLOT / 2, y: Q_SLOT / 2 + 1 }));
    svg.appendChild(slot);
  }

  svgHostDiv.appendChild(svg);
  host.appendChild(svgHostDiv);

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

  function render(step) {
    for (const name of Object.keys(NODES)) {
      const g = svg.querySelector(`[data-node="${name}"]`);
      g.classList.remove("visited", "current", "inqueue");
      if (name === step.current) g.classList.add("current");
      else if (step.queue.includes(name)) g.classList.add("inqueue");
      else if (step.visited.has(name)) g.classList.add("visited");
      const dEl = svg.querySelector(`[data-dist-for="${name}"]`);
      dEl.textContent = step.dist[name] !== undefined ? `d=${step.dist[name]}` : "";
    }
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
    svg.querySelector("#skipFlash").classList.toggle("show", step.skip);
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
    }, 2200);
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
// Scroll spy — highlight active anchor chip
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
// Expert mode toggle
// ==========================================================
function initExpertToggle() {
  const toggle = document.getElementById("expertToggle");
  if (!toggle) return;

  // Restore from localStorage
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
  buildTraceWidget();
  initScrollSpy();
  initExpertToggle();
  initThemeToggle();
});
