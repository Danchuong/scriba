# Fix spec — JZ-13: label pipeline "one interpretation" contract (measure == paint == announce)

**Status:** implemented, GREEN (93/93 targeted + 83 consumer regression tests)
**Investigation:** `investigations/judgezone-13-label-textmode-investigation.md`
**Authors:** fix-label agent (implementation; session expired before this spec) + lead session (property-test whitespace edge, verification renders, this spec)

## Contract

A label string has ONE interpretation shared by all three consumers:

| Consumer | Function | File |
|---|---|---|
| width ruler | `pill_dimensions` | `_svg_helpers.py` |
| SVG painter | `_emit_pill_label_text` / `strip_math_markup` | `_svg_helpers.py` / `_text_render.py` |
| aria/title builder | `_latex_to_speech` | `_svg_helpers.py` |

Rules: text outside `$...$` is literal (`_` literal, `\_` → `_`, no TeX-speech
transforms); math transforms and R-11 speech rules apply ONLY inside `$...$`
segments; `\texttt{...}` is a literal-text-island that unwraps unconditionally
(mirrors `core/text_utils.py::apply_text_commands`). ONE sanctioned divergence:
speech collapses whitespace runs as its final a11y step (R-11 step 7); paint
preserves them.

## Per-defect fixes

### Defect 1 — width under-reserve on wrapped labels (root cause ≠ report)
Reporter's subscript theory REFUTED by investigation; real cause: painter
re-adds an unmeasured trailing space to every non-final wrapped line
(`_emit_pill_label_text`), ruler measured the rstripped line.
**Fix:** `pill_dimensions` now mirrors the painter's OWN branching exactly
(`_svg_helpers.py` ~1474): FO path (KaTeX callback + math present) measures
bare lines; both tspan fallback paths add `measure_text_run(" ")` /
`estimate_text_width(" ")` to non-final lines. Generic: fixes ALL 2+-line
wrapped labels, not just underscores.

### Defect 2 — aria said "subscript" for plain text
`_SUBSCRIPT_RE`/`_latex_to_speech` ran unconditionally on the raw label.
**Fix:** speech algorithm split: `_speech_segment` (R-11 steps 2–6) runs per
`$...$` fragment only; outside-math text gets `_unescape_literal` only
(`_svg_helpers.py:1045-1118`).

### Defect 3 — `\_` painted a literal backslash
`strip_math_markup` early-returned unchanged when no `$` present.
**Fix:** `_unescape_literal` (`\_` → `_`) applies to literal text on every
path, gated or not (`_text_render.py:201-245`).

### Defect 4 — `\texttt{}` painted verbatim + garbled aria
No unwrap outside math; speech backslash-strip mangled it.
**Fix:** `_unwrap_texttt` unconditional pre-pass before any `$`-split, in both
`strip_math_markup` and `_latex_to_speech`. Its `\_` content unescapes via the
`_SENT_LIT_USCORE` sentinel so math-fragment subscript regexes can never
misread the restored `_` (restored as the very last step).

### Side-finding — `color="state:X"` silently painted as "info"
`ARROW_STYLES` keys are bare (`info/warn/good/error/muted/path`); every
`ARROW_STYLES.get(color, ARROW_STYLES["info"])` call site collapsed all six
`state:X` tokens to "info".
**Fix:** shared resolver `resolve_arrow_style` replaces all 5 call sites
(`emit_plain_arrow_svg`, `emit_arrow_svg` ×2, `_position_pill_width`,
`emit_position_label_svg`). `state:X` resolves via new
`STATE_ANNOTATION_FALLBACK` (stroke/label_fill = the CSS-authoritative
`--scriba-annotation-state-*` light hex; non-color cosmetics borrow the
closest bare analogue). Unknown token → `warnings.warn("[E1113] ...")` +
"info" fallback (fail-loud instead of silent wrong choice).

## Tests (all GREEN; RED confirmed against pre-fix code by fix-label)

- `tests/unit/test_label_one_interpretation.py` — 15 pins: paint/speech per
  variant, 4-variant convergence, `$dp_i$` → "dp subscript i" regression pin,
  mixed text+math.
- `tests/unit/test_pill_math_wrap.py` — +2 multiline invariants
  (`covers_painted_text_multiline`, no-callback twin) — exactly the gap that
  hid defect 1.
