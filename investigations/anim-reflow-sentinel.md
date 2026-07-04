# Ordered-structure insert / reflow (grow, not just shrink) + sentinel slots — request item ⑦

> Design synthesis. **No repo source modified.** Repo @ `main` (scriba 0.22.2,
> `SCRIBA_VERSION = 15`, `scriba/_version.py:6`). Deep-dive for animation-clarity
> item ⑦ under the **A-rules** (`investigations/anim-unified-motion-model.md`,
> A-6) and **R-32** frame stability (`docs/spec/ruleset.md:907-958`). Companion to
> `investigations/fixedbox-content-sizing.md` (the monotonic-`_cell_width` prescan
> pattern this file generalises from *width* to *count*).
>
> Evidence grades: **[Confirmed]** = read in source or executed this session (probes
> `scratchpad/rf_probe.py`, `rf_hidden.py`, run against `.venv`) · **[Deduced]** =
> logical consequence of confirmed facts · **[Hypothesized]** = design proposal, not
> yet built. All paths absolute; line numbers at HEAD `9906652`.

---

## Hand-off Brief (3 sentences)

The repo already ships **both** reflow models this feature needs — **Tree** does
*element-identity* reflow (every `add_node`/`remove_node` calls `_relayout()`,
recomputing all node positions keyed by a stable `node_id`, and the differ emits
`position_move`, `tree.py:275-320`, `emitter.py:201-228`, `differ.py:218-236`) and
**Queue** does *slot-identity* reflow (a fixed `capacity` grid where `enqueue`/`dequeue`
only fill slots and move a pointer, cell position is always `pad + i·pitch`, bbox width
is frame-invariant, `queue.py:155-205,240`) — so item ⑦ is not new motion machinery but
a choice between two shipped patterns plus a sentinel affordance. The load-bearing
constraint is **R-32 centering**: `_frame_renderer.py:746` centers every primitive on
its *per-frame live* bbox width (`x_offset = (vb_width - bw) // 2`), so any primitive
whose `bounding_box().width` shrinks when it loses an element **jumps horizontally** —
this session executed that exact failure on **LinkedList**, whose `insert`/`remove`
already ship but vary bbox width 544→434→544 px and slide values 110 px with no
`position_move` (`linkedlist.py:141-170,229-246`; probe `rf_probe.py`), and which is
conspicuously **absent from R-32's applies-to list** (`ruleset.md:915-917`). The
recommendation is **slot-identity on a fixed max-N grid (the Queue model) for v1** —
insert/remove become a `value_change` cascade inside a reserved envelope so cell
positions never move and R-32 holds by construction, index-based selectors stay intact,
and *zero* new motion vocabulary or JS is required — with element-identity `position_move`
"slide" deferred to v1.1 as an opt-in cosmetic and client-side FLIP **rejected** (it needs
real per-item identity anyway and reintroduces the parallel client-motion path A-1/A-2 close).

---

## 1. Current-state map — what "shrink" and "grow" do today, per primitive

Two independent facts decide a primitive's shrink/grow behaviour: (a) does its
`emit_svg` loop **skip** elements in the `hidden` state, and (b) does it implement a
structural `apply_command` (insert/remove/push/pop)? `base.apply_command` is a **no-op
by default** (`base.py:1287-1294`) — only four primitives override it.

