# 07 — Open Questions

## Purpose

This file tracks decisions the planning and v0.3 pivot intentionally
deferred. Unlike [`out-of-scope.md`](out-of-scope.md) — which records
firm, rationale-backed exclusions — every question here is genuinely open
and will be resolved during or before the implementation phase that needs
it. When a question is resolved, the answer is written into the
authoritative file ([`architecture.md`](../spec/architecture.md),
[`tex-plugin.md`](../guides/tex-plugin.md),
[`environments.md`](../spec/environments.md), or a new contract
file) **and** this entry is updated with a `RESOLVED` note and the commit
SHA where the decision landed.

Implementation engineers: when you hit an ambiguity not listed here, add
it before making a unilateral choice.

---

## Closed by the v0.3 pivot (kept for history)

### ~~Q-old-1. Should Scriba have its own `.scriba` file format?~~

**RESOLVED:** No. Environments live inside regular `.tex` files; see
`environments.md` §1. Closed by the v0.3 pivot.

### ~~Q-old-2. Where do diagram per-step descriptions live (D2 fenced-block design)?~~

**RESOLVED:** Obsolete. The D2-based diagram plugin is cancelled. Narration
for `\begin{animation}` lives inside `\narrate{...}` per
`environments.md` §3.4. The `\begin{diagram}` environment is
single-frame and has no narration.

### ~~Q-old-3. D2 version pinning strategy~~

**RESOLVED:** Obsolete. D2 is no longer a Scriba dependency.

### ~~Q-old-4. MermaidEngine design (jsdom vs Puppeteer)~~

**RESOLVED:** Obsolete. MermaidEngine is removed from the roadmap.

### ~~Q-old-5. Diagram step-mode default (cumulative vs exclusive)~~

**RESOLVED:** Obsolete. There is no runtime step controller.

---

## Still-relevant questions carried from the pre-pivot list

### Q1. Is Pygments a required dependency or an optional extra?

**Status:** unresolved. **Default:** required. Currently a hard dependency
in `pyproject.toml` per the 0.1.1-alpha `CHANGELOG.md`. Revisit only if a
consumer reports an install-size constraint.

### Q2. Naming: `Document` vs `RenderedDocument`, `Block` vs `Fragment`

**Status:** unresolved. **Default:** keep `Document` and `Block`. Revisit
only at the 1.0 API freeze review.

### Q3. PyPI name collision check for `scriba`

**Status:** shipped. `scriba` is claimed on PyPI (v0.1.1-alpha published).
No longer open.

### Q4. KaTeX version pinning strategy

**Status:** resolved. Pinned at `katex@0.16.11` bundled in
`scriba/tex/katex_worker.js`. See 0.1.1-alpha `CHANGELOG.md`.

### Q5. Dark mode trigger (`[data-theme="dark"]` vs `.dark`)

**Status:** resolved. Locked to `[data-theme="dark"]`. See
`01-architecture.md` §CSS.

### Q6. CSS variable prefix (`--scriba-*`)

**Status:** resolved. Locked. See `01-architecture.md`.

### Q7. Sanitization library choice (bleach vs nh3)

**Status:** unresolved. **Default:** mention both, bleach primary in
examples, nh3 secondary. Revisit when bleach deprecates.

### Q8. License

**Status:** resolved. MIT. Locked.

### Q9. `RenderContext.render_inline_tex` auto-wiring via duck typing

**Status:** resolved in 0.1.1-alpha. `Pipeline` duck-types on `name == "tex"`
and callable `_render_inline`, wired via `context_providers`.

### Q10. Copy button feedback duration

**Status:** resolved. 2000 ms, hardcoded.

### Q11. Copy button i18n

**Status:** unresolved. **Default:** English only in 0.x.

### Q12. Plugin namespace in PyPI (`scriba-plugin-*`)

**Status:** unresolved. **Default:** no convention published in 0.x.
Revisit at 1.0.

---

## New questions raised by the v0.3 environments model

