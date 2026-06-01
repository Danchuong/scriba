# SCRIBA-TEX-REFERENCE.md — Documentation Audit

**Date:** 2026-06-01
**Target:** `docs/SCRIBA-TEX-REFERENCE.md` (1493 lines)
**Goal of the doc:** "Read this one file → know how to author valid Scriba `.tex`."
**Audit verdict:** Goal met at **~75%**. Solid for the common 80% of authoring,
but gaps in field clarity, freshness, and signal-to-noise weaken the
"one file is enough" promise.

---

## Evaluation criteria (8)

| # | Criterion | Meaning | Score |
|---|-----------|---------|-------|
| 1 | Completeness | Every command / primitive / param is present | High |
| 2 | Field clarity | Each param documents type, default, allowed values, example | **Low** |
| 3 | Consistency | No internal contradictions | Medium |
| 4 | Correctness / freshness | Matches current code behaviour | **Medium-Low** |
| 5 | Self-sufficiency | "One file is enough" — no required jumps to other files | **Medium** |
| 6 | Signal-to-noise | No internal / forward-compat fields mixed into author-facing body | **Low** |
| 7 | Disambiguation | Similar-looking syntax is clearly distinguished | Medium |
| 8 | Navigability | Fast to find what you need; good TOC | High |

---

## 1. Ambiguities / contradictions (criteria 3, 4)

### a) Interpolation reliability is contradictory — highest priority
- §5.11 (L492): `value=${i}` "supported since v0.8.2".
- §13.2 (L1355–1375): "`${var}` outside `\foreach` is **unreliable**, may fail."
- Commit `cbdd7ce` (2026-06-01) added `_resolve_interp` so `\apply{x}{value=${scalar}}`
  now resolves compute scalars → **§13.2 is now partly stale.**
- The true model is two-dimensional:
  `(inside / outside \foreach) × (value position / selector-index position)`.
  The doc blends these, so a reader still cannot predict when `${x}` resolves.

**Fix:** add a 2×2 reliability table; reconcile §13.2 with the `cbdd7ce` fix.

### b) Tree vs Graph node-id type rule is lumped together
- §8 (L942–943): "bare integer is coerced to `int`; quoted ids must match the
  declared type."
- Commit `8989a10` (2026-06-01) normalizes **Tree** node ids to `str`. So for Tree
  the "must match declared type" rule is now **false** (both `T.node[8]` and the
  string form resolve). **Graph** is still strict int/str.
- The divergence is undocumented (introduced by today's change).

**Fix:** split §8 into Tree (str-normalized) vs Graph (strict) behaviour.

### c) Boolean casing `true` vs `True`
- LaTeX examples use `directed=true` / `false` (L219, L666).
- §13.10–13.11 prose uses `directed=True`, `global_optimize=True` (Python caps).
- The doc never states both forms are accepted → reader unsure which to type.

### d) State count mismatch
- §5.7 (L338) lists **8** states (omits `highlight`).
- §6 (L626) lists **9** (includes `highlight`).

### e) Graph core params have no param table
- `nodes, edges, directed, layout, layout_seed, show_weights` appear only in
  prose / examples (L663–672); the param table at L678 covers only secondary
  params. `directed`'s default is stated nowhere.

---

## 2. Fields exposed but the author doesn't need (criterion 6 — noise)

Forward-compat / internal items mixed into the author-facing reference:

| Field / flag | Location | Problem |
|---|---|---|
| `global_optimize` | §7.4 L685, §13.11 | **no-op**, emits a UserWarning — why expose to authors? |
| `grid` (diagram option) | §10 L1267 | "accepted but **ignored** — forward-compat placeholder" |
| `SCRIBA_DEBUG_LABELS`, `SCRIBA_LABEL_ENGINE` | §13.12 | dev-only env flags ("never enable in production") |
| R-22 / `side_hint` / "Hirsch 1982 NE-preference ladder" / R-06 (planned v0.12) | §5.8 L361–371 | internal-spec jargon bleeding into an authoring doc |
| `tint_by_source` / `tint_by_edge` | §7.4 | niche, rarely used |

**Fix:** move these to an "Internal / forward-compat" appendix, or drop them, to
keep the main body clean.

---

## 3. Fields where you can't tell what to fill in (criterion 2 — significant)

| Field | Location | Missing |
|---|---|---|
| `colorscale` (Matrix) | L793 | default `"viridis"` but **no list of other valid names** |
| `add_region=...` (Plane2D) | L838 | literally `...` — **no region syntax given** |
| `regions` / `polygons` (Plane2D) | L826–827 | "inline batch" but **element format unspecified** |
| `add_line=("y=x",1,0)` | L835 | what do the 3 tuple elements mean? (eq string + slope? intercept?) |
| `data` (Matrix) | L785 | `[0.1,0.3,...]` — **flat row-major or nested 2D?** |
| `data` (Grid) | L646 | `${matrix_data}` — shape unstated |
| `ticks` (NumberLine) | L778 | `ticks=25` — **count of ticks or spacing?** |
| `labels` (Array) | L639 | only `"0..7"` shown — can it be a list? `labels` vs `label` difference? |
| `tooltip=` (`\apply`) | L332 | mentioned **once**, never documented — where does it show? what does it do? |

---

## 4. Self-sufficiency gaps (criterion 5)

Line 3 promises "**Read this one file**", but several spots push the reader out:
- §5.8 (L344): "see spec/smart-label-ruleset.md … Read that document before…"
- §6 (L628): color CSS token values → external CSS file
- §5.2 (L271), §15 (L1469): point to a test file / `errors.py`

Pushing *internals* out is fine. But **color values** and the **colorscale name
list** are needed at authoring time → they should be inlined.

---

## Prioritized fixes (for the "one file → usable" goal)

1. **2×2 interpolation table** + update §13.2 after the `cbdd7ce` fix. *(worst contradiction)*
2. **One full param table per primitive** (type / default / allowed / example) —
   fixes the Graph core params plus the 9 "can't fill" fields.
3. Fix §8 for **Tree (str-normalized) ≠ Graph (strict)** — caused by today's change.
4. Move **forward-compat / dev noise** to an appendix.
5. Inline **colorscale names** and **annotation color values**.
6. Lock the `true`/`false` casing; fix the 8-vs-9 state-count mismatch.

**Suggested commit grouping:** start with #1 and #3 (they are contradictions and
were introduced by today's code changes), one commit per group.
