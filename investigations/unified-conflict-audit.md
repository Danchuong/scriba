# Unified "decoration" framework — adversarial conflict audit (existing-system side)

> Independent audit for the proposed unified decoration model (anchor `Point|Rect|Path` + glyph
> `arrow|bracket|trace|leader` + label pill + `color=state:X` token-ref, all routed through
> smart-label placement/extent/obstacle, all emitting `data-annotation` for free JS animation).
> **No repo source modified.** Traced against `main` @ 9062239, scriba 0.22.1, `.venv/bin/python`.
> Audited from the *existing system* — does NOT depend on the unify-model agent's ruleset D.
> Companion briefs: `feat-trace-primitive.md`, `feat-label-state-colors.md`, `feat-grid-block-selector.md`.
>
> Grades: **[Confirmed]** read in source / executed this session · **[Deduced]** logical
> consequence of confirmed facts · **[Hypothesized]** design proposal, not yet verified.
> Baseline behaviours (§0) were **executed** (`scratchpad/ua_probe.py`, `ua_probe2.py`).

---

## 1. Hand-off Brief (3 sentences)

The unified model **survives** for the two `\annotate`/`\recolor`-family features (block bracket,
`color=state:X`) because they already flow through the one dispatcher (`emit_annotation_arrows`,
`base.py:835`) that owns the shared placement registry, obstacle set, and extent reservation — but
**`\trace` is the stress case**: it is the only decoration whose anchor is a `Path` with no single
`{shape}.{suffix}` target, and every downstream filter (differ key `differ.py:241-243`, min-arrow
reservation `_html_stitcher.py:157-160`, per-shape routing `_frame_renderer.py:141`, extent
`_measure_emit` `base.py:453-466`) keys on that target string, so the brief's `trace:{id}` naming
and its "emit *before* the cell loop for z-order" both fight the framework at once. No single
conflict **kills** the unified design, but two structural knots must be resolved up front — (a) name
the trace target `{shape}.trace[{id}]` (not `trace:{id}`) so it re-uses the target-string plumbing,
and (b) split `emit_annotation_arrows` into an under-cells and over-cells phase that share one
`placed` registry — otherwise trace should ship as a **separate patch** and the framework's scope
should be declared "annotate/recolor decoration family (Point/Rect anchors)" with trace adjacent.
A handful of smaller real conflicts (bare `color=state:X` is a **lexer** error not an enum error;
`\trace` inside `\foreach` hits a second undispatched command site; block-bracket vs the 1D-span
bracket `if/elif` precedence; two leaders drawing at once) are all fixable but none are covered by
the three briefs as written.

---

## 0. Baselines executed this session (`scratchpad/ua_probe.py`, `ua_probe2.py`) — [Confirmed]

| Probe | Result today | Consequence |
|---|---|---|
| `\trace{g}{cells=[[0,0],[0,1]]}` | **E1006** unknown command | trace needs dispatch (known) |
| `\trace` inside `\foreach…\endforeach` | **E1006** *at the foreach body* (line 4) | **2nd dispatch site** the trace brief missed (§C6) |
| `\recolor{g.block[0:1][0:1]}{…}` | **E1010** selector parse error (`expected ']'`) | no `BlockAccessor` (known) |
| `\annotate{g.block[0:1][0:1]}{…}` | **E1010** same | block anchor unparsed (known) |
| `\annotate{…}{color=state:current}` (bare) | **E1012** `expected IDENT, got COLON` | **lexer** rejects `:` before any enum check (§C17) |
| `\annotate{…}{color="state:current"}` (quoted) | **E1113** `unknown annotation color 'state:current'` | only the **quoted** form reaches the enum branch the brief patches (§C17) |
| `\annotate{…}{bracket=true}` / `{leader=true}` | **PARSED OK** | unknown bool params are silently accepted → additive, no error today (§C7) |
| `\reannotate{…}{color="state:current"}` | **E1113** | reannotate validates the same enum → `state:` branch needed there too |

---

## 2. Conflict table

Levels: **COMPOSE** (clean under one model) · **NEEDS-RULE** (composes only with a new normative
decision) · **CONFLICT** (the briefs as written collide with existing system; must change a brief).

### §1 — Smart-label ruleset (35 R-cards)

