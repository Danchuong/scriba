# §10, §11, §13, §14 Options/Colors/Gotchas/Limits Audit

Audit date: 2026-04-19
Doc range: lines 772–928 of `docs/SCRIBA-TEX-REFERENCE.md`

---

## §10 Env Options

Doc table (lines 774–780) lists five options. Code ground truth:
- `VALID_OPTION_KEYS` — `scriba/animation/constants.py:46`
- `AnimationOptions` dataclass — `scriba/animation/parser/ast.py:291-298`
- Parser: `scriba/animation/parser/grammar.py:521-527`

| Option | Doc default | Doc applies-to | Code default | Code applies-to | Status |
|--------|-------------|----------------|--------------|-----------------|--------|
| `id` | auto | both | `None` (auto-generated) | animation; diagram reuses same parser | OK |
| `label` | none | both | `None` | animation; diagram reuses same parser | OK |
| `width` | auto | both | `None` | animation; diagram reuses same parser | OK |
| `height` | auto | both | `None` | animation; diagram reuses same parser | OK |
| `layout` | filmstrip | animation only | `"filmstrip"` | animation only | OK |
| `grid` | — | — | accepted, silently dropped | animation | **UNDOCUMENTED** |

### `grid` option — undocumented accepted key

`"grid"` is present in `VALID_OPTION_KEYS` (`constants.py:46`) and therefore accepted without error by the parser (`grammar.py:503`), but it is **never passed into `AnimationOptions`** (`ast.py:291-298`; `grammar.py:521-527`) and has no effect. It is not documented in §10.

This is neither a user-visible bug (it silently no-ops) nor a documentation gap that causes broken output, but it is confusing: authors who write `\begin{animation}[grid=true]` receive no warning and no effect.

---

## §11 Annotation Colors

Doc table (lines 786–793) lists six tokens with descriptions only (no hex values). Code ground truth:
- `VALID_ANNOTATION_COLORS` — `scriba/animation/constants.py:36`
- CSS custom properties — `scriba/animation/static/scriba-scene-primitives.css:160-165`

| Token | Doc | Code (`VALID_ANNOTATION_COLORS`) | CSS variable | Status |
|-------|-----|----------------------------------|--------------|--------|
| `info` | neutral information (default) | present | `--scriba-annotation-info: #0b68cb` | OK |
| `warn` | warning/caution | present | `--scriba-annotation-warn: #92600a` | OK |
| `good` | positive/optimal | present | `--scriba-annotation-good: #2a7e3b` | OK |
| `error` | error/wrong | present | `--scriba-annotation-error: #c6282d` | OK |
| `muted` | de-emphasized | present | `--scriba-annotation-muted: var(--scriba-fg-muted)` | OK |
| `path` | solution path | present | `--scriba-annotation-path: #0b68cb` | OK |

All six documented tokens exist in code and CSS. No documented tokens are missing. No undocumented tokens exist in `VALID_ANNOTATION_COLORS`.

Note: `info` and `path` share the same light-mode hex (`#0b68cb`). This is intentional by the tonal architecture but is not mentioned in the doc. Low-priority observation only.

---

## §13 Gotchas & Known Limitations

### Gotcha 13.1 (line 848) — Stack/Queue: recolor in NEXT step

**Status: STILL TRUE**

The gotcha is structural: `\apply{s}{push="C"}` mutates primitive state when `apply_command` is called during SVG emit (`_emit_frame_svg` → `apply_command`), which happens after selectors are validated for the same frame. The new item's selector (`s.item[2]`) is unknown at `\recolor` resolution time within the same step.

No code path has been added to make newly pushed items addressable within the same step. The warning `E1115` ("Selector does not match any addressable part") is still the runtime signal — `scriba/animation/primitives/base.py:251-256`.

Same applies to Queue `enqueue` by the same mechanism.

### Gotcha 13.2 (line 868) — `${interpolation}` reliable only inside `\foreach`

**Status: STILL TRUE**

`InterpolationRef` objects from `\compute` bindings are only substituted during `\foreach` expansion in `_substitute_body` (`scriba/animation/scene.py:462-515`). Outside `\foreach`, a `RecolorCommand` or `AnnotateCommand` whose target contains an unresolved `InterpolationRef` will produce a mangled selector string (e.g. `a.cell[InterpolationRef(name='target')]`) when `_selector_to_str` renders the `CellAccessor.indices` (`scriba/animation/scene.py:75-77`). The primitive's `validate_selector` then rejects it silently via `E1115`.

The gotcha example (`\compute{ target = 4 }` + `\recolor{a.cell[${target}]}{state=good}` outside `\foreach` labelled "UNRELIABLE") is accurate.

### Gotcha 13.3 (line 887) — No `\documentclass` or `\begin{document}`

**Status: STILL TRUE**

The TeX renderer processes source as body content directly. `\documentclass` and `\begin{document}` are not in the supported command set and produce parse errors. No change in code.

### Gotcha 13.4 (line 891) — Math delimiters

**Status: STILL TRUE**

Only `$...$` (inline) and `$$...$$` (display) are supported. `\[...\]` and `\(...\)` are not handled by the TeX parser. No code change.

### Gotcha 13.5 (line 895) — No `\section*{}` starred variants

**Status: STILL TRUE**

`apply_sections` in `scriba/tex/parser/environments.py` handles `\section`, `\subsection`, `\subsubsection` but not their starred forms. No code change.

### Gotcha 13.6 (line 898) — Starlark integer literals max 10,000,000

**Status: STILL TRUE — value confirmed correct**

