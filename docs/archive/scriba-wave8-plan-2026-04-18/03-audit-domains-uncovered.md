# Wave 8 — Audit Domains Not Yet Covered

Waves 5–7 covered correctness, security, IPC robustness, KaTeX edges, memory, browser compat, i18n, and CSP planning. The seven domains below have never been the primary focus of an audit. Each is a candidate for a Wave 8 audit pass with one agent per domain.

---

## P1 — CLI Ergonomics + Error UX

**Why:** Scriba's first impression is the CLI. Every error a user sees from `render.py` is the product's voice. We have never measured what that voice sounds like end-to-end.

**Scope:**
- Every flag in `render.py`: is the help text accurate? Are short forms consistent? Are required vs optional clearly signalled?
- Every error path: does the user get a single actionable message, or a Python traceback?
- Exit codes: are they meaningful and documented, or is everything `1`?
- `--help` quality: examples present? common workflows covered?
- Handling of common mistakes: wrong file extension, missing `\begin{animation}`, output path collisions, tty vs non-tty colour output.

**Deliverables:** finding list with severity, "before/after" stderr transcripts, recommended help text revisions.

---

## P2 — Docs Drift vs Code

**Why:** The codebase has moved through 7 waves of fixes. Docs were updated opportunistically, not systematically. There is no automated check that examples in the docs still parse, or that documented flags still exist.

**Scope:**
- Every code block in `docs/` and `README.md`: does it actually run?
- Every flag and env var mentioned: does it exist in the current code?
- Every error code referenced: does it match the emitted text?
- Tutorial fixtures: do they still render without warnings on the current build?
- Public API surface (anything imported by `scriba` package): does docstring coverage match reality?

**Deliverables:** drift list, broken-example list, suggested doc-test harness so this doesn't repeat.

---

## P3 — Animation Timing + Easing Correctness

**Why:** Timing is the product. We have never audited whether stated durations match observed durations, whether easing curves match spec, or whether `prefers-reduced-motion` produces a consistent visual reduction across primitives.

**Scope:**
- Stated `duration=` vs measured WAAPI animation length.
- Easing curves: do per-primitive defaults match the documented curve names?
- Stagger and chain semantics: is there phase drift after N steps?
- `prefers-reduced-motion`: does every primitive reduce the same way (instant snap vs short fade), or is it inconsistent?
- Frame stepping: is `\step` advancing exactly one logical frame, or are there off-by-one cases?

**Deliverables:** per-primitive timing table (stated vs observed), inconsistency list, recommended canonical easing token set.

---

## P4 — SVG Output Quality Cross-Resolution

**Why:** SVG output is consumed at screen, retina, print, and zoomed contexts. We have never verified it renders correctly across all four.

**Scope:**
- Stroke widths under heavy zoom: hairlines disappearing or doubling.
- Text scaling: KaTeX-rendered math at 200% zoom and at print DPI.
- Marker (arrowhead) positioning under viewport scaling.
- `viewBox` correctness when content overflows the declared bounds.
- Print stylesheet: do dark-mode colours invert correctly, do annotations stay readable on white paper?
- Retina (2x): are any raster fallbacks blurry?

**Deliverables:** screenshot matrix (zoom × theme × medium), defect list, `@media print` recommendations.

---

## P5 — Public API Stability Surface

**Why:** Anything importable from the `scriba` package is an implicit contract. We have refactored internals freely; we have never inventoried what the contract actually is.

**Scope:**
- Inventory every public name (no leading underscore) reachable from top-level imports.
- Classify: intentional public API vs accidental leak.
- For intentional: document. For accidental: rename with `_` prefix or move.
- Re-exports: are they intentional or copy-paste?
- Version policy: is there one? (Probably not.) Recommend semver guarantees per surface.

**Deliverables:** public-API inventory, accidental-leak list, suggested `__all__` declarations, draft compatibility policy.

---

## P6 — Performance Benchmarks (No Baseline)

**Why:** We have no baseline. We do not know whether v0.8.2 is faster or slower than v0.7. Every "this feels slow" report is currently un-actionable.

**Scope:**
- Establish a benchmark suite: small / medium / large fixture, single-block / many-blocks, with-math / no-math, with-Starlark / no-Starlark.
- Measure: total render time, per-phase split (parse / compute / KaTeX / emit), peak RSS, output bytes.
- Capture a baseline against current `main`.
- Add CI job that flags >10% regression on the baseline set.
- Identify obvious wins: caching opportunities, redundant work across blocks, hot loops worth profiling.

**Deliverables:** benchmark suite, baseline numbers checked in, regression-flagging CI recipe, top 5 optimisation candidates with measured wins.

---

## P7 — Accessibility Deep Dive

**Why:** Wave 5 covered ARIA and contrast. We have never walked through a rendered animation with a screen reader. We have never tested keyboard-only operation of player controls. We have never tested with Windows High Contrast active.

**Scope:**
- Screen reader walkthrough on at least three readers (NVDA, VoiceOver, JAWS) for one tutorial fixture.
- Keyboard-only: every player control reachable, focus visible, focus order logical.
- Forced-colors / High Contrast: does the rendering still convey state, or do all our state colours collapse?
- Live region announcements: when a step advances, does the reader announce it appropriately (or annoyingly)?
- Math accessibility: KaTeX's `aria-hidden`/`aria-label` strategy — is it actually consumed?
- `narrate` blocks: are they read at the right moment in the flow?

**Deliverables:** per-reader transcript notes, keyboard nav defect list, High Contrast screenshots, recommended ARIA fixes.

---

## Recommended Wave 8 Sequencing

1. Architecture work (CSP migration — 01-architecture-csp-migration.md) first, because it touches output shape and would invalidate any audit done before it.
2. Audit domains in parallel after that, one agent per domain.
3. Triage findings into Round A/B/C as Wave 7 did, then ship.
4. Defer items move from `02-deferred-technical-debt.md` only when their trigger fires.
