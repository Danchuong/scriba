# Contributing to Scriba

Thanks for your interest in Scriba! This document covers the basics for
working on the library locally.

## Prerequisites

Before cloning the repo you will need:

- **Python 3.10+.** Scriba's `pyproject.toml` declares `requires-python
  = ">=3.10"`, and the CI matrix covers 3.10, 3.11, and 3.12.
- **Node.js 18+.** Required by the KaTeX subprocess worker. Any install
  method works — system package, [nvm](https://github.com/nvm-sh/nvm),
  [volta](https://volta.sh/), or your OS package manager. CI pins
  Node 20. KaTeX itself is vendored inside the wheel at
  `scriba/tex/vendor/katex/katex.min.js`, so no `npm install` is
  required.
- **[`uv`](https://docs.astral.sh/uv/getting-started/installation/).**
  Scriba uses `uv` for environment management, dependency resolution,
  and test runs. Install with the instructions at the link above (the
  one-line curl or Homebrew install both work).

> **Platform note.** Windows is **not** supported for development.
> The Starlark animation sandbox uses a `SIGALRM`-based wall-clock
> timeout for step-budget enforcement, and `signal.SIGALRM` does not
> exist on Windows. Use Linux, macOS, or WSL2. This is documented in
> `SECURITY.md` under "Known limitations".

## Local installation via Homebrew

If you want to install Scriba as a command-line tool on macOS via Homebrew
rather than setting up a dev environment, use the ojcloud tap:

```bash
brew tap Danchuong/tap
brew install scriba
```

See [`homebrew/README.md`](homebrew/README.md) for formula details, supported
architectures (arm64 + x86_64), and upgrade instructions.

## Dev install

Scriba uses a standard PEP 621 / Hatch layout. Fresh-clone quickstart:

```bash
git clone https://github.com/Danchuong/scriba.git
cd scriba
uv sync --dev
uv run pytest -q
```

`uv sync --dev` creates `.venv/` and installs runtime and dev
dependencies in one step. Prefix every Python / pytest command with
`uv run` to pick up that environment (e.g. `uv run pytest
tests/tex/test_snapshots.py`).

If you prefer a vanilla `venv` + `pip` workflow, the equivalent is:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Scriba does not use `pre-commit` hooks, so there is no extra
`pre-commit install` step.

### Bumping the vendored KaTeX version

To refresh the vendored KaTeX copy (e.g. `0.16.11` → `0.16.12`), run:

```bash
scripts/vendor_katex.sh 0.16.12
```

The script downloads the pinned version from jsDelivr, updates
`VENDORED.md` with the new SHA-256, and refreshes `LICENSE`. Commit all
three files together.

## Running tests

```bash
pytest -q
```

The suite covers snapshot HTML output, XSS hardening, the validator, the
pipeline contract, the subprocess worker pool, and the sanitization
allowlist. Snapshots live under `tests/tex/snapshots/` and should only be
updated after manual review against the TeX plugin contract in
`docs/guides/tex-plugin.md`.

## Code style

- Target **Python 3.10+**.
- Follow **PEP 8**.
- Put type hints on all function and method signatures.
- Prefer immutable data (frozen dataclasses, tuples) at public boundaries.
- Keep modules focused and small. Extract helpers rather than growing a
  file past ~800 lines.

## Pull requests

1. Open an issue first for anything non-trivial so we can agree on the
   approach before code is written.
2. Branch from `main`, keep the PR focused, and include tests for any
   behavior change.
3. Run `pytest -q` locally before pushing.
4. Write a descriptive PR body that explains the *why*, not just the
   *what*. Link to the relevant doc section in `docs/` when
   touching the plugin contract.

## Architecture and open questions

The canonical design documents live under `docs/`:

- `spec/architecture.md` — pipeline, workers, renderer protocol
- `guides/tex-plugin.md` — HTML output contract and snapshot spec
- `spec/environments.md` — the v0.2.0 `\begin{animation}` environment
  (and the v0.3+ `\begin{diagram}` environment roadmap)
- `planning/open-questions.md` — unresolved design decisions

## Roadmap pointer

The project is at **v0.9.1**. The `\begin{animation}` environment has
been shipping since v0.2.0 and is fully documented in
`docs/spec/environments.md`. The next milestone is **v1.0.0**
stabilization: API surface lock, extended test coverage, and public
documentation polish. Contributions in those areas are especially
welcome.

By contributing, you agree that your contributions will be licensed under
the project's MIT license.
