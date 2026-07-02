# Sweep: dual-runtime drift (scriba.js vs _script_builder.py)

The interactive animation runtime exists **twice**:

- **Asset** — `scriba/animation/static/scriba.js` (external `<script src>`, CSP mode).
- **Inline** — a Python format-string inside `_build_inline_script` in
  `scriba/animation/_script_builder.py` (lines 49–370; `{{ }}` are `str.format`
  escapes → real JS `{ }`; `{sid}`/`{js_frames_str}` are the only substituted fields).

Method: extracted every `function NAME(){…}` body from both copies with brace
matching, normalized the builder (`{{`→`{`, `}}`→`}`) and whitespace, and diffed
per function (`scratchpad/normdiff.py`). Result is authoritative: only four
functions differ, two exist in one copy only, everything else is byte-identical
after normalization. Browser verification used the shipped inline runtime
(`render.py` default) via Playwright + `chrome-headless-shell`.

**Bottom line:** the two copies have drifted **bidirectionally** — each carries a
feature the other lacks — and the copy that ships by default (inline) is missing
an a11y fix that only ever landed in the asset. A shared, unpinned race
(`_runPhase2` after supersede) is present in both and is browser-reproducible
with persistent, user-visible corruption.

---

## Shipping matrix (which copy ships when, path:line)

| Mode | Selector | Ships | Theme toggle handler |
|------|----------|-------|----------------------|
| `inline_runtime=True` **(DEFAULT)** | `render.py:116` default `=True`; CLI `render.py:349`; `renderer.py:501` `ctx.metadata.get("inline_runtime", True)`; `_html_stitcher.py:687–688` → `_build_inline_script(...)` | **`_script_builder.py`** (inline) | separate page bootstrap `_INLINE_THEME_SCRIPT` (`render.py:53–60`, injected `render.py:286`) |
| `inline_runtime=False` (opt-in) | `_html_stitcher.py:690` → `_build_external_script(...)`; asset bytes/hash from `runtime_asset.py:18–26`; `<script src="scriba.<hash>.js">` emitted `_script_builder.py:399–405` | **`static/scriba.js`** (asset) | self-contained delegated listener in scriba.js (`scriba.js:8–14`) |

**Consequence:** rendered pages ship the **inline** copy. `static/scriba.js`
ships **only** when a caller explicitly passes `inline_runtime=False`. Verified:
re-rendered `number_spiral.tex` → HTML contains `_fadeInNewAnnotations` (inline
marker) and eager `narr.innerHTML` before `new DOMParser()`, and **no** JSON
island / no `A03` comment. This is precisely why the first rapid-click fix
(commit `14fbcd5`, first applied to scriba.js only) had zero effect on rendered
pages.

---

## Divergence table

Line refs: **A** = `static/scriba.js`, **B** = `_script_builder.py`.

