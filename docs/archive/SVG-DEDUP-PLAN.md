# SVG Deduplication Plan

> Addresses HIGH finding from `deep-analysis-2026-04-10.md` §6 Performance:
> Every frame generates a complete, independent SVG. 100 frames × 5KB = 500KB.
> A diff-based approach could reduce output by 60-80%.

---

## 1. Problem

Interactive mode stores every frame as a full SVG string in a JS array:

```javascript
frames = [
  {svg: `<svg>...complete SVG...</svg>`, narration: `...`, substory: `...`},
  {svg: `<svg>...complete SVG...</svg>`, narration: `...`, substory: `...`},
  // ... N frames, each with ~2-3KB of near-identical SVG
]
```

On frame change: `stage.innerHTML = frames[i].svg` (full DOM replacement).

~95% of each SVG is static geometry (positions, shapes, defs, structure).
Only these things change between frames:
- **State CSS classes** (idle → current → done → dim)
- **Cell text values** (`""` → `"7"`)
- **Annotations** (arrows, labels — added/removed/recolored)
- **Highlights** (ephemeral borders)

---

## 2. Approach: Base SVG + Patch Array

### Concept

1. **Frame 0**: Emit complete SVG as `baseSvg`
2. **Frames 1..N**: Compute a diff against frame 0, store only the mutations
3. **Playback**: Clone `baseSvg` into DOM once; on frame change, apply/revert patches

### Patch Format

```javascript
const baseSvg = `<svg>...</svg>`;
const patches = [
  [],  // frame 0: no patches (is the base)
  [    // frame 1: 3 mutations
    {t: "a.cell[0]", a: "class", v: "scriba-state-current"},
    {t: "dp.cell[0]", a: "class", v: "scriba-state-done"},
    {t: "dp.cell[0]", a: "text", v: "0"},
  ],
  [    // frame 2: 5 mutations
    {t: "a.cell[0]", a: "class", v: "scriba-state-dim"},
    {t: "a.cell[1]", a: "class", v: "scriba-state-current"},
    {t: "dp.cell[1]", a: "class", v: "scriba-state-current"},
    // annotation additions...
    {t: "dp.cell[1]", a: "+ann", v: {label: "+7", from: "dp.cell[0]", color: "good"}},
  ],
];
```

### Patch Types

| Type | `a` value | Meaning |
|------|-----------|---------|
| State change | `"class"` | Set CSS class on element |
| Value change | `"text"` | Set text content of value `<text>` |
| Add annotation | `"+ann"` | Insert annotation arrow/label SVG |
| Remove annotation | `"-ann"` | Remove annotation SVG elements |
| Add highlight | `"+hl"` | Add ephemeral highlight border |
| Remove highlight | `"-hl"` | Remove ephemeral highlight |

### Playback JS

```javascript
function applyFrame(i) {
  if (i === 0) {
    stage.innerHTML = baseSvg;
    baseEl = stage.querySelector('svg');
    return;
  }
  // Reset to base state first, then apply patches up to frame i
  // OR: compute incremental diff from current frame to target
  const patch = patches[i];
  for (const p of patch) {
    const el = baseEl.querySelector(`[data-target="${p.t}"]`);
    if (!el) continue;
    switch (p.a) {
      case 'class': el.className.baseVal = p.v; break;
      case 'text': el.querySelector('.scriba-value').textContent = p.v; break;
      case '+ann': /* insert annotation SVG */ break;
      case '-ann': /* remove annotation SVG */ break;
    }
  }
}
```

---

## 3. Implementation

### Phase 1: Diff Engine (Python side)

**File: `scriba/animation/svg_diff.py`** (new)

```python
def compute_patches(frames: list[FrameSnapshot]) -> tuple[str, list[list[Patch]]]:
    """Given N frame snapshots, return (base_svg, patches).
    
    base_svg: complete SVG string for frame 0
    patches: list of N patch lists, where patches[0] = []
    """
```

For each frame i > 0, compare snapshot[i] against snapshot[0]:
- For each shape target, compare state, value, annotations, highlights
- Emit minimal patch entries

This does NOT require SVG parsing — we already have structured `FrameSnapshot`
data (shape states, values, annotations) in `scene.py`. We diff the snapshots,
not the SVG strings.

### Phase 2: Emitter Changes

**File: `scriba/animation/emitter.py`**

- Add `emit_interactive_html_patched()` alongside existing `emit_interactive_html()`
- Or: add `dedup: bool = True` parameter to `emit_interactive_html()`
- Emit `baseSvg` as single template literal
- Emit `patches` as JSON array
- Replace the `frames` JS array with the patch-based player

### Phase 3: Player JS

**In `emitter.py`** (inline JS):

- On init: `stage.innerHTML = baseSvg`
- Cache element references by `data-target` for O(1) lookup
- On frame change: apply patches[i] to cached elements
- Handle annotation add/remove by managing a `<g class="scriba-annotations">` layer

### Phase 4: Fallback

Keep the old full-SVG mode as fallback:
- `--no-dedup` CLI flag
- Substories may need special handling
- If patch computation fails, fall back to full SVG

---

## 4. Data Flow

```
Current:
  scene.py → snapshots → renderer.py → frame SVGs → emitter.py → frames[] JS array

New:
  scene.py → snapshots → renderer.py → frame SVGs → svg_diff.py → (baseSvg, patches[])
                                                   → emitter.py → patched JS player
```

---

## 5. Complexity Estimate

| Component | Effort | Lines (est.) |
|-----------|--------|-------------|
| `svg_diff.py` (diff engine) | Medium | ~150 |
| Emitter changes | Medium | ~100 |
| Player JS rewrite | Medium | ~80 |
| CLI flag + fallback | Small | ~20 |
| Tests | Medium | ~100 |
| **Total** | **Medium-Large** | **~450** |

---

## 6. Risks

- **Annotation SVG generation**: Annotations are currently rendered inline in each
  frame's SVG. The patch system needs to generate annotation SVG snippets
  independently. May need to extract annotation rendering from primitives.
  
- **Substory handling**: Substories have their own frame sequences. Need to
  decide: dedup within substory, or keep substories as full SVG?

- **Print frames**: The `.scriba-print-frames` div (added for @media print)
  currently stores full SVG per frame. Could keep as-is for print, only
  dedup the interactive player.

- **Correctness**: Must verify that patch-based playback produces identical
  visual output to full-SVG mode. Can compare by rendering both and diffing.

---

## 7. Expected Savings

| Scenario | Current | Patched | Savings |
|----------|---------|---------|---------|
| 8 frames, simple array | ~20KB | ~5KB | 75% |
| 12 frames, DP + foreach | ~30KB | ~7KB | 77% |
| 50 frames, graph algo | ~150KB | ~25KB | 83% |
| 100 frames, complex | ~500KB | ~60KB | 88% |

Savings increase with frame count (more frames = more dedup opportunity).
