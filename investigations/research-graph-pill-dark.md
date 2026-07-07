# Research — Graph edge-weight pill dark-mode theming (tint-preserving)

**Discipline:** bmad-investigate (structural design, READ-ONLY). Evidence-graded, WCAG numbers computed.
**Follow-up to:** `investigations/hunt2-theme-a11y.md` §F2, and the explicit deferral in
`scriba/_version.py:473-474` ("the graph edge-weight pill's dark-mode theming (needs a tint-preserving rework)").
**Verdict:** CSS-only fix. `SCRIBA_VERSION 24 → 25`. Golden blast = 107 corpus goldens (identical CSS delta).

---

## Hand-off Brief (for the implementer)

Add **four rules** (two selectors × two dark scopes) to `scriba/animation/static/scriba-scene-primitives.css`,
placed next to the existing annotation/idx dark overrides (after css:867). No `graph.py` change. No SVG change.

```css
/* Graph weight pill — default (fill="white") only; tinted pills carry a hex
   fill (#dbeafe / #ffffff / …) and are excluded so their state tint survives.
   Mirrors the annotation-pill precedent (.scriba-annotation > rect, css:852)
   and the .idx hardcoded-fill flip (css:867). */
[data-theme="dark"] .scriba-graph-pill[fill="white"] {
  fill: var(--scriba-state-idle-fill);            /* #1a1d1e in dark */
}
[data-theme="dark"] .scriba-graph-pill[fill="white"] ~ .scriba-graph-weight {
  fill: var(--scriba-state-idle-text);            /* #ecedee in dark */
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .scriba-graph-pill[fill="white"] {
    fill: var(--scriba-state-idle-fill);
  }
  :root:not([data-theme="light"]) .scriba-graph-pill[fill="white"] ~ .scriba-graph-weight {
    fill: var(--scriba-state-idle-text);
  }
}
```

**Why the attribute selector is the whole trick:** the DEFAULT pill emits the literal string
`fill="white"`; EVERY tinted pill emits a **hex** (`#ffffff`, `#dbeafe`, `#d1fae5`, …). `[fill="white"]`
matches the default **and nothing else** — so the tint signal is untouched with zero graph.py work and
zero SVG churn. The blanket `[data-theme="dark"] .scriba-graph-pill { fill: … }` suggested in hunt2 §F2
(`:146`) would clobber the tinted fills; this is the tint-preserving refinement of it.

---

## 1. pill_fill map (evidence)

### How `pill_fill` is chosen — `graph.py:2141-2147`
```python
if self.tint_by_edge:                       # Phase 7 smart-label v2.0
    pill_fill = _pill_tint_for_edge_state(state)
elif self.tint_by_source:                   # Phase 6 U-03
    src_state = self.get_state(self._node_key(u))
    pill_fill = _pill_tint_for_state(src_state)
else:
    pill_fill = "white"                      # ← DEFAULT (the flagged path)
```

- `_pill_tint_for_edge_state` (`graph.py:242-244`) → `_PILL_TINT_BY_EDGE_STATE` (`graph.py:229-239`):
  `idle #ffffff` · `current/active #dbeafe` · `good #d1fae5` · `bad #fee2e2` · `done/muted #f3f4f6`
  · `dim #f9fafb` · `highlighted #fef3c7`. **All hex, all light.**
- `_pill_tint_for_state` (`graph.py:221-223`) → `_PILL_TINT_BY_STATE` (`graph.py:211-218`):
  `idle #eff6ff` · `active #dbeafe` · `visited/complete #ecfdf5` · `highlight #fef3c7` · `error #fee2e2`.
  graph.py:206-210 already documents these as "light-mode-only".
- **Key fact:** only the `else` branch emits the literal token `"white"`. No tint entry is the string
  `"white"` (idle-tint is the *hex* `"#ffffff"`). So `fill="white"` ⇔ default pill. **Byte-verified** by
  rendering a 4-edge `show_weights=true` graph: 4× `class="scriba-graph-pill" … fill="white"` and 4×
  `class="scriba-graph-weight" … fill="#687076"` (a denser graph → ~20×, per hunt2 §F2).

