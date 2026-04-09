# Extension E2 — `\hl{step-id}{tex-expr}` Highlight Macro

> **Status:** Accepted extension to `04-environments-spec.md`. This document
> specifies the `\hl` macro, which highlights a LaTeX term inside `\narrate{...}`
> in sync with the filmstrip frame via CSS `:target` and zero JavaScript.
>
> Cross-references: `04-environments-spec.md` §3.4 (`\narrate`), §5 (Starlark
> host), §8.1 (HTML output shape), §9 (CSS contract, `:target` rule), §10.4
> (`ctx.render_inline_tex`); `02-tex-plugin.md` for `TexRenderer` KaTeX trust
> configuration.

---

## 1. Purpose

For algorithm editorials whose primary content is algebraic derivation rather than
data-structure mutation — Miller–Rabin, Burnside, Splay amortized analysis —
equation-level highlighting is the highest-leverage visual tool available. The
`\hl` macro connects a LaTeX sub-expression to the filmstrip's frame-navigation
mechanism (CSS `:target`) so that the expression lights up when the reader is on
the matching step, without any runtime JavaScript.

### HARD-TO-DISPLAY problems unlocked

| # | Problem | How `\hl` helps |
|---|---------|-----------------|
| 1 | Zuma interval DP | Highlights the recursive sub-expression `dp[l][r]` in the recurrence narration alongside `\substory` |
| 2 | Miller–Rabin | Highlights `a^d`, `a^{2d}`, `a^{4d}` mod `n` as the witness sequence advances frame by frame |
| 6 | Convex Hull Trick | Highlights `dp[j] + b_j · a_i` at the query point to connect algebra to the geometric tangent |
| 7 | Splay amortized | Highlights the potential-function term `Δφ` vs `actual cost` in the access lemma |
| 8 | Burnside | Highlights `φ(d) · k^{N/d}` for each divisor `d` as the summation table fills |

---

## 2. Grammar

`\hl` is a **macro** (not an environment) recognized inside `\narrate{...}` body
text by a pre-processing pass in `SceneParser` before the body is passed to
`ctx.render_inline_tex`. It does NOT require its own top-level environment.

### 2.1 BNF

```
hl_macro     ::= "\hl" "{" step_id "}" "{" tex_expr "}"
step_id      ::= IDENT           (* matches [a-z][a-zA-Z0-9_]* *)
tex_expr     ::= balanced_text   (* any LaTeX expression accepted by KaTeX *)
```

`\hl` may appear **only inside `\narrate{...}`** (E1320 otherwise). Multiple `\hl`
calls in the same `\narrate` body are allowed and independent.

### 2.2 `step_id` resolution

The `step_id` is matched against the `label` of the enclosing or peer `\step`
command:

- If the enclosing `\step` carries `\step[label=step_id]`, it matches.
- If any `\step` in the same `\begin{animation}` environment carries
  `\step[label=step_id]`, it matches (cross-frame referencing is valid).
- An `\hl` whose `step_id` does not match any `\step` label in the animation is
  E1321 at compile time.

**Implicit label convention.** The base spec `\step` takes no arguments. This
extension requires extending `\step` to optionally accept `[label=<ident>]`.
See §10 (Base-spec deltas) for the required change. When no `label=` is provided,
`\step` gets an implicit label `step{N}` (1-indexed), so `\hl{step3}{...}` is
valid without an explicit label on the third step.

### 2.3 Multiple terms per step

A single `\narrate` may contain multiple `\hl` calls with the same `step_id`:

```latex
\step[label=witness-check]
\narrate{
  Compute $\hl{witness-check}{a^d} \bmod n$, then square to get
  $\hl{witness-check}{a^{2d}}$ and $\hl{witness-check}{a^{4d}}$.
}
```

All terms with the same `step_id` highlight simultaneously when that frame is
`:target`.

---

## 3. Preprocessing pass

