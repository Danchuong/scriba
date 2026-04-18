# User-Facing Docs Audit

## Summary

Audit covers: `docs/guides/how-to-animate-dp.md`, `docs/guides/tex-plugin.md`, `docs/tutorial/getting-started.md`, and all 12 cookbook entries. The most serious issues are (1) a wrong parameter name (`vars=` vs `names=`) in cookbook-10 that will trigger E1114 under strict mode, (2) cookbook-03, -04, -05, -06, -07, -08 containing legacy prose that describes a D2/`@compute`/`apply_tag`/`match event.type` architecture that no longer matches the current codebase, (3) the tutorial CLI table documents `--debug` as a flag that does not exist in `render.py`, and (4) `tex-plugin.md` references three non-existent files. Coverage gaps and broken xrefs are also catalogued.

---

## Guides findings

### `docs/guides/how-to-animate-dp.md`

**[LOW] Line 17 — `Array` shape param `size=5` is correct.**
`Array.ACCEPTED_PARAMS` includes `"size"`. No issue.

**[LOW] Line 88 — `DPTable` 2D cell address syntax `dp.cell[r][c]` correct.**
`DPTable.ACCEPTED_PARAMS` includes `"rows"`, `"cols"`. The tip on line 87 (`\shape{dp}{DPTable}{rows=N, cols=M, ...}`) matches the frozenset exactly.

**[LOW] Line 44 — `\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[1]"}` is current syntax.**
`ReannotateCommand` accepts `color` and `arrow_from`. Correct.

**[LOW] Line 27 — `\annotate` `color=good` is accepted.**
`AnnotateCommand` sets `color` from `cmd.color or "info"`. `"good"` is a valid annotation color per `VALID_ANNOTATION_COLORS`. Correct.

**Overall: no defects found in `how-to-animate-dp.md`.**

---

### `docs/guides/tex-plugin.md`

This file is a Wave-2 design document, not a how-to guide. It is misclassified under `docs/guides/` but is not user-facing instructions so most of its content is out of scope for a runnable-accuracy audit. However:

**[HIGH] Lines 362, 443 — references `04-packaging.md` (bare filename, no path).**
Neither `docs/04-packaging.md` nor any `04-packaging.md` exists in the repository. The file is never created. Any author following the cross-reference link will 404.

**[HIGH] Line 606 — references `05-migration.md` (bare filename).**
Does not exist anywhere in `docs/`. Same broken-xref class.

**[MED] Line 3 — references `07-open-questions.md` (bare filename).**
Does not exist. Also references it as "file an entry in `07-open-questions.md`" — the authoring workflow breaks if authors follow this instruction.

**[MED] Lines 131, 322, 590, etc. — repeatedly references `01-architecture.md` with a relative path `../spec/architecture.md`.**
`docs/spec/architecture.md` exists (confirmed). These xrefs are valid.

**[LOW] This file is titled `02 — scriba.tex plugin` suggesting it is document number 2 in a numbered series, but no `01-*.md` sibling exists in `docs/guides/`.**
The numbering convention implies a series that does not exist in `guides/`.

---

## Tutorial findings

### `docs/tutorial/getting-started.md`

**[CRITICAL] Lines 576–587 — CLI table includes `--debug` / `SCRIBA_DEBUG=1` as a flag, but `--debug` is not registered in `render.py`.**
`render.py` parses `SCRIBA_DEBUG` from the environment (`os.environ.get("SCRIBA_DEBUG")` at line 412) but never adds a `--debug` argparse argument. The tutorial table entry reads:

```
| `--debug` / `SCRIBA_DEBUG=1` | Enable verbose debug output (stack traces, intermediate state). Set the env var or pass the flag. |
```

The env-var half works. The `--debug` flag half does not — passing `python render.py input.tex --debug` produces an `unrecognized arguments: --debug` error. **Severity: CRITICAL** because a beginner will copy this verbatim and get an immediate CLI error.

**[MED] Lines 506–511 — examples directory cross-references.**
The tutorial lists `quickstart/hello.tex`, `quickstart/binary_search.tex`, `algorithms/dp/frog.tex`, `algorithms/graph/dijkstra.tex`, and `primitives/diagram.tex` as example files. All five exist under `examples/` (confirmed via glob). These xrefs are valid.

**[MED] Line 499 — `examples/primitives/substory.tex` referenced.**
Exists (confirmed). Valid.

**[LOW] Line 9 — `spec/tex-ruleset.md` link.**
`docs/spec/tex-ruleset.md` exists. Valid.

**[LOW] Lines 381–382 — `spec/ruleset.md §2.1` referenced.**
`docs/spec/ruleset.md` exists. Valid.

