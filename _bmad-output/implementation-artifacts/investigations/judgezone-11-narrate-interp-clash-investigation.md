# Investigation: JudgeZone #11 — `${...}` interpolation shield clashes with math brace-groups in `\narrate`/`\invariant`

## Hand-off Brief

1. **Verdict: CONFIRMED**, and the root cause is more precise than the original report guessed. The bug does **not** live in the lexer (`scriba/animation/parser/lexer.py`) — for `\narrate`/`\invariant` bodies the lexer's `${`-tokenization is produced but never consulted (these fields re-slice raw source text, bypassing the token stream). The actual corruption is in the renderer: `scriba/tex/renderer.py:433-437`, a shield regex (`r"\$\{[^}]*\}"`) that unconditionally treats *any* `${...}` span as leftover interpolation syntax and stashes it — but the stash consumes only **one** dollar sign (the `${` opener), not the two a real `$...$` math span would need. That leaves an odd number of dollar signs in the remainder of the line, and every subsequent `$...$` pairing after it shifts by one position.
2. Silent-echo path (the *documented, correct* behavior being exploited, not itself the bug): `scriba/animation/scene.py:816` `_interpolate_narration`. It is content-shape-blind (matches any `${...}`, not just identifiers) but is parity-neutral — on a lookup miss it returns `m.group(0)` unchanged, byte for byte, so it never corrupts anything itself. The corruption is 100% downstream, in the renderer's shield.
3. Blast surface is **narrower** than "every text field" — of the six candidate positions checked, only `\narrate{}` and `\invariant{}` reproduce this exact corruption (both empirically confirmed by rendering). Selector indices are protected by a pre-existing strict identifier grammar. `\step[title=]` and the animation `label="..."` id are not interpolation positions at all (plain HTML-escape only). Structured `value=${...}` positions have a *related* but *different* bug (silent wrong-value substitution, not KaTeX corruption). Shape/annotation `label=` and `\note{...}{text=...}` route through a completely separate math pipeline (`_text_render.py`) that has no shield at all, so they don't reproduce this corruption pattern — see Blast Surface Table below for the full breakdown with evidence.

## Case Info

| Field | Value |
|---|---|
| JudgeZone ID | #11 |
| Severity (reported) | HIGH, silent |
| Component | `scriba/tex/renderer.py` (actual locus); `scriba/animation/parser/lexer.py` (reported locus, ruled out for this field class) |
| Repo version | 0.34.0, commit `13eadc7` |
| Verdict | **CONFIRMED** (root cause relocated: renderer shield, not lexer) |
| Investigation date | 2026-07-10 |
| Task scope | READ-ONLY on repo source; only permitted repo write is this file |

## Problem Statement

The reporter's claim: `${` inside `\narrate{}` (and similarly `\invariant{}`) text is unconditionally treated as the interpolation opener, even when the braced content is math (e.g. `${5 \choose 3}$`) rather than a `\compute`-bound name reference. The claimed effects: silent failure with no E-code, and an off-by-one cascade that mis-pairs every subsequent `$...$` in the line — Vietnamese prose lands inside KaTeX, `\texttt` content pops out as plain text, and a stray `$` is left dangling at the end.

Repro:
```latex
\begin{animation}[id="t", label="x"]
\shape{a}{Array}{values=[10,20]}
\step[title="one"]
\narrate{Cho ${5 \choose 3}$ đọc ba ô: $\texttt{x}[b]$ và $\texttt{y}[c]$ ở đây. Là $a-b=2$, không phải $b$.}
\end{animation}
```

This line has 5 authored `$...$` math spans (10 dollar signs total): `${5 \choose 3}$`, `$\texttt{x}[b]$`, `$\texttt{y}[c]$`, `$a-b=2$`, `$b$`. The first one is written with `${` immediately after the opening `$` purely because `5 \choose 3` happens to start right after a brace-worthy group — coincidental, not an attempt to use interpolation syntax.

## Documented Interpolation Grammar vs. What The Code Enforces

`docs/SCRIBA-TEX-REFERENCE.md` §13.2 (lines 2102-2139) enumerates the **only** five positions where `${...}` interpolation resolves: `\foreach` bodies, `\apply` values, selector indices, `\narrate` text, and `\invariant` panels. Title, label, and note text are explicitly **not** on that list. The same section states the silent-echo behavior for narrate/invariant is deliberate: "neither errors on an unknown name."