Before the narration body is handed to `ctx.render_inline_tex`, `SceneParser`
runs a single-pass substitution:

**Input:** `\hl{step1}{a^d}`

**Output:** `\htmlClass{scriba-tex-term}{\htmlId{scriba-term-step1}{a^d}}`

Expanded inline in the narration body. After substitution, `ctx.render_inline_tex`
processes the full body (including the `\htmlClass` / `\htmlId` wrappers) through
the KaTeX pipeline.

The data attribute `data-scriba-step-id` is not a KaTeX construct — it is injected
by a post-KaTeX DOM pass (see §4).

### 3.1 Multiple terms with the same step_id

Each occurrence of `\hl{step1}{...}` generates a separate `\htmlId` call. Because
HTML `id` attributes must be unique per document, the renderer disambiguates by
appending a per-occurrence counter:

- First `\hl{step1}{a^d}` → `\htmlId{scriba-term-step1-0}{a^d}`
- Second `\hl{step1}{a^{2d}}` → `\htmlId{scriba-term-step1-1}{a^{2d}}`

All generated elements share the CSS class `scriba-tex-term` and the
`data-scriba-step-id="step1"` attribute added in §4.

---

## 4. KaTeX trust configuration

The KaTeX worker MUST enable `trust` for the `\htmlId` and `\htmlClass` commands.
No other `trust` extensions are required by this spec.

### 4.1 Required KaTeX option

```js
// katex_worker.js (or equivalent worker that handles render_inline_tex)
katex.renderToString(tex, {
  trust: (context) =>
    context.command === '\\htmlId' ||
    context.command === '\\htmlClass' ||
    context.command === '\\htmlData',
  throwOnError: false,
  // ... other existing options unchanged
});
```

This option must be set in the SAME worker invocation used by
`ctx.render_inline_tex`. The `AnimationRenderer` and `DiagramRenderer` call
`ctx.render_inline_tex` for narration bodies; they do not invoke KaTeX directly.
Therefore this configuration change belongs in the TexRenderer's worker, not in a
new worker.

### 4.2 KaTeX output for `\htmlId`

KaTeX's `\htmlId{id}{content}` expands to:
```html
<span id="id"><!-- rendered content --></span>
```

KaTeX's `\htmlClass{cls}{content}` wraps in:
```html
<span class="cls"><!-- rendered content --></span>
```

The combined expansion of
`\htmlClass{scriba-tex-term}{\htmlId{scriba-term-step1-0}{a^d}}` is:
```html
<span class="scriba-tex-term">
  <span id="scriba-term-step1-0"><!-- KaTeX-rendered a^d --></span>
</span>
```

### 4.3 Post-KaTeX data attribute injection

After `ctx.render_inline_tex` returns the KaTeX HTML string, the `SceneParser`
runs a lightweight string-pass that finds every `id="scriba-term-{step_id}-{n}"`
attribute and appends `data-scriba-step-id="{step_id}"` to the same element. This
is a mechanical string substitution, not a DOM parse, and MUST produce valid HTML.

Example transformation:
```html
<!-- before -->
<span id="scriba-term-step1-0" class="scriba-tex-term">...</span>
<!-- after -->
<span id="scriba-term-step1-0"
      class="scriba-tex-term"
      data-scriba-step-id="step1">...</span>
```

---

## 5. HTML output shape

### 5.1 Narration paragraph (from §8.1 of base spec)

The base spec emits:
```html
<p class="scriba-narration" id="{scene-id}-frame-3-narration">
  <!-- render_inline_tex output -->
</p>
```

With `\hl` in the narration:
```html
<p class="scriba-narration" id="mrprime-frame-3-narration">
  Compute
  <span class="scriba-tex-term katex-html" ...>
    <span id="scriba-term-witness-check-0"
          data-scriba-step-id="witness-check">
      <!-- KaTeX-rendered a^d -->
    </span>
  </span>
  mod <em>n</em>, then square to get
  <span class="scriba-tex-term katex-html" ...>
    <span id="scriba-term-witness-check-1"
          data-scriba-step-id="witness-check">
      <!-- KaTeX-rendered a^{2d} -->
    </span>
  </span>.
</p>
```

