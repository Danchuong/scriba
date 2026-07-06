# Design: delta-emphasis excludes self-announcing motion kinds

**Status:** design (do not implement — lead reviews the exclusion set before it drives a `SCRIBA_VERSION` bump)
**Scope:** `scriba/animation/static/scriba.js` runtime `_finish` pulse set + one motion-ruleset A-rule.
**Evidence grades:** *Confirmed* = cited `path:line` + rendered/manifest proof; *Deduced* = follows from confirmed facts; *Hypothesized* = plausible, unverified.

---

## RETURN-TO-LEAD SUMMARY

- **Classification verdict — 7 self-announcing, 4 silent.**
  Self-announcing (exclude from delta-emphasis): `value_change`, `element_add`, `element_remove`, `position_move`, `annotation_add`, `annotation_remove`, `cursor_move`.
  Silent (keep pulse — the pulse is the real "this changed" signal): `recolor`, `highlight_on`, `highlight_off`, `annotation_recolor`.
- **Double-signal count — 5 kinds fire a redundant pulse today** (target survives to settle and resolves in `_emphasize`): `cursor_move` (#1, flagship), `position_move` (#2), `value_change`, `element_add`, `annotation_add`. The two remove kinds are self-announcing but their target is gone at settle, so they never resolve → no pulse today (excluded for closure only).
- **Exact exclusion set to bake** (a named `_SELF_ANNOUNCING` object-set, mirroring `_INV_KIND`):
  `{value_change:1, element_add:1, element_remove:1, position_move:1, annotation_add:1, annotation_remove:1, cursor_move:1}`.
- **Predicted golden shift — 93 files, NOT 5.** The mandate's PART-4 hypothesis ("only cursor_move/position_move goldens change") is **refuted**. Emphasis is applied at RUNTIME, never baked into static SVG (0 elements carry `class="…scriba-emphasis…"` across the whole corpus). So no golden's SVG/`tr`/narration/stylesheet bytes move. The ONLY changed bytes are the inline `<script>` CORE region, which is byte-identical across every interactive widget → **all 93 interactive corpus goldens re-bless by the same delta**; the 14 static corpus HTMLs + the 5 `tests/golden/animation/html_*.html` + the `differ_*.json` manifests + `smart_label/` do NOT change. The cursor/position census matters only for verifying which *behaviors* change, which golden bytes never captured.
- **Confidence: HIGH** on classification, double-signal map, and golden-shift character; **HIGH** on the two-pass necessity (463 corpus frames prove it).

---

## PART 1 — Classification of all 11 closed motion kinds

Registry is closed (motion-ruleset A-2, `docs/spec/motion-ruleset.md:64-66`; differ schema `scriba/animation/differ.py:59-62`). Each kind's runtime handler is in `_applyTransition` (`scriba/animation/static/scriba.js:152-344`). "Self-announcing" = the handler plays a per-element transform / draw-on / opacity motion during the single-step transition, so the emphasis pulse (CSS `.scriba-emphasis`, scale 1→1.08→1, 700 ms, `css:917-925`) is redundant. "Silent" = an instant class swap (a CSS *paint* fade at most, never a transform/translate/scale/draw) the eye can miss — the pulse is the intended signal.

| # | kind | runtime handler (`scriba.js`) | motion played by the handler | self-announcing? | pulse redundant? | grade |
|---|------|------------------------------|------------------------------|:---:|:---:|---|
| 1 | `recolor` | `:155-162` swaps `scriba-state-{from}`→`{to}` class | none in JS; CSS fades `fill/stroke 180ms` (`css:885-894`) — a **paint** change, no transform | **NO** | no — pulse wanted | Confirmed |
| 2 | `value_change` | `:163-175` writes `<text>`, then `animate scale(1)→1.15→1` over `DUR_VALUE=100ms` | **scale bounce** (A-3 calls this "proto-emphasis", `motion-ruleset.md:94`) | **YES** | **YES** (scale-pulse on scale-bounce) | Confirmed |
| 3 | `highlight_on` | `:176-185` adds `.scriba-highlighted` | none — `.scriba-highlighted` is **paint-dead** (KNOWN-DEAD, `css:1002-1008`) | **NO** | no — pulse wanted | Confirmed |
| 4 | `highlight_off` | `:186-193` removes `.scriba-highlighted` | none (paint-dead class) | **NO** | no — pulse wanted | Confirmed |
| 5 | `element_add` | `:201-219` clones from dest, `animate opacity 0→1` over `DUR` | **fade-in** (appearance) | **YES** | **YES** | Confirmed |
| 6 | `element_remove` | `:194-200` `animate opacity 1→0` over `DUR` | **fade-out** | **YES** | no today (target gone at settle) | Confirmed |
| 7 | `position_move` | `:220-237` `animate translate(0,0)→translate(to−from)` over `DUR` | **glide** to new seat (A-4, `motion-ruleset.md:118-122`) | **YES** | **YES** | Confirmed |
| 8 | `annotation_remove` | `:238-244` `animate opacity 1→0` | **fade-out** | **YES** | no today (target gone at settle) | Confirmed |
| 9 | `annotation_add` | `:245-315` split: `<path>`→**stroke draw-on** (`:279-306`); else **opacity 0→1 fade-in** (`:307-313`) | **draw-on OR fade-in** — **uniform: both sub-paths self-announce**, neither is instant | **YES** | **YES** | Confirmed |
| 10 | `annotation_recolor` | `:316-326` swaps `scriba-annotation-{from}`→`{to}` class | none — no CSS transition on annotation-state classes (absent from `css:882-894`) | **NO** | no — pulse wanted (instant swap) | Confirmed |
| 11 | `cursor_move` | `:327-343` `animate translate(0,0)→translate(delta)` over `DUR`, cubic-bezier | **glide** (A-4 caret slide) | **YES** | **YES** (flagship) | Confirmed |

Subtle ones resolved by evidence:
- **`value_change` — self-announcing.** Its scale-bounce (`scriba.js:173-174`) is literally named *proto-emphasis* by A-3 (`motion-ruleset.md:94, 99`). The delta-pulse is a second scale animation on the same element → the most egregious double (scale-on-scale). Exclude.
- **`annotation_add` — uniform, does not split.** Both branches animate: draw-on for traces/arrows (has `<path>`), fade-in for notes/labels/pills (no `<path>`). No instant sub-path exists (`scriba.js:245-315`). Exclude the kind wholesale.
- **`element_add/remove` — fade, not snap** (`scriba.js:197, 215`). Self-announcing.
- **`recolor` vs a paint fade.** `recolor` carries a CSS `fill/stroke 180ms` transition (`css:885-894`) but that is a *color* change with no positional/scale motion; the pulse is the motion cue that says *which* element changed. Silent → keep the pulse. `highlight_on/off` toggle a paint-dead class (`css:1002`); `annotation_recolor` has no transition at all — both are the canonical "instant swap the eye can miss" the emphasis feature exists for.

---

## PART 2 — The double-signal map (every redundant pulse, not just the caret)

**Mechanism (Confirmed):** on a forward/reverse single step, once the WAAPI motion settles, `_finish` (`scriba.js:404-419`) calls `_emphasize(_manifestTargets(tr))`. `_manifestTargets` (`:353`) returns **every** changed identity `tr[t][0]` with **no kind filter**. `_emphasize` (`:363-382`) resolves each via `[data-target=X] || [data-annotation=X]` (`:374`) and toggles `.scriba-emphasis`. On any pending-animation step `_finish` is called with `fullSync=true` (`needsSync||true`, `:426`) → `stage.innerHTML = frames[toIdx].svg` (`:407`) → every identity present in the destination frame resolves → pulses. Gated only by `_canAnim`, the `data-scriba-no-emphasis` opt-out, and `EMPH_CAP=8` (`:369-371`) — never by kind.

**Confirmed instance (the flagship showcase golden).** `tests/golden/examples/corpus/anim_clarity_showcase.html` frame manifest, extracted verbatim:

```
tr:[["a.cell[2]","state","idle","current","recolor"],
    ["w.var[i]","value","0","2","value_change"],
    ["a.cursor[i]-solo","position","92.0,46.0","216.0,46.0","cursor_move"]], fs:1
```

`_manifestTargets(tr)` = `["a.cell[2]","w.var[i]","a.cursor[i]-solo"]` (3 identities, ≤ `EMPH_CAP` → pulses). Traced through `_emphasize`:
- `a.cell[2]` — `recolor` only → resolves `[data-target]` → pulse **correct** (silent recolor gets its signal).
- `w.var[i]` — `value_change` only → resolves `[data-target]` → **REDUNDANT** (already scale-bounced).
- `a.cursor[i]-solo` — `cursor_move` → resolves `[data-annotation="a.cursor[i]-solo"]` (present 6× in the golden, Confirmed) → **REDUNDANT** (already glided). This is bug #1: a 700 ms scale pulse lands on the flagship 0.23 `\cursor` glide → the perceived jolt.

**Corpus-wide confirmation (island-parsed census of all 107 corpus HTMLs, 776 frames-with-`tr`).** Files carrying ≥1 manifest record of each kind:

| kind | files | pulses today? |
|------|:---:|---|
| `recolor` | 77 | yes — **keep** |
| `value_change` | 52 | **yes — redundant** |
| `annotation_add` | 47 | **yes — redundant** (where the `data-annotation` key matches `_emphasize`'s direct lookup) |
| `highlight_on` | 18 | yes — keep |
| `highlight_off` | 16 | yes — keep |
| `element_add` | 16 | **yes — redundant** |
| `annotation_remove` | 9 | no (target gone at settle) |
| `annotation_recolor` | 9 | yes — keep |
| `position_move` | 4 | **yes — redundant** (#2; targets are `T.node[N]` in `[data-target]` space, differ `:455`) |
| `cursor_move` | 1 | **yes — redundant** (#1) |
| `element_remove` | 0 | n/a (differ suppresses bogus removals, `differ.py:22-34`; 0.26.2 note) |

**Redundant-pulse count = 5 kinds** actually double-signal today: `cursor_move`, `position_move`, `value_change`, `element_add`, `annotation_add`. `element_remove`/`annotation_remove` are self-announcing but their target is absent from the settled frame so `_emphasize`'s `querySelector` returns null → no pulse (Deduced from `_finish` fullSync swap `:407` + resolution `:374`); they join the exclusion set for closure/symmetry only.

*Minor pre-existing nuance (Deduced):* `_emphasize` (`:374`) uses a **direct** `[data-annotation=X]` match, while the annotation handlers use `_annEl` with the `-solo`→`-position-{side}` fallback (`:135-151`). So some `-solo` pills already fail to resolve in `_emphasize` and don't pulse today. Excluding `annotation_add` is a no-op for those and removes the redundant pulse for the rest (traces, matching keys). Not a blocker.

---

## PART 3 — The structural fix

### 3.1 A named self-announcing set (single source of truth)

Add a closed object-set inside the CORE slice, adjacent to `_INV_KIND` (`scriba.js:345`), so it is inlined verbatim into every widget (the slice runs `__SCRIBA_CORE_START__`…`__SCRIBA_CORE_END__`, `scriba.js:25/467`, sliced by `_script_builder._build_inline_script`, `_script_builder.py:60-61,102-105`). *It must live between the sentinels and reference no module-scope state* (`scriba.js:23`).

```js
// The motion kinds whose handler already plays a per-element transform /
// draw-on / opacity during a single step (A-9): the element self-announces,
// so a delta-emphasis pulse on top is redundant double-signaling. Silent kinds
// (recolor / highlight_on / highlight_off / annotation_recolor) are instant
// class swaps the eye can miss and KEEP the pulse. Closed set — mirrors the
// _INV_KIND single-source-of-truth discipline (A-2).
var _SELF_ANNOUNCING={value_change:1,element_add:1,element_remove:1,position_move:1,annotation_add:1,annotation_remove:1,cursor_move:1};
```

### 3.2 Two-pass identity exclusion (replaces `_manifestTargets` on the pulse path)

The report's per-record `continue` is **wrong** and the corpus proves it: **463 of 776 frames** have a single identity carrying BOTH a self-announcing AND a silent kind in the same step — overwhelmingly `['recolor','value_change']` on one cell (`vars.var[detail]`, `hm.bucket[0]`, `ll.node[1]`, `V.cell[0]`, …). A per-record skip would still emit that identity via its `recolor` record and pulse a cell that just scale-bounced. The exclusion must be keyed on the **identity**, collected across ALL records first:

```js
function _pulseTargets(tr){
  // Pass 1: any identity that appears under ANY self-announcing kind — the eye
  // tracked it through that motion, so exclude the WHOLE identity even if it
  // also recolored this step. Pass 2: emit the changed identities not excluded.
  var glided={},i;
  for(i=0;i<tr.length;i++){if(_SELF_ANNOUNCING[tr[i][4]])glided[tr[i][0]]=1;}
  var set={},out=[];
  for(i=0;i<tr.length;i++){var id=tr[i][0];
    if(glided[id]||set[id])continue;
    set[id]=1;out.push(id);}
  return out;
}
```

`_finish` change — one line (`scriba.js:418`):

```js
_emphasize(_manifestTargets(tr));   // OLD
_emphasize(_pulseTargets(tr));      // NEW
```

**Orphan note (house rule "clean up your own mess"):** this leaves `_manifestTargets` (`:353`) with no caller. Recommend **removing** it and updating its two test references (see PART 5), rather than leaving dead code that tests would still green-light. `_pulseTargets` subsumes its dedup role.

### 3.3 Jump / reverse paths

- **Reverse single step is already covered** — no extra work. `show` routes `d===-1` through the same `animateTransition`→`_finish` (`:446`), and `_invertManifest` keeps `cursor_move`/`value_change`/`position_move` self-inverse (kind preserved, `_INV_KIND` omits them, `:345`) and flips `add↔remove`. So `_pulseTargets` on the inverted manifest still sees the self-announcing kind and excludes it. The reverse glide self-announces → its pulse is correctly dropped. (Confirmed by `_INV_KIND`/`_invertRec` `:345-351`.)
- **Multi-step jump stays UNCHANGED** (`_emphasize(_changedTargets(from,i))`, `:452`). Justification (Confirmed): a `>1`-step jump calls `snapToFrame` (`:451`), which cancels anims and swaps `innerHTML` (`:113-124`) — **no per-kind WAAPI motion plays** (no glide/bounce/draw). Nothing self-announced, so the pulse IS the sole arrival signal for every changed identity across the skipped frames; `_changedTargets` (union, no kind filter, `:354-362`) is exactly right. Applying self-announce exclusion here would leave a jump-onto-a-moved-caret showing neither motion nor pulse → illegible.
  *Out-of-scope secondary (Deduced, flagged for the lead):* `snapToFrame` still fades in genuinely-new annotations via `_fadeInNewAnnotations` (`:123`), so on a jump a newly-added annotation both fades and pulses — a minor residual double on the jump path only. Left untouched per mandate; note for a later pass.

### 3.4 Motion-ruleset rule (A-9)

Add one A-card to `docs/spec/motion-ruleset.md` (same `### A-N — Title` / **Normative** / **Since** / prose / **Code ref** / **Test ref** shape the sync checker scans, `check_ruleset_sync.py:_check_code_ref`). Draft:

> **### A-9 — Delta-emphasis excludes self-announcing kinds**
> **Normative:** MUST — **Since:** v0.27.0
> On the animated single-step path, delta-emphasis (A-3) MUST pulse only the changed identities that did NOT already self-announce. A kind is *self-announcing* when its handler plays a per-element transform / draw-on / opacity during the step (`value_change`, `element_add/remove`, `position_move`, `annotation_add/remove`, `cursor_move`); a pulse on top is redundant double-signaling. *Silent* kinds (`recolor`, `highlight_on/off`, `annotation_recolor`) are instant class swaps and KEEP the pulse. Exclusion is by **identity** (an identity that glided AND recolored is excluded whole) via a two-pass over the manifest. The multi-step jump path is exempt: a jump snaps with no per-kind motion, so the pulse is the sole arrival signal there.
> **Code ref:** `scriba/animation/static/scriba.js:_pulseTargets`; `scriba/animation/static/scriba.js:_SELF_ANNOUNCING` *(pending v0.27.0-dev until the commit lands, then flip)*.
> **Test ref:** `tests/unit/test_runtime_reverse.py:TestSelfAnnounceExclusion` *(pending v0.27.0-dev)*.

The `pending` escape hatch keeps `check_ruleset_sync.py` green pre-implementation (`check_ruleset_sync.py` docstring; A-2/A-3/A-4 use the same pattern). ID `A-9` matches the scanner regex `A-[0-9]+[a-z]?`.

### 3.5 Invariants preserved

- **0 new motion kinds.** Only *which targets* receive the existing `.scriba-emphasis` class changes; the closed kind registry (A-2) is untouched. (Confirmed — differ.py not edited; `_INV_KIND`/handlers unchanged.)
- **NO new CSS.** Reuses `.scriba-emphasis`/`.scriba-emphasis-pulse` (`css:917-925`). The inlined stylesheet is byte-identical across the fix (Deduced — no CSS file edited).
- **A-3 / A-8 hold.** Still compositor-only, still `fs=0`, still reduced-motion/opt-out gated — `_emphasize`'s gates (`:369-371`) are untouched; only its argument narrows.

---

## PART 4 — Golden / version impact (correcting the PART-4 hypothesis)

**Bump:** `SCRIBA_VERSION 19→20` (`scriba/_version.py`, currently `19`), `__version__ 0.26.2→0.27.0`. Forced by the shared-asset `scriba.js` change (motion-ruleset Version Policy, `motion-ruleset.md:245-247`: a `scriba.js` change moves the external hash AND the inline slice → every interactive page's bytes move → bump + full interactive re-bless).

**Which golden files change — 93, not 5.** Evidence:
1. The emphasis class is applied at **runtime**, never baked into static SVG. Corpus-wide grep for `class="…scriba-emphasis…"` **on any element = 0 matches** (Confirmed). So no golden's SVG geometry, `tr` island, or narration bytes move.
2. `differ.py` is untouched → the `tr:[…]` manifests in every island are byte-identical → `tests/golden/animation/differ_*.json` unchanged (Confirmed — no differ edit).
3. No CSS edit → the inlined `<style>` bytes are identical (Deduced).
4. The **only** changed bytes are the inline `<script>` CORE region (the `_finish` line + inserted `_SELF_ANNOUNCING` + new `_pulseTargets` − removed `_manifestTargets`), which is byte-identical across every widget. **93 of 107** corpus HTMLs inline that region (`grep -lF '_emphasize(_manifestTargets(tr))'` = 93; Confirmed) → all 93 re-bless, the delta repeated once per widget in each file (the showcase carries 2 widgets → 2× per file).

**Which do NOT change (Confirmed):** the 14 static/diagram corpus HTMLs (`05_diagram_prescan`, `diagram*`, `plane2d*`, `apt_window_diagram`, `gep_v2_smoke`, `test_edge_overlap`, `test_plane2d_dense/edges`, `test_reference_tex_heavy`) — no runtime; the 5 `tests/golden/animation/html_*.html` (all `CORE=0`, incl. `html_static_mode` and `html_value_change`) — static-mode, no runtime; `differ_*.json`; `smart_label/`.

⇒ **The mandate's "only cursor_move/position_move goldens change" is refuted.** Those kinds' presence (cursor 1 file, position 4 files) determines which *behaviors* change; it has **zero** bearing on which golden *bytes* change, because emphasis behavior was never in the bytes. The correct re-bless set is "every interactive golden," uniformly.

**Expected diff character (so the implementer verifies a clean re-bless):** every re-blessed golden's diff is confined to inline-`<script>` hunks — the `_emphasize(_manifestTargets(tr))`→`_emphasize(_pulseTargets(tr))` swap, the removed `function _manifestTargets`, and the added `var _SELF_ANNOUNCING=…` + `function _pulseTargets`, appearing identically once per widget. **No hunk may fall inside any `svg:` backtick template, `narration:`, `tr:[…]`, `fs:`, or the `<style>` block.** A diff touching an `svg:` string means geometry leaked — investigate before blessing.

---

## PART 5 — RED-first test plan (source-inspection; no browser, matches house style)

The runtime has no JS rig; `tests/unit/test_runtime_reverse.py` pins it by brace-matching functions against BOTH the asset and the `_build_inline_script` inline slice (`_SOURCES`, `test_runtime_reverse.py:30-49`). Extend that file with `class TestSelfAnnounceExclusion` (parametrized over `_SOURCES`), each assertion encoding a behavioral guarantee:

1. **`test_self_announcing_set_named`** — `var _SELF_ANNOUNCING={` in `src` (single source of truth exists).
2. **`test_self_announcing_membership`** — regex-extract the `{…}` literal (like `test_inv_kind_omits_self_inverse_kinds:89`); assert the 7 self-announcing keys present (`value_change:`, `element_add:`, `element_remove:`, `position_move:`, `annotation_add:`, `annotation_remove:`, `cursor_move:`) and the 4 silent keys **absent** (`recolor:`, `highlight_on:`, `highlight_off:`, `annotation_recolor:`). *Encodes: cursor_move excluded, recolor retained.*
3. **`test_pulse_targets_two_pass`** — `function _pulseTargets(` exists; body has a pass keyed by `_SELF_ANNOUNCING[tr[i][4]]` writing `glided[tr[i][0]]`, then a second loop gated by `glided[id]`. *Encodes: exclusion is by identity, collected across all records → a glided-AND-recolored identity is excluded whole.*
4. **`test_finish_uses_pulse_targets`** — `_emphasize(_pulseTargets(tr))` in `animateTransition`, and `_emphasize(_manifestTargets(tr))` **absent**. ⚠️ **This flips the existing `test_finish_pulses_arrival` (`:159-163`)**, which asserts the old string — update it in the same change (expected RED→GREEN).
5. **`test_jump_path_unchanged`** — `show` still contains `_emphasize(_changedTargets(from,i))` (existing `test_jump_snaps_and_emphasizes:122-128` stays green). *Encodes: a ≥2-frame jump still pulses all changed identities.*
6. **`test_reduced_motion_optout_unchanged`** — `_emphasize` still contains `_canAnim` and `data-scriba-no-emphasis` (existing `test_reduced_motion_and_opt_out_gated:238-241` stays green — gates untouched).
7. **Byte-lock** — add `_pulseTargets` to the `TestByteIdentical` param list (`:266-279`); **remove `_manifestTargets`** from it (`:274`); add a `_SELF_ANNOUNCING` literal asset==inline check mirroring `test_inv_kind_table_is_byte_identical:286-289`.
8. **Ruleset sync** — `tests/unit/test_motion_ruleset_sync.py` must stay green: the A-9 card carries `**Code ref:**`/`**Test ref:**` (use `pending v0.27.0-dev` until symbols land).

*Optional stronger oracle (lead's call):* port the 4-line `_pulseTargets` two-pass into a Python helper test and run it on the real showcase manifest, asserting `pulse == {"a.cell[2]"}` (recolor-only kept; `w.var[i]` value_change and `a.cursor[i]-solo` cursor_move dropped) and on a `01_variablewatch_shrink` frame asserting `vars.var[detail]` (recolor+value_change) is dropped. Rejected as primary because a port drifts from the JS source of truth; the source-inspection form is the house contract.

---

## Conclusion & confidence

The fix is a class-complete, structural narrowing of the delta-emphasis target set: a named `_SELF_ANNOUNCING` closed set (7 kinds) + a two-pass identity exclusion in `_pulseTargets` replacing `_manifestTargets` on `_finish`'s single-step pulse, plus motion-ruleset A-9. It removes the redundant pulse for all 5 double-signaling kinds (flagship `cursor_move`, `position_move`, `value_change`, `element_add`, `annotation_add`), keeps the pulse for the 4 silent kinds where it is the real signal, leaves the multi-step jump path (the genuine no-motion arrival) untouched, adds no motion kind and no CSS, and re-blesses the 93 interactive goldens uniformly by an inline-`<script>`-only delta with zero SVG drift.

- Classification (7 self-announcing / 4 silent): **HIGH** — every kind's handler + CSS read directly.
- Double-signal map (5 firing today): **HIGH** — flagship manifest traced end-to-end + 107-file census.
- Two-pass necessity: **HIGH** — 463 corpus frames with same-identity glide+silent.
- Golden shift = 93 files, SVG-stable, script-only: **HIGH** — 0 baked-emphasis elements, 93/107 inline-CORE count, differ/CSS untouched.
- Residual (Deduced, out-of-scope): annotation fade-in still doubles on the jump path via `_fadeInNewAnnotations` — flagged, not fixed.