§13.4 (lines 2144-2151) goes further and states an explicit guarantee that this bug violates verbatim: "`${name}` interpolation... never clashes with math: a `${...}` run is shielded before math parsing, so an unresolved `${name}` sitting next to a stray `$` stays literal instead of being paired into `$...$`." This elevates the bug from an undocumented edge case to a **contract violation** — the shield exists specifically to prevent this class of corruption, and it fails to do so when the shielded span was never a name reference to begin with.

Critically, the codebase already has, in a different position, exactly the disambiguation rule the reporter proposes. `scriba/animation/parser/selectors.py:254-264` (`_parse_interpolation`) parses `${...}` content for selector-index positions with a **strict** grammar: `$`, `{`, `_expect_ident()` (an identifier check at line 317-330, using `[^\W\d]\w*`, Unicode-aware), zero-or-more `[index_expr]` subscripts, `}`. Any non-identifier content raises `E1010` at parse time. So "treat `${` as interpolation only when it wraps an identifier(+subscript/index) form" is not a novel rule being proposed — it is the codebase's own existing precedent for one position, just not applied at the render-time shield that guards narrate/invariant text.

## Evidence Inventory

| Evidence | Location | What it shows |
|---|---|---|
| Shield regex | `scriba/tex/renderer.py:433-437` | `r"\$\{[^}]*\}"`, content-shape-blind, matches any `${...}` |
| Narration interpolation resolver | `scriba/animation/scene.py:816-848` | Content-shape-blind but parity-neutral; echoes unchanged on miss |
| Lexer interpolation extractor | `scriba/animation/parser/lexer.py:347-377` | Nested-brace-aware, content-shape-blind, only errors on unclosed brace (E1001) |
| Selector-index strict grammar | `scriba/animation/parser/selectors.py:254-330` | Existing identifier-only precedent, fail-loud E1010/E1159 |
| Repro render | `jz11_repro.tex` → `jz11_repro.html` (scratchpad) | 4 math spans (not 5), Vietnamese content, raw echo, stray trailing `$.` |
| Invariant render | `jz11_invariant.tex` → `jz11_invariant.html` (scratchpad) | Identical corruption signature to narrate |
| Control render | `jz11_control.tex` → `jz11_control.html` (scratchpad) | 5 clean math spans when `\binom{5}{3}` used instead of `${5 \choose 3}` |
| Faithful pipeline simulation | ad hoc script, scratchpad | Reproduces the exact 4-span/9-dollar-remainder result using the verbatim shield/display/inline regex sequence from `_render_cell` |
| Disambiguation simulation | ad hoc script, scratchpad | Identifier-shape gate on the shield restores 5 clean spans with zero special-casing |
| Regression baseline test | `tests/unit/test_reannotate_apply_compute.py:366-388` | Pins silent-echo-on-miss AND successful bound substitution as the required contract |
| Doc contract | `docs/SCRIBA-TEX-REFERENCE.md:2102-2151` | §13.2 defines the 5 valid interpolation positions; §13.4 states the "never clashes with math" guarantee this bug breaks |

## Confirmed Findings

1. **The shield consumes an asymmetric number of dollar signs.** `r"\$\{[^}]*\}"` matches from a `$` through the *first* unbalanced `}` that follows — i.e., exactly the `${...}` span itself. In `${5 \choose 3}$`, this matches `${5 \choose 3}` only (one dollar, the `${` opener), and leaves the second `$` — the one the author intended to *close* that math span — sitting in the text, undigested. A real `$...$` pair is two dollars; the shield only ever removes one dollar per match. Verified by direct simulation of the exact regex against the repro string: shield matches `['${5 \\choose 3}']`, and the post-shield remainder still contains 9 literal `$` characters (an odd count) out of the original 10.

2. **That single leftover dollar cascades every subsequent pairing.** The next regex pass, `r"\$([^\$]+?)\$"` (renderer.py:439), pairs dollars strictly left-to-right and non-nested. Fed 9 dollars instead of an even 8 or clean 10, it pairs: (leftover-closer, opener-of-texttt-x) → captures `" đọc ba ô: "`; (closer-of-texttt-x, opener-of-texttt-y) → captures `" và "`; (closer-of-texttt-y, opener-of-a-b) → captures `" ở đây. Là "`; (closer-of-a-b, opener-of-b) → captures `", không phải "`. The final dollar (meant to close `$b$`) is now odd-one-out and survives as a **literal, unpaired `$`** immediately before the trailing period. `\texttt{x}[b]`, `\texttt{y}[c]`, `a-b=2`, and the final `b` are never captured by any math pair at all — they fall in the gaps *between* pairs, so they're left as plain text (subsequently passed through `apply_text_commands`, which turns the `\texttt{...}` runs into `<code>` elements outside of any math span).

