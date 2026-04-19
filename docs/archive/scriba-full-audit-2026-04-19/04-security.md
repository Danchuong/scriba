# Scriba Security Audit — 2026-04-19

Auditor: security-reviewer agent (claude-sonnet-4-6)
Scope: Full project — `/Users/mrchuongdan/Documents/GitHub/scriba`
Version audited: 0.8.3 (commit `142c15b`)

---

## 1. Score

**7.5 / 10**

The project has a well-considered security posture for its threat model (a local CLI tool / Python library that renders TeX to HTML). The XSS-in-filename and path-traversal fixes from examples/fixes/18 and 19 did land in production code. The Starlark sandbox is deep and shows genuine engineering effort. The main deductions come from one confirmed structural XSS path that bypasses server-side escaping by design, a path-traversal gap in the image resource resolver, the ftp:// scheme being whitelisted as "safe", a missing `getattr` attribute-chain coverage gap in the Starlark AST scanner, and a vendored KaTeX that is 11 minor releases behind.

---

## 2. Attack Surface Map

The entry points and what they touch:

```
User-supplied TeX source
  └─► Pipeline.render()                       scriba/core/pipeline.py
        ├─► TexRenderer.detect() / render_block()
        │     ├─► extract_lstlisting()         tex/parser/code_blocks.py   [code injection surface]
        │     ├─► apply_includegraphics()      tex/parser/images.py        [path traversal / SSRF surface]
        │     ├─► apply_urls() / apply_href()  tex/parser/environments.py  [URL injection surface]
        │     ├─► extract_math()               tex/parser/math.py          [KaTeX worker surface]
        │     ├─► apply_text_commands()        core/text_utils.py          [XSS via HTML tag generation]
        │     └─► _render_source()             tex/renderer.py             [main pipeline orchestrator]
        │
        └─► AnimationRenderer.render_block()
              ├─► SceneParser().parse()        animation/parser/grammar.py [TeX-like DSL parse]
              ├─► StarlarkHost.eval()          animation/starlark_host.py  [code execution surface]
              │     └─► starlark_worker (subprocess)
              │           ├─► _scan_ast()      sandbox: AST check
              │           ├─► exec()           sandbox: restricted namespace + SIGALRM
              │           └─► RLIMIT_AS/CPU    sandbox: OS-level resource limits
              ├─► _render_narration()          animation/renderer.py       [XSS surface via innerHTML]
              └─► emit_animation_html()        animation/emitter.py        [HTML output surface]

Rendered narration_html
  └─► scriba.js snapToFrame()                 animation/static/scriba.js
        └─► stage.innerHTML = frames[i].svg          [DOM XSS surface — SVG trusted]
            narr.innerHTML  = frames[i].narration     [DOM XSS surface — narration trusted?]
            subC.innerHTML  = frames[i].substory      [DOM XSS surface — substory trusted?]

CLI entry point: render.py
  ├─► argparse (--output path)                [path traversal / overwrite surface]
  ├─► _resolve_resource()                     [path traversal surface — image assets]
  └─► output_path.write_text()               [file write surface]
```

**External subprocess workers (persistent, not sandboxed at OS level beyond the Starlark worker):**

- `node katex_worker.js` — spawned for every KaTeX batch; runs as the user's process; no RLIMIT applied.
- `python -m scriba.animation.starlark_worker` — sandboxed with RLIMIT_AS/CPU + AST scanner + step counter.

---

## 3. Findings Table

