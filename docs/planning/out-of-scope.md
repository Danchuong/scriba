# 06 — Out of Scope

## Purpose

This document is the canonical list of features Scriba explicitly decides
**not** to implement in the v0.2–v0.5 series. It is a reference for
contributor pushback, not a proposal list. Before opening a feature request,
check this file. If the feature is listed here, read the rationale first. If
you still believe the exclusion is wrong, follow the proposal process in §3.

The items below were re-derived for the v0.3 LaTeX-environments model locked
in [`environments.md`](../spec/environments.md) and the editorial
genres catalogued in [`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md).

---

## Non-goals

### 1. Runtime JavaScript of any kind (static mode)

> **As of v0.8.x (2026-04-18 note):** This constraint applies to **static/filmstrip mode only** (`--static-mode`). Interactive mode (default in v0.8.x) emits a JS runtime (`scriba.<hash>.js`) that is inline by default and external in the recommended configuration. See `docs/csp-deployment.md` for the three deployment modes. The "zero `<script>`" guarantee is preserved in static mode and for `\begin{diagram}` environments.

No Lit 3 widget, no Motion One timeline, no step controller, no keyboard
navigation, no `<script>` emitted by any renderer in the `animation` or
`diagram` plugins in static mode. The HTML output per `environments.md` §8 is a
pure `<figure>` + `<ol>` + inline `<svg>` tree that renders identically in
email, print, PDF export, RSS, and any sanitizer-aware HTML consumer. An
interactive runtime returned in v0.8.x as an opt-in layer (and became the
default in v0.8.x). Rationale: every consumer we have spoken with reads editorials
in contexts (print, email, embedded JS-free shells) where a runtime would
break. A static filmstrip works everywhere.

### 2. Hot-reload dev server / `scriba init|dev|build` CLI

There is no `scriba init` scaffolder, no `scriba dev` preview server, no
`scriba build` bundler. Authors use their existing LaTeX toolchain plus a
one-shot `Pipeline.render()` call. Rationale: Scriba is a library, not a
framework. Authors already have editors, linters, and build systems; adding
a CLI competes with those tools rather than complementing them. The
`examples/` directory shows copy-paste integrations for each common
workflow (plain HTML, Next.js, Astro, mdBook).

### 3. Playground / live preview UI

No web-based playground, no live preview panel, no `scriba.ojcloud.dev/play`
runtime editor. Authors who want a feedback loop run `pytest --snapshot-update`
or a file watcher around their editor. Rationale: a playground is a docs-site
feature, and it brings an entire second code path (browser-side rendering,
bundling, asset serving) that duplicates the backend pipeline. Out of scope
until v1.0 minimum.

### 4. Standalone `.scriba` file format

Environments live inside regular `.tex` files. There is no `.scriba`
extension, no standalone document type, no `front-matter` block. A source
document is always a `.tex` file that the `Pipeline` processes. Rationale:
authors already have `.tex` tooling; inventing a new extension forks the
ecosystem and breaks editor support.

### 5. Nested environments

`\begin{animation}` cannot contain another `\begin{animation}` or
`\begin{diagram}`. A `\begin{diagram}` cannot appear inside
`\begin{animation}`. Parser raises `E1003`. Rationale: the scene-state
model in `environments.md` §6.1 is flat; nesting would require a
stack of `SceneState` contexts and a selector-resolution rule for crossing
scopes. The complexity is not justified by any cookbook use case.

### 6. User-provided custom primitives in v0.3

Only the 6 built-in primitive types from `environments.md` §3.1 are
available: `Array`, `Grid`, `DPTable`, `Graph`, `Tree`, `NumberLine`. There
is no `register_primitive()` API, no plugin registry, no entry-point
discovery mechanism. Rationale: primitives are the visual vocabulary; a
stable set gives consumers predictable output shape and CSS hooks. New
primitives land through a PRD in `docs/scriba/rfcs/` and a Scriba release,
not via third-party code.

### 7. 4D / tensor primitive

`environments.md` §3.1 locks primitives to 1D and 2D layouts. A 4D
or higher-rank tensor primitive with a slice scrubber is **deferred** —
see [`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md) §3.
Rationale: honest 4D visualization requires runtime interaction (slice
selector), which contradicts §1. The best a static filmstrip can do is
animate two fixed 2D slices, which authors already express with two
`DPTable` primitives.

