# Spec-Fix: JudgeZone #11 — `${...}` Interpolation Shape Gate (+ Sibling)

**Agent:** fix-interp (BMAD patcher)
**Status:** DONE — primary fix and sibling fix both GREEN, regression-clean.
**Investigation doc:** `_bmad-output/implementation-artifacts/investigations/judgezone-11-narrate-interp-clash-investigation.md`

## Contract

`${...}` is interpolation syntax **if and only if** its brace content is
identifier-shaped: an identifier, optionally followed by zero or more
`[index]` / `.attr` tails. This is the same shape
`selectors.py::_expect_ident` already enforces at selector positions.

Anything else — math (`${5 \choose 3}`), arithmetic (`${i+1}`), a bare
call expression (`${range(25)}`), or an empty body (`${}`) — is **not**
interpolation syntax at all. It must never be partially consumed as if it
were, and it must never silently resolve to a garbage literal at runtime.
It either falls through to normal `$...$` math pairing (renderer) or fails
loudly with a new error code (parser), per call site.

This restores the documented guarantee at
`docs/SCRIBA-TEX-REFERENCE.md` §13.4:

> `${name}` interpolation (§13.2) never clashes with math: a `${...}` run
> is shielded before math parsing, so an unresolved `${name}` sitting next
> to a stray `$` stays literal instead of being paired into `$...$`.

Root cause (confirmed, not the lexer): the shield regex in
`scriba/tex/renderer.py` (previously unconditional) consumed one `$` per
`${...}` match regardless of brace-content shape. For math-shaped content
this ate only the `${` opener's dollar, not the `$` the author wrote to
close their math — an odd dollar count that mis-paired every later
`$...$` on the line.

---

## Work Item 1 (PRIMARY) — `scriba/tex/renderer.py`

### Fix

Added two class attributes directly above `_render_cell`
(`scriba/tex/renderer.py:397-418`):

- `_INTERP_IDENT` (`:397-404`) — identifier fragment: `[^\W\d]` start,
  then `\w` or a combining-mark continuation, `*`-repeated.
- `_INTERP_SHAPE_RE` (`:411-418`) — `^\{IDENT(?:\[[^\]]*\]|\.IDENT)*\}$`
  applied to the shield match's content (brace-delimited).

Gated the shield inside `_render_cell` (`:460-476`): the `re.sub` callback
(`_shield_sub`, `:471-474`) now checks `_INTERP_SHAPE_RE.match(m.group(0)[1:])`
first; on no match it returns `m.group(0)` unchanged so the text falls
through to the two subsequent `$$...$$` / `$...$` passes at `:477-478`
exactly as if the shield never ran.

### Unicode-identifier decision

`_INTERP_IDENT`'s combining-mark ranges
(`̀-ͯ`, `҃-҉`, ... `︠-︯`) are copied verbatim
from `scriba/animation/parser/lexer.py:104`'s `_IDENT_RE`, **not**
`[^\W\d]\w*` alone. Justification: a `\compute` binding name is legal
anywhere `\w` combining marks make Thai/Devanagari/Hebrew identifiers
possible (e.g. a Thai binding `ค่า`), and the lexer already accepts such
names for real `\compute{ค่า = ...}` bindings — the renderer's shape gate
must classify `${ค่า}` as interpolation exactly as the lexer would, or a
legitimate non-Latin binding reference would wrongly fall through to math
pairing and get corrupted. `scriba.tex` cannot import
`scriba.animation.lexer` (layering: `tex` must not depend on `animation`),
so the ranges are duplicated with a comment pointing at the source of
truth. Verified via `TestInterpShapeRegexContract::test_shape_gate_classifies_content[{ค่า}-True]`.

No dot/`.attr` support was added to the *sibling* fix (see below) — but
the renderer's gate *does* accept `.attr` tails, because the investigation
doc's verified sketch specifies it and existing shielded literal forms
like `${arr.length}` must keep echoing literally (Work Item 3d).

### Tests — RED → GREEN

New file: `tests/tex/test_interp_shape_gate.py` (18 tests).