| ID | System touched (path:line) | Scenario | Level | Resolution | Grade |
|---|---|---|---|---|---|
| **C1** | R-33 content obstacles + R-31/ext arrow-stroke obstacles, built **inside** `emit_annotation_arrows` (`base.py:895-907`, `:914,922-930`) | The obstacle set (content cells + prior arc strokes) is assembled *per dispatcher call*. A `\trace` emitted as a **side-channel before the cell loop** (trace brief §4.1) never enters this loop, so (a) the trace stroke is **not** registered as an obstacle for later annotation pills, and (b) the trace's own pill can't see content cells. | **NEEDS-RULE** | Trace segments must be sampled into `ObstacleSegment`s and fed to the same registry (mirror `_sample_arrow_segments` `_svg_helpers.py:1816`). Requires trace to run *through* the dispatcher (see C14/C24), not beside it. | [Confirmed] mechanism; [Deduced] gap |
| **C2** | R-33/R-34 + `resolve_self_content_rects` (Grid `grid.py:213-224`); position-label placement `emit_position_label_svg` (`_svg_helpers.py:3495`) | Block bracket routes its pill through `emit_position_label_svg` (block brief §3.5) with the **block AABB as `cell_width`**. Grid already returns every cell box as `content_cell` obstacles → the block pill auto-avoids the cells (R-33) and escape lanes (R-34) apply. | **COMPOSE** | No new rule — block bracket is a normal position-label annotation; the dashed rect is extra SVG in the same `<g>`. | [Confirmed] |
| **C3** | The `if _pill_spans_neighbours … elif is_range …` in `emit_position_label_svg` (`_svg_helpers.py:3678` vs `:3697`) | For a **tall-narrow block** (e.g. `block[0:2][0:0]`, one column) the block AABB width ≈ one cell, so a wide pill trips `_pill_spans_neighbours` **first** and draws a stray `<line>` leader instead of the block outline (the bracket branch is an unreachable `elif`). | **NEEDS-RULE** | `bracket=true` MUST take precedence: restructure so the block-bracket branch is checked before `_pill_spans_neighbours`, or gate `_pill_spans_neighbours` off when `bracket` is set. | [Confirmed] if/elif; [Deduced] tall-narrow case |
| **C4** | Three leader emitters: arc visual-gap (R-27c) `_svg_helpers.py:2601-2627`; position "spans-neighbours" leader `:3678-3696`; **new** plain-arrow leader (label-state brief §4, path 1 = new block) | `\annotate{cell}{arrow_from=…, leader=true}`: the arc already emits an automatic visual-gap leader to `curve_mid` (`:2606`), and design-B `leader=true` forces a **second** leader to the target cell → two leaders from one pill. Under a unified "leader glyph" the gate/anchor differ per site (curve-mid vs cell vs cell-edge). | **NEEDS-RULE** | Define leader precedence: a forced `leader=true` MUST suppress the automatic visual-gap leader (or the two are explicitly additive). One gate + one anchor policy in the unified glyph. | [Confirmed] 2 existing sites; [Deduced] double-draw |
| **C5** | Single shared `placed: list[_LabelPlacement]` per frame (`base.py:916`); FP-2 anti-pattern (`lint_smart_label.py:252-304`) | Trace's midpoint pill (trace brief §7) placed in a **separate** `emit_traces` pass has its **own** `placed` list → an annotate pill and a trace pill on the same region don't see each other and can overlap. This is exactly the "isolated placement registry" FP-2 forbids. | **CONFLICT** | Trace pills MUST join the frame's shared `placed`. Only possible if trace runs inside the dispatcher (C14). Otherwise cross-glyph collision avoidance is lost. | [Confirmed] shared list + FP-2 |

### §2 — Selector / expand

