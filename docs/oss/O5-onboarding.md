# O5 — Onboarding: Add Scriba to Your Existing LaTeX Pipeline

> The first 15 minutes a new user spends with Scriba. Source of truth: [`../environments.md`](../spec/environments.md).

## 1. Framing

Scriba does **not** create a new project. It plugs into an OJ backend or static site that already stores problem statements as `.tex`. The onboarding story is "install a Python package, register two renderers, feed it the `.tex` you already have, get HTML back".

There is no `scriba init`. There is no starter template. There is no dev server. The user's existing editor, existing repo layout, and existing LaTeX tooling keep working.

## 2. The 15-minute journey

| Minute | Milestone |
|---|---|
| 0:00 | Land on `scriba.dev`. Watch a 60-second capture. See the install command above the fold. |
| 0:30 | `pip install scriba-tex` inside whatever Python env already runs the user's backend. |
| 1:00 | Copy 6 lines of Python from Quick Start. Register the three renderers in a `Pipeline`. |
| 3:00 | Paste the 20-line `binary-search.tex` canon from the docs into an existing problem statement file. |
| 5:00 | Call `pipeline.render(tex)`. Copy the resulting HTML into a throwaway template or `.html` file and open it. The filmstrip renders. |
| 8:00 | Tweak one `\step` and its `\narrate{...}` body. Re-render. See the diff. |
| 12:00 | Author a first animation for the user's own CP problem using the primitive that matches their shape (array, grid, graph, tree, dptable, code). |
| 15:00 | Wire the compile step into the existing problem-upsert hook (Django signal / FastAPI background task / Flask route / static pre-build script). |

## 3. Install

**Primary**: `pip install scriba-tex`

The package drops into the user's existing venv, lockfile, or Poetry/uv/Pipenv project. It has a small dependency footprint (Pydantic v2, a Starlark runtime, no GUI deps).

**Alt for Python-less sites**: none at v0.3. If the user has no Python environment we recommend spinning up a minimal one with `uv` for the pre-build script — it is not worth maintaining a separate distribution channel.

**Rejected**:
- curl-pipe install (security)
- npm wrapper (wrong runtime — Scriba is Python)
- Docker image (heavy; Scriba is a library, not a daemon)
- Homebrew tap (no CLI to install)

## 4. The Quick Start snippet

```python
from scriba import Pipeline, SubprocessWorkerPool
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer, DiagramRenderer

pool = SubprocessWorkerPool()
pipeline = Pipeline(renderers=[
    AnimationRenderer(),
    DiagramRenderer(),
    TexRenderer(worker_pool=pool),
])

with open("problem.tex") as f:
    html = pipeline.render(f.read())

print(html)
```

That snippet is the entire surface a new user has to learn on day one. Everything else is looked up as needed.

## 5. First author experience

The docs cookbook offers the `binary-search.tex` canon as the copy-paste starting point. It exercises:
- `\begin{animation}[id=binsearch, width=60ex]`
- `\shape{arr}{array}{...}` to declare the array
- `\compute{...}` to compute a value at build time
- `\step` + `\highlight{arr.cell[mid]}` + `\narrate{...}` across ~8 frames
- Closing `\end{animation}`

A user who can diff this example against their own problem can ship their first animation without reading the full reference.

## 6. What existing tooling to use

- **Editor**: whatever the user already uses for `.tex` — VS Code with LaTeX Workshop, Neovim with VimTeX, TeXShop, Emacs AUCTeX. They all already understand `\begin{...}` and `\end{...}` blocks. Scriba's commands look like normal LaTeX macros and cause no syntax-highlighting regressions.
- **Formatter**: the user's existing LaTeX formatter works fine. Scriba does not ship `scriba fmt`.
- **Linting**: `python -m scriba lint problem.tex` is the contributor debugging helper; it is optional.
- **Diff review**: normal git diff on `.tex` files.

## 7. Error UX is the single highest-leverage DX investment

A first-time author **will** make mistakes — wrong primitive name, invalid selector, Starlark that touches forbidden builtins, malformed options block. The error output is what decides whether they forgive a v0.3 rough edge. Every error code in `E1001–E1299` follows the Rust-style template (see [`O4-quality-bar.md`](O4-quality-bar.md) §3) with source caret, hint, and a docs URL.

Budget one engineering week purely on error quality before launch. Every code in the range must have:
1. A source caret that points at the right character
2. A hint that describes the likely fix
3. A docs page reachable at `https://scriba.dev/errors/EXXXX`

## 8. What we cut from the pre-pivot onboarding

- `scriba init my-first` scaffold
- 4-file starter template
- `scriba dev` hot-reload server on `localhost:4321`
- VS Code extension install step
- TextMate grammar
- `editorials/hello.scriba` and `editorials/animated.scriba` starter files
- `.scriba` file format entirely

The new onboarding is measurably shorter because Scriba stopped asking the user to adopt a new file format and project layout.

## 9. Graduation path

- **Beginner**: copy the binary-search canon, tweak it for their problem.
- **Intermediate**: mix `\begin{diagram}` (for static illustration) and `\begin{animation}` (for step-through) in the same `.tex` file. Drive one animation from `\compute{}`-generated data.
- **Advanced**: write a thin wrapper that walks their problem corpus, compiles in parallel using the shared `SubprocessWorkerPool`.
