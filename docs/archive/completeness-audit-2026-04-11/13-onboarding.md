# 13 — Onboarding Walkthrough Audit

**Agent:** 13/14 (Completeness audit — new user onboarding)
**Date:** 2026-04-11
**Scriba version:** v0.5.1 (HEAD eb4f017)
**Persona:** Experienced CP editorial author. Knows Python, LaTeX, and CP.
Zero prior exposure to Scriba. Goal: clone repo, render first animation.

## Scope

Simulate the path from `git clone` to "my first HTML rendered on screen"
using only the in-repo docs a newcomer would plausibly read. Record every
snag, missing link, and doc-hunt. Files in scope: `README.md`,
`CONTRIBUTING.md`, `STABILITY.md`, `CHANGELOG.md`, `docs/tutorial/`,
`docs/guides/`, `docs/spec/`, `examples/`, `scriba/__init__.py` docstring,
`render.py` docstring.

## Onboarding walkthrough (step by step, newcomer POV)

### Step 1 — First impression (README.md)

- **Open `README.md`.** Title + one-line status line lands fast. Value
  prop in the first paragraph is serviceable: "backend Python library
  that renders LaTeX problem statements and CP editorials to
  self-contained HTML fragments."
- **What does Scriba DO?** After 30 seconds I can say: it takes `.tex`
  in, emits HTML + a list of asset basenames. Good.
- **But:** the README is pitched at *library consumers* (people
  embedding Scriba into a tenant backend). I, an editorial author, do
  not want a `Pipeline` + `RenderContext` + `SubprocessWorkerPool`
  four-line import. I want `render.py my_editorial.tex`. The
  `render.py` CLI **is not mentioned in the README at all** (Grep
  confirms). That is the single biggest onboarding miss.
- **Hello world example.** README.md:48–64 shows a Python snippet. It
  uses `RenderContext(resource_resolver=..., theme=..., dark_mode=...,
  metadata={}, render_inline_tex=None)` — five required-looking kwargs
  with no explanation of what any of them mean. A newcomer will cargo-
  cult this and hope.
- **What it does NOT show me:** how to render the `\begin{animation}`
  feature that the README spends a whole paragraph advertising. For
  animations, the hello world is at `docs/tutorial/getting-started.md`
  — but the README never links there.

### Step 2 — Install

- README.md:29 says `pip install scriba`. That is the *consumer* path.
  For a CP author who wants to iterate on `.tex` sources, you want a
  clone + `uv sync` flow.
- **CONTRIBUTING.md:30–51** has the dev install, and it is actually
  good: `git clone`, `uv sync --dev`, `uv run pytest -q`, plus a
  `venv + pip install -e ".[dev]"` fallback. Node 18+ called out,
  platform note about Windows + SIGALRM called out.
- **But I only find this if I open `CONTRIBUTING.md`.** The README never
  points authors at the dev-install path, and "I want to render my
  `.tex`" is not the same mental model as "I want to contribute." A
  newcomer will not think to read CONTRIBUTING.md for install steps.
- **Node 20 specifically:** CONTRIBUTING.md:13 says "Node 18+. CI pins
  Node 20." README.md:34 says "Node.js 18+." Consistent. OK.
- **macOS vs Linux gotcha:** Nothing in README or CONTRIBUTING warns
  about macOS-specific worker behavior. SECURITY.md is referenced for
  "Windows not supported," but macOS-vs-Linux subtleties around the
  KaTeX subprocess worker are not called out anywhere a new user would
  look. (Nothing actually broken — but if one exists it is undocumented.)

### Step 3 — First render

- **Finding the CLI.** Grep `README.md` for `render.py` → zero hits.
  Grep `CONTRIBUTING.md` → zero hits. The only way to discover
  `render.py` is to `ls` the repo root or stumble into it. A newcomer
  **will not find it in under 5 minutes** of doc reading alone.
