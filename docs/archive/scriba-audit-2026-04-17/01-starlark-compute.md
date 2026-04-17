# Starlark `\compute` Subsystem Audit

**Date**: 2026-04-17
**Auditor**: automated empirical audit via `uv run python`
**Scope**: `scriba/animation/starlark_host.py`, `scriba/animation/starlark_worker.py`,
`scriba/animation/constants.py`, `scriba/animation/errors.py`, `scriba/core/workers.py`
**Python**: 3.10.20 (CPython, macOS aarch64)

All findings are empirical. Each attack was crafted as a JSON-line request sent to a live
`starlark_worker` subprocess, and the actual response (code, message, bindings) was captured.

---

## Summary

| # | Finding | Severity |
|---|---------|----------|
| 1 | Cumulative budget (`_CUMULATIVE_BUDGET_SECONDS = 5 s`) is **never wired** — `StarlarkHost.eval()` neither calls `reset_cumulative_budget()` nor `consume_cumulative_budget()`. The 5-second cumulative cap exists only in test code; production renders have no cumulative limit. | 🔴 Critical |
| 2 | C-level list/zip allocations **bypass SIGALRM**. `[0] * 9_000_000` takes ~1.8 s and succeeds; `list(zip(range(1M), range(1M)))` takes ~1.7 s and succeeds. RLIMIT_CPU (5 s) is the only backstop, and macOS RLIMIT_DATA is not reliably enforced. | 🟠 High |
| 3 | `RecursionError` raised inside `compile()` (triggered by deeply-nested AST from ~5 000-token source expressions) leaks the full internal file path (`…/scriba/animation/starlark_worker.py`, line 527) in the E1151 error message. The `format_compute_traceback` filter's fallback returns the raw traceback when no `<compute>` frame is present. | 🟡 Medium |

---

## Sandbox Surface

### What is exposed to author code

| Feature | Exposed? | Notes |
|---------|----------|-------|
| `import` / `from … import` | Blocked (E1154) | AST pre-scan |
| `exec` / `eval` / `compile` | Blocked (E1154) | `FORBIDDEN_BUILTINS` set |
| `open` / `os` / `sys` / `subprocess` | Blocked (E1154) | Not in scope + AST |
| `__import__` as name | Blocked (E1154) | `FORBIDDEN_BUILTINS` |
| `getattr` / `setattr` / `delattr` | Blocked (E1154) | `FORBIDDEN_BUILTINS` |
| `type` / `vars` / `dir` / `globals` / `locals` | Blocked (E1154) | `FORBIDDEN_BUILTINS` |
| `while` / `try` / `class` / `lambda` | Blocked (E1154) | `_FORBIDDEN_NODE_TYPES` AST |
| `async def` / `await` / `yield` | Blocked (E1154) | Wave 4B AST |
| `walrus (:=)` | Blocked (E1154) | `ast.NamedExpr` |
| `__class__` / `__mro__` / `__globals__` / `__builtins__` as attribute | Blocked (E1154) | `BLOCKED_ATTRIBUTES` |
| `f.__globals__` via attribute chain | Blocked (E1154) | `_attribute_chain_names` walk |
| `"{0.__class__}".format(x)` | Blocked (E1154) | `_scan_format_call` |
| `__builtins__` as **variable name** | **Allowed** | Injected as `namespace["__builtins__"]` dict; readable at runtime |
| `def f(): …` (regular functions) | Allowed | Required by cookbook examples |
| `filter` / `map` with a `def` function | Allowed | Useful compute pattern |
| `repr(fn)` | Allowed | Leaks pointer address (non-deterministic) |
| `sorted` / `sum` / `max` / `min` on large ranges | Allowed | C-level; may exceed 1 s |
| `pow(b, e)` with injected `e` | Allowed | Large exponents raise `ValueError` (E1151) via Python 3.11+ int str limit; on 3.10 the bigint itself is computed |
| Integer literals > 10 000 000 | Blocked (E1154) | AST constant check |
| String literals > 10 000 chars | Blocked (E1154) | AST constant check |
| `range()` > 1 000 000 | Blocked (E1173) | `_safe_range` wrapper |
| Recursion depth > 1 000 | Blocked (E1151 RecursionError) | `sys.setrecursionlimit(1000)` |

