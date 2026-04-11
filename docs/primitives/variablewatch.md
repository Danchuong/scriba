# Primitive Spec: `VariableWatch`

> Status: **shipped in v0.5.x** as a data-structure primitive. Extends
> the primitive catalog in
> [`environments.md`](../spec/environments.md) and
> [`ruleset.md`](../spec/ruleset.md) §5.
>
> Source: `scriba/animation/primitives/variablewatch.py`.

---

## 1. Overview

`VariableWatch` renders a two-column name-value table for displaying algorithm
variable states as they change over time. It unlocks:

- Real-time variable inspection alongside data structure animations.
- Showing loop counters, accumulators, flags, and other scalar state during
  algorithm walkthroughs.
- Side-by-side "watch window" displays similar to IDE debuggers.

Each variable row is independently addressable and state-colorable. Values
default to `"----"` (uninitialized) until explicitly set.

---

## 2. Shape declaration

```latex
\shape{vars}{VariableWatch}{
  names=["i", "j", "total", "found"],
  label="Variables"
}
```

### 2.1 Required parameters

| Parameter | Type             | Description                                          |
|-----------|------------------|------------------------------------------------------|
| `names`   | list of strings  | Variable names to display. Each must match `[A-Za-z_]\w*`. Also accepts a comma-separated string (e.g. `"i, j, total"`). |

### 2.2 Optional parameters

| Parameter | Type   | Default | Description                                    |
|-----------|--------|---------|------------------------------------------------|
| `label`   | string | none    | Caption text rendered below the table.          |

---

## 3. Addressable parts (selectors)

| Selector             | Addresses                                             |
|----------------------|-------------------------------------------------------|
| `vars`               | The entire variable watch (whole-shape target)        |
| `vars.var[name]`     | Variable row by name (e.g. `vars.var[i]`, `vars.var[total]`). The name must match one of the declared variable names. |
| `vars.all`           | All variable rows.                                    |

Variable names are used directly as selector keys -- not numeric indices.
`vars.var[x]` where `x` is not in the declared `names` list is rejected by
the selector validator.

---

## 4. Apply commands

### 4.1 Set a single variable value

```latex
\apply{vars.var[i]}{value=3}
```

Sets the display value of variable `i` to `"3"`. The value column auto-widens
to fit the longest displayed value (minimum 100px).

### 4.2 Bulk set via whole-shape apply

```latex
\apply{vars}{i=0, j=5, total=0}
```

Sets multiple variables at once by passing variable names as parameter keys.
Only variables matching declared names are updated.

### 4.3 Persistence

Value assignments are **persistent** -- they carry forward to later frames per
base spec SS3.5 semantics.

---

## 5. Semantic states

Standard SS9.2 state classes are applied to individual variable row `<g>`
elements:

```latex
\recolor{vars.var[i]}{state=current}    % highlight the "i" row
\recolor{vars.all}{state=dim}           % dim all variables
\highlight{vars.var[total]}             % ephemeral highlight on "total"
```

The `all` selector propagates to individual rows: if a variable has no specific
state override and `all` is set to a non-idle state, the variable inherits that
state.

| State       | Visual effect                                          |
|-------------|--------------------------------------------------------|
| `idle`      | Default: muted name text, normal value text            |
| `current`   | Value cell fill #0072B2 (Wong blue), white text        |
| `done`      | Value cell fill #009E73 (Wong green), white text       |
| `dim`       | Opacity 0.35                                           |
| `error`     | Value cell fill #D55E00 (Wong vermillion)              |
| `good`      | Value cell fill #009E73 alt tone                       |
| `highlight` | Gold border #F0E442, 3px dashed (ephemeral)            |

Only the value column (right) changes fill with state. The name column (left)
always uses the theme's muted text color.

---

## 6. Visual conventions

The variable watch is rendered as a bordered two-column table:

```
+-----------+-----------+
| i         |    0      |
+-----------+-----------+
| j         |    5      |
+-----------+-----------+
| total     |   42      |  <-- state=current (highlighted)
+-----------+-----------+
| found     |  true     |
+-----------+-----------+
       Variables
```

- **Name column**: left column with variable names, left-aligned (8px indent),
  muted text at 12px. Width scales with longest variable name (minimum 100px).
- **Value column**: right column with variable values, center-aligned, 13px
  font. Width auto-expands from longest value (minimum 100px).
- **Row height**: 40px per variable.
- **Dividers**: a vertical line separates name and value columns; horizontal
  lines separate rows (except above the first row).
- **Outer border**: 1px border with 4px corner radius around the entire table.
- **Empty state**: if `names` is empty, renders a dashed-border placeholder
  with "no variables" text.
- **Default value**: unset variables display `"----"` until assigned.

---

## 7. Example

```latex
\begin{animation}[id=binary-search-vars]
\shape{vars}{VariableWatch}{
  names=["lo", "hi", "mid", "result"],
  label="Binary Search"
}

\step
\apply{vars}{lo=0, hi=9, result="----"}
\recolor{vars.var[lo]}{state=current}
\recolor{vars.var[hi]}{state=current}
\narrate{Initialize search bounds: lo=0, hi=9.}

\step
\apply{vars.var[mid]}{value=4}
\recolor{vars.all}{state=idle}
\recolor{vars.var[mid]}{state=current}
\narrate{Compute mid = (0 + 9) / 2 = 4.}

\step
\apply{vars}{lo=5, mid=7}
\recolor{vars.var[lo]}{state=current}
\recolor{vars.var[mid]}{state=current}
\narrate{Target is larger. Update lo=5, recompute mid=7.}

\step
\apply{vars.var[result]}{value=7}
\recolor{vars.all}{state=idle}
\recolor{vars.var[result]}{state=done}
\narrate{Found target at index 7.}
\end{animation}
```

---

## 8. Error codes

`VariableWatch` has no primitive-specific error codes. Validation goes
through the shared parse/selector paths:

- Missing or empty `names` list — emits a `UserWarning` at shape
  construction time (the shape still renders with a placeholder).
- Unknown variable name in a selector (`vars.var[x]` where `x` is not
  in `names`) — rejected by the selector validator per the shared
  `E1009`/`E1010` selector-parse path. See
  [`error-codes.md`](../spec/error-codes.md).
- Unknown `\apply` parameter keys (names not in `names`) are silently
  ignored during bulk apply.

---

## 9. Notes

- `names` may be a list (`names=["i", "j"]`) or a comma-separated
  string (`names="i, j"`). The primitive normalizes both forms.
- Values are stored as display strings; the primitive calls `str(...)`
  on any numeric value passed through `\apply`.
- Uninitialized variables display `"----"` until explicitly set.
- Column widths scale automatically from the longest variable name and
  the longest value currently bound.
