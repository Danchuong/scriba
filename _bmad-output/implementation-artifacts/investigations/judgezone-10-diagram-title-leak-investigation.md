# Investigation: JudgeZone #10 — static-diagram SVG `<title>` leaks the internal id slug

## Hand-off Brief

1. **What happened.** (Confirmed) Every static `\begin{diagram}` figure's inner `<svg><title>` renders the widget's internal `id=` slug — even when the author also supplies `label=`. The bug is worse than the report assumed: `label=` **is** a valid, tested, wired diagram parameter today, but it is wired only to the outer `<figure>`'s `aria-label`. The inner `<svg>` — the element that actually owns `role="img"` and drives the native hover tooltip — never sees the label at all, so it always falls through a shared fallback chain to `scene_id`.
2. **Where the case stands.** Concluded (root cause + fix site both Confirmed). No source files were modified — this is investigation-only.
3. **What's needed next.** Implement the fix sketch below (§ Recommended Fix) at `scriba/animation/renderer.py:1113-1129` and `scriba/animation/_html_stitcher.py:849-871`, plus a matching change to the shared fallback in `scriba/animation/_frame_renderer.py:1847-1875` so the same class of bug can't recur on the animation path's untitled/unnarrated-step edge case (found during this investigation, see Finding 6).

## Case Info

