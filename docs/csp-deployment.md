# CSP Deployment Guide

Scriba supports three deployment modes for the animation runtime JS.
Choose the one that fits your hosting environment.

---

## Mode 1 — Inline runtime (default in v0.8.x)

All JS and frame data are inlined in the HTML file.  Self-contained, works
on `file://`, zero additional files to serve.

```bash
python render.py input.tex                   # default: inline-runtime
python render.py input.tex --inline-runtime  # explicit
```

**CSP requirement:**  `script-src 'unsafe-inline'`  (or a per-hash value
for each rendered page).

This mode exists as the default for backwards compatibility through v0.8.x.
The default **flips to external-runtime in v0.9.0**.

---

## Mode 2 — External runtime, copy next to HTML (recommended for v0.9.0+)

Frame data is placed in an inert `<script type="application/json">` island.
The runtime is referenced via `<script src="scriba.<hash>.js" integrity="sha384-..." defer>`.

```bash
python render.py input.tex --no-inline-runtime
```

This creates two files in the output directory:
- `input.html`
- `scriba.<hash>.js`  (the runtime asset)

Serve both files from the same directory.

**CSP header (paste-ready):**

```
Content-Security-Policy:
  default-src 'none';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  font-src 'self' data:;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
```

> `style-src 'unsafe-inline'` is required because KaTeX emits inline
> `style=` attributes.  This is a known limitation tracked for Wave 9.

---

## Mode 3 — External runtime via CDN / asset base URL

Host `scriba.<hash>.js` on a CDN or shared static server and reference it
by full URL.  Use `--no-copy-runtime` to skip copying the file locally.

```bash
python render.py input.tex \
  --no-inline-runtime \
  --asset-base-url https://cdn.example.com/scriba/0.8.3 \
  --no-copy-runtime
```

The rendered HTML will contain:

```html
<script src="https://cdn.example.com/scriba/0.8.3/scriba.<hash>.js"
        integrity="sha384-<base64>"
        crossorigin="anonymous" defer></script>
```

**CSP header:**

```
Content-Security-Policy:
  default-src 'none';
  script-src 'self' https://cdn.example.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  font-src 'self' data:;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
```

---

## Exporting the runtime asset manually

To obtain `scriba.<hash>.js` without rendering a `.tex` file:

```python
from scriba.animation.runtime_asset import (
    RUNTIME_JS_BYTES,
    RUNTIME_JS_FILENAME,
    RUNTIME_JS_SHA384,
)

print(f"Filename : {RUNTIME_JS_FILENAME}")
print(f"SHA-384  : sha384-{RUNTIME_JS_SHA384}")

with open(RUNTIME_JS_FILENAME, "wb") as f:
    f.write(RUNTIME_JS_BYTES)
```

---

## Deprecation timeline

| Version | Default mode | Notes |
|---------|-------------|-------|
| v0.8.3  | inline-runtime | external-runtime available via `--no-inline-runtime` |
| v0.9.0  | external-runtime | `--inline-runtime` flag kept as escape hatch |
| v1.0.0  | external-runtime | `--inline-runtime` removed |
