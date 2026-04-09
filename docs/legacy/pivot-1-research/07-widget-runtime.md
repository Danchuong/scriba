# 07 — Widget Runtime Substrate

> Research into the runtime layer Scriba compiles widgets onto. The question
> is not "which framework do we like"; it is "what is the smallest substrate
> that gives us CSS isolation, SVG event wiring, sub-widget composition, and
> a clean hydration story — without betraying Scriba's promise that a compiled
> widget is a single HTML file you can email to a friend?"

## Executive summary

**Recommendation: Lit 3 inside a single Custom Element per widget, emitted by
the Scriba compiler as a self-contained `<scriba-widget>` tag with an inline
`<script type="module">` that defines the element and registers it.**

Rationale, compressed:

1. **Shadow DOM is non-negotiable.** The cookbook already shows that the
   moment we put two widgets on one editorial page, CSS class collisions
   (`.step-active`, `.narration`, `.dp-cell`) will bite. Shadow DOM is the
   only CSS isolation primitive the platform gives us for free. Lit is the
   thinnest ergonomic wrapper around it (Lit 3 is ~5 KB min+gzip, MIT,
   Google-maintained — see `https://lit.dev/docs/`).
2. **Custom Elements give us recursive composition for free.** A parent
   `<scriba-widget>` can contain a child `<scriba-widget>` in a slot or in
   an inset without any framework-level "portal" or "subtree" concept. The
   drill-down-into-a-DP-cell feature falls out of the element model.
3. **Lit does not own your SVG.** Its template system is string-based
   tagged templates, but it also happily attaches to pre-rendered DOM via
   `@eventName` binding on existing nodes, and the compiler can emit the
   SVG literally inside the template. D2's SVG survives untouched — Lit
   only wires listeners and toggles `data-step` attributes.
4. **No bundler required.** Lit ships as a browser-native ES module on
   jsDelivr / esm.sh. Scriba can keep its zero-JS-toolchain story: the
   compiler emits HTML that does
   `import {LitElement, html} from 'https://esm.sh/lit@3'` — or, for the
   "email to a friend" path, inlines the ~5 KB runtime directly. Both are
   a build-time switch, not a framework change.
5. **Signals are optional, not load-bearing.** Lit's reactive properties
   cover `currentStep`, `hovered`, `branch` without needing a separate
   state library. If we outgrow them, `@lit-labs/signals` is a drop-in
   and still under the 10 KB budget.

Every competing option either (a) requires a bundler (Svelte, Stencil,
Solid's compiler), (b) does not give Shadow DOM for free (Preact, Alpine,
petite-vue), or (c) keeps us in the vanilla-DOM swamp that already creaks
at two widgets per page.

## Comparison matrix

Scored on a 0–2 scale per criterion (0 = fails, 1 = workable, 2 = good).
Bundle sizes are min+gzip, runtime only, from each project's published
docs and `bundlephobia` at time of writing.

| Option              | Shadow DOM | Bundle    | SSR/hydrate | State model     | Raw-SVG interop | Sub-widgets | DX / debuggable | License | Build pipeline | Total |
|---------------------|-----------:|----------:|------------:|----------------:|----------------:|------------:|----------------:|--------:|---------------:|------:|
| Vanilla DOM + inline| 1 (manual) | 0 KB      | 2           | 1 (imperative)  | 2               | 1           | 2               | n/a     | 2 (none)       | 11    |
| **Lit 3**           | **2**      | **~5 KB** | **2**       | **2 (reactive)**| **2**           | **2**       | **2**           | **BSD** | **2 (none req)**| **17** |
| Preact + signals    | 0          | ~4 KB     | 2           | 2               | 1 (VDOM fights) | 1           | 2               | MIT     | 1 (JSX needs)  | 10    |
| Solid.js            | 0          | ~7 KB     | 2           | 2 (fine-grain)  | 1               | 1           | 1 (compiled)    | MIT     | 0 (compiler)   | 9     |
| Svelte 5            | 1 (opt-in) | ~0 (compiled per comp) | 2 | 2            | 1               | 1           | 1               | MIT     | 0 (compiler)   | 9     |
| Alpine.js           | 0          | ~15 KB    | 1           | 1 (attr-based)  | 2               | 0           | 2               | MIT     | 2              | 9     |
| HTMX + _hyperscript | 0          | ~14 KB    | 0 (server)  | 0               | 1               | 0           | 1               | BSD     | 0 (needs server)| 4    |
| petite-vue          | 0          | ~6 KB     | 1           | 2               | 1               | 0           | 2               | MIT     | 2              | 9     |
| Stencil.js          | 2          | ~10 KB    | 2           | 2               | 2               | 2           | 1 (heavy compiler) | MIT  | 0 (compiler)   | 12    |
| Custom mini-FW      | 2          | ~1–2 KB   | 2           | 1               | 2               | 2           | 1 (we own bugs) | n/a     | 2              | 13    |

