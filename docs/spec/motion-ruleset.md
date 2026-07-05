# Motion Ruleset (A-1 … A-8)

> Companion to [smart-label-ruleset.md](./smart-label-ruleset.md) (pill placement) and
> the R-32 stability rule. Where the R-rules govern *what a decoration is and where its
> label sits*, the **A-rules govern how anything on stage MOVES between two
> server-authored frames**. The two are orthogonal layers: a decoration can carry its own
> Python plumbing yet be fully unified at the motion layer.
>
> Card format mirrors the R-cards (`### A-N — Title` / **Normative** / **Since** / prose /
> **Code ref** / **Test ref**) so `scripts/check_ruleset_sync.py` verifies these anchors the
> same way it verifies the R-cards. Refs that name machinery landing in the same
> v0.23.0-dev motion phase (reverse manifest, emphasis/cursor handlers, `\ref`/`\focus`)
> are marked `pending v0.23.0-dev` until their commit lands, then flipped to a real
> `path:anchor`.
>
> Cross-links: **R-32** (layout stability — the A-6 prerequisite) and **R-30**
> (one-dispatcher routing — the A-1 analogue).

---

## A-0 — The invariant axes (premises)

Six axes hold in the shipped runtime today. Every A-rule below is derived from them, and
every motion feature — present or future — is judged by "does it preserve axis Y". These are
premises, not normative cards; each carries its own `path:line` anchor.

| Axis | Statement | Anchor |
|---|---|---|
| **A-0.i — Stage is data** | A frame is the tuple `{svg, narration, substory, tr, fs}` shipped as a JSON island. The runtime is structure-driven — it sees only `data-target` / `data-annotation` / `data-shape` attributes and a `kind` string, never "this is a Queue". | `scriba/animation/_html_stitcher.py` (`_needs_sync`, frame serialization); `scriba/animation/static/scriba.js` (`_applyTransition`) |
| **A-0.ii — Identity = key** | Cross-frame identity is the selector on `data-target` (cells/nodes) or the composite key on `data-annotation` (decorations). All motion is a **diff on identity**: the differ matches prev/curr by key → `[target, prop, from, to, kind]`; the runtime resolves the selector and mutates it. | `scriba/animation/differ.py` (`_diff_shape_states`); `scriba/animation/static/scriba.js` (`_applyTransition`) |
| **A-0.iii — Lifecycle** | Highlights are ephemeral (cleared each `\step`); annotations & traces persistent-by-default, ephemeral if flagged; structural pushes ephemeral per-frame. | `scriba/animation/scene.py` (`apply_frame` ephemeral clear) |
| **A-0.iv — Measured == painted** | The WAAPI tween is cosmetic; when the server SVG differs (`fs=1`) the runtime snaps `innerHTML` to the server bytes at settle. The destination is **always** the server frame, never a JS approximation. | `scriba/animation/_html_stitcher.py` (`svg_changed`); `scriba/animation/static/scriba.js` (`animateTransition`) |
| **A-0.v — Color = token-ref** | State is a CSS class (`scriba-state-X` / `scriba-annotation-state-X`); the runtime swaps class **names**, not colors, so dark-theme adaptation is free (R-36). | `scriba/animation/static/scriba.js` (`_applyTransition`); `scriba/animation/static/scriba-scene-primitives.css` (`--scriba-annotation-state-current`) |
| **A-0.vi — Opt-in → byte-stable** | Motion features are additive; `SCRIBA_VERSION` bumps only when *existing* bytes move — for motion that means the shared `scriba.js` (+ its verbatim inline slice) or the `{svg,…,tr,fs}` schema changes. A new command emitting only existing kinds ships with no bump. | `scriba/_version.py` |

---

## The A-rules (A-1 … A-8)

Each is a MUST for any motion, existing or future. Rationale ties to the confirmed substrate.

### A-1 — Motion is a pure function of an identity diff

**Normative:** MUST
**Since:** v0.23.0

The only way to produce animation is `compute_transitions(prev, curr)` → an ordered list of
`Transition[target, prop, from, to, kind]`, applied by a stateless kind→handler dispatch. A
command never "animates"; it mutates scene state and motion **falls out of the diff**. This
preserves A-0.i/.ii — every present and future feature reduces to "what identity changed, and
how", so one runtime serves all. Satisfied today for forward-adjacent steps; reverse and jump
(A-2) generalize the *dispatch*, not the diff.