### What is not blocked but harmless

- `hasattr` is absent from both `_ALLOWED_BUILTINS` and `_FORBIDDEN_BUILTINS`; it raises
  `NameError` (E1151) at runtime — acceptable but could be a cleaner E1154.
- `str.maketrans` attribute is allowed (not in `BLOCKED_ATTRIBUTES`); it returns a dict
  and cannot be used for escape.
- `isinstance` is explicitly allowed (SS7.3 spec note). The AST scanner blocks
  `__class__`/`__mro__` attribute access, so `isinstance` alone is not a stepping stone.

---

## Resource Limits — Empirical Results

All tests ran on macOS aarch64, Python 3.10, SIGALRM available, RLIMIT_DATA set to 64 MB
in `_starlark_preexec`.

| Attack | Expected defence | Actual result | Elapsed | Verdict |
|--------|-----------------|---------------|---------|---------|
| `while True: pass` | E1154 (AST blocks `while`) | E1154 ✓ | <1 ms | BLOCKED |
| `for i in range(10**9)` | E1173 (`_safe_range`) | E1173 ✓ | <1 ms | BLOCKED |
| `[0] * 1_000_000` | tracemalloc / RLIMIT | ok, 8 MB | 241 ms | ALLOWED — within limits |
| `[0] * 5_000_000` | tracemalloc / RLIMIT | ok, 40 MB | 1.27 s | **BYPASSES 1 s SIGALRM** |
| `[0] * 8_000_000` | tracemalloc / RLIMIT | ok, 64 MB | 1.77 s | **BYPASSES 1 s SIGALRM** |
| `[0] * 9_000_000` | RLIMIT_DATA 64 MB | ok, 72 MB | 1.84 s | **BYPASSES both SIGALRM and soft memory limit** |
| `list(zip(range(1M), range(1M)))` | 1 s SIGALRM | ok | 1.72 s | **BYPASSES 1 s SIGALRM** |
| `list(zip(range(1M)) * 8)` | 1 s SIGALRM | E1152 ✓ | 1.82 s | caught by SIGALRM on the way back |
| `sum(i*i for i in range(1M))` (generator) | 1 s SIGALRM | E1152 ✓ | 1.01 s | caught — generator ticks trace hook |
| `sorted(range(1M))` | 1 s SIGALRM | ok | 326 ms | fast enough; no issue |
| `list(map(str, range(1M)))` | 1 s SIGALRM | ok | 734 ms | within 1 s |
| `max(range(1M))` | 1 s SIGALRM | ok | 253 ms | fast; no issue |
| `sum(range(1M))` | 1 s SIGALRM | ok | 157 ms | fast; no issue |
| `def f(n): return f(n+1); f(0)` | RecursionError | E1151 ✓ | <1 ms | caught |
| `pow(2, e)` with `e=100_000` | step counter / SIGALRM | E1151 (ValueError: int_str_digits) ✓ | fast | caught by Python guard |
| `'x = ' + '+'.join(['1']*5000)` | source too deep | E1151 (RecursionError in compile) — **leaks path** | <1 ms | **PATH LEAK** |
| `x = __builtins__` | — | ok — full whitelist dict readable | <1 ms | LOW — no escape possible |

**Key observation on C-level bypass**: `[0] * N` is a single `list_repeat` C call.
SIGALRM fires between Python bytecode instructions; a single C-level call that runs
for >1 s will complete before the handler has a chance to fire. The 64 MB
`RLIMIT_DATA` cap on macOS is also not reliably honoured by the kernel for anonymous
heap pages. The tracemalloc soft check only runs every 1 000 Python trace steps, so a
C-level allocation completes before the next check.

