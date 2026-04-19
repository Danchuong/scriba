# §6–8 Primitives, States, Selectors Audit

Audit date: 2026-04-19
Source sections: SCRIBA-TEX-REFERENCE.md lines 418–634
Code baseline: scriba/animation/primitives/ (all .py files listed)

---

## Primitive-by-Primitive Check

### Array
- **Type:** `array` — matches doc (`primitive_type = "array"`, array.py:81)
- **ACCEPTED_PARAMS (code):** `size`, `n`, `data`, `labels`, `label`, `values` (array.py:89–98)
- **ACCEPTED_PARAMS (doc §7.1):** `size`, `data`, `labels`, `label` — doc example uses `size=8, data=[...], labels="0..7", label="$arr$"`. Code also accepts `n` (alias for `size`) and `values` (legacy alias). These extras are undocumented but intentionally accepted for backward compatibility. Not a bug; note for completeness.
- **SELECTOR_PATTERNS (code):** `cell[{i}]`, `range[{lo}:{hi}]`, `all` (array.py:83–87)
- **§8 selectors (doc):** `.cell[i]`, `.range[i:j]`, `.all` — matches code patterns exactly.
- **§7.1 inline selectors:** `a`, `a.cell[i]`, `a.cell[${i}]`, `a.range[i:j]`, `a.all` — all match.
- **Status:** PASS

---

### Grid
- **Type:** `grid` — matches doc (`primitive_type = "grid"`, grid.py:99)
- **ACCEPTED_PARAMS (code):** `rows`, `cols`, `data`, `label` (grid.py:106–111)
- **ACCEPTED_PARAMS (doc §7.2):** doc example uses `rows=3, cols=3, data=${matrix_data}, label="Board"` — matches exactly.
- **SELECTOR_PATTERNS (code):** `cell[{r}][{c}]`, `all` (grid.py:101–104)
- **§8 selectors (doc):** `.cell[r][c]`, `.all` — matches.
- **Status:** PASS

---

### DPTable
- **Type:** `dptable` — matches doc (`primitive_type = "dptable"`, dptable.py:75)
- **ACCEPTED_PARAMS (code):** `n`, `rows`, `cols`, `data`, `labels`, `label` (dptable.py:84–91)
- **ACCEPTED_PARAMS (doc §7.3):** doc 1D example uses `n=7, label="dp[i]", labels="0..6"`; 2D uses `rows=6, cols=6, label="dp[l][r]"`. All used params are in the accepted set. Matches.
- **SELECTOR_PATTERNS (code):** `cell[{i}]`, `cell[{r}][{c}]`, `range[{lo}:{hi}]`, `all` (dptable.py:77–82)
- **§8 selectors (doc):** `.cell[i]` or `.cell[i][j]`, `.range[i:j]` (1D), `.all` — matches code patterns exactly.
- **Status:** PASS

---

### Graph
- **Type:** `graph` — matches doc (`primitive_type = "graph"`, graph.py:298)
- **ACCEPTED_PARAMS (code):** `nodes`, `edges`, `directed`, `layout`, `layout_seed`, `layout_lambda`, `seed`, `show_weights`, `label` (graph.py:306–316)
- **ACCEPTED_PARAMS (doc §7.4):** doc mentions `nodes`, `edges`, `directed`, `layout`, `layout_seed`, `show_weights`, `label`. Two params in code are undocumented in §7.4:
  - `layout_lambda` — internal tuning param; not mentioned anywhere in §7.4.
  - `seed` — accepted as convenience alias for `layout_seed`; mentioned in code docstring (graph.py:291–296) but not in the user-facing doc.
  These are LOW severity omissions (advanced/alias params).
- **SELECTOR_PATTERNS (code):** `node[{id}]`, `edge[({u},{v})]`, `all` (graph.py:300–304)
- **§8 selectors (doc):** `.node[id]`, `.node["A"]`, `.edge[(u,v)]`, `.all` — matches. The `node["A"]` form is a string-quoted variant of `node[{id}]` and is handled by the same pattern.
- **Status:** PASS (minor LOW omissions noted)

---

