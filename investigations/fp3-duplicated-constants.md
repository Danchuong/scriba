# FP-3 — Duplicated Layout Constants (twin-drift) — Structural Fix Design

> Status: research / design only. No source touched. Deliverable for the person who lands the fix.
> Probes run with `.venv/bin/python` from repo root; every value below is machine-verified, not eyeballed.

---

## 1. Hand-off Brief

**The seed.** `scriba/animation/primitives/plane2d.py:1020` declares
`_LINE_LABEL_CHAR_W = 7` inside `Plane2D._emit_labels`, used one place —
`plane2d.py:1058` `est_w = len(label_text) * _LINE_LABEL_CHAR_W + _LINE_LABEL_PAD`.
It is a hand-rolled per-character advance width. The canonical width model is the
function `estimate_text_width(text, font_size)` in
`scriba/animation/primitives/_text_render.py:71` (Latin glyph = `0.62 em`,
CJK = `1.0 em`, combining marks = `0`, ZWJ clusters = `1 em`). Line labels render
at `_TICK_FONT_SIZE = 10` (`plane2d.py:54`), so the canonical Latin advance is
`0.62 × 10 = 6.2 px/char`. **`7 ≠ 6.2` — the pair has already drifted**, and it
drifts the *wrong way on CJK*: `estimate_text_width("斜率", 10) = 20` but
`len("斜率") * 7 = 14` — a **-6 px under-estimate** that under-sizes the pill and
lets CJK line-label text overflow. That is the exact a11y-regression family the
dual runtime shipped this week.

**Why this keeps happening.** The FP-3 linter
(`scripts/lint_smart_label.py::_check_fp3`) is a *name blocklist* that only scans
*assignments inside primitive-class method bodies*. It therefore sees exactly one
copy in the whole family — the seed — because the seed is the only twin that is
both (a) method-local and (b) named in `_FP3_SUSPICIOUS_NAMES`. Every other copy
(module-level constants, differently-named copies, and everything in the excluded
files `base.py`, `_svg_helpers.py`, `_text_render.py`, `_types.py`, `layout.py`)
is invisible to it. The linter's "1 FP-3 violation" is a *floor, not a census*.

**What the sweep actually found.** Two live drifted twins (a bug each), seven
already-equal twins (latent regrowth surface, zero-churn to consolidate), a family
of coincidental look-alikes that must **not** be merged, and one structural asset
worth copying (the Python↔JS timing boundary is already drift-proofed by slicing
the runtime out of `static/scriba.js`). The design below consolidates the true
twins, refuses the false ones, and replaces the name-blocklist guard with a
**constant-parity ratchet** grounded in the existing `tests/unit/test_css_font_sync.py`.

**The two live bugs (grade them loudly):**

| # | Bug | Where | Values | Grade |
|---|-----|-------|--------|-------|
| B-1 | Line-label width hand-rolled, drifted, **CJK under-sizes pill** | `plane2d.py:1020,1058` vs `_text_render.estimate_text_width` | `7` vs `6.2` (Latin), `7` vs `10` (CJK) | **HIGH** (a11y: CJK/diacritic overflow) |
| B-2 | Graph edge-weight pill drifted from canonical pill after the FP-3 sweep skipped `graph.py` | `graph.py:88-90` `_WEIGHT_PILL_PAD_X/Y/R = 5/2/3` vs `_svg_helpers.py:93-95` `_LABEL_PILL_PAD_X/Y/RADIUS = 6/3/4` | `(5,2,3)` vs `(6,3,4)` | **MEDIUM** (visual inconsistency; every weighted-graph frame) |

B-2 is the smoking gun for the whole thesis: the earlier FP-3 remediation
reconciled the *same* `(5,2,3) → (6,3,4)` pill lineage in `plane2d.py:1023-1025`
(the `# was: 5/2/3 (FP-3 fix)` comments) but **never touched `graph.py`**, so the
two pill lineages silently diverged. A name-blocklist guard cannot catch this —
`_WEIGHT_PILL_*` is module-level.

---

## 2. Seed analysis

