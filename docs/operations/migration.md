# 05 — Migration Guide

> This document is a **guide**, not a locked spec. It describes how to migrate
> existing ojcloud content and backend code to use Scriba. The authoritative
> contracts it references are [`01-architecture.md`](../spec/architecture.md),
> [`02-tex-plugin.md`](../guides/tex-plugin.md), and
> [`04-environments-spec.md`](../spec/environments.md). When this guide and a
> locked spec disagree, the spec wins.

## 1. Migration scope

The migration touches three layers:

| Layer | What changes | Effort |
|-------|-------------|--------|
| **Backend rendering** | Replace `tex_renderer.py` singleton + `get_katex_worker()` with Scriba `Pipeline` / `TexRenderer` | Medium |
| **Frontend HTML consumer** | Update CSS class selectors from Tailwind/hardcoded names to `scriba-tex-*`; remove regex-injected copy buttons | Medium |
| **Static assets** | Replace ad-hoc CSS/JS files with Scriba's namespaced `scriba-tex-*` assets | Low |
| **Sanitization** | Add bleach (or nh3) pass with `ALLOWED_TAGS` / `ALLOWED_ATTRS` | Low |
| **Existing content** | TeX source files require **no changes** — the same LaTeX input produces equivalent output with new class names | None |

Authors do not need to rewrite their `.tex` source. The migration is
entirely an infrastructure concern: backend render calls, frontend
selectors, and asset serving.

## 2. Breaking changes from the prior rendering system

The prior system is `services/tenant/backend/app/utils/tex_renderer.py`
(1686 lines). Scriba introduces the following breaking changes, all
documented in [`02-tex-plugin.md` 4](../guides/tex-plugin.md):

### 2.1 CSS class renames

Every Tailwind utility class and custom class in the old renderer is
replaced with a `scriba-tex-*` namespaced class. The old output is not
valid under Scriba's CSS; both cannot coexist on the same page.

| Old class / inline style | New Scriba class |
|---|---|
| `katex-display my-4 text-center` | `scriba-tex-math-display` |
| `style="border: 1px solid #374151"` (table cells) | `scriba-tex-border-*` classes per column spec |
| `style="border-left: 4px solid #6b7280; ..."` (epigraph) | `scriba-tex-epigraph` |
| `style="font-size: 85%"` etc. (size commands) | `scriba-tex-size-{tiny,scriptsize,...,Huge}` |
| `code-block-wrapper` | `scriba-tex-code-block` |
| (no class, bare `<pre>`) for unknown-language code | `scriba-tex-code-plain` |

The full mapping is in [`02-tex-plugin.md` 3](../guides/tex-plugin.md).

### 2.2 Inline styles removed

Scriba emits inline `style=""` in exactly three cases
([`02-tex-plugin.md` 3.3](../guides/tex-plugin.md)):

1. `\includegraphics[scale=...]` -- `transform: scale(X); transform-origin: top left`
2. `\includegraphics[width=...|height=...]` -- `width: Npx` / `height: Npx`
3. (Reserved for 0.2) KaTeX display per-instance transform

All other visuals -- borders, colors, font sizes, margins, alignment --
are CSS classes referencing `--scriba-*` custom properties.

### 2.3 Copy button injection removed

The old renderer emitted a comment placeholder; the frontend
(`pre-rendered-tex.tsx`) regex-injected `<button>` elements at hydration
time. Scriba emits the `<button class="scriba-tex-copy-btn">` statically
at render time. The frontend regex injection must be **deleted**, not
adapted.

### 2.4 URL resolution decoupled

The old renderer hardcoded
`f"{base_url}/api/problems/{problem_id}/{filename}"` for image URLs.
Scriba accepts a `ResourceResolver` callback via `RenderContext` --
the consumer owns URL shape entirely.

### 2.5 Worker lifecycle change

The old `get_katex_worker()` singleton is replaced by a per-`Pipeline`
`SubprocessWorkerPool`. Each gunicorn worker process gets its own pool.
See [`02-tex-plugin.md` 12.3](../guides/tex-plugin.md) for the full ops
migration note.

## 3. Step-by-step migration process

### Phase 1: Install and validate (1 day)

1. Add `scriba` to `requirements.txt` / `pyproject.toml`.
2. Verify Node.js 18+ is available on PATH in the deployment environment.
3. Run the Scriba test suite against the ojcloud environment:
   ```bash
   pip install scriba
   python -m pytest --pyargs scriba
   ```