### Tree
- **Type:** `tree` — matches doc (`primitive_type = "tree"`, tree.py:73)
- **ACCEPTED_PARAMS (code):** `root`, `nodes`, `edges`, `kind`, `data`, `range_lo`, `range_hi`, `show_sum`, `label` (tree.py:81–91)
- **ACCEPTED_PARAMS (doc §7.5):** doc covers `root`, `nodes`, `edges`, `kind`, `data`, `range_lo`, `range_hi`, `show_sum`, `label`. All accepted params are documented in §7.5 examples. Matches.
- **SELECTOR_PATTERNS (code):** `node[{id}]`, `edge[({u},{v})]`, `all` (tree.py:75–79)
- **§8 selectors (doc):** `T.node[id]`, `T.node["[0,5]"]`, `T.edge[(p,c)]`, `T.all` — matches.
- **Status:** PASS

---

### NumberLine
- **Type:** `numberline` — matches doc (`primitive_type = "numberline"`, numberline.py:68)
- **ACCEPTED_PARAMS (code):** `domain`, `ticks`, `labels`, `label` (numberline.py:77–82)
- **ACCEPTED_PARAMS (doc §7.6):** doc example uses `domain=[0,24], ticks=25, label="Range"`. Missing from doc example: `labels` param is in the accepted set but not mentioned in §7.6. LOW omission.
- **SELECTOR_PATTERNS (code):** `tick[{i}]`, `range[{lo}:{hi}]`, `axis`, `all` (numberline.py:70–75)
- **§8 selectors (doc):** `nl.tick[i]`, `nl.range[lo:hi]`, `nl.axis`, `nl.all` — matches code exactly.
- **Status:** PASS (LOW: `labels` param not shown in §7.6 example)

---

### Matrix / Heatmap
- **Type:** `matrix` — matches doc (`primitive_type = "matrix"`, matrix.py:130)
- **Alias:** `@register_primitive("Matrix", "Heatmap")` (matrix.py:123) — doc §7.7 correctly notes `Heatmap` is an alias.
- **ACCEPTED_PARAMS (code):** `rows`, `cols`, `data`, `colorscale`, `show_values`, `cell_size`, `vmin`, `vmax`, `row_labels`, `col_labels`, `label` (matrix.py:137–149)
- **ACCEPTED_PARAMS (doc §7.7):** doc example uses only `rows=4, cols=4, data=[...], show_values=true`. Undocumented accepted params: `colorscale`, `cell_size`, `vmin`, `vmax`, `row_labels`, `col_labels`. These are genuine feature params not mentioned anywhere in §7.7. **HIGH**: Users cannot discover these params from the reference doc.
- **SELECTOR_PATTERNS (code):** `cell[{r}][{c}]`, `all` (matrix.py:132–135)
- **§8 selectors (doc):** `m.cell[r][c]`, `m.all` — matches.
- **Status:** FAIL — HIGH: six accepted params (`colorscale`, `cell_size`, `vmin`, `vmax`, `row_labels`, `col_labels`) undocumented in §7.7.

---

### Stack
- **Type:** `stack` — matches doc (`primitive_type = "stack"`, stack.py:82)
- **ACCEPTED_PARAMS (code):** empty frozenset — Stack does **not** override `ACCEPTED_PARAMS` (stack.py:84–88 shows only `SELECTOR_PATTERNS`; no `ACCEPTED_PARAMS` assignment). This is the intentional permissive opt-out inherited from `PrimitiveBase` (base.py:191). All `\shape` params are accepted without validation.
- **Note:** Stack's constructor silently reads `items`, `orientation`, `max_visible`, `label` from params. These are the de-facto accepted params but are not enforced via `ACCEPTED_PARAMS`. This is intentional permissive behavior, not a bug.
- **SELECTOR_PATTERNS (code):** `item[{i}]`, `top`, `all` (stack.py:84–88)
- **§8 selectors (doc):** `s.item[i]`, `s.top`, `s.all` — matches code exactly.
- **Status:** PASS (note: empty `ACCEPTED_PARAMS` is permissive opt-out, intentional)

---

