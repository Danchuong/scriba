# 04 — Animation Authoring Model

How does a `.tex` author express animation intent in Scriba?

---

## Status Quo

Scriba uses a **step-based model**. Each `\step` is a discrete frame. The
user clicks Next/Prev to navigate. All mutation commands within a step
(`\recolor`, `\apply`, `\annotate`, `\cursor`, `\foreach`) execute
simultaneously as an atomic state transition. The emitter produces one SVG
snapshot per frame; the inline JS widget swaps the `<svg>` innerHTML on
button click. CSS transitions on individual elements (cell backgrounds,
border colours) provide a small amount of visual smoothing, but there is
no coordinated animation timeline between changes in a single step.

Relevant code paths:

- `scriba/animation/parser/ast.py` — `FrameIR.commands` is an unordered
  tuple of `MutationCommand`. Nothing encodes timing or sequencing.
- `scriba/animation/scene.py` — `SceneState.apply_frame()` resolves the
  delta for each frame. The output is a flat `FrameSnapshot` dict, not a
  timeline.
- `scriba/animation/emitter.py` — `emit_interactive_html()` builds a
  frames-JSON array where each entry is a pre-rendered SVG string. The
  widget JS does a hard swap: `ss.innerHTML = fd[i].svg`.
- Existing CSS: some cookbook examples already declare `transition:
  background 0.15s` on cells. This is per-element CSS, not orchestrated
  by the `.tex` source.

**Key constraint:** Today the emitter pre-renders every frame on the
server side. The JS widget is a thin frame switcher with no animation
engine. Any authoring model we design must be implementable within this
architecture or define a clear migration path away from it.

---

## Three Candidate Approaches

### Approach A: Fully Automatic (zero author effort)

The runtime computes a diff between frame N and frame N+1. Every property
change receives a default CSS transition. The author writes exactly the
same `.tex` as today.

```tex
\step
\recolor{arr.cell[0]}{state=current}
\apply{dp.cell[1]}{value="4"}
\annotate{dp.cell[1]}{arrow_from="dp.cell[0]", label="+4", color=good}
\narrate{Now we compute dp[1] = 4.}
```

Nothing changes in the source. The emitter and widget internalize all
animation decisions.

#### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Backward compatibility** | Perfect | Existing `.tex` files gain animation with zero edits. |
| **Learning curve** | Zero | No new syntax to learn. |
| **Expressiveness** | Low | All changes are parallel with identical duration. No way to express "recolor first, then draw the arrow". No stagger, no speed per-command. |
| **Implementation complexity** | Medium | Requires moving from full-SVG swap to a stable-DOM diffing model. Each element needs a persistent `id` across frames so CSS transitions fire. The emitter must output a single SVG per scene with per-element state attributes, not N separate SVGs. |
| **Interaction with existing commands** | Transparent | `\recolor`, `\apply`, `\annotate`, `\cursor`, `\foreach` all work as before. |
| **Step backward (Prev)** | Simple | Reverse diff applies the same transitions in reverse. CSS `transition` is direction-agnostic. |

#### Limitations that matter

Competitive programming editorials often have steps where two things
happen in a meaningful order: "mark the current cell, *then* update the
DP value". With Approach A, both fire at once. For simple walkthroughs
this is fine. For steps with 4+ changes it becomes visual noise — the
viewer cannot tell what caused what.

---

### Approach B: Explicit Animation Commands (maximum control)

Every animated property change uses a new `\animate` command with
duration, delay, and easing parameters.

```tex
\step
\animate{arr.cell[0]}{state=current, duration=300, easing=ease-out}
\animate{dp.cell[1]}{value="4", duration=200, delay=100}
\animate{dp.cell[1]}{arrow_draw, duration=400, delay=300}
\narrate{Now we compute dp[1] = 4.}
```

#### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Backward compatibility** | None | Existing `\recolor`/`\apply`/`\annotate` commands produce no animation. Authors must rewrite every step with `\animate`. |
| **Learning curve** | High | Authors must understand duration, delay, easing, and how they compose. This is animation authoring, not algorithm explanation. |
| **Expressiveness** | Full | Can express any timing, any ordering, any easing. |
| **Implementation complexity** | High | New AST node, new parser path, timeline resolver in the emitter, full JS animation engine in the widget. |
| **Interaction with existing commands** | Replaces them | `\animate` would need to subsume every mutation type (`state=`, `value=`, `arrow_draw`, `hide`, etc.). Duplicates the surface area. |
| **Step backward (Prev)** | Complex | Reversing an arbitrary timeline with varying delays requires either replaying in reverse or snapping to the previous frame state. |