| ID | System touched (path:line) | Scenario | Level | Resolution | Grade |
|---|---|---|---|---|---|
| **C6** | `\foreach` body dispatcher is a hardcoded command whitelist (`_grammar_foreach.py:159-198`) → `else: E1006` | The natural way to draw a spiral is `\foreach{i}{…}\trace{g}{cells=…}\endforeach`, but the foreach body only dispatches `recolor/reannotate/apply/highlight/annotate/cursor/foreach`. `\trace` there → **E1006** (executed §0). The trace brief patches `grammar.py` dispatch only. | **CONFLICT** | Add `elif inner_cmd == "trace": body.append(self._parse_trace())` at `_grammar_foreach.py:171`. block/state-color reuse `\recolor`/`\annotate`, already whitelisted → unaffected. | [Confirmed] executed |
| **C7** | `_expand_selectors` runs on `shape_states` (recolor **and** highlight, folded at `renderer.py:297-307`); annotations are **not** expanded (block brief §2.4) | `\highlight{g.block[…]}` and `\recolor{g.block[…]}` both need the new `block_re` branch (block brief §3.2) — one branch covers both since highlight is a `shape_states` key. `\reannotate{g.block[…]}{color=…}` matches the raw block target in the annotations list (no expansion needed). | **COMPOSE** | Add the single `block_re` branch in `_expand_selectors` (`_frame_renderer.py:378`); reannotate needs nothing extra (raw-key match). | [Confirmed] expand scope |
| **C8** | `_expand_selectors._merge` — later writes win for `state`, `highlighted` preserved (`_frame_renderer.py:357-369`) | Two overlapping `\recolor{block}` (or block over single-cell) in one step: both expand to the `cell[r][c]` product; the later command's state wins per cell, deterministically (dict insertion = command order). | **COMPOSE** | None — matches `all`/`range` semantics (block brief Q5). Document last-writer-wins. | [Confirmed] |
| **C9** | Trace targets are Grid/DPTable/Array/NumberLine only (trace brief §4); structural add/remove is Graph/Tree only | "Trace cells → removed cell" cannot occur: the four trace-eligible primitives are fixed-size at `\shape` declaration; DPTable does not shrink. A trace never dangles. | **COMPOSE** | None; if trace is ever extended to Tree/Graph, a removed cell → E1491 (trace brief §8). Out of scope now. | [Deduced] |
| **C10** | Traces live in `SceneState.traces` (proposed), recolor in `shape_states` — independent channels | `\trace` + `\recolor` on the same cell in one step: trace geometry is state-independent; they occupy different layers and different scene channels. | **COMPOSE** | None. (If the unified `color=state:X` is later applied to a *trace* stroke, it reuses the same CSS-class mechanism — feasible.) | [Deduced] |

### §3 — Runtime / animation