**[LOW] Line 513 — claims Scriba ships "16 primitive types".**
Counting the primitive Python files: `array`, `grid`, `dptable`, `graph`, `graph_layout_stable`, `tree`, `numberline`, `matrix`, `stack`, `plane2d`, `metricplot`, `codepanel`, `hashmap`, `linkedlist`, `queue`, `variablewatch` = 16. Count matches. But `graph_layout_stable` is presented as a variant of `Graph` ("`Graph layout=stable`") in the table at line 540, not as a separate type. The count is technically correct but the grouping in the table may confuse authors who look for a 17th shape.

**[LOW] Lines 592–614 — Library API example uses `AnimationRenderer()` with no arguments.**
`AnimationRenderer` constructor in `scriba/animation/renderer.py` should be checked; this is out of scope for this audit pass but warrants a targeted check.

---

## Cookbook findings

### `01-small-multiples`, `02-side-by-side` — `\begin{diagram}` examples

These contain only `\shape` and `\recolor` commands which match current primitives. No issues found.

### `03-animated-bfs/input.md` — **[HIGH] Stale architecture prose**

The `.tex` source block at lines 9–33 uses current `\begin{animation}` / `\step` / `\narrate` / `\recolor` / `\highlight` syntax. **That block is correct and would compile today.**

However, the explanatory prose at lines 39–115 describes an entirely different, superseded architecture:

- Line 39: "L1 parser reads `scene { ... }` block" — the current parser uses `\begin{animation}`, not a `scene {}` block. The `scene {}` syntax does not exist in any current source file.
- Line 44: "**`d2` subprocess** render ra 1 SVG master" — `d2` is not used; the current renderer emits SVG directly via Python primitives.
- Lines 45–46: `d2-step-N` class-stamping, `<figure class="scriba-widget">` with a `scriba-steps.js` — none of these exist in the current runtime.
- Lines 51–109: The "Generated D2 source" block uses D2 syntax (`vars: { d2-config: {...} }`, `steps: {...}`) that is entirely legacy and would mislead authors into thinking they can write D2 directly.

**The `.tex` source block is correct; the explanation below it describes a different, pre-Wave-8 system.** Authors reading the "What happens at compile time" section will have a false mental model.

### `04-segment-tree-query/input.md`, `05-sparse-segtree-lazy/input.md`, `07-swap-game/input.md`, `08-monkey-apples/input.md` — **[HIGH] Legacy `@compute` / `apply_tag` prose**

These files repeatedly reference:
- `@compute` block syntax (e.g., `05/input.md` line 5, 163–166, 189) — the current syntax is `\compute{...}`, not `@compute`.
- `apply_tag` directive (e.g., `06/input.md` line 127, 156; `05/input.md` line 163) — no such directive exists. The current command is `\apply`.
- `scene` / `step` / `narrate` in prose descriptions using old names (e.g., `06/input.md` line 127: "editorial script (`scene`, `step`, `narrate`, `apply_tag`, `recolor`, ...)").

These are in explanatory prose sections, not in the `.tex` example blocks. The actual `.tex` blocks in these files use current syntax. But a new author reading the explanatory text will believe `@compute`, `apply_tag`, and `scene {}` are valid directives and will waste time debugging E1xxx errors.

### `06-frog1-dp/input.md` — **[HIGH] `match event.type` directive does not exist**

Line 136–148 describes a `match event.type { ... }` directive as "compile-time unroll":

```
`match event.type { ... }` là directive mới giới thiệu trong example này.
```

No such directive exists in any grammar file (`_grammar_commands.py`, `_grammar_foreach.py`, `_grammar_substory.py`, `grammar.py`, `lexer.py`). The lexer's known command set is: `shape`, `step`, `apply`, `recolor`, `reannotate`, `highlight`, `annotate`, `cursor`, `foreach`, `endforeach`, `substory`, `endsubstory`, `narrate`, `compute`. There is no `match`. This would produce an immediate parse error if an author tried to use it. The `.tex` example block in the same file does not use `match` — only the explanatory prose claims it exists.

### `10-substory-shared-private/input.md` — **[CRITICAL] Wrong parameter name for `VariableWatch`**

Line 30:
```latex
\shape{result}{VariableWatch}{vars=["min","max"], label="result"}
```

`VariableWatch.ACCEPTED_PARAMS` is `frozenset({"names", "label"})`. The parameter is `names=`, not `vars=`. Under Wave E1 strict validation, this will raise `E1114: unknown VariableWatch parameter 'vars'; valid: label, names`. The example will fail to compile.

Correct form:
```latex
\shape{result}{VariableWatch}{names=["min","max"], label="result"}
```

