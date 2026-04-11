# Agent 8: Security Boundary Audit

**Score: 8.5/10**

## Executive Summary

Strong security posture with deliberate, multi-layered defenses. No CRITICAL or HIGH findings.

## Trust Boundary Diagram

```
UNTRUSTED (.tex input)
    │
    ▼
PARSER (grammar.py) — syntax validation, no execution
    │
    ▼
STARLARK SANDBOX (starlark_worker.py)
  ✓ AST pre-scan rejects: import, exec, eval, __class__, getattr
  ✓ Limited builtins: no file I/O, no network, no class creation
  ✓ Execution limits: 3s timeout, 10^8 steps, 128MB memory
    │
    ▼
SCENE STATE (scene.py)
  ✓ foreach depth ≤ 3, iterable ≤ 10k, array ≤ 10k
    │
    ▼
HTML/SVG GENERATION (emitter.py, primitives/)
  ✓ _escape_html() for narration
  ✓ _escape_xml() for annotations/labels
  ✓ _escape_js() for widget JS
    │
    ▼
TRUSTED OUTPUT (safe HTML/SVG)
```

## Exploit Scenarios Tested

| Attack | Vector | Result |
|--------|--------|--------|
| XSS via narration | `<script>` in \narrate | ✅ BLOCKED by _escape_html() |
| SVG injection | `</text>` in \annotate | ✅ BLOCKED by _escape_xml() |
| Code execution | `import os` in \compute | ✅ BLOCKED by AST rejection |
| Sandbox escape | `x.__class__` | ✅ BLOCKED by attribute blocklist |
| DoS via foreach | `0..999999999` | ✅ BLOCKED by 10k limit |
| DoS via array | `size=999999999` | ✅ BLOCKED by 10k limit |
| JS template injection | `${process.exit()}` | ✅ BLOCKED by _escape_js() |

## Medium Findings

### M1: Grid/Matrix/DPTable Size Bounds Missing

Unlike Array (max 10k), these primitives don't validate max size. Could cause memory pressure with very large values.

### M2: isinstance() Exposed in Sandbox

Not essential for compute blocks. Represents unnecessary surface area (theoretical risk only).

## Low Findings

### L1: Limited Security Documentation

No SECURITY.md or inline comments explaining the three-layer defense.

### L2: No Explicit Sandbox Escape Test Suite

Sandbox is robust but no dedicated tests for escape attempts.

## Dependency Security

Only production dependency: `pygments>=2.17,<2.20` — no known vulnerabilities.
