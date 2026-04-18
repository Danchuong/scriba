# Spec & Tech Docs Audit

**Date:** 2026-04-18
**Scope:** `docs/spec/`, `docs/rfc/`, `docs/primitives/`, `docs/extensions/`, `docs/SCRIBA-TEX-REFERENCE.md`, `docs/README.md`, `docs/planning/phase-c.md`
**Code baseline:** `scriba/animation/primitives/*.py`, `scriba/animation/scene.py`, `scriba/animation/parser/grammar.py`

---

## Summary

| Area | Findings | Critical | High | Med | Low |
|------|----------|----------|------|-----|-----|
| docs/spec/ | Grammar accurate; 3 error-code conflicts | 0 | 2 | 1 | 0 |
| docs/rfc/ | 2 RFCs, both accepted; implementation status unclear | 0 | 1 | 1 | 0 |
| docs/primitives/ | 7 param-schema drifts across 5 primitives | 0 | 3 | 2 | 2 |
| docs/extensions/ | 1 extension documented as unimplemented | 0 | 1 | 0 | 1 |
| SCRIBA-TEX-REFERENCE.md | 5 divergences vs code | 0 | 2 | 2 | 1 |
| docs/README.md | Minor version claim | 0 | 0 | 0 | 1 |
| docs/planning/phase-c.md | References removed feature | 0 | 0 | 1 | 0 |

---

## docs/spec/ findings

### spec/environments.md

**Directive list (grammar.py lines 245–355)** — All 12 inner commands documented in `environments.md` §3 are implemented in `grammar.py`:
`\shape`, `\compute`, `\step`, `\narrate`, `\apply`, `\highlight`, `\recolor`, `\annotate`, `\reannotate`, `\cursor`, `\foreach`/`\endforeach`, `\substory`/`\endsubstory`. No drift here.

**HIGH — E1150 collision (environments.md line 432 vs error-codes.md line 64):**
`environments.md` §6.2 states that zero `\narrate` in a step emits `E1150` (warning). However `error-codes.md` assigns `E1150` to "Starlark parse/syntax error" and `errors.py` line 203 confirms this. The zero-narrate path does NOT use E1150 — it is a silent/implicit warn. The spec text is wrong. This is a code–doc conflict on a published error code.

**MED — `\compute` `def` allowance divergence (environments.md §5.2 vs SCRIBA-TEX-REFERENCE.md §5.2):**
`environments.md` §5.1 says `def` is allowed ("Recursive calls allowed"). `SCRIBA-TEX-REFERENCE.md` line 172 also lists `def` as allowed inside `\compute`. These are consistent with each other and with `starlark_host.py`. No drift in code, but `error-codes.md` line 64 lists `E1154` as covering "import, while, class, lambda, try" — `def` is not in that list but is a recognized allowed feature. This is fine, no action needed.

**HIGH — `\narrate` cardinality: "exactly one" vs "should have":**
`environments.md` §3.4 says "exactly one `\narrate` per `\step`", "Zero is `E1150` (warning, emits empty `<p>`)", but then §6.2 corrects this to "SHOULD have exactly one." The `E1150` assignment in §3.4 is a stale cross-reference; the actual zero-narrate behavior is not tied to E1150. Authors relying on §3.4 for error-code handling will be misled.

### spec/primitives.md

**Accurate:** All 6 base primitives (Array, Grid, DPTable, Graph, Tree, NumberLine) documented parameters match `ACCEPTED_PARAMS` frozensets exactly. The `graph.py` `seed` alias is not documented in `primitives.md` §6 (only `layout_seed` is listed), but this is a silent compat alias and low risk.

**Graph `seed` alias (LOW):** `graph.py` ACCEPTED_PARAMS line 312 includes `"seed"` as an undocumented alias for `layout_seed`. `primitives.md` §6 does not mention it. Authors could accidentally use `seed=42` expecting it to work — it does, but silently and without documentation.

### spec/error-codes.md

**Accurate overall.** E1400–E1505 codes verified against implementation. One gap:

**LOW — E1437 is listed in `error-codes.md` under "Plane2D Errors" but the code description references `remove_point`, `remove_line`, etc. — the RFC-001 `add_node`/`remove_node` errors on Tree (E1433–E1436) are documented correctly. No conflict.**

