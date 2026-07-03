# Unified Decoration Model — one substrate under `\trace`, `block[…]`+bracket, and `color=state:X`+leader

> Design synthesis. **No repo source modified.** Repo @ `main` (scriba 0.22.1, `SCRIBA_VERSION = 14`,
> `scriba/_version.py`). Supersedes nothing; unifies the three prior investigations
> (`feat-trace-primitive.md`, `feat-label-state-colors.md`, `feat-grid-block-selector.md`) into one
> framework so the three features are special cases, not three patches.
>
> Evidence grades: **[Confirmed]** = read in source or run this session (probes
> `scratchpad/um_probe.py`, `um_probe2.py`) · **[Deduced]** = logical consequence of confirmed facts ·
> **[Hypothesized]** = design proposal, not yet built.

---

## 1. Hand-off Brief (3 sentences)

Scriba **already has** a unified decoration substrate — it is simply unnamed and dispatched implicitly:
one list (`SceneState.annotations` → `prim.set_annotations` → `self._annotations`), one renderer
(`emit_annotation_arrows`, already a dispatch over `arrow_from`/`arrow`/position-only), one
reservation/obstacle pipeline (`_measure_emit` *replays* that renderer, so measured == painted by
construction, R-30/R-31/R-32), one color channel (CSS `scriba-annotation-{color}` with Python
`ARROW_STYLES` as fallback only), one animation channel (`<g data-annotation>` + structure-driven
draw-on), and one geometry-resolver family (`resolve_annotation_point` = Point, `resolve_annotation_box`
= Rect). The unified model **names** this substrate and adds exactly three things — an explicit `glyph`
discriminator on the record, a third geometry kind `resolve_annotation_path` = Path (the only genuinely
new resolver, for `\trace`), and a two-band z-order — so that `\trace`, `block[…]`+`bracket=true`,
`color=state:X`, and `leader=true`, plus future glyphs (underline, badge, shape-to-shape connector) all
land as **data**, not new pipelines; the alternative the three separate investigations imply — a parallel
`_traces`/`set_traces`/`emit_traces` stack (feat-trace §9), a `bracket:bool` threaded 5 layers (feat-3
§3.4), a `leader:bool` threaded 5 layers (feat-2 §6) — duplicates plumbing and, worse, the parallel trace
list is **invisible to `_measure_emit`** and would silently violate R-32.4. The framework is strictly
additive (goldens change only for files that opt into a new glyph; `SCRIBA_VERSION` unchanged), and this
session **executed** the three load-bearing facts it turns on: unknown `\annotate` params are silently
accepted today (additive surface), `color=state:current` does **not** parse today (the bare colon dies at
the tokenizer with **E1012**, not at the enum check the feat-2 plan assumed), and two order-free
decorations on one target **collide** in the differ key `('g','solo')`.

---

## 2. The decoration substrate that already exists (Confirmed path:line)

Every decoration today travels the **same seven-stage spine**. This is the finding the whole model rests on.

| # | Stage | Code (Confirmed) | What it is in "decoration" terms |
|---|---|---|---|
| 1 | **AST** | `AnnotateCommand` `parser/ast.py:213-226` | the authored request |
| 2 | **Scene entry** | `AnnotationEntry(target,text,ephemeral,arrow_from,color,position,arrow)` `scene.py:110-121`; appended in `_apply_annotate` `scene.py:806-846`; ephemeral cleared each `\step` `scene.py:207-208` | the persistent record |
| 3 | **Snapshot → FrameData dict** | ann-dict comprehension `renderer.py:309-320` | the wire form (a plain `dict`) |
| 4 | **Hand to primitive** | `set_annotations(self._annotations=…; invalidate extent cache)` `base.py:363-370`; 3 call sites `_frame_renderer.py:136-142,270-276`, `_html_stitcher.py:158-168` | the per-primitive list |
| 5 | **Render dispatch** | `emit_annotation_arrows` `base.py:835-1036` — branches: `arrow_from`→`emit_arrow_svg`; `arrow=true`→`emit_plain_arrow_svg`; else position-only→`emit_position_label_svg` (which itself branches `is_range`→span-bracket `_svg_helpers.py:3697-3728`) | the glyph dispatch |
| 6 | **Reservation / obstacles** | `_measure_emit` *calls the same* `emit_annotation_arrows` `base.py:453-466`; extent → 4-way lane reservation `base.py:396-441`; strokes → R-31 obstacles `base.py:909-936` | the "citizen" pipeline |
| 7 | **Diff → animation** | `_diff_annotations` keys `(target, arrow_from|"solo")` → `annotation_add/remove/recolor` `differ.py:241-301`; JS draw-on is structure-driven on `[data-annotation]`+`<path>`+`getTotalLength`/`strokeDashoffset` `static/scriba.js:205-259` | the runtime channel |