Lit wins cleanly. The interesting runner-up is **a custom Web-Components
mini-framework** — it scores 13 and has the smallest bundle — but trades
~2 KB of saved runtime for "we maintain reactivity, template diffing,
and attribute reflection ourselves forever". Lit has already solved those
problems and is 5 KB; the 3 KB saving is not worth the yak.

## Top 3 deep dive

### 1. Lit 3 (recommended)

Lit (`https://lit.dev/docs/`) is a ~5 KB base class over the Custom
Elements v1 + Shadow DOM v1 + Template Literal platform APIs.

- **CSS isolation:** each `LitElement` opens a shadow root by default.
  Styles defined via `static styles = css\`...\`` are scoped to the
  instance. Two `<scriba-widget>` instances on the same page cannot
  leak styles into each other. This is the single most important
  property.
- **SVG interop:** `html\`${unsafeSVG(d2Output)}\`` from
  `lit/directives/unsafe-svg.js` injects the D2-emitted SVG literally,
  preserving IDs and classes. Event wiring happens by delegating on the
  host: `@click=${this.onCellClick}` with an `e.target.closest('[data-cell]')`
  check. No VDOM, no node recreation — the SVG DOM we emit at compile
  time is the SVG DOM at runtime.
- **State:** `@property({type: Number}) currentStep = 0` gives us a
  reactive property that auto-rerenders on change. `@state()` for local
  UI state (hovered cell, open inset). `prefers-reduced-motion` is a
  one-liner in the render method.
- **Sub-widgets:** because `<scriba-widget>` is a real element, a parent
  widget can render `<scriba-widget src="child" step="0"></scriba-widget>`
  in an inset and it Just Works — independent shadow root, independent
  state, independent keyboard focus scope.
- **No bundler required.** Lit publishes browser-ready ESM. The compiler
  can emit either `import {LitElement} from 'https://esm.sh/lit@3'`
  (network build) or inline the 5 KB runtime once per HTML file (offline
  build). This preserves the email-to-a-friend property.
- **License:** BSD-3-Clause.
- **Cost:** ~5 KB gzipped per page (not per widget — one import, N
  instances). Well under the 10 KB target.

### 2. Custom mini-framework on raw Custom Elements

Write ~200 lines of framework: a `ScribaWidget` base class extending
`HTMLElement`, an `observedAttributes` wiring, a tiny reactive-property
decorator-less helper, and a `render()` hook that sets `innerHTML` on
the shadow root.

- **Pros:** absolute minimum bundle (~1–2 KB), no external dep, total
  control.
- **Cons:** we will reinvent Lit's `html` tagged template and its
  directives (especially `unsafeSVG`, `classMap`, `styleMap`, `repeat`).
  Every bug is ours. The "email to a friend" file will contain our
  framework inline anyway, so the 3 KB we saved is invisible to the
  user.
- **Verdict:** only compelling if we have a hard religious objection to
  third-party runtime code. We don't.

### 3. Vanilla DOM + inline JS (status quo)

The current cookbook pattern (see `docs/scriba/cookbook/06-frog1-dp/output.html`)
uses a single `<div class="widget">`, global CSS, and an IIFE that
wires `currentStep`. It is beautifully simple.

- **Upper limit:** one widget per page, no hover interactivity beyond
  attribute toggles, no nested widgets. The moment we introduce
  `.step-active` on two widgets in one page, we're done.
- **Could we salvage it with BEM + per-widget ID prefixes?** Yes,
  mechanically. But the compiler now has to mangle every selector,
  every event handler has to qualify by widget ID, and the "drill into
  a sub-widget" feature requires a manual scope stack. At that point
  we've written a worse Lit.
- **Verdict:** good enough for v0.1 cookbook, must evolve.

## Migration plan (vanilla → Lit)

The migration is small because the current compiler output is already
structured per-widget.

1. **Introduce a `ScribaWidget` LitElement base class** in
   `scriba/runtime/base.ts` (or whatever the compiler output directory is).
   It owns: `currentStep`, `totalSteps`, `narration[]`, `stepChanged` event,
   keyboard handler (Left/Right/Space), play/pause, reduced-motion check,
   print-media fallback.
2. **Compiler change:** the widget template that currently emits a
   `<div class="widget">` + `<script>(function(){...})()</script>`
   starts emitting
   `<scriba-widget narration='[...]' total-steps="6"><svg>...</svg></scriba-widget>`
   plus a single module script at the top of the document registering the
   element. The D2 SVG goes into the default slot; the narration panel
   is rendered by the element itself from the JSON attribute.
3. **Runtime loading mode** (build flag):
   - `--runtime=cdn` — emits `import 'https://esm.sh/lit@3'` + our base class.
     ~300 bytes of HTML overhead, needs network.
   - `--runtime=inline` — inlines Lit + base class directly in a
     `<script type="module">` block. Adds ~7 KB per file but the file is
     fully offline (the email-to-a-friend case).
   - Default for the cookbook: `inline`. Default for docs sites: `cdn`
     (one download, cached for all widgets).
