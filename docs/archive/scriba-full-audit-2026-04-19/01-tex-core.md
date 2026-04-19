# scriba/tex/ Core Audit — 2026-04-19

Auditor: Claude Sonnet 4.6 (python-reviewer agent)
Scope: `scriba/tex/` — parser/, renderer.py, validate.py, highlight.py
Files reviewed: 15 Python files, 2 175 lines total

---

## 1. Score: 7.5 / 10

Well-engineered pipeline with correct ordering, solid security posture, and good use of Python idioms throughout. Held back by two oversized functions, three untyped `dict` annotations, a bare `except Exception` that swallows unknown errors silently, a module-level global mutation (`os.environ`) in `__init__`, and a _VALIDATION_ONLY_ENVS / KNOWN_ENVIRONMENTS split that is fragile and under-documented.

---

## 2. Findings Table

| Severity | File:Line | Issue | Concrete Fix |
|----------|-----------|-------|--------------|
| HIGH | `renderer.py:255` | **Bare `except Exception` silently swallows all errors** during the vendored-KaTeX stat check. Any unexpected exception (PermissionError, MemoryError, etc.) is eaten with `_vendored_exists = False`, causing a misleading fallback to the slow `npm root -g` path and hiding bugs. | Replace with `except OSError` — the only realistic exception from `.exists()` on a `Path`. |
| HIGH | `renderer.py:260` | **Global process environment mutated inside `__init__`** (`os.environ["NODE_PATH"] = global_root`). Any code running in the same process after the first `TexRenderer` construction sees a polluted `NODE_PATH`. This is especially dangerous in web servers (gunicorn/uvicorn workers) where multiple renderers may race, and in test suites where env state leaks between cases. | Pass the env dict explicitly to `SubprocessWorker` rather than mutating the process env. Store `_extra_env: dict[str, str]` on `self` and thread it through the worker's `env=` argument. |
| HIGH | `renderer.py:203–272` | **`__init__` is 70 lines** (exceeds 50-line function budget). It performs side-effectful I/O (stat, subprocess probe, worker registration) inside the constructor, making it impossible to construct a `TexRenderer` in tests without node being present. | Extract `_resolve_worker_path()`, `_maybe_set_node_path()`, `_create_worker()` as private helpers. Constructor becomes 25 lines of assignment + calls. |
| HIGH | `renderer.py:510–639` | **`_render_source` is 130 lines** (far exceeds the 50-line budget). The pipeline steps 0–10 are each labelled but live in one monolithic function. | Extract each logical phase into `_phase_extract_blocks()`, `_phase_escape()`, `_phase_inline_transforms()`, `_phase_block_transforms()`, `_phase_render_math()`, `_phase_wrap_paragraphs()`. `_render_source` becomes a 20-line orchestrator. |
| HIGH | `renderer.py:455`, `renderer.py:484`, `parser/math.py:120` | **Untyped `request: dict` annotation** — bare `dict` instead of `dict[str, object]` or a TypedDict. Loses type safety on the KaTeX JSON protocol; a wrong key silently sends `None` to the worker. | Define a `KatexSingleRequest` and `KatexBatchRequest` TypedDict in `parser/math.py` and use them in both `_render_inline`/`_render_display` (renderer.py) and `render_math_batch` (math.py). |
| HIGH | `parser/tables.py:128` | **`rows: list[dict]` is untyped** — the dict schema (`raw`, `top_hline`, `top_clines`, `bottom_hline`, `bottom_clines`) is only discoverable by reading code. Mutation of `rows[-1]` at line 153/155 is hidden from type checkers. | Replace with `@dataclass class _TableRow` (or a `TypedDict`). Mutation becomes explicit attribute assignment; mypy can catch key-name typos. |
| HIGH | `parser/math.py:32–52` | **`_preprocess_text_command_chars` recompiles its regex on every call**. The `pattern = re.compile(...)` at line 39 is inside the function body, so every invocation of `_make_item` pays the compile cost. With up to 500 math items per document this is called 500 times. | Hoist `_TEXT_CMD_RE = re.compile(...)` to module level, matching the style of every other module in the package. |
| MED | `renderer.py:346–350` | **`__exit__` missing type annotations** on `exc_type`, `exc`, `tb`. Signature is `def __exit__(self, exc_type, exc, tb) -> None` — three unannotated parameters. | Change to `def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> None`. |
| MED | `validate.py:81–85` | **Unknown-environment warning skips nesting validation**. When `env_name not in KNOWN_ENVIRONMENTS` the code emits a warning and `continue`s — so a mistyped `\begin{tabulr}` is warned about but its `\end{tabulr}` is never pushed/popped from `env_stack`, leaving nesting tracking in a correct state by accident. However, if the typo is consistent (begin+end both wrong), no stack imbalance is detected. The intent is ambiguous. | Either push/pop unknown environments onto a separate `unknown_stack` to detect their own nesting imbalance, or document explicitly that unknown environments are ignored for nesting purposes. |
| MED | `validate.py:14` and `environments.py:77` | **`KNOWN_ENVIRONMENTS` / `_VALIDATION_ONLY_ENVS` split is fragile**. `KNOWN_ENVIRONMENTS` (validate.py:14) lists 20 environments. `_VALIDATION_ONLY_ENVS` (environments.py:77) is a subset of 7. Adding a new validation-only environment requires updating both sets in two different files with no compile-time guard ensuring consistency. | Move `_VALIDATION_ONLY_ENVS` next to `KNOWN_ENVIRONMENTS` in `validate.py` (or a shared `_tex_constants.py`), and add an assertion: `assert _VALIDATION_ONLY_ENVS <= KNOWN_ENVIRONMENTS`. |
| MED | `highlight.py:77–82` | **Double docstring on `highlight_code`**. Lines 80–91 contain a second docstring that supersedes the one-liner at line 81. The first string is the one that shows up in `help()`. | Remove the one-liner at line 81; the full docstring at 82–91 is the correct one. |
| MED | `renderer.py:224–226` | **Redundant double-copy of `katex_macros`**. `self._katex_macros = dict(katex_macros)` then `self._katex_macros_request_dict = dict(self._katex_macros)`. Two copies of the same dict are held for the stated reason "avoid copying on every call" (Opt-5 comment), but `self._katex_macros` is never mutated after init and is only used as the source for `self._katex_macros_request_dict`. | Remove `self._katex_macros`. Keep only `self._katex_macros_request_dict` (built directly from the constructor argument) plus a `self._katex_macros_original: Mapping[str, str] | None` if raw access is needed elsewhere. |
| MED | `parser/text_commands.py:16–19` | **Private symbols re-exported from a public-ish module**. `_BRACE_COMMANDS` and `_replace_balanced` (prefixed `_` = internal) are re-exported from `scriba.tex.parser.text_commands` via an explicit import with `# noqa: F401`. This exposes internal helpers at a module boundary. | Export only `apply_text_commands` (the public function). Keep `_BRACE_COMMANDS` and `_replace_balanced` import-only within the module; don't list them in the `from … import (…)` block. |
| MED | `parser/environments.py:162–189` | **`apply_urls` applies `\href` before `\url`** (line 187 then 188). If a `\href` argument contains a `\url{}` substring the `\href` regex runs first and may consume text that was intended as a nested `\url`. The order is unlikely to cause problems in practice but it is the reverse of what most TeX authors would expect and is not documented. | Add a comment explaining why `\href` is matched before `\url`, or swap to `\url` first (simpler patterns first). |
| LOW | `parser/dashes_quotes.py:23` | **Smart-quote regex allows `'` inside the match group** (`(?:[^']|'(?!'))*?`). The negative lookahead `'(?!')` means a single apostrophe not followed by another apostrophe is allowed inside a double-quoted span. This is correct LaTeX, but it means `\`\`it's a test''` will match with the apostrophe inside the quoted content. The regex is more complex than necessary; a simpler `[^']*` would handle 99% of real content. | Document the intent or simplify; the current pattern is not wrong but its complexity is unexplained. |
| LOW | `parser/escape.py:42` | **`import re` inside function body** (`parse_command_args`). Every call to `parse_command_args` incurs a module-lookup (cheap, but inconsistent with every other file in the package). | Move `import re` to the top of `escape.py`. |
| LOW | `parser/lists.py:59` | **`re.split(r"\\item\s*", content)` at line 59 will produce a leading empty string** when content starts with `\item`. The `if item.strip()` filter at line 60 silently drops it, which is correct behaviour, but the intent is not obvious. | Replace with `re.split(r"\\item\b\s*", content)[1:]` to make the skip of the preamble explicit. |
| LOW | `parser/math.py:19` | **`_DOLLAR_LITERAL` sentinel is a module-level constant but is not documented as package-internal**. It leaks into the module's namespace and could clash if this module is ever monkey-patched in tests. | Prefix as `__DOLLAR_LITERAL` (name-mangled) or keep as-is and add a `# internal` comment; minor. |
| LOW | `renderer.py:391` | **`_CELL_DOLLAR` sentinel is defined inside `_render_cell` on every call** rather than at class or module level. There is no correctness issue (it is a string constant), but it is inconsistent with how all other sentinels in the package are defined. | Hoist to `_CELL_DOLLAR: str = "\x00SCRIBA_CELL_DOLLAR\x00"` at module level alongside `_KATEX_ERROR_RE` etc. |

