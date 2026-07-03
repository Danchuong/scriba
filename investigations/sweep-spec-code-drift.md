# Sweep: spec ↔ code drift

> **STATUS: CLOSED 2026-07-03** — ruleset guard structural + in-suite, diagram options wired, grid=/side= phantoms removed, §8 matrix + refs reconciled (93863ec). Guards: `tests/doc_coverage/test_ruleset_sync.py`, `test_smart_label_lint.py`.

**Date:** 2026-07-02 · **Code baseline:** 0.21.2 (`SCRIBA_VERSION` 11), HEAD `369e80f`
**Audience lens:** ranked by how badly the drift misleads a human author or an AI agent *writing `.tex`*. Engine-internal drift (misleads maintainers/AI editing the renderer) is capped lower on that axis and labelled as such.

Drift window: 26 commits since `ad2e91d` (v0.21.0). Docs touched in-window: `CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/SCRIBA-TEX-REFERENCE.md`, `docs/spec/animation-css.md`, `docs/spec/environments.md`, `docs/spec/smart-label-ruleset.md`.

---

## Method (what was cross-checked, tools run + output)

**Tools run (`.venv/bin/python`, read-only):**

- `scripts/check_ruleset_sync.py` → `ERROR: expected 31 rules, found 33` / **exit 1**. The guard hardcodes `if len(rules) != 31` (line 35) but the ruleset now defines 33 numeric `### R-NN` cards (R-32 intentionally skipped; +R-27b/R-27c non-numeric). It is **not wired into any workflow** (no `.github/workflows/`, no Makefile/pre-commit/pyproject reference — grep returns nothing). Last touched `7b621cb` (Apr 22, R-31); the ruleset gained R-33/R-34 in `f2d0e21` (Jul 2) without a guard bump. Even when it passes it only checks *file exists* + *lineno ≤ file length* (lines 54-64) — never that the cited symbol is at the cited line, so it cannot catch the line-ref rot below.
- `scripts/lint_smart_label.py` → 11 errors, **advisory (exit 0)**, also unwired. Flags live FP-2/FP-5/FP-6 patterns in `graph.py:1279`, `numberline.py:321/323/333`, `plane2d.py:698/704/1020/1029`, `queue.py:280/283/294` — corroborates R-30 (NumberLine bypass still present) and the R-31 shared-registry rule.

**Cross-checks performed:**
1. `docs/spec/smart-label-ruleset.md` R-01..R-34: every code-ref/test-ref line and every load-bearing constant vs `scriba/animation/primitives/_svg_helpers.py` (+ `base.py`, primitives, `_frame_renderer.py`, `_html_stitcher.py`, CSS) and vs `tests/unit/`.
2. `docs/spec/animation-css.md` + `docs/spec/environments.md` vs emitters/`constants.py` (data-* names, aria, option wiring, §8.4 KaTeX sites). *(delegated agent, cross-verified quotes)*
3. `docs/SCRIBA-TEX-REFERENCE.md` + `README.md` + `CHANGELOG 0.21.2` vs parser/primitives (selectors, `side=`, `split_labels`, states/colors, error codes). *(delegated agent, cross-verified)*
4. `tests/doc_coverage/` reviewed so covered ground is not re-reported (see Cleared).
5. `investigations/*.md` "Resolution" claims vs current code. *(delegated agent)*

**Ground-truth constants confirmed in code (`_svg_helpers.py`)** — all match the values in the brief, so *drift is doc-side, not code-side*: `_KIND_WEIGHT` pill 1.0 / target_cell 3.0 / axis_label 2.0 / source_cell 0.5 / grid 0.2 / **content_cell 0.02** (:290-301); `_W_OVERLAP 10.0` `_W_DISPLACE 2.0` `_W_SIDE_HINT 5.0` `_W_SEMANTIC 2.0` `_W_WHITESPACE 0.3` `_W_READING_FLOW 0.8` `_W_EDGE_OCCLUSION 40.0` (:318-324); touch sentinel **3.0 px²** (:596-597, comment notes 1.0→3.0); nudge **48 = 8 compass × 6 steps 0.25/0.5/1.0/1.5/2.0/2.5** (:907-909); `_DEGRADED_SCORE_THRESHOLD 200.0` measured **net of `_content_cell_penalty`** (:332, :2077-2082, :2453-2458); `_PILL_EDGE_CLEAR 1` (:1411); `_ESCAPE_LANE_CLEAR 4.0` (:1416); leader `_LEADER_DISPLACEMENT_THRESHOLD 20.0` (:107) / `_LEADER_GAP_FACTOR 1.0` (:352) / `_LEADER_ARC_CLEARANCE_PX 4.0` (:357).

---

## Findings

Ranked by `.tex`-author / AI-authoring impact. **Grade** = drift class: `AUTHOR-BREAK` (produces failing or wrong `.tex`), `SILENT-WRONG` (renders but ignores author intent), `STALE-STATUS`, `NUMERIC`, `STALE-REF`, `DEAD-GUARD`, `CROSS-DOC`, `UNDER-DOC`.

### F1 — `grid=` option: docs say "accepted / ignored", code hard-errors E1004
- **Severity:** HIGH · **Grade:** AUTHOR-BREAK
- **Spec:** `docs/spec/environments.md:458` (§7) "*`grid=on` is accepted but is authoring-only*"; `docs/SCRIBA-TEX-REFERENCE.md:1470` (§10 table) "`grid` … Accepted but ignored", `:1646-1648` (§13.10), `:1723` (Appendix A) "Accepted but **ignored** — forward-compat placeholder."
- **Code:** `scriba/animation/constants.py:48-50` `VALID_OPTION_KEYS = {width,height,id,label,layout}` (no `grid`; comment :45-47 "dropped in 0.21.2 … fail fast with E1004"); `scriba/animation/parser/grammar.py:523-532` raises E1004 on any unknown key; `errors.py:114`.
- **Drift / who:** `\begin{diagram}[grid=on]` now **aborts the render**. Four stale locations across the two primary authoring docs — including the exact "port old sources" use-case they describe. CHANGELOG 0.21.2 announced the removal; the reference/spec were never updated. Misleads authors *and* AI agents porting older `.tex`. (Not caught by doc_coverage: a diagram with `grid=` is a `neg_` case only if someone wrote one.)

