# Wave 8 Audit — P1: CLI Ergonomics + Error UX

**Date:** 2026-04-18  
**Auditor:** Claude (Sonnet 4.6)  
**Scope:** `render.py` CLI, `scriba/core/errors.py`, `scriba/animation/errors.py`

---

## Methodology

- Read `render.py` end-to-end; inventoried all 11 flags with defaults, types, and help text.
- Traced every `sys.exit()` call (2 explicit) and every unhandled-exception path (uncaught `ScribaError` subclasses propagate as tracebacks).
- Ran `python3 render.py --help` and captured verbatim output.
- Executed 10 deliberate-mistake reproducer runs (see findings below), capturing stdout and stderr separately using `2>/dev/null` / `1>/dev/null` redirects.
- Inspected all `print()` calls in `render.py` for stdout/stderr correctness.
- Confirmed E-code formatting via `scriba/core/errors.py __str__` (code, location, hint, docs URL).

---

## Findings Table

| ID | Severity | Class | Location | Effort |
|----|----------|-------|----------|--------|
| F-01 | 🔴 | Unhandled traceback on library error | `render.py:361` (no try/except in `main`) | S |
| F-02 | 🟠 | "File not found" printed to stdout, not stderr | `render.py:345-346` | XS |
| F-03 | 🟠 | Silent success on non-`.tex` input | `render.py:344` (no extension check) | XS |
| F-04 | 🟠 | Silent success on missing `\begin{animation}` | `render.py:171` / `render_file` | S |
| F-05 | 🟠 | Output overwrites `.tex` source silently | `render.py:348` (no output collision guard) | XS |
| F-06 | 🟠 | E1116 (undeclared shape) emitted as `UserWarning`, not stderr error | `scriba/animation/scene.py:710` | S |
| F-07 | 🟡 | `--inline-runtime` shown in `--help` as a usable flag but it is a no-op (default=True) | `render.py:298-306` | XS |
| F-08 | 🟡 | `--copy-runtime` with `--asset-base-url` silently ignored; no diagnostic | `render.py:261` | XS |
| F-09 | 🟡 | `--help` has no usage examples for the external-runtime workflow | `render.py:273` (docstring) | XS |
| F-10 | 🟡 | Output dir write failure (PermissionError, no-such-dir) produces raw Python traceback | `render.py:258` | S |
| F-11 | 🔵 | `--lang` not validated against BCP 47; silently accepts garbage | `render.py:294-296` | S |
| F-12 | 🔵 | Success message ("Rendered … ->") goes to stdout; mixing with `--dump-frames` JSON | `render.py:224,269` | XS |

---

## Per-Finding Detail

### F-01 🔴 — Unhandled traceback on library error

`main()` has no `try/except` around `render_file()`. Any `ScribaError` subclass (E1400, E1151, WorkerError, PermissionError, etc.) propagates as a raw Python traceback on stderr. Users see internal file paths and no guidance.

**Before (stderr for `\shape{foo}{Array}{}`)**
```
Traceback (most recent call last):
  File ".../render.py", line 377, in <module>
    main()
  ...
  File ".../scriba/animation/primitives/array.py", line 96, in __init__
    raise animation_error(...)
scriba.animation.errors.AnimationError: [E1400]: Array requires 'size' or 'n' parameter
  hint: example: \shape{a}{Array}{size=10}
  -> https://scriba.ojcloud.dev/errors/E1400
EXIT: 1
```

The E-code and hint are present — but buried after 12 lines of traceback. The exit code is 1 (correct) but only because Python's default uncaught-exception handler uses 1.

**After (suggested stderr)**
```
error [E1400]: Array requires 'size' or 'n' parameter
  hint: example: \shape{a}{Array}{size=10}
  -> https://scriba.ojcloud.dev/errors/E1400
EXIT: 1
```

**Fix:** Wrap `render_file(...)` in `main()` with:
```python
except ScribaError as exc:
    print(f"error {exc}", file=sys.stderr)
    sys.exit(1)
```

---

### F-02 🟠 — "File not found" printed to stdout

`render.py:345` uses `print(f"File not found: {args.input}")` with no `file=sys.stderr`. Diagnostic messages must go to stderr so shell pipelines and CI log parsers work correctly.

**Before (stdout)**
```
$ python3 render.py missing.tex > /dev/null
File not found: missing.tex     # ← appears on stdout
```

**After**
```python
print(f"error: file not found: {args.input}", file=sys.stderr)
```

---

### F-03 🟠 — Silent success on non-`.tex` input

Passing a `.pdf`, `.docx`, or any non-`.tex` file silently produces HTML output. No warning, exit 0.

