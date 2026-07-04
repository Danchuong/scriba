# Unified Motion Model — one law-set (A-rules) under reverse/jump, emphasis, cursors, `\playeach`, reflow, and `\ref`

> Design synthesis. **No repo source modified.** Repo @ `main` (scriba 0.22.2, `SCRIBA_VERSION = 15`,
> `scriba/_version.py:6`). Companion to the **D-rules** (decoration spine, `investigations/unified-decoration-model.md`):
> D governs *what a decoration is and how it is emitted*; **A governs *how anything on stage moves* between two
> frames.** The two are orthogonal layers — a decoration can ship parallel Python plumbing yet be fully unified at
> the motion layer (see §1 note on `\trace`).
>
> Evidence grades: **[Confirmed]** = read in source or executed this session (probe
> `scratchpad/au_motion.py`, run against `.venv`) · **[Deduced]** = logical consequence of confirmed facts ·
> **[Hypothesized]** = design proposal, not yet built.

---

## 1. Hand-off Brief (3 sentences)

Scriba **already has** a unified motion substrate — every animation is `compute_transitions(prev_frame, curr_frame)`
producing an ordered list of `Transition[target, prop, from, to, kind]` (`differ.py:336-369`) that a **stateless
kind→handler dispatch** (`scriba.js:119-277`) replays against identity-keyed DOM nodes, and the tween is only a
*cosmetic bridge*: when the server SVG differs the runtime snaps `stage.innerHTML` to the server bytes (`fs=1`,
`_html_stitcher.py:585-608`; `scriba.js:301-303`), so the server frame is always the resting truth. The **A-rules**
name this substrate and add exactly three obligations — the kind registry is **closed under inversion** (Confirmed
today, probe P1: 10/10 kinds pair up), **emphasis is a channel disjoint from state** (transient, compositor-only,
`fs`-neutral), and **markers are decorations with identity** (not stateless state-hops) — so that all ten
animation-clarity requests, plus future motion, land as *diffs on identity* rather than new runtime code paths; the
only genuinely new machinery is a reverse-manifest walk (①), one emphasis kind family (②④⑤), and per-marker identity
(③), while `\playeach` (⑥), reflow (⑦), and the two new primitives (⑧⑨) are pure scene-build additions that emit only
*existing* kinds. This session **executed** the three load-bearing facts the model turns on: the transition kinds are
already closed under inversion (P1), `\cursor` today is a **stateless two-recolor hop** with no moving glyph (P2), and
two cursors sharing `curr_state` **collide** — the second demotes the first (P3) — which is precisely why bindable
multi-cursor needs identity.

> **Motion-layer boundary (why this is a separate law-set from D).** `\trace` shipped (R-37, v0.22.2) as a *parallel*
> Python `traces` list with its own `_diff_traces` (`differ.py:246-270`) — the letter of D-1 ("one list") is bent — yet
> at the **motion layer it is fully unified**: it emits the existing `annotation_add` kind, uses the same
> `data-annotation="…-solo"` key shape, and draw-ons through the shipped JS handler with **zero JS changes** (R-37,
> `smart-label-ruleset.md:548-551`; conflict-audit C11). The A-rules govern the *manifest + kinds + runtime* and are
> **independent of whether the upstream Python is one list or two**. That independence is what makes them stable.

---

## 2. A-0 — the invariant axes (premises, all [Confirmed] path:line)

Six axes hold today. Every A-rule is derived from them; every conflict in §5 is "does feature X preserve axis Y".