### ~~Q21. Starlark worker implementation: Go binary (`starlark-go`) vs pure Python (`google.starlark` or `python-starlark-go`)?~~

**RESOLVED:** (a) Go binary built from `go.starlark.net`, bundled per-platform
(`mac-arm64`, `mac-x64`, `linux-x64`, `linux-arm64`) via `package_data` in the
Scriba wheel — same mechanism as `katex_worker.js`. Rationale: reference
implementation used by Bazel/Buck2/Tilt, native `resolve.AllowRecursion` +
`EvalTimeout` + memory accounting, 5-10x faster than pure-Python wrappers, and
the subprocess JSON-line pattern already exists in `scriba.tex`. CI adds a
`setup-go` job that builds the worker binary before `hatch build` packages the
wheel. To be written into `01-architecture.md` §subprocess workers and
`05-implementation-phases.md` Phase A week A1 when the task is picked up.

---

#### Historical options (kept for context)


**Context.** `environments.md` §5 locks the Starlark language
contract but leaves the host implementation open. The worker must run
out-of-process, honor a 5 s wall-clock timeout, a 10^8 step cap, a 64 MB
memory rlimit, and expose the JSON-line protocol from §5.5.

**Options.**

| | Option | Pros | Cons |
|---|--------|------|------|
| (a) | Ship a compiled Go binary built from `starlark-go` | Reference implementation, `resolve.AllowRecursion = true` is a one-line flag, fastest | Cross-platform binary distribution (macOS arm64, macOS x86_64, Linux arm64, Linux x86_64), supply-chain story, larger wheel |
| (b) | Pure Python host via `google.starlark` (aka `python-starlark-go` bindings) | No binary distribution, pip-installable | Slower, fewer Starlark features implemented, recursion flag may not be exposed |
| (c) | Write a thin wrapper around `tinystark` or similar pure-Python Starlark-lite | Minimal deps | Feature-incomplete; may not support recursion correctly for tree DP |

**Default.** (a), Go binary built from `starlark-go`, bundled per-platform
via the same `package_data` mechanism as `katex_worker.js`. Alternative
path: pure Python at Phase A spike if bundle size is unacceptable.
**Revisit trigger:** Phase A week A1 spike comparing both on the 1 000-node
tree-DP test case.

### Q22. Frame-count hard limit: configurable per project or truly hardcoded at 100?

**Context.** `environments.md` §6.3 locks the hard limit at 100
frames (`E1181`) and the soft warning at 30 (`E1180`).

**Options.**

| | Option |
|---|--------|
| (a) | Truly hardcoded at 100 (current lock). |
| (b) | Configurable via `AnimationRenderer(max_frames=N)` constructor param, default 100. |
| (c) | Configurable via `RenderContext.metadata["max_frames"]`. |

**Default.** (a) for v0.3. Revisit if a real cookbook editorial legitimately
needs 101+ frames.

### Q23. D2 subprocess reuse between renderers — is it still relevant?

**Context.** The pre-pivot plan had a single D2 subprocess shared between
`AnimationRenderer` and `DiagramRenderer`. The v0.3 pivot removes D2.

**Default.** Closed. No D2. Leaving the entry in place as a marker.

### Q24. `RendererError.code` field — add to base class or subclass-specific?

**Context.** Animation/diagram parsing raises `ValidationError` with
`E1xxx` codes per `environments.md`. The existing
`scriba.core.errors.RendererError` has `message` and `renderer` but no
`code` field.

**Options.**

| | Option |
|---|--------|
| (a) | Add `code: str \| None = None` to the base `RendererError` class. |
| (b) | Subclass `AnimationParseError(RendererError)` with the `code` field only on the subclass. |
| (c) | Attach code via `RendererError.__cause__.args[0]` or similar implicit convention. |

**Default.** (a). A `code` field on the base class is a strictly additive
change; consumers who do not care ignore it. Low-cost decision.
**Revisit trigger:** none; apply in Phase A week A1.

### Q25. Theme inheritance: how does `[data-theme="dark"]` propagate from the host page into the inline SVG?

