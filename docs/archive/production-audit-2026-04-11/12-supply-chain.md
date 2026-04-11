# Agent 12: Path Traversal, Asset Resolution, Supply Chain

**Score:** 9/10
**Verdict:** production-ready

## Prior fixes verified
- 0.1.1 includegraphics validation: PRESENT

The CHANGELOG confirms that 0.1.1 introduced `is_safe_url` validation of resolver output: "apply_includegraphics validates resolver result through is_safe_url; unsafe URLs are treated as missing images."

## Critical Findings

**None.** No path traversal, supply chain, or asset resolution vulnerabilities detected.

## High Findings

1. **resource_resolver contract is secure** — ResourceResolver protocol receives raw filename strings and returns URL or None. The contract is enforced: (a) includegraphics HTML-escapes the filename before embedding in attributes; (b) the resolver output is re-validated through `is_safe_url()` before embedding in `src=` attributes. Test coverage includes `test_xss_image_resolver_returns_javascript_url()` verifying javascript: URLs are rejected.

2. **Filename sanitization is complete** — includegraphics (parser/images.py:79–113) applies defense-in-depth: (a) filename is HTML-escaped via `_html.escape(filename, quote=True)` before embedding in data attributes (line 90); (b) resolver URL is validated via `is_safe_url()` and re-escaped before embedding as `src=` (lines 92–102); (c) no path traversal vectors (`../`, NUL bytes, unicode line separators) can slip through because attributes use entity encoding.

3. **KaTeX vendored, pinned, and licensed** — KaTeX 0.16.11 (vendored Oct 8, 2026) is shipped inside the wheel at `scriba/tex/vendor/katex/katex.min.js` (269 KiB, SHA-256 verified). No known CVEs for 0.16.11 as of cutoff. Pinned version ensures reproducible builds. Loaded via Node worker at `katex_worker.js:26–34` using path-relative require (safe), with fallback to global install if vendored missing.

4. **Pygments 2.19.2 pinned, CSS generated at build time** — pyproject.toml locks `pygments>=2.17,<2.20` and uv.lock pins 2.19.2. CSS files (scriba-tex-pygments-light.css, scriba-tex-pygments-dark.css) are pre-generated at build time (116 lines each) and shipped in the wheel. No runtime Pygments execution of untrusted input.

5. **No shell injection, no PATH poisoning** — All subprocess calls use list-based argv (no shell=True): (a) `_probe_runtime()` spawns node with `[node, "-e", f"require({repr(...)})"]` (line 106); (b) katex_worker spawned with `[node_executable, path]` (line 183); (c) NODE_PATH set defensively only if unset in parent env (line 173), preventing overwrite of operator intent.

## Medium Findings

1. **importlib.resources usage is safe** — Files imported via `files("scriba.tex").joinpath(...)` and converted to `Path(str(...))` do not join user input; all joinpath arguments are hardcoded asset names (vendor/katex/katex.min.js, katex_worker.js, static/). No path traversal via user-controlled keys.

2. **Subprocess worker does not read user filenames** — Worker communication is JSON-based (json.dumps/json.loads on line 242–299 of workers.py); no shell metacharacters or path strings pass through. KaTeX input is LaTeX math expressions, not filenames.

3. **Bleach 6.3.0 pinned for dev/tests** — Optional dev dependency (uv.lock), not shipped in production wheel. Tests use `test_xss_*` functions as primary XSS defense; bleach is a safety net, not a runtime requirement.

## Low Findings

1. **NODE_PATH set at process startup** — Line 176 writes `os.environ["NODE_PATH"]` once per TexRenderer init. Side effect is global but idempotent (only if unset). Could be isolated to worker Popen env in future if strictness desired.

2. **No symlinks out of tree** — KaTeX fonts reference relative paths (url(fonts/...)) in CSS; no absolute paths in wheel metadata. Glob confirms all vendor files are regular files, no symlinks.

## Notes

- XSS test suite (test_tex_xss.py) covers resolver injection, filename quote breakout, newline/tab smuggling, unicode line separators—comprehensive coverage.
- Subprocess worker protocol is JSON-line; no shell templating or command-line injection surface.
- Asset namespacing (renderer/basename) prevents collisions; all asset keys are fixed strings, never user-derived.
- CHANGELOG 0.1.1 documents the is_safe_url defense; behavior is locked.
