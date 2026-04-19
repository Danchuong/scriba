# §9 + §12 Examples & Patterns Audit

**Date**: 2026-04-19
**Reference doc**: `docs/SCRIBA-TEX-REFERENCE.md`
**Method**: Each example extracted verbatim and fed to `AnimationRenderer.render_block()` /
`DiagramRenderer.render_block()` via the Python API (no Starlark host — matching the
documented minimal setup). Failures captured with full tracebacks.

---

## Render Results

| # | Section | Example | Ref lines | Result | Errors / Notes |
|---|---------|---------|-----------|--------|----------------|
| 1 | §9.1 | Minimal Animation (Hello World) | 638–652 | PASS | — |
| 2 | §9.2 | Static Diagram | 657–661 | PASS | — |
| 3 | §9.3 | DP Editorial (Frog Problem) | 674–698 | PASS | — |
| 4 | §9.4 | BFS with Multiple Primitives | 703–723 | PASS | — |
| 5 | §9.5 | foreach and compute | 728–743 | **FAIL** | E1173 — see §Findings |
| 6 | §9.6 | Hidden State Pattern (BFS Tree) | 748–767 | PASS | — |
| 7 | §12.1 | Cursor movement through array | 800–804 | PASS | — |
| 8 | §12.2 | DP transition arrows | 809–811 | PASS | — |
| 9 | §12.3 | Traceback with reannotate | 815–821 | **FAIL** | E1173 (same root cause) |
| 10 | §12.4 | Graph edge marking | 824–827 | PASS | — |
| 11 | §12.5 | Flow network (dynamic edge labels) | 830–841 | PASS | — |

**Summary: 9 PASS, 2 FAIL out of 11 examples.**

---

## Findings

### [CRITICAL] §9.5 (lines 728–743): `\compute` + `\foreach` silently dropped without Starlark host

**Symptom**
```
ValidationError: [E1173] at line 6: foreach binding '${evens}' not found
```

**Root cause — two-layer problem**

1. `AnimationRenderer(starlark_host=None)` (the documented minimal setup) silently skips all
   `\compute` blocks. In `scene.py:735–738`:
   ```python
   def _run_compute(self, cb, starlark_host):
       if starlark_host is None:
           return          # bindings are never populated
   ```

2. `apply_frame` in `scene.py:210–216` correctly runs compute *before* `_expand_commands`,
   so the ordering logic is sound — but with no host, `evens` is never written into
   `self.bindings`. When `_resolve_iterable` checks `self.bindings` for `"${evens}"`,
   it raises E1173 (line 383).

**The parse is correct.** `SceneParser` correctly stores the `ComputeCommand` in
`frame_ir.compute` (not `frame_ir.commands`), and emits no parse-time warning because
`_collect_compute_bindings` does detect `evens = [0, 2, 4]` and adds it to
`_known_bindings` — suppressing `_check_interpolation_binding`'s UserWarning.

**Documentation gap**: The reference doc presents this example (lines 728–743) without any
caveat that `\compute` requires a Starlark host (a `SubprocessWorkerPool` + pipeline, or a
custom `starlark_host=` object). A reader using the minimal `AnimationRenderer()` will get
a hard crash. The doc should either:
- Add a prerequisites note ("requires a Starlark host — see §X.Y Pipeline Setup"), OR
- Provide an alternative using a list literal: `\foreach{i}{[0, 2, 4]}` which works without
  a host.

**Affected examples**: §9.5 (lines 728–743), §12.3 pattern (lines 815–821, `\compute{path = ...}`).

---

### [CRITICAL] §12.3 (lines 815–821): `\compute` + `\foreach` in Traceback pattern — same root cause

**Symptom**
```
ValidationError: [E1173] at line 11: foreach binding '${path}' not found
```

The traceback/reannotate pattern uses `\compute{ path = [0, 2, 3, 5] }` immediately before
`\foreach{i}{${path}}`. Without a Starlark host the pattern is broken in exactly the same
way as §9.5. The `\reannotate` command itself is fully functional (verified in isolation).

