# BMAD Render-Quality Hunt 2 — Theme Contrast · Accessibility · Copy-Paste Integrity

> **STATUS: AUDIT COMPLETE 2026-07-07** (SCRIBA 0.28.0, git 0e8e09f). **No repo source modified.**
> Read-only. WCAG 2.1 contrast ratios computed from the inlined stylesheet tokens and the
> emitted SVG/HTML — **no browser / no Playwright**. Calculator calibrated against the repo's
> own asserted numbers (current 4.91:1, path 4.78:1, dim nominal 4.53:1 all reproduced exactly),
> so the deltas below are trustworthy. Sources of truth:
> `scriba/animation/static/scriba-scene-primitives.css`, `scriba/animation/static/scriba-embed.css`,
> `scriba/animation/primitives/_types.py`, `_svg_helpers.py`, `graph.py`, `_html_stitcher.py`.
> Round-1 (0.28.0) covered static geometry; this slice is the non-geometry correctness round-1 only glanced at.

---

## 1. Hand-off Brief

**The state text layer is solid; the failures live in the layers CSS state-classes do not reach.**
Every semantic state's **cell/node TEXT vs its FILL passes AA (≥4.5:1) in BOTH themes** — the C3
(current), path, and dim token fixes all hold, and no state regressed. The dark idle-stroke fix
from 0.24 also holds (3.04:1 vs the #1a1d1e surface, ≥3.0 UI). Copy-paste is clean: both multi-line
tspan emitters carry explicit fusion-guard trailing spaces, verified in rendered output. A11y is
strong: `role="img"`+`aria-labelledby`, `role="region"`+`tabindex=0`, `aria-live` narration,
`dir="auto"`, 20 `graphics-symbol` roles, a `prefers-reduced-motion` block, a focus ring, a
`forced-colors` HCM path, and a print filmstrip all ship inline.

**Three real theme defects, all in the "CSS-can't-reach-it" gap:**

1. **`dim` opacity collapse (systematic, both themes).** `.scriba-state-dim { opacity: 0.5 }`
   (primitives.css:264) composites the *whole group* — text AND fill — toward the stage. The
   token comment asserts "4.53:1 ✓ AA", but the **rendered** text/fill contrast is **1.90:1 (light)
   / 2.53:1 (dark)** — below even the 3:1 floor. Every dim cell in every primitive is affected, and
   the in-code "✓ AA" claims are factually wrong about what paints.
2. **Graph edge-weight pill never theme-switches (the Hypercube-edge sibling).** `.scriba-graph-pill`
   is emitted with inline `fill="white"` (graph.py:2200-2203) and is *deliberately excluded* from the
   state CSS (`:not(.scriba-graph-pill)`), with **no `[data-theme="dark"]` rule anywhere**. In dark mode
   every weighted graph (`show_weights`, the default weighted path — not an opt-in) paints bright
   `#dddddd` islands on the `#1a1d1e` stage; pill text `#687076` drops to 3.71:1 (sub-AA). Opt-in
   `tint_by_edge`/`tint_by_source` pastels are worse (3.06–3.56:1) and are documented light-only.
3. **Idle progress dots invisible (both themes).** `.scriba-dot` upcoming `#dfe3e6`/`#313538` on the
   controls bar = **1.22:1 / 1.27:1** — fails 3.0 UI. Redundant with the step counter, so LOW.

Plus by-design tonal quiet (non-signal strokes <3:1 vs stage) and minors (sentinel real 2.00:1;
step-counter has `aria-atomic` but no `aria-live`; dark halo token/surface mismatch; OS-dark is
inert on default `render.py` output because `<html data-theme="light">` is pinned).

---

## 2. Contrast tables (computed)

Thresholds: **text 4.5:1** (WCAG 1.4.3 AA), **non-text/UI 3.0:1** (1.4.11). Stage bg = widget bg
(`.scriba-stage` transparent): **light `#ffffff`**, **dark `#1a1d1e`** (embed.css:33 / :249).

### 2a. Cell/node states — TEXT vs FILL (the layer that matters most)

| state | LIGHT text/fill | | DARK text/fill | |
|---|--:|:--|--:|:--|
| idle | 17.01:1 | PASS | 14.47:1 | PASS |
| current | 4.91:1 | PASS | 4.91:1 | PASS |
| done | 14.61:1 | PASS | 11.53:1 | PASS |
| dim (nominal) | 4.53:1 | PASS | 6.00:1 | PASS |
| **dim (RENDERED, ×opacity 0.5)** | **1.90:1** | **FAIL** | **2.53:1** | **FAIL** |
| error | 17.01:1 | PASS | 14.47:1 | PASS |
| good | 14.61:1 | PASS | 11.53:1 | PASS |
| highlight | 5.17:1 | PASS | 8.07:1 | PASS |
| path | 4.78:1 | PASS | 5.18:1 | PASS |

**Text/fill is CLEAN in both themes except dim once its own opacity is applied.**

### 2b. STROKE vs stage-bg (UI 3.0) — the cell boundary

| state | LIGHT stroke/bg | | DARK stroke/bg | | note |
|---|--:|:--|--:|:--|---|
| idle | 1.29:1 | fail | 3.04:1 | PASS | dark = 0.24 fix, holds; light idle quiet by design |
| current | 5.45:1 | PASS | 8.07:1 | PASS | signal |
| done | 1.69:1 | fail | 2.11:1 | fail | non-signal, tonal-quiet |
| dim | 1.23:1 | fail | 1.25:1 | fail | + ×0.5 opacity → ~1.1:1 real |
| error | 3.91:1 | PASS | 5.85:1 | PASS | signal (fill==bg in dark, stroke carries it) |
| good | 5.07:1 | PASS | 7.13:1 | PASS | signal |
| highlight | 3.26:1 | PASS | 5.19:1 | PASS | signal (fill==bg in dark) |
| **path** | **1.69:1** | **fail** | **2.11:1** | **fail** | **signal state, but stroke invisible** |

Non-signal (idle/done) low stroke contrast is the intentional β "tonal quiet" — their meaning is
"no signal", so low salience is correct; flagged for completeness, **not** counted as defects.
`path` is the exception: it is a *signal* state whose stroke never crosses 3:1, so path leans
entirely on fill+text — and its fill `#e6e8eb` is **identical to `done`** and ~1.08:1 vs idle fill,
so path vs done vs idle differ only by text darkness (see F5).

### 2c. Dark-mode "fill == stage bg" (body invisible, stroke-only) — BY DESIGN

`idle`, `error`, `highlight` all use fill `#1a1d1e` = the dark stage. The cell body is invisible;
the (signal) stroke carries it — idle 3.04:1, error 5.85:1, highlight 5.19:1 all ≥3.0. Acceptable.

### 2d. Annotation pill label text on pill bg (CSS token values) — CLEAN both themes

| ink | LIGHT on #ffffff | DARK on #1a1d1e |
|---|--:|--:|
| info | 5.45:1 PASS | 8.07:1 PASS |
| warn | 5.38:1 PASS | 10.74:1 PASS |
| good | 5.07:1 PASS | 7.13:1 PASS |
| error | 5.61:1 PASS | 5.85:1 PASS |
| path | 5.45:1 PASS | 6.23:1 PASS |
| muted | 5.04:1 PASS | 6.49:1 PASS |

Arrow **strokes** on the stage use the same inks — identical ratios, all ≥3.0 UI. `\ref`/`\term`
narration inks (`--scriba-annotation-state-*`) on the narration bg: all 4.58–8.07:1, PASS both
themes (tightest = dark `dim` #7e868c → 4.58:1). **Annotation contrast is fully clean.**

### 2e. Chrome / controls

| element | ratio | verdict |
|---|--:|:--|
| LIGHT narration #475467 / #fff | 7.69:1 | PASS |
| LIGHT step-counter #687076 / #f8f9fa | 4.78:1 | PASS |
| DARK narration #ecedee / #1a1d1e | 14.47:1 | PASS |
| DARK step-counter #9ba1a6 / #202425 | 6.00:1 | PASS |
| **LIGHT dot idle #dfe3e6 / #f8f9fa** | **1.22:1** | **FAIL (UI)** |
| **DARK dot idle #313538 / #202425** | **1.27:1** | **FAIL (UI)** |
| LIGHT dot active #0070d5 / #f8f9fa | 4.66:1 | PASS (UI) |

---

## 3. Findings (graded)

### F1 — `dim` state renders at 1.90:1 (light) / 2.53:1 (dark), not the asserted 4.53/6.00 — **MEDIUM**
**Confirmed.** `scriba-scene-primitives.css:248-267`: the `.scriba-state-dim` **group** carries
`opacity: 0.5` (and `filter: saturate(0.3)`). SVG group opacity flattens rect+text then alpha-blends
the result over the stage, so effective text = `0.5·#687076 + 0.5·stage` = `#b4b8ba` (light) and
effective fill = `#f8f9fa` → **ratio 1.90:1**; dark → **2.53:1**. The token comments (primitives.css:117,
`_types.py:85`) claim "#687076 on #f1f3f5 → 4.53:1 ✓ AA" but that pair never paints in isolation —
opacity always applies. `dim` "deemphasizes but still renders" (constants.py:31), i.e. the reader is
still meant to read dim values, so 1.90:1 is a real legibility loss, and the "✓ AA" claim is false.
*Fix options:* raise dim group opacity to ~0.75 and pre-verify, or drop the group opacity and bake the
mute into the tokens; then correct the "✓ AA" comments.

### F2 — Graph edge-weight pill has no dark-mode fill; bright island + sub-AA text in dark — **MEDIUM**
**Confirmed.** `graph.py:2199-2203` emits `<rect class="scriba-graph-pill" … fill="{pill_fill}"
fill-opacity="0.85" …>` where `pill_fill` defaults to `"white"` (graph.py:2147). The state CSS
*excludes* the pill (`:not(.scriba-graph-pill)`, primitives.css:197-333) and **no `[data-theme="dark"]
.scriba-graph-pill` rule exists** (grep: none). Rendered `.demo/graph_edge.tex` (`show_weights=true`,
the ordinary weighted path) → 20× `class="scriba-graph-pill" … fill="white"` and 20× graph-weight text
`fill="#687076"` (also inline, no dark switch). In dark mode: white@0.85 over #1a1d1e = **#dddddd**
(12.48:1 vs stage — a jarring light island), text #687076 on it = **3.71:1 (sub-AA)**, with a *dark*
halo (`--scriba-halo: var(--scriba-bg)` = #151718) outlining it. Opt-in `tint_by_edge`/`tint_by_source`
pastels (#dbeafe/#d1fae5/#fee2e2/#fef3c7) → 3.06–3.56:1, and graph.py:206-210 already flags them
"light-mode-only" — but nothing guards dark+tint, and the *default* white pill is unguarded too. This
is the exact class of the Hypercube-edge bug fixed in 0.24 (route the inline paint through a token so
the dark override lands). *Fix:* add `[data-theme="dark"] .scriba-graph-pill { fill: var(--scriba-bg-code) }`
(+ OS-dark sibling) and theme the weight text, or route pill fill through a `--scriba-graph-pill-fill` token.

### F3 — Idle/upcoming progress dots ~1.2:1, invisible in both themes — **LOW**
**Confirmed.** embed.css:92 `.scriba-dot{background:#dfe3e6}` on controls `#f8f9fa` = 1.22:1; dark
:256 `#313538` on `#202425` = 1.27:1. Fails 3.0 UI. Mitigated: the `aria-atomic` step counter conveys
position textually, and active/done dots (#0070d5 4.66:1 / #c1c8cd) are visible — only the "how many
upcoming" cue is lost. *Fix:* darken idle dot to ≥3:1 vs the bar (e.g. #b9c0c6 light / #4a5054 dark).

### F4 — Sentinel slot real 2.00:1 after opacity 0.5 — **LOW**
**Confirmed.** primitives.css:425-431 `.scriba-sentinel > rect` stroke `#687076` (#9ba1a6 dark) at
`opacity:0.5`, dashed. Nominal 5.04:1 → **real 2.00:1** vs white. Opt-in (`sentinels=true`), a dashed
capacity/boundary marker deliberately faint, so LOW — but below 3:1.

### F5 — `path` and `done` are visually near-identical; path signal leans on invisible stroke — **LOW**
**Confirmed.** Both use fill `#e6e8eb` + stroke `#c1c8cd` (primitives.css:131-133 / 152-153); they
differ *only* in text (`done #11181c` near-black vs `path #5e6669` gray). path stroke never reaches
3:1 vs stage (2b), and path fill vs idle fill ≈ 1.08:1, so "on the path" reads as a faint gray text
tint. Discriminable but subtle — a reviewer tracing a shortest-path highlight in a dense array may not
see it. Design note more than a hard defect.

### F6 — By-design / informational (not counted as defects)
- Non-signal idle/done strokes <3:1 vs stage = intentional β tonal quiet (2b).
- Dark halo uses `--scriba-bg` #151718 while the real surface is #1a1d1e (embed.css:249) — a slight
  halo/surface mismatch, cosmetic.
- The `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])` machinery is **inert on
  default `render.py` output** because the template pins `<html … data-theme="light">` (render.py:33):
  OS-dark users see light until they hit the toggle. Intentional (toggle exists), but the OS-pref CSS
  only benefits embedders who don't pin the attribute.
- The ARROW_STYLES inline fallback inks (`_svg_helpers.py:1923-1972`, #027a55/#506882/#526070/#2563eb)
  are light-only, **but** the no-CSS fallback is self-consistent (white pill + dark ink; dark mode
  requires CSS, which switches both) → **checked, not a defect**.

---

## 4. Accessibility findings (from markup)

**Strong — one LOW gap.** Verified in emitted HTML (`_html_stitcher.py`, rendered `.demo/graph_edge.tex`):

| check | status | evidence |
|---|---|---|
| Widget role + name | PASS | `role="region" aria-label="…"` + `tabindex="0"` (stitcher:730) |
| Prev/next buttons labelled | PASS | `aria-label="Previous step"/"Next step"` (:734-736) |
| Narration live region | PASS | `aria-live="polite"` + `dir="auto"` (:739); 5× dir=auto in output |
| Stage SVG graphic role + name | PASS | `role="img" aria-labelledby="…-narration"` (rendered) |
| Sub-shape graphics roles | PASS | 20× `role="graphics-symbol"` (nodes/edges/annotations); `aria-roledescription` (svg_helpers:2080-2083, graph:1752) |
| Reduced-motion path | PASS | `@media (prefers-reduced-motion: reduce)` block (primitives.css:1020-1058); 3× in output; static filmstrip + print fallback exist |
| Focus visible | PASS | `.scriba-widget:focus-visible{outline:…}` (primitives.css:875-879); widget reset only sets box-sizing (buttons keep native ring) |
| Windows HCM | PASS | `@media (forced-colors: active)` strips halo (primitives.css:700-706) |
| **Step counter live** | **LOW** | `<span class="scriba-step-counter" aria-atomic="true">` has **no `aria-live`** (stitcher:735) — `aria-atomic` is inert without it, so the "N / M" position change is silent on navigation. Narration *is* announced, so redundant but the counter itself never speaks. *Fix:* add `aria-live="polite"`. |

### 4b. Copy-paste integrity — **CLEAN**
Both multi-line tspan emitters add a trailing space to non-final lines, with explicit anti-fusion
comments citing the "sang"+"phải"→"sangphải" bug: pill labels `_svg_helpers.py:1627-1634`
(`trail = "" if li == last else " "`) and primitive captions `base.py:1217-1225`. Verified in
rendered output: `<tspan …>min(dp[0]+w(0,4), … dp[2]+w(2,4), </tspan>` — trailing space present, so
select-copy across wrapped lines stays worded. Two-value labels (`_text_render.py:463`) fold the
separator into the secondary tspan (`primary+sep+secondary`, `xml:space="preserve"`) → "5/3" copies
intact. Math is emitted as per-line `<foreignObject>` blocks (block divs → newline on copy, no fusion).

---

## 5. Conclusion + Confidence

- **Theme contrast — NOT clean.** State TEXT/FILL passes AA in both themes (all fixes hold, nothing
  regressed), and annotations are fully clean — but three real defects sit where CSS state-classes
  don't reach: **F1 dim opacity collapse** (1.90/2.53:1 vs asserted 4.53/6.00 — MEDIUM, systematic),
  **F2 graph-weight pill no dark switch** (MEDIUM, the hunted Hypercube sibling, hits the default
  weighted-graph path), **F3 invisible idle dots** (LOW). Plus F4/F5 LOW and F6 informational.
- **Accessibility — effectively clean.** Roles, names, live narration, dir=auto, reduced-motion,
  focus, HCM, print all present and correct. Only **F7 step-counter `aria-live` LOW** gap.
- **Copy-paste — CLEAN.** Guards present in source and verified in rendered output.

**Confidence: HIGH.** Contrast math is standard WCAG 2.1, calibrated against the repo's own asserted
numbers (reproduced exactly). F2 confirmed by grepping emitted HTML (20× inline `fill="white"`, zero
dark rules). F1 uses standard SVG group-opacity compositing semantics. The only residual uncertainty
is *severity framing* — dim (F1) and non-signal strokes (F6) are partly intentional de-emphasis, so a
maintainer may accept F1 as "dim is disabled-like"; the falsified "✓ AA" comment and the sub-3:1
rendered result are the objective parts.

**Counts:** 3 real theme defects (2 MEDIUM, 1 LOW) + 2 LOW (F4/F5) + 1 LOW a11y (F7) + 3 informational.
Categories: contrast NOT clean; a11y clean-minus-one-LOW; copy-paste CLEAN.