RED (confirmed via `git stash push -- scriba/tex/renderer.py`, i.e. against
the actual pre-fix shield): **11 failed / 7 passed**. Failures showed the
predicted corruption exactly — e.g. the repro narration's Vietnamese text
absorbed into a garbled KaTeX span, a stray trailing `$`, and 4 of 5
expected math spans instead of 5.

GREEN (after `git stash pop`, i.e. with the fix in place): **18 passed.**

| Test | Covers |
|---|---|
| `TestInterpShapeGateRepro::test_repro_narration_yields_five_clean_math_spans` | Work Item 3a — repro line, 5 clean spans, no raw `${5` echo, no stray `$` |
| `TestInterpShapeGateRepro::test_control_narration_yields_five_clean_math_spans` | Work Item 3b — `\binom{5}{3}` control equivalence |
| `TestInterpShapeGateRepro::test_invariant_narration_yields_five_clean_math_spans` | Work Item 3c — same clash via `\invariant` panel text |
| `TestInterpShapeGateStillShields::test_genuine_interp_form_echoes_literally[${a}\|${a_1}\|${arr[i]}\|${total}\|${arr.length}]` | Work Item 3d — every genuine interp form still shielded |
| `TestInterpShapeGateStillShields::test_shielded_interp_does_not_disturb_neighbouring_math` | Work Item 3e — unbound-but-identifier-shaped still echoes literally, doesn't disturb neighboring math |
| `TestInterpShapeRegexContract::test_shape_gate_classifies_content[9 cases]` | Direct regex contract, including the Thai combining-mark case, no KaTeX worker needed |

Regression (mandatory per task): `tests/unit/test_reannotate_apply_compute.py:366-373` and
`:375-388` — **pass unmodified**, confirmed as part of the full targeted run below.

### Repro before/after (real renders, not just unit tests)

Rendered via `SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py <tex> -o <out.html>`
against the scratchpad fixtures (`jz11_repro.tex`, `jz11_control.tex`,
`jz11_invariant.tex`):

| Fixture | `scriba-tex-math-inline` spans (pre → post) | Raw `${5` echoes (pre → post) |
|---|---|---|
| `jz11_repro.tex` | 12 → **15** | 3 → **0** |
| `jz11_control.tex` (baseline, never hits the shield) | 15 → 15 (unchanged) | n/a |
| `jz11_invariant.tex` | 12 → **15** | 3 → **0** |

The +3 delta (not +1) is expected, not a discrepancy: the narration text
is duplicated across 3 separate page-rendering surfaces in the full HTML
output (e.g. filmstrip caption + step panel + a third surface), each
independently corrupted pre-fix by the same per-call shield bug and each
independently fixed by the same change. The control fixture (which uses
`\binom{5}{3}` and never contains the literal substring `${`) is included
as a baseline showing the target shape (5 clean spans) was reachable all
along for non-`${`-shaped math — confirming the bug was specific to the
shield, not math-pairing in general.

---

## Work Item 4 (SIBLING) — `scriba/animation/parser/_grammar_values.py`

### Decision: fail-loud E1161 for all non-identifier shapes (no partial preservation)

Per the task's decision rule, searched `examples/`, `tests/`, and `docs/`
(excluding `docs/legacy/`, see below) for every `value=${...}`-shaped
usage:

```
grep -rEon '=\$\{[^}]*\}' examples/ docs/ tests/
```

**Result: every real, tested usage is identifier-shaped** (bare name or
`name[sub]*`, subscript either an int literal or another identifier) —
`${dp}`, `${i}`, `${arr[0]}`, `${dp_vals[i][j]}`, `${d[key]}`,
`${unbound_var}`, `${nope}`, etc. Nothing in the corpus relies on a
math-shaped or otherwise-invalid `${...}` resolving to its literal string
at runtime. This authorizes the task's "nothing relies on non-identifier
fallback → add validation with a fail-loud E-code" branch.

Two side-findings from that grep, neither a regression:

1. `docs/legacy/**` (`frog1-demo/app.js`, `swap-game-demo*/app.js`,
   `pivot-1-research/*.md`) contains non-identifier `${...}` forms
   (`${c.total}`, `${step.dist[name]}`, `${this.onCellClick}`). These are
   **not** Scriba TeX syntax — `docs/legacy/README.md` states outright:
   "This directory archives the first-generation Scriba design... **That
   model has been retired.**" They're plain ES6 template-literal JS from
   a retired standalone-DSL prototype's HTML/JS demos. Irrelevant to
   `_parse_interp_ref`.
2. `docs/primitives/graph-stable-layout.md:527` (§11.3, "Fallback test —
   N=25 triggers E1501") has `nodes=${range(25)}` — not identifier-shaped.
   This example is **not** covered by any `tests/doc_coverage/corpus/`
   fixture (unlike sibling examples in the same doc, which have matching
   `.tex` corpus files). Traced what pre-fix behavior actually was:
   `_parse_interp_ref("range(25)")` has no `[`, so pre-fix it built
   `InterpolationRef(name="range(25)")` unconditionally; at runtime
   `scene.py`'s `.get("range(25)", "range(25)")` would return the literal
   string `"range(25)"` — never a 25-element node list — so the Graph
   shape's `nodes` param would receive a string, not a list, and the
   documented "E1501 emitted (N=25 > 20)" outcome could never actually
   have been reached this way. **The example was already non-functional
   before this fix**; it was illustrative/aspirational, not a working,
   tested code path. Confirmed post-fix behavior directly:
   ```
   AnimationError code=E1161 msg=${range(25)} is not identifier-shaped...
   ```
   This is a strict improvement (fails loudly and immediately at the
   interpolation site with an actionable message) over the prior silent
   wrong-type value that would have surfaced later, confusingly, as a
   Graph shape validation failure. Flagging as a doc-accuracy follow-up;
   `docs/primitives/graph-stable-layout.md` is outside this agent's scope
   fence (only `docs/spec/error-codes.md`, registration-only, is owned
   here), so no edit was made to it.

No dot/`.attr` tail support was added here (asymmetric vs. the renderer's
gate, intentionally): grepped the same corpus for a dotted
`InterpolationRef`-producing form and found none; nothing downstream ever
resolves a dotted `InterpolationRef.name`. Adding it would be speculative
scope beyond what's asked.

### Fix

`scriba/animation/parser/_grammar_values.py`:
- `:10` — added `from ..errors import _animation_error` (fresh import;
  confirmed `SelectorParser._error()` in `selectors.py` is an unrelated,
  standalone class not reachable from `_ValuesMixin`'s MRO, so it could
  not be reused).
- `:60-109` — `_parse_interp_ref` now splits `name`/`rest` unconditionally
  first, then:
  - `:80-88` — raises `_animation_error("E1161", ...)` if
    `not name.isidentifier()` (covers empty content, math bodies,
    backslash commands, arithmetic-as-name, whitespace).
  - `:97-105` — for each subscript that fails `int(sub_str)` conversion,
    raises the same `E1161` if `not sub_str.isidentifier()` (covers
    arithmetic subscripts like `arr[i+1]`), before falling back to
    treating it as a name-subscript.

`scriba/animation/errors.py:300-305` — new `ERROR_CATALOG["E1161"]` entry,
inserted directly after `"E1159"`, with an explicit comment that `E1160`
remains reserved (pre-existing gap, left untouched).

`docs/spec/error-codes.md:89` — new table row registered in the "Starlark
Sandbox Errors" section, directly after the `E1159` row, matching that
row's column format (Code / Description / Common Fix). Note: this
section's header already read `(E1150--E1156)` while listing through
E1159 *before* this change — a pre-existing, stale range comment. Left
as-is (registration only, per scope fence); flagging as a side-finding
for whichever agent next touches that header.

### Tests — RED → GREEN

New file: `tests/unit/test_interp_ref_shape_validation.py` (13 tests).

RED (confirmed against the unmodified method, before any sibling-fix code
existed): **6 failed / 7 passed** — failures were all `DID NOT RAISE
AnimationError`, confirming the exact "silent wrong-value fallback" the
task described (a math-shaped `${...}` built a garbage
`InterpolationRef` with no error).

GREEN (after implementing the validation above): **13 passed.**

| Test class | Covers |
|---|---|
| `TestParseInterpRefValidShapes` (6 tests) | Bare identifier, int subscript, name subscript, multiple subscripts, underscore/digit identifier, Unicode (Thai) identifier — all still parse unchanged |
| `TestParseInterpRefRejectsMathShape` (5 tests) | `5 \choose 3`, `\text{x}`, empty string, arithmetic subscript `arr[i+1]`, whitespace name — all raise `E1161` |
| `TestParseInterpRefEndToEnd` (2 tests) | Full `SceneParser().parse()` path: a legitimate `value=${dp}` still parses; `value=${5 \choose 3}` raises `E1161` end-to-end (the sibling repro) |

### Regression sweep (both fixes, targeted per task's explicit scope)

```
uv run pytest tests/unit/test_reannotate_apply_compute.py tests/tex/ \
  tests/unit/test_interp_ref_shape_validation.py tests/unit/test_parser_interpolation.py \
  tests/unit/test_foreach.py -q -p no:cacheprovider
# 253 passed, 1 warning (pre-existing, unrelated)

uv run pytest tests/unit/test_parser_values_unit.py tests/unit/test_interp_generic_selectors.py \
  tests/unit/test_authoring_traps.py tests/unit/test_animation_parser.py -q -p no:cacheprovider
# 156 passed, 8 warnings (pre-existing, unrelated)
```

The second sweep covers files found via `grep -rn "_parse_interp_ref\|InterpolationRef(" tests/ scriba/`
that were not in the task's explicit list but directly exercise the
sibling's target function/type — including `test_parser_values_unit.py`,
which unit-tests `_parse_interp_ref` end-to-end and was the highest-risk
file for an overlooked regression. **409 tests total, 0 failures.**

`tests/unit/test_authoring_traps.py:211,221,230` construct
`InterpolationRef(...)` directly (bypassing `_parse_interp_ref` entirely),
including one with `subscripts=("i+1",)` — unaffected by this fix since
validation lives only in the parse function, not the AST dataclass.
Confirmed passing.

---

## GitNexus impact analysis (run before editing, per repo `CLAUDE.md`)

`impact(target="_render_cell", direction="upstream", file_path="scriba/tex/renderer.py")`:
risk **LOW**, impactedCount 2 — direct caller `TexRenderer.render_inline_text` (depth 1),
transitively `_inline_tex` in `render.py` (depth 2). No affected execution
processes.

`impact(target="_parse_interp_ref", direction="upstream", file_path="scriba/animation/parser/_grammar_values.py")`:
risk **LOW**, impactedCount 1 — reached via `SceneParser`'s mixin
composition (`METHOD_OVERRIDES`, depth 1; concretely called from
`_grammar_tokens.py:343`). No affected execution processes.

Both LOW-risk, consistent with the narrow, call-site-local nature of both
changes — neither introduces a new caller or changes a public signature.

## Regression risks

- **Renderer**: none identified beyond the corpus already swept. The
  shape gate is strictly *more permissive* about what falls through to
  math pairing (previously: everything inside `${...}` was shielded
  unconditionally; now: only identifier-shaped content is) — it cannot
  newly break a case that used to render as math, only fix cases that
  used to render as broken math.
- **Sibling**: the one identified doc example that would newly fail
  (`docs/primitives/graph-stable-layout.md:527`) was already
  non-functional pre-fix (see above) and untested — its failure mode
  changes from "silent wrong value, confusing downstream Graph-shape
  error" to "immediate, actionable E1161 at the interpolation site."  No
  passing test, example, or documented-as-working behavior newly breaks.
- Golden corpus: no math-shaped `${` exists in `tests/golden/examples/`
  (confirmed via the corpus-wide grep above — the only golden-corpus
  `${...}` hits are `${i}` and `${maze}`, both identifier-shaped). **No
  golden re-bless needed or performed.**

## Scope compliance

Touched only: `scriba/tex/renderer.py`, `scriba/animation/parser/_grammar_values.py`,
`scriba/animation/errors.py` (new `E1161` entry only), `docs/spec/error-codes.md`
(one new registration row only), and two new test files
(`tests/tex/test_interp_shape_gate.py`, `tests/unit/test_interp_ref_shape_validation.py`).
No CSS, `plane2d.py`, `primitives/base.py`, `_svg_helpers.py`, `_text_render.py`,
`animation/renderer.py`, `_frame_renderer.py`, `animation/scene.py` behavior, or
`lexer.py` touched. No golden re-bless, no version bump, no CHANGELOG edit, no commit.

---

## Sweep wave (wave 2)

**Agent:** sweep-interp (BMAD sweep). Closes the four residual-risk items named
against this family, plus the JZ-11 side-finding. Scope fence: `_text_render.py`
(label math-split region only — `_unescape_literal`/`_unwrap_texttt`/
`strip_math_markup` semantics are JZ-13's frozen contract, not touched),
`docs/primitives/graph-stable-layout.md`, `errors.py` comments, own tests. No
`tex/renderer.py`, `_grammar_values.py`, or `_svg_helpers.py` edits. No version
bump/CHANGELOG/commit.

### Item 1 — REVERSE-RISK probe: label/note `${ident}` vs. adjacent math

**Verdict: REAL, reproducible.** Confirmed via adversarial full-pipeline repro
`"${x} and $mid$ and ${y} tail"` through both `\annotate{...}{label=...}` and
`\note{...}{text=...}`: pre-fix, `_has_math`/`_render_mixed_html` in
`_text_render.py` had no shield at all for `${...}` runs (label/note text is
not a documented interpolation position — SCRIBA-TEX-REFERENCE.md §13.2 — so
any `${name}` reaching this code is always an unresolved literal). Confirmed
corruption: genuine `$mid$` degraded to unstyled literal text (lost its `$`
delimiters and KaTeX rendering), the literal word `" and "` between the two
refs got bogusly KaTeX-rendered as math, and the second ref's leading `$` was
silently eaten, leaving bare `{y}` — no longer even recognisable as `${...}`
syntax. Mirror image of the wave-1 bug: same odd-dollar-parity mechanism, but
here because the position never had a shape-gated shield to begin with,
rather than having an unconditional one.

**Fix** (`scriba/animation/primitives/_text_render.py`): added
`_INTERP_SHAPE_RE` (duplicated from `TexRenderer._INTERP_SHAPE_RE`, same
identifier-fragment character ranges — this low-level SVG text helper stays
free of a dependency on `scriba.tex`) plus a `_shield_interp_refs` /
`_unshield_interp_refs` pair. Identifier-shaped `${...}` runs are replaced
with an opaque, `$`-free placeholder *before* `$...$` pairing runs in
`_has_math` and `_render_mixed_html`, and restored to their original literal
text afterward. Math-shaped `${...}` (e.g. the body of `${5 \choose 3}$`) is
left unshielded and falls through to normal pairing — symmetric with the
wave-1 gate.

Ordering constraint (load-bearing, documented inline at the restore call
site): restoration happens *after* `strip_math_markup` runs on each literal
segment, not before. `strip_math_markup` (JZ-13) does its own internal,
unshielded `$...$` pairing pass — restoring placeholders first would let two
independently-shielded refs re-pair into a phantom math span inside
`strip_math_markup`'s own logic, reproducing the same bug one layer down.
This mirrors the pre-existing `_SENTINEL` (`\x00SCRIBA_BASE_DOLLAR\x00`,
W7-H1's escaped-`\$` guard) restore-after-`strip_math_markup` pattern already
in this function.

**Second exposure found and fixed (beyond the original task brief):** JZ-13's
concurrent edits (landed mid-sweep, in the same file) made
`_render_svg_text`'s fast path call `strip_math_markup` unconditionally
(previously gated on `_has_math`), reopening the identical reverse-risk bug
through a second, independent route — verified analytically for
`"here ${x} and ${y} done"`: `strip_math_markup`'s own unshielded pairing
would find the two dollars from the two refs, pair them, and strip braces,
producing corrupted `"here x and y} done"`. Fixed by applying the same
shield/unshield wrap at that call site. In scope: same file, same label
math-split region, does not touch `strip_math_markup`'s own semantics — only
what text is fed into it.

**Side-finding (documented, not fixed — out of scope):** `\note{...}{text=}`
renders a stray literal backslash (`\`) immediately before `${x}` in the
*visible painted SVG text* (not present in `\annotate{...}{label=}`'s output,
and not present in either primitive's `aria-label`/`aria-description`).
Confirmed real (raw-`repr()` byte inspection, not a display artifact) and
confirmed not introduced by anything in `_text_render.py` (isolated direct
call to `_render_mixed_html` does not add it; grepped for a second shield
copy, found none). It is added upstream of `_render_svg_text`, specific to
`\note`'s text-value handling, in a file outside this sweep's owned scope.
Cosmetic only — `${x}` stays recognisable, not corrupted into bogus math —
so it is not the mis-pairing/corruption bug this item was scoped to fix.
Flagging for whichever agent next owns `\note`'s text-value plumbing.

**Tests:** new `tests/unit/test_interp_reverse_risk_shield.py` (12 tests) —
direct `_render_mixed_html`/`_has_math` unit coverage (fake-tex callback, no
KaTeX worker) plus a full-pipeline adversarial repro through real
`\annotate label=` / `\note text=`. RED confirmed pre-fix (6 failed / 6
passed against the no-shield baseline); GREEN post-fix, 12/12.

### Item 2 — Doc-accuracy fix

`docs/primitives/graph-stable-layout.md:527` used `nodes=${range(25)}`, which
(per the wave-1 sibling fix, Work Item 4 side-finding #2 above) now raises
E1161 and was *already non-functional pre-fix* (silently resolved to the
literal string `"range(25)"`, never a 25-element node list — the documented
"E1501 emitted" outcome could never actually have been reached this way).
Fixed to working syntax, mirroring the working `\compute{}` + `${nodes}`
idiom already demonstrated earlier in the same file (the Tarjan SCC example):

```latex
\compute{
  nodes = list(range(25))
}
\shape{large_g}{Graph}{
  nodes=${nodes},
  edges=[],
  layout="stable"
}
```

### Item 3 — E-code hygiene side-finding

`scriba/animation/errors.py` band-header comments claimed overlapping
ranges: Starlark's header said `(E1150 -- E1179)` and Foreach's said
`(E1170 -- E1179)` — both claiming the 1170s. Verified actual allocation by
reading the catalog: Starlark occupies E1150-E1156, E1159, E1161 (E1157/
E1158 unallocated; E1160 explicitly reserved per its own inline comment,
"earmarked for a separate, not-yet-implemented lint"); Foreach occupies
E1170-E1173, with its header comment already accurately reserving the full
decade (unchanged, matches Starlark's own E1160 reservation precedent).
Fixed both Starlark header comments (lines 296, 870) from `E1150 -- E1179`
to `E1150 -- E1161`. Left Foreach's header untouched (already correct) and
left the separate, unrelated "Scene errors (E1150 -- E1199)" outer-section
label untouched — different, pre-existing, loosely-scoped label (contains
`EmptySubstoryWarning` at E1366, clearly outside any strict numeric claim),
not the specific Starlark/Foreach clash this item named. Comment-only
change; verified via `ast.parse` after each edit.

### Item 4 — Probe non-interpolation positions

Probed `\step[title=]` and top-level `\begin{animation}[label=]` — both
explicitly excluded from the five documented interpolation positions
(§13.2: `\foreach` bodies, `\apply` values, selector indices, `\narrate`
text, `\invariant` panels) — with an unbound `${x}` adjacent to real
`$y_i$` math. Both confirmed **fully inert**: neither has a math-rendering
path at all (title/label are plain attribute text, never reaching
`_has_math`/`_render_mixed_html`), so there is no mis-pairing surface here
the way there was for `label=`/`\note text=` (Item 1) — no `\compute`
substitution, no E1159/E1161, no crash, no KaTeX span produced. Checked
`tests/tex/test_interp_shape_gate.py` and
`tests/unit/test_interp_ref_shape_validation.py` first for overlap — neither
covers these two positions. Pinned both as regression tests (not shape-gate
fixes, since there was nothing to fix) in new
`tests/unit/test_non_interp_positions_inert.py` (2 tests, 2/2 passing).

### GitNexus impact analysis (run before editing, per repo `CLAUDE.md`)

`impact(target="_has_math", direction="upstream")`: risk **CRITICAL**, 33
impacted symbols, 11 processes affected, 2 modules affected.

`impact(target="_render_mixed_html", direction="upstream")`: risk
**CRITICAL**, 45 impacted symbols, 15 processes affected, 3 modules affected.

Both functions sit on the hot path for essentially all SVG text rendering
(labels, annotations, notes, cell values), which is why the blast radius is
large — but the change itself is additive and narrowly gated: identifier-
shaped `${...}` is a new shield applied *before* existing `$...$` pairing,
non-identifier-shaped and plain text take the exact pre-existing code path
unchanged. Verified no regression: `tests/tex/test_interp_shape_gate.py`
(18/18), `tests/unit/test_reannotate_apply_compute.py` (regression-mandated
subset, all passing), JZ-13's own `_text_render`-adjacent suite (9/9), and
the broader `_text_render`-adjacent regression sweep (317/319 passed — 2
pre-existing skips, unrelated). Full-suite run (111 failed / 5949 passed,
beyond this task's specified verify scope, run as an extra safety check
given the CRITICAL rating) triaged below — all 111 confirmed unrelated to
this change.

### Verification

Task-specified verify command:

```
uv run pytest tests/unit/test_interp_reverse_risk_shield.py \
  tests/unit/test_non_interp_positions_inert.py \
  tests/tex/test_interp_shape_gate.py \
  tests/unit/test_reannotate_apply_compute.py -q
# 50 passed
```

Broader `_text_render`-adjacent regression sweep: 317 passed, 2 skipped
(pre-existing, unrelated).

Full-suite safety check (`uv run python -m pytest -q`, beyond task scope):
111 failed / 5949 passed / 9 skipped / 1 xfailed. Triaged all 111 into three
categories, all confirmed pre-existing/concurrent-sibling noise unrelated to
this sweep's `_text_render.py` edits — none touch `${...}` shielding, math
pairing, or text content, all are CSS `class=`/theme-attribute additions on
elements this sweep never edits:

1. ~28× `test_example_matches_golden[...]` — diffs are dark-mode CSS
   additions only, explicitly commented "wave-2 theme-attr sweep" (a
   different concurrent sibling agent's uncommitted work).
2. `test_primitive_css_centering.py::TestEveryReferencedClassHasCSS` —
   missing CSS rule for `scriba-plane-label-text`; class lives entirely in
   `plane2d.py` (never touched by this sweep).
3. `tests/golden/smart_label/test_corpus.py` (`ok-simple`, `bug-B`,
   `critical-2-null-byte`) — diffs are a `class="scriba-annot-label-text"`
   addition to `<text>` elements; the class is emitted from
   `_svg_helpers.py:1706,1781` (not `_text_render.py`) and consumed by
   `[data-theme="dark"] .scriba-annot-label-text` rules in
   `scriba-scene-primitives.css:979,988` — same dark-mode theme-sweep
   category as (1), independently confirmed via the CSS grep.

### Scope compliance

Touched: `scriba/animation/primitives/_text_render.py` (label math-split
region only), `docs/primitives/graph-stable-layout.md`,
`scriba/animation/errors.py` (two band-header comments only), and three new
test files (`tests/unit/test_interp_reverse_risk_shield.py`,
`tests/unit/test_non_interp_positions_inert.py` — Item 4 — plus no changes
to existing test files). No `tex/renderer.py`, `_grammar_values.py`, or
`_svg_helpers.py` edits. No golden re-bless, no version bump, no CHANGELOG
edit, no commit.
