# Phase 1 — A4 Independent Security Evaluation

**Reviewer:** A4 (independent adversarial reviewer)
**Date:** 2026-04-19
**Scope:** Three security fixes implemented by A2 during Phase 1

---

## Executive Summary

| Fix | Verdict | Severity of Remaining Issues |
|-----|---------|------------------------------|
| Fix #1 — Path traversal in `_resolve_resource()` | APPROVE WITH NOTES | LOW (DoS only, not bypass) |
| Fix #2 — DOM XSS via `innerHTML` narration | REJECT | CRITICAL (untested bypass path) |
| Fix #3 — Starlark `_scan_format_call` variable-receiver bypass | APPROVE WITH NOTES | LOW (scan gap, not exploitable) |

**Overall Phase 1 recommendation: DO NOT COMMIT until Fix #2 is remediated.**

---

## Fix #1 — Path Traversal in `_resolve_resource()`

**File:** `render.py` lines 98–107
**Approach:** `(input_dir / name).resolve()` + `is_relative_to(input_dir.resolve())`

### Adversarial Findings

**Absolute path injection (`name="/etc/passwd"`):**
Verified. `Path(input_dir / "/etc/passwd").resolve()` on POSIX discards the `input_dir` prefix and produces `/private/etc/passwd`. `is_relative_to(input_dir.resolve())` returns `False` and the fix returns the `/static/` fallback. BLOCKED.

**Windows drive injection (`name="C:\\..."`):**
The library specifies `requires-python = ">=3.10"` and has no Windows-specific classifiers, but `Path` behavior on Windows is analogous: an absolute Windows path supplied to `input_dir / name` discards the base just as on POSIX. `resolve()` returns the absolute path; `is_relative_to` returns `False`. BLOCKED. (Not practically tested—no CI runner—but the logic is sound.)

**Symlink traversal:**
`resolve()` follows symlinks before the bounds check. A symlink `input_dir/legit_link.txt -> /tmp/secret.txt` resolves to the target path outside `input_dir`. `is_relative_to` returns `False`. BLOCKED. This is desired behavior: symlinks pointing outside the sandbox are treated as escape attempts.

**TOCTOU race (resolve → is_file):**
The gap between `resolve()` / `is_relative_to()` and `is_file()` / `read_bytes()` is theoretical. Exploiting it requires an attacker to create a non-traversing path, pass the bounds check, then swap the file to a symlink pointing outside before `read_bytes()` is called. The function is called synchronously within a single-threaded render loop. Risk: negligible.

**URL-encoded traversal (`%2e%2e%2f`):**
The `name` parameter comes from `\includegraphics{...}` in `.tex` source files. The TeX parser does not URL-decode values. No URL-decoding occurs between the `.tex` source and `_resolve_resource`. Not a viable attack vector.

**Null byte in `name` (`"img\x00.png"`):**
`Path("img\x00.png")` is created without error (Python 3.14 normalizes the null). However, `.resolve()` raises `ValueError: embedded null byte`, which propagates uncaught. The result is a crash (DoS) rather than a security bypass. Not a bypass, but a hardening gap.

PoC for the DoS (not a security bypass):
```python
from pathlib import Path
_resolve_resource(Path("/tmp/project"), "img\x00.png")
# -> raises ValueError: embedded null byte
```

**Case-insensitive filesystem (macOS HFS+):**
`resolve()` canonicalizes case through the filesystem on macOS. An attacker would need a real directory with the capital-letter name to create a different canonical path, which is impossible using only the existing `input_dir` tree. Not a practical bypass.

### Verdict: APPROVE WITH NOTES

The core sandbox logic is correct and covers all primary attack vectors. Two notes for defense-in-depth:

1. Null bytes in `name` cause an uncaught `ValueError` (DoS, not security bypass). Consider catching `(ValueError, OSError)` around the `resolve()` call and returning the `/static/` fallback.
2. Symlink blocking is a side effect of `resolve()` rather than an explicit policy. If legitimate symlinks within `input_dir` need to be followed (e.g., pointing to other locations inside the same project), the current fix would block them. Document this behavior.

---

## Fix #2 — DOM XSS via `innerHTML` in Narration

