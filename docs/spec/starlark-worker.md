# 07 -- Starlark Worker Wire Protocol

> Status: **locked foundation spec** for Scriba v0.3. This file is the single source of truth for the Starlark worker subprocess wire protocol -- how the main Python process communicates with the Starlark execution host over stdin/stdout. `environments.md` SS5 defines the **language contract** (allowed features, scope rules, determinism); this file defines the **transport and lifecycle**.
>
> Cross-references: [`environments.md`](environments.md) SS5 (Starlark host contract, scope rules, sandboxing), [`01-architecture.md`](architecture.md) SS`SubprocessWorkerPool`, [`03-diagram-plugin.md`](../guides/diagram-plugin.md) SS7 (diagram compute usage), [`09-animation-plugin.md`](../guides/animation-plugin.md) SS7 (animation compute usage, frame-local vs global scope).

## 1. Overview

The Starlark worker is a persistent subprocess registered in the Pipeline's `SubprocessWorkerPool` under the name `"starlark"`. It speaks the same JSON-line protocol as `katex_worker.js` (see `scriba/tex/katex_worker.js`): one JSON object per line on stdin (requests) and one JSON object per line on stdout (responses). Stderr carries the ready signal and diagnostic output.

The worker evaluates Starlark source blocks on behalf of `\compute{...}` commands in both `\begin{animation}` and `\begin{diagram}` environments. It is stateless between requests -- each request carries the full set of global bindings the block should inherit, and the response returns the full set of bindings produced. The host (Python side) owns scope management; the worker is a pure evaluator.

### Design constraints

1. **One worker, shared across plugins.** `AnimationRenderer` and `DiagramRenderer` share a single `"starlark"` worker instance. The `SubprocessWorkerPool` ensures only one registration (idempotent `register()`; see `workers.py` line 406).
2. **No state between requests.** Each `eval` request is self-contained. The worker does not cache bindings, environments, or function definitions across requests. This simplifies crash recovery and makes the worker trivially restartable.
3. **Deterministic output.** Identical `(source, globals)` pairs MUST produce identical `bindings` maps. The worker does not inject randomness, time, or I/O.
4. **Fail-fast error reporting.** Every error is surfaced as a structured JSON response with an error code from `environments.md` SS11.4 (`E1150`--`E1157`). The worker never writes unstructured text to stdout.

## 2. Worker registration

### 2.1 Pool registration

Both `AnimationRenderer` and `DiagramRenderer` register the Starlark worker lazily on first `\compute` invocation. The registration call is idempotent:

```python
pool.register(
    "starlark",
    argv=["python", "-m", "scriba.animation.starlark_worker"],
    mode="persistent",
    ready_signal="starlark-worker ready",
    max_requests=50_000,
    default_timeout=10.0,
)
```

| Parameter         | Value                                           | Rationale                                                                                          |
|-------------------|------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `name`            | `"starlark"`                                    | Shared key for both animation and diagram plugins.                                                 |
| `argv`            | `["python", "-m", "scriba.animation.starlark_worker"]` | Entry point is the `scriba.animation.starlark_worker` module. Uses the same Python interpreter as the host. |
| `mode`            | `"persistent"`                                  | Long-lived subprocess; amortizes startup cost across many `\compute` blocks.                       |
| `ready_signal`    | `"starlark-worker ready"`                       | Emitted on stderr after interpreter initialization. Host blocks until this line appears (up to 10s). |
| `max_requests`    | `50_000`                                        | Restart after 50k successful evaluations to bound memory growth.                                   |
| `default_timeout` | `10.0`                                          | Per-request timeout at the transport level. The Starlark-level timeout (5s) is enforced inside the worker; the transport timeout is a safety net. |

### 2.2 Entry point

The worker entry point is `scriba/animation/starlark_worker/__main__.py`. It:

1. Initializes the Starlark interpreter with the pre-injected builtins from `environments.md` SS5.2.
2. Configures resource limits (SS6).
3. Emits `"starlark-worker ready\n"` on stderr.
4. Enters the request loop: read one JSON line from stdin, evaluate, write one JSON line to stdout.

## 3. Wire protocol

### 3.1 Transport