**Minimal fix for the doc**: Replace `\compute` + `\foreach{i}{${path}}` with a literal:
```latex
\foreach{i}{[0, 2, 3, 5]}
```
or note that `\compute` requires a Starlark host.

---

### [MED] §12.1 (lines 800–804): Cursor snippets are not self-contained examples

The §12.1 snippet shows three `\cursor` calls at the top level with `%` comments:
```latex
\cursor{a.cell}{0}                          % initial position
% next step:
\cursor{a.cell}{1}
\cursor{a.cell}{2, prev_state=done}
```
This is presented as a pattern, not a standalone block — there is no `\begin{animation}` /
`\end{animation}` wrapper or `\step` delimiters. Taken literally, a reader copying the block
will get a parser error: `\cursor` is not valid at top level without a step frame, and there
is no shape named `a` declared.

Audit wrapped these in a minimal animation env with `\step` separators — render PASS.
The doc should clarify these are snippet fragments inside a step, not runnable standalone.

---

### [LOW] §9.2 (line 658): Weighted edge format — no parentheses example in §9 prose

§9.2 uses `edges=[("A","B",3),("A","C",5),...]` (3-tuple weighted edges) without explaining
the format. The primitive supports both 2-tuple and 3-tuple edges but the format is only
documented in the primitive reference (§5), not cross-referenced from §9.2. Low risk since
the example itself renders correctly.

---

### [LOW] §9.5 (line 739): `\foreach{i}{0..4}` step renders but iterates 0..4 inclusive

The range `0..4` produces `[0, 1, 2, 3, 4]` (5 elements) which is correct for a size-5
array. Verified at runtime. No documentation inconsistency — the range semantics are
inclusive on both ends as stated in §8. Noted for completeness.

---

## Passing Example Notes

- **§9.1**: `\shape{a}{Array}` + `\recolor` + `\narrate` — clean baseline. PASS.
- **§9.2**: `\begin{diagram}`, `Graph` with weighted directed edges, bare node selectors
  (`G.node[A]`) — bare identifiers in node/edge selectors correctly resolve to string keys.
  PASS.
- **§9.3**: `\apply{dp.cell[0]}{value=0}`, `\annotate` with `arrow_from=` and `color=good` —
  all resolved correctly. PASS.
- **§9.4**: Queue `enqueue`/`dequeue`, multi-primitive scene, `G.edge[(A,B)]` edge selector —
  all functional. `data=[]` (empty queue) initialises correctly. PASS.
- **§9.6**: `state=hidden` on Tree nodes/edges, then reveal via `state=current` /
  `state=good` — `hidden` is a valid VALID_STATE and renders correctly. PASS.
- **§12.1**: `\cursor{a.cell}{2, prev_state=done}` — cursor parser splits second brace arg
  by comma; `prev_state=done` is parsed as key/value. `done` is in VALID_STATES. PASS.
- **§12.2**: Double `\annotate` on same target — multiple annotations accumulate correctly.
  PASS.
- **§12.4**: `state=good` (tree edge) and `state=dim` (cross edge) — both valid. PASS.
- **§12.5**: `\apply{G.edge[(S,A)]}{value="5/10"}` edge label updates + `state=error` for
  saturated edge — all functional. PASS.

---

## Verdict

**7/11** — correct without caveats. 2 examples are critically broken without a Starlark host
(which the doc never requires the reader to set up). 2 additional medium/low notes.

The two CRITICAL failures share a single root cause: the doc uses `\compute` in examples
without stating that `\compute` requires a Starlark subprocess host. When `AnimationRenderer()`
is constructed with no host (the natural minimal form), `_run_compute` silently returns and
the subsequent `\foreach` binding lookup hard-crashes with E1173. Neither a parse-time
warning nor a graceful degradation message is emitted.

**Recommended actions (priority order)**

1. Add a admonition block before §9.5 and in §12.3 noting the Starlark host prerequisite.
2. Provide an alternative `\foreach{i}{[0,2,4]}` list-literal form that works host-free.
3. Clarify §12.1 that cursor snippets are fragments inside `\step` blocks, not standalone.
4. Cross-reference §9.2's weighted edge tuple format to the relevant primitive docs.
