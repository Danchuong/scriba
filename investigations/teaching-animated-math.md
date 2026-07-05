# Animated Math / Derivation — can scriba teach MATH as an evolving object?

> BMAD investigation. **No repo source modified.** Read-only; probes written to scratchpad, rendered
> to a throwaway `.scriba_probe/` dir inside the repo (cwd-write restriction) and parsed (no Playwright).
> Repo @ `main` `5e7d75b`, scriba 0.21.1 (docs target 0.25.0). Every `path:line` was read this session;
> every verdict is backed by a render probe or a source stronghold.
>
> Evidence grades: **[Confirmed]** = read in source / rendered this session · **[Deduced]** = logical
> consequence of confirmed facts · **[Hypothesized]** = design proposal, not built.

---

## 1. Hand-off Brief (3 sentences)

**scriba cannot teach math as an evolving object — it can only replace one static equation-image with
another.** Math is a fully **opaque KaTeX atom**: `$...$` is rendered whole to an HTML/SVG blob at
build-time (`renderer.py:499`), the runtime ships **no KaTeX and no morph** (`scriba.js` has only a
guard that *refuses* to touch math text, `:160-172`), and **no selector reaches inside an expression**
— the finest addressable unit is a whole cell/node (`selectors.py:100-129`; `a.cell[0].term[0]` →
**E1009**, rendered). The single biggest gap is therefore **in-place sub-term highlighting** — the
canonical math-teaching gesture of pointing at the `2T(n/2)` term and saying "*this* becomes `4T(n/4)`"
— which is structurally impossible; term color exists **only** as frozen author-time KaTeX `\textcolor`
(rendered), never as an animatable `\recolor`.

---

## 2. Coverage Table

