# Contributing to Scriba

Thanks for your interest in Scriba! This document covers the basics for
working on the library locally.

## Dev install

Scriba uses a standard PEP 621 / Hatch layout. Clone the repo and install
the package in editable mode with dev extras:

```bash
git clone https://github.com/ojcloud/scriba.git  # TODO: confirm URL
cd scriba
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

You will also need Node.js 18+ on your PATH for the math worker. KaTeX
itself is vendored inside the wheel at
`scriba/tex/vendor/katex/katex.min.js`, so no separate `npm install` is
required.

### Bumping the vendored KaTeX version

To refresh the vendored KaTeX copy (e.g. `0.16.11` → `0.16.12`), run:

```bash
packages/scriba/scripts/vendor_katex.sh 0.16.12
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
   *what*. Link to the relevant doc section in `docs/scriba/` when
   touching the plugin contract.

## Architecture and open questions

The canonical design documents live under `docs/`:

- `spec/architecture.md` — pipeline, workers, renderer protocol
- `guides/tex-plugin.md` — HTML output contract and snapshot spec
- `spec/environments.md` — the v0.2.0 `\begin{animation}` environment
  (and the v0.3+ `\begin{diagram}` environment roadmap)
- `planning/open-questions.md` — unresolved design decisions

## Roadmap pointer

The next feature milestone is **v0.2.0**, which introduces the
`\begin{animation}` LaTeX environment for step-through CP editorials.
See `docs/spec/environments.md` for the contract in progress.
Contributions targeting that milestone are especially welcome.

By contributing, you agree that your contributions will be licensed under
the project's MIT license.
