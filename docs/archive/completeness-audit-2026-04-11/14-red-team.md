# 14 — Cross-Cutting Red-Team Completeness Audit

**Agent**: 14 / 14 (last)
**Scriba**: v0.5.1, HEAD `eb4f017`
**Date**: 2026-04-11
**Scope tag**: adversarial / cross-cutting

## Scope

This is the *last* completeness agent. Prior audits covered grammar fuzzing,
Starlark sandbox escape, XSS injection, supply-chain, parser corner cases,
error catalog coverage, recursion DoS, and the 13 peer completeness
threads (API consistency, emitter warnings, silent auto-fix, error hints,
authoring walkthroughs, widget QA, cookbook, onboarding). This agent does
**not** re-run those. Instead it explores seven adversarial categories
with real `.tex` inputs that are actually compiled against `render.py`:

1. Scale extremes (step counts, narrate size, shape counts, foreach bombs)
2. Unicode horror (RTL, ZWJ, combining marks, emoji, NFC vs NFD)
3. KaTeX rendering bombs (nested `\text`, `\def` macros, long equations,
   invalid LaTeX)
4. Selector injection (dot-in-names, negative/OOB indices, deep paths)
5. Filesystem-adjacent strings (absolute paths, `../`, `file://`,
   `javascript:` URIs in narrate)
6. Starlark corner cases not covered by prior sandbox audit (nested
   closures, long identifiers, non-string dict keys, n² comprehensions,
   recursion)
7. Emitter edges (empty animations, special frame labels, duplicate IDs,
   duplicate shape declarations, per-frame annotation cap)

## Methodology

For each category one or more minimal `.tex` fixtures were written to
`/tmp/completeness_audit/14-redteam-<slug>.tex` and compiled with:

```
uv run python render.py <fixture> -o <out>.html
```

Outcomes were classified as:

| Class | Meaning |
|-------|---------|
| clean-accept | Compiled without error, output inspected, looks correct |
| clean-reject | Rejected with a specific `E`-code and readable message |
| silent-accept | Compiled without error but the behavior is surprising or the input should have been flagged |
| dirty-fail | Uncaught traceback / crash |
| hang | Wall-clock / memory spike |

Scriba core was **not** modified. Only `/tmp/completeness_audit/` fixtures
were created. All tests ran against the stock `uv run python render.py`
pipeline.

## Adversarial results per category

### 1. Scale extremes

| ID | Input | Result | Class |
|----|-------|--------|-------|
| 1a | 1000 `\step` blocks | `E1181 "animation has 1000 frames, exceeding the 100-frame limit"` | clean-reject |
| 1b | Single `\narrate{}` with ~100 KB of text | Compiled; 220 KB HTML output | **silent-accept** |
| 1c | 50 `\shape` declarations in one animation | Compiled | clean-accept |
| 1d | `\foreach` + `\step` inside body | `E1172 "\step is not allowed inside \foreach body"` | clean-reject |
| 1e | `\foreach{i}{0..9999}` (exactly at cap) | Compiled, 9 KB HTML | clean-accept |
| 1f | `\foreach{i}{0..10001}` (over cap) | `E1173 "iterable length 10002 exceeds maximum 10000"` | clean-reject |

**Finding 1b**: There is no upper bound on the text length of a single
`\narrate{}` block. The only guard is the 1 MB source-file limit (`E1013`).
A single-step animation can legally embed ~1 MB of narrate text, which
then survives through emit and lands in the HTML. Not a security bug but
an unbounded growth vector.

### 2. Unicode horror

| ID | Input | Result | Class |
|----|-------|--------|-------|
| 2a | RTL (`عربي`), Hebrew (`עברית`), emoji with ZWJ (`👩‍🔬`), variation selector (`⚠️\ufe0f`) in labels and narrate | Compiled | clean-accept |
| 2b | Shape id with NFD `café` (`e` + U+0301 combining acute) | `E1009 "Selector parse error ... unexpected trailing text"` at the `\recolor` site (**not** at the `\shape` site) | **silent-accept → dirty-reject** |
| 2c | Shape id with NFC `café` (precomposed `é`) | Compiled | clean-accept |
| 8a | Emoji inside `\shape` label, `\annotate` text | Compiled | clean-accept |