This is confirmed by: `docs/primitives/variablewatch.md` line 31 and `docs/SCRIBA-TEX-REFERENCE.md` line 592, both of which correctly use `names=`.

### `11-loop-to-step-manual-unroll.md` — **[MED] Stack `ACCEPTED_PARAMS` gap**

Line 61:
```latex
\shape{s}{Stack}{orientation="horizontal", max_visible=6, label="mono-stack (indices)"}
```

`Stack` has no `ACCEPTED_PARAMS` frozenset defined (the grep returns no match; the class inherits `frozenset()` from `PrimitiveBase`). The base class `_validate_accepted_params` only runs when `ACCEPTED_PARAMS` is non-empty (line 203 of `base.py`: `if self.ACCEPTED_PARAMS:`). So `orientation`, `max_visible`, and `label` are accepted silently — they are consumed in `Stack.__init__`. The example will compile. **However**, this means Stack accepts any unknown parameter silently without E1114, which contradicts the Wave E1 strict-mode guarantee. This is a code gap, not a doc gap per se, but the tutorial's claim (getting-started.md) that all primitives raise E1114 on unknown params is false for Stack.

### `12-foreach-apply-dp-table.md` — **[LOW] Minor interpolation warning claim is imprecise**

Lines 36–38 state:
> "The parser does **not** warn when a bare identifier inside a selector matches the foreach variable name. The wrong form silently produces a `UserWarning` at runtime and leaves cells unchanged."

`scene.py` `_substitute_body` does not emit a `UserWarning` — it silently does string substitution. A bare `dp.cell[i]` with no `${}` will not match the `InterpolationRef` path and will be treated as a literal string selector `"i"`. The cell will be addressed as if the user wrote `dp.cell["i"]`, which resolves to a new target silently rather than producing a warning. The claim that a `UserWarning` is raised is inaccurate.

### `HARD-TO-DISPLAY.md` — No accuracy issues. Content is editorial/roadmap, not directive reference.

### `HARD-TO-DISPLAY-COVERAGE.md` — Not read (filename confirmed to exist). Scope is roadmap analysis, not user instruction.

---

## Coverage gaps (features in primitives without guides)

The following primitives have dedicated docs under `docs/primitives/` but **no how-to guide** in `docs/guides/`:

| Primitive | Primitive doc | Guide |
|---|---|---|
| `Stack` | `docs/primitives/stack.md` | None |
| `Queue` | `docs/primitives/queue.md` | None |
| `LinkedList` | `docs/primitives/linkedlist.md` | None |
| `HashMap` | `docs/primitives/hashmap.md` | None |
| `CodePanel` | `docs/primitives/codepanel.md` | None |
| `VariableWatch` | `docs/primitives/variablewatch.md` | None |
| `MetricPlot` | `docs/primitives/metricplot.md` | None |
| `Plane2D` | `docs/primitives/plane2d.md` | None |
| `NumberLine` | `docs/primitives/numberline.md` | None |
| `Matrix` / `Heatmap` | `docs/primitives/matrix.md` | None |

The getting-started tutorial lists all 16 primitives (line 519–551) but only `Array`, `DPTable`, `Graph`, and `Tree` appear in how-to guides (`how-to-animate-dp.md`, `how-to-animate-graphs.md`).

`\compute` + `\foreach` are covered by cookbook recipe 12 and partially by the tutorial §7, but there is no standalone guide for the Starlark compute feature.

`\cursor` command is documented in the tutorial (§8) but has no standalone guide.

`\substory` has tutorial coverage (§11) and cookbook recipe 10, which is adequate.

---

## Stale / removed feature docs

**[HIGH] `docs/cookbook/03-animated-bfs/input.md` — D2 pipeline description (lines 39–115).**
The D2-subprocess architecture described is fully removed. No file in `scriba/animation/` imports or references D2. The `scene {}` block syntax, `d2-step-N` class stamping, and `scriba-steps.js` are all superseded.

**[HIGH] `docs/cookbook/05-sparse-segtree-lazy/input.md`, `06-frog1-dp/input.md`, `07-swap-game/input.md`, `08-monkey-apples/input.md` — `@compute` / `apply_tag` terminology.**
These terms describe an older API surface. `@compute` → `\compute{...}`. `apply_tag` → `\apply`. Authors who pattern-match off the prose will write broken `.tex`.

**[HIGH] `docs/cookbook/06-frog1-dp/input.md` lines 136–148 — `match event.type` directive.**
Documented as a real directive; does not exist at all.

**[MED] `docs/guides/tex-plugin.md` — document is Wave-2 spec, not a current user guide.**
Its title says "02 — `scriba.tex` plugin" which suggests it is a numbered spec document accidentally placed in `guides/`. The content is correct architecture-level description but is not user-facing instruction. It should live in `docs/spec/` or `docs/archive/`.