**Context.** SVG is inline, so CSS custom properties on `<html>` cascade
into `<svg>` naturally. But authors may want to override state colors
(`--scriba-state-current-fill`) via a media query in user CSS. The question
is whether Scriba's CSS should re-declare Wong palette under `[data-theme="dark"]`
or rely on the host page cascade.

**Options.**

| | Option |
|---|--------|
| (a) | Scriba ships identical Wong values in both themes (Wong palette is CVD-safe and readable in both). |
| (b) | Scriba ships a dark-theme override block re-declaring the six state variables inside `[data-theme="dark"]`. |
| (c) | Attribute-passthrough: emit `data-theme` on the outer `<figure>` based on `RenderContext.theme`. |

**Default.** (a) for v0.3. Wong values were chosen precisely so they work
in both light and dark backgrounds. **Revisit trigger:** axe-core reports
a contrast failure in dark mode during Phase A week A2.

### Q26. Wong palette exhaustion: what if an author's algorithm needs a 7th semantic state?

**Context.** `environments.md` §3.7 locks the allowed states to six:
`idle`, `current`, `done`, `dim`, `error`, `good`. `\recolor` with any
other value is `E1109`.

**Options.**

| | Option |
|---|--------|
| (a) | Truly locked: six states forever; authors who need more use `\annotate` with colored labels. |
| (b) | Reserve two more Wong palette slots (`--scriba-state-warn`, `--scriba-state-accent`) for v0.4+. |
| (c) | Let authors register custom states via a `\defstate` meta-command. |

**Default.** (a) for v0.3. The six-state set covers every editorial in
the Phase B cookbook. **Revisit trigger:** a cookbook editorial that
legitimately needs a seventh state (not "I want prettier colors"). At
that point, (b) is the next candidate.

### Q27. Math inside `\shape{}{DPTable}{label="$dp[i][j]$"}` — can param strings contain inline LaTeX?

**Context.** Primitive labels often want to be math — `$a_i$`, `$dp[i][j]$`.
The parser accepts quoted strings as param values; the question is whether
those strings should be rendered via `ctx.render_inline_tex` at emit
time.

**Options.**

| | Option |
|---|--------|
| (a) | String params are plain text only; authors who want math use `\annotate` with LaTeX content. |
| (b) | String params are passed through `ctx.render_inline_tex` at SVG emit time, and the result is embedded as `<foreignObject>` inside the `<svg>`. |
| (c) | String params may contain `$...$`, rendered to MathML via KaTeX and sliced into the SVG as `<text>` with `<tspan>` fallback. |

**Default.** (b) for Phase A on label-typed parameters only (`label=`,
`header=`). `<foreignObject>` is widely supported in modern browsers and
degrades to plain text in email clients. **Revisit trigger:** email-client
smoke test shows `<foreignObject>` falling back uglily; at that point,
(c).

### Q28. Cache invalidation: does changing the Starlark worker version bust the content-hash cache?

**Context.** Consumers key their cache on `Document.versions` +
`sha256(source)`. `Document.versions` currently includes `core`, `tex`,
`animation`, `diagram`. The Starlark worker is an external binary; a bug
fix in the worker could change `\compute` output without bumping any of
those integers.

**Options.**

| | Option |
|---|--------|
| (a) | Include `starlark_worker.version` as a synthetic entry in `Document.versions` (e.g., `"animation": "1+starlark=2"`). |
| (b) | Fold Starlark worker version into `AnimationRenderer.version` and bump whenever the worker changes. |
| (c) | Pin the Starlark worker binary version inside the Scriba wheel so it never changes without a Scriba release. |

**Default.** (c). The Starlark worker is bundled as `package_data` exactly
like `katex_worker.js`; it cannot change without a Scriba release, so
`AnimationRenderer.version` is sufficient. **Revisit trigger:** none if
bundling holds. If the worker ever becomes an external binary (like the
pre-pivot D2), switch to (b).

### Q29. Per-environment `id=` collision detection

