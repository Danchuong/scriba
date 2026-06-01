# Scriba TeX Reference — Phase 0 Ground Truth (2026-06-01)

Authoritative fact sheet extracted by reading `scriba/animation/` source. Every
row below is backed by a `file:line` citation. The later integrator should paste
from here; do **not** trust the current doc where it conflicts.

Source roots:
- Primitives: `scriba/animation/primitives/*.py`
- Commands / state validation: `scriba/animation/parser/_grammar_commands.py`, `_grammar_tokens.py`
- Apply/recolor resolution: `scriba/animation/scene.py`
- Errors: `scriba/animation/errors.py`
- States/colors: `scriba/animation/constants.py`, `scriba/animation/primitives/_types.py`

General mechanics (apply to ALL primitives):
- `ACCEPTED_PARAMS` is enforced at construction by `PrimitiveBase._validate_accepted_params` (`base.py:224`); any key NOT in the set raises **E1114** with a fuzzy "did you mean" hint. An empty set means no checking, but **all 15 primitives below declare a non-empty set**, so every param the doc lists must appear in `ACCEPTED_PARAMS` or it is invalid.
- Selector validity is checked by `validate_selector`; an unknown selector on `set_state/set_value/set_label` is a **silent drop with an E1115 warning** (`base.py:256-272`), not an error.

---

## A. Per-primitive param tables (all 15)

### 1. Array — `array.py:81-166`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `size` | int | — | one of size/n/values | 1..10000 | cell count (`array.py:111,121-133`) |
| `n` | int | — | alias for size | 1..10000 | alias of `size` |
| `values` | list | — | alias | any list | supplies BOTH size (=len) and data in one param (`array.py:104-114,136-137`) |
| `data` | list | `[""]*size` | no | len must == size | initial cell contents; E1402 if len mismatch (`array.py:135-146`) |
| `labels` | str | None | no | `"0..6"` or `"dp[0]..dp[6]"` format string only | index-label row under cells (`array.py:152`, parser `array.py:454-471`) |
| `label` | str | None | no | any | caption below the array (`array.py:153`) |

- Errors: E1400 (missing size/n/values), E1401 (size out of range), E1402 (data length).
- Operations (`apply_command`): **NONE** — Array has no `apply_command` override; it is immutable post-construction. (No mutation method in `array.py`.)
- Selectors (`SELECTOR_PATTERNS`, `array.py:91-95`): `cell[{i}]`, `range[{lo}:{hi}]`, `all`.
- Doc-omission flags: `values` alias often undocumented. `labels` is a **format string**, NOT a list (see §B).

### 2. Grid — `grid.py:94-157`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `rows` | int | — | yes | 1..500 | row count (`grid.py:118,130-148`) |
| `cols` | int | — | yes | 1..500 | col count |
| `data` | flat or 2D list | `[""]*r*c` | no | len==r*c (flat) or 2D r×c | E1412 on mismatch (`grid.py:38-74,151-152`) |
| `label` | str | None | no | any | caption |

- Errors: E1410 (missing rows/cols), E1411 (out of range), E1412 (data length).
- Operations: **NONE** (no `apply_command`).
- Selectors (`grid.py:104-107`): `cell[{r}][{c}]`, `all`.

### 3. DPTable — `dptable.py:76-180`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `n` | int | — | n OR (rows+cols) | positive int | 1D mode size (`dptable.py:104-121`) |
| `rows` | int | — | with cols → 2D | positive int | 2D rows (`dptable.py:122-142`) |
| `cols` | int | — | with rows → 2D | positive int | 2D cols |
| `data` | list | `[""]*n` | no | len == n (1D) or rows*cols (2D) | E1429 on mismatch (`dptable.py:162-171`) |
| `labels` | str | None | no | same format string as Array | index labels (1D only) (`dptable.py:179`) |
| `label` | str | None | no | any | caption |

- Cell cap: rows*cols ≤ 250000 → else E1425 (`dptable.py:151-160`).
- Errors: E1426 (missing n/rows+cols), E1427 (n range), E1428 (rows/cols range), E1425 (cap), E1429 (data length).
- Operations: **NONE** (no `apply_command`). Values are set via `\apply{t.cell[i]}{value=...}` through the base value layer, not a custom op.
- Selectors (`dptable.py:86-91`): `cell[{i}]` (1D), `cell[{r}][{c}]` (2D), `range[{lo}:{hi}]` (1D), `all`.

