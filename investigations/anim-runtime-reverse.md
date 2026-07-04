# Reverse & jump tweening + delta-emphasis — wiring the runtime that already tweens

> Design investigation. **No repo source modified.** Feature request: animation-clarity (JudgeZone) Tier 1 —
> ① reverse & jump tweening, ② delta-emphasis. Repo @ `main` `5925bb1`, scriba 0.22.2. Every `path:line`
> citation was read this session against that tree; the wire format and the load-bearing kind-matrix claims
> were **executed** — three docs rendered via `render.py` (`SCRIBA_ALLOW_ANY_OUTPUT=1`) into the scratchpad and
> their emitted `tr:` manifests read back (see the Evidence Ledger, §9).
>
> Evidence grades: **[Confirmed]** = read directly in source or observed in rendered output this session ·
> **[Deduced]** = logical consequence of confirmed facts · **[Hypothesized]** = design proposal, not yet built.

---

## 1. Hand-off Brief (3 sentences)

The claim is correct: the diff engine (`differ.py`) already emits a full per-pair transition manifest and the
runtime (`scriba.js`) already has WAAPI handlers for 9 of the 10 kinds, but the **only wire missing** is
directionality — `show(i,animate)` animates *exclusively* when `i===cur+1` (scriba.js:332), so Prev, ArrowLeft
and every non-adjacent move fall through to `snapToFrame`, and there is in fact **no multi-step jump affordance
in the UI at all** (dots are render-only, no click handler — scriba.js:34,78). Reverse is a small, contained
change because the destination-relative machinery (`animateTransition` parses the *target* SVG, commits `cur`
early, and guards every async callback with the `_gen`/`myGen` race token) already works in both directions —
you only need to feed it the **inverted** manifest `frames[cur].tr` (the sole manifest that describes the
`cur-1 ↔ cur` delta), via a pure `_invertManifest` helper that swaps `from/to` and maps `add↔remove` /
`on↔off`. Jump (>1 step) is best served by **snap + delta-emphasis** rather than tween-chaining, because the
client has no serialized state to net-diff (only `{svg,narration,substory,label,tr,fs}` ships — no
`shape_states`), so ② is not a separate nicety but the mechanism that makes ① legible for jumps.

---

## 2. What actually exists today (Confirmed)

### 2.1 Navigation surface — everything is ±1

| Control | scriba.js | Calls | Animates? |
|---|---|---|---|
| Next button | 339 | `show(cur+1,true)` | forward tween |
| ArrowRight / Space | 342 | `show(cur+1,true)` | forward tween |
| Prev button | 338 | `show(cur-1,false)` | **snap** |
| ArrowLeft | 343 | `show(cur-1,false)` | **snap** |
| Dots | 34 decl; 74–79 class only | — | **not clickable** |
| Initial | 350 | `show(0,false)` | snap |

`show(i,animate)` (331–337) gates animation on
`animate && i===cur+1 && frames[i] && frames[i].tr && _canAnim` (332); every other path → `snapToFrame(i)`.
So the runtime *can never* tween backward or across a gap today, regardless of `animate`. **[Confirmed]**

There is **no** slider, no `hashchange` handler, no Home/End key, and no dot click listener anywhere in the
CORE region — the `dots` NodeList is read once (34) and only ever has its `className` rewritten in
`_updateControls` (78). Jump is therefore a **latent** capability: nothing in the shipped UI can request a
move of more than one step. **[Confirmed]**

### 2.2 The manifest is forward-only and adjacent-only

`_html_stitcher.py` computes `compute_transitions(frames[i-1], frames[i])` for `i in range(1, len(frames))`
and stores the result at index `i` (573–574). Frame 0 gets `tr:null` (571); any frame whose manifest is empty
or exceeds `_MAX_TRANSITIONS=150` also gets `tr:null` (575–577, differ.py:368). Each frame serializes as:

```
{svg:`…`, narration:`…`, substory:`…`, label:`…`, tr:<manifest|null>, fs:<0|1>}   // stitcher 594–598
```

- `tr` = compact `[[target, prop, from, to, kind], …]` (differ.py `to_compact` 41–46). **[Confirmed, live]**
- `fs` = **"needs full innerHTML sync"** boolean — `"1"` iff the rendered SVG string differs from the previous
  frame's (586–587,593). It is *not* "full state." **[Confirmed]**
- **No `shape_states`, no per-frame state dict, ships to the client.** The only backward-delta information
  available on the client is `frames[cur].tr` (the manifest that took `cur-1 → cur`). **[Confirmed]**
- Substory frames serialize `{svg, narration}` only (stitcher 349–352) — no `tr`/`fs`, so **substories are
  snap-only forever**; this whole investigation concerns the top-level widget only. **[Confirmed]**

### 2.3 The runtime is one source, sliced two ways

`static/scriba.js` is authoritative. `_script_builder.py` slices the region between
`// __SCRIBA_CORE_START__` (scriba.js:25) and `// __SCRIBA_CORE_END__` (351) **verbatim** and wraps it with a
`W`/`frames` binding (60–84) to produce the inline `<script>`. External-runtime pages instead reference
`scriba.<hash>.js` with an SRI `integrity="sha384-…"` (_script_builder.py:147). **Consequence:** any edit
inside the CORE region rewrites the inline slice in *every* inline widget **and** changes
`RUNTIME_JS_SHA384` → every golden HTML and every hash/asset pin churns. This is the dominant cost of the
change and it is mechanical, not logical (§7). **[Confirmed]**

---

## 3. Kind matrix — emit × JS handler × reversibility

Columns: **Emit** = differ.py line(s) that construct the `Transition`; **JS** = `_applyTransition` branch
(scriba.js) or ✗ if none; **Rev** = inverse is well-defined.

| kind | Emit (differ.py) | JS handler (scriba.js) | mechanism | Reversible |
|---|---|---|---|---|
| `recolor` | 97, 176 | 122 | swap `scriba-state-*` class → CSS `transition:fill 180ms` (primitives.css:851–860) | ✅ swap from/to |
| `value_change` | 110, 189 | 130 | write `<text>` (guarded on `$`), scale-pulse `vt` | ✅ swap + **null guard** |
| `highlight_on` | 119, 203 | 141 | add `.scriba-highlighted` | ✅ → `highlight_off` |
| `highlight_off` | 161, 214 | 151 | strip `.scriba-highlighted` | ✅ → `highlight_on` |
| `element_add` | 84 | 166 | clone from *target* SVG, fade opacity 0→1 | ✅ → `element_remove` |
| `element_remove` | 139 | 159 | fade opacity 1→0 on live node | ✅ → `element_add` |
| `position_move` | 233 | 185 | `translate(from−to)→translate(0)` (see §3.1) | ✅ swap from/to (mirror) |
| `annotation_add` | 302; trace 263 | 205 | draw-on stroke-dashoffset, else fade | ✅ → `annotation_remove` (§4.4) |
| `annotation_remove` | 311; trace 269 | 198 | fade opacity 1→0 | ✅ → `annotation_add` |
| `annotation_recolor` | 324 | **✗ NONE** | — | needs handler first (§3.2) |

Nine handlers, ten kinds. The `_applyTransition` if/else chain (119–276) has **no `annotation_recolor`
branch** — the record falls through to a no-op. **[Confirmed]** Verified live: a `\reannotate` emits
`["dp.cell[1][1]-solo","state","info","good","annotation_recolor"]` with `fs:1`, so the recolor only ever
appears via the end-of-transition full-SVG swap; on an `fs:0` pair it is a total no-op (this is the
"BUG 3 — `\reannotate` is a no-op" the demo doc itself documents). **[Confirmed, live]**

### 3.1 `position_move` — what the handler does, and a sign caveat (question a/b)