### 5.2 Frame `<li>` (unchanged from base spec §8.1)

The enclosing `<li>` carries the frame `id` that acts as the `:target` anchor:
```html
<li class="scriba-frame"
    id="mrprime-frame-3"
    data-step="3">
  <!-- stage, narration with \hl terms -->
</li>
```

When the reader navigates to `#mrprime-frame-3`, the CSS rule in §6 activates all
`scriba-tex-term` elements inside that `<li>` whose `data-scriba-step-id` matches
the `step_id` of that frame.

---

## 6. CSS sync mechanism

### 6.1 The `:target` anchor

The base spec (§9.1) already defines:
```css
.scriba-frame:target {
  outline: 2px solid var(--scriba-link);
}
```

The `\hl` extension adds the following rule to `scriba-animation.css`:

```css
/* Default: all \hl terms are un-highlighted */
.scriba-tex-term {
  border-radius: 0.15em;
  padding-inline: 0.05em;
  transition: background-color var(--duration-fast, 150ms) ease,
              color            var(--duration-fast, 150ms) ease;
}

/* When a frame is :target, highlight its \hl terms */
.scriba-frame:target .scriba-tex-term[data-scriba-step-id] {
  background-color: var(--scriba-state-highlight-fill, #F0E442);
  color:            var(--scriba-state-highlight-stroke, currentColor);
  outline:          1px solid var(--scriba-state-highlight-stroke, currentColor);
}

/* Reduced-motion: skip the transition */
@media (prefers-reduced-motion: reduce) {
  .scriba-tex-term {
    transition: none;
  }
}
```

### 6.2 Why this does not conflict with existing `:target` rules

The base-spec rule targets `.scriba-frame:target` directly for the card outline.
The new rule is more specific: `.scriba-frame:target .scriba-tex-term[data-scriba-step-id]`.
Because the new rule is a descendant selector (not a modification of the same
element), it does not override or conflict with any existing `:target` styles.
There is no specificity collision.

### 6.3 Cross-frame `\hl` visibility