**Files modified:** `scriba/animation/_html_stitcher.py` (added `_sanitize_narration_html` using bleach)
**Approach:** Server-side bleach sanitization before narration enters JS frame data

### Adversarial Findings

#### CRITICAL: Substory narration path is unsanitized (bypass confirmed)

`emit_substory_html()` at line 296 of `_html_stitcher.py` populates the `data-scriba-frames` JSON attribute with unsanitized `sub_frame.narration_html`:

```python
json_frames.append({
    "svg": svg_html,
    "narration": sub_frame.narration_html,  # NOT sanitized
})
```

The JS runtime reads this at `scriba.js` line 54:
```javascript
sn.innerHTML = fd[i].narration;
```

This is an innerHTML assignment from unsanitized server-supplied content. Fix #2 does not cover this code path. An author placing `<script>alert('xss')</script>` in a substory narration bypasses the sanitization applied to main-frame narrations.

**PoC bypass:**
The substory frame JSON goes through `_escape(_json.dumps(json_frames))` which HTML-entity-encodes the outer attribute value, but the inner narration string values within the JSON are not bleach-sanitized. When the JS runtime `JSON.parse`s the attribute and assigns `fd[i].narration` to `innerHTML`, the raw HTML (with `<script>` intact) executes.

The regression tests in `test_p2_dom_xss.py` do not test substory narrations. `_frames_with_narration` and `_frames_with_svg` helpers create only main frames; no fixture exercises the substory code path.

#### CRITICAL: `bleach` is a dev-only dependency

`pyproject.toml` lists `bleach>=6.1` under `[project.optional-dependencies.dev]` only. It is not in `[project.dependencies]`. In a production `pip install scriba-tex` environment, `bleach` is not installed. The deferred `import bleach` at line 71 of `_sanitize_narration_html` will raise `ImportError`, crashing every animation render:

```python
def _sanitize_narration_html(html: str) -> str:
    import bleach  # ModuleNotFoundError in production
```

There is no try/except around this import, and no fallback behavior. This fix as deployed would break all production rendering. The security fix is conditional on a non-declared dependency.

#### APPROVED: Main-frame narration path correctly sanitized

For completeness: the `emit_interactive_html` path at line 460 correctly calls `_sanitize_narration_html(frame.narration_html)` before embedding narration into JS frame data. The fix handles both inline-runtime (backtick template, line 461) and external-runtime (JSON island, line 479) modes.

#### bleach whitelist analysis — HIGH risks

**`<a href>` with `javascript:` scheme:** bleach v6 applies protocol checking by default (`ALLOWED_PROTOCOLS = frozenset(['http', 'https', 'mailto'])`). `javascript:`, `vbscript:`, `data:`, and `ftp:` hrefs are stripped. Verified.

**`<svg>` / `<foreignObject>` / `<math>` mutation XSS:** bleach uses a vendored html5lib for parsing. Known mXSS vectors involving `foreignObject` and `annotation-xml encoding="text/html"` are handled correctly at bleach v6.3.0. Verified via live tests. `<script>` is stripped to its text content (`alert(1)`) which does NOT execute when set as `innerHTML` — a text node is not executable.

**`onerror`, `onload`, and other event handlers:** No event-handler attributes appear in `ALLOWED_ATTRS`. bleach strips them. Verified.

**`style` attribute:** Allowed on `div`, `span`, and `img`. bleach v6 strips all style attribute values to an empty string when no `css_sanitizer` is provided. CSS expression injection and `moz-binding` attacks are blocked. Verified.

**`<noscript>` and `<template>` mutation XSS:** bleach strips tags not in `ALLOWED_TAGS`. These produce text content only. Not executable. Verified.

**Protocols on `a[href]`:** bleach strips `javascript:`, `vbscript:`, `data:`, `ftp:` without needing an explicit `protocols=` argument because its default is `['http','https','mailto']`. Verified.

**MEDIUM risk note:** `<foreignObject>` is in `ALLOWED_TAGS`. In an `innerHTML` context with a fully compliant modern browser, this is safe. However, `foreignObject` is a known historical mXSS vector. Its presence in the whitelist should be documented with justification (it is required for KaTeX MathML rendering). If the narration context never requires `foreignObject`, it should be excluded from the narration-specific sanitizer.

### Verdict: REJECT