Handler (185–197): `dx = from.x − to.x`, keyframes `translate(dx,dy) → translate(0,0)`, `fill:forwards`, on
the element queried from the **live (old) stage**. Live manifest, confirmed:
`["T.node[3]","position","200,270","30,270","position_move"]`, and every `position_move` frame carries `fs:1`.
**[Confirmed, live]** Because the element is mutated on the *old* DOM (`stage` is not swapped until
`_finish`), the visual midpoint depends on whether the old element is treated as sitting at `from` or `to`;
the `fs:1` full-sync that always accompanies these frames masks any residual offset by hard-swapping to the
target SVG at the end. **I could not verify the on-screen trajectory without a browser** (§8, Q1). This does
**not** block the inverse: inverting is a pure `from/to` swap, so the reverse inherits *exactly* whatever
correctness the forward has — it is its mirror by construction. **[Deduced]**

### 3.2 `annotation_recolor` (question c)

Emitted (differ.py:324), never handled. Two independent reasons it is invisible mid-transition: (1) no JS
branch; (2) even with a branch, the selector would miss for pill annotations (§3.3). Recommendation in §4.5.

### 3.3 Annotation selector key mismatch (adjacent Confirmed finding — affects reverse fidelity)

The differ keys annotations `{target}-{arrow_from|"solo"}` (differ.py:290, `_annotation_key` 241–243) and the
runtime selects `[data-annotation="{that key}"]` (scriba.js:199, 206). The SVG emitter has **two** key
schemes:

- `_svg_helpers.py:2854` → `{target}-{arrow_from}` / `{target}-solo` — **matches** the differ (arrow-style
  and solo-arc annotations).
- `_svg_helpers.py:3661` → `{target}-position-{position}` — **does not match** (position-only "pill"
  annotations, `_position_only_anns` 3088+).

Live proof from the same SVG: an arrow annotation is `data-annotation="dp.cell[2][2]-dp.cell[1][1]"`
(matches) but a pill is `data-annotation="dp.cell[1][1]-position-above"` while its manifest target is
`dp.cell[1][1]-solo` (misses). **[Confirmed, live]** So **forward** `annotation_add`/`annotation_remove`
already silently no-op their WAAPI tween for pill annotations and rely on `fs` full-sync; **reverse inherits
the identical limitation** — not a regression, but it caps reverse fidelity for pill annotations (§8, Q3).
Traces are safe: differ `{target}.trace[{id}]-solo` == emitter `g.trace[p]-solo`, verified live. **[Confirmed]**

---

## 4. Reversal design, per kind (Prev = invert `frames[cur].tr`)

The manifest at index `cur` describes `cur-1 → cur`. To step `cur → cur-1`, invert each record. A single pure
helper does the whole job; the existing handlers then run **unchanged**.

```js
// lives inside the CORE region so the inline slice inherits it verbatim
var _INV_KIND = {annotation_add:'annotation_remove', annotation_remove:'annotation_add',
                 element_add:'element_remove',       element_remove:'element_add',
                 highlight_on:'highlight_off',       highlight_off:'highlight_on'};
function _invertRec(r){                 // r = [target, prop, from, to, kind]
  return [r[0], r[1], r[3], r[2], _INV_KIND[r[4]] || r[4]];   // swap from/to; map or keep kind
}
function _invertManifest(tr){ var o=[]; for(var i=0;i<tr.length;i++)o.push(_invertRec(tr[i])); return o; }
```

Per-kind semantics of that one rule:

| Forward | Inverse | Reads to the learner as | Notes |
|---|---|---|---|
| `recolor` from→to | `recolor` to→from | color eases back | CSS transition auto-tweens the class swap; no JS motion needed |
| `value_change` a→b | `value_change` b→a | old value returns, gentle pulse | **null guard** below |
| `highlight_on` | `highlight_off` | highlight lifts | class strip |
| `highlight_off` | `highlight_on` | highlight returns | class add |
| `element_add` | `element_remove` | the new node fades away | node exists in the *current* DOM → fade 1→0 |
| `element_remove` | `element_add` | the removed node fades back | clone from `parsed` = `frames[cur-1].svg` (the destination) |
| `position_move` from→to | `position_move` to→from | node slides back to where it was | pure mirror (§3.1) |
| `annotation_add` | `annotation_remove` | the arrow/pill fades out (§4.4) | reuse existing remove handler |
| `annotation_remove` | `annotation_add` | the arrow/pill re-draws / fades in | clone from `parsed` = destination |

### 4.1 Why `parsed = frames[toIdx].svg` is correct in both directions

`animateTransition` parses the **destination** SVG (scriba.js:289) and the two "materialize a node" handlers
(`element_add` 167, `annotation_add` 206) clone from it. Forward: `toIdx=cur+1`, they clone the *newly
appearing* node from `cur+1`'s SVG. Reverse: `toIdx=cur-1`, the inverse of an `element_remove` is an
`element_add` that must clone the *reappearing* node — from `cur-1`'s SVG, which is exactly the destination.
So the destination-relative design already does the right thing backward; no per-direction branching in the
handlers. **[Deduced]**

### 4.2 `value_change` null guard (Confirmed hazard)

Live manifests contain `["info.cell[1]","value",null,"1","value_change"]` — a `null` `from`. Inverting yields
`to = null`. The current handler writes text when `String(toVal).indexOf('$')===-1` (136); `String(null)` is
`"null"`, so a naive inverse would stamp the literal `"null"` into the cell. Fix: guard on
`toVal != null` **and** the `$` check, so a null-target inverse **pulses only** (no text write) — identical in
spirit to the math-`$` no-raw-flash fix already shipped at 133–136. **[Confirmed hazard / Hypothesized fix]**

### 4.3 The phase split reorders itself correctly

`animateTransition` buckets `annotation_add`/`highlight_on` into phase-1 and the rest into phase-2 (291–296),
staggered by `DUR_STAGGER=50` (326). Because the split reads `rec[4]` **after** inversion, a reversed
`highlight_off→highlight_on` naturally lands in phase-1 and a reversed `annotation_add→annotation_remove`
lands in phase-2 — "things that appear/highlight first, then moves/removes." No change to the split logic is
needed. **[Deduced]**

### 4.4 `annotation_add` inverse: fade-out, not reverse-draw (recommendation + rationale)

The forward `annotation_add` for a trace/arrow is a draw-on (stroke-dashoffset len→0, 228–266). The tempting
"symmetric" inverse is a draw-**off** (0→len then remove). **Recommend the plain fade-out** (the existing
`annotation_remove` handler, opacity 1→0, 198–204) instead, because: (1) it reuses a shipped, tested handler
— zero new motion code; (2) reverse-drawing a stroke reads as "un-drawing / erasing tip-first," a novel motion
that draws *more* attention to the mechanic than to the state change the learner is trying to re-see; (3) the
learner's model when stepping back is "the thing that appeared is now gone" — a quick fade says that
unambiguously and matches how every other removal reads. Draw-off is a defensible polish option if design
insists, but it is strictly more code and more risk for less clarity. **[Hypothesized — design call, §8 Q2]**

### 4.5 `annotation_recolor`: add a minimal handler (optional, closes a shipped bug)

To make reverse *and* forward correct, add a branch mirroring `recolor` but on the annotation node:

```js
}else if(kind==='annotation_recolor'){
  var elc=stage.querySelector('[data-annotation="'+_cssEscape(target)+'"]');
  if(elc){ /* swap annotation state class fromVal→toVal, same className.baseVal dance as recolor */ }
}
```

Inverse is the same branch with `from/to` swapped (the generic rule handles it). **Caveat:** for pill
annotations this still misses on the `-position-` key (§3.3), so it only fixes arrow-style recolors until the
key schism is reconciled. This is **scope beyond pure reverse** (it changes forward behavior / touches a
documented bug), so gate the decision explicitly (§8, Q3). **[Hypothesized]**