| Fact | Value | Source |
|------|-------|--------|
| Seed constant | `_LINE_LABEL_CHAR_W = 7` | `plane2d.py:1020` (method-local, `Plane2D._emit_labels`) |
| Sole consumer | `est_w = len(label_text) * _LINE_LABEL_CHAR_W + _LINE_LABEL_PAD` | `plane2d.py:1058` |
| Label font | `_TICK_FONT_SIZE = 10` | `plane2d.py:54`, applied at `plane2d.py:1107` |
| Canonical model | `estimate_text_width(text, font_size)` → `int(Σ_char width · font + 0.5)` | `_text_render.py:71` |
| Canonical per-char (Latin) | `_char_display_width('a') = 0.62` → `6.2 px` at font 10 | `_text_render.py:54,68` |

**Does `7` name a constant in `_svg_helpers.py`?** No. The FP-3 message
("duplicates a named constant in `_svg_helpers.py`") is *inaccurate for this
case*: there is **no** `_CHAR_W`/char-width constant anywhere. The canonical is a
*function* (`estimate_text_width`) whose `0.62` lives inside `_char_display_width`.
So the seed's true canonical home is `_text_render.py`, and the fix is **call the
function**, not import a number. Note the point-label branch **12 lines above**
already does exactly that: `plane2d.py:1008` uses
`estimate_text_width(_label_width_text(str(label_text)), _TICK_FONT_SIZE) + 12`.
The seed is a hand-rolled *second* width model living beside the canonical one in
the same method.

**Do they agree today? No — machine-verified drift:**

```
text            len  hand=len*7   canon=estimate_text_width(·,10)   drift
'y=2x+1'          6      42                37                        +5
'y = 3x - 5'     10      70                62                        +8
'斜率'            2      14                20                        -6   ← pill UNDER-sized (a11y)
'ábc' (a+◌́ b c)  4      28                19                        +9   ← combining mark over-counted
```

**Divergent behaviors if one changes.** The hand-rolled path is Unicode-*blind*:
it counts every code unit as 7 px. Consequences that the canonical path handles
and the seed does not: (1) CJK/full-width labels under-size the pill → text
overflow (the shipped a11y bug); (2) combining diacritics and ZWJ emoji
over-size; (3) it is invariant to `_TICK_FONT_SIZE` — bump the tick font and every
other measurement rescales except line labels. Any future change to the `0.62`
average, the CJK rule, or the tick font size updates point labels and leaves line
labels behind.

**Verdict:** TRUE duplicate, **already drifted**. Consolidate by replacing
`len(label_text) * _LINE_LABEL_CHAR_W` with
`estimate_text_width(label_text, _TICK_FONT_SIZE)` and deleting `_LINE_LABEL_CHAR_W`.
**This produces nonzero golden churn** (line-label pills resize; CJK pills grow) —
it is a value reconciliation, not a byte-identical move. See Landing Commit B.

---

## 3. Duplicate-cluster table

Paths under `scriba/animation/primitives/` unless noted. "Canonical" = the home
the design assigns. "Drifted?" = are the live copies numerically equal *today*.

### 3a. TRUE duplicates — consolidate

