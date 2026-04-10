# Scriba Ruleset — 6-Angle Deep Analysis (2026-04-10)

> 6 parallel agents analyzed the ruleset from distinct perspectives:
> formal grammar theory, UX ergonomics, CP education completeness,
> security hardening, accessibility (WCAG 2.1 AA), and scalability.

---

## 1. Formal Grammar Theory

### Grammar Class — LOW
Scriba is **context-free** overall. The selector syntax is a valid CFG.
`\compute` with `${var}` interpolation does NOT make it context-sensitive —
interpolation is resolved at build time (semantic pass), not during parsing.
The `\compute` body is consumed as opaque raw text, keeping Starlark outside
the Scriba grammar proper.

### LL(1) Compatibility — LOW
The grammar is effectively **LL(1)**. The parser is predictive recursive
descent with no backtracking. Command dispatch uses a single `BACKSLASH_CMD`
token. Selector accessor dispatch requires one token lookahead on the
identifier name — standard LL(1).

### Ambiguity — MEDIUM
Two potential issues:
- `$` in `\narrate` vs `${var}` interpolation: resolved by lexer checking
  `$` followed by `{`. `\narrate` uses raw extraction path — subtle coupling.
- Generic IDENT accessor vs named accessors: `cell`, `node`, etc. are reserved.
  If a primitive defines a part named `cell`, it shadows the built-in. Documented
  but could surprise users.

### Error Recovery — MEDIUM
The parser is **fail-fast** with no error recovery. Every error immediately
raises `ValidationError`. Users get one error at a time. No "did you mean?"
suggestions. Position info uses command position, not offending parameter's.

### Lexer-Parser Coupling — MEDIUM
- `_read_raw_brace_arg` bypasses the token stream and re-reads from raw source
- `_find_brace_pos_in_source` performs O(n) linear scan to map token line/col
  back to source offset — fragile if line/col tracking drifts
- `_KNOWN_COMMANDS` whitelist requires updating both lexer and parser for new commands

### BNF Completeness — MEDIUM
The BNF in S3 covers selectors but is incomplete for a full parser generator:
- No BNF for command grammar (sequencing, prelude vs step phases)
- No BNF for parameter lists or value types
- `\foreach` and `\substory` block structure undocumented formally
- A parser generator could not be built from the BNF alone

---

## 2. UX / Ergonomics

### First-Time Author Experience — HIGH
A LaTeX user reading one example would grasp `\begin{animation}`, `\shape`,
`\step`, `\narrate`. But the distinction between `\recolor`, `\apply`,
`\annotate`, `\reannotate`, and `\highlight` is not obvious. There is no
tutorial or "Getting Started" guide — only a reference document.

### Boilerplate Ratio — MEDIUM
In `frog1_dp.tex` (77 lines), ~60% is `\recolor` state management (dimming
previous, highlighting current). Only ~15% is meaningful content. `\foreach`
helps at the traceback step but the main DP loop is still fully manual.
A `\dpstep` or iteration macro would cut 60% of the file.

### Mental Model — HIGH
The persistent-state + ephemeral-highlights model is the biggest cognitive
burden. Authors must mentally track every cell's state across steps. If you
forget one `\recolor{...}{state=dim}`, the visualization breaks silently.
There is no "auto-dim previous" or "focus" command.

### Naming Clarity — MEDIUM
- `\apply` — does it mean "set a value"? "Execute a function"? `\set` or
  `\write` would be clearer.
- `\reannotate` vs `\annotate` — "re-annotate" suggests "annotate again."
  `\recolor_annotation` would be more precise.
- `\recolor` vs `\highlight` — critical behavioral difference (persistent vs
  ephemeral) hidden behind two unrelated verbs.
- `\compute` — clear enough, but Starlark subset (no `while`, no `lambda`)
  will surprise Python users.

### Common Patterns That Should Be Easier — HIGH
Three patterns repeat across nearly every example:
1. **Cursor advance**: dim previous, highlight current, mark previous done (3+
   lines per step → could be `\cursor{arr}{i}`)
