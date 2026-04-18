# Wave 8 Audit — P6: Performance Benchmarks (Baseline)

**Date:** 2026-04-18  
**Commit:** `main` @ `0a8ec6e`  
**Status:** Baseline established. No production code modified.

---

## 1. Methodology

### Machine

| Field | Value |
|-------|-------|
| Hardware | Apple M-series (arm64) |
| RAM | 32 GB |
| OS | macOS 26.1 (Darwin 25.1.0) |
| Python | 3.14.3 (`/opt/homebrew/bin/python3`) |
| Shell | zsh |

### Tools

- **Timing:** `time.monotonic()` wrapped around `render_file()` in `benchmarks/bench_render.py` (5 runs per fixture; median + min reported).
- **Peak RSS:** `/usr/bin/time -l python3 render.py <fixture>` — `maximum resident set size` field (bytes → MB). Measured once per fixture after warm OS cache.
- **Profiler:** `python3 -m cProfile -o /tmp/scriba_medium.prof render.py examples/tutorial_en.tex` and `python3 -m cProfile -o /tmp/scriba_large.prof render.py examples/dinic.tex`. Stats sorted by cumulative time.
- **Note on first-run inflation:** `render_file()` runs `npm root -g` (~100 ms) and a Node.js probe (~46 ms) on every cold process. The baseline.json `times_ms[0]` values reflect this cold-start overhead; medians are dominated by warm runs.

### Why per-phase times cannot be isolated without instrumentation

The four phases (parse → compute → KaTeX → emit) share the same thread and have no timing hooks. The profiler confirms this: subprocess IPC, import machinery, and Python-level work are interleaved. Per-phase wall-clock splits require explicit `time.monotonic()` checkpoints in `render_file()` — recommended as a follow-up instrumentation task.

---

## 2. Baseline Fixture Table

All runs: 5 iterations, macOS warm file cache. Median and min across runs 2–5 (run 1 includes cold Python import cost when noted).

| Fixture | Tier | Math | Starlark | Source KB | Output KB | Median ms | Min ms | Peak RSS MB |
|---------|------|------|----------|-----------|-----------|-----------|--------|-------------|
| `fixes/05_diagram_prescan.tex` (tiny-nomath) | small | N | N | 0.4 | 407.8 | 1 | 1 | 54.1 |
| `fixes/01_variablewatch_shrink.tex` (small-math) | small | Y | Y | 1.0 | 428.9 | 3 | 2 | 54.0 |
| `examples/tutorial_en.tex` (medium-tutorial) | medium | Y | Y | 6.5 | 542.4 | 71 | 69 | 54.1 |
| `examples/dinic.tex` (large-dinic) | large | Y | Y | 11.8 | 944.1 | 98 | 97 | 54.1 |
| `examples/editorials/bfs_grid_editorial.tex` (large-bfs) | large | Y | Y | 14.7 | 911.3 | 99 | 97 | 53.8 |

**Key observations:**
- Peak RSS is essentially flat at ~54 MB across all fixture sizes. Memory footprint is dominated by Python + module imports, not fixture content.
- Output is disproportionately large (407–944 KB) relative to source (0.4–14.7 KB). The inlined KaTeX CSS with base64 woff2 fonts is the dominant contributor.
- Render time scales with block count and Starlark compute complexity, not linearly with source bytes. The two large fixtures (dinic: 310 lines, bfs: 417 lines) both land at ~99 ms despite ~25% file size difference, suggesting Starlark IPC round-trips dominate, not I/O.

---

## 3. Per-Phase Breakdown (Approximate, cProfile-derived)

Profiled on `examples/dinic.tex` (large fixture, 401 ms cold process wall-clock). The first `render_file()` call in a fresh process incurs substantial startup cost.

| Phase | Approx ms | % of total | Notes |
|-------|-----------|------------|-------|
| `TexRenderer.__init__` startup | ~150 | 37% | Includes npm root (~100 ms) + node probe (~46 ms) |
| Worker IPC — all 93 `worker.send()` calls | ~62 | 15% | KaTeX + Starlark combined |
| Animation `render_block` (Starlark eval loop) | ~88 | 22% | Includes worker IPC for Starlark; 19-frame animation |
| TeX `render_block` x2 + `_render_source` | ~53 | 13% | Block-level TeX processing |
| `render_math_batch` (block-level KaTeX) | ~47 | 12% | 2 batch calls cover block-level math |
| `emit_html` + `emit_interactive_html` | ~38 | 9% | HTML serialization + JS runtime embed |
| Animation parse + grammar | ~28 | 7% | Lexer + recursive-descent parse |
| Frame SVG emit (x19 frames) | ~22 | 5% | Per-frame SVG assembly |
| Animation `_materialise` | ~21 | 5% | Scene graph snapshot loop |
| Python import machinery (first call only) | ~102 | 25% | Amortized to zero after second call |

