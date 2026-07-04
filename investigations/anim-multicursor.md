# anim-multicursor — named multi-cursor carets that slide and bind to watch vars

> Investigation case file. Feature request: animation-clarity Tier 2 ③ — multiple
> named cursors that **slide** between steps and **bind** their cell index to a
> `VariableWatch` variable. Research only; no repo source was modified.
> Repo `main` @ `5925bb1` (0.22.2). Grades: **Confirmed** (read code / rendered
> and observed), **Deduced** (follows necessarily from confirmed facts),
> **Hypothesized** (design proposal, not yet proven).

---

## Hand-off Brief (3 sentences)

Today `\cursor{targets}{index}` is a **recolor-hop**: it finds the cell currently in
`curr_state`, demotes it to `prev_state`, and promotes `target[index]` to `curr_state`
(`scene.py:905` `_apply_cursor`) — there is **no glyph and no motion**, and it churns
`shape_states` so it rides the ordinary `recolor` differ. The proposed feature is a
*different animal*: a named `▲` caret glyph, emitted through the **decoration spine**
(the same `data-annotation` structure contract that `\trace` R-37 and annotations use,
`base.py:516` `emit_traces_under`), whose cell index is re-resolved every frame from a
bound `VariableWatch` value and which **slides** from its old cell to its new cell.
The one hard finding that shapes the whole design: the shipped `position_move` handler
**cannot** produce that slide (it ends every tween at the element's *old* position and
relies on a full-SVG snap to reach the new one), so a clean caret slide needs **one small,
isolated JS handler (~9 lines)** — everything else reuses existing spine machinery with
zero new runtime surface.

---

## Proposed surface (JudgeZone)

```latex
\cursor{arr}{id=i, at="w.var[i]", color="state:current"}
```

- multiple **named** carets coexist (`id=i`, `id=j`, …), update-in-place by id;
- `at=` binds the cell index — `at="w.var[i]"` reads `VariableWatch` var `i` each frame and
  places the caret at `arr[value]`; `at=3` is a literal;
- `color="state:current"` paints the caret via the R-36 state-color binding;
- differ emits a **slide** when a named caret's cell changes between steps; the `▲` sits in a
  band just under the cell it points at.

---

## 1 — The current `\cursor` machine  *(Confirmed)*

### 1.1 Grammar / parse — `parser/_grammar_commands.py:338` `_parse_cursor`
Two brace args. Arg 1 = comma list of accessor prefixes → `targets: tuple[str,...]`
(`:352`). Arg 2 = `index` first (int, else kept as interp string e.g. `${i}`, `:378-382`),
then optional `prev_state=` / `curr_state=` keys validated against `VALID_STATES`
(`:387-412`, invalid → **E1182**). Empty target → **E1180** (`:344`); empty index →
**E1181** (`:363`). Registered in the dispatcher at `grammar.py:306`; also reachable inside
`\foreach` (`_grammar_foreach.py:178`) and `\substory` (`_grammar_substory.py:317`).

### 1.2 AST — `parser/ast.py:273` `CursorCommand`
`@dataclass(frozen=True, slots=True)` with `targets: tuple[str,...]`, `index: int|str`,
`prev_state="dim"`, `curr_state="current"`, `line`, `col`. Member of the `MutationCommand`
union (`:294-303`) and `Command` union (`:306-320`).

### 1.3 Semantics — `scene.py:905` `_apply_cursor`
For each `target_prefix`: (a) scan `shape_states[shape]` for the key already in `curr_state`,
`replace(state=prev_state)` it (`:918-922`); (b) `new_key = f"{prefix}[{index}]"`,
`_ensure_target` (raises **E1116** if the shape was never `\shape`-declared, `:930`), set it
to `curr_state` (`:924-928`). Dispatched from `_apply_command` at `scene.py:605`. **No SVG,
no geometry, no glyph** — it only rewrites cell *states*, so the frame differ picks it up as
ordinary `recolor` transitions. This is why the recolor "hops" between cells.