| Field            | Value |
| ---------------- | ----- |
| Ticket           | JudgeZone #10 (LOW, a11y/cosmetic) + Structural Ask 5 (accessible-name policy audit) |
| Date opened      | 2026-07-10 |
| Status           | Concluded |
| System           | scriba @ 13eadc7 (0.34.0) |
| Evidence sources | source (renderer.py, _html_stitcher.py, _frame_renderer.py, ast.py, emitter.py, primitives/*), docs/spec/smart-label-ruleset.md (R-15), docs/spec/ruleset.md §7.5, tests/unit/test_env_options_wired.py, tests/unit/test_filmstrip_aria.py, live renders of 4 repro `.tex` files |

## Problem Statement

**Bug #10:** `\begin{diagram}[id="internal-slug-x"]` emits `<title>internal-slug-x</title>` inside the figure's SVG. The reporter's proposed policy: (1) use `label=` for `<title>`/aria when present, (2) else omit `<title>` entirely (keep `role="img"`, and `aria-label` from `label` when present), (3) never fall back to `id`. Reporter believes animations are unaffected since the 0.33.0 tooltip cleanup.

**Structural Ask 5:** audit the accessible-name story for every widget/output shape scriba emits — static diagram, animation player (frames + container), substories, tex figures, primitive-level tooltips (graph edges, annotations), image embeds — everywhere `<title>`, `aria-label`, `aria-labelledby`, or `role=` is emitted. Determine what feeds the name today, whether the internal id ever surfaces, and score each against the reporter's 3-point policy.

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| `scriba/animation/_frame_renderer.py:1847-1896` (`_emit_frame_svg`) | Available (Confirmed) | Shared title-fallback chain for **every** SVG root: `frame.title` → stripped `narration_html` → `scene_id`. One function serves diagram, filmstrip, and interactive modes. |
| `scriba/animation/_html_stitcher.py:829-871` (`emit_diagram_html`) | Available (Confirmed) | Builds the diagram `<figure>`; `label` reaches the figure's `aria-label` (line 863) but is never passed into the `_emit_frame_svg` call (854-861). |
| `scriba/animation/renderer.py:1067-1149` (`DiagramRenderer.render_block`) | Available (Confirmed) | `scene_id` sourced from `ir.options.id` (1096-1098); frame built via `_snapshot_to_frame_data(snap, 1, scene_id, ctx)` at line 1115 with **no** `label=`/`title=` kwarg — label is only forwarded to `emit_html(..., label=...)` at 1122-1129, i.e. figure-level, not frame-level. |
| `scriba/animation/parser/ast.py:525-531` (`AnimationOptions`) | Available (Confirmed) | `id: str \| None` and `label: str \| None` are both real, parsed fields — shared by animation and diagram envs (diagram reuses `SceneParser`/`AnimationOptions`). |
| `scriba/animation/emitter.py:107-130` (`FrameData`) | Available (Confirmed) | `title: str \| None = None` — the same field `\step[title="..."]` populates; diagram path never populates it. |
| `tests/unit/test_env_options_wired.py:104-106` | Available (Confirmed) | `test_diagram_label_reaches_figure` asserts `aria-label="A small BST"` is in the **figure** HTML. No sibling assertion anywhere in this file (or `test_diagram_renderer.py`, `test_phase_b_diagram.py`) checks the SVG's own `<title>` content — this is the exact coverage gap that let the bug ship. |
| `docs/spec/smart-label-ruleset.md:1024-1043` (Rule R-15) | Available (Confirmed) | Normative **MUST**: "The `<title>` content MUST describe the animation frame in natural language." `scene_id` is not natural language — the current diagram output is a live violation of the project's own spec, not just the reporter's opinion. |
| `tests/unit/test_filmstrip_aria.py:114-124` | Available (Confirmed) | This is R-15's own cited "Test ref" (`test_frames_with_label_uses_frame_label`). It asserts on the **filmstrip figure's `aria-label`**, not on `<title>` content at all — the spec's test-traceability is stale/mismatched, which is part of why the gap was invisible. |
| 4 live renders (see Reproduction Plan) | Available (Confirmed) | `render.py` executed against 4 hand-written `.tex` repros; raw HTML inspected for `<title>`, `aria-label`, `role`, `aria-labelledby`. |

## Confirmed Findings

### Finding 1: `label=` is already an accepted, tested diagram parameter today
**Evidence:** `ast.py:530-531`; `renderer.py:1121-1129` (comment: "Forward env options exactly like the animation path — the emitter half ... was wired and tested, but this call site never fed it"); `test_env_options_wired.py:46-48,104-106` (`test_diagram_uses_env_label`, `test_diagram_label_reaches_figure`, both passing today).
**Detail:** The team lead's prompt hedged on whether `label=` is valid for diagrams — it is, unambiguously. `\begin{diagram}[id="...", label="..."]` is documented (environments.md §12.3 per the code comment) and reaches the `<figure aria-label="...">` attribute correctly.

### Finding 2: the diagram's `label=` never reaches the SVG's own `<title>` — confirmed even when label is supplied
**Evidence:** live render of `repro_diagram_withLabel.tex` (see Reproduction Plan) → `<figure class="scriba-diagram" data-scriba-scene="internal-slug-x" aria-label="Two-element array">...<svg ... role="img" ...><title>internal-slug-x</title>...`.
**Detail:** This is the crux of the bug and is stronger evidence than the original report assumed. It is not "no label → falls back to id"; it is "label is present and correctly reaches the figure, but the SVG's own accessible name/tooltip source (`<title>`) is on a completely separate, unconnected code path and still resolves to the id." `emit_diagram_html` (`_html_stitcher.py:863`) builds `_aria` from `label` for the **figure**, but the `_emit_frame_svg` call two lines above (854-861) has no `label` parameter at all.

### Finding 3: the diagram case is guaranteed to hit the id fallback, not merely likely to
**Evidence:** `DiagramRenderer.render_block` rejects `\step` (E1050, `renderer.py:1090-1094`) and `\narrate` (E1054, `renderer.py:1078-1082`) before parsing even completes. `_frame_renderer.py:1851-1875`: `_explicit_title = getattr(frame, "title", None)` is always `None` for diagrams (never set); `_raw_narration` is always `""` (narrate forbidden); so `_title_text` is unconditionally empty going into `if not _title_text: _title_text = scene_id` (line 1874-1875).
**Detail:** For every diagram, with or without `label=`, 100% of renders produce `<title>{scene_id}</title>`. This isn't an edge case to patch defensively — it's the only possible outcome of the current code shape.

### Finding 4: animations are *mostly* fine, but not structurally guaranteed to be — the "FINE" claim has a real counter-example
**Evidence:** live render of `repro_animation.tex` → `<title>Initial state of the array.</title>` and `<title>Swap</title>` (narration / `\step[title=...]` respectively) — matches the reporter's claim. But live render of `repro_animation_silent.tex` (a `\step` with **no** `\narrate` and **no** `title=`, which is syntactically legal — no error code enforces either) → `<title>internal-anim-slug-silent</title>`.
**Detail:** `\narrate` is optional per `\step` (only E1055 "duplicate narrate" and E1056 "narrate must be inside step" exist — nothing enforces presence). Because `_emit_frame_svg` is the same function for animation and diagram frames, a silent step (no narration, no title) leaks `scene_id` exactly like a diagram does. The reporter's "animations are FINE" is true in the common/idiomatic case (steps almost always narrate) but false as a structural guarantee. This matters for the fix: patching only the diagram call site leaves this animation edge case open.

### Finding 5: the fix belongs partly in shared code, not only in the diagram-specific call site
**Evidence:** Findings 3 and 4 both terminate in the same line — `_frame_renderer.py:1875` (`_title_text = scene_id`) — reached via two different callers (`emit_diagram_html` always; `emit_animation_html`/`emit_interactive_html` only on a silent step).
**Detail:** A minimal, ticket-scoped fix could patch only the diagram call site (thread `label` through, stop there). A structurally complete fix — consistent with the reporter's rule 3 ("never fall back to id") stated as an absolute, and with R-15's "MUST describe... in natural language" also stated as an absolute — removes the `scene_id` fallback from the shared function itself.

### Finding 6: `role="img"` + `<title>` means this is not purely cosmetic — it is the SVG's *computed accessible name*, not only its hover tooltip
**Evidence:** `_frame_renderer.py:1890-1896`: `role="img"` plus (for diagrams) no `aria-labelledby` (explicitly suppressed, `_html_stitcher.py:858-860`, tested by `test_env_options_wired.py:69-71` `test_diagram_svg_has_no_dangling_labelledby`) plus a `<title>` first child. Per SVG 2 §5.1 (cited directly in R-15's own rationale, `smart-label-ruleset.md:1036-1039`), an element with no `aria-label`/`aria-labelledby` computes its accessible name from its `<title>` child.
**Detail:** The outer `<figure>`'s `aria-label` (from `label=`) does **not** propagate down to give the inner `role="img"` element a name — accessible-name computation is per-element, not inherited from an ancestor's `aria-label`. So a screen reader landing on the SVG graphic itself (not the figure) announces the id slug, and — separately — the native mouse-hover tooltip (which follows the SVG `<title>` element specifically, never `aria-label`) also shows the id slug. Two independent consumers (AT accessible-name tree, and native browser tooltip) are both fed by the same broken value. This is arguably stronger than "LOW/cosmetic" from a strict WCAG SC 1.1.1 / SC 4.1.2 reading, though this report does not attempt to override the reporter's own severity tag.

## Policy-Conformance Table (Structural Ask 5)

Policy key: **L**=uses `label=` for name when present · **O**=omits name when no label · **N**=never falls back to id. ✅ compliant · ⚠️ partial/conditional · ❌ violates.

| # | Widget / surface | Emission site | What feeds the name today | Does id ever surface? | L | O | N |
|---|---|---|---|---|---|---|---|
| 1 | Static diagram — `<figure>` wrapper | `_html_stitcher.py:863-866` | `aria-label` = env `label=` if present, else attribute omitted | No | ✅ | ✅ | ✅ |
| 2 | Static diagram — inner `<svg><title>` | `_frame_renderer.py:1847-1896`, called from `_html_stitcher.py:854-861` | Fallback chain title→narration→`scene_id`; diagrams forbid the first two (E1050/E1054), so always `scene_id` | **Yes, always** | ❌ | ❌ | ❌ |
| 3 | Animation interactive widget container | `_html_stitcher.py:694,730` | `aria-label` = env `label=` else literal `"Animation"` | No | ✅ | ✅ | ✅ |
| 4 | Animation static/filmstrip `<figure>` | `_html_stitcher.py:221,251-258,325` | env `label=` → first frame's `\step[label=]` → literal `"Animation"` | No | ✅ | ✅ | ✅ |
| 5 | Animation per-frame `<svg><title>` (interactive, filmstrip, and print-frame variants — all reuse the same SVG per `_html_stitcher.py:507-511,573-577`) | `_frame_renderer.py:1847-1896` | `\step[title=]` → stripped `\narrate` text → `scene_id` | **Yes, on a step with neither title nor narration** (repro'd, Finding 4) | ⚠️ | ⚠️ | ❌ |
| 6 | Substory `<section role="group">` | `_html_stitcher.py:404-408`; title field `ast.py:546` | `aria-label="Sub-computation: {substory.title}"`; `title` defaults to the literal string `"Sub-computation"`, never an id (`substory_id` is a separate field) | No | N/A (no `label=` param on substories) | ✅ | ✅ |
| 7 | Graph edge weight tooltip | `graph.py:2506,2516,2522` | `<title>`/`aria-label` = `edge_label`, the user's own edge weight/label data | No (not the widget's env id) | N/A | N/A | ✅ |
| 8 | Annotation arrow tooltip | `_svg_helpers.py:2888` (+ siblings per R-13/R-14: lines ~671, 994/1004, 1052, 1758) | `<title>` = "Arrow from X to Y[: label_text]" built from the user's own selector names + `\annotate` text | No | N/A | N/A | ✅ |
| 9 | Cursor / trace annotation `aria-label` | `base.py:790-791,912-913` | User's own `\cursor{cid}`/label text | No (user-chosen cursor id, different namespace from env `id=`) | N/A | N/A | ✅ |
| 10 | Plain TeX math rendering (`TexRenderer`) | n/a — zero `<title>`/`aria-*`/`role=` emission found in `scriba/tex/renderer.py` | Not applicable; this path renders KaTeX HTML, not an image-like figure | No | N/A | N/A | N/A |
| 11 | `\includegraphics` embed | `scriba/tex/parser/images.py:108` | `alt="{filename}"` — the raw included filename, escaped | No `id=`/`label=` param exists on this command at all (different leak class: filename-as-alt, not an internal slug) | N/A | N/A | ⚠️ (see Side Findings) |
| 12 | `\begin{figure-embed}` (spec'd, `docs/spec/ruleset.md:766`, priority E1) | Not implemented | — | Cannot leak; does not exist in code yet | — | — | — |
| 13 | MetricPlot / Plane2D primitives | none — zero primitive-specific `<title>`/`aria`/`role` code (grep-confirmed) | Inherits row 2/5's frame-level `<svg><title>` entirely; no independent surface | Same as row 2/5 | — | — | — |

**Summary:** 13 rows surveyed. 2 rows (#2, #5) violate the "never id" rule; #2 does so unconditionally, #5 only on an untitled/unnarrated step. 1 row (#11) is a related-but-distinct minor smell (filename, not an id) that the reporter's ticket doesn't cover. Every other emission site (#1, #3, #4, #6-9) is already fully compliant with the reporter's 3-point policy. Rows #10, #12, #13 are not applicable / not yet built.

## Deduced Conclusions

### Deduction 1: the root cause is a missing wire, not a missing feature
**Based on:** Findings 1, 2, 3.
**Reasoning:** Every piece the fix needs already exists — `AnimationOptions.label`, `FrameData.title`, and the title-fallback chain in `_emit_frame_svg` are all real, working, tested machinery. `DiagramRenderer.render_block` (renderer.py:1113-1129) simply never threads `label` into the frame it builds before that frame reaches the shared SVG emitter — it only threads `label` into the outer figure's `emit_html(..., label=...)` call.
**Conclusion:** This is a one-hop wiring fix at the diagram call site, matching the same shape as the earlier "label/width/height silently dropped" bug already fixed and tested in `test_env_options_wired.py` (per its own docstring) — this is the same class of bug recurring one layer deeper (figure-level was fixed; SVG-level was missed).

### Deduction 2: a ticket-scoped fix and a structurally complete fix diverge at one line
**Based on:** Findings 3, 4, 5.
**Reasoning:** Patching only `DiagramRenderer`/`emit_diagram_html` satisfies bug #10's literal repro and the reporter's policy for diagrams, but leaves the identical `scene_id` fallback live in `_frame_renderer.py:1875` for the animation silent-step case this investigation found independently.
**Conclusion:** Recommend fixing the shared fallback (remove the `scene_id` branch, replace with "omit `<title>`") rather than only special-casing diagrams — see Recommended Fix. This also brings the code into conformance with R-15's own absolute "MUST describe... in natural language" wording, which the current `scene_id` fallback violates regardless of which caller reaches it.

## Source Code Trace

| Element | Detail |
| ------- | ------ |
| Error origin | `scriba/animation/_frame_renderer.py:1874-1875` — `if not _title_text: _title_text = scene_id` |
| Trigger (diagram) | `scriba/animation/renderer.py:1115` — `_snapshot_to_frame_data(snap, 1, scene_id, ctx)` called with no `label=`/`title=`; `scriba/animation/_html_stitcher.py:854-861` — `_emit_frame_svg(...)` call has no `label` parameter |
| Trigger (animation edge case) | Any `\step` with no `\narrate` and no `\step[title=...]` — no validator (E1055/E1056 only guard duplication/nesting, not presence) |
| Where label *is* wired (figure only) | `scriba/animation/renderer.py:1122-1129`; `scriba/animation/_html_stitcher.py:863` |
| Governing spec | `docs/spec/smart-label-ruleset.md:1024-1043` (R-15, normative MUST) |
| Related, already-fixed sibling bug | `tests/unit/test_env_options_wired.py:81-117` (`TestDiagramRendererForwardsOptions`) — same "wired in emitter, not fed by call site" shape, previously fixed for figure-level `aria-label`/size, not extended to SVG-level `<title>` |
| Test coverage gap | No test in `test_env_options_wired.py`, `tests/animation/test_diagram_renderer.py`, or `tests/unit/test_phase_b_diagram.py` asserts on `<title>` content for a diagram |

## Reproduction Plan

All four repros rendered via `uv run python render.py <input> -o <output>` from the repo root (0.34.0 / 13eadc7).

**1. No-label diagram** (`\begin{diagram}[id="internal-slug-x"]` + `\shape{a}{Array}{values=[1,2]}`):
```html
<figure class="scriba-diagram" data-scriba-scene="internal-slug-x"><div class="scriba-stage">
<svg class="scriba-stage-svg" ... role="img" xmlns="http://www.w3.org/2000/svg">
<title>internal-slug-x</title>
```
Matches the reported break exactly.

**2. With-label diagram** (same, + `label="Two-element array"`):
```html
<figure class="scriba-diagram" data-scriba-scene="internal-slug-x" aria-label="Two-element array"><div class="scriba-stage">
<svg class="scriba-stage-svg" ... role="img" xmlns="http://www.w3.org/2000/svg">
<title>internal-slug-x</title>
```
Confirms Finding 2: label reaches the figure, **not** the SVG title — the bug persists even with the reporter's own proposed remedy already supplied by the author.

**3. Animation with narration/title** (`\step` → `\narrate{Initial state of the array.}`; `\step[title="Swap"]`):
```html
<title>Initial state of the array.</title>
<title>Swap</title>
```
Confirms the reporter's "animations are FINE" claim for the common case.

**4. Animation silent step** (`\step` with only `\highlight`, no narrate, no title):
```html
<title>internal-anim-slug-silent</title>
```
Refutes "animations are FINE" as an absolute — see Finding 4.

## A11y Notes

- The diagram figure's `aria-label` (from `label=`) and the inner SVG's accessible name (from `<title>`) are **two separate computed names on two separate elements**. Fixing one does not fix the other; a screen reader can land on either the figure or the graphic depending on how it traverses the DOM.
- The native mouse-hover tooltip specifically follows the SVG `<title>` **element** (SVG 2 §5.1), not the HTML `aria-label` **attribute** — this is why the reporter's repro shows a tooltip at all despite `aria-label` being a non-tooltip-producing attribute in every mainstream browser. Any fix must target the `<title>` element itself, not just add/adjust `aria-label`.
- Diagrams already correctly suppress `aria-labelledby` (no dangling reference to a nonexistent narration paragraph — `_html_stitcher.py:858-860`, tested). This part of the a11y wiring is sound and should not be touched by the fix.
- Omitting `<title>` (reporter's policy point 2) is safe: an `<svg role="img">` with no name at all is a well-understood, lesser-severity a11y state ("unlabelled image") versus a *wrong* name (a meaningless slug read aloud as a word). No AT regression from choosing "no name" over "wrong name."
- Implementing "omit `<title>` when no label" will put the code in tension with R-15's current literal text ("Each `<svg>` root **MUST** have a `<title>` element as its first child") — the spec doc itself will need a one-line amendment alongside the code fix (e.g., "...MUST have a `<title>` element when natural-language content is available; otherwise the element MUST be omitted rather than populated with a non-prose identifier").

## Recommended Fix Sketch

1. **Diagram call site** (`scriba/animation/renderer.py:1113-1115`): pass the env `label` into the frame, e.g. `_snapshot_to_frame_data(snap, 1, scene_id, ctx, title=(getattr(_opts, "label", None) or None))`, so the existing `\step[title=]`-shaped machinery naturally prefers it — no new parameter needed, just feed the one that already exists.
2. **Shared fallback** (`scriba/animation/_frame_renderer.py:1874-1875` and the `<title>` emission at 1896): delete the `_title_text = scene_id` fallback; when `_title_text` is still empty after the title→narration chain, omit the `<title>` element entirely (and its trailing comma/line) rather than emitting one with the id. This closes both the diagram case (now guaranteed to have `label` available via step 1) and the untitled/unnarrated-animation-step edge case (Finding 4) in the same change.

## Affected Tests

- `tests/unit/test_env_options_wired.py` — extend `test_diagram_uses_env_label` / `test_diagram_label_reaches_figure` with a sibling assertion on `<title>{label}</title>` (or its absence) inside the `<svg>`, not just the figure's `aria-label`.
- `tests/animation/test_diagram_renderer.py`, `tests/unit/test_phase_b_diagram.py` — no existing test touches `<title>` content; add coverage for the no-label-omit-title case and the label-uses-title case.
- `tests/unit/test_filmstrip_aria.py` — currently the sole test R-15 cites; should either gain a real `<title>`-content assertion or R-15's "Test ref" should be corrected to point at whatever test ends up covering this (today it cites a test that covers a different attribute on a different element).
- `tests/unit/test_step_title.py` — already covers `\step[title=]` → title precedence; worth a new case for the "neither narrate nor title" silent-step path once the fallback changes from id to omission.
- Golden corpus: any diagram-only golden fixtures (CHANGELOG 0.33.0 mentions "14 diagram-only docs byte-identical" for the prior sweep) will need re-blessing once the `<title>` content changes.

## Side Findings

- (Confirmed) `\includegraphics{path/to/file.png}` sets `alt="{filename}"` (`scriba/tex/parser/images.py:108`) with no separate `alt=`/`caption=` option in the parser — a different, lower-severity leak class (raw filename, not an internal env `id=`) than bug #10, and not covered by the reporter's ticket. Flagged for awareness only; not scored against the 3-point policy since there is no `id=`/`label=` concept on this command to violate.
- (Confirmed) `\begin{figure-embed}` is spec'd (`docs/spec/ruleset.md:766`, "SVG/PNG pass-through with DOMPurify sanitization. Requires `alt`, `caption`, `credit`.", priority E1) but has zero implementation in `scriba/` today (grep-confirmed across all `.py` files). Whenever it ships, its mandatory `alt`/`caption` fields put it in a good position to be policy-compliant from day one — worth linking this investigation from that future PR.
- (Confirmed) `SubstoryBlock.title` defaults to the literal string `"Sub-computation"` (`ast.py:546`) when the author omits `\substory[title=...]`, producing `aria-label="Sub-computation: Sub-computation"` in that case — mildly redundant copy, but never an id leak. Not worth fixing under this ticket.
- (Confirmed) R-15's spec entry cites a stale test reference (`test_filmstrip_aria.py::test_frames_with_label_uses_frame_label`) that does not actually assert on `<title>` content — a documentation/traceability drift that likely contributed to this gap surviving review. Worth a docs fix independent of the code fix.

## Conclusion

**Confidence:** High

**Verdict: CONFIRMED**, and more severe in mechanism than the original report assumed. `label=` is already a valid, parsed, tested diagram parameter — the bug is not "no label support," it is that the label is wired to the wrong element (the outer `<figure>`) and never reaches the inner `<svg>`, whose own `<title>` child is what actually drives both the native hover tooltip and (per SVG 2 §5.1, cited in the project's own R-15 spec rule) that element's computed accessible name. The diagram path hits this 100% of the time by construction (narrate/title are structurally forbidden in diagrams), and this investigation additionally found the same fallback leaks on a legal-but-uncommon animation state (a step with neither narration nor title) — so the fix is best made in the one shared fallback function plus a one-line wiring fix at the diagram call site, rather than as a diagram-only patch.