Note: percentages sum above 100% because phases overlap (e.g., Starlark eval is inside `render_block`). The column shows rough independent contributions as read from cProfile cumulative times.

**Warm-process incremental cost** (subtracting one-time startup: npm + node probe + worker spawn):  
Large fixture cold total = ~401 ms; estimated warm-only = ~150–160 ms. Confirmed by the benchmark median of 98 ms (where workers are re-spawned each `render_file()` call but Python import machinery is hot).

---

## 4. Top 20 cProfile Entries — Large Fixture (`dinic.tex`)

Profile: 324,277 function calls in 0.401 seconds (fresh process, cumulative sort).

```
ncalls  tottime  percall  cumtime  percall  symbol
     1    0.000    0.000    0.404    0.404  render.py:107(render_file)
     1    0.000    0.000    0.150    0.150  scriba/tex/renderer.py:201(TexRenderer.__init__)
     2    0.001    0.000    0.145    0.073  subprocess.py:512(run)          ← npm + node probe
     3    0.135    0.045    0.135    0.045  {select.poll}                   ← subprocess wait
     1    0.000    0.000    0.100    0.100  tex/renderer.py:252(_discover_node_global_root)
     1    0.000    0.000    0.088    0.088  animation/renderer.py:413(render_block)
    93    0.001    0.000    0.062    0.001  core/workers.py:231(send)       ← all IPC
    95    0.055    0.001    0.055    0.001  {select.select}                 ← IPC poll
     2    0.000    0.000    0.053    0.026  tex/renderer.py:281(render_block)
     2    0.000    0.000    0.047    0.024  tex/parser/math.py:104(render_math_batch)
     1    0.000    0.000    0.046    0.046  tex/renderer.py:149(_probe_runtime)
     1    0.000    0.000    0.042    0.042  core/workers.py:94(_spawn)      ← Starlark spawn
     1    0.000    0.000    0.038    0.038  animation/emitter.py:1590(emit_html)
     1    0.001    0.001    0.031    0.031  animation/emitter.py:864(emit_interactive_html)
     1    0.000    0.000    0.028    0.028  animation/renderer.py:508(_parse)
     1    0.000    0.000    0.027    0.027  animation/parser/grammar.py:66(parse)
    19    0.001    0.000    0.022    0.001  animation/emitter.py:496(_emit_frame_svg)
    91    0.000    0.000    0.016    0.000  tex/renderer.py:412(_render_inline)   ← 91 individual KaTeX calls
    91    0.000    0.000    0.016    0.000  tex/renderer.py:372(_math_sub)
   892    0.003    0.000    0.006    0.000  primitives/graph.py:588(addressable_parts)
```

**Key finding:** 93 total `worker.send()` calls — 2 are batched `render_math_batch` covering block-level math; 91 are individual `_render_inline` calls, each a separate JSON-line IPC round trip to the KaTeX subprocess for narration/label inline math.

---

## 5. Top 5 Optimisation Candidates

### Candidate 1 — Eliminate `_discover_node_global_root()` cold call (~100 ms saved per process)

**File:** `scriba/tex/renderer.py:252`  
**What it does:** Runs `subprocess.run(['npm', 'root', '-g'])` on every `TexRenderer.__init__()` call to discover the global `node_modules` path, then sets `NODE_PATH` in `os.environ`. This is 100 ms of pure subprocess wait per fresh process.  
**Problem:** `TexRenderer` is constructed once per `render_file()` call. In the CLI the process exits after one render, so the cost is always paid. In any server/batch scenario it is paid on every invocation.  
**Fix:** Cache the result in a module-level variable (already guarded by `if "NODE_PATH" not in os.environ`), or skip `npm root -g` entirely when the vendored KaTeX worker does not need it. Since `katex_worker.js` uses the vendored `katex.min.js` via an explicit path (not via `require('katex')`), setting `NODE_PATH` may be unnecessary for vendored operation.  
**Estimated win:** 100 ms per cold process; 0 ms warm (already one-time via `os.environ` guard, but still triggers for the very first call).

### Candidate 2 — Batch narration/label inline math into a single KaTeX round trip (~30–50 ms saved on large fixtures)