### 1.4 Backward-compat surface — **large**  *(Confirmed)*
`\cursor` appears **232×** across `examples/`, `tests/`, `docs/`. Golden-pinned corpuses
that exercise it include `kmp` (27), `elevator_rides` (16), `linkedlist_reverse` (10),
`range_queries_copies` (6), `frog` (5), `dptable` (5), `test_reference_advanced` (5). **Any
behavior change to the existing form re-pins a wide golden set** → the new form MUST be
strictly additive and opt-in.

**Compat rule (Hypothesized, low-risk):** discriminate by the `id=` key. Legacy arg 2 always
leads with a *bare* index token (`3` or `${i}`); the new form leads with `id=…` and never a
bare index. Parse rule: *if any `key=val` part in arg 2 has key `id`, route to the new caret
path; else legacy.* `id` is a free key (legacy only knows `prev_state`/`curr_state`), so this
is unambiguous and leaves every existing `\cursor` byte-identical. Keep one AST node — extend
`CursorCommand` with three optional fields (`cursor_id: str|None=None`, `at: str|None=None`,
`color: str|None=None`); defaults `None` mean legacy construction is unchanged and the union
memberships stay put. `_apply_cursor` branches on `cmd.cursor_id is not None`.

---

## 2 — `position_move` today, and why the caret can't reuse it  *(Confirmed — load-bearing)*

### 2.1 What emits it — `differ.py:218-236`
Inside `_diff_shape_states`, when a target exists in both frames and its `(x,y)` differ, it
emits `Transition(target, "position", "px,py", "cx,cy", "position_move")`. Populated **only**
for Tree nodes today, via `emitter.py:198` `_inject_tree_positions`, which — **after** the
SVG is emitted — copies `prim.get_node_positions()` (`tree.py:507`, keys are the node
`data-target`) into `frame.shape_states`. Call site: `_html_stitcher.py:481-482`, immediately
after `_emit_frame_svg`. Wire format verified by rendering `examples/algorithms/tree/splay.tex`:
`["T.node[2]","position","88,190","322,150","position_move"]` (`from`=prev, `to`=curr).

### 2.2 What the JS does — `static/scriba.js:185-197`
```js
}else if(kind==='position_move'){
  var el9=stage.querySelector(sel);            // sel = [data-target="…"]  (:121)
  var pf=fromVal.split(','), pt=toVal.split(',');
  var dx=parseFloat(pf[0])-parseFloat(pt[0]);  // prevX - currX
  var dy=parseFloat(pf[1])-parseFloat(pt[1]);
  var a9=el9.animate([{transform:'translate('+dx+'px,'+dy+'px)'},
                      {transform:'translate(0,0)'}],
                     {duration:_dur(DUR),easing:'ease-out',fill:'forwards'});
```

### 2.3 The defect that blocks reuse
The stage `innerHTML` is swapped in **only two** places: `snapToFrame` (`:102`) and
`_finish` (`:302`), and `_finish` runs **after** all phase-2 tweens resolve. So during the
tween the stage still shows the **old** frame, and `[data-target]` selects the **old**
element. A tree node `<g>` carries **no transform** — its position lives in absolute child
coords (`tree.py:749-758`, `<circle cx cy>`), so the group's natural position is `prevX`.
The keyframes therefore render (for `T.node[2]`, prev `(88,190)`→curr `(322,150)`):

- start `translate(88-322,190-150)=translate(-234,40)` → visual `(-146, 230)`
- end `translate(0,0)` → visual `(88, 190)`  ← **the OLD cell**
- then `_finish` (fs=1) snaps innerHTML → `(322,150)`.

