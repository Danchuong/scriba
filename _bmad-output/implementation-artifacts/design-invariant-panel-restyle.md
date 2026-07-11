---
title: 'Invariant panel restyle — design options'
type: 'design-options'
created: '2026-07-11'
status: 'proposal — no option yet approved'
context: ['docs/SCRIBA-TEX-REFERENCE.md §5.17', 'scratchpad: removal-game.tex render']
---

## 1. Problem framing

A real doc (`removal-game.tex`) declares one `\invariant` whose body joins **two**
formulas with a literal `; `:

```latex
\invariant{$\mathrm{score}(l,r)=\max\bigl(x_l-\mathrm{score}(l{+}1,r),\ x_r-\mathrm{score}(l,r{-}1)\bigr)$; $\mathrm{score}(l,l)=x_l$}
```

`\invariant{text}` parses as one raw brace string, byte-identical mechanism to
`\narrate` (`scriba/animation/parser/_grammar_commands.py:186-189`) — no
semicolon segmentation happens anywhere in the pipeline. The two KaTeX spans
land on one unbroken inline-math line inside a box that was styled for a
short one-line predicate, not a compound recurrence. That mismatch, not any
single CSS property, is the dominant "ugly" driver on this doc.

## 2. Current implementation — full pipeline map

| Stage | Locus | What happens |
|---|---|---|
| Lexer | `scriba/animation/parser/lexer.py:89` | `invariant` keyword token |
| Grammar | `scriba/animation/parser/grammar.py:108,228-230,269,307-318` | Collects raw body into `invariants: list[str]`; dispatch guard raises **E1058** outside the prelude |
| Substory guard | `scriba/animation/parser/_grammar_substory.py:371-378` | Same E1058 guard inside `\substory` blocks |
| AST | `scriba/animation/parser/ast.py:583` | `invariants: tuple[str, ...] = ()` field on the environment IR |
| Render (static) | `scriba/animation/renderer.py:238-252` (`_render_invariant`), `:785-799` | KaTeX-renders `$...$`, expands `\textbf` etc. — no `\hl`/`\ref` macros, unlike narration |
| Render (live) | `scriba/animation/renderer.py:574-602,901-939` | `invariants_live = any("${" in t ...)`; when true, every frame gets its own `_render_invariant` pass over the `${}`-resolved body |
| HTML — single source of markup | `scriba/animation/_html_stitcher.py:107-122` (`_invariant_panel_elements`) | Emits `<p class="scriba-invariant" role="note">{html}</p>` per text. **Shared by filmstrip, interactive widget, and print** — one change here reaches all three render modes |
| HTML — interactive widget | `scriba/animation/_html_stitcher.py:705-721,739` | Panel(s) emitted **once**, as a direct sibling immediately after `<p class="scriba-narration">`, before `.scriba-substory-container` |
| HTML — filmstrip (legacy) | `scriba/animation/_html_stitcher.py:260-316` | Panel re-emitted inside every `<li class="scriba-frame">`, after that frame's narration |
| HTML — print | `scriba/animation/_html_stitcher.py:619-642` | Live invariants get a per-frame print copy; static ones don't (byte-stable) |
| JS runtime | `scriba/animation/static/scriba.js:31-32,119,461` | `invp = querySelectorAll('.scriba-invariant')`; `_setInv(i)` swaps `.innerHTML` per node, called on init and after each transition settles ("rides the same after-settle beat" as narration's aria-live announcement) |
| CSS | `scriba/animation/static/scriba-scene-primitives.css:1113-1124` | The entire visual definition — see §3 |

## 3. What's actually wrong (grounded, not vibes)

```css
.scriba-invariant {
  margin: 0.5em 0 0;
  padding: 0.35em 0.6em;
  border-inline-start: 3px solid var(--scriba-annotation-info, #0070d5);
  background: color-mix(in srgb, var(--scriba-annotation-info, #0070d5) 7%, transparent);
  border-radius: 0 var(--scriba-frame-radius, 4px) var(--scriba-frame-radius, 4px) 0;
  font-size: 0.9em;
  line-height: 1.4;
}
```

1. **No signifier.** Nothing says "this is an invariant" — no caption, no icon, just a
   thin blue rule. Compare the codebase's own two label idioms it doesn't reuse
   here: `.scriba-step-title` (bold inline caption, primitives CSS:1104-1111) and
   `.scriba-step-label` (uppercase monospace mini-badge, primitives CSS:63-64,
   embed CSS:233-238) — both already exist for exactly this "meta-label on a
   content block" job.
2. **Inverted type hierarchy.** Interactive `.scriba-narration` is `font-size: 0.85rem`
   (hardcoded, `scriba-embed.css:186`); `.scriba-invariant` is `0.9em` against the
   widget's root size (≈0.9rem). The "pinned supporting fact" reads *larger* than
   the primary narration above it.
3. **Cramped, asymmetric spacing.** `margin: 0.5em 0 0` (top only) + `padding: 0.35em 0.6em`
   (tight) — the panel has no breathing room below it and, since
   `.scriba-substory-container` is empty in single-substory docs, it sits flush
   against the widget's rounded bottom edge.
4. **No dark-mode adaptation, anywhere.** Checked `scriba-embed.css`'s two dark
   blocks (`[data-theme="dark"]` at :249-261 and `@media (prefers-color-scheme: dark)`
   at :264-277) — `.scriba-narration`, `.scriba-controls`, `.scriba-dot`,
   `.scriba-frame`, `.scriba-step-label` all get overrides; `.scriba-invariant`
   gets none. `--scriba-annotation-info` (`#0b68cb`) is also never redefined for
   dark anywhere in the repo. The panel has no explicit `color` either, so its
   legibility in a dark host depends entirely on inherited cascade.
5. **Zero overflow protection, and it's not a house gap — it's specific to this
   element.** No `.katex-display`, `overflow-x`, `word-break`, or `overflow-wrap`
   rule exists anywhere in `scriba-scene-primitives.css` or `scriba-tex-content.css`
   for *any* math context. Narration math tends to be short inline symbols;
   invariant bodies are, by the documented use case (loop invariants, recurrences),
   the most likely place in the whole system to carry a long unbroken formula.
6. **Multiple `\invariant` calls stack as N separately-chromed bars.** The docs
   confirm this is legal and expected (`docs/SCRIBA-TEX-REFERENCE.md:829`), but
   each stacked `<p>` repaints its own left-rule + tint — no shared grouping,
   so two or three invariants read as a stack of thin blue stripes rather than
   one coherent block.
7. **Minor a11y gaps.** `role="note"` is present but there's no `aria-live` on the
   live-updating panel (narration gets `aria-live="polite"` at `_html_stitcher.py:739`;
   the invariant panel doesn't), and no `dir="auto"` (narration has it; invariant
   bodies can carry the same mixed Vietnamese/math content).

## 4. Design options

| # | Name | Effort | Segmentation? | Authoring impact |
|---|---|---|---|---|
| A | Labeled Callout | S | No | Zero |
| B | **Theorem Box** (recommended) | S core / +M for segmentation | Yes (fast-follow) | Zero |
| C | Segmented Chip Row | M | Yes (chips) | Zero (docs nudge only) |
| D | Placement Move (above stage) | M, higher risk | No | Zero, but doc-contract wording changes |
| E | Display-mode math | S–M | No (orthogonal) | Zero |
| F | Step-scoped live emphasis | M | No (orthogonal, additive) | Zero |

### Option A — Labeled Callout

Keep today's left-rule quote-block shape; add a small uppercase caption
reusing the *existing* `.scriba-step-label` token set verbatim
(`font: var(--scriba-step-label-font); color: var(--scriba-step-label-color);
text-transform: uppercase; letter-spacing: 0.05em;`), fix the asymmetric
margin/padding, add an explicit `color` and dark-mode override.

- **Visual:** `[INVARIANT]` mini-badge sits above the body inside the same
  left-ruled block; block gets symmetric padding and a proper bottom margin.
- **Authoring impact:** zero.
- **Locus:** `scriba-scene-primitives.css:1113-1124` (rewrite rule, add
  `.scriba-invariant-label`), `scriba-embed.css:249-277` (dark overrides),
  `_html_stitcher.py:107-122` (prepend the label span into the same emitted
  string — single source, reaches all three render modes for free).
- **Risk:** lowest of all options. Cheapest fix, but doesn't touch the
  semicolon-jam problem that's the dominant defect on the actual reported doc.

### Option B — Theorem Box (recommended)

Move the "box" chrome to a **new outer wrapper**; the existing
`<p class="scriba-invariant">` becomes a plain interior row. This is the key
structural idea: it lets N stacked invariants (whether from N separate
`\invariant{}` calls, or from splitting one semicolon-joined call) share
**one** bordered surface and **one** caption instead of N repainted bars.

**B-core (ship first, S effort, zero data-shape risk):**
- Outer `<section class="scriba-invariant-panel">`: full border using the
  existing neutral `--scriba-border` token (not the saturated blue
  `--scriba-annotation-info` tint — matches the `.scriba-frame` /
  `.scriba-frame-header` neutral chrome language already used for the print
  filmstrip, `scriba-embed.css:227-231`), `background: var(--scriba-bg-code)`
  (reuse the existing "code panel" surface token instead of inventing one),
  `border-radius: var(--scriba-frame-radius)` on all corners.
- `.scriba-invariant-label`: reuses `--scriba-step-label-font` /
  `--scriba-step-label-color` verbatim — zero new typographic decisions.
- Inner `.scriba-invariant` rows: drop border/background (now owned by the
  panel), add explicit `color: var(--scriba-fg)` (closes the dark-mode
  inheritance gap directly), drop to `0.82em` (deliberately subordinate to
  narration's 0.85rem — fixes the inverted hierarchy), add `dir="auto"` and
  `aria-live="polite"` only when the invariant is live (`invariants_live`
  is already computed at `renderer.py:907-908` — thread that bool through
  to the emitted attribute), add a scoped `overflow-wrap: anywhere` on the
  KaTeX span inside this box only.
- New dark rule mirrors the *existing* dark palette exactly
  (`#202425`/`#313538`, the same values already used for
  `.scriba-frame-header`/`.scriba-controls`) — no new hex values invented.
- **Locus:** `scriba-scene-primitives.css:1113-1124`,
  `scriba-embed.css:249-277`, `_html_stitcher.py:107-122` (wrap all texts for
  one scene in one panel instead of mapping each to its own `<p>`).

**B-extended (fast-follow, +M effort, the one part with real plumbing risk):**
- Split a single body on top-level `;` (semicolon seen while `$...$` delimiter
  parity is even, i.e. outside math) into multiple interior rows, purely as
  a rendering-time string operation — **no grammar/AST change**, `ir.invariants`
  stays a 1-element tuple for this doc.
- The one thing this touches for real: the **live** `${}` path's cardinality.
  `renderer.py:574-602` currently emits one HTML string per `ir.invariants`
  entry, and `scriba.js`'s `_setInv` maps `invp[q]` to `frames[i].inv[q]` by
  **index**. Splitting one entry into two rows means the static
  prelude-panel-count and the per-frame live-cell-count must grow together
  (both derived from the same split), or the index mapping desyncs and a
  live invariant swaps the wrong row's text. This is a real but contained
  fix — same function, same call site, just needs the split applied
  consistently on both the once-rendered path (`renderer.py:785-799`) and the
  per-frame live path (`renderer.py:574-602`).

- **Risk:** B-core is CSS + wrapper-markup only — no data-shape change, lowest
  risk of any option that actually solves the reported doc. B-extended is the
  one place across all six options that touches the live-data index contract;
  isolate it as a separate PR from B-core.

### Option C — Segmented Chip Row

Restyle the *already-legal* multi-`\invariant`-call case as a wrapping row of
pill chips, reusing the annotation-pill visual language that already exists
for pill/link/note labels (white/neutral fill + colored stroke, "Scriba Sans"
face, `--scriba-annotation-font`, `scriba-scene-primitives.css:98-105`).
Each clause becomes its own rounded chip; `flex-wrap: wrap` handles overflow.

- **Authoring impact:** zero for the syntax itself, but this option only pays
  off if authors are nudged (docs wording, not a hard requirement) to prefer
  multiple `\invariant{}` calls over one semicolon-joined string — otherwise
  a chip-row restyle of a *single* stacked `<p>` doesn't help this doc at all.
- **Locus:** `_html_stitcher.py:107-122` (wrap N panels in a flex container),
  new CSS for `.scriba-invariant-chip`, `docs/SCRIBA-TEX-REFERENCE.md` §5.17
  wording nudge.
- **Risk:** M. Bolder visual differentiation than B, but doesn't fix today's
  actual doc unless paired with a docs nudge (behavior change, not a code
  fix) or with B-extended's semicolon splitter (in which case it's really
  "B-extended with chip chrome instead of plain rows" — a valid variant, not
  an independent alternative).

### Option D — Placement Move (pin above the stage)

Relocate the panel to read as a precondition shown *before* the animation
rather than an addendum after narration.

- **Locus:** touches **three** separate emission sites —
  `_html_stitcher.py:729-745` (interactive), `:300-316` (filmstrip),
  `:619-642` (print) — each needs its insertion point moved, not just
  restyled.
- **Risk:** highest of all six. This is the only option where the *documented
  contract* itself says otherwise — `docs/SCRIBA-TEX-REFERENCE.md:821` states
  the panel renders "pinned **below the narration**" verbatim, so this isn't
  a CSS change, it's a spec-contract change. Also the largest golden-diff
  surface since three call sites reorder DOM instead of one wrapping change.
  Not recommended — the complaint is chrome quality, not position.

### Option E — Display-mode math for math-dominant bodies

When an invariant clause is "mostly math" (strip `$...$`/`\(...\)` delimiters;
remainder is only whitespace/`;`), render that KaTeX chunk in **display
mode** instead of inline — larger operators, properly-sized stretchy parens
for things like `\max(...)`, centered instead of squeezed to 0.9em.

- **Confirmed feasible, not a spike:** `displayMode: True` is already a live,
  working code path — `scriba/tex/renderer.py:559-574` (`_render_display`) is
  a sibling of the inline path used today (`_render_inline`,
  `scriba/tex/renderer.py:530-557`, `displayMode: False`). `_render_invariant`
  (`renderer.py:238-252`) just needs a route to the display path for
  qualifying clauses instead of only ever calling the inline one.
- **Authoring impact:** zero (auto-detected from body shape).
- **Risk:** S–M. Display-mode KaTeX is taller, so pair with B's box (fixed
  padding, not a fixed height) rather than the current unstyled paragraph.
  Classification is per-clause and stable across a scene's frames (only the
  `${}` *value* changes per frame, not the clause's math-vs-prose shape), so
  this does not violate "panel must not resize per step" any more than plain
  text-length changes already can.