Two blockers exist:

1. **Substory narration bypass:** `emit_substory_html` line 296 puts unsanitized `sub_frame.narration_html` into the `data-scriba-frames` JSON. The JS runtime assigns it to `innerHTML`. This is the same vulnerability the fix was meant to close, on a different code path that the fix does not cover and the tests do not exercise.

2. **`bleach` not declared as production dependency:** `pyproject.toml` lists bleach under `[dev]` only. The fix will crash production installs with `ModuleNotFoundError`. It must be added to `[project.dependencies]`.

---

## Fix #3 — Starlark `_scan_format_call` Variable-Receiver Bypass

**File:** `scriba/animation/starlark_worker.py`, `_scan_format_call()`
**Approach:** Reject any `.format()` call whose receiver is not an `ast.Constant` string

### Adversarial Findings

**`getattr("{0.__class__}", "format")(payload)`:**
`getattr` is in `FORBIDDEN_BUILTINS` and would be caught by the `ast.Name` scan. Confirmed: `_scan_ast` returns `('getattr', 1, 1)`. BLOCKED.

**`format("{0.__class__}", [])` — built-in `format()` function:**
The AST scanner does NOT catch this. The call node is `ast.Call(func=ast.Name('format'), ...)` — not an `ast.Attribute`, so `_scan_format_call` returns `None`. The `ast.Name` check catches names in `FORBIDDEN_BUILTINS`, but `format` is not in that set.

However: `format` is also not in `_ALLOWED_BUILTINS`. At runtime, the sandbox namespace has `__builtins__` set to only the allowed builtins dict, which does not include `format`. The call raises `NameError: name 'format' is not defined`. Confirmed via `_evaluate`. **Not exploitable in practice.**

The scan gap exists at the AST level but is defended at the runtime level. This is defense in depth working as intended, but the gap is worth documenting.

**`"{}".format(payload)` with malicious payload content:**
Payload content does not matter — `_FORMAT_ATTR_PATTERN` only inspects the template (the receiver literal), not the arguments. A template without `.attr` fields is safe regardless of argument values. Correct.

**`str.format("{0.__class__}", [])` — class-method call:**
`str.format` has `str` as the receiver Name node. `isinstance(ast.Name('str'), ast.Constant)` is `False`, so it falls into the non-literal receiver branch and is rejected as `format-on-variable-receiver`. BLOCKED. Confirmed.

**`f"{payload.__class__}"` — f-strings:**
f-strings produce `ast.JoinedStr` nodes containing `ast.FormattedValue`. If the formatted value contains an attribute access like `payload.__class__`, the attribute `__class__` is detected by the existing `ast.Attribute` block in `_scan_ast`. BLOCKED. Confirmed: `f"{x.__class__}"` returns `('__class__', 1, 21)`.

**`"%s" % []` — percent-format operator:**
`%` calls `__mod__` on the string, which invokes `__str__`/`__repr__` on arguments. It does NOT perform attribute field access like `{0.__class__}`. The result is the list's string representation. Not exploitable. Confirmed via `_evaluate`.

**`repr(obj)`, `str(obj)` — reflection via allowed builtins:**
`repr` and `str` are in `_ALLOWED_BUILTINS`. However, `repr([])` returns `'[]'` — the string representation of the list, not its class. Accessing `__class__` is blocked by `BLOCKED_ATTRIBUTES`. The string returned by `repr()` is opaque data, not a class introspection vector. Not exploitable.

**`map("{...}".format, [1,2,3])` — passing format as callable to map:**
When the receiver is a literal string without `.attr` fields, it is permitted. `"{1}".format` used as a callable to `map` is allowed. Verified: `_evaluate('result = list(map("{}".format, [1,2,3]))')` returns `['1', '2', '3']`. This is correct and intentional — no attribute access occurs.

**Legitimate use non-regression:**
The fix does not block `"{0}-{1}".format(a, b)` (literal receiver, no attribute fields). Confirmed: `_scan_ast` returns `None`. All seven tests in `TestStarlarkFormatVariableReceiverBlocked` pass.

**Multi-statement variable receiver (`template = "{0.__class__.__mro__}"; template.format([])`):**
Caught. `template` is an `ast.Name` node at the `.format()` call site. The assignment in a prior statement does not change the receiver type at AST time. BLOCKED. Confirmed.