2. **Batch initialization**: setting N cells to same value/state (→ `\fill`)
3. **DP transition pattern**: annotate arrows, narrate comparison, apply
   min/max, mark done (6-8 lines per step, identical structure)

### Debugging Experience — MEDIUM
No debug or inspect mode. When output looks wrong, only recourse is re-reading
source and mentally replaying state. A `--dump-frames` flag showing per-frame
state snapshots would be invaluable.

### Documentation Quality — MEDIUM
Ruleset is an excellent reference for someone who already knows Scriba. Missing:
tutorial with progressive examples, cheat sheet of 5 most common patterns,
"common mistakes" section.

---

## 3. CP Education Completeness

| Category | Rating | Notes |
|----------|--------|-------|
| Basic data structures | PARTIAL | Array/Stack/Grid: FULL. Queue/Deque/LinkedList/HashMap: NONE |
| Sorting algorithms | PARTIAL | Expressible but manual, no swap animation |
| Graph algorithms | FULL | All major algos expressible, 5 layout modes, stable layout |
| Tree algorithms | FULL | Generic, segtree, sparse_segtree. BST/Fenwick/LCA/HLD all work |
| DP patterns | FULL | 1D/2D/interval/knapsack/bitmask all demonstrated in cookbook |
| String algorithms | MINIMAL | No string-specific primitive, KMP/Z possible with Array hack |
| Geometry | PARTIAL | Plane2D has points/lines/segments/polygons. No arc/circle |
| Advanced | PARTIAL | MCMF, FFT, persistent segtree demonstrated. No residual graph |

### Missing Primitives
- **Queue/Deque**: No FIFO with enqueue/dequeue semantics
- **Linked List**: No pointer/node-chain visualization
- **Hash Map/Set**: No key-value bucket visualization
- **Code Panel**: No source code display synced to steps
- **Variable Watch**: No variable inspector panel
- **Trie**: No prefix tree (would need generic Tree)

### Missing Features
- Auto-step from code execution (code-to-animation binding)
- Side-by-side comparison (two algorithms)
- Complexity annotations (O(n) badges)
- Swap animation (native element swap)
- Edge labels (capacity/weight on graph edges)
- Multi-shape layout grid (side-by-side instead of vertical stack)

---

## 4. Security

### Sandbox Escape — MEDIUM
- `_BLOCKED_ATTRIBUTES` covers 7 dunders but misses `__code__`, `__func__`,
  `__dict__`, `__init__`, `__new__`, `__reduce__`
- Dictionary subscript access `{"__builtins__": x}["__builtins__"]` uses
  `ast.Subscript`, not `ast.Attribute` — detection gap (mitigated by
  `__builtins__` overwrite)
- `isinstance` is allowed — leaks type hierarchy but cannot escape

### Resource Exhaustion — HIGH
- **C-level operations bypass `sys.settrace` step counter**: `sorted()` on huge
  lists, `"x" * 10**8`, `sum(range(10**9))` execute in C without tracing.
  Only the 5s `SIGALRM` wall-clock timeout protects.
- **`RLIMIT_AS` silently fails on macOS/Darwin**: the `_set_memory_limit`
  function catches and ignores the error. No memory limit on Darwin.
- String multiplication memory bombs viable within 5s window on macOS.

### Denial of Service — MEDIUM
- Parser has no input size limit on .tex source
- No hard frame count cap (100-frame limit documented but E1181 may not be
  enforced in all code paths)
- Unbounded HTML output proportional to frame count × primitive size

### HTML Injection — LOW
- Narration escaped via `html.escape()` or KaTeX-sanitized HTML
- `_escape_js` handles `</script>`, backticks, template literals
- `narration_html` injected raw into `<p>` — safe only if rendering always
  produces safe HTML

