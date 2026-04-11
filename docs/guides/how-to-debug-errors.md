# Debugging Scriba Animation Errors

This guide explains how to read Scriba error messages and fix the most common mistakes.

---

## Error code format

Every Scriba error has a code like `E1xxx`. The first two digits indicate the category:

| Range | Category |
|-------|----------|
| E1001 -- E1099 | Structural / detection errors (unclosed environments, unknown commands) |
| E1100 -- E1149 | Parse errors (unknown primitives, legacy validation bucket) |
| E1150 -- E1159 | Starlark sandbox errors (syntax, runtime, timeout, memory) |
| E1170 -- E1179 | `\foreach` errors (nesting, empty body, unclosed) |
| E1180 -- E1199 | Frame / cursor errors (frame count limits, cursor issues) |
| E1360 -- E1369 | Substory errors |
| E1400 -- E1459 | Primitive parameter validation (Array, Grid, Matrix/DPTable, Tree, Queue/Stack, HashMap/NumberLine, Graph) |
| E1460 -- E1505 | Primitive-specific errors (Plane2D, MetricPlot, Graph layout) |

---

## Top common errors

### E1001: Unclosed `\begin{animation}`

**Message**: `Unclosed \begin{animation} or unbalanced braces/strings/interpolation.`

**Cause**: Missing `\end{animation}`, or a brace `{` or string `"` was opened but never closed.

**Fix**:
1. Check that every `\begin{animation}` has a matching `\end{animation}`.
2. Count your braces -- every `{` needs a `}`. Pay special attention inside `\compute{...}` blocks where nested braces are common.
3. Check for unclosed string literals in option lists: `[id="hello"]` not `[id="hello]`.

---

### E1006: Unknown command

**Message**: `Unknown backslash command.`

**Cause**: A `\something` command was found that Scriba does not recognize. Usually a typo.

**Fix**: Check spelling. The valid commands inside an animation are:

`\shape`, `\compute`, `\step`, `\narrate`, `\apply`, `\highlight`, `\recolor`, `\annotate`, `\reannotate`, `\cursor`, `\foreach`, `\endforeach`, `\substory`, `\endsubstory`

Common typos: `\colour` (use `\recolor`), `\note` (use `\narrate`), `\color` (use `\recolor`).

---

### E1102: Unknown primitive type

**Message**: `Unknown primitive type in \shape declaration.`

**Cause**: The second argument to `\shape` is not a recognized primitive name.

**Fix**: Check spelling and capitalization. Primitive names are case-sensitive. The valid types are:

`Array`, `Grid`, `DPTable`, `Graph`, `Tree`, `NumberLine`, `Matrix`, `Heatmap`, `Stack`, `Plane2D`, `MetricPlot`, `CodePanel`, `HashMap`, `LinkedList`, `Queue`, `VariableWatch`

Common mistakes: `array` (use `Array`), `Table` (use `DPTable`), `List` (use `LinkedList`).

---

### E1400 -- E1459: Invalid primitive parameters

> **Note:** Before v0.5.1, primitive parameter validation raised a single
> mega-bucket code `E1103`. It is now split into specific codes per
> `(primitive, check)` pair. `E1103` is retained as a documented
> deprecated alias; new code paths raise one of the codes listed below.

**Cause**: A parameter name or value in the `\shape` declaration does not match what the primitive expects.

Common codes:

| Code | Primitive | Meaning |
|------|-----------|---------|
| `E1400` / `E1401` | Array | Missing `size`/`n`, or `size` out of range (1..10000). |
| `E1402` | Array | `data` length does not match `size`. |
| `E1410` / `E1411` | Grid | Missing `rows`/`cols`, or out of range (1..500). |
| `E1412` | Grid | `data` length does not match `rows*cols`. |
| `E1420` / `E1421` / `E1422` | Matrix | Missing dimensions, non-positive, or data size mismatch. |
| `E1425` | Matrix / DPTable | Cell count `rows*cols` exceeds 250000. |
| `E1426`--`E1429` | DPTable | Missing dims, non-positive, or data size mismatch. |
| `E1430`--`E1432` | Tree | Missing `root`, segtree `data`, or sparse segtree range. |
| `E1440` / `E1441` | Queue / Stack | Non-positive `capacity` / `max_visible`. |
| `E1450` / `E1451` | HashMap | Missing or non-positive `capacity`. |
| `E1452`--`E1454` | NumberLine | Missing `domain`, malformed domain, or too many ticks. |
| `E1470` | Graph | Missing or empty `nodes`. |

**Fix**:
1. Read the detail message -- it names the specific primitive, parameter, and constraint.
2. Check parameter spelling: e.g. `size` not `len`, `rows` not `row`.
3. Check value types: `size=5` (number), `data=[1,2,3]` (list), `label="$a$"` (string).
4. Refer to the primitive's documentation in the [ruleset](../spec/ruleset.md) or [error-codes.md](../spec/error-codes.md) for the full parameter list and valid ranges.

---

### E1109: Unknown recolor state

**Message**: `Invalid \recolor state or missing required state/color parameter.`

**Cause**: The `state=` value is not one of the recognized visual states.

**Fix**: Use one of these states:

`idle`, `current`, `done`, `dim`, `good`, `error`, `path`

Common mistakes: `visited` (use `done`), `active` (use `current`), `highlight` (use `good` or `current`).

---

## General debugging tips

1. **Read the full error message.** Scriba errors include the line number and a description. The detail after the code often pinpoints the exact issue.
2. **Check one step at a time.** Comment out steps with `%` and re-run to isolate which step causes the error.
3. **Validate shapes first.** If `\shape` fails, nothing else will work. Get the shape declaration right before adding steps.
4. **Watch for selector typos.** `dp.cell[0]` is valid; `dp.cells[0]` is not. Node names are case-sensitive: `G.node[A]` not `G.node[a]`.

---

## Full error reference

See [docs/spec/error-codes.md](../spec/error-codes.md) for the complete catalog of all error codes and their descriptions.
