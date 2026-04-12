# Scriba Legacy Docs

This directory archives the **first-generation Scriba design**, in which Scriba was modeled as a standalone domain-specific language (DSL) with its own author-facing syntax, its own widget runtime, and bespoke HTML/JS demos.

**That model has been retired.** Scriba is no longer a standalone DSL.

## The pivot

Scriba is now **two new LaTeX environments** that plug into the existing `packages/scriba/` Python plugin pipeline alongside `TexRenderer`:

- `\begin{animation} ... \end{animation}`
- `\begin{diagram} ... \end{diagram}`

Authors write regular LaTeX and embed these environments the same way they embed TikZ. The toolchain compiles them to zero-JS static SVG output (animations become SVG filmstrips). There is no custom DSL parser, no widget runtime, and no client-side JavaScript.

See `../environments.md` for the current source of truth.

## Why these files are archived (not deleted)

The legacy material still has value as historical reference for **design intent** — the pedagogical principles, motion grammar, visual style, and interaction vocabulary we want the new LaTeX environments to preserve. It is **not** a reference for implementation; the runtime model, author surface, and output format have all changed.

Treat everything in this directory as:

- Valid: editorial intent, motion vocabulary, visual language, worked pedagogical examples.
- Invalid: syntax, file formats, widget APIs, HTML/JS runtime assumptions, standalone-DSL framing.

## Contents

| Path | What it was | Why archived |
|---|---|---|
| `ANIMATION-RULESET.md` | Rules for the legacy animation DSL — timing, easing, staging, motion grammar. | Output format changed to static SVG filmstrips under the LaTeX `animation` environment. Principles remain useful; syntax does not. |
| `STATIC-FIGURE-RULESET.md` | Rules for legacy static figure DSL — layout, labels, visual hierarchy. | Superseded by the LaTeX `diagram` environment. Visual principles remain useful. |
| `EDITORIAL-PRINCIPLES.md` | First pass at Scriba's editorial voice and pedagogical stance. | Superseded by V2; kept for lineage. |
| `EDITORIAL-PRINCIPLES-V2.md` | Second pass at editorial principles. | Archived pending a rewrite against the new LaTeX-environments model. |
| `USAGE-DIAGRAM-WIDGET.md` | Author guide for the legacy diagram widget. | Widget runtime is gone; authors now write LaTeX. |
| `mock-diagram-widget.html` | Standalone HTML mock of the diagram widget. | Zero-JS static SVG output replaces the widget. |
| `frog1-demo/` | Worked demo — frog pedagogical example. | HTML/JS demo targeting the old widget runtime. Pedagogical content still instructive. |
| `monkey-apples-demo/` | Worked demo — monkey/apples counting example. | Same as above. |
| `swap-game-demo/` | Worked demo — swap game interaction. | Same as above. |
| `swap-game-demo-ver2/` | Iteration 2 of swap game. | Same as above. |
| `swap-game-demo-ver3/` | Iteration 3 of swap game. | Same as above. |

## If you are implementing the new Scriba

Do not read these files as spec. Read `../environments.md` and the sibling numbered docs (`01-architecture.md`, `03-diagram-plugin.md`, `09-animation-plugin.md`, etc.). Use this directory only when you need to understand *why* a given visual or pedagogical choice was originally made.
