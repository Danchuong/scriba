# Extension E4 — `\substory` / `\endsubstory` Inline Drilldown

> **Status:** Accepted extension to `environments.md`. This document
> specifies the `\substory` / `\endsubstory` block, which embeds a nested linear
> frame sequence inside a single parent filmstrip frame.
>
> Cross-references: `environments.md` §2 (grammar), §3.3 (`\step`), §6
> (frame semantics and frame count limits), §8.1 (HTML output shape), §9 (CSS
> contract); `00-ARCHITECTURE-DECISION-2026-04-09.md` E4 and coverage row #1.

---

## 1. Purpose

Interval DP and other recursive algorithms exhibit a structure where understanding
a single top-level DP cell requires replaying a sub-computation — a recursive
trace of depth 2 or 3. Interactive "click to expand" drilldowns require JavaScript
and therefore violate Scriba's portability contract. `\substory` solves this by
**unrolling the sub-computation inline** as a nested sequence of frames inside the
parent step. The result is a linear filmstrip within a filmstrip: the reader
scrolls or tabs through the substory frames exactly as they do the parent frames,
with no interactivity required.

### HARD-TO-DISPLAY problems unlocked

| # | Problem | How `\substory` helps |
|---|---------|------------------------|
| 1 | Zuma interval DP | Top-level frame shows `dp[2][5]` being filled; substory inside that frame traces the sub-computation `dp[3][4]` that justifies the recurrence step |

`\substory` is also useful for any recursive algorithm where one step of the outer
algorithm spawns an inner algorithm execution that the reader needs to follow:
divide-and-conquer merge steps, tree recursion base cases, segment-tree build
sub-problems.

---

## 2. Grammar / BNF

`\substory` / `\endsubstory` are inner commands recognised by `SceneParser`
**only inside `\begin{animation}`** (E1362 if used at top level or inside
`\begin{diagram}`). See `environments.md` §6 for scene-scoping semantics
that govern how substory-local bindings interact with the parent scope.

```
substory_block   ::= "\substory" opt_substory_options NEWLINE
                     substory_body
                     "\endsubstory"

opt_substory_options ::= "" | "[" substory_option_list "]"
substory_option_list ::= substory_option ("," substory_option)*
substory_option  ::= "title" "=" STRING
                   | "id"    "=" IDENT

substory_body    ::= (substory_shape_cmd | substory_compute_cmd)*
                     substory_step_block+

substory_shape_cmd   ::= "\shape"   brace_arg brace_arg param_brace
substory_compute_cmd ::= "\compute" compute_brace
substory_step_block  ::= "\step" NEWLINE
                         (apply_cmd | highlight_cmd | recolor_cmd | annotate_cmd)*
                         narrate_cmd?
```

`\substory` / `\endsubstory` MUST each appear on their own line (same rule as
`\begin{...}` / `\end{...}` in the base spec). Text on the same line as
`\substory` is E1368. Text on the same line as `\endsubstory` is E1368.

### 2.1 Position constraint

`\substory` MUST appear **inside a `\step` block** (between two `\step` markers
or between the last `\step` and `\end{animation}`). It is NOT allowed in the
animation prelude (before the first `\step`). The `\substory` block ends with
`\endsubstory`, which MUST be encountered before the next parent `\step` or
`\end{animation}`. An unclosed `\substory` at parent `\step` or `\end{animation}`
is E1361.

### 2.2 Options

| Key     | Required | Type   | Default         | Meaning |
|---------|----------|--------|-----------------|---------|
| `title` | No       | string | `"Sub-computation"` | Human-readable label for the substory. Used as the `aria-label` of the wrapper `<section>`. |
| `id`    | No       | ident  | auto-generated  | Stable substory id for HTML id generation. Auto-generated as `substory{K}` where K is the 1-indexed count of substories in the same animation. |

### 2.3 Nesting depth

Substories may nest: a `\substory` inside a `substory_step_block` opens a depth-2
substory. Maximum depth is **3** (E1360 if exceeded). Depth counting:

- Depth 0: regular animation step
- Depth 1: `\substory` inside a depth-0 step
- Depth 2: `\substory` inside a depth-1 substory step
- Depth 3: `\substory` inside a depth-2 substory step (maximum allowed)

Depth 4 (`\substory` inside depth-3) is E1360.