---

## 5. Jump policy (>1 step) — recommend **snap + delta-emphasis**

Three options, against the confirmed constraint that **no client state ships** (§2.2):

| Option | How | Verdict |
|---|---|---|
| (i) chain-replay | tween each intermediate pair in sequence | ✗ N·(~230ms) feels sluggish for N>2; reverse-chaining needs composed inverses; fragile |
| (ii) client net-delta | **compose** `frames[k].tr` for `k in (min,max]` (recolors: first-from/last-to; add+remove cancel; value first/last; position first/last) | ⚠ feasible (compose the *manifests*, since state is absent) but real complexity + new goldens + new bug surface |
| (iii) **snap + emphasis** | `snapToFrame(i)` then pulse the changed targets | ✅ instant, deterministic, reuses ②; lowest risk |

**Recommend (iii).** A jump is a context switch, not a motion to follow; the honest signal is "you are now
here, and *these* cells are what moved," which is precisely delta-emphasis. Crucially, emphasis-on-jump does
**not** need full manifest composition — it needs only the **set** of changed targets, which is the cheap
union of `rec[0]` over the skipped manifests:

```js
function _changedTargets(a,b){                 // exclusive a … inclusive b (or reverse)
  var lo=Math.min(a,b)+1, hi=Math.max(a,b), set={};
  for(var k=lo;k<=hi;k++){ var tr=frames[k]&&frames[k].tr; if(!tr)continue;
    for(var t=0;t<tr.length;t++)set[tr[t][0]]=1; }
  return Object.keys(set);
}
```

Since the shipped UI has no jump affordance (§2.1), this policy is **dormant until one is added**. If dots are
made clickable in the same change, they become the jump vector; otherwise the reverse wiring lands now and the
`Math.abs(d)>1` branch is a correct, tested no-tween until an affordance exists (§8, Q5).

---

## 6. Delta-emphasis design (②)

**Trigger.** On **arrival**, fire only when `_canAnim` is true and the arrival was a **snap that skipped a
tween** — i.e. jumps (and, if desired, single-step arrivals when the caller opts in). Single-step tweens are
self-emphasizing (the motion *is* the signal), so do not double-pulse them by default.

**Motion — WAAPI, not new CSS keyframes.** Reuse the existing pulse idiom (the value-change scale bounce at
138–139) so reduced-motion is handled by the *same* `_canAnim` gate with zero new `@media` rules:

```js
var DUR_EMPH=220, EMPH_CAP=8;
function _emphasize(targets){
  if(!_canAnim) return;                                   // reduced-motion off, for free
  if(W.getAttribute('data-scriba-emphasis')==='0') return; // opt-out (§6.1)
  if(targets.length>EMPH_CAP) return;                      // noise cap
  for(var i=0;i<targets.length;i++){
    var el=stage.querySelector('[data-target="'+_cssEscape(targets[i])+'"]');
    if(!el) continue;
    var a=el.animate([{transform:'scale(1)'},{transform:'scale(1.08)'},{transform:'scale(1)'}],
                     {duration:_dur(DUR_EMPH),easing:'ease-out'});  // no fill → auto-reverts, no cleanup class
    _anims.push(a);                                        // tracked → next nav's _cancelAnims().finish() settles it
  }
}
```

Compositor-safe (`transform` only). **[Hypothesized]**

**One CSS caveat:** an SVG `<g data-target>` scales from the user-space origin unless
`transform-box:fill-box; transform-origin:center` is set on the emphasis target — otherwise the pulse also
translates. That is a one-rule addition to `scriba-scene-primitives.css` (or an inline style set before
`.animate`). Needs a browser to confirm the exact selector; flagged §8 Q4. **[Hypothesized]**

**Cap.** `EMPH_CAP=8`: a jump spanning many changes should *not* flash a dozen cells at once — above the cap,
the snap alone carries. Mirrors the spirit of differ's `_MAX_TRANSITIONS=150` bail-out. **[Hypothesized]**