### Pill rect emit — `graph.py:2199-2205`
```
<rect class="scriba-graph-pill" x=.. y=.. width=.. height=.. rx="4"
      fill="{pill_fill}" fill-opacity="0.85" stroke="{edge_stroke}" stroke-width="0.5"/>
```
`class="scriba-graph-pill"` scopes the state CSS AWAY from the pill via `:not(.scriba-graph-pill)`
(`scene-primitives.css:197-334`). `fill` is a **presentation attribute** (specificity 0,0,0) → any CSS
rule beats it. `fill-opacity="0.85"` composites over the stage. `edge_stroke` is inline light
(`#dfe3e6` for idle) and also un-themed — **out of scope** (thin 0.5px chip border; noted, not fixed).

### Pill TEXT emit — `graph.py:2170-2191` → `_text_render.py`
Both the split path (`:2172`) and normal path (`:2183`) pass `fill=THEME["fg_muted"]`,
`css_class="scriba-graph-weight"`. `THEME["fg_muted"] = "#687076"` (`_types.py:110`).
- **Numeric weight (default, the flagged case):** `_text_render.py:281,326` → plain
  `<text class="scriba-graph-weight" … fill="#687076" style="text-anchor:…">N</text>`. `fill` is a
  presentation attribute → **CSS-overridable.** ✓
- **Math weight `$…$` (rare):** `_text_render.py:369,419-425` →
  `<foreignObject class="scriba-graph-weight"><div style="color:#687076">…`. Color is pinned via
  **inline `style`** (specificity beats selectors) → **NOT CSS-overridable** without `!important`.
  See Residual §5.
- `.scriba-graph-weight` CSS (`scene-primitives.css:685-688`) sets only `--scriba-halo` + `stroke-width`,
  **never `fill`** — so nothing currently overrides the inline `#687076`, in either theme.

### Existing dark mechanism (mirror targets)
- Dark tokens: `[data-theme="dark"]` block `:719-783` and `@media (prefers-color-scheme: dark)
  :root:not([data-theme="light"])` `:788-837`. `--scriba-state-idle-fill: #1a1d1e` (`:731,797`),
  `--scriba-state-idle-text: #ecedee` (`:733,799`), `--scriba-bg-code: #1a1d1e` (`:724,793`).
- **Annotation-pill precedent (same problem, already solved):**
  `[data-theme="dark"] .scriba-annotation > rect { fill: #1a1d1e; }` (`:852`) + `@media` twin (`:863`).
- **Hardcoded-fill text precedent:** `.idx` — "hardcoded fill in light mode; flip for dark" →
  `[data-theme="dark"] .idx { fill: #9ba1a6; }` (`:867`) + `@media` twin (`:869`).
- **Hypercube-edge precedent** (the 0.24 sibling this task cites): `:where([data-primitive="hypercube"])
  .scriba-hypercube-edge { stroke: var(--scriba-state-idle-stroke); }` (`:469-471`) — route an un-themed
  inline paint through a token so the dark override lands.
- Real dark stage surface = **`#1a1d1e`** (`scriba-embed.css:249`, `.scriba-widget` bg).

---

## 2. Tint-preserving design — options & choice

| Opt | Mechanism | Tint kept? | Light bytes | SVG churn | Verdict |
|-----|-----------|:---:|:---:|:---:|---------|
| (a) | graph.py emits default `fill="var(--scriba-graph-pill-fill)"`, tinted keep hex | ✓ | **changes** (`white`→`var(…)`) | **all show_weights graphs re-bless** | rejected — breaks byte-identical light |
| (b) | graph.py adds `.scriba-graph-pill--default` class; dark rule on it | ✓ | changes (extra class) | re-bless | rejected — SVG churn |
| (c) | also re-ink the tinted dark values (fix 3.06–3.56:1) | ✓ | ok | ok | over-scope — the brief wants minimal + "keep signal", not "fix tinted contrast" |
| **(d)** | **CSS attribute selector `[fill="white"]` + sibling combinator** | **✓** | **byte-identical** | **none** | **CHOSEN** |

**Chosen = (d).** See the four rules in the Hand-off Brief. Two facts make it work:

1. **Rect isolation** — default emits `fill="white"` (string), every tint emits a hex; `[fill="white"]`
   is an exact, robust discriminator (specificity `0,3,0` beats the inline presentation attribute `0,0,0`).