| Axis | Statement | Anchor |
|---|---|---|
| **A-0.i — Stage is data** | A frame is the tuple `{svg, narration, substory, tr, fs}` shipped as a JSON island (`scriba.js:356-365`). The runtime is structure-driven: it sees only `data-target` / `data-annotation` / `data-shape` attributes and a `kind` string — never "this is a Queue". | `_html_stitcher.py:593-599`; `emitter.py:106-117`; `scriba.js:280,289,298` |
| **A-0.ii — Identity = key** | Stable cross-frame identity is the selector on `data-target` (cells/nodes) or the composite key on `data-annotation` (decorations). All motion is a **diff on identity**: the differ matches prev/curr by key → `[target,prop,from,to,kind]`; the JS resolves `[data-target="…"]` / `[data-annotation="…"]` and mutates it. | `differ.py:54-243`; `scriba.js:121,199,206` |
| **A-0.iii — Lifecycle** | Highlights are ephemeral (cleared each `\step`); annotations & traces persistent-by-default, ephemeral if flagged; `apply_params` (structural pushes) ephemeral per-frame. | `scene.py:232-235,252-256` |
| **A-0.iv — Measured == painted, at build AND runtime** | Build: `bounding_box()` is pure over `_annotations`; the reserved envelope is the cross-frame max, computed once by `measure_scene_layout` (R-32.1–.6). Runtime: the WAAPI tween is cosmetic; when server SVG differs (`fs=1`) the runtime snaps `innerHTML` to server bytes at settle — the destination is **always** the server frame, never a JS approximation. | `ruleset.md:907-956`; `_frame_renderer.py:45,60`; `_html_stitcher.py:585-608`; `scriba.js:301-303` |
| **A-0.v — Color = token-ref** | State is a CSS class (`scriba-state-X` / `scriba-annotation-state-X`); the runtime swaps class **names**, not colors, so dark-theme adaptation is free. | `scriba.js:122-129`; R-36 `smart-label-ruleset.md:503-532`; conflict-audit C19 |
| **A-0.vi — Opt-in → byte-stable** | Motion features are additive; `SCRIBA_VERSION` (now **15**) bumps only when *existing* bytes move — for motion that means the shared `scriba.js` (+ its verbatim inline slice) or the `{svg,…,tr,fs}` schema changes. | `_version.py` (14→15 history: 0.22.2 bumped only for a shared-stylesheet token add) |

---

## 3. The A-rules (A-1 … A-8)

R-card style. Each is a MUST for any motion, existing or future. Rationale ties to confirmed code.

### A-1 — Motion is a pure function of an identity diff
The only way to produce animation is `compute_transitions(prev, curr)` → ordered `Transition[target,prop,from,to,kind]`
(`differ.py:336-369`), applied by a stateless kind→handler dispatch (`scriba.js:119-277`). A command never "animates";
it mutates scene state and motion **falls out of the diff**.
*Rationale:* preserves A-0.i/.ii — every present and future feature reduces to "what identity changed, and how", so one
runtime serves all. *Request items:* ALL (foundational). *Today:* satisfied for forward-adjacent steps. [Confirmed spine]

### A-2 — Closed kind registry; every kind declares an inverse
`kind ∈ {recolor, value_change, highlight_on/off, element_add/remove, annotation_add/remove/recolor, position_move}`
is a **closed** registry (`differ.py:25-31`). Each kind MUST have an inverse in the registry and the registry MUST stay
closed under inversion. **Reverse and jump playback MUST be the inverse manifest applied**, not a new emit path; a new
kind ships only with `{emit, JS handler, inverse}`.
*Rationale:* reverse-step (①) is already latent — closure is **Confirmed** (probe P1: 10/10; `add↔remove`, `on↔off`,
and `recolor`/`value_change`/`position_move`/`annotation_recolor` self-inverse under from/to swap) — but unused:
`show()` animates only `i===cur+1` (`scriba.js:331-337`); prev and jumps `snapToFrame`. Making inverse a law turns ①
into "generalize `show` + build the reverse of `frames[cur].tr`", not per-kind code. *Request items:* ① (reverse/jump);
guards ⑧⑨ (new-primitive kinds must not break closure). *Today:* closure Confirmed (P1); runtime reverse **not wired** —
the gap. [Confirmed]

### A-3 — Emphasis is a channel disjoint from state
Emphasis (pulse, tint, defocus) is transient salience that (a) never writes persistent `shape_states`/`annotations`,
(b) self-expires within the step, (c) leaves the resting SVG **byte-identical** to the un-emphasized frame, (d) uses
compositor-only props (`transform`/`opacity`), never layout. It is A-0.iii lifecycle + A-0.iv purity applied to motion.
*Rationale:* today `value_change`'s scale-bounce (`scriba.js:138-139`) and `_fadeInNewAnnotations` (`:87-96`) are
proto-emphasis — cosmetic, stateless, `fs`-neutral. ②④⑤ are all this: ② pulse a changed cell, ④ tint a `\ref`-ed node,
⑤ dim the non-focused. Modeling emphasis as *state* would churn goldens and threaten R-32 reflow. *Request items:*
② (delta-emphasis), ⑤ (`\focus` defocus), ④ (`\ref` tint, with A-7). *Today:* proto-emphasis exists; **no first-class
emphasis kind** — NET-NEW kind family emitting `tr`-only entries with no scene-state backing (so `fs` stays 0).
[Confirmed proto-emphasis; Hypothesized kind family]