**Before**
```
$ echo 'dummy' > /tmp/test.pdf && python3 render.py /tmp/test.pdf
Rendered 0 block(s) + 1 TeX region(s) -> /tmp/test.pdf.html
EXIT: 0
```

**After (suggested stderr + exit 1)**
```
error: input file must have a .tex extension (got: .pdf)
EXIT: 1
```

**Fix:** Add after `args.input.exists()` check (`render.py:344`):
```python
if args.input.suffix.lower() != ".tex":
    print(f"error: expected a .tex file, got '{args.input.suffix}'", file=sys.stderr)
    sys.exit(1)
```

---

### F-04 🟠 — Silent success on missing `\begin{animation}`

A `.tex` file with no animation block renders exit 0, producing valid but content-free HTML with "0 block(s)". New users following a tutorial who forget the environment wrapper get no diagnostic.

**Before**
```
$ python3 render.py plain.tex
Rendered 0 block(s) + 1 TeX region(s) -> plain.tex.html
EXIT: 0
```

**After (suggested stderr warning)**
```
warning: no \begin{animation} or \begin{diagram} blocks found in plain.tex
         If this is intentional, pass --allow-plain-tex to suppress.
Rendered 0 block(s) + 1 TeX region(s) -> plain.tex.html
EXIT: 0
```

Note: this should remain a warning (exit 0), not an error, since plain TeX rendering is a valid use case in principle.

---

### F-05 🟠 — Output overwrites `.tex` source silently

When run from the same directory as the input, `-o input.tex` passes the path-traversal guard (`render.py:351-358`) and silently overwrites the `.tex` source with HTML.

**Before**
```
$ cd /tmp && python3 render.py test.tex -o test.tex
Rendered 0 block(s) + 1 TeX region(s) -> test.tex
EXIT: 0
# test.tex is now an HTML file
```

**After (suggested stderr + exit 1)**
```
error: output path 'test.tex' would overwrite the input file
EXIT: 1
```

**Fix:** After `output` is resolved (`render.py:348`), add:
```python
if args.output and Path(args.output).resolve() == args.input.resolve():
    print("error: output path would overwrite the input file", file=sys.stderr)
    sys.exit(1)
```

---

### F-06 🟠 — E1116 undeclared shape is a silent `UserWarning`

A reference to an undeclared shape name emits `UserWarning` via `warnings.warn()` at `scene.py:710`. The render succeeds (exit 0), the warning appears in a `warnings.warn` context block, and it is fully suppressed when a consumer runs with `-W ignore`. This is a logic error the user will not notice until the output is wrong.

**Before (stderr, exit 0)**
```
.../scene.py:710: UserWarning: [E1116] mutation command references undeclared shape 'barbar'...
  warnings.warn(
Rendered 1 block(s) + 0 TeX region(s) -> ...
EXIT: 0
```

**After (suggested)**

E1116 should be promoted to a raised `AnimationError` (exit 1), or at minimum printed directly to stderr unconditionally (not via `warnings.warn`), with a clear "shape 'barbar' not declared" message.

---

### F-07 🟡 — `--inline-runtime` flag is effectively a no-op

`--inline-runtime` is `default=True` and `action="store_true"`. Passing it explicitly changes nothing. The help text reads "Deprecated: will no longer be the default in v0.9.0" — but `--help` lists it as a peer of `--no-inline-runtime`, which is confusing: users may think they need to pass it to get the current behavior.

**Before (--help excerpt)**
```
--inline-runtime   Inline the full JS runtime into the HTML (default; works
                   on file://). Deprecated: will no longer be the default in v0.9.0.
```

**After (suggested)**

Remove `--inline-runtime` from `--help` output (use `argparse.SUPPRESS`) or add a note "(passing this flag has no effect in v0.8.x)".

---

### F-08 🟡 — `--copy-runtime` with `--asset-base-url` silently ignored

When both `--copy-runtime` (default: True) and `--asset-base-url` are passed, the copy is silently skipped (`render.py:261`). No diagnostic tells the user their flag was ignored.

**Before**
```
$ python3 render.py input.tex --no-inline-runtime --asset-base-url https://cdn.example.com
Rendered 1 block(s) + 0 TeX region(s) -> input.html
EXIT: 0
# scriba.*.js was NOT copied — no indication
```

**After (suggested)**
```
note: --copy-runtime ignored because --asset-base-url is set; runtime will be
      served from https://cdn.example.com/scriba.ce590585.js
```

---

### F-09 🟡 — `--help` has no examples for the external-runtime workflow

The module docstring at the top of `render.py` has four examples — all for the default inline-runtime mode. The three new Wave 8 flags (`--no-inline-runtime`, `--asset-base-url`, `--copy-runtime`) have zero examples in `--help`.