### F2 — `\annotate{…}{side=…}` documented as a functional override; parser silently ignores it
- **Severity:** HIGH · **Grade:** SILENT-WRONG
- **Spec:** `docs/SCRIBA-TEX-REFERENCE.md:407` (§5.8 param table) "`side` … Force the pill's half-plane: left/right/above/below"; prose `:409-410`; worked example `:417` `\annotate{dp.cell[3]}{…, side="below"}`. Reinforced by ruleset R-22 (`smart-label-ruleset.md:406`) which calls `side=` a "redundant" author param.
- **Code:** `side` is never carried through the parse chain — `parser/_grammar_commands.py:213-261` (`_parse_annotate`) reads only position/color/arrow/ephemeral/arrow_from/label; `parser/ast.py:213-225` `AnnotateCommand` has no `side`; `scene.py:110-120` `AnnotationEntry` has no `side`; `renderer.py:302-308` builds the layout dict without `side`. `_svg_helpers.py:2037,2396` has latent `ann.get("side") or ann.get("position")` support, but nothing upstream ever populates `"side"` → always falls back to `position`.
- **Drift / who:** The real half-plane knob is `position=` (documented and working). `side=` is a phantom duplicate that renders with **no error and no effect**. An author copying the §5.8 example to force a pill below gets the default/auto side. Silent, high-copy-rate surface.