- **Encoding:** UTF-8.
- **Framing:** Newline-delimited JSON (JSON-line). Each message is exactly one line terminated by `\n`. No multi-line JSON. No length-prefix framing.
- **Direction:** stdin is host-to-worker (requests); stdout is worker-to-host (responses). Stderr is reserved for the ready signal and diagnostic logging.
- **Ordering:** Strictly sequential. The host sends one request, waits for one response, then sends the next. No pipelining, no out-of-order responses.
- **Serialization:** `json.dumps(obj, ensure_ascii=False) + "\n"` on both sides. Values are restricted to JSON-compatible types: strings, numbers (int and float), booleans, `null`, arrays, and objects.

### 3.2 Request types

#### `eval` -- Evaluate Starlark source

The primary request type. Evaluates a Starlark source block in a fresh environment pre-populated with the given globals.

```json
{
  "op": "eval",
  "env_id": "<string>",
  "globals": { "<name>": <json_value>, ... },
  "source": "<starlark_source>"
}
```

| Field      | Type     | Required | Description                                                                                          |
|------------|----------|----------|------------------------------------------------------------------------------------------------------|
| `op`       | string   | yes      | `"eval"`.                                                                                            |
| `env_id`   | string   | yes      | Opaque identifier for the environment instance (e.g., `sha256(block.raw)[:10]`). Used for logging and error attribution only; the worker does not cache state by `env_id`. |
| `globals`  | object   | yes      | Key-value map of bindings to pre-populate in the Starlark global scope before executing `source`. Values must be JSON-serializable. Functions defined in earlier `\compute` blocks are serialized as their source text under a `"__fn__"` wrapper (see SS4). |
| `source`   | string   | yes      | The raw Starlark source from inside the `\compute{...}` braces. Newlines are literal `\n` characters in the JSON string. |

#### `ping` -- Health check

```json
{
  "op": "ping"
}
```

Response:

```json
{
  "ok": true,
  "status": "healthy"
}
```

The host uses `ping` to verify the worker is alive after crash recovery. The `PersistentSubprocessWorker` does not send `ping` automatically; it is available for explicit health checks by the Pipeline or by tests.

### 3.3 Response types

#### Success response (`eval`)

```json
{
  "ok": true,
  "bindings": {
    "<name>": <json_value>,
    ...
  },
  "debug": ["<captured print output line>", ...]
}
```

| Field      | Type     | Description                                                                                          |
|------------|----------|------------------------------------------------------------------------------------------------------|
| `ok`       | boolean  | `true` on success.                                                                                   |
| `bindings` | object   | All top-level bindings after evaluation. Includes both pre-existing globals that were passed in and new bindings created by the source. Functions are serialized as `{"__fn__": "<source>", "name": "<fn_name>"}`. Non-serializable values (if any) are omitted with a `debug` warning. |
| `debug`    | array    | Captured `print()` output, one string per call. Empty array if no `print` calls were made.           |

#### Error response

```json
{
  "ok": false,
  "code": "E11xx",
  "message": "<human-readable error description>",
  "line": 5,
  "col": 12
}
```

| Field     | Type            | Description                                                                     |
|-----------|-----------------|---------------------------------------------------------------------------------|
| `ok`      | boolean         | `false` on error.                                                               |
| `code`    | string          | Error code from `environments.md` SS11.4. One of `E1150`--`E1157`.      |
| `message` | string          | Human-readable description. Includes the Starlark traceback for runtime errors. |
| `line`    | integer or null | 1-indexed line number within the `source` where the error occurred. `null` if not applicable (e.g., timeout). |
| `col`     | integer or null | 1-indexed column number. `null` if not available.                               |

### 3.4 Error code mapping

The worker maps internal Starlark interpreter exceptions to the error codes defined in `environments.md` SS11.4:

