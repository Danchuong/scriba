# 11 — Widget QA (Static Audit)

Agent 11/14, Scriba v0.5.1 @ eb4f017.

## Scope

Validate the interactive animation player widget emitted by `scriba/animation/emitter.py::emit_interactive_html`. Prior audits were all backend-focused (HTML serialization correctness). This pass asks: **does the widget actually work when a human loads it in a browser, and does the feature set match the scope the prompt implies**?

## Environment

| Tool | Available? | Version |
|---|---|---|
| Node Playwright (`npx playwright`) | No | `NOT_INSTALLED` |
| Python `playwright` module | No | `ModuleNotFoundError` |
| `pytest-playwright`, `selenium`, `puppeteer` in pyproject | No | not declared |
| Browser binary available to the harness | n/a | n/a |

**No dynamic browser testing was possible.** The report is a static audit of:

- `scriba/animation/emitter.py` lines 751–815 (widget HTML + inline JS)
- `scriba/animation/static/scriba-animation.css` (70 lines)
- `scriba/animation/static/scriba-scene-primitives.css` (523 lines)
- `render.py` lines 58–325 (the CSS block actually shipped with cookbook HTMLs)
- Compiled HTML samples: `examples/cookbook/h05_mcmf.html`, `frog1_dp.html`, `convex_hull_andrew.html`

## Test method

Static code + HTML inspection. Every claim below is tied to a line number and could be verified quickly in a browser.

## Widget feature inventory (actual, from `emitter.py:751–815`)

The rendered DOM for a scene is:

```
<div class="scriba-widget" id="..." tabindex="0">
  <div class="scriba-controls">
    <button class="scriba-btn-prev" disabled>Prev</button>
    <span class="scriba-step-counter" aria-live="polite" aria-atomic="true">Step 1 / N</span>
    <button class="scriba-btn-next">Next</button>
    <div class="scriba-progress">
      <div class="scriba-dot [active]"></div> ... (one per frame)
    </div>
  </div>
  <div class="scriba-stage"></div>
  <p class="scriba-narration" aria-live="polite"></p>
  <div class="scriba-substory-container"></div>
  <div class="scriba-print-frames" style="display:none"> ... </div>
</div>
```

Inline JS (`emitter.py:768–815`) binds:

- `prev.click` → `show(cur-1)`
- `next.click` → `show(cur+1)`
- `W.keydown` → `ArrowRight` or `Space` advances; `ArrowLeft` goes back.

That is the **entire** widget surface. Nothing else.

## Test results per feature

| # | Feature in prompt scope | Implemented? | Evidence |
|---|---|---|---|
| 1 | **Play button** (autoplay) | **No** | No `btn-play`, no `setInterval`/`requestAnimationFrame`, no autoplay state machine anywhere in `emitter.py`. Grep for `setInterval\|requestAnimationFrame\|autoplay` returns only legacy `docs/legacy/*` demos. |
| 2 | **Pause button** | **No** | Same. There is no timer to pause. |
| 3 | **Step-forward** | Yes (labelled `Next`) | `next.addEventListener('click', …)` at line 808. |
| 4 | **Step-back** | Yes (labelled `Prev`) | `prev.addEventListener('click', …)` at line 807. |
| 5 | **Progress bar scrubbing** | **No scrubbing** | `.scriba-progress` is a row of non-interactive `<div class="scriba-dot">` elements. They have no click handler, no `role="button"`, no `tabindex`. They are a visual progress indicator only. Frame counter (`Step i / N`) is present and live-announced. |
| 6 | **Keyboard shortcuts** | Partial | `ArrowRight` and `Space` advance; `ArrowLeft` rewinds. **Missing:** `Home`/`End` (first/last frame), `ArrowUp`/`ArrowDown`, number keys to jump, and `Space`-as-play-pause (because there is no play state). |
| 7 | **Reduced-motion** | Partial — see note | `scriba-animation.css:57` kills the five `.scriba-anim-*` utility classes. `scriba-scene-primitives.css:435` zeros `transition-duration` and `animation-duration` globally. **But** the static CSS file is not the one actually shipped to users — see *Bugs* below. The inline CSS block in `render.py` (which is what cookbook HTMLs actually carry) contains **no `prefers-reduced-motion` media query** and an unconditional `.scriba-stage svg, .scriba-narration { transition: opacity .2s ease; }` rule at line 100–102 of every compiled HTML. A reduced-motion user still sees that fade. |
| 8 | **Accessibility** | Partial — see a11y section | |
| 9 | **Frame-label jump UI** | **No** | `data-label` is emitted on `.scriba-print-frame` for the print-only fallback, and emitter validates label uniqueness (E1005), but the interactive widget has no jump-to-label control, no dropdown, no `<select>`, no anchor-hash navigation binding inside `show()`. Labels are a print/diagram feature only. |
| 10 | **KaTeX in narration** | Yes, server-rendered | `render.py::_make_inline_tex_callback` expands `$...$` via `TexRenderer._render_inline` into serialized KaTeX HTML, which is stored verbatim in `FrameData.narration_html`. The JS then assigns it via `narr.innerHTML=frames[i].narration`, which does parse `<span class="katex">` correctly. `frog1_dp.html` contains 48 `katex-html` spans; `convex_hull_andrew.html` ships too. The CDN `katex.min.css` is linked for font files (line 160 of the template). Rendering is correct for the pre-serialized math. |