---

## 3. Scope semantics

### 3.1 Shape declarations

`\shape` commands inside a `substory_body` declare **substory-local** shapes.
These shapes are visible only within the substory and are destroyed at
`\endsubstory`. Their names do NOT collide with parent-scope shapes; a substory
may reuse the same identifier as a parent-scope shape (the inner binding shadows
the outer one within the substory).

After `\endsubstory`, the parent frame's shape and state are **fully restored**
to what they were before `\substory` opened. Mutations to **parent-scope shapes**
made by `\apply`, `\recolor`, or `\annotate` inside the substory ARE ALSO RESTORED
(substory mutations to parent shapes are ephemeral and do not persist to the next
parent step). If an author references a parent-scope shape inside a substory, the
compiler issues **E1363** (warning: substory references parent-scope shape — the
reference is allowed, but the mutation is ephemeral and will be rolled back at
`\endsubstory`).

If a substory shape name is referenced outside the substory (i.e., after
`\endsubstory`), that is **E1369** (hard error: substory-local shape leaked into
parent scope).

### 3.2 `\compute` in substory

`\compute` blocks inside a substory body have access to the parent animation's
global bindings (read-only) and may define new substory-local bindings. Substory-
local bindings do NOT propagate to the parent scope after `\endsubstory`.

### 3.3 Frame budget

Substory frames count toward the parent animation's hard frame cap (100 frames,
E1181 from base spec). If the total frame count including all substory frames
across the whole animation exceeds 100, E1364 is raised (overrides E1181 to
provide a more specific message indicating substory overflow).

---

## 4. HTML output shape

### 4.1 Substory wrapper

A `\substory` block is rendered as a nested `<section>` + `<ol>` inside the
parent `<li class="scriba-frame">` that contains it:

```html
<!-- Parent animation frame (e.g. frame 3) -->
<li class="scriba-frame"
    id="{scene-id}-frame-3"
    data-step="3">
  <header class="scriba-frame-header">
    <span class="scriba-step-label">Step 3 / N</span>
  </header>

  <!-- Content BEFORE the substory block (apply/highlight/recolor/annotate
       commands that appear in the parent step before \substory) -->
  <div class="scriba-stage">
    <svg ...><!-- parent step SVG --></svg>
  </div>
  <p class="scriba-narration" id="{scene-id}-frame-3-narration">
    <!-- parent \narrate text, if present before \substory -->
  </p>

  <!-- Substory block, rendered immediately after parent step content -->
  <section class="scriba-substory"
           role="group"
           aria-label="Sub-computation: {title option}"
           data-substory-id="{substory-id}"
           data-substory-depth="1">
    <ol class="scriba-substory-frames">

      <li class="scriba-frame scriba-substory-frame"
          id="{scene-id}-frame-3-substory-1-frame-1"
          data-step="1"
          data-substory-depth="1">
        <header class="scriba-frame-header">
          <span class="scriba-step-label">Sub-step 1 / M</span>
        </header>
        <div class="scriba-stage">
          <svg ...><!-- substory step 1 SVG --></svg>
        </div>
        <p class="scriba-narration"
           id="{scene-id}-frame-3-substory-1-frame-1-narration">
          <!-- substory \narrate text -->
        </p>
      </li>

      <li class="scriba-frame scriba-substory-frame"
          id="{scene-id}-frame-3-substory-1-frame-2"
          data-step="2"
          data-substory-depth="1">
        <!-- ... -->
      </li>

      <!-- ... remaining substory frames ... -->

    </ol>
  </section>
</li>
```

### 4.2 Frame ID scheme

Substory frame IDs are constructed hierarchically:

```
{scene-id}-frame-{P}-substory-{S}-frame-{F}
```

Where:
- `{P}` = parent frame index (1-indexed, global to the animation)
- `{S}` = substory index within the parent frame (1-indexed; if a parent step
  contains two substories, they are `substory-1` and `substory-2`)
- `{F}` = frame index within the substory (1-indexed)

For depth-2 nesting:
```
{scene-id}-frame-{P}-substory-{S1}-frame-{F1}-substory-{S2}-frame-{F2}
```

### 4.3 `:target` navigation