---

## Broken xrefs

| Location | Broken link | Status |
|---|---|---|
| `docs/guides/tex-plugin.md` line 362 | `04-packaging.md` (bare, no path) | File does not exist anywhere |
| `docs/guides/tex-plugin.md` line 443 | `04-packaging.md` (bare, no path) | File does not exist anywhere |
| `docs/guides/tex-plugin.md` line 606 | `05-migration.md` (bare, no path) | File does not exist anywhere |
| `docs/guides/tex-plugin.md` line 3 | `07-open-questions.md` (bare, no path) | File does not exist anywhere |
| `docs/tutorial/getting-started.md` line 505 | `spec/ruleset.md` | EXISTS — valid |
| `docs/tutorial/getting-started.md` line 512 | `guides/how-to-use-diagrams.md` | EXISTS — valid |
| `docs/guides/how-to-animate-dp.md` line 95 | `how-to-animate-graphs.md` | EXISTS — valid |
| `docs/guides/how-to-animate-dp.md` line 96 | `how-to-debug-errors.md` | EXISTS — valid |
| `docs/cookbook/10-substory-shared-private/input.md` line 163 | `spec/ruleset.md §7.2` | `spec/ruleset.md` EXISTS; §7.2 not verified |
| `docs/cookbook/11-loop-to-step-manual-unroll.md` line 141 | `ruleset.md §2.1` | `spec/ruleset.md` EXISTS |
| `docs/cookbook/12-foreach-apply-dp-table.md` line 193 | `SCRIBA-TEX-REFERENCE.md §5.11` | `docs/SCRIBA-TEX-REFERENCE.md` EXISTS |

Four xrefs in `tex-plugin.md` are hard broken (files do not exist). All guide-to-guide links within `docs/guides/` are valid. All `examples/` paths listed in the tutorial exist.

---

## Recommended actions

**Priority 1 — Fix before any public release**

1. **[CRITICAL] `docs/tutorial/getting-started.md` line 587** — Remove `--debug` from the CLI table, or add a `--debug` argparse argument to `render.py`. The env-var `SCRIBA_DEBUG=1` works; the flag does not.

2. **[CRITICAL] `docs/cookbook/10-substory-shared-private/input.md` line 30** — Change `vars=["min","max"]` to `names=["min","max"]` in the `\shape{result}{VariableWatch}{...}` call.

3. **[HIGH] `docs/cookbook/06-frog1-dp/input.md` lines 136–148** — Delete or clearly mark the `match event.type` section as describing a proposed future directive. It does not exist today and will confuse authors.

**Priority 2 — Fix before sharing cookbook with external authors**

4. **[HIGH] `docs/cookbook/03-animated-bfs/input.md` lines 39–115** — Replace the "What happens at compile time" and "Generated D2 source" sections with an accurate description of the current SVG-primitive pipeline. The `.tex` example block is fine; only the explanatory prose is wrong.

5. **[HIGH] `docs/cookbook/05-sparse-segtree-lazy`, `06-frog1-dp`, `07-swap-game`, `08-monkey-apples` — `input.md` prose sections** — Do a pass to replace `@compute` with `\compute{...}` and `apply_tag` with `\apply` everywhere in explanatory text. These legacy terms appear only in prose, not in the `.tex` code blocks.

6. **[HIGH] `docs/guides/tex-plugin.md`** — Create stub files at `docs/spec/04-packaging.md`, `docs/spec/05-migration.md`, and `docs/spec/07-open-questions.md`, or update the four broken bare-path references in `tex-plugin.md` to point to actual files (or remove the references). Also consider moving `tex-plugin.md` to `docs/spec/02-tex-plugin.md` to match its wave-numbering convention.

**Priority 3 — Documentation completeness**

7. **[MED] Stack primitive `ACCEPTED_PARAMS` gap** — Add `ACCEPTED_PARAMS = frozenset({"orientation", "max_visible", "items", "label"})` to `Stack` so that E1114 fires on unknown params consistently with all other primitives. Update `docs/primitives/stack.md` to document valid params explicitly.

8. **[MED] `docs/cookbook/12-foreach-apply-dp-table.md` line 37** — Correct the claim that a `UserWarning` is emitted for bare `i` in a selector. Actual behavior is silent wrong-target addressing with no warning.

9. **[LOW] Coverage gaps** — Write at minimum a one-page how-to for `Stack`, `Queue`, `HashMap`, `LinkedList`, and `VariableWatch` since these are the most likely primitives a new author will reach for after Array/Graph. `MetricPlot`, `Plane2D`, `CodePanel` are advanced and can wait.
