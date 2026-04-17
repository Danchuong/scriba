# Report 1 — Grammar / Parser Audit

## 1. Command Inventory

| Command | Required Params | Optional Params | Notes | Parsed In |
|---|---|---|---|---|
| `\shape` | `{name}` `{Type}` | `{key=value,...}` | Type validated against primitive registry at parse time (E1102). Prelude-only, rejected after first `\step` (E1051). | `grammar._parse_shape` |
| `\compute` | `{starlark_body}` | — | Body raw brace-balanced text passed to Starlark subprocess. Static binding extraction best-effort; never fails parse. | `grammar._parse_compute` |
| `\step` | — | `[label=ident]` | Bracket must be on same line. Creates `FrameIR`. `\step` in prelude silently ignored. `\narrate` before first `\step` → E1056. | `grammar._dispatch_command` |
| `\narrate` | `{latex_text}` | — | One per step (E1055 on duplicate). Not allowed in prelude (E1056). LaTeX macros pass through to KaTeX. | `grammar._parse_narrate` |
| `\apply` | `{selector}` `{key=value,...}` | — | Param brace optional (empty dict). `value=`, `label=` well-known; rest stored as `apply_params`. Persistent. | `grammar._parse_apply` |
| `\highlight` | `{selector}` | — | Ephemeral — cleared at each `\step`. Not allowed in prelude (E1053) unless `allow_highlight_in_prelude=True` (diagram). | `grammar._parse_highlight` |
| `\recolor` | `{selector}` `{state=\|color=}` | `arrow_from=` | At least one of `state` / `color` required (E1109). `color=` deprecated; use `\reannotate`. State validated against `VALID_STATES`. Persistent. | `grammar._parse_recolor` |
| `\reannotate` | `{selector}` `{color=...}` | `arrow_from=` | `color` required (E1113). Color validated against `VALID_ANNOTATION_COLORS`. Does not change cell state. | `grammar._parse_reannotate` |
| `\annotate` | `{selector}` | `label=`, `position=`, `color=`, `arrow=`, `ephemeral=`, `arrow_from=` | `position` defaults `above`; `color` defaults `info`. `arrow_from` parsed as a second selector. Persistent by default. | `grammar._parse_annotate` |
| `\cursor` | `{targets}` `{index,...}` | `prev_state=`, `curr_state=` | `targets` comma-separated accessor prefixes. Index = first token of second brace arg. | `grammar._parse_cursor` |
| `\foreach` | `{var}` `{iterable}` `...body...` `\endforeach` | — | Variable must be valid Python ident. Iterable: `lo..hi` range, `${name}` lookup, or `[...]` literal. Max depth 3. Empty body → E1171. | `grammar._parse_foreach` |
| `\substory` | (body) `\endsubstory` | `[title="...", id="..."]` | Must be inside `\step` (E1362). Max depth 3. Zero-step → UserWarning only. State isolated and restored after. | `grammar._parse_substory` |

**Not implemented:** `\let`, `\if`. Conditional logic must use `\compute` Starlark.

## 2. Selector Grammar

```
selector    ::= IDENT ("." accessor)?
accessor    ::= "cell" "[" index "]" ("[" index "]")?
              | "tick" "[" index "]"
              | "item" "[" index "]"
              | "node" "[" node_id "]"
              | "edge" "[" "(" node_id "," node_id ")" "]"
              | "range" "[" index ":" index "]"
              | "all"
              | IDENT ("[" index "]")?   ← generic NamedAccessor
```

**Index resolution:**

- `arr.cell[i]` — bare ident `i` parsed as **string** `"i"` via `_expect_ident()`. NOT treated as variable lookup.
- `arr.cell[${i}]` — creates `InterpolationRef(name="i")`, resolved by `_substitute_body` at `\foreach` expansion time.
- `arr.cell[0]` — Python `int`. Negative indices rejected at parse time (E1010).
- `G.node["A"]` — Python `str`.

**Substitution timing:** `${i}` resolved in `scene._substitute_body` at runtime during `_expand_commands`, not at parse time. Bare `i` silently passes through as the literal string `"i"`.

## 3. Foreach Semantics

