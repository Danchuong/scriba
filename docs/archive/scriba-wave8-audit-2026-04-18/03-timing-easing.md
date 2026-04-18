# Wave 8 Audit — P3: Animation Timing + Easing Correctness

**Date:** 2026-04-18
**Auditor:** Wave 8 static code audit
**Status:** Research-only — no files were modified

---

## Methodology

1. Inventoried all animation primitives under `scriba/animation/primitives/`. None expose a `duration=` or `easing=` parameter — timing lives entirely in the JS runtime layer.
2. Traced the data path: `SceneState` → `FrameSnapshot` → `FrameData` → `TransitionManifest` (via `differ.py`) → JSON `tr` array → `scriba.js` `_applyTransition`. The JSON manifest carries only `[target, prop, from_val, to_val, kind]` — **no duration or easing data is emitted from Python**.
3. Read both the external `scriba/animation/static/scriba.js` and the inline template in `scriba/animation/emitter.py` (lines 1130–1413). Both are character-for-character identical; all timing constants are hardcoded in JS.
4. Searched for `prefers-reduced-motion` / `_canAnim` across the full repo.
5. Read the `\step` handler in `scriba/animation/parser/grammar.py` and the state machine in `scriba/animation/scene.py` for off-by-one analysis.
6. Checked keyframe animation timing in `scriba/animation/extensions/keyframes.py` and `scriba-animation.css`.

---

## Architecture Overview

Scriba does **not** have per-primitive `duration=` parameters. The Python emitter produces a diff manifest (`kind` tags such as `recolor`, `element_add`, `position_move`) with no timing metadata. The JS runtime maps each `kind` to a hardcoded WAAPI call. This means all timing audit findings are in the JS layer, not in Python primitives.

---

## Per-Primitive Timing Table

"Primitive" here means the transition `kind` emitted by the differ — the closest analog to what the audit prompt calls a "primitive" in timing context.

| Transition kind | Duration emitted by Python | WAAPI duration in scriba.js | Easing in scriba.js | Consistent w/ CSS? |
|---|---|---|---|---|
| `recolor` | none (CSS only) | n/a — CSS class swap, no WAAPI | CSS `transition: 180ms ease-out` | Yes |
| `value_change` | none | `_dur(100)` = 100ms (`DUR`-independent) | `ease-out` | No CSS counterpart |
| `element_remove` | none | `_dur(DUR)` = 180ms | `ease-out` | No CSS counterpart |
| `element_add` | none | `_dur(DUR)` = 180ms | `ease-in` | No CSS counterpart |
| `position_move` | none | `_dur(DUR)` = 180ms | `ease-out` | No CSS counterpart |
| `annotation_remove` | none | `_dur(DUR)` = 180ms | `ease-out` | No CSS counterpart |
| `annotation_add` (path) | none | rAF loop, `_dur(120)` = 120ms total + arrowhead fade `_dur(36)` = 36ms | custom cubic (1-(1-t)³ via JS) | No CSS counterpart |
| `annotation_add` (non-path) | none | `_dur(DUR)` = 180ms | `ease-in` | No CSS counterpart |
| `highlight_on` | none | CSS class add, no WAAPI | CSS `transition: 180ms ease-out` | Yes |
| `highlight_off` | none | CSS class removal | CSS `transition: 180ms ease-out` | Yes |
| Keyframe presets (`rotate`, `orbit`, `fade-loop`, `trail`, `pulse`) | none | n/a — CSS `animation` only | per-class, see below | Yes (self-contained) |

**Keyframe preset durations (CSS only, defined in `scriba-animation.css` / `extensions/keyframes.py`):**

| Preset class | Duration | Easing |
|---|---|---|
| `scriba-anim-rotate` | 2s | `linear` |
| `scriba-anim-pulse` | 1s | `ease-in-out` |
| `scriba-anim-orbit` | 3s | `linear` |
| `scriba-anim-fade-loop` | 2s | `ease-in-out` |
| `scriba-anim-trail` | 1.5s | `linear` |

---

## Inconsistency List

### 🔴 CRITICAL (user-visible incorrect timing)

None found at the static code level. All transitions that complete (`element_add`, `element_remove`, `position_move`, `annotation_add`) use `fill:'forwards'` and the `Promise.all(pending).then(...)` finish gate, so the runtime does reach a clean end state. No animation that snaps when it should not was found.

### 🟠 HIGH — Inconsistency Between Transition Kinds