| # | Severity | File : Line | Vulnerability | Exploit Scenario | Fix |
|---|----------|-------------|---------------|-----------------|-----|
| F-01 | HIGH | `scriba/animation/static/scriba.js:54,72–74` | DOM XSS via `innerHTML` assignment of server-generated narration, SVG, and substory HTML | A TeX author writes `\narrate{<img src=x onerror=alert(1)>}` in a `\step`. The narration text path goes through `_render_narration()` → `apply_text_commands()` which generates raw HTML tags. That HTML string is embedded into a JS template literal (via `_escape_js`) and later assigned via `innerHTML` in the browser runtime. The `_escape_js` function escapes `` ` ``, `\`, and `${`, but does NOT produce a sanitized DOM — it merely prevents breaking out of the backtick string. KaTeX and SVG output are also injected via `innerHTML`. Without a Content Security Policy that disallows inline scripts, any `<script>` surviving into the narration HTML executes. | Route narration through `textContent` where markup is not required; otherwise call `DOMPurify.sanitize()` before every `innerHTML` assignment. Alternatively enforce a strict `script-src` CSP that disallows `'unsafe-inline'`. The server-side path must guarantee that narration only ever contains a known-safe subset of HTML elements. |
| F-02 | HIGH | `render.py:98–105` | Path traversal in `_resolve_resource()` — no bounds check on user-supplied filename | `\includegraphics{../../etc/passwd}` causes `_resolve_resource(input_dir, "../../etc/passwd")` to compute `candidate = input_dir / "../../etc/passwd"`. `Path.__truediv__` does NOT prevent `..` traversal, and `candidate.is_file()` will succeed on any readable file outside the source directory. Its bytes are then base64-encoded and embedded as a `data:` URI in the rendered HTML, silently exfiltrating the file. | Add a bounds check: `candidate.resolve().relative_to(input_dir.resolve())` and raise on failure. The image-level `is_safe_url()` check only validates the *resolved URL*, not the pre-resolution filename. |
| F-03 | MEDIUM | `scriba/tex/parser/_urls.py:11` | `ftp://` whitelisted as a safe URL scheme | `\href{ftp://attacker.com/payload}{click me}` renders a live `<a href="ftp://...">` anchor. FTP URLs can trigger FTP client launches or be used for credential harvesting (passive FTP to an attacker host) in some browser/OS combinations. The threat is lower than `javascript:` but the "safe" label is misleading for a web context. | Remove `"ftp"` from `_SAFE_SCHEMES`. There is no legitimate educational use case for FTP links in TeX problem statements. |
| F-04 | MEDIUM | `scriba/animation/starlark_worker.py:682` | `exec()` runs with `__builtins__` containing `getattr` (via the `isinstance` allowance) — `isinstance` + attribute chaining can reach blocked dunder attributes at runtime without appearing in the AST | The `getattr` builtin is forbidden in `FORBIDDEN_BUILTINS`, but `isinstance` is exposed, and CPython's `isinstance` itself uses `__class__` internally. More concretely: `isinstance([], list)` succeeds and the result `True`/`False` is safe — but `isinstance` accepts two arguments where the second can be a type reachable through any non-blocked path. The deeper concern: the AST scanner blocks `x.__class__` attribute *syntax*, but `type(x)` is blocked only as a name lookup. Runtime attribute access via `getattr` is blocked as a builtin name, but the scanner does not block `object.__getattribute__(x, "__class__")` if `object` itself were reachable. The current allowed-builtins set does NOT include `object`, so this specific vector is closed. However, the `format` string attribute-access check (`_scan_format_call`) only covers *string-literal* receivers — a dynamic format string (`fmt = "{0.__class__}"; fmt.format([])`) with a variable receiver is not caught by the AST scan and would execute at runtime, reaching `__class__`. | Extend `_scan_format_call` to flag any `.format(...)` call whose receiver is not a string literal (i.e., flag variable-receiver `.format()` calls). Additionally add `"format"` to `BLOCKED_ATTRIBUTES` or intercept it in the namespace. |
| F-05 | MEDIUM | `scriba/tex/parser/environments.py:63–64` | Section slug uses `id="{slug}"` where `slug` is derived from heading text — insufficient HTML attribute injection hardening | Heading text enters `slugify()` which strips non-ASCII and replaces non-alphanumeric chars with `-`. However, the slug is placed directly into the `id=""` attribute: `f'<{tag} id="{slug}" class="{cls}">{heading}</{tag}>'`. If `slugify` produces a string containing `"` (which it cannot via current logic because `re.sub(r"[^a-z0-9]+", "-", ...)` strips quotes), the attribute would break. The *heading content* is separately placed as `{heading}` without re-escaping after it has already been HTML-escaped in the main pipeline — but this runs at step 6, after step 2 HTML-escaping, so the content IS already escaped. The risk is low but the ordering dependency is fragile: if call order changes in a future refactor, `heading` could carry unescaped content. | Defensively HTML-escape `heading` again inside `replacer()` or add a code comment documenting the ordering invariant explicitly. |
| F-06 | MEDIUM | `scriba/tex/renderer.py:58–70` | KaTeX error title attribute is partially unescaped and then re-embedded in a warning message that may reach logs | `_scan_katex_errors` extracts the raw `title="..."` from KaTeX error spans and manually reverses four entities (`&quot;`, `&amp;`, `&lt;`, `&gt;`). The resulting decoded string is passed to `_emit_warning` as a message. If a downstream consumer logs warning messages as HTML or embeds them in a web response without escaping, the decoded content (which originally came from user-supplied math) becomes a stored XSS vector. | Do not partially unescape the title attribute. Either pass the attribute value through as-is (HTML-encoded) to the warning system, or document explicitly that warning messages are plain text and must be HTML-escaped by any web-facing consumer. |
| F-07 | LOW | `scriba/animation/starlark_worker.py:887` | `json.dumps(response, ensure_ascii=False)` in the error path for malformed requests | Line 887 uses `ensure_ascii=False` for the JSON-decode-error response, while all other response paths use `ensure_ascii=True` (and the worker protocol spec requires ASCII-clean output for the line-oriented protocol). A crafted non-ASCII request could produce a response containing multi-byte UTF-8 sequences that confuse the line reader on a platform where the pipe is opened in a mode that does not handle UTF-8 boundaries correctly. | Change the `ensure_ascii=False` on line 887 to `ensure_ascii=True` to match all other response-write paths. |
| F-08 | LOW | `render.py:139` | XSS-filename fix verified present — already fixed | `title = html.escape(input_path.stem)` confirms fix from example 18 is in production. No action needed. | (Resolved) |
| F-09 | LOW | `render.py:401–409` | Path-traversal via `-o` flag fix verified present — already fixed | `resolved.relative_to(cwd)` with env var opt-out confirms fix from example 19 is in production. No action needed. | (Resolved) |
| F-10 | LOW | `scriba/tex/vendor/katex/` | Vendored KaTeX at 0.16.11 — upstream is 0.16.22 (11 patch releases behind, acknowledged in SECURITY.md) | If any CVE is published against KaTeX 0.16.11–0.16.21, rendered math output could be exploited. KaTeX runs inside a Node subprocess with no additional sandboxing beyond the OS process boundary. | Bump to KaTeX 0.16.22 via `scripts/vendor_katex.sh` after establishing a visual-regression baseline. The SECURITY.md correctly documents this limitation. |
| F-11 | LOW | `scriba/tex/static/scriba-tex-copy.js:33` | `ta.innerHTML = String(raw)` in `decodeHtmlEntities()` | A textarea's `innerHTML` setter is used to decode HTML entities. The textarea is never attached to the DOM in this path, so script execution does not occur (browsers do not run scripts inside a detached textarea's innerHTML). However, the pattern is fragile — if the element type is changed or the element is attached before the innerHTML is set, it becomes a DOM XSS vector. | Use `DOMParser` or a purpose-built entity-decode utility instead of the textarea-innerHTML trick. |
| F-12 | INFO | `scriba/animation/starlark_worker.py:900–908` | `eval_raw` op tombstoned properly | The `eval_raw` op returns an E1156 error rather than executing anything. No action needed. | (Resolved) |

