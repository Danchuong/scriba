# Vendored: KaTeX

This directory contains a vendored copy of KaTeX shipped inside the
`scriba` wheel so that `pip install scriba` works without a separate
`npm install -g katex` step.

| Field | Value |
|-------|-------|
| Upstream | https://github.com/KaTeX/KaTeX |
| Source URL | https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js |
| Version | `0.16.11` |
| SHA-256 | `e6bfe5deebd4c7ccd272055bab63bd3ab2c73b907b6e6a22d352740a81381fd4` |
| License | MIT (SPDX: `MIT`) — see `LICENSE` in this directory |
| Copyright | Copyright (c) 2013-2020 Khan Academy and other contributors |
| Vendored on | 2026-04-08 |

Only `katex.min.js` is vendored. Fonts and CSS are not needed because
Scriba consumes KaTeX's HTML-only output (`output: 'html'`) at render
time; downstream consumers ship KaTeX's CSS and fonts themselves.

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
