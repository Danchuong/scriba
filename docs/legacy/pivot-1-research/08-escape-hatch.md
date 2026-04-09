# Scriba Escape Hatch: Embedding Pre-Rendered Frames

**Status:** Research / Proposal
**Audience:** Scriba compiler authors, editorial authors
**Scope:** How to embed hand-made visuals when Scriba's discrete-step engine cannot (or should not) render them automatically.

---

## Executive Summary

Scriba's compiler models small, structured, step-wise algorithms: sorting six integers, a BFS on twelve nodes, a segment tree of depth four. The HARD-TO-DISPLAY analysis identified a recurring class of problems — planar separator, dense min-cost max-flow residual graphs, splay rotation cascades, suffix automaton at N ≥ 10^4, and FFT correctness arguments — where the algorithmic state is either too large to lay out discretely, too continuous to decompose into meaningful frames, or requires a proof-shaped argument rather than a data-shaped animation. For these, auto-rendering produces either an illegible hairball or, worse, a misleadingly tidy picture.

The answer is an **escape hatch**: a first-class `embed` directive that lets the author paste a pre-rendered asset as *one frame of the step controller*, indistinguishable to the reader from a compiler-generated frame except that the glyphs are whatever the author drew.

**Recommendation, one line each:**

- **Primary authoring tool:** Excalidraw (CP editorials are hand-drawn board-work, and Excalidraw's aesthetic matches that). tldraw is a close second when collaboration matters; Figma wins only when the editorial team already lives in Figma.
- **Primary file format:** inline SVG, fallback PNG@2x. No Lottie, no GIF, no MP4 in-tree.
- **Embed convention:** a Scriba `embed "path.svg"` step-body directive that replaces the auto-rendered canvas for that step and participates in the step controller like any other frame.
- **When to reach for it:** whenever Scriba's shape model would lie, or the figure's job is pedagogical intuition rather than state-tracking.

---

## Comparison of Embedding Approaches

| # | Approach | Vector? | Addressable? | Print-clean? | Auth effort | Verdict for Scriba |
|---|---|---|---|---|---|---|
| 1 | `<img src="x.png">` | No | No | Yes if ≥ 2x DPR | Low | Fallback only |
| 2 | Inline `<svg>...</svg>` | Yes | Yes (DOM) | Yes | Medium | **Primary** |
| 3 | `<img src="x.svg">` | Yes | No (opaque) | Yes | Low | Good for simple figures |
| 4 | `<object data="x.svg">` | Yes | Partial (sandboxed) | Yes | Low | Rejected: awkward focus/a11y |
| 5 | `<iframe>` | Yes | No | Flaky on print | Low | Rejected |
| 6 | `<picture>` responsive | Mixed | No | Yes | Medium | Use inside the primary |
| 7 | Asciinema JSON player | N/A | Yes | **No** | Low | Terminal replays only |
| 8 | Lottie JSON | Vector-ish | Yes | No (animated) | High | Rejected: tooling cost |
| 9 | Animated GIF | Raster | No | No | Low | Rejected: ugly, heavy |
| 10 | MP4 / WebM | Raster | No | No | High | External link only |
| 11 | Mermaid/D2 source block | Vector | Yes | Yes | Low | Already the default path |
| 12 | LaTeX TikZ → SVG | Yes | Yes | Yes | High | Opt-in for formal figures |
| 13 | Asymptote → SVG | Yes | Yes | Yes | Very high | Rejected: toolchain burden |
| 14 | draw.io XML embed | Yes | Yes | Yes | Medium | Accepted as alt source |
| 15 | External link card | — | — | Yes (link) | Low | For 3Blue1Brown etc. |

The table collapses into one rule: **SVG in, PNG fallback, everything else out of the core path.** Anything animated beyond discrete frames belongs either to Scriba's own step engine (if it fits the model) or to an external link card (if it doesn't).

---

## Authoring Tool Deep Dive

### Excalidraw — recommended primary