An `\hl{step2}{...}` that appears in a `\narrate` belonging to frame 3 will be
highlighted ONLY when frame 2 is `:target` (the step_id is `step2`, which maps
to frame 2's id). When frame 3 is `:target`, terms with `data-scriba-step-id="step3"`
are highlighted.

This cross-frame referencing is intentional: it allows the narration on frame 3
to say "recall $\hl{step2}{a^d}$ from step 2" and have the term visually
distinguished as a back-reference.

### 6.4 No active state without `:target`

When no frame is `:target` (page load without fragment), ALL `scriba-tex-term`
elements are un-highlighted. This is the correct default: equations read as
normal text.

---

## 7. Fallback behaviour

If `TexRenderer` is not registered in the Pipeline (i.e., `ctx.render_inline_tex`
is `None`), the preprocessing pass still runs but instead of generating
`\htmlClass` / `\htmlId` wrappers, it generates a plain HTML span:

```html
<span class="scriba-tex-term scriba-tex-fallback"
      data-scriba-step-id="step1"
      data-scriba-tex-fallback="true">a^d</span>
```

The `tex_expr` body is HTML-escaped (not rendered). Highlighting via CSS still
applies (the `data-scriba-step-id` attribute is present), but the expression
renders as plain text instead of typeset math. This is E1322 (warning, not error).

---

## 8. Error catalog (E1320–E1329)

| Code  | Severity | Meaning                                                              | Hint |
|-------|----------|----------------------------------------------------------------------|------|
| E1320 | **Error** | `\hl` used outside `\narrate{...}`                                   | `\hl` is only valid inside a `\narrate` body. |
| E1321 | **Error** | `\hl` references a `step_id` that does not match any `\step` label in the enclosing `\begin{animation}` | Add `\step[label=step_id]` or use the implicit label `step{N}`. |
| E1322 | Warning  | `TexRenderer` not registered; `\hl` terms render as plain HTML text  | Register a `TexRenderer` for typeset math. |
| E1323 | **Error** | `\hl` used inside a `\begin{diagram}` environment                    | Diagrams have no `\step` frames; `\hl` step-sync is meaningless here. |
| E1324 | Warning  | `\hl` step_id matches a step in a different `\begin{animation}` block in the same document | Cross-environment `\hl` references are not supported; use the enclosing animation's step labels. |

---

## 9. Acceptance test

### Miller–Rabin witness sequence (Problem #2)

```latex
\begin{animation}[id=miller-rabin-demo, label="Miller-Rabin: n=221, a=3"]
\shape{seq}{Array}{size=4, labels="d,2d,4d,8d"}

\compute{
  n = 221
  d = 13   # n-1 = 220 = 13 * 2^4 => d=13, s=4
  a = 3
  vals = []
  v = 1
  for i in range(4):
      v = (v * a) % n if i == 0 else (v * v) % n
      vals = vals + [v]
}

\step[label=compute-ad]
\apply{seq.cell[0]}{value=${vals[0]}}
\highlight{seq.cell[0]}
\narrate{Tính $\hl{compute-ad}{a^d} = 3^{13} \bmod 221 = ${vals[0]}$.
         Vì $${vals[0]} \neq 1$ và $${vals[0]} \neq 220$, ta tiếp tục.}

\step[label=compute-a2d]
\apply{seq.cell[1]}{value=${vals[1]}}
\highlight{seq.cell[1]}
\narrate{Bình phương: $\hl{compute-a2d}{a^{2d}} = ${vals[1]} \bmod 221$.
         Kiểm tra $\hl{compute-a2d}{a^{2d}} \equiv -1 \pmod{221}$?}

\step[label=compute-a4d]
\apply{seq.cell[2]}{value=${vals[2]}}
\highlight{seq.cell[2]}
\recolor{seq.cell[2]}{state=error}
\narrate{$\hl{compute-a4d}{a^{4d}} = ${vals[2]}$. Không bằng $\pm 1$
         sau $s=4$ bước bình phương $\Rightarrow$ $221$ là hợp số (nhân chứng $a=3$).}
\end{animation}
```

Expected: navigating to `#miller-rabin-demo-frame-1` highlights the `a^d` term
in the narration; frame 2 highlights `a^{2d}`; frame 3 highlights `a^{4d}`.
All highlighting is CSS-only, no JS.

---

## 10. Base-spec deltas

The following changes to `04-environments-spec.md` are REQUIRED.

1. **§3.3 `\step`**: Add an optional `[label=<ident>]` argument:
   > `\step` optionally accepts `[label=<ident>]` where `<ident>` matches
   > `[a-z][a-zA-Z0-9_]*`. The label is used by the `\hl` macro (extension E2)
   > to associate narration terms with frame `:target` CSS rules. When absent,
   > the implicit label `step{N}` (1-indexed) is assigned. Duplicate labels in
   > the same animation are E1058. Labels must be unique per animation.

2. **§10 (Parser notes)**: Document that `SceneParser` runs a pre-processing pass
   on `\narrate` bodies before calling `ctx.render_inline_tex`, which expands
   any `\hl` macros found within. This pass is the only place where the narration
   body is modified before TeX rendering.

3. **§11 Error catalog**: Reserve E1058 for "duplicate `\step` label within one
   animation". Reserve E1320–E1329 for `\hl` macro errors.

4. **§9 CSS contract**: Note that `scriba-animation.css` contains additional rules
   for `.scriba-tex-term` and `.scriba-frame:target .scriba-tex-term[data-scriba-step-id]`
   as defined in extension E2 §6.
