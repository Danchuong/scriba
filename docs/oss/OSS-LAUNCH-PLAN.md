# Scriba OSS Launch Plan — v0.3

> Unified launch plan for Scriba v0.3 after the LaTeX-environments pivot. Source of truth for the environments, commands, primitives, and error codes is [`../04-environments-spec.md`](../spec/environments.md). Each sub-report (O1–O6) drills into one dimension; this file is the ranked synthesis.

---

## TL;DR

**Scriba v0.3** ships as an open-source Python package that adds two new LaTeX environments — `\begin{animation}` and `\begin{diagram}` — to the existing `scriba.Pipeline`. Authors write regular `.tex` problem statements; Scriba compiles them to **zero-JavaScript static HTML + inline SVG**.

- **2 LaTeX environments** (`animation`, `diagram`) implemented as `Renderer`s alongside `TexRenderer`
- **8 inner commands**: `\shape`, `\compute`, `\step`, `\narrate`, `\apply`, `\highlight`, `\recolor`, `\annotate`
- **6 shape primitives**: array, grid, graph, tree, dptable, code
- **6 semantic states**: default, active, visited, candidate, rejected, accepted
- **Starlark `\compute{}`** — deterministic, sandboxed, build-time only
- **Output**: `<figure>` → `<ol>` of `<li class="scriba-frame">`, each with an inline `<svg>` + `<p>` narration. No `<script>`, no custom elements, no hydration.
- **Docs site**: Astro Starlight + Cloudflare Pages + Pagefind (HTML+SVG drops verbatim into MDX — zero runtime)
- **Integrations**: `pip install scriba`, import `Pipeline`, feed `.tex`, get HTML. Examples for Django, FastAPI, Flask, and static generators.
- **Quality bar**: pytest + syrupy, mypy strict, Pydantic v2 IR, Rust-style errors (codes `E1001–E1299`), towncrier, CI on every PR
- **USP**: "two LaTeX environments that compile CP editorial animations into zero-JS static SVG — drop the output into any site, email, or PDF"

**Timeline** (single engineer, aggressive): 6–8 weeks to launch-ready.

---

## What changed from the pre-pivot plan

| Area | Before | After |
|---|---|---|
| Authoring surface | Standalone `.scriba` DSL | Regular `.tex` with two new environments |
| CLI | `scriba init/build/dev/check` | **No CLI**. Consumers call `scriba.Pipeline` from Python. Optional Typer helper for debugging only. |
| Runtime | Lit 3 custom element `<scriba-widget>` | **No runtime**. Output is pre-rendered static HTML + inline SVG. |
| Editor tooling | VS Code language extension | **None** — existing LaTeX tooling works as-is |
| File format | `.scriba` | `.tex` (unchanged from what OJs already author) |
| Runtime package | `packages/scriba-runtime/` | **Deleted** |
| Output shape | DOM that booted a widget | `<figure><ol><li><svg/><p/></li>…</ol></figure>` — works in email, PDF, print, RSS |

---

## 1. API surface (O1)

Scriba is a **Python package** that extends the existing `scriba.Pipeline`. The public surface is:

1. **Two LaTeX environments** in user source: `\begin{animation}[opts] … \end{animation}`, `\begin{diagram}[opts] … \end{diagram}`.
2. **Eight inner commands**: `\shape`, `\compute`, `\step`, `\narrate`, `\apply`, `\highlight`, `\recolor`, `\annotate`.
3. **Six primitives** for `\shape`: array, grid, graph, tree, dptable, code.
4. **Six semantic states** for `\highlight`: default, active, visited, candidate, rejected, accepted.
5. **Python import surface**: `from scriba import Pipeline, RenderContext` plus `from scriba.animation import AnimationRenderer, DiagramRenderer` and `from scriba.tex import TexRenderer`.

Full spec: [`O1-api-surface.md`](O1-api-surface.md)

---

## 2. Documentation site (O2)

**Winner: Astro Starlight + Cloudflare Pages + Pagefind.**

Decisive reason (post-pivot): Scriba output is **static HTML + inline SVG with no runtime**. Starlight's zero-JS-by-default island architecture means an author can paste the compiled `<figure>` directly into an MDX page and it just renders — no `<scriba-widget>`, no hydration, no React wrapper. Every cookbook example on the docs site is the literal output Scriba would generate for a consumer.