### Plane2D
- **Type:** `plane2d` — matches doc (`primitive_type = "plane2d"`, plane2d.py:98)
- **ACCEPTED_PARAMS (code):** `xrange`, `yrange`, `grid`, `axes`, `aspect`, `width`, `height`, `points`, `lines`, `segments`, `polygons`, `regions`, `xlabel`, `ylabel`, `label`, `show_coords` (plane2d.py:118–138)
- **ACCEPTED_PARAMS (doc §7.9):** doc mentions `xrange`, `yrange`, `grid`, `axes`, `show_coords`. Undocumented accepted params: `aspect`, `width`, `height`, `points`, `lines`, `segments`, `polygons`, `regions`, `xlabel`, `ylabel`. Note the code itself comments that `xlabel`/`ylabel`/`label` are accepted but "currently have no rendered effect" (plane2d.py:112–117). **HIGH**: many accepted params are invisible to users from §7.9.
- **SELECTOR_PATTERNS (code):** `point[{i}]`, `line[{i}]`, `segment[{i}]`, `polygon[{i}]`, `region[{i}]`, `all` (plane2d.py:100–107)
- **§8 selectors (doc):** §8 table lists `.point[i]` in Cell/Item column. The extended §8 table at lines 620–631 documents all six selector families (`point`, `line`, `segment`, `polygon`, `region`, `all`) — this **matches** the code `SELECTOR_PATTERNS` exactly.
- **Status:** PASS for selectors. HIGH for undocumented params.

---

### MetricPlot
- **Type:** `metricplot` — matches doc (`primitive_type = "metricplot"`, metricplot.py:115)
- **ACCEPTED_PARAMS (code):** `series`, `xlabel`, `ylabel`, `ylabel_right`, `grid`, `width`, `height`, `show_legend`, `show_current_marker`, `xrange`, `yrange`, `yrange_right` (metricplot.py:121–134)
- **ACCEPTED_PARAMS (doc §7.10):** doc mentions only `series`, `xlabel`, `ylabel`. Undocumented params: `ylabel_right`, `grid`, `width`, `height`, `show_legend`, `show_current_marker`, `xrange`, `yrange`, `yrange_right`. **HIGH**: nine accepted params undocumented in §7.10.
- **SELECTOR_PATTERNS (code):** `all` (metricplot.py:117–119)
- **§8 selectors (doc):** MetricPlot row shows `—` for all selector types, no `.all`. **Code has `all` in SELECTOR_PATTERNS** but doc §8 omits it. **MED**: §8 is incomplete for MetricPlot — `.all` is a valid selector in code but not shown.
- **Status:** FAIL — HIGH: nine params undocumented; MED: `.all` selector missing from §8.

---

### CodePanel
- **Type:** `codepanel` — matches doc (`primitive_type = "codepanel"`, codepanel.py:67)
- **ACCEPTED_PARAMS (code):** `source`, `lines`, `label` (codepanel.py:74–78)
- **ACCEPTED_PARAMS (doc §7.11):** doc example uses only `lines=[...]`, `label="Code"`. The `source` param (newline-separated string alternative) is accepted in code but not mentioned in §7.11. LOW omission.
- **SELECTOR_PATTERNS (code):** `line[{i}]`, `all` (codepanel.py:69–72)
- **§8 selectors (doc):** CodePanel row shows only `.line[i]` — **`.all` is present in code `SELECTOR_PATTERNS` but absent from §8 table**. **MED**: `.all` is a valid selector but the §8 table omits it.
- **Status:** FAIL — MED: `.all` missing from §8; LOW: `source` param undocumented.

---

### HashMap
- **Type:** `hashmap` — matches doc (`primitive_type = "hashmap"`, hashmap.py:69)
- **ACCEPTED_PARAMS (code):** `capacity`, `label` (hashmap.py:76–79)
- **ACCEPTED_PARAMS (doc §7.12):** doc uses `capacity=4, label="$map$"` — matches exactly.
- **SELECTOR_PATTERNS (code):** `bucket[{i}]`, `all` (hashmap.py:71–74)
- **§8 selectors (doc):** HashMap row shows `.bucket[i]` only — **`.all` is in code `SELECTOR_PATTERNS` but absent from §8 table**. **MED**: `.all` is a valid selector but §8 omits it.
- **Status:** FAIL — MED: `.all` missing from §8.

---