3. **Simulation and real rendering agree exactly.** A faithful replay of `_render_cell`'s three regex passes (shield → display-math → inline-math), using the same non-dollar stash sentinel format the real code uses (`\x00CELL{n}\x00`), produces stashed placeholders with content `" đọc ba ô: "`, `" và "`, `" ở đây. Là "`, `", không phải "` — and a final literal string ending in `...b$.`. Inspecting the actual previously-rendered `jz11_repro.html` (scratchpad) confirms this structurally: 4 math spans (not the 5 authored), with annotation content `đọc ba ô:`, `và`, `ở đây. Là`, `, không phải`; the leading text run contains the raw, un-resolved echo `${5 \choose 3}` verbatim; the trailing text run ends in `...b$.` — a literal stray dollar sign survives into the final HTML.

4. **`\invariant{}` reproduces the identical corruption.** Rendering the same pattern inside `\invariant{...}` (scratchpad `jz11_invariant.tex` → `jz11_invariant.html`) produces the exact same structural signature: 4 math spans with the same Vietnamese content, the same raw echo of `${5 \choose 3}`, and the same trailing `...b$.`. This is expected from the code: both `\narrate` and `\invariant` route through `_interpolate_narration` (`scene.py:410` and `:415` respectively) and then `ctx.render_inline_tex` → `_render_cell` (`scriba/animation/renderer.py:227` for narration, `:247` for invariant) — same resolver, same shield, same bug.

5. **The control confirms the shield, not the KaTeX renderer, is at fault.** Swapping `${5 \choose 3}$` for the equivalent `$\binom{5}{3}$` (scratchpad `jz11_control.tex` → `jz11_control.html`) — same 10-dollar-sign structure, same intended 5 math spans, but no `${` substring anywhere — renders cleanly: exactly 5 math spans, correctly bounded, with clean Vietnamese text runs between them (` đọc ba ô: `, ` và `, ` ở đây. Là `, `, không phải `, `.`). The only variable that changed is whether a `${` substring exists in the source; the corruption is entirely attributable to the shield's match.

6. **`_interpolate_narration` (the reported "silent echo" site) is not itself the bug.** Its regex (`scene.py:848`, `r"\$\{([^}]+)\}"`) is also content-shape-blind — it will attempt a dict lookup on `"5 \choose 3"` as a binding name, fail, and return `m.group(0)` unchanged (per its own docstring, `scene.py:822-824`: "An unknown name is left untouched... which also leaves any non-binding `${...}` text intact"). This is parity-neutral: it does not remove or alter any dollar signs when it doesn't resolve. The text reaches `_render_cell` byte-for-byte unchanged from this pass. The actual corruption is isolated entirely to the renderer's shield regex.

7. **The reporter's proposed fix rule is correct; the reporter's proposed fix location is not, for this field class.** Gating the shield to only fire when the `${...}` content is identifier(+subscript/index)-shaped — the same grammar `selectors.py::_expect_ident` already enforces — was simulated directly against the repro: with the gate applied, the shield does not match `${5 \choose 3}` at all (it contains whitespace and a backslash), so the span falls through untouched to the normal inline-math regex, which then pairs `${5 \choose 3}$` as one clean math span with content `{5 \choose 3}` — valid TeX for a binomial coefficient, rendered correctly with zero special-casing. All 5 spans come out clean, matching the control's structure exactly. The same gate correctly still shields every genuine interpolation form tested: `${a}`, `${a_1}`, `${arr[i]}`, `${total}`, `${arr.length}` all pass the identifier-shape test and remain shielded as before.

## Blast Surface Table