### A-4 — A marker is a decoration with identity; its motion is `position_move`
A cursor/pointer that persists and MOVES is an addressable decoration (stable `data-annotation` key) that rides
`position_move` (`scriba.js:185-197`; `differ.py:218-236`), **not** a state that hops between cells. Multiple markers
are distinct identities.
*Rationale:* today `\cursor` is a **stateless two-recolor hop** (probe P2 Confirmed: `cell[0]` current→done,
`cell[1]` idle→current; `scene.py:905-928`) — so two cursors sharing `curr_state` **collide** (probe P3 Confirmed: the
second demotes the first; only one cell stays `current`). Binding named cursors (③) requires identity: a marker glyph
that `position_move`s, or per-cursor distinct states. *Request items:* ③ (multi-cursor bind). *Today:* single stateless
cursor works; multi/glide needs identity. **Additive**: keep `\cursor` hop (zero churn) + add opt-in marker. [Confirmed P2/P3]

### A-5 — A frame macro expands to indistinguishable hand-frames
A frame generator (`\playeach`) MUST expand at **scene-build time** to the same `FrameIR` sequence a hand-authored
`\step` list would produce — identical snapshots, identical `tr`/`fs`, identical step-count. **No runtime-only frames.**
*Rationale:* preserves A-0.i, A-1, A-0.iv — the macro is front-end sugar over `apply_frame` (`scene.py:224-256`), exactly
as `\foreach` is sugar over `_expand_commands` (`scene.py:243`). A generated frame and a hand frame must be
byte-indistinguishable downstream, or the differ/measure invariants fork. *Request items:* ⑥ (`\playeach`). *Today:*
`\foreach` precedent exists; `\playeach` NET-NEW, pure Python, no JS. [Confirmed precedent; Hypothesized macro]

### A-6 — Layout mutation goes through prescan; the resting frame is server truth
Any insert/reflow/grow (⑦) MUST widen the reserved envelope via the build-time prescan (`_prescan_value_widths`,
monotonic, `_frame_renderer.py:45,60`; `measure_scene_layout`, R-32.3) so R-32.1–.4 hold for **every** frame, and MUST
carry `fs=1` (`svg_changed`, `_html_stitcher.py:585-608`) so the runtime resyncs to the exact server SVG after the
cosmetic `position_move`. **Sentinel slots are addressable from declaration** (a real `data-target` reserved at t0),
never runtime-injected.
*Rationale:* an insert that grows the structure mid-scene jumps every later frame unless the max width is reserved from
frame 0 — the exact displacement R-32 forbids. `position_move` source/dest must be the pre/post **server** coords (Tree
already does this via `_inject_tree_positions`, `emitter.py:198`; `differ.py:218-236`). *Request items:* ⑦ (insert/reflow
+ sentinel). *Today:* value-width prescan + structural-growth envelope (R-32.3) + `fs` all exist; sentinel addressability
+ `position_move` for inserted cells is the new wiring. [Confirmed mechanisms; Hypothesized sentinel]

### A-7 — Narration binds identity through the same selector algebra
A narration reference (`\ref{selector}`) MUST resolve through the **same** selector→identity resolver decorations use
(Point/Rect/Path, D-3), producing (a) an emphasis (A-3) on the referenced node and (b) the aria-live announcement
(`_html_stitcher.py:377,628`), fired together **after** the visual settles (`scriba.js:304-307`, the A03 ordering fix).
No parallel "narration target" grammar.
*Rationale:* `\ref` is "point at this while I say it" — the pointing reuses the decoration resolver and the emphasis
reuses A-3, so `\ref{g.block[…]}` works the day `block` resolves. A **single** aria-live channel (narration) avoids
double-announce. *Request items:* ④ (`\ref` narrate). *Today:* narration interpolation + aria-live exist; `\ref` NET-NEW,
resolves via existing selector algebra + A-3 tint. [Confirmed aria/ordering; Hypothesized `\ref`]

