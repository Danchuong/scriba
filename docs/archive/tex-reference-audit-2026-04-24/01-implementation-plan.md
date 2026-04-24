# TEX-REFERENCE — Implementation Plan (Option C: Full)

**Date:** 2026-04-24
**Target:** `docs/SCRIBA-TEX-REFERENCE.md` (956 → ~1500–1600 lines) + `README.md`
**Scope:** apply **all three tiers** of findings from [00-synthesis.md](00-synthesis.md) + README AI integration section.
**Budget:** ~650 line additions + ~50 line corrections total.

---

## Phase Summary

| Phase | Work | Agent | Parallelism | Est. lines |
|-------|------|-------|-------------|-----------|
| P1 | Tier 1 — factual fixes + code-backed additions | `general-purpose` | sequential | ~250 |
| P2 | Tier 2 — usability + Dijkstra example | `general-purpose` | sequential | ~300 |
| P3 | Tier 3 — polish + README | `general-purpose` | sequential | ~150 + README |
| P4 | Verification: re-audit code-vs-ref + LLM cold-read | 2 × `Explore` | **parallel** | — |
| P5 | Commit + close task #74 | (direct) | — | — |

**Why sequential writers:** all three writer phases edit the same file (`SCRIBA-TEX-REFERENCE.md`). Parallel writes → merge conflict hell. Sequential is cheaper than reconciling.

**Why parallel verifiers:** independent axes (ground truth vs cold-read) — gộp sẽ bias.

**Total agent runs:** 5 (3 writers sequential + 2 verifiers parallel).

---

## Phase 1 — Tier 1: Factual Fixes + Code-Backed Additions

**Agent:** `general-purpose`
**Tools:** Read, Edit, Grep, Glob
**Estimate:** ~250 lines changed

### Checklist

**Counts / headers:**
- [ ] §7 heading: `"All 16 Primitives"` → `"All 15 Primitives"`
- [ ] §5 heading: `"12 total"` → `"13 total"` + insert `\hl` as §5.13

**§5.2 `\compute`:**
- [ ] Extend pre-injected builtins list: add `isinstance, repr, round, chr, ord, pow, map, filter`
- [ ] Expand forbidden list: add `async def, async for, async with, await, yield, yield from, walrus (:=), match`
- [ ] Resolve §3.1 vs §9.5 contradiction: **`\compute` may appear inside `\step`; bindings are frame-local and dropped at the next `\step`**. Update both §3.1 comment and §5.2 prose.

**§5.3 `\step[label=...]`:**
- [ ] Add E1320/E1321 cross-refs for `\hl` placement.

**§5.9 `\reannotate`:**
- [ ] State that `color=` is **required** (E1113 if absent).
- [ ] Expand to show all valid params (`color`, `arrow_from`, `label`, `ephemeral`) matching §5.8 table format.

**§5.13 `\hl` (NEW):**
- [ ] Add formal subsection: syntax, cross-ref to §5.3 label rules, error codes E1320/E1321, step{N} vs labeled step behavior.

**§6 Visual States:**
- [ ] Drop inline hex OR replace with actual `STATE_COLORS` values. Recommend: drop hex, add "See CSS tokens in `scriba/animation/static/scriba-scene-primitives.css` for exact colors".
- [ ] Fix `hidden`: "element omitted from SVG output entirely (not given a CSS color)".

**§7.4 Graph:**
- [ ] Add `add_edge` / `remove_edge` ops (E1471/E1472).
- [ ] Add params: `orientation` ("TB"/"LR"), `auto_expand`, `split_labels`, `tint_by_source`, `tint_by_edge`, `global_optimize`.

**§7.5 Tree:**
- [ ] Add mutation ops: `add_node`, `remove_node` (with `cascade=true`), `reparent`. E1433–E1436.

**§7.7 Matrix/Heatmap:**
- [ ] Expand params: `colorscale`, `vmin`/`vmax`, `row_labels`, `col_labels`, `cell_size`.

**§7.9 Plane2D:**
- [ ] Add ops: `add_segment`, `add_polygon`, `add_region`, `remove_point`, `remove_line`, `remove_segment`, `remove_polygon`, `remove_region`.
- [ ] Add shape params: `aspect` (`equal`/`"auto"`), inline batch params (`points=`, `lines=`, `segments=`, `polygons=`, `regions=`), per-primitive `width=<px>`.

**§7.10 MetricPlot:**
- [ ] Add params: `show_legend`, `grid`, `xrange`, `yrange`, `width`, `height`, per-series `axis`/`scale`/`color`, two-axis mode documentation.

**§7.13 LinkedList:**
- [ ] Add ops: `\apply{ll}{insert={"index":i,"value":v}}`, `\apply{ll}{remove=i}`.

**§7.14 Queue:**
- [ ] Add `.front` and `.rear` selectors. Update §8 selector table Queue row.

**§10 Environment Options:**
- [ ] Add `grid` row (diagram only) OR remove from `VALID_OPTION_KEYS` in code. **Decision:** document as accepted-but-ignored pending implementation.
- [ ] Add `id` charset constraint: `[a-z][a-z0-9-]*`.