2. **Text isolation** — the weight text is emitted immediately after its pill rect, **same parent**
   (verified in the rendered DOM):
   ```
   <g transform="rotate(61.70 309.5 107.0)">
     <rect class="scriba-graph-pill" … fill="white" fill-opacity="0.85" stroke="#dfe3e6" …/>
     <text class="scriba-graph-weight" … fill="#687076" style="…">2</text>
   </g>
   ```
   (Horizontal edges drop the rotate `<g>` but keep rect-then-text adjacency.) So
   `.scriba-graph-pill[fill="white"] ~ .scriba-graph-weight` selects **only default-pill text**;
   tinted-pill text (sibling of a hex-fill pill) never matches → its pre-existing look is preserved.

**Both rules are required.** With the fill flipped to `#1a1d1e` but text left at `#687076`, the text sits
at **3.37:1 (sub-AA)** — `#687076` is a mid-gray that fails AA on any dark surface. The text must flip to
`#ecedee` too. `--scriba-state-idle-fill` + `--scriba-state-idle-text` are a designed AA pair and match the
annotation-pill house style (`#1a1d1e` chip, light text); hardcoding `#1a1d1e`/`#ecedee` is the exact
annotation-precedent equivalent.

### Computed dark contrast (WCAG 2.1, sRGB; `fill-opacity 0.85` composited over the `#1a1d1e` stage)
| | pill fill (effective) | text | text-on-pill | pill-vs-stage |
|---|---|---|:---:|:---:|
| **Current default (dark)** | `white`@0.85/#1a1d1e = **#dddddd** | #687076 | **3.71:1** ✗ sub-AA | **12.48:1** (jarring bright island) |
| **Proposed default (dark)** | #1a1d1e@0.85/#1a1d1e = **#1a1d1e** | **#ecedee** | **14.47:1** ✓ AAA | **1.00:1** (blends into stage) |
| Proposed w/ text NOT flipped | #1a1d1e | #687076 | 3.37:1 ✗ | — (proves text must flip) |
| **Tinted (dark) — UNCHANGED** | hex@0.85/#1a1d1e | #687076 | **3.06–3.71:1** (pre-existing) | — (signal = fill hue, preserved) |
| Light default (UNCHANGED) | `white`@0.85/#f8f9fa = #fefefe | #687076 | 5.00:1 ✓ | — |

Current dark 3.71 / 12.48 and tinted 3.06–3.56 reproduce hunt2 §F2 exactly. Tinted range here is
3.06–3.71 because it includes the idle-tint `#ffffff` (3.71, = the default's old value); the pastel-only
range is 3.06–3.56. **The fix neither improves nor regresses tinted pills** (selector excludes them) —
consistent with the brief's "keep the state signal, minimal."

---

## 3. Byte verdict + golden blast + SCRIBA_VERSION

- **CSS-only.** Only `scriba-scene-primitives.css` changes; it is inlined into every emitted page.
  **SVG geometry is untouched** (no graph.py edit). **Light mode is byte-identical** (all four rules are
  scoped under `[data-theme="dark"]` / `prefers-color-scheme: dark`; light default pill stays
  `fill="white"` / text `#687076`, 5.00:1, verified).
- **Golden blast = 107 corpus goldens** (`tests/golden/examples/corpus/*.html`, which inline the scene
  stylesheet) re-bless by **one identical CSS delta**. Untouched: 5 animation-runtime goldens
  (`tests/golden/animation/html_*.html` — do not inline the scene CSS) + 3 `tests/golden/smart_label/*/
  expected.svg` (SVG fragments, no CSS). This is the "DNA-3 shared-asset bump" pattern.
- **SCRIBA_VERSION 24 → 25.** Any emitted-byte change bumps. **Exact precedent:** the 0.29.0 `dim`
  opacity fix — "SVG geometry is untouched; only the shared inline stylesheet changes (every page
  re-blesses by the identical delta — the DNA-3 shared-asset bump)" (`_version.py:466-472`) — was a
  CSS-only change carried inside the 23→24 bump. Add a `0.30.0 bumps 24→25` note to `_version.py`.

---

## 4. RED tests (`tests/unit/test_contrast.py` — reuse its `contrast_ratio`, `WCAG_AA_NORMAL`, `_dark_token`)