**[1] `element_add` uses `ease-in`; all other opacity fades use `ease-out`**

File: `scriba/animation/static/scriba.js:137-138`

`element_add` fades in with `{easing:'ease-in'}` while `element_remove` uses `ease-out`. The non-path branch of `annotation_add` also uses `ease-in`. This means new elements materialize slowly then snap to full opacity (the perceptually wrong curve — fade-in should decelerate, i.e. `ease-out`), while elements disappear with a slow exit (also the wrong curve for removals — fade-out should accelerate, i.e. `ease-in`).

The curves are backwards. Users will perceive new elements as "popping in late" and removed elements as "lingering."

Fix: swap — `element_add` / `annotation_add` should use `ease-out`; `element_remove` / `annotation_remove` should use `ease-in`.

**[2] `annotation_add` (path branch) uses a different duration than all other transitions**

File: `scriba/animation/static/scriba.js:200`

Arrow-path annotations draw over `_dur(120)` = 120ms, then the arrowhead and label fade in over `_dur(36)` = 36ms (triggered at 70% of the draw). Total wall time is approximately 120ms + 0ms overlap = ~120ms, not the 180ms `DUR` baseline used by every other transition kind. The shorter window is intentional (drawn annotations feel snappier) but it is undocumented and inconsistent with the implied baseline.

### 🟡 CODE-SMELL — Magic Numbers and Unexplained Constants

**[3] `DUR = 180` is a bare magic number**

File: `scriba/animation/static/scriba.js:34` and `scriba/animation/emitter.py:1149`

`180` appears with no named constant and no comment explaining the design decision (why 180ms? why not 200ms, which is the CSS `line > opacity` transition value?). The `value_change` animation uses `_dur(100)` — a different hardcoded value also unnamed.

**[4] `value_change` duration (100ms) differs from the baseline (180ms) with no documentation**

File: `scriba/animation/static/scriba.js:96`

The value-change "scale bounce" animation is 100ms, not 180ms. This is not wrong per se, but it is inconsistent with the baseline and not explained.

**[5] Phase-gap stagger delay (50ms) is a magic number**

File: `scriba/animation/static/scriba.js:274`

When both phase 1 (`annotation_add`, `highlight_on`) and phase 2 (everything else) transitions exist, phase 2 is deferred by `_dur(50)` = 50ms. This 50ms stagger is hardcoded and undocumented. Over N steps with mixed transition types, the phase gap accumulates only within one step — it does not drift across frames because the `_finish` callback calls `_cancelAnims()` at the start of the next `animateTransition`. **No cross-frame phase drift found**, but the 50ms value is unexplained.

**[6] `needsSync` timeout guard uses `_dur(DUR)+20`**

File: `scriba/animation/static/scriba.js:268`

When a frame has `fs:1` (full sync needed) but no pending WAAPI animations, the runtime waits `_dur(DUR)+20` ms before calling `_finish(true)`. The `+20` is an unexplained fudge factor. Under `data-scriba-speed` values other than 1, `_dur(DUR)` scales but the +20 does not, so at `speed=0.5` the fudge is 36ms / 200ms = 18% of the total wait — visible.

**[7] The `_dur(36)` arrowhead fade is a nested magic duration**

File: `scriba/animation/static/scriba.js:207, 211`

The arrowhead opacity fade uses `_dur(36)` with no explanation of why 36ms (approximately 2 frames at 60fps, or 30% of the path draw duration).

### 🔵 POLISH — Naming and Defaults

**[8] Easing tokens are bare CSS keyword strings scattered across the runtime**