**The load-bearing consequence [Deduced]:** stage 6 measures by *replaying stage 5*. Therefore any glyph
added **inside** `emit_annotation_arrows` is automatically reserved, obstacle-aware, and R-32-stable —
and any glyph emitted **outside** it (a parallel `emit_traces`, as feat-trace §9 proposes) is invisible to
reservation and **breaks R-32.4** (`bounding_box` must be a pure function of `_annotations`,
`ruleset.md:934-938`). This single fact is why unification is *more correct*, not just less code.

Geometry today has **two** kinds, both resolved by the primitive from the target string:

- **Point** — `resolve_annotation_point(selector)` `base.py:529-536` (Grid returns cell center
  `grid.py:197-211`), plus the center-corrected `resolve_label_anchor` `base.py:538-549`.
- **Rect** — `resolve_annotation_box(selector)` `base.py:551-561` (used as the R-02 blocker and the 1D
  span-bracket span width, gated by `_target_has_below_pill` `base.py:563-579`).

There is **no Path kind**. That is the one real geometry gap (`\trace`).

---

## 3. The D-rules (D-1 … D-8)

R-card-style. Each is a MUST for any decoration, existing or future. Rationale ties to confirmed code.

### D-1 — One list, one emitter (no parallel decoration pipelines)
Every decoration — arc arrow, plain arrow, position pill, 1D span bracket, 2D block bracket, trace,
leader, and future glyphs — is an entry in the single `AnnotationEntry` list and is rendered by the single
`emit_annotation_arrows` dispatch. **No** sibling `_traces`/`_brackets` list or `emit_traces`/`emit_*`
function.
*Rationale:* `_measure_emit` (`base.py:453-466`) only replays `emit_annotation_arrows`; a parallel list is
invisible to reservation → drift → R-32.4 violation. Generalizes **R-30** ("NumberLine MUST route through
the one dispatcher", `smart-label-ruleset.md:959-983`) from one primitive to every glyph. [Confirmed spine]

### D-2 — Glyph is an explicit discriminator
Each entry carries `glyph ∈ {arrow, pill, bracket, trace, leader-modifier, …}`. Dispatch branches on it.
The three legacy *implicit* signals map onto it losslessly: `arrow_from` set → `glyph=arrow` (arc);
`arrow=true` → `glyph=arrow` (plain); neither, with a label → `glyph=pill`; `is_range`+pill →
`glyph=bracket` (1D).
*Rationale:* implicit dispatch (`base.py:917-1000`) cannot disambiguate two glyphs on one target, nor
scale past six. Making it explicit is the seam every new glyph plugs into. [Deduced from `base.py:917-1000`]

### D-3 — Geometry is resolved from the target, in exactly three kinds
A decoration's anchor is `Point | Rect | Path`, produced by `resolve_annotation_point`,
`resolve_annotation_box`, and a **new** `resolve_annotation_path` (ordered cell centers). Selectors/params
name *regions/paths*; the **primitive** owns pixels. No glyph computes cell coordinates itself.
*Rationale:* content-based sizing (`self._cell_width`, `grid.py:161-177`) and Matrix header offsets
(`matrix.py:305-306`) live in one place per primitive; both block-box (feat-3 `_cell_rect`) and trace-path
build on the same `_cell_rect(r,c)` hook. [Confirmed resolvers `base.py:529-561`; Path is Hypothesized]

### D-4 — Every decoration is a placement citizen
A decoration's painted SVG flows through `_measure_emit` so its extent reserves layout (R-32) and its
strokes register as obstacles (R-31) for later pills; anchored glyphs (bracket, trace) register as
*obstacles*, not pill *candidates* (they have fixed geometry, they don't compete for lanes).
*Rationale:* the only construction under which measured == painted (`base.py:372-394`, R-32.3/.4). This is
what a side-channel emitter forfeits. [Confirmed `base.py:453-466`, `909-936`]

### D-5 — Color is a token reference; Python is fallback only
`color` is a token ref: an annotation-palette name (`info|warn|good|error|muted|path`,
`constants.py:35-37`) **or** a `state:X` reference. Emit sets CSS class `scriba-annotation-{color}` /
`scriba-annotation-state-{X}`; children (`text|path|line|circle|polygon|rect`) inherit
`--scriba-annotation-*` / `--scriba-state-*`. `ARROW_STYLES` (`_svg_helpers.py:1916-1965`) fills **only**
the no-CSS raw-SVG path.
*Rationale:* CSS token wins over the SVG presentation attribute (`_svg_helpers.py:552-554`), so `state:X`
dark-adapts for free off existing `--scriba-state-*` dark variants (`static/scriba-scene-primitives.css:122-154`).
[Confirmed tokens; feat-2 §2]

### D-6 — One key drives structure *and* animation; it must be unique and co-derived
A decoration emits `<g class="scriba-annotation…" data-annotation="{key}" role="graphics-symbol"
aria-roledescription="annotation" aria-label="{speech}">` wrapping its glyph. The **differ** transition
key and the **emit** `data-annotation` key MUST both derive from the same `(target, glyph, arrow_from)`
tuple, so the JS `annotation_add` handler resolves the DOM node it animates. New glyphs get a glyph
segment; legacy keys (`{target}-{arrow_from|solo}` arc, `{target}-plain-arrow`, `{target}-position-{pos}`)
stay byte-identical (glyph segment elided for back-compat).
*Rationale:* emit already namespaces per glyph (`_svg_helpers.py:2847`, `:2068`, `:3654`) but the differ
keys on `(target, arrow_from|solo)` only (`differ.py:243,263`) — so today the two sides align **only** for
arc arrows, and two order-free glyphs on one target collide on `('g','solo')` (**Confirmed by execution**,
`um_probe.py` P2). Any path-bearing new glyph needs both sides to agree, or draw-on silently no-ops.
[Confirmed]

### D-7 — Z-order is a two-band property
Each decoration declares a band: `under` (behind primitive content — `trace` threads behind digits) or
`over` (in front — arrows, pills, brackets, leaders). `emit_svg` invokes the dispatch twice: `under`
before the cell loop, `over` after. **Both** bands feed `_measure_emit` (else the under-band escapes
reservation).
*Rationale:* a single emit call sits at one z-index; every cell primitive's skeleton is
`open group → [under here] → cell loop → caption → [over here] emit_annotation_arrows` (`grid.py:277-359`).
[Confirmed skeleton; two-band is Hypothesized]

### D-8 — Additive, zero-churn
A new glyph adds: one `glyph` enum value, one resolver branch, one emit branch, CSS rules. It never mutates
emit for *existing* inputs. Goldens change only for files that use the new glyph; `SCRIBA_VERSION`
(currently 14) stays put unless an existing decoration's bytes move.
*Rationale:* the 105-file byte-golden corpus must not re-bless for opt-in features. The single shared churn
risk (trace number-halo) is gated on under-band presence so non-trace output is byte-identical (feat-trace
§9 Q5). [Confirmed additive surface by execution, `um_probe.py` P1]

---

## 4. Region algebra — verdict

**Framing (from the brief):** selectors carry two semantics — **RegionSet** (order-free: recolor /
highlight / annotate-anchor) and **CellPath** (ordered: trace). `block` = RegionSet-2D, `range` =
RegionSet-1D, `cells=[[…]]` = CellPath.

**Verdict: keep stringly-keyed selectors + extend the expand machinery; do NOT introduce a `Region` IR
node.** And the sharper realization that dissolves the tension:

> **CellPath is not a selector at all — it is a decoration *parameter*.** `range`/`block`/`all` are
> *targets* (they live in the first brace, become `shape_states` keys, expand to cells). An ordered trace
> path `cells=[[r,c],…]` lives in the *second* brace as a param and is only meaningful to one glyph. So the
> two "region semantics" are not two selector types — they are **RegionSet = the selector** and **CellPath
> = the geometry payload of `glyph=trace`**, both feeding the *same* three-kind resolver family (D-3):
> RegionSet→Rect (`resolve_annotation_box`) or →cells (recolor expand); CellPath→Path
> (`resolve_annotation_path`).

**Why not a Region IR node (the honest "weigh really"):**

| | Stringly + extend (RECOMMENDED) | Region IR node (overhaul) |
|---|---|---|
| Scene state keying | unchanged — `shape_states[shape][selector_str]` `scene.py:743-751` | must re-key on a Region object; touches every read |
| `_selector_to_str` | +1 branch (`BlockAccessor`) `scene.py:86-92` | replaced by a node type |
| `_expand_selectors` | +1 regex branch (`block_re` → 2D cell product) `_frame_renderer.py:352-386` | replaced by node dispatch |
| `resolve_*` (per primitive) | +1 suffix regex (`BLOCK_RE`) mirroring `RANGE_RE` `_types.py:192-205` | rewrite to consume nodes |
| Differ / interpolation | unchanged (`fields(acc)` generic resolve already handles new accessors, feat-3 §8 Q1) | must re-plumb |
| Byte-golden risk | **zero** (additive) | high (key-format churn) |
| Net | ~4 branches, ~40 lines, localized | touches 6 layers, byte-risky |

The one honest wart: `_expand_selectors` is regex-on-string and grows one branch per RegionSet type
(`range`, `all`, `top`, `block`). A Region node would centralize that. But the wart is small and local; the
overhaul cost is large and churny. **Recommend: land `block` additively now; file the
`_expand_selectors`→Region-IR centralization as an independent, non-blocking hygiene task** (it is not
needed by any of the three features). Migration path is therefore: `BlockAccessor` (mirror `RangeAccessor`,
`ast.py:67-72`) + one `_selector_to_str` branch + one `_expand_selectors` branch + one `_types.py` regex —
exactly feat-3 §3.1-3.3, zero existing-selector change.

---

## 5. The unified Decoration record + mapping table

```
Decoration (unified — a superset of today's AnnotationEntry):
  target      : SelectorKey     # "g.cell[0][1]" | "g.block[0:1][0:1]" | "g"   (RegionSet / Point / Rect)
  glyph       : arrow | pill | bracket | trace | (future: underline | badge | connector)
  anchor      : resolve_annotation_point|_box|_path(target|geometry)  →  Point | Rect | Path   (D-3)
  label?      : LaTeX pill text
  color       : TOKEN-REF       # "info".."path" | "state:current"                              (D-5)
  position    : above|below|left|right|inside          # pill placement hint
  leader      : bool            # modifier: force a connector pill→anchor (feat-2)              (D-6/over)
  ephemeral   : bool            # persistence: cleared each \step (scene.py:207-208)
  z           : under | over    # trace=under; arrow/pill/bracket/leader=over                   (D-7)
  geometry?   : tuple           # glyph=trace only: ordered cells=/path= payload → Path
  arrow_from? : SelectorKey     # glyph=arrow (arc) only
```
Today's `AnnotationEntry` (`scene.py:110-121`) is the **shaded subset**: `target, text, ephemeral,
arrow_from, color, position, arrow`. The model adds `glyph` (explicit), `leader`, `z`, `geometry`.

### 5.1 Mapping — the three features are rows in one table

| Request arg (per feature) | Decoration field | Resolver / glyph | Shared plumbing it rides |
|---|---|---|---|
| **trace** `\trace{g}{cells=[[r,c],…]}` | `glyph=trace`, `geometry=cells`, `z=under` | `resolve_annotation_path` → **Path** (new, D-3) | D-1 list, D-4 measure, D-6 key `g-trace-solo`, D-7 under-band |
| **trace** `color=good`, `label=`, `arrowhead=` | `color`, `label`, glyph-local `arrowhead` | Path + inline `<polygon>` (reuse `_svg_helpers.py:2809-2835`) | D-5 color token, pill via `emit_position_label_svg` |
| **block** `\recolor{g.block[…]}{state=done}` | `target=g.block[…]` (RegionSet-2D) | `_expand_selectors` block branch → 2D cell product | existing recolor (`scene.py:743-751`), **no glyph** |
| **block** `\annotate{g.block[…]}{bracket=true}` | `target=g.block[…]`, `glyph=bracket`, `z=over` | `resolve_annotation_box(block)` → **Rect** + `_cell_rect` | D-1 list, D-4 measure, D-6 key `g.block…-bracket-solo` |
| **state-color** `color=state:current` | `color="state:current"` | class `scriba-annotation-state-current` → `--scriba-state-current-fill` | D-5 (needs value-lexer fix §6) |
| **leader** `leader=true` | `leader=true` modifier on any labelled glyph | `_line_rect_intersection` pill→anchor (`_svg_helpers.py:1099-1185`) | D-6 (over-band), existing pill path |

### 5.2 What the three separate designs duplicate — and the saving

Each investigation independently threads a *new field through the same 5-layer stack*
(`AST → AnnotationEntry → ann-dict → set_* → emit`):

- feat-3 threads `bracket:bool` through **5 sites** (feat-3 §3.4 table).
- feat-2 threads `leader:bool` through **5 sites** (feat-2 §6 B, steps 5-10).
- feat-trace threads a **whole parallel stack**: `TraceEntry`, `SceneState.traces`, `FrameData.traces`,
  `set_traces`, `emit_traces`, `_diff_traces` — **~13 files** (feat-trace §9), *and* that stack is
  invisible to `_measure_emit` (D-4 violation).

**Unified: thread the generalization *once*.** Add `glyph` (1 field, 5 sites), `leader` (1 modifier, 5
sites), `geometry` (1 field, 5 sites, `None` for non-trace). Three fields plumbed once each ≈ **15 edits**
that serve *all present and future glyphs*, versus feat's `bracket`(5) + `leader`(5) + trace-stack(13) ≈
**23 edits** that serve exactly three features **and** carry a latent R-32 bug. Four concrete conflicts the
separate designs create, that unification removes:

1. **Trace's parallel list vs the annotation list** — `emit_traces` is not replayed by `_measure_emit`
   (which calls only `emit_annotation_arrows`, `base.py:462`), so a trace bowing outside the grid would not
   reserve headroom → **R-32.4 violation**. Unified routes trace through the one emitter → compliant. [Deduced]
2. **Differ-key collision** — trace-on-`g` and bracket-on-`g` both key `('g','solo')` (**Confirmed**,
   `um_probe.py` P2). feat-trace dodged it by namespacing `target="trace:{id}"`; feat-3 did not consider it.
   D-6 makes the key `(target, glyph, arrow_from)` for all. [Confirmed]
3. **`color=state:X` lexer gap** — feat-2 §3(ii) budgeted only "branch on `color.startswith('state:')` at
   `_grammar_commands.py:234`", but the bare colon **dies at the tokenizer with E1012 before that branch is
   reached** (**Confirmed**, `um_probe2.py`: bare `state:current`→E1012, `state.current`→E1012,
   quoted→E1113). One shared value-reader fix (§6) serves `\annotate`, `\reannotate`, and `\trace` color.
   [Confirmed]
4. **`resolve_*` fragmentation** — feat-3 adds `resolve_annotation_box(block)` + `_cell_rect`; feat-trace
   adds `resolve_trace_point`. Same family. Unified names three resolvers and both new ones build on the one
   `_cell_rect(r,c)` primitive hook (feat-3 §3.3). [Deduced]

---

## 6. Grammar decision + EBNF

**Question:** is `\trace` a new command or `\annotate` extended (`glyph=trace`, `target=path`)?

**Executed facts that constrain the answer:**
- Unknown `\annotate` params are **silently accepted** today (`bracket=true`, `leader=true`, `foo=bar`,
  `cells=[[…]]`, `path=[[…]], glyph=trace` all parse to an `AnnotateCommand`) — **Confirmed**,
  `um_probe.py` P1 / `um_probe2.py`. The parser only enum-validates the keys it explicitly reads
  (`position`, `color`, `_grammar_commands.py:223-242`). So the additive surface is real.
- `color=state:current` (bare) → **E1012 "expected IDENT, got COLON"** at the value tokenizer;
  `color="state:current"` (quoted) → parses, then **E1113** at enum validation; `color=state.current` →
  **E1012**. **Confirmed**, `um_probe2.py`. The value reader accepts only a bare `IDENT` in enum position.

**Recommendation — thin, specific verbs over one overloaded verb; single substrate underneath.**

- **Keep `\annotate`** as the verb for *target-anchored* decorations (Point/Rect): `bracket=true`
  (feat-3), `leader=true` (feat-2), `color=state:X` (feat-2) ride here — they are all "annotate this
  target". Mirror `color=state:X` into `\reannotate` for parity (feat-2 note).
- **Add `\trace`** as a thin new verb for the *CellPath* glyph, because its anchor is an ordered `cells=`
  path, not a target — semantically distinct, and JudgeZone authors want the verb. **But `\trace` is pure
  sugar**: its parser emits the *same* `AnnotateCommand`/`AnnotationEntry` with `glyph=trace` +
  `geometry=cells`, and rides the shared scene/render/emit/diff spine (D-1). Grammar surface grows by one
  dispatch line (`grammar.py:299-303`) + one valid-command entry (`grammar.py:353-362`) — not a pipeline.
  *Rejected:* `\annotate{g}{glyph=trace,cells=…}` — reads as "annotate what?" and overloads one verb with
  six glyphs of params; the ergonomic cost outweighs the one saved dispatch line.
- **`color=state:X` token:** teach the enum-value reader to accept a `namespace ":" name` bare token in
  color position (minimal, keeps unquoted author ergonomics), *then* branch on the `state:` prefix and
  validate the suffix ∈ `VALID_STATES`. This is the shared fix conflict #3 demands. (Fallback if the lexer
  change is unwanted: require `color="state:current"` quoted + the enum branch — uglier, no lexer touch.)

**Mini-EBNF (additions in bold):**

```ebnf
decoration_cmd ::= annotate_cmd | trace_cmd | recolor_cmd
annotate_cmd   ::= "\annotate" "{" selector "}" "{" param_list "}"
trace_cmd      ::= "\trace"    "{" shape_ref "}" "{" param_list "}"        (* sugar → glyph=trace *)

selector       ::= IDENT ( "." accessor )?
accessor       ::= cell | tick | item | node | edge | range | **block** | "all" | NAMED
range          ::= "range" "[" index ":" index "]"
**block**          ::= "block" "[" index ":" index "]" "[" index ":" index "]"   (* RegionSet-2D, inclusive *)

param_list     ::= param ( "," param )*
param          ::= key "=" value
value          ::= INT | FLOAT | STRING | bool | list | **color_value** | index_tuples
**color_value**    ::= annotation_color | **state_ref**
**state_ref**      ::= "state" ":" state_name                (* NEW value token: reader accepts ns ":" name *)
index_tuples   ::= "[" ( "[" index ("," index)* "]" ("," "[" index ("," index)* "]")* )? "]"   (* cells=/path= *)
deco_flags     ::= "bracket" "=" bool | "leader" "=" bool | "arrow" "=" bool | "arrowhead" "=" ("end"|"start"|"both"|"none")
```

---

## 7. Conflict check vs the R-cards (35 rules: R-01…R-34 + R-27b/c + R-31ext in
`smart-label-ruleset.md`; R-32 in `ruleset.md`)

No hard contradictions. The model **reinforces** three rules and takes on **two** documented obligations.

| D-rule | Touches | Verdict |
|---|---|---|
| **D-1** one emitter | **R-30** (`smart-label-ruleset.md:959-983`) | **Reinforces** — R-30 says NumberLine MUST route through the one dispatcher; D-1 says *every glyph* must. Same principle, wider scope. |
| **D-4** citizen/measure | **R-32.3/.4** (`ruleset.md:926-938`), **R-31/ext** (`:986-1008`) | **Reinforces / resolves** — D-4 is the mechanism R-32 relies on. feat-trace's parallel `emit_traces` would **violate** R-32.4; unified is compliant by construction. New glyph strokes register as R-31 SHOULD obstacles. |
| **D-4** anchored glyphs | **R-05** semantic ordering (`:614-637`), **R-02** target-box blocker (`:266-291`), **R-33** content obstacles (`:416-435`) | **Compatible** — brackets/traces register as *obstacles*, not pill *candidates*; they don't enter the R-05 placement ordering. Clarify in the R-card. |
| **D-5** color token | **R-12** opacity floor (`:110`), **R-25** dark collision (`:187`), **R-13/R-23/R-29** dash differentiators (`:136/:163/:212`) | **Obligation A** — each new `--scriba-annotation-state-*` needs a contrast proof (≥4.5:1 light + dark pill) and must not reintroduce a dark collision. State tokens already carry dark variants (free). feat-2 §6 budgets `test_contrast.py`. |
| **D-6** key + `<g>` | **R-14** roledescription (`:761`), **R-11** speech aria-label (`:735`), **R-15** `<title>` (`:785`) | **Compatible** — new glyph `<g>`s must emit the same `role`/`aria-roledescription="annotation"`/`aria-label` (already the house pattern, `_svg_helpers.py:2852-2855`). Additive. |
| **leader=true** | **R-27/b/c** leader gates (`:515/:546/:571`), **R-08** endpoint at pill perimeter (`:491`) | **Obligation B** — `leader=true` *forces* a leader, bypassing the R-27c auto visual-gap gate. This is deliberate authorial override, not a contradiction (R-27* govern *automatic* leaders). Document as an explicit exception; keep R-08 perimeter geometry. |
| **D-7** two-band z | **R-32** (`ruleset.md:903-959`) | **Compatible** — the under-band trace measures inside the grid body (≈0 above-lane, feat-trace §7), so headroom is unaffected; both bands MUST feed `_measure_emit`. |
| **D-2/D-3/D-8** | — | No R-card contradiction (internal structure / additivity). |

**SCRIBA_VERSION / golden:** additive by D-8 → `SCRIBA_VERSION` stays **14** (`_version.py`). The only
shared churn risk is the trace number-halo (feat-trace §9 Q5); gate it on `if under-band present` so the
105-file corpus stays byte-identical. Block/bracket/state-color/leader are all opt-in → 0 existing-golden
change (feat-3 §7.4, feat-2 §6).

---

## 8. Phased plan — value-first, risk-last, each phase independently shippable

Refines the brief's proposed order (which landed trace 2nd): land the **Path resolver + under-band +
halo** — the only genuinely novel machinery — **last**, on a substrate proven by three prior glyphs.

**Phase 0 — Region: `block` selector + `\recolor` expansion** *(RegionSet half of §4; no glyph yet)*
`BlockAccessor` (`ast.py`, mirror `RangeAccessor`) + `_selector_to_str` branch (`scene.py:86`) +
`_expand_selectors` block→2D-cell-product branch (`_frame_renderer.py:378`) + `_cell_rect(r,c)` base hook +
`resolve_annotation_box(block)`. Ships 2D region recolor (independently useful). **0 golden churn.**
Validates D-3's Rect resolver and the shared `_cell_rect`. (feat-3 §3.1-3.3, §6)

**Phase 1 — D-core plumbing + block-bracket glyph** *(lowest-risk glyph; proves the framework)*
Introduce `glyph` (default-mapped so existing arrow/pill/span-bracket bytes are unchanged, D-2/D-8),
two-band emit (block-bracket is `over`; `under` is a measured no-op stub, D-7), diff-key extension
(`(target, glyph, arrow_from)`; legacy keys elide the glyph segment → byte-identical, D-6). Ship
`bracket=true` → `emit_block_bracket_svg` (feat-3 §3.4-3.5). **0 golden churn.** Validates
D-1/D-2/D-4/D-6/D-8 without needing Path, under-band, or the lexer fix.

**Phase 2 — Color/modifier layer: `color=state:X` + `leader=true`** *(orthogonal to geometry)*
Value-lexer `state:` extension (fixes conflict #3 / P1b) + `scriba-annotation-state-*` CSS referencing
`--scriba-state-*` (dark-free) + the `state:` enum branch in `\annotate`/`\reannotate` (D-5); `leader=true`
forced connector on the over-band (feat-2 §4, R-27 exception). Adds `test_contrast.py` (Obligation A).
**0 golden churn.** (feat-2 A+B)

**Phase 3 — `trace` glyph** *(highest-risk machinery, now de-risked)*
`resolve_annotation_path` (the new Path kind, D-3), the first real `under`-band user (D-7), the `\trace`
thin verb (§6), inline `<polygon>` arrowhead (reuse `_svg_helpers.py:2809-2835`), and the number-halo gated
on under-band presence (D-8, feat-trace §9 Q5). Draw-on is free via D-6 (`g-trace-solo` on both emit and
differ). (feat-trace §8-9)

**Deferred (not part of this framework):** feat-2 Design C (tinted `current` palette) — a ~74%-corpus
re-bless and a product call, ship as opt-in `[palette=tinted]` on its own RFC (feat-2 §5); and the
`_expand_selectors`→Region-IR centralization (§4) — independent hygiene.

Dependency: Phase 0 → 1 (glyph needs the Rect resolver + `_cell_rect`); Phase 2 ∥ Phase 1 (orthogonal, can
interleave); Phase 3 needs the two-band + diff-key from Phase 1.

---

## 9. Open questions (≤5)

1. **`\trace` thin verb vs `\annotate{glyph=trace}`** — recommend the verb (author ergonomics; costs one
   dispatch line). Confirm the product accepts one more command in the grammar surface.
2. **`color=state:X` token form** — extend the value lexer to accept bare `state:current` (best
   ergonomics, small `_grammar_values`/`_grammar_tokens` change) vs require `color="state:current"` quoted
   + enum branch (no lexer touch). Recommend the lexer extension. *(Blocks Phase 2; the bare colon is
   Confirmed-broken today, E1012.)*
3. **Diff-key format** — namespace new glyphs as `(target, glyph, arrow_from)` while eliding the glyph
   segment for legacy arc/pill/plain keys (zero churn) vs a uniform new format (churns every existing
   `data-annotation` string + any golden pinning it). Recommend elide-for-legacy. *(Verify no golden pins
   the composite before Phase 1.)*
4. **Trace number-halo** (shared with feat-trace Q5) — gate the digit halo on under-band presence so
   non-trace goldens stay byte-identical. Confirm acceptable, since it touches cell-text emit
   (`grid.py:315-327`).
5. **`bracket=true` / `leader=true` on unexpected targets** — `bracket=true` on a single cell (draw a
   1-cell hug?) and `leader=true` on a glyph with no pill (no-op?). Recommend: allow the 1-cell hug
   (cheap, consistent), no-op the pill-less leader. Lock these contracts before Phase 1/2.

---

## 10. Evidence ledger (quick index)

| Claim | Grade | Anchor |
|---|---|---|
| One decoration spine: list→set_annotations→emit_annotation_arrows | Confirmed | `scene.py:110-121,806-846`; `base.py:363-370,835-1036` |
| `_measure_emit` replays the real emitter (measured==painted) | Confirmed | `base.py:453-466` |
| Dispatch already branches arrow_from / arrow / position-only / is_range | Confirmed | `base.py:917-1000`; `_svg_helpers.py:3697-3728` |
| Two geometry kinds today (Point, Rect); no Path | Confirmed | `base.py:529-561`; `grid.py:197-211` |
| `data-annotation` `<g>` envelope + structure-driven draw-on | Confirmed | `_svg_helpers.py:2847-2856`; `static/scriba.js:205-259` |
| Emit keys per glyph: `-solo`/`-plain-arrow`/`-position-{pos}` | Confirmed | `_svg_helpers.py:2847,2068,3654` |
| Differ keys only `(target, arrow_from\|solo)` → collides for 2 solo glyphs | Confirmed (executed) | `differ.py:243,263`; `um_probe.py` P2 |
| Unknown `\annotate` params silently accepted (additive surface) | Confirmed (executed) | `_grammar_commands.py:223-242`; `um_probe.py` P1 |
| `color=state:current` dies at tokenizer (E1012), not enum (E1113) | Confirmed (executed) | `um_probe2.py`; `selectors`/values reader |
| CSS `--scriba-state-*` / `--scriba-annotation-*` split; CSS wins over Python | Confirmed | `static/scriba-scene-primitives.css:122-165`; `_svg_helpers.py:552-554` |
| R-30 one-dispatcher / R-32 stable-layout / R-31 obstacles | Confirmed | `smart-label-ruleset.md:959-1008`; `ruleset.md:903-959` |
| Parallel `emit_traces` would violate R-32.4 | Deduced | `base.py:462` + `ruleset.md:934-938` |
| block additive (BlockAccessor + expand branch + resolvers) | Hypothesized | feat-3 §3; §4 above |
| glyph / resolve_annotation_path / two-band / diff-key extension | Hypothesized | §3, §5, §8 above |
| Future glyphs (connector) already have a home: graph-edge-pill ruleset | Confirmed | `docs/spec/graph-edge-pill-ruleset.md` GEP-01…16 |
