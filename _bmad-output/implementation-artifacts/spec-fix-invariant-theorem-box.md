# Fix: `\invariant` theorem-box restyle (B-core, no caption) + full-size operators (Option E)

**Agent:** fix-invariant (BMAD patcher subagent) · **For:** team-lead · **Status:** DONE

## Approved scope

1. **B-core WITHOUT the caption label.** Wrap the emitted invariant `<p>` run in a
   theorem-box container (`.scriba-invariant-panel`) that owns
   border/background/radius/spacing via design tokens (`--scriba-border`,
   `--scriba-bg-code`, `--scriba-frame-radius`), with a dark pair (`#202425` /
   `#313538`) in both `[data-theme="dark"]` and
   `@media (prefers-color-scheme: dark)`. Inner `<p class="scriba-invariant"
   role="note">` stays byte-identical. N stacked `\invariant` calls land inside
   ONE wrapper.
   **Hard i18n constraint (verbatim, overrides the literal approved preview):**
   no hardcoded human-language string anywhere — no visible "Invariant"
   caption, no `aria-label="Invariant"`. Box chrome is the only signifier;
   existing per-`<p>` `role="note"` stays.
2. **Option E, route (b).** Inject `\displaystyle` into every inline `$...$`
   span of an invariant body so operators (`\max`, `\sum`, ...) render at
   full size while the panel stays inline-flowing — never switches KaTeX's
   `displayMode`.
3. **Emission locus.** `_html_stitcher.py:_invariant_panel_elements` — the
   shared emitter, so filmstrip, interactive widget, and print modes all get
   the box from one place.

**Mandatory method:** impact analysis before editing, TDD (RED→GREEN),
targeted tests only + grep-swept related tests, static verification only (no
Playwright — repo AGENTS.md ban). No version bump / CHANGELOG / commit / golden
re-bless (out of scope for this agent).

## Divergence from the literal approved preview (AFTER.html) — documented per instruction

The approved preview literally used `role="group" aria-label="Invariant"` on the
wrapper plus a `.scriba-invariant-label` caption span. The user's later, more
specific directive explicitly overrides this: no hardcoded language string
anywhere in the feature, in any form. Implemented wrapper: `<div
class="scriba-invariant-panel">` — no `role`, no `aria-label`, no caption
element of any kind. The inner `<p role="note">` (already present, already
non-lingual) remains the only exposed a11y semantic. This is a deliberate,
instructed divergence, not an oversight.

## Impact analysis (GitNexus, run BEFORE editing either function)

`mcp__gitnexus__impact`, repo `scriba`:

| Target | Direction | impactedCount | risk | epistemic | direct callers (depth 1) | processes affected |
|---|---|---|---|---|---|---|
| `_invariant_panel_elements` (`_html_stitcher.py`) | upstream | 5 | **LOW** | exact | `emit_animation_html`, `emit_interactive_html` | 0 |
| `_render_invariant` (`renderer.py`) | upstream | 7 | **LOW** | exact | `AnimationRenderer.render_block`, `_snapshot_to_frame_data` | 0 |

Full chains: `_invariant_panel_elements` → `emit_animation_html`/`emit_interactive_html`
(d1) → `emit_html` (d2) → `AnimationRenderer.render_block` / `DiagramRenderer.render_block`
(d3). `_render_invariant` → `AnimationRenderer.render_block`/`_snapshot_to_frame_data`
(d1) → `_materialise`/`_materialise_substory`/`DiagramRenderer.render_block`/
`render.py:render_file` (d2) → `render.py:main` (d3). Both LOW risk, 0
`affected_processes` — no execution-flow break, matching a pure markup/CSS +
additive-regex change.

