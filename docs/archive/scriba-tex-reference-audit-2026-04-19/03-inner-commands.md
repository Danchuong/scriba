# §5 Inner Commands Audit

Audit date: 2026-04-19
Reference lines: 163–417 (`docs/SCRIBA-TEX-REFERENCE.md`)
Implementation files checked:
- `scriba/animation/parser/grammar.py` (dispatcher)
- `scriba/animation/parser/_grammar_commands.py` (parse methods)
- `scriba/animation/parser/_grammar_foreach.py`
- `scriba/animation/parser/_grammar_substory.py`
- `scriba/animation/parser/ast.py` (IR dataclasses)
- `scriba/animation/scene.py` (runtime semantics)
- `scriba/animation/constants.py` (enum sets)
- `scriba/animation/errors.py` (error catalog)

---

## Command-by-Command Verification

### \shape (doc line 165)

Documented signature: `\shape{name}{Type}{params...}`

Actual signature (`grammar.py:529–539`, `ast.py:127–135`):
```
ShapeCommand(line, col, name: str, type_name: str, params: dict[str, ParamValue])
```
Parser: `_parse_shape` reads two brace args then `_read_param_brace`.

Status: **PASS** — signature matches. Constraint "Name must be unique, match `[a-z][a-zA-Z0-9_]*`" is partially wrong (see Findings).

---

### \compute (doc line 168)

Documented signature: `\compute{...Starlark...}`

Actual signature (`_grammar_compute.py:31–41`, `ast.py:138–143`):
```
ComputeCommand(line, col, source: str)
```

Forbidden list in doc: `while`, `import`, `class`, `lambda`, `try`

Actual forbidden list (`errors.py:E1154`): "import, while, class, lambda, etc." — implementation is in `starlark_worker.py` (AST scan). No discrepancy visible in grammar layer.

Pre-injected builtins list documented: 24 names listed.

Status: **PASS** — signature correct. Builtins list not fully verifiable without reading starlark_worker but no contradicting evidence.

---

### \step (doc line 174)

Documented signature: `\step` with optional `[label=ident]`

Actual signature (`grammar.py:260–264`, `_grammar_tokens.py:345–424`, `ast.py:147–158`):
```
StepCommand(line, col, label: str | None = None)
```
Options parser: only `label` key accepted; unknown key → E1004; invalid value → E1005; duplicate label → E1005; empty label → E1005; trailing text → E1052.

Doc claims: "Unknown key raises `E1004`" ✓ | "Duplicate label raises `E1005`" ✓ | "Trailing non-whitespace raises `E1052`" ✓ | "Empty not allowed — raises `E1005`" ✓

Label regex in doc: `[A-Za-z_][A-Za-z0-9._-]*` — actual validation (`_grammar_tokens.py:402`): `label.replace("-","_").replace(".","_").isidentifier()` — functionally equivalent, allows same character set.

Status: **PASS** — error codes and semantics match.

---

### \narrate (doc line 229)

Documented signature: `\narrate{LaTeX text}`

Actual signature (`_grammar_commands.py:64–66`, `ast.py:162–167`):
```
NarrateCommand(line, col, body: str)
```
Uses `_read_raw_brace_arg` (preserves verbatim whitespace). Forbidden in prelude (E1056), forbidden in diagram (E1054), duplicate in same step (E1055).

Status: **PASS** — matches.

---

### \apply (doc line 232)

Documented signature: `\apply{target}{params...}`
Doc says common params: `value=`, `label=`, `tooltip=`

Actual signature (`_grammar_commands.py:68–76`, `ast.py:171–177`):
```
ApplyCommand(line, col, target: Selector, params: dict[str, ParamValue])
```
Runtime handler (`scene.py:563–586`): explicitly handles `value` and `label`; any other key is stored as `apply_params` and passed to the primitive's `apply_command`.

**`tooltip=` is NOT a documented/implemented standard param.** The word "tooltip" does not appear anywhere in `scene.py`, `_grammar_commands.py`, `ast.py`, or any primitive. It appears only in the reference doc.

Status: **FAIL — HIGH** — `tooltip=` listed as a common param does not exist in any implementation layer. It would not error (unknown keys pass through as `apply_params`) but the primitive would silently ignore it.

---

### \highlight (doc line 235)

Documented signature: `\highlight{target}`
Doc claims: "Ephemeral focus marker. Cleared at next `\step`."