### F3 — Diagram `label=` / `width=` / `height=` documented (with a worked example) but never wired
- **Severity:** HIGH · **Grade:** SILENT-WRONG
- **Spec:** `docs/spec/environments.md:117-120` (§2.4 "Applies to: animation, **diagram**"; `label` = "`aria-label` for the outer `<figure>`"), `:458` (§7 "width/height/id/label options apply"), `:544` (§8.2 shape shows `aria-label`), and the §12.3 worked example `:879` `\begin{diagram}[id=bst-demo, label="A small binary search tree"]` → `:891-892` expected `<figure class="scriba-diagram" … aria-label="A small binary search tree">`.
- **Code:** `scriba/animation/renderer.py:819-823` `DiagramRenderer.render_block` calls `emit_html(scene_id,[frame],primitives, mode="diagram", render_inline_tex=…, minify=…)` — passes **no label/width/height**. Defaults (`_html_stitcher.py:718-731`) yield `aria-label=""` (suppressed) and no `max-*` style. The plumbing exists and is unfed (contrast `AnimationRenderer.render_block` `renderer.py:504-514`, which passes all four — see Cleared).
- **Drift / who:** Documented diagram accessibility/size options are dead; the §12.3 example output is wrong. Silently loses `aria-label` for screen-reader users; misleads authors/agents emitting `\begin{diagram}[label=…]`. (CHANGELOG's "honoured end-to-end" claim is true only for *animation*; the environments spec over-promises for diagram.)

### F4 — `split_labels` documented as node-label wrapping; code splits edge-weight pills on `/`
- **Severity:** MEDIUM · **Grade:** SILENT-WRONG
- **Spec:** `docs/SCRIBA-TEX-REFERENCE.md:762` (§7.4) "`split_labels` … Split long node labels across two lines".
- **Code:** `scriba/animation/primitives/graph.py:1537-1557` — split applies to `display_weight` (edge-weight pill), triggered by a `/` separator, rendering bold-primary + dim-secondary tspans (flow/capacity style). Never touches node labels. CHANGELOG 0.21.2 correctly calls these "graph split **edge** labels"; the reference doc does not.
- **Drift / who:** Wrong on target (node→edge), trigger ("long"→`/`-separated), and effect. Author setting `split_labels=true` to wrap node names gets nothing. *Related-but-cleared:* the math half of this area (edge-weight `$…$` no longer escapes raw) **is** fixed and correct — `graph.py:1549` routes math weights to the KaTeX single-value path via `not _label_has_math(...)` (verified; see Cleared).

### F5 — `.scriba-state-hidden` CSS class + `--scriba-state-hidden-*` vars documented but not implemented
- **Severity:** MEDIUM · **Grade:** SILENT-WRONG
- **Spec:** `docs/spec/environments.md:620` (§9.2) "`.scriba-state-hidden` — present in the document model but invisible"; `:642-643` (§9.3) `--scriba-state-hidden-fill/stroke: transparent`.
- **Code:** No such class or vars exist (`scriba-scene-primitives.css` defines only idle/current/done/dim/error/good/highlight/path). "hidden" is implemented by **omitting the element** (`constants.py:29-31`; `graph.py:1611`, `tree.py:714` `if state=="hidden": continue`). `animation-css.md §11.3` also omits it.
- **Drift / who:** Theme authors overriding `--scriba-state-hidden-*` get no-ops; consumers expecting a present-but-transparent `<g>` find the node absent from the DOM.

### F6 — smart-label §8 conformance matrix marks shipped rules "Gap" and omits R-33/R-34
- **Severity:** MEDIUM (engine/AI-maintainer axis; low for pure `.tex` authors) · **Grade:** STALE-STATUS
- **Spec:** `docs/spec/smart-label-ruleset.md:1049-1083` (§8 matrix). Marks R-02, R-04, R-05, R-06, R-10, R-17, R-18, **R-20**, R-21 as "Gap / planned v0.12.0". Matrix columns stop at `v0.13.0+` — no v0.15/v0.21 column — and **R-33 and R-34 are absent from the matrix entirely**.
- **Code (shipped):** R-02 target-cell obstacle built `base.py:940` (`kind="target_cell"`); R-05 `_SEMANTIC_RANK`/`semantic_rank()` `_svg_helpers.py:307,695`; R-17 min-overlap fallback `:825,853`; R-18 `emit_annotation_arrows` obstacle merge `base.py:796,835`; R-20 `emit_position_label_svg` **now routes through `_place_pill`** (`_svg_helpers.py:3454+`, "EVERY position pill goes through _place_pill"), the legacy 4-dir loop retired.
- **Drift / who:** An AI agent or maintainer reading the matrix concludes the entire scoring engine is unbuilt and R-33/R-34 don't exist. This is the single most misleading artifact in the ruleset for anyone editing the renderer.

### F7 — R-31 prose states `_W_EDGE_OCCLUSION = 8.0`; code is 40.0
- **Severity:** MEDIUM (engine axis) · **Grade:** NUMERIC
- **Spec:** `docs/spec/smart-label-ruleset.md:1004` "assigned `severity="SHOULD"` and contribute `_W_EDGE_OCCLUSION = 8.0` to the candidate score via the P7 term."
- **Code:** `_svg_helpers.py:324` `_W_EDGE_OCCLUSION = _parse_weight_override("edge_occlusion", 40.0)`. 5× off. (It is the only literal `_W_*` value written into the ruleset prose, so no weight *table* exists to drift — this single stray number is the whole exposure.)
- **Drift / who:** Anyone reasoning about pill-vs-segment occlusion strength gets a value 5× too small.

### F8 — the ruleset sync guard is dead and broken (root-cause enabler)
- **Severity:** MEDIUM · **Grade:** DEAD-GUARD
- **Spec/claim:** `scripts/check_ruleset_sync.py:3-4` docstring "Run in CI to catch drift between ruleset and implementation."
- **Code/reality:** hardcoded `!= 31` (line 35) → **exit 1** today (33 rules); **not referenced by any CI/Makefile/pre-commit** in the repo; and even on the happy path it only validates *lineno-in-range*, never symbol-at-line (lines 54-64). This is why F6/F7/F10/F11 accumulated undetected.
- **Drift / who:** Gives maintainers false confidence that ruleset↔code is guarded. Fixing this (bump count, wire into CI, assert symbol at line) would have caught most ruleset findings here.

### F9 — R-17 / R-20 say "32 candidates" / "4-dir × 16-candidate"; code generates 48
- **Severity:** MEDIUM (engine axis) · **Grade:** NUMERIC
- **Spec:** `smart-label-ruleset.md:647,656,662` ("all 32 candidates"), `:915-916,922` ("32-candidate 8-direction", "legacy 4-direction × 16-candidate loop").
- **Code:** `_svg_helpers.py:907-909` `_nudge_candidates` "Generates **48** candidates = 8 compass directions × 6 step sizes" (was 8×4=32; now 8×6). The pill-placement investigation already noted a "32 nudges STALE" comment that code has since fixed to 48.
- **Drift / who:** Misleads engine maintainers on the search breadth; the R-20 "4-dir/16" description also describes retired code (see F6).

### F10 — systematic stale code-ref line numbers across nearly every shipped ruleset rule
- **Severity:** LOW-MEDIUM (engine axis) · **Grade:** STALE-REF
- **Cause:** the file grew and functions moved: `emit_arrow_svg` 634→**2573**, `emit_plain_arrow_svg`→**1886**, `_place_pill` 1213→**3283**, `emit_position_label_svg` 1337→**3413**, `_infer_side_hint`→**1489**, `_LEADER_DISPLACEMENT_THRESHOLD` 83→**107**, `_LABEL_PILL_PAD_Y` 69→**94**, `_LEADER_GAP_FACTOR` 330→**352**.
- **Examples (doc line → cited code line → what's actually there):** R-01 `:260`→`_svg_helpers.py:969` (real formula `label_ref_y = int(qy) - _est_pill_h//2 - 4` lives at **:2299**); R-07 `:485`→`:83` (line 83 is `_LABEL_MAX_WIDTH_CHARS=24`, not the threshold); R-08 `:509`→`:1198/1213`; R-19 `:901`→`:775/1170`; R-20 `:926`→`:1337`; R-22 `:410`→`:1101` (real `_infer_side_hint` at **:1489/2399**); R-25 `:206`→css `:647` (real `--scriba-annotation-path:#a78bfa` at css **:667/720**); R-26 `:871`→`:69` (real `_LABEL_PILL_PAD_Y` at **:94**); R-12/R-13 `:130/157`→`:527/659` (real `ARROW_STYLES` dict at **:1834**, dasharray at **:1980-1984**).
- **Drift / who:** Behavior at these rules is mostly *correct* (R-01 formula live, `ARROW_STYLES` exists, R-25 value `#a78bfa` correct) — only the pointers rot. An AI agent that jumps to the cited line lands on blank lines or unrelated function signatures. The sync guard (F8) cannot catch this by design.

### F11 — stale test-refs that resolve to nonexistent classes
- **Severity:** LOW-MEDIUM (engine axis) · **Grade:** STALE-REF
- **Spec/Code:** R-22 `smart-label-ruleset.md:411` cites `test_smart_label_phase0.py::TestSideHintUpperFirst` — **no such class**; the tests are module-level fns `test_side_hint_above_upper_first`/`_below_lower_first` (`:950,961`). R-19 `:902` cites `TestR19StderrDegradedWarning` — actual class is `TestR19DegradedWarning` (`test_w3_batch1.py:146`; the method `test_emit_arrow_svg_warns_on_degraded` at :169 exists). Both slip past the guard, which only checks the path before `::`. *(Cleared: all cited test **files** exist, and TestEscapeLanes/TestR25DarkModePathToken/test_visual_gap_formula_applied/test_constant_exported do exist.)*

### F12 — `label-rendering-investigation.md` backlog lists solved bugs as open
- **Severity:** LOW-MEDIUM (maintainer axis) · **Grade:** STALE-STATUS
- **Spec/Code:** "symptom 5" (`:74-76,231` — env `label`/`width`/`height`/`layout` "never forwarded / 0 consumers") is **shipped**: `renderer.py:503-509` now forwards all four to `emit_html`. "symptom 7" (`:82-84,231` — dangling `aria-labelledby` unconditional at `_frame_renderer.py:512`) is **fixed**: guarded at `_frame_renderer.py:518` with a diagram `narration_id_override=""` (`_html_stitcher.py:820`). Follow-up #5's three "chưa fix" items (`:184-188`) are all resolved by Follow-up #6 + current code (`_emit_pill_label_text` :1506; no first-fit loop at :3288-3335; `array._below_pill_width` deleted).
- **Drift / who:** Misleads a maintainer/AI into re-fixing already-solved bugs. (`pill-placement-space-investigation.md` Resolution + W4 are fully accurate — see Cleared.)

### F13 — Tree error-code semantics are tangled (doc ↔ catalog ↔ raise sites ↔ test all disagree)
- **Severity:** LOW-MEDIUM · **Grade:** CROSS-DOC (partially tracked)
- **Spec/Code:** `SCRIBA-TEX-REFERENCE.md:895` (§7.5) says E1433="cycle would be created". Raise sites: `tree.py:356-363` raises E1433 for *remove-node-with-children-without-cascade* **and** `tree.py:429-446` for reparent-cycle (overloaded); `errors.py:332-343` catalog disagrees with those raise sites; and `tests/doc_coverage` already **xfails** `prim_graph_tree_cycle_E1433` because the cycle case observes **E1435** in practice.
- **Drift / who:** An author debugging a "remove subtree without cascade" error is told (via §7.5) it means a cycle. Lookup/debugging confusion, not broken `.tex`. Partly covered by doc_coverage already; the doc↔catalog↔raise-site disagreement is the un-covered part.

### F14 — dangling "(R-32)" reference in the author-facing reference
- **Severity:** LOW · **Grade:** CROSS-DOC
- **Spec:** `docs/SCRIBA-TEX-REFERENCE.md:1628` (§13.8) tags the annotation-reservation gotcha "(R-32)". R-32 is **not defined in `smart-label-ruleset.md`** (which skips 32, going R-31→R-33); it lives in a *different* file, `docs/spec/ruleset.md:903` (§8.9 "Annotation Stable Layout"). A prior audit (`docs/archive/tex-reference-audit-2026-06-01/…`) resolved to strip this tag; it remains.
- **Drift / who:** An author/agent grepping the smart-label ruleset for "R-32" finds nothing (the two R-series numbering spaces collide in range). Cosmetic but cross-doc confusing.

### F15 — animation always emits an `aria-label` fallback; spec shows it optional
- **Severity:** LOW · **Grade:** UNDER-DOC
- **Spec:** `environments.md:502,544` (§8.1/§8.2) show `aria-label="{optional label}"`. **Code:** `_html_stitcher.py:281-286,684-693` `aria_label = label or "Animation"` (then first-frame label). Minor (a11y improvement); only misleads a byte-diff. Note the inconsistency with F3: animation defaults to "Animation", diagram emits nothing.

### F16 — emitters add many `data-*` attrs beyond the "frozen" §8 shape
- **Severity:** LOW / INFO · **Grade:** UNDER-DOC
- **Spec/Code:** `environments.md §8` calls the HTML shape "frozen", but emitters add `data-label` (`_html_stitcher.py:296,318`), `data-shape`, `data-node-x/-y` (`tree.py:751`), `data-scriba-series/-series-name`, `data-scriba-xrange/-yrange`, `data-scriba-speed`, `data-substory-id/-depth`, `data-scriba-frames`, `data-hl-step`. All additive, exact-named, not contradicted by the animation-css §12 selector table — low risk, but undocumented in the frozen contract.

**Already catalogued elsewhere (not re-reported as new):** `tests/doc_coverage/REPORT.md` already tracks 6 doc/code xfails (E1433→E1435 tree cycle, E1320→E1006 `\hl` order, `\step` hyphen-label E1012, `width=8cm` unit E1012) and doc-gaps (E1170/E1172/E1117 missing from §15, E1154-vs-E1150, E1421 colorscale, E1483 wording). The `check_render_sanity` duplicate-`id` defect on directed graphs (`scriba-arrow-fwd/rev`) is a known minor render bug, not doc drift.

---

## Cleared (verified in sync)

**Code constants ↔ brief:** every numeric in the Method block matches code exactly. The drift is doc-side; the *engine numbers are correct today*.

**smart-label-ruleset.md — behavior/refs that ARE accurate:** R-01 arc formula live (`_svg_helpers.py:2299`); R-33 content-cell weight 0.02 (doc §R-33:424 == code :301); R-34 escape lane `extent ∓ (pill_h/2+4)` == `_escape_lane_candidates` with `_ESCAPE_LANE_CLEAR 4.0`; R-15 `<title>` first child (`_frame_renderer.py:521`); R-16 aria-live region (`_html_stitcher.py:441`); R-11/R-14 annotation aria (`graphics-symbol` + `aria-roledescription="annotation"` + speech `aria-label` + raw-TeX `aria-description`, `_svg_helpers.py:1991-1994,2768-2771,3576-3579`); all cited **test files** exist; `ARROW_STYLES` exists (:1834). **`docs/spec/leader-line.md §3` is fully synced with code** (visual-gap gate `pill_h/2 + 4 + pill_h × _LEADER_GAP_FACTOR`, all four leader constants) — it is the authoritative leader doc and it is clean; R-27c matches it.

**environments.md §8.4 KaTeX 12-site list — COMPLETE and ACCURATE.** This is the surface that caused the earlier user-facing bug (9-of-12); it is now clean. All 12 site families map to real `render_inline_tex`/`_render_svg_text` call sites (cells, `\apply value=`, watch name/value, matrix row/col, stack/hashmap, plane2d point/line, codepanel caption, tree/graph node labels, numberline ticks, metricplot axes, **graph edge weights incl. `split_labels`** via `graph.py:1540-1566`), with no code math-site omitted; the "deliberately verbatim" list (codepanel code/line-numbers, numeric axis ticks, queue index labels) holds behaviorally.

**Option / state / color surfaces:** `VALID_OPTION_KEYS {width,height,id,label,layout}` == env §2.4:115-122 (no stale keys in that table); `VALID_SUBSTORY_OPTION_KEYS {title,id}` == §3.12; `VALID_STATES {idle,current,done,dim,error,good,highlight,path,hidden}` == §5.7/§6 (incl. `hidden`); `VALID_ANNOTATION_COLORS {info,warn,good,error,muted,path}` == §5.8/§11 (incl. `path`); `VALID_ANNOTATION_POSITIONS {above,below,left,right,inside}` == §5.8. Real `\annotate` params (arrow/arrow_from/label/color/position/ephemeral), `\reannotate` E1113, `\step` E1004/E1005/E1052, `\hl` E1320/E1321, lowercase booleans, queue `dequeue` truthy-only, and **`label=` as the sole caption knob** (no `caption=` param exists) all verified.

**Animation option wiring (correct for animation):** `label→aria-label`, `width/height→max-width/max-height` (`_size_style_attr`), `layout→data-layout` all fed from options at `renderer.py:504-514`. animation-css §12 `data-scriba-scene/-frame-count/-layout/-step/-target/-primitive` all emitted with exact names.

**E1004 raise + message**, README quickstart (`pip install scriba-tex`, `python render.py input.tex [-o|--open|--static]` matches `pyproject.toml` + `render.py` argparse), and **CHANGELOG 0.21.2 claims are code-accurate** (grid→E1004; split edge-weight `$…$` math no longer escapes raw).

**investigations/pill-placement-space-investigation.md** — Resolution + W4 match code exactly (content_cell 0.02, `resolve_self_content_rects` overrides, `_arc_wrap_px`, `_infer_side_hint` 4-direction, threshold 200 net-of-floor, `_escape_lane_candidates` center-coordinate math).

**tests/doc_coverage** guards 396 corpus snippets (render-OK-vs-error-code for documented features) + `check_render_sanity` (katex-error, NaN/Infinity/undefined, viewBox validity, duplicate ids). It does **not** assert: raw-unrendered `$…$` sites (a literal `$x$` passes sanity — exactly the KaTeX-completeness gap), attribute-name correctness, numeric placement constants, or prose semantics — which is why F1-F16 sit outside its coverage.

---

## Verdict

The dangerous, high-frequency drift is **author-facing and concentrated in the option/annotate surfaces of `SCRIBA-TEX-REFERENCE.md` + `environments.md`**, not in the engine numbers:

1. **`grid=` (F1)** turns a documented-safe key into a fatal E1004 — 4 stale doc locations.
2. **`side=` (F2)** is a fully-documented, worked-example control that the parser silently drops (real knob is `position=`).
3. **Diagram `label/width/height` (F3)** are documented (with expected-output example) but unwired — silent a11y loss.
These three will burn an author or an AI agent immediately and should be fixed first; all three are pure doc-side edits (or, for F2/F3, a one-line wire).

The **smart-label-ruleset.md** is internally drifted but *not* numerically wrong in code: its §8 status matrix is frozen at planning stage (F6), it carries one stray `8.0` (F7, real value 40.0), and essentially all its code/test line-refs have rotted (F10/F11) — all of which mislead an AI agent *editing the renderer*, not one writing `.tex`. The root enabler is that **`check_ruleset_sync.py` is dead and broken (F8)** and never ran; repairing + wiring it (and extending it to assert the symbol at the cited line) would have caught F6/F7/F9/F10/F11.

Good news the sweep confirms: the previously-buggy **environments.md §8.4 KaTeX site list is now complete and accurate**, **`leader-line.md §3` is fully in sync**, the CHANGELOG 0.21.2 claims hold, and the code constants all match the brief. The reconciliation debt is real but bounded and mostly mechanical.

---

## Structural Fix Design (2026-07-02)

Read-only design pass. No source touched. All touch-points are absolute-repo-relative `path:line` verified against HEAD `369e80f`; probes run with `.venv/bin/python`.

### Design summary

The 16 findings split into three landing tracks that are **mutually independent** and can ship in parallel:

- **Track A — author-facing docs (F1, F2, F3-doc-example):** pure prose edits to the two primary authoring docs. Highest user impact, zero code risk. F2 resolves to *delete* (see decision below), F1 resolves to *delete/annotate*, the F3 §12.3 example needs an orthogonal `id` quoting fix regardless of code.
- **Track B — one code wire (F3):** `DiagramRenderer.render_block` must forward `label/width/height` exactly as `AnimationRenderer.render_block` already does. The emitter half is already built and already unit-tested; only the renderer call site is unfed.
- **Track C — tooling + engine-doc reconciliation (F6–F12):** repair `check_ruleset_sync.py`, wire it into pytest, then let it (plus a one-time symbol-anchor migration) drive the smart-label-ruleset edits. These mislead maintainers/AI editing the renderer, not `.tex` authors.

Verified-in-code truths used below: `_W_EDGE_OCCLUSION = 40.0` (`_svg_helpers.py:324`); `_nudge_candidates` "Generates 48 candidates = 8 compass directions x 6 step sizes" (`_svg_helpers.py:907`); the ruleset carries **35 `### R-*` cards** (33 numeric R-01..R-34 with R-32 skipped, + R-27b/R-27c) each with exactly one `**Code ref:**` and one `**Test ref:**` line (35 == 35 == 35; 14 code-refs / 17 test-refs are `pending`).

### F2 decision — REMOVE `side=` from docs (do NOT wire it). Evidence-backed.

**Decision: retire the `side=` param from the docs; `position=` already is the working half-plane knob.** This is the opposite of the "small wire, big value" hypothesis — the probes disprove it.

Probes (`scratchpad/probe_f2_side.py`, `probe_f2_collision.py`, injecting `side` directly into an annotation dict / `ArrayPrimitive.set_annotations`):

| Scenario | pill (x,y) `position=above` | `position=above, side=below` | `position=below` |
|---|---|---|---|
| `emit_arrow_svg`, no collision | (70.0, 60.7) | (70.0, 60.7) | (70.0, 60.7) |
| `emit_position_label_svg`, no collision | (60.0, 63.2) | **(60.0, 63.2)** | (60.0, 130.2) |
| `ArrayPrimitive.emit_svg` end-to-end (text y) | [...,-13.0] | **[...,-13.0]** | [...,63.0] |
| `emit_arrow_svg`, forced collision above | (70.0, 89.2) | (70.0, 89.2) | (70.0, 89.2) |

Interpretation:
- **Position-only pills ignore `side` entirely.** `emit_position_label_svg` computes the base offset from `position` (`_svg_helpers.py:3481-3515`) and passes `side_hint=position` to `_place_pill` (`:3538`) — it **never reads `ann.get("side")`**. Injecting `side` is provably inert (row 2/3: B == A, not C).
- **Arrow pills read `side` but it is only a soft `side_hint`.** `emit_arrow_svg`/`emit_plain_arrow_svg` do `anchor_side = ann.get("side") or ann.get("position")` (`:2396`, `:2037`), but `side_hint` is a scoring preference (P3 term, `_W_SIDE_HINT = 5.0`) that did not move the pill in *either* the no-collision or the forced-collision probe. It does not "force" a half-plane.
- **For arrow annotations `position` ≡ `side`.** An arrow pill has no `position`-driven base offset (arc geometry sets it); `position` only feeds the same `side_hint`. So the §5.8 worked example could write `position="below"` for the identical (soft) effect — `side` adds nothing.
- **`position=` is the real, documented, hard half-plane knob** (above/below/left/right/inside), and R-22 (`smart-label-ruleset.md:406`) itself calls `side=` "redundant."

Cost of the *alternative* (wiring `side` to actually match the "Force the pill's half-plane" wording), for the record — it is **not** a one-liner:
1. `parser/_grammar_commands.py:_parse_annotate` (:213-261) — read + validate `side` against `{left,right,above,below}`.
2. `parser/ast.py:AnnotateCommand` (:213-225) — add `side: str | None = None`.
3. `scene.py:AnnotationEntry` (:110-120) + build site (:843) — add `side`, thread `side=cmd.side`.
4. `renderer.py:_snapshot_to_frame_data` (:300-311) — add `"side": a.side` to the dict.
5. `_svg_helpers.py:3538` — change `side_hint=position` → consult `ann.get("side")`.
6. To make it *force* (relocate a non-colliding pill), rewrite the base-offset logic (`:3481-3515`) so `side` overrides `position` — which then makes `side` a pure alias of `position` with a contradictory-precedence hazard (`position=above, side=below`).

Steps 1-5 deliver only an invisible soft hint (per probes); step 6 duplicates `position`. **Recommendation stands: delete `side` from docs.** (If the maintainer values R-22's explicit-override intent, the honest middle path is steps 1-5 **plus** re-wording the doc from "Force" to "Hint" — but that ships a knob whose effect authors cannot see, so it is not recommended.)

### F3 wiring spec — forward diagram env options (code)

The emitter half is **already built and tested**: `emit_html(mode="diagram")` forwards `label`+`size_style` into `emit_diagram_html` (`_html_stitcher.py:766-770, 789-831`), and `tests/unit/test_env_options_wired.py::TestEnvLabelWired::test_diagram_uses_env_label` + `TestSizeWired::test_diagram_size` already pass at the `emit_html` layer. The only unfed link is the renderer.

Confirmed end-to-end (`render_file` on a diagram with `[id=bstdemo, label="...", width=480]`): output is `<figure class="scriba-diagram" data-scriba-scene="bstdemo">` — **no `aria-label`, no `max-width`**. Matches F3.

Fix (single call site), mirror `AnimationRenderer.render_block` (`renderer.py:504-514`) at `DiagramRenderer.render_block` (`renderer.py:819-823`):

```python
# renderer.py:819-823 — current
html = emit_html(scene_id, [frame], primitives, mode="diagram",
                 render_inline_tex=ctx.render_inline_tex, minify=minify)
# target
_opts = getattr(ir, "options", None)
html = emit_html(scene_id, [frame], primitives, mode="diagram",
                 label=(getattr(_opts, "label", None) or ""),
                 width=getattr(_opts, "width", None),
                 height=getattr(_opts, "height", None),
                 render_inline_tex=ctx.render_inline_tex, minify=minify)
```

- **No `layout`** — `emit_diagram_html` is single-frame and has no `layout` param (correct; a diagram has no filmstrip/stack).
- **E-code validation is already free:** diagrams parse through the same `SceneParser().parse` (`renderer.py:787`) → `VALID_OPTION_KEYS` → `E1004` for unknown keys. `width/height/label/id` are valid `AnimationOptions` fields; bad *values* pass through as strings exactly as the animation path does (`_size_style_attr` just suffixes `px`) — no new validation, mirror animation exactly.
- **Orthogonal doc bug in the §12.3 example** (must fix in the same PR or the example still won't parse): unquoted `id=bst-demo` raises **E1012** (`bare IDENT` can't contain `-`); `id="bst-demo"` parses. The §10 charset note `[a-z][a-z0-9-]*` is only reachable when the value is quoted.

### F8 tooling fix + suite wiring

**Exact diagnosis.** `scripts/check_ruleset_sync.py:35` hardcodes `if len(rules) != 31` where `rules` is `re.findall(r"^### R-(\d+) — ...")` (numeric cards only). The ruleset now has **33** numeric cards (R-01..R-34, R-32 intentionally skipped), so it prints `expected 31 rules, found 33` and returns **1**. Last bumped `7b621cb` (R-31); R-33/R-34 landed `f2d0e21` without a bump. It is referenced by **no** CI/Makefile/pre-commit (grep-clean), and even on the happy path only checks *path-exists* + *lineno ≤ file length* (`:54-64`), never symbol-at-line — which is why F6/F7/F9/F10/F11 accumulated.

**Fix (make the count self-adjusting, not a new magic number).** A hardcoded `33` re-rots on the next rule. Replace the equality gate with a structural invariant:
1. Match **all** cards incl. suffixes: `r"^### R-([0-9A-Za-z]+) — (.+)$"` (35 today).
2. Assert every card carries ≥1 `**Code ref:**` and ≥1 `**Test ref:**` (parse into per-card spans; today 35 cards == 35 == 35). This catches "rule added without refs" — the count gate's real intent — with nothing to hardcode.
3. Make `RULESET` cwd-independent: `RULESET = REPO_ROOT / "docs/spec/smart-label-ruleset.md"` (currently a bare relative `Path(...)`, inconsistent with the `REPO_ROOT`-anchored code-refs) so it runs from any cwd.
4. (Optional, closes F10 permanently — see Citation style) once citations become `path:symbol`, replace the `lineno ≤ len` check with "grep the file for `def symbol` / `symbol =`", giving the guard a real symbol-at-anchor assertion.

**Pytest wiring (house style = `tests/doc_coverage/`).** Add `tests/doc_coverage/test_ruleset_sync.py` that shells out to the real entry point (robust to `scripts/` not being a package; `cwd=REPO` satisfies the relative-path read; runs in <100 ms):

```python
import subprocess, sys
from pathlib import Path
_REPO = Path(__file__).resolve().parents[2]

def test_ruleset_sync_guard_passes() -> None:
    r = subprocess.run([sys.executable, "scripts/check_ruleset_sync.py"],
                       cwd=_REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
```

This mirrors `test_doc_coverage.py`'s "run the real pipeline, assert the contract" shape and holds the ruleset guarded forever. (Import-mode `from check_ruleset_sync import main; assert main()==0` also works once step 3 lands, if a subprocess is undesirable.)

**`scripts/lint_smart_label.py` — wire as a count-ceiling ratchet, do not retire.** The 11 advisory hits (`graph.py:1279`; `numberline.py:321/323/333`; `plane2d.py:698/704/1020/1029`; `queue.py:280/283/294`) encode a real design contract (§5.3 FP-1..FP-6) and some are true positives (R-30 NumberLine bypass). Retiring loses signal; forcing `--strict` to zero risks blocking legit patterns. Add `tests/doc_coverage/test_smart_label_lint.py` asserting the ERROR-violation **count does not exceed the frozen baseline (11)** — a ratchet that fails only when a *new* violation is introduced, robust to line drift (count, not `file:line`). File a follow-up to triage the 11 (suppress design-intended ones with `@allow_forbidden_pattern`, fix the genuine R-30 bypass) and lower the ceiling as they clear. Mirrors `doc_coverage`'s `KNOWN_BUGS`-xfail "hold the line without blocking" idiom.

### Docs edit batch (table)

Grouped into 3 commits. `SL` = `docs/spec/smart-label-ruleset.md`, `REF` = `docs/SCRIBA-TEX-REFERENCE.md`, `ENV` = `docs/spec/environments.md`, `LRI` = `investigations/label-rendering-investigation.md`.

**Commit `docs(author): retire grid= and side= phantoms` (F1 + F2)** — highest impact, pure prose:

| File:line | Finding | Wrong text (current) | Corrected |
|---|---|---|---|
| ENV:458 | F1 | "`grid=on` is accepted but is authoring-only — it emits a faint grid over the stage" | "`grid` was removed in 0.21.2 and now raises `E1004` (unknown option key)" |
| REF:1470 | F1 | table row "\| `grid` \| bool \| _(n/a)_ \| diagram \| Accepted but ignored — see Appendix A \|" | delete the row (or "Removed in 0.21.2 — now raises `E1004`") |
| REF:1646-1648 | F1 | "…(`global_optimize`, the diagram `grid` option, `SCRIBA_DEBUG_LABELS`…) are not needed for authoring" | drop "the diagram `grid` option," from the list (it errors, it is not a no-op) |
| REF:1723 | F1 | App-A row "\| `grid` \| `\begin{diagram}` option \| Accepted but **ignored** — forward-compat placeholder. \|" | "Removed in 0.21.2 — now raises `E1004`." (or delete row) |
| REF:407 | F2 | param-table row "\| `side` \| enum \| _(auto)_ \| Force the pill's half-plane… \|" | delete the row |
| REF:409-410 | F2 | "Override with `side=\"below\"` when there is more clearance underneath." | "Override with `position=\"below\"` when there is more clearance underneath." |
| REF:417 | F2 | example line `\annotate{dp.cell[3]}{label="+5", arrow_from="dp.cell[1]", color=good, side="below"}` | `…, color=good, position="below"}` (and comment "force pill below" stays valid) |
| SL:406 | F2 | R-22 rationale "…eliminates the need for authors to add redundant `side=` parameters…" | keep, but ensure R-22 normative (`:396-397`) is not read as an *author* param: note `side=` is emitter-latent only, not a wired `\annotate` key |

**Commit `docs(diagram): fix §12.3 example` (F3 doc half)** — ship with the F3 code wire:

| File:line | Finding | Wrong | Corrected |
|---|---|---|---|
| ENV:879 | F3 | `\begin{diagram}[id=bst-demo, label="A small binary search tree"]` | `\begin{diagram}[id="bst-demo", label="A small binary search tree"]` (quote the id → parses; expected-output `aria-label` at ENV:891-892 becomes correct once the code wire lands) |

**Commit `docs(ruleset): reconcile smart-label §8 + numbers + refs` (F6, F7, F9, F11)** — engine-facing:

| File:line | Finding | Wrong | Corrected |
|---|---|---|---|
| SL:1004 | F7 | "contribute `_W_EDGE_OCCLUSION = 8.0` to the candidate score" | "`_W_EDGE_OCCLUSION = 40.0`" |
| SL:647 | F9 | "When all 32 candidates are exhausted" | "all 48 candidates" |
| SL:656 | F9 | "argmin pass over the already-computed 32 candidates" | "48 candidates" |
| SL:662 | F9 | "only fires when all 32 candidates are exhausted" | "all 48 candidates" |
| SL:915-916 | F9 | "the 32-candidate 8-direction `_nudge_candidates`… legacy 4-direction × 16-candidate loop MUST be retired" | "48-candidate 8-direction…"; note the legacy loop **is** retired (R-20 shipped) |
| SL:1049-1085 | F6 | §8 matrix marks R-02/R-04/R-05/R-06/R-10/R-17/R-18/R-20/R-21 as "Gap"; R-33/R-34 absent | flip those nine Status cells to "Shipped"; add R-33 + R-34 rows; add a note "R-32 intentionally unused (lives in `ruleset.md` §8.9)"; add a v0.15/v0.21 column (or collapse the release columns). **Re-verify every cell with the repaired guard before committing** — do not hand-flip blind |
| SL:411 | F11 | test-ref `…::TestSideHintUpperFirst` | `tests/unit/test_smart_label_phase0.py::test_side_hint_above_upper_first` (module fn, no class) |
| SL:902 | F11 | test-ref `…::TestR19StderrDegradedWarning::test_emit_arrow_svg_warns_on_degraded` | `…::TestR19DegradedWarning::test_emit_arrow_svg_warns_on_degraded` |

**Commit `docs(investigation): close resolved backlog` (F12)** — `LRI`, maintainer-facing status flips (all verified shipped in code):

| File:line | Wrong (status) | Corrected |
|---|---|---|
| LRI:71 | "Symptom 5 — env label drop (H5: CONFIRMED…)" open | mark RESOLVED — `renderer.py:503-509` forwards label/width/height/layout |
| LRI:80-84 | "Symptom 7 (ARIA) — dangling aria-labelledby ở diagram (CONFIRMED)" | mark RESOLVED — guarded at `_frame_renderer.py:518` + `narration_id_override=""` (`_html_stitcher.py:820`) |
| LRI:42 | E7 row "…id không tồn tại \| Confirmed" | Resolved |
| LRI:184-188 | Follow-up #5 "ĐÃ DRIFT — còn lại (chưa fix, chờ quyết)" 3 items | mark resolved by Follow-up #6 + current code |
| LRI:231 | final "Backlog còn:" lists symptom 5 + symptom 7 as open | strike symptom 5 and symptom 7 (both shipped) |

*(F14 `(R-32)` dangling tag at REF:1628 and F10 line-refs are handled by the citation-style migration below; F13/F15/F16 are out of this batch's scope.)*

### Citation-style recommendation (F10) — switch to symbol anchors

**Recommend: migrate every `path:line` code-ref/test-ref to `path:symbol` (function/constant name), not "re-number the lines."** Line numbers rot on every insertion (F10 shows ~10 already dead: `emit_arrow_svg` 634→2573, `_place_pill` 1213→3283, `emit_position_label_svg` 1337→3413, `_infer_side_hint`→1489, `_LEADER_DISPLACEMENT_THRESHOLD` 83→107, `_LABEL_PILL_PAD_Y` 69→94, `_LEADER_GAP_FACTOR` 330→352, …). Symbol anchors (a) can't rot under insertion, and (b) give `check_ruleset_sync.py` something it can actually verify (grep for `def <sym>`/`<sym> =`), turning F8's dead lineno-range check into a live symbol-at-anchor assertion.

Citations to convert (from F10 + this pass), each `…:NNNN` → `…:<symbol>`: R-01 `:260`, R-07 `:485`, R-08 `:509`, R-12/R-13 `:130/157`, R-17 `:659` (`_place_pill`), R-19 `:901` (`emit_plain_arrow_svg` / `emit_arrow_svg` stderr sites), R-20 `:926` (`emit_position_label_svg`), R-22 `:410` (`_infer_side_hint`), R-25 `:206` (css token `--scriba-annotation-path`), R-26 `:871` (`_LABEL_PILL_PAD_Y`), plus the eight moved symbols above. Where a citation points at a *value* (e.g. R-25 `#a78bfa`) anchor to the CSS custom-property name. Keep the 14/17 `pending` refs as-is (no symbol yet).

### TDD plan (failing tests first; follow `test_env_options_wired.py` idiom)

**F3 (RED → GREEN):** add to `tests/unit/test_env_options_wired.py` a *renderer-level* class (the existing tests only exercise `emit_html`; the gap is the renderer):

```python
class TestDiagramRendererForwardsOptions:
    # render through DiagramRenderer.render_block (or render_file on a .tex string)
    def test_diagram_label_reaches_figure(self):
        html = _render_diagram('[id="d", label="A small BST"]\n\\shape{a}{Array}{size=2}')
        assert 'aria-label="A small BST"' in html          # RED today (dropped)
    def test_diagram_width_becomes_max_width(self):
        html = _render_diagram('[id="d", width=480]\n\\shape{a}{Array}{size=2}')
        assert 'max-width:480px' in html                    # RED today
    def test_diagram_no_size_when_unset_is_byte_stable(self):
        html = _render_diagram('[id="d"]\n\\shape{a}{Array}{size=2}')
        assert 'style=' not in html.split('scriba-stage')[0] # guard byte-stability
```
Then wire `renderer.py:819-823` → GREEN. Also add a `tests/doc_coverage/corpus/` pair: `env_diagram_id_quoted_ok.tex` (`ok`) and a `neg_diagram_id_hyphen_bare_E1012.tex` (`error E1012`) to lock the §12.3 example's id fix.

**F2 (no code; lock the doc contract):** add a `tests/doc_coverage/corpus/` negative asserting `side=` is *not* a functional knob — e.g. render two diagrams identical but for `side=`, assert byte-identical SVG (proves removal from docs is truthful), or simply a doc-lint test that `side` no longer appears as an `\annotate` param in `REF`. Keep the existing `TestGridOptionRejected` (F1 already covered there).

**F8:** the two wiring tests above (`test_ruleset_sync.py`, `test_smart_label_lint.py`) are themselves the RED→GREEN: `test_ruleset_sync_guard_passes` fails today (exit 1) and passes after the script fix; the lint ratchet passes at ≤11 and fails if a 12th is introduced.

**F6/F7/F9/F10/F11:** the repaired `check_ruleset_sync.py` (structural + symbol-at-anchor) is the regression harness — after the doc edits + symbol migration it returns 0, and any future numeric/ref drift flips it red in CI.

### Landing order

Independent tracks; within each, top-to-bottom.

1. **F8 script repair + pytest wiring first** (Track C root). It is the harness that makes every later ruleset edit verifiable and prevents re-rot. Ship `check_ruleset_sync.py` fix + `test_ruleset_sync.py` + `test_smart_label_lint.py`. *Independent of everything else.*
2. **F3 code wire + its §12.3 doc/example fix + renderer TDD tests** (Track B). Self-contained; the emitter + `emit_html` tests already exist, so this is low-risk and high-value (restores diagram a11y). *Independent of Track A/C.*
3. **F1 + F2 author-doc commit** (Track A). Pure prose, no dependency; can land anytime, but do it *after* confirming F2 via the byte-identical probe so the "delete" is defensible. *Independent.*
4. **F10 symbol-anchor migration** — land *after* F8 step 1 (so the guard can validate the new anchors) but *before* the F6/F7/F9/F11 ruleset edits (so those edits are written in the rot-proof style).
5. **F6/F7/F9/F11 ruleset reconciliation** last — mechanical, gated green by the now-live guard. **F12** (investigation status flips) can ride alongside; it touches only the maintainer-facing backlog.

Critical path is only **1 → 4 → 5** (guard before symbol-migration before ruleset edits). Tracks A (3) and B (2) have no ordering constraint and can be done in parallel by separate hands.
