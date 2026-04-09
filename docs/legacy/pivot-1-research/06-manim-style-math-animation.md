# 06 — Manim-Style Math Animation: Build-Time Integration Research

**Status:** Research / decision document
**Audience:** Scriba compiler maintainers
**Date:** 2026-04-08
**TL;DR:** **Accept defeat on Manim-style derivations.** None of the surveyed tools fit Scriba's build-time → per-step SVG keyframe → discrete step controller model without substantial glue code that would dwarf the payoff. The gap is better served by (a) extending Agent 1's *animatable equations* primitive for local term-rewriting steps, and (b) a prose + external-video-link convention for the handful of problems where a full 3B1B-grade derivation is genuinely load-bearing.

---

## 1. Executive summary

Scriba's widget model is **discrete, static, SVG-per-step**. A widget is N independent SVG snapshots driven by a step controller. This is the opposite of Manim's model, which is a **continuous timeline rendered to video**. Every tool in this survey either:

1. Targets video/WebGL output and cannot cheaply emit per-step SVG (Manim CE, MathBox, Motion Canvas video export).
2. Is a **runtime** library that renders in the browser from a JS/TS scene description (Motion Canvas runtime, Theatre.js, Framer Motion, Mafs). This violates Scriba's "build-time compile, ship static SVG" invariant.
3. Is a declarative diagram language that can emit SVG but has no notion of **equation term rewriting** (Penrose).
4. Is slideware (reveal.js chalkboard) with no programmatic step extraction.

The one honest win available is narrow: **reuse KaTeX output + a hand-rolled diff/morph pass** driven by Agent 1's animatable-equation primitive. This handles ~80% of the "terms appear, cancel, move" cases (Frog DP, Burnside expansion, Mobius pairs, loop invariants) without adopting any of the tools below. The remaining ~20% — genuine visual-geometric derivations like **FFT butterfly + complex root rotation** — should be served by linking to the existing 3B1B video. Scriba should not try to out-Manim Manim at build time.

---

## 2. Comparison matrix

Legend: Y = yes, native / N = no / P = possible with significant glue.

| Tool | Output | Build-time invocable | Per-step SVG keyframes | Math rewrite semantics | Authoring cost/step | KaTeX/MathJax compat | License |
|---|---|---|---|---|---|---|---|
| Manim Community | MP4/PNG seq | Y (subprocess) | P (PNG per frame, not semantic steps) | N (tween-based, not rewrite) | High (20–50 LOC/step) | Own TeX via LaTeX install | MIT |
| Manim CE Web / WebManim | Experimental WASM | N (unstable) | N | N | High | LaTeX | MIT |
| Motion Canvas | MP4/PNG or runtime canvas | P (CLI render) | N (canvas raster, not SVG) | Partial (code morph, no eqn algebra) | Medium (10–20 LOC) | KaTeX via plugin | MIT |
| reveal.js + chalkboard | HTML runtime | N (slide-time) | N | N | Low but manual | MathJax | MIT |
| Theatre.js | Runtime DOM/SVG timeline | N (editor-driven) | N | N | Medium | Agnostic | Apache-2 |
| Mafs | React runtime | N | N | N (plots, not derivations) | Low | KaTeX | MIT |
| Penrose | SVG (static) | Y (CLI) | N (one diagram, not steps) | N (diagram DSL, no term rewriting) | High (Domain+Style+Substance) | Own | MIT |
| Framer Motion + LaTeX | Runtime DOM | N | N | P (layoutId morph) | Medium | KaTeX | MIT |
| MathBox | WebGL runtime | N | N | N (3D plots) | High | Own | MIT |
| Smile.js / math-morph libs | Runtime SVG | N | N | P | Medium | Varies | Varies |

**Zero tools** satisfy all four of: build-time CLI, SVG output, per-step semantic keyframes, equation term-rewriting. The closest near-miss is **Manim CE** (build-time, can emit PNG sequences), but it is fundamentally a video tool — its "steps" are frames, not editorial steps, and the LaTeX it renders is rasterized into the PNG, breaking Scriba's text-selectable SVG invariant.