| Field | Interpolation active today? | Shares `_render_cell` shield? | Failure mode on math-shaped `${...}` | Evidence |
|---|---|---|---|---|
| `\narrate{...}` | Yes (`_interpolate_narration`) | Yes | **CONFIRMED** — off-by-one KaTeX corruption | `jz11_repro.html`, this doc §Confirmed Findings 1-3 |
| `\invariant{...}` | Yes (`_interpolate_narration`) | Yes | **CONFIRMED** — identical corruption | `jz11_invariant.html`, Finding 4 |
| Selector index, e.g. `a.cell[${i}]` | Yes (`selectors.py::_parse_interpolation`) | No — never reaches `_render_cell`; it's a parse-time index expression, not prose | Not reproducible — strict identifier grammar rejects non-identifier content at parse time with `E1010`; math text isn't grammatically valid here at all | `selectors.py:254-330` |
| `\apply` values / `\foreach` bodies / structured `value=${...}` | Yes (`_grammar_values.py::_parse_interp_ref` → `scene.py::_resolve_interp`) | No — resolved as a typed param value, never passed through the prose math pipeline | **Different bug, same root cause**: `_parse_interp_ref` (lines 59-77) does naive `"[" in content` string slicing with no identifier validation, so non-identifier content silently becomes a fallback literal-string *value* via `.get(name, name)` (scene.py:850-860) instead of a KaTeX render corruption. Flagged as a related-but-distinct finding, not this bug's blast radius. | `scriba/animation/parser/_grammar_values.py:59-77`, `scene.py:850-860` |
| `\step[title="..."]` | **No** — not a documented interpolation position | N/A | Not reproducible — title is emitted via plain `html.escape()`, never touches interpolation lookup or math pairing | `scriba/animation/renderer.py:570` |
| Animation `label="x"` (anchor id) | **No** | N/A | Not reproducible — used only for ARIA/data attributes via a plain escaper, gated as an id-safe identifier | `scriba/animation/_html_stitcher.py` (label/anchor handling) |
| Shape/cell/annotation `label=` (display text) | Not via `${...}` interpolation resolution — but can independently contain `$math$` | No — routes through `_text_render.py`'s `_render_mixed_html`/`_label_has_math`, a *separate* pipeline with **no shield at all** | Not reproducible as *this* corruption — with no shield present, `${5 \choose 3}$` would pair directly and correctly as 2 clean dollars. (Separate, out-of-scope latent risk: a genuinely unresolved `${name}` sitting next to real math *could* get swept into a math pair here, the mirror-image problem — not investigated further, flagged as a side finding) | `scriba/animation/primitives/_text_render.py:152-184`, callers in `_svg_helpers.py`, `base.py`, `equation.py` |
| `\note{...}{text=...}` | Same as shape/annotation label — no `${...}` resolution step, but can contain `$math$` | No — confirmed to route through the same `_label_has_math`/`_render_mixed_html` SVG pipeline as labels | Not reproducible as this corruption, same reasoning as the label row above | `scriba/animation/_frame_renderer.py:1525-1534` (`has_math = ... and _label_has_math(text)`) |

Net: **2 of 8 candidate positions** (`\narrate`, `\invariant`) reproduce the reported corruption. Selector indices are protected by existing strict grammar. Title/anchor-label are not interpolation positions. Structured values have a related but functionally different bug. Display labels/notes use an entirely separate, shield-less pipeline that doesn't exhibit this failure mode (though it has its own unrelated, unquantified risk in the opposite direction).

## Source Code Trace

Pipeline for the repro line, in execution order:

1. **Parse time** — `grammar.py:88` tokenizes the whole source once. `lexer.py:212-222` fires on `${5` (the `$` immediately followed by `{`), calls `_extract_interpolation` (`lexer.py:347-377`, nested-brace-aware, stops at the first balanced `}`), and emits an `INTERP` token with content `"5 \choose 3"`. This token is produced but **irrelevant**: `_parse_narrate`/`_parse_invariant` (`_grammar_commands.py`) use `_read_raw_brace_arg`, which re-slices the *raw source string* directly rather than consuting the token stream, so the narrate body text reaching later stages is the untouched original characters, including the literal `${5 \choose 3}$...` substring.

2. **Narration resolution** — `scene.py:410`/`:415` call `_interpolate_narration` (`scene.py:816-848`) on the raw body. Its regex `r"\$\{([^}]+)\}"` matches `${5 \choose 3}`, captures `"5 \choose 3"`, attempts `self.bindings["5 \choose 3"]` (via the `name not in self.bindings` guard at line 832), misses, and returns `m.group(0)` unchanged (line 833/846 fallback path). Output byte-identical to input for this span.

