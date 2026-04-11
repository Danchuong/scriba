# Debugging Scriba Animation Errors

This guide explains how to read Scriba error messages and fix the most common mistakes.

---

## Error code format

Every Scriba error has a code like `E1xxx`. The first two digits indicate the category:

| Range | Category |
|-------|----------|
| E1001 -- E1099 | Structural / detection errors (unclosed environments, unknown commands) |
| E1100 -- E1149 | Parse errors (unknown primitives, invalid parameters) |
| E1150 -- E1179 | Starlark sandbox errors (syntax, runtime, timeout) |
| E1170 -- E1179 | `\foreach` errors (nesting, empty body, unclosed) |
| E1180 -- E1199 | Frame / cursor errors (frame count limits, cursor issues) |
| E1360 -- E1369 | Substory errors |
| E1460 -- E1505 | Primitive-specific errors (Plane2D, MetricPlot, Graph layout) |

---

## Top 5 most common errors

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

### E1103: Invalid primitive parameters

**Message**: `Primitive parameter validation error.`

**Cause**: A parameter name or value in the `\shape` declaration does not match what the primitive expects.

**Fix**:
1. Read the detail message -- it names the specific primitive, parameter, and constraint.
2. Check parameter spelling: e.g. `size` not `len`, `rows` not `row`.
3. Check value types: `size=5` (number), `data=[1,2,3]` (list), `label="$a$"` (string).
4. Refer to the primitive's documentation in the [ruleset](../spec/ruleset.md) for the full parameter list.

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
