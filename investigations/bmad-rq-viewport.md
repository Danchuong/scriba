# BMAD RQ — Family E: Content-Extent vs Viewport

**Discipline:** bmad-investigate · **Mode:** READ-ONLY source, evidence-graded (path:line + rendered px)
**Scope:** scriba @ `main` · SCRIBA_VERSION = 22 (`scriba/_version.py:6`)
**Verdict:** F1 **CONFIRMED (HIGH)** · F2 **CONFIRMED (HIGH)** · both require a SCRIBA_VERSION bump (22 → 23)

---

## Hand-off Brief

Two viewports silently drop painted content because the box is sized from a formula, never from the content it must contain.

- **F1** — `Plane2D` with `aspect="equal"` (the default) computes plot height purely from the domain ratio: `height = width · yspan/xspan`. For a wide/short domain this collapses below the `2·_PAD` (64px) floor, which **flips the Y transform sign** and paints axis/ticks/points tens of px outside the viewBox; for a tall/narrow domain it produces a **runaway 32024px** viewBox. Line 195 additionally **caps an explicitly requested height** to that tiny value, defeating the only escape hatch.
- **F2** — `_emit_scene_notes` wraps a `\note` to fit the viewBox **width** (and warns E1125 when it can't) but **never checks height**. A multi-line note pill grows unbounded (`ph = 11·lines + 8`) and spills out the **bottom** of the viewBox, cutting the last lines with **no warning**.

Both are content-extent-vs-viewport bugs: fix by bounding the painted extent to the box (F1: clamp the plot box to a legible, non-runaway band + honor explicit height; F2: height-bound the note like width is bounded, and warn).

---

## F1 — Plane2D asymmetric domain collapses the short axis

### CONFIRMED — rendered numbers

Rendered via `render.py`, parsed viewBox vs every painted `x/x1/x2/cx` and `y/y1/y2/cy` (script `scratchpad/bmad-viewport/measure.py`).

| domain (xrange × yrange) | ratio | viewBox W×H | element y-extent | TOP clip | BOTTOM clip | y-coords outside |
|---|---|---|---|---|---|---|
| [0,10]×[0,10] | 1:1 | 344 × **344** | [0 .. 300] | 0 | 0 | 0 / 88 — **CLEAN** |
| [0,20]×[0,1] | 20:1 | 344 × 40 | [−16 .. 32] | **16px** | 0 | 36 / 91 |
| [0,100]×[0,1] | 100:1 | 344 × **27** | [−29 .. 35] | **29px** | **8px** | **220 / 331** |
| [0,1]×[0,100] (inverse) | 1:100 | 344 × **32024** | [0 .. 31980] | 0 | 0 | runaway |
| [0,100]×[0,1] `aspect=auto` | 100:1 | 344 × 344 | [0.5 .. 300] | 0 | 0 | 0 / 327 — **escape hatch works** |

**Threshold sweep** (xrange=[0,r], yrange=[0,1]): clean at **≤10:1** (10:1 → 0px clip), first clip at **15:1 → 11px top**. Matches the reported "clean at ≤10:1".

- **Runaway 32024px** reproduced exactly (report's figure).
- The 100:1 **−29px top** is not incidental: it equals `height(3) − _PAD(32)` — see root cause. (Report cited a larger −81.8..108.8 extent from a denser point set; the *mechanism*, the *runaway*, and the *≤10:1 threshold* all reproduce; my sparser 3-point set yields the smaller but structurally identical clip.)

### Root cause — `scriba/animation/primitives/plane2d.py:191-197`

```python
if self.aspect == "equal":
    computed_h = self.width * (self.yrange[1]-self.yrange[0]) / (self.xrange[1]-self.xrange[0])  # 191-192
    explicit_h = params.get("height")
    if explicit_h is not None:
        self.height = min(int(explicit_h), int(computed_h))   # 195  ← CAPS explicit height
    else:
        self.height = int(computed_h)                          # 197
```
- **Collapse / runaway (192):** `computed_h = 320·1/100 = 3.2 → 3` (100:1); `= 320·100 = 32000` (inverse). No floor, no ceiling.
- **Sign flip (`_compute_transform`, line 245):** `self._sy = -(self.height - 2*_PAD)/yspan`. When `height < 2·_PAD (64)`, `(height−64) < 0` ⇒ **`_sy` goes positive** ⇒ the Y-flip inverts and the interior degenerates. Sign flips for any `xspan/yspan > 5`.
- **Top clip origin (line 247):** `self._ty = (self.height - _PAD) + …`. For `height=3`, `_ty = 3−32 = −29` ⇒ the y=0 axis/origin row is painted at svg_y = −29, i.e. **29px above the viewBox top** — exactly the measured top clip.
- **Escape hatch defeated (195):** `min(explicit_h, computed_h)` ⇒ a user asking `height=300` for a 100:1 plot gets `min(300,3)=3`.

### Fix design — exact edits

1. **New constants** near `plane2d.py:52` (`_PAD = 32`):
   ```python
   _MIN_PLOT_H = 3 * _PAD   # 96 → guarantees interior (height-2*_PAD) >= _PAD, legible & non-inverted
   _MAX_PLOT_H = 1280       # 4 * default width → bounds the tall-domain runaway
   ```
2. **Replace `plane2d.py:191-197`** — clamp the auto height into the legible band; **honor** explicit height verbatim (drop the `min()` cap):
   ```python
   if self.aspect == "equal":
       explicit_h = params.get("height")
       if explicit_h is not None:
           self.height = int(explicit_h)                    # honor the user's escape hatch
       else:
           computed_h = self.width * (self.yrange[1]-self.yrange[0]) / (self.xrange[1]-self.xrange[0])
           self.height = int(min(max(computed_h, _MIN_PLOT_H), _MAX_PLOT_H))
   ```
   `bounding_box()` (line 1212-1219) and the stage viewBox both derive from `self.height`, so this one clamp fixes the transform, the plot box, **and** the viewBox — no second edit site.
   - *Tuning note for the implementer:* `_MIN_PLOT_H` picks the byte-vs-legibility boundary. `96` (recommended) is legibility-first per the "must stay readable" requirement and changes any plot with `xspan/yspan > 3.33`. `65 (=2·_PAD+1)` is the byte-minimal correctness-only floor (fixes only sign-inverted plots, `>5:1`). Either leaves 1:1 untouched.
   - *Optional defense-in-depth:* also grow `bounding_box` to the painted extent, but the clamp is the primary fix — a 3px plot is unreadable regardless of viewBox.

### RED tests (all FAIL now; byte-guard PASSES)
`scratchpad/bmad-viewport/test_red_viewport.py` — run + observed:
- `test_f1_asymmetric_domain_transform_not_inverted` — **FAIL**: `interior 3−64 = −61`, `_sy = +61`.
- `test_f1_no_element_painted_outside_plot_box` — **FAIL**: `element painted 29.0px above plot-box top`.
- `test_f1_inverse_domain_height_not_runaway` — **FAIL**: `runaway height=32000` (asserts ≤ 4·width).
- `test_f1_explicit_height_is_honored_not_capped` — **FAIL**: `explicit height capped to 3` (asked 300).
- `test_f1_symmetric_baseline_height_unchanged` — **PASS** (byte guard: 1:1 height stays 320).

### Impact / byte verdict
- `bounding_box`/`_compute_transform`/`emit_svg` all read `self.height`; clamping it is the single lever (no call-graph fan-out).
- **1:1 (and every `≤ ~3.3:1`) plot: byte-IDENTICAL** — `computed_h ∈ [_MIN_PLOT_H, _MAX_PLOT_H]`, unclamped (1:1 → 320). Hard requirement met.
- Bytes change **only** for degenerate/runaway plots (`xspan/yspan > 3.33` or tall) — **all currently broken** (inverted axis, clip, or 32000px). Correctness fix ⇒ **SCRIBA_VERSION 22 → 23**.
- Existing `test_aspect_equal_computes_height` (width=200, 2:1 → 100) stays green (100 ∈ band).

**Confidence: HIGH** — mechanism traced to exact lines, top-clip magnitude derived to the pixel (`height−_PAD`), runaway reproduced exactly, escape hatch and threshold both reproduced.

---

## F2 — Multi-line `\note` clips at the viewBox bottom (silent)

### CONFIRMED — rendered numbers

3-cell `Array` (viewBox **208 × 64**), one `\note{…, at=bottom}`:

| note text | wrapped lines | pill height `ph` | pill bottom (py+ph) | viewBox vh | BOTTOM clip | lines cut | warning? |
|---|---|---|---|---|---|---|---|
| 1 line ("0-indexed") | 1 | 19 | 64.0 | 64 | 0 | 0 | — (fits) |
| ~2 sentences | 8 | **96** | **96.0** | 64 | **32px** | 3 (y=64.5/75.5/86.5) | **none — SILENT** |
| ~4 sentences | 11 | **129** | 129.0 | 64 | **65px** | 6 | **none — SILENT** |

`render.py … 2>&1 | grep -i warn` → **"NO warnings on stderr"**. Bottom lines are cut with zero diagnostic. (Report cited 7-line/85px/21px; the 8-line/96px/32px case is the same mechanism at a slightly denser wrap.)

### Root cause — `scriba/animation/_frame_renderer.py`, `_emit_scene_notes` (1410-1552)

- **Width IS bounded + warned:** `board_avail = vw − 2·_NOTE_MARGIN` (1450); `wrap_px = min(board_avail, 132)` (1451); wrap at 1465-1478; **E1125 warn + clamp** when `pw > board_avail` (1488-1494).
- **Height is NEVER bounded:** `ph = LABEL_FONT_PX * len(lines) + 8` (**line 1479**) grows with line count, unchecked. `vh` is used only to *position* the pill — `_note_anchor_xy` (1404/1406/1483) and `_place_pill(viewbox_h=vy+vh)` (1508) — which pins the pill's top-left inside the box but **cannot shrink a pill taller than the box**, so the overflow spills out the bottom. There is **no `ph`-vs-`vh` comparison and no warning** anywhere in the function (`grep "ph.*vh"` → only the two positioning lines).
- Constants: `_NOTE_MARGIN = 8.0` (1373), `LABEL_FONT_PX = 11`, `_LABEL_PILL_MAX_W_PX = 132` (`_svg_helpers.py:97,126`).

### Fix design — exact edits (recommend: height-bound + warn, symmetric with width)

Right after `ph` is computed (**after line 1479**), mirror the width path:
```python
board_avail_h = max(1.0, vh - 2.0 * _NOTE_MARGIN)
max_lines = max(1, int((board_avail_h - 8) // LABEL_FONT_PX))
if len(lines) > max_lines:
    lines = lines[:max_lines - 1] + [lines[max_lines - 1].rstrip() + "…"]  # ellipsis last kept line
    ph = float(LABEL_FONT_PX * len(lines) + 8)
    warnings.warn(
        f"[E1126] \\note {nid!r} text is taller than the board; "
        f"truncated/clamped into the viewBox", stacklevel=2)
```
Then the existing anchor/scorer flow keeps the (now-fitting) pill on-board. This makes the loss **visible** (warned) instead of silent, and is consistent with the already-shipped width contract.

- **Rejected alternative — grow the viewBox to contain the note:** the viewBox is **board-level and byte-locked** — `_zoom_viewbox` (1555+) and the link/stage layout all `.split()` and depend on it (1439). Growing it for a *decoration overlay* would ripple bytes across every co-rendered shape and break the "note is a free margin callout" invariant. Height-bound+warn is the minimal, local, consistent fix. (If product wants a dedicated note lane, that is a separate layout RFC.)

### RED test (FAILS now)
`test_f2_multiline_note_pill_within_viewbox` — **FAIL**: `note pill bottom 96.0 exceeds viewBox bottom 64.0 by 32.0px`. Asserts `py + ph <= vy + vh`.

### Impact / byte verdict
- The new branch fires **only** when `len(lines) > max_lines` — i.e. exactly the notes that currently overflow/clip.
- **Short/fitting notes: byte-IDENTICAL** — verified: a 1-line note pill bottom = 64 = vh takes the unchanged path (no-op). Growing/clamping never touches a note that already fits.
- Bytes change **only** for previously-clipped notes ⇒ **SCRIBA_VERSION 22 → 23** (shared bump with F1).

**Confidence: HIGH** — width-checked/height-unchecked asymmetry located to the exact lines, silent clip reproduced with stderr proof, no-op on fitting notes verified.

---

## Combined verdict
- **F1 CONFIRMED**, **F2 CONFIRMED** — both HIGH, both silent content loss.
- **Byte-stability:** neither fix moves bytes for the healthy baseline (F1 1:1 plots; F2 short notes). Both move bytes only for already-broken inputs.
- **SCRIBA_VERSION:** currently 22 → **must bump to 23** (rendered-output change for the affected inputs). Neither fix is a pure refactor.

*Artifacts:* `scratchpad/bmad-viewport/` — `f1_*.tex`, `f2_*.tex`, `measure.py`, `test_red_viewport.py`. Repo left clean (`_*.html` I generated removed).