### LinkedList
- **Type:** `linkedlist` — matches doc (`primitive_type = "linkedlist"`, linkedlist.py:80)
- **ACCEPTED_PARAMS (code):** `data`, `label` (linkedlist.py:88–91)
- **ACCEPTED_PARAMS (doc §7.13):** doc uses `data=[3,7,1,9], label="$list$"` — matches exactly.
- **SELECTOR_PATTERNS (code):** `node[{i}]`, `link[{i}]`, `all` (linkedlist.py:82–86)
- **§8 selectors (doc):** LinkedList row shows `.node[i]`, `.link[i]` — **`.all` is in code `SELECTOR_PATTERNS` but absent from §8 table**. **MED**: `.all` is a valid selector but §8 omits it.
- **Status:** FAIL — MED: `.all` missing from §8.

---

### Queue
- **Type:** `queue` — matches doc (`primitive_type = "queue"`, queue.py:98)
- **ACCEPTED_PARAMS (code):** `capacity`, `data`, `label` (queue.py:107–111)
- **ACCEPTED_PARAMS (doc §7.14):** doc uses `capacity=6, data=[1], label="$Q$"` — matches exactly.
- **SELECTOR_PATTERNS (code):** `cell[{i}]`, `front`, `rear`, `all` (queue.py:100–105)
- **§8 selectors (doc):** Queue row shows `.cell[i]`, `.front`, `.rear` — **`.all` is in code `SELECTOR_PATTERNS` but absent from §8 table**. **MED**: `.all` is a valid selector but §8 omits it.
- **Status:** FAIL — MED: `.all` missing from §8.

---

### VariableWatch
- **Type:** `variablewatch` — matches doc (`primitive_type = "variablewatch"`, variablewatch.py:65)
- **ACCEPTED_PARAMS (code):** `names`, `label` (variablewatch.py:72–75)
- **ACCEPTED_PARAMS (doc §7.15):** doc uses `names=["i","j","min_val","result"], label="Variables"` — matches exactly.
- **SELECTOR_PATTERNS (code):** `var[{name}]`, `all` (variablewatch.py:67–70)
- **§8 selectors (doc):** VariableWatch row shows `.var[name]` only — **`.all` is in code `SELECTOR_PATTERNS` but absent from §8 table**. **MED**: `.all` is a valid selector but §8 omits it.
- **Status:** FAIL — MED: `.all` missing from §8.

---

## Visual States Check

### Documented states (§6, lines 418–431)
`idle`, `current`, `done`, `dim`, `error`, `good`, `path`, `hidden`, `highlight`
Total: 9 states

### Code states (constants.py:27–32, `VALID_STATES` frozenset)
`idle`, `current`, `done`, `dim`, `error`, `good`, `highlight`, `path`, `hidden`
Total: 9 states

### State presence diff
All 9 code states are documented. All 9 doc states exist in code. **No diff.**

### Color accuracy check (§6 vs `STATE_COLORS` in _types.py:74–86)

| State | Doc color | Code fill color | Match? |
|-------|-----------|-----------------|--------|
| `idle` | "default bg" | `#f8f9fa` | OK (no hex claimed) |
| `current` | blue `#0072B2` | `#0070d5` (_types.py:77) | **MISMATCH** — doc claims `#0072B2`, code uses `#0070d5` |
| `done` | green `#009E73` | `#e6e8eb` (_types.py:78) | **MISMATCH** — doc claims green `#009E73`, code renders as slate-5 `#e6e8eb` (neutral gray) |
| `dim` | "50% opacity" | `#f1f3f5` fill, `#687076` text (_types.py:80) | **MISMATCH** — doc says opacity-based, code uses distinct fill/text colors (no opacity reduction) |
| `error` | vermillion `#D55E00` | `#e5484d` stroke, `#f8f9fa` fill (_types.py:81) | **MISMATCH** — doc claims vermillion `#D55E00`, code uses red `#e5484d` stroke |
| `good` | sky blue `#56B4E9` | `#e6e8eb` fill, `#2a7e3b` stroke (_types.py:82) | **MISMATCH** — doc claims sky blue `#56B4E9`, code uses slate fill + green stroke |
| `path` | blue `#2563eb` | `#e6e8eb` fill, `#c1c8cd` stroke (_types.py:85) | **MISMATCH** — doc claims blue `#2563eb`, code renders as neutral gray fill |
| `hidden` | "invisible" | not in STATE_COLORS | OK (hidden elements are skipped in emit_svg, no color needed) |
| `highlight` | yellow `#F0E442` | `#f8f9fa` fill, `#0090ff` stroke (_types.py:83) | **MISMATCH** — doc claims yellow `#F0E442`, code uses white fill + blue stroke |

