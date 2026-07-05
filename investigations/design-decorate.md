# Design — Decoration / Marking Verbs (the free marks a teacher makes)

> DESIGN spec (read-only investigation; only this doc written). Repo @ `main` `5e7d75b`,
> scriba 0.25.0, `SCRIBA_VERSION = 18`. Every `path:line` was read this session; every
> gap and every "rides existing kind" claim is backed by source **and** a rendered probe
> (`SCRIBA_ALLOW_ANY_OUTPUT=1 .venv/bin/python render.py <p>.tex -o <p>.html`; no Playwright).
>
> **Axis:** the marker verbs a teacher lays *on top of* an already-drawn structure — cross
> out a rejected candidate, drop a free note, spotlight the whole board, sweep a path along
> graph edges. Companion investigations: `teaching-marker-verbs.md` (GAP-1 strike, GAP-2
> graph-trace) and `teaching-framing-attention.md` (untethered note, board spotlight).

---

## 1. Problem + confirmed constraints

A teacher's overlay marks are almost fully covered by shipped verbs, but **four** high-value
gestures have no clean surface. All four are *overlays* — they sit on top of a structure and
leave its identity/state intact. Confirmed this session (source + render):

| Gesture | Status | Confirmed constraint (path:line + render) |
|---|---|---|
| **Strike / cross-out / prune** (struck-yet-visible) | **MISSING** | `VALID_STATES` has 9, no `strike` (`constants.py:27-32`); parse-enforced (`_grammar_commands.py:160`). Rendered `\recolor{a.cell[1]}{state=strike}` → **E1109**. No strike/line-through in the 11-kind registry (`scriba.js:152-324`) or scene CSS. |
| **Untethered note** (free margin callout) | **MISSING** | `\annotate` target → `parse_selector`, must be a shape identifier (`_grammar_commands.py:554`, `selectors.py` E1010); resolves via `resolve_annotation_point` — no xy path (`base.py:774-781`). Rendered `\annotate{(120,40)}{…}` → **E1010**. |
| **Board-wide spotlight** (dim *all* other shapes) | **AWKWARD** | `\focus` dims the complement **inside one shape**; `_apply_defocus` only tags focused shapes' own parts (`_frame_renderer.py:641-697`); "other shapes are untouched" (§5.16 `:734`). |
| **Trace a path over graph/tree edges** | **AWKWARD** | `\trace` is `supports_trace`-gated to Array/Grid/DPTable/NumberLine (`base.py:271`, flags in `array.py:112` etc.); Graph/Tree → **E1118** (`scene.py:1075-1081`). Rendered `\trace{g}{…}` on a Graph → **E1118**. |

**The hard invariant every design must honor** (the scriba DNA, confirmed in
`docs/spec/motion-ruleset.md`):

- **A-2 closed motion registry** (`:59-80`): 11 kinds, closed under inversion. A new kind is a
  RED FLAG. Target: **0 new motion vocabulary**.
- **A-0.vi opt-in → byte-stable** (`:34`) + **version policy** (`:244-251`): a new command
  emitting only existing kinds ships with **no `SCRIBA_VERSION` bump** — *unless it ships shared
  CSS* (which regenerates every inlined stylesheet) or touches `scriba.js`/the frame schema.
- **The established pattern for zero-CSS overlays:** `\trace` and the R-35 `bracket=true`
  outline both render as `<g class="scriba-annotation scriba-annotation-{color}"
  data-annotation="…">` with the mark drawn by **inline presentation attributes**, reusing the
  *existing* `scriba-annotation-*` classes for theming. Grep confirms **zero** dedicated
  `.scriba-trace`/`.scriba-bracket` CSS. Rendered trace group (captured this session):
  ```html
  <g class="scriba-annotation scriba-annotation-good" data-annotation="a.trace[t1]-solo" …>
    <path d="M30,20 L92,20 L154,20 L216,20" fill="none" stroke="#027a55" stroke-width="2.5"/>
    <polygon points="…" fill="#027a55"/><rect …/><text …>sweep</text></g>
  ```
  and every decoration differ (`_diff_traces`, `_diff_links`, `_diff_groups`, `_diff_cursors`,
  `_diff_annotations` — `differ.py:257-477`) emits **only** `annotation_add` / `annotation_remove`
  / `annotation_recolor`. This is the substrate all four verbs will ride.