**Finding 2b (MEDIUM, real)**: Two textually "identical" shape identifiers
produce opposite outcomes depending on Unicode normalization form.
`\shape{café_x}{...}` under NFC compiles; under NFD the *same* glyph
sequence parses into `\shape{` then is later rejected by the selector
lexer at `\recolor{café_x...}` because `selectors.py` walks
character-by-character with `str.isalpha()` / `str.isalnum()`, which
accept precomposed letters but not combining marks. Scriba never runs
`unicodedata.normalize()` on identifiers. Authors who paste IDs from
macOS filesystems (NFD) or from mixed-source clipboards will hit
confusing `E1009` errors at use-sites, not at declaration sites.

### 3. KaTeX rendering bombs

| ID | Input | Result | Class |
|----|-------|--------|-------|
| 3a | `$\text{\text{...}}$` 40 levels deep | Compiled; HTML ~9 KB | clean-accept |
| 3b | `$\def\foo{999}\foo + \foo$` | Compiled; KaTeX evaluated the macro (`999` appears in output) | **silent-accept** |
| 3c | 5 KB equation (`x_0^0 + x_1^1 + … + x_399^399`) | Compiled | clean-accept |
| 3d | Unbalanced braces `$\frac{1}{$` | `E1001 "unbalanced braces"` (caught by lexer, not KaTeX) | clean-reject |
| 3e | Recursive macro `\def\x{\x\x}\x` | **Compiled with exit code 0**; HTML contains `<span class="katex-error" title="ParseError: Too many expansions…">` | **silent-accept** |
| 3f | Mutual recursion `\def\a{\b}\def\b{\a}\a` | Same as 3e — ParseError inlined in HTML, CLI silent | **silent-accept** |

**Finding 3b (LOW)**: KaTeX's `\def` is enabled by default in this
scriba build (it uses the vendored KaTeX without `strict: true` or
`maxExpand` reduction). `\def` has historically been a source of TeX
sandbox bypasses and expansion bombs. Today KaTeX's `maxExpand` guard
(finding 3e) neutralises the worst case, but the feature is still on.

**Finding 3e/3f (MEDIUM, real)**: KaTeX *does* catch macro expansion
bombs and serialises them as an inline `<span class="katex-error">`
token. However scriba's CLI reports "Rendered 1 block(s)" and exits 0.
There is no aggregated KaTeX-error surfacing: an author with five
broken math snippets in a lecture will only discover them by viewing
each block in a browser. This is the *same* silent-accept class flagged
by agent 03 (emitter-warnings) for selector misses, but in the math path
instead of the selector path.

### 4. Selector injection

| ID | Input | Result | Class |
|----|-------|--------|-------|
| 4a | `\shape{a.b}` then `\recolor{a.b.cell[0]}` | Shape compiles with dot-name; recolor fails `E1009 unexpected trailing text '.cell[0]'` | **silent-accept at shape → dirty-reject at selector** |
| 4b | `\recolor{a.cell[-1]}` | `E1010 "expected non-negative index, got -1"` | clean-reject |
| 4c | `\recolor{a.cell[999]}` (OOB on size-3 array) | Compiled. Two `UserWarning`s emitted (`selector … does not match any addressable part`, `invalid selector cell[999], ignoring set_state()`). Exit 0. | **silent-accept (warn-only)** |
| 4d | 10-level deep path `a.child.child…[0]` | `E1009` | clean-reject |
| 8b | 501 `\annotate` in one frame | `E1103 "annotation count 501 exceeds maximum of 500 per frame"` | clean-reject |

**Finding 4a (MEDIUM)**: `\shape` accepts arbitrary characters in the
identifier slot (including `.`, `[`, and `]`) because `_read_brace_arg`
reads raw to the matching `}`. The selector parser then assumes IDs do
*not* contain dots, so dot-bearing shape names are defined but
unaddressable. Two fixes are reasonable:

1. Validate shape identifiers at `\shape` time: `re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)` — fail fast with a new `E11xx` code.
2. Mirror the validation at selector parse time with a specific message.

Both help, (1) is preferable because it fails at declaration.

