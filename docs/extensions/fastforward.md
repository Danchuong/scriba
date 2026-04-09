# Extension E3 — `\fastforward{N}{sample_every=K, ...}` Meta-step

> **Status:** Accepted extension to `04-environments-spec.md`. This document
> specifies the `\fastforward` command, which runs a Starlark simulation loop
> for many iterations and emits a sampled subset as filmstrip frames.
>
> Cross-references: `04-environments-spec.md` §3.3 (`\step`), §5 (Starlark host
> and worker contract), §6.3 (frame count limits), §8.1 (HTML output shape);
> `00-ARCHITECTURE-DECISION-2026-04-09.md` E3 and coverage row #9.

---

## 1. Purpose

Iterative heuristics such as simulated annealing, local search, and gradient
descent require 10^4–10^6 iterations before any structure is visible. A naïve
one-`\step`-per-iteration approach is both too slow to render and too large to
transmit. `\fastforward` solves this by delegating the iteration loop to the
Starlark worker, running it at full speed (subject to raised resource limits),
and surfacing only N sampled frames as standard filmstrip steps. The filmstrip
consumer is unaware that the frames came from a fast-forward loop.

### HARD-TO-DISPLAY problem unlocked

| # | Problem | How `\fastforward` helps |
|---|---------|--------------------------|
| 9 | Simulated Annealing | Run 10^4+ iterations in the worker; sample every K-th state as one frame; pair with `MetricPlot` showing energy and temperature curves |

`\fastforward` is also useful for iterative DP convergence demonstrations (e.g.
Bellman-Ford relaxations on a dense graph) and genetic algorithm population
evolution.

---

## 2. Grammar / BNF

`\fastforward` is an inner command, valid **only inside `\begin{animation}`**,
positioned in the same location as `\step` (between frames, never inside a step
block). It may not appear in `\begin{diagram}` (E1345).

```
fastforward_cmd  ::= "\fastforward" "{" total_iters "}" "{" ff_params "}"
                     ff_narrate_cmd?

total_iters      ::= NUMBER     (* positive integer, 1 ≤ total_iters ≤ 10^6 *)

ff_params        ::= ff_param ("," ff_param)*
ff_param         ::= "sample_every" "=" NUMBER
                   | "seed"         "=" NUMBER
                   | "label"        "=" STRING    (* optional: label prefix for steps *)

ff_narrate_cmd   ::= "\narrate" "{" balanced_text "}"
                 (*  narrate is OPTIONAL for fastforward; if omitted, each frame
                     gets an auto-generated narration using substitution below   *)
```

### 2.1 Required and optional parameters

| Parameter      | Required | Type    | Default | Constraint                     |
|----------------|----------|---------|---------|--------------------------------|
| `sample_every` | Yes      | int     | —       | ≥ 1; `total_iters / sample_every` ≤ 100 (E1341) |
| `seed`         | Yes      | int     | —       | Any integer; must be explicit (E1342) |
| `label`        | No       | string  | `"ff"`  | Used as prefix for auto-generated step ids |

`N` (the number of emitted frames) is computed as:
```
N = floor(total_iters / sample_every)
```
If `N == 0`, that is a compile-time error (total_iters < sample_every).
If `N > 100`, that is E1341.

### 2.2 Position in animation body

`\fastforward` may appear anywhere that `\step` is allowed. It expands into
exactly `N` sequential `\step` frames during compilation. The frame counter
advances by `N` after a `\fastforward`. Frame numbering is contiguous with
preceding manual `\step` frames.

Example with mixed manual steps and fastforward:

```latex
\begin{animation}[id=sa-demo]
\shape{...}
\compute{...}

\step                             % frame 1: initial state
\narrate{Initial tour.}

\fastforward{10000}{sample_every=500, seed=42}  % frames 2–21 (20 frames)
\narrate{Iter ${iter}: cost=${cost}.}

\step                             % frame 22: final state
\narrate{Converged.}
\end{animation}
```

---

## 3. Starlark callback contract

`\fastforward` requires the author to define an `iterate` function in a preceding
`\compute` block. The function is called by the worker for each iteration.

