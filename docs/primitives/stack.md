# Primitive Spec: `Stack`

> Status: **draft — Pivot #2 extension**. Extends base spec `04-environments-spec.md` §5
> (primitive catalog). Error codes in range **E1440–E1449**.

---

## 1. Purpose

`Stack` renders a monotonic deque, hull stack, call stack, or any last-in-first-out
structure as a horizontal or vertical sequence of labeled cells. It unlocks:

- **HARD-TO-DISPLAY #6** (Convex Hull Trick / Li Chao Tree): the deque of active lines at
  each iteration, with lines entering from the back and dominated lines popping from the
  front or back. Authors use `push` and `pop` apply commands to build up the deque
  step-by-step in an `\begin{animation}` filmstrip.
- General monotonic stack editorials (next greater element, largest rectangle in
  histogram, online median).
- Call stack visualization for recursive algorithm editorials.
- Parenthesis matching, balanced bracket, and stack-based parsing demonstrations.

`Stack` is a structural complement to `Array` (which is a fixed-length indexed sequence).
`Stack` is variable-length, grows/shrinks via push/pop, and carries a concept of "top".

---

## 2. Shape declaration

```latex
\shape{s}{Stack}{
  orientation="vertical",
  max_visible=10,
  items=[]
}
```

### 2.1 Required parameters

None. All parameters have defaults. A bare `\shape{s}{Stack}{}` is valid and produces an
empty vertical stack.

### 2.2 Optional parameters

| Parameter      | Type                         | Default       | Description                                                   |
|----------------|------------------------------|---------------|---------------------------------------------------------------|
| `orientation`  | `"vertical"` \| `"horizontal"` | `"vertical"` | Axis along which items stack. See §9 for visual conventions.  |
| `max_visible`  | positive integer             | 10            | Maximum items shown before overflow collapse. See §7.         |
| `items`        | list of item specs           | `[]`          | Initial contents. Each item spec is defined in §2.3.          |
| `label`        | string                       | none          | Optional caption rendered below the stack.                    |

> **Dimensions are automatic.** `cell_width`, `cell_height`, and `gap` are
> **not** accepted parameters; cell geometry is recomputed from the current
> item labels on every push/pop so the shape always fits its contents. Any
> extra keys passed to the constructor are benignly ignored (§5.2 of the
> ruleset spec formerly listed these as options; that entry has been fixed
> for v0.5.1).

**Hard cap:** 1000 items total (across all push operations in the animation lifetime).
Exceeding this is **E1440** (push-beyond-capacity, error).

### 2.3 Item specification

Each element in the `items` list (and each item created via `push`) is a dict-like spec:

```
{label="<string>", value=<float|int|None>}
```

| Field    | Type              | Required | Description                                                  |
|----------|-------------------|----------|--------------------------------------------------------------|
| `label`  | string            | yes      | Display text. May include inline LaTeX (`$...$`), which is
                                              rendered via `ctx.render_inline_tex`. Passed verbatim to the
                                              SVG emitter; KaTeX output is placed inside a `<foreignObject>`. |
| `value`  | float, int, None  | no       | Numeric value shown in a secondary badge below the label.    |

A bare string is also accepted as shorthand for `{label="...", value=None}`.

Example:

```latex
\shape{s}{Stack}{
  items=[{label="$y = 2x+1$", value=1.0},
         {label="$y = x+3$",  value=3.0}]
}
```

---

## 3. Addressable parts (selectors)

| Selector            | Addresses                                                                |
|---------------------|--------------------------------------------------------------------------|
| `s`                 | The entire stack (whole-shape target)                                    |
| `s.top`             | The topmost item (most recently pushed). Alias for `s.item[-1]`.         |
| `s.bottom`          | The bottommost item. Alias for `s.item[0]`.                              |
| `s.item[i]`         | Item at 0-based index from bottom. `i=0` is the oldest item.            |
| `s.item[-1]`        | Top item (alias). Negative indices count from the top.                   |
| `s.range[lo:hi]`    | Items from index `lo` to `hi`, **inclusive on both ends** (matches base spec §4.2 inclusive-range convention). |
| `s.all`             | Every item currently in the stack.                                       |

