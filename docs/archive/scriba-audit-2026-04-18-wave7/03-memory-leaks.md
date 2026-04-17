# Wave 7 — Memory and Resource Leak Audit

**Date**: 2026-04-18
**Scope**: Long-session / many-render memory behaviour across the Python
LaTeX-to-HTML pipeline.
**Methodology**: Empirical PoC benchmarks. RSS measured via
`ps -o rss= -p <pid>` after `gc.collect()`. tracemalloc top-N allocators
captured over rolling windows. All runs on macOS (darwin 25.1.0),
CPython 3.14, scriba main @ 0a8ec6e.

---

## Benchmark Summary

| Scenario | Renders | RSS baseline | RSS final | Net delta |
|---|---|---|---|---|
| Same source, no compute, 100 renders | 100 | 30 928 KB | 31 168 KB | +240 KB |
| 1 000 distinct sources, no compute | 1 000 | 30 912 KB | 31 520 KB | +608 KB |
| Same source, `\compute` block, 100 renders | 100 | 30 832 KB | 31 088 KB | +256 KB |
| Same source, `\compute` block, 1 000 renders | 1 000 | 31 072 KB | 32 080 KB | +1 008 KB |
| 500 worker evals (host process) | 500 | 30 400 KB | 30 432 KB | +32 KB |
| Worker subprocess, 500 evals | 500 | 30 000 KB | 30 080 KB | +80 KB |

**Overall verdict**: growth is sub-linear, plateaus after ~500 renders, and
shows no sign of unbounded monotonic accumulation. No critical leak was found.
The detailed findings below explain every non-trivial delta observed.

---

## Finding 01 — MEDIUM: Cumulative Starlark budget not reset when same `StarlarkHost` is reused across render sessions

**File**: `scriba/animation/starlark_host.py:152`, `scriba/animation/starlark_worker.py:533`

### What was observed

`StarlarkHost._budget_reset_done` is an **instance-level** flag set to `True`
after the first `eval()` call. The module-level counter
`starlark_worker._cumulative_elapsed` is then only zeroed once per host
instance lifetime, not once per render.

When the same `StarlarkHost` is reused across multiple `Pipeline.render()`
calls (the normal production pattern — one persistent pool per process), elapsed
time from render N accumulates into render N+1:

```
Scenario A: same host reused across renders
  Initial _budget_reset_done: False
  After first eval: _budget_reset_done=True, elapsed=0.0778s
  After second eval (same host, NO reset): elapsed=0.0779s   # leaked
```

A document with N expensive `\compute` blocks can burn through the 5 s
cumulative budget in fewer real-wall-clock seconds than intended, because
leftover time from previous renders is charged against it.

In the measured 100-render + compute run, each render individually consumed
~0.08–0.13 s. With unlimited renders the running total would cross the 5 s
cap after roughly 40–60 renders and would start raising spurious `E1152`
("cumulative budget exceeded") errors against perfectly legitimate documents.

### Root cause

`_budget_reset_done` is semantically "reset done for the lifetime of this
host", but the intended contract is "reset done for the current render". The
flag should be cleared by the caller at the start of each render, not just at
host construction.

### Fix recommendation

The reset should happen at the start of each render — either by clearing
`_budget_reset_done` in `AnimationRenderer.render_block()` before it calls
`_instantiate_primitives` / `_materialise`, or by exposing a
`StarlarkHost.reset_render_budget()` method that callers invoke explicitly.
The simplest one-line fix in `renderer.py`:

```python
# renderer.py — AnimationRenderer.render_block()
if self._starlark_host is not None:
    self._starlark_host._budget_reset_done = False   # allow reset on first eval
```

Or, cleaner, add a public method to `StarlarkHost`:

```python
def begin_render(self) -> None:
    """Reset the per-render cumulative budget. Call before each render_block."""
    self._budget_reset_done = False
```

**Severity**: MEDIUM — affects correctness of budget enforcement under host
reuse, not RSS growth. Renders in a long session will eventually raise
spurious E1152 errors once the running total crosses 5 s.

---

## Finding 02 — LOW: `lru_cache(maxsize=None)` on CSS bundler holds ~16 MB permanently

**File**: `scriba/core/css_bundler.py:16,39`

### What was observed

```
RSS before first inline_katex_css():  17 216 KB
RSS after  first inline_katex_css():  33 136 KB
RSS delta:                            +15 920 KB
inline_katex_css string length: 367 436 chars (359 KB)
```