Excalidraw ([excalidraw.com](https://excalidraw.com), docs at [docs.excalidraw.com](https://docs.excalidraw.com)) exports clean SVG with a deliberately hand-drawn, board-work aesthetic. For competitive programming editorials this is exactly right: the reference medium for CP teaching is the whiteboard, and Excalidraw's Virgil/Cascadia stroke style reads as "I drew this while thinking" rather than "a designer polished this for shipping." It runs entirely in-browser, requires no account for single-author work, supports a `.excalidraw` JSON source file that can be committed alongside the exported SVG for later editing, and its SVG export embeds the source JSON in a `<!-- payload-start -->` comment so the asset is round-trippable. The library of shapes is intentionally small — rectangles, ellipses, arrows, text, freehand — which matches the granularity of a planar-separator illustration or a splay-rotation snapshot. For the five HARD-TO-DISPLAY cases, Excalidraw handles four of them natively (planar separator, splay cascade, FFT butterfly, MCMF small residual) and the fifth (dense MCMF at realistic N) should be rendered by Gephi and only *captioned* in Excalidraw.

### tldraw — recommended when collaborating

[tldraw.com](https://tldraw.com), docs at [tldraw.dev](https://tldraw.dev). Same SVG-first philosophy as Excalidraw, slightly more polished stroke style, and a mature multi-cursor collaboration mode. Choose tldraw over Excalidraw only when two editorial authors need to draw the same figure together in real time, or when the figure needs tldraw's shape-inheritance model. tldraw's SVG export is similarly clean and its `.tldr` source format is JSON.

### Figma — only if already in use

Figma exports SVG but it is designed for pixel-perfect UI and the resulting SVG is verbose, carries Figma-isms (clip paths, transform matrices), and the aesthetic is *too* clean for a CP editorial — figures look corporate rather than pedagogical. Use Figma only if the editorial team already has a Figma style system and will reuse components across dozens of editorials.

**Also considered and rejected:** draw.io (accepted as a secondary source format because its XML is open, but its SVG export has layout artifacts), Mermaid Live Editor (already covered by the D2/Mermaid source-block path), Asymptote and TikZ (world-class output, unacceptable toolchain weight for an editorial author on deadline).

---

## Proposed Scriba `embed` Syntax

Scriba steps already accept narration, highlights, and shape operations. `embed` extends the step body with a single new directive:

```
step "Planar separator: pick centroid level" {
  embed "fig/planar-separator-step3.svg" {
    alt "Planar graph with 20 nodes. Separator set of 4 nodes highlighted in red, splitting the graph into a 7-node and a 9-node component."
    caption "Hand-drawn. Separator found by level-BFS from node v0."
    credit "editorial author"
  }
  narrate "The separator has size O(sqrt N). Here, N=20 and |S|=4 ≈ sqrt(20)."
}
```

Three concrete use cases showing the full shape:

**1. Single hand-drawn SVG replacing the auto frame**

```
step "Splay: zig-zig rotation" {
  embed "fig/splay-zigzig.svg" { alt "..." }
  narrate "x moves up two levels; grandparent g and parent p are both demoted."
}
```

**2. Multi-frame sequence that the step controller walks through**

```
sequence "Splay rotation cascade" {
  embed "fig/splay/cascade-01.svg" { alt "..." caption "Start: x is 5 levels deep" }
  embed "fig/splay/cascade-02.svg" { alt "..." caption "After first zig-zig" }
  embed "fig/splay/cascade-03.svg" { alt "..." caption "After second zig-zig" }
  embed "fig/splay/cascade-04.svg" { alt "..." caption "After zig" }
  embed "fig/splay/cascade-05.svg" { alt "..." caption "x is root" }
  narrate "Five rotations total; amortized O(log N) across the splay."
}
```

Each `embed` in a `sequence` becomes one step in the step controller, numbered automatically. The reader advances through cascade-01 → cascade-05 with the same Next button that advances a compiler-generated BFS.

**3. External link card (no inline asset)**

```
step "FFT intuition" {
  link "https://www.youtube.com/watch?v=spUNpyF58BY" {
    title "But what is the Fourier Transform? A visual introduction"
    source "3Blue1Brown"
    duration "20m"
  }
  narrate "The butterfly diagram below is the discrete version of the idea Grant draws continuously."
  embed "fig/fft-butterfly-n8.svg" { alt "..." }
}
```

`link` is a distinct directive from `embed`: it never becomes a frame, it renders as a card with thumbnail and source attribution, and the print exporter turns it into a footnote with the URL spelled out.

---

## Step Controller Integration

An embedded asset *replaces* the auto-rendered canvas for its step; it does not overlay. Rationale: overlaying a hand-drawn SVG on top of a compiler-rendered shape tree means the two can disagree, and readers cannot tell which is authoritative. Replacement is honest.

Concretely, the compiler pipeline becomes:

1. Parse the step. If `embed` is present, mark the step's render mode as `external`.
2. For `external` steps, skip shape-tree construction. Load the SVG file, parse it, rewrite `id` attributes with a step-scoped prefix to avoid DOM collisions, and inline it into the frame's container.
3. The step controller's frame counter still increments. `Prev`/`Next`/scrubber/keyboard navigation all work identically.
4. Narration, timing, and highlight anchors still apply. An author can write `highlight "#node-v0"` and, because `id`s are preserved (namespaced), the highlight lands on the right glyph inside the hand-drawn figure. This turns Excalidraw's named shapes into first-class anchor targets, which is a surprisingly powerful consequence.
5. **Determinism:** the compiler hashes each embedded file with SHA-256 at compile time, stores the hash in the source map, and refuses to compile if the file on disk no longer matches a previously committed hash in `scriba.lock` (unless `--update-embeds` is passed). This gives the same reproducibility guarantees as the rest of the build.
6. **Caching:** the hash also keys the tenant-backend's HTML cache, so a re-rendered SVG busts the cache on the very next publish.

---

## When to Use the Escape Hatch (Author Rules)

1. **Use it when the shape model would lie.** If the auto-layout of a 200-node dense residual graph produces a hairball, embed a Gephi SVG. The reader's trust is worth more than any single auto-rendered frame.
2. **Use it when the figure's job is intuition, not state.** FFT butterfly, planar separator proof sketch, amortized potential-function cartoons — these are *arguments*, not *traces*. Scriba traces; authors argue.
3. **Do not use it to dodge debugging.** If the auto-render is ugly because the shape model is wrong, fix the shape model. The escape hatch is for "fundamentally beyond" cases, not for "I didn't feel like tuning the layout."
4. **Do not embed raster when vector is possible.** PNG is a fallback for photographs and Gephi exports, not a default.
5. **Always write alt text, always caption, always credit.** No exceptions. The compiler should hard-fail on missing `alt`.

---

## Print, PDF, and Email Verification

The embed pipeline is SVG-first precisely because SVG survives print. Concretely:

- **PDF export** (via the existing tenant-backend HTML → PDF path, typically Puppeteer or Playwright): inlined SVG rasterizes at the device's native resolution, so a 300 DPI print of a planar-separator figure stays crisp. Raster fallbacks ship at 2x and the print CSS sets `image-rendering: crisp-edges` for pixel art and `auto` for photographs.
- **Email**: email clients dislike inline SVG. For email digests, the compiler emits a parallel PNG rasterization of every embed at 1200px wide and swaps the `<svg>` for an `<img>` with the PNG `src` under `@media` — actually, email lacks media queries reliably, so the email template literally references the PNG path stored next to the SVG. The SVG and the PNG share the same base filename and the same hash prefix.
- **Dark mode**: SVGs authored in Excalidraw carry their own stroke colors, which look wrong on a dark background. The compiler inspects the inline SVG for `stroke="#000000"` / `fill="#ffffff"` and, when the reader is in dark mode, applies a CSS filter `invert(1) hue-rotate(180deg)` scoped to embeds marked `theme: auto`. Authors who hand-pick palettes can set `theme: fixed` to opt out.
- **Accessibility**: `alt` is mandatory. For sequences, each frame's `alt` is spoken by screen readers as the step controller advances. Captions render below the figure in a `<figcaption>` and are always visible.

---

## Implementation Tasks

1. **Parser**: add `embed`, `sequence`, and `link` directives to the Scriba grammar. Reject `embed` without `alt`.
2. **Loader**: file-path resolution relative to the editorial source; SHA-256 hashing; `scriba.lock` integration.
3. **SVG sanitizer**: strip `<script>`, external references, and `on*` attributes from embedded SVGs. Namespace all `id`s with a per-step prefix. This is a small, well-understood problem; use DOMPurify's SVG profile as a reference.
4. **Renderer integration**: teach the step controller that `render_mode: external` skips shape-tree rendering and inlines sanitized SVG.
5. **Anchor resolution**: let `highlight` directives target `id`s inside embedded SVG via the namespaced prefix.
6. **Raster fallback generator**: at compile time, rasterize each SVG to PNG@2x for email and legacy clients. resvg or Playwright screenshot suffice.
7. **Source map**: record `(step, embed-path, sha256)` triples so debugging points into the right asset.
8. **Print CSS**: verify SVG embeds survive the existing HTML-to-PDF pipeline; add a visual regression test at 320 / 768 / 1440.
9. **Link cards**: renderer + print-footnote fallback.
10. **Author docs**: a one-page "escape hatch" guide, with the five author rules and three worked examples (planar separator, splay cascade, FFT butterfly).
11. **Lint**: a Scriba lint rule that flags editorials where more than ~30% of steps are `embed` — a signal the auto-engine should probably learn the pattern instead.

The escape hatch is not a concession. It is the seam where Scriba admits that some editorial insight is load-bearing and belongs to the human, and then treats the human's drawing with the same determinism, accessibility, and print-fidelity guarantees as everything the compiler produces itself.
