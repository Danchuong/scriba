# Vendored: KaTeX

This directory contains a vendored copy of KaTeX shipped inside the
`scriba` wheel so that `pip install scriba` works without a separate
`npm install -g katex` step.

| Field | Value |
|-------|-------|
| Upstream | https://github.com/KaTeX/KaTeX |
| Version | `0.16.11` |
| License | MIT (SPDX: `MIT`) — see `LICENSE` in this directory |
| Copyright | Copyright (c) 2013-2020 Khan Academy and other contributors |
| Vendored on | 2026-04-08 |

## Files

| File | Source URL | Size | SHA-256 |
|------|------------|------|---------|
| `katex.min.js` | https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js | 269 KiB | `e6bfe5deebd4c7ccd272055bab63bd3ab2c73b907b6e6a22d352740a81381fd4` |
| `katex.min.css` | https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css | 21 KiB | `f0dbfcc2940b4d788c805c1a1e117e898d2814b0f1a52bf16640543216e0964d` (post-strip) |
| `fonts/KaTeX_*.woff2` | https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/fonts/ | 296 KiB total (20 files) | — |

`katex.min.js` is consumed by `scriba/tex/katex_worker.js` to render
TeX into HTML. `katex.min.css` and the woff2 fonts style the resulting
`.katex` HTML class tree. Both must be served to the browser by the
consumer; `katex.min.css` references the woff2 files via relative
`url(fonts/...)` so they must live in this same vendor directory.

The vendored `katex.min.css` has the `.woff` and `.ttf` `@font-face`
fallbacks stripped — only `.woff2` sources remain. Modern browsers
support woff2 universally, and this saves serving 18 unused 404s.

Vendored fonts (20):

```
KaTeX_AMS-Regular            KaTeX_Math-BoldItalic
KaTeX_Caligraphic-Bold       KaTeX_Math-Italic
KaTeX_Caligraphic-Regular    KaTeX_SansSerif-Bold
KaTeX_Fraktur-Bold           KaTeX_SansSerif-Italic
KaTeX_Fraktur-Regular        KaTeX_SansSerif-Regular
KaTeX_Main-Bold              KaTeX_Script-Regular
KaTeX_Main-BoldItalic        KaTeX_Size1-Regular
KaTeX_Main-Italic            KaTeX_Size2-Regular
KaTeX_Main-Regular           KaTeX_Size3-Regular
KaTeX_Size4-Regular          KaTeX_Typewriter-Regular
```

## How to refresh

To bump the vendored version, run the refresh script from the repo root:

```bash
packages/scriba/scripts/vendor_katex.sh 0.16.12
```

The script downloads the requested version from the jsDelivr CDN,
computes its SHA-256, and updates this file in place. Commit both the
new `katex.min.js` and the updated `VENDORED.md` in the same commit.

Any KaTeX version bump is a coordinated change: update the pin in
`CHANGELOG.md`, `README.md`, and any other place the version is
referenced.