The large RSS delta (~16 MB) is dominated by loading and base64-encoding the
KaTeX woff2 fonts into memory. After the first call this string is interned
in the cache and **never freed** for the lifetime of the process.

`load_css.cache_info()` after 1 000 distinct-source renders stabilises at
`currsize=2` (two CSS filenames). `inline_katex_css.cache_info()` stays at
`currsize=1`. Neither grows monotonically.

### Assessment

**This is intentional and correct**. The KaTeX CSS (with embedded fonts) is
used on every render. Caching it permanently avoids re-reading and
re-base64-encoding ~360 KB of font data on each call. The 16 MB one-time
cost is a deliberate trade-off documented in the function docstring. The cache
does NOT grow across renders — it is bounded by the finite set of CSS
filenames in the package.

**Severity**: LOW / INFO — no action required. Add a code comment noting the
deliberate 16 MB working-set cost if future reviewers raise this as a concern.

---

## Finding 03 — LOW: `re.compile()` inside `_expand_selectors` creates per-shape-name patterns

**File**: `scriba/animation/emitter.py:367–370`

### What was observed

`_expand_selectors(shape_state, shape_name, prim)` contains three inline
`re.compile()` calls whose patterns embed the caller-supplied `shape_name`:

```python
range_re = re.compile(rf"^{re.escape(shape_name)}\.range\[(\d+):(\d+)\]$")
all_re   = re.compile(rf"^{re.escape(shape_name)}\.all$")
top_re   = re.compile(rf"^{re.escape(shape_name)}\.top$")
```

This function is called once per shape per frame. With 1 000 distinct source
files each using a unique shape name, the re module's internal LRU cache
accumulates patterns. tracemalloc confirmed `re/_compiler.py` as the top
allocator across 10 measured renders:

```
re/_compiler.py:778: size=17.4 KiB, count=40, average=446 B
```

Python's re module caps its compiled-pattern cache at `re._MAXCACHE = 512`
entries. After 600 unique shape names (1 800 patterns), the cache stabilises
at exactly 512 entries:

```
After 600 unique shapes: re._cache = 512  (capped at MAXCACHE)
```

### Assessment

**Bounded, not a leak**. The cache will not grow beyond 512 × ~450 B ≈ 230 KB.
For typical documents (few dozen unique shape names) the cache never fills.

Minor inefficiency: three compile() calls per `_expand_selectors()` invocation
re-register patterns on every frame. Hoisting these patterns to module-level
constants with a `functools.lru_cache` keyed on `shape_name` would eliminate
repeated compilation. Not a correctness issue.

**Severity**: LOW — no action required for correctness; optional optimisation.

---

## Finding 04 — PASS: Worker process recycled correctly; no indefinite lifetime accumulation

**File**: `scriba/core/workers.py:48–314`

### What was observed

`PersistentSubprocessWorker` spawns one subprocess and restarts it after
`max_requests = 50 000` successful sends. In the 100-render compute benchmark,
the worker handled 202 requests total (`~2 eval() calls per render`).
The subprocess RSS grew by only +80 KB across 500 evals:

```
eval    1: worker_RSS=30 000 KB  delta=  0 KB
eval  100: worker_RSS=30 064 KB  delta=+64 KB
eval  250: worker_RSS=30 064 KB  delta=+64 KB
eval  500: worker_RSS=30 080 KB  delta=+80 KB
```

The 50 000-request recycling threshold means the subprocess lives for the
entire process lifetime in normal use (a 1 000-page document with 5 compute
blocks per page = 5 000 requests — well under the limit).

No accumulation was observed in the worker subprocess RSS. The
`starlark_worker` main loop allocates on the stack per-eval (`namespace`
dict, `debug` list, `print_capture` list) and these are freed after each
response is written.

**Severity**: PASS — no issue.

---

## Finding 05 — PASS: tracemalloc started and stopped correctly per eval in worker

**File**: `scriba/animation/starlark_worker.py:631–641`

### What was observed

`_evaluate()` conditionally starts tracemalloc if it was not already running,
runs the user code, then stops it unconditionally in the `finally` block:

```python
_tracemalloc_was_tracing = tracemalloc.is_tracing()
if not _tracemalloc_was_tracing:
    tracemalloc.start()
...
finally:
    sys.settrace(old_trace)
    if not _tracemalloc_was_tracing and tracemalloc.is_tracing():
        tracemalloc.stop()
```

Verified empirically: `tracemalloc.is_tracing()` returns `False` after 100
back-to-back `_evaluate()` calls in the worker. No persistent tracing overhead
accumulates.

