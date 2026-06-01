# Field Clarity Audit

**Document:** `docs/SCRIBA-TEX-REFERENCE.md` (1493 lines)
**Criterion:** FIELD CLARITY — for every settable parameter/field, can the reader tell exactly what to put in (type, default, allowed values, example)?
**Date:** 2026-06-01

## Verdict: **MEDIUM** (score: Medium-Low)

The doc has good field tables for `\annotate`, `\reannotate`, Graph, MetricPlot top-level params, and the `\step` label. But the **highest-traffic data-input fields are under-specified or actively misleading**, and several primitives have NO param documentation at all (Stack max_visible aside, HashMap, LinkedList, Queue, VariableWatch, CodePanel, Tree, DPTable list only one inline example each — their full `ACCEPTED_PARAMS` and the shape/forms of `data`/`labels`/`nodes` are not enumerated).

Two findings are **factually wrong** (block authoring or cause silent failure):
- `colorscale` is documented as "Named colorscale" implying a choice, but **only `"viridis"` exists** — any other value silently falls back to viridis.
- `tooltip=` on `\apply` (L332) is **not implemented anywhere in the codebase** — it is silently swallowed and never rendered.

And one is a literal placeholder: `add_region=...` (L838) ships `...` as if it were syntax.

---

## Findings Table

Ranked worst-first (blocks authoring → cosmetic).

