# Label ↔ State Colour Binding — annotation colours, opt-in leaders, and the tint-family question

> Design investigation for JudgeZone feature request (driver: CSES 1071). **No repo source
> modified.** All facts traced against `main` @ 9062239, scriba 0.22.1, `.venv/bin/python`.
> Visual probes rendered in the session scratchpad (`fl_probe.tex` → `.html` → `.png`, light +
> forced `data-theme="dark"`, chrome-headless-shell). Grades: **Confirmed** (read in source /
> rendered), **Deduced** (follows from confirmed facts), **Hypothesized** (needs a probe before
> building).

---

## 1. Hand-off Brief

There are **three** colour systems, not two, and the split is the whole story: the `\recolor`
**state palette** lives only in CSS (`--scriba-state-*`, `scriba-scene-primitives.css:122-154`
light + `:640-672` dark), the `\annotate` **colour palette** lives in *both* a static Python
dict (`ARROW_STYLES`, `_svg_helpers.py:1916-1965`, the no-CSS fallback) *and* CSS tokens
(`--scriba-annotation-*`, `:163-168` light + `:679-684` dark), and — confirmed by a dark-mode
screenshot — **the CSS token wins over the Python presentation attribute** (the code says so at
`:552-554`), so the rendered label colour is the CSS value and it already dark-adapts. The two
palettes only share three names (**good, error, path**); the states the user cares about —
**current (#0070d5), done, dim** — have *no* annotation colour, which is why a label on a blue
`current` cell can only borrow `info` (a near-but-not-equal blue) and a label on a grey `done`
cell can't match at all (`VALID_ANNOTATION_COLORS`/`VALID_STATES` at `constants.py:35-37`/`27-32`).
Problem **A** is real and cheap to fix; problem **B** (leaders) already exists in two gated forms
we can reuse; problem **C** (make `current` a tint chip like the others) is real but touches the
single most-used visual in **82 of 111** example files — recommend shipping A+B and deferring C to
an opt-in palette.

---

## 2. Inventory — the three colour systems (light + dark)

### 2a. `ARROW_STYLES` — Python static dict (no-CSS fallback + weight/size)
`scriba/animation/primitives/_svg_helpers.py:1916-1965`. **6 keys.** Every key carries
`stroke`, `stroke_width`, `opacity`, `label_fill`, `label_weight`, `label_size`. No dark
variant (it is a static module-level dict — dark is handled entirely in CSS). Consumed at
`:2017` (plain arrow), `:2758`/`:2784` (arc arrow), `:3187` (position label); unknown colour →
silent `ARROW_STYLES.get(color, ARROW_STYLES["info"])`. **Confirmed.**

| key | stroke / label_fill | weight | size | opacity | stroke_width |
|---|---|---|---|---|---|
| good  | `#027a55` | 700 | 12px | 1.0 | 2.2 |
| info  | `#506882` | 500 | 11px | 0.7 | 1.5 |
| warn  | `#92600a` | 600 | 11px | 0.8 | 2.0 |
| error | `#c6282d` | 600 | 11px | 0.8 | 2.0 |
| muted | `#526070` | 500 | 11px | 0.7 | 1.2 |
| path  | `#2563eb` | 700 | 12px | 1.0 | 2.5 |

### 2b. `--scriba-annotation-*` — CSS tokens (the colour that actually renders)
Light `:root` `scriba-scene-primitives.css:163-168`; dark `[data-theme="dark"]` `:679-684` and
`@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` `:690+`. Applied via
`.scriba-annotation-{color} > text {fill}` and `> path, > line {stroke}` at `:517-539`.
**Confirmed.**

| token | light | dark |
|---|---|---|
| info  | `#0b68cb` | `#70b8ff` |
| warn  | `#92600a` | `#ffc53d` |
| good  | `#2a7e3b` | `#65ba74` |
| error | `#c6282d` | `#ff6369` |
| path  | `#0b68cb` | `#a78bfa` |
| muted | `var(--scriba-fg-muted)` | `var(--scriba-fg-muted)` |

**Precedence (Confirmed, load-bearing).** `<text fill="{l_fill}">` (`:1603`,`:1690`) and the
arrow `<path stroke="{s_stroke}">` (`:2858`) are SVG **presentation attributes**, which have
lower specificity than any stylesheet rule — the code states this explicitly at `:552-554`
("Inline SVG presentation attributes … have LOWER CSS specificity than any stylesheet rule").
So when the CSS loads, `--scriba-annotation-*` overrides Python; when it doesn't (raw SVG),
Python is the fallback. **Verified in the dark screenshot**: the "current cell" label rendered
`#70b8ff` (dark info token), not the static `#506882` — CSS won and dark-adapted.

**Drift (Deduced).** Python 2a and CSS-light 2b disagree for `info` (`#506882` vs `#0b68cb`),
`path` (`#2563eb` vs `#0b68cb`), `good` (`#027a55` vs `#2a7e3b`). Not a *rendered* bug (CSS wins),
but the two are "manually kept in sync" and currently diverged — the fallback is lower-fidelity
than the real render. Any A fix should add to **both**.

**Coverage gaps (Confirmed).** The colour CSS only styles `> text` and `> path, > line`. It does
**not** cover the arrowhead `<polygon>` (`:2864`), the arc leader `<polyline>`/dot `<circle>`
(`:2618-2627`), or the pill border `<rect stroke>` (`:2587`). Those keep the static Python
`s_stroke` (light) and therefore **do not dark-adapt** — a latent cosmetic bug and a design
constraint for B (prefer `<line>` for new leaders, since `> line` *is* covered).

### 2c. `--scriba-state-*` — CSS tokens (the `\recolor` palette)
Light `:root` `scriba-scene-primitives.css:122-154`; dark `:640-672` (+ prefers dup `:699+`).
Per state: `-fill`, `-stroke`, `-text`. Applied via plain class-child selectors
`.scriba-state-X > rect:not(.scriba-graph-pill), > circle {fill; stroke; stroke-width}` at
`:200-321`. **No `:where()` wrapper** — the brief's "0.8.0 `:where()` specificity" assumption is
not present in the current state rules; they are ordinary class selectors (still beat
presentation attributes). **Confirmed.**

| state | light fill / stroke / text | dark fill / stroke / text | shape |
|---|---|---|---|
| idle | `#f8f9fa` / `#dfe3e6` / `#11181c` | `#1a1d1e` / `#313538` / `#ecedee` | 1px neutral |
| **current** | **`#0070d5`** / `#0b68cb` / **`#ffffff`** | **`#0070d5`** / `#70b8ff` / **`#ffffff`** | **SOLID fill, white text, 2px** |
| done | `#e6e8eb` / `#c1c8cd` / `#11181c` | `#2b2f31` / `#4c5155` / `#ecedee` | tint, 1px |
| dim | `#f1f3f5` / `#e6e8eb` / `#687076` (+opacity .5, saturate .3) | `#202425` / `#2b2f31` / `#9ba1a6` | tint, faded |
| error | `#f8f9fa` / `#e5484d` / `#11181c` | `#1a1d1e` / `#ff6369` / `#ecedee` | tint, red border, 2px |
| good | `#e6e8eb` / `#2a7e3b` / `#11181c` | `#2b2f31` / `#65ba74` / `#ecedee` | tint, green border, 2px |
| highlight | `#f8f9fa` / `#0090ff` / `#0b68cb` | `#1a1d1e` / `#0090ff` / `#70b8ff` | tint, 2px |
| path | `#e6e8eb` / `#c1c8cd` / `#5e6669` | `#2b2f31` / `#4c5155` / `#9ba1a6` | tint, 1px |
| hidden | (not rendered — element skipped) | — | — |

### 2d. State ↔ annotation-colour comparison (the gap)

| name | is a `\recolor` state? | is an `\annotate` colour? | verdict |
|---|:--:|:--:|---|
| good | ✅ | ✅ | **matches** — label green ≈ cell green border |
| error | ✅ | ✅ | **matches** — label red ≈ cell red border |
| path | ✅ | ✅ | matches by name (hues differ: state text `#5e6669` grey vs colour `#0b68cb` blue) |
| **current** | ✅ (`#0070d5`) | ❌ | **GAP** — closest is `info` (`#0b68cb`), a different blue |
| **done** | ✅ (grey tint) | ❌ | **GAP** — closest is `muted` (grey) |
| **dim** | ✅ (grey faded) | ❌ | **GAP** — closest is `muted` |
| idle | ✅ | ❌ | gap (rarely annotated) |
| highlight | ✅ | ❌ | gap |
| hidden | ✅ | ❌ | n/a |
| info | ❌ | ✅ | colour-only |
| warn | ❌ | ✅ | colour-only |
| muted | ❌ | ✅ | colour-only |

Sources: `VALID_STATES` `constants.py:27-32`, `VALID_ANNOTATION_COLORS` `constants.py:35-37`.
**Corpus proof (Confirmed):** `\annotate color=` usage in `examples/` is good 162, info 112,
error 48, warn 40, path 26, muted 17 — **zero** current/done/dim, because they are not
expressible. The screenshot below shows the consequence.

**Visual evidence** (`scratchpad/fl_probe.png` light, `fl_probe_dark.png` dark): five cells
`current / good / done / path / error` with three labels. `good` and `error` labels colour-match
their cells (shared names); the `current` label had to use `info` and is a visibly *different*
blue from the `#0070d5` chip. Both themes render the same mismatch; the dark shot confirms labels
recolour via the CSS tokens.

---

## 3. Design A — make labels colour-match states

### Option (i): extend `ARROW_STYLES` + CSS annotation tokens to add current/done/dim
Add `current`,`done`,`dim` to `VALID_ANNOTATION_COLORS`, to `ARROW_STYLES` (fallback), to
`--scriba-annotation-*` (light **and** dark, hand-authored), and add
`.scriba-annotation-{name} > text/path/line` rules.

- **Cost:** 3 new names × (Python fallback + light token + dark token + CSS rule + contrast
  proof). Moderate, all mechanical.
- **Weakness (Deduced):** the missing states collapse onto hues already taken. `current`'s
  identifying colour `#0070d5` is ~indistinguishable from `info` `#0b68cb`; `done`/`dim` are grey
  ≈ `muted`. You'd ship named colours users can't tell apart, and `done`/`dim`'s light identifying
  colour (`#c1c8cd`, `#e6e8eb`) **fails WCAG on the white pill** (`#c1c8cd` on white ≈ 1.4:1), so
  their label would have to be a darker grey anyway — i.e. `muted`.

### Option (ii) — RECOMMENDED: `color=state:<name>` (label inherits the state's own tokens)
Author writes `\annotate{a.cell[0]}{label=…, color=state:current}`. The label's text/stroke is
driven by a purpose-made CSS var that references the **state** token, so it is guaranteed to match
the cell and **dark-adapts for free** (state tokens already have dark variants — no new dark
authoring).

- **Parser:** at `_grammar_commands.py:234`, branch on `color.startswith("state:")` → validate the
  suffix against `VALID_STATES` (reuse `_raise_unknown_enum`, `grammar.py:394`); store
  `color="state:current"`. Plain colours unchanged.
- **Emit:** when `color` is `state:X`, emit class `scriba-annotation-state-{X}` instead of
  `scriba-annotation-{X}` (`:2849`,`:3656`, plain-arrow `<g>`), and add CSS:
  ```css
  /* light + dark come free because these reference --scriba-state-* which already has both */
  :root { --scriba-annotation-state-current: var(--scriba-state-current-fill);   /* #0070d5, 4.91:1 on white ✓ */
          --scriba-annotation-state-good:    var(--scriba-state-good-stroke);    /* #2a7e3b */
          --scriba-annotation-state-error:   var(--scriba-state-error-stroke);   /* #e5484d — verify on white */
          --scriba-annotation-state-path:    var(--scriba-state-path-text);      /* #5e6669 */
          --scriba-annotation-state-done:    var(--scriba-state-done-text);      /* #11181c — done is "quiet" */
          --scriba-annotation-state-dim:     var(--scriba-fg-muted); }
  .scriba-annotation-state-current > text { fill: var(--scriba-annotation-state-current); }
  .scriba-annotation-state-current > path,
  .scriba-annotation-state-current > line { stroke: var(--scriba-annotation-state-current); }
  /* …one triplet per state… */
  ```
  Each var **picks the legible hue**: `current` → its saturated fill (`#0070d5`, already AA on
  white per `:115`); `good`/`error` → their border; `done`/`dim` → a dark/muted neutral (their
  faint identifying colour is illegible on the white pill, so the honest match is a quiet grey).
- **Python fallback:** add a tiny `STATE_ANNOTATION_FALLBACK` map (or reuse `--scriba-state-*`
  hex) so no-CSS SVG still colours the `state:` label; else default to `info`.

**Why (ii) over (i):** free dark adaptation (references existing dark state tokens); the binding
is *semantic and guaranteed identical* to the cell (exactly the user's ask); it dodges the
name/hue collisions of (i); fully backward compatible (new value form, old colours untouched).
Cost is comparable but the result is more correct.

> **Note:** `\reannotate` (`_grammar_commands.py:161-211`) validates against the *same*
> `VALID_ANNOTATION_COLORS`, so the `state:` branch should be added there too for parity
> (`\reannotate{sel}{color=state:current}`).

---

## 4. Design B — `leader=true` opt-in (reuse existing leaders)

Two leaders already exist, both **gated**; the feature is "let the author force one, to the
target cell, for any pill".

- **Leader #1 — arc, R-08 / v0.15.0 visual-gap.** `_emit_label_and_pill`,
  `_svg_helpers.py:2591-2627`. Gate: `_visual_gap >= _natural_gap + pill_h*_LEADER_GAP_FACTOR`
  (`:2606`; `_LEADER_GAP_FACTOR=1.0` `:367`, `_LEADER_ARC_CLEARANCE_PX=4.0` `:372`). Anchor =
  **arrow curve-mid** `geom.curve_mid_x/y` (not the cell). Draws `<circle r=2>` + `<polyline>`,
  colour `s_stroke`, dashed only for `warn`. Spec: `docs/spec/leader-line.md`.
- **Leader #2 — position=below callout lane, ~v0.21.0.** `emit_position_label_svg`,
  `_svg_helpers.py:3664-3728`. Gate: `_pill_spans_neighbours = cell_width is not None and
  pill_w > cell_width+1.0` (`:3677`). Anchor = **the target cell** `_lead_ox=ax`,
  `_lead_oy=below_baseline or ay` (`:3685-3686`). Draws a `<line>` (`:3692-3696`), colour
  `s_stroke`, **no dot**. (Plus a range-bracket `elif` `:3697-3728`.)
- **Reusable geometry:** `_line_rect_intersection(origin_x, origin_y, pill_cx, pill_cy, pill_w,
  pill_h) -> tuple[int,int] | None` (`:1099-1185`) — perimeter hit of the ray origin→pill-centre,
  `None` if origin inside the pill.

**Design:** add a boolean `leader` annotate key (parsed exactly like `arrow` at `:243`:
`params.get("leader", False) in (True, "true")`) threaded to the `ann` dict. In each emit path,
when `ann.get("leader")` is true, **force** a leader from the pill perimeter to the **target
cell**, ignoring the gate, drawn as a dotted `<line>` (so `.scriba-annotation-{color} > line`
recolours it and it dark-adapts) plus a `<circle>` dot at the cell anchor:

| path | function | pill centre | cell anchor | today |
|---|---|---|---|---|
| arc (`arrow_from`) | `_emit_label_and_pill` | `_pill_cx/_pill_cy` `:2595-2596` | `(ix2, iy2)` (params `:2425-2426`, = dst) | leader → curve-mid, gated |
| position (label only) | `emit_position_label_svg` | `_pill_cx/_pill_cy` `:3675-3676` | `(ax, ay)` | leader → cell, gated (drop gate + add dot) |
| plain arrow (`arrow=true`) | `emit_plain_arrow_svg` | from `final_x/final_y` `:2108-2109` | `(x2, y2)` `:2013` (dst) | **no leader today — new block** |

The dot needs one CSS rule so it recolours: `.scriba-annotation-{color} > circle { fill:
var(--scriba-annotation-{color}); }` (and a `-state-` variant). Default off → **no golden churn**.

> **Grade:** arc + position plumbing **Confirmed** (anchors and centres read in source);
> plain-arrow reuse **Deduced** — it has its *own* duplicated placement (`final_x/final_y`
> `:2108-2109`, `pill_w/pill_h` `:2102-2103`) and shares only the text emitters, so path 1 is a
> genuinely new leader block, not a gate flip.

---

## 5. Design C — tint+border family (breaking; recommend defer / opt-in)

**The inconsistency is real and confirmed** (both screenshots): `current` is the lone **solid
`#0070d5` chip with white text**; `good`/`done`/`path`/`error`/`dim` are all **light-tint fill +
border + dark text**. Side by side they read as two *kinds* of highlight. Proposal C: retune
`current` to tint-fill + blue border + dark text so the family is uniform, hue being the only
difference.

**Breaking-change measurement (Confirmed, `examples/*.tex`, 111 files):**

| metric | count |
|---|---|
| files using `state=current` | **82 / 111 (74%)** |
| files using **both** `current` and `good` | **62 / 111 (56%)** |
| files using `current` + any tint state (good/done/path) | **80 / 111 (72%)** |
| total `state=current` occurrences | 782 (the **most-used** state; done 670, good 493) |

Changing `current`'s appearance rewrites the most recognizable pixel in ~three-quarters of the
corpus → churns the byte-golden set (~105 files), the cookbook, and doc banners; forces a
`SCRIBA_VERSION` bump + full re-bless. It also *removes* a deliberate cue: solid-current is the
highest-contrast "you are here" focal point; flattening it to a tint may **reduce** scannability,
and it is the only state using white text (its own `--scriba-halo` = current-fill at `:578`, plus
dark-text/contrast re-tuning across light+dark).

**Recommendation (honest):** **do not change the default.** The user's actual pain is A (labels
can't match) and B (no forced leader) — both fully solved *without* touching C. If a unified
family is genuinely wanted, ship it as **opt-in** (`\begin{animation}[palette=tinted]`, a new
`VALID_OPTION_KEYS` entry at `constants.py:48-50`) so authors choose it and goldens opt in
per-file, and treat it as its own palette RFC rather than a rider on the A/B fix. If forced to
choose between "change default" and "opt-in", opt-in wins on churn and on preserving the focal
cue.

---

## 6. Patch plan — A (option ii) + B, TDD RED-first

Default-off / additive → **zero churn to existing goldens**; new goldens added for the new
surfaces. (Contrast C's ~74% churn.)

**A — `color=state:X`:**
1. `parser/_grammar_commands.py:213-261` `_parse_annotate` — branch: `state:`-prefixed colour →
   validate suffix ∈ `VALID_STATES` (E1113 or new E1114). Mirror in `_parse_reannotate`
   (`:161-211`).
2. `_svg_helpers.py` — emit class `scriba-annotation-state-{suffix}` at the three `<g>` sites
   (`:2849`, `:3656`, plain-arrow); add `STATE_ANNOTATION_FALLBACK` for no-CSS `label_fill`/
   `stroke`; keep `label_weight`/`size` from a sensible default.
3. `static/scriba-scene-primitives.css` — add `--scriba-annotation-state-*` vars (referencing
   `--scriba-state-*`, so dark is free) + `.scriba-annotation-state-{X} > text/path/line` rules
   near `:517-539`.
4. Docs: `docs/SCRIBA-TEX-REFERENCE.md` colour section (add `state:` form); update the state↔colour
   table there.

**B — `leader=true`:**
5. `parser/ast.py` `AnnotateCommand` (~`:190`) add `leader: bool = False`.
6. `parser/_grammar_commands.py` `_parse_annotate` — parse `leader` like `arrow` (`:243`); pass to
   `AnnotateCommand` (`:256-261`).
7. `scene.py` `AnnotationEntry` (`:111-120`) add `leader: bool=False`; `_apply_annotate`
   (`:836-846`) pass `leader=cmd.leader`.
8. `renderer.py:309-320` — add `**({"leader": True} if a.leader else {})` to the ann dict.
9. `_svg_helpers.py` — force-leader block in `_emit_label_and_pill` (anchor `(ix2,iy2)`),
   `emit_position_label_svg` (drop gate, add dot), `emit_plain_arrow_svg` (new block, anchor
   `(x2,y2)`); emit `<line>` + `<circle>` via `_line_rect_intersection`.
10. `static/scriba-scene-primitives.css` — `.scriba-annotation-{color} > circle { fill:
    var(--scriba-annotation-{color}); }` (+ `-state-` variant) so dots recolour.
11. Docs: `docs/spec/leader-line.md` (document the opt-in, forced, cell-anchored leader);
    R-card in `docs/spec/ruleset.md` if a rule number is assigned.

**Tests (write first, expect RED):**
- `tests/unit/test_parser_annotation_cmds.py`: `color=state:current` parses & stores;
  `color=state:bogus` → E1113/E1114 with a `valid: …` hint listing states; `leader=true` sets
  `AnnotateCommand.leader`.
- emitter test (`tests/unit/test_animation_emitter.py` neighbourhood): `color=state:current` →
  `<g class="… scriba-annotation-state-current">`; `leader=true` forces a `<line>`+`<circle>` to
  the target anchor **even when the gate would not fire** (assert on all three paths).
- `tests/unit/test_contrast.py`: each `--scriba-annotation-state-*` ≥ 4.5:1 on white (light) and
  on the dark pill.
- 1–2 new goldens under `tests/golden/examples/corpus/`; bless.

---

## 7. Open questions

1. **`color=match` (auto)** vs explicit `state:X` — auto would read the target cell's *live*
   state at build time; the `shape_states` map is in scope at `renderer.py:302` where the ann
   dict is built, so it's feasible, but explicit is deterministic and simpler. Ship explicit
   first?
2. **done/dim/idle legible-hue mapping** — their identifying colour is too light for the white
   pill. Map their `state:` label to the state *text* token (dark neutral) or to `muted`? (§3
   proposes text/muted.)
3. **current vs info collision** — `state:current` (`#0070d5`) will look ~identical to
   `color=info` (`#0b68cb`). Accept (intent differs) or add a subtle differentiator?
4. **E-code** for an invalid `state:` suffix — reuse E1113 (annotation colour) or mint E1114 for a
   clearer catalog entry?
5. **Retro-fix leader #1** — its `<polyline>`+`<circle>` (and the arrowhead `<polygon>`, pill
   border) don't dark-adapt (§2b coverage gap). Fold into B (switch to `<line>` + CSS) or keep B
   strictly additive?
6. **Dot vs cell collision** — a dot at the cell anchor may sit on the cell border/content;
   `_line_rect_intersection` returns `None` when the origin is inside the pill, but the cell-end
   dot may need a small inward offset.
7. **C palette** — if pursued, confirm `[palette=tinted]` opt-in vs a default bump + full
   re-bless (product call; §5 recommends opt-in).