**All 8 colored states have hex values that are stale or wrong.** The code switched from the Wong/CBF palette (cited in §6) to a Radix Slate system in a prior refactor, but §6 was not updated. The inline STATE_COLORS are the fallback for non-browser environments; the canonical colors are in `scriba-scene-primitives.css` (referenced in _types.py:68–71), but the hex values in §6 do not match either the CSS variables or the Python fallbacks.

---

## Findings

### [HIGH] §6 color hex values are entirely stale — all 8 colored states wrong
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 420–431
**Code ref:** scriba/animation/primitives/_types.py:74–86

§6 documents colors from the old Wong colorblind-friendly palette (`#0072B2`, `#009E73`, `#D55E00`, `#56B4E9`, `#F0E442`, `#2563eb`). The code was migrated to the Radix Slate β system. None of the hex values in §6 match the current code or CSS fallbacks. Users relying on §6 for custom CSS overrides, export theming, or accessibility review will get wrong values.

Specific mismatches:
- `current`: doc `#0072B2` → code `#0070d5` (_types.py:77)
- `done`: doc green `#009E73` → code slate `#e6e8eb` (_types.py:78)
- `dim`: doc "50% opacity" → code distinct fill `#f1f3f5` / text `#687076` (_types.py:80)
- `error`: doc vermillion `#D55E00` → code red stroke `#e5484d` (_types.py:81)
- `good`: doc sky blue `#56B4E9` → code slate fill + green stroke `#2a7e3b` (_types.py:82)
- `path`: doc blue `#2563eb` → code slate fill `#e6e8eb` + `#c1c8cd` stroke (_types.py:85)
- `highlight`: doc yellow `#F0E442` → code white fill `#f8f9fa` + blue stroke `#0090ff` (_types.py:83)

### [HIGH] §7.7 Matrix: six accepted params undocumented
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 527–533
**Code ref:** scriba/animation/primitives/matrix.py:137–149

Accepted params `colorscale`, `cell_size`, `vmin`, `vmax`, `row_labels`, `col_labels` exist in `ACCEPTED_PARAMS` but are not mentioned anywhere in §7.7. A user cannot customize the heatmap colorscale or cell size from the reference doc.

### [HIGH] §7.10 MetricPlot: nine accepted params undocumented
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 552–558
**Code ref:** scriba/animation/primitives/metricplot.py:121–134

Accepted params `ylabel_right`, `grid`, `width`, `height`, `show_legend`, `show_current_marker`, `xrange`, `yrange`, `yrange_right` exist in `ACCEPTED_PARAMS` but are absent from §7.10. Users cannot discover dual-axis (`ylabel_right`, `yrange_right`), range controls, or legend toggle from the doc.

### [MED] §8 table omits `.all` selector for five primitives
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 600–617
**Code refs:** codepanel.py:69–72, hashmap.py:71–74, linkedlist.py:82–86, queue.py:100–105, variablewatch.py:67–70, metricplot.py:117–119

The §8 selector quick-reference table shows `—` in the All column for CodePanel, HashMap, LinkedList, Queue, VariableWatch, and MetricPlot. All six have `"all"` in their `SELECTOR_PATTERNS`. Using `\recolor{code.all}`, `\recolor{hm.all}`, etc. is valid and works at runtime, but the table implies it is not supported.

### [MED] §8 table omits `.all` for MetricPlot (also reported above for completeness)
**File:** docs/SCRIBA-TEX-REFERENCE.md line 616
**Code ref:** scriba/animation/primitives/metricplot.py:117–119
`SELECTOR_PATTERNS` contains `"all": "the entire plot"` but §8 MetricPlot row is blank.

### [LOW] §7.9 Plane2D: nine accepted params undocumented (some intentional)
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 542–551
**Code ref:** scriba/animation/primitives/plane2d.py:118–138

