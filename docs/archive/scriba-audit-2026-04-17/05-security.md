# Security Audit — scriba 2026-04-17

**Threat model:** attacker controls `.tex` input files.
Targets: (1) end-users who view the rendered HTML in a browser, (2) the build host running `render.py`.

**Scope:** entire `scriba/` tree plus `render.py`, `pyproject.toml`, `scriba/tex/katex_worker.js`.

**Auditor:** security-reviewer agent (claude-sonnet-4-6), April 17 2026.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1     |
| HIGH     | 1     |
| MEDIUM   | 3     |
| LOW      | 4     |
| INFO     | 3     |

**Total: 12 findings.**
No pickle/deserialization issues. No shell injection. No dependency CVEs in locked versions.

---

## Findings Table

| ID | Severity | Vector | File:Line | Fix Sketch |
|----|----------|--------|-----------|------------|
| S-01 | CRITICAL | XSS — unescaped filename in HTML title and h1 | `render.py:34,44` | `html.escape(input_path.stem)` before template interpolation |
| S-02 | HIGH | Path traversal — `-o` writes to arbitrary filesystem paths | `render.py:219` | Restrict output path to CWD or an explicit allow-list; validate no `..` traversal |
| S-03 | MEDIUM | CSP incompatibility — inline `onclick` + inline `<script>` block force `unsafe-inline` | `render.py:40-43`, `emitter.py:857` | Move onclick to external JS; emit nonce on `<script>` or move frame data to `<template>` / `data-` attributes |
| S-04 | MEDIUM | `innerHTML` assignment in emitter JS widget (`stage.innerHTML = frames[i].svg`) | `emitter.py:1118` | Confirmed trusted pipeline; add a server-side comment and DOM-purify gate if SVG ever accepts raw user text in future |
| S-05 | MEDIUM | Starlark SIGALRM absent on Windows — only step counter limits CPU | `starlark_host.py` | Document limitation; recommend running on Linux/macOS in production; add Windows process kill via `multiprocessing` watchdog |
| S-06 | LOW | Animation `id=` option accepts arbitrary string — no character allowlist enforced at parse time | `grammar.py:530` | Validate `id` against `^[A-Za-z0-9_-]+$` at parse time; downstream `_escape()` and `_escape_js()` handle output correctly but defence-in-depth favours early rejection |
| S-07 | LOW | `_escape_js()` does not escape `\r` / `\n` — embedded newlines in JS template literals produce multi-line strings | `emitter.py:629-638` | Add `\r` → `\\r`, `\n` → `\\n` to `_escape_js()`; prevents semantic confusion in generated JS |
| S-08 | LOW | `html.escape(text, quote=False)` used for body text — correct, but undocumented | `escape.py` | Add inline comment explaining `quote=False` is intentional for body context; reduces future incorrect "fix" risk |
| S-09 | LOW | Textarea innerHTML decode idiom (`ta.innerHTML = String(raw)`) — safe, but pattern looks dangerous | `scriba-tex-copy.js:33` | Add comment; or replace with `DOMParser` / `document.createTextNode` to eliminate false-positive scanners |
| S-10 | INFO | KaTeX `trust: false` blocks all active-content macros (`\href`, `\url`, `\htmlId`, `\class`, `\data`) — confirmed | `katex_worker.js` | No action; document the setting explicitly in security docs |
| S-11 | INFO | No pickle / shelve / marshal anywhere in the codebase | — | No action |
| S-12 | INFO | subprocess uses list argv, `shell=False` — no shell injection possible | `starlark_host.py` | No action |

---

## Confirmed PoCs

### S-01 — CRITICAL: XSS via filename (title + h1)

**Vector:** create a `.tex` file whose stem (name without extension) contains HTML.

**Exploit input — filename:**
```
<img src=x onerror=alert(1)>.tex
```

**Command:**
```bash
uv run python render.py '<img src=x onerror=alert(1)>.tex' -o /tmp/s01_xss.html
```

**Observed output (excerpt):**
```html
<title>Scriba — <img src=x onerror=alert(1)></title>
...
<h1><img src=x onerror=alert(1)></h1>
```

The `<img onerror>` payload is injected verbatim. Any browser loading the file executes the handler. The vector also works with `<script>` tags on filesystems that permit angle-bracket filenames (most Linux/macOS), or with `"` characters to break attribute context if the title were ever used in an attribute.