### 4. Graph — `graph.py:551-596`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `nodes` | list | — | yes (non-empty) | ≤ 100 nodes | node ids (str or int, kept as-is) (`graph.py:601-622`) |
| `edges` | list | `[]` | no | (u,v) or (u,v,w) tuples; no mixing | E1474 on bad shape/mix (`graph.py:623-644`) |
| `directed` | bool | False | no | bool | arrowheads (`graph.py:645`) |
| `layout` | str | `"force"` | no | `force`, `stable`, `hierarchical`, `auto` | layout engine (`graph.py:646`, dispatch 743-824) |
| `layout_seed` | int | 42 | no | non-negative int | deterministic seed (canonical) (`graph.py:699-721`) |
| `seed` | int | — | no | non-negative int | alias for layout_seed (layout_seed wins) (`graph.py:701`) |
| `show_weights` | bool | False | no | bool | render edge-weight pills (`graph.py:666`) |
| `label` | str | None | no | any | caption (`graph.py:723`) |
| `auto_expand` | bool | False | no | bool | expand positions so pills fit (`graph.py:667`) |
| `split_labels` | bool | False | no | bool | split `a/b` weight into two tspans (`graph.py:670`) |
| `tint_by_source` | bool | False | no | bool | pill fill from source-node state (`graph.py:671`) |
| `tint_by_edge` | bool | False | no | bool | pill fill from edge state (`graph.py:672`) |
| `global_optimize` | bool | False | no | bool | **no-op forward-compat flag; warns** (`graph.py:680-691`) |
| `orientation` | str | `"TB"` | no | `TB`, `LR` (hierarchical only) | layer axis (`graph.py:651`) |

- Errors: E1470 (empty nodes), E1501 (>100 nodes), E1474 (edge shape/mix), E1505 (bad seed).
- Operations (`apply_command`, `graph.py:828-880`): `add_edge` `{from,to,weight?}`, `remove_edge` `{from,to}`, `set_weight` `{from,to,value}`. NO add_node/remove_node.
- Selectors (`graph.py:575-579`): `node[{id}]`, `edge[({u},{v})]`, `all`.
- Node ids are NOT str-normalized — Graph stays strict on `int` vs `str` (`graph.py:601`, resolve `1042-1048`).

### 5. Tree — `tree.py:63-94`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `root` | str/int | — | yes (standard kind) | any (str-normalized) | root id; E1430 if missing (`tree.py:152-164`) |
| `nodes` | list | `[]` | no | ids str-normalized | node ids (`tree.py:165`) |
| `edges` | list | `[]` | no | (parent,child) tuples, str-normalized | edges (`tree.py:166-169`) |
| `kind` | str | None | no | `segtree`, `sparse_segtree`, or unset (standard) | tree variant (`tree.py:99,104-109`) |
| `data` | list | — | required if kind=segtree | leaf values | E1431 if missing (`tree.py:187-198`) |
| `range_lo` | int | — | required if kind=sparse_segtree | int | lower bound; E1432 (`tree.py:211-225`) |
| `range_hi` | int | — | required if kind=sparse_segtree | int | upper bound |
| `show_sum` | bool | False | no | bool | append `=sum` to segtree node labels (`tree.py:101,206-209`) |
| `label` | str | None | no | any | caption |

- Errors: E1430, E1431, E1432; mutation guards E1433/E1434/E1435/E1436.
- Operations (`apply_command`, `tree.py:236-275`): `add_node` `{id,parent}`, `remove_node` `id` or `{id,cascade?}`, `reparent` `{node,parent}`.
- Selectors (`tree.py:78-82`): `node[{id}]`, `edge[({u},{v})]`, `all`.
- Node ids ARE str-normalized at construction and on all mutations (see §D).

### 6. NumberLine — `numberline.py:70-159`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `domain` | 2-element list | — | yes | `[min, max]` | axis bounds; E1452 missing, E1453 not 2-elem (`numberline.py:96-113`) |
| `ticks` | int | auto (max-min+1 if int domain, else 11) | no | 1..1000 (**count, not spacing**) | number of tick marks (`numberline.py:115-139`) |
| `labels` | list OR str | auto from domain | no | list of strings, or `"0..10"` format string | tick labels (`numberline.py:141-142`, `_resolve_labels:368-394`) |
| `label` | str | None | no | any | caption |

