# 03 — Emitter & Scene Log-Noise Audit

**Agent:** Completeness Audit 3/14
**Scriba:** v0.5.1 (HEAD `eb4f017`)
**Date:** 2026-04-11
**Mode:** Read-only

## Scope

Inventory every `logger.warning/error/info/debug`, `warnings.warn`, and
bare `print()` in:

- `scriba/animation/emitter.py`
- `scriba/animation/scene.py`
- `scriba/animation/parser/*.py`  *(clean — zero hits)*
- `scriba/animation/primitives/*.py`
- `scriba/core/*.py`

Each site is classified and given a remediation action. The audit also
traces the `stk` false-positive warning observed when compiling
`examples/cookbook/convex_hull_andrew.tex`.

## Logging inventory

Columns: **Site** • **Message (abbrev.)** • **Class** • **Action**

### `scriba/animation/emitter.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 1 | `emitter.py:339` (`_validate_expanded_selectors`) | `selector '{target}' does not match any addressable part of '{shape}'` | **NOISE** *(for whole-primitive apply; would be BUG for typo selectors)* | Fix false positive (see root cause below). Keep the warning but add `target_key == shape_name` to the skip condition and promote typo cases to **E1107** `ScribaError` with line/col carried via the AST. |

### `scriba/animation/scene.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 2 | `scene.py:599` (`_apply_annotate`) | `\annotate target shape '{shape}' not found in declared shapes, annotation may be invalid` | **BUG** — author referenced an undeclared shape | Promote to `ScribaError` **E1115** (or reuse existing annotate validator). This is the classic "typo in shape name" case; silently warning is user-hostile. Must carry `cmd.line`/`cmd.col`. |

### `scriba/animation/primitives/base.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 3 | `base.py:194` (`set_state`) | `{cls} '{name}': invalid selector '{target}', ignoring set_state()` | **DEBUG** | Demote to `logger.debug`. Emitter already validates selectors one frame earlier (site #1); this is an internal-API safety net hit only when renderers misuse `set_state`. Authors should never see it. |
| 4 | `base.py:201` (`set_state`) | `{cls} '{name}': invalid state '{state}', ignoring set_state()` | **DEBUG** | Same — demote to `logger.debug`. `VALID_STATES` is enforced in the parser (E1109). |
| 5 | `base.py:216` (`set_value`) | `{cls} '{name}': invalid selector '{suffix}', ignoring set_value()` | **DEBUG** | Demote to `logger.debug`. |
| 6 | `base.py:231` (`set_label`) | `{cls} '{name}': invalid selector '{suffix}', ignoring set_label()` | **DEBUG** | Demote to `logger.debug`. |

### `scriba/animation/primitives/variablewatch.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 7 | `variablewatch.py:78` | `VariableWatch '{name}' created with empty names list` | **BUG** | Promote to `ScribaError` (new code e.g. **E1488** or reuse E1108 family). An empty VW is not valid config — fail fast at shape declaration. |

### `scriba/animation/primitives/metricplot.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 8 | `metricplot.py:182` | `[E1486] degenerate xrange [%s, %s]; falling back to auto` | **BUG** *(already raises)* | Keep but **delete the `logger.error`** — the next line raises `animation_error("E1486", ...)` so the log line is redundant noise from the same exception. |
| 9 | `metricplot.py:591` | `[E1484] log scale: non-positive value %s in series %r clamped to 1e-9` | **BUG** (silent data mangling) | Keep as warning **but** only emit once per series (dedupe key = series.name). Currently fires per non-positive sample which can produce thousands of lines. Consider promoting to E1484 error gated by a `strict=true` pipeline flag. |