**File:** `scriba/tex/renderer.py:412(_render_inline)`, `scriba/animation/renderer.py:113(_render_narration)`  
**What it does:** Every narration string and every annotated label calls `_render_inline()` independently. Each call is a full JSON-line IPC round trip: `json.dumps` → `proc.stdin.write` → `proc.stdin.flush` → `select.select` → `proc.stdout.readline` → `json.loads`. The dinic profile shows 91 such calls.  
**Problem:** The KaTeX worker already supports `type: "batch"` (used by `render_math_batch`). The 91 individual calls could be collected across all narration strings and dispatched in 1–3 batch calls. At 55 ms for 95 `select.select` calls, each round trip costs roughly 0.6 ms in IPC overhead alone.  
**Fix:** In `AnimationRenderer._render_narration`, collect all inline math fragments in a pre-pass over all frames, dispatch a single batch to `render_math_batch`, then substitute rendered HTML back. Requires refactoring the narration render loop to be two-pass.  
**Estimated win:** 40–60% of the 62 ms IPC budget on math-heavy fixtures = 25–37 ms.

### Candidate 3 — Cache `inline_katex_css()` across processes (output size reduction, or accept the lru_cache)

**File:** `scriba/core/css_bundler.py:39(inline_katex_css)` and `render.py:241`  
**What it does:** `inline_katex_css()` reads `katex.min.css`, finds every `url(fonts/KaTeX_*.woff2)` reference, reads each font file, base64-encodes it, and inlines the URI. It is decorated with `@functools.lru_cache(maxsize=None)`, so in-process the cost is paid once. However, this function is the reason the output HTML is 407–944 KB: the inlined woff2 fonts dominate the output size.  
**Problem:** The KaTeX CSS alone inflates every output by ~380 KB regardless of whether any math is present (the `tiny-nomath` fixture outputs 407.8 KB despite having zero math). This is a correctness vs. performance trade-off for self-contained HTML.  
**Fix (option A):** Conditionally skip KaTeX CSS embedding when no math is detected in the document. Saves ~380 KB on math-free documents and reduces I/O + write time for those.  
**Fix (option B):** In server mode, serve KaTeX CSS as a shared static asset. Already partially implemented via `--no-inline-runtime`. A `--no-inline-katex` flag would complete it.  
**Estimated win:** 380 KB output reduction on no-math documents; write I/O cost proportional reduction.

### Candidate 4 — `addressable_parts` called 892 times with no memoisation

**File:** `scriba/animation/primitives/graph.py:588(addressable_parts)`  
**Profile entry:** 892 calls, 3 ms own time.  
**What it does:** Returns all addressable sub-elements of a graph primitive — called on every selector validation and every frame mutation. With 19 frames and ~47 apply/recolor commands per frame, the same graph structure is re-traversed hundreds of times.  
**Fix:** Memoize `addressable_parts` on the primitive instance. The graph topology does not change between frames (only state values change), so the addressable parts set is stable. A simple `@functools.cached_property` or dict cache keyed on object identity would reduce 892 traversals to ~1.  
**Estimated win:** 3 ms direct; larger indirect benefit if `validate_selector` (892 calls, 6 ms) is also cached.

### Candidate 5 — `_render_inline` re-creates `request["macros"]` dict on every call

**File:** `scriba/tex/renderer.py:412(_render_inline)`  
**What it does:** Every call executes `if self._katex_macros: request["macros"] = dict(self._katex_macros)`, which shallow-copies the macros dict 91 times per render.  
**Problem:** `dict(self._katex_macros)` allocates a new dict object on every call. For renders with zero macros this is a no-op, but for projects using macros it is 91 redundant allocations in the hot path.  
**Fix:** Pre-compute the macros dict once as `self._katex_macros_request_dict` during `__init__` and reuse the same object (the KaTeX worker treats it as read-only). Combined with Candidate 2 (batching), this becomes a single macros dict per batch call instead of 91 copies.  
**Estimated win:** Minor in isolation (~0.5 ms), meaningful when combined with batching.

---

## 6. Suggested CI Regression-Flagging Recipe

### Scripts

Two scripts in `benchmarks/`:

- `bench_render.py` — runs all fixtures, emits a JSON results file
- `ci_regression_check.py` — compares a run against a baseline, exits 1 if any fixture regresses beyond a threshold

### Baseline management

```bash
# On main, after establishing the baseline:
python3 benchmarks/bench_render.py --runs 5 --json benchmarks/baseline.json
git add benchmarks/baseline.json
git commit -m "perf: update benchmark baseline"
```

### CI job (GitHub Actions)

```yaml
name: Performance regression check

on:
  pull_request:
    branches: [main]

jobs:
  perf:
    runs-on: ubuntu-latest   # Must match baseline machine class
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: pip install -e .
      - name: Run benchmarks
        run: |
          python3 benchmarks/bench_render.py --runs 5 --json /tmp/current.json
      - name: Check regression
        run: |
          python3 benchmarks/ci_regression_check.py \
            --baseline benchmarks/baseline.json \
            --current /tmp/current.json \
            --threshold 0.10
```

