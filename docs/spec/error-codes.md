# Scriba Error Code Reference

> Extracted from `scriba.animation.errors.ERROR_CATALOG`. See `errors.py` for
> the exception classes and `constants.py` for the error numbering scheme.

---

## Detection / Structural Errors (E10xx)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1001 | Unclosed `\begin{animation}` or unbalanced braces/strings/interpolation. | Add matching `\end{animation}` or close the brace/string. |
| E1003 | Nested `\begin{animation}` or `\begin{diagram}` detected. | Remove the inner environment; nesting is not allowed. |
| E1004 | Unknown environment or substory option key. | Check spelling; valid keys are `width`, `height`, `id`, `label`, `layout`, `grid`. |
| E1005 | Invalid option or parameter value. | Check that the value type matches what the key expects. |
| E1006 | Unknown backslash command. | Use one of the 14 recognized commands (see `ruleset.md` section 2). |
| E1007 | Expected opening brace `{` after command. | Add the missing `{`. |
| E1009 | Selector parse error (general). | Check selector syntax against the grammar in `ruleset.md` section 3. |
| E1010 | Selector parse error: expected number, identifier, or specific character. | Fix the token at the reported position. |
| E1011 | Unterminated string literal in selector. | Close the string with a matching quote. |
| E1012 | Unexpected token kind. | Check for typos or misplaced characters in the selector. |
| E1013 | Source exceeds maximum size limit (1 MB). | Split into smaller animations or reduce content. |

## Diagram-Specific Errors (E1050--E1059)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1050 | `\step` is not allowed inside a diagram environment. | Use `\begin{animation}` if you need steps. |
| E1051 | `\shape` must appear before the first `\step`. | Move shape declarations to the prelude. |
| E1052 | Trailing text after `\step` on the same line. | Put `\step` on its own line. |
| E1053 | `\highlight` is not allowed in the prelude. | Move `\highlight` into a `\step` block. |
| E1054 | `\narrate` is not allowed inside a diagram environment. | Remove `\narrate`; diagrams have no narration. |
| E1055 | Duplicate `\narrate` in the same step. | Keep only one `\narrate` per step. |
| E1056 | `\narrate` must be inside a `\step` block. | Move `\narrate` after a `\step`. |

## Parse / Validation Errors (E11xx)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1100 | General parse failure inside animation body. | Check syntax around the reported position. |
| E1102 | Unknown primitive type in `\shape` declaration. | Use a valid type: Array, Grid, DPTable, Graph, Tree, NumberLine, Matrix, Stack, etc. |
| E1103 | **DEPRECATED** — legacy primitive validation mega-bucket. New code raises one of the specific `E14xx` codes below. Retained for backward compat (`scene.annotate` cap and some legacy call sites still use it). | See `E14xx` below. |
| E1109 | Invalid `\recolor` state or missing required state/color parameter. | Use a valid state: idle, current, done, dim, error, good, highlight, path. |
| E1112 | Unknown annotation position. | Use: above, below, left, right, inside. |
| E1113 | Invalid or missing annotation color. | Use: info, warn, good, error, muted, path. |
| E1115 | Selector does not match any addressable part of the target primitive (warning — command silently dropped). | Check selector syntax against the primitive's addressable parts. |
| E1116 | Mutation command (`\apply`, `\highlight`, `\recolor`, `\annotate`) references a shape that was never declared with `\shape`. | Add a `\shape` declaration in the animation prelude before the first `\step`, e.g. `\shape{a}{Array}{size=5}`. |

## Starlark Sandbox Errors (E1150--E1155)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1150 | Starlark parse/syntax error. | Fix the Python syntax inside `\compute{...}`. |
| E1151 | Starlark runtime evaluation failure. | Check for runtime errors (IndexError, KeyError, etc.) in compute code. |
| E1152 | Starlark evaluation timed out (5s cumulative limit across all `\compute` blocks). | Simplify the computation or reduce data size. |
| E1153 | Starlark execution step count exceeded. | Reduce loop iterations or algorithmic complexity. |
| E1154 | Starlark forbidden construct (import, while, class, lambda, etc.). | Use only `for` loops and allowed builtins. |
| E1155 | Starlark memory limit exceeded (64 MB). | Reduce data size or avoid large intermediate structures. |

## Foreach Errors (E1170--E1173)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1170 | `\foreach` nesting depth exceeds maximum (3). | Flatten nested loops or restructure with `\compute`. |
| E1171 | `\foreach` with empty body. | Add at least one command inside the foreach block. |
| E1172 | Unclosed `\foreach`, forbidden command, or `\endforeach` without match. | Ensure every `\foreach` has a matching `\endforeach`. |
| E1173 | `\foreach` iterable validation failure. | Check that the variable/binding exists and the iterable length is within limits. |

## Frame / Cursor Errors (E1180--E1182)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1180 | Animation has >30 frames (warning) or `\cursor` requires at least one target. | Reduce frame count or add cursor targets. |
| E1181 | Animation has >100 frames (hard limit) or `\cursor` requires index. | Split into multiple animations or add the index parameter. |
| E1182 | Invalid `\cursor` prev_state or curr_state value. | Use a valid state name. |

## Substory Errors (E1360--E1368)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1360 | Substory nesting depth exceeds maximum. | Reduce substory nesting. |
| E1361 | Unclosed `\substory` (missing `\endsubstory`). | Add `\endsubstory` to close the block. |
| E1362 | `\substory` must be inside a `\step` block. | Move `\substory` after a `\step`. |
| E1365 | `\endsubstory` without matching `\substory`. | Remove the orphan `\endsubstory` or add the opening `\substory`. |
| E1366 | Substory with zero steps (warning). | Add at least one `\step` inside the substory. |
| E1368 | Non-whitespace text on same line as `\substory`/`\endsubstory`. | Put these commands on their own line. |