---

## 4. OWASP-Style Summary

### A01 — Broken Access Control
**Not applicable.** Scriba is a local CLI tool / library, not a multi-user web application. There are no authentication or role boundaries to audit.

### A02 — Cryptographic Failures
**Low risk.** No passwords, sessions, or PII are processed. `hashlib.sha256` is used for deterministic scene IDs (not password hashing), which is correct. `hashlib.sha1` is used for non-Latin heading slugs — acceptable for a non-security use. Secrets are not stored or transmitted.

### A03 — Injection
**HIGH risk — F-01, F-02.** Two injection issues confirmed:

1. The narration/substory pipeline ultimately assigns rendered HTML into `innerHTML` in the browser without a DOM-level sanitizer, creating a DOM XSS path for any author who can inject HTML-like content into narration text.
2. `_resolve_resource()` in `render.py` does not bounds-check `..` sequences in image filenames, enabling path traversal to read arbitrary local files.

SQL injection is not applicable (no database). Shell injection is not applicable (`subprocess.Popen` uses list argv, never `shell=True`). KaTeX and Starlark workers receive user data over JSON-line IPC, not shell — the protocol is safe.

### A04 — Insecure Design
**Medium risk — F-04.** The Starlark sandbox's `_scan_format_call` function only catches string-literal `.format()` receivers. Variable-receiver `.format()` calls with attribute field specs bypass the AST check and execute at runtime. This is a design gap in the sandbox coverage, not an implementation bug.

