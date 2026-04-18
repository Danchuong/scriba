# Extension E1 — `\begin{figure-embed}` Environment

> **Status: not yet implemented (planned for E6 extension).** `FigureEmbedRenderer`
> does not exist in the current package. This document is a design spec only.
> Do not attempt to import or instantiate `FigureEmbedRenderer` — it will raise
> `ImportError`. The implementation is tracked separately and will ship in a future
> minor release.

> **Design status:** Accepted extension to `environments.md`. This document defines
> a compile-time SVG/PNG escape-hatch environment. It does not modify the base spec;
> any required base-spec changes are listed in §12 (Base-spec deltas).
>
> Cross-references: `environments.md` §2 (grammar carve-out rules), §8 (HTML
> shape conventions), §9 (CSS contract), §10 (error catalog ranges); `00-ARCHITECTURE-
> DECISION-2026-04-09.md` for the pivot decision that accepted Problem #10 as
> "author-provides-SVG".

---

## 1. Purpose

`\begin{figure-embed}` admits a pre-rendered SVG or PNG file as a first-class scene
frame with mandatory attribution and accessibility metadata. It is the formal
**escape hatch** for cases where no Scriba primitive can represent the visual
adequately at compile time.

### HARD-TO-DISPLAY problems unlocked

| # | Problem | How figure-embed helps |
|---|---------|------------------------|
| 4 | FFT butterfly | Author provides a planar butterfly wiring diagram for N=256 as a hand-crafted SVG inset |
| 5 | MCMF dense graph | Pre-rendered Matplotlib heatmap of the final 200×200 assignment matrix |
| 6 | Convex Hull Trick geometry | Matplotlib line-plot SVG for N=20 lines showing the lower envelope |
| 9 | Simulated Annealing | Pre-rendered tour snapshot used alongside `\fastforward` frames |
| 10 | Planar Separator | Hardcoded N=20 planar graph with BFS layers hand-drawn in Excalidraw |

The escape hatch is not a failure mode — it is a design feature. An editorial that
uses one embedded SVG for its most pathological frame and native Scriba primitives
for the rest is better than an editorial that distorts a primitive to fit.

---

## 2. Grammar / BNF

`\begin{figure-embed}` is recognized by `FigureEmbedRenderer` as a top-level
environment. It follows the carve-out rules of `environments.md` §2.2:
both tags MUST appear on their own lines. It does NOT nest inside
`\begin{animation}` or `\begin{diagram}` (E1003 from the base spec).

```
figure_embed_env ::= "\begin{figure-embed}" opt_options NEWLINE
                     embed_body
                     "\end{figure-embed}"

opt_options      ::= "" | "[" option_list "]"
option_list      ::= option ("," option)*
option           ::= IDENT "=" option_value
option_value     ::= IDENT | NUMBER | STRING

embed_body       ::= source_cmd
                     alt_cmd
                     caption_cmd
                     credit_cmd
                     highlight_cmd*

source_cmd       ::= "\source" brace_arg
                 %  brace_arg is a file path, relative to the document root

alt_cmd          ::= "\alt" brace_arg
caption_cmd      ::= "\caption" brace_arg
credit_cmd       ::= "\credit" brace_arg

highlight_cmd    ::= "\highlight" brace_arg opt_highlight_params
opt_highlight_params ::= "" | "{" param_list "}"

brace_arg        ::= "{" balanced_text "}"
param_list       ::= param ("," param)*
param            ::= IDENT "=" param_value
param_value      ::= NUMBER | STRING | IDENT
```

### 2.1 Command ordering

`\source`, `\alt`, `\caption`, and `\credit` MUST each appear exactly once inside
the body. The parser accepts them in any order but normalises them before
validation. `\highlight` commands, if present, MUST appear after `\source` and
before `\end{figure-embed}`.

### 2.2 Environment options