**Root cause** — `render.py` line ~106 and template lines 34, 44:
```python
title = input_path.stem          # raw — no escaping
...
HTML_TEMPLATE.format(title=title, ...)
# template: <title>Scriba — {title}</title>  and  <h1>{title}</h1>
```

**Fix:**
```python
import html as _html
...
title = _html.escape(input_path.stem)   # ← add this
```

---

### S-02 — HIGH: Path traversal via `-o` flag

**Vector:** caller supplies an absolute output path outside CWD.

**Exploit input:**
```bash
uv run python render.py examples/tutorial_en.tex -o /tmp/owned.html
```

**Observed:** file `/tmp/owned.html` is created and contains full rendered HTML. No error or warning is emitted.

**Escalation scenario:** in a web service or CI pipeline that calls `render.py` with a user-supplied output path, an attacker can write to any path the process user owns — e.g. `~/.ssh/authorized_keys`, a cron script, or an adjacent service's config.

**Root cause** — `render.py` line ~219:
```python
parser.add_argument("-o", "--output", type=Path)
# ... later:
output_path.write_text(full_html, encoding="utf-8")
```
No validation that `output_path` is within a permitted directory.

**Fix:**
```python
output_path = Path(args.output).resolve()
cwd = Path.cwd().resolve()
if not str(output_path).startswith(str(cwd)):
    parser.error(f"Output path must be inside the working directory: {output_path}")
```
Or, for a build-server context, accept only a filename (no path separators) and write into a designated output directory.

---

## Defense Gaps

1. **No output encoding at template boundary (render.py).** The HTML template in `render.py` uses Python's `str.format()` with zero escaping. Any field inserted via `format()` is a potential injection point. Use a proper templating engine (e.g. `jinja2` with autoescape, or `markupsafe.escape`) at this boundary instead of raw `str.format`.

2. **No CSP on generated HTML.** The generated `<html>` page has no `Content-Security-Policy` meta tag. Any embedding server that adds one must use `unsafe-inline` because of the inline `onclick` and inline `<script>` block. This undermines CSP's primary XSS mitigation.

3. **Starlark sandbox platform gap (Windows).** SIGALRM is unavailable on Windows; only the software step counter (`sys.settrace`) limits runaway compute. A sufficiently tight inner-loop that does expensive C-level work (e.g. large list multiplication `[0]*10**7` in one expression — not a `for` loop) could still burn CPU for several seconds before the step counter fires. The RLIMIT_CPU OS-level hard limit is also absent on Windows.

4. **No schema validation on LaTeX command parameters beyond specific cases.** Color and position arguments for `\annotate` are allowlisted (good). But many other parameters (e.g. `id=`, `title=`, `label=` on hashmap / linkedlist / etc.) accept arbitrary strings and rely entirely on downstream escaping. Defence-in-depth favours an allowlist/regex at parse time for every option that ends up in HTML/JS/SVG output.

5. **No rate limiting or input-size cap on `render.py`.** A pathologically large `.tex` file (e.g. millions of `\step{}` calls inside `\foreach`) will consume unbounded host memory and CPU before the Starlark sandbox fires (the sandbox only limits the compute inside `\compute` blocks). The parser and renderer have no equivalent global limits.

---

## Hardening Recommendations (ranked)

### P0 — Fix immediately (CRITICAL)

**R-01: Escape filename before HTML template interpolation.**

In `render.py`, immediately after `title = input_path.stem`, add:
```python
import html as _html
title = _html.escape(input_path.stem)
```
This closes S-01. One line. Zero risk of regression.

---

### P1 — Fix before next public release (HIGH)

**R-02: Restrict `-o` output path to a safe directory.**

Add a CWD-anchored check (see S-02 fix sketch above). For a CLI tool used locally this is a low-severity quality-of-life issue, but for any service wrapper it is a genuine SSRF-adjacent risk.

---

### P2 — Fix in next sprint (MEDIUM)

**R-03: Remove `unsafe-inline` requirement from generated HTML.**

Two changes eliminate the need for `unsafe-inline` in a downstream CSP:
- Convert the theme-toggle `onclick` attribute to a `<script>` event listener in an external `.js` file (or the same file that already loads the widget).
- Emit the frame data as a `<template id="scriba-frames">` block or `data-frames` attribute on a `<div>`, and read it from JS with `JSON.parse(document.getElementById(...).textContent)`. This removes the inline `<script>` block.