**Correction to the task's premise:** the task/design doc assumed 3 call
sites already shared `_invariant_panel_elements` ("single source, 3
consumers"). Direct reading showed `emit_interactive_html`'s widget-level
pinned-panel block (previously lines 712–721) **inline-duplicated** the same
markup logic instead of calling the helper. Fixed in-scope (low-risk,
same already-impact-analyzed function, DRY, makes the design intent
literally true) — see change (b) below. This is why `emit_interactive_html`
now correctly appears as a depth-1 caller in the impact table above.

## Code changes

### (a) `scriba/animation/_html_stitcher.py:107-127` — shared emitter now wraps in one panel

Before:
```python
def _invariant_panel_elements(texts: "list[str] | None") -> list[str]:
    """Render ``\\invariant`` bodies to ``<p class="scriba-invariant">`` panels.
    ...
    """
    if not texts:
        return []
    return [
        f'<p class="scriba-invariant" role="note">'
        f"{_safe_narration_html(h)}</p>"
        for h in texts
    ]
```

After:
```python
def _invariant_panel_elements(texts: "list[str] | None") -> list[str]:
    """Render ``\\invariant`` bodies into ONE theorem-box panel element.
    ...N stacked bodies land inside a single ``.scriba-invariant-panel``
    wrapper...; the wrapper carries no role/aria-label — the box chrome is
    the signifier, not a hardcoded caption string (i18n)...
    """
    if not texts:
        return []
    body = "\n  ".join(
        f'<p class="scriba-invariant" role="note">'
        f"{_safe_narration_html(h)}</p>"
        for h in texts
    )
    return [f'<div class="scriba-invariant-panel">\n  {body}\n</div>']
```

Return-type contract unchanged (list of 0-or-1 strings), so both other call
sites (F1 filmstrip loop at line ~271-275, F2 print-frame block at line
~625-630) need no changes — they already just `"".join(...)` over whatever
the helper returns.

### (b) `scriba/animation/_html_stitcher.py:712-721` — widget-level site refactored onto the shared helper

Before (inline-duplicated the panel markup, bypassing the "single source"):
```python
_invariant_panels = (
    frames[0].invariants_html if _inv_live else invariants
)
_invariant_html = ""
if _invariant_panels:
    _invariant_html = "\n  " + "\n  ".join(
        f'<p class="scriba-invariant" role="note">'
        f'{_safe_narration_html(h)}</p>'
        for h in _invariant_panels
    )
```

After:
```python
_invariant_panels = (
    frames[0].invariants_html if _inv_live else invariants
)
_panel_elements = _invariant_panel_elements(_invariant_panels)
_invariant_html = ("\n  " + _panel_elements[0]) if _panel_elements else ""
```

### (c) `scriba/animation/renderer.py:238-258` — new `_inject_displaystyle` helper (Option E, route b)

```python
_INVARIANT_MATH_RE = re.compile(r"\$\$([\s\S]*?)\$\$|\$([^\$]+?)\$")


def _displaystyle_sub(m: "re.Match[str]") -> str:
    if m.group(1) is not None:
        return m.group(0)  # $$...$$ display span — already full-size.
    body = m.group(2)
    if body.lstrip().startswith("\\displaystyle"):
        return m.group(0)  # already present — do not double-inject.
    return f"$\\displaystyle {body}$"


def _inject_displaystyle(text: str) -> str:
    """Force display-size operators in every inline ``$...$`` span of *text*."""
    return _INVARIANT_MATH_RE.sub(_displaystyle_sub, text)
```

Single combined alternation regex (display-before-inline in one pass), mirroring
`tex/renderer.py:_render_cell`'s shield→display→inline precedence, so a
`$$...$$` span can never be mis-split by a naive `$...$`-only pattern (the
"stray $" bug). A single trailing space after the injected `\displaystyle` is
mandatory TeX hygiene — `\displaystylex_i` would tokenize as one invalid
control word; a space is always safe and is consumed as the control-word
terminator, so it adds no visible gap.

### (d) `scriba/animation/renderer.py:261-277` (`_render_invariant`) — wired in

Before: `rendered = ctx.render_inline_tex(text)`
After: `rendered = ctx.render_inline_tex(_inject_displaystyle(text))`

Both of `_render_invariant`'s callers (`AnimationRenderer.render_block`'s static
path, `_snapshot_to_frame_data`'s live per-frame path) funnel through this one
function, so Option E is covered with zero additional call-site changes.

### (e) `scriba/animation/static/scriba-scene-primitives.css`

Light rule, `:1131-1144` (was `.scriba-invariant` alone at 1113-1124):
```css
.scriba-invariant-panel {
  margin: 0.75rem 0 0;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--scriba-border);
  background: var(--scriba-bg-code);
  border-radius: var(--scriba-frame-radius);
}
.scriba-invariant {
  margin: 0.2em 0 0;
  padding: 0;
  color: var(--scriba-fg);
  font-size: 0.82em;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
```
Old per-`<p>` `border-inline-start` + `color-mix(...)` background chrome
removed (chrome moved to the wrapper).

Dark pair, `:997-1006` (new, appended after the existing dark-override bucket,
following the file's established convention — e.g. `.scriba-annot-label`'s
light rule at line 549 vs. its dark override at 980-991 — of bucketing dark
selector overrides together, physically apart from the light rule):
```css
[data-theme="dark"] .scriba-invariant-panel {
  background: #202425;
  border-color: #313538;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .scriba-invariant-panel {
    background: #202425;
    border-color: #313538;
  }
}
```
`#202425`/`#313538` matches `.scriba-frame-header`/`.scriba-controls`'s dark
pair (H6 fix convention), not `--scriba-bg-code`'s own dark resolution
(`#1a1d1e`, per `.scriba-codepanel-chrome`'s fallback) — an intentionally
distinct, slightly lighter dark shade for this chrome, per the design doc.

## Overflow-protection decision: `overflow-wrap: anywhere` (not `overflow-x: auto`)

Measured with `measure_inline_math` (`scriba/animation/primitives/_math_metrics.py:461`,
static advance-sum against vendored KaTeX metrics — no browser):

```
big invariant fragment (removal-game.tex): linear_model=True width_px=397.5 (font_px=13)
short invariant fragment:                  linear_model=True width_px=100.1 (font_px=13)
estimated available inline width at 375px viewport: ~333px
```

The big fragment's linear-model width (397.5px) already exceeds the ~333px
estimated available panel content width at a 375px viewport — **before** any
`\displaystyle` upsizing is even factored in. Caveat: `\displaystyle` is in
`_math_metrics.py`'s `_IGNORABLE` set (a zero-glyph structural token for the
advance-sum model), so this tool structurally cannot quantify the *additional*
width `\displaystyle` adds (bigger `\max` glyph, `\bigl`/`\bigr` fence
upsizing) — 397.5px is a **lower bound**, not the true post-injection width.
The actual rendered KaTeX output (see repro snippets below) confirms the fence
delimiters upsize to `minsize="1.2em" maxsize="1.2em"` under `displaystyle`,
so the true width is larger still, not smaller. Conclusion: overflow is a
real, already-measured risk at mobile widths, and `overflow-wrap: anywhere`
(matching `.scriba-progress`'s convention, and the approved design mock)
keeps all content visible without requiring a discoverable horizontal-scroll
gesture — appropriate since an invariant's whole purpose is at-a-glance
readability. `overflow-x: auto` was rejected: the fragment is one unbroken
run with no natural break points, so a scroll-only approach without wrap
risks silently clipping formula content off-screen with no obvious affordance.

## Tests — RED → GREEN

New files (28 tests total, all RED against unmodified code, all GREEN after
the 5 edits above):

- `tests/unit/test_invariant_panel_wrapper.py` (6 tests) — wrapper present;
  exactly one wrapper for N stacked `\invariant` calls (both single- and
  two-predicate cases); wrapper present in static filmstrip and interactive
  print frames; wrapper tag carries **zero** extra attributes (no
  `aria-label`, no `role`); no `.scriba-invariant-label` class or `>Invariant<`
  text anywhere (i18n gate).
- `tests/unit/test_invariant_panel_css_theme.py` (9 tests) — light rule uses
  `var(--scriba-border)` / `var(--scriba-bg-code)` / `var(--scriba-frame-radius)`;
  old `border-inline-start` chrome gone from `.scriba-invariant`; type scale
  (`0.82em`, `var(--scriba-fg)`, `1.4`, `overflow-wrap: anywhere`) present;
  explicit `[data-theme="dark"]` pair present; OS-preference twin present
  inside a `@media (prefers-color-scheme: dark)` block; `#202425`/`#313538`
  pair present.
  *(One self-inflicted RED→GREEN detour: my first draft of the token-presence
  assertions naively `.split()`ed on the bare selector text, which also
  matches inside `[data-theme="dark"] .scriba-invariant-panel {` — and since
  that dark bucket sits earlier in the file than the light rule (by
  convention), the split grabbed the wrong block. Fixed by anchoring on a
  leading newline, which only the column-0 light rule has. Confirmed this was
  a test bug, not an implementation bug, by re-deriving the CSS placement
  intent before changing anything.)*
- `tests/unit/test_invariant_displaystyle.py` (13 tests) — `_inject_displaystyle`
  unit tests (bare math, no double-injection, multiple spans, mixed
  prose+math, `$$...$$` untouched, mixed display+inline, plain text/empty
  string untouched) and `_render_invariant` wiring tests via a fake
  `RenderContext` (pure-math gets `\displaystyle`, mixed text+math stays
  inline AND gets it, no-math untouched, live-interpolated value survives,
  no-KaTeX fallback still escapes correctly).

Pre-existing named tests — run **unmodified**, still pass:

- `tests/unit/test_invariant.py` (5 tests) — PASS
- `tests/unit/test_invariant_interpolation.py` (5 tests) — PASS
- `tests/unit/test_fixc_static_print_invariant.py` (5 tests) — PASS

Grep-swept for anything else touching `_html_stitcher`/`_invariant_panel_elements`/
`_render_invariant`/`_inject_displaystyle`/`invariants_html`/`scriba-invariant`:
found `test_r32_annotation_stable_layout.py`, `test_env_options_wired.py`,
`test_w3_batch1.py` (import `_html_stitcher` for unrelated symbols — annotation
layout, `emit_html` env-var wiring, `_safe_narration_html` escaping — none
touch invariant-panel logic). Ran anyway per the task's grep mandate: **75
passed**, 0 regressions.

**Total: 28 new + 15 pre-existing (unmodified) + 75 swept = 118 passing, 0 failing.**

## Static repro verification (no Playwright, per AGENTS.md ban)

Rendered both scratchpad repro docs via
`SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py <in>.tex -o <out>.html --no-minify`
and inspected emitted bytes directly.

**`removal-game.tex`** (one `\invariant` call, two `$...$` spans joined by `;`):
```html
<div class="scriba-invariant-panel">
  <p class="scriba-invariant" role="note">…annotation="…">\displaystyle \mathrm{score}(l,r)=\max\bigl(x_l-\mathrm{score}(l{+}1,r),\ x_r-\mathrm{score}(l,r{-}1)\bigr)</annotation>…</p>
</div>
```
(panel count = 1; both math spans carry the injected `\displaystyle `, MathML
shows `displaystyle="true"`, fence delimiters `minsize="1.2em" maxsize="1.2em"`.)

**`removal-game-after.tex`** (two stacked `\invariant` calls; the first
hand-authored with `\displaystyle` already inline):
```html
<div class="scriba-invariant-panel">
  <p class="scriba-invariant" role="note">…annotation="…">\displaystyle\mathrm{score}(l,r)=\max\bigl(...)\bigr)</annotation>…</p>
  <p class="scriba-invariant" role="note">…annotation="…">\displaystyle \mathrm{score}(l,l)=x_l</annotation>…</p>
</div>
```
panel count = **1**, inner `<p>` count = **2** — confirms N stacked
`\invariant` calls land inside one wrapper. First span: no double-injection
(`\displaystyle\mathrm` stays single, hand-authored form preserved). Second
span: auto-injected with the mandatory space (`\displaystyle \mathrm`).
Both bundles' inlined `<style>` confirmed to carry the new light rule
(`var(--scriba-border)`/`var(--scriba-bg-code)`/`var(--scriba-frame-radius)`)
and the OS-preference dark twin (present in exactly 1 of the 16
`@media (prefers-color-scheme: dark)` blocks in the bundle) plus the explicit
`[data-theme="dark"]` toggle.

## Goldens expected to shift (NOT re-blessed — listing only, per scope)

Grep-verified (`\invariant{` across `tests/golden` + `tests/doc_coverage`):

- **Structural + CSS diff:**
  - `tests/golden/examples/corpus/anim_clarity_showcase.tex`/`.html`
  - `tests/doc_coverage/corpus/invariant_panel.tex`/`.html` (its `.expect` is
    just `"ok\nfeature: §5.17..."`, not a markup pin — does **not** need
    updating)
- **CSS-bundle-growth-only diff** (every full-page render inlines the entire
  `scriba-scene-primitives.css`, confirmed by grepping a non-invariant corpus
  doc's `.html` for the stylesheet's header comment and finding it present):
  all other **106** `tests/golden/examples/corpus/*.html` and all other **421**
  `tests/doc_coverage/corpus/*.html` — pure byte/whitespace diff from the ~13
  added CSS lines, no markup-structure change in any of them.
- **NOT affected:**
  - `tests/doc_coverage/corpus/neg_E1058_invariant_after_step.tex`/`.expect`
    — parse-error path (E1058), never reaches the renderer/emitter, has no
    `.html` golden.
  - `tests/golden/animation/*` and `tests/golden/smart_label/*` — fragment-level
    goldens (bare widget markup, no inlined stylesheet, confirmed via
    inspection); none reference `invariant` at all.

## Out of scope (per task), confirmed not done

No version bump, no CHANGELOG entry, no git commit, no golden re-bless.
`git status` intentionally left dirty for team-lead to review/commit.