**After (suggested addition to module docstring / epilog)**
```
External runtime (CDN):
    python render.py input.tex --no-inline-runtime --asset-base-url https://cdn.example.com/scriba/0.8.3
    python render.py input.tex --no-inline-runtime   # copies scriba.*.js next to output
```

---

### F-10 🟡 — Output directory write failure gives raw Python traceback

If the output directory does not exist or the file is not writable, `output_path.write_text(...)` at `render.py:258` raises an unhandled `PermissionError` / `FileNotFoundError`.

**Before**
```
Traceback (most recent call last):
  ...
  File ".../pathlib/__init__.py", line 809, in write_text
    ...
PermissionError: [Errno 13] Permission denied: 'readonly_dir/out.html'
EXIT: 1
```

**After (suggested)**
```
error: cannot write output file 'readonly_dir/out.html': Permission denied
EXIT: 1
```

Caught by the same `try/except OSError` block that should wrap `render_file()` (see F-01).

---

### F-11 🔵 — `--lang` not validated

`--lang` accepts any string. `--lang "not a language tag"` silently injects the value into the HTML `lang=` attribute.

**Fix (low priority):** A simple allowlist or regex for BCP 47 format (`[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*`) would catch the common mistake of passing a full locale like `en_US` (should be `en-US`).

---

### F-12 🔵 — Success message and `--dump-frames` JSON share stdout

`--dump-frames` prints JSON to stdout (`render.py:224`). The success message "Rendered … ->" also goes to stdout (`render.py:269`). When both are active, the progress message is appended after the JSON, corrupting the JSON stream for downstream parsers.

**Before**
```
$ python3 render.py input.tex --dump-frames | python3 -m json.tool
Rendered 1 block(s) + 0 TeX region(s) -> input.html   ← injected after JSON
json.decoder.JSONDecodeError: Extra data
```

**Fix:** Move the "Rendered …" progress message to stderr, or guard it with `if not args.dump_frames`.

---

## Recommendations (prioritized)

1. **[F-01] Wrap `render_file()` in `main()` with `except ScribaError`** — print `error {exc}` to stderr and `sys.exit(1)`. This single change eliminates all raw Python tracebacks for library errors and also fixes F-10 when combined with `except OSError`. *Effort: S.*

2. **[F-02] Move "File not found" print to stderr** — one-line fix: add `file=sys.stderr`. *Effort: XS.*

3. **[F-05] Detect output-overwrites-input collision** — compare resolved paths before writing. *Effort: XS.*

4. **[F-03] Reject non-`.tex` input with a clear error** — check `args.input.suffix` after existence check. *Effort: XS.*

5. **[F-06] Promote E1116 from `UserWarning` to a surfaced error** — discuss in Wave 8 whether this should be exit-1 or a mandatory stderr print bypassing `warnings` filters. *Effort: S.*

6. **[F-04] Warn on zero animation blocks** — print to stderr if `len(anim_blocks) + len(diag_blocks) == 0`. *Effort: S.*

7. **[F-12] Send "Rendered …" progress to stderr** — keeps stdout clean for `--dump-frames` JSON piping. *Effort: XS.*

8. **[F-08] Emit a note when `--copy-runtime` is ignored due to `--asset-base-url`**. *Effort: XS.*

9. **[F-09] Add external-runtime examples to `--help` epilog**. *Effort: XS.*

10. **[F-07] Suppress `--inline-runtime` from `--help`** using `argparse.SUPPRESS`. *Effort: XS.*

---

## Exit Code Consistency

Only two exit codes are currently used: **0** (success) and **1** (all errors). This is acceptable for a single-command tool. However, because unhandled exceptions default to exit 1 via the Python runtime (not an explicit `sys.exit`), there is no guarantee of a stable contract. After F-01 is fixed, all error paths should explicitly call `sys.exit(1)` so the contract is code-driven, not coincidental.

---

## Confirmed OK

- **E-code format in `ScribaError.__str__`** — structured with code prefix, location, hint, and docs URL (`scriba/core/errors.py:41-79`). When errors do reach the user (post-traceback), the message quality is high.
- **Path-traversal guard** (`render.py:351-358`) — correctly rejects output paths outside cwd and prints to stderr (`file=sys.stderr`). Exit code 1 is explicit.
- **`--no-inline-runtime` default behaviour** — correctly copies runtime JS next to output HTML and prints "Copied runtime -> …" to inform the user.
- **E1151 Starlark error formatting** — user `\compute{}` frames are isolated by `format_compute_traceback()`; internal Scriba paths are stripped.
- **No-argument invocation** — argparse prints usage and exits 2 correctly.
- **Exit code 2 for argument parse errors** — argparse default; semantically correct (usage error vs runtime error).