- **`render.py` itself is well-documented** — the module docstring
  (render.py:1–9) gives four clean invocation patterns: plain, `-o`,
  `--open`, `--static`. Nice UX. But nothing points the user here.
- **Public API (`Pipeline`, `TexRenderer`).** `scriba/__init__.py:1–11`
  has a decent top-level docstring listing the public surface. The
  `__all__` list (lines 33–56) is complete. But there is **no usage
  prose** in the docstring — no "start here, call Pipeline with one
  TexRenderer" tour. A Python user who does `help(scriba)` in a REPL
  gets a structural listing, not a tutorial.
- **Mental-run the README hello world:** constructor arguments work,
  `pipeline.render(...)` is called, but the example renders a trivial
  `\section{Hello}` with an inline `$x^2$` — no animation. So the
  flagship v0.2+ feature is invisible to anyone who copies the README
  snippet and stops.

### Step 4 — First custom animation

- **Where is the grammar?** The README (line 24) points to
  `docs/spec/ruleset.md` for "the full grammar and error catalog." That
  file is **55 KB** of reference material. Useful, but not a tutorial.
- **`docs/tutorial/getting-started.md` IS a tutorial** and it is a good
  one: prelude → `\step` → `\recolor` → `\annotate` → `\apply` →
  `\foreach` → cheat sheet → primitive list. Reads naturally for
  someone with LaTeX background. Nine sections, ~9 KB.
- **Problem: it is not linked from README.md.** `grep -n "tutorial"
  README.md` → zero hits. A user who reads README then
  CONTRIBUTING will never reach this file unless they manually browse
  `docs/`. This is a critical miss — the single best onboarding doc in
  the repo is invisible.
- **`examples/cookbook/` has 15+ full worked animations** (`frog1_dp.tex`,
  `convex_hull_andrew.tex`, the `h01`–`h10` hard set). README does not
  mention them. `docs/tutorial/getting-started.md:290–294` does link
  three of them by name. There is **no `examples/cookbook/README.md`
  or `INDEX.md`** — a user browsing that directory sees a wall of 30
  files (`.tex` and `.html` pairs) with no recommended reading order
  and no difficulty annotation.
- **Recommended reading order across the docs set:** nowhere. No doc
  says "read A, then B, then C." A newcomer bouncing between
  `README.md` → `CONTRIBUTING.md` → `docs/spec/ruleset.md` (55 KB) →
  `docs/tutorial/getting-started.md` is doing so by luck.

### Step 5 — Getting unstuck

- **E-codes.** `docs/spec/error-codes.md` exists and is a proper
  reference (11 KB, E10xx → E1Xxx tables with "Common Fix" columns).
  Good.
- **Discoverability of error-codes.md.** Grep README → zero hits. Grep
  CONTRIBUTING → zero hits. Only reachable by browsing `docs/spec/` or
  following the ruleset cross-reference. When a user hits `E1054` in
  the CLI, they will not know this file exists.
- **`docs/guides/how-to-debug-errors.md`** (5.4 KB) also exists.
  Unlinked from README or tutorial.
- **CONTRIBUTING.md** covers dev setup, code style, and PR flow. It
  does **not** tell a user where to file bugs, what to include in a
  repro, or that a `stability` tag exists (STABILITY.md:9 mentions it).
  No issue-template pointer.
- **STABILITY.md** is genuinely internal/API-consumer-facing, not
  onboarding material. Fine as-is; should not be pushed on newcomers.
- **CHANGELOG.md** is 35 KB and opens with v0.5.1 wave-fix minutiae
  ("Wave 4A", "13-C1", `_TRACEMALLOC_PEAK_LIMIT` at 64 MB). Actively
  confusing for a first-read. Newcomers will bounce.

### Step 6 — Time-to-first-render estimate

- **Best case (user finds `render.py` immediately, has Node + uv
  preinstalled, reads tutorial first):** ~10 minutes. Clone, `uv sync
  --dev`, `uv run python render.py examples/cookbook/frog1_dp.tex
  --open`, done.
