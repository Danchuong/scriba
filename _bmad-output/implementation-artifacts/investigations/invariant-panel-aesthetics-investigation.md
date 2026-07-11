---
title: 'Invariant panel aesthetics — measured investigation'
type: 'investigation'
created: '2026-07-11'
status: 'confirmed — measured, not vibes'
---

# Invariant Panel Aesthetics Investigation

## Hand-off Brief

A user reported the `\invariant` panel "trông xấu quá" (looks ugly) on a real
document. Mandate: characterize precisely what is visually wrong — measured
facts, not vibes — and trace the emission pipeline so a design fix can be
grounded. Read-only on repo source; this file is the only repo write.

## Case Info

| Field | Value |
|---|---|
| Reported symptom | `\invariant` panel "looks ugly" (Vietnamese user report) |
| Repo / version | `scriba`, `0.35.0` (`scriba/_version.py`), branch `main` |
| Repro doc | `/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/b6b798d6-92ae-4dfa-9982-9f3f2f1a33de/scratchpad/invariant-ugly/removal-game.tex` (real Vietnamese editorial content, DP recurrence) |
| Rendered output | same dir, `removal-game.html` (`SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py removal-game.tex -o removal-game.html`; confirmed "Rendered 1 block(s) + 1 TeX region(s)") |
| Measurement method | Two passes. **(1) Browser pass, completed first:** real headless-Chromium DOM measurement (Playwright `sync_api`, `p.chromium.launch(executable_path="/opt/homebrew/bin/chromium")`) — the project's Playwright MCP bridge was unavailable (CDP session timed out / "Extension disconnected"), so a direct Python `playwright` script was used instead. This predates the later repo-wide Playwright/browser-MCP ban for subagents (`848caf3`) and a follow-up explicit no-Playwright directive to this investigation; all screenshots and pixel numbers below are real renders, not estimates — none were skipped. **(2) Static pass, added after the no-Playwright directive:** zero further browser calls were made; instead the repo's own validated math-width oracle (`measure_inline_math`, `scriba/animation/primitives/_math_metrics.py:461`) was invoked directly in Python to independently corroborate the two formulas' widths with no browser involved — see "Static Corroboration" below. |
| Evidence sources | Rendered HTML/CSS, `scriba-embed.css`, `scriba-scene-primitives.css`, `scriba.js`, Python pipeline (`parser` → `scene` → `renderer` → `tex/renderer` → `_html_stitcher`), `docs/SCRIBA-TEX-REFERENCE.md` §5.17/§13.2, `docs/spec/environments.md` §3.17, 8 screenshots, `measurements.json` |
| Related artifact found in-repo | `_bmad-output/implementation-artifacts/design-invariant-panel-restyle.md` (untracked, dated same day) — a design-options doc for this same panel, written independently. See **Cross-Check** section below; one material factual correction is offered against it. |

## Problem Statement

The repro's `\invariant` line joins two independent formulas with a literal
`; ` inside **one** brace body:

```latex
\invariant{$\mathrm{score}(l,r)=\max\bigl(x_l-\mathrm{score}(l{+}1,r),\ x_r-\mathrm{score}(l,r{-}1)\bigr)$; $\mathrm{score}(l,l)=x_l$}
```

At normal desktop widths this renders as one long inline-math line with a
faint blue left rule. At mobile width (375px, a supported/expected container
size) the line wraps — and it wraps **inside** a matched `\bigl(...\bigr)`
delimiter pair, splitting one KaTeX-rendered formula across two lines. That
is the single most concretely "broken-looking" defect found; four more
contributing factors are ranked below it, all with pixel-level evidence.

## Emission Pipeline Trace

Ordered by data flow, `\invariant{text}` → rendered `<p>`:

| Stage | Locus | What happens |
|---|---|---|
| 1. Parse | `scriba/animation/parser/_grammar_commands.py:186-189` (`_parse_invariant`) | Raw brace-body parse, **byte-identical mechanism to `\narrate`** — no `;`-splitting exists anywhere in the grammar. Produces `InvariantCommand` (`scriba/animation/parser/ast.py:214`). |
| 2. Prelude-only guard | `scriba/animation/parser/grammar.py:228,313`; `scriba/animation/parser/_grammar_substory.py:378` | Raises **E1058** if `\invariant` appears after the first `\step` (registry entry: `scriba/animation/errors.py:174`). |
| 3. Scene state | `scriba/animation/scene.py:301-303` (`SceneState.invariants: tuple[str, ...] = ()`, raw prelude bodies) | Collected once, unparsed beyond the raw string. |
| 4. Per-frame resolution | `scriba/animation/scene.py:411-415` | `self._interpolate_narration(body) or "" for body in self.invariants` — **same `${}` resolution machinery as `\narrate`**, run fresh per frame. Result stored on `FrameSnapshot.invariants` (`scene.py:273-277`) and threaded through frame construction (`scene.py:467`). |
| 5. KaTeX render | `scriba/animation/renderer.py:238-252` (`_render_invariant`) | Calls `ctx.render_inline_tex(text)`, then `apply_text_commands`. Live path: `renderer.py:574-581` (gated by `render_invariants`, `:403`), one `_render_invariant` pass per frame. Static path: `renderer.py:785-799`, rendered once. Live-vs-static decision: `renderer.py:907-908`, `invariants_live = any("${" in t for t in getattr(ir, "invariants", ()))`. |
| 6. Inline vs. display KaTeX | `scriba/tex/renderer.py:470,476` dispatch on delimiter; `:530-557` (`_render_inline`, **`"displayMode": False"` hardcoded at `:538`**, wraps output in `<span class="scriba-tex-math-inline">`); `:559-579` (`_render_display`, `displayMode: True`, unused by this repro since it uses single `$...$`, not `$$...$$`). |
| 7. Frame payload | `scriba/animation/emitter.py:127-130` | `invariants_html: list[str] \| None = None` — `None` sentinel (not `[]`) distinguishes "no invariant at all" from "invariant present, empty body," preserving the byte-identical-when-absent contract downstream. |
| 8. HTML — single source of markup | `scriba/animation/_html_stitcher.py:107-122` (`_invariant_panel_elements`) | The **only** place `<p class="scriba-invariant" role="note">{html}</p>` is built. Returns `[]` for empty/`None` input so a document without `\invariant` stays byte-identical (docstring, `:108-114`). |
| 9. HTML — 3 emission sites, same source | Static filmstrip: `_html_stitcher.py:260-274`. Interactive per-frame JS payload: `:514-570`, `:619-629` (`inv_escaped`, `_raw_frame["inv"]`). Widget-level static panel: `:705-739` (direct DOM sibling, immediately after `<p class="scriba-narration">`, before `.scriba-substory-container`). All three call `_invariant_panel_elements()` — **not** three independent markup builders. |
| 10. CSS | `scriba/animation/static/scriba-scene-primitives.css:1113-1124` | Sole visual rule (quoted in full under Finding 4). |
| 11. Client runtime | `scriba/animation/static/scriba.js:31-32,119,461` | `invp = querySelectorAll('.scriba-invariant')`; `_setInv(i)` swaps **pre-rendered** `.innerHTML` per node by **array index** — the browser never re-runs KaTeX; all math rendering happened server-side in step 5-6. |
| 12. Page wrapper | `render.py:31,291` (`HTML_TEMPLATE`) | No width-constraining container around `.scriba-widget`; the widget's own `max-width: 100%` (`scriba-embed.css:35`) is the only horizontal constraint. |

## Measured Geometry

Headless Chromium, `viewport.height=1000`, KaTeX settle wait 150ms,
`document.documentElement.setAttribute('data-theme','dark')` for dark runs.
Full raw data: `.../invariant-ugly/measurements.json`. Script:
`.../invariant-ugly/measure.py`.