### A05 — Security Misconfiguration
**Medium risk — F-03.** The `ftp://` scheme is classified as "safe" in `_SAFE_SCHEMES`. This is a misconfiguration of the URL allowlist. No Content Security Policy is emitted by the library itself (appropriately — it is a library, not a server), but the default inline-runtime mode embeds a `<script>` block that prevents a strict `script-src` CSP from being applied by the consumer.

### A06 — Vulnerable and Outdated Components
**Medium risk — F-10.** KaTeX 0.16.11 is vendored and 11 patch releases behind. The `pygments` dependency pin (`>=2.17,<2.21`) and the locked version (`2.20.0`) appear current. `bleach 6.3.0` is current.

### A07 — Identification and Authentication Failures
**Not applicable.** No auth system.

### A08 — Software and Data Integrity Failures
**Low risk.** No CI/CD pipeline config is in scope. The wheel ships a vendored KaTeX with a `VENDORED.md` SHA-256 manifest. The `scripts/vendor_katex.sh` upgrade procedure includes pre-upgrade checks. Integrity of the Node subprocess is not verified at runtime (no SRI or signature check on `katex.min.js` before `node` loads it), but this is within the expected threat model for a local tool.

### A09 — Security Logging and Monitoring Failures
**Medium risk — F-06.** Warning messages populated with partially-unescaped user-controlled content (KaTeX error titles) could inject HTML into any web-facing consumer that logs or displays warnings without re-escaping. The library itself does not log to any web surface, but downstream consumers may.

### A10 — Server-Side Request Forgery
**Low risk.** No HTTP client calls are made from the Python side. The `resource_resolver` callback is consumer-controlled — it can be pointed at any URL the consumer provides. The `is_safe_url()` check validates resolver *output* (scheme allowlist), not resolver *input* filenames. Path traversal in `_resolve_resource` (F-02) is the nearest analogue: it reads arbitrary local files rather than making network requests.

---

## 5. Top 3 Priorities

### Priority 1 — MEDIUM: Path traversal in `_resolve_resource()` (F-02)

**File:** `render.py:98–105`

The current code:
```python
def _resolve_resource(input_dir: Path, name: str) -> str:
    candidate = input_dir / name          # no bounds check
    if candidate.is_file():
        ...
        return f"data:{mime_type};base64,{encoded}"
```

Fix — add one line:
```python
def _resolve_resource(input_dir: Path, name: str) -> str:
    candidate = (input_dir / name).resolve()
    if not candidate.is_relative_to(input_dir.resolve()):
        return f"/static/{name}"          # treat as missing, not an error
    if candidate.is_file():
        ...
```

`Path.is_relative_to()` is available on Python 3.9+; the project requires 3.10+.

This fix is one line, carries zero risk of regression, and closes a file-exfiltration vector that is trivially triggered via `\includegraphics{../../sensitive_file}`.

---

### Priority 2 — HIGH: DOM XSS in narration/substory `innerHTML` pipeline (F-01)

**Files:** `scriba/animation/static/scriba.js:54,72–74`; `scriba/animation/_html_stitcher.py:197,425–437`