| Primitive | `hidden` in emit | Structural `apply_command` | Position model | bbox width frame-stable? | Reflow today |
|---|---|---|---|---|---|
| **Array** | **not skipped** (renders normally) | **none** (base no-op) | `i·(cw+gap)` fixed slots, `array.py:275` | **yes** — `size·cw` fixed, `array.py:363-393` | **none at all** |
| **DPTable / Grid** | not skipped | none | fixed grid | yes | none |
| **Queue** | not skipped | `enqueue`/`dequeue`, `queue.py:155-205` | `pad + i·pitch` fixed, `queue.py:240` | **yes** — `capacity` fixed | slot-identity (pointer moves, slots fill/clear) |
| **Stack** | not skipped | `push`/`pop`, `stack.py:148` | fixed slots | yes (fixed height reserve) | slot-identity |
| **LinkedList** | not skipped | **`insert`/`remove`**, `linkedlist.py:141-170` | `pad + i·pitch`, `linkedlist.py:217` | **NO** — `len(values)·nw`, `:229-246` | slot-identity **but width varies → jumps** |
| **Tree** | skipped (`graph.py` sibling pattern) | `add_node`/`remove_node`/`reparent`, `tree.py:232-271` | Reingold-Tilford, recomputed `_relayout()` | height stable; positions move | **element-identity** (`position_move`) |
| **Graph** | **skipped**, `graph.py:1435,1688` | `add_edge`/`remove_edge`/`set_weight` | fixed layout | yes | skip-hidden (no linear reflow) |
| **Plane2D** | **skipped**, `plane2d.py:834-1031` | tombstone remove, `plane2d.py:407-424` | coordinate positions | yes | skip-hidden |

### 1a. Array's `hidden` is a visual no-op — there is no interior "hole" mechanism to fix; there is *no shrink at all* [Confirmed, probe `rf_hidden.py`]

`VALID_STATES` includes `hidden` with the comment "primitive emit_svg loops skip elements
in this state" (`constants.py:29-31`), **but that is only true for Graph and Plane2D**.
Array's emit loop (`array.py:259-302`) has no `if state == "hidden": continue`, and there
is **no `scriba-state-hidden` CSS rule** (the styled states are exactly
idle/current/done/dim/error/good/highlight/path, `scriba-scene-primitives.css:122-148`).
Probe: `\recolor{a.cell[2]}{hidden}` on a 5-cell Array still emits **5 rects** and the
literal value `3` — the cell renders identically to idle. So the brief's premise ("delete
via hidden exists, but leaves a hole") is **imprecise for Array**: Array cannot hide or
remove a cell by any means today. The "predecessor looks two cells away" pathology is the
general risk of *any* linear structure that vacates an interior slot — it is realisable on
the **skip** primitives (Graph/Plane2D hiding an interior element leaves a genuine gap) and
would appear on Array the moment a skip-or-blank interior removal is added **without**
reflow. The fix (§2) makes interior removal reflow so the gap never exists.

### 1b. Queue is the R-32-correct slot model; LinkedList is the latent R-32 bug [Confirmed, probe `rf_probe.py`]

- **Queue** always draws `capacity` slots; `enqueue` writes `cells[rear]` and advances the
  rear pointer, `dequeue` clears `cells[front]` and advances front (`queue.py:173-191`).
  Cell `i` is always at `pad + i·pitch` (`:240`); `bounding_box` reserves `capacity`
  (`:317`) → **width is frame-invariant** → `_frame_renderer.py:746` centers it identically
  every frame → **no jump**. No `position_move` is ever emitted for queue cells; the whole
  animation is `value_change` + pointer recolor. This is strategy (a) done correctly.
- **LinkedList** draws `len(values)` nodes and `bounding_box` width `= len·node_width`
  (`:229-246`). Probe: `remove(2)` on `[10,20,30,40,50]` drops width **544 → 434** and the
  value `40` moves from slot-3 anchor `x=382` to slot-2 anchor `x=272`. Because
  `_frame_renderer.py:746` re-centers on the *smaller* bbox, the entire list also shifts
  right ~55 px — **every node jumps**, and there is no `get_node_positions` so the differ
  emits **no `position_move`** (the jump is instantaneous). LinkedList is **not in R-32's
  applies-to list** (`ruleset.md:915-917`) — a pre-existing gap, not a regression this
  feature introduces, but the exact hazard ⑦ must avoid.