| Metric | wide700 / light | wide700 / dark | narrow375 / light | narrow375 / dark |
|---|---|---|---|---|
| Widget content width (`clientWidth`) | 666px | 666px | 341px | 341px |
| Panel rect width | 666px | 666px | 341px | 341px |
| Panel content box (`clientWidth`) | 663px | 663px | 338px | 338px |
| **Panel `offsetHeight`** | **32px** | 32px | **54px (+68.75%)** | 54px |
| Panel font-size | 14.4px (0.9em × 16px root) | 14.4px | 14.4px | 14.4px |
| Panel padding | 5.04px 8.64px (0.35em/0.6em) | same | same | same |
| Panel margin | 7.2px 0 0 (0.5em) | same | same | same |
| Panel border-radius | 0 6px 6px 0 | same | same | same |
| Panel border-left / bg accent | `rgb(11,104,203)` / 7% alpha (`#0b68cb`) | `rgb(112,184,255)` / 7% alpha (`#70b8ff`) | `rgb(11,104,203)` | `rgb(112,184,255)` |
| **Panel text color** | `rgb(17,24,28)` (near-black) | `rgb(236,237,238)` | `rgb(17,24,28)` | `rgb(236,237,238)` |
| Narration font-size | 13.6px (0.85rem) | 13.6px | 13.6px | 13.6px |
| **Narration text color** | `rgb(71,84,103)` (muted) | `rgb(236,237,238)` | `rgb(71,84,103)` | `rgb(236,237,238)` |
| Formula 1 (`mathSpans[0]`) box | 416.92 × **17**px | same | 313.63 × **38.91px** | same |
| Formula 2 (`mathSpans[1]`) box | 108.16 × 17px | same | 108.16 × 17px (unchanged) | same |
| `overflow-x` / `overflow-wrap` / `word-break` (computed) | visible / normal / normal | same | same | same |
| `overflowsWidget` (panel wider than widget) | false | false | false | false |

Key reads from this table:

- **Formula 1 alone is 416.9px wide** — wider than the entire 338px mobile
  panel content box. It cannot fit narrow at any font-size scaling was ever
  applied (none is — 14.4px is identical in all four runs).
- **The panel never overflows/clips** (`overflowsWidget: false` in all four
  runs) — it *wraps*, and the wrap point, not clipping, is the defect.
- Font-size and all box-model values are **theme-invariant**; only color
  tokens change between light/dark. Dark-mode re-theming of the border/tint
  is confirmed working (see Finding 4 and the Cross-Check section).
- Panel text color and narration text color are **equal in dark mode**
  (`rgb(236,237,238)` both) but **different in light mode** (`rgb(17,24,28)`
  vs `rgb(71,84,103)`) — this is coincidental, not designed; see Finding 3.

### Confirmed wrap location (narrow375)

`mathSpans[0]` (formula 1) bounding box grows from a single line
(x=28.625, y=804.03, w=416.92, h=17 at wide700) to a two-line union box at
narrow375 (x=28.625, y=825.09, w=313.63, **h=38.91** — more than 2× the
single-line height, at the *same* 14.4px font-size). `mathSpans[1]` (formula
2) keeps its wide700 dimensions exactly (108.16 × 17) and sits at y=847,
overlapping the tail of formula 1's box — i.e. formula 2 shares the
*second* wrapped line with whatever of formula 1 didn't fit on the first.
Screenshot inspection (`invariant_narrow375_light_panel_only.png`) confirms
the glyph-level break lands between "$x_r-$" and "$\mathrm{score}(l,r{-}1))$"
— inside the second `\bigl(...\bigr)`-delimited subtraction term of the
`\max`, immediately after the minus sign.

### Static corroboration (no-browser, run after the Playwright directive)

Per an explicit team directive received mid-investigation, no further
Playwright/browser-MCP calls were made. The width claim behind Finding 1 is
corroborated below with zero browser involvement, using the repo's own
math-width oracle instead of a fresh render:

```
scriba.animation.primitives._math_metrics.measure_inline_math(frag, font_px)
```