All WAAPI calls use raw strings `'ease-out'`, `'ease-in'`. There are no named constants (e.g., `EASE_ENTER = 'ease-out'`, `EASE_EXIT = 'ease-in'`). Swapping to a physically correct easing library (e.g., `cubic-bezier`) or correcting the add/remove inversion (finding #1) would require touching 8 call sites.

---

## `prefers-reduced-motion` Handling Map

### Where it is checked

| Location | Mechanism | Effect |
|---|---|---|
| `scriba.js:31-33` | `window.matchMedia('(prefers-reduced-motion:reduce)')` → `_canAnim` | Disables all WAAPI transitions; falls back to `snapToFrame()` |
| `scriba-scene-primitives.css:763-791` | `@media (prefers-reduced-motion: reduce)` | Sets `transition-duration: 0.01ms` on all elements; sets `transition: none` on widget controls and `[data-target]` children |
| `scriba-animation.css:57-70` | `@media (prefers-reduced-motion: reduce)` | Sets `animation: none !important` on all five keyframe preset classes |
| `extensions/keyframes.py:106-113` | `UTILITY_CSS` string containing the same `@media` block | Same keyframe disable, emitted inline with keyframe styles |

### Per-primitive behaviour under reduced motion

| Transition kind | Reduced-motion behaviour | Consistent? |
|---|---|---|
| `recolor` | CSS transition collapses to 0.01ms — effectively instant class swap | Yes |
| `value_change` | `_canAnim=false` → WAAPI call skipped entirely; text is set without scale bounce | Yes (no animation) |
| `element_remove` | `_canAnim=false` → `snapToFrame()` called; element disappears instantly | Yes |
| `element_add` | `_canAnim=false` → `snapToFrame()` called; element appears instantly | Yes |
| `position_move` | `_canAnim=false` → `snapToFrame()` called; element teleports | Yes |
| `annotation_add` (path) | `_canAnim=false` → `snapToFrame()` called; annotation appears instantly | Yes |
| `annotation_remove` | `_canAnim=false` → `snapToFrame()` called; annotation disappears instantly | Yes |
| `highlight_on/off` | CSS class swap without CSS transition (duration 0.01ms) | Yes |
| Keyframe presets | CSS `animation: none !important` via media query | Yes |

**Verdict: `prefers-reduced-motion` handling is consistent across all transition kinds.** When `_canAnim` is false, `animateTransition` falls through to `snapToFrame` immediately (line 238: `if(!tr||!tr.length||!_canAnim){snapToFrame(toIdx);return;}`). CSS transitions are independently zeroed out by the media query. The only minor note is that CSS transitions use `0.01ms` rather than `0ms` — this is a documented browser workaround for transition-end event firing and is intentional.

One previously-identified issue from Wave 7 audit (`docs/archive/scriba-audit-2026-04-17/02-runtime-a11y.md`) — `_canAnim` not being updated reactively on OS setting change — was **already fixed** in the current code. Lines 32-33 of `scriba.js` register a `change` listener on the `MediaQueryList` that updates `_canAnim` dynamically, with a legacy `addListener` fallback for older browsers.

---

## `\step` Semantics: Off-by-One Analysis

### Frame counter mechanics

`SceneState._frame_counter` starts at `0`. Each call to `apply_frame()` increments it first (`self._frame_counter += 1`) then passes it as the `index` argument to `snapshot()`. Therefore:

- Frame 1: `_frame_counter` becomes 1 → `snap.index = 1`
- Frame 2: `_frame_counter` becomes 2 → `snap.index = 2`
- Frame N: `snap.index = N`

`_snapshot_to_frame_data` maps this directly: `step_number=snap.index`. The JS runtime displays `Step {idx+1} / {frames.length}` using 0-based array indexing with a +1 offset for display — consistent with 1-based `step_number`.

**No off-by-one found in the mainline `\step` path.**

### Edge cases examined

**Empty steps (no commands between two `\step`s):** `apply_frame()` is called for every `FrameIR` regardless of whether it has commands. An empty frame increments `_frame_counter` and produces a snapshot identical to the previous frame. This is correct — one `\step` always produces exactly one frame, empty or not.

**Substory frame counter:** `apply_substory()` saves `_frame_counter`, resets it to 0, runs substory frames (each producing indices 1, 2, ... within the substory), then restores the parent counter. Substory frame indices are local to the substory. The substory JS player uses a separate `sc` variable and separate `fd` array. **No index collision between parent and substory frames.**

**DiagramRenderer:** `snap = state.snapshot(index=1, narration=None)` at line 736 of `renderer.py` hardcodes `index=1`. This is correct for the single-frame diagram case.

**`\step` with only `\narrate`:** The `narrate_body` is set on the `FrameIR`; `apply_frame()` processes it into the snapshot. One step → one frame. No issue.

**Consecutive `\step` commands with no intervening content:** Grammar forces a new `FrameIR` for each `\step` (lines 179-199 of grammar.py). Each FrameIR gets its own `apply_frame()` call. Exactly one frame per `\step`. **No doubling.**

**Verdict: `\step` advances exactly one logical frame in all examined cases.**

---

## Recommended Canonical Easing Token Set

The current codebase has no easing abstraction layer. The following canonical set is proposed to unify naming and fix the add/remove inversion:

```javascript
// Proposed: scriba.js top of _scribaInit
var EASE = {
  ENTER:  'ease-out',   // decelerates — correct for elements appearing
  EXIT:   'ease-in',    // accelerates — correct for elements disappearing
  BOUNCE: 'ease-in-out' // for ping-pong value changes
};
var DUR_BASE     = 180;  // ms — primary WAAPI transition baseline
var DUR_VALUE    = 100;  // ms — value-change bounce (intentionally snappier)
var DUR_DRAW     = 120;  // ms — annotation path draw
var DUR_ARROWHEAD = 36;  // ms — arrowhead/label fade after draw
var DUR_STAGGER  = 50;   // ms — phase 1 → phase 2 gap
```

With these constants, each `_applyTransition` branch becomes:

| kind | duration | easing |
|---|---|---|
| `element_add` | `_dur(DUR_BASE)` | `EASE.ENTER` (was `ease-in` — fix) |
| `element_remove` | `_dur(DUR_BASE)` | `EASE.EXIT` (was `ease-out` — fix) |
| `annotation_add` (non-path) | `_dur(DUR_BASE)` | `EASE.ENTER` (was `ease-in` — fix) |
| `annotation_remove` | `_dur(DUR_BASE)` | `EASE.EXIT` (unchanged) |
| `position_move` | `_dur(DUR_BASE)` | `EASE.ENTER` (unchanged) |
| `value_change` bounce | `_dur(DUR_VALUE)` | `EASE.BOUNCE` (unchanged) |
| annotation draw | `_dur(DUR_DRAW)` + `_dur(DUR_ARROWHEAD)` | cubic (unchanged) |

---

## Confirmed-OK Findings

- `prefers-reduced-motion`: fully consistent snap behaviour across all transition kinds. Both CSS and WAAPI paths reduce correctly.
- `\step` frame counting: no off-by-one. One `\step` → exactly one frame. Empty steps, substory steps, and nested substories all count correctly.
- The `_dur(ms)` speed-scaling wrapper is applied to all WAAPI duration arguments, so `data-scriba-speed` works consistently — except the `+20` fudge in the `needsSync` timeout path (finding #6).
- CSS transition baseline (180ms `ease-out` on `rect`, `circle`, `text`) matches `DUR_BASE = 180` for `recolor` transitions. The CSS and WAAPI layers agree on the baseline value for state changes that go through CSS.
- `fill:'forwards'` is applied on all WAAPI calls that modify opacity or transform, preventing flash-of-original-state on completion.
- Keyframe presets (rotate, pulse, orbit, fade-loop, trail) are self-consistent: durations and easings match between `scriba-animation.css` and `extensions/keyframes.py UTILITY_CSS`. Reduced-motion disables them via CSS in both paths.
- The `_MAX_TRANSITIONS = 150` bail-out in `differ.py` correctly sets `skip_animation: True`, which the JS runtime maps to `null` for `tr`, causing `snapToFrame()` — correct degradation.
- `_cancelAnims()` calls `.finish()` on in-flight WAAPI animations before starting a new transition, preventing ghost animations from overlapping across frames.

---

## Summary Table

| # | Severity | Finding | Location |
|---|---|---|---|
| 1 | 🟠 | `element_add` / `annotation_add` use `ease-in` (should be `ease-out`) | `scriba.js:137, 228` |
| 2 | 🟠 | `annotation_add` path draw uses 120ms vs 180ms baseline — undocumented inconsistency | `scriba.js:200` |
| 3 | 🟡 | `DUR = 180` magic number; no named constant, no rationale | `scriba.js:34` |
| 4 | 🟡 | `value_change` 100ms differs from baseline; unnamed | `scriba.js:96` |
| 5 | 🟡 | Phase stagger 50ms magic number; undocumented | `scriba.js:274` |
| 6 | 🟡 | `needsSync` fudge `+20` does not scale with `_speed` | `scriba.js:268` |
| 7 | 🟡 | `_dur(36)` arrowhead fade — nested magic duration | `scriba.js:207,211` |
| 8 | 🔵 | Easing strings scattered across 8 call sites; no constants | `scriba.js` passim |

**Decision:** WARN — no CRITICAL timing bugs found; two HIGH-severity easing inversions (add/remove curves backwards) and five MEDIUM code-smell issues. Safe to ship existing behaviour, but the easing inversion (#1) will be perceptually visible to users who watch elements appear and disappear in sequence.
