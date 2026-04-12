# Animation v1 — Detailed Implementation Plan

**Date:** 2026-04-12
**Based on:** Research reports 01–06 in this folder
**Goal:** Smooth forward-step transitions for Scriba's interactive widget. Backward/dot-jump = instant snap. No new `.tex` syntax in v1.

---

## Architecture Overview

```
Python (build time):
  list[FrameData]  ──>  compute_transitions(prev, curr)  ──>  TransitionManifest
                                                                     │
  _emit_frame_svg()  ──>  SVG strings                               │
       │                                                             │
       └──────────────> emit_interactive_html() <────────────────────┘
                              │
                              v
                  frames = [{svg, narration, tr}, ...]

Browser (runtime):
  show(i, animate=true)
    ├── tr exists? ──YES──> animateTransition(cur, i)
    │                         1. Swap narration immediately
    │                         2. Parse target SVG via DOMParser
    │                         3. Remove elements: WAAPI opacity 1→0
    │                         4. Recolor elements: swap CSS class (CSS transition handles fill/stroke)
    │                         5. Update text: el.querySelector('text').textContent = newVal
    │                         6. Add elements: clone from parsed SVG, WAAPI opacity 0→1
    │                         7. Promise.all(finished) → snapToFrame(i)
    │
    └── NO ──> snapToFrame(i)  (innerHTML swap, same as today)
```

---

## Golden File Testing Strategy

Every agent that produces output (differ manifests, HTML output) must also
produce **expected golden files** that future test runs diff against. The
agent writes the expected file **by hand from the specification** — it does
NOT compile a `.tex` file and save the output. This ensures the expected
file reflects the *intended* behavior, not whatever the code happens to
produce today.

### Directory layout

```
tests/
  golden/
    animation/
      # Differ engine golden files (Agent A)
      differ_recolor.json              # expected manifest for idle→current
      differ_value_change.json         # expected manifest for value "?"→"4"
      differ_element_add.json          # expected manifest for new target
      differ_element_remove.json       # expected manifest for removed target
      differ_mixed.json                # expected manifest for multi-shape mixed changes
      differ_annotations.json          # expected manifest with annotation add/remove
      differ_empty.json                # expected manifest for identical frames
      differ_over_threshold.json       # expected manifest with skip_animation=true

      # Full HTML golden files (Agent G)
      two_step_recolor_expected.html   # full HTML output for 2-step recolor animation
      value_change_expected.html       # full HTML output for value change animation
      element_add_expected.html        # full HTML output for push/add animation
      static_mode_expected.html        # full HTML output for --static mode (no tr)
```

### How golden files are written

**Rule: agents write expected files from the SPEC, not from running the code.**

For differ manifests (JSON):
- Agent A reads the `FrameData` input for each test case
- Agent A writes the expected `TransitionManifest.to_compact()` output by hand
- The test loads the JSON and compares with `compute_transitions()` output

For full HTML golden files:
- Agent G reads the `.tex` source for each test case
- Agent G writes the expected HTML by hand, following the spec:
  - Widget structure (`<div class="scriba-widget">`, controls, stage, narration, print frames)
  - Frame JS array with `tr:` field containing the expected manifest
  - The `<script>` block with `_canAnim`, `animateTransition`, `snapToFrame`, etc.
  - CSS transition rules in `<style>` if standalone mode
- The test compiles the `.tex` and compares key fragments against the golden file

### How tests compare

**NOT full string equality** — HTML output has dynamic parts (scene IDs, hashes).
Instead, tests extract and compare **structured fragments**:

```python
def _extract_tr_fields(html: str) -> list[str | None]:
    """Extract all tr: values from the JS frames array."""
    # Match tr:null or tr:[[...]]
    pattern = r'tr:(null|\[\[.*?\]\])'
    return re.findall(pattern, html)

def _extract_svg_data_targets(html: str) -> list[str]:
    """Extract all data-target values from the HTML."""
    return re.findall(r'data-target="([^"]+)"', html)

def test_two_step_recolor():
    actual_html = compile_tex(SOURCE)
    expected = load_golden("two_step_recolor_expected.html")

    # Compare tr fields
    assert _extract_tr_fields(actual_html) == _extract_tr_fields(expected)

    # Compare data-target presence
    assert _extract_svg_data_targets(actual_html) == _extract_svg_data_targets(expected)

    # Compare key JS functions exist
    assert '_cancelAnims' in actual_html
    assert 'animateTransition' in actual_html
    assert 'prefers-reduced-motion' in actual_html
```

For differ JSON golden files, comparison is exact:

```python
def test_recolor_manifest():
    prev = FrameData(...)  # defined in test
    curr = FrameData(...)  # defined in test
    actual = compute_transitions(prev, curr).to_compact()
    expected = json.loads(Path("tests/golden/animation/differ_recolor.json").read_text())
    assert actual == expected
```

### Golden file update workflow

When the implementation intentionally changes output format:
1. Run tests → they fail because golden files are stale
2. **Manually review** the new output to confirm it's correct
3. Update golden files (agent can do this, but the diff must be reviewed)
4. Tests pass again

Golden files are **never auto-generated** from code output. They are always
written from the spec first, then updated manually when the spec changes.

---

## Wave 1 — Foundation (3 agents, parallel, no dependencies)

---

### Agent A: Frame-Diff Engine

**Create:** `scriba/animation/differ.py`
**Create:** `tests/animation/test_differ.py`
**Create:** `tests/golden/animation/differ_*.json` (8 golden files)
**Touch nothing else.**

#### Context the agent needs

`FrameData` is defined at `scriba/animation/emitter.py:68-78`:

```python
@dataclass(frozen=True, slots=True)
class FrameData:
    step_number: int
    total_frames: int
    narration_html: str
    shape_states: dict[str, dict[str, dict]]  # shape_name -> target_key -> {state, value, label, highlighted, apply_params}
    annotations: list[dict]  # [{target, label, ephemeral, arrow_from, color}]
    label: str | None = None
    substories: list[SubstoryData] | None = None
```