- **Realistic case (user follows README, tries the Python snippet,
  hunts for animation docs, eventually lands in tutorial, finally
  discovers `render.py`):** 45–90 minutes. Most of that is doc-hunting
  and confusion about which install path matches their use case.
- **Worst case (user hits a missing Node binary, reads SECURITY.md to
  understand SIGALRM, then tries to debug a `ValidationError` with no
  pointer to `error-codes.md`):** 2–4 hours, and a nontrivial fraction
  of users abandon here.

## Snags encountered (with file:line)

1. **README.md:46–64** — Hello world uses the library API (`Pipeline` +
   `RenderContext` + `SubprocessWorkerPool`), not the CLI. Wrong entry
   point for the CP author persona.
2. **README.md (entire file)** — No mention of `render.py`. No mention
   of `docs/tutorial/getting-started.md`. No mention of
   `examples/cookbook/`. No mention of `docs/spec/error-codes.md`.
3. **README.md:103–107** — "Documentation" section points to a GitHub
   tree URL marked `<!-- TODO: update once public mirror exists -->`.
   Dead/placeholder link for a v0.5.1 release.
4. **README.md:55–58** — `RenderContext(...)` example shows five kwargs
   with no prose explaining `resource_resolver`, `theme`,
   `render_inline_tex`. A cargo-cult trap.
5. **CONTRIBUTING.md:34** — `git clone https://github.com/ojcloud/scriba.git
   # TODO: confirm URL`. Still a TODO at v0.5.1.
6. **CONTRIBUTING.md** — Does not mention `docs/tutorial/getting-started.md`
   or `examples/cookbook/` either. Dev setup + code style only.