## A11y findings

From `emitter.py:751–767`:

| Check | Status |
|---|---|
| Widget container is focusable (`tabindex="0"`) | Yes |
| Focus ring on `.scriba-widget:focus-visible` | Yes in `static/scriba-scene-primitives.css:425`, **but the static CSS isn't used by the cookbook pipeline** (see Bug W1). The inline CSS block in `render.py` has no focus-visible rule on `.scriba-widget`. A keyboard user who tabs in will see the browser default outline at best, nothing at worst. |
| `aria-label` on Prev/Next buttons | **No**. Buttons have only the visible text `"Prev"` / `"Next"`. Screen readers will read those, which is acceptable but unlabelled for "what does this do in this scene" context. |
| `aria-label` on `.scriba-dot` | **No**. Dots have no role, no label, no text. A screen reader user has no idea they exist. Fine if they're purely decorative, but combined with the counter that's probably OK. |
| `aria-live` on step counter | Yes (`aria-live="polite" aria-atomic="true"`). When `ctr.textContent` changes on frame advance, SR will announce `"Step 3 / 7"`. |
| `aria-live` on narration | Yes (`aria-live="polite"`). The change will be announced on frame advance. |
| `role="region"` or `aria-label` on the widget itself | **No**. The widget container has no `role`, no `aria-label`, no `aria-labelledby`. A screen-reader landmark list won't show it. |
| Keyboard focus trap / tab order | Natural. Prev → step-counter (not focusable) → Next → dots (not focusable). Sensible. |
| `Space` key intercepted globally | Yes. `e.preventDefault()` on line 810 blocks space from scrolling. Correct inside the widget, but because `Space` is bound to `W.addEventListener('keydown', …)`, it only fires when the widget or a child has focus. Good. |
| High-contrast / forced-colors handling | Not addressed. |

## Bugs found (with severity)

### W1. Static CSS files are orphaned from the cookbook render pipeline — MEDIUM

`scriba/animation/static/scriba-animation.css` and `scriba/animation/static/scriba-scene-primitives.css` together contain 593 lines of well-considered widget CSS including focus rings, reduced-motion handling, print styles, dark-mode tokens, and tokens like `--scriba-widget-focus-ring`. **None of this CSS reaches the compiled cookbook output.** `render.py:58+` carries its own `HTML_TEMPLATE` with ~150 lines of hand-rolled inline styles and a different, partial rule set. Confirmed by grepping `examples/cookbook/h05_mcmf.html` for `scriba-btn`, `scriba-widget:focus-visible`, `prefers-reduced-motion` — all absent.

Consequence: every feature that lives only in the static CSS (focus ring, global reduced-motion override, print hiding of substory controls, `--scriba-widget-shadow` token) is not delivered to end users of the primary render path. Two parallel CSS truths exist.

### W2. No reduced-motion fallback in the shipped CSS — MEDIUM

Compiled cookbook HTML has an unconditional

```
.scriba-stage svg, .scriba-narration { transition: opacity .2s ease; }
```

(`h05_mcmf.html:100–102`) and no `@media (prefers-reduced-motion: reduce)` block. A user with OS-level reduced-motion still sees fades on every frame advance. Small magnitude but the prompt explicitly asks about this.

