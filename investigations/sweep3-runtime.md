# Sweep 3-D — Runtime-contract + math-paint parity (static, 0.30.0)

Scope: static analysis of the 0.30.0 emitted HTML/JS/CSS/SVG plus the emitter/
runtime sources. No browser. Read-only on `scriba/` and `tests/`. Probes live
under `_sweep3_runtime/*.tex` (rendered `.html` deleted after analysis).

Method: rendered probes from repo root with
`.venv/bin/python render.py <probe> -o ./_sweep3_runtime/<name>.html`, then
parsed the emitted frame payloads, inline `<style>`, and SVG. Contrast uses the
WCAG 2.x relative-luminance formula (verified against the values already baked
into `_types.py`/CSS comments).

Version pinned: `scriba/_version.py` → `__version__ = "0.30.0"`, `SCRIBA_VERSION = 25`.

---

## Findings (one line each)

- **HIGH** | Math-value foreignObjects do not adapt to dark mode (general math-paint parity break) | probe p4 idle `$\infty$` cell + mcmf.tex | `#11181c` on `#1a1d1e` = **1.06:1** (invisible); dim `#687076`=3.37:1; path `#5e6669`=2.89:1 | `_text_render.py:369` bakes `color:{fill}` inline; `array.py:591` passes hardcoded `colors["text"]`; CSS state rules only touch SVG `fill` (`scriba-scene-primitives.css:209-345`)
- **MEDIUM** | Theme-scope asymmetry: 6 `--scriba-annotation-state-*` tokens present in `[data-theme="dark"]` but absent from the `@media (prefers-color-scheme:dark)` twin | union_find.html emitted CSS (6 vs 0) | light inks on dark pill 2.89–3.45:1 (all sub-AA) | `scriba-scene-primitives.css:776-782` present, `:829-835` twin omits them
- **LOW** | Documented edge-weight fix (`~ .scriba-graph-weight{fill}`) is inert for a *math* edge weight | probe p1 `\apply{edge}{value="$\max(0,i)$"}` | math weight FO stuck `color:#687076` = 3.37:1 on dark chip | `scriba-scene-primitives.css:880-882` flips SVG `fill`, but the math weight is a `<foreignObject>` (HTML `color`), `graph.py:2411-2421`
- **LOW/clean-note** | Dark-contrast golden never exercises a math value | `24_contrast_dark_mode.tex` `data=[10,20,...]` (0 `$`) | 0 math values → the residual above is uncaught by the suite | test corpus gap

Clean (verified robust): fs-snap / flip-back contract; reduced-motion gating;
data-scriba-speed plumbing; a11y of grown-canvas graphs; asset/manifest honesty;
reserved-box WIDTH parity (FO vs text); runtime state-machine ↔ server-frame
correspondence. Details below.

---

## Slice 1 — Runtime wiring + fs-snap (flip-back) contract — CLEAN

**fs-snap contract (mechanism).** `_html_stitcher.py:664-665` sets
`_needs_sync[i] = (svg[i] != svg[i-1])` — a frame gets `fs=1` whenever its
server SVG string differs *at all* from the previous. `fs` rides the frame
payload (`:671,681,692`). In `scriba.js`, `animateTransition` ends in
`_finish(fullSync)`; when `fullSync` is truthy it re-snaps
`stage.innerHTML=frames[toIdx].svg` (`:453-454`) — server truth. The only
non-re-snap path is `_finish(false)` (`:476-478`), reached solely when
`needsSync` is false, i.e. the two frames' SVG is byte-identical, so there is
nothing to reconcile.

**Empirical (flip-back scan).** Rendered p1 (graph value channel), p3
(state annotations), bst, dijkstra, kruskal_mst, mcmf, union_find and scanned
every emitted frame object for the risky pattern `tr:[…]` **and** `fs:0`:

| doc | fs:0 frames | fs:1 frames | RISKY (tr-array + fs:0) |
|---|---|---|---|
| p1 | 1 | 4 | 0 |
| bst | 1 | 18 | 0 |
| dijkstra | 1 | 15 | 0 |
| kruskal_mst | 1 | 10 | 0 |
| mcmf | 1 | 15 | 0 |
| union_find | 1 | 17 | 0 |
| p3 | 1 | 1 | 0 |

The single `fs:0` per doc is always frame 0 (`tr:null`, no predecessor). **Every
transition frame is `fs:1`** → full re-snap → server truth. No reachable DOM
state fails to equal a server frame.