**Context.** `environments.md` §2.4 allows authors to set
`id=my-scene` on an environment; the auto-fallback is
`"scriba-" + sha256(env_body)[:10]`. Two environments with the same
explicit `id=` in the same `Document` produce colliding HTML `id`s and
break `<figure>:target` styling.

**Options.**

| | Option |
|---|--------|
| (a) | Emit a warning-level error `E1005` on duplicate explicit id within a single render. |
| (b) | Auto-suffix duplicates (`-2`, `-3`) silently. |
| (c) | Hard error `E1005` stops render. |

**Default.** (c). Duplicate ids are author mistakes; failing loud is
better than mysterious CSS targeting bugs. **Revisit trigger:** none.

### Q30. `\narrate{}` with zero-body: `E1150` warning vs silent empty paragraph?

**Context.** `environments.md` §3.4 and §6.2 already specify
`E1150` (warning) for zero narration and emit an empty
`<p aria-hidden="true">`. This question is about whether `E1150` should
escalate to error at frame-count > 10 (an animation with 10+ empty
narrations is almost certainly a mistake).

**Default.** Keep the spec as-is: always warning, never error. Escalation
rules add hidden complexity. **Revisit trigger:** a real editorial where
authors systematically leave narration empty and miss the warning in CI.

### Q31. Accessibility: is one `aria-labelledby` per frame enough, or do addressable parts (`cell[i]`, `node[u]`) need individual `aria-label`s?

**Context.** `environments.md` §8.1 wires frame-level
`aria-labelledby` pointing at the narration paragraph. Individual SVG
`<g data-target="...">` groups are semantically inert to screen readers.

**Options.**

| | Option |
|---|--------|
| (a) | Frame-level labelledby only (current spec). |
| (b) | Per-part `aria-label` automatically derived from `\shape` + `\apply`. |
| (c) | Opt-in per-part labels via an `accessible=true` param. |

**Default.** (a) for v0.3. **Revisit trigger:** accessibility audit by a
screen-reader user during Phase D.

### ~~Q32. KaTeX bundling strategy for the `pip install scriba-tex` UX~~

**RESOLVED:** Option 2 — `katex.min.js` v0.16.11 is now vendored inside the
wheel at `scriba/tex/vendor/katex/katex.min.js` (~275 KB). `katex_worker.js`
loads it via a relative `require()` with a fallback to the global `katex`
module for source checkouts. `_probe_runtime` no longer checks for a global
`katex` install; it only verifies that `node` is on PATH and that the
vendored file is readable. `pip install scriba-tex` now works on any machine
with Node.js — no separate `npm install -g katex` step required.

Supporting files:
- `packages/scriba/scriba/tex/vendor/katex/katex.min.js` — vendored bundle
- `packages/scriba/scriba/tex/vendor/katex/VENDORED.md` — upstream URL, SHA-256, license
- `packages/scriba/scriba/tex/vendor/katex/LICENSE` — KaTeX MIT license copy
- `packages/scriba/scripts/vendor_katex.sh` — refresh script for version bumps
- `docs/scriba/research/KATEX-BUNDLING.md` — original tradeoff analysis

**Revisit trigger.** KaTeX upstream ships a breaking change, or wheel size
becomes a concern (currently a non-issue at ~275 KB).

---

## Process for resolving open questions

1. **Identify the blocker.** The implementing engineer notes which question
   is blocking a specific file or test they need to write.
2. **Review options and default.** If the default is acceptable, apply it.
3. **Escalate if the default is not acceptable.** Comment on the relevant
   planning GitHub issue or open a new one. Describe why the default does
   not work for the case at hand.
4. **Write down the decision.** Once consensus is reached (or after 48
   hours of no objection to the default), write the decision into the
   authoritative file (`01-architecture.md`, `environments.md`, or
   a new contract file).
5. **Update this file.** Add a `RESOLVED: <answer>. Written into <file> in
   commit <sha>.` line to the relevant question section.
6. **Do not re-open resolved questions** without a compelling new argument.

Questions that are not blocking any current implementation phase may wait
until they become blockers. Do not resolve questions speculatively.
