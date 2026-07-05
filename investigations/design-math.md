# Design — Math as an Evolving Object (the `Equation` primitive)

> DESIGN spec. **No repo source modified** except this doc. Every `path:line` was read this
> session; every KaTeX claim is backed by a live probe against the vendored KaTeX 0.16.11
> (`scriba/tex/vendor/katex/katex.min.js`, SHA in `vendor/katex/VENDORED.md`). Repo @ `main` `5e7d75b`,
> scriba 0.21.1.
>
> Grades: **[Confirmed]** read/rendered this session · **[Design]** proposed, not built.

---

## 1. Problem + the confirmed constraint

A CS-theory teacher needs math to be an **evolving object**, not a slideshow of images. Three
canonical gestures (from the census `investigations/teaching-animated-math.md`, **0 Covered · 5
Awkward · 2 Missing**):

- **(a) tint one TERM** inside an expression — point at `2T(n/2)` and say "*this* term".
- **(b) morph in place** across steps — `2T(n/2)+cn → 4T(n/4)+2cn`, corresponding terms persisting.
- **(c) reveal an ALIGNED derivation** line-by-line — `\begin{aligned}` with `&` columns, one row per `\step`.

**Why it is impossible today** *(all [Confirmed])*:

1. `$...$` is one **opaque KaTeX atom**: `_render_inline` wraps the whole KaTeX blob verbatim —
   `return f'<span class="scriba-tex-math-inline">{html}</span>'` (`renderer.py:499`). scriba never
   tags anything inside.
2. **No selector reaches inside.** The parser takes **one** accessor then errors on trailing text
   (`selectors.py:90-93`); `a.cell[0].term[0]` → **E1009** (census PROBE B). The finest grain is a
   whole cell.
3. **No math primitive exists** — 19 primitives, none an Equation/Derivation
   (`primitives/__init__.py`). Math is only a *string value* on someone else's cell.
4. **The runtime carries no KaTeX and cannot morph** — it pulses and hard-snaps between
   independently server-rendered SVGs; its only math code is a guard that *refuses* to write `$`
   (`scriba.js`, census stronghold 4). Aligned multi-line collapses to one atom, so aligned **and**
   revealable are mutually exclusive (census GAP-2).

The design must add math evolution **without** a browser math engine (LIGHTNESS: KaTeX is
server-only), **without** new runtime motion kinds (A-2: the 11 kinds are closed), and byte-stable
for docs that don't use it.

---

## 2. Three approaches vs the DNA

### Approach A — Term-tag inside existing cells (`a.cell[0].term[k]`)
Wrap terms in a cell's math value; extend the selector to chain `.term[k]` after `cell[i]`.

- GRAMMAR: **breaks** the one-accessor rule (`selectors.py:90-93`); needs a 2-level grammar change
  touching the parser **every primitive shares** — wide blast radius.
- Math stays **second-class** (a string in a cell) — does not serve the "math as an object" axis.
- Reveal/alignment of multi-line derivations has no home (a cell is one atom).
- **Verdict: reject.** Most parser risk, least teaching power, wrong altitude.

### Approach B — Author-side raw `\htmlClass` + macro, no primitive
Enable KaTeX `\htmlClass` (selective trust); author writes `\htmlClass{...}` (or a KaTeX-macro
`\term`) directly in any `$...$`; the runtime targets terms by class.

- LIGHTNESS: good (server-only). But scriba never learns the term-id set (it's buried in KaTeX
  expansion), so `\recolor{...term[9]}` on a **typo** can't be caught → **breaks RENDER-TRUST**
  (no boundary validation, silent no-op).
- Still no addressable, revealable, *aligned* multi-line object → GAP-2 unsolved.
- Needs runtime changes to target-by-class (the runtime keys on `[data-target]`).
- **Verdict: reject as the surface**, but keep its engine: `\htmlClass` under selective trust is the
  right *mechanism* (see §3).

