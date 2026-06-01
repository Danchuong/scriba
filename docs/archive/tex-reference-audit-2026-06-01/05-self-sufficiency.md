# Self-Sufficiency Audit

**Doc audited:** `docs/SCRIBA-TEX-REFERENCE.md` (1494 lines)
**Criterion:** Self-sufficiency — does the doc honor its L3 promise ("Read this one file to write valid Scriba `.tex` sources"), or does it force authors to open other files to author?

## Verdict: **Medium** self-sufficiency

The doc is *mostly* self-sufficient for authoring. Every external pointer was located and classified. The good news: the most prominent external references (smart-label ruleset, errors.py, ruleset.md §6.5, the dptable example) defer **maintainer-only** detail or are redundant with inline content — authors do not need them. The one genuine gap is the **smart-label callout in §5.8 (L344-347)**, whose imperative tone ("Read that document before…") wrongly signals authors must leave the file. Two pointers (§5.8, §15) are mis-framed and should be softened/labeled internal. No referenced file contains author-required data that is *missing* inline; the §6 CSS pointer correctly defers exact hex values that authors don't need (semantic color names are already in the table).

## Findings

| # | External ref (doc line) | Defers what | Author-need? | Verdict | Severity | One-line fix |
|---|---|---|---|---|---|---|
| 1 | §5.8 L344-347 → `spec/smart-label-ruleset.md` ("Read that document before changing `_svg_helpers.py`…") | Pill placement, collision avoidance, viewBox headroom, `SCRIBA_DEBUG_LABELS`/`SCRIBA_LABEL_ENGINE` internals | **NO** — these are emitter internals; authors only place `\annotate`, they don't tune the engine. Env flags are already documented inline in §13.12 (L1436-1444). | OK TO DEFER — but **reframe** | **HIGH** (mis-framing, not missing content) | Change "Read that document before changing…" to "Maintainers changing `_svg_helpers.py` or `emit_svg` should consult [spec/smart-label-ruleset.md]". Add "(authors do not need this)". The imperative "Read that document" directly contradicts the L3 single-file promise. |
| 2 | §6 L628 → `scriba/animation/static/scriba-scene-primitives.css` | Exact CSS fill/stroke/text **hex token values** per state (e.g. `--scriba-state-idle-fill: #f8f9fa`, current `#0070d5`, etc. — confirmed present in CSS L126+) | **NO** — authors pick states by semantic name (`current`, `done`, `good`…); the §6 table (L616-626) already gives the semantic color (blue/green-tinted/etc.). Exact hex is for theming/CSS overrides, not `.tex` authoring. | OK TO DEFER | LOW | None required. Optionally append "(for theming/overrides only)" to L628 to make the maintainer-scope explicit. |
| 3 | §5.2 L271 → `examples/integration/test_reference_dptable.tex` | A full worked 2D-DP animation using the nested-loop `\compute` pattern | **NO** — it's a "see also" enrichment. The inline example at L251-269 already shows the full pattern; §9.3/§9.7 give complete runnable animations. Authoring is possible without opening it. | OK TO DEFER | LOW | None. Pointer is correctly framed as supplementary ("for the full … animation"). |
| 4 | §5.11 L550-551 → `spec/ruleset.md §6.5` ("broader `\compute` scope rules") | Global vs frame-local binding scope, shadowing, `${name}` resolution order, E1155 | **NO** — §6.5 (verified) only restates what is *already inline*: §5.2 L238 (prelude vs in-step `\compute`, frame-local drop) and §5.11 L533-547 (loop-var scope). No new author-facing rule lives only in §6.5. | OK TO DEFER | LOW | None. Redundant-but-harmless cross-link. |
| 5 | §15 L1469 → `scriba/animation/errors.py` → `ERROR_CATALOG` | The full error-code catalog (doc lists only "top author-facing codes") | **PARTIAL** — an author hitting a non-listed E-code (e.g. E1004, E1052, E1320, E1437 referenced elsewhere in the doc but absent from the §15 table) must open a `.py` source file to decode it. | OK TO DEFER (inline is impractical), but **gap exists** | MEDIUM | Either (a) point to the rendered `docs/spec/error-codes.md` (exists, 22.9K) instead of a `.py` internal, or (b) add the E-codes the doc itself cites (E1004, E1005, E1052, E1320, E1321, E1437, E1113, E1471/2, E1433-6) to the §15 table so the doc is closed over its own references. |
| 6 | §0.1 L18 → `README.md` ("full install instructions") | Install steps for Python/Node prerequisites | **NO** — this is environment setup, not `.tex` authoring. L18 already states the version prereqs inline (Python 3.10+, Node 18+). | OK TO DEFER | LOW | None. Correct scope boundary. |
| 7 | §5.3 L290 → "(§7.1 of the spec)" | Spec section for `\hl` `:target` mechanics | **NO** — `\hl` usage is fully documented inline in §5.13 (L578-610). The "§7.1 of the spec" reference is an orphan/internal pointer with no filename. | OK TO DEFER, but **fix orphan ref** | LOW | Replace "(§7.1 of the spec)" with "(see §5.13)" — the info is in *this* doc, so the external-spec pointer is both wrong and unnecessary. |
| 8 | §5.8 L366 / L361 → "R-22", "R-06", "Hirsch 1982 NE-preference ladder" | Internal ruleset rule IDs / academic citation for side-hint inference | **NO** — pure internal/algorithmic provenance. Author-facing behavior (default side, `side=` override) is stated inline at L359-378. | OK TO DEFER | LOW | None. (Cosmetic: the bare "R-22"/"R-06" tokens read as dangling jargon to an author; could drop them.) |
| 9 | §13.1 / §7.x → "GEP-20", "(R-32)", "(R-22, v0.11.0+)" scattered | Internal proposal/rule identifiers | **NO** — behavior is described inline at each site (e.g. §13.8 R-32 headroom fully explained L1414-1419). | OK TO DEFER | LOW | None. |