The `shape_states` dict nests like:
```python
{
    "arr": {
        "arr.cell[0]": {"state": "current", "value": "5", "highlighted": True},
        "arr.cell[1]": {"state": "idle", "value": "3"},
    },
    "dp": {
        "dp.cell[0]": {"state": "done", "value": "0"},
    }
}
```

The `annotations` list contains dicts like:
```python
{"target": "dp.cell[3]", "label": "+4", "ephemeral": False, "arrow_from": "dp.cell[0]", "color": "good"}
```

#### What to build

**File: `scriba/animation/differ.py`**

```python
"""Frame-diff engine — computes transition manifests between consecutive frames."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scriba.animation.emitter import FrameData

# Performance threshold: if more than this many transitions in a single
# frame pair, skip animation entirely (instant snap).  Report 06 §1.1.
_MAX_TRANSITIONS = 150


@dataclass(frozen=True, slots=True)
class Transition:
    """A single property change between two frames."""
    target: str       # e.g. "arr.cell[0]", "G.edge[(A,B)]"
    prop: str         # "state" | "value" | "label" | "add" | "remove" | "highlighted"
    from_val: str | None
    to_val: str | None
    kind: str         # "recolor" | "value_change" | "element_add" | "element_remove"
                      # | "highlight_on" | "highlight_off"
                      # | "annotation_add" | "annotation_remove" | "annotation_recolor"


@dataclass(frozen=True, slots=True)
class TransitionManifest:
    """All transitions for one frame pair."""
    transitions: tuple[Transition, ...]
    skip_animation: bool = False  # True when len > _MAX_TRANSITIONS

    def to_compact(self) -> list[list[str | None]]:
        """Serialize to array-of-arrays for JSON embedding.
        
        Each inner array: [target, prop, from_val, to_val, kind]
        """
        return [
            [t.target, t.prop, t.from_val, t.to_val, t.kind]
            for t in self.transitions
        ]


def compute_transitions(prev: FrameData, curr: FrameData) -> TransitionManifest:
    """Diff two consecutive frames, return a transition manifest."""
    ...
```

**Diff algorithm** (implement inside `compute_transitions`):

1. **Shape states diff** — iterate `prev.shape_states.keys() | curr.shape_states.keys()`:
   - For each shape, iterate `prev_targets.keys() | curr_targets.keys()`
   - Target in curr but not prev → `Transition(target, "add", None, curr_state, "element_add")`
   - Target in prev but not curr → `Transition(target, "remove", prev_state, None, "element_remove")`
   - Both exist:
     - `prev["state"] != curr["state"]` → `Transition(target, "state", prev_state, curr_state, "recolor")`
     - `prev.get("value") != curr.get("value")` → `Transition(target, "value", prev_val, curr_val, "value_change")`
     - `prev.get("highlighted") != curr.get("highlighted")`:
       - curr highlighted → `"highlight_on"`
       - prev highlighted → `"highlight_off"`

2. **Annotations diff** — match by composite key `(target, arrow_from or "solo")`:
   - Build `prev_anns: dict[tuple, dict]` and `curr_anns: dict[tuple, dict]`
   - Key in curr not prev → `annotation_add`
   - Key in prev not curr → `annotation_remove`
   - Both exist, color changed → `annotation_recolor`

3. **Performance gate** — if `len(transitions) > _MAX_TRANSITIONS`, return `TransitionManifest(transitions, skip_animation=True)`

#### Test file: `tests/animation/test_differ.py`

Write **at least 15 test cases** using pytest. Each test that checks manifest output
must compare against a golden JSON file in `tests/golden/animation/`.

| Test | Scenario | Golden file |
|------|----------|-------------|
| `test_identical_frames` | Same shape_states → empty manifest | `differ_empty.json` |
| `test_single_recolor` | One cell idle→current → 1 recolor transition | `differ_recolor.json` |
| `test_multiple_recolors` | 5 cells change state → 5 recolor transitions | (inline assert on len) |
| `test_value_change` | Cell value "?"→"4" → 1 value_change | `differ_value_change.json` |
| `test_state_and_value_change` | Both state and value change → 2 transitions for same target | (inline) |
| `test_element_add` | New target in curr → element_add | `differ_element_add.json` |
| `test_element_remove` | Target absent in curr → element_remove | `differ_element_remove.json` |
| `test_highlight_on` | highlighted False→True → highlight_on | (inline) |
| `test_highlight_off` | highlighted True→False → highlight_off | (inline) |
| `test_annotation_add` | New annotation in curr → annotation_add | `differ_annotations.json` |
| `test_annotation_remove` | Annotation absent in curr → annotation_remove | (shares `differ_annotations.json`) |
| `test_annotation_recolor` | Same (target, arrow_from) different color → annotation_recolor | (inline) |
| `test_empty_frames` | Both frames have empty shape_states → empty manifest | (shares `differ_empty.json`) |
| `test_performance_threshold` | >150 transitions → skip_animation=True | `differ_over_threshold.json` |
| `test_to_compact_format` | Verify array-of-arrays output shape | (inline) |
| `test_multi_shape_diff` | 2+ shapes with mixed changes | `differ_mixed.json` |
| `test_add_and_remove_same_step` | One target removed, another added | (inline) |

Use `FrameData` directly — import from `scriba.animation.emitter`.

#### Golden files: `tests/golden/animation/differ_*.json`

**Write these by hand from the spec, NOT by running compute_transitions.**

Each golden file is the expected output of `TransitionManifest.to_compact()` — an array-of-arrays.

Example `differ_recolor.json` (for `test_single_recolor`):
```json
[
  ["arr.cell[0]", "state", "idle", "current", "recolor"]
]
```

Example `differ_value_change.json` (for `test_value_change`):
```json
[
  ["dp.cell[1]", "value", "?", "4", "value_change"]
]
```