| Key        | Type    | Default  | Meaning                                                          |
|------------|---------|----------|------------------------------------------------------------------|
| `id`       | ident   | auto-SHA | Stable scene id used in `data-scriba-scene`. Same rules as base. |
| `label`    | string  | none     | `aria-label` for the outer `<figure>`.                           |
| `width`    | dim     | `auto`   | Hint for rendered width. `auto` uses the SVG intrinsic viewBox.  |
| `height`   | dim     | `auto`   | Hint for rendered height.                                        |
| `format`   | ident   | auto     | `svg` or `png`. Overrides extension-based detection (§3.1).      |

Unknown keys → E1004 (base spec).

---

## 3. The inner commands

### 3.1 `\source{path}`

Resolves the file path via `ctx.resource_resolver(path)`:

- `path` is relative to the directory of the source `.tex` file being compiled.
- Absolute paths are forbidden (E1308).
- Only `.svg` and `.png` extensions are supported (E1306). Case-insensitive.
- The resolver MUST return a `bytes` payload and a MIME type string.
- For SVG: `bytes` is the raw UTF-8 source. For PNG: `bytes` is the binary PNG.
- If the file does not exist, the resolver raises `ResourceNotFoundError` → E1305.
- If `format=` is provided in options, that overrides the file extension check.

**PNG `@2x` auto-detection.** If `path = "fig/tour.png"` and
`"fig/tour@2x.png"` also exists in the same resolver context, both are recorded.
The `@2x` variant is embedded as `srcset` data in the HTML output for email
clients that support it (§6). No error is raised if only the `1x` exists.

### 3.2 `\alt{text}`

Plain text alternative for the embedded image. MUST be non-empty (E1300). This
is the `alt` attribute of the rendered `<img>` (for PNG) or the `<title>` child
of the `<svg>` root (for inline SVG). HTML-escaped at emit time. LaTeX markup
inside `\alt` is not processed — the body is treated as plain text.

### 3.3 `\caption{LaTeX text}`

Caption text rendered by `ctx.render_inline_tex`. Supports `$math$` and inline
TeX commands. MUST be non-empty (E1301). Emitted inside `<figcaption>`.

### 3.4 `\credit{text}`

Attribution string (author name, tool name, license). Plain text, no TeX
processing. MUST be non-empty (E1302). Appended to the caption inside the same
`<figcaption>` element, separated by " — ".

### 3.5 `\highlight{selector}{params...}`

Overlays a primitive-style highlight on a sub-element of an embedded SVG
identified by an XML `id` attribute. Only available when the source format is SVG.

- `selector` is a bare `id` value (no `#` prefix). The renderer looks for an
  element with that `id` inside the sanitized SVG.
- To avoid collisions with the host document, the renderer rewrites all SVG `id`
  attributes with the prefix `scriba-embed-{scene-id}-`. The `selector` in
  `\highlight` refers to the ORIGINAL id before rewriting; the renderer performs
  the mapping internally.
- Allowed `params`:
  - `state=<state>` — one of the base-spec states: `idle`, `current`, `done`,
    `dim`, `error`, `good`, `highlight`. Adds class `scriba-state-<state>` to
    the matched SVG element.
  - `label=<string>` — injects a `<text>` overlay inside a
    `<g class="scriba-embed-overlay">` wrapper positioned above the element's
    bounding box. Plain text, no TeX.
- `\highlight` on a PNG source is E1309 (SVG-only feature).
- Referencing an `id` not found in the sanitized SVG is a WARNING, not an error
  (the element may have been stripped by DOMPurify). The warning is surfaced in
  `RenderContext.metadata["warnings"]` as `W1308` (highlight-selector-not-matched).

---

## 4. SVG sanitization

All inline SVG content is passed through DOMPurify configured with the SVG
security profile. The exact allow-list is specified here so that it does not drift
between `DOMPurify` version bumps.

### 4.1 Allowed tags