| Code   | Condition                                              | Worker behavior                                                         |
|--------|--------------------------------------------------------|-------------------------------------------------------------------------|
| E1150  | Starlark syntax/parse error                            | Return error response with line/col from the parser exception.          |
| E1151  | Starlark runtime error (including memory cap exceeded) | Return error response with traceback in `message`. If the process was killed by OOM, the host receives a `WorkerError` (broken pipe / empty response) and maps it to E1151. |
| E1152  | Wall-clock timeout (>5s)                               | The worker runs a 5s internal alarm. If the alarm fires, it writes an E1152 error response and resets the interpreter. If the worker is unresponsive, the host's transport-level timeout (10s) kills the process and raises `WorkerError`, which the plugin maps to E1152. |
| E1153  | Step-count cap exceeded (>10^8 ops) | The interpreter's step counter callback raises an internal exception. The worker catches it and returns an E1153 error response. |
| E1154  | Forbidden feature detected (`while`, `import`, `class`, `lambda`, `try`, `match`, `:=`, `hash()`, `.format()` with attribute fields, blocked attribute chain) | The worker's pre-parse AST scanner rejects the construct before evaluation. Returns E1154 with the offending line/col. See SS7.1 for the full list. |
| E1155  | Sandbox memory soft-cap exceeded (tracemalloc, 64 MB) | The worker's `_step_trace` tracemalloc check catches allocation peaks above 64 MB and raises `MemoryError` with the `E1155` code prefix. |
| E1173  | `range()` argument exceeds the 10^6 cap                | `_safe_range` rejects requests that would produce more than 1 000 000 elements, raising an `animation_error("E1173", ...)` instead of a bare `ValueError`. Historically this escaped as E1151 (see audit 05-C2). |

## 4. Binding serialization

Starlark values must round-trip through JSON. The worker applies these serialization rules:

| Starlark type     | JSON representation                                                  |
|-------------------|----------------------------------------------------------------------|
| `int`             | JSON number (integer).                                               |
| `float`           | JSON number (float). `NaN` and `Inf` are serialized as `null` with a debug warning. |
| `string`          | JSON string.                                                         |
| `bool`            | JSON boolean (`true` / `false`).                                     |
| `None`            | JSON `null`.                                                         |
| `list`            | JSON array (recursive).                                              |
| `tuple`           | JSON array (recursive). Round-trips as list; the host does not distinguish. |
| `dict`            | JSON object (recursive). Keys must be strings; non-string keys are coerced via `str()`. |
| `set`             | JSON array of sorted elements. Round-trips as list.                  |
| `function`        | `{"__fn__": "<source_text>", "name": "<fn_name>"}`. The host re-evaluates the function source when passing it back in a later `globals` field. |

Values that cannot be serialized (e.g., opaque Starlark internal objects) are replaced with `null` and a warning is appended to the `debug` array.

### 4.1 Function round-tripping

When a `\compute` block defines a function (`def foo(x): ...`), the worker captures the original source text of the function definition and serializes it as a `__fn__` wrapper. On subsequent requests, the host includes the function in `globals`. The worker detects `__fn__` wrappers, re-evaluates the source text to reconstruct the callable, and binds it in the Starlark environment before executing the new `source`.

This ensures that functions defined in one `\compute` block are callable from later blocks, even though the worker is stateless between requests.

## 5. Ready signal

After process startup and interpreter initialization, the worker writes exactly one line to stderr:

```text
starlark-worker ready\n
```

The host's `PersistentSubprocessWorker._spawn()` blocks until this line appears (up to ~10s, per `workers.py` line 112). If the ready signal is not received within the timeout window, the host kills the process and raises `WorkerError("worker 'starlark' did not report ready")`.

The ready signal MUST NOT be written to stdout (stdout is reserved for JSON responses). Diagnostic messages after the ready signal are also written to stderr and are captured by the host's `_drain_stderr()` for inclusion in error reports.

## 6. Resource limits

The worker enforces resource limits per-evaluation to prevent runaway Starlark code from blocking the Pipeline.

| Limit             | Value         | Enforcement mechanism                                          |
|-------------------|---------------|----------------------------------------------------------------|
| Wall clock        | 5 s           | Internal alarm (SIGALRM on Unix) plus host transport timeout.  |
| Starlark ops      | 10^8          | Interpreter step-counter callback. Raises internal exception on breach. |
| Memory            | 64 MB         | Process-level `RLIMIT_AS` (Linux) / `RLIMIT_DATA` (macOS) plus in-process tracemalloc peak-check at the same 64 MB budget. See SS6.4. |
| Recursion depth   | 1000 frames   | Explicit `sys.setrecursionlimit(1000)` at worker startup. See SS6.5. |

### 6.1 Wall-clock timeout

The worker sets a 5-second alarm before each evaluation. If the alarm fires mid-evaluation:

1. The worker interrupts the Starlark interpreter.
2. Writes an `E1152` error response to stdout.
3. Resets internal state and returns to the request loop (the worker is NOT killed).

If the worker is entirely unresponsive (e.g., stuck in a C extension or the interpreter does not honor the interrupt), the host's transport-level `select()` timeout (10s) expires, the host kills the process via `_kill()`, and raises `WorkerError`. The plugin maps this to `E1152`.