**Practical impact**: an author can allocate up to ~72 MB (9 M element list of Python ints,
each 28 bytes) in a single `\compute` block without any defence firing. This is above the
advertised 64 MB spec limit.

---

## Subprocess Lifecycle Bugs

### Orphan processes
**None found.** `pool.close()` correctly calls `worker._kill()` → `proc.terminate()` →
`proc.wait(timeout=3)` → `proc.kill()`. After `pool.close()`, `os.kill(pid, 0)` raises
`ProcessLookupError`. No zombie state observed.

### Pipe deadlock on large output
**None found.** `PersistentSubprocessWorker.send()` uses `select()` on
`proc.stdout` before `readline()`, so the host does not block indefinitely. Tested with
outputs up to 100 000 integers (~790 KB JSON); all completed in <50 ms.

### IPC encoding
- `ensure_ascii=True` is correctly set on the host side (`workers.py:248`).
- The worker uses `ensure_ascii=False` on responses (line 725) — a mismatch in strictness
  but not a security issue; non-ASCII in output is valid JSON.
- Null bytes in the source string cause the JSON decoder to crash (`json.JSONDecodeError`
  on an empty string), which kills the worker process. The host sees a `BrokenPipeError`
  and recovers on the next request by respawning. **Not a security issue** because null
  bytes in TeX source are extremely unlikely and the host recovers gracefully.
- Worker recovery after SIGKILL: verified — a fresh worker spawns correctly on the
  next `StarlarkHost.eval()` call via `_ensure_started()`.

### Windows path
On Windows, `preexec_fn=None` (correctly set by `workers.py:74`), so `_starlark_preexec`
does not run. No `SIGALRM`, no `RLIMIT_AS/DATA/CPU`. Only the step counter
(`_STEP_LIMIT = 10**8`) protects against runaway loops. The `RuntimeWarning` fires once
per process, but there is **no mechanism to enforce the 1 s wall-clock promise** on
Windows.

---

## State Leakage Findings

### Cross-request global state
**None found.** The worker allocates a fresh `namespace` dict per `_evaluate()` call
(line 497). Sequential requests cannot read each other's bindings.

### Cross-render cumulative budget — **NOT ENFORCED**
`_cumulative_elapsed` is a module-level float in `starlark_worker.py`. The worker process
is persistent (`max_requests = 50_000`), so this float accumulates across requests — but
`consume_cumulative_budget()` is **never called from `StarlarkHost.eval()`**.

```python
# starlark_host.py — StarlarkHost.eval() does NOT call either:
reset_cumulative_budget()      # never called in production
consume_cumulative_budget()    # never called in production
```

Confirmed via `inspect.getsource`:
```
StarlarkHost.eval calls consume_cumulative_budget: False
StarlarkHost.eval calls reset_cumulative_budget:   False
```

The functions are tested in `test_starlark_budget.py` in isolation, but the host-side
wiring is missing. An animation with 20 `\compute` blocks each taking 900 ms (just under
the 1 s per-block alarm) would consume 18 s total with no cumulative check firing.

### Mutable globals injection
Author code **can mutate** host-injected mutable objects:

```
h.append(99)  # h=[1,2,3] → [1,2,3,99] — visible in response bindings
d["new"] = 999  # injected dict mutated — visible in response
```

The mutation flows back over JSON round-trip → `self.bindings.update(result)`.
Because `_run_compute` passes `self.bindings` directly to `starlark_host.eval()` and JSON
serialization creates new objects on the wire, there is **no aliasing attack** — the host
object is not mutated in-place. The mutation is intentional for the persistent binding model.

Frame-local compute correctly uses `copy.deepcopy(self.bindings)` to isolate frame bindings
from the persistent state (scene.py:211, 286).

