# Agent 04: Registry Drift (Commands/Selectors/Primitives/Options)

**Score:** 6/10
**Verdict:** needs-work

## Prior fixes verified
- H2, H3 (primitives & selectors missing from §5, §3): PARTIAL
  - H2 RESOLVED: All 16 primitives now in __init__.py registry ✓
  - H3 RESOLVED: All selector tables added to ruleset.md §3 ✓
- C1 (Stack params): PARTIAL — Spec drift unresolved
- M2 (Matrix/Heatmap alias): PRESENT ✓ (`@register_primitive("Matrix", "Heatmap")` + `HeatmapPrimitive = MatrixPrimitive`)
- H2 (§5.2b): DRIFT FOUND

## Critical Findings

**C1: Stack Required Parameters Contradiction**
Spec §5.2 summary: "Stack | (none; all optional)" vs §5.7 table: "`capacity` or `n` (required)". Code matches §5.2 (all optional, no capacity param enforced). Additionally, §5.2 lists non-existent params: `cell_width`, `cell_height`, `gap` — not accepted by Stack.__init__.

**C2: Environment Options Missing from Spec Summary**
Ruleset §1.2 defines 6 keys (width, height, id, label, layout, grid). Code accepts exactly 6. Match ✓. But §1.2 shows scope "both|both|both|both|animation only|diagram only" — `grid` is "diagram only" per spec but grammar.py _try_parse_options() applies to all environments (no differentiation).

## High Findings

**H1: Stack Parameters §5.2 Inconsistency**
§5.2 features list includes `cell_width`, `cell_height`, `gap` but §5.7 table and code both omit them. Code computes `_cell_width` dynamically. Are these deprecated/planned features leaked into spec?

**H2: Heatmap vs Matrix Naming**
Spec uses both "Matrix/Heatmap" (unified) but code structure is clear:
- `@register_primitive("Matrix", "Heatmap")` registers MatrixPrimitive under both names
- Alias: `HeatmapPrimitive = MatrixPrimitive`
- No distinction in behavior. Spec/code align ✓

**H3: MetricPlot Selector Coverage**
Spec §3: "MetricPlot | plot | (whole shape only — series via `\apply` params)"
Code (metricplot.py): Series targeted via frame-level apply params, not selectors. Matches spec ✓

**H4: CodePanel 1-Based vs 0-Based Indexing**
Spec §3: `.line[i]` (no mention of 1-based).
Code (codepanel.py line 43): `_LINE_RE = re.compile(r"^line\[(?P<idx>\d+)\]$")` — accepts any integer, no validation that it's 1-based vs 0-based. Prior audit (M12) noted 1-based is undocumented.

## Medium Findings

**M1: LinkedList Link Selector Off-by-One Potential**
Spec §3: `.link[i]` — which link does index `i` refer to? Link after node i, or link before node i?
Code (linkedlist.py lines 48-50): `_LINK_RE = re.compile(r"^link\[(?P<idx>\d+)\]$")` — regex exists but validation in validate_selector() untested for consistency with node[i] semantics.

**M2: Queue Selector `.front`/`.rear` vs `.cell[i]`**
Spec §3: Queue has `.cell[i]`, `.front`, `.rear`, `.all`
Code (queue.py lines 43-46): All four regexes present. `.front` maps to front_idx; `.rear` maps to rear_idx. Matches ✓

**M3: VariableWatch `.var[name]` Selector Grammar**
Spec §3: `.var[name]` (name is variable identifier)
Code (variablewatch.py line 40): `_VAR_RE = re.compile(r"^var\[(?P<varname>[A-Za-z_]\w*)\]$")` — correctly enforces valid Python identifier. Matches ✓

**M4: Plane2D Selector `.region[i]` vs `.regions`**
Spec §3: `.region[i]` (singular)
Code (plane2d.py): Accepts `.region[i]`. Matches ✓

**M5: DPTable 1D vs 2D Selector Ambiguity**
Spec §3: "1D: `.cell[i]`, `.range[i:j]`, `.all`; 2D: `.cell[i][j]`, `.all`"
Code determines 1D vs 2D at construction but both selector patterns coexist. No runtime discrimination documented.

## Low Findings

**L1: Commands Count Verification**
Spec §2: 14 total (12 base + 2 extension)
Grammar.py _dispatch_command: Handles shape, compute, step, narrate, apply, highlight, recolor, reannotate, annotate, cursor, foreach, endforeach, substory, endsubstory = 14 ✓

**L2: Environment Options Scope Not Enforced**
Spec §1.2: `layout` → "animation only"; `grid` → "diagram only"
Code: Grammar applies all options uniformly; diagram vs animation context not checked during parsing. Emitter may ignore unknown options, but no validation error.

**L3: States vs Colors in Constants**
Spec §4: 8 recolor states (idle, current, done, dim, error, good, path, highlight)
Code constants.py: VALID_STATES includes "highlight" (line 17) ✓

---

## Notes

Phase D successfully resolved H2/H3 (all 16 primitives + selectors in spec). New drift identified:
1. **Stack params mismatch** (§5.2 vs §5.7 vs code) — §5.2 is stale
2. **scope enforcement gap** — environment options ignore "animation only" / "diagram only" constraints
3. **CodePanel 1-based indexing** — spec silent; prior audit flagged as undocumented

Minor selector/grammar issues are cosmetic (all working correctly). Registry alignment is production-ready except for Stack spec clarification.