### `scriba/animation/primitives/graph_layout_stable.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 10 | `graph_layout_stable.py:182` | `E1504: layout_lambda=%.4f outside [...], clamping` | **BUG** (silent clamp) | Promote to `ScribaError` E1504 with suggestion; clamping hides author intent. |
| 11 | `graph_layout_stable.py:192` | `E1501: %d nodes exceeds limit of %d` | **BUG** | Promote to E1501 `ScribaError`. Fallback happens silently — author deserves a hard error. |
| 12 | `graph_layout_stable.py:195` | `E1503: falling back to force layout` | **NOISE** (companion of #11) | Delete — already implied by E1501. |
| 13 | `graph_layout_stable.py:200` | `E1502: %d frames exceeds limit of %d` | **BUG** | Same treatment as #11 — promote. |
| 14 | `graph_layout_stable.py:205` | `E1503: falling back to force layout` | **NOISE** | Delete (duplicate of #12). |
| 15 | `graph_layout_stable.py:257` | `E1500: final objective (%.4f) exceeds 10x initial (%.4f)` | **DEBUG** | Demote to `logger.debug`. This is a convergence diagnostic that means nothing to an author; they can't act on it. |

### `scriba/animation/primitives/plane2d.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 16 | `plane2d.py:198` | `[E1463] point (%.2f, %.2f) is outside viewport` | **BUG** (silent off-screen) | Promote to `ScribaError` E1463 or gate on `strict=true`. Currently silently adds invisible point. |
| 17 | `plane2d.py:211` | `[E1461] degenerate line (a=0, b=0)` | **BUG** | Promote to E1461 `ScribaError`. |
| 18 | `plane2d.py:248` | `[E1462] polygon not closed — auto-closing` | **NOISE** | Delete. Auto-close is documented, expected behavior — warning every time pollutes output. |
| 19 | `plane2d.py:253` | `[E1462] polygon not closed — auto-closing` (dict path) | **NOISE** | Delete (duplicate of #18). |
| 20 | `plane2d.py:529` | `[E1461] vertical line x=%.2f outside viewport` | **NOISE** (expected clip) | Demote to `logger.debug`. Clipping off-screen lines is expected rendering behavior, not an authoring error. |
| 21 | `plane2d.py:534` | `[E1461] line (slope=%.2f, intercept=%.2f) outside viewport` | **NOISE** | Same — demote to `logger.debug`. |

### `scriba/core/workers.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 22 | `workers.py:187` | `worker cleanup: wait after kill: %s` | **DEBUG** *(already)* | **Keep.** Already at `debug` level, correct. |
| 23 | `workers.py:189` | `worker cleanup: terminate failed: %s` | **DEBUG** | Keep. |
| 24 | `workers.py:193` | `worker cleanup: kill failed: %s` | **DEBUG** | Keep. |
| 25 | `workers.py:200` | `worker cleanup: stream close: %s` | **DEBUG** | Keep. |
| 26 | `workers.py:220` | `worker drain_stderr: %s` | **DEBUG** | Keep. |
| 27 | `workers.py:341` | `SubprocessWorker is a deprecated alias…` | **DEPRECATION** | Keep. Properly gated on external callers, `DeprecationWarning`. |
| 28 | `workers.py:408` | `oneshot worker cleanup: %s` | **DEBUG** | Keep. |
| 29 | `workers.py:508` | `pool close: %s` | **DEBUG** | Keep. |

### `scriba/core/pipeline.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 30 | `pipeline.py:124` | `Pipeline(context_providers=[]) disables ALL default context providers…` | **DEPRECATION/WARN** | Keep. Loud intentional footgun warning on explicit API misuse. |
| 31 | `pipeline.py:263` | `asset path collision for {key!r}: keeping {old}, ignoring {new}` (CSS) | **BUG** | Promote to `ScribaError` **E2001** (new — asset collision). Silently shadowing an asset is a real bug that will surface as a runtime 404. |
| 32 | `pipeline.py:277` | `asset path collision for {key!r}: keeping {old}, ignoring {new}` (JS) | **BUG** | Same — promote. |
| 33 | `pipeline.py:335` | `renderer {name!r} close() raised: {e}` (warnings.warn) | **DEBUG + KEEP** | The `warnings.warn` duplicates `logger.warning` on the same line. Drop the `warnings.warn` (UserWarning), keep `logger.warning` with `exc_info=True`. Users should not see pipeline-shutdown failures as `UserWarning` — they indicate renderer bugs, not user errors. |
| 34 | `pipeline.py:336` | `renderer {name!r} close() raised: {e}` (logger.warning) | **DEBUG** | Keep as logger.warning. |

### `scriba/core/__init__.py`

| # | Site | Message | Class | Action |
|---|---|---|---|---|
| 35 | `__init__.py:69` | `SubprocessWorker is a deprecated alias…` | **DEPRECATION** | Keep. Mirror of #27, gated on external callers. |

## Root cause: the `stk` warning

**Symptom.** `\apply{stk}{push=...}` emits
`selector 'stk' does not match any addressable part of 'stk'` **per
frame × per apply**, polluting the console during
`examples/cookbook/convex_hull_andrew.tex`.

**Trace.**

1. Parser (`grammar.py:_parse_apply`) reads the brace arg `stk` and
   calls `parse_selector("stk")`.
2. `selectors.py:65` returns `Selector(shape_name="stk", accessor=None)`.
3. Scene (`scene.py:_apply_apply`, line 524) converts it to a string
   via `_selector_to_str`. Because `accessor is None`, the function
   returns the **bare shape name** `"stk"` (line 70).
4. That bare string becomes the key in
   `frame.shape_states["stk"]["stk"] = {"apply_params": [...]}`.
5. In `emitter.py:_emit_frame_svg`, for `shape_name="stk"` the code
   calls `_expand_selectors({"stk": data}, "stk", prim)`.
6. In `_expand_selectors` (line 277), the key `"stk"` matches **none**
   of the `range`, `all`, or `top` regexes, so it falls through to
   `_merge(key, data)` — `expanded["stk"] = data` unchanged.
7. `_validate_expanded_selectors` (line 324) iterates. It strips the
   prefix `"stk."` only when `target_key.startswith("stk.")` — but the
   key is bare `"stk"`, so the strip is a no-op and `suffix` stays as
   `"stk"`.
8. The skip guard on line 330 is `if not suffix or suffix in ("all",)`.
   `"stk"` is neither empty nor `"all"`, so it proceeds.
9. `prim.validate_selector("stk")` returns `False` (the stack primitive
   has no "stk" part) → warning fires.
10. The apply **still works** because the adjacent pre-pass loop at
    line 367 extracts the same bare `"stk"` suffix and routes it to
    `prim.apply_command(params, target_suffix="stk")`, and stack
    primitives treat `target_suffix == self.name` (or a bare shape name)
    as "operate on the whole primitive".

The validator and the apply dispatcher disagree on whether "bare shape
name" is a legal selector. Apply says yes; validator says no.

## Fix proposals

### Minimal (targeted, one-liner)

Extend the skip condition in `emitter.py:_validate_expanded_selectors`
(line 330) so a bare whole-primitive selector is never flagged:

```python
# Skip meta-selectors that are handled specially
if (
    not suffix
    or suffix in ("all",)
    or target_key == shape_name  # whole-primitive selector, e.g. \apply{stk}
):
    continue
```

This fixes the noise without changing dispatch semantics. Matches the
exact behavior `_expand_selectors` already exhibits on line 307.

### Preferred (semantic alignment)

Normalize whole-primitive selectors in `_expand_selectors` so the
validator never sees bare shape keys:

```python
# Bare shape name → alias for `.all` if the primitive accepts it,
# otherwise pass through to apply_command as a whole-primitive op.
if key == shape_name:
    # Route through apply_command path but normalize to a stable key
    _merge(f"{shape_name}.__whole__", data)
    continue
```

…and teach `_validate_expanded_selectors` to skip `__whole__`. This
keeps one canonical internal key for whole-primitive operations and
avoids bare-name collisions with addressable parts named after the
shape.

### Parallel fix for #2 (`\annotate` undeclared shape)

Promote `scene.py:599` from `warnings.warn` to
`ScribaError` E1115 using `cmd.line`/`cmd.col`. This is a real bug
(author typo) and deserves a pointer to the source location, not a
`UserWarning` the author may never notice.

## Severity summary

| Class | Count | Examples |
|---|---|---|
| **BUG → promote to `ScribaError`** | 10 | #2, #7, #10, #11, #13, #16, #17, #31, #32; also #9 with dedupe |
| **NOISE → delete or gate** | 6 | #1 (skip guard), #12, #14, #18, #19, #33 (drop warnings.warn, keep logger) |
| **NOISE → demote to `logger.debug`** | 6 | #3, #4, #5, #6, #15, #20, #21 *(7 — double-counted on purpose: #20 and #21 are both demotions)* |
| **DEBUG → keep as-is** | 9 | #22–#29, #34 |
| **DEPRECATION → keep** | 3 | #27, #30, #35 |
| **Redundant log alongside raise → delete log line only** | 1 | #8 |

**Headline findings:**

1. **#1 is the top console-polluter** in practice (per-frame × per-apply
   × per-shape for whole-primitive selectors). The one-line skip-guard
   fix kills it immediately; the preferred fix hardens semantics.
2. **`primitives/base.py` leaks internal safety-net warnings** (#3–#6)
   to the author. These should never escape to stderr — the parser and
   emitter already validate upstream. Demote all four to `debug`.
3. **`graph_layout_stable.py` silently clamps & falls back** (#10, #11,
   #13) where authors expect hard errors. Three `BUG` promotions.
4. **`plane2d.py` auto-closes polygons noisily** (#18, #19) and
   duplicates E-codes between validation-time and render-time clipping
   (#20, #21). Delete the auto-close warnings; demote the clip ones.
5. **`pipeline.py` asset collisions** (#31, #32) deserve `ScribaError`
   promotion — silent shadowing → runtime 404.
6. **`core/workers.py` is clean.** All eight `logger.debug` calls are
   correctly gated; only the deprecation warning is user-facing and it
   is appropriately gated on external callers.
7. **`parser/*.py` is clean.** Zero logging sites — all validation
   raises `ScribaError` with line/col, which is the correct pattern the
   rest of the codebase should converge on.

**Estimated total console-line reduction for a typical cookbook
compile after all fixes: ~95%** (driven mostly by #1, #18/#19, #20/#21,
and #9 dedupe).