### Option F — Step-scoped live emphasis (additive delight layer)

No chrome change. When a live `${var}` inside the panel is the binding a
`\compute`/`\apply` touched *this* step, pulse that row using the exact
mechanic already wired for stage targets (`_emphasize`/`_pulseTargets` in
`scriba.js`, and the existing `.scriba-emphasis` keyframe — no new CSS
animation needed). Detectable client-side by string-diffing
`frames[i].inv[q]` against `frames[i-1].inv[q]`; no new data field required.

- **Risk:** low — purely additive, motion-only, already respects
  `prefers-reduced-motion` via the existing `_canAnim` gate. This is a
  complement to whichever chrome option ships, not a substitute for one.

## 5. Recommendation

**Ship Option B (Theorem Box), B-core first.** It is the only option that
directly closes every concretely-diagnosed defect in §3 — missing signifier,
inverted type scale, cramped spacing, absent dark-mode support, N-bars-instead-
of-one-panel for stacked invariants — using **only tokens that already exist**
in the codebase (`--scriba-border`, `--scriba-bg-code`, `--scriba-frame-radius`,
`--scriba-step-label-font/-color`, the established `#202425`/`#313538` dark
pair), with a change confined to one CSS rule plus one shared HTML-emission
function that already fans out to all three render modes. Follow with
B-extended (semicolon segmentation) as a fast-follow once the live-index
plumbing is isolated in its own change — that second step is what actually
fixes the reported doc's two-formulas-on-one-line problem, and it's worth
sequencing separately because it's the one piece of this whole design space
with real data-shape risk. Layer Option E (display-mode for math-dominant
clauses) on top once B-extended ships; it's now confirmed cheap and it's what
will make `\max(x_l - \mathrm{score}(l{+}1,r), \ldots)` actually read like a
proper recurrence instead of squeezed inline text.