```
svg, g, defs, title, desc, symbol, use, marker,
rect, circle, ellipse, line, polyline, polygon, path,
text, tspan, textPath, image,
clipPath, mask, linearGradient, radialGradient, stop,
filter, feBlend, feColorMatrix, feComposite,
feFlood, feGaussianBlur, feMerge, feMergeNode, feOffset, feTile,
animate, animateTransform, animateMotion, set,
foreignObject
```

`foreignObject` is ALLOWED but its children are sanitized with the HTML profile
(no script, no form, no iframe inside foreignObject). This permits MathML labels
exported by Inkscape.

`script`, `style` (top-level), `a` (with `href`), `iframe`, `embed`, `object`,
`base`, `form`, `input`, and `canvas` are REMOVED. Presence of a `<script>` tag
in the source SVG triggers E1303.

> **Note on `FORBID_TAGS: ["style"]`:** This rule applies exclusively to
> *author-embedded* SVG content passed through this environment. Scriba's own
> primitive output does not emit inline `<style>` blocks — all primitive CSS
> ships via static files in `required_css` (e.g.
> `scriba/animation/static/scriba-keyframes.css`). Because primitives never
> emit inline `<style>`, the distinction between author-embed sanitization and
> Scriba-emit sanitization is moot in practice; the `FORBID_TAGS: ["style"]`
> profile stays as-is.

### 4.2 Allowed attributes

Geometry: `x`, `y`, `cx`, `cy`, `r`, `rx`, `ry`, `d`, `points`,
`x1`, `y1`, `x2`, `y2`, `width`, `height`, `viewBox`, `preserveAspectRatio`,
`transform`, `patternTransform`, `gradientTransform`.

Style: `fill`, `stroke`, `stroke-width`, `stroke-dasharray`, `stroke-linecap`,
`stroke-linejoin`, `opacity`, `fill-opacity`, `stroke-opacity`, `color`,
`font-size`, `font-family`, `font-weight`, `text-anchor`, `dominant-baseline`.

Reference: `href` (data URIs and relative paths only; `http://`, `https://`,
`javascript:` are stripped), `xlink:href` (same), `clip-path`, `mask`, `filter`,
`marker-start`, `marker-mid`, `marker-end`.

Identity: `id`, `class` (class values are preserved but namespaced — see §3.5).

Animation: `attributeName`, `attributeType`, `begin`, `dur`, `end`, `repeatCount`,
`from`, `to`, `values`, `keyTimes`, `calcMode`, `fill` (SMIL fill, not SVG fill).

Event handler attributes (`onclick`, `onmouseover`, `onload`, etc.) are REMOVED.

### 4.3 DOMPurify configuration object

The Python implementation invokes DOMPurify via the same `katex_worker.js`-style
node subprocess (see `environments.md` §5.5 for the SubprocessWorkerPool
pattern). The worker receives the raw SVG string and returns the sanitized string.
The configuration object passed to `DOMPurify.sanitize`:

```js
{
  USE_PROFILES: { svg: true, svgFilters: true },
  ADD_TAGS: ["foreignObject", "title", "desc",
             "animate", "animateTransform", "animateMotion", "set"],
  ADD_ATTR: ["attributeName", "attributeType", "begin", "dur", "end",
             "repeatCount", "from", "to", "values", "keyTimes",
             "calcMode", "dominant-baseline", "text-anchor"],
  FORBID_TAGS: ["script", "style"],
  FORBID_ATTR: ["onload", "onclick", "onerror", "onmouseover",
                "onmouseout", "onfocus", "onblur",
                "xlink:actuate", "xlink:show"],
  FORCE_BODY: false,
  RETURN_DOM: false
}
```

---

## 5. Determinism and `scriba.lock`

### 5.1 Content hash

At build time, after sanitization, the renderer computes
`SHA-256(sanitized_bytes)` for each embedded asset. This hash is stored in a
top-level `scriba.lock` JSON file alongside the `.tex` source.

**Format of `scriba.lock`:**