- Errors: E1452, E1453, E1454 (ticks > 1000), E1103 (ticks < 1).
- Operations: **NONE** (no `apply_command`).
- Selectors (`numberline.py:80-85`): `tick[{i}]`, `range[{lo}:{hi}]`, `axis`, `all`.

### 7. Matrix / Heatmap — `matrix.py:125-152` (alias `Heatmap` → same class, `matrix.py:125`)

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `rows` | int | — | yes | positive int | (`matrix.py:156-175`) |
| `cols` | int | — | yes | positive int | rows*cols ≤ 250000 → else E1425 |
| `data` | flat or 2D list | zeros | no | flat len==r*c OR 2D | E1422 on flat mismatch (`matrix.py:185-207`) |
| `colorscale` | str | `"viridis"` | no | **`"viridis"` ONLY** | validated; unknown → E1421 (`matrix.py:209-218`) |
| `show_values` | bool | False | no | bool | print numeric values in cells |
| `cell_size` | int | 24 | no | int px | per-cell pixel size |
| `vmin` | float | data min | no | float | color-scale lower clamp |
| `vmax` | float | data max | no | float | color-scale upper clamp |
| `row_labels` | list | None | no | list of str | left-axis labels |
| `col_labels` | list | None | no | list of str | top-axis labels |
| `label` | str | None | no | any | caption |

- Errors: E1420 (missing rows/cols), E1421 (range OR bad colorscale), E1422 (data length), E1425 (cap).
- Operations: **NONE** (no `apply_command`). Cell values are display-driven by `data`/state only.
- Selectors (`matrix.py:135-138`): `cell[{r}][{c}]`, `all`.
- Doc flag: `colorscale` is **validated to viridis only** now (see §B).

### 8. Stack — `stack.py:71-98`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `items` | list | `[]` | no | list of str or `{label,value?}` dicts | initial items (`stack.py:116-127`) |
| `orientation` | str | `"vertical"` | no | `vertical`, `horizontal` | layout direction (`stack.py:103`) |
| `max_visible` | int | 10 | no | positive int | visible window; E1441 if <1 (`stack.py:104-112`) |
| `label` | str | None | no | any | caption |

- Errors: E1441 (max_visible range).
- Operations (`apply_command`, `stack.py:143-170`): `push="label"` or `push={label,value?}`, `pop=N` (removes N from top).
- Selectors (`stack.py:87-91`): `item[{i}]`, `top`, `all`.

### 9. Plane2D — `plane2d.py:94-136`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `xrange` | 2-list | `[-5,5]` | no | endpoints not equal | x viewport; E1460 if degenerate (`plane2d.py:142-146`) |
| `yrange` | 2-list | `[-5,5]` | no | endpoints not equal | y viewport; E1460 |
| `grid` | bool OR str | True | no | `True`/`False`/`"fine"` | grid lines (`plane2d.py:151`, fine at 766) |
| `axes` | bool | True | no | bool | draw axes |
| `aspect` | str | `"equal"` | no | `equal`, `auto` | E1465 otherwise (`plane2d.py:153-156`) |
| `width` | int | 320 | no | int px | canvas width |
| `height` | int | computed (equal) / 320 (auto) | no | int px | canvas height |
| `points` | list | `[]` | no | see add_point shape | initial points |
| `lines` | list | `[]` | no | see add_line shape | initial lines |
| `segments` | list | `[]` | no | see add_segment shape | initial segments |
| `polygons` | list | `[]` | no | see add_polygon shape | initial polygons |
| `regions` | list | `[]` | no | see add_region shape | initial shaded regions |
| `show_coords` | bool | False | no | bool | print coords next to points (`plane2d.py:192`) |

- Element cap: 500 per frame → E1466 (`plane2d.py:226-239`).
- Errors: E1460, E1465, E1466, E1467 (malformed add-spec), E1437 (remove out of range/already-removed). E1461/E1462/E1463 are warnings only.
- Operations (`apply_command`, `plane2d.py:388-421`): `add_point`, `add_line`, `add_segment`, `add_polygon`, `add_region`, and `remove_point/line/segment/polygon/region=<idx>` (tombstone semantics).
- Selectors (`plane2d.py:108-115`): `point[{i}]`, `line[{i}]`, `segment[{i}]`, `polygon[{i}]`, `region[{i}]`, `all`.