### A-8 — Reduced-motion / print / no-JS is ground truth; motion is progressive enhancement
Every kind (existing + new) MUST render correctly with `_canAnim=false` (`scriba.js:41-43,281,331-336`): the server SVG
at rest already shows the destination, so disabling the tween loses only the interpolation. Emphasis (A-3) MUST be
instant/no-op under reduced-motion; aria-live still fires (A-7). New kinds prove this before merge.
*Rationale:* R-32.5 parity + conflict-audit C13 — draw-on, fades, pulses are all pure enhancement over an
already-correct static frame. This is what lets emphasis stay stateless and reversible. *Request items:* cross-cutting
a11y for ②④⑤⑥⑦; a MUST-gate on any new kind. *Today:* Confirmed for all shipped kinds (`scriba.js:88,281`; conflict-audit
C13). [Confirmed]

---

## 4. Matrix — 10 request items × A-rules

| # | Item | Primary A-rule(s) | Classification | JS touch? | One-line disposition |
|---|---|---|---|---|---|
| ① | reverse / jump tween | **A-2** | *consequence* (inverse already closed) + runtime wiring | **YES** (generalize `show`) | Build reverse of `frames[cur].tr`; drop the `i===cur+1` gate. Biggest latent win. |
| ② | delta-emphasis | **A-3** | *new kind* (`pulse`) | **YES** (new handler) | Stateless compositor pulse on the changed identity; `fs=0`. |
| ③ | multi-cursor bind | **A-4** | *new capability* (marker identity) | maybe (`position_move` exists) | Opt-in marker glyph; per-marker `data-annotation` key; P3 proves state-hop can't scale. |
| ④ | `\ref` narrate | **A-7** (+A-3) | *consequence* (selector algebra + emphasis) | reuse (A-3 handler) | `\ref{sel}` → tint + aria-live, atomically, after settle. |
| ⑤ | `\focus` | **A-3** | *consequence* (emphasis on the complement set) | maybe (new `defocus` handler) | Dim all-but-target; ephemeral; resting SVG unchanged. |
| ⑥ | `\playeach` | **A-5** | *new macro* (pure Python) | **NO** | Expands to hand-frames at build; `\foreach` precedent. |
| ⑦ | insert / reflow + sentinel | **A-6** | *consequence* (R-32 + `fs` + `position_move`) + sentinel | **NO** (`position_move` ships) | Sentinel addressable at t0; prescan reserves max width; insert glides within envelope. |
| ⑧ | string playbook | — (**D + A only**) | *new primitive* | **NO** | Cells ride `recolor`/`value_change`/`position_move`/marker. No new motion rule. |
| ⑨ | heap | — (**D + A only**) | *new primitive* | **NO** | Swaps ride `position_move`; compares ride A-3 emphasis. No new motion rule. |
| ⑩ | title / invariant / polish | **A-8** / D-chrome | *chrome + constant tuning* | **YES** (DUR/easing) | Invariant banner = persistent caption; polish = tune `scriba.js:44-52`. Batch into ①'s JS revision. |

**Reading:** only ①②③⑩ touch `scriba.js`; ④ reuses A-3's handler; ⑤⑥⑦⑧⑨ are Python-only. **⑧ and ⑨ carry no new
motion rule at all** — they are D-layer primitives whose animations are entirely existing kinds. That is the test the
A-rules are meant to pass: a new data structure should need *zero* new motion vocabulary.

---

## 5. Conflict & condition table (A-rules vs R-30/31/32, D-rules, a11y)