4. Confirm 71 tests pass (snapshot, XSS, validator, pipeline, workers,
   sanitize).

### Phase 2: Backend render path (2--3 days)

1. **Create the Pipeline in the Flask factory.**

   ```python
   # services/tenant/backend/app/__init__.py  (inside create_app)
   from scriba import Pipeline, SubprocessWorkerPool
   from scriba.tex import TexRenderer

   pool = SubprocessWorkerPool()
   tex = TexRenderer(
       worker_pool=pool,
       pygments_theme="one-light",
       enable_copy_buttons=True,
       katex_worker_max_requests=50_000,
   )
   pipeline = Pipeline([tex])
   app.extensions["scriba"] = pipeline
   ```

2. **Wire the teardown hook.**

   ```python
   @app.teardown_appcontext
   def close_scriba(exc):
       if "scriba" in app.extensions:
           app.extensions["scriba"].close()
   ```

3. **Replace render calls.** Every call site that currently does:

   ```python
   from app.utils.tex_renderer import render_tex_content
   html = render_tex_content(source, problem_id=pid)
   ```

   becomes:

   ```python
   from scriba import RenderContext

   ctx = RenderContext(
       resource_resolver=lambda name: f"/api/problems/{pid}/{name}",
       theme="auto",
   )
   doc = current_app.extensions["scriba"].render(source, ctx)
   html = doc.html
   css_keys = doc.required_css
   js_keys = doc.required_js
   ```

4. **Delete the old files.**
   - `services/tenant/backend/app/utils/tex_renderer.py`
   - `services/tenant/backend/app/utils/katex_worker.py`
   - `services/tenant/backend/app/utils/tracing_decorators.py` (if only
     used by the renderer)

5. **Update any response caching.** Consumer caches must be keyed on
   `doc.versions` plus `sha256(source)` instead of the old ad-hoc keys.
   See [`01-architecture.md` "Versioning policy"](../spec/architecture.md).

### Phase 3: Asset migration (1 day)

1. **Copy Scriba assets to the static directory.**

   ```python
   from importlib.resources import files
   import shutil

   scriba_static = str(files("scriba.tex") / "static")
   shutil.copytree(scriba_static, "./public/scriba", dirs_exist_ok=True)
   ```

   Or add this as a deploy-time step in the Dockerfile / CI pipeline.

2. **Update HTML templates.** Replace old ad-hoc CSS/JS includes:

   ```html
   <!-- OLD -->
   <link rel="stylesheet" href="/static/css/tex-content.css">
   <script src="/static/js/copy-button.js"></script>

   <!-- NEW -->
   <link rel="stylesheet" href="/cdn/katex/katex.min.css">
   <link rel="stylesheet" href="/public/scriba/scriba-tex-content.css">
   <link rel="stylesheet" href="/public/scriba/scriba-tex-pygments-light.css">
   <script defer src="/public/scriba/scriba-tex-copy.js"></script>
   ```

   For dual-theme support, include both Pygments stylesheets:

   ```html
   <link rel="stylesheet" href="/public/scriba/scriba-tex-pygments-light.css">
   <link rel="stylesheet" href="/public/scriba/scriba-tex-pygments-dark.css">
   ```

   The dark stylesheet activates automatically under
   `[data-theme="dark"]`.

3. **Delete old asset files** that the prior renderer depended on.

### Phase 4: Frontend consumer update (1--2 days)

1. **Remove the copy-button regex injection** from
   `services/tenant/frontend/components/pre-rendered-tex.tsx`. Scriba
   emits `<button class="scriba-tex-copy-btn">` statically -- the
   frontend only needs the `scriba-tex-copy.js` script loaded.

2. **Update CSS selectors.** Search the frontend codebase for every
   reference to the old class names and replace:

   | Search for | Replace with |
   |---|---|
   | `.katex-display` | `.scriba-tex-math-display` |
   | `.code-block-wrapper` | `.scriba-tex-code-block` |
   | any Tailwind class in TeX-related selectors (`my-4`, `text-center`) | remove (handled by Scriba CSS) |

3. **Wrap rendered content in the scoping element.**

   ```html
   <article class="scriba-tex-content">{{ doc.html }}</article>
   ```

   All Scriba CSS rules are scoped under `.scriba-tex-content`, so the
   wrapper is required for styles to apply.