#### Windows limitation

`SIGALRM` is not available on Windows, so the wall-clock alarm is a **Unix-only** enforcement mechanism. On Windows the only in-process backstop is the step-counter (SS6.2) — a runaway C-extension builtin that does not tick the trace hook could in theory evade both. The host's 10-second transport-level timeout (see SS8.3) remains as the outermost safety net.

Because Scriba does not currently ship a `threading.Timer` fallback on Windows, this is a **documented known limitation**. Operators running the pipeline on Windows SHOULD either (a) accept the transport timeout as the only wall-clock bound, or (b) run the worker inside a short-lived container that enforces CPU quotas at the OS level. This will be revisited if Windows becomes a primary deployment target.

### 6.2 Step-count cap

The Starlark interpreter's step counter is configured via a callback that fires every N operations. When the counter exceeds the cap:

1. The callback raises an internal `StepLimitExceeded` exception.
2. The worker catches it and writes an `E1153` error response.
3. The worker resets and returns to the request loop.

### 6.3 Memory cap: three layers

Memory is enforced at three layers (strongest to weakest), all pinned to the same 64 MB budget:

1. **OS-level hard cap** — `RLIMIT_AS` on Linux, `RLIMIT_DATA` on macOS, set to **64 MB** in `starlark_host._starlark_preexec` (Unix only). When this is exceeded the kernel SIGKILLs the worker; the host observes a broken pipe and maps it to `E1151`.
2. **In-process tracemalloc check** — fires on every `_MEMORY_CHECK_INTERVAL` (1000 steps) inside `_step_trace`. Peak memory above **64 MB** raises `MemoryError` which the worker converts into an `E1155` response.
3. **Integer- and string-literal pre-scan** — `_MAX_INT_LITERAL` = 10⁷ and `_MAX_STR_LITERAL_LEN` = 10 000 reject the usual `"x" * 10**8` style blowups before evaluation even starts.

Historically these drifted (`RLIMIT_AS` was 256 MB and tracemalloc was 128 MB while the spec already promised 64 MB). Drift between the three layers was the subject of finding 08-C1 of the 2026-04-11 production audit.

On platforms where the `preexec_fn` cannot set the limit (Windows, or certain macOS configurations), the tracemalloc check remains the primary enforcement path. The host's transport-level timeout is the outermost safety net.

### 6.4 Recursion depth

The spec promises a hard cap of 1000 frames. The worker enforces this explicitly by calling `sys.setrecursionlimit(1000)` during `main()` startup, which pins the ceiling independently of the Python interpreter default. Implementations MUST NOT rely on the default limit.

## 7. Security sandboxing

The worker enforces the sandbox constraints from `environments.md` SS5.1 and SS5.4 at two levels:

### 7.1 Pre-parse scan

Before evaluating any source, the worker performs a full **AST walk** (`_scan_ast` in `scriba/animation/starlark_worker.py`). A simple token-level substring match would mis-flag `meanwhile = 3` and miss constructs that do not appear as identifiers (e.g. `match` statements or walrus expressions inside comprehensions), so the walk MUST visit every node produced by `ast.parse`.

The walk rejects the following node types and names:

| Construct                        | Error  | Rationale                                                         |
|----------------------------------|--------|-------------------------------------------------------------------|
| `while`                          | E1154  | Unbounded loops. Authors use `for _ in range(N): ... break`.      |
| `import` / `from ... import`     | E1154  | No external modules. All APIs are pre-injected.                   |
| `load` (Starlark module loading) | E1154  | Disabled for isolation (tracked via the `import` node family).    |
| `class`                          | E1154  | No class definitions. Use dicts or tuples.                        |
| `lambda`                         | E1154  | No anonymous functions. Use `def`.                                |
| `try` / `except`                 | E1154  | No exception handling. Errors propagate to the host.              |
| `match` / `case`                 | E1154  | Custom `__match_args__` can invoke class-level side effects.      |
| walrus `:=` (`ast.NamedExpr`)    | E1154  | Unusual binding scopes and comprehension leaks.                   |
| `hash(...)` builtin              | E1154  | Seeded by `PYTHONHASHSEED` — breaks byte-identical determinism.   |
| `"...{x.attr}...".format(...)`   | E1154  | Format-field attribute lookups are resolved at runtime and bypass the AST scanner entirely. Reported as `forbidden construct 'format-with-attribute'`. |