#### Why this is wrong for Scriba

Scriba's audience is competitive programmers and coaches writing
editorials. They care about algorithmic correctness, not keyframe curves.
Approach B turns every author into an animator. It also breaks the
existing corpus: every `.tex` file that works today would need a rewrite
to gain animation. This violates the principle of progressive
enhancement.

---

### Approach C: Hybrid (auto defaults + optional override)

All existing commands animate automatically with sensible defaults. New
optional constructs let authors control sequencing when they want to.

```tex
\step[transition=300ms]
\recolor{arr.cell[0]}{state=current}  % animates over 300ms
\apply{dp.cell[1]}{value="4"}         % animates over 300ms, parallel
\annotate{dp.cell[1]}{arrow_from="dp.cell[0]", label="+4", color=good}
\narrate{Now we compute dp[1] = 4.}
```

For ordering control:

```tex
\step[transition=250ms]
\sequence{
  \recolor{arr.cell[0]}{state=current}    % plays first (250ms)
  \recolor{arr.cell[1]}{state=done}       % plays after first finishes
}
\apply{dp.cell[1]}{value="4"}             % parallel with the sequence
\narrate{...}
```

For staggered bulk operations:

```tex
\step[transition=200ms]
\stagger{40ms}{
  \recolor{arr.cell[0]}{state=done}
  \recolor{arr.cell[1]}{state=done}
  \recolor{arr.cell[2]}{state=done}
  \recolor{arr.cell[3]}{state=done}
}
\narrate{Mark all visited cells as done.}
```

For per-command override:

```tex
\annotate{dp.cell[1]}{arrow_from="dp.cell[0]", label="+4", color=good,
                       transition=500ms}
```

For instant snap (backward compatibility):

```tex
\step[transition=0]     % everything snaps, identical to today's behavior
```

#### Evaluation

| Criterion | Rating | Notes |
|-----------|--------|-------|
| **Backward compatibility** | Full | If the global default is `transition=0` (or a config flag defaults to `auto`), every existing `.tex` works unchanged. Authors opt in by adding `transition=Nms` to `\step` or to the environment header. |
| **Learning curve** | Low-to-medium | Zero for basic use (just set `transition=250ms` on the step). `\sequence` and `\stagger` are optional power-user features; most authors never need them. |
| **Expressiveness** | High | Parallel (default), sequential (`\sequence`), staggered (`\stagger`), per-command duration override, per-step speed. Covers 95% of editorial animation needs without exposing easing curves or keyframes. |
| **Implementation complexity** | Medium | The parser gains three new constructs (`\sequence`, `\stagger`, and the `transition` option). The emitter must produce a stable DOM with CSS transition properties keyed to a timeline computed from these constructs. The JS widget needs a small timeline player instead of a hard innerHTML swap. Importantly, this is a superset of Approach A's implementation — we build the auto-diff engine first, then layer the override constructs. |
| **Interaction with existing commands** | Additive | `\recolor`, `\apply`, `\annotate`, `\cursor` keep their semantics. They gain a `transition` optional param. `\foreach` body commands inherit the step's transition. `\sequence` and `\stagger` are grouping wrappers around existing commands. |
| **Step backward (Prev)** | Manageable | The widget stores the target state for each frame. Clicking Prev sets the target state of the previous frame and lets CSS transitions handle the visual. No need to reverse a timeline — just transition to a known snapshot. |

---

## Recommendation: Approach C (Hybrid)

Approach C is the right design for Scriba. The rationale:

1. **The audience is not animators.** Competitive programming authors
   want to write `\step`, `\recolor`, `\apply`, and have it look good.
   Approach C delivers this: add `transition=250ms` to the environment
   header and every step animates. Done.

2. **Progressive enhancement preserves the corpus.** Hundreds of existing
   `.tex` files compile unchanged. Animation is opt-in at the environment
   or step level. No migration required.

3. **Sequencing is the one thing auto-animation gets wrong.** When a step
   has multiple changes, the viewer needs to see them in a pedagogically
   meaningful order. `\sequence{}` solves this without requiring the
   author to specify milliseconds — it just means "play these one after
   another, each using the step's transition duration." This is the
   minimal construct that unlocks narrative animation.

4. **Stagger handles bulk operations.** DP walkthroughs, BFS level
   marking, and array sweeps routinely recolor 5-20 cells in one step.
   `\stagger{40ms}{}` makes this a wave instead of a flash. Without
   stagger, the only alternative is splitting into N steps (destroying
   the narrative) or accepting a simultaneous blink (ugly).

