# O6 — Unique Selling Proposition & Launch Messaging

> Source of truth for what Scriba is: [`../environments.md`](../spec/environments.md). This file freezes the positioning that lands on the README, the home page, and the HN post.

## 1. One-sentence USP

> Scriba adds two LaTeX environments — `\begin{animation}` and `\begin{diagram}` — that compile CP editorial visualizations into **zero-JavaScript static SVG**. The output drops into any site, email, PDF, or print medium and renders identically.

## 2. Five capabilities nobody else combines

1. **LaTeX-native, zero runtime.** Authors write regular `.tex`. Output is pre-rendered `<figure><ol><li><svg/><p/></li>…</ol></figure>`. No `<script>`, no custom element, no hydration. Works in email clients, print stylesheets, PDF exporters, RSS readers, and archive.org.
2. **Declarative CP-domain primitives.** `array`, `grid`, `graph`, `tree`, `dptable`, `code` are first-class shapes with semantic states. You describe what an element *means* (active, visited, candidate, rejected, accepted) instead of what color it should be.
3. **Narration-synced step frames.** Each `\step` becomes its own `<li class="scriba-frame">` with its own rendered SVG and its own `\narrate{...}` paragraph. Screen readers walk frames in order. Print fallback is a vertical filmstrip.
4. **Build-time determinism via sandboxed Starlark.** `\compute{...}` runs at build time in a subprocess worker with no I/O, no time, no randomness. Same source + same Scriba version ⇒ byte-identical HTML, so consumer caches never drift.
5. **Accessible by construction.** Semantic `<figure>/<ol>/<li>/<p>`, real text narration (not baked into the SVG), ARIA labels from the environment `label` option, reduced-motion safe because there is no motion.

## 3. Killer demos (LaTeX env code)

All three demos are written as `\begin{animation}` blocks inside a normal `.tex` file. LOC is the number of lines inside the environment, excluding the surrounding problem statement prose.

| Demo | Before | After (Scriba) |
|---|---|---|
| **Binary search over a sorted array** | ~200 LOC hand-authored SVG + JS step controller | ~25 lines inside `\begin{animation}` |
| **BFS from a source node on a small graph** | 30-minute screen recording + manual captions | ~40 lines inside `\begin{animation}` authored in ~4 minutes |
| **DP table fill for a classic knapsack** | ~300 LOC matplotlib + imageio GIF export | ~20 lines inside `\begin{animation}` |

Capture real byte-size and real author-time numbers against the canon cookbook before launch. Do not ship the post with estimated numbers.

## 4. Honest non-coverage

Scriba does **not** try to be:

- A continuous-math animation engine → use Manim.
- A general graph layout tool for large graphs (>100 nodes) → use Cytoscape, Gephi, or hand-written D3.
- An interactive explorer with click/hover state → use custom JS; Scriba is intentionally static.
- A slide deck authoring tool → use Beamer or reveal.js.
- A video generator → output is HTML+SVG, not mp4.

Saying no to these loudly is part of the pitch. The product is sharper for it.

## 5. Adoption path

1. **ojcloud** — internal dogfood. First real editorial cut during Phase 6.
2. **DMOJ** — large open-source Django OJ. Q2 pitch once the Django integration example has been battle-tested on ojcloud.
3. **cp-algorithms.com** — canonical CP reference site, mostly static content, natural fit for pre-compiled HTML. Q3 pitch.
4. **Codeforces blog authors** — Scriba output can be pasted into Codeforces blog posts because the CSS is self-contained and there is no runtime. Organic adoption target once the cookbook is live.

## 6. Launch messaging

### HN title options
- "Scriba: Two LaTeX environments that compile algorithm animations to zero-JS SVG"
- "Show HN: Scriba — `\begin{animation}` for competitive programming editorials"

### Twitter thread skeleton (10 tweets)
1. Hook with the binary-search animation rendered in a screenshot. "This is 25 lines of LaTeX. No JS. No runtime. It renders in your email client."
2. Show the source side-by-side.
3. Explain the filmstrip model — one `<li>` per `\step`.
4. Primitives: array, grid, graph, tree, dptable, code.
5. Semantic states: active, visited, candidate, rejected, accepted, default.
6. Starlark `\compute{}` for build-time determinism.
7. Drop the compiled HTML into a Django template: literally `{{ problem.html|safe }}`.
8. Prints as a vertical filmstrip. Works in Thunderbird. Works in a PDF export.
9. `pip install scriba-tex`, 6 lines of Python, done.
10. Repo + docs links.

### README first three paragraphs
1. **Problem statement.** CP editorials need step-by-step visualizations. Hand-authored SVG is a nightmare. Matplotlib GIFs are inaccessible. Manim is overkill and non-text. JS widgets break in email and print.
2. **Scriba's answer.** Two new LaTeX environments. Author in `.tex`. Get back static HTML + inline SVG. Zero JavaScript. Works everywhere.
3. **Install and hello.** `pip install scriba-tex`, 6 lines of Python to register the renderers, 25 lines of LaTeX for a binary-search animation.

## 7. What the messaging does *not* say

The pre-pivot pitch leaned on "framework-agnostic Lit 3 custom element". That language is **dead**. Do not reintroduce it in any launch copy. The new pitch is stronger precisely because "no runtime" is more defensible than "framework-agnostic runtime".

Similarly, do not mention:
- `scriba init`, `scriba dev`, `scriba build`
- A `.scriba` file format
- VS Code language extension
- Hot reload / dev server
- `<scriba-widget>` custom element

The product is smaller, sharper, and easier to explain without any of those.
