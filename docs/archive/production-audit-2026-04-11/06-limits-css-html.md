# Agent 06: Limits & CSS/HTML Contract

**Score:** 8/10
**Verdict:** ship-with-caveats

## Prior fixes verified

- **M1 (scriba-filmstrip):** MISSING — Animation-plugin.md line 212 still references `scriba-filmstrip` (should be `scriba-frames`). However, emitter.py line 436 correctly emits `<ol class="scriba-frames">`, so the code is correct but docs are stale.

- **M2 (data-frame/data-step, scriba-stage/scriba-stage-svg):** PARTIALLY FIXED — Usage-example.md still shows old markup, but emitter.py line 468 correctly emits `data-step="{step}"` and line 324 emits `<svg class="scriba-stage-svg">`. Code is correct; docs need update.

- **L4 (matrix 10k error code):** PARTIAL — Ruleset.md §13 shows "Matrix cells | 10,000 | E1425" but code at primitives/matrix.py line 156 checks `250_000` cells (not 10,000) with no error code. DPTable also checks `250_000`. Mismatch between spec limit (10,000) and actual code limit (250,000).

## Critical Findings

**C1. HTML attribute allowlist gap (CRITICAL)**

`figure` element in whitelist.py line 57-60 only allows `class`, `id`, `data-step*` attributes. But emitter.py emits:
- `data-scriba-scene="{id}"` (line 432, 487)
- `data-frame-count="{N}"` (line 433, 488)
- `data-layout="filmstrip"` (line 434, 489)
- `aria-label="{label}"` (line 490)

When sanitized by default (bleach or consumer), these attributes silently strip, leaving empty figure elements. **Result: data loss on frame count, scene tracking, and accessibility labels.** The `svg` element's `class="scriba-stage-svg"` (line 324) is allowed, but `aria-labelledby` (line 326) is not in SVG allowlist.

**Impact:** Output is structurally valid but semantically broken for interactive widgets and scene reconstruction.

## High Findings

**H1. Substory widget data attributes not whitelisted**

Line 555: `data-scriba-frames="{frames_json}"` emitted on `<div class="scriba-substory-widget">`. Whitelist has no entry for `div` attribute `data-scriba-frames`. Silently stripped on sanitization.

**H2. Matrix/DPTable cell limit spec-code mismatch (CRITICAL)**

| Constraint | Spec (ruleset.md §13) | Code | Error Code |
|-----------|------------------|------|-----------|
| Matrix cells | 10,000 | 250,000 | E1425 (spec) / E1103 (code) |
| DPTable cells | 10,000 | 250,000 | E1425 (spec) / E1103 (code) |

Spec says 10k, code enforces 250k. E1103 is generic shape-validation error, not E1425. Undocumented in error.py.

**H3. Plane2D element limit is `_ELEMENT_CAP = 500` (E1466 correct)**

Code matches ruleset.md: 500 elements/frame, error code E1466. ✓

**H4. MetricPlot points limit is `_MAX_POINTS = 1000` (E1483 correct)**

Code matches ruleset.md: 1,000 points/series, error code E1483. ✓

**H5. Frame count limits correct**

- `_FRAME_WARN_THRESHOLD = 30` → E1180 (warning) ✓
- `_FRAME_ERROR_THRESHOLD = 100` → E1181 (error) ✓

## Medium Findings

**M1. SVG `g` element missing `data-target` in whitelist**

Primitives emit `<g data-target="{selector}" class="scriba-state-...">` (e.g., array.py, all primitives). Whitelist line 126 allows `data-step` and `data-scriba-action` on `g`, but not `data-target`. **Silently stripped on sanitization**, breaking selector-to-state mapping.

**M2. Foreach/array iterable length limit correct**

`scene.py` line 301: `_MAX_ITERABLE_LEN = 10_000` matches ruleset.md. ✓

**M3. Array size limit enforced (10,000)**

`array.py` line 79: size > 10_000 raises E1103. Matches spec for Array part of ruleset (not explicit in §13 but consistent with 10k pattern). ✓

**M4. Foreach nesting depth correct**

`scene.py` line 302: `_MAX_FOREACH_DEPTH = 3` matches E1170 in ruleset.md §13. ✓

**M5. TeX source size correct**

`tex/renderer.py` line 51: `MAX_SOURCE_SIZE = 1_048_576` (1 MiB) matches ruleset.md §13. ✓

**M6. TeX math items limit correct**

`tex/parser/math.py` line 21: `MAX_MATH_ITEMS = 500` enforced at line 91 with E1162. Spec shows no explicit limit, but code implements 500. ✓

## Low Findings

**L1. CSS classes emitted but not in documentation**

Emitter produces 15+ `scriba-*` classes (scriba-animation, scriba-frames, scriba-frame, scriba-frame-header, scriba-step-label, scriba-stage, scriba-narration, scriba-substory, scriba-substory-widget, scriba-controls, scriba-btn-prev, scriba-btn-next, scriba-step-counter, scriba-progress, scriba-dot). Ruleset.md §10 (CSS Contract) lists state classes but not layout classes.

**L2. Substory progress dots class (`scriba-dot`) not styled**

Line 545: `<div class="scriba-dot{" active" if i == 0 else ""}"></div>` — no CSS definition found in codebase for `.scriba-dot` or `.scriba-dot.active`. Markup emitted but styling likely missing.

**L3. String literal length cap in Starlark**

`starlark_worker.py` line 42: `_MAX_STR_LITERAL_LEN = 10_000` — not documented in ruleset §13. Internal security measure, not advertised.

## Notes

1. **Whitelist is the real bottleneck:** Fix list above (data-scriba-scene, data-frame-count, data-layout, aria-labelledby, data-target on g) must be added or the HTML/SVG is silently corrupted on sanitization.

2. **Matrix cell limit is de facto 250k, not 10k:** Either update spec or code. If 250k is intentional, add E1425 to error.py.

3. **Documentation outdated:** animation-plugin.md and usage-example.md reference removed/renamed CSS classes. Audit 2026-04-11 M1/M2 are still unresolved in docs.

4. **No error code for Starlark memory limit:** E1151 defined but silently surfaces as E1151 per environments.md — should document exact mapping.