This function is a TeX-atom advance-sum engine fitted against real Chromium
measurements (module comment, `_math_metrics.py:426`: "fitted against
Chromium scrollHeight... `tests/unit/test_math_metrics.py`"), independent of
any browser call at evaluation time. Invoked directly in Python against the
repro's two formula fragments at the panel's own 14.4px font:

| Fragment | `is_linear_math` | Static estimate @14.4px (`measure_inline_math`) | Playwright-measured @14.4px | Delta |
|---|---|---|---|---|
| Formula 1 (`\mathrm{score}(l,r)=\max\bigl(...\bigr)`) | `True` | **440.26px** | 416.92px | +23.3px (+5.6%) |
| Formula 2 (`\mathrm{score}(l,l)=x_l`) | `True` | **110.93px** | 108.16px | +2.8px (+2.6%) |

Both fragments take the Tier-B advance-sum path (not the cruder heuristic
fallback), and both independently confirm the load-bearing conclusion
without any browser: formula 1 (~417-440px) cannot fit inside the ~338px
mobile panel content box under any of the measured/estimated numbers,
while formula 2 (~108-111px) fits comfortably alone. The ~3-6% gap between
static estimate and live measurement is expected — the oracle's own
documented accuracy band ("p50 0.06% / p95 0.66%") applies to its core
advance-sum primitive on plain runs, not to a full fragment carrying a
`\max` operator, subscripts, and scaled `\bigl`/`\bigr` delimiters, which
add harder-to-model italic-correction and delimiter-scaling terms. The
static pass corroborates the earlier measurement; it does not replace it,
and the browser-derived numbers throughout this report (which predate the
no-Playwright directive) remain the numbers cited elsewhere in this
document.

## Confirmed Findings — Ranked Ugliness Factors

### 1. Mid-formula line wrap (highest impact — objectively broken typesetting)

**Evidence:** `measurements.json`, `narrow375_light`/`narrow375_dark`:
panel `offsetHeight` 32px → 54px (+68.75%); `mathSpans[0]` height 17px →
38.91px at a constant 14.4px font-size; break point visually confirmed
between "$x_r-$" and "$\mathrm{score}(l,r{-}1))$" (screenshot
`invariant_narrow375_light_panel_only.png`).

**Detail:** Zero CSS anywhere sets `overflow-wrap`, `word-break`, or a
`.katex`-scoped rule for `.scriba-invariant`
(`scriba-scene-primitives.css`, `scriba-embed.css` — confirmed via grep,
zero matches). Computed `overflow-wrap: normal`, `word-break: normal` in
all four measured runs — pure unconstrained inline flow, so the browser is
free to break at any whitespace inside KaTeX's own generated markup,
including whitespace between glyphs that sit inside a matched delimiter
pair. Notably, this codebase already has a working "overflow at narrow
width → horizontal scroll" pattern in two other places —
`.scriba-progress` (`scriba-embed.css:76-85`, "L4 fix: flex-wrap +
overflow-x: auto so dots wrap or scroll at 320px") and `.scriba-frames`
(`scriba-embed.css:204-213`, `scroll-snap-type: x mandatory`) — neither of
which was extended to `.scriba-invariant` or any KaTeX-bearing element.

### 2. Semicolon-joined two-formula run-on (present even without wrapping)

**Evidence:** `removal-game.tex:6` — one `\invariant{}` brace body holds two
independent facts joined by a hand-typed `; `. At wide700 (no wrap), the
rendered line reads `…score(l,r−1))); score(l,l)=xl` with only an ~8px
visual gap (`mathSpans[1].x − (mathSpans[0].x + mathSpans[0].width)` =
`453.52 − (28.625+416.92)` ≈ 7.97px) marking the boundary between two
unrelated statements.

**Detail:** `_parse_invariant` (`_grammar_commands.py:186-189`) treats the
whole brace body as one opaque raw string — there is no `;`-splitting
anywhere in the grammar, so this run-on is entirely an authoring artifact,
not a parser limitation. `docs/SCRIBA-TEX-REFERENCE.md:829` documents
"Multiple `\invariant` lines stack," implying the intended pattern is two
separate `\invariant{}` calls (→ two separately-rendered `<p>` panels), not
one joined string. However, splitting the repro this way would **not**
fully resolve Finding 1: formula 1 alone measures 416.9px, still wider than
the 338px mobile panel content box, so it would still wrap internally as
its own single-formula panel. *(This specific claim — that a split-doc
would still wrap — is an arithmetic inference from the measured widths,
not independently re-rendered/re-measured.)*

### 3. Font-size and color hierarchy inversion

**Evidence:** Panel font-size 14.4px (`0.9em` × inherited 16px widget-root
— `scriba-scene-primitives.css:1122`) vs. narration font-size 13.6px
(`0.85rem` — `scriba-embed.css:186`): the panel's supporting text renders
**5.88% larger** than the primary narration paragraph it sits below. In
light mode this compounds with color weight: `.scriba-invariant` sets no
`color` property at all (`scriba-scene-primitives.css:1116-1124`), so it
inherits the ambient default, which resolves to `--scriba-fg: #11181c`
(`scriba-scene-primitives.css:39`) — a near-black, high-emphasis token —
while `.scriba-narration` **explicitly** sets the softer `color: #475467`
(`scriba-embed.css:188`). Measured: panel text `rgb(17,24,28)` vs.
narration text `rgb(71,84,103)` in light mode.

**Detail:** In dark mode the two colors happen to coincide
(`rgb(236,237,238)` both — panel inherits `--scriba-fg: #ecedee` at
`scriba-scene-primitives.css:750`; narration's explicit dark override at
`scriba-embed.css:255,271` independently also uses `#ecedee`). This is
**coincidental parity, not a shared rule** — two independently-chosen
values that happen to match in dark but diverge in light. Net effect: a
secondary/supporting-fact panel reads larger, and in light mode also
darker/heavier, than the primary narration it is meant to support —
independently confirmed by `design-invariant-panel-restyle.md` §3.2 via
static CSS reading (not live measurement); this report's contribution is
the measured pixel/color proof plus the light/dark asymmetry.

### 4. Weak, flat panel chrome

**Evidence:** Panel left edge `x=17` is pixel-identical to narration's left
edge (`x=17`) — no inset/indent treatment distinguishing it as its own
block. Background tint is `color-mix(in srgb, var(--scriba-annotation-info)
7%, transparent)` (`scriba-scene-primitives.css:1120`) — 7% alpha, measured
as `color(srgb 0.043 0.408 0.796 / 0.07)` in light. Vertical padding
5.04px/8.64px (0.35em/0.6em) is tighter than narration's 8px/16px/12px
(`scriba-embed.css:184-186`).

**Detail:** Dark-mode re-theming of the border/background **does work
correctly** — confirmed by direct measurement, not just markup-reading:
`border-inline-start` swaps `rgb(11,104,203)` → `rgb(112,184,255)` and the
background tint swaps its base color to match, both riding the
`--scriba-annotation-info` custom property, which **is** redefined for dark
at `scriba-scene-primitives.css:799` (`[data-theme="dark"]`) and `:858`
(`@media (prefers-color-scheme: dark)`). See the Cross-Check section — this
directly corrects a claim in the sibling design doc. The combined effect of
identical left-edge alignment + low-alpha tint + tight padding is that the
panel reads as a "highlighted paragraph continuation" of the narration
above it rather than a distinct, stable piece of UI chrome — a real but
comparatively minor defect next to Findings 1-3.

### 5. Unused horizontal space at desktop width (minor — opportunity, not defect)

**Evidence:** At wide700, formula content spans from `x=28.625` to
`x=561.67` (≈533px used) inside a ≈645.7px content box (663px `clientWidth`
− 2×8.64px padding) — roughly **113px (17%) of trailing horizontal space**
goes unused to the right of formula 2, with no alternate layout (columns,
math/prose split) making use of it.

**Detail:** Weakest and most "matter of opinion" of the five — flagged for
completeness since the brief specifically asked about space distribution,
not because it independently reads as "ugly."

## Side Findings

- **Accessibility: no `aria-live` on a live-updating panel.** `.scriba-narration`
  gets `aria-live="polite" aria-atomic="true"` (`_html_stitcher.py:421,739`);
  `.scriba-invariant` gets only `role="note"` (`_html_stitcher.py:119,718` —
  identical string in both emission sites, confirming it's the single-source
  function, not a per-site inconsistency). Per `scene.py:411-415`, a live
  (`${}`-interpolating) invariant's text changes every frame exactly like
  narration's does, but only narration announces that change to assistive
  tech. Not a "looks ugly" factor, but a real, precisely-located gap adjacent
  to the ones above. Independently confirmed by `design-invariant-panel-restyle.md`
  §3.7, same file:line.
- **No "this is an invariant" signifier.** The panel carries no caption, icon,
  or label distinguishing it from any other left-ruled note — a valid point
  raised in `design-invariant-panel-restyle.md` §3.1 that this investigation
  did not independently derive (no pixel measurement would surface a missing
  *feature*, only a missing rule), but is corroborated by the pipeline trace:
  `_invariant_panel_elements` (`_html_stitcher.py:107-122`) emits body text
  only, no label wrapper.
- **`border-radius` fallback is dead in practice.** The rule reads
  `var(--scriba-frame-radius, 4px)`, but `--scriba-frame-radius` is *always*
  defined (`scriba-scene-primitives.css:51`, `var(--scriba-radius)` →
  `:45`, `6px`) wherever `.scriba-invariant` can render, so the measured
  computed radius is `6px`, never the `4px` fallback. Not a visual defect —
  the CSS still resolves deterministically — just a discrepancy worth
  knowing before assuming the fallback value is what ships.

## Cross-Check Against `design-invariant-panel-restyle.md`

An untracked design-options document for this exact panel already exists in
the repo (`_bmad-output/implementation-artifacts/design-invariant-panel-restyle.md`,
created same day). Comparing it against this investigation's measured data:

**Convergent (independent confirmation, different methods):** inverted
type-scale hierarchy (Finding 3); zero `overflow-wrap`/`word-break`/`.katex`
rule anywhere for math content; the `role="note"`-without-`aria-live` a11y
gap (Side Findings); cramped/asymmetric spacing.

**One material correction offered:** §3.4 of the design doc states dark
mode has "no adaptation, anywhere" and that `--scriba-annotation-info` "is
also never redefined for dark anywhere in the repo." Both claims are
incorrect per direct measurement in this report (Finding 4, Measured
Geometry table) — the token **is** redefined for dark at
`scriba-scene-primitives.css:799` and `:858`, and the panel's rendered
border-left/background-tint **do** correctly re-theme (`rgb(11,104,203)` →
`rgb(112,184,255)`, verified by computed style in a live dark-mode render,
not just source reading). The design doc's check appears to have looked for
a `.scriba-invariant`-specific override inside `scriba-embed.css`'s two dark
blocks (`:249-261`, `:264-277`) and correctly found none there — but missed
that the mechanism lives one file over, as a redefinition of the custom
property itself, automatically picked up via `var()` with no
element-specific override needed. What the design doc gets right, narrower
than stated: `.scriba-invariant` has no explicit `color` property, so *text*
legibility (as opposed to border/background) rides on inherited cascade —
that part of the concern stands, it's just the border/background portion of
"no dark-mode adaptation" that this report disproves.

**Empirical backing supplied for a previously-reasoned claim:** the design
doc's §3.5 argues invariant bodies are "the most likely place in the whole
system to carry a long unbroken formula" as reasoning, without measurement.
This report supplies the missing numbers (416.9px single-formula width vs.
338px mobile container; exact break-point location) that turn that
reasoning into a confirmed, quantified defect — directly substantiating the
design doc's proposed `overflow-wrap: anywhere` remediation (its Option
B-core).

## Constraints Any Redesign Must Respect

1. **Byte-identical when absent.** A document with no `\invariant` must
   produce unchanged output — `_invariant_panel_elements` returns `[]` for
   empty/`None` (`_html_stitcher.py:107-122`), and `invariants_html`'s
   `None` sentinel (`emitter.py:127-130`) is threaded through so "no
   invariant" never emits an empty-but-present marker
   (`_html_stitcher.py:673`, "invariant emits no key, so the frame object is
   byte-identical"). Guarded by `tests/unit/test_invariant.py::test_no_invariant_is_empty`.
2. **Single source of markup, three consumers.** F1 static/print-frame
   (`_html_stitcher.py:260-274`), F2 interactive per-frame JS payload
   (`:514-570,619-629`), and the widget-shell static panel (`:705-739`) all
   call `_invariant_panel_elements()` (`:107-122`). Change that function
   (plus CSS), not each call site, or the three renderings drift apart.
3. **Live `${}` values are resolved server-side, per frame — not
   client-side.** `scene.py:411-415` re-resolves against the same bindings
   `\narrate` uses; `renderer.py:574-581` KaTeX-renders the result before it
   ever reaches the browser. `scriba.js:31-32`'s `_setInv` only swaps
   pre-rendered HTML strings into existing nodes — there is no client-side
   math engine or re-layout logic to lean on.
4. **Index-positional DOM swap.** `scriba.js:31-32` matches
   `.scriba-invariant` nodes to per-frame values by array position
   (`invp[q].innerHTML = v[q]`). Panel count/order must stay identical
   across every frame of a given animation.
5. **N invariants must stack, N ≥ 0.**
   `docs/SCRIBA-TEX-REFERENCE.md:829` documents multiple `\invariant` lines
   stacking as legal and expected; a redesign can't assume exactly one panel.
6. **KaTeX inline-mode is a shared convention, not invariant-specific.**
   `_render_invariant` (`renderer.py:238-252`) calls the same
   `ctx.render_inline_tex` used by narration/annotations, which hardcodes
   `displayMode: False` (`tex/renderer.py:538`). Routing invariants (or
   math-dominant clauses within them) to `displayMode: True`
   (`tex/renderer.py:559-579`, already a live code path) is a scoped,
   deliberate deviation from every other inline `$...$` region, not an
   incidental side effect of a chrome-only fix.
7. **Dark-mode token plumbing already works for border/background and must
   not regress.** `--scriba-annotation-info` (light `#0b68cb` at
   `scriba-scene-primitives.css:169`; dark `#70b8ff` at `:799`,`:858`)
   verified correct by direct measurement (see Cross-Check). Any chrome
   redesign should keep riding this token rather than hardcoding a
   light-only color, and should additionally add the currently-missing
   explicit `color` property for text (Finding 3 / Side Findings).
8. **No SVG viewBox involvement.** Unlike Scriba's diagram primitives
   (Array, DPTable, etc.), `.scriba-invariant` is a plain HTML `<p>`
   sibling of `.scriba-narration`, entirely outside `.scriba-stage`'s SVG
   (`_html_stitcher.py:705-739`). A redesign is free to change its box
   model without any viewBox/coordinate recompute.
9. **Existing tests encode part of this contract today** and should stay
   green (or be deliberately, visibly updated): `tests/unit/test_invariant.py`
   (`test_prelude_invariant_collected`, `test_invariant_after_step_raises_e1058`,
   `test_no_invariant_is_empty`), `tests/unit/test_invariant_interpolation.py`
   (`test_invariant_interpolates_value_not_literal`,
   `test_invariant_updates_per_step` → calls `_render_live`).

## Artifacts

- Repro source: `.../scratchpad/invariant-ugly/removal-game.tex`
- Rendered HTML: `.../scratchpad/invariant-ugly/removal-game.html`
- Measurement script (Playwright, browser pass): `.../scratchpad/invariant-ugly/measure.py`
- Raw measurements: `.../scratchpad/invariant-ugly/measurements.json`
- Static corroboration script (no browser, post-directive): `.../scratchpad/invariant-ugly/static_check.py`
- Screenshots (`.../scratchpad/invariant-ugly/screenshots/`):
  - `invariant_wide700_light.png`, `invariant_wide700_light_panel_only.png`
  - `invariant_wide700_dark.png`, `invariant_wide700_dark_panel_only.png`
  - `invariant_narrow375_light.png`, `invariant_narrow375_light_panel_only.png`
  - `invariant_narrow375_dark.png`, `invariant_narrow375_dark_panel_only.png`

(Full scratchpad prefix:
`/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/b6b798d6-92ae-4dfa-9982-9f3f2f1a33de/scratchpad/invariant-ugly/`)

## Conclusion

**Confidence: High.** All five ranked findings are grounded in direct
computed-style/bounding-rect measurement across four viewport×theme
combinations, cross-checked against the CSS source and the full emission
pipeline, and the central width claim behind Finding 1 is independently
corroborated by a second, no-browser method (the repo's own math-width
oracle, "Static corroboration" above) added after a mid-investigation
directive to stop using Playwright — the two methods agree within ~6%. The
dominant, unambiguous defect is Finding 1 (mid-formula line wrap at mobile
width, landing inside a matched delimiter pair) — everything else is real
but secondary. A sibling design-options document already proposes a
concrete fix (Option B, "Theorem Box") that independently targets four of
these five findings; this report supplies the missing empirical proof for
the wrap defect and corrects one factual claim in that document regarding
dark-mode border/background theming (Finding 4 / Cross-Check).

**Note on the no-Playwright directive:** the browser measurements in this
report (screenshots, `measurements.json`) were captured before that
directive was issued and are real, not skipped — removing or
mislabeling them would understate the evidence behind Finding 1. No
Playwright/browser-MCP call was made after the directive; the only
work added afterward is the static, no-browser corroboration above.