### 10. MetricPlot — `metricplot.py:96-136`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `series` | list | — | yes (≥1) | str OR `{name,color?,axis?,scale?}` dicts | ≤8 series; E1480 empty, E1481 >8 (`metricplot.py:142-188`) |
| `xlabel` | str | `"step"` | no | any | x-axis label |
| `ylabel` | str | `"value"` | no | any | left y-axis label |
| `ylabel_right` | str | None | no | any | right y-axis label |
| `grid` | bool | True | no | bool | grid lines |
| `width` | int | 320 | no | int | canvas width |
| `height` | int | 200 | no | int | canvas height |
| `show_legend` | bool | True | no | bool | legend (`metricplot.py:202`) |
| `show_current_marker` | bool | True | no | bool | marker at latest point (`metricplot.py:203`) |
| `xrange` | `"auto"` or 2-list | `"auto"` | no | auto or `[min,max]` | E1486 if degenerate (`metricplot.py:206-214`) |
| `yrange` | `"auto"` or 2-list | `"auto"` | no | auto or `[min,max]` | left axis range |
| `yrange_right` | `"auto"` or 2-list | `"auto"` | no | auto or `[min,max]` | right axis range |

- Per-series dict fields: `name` (req), `color` (default `"auto"` → Wong palette), `axis` (`left`/`right`), `scale` (`linear`/`log`). Same-axis series must share scale → E1487 (`metricplot.py:159-188,237-245`).
- Errors: E1480, E1481, E1483 (>1000 pts/series), E1485 (dup series name), E1486, E1487.
- Operations (`apply_command`, `metricplot.py:251-272`): feed data via `\apply{plot}{seriesName=value, ...}` — each known series name in params appends one point; unknown keys ignored. Advances step index.
- Selectors (`metricplot.py:119-121`): `all` ONLY.

### 11. CodePanel — `codepanel.py:56-82`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `source` | str | None | one of source/lines | newline-separated string | strips one leading/trailing `\n`, splits on `\n` (`codepanel.py:88-103`) |
| `lines` | list | None | one of source/lines | list of str | explicit line list (`codepanel.py:91-95`) |
| `label` | str | None | no | any | **renders as a top header/title bar** (see §D) (`codepanel.py:107,213,284-305`) |

- Errors: none specific (empty → "no code" placeholder).
- Operations: **NONE** (no `apply_command`).
- Selectors (`codepanel.py:73-76`): `line[{i}]` (**1-based**; `line[0]` rejected, `codepanel.py:148-164`), `all`.

### 12. HashMap — `hashmap.py:57-82`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `capacity` | int | — | yes | positive int | bucket count; E1450 missing, E1451 <1 (`hashmap.py:87-102`) |
| `label` | str | None | no | any | caption |

- Errors: E1450, E1451.
- Operations (`apply_command`, `hashmap.py:141-163`): `\apply{hm.bucket[i]}{value="..."}` sets bucket display text (target_suffix = `bucket[i]`). No push/insert/delete op.
- Selectors (`hashmap.py:74-77`): `bucket[{i}]`, `all`.

### 13. LinkedList — `linkedlist.py:68-93`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `data` | list OR JSON-string | `[]` | no | list of values, or `"[3,7,1]"` parsed via json (`linkedlist.py:104-115`) | node values |
| `label` | str | None | no | any | caption |

- Errors: none specific.
- Operations (`apply_command`, `linkedlist.py:139-168`): `insert={index,value}` (defaults index=end), `remove=<idx>`. Per-node `value=X` via base value layer / `set_value`.
- Selectors (`linkedlist.py:84-88`): `node[{i}]`, `link[{i}]` (link[i] is the arrow node[i]→node[i+1]; valid `0 ≤ i < len-1`), `all`.

### 14. Queue — `queue.py:89-116`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `capacity` | int | 8 | no | positive int | fixed capacity; E1440 if <1 (`queue.py:121-129`) |
| `data` | list | `[]` | no | list (truncated to capacity) | initial contents (`queue.py:136-139`) |
| `label` | str | None | no | any | caption |

- Errors: E1440.
- Operations (`apply_command`, `queue.py:157-194`): `enqueue=<value>` (adds at rear, advances rear), `dequeue=true` (removes at front, advances front — only fires on truthy `True`/`"true"`; `dequeue=false` is a no-op). Per-cell `value=X` via `set_value`.
- Selectors (`queue.py:105-110`): `cell[{i}]`, `front`, `rear`, `all`.