**Severity**: PASS — no issue.

---

## Finding 06 — PASS: `_CAPTURED_PRINTS` module-level list does not accumulate

**File**: `scriba/animation/starlark_worker.py:253`

### What was observed

`_CAPTURED_PRINTS: list[str] = []` is defined at module level but is never
mutated by `_evaluate()`. Each eval creates a fresh `print_capture: list[str]`
local variable, passes it to `_make_print_fn`, and discards it after the
response is serialised. The module-level list stays empty across 100 evals:

```
_CAPTURED_PRINTS after 100 evals: []   (confirmed empty)
_ALLOWED_BUILTINS keys stable: True
```

**Severity**: PASS — the module-level list is vestigial and harmless.

---

## Finding 07 — PASS: `AnimationRenderer.last_snapshots` is replaced, not appended, on each render

**File**: `scriba/animation/renderer.py:585`

### What was observed

```python
self.last_snapshots = snapshots   # assignment, not extend
```

Confirmed: after 10 consecutive renders of a 3-frame source, `last_snapshots`
always holds exactly 3 entries. The previous render's snapshots are released
immediately.

`render.py:166` uses `all_snapshots.extend(anim_renderer.last_snapshots)` to
collect snapshots across a document-level multi-block render. This accumulates
snapshots proportional to the number of animation blocks in the document, not
across renders. It is the caller's responsibility to clear `all_snapshots`
between documents.

**Severity**: PASS — no issue in the library itself.

---

## Finding 08 — PASS: GC cycles and reference leaks

### What was observed

```
gc.get_count() after 100 renders:  (0, 0, 0)
gc.garbage after DEBUG_SAVEALL:    0 objects
```

`RenderContext` instances are not retained after `Pipeline.render()` returns.
`FrameSnapshot` objects (frozen dataclasses containing `frozenset` and
`tuple`) form no reference cycles. `SceneState` is a local variable inside
`_materialise()` and is freed at the end of each render.

**Severity**: PASS — no cycles, no orphaned objects.

---

## Finding 09 — PASS: `SubprocessWorkerPool` close() flushes all streams

**File**: `scriba/core/workers.py:173–201`

### What was observed

`_kill()` explicitly closes `proc.stdin`, `proc.stdout`, and `proc.stderr`
in a `finally` block after `terminate()` / `kill()`. The stdout/stderr
`TextIOWrapper` objects showed no unconsumed buffer accumulation across 500
evals. Line-buffered JSON-line protocol (`bufsize=1`) means the kernel pipe
buffer does not grow between request/response pairs.

**Severity**: PASS — no buffer growth.

---

## Finding 10 — INFO: `_WINDOWS_WARNING_EMITTED` module-level sentinel is never re-armed on Windows

**File**: `scriba/animation/starlark_host.py:27`

### What was observed

`_WINDOWS_WARNING_EMITTED` is a module-level boolean. Once set to `True` on
Windows, `_reset_windows_warning()` (a test-only hook) is the only way to
clear it. This is intentional (one-shot warning). Under test isolation this
is correctly documented and the reset helper works.

**Severity**: INFO — working as intended. No change needed.

---

## RSS Growth Profile (1 000-render compute session)

```
Iter   50: RSS=31 376 KB  delta= +304 KB
Iter  100: RSS=31 472 KB  delta= +400 KB
Iter  250: RSS=31 696 KB  delta= +624 KB
Iter  500: RSS=31 952 KB  delta= +880 KB
Iter  650: RSS=32 032 KB  delta= +960 KB   ← plateau begins
Iter  750: RSS=32 064 KB  delta= +992 KB
Iter 1000: RSS=32 080 KB  delta=+1 008 KB
```

Second-half delta (iter 550 → 1 000): 31 984 → 32 080 KB = **+96 KB over 450
renders**. This is below the 100 KB threshold for a monotonic leak verdict.
The residual growth is attributed to CPython's jit/specialisation caches and
re module pattern interning, both of which are capped by the interpreter.

---

## Action Items

| Priority | Finding | Action |
|---|---|---|
| MEDIUM | 01 — budget reset | Add `StarlarkHost.begin_render()` or clear `_budget_reset_done` in `AnimationRenderer.render_block()` before the first `eval()` call |
| LOW | 02 — LRU CSS | No change. Add a comment noting the deliberate 16 MB permanent footprint |
| LOW | 03 — re.compile | Optional: hoist patterns to module level or use `functools.lru_cache(maxsize=64)` keyed on `shape_name` in `_expand_selectors` |