### 3.1 Callback signature

```python
# In \compute block (before \fastforward)
def iterate(scene, rng):
    """
    scene : dict  — the current scene state (mutable key-value store).
                    Keys are string identifiers; values are any Starlark type.
                    The host pre-populates `scene` with all global bindings
                    visible at the point of the \fastforward command.
    rng   : RNG   — seeded random number generator (see §4).
    Returns: the mutated scene dict (or None to leave scene unchanged).
    """
    ...
    return scene
```

If `iterate` is not defined in the accessible scope at the point of the
`\fastforward` command, the error is E1343.

### 3.2 State snapshot sampling

The worker calls `iterate(scene, rng)` exactly `total_iters` times. Before the
first call (iteration 0) and after iterations `sample_every`, `2 * sample_every`,
... (up to `N * sample_every`), the worker takes a **snapshot** of the scene dict.
This produces `N + 1` snapshots (including iteration 0). The emitted filmstrip
frames are snapshots 1 through `N` (snapshot 0 is the initial state accessible to
the preceding manual step, if any).

The snapshot is a deep-copy of the scene dict taken at that iteration. Snapshot
data is serialised over the worker wire protocol as part of the per-frame binding
set (same JSON protocol as `\compute` responses, `04-environments-spec.md` §5.5).

### 3.3 Bindings available in narration and `\apply`/`\recolor` after `\fastforward`

For each sampled frame k (1-indexed):

| Binding name    | Type    | Value |
|-----------------|---------|-------|
| `frame_idx`     | int     | k (1 to N) |
| `iter`          | int     | k * sample_every |
| `scene`         | dict    | The snapshot dict at iteration `iter` |
| `*scene`        | —       | All top-level keys in `scene` are splatted into the frame scope. A key `cost` in `scene` is accessible as `${cost}` in narration. |

Splat happens after all global bindings to avoid name shadowing of non-scene globals.
If a scene key conflicts with a global binding, the scene key wins (frame scope beats global scope, per `04-environments-spec.md` §5.3).

### 3.4 Frame `\apply` / `\recolor` within fastforward

There is no per-frame `\apply` / `\recolor` block inside a `\fastforward` — all
frames in the fast-forward run share the same visual state delta template:
**whatever state the scene dict implies at the snapshot time**.

Authors can express conditional state transitions by storing state flags in the
scene dict and using `\compute` blocks after `\fastforward` for per-step overrides:

```latex
\fastforward{10000}{sample_every=500, seed=42}
\narrate{Iter ${iter}: cost=${cost}.}
% After fastforward: manual per-step overrides if needed
```

If per-frame `\apply` is needed, the author should use manual `\step` blocks with
per-step `\compute` calls. `\fastforward` is for fast bulk iteration, not for
frames that require custom SVG mutations.

---

## 4. Seeded RNG

### 4.1 Worker-provided `rng` object

Scriba injects an `rng` object into the Starlark environment before calling
`iterate`. The `rng` object has the following methods:

| Method                     | Return type | Description |
|----------------------------|-------------|-------------|
| `rng.random()`             | float       | Uniform float in [0.0, 1.0) |
| `rng.randint(lo, hi)`      | int         | Uniform integer in [lo, hi] inclusive |
| `rng.uniform(lo, hi)`      | float       | Uniform float in [lo, hi) |
| `rng.shuffle(lst)`         | None        | Shuffles list in place |
| `rng.choice(lst)`          | any         | Returns a random element |

The `rng` object is seeded with `seed` at the start of the `\fastforward`
execution, before the first call to `iterate`. The seed is reset to `seed` at the
start of each compilation run, ensuring byte-identical HTML for identical source.

Authors MUST use `rng` for all randomness inside `iterate`. Because Starlark
forbids `import` (`04-environments-spec.md` §5.1), Python's `random` module is
inaccessible anyway.

### 4.2 RNG implementation

The host implements the RNG using a PCG64 generator (or equivalent well-tested
PRNG) with 64-bit state. The exact generator is an implementation detail;
**what is specified here is the interface and the seed contract**. The
implementation MUST document its PRNG choice in `07-starlark-worker.md`.