| Math gesture | Verdict | scriba surface (path:line) or the gap |
|---|---|---|
| **Equation → equation transformation** across steps | **Awkward** | Whole-atom swap only. `\apply{a.cell[0]}{value="$expr$"}` diffs to a `value_change` (`differ.py:189-198`); manifest record carries **raw `$...$`** (`["a.cell[0]","value","$2T(n/2)+cn$","$4T(n/4)+2cn$","value_change"]`, rendered p0b). Each frame is an **independent** server-side KaTeX render (`renderer.py:499`); the runtime **pulses only** and snaps to the next SVG (`scriba.js:160-172`, `:443`). A hard cut between two images — no term persists or moves; author hand-writes every full line. |
| **Highlight / color a single TERM inside an expression** | **Missing** | No accessor descends into `$...$`. Grammar stops at `cell/tick/item/node/edge/range/block/all` (`selectors.py:100-129`). **PROBE B**: `\recolor{a.cell[0].term[0]}` → **E1009** "unexpected trailing text: '.term[0]'". Only whole-cell `\recolor` (9 `VALID_STATES`, `constants.py:27-34`) tints the **whole** expression box (PROBE F). Per-term tint exists only as static author-time `\textcolor` (**PROBE D**: `style="color:red"`), which cannot change across steps except by swapping the whole blob. |
| **Substitute-and-simplify** (unfold `T(n)=2T(n/2)+n` one level) | **Awkward** | Same mechanism as row 1. Each level is a hand-typed full string; nothing "unfolds" — `2T(n/2)` is not kept and expanded in place, it is erased and a new independent image appears. `\compute` (Starlark) is **numeric only** (§13.6 integer sandbox), so the engine cannot expand the algebra for you. |
| **Multi-line ALIGNED derivation revealed line-by-line** | **Missing** (as aligned **and** revealable) | `\begin{aligned}` renders **only inside one** `$...$`/`$$...$$` (§2.3, ref `:198`) = **one opaque KaTeX atom** (**PROBE C**: 3 lines → **1** `class="katex"` blob, no per-line handle). Splitting each line into its own Array cell / Grid row *does* allow `hidden`→reveal, **but** KaTeX `&`-column alignment only holds **within one blob**, so per-line reveal and true alignment are mutually exclusive. |
| **Complexity COST accounting on a recurrence tree** (∑ level costs) | **Awkward** | Per-level `$O(n)$` labels sit as node/row/cell values (opaque blobs). A running total needs a `VariableWatch` row or a per-step relabel (whole-blob swap); `\compute` sums **numbers**, not symbolic `O(·)`. No summation is ever shown **as math evolving** — only a final typed answer. (Tree *structure* is teach-board's slice; the **cost math** has no evolving surface.) |
| **Inequality / bound / number-theory (modular) steps** | **Awkward** | Same whole-atom swap. No operation touches a relation or a term: you cannot flip `\le`→`\ge` in place, cancel a factor, or reduce a subterm `\bmod m` — every step is a full retype of the line, rendered as a fresh independent image. |
| **Running symbolic invariant that CHANGES value** | **Awkward / Missing** | `\invariant` is **static v1**, prelude-only, renders **once**, and "does not change between frames" (§5.17, ref `:743-764`); `${...}` is not interpolated into it (prior slice *teaching-lecture-tempo* G1). A changing value must be faked in a `VariableWatch` row — a current-value **overwrite** panel (`variablewatch.py:103,148-149`), and with a `$...$` value the runtime pulses-only (guard). Reads as a variable readout, not a pinned evolving predicate. |

**Counts: 0 Covered · 5 Awkward · 2 Missing.**

---

## 3. Confirmed Gaps

### PRIME FINDING — Math is an opaque KaTeX atom, not sub-term-addressable *(Confirmed, prime suspect CONFIRMED)*

The user's premise ("scriba đáp ứng được") **fails** for animated math. Four independent strongholds:

1. **No math primitive exists.** The registry ships **19** primitives — Array, Bar, CodePanel, DPTable,
   Forest, Graph, Grid, HashMap, Hypercube, LinkedList, Matrix, MetricPlot, NumberLine, Plane2D, Queue,
   Stack, Tree, VariableWatch (`primitives/__init__.py:47-67`). **None** is an Equation / Formula /
   Derivation / Math primitive. `grep -niE "equation|formula|derivation|eqnarray"` over
   `primitives/*.py` returns only unrelated "formula" comments. Math is never a first-class object,
   only a **string value** carried by another primitive's cell/label. **[Confirmed]**

2. **`$...$` is rendered whole and embedded opaquely.** `TexRenderer._render_inline` sends the fragment
   to the KaTeX worker (`katex.renderToString`, `output:"htmlAndMathml"`) and wraps the returned blob
   verbatim: `return f'<span class="scriba-tex-math-inline">{html}</span>'` (`renderer.py:499`). scriba
   never parses inside; sub-terms get **no** scriba ids/classes/`data-target` (rendered p0: the KaTeX
   `<span class="katex">` carries no `data-target`). **[Confirmed]**

3. **No selector reaches inside math.** `SelectorParser._parse_accessor` accepts exactly
   `cell / tick / item / node / edge / link / range / block / all` + a generic `[index]`
   (`selectors.py:100-129`), and `parse()` allows **one** accessor then errors on trailing text
   (`:90-93`). **PROBE B** (rendered): `\recolor{a.cell[0].term[0]}{state=current}` →
   `error [E1009] … unexpected trailing text: '.term[0]'`. The finest grain is the **whole cell**;
   **PROBE F** confirms `\recolor{a.cell[0]}{state=current}` tints the entire `$a_i+b_i$` box
   (`class="scriba-state-current"`). You can color the expression; you cannot color `a_i`. **[Confirmed]**

4. **The runtime cannot render or morph math — it snaps whole frames.** `scriba.js` ships **no KaTeX**;
   its only mention of math is a guard: on a `value_change` it writes the new text **only if it contains
   no `$`** — `if(txt&&toVal!=null&&String(toVal).indexOf('$')===-1){txt.textContent=toVal;}`
   (`scriba.js:160-172`), with the comment *"math values ($...$) render as KaTeX foreignObject in the
   next frame's server SVG — writing the raw string into <text> here would flash '$\max(0,i)$'
   mid-transition; pulse only instead."* So a math step = **scale-bounce pulse + hard snap** to a
   **pre-rendered, independent** server SVG (`:443` "No tween available … snap"). **PROBE p0b**
   (rendered): three `\apply` steps produce **three distinct KaTeX blobs** — `2T(n/2)+cn`,
   `4T(n/4)+2cn`, `cn\log n` — each a full re-render, none sharing a term with its neighbour. **[Confirmed]**

**What a teacher cannot do on screen:** take `T(n)=2T(n/2)+n`, **tint the `2T(n/2)` term**, and show it
**expand in place** to `4T(n/4)+2n` while the `+n` term slides and accumulates. Every one of those moves
— term highlight, term persistence, in-place substitution, animated cancellation — requires reaching
inside the expression, which no surface does. The only expressible "derivation" is a **slideshow of
independently-typed equation images** advanced by `\step`, with a pulse between slides.

### GAP-2 — No aligned-and-revealable derivation *(Confirmed)*

A line-by-line aligned derivation (the `align`/`eqnarray` board every complexity proof uses) cannot be
built with both properties at once. **PROBE C** (rendered): a 3-line `\begin{aligned}` inside `$...$`
collapses to a **single** `class="katex"` atom — there is no `.line[k]` into it, so you cannot reveal
line 2 while hiding line 3. The workaround (one Array cell / Grid row per line, revealed via
`state=hidden`→visible, per the *teaching-board-archetypes* dry-run recipe) restores per-line reveal but
**loses the `&` alignment** that makes a derivation readable, because KaTeX alignment is scoped to one
blob. Aligned **or** revealable — never both. **[Confirmed]**

### Secondary caveats (not standalone gaps)

- **Author-time term color ≠ animated highlight.** KaTeX `\textcolor`/`\color` survive the worker's
  `trust:false` hardening (which blocks only `\href,\url,\htmlId,\class,\data,\includegraphics`,
  `katex_worker.js:44-52`), so **PROBE D** tints one term red — but that color is baked into the render
  and can only *change* by swapping the whole blob. It is a static author choice, not a `\step`-driven gesture.
- **First-frame overwrite (general, not math-specific).** Commands after the first `\step` populate that
  step's frame, so a value set on `\shape` and immediately changed in step 1 never gets its own frame
  (PROBE p0b dropped the initial `$T(n)$`; PROBE p0c/p0d kept the initial when it survived step 1). To
  show a "before" equation, give it its own leading `\step`. This is the standard frame model, not a
  math bug — noted so it is not mistaken for one.
- **`${...}` interpolation is textual + numeric only.** A computed **number** can be spliced into a math
  string in `\apply`/`\narrate` (§13.2, ref `:1900`), e.g. `value="$O(${n}\log ${n})$"`, but it is
  substituted **before** KaTeX runs and the result is still a whole-blob swap; Starlark does no symbolic
  algebra (§13.6).

---

## 4. Conclusion + Confidence

**scriba can display a sequence of equations; it cannot animate an equation.** Math is a static image
that scriba can **swap** (whole-atom, hand-authored per frame, pulse-then-snap) but never **manipulate**:
no term is addressable, no term persists across a step, no in-place rewrite/highlight/cancellation/align-
reveal exists, and the runtime carries no math engine at all. The user's hypothesis holds only in the
weakest reading — "show equation A, then show equation B" works like advancing slides — and **fails** for
every gesture that treats math as an evolving object. The prime suspect is **CONFIRMED**: equation-
derivation is possible only by hand-rolling each frame as a whole new static string, exactly as predicted.

**Confidence: HIGH.** The four prime-finding strongholds are each read at `path:line` and corroborated by
rendered probes (E1009 sub-term rejection; raw-`$...$` manifest with the pulse-only guard; three
distinct KaTeX blobs across steps; whole-cell tint; single-atom aligned block; author-time `\textcolor`).
No source was modified.

### Probes (scratchpad + `.scriba_probe/`, reproducible)
`p0_katex.tex` (cell equation swap) · `p0b_three.tex` (3-level unfold → 3 independent blobs) ·
`pb_subterm.tex` (**E1009** sub-term) · `pc_aligned.tex` (aligned = one atom) ·
`pd_textcolor.tex` (author-time term color) · `pe_varwatch.tex` (running symbolic value) ·
`pf_wholecell.tex` (whole-atom tint). Render:
`.venv/bin/python render.py <probe>.tex -o <out-in-cwd>.html`.

**Status: Concluded.**
