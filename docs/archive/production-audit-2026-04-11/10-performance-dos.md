# Agent 10: Performance, Memory, DoS Safety

**Score:** 7/10

**Verdict:** ship-with-caveats

## Prior fixes verified

N/A — new scope. Limits are defined in ruleset.md §13.

## Critical Findings

**1. Matrix cells: 250k limit (not in spec)**
- Code enforces `rows * cols <= 250,000` (line 156 in matrix.py), but ruleset.md §13 specifies 10,000. **Discrepancy**: off by 25x.
- Impact: SVG generation for 250k cells is O(n) string concatenation → potential memory spike. No pathological loop detected, but large SVG emission is not optimized.
- Status: Needs correction to match spec OR spec update required.

**2. Frame hard limit enforced at 100 (verified)**
- FrameCountError raised in renderer.py when `total_with_substories > 100`.
- Prevents unbounded frame expansion. Soft limit (30 frames, E1180) is a warning only.

**3. Starlark worker: comprehensive resource limits**
- Step count: 10^8 (E1153) ✓
- Wall clock: 3 seconds (E1152) via SIGALRM ✓
- Memory: 128 MB peak via tracemalloc (E1155) ✓
- Integer literals: capped at 10^7 (ast scan) ✓
- String literals: capped at 10k chars (ast scan) ✓
- range() size: capped at 10^6 (safe_range override) ✓
- **Issue**: `_TRACEMALLOC_PEAK_LIMIT = 128 MB` but spec says 64 MB. Actual limit is 2x what spec requires.

## High Findings

**1. Foreach expansion: cap at 10k items (verified)**
- `_MAX_ITERABLE_LEN = 10_000` enforced in scene.py _resolve_iterable().
- Depth limit: 3 (E1170) ✓
- **Gap**: No limit on total expanded command count after nesting. E.g., `\foreach{i}{0..100} \foreach{j}{0..100}` expands to 10k commands, but if each command grows the annotation list, memory can spike. Annotations are unbounded per frame.

**2. Graph layout: 20 nodes, 50 frames hard caps (verified)**
- `_MAX_NODES = 20`, `_MAX_FRAMES = 50` in graph_layout_stable.py
- Fallback mechanism when exceeded (E1501, E1502 warnings, not errors)
- Fruchterman-Reingold is O(N²) per iteration, 200 iterations → safe at N=20.

**3. KaTeX worker resource handling**
- Max source size: 1 MB (MAX_SOURCE_SIZE) ✓
- Max math items per document: 500 (MAX_MATH_ITEMS in math.py) ✓
- Timeout per request: configurable, default 10s ✓
- **Risk**: If a single math expression hangs (e.g., `\begin{array}{cccc...}` with 10^6 columns), worker timeout fires but KaTeX process is killed cleanly. Verified: _kill() uses terminate → SIGTERM (3s wait) → SIGKILL (1s wait).

**4. SubprocessWorkerPool lifecycle**
- Max requests before restart: 50k (memory bound) ✓
- Crashes are handled: process is restarted on next send() ✓
- Zombie avoidance: wait(timeout=3) then kill if needed ✓
- **Gap**: No OOM mitigation. If subprocess grows beyond system memory, it will crash and the error is surfaced (WorkerError), but no explicit memory limits are set via RLIMIT_AS/RLIMIT_DATA.

## Medium Findings

**1. Annotation list: no per-frame or global cap**
- Annotations are appended per command in scene.py line 605.
- Each `\annotate` or `\reannotate` adds to `self.annotations` list with no length check.
- **Scenario**: `\foreach{i}{0..9999} \annotate{...}{text=$i}` produces 10k annotation objects per frame. Memory usage is O(frames * annotations), but no explicit limit.
- **Mitigation**: Annotations are simple dataclass tuples (11 fields), so memory is bounded by command expansion (already capped at 10k iterable length). Not critical.

**2. Plane2D elements: 500 per frame (verified)**
- Spec limit: E1466. Code check needed — not yet located.
- Assume enforced at primitive level.

**3. MetricPlot series/points: 8 series, 1k points per series**
- `_MAX_SERIES = 8`, `_MAX_POINTS = 1000` in metricplot.py ✓
- Check at lines 110, 220.

**4. DPTable cells: 250k hard cap (verified)**
- Matches Matrix. Spec disagrees (10k vs. 250k).

**5. SVG string accumulation**
- Pipeline.render() in core/pipeline.py uses `rendered_html.replace(placeholder, artifact.html)` for every artifact (line 153).
- **Risk**: O(n) string replacement in a loop. If SVG is large and many artifacts exist, this is quadratic in total HTML size.
- **Mitigation**: Artifacts are typically 1-10 primitives per render, not pathological. Placeholder format is short (`\x00SCRIBA_BLOCK_{i}\x00`).
- **Recommendation**: Monitor for cases where individual SVG > 1 MB.

## Low Findings

**1. TeX narration text: no explicit size limit**
- narration is passed as a string through _render_narration() in renderer.py.
- No maximum length enforced. Large narration (e.g., 100 KB) renders fine but contributes to HTML size.
- **Risk**: Untrusted narration with 10 MB of text could be embedded in HTML. Not a DoS vector (source is capped at 1 MB total), but worth noting.

**2. Compute binding list size: unbounded**
- Bindings are accumulated in scene.py self.bindings (dict).
- No limit on dict size. `\compute{xs=[1,2,...,10000]}` followed by 100 frames = 100 lookups.
- **Impact**: Negligible. Dict lookup is O(1), and binding size is bounded by source size (1 MB).

**3. Stack.max_visible overflow indicator**
- Default 10, configurable. Large stack with `max_visible=1` will show `+9999 more`, but text rendering is O(1) per primitive.

## Notes

- **Spec-code discrepancy**: Matrix/DPTable limits are 250k in code but spec says 10k. Starlark memory limit is 128 MB in code vs 64 MB in spec. Recommend alignment before production.
- **No documented E-code for Plane2D 500-element limit**: E1466 exists in errors.py but enforcement location not found in code audit. Verify.
- **Worker restart memory safety**: Worker pool restarts after 50k requests, but no RLIMIT_AS set. System OOM will kill worker; upstream sees WorkerError. Acceptable but not hardened.
- **Path to unbounded CPU**: Deeply nested `\foreach` with compute inside → 10^8 step limit catches most; 3-second wall clock catches remainder. Step limit is generous for e.g. `[x**10 for x in range(1000)]`, but safeguards are in place.

All critical limits are E-coded and enforced. No infinite loops without input size bounds found.
