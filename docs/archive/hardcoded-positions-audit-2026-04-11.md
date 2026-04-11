# Hardcoded Positions Audit — 2026-04-11

**10-agent deep investigation** into hardcoded position/size values across all Scriba primitives.
Root cause of visual overlap, text truncation, and unreadable output.

---

## Root Causes

| # | Root Cause | Severity | Scope |
|---|-----------|----------|-------|
| R1 | **No text measurement** — all primitives use fixed cell/container sizes without measuring actual text content | CRITICAL | All primitives |
| R2 | **`overflow:visible`** in `_render_svg_text()` (base.py:332) — text bleeds outside container without clipping | CRITICAL | All primitives |
| R3 | **BoundingBox inaccurate** — doesn't account for text overflow, node radius, or annotation arrows | HIGH | Multi-primitive layout |
| R4 | **Global CSS `svg text { font: 700 14px... }`** — overrides all text attributes unless inline style is set | MEDIUM | All HTML output |
| R5 | **ForeignObject centering bug** — HashMap entry text `fo_x = x - w//2 = -40` (negative!) bleeds into index column | HIGH | HashMap |

---

## Per-Primitive Findings

### 1. Base Constants + Array

**File:** `primitives/base.py`, `primitives/array.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `CELL_WIDTH` | 60 | Cell width for Array, Queue, Grid, DPTable |
| `CELL_HEIGHT` | 40 | Cell height |
| `CELL_GAP` | 2 | Space between cells |
| `INDEX_LABEL_OFFSET` | 16 | Vertical offset for index labels below cells |

**Issues:**
- Text >6 characters (e.g., "1000000") overflows 60px cell
- `overflow:visible` in `_render_svg_text()` allows text to bleed into adjacent cells
- Index labels use `fo_height=20` — insufficient for long custom labels
- Arrow annotations use undocumented magic numbers (`+12`, `0.75`, `0.5`)
- `bounding_box()` doesn't account for text overflow
- ForeignObject fallback dimensions (80x30) are arbitrary

**Overlap scenarios:**
- Array `data=["1000000", "2000000"]` — text from cell[0] overlaps cell[1]
- Custom labels like `"variable_name_x"` (~110px) overflow `fo_width=60`
- 5+ annotation arrows exceed computed bounding box height

---

### 2. Queue

**File:** `primitives/queue.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_POINTER_HEIGHT` | 20 | Vertical space for pointer arrows above cells |
| `_POINTER_LABEL_GAP` | 14 | Gap between triangle and label text |
| `_POINTER_TRIANGLE_SIZE` | 8 | Half-width of pointer triangle |
| `_DEFAULT_CAPACITY` | 8 | Default queue size |

**Additional magic numbers:**
- `tip_y = cell_y - 2` (line 303) — 2px offset, no rationale
- `label_y = tri_top_y - 6` (line 326) — 6px offset, no rationale
- `nudge = CELL_WIDTH // 3` (line 330) — 20px, insufficient for "front"/"rear" labels

**Issues:**
- Pointer labels overlap when front/rear share a cell — nudge of 20px is insufficient
  - "front" label (~35px wide) extends from x=-7 to x=33, overlapping triangle
  - "rear" label (~25px wide) extends into adjacent cell by ~3px
- Cell values overflow 60px width (uses shared `CELL_WIDTH` from base)
- Capacity=20 creates SVG 1238px wide (exceeds typical viewport)
- Caption positioned only 6px below index labels — collision risk
- No horizontal padding in bounding box for pointer label offsets

**Vertical layout (Y-coordinates):**
```
Y=0-20:     Pointer arrow triangles (_POINTER_HEIGHT=20)
Y=20-34:    Gap for pointer labels (_POINTER_LABEL_GAP=14)
Y=34-74:    Cell rectangles (cell_y = 34, CELL_HEIGHT=40)
Y=74-90:    Index labels (INDEX_LABEL_OFFSET=16)
Y=90-110:   Caption label (optional +20px)
```

---

### 3. LinkedList