### 15. VariableWatch — `variablewatch.py:53-78`

| Param | Type | Default | Required? | Allowed values | Description |
|-------|------|---------|-----------|----------------|-------------|
| `names` | list OR comma-str | `[]` | effectively yes (empty → warning) | list of var-name strings, or `"a,b,c"` (`variablewatch.py:83-93`) | tracked variable names |
| `label` | str | None | no | any | caption |

- Errors: none (empty names → UserWarning, not E-code).
- Operations (`apply_command`, `variablewatch.py:131-154`): targeted `\apply{vars.var[name]}{value=X}` OR bulk `\apply{vars}{a=1, b=2}` (each param key matching a var name sets it). `set_value` also supported.
- Selectors (`variablewatch.py:70-73`): `var[{name}]` (name must match `[A-Za-z_]\w*`), `all`.

---

## B. Field shapes the doc gets wrong / vague

1. **`colorscale` (Matrix/Heatmap)** — now VALIDATED. Only valid value is `"viridis"` (`COLORSCALES` dict, `matrix.py:45-47`; check + E1421 at `matrix.py:209-218`). Any other name (e.g. `"plasma"`, `"magma"`) is a hard error. The doc must not list multiple colorscales.

2. **Plane2D `add_region` shape** (`plane2d.py:373-384`) — a **dict only**: `{polygon: [(x,y), ...], fill?: <color>}`. Default `fill` is `"rgba(0,114,178,0.2)"`. A bare list is NOT accepted for regions (raises E1467). (Polygons, by contrast, accept a bare list.)

3. **Plane2D `add_line` tuple element meaning** (`plane2d.py:270-315`) — two tuple forms:
   - `(label, slope, intercept)` → 3-tuple where element[1] is **slope**, element[2] is **intercept** (y = slope·x + intercept).
   - `(label, {a, b, c})` → 2-tuple with a dict, representing the implicit line **ax + by = c** (converted to slope/intercept internally; vertical when b≈0).
   - Also accepts dict `{label?, slope, intercept}`.
   So in the 3-tuple, element 0 is the label, NOT a coordinate.

4. **Matrix/Grid/DPTable `data` flat-vs-nested rule:**
   - Grid (`grid.py:38-74`): accepts a flat list of length rows*cols, OR a 2D list (list of rows). Both validated to rows*cols; E1412 on mismatch.
   - Matrix (`matrix.py:185-207`): accepts 2D list (kept as rows) OR flat list (reshaped); flat must be len==rows*cols else E1422. Empty → zeros.
   - DPTable (`dptable.py:162-171`): `data` is a **flat list** of length n (1D) or rows*cols (2D); E1429 on mismatch. (No 2D-nested form for DPTable — it is always flat.)

5. **NumberLine `ticks`** (`numberline.py:115-139`) — a **COUNT** (number of tick marks), not a spacing. Default = `max-min+1` for integer domains, else 11. Range 1..1000 (E1454 over, E1103 under).

6. **Array `labels` vs `label`** (`array.py:152-153,454-471`):
   - `labels` is a **format string** describing the index-label row: `"0..6"` (numeric) or `"dp[0]..dp[6]"` (prefixed). It is NOT a list of labels.
   - `label` is a single caption string shown below the array.
   - (Contrast NumberLine, where `labels` DOES accept a list — `numberline.py:388-389`.)

---

## C. Error catalog truth

- **E1501** — real meaning: "Too many nodes for stable layout (falling back to force layout)" per catalog (`errors.py:425`), BUT the only **raised** site is Graph construction rejecting >100 nodes (`graph.py:611-622`). The doc mislabels it; it is the node-count cap, not a generic graph error.
- **E1502** — "Too many frames for stable layout (falling back to force layout)" (`errors.py:426`). It is a layout fallback warning, not an editorial-facing error.
- **E1159** — REGISTERED (`errors.py:211-214`) and RAISED (`scene.py:637-646`): a `${name}` used as a selector index outside `\foreach` whose binding is absent. New fix.
- **E1320 / E1321** — both REGISTERED (`errors.py:237-238`): E1320 = `\hl` outside a `\narrate` body; E1321 = `\hl` references unknown step-id. These EXIST (the `\hl` cross-reference macro codes), contrary to any doc claim they are missing.
- **E1467** — REGISTERED (`errors.py:391`) and RAISED across Plane2D add helpers (`plane2d.py:250,298,309,327,367,380`): malformed add-element spec.
- All four "new codes" the task asks about (**E1159, E1320, E1321, E1467**) are present in `ERROR_CATALOG`.
- Codes that exist as catalog entries but are **warning/log-only, never raised**: E1461, E1462, E1463 (Plane2D), E1466 is now RAISED (`plane2d.py:234`), E1500/E1502/E1503/E1504 (layout warnings). E1103 is a retained deprecated mega-bucket alias (`errors.py:172-178,472`).