---

## 3. Strengths — Keep These

**Pipeline ordering is correct and well-commented.** The `_render_source` step sequence (lstlisting/tabular extraction → includegraphics → strip_validation_environments → extract_math → html.escape → restore_dollar_literals → unescape TeX specials → text/size commands → urls → block environments → typography → math rendering → restore inline → paragraph wrap) is the right order and every step is labelled with a numbered comment. The ordering avoids double-escaping, protects code bodies from math extraction, and defers math rendering until after all cheap transforms.

**`PlaceholderManager` is clean and correct.** The NUL-sentinel approach, the block/inline split, and the `frozenset` return from `block_tokens` are all correct choices. Storing `(token, html)` tuples in insertion order and restoring in that order is safe even when one placeholder's HTML contains another's token.

**`_MathItem` is a frozen dataclass.** Immutable by construction, hashable, correct use of the pattern for a value-object that crosses a module boundary.

**`KNOWN_ENVIRONMENTS` and `_VALIDATION_ONLY_ENVS` use `frozenset`.** Correct immutability for set constants.

**URL safety check (`_urls.py`) is thorough.** Control-character strip before `urlparse`, allowlist of schemes, bidi/zero-width character rejection — this is production-quality XSS defence.

**`_LANG_HEURISTICS` tuple-of-tuples is immutable.** Precompiled `re.Pattern` objects stored at module level; no per-call compilation (aside from the `math.py` issue noted above).

