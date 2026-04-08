# Security Policy

## Supported versions

Scriba is pre-1.0. Only the current `0.1.x` alpha line receives security
fixes.

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** rather than opening
a public issue. Email:

`security@ojcloud.dev`  <!-- TODO: confirm email before first public release -->

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

## Out of scope

- **Consumer-side sanitization.** Scriba intentionally does not sanitize
  its output; it ships `scriba.ALLOWED_TAGS` / `ALLOWED_ATTRS` for use
  with `bleach`. Consumers are responsible for running a vetted
  sanitizer before embedding HTML in a page.
- Issues in third-party dependencies (KaTeX, Pygments, Node.js) unless
  Scriba's usage of them is the root cause.
- Denial of service through inputs that exceed already-documented caps.