### `__builtins__` dict readable
Authors can read the entire whitelisted builtins dict via `x = __builtins__`. In
CPython, when `exec()` is called with `{"__builtins__": dict_obj, …}`, the dict is
accessible as `__builtins__` from inside the code object.

```python
# Confirmed:
x = __builtins__
# → {'list': None, 'dict': None, … 'isinstance': None, 'print': None}
# (callables serialized as None in response, but usable at runtime)

fn = __builtins__["len"]
x = fn([1, 2, 3])   # → 3  (works at runtime)

__builtins__["evil"] = str  # allowed — modifies namespace dict for this request only
```

The security impact is low: all functions reachable via `__builtins__` are already in the
whitelist; blocked functions (`exec`, `__import__`, etc.) are not in the namespace and
cannot be placed there because the AST scanner blocks any reference to them. Modifying
`__builtins__` only affects the current request's namespace.

---

## Error Reporting Gaps

### Line/col on E1151 runtime errors
`E1151` (runtime exception) always returns `line=None, col=None`. The `<compute>` frame
appears in the traceback message, so line information is present as text — but the
structured `line`/`col` fields are never populated for runtime errors.

```
# ZeroDivisionError at line 1:
{"code": "E1151", "line": null, "col": null,
 "message": "Traceback …\n  File \"<compute>\", line 1…\nZeroDivisionError"}
```

Callers that read `response["line"]` to display a caret marker get `None` even when the
line is recoverable.

### E1150 syntax errors carry correct line/col
```
# "def (invalid" → line=1, col=5  ✓
{"code": "E1150", "line": 1, "col": 5, "message": "parse error: invalid syntax"}
```

### E1154 forbidden-construct errors carry correct line/col
```
# "import os" → line=1, col=1  ✓
{"code": "E1154", "line": 1, "col": 1, "message": "forbidden construct 'import' at line 1"}
```

### Internal path leak via `RecursionError` in `compile()`
A source expression with ~5 000 chained additions (`x = 1+1+1+…`) triggers a
`RecursionError` inside `compile()`, before `exec()` runs. The generic `except Exception`
handler at line 593 calls `format_compute_traceback()`, but the fallback logic in that
function returns the **raw traceback when no `<compute>` frame is present** (because the
error happened in `compile()`, not inside the compiled code):

```python
# format_compute_traceback fallback (errors.py:639):
if not any("<compute>" in line for line in kept):
    return tb_text   # ← returns raw traceback unchanged
```

Actual output observed:
```
Traceback (most recent call last):
  File "/Users/…/scriba/animation/starlark_worker.py", line 527, in _evaluate
    exec(compile(source, "<compute>", "exec"), namespace)
RecursionError: maximum recursion depth exceeded during compilation
```

This discloses the absolute filesystem path of the worker and the line number of the
`exec(compile(…))` call.

**Trigger condition**: source with ~5 000 tokens in a deeply nested binary expression.
String literal > 10 000 chars is blocked by AST scan, but the scan runs `ast.parse(source)`
first — if `ast.parse()` succeeds (it does for `x = 1+1+…`), the AST scan returns clean,
and the source is passed to `compile()`. CPython's compiler uses recursion to lower the
AST, so a wide flat expression (not deep nesting) overflows the stack when the worker's
recursion limit is 1 000.

### `hasattr` raises E1151 (NameError), not E1154
`hasattr` is neither in `_ALLOWED_BUILTINS` nor in `_FORBIDDEN_BUILTINS`. Authors who write
`hasattr(x, "y")` get a confusing `NameError: name 'hasattr' is not defined` wrapped in
E1151 rather than a clear E1154 "forbidden construct" message.

---

## Top 5 Fixes Ranked by Severity

### 1. Wire the cumulative budget into `StarlarkHost.eval()`
**Severity**: 🔴 Critical  
**Effort**: Small (2–4 lines in `starlark_host.py`)  
**File:line**: `scriba/animation/starlark_host.py:149` (`StarlarkHost.eval`)