---

## docs/rfc/ findings

| RFC | Title | Documented Status | Actual Implementation Status |
|-----|-------|-------------------|------------------------------|
| RFC-001 | Tree / Graph / Plane2D Mutation API | Accepted, target v0.6.0 | HIGH: partial. Tree `add_node`/`remove_node`/`reparent` API shape in RFC matches current `tree.py` docstring comments, but searching the tree.py implementation shows no `_add_node_internal`, `_remove_node_internal`, or `_reparent_internal` methods — the RFC describes the planned interface, not the shipped one. Graph `add_edge`/`remove_edge`/`set_weight` — graph.py ACCEPTED_PARAMS does not include `add_edge`, `remove_edge`, `set_weight` (only includes `nodes`, `edges`, `directed`, `layout`, `layout_seed`, `seed`, `show_weights`, `label`). |
| RFC-002 | Strict Mode Wiring and Render Report | Accepted, target v0.6.0 | MED: `CollectedWarning`, `Document.warnings`, `RenderContext.strict` fields described in RFC — need cross-check against `scriba/core/artifact.py` and `context.py` (not in audit scope for this pass). Error code E1200 (KaTeX HTML scan) is documented in `error-codes.md`. |

**HIGH — RFC-001: documented Tree mutation ops and Graph edge mutation ops are described as if they exist in v0.6.0, but the primitive ACCEPTED_PARAMS frozensets have no `add_node`, `remove_node`, `reparent`, `add_edge`, `remove_edge`, `set_weight` entries.** These are _future spec_ not current code. The RFC status "Accepted" does not mean implemented. The RFC header says "Target release: v0.6.0" which is future — but the RFC is filed under `docs/rfc/` without a clear "not yet implemented" notice, which may mislead contributors reading the code against the RFC. Recommend adding an implementation status note.