Index semantics: the "bottom" is index 0; the "top" is index `size-1`. Negative indices
wrap from the top: `item[-1]` = top, `item[-2]` = second from top.

Out-of-range index after all push/pop operations for the frame is **E1443**
(item-out-of-range). Empty-stack access (top/bottom on an empty stack) is also E1443.

> **Note (audit 3.3):** the earlier draft used Python-style exclusive-hi slice semantics
> (`lo:hi-1`). This has been corrected to **inclusive** range `[lo, hi]` to match the
> base spec §4.2 convention used by `DPTable` and `Matrix`.

---

## 4. Apply commands

### 4.1 Push

```latex
\apply{s}{push={label="$y=2x+1$", value=2.0}}
```

Appends a new item to the top of the stack. The item spec follows §2.3. If the stack
size after push exceeds the 1000-item hard cap, emit **E1440** and ignore the push.

A bare string shorthand is accepted:

```latex
\apply{s}{push="$y=2x+1$"}
```

The SVG emitter adds an animation hint class `scriba-stack-enter` to the new item's `<g>`
element. The animation is driven by the `slide-in-vertical` preset (when
`orientation="vertical"`) or `slide-in-horizontal` preset (when `orientation="horizontal"`)
defined in `extensions/keyframe-animation.md`. These are two of the 7 canonical keyframe
presets (`rotate`, `orbit`, `pulse`, `trail`, `fade-loop`, `slide-in-vertical`,
`slide-in-horizontal`). No `@keyframes` block is emitted inline into the SVG — the
animations ship via `required_css` (see §9). Reduced-motion override: the slide-in
animation is suppressed when `@media (prefers-reduced-motion: reduce)` is active; the
item appears instantly.

### 4.2 Pop

```latex
\apply{s}{pop=1}
```

Removes the top `N` items (default 1). If `pop` would remove more items than the current
size, emit **E1442** (pop-from-empty, error) and remove only as many as exist.

```latex
\apply{s}{pop=3}   % pop the top 3 items
```

### 4.3 Mutate an existing item

```latex
\apply{s.item[i]}{label="new text", value=3.2}
```

Changes the label or value of item at index i in place. Does not affect the item's
position in the stack.

Accepted parameters on individual item apply:

| Parameter | Type    | Description                                   |
|-----------|---------|-----------------------------------------------|
| `label`   | string  | New display text. LaTeX inline supported.      |
| `value`   | float   | Update the numeric badge value.               |
| `tooltip` | string  | Rendered into `data-tooltip` attribute.       |

### 4.4 Persistent vs. ephemeral

All push/pop operations are **persistent** — they carry forward to later frames per base
spec §3.5 semantics. Pushing item X in frame 3 means X is visible in frames 4, 5, ... until
explicitly popped.

---

## 5. Semantic states

Standard §9.2 state classes from base spec are applied to individual items' `<g>` elements:

```latex
\recolor{s.top}{state=current}       % highlight the top item persistently
\highlight{s.item[2]}                % ephemeral yellow border on item 2
\recolor{s.range[0:3]}{state=dim}    % dim the bottom 3 items
```

State is communicated via the `scriba-state-*` classes on `.scriba-stack-item`:

| State       | Visual effect                                          |
|-------------|--------------------------------------------------------|
| `idle`      | Default fill `var(--scriba-bg-code)`, border `var(--scriba-border)` |
| `current`   | Fill #0072B2 (Wong blue), white text                   |
| `done`      | Fill #009E73 (Wong green), white text                  |
| `dim`       | Opacity 0.35                                           |
| `error`     | Fill #D55E00 (Wong vermillion), white text             |
| `good`      | Fill #009E73 alt tone                                  |
| `highlight` | Gold border #F0E442, 3px dashed (ephemeral)            |

For `Matrix`, state was communicated via stroke-only to preserve colorscale. For `Stack`,
fill IS overridden because there is no colorscale — `Stack` cells use semantic fill as
their primary state signal.

---

## 6. Visual conventions

### 6.1 Vertical stack (`orientation="vertical"`)