---

## 5. Worker resource limits

`\fastforward` runs in the same Starlark subprocess worker as regular `\compute`
(`04-environments-spec.md` §5.5). However, given that `\fastforward` can execute
up to 10^6 iterations, the **step cap is elevated**:

| Limit            | Regular `\compute` | `\fastforward` |
|------------------|--------------------|----------------|
| Wall clock       | 5 s                | 5 s (same)     |
| Starlark ops     | 10^8               | 10^9           |
| Memory           | 64 MB              | 64 MB (same)   |

The worker detects it is inside a `\fastforward` execution via the environment
variable `SCRIBA_FASTFORWARD=1` set by the host before spawning the iteration
loop. Workers without `SCRIBA_FASTFORWARD` use the regular step cap.

If the 5-second wall clock is exceeded, the error is still E1152 (base spec
timeout). If 10^9 ops are exceeded, it is E1153 (base spec step cap). The
elevated cap means these errors occur less frequently for fast-forward workloads
but the same error codes apply.

---

## 6. Determinism check (CI-level, optional)

For CI pipelines that opt in, Scriba can detect non-deterministic `iterate`
callbacks by running the entire `\fastforward` execution twice with the same seed
and diffing the snapshot sequences:

- If snapshot sequences differ → E1344 (non-deterministic callback).
- This check is skipped in regular builds; it is enabled by setting the
  environment variable `SCRIBA_CHECK_DETERMINISM=1` before the build.
- E1344 is a **hard error** (build fails) when the check is enabled.

The most common cause of E1344 is using mutable Python/Starlark built-ins in a
way that depends on iteration order of an unordered data structure. Authors should
use `sorted()` when iterating dicts or sets inside `iterate`.

---

## 7. Narration template and substitution

`\fastforward` accepts an optional `\narrate{...}` template. The template body
is a LaTeX string that MAY contain `${placeholder}` interpolations. The available
placeholders are:

| Placeholder         | Expands to |
|---------------------|------------|
| `${frame_idx}`      | The 1-indexed frame number within the fast-forward block |
| `${iter}`           | The iteration number (`frame_idx * sample_every`) |
| `${total_iters}`    | The `total_iters` argument (constant) |
| `${sample_every}`   | The `sample_every` argument (constant) |
| `${<scene_key>}`    | Any top-level key from the scene dict at that frame's snapshot |

Each frame gets independent substitution. KaTeX rendering (`ctx.render_inline_tex`)
is applied per-frame after substitution.

If no `\narrate` is provided, the auto-generated narration is:
```
Iteration ${iter} / ${total_iters} (frame ${frame_idx}).
```

The `\hl` macro (`extension E2`) is valid inside a `\fastforward` `\narrate`
template. The `step_id` must match the label of a frame that the fast-forward
will emit. Auto-generated step labels for fast-forward frames are
`{label_prefix}{frame_idx}` where `label_prefix` is the `label` parameter
(default `"ff"`), e.g. `ff1`, `ff2`, ..., `ff20`.

---

## 8. HTML output shape

`\fastforward` emits standard filmstrip frames. There is NO extra wrapper or
class marking that a frame came from fast-forward. The consumer cannot distinguish
fast-forward frames from manual frames.

Each emitted frame follows the base spec §8.1 shape:

```html
<li class="scriba-frame"
    id="{scene-id}-frame-{K}"
    data-step="{K}">
  <header class="scriba-frame-header">
    <span class="scriba-step-label">Step K / N</span>
  </header>
  <div class="scriba-stage">
    <svg class="scriba-stage-svg" ...>
      <!-- primitive SVG rendered from scene snapshot at iter=(K-first_ff_frame)*sample_every -->
    </svg>
  </div>
  <p class="scriba-narration" id="{scene-id}-frame-{K}-narration">
    <!-- narration template instantiated for this frame -->
  </p>
</li>
```

`{K}` is the global frame index within the animation (contiguous with surrounding
manual steps).

---

## 9. Interaction with `MetricPlot` primitive

