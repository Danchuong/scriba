# O3 — Reference Integrations

> How consumers wire Scriba into an existing system. Source of truth: [`../environments.md`](../spec/environments.md).

## 1. Integration model

Scriba is a Python package. Consumers:

1. `pip install scriba-tex` into whatever Python environment already runs their OJ backend or static site build.
2. Import `Pipeline`, `AnimationRenderer`, `DiagramRenderer`, `TexRenderer`.
3. Build a `Pipeline` once at process start.
4. Feed `.tex` source into `pipeline.render(...)` whenever a problem is created or updated.
5. Cache the resulting HTML keyed by `(source_hash, scriba_version)` because Scriba output is deterministic.
6. Serve the HTML via whatever templating/response mechanism the host framework already uses, and load `/scriba.css` once per page.

There is no HTTP API, no daemon, no sidecar, no file watcher. Scriba is a pure function from `str → str` with a subprocess worker pool for Starlark sandboxing.

---

## 2. Tier 1 — shipped with v0.3

### 2.1 Django

**Pattern**: management command + model signal

```python
# problems/scriba_renderer.py
from functools import lru_cache
from scriba import Pipeline
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer, DiagramRenderer
from scriba.workers import SubprocessWorkerPool

@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    pool = SubprocessWorkerPool(max_workers=4)
    return Pipeline(renderers=[
        AnimationRenderer(worker_pool=pool),
        DiagramRenderer(worker_pool=pool),
        TexRenderer(worker_pool=pool),
    ])
```

```python
# problems/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Problem
from .scriba_renderer import get_pipeline

@receiver(post_save, sender=Problem)
def compile_statement(sender, instance, **kwargs):
    html = get_pipeline().render(instance.statement_tex)
    Problem.objects.filter(pk=instance.pk).update(statement_html=html)
```

Template usage: `{{ problem.statement_html|safe }}`. The site's base template loads `/static/scriba.css` once.

### 2.2 FastAPI

**Pattern**: background task on problem upsert

```python
from fastapi import FastAPI, BackgroundTasks
from scriba import Pipeline  # plus renderers

app = FastAPI()
pipeline = Pipeline(renderers=[...])

async def compile_and_store(problem_id: str, tex: str):
    html = pipeline.render(tex)
    await db.problems.update_one({"_id": problem_id}, {"$set": {"html": html}})

@app.put("/problems/{pid}")
async def upsert(pid: str, payload: ProblemIn, bg: BackgroundTasks):
    await db.problems.upsert(pid, payload)
    bg.add_task(compile_and_store, pid, payload.tex)
    return {"status": "queued"}
```

### 2.3 Flask

**Pattern**: blueprint with explicit cache table

```python
from flask import Blueprint, current_app
from scriba import Pipeline
# ...

bp = Blueprint("problems", __name__)
pipeline = Pipeline(renderers=[...])

@bp.post("/problems/<pid>/compile")
def compile_problem(pid):
    tex = current_app.db.problems.get_tex(pid)
    html = pipeline.render(tex)
    current_app.db.problems.set_html(pid, html)
    return {"ok": True}
```

### 2.4 Static site generators

**Pattern**: pre-build step writes HTML files

```python
# scripts/build_problems.py
import hashlib, pathlib
from scriba import Pipeline
# ...

pipeline = Pipeline(renderers=[...])
SRC = pathlib.Path("content/problems")
OUT = pathlib.Path("build/problems")

for tex_file in SRC.glob("*.tex"):
    tex = tex_file.read_text()
    html = pipeline.render(tex)
    (OUT / f"{tex_file.stem}.html").write_text(html)
```

Demonstrated in the repo for:
- **Astro** — invoked from `astro.config.mjs` via a pre-build hook
- **Hugo** — invoked from a Makefile target before `hugo`
- **Plain Makefile** — simplest possible version for hand-rolled static sites

---

## 3. Caching contract

Scriba output is deterministic: same source + same `scriba` version ⇒ byte-identical HTML. All integrations should cache on:

```
cache_key = sha256(tex_source) + scriba.__version__
```

Invalidate whenever either changes. No TTL needed.

---

## 4. What was dropped as a primary target

- **Next.js RSC page** — can still import the pre-compiled HTML and use `dangerouslySetInnerHTML`, but we no longer ship it as a shipped example. The RSC model added ceremony that obscured the point.
- **mdBook preprocessor** — a Rust preprocessor shelling out to Python was the wrong shape. Consumers who want mdBook integration can write a thin wrapper; it is not a launch priority.
- **Lit 3 custom element runtime loader contract** — deleted. There is no runtime.
- **`defineScribaElement` / `SCRIBA_RUNTIME_VERSION`** — deleted.

---

## 5. Directory scaffold

```
scriba/
├── packages/
│   └── scriba/             # core Python package
│       ├── src/scriba/
│       │   ├── core/        # Pipeline, RenderContext
│       │   ├── tex/         # TexRenderer (existing)
│       │   ├── animation/   # AnimationRenderer, DiagramRenderer
│       │   ├── workers/     # SubprocessWorkerPool
│       │   └── errors.py    # E1001–E1299
│       └── tests/
└── examples/
    ├── django/
    ├── fastapi/
    ├── flask/
    └── static-site/
        ├── astro/
        ├── hugo/
        └── makefile/
```

No `packages/scriba-runtime/`. No `packages/scriba-astro/` (Astro consumers use the pre-build script pattern instead).

---

## 6. Cross-cutting work that lands in core

Instead of a runtime contract, the cross-cutting work is:

- **Deterministic output guarantee** — snapshot-tested in CI
- **CSS class contract** (`../environments.md` §9) — frozen part of the public API
- **`scriba.css`** — a single canonical stylesheet that realizes the class contract; consumers ship it unchanged or theme via CSS custom properties
- **Versioned cache key helper** — `scriba.cache_key(tex_source) -> str`, exported so integrations do not have to invent their own hashing