---

## 2. Approaches + trade-offs

### 2A. Strike — a STATE vs a DECORATION (the crux)

**Option A — 10th recolor state (`state=strike`).**
Add `strike` to `VALID_STATES`; every primitive's emit loop already stamps `scriba-state-{X}` on
its `<g data-target>`, and it rides the shipped `recolor` kind for free.

**Option B — a decoration overlay** riding `annotation_add`, drawn inline like the R-35 bracket.

**Verdict: DECORATION (Option B).** Three independent arguments, each decisive:

1. **Semantic — state is single-valued, strike is orthogonal.** "Only one `scriba-state-*` class
   per element" (`scriba-scene-primitives.css:188`). The teaching need is *struck-YET-still-
   showing-its-role*: the cell was the `current` candidate, we reject it, and it must stay
   **red/current-colored AND crossed out** next to the survivors. A single state slot cannot hold
   both "was-current" and "struck". Strike is orthogonal to the color-role — exactly like the
   R-35 bracket, `\focus` defocus, and A-3 emphasis are orthogonal overlays. Orthogonal overlays
   *are* decorations by definition (A-3).

2. **Byte-cost — a state forces new shared CSS; a decoration doesn't.** A `scriba-state-*` class
   can only *restyle the existing* `<rect>`/`<circle>` (fill/stroke/opacity). It **cannot add a
   diagonal line** — SVG has no `::before`, and CSS can't inject a child element. So strike-as-
   state *still* needs an emitted overlay element **and** a new `.scriba-state-strike` rule →
   shared-stylesheet change → regenerates every inlined golden → **`SCRIBA_VERSION` bump + full
   re-bless** (version policy `:250`). A decoration draws the line inline (like trace) and reuses
   `scriba-annotation-{color}` → **zero new CSS → no bump**. Strictly cheaper.

3. **Mechanics — a state fights the single-state model.** A strike-state would need all 16
   primitives' emit loops to draw the overlay (or a shared post-pass) and would collide with
   `\playeach`, `\cursor prev_state/curr_state`, and `\ref` ink — all of which assume one state
   per cell. A decoration reuses the *one* shared emit path (`emit_annotation_arrows`) plus the
   broad `resolve_annotation_box` coverage (8 primitives already override it) with a center
   fallback — no per-primitive plumbing.

The *only* thing state buys is "part of the recolor sweep" (recolorable, `\ref`-tintable). But a
strike is a **terminal** "rejected" mark — you never recolor a strike to `done`. That affordance
is a mismatch. **Decoration wins on all three axes.**

**Sub-choice — standalone `\strike{x}` verb vs `\annotate{x}{strike=true}` flag.** Converge on the
**flag**. It is the exact R-35 `bracket=true` precedent (annotate already hosts label-less
geometry overlays), costs **zero new lexer tokens**, and is **combinable**: `\annotate{x}{strike=
true, label="rejected", color=error}` crosses out *and* says why in one gesture. A standalone verb
reads marginally better but duplicates annotate's whole plumbing (lexer+ast+parser+scene+differ)
for an identical pixel — ~M cost for the same result as the ~S flag. DNA rule #1 ("least new
vocabulary, reuse before inventing") settles it. *If synthesis prefers verb-readability, the emit
code is identical — only the parse entry-point differs (a one-file swap).*

### 2B. Untethered note — extend `\annotate` vs a new `\note` verb