### Approach C — First-class `Equation` primitive (CHOSEN)
A new primitive `Equation` whose **native accessors** are `E.term[k]` (tagged sub-terms) and
`E.line[i]` (aligned rows). Terms are declared once via a scriba-owned `\term{id}{body}` macro that
scriba rewrites to KaTeX `\htmlClass`; multi-line derivations are laid out **by the primitive** (each
line its own foreignObject, aligned on the `&` anchor), so per-line reveal and true alignment
coexist. Everything rides existing motion kinds.

- GRAMMAR: **perfect fit.** `E.term[0]`, `E.line[2]`, `E.term[k]` **already parse for free** as
  `IndexedAccessor` — the unknown-name-with-`[index]` fall-through (`selectors.py:120-128`). Verified
  live (§3 probe 3). **Zero selector-parser change.** Addressing a shape by `shape.accessor[i]` is the
  existing idiom (`G.node[X]`, `a.cell[i]`).
- Math becomes **first-class** — the axis, delivered.
- Solves GAP-2: alignment moves from KaTeX (blob-scoped) to the primitive (row layout, like a
  table), so lines are independently revealable **and** column-aligned.
- Rides `recolor` (tint + reveal) and existing `value_change` — **0 new motion kinds** (§3.4).
- **Verdict: choose.** Least new vocabulary (one macro `\term`, one primitive), most power (all of
  a/b/c), honors every DNA rule.

---

## 3. THE CHOSEN DESIGN — `Equation` primitive

### 3.0 KaTeX addressability — VERIFIED (live probes, vendored 0.16.11)

The whole design rests on "can KaTeX emit a server-side addressable sub-span, cheaply, without
shipping KaTeX to the browser." **Yes**, via `\htmlClass` under *selective* trust:

```
[htmlClass trust:false]        classFound=false*  len=934   (*only the MathML \annotation echo; no HTML span)
[htmlClass trust:true]         span emitted       len=1125
[htmlClass selective-trust]    span emitted       len=1125  <-- identical to trust:true
   selective trust = (ctx)=> ctx.command === "\\htmlClass"
   emitted tag: <span class="enclosing scriba-term-k0">        (probe 1)
aligned rows:  \begin{aligned}...\htmlClass{scriba-term-a}{2T(n/2)}...\\...\end{aligned}
               → both row-terms tagged                          (probe 1)
href gating:   \href{https://evil.test}{x} under selective trust, output:"html"
               → emits <a href>: FALSE ; contains "evil.test": FALSE   (probe 2)
selector:      E.term[0] / E.line[2] / E.term[k] → IndexedAccessor(name, index), no parser change (probe 3)
```

**Consequences:** (i) enabling `\htmlClass` re-opens **only** a CSS-class attribute — **not** URL/HTML
injection (`\href`/`\url`/`\includegraphics`/`\htmlData` stay gated by the same trust predicate);
(ii) for any doc that never emits `\htmlClass`, output is **byte-identical** (trust:false == selective
for such inputs). This is the security- and byte-stability-preserving unlock.

### 3.1 Authorable syntax (the whole new surface = **one macro + one primitive type**)

**Declare** (prelude `\shape`). Single equation:

```latex
\shape{E}{Equation}{tex="T(n) = 2\term{rec}{T(n/2)} + \term{work}{cn}"}
```

Multi-line aligned derivation (rows split on `\\`, aligned on the first `&`, exactly like `aligned`):

```latex
\shape{D}{Equation}{lines=[
  "T(n) &= 2\term{rec}{T(n/2)} + \term{work}{cn}",
  "     &= 4\term{rec}{T(n/4)} + 2\term{work}{cn}",
  "     &= cn\log_2 n"
]}
```

- `\term{id}{body}` — scriba-owned macro. `id` is an identifier (validated). Declares an
  **addressable** sub-expression. The same `id` may repeat across lines (that is how "the same term"
  is tracked down a derivation — need (b)).
- Everything else is ordinary KaTeX (`\begin{aligned}` is implied by `lines=`).

**Address & animate** (existing commands, new targets):