The walk also blocks attribute access to any name in `BLOCKED_ATTRIBUTES` (see `scriba/animation/constants.py`). The check is **recursive over attribute chains**: `x.append.__self__.__class__` is rejected even though the immediate `.__self__` is not itself dunder-prefixed. The audit found that the previous direct-match scan allowed f-strings like `f"{[].append.__self__.__class__}"` to leak class references; the recursive walk closes that hole.

`BLOCKED_ATTRIBUTES` covers:

- Standard introspection dunders (`__class__`, `__mro__`, `__subclasses__`, `__globals__`, `__builtins__`, `__import__`, `__code__`, `__func__`, `__dict__`, `__reduce__`, `__reduce_ex__`).
- Operator-overloading dunders that can leak internals via indirect lookup (`__class_getitem__`, `__format__`, `__getattr__`, `__getattribute__`, `__set_name__`, `__init_subclass__`).
- Generator / coroutine / async-generator frame-introspection slots (`gi_frame`, `gi_code`, `gi_yieldfrom`, `gi_running`, `cr_frame`, `cr_code`, `cr_running`, `cr_await`, `ag_frame`, `ag_code`).

#### Comprehensions and f-strings are intentionally allowed

`ast.ListComp`, `ast.DictComp`, `ast.SetComp`, `ast.GeneratorExp`, and `ast.JoinedStr` (f-strings) are **intentionally permitted** for compute-block ergonomics — they are idiomatic Python and authors routinely reach for them when manipulating array state for animation primitives. The recursive AST walk descends into their bodies, so any blocked node type, blocked attribute, or forbidden builtin nested inside a comprehension or f-string is still rejected.

If future hardening ever restricts comprehensions, the change MUST bump the spec revision and ship with a migration note for any cookbook recipe that uses them.

### 7.2 Interpreter configuration

- `AllowRecursion = true` (recursive `def` calls are allowed per SS5.1).
- `AllowSet = true` (set literals and `set()` builtin).
- `AllowGlobalReassign = true` (top-level rebinding in successive `\compute` blocks).
- `load()` is disabled (no module loading callback registered).
- No filesystem, network, or OS access is available in the Starlark environment.

### 7.3 Pre-injected builtins

The worker pre-binds exactly these names into the global environment:

```text
len, range, min, max, enumerate, zip, abs, sorted,
list, dict, tuple, set, str, int, float, bool,
reversed, any, all, sum, divmod, repr, round,
chr, ord, pow, map, filter,
isinstance,
print
```

`print(*args)` is captured into the `debug` array of the response. It never writes to the worker's stdout (which is reserved for JSON responses) or stderr.

`range` is replaced with `_safe_range`, which caps its arguments at `_MAX_RANGE_LEN` (1 000 000). Overflows raise an `E1173` animation_error so the host sees a structured response rather than a bare `ValueError`.

`isinstance` is **intentionally allowed**. Compute blocks routinely need `isinstance(x, (int, float))`-style checks, and `type()` is forbidden. `isinstance` cannot by itself reach a blocked class object because `__class__`, `__mro__`, and `__subclasses__` are already rejected by the AST scanner (SS7.1). If this ever changes, update the spec before the sandbox.

Generator `.send(...)` / `.throw(...)` are **intentionally allowed** — they are native attributes of the generator object type, and the red-team audit could not construct an escape using them. They are documented here so future hardening does not silently remove them.

No other names are pre-bound. Authors cannot access Python stdlib, Starlark stdlib extensions, or any host-injected objects beyond this set.

## 8. Lifecycle

### 8.1 Spawn

The worker is spawned lazily by `PersistentSubprocessWorker._spawn()` on the first `send()` call. The spawn sequence:

1. `subprocess.Popen(argv, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True, bufsize=1)`.
2. Wait for `"starlark-worker ready"` on stderr (up to ~10s).
3. On success: worker is ready to accept requests.
4. On failure: drain stderr, kill process, raise `WorkerError`.

### 8.2 Health check

The host can send a `ping` request at any time. If the worker responds with `{"ok": true, "status": "healthy"}`, it is alive. If the worker does not respond within the transport timeout, it is considered dead.

`PersistentSubprocessWorker` also checks `process.poll()` before each `send()`. If the process has exited, it respawns transparently.

### 8.3 Restart policy

The worker is restarted under these conditions:

| Condition                        | Trigger                                          | Behavior                          |
|----------------------------------|--------------------------------------------------|-----------------------------------|
| Crash (non-zero exit)            | `process.poll() is not None` on next `send()`    | Automatic respawn by `_ensure_started()`. |
| Max requests reached             | `request_count >= max_requests` (50,000)          | Graceful kill + respawn.          |
| Timeout (transport-level)        | `select()` returns no data within 10s             | Kill + raise `WorkerError`. Respawn on next `send()`. |
| Memory cap exceeded              | OS kills process (SIGKILL)                        | Detected as crash. Automatic respawn. |
| Explicit close                   | `pool.close()` or `worker.close()`               | Terminate + SIGKILL fallback. No respawn. |

### 8.4 Graceful shutdown

On `worker.close()`:

1. `process.terminate()` (SIGTERM).
2. Wait up to 3s for exit.
3. If still alive: `process.kill()` (SIGKILL).
4. Wait up to 1s.
5. Close stdin/stdout/stderr handles.

The worker SHOULD handle SIGTERM by exiting cleanly (flush any pending output, exit 0). It MUST NOT write partial JSON to stdout on shutdown.

## 9. Sequence diagrams

### 9.1 Normal `eval` flow

```text
Host (Python)                          Worker (subprocess)
     |                                       |
     |--- {"op":"eval", ...} + \n ---------> |
     |                                       | 1. Deserialize request
     |                                       | 2. Reconstruct __fn__ globals
     |                                       | 3. Pre-parse scan (E1154 check)
     |                                       | 4. Set 5s alarm + step counter
     |                                       | 5. Execute Starlark source
     |                                       | 6. Serialize bindings
     | <--- {"ok":true, "bindings":...} + \n |
     |                                       |
```

### 9.2 Error flow

```text
Host (Python)                          Worker (subprocess)
     |                                       |
     |--- {"op":"eval", ...} + \n ---------> |
     |                                       | 1. Pre-parse scan finds "while"
     | <--- {"ok":false,"code":"E1154",...} --|
     |                                       |
     | Plugin maps to RendererError(code="E1154")
```

### 9.3 Timeout flow

```text
Host (Python)                          Worker (subprocess)
     |                                       |
     |--- {"op":"eval", ...} + \n ---------> |
     |                                       | 1. Execute source (infinite loop via for+range)
     |                                       | ... 5s passes ...
     |                                       | 2. SIGALRM fires, interrupt eval
     | <--- {"ok":false,"code":"E1152",...} --|
     |                                       |
     | Plugin maps to RendererError(code="E1152")
```

### 9.4 Crash recovery flow

```text
Host (Python)                          Worker (subprocess)
     |                                       |
     |--- {"op":"eval", ...} + \n ---------> |
     |                                       | OOM: OS sends SIGKILL
     |                                       X (process exits)
     | <--- (broken pipe / empty response)   |
     |                                       |
     | WorkerError raised
     | Plugin maps to RendererError(code="E1151")
     |                                       |
     | Next send():                          |
     | _ensure_started() detects poll()!=None|
     | _spawn() creates new process          |
     |                    starlark-worker ready (stderr)
     |--- {"op":"eval", ...} + \n ---------> |  (new process)
     | <--- {"ok":true, ...} + \n -----------|
```

## 10. Implementation notes

### 10.1 Starlark interpreter choice

The worker uses `starlark-go` compiled as a Python extension (via cgo + cffi) or as a standalone binary. The exact interpreter is an implementation detail not locked by this spec. The requirements are:

- Supports all features in `environments.md` SS5.1 (including recursion).
- Exposes a step-counter callback for enforcing the ops cap.
- Supports interruption for timeout enforcement.
- Pre-injection of custom builtins.

Alternative: a pure-Python Starlark implementation (e.g., `pystarlark`, `starlark-pgo`). The wire protocol is identical regardless of interpreter choice.

### 10.2 Thread safety

The worker subprocess is single-threaded. Concurrent requests from multiple `render_block()` calls are serialized by `PersistentSubprocessWorker._lock` on the host side. The worker never receives concurrent requests.

---

**End of wire protocol spec.** Implementation MUST conform to the request/response schemas in SS3, the error code mapping in SS3.4, the resource limits in SS6, and the security constraints in SS7. The language contract (what Starlark features are allowed and what builtins are injected) is owned by `environments.md` SS5; this file defers to it.