### 8. Splay / treap / red-black rotation morph animations

Tree rotations are animated via discrete `\apply` / `\recolor` /
`\annotate` deltas on the `Tree` primitive. There is no continuous rotation
morph, no "swap parent and child with a tweened path". Rationale: the
editorial value of a rotation is the structural before/after, not the
intermediate trajectory. See `HARD-TO-DISPLAY.md` §7 for the amortized
analysis argument that is genuinely hard and explicitly out of scope.

### 9. FFT butterfly animation, MCMF visualization, Manim-class math

These editorial genres are documented in `HARD-TO-DISPLAY.md` §§4, 5, 8 as
hostile to Scriba's model for different reasons (massive parallelism,
non-local residual graph mutation, continuous derivation). Scriba will
not add first-class primitives or modes to support them. Authors writing
these editorials should embed a pre-rendered image via normal LaTeX
`\includegraphics{...}`, which the TeX plugin already handles.

### 10. Interactive drilldown into DP cells

`HARD-TO-DISPLAY.md` §1 proposes a "recursive callout" primitive that
plays a nested Scriba scene on hover. This requires runtime JavaScript (§1)
and cross-scene coordination (§11). Out of scope for v0.2–v0.5.

### 11. Multi-scene coordination

Each `\begin{animation}` and `\begin{diagram}` is a fully independent
scene. There is no cross-scene variable sharing, no shared timeline, no
"scene A advances when scene B reaches step 5". Rationale: independence is
what keeps the HTML shape static and the content-hash cache correct. Two
animations on the same page scroll independently.

### 12. Sass / SCSS / CSS-in-JS output

Scriba emits plain CSS referencing `--scriba-*` custom properties. No
Sass, no Less, no Stylus, no CSS-in-JS, no styled-components. Rationale:
consumers already use their own styling strategy; Scriba's job is to
expose a stable variable contract (see `environments.md` §9) that
every styling strategy can override with one rule.

### 13. i18n helpers for narration

The Python backend does not translate `\narrate{...}` content. Authors
write narration in one language per environment. If an editorial needs
two languages, the author writes two separate `\begin{animation}`
environments (one per language) and the host page decides which to render.
Rationale: machine translation would be both slow and inaccurate for
technical prose; manual translation is the author's job and does not
belong inside a rendering library.

### 14. Markdown, AsciiMath, MathML output

Inherited from v0.1: Scriba is a LaTeX renderer. CommonMark, GFM,
AsciiMath, and MathML are out of scope. Consumers who need Markdown run
a Markdown pipeline first and feed the result (or specific fenced blocks)
to Scriba.

### 15. SSR React / Vue / Svelte components

Scriba is backend-only. It ships no JSX, no `.vue`, no `.svelte`, no
component manifest. Consumers in those frameworks render `Document.html`
via the framework's raw-HTML escape (`dangerouslySetInnerHTML`, `v-html`,
`{@html}`) after running the consumer's sanitizer.

### 16. Automatic sanitization inside `render()`

`Pipeline.render()` returns unsanitized HTML. The consumer calls
`bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS,
css_sanitizer=...)` (or `nh3.clean(...)`) once, at the boundary they
already manage for every other piece of HTML on the page.

### 17. Database integration / ORM / migrations

No models, no SQLAlchemy session, no migration helpers. Consumers cache
`Document.html` keyed on `Document.versions + sha256(source)` using
whatever storage they already use.

### 18. In-package caching layer

No `@lru_cache` on `Pipeline.render()`, no Redis integration, no disk
cache. The only caching inside Scriba is at the subprocess worker level
(KaTeX expression results, Starlark environment bindings), which is
invisible to the caller.

### 19. Async API

Scriba 0.x is synchronous. `Pipeline.render()` is a blocking call.
Consumers running async frameworks wrap it in `asyncio.to_thread(...)`.
An `AsyncPipeline` may ship post-1.0 under a separate ADR.

### 20. Windows-native path handling

Targets: Linux and macOS. Contributors may submit Windows fixes;
maintainers will review them; Windows CI is not maintained and is not a
release gate. Consumers on Windows use WSL2 or a Linux container.

### 21. Auto-install of Node.js, Starlark worker binary, or npm packages