The stack grows **upward**: the bottom item (index 0) is at the lowest Y position in SVG
space; the top item (index size-1) is at the highest Y in author-space but lowest SVG Y
(because SVG Y increases downward). The "top" is visually at the top of the rendered image.

Concretely in SVG coordinates (Y increases downward, origin top-left):

```
item[size-1] (top)   → y = pad_top
item[size-2]         → y = pad_top + (cell_height + gap)
...
item[0] (bottom)     → y = pad_top + (size-1) * (cell_height + gap)
```

A "PUSH" label or arrow is rendered above the top cell (optional, if `show_labels=true`).

### 6.2 Horizontal stack (`orientation="horizontal"`)

The stack grows **rightward**: index 0 is at the leftmost x; index size-1 (top) is at the
rightmost x. This matches the deque visual used in Li Chao tree editorials where lines are
added to the right end and dominated lines are removed from either end.

```
item[0] (bottom)     → x = pad_left
item[1]              → x = pad_left + (cell_width + gap)
...
item[size-1] (top)   → x = pad_left + (size-1) * (cell_width + gap)
```

### 6.3 Item cell layout

Each item cell is a `<g class="scriba-stack-item" data-index="{i}">` containing:

```
+--------------------------+
|    label text            |  <- <text> centered in cell
|  [ value badge ]         |  <- <text> smaller, below center (omitted if value is None)
+--------------------------+
```

The badge is a separate `<text class="scriba-stack-badge">` at font-size 10px. If `value`
is None, the badge element is omitted from the SVG.

---

## 7. Overflow collapse (`max_visible`)

When the stack contains more than `max_visible` items, the middle section collapses to an
ellipsis row:

```
[item[size-1]]  (top)
[item[size-2]]
...
[item[size - max_visible//2]]
[ ··· N hidden ··· ]         <- <g class="scriba-stack-overflow"> with count badge
[item[max_visible//2 - 1]]
...
[item[0]]  (bottom)
```

The collapse rule: show the top `max_visible // 2` items and the bottom `max_visible // 2`
items; collapse everything in between into a single row with the hidden count. If
`max_visible` is odd, the extra slot goes to the top half.

`\apply`, `\recolor`, `\highlight`, and `\annotate` selectors still work on hidden items
(the commands are applied to the internal state; the overflow placeholder just hides them
visually). **E1441** (overflow-visible, warning) is emitted when overflow is first
triggered, with the hidden count.

---

## 8. Inline LaTeX in labels

When a label string contains `$...$`, the emitter invokes `ctx.render_inline_tex` to
produce KaTeX HTML, then embeds it using `<foreignObject>` inside the cell:

```html
<foreignObject x="{x}" y="{y}" width="{w}" height="{h}">
  <span xmlns="http://www.w3.org/1999/xhtml"
        class="scriba-stack-label-math">
    <!-- KaTeX HTML output -->
  </span>
</foreignObject>
```

Plain-text labels are rendered as `<text>` directly (no `foreignObject`). The emitter
detects `$` characters to choose the path. Mixed content (e.g. `"slope $m=2$"`) routes
the entire label through `render_inline_tex`.

---

## 9. HTML output contract

### 9.1 SVG root

All custom data attributes on Stack SVG elements use the `data-scriba-<kebab-case-name>`
convention (audit finding 4.10). No inline `<style>` is emitted inside the SVG — all CSS
ships via `required_css`.

**`required_css`**: `["scriba/animation/static/scriba-stack.css"]`

The stylesheet provides `.scriba-stack-cell`, `.scriba-stack-enter` animation rules
(including `slide-in-vertical` and `slide-in-horizontal` keyframes), reduced-motion
overrides, and `.scriba-state-*` fill rules. Consumer includes it via
`<link rel="stylesheet">` before rendering animation frames.

**Supported §9.2 state classes**: `focus`, `update`, `path`, `reject`, `accept`, `hint`,
`current`, `done`, `dim`, `error`, `good`, `highlight` (applied as fill override — Stack
cells use semantic fill as primary state signal, no colorscale to preserve).