4. **Remove `src`-rewriting logic.** The old frontend rewrote `src`
   attributes on `<img>` elements at hydration time. Scriba resolves
   image URLs at render time via `ResourceResolver` -- the emitted HTML
   already contains the correct URLs.

### Phase 5: Sanitization setup (half day)

Scriba does **not** sanitize its output. The consumer must run a
sanitizer before embedding. Scriba ships the exact allowlist its output
is safe against.

```python
import bleach
from bleach.css_sanitizer import CSSSanitizer
from scriba import ALLOWED_TAGS, ALLOWED_ATTRS

css_sanitizer = CSSSanitizer(
    allowed_css_properties=["transform", "transform-origin", "width", "height"]
)

safe_html = bleach.clean(
    doc.html,
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRS,
    css_sanitizer=css_sanitizer,
    strip=True,
)
```

If the backend already runs a bleach pass on all user-facing HTML, update
the existing pass to use `scriba.ALLOWED_TAGS` and `scriba.ALLOWED_ATTRS`
instead of the current ad-hoc tag lists. The Scriba allowlists are
supersets of typical editorial HTML needs and include MathML, SVG, and
`data-*` attributes required by KaTeX and future animation/diagram
environments.

**Alternative: nh3.** If you prefer `nh3` over `bleach` (see
[`07-open-questions.md` Q7](../planning/open-questions.md)), the allowlists are
plain Python data structures and translate directly to `nh3.clean()`
kwargs.

## 4. API migration reference

### 4.1 Old API to new API mapping

| Old call | New equivalent |
|---|---|
| `render_tex_content(source, problem_id)` | `pipeline.render(source, ctx)` returning `Document` |
| `get_katex_worker()` | Handled internally by `SubprocessWorkerPool` |
| `validate_tex_content(source)` | `tex_renderer.validate(source)` returning `(bool, str \| None)` |
| `base_url + "/api/problems/" + pid + "/" + filename` | `ctx.resource_resolver(filename)` |
| `@_traced_render("TeX body")` | Deleted; wrap `pipeline.render()` with your own tracing |

### 4.2 Return value differences

| Old return | New return |
|---|---|
| `str` (raw HTML) | `Document(html, required_css, required_js, versions)` |
| CSS/JS requirements implicit (hardcoded in templates) | Explicit via `doc.required_css` and `doc.required_js` |
| Cache key: ad-hoc | Cache key: `(doc.versions, sha256(source))` |

## 5. HTML output differences

The TeX source input is identical. The HTML output differs only in class
names and structure. A side-by-side comparison for common constructs:

### Display math

```html
<!-- OLD -->
<div class="katex-display my-4 text-center">
  <span class="katex-display">...</span>
</div>

<!-- NEW -->
<div class="scriba-tex-math-display">
  <span class="katex-display">...</span>
</div>
```

### Code block

```html
<!-- OLD -->
<div class="code-block-wrapper">
  <div class="highlight"><pre>...</pre></div>
  <!-- frontend injects copy button here -->
</div>

<!-- NEW -->
<div class="scriba-tex-code-block" data-language="cpp" data-code="ESCAPED">
  <div class="highlight"><pre>...</pre></div>
  <button type="button" class="scriba-tex-copy-btn" aria-label="Copy code">Copy</button>
</div>
```

### Table cell borders

```html
<!-- OLD -->
<td style="border: 1px solid #374151">A</td>

<!-- NEW -->
<td class="scriba-tex-table-cell scriba-tex-align-left scriba-tex-border-left scriba-tex-border-right scriba-tex-border-top scriba-tex-border-bottom">A</td>
```

### Font sizes

```html
<!-- OLD -->
<span style="font-size: 85%">small text</span>

<!-- NEW -->
<span class="scriba-tex-size-small">small text</span>
```

## 6. Resource resolver setup

The `ResourceResolver` protocol is a single callable:

```python
class ResourceResolver(Protocol):
    def __call__(self, filename: str) -> str | None: ...
```

Returning `None` causes Scriba to emit a
`<span class="scriba-tex-image-missing">` placeholder instead of an
`<img>`. This replaces the old hardcoded URL construction.

**ojcloud tenant backend example:**

```python
def make_resolver(problem_id: int) -> ResourceResolver:
    def resolve(filename: str) -> str | None:
        # Reproduce the old URL shape
        return f"/api/problems/{problem_id}/{filename}"
    return resolve

ctx = RenderContext(
    resource_resolver=make_resolver(pid),
    theme="auto",
)
```