**Variable scoping:** Loop variable added to `_known_bindings` during body parse, removed after (`finally` block at line 1102). Static interpolation checker knows the variable exists during body parsing; siblings outside the foreach do not see it.

**Shadowing:** No `\let` exists. If author sets `i` via `\compute{i = 5}` then uses `\foreach{i}{0..3}{...}`, no parse-time conflict. At runtime `_substitute_body` does string replace `${i}` → foreach value; the `\compute` binding in `self.bindings` is unchanged. Two separate namespaces, no error.

**Body command restrictions:** Only `\apply`, `\highlight`, `\recolor`, `\reannotate`, `\annotate`, `\cursor`, and nested `\foreach` allowed. `\step`, `\shape`, `\substory`, `\endsubstory` → E1172. **`\compute` and `\narrate` silently consumed** as non-command tokens (line 1090 `else: self._advance()`) — no error, no IR node.

### The user-reported foreach-`i` bug (path)

1. Author writes `\apply{arr.cell[i]}{...}` inside `\foreach{i}{0..3}`.
2. Selector `arr.cell[i]` passed to `parse_selector`.
3. `_parse_index_expr()` sees `i` is not digit / `$` → falls to `_expect_ident()` → returns string `"i"`.
4. `CellAccessor(indices=("i",))` stored in IR.
5. At runtime, `_substitute_body._sub_index_expr` calls `"i".replace("${i}", val_str)` → no match → `"i"` unchanged.
6. **Result: all iterations target `arr.cell[i]` (literal), not `arr.cell[0]`, etc.**

**Fix:** author must write `arr.cell[${i}]`. Parser does not warn when bare ident inside selector matches the foreach variable name.

## 4. Validation Strength

| Check | Strength |
|---|---|
| Unknown `\command` | Hard error E1006 — but no fuzzy hint despite `suggest_closest` existing |
| Unknown primitive type in `\shape` | Hard error E1102 with fuzzy hint |
| Unknown enum values (`state`, `color`, `position`) | Hard error with fuzzy hint |
| Missing required param (`\reannotate` no `color`) | Hard error E1113 |
| Extra/unknown params in `\apply{}{xyz=1}` | Silently passed to `apply_params`; primitive ignores. No error |
| Selector format | Full parse with error codes (E1009/E1010/E1011) |
| Starlark syntax errors | Surface only at eval time |
| `${name}` without known binding | UserWarning only; suppressible |
| Empty `\foreach` body | Hard error E1171 |
| `\compute` inside `\foreach` body | **Silently consumed** |
| Selector trailing text | Hard error |

## 5. Footguns

1. **Bare identifier vs `${...}` interpolation in selectors.** `arr.cell[i]` and `arr.cell[${i}]` parse differently with no warning when the bare ident matches a known foreach/compute var. Primary source of silent wrong-behavior bugs.

2. **`\compute` inside `\foreach` silently eaten.** Inner token loop at line 1089 (`else: self._advance()`) consumes any non-backslash and unrecognized backslash tokens including `\compute{...}`. Tokens scattered as individuals and silently skipped.

3. **Extra params silently passed to primitives.** `\apply{a.cell[0]}{vlue=5}` produces `apply_params=[{"vlue": 5}]`; primitive ignores it; cell unchanged. No error.

4. **`\annotate` target shape validation is a UserWarning, not error.** `scene._apply_annotate` warns rather than raises on misspelled shape. Renders silently with floating annotation.

5. **`\recolor` selector parsed AFTER param checks.** Bad selector with valid params errors only after param validation; location info points to command token, not selector position.

6. **`\substory` with zero steps is a warning, not error.** Renders nothing; no diagnostic.

7. **`%` inside brace args.** Comments stripped by lexer before token stream. `%` inside `\narrate{...}` survives via character-level extraction (correct, sent to KaTeX). `%` inside selector or token-stream-reconstructed param brace → already stripped by lexer → silent corruption.

8. **Name collision: shape name = command keyword.** A shape named `step` or `apply` accepted by `_parse_shape` (`_read_brace_arg` returns any string). Selectors `step.cell[0]` parse cleanly. Footgun is purely human readability.

9. **`\step` placement inside `\foreach` is hard error (E1172) — correct.** But `\foreach` inside `\substory` is accepted via substory's own dispatch with no doc-level statement about the interaction.