> **Determinism.** Given identical `\shape` parameters and identical `\apply` command
> sequence, the Stack emitter produces byte-identical SVG output across runs.

```html
<svg class="scriba-stack"
     data-scriba-orientation="vertical"
     data-scriba-size="{current size}"
     viewBox="0 0 {W} {H}"
     xmlns="http://www.w3.org/2000/svg"
     role="img">
  <g class="scriba-stack-items">
    <g class="scriba-stack-item scriba-state-idle"
       data-target="s.item[0]"
       data-scriba-index="0">
      <rect class="scriba-stack-cell"
            x="{x}" y="{y}" width="{cell_width}" height="{cell_height}"
            rx="3"/>
      <text class="scriba-stack-label"
            x="{cx}" y="{cy}"
            text-anchor="middle"
            dominant-baseline="central">{label}</text>
      <!-- badge, present only if value is not None: -->
      <text class="scriba-stack-badge"
            x="{cx}" y="{cy + 10}"
            text-anchor="middle">{value}</text>
    </g>
    <!-- ... remaining items ... -->
    <!-- overflow placeholder (when size > max_visible): -->
    <g class="scriba-stack-overflow" data-scriba-hidden-count="{N}">
      <rect .../>
      <text>··· {N} hidden ···</text>
    </g>
  </g>
</svg>
```

> **Breaking change note (audit 4.10):** `data-orientation` → `data-scriba-orientation`,
> `data-size` → `data-scriba-size`, `data-index` → `data-scriba-index`,
> `data-hidden-count` → `data-scriba-hidden-count`.

### 9.2 ViewBox dimensions

For `orientation="vertical"`:

```
W = pad_left + cell_width + pad_right   (default: 8 + 80 + 8 = 96)
visible = min(size, max_visible)
H = pad_top + visible * cell_height + (visible - 1) * gap + pad_bottom
```

For `orientation="horizontal"`:

```
H = pad_top + cell_height + pad_bottom   (default: 8 + 36 + 8 = 52)
visible = min(size, max_visible)
W = pad_left + visible * cell_width + (visible - 1) * gap + pad_right
```

An empty stack (size=0) produces a minimal SVG with `viewBox="0 0 96 52"` showing an empty
container placeholder with a dashed border labeled `(empty)`.

---

## 10. CSS `@keyframes` animations

Stack push animations use two keyframe presets from the canonical 7-preset vocabulary
defined in `extensions/keyframe-animation.md` §2. The presets are part of the Scriba
animation CSS shipped via `required_css`; they are **not** re-defined or inlined here.

| Orientation        | Preset used            | CSS class on new item   |
|--------------------|------------------------|-------------------------|
| `"vertical"`       | `slide-in-vertical`    | `scriba-stack-enter`    |
| `"horizontal"`     | `slide-in-horizontal`  | `scriba-stack-enter`    |

The full `@keyframes` definitions, duration (`200ms`), easing (`ease-out`), and
`@media (prefers-reduced-motion)` guard are specified in `extensions/keyframe-animation.md`
and live in `scriba/animation/static/scriba-stack.css`. Do NOT re-define them here.

The `.scriba-stack-enter` class is added to a newly pushed item's `<g>` element and
is absent in subsequent frames (static filmstrip). On a cache-hit rebuild the class
placement is identical — output is deterministic.