```json
{
  "version": 1,
  "embeds": {
    "fig/planar-sep.svg": "e3b0c44298fc1c149afb...truncated",
    "fig/tour.png":       "a7ffc6f8bf1ed76651c1...truncated",
    "fig/tour@2x.png":    "4a8a08f09d37b73795649..."
  }
}
```

- Keys are the original `\source` paths (exactly as written by the author).
- Values are lowercase hex SHA-256 of the sanitized bytes (SVG) or raw bytes
  (PNG — no sanitization for PNG, so hash is of the original file).
- The file is created on first build and committed alongside the source.

### 5.2 Lock mismatch (E1304)

On subsequent builds, if the SHA-256 of the file currently on disk differs from
the value stored in `scriba.lock`, the renderer emits E1304 and STOPS. This is a
**hard error** because a silently changed embedded SVG can introduce security
regressions (an attacker replacing a benign SVG with one containing event
handlers). The author must either:

- Accept the new version by running `scriba lock --update` (CLI command that
  recomputes hashes and rewrites `scriba.lock`), or
- Revert the file to the locked version.

### 5.3 New embeds

On first build (no entry in `scriba.lock`), the hash is computed, added to
`scriba.lock`, and the build proceeds normally. A warning is emitted to remind
the author to commit `scriba.lock`.

---

## 6. HTML output shape

```html
<!-- SVG source -->
<figure class="scriba-figure-embed"
        data-scriba-scene="{scene-id}"
        data-scriba-format="svg"
        data-scriba-embed-hash="{sha256-hex}"
        aria-label="{label option or caption text}">
  <!-- inline sanitized SVG with rewritten ids -->
  <svg class="scriba-embed-svg"
       viewBox="..."
       xmlns="http://www.w3.org/2000/svg"
       role="img"
       aria-labelledby="scriba-embed-{scene-id}-title">
    <title id="scriba-embed-{scene-id}-title">{alt text}</title>
    <!-- sanitized SVG content with ids prefixed scriba-embed-{scene-id}- -->
    <!-- \highlight overlays injected as <g class="scriba-embed-overlay"> children -->
  </svg>
  <figcaption class="scriba-embed-caption">
    <!-- ctx.render_inline_tex(caption) output -->
    <span class="scriba-embed-credit"> — {credit text}</span>
  </figcaption>
</figure>

<!-- PNG source -->
<figure class="scriba-figure-embed"
        data-scriba-scene="{scene-id}"
        data-scriba-format="png"
        data-scriba-embed-hash="{sha256-hex}"
        aria-label="{label option or caption text}">
  <img class="scriba-embed-img"
       src="data:image/png;base64,{base64-encoded-png}"
       srcset="data:image/png;base64,{base64-1x} 1x,
               data:image/png;base64,{base64-2x} 2x"
       alt="{alt text}"
       width="{intrinsic-width}"
       height="{intrinsic-height}"
       loading="lazy"
  />
  <figcaption class="scriba-embed-caption">
    <!-- ctx.render_inline_tex(caption) output -->
    <span class="scriba-embed-credit"> — {credit text}</span>
  </figcaption>
</figure>
```

Notes:
- PNG is embedded as a `data:` URI so the output is a single self-contained HTML
  file with no external asset dependencies. This is required for Codeforces
  editorial portability.
- `srcset` is omitted if the `@2x` file does not exist.
- `width` and `height` on `<img>` are the intrinsic pixel dimensions of the `1x`
  variant, to prevent layout shift.
- `data-scriba-embed-hash` is the SHA-256 of the sanitized bytes, enabling
  downstream content-hash caches to detect embed changes.
- When `\highlight` is used, each highlighted element gains `class="scriba-state-{state}"` (mapped to the same CSS variables as the base spec §9.2), and any `label=` overlay is injected as a `<text>` element inside a `<g class="scriba-embed-overlay">` wrapper positioned above the element's bounding box.

---

## 7. CSS contract