i.e. the node lurches backward, slides to its **old** seat, then **jumps** to the new one.
Because the end keyframe is *always* `translate(0,0)` = the old natural position, **no choice
of `from`/`to` can make the existing handler land on the new position.** Tolerable for tiny
tree reparents (latent, shipped); unacceptable for a caret, which is the visual focus and can
travel many cells. `fs=1` is guaranteed for caret frames anyway — `_html_stitcher.py:586`
sets it whenever the SVG bytes change, and a moved caret changes them.

### 2.4 Conclusion → **one small new handler is required** *(Confirmed the need; handler is Hypothesized)*
The brief's hoped-for "no new JS" does **not** hold. The minimal fix is an isolated
`cursor_move` kind that animates the **old** caret *forward by the delta and holds it*, so the
subsequent `fs` snap is seamless:

```js
}else if(kind==='cursor_move'){
  var elc=stage.querySelector('[data-annotation="'+_cssEscape(target)+'"]');
  if(elc){
    var cf=fromVal.split(','), ct=toVal.split(',');
    var cdx=parseFloat(ct[0])-parseFloat(cf[0]);   // currX - prevX  (forward)
    var cdy=parseFloat(ct[1])-parseFloat(cf[1]);
    var ac=elc.animate([{transform:'translate(0,0)'},
                        {transform:'translate('+cdx+'px,'+cdy+'px)'}],
                       {duration:_dur(DUR),easing:'cubic-bezier(0.16,1,0.3,1)',fill:'forwards'});
    _anims.push(ac); pending.push(ac.finished);
  }
}
```
Old caret is at `prevX` in the shown old frame; it eases to `prevX+(currX-prevX)=currX` and
holds; `_finish` swaps to the new SVG where the caret is already at `currX` → no jump. It
selects by `data-annotation` (the caret's spine key), so the caret needs **no** `data-target`.
Risk: **nil** — a brand-new `kind` that only carets emit; every existing transition path is
untouched. (Do **not** "fix" `position_move` globally here — that re-pins tree/graph goldens
and is out of scope for an opt-in feature. Note it as separate future work.)

---

## 3 — Binding `at=` and the resolve policy  *(Deduced / Hypothesized)*

### 3.1 Where the value lives  *(Confirmed)*
`VariableWatch` stores values as **strings** in `self._values: dict[str,str]`
(`variablewatch.py:103`), mutated by `\apply` (`:137-160`). The scene mirrors every target's
value into `ShapeTargetState.value` (`scene.py:112`), snapshotted into `FrameSnapshot`
(`scene.py:266`) and serialized to `frame.shape_states[shape][key]["value"]`
(`renderer.py:289-290`). So after a step's commands apply, `shape_states["w"]["w.var[i]"]
["value"]` holds the caret's bound string (`"3"`, `"----"`, or `"$\max(0,i)$"`).

### 3.2 Two-phase resolve (mirrors `_inject_tree_positions`)  *(Hypothesized)*
The caret needs *both* an integer index (known at build) *and* a pixel `(x,y)` (known only
after the target primitive realizes its dynamic pitch). Split the resolve exactly like trees:

- **Build phase** — in `_snapshot_to_frame_data` (`renderer.py:266`), for each `CursorEntry`
  produce `{"target": shape, "id": cid, "index": <resolved int>, "color": color,
  "label": cid}`. Resolve the index:
  - `at=<int>` → that int.
  - `at="shape.var[name]"` → parse `int(shape_states[shape][f"{shape}.var[name]"]["value"])`.
  - unparseable (`"----"`, `"$…$"`, missing) → **soft-drop this caret for this frame** and
    `_emit_warning(ctx, "E1184", …, severity="info")`. Soft, not fatal (matches selector
    semantics: an out-of-range selector degrades quietly at emit).
- **Inject phase** — add `_inject_cursor_positions(frame, primitives)` right beside
  `_inject_tree_positions` at `_html_stitcher.py:482` (after `_emit_frame_svg`). For each
  `frame.cursors` entry ask the target primitive for the cell center of `index`
  (`resolve_annotation_point(f"{shape}.cell[{index}]")`, then apply the band offset from §4)
  and write `x,y` into the entry dict. Out-of-range index → drop the entry. Because
  `frame.cursors` is a plain list of mutable dicts, this in-place write is legal even though
  `FrameData` is `frozen+slots` (same trick `_inject_tree_positions` uses on `shape_states`).

Re-resolving every frame is what makes the caret *move*: step N reads `i=2`→`arr[2]`, step
N+1 reads `i=5`→`arr[5]`, and §5's differ turns the `(x,y)` delta into a `cursor_move`.

### 3.3 `at=` value grammar (minimal v1)  *(Hypothesized)*
`at=INT` | `at="shape.var[name]"`. The quoted form is mandatory for the binding because the
value lexer splits on bare `:`/`[` (same reason R-36 requires quoted `color="state:X"`,
`constants.py:39-41`). Reject any other shape (`at="arr.cell[…]"`, arithmetic) at parse with
**E1183** in v1; leave `${expr}` / arithmetic for a later revision. `\foreach` interpolation
is **free**: `_sub_cmd` substitutes `${var}` generically across *all* dataclass fields
(`scene.py:576-587`), so `id`, `at`, `color` strings get `${i}` expansion with no extra code.

---

## 4 — Glyph and per-primitive geometry  *(Confirmed for Array; Deduced elsewhere)*

### 4.1 The glyph and its spine group  *(Hypothesized, modeled on R-37)*
Emit, on the **target** primitive (the caret decorates *its* cells, so it lives in that
shape's SVG — exactly like `\trace`), one group carrying the **annotation structure
contract**:

```
<g class="scriba-annotation scriba-annotation-{annotation_color_class(color)}"
   data-annotation="{shape}.cursor[{id}]-solo"
   role="graphics-symbol" aria-roledescription="cursor" aria-label="{id}">
   <polygon points="…▲…" fill="{stroke}"/>          <!-- caret pointer -->
   <text …>{id}</text>                               <!-- small id label 'i'/'j' -->
</g>
```
Key = `{shape}.cursor[{id}]-solo` — a fresh infix (`cursor` vs `trace`/annotations), so it can
**never** collide with a trace or annotation key on the same shape. `annotation_color_class`
(`_svg_helpers.py:1391`) already maps `state:current` etc. (R-36), so `color=` reuses it with
zero new color code. The label text **is** the cursor id (`i`, `j`) — that is the "small
label beside the caret" the mockup calls for. Because the group is the annotation contract,
the shipped `annotation_add`/`annotation_remove` handlers fade it in/out for free
(`scriba.js:205-273`; the polygon has no `<path>`, so it takes the plain-opacity `else`
branch at `:267-272`), and the static/print/reduced-motion fallbacks are inherited (the glyph
is just present in the static SVG at its resolved seat).

### 4.2 Band placement  *(Confirmed geometry for Array)*
Convention for pointer carets (two-pointer, KMP `i`/`j`) is a `▲` **below** the row pointing
**up** at the cell, id label beneath. Array cell geometry (`_types.py`: `CELL_WIDTH=60`,
`CELL_HEIGHT=40`, `CELL_GAP=2`): `resolve_annotation_point("arr.cell[i]")` returns
`(cx, 0)` = cell **top** (`array.py:389-403`, `_cell_center`), `cx` already tracks the
dynamic `_cell_width` and caption shift `_row_dx`. Place the caret apex at `(cx, CELL_HEIGHT +
gap)` (≈ y 46) and the id text just below. Horizontal x = `cx` (Confirmed dynamic-pitch-aware
because `_cell_center` divides by the live `_cell_width`, the 0.22.1 dynamic pitch).

### 4.3 Vertical reservation
A caret below the cells extends the content box downward; the below-cells reservation already
exists as `resolve_below_baseline()` (`array.py:520`, `base.py:712`) feeding the layout/extent
(`base.py:1138`). v1 either (a) route the caret band through the existing below-baseline
reservation, or (b) add a `set_min_cursor_below` floor mirroring `set_min_arrow_above`
(`base.py:597`) so the translate offset stays stable across frames that gain/lose a caret
(the R-32 stable-layout discipline). **(b) is the safer mirror** — annotations already solved
exactly this "reserve a constant band so frames don't jump" problem above the cells.

### 4.4 Per-primitive scope for v1  *(Deduced)*
Every cell-addressable 1-D primitive already exposes `resolve_annotation_point` for
`cell[i]`, so the caret geometry generalizes for free to **Array, DPTable-1D, Stack, Queue,
NumberLine (tick center — note NumberLine overrides the trace anchor for the same reason,
`base.py:502-508`)**. Two-pointer/sliding-window — the actual motivating cases — are 1-D.
**Recommend v1 = 1-D cell/tick primitives only.** 2-D (`Grid`, `DPTable-2D`) needs a
`▲`-vs-corner-marker decision and a 2-axis band; **defer to v2** (Hypothesized).

---

## 5 — Persistence, frames, and the differ  *(Deduced, mirrors trace spine)*

### 5.1 Scene state — `CursorEntry` (mirror `TraceEntry` at `scene.py:132`)
```python
@dataclass(frozen=True)
class CursorEntry:
    target: str          # shape name
    cursor_id: str       # 'i', 'j'
    at: str              # 'w.var[i]' or literal '3'
    color: str = "info"
    ephemeral: bool = False
```
`SceneState.cursors: list[CursorEntry]` (like `traces`, `scene.py:182`). New-form
`_apply_cursor` branch = **update-in-place by (target, cursor_id)**: first `\cursor{arr}{id=i…}`
appends; a later one with the same id **replaces** the entry (that is a *move*, realized as a
new resolved index next frame). `FrameSnapshot.cursors: tuple[CursorEntry,...]` added beside
`traces` (`scene.py:159`); `snapshot()` copies it. Ephemeral carets clear next step exactly
like ephemeral traces/annotations.

### 5.2 Frame data + wiring
- `FrameData` (`emitter.py:106`, frozen+slots, fields today end at `substories`): add
  `cursors: list[dict] | None = None` beside `traces`.
- `_snapshot_to_frame_data` (`renderer.py:324`): build `cursors` dicts (index resolved per
  §3.2 build phase) exactly parallel to the `traces` comprehension.
- `_frame_renderer.py:277-283` (and the reserved-offset twin at `:659-665`): add
  `prim.set_cursors(prim_cursors)` guarded by `hasattr`, mirroring `set_traces`
  (`base.py:498`). The primitive's `emit_cursors_under(parts)` mirrors `emit_traces_under`
  (`base.py:516`) and records the `(x,y)` it drew at so `get_cursor_positions()` can feed §3.2
  inject phase (mirror of `tree.get_node_positions`).

### 5.3 `_diff_cursors` (mirror `_diff_traces` at `differ.py:246`)
```python
def _key(c): return f"{c['target']}.cursor[{c['id']}]-solo"
# same id in both, (x,y) differ  -> Transition(key,"position","px,py","cx,cy","cursor_move")
# id only in curr                -> Transition(key,"add",   None, color, "annotation_add")
# id only in prev                -> Transition(key,"remove",color,None, "annotation_remove")
```
Wire the call into `compute_transitions` (`differ.py:355-366`) after `_diff_traces`, reading
`getattr(prev,"cursors",None) or []`. Appear/disappear reuse the annotation fade verbatim;
move uses the new §2.4 `cursor_move`. Note the caret adds **no** `shape_states` churn (it is a
glyph, not a recolor) so it never contaminates cell diffs — the exact opposite of legacy
`\cursor`.

---

## 6 — Interactions  *(Deduced)*

- **cursor + trace same frame** — different key infix (`.cursor[…]` vs `.trace[…]`) → no
  collision; both are annotation-contract groups, z-ordered together under pills/arrows.
- **caret on a `hidden` cell** — the cell body is skipped by emit (state `hidden`,
  `constants.py:29-31`) but the *slot geometry* still resolves (`_cell_center` is purely
  index math). v1 policy (Hypothesized): **still draw the caret** — it legitimately marks a
  position even when the cell is hidden; document it, add an Open Question if reviewers prefer
  a soft-drop.
- **watch var mutated by `\apply` in the same step** — frame snapshot is taken **after all**
  the step's commands apply (`scene.py:224` `apply_frame` → `snapshot`), and the build-phase
  resolve reads that post-command snapshot, so the caret always sees the settled value. Order
  within the step is irrelevant. *(Confirmed by the apply→snapshot ordering.)*
- **`\foreach` spawning carets** — free via generic field interpolation (`scene.py:576-587`);
  `\foreach{k}{[0,1]}\cursor{arr}{id=${k}, at="w.var[${k}]"}\endforeach` expands to two named
  carets.
- **reduced-motion / print** — caret is in the static SVG at its seat; no motion, correct
  position. Inherited from the spine, no extra work.

---

## 7 — Test + patch plan, impact, R-card, refs, E-codes

### 7.1 RED-first tests (write first, watch fail)
| Test (new) | Asserts |
|---|---|
| `tests/unit/test_cursor_pin.py::test_new_form_parses_id_at_color` | `id=`/`at=`/`color=` populate the new optional fields; legacy `\cursor{a}{3}` still parses to `index=3`, new fields `None`. |
| `…::test_legacy_cursor_unchanged` | rendering a legacy `\cursor` corpus snippet is byte-identical (guards the 232-token surface). |
| `…::test_glyph_structure` | emitted `<g data-annotation="arr.cursor[i]-solo">` with `<polygon>` + id `<text>`, class `scriba-annotation-…`. |
| `…::test_bind_reads_watch_value` | `at="w.var[i]"` with `w.var[i]=2` seats the caret at `arr[2]` center (dynamic `_cell_width`). |
| `…::test_move_emits_cursor_move` | var 2→5 across steps → one `["arr.cursor[i]-solo","position","x2,y","x5,y","cursor_move"]`. |
| `…::test_appear_disappear_uses_annotation_addremove` | first appearance → `annotation_add`; ephemeral clear → `annotation_remove`. |
| `…::test_unparseable_binding_soft_drops` | `at="w.var[i]"` with value `"----"` → no caret, one E1184 info warning, no exception. |
| `tests/integration/test_animation_transitions.py` (extend) | golden manifest for a two-pointer array with `i`,`j` carets. |

### 7.2 Patch plan (files → change)
1. `parser/_grammar_commands.py:338` — branch `_parse_cursor` on `id=` key; parse `at`/`color`;
   new-form errors **E1183** (bad `at=`), reuse E1180/E1181.
2. `parser/ast.py:273` — add `cursor_id`/`at`/`color: str|None=None` to `CursorCommand`.
3. `scene.py` — `CursorEntry` dataclass; `SceneState.cursors`; `FrameSnapshot.cursors`;
   `_apply_cursor` branch (update-in-place by id) + build-phase resolver helper; E1184 soft
   warn via `_emit_warning(ctx,…,severity="info")` (`core/warnings.py`).
4. `emitter.py:106` — `FrameData.cursors`; `emitter.py:198`-style `_inject_cursor_positions`.
5. `renderer.py:266` — build `cursors` dicts in `_snapshot_to_frame_data`.
6. `_html_stitcher.py:482` — call `_inject_cursor_positions(frame, primitives)`.
7. `_frame_renderer.py:277,659` — `prim.set_cursors(...)` guarded by `hasattr`.
8. `primitives/base.py` — `set_cursors`, `emit_cursors_under`, `get_cursor_positions`,
   optional `set_min_cursor_below`; call `emit_cursors_under` in 1-D `emit_svg`s
   (`array.py:342` is the trace call-site template).
9. `differ.py:355` — `_diff_cursors` + wire into `compute_transitions`.
10. `static/scriba.js:197` — add the ~9-line `cursor_move` handler (§2.4). **Only JS change.**

### 7.3 Golden impact
Opt-in ⇒ **zero churn** on the 232 legacy `\cursor` tokens (byte-identical, guarded by
`test_legacy_cursor_unchanged`). New goldens only for new-form examples. The `cursor_move`
kind is inert for every existing animation (no caret ⇒ never emitted).

### 7.4 R-card draft — **R-38** (next free; body R-35/36/37 exist, table stops at R-34)
> **R-38 — `\cursor{…}{id=,at=,color=}`: named binding caret that slides.**
> **Normative:** SHOULD **Since:** vX.Y.Z
> New-form `\cursor` (discriminated by the `id=` key; legacy `{targets}{index}` untouched)
> emits a `▲` caret inside `<g data-annotation="{shape}.cursor[{id}]-solo">`, carrying the
> annotation structure contract so `annotation_add`/`annotation_remove` fade it for free.
> `at=` re-resolves the cell index every frame (`at=INT` | `at="shape.var[name]"`, quoted);
> an unparseable/out-of-range binding soft-drops the caret with E1184. A named caret whose
> resolved cell changes between steps emits a **`cursor_move`** transition — the one new
> runtime handler — sliding old→new; `position_move` is deliberately **not** reused (it ends
> at the old seat, §2.3). Persistent by default; `ephemeral=true` clears next step. v1 scope:
> 1-D cell/tick primitives.
> **Code ref:** `differ.py` `_diff_cursors`; `base.py` `emit_cursors_under`;
> `scene.py` `_apply_cursor` (new branch), `CursorEntry`; `static/scriba.js` `cursor_move`.
> **Test ref:** `tests/unit/test_cursor_pin.py`.

Also add the R-38 summary row to the table at `smart-label-ruleset.md:1182` and register it in
`scripts/check_ruleset_sync.py` (the doc-coverage gate).

### 7.5 REFERENCE section draft (`docs/SCRIBA-TEX-REFERENCE.md`)
New sub-section under the animation commands: legacy vs binding forms, the `at=` grammar,
`color="state:X"`, the slide behavior, the 1-D scope note, and a KMP two-pointer example with
`id=i`/`id=j`.

### 7.6 E-codes  *(Confirmed free)*
Cursor band `E1180-E1199` (`constants.py:9`): **E1183, E1184, E1185 FREE**. Use **E1183** =
malformed new-form (`at=` shape rejected / bad key), **E1184** = unresolvable/out-of-range
binding (**soft**, `severity="info"`). E1180/1181/1182 already taken (`errors.py:227-235`).
Trace band note for the brief's question: E1491/E1492 are trace's (`_grammar_commands.py:234,256`);
**E1493, E1494 are free** — but the caret belongs in the cursor band, so use E1183/E1184.

---

## Open questions (≤5)

1. **`cursor_move` vs fixing `position_move`.** Recommend the isolated new handler (zero
   regression) over repairing `position_move` globally (fixes trees too but re-pins tree/graph
   goldens). Confirm the scope boundary.
2. **Caret on a `hidden` cell** — draw anyway (proposed) or soft-drop? Affects two-pointer
   over partially-hidden rows.
3. **Band reservation** — reuse `resolve_below_baseline` or add a dedicated
   `set_min_cursor_below` floor (proposed, matches the R-32 stable-layout discipline above the
   cells)?
4. **`at=` breadth for v1** — lock to `INT | "shape.var[name]"` (proposed), or also accept
   `at="arr.cell[k]"` / `${expr}` now? Wider surface = more parse/resolve tests.
5. **2-D primitives** — defer Grid/DPTable-2D carets to v2 (proposed), since two-pointer is
   1-D; confirm no immediate 2-D caller.