| ID | System touched (path:line) | Scenario | Level | Resolution | Grade |
|---|---|---|---|---|---|
| **C11** | Gen-token supersede guard (`scriba.js:40,56,283,300,313`); draw-on `annotation_add` (`:205-266`) | Rapid Next/Prev: `_cancelAnims` bumps `_gen`; `_finish`/`_runPhase2` self-abort on `myGen!==_gen`. A trace using the **same** `annotation_add` path inherits this verbatim. (Latent: the rAF stroke-draw `tick` `:242-264` is *not* gen-guarded and keeps mutating a detached node after supersede — harmless, GC'd — but the trace inherits that quirk identically.) | **COMPOSE** | None — trace is indistinguishable to the JS (structure-driven: `<path>`+`<polygon>`+`<text>`). The rAF-orphan quirk is pre-existing, not trace-specific. | [Confirmed] |
| **C12** | Differ emits `annotation_add` only when the key is **new** (`differ.py:262-276`); `compute_transitions` diffs **only** `annotations` (`:328-333`) — no `_diff_traces`; `_fadeInNewAnnotations` keys on `data-annotation` presence (`scriba.js:87-96`) | "Persistent trace re-draws every frame?" **No** — a stable trace key present in both prev/curr maps yields no `add` transition, so later frames render it statically (offset 0). **But** this requires (a) adding `_diff_traces` to `compute_transitions` (absent today) and a `FrameData.traces` field, and (b) a **stable `{id}`**: if `{id}` is ordinal and trace order changes, the key shifts → spurious remove+add → re-draw. | **NEEDS-RULE** | Define a stable trace identity. **Recommend** target = `{shape}.trace[{id}]` (see C14) so `_annotation_key` (`differ.py:241-243`) works unchanged and no `_diff_traces` is needed at all — trace becomes a normal annotation to the differ. | [Confirmed] differ; [Deduced] re-draw avoidance |
| **C13** | `_canAnim = animate && !prefers-reduced-motion` (`scriba.js:42`); `show()` routes to `snapToFrame` when false (`:331-336`); server SVG has offset 0 | Reduced-motion / print / no-JS: the trace is drawn fully immediately; `_fadeInNewAnnotations` early-returns when `!_canAnim` (`:88`). Draw-on is pure progressive enhancement. | **COMPOSE** | None (trace brief §5.4 confirmed). | [Confirmed] |

### §4 — Extent / viewBox / goldens

| ID | System touched (path:line) | Scenario | Level | Resolution | Grade |
|---|---|---|---|---|---|
| **C14** | `_measure_emit` emits **only** `self._annotations` via the dispatcher (`base.py:453-466`); `_apply_min_arrow_above` filters `f.annotations` by `target.startswith(shape_name + ".")` (`_html_stitcher.py:157-160`); per-shape routing filters the same way (`_frame_renderer.py` set_annotations sites) | **The core knot.** A trace emitted as a side-channel with target `trace:{id}` (trace brief §5.3) is invisible to the extent measurement, the cross-frame min-arrow reservation, and the per-shape `set_annotations` routing — *because* `trace:{id}` does not start with `{shape}.`. The `trace:` naming is chosen precisely to make the differ treat traces separately, but that same distinctness breaks 4 target-string filters. | **CONFLICT** | **Name the target `{shape}.trace[{id}]`** (starts with `{shape}.`). Then differ, min-arrow, per-shape routing and `_annotation_key` all work unchanged, and trace is a genuine annotation subtype. This single rename collapses most of the trace brief's ~13-file parallel plumbing. | [Confirmed] all 4 filters |
| **C15** | Same filters as C14, but block target = `g.block[…]` (via `_selector_to_str`, block brief §3.1) **starts with** `g.` | Block bracket routed through the dispatcher with target `g.block[…]` **is** counted by `_apply_min_arrow_above` (startswith `g.`), measured by `_measure_emit`, and reserved above the top row via `annotation_height_above` — the extent parser handles the dashed `<rect>` (`_extent.py:164-169`). | **COMPOSE** | None — block bracket's above-inset is auto-reserved. Contrast C14: block *embraces* the target-string plumbing, trace *fights* it. | [Confirmed] |
| **C16** | `measure_painted_extent` parses `path/polyline/polygon/rect` (`_extent.py:180-189`); reservation only sees what `_measure_emit` emits | A trace with `arrowhead=end` pointing up at row-0's top, a `startdot` circle, or a midpoint pill placed *above* the path can poke **above** the grid AABB. If trace is a side-channel (C14), that overhang is **not** reserved → the viewBox clips it or it collides with a neighbour primitive above. | **CONFLICT** (consequence of C14) | Fixed by C14's rename + running trace through the (two-phase) dispatcher so `_measure_emit` sees it. Trace brief §7's "extent ≈ 0" holds **only** for the strictly-interior center-to-center case. | [Confirmed] parser; [Deduced] overhang |

### §5 — Colour token-ref (`color=state:X`)

| ID | System touched (path:line) | Scenario | Level | Resolution | Grade |
|---|---|---|---|---|---|
| **C17** | Value lexer rejects `:` in a bare enum (**E1012**); only a **quoted** string reaches the colour enum check (**E1113**) — both executed §0 | The label-state brief §3 says "branch on `color.startswith("state:")`", implying the value arrives as `"state:current"`. But **bare** `color=state:current` is an **E1012 lexer error** (`expected IDENT, got COLON`) — it never reaches the enum branch. Only `color="state:current"` (quoted) tokenises. | **CONFLICT** | Either (a) require the **quoted** form `color="state:current"` in docs/examples (cheap, no lexer work — the `startswith` branch then works), or (b) extend the value lexer to accept `:` in bare enums. The brief's bare-form examples do not tokenise as written. | [Confirmed] executed |
| **C18** | `DiagramRenderer` ships `scriba-scene-primitives.css` (`renderer.py:843,861`) which defines `--scriba-state-*` | `color=state:X` inside `\begin{diagram}` has the state tokens present; `\annotate` is legal in a diagram (only `\step`/`\narrate` are barred, `renderer.py:787,799`). The new `--scriba-annotation-state-*` vars land in the same stylesheet → shipped in both envs. | **COMPOSE** | None. (Diagram is single-frame static → no differ/draw-on; irrelevant to trace animation.) | [Confirmed] |
| **C19** | State rules are ordinary class selectors, dark tokens exist (`scriba-scene-primitives.css:640-672`); theme toggle flips `data-theme` (`scriba.js:10-16`) | `color=state:X` inherits `var(--scriba-state-X-*)` which has light+dark variants → dark-adapts for free on toggle, no new dark authoring. | **COMPOSE** | None (label-state brief §3 option ii's central advantage). | [Confirmed] |
| **C20** | `tests/unit/test_contrast.py` gate; `done`/`dim` identifying fills `#c1c8cd`/`#e6e8eb` on white pill | `state:done`/`state:dim` mapped to their **fill** token would fail WCAG on the white pill — `#c1c8cd` on white ≈ **1.4:1** (label-state brief §3, `< 4.5:1`). The contrast test would fail. | **NEEDS-RULE** | `state:done`/`dim`/`idle` MUST map to the state **text** token (dark neutral) or `muted`, not the faint fill (label-state brief §3, Q2). Each `--scriba-annotation-state-*` must pass ≥ 4.5:1. | [Confirmed] number cited; [Deduced] gate |
| **C21** | Annotation `color` is a stored snapshot (`renderer.py:315`); persistent across steps (`scene.py:206-208`); `shape_states` **is** in scope where the ann dict is built (`renderer.py:295,309`) | `\annotate{cell}{color=state:current}` then a later `\recolor{cell}{state=done}`: the label's stored colour stays `"state:current"`, re-emitted as class `scriba-annotation-state-current` on **every** frame, while the cell becomes `scriba-state-done` → label (blue) and cell (grey) **diverge permanently**, not just during a transition. | **NEEDS-RULE** | Decide semantics: `state:X` = **snapshot** (deterministic, current naive build) vs a separate `color=match` = **live** (feasible — `shape_states[shape][target]` is in scope at `renderer.py:309`). Recommend explicit snapshot + optional `match`; document the divergence. | [Confirmed] snapshot + scope |
| **C22** | JS has **no** `annotation_recolor` handler (only `recolor` for cells, `scriba.js:122`); differ emits `annotation_recolor` (`differ.py:287-299`) | `\reannotate{cell}{color="state:done"}` produces an `annotation_recolor` transition the JS ignores → the label colour changes only on the next full SVG swap, not during the animated step. Pre-existing quirk that `state:` reannotate inherits. | **COMPOSE** (pre-existing) | Out of scope for the unified model; flag as a latent annotation-recolor gap independent of `state:`. | [Confirmed] |

### §6 — Docs / tooling gates

| ID | System touched (path:line) | Scenario | Level | Resolution | Grade |
|---|---|---|---|---|---|
| **C23** | `check_ruleset_sync.py` — every `### R-*` card MUST carry `**Code ref:**` + `**Test ref:**`; non-`pending` `path:anchor` refs are verified to exist (`:65-110`); card regex needs the em-dash `— ` (`:67`) | Three new R-cards (trace, block, state-colour) cannot merge doc-first: the cited code symbol must exist in the file and the test file must exist, else CI fails. Wired into `tests/doc_coverage/test_ruleset_sync.py`. | **NEEDS-RULE** (landing order) | Land each R-card **with** its code+test in the same commit, or cite `pending v0.x` (the escape hatch at `:89,97`). Use the exact `### R-NN — Title` format. | [Confirmed] |
| **C24** | `lint_smart_label.py` FP-6 (`_check_fp6 :548-584`) flags any `emit_position_label_svg`/`emit_*_arrow_svg` call inside a primitive method except `dispatch_annotations`; `_EXCLUDED_FILES` excludes `base.py`/`_svg_helpers.py` (`:62-72`); default mode is **advisory** (exit 0) unless `--strict` | Trace's midpoint pill calls `emit_position_label_svg`. If that call lives in a per-primitive `emit_svg`/`emit_traces` in `grid.py` etc., it is an **E1570-F** (FP-6) violation. It escapes only if the call sits inside `base.py`'s `emit_traces` (an excluded file). | **CONFLICT** (smell) | Put the shared `emit_traces` in `base.py` (excluded) **and** route through the dispatcher, or the lint (in `--strict` CI) blocks it. Confirms trace's placement helper must not live in a leaf primitive. | [Confirmed] |
| **C25** | `lint_smart_label.py` FP-2 (`_check_fp2 :252-304`) forbids `foo: list[_LabelPlacement] = []` outside `register_decorations`/`dispatch_annotations` | Trace's own `placed: list[_LabelPlacement] = []` (needed for its separate pass, C5) is the exact anti-pattern FP-2 codifies — "isolated placement registry that breaks multi-primitive collision avoidance". The linter (scoped to non-`base.py` files) may not catch it, but the *rule exists* and names the smell. | **CONFLICT** (smell) | Do not give trace its own registry; share the frame `placed` (requires the two-phase dispatcher, C5/C14). | [Confirmed] |
| **C26** | `docs/SCRIBA-TEX-REFERENCE.md` is the single-file author contract; `tests/doc_coverage/` generates tests **from** it (`tests/doc_coverage/README.md:3`) | Adding `\trace`, `block[…]`+`bracket`, and `color=state:X` each needs a REFERENCE section; doc-coverage will generate snippet tests from them, so every documented form must actually render. The bare-`state:X` example (C17) would generate a **failing** snippet. | **NEEDS-RULE** | Document the **quoted** `color="state:X"` form only; ensure each new section's snippet renders (esp. C3, C17). | [Confirmed] |

---

## 3. Can any conflict kill the unified design?

**No conflict kills it outright — but one decision gates whether trace belongs in the model at all.**

The two `\annotate`/`\recolor`-family features compose cleanly: block bracket and `color=state:X`
both inherit the shared registry (C2), the extent reservation (C15), the obstacle set (C2), the
differ (C7), and the theme system (C19) *for free*, because their anchors are `Point`/`Rect` with a
`{shape}.{suffix}` target that every existing filter already understands. For these two, the unified
"decoration" framing is not just viable — it is the path of least resistance, and the only real work
is normative (C3 if/elif precedence, C20 WCAG mapping, C17 quoted-form, C21 snapshot semantics).

`\trace` is where the framework is load-bearing. Its `Path` anchor has **no single target**, and the
brief's two headline choices — target `trace:{id}` and "emit before the cell loop for z-order under
the numbers" — each break a different half of the framework:

- `trace:{id}` breaks the **target-string plumbing** (C14): extent (`_measure_emit`), min-arrow
  reservation, and per-shape routing all filter on `target.startswith(shape + ".")`.
- "before the cell loop" breaks the **shared placement pass** (C5/C24/C25): the one `placed` registry
  and the obstacle set live *inside* `emit_annotation_arrows`, which emits **last / on top**.

These are resolvable, and cheaply, but only together:

1. **Rename** the trace target to `{shape}.trace[{id}]` → the differ, min-arrow, routing, and
   `_annotation_key` all work unchanged; no `_diff_traces`, no `FrameData.traces`, no parallel
   plumbing (collapses ~half the trace brief's 13-file estimate).
2. **Split** `emit_annotation_arrows` into `…_under` (traces, before cells) and `…_over` (arrows,
   brackets, leaders, pills, after cells) phases that **share one `placed` list and one obstacle
   set**, and make `_measure_emit` replay **both** phases. The unified glyph then carries a `layer`
   attribute (`under` for trace, `over` for the rest).

**Verdict:** if the team is willing to do (1)+(2), the unified model is coherent and strictly reduces
total code versus three separate patches. If (2) — the dispatcher refactor — is out of scope for this
cycle, then **trace should ship as a separate patch** and the framework's advertised scope should be
narrowed to *"annotate/recolor decoration family (Point/Rect anchors, one placement pass, one
target-string namespace)"*, with `\trace` documented as an adjacent primitive that shares only the
JS `data-annotation` draw-on contract (which it genuinely does, C11/C13). The three-patch fallback
loses nothing for block/state-colour and de-risks the one feature that stresses the model.

---

## 4. Recommendation — conditions for going unified

Ship the unified model **iff** all of the following are accepted up front; otherwise 2-unify
(block + state-colour) and ship trace separately.

1. **Trace target = `{shape}.trace[{id}]`**, `{id}` a stable per-declaration id (not ordinal), so
   the differ key and all `startswith(shape+".")` filters work unchanged (C12, C14).
2. **Two-phase, registry-sharing dispatcher**: `emit_annotation_arrows` gains an under-cells phase;
   `_measure_emit` replays both; one `placed` + one obstacle set across all glyphs (C1, C5, C16, C24, C25).
3. **Second dispatch site**: add `trace` to the `\foreach` body whitelist (`_grammar_foreach.py:171`) (C6).
4. **`color="state:X"` is quoted** in the grammar/docs (bare form is an E1012 lexer error), and the
   `state:` branch is added to **both** `_parse_annotate` and `_parse_reannotate` (C17).
5. **State-colour WCAG mapping**: `done`/`dim`/`idle` → state **text** token, not fill; each
   `--scriba-annotation-state-*` passes `test_contrast.py` (C20).
6. **`state:X` semantics documented as snapshot** (label does not track a later `\recolor`); optional
   `color=match` for the live binding (C21).
7. **Leader precedence rule**: forced `leader=true` suppresses the automatic visual-gap leader (C4).
8. **Block-bracket precedence**: `bracket=true` outranks the `_pill_spans_neighbours` branch (C3).
9. **Landing discipline**: each new R-card lands with real code+test refs (or `pending`), quoted-form
   snippets in `SCRIBA-TEX-REFERENCE.md` that actually render (C23, C26).

If (1)+(2) are not funded this cycle → **3-patch fallback**: block and state-colour unify under the
existing dispatcher with only normative additions (C2/C15/C19 are already clean); trace ships beside
them, sharing the JS draw-on contract but not the Python decoration model. Scope the framework
accordingly.

---

## 5. Evidence ledger (quick index)

| Claim | Grade | Anchor |
|---|---|---|
| Bare `color=state:X` → E1012 lexer; quoted → E1113 | Confirmed (executed) | `scratchpad/ua_probe.py`, `ua_probe2.py` |
| `\trace` in `\foreach` → E1006 at foreach body | Confirmed (executed) | `_grammar_foreach.py:159-198` |
| block selector unparsed today → E1010 | Confirmed (executed) | `selectors.py` (no BlockAccessor) |
| One shared `placed` registry per frame | Confirmed | `base.py:916` |
| Obstacle set (content cells + arc strokes) built inside the dispatcher | Confirmed | `base.py:895-907,914,922-930` |
| Differ key `(target, arrow_from|solo)`; only `annotations` diffed | Confirmed | `differ.py:241-243,262-276,328-333` |
| `_measure_emit` emits only `self._annotations` | Confirmed | `base.py:453-466` |
| min-arrow reservation filters `target.startswith(shape+".")` | Confirmed | `_html_stitcher.py:157-160` |
| Extent parser handles path/polyline/polygon/rect | Confirmed | `_extent.py:164-189` |
| Draw-on gen-token supersede guard | Confirmed | `scriba.js:40,56,283,300,313` |
| `_fadeInNewAnnotations` keys on `data-annotation` presence; gated on `_canAnim` | Confirmed | `scriba.js:87-97` |
| Two existing leader sites (arc visual-gap R-27c; position spans-neighbours) | Confirmed | `_svg_helpers.py:2601-2627`, `:3678-3696` |
| 1D span bracket is an `elif` after `_pill_spans_neighbours` | Confirmed | `_svg_helpers.py:3678,3697-3728` |
| DiagramRenderer ships state CSS; `\annotate` legal in diagram | Confirmed | `renderer.py:843,861,787,799` |
| State rules class-based; dark tokens exist | Confirmed | `scriba-scene-primitives.css:640-672`; `scene-primitives` state block |
| `#c1c8cd` on white ≈ 1.4:1 (done/dim fill fails WCAG) | Confirmed (cited) | `feat-label-state-colors.md §3` |
| lint FP-6 flags helper calls outside dispatcher; base.py excluded; advisory default | Confirmed | `lint_smart_label.py:548-584,62-72,676` |
| lint FP-2 forbids isolated `list[_LabelPlacement]` | Confirmed | `lint_smart_label.py:252-304` |
| check_ruleset_sync requires code+test refs per card | Confirmed | `check_ruleset_sync.py:65-110` |
| JS has no `annotation_recolor` handler | Confirmed | `scriba.js:122` (only `recolor`) |
| Rename trace → `{shape}.trace[{id}]`; two-phase dispatcher | Hypothesized | §3, §4 |