| # | Function(s) | Asset behavior | Builder (inline, SHIPPED) behavior | User-visible? | Severity | Verdict |
|---|-------------|----------------|-----------------------------------|---------------|----------|---------|
| 1 | `animateTransition` + `_finish` — **narration / aria-live timing** | Narration **deferred**: `_finish` sets `narr.innerHTML` **after** the WAAPI transition settles. A#03 comment + `narr.innerHTML` at **A:268–271**; `animateTransition` does *not* touch narr (A:243–262). | Narration **eager**: `animateTransition` sets `narr.innerHTML=frames[toIdx].narration` up front, before `DOMParser` (**B:311**); `_finish` never sets narr (B:323–331). | **Yes (a11y).** `.scriba-narration` is `aria-live="polite"` (`_html_stitcher.py:702`). Shipped pages announce the next step ~one transition-duration **early**, at click time, not after the visual settles. | **Medium** (a11y timing; final text correct) | **Asset is correct** (A#03 intent). The fix is in the non-shipping copy. Shipped default has the pre-A#03 behavior. **Confirmed (browser).** |
| 2 | `snapToFrame` + `_annKeysIn` + `_fadeInNewAnnotations` — **annotation fade on snap** | **Absent.** `snapToFrame` (A:69–77) just replaces innerHTML — new annotations pop in instantly on snaps. | **Present.** `snapToFrame` snapshots prev annotation keys (**B:128**) and WAAPI-fades annotations new to the target frame (`_fadeInNewAnnotations` **B:115–125**, `_annKeysIn` **B:108–114**). | **Yes (visual).** On Prev / reduced-motion / non-`+1` jumps, inline fades new annotations in; asset shows them instantly. | **Low** (polish only) | **Inline is correct** (newer P2 feature, commit `dc17ae4`). External-runtime pages lose the fade. **Confirmed (code+git).** |
| 3 | `_scribaInit` + `_initAll` (asset-only) | Multi-widget bootstrap: JSON-island discovery `script[type=application/json][id^=scriba-frames-]` (A:325–338), `W.dataset.scribaReady` double-init guard (A:330), one **shared** `MutationObserver` via `_allWidgetRefresh` (A:16–18, 310, 317–322), DOMContentLoaded gate (A:341–345). | None of this exists — inline is one `<script>` per widget; a per-widget `MutationObserver` is attached instead (**B:364–367**). | No (both init correctly in their own mode) | **Low** (architecture) | Equivalent for each mode; differs in structure only. Cleared functionally. |
| 4 | Theme-toggle click handler | **Self-contained** delegated document listener (**A:8–14**). | **None** in the widget script; relies on page-level `_INLINE_THEME_SCRIPT` (`render.py:286`). | No for default `render.py` output; **Yes** if the inline widget is embedded in a host page without the bootstrap (dead toggle button). | **Low** | Cleared for default output; note inline runtime is **not self-contained** for theming. |
| 5 | Theme `MutationObserver` | One global observer for all widgets, `_moAttached`-guarded (A:16, 317–322). | One observer **per widget** (B:364–367). | No (both re-snap current frame on `data-theme`) | **Low** (perf: O(N) observers) | Behaviorally equivalent. Cleared. |

Divergences #1 and #2 are the "live trap": each edits a different copy, so the
default-shipping inline runtime is simultaneously *ahead* (has the fade) and
*behind* (lacks A#03). Git confirms bidirectional, long-standing drift:

- A#03 narration-defer → **asset only**, commit `16b2dee` (2026-04-18).
- `_fadeInNewAnnotations` → **inline only**, commit `dc17ae4` (2026-04-24).
- rapid-nav fix → **both**, commit `14fbcd5` (2026-07-02, after a first asset-only miss).

---

## Race audit (shared state machine, both copies)

### R1 — Orphaned `_runPhase2` applies phase2 onto a snapped stage — CONFIRMED (browser), user-visible, persistent

`_runPhase2` is **normalized-identical** in both copies (A:276–287 / B:332–348).
When a frame's transition has **both** a phase1 kind (`annotation_add` /
`highlight_on`) and a phase2 kind, `animateTransition` schedules
`setTimeout(_runPhase2,_dur(DUR_STAGGER))` (**A:289 / B:345**, ~50 ms at speed 1).

If a click supersedes during that stagger window, the reentrant
`animateTransition` guard (`A:244 / B:303`) runs `_cancelAnims()` + `snapToFrame()`
(→ `_animState='idle'`), **but never clears the pending `setTimeout`** (no
`clearTimeout` anywhere). The orphaned `_runPhase2` then fires and calls
`_applyTransition(...)` for every phase2 record against the **now-snapped** stage.

The `_finish` guard (`A:264 / B:324`, `if(_animState!=='animating')return;` — the
exact contract pinned by `tests/unit/test_runtime_rapid_nav.py`) sits **downstream**
of those `_applyTransition` calls, so it prevents the final innerHTML overwrite
but **not** the phase2 mutations (recolor class swaps, `value_change` text writes,
`element_add` clones, `position_move` starts) that already landed on the wrong
frame.

**Browser proof** (`scratchpad/drive_race2.py`, `drive_race3.py`, shipped inline
runtime, `data-scriba-speed=0.2` to widen the window deterministically;
`spiral-layer-walk`, frame 2 is dual-phase):

- MutationObserver on the stage: supersede-snap to frame 3 at `t=114 ms`; at
  `t=256 ms` (= `_dur(DUR_STAGGER)`) two `childList` mutations landed on the
  snapped stage's `<text>` under `data-target=watch.var[d]` and `watch.var[val]`
  — the orphaned frame-2 `value_change`, executing on frame 3.
