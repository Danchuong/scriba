# Agent 02: Spec Internal Consistency

**Score:** 6/10
**Verdict:** ship-with-caveats

## Prior fixes verified

- **H7:** PARTIAL — environments.md §3 now documents 12/14 commands (was 8). Missing: 2 additional commands not yet identified in headers (comment at line 128 claims "14" but only 12 subsections §3.1–3.12 exist).
- **M9:** PRESENT — `\recolor` deprecation note added at environments.md §3.7 line 210; both environments.md and ruleset.md consistently direct authors to `\reannotate` for annotation recoloring.
- **M10:** RESOLVED — PHASE-D-PLAN.md not referenced in v0.5.0 active spec.
- **M11:** PRESENT — fastforward extension removed from all spec cross-references; docs/extensions/SANITIZER-WHITELIST-DELTA.md and hl-macro.md remain but are not imported into v0.5.0 spec.
- **C1:** PRESENT — all 6 fastforward internal links removed; zero references in environments.md, ruleset.md.
- **C2:** RESOLVED — scriba-filmstrip terminology not used in animation-css.md; HTML/SVG contracts are stable.
- **H2:** CRITICAL — §5.3 numbering duplicated in ruleset.md (line 368 "Data-Structure Primitives", line 378 "Graph Layout Modes" — both labeled §5.3).
- **M1:** PRESENT — SubstoryBlock terminology consistent (line 77 ruleset.md); no contradiction with SubstoryCommand found.

## Critical Findings

### C1: Duplicate section number §5.3 (ruleset.md:368,378)
ruleset.md contains two subsections both labeled "### 5.3": "Data-Structure Primitives (5)" at line 368 and "Graph Layout Modes" at line 378. Second should be renumbered to "### 5.4". Cascading: all subsequent subsections (5.4 Tree Variants, 5.5 Plane2D, etc.) are one level off.

### C2: Broken file reference in primitives.md (primitives.md:7,46,560)
Three cross-references cite `04-environments-spec.md` by old name. Should be `environments.md`. Link target exists but label is stale (v0.5.0 renamed file).

### C3: Command count mismatch (environments.md:128)
Header claims "14 inner commands" but §3 defines only 12 subsections (§3.1–3.12). Breakdown: base 8 (shape, compute, step, narrate, apply, highlight, recolor, annotate) + 4 new in v0.5.0 (reannotate, cursor, foreach/endforeach, substory/endsubstory) = 12 total. Comment is aspirational or incomplete; clarify the actual inventory.

## High Findings

### H1: Section 5.2 reference wrong in svg-emitter.md (svg-emitter.md:199)
Table references `§5.2` for Array layout. In ruleset.md, Array is under §5.1 (Base Primitives), not §5.2 (Extended Primitives). Cross-reference should be `§5.1`.

## Medium Findings

### M1: Primitives.md file labels inconsistent (primitives.md header)
Primitives spec says "06 — Primitive Catalog" but is actually the locked base 6-primitive spec (not extended 16-type catalog in ruleset.md). No contradiction, but title is ambiguous.

## Low Findings

### L1: Extension references not validated (ruleset.md:1019+)
§14 "Cross-References" table lists `extensions/substory.md`, `extensions/hl-macro.md`, `extensions/keyframe-animation.md`, etc. No broken links found, but these are informational only (not imported into v0.5.0 spec).

## Notes

- **Fastforward removal verified**: All references to `\fastforward` command and `fastforward` parameter successfully removed from v0.5.0 spec. Extensions remain in docs/extensions/ for future use but do not interfere with core spec.
- **Reannotate adoption confirmed**: Both environments.md and ruleset.md consistently use `\reannotate` for annotation recoloring; `\recolor` color/arrow_from params marked deprecated with cross-reference.
- **Selectors consistent**: environments.md §4 and primitives.md §2.2–§10 agree on selector grammar and per-primitive syntax.
- **Error code coverage**: §11 (ruleset.md) and §11 (environments.md) enumerate same E-codes; no orphan errors found.

**Recommend:** Fix C1 (renumber §5.4+), C2 (update file refs to environments.md), C3 (verify command claim; adjust to 12 if intentional), H1 (correct svg-emitter cross-ref to §5.1). Then ship.