- **Extend `\annotate{…}{at="(x,y)"}`:** forks annotate's grammar (its target is *always* a
  selector, E1010 otherwise) and, worse, a raw coordinate has **no identity key** for the differ
  (A-0.ii) and is unusable in practice (authors don't know computed pixel geometry).
- **New `\note{id}{…}` stage-level verb (chosen):** a sibling of `\link`/`\combine` (also stage-
  level, no shape prefix, keyed `link[…]-solo`, `differ.py:284-319`). Keyed `note[{id}]-solo` by an
  explicit author id → clean identity → rides `annotation_add/remove/recolor`. Anchored to a
  **board-relative margin enum** (the framing investigation's exact words: "free … **margin**
  note"), not a raw coord — deterministic (viewBox is byte-identical every frame, confirmed
  `_frame_renderer.py:861-862`) and usable ("put it top-right"). Painted *inside* the existing
  viewBox → **no envelope growth → R-32 untouched**.

Trade-off accepted for v1: a note paints in existing whitespace and can overlap dense content
(mitigated by the author picking an empty corner + the shipped `.scriba-annotation:hover` fade).
Reserving a true margin lane (growing the viewBox) is an R-32 reservation change — **deferred to
v2**; a raw-coord `at="(x,y)"` escape hatch is likewise a documented future extension.

### 2C. Board spotlight — reuse `\focus` + a `scope` param

`\focus` already bakes the shipped `.scriba-defocused` class (opacity 0.35, A-3 overlay,
byte-stable resting frame). The only change for board scope is: `_apply_defocus` also tags the
`<g data-target>`s of the *other* shapes. Expose via an optional 2nd brace `scope=shape|board`
(default `shape` = today's behavior, byte-identical). **Zero new CSS** (reuses `.scriba-
defocused`), zero new kind (defocus is a baked-class overlay, not a motion kind).

### 2D. Graph/tree trace — lift E1118

`\trace` is capability-gated by `supports_trace` (`base.py:271`). Graph and Tree both expose
`resolve_annotation_point` (node anchor; `graph.py:1435`, `tree.py:739`) — enough to thread a
polyline through node centers. Flip `supports_trace=True` on both, map `cells=` entries to
`node[{id}]` suffixes, and the *same* `emit_traces_under` decoration draws the sweep. Rides the
shipped trace `annotation_add`. The straight segment between adjacent node centers **is** the edge
in a hierarchical/tree layout — the "follow the edges" gesture, no new machinery.

---

## 3. THE CHOSEN DESIGN — the DECORATE verb set

**One design philosophy binds all four:** *static, inline-styled overlay decorations that ride the
existing `annotation_add`/`annotation_remove`/`annotation_recolor` contract (or the shipped
`.scriba-defocused` baked overlay), reuse the existing `scriba-annotation-*` color classes, and
therefore add **zero new motion kinds** and **zero shared CSS**.* Net new vocabulary: **1 verb
(`\note`) + 1 flag (`strike=true`) + 1 param (`scope=board`) + 1 lifted restriction (trace on
Graph/Tree).**

### Verb 1 — `\strike` (as `\annotate{target}{strike=true}`)

```latex
% cross out a rejected candidate but KEEP it visible next to the survivors
\annotate{cand.cell[2]}{strike=true, color=error}
% strike AND label in one gesture ("crossed out, here's why")
\annotate{cand.node[G]}{strike=true, label="dominated", color=error}
```

- **Semantics:** draws a diagonal cross-out over `resolve_annotation_box(target)` (corner-to-
  corner). Orthogonal to `\recolor` state — the element keeps its `scriba-state-*` color.
  Persistent by default; `ephemeral=true` clears at the next `\step` (like every annotation).
- **Coverage:** every primitive that overrides `resolve_annotation_box` — Array (cell + `range`),
  Grid, DPTable, Matrix, Graph, Tree, Bar, Hypercube (grep-confirmed 8). A center-anchored
  fixed-size mark falls back for the rest; a target that resolves neither box nor point
  **soft-drops with a warning (E1119)** — render never blanks (mirrors trace's out-of-range
  soft-drop, `base.py:555-565`).
- **New E-code:** **E1119** (emit-time, soft) — "strike target 'X' has no drawable extent;
  skipped". No parse-time code needed (the flag is always syntactically valid).

### Verb 2 — `\note{id}{text=…, at=<anchor>, color=…, ephemeral=…}`  *(new, stage-level)*

```latex
\note{n1}{text="careful: 0-indexed", at=top-right, color=warn}
\note{n2}{text="$O(n\log n)$", at=bottom-left}
```

- **Semantics:** a free callout pill keyed `note[{id}]-solo`, painted inside the existing viewBox
  at a **board-relative margin anchor**. Not tied to any shape. Persistent by default; ephemeral
  if flagged. Re-issuing the same `id` updates it (recolor rides `annotation_recolor`).
- **`at=` enum (`VALID_NOTE_ANCHORS`):** `top-left, top, top-right, right, bottom-right, bottom,
  bottom-left, left` — 8 compass margins. Multiple notes sharing an anchor stack downward
  deterministically.
- **Determinism:** anchor → viewBox-relative coordinate computed once; the viewBox is byte-
  identical on every frame (`_frame_renderer.py:861-862`) → the note lands in the same spot every
  frame.
- **New E-codes:** **E1120** — "`\note` requires `id=` and `text=`"; **E1121** — "unknown note
  anchor 'X'; valid: …" (enum gate, mirrors annotation-position **E1112**).

### Verb 3 — `\focus{target}{scope=board}`  *(param extension)*

```latex
\focus{tree.node[root]}{scope=board}   % dim EVERY other shape on the board
\focus{a.cell[1]}                       % unchanged: dims only a's other cells
```

- **Semantics:** `scope=shape` (default) = today's intra-shape dim, **byte-identical**.
  `scope=board` also tags every `<g data-target>` of *other* shapes with the shipped
  `.scriba-defocused`. Ephemeral (A-3), cleared next `\step`, resting SVG byte-stable. Stage-level
  overlays (`\link`, `\note`) stay lit so the focused element's arrows remain readable.
- **New E-code:** **E1122** — "unknown focus scope 'X'; valid: shape, board" (enum gate).

### Verb 4 — `\trace{Graph|Tree}{cells=[node-seq], …}`  *(restriction lift)*

```latex
\trace{g}{cells=["A","B","C","F"], color=good, label="BFS"}   % follow the edges
\trace{t}{cells=[0, 2, 5], color=path}                          % by node index
```

- **Semantics:** Graph/Tree become `supports_trace=True`; `cells=` accepts node ids (strings) or
  indices, mapped to `node[{id}]` suffixes; the polyline threads node centers. Same trace
  decoration, same `annotation_add` draw-on, same soft-drop on an unknown node. E1118 narrows from
  "grid-only" to "grid + Graph/Tree"; genuinely non-trace primitives (Stack, Queue, …) still raise
  E1118.

### 3.1 Motion-kind analysis — prove 0 new kinds

| Verb | Rides | New kind? |
|---|---|---|
| `strike=true` | `_diff_annotations` (`differ.py:422`) → `annotation_add/remove/recolor` — the strike sub-group is one more `[data-annotation]` group, drawn-on exactly like the bracket | **NO** |
| `\note` | new `_diff_notes` mirroring `_diff_links` verbatim (`differ.py:284-319`) → `annotation_add/remove/recolor` | **NO** |
| `\focus scope=board` | baked `.scriba-defocused` overlay applied at frame-render (`_apply_defocus`) — **not a motion kind at all** (A-3, matrix row `motion-ruleset.md:231`) | **NO** |
| graph/tree trace | `_diff_traces` (`differ.py:257`) → `annotation_add/remove` — unchanged | **NO** |

The 11-kind registry closes unchanged. `scriba.js` is **not touched**.

### 3.2 Byte-stability + `SCRIBA_VERSION`

**No bump.** All four are additive Python emit/parse paths. **Zero** shared `scriba.js` change,
**zero** shared CSS change (strike/note draw inline + reuse `scriba-annotation-*`; board-spotlight
reuses shipped `.scriba-defocused`; graph-trace reuses the trace path). Per version policy
(`motion-ruleset.md:250`): "New … command emitting only existing kinds → additive → no bump
(unless it ships shared CSS)." Non-users take no new emit path → **byte-identical output** (A-0.vi).
This is the best-case the DNA asks for.

### 3.3 R-32 (envelope invariance)

- **strike:** the diagonal lives inside `resolve_annotation_box` (the cell/node extent) → inside
  the content box → `bounding_box()` untouched (same argument as trace threading cell centers,
  `base.py:539-541`).
- **note:** painted inside the existing viewBox, no envelope growth.
- **board spotlight:** opacity overlay only (A-3), resting SVG byte-identical, `bounding_box()`
  untouched.
- **graph/tree trace:** polyline through node centers, inside the content box.

All four leave every frame's reserved envelope unchanged → R-32.1–.4 hold with no prescan work.

### 3.4 TDD plan (RED first)

*Strike* — `tests/unit/test_annotate_strike.py`:
1. `test_strike_emits_inline_group` — `\annotate{a.cell[1]}{strike=true}` emits `<g
   data-annotation="a.cell[1]-strike">` with a `<line>`/`<path>`; **no** new CSS class. *(RED: no
   strike handling today.)*
2. `test_strike_coexists_with_state` — `\recolor{a.cell[1]}{state=error}` + strike → cell keeps
   `scriba-state-error` **and** carries the strike group (orthogonality).
3. `test_strike_rides_annotation_add` — differ prev(none)/curr(strike) → a `kind=="annotation_add"`
   transition; assert **no** kind outside the closed 11.
4. `test_strike_ephemeral_clears` / `test_strike_unresolvable_soft_drops` (→ E1119 warn, render
   continues).
5. `test_no_strike_byte_identical` — a strike-free golden renders unchanged.

*Note* — `tests/unit/test_note_command.py`: emits `note[n1]-solo` at the anchor coord;
missing id/text → **E1120**; bad anchor → **E1121**; differ → add/remove/recolor only; same coord
across two frames (determinism).

*Board spotlight* — `tests/unit/test_focus_scope.py`: two shapes a,b; `scope=board` dims **b**'s
cells (today it doesn't); default `\focus` **byte-identical** to today (byte-stability guard); bad
scope → **E1122**.

*Graph/tree trace* — extend `tests/unit/test_trace_*`: `\trace{g}{cells=["A","B","C"]}` → polyline,
no E1118; Tree likewise; bad node → soft-drop; `\trace` on Stack **still** E1118 (gate intact).

### 3.5 Implementation sketch (files + approach)

| Verb | Files (approach) | Cost |
|---|---|---|
| **strike=true** | `ast.py` (`AnnotateCommand.strike: bool`), `_grammar_commands.py::_parse_annotate` (read `strike=`), `scene.py::_apply_annotate` (`AnnotationEntry.strike`), `base.py::emit_annotation_arrows` (add a `strike` block right after the R-35 bracket block at `:1208`: resolve box → emit `<g class="scriba-annotation scriba-annotation-{color}" data-annotation="{target}-strike"><line …/></g>`, inline `stroke` fallback), docs §5.8. **No** CSS/js/differ change. | **S** |
| **\note** | `lexer.py` (`\note` token), `ast.py` (`NoteCommand`), `_grammar_commands.py::_parse_note`, `grammar.py` (dispatch), `constants.py` (`VALID_NOTE_ANCHORS`), `scene.py` (`_apply_note` + `notes` on FrameData + ephemeral clear), `differ.py::_diff_notes` (copy `_diff_links`), `_frame_renderer.py` (stage emit: anchor→coord + pill, like `_apply_link_overlay`), docs new §5.x. | **M** |
| **focus scope=board** | `ast.py` (`FocusCommand.scope`), `_grammar_commands.py::_parse_focus` (optional 2nd brace, enum), `scene.py::_apply_focus` (record scope), `_frame_renderer.py::_apply_defocus` (board branch: tag other shapes' `data-target`s), docs §5.16. **No** CSS change. | **S** |
| **graph/tree trace** | `graph.py`+`tree.py` (`supports_trace=True`, `_trace_cell_suffix`→`node[{id}]`, `resolve_trace_point`→node center if the annotation anchor isn't already center), `_grammar_commands.py::_parse_trace` (keep string node-ids, don't int-coerce), `scene.py` E1118 message, docs §5.9 (lift "grid only"). | **S–M** |

### 3.6 Risk

- **strike — LOW.** Mirrors the bracket block exactly. Watch: a strike over a `state=hidden`
  (display:none) target would float → skip strike when the target is hidden (soft). Center-fallback
  mark on box-less primitives may look plain — documented.
- **note — LOW-MED.** Most new surface (a real command). Pin the anchor→coord map with a golden;
  overlap-with-content is documented (no reservation in v1).
- **board spotlight — LOW.** `_apply_defocus` already regexes `<g data-target>`; the board branch
  is a set-membership tweak. Pin a default-scope byte-stability golden.
- **graph/tree trace — MED.** `_parse_trace` currently int-coerces `cells`; the string-node path
  must not disturb existing grid traces (keep the int branch, add a string branch). Straight
  polylines can cross unrelated nodes on dense graphs (documented; correct for tree/hierarchical
  layouts).

---

## 4. Recipe-today baseline — the recolor-or-remove binary

Today, pruning a rejected candidate has exactly **two** expressible moves, both lossy — confirmed
by render:

- **`\recolor{x}{state=dim|error}`** — keeps `x` visible but only **re-tints** it. `dim` reads
  "faded/irrelevant", `error` reads "invalid/bad" — neither reads "considered, then eliminated" —
  and it **overwrites** the role color, so `x` can no longer show it *was* the current candidate.
- **`\recolor{x}{state=hidden}` / `remove_node`** — `x` **vanishes**; the reasoning ("we tried
  this branch") disappears with it.

There is no third option. The teacher's actual gesture — **strike-but-keep** — is the only mark
that says *"this was on the table, here is the X, and it stays visible next to the survivors so the
elimination is legible."* Rendered proof: `\recolor{a.cell[1]}{state=strike}` → **E1109**; the only
substitute is `recolor`→`error`/`dim`/`hidden` (pure class swaps, no mark drawn). That single hard
MISSING gesture is why the strike verb carries the most teaching value in this set.

---

## 5. Summary (for synthesis)

**Chosen design:** a four-verb DECORATE set unified by one philosophy — inline-styled overlay
decorations riding the shipped `annotation_add`/`annotation_remove`/`annotation_recolor` contract
(plus the shipped `.scriba-defocused` overlay for board-spotlight). **Rationale (1 paragraph):**
each gesture is an *overlay* that must coexist with the element's identity and state, which is the
definition of an A-3 decoration, not a state; modeling them as decorations lets every one reuse the
existing motion kinds and the existing `scriba-annotation-*` / `.scriba-defocused` CSS, so the whole
set ships as additive Python with **no new motion kind and no shared-CSS change**, i.e. **no
`SCRIBA_VERSION` bump** and byte-identical output for non-users — the best-case the scriba DNA asks
for, while filling the one hard MISSING gesture (strike-but-keep) and three awkward ones.

- **Syntax:** `\annotate{x}{strike=true}` · `\note{id}{text=…, at=<compass>}` ·
  `\focus{x}{scope=board}` · `\trace{Graph|Tree}{cells=[node-seq]}`.
- **Cost:** strike **S** · note **M** · board-spotlight **S** · graph-trace **S–M**.
- **Risk:** strike LOW · note LOW-MED · board-spotlight LOW · graph-trace MED.
- **strike-as-state-or-decoration:** **DECORATION** (an `\annotate` flag), decisively — state is
  single-valued and would erase the role color, and it would force new shared CSS + a bump; the
  decoration is orthogonal, cheaper, and broader.
- **new motion kind?** **NO** (all four ride existing kinds; board-spotlight isn't a motion kind).
- **`SCRIBA_VERSION` bump?** **NO** (zero shared CSS, zero `scriba.js`/schema change).
- **New E-codes:** E1119 (strike no-extent, soft) · E1120/E1121 (note id/text, note anchor) ·
  E1122 (focus scope). All in the free E11xx band (highest in-use is E1118).
- **Value/cost self-score: 5/5** — fills the single hard MISSING gap plus three awkward gaps, all
  high-frequency CP-teaching moves, for 2×S + 1×(S–M) + 1×M, no bump, no new kinds.

**Probes (session scratchpad):** `trace_ok.tex` (captured the inline decoration structure to mimic),
`strike_state.tex` → E1109, `trace_graph.tex` → E1118, `untether.tex` → E1010.

**Status: Design complete.**