### 6.1 Opt-out plumbing (env flag → data attribute)

The widget already reads one tuning attribute — `data-scriba-speed` (scriba.js:53), hard-set to `"1"` in the
stitcher (619). Follow that exact channel for emphasis:

1. Add `emphasis: bool = True` to `AnimationOptions` (ast.py:327–335; today width/height/id/label/layout only)
   + one grammar key.
2. Thread it in `renderer.py` where `_opts.width/height/label/layout` already flow into `emit_html`
   (529–537) → `emit_interactive_html` → emit `data-scriba-emphasis="0"` on the widget `<div>` (stitcher
   618–619) when disabled.
3. JS reads `W.getAttribute('data-scriba-emphasis')==='0'` (already in `_emphasize` above).

Reduced-motion needs no attribute — `_canAnim` already suppresses it. If a per-scene flag is judged too much
surface for v1, a global `SCRIBA_*` env var (precedent: `SCRIBA_DEBUG` render.py:426, `SCRIBA_ALLOW_ANY_OUTPUT`
439) is the cheaper fallback, at the cost of per-scene control. **[Hypothesized — §8 Q4]**

---

## 7. Race & safety analysis

The rapid-nav hardening already in place (tests: `test_runtime_rapid_nav.py`, `test_runtime_unified.py`) is
**inherited for free** because reverse reuses `animateTransition`:

- **Generation token.** `_cancelAnims` bumps `_gen` (56); `animateTransition` captures `myGen=_gen` (283);
  `_finish` (300) and `_runPhase2` (313) bail on `myGen!==_gen`. Reverse enters the same function → same
  guards. **[Confirmed mechanism / Deduced inheritance]**
- **Prev overrides Prev / Prev mid-forward-anim.** The reentrancy guard `if(_animState==='animating'){
  _cancelAnims(); snapToFrame(toIdx); return; }` (279) means a nav landing during any running tween **cancels
  and snaps** to the newest target. Keep this verbatim — it is the shipped, tested behavior and it is the
  right call for reverse too (a user hammering Prev wants to *get there*, not queue tweens). **[Confirmed]**
- **Early `cur` commit.** `cur=toIdx` before any async work (287) means a Prev arriving mid-animation steps
  back from the *committed* target, not a stale index — the exact bug the rapid-nav fix cured, now covering
  reverse as well. **[Confirmed]**
- **Jump snap.** `snapToFrame` calls `_cancelAnims` first (99) → `_gen++` orphans any in-flight tween. Then
  `_emphasize` pushes its pulses to `_anims`, so the *next* nav's `_cancelAnims().finish()` settles them to
  `scale(1)` (no `fill` → last keyframe is identity). No stray pulse survives a supersede. **[Deduced]**
- **Reduced motion.** `show` only routes to `animateTransition` when `_canAnim` (must be preserved for the
  reverse branch); `_emphasize` early-returns on `!_canAnim`. Everything degrades to snap with no pulse, as
  today. **[Confirmed gate / Deduced]**
- **Theme swap.** The `MutationObserver` on `data-theme` does `_cancelAnims(); snapToFrame(cur)` (346–348) —
  untouched, still valid. **[Confirmed]**

**`needsSync` correctness for reverse (subtle).** Forward reads `needsSync = !!frames[toIdx].fs` (298). For a
reverse `cur → cur-1`, the pair's SVG-change truth lives in `frames[cur].fs` (the manifest being inverted),
**not** `frames[cur-1].fs`. The generalized signature must therefore pass the *source* frame's `fs` on reverse
(§7.1 in the patch). Getting this wrong would skip a needed full-sync and leave a stale node. **[Deduced]**

---

## 8. Open questions (≤5)