**Finding 4c (MEDIUM, overlaps agent 03)**: Out-of-bounds index on an
indexed primitive (`cell[999]` on size-3 array) is warn-only. The
animation renders but the step is a no-op. Prior agent 03 likely covers
this in the emitter-warnings thread — noting it again for cross-check.

### 5. Filesystem-adjacent strings

| ID | Input | Result | Class |
|----|-------|--------|-------|
| 5a | `\shape{a}{Array}{size=3, label="/etc/passwd"}` | Compiled | clean-accept |
| 5b | `id="../../../etc/passwd"` | Compiled; id embedded verbatim in HTML | **silent-accept (mild)** |
| 5c | `\narrate{file:///etc/passwd javascript:alert(1)}` | Compiled; text double-escaped as `&amp;lt;…&amp;gt;` | clean-accept (escaped, no XSS) |
| 7g | `\narrate{<script>… <img onerror=…>}` | Compiled; HTML-escaped twice (`&amp;lt;script&amp;gt;`) | clean-accept (safe) |

**Finding 5b (LOW)**: `id=` attribute on `\begin{animation}` accepts
path-traversal-looking strings. Scriba does not use the id as a
filesystem path anywhere (verified in `scriba/animation/renderer.py`
and `emitter.py`), so `../` has no live attack surface — it just lands
in an HTML `id` attribute. Still, normalising the id to a DOM-safe slug
(`[A-Za-z0-9_-]+`) would prevent downstream tooling surprises (e.g.
static-site pipelines that do `open(f"public/{anim.id}.html")`).

**Finding 5c**: dangerous URIs in narrate text are rendered as
*plain text*, not as `<a>` links. Since scriba does not linkify, there
is no live `javascript:` or `file://` vector — the string is double-HTML-
escaped (`\``&amp;lt;…\``) inside the JS bootstrap template literal. Safe.

### 6. Starlark corner cases

| ID | Input | Result | Class |
|----|-------|--------|-------|
| 6a | `def make_adder(x):\n  def adder(y):\n    return x+y` — nested closure | Compiled | clean-accept |
| 6b | 10 KB identifier (`x * 10240`) as variable name | Compiled | **silent-accept** |
| 6c | Dict with int, tuple, and float keys | Compiled | clean-accept |
| 6d | Recursive `fib(15)` | Compiled | clean-accept |
| 6e | `list(range(50000))` then `\foreach` over binding | `E1173 "length 50000 exceeds maximum 10000"` | clean-reject |
| 6f | `"x" * 1_000_000` (1 MB string) | Compiled | **silent-accept** |
| 6g | 1000×1000 list comprehension (`[[i*j for j in range(1000)] for i in range(1000)]`) | Compiled in ~3.1 s | **silent-accept, near DoS** |

**Finding 6g (HIGH)**: The Starlark compute worker's wall-clock budget
is 3 s (`_WALL_CLOCK_SECONDS = 3`) and the tracemalloc peak cap is 64 MB.
A 1 M-cell list comprehension creates ~28 MB of live objects and
completes in ~3 s — right at both ceilings. An adversarial `.tex` that
runs several *sequential* compute blocks, each at 90 % of the budget,
would multiply wall time linearly (each block forks a worker and resets
its own 3-s alarm). The subprocess isolation prevents process-memory
growth, but CPU / latency scale with compute-block count. Recommended
hardening: (a) add a *per-file* cumulative compute-time budget on the
host side and (b) lower the default `_WALL_CLOCK_SECONDS` from 3 s to
1 s — the cookbook examples all run in <50 ms, so 1 s still gives 20×
headroom for legitimate cases.

**Finding 6b (LOW)**: There is no bound on Starlark identifier length.
A 10 KB variable name is accepted, living inside the namespace dict
until the worker returns. Not exploitable — the 64 MB tracemalloc cap
is a hard ceiling — but it is an example of an input dimension with
no declared limit. Specify a `MAX_IDENT_LEN = 256` in the AST
pre-walk alongside the existing integer-literal cap at line 217.

**Finding 6f**: 1 MB string multiplication survives because
`_TRACEMALLOC_PEAK_LIMIT = 64 MB` is far above the produced allocation.
This is consistent with the documented `SS6` budget and is not a bug,
but combined with an unbounded number of compute blocks it is worth
reviewing the *cumulative* memory budget.