## Prioritized Fixes

1. **HIGH — §5.8 L344-347 (finding #1).** Reframe the smart-label callout. The line "**Read that document before changing** `_svg_helpers.py`…" is the single clearest violation of the L3 promise: it issues an imperative to leave the file. Reword as a maintainer-only note and add "(authors do not need this)". This is the headline fix.

2. **MEDIUM — §15 L1469 (finding #5).** Close the doc over its own error codes. The doc *cites* ~15 E-codes (E1004, E1005, E1052, E1320, E1321, E1437, E1113, E1115, E1471/2, E1433-6, E1173, E1502, E1501…) but the §15 table lists only a subset, forcing a jump to `errors.py` (a source file) or an unreferenced spec. Add the self-cited codes to the table, and repoint the "full catalog" link to `docs/spec/error-codes.md` rather than a `.py`.

3. **LOW — §5.3 L290 (finding #7).** Fix the orphan "(§7.1 of the spec)" → "(see §5.13)". Self-contained info is wrongly pointed outward.

4. **LOW — §6 L628 (finding #2).** Optional: annotate the CSS pointer as theming-only so its maintainer scope is unambiguous.

## Notes

- Verified `scriba-scene-primitives.css` does contain the exact per-state hex tokens (L126+); they are correctly omitted from the doc because authors select states by name, not hex.
- Verified `ruleset.md §6.5` adds no author-facing rule absent from the main doc (it duplicates §5.2 and §5.11 inline content).
- Verified `smart-label-ruleset.md` (1166 lines) is an emitter/algorithm spec — correctly maintainer-scoped.
- No external pointer was found that hides authoring-critical data the author cannot reconstruct from inline content. The doc keeps the *spirit* of the L3 promise; the gaps are framing (finding #1) and self-citation closure (finding #5).