**Takeaway:** the correct reflow envelope is *fixed max-N, always reserved* (Queue), not
*live-N* (LinkedList). The `_frame_renderer.py:746` centering line is the single reason
frame-invariant bbox width is mandatory.

---

## 2. Two strategies + FLIP — comparison and verdict

The insert/remove semantics are identical at the data level (`insert(k,v)`: elements
`k..N-1` shift up; `remove(k)`: elements `k+1..N-1` shift down). They differ in **what
carries identity across the shift**.

### Strategy (a) — Slot-identity (the Queue model) [recommended for v1]

`data-target = shape.cell[i]` is the **slot at position i**. Positions are fixed
(`i·pitch`) on a grid of `max-N` physical slots (always reserved). A logical `live`
count says how many slots are populated. `insert(k,v)`/`remove(k)` are **macros over
`value_change`**: the values cascade through fixed slots, `live` adjusts, and cells at
`i ≥ live` render empty (or hidden-skipped tail).

- **R-32:** trivially satisfied — `bounding_box().width = max_N·cw` is constant, so
  `_frame_renderer.py:746` centering is identical every frame. **No jump.** [Deduced from
  `array.py:363-393` + `:746`]
- **Motion vocabulary:** only `value_change` (+ `recolor` for state, `element_add/remove`
  for the live/dead boundary). **Zero new kinds, zero JS.** Reuses the shipped
  `value_change` handler (`scriba.js:136-139`). [Confirmed kinds closed, A-2]
- **Selectors:** `cell[i]` keeps meaning "position i" — annotations, `\recolor`, `\ref`,
  smart-label all keep working unchanged. Semantics: an annotation on `cell[2]` tracks
  *the position*, not *the value that was there* (documented, §7 risk R4). [Deduced]
- **Tween quality:** the shift reads as "values flow one slot over" via text morph, not a
  spatial glide. For the ~5 target problems (small N) this is clear; for large N it is
  `N−k` simultaneous text tweens ("differ noise", §7 risk R2). [Deduced]
- **Cost:** low. One `apply_command` on Array mirroring `queue.py:155-205`; a `live`
  count; relax `E1402` to allow `len(data) < size` (`array.py:147`). No grammar, renderer,
  differ, or JS change.

### Strategy (b) — Element-identity (the Tree model) [defer to v1.1, opt-in]

Each element carries a **stable item-id**; `data-target` (or a parallel key) follows the
*value*, not the slot. On insert/remove, positions recompute and the primitive publishes
per-item `(x,y)` (mirroring `_inject_tree_positions`, `emitter.py:201-228`); the differ
emits `position_move` (`differ.py:218-236`) and the **shipped** `scriba.js:206-215`
handler slides them.

- **R-32:** holds *if* the reserved envelope is max-N (same requirement as (a)); the slide
  is a cosmetic `transform`, `fs`-snapped to server truth at settle (A-6). [Deduced]
- **Motion vocabulary:** `position_move` + `element_add/remove` — all shipped, **zero JS**.
  The slide is the clearer motion (elements visibly move over). [Confirmed handler ships]
- **Selectors — the blocker:** `cell[i]` today is index-based. True element-identity means
  addressing by item-id, so every index-based selector (`\annotate{a.cell[2]}`,
  `\recolor{a.range[1:3]}`, smart-label pins) changes meaning or breaks. Re-keying
  `data-target` from slot to item is a **large blast radius** across the decoration/selector
  algebra. [Deduced from `array.py:395-482` index-keyed anchors]
- **Cost:** high. New addressing model + position injection + selector-algebra migration.

### FLIP (First-Last-Invert-Play, client-side) — rejected [Deduced]

The brief asks whether FLIP on `data-target` after the `innerHTML` swap avoids new
identity. It does not, for three independent reasons:

1. **FLIP needs real per-element identity.** After the `fs=1` snap the runtime replaces
   `stage.innerHTML` with server bytes (`_html_stitcher.py:585-608`; `scriba.js:301-303`)
   — the old DOM nodes are destroyed. To animate "value 40 moved slot 3→2" FLIP must match
   the *value's* identity across the swap, i.e. a `data-item-id`. Matching by `data-target`
   matches **slots**, and slots don't move under (a) — so FLIP-by-`data-target` animates
   nothing. Correct per the brief's own note: "FLIP cần identity thật." So FLIP buys no
   savings over strategy (b)'s item-id; it just moves the identity to a data attribute.
2. **It reopens the closed motion path.** A-1 makes motion a pure function of the
   server-computed identity diff; A-2 keeps the kind registry closed; a bespoke client FLIP
   walk is exactly the parallel runtime motion path those rules exist to prevent
   (`anim-unified-motion-model.md` §3 A-1/A-2). If we want the slide, do it **server-side**
   via `position_move` (strategy b, Tree precedent) — same visual, inside the law-set.
3. **It fights resting-truth.** The server SVG already paints the final frame (A-0.iv);
   a client FLIP animates *on top of* the settled truth, risking measured≠painted.

There **is** a blessed hybrid if the slide is wanted *without* breaking selectors: a
**second identity channel**, exactly as `\cursor` got its own `cursor_move` kind and
`_diff_cursors` channel distinct from the slot grid (`differ.py:273-283`,
`scriba.js:308-320`). Keep `data-target=cell[i]` slot-keyed for selectors **and** emit an
item-keyed position channel that slides content. This is architecturally sanctioned but is
strictly more machinery than (a); it belongs in v1.1 behind an opt-in flag, not v1.

### Verdict

**v1 = strategy (a), slot-identity on a fixed max-N grid (Queue model).** It solves the
stated problem (interior removal reflows so no hole exists → linear narration is honest),
holds R-32 by construction, keeps index selectors intact, and adds **no** motion
vocabulary or JS. **v1.1 (opt-in) = element-identity `position_move` slide** for the
prettier motion, via a Tree-style position injection **plus** the item-keyed second
channel so selectors stay index-based. **FLIP: rejected.**

---

## 3. Sentinel design

**Goal:** `begin()−1` and `end()` slots that an out-of-range iterator/cursor/annotation can
park on (~5 target problems), drawn faint/dashed, **addressable from declaration** (A-6:
real `data-target` reserved at t0, never runtime-injected), and **excluded** from
`all`/`range`.

**Addressing — reuse Queue's `front`/`rear` precedent, not a new index form.** The cell
selector regex is numeric-only (`SUFFIX_CELL_RE = ^cell\[(\d+)\]$`, `_types.py:202`), so
`cell[-1]` cannot parse. Queue already ships **bare named parts** `front`/`rear`/`all`
(`queue.py:213-215`) that resolve to anchors without any `[index]`. Sentinels should
mirror that exactly:

```
\shape{a}{Array}{size=5, sentinels=true}
        a.before   → the begin()−1 slot, left of cell[0]   (anchor x = −(cw+gap) + cw/2)
        a.after    → the end() slot, right of cell[live−1]  (anchor x = live·(cw+gap) + cw/2)
```

- **Parsing:** zero regex change — `before`/`after` are bare suffixes like `front`/`rear`.
  Add them to `addressable_parts()` and `validate_selector()` **only when `sentinels=true`**.
  [Deduced from `queue.py:209-227`]
- **Excluded from `all`/`range`:** because they are **named**, not `cell[i]`, the `.all`
  expansion (→ `cell[0..size-1]`) and numeric `range[lo:hi]` never include them. Free. [Deduced]
- **Drawn faint/dashed:** a dedicated `scriba-sentinel` CSS class (dashed stroke, reduced
  opacity) — a new class, not a `scriba-state-*`, so it never collides with the signal
  states and reads as chrome. [Hypothesized]