Scriba never runs `subprocess.run(["npm", "install", ...])` or any network
fetch at import time. Runtime dependencies (Node.js for KaTeX, the
Starlark worker binary, KaTeX npm package) are declared in documentation
and must be installed by the consumer or by the Homebrew formula shipped
at v0.5.0. Rationale: supply chain safety and reproducible CI.

### 22. HTTP endpoint / Flask Blueprint / FastAPI router inside the package

`examples/` shows how to wire `Pipeline.render()` into a request handler;
the package itself ships no HTTP layer.

### 23. Image processing

`\includegraphics{foo.png}` calls `resource_resolver("foo.png")` and emits
`<img src="..." width="..." height="...">`. Scriba does not resize,
recompress, convert, or OCR. Image optimization is the consumer's CDN or
asset pipeline.

### 24. LaTeX preamble beyond `katex_macros`

`\usepackage{...}`, `\newcommand`, `\def`, `\let` in document content are
not supported. Math-mode macros are provided via the `katex_macros`
constructor argument on `TexRenderer`. Inside a `\begin{animation}` body,
authors use the 12 inner commands from `environments.md` §3, not
arbitrary LaTeX macros.

### 25. Internationalization of error messages

All `E1xxx` error messages and log lines are English. Consumers translate
at the display layer.

### 26. Tailwind / design-system coupling

No Tailwind utility class appears in Scriba's emitted HTML. All visual
tokens live under `--scriba-*` CSS variables per
`environments.md` §9. Consumers using Tailwind add a bridging
stylesheet.

### 27. Font bundling

Scriba ships no font files. KaTeX references the KaTeX math fonts by name;
the consumer installs them through the `katex` npm package.

### 28. Mathematical-semantic validation

The parser validates grammar and selector correctness (balanced braces,
matched environments, known types, known states). It does not validate
that `\frac{1}{2}` is the right ratio in context or that a proof is
logically sound. Semantic validity is an editorial-review concern.

### 29. Real-time collaborative editing

Scriba is a one-shot synchronous render engine. No sessions, no deltas,
no CRDT. Consumers building live preview debounce keystrokes and call
`Pipeline.render()` per save.

### 30. OCR / PDF extraction

Scriba takes text source as input. Consumers extract TeX from PDFs or
images before calling the Pipeline.

### 31. User-provided plugin hook API in 0.x

The `Renderer` protocol exists and is well-defined, but the core team
makes no stability promise across 0.x minor versions. Third-party
`Renderer` implementations will work mechanically; they may break between
releases. A stable third-party plugin API is a post-1.0 consideration.

### 32. Continuous sub-step scrubbing and Starlark randomness

`\compute{...}` Starlark has no `random`, no `time`, no `print` to stdout.
See `environments.md` §5.4. Randomized algorithms like simulated
annealing (`HARD-TO-DISPLAY.md` §9) can be authored with a seeded RNG
injected via `RenderContext.metadata` in v0.6+, but not in v0.3.

---

## How to propose adding something from this list

1. **Open a GitHub issue** with the title `Scope: consider adding <feature>`.
2. **Justify the adequacy gap.** Explain why the feature is not adequately
   addressed by an external tool, consumer-layer composition, or the
   existing Scriba API. Reference the rationale above and explain why it
   no longer holds.
3. **Show adoption signal.** Identify at least two consumer projects that
   would adopt Scriba because of this addition and cannot work around it today.
4. **Core team review.** If the argument is compelling, the feature is
   promoted to an RFC under `docs/scriba/rfcs/` before any code is written.
   The RFC is the gate; a pull request without an approved RFC will be closed.

Features that are not on this list — things simply not mentioned — do not
need this process. Open a normal feature request.

---

## Precedent

Tight, well-defended scopes are the norm in the typesetting and
visualization-library space:

- **KaTeX** limits itself to display and inline math rendering and has
  declined repeated requests to support arbitrary LaTeX packages.
- **Mermaid** restricts itself to a fixed set of diagram types and declines
  to expose a primitive-authoring API.
- **Manim** is a Python library that ships its own runtime and an entire
  video pipeline; Scriba is explicitly the opposite — build-time SVG only,
  no animation runtime — because the CP editorial genre does not need
  video.

Every item on this non-goal list was excluded because adding it would
either impose unacceptable coupling, increase install footprint without
proportional value, or blur the boundary between Scriba's responsibility
and the consumer's. For the full catalogue of editorial genres Scriba
gracefully refuses, see
[`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md).