| Cluster (role) | Canonical home | Copies (path:line = value) | Values | Drifted? | Verdict / churn |
|---|---|---|---|---|---|
| **C1 · char advance width (proportional label font)** | `_text_render.estimate_text_width` (fn) | `plane2d.py:1020` `_LINE_LABEL_CHAR_W=7` → `:1058` `len*7` | 7 vs 6.2/10 | **YES — live (B-1)** | TRUE dup; call fn; **nonzero churn** |
| **C2 · text-background pill pad/radius** | `_svg_helpers.py:93-95` `_LABEL_PILL_PAD_X/Y/RADIUS=6/3/4` | `graph.py:88-90` `_WEIGHT_PILL_PAD_X/Y/R=5/2/3`; (`plane2d.py:1023-25` already aliased) | (5,2,3) vs (6,3,4) | **YES — live (B-2)** | TRUE dup (pending design sign-off, §4); **nonzero churn** |
| **C3 · primitive label/caption font** (CSS `--scriba-label-font:11px`) | new `LABEL_FONT_PX` (see §4) | `base.py:182` `_CAPTION_FONT_PX=11`; `array.py:55` `_FONT_SIZE_CAPTION=11`; `dptable.py:45` `_FONT_SIZE_CAPTION=11` | all 11 | no | TRUE dup; **zero churn** |
| **C4 · annotation/weight-pill font** (CSS `--scriba-annotation-font:11px`) | `_svg_helpers.py:111` `_DEFAULT_LABEL_FONT_PX=11` | `graph.py:87` `_WEIGHT_FONT=11`; `_svg_helpers.py:3014/3168/3239` `l_font_px:int=11` defaults; `_svg_helpers.py:1849-1873` `_ARROW_STYLES "11px"` | all 11 | no | TRUE dup; **zero churn**. **Keep separate from C3** (CSS keeps two vars) |
| **C5 · cell-index font** (CSS `--scriba-cell-index-font:10px`) | new `INDEX_FONT_PX` in `_types.py` | `array.py:54` `_FONT_SIZE_INDEX=10`; `dptable.py:44` `_FONT_SIZE_INDEX=10` | both 10 | no | TRUE dup; **zero churn** |
| **C6 · index-label vertical offset** | `_types.py:132` `INDEX_LABEL_OFFSET=16` | `linkedlist.py:48` `_INDEX_LABEL_OFFSET=16` | both 16 | no | TRUE dup; import it; **zero churn** |
| **C7 · math line strut extra (+5)** *(hidden twin)* | `_svg_helpers.py:1373` `_MATH_PILL_LINE_EXTRA=5` | `base.py:193` `_MATH_CAPTION_LINE_H=18` = `(_CAPTION_FONT_PX+2)+5` = `13+5` | 18 == 13+5 | no (linked) | TRUE dup of the "+5"; **derive** `_MATH_CAPTION_LINE_H`; **zero churn** |
| **C8 · math headroom extra (+8)** *(hidden twin, intra-file)* | new `_MATH_HEADROOM_EXTRA=8` | `_svg_helpers.py:2980,3061` `32 = _LABEL_HEADROOM(24)+8`; `:3226,3279` `8` | 32 == 24+8 | no (linked) | TRUE dup of the "+8"; **derive**; **zero churn** |
| **C9 · line-box height `font_px + 2`** *(formula)* | new helper `line_box_h(font_px)` in `_text_render` | `base.py:651,678`; `graph.py:1406`; `_layout_expand.py:133,292`; `_svg_helpers.py:1396` | `+2` everywhere | no | TRUE formula dup; extract helper; **zero churn** |
| **C10 · pill cell-gap `max(4.0, cell_height*0.1)`** *(formula, intra-file)* | new helper `_pill_cell_gap(cell_height)` | `_svg_helpers.py:3052,3146,3221,3479` verbatim ×4 | identical | no | TRUE formula dup; extract; **zero churn** |

### 3b. COINCIDENTAL — do NOT merge (merging = wrong coupling)