`reset_cumulative_budget()` and `consume_cumulative_budget()` exist in `starlark_worker.py`
and are tested in `test_starlark_budget.py`, but `StarlarkHost.eval()` never calls them.
A document with many `\compute` blocks can consume unbounded wall-clock time.

**Fix**: import and call these two functions from the host side, tracking elapsed time
per `eval()` call:

```python
# starlark_host.py imports
from scriba.animation.starlark_worker import (
    consume_cumulative_budget,
    reset_cumulative_budget,
)

# In StarlarkHost.eval():
import time as _time
t0 = _time.monotonic()
response = worker.send(request, timeout=timeout)
elapsed = _time.monotonic() - t0
consume_cumulative_budget(elapsed)
```

Call `reset_cumulative_budget()` at the start of each render (before the first `\compute`
block) in `render.py` or at the `AnimationRenderer.render_block()` entry point.

---

### 2. Cap C-level allocation to close the SIGALRM bypass window
**Severity**: 🟠 High  
**Effort**: Medium  
**File:line**: `scriba/animation/starlark_worker.py:285` (`_ALLOWED_BUILTINS`)

Single C-level operations such as `[0] * N` bypass SIGALRM because SIGALRM fires only
between Python bytecode instructions. Confirmed: `[0] * 9_000_000` (~72 MB) takes 1.84 s
and succeeds — above the 64 MB spec limit and above the 1 s wall-clock promise.

**Fix A** (fast): wrap `list` constructor to cap the result size, similar to `_safe_range`:

```python
def _safe_list(*args, **kwargs):
    result = list(*args, **kwargs)
    if len(result) > _MAX_RANGE_LEN:   # reuse 1M cap
        raise animation_error("E1155", f"list too large ({len(result)} > {_MAX_RANGE_LEN})")
    return result
# Replace "list": list  →  "list": _safe_list  in _ALLOWED_BUILTINS
```

**Fix B** (defense-in-depth): add a tracemalloc check after `exec()` returns (in addition
to the periodic in-trace check) so even a single C-level alloc that completes before the
next trace step is caught before the response is serialized.

---

### 3. Fix the `format_compute_traceback` fallback to suppress the internal path
**Severity**: 🟡 Medium  
**Effort**: Small  
**File:line**: `scriba/animation/errors.py:639`, `scriba/animation/starlark_worker.py:593`

When `compile()` raises `RecursionError`, the traceback has no `<compute>` frame.
The fallback in `format_compute_traceback` returns the raw traceback, which contains the
absolute path of `starlark_worker.py`.

**Fix option A** — strip all `File "…/starlark_worker.py"` lines unconditionally before
applying the fallback, so the internal path is never returned regardless of `<compute>`
presence:

```python
# In format_compute_traceback, before the final fallback:
kept_no_internal = [
    l for l in kept
    if "starlark_worker.py" not in l
]
```

**Fix option B** — catch `RecursionError` explicitly in `_evaluate()` alongside the
existing `MemoryError` handler and return a clean E1154-style message:

```python
except RecursionError:
    if has_alarm:
        signal.alarm(0)
    return {
        "id": request_id,
        "ok": False,
        "code": "E1154",
        "message": "source expression too complex (recursion depth exceeded during compilation)",
        "line": None,
        "col": None,
    }
```

Option B is cleaner because it gives the author an actionable message. The AST scan
could also pre-detect this by counting total AST nodes (a cheap `sum(1 for _ in ast.walk(tree))`
cap would catch the 5 000-token case before `compile()` runs).

---

### 4. Add `hasattr` to `FORBIDDEN_BUILTINS` (clear E1154 instead of confusing E1151)
**Severity**: 🟡 Medium (UX)  
**Effort**: Trivial (one-liner)  
**File:line**: `scriba/animation/constants.py:103` (`FORBIDDEN_BUILTINS`)