| Concern | Rule pair | Risk | Condition (MUST) | Grade |
|---|---|---|---|---|
| Inverse of draw-on | A-2 vs R-37 | `annotation_add` draws the stroke *in*; its registry inverse is `annotation_remove` (a **fade**), not a literal un-draw | Define inverse **semantically** (kind-level), not pixel-time-reverse. Reverse of draw-on = fade-out (already exists, `scriba.js:198-204`). Document as the contract. | [Deduced] |
| `value_change` reverse | A-2 vs `$math$` guard | reverse writes text; math values skip the text write (`scriba.js:136`) | Reverse manifest inherits the same `indexOf('$')` guard → math cells pulse-only in both directions. | [Confirmed guard] |
| Emphasis reflow | A-3 vs R-32 | a pulse that scales *layout* would change bbox → cross-frame jump | Emphasis MUST use `transform`/`opacity` only (compositor), never `width`/`height`/`font-size`. `bounding_box()` untouched → `fs` stays 0 (R-32.4 purity holds). | [Deduced] |
| Emphasis a11y / double-announce | A-3 vs A-8/A-7 | pulse invisible under reduced-motion; a second live region would double-announce | **Single** aria-live = narration (A-7, `_html_stitcher.py:377,628`). Emphasis is visual-only; reduced-motion → instant/no-op; semantics reach AT via narration. | [Confirmed aria; Deduced policy] |
| Marker vs cursor goldens | A-4 vs D-8 | promoting `\cursor` to `position_move` churns every cursor golden **and** needs multi-state disambiguation (P3) | **Additive**: keep `\cursor` state-hop (zero churn); add marker as opt-in (`\marker`, or `\cursor[glyph=pointer]`). | [Confirmed P3] |
| Marker coordinates | A-4 vs `position_move` source | the differ reads `x,y` from `shape_states`; today only Tree injects them (`emitter.py:198`) | The marker MUST publish its `x,y` into the wire (mirror `_inject_tree_positions`) so `differ.py:218-236` emits `position_move`. | [Confirmed source] |
| Focus persistence | A-3 vs A-0.iii | "dim all-but-X" could read as a persistent state change | Focus is **ephemeral** emphasis on the complement set; auto-clears next step; resting SVG unchanged. | [Deduced] |
| `\playeach` narration / substory | A-5 vs snapshot | generated frames need per-iteration narration + correct `total_frames`; substory nesting | Macro templates narration per loop var (foreach precedent); each iteration is a real `\step` counted in `total_frames`; MUST NOT cross a substory boundary. | [Deduced] |
| Reflow vs R-32.4 purity | A-6 vs R-32 | insert mid-scene jumps later frames | Sentinel declared at `\shape` (addressable t0); prescan reserves max structural width (R-32.3 **replays** `apply_command` growth, `ruleset.md:930-937`); insert → `position_move` within the reserved envelope; `fs=1` auto. | [Confirmed R-32.3] |
| Sentinel vs D-1/D-4 | A-6 vs D | a sentinel must be a real addressable part, not a runtime hack | Sentinel is a declared slot with its own `data-target`, emitted (empty) from t0 → a placement citizen (D-4), measured. | [Deduced] |
| JS churn amplification | A-2/A-3/A-4/A-8 vs A-0.vi | each JS-touching feature separately bumps `SCRIBA_VERSION` + re-blesses all interactive goldens | **BATCH** all `scriba.js` changes into ONE revision → one bump (§6). Python-only features ride after with none. | [Confirmed mechanism] |

**No hard contradiction.** Every risk resolves to a condition already satisfiable with shipped machinery; the two that
need genuinely new code (A-3 emphasis kind, A-4 marker identity) are additive and `fs`-neutral by construction.

---

## 6. `SCRIBA_VERSION` policy & phased plan

### 6.1 Version policy (explicit)

- **`scriba.js` change** (new handler, reverse walk, tuned `DUR`/easing) → external hash **and** the verbatim inline
  slice both differ (the inline runtime is *derived* from `scriba.js`, `scriba.js:24-25,351`) → **every** interactive
  page's bytes move → `SCRIBA_VERSION` bump + full interactive golden re-bless. [Confirmed mechanism]
- **Frame-schema change** (new field in `{svg,narration,substory,tr,fs}`) → same → bump.
- **New primitive / new command emitting only existing kinds** → additive → goldens for opt-in files only → **no bump**
  (unless it ships shared CSS — cf. 0.22.2's R-36 token add, which bumped 14→15 for a *stylesheet* change alone,
  `_version.py`).
- **Recommendation:** spend **one** bump. Land the JS-touching items as a single `scriba.js` revision; everything else
  is additive Python that reuses shipped kinds.

### 6.2 Phases (each independently shippable)

Sibling deep-dive files do **not exist yet** (Confirmed: no `investigations/anim-{runtime-reverse,multicursor,narrate-focus}.md`).
Their outputs slot into Phases A/B below; the framework does not block on them.