Because substory frames have valid HTML `id` attributes, they participate in
standard browser fragment navigation. Navigating to
`#zuma-frame-3-substory-1-frame-2` highlights that substory frame with the same
`:target` CSS rule as parent frames (the `.scriba-frame:target` rule from base
spec §9.1 applies to `.scriba-substory-frame` elements as well, since they also
carry the `scriba-frame` class).

### 4.4 Print rendering

Under `@media print`, all substories are rendered expanded inline. The connecting
CSS tree indicators are preserved (see §5). There is no collapsed state in print.

---

## 5. CSS contract

Substory styling is added to `scriba-animation.css`:

```css
/* Substory wrapper */
.scriba-substory {
  margin-block-start: 0.75rem;
  padding-inline-start: 1.5rem;
  border-inline-start: 2px solid var(--scriba-border);
  position: relative;
}

/* Depth-based indent increase */
.scriba-substory[data-substory-depth="2"] {
  padding-inline-start: 3rem;
}
.scriba-substory[data-substory-depth="3"] {
  padding-inline-start: 4.5rem;
}

/* Connecting tree indicator: vertical line from border to first frame */
.scriba-substory::before {
  content: "";
  position: absolute;
  inset-inline-start: 0;
  inset-block: 0;
  width: 2px;
  background: var(--scriba-border);
}

/* Substory frames list */
.scriba-substory-frames {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(14rem, 1fr);
  gap: var(--scriba-frame-gap, 1rem);
  overflow-x: auto;
  scroll-snap-type: x mandatory;
}
.scriba-substory-frame { scroll-snap-align: start; }

/* Substory step label uses a different prefix */
.scriba-substory-frame .scriba-step-label::before {
  content: "Sub-step ";
}

/* :target for substory frames — same as base spec but no border change
   (border is already provided by the parent substory connector) */
.scriba-substory-frame:target {
  outline: 2px solid var(--scriba-link);
}

/* Print: expand all substories, stack vertically */
@media print {
  .scriba-substory {
    border-inline-start: 1px solid var(--scriba-border);
    padding-inline-start: 1rem;
    page-break-inside: avoid;
  }
  .scriba-substory-frames {
    display: block;
  }
  .scriba-substory-frame {
    margin-block-end: 0.5rem;
  }
}

/* Responsive: collapse to vertical on narrow viewports */
@media (max-width: 640px) {
  .scriba-substory-frames {
    grid-auto-flow: row;
  }
}
```

No new CSS variables are introduced beyond `--scriba-border` and `--scriba-link`
which are defined by the base spec.

---

## 6. Screen reader accessibility

The `<section>` wrapper uses `role="group"` with `aria-label="Sub-computation: {title}"`.
This groups the substory frames into a labelled region distinct from the parent
animation. Screen readers announce the group label before reading the substory
frames, giving context that the frames are a sub-computation.

Each substory `<li>` follows the same `role="img"` + `aria-labelledby` pattern
as parent frames (base spec §8.1), pointing the SVG at its own narration paragraph.

---

## 7. Error catalog (E1360–E1369)

| Code  | Severity | Meaning                                                              | Hint |
|-------|----------|----------------------------------------------------------------------|------|
| E1360 | **Error** | Substory nesting depth exceeds 3                                     | Flatten the recursion or accept narrative depth limit. Maximum depth is 3. |
| E1361 | **Error** | Unclosed `\substory` (EOF or parent `\step` reached before `\endsubstory`) | Add `\endsubstory` before the next `\step` or `\end{animation}`. |
| E1362 | **Error** | `\substory` used outside `\begin{animation}` or in prelude           | `\substory` must appear inside a `\step` block within `\begin{animation}`. |
| E1363 | Warning   | Mutation of parent-scope shape inside substory (ephemeral)           | Mutations to parent shapes inside a substory are ephemeral and will be rolled back at `\endsubstory`. The reference is allowed; this warning alerts the author that the change does not persist. |
| E1364 | **Error** | Total frame count including substory frames exceeds 100              | Reduce the number of substory steps or parent steps. |
| E1365 | **Error** | `\endsubstory` without matching `\substory`                          | Remove the unmatched `\endsubstory`. |
| E1366 | Warning   | Substory has zero `\step` blocks                                     | An empty substory emits no frames; consider removing it. |
| E1367 | RESERVED  | (reserved for future substory errors)                                | — |
| E1368 | **Error** | Text on the same line as `\substory` or `\endsubstory`               | `\substory` and `\endsubstory` must each appear on their own line. |
| E1369 | **Error** | Substory-local shape name referenced after `\endsubstory` (leaked)   | Substory shapes are destroyed at `\endsubstory`. Move the `\shape` declaration to the parent animation scope if persistent access is needed. |

