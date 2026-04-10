# O2 — Docs Site: Tool Selection & IA

> Picks the docs site stack and locks an information architecture for the v0.3 launch. Source of truth for environments, commands, primitives, and error codes is [`../04-environments-spec.md`](../spec/environments.md).

## 1. Winner: Astro Starlight on Cloudflare Pages + Pagefind

**Stack**
- **Framework**: Astro Starlight
- **Host**: Cloudflare Pages (free tier, global CDN, preview deploys per PR)
- **Search**: Pagefind (static, no SaaS, no JS runtime cost on cold load)
- **Domain**: `scriba.dev` (to be reserved)

## 2. Why Starlight (post-pivot rationale)

Pre-pivot, Starlight was chosen because the runtime was a Lit 3 custom element and Starlight's zero-JS-by-default island architecture let `<scriba-widget>` ship without a React reconciler.

After the pivot, the rationale is **even stronger**: Scriba output is now **pure static HTML + inline SVG with no runtime at all**. Every cookbook example on the docs site is just the literal compiled output pasted into an MDX file.

```mdx
---
title: Binary Search
---

Here is the animation compiled from `examples/binary-search.tex`:

<figure class="scriba-figure scriba-animation" ...>
  <ol class="scriba-filmstrip">
    <li class="scriba-frame">...</li>
    ...
  </ol>
</figure>
```

No import. No component. No hydration. No bundler config. The same CSS file Scriba ships loads once from `/scriba.css` and the figure renders identically to how it would render in a consumer's Django template, email client, or printed PDF.

Every other option pays a tax we now have no reason to pay:
- Docusaurus / Nextra — React reconciler for content that contains zero React.
- mkdocs-material — forces Jinja templates; cookbook entries become iframes or raw HTML blocks.
- Mintlify / GitBook — SaaS lock-in, worse for error-code reference tables that need to cross-link deeply.
- VitePress — nice, but Vue runtime loads on pages that contain only static SVG.

Starlight wins because "paste compiled HTML into MDX, done" is the shortest possible cookbook pipeline.

## 3. Information architecture (~20 pages at v0.3)

### Home
- Tagline, 60s screen capture, `pip install scriba`, 20-line binary-search demo, CTA to Quick Start.

### Quick Start (5 minutes)
1. `pip install scriba`
2. Minimal Python snippet that builds `Pipeline([AnimationRenderer, DiagramRenderer, TexRenderer])`
3. Paste a 20-line `\begin{animation}` source, call `pipeline.render`, print HTML
4. Drop output into any file served as `text/html` — it renders.

### Concepts
- `environments-vs-tex` — how Scriba coexists with `TexRenderer`
- `animation-vs-diagram` — when to pick which
- `frames-and-narration` — how `\step` + `\narrate` compose
- `primitives` — the 6 shape primitives
- `semantic-states` — the 6 state classes
- `starlark-host` — build-time determinism, sandbox rules
- `html-css-contract` — what consumers may style against

### Reference
- Environments (`animation`, `diagram`) — options table
- Commands (8 commands, one page each)
- Primitives (6 primitives, one page each with full parameter schema)
- Semantic states (single page)
- Python API (`Pipeline`, renderers, IR, error classes)
- **Error codes** — one page per code in `E1001–E1299`, each with example source that triggers it and the fix

### Cookbook
Live gallery of canon entries. Each page contains:
1. The `.tex` source in a syntax-highlighted block
2. The compiled `<figure>` pasted verbatim as MDX below it
3. Narrative walkthrough of the 8 commands it uses

Canon for v0.3: binary-search, bfs, dp-table-fill, segment-tree-query, grid-flood-fill, tree-traversal.

### Recipes (FAQ-shaped)
- "How do I reuse a shape across frames?"
- "How do I highlight multiple cells at once?"
- "How do I add a caption under the whole figure?"
- "How do I make narration render inline math?"
- "How do I test that my `\compute` block is deterministic?"

### Integration Guides
One page each: **Django**, **FastAPI**, **Flask**, **Static site generators**. These consume the compiled HTML; see [`O3-integrations.md`](O3-integrations.md).

## 4. Search

Pagefind indexes all MDX content including the literal SVG labels inside cookbook entries. A user searching "binary search" or "invariant" lands directly on the cookbook page whose frame narration contains those words.

## 5. Performance budget

- Zero JS on cold load for every page except a tiny `pagefind` bundle loaded on `/search` focus.
- CSS budget: < 15 KB gzipped for `/scriba.css` (the one stylesheet that realizes the CSS contract in `../04-environments-spec.md` §9).
- No web fonts beyond the system stack unless a cookbook page explicitly opts in.
- LCP < 1.5s on every page on the Cloudflare edge.

## 6. Open items

- `scriba.dev` domain reservation
- OG image template per cookbook entry
- Versioned docs story (defer until v0.4 — v0.3 ships unversioned)