`MetricPlot` (see `primitives/metricplot.md` for the full spec) is the canonical
pairing for `\fastforward`. `MetricPlot` renders a compile-time SVG line chart
that tracks scalar values across frames. Inside a `\fastforward` block, the
MetricPlot is updated per frame by storing the tracked scalars in the scene dict.

### Series schema

The canonical `series` parameter for `MetricPlot` is a **list of dicts**:

```
series = [
  {"name": "<series-name>",
   "color": "auto" | "<palette-token>",
   "axis": "left" | "right",
   "scale": "linear" | "log"},
  ...
]
```

A shortcut form accepts a list of strings:
```
series = ["phi", "cost"]
```
which implicitly expands each string `s` to
`{"name": s, "color": "auto", "axis": "left", "scale": "linear"}`.

Two-axis mode is opt-in: set `"axis": "right"` on at least one series to enable
a secondary Y-axis on the right side of the chart.

### Example with `\fastforward`

```latex
\shape{energy}{MetricPlot}{
  series=[
    {"name": "cost",  "color": "auto",   "axis": "left",  "scale": "linear"},
    {"name": "temp",  "color": "auto",   "axis": "right", "scale": "linear"}
  ],
  x_label="Iteration",
  y_label="Cost / Temperature",
  frames=20
}

\compute{
  def iterate(scene, rng):
      # ... simulated annealing step ...
      scene["cost"] = new_cost
      scene["temp"] = new_temp
      return scene
}

\fastforward{10000}{sample_every=500, seed=42}
\narrate{Iter ${iter}: cost=$${cost}$, temp=$${temp}$.}
```

The `MetricPlot` renderer reads the `cost` and `temp` values from each frame's
scene snapshot and plots them as `<polyline>` points. This wiring is defined in
`primitives/metricplot.md`; `\fastforward` only needs to ensure the scene dict
contains the expected keys matching the `"name"` fields in the `series` list.

---

## 10. Error catalog (E1340–E1349)

| Code  | Severity | Meaning                                                              | Hint |
|-------|----------|----------------------------------------------------------------------|------|
| E1340 | **Error** | `total_iters` exceeds 10^6                                           | Maximum iterations per `\fastforward` is 1,000,000. |
| E1341 | **Error** | Computed `N = floor(total_iters / sample_every)` exceeds 100         | Reduce `total_iters` or increase `sample_every`. N ≤ 100. |
| E1342 | **Error** | `seed` parameter missing                                             | `seed` is mandatory for deterministic builds. |
| E1343 | **Error** | `iterate` function not defined in scope at `\fastforward`            | Define `def iterate(scene, rng): ...` in a preceding `\compute`. |
| E1344 | **Error** | (CI-level) Two runs with the same seed produced different snapshots  | `iterate` function is non-deterministic; check for unordered dict/set iteration. |
| E1345 | **Error** | `\fastforward` used inside `\begin{diagram}`                         | `\fastforward` requires `\step`-based frames; use `\begin{animation}`. |
| E1346 | **Error** | `total_iters` is 0 or negative                                       | `total_iters` must be a positive integer. |
| E1347 | **Error** | `sample_every` is 0 or negative                                      | `sample_every` must be a positive integer. |
| E1348 | Warning  | `N = 1`: single sampled frame from fast-forward; use `\step` instead | With N=1 the fast-forward loop is just a compute block. |

---

## 11. Acceptance test — Simulated Annealing TSP

N=10 cities (hard-coded coordinates), 10,000 iterations, sampled every 500 →
20 frames showing tour evolution and temperature decay.