**File:** `primitives/linkedlist.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_VALUE_WIDTH` | 50 | Left half of node (value display) |
| `_PTR_WIDTH` | 30 | Right half of node (pointer indicator) |
| `_NODE_WIDTH` | 80 | Total node width (50+30) |
| `_NODE_HEIGHT` | 40 | Node height |
| `_LINK_GAP` | 30 | Horizontal gap between nodes |
| `_PADDING` | 12 | Top/left margin |
| `_INDEX_LABEL_OFFSET` | 16 | Vertical offset for index labels |
| `_CORNER_RADIUS` | 4 | Rectangle corner rounding |
| `_ARROWHEAD_SIZE` | 8 | Arrowhead marker dimensions |

**Issues:**
- Value area only 50px — "1000000" (7 chars, ~50px) barely fits, longer values overflow
- Null indicator uses magic number 4px offset (not parameterized)
- 10+ nodes create SVG 1094px wide (110px per node)
- Arrowhead size=8 doesn't scale with link gap
  - At `_LINK_GAP=10`: arrowhead is 47% of line length (visually jarring)
- `bounding_box()` doesn't fully account for arrow markers and text descent
- Index labels "node[0]", "node[1]" use `font-size=10` — OK for now but not parameterized

**Width formula:**
```
width = 2*12 + n*80 + (n-1)*30 = 110n - 6
  3 nodes: 324px
  5 nodes: 544px
 10 nodes: 1094px
 20 nodes: 2194px
```

---

### 4. HashMap

**File:** `primitives/hashmap.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_INDEX_COL_WIDTH` | 40 | Width of left index column |
| `_ENTRIES_COL_WIDTH` | 200 | Width of right entries column |
| `_ROW_HEIGHT` | 40 | Height of each bucket row |
| `_PADDING` | 4 | Border margin |
| `_TOTAL_WIDTH` | 240 | Computed: 40 + 200 |
| `_INDEX_FONT_SIZE` | "13" | Index text font size |
| `_ENTRIES_FONT_SIZE` | "13" | Entry text font size |

**CRITICAL BUG — ForeignObject centering:**
```python
entry_tx = entries_x + 8  # = 52
fo_width = _ENTRIES_COL_WIDTH - 16  # = 184
# In _render_svg_text():
fo_x = x - w // 2 = 52 - 92 = -40  # NEGATIVE! Extends into index column!
```
- Entry text foreignObject spans x=-40 to x=144
- Index column spans x=4 to x=44
- **Definite overlap at x=4 to x=44** — entry text covers index column

**Other issues:**
- Entry text >23 chars wraps and bleeds into next row (overflow:visible)
- `text_anchor="start"` conflicts with center-aligned foreignObject div
- Capacity=20 creates 808px tall table
- Bounding box doesn't account for wrapped text height

---

### 5. VariableWatch

**File:** `primitives/variablewatch.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_NAME_COL_WIDTH` | 100 | Left column for variable names |
| `_VALUE_COL_WIDTH` | 100 | Right column for values |
| `_ROW_HEIGHT` | 40 | Height per variable row |
| `_PADDING` | 4 | Outer margin |
| `_TOTAL_WIDTH` | 200 | Computed: 100 + 100 |
| `_FONT_SIZE` | "13" | Value text font size |
| `_NAME_FONT_SIZE` | "12" | Name text font size |

**Issues:**
- Variable names >15 chars overflow 100px column
  - "current_minimum_distance" (25 chars) needs ~175px, available: 88px
- Values like "max(arr1) + min(arr2)" (25 chars) overflow 92px
- ForeignObject centering similar to HashMap — extends beyond column boundaries
- Name text at x=12 with fo_width=88 ends at x=100, but column divider at x=104
- Value cell background 4px misaligned from text container
- Bounding box width is 208px but content only spans 204px

---

### 6. CodePanel

**File:** `primitives/codepanel.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_LINE_HEIGHT` | 24 | Vertical spacing between lines |
| `_PADDING_X` | 12 | Horizontal padding |
| `_PADDING_Y` | 8 | Vertical padding |
| `_LINE_NUM_WIDTH` | 30 | Gutter width for line numbers |
| `_CHAR_WIDTH` | 9.6 | Estimated monospace char width at 14px |
| `_FONT_SIZE` | 14 | Code font size |
| `_BORDER_RADIUS` | 6 | Corner rounding |

**Issues:**
- `_CHAR_WIDTH=9.6` is 15-20% wider than actual monospace fonts (typically 8.0-8.5px)
- Line numbers >999 overflow 30px gutter (4 digits: 38.4px > 30px)
- No text clipping for lines exceeding panel width
- Highlighted line background starts at x=1 (magic number)
- Line number font `_FONT_SIZE - 1 = 13px` — 1px difference unexplained
- 100 lines create 2416px tall SVG
- No tab character handling