**Code ref:** `scriba/animation/differ.py:compute_transitions`;
`scriba/animation/static/scriba.js:_applyTransition`.
**Test ref:** `tests/unit/test_keyframes.py`;
`tests/unit/test_animation_scene.py`.

### A-2 — Closed kind registry; every kind declares an inverse

**Normative:** MUST
**Since:** v0.23.0

The transition `kind` is drawn from a **closed** registry
(`recolor`, `value_change`, `highlight_on/off`, `element_add/remove`,
`annotation_add/remove/recolor`, `position_move`, `cursor_move`); the registry MUST stay closed **under
inversion** — every kind has an inverse in the set (`add↔remove`, `on↔off`, and the rest
self-inverse under a from/to swap). **Reverse and jump playback MUST be the inverse manifest
applied**, never a new emit path: stepping `cur → cur-1` inverts `frames[cur].tr`
(swap `from/to`, map `add↔remove` / `on↔off`) and feeds it to the *unchanged* handlers. A new
kind ships only as the triple `{emit, JS handler, inverse}`. The inverse of a draw-on
(`annotation_add`) is defined **semantically** as the shipped `annotation_remove` fade — not a
pixel-time-reversed un-draw. A new kind must not break closure (guards `\string`/`\heap`, which
add no new kind at all).

**Code ref:** `scriba/animation/differ.py:Transition`;
reverse manifest `scriba/animation/static/scriba.js` `_invertManifest` / `_INV_KIND`
(pending v0.23.0-dev, motion-runtime phase).
**Test ref:** `tests/unit/test_keyframes.py`;
reverse-manifest pins `tests/unit/test_runtime_reverse.py` (pending v0.23.0-dev).

### A-3 — Emphasis is a channel disjoint from state

**Normative:** MUST
**Since:** v0.23.0

Emphasis (pulse, tint, defocus) is transient salience that (a) never writes persistent
`shape_states` / `annotations`, (b) self-expires within the step, (c) leaves the resting SVG
**byte-identical** to the un-emphasised frame, and (d) uses **compositor-only** props —
`transform` / `opacity`, never a layout property (`width`, `height`, `font-size`). Because
`bounding_box()` is untouched the full-sync flag stays 0 and R-32 reflow is unthreatened. The
baked emphasis class scales about the element's own box (`transform-box: fill-box`) so an SVG
`<g>` pulse does not also translate; its resting keyframe is `scale(1)`, so a statically shown
frame equals one with no emphasis. Today's `value_change` scale-bounce is proto-emphasis; the
first-class channel is the CSS `.scriba-emphasis` / `.scriba-defocused` classes plus the
runtime jump-pulse. Modeling emphasis as *state* would churn goldens and threaten R-32.

**Code ref:** `scriba/animation/static/scriba.js:_applyTransition`
(proto-emphasis `value_change` scale-bounce);
`scriba/animation/static/scriba-scene-primitives.css` (`.scriba-emphasis`, `.scriba-defocused`
— this phase); runtime jump-pulse `_emphasize` (pending v0.23.0-dev, motion-runtime phase).
**Test ref:** `tests/unit/test_runtime_unified.py`
(runtime byte-lock / source-inspection);
emphasis pins `tests/unit/test_runtime_reverse.py` (pending v0.23.0-dev).

### A-4 — A marker is a decoration with identity; its motion is a slide

**Normative:** MUST
**Since:** v0.23.0

A cursor/pointer that persists and MOVES is an addressable **decoration** (stable
`data-annotation` key `{shape}.cursor[{id}]-solo`), not a state that hops between cells.
Multiple markers are distinct identities. Today's `\cursor{targets}{index}` is a stateless
two-recolor hop — it rewrites cell *states*, so two cursors sharing `curr_state` collide (the
second demotes the first); binding named carets therefore **requires identity**. The named form
is strictly additive and opt-in (discriminated by the `id=` key) so the legacy state-hop and its
~232-token golden surface stay byte-identical (see R-38). A moving caret rides a dedicated
`cursor_move` slide, distinct from `position_move` only in the identity space it resolves:
`cursor_move` glides a `[data-annotation]` decoration, `position_move` a `[data-target]`
cell/node. Both now share one canonical geometry — `translate(0,0)→translate(to-from)`, so the
tween **ends at the new seat** and the full-SVG snap only reaffirms it (v0.24.0 gave
`position_move` this glide too, curing its old ends-at-old-seat lurch). The caret's
`<polygon>`/`<text>` are painted by the R-36 annotation-state classes, so no new color code and
no new CSS are needed.