**NEW 0.30.0 value_change over graphs.** p1 emits 3 `value_change` records
(node `$\infty$`, edge `$\max(0,i)$`, node `7`) — all `fs:1`. The client stamp
`txt.textContent=toVal` (`scriba.js:183`) is guarded to skip `$`-math and
`null`, and is reconciled by the subsequent fs-snap regardless. External-runtime
mode (`--no-inline-runtime`) carries the same `fs` per frame in the JSON island
(verified on p1_ext: frames 1-4 `fs=1`).

**position_move over "grown" graphs is a non-event.** `graph.py:1421-1427`
(A1 position-pinning): a Graph's node set never changes and node coordinates are
pinned at construction, so `add_edge`/`set_weight` never move a node or grow the
canvas mid-animation. p1's scene viewBox is a single constant `0 0 464 364`
across **all** frames (max-extent viewBox, SCRIBA_VERSION-4 contract).
`position_move` is emitted only for Tree relayout (`differ.py:263-281`), and it
too rides `fs=1`. Force-canvas scaling (0.30.0 Piece #3) is an *initial* sizing,
not a per-frame growth.

**Flip-back guard confirmed at the boundary.** `errors.py:207-216` (E1107)
rejects a non-numeric `value=` on an intrinsically-numeric part (Bar height,
Matrix cell colour) precisely because "the differ still bakes a value_change …
the runtime stamps it then the fs-snap reverts it (a flip-back)". The class is
closed at validation, not left to the runtime.

**State machine ↔ frames.** Reachable states: `snapToFrame(i)` (server SVG),
mid-transition (transient, ends in re-snap), theme-toggle MutationObserver
(`:509-512`, re-snaps `frames[cur]`). Keyboard (`:503-507`) and prev/next
(`:501-502`) all funnel through `show()`. Substory frames are server-rendered
(`initSub`, `:64-77`). No client-only terminal DOM state.

## Slice 2 — Reduced-motion + speed — CLEAN

Gated at **both** layers:
- JS: `_motionMQ=matchMedia('(prefers-reduced-motion:reduce)')` +
  `_canAnim=…&&!_motionMQ.matches` with a live `change` listener
  (`scriba.js:43-45`); every animation entry checks `_canAnim`
  (`:103,187,416,433,488`) → falls back to `snapToFrame`.
- CSS: `scriba-scene-primitives.css:1041` `*,*::before,*::after{
  transition-duration:.01ms!important;animation-duration:.01ms!important}` plus
  `scriba-animation.css:28`. Present in emitted p1 (`@media (prefers-reduced-motion: reduce)`, 2×).

`data-scriba-speed` emitted on the widget root (`data-scriba-speed="1"`), read
by `_speed=parseFloat(W.getAttribute('data-scriba-speed'))||1` and applied
uniformly via `_dur(ms)=Math.round(ms/_speed)` (`:57-58`).

## Slice 3 — Theme dark-scope rule-by-rule diff — 1 asymmetry (MEDIUM)

Mechanical diff of the two dark token scopes:
- Scope A `[data-theme="dark"]` (`scriba-scene-primitives.css:719-783`) — 42 decls.
- Scope B `@media (prefers-color-scheme:dark) :root:not([data-theme="light"])`
  (`:789-836`) — 36 decls.

**Present in A, missing from B (6):** `--scriba-annotation-state-current`,
`-done`, `-dim`, `-good`, `-error`, `-path`. All shared props are value-identical;
B has nothing A lacks.

Consumed by `.scriba-annotation-state-* > text|path|line|polyline|polygon|rect`
(`:576-600`) — the R-37 `color="state:X"` binding used by `\cursor`/`\annotate`
(probe p3 emits `scriba-annotation-state-current/done/error` classes; live in
union_find.tex). When Scope B is the active dark path they fall back to the
light `:root` inks (`:177-182`) on the dark pill (`.scriba-annotation>rect`
flips to `#1a1d1e`, which IS in both scopes):

| token | light ink (fallback) | on `#1a1d1e` | dark-correct | 
|---|---|---|---|
| state-current | #0070d5 | 3.45:1 ✗ | #70b8ff (8.07) |
| state-done | #5b6871 | 2.96:1 ✗ | #9ba1a6 (6.49) |
| state-dim | #687076 | 3.37:1 ✗ | #7e868c (4.58) |
| state-good | #2a7e3b | 3.35:1 ✗ | #65ba74 (7.13) |
| state-error | #c6282d | 3.02:1 ✗ | #ff6369 (5.85) |
| state-path | #5e6669 | 2.89:1 ✗ | #a78bfa (6.23) |

**Severity MEDIUM (scoped).** The standalone page hard-codes
`<html … data-theme="light">` (`render.py:33`), so Scope B (`:root:not(
[data-theme="light"])`) is inert there — the toggle reaches dark via Scope A,
which is complete. Scope B is the *embed* path (a scriba widget on a host page
with no `data-theme`, OS in dark). Confirmed in a shipped doc: union_find.html
emitted CSS carries 6 annotation-state tokens in `[data-theme=dark]` and **0**
in the `@media` twin. No other stylesheet rescues it (checked embed/standalone/
animation CSS).

The **NEW 0.30.0 graph-pill rules** (`:877-890`) ARE symmetric — both scopes
carry `.scriba-graph-pill[fill="white"]{fill}` and `~ .scriba-graph-weight{fill}`.
The category-annotation polygon/rect dark overrides (`:845-863`) and `.idx`
(`:867-869`) are also symmetric.

**Minimal fix (design only):** copy the 6 declarations (`:777-782`) verbatim
into the Scope B block after `:835`. Byte-blast ≈ +240 B to the inlined
primitives CSS (per-doc, since CSS is inlined). Zero SVG change, no golden reflow.

## Slice 4 — Math-weight dark residual — CONFIRMED, and it generalises (see Slice 5)

**Reachability.** A graph edge weight is math only via a dynamic `value=`
(`graph.py:2247-2248` `dynamic_val = get_value(edge)`; `str(dynamic_val)`), NOT
via numeric `show_weights` (`_format_weight`, `:763-771`, always a number).
Probe p1 `\apply{G.edge[(A,B)]}{value="$\max(0,i)$"}` emits
`<foreignObject class="scriba-graph-weight" … width="67">` (matching the ~69 px
reserved box) with `<div style="…color:#687076…"><span class="katex">`. The pill
flips to `#1a1d1e` (`~`-sibling rule engages — pill precedes weight, `fill="white"`,
verified), but the FO's HTML `color:#687076` is untouched by the SVG-`fill`
rule → **3.37:1** (exactly the value the CSS comment `:872-876` documents).

**Corpus reach of *math weights with show_weights*: ZERO.** 14 docs use
`show_weights`; all edge weights are numeric (`weight=4`, `"8/10"`). No corpus/
example doc sets a math value on a graph edge. So the edge-weight instance is a
latent author footgun — **LOW** on its own. But it is one face of the general
break in Slice 5.

## Slice 5 — FO-vs-text parity — WIDTH parity holds; COLOR parity BROKEN in dark

**Reserved-box WIDTH (the `measure_value_text` contract) — CLEAN.**
`_text_metrics.py:207-224` returns, for a `$`-string,
`max(measure_label_line (KaTeX model), base(strip_math_markup))` — the max of
the KaTeX-on and the stripped-fallback paint. Numerically (mono, 14 px):

| string | KaTeX-model | stripped-fallback | reserved | = max? |
|---|---|---|---|---|
| `$\max(0,i)$` | 69 | 69 | 69 | ✓ |
| `$\frac{n}{2}$` | 26 | 52 | 52 | ✓ (over-reserves) |
| `$\infty$` | 17 | 43 | 43 | ✓ (over-reserves) |
| `$x^2+1$` | 46 | 43 | 46 | ✓ |

The reserved box is ≥ both render widths → neither path clips. Good.

**COLOR parity — BROKEN (this is the HIGH finding).** The two paint paths
diverge in dark mode:
- Plain value → `<text fill="#11181c">`; CSS `.scriba-state-idle > text{fill:
  var(--scriba-state-idle-text)}` (`:209-210`) overrides the attribute → dark
  `#ecedee` on `#1a1d1e` = 14.5:1. **Adapts.**
- Math value → `<foreignObject><div style="color:#11181c">…KaTeX…`
  (`_text_render.py:369`); the state CSS rules act on SVG `fill`, which the
  div's HTML `color` ignores. The div carries **no class** (array.py:587-597
  passes no `css_class`) and the colour is a **hardcoded light hex**
  (`array.py:591` `colors["text"]`; `_types.py:81-90`). **Does NOT adapt.**