**`slugify` non-Latin fallback is correct.** SHA-1 of the original text as a stable `section-<hash>` slug for CJK/Arabic headings is the right approach. Using `hashlib.sha1` for a non-security purpose (stable ID generation) is acceptable here.

**`_render_inline` / `_render_display` duplication is intentional and minor.** The two functions share ~20 lines of structural similarity but differ in `displayMode` and the wrapper tag. Merging them would add a parameter and reduce clarity. The duplication is acceptable.

**`is_safe_url` returns `False` for empty string.** Explicit guard at line 28; callers do not need to pre-check for empty input.

**`apply_tabular` cell-renderer is `None`-safe.** `_render_cell_content` falls back to plain HTML escape when no renderer is provided, making the module usable in isolation.

---

## 4. Top 3 Priorities to Fix First

### Priority 1 — `os.environ` mutation in `__init__` (renderer.py:260)

This is the most dangerous issue in the module. Mutating the process-level environment inside a constructor is a global side effect that cannot be rolled back, races with concurrent `TexRenderer` constructions in async contexts, and will cause confusing failures in multi-renderer test suites. The fix is straightforward: store the extra env var as `self._extra_node_env: dict[str, str]` and pass it as `env={**os.environ, **self._extra_node_env}` to `SubprocessWorker`. Zero user-visible behaviour change; eliminates a class of hard-to-reproduce bugs.

### Priority 2 — `_render_source` and `__init__` size (renderer.py:203 and 510)

At 70 and 130 lines respectively these are the two functions most likely to harbour latent bugs, hardest to unit-test in isolation, and most resistant to future modification. Extracting `__init__`'s I/O side-effects into helpers also unblocks dependency injection in tests (pass a pre-built worker, skip the probe). Extracting `_render_source` phases makes each phase independently testable. This is the single highest-leverage refactor for long-term maintainability.

### Priority 3 — `request: dict` / `rows: list[dict]` untyped annotations (renderer.py:455,484 + math.py:120 + tables.py:128)

These three untyped `dict` annotations are the largest type-safety gap in the codebase. The KaTeX wire protocol is clearly defined but invisible to mypy; a wrong key or missing field will only surface at runtime when a worker receives a malformed request. Defining `KatexSingleRequest`, `KatexBatchRequest` TypedDicts and a `_TableRow` dataclass closes the loop. This also forces the KaTeX protocol shape to be documented in code rather than just in comments, making future protocol changes safer.