- `tests/property/test_label_one_interpretation.py` — 6 hypothesis properties
  (200 examples each): paint/speech convergence (whitespace-normalized — the
  sanctioned divergence), no `\_` survivor, no `texttt` leak, generalized
  `$x_i$` speech, mixed-segment scoping, pill-width ≥ measured painted lines
  (both paint branches).
- `tests/unit/test_state_color_leader.py` — resolver coverage (state:X ≠
  info, unknown warns).

Fixed during hand-off: property `test_paint_and_speech_converge_outside_math`
initially demanded byte-identical outputs; falsified by `' '` (speech
whitespace-collapse). Amended to whitespace-normalized comparison + docstring
documents the sanctioned divergence.

## Verification (real renders, 4 variants, post-fix)

| variant | painted line 1 | aria | pill w (pre→post) |
|---|---|---|---|
| `upper_bound = ...` | `upper_bound = begin(): ` | literal, no "subscript" | 134 → 136.95 |
| `upper\_bound = ...` | `upper_bound = begin(): ` (no `\`) | literal | 138 → 140.95 |
| `\texttt{upper\_bound} = ...` | `upper_bound = ` (unwrapped) | literal | 134 → 136.95 |
| `$\texttt{upper\_bound}$ = ...` | KaTeX mono (unchanged path) | literal | FO path |

+2.95px = the previously-unmeasured trailing space — matches the reporter's
~3px shortfall (122 measured vs 125 painted). All 4 variants converge on the
identical aria string: `upper_bound = begin(): nothing ≤ 3`.

## Impact analysis (gitnexus, upstream)

- `pill_dimensions`: CRITICAL / 28 impacted / 19 processes (hub: every pill
  emitter).
- `_latex_to_speech`: CRITICAL / 27 impacted / 18 processes.
- `strip_math_markup`: CRITICAL / 116 impacted / 38 processes (hub: measure +
  paint fallbacks across all primitives).
CRITICAL is fan-out-count: these ARE the shared label pipeline, touching them
is the point of a structural fix. Mitigation: 93 targeted + 83 consumer tests
GREEN (`tests/animation/`, note/i18n/text-metrics suites); full-suite + full
golden-corpus verification required before release (consolidation phase).

## Goldens expected to shift

Any golden with a 2+-line wrapped annotation/position label: pill width grows
by one space-advance (~3px @ 11px font). Any golden using `color="state:X"`
arrows/position labels: stroke/label_fill change from info-blue to the correct
state hex. Not re-blessed here — central re-bless in consolidation.

## Regression risks

- `$dp_i$`-style real math subscripts: pinned by unit + property tests.
- RTL/i18n: Vietnamese verified no-divergence (investigation) + property
  alphabet includes diacritics; bidi handling untouched.
- `\$` escapes: `strip_math_markup` sentinel path untouched for math-bearing
  strings.
- Speech whitespace collapse preserved (R-11 step 7) — aria strings for
  existing corpora unchanged except where they were wrong (subscript/texttt).

## Sweep wave (wave 2)

**Status:** implemented, GREEN (60/60 targeted). Golden corpus is currently
red repo-wide but for reasons unrelated to this wave — see Golden status.
**Scope:** every OTHER text channel that measures+paints+announces author
strings, per the wave-1 follow-up brief. Owner: sweep-label agent.

### Channel inventory

| Channel | Measure | Paint | Announce | Verdict |
|---|---|---|---|---|
| Annotation pill (`\annotate`/`\link`/`\note`) | `pill_dimensions` | `_emit_pill_label_text` | `_latex_to_speech` | wave-1 fixed |
| Cell/node `value=` (Array, VariableWatch, Equation, NumberLine, Bar, graph node/edge weight) | `measure_value_text` | `_render_svg_text`/`_render_mixed_html` | none exists | **VIOLATION — fixed this wave** |
| Generic wrapped label line (shared multi-consumer helper) | `measure_label_line` | feeds pill/position/bar via `_render_*` | — | **VIOLATION — fixed this wave** (same root cause) |
| `\trace` scan-pill text | `strip_math_markup` | `strip_math_markup` | `strip_math_markup` | clean — already wired to wave-1-fixed helper (`base.py::emit_traces_under` L782-793) |
| `\group` title/hull label | `measure_label_line` (width) | `strip_math_markup` | `strip_math_markup` | clean paint/announce; latent measure-side gap closed by this wave's fix (`graph.py::_emit_group_hulls` L2020-2086) |
| Position labels (`emit_position_label_svg`) | `pill_dimensions` | `_emit_pill_label_text` | `_latex_to_speech` | clean, confirmed already on wave-1-fixed helpers (`_svg_helpers.py` L3705-3795) |
| Graph edge topology `aria-label`/`<title>` | n/a | n/a | synthetic `"Edge from node X to node Y"`, disjoint from weight text | N/A — not a text channel, nothing to diverge |
| `\includegraphics` alt=filename | n/a | n/a | alt = raw filename | investigated, not fixed — see below |

### Violation found + fixed: the `value=` channel (4 shared functions)

Root cause, same signature as wave-1: `_render_svg_text`, `_render_mixed_html`
(`_text_render.py`) and `measure_value_text`, `measure_label_line`
(`_text_metrics.py`) gated their literal-text pass on `_has_math(text)`. For
non-math text — a plain value like `upper_bound`, the dominant real-world
case — 3 of 4 callback×math combinations skipped
`_unwrap_texttt`/`_unescape_literal`/`strip_math_markup` entirely and
painted/measured raw markup (`\_` as literal backslash-underscore,
`\texttt{...}` verbatim). Worst case: "callback present + no math" — the
default in practice, since Pipeline/TexRenderer always registers a working
KaTeX callback.

VariableWatch, Equation, NumberLine, Bar, Array, and graph node/edge-weight
text all call these same 4 functions, so fixing the 4 functions fixed every
consumer transitively — no per-primitive edits, per the "route through
shared helpers, don't reimplement" constraint.

**Fix** (mirrors wave-1's own pattern):
- `_render_svg_text` fast path: wrap in `strip_math_markup(...)`
  unconditionally, regardless of callback presence.
- `_render_mixed_html`: non-math segments wrapped in `strip_math_markup(...)`
  before sentinel restoration — same restore-order-safety invariant as
  wave-1 (sentinels/placeholders restore AFTER the literal-text transform,
  never before; restoring first risks two independent escapes/refs
  re-pairing into a phantom math span).
- `measure_value_text`: no-`$` fast path now routes through
  `strip_math_markup` before width measurement.
- `measure_label_line`: BOTH the no-`$` early return AND the has-`$`
  branch's non-math `text_seg`/`tail` splits route through
  `strip_math_markup` — matching exactly what `_render_mixed_html` paints
  for the same split.

A concurrent peer fix (JZ-11, `${ident}` interpolation-ref shielding, same
file) layers `_shield_interp_refs`/`_unshield_interp_refs` around these
changes. Verified compositionally correct by full diff read: the peer's
shield/unshield wraps outside this wave's `strip_math_markup` call, in the
correct order, and the peer's own comment explicitly cites and extends this
wave's restore-order-safety invariant.

### Channels confirmed clean (no fix needed)

- **`\trace` scan-pill** (`base.py::emit_traces_under`): paint (L782-786)
  and aria-label (L787-793) both call `strip_math_markup` directly already.
- **`\group` title/hull** (`graph.py::_emit_group_hulls`): aria-label
  (L2020-2027) and paint `<text>` (L2082-2086) call `strip_math_markup`;
  width (L2033) calls `measure_label_line` — now fixed above, closing a
  latent measure-side divergence that existed even though paint/announce
  were already correct.
- **Position labels** (`_svg_helpers.py::emit_position_label_svg`,
  L3705-3795): measure = `pill_dimensions`, announce = `_latex_to_speech`,
  paint = `_emit_pill_label_text` — all three wave-1-fixed already. Matches
  the brief's expectation exactly.
- **Graph edge topology announce** (`graph.py` L2294-2523): `aria-label`/
  `<title>` built from `f"Edge from node {u} to node {v}"` — node
  identifiers, not weight/value text. `display_weight` (the actual weight
  text) is a disjoint string that already routes through
  `measure_value_text`/`_render_svg_text`/`_render_split_label_svg` (fixed
  above). No violation: the two strings never claim to represent the same
  content.

### No-announce-channel finding

VariableWatch, Equation, NumberLine, Bar, Array, and graph node/edge values
have **no separate aria/title/`data-value` announce channel at all** —
grepped `aria`, `aria-label`, `<title`, `role="img"`, `data-value` across
all 6 files, zero hits outside the graph edge topology case above. Not a
violation (nothing to diverge from); documented so a future `data-value=`
or per-cell `aria-label` addition knows to route through the same 4 fixed
functions from day one.

### `\includegraphics` alt=filename (JZ-10-adjacent, deferred)

Investigated per brief. `alt=` text is the raw filename (e.g.
`alt="diagram.png"`), never run through any measure/paint/speech transform
— so it cannot exhibit the JZ-13 signature (a single flat string used once,
no divergent interpretations to reconcile). Coordinated with sweep-title
(owns JZ-10 proper): not fixed. Filename-as-alt-text is a separate
a11y-quality smell (bad alt text), not a one-interpretation violation —
outside JZ-13's family. No action taken.

### Tests

`tests/unit/test_value_math_sizing.py::TestValueChannelOneInterpretation` —
9 new tests, parametrized over the JZ-13 4-variant pattern (`upper_bound` /
`upper\_bound` / `\texttt{upper\_bound}` / `$\texttt{upper\_bound}$`) across
all 4 fixed functions: measure convergence (×2, incl. the has-`$`
mixed-segment split), paint convergence with and without a KaTeX callback,
`_render_mixed_html` convergence, the one sanctioned exception (`\texttt{}`
inside real `$...$` stays untouched for KaTeX), mixed literal+math segment
scoping, and an adjacent-escaped-dollar phantom-pairing stress test
(sentinel-restore-order safety, mirrors wave-1's own regression pin).

### Verification

Targeted suite green:
```
tests/unit/test_label_one_interpretation.py
tests/property/test_label_one_interpretation.py
tests/unit/test_pill_math_wrap.py
tests/unit/test_value_math_sizing.py
```
→ 60/60 passed.

### Golden status: RED, unrelated to this wave

`tests/golden/examples/` — 107 failed / 1 passed. Fully investigated, **not
a regression from this wave's fix**:
- Full untruncated diff on 2 representative goldens (`hello`,
  `variablewatch`) shows 100% CSS-block-and-class-marker divergence (a
  concurrent agent's dark-mode "wave-2 theme-attr sweep" — e.g. new
  `class="scriba-annot-label-text"` markers), **zero value-text-content
  differences**.
- Full corpus grep: no `.tex` example under `tests/golden/examples/corpus/`
  exercises `\_`/`\texttt` inside a primitive's `values=`/`labels=` field —
  all such occurrences are inside `\narrate{}` prose (a disjoint rendering
  channel). This wave's fix is therefore **invisible in the current
  corpus** — a coverage gap, not a fix defect.
- `git status`/`git diff --stat` cross-check: this wave never touched any
  CSS file or `_svg_helpers.py` (own-files constraint honored); the only
  files modified are `_text_render.py`, `_text_metrics.py`,
  `test_value_math_sizing.py`.
- Recommendation for consolidation phase: add a golden example exercising
  `\_`/`\texttt` inside a `values=` field to close this corpus gap and give
  the value= fix golden-level coverage.

`detect_changes()` intentionally not run repo-wide for this wave: not
committing (explicit constraint), and repo-wide scope at this point in the
sweep mixes in 130+ files of concurrent unrelated agent work, producing
low-signal noise rather than a usable diff.

### Impact analysis (gitnexus, upstream, `repo=scriba`)

- `_render_svg_text`: CRITICAL / 32 impacted / 11 processes.
- `_render_mixed_html`: CRITICAL / 45 impacted / 15 processes.
- `measure_value_text`: CRITICAL / 68 impacted / 15 processes.
- `measure_label_line`: CRITICAL / 129 impacted / 40 processes (largest hub
  touched by either wave — reaches `_svg_helpers.py` position-label
  helpers, every primitive's `bounding_box`/`__init__`, and
  `_html_stitcher.py`).

All 4 CRITICAL by fan-out, consistent with wave-1's own hub functions
(`strip_math_markup`: 116/38). Mitigation: same posture as wave-1 —
targeted tests green; golden-corpus content-level verification done via
direct diff (see Golden status) since the corpus itself doesn't exercise
the fixed path end-to-end.