1. **`position_move` forward trajectory.** Does the handler (185–197, mutating the *old* DOM element with
   `translate(from−to)→0`) render a clean slide today, or does it visually jump and rely on the accompanying
   `fs:1` full-sync to hide it? Reverse mirrors whatever the answer is; needs a browser frame-capture to
   confirm forward is actually smooth. (Playwright is intentionally not installed this session.)
2. **`annotation_add` inverse motion:** plain fade-out (recommended, reuses `annotation_remove`) vs. reverse
   stroke draw-off. Pedagogy/taste call for the design owner.
3. **Scope of the `annotation_recolor` fix + the `-solo` vs `-position-` key schism (§3.3).** Do we (a) ship
   reverse only and let annotation_recolor keep deferring to `fs` full-sync, or (b) add the handler *and*
   reconcile the emitter/differ key so pill annotations actually animate forward and back? (b) fixes a
   documented bug but widens the diff into `_svg_helpers.py`.
4. **Emphasis surface:** per-scene `AnimationOptions.emphasis` flag (parser + renderer thread) vs. a global
   `SCRIBA_*` env var; and is the one-rule `transform-box:fill-box` CSS addition acceptable for the SVG scale?
5. **Jump affordance:** wire reverse only now (leaving the `|d|>1` branch a correct dormant no-tween), or make
   dots clickable / add Home-End in the same change to actually create jump vectors and light up ②?

---

## 9. RED-first test plan

All existing runtime tests are **source-inspection** over both `_ASSET` (static/scriba.js) and `_INLINE`
(`_build_inline_script(...)`), using brace-matching (`_fn`) / regex extractors — no browser rig
(`test_runtime_unified.py`, `test_runtime_rapid_nav.py`). New pins follow that exact shape. Write these
**RED first**, against both sources:

| # | Test (assert on both asset + inline) | RED because |
|---|---|---|
| R1 | `_invertManifest`/`_invertRec` exist; byte-identical asset==inline | helper absent |
| R2 | `prev` click handler emits `show(cur-1,true)`; ArrowLeft too | currently `,false` (338,343) |
| R3 | `show` body routes `d===-1` (or `i===cur-1`) into `animateTransition` w/ inverted manifest | branch absent (332) |
| R4 | `_INV_KIND` maps `annotation_add↔annotation_remove`, `element_add↔element_remove`, `highlight_on↔highlight_off`; `_invertRec` swaps `r[3],r[2]` | absent |
| R5 | `value_change` branch guards `toVal!=null` (not just `$`) | only `$` guarded (136) |
| R6 | `show` snaps (no `animateTransition`) when `Math.abs(i-cur)>1` | branch absent |
| R7 | `_emphasize` exists; references `_canAnim` **and** `data-scriba-emphasis`; `EMPH_CAP` const present | absent |
| R8 | `animateTransition` signature takes an explicit manifest + `fs` (not `frames[toIdx].tr`/`.fs` literally) | hard-wired (280,298) |
| R9 | (if §4.5 chosen) `_applyTransition` has an `annotation_recolor` branch | absent |
| R10 | Extend `test_core_is_byte_identical` (unified 114–119): add `show`, `animateTransition`, `_applyTransition`, `_invertManifest`, `_emphasize` to the asset==inline byte-lock list | new fns must be locked |

**Expected churn (regen, not logic):**
- Every golden HTML with an inline widget (`tests/golden/examples/corpus/*.html`, `docs/cookbook/**/output.html`)
  — the CORE slice text changes. Regen via the repo's golden-update path.
- External-runtime hash/asset pins (`test_csp_external_runtime.py`, `test_runtime_asset.py`) — `RUNTIME_JS_SHA384`
  and `scriba.<hash>.js` filename change. Regen the hash.
- `test_runtime_rapid_nav.py` / `test_runtime_unified.py` existing pins should stay GREEN (the race machinery
  is reused, not rewritten) — if any go RED, the generalization of `animateTransition` broke a guard: fix the
  code, not the test.

---

## 10. Patch plan (JS-first; Python only for the opt-out)

