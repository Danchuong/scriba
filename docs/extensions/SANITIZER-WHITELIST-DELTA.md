# Sanitizer Whitelist Delta — Pivot #2 Extensions

> **Scope:** This file catalogs every HTML element, CSS class, and data attribute
> that `services/tenant/frontend/lib/sanitize.ts` must additionally allow to
> support the **five Pivot #2 extension features** (E1–E5). Additions required by
> the five primitives (P1–P5) are tracked in a separate file maintained by the
> primitive agent.
>
> This file is the authoritative reference for the sanitizer-update task in
> `05-implementation-phases.md` Week C5.
>
> Cross-references: `extensions/figure-embed.md` §4, `extensions/substory.md` §4,
> `extensions/keyframe-animation.md` §4–§5, `extensions/hl-macro.md` §5,
> `environments.md` §8.1.

---

## Naming convention

All Scriba-specific data attributes use the `data-scriba-<kebab-case-name>` prefix.
Attributes introduced before this convention was codified (e.g. `data-substory-id`,
`data-substory-depth`) are listed here for completeness; new code MUST use the
`data-scriba-*` namespace.

CSS classes emitted by Scriba use the `scriba-` prefix. No exceptions.

---

## New HTML elements

These elements appear in Scriba output HTML outside of any embedded SVG and MUST
NOT be stripped by the frontend sanitizer.

| Element / selector | Source extension | Notes |
|--------------------|-----------------|-------|
| `<figure class="scriba-figure-embed">` | E1 figure-embed §6 | Wrapper for embedded SVG or PNG frames |
| `<img class="scriba-embed-img">` with `data:image/png;base64,` `src` | E1 figure-embed §6 | `data:` URIs MUST be allowed on `src` and `srcset` attributes of `<img>` elements with this class |
| `<figcaption class="scriba-embed-caption">` | E1 figure-embed §6 | Caption inside figure-embed |
| `<span class="scriba-embed-credit">` | E1 figure-embed §6 | Attribution inside figcaption |
| `<section class="scriba-substory">` | E4 substory §4.1 | Wrapper around substory frame list |
| `<ol class="scriba-substory-frames">` | E4 substory §4.1 | Ordered list of substory frames |
| `<li class="scriba-frame scriba-substory-frame">` | E4 substory §4.1 | Individual substory frame (also carries `scriba-frame` class from base) |

---

## New SVG elements (inside Scriba-emitted inline SVG)

These appear inside `<svg class="scriba-stage-svg">` or `<svg class="scriba-embed-svg">`
elements. The frontend sanitizer profile for inline SVG must allow them.

| Element | Source extension | Notes |
|---------|-----------------|-------|
| `<g class="scriba-embed-overlay">` | E1 figure-embed §3.5 / §6 | Wrapper for `\highlight` label overlays on embedded SVG |

> **No `<style>` inside Scriba-emitted SVG.** Decision lock #6: all preset CSS
> ships via `required_css["keyframes/scriba-keyframes.css"]`. Scriba primitives
> never emit inline `<style>` blocks. The `FORBID_TAGS: ["style"]` rule in the
> figure-embed DOMPurify profile applies to author-provided SVG only and is
> not a concern for Scriba-emitted SVG.

---

## New CSS classes

### E1 — `figure-embed`

| Class | Element it appears on |
|-------|-----------------------|
| `scriba-figure-embed` | `<figure>` |
| `scriba-embed-svg` | `<svg>` inside figure-embed |
| `scriba-embed-img` | `<img>` inside figure-embed (PNG) |
| `scriba-embed-caption` | `<figcaption>` |
| `scriba-embed-credit` | `<span>` inside figcaption |
| `scriba-embed-overlay` | `<g>` inside embedded SVG, for `\highlight` overlays |

### E2 — `\hl` macro

| Class | Element it appears on |
|-------|-----------------------|
| `scriba-tex-term` | `<span>` wrapping KaTeX-rendered `\hl` expressions |
| `scriba-tex-fallback` | `<span>` used when `TexRenderer` is absent |

### E4 — `\substory`

| Class | Element it appears on |
|-------|-----------------------|
| `scriba-substory` | `<section>` wrapper |
| `scriba-substory-frames` | `<ol>` list of substory frames |
| `scriba-substory-frame` | `<li>` individual substory frame |

### E5 — `@keyframes` animation

| Class | Element it appears on | Preset |
|-------|-----------------------|--------|
| `scriba-animate-rotate` | `<g>` inside SVG | `rotate` |
| `scriba-animate-orbit` | `<g>` inside SVG | `orbit` |
| `scriba-animate-pulse` | `<g>` inside SVG | `pulse` |
| `scriba-animate-trail` | `<g>` inside SVG | `trail` |
| `scriba-animate-fade-loop` | `<g>` inside SVG | `fade-loop` |
| `scriba-animate-slide-in-vertical` | `<g>` inside SVG | `slide-in-vertical` (Stack push) |
| `scriba-animate-slide-in-horizontal` | `<g>` inside SVG | `slide-in-horizontal` (Stack push) |

---

## New data attributes

### Attributes following `data-scriba-*` convention

| Attribute | Element | Source | Notes |
|-----------|---------|--------|-------|
| `data-scriba-format` | `<figure class="scriba-figure-embed">` | E1 figure-embed §6 | `"svg"` or `"png"` |
| `data-scriba-embed-hash` | `<figure class="scriba-figure-embed">` | E1 figure-embed §6 | SHA-256 hex of sanitized bytes |
| `data-scriba-step-id` | `<span class="scriba-tex-term">` | E2 hl-macro §4.3 | Step id matching a `\step[label=]` |
| `data-scriba-tex-fallback` | `<span class="scriba-tex-fallback">` | E2 hl-macro §7 | `"true"` when TexRenderer absent |
| `data-scriba-beta` | `<svg>` with `layout="stable-beta"` | E5 / P5 graph-stable | `"true"` for beta stable-layout graphs |

### Attributes predating the `data-scriba-*` convention (retain for compat)

| Attribute | Element | Source | Notes |
|-----------|---------|--------|-------|
| `data-substory-id` | `<section class="scriba-substory">` | E4 substory §4.2 | Substory id (auto or author-provided) |
| `data-substory-depth` | `<section class="scriba-substory">`, `<li class="scriba-substory-frame">` | E4 substory §4.1 | Nesting depth (1–3) |
| `data-orbit-direction` | `<g class="scriba-animate-orbit">` | E5 keyframe-animation §3.2 | `"cw"` or `"ccw"` |

---

## Allowed inline style properties

The frontend sanitizer must permit these inline `style` property names on
`<g>` elements inside Scriba-emitted SVG (set by the keyframe-animation emitter):

| Property | Set by |
|----------|--------|
| `animation-duration` | E5 keyframe-animation emitter |
| `--scriba-orbit-cx` | E5 orbit preset |
| `--scriba-orbit-cy` | E5 orbit preset |
| `--scriba-orbit-r` | E5 orbit preset |
| `--scriba-rotate-cx` | E5 rotate preset |
| `--scriba-rotate-cy` | E5 rotate preset |
| `--scriba-pulse-scale` | E5 pulse preset |
| `--scriba-trail-min-opacity` | E5 trail preset |

---

## Required static assets

The following static CSS files must be served (or inlined) alongside Scriba output
for extension features to render correctly:

| File (in `required_css`) | Purpose |
|--------------------------|---------|
| `keyframes/scriba-keyframes.css` | All 7 `@keyframes` rules + `.scriba-animate-*` classes (E5) |
| `figure-embed/scriba-figure-embed.css` | Figure-embed layout and caption styles (E1) |