3. **TeX rendering** — `scriba/animation/renderer.py:227` (narration) / `:247` (invariant) call `ctx.render_inline_tex(text)`, which delegates to `_render_cell` (`renderer.py:389-470`).
   - Step 0 (line 404-405): no literal `\$` present, no-op.
   - Step 1a, the shield (line 433-437): `re.sub(r"\$\{[^}]*\}", ...)` matches **only** `${5 \choose 3}` — one dollar sign consumed (the `${` opener) plus the brace content, stashed as placeholder `\x00CELL0\x00`. The dollar sign immediately following (originally intended to close this math span) is **not** part of the match and survives in the text.
   - Step 1b, display math (line 438): `r"\$\$([\s\S]*?)\$\$"` finds no `$$`, no-op.
   - Step 1c, inline math (line 439): `r"\$([^\$]+?)\$"` now scans the remaining 9 dollar signs left-to-right, non-nested, producing 4 pairs with captured content `" đọc ba ô: "`, `" và "`, `" ở đây. Là "`, `", không phải "` (stashed as `\x00CELL1\x00`-`\x00CELL4\x00`), leaving `\texttt{x}[b]`, `\texttt{y}[c]`, `a-b=2`, and `b` as literal text between placeholders, and one final unpaired `$` before the trailing `.`.
   - Steps 2-5: HTML-escape and text-command passes run on this already-corrupted text; `apply_text_commands` (line 459) turns the surviving `\texttt{...}` runs into `<code>` elements, now sitting outside any math span.
   - Steps 6-7: placeholders restored; the four stashed spans (containing Vietnamese prose, not math) are re-inserted as KaTeX-rendered HTML.

4. **Empirical confirmation** — `jz11_repro.html`'s narration fragment: 4 `scriba-tex-math-inline` spans with annotation content `đọc ba ô:` / `và` / `ở đây. Là` / `, không phải`; surrounding text runs contain the raw echoed `${5 \choose 3}` and a trailing `...b$.`. Matches the simulated trace exactly.

## Reproduction Plan

```bash
cd /Users/mrchuongdan/Documents/GitHub/scriba
SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py <path-to-repro.tex> -o <path-to-repro.html>
```

Repro source (5 authored `$...$` spans, first one coincidentally starting with `${`):
```latex
\begin{animation}[id="t", label="x"]
\shape{a}{Array}{values=[10,20]}
\step[title="one"]
\narrate{Cho ${5 \choose 3}$ đọc ba ô: $\texttt{x}[b]$ và $\texttt{y}[c]$ ở đây. Là $a-b=2$, không phải $b$.}
\end{animation}
```
Expect (buggy, current behavior): 4 KaTeX spans in the rendered narration, containing Vietnamese prose fragments as their math content; `\texttt{x}[b]`/`\texttt{y}[c]` rendered as plain `<code>` outside any math span; `a-b=2` as bare unrendered plain text; a literal stray `$` before the final period; the string `${5 \choose 3}` echoed raw near the start.