Actual signature (`_grammar_commands.py:78–86`, `ast.py:181–186`):
```
HighlightCommand(line, col, target: Selector)
```
Runtime (`scene.py:7`, `scene.py:207`, `scene.py:633–644`): `\highlight` is confirmed ephemeral — `self.highlights.clear()` runs at the top of every `apply_frame` call, before commands are applied.

Note: `\unhighlight` does not exist in any parser file, grammar dispatcher, AST, or scene module. The audit prompt mentioned it; it is NOT a real command.

Status: **PASS** — signature and ephemeral semantics match.

---

### \recolor (doc line 237)

Documented signature: `\recolor{target}{state=...}`
Documented states: `idle`, `current`, `done`, `dim`, `error`, `good`, `path`, `hidden`

Actual states (`constants.py:27–32`, `VALID_STATES`):
```python
frozenset({"idle", "current", "done", "dim", "error", "good", "highlight", "path", "hidden"})
```

**The doc omits `highlight` from the valid states list.** `highlight` IS a valid recolor state (used by Stack, Graph, Plane2D primitives via `effective_state = "highlight"`).

Actual signature (`_grammar_commands.py:88–161`, `ast.py:189–198`):
```
RecolorCommand(line, col, target: Selector, state: str | None, annotation_color: str | None, annotation_from: str | None)
```
Parser: `state` is now optional (can be omitted if `color=` is present, though `color=` is deprecated). At least one of `state` or `color` must be present (E1109).

The doc shows only `state=` as the param, not mentioning the deprecated `color=`/`arrow_from=` passthrough — acceptable omission for deprecated params, but the missing `highlight` state is an active error.

Status: **FAIL — HIGH** — `highlight` omitted from the documented states list.

---

### \annotate (doc line 241)

Documented signature: `\annotate{target}{params...}`

Parameters table documented: `label`, `position`, `color`, `ephemeral`, `arrow`, `arrow_from`

Actual signature (`_grammar_commands.py:208–256`, `ast.py:212–224`):
```
AnnotateCommand(line, col, target: Selector, label: str | None = None,
    position: str = "above", color: str = "info", arrow: bool = False,
    ephemeral: bool = False, arrow_from: Selector | None = None)
```

Param-by-param:
- `label`: doc says default `""`, actual default `None` — label is omitted from output if not supplied, not rendered as empty string. **MED mismatch** (default type differs: `None` vs `""`).
- `position`: doc default `above` ✓, valid values: `above`, `below`, `left`, `right`, `inside` ✓ (`constants.py:40–42`)
- `color`: doc default `info` ✓, valid: `info`, `warn`, `good`, `error`, `muted`, `path` ✓ (`constants.py:35–37`)
- `ephemeral`: doc default `false` ✓
- `arrow`: doc default `false` ✓
- `arrow_from`: doc says type "selector" ✓ (parsed via `parse_selector`)

Error codes used: E1112 (unknown position), E1113 (invalid color) — both exist in catalog ✓

Examples in doc: all syntactically valid; selectors like `a.cell[3]`, `dp.cell[2][2]` parse correctly.

Status: **PASS** with LOW note on `label` default (`None` vs `""`).

---

### \reannotate (doc line 312)

Documented signature: `\reannotate{target}{color=..., arrow_from=...}`
Doc says: "Recolors existing annotations. Persistent."

Actual signature (`_grammar_commands.py:163–206`, `ast.py:201–209`):
```
ReannotateCommand(target: Selector | str, color: str, arrow_from: str | None = None, line: int = 0, col: int = 0)
```

**`color` is REQUIRED in the implementation** (`_grammar_commands.py:168–176`): missing `color` raises E1113. The doc does not flag `color` as required — the signature presentation `{color=..., arrow_from=...}` implies both are optional.

`arrow_from` is optional ✓.

Status: **FAIL — HIGH** — `color` is a required parameter; doc presents it as optional/positional without marking it required.

---

### \cursor (doc line 315)

Documented signature: `\cursor{targets}{index, prev_state=..., curr_state=...}`
Doc says defaults: `prev→dim`, `curr→current`

Actual signature (`_grammar_commands.py:258–341`, `ast.py:238–251`):
```
CursorCommand(targets: tuple[str, ...], index: int | str,
    prev_state: str = "dim", curr_state: str = "current",
    line: int = 0, col: int = 0)
```