### 7. Emitter corner cases

| ID | Input | Result | Class |
|----|-------|--------|-------|
| 7a | Animation with `\shape` + `\step` + `\narrate` only, no recolors | Compiled | clean-accept |
| 7b | Animation with only `\shape`, zero `\step` | Compiled | clean-accept |
| 7c | Frame label with embedded quotes and `<tag>` | Compiled; escaped correctly | clean-accept |
| 7d | Two animations both `id="dup"` in one file | **Both blocks rendered, both HTML nodes carry `id="dup"`** | **silent-accept (HIGH)** |
| 7e | `\substory{L1}` (brace form, which is not the documented syntax) | `E1368` trailing text | clean-reject |
| 7f | Same shape id `a` declared twice in one animation | Compiled; second declaration silently overrides first | **silent-accept (HIGH)** |
| 7g | HTML / `<script>` / `onerror` in narrate | Compiled; double-escaped | clean-accept (safe) |

**Finding 7d (HIGH, real)**: Duplicate animation `id` attributes within
a single source file are accepted without any warning. Two widgets with
`id="dup"` are emitted; both produce `<div class="scriba-widget" id="dup">`
in the HTML. In the browser, `document.getElementById("dup")` is
deterministic (returns the first), so the second widget's bootstrap
JavaScript will attach to the first widget's DOM node and both will
misbehave. This should be a clean `E10xx` at render-time.

**Finding 7f (HIGH, real)**: Two `\shape{a}{…}` declarations in a row.
The second silently overrides the first. No `E1xxx` raised, no warning
emitted. Authors who accidentally paste a shape twice (classic rename
pattern) get the wrong primitive with no indication. Recommended fix:
track shape ids in a set inside the scene builder and raise a new code
(e.g. `E1018 "duplicate shape id {name}"`) on collision.

## Crashes / hangs / silent-accepts summary

**Crashes (dirty-fail, uncaught)**: none.

**Hangs**: none. 6g ran at the edge of the 3-s wall clock but
terminated cleanly.

**Silent-accepts of real concern**:

1. **7d** — duplicate animation `id` → broken JS bootstrap (HIGH)
2. **7f** — duplicate `\shape` id → wrong primitive shape (HIGH)
3. **6g** — 1 M-cell comprehension near DoS threshold (HIGH)
4. **3e/3f** — KaTeX macro bombs swallowed at CLI level (MEDIUM)
5. **2b** — NFC vs NFD asymmetry for identifiers (MEDIUM)
6. **4a** — `.`/`[`/`]` tolerated in `\shape` id → unreachable selector (MEDIUM)
7. **4c** — OOB cell index warn-only (MEDIUM, overlaps agent 03)
8. **1b** — unbounded `\narrate` text (LOW)
9. **5b** — `../` tolerated in animation id (LOW)
10. **6b** — unbounded Starlark identifier length (LOW)
11. **3b** — KaTeX `\def` enabled (LOW — bombs are caught by maxExpand)

## Severity summary

| Severity | Count | Items |
|----------|-------|-------|
| CRITICAL | 0 | — |
| HIGH | 3 | 6g, 7d, 7f |
| MEDIUM | 4 | 2b, 3e/3f, 4a, 4c |
| LOW | 4 | 1b, 3b, 5b, 6b |

No CRITICAL: scriba held up under this red-team pass. No crash, no hang,
no XSS bypass (narrate double-escapes), no sandbox escape. The failures
are all of the form *"input was accepted when it should have been
flagged"*, which is the expected signature of a completeness audit
rather than a correctness audit.

## Proposed hardening

### P0 (HIGH — before next release)

1. **Duplicate animation id**: in
   `scriba/animation/renderer.py::render_block` (or the pipeline that
   walks multiple blocks), maintain a `seen_ids: set[str]` and raise a
   new `E1019 "duplicate animation id '{id}'"` on collision.
2. **Duplicate shape id**: in `scriba/animation/scene.py` where
   `ShapeCommand` is accumulated, track ids in a set and raise a new
   `E1018 "duplicate shape id '{id}'"`.