### Before / after mock (B-core)

**Before** (`_html_stitcher.py:739`, `scriba-scene-primitives.css:1113-1124`):
```html
<p class="scriba-narration" ...>...</p><p class="scriba-invariant" role="note">…</p>
```
```css
.scriba-invariant {
  margin: 0.5em 0 0; padding: 0.35em 0.6em;
  border-inline-start: 3px solid var(--scriba-annotation-info, #0070d5);
  background: color-mix(in srgb, var(--scriba-annotation-info, #0070d5) 7%, transparent);
  border-radius: 0 var(--scriba-frame-radius,4px) var(--scriba-frame-radius,4px) 0;
  font-size: 0.9em; line-height: 1.4;
  /* no color, no dark override, no dir, no aria-live */
}
```

**After** (structural sketch, not literal code):
```html
<p class="scriba-narration" ...>...</p>
<section class="scriba-invariant-panel" role="group" aria-label="Invariant">
  <span class="scriba-invariant-label">Invariant</span>
  <p class="scriba-invariant" role="note" dir="auto">…</p>
  <!-- one <p class="scriba-invariant"> per clause; N calls or N split rows both land here -->
</section>
```
```css
.scriba-invariant-panel {
  margin: 0.75rem 0 0; padding: 0.6rem 0.75rem;
  border: 1px solid var(--scriba-border);
  background: var(--scriba-bg-code);
  border-radius: var(--scriba-frame-radius);
}
.scriba-invariant-label {
  font: var(--scriba-step-label-font); color: var(--scriba-step-label-color);
  text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.3em;
}
.scriba-invariant {
  margin: 0.2em 0 0; padding: 0; color: var(--scriba-fg);
  font-size: 0.82em; line-height: 1.4; overflow-wrap: anywhere;
}
[data-theme="dark"] .scriba-invariant-panel { background: #202425; border-color: #313538; }
```