Empirical: probe p4 idle `$\infty$` cell → `<foreignObject x=0 y=0 width=60
height=40>` (no class) under `scriba-state-idle`, `color:#11181c`. mcmf.html
(`\apply{dist.cell[i]}{value="$\infty$"}`) → **66** math-value FO divs all at
`color:#11181c`.

Dark-mode contrast of the baked light inks on the dark idle fill `#1a1d1e`:

| state text | baked ink | on `#1a1d1e` | verdict |
|---|---|---|---|
| idle / done / good / error | #11181c | **1.06:1** | invisible |
| dim | #687076 | 3.37:1 | sub-AA |
| path | #5e6669 | 2.89:1 | sub-AA |
| current | #ffffff | 16.96:1 | ok (white in both) |
| highlight | #0b68cb | — | ok-ish |

There is **no** dark-mode CSS rule anywhere that flips a foreignObject/div text
`color` for value FOs (only `.scriba-term`, `:988`, handles the Equation-`\term`
case — proof the team knows the mechanism but did not extend it to primitive
values). A shipped example (mcmf) renders its `$\infty$` distances invisible in
dark mode; any doc with math values on non-current cells/nodes is affected.

**Golden gap:** `24_contrast_dark_mode.tex` uses `data=[10,20,30,40,50,60]`
(0 `$`) — the dark-contrast golden never exercises the FO path, so the suite
cannot catch this.