**§14 Limits:**
- [ ] Add "Graph (force layout): ≤100 nodes (E1474)".
- [ ] Add "Starlark range() max elements: 1,000,000 (E1173)".

### Exit criteria P1
- `grep -c "16 primitives"` = 0
- `grep -c "12 total"` = 0 in §5
- No state has `current #0072B2` style hex unless backed by CSS truth
- All code-backed APIs (add_edge, remove_edge, add_node, Plane2D ops, etc.) documented

---

## Phase 2 — Tier 2: Usability + Dijkstra Example

**Agent:** `general-purpose`
**Tools:** Read, Edit, Write (for render test), Bash (for render validation), Grep
**Estimate:** ~300 lines added

### Checklist

**§0 How to render (NEW, prepend before §1):**
- [ ] Single subsection with `python render.py file.tex --open`, brief mention of `--static` for filmstrip mode.
- [ ] Note: Python 3.10+ and Node.js 18+ required (link to README Install).

**§3 Animation Environment:**
- [ ] Add operational definition of "delta-based": "Before the first `\step`, prelude commands (`\apply`, `\recolor`) set the initial frame-0 state. Each subsequent `\step` snapshots the scene; later commands mutate the state for the next snapshot. Persistent commands carry forward; ephemeral commands reset at each `\step`."

**§5.2 `\compute`:**
- [ ] Add example: filtered list comprehension `even_indices = [i for i in range(n) if i % 2 == 0]`.
- [ ] Add example: nested `for` loops building 2D DP table (canonical pattern from `test_reference_dptable.tex`).

**§5.10 `\cursor`:**
- [ ] Add multi-target example `\cursor{h.cell, dp.cell}{i}` — explain it syncs two primitives at once.

**§7.4 Graph — Layout Decision Guide (NEW subsection):**
| Layout | Use when | Notes |
|---|---|---|
| `"force"` (default) | Undirected, any size | Non-deterministic across seeds — prefer `layout_seed=` |
| `"stable"` | Small (≤20 nodes), undirected | Deterministic; warns on `directed=true` |
| `"hierarchical"` | DAGs, tree-like directed flows | Respects `orientation="TB"` or `"LR"` |
| `"circular"` | Cyclic structures, ring topologies | Nodes placed on a circle |
| `"bipartite"` | Two-partition graphs | Requires bipartite structure |

**§8 Selectors:**
- [ ] Add definition: "A **selector** is a string of the form `<shape>.<family>[<index>]` (e.g., `a.cell[3]`, `G.node[A]`) that addresses a sub-element of a shape for commands like `\recolor`, `\apply`, `\annotate`."
- [ ] Add node ID quoting rule: "Unquoted form (`G.node[A]`) when ID is a simple identifier (`[A-Za-z_][A-Za-z0-9_]*`). Quote (`G.node["[0,5]"]`) when ID contains brackets, spaces, commas, or other special characters."

**§9.7 Dijkstra Example (NEW):**
- [ ] Write a full worked example using `Graph` (weighted, directed, `hierarchical` layout) + `Array` (distance table) + `CodePanel` (pseudo-code) in one animation.
- [ ] 5–8 frames: initialize, pick source, relax neighbors (2–3 frames), finalize.
- [ ] Uses `\cursor` multi-target, `\annotate` with `arrow_from=` for edge relax arrows, `\reannotate` for final shortest path highlight.
- [ ] **Verify renders cleanly** via `python render.py examples/_tmp_dijkstra.tex`. Delete temp file after verification.

**§13 Gotchas:**
- [ ] New §13.8: "Annotation headroom is reserved at the per-scene maximum (R-32)" — annotations that appear in only some frames still push layout for every frame.
- [ ] Cross-ref §13.2: explain *why* `${var}` outside `\foreach` is unreliable (deferred resolution vs textual substitution) + concrete workaround (use a single-iteration `\foreach` wrapper).

### Exit criteria P2
- §0 exists with render command
- §9.7 Dijkstra example renders without error or warning
- "selector" is defined on first use
- Graph layout choice has decision criteria

---

## Phase 3 — Tier 3: Polish + README

**Agent:** `general-purpose`
**Tools:** Read, Edit, Grep
**Estimate:** ~150 lines + ~15 line README block

### Checklist