5. **Implementation is incremental.** Phase 1 builds the auto-diff
   engine (Approach A). Phase 2 adds `\sequence`/`\stagger` parsing.
   Phase 3 adds per-command `transition` overrides. Each phase ships
   independently.

---

## Detailed Design

### New Syntax Elements

#### Environment-level default

```tex
\begin{animation}[transition=250ms]
  ...
\end{animation}
```

Sets the default transition duration for every step in this animation.
Equivalent to writing `transition=250ms` on each `\step`. Overridable
per-step.

When omitted, the default is `transition=auto`. `auto` means the runtime
picks sensible per-command defaults (see table below). `transition=0`
means instant snap (today's behavior).

#### Step-level override

```tex
\step[transition=500ms]
\step[transition=0]        % snap this step, even if env default is 250ms
\step[speed=2x]            % halve all durations in this step
```

`speed` is a multiplier applied to all durations within the step. `2x`
means twice as fast (durations halved). `0.5x` means half speed (durations
doubled). Composes with per-command overrides.

#### `\sequence{}` — ordered group

```tex
\sequence{
  \recolor{arr.cell[0]}{state=done}     % phase 1
  \apply{dp.cell[1]}{value="4"}         % phase 2 (starts after phase 1)
  \annotate{dp.cell[1]}{...}            % phase 3
}
```

Commands inside `\sequence` play one after another. Each command uses the
step's transition duration. The total time is `N * transition_duration`.

`\sequence` is a **grouping construct**, not a new command type. It
contains existing mutation commands. It cannot be nested inside another
`\sequence` (flat only — keeps the model simple).

Commands outside `\sequence` in the same step run in parallel with the
sequence (starting at t=0).

#### `\stagger{offset}{}` — offset group

```tex
\stagger{40ms}{
  \recolor{arr.cell[0]}{state=done}    % starts at t=0
  \recolor{arr.cell[1]}{state=done}    % starts at t=40ms
  \recolor{arr.cell[2]}{state=done}    % starts at t=80ms
}
```

Each command starts `offset` after the previous one. All commands use the
step's transition duration. Unlike `\sequence`, commands overlap — the
second starts before the first finishes (if `offset < transition`).

`\stagger` composes with `\foreach`:

```tex
\stagger{30ms}{
  \foreach{i}{range(n)}
    \recolor{arr.cell[${i}]}{state=done}
  \endforeach
}
```

The expanded commands inherit stagger offsets in expansion order.

#### Per-command `transition` override

Any mutation command accepts an optional `transition` parameter:

```tex
\annotate{dp.cell[1]}{..., transition=500ms}   % slower arrow draw
\recolor{arr.cell[0]}{state=current, transition=0}  % instant snap
```

This overrides the step-level default for that single command.

### Default Transition Durations (`transition=auto`)

When the environment or step uses `transition=auto`, each command type
gets a tuned default:

| Command | Property | Default duration | Easing | Visual |
|---------|----------|-----------------|--------|--------|
| `\recolor` | `state` change | 200ms | ease-out | Background/border colour crossfade |
| `\apply` | `value` change | 150ms | ease-out | Old value fades out, new fades in (crossfade) |
| `\apply` | `label` change | 150ms | ease-out | Text crossfade |
| `\annotate` | arrow draw | 300ms | ease-out | SVG path stroke-dashoffset animation |
| `\annotate` | label appear | 200ms | ease-out | Fade-in + slight translate-Y |
| `\cursor` | move | 250ms | ease-in-out | Previous cell dims while new cell highlights |
| `add_edge` (graph) | draw | 400ms | ease-out | Stroke-dashoffset draw-in |
| `reparent` (tree) | position | 500ms | ease-in-out | Position lerp (transform translate) |
| `\highlight` | glow | 150ms | ease-out | Box-shadow or outline fade-in |

**Total frame budget:** The runtime computes the total animation time for
a step (accounting for sequences, staggers, and parallel groups). If it
exceeds 1200ms, a parser warning is emitted: "Step N animation exceeds
1.2s — consider splitting into multiple steps or increasing speed." This
is a warning, not an error. Long animations are legal; the author should
be aware they exist.

### Speed Control

#### Per-step speed

```tex
\step[speed=2x]           % all durations halved
\step[speed=0.5x]         % all durations doubled
```

`speed` is a divisor applied to every computed duration in the step
(including `auto` defaults, explicit `transition=Nms` values, and
`\stagger` offsets). This gives the author a single knob to compress or
expand time without rewriting individual values.

#### Widget speed control

The rendered widget exposes a speed toggle in the controls bar:

```
[Prev]  Step 3 / 12  [Next]   [1x ▾]
                                 0.5x
                                 1x
                                 2x
```

The widget multiplier composes with the per-step speed. If the `.tex`
says `speed=2x` and the viewer selects 0.5x in the widget, the effective
speed is 1x. Implementation: the widget multiplier scales all CSS
`transition-duration` values at render time via a CSS custom property:

```css
.scriba-widget { --scriba-speed: 1; }
.scriba-widget [data-transition] {
  transition-duration: calc(var(--base-duration) / var(--scriba-speed));
}
```

The JS changes `--scriba-speed` when the dropdown is toggled.

### Autoplay Mode

```tex
\begin{animation}[autoplay=true, interval=2000]
  ...
\end{animation}
```

- `autoplay=true` — the widget starts playing automatically on load.
- `interval=Nms` — time between steps (default: 2000ms).
- The interval timer does not start until the current step's animation
  completes. If a step's animation takes 800ms and `interval=2000`, the
  next step fires at t=2800ms.
- A visible play/pause button replaces the Next button during autoplay.
  Clicking any navigation control pauses autoplay.
- Keyboard: Space toggles play/pause. Arrow keys override autoplay.

### Print / Static Mode

Animations must degrade gracefully for `@media print` and for static
HTML export (e.g., PDF generation).

Design: the CSS custom property `--scriba-speed` is set to `infinity` in
print media, which collapses all transitions to 0ms:

```css
@media print {
  .scriba-widget { --scriba-speed: 9999; }
}
```

All elements render in their final state for each frame. The widget
layout switches from interactive carousel to a vertical filmstrip (one
frame per block, stacked). This is the existing `layout=filmstrip`
behaviour — no author action needed.

The `.tex` author never needs to think about print mode. It is automatic.

### Interaction with `\foreach`

`\foreach` expands its body commands before animation timing is applied.
The expanded commands are treated as individual mutation commands for
timing purposes. This means:

```tex
\stagger{30ms}{
  \foreach{i}{[0,1,2,3]}
    \recolor{arr.cell[${i}]}{state=done}
  \endforeach
}
```

expands to four `\recolor` commands, each staggered by 30ms. The
expansion happens at parse/eval time (as today); the stagger is applied
at emit time.

`\foreach` inside `\sequence` works similarly: expanded commands become
sequential phases.

### Interaction with `\cursor`

`\cursor` already encodes a two-part state change (dim the old cell,
highlight the new cell). Under animation, these two sub-operations play
as a short sequence: dim begins, then highlight begins after a brief
overlap (50ms offset by default). This is handled internally — the
author does not need to wrap `\cursor` in `\sequence`.

### Interaction with `\substory`

Substories are self-contained animation contexts. A substory inherits
the parent animation's `transition` default but can override it:

```tex
\substory[title="Relaxation", transition=150ms]
  \step
  ...
\endsubstory
```

Substory transitions are independent of the parent step. When the user
navigates the parent and enters a substory, the substory plays its own
timeline.

---

## AST Impact

The following changes to `scriba/animation/parser/ast.py` are needed:

- `AnimationOptions`: add `transition: str | None` (e.g., `"250ms"`,
  `"auto"`, `"0"`) and `autoplay: bool`, `interval: str | None`.
- `StepCommand`: add `transition: str | None` and `speed: str | None`.
- `FrameIR`: add `sequence_groups` and `stagger_groups` fields (or
  represent them as wrapper command types).
- New AST nodes: `SequenceGroup` and `StaggerGroup`, each wrapping a
  tuple of `MutationCommand`.
- Mutation commands: each gains an optional `transition: str | None`
  field for per-command override.

The `MutationCommand` union grows to include `SequenceGroup` and
`StaggerGroup`. The scene materializer (`scene.py`) ignores these
wrappers when computing state (they are transparent for delta
resolution). The emitter reads them when computing the animation
timeline.

---

## Migration Path

**Phase 0 (no change):** Ship nothing. Existing `.tex` files work.

**Phase 1 — Auto-diff engine:** Move from full-SVG swap to stable-DOM
diffing. Each SVG element gets a persistent `id` derived from its
selector (e.g., `arr-cell-0`). The widget JS patches element attributes
instead of replacing innerHTML. CSS transitions on patched attributes
provide automatic animation. The `.tex` source is unchanged. The
environment default is `transition=auto`. This alone delivers 80% of the
visual improvement.

**Phase 2 — `\sequence` and `\stagger`:** Parse the new grouping
constructs. The emitter computes per-element delay values and emits them
as `transition-delay` CSS. Small parser addition, small emitter change.

**Phase 3 — Per-command `transition`, `speed`, autoplay:** Incremental
additions to the option parser. Each feature is independent and can ship
in any order.

**Phase 4 — Widget speed control:** Pure frontend work. Add the speed
dropdown, wire it to `--scriba-speed`.

---

## Worked Example

A DP editorial step that fills `dp[3]` by taking the max of two
candidates:

```tex
\begin{animation}[transition=auto]

\shape{arr}{Array}{values=[3,1,4,1,5]}
\shape{dp}{Array}{values=[0,0,0,0,0], label="dp"}

\step
\narrate{Consider dp[3]. We compare dp[2]+arr[3] vs dp[1]+arr[3].}
\sequence{
  \recolor{arr.cell[3]}{state=current}
  \recolor{dp.cell[2]}{state=compare}
  \recolor{dp.cell[1]}{state=compare}
}

\step
\narrate{dp[2]+arr[3] = 4+1 = 5 wins. Set dp[3] = 5.}
\sequence{
  \annotate{dp.cell[3]}{arrow_from="dp.cell[2]", label="+1", color=good}
  \apply{dp.cell[3]}{value="5"}
  \recolor{dp.cell[3]}{state=done}
}
\recolor{dp.cell[2]}{state=default}
\recolor{dp.cell[1]}{state=default}

\end{animation}
```

**What the viewer sees on step 1:**

- t=0ms: `arr.cell[3]` background crossfades to "current" (200ms)
- t=200ms: `dp.cell[2]` background crossfades to "compare" (200ms)
- t=400ms: `dp.cell[1]` background crossfades to "compare" (200ms)
- Total: 600ms. The narration text is visible from t=0.

**What the viewer sees on step 2:**

- t=0ms: `dp.cell[2]` and `dp.cell[1]` snap back to default (parallel, 200ms)
- t=0ms: the annotation arrow draws in (300ms)
- t=300ms: `dp.cell[3]` value crossfades to "5" (150ms)
- t=450ms: `dp.cell[3]` background crossfades to "done" (200ms)
- Total: 650ms.

The author wrote 12 lines of `.tex` and got a 1.25-second choreographed
animation across two steps. No millisecond values were specified (all
`auto` defaults). The `\sequence` blocks were the only animation-specific
additions, and they read naturally: "do these things in order."

---

## What We Deliberately Exclude

- **Easing curves as author-facing syntax.** Authors should not write
  `cubic-bezier(0.16, 1, 0.3, 1)`. The runtime picks good defaults.
  If we ever need per-command easing, it can be a named preset:
  `easing=bounce`, `easing=spring`. Not in v1.

- **Keyframe animation.** No `@keyframes`-style multi-stop definitions.
  Scriba animations are state transitions, not motion graphics.

- **Camera/viewport animation.** No pan, zoom, or scroll-to-element.
  The viewport is fixed. If the scene is too large, the author uses
  `\substory` or splits into multiple animations.

- **Audio/sound.** Out of scope.

- **Looping/repeating steps.** Not a common editorial pattern. Can be
  added later as `\step[repeat=3]` if needed.

---

## Summary of New Author-Facing Syntax

| Syntax | Required? | Purpose |
|--------|-----------|---------|
| `transition=Nms` on `\begin{animation}` | No | Set default duration for all steps |
| `transition=Nms` on `\step` | No | Override duration for one step |
| `transition=0` | No | Disable animation (snap), backward compat |
| `speed=Nx` on `\step` | No | Scale all durations in a step |
| `\sequence{...}` | No | Play enclosed commands one after another |
| `\stagger{Nms}{...}` | No | Offset each enclosed command by N ms |
| `transition=Nms` on any command | No | Override duration for one command |
| `autoplay=true` on `\begin{animation}` | No | Auto-advance steps |
| `interval=Nms` on `\begin{animation}` | No | Time between auto-advance |

Every item in this table is optional. An author who writes zero new
syntax gets either today's snap behavior (if `transition` is unset and
the global default remains 0) or automatic animation (if the global
default is changed to `auto`). The recommendation is to default to `auto`
in a new major version, with a one-line config to revert to snap for
authors who prefer it.