Site IA (v0.3 launch — ~20 pages):
- Home, Quick Start (Python), Concepts (environments, primitives, states, Starlark host), Cookbook (canon gallery), Reference (environments, commands, Python API, error codes), Recipes, Integration Guides (Django, FastAPI, Flask, static generators).

Full spec: [`O2-docs-site.md`](O2-docs-site.md)

---

## 3. Integrations (O3)

Scriba integrates by **being imported into whatever already runs your OJ backend or static site**. The consumer calls `Pipeline.render(tex_source)` and receives HTML; how they serve that HTML is their concern.

Tier 1 — ship with v0.3:

| # | Integration | Pattern |
|---|---|---|
| 1 | **Django** | Management command or signal compiles `.tex` problem statements, caches HTML keyed by `(source_hash, scriba_version)`, template renders `{{ problem.html|safe }}`. |
| 2 | **FastAPI** | Background task compiles on problem upsert, stores HTML blob in DB, endpoint returns it. |
| 3 | **Flask** | Same pattern as FastAPI, smaller blueprint example. |
| 4 | **Static site generators** | Pre-build step walks `content/problems/*.tex`, writes `build/problems/*.html`. Demonstrated for Astro, Hugo, and a plain Makefile. |

Dropped as primary targets: Next.js RSC, mdBook preprocessor. Either can consume the pre-compiled HTML via their own fetch/import mechanisms, but they are not first-class shipped examples.

Full spec: [`O3-integrations.md`](O3-integrations.md)

---

## 4. Quality bar (O4)

Unchanged in spirit, rewritten for the new surface:

| Dimension | Target |
|---|---|
| Testing | pytest + syrupy snapshots on HTML+SVG output, 80% line coverage on parser / Starlark host / SVG emitter |
| Error messages | Rust-style with source caret + hint + docs link. Codes `E1001–E1299` (see `../04-environments-spec.md` §12) |
| Type safety | mypy `--strict`, Pydantic v2 for Scene IR, `Protocol` for `Renderer` |
| CLI | Optional Typer helper (`scriba compile file.tex`) for debugging only. Not the primary surface. |
| Semver | Strict from v0.3. Public API = `from scriba import …` and the two environments. |
| Changelog | towncrier, fragments per PR |
| CI | GitHub Actions: ruff, mypy, pytest+syrupy, docs build, PyPI publish on tag |
| Release | `hatch publish` to PyPI, tagged GitHub release, `npx gitnexus`-style reproducible build |
| Docs bar | Every public name has docstring + 1 example. Every error code `E1001–E1299` has a docs page. |

Full spec: [`O4-quality-bar.md`](O4-quality-bar.md)

---

## 5. Developer onboarding (O5)

Onboarding is now "**add Scriba to your existing LaTeX pipeline**", not "start a new Scriba project".

15-minute journey:

| Min | Milestone |
|---|---|
| 0:00 | Land on homepage, see 60s video + `pip install scriba` |
| 0:30 | `pip install scriba` in existing OJ backend venv |
| 1:00 | Import `Pipeline`, register `AnimationRenderer + DiagramRenderer + TexRenderer` |
| 3:00 | Paste the 20-line `binary-search.tex` canon into an existing problem statement |
| 5:00 | `Pipeline.render(tex)` → copy resulting HTML into a test template, see it render |
| 8:00 | Tweak one `\step` / `\narrate` pair, re-render |
| 12:00 | Author a first animation for the user's own CP problem |
| 15:00 | Wire the compile step into the existing problem-upsert hook |

Full spec: [`O5-onboarding.md`](O5-onboarding.md)

---

## 6. USP + launch messaging (O6)

### 1-sentence USP
> Scriba adds two LaTeX environments — `animation` and `diagram` — that compile CP editorial visualizations into zero-JavaScript static SVG. The output drops into any site, email, PDF, or print medium and renders identically.