| # | Field | Primitive / Cmd | Doc line | What's missing | What it ACTUALLY accepts (from code) | Severity | One-line fix |
|---|-------|-----------------|----------|----------------|--------------------------------------|----------|--------------|
| 1 | `add_region=` | Plane2D `\apply` | L838 | **Everything** — value is literally `...` | `{polygon=[(x,y),...], fill="rgba(...)"}` dict. `fill` default `"rgba(0,114,178,0.2)"`. Non-dict input is silently dropped (`_add_region_internal`, plane2d.py:349-354) | CRITICAL | `\apply{p}{add_region={polygon=[(0,0),(2,0),(0,2)], fill="rgba(0,114,178,0.2)"}}` |
| 2 | `regions` | Plane2D ctor | L827 | Element format absent ("Inline batch of shaded regions") | List of dicts `{polygon=[(x,y)...], fill="rgba(...)"}`. Bare list/tuple elements are silently ignored — region is the ONE element type with no tuple form (plane2d.py:349) | CRITICAL | Show element shape: `regions=[{polygon=[(0,0),(1,0),(0,1)], fill="rgba(0,114,178,0.2)"}]` |
| 3 | `colorscale` | Matrix | L793 | "allowed values" — implies a menu of named scales | **Only `"viridis"` is registered** (`COLORSCALES` matrix.py:45-47). Any other string silently falls back to viridis (matrix.py:273 `.get(..., VIRIDIS)`). No error. | CRITICAL | State: "Only `\"viridis\"` is supported today; other names silently fall back to viridis." |
| 4 | `tooltip=` | `\apply` | L332 | Type, behavior, example — listed as "Common" | **Not implemented.** `\apply` stores any non-`value`/`label` key in `apply_params` (scene.py:615-619); no primitive reads `tooltip`. Pure no-op, no warning. | CRITICAL | Remove `tooltip=` from L332, or mark "(reserved, not yet rendered)". |
| 5 | `add_line=("y=x",1,0)` | Plane2D `\apply` | L835 | Tuple element meaning fully unclear | `(label, slope, intercept)`: el0 is a **cosmetic label string only** (NOT parsed as an equation — `"y=x"` has no effect on geometry); el1=slope (float), el2=intercept (float). Also accepts `(label, {a,b,c})` for `ax+by=c`, or dict `{label, slope, intercept}` (plane2d.py:266-301). Vertical line: pass `{a=1,b=0,c=k}`. | HIGH | `add_line=("label", slope, intercept)` — first element is a display label, not an equation; e.g. `("y=x", 1, 0)`. |
| 6 | `lines` | Plane2D ctor | L824 | Element format ("Inline batch of infinite lines") | Same three forms as `add_line` (#5): `(label,slope,intercept)`, `(label,{a,b,c})`, or `{label,slope,intercept}` | HIGH | Cross-reference the `add_line` forms with one example each. |
| 7 | `data` (flat vs nested) | Matrix | L785 | Example uses `[0.1,0.3,...]` — flat vs 2D not stated; element type | Accepts **either** flat `[v,...]` (len must == rows*cols, else E1422) **or** nested `[[...],[...]]`. Values coerced to `float` (matrix.py:185-207). `...` in the example is not literal. | HIGH | "`data`: flat list of `rows*cols` floats, OR a nested `rows`×`cols` list. E.g. flat `[0.1,0.3,0.5,...]` (16 values for 4×4)." |
| 8 | `data` (shape) | Grid | L646 | Uses `${matrix_data}` — never says flat or nested accepted, or element type | Accepts flat list (len==rows*cols) OR nested list-of-lists; any element type (strings allowed); empty → blank cells. Mismatch → E1412 (grid.py:38-74) | HIGH | "`data`: flat or nested list of `rows*cols` items (any displayable value); omit for blank." |
| 9 | `labels` (Array) | Array | L639 | Forms not enumerated; `labels` vs `label` distinction implicit | `labels` is a **string** range-spec, not a list: `"0..7"` → `["0".."7"]`, or `"dp[0]..dp[6]"` → `["dp[0]"...]`; any other string falls back to plain indices `0..size-1` (array.py:454-471). A list is NOT parsed (only `str` handled). `label` is the single caption string. | HIGH | "`labels` (str): index-row format `\"0..N\"` or `\"name[0]..name[N]\"`. `label` (str): caption below the row." |
| 10 | `ticks` (count vs spacing) | NumberLine | L778 | Is it a count or a spacing? Default unstated | `ticks` = **integer COUNT** of tick marks (1..1000, E1454 over). Default = `max-min+1` for integer domains, else `11` (numberline.py:115-139). `ticks=25` on `[0,24]` → 25 ticks at 0,1,...,24. | HIGH | "`ticks` (int): number of tick marks (1..1000). Default: span+1 for integer domains, else 11." |
| 11 | `polygons` | Plane2D ctor | L826 | Element format ("Inline batch of closed polygons") | List of either bare vertex lists `[(x,y),...]` OR dicts `{points=[(x,y),...]}`. Auto-closes (E1462 warn) if first≠last (plane2d.py:316-347) | MEDIUM | `polygons=[[(0,0),(1,2),(2,0)]]` (auto-closes); dict form `{points=[...]}` also accepted. |
| 12 | `points` / `segments` | Plane2D ctor | L823, L825 | Element format for batch forms | `points`: `(x,y)` or `(x,y,label)` or `{x,y,label}`. `segments`: `((x1,y1),(x2,y2))` or `{x1,y1,x2,y2}` (plane2d.py:241-314). Off-viewport points warn (E1463, hidden). | MEDIUM | Show element shape for each (mirror the `add_point`/`add_segment` dynamic examples). |
| 13 | `color` (per-series) | MetricPlot | L883 | "`\"auto\"` or CSS color" — what does auto pick? validation? | `"auto"` → indexed Wong/Radix palette by series order (8 colors, metricplot.py:39-48,177). Any other string passed through verbatim as SVG color (no validation). | MEDIUM | "`color`: `\"auto\"` (palette by series index) or any CSS/SVG color string (unvalidated)." |
| 14 | `scale` / `axis` (per-series) | MetricPlot | L883 | Allowed values given but not the E1487 constraint | `axis` ∈ `{"left","right"}`, `scale` ∈ `{"linear","log"}`. **Constraint:** left and right axes can't mix scales inconsistently — violation raises E1487 (`_validate_axis_scales`, metricplot.py:192-193). | MEDIUM | Note the E1487 axis/scale-consistency rule with a valid example. |
| 15 | `data` (Tree segtree) | Tree | L720 | Element type / count limits for `kind="segtree"` | (verify in tree.py) — `data` is the leaf-value list; `show_sum` bool; range derived from len. Doc shows example but no type/limit table. | MEDIUM | Add a Tree param table (data, kind enum, root, range_lo/hi, show_sum). |
| 16 | `vmin`/`vmax` | Matrix | L794-795 | Interaction: must BOTH be set? | If both set → fixed range; if only one set → the OTHER still uses that explicit value, missing side uses data extent (matrix.py:418-433). Floats. | LOW | "Set either/both; unset side uses data min/max." |
| 17 | `xrange`/`yrange` "auto" | MetricPlot | L863-864 | `"auto"` literal vs `[lo,hi]` clear, but degenerate behavior | `[lo,hi]` with `lo==hi` raises E1486; `"auto"` fits to data (metricplot.py:206-217). | LOW | Note E1486 on equal endpoints. |
| 18 | `max_visible` overflow | Stack | L805 | Documented inline well; element form of `items` not | `items`: list of strings, or push accepts `{label, value}` dict (stack.py:147-158). `items` dict form undocumented. | LOW | Mention `items` may hold `{label, value}` dicts, not just strings. |
| 19 | `id` / `label` | animation/diagram env `[...]` | L177, L218 | No type/constraint table for env options themselves | `id` (string, becomes scene HTML id), `label` (string caption). Constraints not stated at env level (label syntax rules at L293 are for `\step`, not env). | LOW | Add a one-row note: env `id`/`label` are free strings; `id` must be unique per document. |
| 20 | `capacity` / `data` | Queue, HashMap, LinkedList, VariableWatch, CodePanel | L888-932 | These 5 primitives have **only an inline example**, no param table | Each has an `ACCEPTED_PARAMS` frozenset not surfaced (e.g. HashMap `capacity`, Queue `capacity`+`data`, VariableWatch `names` list, CodePanel `lines` list). Types/limits/defaults absent. | MEDIUM | Add a minimal param table per primitive (param, type, default, example). |

---

## Prioritized Fix List

**Fix first — actively wrong or unauthorable (CRITICAL):**

1. **L838 `add_region=...`** — replace the `...` placeholder with the real dict form `{polygon=[...], fill="rgba(...)"}`. As written it is impossible to author.
2. **L827 `regions`** — document the dict element format; warn that bare tuples (unlike every other Plane2D element) are silently dropped.
3. **L793 `colorscale`** — correct the false implication of a named-scale menu. Only `"viridis"` exists and other values silently fall back. Either say so or remove the field until more scales ship.
4. **L332 `tooltip=`** — remove or flag as not-implemented. It is a silent no-op and will mislead every author who tries it.

**Fix next — ambiguous geometry/data fields (HIGH):**

5. **L835/L824 `add_line` / `lines`** — clarify the 3-tuple is `(label, slope, intercept)` and that element 0 is a cosmetic label, NOT a parsed equation (`"y=x"` is decorative).
6. **L785/L646 Matrix & Grid `data`** — state flat-OR-nested acceptance, the `rows*cols` length rule (E1422/E1412), and that `...` in examples is illustrative, not literal.
7. **L639 Array `labels`** — clarify it is a *string range-spec* (`"0..7"` / `"name[i]..name[j]"`), not a list, and distinguish from the `label` caption.
8. **L778 NumberLine `ticks`** — state it is a tick COUNT (not spacing) with the integer-domain default.

**Fix when convenient (MEDIUM/LOW):**

9. Add element-format examples for Plane2D `points`, `segments`, `polygons` (#11–12).
10. Add full param tables for the five table-less primitives: Queue, HashMap, LinkedList, VariableWatch, CodePanel, and a proper Tree param table (#15, #20).
11. Document MetricPlot per-series `color`/`scale`/`axis` semantics incl. the E1487 axis-scale constraint (#13–14).
12. Clarify Matrix `vmin`/`vmax` partial-set behavior and MetricPlot range degeneracy (E1486) (#16–17).
13. Add an env-options note for `id`/`label` uniqueness (#19).

**Cross-cutting recommendation:** Several `\apply` ops accept unknown keys silently (scene.py:615) and several Plane2D element parsers `return` silently on malformed input (plane2d.py:250, 294, 300, 313). The doc should warn authors that **malformed field values fail silently rather than erroring**, since this is the single biggest source of "looks fine, renders wrong" bugs for these fields.