### Actionable Items
1. Add macOS-specific memory limiting (subprocess `ulimit` or allocation tracking)
2. Lower wall-clock timeout or add C-operation budget
3. Expand `_BLOCKED_ATTRIBUTES` to include `__code__`, `__func__`, `__dict__`,
   `__reduce__`, `__reduce_ex__`
4. Enforce hard frame count cap in all code paths

---

## 5. Accessibility (WCAG 2.1 AA)

### ARIA — HIGH
- **Broken `aria-labelledby` in interactive mode**: SVG references narration
  `<p>` ID but the `<p>` has no `id` attribute in interactive mode (static
  mode is correct)
- Widget `<div>` has no `role` attribute (should be `role="region"`)

### Screen Reader — HIGH
- **No `aria-live` region**: narration text swapped via `innerHTML` without
  announcement. Screen readers won't announce frame changes.
- Narration `<p>` needs `aria-live="polite"`, step counter needs
  `aria-atomic="true"`

### Focus — HIGH
- **No visible focus indicator**: `--scriba-widget-focus-ring` CSS token defined
  but never applied to any selector. No `:focus` or `:focus-visible` rule.
- `tabindex="0"` only set via JS — if JS fails, widget is keyboard-unreachable

### Color Contrast — HIGH
- `good` (#56B4E9 on white) = **2.49:1** — fails both AA thresholds
- `error` (#D55E00 on white) = **3.67:1** — fails normal text (passes large)
- `dim` at 50% opacity can push borderline contrasts below threshold

### SVG — MEDIUM
- Graph edges and arrows have no text alternative (`<line>` elements with no
  `<title>` or `aria-label>`)
- Annotations use `pointer-events: none` with no accessible description

### Print — MEDIUM
- Interactive mode has no print stylesheet — controls print, only visible
  frame appears. Spec says "vertical stack, expand substories" but not
  implemented for interactive mode.

### Passing
- `@media (prefers-reduced-motion: reduce)` correctly implemented (SC 2.3.3)
- Static mode uses semantic HTML (`<figure>`, `<ol>`, `<li>`, `<header>`)
- SVGs have `role="img"` with `aria-labelledby`

---

## 6. Scalability / Performance

### SVG Duplication — HIGH
Every frame generates a complete, independent SVG. In interactive mode, all
frames inlined as JS template literals. 100 frames × 5KB SVG = 500KB HTML.
No deduplication — static elements (positions, paths, defs) repeated verbatim.
A diff-based approach (base SVG + per-frame patches) could reduce output by
60-80%.

### Output Size — HIGH
HTML is not minified. No compression pass. Major optimization opportunity.

### Arrow Layout — MEDIUM
`_arrow_height_above()` uses `.index()` inside a loop = O(n²). Fine for 5-10
arrows, noticeable with 100+. Fix: use enumerated index.

### DOM Performance — MEDIUM
Interactive widget sets `innerHTML` per frame. For SVGs >100KB could cause
perceptible jank on low-end devices. Typical scenes (5-20KB) are fine.

### Foreach Expansion — MEDIUM
`_substitute_body()` is O(n*m) where n=iterations, m=body fields. Capped at
10K iterations, depth 3 nesting. Bounded but could spike to tens of MB for
large bodies.

### Fast Enough
- Build time <100ms typical, 1-3s worst case (100 frames)
- Frame processing O(F*S) with shallow snapshots
- Starlark uses persistent subprocess worker (no spawn per call)
- Graph layout runs once at init, sub-millisecond for N≤20
- `copy.deepcopy(bindings)` only runs with compute blocks

---

## Priority Matrix

| Category | Critical Items | Action |
|----------|---------------|--------|
| Security | macOS memory limit, C-ops bypass | Fix soon |
| A11y | aria-live, focus indicator, contrast | Fix soon |
| Performance | SVG dedup, output minification | Plan for next phase |
| UX | Tutorial, cursor macro, debug mode | Plan for next phase |
| CP Education | Queue/LinkedList/Code panel | Future primitives |
| Grammar | Full BNF, error recovery | Low priority |