| Phase | Items | Content | Bump? | Golden churn |
|---|---|---|---|---|
| **A — Motion runtime core** | ①②③⑤ (+⑩ constants) | One `scriba.js` revision: (1) generalize `show()` to build+apply the **inverse** of `frames[cur].tr` for backward/jump (A-2); (2) add the **emphasis kind family** `pulse`/`tint`/`defocus`, compositor-only (A-3); (3) marker **identity** plumbing over the existing `position_move` (A-4); (4) fold ⑩ constant tuning here. | **YES ×1** | all interactive goldens (the bump) |
| **B — Narration binding** | ④ | `\ref{sel}` resolves via selector algebra → Phase-A emphasis + aria-live (A-7). Pure Python + reuses shipped handler. | no | opt-in files |
| **C — Frame macro** | ⑥ | `\playeach` expands to `FrameIR` at build (A-5, `\foreach` precedent). Pure Python, no JS. | no | opt-in files |
| **D — Layout mutation** | ⑦ | Sentinel addressability + structural-insert envelope + `position_move` for inserted cells (A-6). Reuses shipped `position_move`. | no | opt-in files |
| **E — New primitives** | ⑧⑨ | `string` + `heap` (D+A compliant); ride existing kinds. | no | opt-in files |
| **F — Polish / invariant** | ⑩ residue | Invariant banner (persistent caption); any residual constant tuning batched back into Phase A. | (folded into A) | — |

**Dependencies:** B needs A's emphasis kind. C/D/E are mutually independent and parallelizable. **Order rationale:**
front-load JS (A) to spend the single bump; every later phase is additive Python that never re-blesses the corpus.

---

## 7. Doc-home recommendation

**Recommend a NEW file `docs/spec/motion-ruleset.md`** holding A-1…A-8, in the **same card format** as
`smart-label-ruleset.md` R-cards, so `check_ruleset_sync.py` extends to it by adding the file to its scan list (that
tool validates each `### <ID> — Title` card carries a verifiable `**Code ref:**` + `**Test ref:**`, cf. conflict-audit
C23). Motion is orthogonal to smart-label *pill placement*, so it earns its own file rather than swelling
`smart-label-ruleset.md`; cross-link **R-32** (stability, the A-6 prerequisite) and **R-30** (one-dispatcher, the A-1
analogue). Card prefix `A-` (animation/motion).

**Skeleton:**

```markdown
# Motion Ruleset (A-01 … A-08)

> Companion to smart-label-ruleset.md (pill placement) and the R-32 stability rule.
> Governs how identity-keyed stage elements move between two server-authored frames.

### A-01 — Motion is a pure function of an identity diff
**Normative:** MUST
**Since:** vX.Y.Z
... statement ...
**Code ref:** scriba/animation/differ.py compute_transitions;
              scriba/animation/static/scriba.js _applyTransition
**Test ref:** tests/unit/test_keyframes.py; tests/unit/test_animation_scene.py

### A-02 — Closed kind registry; every kind declares an inverse
**Normative:** MUST
...
**Code ref:** scriba/animation/differ.py Transition.kind
**Test ref:** tests/unit/test_reverse_manifest.py   (pending vX.Y.Z)
... A-03 … A-08 identically ...
```

Use the `pending vX.Y.Z` escape hatch (the sync tool honours it, conflict-audit C23) so a card may land one commit
ahead of its code, then flip to a real `path:anchor` when the phase ships.

---

## 8. Open questions (≤5)

1. **Reverse of draw-on** — semantic inverse (fade-out, free today via `annotation_remove`, `scriba.js:198-204`) vs a
   literal stroke-retract (new JS). Recommend **semantic**. Confirm it reads acceptably when stepping backward over a
   `\trace`/arrow. *(Blocks ① contract.)*
2. **Marker migration** — additive opt-in marker glyph (zero churn, P3-safe) vs promoting `\cursor` to `position_move`
   (churns cursor goldens, needs multi-state disambiguation). Recommend **additive marker**; keep `\cursor` as-is.
3. **Batch the bump** — land ①②③⑤ (+⑩ constants) as ONE `scriba.js` revision (one `SCRIBA_VERSION` bump). Confirm the
   three deep-dive agents coordinate a **single** JS PR, not three sequential bumps.
4. **Emphasis aria** — rely solely on the narration aria-live (single channel, A-7) vs per-emphasis announcements.
   Recommend **narration-only** to avoid double-announce; emphasis stays visual.
5. **`\playeach` step semantics** — each iteration = a full `\step` counted in `total_frames` (step counter grows) with
   narration templated per loop var? Or a `sub-step` model? Recommend **full `\step`** for A-5 indistinguishability.