7. **examples/cookbook/** — No `README.md` or `INDEX.md`. 30 files in
   a flat list with no recommended order, no difficulty tags, no
   description of what each one demonstrates.
8. **examples/minimal.py:1–4** — Docstring still says "Imports work in
   Phase 1A; calling the pipeline raises NotImplementedError until
   later phases land." At v0.5.1 this is stale and will mislead a user
   who opens the file expecting a working example.
9. **scriba/__init__.py:1–11** — Docstring lists the public surface
   structurally but has no usage example. `help(scriba)` is not a
   tutorial.
10. **CHANGELOG.md:8–40** — Front page of the changelog is
    wave/cluster release-note jargon. Not newcomer-friendly.
11. **docs/spec/error-codes.md** — Exists and is useful, but unlinked
    from README/CONTRIBUTING/tutorial. When a user sees `E1054` they
    will not find this file.
12. **docs/guides/how-to-debug-errors.md** — Same: exists, unlinked
    from the obvious onboarding path.

## Missing docs (prioritized)

**P0 — blocks first render**

- README "Quickstart for editorial authors" section: `git clone` →
  `uv sync --dev` → `uv run python render.py
  examples/cookbook/frog1_dp.tex --open`. Three commands. Would
  collapse time-to-first-render from ~45 min to ~10 min.
- README link to `docs/tutorial/getting-started.md` as "Write your
  first animation."
- `examples/cookbook/README.md` indexing every `.tex` with a one-line
  description and difficulty tag (basic / intermediate / hard-set).

**P1 — blocks getting unstuck**

- README "Troubleshooting" section linking `docs/spec/error-codes.md`
  and `docs/guides/how-to-debug-errors.md`.
- CONTRIBUTING.md "Reporting bugs" section: where to file, what to
  include, the `stability` tag convention.
- CHANGELOG.md "Highlights for new users" preface pointing at the
  tutorial and cookbook instead of wave jargon.

**P2 — longer-term polish**

- `scriba/__init__.py` module docstring: add a 10-line Pipeline usage
  example so `help(scriba)` teaches.
- `render.py --help` (already has argparse) referenced from README.
- Remove/update stale TODOs: CONTRIBUTING.md:34 (clone URL), README.md
  :107 (mirror URL), `examples/minimal.py:1–4` (Phase 1A docstring).
- A doc map at `docs/README.md` giving reading order (tutorial → spec
  → guides → archive).

## Time-to-first-render estimate

| Scenario | Time | Limiting factor |
|----------|------|-----------------|
| Best case | ~10 min | Already has uv + Node; finds `render.py` by `ls`. |
| Realistic | 45–90 min | Doc-hunting. Reads README python snippet first, gets confused, eventually finds tutorial. |
| Worst case | 2–4 hr or abandon | Missing Node, hits a validation error with no E-code pointer, cannot find tutorial, reads CHANGELOG for context (worse). |

## Quick wins (< 1 hour each)

1. **Add a "Quickstart for authors" block to README.md** pointing at
   `render.py` and `examples/cookbook/frog1_dp.tex`. ~15 min.
2. **Add a "Next steps" section to README.md** with four links:
   tutorial, cookbook, ruleset, error-codes. ~10 min.
3. **Write `examples/cookbook/README.md`** indexing every `.tex` with
   one-line descriptions. ~45 min.
4. **Fix the three stale TODOs** (README.md:107, CONTRIBUTING.md:34,
   examples/minimal.py docstring). ~10 min.
5. **Add "Reporting bugs" to CONTRIBUTING.md** with issue-template
   pointer and E-code reference. ~15 min.
6. **Add a usage example to `scriba/__init__.py` docstring.** ~10 min.

Total: under 2 hours for a dramatically better onboarding.

## Longer-term doc work

- `docs/README.md` with a reading order and a doc map.
- Reorganize README.md into two personas: "I want to render animations
  (author)" vs "I want to embed Scriba in my backend (library
  consumer)." Currently the second persona dominates.
- Move consumer embedding docs (`Sanitize before embedding`, `Serving
  static assets`) out of the top-level README into
  `docs/guides/embedding.md`, leaving the README lean.
- A `docs/guides/troubleshooting.md` that joins
  `how-to-debug-errors.md`, `error-codes.md`, and common install
  gotchas (Node missing, macOS permission prompts, SIGALRM on Windows)
  into a single page.
- A 5-minute screencast / asciinema of `render.py` in action linked
  from README. Optional but high-impact.

## Severity summary

| Area | Severity | Notes |
|------|----------|-------|
| README entry point wrong for authors | HIGH | Pushes library API, hides CLI and tutorial. |
| Tutorial unlinked from README | HIGH | Best onboarding doc in the repo is invisible. |
| `render.py` undocumented in README/CONTRIBUTING | HIGH | CLI exists and is good; nobody can find it. |
| `examples/cookbook/` has no index | HIGH | 30 flat files, no reading order. |
| Error-codes reference unlinked | MEDIUM | Exists, useful, but discoverability = 0. |
| Stale TODOs in README/CONTRIBUTING/minimal.py | MEDIUM | Erodes trust in a v0.5.1 release. |
| CHANGELOG opens with wave jargon | MEDIUM | Confuses newcomers who read CHANGELOG for context. |
| CONTRIBUTING missing bug-report flow | MEDIUM | Users have nowhere to go when stuck. |
| `scriba/__init__.py` docstring has no example | LOW | `help(scriba)` is structural, not instructional. |
| macOS/Linux worker gotchas undocumented | LOW | No evidence anything is broken; flag as unknown. |

**Bottom line:** Scriba v0.5.1 has *all the right docs* — a solid
tutorial, a thorough ruleset, a full error-code catalog, a working CLI,
and a deep cookbook. They are simply not wired together. A newcomer
following the README alone never reaches any of them. The highest-value
fix is under one hour of README editing: add the `render.py` quickstart
and four "Next steps" links. Everything else in the Quick Wins list
compounds from there.