---

## 8. Acceptance test — Zuma DP

The top-level frame shows `dp[2][5]` being filled. Inside that frame, a substory
traces the `dp[3][4]` sub-computation that forms the merge case.

```latex
\begin{animation}[id=zuma-demo, label="Zuma DP: dp[2][5] filled via palindrome merge"]

\shape{dp}{DPTable}{rows=6, cols=6, row_label="l", col_label="r"}
\shape{gems}{Array}{size=6, data=["R","B","B","R","B","R"], labels="0..5"}

\compute{
  # Precompute dp for a tiny example
  s = ["R","B","B","R","B","R"]
  N = len(s)
  dp = [[0]*N for _ in range(N)]
  # ... (bottom-up DP logic) ...
  dp[2][5] = 3
  dp[3][4] = 2
}

\step[label=fill-dp25]
\apply{dp.cell[2][5]}{value=${dp[2][5]}}
\recolor{dp.cell[2][5]}{state=current}
\highlight{gems.range[2:5]}
\narrate{Điền $dp[2][5] = ${dp[2][5]}$. Trường hợp merge: $s[2]="B"$ khớp $s[5]="R"$?
         Không; nhưng $s[2]="B"$ khớp $s[4]="B"$. Ta xem sub-bài toán $dp[3][4]$.}

\substory[title="Sub-problem: dp[3][4]"]

\shape{sub_gems}{Array}{size=2, data=["R","B"], labels="3..4"}

\step[label=sub-init]
\apply{sub_gems.cell[0]}{value="R"}
\apply{sub_gems.cell[1]}{value="B"}
\highlight{sub_gems.all}
\narrate{Xét đoạn $s[3..4] = $ [R, B]. Hai ký tự khác nhau: $dp[3][4] = dp[3][3] + 1 = 0 + 1 = 1$? Thực ra với Zuma $dp[3][4] = 2$.}

\step[label=sub-merge]
\recolor{sub_gems.all}{state=done}
\narrate{$dp[3][4] = ${dp[3][4]}$ (cần 2 bước để xóa [R, B]).}

\endsubstory

% Back to parent step
\step[label=fill-complete]
\recolor{dp.cell[2][5]}{state=done}
\narrate{Với $dp[3][4] = ${dp[3][4]}$, ta có $dp[2][5] = 1 + dp[3][4] = ${dp[2][5]}$.}

\end{animation}
```

Expected: frame 1 (`fill-dp25`) contains a nested `<section class="scriba-substory">` with two substory frames: `zuma-demo-frame-1-substory-1-frame-1` and `zuma-demo-frame-1-substory-1-frame-2`. Frame 2 (`fill-complete`) is a normal parent frame. Total frames: 2 parent + 2 substory = 4 toward the 100-frame budget.

---

## 9. Base-spec deltas

The following changes to `environments.md` are REQUIRED.

1. **§2.1 BNF**: Update `step_block` to allow an optional `substory_block`
   following the `narrate_cmd`:
   ```
   step_block ::= "\step" NEWLINE
                  (comment | step_cmd)*
                  narrate_cmd?
                  (comment | step_cmd | substory_block)*
   ```
   Where `substory_block` is the new non-terminal from this extension.

2. **§6.3 Frame count**: Clarify that substory frames count toward the 100-frame
   hard limit and the 30-frame soft warning. Document that E1364 is the substory-
   specific variant of E1181.

3. **§11 Error catalog**: Reserve E1360–E1369 for substory errors (E1360–E1366,
   E1368, E1369 are in use; E1367 is reserved). See §7 for the full catalog.

4. **§8.1 HTML output shape**: Note that `<li class="scriba-frame">` children
   may contain a `<section class="scriba-substory">` after the narration paragraph,
   as defined in extension E4.

5. **§3 Inner commands**: Document `\substory` / `\endsubstory` as the 10th and
   11th inner commands (paired open/close). Add their position constraint: only
   inside a `\step` block.
