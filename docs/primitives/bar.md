# Primitive Spec: `Bar`

> Status: **draft**. Extends the base primitive catalog. Error codes in range
> **E1488–E1490**.

---

## 1. Purpose

`Bar` renders a histogram — a row of columns over an integer index axis whose
**pixel heights are proportional to their values**, sharing a common baseline.
It is the "height = value" channel the catalog was missing: `MetricPlot` draws a
cumulative polyline, and the cell primitives (`Array`, `Grid`) show text or crude
brick towers, neither of which reads as a magnitude.

It unlocks the histogram family of editorials:

- **Largest rectangle in a histogram** and **monotonic stack on heights** (pair it
  with `Stack` for the deque of indices).
- **Trapping rain water**, **skyline**, **sorting as bars**, **convolving/booth
  distributions** — anything where the *shape of the heights* is the point.

---

## 2. Shape declaration

```latex
\shape{h}{Bar}{data=[3,1,4,1,5,9,2], max=9, show_values=true, label="heights"}
```

### 2.1 Parameters

| Param | Type | Default | Meaning |
|-------|------|---------|---------|
| `data` | list of numbers | *(required)* | Column values, left to right. |
| `max` | number | `max(data)` | Full-scale ceiling — a column of this value fills the plot. A `max` below the data is grown so nothing clips. |
| `label` | string | — | Caption below the plot. |
| `bar_width` (alias `width`) | int | 36 | Per-column width in px. |
| `show_values` | bool | `false` | Print each value above its column. |

Empty / missing `data` → **E1488**; a non-list `data` (string or scalar) →
**E1489**; a non-numeric element → **E1490**.

---

## 3. Selectors

| Selector | Addresses |
|----------|-----------|
| `h` | the whole primitive |
| `h.bar[i]` | column *i* (0-based) — recolor / highlight / annotate |
| `h.all` | every column |

An out-of-range `h.bar[i]` **soft-drops** (warns `E1115`, no output change),
matching every other primitive's selector contract.

---

## 4. Operations

```latex
\recolor{h.bar[5]}{state=current}   % state-color a column
\apply{h.bar[0]}{value=9}           % change a column's height
```

A column's height is a pure function of its stored value, recomputed each frame.
`\apply{h.bar[i]}{value=X}` therefore rides the existing **`value_change`**
transition — no bespoke motion kind. The runtime stamps the destination frame's
SVG, so the column **snaps** to its new height and its value label pulses (the
same behaviour as an `Array` cell value change).

---

## 5. Envelope invariant (R-32)

The bounding box is a pure function of the **column count** and the layout
constants — never of the values — so the stage viewBox is identical in every
frame. The scaling ceiling (`_envelope_max`) only ever grows, so the
value-prescan lifts it to the timeline maximum before the first frame renders: a
value pushed above `max` mid-animation is honoured (the tallest column fills the
plot and the rest rescale), never clipped, and the envelope still does not move.

---

## 6. Rendering

Each column is `<g data-target="h.bar[i]" data-primitive="bar" class="scriba-state-…">`
wrapping a direct-child `<rect>` (filled by the CSS state class, so `\recolor`
swaps the class at runtime). The baseline is a `<line>` under the columns; index
labels sit below the baseline and value labels (when `show_values`) above each
column, both outside the addressable group.
