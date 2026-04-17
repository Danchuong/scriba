# Report 3 — Documentation Coverage

## Command Coverage Table

| Command | In parser | In SCRIBA-TEX-REFERENCE | Cookbook recipe? | Status |
|---|---|---|---|---|
| `\shape` | Yes | Yes §5.1 | Yes (all recipes) | OK |
| `\compute` | Yes | Yes §5.2 | Yes | OK |
| `\step` | Yes | Yes §5.3 | Yes | OK |
| `\narrate` | Yes | Yes §5.4 | Yes | OK |
| `\apply` | Yes | Yes §5.5 | Yes | OK |
| `\highlight` | Yes | Yes §5.6 | Implicit only | OK |
| `\recolor` | Yes | Yes §5.7 | Yes | OK |
| `\annotate` | Yes | Yes §5.8 | Yes | OK |
| `\reannotate` | Yes | Yes §5.9 | Partial | OK |
| `\cursor` | Yes | Yes §5.10 | Yes | OK |
| `\foreach` | Yes | Yes §5.11 | Yes | OK |
| `\endforeach` | Yes (sentinel) | Yes §5.11 | Implicit | OK |
| `\substory` | Yes | Yes §5.12 | **No dedicated recipe** | Missing recipe |
| `\endsubstory` | Yes (sentinel) | Yes §5.12 | None | Missing recipe |
| `\step[label=...]` | Yes (options) | In `spec/ruleset.md §3.1`; absent from main reference | No | Missing from main reference |

All 14 parser commands present in main reference. No stale-doc commands.

## Parameter Coverage — Gaps

- **`\annotate`**: `arrow` (bool) and `ephemeral` accepted by parser (`grammar.py:844–845`) but `SCRIBA-TEX-REFERENCE.md §5.8` lists only `arrow_from=`. The distinction `arrow=true` (bare arrowhead, no source) undocumented.
- **`\recolor`**: deprecated `color=` and `arrow_from=` accepted but reference §5.7 documents only `state=`. No mention of DeprecationWarning.
- **`\substory`**: `id=` and `title=` parsed (`grammar.py:1150–1154`) and mentioned in §5.12 but defaults (title `"Sub-computation"`, auto-id) not stated.
- **`\cursor`**: `prev_state` / `curr_state` defaults (`dim` / `current`) correctly documented.

## Foreach + Variable Docs

**Scoping:** `spec/ruleset.md §6.5` explains prelude vs frame-local `\compute` scope. Foreach variable scoping (added to `_known_bindings`, removed after `\endforeach`) **not documented**. Authors not told `i` invisible outside loop.

**Interpolation syntax:** §5.11 and tutorial §7 correctly show `${i}` inside body. `spec/ruleset.md §3.1` BNF gives formal grammar. Neither doc explains:
- Why `${i}` is required (vs bare `i`) — bare `i` parsed as IDENT string key
- That subscripts on loop variable work: `${arr[i]}` for indexing a compute-bound list

**Common patterns:** §9.5 shows foreach + compute over a list. Tutorial §7 shows range, list literal, computed binding. **Missing:** pattern for `\foreach` + `\apply` with loop variable (e.g. assigning computed values to DP cells), and nested foreach.

## Selector Grammar Docs

**Documented:** `spec/ruleset.md §3` formal BNF for `cell`, `node`, `edge`, `range`, `tick`, `item`, `all`, generic `IDENT "[" idx "]"`. Per-primitive selector table present.

**Gaps:**
- **Wildcards**: no wildcard accessor (`a.cell[*]`) exists; not documented. Authors who try get opaque E1009.
- **Out-of-range behavior**: `spec/ruleset.md §3.1` mentions E1156 for interpolation subscripts, but literal out-of-range (`a.cell[999]`) behavior **not documented** in user-facing reference.
- **Unknown selectors**: `shape.nonexistent` behavior not stated in main reference.
- **`NamedAccessor` generic form**: BNF includes it for Plane2D `.point[i]` etc., but main reference §8 selector table **omits ALL Plane2D selectors** (row shows dashes for every column).

## Error Catalog

**`docs/spec/error-codes.md`** thorough — covers E10xx, E1050–E1059, E11xx, E1150–E1155, E1170–E1173, E1180–E1182, E1360–E1368, E1400–E1459, E1460–E1466, E1470, E1480–E1487, E1500–E1505.

**`spec/ruleset.md §11`** duplicates with slight schema differences.

### Inconsistencies

- `error-codes.md` says Starlark timeout 3s; `ruleset.md §6.4` and reference §14 say 5s. **3s figure stale.**
- `error-codes.md` says memory 128 MB; `ruleset.md §6.4` and reference §14 say 64 MB. **One is wrong.**
- E1182 means "invalid cursor state" in `grammar.py:926` and in `error-codes.md` cursor table, but `ruleset.md §11` lists as "Missing narration (strict mode)." **Code collision.**
- `ruleset.md §11` E1057 labeled "Empty animation (no `\step`) (reserved)" but `grammar.py` actively raises E1057 for commands in substory prelude before first `\step`. **Active error, not reserved.**

## Tutorial Sufficiency

`docs/tutorial/getting-started.md` substantive. Covers environments, `\shape`, `\step`, `\narrate`, `\recolor`, `\annotate`, `\reannotate`, `\apply`, `\foreach` (range + list + computed), `\cursor`, static diagrams, full primitive list.

### Gaps

- `\substory` not covered at all in tutorial
- `\compute` scope rules (global vs frame-local) not explained
- `\step[label=...]` option absent
- **Tutorial §10 ("What does NOT work in diagrams") falsely states `\foreach`/`\compute` requires steps.** Both are valid in diagram prelude per `spec/ruleset.md §2.1`. Factual error.
- Otherwise current with the 14 commands.

## Cookbook Pattern Coverage

| Pattern | Recipe? |
|---|---|
| foreach + recolor with loop var | Yes — §9.5, tutorial §7 |
| foreach + apply with loop var | **No dedicated recipe** |
| substory with shared/private primitives | **No recipe** |
| cross-frame variable persistence (`\compute` prelude) | Partial — `guides/hidden-state-pattern.md` |
| conditional rendering / `\if` | N/A — `\if` doesn't exist; Starlark `if` inside `\compute` not demonstrated |
| annotation with arrow + label | Yes — tutorial §5, §9.3 |
| state transitions across many cells | Partial — 06-frog1, 03-animated-bfs |

## Top 5 Doc Gaps to Fix

1. **Reconcile error catalog** — fix 3s vs 5s timeout, 128 MB vs 64 MB memory, E1182 collision, E1057 reserved-vs-active. Pick one canonical source; auto-generate the other.

2. **Plane2D selector table** — `SCRIBA-TEX-REFERENCE.md §8` shows all dashes for Plane2D, omitting `.point[i]`, `.line[i]`, `.segment[i]`, `.polygon[i]`, `.region[i]`, `.all`. Most glaring per-primitive omission.

3. **Foreach scoping + interpolation rationale** — document loop var scoped to body and invisible to siblings; explain why `${i}` is mandatory (bare `i` is string key); add recipe for `\foreach` + `\apply` (e.g. filling DP table from compute binding).

4. **Tutorial factual error + `\substory` coverage** — fix incorrect claim that `\foreach`/`\compute` don't work in diagrams; add tutorial section for `\substory` covering scope rules (mutations ephemeral, parent state restored) and `title=` / `id=` options.

5. **`\step[label=...]` and `\annotate arrow=`** — add to `SCRIBA-TEX-REFERENCE.md §5.3` and `§5.8` with examples.