`figure-embed` introduces one new CSS block in `scriba-animation.css` (or a new
`scriba-figure-embed.css` loaded via `@import`):

```css
.scriba-figure-embed {
  display: block;
  max-width: 100%;
  margin-block: var(--scriba-frame-gap, 1rem);
}

.scriba-figure-embed .scriba-embed-svg,
.scriba-figure-embed .scriba-embed-img {
  display: block;
  max-width: 100%;
  height: auto;
}

.scriba-embed-caption {
  font-size: var(--scriba-caption-size, 0.85em);
  color: var(--scriba-fg-muted);
  margin-block-start: 0.375rem;
}

.scriba-embed-credit {
  font-style: italic;
}

/* Highlight overlays on SVG sub-elements */
.scriba-embed-svg [class^="scriba-state-"] {
  /* inherits the same Wong CVD-safe palette as base spec §9.2 */
}

@media print {
  .scriba-figure-embed .scriba-embed-img,
  .scriba-figure-embed .scriba-embed-svg {
    page-break-inside: avoid;
  }
}
```

No new CSS variables are introduced. The `--scriba-state-*` variables from
`environments.md` §9.2 are reused for `\highlight` overlays.

---

## 8. Error catalog (E1300–E1309)

| Code  | Severity | Meaning                                                              | Hint |
|-------|----------|----------------------------------------------------------------------|------|
| E1300 | **Error** | `\alt` is empty or missing                                           | Provide non-empty alt text for accessibility. |
| E1301 | **Error** | `\caption` is empty or missing                                       | A caption is required for all embedded figures. |
| E1302 | **Error** | `\credit` is empty or missing                                        | Attribute the source (author, tool, license). |
| E1303 | **Error** | SVG source contains a forbidden tag (`<script>`, event handler, etc.)| Remove scripting from the SVG or regenerate from the source tool. |
| E1304 | **Error** | SHA-256 of file on disk does not match `scriba.lock`                 | Run `scriba lock --update` to accept the new file, or revert it. |
| E1305 | **Error** | `\source` file not found via `ctx.resource_resolver`                 | Check path is relative to the `.tex` file and the file exists. |
| E1306 | **Error** | `\source` file has an unsupported extension (not `.svg` or `.png`)   | Only SVG and PNG are accepted. Pre-render to one of these formats. |
| E1307 | Warning  | ≥30% of animation steps in this document use `figure-embed`          | Consider whether native Scriba primitives cover some frames. |
| E1308 | **Error** | `\source` path is absolute; only relative paths are permitted        | Use a path relative to the `.tex` source file. |
| E1309 | **Error** | `\highlight` used on a PNG source                                    | Highlight overlays require SVG source format. |

E1300, E1301, E1302 are **hard failures**: the HTML is NOT emitted and the build
exits with a non-zero status. This matches the base spec philosophy that
accessibility attributes are never optional.

E1307 is a **document-level lint warning** computed after all environments in the
document are compiled. It fires if the ratio:

```
count(figure-embed frames in document) / count(total animation frames in document)
≥ 0.30
```

"Animation frames" counts frames from all `\begin{animation}` environments in the
same document. `\begin{diagram}` frames count as one frame each. `figure-embed`
figures count as one frame each. The threshold is 30%.

---

## 9. Acceptance tests

### 9.1 Planar separator (Problem #10)

Source file: `cookbook/10-planar-separator/planar-sep.svg` — a hand-drawn SVG
of a 4×5 grid graph (N=20 nodes) with BFS layers coloured using named `id` values
`layer-0` through `layer-3` and `separator` for the cut vertices.

```latex
\begin{figure-embed}[id=planar-sep-demo, label="Planar separator on a 4×5 grid"]
\source{../assets/planar-sep.svg}
\alt{A 4×5 grid graph with BFS layers shown in alternating colours. The separator
     consists of the 4 nodes in layer 2, shown in red.}
\caption{One step of the Lipton--Tarjan planar separator algorithm. BFS from
         the top-left corner produces layers $L_0, L_1, L_2, L_3$; layer $L_2$
         has $|\sqrt{N}| = 4$ nodes and separates the graph into two components.}
\credit{Hand-drawn in Excalidraw, exported as SVG. CC0.}
\highlight{separator}{state=error, label="separator"}
\highlight{layer-0}{state=done}
\highlight{layer-1}{state=current}
\end{figure-embed}
```