**Minimal fix (design only), two options:**
1. *CSS-only, no golden reflow (short-term):* add `!important` child rules per
   state mapping the FO div colour to the state's text var, in BOTH dark scopes,
   e.g. `[data-theme="dark"] .scriba-state-idle foreignObject>div{color:var(
   --scriba-state-idle-text)!important}` ×8 states ×2 scopes. `!important` beats
   the inline non-important `color`. Byte-blast ≈ +1.1–1.4 KB inlined CSS. Zero
   SVG change. Subsumes the Slice-4 edge-weight case.
2. *Emitter, cleaner, bumps SCRIBA_VERSION (long-term):* stop baking a hex —
   emit the value FO div as `color:currentColor` (or `color:var(
   --scriba-state-{state}-text,{fill})`) and let the state cascade set it; no
   `!important`. Reflows every value-bearing SVG (golden invalidation), so gate
   behind a version bump.

## Slice 6 — a11y of grown-canvas graphs — CLEAN

Probe p1 (grown force-canvas graph, viewBox `0 0 464 364`):
- Every stage SVG (10/10: 5 live + 5 print) carries `role="img"` +
  `aria-labelledby="…-narration"`.
- Edges: `role="img"` + `aria-label="Edge from node A to node B"` (per edge).
- Widget root: `class="scriba-widget" id=… tabindex="0" data-scriba-speed="1"
  role="region" aria-label="Graph value channel"`.
- Narration region `aria-live="polite"` present; invariant panels `role="note"`.
- Focus ring intact: `.scriba-widget:focus,:focus-visible{outline:var(
  --scriba-widget-focus-ring);outline-offset:2px}` (`:896-899`).

Grown canvas did not drop or alter any aria/role wiring.

## Slice 7 — Asset / manifest honesty — CLEAN

External render (`--no-inline-runtime`) of p1:
- Emitted `<script src="scriba.aebe380c.js" integrity="sha384-rr44DPa1f+5d0IC…"
  crossorigin="anonymous" defer>`.
- Copied asset basename `scriba.aebe380c.js` == `RUNTIME_JS_FILENAME`
  (`runtime_asset.py:26`).
- Recomputed SHA-384 of the copied bytes == referenced `integrity` ==
  `RUNTIME_JS_SHA384`. **BASENAME MATCH: True. INTEGRITY MATCH: True.**

The HTML references exactly the basename the manifest lists, and the SRI hash is
honest. (Default inline mode inlines JS/CSS with no external refs — nothing to
mismatch.)

---

## Clean list (verified robust on 0.30.0)

1. fs-snap / flip-back contract — every transition frame `fs:1` → server re-snap; no `tr:[…]`+`fs:0` frame in 7 renders; E1107 closes the value flip-back at validation; graph nodes pinned so no mid-anim canvas growth; viewBox constant across frames.
2. Reduced-motion — JS `_canAnim` + universal CSS `animation-duration:.01ms!important`.
3. `data-scriba-speed` — emitted on root, read and applied uniformly.
4. Graph-pill dark rules (0.30.0) — symmetric across both dark scopes; numeric `<text>` weight flips correctly via CSS `fill`.
5. a11y — role="img" + aria-labelledby on all stage/print SVGs and edges; widget tabindex/role=region/aria-label; aria-live=polite; focus ring intact on grown canvas.
6. Asset/manifest — basename + SRI honest in external mode.
7. Reserved-box WIDTH parity — `measure_value_text` = max(KaTeX-model, stripped-fallback); over-reserves, never clips.

## Probes (kept under `_sweep3_runtime/`)

- `p1_graph_value.tex` — graph value channel: recolor + node/edge math value_change (fs-snap, math-weight residual, viewBox, a11y).
- `p3_state_annotation.tex` — `\cursor`/`\annotate color="state:X"` (R-37 asymmetry reach).
- `p4_mathvalue_dark.tex` — idle-cell math value (general FO dark residual).
