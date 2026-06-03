# `layout_seed` — what it is, and is it a problem?

**Date:** 2026-06-03
**Status:** analysis / explainer (no code change proposed here)
**Audience:** content authors ("người ra đề") + maintainers

## TL;DR

- `layout_seed` is an **optional** Graph parameter. Default `42`. Most authors
  should never touch it.
- It controls the **random starting positions** of the force-directed layout,
  not the quality of the result. Same seed → same picture (reproducible);
  different seed → different scatter → different final layout.
- The real footgun: a force layout can look **lopsided** (nodes shoved to the
  canvas edge, disconnected nodes flung to a corner) for *some* seeds, and the
  only "fix" today is to **guess another integer** until it looks nice. That is
  a poor authoring experience, but it is **cosmetic**, not a correctness bug.
- After the A1 position-pinning fix (2026-06-03), the layout is computed **once**
  at construction and frozen for the whole animation. So the seed now decides the
  look of *every* frame — its influence went up, which makes good defaults more
  important.

## 1. What it actually is

`layout="force"` places nodes with the **Fruchterman-Reingold** algorithm
(`scriba/animation/primitives/graph.py:395`):

1. Seed a PRNG: `rng = random.Random(seed)` (`graph.py:423`).
2. Scatter every node to a **random** initial `(x, y)` (`graph.py:424–428`).
3. Iterate "forces": edges pull endpoints together, all nodes repel each other,
   cooling over ~iterations until positions settle.
4. A post-pass nudges any remaining overlaps apart.

`layout_seed` only feeds step 1. So:

- It makes the layout **deterministic**: same graph + same seed → byte-identical
  positions on every render (important for golden tests and reproducible docs).
- It does **not** improve the layout. It just selects *which* random start you
  get, and different starts converge to different (sometimes worse) arrangements.

Aliases & default: canonical key `layout_seed`; bare `seed` accepted as an alias
(`layout_seed` wins if both given); default **42**.

## 2. The problem, precisely

Three distinct issues get lumped together as "the seed problem":

1. **Force layout has no notion of "pretty".** It minimises an energy function,
   not visual balance. For small/sparse graphs the minimum often sits with nodes
   pinned to the canvas border (repulsion dominates), which reads as "lệch".
2. **Disconnected nodes get flung to a corner.** A node with no edges feels only
   repulsion, so it's pushed as far from everyone as possible — a corner. This is
   exactly what happened in the demo: `D` had no edge at construction time, so it
   landed in a corner regardless of seed.
3. **The only knob is a magic integer.** When the auto-layout looks bad, the
   documented remedy is "try another `layout_seed`." There is no semantic control
   ("spread out", "center", "rank top-to-bottom") at the `force` layer — you brute
   force integers. That is the genuine UX wart.

None of these produce a *wrong* graph — topology, weights, and labels are always
correct. The cost is purely aesthetic.

## 3. Evidence (measured via Chrome CDP)

Same 4-node graph (`A,B,C,D`, edges `A-B`, `A-C` at construction), node `D`
disconnected initially:

| seed | A | B | C | D | shape |
|------|---|---|---|---|-------|
| `7`  | (374,145) | (380,20) | (380,280) | (20,280) | A/B/C crammed on the right edge, D alone bottom-left |
| `42` | (20,204)  | (20,20)  | (175,280) | (380,20) | more spread (A,B left · C bottom-mid · D top-right) |

Both are valid; `42` is merely better balanced. In both, `D` sits on a border
because it has no edge to pull it inward. Changing the seed reshuffles *which*
border — it does not make `D` join the cluster.

## 4. Who needs to care

**Author — usually no.** Omit `layout_seed` entirely; the default `42` is fine
for the large majority of small, fully-declared graphs.

**Author — only when:**
- the auto-layout genuinely looks bad and they want to polish → try a few seeds;
- they need pixel-reproducibility across renders (screenshots, diffing) → pin one;
- the graph **starts sparse and grows** via `add_edge` → the initial frame has
  disconnected nodes that the seed can't rescue.

**Maintainer — yes,** because "guess an integer" is a weak authoring story and
worth improving (see §6).

## 5. Interaction with the A1 pinning fix

Before A1, the layout was re-solved on every edge mutation, so the seed's
influence was diluted (and unstable). After A1 (`graph.py` no longer relayouts on
`add_edge`/`remove_edge`), the layout is decided **once at construction from the
initial node+edge set** and **frozen** for the whole animation.

Consequence: the seed now fully determines the look of *every* frame, and — more
importantly — the *initial* topology decides node placement. A node that is
disconnected at construction stays in its corner for the entire animation even
after an edge is later added to it. This is the right stability tradeoff (no
teleporting), but it shifts the burden onto **declaring a good initial topology**.

## 6. Recommendations

### For authors (no code change)
1. **Declare all nodes _and_ all edges up front**, then animate with
   `\recolor` / state (hide/show/emphasise) instead of `add_edge`/`remove_edge`.
   With full topology at construction, no node is disconnected → no corner-fling,
   and (post-A1) positions stay stable anyway.
2. For small graphs (≤20 nodes) prefer **`layout="stable"`** — deterministic,
   tends to spread evenly, and you stop thinking about seeds.
3. Only reach for `layout_seed` as a last-resort cosmetic tweak; if you do, pin a
   value you like and leave a comment why.

### For maintainers (potential product fixes — not yet scoped)
- **Auto-seed selection:** try N seeds at build time, score each (border-hugging
  penalty, edge crossings, aspect balance), keep the best. Removes the magic
  integer for the default case. Cost: N× layout solves at render time.
- **Disconnected-node handling:** detect isolated nodes and place them in a tidy
  reserved lane (e.g. a row) instead of letting repulsion fling them to a corner.
- **Semantic knobs** instead of a raw seed: e.g. `layout="stable"` already exists;
  consider a `compact`/`spread` hint so authors express intent, not an RNG seed.
- **Author warning:** when a Graph has disconnected nodes at construction, emit a
  soft note pointing to "declare edges up front or use layout=stable" — turns a
  silent cosmetic surprise into actionable guidance.

## 7. Verdict

`layout_seed` is **not a bug and not something most authors must understand.** It
is an optional reproducibility/cosmetic knob with a reasonable default. The only
*real* issue is the authoring ergonomics around bad auto-layouts (magic-integer
tuning) and disconnected-node corner-flinging — both cosmetic, both avoidable
today by declaring full topology or using `layout="stable"`, and both improvable
later with auto-seed selection or isolated-node handling.
