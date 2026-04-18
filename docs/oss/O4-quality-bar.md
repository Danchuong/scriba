# O4 — Quality Bar (v0.3)

> The standards a Scriba v0.3 release must meet before it ships. Source of truth for environments, commands, and error codes: [`../environments.md`](../spec/environments.md).

## 1. Targets at a glance

| Dimension | Target |
|---|---|
| Testing | pytest + syrupy snapshot tests on HTML+SVG output, 75% line coverage enforced in CI (`fail_under = 75` in `pyproject.toml`); aspirational target is 80% |
| Error messages | Rust-style with source caret + hint + docs link (codes `E1001–E1299`) |
| Type safety | mypy `--strict`, Pydantic v2 for Scene IR, `typing.Protocol` for `Renderer` / `WorkerPool` |
| Determinism | Byte-identical output across runs and OSes for the full cookbook canon (CI matrix: linux, macos; py3.11, py3.12) |
| Semver | Strict from v0.3; public API frozen per [`O1-api-surface.md`](O1-api-surface.md) |
| Changelog | towncrier, one fragment per PR, compiled at release |
| Contributor docs | `CONTRIBUTING.md`, `ARCHITECTURE.md`, `scripts/hack.sh` (hack on Scriba in 10 minutes) |
| CI | GitHub Actions: ruff, mypy, pytest+syrupy, docs build, PyPI publish on tag |
| Release | `hatch publish` to PyPI on tagged GitHub release |
| Docs bar | Every public Python name has a docstring + 1 example; every error code `E1001–E1299` has a dedicated docs page |

## 2. Testing

### 2.1 Unit tests
- Parser: every production in the BNF from `../environments.md` §2, positive and negative cases.
- Each of the 8 inner commands: valid forms, invalid forms, each error code it can emit.
- Each of the 6 primitives: parameter validation, selector resolution.
- Starlark host: sandbox rules (no `time`, no `random`, no I/O), CPU/memory caps, deterministic re-runs.

### 2.2 Snapshot tests (syrupy)
- Every cookbook canon `.tex` file compiles to an HTML+SVG snapshot checked into the repo.
- Snapshots include the full `<figure>` down to attribute order. Any diff fails CI.
- Runs on linux + macos on both py3.11 and py3.12.

### 2.3 Property tests
- Round-trip: parse → IR → emit → re-parse emitted narration; narration text preserved modulo whitespace normalization.
- Determinism: compile the same source twice in the same process and across two fresh subprocesses; output must be byte-identical.

### 2.4 Coverage
- 80% line coverage on `scriba.core`, `scriba.animation`, `scriba.tex`, `scriba.workers`. Measured via `coverage.py`.

## 3. Error messages

All errors follow the Rust-style template:

```
error[E1118]: unknown primitive 'heap'
  ╭─[binary-search.tex:12:12]
  │
12│   \shape{h}{heap}{size=8}
  │           ^^^^ primitive 'heap' is not one of the 6 shipped primitives
  │
  = hint: did you mean `array`? `heap` is deferred to v0.4.
  = docs: https://scriba.dev/errors/E1118
```

- All codes live in the `E1001–E1299` range defined in `../environments.md` §12.
- Every code has a stable URL `https://scriba.dev/errors/EXXXX`.
- Every code has a dedicated docs page (see [`O2-docs-site.md`](O2-docs-site.md) §3).
- `ScribaError.__str__` emits the full formatted block; `ScribaError.code` exposes the numeric code; `ScribaError.spans` exposes source locations for programmatic tooling.

## 4. Type safety

- `mypy --strict` on the entire `scriba` package with zero `# type: ignore` except at clearly marked subprocess boundaries.
- Scene IR is Pydantic v2 `BaseModel` throughout — parsed values are validated at IR boundaries, not inside rendering code.
- `Renderer`, `WorkerPool`, `RenderContext` are `typing.Protocol`s so consumers can plug in custom implementations without inheriting.

## 5. Determinism

- The Starlark host disables `time`, `random`, file I/O, and network.
- `SubprocessWorkerPool` seeds nothing and accepts no clock.
- CI runs `scripts/check-determinism.sh` which compiles every canon `.tex` twice on two OSes and diffs the bytes.
- Violations are treated as critical bugs and block release.

## 6. Semver and public API

- The public API is exactly what [`O1-api-surface.md`](O1-api-surface.md) §3.3 lists. Adding a new public name is a MINOR bump. Changing a signature is a MAJOR bump.
- The HTML / CSS contract in `../environments.md` §9 is **also** part of the public API — changing a class name is a MAJOR bump.
- Error codes are append-only within `E1001–E1299`. Removing a code is a MAJOR bump; changing its message text is not.

## 7. Changelog and release

- `towncrier` with categories: `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`.
- One fragment file per PR under `changes/`. CI fails if a PR modifies `src/` without adding a fragment.
- Tagged GitHub releases trigger `hatch publish` to PyPI via Actions.
- Release notes auto-link every `E1XXX` mention to its docs page.

## 8. CI pipeline

```
lint     → ruff check + ruff format --check
types    → mypy --strict
test     → pytest + syrupy (matrix: ubuntu, macos; py3.11, py3.12)
determinism → scripts/check-determinism.sh
docs     → astro build inside docs/
publish  → on tag: hatch publish to PyPI
```

Every stage must be green for merge. No "retry until green" culture — flaky tests are bugs.

## 9. Optional Typer helper

A single `python -m scriba` entry point exists purely for contributor debugging. It is not the product, is not marketed, and has two subcommands:

- `compile file.tex [--out file.html]`
- `lint file.tex`

No `init`, `build`, `dev`, or `check`. No scaffolding. No dev server. No hot reload.

## 10. Security & sandbox

- Starlark worker runs in a subprocess with `RLIMIT_CPU`, `RLIMIT_AS`, and a hard wall-clock timeout.
- No file system access inside Starlark. No `os`, no `subprocess`, no `open`.
- Parser rejects any `\input{}` / `\include{}` inside an environment body (`E1104`).
- Fuzzing corpus seeded with malformed `.tex` and weird Unicode. Runs weekly in CI.

## 11. Docs bar

- Every public Python name: docstring + 1 runnable example in the docstring.
- Every error code `E1001–E1299`: dedicated docs page with source that triggers it, rendered error output, and the fix.
- Every cookbook canon entry: `.tex` source + compiled `<figure>` + narrative walkthrough.

Miss any of those on a public name and CI fails the docs-completeness check.
