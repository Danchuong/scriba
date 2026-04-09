# 01 — Animatable Equations as First-Class Scriba Primitives

> Status: research recommendation
> Audience: Scriba compiler team
> Scope: how to turn LaTeX math from a static blob inside `narrate` strings into an addressable, step-animatable shape primitive.

## Executive Summary

Use **KaTeX** as the build-time renderer, emit its native `\htmlId{name}{...}` trust macro wrapped behind a Scriba `\scribahl{id}{expr}` author macro, and render equations as a **side-car SVG positioned next to the D2 diagram** (not inside `<foreignObject>`), with animation driven by **CSS class toggling** on `[data-tex-id="..."]` selectors keyed off the step controller. KaTeX wins because it is the only renderer with (a) synchronous sub-millisecond SSR from a Python/Node subprocess, (b) a stable, documented ID-injection macro, and (c) an output format (HTML + MathML) whose DOM structure survives rebuilds byte-for-byte when the source is unchanged.

## Comparison: KaTeX vs MathJax v4 vs Temml vs typst.ts

| Criterion              | **KaTeX 0.16**                                     | **MathJax v4**                                  | **Temml**                                 | **typst.ts**                              |
|------------------------|----------------------------------------------------|-------------------------------------------------|-------------------------------------------|-------------------------------------------|
| Sub-expression IDs     | `\htmlId{name}{...}` + `\htmlClass` + `\htmlData` (trust-gated) | `\cssId{name}{...}`, `\href`, `\class`          | Pass-through `\class` to MathML; no id macro out of the box | No native macro; IDs only via post-processing |
| Output format          | HTML+CSS (default) or MathML-only                  | SVG, CHTML, MathML (v4 modular)                 | MathML (+ optional CSS)                   | SVG (typst frame)                          |
| SSR speed (per eq)     | ~1–3 ms (pure JS, no DOM)                          | ~15–40 ms (heavier runtime)                     | ~2–5 ms                                   | ~20–80 ms (WASM cold, faster warm)         |
| Bundle size (runtime)  | ~280 KB JS + 23 KB CSS + fonts                     | ~800 KB+ modular                                | ~180 KB                                   | ~3–5 MB WASM                               |
| License                | MIT                                                | Apache 2.0                                      | MIT                                       | Apache 2.0                                 |
| Determinism            | Byte-stable output across runs                     | Stable but SVG `id` counters drift on reloads   | Stable                                    | Stable but evolving                        |
| **Recommendation**     | **Pick this.**                                     | Too heavy, slower SSR, nondeterministic counters | Viable fallback if you go MathML-first    | Too immature for CP editorial in 2026      |

KaTeX docs confirm `\htmlId` is enabled when the renderer is invoked with `trust: true` (or a predicate allowing `htmlId`) and `strict: false` — see https://katex.org/docs/supported.html#html. MathJax v4's `\cssId` is documented at https://docs.mathjax.org/en/latest/input/tex/extensions/html.html but requires loading the `html` TeX extension and does not produce the compact HTML KaTeX does. Temml (https://temml.org/docs/en/supported) emits MathML and recommends `\class{}{}` for styling, but sub-element addressing depends on Safari/Chromium MathML Core support, which is good in 2026 but still has inconsistencies around `transform` on inner `<mrow>` elements — a deal-breaker for animation.

**Verdict: KaTeX.** It is the only renderer whose output is simultaneously small, deterministic, fast enough to render dozens of equations per compile, and has a documented, first-class mechanism for stamping author-controlled IDs onto sub-trees.

## Macro Layer Proposal

Scriba authors should never see raw `\htmlId`. Instead, Scriba exposes a single editorial macro `\hl` (highlight) plus a `\term` alias for semantic clarity. The compiler's TeX preprocessor rewrites these into KaTeX trust macros before invocation.

**Scriba source:**

```scriba
equation E = "$
  T(n) \;=\; \hl{recurse}{2\,T(n/2)} \;+\; \hl{merge}{\Theta(n)}
$"

step "split" {
  recolor E.term("recurse") state=current
}
step "combine" {
  recolor E.term("merge") state=current
  recolor E.term("recurse") state=done
}
```

**Compiler rewrite (pre-KaTeX):**

```tex
T(n) \;=\; \htmlId{E__recurse}{\htmlClass{tex-term}{2\,T(n/2)}}
      \;+\; \htmlId{E__merge}{\htmlClass{tex-term}{\Theta(n)}}
```

**Rendered KaTeX output (abbreviated):**

```html
<span class="katex" data-scriba-eq="E">
  <span class="katex-html" aria-hidden="true">
    …T(n) = …
    <span id="E__recurse" class="tex-term">
      <span class="mord">2</span><span class="mord">T</span>…
    </span>
    +
    <span id="E__merge" class="tex-term">…</span>
  </span>
</span>
```

The step controller then does `document.querySelector('#E__recurse').classList.add('state-current')`. The namespacing `E__<term>` prevents collisions when multiple equations share term names and makes the source map trivially reversible.

Precedents worth noting: Observable's `tex` display uses KaTeX but doesn't expose IDs; RevealJS's math plugin is a thin KaTeX wrapper; 3Blue1Brown's Manim bakes `TexMobject` sub-mobjects by LaTeX group parsing, which we deliberately avoid — author-declared IDs are less magical and less fragile than automatic group inference.