**Code ref:** `scriba/animation/scene.py:_apply_cursor`
(legacy recolor-hop, the additive boundary);
`scriba/animation/differ.py:_diff_shape_states` (`position_move` source);
new caret `differ.py` `_diff_cursors`, `base.py` `emit_cursors_under`,
`scriba.js` `cursor_move` (pending v0.23.0-dev, multi-cursor phase).
**Test ref:** `tests/unit/test_cursor_command.py`
(legacy byte-stability);
new-form caret pins `tests/unit/test_multicursor.py` (pending v0.23.0-dev, multi-cursor phase).

### A-5 — A frame macro expands to indistinguishable hand-frames

**Normative:** MUST
**Since:** v0.23.0

A frame generator (`\playeach`) MUST expand at **scene-build time** to the same frame sequence a
hand-authored `\step` list would produce — identical snapshots, identical `tr`/`fs`, identical
step count. **No runtime-only frames.** The macro is front-end sugar over `apply_frame`, exactly
as `\foreach` is sugar over command expansion; a generated frame and a hand frame must be
byte-indistinguishable downstream or the differ / measure invariants fork. Each iteration is a
real `\step` counted in the total, with narration templated per loop var, and MUST NOT cross a
substory boundary.

**Code ref:** `scriba/animation/scene.py:apply_frame`
(the frame builder the macro desugars into);
`scriba/animation/parser/_grammar_playeach.py:_parse_playeach`
(the parser-level expander that emits one `FrameIR` per swept element).
**Test ref:** `tests/unit/test_animation_scene.py`;
`tests/unit/test_playeach.py`
(N-frame expansion + byte-for-byte indistinguishability from hand `\step`s).

### A-6 — Layout mutation goes through prescan; the resting frame is server truth

**Normative:** MUST
**Since:** v0.23.0

Any insert / reflow / grow MUST widen the reserved envelope via the build-time prescan
(monotonic value-width prescan + cross-frame `measure_scene_layout`) so R-32.1–.4 hold for
**every** frame, and MUST carry `fs=1` so the runtime resyncs to the exact server SVG after the
cosmetic `position_move`. An insert that grows the structure mid-scene otherwise jumps every
later frame — the exact displacement R-32 forbids. **Sentinel slots are addressable from
declaration** (a real `data-target` reserved at t0), never runtime-injected, so an inserted cell
is a placement citizen that measures and glides within the reserved envelope.

**Code ref:** `scriba/animation/_frame_renderer.py:_prescan_value_widths`,
`measure_scene_layout`;
`scriba/animation/_html_stitcher.py:svg_changed` (the `fs` flag);
sentinel addressability + insert `position_move` (pending v0.23.0-dev, layout-mutation phase).
**Test ref:** `tests/unit/test_stability.py` (R-32 layout stability);
sentinel/insert pins (pending v0.23.0-dev, layout-mutation phase).

### A-7 — Narration binds identity through the same selector algebra

**Normative:** MUST
**Since:** v0.23.0

A narration reference (`\ref{sel}{text}`) MUST resolve through the **same** selector→identity
algebra decorations use — no parallel "narration target" grammar — producing (a) an emphasis
(A-3) on the referenced node and (b) tinting the word with the target's current-frame state ink.
The ink is the WCAG-AA `--scriba-annotation-state-*` family (R-36), because the word sits on the
page background, not a colored pill; a target with no signal state takes the info ink. A single
aria-live channel (narration) carries the announcement, fired **after** the visual settles, so
there is no double-announce. Bad/undeclared selectors degrade softly to plain text with a
warning — a narration typo must never blank a render.