Control (swap the coincidental `${` for an equivalent that doesn't start with `${`):
```latex
\narrate{Cho $\binom{5}{3}$ đọc ba ô: $\texttt{x}[b]$ và $\texttt{y}[c]$ ở đây. Là $a-b=2$, không phải $b$.}
```
Expect (confirmed clean): exactly 5 KaTeX spans matching the 5 authored `$...$` pairs, correct content in each, clean Vietnamese text runs between them.

`\invariant{...}` with the same buggy body reproduces the identical signature (already rendered and confirmed in this investigation).

## Regression Risk Notes

Any fix **must** preserve:

1. **Silent echo of genuinely unbound, identifier-shaped names.** `tests/unit/test_reannotate_apply_compute.py:366-373` (`test_narration_unknown_name_stays_literal`) asserts `"Price is ${total} dollars."` stays completely literal with no error when `total` is unbound. `${total}` is identifier-shaped, so it must still be shielded/attempted and, on miss, echoed unchanged — this test is unaffected by an identifier-shape gate on the shield, since `${total}` passes the identifier test.
2. **Successful substitution of bound identifier-shaped names.** `tests/unit/test_reannotate_apply_compute.py:375-388` (`test_narration_mixes_bound_and_unbound`) proves `${x}` resolves to `42` when bound via `\compute{x = 42}`, while `${missing}` stays literal in the same string: `"Answer ${x}, but ${missing} stays."` → `"Answer 42, but ${missing} stays."` This exercises the resolution layer (`_interpolate_narration`) upstream of the renderer shield and is unaffected by a shield-level fix, since that fix only changes what the *renderer* additionally shields after resolution has already run — a bound name is already substituted away to a literal number by the time the shield would ever see it.
3. **`${name[idx]}` subscript forms**, e.g. `${arr[i]}`, `${dp_vals[i]}` — must remain identifier-shaped-with-subscript per the existing `selectors.py::_parse_interpolation` grammar; the proposed gate (verified in Confirmed Finding 7) already accepts `${arr[i]}` as identifier-shaped.
4. **The documented §13.4 guarantee itself** ("`${name}` interpolation never clashes with math") is what a shield-level fix restores, rather than weakens — the current implementation is the one violating it.

The fix must **not** introduce a hard error (E-code) for narrate/invariant on an unresolved, non-identifier `${...}`, because that would contradict the documented behavior in §13.2 ("neither errors on an unknown name") and break both tests above outright.

## Recommended Fix Sketch

Primary fix — gate the shield in `scriba/tex/renderer.py:433-437` to only match identifier(+subscript/index)-shaped content, reusing the grammar already codified in `selectors.py::_expect_ident` (`[^\W\d]\w*` for the identifier, then zero-or-more `[index]` or `.attr` tails):

```python
_INTERP_SHAPE_RE = re.compile(r"^\{[^\W\d]\w*(?:\[[^\]]*\]|\.[^\W\d]\w*)*\}$")

def _shield_sub(m: re.Match[str]) -> str:
    if not _INTERP_SHAPE_RE.match(m.group(0)[1:]):
        return m.group(0)  # not identifier-shaped -> let it fall through to math pairing
    return _stash(_html.escape(m.group(0), quote=False))

text = re.sub(r"\$\{[^}]*\}", _shield_sub, raw)
```

This was verified directly against the repro (Confirmed Finding 7): the shield no longer matches `${5 \choose 3}`, which then falls through cleanly to the existing, unmodified inline-math regex and pairs correctly as 1 of 5 clean spans — restoring exact parity with the control. Every existing genuine interpolation form (`${a}`, `${a_1}`, `${arr[i]}`, `${total}`, `${arr.length}`) still gates as identifier-shaped and remains shielded exactly as before, so `_interpolate_narration`'s upstream resolution and the two regression tests are untouched.

No new E-code is required for this primary fix — the point of the fix is that math-shaped `${...}` should need no special handling at all, just normal math rendering.

Optional, secondary, non-blocking: reserve `E1160` (first free slot in the interpolation-themed band adjacent to `E1159` in `scriba/animation/errors.py`/`docs/spec/error-codes.md`) for a future *non-fatal* diagnostic (e.g., a lint-level hint, not a render-blocking error) if a `${...}`-shaped-but-non-identifier span is detected — explicitly must not fire for identifier-shaped-but-unbound names, to avoid contradicting §13.2 and the two tests above. This is a nice-to-have, not required to close this bug.

Related, out-of-scope-for-this-fix locus worth a follow-up ticket: `scriba/animation/parser/_grammar_values.py:59-77` (`_parse_interp_ref`) has the same unvalidated-content-shape root cause for structured `value=${...}` positions, but manifests as a silent wrong-value fallback rather than KaTeX corruption (see Blast Surface Table). Applying the same identifier-shape validation there (ideally fail-loud, since structured values are not documented to tolerate arbitrary literal fallback) would close that related gap but is a separate change with its own regression surface.

## Affected Tests

- `tests/unit/test_reannotate_apply_compute.py:366-373` — `test_narration_unknown_name_stays_literal` — must continue passing unmodified.
- `tests/unit/test_reannotate_apply_compute.py:375-388` — `test_narration_mixes_bound_and_unbound` — must continue passing unmodified.
- No existing test currently exercises math-shaped `${...}` inside `\narrate`/`\invariant`; a new test fixture based on the repro/control pair in this document (scratchpad `jz11_repro.tex` / `jz11_control.tex`) is recommended to lock in the fix and prevent regression.

## Side Findings

- The two band-header comments in `scriba/animation/errors.py` around the `E11xx` range overlap (`# --- Starlark sandbox errors (E1150 -- E1179) ---` at line 288 and `# --- Foreach errors (E1170 -- E1179) ---` at line 300 both claim part of the same numeric range) — a pre-existing documentation nit, unrelated to this bug, not fixed here per the read-only scope.
- The SVG/foreignObject label pipeline (`scriba/animation/primitives/_text_render.py:152-184`, `_render_mixed_html`/`_label_has_math`, used by shape/cell/annotation `label=` and `\note{...}{text=...}`) has no `${...}` shield at all. It does not reproduce this bug's corruption pattern (confirmed: no shield means `${5 \choose 3}$` would pair as 2 clean dollars directly), but it has an unquantified, un-investigated latent risk in the *opposite* direction — a genuinely unresolved `${name}` sitting adjacent to real math could get swept into a math pair, since there is no interpolation-resolution or shielding step for these fields at all. Worth a separate, dedicated investigation if this is in scope for the broader sweep.