- Persistence/visibility: clean walk to frame 3 shows readouts `d` / `val`; the
  raced walk to the **same** frame (counter `4/5`) persistently shows `$3$` and
  `$4 + 3 = 7$` (frame-2's values). Nothing corrects it — `_finish` bailed.

Severity: **HIGH** (persistent wrong data displayed) with a **narrow trigger** (a
supersede within the ~50 ms stagger at default speed — exactly the rapid-nav
regime the recent fix targeted, e.g. clicks at 30–50 ms gaps). **Grade: Confirmed.**
The pinned contract does **not** cover it; guarding only `_finish` gives false
confidence. A correct fix would bail at the **top of `_runPhase2`** (or capture a
generation token and `clearTimeout` on cancel). Present identically in both copies.

### R2 — `_cancelAnims` uses `.finish()` not `.cancel()` — correct in both, one shared gap

`_cancelAnims` (A:45–48 / B:84–87, identical) calls `anim.finish()` (jump-to-end).
This is immaterial here: every caller (`snapToFrame`, reentrant `animateTransition`)
replaces `stage.innerHTML` immediately after, discarding the finished state.
**Shared gap:** `_cancelAnims` only stops WAAPI anims tracked in `_anims`. The
`annotation_add` path-draw runs a `requestAnimationFrame` loop + Promise that is
**not** pushed to `_anims` (A:204–231 / B:263–290), so a cancel does **not** stop
it — it keeps ticking on the detached old node (harmless; the node is gone). Same
in both. **Cleared (shared, benign).**

### R3 — Keyboard vs click paths — consistent

`next`/click and `ArrowRight`/`Space` both call `show(cur+1,true)` (animate);
`prev`/click and `ArrowLeft` both call `show(cur-1,false)` (snap). Identical
across handlers and across both copies (A:301–307 / B:357–363). **Cleared.**

### R4 — Substory `initSub` re-init on every `_finish`/`snap` — no leak

`subC.innerHTML` is reassigned (fresh DOM) immediately before
`…forEach(initSub)` in both `snapToFrame` and `_finish`, so `initSub`'s
`addEventListener`s attach to brand-new nodes; the old subtree + its listeners are
dropped and GC'd → **no listener stacking / no leak**. Identical in both. Side
effect (shared): any open substory resets to step 0 whenever the main frame
changes. **Cleared.**

### R5 — Early `cur=toIdx` commit + `_finish` guard (the pinned contract) — present in both

`cur=toIdx` committed before parse (A:251 / B:310); `_finish` no longer owns the
commit and bails when superseded (A:264 / B:324). This is what
`test_runtime_rapid_nav.py` pins and it holds in both copies. **Cleared** (but see
R1 — the guard's placement leaves the phase2 window unprotected).

---

## Cleared (matches exactly / safe)

- `_applyTransition` — identical (the lone normdiff hit was source-level `\\s`→`\s` Python escaping; rendered JS is `/\s*scriba-highlighted/g` in both). A:88–242 / B:147–301.
- `_cancelAnims`, `_dur`, `_updateControls`, `initSub`, `sh`, `show`, `tick`, `_arrowheadAt` — all normalized-identical. (`_arrowheadAt` is **dead code in both** — defined, never called; not drift, just note.)
- Constants identical in both: `DUR=180`, `DUR_PATH_DRAW=120`, `DUR_VALUE=100`, `DUR_ARROWHEAD=36`, `DUR_STAGGER=50`, `DUR_SYNC_FUDGE=20` (A:34–42 / B:73–81).
- `_speed` / `_dur` speed scaling — identical (A:43–44 / B:82–83).
- Reduced-motion handling — identical `_motionMQ` + `_canAnim` + `change` listener with `addEventListener`/`addListener` fallback (A:31–33 / B:70–72). Browser-checked: `canAnimate=true`, `reduceMotion=false`.
- `_cssEscape` polyfill — identical (A:5 / B:55).
- `needsSync` / `fs` full-sync path + `DUR_SYNC_FUDGE` timeout — identical (A:262, 282–283 / B:322, 338–339).
- Phase-split classification (`annotation_add`/`highlight_on` → phase1) — identical (A:256–260 / B:315–320).

---

## Verdict — unify the copies

**Yes, unify.** The duplication is an active liability, not a theoretical one:

- **Bidirectional drift already shipped.** The default runtime (inline) lacks the
  A#03 aria-live fix (asset-only since Apr 18); the asset lacks the annotation
  fade (inline-only since Apr 24). Neither copy is a superset; both are "wrong"
  relative to the union of intended behavior.
- **Every fix costs double and is easy to half-apply.** The rapid-nav fix was
  applied to the wrong copy first and changed nothing on real pages. The test
  suite pins exactly **one** contract against both copies; the other four
  divergences and the R1 race are unpinned, so nothing stops the next drift.
- **A real race hides in the shared logic.** R1 corrupts the displayed frame
  persistently and is reachable in the rapid-nav regime that is under active
  concern — and it is *not* what the current contract guards.

Recommended direction: make **one** source of truth for the runtime JS (author in
`scriba.js`; have the inline builder emit only the frames payload + a `<script>`
that references the same JS body, e.g. inline the asset text verbatim rather than
maintaining a hand-parallel format-string). Whatever the mechanism, the two
behavior sets (A#03 defer + annotation fade) must be reconciled into that single
copy, and R1 fixed at the top of `_runPhase2`. Cost of *not* unifying: continued
per-fix duplication, silent a11y/visual divergence between modes, and an unpinned
race that the existing "both copies" test gives false confidence about.

---

### Evidence appendix (scratchpad, reproducible)

- `scratchpad/normdiff.py` — authoritative per-function normalized diff (only `animateTransition`, `_finish`, `snapToFrame` differ; `_annKeysIn`/`_fadeInNewAnnotations` inline-only; `_scribaInit`/`_initAll` asset-only).
- `scratchpad/find_dualphase.py` — frames 2,3,4 of `spiral-layer-walk` are dual-phase (`annotation_add` + `recolor`/`value_change`).
- `scratchpad/drive_race.py` — TEST1 narration timing: immediate read after Next already equals the target frame's narration → **EAGER (A#03 absent in shipped)**.
- `scratchpad/drive_race2.py` — orphan mutation timeline: supersede-snap `t=114ms`, orphan `value_change` on snapped stage `t=256ms` (= `_dur(DUR_STAGGER)`).
- `scratchpad/drive_race3.py` + full-`<text>` compare — persistent visible corruption: raced frame `4/5` shows `$3$` / `$4 + 3 = 7$` vs clean `d` / `val`.

---

## Structural Fix Design (2026-07-02)

### Design summary

One canonical runtime: **`scriba/animation/static/scriba.js`**. The external path
serves it verbatim (SRI-hashed, as today). The inline path stops hand-maintaining a
parallel format-string and instead **derives** its `<script>` from the same file at
import time via a deterministic slice + `.replace` (no `str.format`, so the `{{ }}`
tax disappears). The runtime is refactored so its entire state machine lives in one
self-contained `_scribaInit(W, frames)` unit (the only thing that ever drifts); the
two *bootstraps* (island-discovery for the asset; `getElementById + inline frames`
for inline) stay legitimately per-mode. Into that single unit we merge both stranded
features (A#03 narration-defer from the asset + annotation fade-on-snap from the
inline) and fix R1 with a generation token. Net effect: every default page gets the
a11y fix back, every external page gets the fade, and the race dies in one place
instead of two.

### Chosen architecture + rationale

**Chosen: option (a) — `scriba.js` is canonical; the builder loads it at import and
transforms deterministically.** Refined shape ("A3"):

- Refactor `scriba.js` so the whole animation state machine is one self-contained
  `function _scribaInit(W, frames){ … }` — folding in `_cssEscape` (today module-scope
  `scriba.js:5`) and a **per-widget** theme `MutationObserver` (today only inline has
  one, `_script_builder.py:364-367`; the asset uses a shared registry
  `_moAttached`/`_allWidgetRefresh`, `scriba.js:16-18,309-322`). Delete the shared-MO
  machinery; `_initAll` shrinks to island-discovery + DOMContentLoaded gate. The
  shared unit is bracketed by two sentinel comments (below).
- The module-scope **theme-toggle delegated click listener** (`scriba.js:8-14`) stays
  asset-only (a page needs exactly one; N per-widget copies would double-flip). Inline
  pages keep getting theirs from `render.py:_INLINE_THEME_SCRIPT` (`render.py:53-60`,
  injected `render.py:286`). This is divergence #4/#5 — already graded behaviorally
  equivalent — and is *outside* the shared unit by design.
- `_build_inline_script` reads the bytes already cached by `runtime_asset.py`
  (`RUNTIME_JS_BYTES.decode("utf-8")` — no second disk read), slices the sentinel
  region, and wraps it (spec below).

Why (a): the asset stays a first-class `.js` file — lintable (eslint/prettier),
debuggable in browser devtools, and directly SRI-hashable for the CSP path — while the
inline copy becomes a pure derivation with zero authored JS. The import-time file read
already exists (`runtime_asset.py:18`), so no new I/O pattern. Determinism for goldens
is trivial: `read → str.split(sentinel) → str.replace` is pure.

**Rejected:**
- **(b) shared template file consumed by both.** Adds a *third* artifact. The asset
  must still be a real servable/hashable `.js`, so `scriba.js` would have to be
  *generated* from the template + a "template ↔ committed asset in sync" CI check.
  More moving parts than (a), which already has a single source (the asset itself).
- **(c) builder canonical, `scriba.js` generated.** JS-as-Python-string is exactly how
  this drift happened: unlintable, no JS tooling, unreadable in review, and the SRI
  hash becomes a build artifact that must be regenerated + committed. Strictly worse.
- **A1 (inline the whole asset verbatim + a JSON island in inline mode too).** Cleanest
  code-wise but flips inline mode to carry a `type="application/json"` island, breaking
  the inline contract pinned by `test_csp_inline_runtime.py` (`test_no_json_island`,
  `test_no_external_src`) and churning goldens for no benefit. A3 keeps inline's
  self-contained single-`<script>` shape.

Note: the **frame payload format stays per-mode** and need not unify. The core reads
only `frames[i].{svg,narration,substory,tr,fs}` (`.label` is carried but never read at
runtime — verified). Inline keeps its backtick-literal array
(`_html_stitcher.py:668-672`); external keeps its JSON island (`:679-682`). Both supply
those keys, so the shared core is payload-shape-agnostic.

### Token / transform spec for the inline wrapper

Author two sentinels into `scriba.js`, wrapping the self-contained unit (from the first
line after the `W,frames` bind through `show(0,false);` inclusive):

```js
function _scribaInit(W,frames){
  // __SCRIBA_CORE_START__
  var _cssEscape=…; var cur=0; …            // full state machine + handlers + per-widget MO
  show(0,false);
  // __SCRIBA_CORE_END__
}
```

`_build_inline_script(scene_id, js_frames_str)` becomes (`.replace` only, **no**
`f"{{…}}"`):

```python
_CORE = (RUNTIME_JS_BYTES.decode("utf-8")
         .split("// __SCRIBA_CORE_START__")[1]
         .split("// __SCRIBA_CORE_END__")[0])           # module-level, computed once

_WRAPPER = (
    "<script>\n(function(){\n"
    "var W=document.getElementById('__SCRIBA_SID__');\n"
    "var frames=[\n__SCRIBA_FRAMES__\n];\n"
    + _CORE +
    "})();\n</script>"
)

def _build_inline_script(scene_id, js_frames_str):
    return (_WRAPPER
            .replace("__SCRIBA_SID__", _escape_js(scene_id))   # SID first
            .replace("__SCRIBA_FRAMES__", js_frames_str))      # frames last
```

Rules that keep it deterministic/safe:
- Exactly **two** tokens, replaced **SID-then-FRAMES** (so frame content can never
  perturb the SID substitution). Tokens are `__SCRIBA_*__` — absent from both the JS
  body (we own it) and any plausible frame content; and even if present in frame
  content they are inserted as a *value*, never re-scanned.
- `_CORE` closes over `W`/`frames` exactly as `_scribaInit`'s params did, so the sliced
  body runs unchanged. `_escape_js` still guards the id.
- Slicing on fixed sentinels + `.replace` is pure ⇒ byte-identical goldens across runs.

### Feature-merge table (function-by-function; canonical target = `scriba.js`)

| Function | Winner (source) | Action in unified `scriba.js` |
|---|---|---|
| `snapToFrame` | **inline** (`_script_builder.py:126-136`) | Replace asset's pop-in version (`scriba.js:69-77`) with the inline one: snapshot `prevKeys=_annKeysIn(frames[cur]&&…svg)` before `cur=i`, then `_fadeInNewAnnotations(prevKeys)` after `_updateControls`. |
| `_annKeysIn` | **inline-only** (`:108-114`) | **Add** to `_scribaInit` (absent from asset). |
| `_fadeInNewAnnotations` | **inline-only** (`:115-125`) | **Add** to `_scribaInit` (absent from asset). |
| `animateTransition` (body before `_finish`) | **asset** (`scriba.js:243-262`) | Keep asset's: **no** `narr.innerHTML` here. Drop inline's eager line (`_script_builder.py:311`). |
| `_finish` | **asset** (`scriba.js:263-275`) | Keep asset's A#03 deferred `narr.innerHTML=frames[toIdx].narration` (`:271`). Inline's `_finish` (`:323-331`) lacks it. **Also** extend first-line guard (race spec). |
| `_runPhase2` | identical | **Add** gen guard at top (race spec). |
| theme `MutationObserver` | converge → **inline's per-widget** | Fold a per-widget observer into `_scribaInit`; delete asset's `_moAttached`/`_allWidgetRefresh`/shared MO (`scriba.js:16-18,309-322`) and the registry push (`:310`). Perf-only (O(N) observers), already graded equivalent. |
| `_cssEscape` | identical | Move into `_scribaInit` (was module-scope `scriba.js:5`) so the slice is self-contained. |
| theme click listener | **asset-only** (`:8-14`) | Leave at module scope (asset); inline still uses `render.py:_INLINE_THEME_SCRIPT`. Out of the shared slice. |
| `_applyTransition`, `_cancelAnims`, `_dur`, `_updateControls`, `initSub`, `sh`, `show`, `tick`, constants, reduced-motion, `_arrowheadAt` (dead) | identical | Keep as-is; `_cancelAnims` gains one line (`_gen++`). |

After the merge the *inline* path — being a slice of this file — automatically regains
A#03 (fixing the shipped a11y regression) and keeps the fade; the *external* path gains
the fade.

### Race-fix spec (R1 + full orphan-callback audit)

**State added: one integer.** `var _gen=0;` in `_scribaInit` scope.

**Single increment site (the supersede choke point):**
```js
function _cancelAnims(){ _gen++; for(var k=0;k<_anims.length;k++)try{_anims[k].finish();}catch(e){} _anims=[]; _animState='idle'; }
```
Both supersede paths funnel through here: the reentrant
`animateTransition` guard (`scriba.js:244`) and every `snapToFrame` (`:70`).

**Single capture:** in `animateTransition`, immediately after `_animState='animating';`
(`scriba.js:247`), add `var myGen=_gen;`. `_finish` and `_runPhase2` are closures that
see both `myGen` and the live `_gen`.

**Two guards (exact placement):**
1. **Top of `_runPhase2`** (before the phase-2 loop — this is the R1 fix, stopping the
   damaging `_applyTransition` recolor/value_change/element_add writes onto the snapped
   stage):
   ```js
   function _runPhase2(){ if(myGen!==_gen)return; for(var j=0;j<phase2.length;j++){…} … }
   ```
   One guard suffices because `_runPhase2`→phase-2 loop is synchronous (no await between
   check and mutations), so a per-`_applyTransition` re-check is redundant.
2. **Top of `_finish`** — keep the pinned `_animState` contract *and* add gen coverage:
   ```js
   function _finish(fullSync){ if(_animState!=='animating'||myGen!==_gen)return; … }
   ```
   The added `myGen!==_gen` is load-bearing: under an **animate**-supersede (rapid Next),
   the new transition sets `_animState='animating'`, so the *stale* `_finish`'s
   `_animState` check alone would NOT bail and its needsSync `setTimeout(_finish,…)`
   (`scriba.js:283`) would overwrite the stage with the old SVG. The gen check closes it.

**Orphan-callback audit — every `setTimeout`/`requestAnimationFrame`/`Promise`:**

| Site | Location | Verdict under this design |
|---|---|---|
| `setTimeout(_runPhase2, DUR_STAGGER)` | `scriba.js:289` / `_script_builder.py:345` | **Fixed** — `_runPhase2` top gen guard. |
| `setTimeout(_finish, DUR+FUDGE)` (needsSync) | `:283` / `:339` | Covered — `_finish` gen guard. |
| `Promise.all(pending).then/.catch(_finish)` | `:281` / `:337` | Covered — `_finish` gen guard. |
| `annotation_add` `drawDone` Promise + inner `requestAnimationFrame(tick)` | `:204-231` / `:263-290` | **Benign (R2)** — runs on a detached/GC-eligible node, not in `_anims`. Minimal design leaves it. *Optional* polish: `if(myGen!==_gen)return;` in `tick` to stop the dead-node rAF early. |
| reduced-motion `change`, theme `MutationObserver`, keydown/click | throughout | Persistent listeners, not orphaned callbacks. No change. |

**Why gen-token over timer-handle + `clearTimeout`:** one integer + two guards covers
*all four* async completion paths uniformly and self-aborts callbacks that have already
fired but are still queued (which `clearTimeout` cannot). A handle approach needs to
track *both* timers, clear both in `_cancelAnims`, and still misses the queued-callback
window. Gen-token is the minimal-state choice.

### TDD plan

Repo reality (surveyed): tests are **100% pure-Python source-inspection** — even the
rapid-nav contract is regex-pinned, explicitly noting "the runtime has no JS test rig"
(`test_runtime_rapid_nav.py:10`). Browser proof was ad-hoc scratchpad Playwright drivers
against the local `chrome-headless-shell`. **Recommendation: keep browser checks OUT of
the pytest suite** — the executable is a non-portable local cache path, Playwright isn't
a test dependency, and it would inject flakiness against an otherwise deterministic
suite. Preserve the `scratchpad/drive_race*.py` drivers as a documented manual smoke
(they already reproduce R1). If a gate is ever wanted, add an opt-in
`@pytest.mark.browser` test skipped unless `SCRIBA_BROWSER_TESTS=1` *and* the binary
exists — but do not put it in the default run.

Pins (all now assert against **one** source + the **derived** inline output, so they
survive unification):

1. **Re-point `test_runtime_rapid_nav.py`.** Today `_SOURCES` reads two files
   (`static/scriba.js` + `_script_builder.py`, `:30-37`). After unification the JS is no
   longer *in* `_script_builder.py`, so change source #2 from "read the `.py` file" to
   "call `_build_inline_script("x", "[]")` and parse its emitted `<script>`". Keeps both
   parametrized ids (`external_asset`, `inline_emitted`) proving the derived inline still
   carries the early-commit + `_finish` guard contract.
2. **New race pins** (against `scriba.js` **and** emitted inline):
   - `_runPhase2` first statement is `if(myGen!==_gen)return;`.
   - `_cancelAnims` contains `_gen++`.
   - `animateTransition` defines `var myGen=_gen;` *before* `function _runPhase2`.
   - `_finish` first statement still matches `_animState` + `return` (existing
     `TestOrphanFinishGuard` stays green) and now also contains `myGen!==_gen`.
3. **Feature-merge pins** (these start **RED**, then GREEN after the merge — they encode
   the two stranded features):
   - `_annKeysIn` and `_fadeInNewAnnotations` present in `scriba.js` (asset currently
     lacks → RED today).
   - `snapToFrame` calls `_fadeInNewAnnotations`.
   - **Narration-defer against the *emitted inline* output** — extend
     `test_a11y_aria_live.py` (today only reads `static/scriba.js`, `:146-152`) to also
     assert `narr.innerHTML` does **not** appear before `function _finish` in the inline
     `<script>`. *This is the exact pin whose absence let the live regression ship.*
4. **Single-source / anti-drift pins** (the invariant that stops the next drift):
   - `Path(_script_builder.py).read_text()` contains **no** `function animateTransition`
     / `function _runPhase2` (the JS is not re-authored in Python).
   - `_build_inline_script(...)` output **does** contain `animateTransition` +
     `_runPhase2` (proves derivation from the asset).
   - Strongest: extract `animateTransition` from `scriba.js` and from the emitted inline
     and assert **byte-equality** after stripping the `sid`/frames prologue — a literal
     "cannot drift" lock.
5. **No re-point needed** for `test_runtime_asset.py` (SRI/hash) — it recomputes expected
   values from `RUNTIME_JS_BYTES` (`:26-48`), so it stays green when `scriba.js` bytes
   change. `test_csp_inline_runtime.py` / `test_csp_external_runtime.py` are structural
   (inline = one `<script>`, no island; external = island + SRI src) and remain true
   under A3.

### Blast radius & landing order

**Golden churn (confirmed):** the inline `<script>` body changes (narration moved to
`_finish`, `_annKeysIn`/`_fadeInNewAnnotations` added, `snapToFrame` fade, `_gen` +
guards, per-widget-MO fold, `_cssEscape` fold), so **every inline-runtime golden
churns**. Measured: **95** goldens under `tests/golden/**` + `tests/doc_coverage/**`
contain `function animateTransition`; all regenerate. Mechanism is a byte-compare with a
built-in re-baseline: `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/`
(`test_example_html.py:45,112`). Also regenerate the docs artifact
`docs/cookbook/10-substory-shared-private/output.html` (embeds the runtime;
`_runPhase2`/`DUR_STAGGER` at `:1875,1888`). Reviewable because the delta is the *same*
JS diff repeated across files.

**SRI / hashed-asset consumers:** `RUNTIME_JS_SHA384` + `RUNTIME_JS_FILENAME` change
(bytes change). Consumers: only `_build_external_script` output (`_script_builder.py:399-405`)
and `test_runtime_asset.py` (self-recomputes → green). **No golden embeds an SRI hash or
`scriba.<hash>.js`** (grep of `tests/golden` + `tests/doc_coverage` = 0 hits) — external
mode isn't goldened — so SRI churn touches **zero** committed fixtures. No hard-coded
hash anywhere in tests/docs to bump.

**Docs:** `docs/guides/embedding-in-website.md:32` mentions `inline_runtime=True`
(prose, no change). `CHANGELOG.md:298` documents `_script_builder._fadeInNewAnnotations`
— after unification the symbol lives in `scriba.js`; add a changelog entry noting the
move + the unification + the R1 fix + A#03-now-shipping. **Flag (not this task's fix):**
`CHANGELOG.md:721` claims "inline-runtime is no longer the default", but the code defaults
to inline everywhere (`_html_stitcher.py:459,729`; `renderer.py:501`; `render.py:116`) —
pre-existing doc/code drift worth a separate note.

**`_INLINE_THEME_SCRIPT`** (`render.py:53-60`) is a *third*, page-level copy of the
theme-toggle listener. It is not the widget runtime and is untouched here; note it as a
follow-up dedup candidate, not part of this change.

**Landing order (CI green at each step):**
1. Edit `scriba.js`: add sentinels, fold `_cssEscape` + per-widget MO, merge fade
   (`_annKeysIn`/`_fadeInNewAnnotations`/`snapToFrame`), keep A#03 `_finish`, add
   `_gen` + two guards; shrink `_initAll`. (Existing asset-side a11y + rapid-nav pins
   stay green; new race/fade pins go green.)
2. Refactor `_build_inline_script` to slice + `.replace` from `RUNTIME_JS_BYTES`.
3. Re-point + add tests (§TDD 1–4). Run: RED→GREEN as features land.
4. Re-baseline goldens in one dedicated commit (`SCRIBA_UPDATE_GOLDEN=1 …`) + regenerate
   the cookbook doc HTML; diff review = expected JS delta only.
5. Changelog entry; optional follow-ups (`_INLINE_THEME_SCRIPT` dedup, CHANGELOG:721
   default-mode correction, optional `tick` gen check).