```latex
\begin{animation}[id=sa-tsp, label="Simulated Annealing: 10-city TSP"]

\shape{tour}{Graph}{
  nodes=10,
  layout=fixed,
  directed=false,
  coords=[
    [0.2,0.8],[0.9,0.6],[0.5,0.2],[0.1,0.4],[0.7,0.9],
    [0.3,0.1],[0.8,0.3],[0.6,0.7],[0.4,0.5],[0.9,0.1]
  ]
}
\shape{metrics}{MetricPlot}{
  series=[
    {"name": "cost", "color": "auto", "axis": "left",  "scale": "linear"},
    {"name": "temp", "color": "auto", "axis": "right", "scale": "linear"}
  ],
  x_label="Iter",
  y_label="Cost",
  frames=20
}

\compute{
  import_forbidden = False  # Starlark; just a comment-substitute

  # City coordinates as list of (x, y) pairs
  cities = [
    [0.2,0.8],[0.9,0.6],[0.5,0.2],[0.1,0.4],[0.7,0.9],
    [0.3,0.1],[0.8,0.3],[0.6,0.7],[0.4,0.5],[0.9,0.1]
  ]
  N = len(cities)

  def dist(i, j):
      dx = cities[i][0] - cities[j][0]
      dy = cities[i][1] - cities[j][1]
      return (dx*dx + dy*dy) ** 0.5

  def tour_cost(t):
      c = 0.0
      for k in range(len(t)):
          c = c + dist(t[k], t[(k+1) % len(t)])
      return c

  def iterate(scene, rng):
      t = scene["tour"]
      temp = scene["temp"]
      cost = scene["cost"]

      # 2-opt swap
      i = rng.randint(0, N-2)
      j = rng.randint(i+1, N-1)
      new_t = t[:i] + list(reversed(t[i:j+1])) + t[j+1:]
      new_cost = tour_cost(new_t)
      delta = new_cost - cost
      if delta < 0 or rng.random() < (2.718 ** (-delta / temp)):
          scene["tour"] = new_t
          scene["cost"] = new_cost
      scene["temp"] = temp * 0.9997
      return scene

  # Initial state
  init_tour = list(range(N))
  init_cost = tour_cost(init_tour)
  init_temp = 1.0

  # Seed the scene dict — \fastforward reads these keys from scene at each iteration
  scene = {"tour": init_tour, "cost": init_cost, "temp": init_temp}
}

\step[label=init]
\apply{tour.all}{value=0}
\compute{
  for i in range(N):
      tour_edges = [(init_tour[k], init_tour[(k+1) % N]) for k in range(N)]
}
\narrate{Tour khởi tạo (greedy order), cost $= ${init_cost:.3f}$, temp $= ${init_temp}$.}

\fastforward{10000}{sample_every=500, seed=42}
\narrate{Iter ${iter}: cost $\approx ${cost:.3f}$, temp $\approx ${temp:.4f}$.}

\step[label=final]
\narrate{Hội tụ sau 10000 bước. Tour tối ưu xấp xỉ tìm được.}

\end{animation}
```

Expected: 22 total frames (1 initial + 20 fast-forward + 1 final). Frames 2–21
show the tour graph with edges updated to each snapshot's `tour` list, and the
`MetricPlot` showing the cost curve descending and the temperature curve decaying
exponentially. Build is deterministic: running twice produces byte-identical HTML.

---

## 12. Base-spec deltas

The following changes to `04-environments-spec.md` are REQUIRED.

1. **§3 Inner commands**: Add `\fastforward` as a 9th inner command (expanding the
   set from 8 to 9). Its position in the grammar is alongside `\step` in
   `anim_body`:
   ```
   anim_body ::= (comment | decl_cmd)* (step_block | fastforward_block)+
   ```
   `fastforward_block` expands to N `step_block`s at parse time.

2. **§5.4 Sandboxing**: Add a note that `\fastforward` runs with an elevated
   Starlark step cap of 10^9 ops (vs. 10^8 for regular `\compute`) signaled
   by `SCRIBA_FASTFORWARD=1`.

3. **§5.2 Pre-injected host API**: Document that the `rng` object is injected by
   the host ONLY during `\fastforward` execution (not in regular `\compute`).
   Using `rng` outside `\fastforward` is a runtime error (Starlark: unbound name).

4. **§11 Error catalog**: Reserve E1340–E1349 for `\fastforward` errors.

5. **§6.3 Frame count**: Clarify that N frames emitted by `\fastforward` count
   toward both the soft (30) and hard (100) frame limits. A `\fastforward` that
   would push the total over 100 is E1181.