**Code ref:** `scriba/animation/extensions/ref_macro.py:process_ref_macros`
(the shipped narration macro); `scriba/animation/renderer.py:_render_narration`
(pass-1 stash wiring + `state_of` closure);
`scriba/animation/_frame_renderer.py:_expand_selectors`
(the shared selector algebra `\ref` reuses);
`scriba/animation/static/scriba-scene-primitives.css` (`.scriba-ref`, `.scriba-ref-state-*`).
**Test ref:** `tests/unit/test_ref_macro.py:TestRefMacroUnit`
(state→class mapping, idle/unknown degrade, `$math$`);
`tests/unit/test_state_color_leader.py`
(the annotation-state ink tokens `\ref` reuses, both themes).

### A-8 — Reduced-motion / print / no-JS is ground truth; motion is progressive enhancement

**Normative:** MUST
**Since:** v0.23.0

Every kind (existing + new) MUST render correctly with animation disabled: the server SVG at
rest already shows the destination, so disabling the tween loses only the interpolation.
Emphasis (A-3) MUST be instant / no-op under reduced-motion — the `.scriba-emphasis` pulse is
killed outright so the element rests at `scale(1)`, and `.scriba-defocused` keeps its static dim
but drops the fade — while the aria-live announcement (A-7) still fires. Draw-ons, fades and
pulses are pure enhancement over an already-correct static frame; that is what lets emphasis stay
stateless and reversible. New kinds prove this before merge.

**Code ref:** `scriba/animation/static/scriba.js:_canAnim`
(the reduced-motion gate), `snapToFrame`;
`scriba/animation/static/scriba-scene-primitives.css` (`prefers-reduced-motion` emphasis/defocus
overrides — this phase).
**Test ref:** `tests/unit/test_runtime_unified.py`;
`tests/unit/test_runtime_rapid_nav.py`.

---

## Matrix — motion features × A-rules

| Feature | Primary A-rule(s) | New runtime code? | Disposition |
|---|---|---|---|
| Reverse / jump tween | A-2 | yes (generalize the dispatch) | Apply the inverse of `frames[cur].tr`; drop the forward-adjacent gate. |
| Delta-emphasis | A-3 | yes (jump-pulse) | Stateless compositor pulse on the changed identity; `fs=0`. |
| Multi-cursor bind | A-4 | yes (`cursor_move` slide) | Opt-in caret glyph, per-caret `data-annotation` key; legacy hop untouched. |
| `\ref` narrate | A-7 (+A-3) | no (reuses A-3 class) | Tint + aria-live, atomically, after settle. |
| `\focus` | A-3 | no (baked `.scriba-defocused`) | Dim the complement set; ephemeral; resting SVG unchanged. |
| `\playeach` | A-5 | no | Expands to hand-frames at build. |
| Insert / reflow + sentinel | A-6 | no (`position_move` ships) | Sentinel addressable at t0; prescan reserves max width. |
| Plane2D `rotate_*` | A-4 (`position_move`) | no | Rotate computes new coords → mutate-in-place keeps identity → rides `position_move`; the glide is the chord of the rotation arc (small per-step angles read as rotation). **No** new kind. |
| `\string` / `\heap` | A-1/A-2 only | no | Ride existing kinds; carry **no** new motion rule. |

The test the A-rules are meant to pass: a new data structure should need **zero** new motion
vocabulary. Only reverse/emphasis/caret touch the runtime, and those are batched into one
`scriba.js` revision so the corpus re-blesses once.

---

## Version policy

- **`scriba.js` change** (new handler, reverse walk, tuned constants) → the external hash **and**
  the verbatim inline slice both differ → every interactive page's bytes move → `SCRIBA_VERSION`
  bump + full interactive golden re-bless.
- **Frame-schema change** (new field in `{svg, narration, substory, tr, fs}`) → same → bump.
- **New primitive / command emitting only existing kinds** → additive → goldens for opt-in files
  only → **no bump** (unless it ships shared CSS, which regenerates every inlined stylesheet).
- **Recommendation:** spend **one** bump. Land the runtime-touching motion items (reverse,
  emphasis, `cursor_move`) as a single `scriba.js` revision; every later phase is additive Python
  that reuses shipped kinds. The CSS in this phase (`.scriba-emphasis`, `.scriba-defocused`,
  `.scriba-ref*`) is a shared-stylesheet change and regenerates inlined goldens on its own.