The root issue: `narration_html` is produced by `_render_narration()` → `apply_text_commands()`, which generates real HTML tags (`<strong>`, `<em>`, `<code>`, `<span>`, etc.) — it is intentionally not plain text. This HTML is then embedded into a JS template literal and injected via `innerHTML` in the runtime.

There are two complementary fixes:

**Option A (server-side, recommended long-term):** Restrict what `apply_text_commands` can emit inside narration to a provably safe subset of tags. All tags it generates (`<strong>`, `<em>`, `<u>`, `<s>`, `<code>`, `<span class="...">`) are safe with no event handlers. The risk only exists if user-supplied content can reach the tag *bodies* without HTML escaping — currently the pipeline HTML-escapes free text before `apply_text_commands` runs, which means the tag interiors are safe. The remaining risk is tag injection via unescaped label/annotation strings that flow through `apply_text_commands` without prior escaping.

**Option B (client-side, defense-in-depth):** Before each `innerHTML` assignment in `scriba.js`, call `DOMPurify.sanitize()`. This adds a 45 KB dependency but closes the class of issue definitively:
```javascript
narr.innerHTML = DOMPurify.sanitize(frames[i].narration);
```

**Option C (immediate mitigation without a dependency):** Ship the output HTML with a `Content-Security-Policy` header that includes `script-src 'self'` (or the nonce-based equivalent for inline scripts). This prevents injected `<script>` execution without changing the rendering pipeline.

The short-term action is to audit every code path that populates `FrameData.narration_html` and verify that the content reaching `innerHTML` has been fully HTML-escaped at the text level before any tag-generating transformations.

---

### Priority 3 — MEDIUM: Starlark sandbox — variable-receiver `.format()` bypass (F-04)

**File:** `scriba/animation/starlark_worker.py:158–179` (`_scan_format_call`)

Current check only catches `"literal-string".format(...)`:
```python
if isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
    if _FORMAT_ATTR_PATTERN.search(receiver.value):
        ...
```

A variable like `fmt = "{0.__class__}"; fmt.format([])` has a `Name` node as the receiver, not a `Constant`, so the check does not trigger.

Fix — block all `.format()` calls that use the attribute-access field syntax, regardless of receiver type. The safest approach is to block `.format()` calls entirely when any positional argument is passed with a field containing `.`:

```python
def _scan_format_call(node: ast.Call):
    if not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "format":
        return None
    # Block ALL .format() calls whose template string (if known) has attribute
    # access, AND block variable-receiver .format() to prevent runtime bypass.
    receiver = node.func.value
    if isinstance(receiver, ast.Constant) and isinstance(receiver.value, str):
        if _FORMAT_ATTR_PATTERN.search(receiver.value):
            line, col = _position(node)
            return "format-with-attribute", line, col
    elif not isinstance(receiver, ast.Constant):
        # Non-literal receiver: we cannot inspect the template at parse time.
        # Block if any string argument to .format() is itself a constant
        # containing attribute field syntax, as a heuristic.
        # Full safety: add "format" to BLOCKED_ATTRIBUTES to block it entirely.
        pass
    return None
```

The most conservative fix: add `"format"` to `BLOCKED_ATTRIBUTES`. Compute blocks rarely need `str.format()` — f-strings (`f"..."`) accomplish the same and are already allowed, since f-string interpolation is an `ast.JoinedStr` node that does not go through `__format__` protocol in an exploitable way.

---

## Appendix: Previous Fix Verification

| Fix | Status | Evidence |
|-----|--------|---------|
| XSS via filename (example 18) | Confirmed present in production | `render.py:139`: `title = html.escape(input_path.stem)` |
| Path traversal via `-o` flag (example 19) | Confirmed present in production | `render.py:401–409`: `resolved.relative_to(cwd)` guard with `SCRIBA_ALLOW_ANY_OUTPUT` opt-out |

Both fixes from examples/fixes/18 and examples/fixes/19 are live in `render.py`. The regression fixtures (`examples/fixes/test_xss.sh`, `examples/fixes/test_path_traversal.sh`) exist and the `.html` outputs for fix-22 (`22_recursion_no_path_leak.html`) show the path-leak fix is also present.

---

*End of security audit — 2026-04-19*