- **Prescan width (A-6):** the two sentinel slots widen `bounding_box` from t0 by
  `2·(cw+gap)`, reserved every frame → the envelope is stable and the sentinels are
  measured citizens (D-4). Because reservation is at declaration, no timeline scan is
  needed for them. [Deduced]
- **`a.after` tracks `live`:** its anchor sits at `live·pitch`, so it moves as the array
  grows/shrinks. Under strategy (a) this is a `position_move` on a **single** decoration
  (cheap) or, simpler, a redraw — the sentinel is chrome, not a cell. Recommend redraw
  (no identity needed). [Hypothesized]

**Alt considered:** `a.sentinel[left]`/`a.sentinel[right]` — needs a new
`sentinel\[(left|right)\]` regex and reads more verbose than `before`/`after`. The
`front`/`rear` precedent makes bare names the house-consistent choice.

---

## 4. Surface (settled)

**Insert/remove need no grammar or parser work.** The generic `\apply` already forwards
any non-`value`/`label` key as a nested param into `apply_command` — confirmed shipping for
Graph (`\apply{G}{remove_edge={from="D", to="C"}}`, `examples/algorithms/graph/union_find.tex:67`)
and LinkedList. `scene._apply_apply` builds the `extra` dict from all such keys
(`scene.py:766-773`) and `_frame_renderer` replays it via `apply_command`
(`:516-518`). So:

```
\apply{a}{insert={at=2, value=7}}     → ArrayPrimitive.apply_command({"insert": {"at":2,"value":7}})
\apply{a}{remove=2}                    → ArrayPrimitive.apply_command({"remove": 2})
```

route to a new `ArrayPrimitive.apply_command` with **zero** grammar/lexer/parser changes.
Mirror LinkedList's shape (`linkedlist.py:141-170`), but on the **fixed `size` grid** (do
not grow `len` past the reserved envelope). Recommend key `at` (clearer than LinkedList's
`index`; accept both). Only the `sentinels=true` declaration param needs plumbing.

Per-layer deltas:

| Layer | Change | Grade |
|---|---|---|
| Grammar / parser / lexer | **none** — generic `\apply` nested-dict passthrough already works | [Confirmed] |
| `scene.py` | **none** — `_apply_apply` already accumulates `insert`/`remove` into `apply_params` | [Confirmed] |
| `array.py` | new `apply_command` (insert/remove on fixed grid); `live` count; `sentinels` in `ACCEPTED_PARAMS`; sentinel parts in `addressable_parts`/`validate_selector`/`resolve_annotation_point`; relax `E1402` to `len(data) ≤ size` | [Hypothesized] |
| `_frame_renderer.py` | **none** for v1 (fixed size ⇒ bbox already stable); measure already replays `apply_command` on deepcopies (`:260-262`) | [Confirmed] |
| `differ.py` | **none** — `value_change`/`element_add/remove` already emitted | [Confirmed] |
| `scriba.js` | **none** | [Confirmed] |
| CSS | one `scriba-sentinel` rule (dashed/faint) — shared stylesheet ⇒ `SCRIBA_VERSION` bump (§6) | [Hypothesized] |

---

## 5. Prescan / max-N plan

**v1 needs no new prescan.** The physical `size` **is** the reserved envelope, exactly like
Queue's `capacity`. Author declares `size = max-N`; the array starts with `live = len(data)`
populated slots (`live ≤ size`); insert/remove move `live` within `[0, size]`. Because
`bounding_box().width = size·cw` is independent of `live`, every frame reserves the max and
`_frame_renderer.py:746` centers identically → R-32.1/.2 hold with the shipped machinery.
The existing `measure_scene_layout` replay (`_frame_renderer.py:240-293`) already folds any
mid-timeline width growth (a wide inserted `value`) into the envelope via the monotonic
`_cell_width` (`array.py:174`, and a new `set_value`/insert growth hook).