Example `differ_element_add.json` (for `test_element_add`):
```json
[
  ["arr.cell[5]", "add", null, "idle", "element_add"]
]
```

Example `differ_empty.json` (for `test_identical_frames` and `test_empty_frames`):
```json
[]
```

Example `differ_over_threshold.json` (for `test_performance_threshold`):
- The JSON is an array with >150 entries (agent generates 151 recolor entries)
- The test checks `manifest.skip_animation is True` AND `manifest.to_compact()` matches the golden file

Example `differ_mixed.json` (for `test_multi_shape_diff`):
```json
[
  ["arr.cell[0]", "state", "idle", "current", "recolor"],
  ["arr.cell[1]", "state", "current", "done", "recolor"],
  ["dp.cell[3]", "value", "?", "7", "value_change"],
  ["G.node[A]", "add", null, "idle", "element_add"]
]
```

Example `differ_annotations.json` (for `test_annotation_add`):
```json
[
  ["dp.cell[3]-dp.cell[0]", "add", null, "good", "annotation_add"]
]
```

**Test helper pattern:**

```python
import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "animation"

def _load_golden(name: str) -> list:
    return json.loads((GOLDEN_DIR / name).read_text())

def test_single_recolor():
    prev = FrameData(
        step_number=1, total_frames=2, narration_html="",
        shape_states={"arr": {"arr.cell[0]": {"state": "idle"}}},
        annotations=[],
    )
    curr = FrameData(
        step_number=2, total_frames=2, narration_html="",
        shape_states={"arr": {"arr.cell[0]": {"state": "current"}}},
        annotations=[],
    )
    manifest = compute_transitions(prev, curr)
    assert manifest.to_compact() == _load_golden("differ_recolor.json")
    assert manifest.skip_animation is False
```

#### Acceptance criteria

- `pytest tests/animation/test_differ.py -v` → all pass
- `from scriba.animation.differ import compute_transitions, TransitionManifest, Transition` works
- `ruff check scriba/animation/differ.py` → no errors
- `mypy scriba/animation/differ.py --ignore-missing-imports` → no errors

---

### Agent B: CSS Transition Declarations

**Edit:** `scriba/animation/static/scriba-scene-primitives.css`
**Edit:** `render.py`
**Touch nothing else.**

#### Task 1: Add transition rules to `scriba-scene-primitives.css`

Insert a new section **after line 627** (after the `@media (prefers-reduced-motion: reduce)` closing brace, before the MetricPlot section):

```css
/* ============================================
   Animation — CSS transitions for state morphs
   
   When the JS runtime swaps a CSS state class on a
   <g data-target> element (e.g. scriba-state-idle →
   scriba-state-current), these rules interpolate
   fill/stroke/text smoothly instead of snapping.
   ============================================ */

/* Rect and circle fill/stroke morph */
[data-target] > rect,
[data-target] > circle {
  transition: fill 180ms ease-out,
              stroke 180ms ease-out,
              stroke-width 180ms ease-out;
}

/* Edge stroke morph */
[data-target] > line {
  transition: stroke 180ms ease-out,
              stroke-width 180ms ease-out,
              opacity 200ms ease-out;
}

/* Text fill morph (includes halo stroke via paint-order) */
[data-target] > text {
  transition: fill 180ms ease-out,
              stroke 180ms ease-out;
}

/* Dim state: opacity + desaturation */
.scriba-state-dim {
  transition: opacity 200ms linear,
              filter 200ms linear;
}
```

**IMPORTANT:** The existing `@media (prefers-reduced-motion: reduce)` block at lines 604-625 already sets `transition-duration: 0.01ms !important` on `*` — this automatically kills the new transitions for reduced-motion users. Do NOT add a duplicate reduced-motion block.

The existing `@media print` block at lines 645+ already hides the interactive stage — animation never runs in print mode. No new print rule needed.

#### Task 2: Mirror into `render.py` HTML_TEMPLATE

In `render.py`, the `<style>` block ends around line 500. Insert the same CSS transition rules **before the closing `</style>` tag** (before line 500).