| Gesture | Author writes | Rides kind |
|---|---|---|
| (a) tint a term | `\recolor{E.term[rec]}{state=current}` | `recolor` |
| point an arrow at a term | `\annotate{E.term[work]}{text="cost", color=info}` | `annotation_add` |
| (c) reveal line i | prelude `\recolor{D.line[2]}{state=hidden}`, then at a `\step` `\recolor{D.line[2]}{state=idle}` | `recolor` |
| (b) morph across steps | reveal line i+1 while `\recolor{D.term[rec]}{state=current}` highlights the persisting term | `recolor` |
| whole-equation swap (baseline) | `\apply{E}{tex="4T(n/4)+2cn"}` | `value_change` |
| iterate terms | `\foreach{t}{[rec, work]} \recolor{E.term[${t}]}{state=done} \endforeach` | `recolor` |

`E` (bare shape) = the whole equation, addressable as today. `E.term[id]` = a tagged sub-span.
`E.line[i]` = the i-th aligned row (0-based).

**Note on (b) "morph".** The design serves morph the way a derivation is actually taught on a board:
write the next aligned line, highlight the term that changed — reveal + persistent-id highlight, not
physical glyph tweening. True FLIP-tweening of glyphs across a `value_change` would require the
runtime to match term ids between two independently rendered blobs and measure/interpolate positions
— a **new motion kind + heavy runtime JS** (violates A-2 and LIGHTNESS). It is an explicit **non-goal**
(documented as such); the aligned-reveal model is both lighter and pedagogically truer.

### 3.2 New E-codes (primitive block E14xx; confirm free range vs `errors.py` at build)

| Code | Condition | Boundary |
|---|---|---|
| `E1460` | duplicate `\term` id within one `Equation` | shape declaration |
| `E1461` | selector `E.term[id]` references an undeclared term id | selector→primitive `validate_selector` |
| `E1462` | `E.line[i]` index out of range | selector→primitive `validate_selector` |
| `E1463` | malformed `\term` (missing id/body, non-identifier id) | tex preprocess |

KaTeX parse errors inside a term reuse the existing **E1200** scan (`renderer.py:_scan_katex_errors`).
No new detection/parse (E10xx/E11xx) codes — the selector grammar is unchanged.

### 3.3 Motion-kind analysis — **0 new kinds** (the campaign's hard goal, MET)

The 11 closed runtime kinds (grepped from `scriba.js`): `value_change, recolor, element_add,
element_remove, highlight_on, highlight_off, annotation_add, annotation_remove, annotation_recolor,
position_move, cursor_move`. The design rides:

- **`recolor`** — term tint and line reveal are both **state transitions** on a `[data-target]`
  element. `hidden` is already a valid state that works on all primitives (docs §6, ref `:879`); the
  differ emits `recolor` for any state change including `hidden↔idle` (`differ.py:176-187`). The
  runtime already recolors by swapping the state class on `[data-target]` — the term span inherits it.
- **`value_change`** — the whole-equation swap (baseline, already works, `differ.py:191-200`).
- **`annotation_add/remove/recolor`** — `\annotate{E.term[k]}` callouts, via the existing annotation
  path once `resolve_annotation_point("term[k]")` returns the span's anchor.

No `Transition.kind` value is added; `differ.py` is **untouched**. A term/line target is just another
`[data-target]` string to the differ and runtime.

### 3.4 Byte-stability + SCRIBA_VERSION

| Asset | Change | Shipped to browser? | SCRIBA_VERSION |
|---|---|---|---|
| `scriba/tex/katex_worker.js` | `trust:false` → `trust:(ctx)=>ctx.command==="\\htmlClass"` | **No** (build-time only) | **No bump.** Inert for docs without `\term`/`\htmlClass` — output byte-identical (probe: trust:false == selective for such inputs). |
| `scriba/animation/static/scriba-scene-primitives.css` | **Add** rules mapping `.scriba-term.scriba-state-*` → `color: var(--scriba-state-*-fill)`, and a hidden-line rule for foreignObject rows | **Yes** (shared asset) | **One bump.** Additive only; reuses existing state tokens (`:127-145`). A doc not using `Equation` never references `.scriba-term`, so its HTML/SVG bytes are unchanged — but the shared CSS hash changes, which per DNA-3 forces the bump. |
| `scriba/animation/static/scriba.js` | **none** | Yes | **No change** — the LIGHTNESS win. Terms ride the existing `[data-target]` recolor/value_change machinery. |
| `equation.py`, `__init__.py`, docs, tests | new/append | No | n/a |