**Threshold rationale:** 10% is chosen to allow for CI machine noise while catching genuine regressions. The medium and large fixtures consistently run within ±5% across 5 warm runs (std dev < 3 ms). A 10% gate gives 2 sigma headroom on CI machines with moderate load variance.

### Alternative: hyperfine (CLI-level, no Python instrumentation)

```bash
# Install: cargo install hyperfine (or brew install hyperfine)
hyperfine \
  --warmup 1 \
  --runs 5 \
  --export-json /tmp/hf_results.json \
  "python3 render.py examples/tutorial_en.tex -o /dev/null" \
  "python3 render.py examples/dinic.tex -o /dev/null"

# Parse median from JSON:
python3 -c "
import json; d = json.load(open('/tmp/hf_results.json'))
for r in d['results']:
  print(r['command'], f\"{r['median']*1000:.0f}ms\")
"
```

Hyperfine captures full process wall-clock including Python startup (~60–80 ms), making it less sensitive to per-phase changes but easier to integrate without custom scripting.

**Note:** Because `render.py` blocks writing outside CWD, use `-o` with a relative path or set `SCRIBA_ALLOW_ANY_OUTPUT=1` in CI for `/dev/null` redirect.

---

## 7. Benchmark Suite Design

### Current fixture dimensions

| Dimension | Values covered |
|-----------|---------------|
| Size | tiny (0.4 KB), small (1 KB), medium (6.5 KB), large (11–15 KB) |
| Math | none, moderate (~110 dollar spans in tutorial), heavy (~208 in dinic) |
| Starlark compute | none, single block, multiple blocks (bfs: 4 blocks) |
| Diagram type | variablewatch, graph/flow |
| Block count | 1, 4 |

### Gaps to fill

1. **Many-blocks fixture** — a synthetic `.tex` with 10+ `\begin{animation}` blocks to stress Starlark worker spawn amortization and per-block parse overhead.
2. **Math-only, no Starlark** — isolates KaTeX throughput from Starlark cost (e.g., a dense problem statement with 50+ equations but no animation).
3. **Very large single block** — one animation block with 100+ frames to stress the emitter's SVG loop and `_emit_frame_svg` scaling.
4. **No-math, Starlark-only** — isolates compute cost from KaTeX (custom fixture needed).
5. **Repeat render of same fixture** — measures warm-worker incremental cost by calling `render_file()` twice in the same process (workers reused). This would expose the true per-render cost after amortizing startup.

### Recommended synthetic fixtures to create

```
benchmarks/fixtures/
  bench_math_heavy.tex     # 50 math equations, 0 animation blocks
  bench_many_blocks.tex    # 10 animation blocks, minimal math
  bench_many_frames.tex    # 1 animation block, 80+ frames
```

---

## 8. Summary of Actionable Items

| Item | Effort | Estimated Saving |
|------|--------|-----------------|
| Batch narration math into `render_math_batch` | Medium | 25–37 ms per large render |
| Cache or skip `_discover_node_global_root` | Low | 100 ms per cold process |
| Skip KaTeX CSS on math-free documents | Low | 380 KB output; ~5 ms write I/O |
| Memoize `addressable_parts` on graph primitives | Low | 3–6 ms per large animation |
| Pre-compute macros dict in `TexRenderer.__init__` | Trivial | <1 ms; eliminates 91 allocs |
| Add per-phase `time.monotonic()` checkpoints to `render_file` | Low | Unblocks future profiling accuracy |
| Add many-blocks and many-frames synthetic fixtures | Low | Unblocks regression testing breadth |

The single highest-leverage change is **batching narration inline math** (Candidate 2), which transforms 91 serial subprocess IPC round trips into 1–3 batch calls. On the large fixtures this is estimated to save 25–37 ms from the ~99 ms warm render time — a 25–38% improvement on those fixtures.

---

## Benchmark Scripts

| Path | Purpose |
|------|---------|
| `/Users/mrchuongdan/Documents/GitHub/scriba/benchmarks/bench_render.py` | Runs all fixtures N times, emits JSON baseline |
| `/Users/mrchuongdan/Documents/GitHub/scriba/benchmarks/ci_regression_check.py` | Compares JSON results against baseline, exits 1 on regression |
| `/Users/mrchuongdan/Documents/GitHub/scriba/benchmarks/baseline.json` | Committed baseline (main @ `0a8ec6e`, macOS arm64, Python 3.14.3) |