---

## 9. Evidence ledger (quick index)

| Claim | Grade | Anchor |
|---|---|---|
| Motion = `compute_transitions` → `[target,prop,from,to,kind]` → stateless JS dispatch | Confirmed | `differ.py:336-369`; `scriba.js:119-277` |
| Tween is cosmetic; server SVG is resting truth (`fs`→`innerHTML` swap) | Confirmed | `_html_stitcher.py:585-608`; `scriba.js:301-303` |
| `fs = (server SVG string differs between adjacent frames)` | Confirmed | `_html_stitcher.py:585-587` |
| 10 transition kinds closed under inversion | **Confirmed (executed)** | `differ.py:25-31`; probe **P1** |
| `show()` animates forward-adjacent only (`i===cur+1`); prev/jumps snap | Confirmed | `scriba.js:331-344` |
| `\cursor` is a stateless two-recolor hop (no moving glyph) | **Confirmed (executed)** | `scene.py:905-928`; probe **P2** |
| Two cursors sharing `curr_state` collide (2nd demotes 1st) | **Confirmed (executed)** | `scene.py:918-922`; probe **P3** |
| `position_move` exists; reads `x,y` from `shape_states` (Tree-injected) | Confirmed | `differ.py:218-236`; `scriba.js:185-197`; `emitter.py:198` |
| `value_change` skips text write for `$math$`; scale-bounce is proto-emphasis | Confirmed | `scriba.js:136-139` |
| `_fadeInNewAnnotations` = stateless cosmetic (proto-emphasis) | Confirmed | `scriba.js:87-96` |
| `annotation_add` fires only for a NEW key; stable key renders static | Confirmed | `differ.py:294-303`; conflict-audit C12 |
| gen-token supersede guard; reduced-motion → snap (draw-on = enhancement) | Confirmed | `scriba.js:37-59,300,313`; conflict-audit C11/C13 |
| R-32.1–.6 stability; envelope replays `apply_command` growth; prescan monotonic | Confirmed | `ruleset.md:907-956`; `_frame_renderer.py:45,60` |
| Ephemeral clear covers highlights, annotations, traces | Confirmed | `scene.py:232-235` |
| narration aria-live polite; announced AFTER settle (A03) | Confirmed | `_html_stitcher.py:377,628`; `scriba.js:304-307` |
| Inline runtime is a verbatim slice of `scriba.js` (JS change ⇒ every page bumps) | Confirmed | `scriba.js:24-25,351` |
| `SCRIBA_VERSION=15`; 0.22.2 bumped for a shared-stylesheet token add alone | Confirmed | `_version.py:6` + history |
| `\ref`, `\focus`, `\playeach`, delta-emphasis, `\heap`, `\string` do not exist today | Confirmed | grep of `_grammar_commands.py` / `scene.py` (none found) |
| `\cursor`, `\narrate`, `\trace` already exist | Confirmed | `_grammar_commands.py:63,214,338` |
| Reverse manifest well-defined; emphasis kind family; marker identity | Hypothesized | §3 A-2/A-3/A-4 |

---

## 10. Probe log — `scratchpad/au_motion.py` (executed this session, `.venv`)

```
P1 kinds: 10 closed-under-inversion: True
P2 frame0 states: {'arr.cell[0]': 'current'}
P2 frame1 states: {'arr.cell[0]': 'done', 'arr.cell[1]': 'current'}
P2 cursor = two-recolor hop (no identity glyph): True
P3 two same-state cursors in one frame -> #cells in 'current': 1 (collision: 2nd demotes the 1st)
```

- **P1** enumerates the kind set from `differ.py:25-31` and verifies each kind has an involutive inverse (`INV[INV[k]]==k`).
- **P2** drives `SceneState.apply_frame` with two `\cursor` commands and reads `.state` off the snapshot — the `current`
  marker moves cell[0]→cell[1] purely by state, cell[0] becoming `done`. No `data-annotation`/`position_move` involved.
- **P3** fires two `\cursor{…curr_state=current}` in one frame; `_apply_cursor`'s "find element in `curr_state`, demote
  it" (`scene.py:918-922`) makes the second command demote the first → exactly one `current` cell survives. This is the
  executable proof that A-4's identity requirement is load-bearing for ③.