**S3 / CDN example:**

```python
def s3_resolver(filename: str) -> str | None:
    key = f"problems/{problem_id}/assets/{filename}"
    if s3_client.head_object(Bucket=BUCKET, Key=key):
        return f"https://{CDN_DOMAIN}/{key}"
    return None
```

## 7. Testing migrated content

### 7.1 Snapshot comparison

The recommended approach is to render every existing problem statement
through both the old and new renderers, normalize class names, and
compare the structural output.

```python
import re

def normalize_old_html(html: str) -> str:
    """Strip old class names and inline styles so structure can be compared."""
    html = re.sub(r'class="katex-display my-4 text-center"', 'class="MATH_DISPLAY"', html)
    html = re.sub(r'class="code-block-wrapper"', 'class="CODE_BLOCK"', html)
    html = re.sub(r'style="border: 1px solid #374151"', '', html)
    html = re.sub(r'style="font-size: \d+%"', '', html)
    return html

def normalize_new_html(html: str) -> str:
    """Strip new class names so structure can be compared."""
    html = re.sub(r'class="scriba-tex-math-display"', 'class="MATH_DISPLAY"', html)
    html = re.sub(r'class="scriba-tex-code-block[^"]*"', 'class="CODE_BLOCK"', html)
    html = re.sub(r'class="scriba-tex-border-[^"]*"', '', html)
    html = re.sub(r'class="scriba-tex-size-[^"]*"', '', html)
    return html
```

Run this over the full corpus and diff the results. Structural
differences indicate a regression in the port.

### 7.2 Scriba's built-in snapshot tests

Scriba ships 30 snapshot tests ([`02-tex-plugin.md` 8](../guides/tex-plugin.md))
that lock the output shape. Run them after installation:

```bash
python -m pytest --pyargs scriba -k snapshot
```

These tests also assert that **no Tailwind class** (`my-`, `text-`,
`bg-`, `border-`, `px-`, `py-`, `font-`, `rounded-`) appears in the
output, catching regressions where old class names leak through.

### 7.3 XSS regression tests

Scriba ships 5 XSS tests ([`02-tex-plugin.md` 9](../guides/tex-plugin.md))
that verify hostile input is neutralized after a bleach pass with
`ALLOWED_TAGS` / `ALLOWED_ATTRS`. Run them as part of the migration
validation:

```bash
python -m pytest --pyargs scriba -k xss
```

### 7.4 Visual regression

For high-confidence migration, render a representative set of problem
statements in a browser and take screenshots at key breakpoints (320,
768, 1024, 1440). Compare old vs new visually. The structural markup
differs, but the rendered appearance should be equivalent once the new
CSS is loaded.

## 8. Pre-pivot `d2` block migration (Phase B)

Existing ojcloud content authored against the pre-pivot D2 fenced-block
format (`\`\`\`d2 ... \`\`\``) must be migrated to
`\begin{diagram}` before Scriba v0.3.0. A one-off migration script is
delivered as part of Phase B ([`04-roadmap.md` 5.2](../planning/roadmap.md)):

1. Scan all `.tex` files for D2 fenced blocks.
2. Rewrite each block to the `\begin{diagram}...\end{diagram}` grammar.
3. Insert author-notice comments at each rewrite location.
4. Delete the pre-pivot `scriba.diagram` module.

This migration is automated and does not require manual author
intervention. Authors will see a comment in their source indicating the
rewrite.

## 9. Rollback strategy

### 9.1 Backend rollback

The old `tex_renderer.py` and `katex_worker.py` are deleted in Phase 2
step 4. Before deleting, commit them to a `legacy/tex-renderer` branch
(or tag) so they can be restored.

**Rollback procedure:**

1. Revert the Flask factory changes (restore `get_katex_worker()` and
   the old render call sites).
2. Restore the old `tex_renderer.py` and `katex_worker.py` from the
   legacy branch.
3. Revert the frontend changes (restore regex copy-button injection and
   old class selectors).
4. Revert the asset changes (restore old CSS/JS files).
5. Deploy.

The rollback is a full revert -- partial rollback (e.g. keeping Scriba
on the backend but reverting the frontend) is not supported because the
HTML class names are different.

### 9.2 Feature flag approach (recommended)

For a safer migration, gate the render path behind a feature flag:

```python
if feature_flags.get("use_scriba"):
    doc = app.extensions["scriba"].render(source, ctx)
    html = doc.html
else:
    html = render_tex_content(source, problem_id=pid)
```

The frontend must conditionally load the appropriate CSS:

```html
{% if use_scriba %}
  <link rel="stylesheet" href="/public/scriba/scriba-tex-content.css">
{% else %}
  <link rel="stylesheet" href="/static/css/tex-content.css">
{% endif %}
```

This allows per-problem or per-tenant rollback without a full redeploy.
Remove the flag once the migration is validated across the full corpus.

### 9.3 Cache invalidation on rollback

If rolling back after Scriba has been serving content, flush the render
cache. The cache keys include `doc.versions` which will not match the
old renderer's output. Stale Scriba-rendered HTML with `scriba-tex-*`
classes will render incorrectly under the old CSS.

## 10. Timeline alignment with roadmap

The migration is phased to align with the Scriba release roadmap
([`04-roadmap.md`](../planning/roadmap.md)):

| Scriba version | Migration milestone |
|---|---|
| **v0.1.1-alpha** (shipped) | Backend render path migrated. TeX content renders through `Pipeline` / `TexRenderer`. Frontend updated to `scriba-tex-*` classes. Sanitization wired with `ALLOWED_TAGS` / `ALLOWED_ATTRS`. |
| **v0.2.0** (Phase A) | `\begin{animation}` environment available. No migration needed -- new feature, not a replacement. Update `ALLOWED_TAGS` / `ALLOWED_ATTRS` if new tags/attributes are added. |
| **v0.3.0** (Phase B) | `\begin{diagram}` environment ships. Pre-pivot `d2` blocks migrated via script. `scriba.ALLOWED_TAGS` updated for animation/diagram elements. Tenant frontend sanitizer whitelist updated per [`04-environments-spec.md` 8](../spec/environments.md). |
| **v0.4.0** (Phase C) | New primitives and extensions. No migration -- additive only. |
| **v0.5.0 GA** (Phase D) | Migration complete. Old renderer code fully removed from the monorepo. Legacy branch archived. |

No Scriba version is tagged until the ojcloud tenant backend has
migrated to it ([`04-roadmap.md` 3](../planning/roadmap.md)). The migration
and the release are coupled by design.

## 11. Checklist

Use this checklist to track migration progress:

- [ ] `scriba` installed and test suite passes
- [ ] `Pipeline` + `TexRenderer` constructed in Flask factory
- [ ] Teardown hook wired (`pipeline.close()`)
- [ ] All render call sites migrated to `pipeline.render(source, ctx)`
- [ ] `ResourceResolver` implemented for the tenant URL shape
- [ ] Old `tex_renderer.py` and `katex_worker.py` deleted (or behind feature flag)
- [ ] Scriba static assets deployed to CDN / public directory
- [ ] HTML templates updated with `scriba-tex-*` CSS/JS includes
- [ ] `<article class="scriba-tex-content">` wrapper added
- [ ] Frontend copy-button regex injection removed
- [ ] Frontend CSS selectors updated (no old class references remain)
- [ ] Frontend `src`-rewriting logic removed
- [ ] Bleach pass wired with `scriba.ALLOWED_TAGS` / `scriba.ALLOWED_ATTRS`
- [ ] CSS sanitizer configured for `transform`, `transform-origin`, `width`, `height`
- [ ] Snapshot comparison run over full problem corpus
- [ ] XSS test suite passes
- [ ] Visual regression screenshots reviewed
- [ ] Render cache invalidated (new cache keys based on `doc.versions`)
- [ ] Rollback branch tagged
- [ ] Feature flag (if used) configured and tested in both states

## 12. Cross-reference

| Document | Relationship |
|----------|-------------|
| [`01-architecture.md`](../spec/architecture.md) | Locked API surface: `Pipeline`, `RenderContext`, `ResourceResolver`, `ALLOWED_TAGS`, `ALLOWED_ATTRS` |
| [`02-tex-plugin.md`](../guides/tex-plugin.md) | TeX port details, HTML output contract, diff vs old renderer, snapshot/XSS tests |
| [`04-roadmap.md`](../planning/roadmap.md) | Release timeline, migration coupling |
| [`07-open-questions.md`](../planning/open-questions.md) | Q7 (bleach vs nh3), Q5 (dark mode trigger) |