Then a strict CSP header becomes possible:
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
```
(`style-src unsafe-inline` may still be needed for KaTeX; audit separately.)

**R-04: Add `\r\n` escaping to `_escape_js()`.**

In `emitter.py`:
```python
def _escape_js(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")
    text = text.replace("${", "\\${")
    text = text.replace("\r", "\\r")   # add
    text = text.replace("\n", "\\n")   # add
    text = text.replace("</script>", "<\\/script>")
    text = text.replace("</style>",  "<\\/style>")
    return text
```

**R-05: Validate animation `id=` at parse time.**

In `grammar.py`, after reading the `id` option value:
```python
import re
_SAFE_ID_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,63}$')

if not _SAFE_ID_RE.match(id_value):
    raise ScribaParseError("animation id must match [A-Za-z][A-Za-z0-9_-]{0,63}")
```

---

### P3 — Hardening / polish (LOW / INFO)

**R-06: Add `str.format()` → Jinja2 autoescape migration for render.py HTML template.**

Long-term, replace the raw `HTML_TEMPLATE.format(...)` call with a `jinja2.Environment(autoescape=True)` template. This makes all future template variables safe by default and eliminates the class of bugs that produced S-01.

**R-07: Add a global input-size cap to render.py.**

Before parsing, check:
```python
MAX_INPUT_BYTES = 5 * 1024 * 1024  # 5 MB
if input_path.stat().st_size > MAX_INPUT_BYTES:
    sys.exit(f"Input file too large (max {MAX_INPUT_BYTES} bytes)")
```

**R-08: Document the Windows Starlark sandbox limitation.**

Add a warning in `starlark_host.py` and the project README that the CPU hard-kill via SIGALRM/RLIMIT_CPU is unavailable on Windows. Recommend running in a Docker container on Linux for untrusted `.tex` input.

**R-09: Replace textarea innerHTML decode with `DOMParser`.**

In `scriba-tex-copy.js`:
```js
// Before (looks dangerous but is safe for <textarea>):
ta.innerHTML = String(raw);

// After (unambiguously safe, passes security scanners):
const doc = new DOMParser().parseFromString(
    `<!DOCTYPE html><body>${raw}`, 'text/html');
ta.value = doc.body.textContent;
```

**R-10: Run `bandit -r scriba/` in CI.**

Add a `bandit` step to the GitHub Actions workflow (or `pre-commit` hook) to catch future Python security regressions automatically. The current codebase is clean; lock it that way.

---

## What Was Confirmed Safe

The following areas were investigated and found to have correct, defence-in-depth implementations:

- **Narration XSS** — `_render_narration()` → `render_inline_tex()` → `html.escape(quote=False)` fires before `apply_text_commands()` inserts tags. Angle brackets from user text are encoded before any HTML structure is added.
- **Annotation label XSS** — `_escape_xml()` is called on every SVG `<text>` node. Confirmed: `\annotate[label=<script>alert(1)</script>]` emits `&lt;script&gt;alert(1)&lt;/script&gt;` in SVG.
- **KaTeX `\href{javascript:...}`** — `trust: false` in `katex_worker.js` causes KaTeX to throw on `\href`, `\url`, `\htmlId`. No JS URL executes.
- **Starlark `__subclasses__` escape** — AST scan blocks dunder attribute access (`__`-prefixed names). `__subclasses__` is unreachable.
- **Starlark `exec` / `import`** — Both blocked at AST level before the code reaches `exec()`.
- **Subprocess injection** — `starlark_host.py` spawns `[sys.executable, "-m", "scriba.animation.starlark_worker"]` with `shell=False`. No user input appears in argv.
- **Pickle / deserialization** — No `pickle`, `shelve`, `marshal`, `yaml.load` (unsafe), or `jsonpickle` anywhere in the codebase.
- **Substory title XSS** — `_escape()` (`html.escape(quote=True)`) applied to `substory_id` and `title` before embedding in HTML attributes.
- **Scene ID JS injection** — `_escape_js()` converts `'` to `\'`, `` ` `` to `` \` ``, `${` to `\${`. Confirmed: `id="x');alert(2);//"` produces syntactically inert JS string in generated output.
- **URL scheme allowlist** — `is_safe_url()` in `_urls.py` rejects `javascript:`, `data:`, `vbscript:` and all unrecognised schemes.
- **Dependency CVEs** — `pygments 2.20.0`, `bleach 6.3.0`, `lxml 6.0.3` — no known critical CVEs at audit date.