**Why CSS is needed at all:** the shipped state rules target **SVG direct children**
(`.scriba-state-current > rect/circle/text`, `scriba-scene-primitives.css:214-227`). A KaTeX term is
an HTML `<span>` inside a `<foreignObject>` (`_text_render.py:231`, `_math_metrics.py:3`) — the `> text`
rule does not reach it, and KaTeX colors via CSS `color`, not SVG `fill`. So term-tint needs
`.scriba-term.scriba-state-* { color: … }`. This is the **single unavoidable shared-asset touch** →
exactly one SCRIBA_VERSION bump, additive and opt-in-inert.

### 3.5 R-32 (envelope invariance)

The `Equation` primitive **lays out and reserves space for every line and term on every frame** (the
same pattern Array uses — its cell loop emits a `<g data-target>` for every cell regardless of state,
`array.py:534-557`). Hidden lines are emitted with `scriba-state-hidden` (invisible, space reserved),
never omitted. Therefore the primitive's `bounding_box` is frame-invariant and the scene viewBox is
stable across the reveal sequence → **R-32 satisfied**. This is asserted by a golden test (§3.6).

Multi-line alignment is the primitive's job: split each line at the first `&`, measure the pre-`&`
width per line (scriba already measures foreignObject/KaTeX extents — `_math_metrics.py`,
`primitives/_extent.py`), left-pad each row so the `&` anchor column lines up. Deterministic and
testable. This is the mechanism that makes **aligned + revealable** coexist (defeating GAP-2).

### 3.6 TDD plan (RED first)