**§2 LaTeX commands:**
- [ ] Add §2.2.1 size commands: `\tiny`, `\scriptsize`, `\small`, `\normalsize`, `\large`, `\Large`, `\LARGE`, `\huge`, `\Huge`. Both brace and switch forms.
- [ ] Add §2.2.2 legacy aliases (Polygon compat): `\bf{}`, `\it{}`, `\tt{}`.
- [ ] §2.3 math: note `$$$...$$$` as display alias (Polygon legacy).
- [ ] §2.5 `lstlisting`: list Pygments themes (`one-light`, `one-dark`, `github-light`, `github-dark`, `none`) and copy-button behavior.
- [ ] §2.7 `\href`: note non-`http/https/mailto/ftp/relative` URL schemes render as `<span class="scriba-tex-link-disabled">`.
- [ ] §2.8: add curly-quote typography ``` ``text'' ``` → `"text"`, `` `text' `` → `'text'`.

**§5.12 `\substory`:**
- [ ] Document `id=` option key alongside `title=`.
- [ ] Note state persistence across substory boundary: **commands inside substory mutate the parent scope's state and persist after `\endsubstory`** (confirm via code read if ambiguous).

**§6 Visual States:**
- [ ] Add semantic convention note: "Use `current` for the node being actively processed this frame. Use `path` for nodes in the final solution path. Both are blue but semantically distinct."

**§10 Environment Options:**
- [ ] Add dimension format example: `width=800` (px implied) or `width=8cm`.

**§13 Gotchas:**
- [ ] `CodePanel` 1-indexed (promote from §7.11 buried line).
- [ ] `Graph(layout="stable", directed=True)` silent UserWarning.
- [ ] `Graph(global_optimize=True)` silent no-op warning.
- [ ] Smart-label env flags (`SCRIBA_DEBUG_LABELS`, `SCRIBA_LABEL_ENGINE`) — promote from §5.8 block-quote.

**§15 Error Code Quick Reference (NEW):**
- [ ] Table: top 15 author-relevant codes (from A2 Q1) with one-line meaning each.

**README — `## Using Scriba with an AI assistant` (NEW):**
- [ ] Short block (~15 lines) after `## Install`:
  ```markdown
  ## Using Scriba with an AI assistant

  To have an AI write .tex for Scriba, give it one file:
  **[`docs/SCRIBA-TEX-REFERENCE.md`](docs/SCRIBA-TEX-REFERENCE.md)**.

  It's self-contained — all commands, all 15 primitives, all selectors,
  all gotchas. No other spec files needed.

  Prompt template:
  > Read `SCRIBA-TEX-REFERENCE.md`. Write a Scriba `.tex` file that
  > animates [algorithm]. Use only commands and primitives documented
  > in that file.
  ```

### Exit criteria P3
- `grep -c "print()` in §5.2 hits with behavior note
- Error code table present (§15)
- README has AI-usage callout

---

## Phase 4 — Verification (parallel)

Run **two** `Explore` agents concurrently after P3 commits (or staged locally).

### Agent P4-A: Code-vs-Ref re-audit
**Prompt:** Re-run the A1 audit against the updated `SCRIBA-TEX-REFERENCE.md`. Expect **zero CRITICAL, zero HIGH**. Report any remaining MEDIUM/LOW. Write result to `docs/archive/tex-reference-audit-2026-04-24/A1b-reaudit.md`.

### Agent P4-B: LLM cold-read re-test
**Prompt:** Pretend you're an LLM that's never seen Scriba. Given only the updated reference, write a Dijkstra editorial. Report:
1. Did you succeed without inventing syntax?
2. Overall rating (POOR/ACCEPTABLE/GOOD/EXCELLENT)?
3. Remaining friction points?
Write result to `docs/archive/tex-reference-audit-2026-04-24/A4b-reaudit.md`.

### Exit criteria P4
- P4-A: zero CRITICAL/HIGH
- P4-B: rating ≥ GOOD

If either fails, spawn a targeted hotfix phase (P3.5) before P5.

---

## Phase 5 — Commit + Close

**Direct execution, no agent.**

Steps:
1. `git diff docs/SCRIBA-TEX-REFERENCE.md README.md` — manual spot check.
2. `git add docs/SCRIBA-TEX-REFERENCE.md README.md docs/archive/tex-reference-audit-2026-04-24/`
3. Commit message:
   ```
   docs(reference): close 47-issue audit — Tier 1+2+3 + README AI callout

   - Fix factual errors (15 not 16 primitives, 13 not 12 inner commands,
     state hex palette, hidden state behavior)
   - Add code-backed API surface (Graph add_edge/remove_edge + flow params,
     Tree mutation, Plane2D full ops, Queue front/rear, LinkedList insert/remove,
     Matrix/MetricPlot params)
   - Add Starlark builtins (isinstance/repr/round/chr/ord/pow/map/filter)
     and forbidden constructs (async/yield/walrus/match); document range()
     10^6 cap
   - Add §0 render instructions, §9.7 Dijkstra example, selector definition,
     graph layout decision guide, `\compute` in-step scoping, multi-target
     `\cursor`, nested Starlark for 2D DP
   - Polish: size commands, legacy aliases, typography, error-code quick-ref
   - README: "Using Scriba with an AI assistant" section pointing at reference

   Closes audit #74. See docs/archive/tex-reference-audit-2026-04-24/.
   ```
4. `TaskUpdate #74 → completed`

---

## Success metrics

| Metric | Before | Target |
|---|---|--------|
| Reference file size | 956 lines | ~1500–1600 lines |
| CRITICAL issues | 3 | 0 |
| HIGH issues | 4 | 0 |
| MEDIUM issues | 6 | ≤2 (acceptable residual) |
| LOW issues | 4 | ≤2 |
| Cold-read Dijkstra rating | ACCEPTABLE | GOOD+ |
| Example coverage | 6 (missing Dijkstra/2D-DP/segtree) | 7 (Dijkstra added) |