---

## 3. Top-3 deep dive

### 3.1 Manim Community Edition

**What integration would look like.** A Scriba compiler pass would shell out to `manim -qk -s scene.py SceneName`, capturing one PNG (or SVG via `--format svg`, which exists but is incomplete and known-broken for `Tex` mobjects) per `self.wait()` checkpoint. A wrapper would translate Scriba's step DSL (`step "cancel term dp[i-1]"`) into a `self.play(Transform(...))` call.

**Why it fails in practice.** (1) Manim requires a **full LaTeX install** (`texlive-full` is 5+ GB) on every build machine — hostile to Vercel/Netlify/CI. (2) SVG export for `Tex` mobjects rasterizes glyphs to `<image>` tags; you lose text selection, searchability, and file-size sanity. (3) The "step" model is `self.play(duration=...)` — continuous tween, not discrete snapshot. Extracting "state at editorial step N" means rendering the full timeline then seeking, which is 10–100× slower than needed. (4) Authoring is notoriously verbose: a Burnside derivation is ~200 lines of Python for five editorial steps. (5) LaTeX ≠ KaTeX: subtle glyph metric differences mean Manim equations will **not match** the surrounding Scriba body text.

**Verdict:** Do not integrate. The dependency weight alone (5 GB LaTeX) disqualifies it.

### 3.2 Motion Canvas

**What integration would look like.** Motion Canvas has a headless renderer (`@motion-canvas/core` + Puppeteer) that can render a scene to MP4 or a PNG sequence from CLI. You'd write one `.tsx` scene per editorial step or use `yield* waitFor()` as checkpoints and post-process. It has a first-class `Latex` node backed by **KaTeX**, which matches Scriba's TexRenderer.

**Why it fails in practice.** (1) Output is **canvas raster**, not SVG. The Latex node internally uses KaTeX but composites onto canvas; you cannot extract semantic SVG. (2) Headless rendering requires Chromium in CI — doable but heavy. (3) The scene graph is imperative TS; translating Scriba's editorial step DSL into Motion Canvas tweens is a non-trivial transpiler. (4) Per-step snapshot extraction is not a first-class feature — you'd hack it via `project.render({range: [t, t+1]})`. (5) Still fundamentally designed for video end-products, not embedded step widgets.

**Verdict:** Closest philosophical match (code-first, KaTeX-compatible) but wrong output substrate (canvas, not SVG). Would require forking the renderer to emit SVG per checkpoint. Not worth the effort for the 3–5 problems that need it.

### 3.3 Penrose

**What integration would look like.** Penrose is the only build-time, CLI, SVG-native tool in the list. You'd author three files per diagram: a Domain (`SetTheory.domain`), a Substance (the specific instance), and a Style (visual rules). `penrose` CLI emits SVG.

**Why it fails in practice.** Penrose is a **diagram** language — it describes static mathematical objects (sets, vectors, graphs, commutative diagrams) and their layout. It has **no concept of equation term rewriting or temporal steps**. You could produce N separate Penrose Substance files, one per step, to get N SVGs — but that's just "write SVG by hand with extra compile steps," and the per-step manual effort is enormous. Penrose shines for *one* beautiful static diagram, not a sequence of equation states.

**Verdict:** Wrong abstraction. Keep on the radar for Agent 2 (geometry) but not for math derivations.

---

## 4. Realistic verdict: what gap can math-animation actually fill?

The original HARD-TO-DISPLAY list conflates four genuinely different needs:

| Need | Best-served by | Why |
|---|---|---|
| Equation term rewriting (Frog DP, Burnside expansion, Mobius pair, loop invariants) | **Agent 1 animatable equations** (extended) | These are local `KaTeX` DOM diffs. A step controller can swap `<mrow>` children with a CSS opacity/transform transition. Build-time cost: emit N KaTeX SVGs + a diff manifest. |
| Butterfly diagrams, complex-plane rotation (FFT) | **External video link** to 3B1B | Genuinely requires continuous motion + 2D geometric intuition. Any static-SVG reproduction is strictly worse than the existing video. |
| Plots of DP tables, recurrence value evolution | **Agent 5 plot** | Already planned. |
| Geometric constructions (Penrose-style) | **Agent 2 geometry** | Already planned. |