```python
# helpers already in file: contrast_ratio(fg,bg), WCAG_AA_NORMAL=4.5,
# TestDarkModeNonTextContrast._dark_token(name) -> hex from the [data-theme="dark"] block.
CSS = Path("scriba/animation/static/scriba-scene-primitives.css").read_text()

def _over(fg, bg, a=0.85):  # sRGB source-over composite -> hex
    f=[int(fg.lstrip('#')[i:i+2],16) for i in (0,2,4)]
    b=[int(bg.lstrip('#')[i:i+2],16) for i in (0,2,4)]
    return '#%02x%02x%02x'%tuple(round(a*x+(1-a)*y) for x,y in zip(f,b))

STAGE_DARK = "#1a1d1e"   # scriba-embed.css:249

def test_default_graph_pill_dark_text_meets_aa():
    fill = _dark_token("--scriba-state-idle-fill")   # #1a1d1e
    text = _dark_token("--scriba-state-idle-text")   # #ecedee
    eff  = _over(fill, STAGE_DARK)
    assert contrast_ratio(text, eff) >= WCAG_AA_NORMAL   # 14.47 — RED until text rule added

def test_dark_pill_rule_is_default_scoped_not_blanket():
    # tint-preserving guard: rule must carry [fill="white"], never bare .scriba-graph-pill
    assert '.scriba-graph-pill[fill="white"]' in CSS          # RED until rule added
    assert '[data-theme="dark"] .scriba-graph-pill {' not in CSS   # forbids the hunt2 blanket

def test_dark_default_pill_not_bright_island():
    eff = _over(_dark_token("--scriba-state-idle-fill"), STAGE_DARK)
    assert contrast_ratio(eff, STAGE_DARK) < 3.0             # blends (1.00) not 12.48 island

def test_tinted_pill_keeps_state_hex_in_emit():
    # render tint_by_edge=true; assert pill still emits the hex tints (signal preserved)
    svg = render_graph(tint_by_edge=True, show_weights=True)   # via existing graph test harness
    assert 'fill="#dbeafe"' in svg and 'fill="white"' not in svg  # tint intact, no default pill

def test_light_mode_pill_unchanged():
    # every new pill rule is dark-scoped -> light stays fill="white"/#687076 (byte-identical)
    assert ".scriba-graph-pill[fill=\"white\"]" in CSS  # exists...
    # ...but only within a dark scope: no occurrence precedes any [data-theme="dark"]/@media gate
```
`test_default_…`, `test_dark_pill_rule_…`, `test_dark_default_pill_not_bright_island` are **RED today**
(no rule exists); `test_tinted_…` passes now and locks the anti-regression contract.

---

## 5. Residual (documented, out of scope)

- **Math weight (`$…$`) on a default pill** stays `#687076` (~3.37:1) in dark: its FO div pins color via
  inline `style="color:#687076"` (`_text_render.py:369`), which beats selectors. Fixing needs either a
  `… .scriba-graph-weight > div { color: … !important }` (CSS-only but heavy-handed, and touches KaTeX
  span inheritance) or a graph.py change (which would forfeit byte-identical light). Rare, orthogonal
  (pre-existing for tinted FO weights too), and outside the flagged default-numeric path. Fast-follow.
- **idle-tint `fill="#ffffff"`** (opt-in `tint_by_edge`, idle state) stays a #dddddd island in dark
  (12.48:1) — the `[fill="white"]` selector deliberately excludes it. Since idle carries no signal,
  extending the selector to `[fill="#ffffff"]` is a safe, trivial scope-add if desired, but it's the
  opt-in tint path, not the default. Noted, not fixed.
- **Pill stroke** `stroke="#dfe3e6"` (idle, inline, un-themed) reads as a crisp light chip outline on the
  new dark fill — acceptable (defines the chip, matches the annotation-pill outlined look). Not fixed.

## Confidence: HIGH
Every structural claim is cited to `path:line` and byte-verified by a live render; every contrast number
is computed (WCAG 2.1) and cross-checks the prior investigation (3.71 / 12.48 / 3.06–3.56 reproduced).
The mechanism is the already-shipped annotation-pill + `.idx` + hypercube-edge precedent. The byte/version
verdict matches the documented 0.29.0 shared-CSS bump. Only open judgment call: attribute-selector (chosen)
vs a graph.py class split — the attribute-selector strictly dominates on the byte-identical-light criterion.