**Why not an AST count-prescan (the brief's `_prescan_value_widths` analogue)?** Because
`_prescan_value_widths` explicitly **does not replay structural ops** ("no push/pop/add_node
side effects", `_frame_renderer.py:54-55`) — there is no count-prescan today, and the
fixedbox investigation's lesson is that the *frame-level* reserve (fixed `size`) beats a new
upstream scan (`fixedbox-content-sizing.md` §4 note). Fixed `size` = the reserve, no scan
needed.

**v1.1 auto-size (optional convenience).** If authors should omit `size` and let net inserts
grow it, add a `_prescan_slot_counts` pass that replays `apply_command` insert/remove on the
**real** primitives to a monotonic `_reserved_n = max(live over timeline)` (living outside
the display snapshot, exactly like `_cell_width`), with `bounding_box` reserving
`_reserved_n`. This is the count-analogue of `_prescan_value_widths` and is the only place a
timeline scan is justified. [Hypothesized]

**Result:** the original pathology dissolves — with real remove+reflow inside a fixed grid,
the predecessor of a cell is always its physical left neighbour, so "1 cell to the left" is
literally true; there is no hidden hole because there is no hidden slot (removed values
vacate the *tail*, never the interior).

---

## 6. Phased patch plan + RED tests

**Version policy:** the only byte-moving change is the shared `scriba-sentinel` CSS (a
stylesheet token add bumps `SCRIBA_VERSION`, precedent: 0.22.2 bumped 14→15 for exactly one
stylesheet token, `_version.py`). If sentinels ship in the same train as another CSS/JS
change, fold into that single bump. Insert/remove alone (no CSS) are additive Python ⇒
**no bump**, goldens for opt-in files only.

| Phase | Scope | Bump? | Golden churn |
|---|---|---|---|
| **v1** | Array `insert`/`remove` on fixed max-N grid; `live` count; relax `E1402`; slot-identity `value_change` cascade | no | new opt-in fixtures only |
| **v1-sentinel** | `sentinels=true`; `a.before`/`a.after` parts + anchors; `scriba-sentinel` CSS | **yes ×1** (CSS) | interactive goldens (the bump) + opt-in |
| **v1.1** | Queue/LinkedList unify on the fixed-grid reserve (**fixes the LinkedList R-32 jump**; adds LinkedList to R-32 applies-to) | no | LinkedList/Queue opt-in |
| **v1.2 (opt-in)** | element-identity `position_move` slide via item-keyed second channel (§2b) | no | opt-in |

### RED tests (write failing first; `tests/unit/`)

1. `test_array_remove_reflows_no_hole` — `size=5 data=[1,2,3,4,5]`, `\apply{a}{remove=1}` →
   emitted values read `[1,3,4,5]` contiguous in slots 0..3, slot 4 empty; **no interior
   gap**. RED today (Array has no `apply_command`; probe `rf_probe.py` shows `remove` is a
   no-op).
2. `test_array_insert_shifts_right` — `\apply{a}{insert={at=2, value=9}}` → slots become
   `[1,2,9,3,4]`, `live=5`. RED today.
3. `test_array_reflow_bbox_frame_stable` (**R-32 guard**) — across an insert **and** a remove
   frame, `bounding_box().width` is identical and equals `size·cw` → `_frame_renderer.py:746`
   `x_offset` identical → no jump. This is the test LinkedList currently **fails** (544≠434);
   assert Array does not.
4. `test_array_insert_overflow_errors` — inserting past `size` raises a clear E-code (do not
   silently grow in v1). RED today.
5. `test_array_sentinel_addressable_from_t0` — `sentinels=true` ⇒ `a.before`/`a.after`
   validate and resolve to anchors left of cell[0] / right of cell[live−1] at frame 0, and
   are **excluded** from `.all` expansion and `range`. RED today.
6. `test_array_sentinel_reserved_envelope` (**R-32**) — sentinels widen bbox by
   `2·(cw+gap)` in **every** frame (present even when nothing parks on them). RED today.
7. `test_array_hidden_still_noop_guard` — pin current reality (`\recolor{cell}{hidden}`
   renders normally) so the new remove path is proven to be the *only* deletion mechanism and
   we don't accidentally wire a second one. GREEN guard.
8. `test_array_narrow_reflow_byte_identical` — an Array that never inserts/removes emits
   byte-identical SVG to pre-change (additive-only proof). GREEN guard.

---

## 7. Risk table

| # | Risk | Grade | Mitigation |
|---|---|---|---|
| R1 | **R-32 regression** — a reflow that varies bbox width jumps horizontally at `_frame_renderer.py:746`. | **Confirmed** (LinkedList 544→434, probe) | Fixed max-N grid ⇒ `bounding_box().width` constant ⇒ centering constant. Test #3 is the gate. Never grow `len` past the reserve in v1. |
| R2 | **Differ noise for large N** — insert near the front emits `N−k` `value_change`s (mass text morph). | Deduced | Acceptable for the ~5 small-N targets. For large N, v1.2's `position_move` slide reads cleaner. Document the tween as "values flow one slot over". |
| R3 | **`value_change` + `$math$` guard** — a shifted cell holding `$…$` must not flash raw TeX mid-tween. | Confirmed guard exists | The `indexOf('$')` guard (`scriba.js:136`) already skips the text write for math cells; the cascade inherits it (same fix noted in `fixedbox-content-sizing.md`). |
| R4 | **Annotation/selector semantics after reflow** — `\annotate{a.cell[2]}` tracks the *position*, so after a shift it points at a different value. | Deduced | This is correct for slot-identity and must be **documented** in `ruleset.md`/`primitives.md`: `cell[i]` = position, not value. Element-identity (v1.2) is the opt-in for value-tracking annotations. |
| R5 | **LinkedList is already non-compliant** and unifying it churns its goldens. | Confirmed (absent from `ruleset.md:915-917`; probe) | Scope LinkedList to v1.1; its jump is pre-existing, not introduced here. Add it to R-32 applies-to when unified. |
| R6 | **`E1402` relaxation** — allowing `len(data) < size` could mask a real author typo. | Deduced | Keep `len(data) > size` an error; only allow `<` (partial fill), and default `live=len(data)`. Clear hint text. |
| R7 | **Sentinel counted in aggregates** — `\recolor{a.all}` or `range` accidentally hitting a sentinel. | Deduced | Named parts (not `cell[i]`) are structurally excluded from `.all`/`range` (§3). Test #5 pins it. |
| R8 | **CSS bump amplification** — the `scriba-sentinel` rule re-blesses every interactive golden. | Confirmed mechanism | Batch the sentinel CSS with any other pending CSS/JS change into **one** `SCRIBA_VERSION` bump (§6); insert/remove alone need none. |

---

## 8. Open questions (≤5)

1. **Sentinel naming** — `a.before`/`a.after` (mirrors Queue `front`/`rear`, zero regex) vs
   `a.sentinel[left/right]` (new regex, more explicit). Recommend **`before`/`after`**.
2. **Tail-vacate vs hidden-skip on remove** — after `remove`, render the freed tail slot as
   an **empty cell** (reads as "unused capacity", like Queue) or **skip** it (Array would need
   new skip logic + would then shrink width → R1). Recommend **empty cell** (keeps the grid,
   preserves R-32). Confirm the empty-cell look is acceptable.
3. **v1 auto-size** — require the author to declare `size = max-N` (Queue-style, no prescan)
   for v1, deferring the `_prescan_slot_counts` auto-grow to v1.1? Recommend **yes** (simplest,
   R-32-safe).
4. **`at` vs `index` key** — adopt `insert={at=k}` (clearer) while accepting LinkedList's
   `index` alias, or standardise both primitives on one? Recommend **accept both, prefer `at`**.
5. **Does v1.2's slide justify the second identity channel?** — the item-keyed `position_move`
   channel (like `_diff_cursors`) is real machinery; confirm the ~5 target problems actually
   want the spatial glide over the v1 text-morph before building it.

---

## 9. Evidence ledger (quick index)

| Claim | Grade | Anchor |
|---|---|---|
| `base.apply_command` is a no-op; only Tree/Queue/Stack/LinkedList/Graph/Plane2D override | Confirmed | `base.py:1287-1294` |
| Array has no structural remove; `remove` is a no-op | **Confirmed (executed)** | probe `rf_probe.py` |
| Array `hidden` is a visual no-op (5 rects + value still render; no CSS rule) | **Confirmed (executed)** | probe `rf_hidden.py`; `scriba-scene-primitives.css:122-148` |
| Array positions are fixed `i·(cw+gap)`; bbox width `= size·cw` (frame-invariant) | Confirmed | `array.py:275,363-393` |
| Queue = fixed `capacity` slot grid; enqueue/dequeue fill/clear + pointer; no `position_move` | Confirmed | `queue.py:155-205,240,317` |
| LinkedList ships `insert`/`remove` (list.insert/pop); bbox width `= len·nw` (**varies**) | Confirmed | `linkedlist.py:141-170,229-246` |
| LinkedList reflow jumps 544→434→544 px, value slides 110 px, no `position_move` | **Confirmed (executed)** | probe `rf_probe.py` |
| LinkedList absent from R-32 applies-to list | Confirmed | `ruleset.md:915-917` |
| Tree = element-identity reflow; `_relayout()` recomputes all positions; keyed by `node_id` | Confirmed | `tree.py:232-320` |
| Positions reach the wire via `get_node_positions` duck-typing → `position_move` | Confirmed | `emitter.py:201-228`; `differ.py:218-236` |
| Primitives centered on **per-frame live** bbox width (the jump mechanism) | Confirmed | `_frame_renderer.py:738,746` |
| `measure_scene_layout` replays `apply_command` on deepcopies → max-bbox envelope (R-32.3) | Confirmed | `_frame_renderer.py:240-293` |
| `_prescan_value_widths` replays `set_value` only, **not** structural ops | Confirmed | `_frame_renderer.py:45-55` |
| Generic `\apply{X}{key={nested}}` forwards to `apply_command` with no grammar change | Confirmed | `scene.py:766-773`; `_frame_renderer.py:516-518`; `union_find.tex:67` |
| `position_move` handler ships (`translate` slide), zero new JS | Confirmed | `scriba.js:206-215` |
| Second identity channel precedent (`cursor_move`/`_diff_cursors`) exists | Confirmed | `differ.py:273-283`; `scriba.js:308-320` |
| `SUFFIX_CELL_RE` numeric-only (`cell[-1]` cannot parse); Queue ships bare `front`/`rear` | Confirmed | `_types.py:202`; `queue.py:213-215` |
| `E1402` forbids `len(data) != size` (blocks `live < size` today) | Confirmed | `array.py:147-153` |
| Kind registry closed under inversion; `value_change` self-inverse | Confirmed | `differ.py:25-31`; A-2 |

---

## Appendix — probe scripts (scratchpad, not committed)

- `/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/7681f32d-4d54-4c44-ae5a-5a3123c0d2b6/scratchpad/rf_probe.py`
  — LinkedList insert/remove bbox-width variance + value slide; Array `remove` no-op;
  out-of-range selector rejection.
- `/private/tmp/claude-501/-Users-mrchuongdan-Documents-GitHub-scriba/7681f32d-4d54-4c44-ae5a-5a3123c0d2b6/scratchpad/rf_hidden.py`
  — Array `hidden` renders normally (5 rects + value); no `scriba-state-hidden` CSS.

Reproduce with `.venv/bin/python <path>` from the repo root.