The render.py template uses `{{` and `}}` for literal braces in Python f-strings (it's actually a `.format()` template). So the CSS must be:

```
/* Animation — CSS transitions for state morphs */
[data-target] > rect,
[data-target] > circle {{
  transition: fill 180ms ease-out,
              stroke 180ms ease-out,
              stroke-width 180ms ease-out;
}}
[data-target] > line {{
  transition: stroke 180ms ease-out,
              stroke-width 180ms ease-out,
              opacity 200ms ease-out;
}}
[data-target] > text {{
  transition: fill 180ms ease-out,
              stroke 180ms ease-out;
}}
.scriba-state-dim {{
  transition: opacity 200ms linear,
              filter 200ms linear;
}}
```

Insert after the existing `.scriba-stage svg, .scriba-narration` transition rule at line 394-397 (which does `transition: opacity 0.2s ease`).

#### Acceptance criteria

- `ruff check render.py` → no errors
- Open any existing cookbook HTML in browser → cells still render correctly (transitions are inert because no class swaps happen mid-frame yet)
- Verify the reduced-motion and print rules are NOT duplicated
- The CSS in `render.py` exactly mirrors `scriba-scene-primitives.css` (same selectors, same values, but with `{{`/`}}` escaping)

---

### Agent C: JS Animation Runtime

**Edit:** `scriba/animation/emitter.py` — the `emit_interactive_html()` function (lines 700-884)
**Touch nothing else.**

#### Context

The current JS widget is at lines 837-884. The `show(i)` function at line 865-875 does `stage.innerHTML=frames[i].svg` — this is what we're replacing.

The frames JS array at line 765-768 currently looks like:
```js
{svg:`...`,narration:`...`,substory:`...`,label:`...`}
```

After this change, it will look like:
```js
{svg:`...`,narration:`...`,substory:`...`,label:`...`,tr:null}
// or
{svg:`...`,narration:`...`,substory:`...`,label:`...`,tr:[["arr.cell[0]","state","idle","current","recolor"],...]}
```

(The `tr` field embedding is done by Agent D in Wave 2. Agent C only writes the JS runtime that *consumes* `tr`.)

#### What to change

Replace the `<script>` block (lines 837-884) in the `emit_interactive_html` function. The new JS must:

1. **Keep all existing functionality unchanged** (prev/next buttons, keyboard, dots, substory init, step counter)

2. **Add these new functions/variables:**

```js
var _anims=[];  // active WAAPI Animation objects
var _animState='idle';  // 'idle' | 'animating'

// Check if animation is supported and desired
var _canAnim=(typeof Element.prototype.animate==='function')
  && !window.matchMedia('(prefers-reduced-motion:reduce)').matches;

// Parse SVG string into a document
function _parseSvg(s){
  return new DOMParser().parseFromString(s,'image/svg+xml');
}

// Cancel all running animations, snap to final state
function _cancelAnims(){
  _anims.forEach(function(a){try{a.finish();}catch(e){}});
  _anims=[];
  _animState='idle';
}

// Instant frame swap (same as today's show())
function snapToFrame(i){
  _cancelAnims();
  cur=i;
  stage.innerHTML=frames[i].svg;
  narr.innerHTML=frames[i].narration;
  subC.innerHTML=frames[i].substory||'';
  subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
  ctr.textContent='Step '+(i+1)+' / '+frames.length;
  prev.disabled=i===0;
  next.disabled=i===frames.length-1;
  dots.forEach(function(d,j){d.className='scriba-dot'+(j===i?' active':j<i?' done':'');});
}

// Animated transition from cur to i
function animateTransition(toIdx){
  if(_animState==='animating'){_cancelAnims();snapToFrame(toIdx);return;}
  
  var tr=frames[toIdx].tr;
  if(!tr||!tr.length||!_canAnim){snapToFrame(toIdx);return;}

  _animState='animating';
  var DUR=180;
  
  // 1. Swap narration immediately (screen reader timing)
  narr.innerHTML=frames[toIdx].narration;
  ctr.textContent='Step '+(toIdx+1)+' / '+frames.length;
  prev.disabled=toIdx===0;
  next.disabled=toIdx===frames.length-1;
  dots.forEach(function(d,j){d.className='scriba-dot'+(j===toIdx?' active':j<toIdx?' done':'');});
  
  // 2. Parse target frame SVG
  var tDoc=_parseSvg(frames[toIdx].svg);
  var tSvg=tDoc.documentElement;
  
  // 3. Process transitions
  var pending=[];
  for(var k=0;k<tr.length;k++){
    var t=tr[k]; // [target, prop, fromVal, toVal, kind]
    var target=t[0], kind=t[4], toVal=t[3];
    var esc=CSS.escape(target);
    var el=stage.querySelector('[data-target="'+esc+'"]');
    
    if(kind==='recolor'){
      // Swap CSS class — CSS transition handles the interpolation
      if(el){
        el.className.baseVal=el.className.baseVal
          .replace(/scriba-state-\S+/,'scriba-state-'+toVal);
      }
    }
    else if(kind==='value_change'){
      if(el){
        var txt=el.querySelector('text');
        if(txt)txt.textContent=toVal||'';
      }
    }
    else if(kind==='highlight_on'){
      if(el&&!el.classList.contains('scriba-highlighted'))
        el.classList.add('scriba-highlighted');
    }
    else if(kind==='highlight_off'){
      if(el)el.classList.remove('scriba-highlighted');
    }
    else if(kind==='element_remove'){
      if(el){
        var a=el.animate([{opacity:1},{opacity:0}],
          {duration:DUR,easing:'ease-out',fill:'forwards'});
        pending.push(a);_anims.push(a);
      }
    }
    else if(kind==='element_add'){
      var newEl=tSvg.querySelector('[data-target="'+esc+'"]');
      if(newEl){
        var clone=document.importNode(newEl,true);
        clone.style.opacity='0';
        // Find parent group in current DOM to insert into
        var par=stage.querySelector('[data-primitive]')||stage.querySelector('svg');
        if(par){
          par.appendChild(clone);
          var a2=clone.animate([{opacity:0},{opacity:1}],
            {duration:DUR,easing:'ease-out',fill:'forwards'});
          pending.push(a2);_anims.push(a2);
        }
      }
    }
    else if(kind==='annotation_add'){
      var annEl=tSvg.querySelector('[data-annotation="'+esc+'"]');
      if(annEl){
        var ac=document.importNode(annEl,true);
        ac.style.opacity='0';
        var ap=stage.querySelector('svg');
        if(ap){
          ap.appendChild(ac);
          var a3=ac.animate([{opacity:0},{opacity:1}],
            {duration:200,easing:'ease-out',fill:'forwards'});
          pending.push(a3);_anims.push(a3);
        }
      }
    }
    else if(kind==='annotation_remove'){
      var re=stage.querySelector('[data-annotation="'+esc+'"]');
      if(re){
        var a4=re.animate([{opacity:1},{opacity:0}],
          {duration:200,easing:'ease-out',fill:'forwards'});
        pending.push(a4);_anims.push(a4);
      }
    }
  }
  
  // 4. After all WAAPI animations finish, snap to canonical SVG
  if(pending.length>0){
    Promise.all(pending.map(function(a){return a.finished;})).then(function(){
      _anims=[];
      _animState='idle';
      // Final canonical snap — ensures DOM correctness
      stage.innerHTML=frames[toIdx].svg;
      cur=toIdx;
      // Substory injection after snap
      subC.innerHTML=frames[toIdx].substory||'';
      subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
    }).catch(function(){
      // Animation was cancelled — snapToFrame already handled it
      _animState='idle';
    });
  } else {
    // Only CSS transitions (recolors), no WAAPI pending
    // Wait for CSS transitions to settle, then snap
    setTimeout(function(){
      _animState='idle';
      stage.innerHTML=frames[toIdx].svg;
      cur=toIdx;
      subC.innerHTML=frames[toIdx].substory||'';
      subC.querySelectorAll('.scriba-substory-widget[data-scriba-frames]').forEach(initSub);
    }, DUR+20);
  }
}

// New show() with animate parameter
function show(i,animate){
  if(animate && i===cur+1 && frames[i].tr && _canAnim){
    animateTransition(i);
  } else {
    snapToFrame(i);
  }
}
```

3. **Update event listeners** to use the new `show(i, animate)`:

```js
// Replace existing:
prev.addEventListener('click',function(){if(cur>0)show(cur-1,false);});
next.addEventListener('click',function(){if(cur<frames.length-1)show(cur+1,true);});
W.addEventListener('keydown',function(e){
  if(e.key==='ArrowRight'||e.key===' '){e.preventDefault();if(cur<frames.length-1)show(cur+1,true);}
  if(e.key==='ArrowLeft'){e.preventDefault();if(cur>0)show(cur-1,false);}
});
```

4. **Add dark-mode cancel** (MutationObserver):

```js
// Cancel animations on theme change
if(typeof MutationObserver!=='undefined'){
  new MutationObserver(function(){_cancelAnims();if(cur>=0)snapToFrame(cur);})
    .observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
}
```

5. **Call `show(0,false)` at init** (same as today's `show(0)`).

#### Critical constraints

- ALL JS must be inside the f-string template literal in `emit_interactive_html`. Use `{{` and `}}` for JS braces.
- Keep under ~2 KB minified for the new animation code (existing widget JS is ~1 KB).
- Must work in `file://` protocol (no fetch, no imports).
- `CSS.escape` is available in all modern browsers (Chrome 46+, Firefox 31+, Safari 10+).
- The `tr` field may be `null` or `undefined` for frames without transitions — handle gracefully.

#### Acceptance criteria

- Existing `pytest` suite still passes (the JS is a string literal, tests don't execute it)
- `ruff check scriba/animation/emitter.py` → no errors
- The function `emit_interactive_html` produces valid HTML with the new `<script>` block
- When `tr` is null/absent, behavior is identical to today (full `innerHTML` swap)

---

## Wave 2 — Integration (3 agents, parallel, after Wave 1 merges)

---

### Agent D: Emitter Wiring

**Edit:** `scriba/animation/emitter.py` — the `emit_interactive_html()` function
**Create:** `tests/integration/test_animation_manifest.py`
**Touch nothing else.**

**Prerequisite:** Agent A's `differ.py` and Agent C's JS runtime must be merged first.

#### What to change

**1. Add import at top of `emitter.py`** (after line 19):
```python
from scriba.animation.differ import compute_transitions
```

**2. Compute transition manifests** in `emit_interactive_html()`. After the single-pass frame rendering loop (after line 810, before the `js_frames_str` join at line 811), add:

```python
import json as _json

# Compute transition manifests for consecutive frame pairs
manifests: list[str] = ['null']  # Frame 0 has no previous frame
for i in range(1, len(frames)):
    manifest = compute_transitions(frames[i - 1], frames[i])
    if manifest.skip_animation or not manifest.transitions:
        manifests.append('null')
    else:
        manifests.append(_json.dumps(manifest.to_compact()))
```

**3. Embed `tr` field in JS frames array.** Change the `js_frames.append` at line 765-768 from:

```python
js_frames.append(
    f'{{svg:`{svg_escaped}`,narration:`{narration_escaped}`,'
    f'substory:`{substory_escaped}`,label:`{label_escaped}`}}'
)
```

To:

```python
tr_json = manifests[frame_idx]  # need to track frame index in the loop
js_frames.append(
    f'{{svg:`{svg_escaped}`,narration:`{narration_escaped}`,'
    f'substory:`{substory_escaped}`,label:`{label_escaped}`,'
    f'tr:{tr_json}}}'
)
```

You'll need to enumerate the loop — change `for frame in frames:` (line 742) to `for frame_idx, frame in enumerate(frames):`.

**BUT WAIT — important subtlety.** The `manifests` list is computed from `FrameData` objects, but the frames loop at line 742 calls `_emit_frame_svg()` which has side effects (apply_command on primitives). The manifests must be computed BEFORE the SVG rendering loop (because compute_transitions only reads `shape_states` and `annotations`, not the SVG). OR, compute manifests after the loop using saved FrameData objects.

**Recommended approach:** Compute manifests AFTER the rendering loop (lines 742-809), before the join at line 811:

```python
# --- Compute transition manifests ---
manifests: list[str] = ['null']
for i in range(1, len(frames)):
    manifest = compute_transitions(frames[i - 1], frames[i])
    if manifest.skip_animation or not manifest.transitions:
        manifests.append('null')
    else:
        manifests.append(_json.dumps(manifest.to_compact()))
```

Then you need to build the JS frames with the tr field. Since `js_frames` was built in the loop without `tr`, you'll need to either:
- **Option A:** Post-process `js_frames` list to inject `tr` field (string manipulation — fragile)
- **Option B:** Collect manifests first, then build js_frames in a second pass (duplicates the escape work)
- **Option C:** Build js_frames during the loop but defer the `tr` field to after. Use a list of tuples.

**Best approach: Option C.**

Replace the `js_frames.append(...)` with building a list of `(svg_escaped, narration_escaped, substory_escaped, label_escaped)` tuples. After the loop, compute manifests, then build `js_frames` by zipping tuples with manifests.

#### Test file: `tests/integration/test_animation_manifest.py`

```python
"""Test that compiled .tex files produce correct transition manifests in HTML output."""

import re
from scriba.animation.emitter import FrameData, emit_interactive_html

def test_two_frame_recolor_produces_tr():
    """A simple 2-frame animation where cell[0] goes idle→current should produce a tr manifest."""
    frames = [
        FrameData(
            step_number=1, total_frames=2,
            narration_html="Step 1",
            shape_states={"a": {"a.cell[0]": {"state": "idle"}}},
            annotations=[],
        ),
        FrameData(
            step_number=2, total_frames=2,
            narration_html="Step 2",
            shape_states={"a": {"a.cell[0]": {"state": "current"}}},
            annotations=[],
        ),
    ]
    # Need primitives — create a minimal mock
    # ... (use a real Array primitive or a mock with bounding_box/emit_svg)
    ...

def test_identical_frames_produce_null_tr():
    ...

def test_over_threshold_produces_null_tr():
    ...

def test_first_frame_has_null_tr():
    ...
```

#### Acceptance criteria

- `pytest tests/integration/test_animation_manifest.py -v` → all pass
- Output HTML contains `tr:` field in JS frames array
- Frame 0 always has `tr:null`
- Identical consecutive frames have `tr:null`
- `ruff check scriba/animation/emitter.py` → no errors

---

### Agent E: Annotation Identity Attributes

**Edit:** `scriba/animation/primitives/array.py`
**Edit:** `scriba/animation/primitives/dptable.py`
**Touch nothing else.** (Graph/tree/plane2d/metricplot annotations are v2 scope.)

#### Context

Annotations in array.py are emitted at line 500-504:

```python
lines.append(
    f'  <g class="scriba-annotation scriba-annotation-{color}"'
    f' opacity="{s_opacity}"'
    f' role="graphics-symbol" aria-label="{ann_desc}">'
)
```

Annotations in dptable.py are emitted at line 472:

```python
lines.append(
    f'  <g class="scriba-annotation scriba-annotation-{color}">'
)
```

#### What to change

Add a `data-annotation` attribute to the `<g>` element. The key is `{target}-{arrow_from or 'solo'}`:

**array.py** — change line 500-503 to:

```python
ann_key = f"{target}-{arrow_from}" if arrow_from else f"{target}-solo"
lines.append(
    f'  <g class="scriba-annotation scriba-annotation-{color}"'
    f' data-annotation="{_escape_xml(ann_key)}"'
    f' opacity="{s_opacity}"'
    f' role="graphics-symbol" aria-label="{ann_desc}">'
)
```

**dptable.py** — same pattern at line 472.

Find the annotation's `target` and `arrow_from` values in each file's annotation rendering method. In array.py it's `_emit_arrow()` method. In dptable.py it's `_emit_arrows()` method.

#### Acceptance criteria

- `pytest` → all existing tests pass (no regression)
- Output SVG for annotations now includes `data-annotation="dp.cell[3]-dp.cell[0]"` style attributes
- `ruff check scriba/animation/primitives/array.py scriba/animation/primitives/dptable.py` → no errors

---

### Agent F: render.py Standalone Template Sync

**Edit:** `render.py`
**Touch nothing else.**

**Prerequisite:** Agent B's CSS changes and Agent C's JS runtime must be merged first.

#### Context

`render.py` has its own `HTML_TEMPLATE` (lines 58-512) which is a self-contained HTML page used by the CLI `python render.py input.tex output.html`. This template includes its own `<style>` block that mirrors `scriba-scene-primitives.css`, but the JS widget comes from `emit_interactive_html()` in `emitter.py` — NOT from render.py's template.

So render.py needs:
1. **CSS transitions** — Agent B already added these
2. **JS runtime** — comes from `emit_interactive_html()`, which Agent C already updated. No action needed here.

**The only thing Agent F needs to verify:**
- Agent B's CSS transition rules are correctly placed in `render.py`
- The `{{`/`}}` escaping is correct for Python `.format()` strings
- No rule was accidentally duplicated
- The reduced-motion block in render.py (if any) covers the new transition rules

**Actually, render.py does NOT have a reduced-motion block.** The existing reduced-motion block is only in `scriba-scene-primitives.css`. For standalone HTML files produced by render.py, we need to add one.

Add after the new CSS transition rules in render.py:

```
/* Reduced motion */
@media (prefers-reduced-motion: reduce) {{
  [data-target] > rect,
  [data-target] > circle,
  [data-target] > line,
  [data-target] > text,
  .scriba-state-dim {{
    transition-duration: 0ms !important;
  }}
}}
```

Also verify that the existing print rule at lines 441-447 (`@media print`) is sufficient — it only does `print-color-adjust`, no transition disable. Add:

```
@media print {{
  [data-target] > rect,
  [data-target] > circle,
  [data-target] > line,
  [data-target] > text {{
    transition: none !important;
  }}
}}
```

(Can be appended to the existing `@media print` block.)

#### Acceptance criteria

- `python render.py` with a test .tex file produces working HTML
- Open in browser → forward transitions work
- Toggle OS reduced-motion → transitions become instant
- Print preview → no animation artifacts
- `ruff check render.py` → no errors

---

## Wave 3 — Validation (2 agents, parallel, after Wave 2 merges)

---

### Agent G: Integration Tests + Golden HTML Files

**Create:** `tests/integration/test_animation_transitions.py`
**Create:** `tests/golden/animation/html_two_step_recolor.html`
**Create:** `tests/golden/animation/html_value_change.html`
**Create:** `tests/golden/animation/html_element_add.html`
**Create:** `tests/golden/animation/html_static_mode.html`
**Create:** `tests/golden/animation/html_identical_steps.html`
**Touch nothing else.**

Write integration tests that compile actual `.tex` source through the full pipeline,
then compare key structural fragments against hand-written golden HTML files.

#### Golden HTML file format

Each golden file is a **full HTML output** written by hand from the spec.
The agent does NOT compile `.tex` to produce these — they are the *expected* output.

Since full HTML comparison is brittle (scene IDs, hashes change), the golden files
serve as the **reference for structured extraction**. Tests extract specific fragments
and compare them.

**What to include in each golden file:**

1. The widget `<div class="scriba-widget">` container structure
2. The `<script>` block with the JS frames array — showing exact `tr:` field values
3. Print frames `<div class="scriba-print-frames">` with per-step SVG
4. The CSS transition rules (if testing standalone mode)

**What to leave as placeholders:**

- Scene ID: use `SCENE_ID` placeholder
- SVG content: use `<!-- SVG_FRAME_N -->` placeholder (SVG content is tested elsewhere)
- Narration: include the exact expected narration text

Example `html_two_step_recolor.html` structure:

```html
<!-- GOLDEN FILE: two-step recolor animation
     Source: \shape{a}{Array}{size=3, data=[1,2,3]}
             \step \recolor{a.cell[1]}{state=current} \narrate{Step 1}
             \step \recolor{a.cell[1]}{state=done} \narrate{Step 2}
     
     Expected tr fields:
       Frame 0: tr:null (no previous frame)
       Frame 1: tr:[["a.cell[1]","state","idle","current","recolor"]]
       Frame 2: tr:[["a.cell[1]","state","current","done","recolor"]]
-->
<div class="scriba-widget" id="SCENE_ID" tabindex="0">
  <div class="scriba-controls">
    <button class="scriba-btn-prev" aria-label="Previous step" disabled>Prev</button>
    <span class="scriba-step-counter" aria-live="polite" aria-atomic="true">Step 1 / 2</span>
    <button class="scriba-btn-next" aria-label="Next step">Next</button>
    <div class="scriba-progress">
      <div class="scriba-dot active"></div>
      <div class="scriba-dot"></div>
    </div>
  </div>
  <div class="scriba-stage"></div>
  <p class="scriba-narration" id="SCENE_ID-narration" aria-live="polite"></p>
  <div class="scriba-substory-container"></div>
  <div class="scriba-print-frames" style="display:none">
    <!-- print frame 1: a.cell[1] has scriba-state-current -->
    <!-- print frame 2: a.cell[1] has scriba-state-done -->
  </div>
</div>
<script>
(function(){
  // ... widget init ...
  var frames=[
    {svg:`<!-- SVG -->`,narration:`Step 1`,substory:``,label:``,tr:null},
    {svg:`<!-- SVG -->`,narration:`Step 2`,substory:``,label:``,tr:[["a.cell[1]","state","idle","current","recolor"]]}
  ];
  // ... JS runtime with _canAnim, animateTransition, snapToFrame, show ...
  // ... _cancelAnims, MutationObserver for dark-mode ...
})();
</script>
```

**For static mode** (`html_static_mode.html`), the golden file should be a filmstrip
layout with NO `<script>` block and NO `tr:` field — just the `<figure>` with `<ol>`.

#### Test extraction helpers

```python
import re
import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent.parent / "golden" / "animation"


def _load_golden(name: str) -> str:
    return (GOLDEN_DIR / name).read_text()


def _extract_tr_fields(html: str) -> list[str]:
    """Extract tr: values from JS frames array.
    
    Returns list like ['null', '[["a.cell[1]","state","idle","current","recolor"]]']
    """
    return re.findall(r',tr:(null|\[\[.*?\]\])\}', html)


def _extract_js_functions(html: str) -> set[str]:
    """Extract function names defined in the <script> block."""
    return set(re.findall(r'function\s+(\w+)', html))


def _has_animation_runtime(html: str) -> bool:
    """Check if the HTML includes the animation runtime."""
    return all(s in html for s in [
        '_cancelAnims', 'animateTransition', 'snapToFrame',
        '_canAnim', 'prefers-reduced-motion',
    ])


def _extract_data_targets(html: str) -> list[str]:
    """Extract all data-target attribute values."""
    return re.findall(r'data-target="([^"]+)"', html)
```

#### Tests to write

| Test | Source `.tex` | Golden file | What to compare |
|------|---------------|-------------|-----------------|
| `test_two_step_recolor_tr` | 2-step Array recolor | `html_two_step_recolor.html` | `_extract_tr_fields(actual) == _extract_tr_fields(golden)` |
| `test_value_change_tr` | 2-step with `\apply{value="4"}` | `html_value_change.html` | tr fields match |
| `test_element_add_tr` | 2-step with `\apply{arr}{push=5}` | `html_element_add.html` | tr fields match |
| `test_first_frame_always_null` | any multi-step | (any golden) | `_extract_tr_fields(actual)[0] == 'null'` |
| `test_static_mode_no_tr` | same source, static mode | `html_static_mode.html` | no `tr:` anywhere in output |
| `test_identical_steps_null` | 2 identical steps | `html_identical_steps.html` | all tr fields are `'null'` |
| `test_animation_runtime_present` | any interactive | (any golden) | `_has_animation_runtime(actual) is True` |
| `test_animation_runtime_absent_static` | static mode | `html_static_mode.html` | `_has_animation_runtime(actual) is False` |
| `test_data_targets_match` | 2-step Array | `html_two_step_recolor.html` | `_extract_data_targets(actual)` contains all expected targets |
| `test_large_manifest_skip` | 20x20 DPTable all-change step | (inline assert) | all tr fields after threshold are `'null'` |

Use the test patterns from `tests/integration/test_animation_end_to_end.py` as reference — it
compiles `.tex` strings through `AnimationRenderer` with `_render()` helper.

**Important:** The golden HTML file uses placeholder `SCENE_ID` and `<!-- SVG -->` markers.
The extraction helpers ignore these — they only compare the structural fragments (tr fields,
function names, data-targets). The golden file exists so a human reviewer can see the
**complete expected shape** of the output, not just isolated regex assertions.

#### Acceptance criteria

- `pytest tests/integration/test_animation_transitions.py -v` → all pass
- Full test suite `pytest` → 0 failures, 0 regressions
- Golden files in `tests/golden/animation/` are hand-written, not auto-generated
- Each golden HTML file has a comment header documenting the source `.tex` and expected behavior

---

### Agent H: Code Review

**Type:** `python-reviewer`
**Read-only — no edits.**

Review ALL files changed in Waves 1-2:

1. `scriba/animation/differ.py` — correctness of diff algorithm, edge cases, type annotations
2. `scriba/animation/emitter.py` — JS runtime security (XSS via target names in CSS.escape), template escaping, WAAPI usage
3. `scriba/animation/static/scriba-scene-primitives.css` — specificity conflicts, transition property coverage
4. `render.py` — `{{`/`}}` escaping correctness, reduced-motion/print coverage
5. `scriba/animation/primitives/array.py` — data-annotation attribute escaping
6. `scriba/animation/primitives/dptable.py` — same

**Security focus:**
- Can a malicious `data-target` value break out of `CSS.escape()` in the JS runtime?
- Can annotation labels inject HTML via the `data-annotation` attribute?
- Are all user-derived strings (`target`, `arrow_from`, annotation `label`) properly escaped?

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Animation tech | CSS transitions + WAAPI hybrid | 0 KB for color morphs, ~1.1 KB for add/remove fades. Report 01 recommendation. |
| Frame update | DOM diff via `data-target` keys + final `innerHTML` snap | Elements persist → CSS transitions fire. Full snap after animation ensures DOM correctness. |
| WAAPI fill mode | `fill: "forwards"` on WAAPI, then `innerHTML` snap replaces everything | Simpler than `fill: "none"` + manual class swap — the final snap is the cleanup. |
| Backward nav | Instant snap, no animation | Report 05 §6: reverse transitions deferred to v2. |
| Perf threshold | >150 simultaneous changes → snap | Report 06 §1.1: mobile Safari drops frames above ~100. |
| Narration timing | Swap at animation START | Report 06 §3.2: screen readers announce immediately. |
| Dark mode toggle | Cancel all animations, snap to current frame | Report 06 §5: WAAPI keyframes use resolved hex values that go stale. |
| Manifest format | Array-of-arrays JSON `[target, prop, from, to, kind]` | ~40% smaller than objects. |
| New `.tex` syntax | None in v1 | Report 04 Approach A (fully automatic). |

---

## v1 Scope Boundary

### MUST (launch blockers)

- Forward `Next` / `ArrowRight` animation (recolor, value change, add/remove opacity fade)
- `prefers-reduced-motion` support (duration = 0)
- Print fallback unbroken
- `--static` flag skips animation emission
- Standalone HTML works offline (inline JS, no CDN)
- Interrupt-and-snap on rapid clicks / keyboard
- Performance threshold (>150 = instant snap)
- Dark mode cancel-and-snap

### SHOULD (quality, not blockers)

- Highlight on/off CSS class toggle
- Annotation add/remove opacity fade (needs Agent E's `data-annotation`)

### v2 DEFER

- Reverse animation (Prev interpolation)
- Position lerp (graph node relayout, tree reparent)
- `\sequence{}` / `\stagger{}` authoring syntax
- Edge draw-in via `stroke-dashoffset`
- Per-step `transition=Nms` / `speed=Nx` options
- Autoplay mode / widget speed control
- Value crossfade / value counter / cell scale pulse

---

## File Impact Summary

| File | Change | Agent | Wave |
|------|--------|-------|------|
| `scriba/animation/differ.py` | **NEW** (200-300 lines) | A | 1 |
| `tests/animation/test_differ.py` | **NEW** (200-300 lines) | A | 1 |
| `tests/golden/animation/differ_*.json` | **NEW** (8 files, hand-written) | A | 1 |
| `scriba/animation/static/scriba-scene-primitives.css` | +25 lines CSS | B | 1 |
| `render.py` | +30 lines CSS | B, F | 1, 2 |
| `scriba/animation/emitter.py` | Rewrite `<script>` block (~120 lines) + manifest wiring (~30 lines) | C, D | 1, 2 |
| `scriba/animation/primitives/array.py` | +2 lines (data-annotation attr) | E | 2 |
| `scriba/animation/primitives/dptable.py` | +2 lines (data-annotation attr) | E | 2 |
| `tests/integration/test_animation_transitions.py` | **NEW** (200-300 lines) | G | 3 |
| `tests/golden/animation/html_*.html` | **NEW** (5 files, hand-written) | G | 3 |

---

## Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| WAAPI inline style left after animation | HIGH | Final `innerHTML` snap after `Promise.all(finished)` replaces everything — CSS classes take over |
| Rapid click queueing | HIGH | `_cancelAnims()` calls `finish()` on all active WAAPI, then `snapToFrame()` |
| Halo/fill color desync (180ms window) | HIGH | Accept for v1 — 3px halo stroke, barely visible during transition |
| Large DPTable perf | MED | `_MAX_TRANSITIONS=150` in differ.py → `skip_animation=True` → `tr:null` |
| Dark mode mid-animation | LOW | `MutationObserver` on `data-theme` → `_cancelAnims()` + `snapToFrame(cur)` |
| Print breakage | LOW | Animation targets `.scriba-stage` only; print uses `.scriba-print-frames` (separate DOM tree) |
| `CSS.escape` target injection | LOW | `CSS.escape` handles all metacharacters; `data-target` values are generated by Python primitives, not user input |

---

## Agent Spawn Summary

| Wave | Agent | Type | Isolation | Depends on |
|------|-------|------|-----------|------------|
| 1 | **A**: Differ engine | general-purpose | worktree | — |
| 1 | **B**: CSS transitions | general-purpose | worktree | — |
| 1 | **C**: JS runtime | general-purpose | worktree | — |
| 2 | **D**: Emitter wiring | general-purpose | worktree | A, C merged |
| 2 | **E**: Annotation identity | general-purpose | worktree | — |
| 2 | **F**: render.py sync | general-purpose | worktree | B, C merged |
| 3 | **G**: Integration tests | general-purpose | worktree | all merged |
| 3 | **H**: Code review | python-reviewer | — | all merged |

**Total: 8 agents, 3 waves.**