**Subscript receiver (`templates[0].format([])`):**
`templates[0]` is `ast.Subscript`, not `ast.Constant`. Falls into the non-literal receiver branch. BLOCKED. Confirmed.

### Verdict: APPROVE WITH NOTES

The fix correctly closes the variable-receiver bypass. One note:

The built-in `format()` function (called as `format(template, arg)`) is not detected by `_scan_ast` because it is an `ast.Name` call, not an `ast.Attribute`. The gap is mitigated at runtime because `format` is not in `_ALLOWED_BUILTINS` and raises `NameError`. However, if `format` were ever added to `_ALLOWED_BUILTINS` in the future, the AST scan would not catch `format("{0.__class__}", x)` — creating a silent bypass. Recommend adding `format` to `FORBIDDEN_BUILTINS` for defense in depth.

---

## Regression Test Assessment

### `test_p1_path_traversal.py` — Coverage: ADEQUATE

Tests cover: single `..`, double `..`, intermediate-valid-dir traversal, absolute path injection, legitimate file serving, and content verification. The null-byte DoS case is not tested but is a DoS, not a bypass. Tests pass GREEN.

### `test_p2_dom_xss.py` — Coverage: INADEQUATE

Tests cover only the main-frame narration path via `emit_interactive_html`. The substory narration path (`emit_substory_html` line 296) is not tested. A test using substory frames would fail on the current code, exposing the bypass. Tests pass GREEN only because the bypass path is not exercised.

### `test_starlark_format_block.py` — Coverage: ADEQUATE

Tests cover variable receiver, two-step variable assignment, subscript receiver, and non-regression of safe literal-receiver calls. The `format()` built-in gap is not tested but is not exploitable. Tests pass GREEN.

**Full suite:** `uv run pytest tests/regression/audit_2026_04_19/ -v` → 59 passed in 0.18s.

---

## Defense-in-Depth Recommendations (for later phase, do NOT implement now)

### Fix #1 additions
1. Wrap the `resolve()` call in a `try/except (ValueError, OSError)` to handle null bytes and other OS-level path errors gracefully (return `/static/` fallback instead of crashing).
2. Add a `name` length cap to prevent extremely long path names from causing OS errors.

### Fix #2 additions
1. Apply `_sanitize_narration_html` in `emit_substory_html` at line 296 (this is the REJECT blocker — required before commit).
2. Add `bleach` to `[project.dependencies]` in `pyproject.toml` (this is the second REJECT blocker — required before commit).
3. Consider removing `<foreignObject>` from the narration-specific sanitizer whitelist (it is required for diagram SVG output but not for narration text).
4. Add a `protocols=['http', 'https', 'mailto']` explicit parameter to the `bleach.clean()` call in `_sanitize_narration_html` to make the protocol restriction explicit and not reliant on bleach's default.
5. Consider client-side DOMPurify as a second layer of defense for the `innerHTML` assignment, reducing reliance on a single server-side sanitizer.
6. Apply sanitization to the print-frame narration paths (lines 513, 523) if the library is ever used in a multi-tenant context where narration content is user-supplied rather than author-supplied.

### Fix #3 additions
1. Add `format` (the built-in function) to `FORBIDDEN_BUILTINS` to close the AST-scan gap, even though the runtime blocks it today. This ensures the gap cannot become exploitable if `_ALLOWED_BUILTINS` is ever extended.

---

## Final Recommendation

**DO NOT COMMIT Phase 1 in its current state.**

Fix #2 has two REJECT-level issues:

1. The substory narration path (`emit_substory_html` line 296) is not sanitized. This is a complete bypass of the XSS fix via the substory feature. The JS runtime at `scriba.js` line 54 assigns `fd[i].narration` to `innerHTML`, and that value is not run through `_sanitize_narration_html`.

2. `bleach` is declared as a dev-only dependency but is called unconditionally in production code. A production `pip install scriba-tex` without `[dev]` extras will fail at render time with `ModuleNotFoundError`.

Fixes #1 and #3 are approved with minor notes but do not block the commit. Once A2 resolves the two blockers in Fix #2 and adds a regression test covering the substory narration path, Phase 1 may proceed.
