# Embedding Scriba output in a website

How a web developer renders a `.tex` source with Scriba and drops the result
into their own site — and how to control diagram text size from the host page
via `--scriba-diagram-font-scale`.

> Scriba produces **HTML + CSS**, no runtime JavaScript framework. The diagram
> font-scale knob is a **CSS custom property**, so you set it in *your* site's
> stylesheet — it is not a render-time function argument.

---

## 1. Render the source

The reliable entry point is the CLI driver `render.py` at the repo root, which
writes a self-contained HTML file (JS + CSS inlined by default):

```bash
python render.py lesson.tex -o lesson.html
```

`render.py` is a top-level script, not part of the importable `scriba`
package. From a checkout you can also call its `render_file` helper directly
(it lives next to `render.py`):

```python
from render import render_file   # works when render.py is on sys.path (repo root)

render_file(
    "lesson.tex",          # input .tex (may contain \begin{animation} / \begin{diagram})
    "lesson.html",         # output HTML
    inline_runtime=True,   # self-contained: all CSS/JS inlined
)
```

The output is a full HTML document whose `<head>` already declares the default
scale:

```css
:root { --scriba-diagram-font-scale: 1; }
```

---

## 2. Put it on your page

### Option A — iframe the standalone file (least coupling)

```html
<iframe src="/lessons/lesson.html" title="Binary search" loading="lazy"></iframe>
```

To resize the diagram text, inject one rule **inside** the rendered document
(the iframe has its own document, so the host page's CSS does not reach in).
Either render with a wrapper that sets the var (see §3) or post-process the
file to add:

```html
<style>:root { --scriba-diagram-font-scale: 1.3; }</style>
```

### Option B — inline the widget fragment (full control)

Take the rendered `<div class="scriba-widget">…</div>` markup and paste it into
your page, then ship Scriba's stylesheet once:

```python
from scriba.core.css_bundler import load_css

# Concatenate the stylesheets the animation/diagram widgets need.
css = load_css(
    "scriba-scene-primitives.css",   # primitive + diagram font tokens (incl. the scale knob)
    "scriba-animation.css",          # widget chrome (controls, progress, narration)
    "scriba-embed.css",              # embed-safe wrapper styles
    "scriba-tex-content.css",        # TeX prose styling
)
# Serve `css` as /assets/scriba.css (or inline it in <head> once).
```

```html
<link rel="stylesheet" href="/assets/scriba.css">
…
<article class="lesson">
  <!-- paste the rendered widget markup here -->
  <div class="scriba-widget" …> … </div>
</article>
```

Because it lives in *your* DOM, your stylesheet controls it directly (§3).

---

## 3. Resize diagram text with `--scriba-diagram-font-scale`

Every font size inside a Scriba diagram — cell values, node labels, indices,
captions, edge weights, axis ticks, code panels, annotations — is multiplied by
this custom property. Default `1` leaves everything unchanged.

```css
/* whole page */
:root { --scriba-diagram-font-scale: 1.3; }      /* 30% larger diagram text */
```

```css
/* scope to a section/widget — custom properties inherit to descendants */
.lesson { --scriba-diagram-font-scale: 1.5; }
```

```html
<!-- or inline on a wrapper element -->
<div class="scriba-widget" style="--scriba-diagram-font-scale: 0.85"> … </div>
```

Setting it on a wrapping element always wins for everything inside it (no
specificity battle with Scriba's `:root` default), so the wrapper approach is
the most reliable when embedding fragments.

### What it does and does not affect

- ✅ All diagram/animation SVG text (array, dptable, graph, tree, queue,
  stack, hashmap, linkedlist, variablewatch, matrix, plane2d, metricplot,
  codepanel, numberline) and annotation labels.
- ⚠️ **Only text** scales. SVG geometry (cell sizes, node radius, viewBox) is
  fixed, so very large factors can make text overflow its shapes. Adjust in
  moderation (≈ 0.8–1.6 is the comfortable range).
- ❌ TeX prose text outside diagrams is **not** governed by this knob. Scale
  that the normal way — set `font-size` on the `.scriba-tex-content` container
  (it inherits the host page's size):

  ```css
  .scriba-tex-content { font-size: 1.125rem; }
  ```

### Finer control

For per-role sizing instead of a single global factor, redefine the individual
tokens (each is also multiplied by the scale):

```css
:root {
  --scriba-cell-font:        500 16px inherit;     /* cell values */
  --scriba-node-font:        500 16px inherit;     /* graph/tree nodes */
  --scriba-label-font:       600 13px monospace;   /* captions */
  --scriba-cell-index-font:  500 12px monospace;   /* indices */
  --scriba-annotation-font:  600 13px monospace;   /* annotations */
}
```

See [`spec/animation-css.md`](../spec/animation-css.md) §2 for the full token
list.

---

## 4. Security note

`Document.html` / the rendered fragment is **not** HTML-sanitized by Scriba —
it is trusted output meant to be embedded as-is. If you render *untrusted*
`.tex` and must sanitize at your edge, allow at least the tags/attributes in
`scriba.ALLOWED_TAGS` / `scriba.ALLOWED_ATTRS` (SVG elements, `class`,
`style`, `data-*`), or the diagrams will be stripped.

The font-scale knob requires no script and no relaxed CSP — it is plain CSS.