Extending Agent 1 to support a **step-indexed equation** primitive handles 80% of the editorially important cases, reuses the existing TexRenderer / KaTeX path, preserves text-selectable SVG, adds zero runtime dependencies, and costs roughly one compiler pass. The remaining 20% is "just link the 3B1B video" — which is what every competent editorial on hard math already does.

### 4.1 Agent 1 extension sketch (the actual recommendation)

```
::eqn-steps
  $$dp[i] = \min(dp[i-1] + |h_i - h_{i-1}|, dp[i-2] + |h_i - h_{i-2}|)$$
  step "highlight base case"    highlight={dp[i-1]}
  step "expand second branch"   highlight={dp[i-2]}
  step "minimum resolves"       replace={\min(...)}{dp[i]}
::
```

Compile → N KaTeX-rendered SVGs with matching IDs, a JSON step manifest, and a tiny runtime (already written for other widgets) that swaps the active SVG on step change. No new dependency. No LaTeX install. No Chromium in CI.

### 4.2 External-link convention for the hard 20%

For FFT / complex roots / visual-geometric derivations:

```
::math-video
  title   = "FFT butterfly and roots of unity"
  youtube = "h7apO7q16V0"
  authors = "3Blue1Brown"
  fallback = "See §4 of the editorial text below for a static walkthrough."
::
```

Renders as a thumbnail + caption + link. Honest, cheap, and strictly better than any static reproduction Scriba could build.

---

## 5. Implementation tasks (or: do not implement)

**DO NOT** integrate Manim, Motion Canvas, Penrose, Theatre.js, Mafs, Framer Motion, MathBox, or reveal.js chalkboard into Scriba's compile pipeline. Each would consume weeks of glue code and deliver a worse result than the Agent 1 extension.

**DO** (in priority order):

1. **Extend Agent 1 with `::eqn-steps` primitive.** Reuse TexRenderer. Emit N SVGs + step manifest. ~300 LOC in the compiler + ~50 LOC runtime swap. Covers Frog DP, Burnside, Mobius, loop invariants, simple algebraic manipulations.
2. **Add `::math-video` primitive.** Pure markup → `<figure>` with thumbnail, caption, external link, and a `fallback` prose block that renders if video is unavailable. ~80 LOC.
3. **Document the convention** in the Scriba authoring guide: "For derivations requiring continuous visual motion (rotations, butterflies, 3D), link to an external video. Scriba is not a video tool."
4. **Close the door.** Add a `docs/scriba/non-goals.md` entry: *Scriba does not ship a Manim-class animation engine. Build-time SVG snapshots + discrete step controllers are the boundary.*

---

## 6. Citations

- Manim Community docs — https://docs.manim.community/ (SVG export status, LaTeX dependency)
- Motion Canvas docs — https://motioncanvas.io/docs/ (canvas renderer, KaTeX node)
- Penrose — https://penrose.cs.cmu.edu/ (Domain/Style/Substance, SVG output)
- KaTeX — https://katex.org/ (already used by Scriba TexRenderer)
- Mafs — https://mafs.dev/ (React runtime, plots not derivations)
- Theatre.js — https://www.theatrejs.com/ (editor-driven runtime)
- Framer Motion `layoutId` — https://www.framer.com/motion/ (runtime DOM morph)
- MathBox — https://gitgud.io/unconed/mathbox (WebGL)
- reveal.js chalkboard — https://github.com/rajgoel/reveal.js-plugins
- 3Blue1Brown FFT video — https://www.youtube.com/watch?v=h7apO7q16V0

---

## 7. One-line answer

*Scriba should extend Agent 1 for local equation rewriting, link to 3B1B for everything visually continuous, and put "Manim integration" on the permanent non-goals list.*