3. **Starlark wall-clock**: drop `_WALL_CLOCK_SECONDS` from 3 to 1 in
   `scriba/animation/starlark_worker.py:402` and verify cookbook still
   passes. Adds a *per-file* cumulative compute-time budget of ~5 s in
   `starlark_host.py` as defence-in-depth against N sequential blocks.

### P1 (MEDIUM)

4. **Unicode normalization for identifiers**: in
   `scriba/animation/parser/grammar.py::_parse_shape` and in the
   selector parser, normalize to NFC before comparing/storing. Add a
   shared `_normalize_id()` helper.
5. **KaTeX error aggregation**: in the narrate-rendering callback in
   `render.py::_make_inline_tex_callback`, capture any `katex-error`
   span in the rendered HTML and emit a warning (or a dedicated
   `E15xx`) back to the CLI summary. The parse errors are already
   produced by KaTeX — they just aren't being surfaced.
6. **Shape identifier validation**: restrict `\shape{name}` to
   `r"[A-Za-z_][A-Za-z0-9_]{0,63}"` at declaration time and raise
   `E1017` on violation. Eliminates finding 4a at its source.
7. **OOB indexed selector**: promote the current `UserWarning` to a
   validation error, or at minimum escalate exit code when warnings
   occur and `--strict` is set. (Overlaps agent 03's thread — coordinate
   fix scope.)

### P2 (LOW)

8. **Narrate length cap**: add `MAX_NARRATE_BYTES = 16 KiB` in
   `scriba/animation/constants.py` and enforce in the parser. Legitimate
   narration is ≤ 500 chars in practice; 16 KB gives 30× headroom.
9. **Animation-id sanitisation**: run the animation `id` through a
   DOM-safe slug check (same regex as for shape ids above), reject
   `../`, `/`, and spaces. Prevents downstream pipelines from receiving
   path-looking ids.
10. **Starlark identifier length cap**: add a `len(name) <= 256` check
    in the AST pre-walker in `starlark_worker.py` alongside the existing
    integer-literal cap.
11. **KaTeX `\def`**: consider setting `strict: "error"` or disabling
    macros in `katex_worker.js` — subjective call; the `maxExpand`
    safeguard already handles the bomb class.

### Prior-art note

Findings 3e/3f (silent KaTeX errors) and 4c (OOB warn-only) have
conceptual overlap with the *emitter-warnings* thread (agent 03); any
aggregation layer added for those cases should cover math errors too.
Finding 7d has conceptual overlap with the *API-consistency* thread
(agent 01) because scriba's public promise of stable animation ids is
currently not checked. A single small module
`scriba/animation/uniqueness.py` could centralise all the "this thing
must be unique" checks (ids, shape names, frame labels) and feed into
the existing `errors.py` catalog with contiguous codes (e.g.
`E1016`–`E1019`).

## Appendix: fixture files

All fixtures live under `/tmp/completeness_audit/`:

```
14-redteam-1a-1000steps.tex        1b-bignarrate.tex         1c-50shapes.tex
14-redteam-1d-foreach500.tex       1e-foreach10k.tex         1f-foreach10k1.tex
14-redteam-2a-unicode.tex          2b-nfd.tex                2c-nfc.tex
14-redteam-3a-katexnest.tex        3b-katexdef.tex           3c-katexbig.tex
14-redteam-3d-katexbad.tex         3e-defbomb.tex            3f-defmutual.tex
14-redteam-4a-dotname.tex          4b-negidx.tex             4c-oob.tex
14-redteam-4d-deep.tex
14-redteam-5a-absfs.tex            5b-trav.tex               5c-fileurl.tex
14-redteam-6a-closure.tex          6b-longname.tex           6c-dictkeys.tex
14-redteam-6d-recurse.tex          6e-biglist.tex            6f-strmul.tex
14-redteam-6g-n2.tex
14-redteam-7a-onlynarrate.tex      7b-empty.tex              7c-speclabel.tex
14-redteam-7d-dupid.tex            7e-subdeep.tex            7f-shapedup.tex
14-redteam-7g-narratehtml.tex      8a-emoji.tex              8b-maxann.tex
```

Each fixture plus its `.html` output and stderr log are preserved in
`/tmp/completeness_audit/` for later reproduction. None of the fixtures
required any scriba source modification to run.