`aspect`, `width`, `height`, `points`, `lines`, `segments`, `polygons`, `regions` are accepted by the primitive but not mentioned in §7.9. Note: the code itself marks `xlabel`/`ylabel`/`label` as accepted-but-no-effect (plane2d.py:112–117). At minimum `width`, `height`, `aspect`, and the bulk-init params (`points`, `lines`, etc.) should appear in the doc.

### [LOW] §7.4 Graph: two accepted params undocumented
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 460–474
**Code ref:** scriba/animation/primitives/graph.py:306–316

`layout_lambda` and `seed` are in `ACCEPTED_PARAMS` but not documented in §7.4. `seed` is noted in code docstring as a convenience alias for `layout_seed` (graph.py:291–296). Both are low-stakes omissions since `layout_seed` is documented.

### [LOW] §7.6 NumberLine: `labels` param not shown in example
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 520–525
**Code ref:** scriba/animation/primitives/numberline.py:77–82

The `labels` param is in `ACCEPTED_PARAMS` but the §7.6 example omits it. Users wanting custom tick labels cannot discover this from §7.6.

### [LOW] §7.11 CodePanel: `source` param undocumented
**File:** docs/SCRIBA-TEX-REFERENCE.md lines 559–565
**Code ref:** scriba/animation/primitives/codepanel.py:74–78, 84–101

`source` (newline-separated multiline string) is a full alternative to `lines=[...]` for constructing a CodePanel, and is handled in `__init__`, but §7.11 only shows the `lines` form.

### [LOW] Stack: `ACCEPTED_PARAMS` is empty frozenset (permissive opt-out)
**File:** scriba/animation/primitives/stack.py (no `ACCEPTED_PARAMS` assignment)
**Code ref:** base.py:191, 203–204

Stack uses the inherited empty `frozenset()` from `PrimitiveBase`, meaning unknown params are silently ignored rather than raising E1114. This is an intentional backward-compat design choice, not a bug. The doc does not describe this validation behavior difference, but the behavior itself is correct. Noted for completeness per audit instructions.

---

## Count Check

Doc claims: **16 primitives** (section header: "## 7. All 16 Primitives", 15 subsections 7.1–7.15 with §7.7 covering Matrix/Heatmap as one section).

Actual `@register_primitive` decorator calls: **15** (one per primitive file)
Registered type names in `_PRIMITIVE_REGISTRY`: **16** (`"Matrix"` and `"Heatmap"` are registered together by the single call at matrix.py:123)

Reconciliation: The doc counts `Heatmap` as the 16th name (it is documented as an alias in §7.7). The decorator count of 15 is accurate; the name-count of 16 matches the doc claim. **Count is consistent** — the doc headline "16 Primitives" refers to registered type names, not decorator calls.

Primitive files audited (15 files, 15 decorator calls, 16 registered names):
- array.py → `"Array"`
- codepanel.py → `"CodePanel"`
- dptable.py → `"DPTable"`
- graph.py → `"Graph"`
- grid.py → `"Grid"`
- hashmap.py → `"HashMap"`
- linkedlist.py → `"LinkedList"`
- matrix.py → `"Matrix"`, `"Heatmap"` (alias)
- metricplot.py → `"MetricPlot"`
- numberline.py → `"NumberLine"`
- plane2d.py → `"Plane2D"`
- queue.py → `"Queue"`
- stack.py → `"Stack"`
- tree.py → `"Tree"`
- variablewatch.py → `"VariableWatch"`

---

## Verdict

**5/10**

The structural skeleton (primitive existence, `primitive_type` strings, core selector patterns) is accurate. The 16-name count is correct. However:

- §6 color values are entirely stale — every non-idle state has the wrong hex. This is the most impactful error since it misleads anyone doing accessibility review or CSS customization.
- §8 systematically omits the `.all` selector for 6 primitives that support it.
- §7.7 (Matrix) and §7.10 (MetricPlot) are severely incomplete — together they hide 15 accepted params.
- §7.9 (Plane2D) is also incomplete for accepted params.
- Minor omissions in Graph, NumberLine, CodePanel.

Fixes required before the reference can be trusted for production use: §6 color table (HIGH), §8 `.all` column gaps (MED ×6), §7.7 Matrix params (HIGH), §7.10 MetricPlot params (HIGH).
