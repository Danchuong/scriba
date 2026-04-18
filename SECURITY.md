# Security Policy

## Supported versions

Scriba is pre-1.0. The current `0.9.x` line and the previous minor `0.8.x`
receive security fixes. All earlier releases are no longer supported.

| Version  | Status              | Security fixes |
|----------|---------------------|----------------|
| 0.9.x    | Current             | Yes            |
| 0.8.x    | Previous minor      | Yes            |
| 0.7.x and below | Unsupported  | No             |

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** rather than opening
a public issue.

The Scriba source currently lives in a private monorepo and is not yet
published on a public GitHub mirror. Until the public mirror exists,
coordinate directly with the OJCloud maintainers through an existing
private channel. Once the public GitHub mirror is live, open a
[GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories/guide-to-privately-reporting-a-security-vulnerability)
on the mirror repository instead of an issue or PR. The maintainer
contact list is tracked in
[`.github/SECURITY_CONTACTS.md`](.github/SECURITY_CONTACTS.md) (a
pre-release stub until the public mirror goes live).

Include a clear description, reproduction steps, affected version, and
any proof-of-concept input. We aim to acknowledge reports within a few
business days and will coordinate disclosure with you.

## In scope

- XSS or HTML injection in Scriba's rendered output, including via
  `\href`, `\url`, `\includegraphics`, `lstlisting`, or attribute
  smuggling.
- Subprocess sandboxing issues in the KaTeX worker harness
  (`SubprocessWorkerPool` / `SubprocessWorker`).
- Resource-exhaustion bypasses of the source-size cap
  (`MAX_SOURCE_SIZE`) or math-item cap (`MAX_MATH_ITEMS`).
- Path traversal or unsafe URL resolution in `resource_resolver`
  handling.
- Sandbox escape from the Starlark animation worker (see
  "Known limitations" below for platform caveats).

## Out of scope

- **Consumer-side sanitization.** Scriba intentionally does not sanitize
  its output; it ships `scriba.ALLOWED_TAGS` / `ALLOWED_ATTRS` for use
  with `bleach`. Consumers are responsible for running a vetted
  sanitizer before embedding HTML in a page.
- Issues in third-party dependencies (KaTeX, Pygments, Node.js) unless
  Scriba's usage of them is the root cause.
- Denial of service through inputs that exceed already-documented caps.

## Known limitations

- **Windows is not a supported development or runtime target.** The
  Starlark animation-worker sandbox uses a SIGALRM-based wall-clock
  timeout for step-budget enforcement. `signal.SIGALRM` is not
  available on Windows, so the sandbox falls back to the step counter
  only — without a hard wall-clock kill, a pathological script could
  run longer than the documented budget. Scriba's CI matrix covers
  Linux and macOS only; Windows is untested. See
  `docs/spec/starlark-worker.md` §6.1 for the sandbox design.
- **Vendored KaTeX is pinned to 0.16.11.** The latest upstream KaTeX
  at the time of this audit is `0.16.22`. The vendored copy has not
  yet been bumped because KaTeX minor releases have historically
  altered HTML class names and markup in ways that could regress
  Scriba's snapshot tests. A visual-regression suite is required
  before merging the upgrade. See `scripts/vendor_katex.sh` for the
  upgrade procedure and the "Vendored dependencies" section below.
- **No bundler sandbox for included assets.** `\includegraphics` and
  image resource resolution enforce path-traversal checks at the Python
  layer but do not run a separate browser-style sandbox; do not feed
  Scriba untrusted resource directories.

## Vendored dependencies

Scriba ships several third-party assets inside the wheel. Upgrades are
done out-of-band rather than via `pip install`, so they are listed here
for auditability:

| Dependency | Version  | Location inside wheel                 | Upgrade procedure |
|------------|----------|---------------------------------------|-------------------|
| KaTeX      | 0.16.11  | `scriba/tex/vendor/katex/`            | `scripts/vendor_katex.sh <version>` |
| Pygments CSS | pre-generated at build time | embedded in rendered HTML | bump `pygments` in `pyproject.toml` and rebuild |

The KaTeX copy includes `katex.min.js`, `katex.min.css`
(woff2-only, with `.woff`/`.ttf` fallbacks stripped), the
`KaTeX_*.woff2` font files, the upstream `LICENSE`, and a `VENDORED.md`
manifest with version + SHA-256. See `scripts/vendor_katex.sh` for the
full refresh procedure, including the pre-upgrade checks that should run
before any KaTeX minor-version bump.