`_MAX_INT_LITERAL = 10**7` at `scriba/animation/starlark_worker.py:45`. The cap of 10,000,000 (10^7) is exact. The doc's `≤10,000,000` wording matches. The `10**9` workaround is valid because `10**9` is a binary expression (`BinOp` AST node), not a `Constant`, and therefore bypasses the literal cap.

### Gotcha 13.7 (line 909) — `\LaTeX` and unsupported commands render as literal text

**Status: STILL TRUE**

Unsupported backslash commands pass through as literal text. No strict-parse mode has been added for the TeX renderer that would raise on unknown commands.

### Undocumented gotchas found in code

**NEW: Windows — SIGALRM backstop unavailable**

On Windows, the `RLIMIT_CPU`/`SIGALRM` wall-clock safety net for Starlark is absent. The step counter (`_STEP_LIMIT = 10**8`) remains, but a runaway C-extension builtin that does not tick the trace hook could evade it. The host emits a `RuntimeWarning` (`starlark_host.py:64`), but this is not documented as a user-facing gotcha in §13. Severity: LOW for most users (not Windows-targeted), but the behaviour difference is real.

---

## §14 Limits

Doc table (lines 917–928) lists nine limit rows. Code ground truth follows each.

| Limit | Doc value | Code value | Source | Status |
|-------|-----------|------------|--------|--------|
| Source size | 1 MiB max | `MAX_SOURCE_SIZE = 1_048_576` | `scriba/tex/renderer.py:115` | OK |
| Math expressions | 500 per document | `MAX_MATH_ITEMS = 500` | `scriba/tex/parser/math.py:21` | OK |
| Animation frames | 30 soft / 100 hard | `_FRAME_WARN_THRESHOLD = 30`; `FrameCountError` at >100 | `scriba/animation/renderer.py:55`; `scriba/animation/errors.py:576-581` | OK |
| Starlark timeout | 5 seconds per `\compute` | transport timeout `5.0 s`; CPU soft limit `5 s` | `scriba/animation/starlark_host.py:79`, `178` | OK |
| Starlark ops | 10^8 per block | `_STEP_LIMIT = 10**8` | `scriba/animation/starlark_worker.py:809` | OK |
| Starlark memory | 64 MB per block | `_TRACEMALLOC_PEAK_LIMIT = 64 * 1024 * 1024`; `_MEMORY_LIMIT_BYTES = 64 * 1024 * 1024` | `scriba/animation/starlark_worker.py:815`; `scriba/animation/starlark_host.py:77` | OK |
| Starlark int literals | ≤10,000,000 | `_MAX_INT_LITERAL = 10**7` | `scriba/animation/starlark_worker.py:45` | OK |
| foreach nesting | 3 levels max | `_MAX_FOREACH_DEPTH = 3` | `scriba/animation/parser/_grammar_foreach.py:21`; `scriba/animation/scene.py:333` | OK |
| substory nesting | 3 levels max | `_MAX_SUBSTORY_DEPTH = 3` | `scriba/animation/parser/_grammar_substory.py:30` | OK |
| Graph stable layout | ≤20 nodes, ≤50 frames | `_MAX_NODES = 20`; `_MAX_FRAMES = 50` | `scriba/animation/primitives/graph_layout_stable.py:31-32` | OK |

### Undocumented limit found in code

**Annotations per frame — 500 (undocumented)**

`_MAX_ANNOTATIONS_PER_FRAME = 500` at `scriba/animation/scene.py:334`. Exceeding this raises `E1103` with the message "exceeds maximum of 500 annotations per frame" (`scene.py:663-666`). This limit is not mentioned in §14.

---

## Findings

### [MED] `grid` environment option accepted but undocumented and inert

`"grid"` is a valid key in `VALID_OPTION_KEYS` (`constants.py:46`) and passes parser validation, but is never forwarded into `AnimationOptions` (`ast.py:291-298`, `grammar.py:521-527`). Authors who write `\begin{animation}[grid=true]` receive no error and no effect. §10 should either document `grid` with a note that it is reserved/no-op, or remove it from `VALID_OPTION_KEYS`.

### [MED] Annotations-per-frame limit (500) not documented in §14

`_MAX_ANNOTATIONS_PER_FRAME = 500` is enforced at runtime (`scene.py:334, 663-666`) with an `E1103` error. Documents that push past 500 annotations per step will receive a hard error with no prior warning. §14 should add this row.

### [LOW] Gotcha 13.6 wording: "≤10,000,000" is correct but explain `10**N` better

The doc says "use `10**N` for larger" which is correct. A small clarification that this works because `10**N` is a `BinOp` AST node (not a `Constant`) would help authors understand why it works, not just that it does.

### [LOW] Windows SIGALRM gap not documented as a gotcha

`starlark_host.py:41-70` emits a `RuntimeWarning` about the missing wall-clock backstop on Windows, but §13 has no corresponding gotcha. Scriba is not primarily Windows-targeted, but the behavioural divergence (step-counter-only protection) is worth noting.

### [LOW] `info` and `path` annotation colors share the same light-mode hex

Both resolve to `#0b68cb` in light mode (`scriba-scene-primitives.css:160, 164`). They are visually indistinguishable to the author. Not a code bug, but worth a doc note in §11.

---

## Verdict

**8/10**

All documented limits and option names match code exactly. All six annotation color tokens exist in code and CSS. Gotchas §13.1–13.7 are all still accurate — none have been silently fixed. Two substantive gaps were found: the `grid` option (accepted, inert, undocumented) and the 500-annotation-per-frame limit (enforced, undocumented). Two lower-severity observations round out the findings. No CRITICAL issues.