---

### 7. Graph

**File:** `primitives/graph.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_DEFAULT_WIDTH` | 400 | Fixed viewport width |
| `_DEFAULT_HEIGHT` | 300 | Fixed viewport height |
| `_NODE_RADIUS` | 20 | All node circle radii |
| `_EDGE_STROKE_WIDTH` | 2 | Edge line width |
| `_PADDING` | 20 | Border margin |
| `_DEFAULT_SEED` | 42 | Layout seed |
| `_DEFAULT_ITERATIONS` | 50 | Fruchterman-Reingold iterations |

**Issues:**
- 400x300 viewport fixed regardless of node count
  - 50 nodes: average distance ~55px, but radius=20 requires min 40px — forced overlaps
- Node text container fixed at 40x40px — labels >5 chars overflow circle
- **BoundingBox ignores node radius** — returns `(0, 0, width, height)` but nodes extend 20px beyond
  - Should be `(-20, -20, width+40, height+40)`
- No edge-node collision detection
- Padding is absolute (20px), not relative to viewport

---

### 8. Tree

**File:** `primitives/tree.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_DEFAULT_WIDTH` | 400 | Default viewport width |
| `_DEFAULT_HEIGHT` | 300 | Default viewport height |
| `_NODE_RADIUS` | 20 | All node circle radii |
| `_LAYER_GAP` | 60 | Vertical distance between levels |
| `_MIN_H_GAP` | 50 | Minimum horizontal sibling spacing |
| `_EDGE_STROKE_WIDTH` | 1.5 | Edge line width |
| `_PADDING` | 30 | Border margin |

**Issues:**
- Viewport scales with node count but uses fixed `_MIN_H_GAP` and `_LAYER_GAP`
- **Tree edges don't shorten to circle boundary** (unlike Graph which uses `_shorten_line_to_circle`)
  - Edges pass through node interiors
- BoundingBox ignores node radius (same as Graph)
- Node text container fixed at 40x40px
- Parent centering uses integer rounding — can be off by 1px
- Reingold-Tilford normalization can compress leaves below minimum spacing

---

### 9. Stack

**File:** `primitives/stack.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_CELL_WIDTH` | 80 | Cell width |
| `_CELL_HEIGHT` | 36 | Cell height |
| `_CELL_GAP` | 4 | Space between cells |
| `_PADDING` | 8 | Border padding |
| `_DEFAULT_MAX_VISIBLE` | 10 | Max visible cells before overflow |

**Issues:**
- Text overflow at 80x36 cell size (overflow:visible)
- Max visible=10 is hardcoded, not parameterized
- Label collision when label text is wide

---

### 10. NumberLine

**File:** `primitives/numberline.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `NL_WIDTH` | 400 | Total horizontal width (fixed!) |
| `NL_HEIGHT` | 56 | Total height |
| `NL_PADDING` | 20 | Left/right padding |
| `NL_AXIS_Y` | 20 | Y-position of axis |
| `NL_TICK_TOP` | 12 | Top of tick mark |
| `NL_TICK_BOTTOM` | 28 | Bottom of tick mark |
| `NL_LABEL_Y` | 42 | Y-position of tick labels |

**Issues:**
- **Width completely fixed at 400px** regardless of tick count
- 50 ticks in 400px = 8px spacing, but labels are 40px wide — massive overlap
- Tick labels use `fo_width=40, fo_height=20` — long labels overflow
- No responsive scaling

---

### 11. Matrix

**File:** `primitives/matrix.py`

**Hardcoded constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_DEFAULT_CELL_SIZE` | 24 | Default cell dimensions |
| `_CELL_GAP` | 1 | Space between cells |
| `_LABEL_OFFSET` | 14 | Space for row/col labels |

**Issues:**
- `_LABEL_OFFSET=14` — labels >2 chars overflow into matrix cells
- Column label text rendered in 14px-wide container — "Product_ID" needs ~70px
- Value font `max(8, cell_size//3)` — inconsistent across cell sizes
- Dense matrices (50x50) create 1200x1200px SVG

---

## Scene Layout System

**File:** `emitter.py`