## Animation Strategy

**Decision: CSS class toggling on named IDs, driven by the existing step controller. No SMIL, no WAAPI-per-element.**

Rationale:

1. KaTeX output is HTML spans, not SVG paths — `<animate>` doesn't apply. Even if we forced MathML/SVG output, SMIL is deprecated in Chromium's roadmap and Safari's MathML doesn't honor it reliably.
2. CSS transitions on `color`, `background-color`, `opacity`, and `transform` are compositor-friendly (matches the repo's `web/performance.md` guidance on animatable properties). Avoid animating `font-size`, `padding`, or layout.
3. The step controller already toggles classes on D2 shapes for `recolor`; reusing the same `state-current | state-done | state-dim` class vocabulary means zero new runtime code — only new CSS rules scoped to `.tex-term`.
4. Per-equation transition timing is controlled by a single CSS custom property `--scriba-tex-duration` tied to the existing `--duration-normal` token.

```css
.tex-term { transition: color var(--duration-normal) var(--ease-out-expo),
                        background-color var(--duration-normal) var(--ease-out-expo); }
.tex-term.state-current { color: var(--color-accent); background: var(--color-accent-wash); }
.tex-term.state-done    { color: var(--color-muted); }
.tex-term.state-dim     { opacity: 0.35; }
```

## Pipeline Integration

Equations render **parallel to D2**, not inside it. D2's SVG label HTML support is lossy (it rewrites inner IDs and escapes attributes), and `<foreignObject>` inside a D2-emitted SVG breaks when the SVG is later inlined or rasterized. Instead, the equation primitive compiles to a sibling DOM node that the layout engine positions against a D2 shape's bounding box at mount time.

```
Scriba IR
   │
   ├── D2 shapes ───► d2 CLI ───► diagram.svg ──┐
   │                                            │
   └── equation nodes ──► tex preprocess        │
                           (\hl → \htmlId)      ▼
                              │           ┌───────────────┐
                              ▼           │ editorial DOM │
                         KaTeX SSR ─────► │  <figure>     │
                       (HTML + MathML)    │   <svg d2/>   │
                                          │   <div eq/>×N │
                                          └───────────────┘
                                                 │
                                      step controller toggles
                                      [data-tex-id], [data-d2-id]
```

The compiler emits a single editorial HTML fragment per scene: one inline D2 SVG plus one `<div class="scriba-eq" data-scriba-eq="E">` per equation, absolutely positioned relative to the scene's `<figure>` using coordinates from the IR. Both equation and D2 DOM share a coordinate space and a single step controller.

## Source Map

Three-level map, serialized to `scene.scriba.map.json`:

```
scriba_source.scriba:L42:C7  ─►  equation E, term "recurse"
                              ─►  #E__recurse
                              ─►  katex span[data-scriba-origin="42:7"]
```

Implementation: the `\hl{id}{expr}` preprocessor emits both `\htmlId{E__id}` **and** `\htmlData{origin=42:7}{...}`. KaTeX's `\htmlData` macro becomes `data-origin="42:7"` on the wrapping span, so devtools inspection round-trips back to the Scriba source line without a separate lookup table. The JSON map is generated for editor tooling (hover-to-locate).

## Open Risks

1. **KaTeX macro gaps.** `\htmlId` cannot wrap certain constructs cleanly (e.g., a single subscript inside `\sum`). We'll need a linter that warns when `\hl` is applied to a token KaTeX cannot wrap, and falls back to `\htmlClass` + generated ordinal IDs.
2. **Font loading FOUT.** KaTeX fonts must be preloaded or the equation layout shifts on first render, violating CLS budgets. Needs explicit `<link rel="preload">` for `KaTeX_Main-Regular.woff2` and the math-italic variant.
3. **Positioning under resize.** The side-car DOM approach requires re-measuring on viewport resize. Use `ResizeObserver`, debounced, not scroll/resize listeners.
4. **Copy-paste fidelity.** KaTeX HTML output is visually correct but copies as nonsense. Ship MathML alongside (`output: "htmlAndMathml"`) so screen readers and copy-paste both work.
5. **Dark theme contrast on `.state-dim`.** 0.35 opacity may drop contrast below WCAG AA on the dark theme — verify with axe.

## Next-Step Implementation Tasks

1. **`scriba/tex/preprocess.py`** — add a tokenizer that rewrites `\hl{id}{expr}` → `\htmlId{<eq>__<id>}{\htmlClass{tex-term}{\htmlData{origin=L:C}{expr}}}`; carries source positions through.
2. **`scriba/renderers/katex_renderer.py`** — call `katex` via Node subprocess with `{trust: true, strict: "ignore", output: "htmlAndMathml", macros: {...}}`; cache by content hash (see `content-hash-cache-pattern`).
3. **Equation IR node** — introduce `Equation(id, tex, terms, anchor)` in the IR; teach the layout engine to emit a sibling DOM node, not a D2 shape.
4. **Step controller extension** — generalize the existing `recolor` action dispatcher to accept `tex` targets (`E.term("recurse")`) and toggle `state-*` classes on `#<eq>__<term>`.
5. **Editorial CSS tokens** — add `.tex-term` + `.state-current|done|dim` rules to `styles/tokens.css`, wired to existing duration/easing tokens; preload KaTeX fonts in the scene template.