Defaults match ✓. Error codes: E1180 (no targets or <1 target), E1181 (missing index), E1182 (invalid prev/curr state) — all in catalog ✓.

Doc example: `\cursor{a.cell, dp.cell}{3}` — valid ✓ (comma-separated targets, integer index).

`index` can also be an interpolation string like `${i}` ✓ (`_grammar_commands.py:297–302`).

Status: **PASS** — signature and defaults match.

---

### \foreach (doc line 321)

Documented signature: `\foreach{var}{iterable}...\endforeach`
Iterables documented: `0..4`, `[1,3,5]`, `${computed_list}`

Actual signature (`_grammar_foreach.py:51–204`, `ast.py:227–235`):
```
ForeachCommand(variable: str, iterable_raw: str, body: tuple[MutationCommand, ...], line: int = 0, col: int = 0)
```

Max depth: doc says 3 ✓ (`_MAX_FOREACH_DEPTH = 3` in `_grammar_foreach.py:21`).

Allowed commands inside body per doc: `\apply`, `\highlight`, `\recolor`, `\reannotate`, `\annotate`, `\cursor`, and nested `\foreach`.
Actual allowed (`_grammar_foreach.py:150–169`): `endforeach`, `recolor`, `reannotate`, `apply`, `highlight`, `annotate`, `cursor`, `foreach` ✓.

Doc says `\step`, `\shape`, `\substory`, `\narrate` not allowed ✓ — code raises E1172 for `step`, `shape`, `substory`, `endsubstory` (`_grammar_foreach.py:171–178`). Note: `\narrate` is not in the explicit blocklist but would fall through to the "unknown command" E1006 handler — functionally blocked, but not with E1172.

Error codes: E1170 (depth), E1171 (empty body), E1172 (unclosed/forbidden/stray endforeach), E1173 (iterable validation) — all in catalog ✓.

Status: **PASS** — minor LOW note: `\narrate` forbidden inside foreach, but blocked via E1006 rather than E1172 as the other forbidden commands are.

---

### \substory (doc line 406)

Documented signature: `\substory[title="..."]...\endsubstory`

Actual signature (`_grammar_substory.py:75–198`, `ast.py:306–316`):
```
SubstoryBlock(line, col, title: str = "Sub-computation",
    substory_id: str | None = None,
    shapes: tuple[ShapeCommand, ...] = (),
    compute: tuple[ComputeCommand, ...] = (),
    frames: tuple[FrameIR, ...] = ())
```

Options parser accepts keys: `title`, `id` (`VALID_SUBSTORY_OPTION_KEYS` in `constants.py:50–52`).

**Doc shows only `[title="..."]` bracket option — does not document `id=` option.** The `id=` option is valid and accepted by the parser; it controls the `substory_id` for HTML rendering.

Max depth: doc says 3 ✓ (`_MAX_SUBSTORY_DEPTH = 3` in `_grammar_substory.py:30`).

Error codes: E1360 (depth), E1361 (unclosed), E1362 (in prelude), E1365 (stray endsubstory), E1366 (empty substory warning), E1368 (trailing text) — all in catalog ✓.

Status: **FAIL — MED** — `id=` option undocumented.

---

## Findings

### [HIGH] \apply `tooltip=` param does not exist
- **Doc line 233**: Lists `tooltip=` as a common parameter for `\apply`.
- **Reality**: `tooltip` is not handled in `scene.py:_apply_apply`, not present in any primitive `apply_command`, and the word does not appear in any Python source file.
- **Effect**: An author writing `\apply{cell}{tooltip="hint"}` would not get an error (unknown keys silently pass to `apply_params`), but the tooltip would never render. This is a broken example in spirit.
- **File ref**: `scriba/animation/scene.py:563–586`

### [HIGH] \recolor missing `highlight` state
- **Doc line 239**: States listed as `idle`, `current`, `done`, `dim`, `error`, `good`, `path`, `hidden` — 8 states.
- **Reality**: `VALID_STATES` contains 9 values — `highlight` is missing from the doc list.
- **File ref**: `scriba/animation/constants.py:27–32`

### [HIGH] \reannotate: `color` is required, not optional
- **Doc line 312**: Signature `\reannotate{target}{color=..., arrow_from=...}` implies both are optional.
- **Reality**: Parser raises E1113 if `color` is absent (`_grammar_commands.py:168–176`).
- **Effect**: An author omitting `color` gets a parse error — the documented form `\reannotate{target}{}` would fail.
- **File ref**: `scriba/animation/parser/_grammar_commands.py:168`

