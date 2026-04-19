# SCRIBA-TEX-REFERENCE.md Audit — Aggregate Summary

**Date:** 2026-04-19
**Target:** `docs/SCRIBA-TEX-REFERENCE.md` (928 lines, 14 sections)
**Method:** 6 parallel agents, one per section bucket, each verifying every claim against source code.

---

## Verdict by Bucket

| # | Bucket | Sections | Score | Report |
|---|--------|----------|-------|--------|
| 1 | LaTeX syntax | §1–2 | 6/10 | [01-latex-syntax.md](01-latex-syntax.md) |
| 2 | Environments | §3–4 | 5/10 | [02-environments.md](02-environments.md) |
| 3 | Inner commands | §5 | 5/10 | [03-inner-commands.md](03-inner-commands.md) |
| 4 | Primitives/states/selectors | §6–8 | 5/10 | [04-primitives-states.md](04-primitives-states.md) |
| 5 | Examples & patterns | §9, §12 | 7/11 PASS | [05-examples-patterns.md](05-examples-patterns.md) |
| 6 | Options/colors/gotchas/limits | §10–11, §13–14 | 8/10 | [06-options-gotchas.md](06-options-gotchas.md) |

**Overall:** ~6/10 — structural skeleton correct, but multiple high-impact accuracy bugs.

---

## CRITICAL (must fix — will mislead AI to produce broken `.tex`)

| # | Section | Issue |
|---|---------|-------|
| C1 | §2 | `equation`, `align`, `align*` pass validator but have no rendering handler — `\begin`/`\end` leak as literal text. AI probing the validator will think they're safe. |
| C2 | §6 | All 8 colored-state hex values are stale Wong/CBF palette. Code migrated to Radix Slate (e.g. `done` = `#e6e8eb` slate, not `#009E73` green). Doc colors do not match output. |
| C3 | §9.5 + §12.3 | Two examples use `\compute` + `\foreach{i}{${binding}}`. Without a Starlark host, `\compute` silently no-ops; runtime then raises E1173. Doc never states `\compute` requires a host. |

---

## HIGH (factually wrong — AI will write code that breaks or no-ops)

| # | Section | Issue |
|---|---------|-------|
| H1 | §2.7 | `\section*{}` starred variants leak as raw text, not silently ignored. |
| H2 | §2.2 | Triple-dollar `$$$...$$$` math implemented but undocumented. |
| H3 | §2.2 | Legacy aliases `\bf`, `\it`, `\tt` implemented but absent. |
| H4 | §3 | `width`, `height`, `layout` parsed into `AnimationOptions` but never read; `grid` accepted by validator but not stored — all silently no-op. |
| H5 | §3 | `\narrate` upper-bound description inverted: ≥2 raises E1055; 0 silently allowed. Doc says "exactly one". |
| H6 | §4 vs §3 | `\highlight` is **ephemeral** in animation but **persistent** in diagram (`allow_highlight_in_prelude=True`). Behavioral asymmetry undocumented. |
| H7 | §3 | E1053 (`\highlight` banned in animation prelude) entirely undocumented. |
| H8 | §5.5 | `\apply` lists phantom `tooltip=` param — zero implementation, silently does nothing. |
| H9 | §5.7 | `\recolor` doc lists 8 valid states — code `VALID_STATES` has 9; `highlight` omitted (used by Stack/Graph/Plane2D). |
| H10 | §5.9 | `\reannotate{color=…, arrow_from=…}` signature implies both optional; `color` is **required** (E1113 if absent). |
| H11 | §7.7 | Matrix missing 6 ACCEPTED_PARAMS: `colorscale`, `cell_size`, `vmin`, `vmax`, `row_labels`, `col_labels`. |
| H12 | §7.10 | MetricPlot missing 9 ACCEPTED_PARAMS: `ylabel_right`, `grid`, `width`, `height`, `show_legend`, `show_current_marker`, `xrange`, `yrange`, `yrange_right`. |

---

## MED (incomplete / surprising)