> **Audit fix C1 (decision lock #2):** the previous draft defined `@keyframes` inline
> and named presets not present in the keyframe-animation vocabulary. Both `slide-in-vertical`
> and `slide-in-horizontal` are now canonical presets in `extensions/keyframe-animation.md`.
> Stack must not invent alternative keyframe names.

---

## 11. Error code catalog (E1440–E1449)

| Code  | Severity | Condition                                               | Hint                                                        |
|-------|----------|---------------------------------------------------------|-------------------------------------------------------------|
| E1440 | Error    | Push would exceed 1000-item hard cap                    | The stack has reached the maximum size. Split the editorial into sub-animations. |
| E1441 | Warning  | Stack size exceeds `max_visible`; overflow collapse active | Increase `max_visible` or accept the collapsed view.      |
| E1442 | Error    | `pop` on empty stack (or pop count > current size)      | Check algorithm logic; emit a guard step before popping.   |
| E1443 | Error    | Item index out of range (after all push/pop for this frame) | Index must be in `[-size, size-1]`.                     |

Codes E1444–E1449 are reserved for future Stack extensions.

---

## 12. Acceptance tests

### 12.1 Monotonic deque for Li Chao / Convex Hull Trick (HARD-TO-DISPLAY #6)

```latex
\begin{animation}[id=li-chao-deque]
\compute{
  lines = [
    {label: "$y = 2x+1$",   value: 1.0},
    {label: "$y = x+3$",    value: 3.0},
    {label: "$y = -x+5$",   value: 5.0},
    {label: "$y = 0.5x+4$", value: 4.0}
  ]
}
\shape{dq}{Stack}{
  orientation="horizontal",
  max_visible=8,
  items=[]
}

\step
\apply{dq}{push={label="$y=2x+1$", value=1.0}}
\narrate{Add line $y=2x+1$ to the deque. It is the only line; no dominated lines.}

\step
\apply{dq}{push={label="$y=x+3$", value=3.0}}
\recolor{dq.top}{state=current}
\narrate{Add $y=x+3$. Check if the previous line is dominated for all future queries.}

\step
\apply{dq}{pop=1}
\apply{dq}{push={label="$y=-x+5$", value=5.0}}
\narrate{$y=x+3$ is dominated; pop it. Add $y=-x+5$.}

\step
\apply{dq}{push={label="$y=0.5x+4$", value=4.0}}
\recolor{dq.top}{state=current}
\narrate{Add $y=0.5x+4$. The lower envelope now has 3 lines.}
\end{animation}
```

Expected:
- Frame 1: horizontal stack with 1 cell `[$y=2x+1$ | 1.0]`.
- Frame 2: 2 cells; rightmost has `scriba-state-current`.
- Frame 3: pop right, push `$y=-x+5$`; stack has 2 cells.
- Frame 4: 3 cells; rightmost `scriba-state-current`.
- `slide-in-horizontal` CSS present on each push frame.
- No E144x errors.

### 12.2 Parenthesis matching

```latex
\begin{animation}[id=paren-match]
\shape{stk}{Stack}{orientation="vertical", max_visible=6}

\step
\apply{stk}{push="("}
\narrate{Open paren: push.}

\step
\apply{stk}{push="("}
\narrate{Second open paren: push.}

\step
\apply{stk}{push=")"}
\narrate{Close paren: this is not pushed — instead we match and pop.}

\step
\apply{stk}{pop=1}
\recolor{stk.top}{state=done}
\narrate{Matched. Stack now has one open paren.}
\end{animation}
```

Expected:
- E1442 NOT raised (no empty-pop attempt).
- `scriba-state-done` on remaining item in frame 4.

---

## 13. Base-spec deltas

**§3.1 primitive type registration**: add `Stack` to the primitive type list in
`04-environments-spec.md` §3.1. Agent 4 will merge.

**§4.1 BNF — negative index extension** (audit finding 2.1, decision lock applied):

`s.item[-1]` and `s.item[-2]` use negative indices. Base spec §4.1 BNF defines:

```
index ::= NUMBER | INTERP
```

where `NUMBER` is unsigned. Negative indexing is a base-spec grammar extension. Agent 4
must extend the `index` production to:

```
index ::= ('-')? NUMBER | INTERP
```

This delta applies only to primitives that define negative-index semantics (`Stack` is the
only one in Pivot #2). Error code **E1443** (item-out-of-range) covers out-of-range
negative indices.

**§4.2 per-primitive selector examples table**: add `Stack` row:

| Primitive | Whole shape | Addressable parts                                                   |
|-----------|-------------|---------------------------------------------------------------------|
| `Stack`   | `s`         | `s.top`, `s.bottom`, `s.item[0]`, `s.item[-1]`, `s.range[0:3]`, `s.all` |

**§4.2 selector range semantics note**: `s.range[lo:hi]` is **inclusive** on both ends
(matching `DPTable` and `Matrix` conventions). This overrides any Python-slice reading.