The existing `<p class="scriba-invariant" role="note">` opening tag stays
**byte-identical in its class attribute** — chrome moves to the new wrapper,
not onto this node — which is deliberate: every existing test that checks
`'class="scriba-invariant"' in html_out` or
`html_out.count('class="scriba-invariant"') == 1`
(`tests/unit/test_invariant.py:74-77,89`,
`tests/unit/test_fixc_static_print_invariant.py:91,98,128,136`) keeps passing
unmodified for the single-invariant case.

### What actually shifts

Checked for the real emitted element, not just the inlined CSS bundle (which
mentions `.scriba-invariant` in every golden's `<style>` block regardless of
whether that doc uses `\invariant` at all):

- **Goldens that actually render the panel:** `tests/golden/examples/corpus/anim_clarity_showcase.html`
  (+ its `.tex`), `tests/doc_coverage/corpus/invariant_panel.html`
  (+ `.tex`/`.expect`) — 2 rendered artifacts, need visual re-approval.
- **Unit tests asserting markup shape:** `tests/unit/test_invariant.py`,
  `tests/unit/test_invariant_interpolation.py`,
  `tests/unit/test_fixc_static_print_invariant.py` — all substring/count
  based (see above), so B-core needs **no test edits**; B-extended's
  multi-row split *would* need `test_fixc_static_print_invariant.py:136`
  reconsidered since `.count('class="scriba-invariant"')` would legitimately
  become 2 for this specific two-clause doc.