**MED — RFC-002:** The `RenderContext.strict` and `CollectedWarning` APIs described in RFC-002 §4 need verification against the actual `scriba/core/` source files (outside this audit's direct read scope). The `_emit_warning` helper referenced in RFC-002 §4.4 is imported in `metricplot.py` and `plane2d.py`, confirming partial implementation.

---

## docs/primitives/ findings (per-primitive drift table)

### ACCEPTED_PARAMS cross-check

| Primitive | Code ACCEPTED_PARAMS | Doc claims | Verdict |
|-----------|---------------------|------------|---------|
| Array | `size`, `n`, `data`, `labels`, `label`, `values`(legacy) | `size`, `n`, `data`, `labels`, `label` | OK — `values` is a legacy alias, doc correctly omits it |
| Grid | `rows`, `cols`, `data`, `label` | `rows`, `cols`, `data`, `label` | MATCH |
| DPTable | `n`, `rows`, `cols`, `data`, `labels`, `label` | `n`, `rows`+`cols`, `data`, `label`, `labels` | MATCH |
| Graph | `nodes`, `edges`, `directed`, `layout`, `layout_seed`, `seed`, `show_weights`, `label` | `nodes`, `edges`, `directed`, `layout`, `layout_seed`, `label` | MED: `seed` alias and `show_weights` undocumented in primitives.md §6 (both work in code) |
| Tree | `data`, `edges`, `kind`, `label`, `nodes`, `range_hi`, `range_lo`, `root`, `show_sum` | same | MATCH |
| NumberLine | `domain`, `ticks`, `labels`, `label` | `domain`, `ticks`, `labels`, `label` | MATCH |
| Matrix | `rows`, `cols`, `data`, `colorscale`, `show_values`, `cell_size`, `vmin`, `vmax`, `row_labels`, `col_labels`, `label` | adds `title` | HIGH: `title` documented in `matrix.md` line 73 ("Text drawn above the matrix") is NOT in ACCEPTED_PARAMS — will trigger E1114 "unknown parameter" |
| Stack | NO ACCEPTED_PARAMS frozenset | `orientation`, `max_visible`, `items`, `label` | HIGH: Stack is missing `ACCEPTED_PARAMS` entirely. It bypasses Wave E1 strict param validation (E1114). Any unknown param silently passes. |
| Plane2D | `xrange`, `yrange`, `grid`, `axes`, `aspect`, `width`, `height`, `points`, `lines`, `segments`, `polygons`, `regions`, `xlabel`, `ylabel`, `label`, `show_coords` | `plane2d.md` matches, `SCRIBA-TEX-REFERENCE.md` §7.9 correct | MED: `xlabel`/`ylabel`/`label` are in ACCEPTED_PARAMS with code comment "no rendered effect — v0.6.2 follow-up". Doc does NOT mention they are no-ops. |
| MetricPlot | `series`, `xlabel`, `ylabel`, `ylabel_right`, `grid`, `width`, `height`, `show_legend`, `show_current_marker`, `xrange`, `yrange`, `yrange_right` | adds `yscale` at top-level | HIGH: `metricplot.md` line 42 shows `yscale="linear"` as a top-level shape param in the example block. `yscale` is NOT in ACCEPTED_PARAMS — it is a per-series field inside the `series` dict. Top-level `yscale=` would trigger E1114. Also: `show_legend` and `show_current_marker` are in ACCEPTED_PARAMS but NOT documented in `metricplot.md` §2.2 param table. |
| CodePanel | `label`, `lines`, `source` | `source`, `lines`, `label` | MATCH |
| HashMap | `capacity`, `label` | `capacity`, `label` | MATCH |
| LinkedList | `data`, `label` | `data`, `label` | MATCH |
| Queue | `capacity`, `data`, `label` | `capacity`, `data`, `label` | MATCH |
| VariableWatch | `names`, `label` | `names`, `label` | MATCH |

### Per-primitive doc findings

**Stack (`docs/primitives/stack.md`):**
- HIGH: `s.bottom` selector documented at line 95 ("The bottommost item. Alias for `s.item[0]`."), and `s.range[lo:hi]` at line 98, are NOT implemented in `stack.py`. `validate_selector` only handles `all`, `top`, and `item[{i}]`. Authors using `s.bottom` or `s.range[0:3]` will silently get E1115 (selector not found, command dropped).
- HIGH: No `ACCEPTED_PARAMS` frozenset means `\shape{s}{Stack}{cell_width=80}` passes without E1114. The doc at `stack.md` line 51 explicitly says "not accepted parameters" for `cell_width`, `cell_height`, `gap` — but the enforcement is missing in code.

**Matrix (`docs/primitives/matrix.md`):**
- HIGH: `title` parameter (line 73) is documented but absent from ACCEPTED_PARAMS and absent from `__init__` — any scene using `title="..."` will raise E1114.

**MetricPlot (`docs/primitives/metricplot.md`):**
- HIGH: Top-level `yscale=` param in declaration example (line 42) is invalid — yscale belongs inside a `series` dict entry. The example block will produce E1114 if used verbatim.
- MED: `show_legend` and `show_current_marker` are functional params (code lines 200–201) but absent from the doc's optional params table (§2.2).

**graph-stable-layout.md:**
- MED: `layout_lambda` is documented as a `\shape` param (line 60) and handled in `graph_layout_stable.py`. However `graph.py` ACCEPTED_PARAMS does NOT include `layout_lambda` — so passing `layout_lambda=0.3` to `\shape{G}{Graph}{...}` will raise E1114 before the stable-layout code ever sees it. This is a gating bug: the stable-layout doc parameter is rejected at the primitive validation layer.

**Stack selector table in `SCRIBA-TEX-REFERENCE.md` §8 (line 608):** shows `Stack` with only `.item[i]` and missing `.range[i:j]`, `.top`, `.all` — consistent with actual implementation. The _doc_ `stack.md` is the incorrect source (it over-promises).

---

## docs/extensions/ findings

| Extension | File | Status Claim | Implementation Status |
|-----------|------|-------------|----------------------|
| E1 — figure-embed | `figure-embed.md` | "not yet implemented (planned for E6)" | Confirmed absent: no `FigureEmbedRenderer` anywhere in the codebase. File explicitly flags itself. |
| E2 — `\hl` macro | `hl-macro.md` | Accepted | `\hl` is processed as a narrate pre-processing pass. Not directly surfaced as a grammar.py command, correct per spec. |
| E4 — `\substory` | `substory.md` | Accepted | Implemented: `_grammar_substory.py` exists, grammar.py dispatches `substory`/`endsubstory`. |
| E5 — CSS keyframes | `keyframe-animation.md` | Accepted | Referenced from `stack.md` for `slide-in-vertical`/`slide-in-horizontal` presets. Code verification of all 7 presets is outside this reading scope but the Stack doc references match the extension vocabulary. |

**HIGH — `figure-embed.md` references `\fastforward` frames (line 34, "Pre-rendered tour snapshot used alongside `\fastforward` frames"). `\fastforward` was explicitly removed (per `planning/phase-c.md` line 4: "`\fastforward` (E3) was removed"). This is a stale cross-reference in an extension doc.**

**LOW — `hl-macro.md` §2.2 states `step_id` must match `[a-z][a-zA-Z0-9_]*` (lowercase start). `SCRIBA-TEX-REFERENCE.md` §5.3 documents label charset as `[A-Za-z_][A-Za-z0-9._-]*` (allows uppercase, dots, dashes). These are inconsistent — cannot both be correct.**

---

## SCRIBA-TEX-REFERENCE.md drift table

| Section | Documented | Actual code | Severity | Line ref |
|---------|-----------|-------------|----------|---------|
| §5.2 `\compute` — `def` listed as "Allowed" | Correct | Allowed in Starlark host | OK | line 172 |
| §5.7 `\recolor` states list includes `hidden` | `VALID_STATES` in code — needs verification; RFC-001 §3 Q2 says add `"hidden"` to `VALID_STATES` as part of v0.6 work | If not yet added, `hidden` listed in SCRIBA-TEX-REFERENCE.md line 239 is premature | MED | line 239 |
| §7.8 Stack selectors | Shows only `s`, `s.item[i]` — does NOT show `.range`, `.top`, `.bottom` | stack.py only implements `all`, `top`, `item[{i}]` | LOW — ref is accurate to code, but misleading relative to stack.md | line 538–540 |
| §7.9 Plane2D — `show_coords=true` | Documented as working feature ("opt-in display of `(x, y)` coordinate labels") | `show_coords` IS in ACCEPTED_PARAMS (plane2d.py line 136) and read at line 194. | OK | line 545–548 |
| §7.10 MetricPlot example | `\shape{plot}{MetricPlot}{series=["cost","temp"], xlabel="step", ylabel="value"}` | Valid — matches ACCEPTED_PARAMS | OK | line 555 |
| §7.14 Queue selectors | Shows `q`, `q.cell[i]` (missing `q.front`, `q.rear`) | queue.py SELECTOR_PATTERNS includes `front`, `rear` | MED — incomplete selector table | line 587 |
| §8 Selector Quick Reference, Stack row | `.item[i]` only, no `.all` column | `validate_selector` does accept `all` | LOW | line 608 |
| §5.2 `\compute` — Starlark `def` | "Allowed" for `def` | Correct | OK | — |
| §3.2 Rules — `\narrate` "should have exactly one" | Doc says "should", implies optional | `environments.md` §3.4 says zero emits E1150 (incorrectly assigned) | MED — see spec/error-codes drift above | line 142 |
| §7.4 Graph weighted edges | Documents `("A","B",4)` 3-tuple form, `show_weights=true` | graph.py ACCEPTED_PARAMS includes `show_weights`; 3-tuple edge handling present | OK | line 472–473 |
| §5.3 `\step[label=…]` charset | `[A-Za-z_][A-Za-z0-9._-]*` | Must cross-check grammar.py `_try_parse_step_options` | MED — charset in doc may not match lexer impl | line 198 |

---

## docs/README.md findings

**LOW — Version claim.** `docs/README.md` line 1 states "Scriba v0.6.0 — 3 renderers, 16 primitive types". The README is consistent with the current package state (16 primitives confirmed in `__init__.py`). The v0.6.0 version claim is forward-looking relative to the RFC target releases — no action needed unless the deployed version differs.

---

## docs/planning/phase-c.md findings

**MED — `\fastforward` (E3) spec present (lines 69–80).** Phase-c.md §3.1 gives a full implementation spec for `\fastforward` including new files (`fastforward.py`, `starlark_rng.py`), parser changes, and Starlark host changes — despite the header note at line 4 explicitly stating it was removed. This section should be struck through or removed to prevent future contributors from implementing a feature that was intentionally dropped. The `figure-embed.md` also still references `\fastforward` (see extensions findings above), compounding the confusion.

---

## Recommended actions

### Critical (block release)
None — no show-stopper bugs found.

### High (fix before authoring or agent use)

1. **Stack: add `ACCEPTED_PARAMS` frozenset** to `scriba/animation/primitives/stack.py`. Add `{"orientation", "max_visible", "items", "label"}`. Without it, E1114 strict validation is bypassed for Stack entirely.

2. **Stack: implement or remove `s.bottom` and `s.range[lo:hi]` selectors.** `stack.md` documents them; `validate_selector` and `addressable_parts` do not implement them. Either wire them in `stack.py` or remove from `stack.md` lines 95–98.

3. **Matrix: remove `title` from `matrix.md` §2.2 optional params table** (line 73) or add `"title"` to `MatrixPrimitive.ACCEPTED_PARAMS` and implement it in `emit_svg`. Current state: `title=` in a `\shape` call raises E1114.

4. **MetricPlot: fix declaration example in `metricplot.md`** — remove top-level `yscale="linear"` from the `\shape{plot}{MetricPlot}{...}` block (lines 36–46). `yscale` is a per-series field, not a top-level param. As written, the example will fail with E1114.

5. **graph-stable-layout.md / graph.py: add `layout_lambda` to `Graph.ACCEPTED_PARAMS`.** The stable-layout spec documents it (line 60) but graph.py ACCEPTED_PARAMS (line 306–315) omits it. Authors using `layout="stable", layout_lambda=0.3` get E1114.

6. **RFC-001: add implementation status note.** Mark the Tree mutation ops (`add_node`, `remove_node`, `reparent`) and Graph edge mutation ops (`add_edge`, `remove_edge`, `set_weight`) as "designed, not yet implemented" so readers do not mistake the RFC's Python pseudocode for deployed API.

### Medium

7. **`environments.md` §3.4 and §6.2: fix E1150 collision.** The spec assigns E1150 to both "zero narrate warning" (§3.4, §6.2) and "Starlark parse error" (error-codes.md line 64, errors.py line 203). The zero-narrate case does not raise E1150 in code. Either assign a new code or remove the erroneous E1150 reference in §3.4/§6.2.

8. **MetricPlot: document `show_legend` and `show_current_marker`** in `metricplot.md` §2.2 optional params table. Both are functional (code lines 200–201, ACCEPTED_PARAMS lines 129–130) but invisible to authors from the doc.

9. **Plane2D: document `xlabel`/`ylabel`/`label` as reserved-but-no-op** in `plane2d.md` §2.1. The code comment at `plane2d.py` line 113–117 explains this is a v0.6.2 forward-declaration. The doc should say "accepted but not rendered; reserved for v0.6.2".

10. **Queue: add `q.front` and `q.rear` to `SCRIBA-TEX-REFERENCE.md` §7.14 selectors** (line 587). Currently only `q.cell[i]` is shown.

11. **`figure-embed.md` line 34: remove `\fastforward` cross-reference.** Stale reference to a removed feature.

12. **`planning/phase-c.md` §3.1: redact or strike out the `\fastforward` implementation spec** to prevent confusion.

13. **`hl-macro.md` vs `SCRIBA-TEX-REFERENCE.md`: reconcile `\step` label charset.** Decide whether uppercase and `-`/`.` are allowed (SCRIBA-TEX-REFERENCE says yes; hl-macro says `[a-z...]` only) and update whichever doc is wrong.

### Low

14. **`primitives.md` §6 Graph: document the `seed` alias** for `layout_seed` or explicitly deprecate it. Currently undocumented but functional.

15. **`SCRIBA-TEX-REFERENCE.md` §8 Stack row**: add `.all` to the All column — `validate_selector` accepts it.

16. **`docs/primitives/SANITIZER-WHITELIST-DELTA.md`**: technically accurate for the 5 Pivot-2 primitives it covers (Matrix, Stack, Plane2D, MetricPlot, Graph stable). No drift found.

17. **RFC-002 implementation status**: verify `CollectedWarning` / `RenderContext.strict` against `scriba/core/artifact.py` and `context.py` in a follow-up pass.