---

## D. Today's behaviour changes to reflect

1. **Tree node ids str-normalized** (commit `8989a10`, `tree.py:164-169,302-303,343,418-419`): root/nodes/edges and all mutation ids are `str()`-cast at construction and in `_add_node_internal`/`_remove_node_internal`/`_reparent_internal`. Therefore for Tree, `T.node[8]` and `T.node["8"]` resolve to the same node, and `parent=3` / `parent="3"` are interchangeable. **Graph stays strict** — Graph keeps raw `int`/`str` node identity (`graph.py:601`, `resolve_annotation_point:1042-1048` only falls back to int parse).

2. **`\apply value=${scalar}` and `${var}` selector-index now resolve** (commits `cbdd7ce` + E1159 fix): apply param values go through `_resolve_interp` (`scene.py:579-602`); selector index `${name}` goes through `_resolve_selector`/`_resolve_index_expr` (`scene.py:604-659`), which looks the name up in `\compute` bindings and substitutes the concrete value. An unbound `${name}` in a selector index is now a hard **E1159** instead of a silent phantom target.

3. **CodePanel label renders as a top header bar** (commit `e9de3f1`, `codepanel.py:33,131-137,212-213,284-305`): when `label` is set, `_HEADER_HEIGHT=26` is reserved and an IDE-tab-style title bar + divider is drawn across the top; code lines are pushed down. It is NOT a bottom caption.

4. **Animation viewBox sizes to max extent across frames** (commit `cc470a8`): several primitives keep monotonic non-shrinking widths so the stage viewBox computed from the largest historical extent stays stable (e.g. Queue `_cell_width` grow-only `queue.py:181-182`, HashMap `_max_entries_col_width` `hashmap.py:112,159-162`, LinkedList `_recalc_widths` monotonic `linkedlist.py:132-133`, VariableWatch `_recalc_value_col` monotonic `variablewatch.py:111-127`). `set_min_arrow_above` (`base.py:308-315`) similarly locks arrow headroom to the cross-frame max.

---

## E. Boolean casing

The parser accepts **only lowercase `true` / `false`** as booleans (`_grammar_tokens.py:304-310`): an `IDENT` token equal to `"true"` → Python `True`, `"false"` → `False`. Any other identifier (including Python-case `True` / `False`) is returned as the **plain string** `"True"` / `"False"`, NOT a boolean.

Consequence: `directed=True` passes the string `"True"` to the primitive. For most flags this still reads truthy (`bool("True")` is True), but `dequeue=False` would be the truthy string `"False"` — Queue specifically guards against this via `_is_truthy_flag`, which only accepts Python `True` or case-insensitive `"true"` (`queue.py:69-82`). **The doc should use lowercase `true`/`false` consistently.**

There is also a bare-flag shorthand: `\apply{stk}{pop}` parses `pop` as `{pop: True}` (`_grammar_tokens.py:243-256`).

---

## F. State list (canonical)

`\recolor{X}{state=...}` validates against `VALID_STATES` (`_grammar_commands.py:95-105`, code E1109). The canonical set is **9 states** (`constants.py:27-32`):

```
idle, current, done, dim, error, good, highlight, path, hidden
```

- `highlight` IS a real, recolor-able state (also set implicitly by `\highlight`).
- `hidden` (RFC-001 §4.4) is included — elements in `hidden` are skipped entirely by emit loops (distinct from `dim`).
- `STATE_COLORS` (`_types.py:79-91`) defines inline-fallback colors for 8 of these (no `hidden` entry, since hidden elements are not drawn).
- So the doc's §5.7 list of 8 and §6 list of 9 are both wrong against the real set: the truth is **these exact 9**, and `highlight` is valid.