Expected: one `<figure class="scriba-figure-embed">` with inline SVG, `separator`
nodes styled `scriba-state-error`, `layer-0` nodes `scriba-state-done`, `layer-1`
nodes `scriba-state-current`. Build writes entry to `scriba.lock`.

### 9.2 Matplotlib function plot (Problem #6)

Source: `assets/cht-lines.svg` — a pre-rendered SVG from Matplotlib showing 6
linear functions `y = m_i * x + b_i` and the lower envelope.

```latex
\begin{figure-embed}[id=cht-geometry]
\source{assets/cht-lines.svg}
\alt{Six lines on a 2D plane with the lower envelope highlighted.}
\caption{Lower envelope of 6 lines. The query point $x_q$ slides right; at each
         $x_q$ the optimal line achieves $\min_i (m_i x_q + b_i)$.}
\credit{Generated with Matplotlib 3.9, CC0.}
\end{figure-embed}
```

---

## 10. Integration with `\begin{animation}`

`figure-embed` is a **standalone** environment, not a frame inside an animation.
To interleave embedded figures with native animation frames in an editorial, the
author places `\begin{figure-embed}` ... `\end{figure-embed}` between two
`\begin{animation}` ... `\end{animation}` environments in the `.tex` source. The
Pipeline handles them as separate top-level blocks.

A future Scriba version may introduce a `\embedframe` command inside
`\begin{animation}` to embed a figure as one filmstrip frame. That is out of scope
for this extension spec and is recorded in `07-open-questions.md`.

---

## 11. `FigureEmbedRenderer` pipeline registration

> **Note:** `FigureEmbedRenderer` is not yet implemented. The code below is a
> design preview of the planned registration API and will not work with the
> current package.

```python
# NOT YET AVAILABLE — design preview only
# from scriba.animation import AnimationRenderer, DiagramRenderer, FigureEmbedRenderer
#
# pipeline = Pipeline(renderers=[
#     AnimationRenderer(),
#     DiagramRenderer(),
#     FigureEmbedRenderer(                      # planned for E6 extension
#         resource_resolver=my_resolver,
#         lock_path=Path("scriba.lock"),
#     ),
#     TexRenderer(worker_pool=pool),
# ])
```

`FigureEmbedRenderer.priority = 10` (same as `AnimationRenderer`). The detection
regex:

```python
FIGURE_EMBED_RE = re.compile(
    r"(?ms)^\\begin\{figure-embed\}(\[[^\]\n]*\])?\s*\n(.*?)\n\\end\{figure-embed\}\s*$",
)
```

---

## 12. Base-spec deltas

The following changes to `environments.md` are REQUIRED to support this
extension. Agent 4 (roadmap/phases rewrite) will merge them.

1. **§2.3 Nesting**: Add `\begin{figure-embed}` to the list of environments that
   do not nest inside `\begin{animation}` or each other. Specifically:
   > `\begin{figure-embed}` inside `\begin{animation}` or `\begin{diagram}` is
   > `E1003`. `\begin{figure-embed}` inside another `\begin{figure-embed}` is
   > `E1003`.

2. **§11 Error catalog**: Reserve `E1300–E1399` for `figure-embed` extension
   errors (currently the catalog ends at `E1299`). The existing reservation note
   at §11 bottom should be updated to acknowledge that `E13xx` is allocated.

3. **§10.1 Detection**: Document that `FigureEmbedRenderer` uses the same carve-out
   regex pattern as `AnimationRenderer` with `figure-embed` substituted, and shares
   `priority = 10`.