`hasattr` is silently absent from both the whitelist and the blocklist. Authors who write
`hasattr(x, "name")` get a confusing `NameError: name 'hasattr' is not defined` (E1151)
instead of the expected E1154 "forbidden construct" message.

**Fix**: add `"hasattr"` to `FORBIDDEN_BUILTINS` in `constants.py`.

---

### 5. Populate `line`/`col` fields for E1151 runtime errors
**Severity**: 🟡 Medium (DX)  
**Effort**: Small  
**File:line**: `scriba/animation/starlark_worker.py:593` (generic `except Exception`)

Runtime errors (E1151) always return `line=None, col=None`. The line number is present
in the `<compute>` traceback text but not in the structured fields. Callers that display
a caret marker must parse the free-text message.

**Fix**: extract `lineno` from the exception's `__traceback__` chain:

```python
except Exception as exc:
    if has_alarm:
        signal.alarm(0)
    tb = exc.__traceback__
    user_line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == "<compute>":
            user_line = tb.tb_lineno
        tb = tb.tb_next
    tb_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    message = format_compute_traceback(tb_text).strip()
    return {
        "id": request_id,
        "ok": False,
        "code": "E1151",
        "message": message,
        "line": user_line,
        "col": None,
    }
```

---

## Additional Observations (Non-Critical)

### `__builtins__` dict readable from author code
Authors can read `x = __builtins__` and get the full whitelisted-function dict. At
runtime they can call functions through it (`__builtins__["len"]([])` works). This has
no security impact because no blocked function is present in the dict and the AST scanner
prevents any reference that would introduce one. However, as defense-in-depth the dict
could be wrapped in a `types.MappingProxyType` to block `.update()` / `del` / `[k] =` at
the C level, or the key `"__builtins__"` could be set to `None` after namespace
construction (CPython interprets `None` as "use real builtins" but only when it is the
module's `__builtins__`, not inside `exec()`).

### `repr(fn)` includes memory address
`repr(f)` where `f` is a `def` inside a compute block returns a string like
`<function f at 0x106f009d0>`. This address is non-deterministic across runs but is not
a meaningful security risk (no pointer arithmetic possible inside the sandbox). It does
break reproducible output if an author accidentally includes `repr(f)` in a binding
that ends up in the animation HTML.

### Computed bigint via `pow(b, e)` with injected `e`
On Python 3.11+, `str(pow(2, 100_000))` raises `ValueError: Exceeds the limit (4300) for
integer string conversion` — this is caught as E1151. On Python 3.10 (in use here via the
system Python) the computation succeeds silently. A document using Python 3.10 and
`pow(b, large_e)` would produce a very large integer that the JSON serializer must traverse,
potentially causing a slow response. The `_MAX_INT_LITERAL` AST check only catches
**literals**, not computed results. Adding a post-execution size check on integer bindings
(e.g., reject ints with `bit_length() > 200_000`) would close this gap.

### Windows: no wall-clock guarantee
On Windows, neither SIGALRM nor RLIMIT_CPU/RLIMIT_AS is available. Only the step counter
(`_STEP_LIMIT = 10**8`) defends against runaway code, and C-level calls (e.g.
`[0] * 9_000_000`) do not tick the step counter at all. The `RuntimeWarning` is emitted
once, but there is no enforced bound on wall-clock time for C-level operations on
Windows. The transport-level timeout (default 10 s in `default_timeout`) is the only
safety net.

### Response `ensure_ascii` mismatch
The host uses `ensure_ascii=True` when writing requests (correct for the line-oriented
protocol). The worker uses `ensure_ascii=False` when writing responses (line 708, 725,
738). Non-ASCII characters in binding values would be written as literal UTF-8 in the
response line. Because `sys.stdout` in text mode uses the locale encoding (typically
UTF-8), this works correctly on most systems but could corrupt the stream on a system
with a non-UTF-8 locale. Using `ensure_ascii=True` on both sides is the safer choice.