### [MED] \substory undocumented `id=` option
- **Doc line 406**: Only shows `[title="..."]`.
- **Reality**: `id=` is a valid bracket option (`constants.py:50–52`; `_grammar_substory.py:124`). It sets the substory's HTML id for rendering.
- **File ref**: `scriba/animation/constants.py:50`

### [MED] \annotate `label` default documented as `""`, actual is `None`
- **Doc line 248**: Default listed as `""` (empty string).
- **Reality**: `ast.py:218` — `label: str | None = None`. An omitted label is `None` in the IR; primitives treat `None` and `""` differently (None means "no label annotation rendered").
- **File ref**: `scriba/animation/parser/ast.py:218`

### [LOW] \foreach: `\narrate` forbidden but via wrong error code
- **Doc line 403**: States `\narrate` is not allowed inside a foreach body.
- **Reality**: Correct, but blocked via E1006 ("unknown command") rather than E1172 ("forbidden command inside foreach") as the other forbidden commands (`\step`, `\shape`, etc.) are.
- **File ref**: `scriba/animation/parser/_grammar_foreach.py:181–188`

### [LOW] \highlight: `\unhighlight` does not exist
- The audit prompt mentions `\unhighlight` as a command to verify. It does not exist anywhere in the codebase — no parser method, no AST node, no dispatch branch. Not documented either. Non-issue in the doc itself; noted for completeness.

---

## Count Check

**Doc claims: 12 inner commands** (section header line 163: "Inner Commands (12 total)")

Actual commands dispatched by `SceneParser._dispatch_command` (`grammar.py:245–356`) and their corresponding parse methods:

| # | Command | AST node |
|---|---------|----------|
| 1 | `\shape` | `ShapeCommand` |
| 2 | `\compute` | `ComputeCommand` |
| 3 | `\step` | `StepCommand` |
| 4 | `\narrate` | `NarrateCommand` |
| 5 | `\apply` | `ApplyCommand` |
| 6 | `\highlight` | `HighlightCommand` |
| 7 | `\recolor` | `RecolorCommand` |
| 8 | `\reannotate` | `ReannotateCommand` |
| 9 | `\annotate` | `AnnotateCommand` |
| 10 | `\cursor` | `CursorCommand` |
| 11 | `\foreach` | `ForeachCommand` |
| 12 | `\substory` | `SubstoryBlock` |

Also recognized (terminator tokens, not stand-alone commands): `\endforeach`, `\endsubstory`.

**Doc count: 12. Actual count: 12. Diff: 0.**

The count is correct. `\endforeach` and `\endsubstory` are not independent commands (they raise errors when encountered outside their respective blocks) and are correctly excluded from the count.

The `_VALID_COMMANDS_LIST` in `grammar.py:362–371` lists 14 names including `\endforeach` and `\endsubstory` — that internal constant is documentation-internal and does not contradict the §5 count.

---

## Coverage Gaps

- **`id=` option for `\substory`**: valid, accepted by parser, not documented (§5.12).
- **`highlight` state for `\recolor`**: valid, accepted by parser, not documented (§5.7).
- **`\apply` custom pass-through params**: The doc rightly mentions `value=`, `label=` as "common" but the `tooltip=` example is wrong. Other primitive-specific params (e.g., `push`, `pop` for Stack; `insert`, `remove` for LinkedList; `add_node`, `remove_node` for Tree) are not in scope for §5 but the false `tooltip=` example could mislead authors.
- **`\reannotate` required-param contract**: Not clearly documented; should say "`color` is required."
- **Deprecated `\recolor {color=, arrow_from=}`**: `_grammar_commands.py:107–138` — these deprecated params emit `DeprecationWarning` at parse time. Not mentioned in §5.7 (acceptable omission for deprecated features, but worth a note).

---

## Verdict

**6/12 commands fully correct** (shape, compute, step, narrate, highlight, cursor).
**3/12 commands have HIGH issues** (apply, recolor, reannotate).
**1/12 has MED issue** (substory — missing `id=` option).
**2/12 have LOW notes only** (annotate label default, foreach narrate error code).

Overall score: **5/10** — three HIGH findings (one phantom param, one missing valid enum value, one required-vs-optional contract inversion) make §5 unsuitable for direct reference without correction.