| # | Section | Issue |
|---|---------|-------|
| M1 | §2 | 9 size cmds (`\large`, `\small`, `\tiny`, …) implemented but not listed. |
| M2 | §2.8 | Smart-quote syntax (` ``…'' `, `` `…' `` ) implemented but absent. |
| M3 | §2 | Validator-accepted passthrough envs (`quote`, `verbatim`, `figure`, …) render inline without block structure — surprising, undocumented. |
| M4 | §4 | Diagram `label=` parsed but silently dropped (no `aria-label` emitted). |
| M5 | §3/§4 | Stray `\end{diagram}` silently skipped; stray `\end{animation}` raises E1007. Asymmetry undocumented. |
| M6 | §3 | Frame-limit counting includes substory frames; doc implies only top-level frames count. |
| M7 | §5.12 | `\substory` accepts `id=` option (not just `title=`); doc only shows `title`. |
| M8 | §5.6 | `\annotate` `label` default is `None`, not `""`. Some primitives distinguish. |
| M9 | §8 | Quick-ref table shows `—` in "All" column for 6 primitives (CodePanel, HashMap, LinkedList, Queue, VariableWatch, MetricPlot) that DO support `.all`. |
| M10 | §10 | `grid=true` env option accepted but never reaches `AnimationOptions`. Silent no-op. |
| M11 | §14 | Annotations-per-frame cap (500, `_MAX_ANNOTATIONS_PER_FRAME`, hard error E1103) not documented. |
| M12 | §12.1 | Cursor snippets are fragments (no `\begin{animation}` / `\step` wrapper); literal copy-paste fails. |

---

## LOW (clarity / completeness)

| # | Section | Issue |
|---|---------|-------|
| L1 | §2.6 | `\hline` first-class but absent. |
| L2 | §2.7 | `\includegraphics` supports `scale=`, `height=`, multiple units; only `width=` shown. |
| L3 | §13 | Windows missing SIGALRM Starlark backstop — `RuntimeWarning` emitted, no gotcha entry. |
| L4 | §5 catalog | E1005 description "Invalid option" lags actual usage (also raised for duplicate `\step` labels). |
| L5 | §7.8 Graph | `layout_lambda`, `seed` alias undocumented. |
| L6 | §7.9 Plane2D | `aspect`, `width`, `height`, `points`, `lines`, `segments`, `polygons`, `regions` absent. |
| L7 | §7.6 NumberLine | `labels` param absent. |
| L8 | §7.4 CodePanel | `source` string-form param absent. |
| L9 | §9.2 | Weighted-edge 3-tuple format not cross-referenced to graph spec. |
| L10 | §9.5 | `\foreach{i}{0..4}` inclusive-both-ends not stated. |

---

## Counts that are correct

- §5 inner cmd count: doc 12, actual 12 ✅ (`\unhighlight`, `\frame`, `\pause` correctly absent)
- §7 primitive count: doc 16, actual 16 ✅
- §11 annotation colors: 6 documented, 6 in `VALID_ANNOTATION_COLORS` ✅
- §14 limits: 10/10 numerical limits exact match ✅
- §10 documented options: 5/5 names exist ✅

---

## Stack permissive design (NOT a finding)

Stack has empty `ACCEPTED_PARAMS` frozenset. This is intentional opt-out per `base.py` (`if self.ACCEPTED_PARAMS:` skips strict validation). Test `test_unknown_kwargs_ignored` codifies the contract. **Do not add params to Stack's frozenset** — flagged by Agent 4 as "noted, not a bug".

---

## Recommended Fix Wave

**Wave R1 (CRITICAL)** — 3 fixes, ~30 min:
- C1: Either implement `equation`/`align` rendering, or remove from validator + document as unsupported.
- C2: Replace all 8 hex values in §6 with Radix Slate palette from `_types.py:74–86`.
- C3: Add prerequisite note "requires Starlark host" to §9.5 + §12.3, or rewrite to literal-form `\foreach{i}{[0,2,4]}`.

**Wave R2 (HIGH)** — 12 fixes:
- H1–H3: Document hidden cmds + starred-variant leak in §2.
- H4–H7: Strip dead env opts from §3 (or implement); fix `\narrate` description; document `\highlight` persistence asymmetry; add E1053.
- H8–H10: Remove phantom `tooltip=`; add `highlight` to recolor states; mark `color` required in `\reannotate`.
- H11–H12: Add 6 Matrix + 9 MetricPlot params to §7.

**Wave R3 (MED + LOW)** — 22 fixes: doc patches, no code changes.

Total fix surface: 3 CRIT + 12 HIGH + 12 MED + 10 LOW = **37 findings**.