All JS edits are **inside** the CORE region (25–351) so the inline slice inherits them.

### 10.1 `show(i, animate)` — the one real behavior change (331–337)

```js
function show(i,animate){
  var d=i-cur;
  if(animate&&_canAnim&&frames[i]){
    if(d===1 && frames[i].tr){            animateTransition(i, frames[i].tr,               frames[i].fs); return; }
    if(d===-1 && frames[cur].tr){         animateTransition(i, _invertManifest(frames[cur].tr), frames[cur].fs); return; }
    // |d|>1 → fall through to snap + emphasis
  }
  snapToFrame(i);
  if(animate && Math.abs(d)>1) _emphasize(_changedTargets(cur/*==i after snap*/, /*old*/ i - d)); // see note
}
```
*(Note: `snapToFrame` sets `cur=i` at 101; capture the pre-snap `cur` before calling, or pass both indices to
`_changedTargets`. Trivial local var; shown loosely here.)*

### 10.2 `animateTransition(toIdx, manifest, fsFlag)` — generalize (278)

Two-line change, everything else verbatim:
- 280 `var tr=frames[toIdx]&&frames[toIdx].tr;` → `var tr=manifest;`
- 298 `var needsSync=!!(frames[toIdx]&&frames[toIdx].fs);` → `var needsSync=!!fsFlag;`

`parsed=frames[toIdx].svg` (289) stays — correct destination for both directions (§4.1). The reentrancy
guard, `myGen`, early `cur` commit, phase split, `_finish`, `_runPhase2` are all untouched → race safety
carries (§7).

### 10.3 New helpers (add near `_applyTransition`, inside CORE)

`_INV_KIND`, `_invertRec`, `_invertManifest` (§4); `_changedTargets` (§5); `_emphasize` + consts
`DUR_EMPH`, `EMPH_CAP` (§6).

### 10.4 `_applyTransition` (119) — two surgical edits

- 136 value_change guard: `if(txt && toVal!=null && String(toVal).indexOf('$')===-1){txt.textContent=toVal;}`
- (optional §4.5) add the `annotation_recolor` branch.

### 10.5 `snapToFrame` (98) — leave pure

Do **not** bake emphasis into `snapToFrame` (it also runs on init `show(0,false)`, theme swaps, and cancels).
Call `_emphasize` from `show`'s jump branch only.

### 10.6 Wire the reverse-capable controls

- prev click 338: `show(cur-1,false)` → `show(cur-1,true)`
- ArrowLeft 343: `show(cur-1,false)` → `show(cur-1,true)`
- (next/ArrowRight/Space already pass `true`.)

### 10.7 Python (only if §6.1 per-scene opt-out is chosen)

`AnimationOptions.emphasis` (ast.py) + grammar key + thread through `renderer.py` (529–537) into the widget
`data-scriba-emphasis` attribute (stitcher 618–619). No change to `differ.py` or the manifest wire format.

### Risk table

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Golden + hash churn from CORE edit | High reach | Certain | Mechanical regen; §9 lists targets; CI diff is expected |
| `value_change` inverse stamps `"null"` | Med | Certain w/o fix | Null guard (§4.2, R5) |
| `position_move` inverse looks wrong because *forward* is wrong | Med | Unknown | Inverse is a pure mirror; resolve forward via browser probe (§8 Q1) |
| Pill-annotation add/remove/recolor tween silently no-ops | Low (pre-existing) | Certain for pills | Document; not a regression; optional key reconciliation (§8 Q3) |
| SVG emphasis scales off-center | Med | Likely w/o CSS | `transform-box:fill-box; transform-origin:center` (§6, Q4) |
| Generalizing `animateTransition` nicks a race guard | High | Low | R10 byte-lock + existing rapid-nav pins stay GREEN |
| `annotation_recolor` handler widens scope into emitter | Med | Only if §4.5 (b) | Gate as an explicit decision (Q3); reverse ships without it |