### W3. No `aria-label` on Prev/Next, no role/label on the widget — LOW

Functional for sighted users. Unhelpful for assistive tech in a document with multiple scenes ("which Prev?"). Easy fix: add `aria-label="Previous frame"` / `"Next frame"` to buttons, `role="group" aria-label="Animation step controls"` to `.scriba-controls`, and `aria-label="{scene_label} animation"` to the widget root.

### W4. Keydown handler loses focus after re-injection of stage SVG — LOW

`show(i)` replaces `stage.innerHTML` on every step. If focus was on an interactive element inside the SVG (there aren't any today, but substory widgets are swapped in via `subC.innerHTML`), that element's focus is silently lost. No focus restore to `W` or any anchor. Not currently observable because substory widgets don't take focus, but latent.

### W5. Progress dots are presented but not scrubbable — LOW→MEDIUM (depends on intent)

The prompt calls out "progress bar — scrubbing works?". The dots are not interactive. If the product intends scrubbing, this is a feature gap. If the dots are purely a position indicator, this is fine — but then they should have `aria-hidden="true"` to avoid SR clutter.

### W6. `Space` key binding collides with assistive use — LOW

`Space` advances one frame. For screen-reader users who rely on `Space` to activate the currently focused button (e.g. Prev), `e.preventDefault()` on the widget-level `keydown` fires **before** the button's click handler would get a chance via synthetic click. Because the check is on `W`, not on the button, both behaviours happen: button is clicked *and* frame advances. Double-advance on Next, effective no-op on Prev. Not verified dynamically but the code path is there.

### W7. No frame-label jump UI — feature gap, see below

Not a bug per se; the ruleset (per `docs/archive/audit-2026-04-09.md`) documents labels as an authoring affordance but doesn't require interactive jumping. Noted as gap, not bug.

## Feature gaps surfaced

The prompt lists ten features. The implemented widget supports **four** of them in full (`Next`, `Prev`, counter, narration+KaTeX), **two** partially (keyboard, reduced-motion), and **four** not at all (play, pause, scrub, label-jump). The gap matters because:

1. The auditor prompt implies play/pause exists. It does not. Either the prompt is stale or this is a documentation / marketing drift bug. I'd recommend clarifying the widget's intended scope in `docs/spec/ruleset.md` and in the README so future audits don't chase a feature that was never built.
2. The static CSS file (`scriba-animation.css`, `scriba-scene-primitives.css`) *does* read like a more ambitious widget (tokens for `--scriba-widget-focus-ring`, `--scriba-progress-height`, print-mode handling of substory controls). The static CSS is ahead of the JS and ahead of `render.py`. That gap is technical debt.
3. If a dynamic test harness is added later, the smallest useful suite is:
   - click Next 3 times, expect counter `"Step 4 / N"` and narration text change.
   - click Prev, expect counter back.
   - press `ArrowRight`, expect advance.
   - press `Home`/`End`, expect no-op (documents the gap).
   - boot browser with `--force-prefers-reduced-motion`, screenshot first and second frame transition, check for visible fade (expected: fade still happens → bug W2).
   - axe-core on a compiled page, expect zero critical a11y violations.

## Severity summary

| Severity | Count | Items |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 2 | W1 (orphaned static CSS), W2 (no reduced-motion in shipped CSS) |
| LOW | 4 | W3 (aria labels), W4 (focus loss), W5 (non-scrubbable dots if intended interactive), W6 (Space collision) |
| Gaps | 4 | play, pause, scrubbing, frame-label jump — all absent by design or omission |

No blocking issues. The widget is functionally correct for its actual (reduced) scope: step through a pre-rendered frame list with Prev/Next and two arrow keys. The biggest actionable finding is **W1**: the well-written static CSS in `scriba/animation/static/` is not wired into the primary render pipeline, so every improvement made there has been shadowed by the inline `HTML_TEMPLATE` in `render.py`. Reconciling those two CSS sources would close W1, W2, and the focus-ring half of W3 in a single change.

Dynamic verification in a real browser is still owed. Recommend adding `pytest-playwright` to dev deps and writing ~20 lines of integration test against one compiled cookbook HTML to lock in the behaviour listed above before the next release.