1. **Selector (already green, lock it):** `parse_selector("E.term[k]")` → `IndexedAccessor("term", k)`
   (proved). Add `Equation.validate_selector("term[rec]")` True for a declared id, and False → E1461
   for an undeclared id; `line[9]` out of range → E1462. *(RED: primitive doesn't exist.)*
2. **Worker trust:** unit test — `render_inline("\\htmlClass{c}{x}")` currently emits **no** `<span
   class="…c…">` (trust:false); after the change it does. And `\href{javascript:…}{y}` still emits
   **no** `<a href>`. *(RED on the first assertion pre-change.)*
3. **Preprocess:** `\term{rec}{T(n/2)}` → `\htmlClass{scriba-term-rec}{T(n/2)}`; duplicate id → E1460;
   `\term{9bad}{}` → E1463.
4. **Emit:** `Equation(tex="2\term{rec}{T(n/2)}").emit_svg(render_inline_tex=…)` produces a
   `<foreignObject>` whose KaTeX span carries `class="… scriba-term-rec"` **and** the primitive wraps
   it with `data-target="E.term[rec]"` + state class. Golden the fragment.
5. **Differ rides recolor:** two frames with `\recolor{E.term[rec]}{state=current}` yield **one**
   `Transition(target="E.term[rec]", kind="recolor", from="idle", to="current")` — assert kind is
   `recolor`, **not** `value_change`, and no new kind string appears.
6. **Reveal + R-32:** `D.line[2]` hidden in prelude, revealed at step 2 → `recolor` transition; **and**
   the scene viewBox is byte-identical across all frames (golden).
7. **Aligned:** a 3-line `lines=[…]` derivation renders 3 foreignObject rows whose `&` anchors share
   an x-column (assert equal anchor x), each with its own `data-target="D.line[i]"`.
8. **Byte-stability guard:** a corpus doc that uses **no** `Equation` renders byte-identical HTML/SVG
   before/after the change (golden). Separately assert the CSS-hash change trips the SCRIBA_VERSION
   bump check.
9. **Security:** `\term{x}{\href{javascript:alert(1)}{z}}` — the nested `\href` still emits no `<a>`
   (selective trust whitelists only `\htmlClass`).

### 3.7 Implementation sketch (files touched)

1. **`scriba/tex/katex_worker.js`** — flip `trust:false` (`:52`) to the selective predicate; narrow the
   hardening comment (`:47-51`) to note `\htmlClass` is now whitelisted (class attr only; URL/HTML
   commands stay gated). *Build-time; no SCRIBA_VERSION.*
2. **`scriba/animation/primitives/equation.py`** — NEW. `@register_primitive class Equation`. Holds
   `lines: tuple[str, ...]` (single `tex` = one line). Responsibilities:
   - preprocess: extract `\term{id}{body}` → record id set (E1460 on dup, E1463 on malformed) →
     rewrite to `\htmlClass{scriba-term-<id>}{body}`.
   - `emit_svg(*, render_inline_tex=…)`: render each line via `render_inline_tex`; wrap each line in
     `<g data-target="{name}.line[i]" class="{state}">` (foreignObject); post-map each
     `class="…scriba-term-<id>…"` span to also carry `data-target="{name}.term[<id>]"` + state class
     (deterministic — scriba emitted the class); left-pad rows on the `&` anchor. Always emit all
     lines (R-32).
   - `addressable_parts()` / `validate_selector(suffix)`: accept `term[<declared id>]` and
     `line[0..n-1]` (mirror `array.py:439,450`), else E1461/E1462.
   - `resolve_annotation_point` / `annotation_headroom_above|below` / `register_decorations` /
     `dispatch_annotations` (protocol §5.1, `_protocol.py:31-95`) — anchor on the term/line box.
   - `bounding_box`: frame-invariant union of all line boxes.
3. **`scriba/animation/primitives/__init__.py`** — import + `__all__` (registry 19 → 20).
4. **`scriba/animation/static/scriba-scene-primitives.css`** — append `.scriba-term.scriba-state-*`
   color rules + hidden-foreignObject-line rule. *One SCRIBA_VERSION bump.*
5. **`docs/SCRIBA-TEX-REFERENCE.md`** — §2.3 cross-ref; new §7.20 `Equation` (params `tex`/`lines`,
   `\term`, accessors `term[id]`/`line[i]`, the a/b/c recipes, morph non-goal). Update the primitive
   count (19 → 20) and §5 command notes (no new inner command — `\term` lives inside math).
6. **tests/** — the RED cases in §3.6 (unit: selector/validate, worker trust, preprocess, emit,
   differ-kind, security; golden: emit fragment, aligned anchors, reveal viewBox, byte-stability).

No change to `selectors.py`, `differ.py`, `scriba.js`, the KaTeX vendor, or any other primitive.

---

## 4. Recipe-today baseline (what an author can do RIGHT NOW, and why C is worth its cost)

**Today:** a slideshow of whole equations. Put a `$...$` on a single-cell `Array` (or a `Grid`
row/`VariableWatch`) and swap the whole string per step:

```latex
\shape{E}{Array}{data=["$2T(n/2)+cn$"]}
\step \apply{E.cell[0]}{value="$4T(n/4)+2cn$"}
\step \apply{E.cell[0]}{value="$cn\log_2 n$"}
```

This diffs to a `value_change` (`differ.py:191-200`); each frame is an **independent** server-side
KaTeX render; the runtime **pulses and hard-snaps** to the next SVG (census stronghold 4, PROBE p0b:
three unrelated blobs). **No term is addressable, none persists, nothing highlights, no aligned reveal
exists.** For multi-line you either accept one opaque `aligned` atom (aligned, *not* revealable) or one
cell per line (revealable, *not* aligned) — GAP-2, never both.

**Why C is worth it.** In-place term highlight + line-by-line aligned reveal is *the* canonical
CS-theory teaching gesture — recurrence unfolding, the master theorem, loop-invariant and induction
proofs, modular-arithmetic steps. It is exactly the census's biggest blind spot (0 Covered). Approach
C converts most of the 5-Awkward/2-Missing row set to Covered for **one macro (`\term`) + one primitive
(`Equation`) + a selective-trust flip + additive CSS**, with **zero new motion kinds** and **zero
runtime-JS change** — server-rendered, deterministic, opt-in-inert. It buys the flagship "math as an
evolving object" capability at the smallest surface the grammar allows.

**Status: Design converged (Approach C).**