## Primitive Parameter Validation (E1400--E1459)

Introduced in v0.5.1 to replace the legacy `E1103` mega-bucket with one
code per `(primitive, validation)` pair. Existing code that caught
`E1103` continues to work because catalog entry `E1103` is retained as a
documented deprecated alias.

### Array (E1400--E1409)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1400 | Array requires `size` or `n` parameter. | Add `size=N` where `1 <= N <= 10000`. |
| E1401 | Array `size` out of range; valid: 1..10000. | Pick an integer between 1 and 10000. |
| E1402 | Array `data` length does not match `size`. | Either drop `data` or ensure `len(data) == size`. |

### Grid (E1410--E1419)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1410 | Grid requires both `rows` and `cols`. | `Grid{g}{rows=R, cols=C}` with `1 <= R,C <= 500`. |
| E1411 | Grid `rows`/`cols` out of range; valid: 1..500. | Pick positive integers no greater than 500. |
| E1412 | Grid `data` length does not match `rows*cols`. | Supply a flat list of length `rows*cols` or a 2D list with `R` rows of `C` items each. |

### Matrix / DPTable (E1420--E1429)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1420 | Matrix requires `rows` and `cols`. | `Matrix{m}{rows=R, cols=C}`. |
| E1421 | Matrix `rows`/`cols` must be a positive integer. | Use a positive integer for both. |
| E1422 | Matrix `data` length does not match `rows*cols`. | Supply a flat list of length `rows*cols`. |
| E1425 | Matrix/DPTable cell count exceeds maximum. | Ensure `rows*cols <= 250000`. |
| E1426 | DPTable requires `n` (1D) or both `rows` and `cols` (2D). | `DPTable{t}{n=10}` or `DPTable{t}{rows=5, cols=5}`. |
| E1427 | DPTable `n` must be a positive integer. | Use a positive integer for `n`. |
| E1428 | DPTable `rows`/`cols` must be a positive integer. | Use positive integers for both. |
| E1429 | DPTable `data` length does not match expected size. | `len(data)` must equal `n` (1D) or `rows*cols` (2D). |

### Tree (E1430--E1439)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1430 | Tree requires `root` parameter. | `Tree{t}{root="A", nodes=[...], edges=[...]}`. |
| E1431 | Tree (kind=segtree) requires `data` parameter. | Supply `data=[v0, v1, ...]` of leaf values. |
| E1432 | Tree (kind=sparse_segtree) requires `range_lo` and `range_hi`. | Specify the valid index bounds. |

### Queue / Stack (E1440--E1449)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1440 | Queue `capacity` must be a positive integer. | Use a positive integer for `capacity`. |
| E1441 | Stack `max_visible` must be a positive integer. | Use a positive integer for `max_visible`. |

### HashMap / NumberLine (E1450--E1459)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1450 | HashMap requires `capacity`. | `HashMap{h}{capacity=N}` where `N >= 1`. |
| E1451 | HashMap `capacity` must be a positive integer. | Use a positive integer for `capacity`. |
| E1452 | NumberLine requires `domain`. | `NumberLine{n}{domain=[min, max]}`. |
| E1453 | NumberLine `domain` must be a two-element [min, max] list. | Supply exactly two numbers. |
| E1454 | NumberLine `ticks` exceeds maximum (1000). | Reduce the tick count. |

### Graph (E1470--E1479)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1470 | Graph requires a non-empty `nodes` list. | `Graph{g}{nodes=[...], edges=[...]}`. |

## Plane2D Errors (E1460--E1466)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1460 | Degenerate viewport (xrange or yrange has equal endpoints). | Use distinct min/max values for the viewport range. |
| E1461 | Degenerate or out-of-viewport line geometry. | Ensure line endpoints are within or intersect the viewport. |
| E1462 | Polygon not closed (auto-closing applied). | Close the polygon explicitly or accept auto-closing. |
| E1463 | Point is outside viewport bounds. | Move the point inside the viewport or expand the range. |
| E1465 | Invalid aspect value. | Use `equal` or `auto`. |
| E1466 | Plane2D element cap reached. | Reduce the number of geometric elements. |

## MetricPlot Errors (E1480--E1487)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1480 | MetricPlot requires at least one series. | Add a series via `\apply`. |
| E1481 | MetricPlot series validation failure. | Check series parameters (name, data, axis). |
| E1483 | Series exceeded maximum point count (truncated). | Reduce the number of data points. |
| E1484 | Log scale: non-positive value clamped. | Use positive values with log scale. |
| E1485 | MetricPlot series data validation error. | Check that data values are numeric and well-formed. |
| E1486 | Degenerate xrange in MetricPlot. | Ensure x-axis min and max differ. |
| E1487 | Same-axis series must share the same scale. | Use consistent scale (linear/log) for series on the same axis. |

## Graph Layout Errors (E1500--E1505)

| Code | Description | Common Fix |
|------|-------------|------------|
| E1500 | Graph layout convergence warning (objective too high). | Simplify the graph or adjust layout parameters. |
| E1501 | Too many nodes for stable layout. | Reduce node count or accept force-layout fallback. |
| E1502 | Too many frames for stable layout. | Reduce frame count or accept force-layout fallback. |
| E1503 | Stable layout fallback triggered. | Informational; the layout engine chose a simpler algorithm. |
| E1504 | layout_lambda out of valid range (clamped). | Use a value within the documented range. |
| E1505 | Invalid seed (must be non-negative integer). | Use a non-negative integer for the seed parameter. |