| Look-alike | Members | Why NOT a duplicate |
|---|---|---|
| **`_PADDING` name** | `_frame_renderer.py:27`=12, `linkedlist.py:47`=12, `graph.py:46`=20, `graph_layout_hierarchical.py:42`=20, `graph_layout_score.py:31`=20, `stack.py:37`=8, `hashmap.py:40`=4, `variablewatch.py:36`=4, `tree.py:48`=30, `tree_layout.py:26`=30 | Same *name*, 5 distinct values, each a per-surface internal margin. `linkedlist=12` equals `_frame_renderer=12` **coincidentally** (node inset vs viewBox frame margin). Merging would make a frame-margin change silently move linkedlist node padding. |
| **cell dimensions** | `_types.py:129-131` `CELL_WIDTH/HEIGHT/GAP=60/40/2` (canonical, imported by array/dptable/grid/queue — **no hardcoded 60/40 copies exist**) vs `stack.py:34-36` `_CELL_*=80/36/4` vs `matrix.py:105` `_CELL_GAP=1` | Different *values* = different visual surfaces. Stack cells and grid cells are genuinely different sizes. Distinct tokens. |
| **height `40`** | `_types.CELL_HEIGHT=40`, `hashmap.py:39` `_ROW_HEIGHT=40`, `variablewatch.py:35` `_ROW_HEIGHT=40`, `linkedlist.py:45` `_NODE_HEIGHT=40` | Table row / hash row / list node / grid cell are not constrained to move together. Coincidental `40`. |
| **font `10` axis family** | `plane2d.py:54` `_TICK_FONT_SIZE`, inline `10` in `matrix.py`, `numberline.py`, `metricplot.py` | Distinct from cell-index `10` (C5): different CSS surface, no shared `--scriba-*` var. A designer may densify number-line ticks without shrinking table index labels. |
| **node radius `20`** | `graph.py:44` `_NODE_RADIUS`, `tree.py:44` `_NODE_RADIUS` | Borderline. Geometry (no CSS arbiter). Graph and tree are independent primitives; keep separate unless product declares one "node" token. Do not merge speculatively. |
| **`18` vs `5`** (the tempting mis-merge) | `_MATH_CAPTION_LINE_H=18`, `_MATH_PILL_LINE_EXTRA=5` | The raw numbers are **not** equal and **not** one quantity — but they are *linked* (`18=13+5`). Correct move is *derive* (C7), **not** collapse to one constant. |

### 3c. Non-issues confirmed (report as clean)

- **Python↔JS timing (`DUR*`/ms):** none. `_script_builder.py` slices the inline
  runtime out of `static/scriba.js` between `__SCRIBA_CORE_START__/END__` sentinels
  precisely to avoid a Python echo of JS durations. `_html_stitcher.py:619`
  `data-scriba-speed="1"` is the only Python→JS numeric, and it is a default, not a
  duplicated constant. **This is the pattern the constant families should emulate:
  one authority, mechanically embedded — never hand-copied.**
- **`_PADDING=12`/`_PRIMITIVE_GAP=20`** are single-source in `_frame_renderer.py:27-28`;
  `emitter.py:68-73` is a stale empty comment, not a live redecl.
- **`CELL_WIDTH/HEIGHT=60/40`** already single-source in `_types.py`; consumers import.

---

## 4. Consolidation design + import rules

### 4a. The true-duplicate test I applied (so the design does not over-merge)

Two numeric definitions are the **same** quantity (must consolidate) iff **both**:

1. **Same design token / surface**, and
2. **Constrained to move together** — changing one *requires* changing the other
   for correctness or visual consistency; keeping them independent is a latent bug.

Grounded arbiter, in priority order:
- **Font & color:** the CSS custom property is the authority. **One `--scriba-*`
  var ⇒ one token.** Two vars at equal px (`--scriba-label-font:11` vs
  `--scriba-annotation-font:11`) ⇒ **two tokens that coincide** — keep two Python
  constants (this is why C3 and C4 stay separate despite both being 11).
- **SVG geometry (pad/radius/offset/cell):** the `_svg_helpers`/`_types` canonical
  is the authority; a copy that feeds the *same rendered element* is a true dup.
- **Value+name coincidence with no shared authority and no move-together
  constraint ⇒ coincidental — keep separate** (the entire §3b table).

### 4b. Module ownership (respects the existing acyclic layering)

Import DAG today (leaf → root): `_text_render`, `_types` → `_svg_helpers` →
`base` → shape primitives (`array`, `graph`, `plane2d`, …). `_frame_renderer`
imports none of the primitives' internals. Rules:

| Canonical | Owning module | Rationale (no cycle) |
|---|---|---|
| char-width model (C1) | `_text_render.py` (already there) | leaf; everyone may import |
| `line_box_h(font_px)` (C9) | `_text_render.py` | leaf; pure typography |
| `LABEL_FONT_PX` (C3), `ANNOTATION_FONT_PX` (C4), pill pad/radius (C2), `_MATH_PILL_LINE_EXTRA`/`_MATH_HEADROOM_EXTRA` (C7/C8), `_pill_cell_gap` (C10) | `_svg_helpers.py` | already imported by `base` + every shape primitive; already home to `_LABEL_PILL_*`, `_DEFAULT_LABEL_FONT_PX`, `_MATH_PILL_LINE_EXTRA` |
| `INDEX_FONT_PX` (C5), `INDEX_LABEL_OFFSET` (C6, exists) | `_types.py` | already home to `CELL_*`/`INDEX_LABEL_OFFSET`; leaf |

**Direction rules to encode:** primitives and `base` import font/pill/math
constants **from `_svg_helpers`**; cell/index geometry **from `_types`**;
width/line-box **from `_text_render`**. `_svg_helpers` may import `_types` and
`_text_render` (already does). Nothing imports *upward* into `base`/shape
primitives. Concretely: `base._CAPTION_FONT_PX` becomes
`from ..._svg_helpers import LABEL_FONT_PX as _CAPTION_FONT_PX` (keep the local
name so `base`'s body is untouched); `graph._WEIGHT_FONT` →
`ANNOTATION_FONT_PX`; `graph._WEIGHT_PILL_PAD_X/Y/R` → the `_LABEL_PILL_*` imports;
`array/dptable._FONT_SIZE_INDEX` → `INDEX_FONT_PX`; `linkedlist._INDEX_LABEL_OFFSET`
→ `_types.INDEX_LABEL_OFFSET`.

**C3/C4 naming split (do this or the parity guard is a lie):** today
`_svg_helpers._DEFAULT_LABEL_FONT_PX=11` is the *annotation* font. Introduce a
distinct `LABEL_FONT_PX=11` (primitive caption/label) so the two CSS vars map
1:1 to two Python constants. Do **not** fold captions and annotations into one
symbol just because both are 11 — that is the over-merge the CSS design explicitly
avoids.

### 4c. The C2 decision (needs a human call, stated honestly)

Reconciling `graph._WEIGHT_PILL_* 5/2/3 → 6/3/4` assumes edge-weight pills are the
*same* token as annotation pills. The plane2d precedent (`# was: 5/2/3 (FP-3 fix)`)
says the org already decided "yes" for line labels. Default recommendation:
**reconcile** (import `_LABEL_PILL_*`), regenerate weighted-graph goldens, verify
weight text still fits. If a designer says weight pills are *intentionally* tighter,
the alternative is to **keep `_WEIGHT_PILL_*` as a documented distinct token and pin
it apart** with a parity test asserting `!= _LABEL_PILL_*` (zero churn). Either way
the drift stops being silent.

---

## 5. Guard design — kill the regrowth

**Why the current FP-3 check is structurally insufficient** (`_check_fp3`,
`lint_smart_label.py:311`): it flags only `ast.Assign`/`AnnAssign` **inside primitive
class methods** whose target name is in the fixed `_FP3_SUSPICIOUS_NAMES` set, and
`lint_primitives` **excludes** `base.py`, `_svg_helpers.py`, `_text_render.py`,
`_types.py`, `layout.py`. So it is blind to: module-level constants (all of
`_WEIGHT_*`, `_FONT_SIZE_*`, `_CELL_*`), any new name, and every excluded file.
It caught the seed only by luck (method-local **and** blocklisted). A guard built on
name+location cannot catch B-2 and cannot catch the next twin.

**Two failure modes to guard, separately:**
- **DRIFT** (twins exist and diverge) — the *shipped-bug* vector (B-1, B-2).
- **BIRTH** (a new copy appears) — the *regrowth* vector.

**Recommendation: option (c), but weighted — a parity ratchet is primary, an
extended AST lint is secondary. Ship both; do not ship a bare value-grep.**

**(Primary) Constant-parity ratchet — catches DRIFT with zero false positives.**
Generalize the *existing* `tests/unit/test_css_font_sync.py` (which already asserts
`array._FONT_SIZE_CELL == css['cell']`, `… _INDEX == css['cell-index']`,
`… _CAPTION == css['label']`) into `test_layout_constant_sync.py` with a single
explicit registry:

```python
# each row: (python constant, authority)  — authority is a CSS var or a canonical symbol
LABEL_FONT_PX        == css['label']          # C3
ANNOTATION_FONT_PX   == css['annotation']     # C4  (proves the split is real)
INDEX_FONT_PX        == css['cell-index']     # C5
graph._WEIGHT_PILL_PAD_X/Y/R == _svg._LABEL_PILL_PAD_X/Y/RADIUS   # C2  ← RED today
_MATH_CAPTION_LINE_H == line_box_h(LABEL_FONT_PX) + _MATH_PILL_LINE_EXTRA  # C7
```

It only checks constants that *opt in* by being registered, so it never fires on the
coincidental `4/8/12/20/30` paddings. It fails the instant two registered twins
diverge. Crucially it closes the current gap where the *rendered* constant
(`base._CAPTION_FONT_PX`) is **unguarded** vs CSS while two non-rendering mirrors
are guarded.

**(Secondary) Extend `lint_smart_label.py::_check_fp3` — catches BIRTH.**
Two surgical changes: (1) also scan **module-level** assignments, not just
method bodies; (2) replace/augment the name-blocklist with a **canonical-value
registry** — flag any *new* module-level or method constant whose value equals a
registered canonical role (e.g. `= 11` for a font, `= 6/3/4` for pill pad) **and**
is not an `import`/alias of the canonical. Keep it in the existing advisory ratchet
(`tests/doc_coverage/test_smart_label_lint.py`, `_CEILING`).

**Why not option (a) alone (grep `= <number>`):** a bare value-grep floods on
coincidental numbers (every `4/8/12/20`), gets muted, and cannot tell a font `11`
from a padding `11`. Its intent is fully subsumed by the AST value-registry above,
which has role/location context. Fold (a) into (b); do not ship it standalone.

---

## 6. TDD plan

**RED first — write the guards, watch the two real bugs fail.**

1. `test_layout_constant_sync.py::test_weight_pill_matches_label_pill` — asserts
   `graph._WEIGHT_PILL_PAD_X/Y/R == _svg_helpers._LABEL_PILL_PAD_X/Y/RADIUS`.
   **RED today** (5,2,3 ≠ 6,3,4) — reproduces B-2.
2. `tests/unit/test_plane2d_line_label_width.py::test_uses_canonical_estimator` —
   render a plane2d line label with a CJK string (e.g. `斜率`) and assert the emitted
   pill width ≥ `estimate_text_width("斜率", 10) + pad`. **RED today** (hand-rolled
   `len*7` under-sizes) — reproduces B-1. (A source-level assert that
   `_LINE_LABEL_CHAR_W` no longer exists is a weaker backstop.)
3. Register the already-equal twins (C3–C8) as parity assertions. **GREEN today** —
   these are *lock-ins* that prevent future drift; they turn each latent twin into a
   fail-closed invariant.

**GREEN — consolidate, grouped by risk (see §7).** Each consolidation makes its
registry rows import-identical; the parity rows stay green by construction.

**Coverage / acceptance bar.** Byte-identical golden output is the acceptance test.
Regeneration is `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/examples/ -v`
(105 `.tex→.html` pairs, compared byte-for-byte; `tests/golden/examples/test_example_html.py`).
- **Equal-value consolidation ⇒ predicted golden churn = ZERO.** Acceptance:
  `pytest tests/golden/examples/` passes **without** `SCRIBA_UPDATE_GOLDEN`. Any
  nonzero diff means a supposedly-equal twin was actually drifted — stop and grade it.
- **Value reconciliation (B-1, B-2) ⇒ nonzero churn, expected and enumerated below.**

---

## 7. Landing order

**Commit A — zero-churn consolidations (behavior-identical moves).** C3, C4, C5,
C6, C7, C8, C9, C10. Introduce `LABEL_FONT_PX`/`ANNOTATION_FONT_PX` in
`_svg_helpers`, `INDEX_FONT_PX` in `_types`; redirect `base`/`graph`/`array`/
`dptable`/`linkedlist` and the `_svg_helpers` internal defaults to them; derive
`_MATH_CAPTION_LINE_H` and the `32`/`8` math extras; extract `line_box_h` and
`_pill_cell_gap` helpers; delete `base.py:182`'s "must match array._FONT_SIZE_CAPTION"
comment (now enforced by test). **Predicted golden churn: ZERO** — gate on
`pytest tests/golden/examples/` green with no update flag. Flips the C3–C8 parity
rows to enforced-green.

**Commit B — seed reconciliation (B-1, nonzero churn).** Replace
`len(label_text) * _LINE_LABEL_CHAR_W` with
`estimate_text_width(label_text, _TICK_FONT_SIZE)` at `plane2d.py:1058`; delete
`_LINE_LABEL_CHAR_W` (`plane2d.py:1020`). Flips RED test #2 green. **Regenerate
goldens** for the plane2d line-label examples — predicted set:
`plane2d_lines`, `test_plane2d_edges`, `test_reference_datastruct`,
`test_reference_grid_numline`, `gep_v2_smoke`. **A11y check:** confirm the CJK
line-label pill now contains its text. **Then lower the FP-3 ceiling 11 → 10**
(`tests/doc_coverage/test_smart_label_lint.py::_CEILING`) — the sole FP-3 (E1570-C)
violation is now gone (the other 10 are FP-2/5/6, out of scope).

**Commit C — graph pill reconciliation (B-2, nonzero churn, design sign-off).**
Point `graph._WEIGHT_PILL_PAD_X/Y/R` at `_svg_helpers._LABEL_PILL_*`. Flips RED
test #1 green. **Regenerate goldens** for weighted-graph examples — predicted set:
`dijkstra`, `dijkstra_editorial`, `mcmf`, `kruskal_mst`, `elevator_rides`,
`diagram_intro`, `test_reference_graph_tree`, `test_label_readability`,
`gep_v2_smoke`, `test_reference_grid_numline` (~10 frames). **A11y check:** weight
text still fits the (now larger-pad) pill. If design rules weight pills a distinct
token, swap this commit for the "pin-apart" variant (§4c) — zero churn, still closes
the drift.

**Commit D — guard hardening.** Land the extended AST birth-check (§5 secondary) in
the advisory ratchet. Order: A (zero-risk, unblocks the green locks) → B → C
(each reconciliation flips exactly one RED guard and regenerates only its own
goldens) → D (prevents the next twin).

---

### Appendix — reproducing the key probes

```
# seed drift + CJK under-size
.venv/bin/python -c "from scriba.animation.primitives._text_render import estimate_text_width as e; \
print('Latin', len('y=2x+1')*7, e('y=2x+1',10)); print('CJK', len('斜率')*7, e('斜率',10))"
# -> Latin 42 37   |   CJK 14 20   (hand-rolled 7 over-sizes Latin, UNDER-sizes CJK)

# B-2 live pill drift
.venv/bin/python -c "import scriba.animation.primitives.graph as g, scriba.animation.primitives._svg_helpers as h; \
print((g._WEIGHT_PILL_PAD_X,g._WEIGHT_PILL_PAD_Y,g._WEIGHT_PILL_R),'vs',(h._LABEL_PILL_PAD_X,h._LABEL_PILL_PAD_Y,h._LABEL_PILL_RADIUS))"
# -> (5, 2, 3) vs (6, 3, 4)

# C7 hidden twin
.venv/bin/python -c "import scriba.animation.primitives.base as b, scriba.animation.primitives._svg_helpers as h; \
print(b._MATH_CAPTION_LINE_H, '==', (b._CAPTION_FONT_PX+2)+h._MATH_PILL_LINE_EXTRA)"
# -> 18 == 18

# linter blind-spot proof: only the seed is visible
python3 scripts/lint_smart_label.py --strict | grep E1570-C
# -> plane2d.py:1020 ... '_LINE_LABEL_CHAR_W = 7' ... (FP-3)   [the only one, of a family of ~8]
```