- `tests/doc_coverage/corpus/neg_E1058_invariant_after_step.tex` is a
  parse-error path (asserts E1058), untouched by any of these options.

## 6. Constraints checklist

- [x] KaTeX-rendered math — unchanged in every option; E adds a second KaTeX
      call variant (`displayMode: True`), already a proven path.
- [x] `${var}` live interpolation keeps working — B-core doesn't touch the
      live path at all; B-extended is flagged as the one piece that must
      keep the static-panel-count/live-cell-count contract in sync.
- [x] Multiple `\invariant` panels stay legal — B unifies them under one
      wrapper instead of changing the legality or call syntax.
- [ ] **Dark mode is a pre-existing gap orthogonal to which option ships** —
      today `.scriba-invariant` has no dark rule and `--scriba-annotation-info`
      is never redefined for dark anywhere in the repo. Whichever option is
      chosen should carry this fix; it isn't unique to B, it's just that B's
      rewrite happens to touch the same rule anyway.
- [x] No new fonts — every option reuses `--scriba-step-label-font`,
      `--scriba-annotation-font`, or inherits body text; none introduce a
      new `@font-face`.
- [ ] Layout stability across steps — no current mechanism reserves a
      cross-frame max height for the invariant panel (unlike, e.g., the
      cross-frame label-width reservations in `primitives/base.py:970-988`
      for node labels). This is a **pre-existing** risk for live invariants
      with variable-length values, not introduced by any option here;
      flagging so implementation can decide whether to add a reservation
      pass or accept today's already-live behavior.
- [x] A11y — `role="note"` already present; B-core adds `dir="auto"` (parity
      with narration) and `aria-live="polite"` gated on `invariants_live`
      (narration already has this exact pattern to copy at
      `_html_stitcher.py:739`).
- [ ] RTL — no option here does anything RTL-specific beyond adding
      `dir="auto"`; should be re-checked visually once `dir="auto"` lands
      since the panel's `border-inline-start`-style left rule (today) or new
      full border (B) both need to be verified mirroring correctly, same as
      any other `border-inline-*` logical-property usage already in this file.