**Constants:**
| Constant | Value | Controls |
|----------|-------|----------|
| `_PADDING` | 16 | Padding on all sides |
| `_PRIMITIVE_GAP` | 50 | Gap between stacked primitives |

**Layout algorithm:** Vertical stacking with `translate(x_offset, y_cursor)`.

**Assessment:** The layout system itself is **correct and deterministic**. The problem is that individual primitives report inaccurate bounding boxes, causing:
1. Primitives to overlap when bounding box is underreported
2. Annotation arrows extending beyond reported bounds
3. Text bleeding across primitive boundaries

**Not supported:** Horizontal layout, grid layout, auto-reflow, collision detection.

---

## Global CSS Conflict

**Location:** HTML template (embedded in each rendered file)

```css
svg text {
  font: 700 14px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  text-anchor: middle;
  dominant-baseline: central;
}
```

**Impact:** Forces bold weight and center alignment on ALL SVG text. Inline styles override this, but any primitive that omits explicit inline styles inherits these defaults. Previous fix (session 2026-04-11) switched `_render_svg_text()` to use inline `style` attributes — this works but is fragile.

---

## Remediation Plan

### Phase 1: Immediate Fixes (stop bleeding)

1. **Change `overflow:visible` to `overflow:hidden`** in `_render_svg_text()` (base.py:332)
   - Prevents text from overlapping adjacent elements
   - Add `text-overflow:ellipsis` for truncation indication

2. **Fix HashMap ForeignObject centering bug**
   - Entry text should use left-aligned positioning, not center-aligned
   - `fo_x = entries_x` instead of `fo_x = x - w // 2`

3. **Fix Graph/Tree bounding box**
   - Include node radius in bounding box calculation
   - `width += 2 * _NODE_RADIUS`, `height += 2 * _NODE_RADIUS`

4. **Fix Tree edge rendering**
   - Shorten edges to circle boundary (like Graph does)

### Phase 2: Dynamic Sizing

5. **Add text width estimation utility**
   ```python
   def estimate_text_width(text: str, font_size: int = 14) -> int:
       avg_char_width = font_size * 0.6  # conservative estimate
       return int(len(str(text)) * avg_char_width)
   ```

6. **Auto-scale cell/column widths** based on content
   - Compute max content width across all cells/values
   - Set minimum width = max(default, estimated_text_width + padding)

7. **Scale node radius** with graph density
   - `radius = max(12, min(20, 400 / (2 * node_count)))`

### Phase 3: Robustness

8. **Add viewport scaling** for primitives exceeding max width
   - Cap total width at configurable max (e.g., 800px)
   - Scale down or wrap when exceeded

9. **Parameterize key constants** via `\shape` params
   - Allow users to override cell_width, column_width, etc.

10. **Add stress test examples** with pathological content
    - Long text, many elements, unicode, multi-line values

---

## Appendix: All Hardcoded Values Summary

```
BASE:        CELL_WIDTH=60, CELL_HEIGHT=40, CELL_GAP=2, INDEX_LABEL_OFFSET=16
ARRAY:       (uses base constants) + magic numbers +12, 0.75, 0.5
QUEUE:       POINTER_HEIGHT=20, POINTER_LABEL_GAP=14, TRIANGLE_SIZE=8
LINKEDLIST:  VALUE_WIDTH=50, PTR_WIDTH=30, NODE_HEIGHT=40, LINK_GAP=30
HASHMAP:     INDEX_COL=40, ENTRIES_COL=200, ROW_HEIGHT=40
VARIABLEWATCH: NAME_COL=100, VALUE_COL=100, ROW_HEIGHT=40
CODEPANEL:   LINE_HEIGHT=24, CHAR_WIDTH=9.6, FONT_SIZE=14, LINE_NUM_WIDTH=30
GRAPH:       WIDTH=400, HEIGHT=300, NODE_RADIUS=20, PADDING=20
TREE:        WIDTH=400, HEIGHT=300, NODE_RADIUS=20, LAYER_GAP=60, MIN_H_GAP=50
STACK:       CELL_WIDTH=80, CELL_HEIGHT=36, CELL_GAP=4, MAX_VISIBLE=10
NUMBERLINE:  NL_WIDTH=400, NL_HEIGHT=56, PADDING=20
MATRIX:      CELL_SIZE=24, CELL_GAP=1, LABEL_OFFSET=14
EMITTER:     PADDING=16, PRIMITIVE_GAP=50
```