4. **Cookbook re-render:** regenerate the six cookbook outputs under
   the new runtime and visually diff. Keep vanilla outputs under
   `cookbook/*/output.vanilla.html` as a regression baseline for one
   release.
5. **Docs update:** `docs/scriba/architecture.md` gets a new section on
   the runtime substrate, with a link to this research doc.

## Bundle budget

| Item                                  | Size (gzip) |
|---------------------------------------|------------:|
| Lit 3 core                            | ~5.0 KB     |
| `unsafeSVG` directive                 | ~0.3 KB     |
| Scriba `ScribaWidget` base class      | ~1.5 KB     |
| Per-widget narration JSON             | variable    |
| Per-widget SVG (D2 output)            | variable    |
| **Runtime total (one page, N widgets)** | **~7 KB**  |

Under the 10 KB runtime budget with headroom for one optional feature
library (e.g. `@lit-labs/signals` if derived state grows teeth).

## Sub-widget composition sketch

```html
<scriba-widget id="frog1-main" total-steps="7">
  <svg slot="stage">...D2 output with data-cell attributes...</svg>

  <!-- inset that pops up when a DP cell is clicked -->
  <scriba-widget slot="inset" id="frog1-cell-3"
                 total-steps="2"
                 parent-step-binding="3">
    <svg slot="stage">...zoomed memo trace for cell 3...</svg>
  </scriba-widget>
</scriba-widget>
```

The parent listens for its own `@click` on `[data-cell]`, toggles the
inset's `hidden` attribute, and optionally forwards `currentStep` via a
`parent-step-binding` attribute. Because each `<scriba-widget>` has its
own shadow root, the child's `.step-active` class cannot touch the
parent's. Keyboard focus is handled by `tabindex="0"` on the host plus
`delegatesFocus: true` in the shadow root options — the platform
handles focus trapping.

## Risks

1. **Build pipeline complexity.** Zero. Lit is a runtime import; the
   compiler stays a pure text transform. This is the main reason Solid,
   Svelte, and Stencil lost — they all require a JS build step we do
   not want to own.
2. **Inline-runtime file size.** ~7 KB added to every "offline" widget
   HTML. Acceptable: the typical cookbook widget is already 30–80 KB
   because of the D2 SVG.
3. **Shadow DOM + print CSS.** Shadow DOM famously interacts oddly
   with `@media print`. Mitigation: the base class emits an additional
   `<img>` (the "key frame" static PNG the compiler can generate at
   build time) in light DOM, hidden on screen, visible on print. This
   also handles the "reader turns off JS" case.
4. **Debuggability.** Lit templates are plain tagged-template literals
   — no JSX, no compilation — so Chrome DevTools shows exactly what the
   compiler emitted. Better than Svelte or Solid's compiled output.
5. **Vendor risk.** Lit is maintained by Google's Polymer team and has
   been stable since Lit 2 (2021). Low, but noted.

## Implementation tasks

- [ ] Add `scriba/runtime/scriba-widget.ts` — the `ScribaWidget`
      LitElement base class with `currentStep`, keyboard nav, narration
      panel slot, `prefers-reduced-motion`, print fallback, and
      `stepChanged` custom event.
- [ ] Compiler: swap the widget template from the current
      `<div class="widget">` + IIFE pattern to
      `<scriba-widget>` + single module import. Gate on a
      `--runtime={cdn,inline}` flag; default `inline` to preserve the
      email-to-a-friend property.
- [ ] Add `unsafeSVG`-based slot wiring so D2 output is injected
      verbatim with event delegation on `[data-cell]`.
- [ ] Regenerate all six cookbook outputs under the new runtime, keep
      `output.vanilla.html` baselines for one release, visual-diff them.
- [ ] Write `docs/scriba/architecture/runtime.md` documenting the
      `ScribaWidget` contract (attributes, slots, events) so future
      emitters (beyond D2+KaTeX) know the integration surface.

---

**References**

- Lit docs: https://lit.dev/docs/
- `unsafeSVG` directive: https://lit.dev/docs/api/directives/#unsafeSVG
- Custom Elements v1 spec: https://html.spec.whatwg.org/multipage/custom-elements.html
- Shadow DOM v1 spec: https://dom.spec.whatwg.org/#shadow-trees
- Preact signals: https://preactjs.com/guide/v10/signals/
- Solid.js: https://www.solidjs.com/docs/latest
- Svelte 5 runes: https://svelte.dev/docs/svelte/what-are-runes
- Stencil: https://stenciljs.com/docs/introduction
- Alpine.js: https://alpinejs.dev/start-here
- petite-vue: https://github.com/vuejs/petite-vue