### Capabilities nobody else combines
1. **Two environments, zero runtime** — LaTeX-native authoring, static SVG output, no `<script>` tag anywhere.
2. **Declarative CP-domain primitives** — `array`, `grid`, `graph`, `tree`, `dptable`, `code` as first-class shapes with semantic states.
3. **Narration-synced step frames** — each `\step` becomes a separate `<li>` with its own rendered SVG and `\narrate{…}` paragraph.
4. **Build-time determinism via Starlark** — `\compute{}` runs sandboxed at build time; same source + version ⇒ byte-identical HTML.
5. **Accessible by construction** — semantic `<figure>/<ol>/<li>/<p>`, real text narration, print stylesheet falls back to a vertical filmstrip.

### Killer demos (LaTeX env code, not standalone DSL)
| Demo | Before | After |
|---|---|---|
| Binary search animation | ~200 LOC hand-SVG+JS | ~25 lines inside `\begin{animation}` |
| BFS walkthrough | 30 min screen recording | ~4 min authoring inside one `.tex` file |
| DP table fill | ~300 LOC matplotlib + imageio | ~20 lines inside `\begin{animation}` |

Full spec: [`O6-usp.md`](O6-usp.md)

---

## 7. Unified task list — v0.3 launch

### Phase 1 — Environments & parser (weeks 1–3)
- [ ] Repo scaffold under `packages/scriba/` with hatch, ruff, mypy strict, pytest, syrupy
- [ ] Pydantic v2 Scene IR (Stage, Frame, PrimitiveInstance, Delta, Narration, Provenance)
- [ ] Environment carve-out + BNF parser for `\begin{animation}` / `\begin{diagram}`
- [ ] 8 inner commands, 6 primitives, 6 semantic states
- [ ] Starlark host via `SubprocessWorkerPool` with deterministic helpers (`range/len/min/max/enumerate/zip`)
- [ ] Error codes `E1001–E1299` wired to Rust-style reporter

### Phase 2 — SVG emitter & CSS contract (week 4)
- [ ] Per-primitive SVG emitters (one file per primitive)
- [ ] CSS class contract (`scriba-figure`, `scriba-frame`, `scriba-stage`, state classes)
- [ ] Print stylesheet: filmstrip → vertical stack
- [ ] Snapshot tests via syrupy for every cookbook canon entry

### Phase 3 — Python integration surface (week 5)
- [ ] Register `AnimationRenderer` / `DiagramRenderer` in `Pipeline` before `TexRenderer`
- [ ] Optional `scriba compile` Typer helper for debugging
- [ ] Tier 1 integration examples: Django, FastAPI, Flask, static generator

### Phase 4 — Docs site (weeks 5–6)
- [ ] Astro Starlight scaffold on Cloudflare Pages
- [ ] ~20 pages: home, quick start, concepts, reference, cookbook, integration guides
- [ ] Every canon cookbook entry rendered live as compiled `<figure>` MDX paste
- [ ] Pagefind search
- [ ] Docs page per error code `E1001–E1299`

### Phase 5 — Quality + release (weeks 6–7)
- [ ] CI: ruff, mypy, pytest, docs build on every PR
- [ ] towncrier changelog
- [ ] PyPI publish on tag via GitHub Actions
- [ ] README with install + 20-line binary-search demo

### Phase 6 — Launch (weeks 7–8)
- [ ] Capture real byte-size numbers for the three killer demos
- [ ] HN post, Twitter thread, CP community announcement
- [ ] ojcloud cuts first real editorial as dogfood

---

## 8. Files

| File | Purpose |
|---|---|
| `OSS-LAUNCH-PLAN.md` | **This file** — unified synthesis |
| `O1-api-surface.md` | Environments, commands, primitives, Renderer Python API |
| `O2-docs-site.md` | Astro Starlight + MDX paste story |
| `O3-integrations.md` | Django, FastAPI, Flask, static generator examples |
| `O4-quality-bar.md` | Testing, errors, types, semver, CI, release |
| `O5-onboarding.md` | "Add Scriba to your existing LaTeX pipeline" journey |
| `O6-usp.md` | USP, killer demos, adoption path, launch messaging |

---

**Status**: Ready for implementation against `../04-environments-spec.md`. Zero-runtime, LaTeX-native, static-SVG-only.
