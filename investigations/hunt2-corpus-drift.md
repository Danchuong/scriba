# Hunt2: unintended byte-drift of the real `examples/` corpus, published 0.26.1 → HEAD

## Hand-off Brief

HEAD (`d628b9b`) sits **three commits** past the published `v0.26.1` (`67fcaee`): one docs
commit (`20c29a6`) and two fix commits (`33e7d7f` E1105/E1104/E1115; `d628b9b` "close 16
round-1 findings"). Every fix claimed "0 golden delta / error-path only". I rendered the
**entire** `examples/` tree — **111 `.tex`**, wider than any single golden corpus — under
**both** versions, in **both** interactive and `--static` mode, and byte-compared every pair.

**Result: zero unintended drift.** All **104 renderable examples are byte-for-byte identical**
between published 0.26.1 and HEAD, in interactive mode **and** in static mode (71.4 MB per
mode compared, 0 mismatches). The **7 `expected-fail` fixtures fail under both** versions with
the **identical** error code — no example that rendered under 0.26.1 now errors under HEAD.
The fixes' claim holds on the wider corpus, not just the goldens.

Critically, this null result is **backed by a validated instrument**: a six-doc sensitivity
control proves the two environments genuinely differ and that my harness *does* detect drift —
every new guard fires under HEAD and not under 0.26.1. The fixes are surgical: **every**
output-changing surface they touch (`side=`, `reannotate ephemeral=true`, `\invariant` static,
`\note`, `strike`, `at=` compaction, the differ pure-removal record) is exercised **only** by
dedicated docs under `tests/doc_coverage/corpus/` and `tests/examples/corpus/` — which were
re-blessed in the same commits — and by **no shipped example**. The `examples/` corpus uses
none of those surfaces, so it cannot drift.

## Method (why the null result is trustworthy)

| | Env A — HEAD | Env B — published 0.26.1 |
|---|---|---|
| source | repo `.venv`, editable → repo `d628b9b` source | fresh venv `verifyB`, `pip install scriba-tex==0.26.1` from PyPI (non-editable, in `site-packages`) |
| interpreter | CPython **3.10** | CPython **3.10** (same minor — Python version eliminated as a confounder) |
| driver | repo `render.py` | byte-copy `render_driver.py`, run from scratchpad cwd so `import scriba` resolves to the **PyPI** package, not the repo |
| output | `SCRIBA_ALLOW_ANY_OUTPUT=1` → `scratchpad/outA` (no repo pollution) | `scratchpad/outB` (under its own cwd) |

Controls that make "0 diff" mean something:
- **render.py is unchanged** between `67fcaee` and HEAD (`git diff` empty) → the driver is not a
  variable; only the `scriba` package differs.
- **Same interpreter (3.10)** on both sides → no float-repr / dict-order / hash-seed skew.
- **Determinism confirmed**: `dinic`, `hld`, `elevator_rides` each render byte-stable across two
  independent Env-A runs; and all 104 A/B pairs match across independent processes.
- **Assets identical**: `stack.tex` renders to the same 505 103 bytes under both, so the ~380 KB
  KaTeX/CSS/JS inlined blob (which would otherwise drown every diff) is byte-equal — consistent
  with the commit's "scriba.js/CSS untouched".
- **Instrument sensitivity proven** (see Sensitivity Control) — the harness detects every
  intentional break, so a real drift would not have been missed.

## Totals

| Metric | Interactive | `--static` |
|---|---|---|
| Examples inventoried | 111 | 111 |
| Renderable (produce HTML) | 104 | 104 |
| **Byte-identical A vs B** | **104 / 104** | **104 / 104** |
| Unexpected drift (Z) | **0** | **0** |
| Expected-diff within `examples/` (Y) | **0** | **0** |
| `expected-fail` fixtures (both exit 2, same E-code) | 7 / 7 | 7 / 7 |
| Now-erroring — rendered under 0.26.1, fails under HEAD (W) | **0** | **0** |

Corpus breakdown (111): algorithms 20 (dp 4, graph 6, misc 5, string 1, tree 4), cses 10,
demos 4, editorials 5, fixtures 24 (pass 17 + expected-fail 7), integration 20, primitives 19,
quickstart 5, smoke 4.

## Per-fix attribution — why every fix lands 0 bytes on `examples/`

Each fix is either an **error-path guard** (changes stderr/exit for broken input, never HTML for
valid input) or an **output change** whose coverage doc lives outside `examples/`.

| Fix (commit) | Class | Surface in `examples/`? | Byte impact on examples |
|---|---|---|---|
| E1105 `\apply` unknown key (`33e7d7f`) | guard | none | 0 |
| E1104 Tree pairs `nodes=[[id,val]]` (`33e7d7f`) | guard | none | 0 |
| E1115 selector-warn prefix (`33e7d7f`) | stderr text | n/a (not HTML) | 0 |
| E1123 9 decoration cmds reject unknown params (`d628b9b`) | guard | no typo'd params in corpus | 0 |
| `\apply state=` → E1105 "use `\recolor`" (`d628b9b`) | guard | migrated demos live in `tests/`, not `examples/` | 0 |
| Equation `tex=`+`lines=` → E1530 (`d628b9b`) | guard | none | 0 |
| double `\zoom` → E1124 (`d628b9b`) | guard (already E1543 in 0.26.1) | none | 0 |
| `side=` threaded to smart-label (`d628b9b`) | **output** | **0** — only `tests/doc_coverage/corpus/annot_annotate_side_below` | 0 |
| `reannotate ephemeral=true` reverts recolor (`d628b9b`) | **output** | **0** — only `tests/doc_coverage/corpus/annot_reannotate_ephemeral`¹ | 0 |
| strike skips hidden targets (`d628b9b`) | **output** | 0 (`strike` unused in examples) | 0 |
| `\note` wrap/clamp/re-anchor (`d628b9b`) | **output** | 0 (`\note` unused in examples) | 0 |
| bare-shape `\annotate` strike/label (`d628b9b`) | **output** | 0 (bare-shape strike form unused) | 0 |
| `at=` board compaction (`d628b9b`) | **output** | 0 (`at=[` unused in examples) | 0 |
| `\invariant` static + print fallback (`d628b9b`) | **output (static)** | 0 (`\invariant` unused in examples) — static pass also 104/104 identical | 0 |
| differ: drop bogus pure-removal `element_add` (`d628b9b`) | **output (manifest)** | 0 — the **1** re-blessed golden corpus-wide is `tests/examples/corpus/anim_clarity_showcase.html` (`\| 2 +-`), outside `examples/`; the shrink/removal fixtures (`0[1-4]_*_shrink`) don't hit the bare-shape pure-removal path and stay byte-identical | 0 |
| TraceTable manifest arbitration (`d628b9b`) | docs/tests only | tracetable examples identical | 0 |

¹ `examples/integration/test_reference_edge_cases.tex` contains the *word* "ephemeral", but only
as a shape `label=` and narration text describing highlight auto-clear — **not** the
`\reannotate … ephemeral=true` parameter the fix changed. Its identical output is correct, not
masked drift.

## Now-erroring inventory (W = 0)

No example that rendered under 0.26.1 fails under HEAD. The 7 `examples/fixtures/expected-fail/`
docs fail under **both** versions, with the **same** error code each — the new guards did not
even change *which* error fires:

| fixture | Env A (HEAD) | Env B (0.26.1) |
|---|---|---|
| 09_command_typo_hint | E1006 | E1006 |
| 11_selector_unknown_shape | E1116 | E1116 |
| 13_apply_before_shape | E1116 | E1116 |
| 15_percent_in_braces | E1015 | E1015 |
| 16_empty_foreach_iterable | E1173 | E1173 |
| 20_cumulative_budget | E1152 | E1152 |
| 21_list_alloc_cap | E1173 | E1173 |

## Sensitivity Control — proof the harness detects drift & the breaks are intentional

Six trap docs, each exercising one new guard on real syntax, rendered under both envs. Every
guard fires under HEAD; 0.26.1 accepts (or, for double-zoom, already errored). This proves
(a) the two environments are genuinely different code, so the 104× "identical" is not two copies
of the same build, and (b) each break is by-design and hits **zero** shipped example.

| trap | HEAD | 0.26.1 | verdict |
|---|---|---|---|
| `\apply{s}{lazy=true}` | E1105 | ok (silently dropped) | new break — intentional |
| `\apply{s}{state=done}` | E1105 | ok (silently dropped) | new break — intentional |
| Tree `nodes=[[1,10],[2,20]]` | E1104 | ok (silently mangled) | new break — intentional |
| `\annotate …{colour=red}` | E1123 | ok (silently dropped) | new break — intentional |
| double `\zoom` in one step | E1124 | **E1543** | already errored in 0.26.1; only the code/message changed — **not** a new break |
| Equation `tex=`+`lines=` | E1530 | ok (accepted) | new break — intentional |

Five guards convert a previously-**silent-swallow** into a loud error; one (double-zoom)
re-codes an already-erroring case. None is triggered by any of the 104 renderable examples.

## Golden-coverage note

`tests/golden/examples/sync_corpus.py` pins every example that has an on-disk sibling `.html`:
**104 renderable examples are byte-pinned** in `tests/golden/examples/corpus/` (so CI already
guards them — consistent with 0 drift). The **7 `expected-fail` fixtures are uncovered by
construction** (they produce no HTML) — this hunt is the byte-level check they can't get from a
golden, and they came back clean (same E-code both sides). Minor housekeeping: 3 golden stems
(`anim_clarity_showcase`, `apt_window_diagram`, `decoration_spiral`) are pinned in the corpus but
no longer live under `examples/` — stale entries, unrelated to drift.

## Conclusion + Confidence

**No unintended byte drift and no unintended breakage exists in the `examples/` corpus between
published 0.26.1 and HEAD.** The three-commit delta is exactly what it claimed: error-path
guards that fire on broken input no shipped example uses, plus output changes whose coverage
docs live in `tests/` and were re-blessed in-commit. Interactive and static renders of all 104
renderable examples are byte-identical; the 7 expected-fail fixtures fail identically.

**Confidence: HIGH.** The instrument is validated (harness detects all 6 intentional breaks;
determinism confirmed; same interpreter and unchanged driver isolate the package source as the
only variable; assets proven byte-equal), the comparison is exhaustive (111 docs × 2 modes,
~143 MB byte-compared with `cmp`), and every fix is individually attributed to zero example
impact. The only residual is untested surface *combinations* not present in any example — but
by definition those cannot cause drift in a corpus that doesn't contain them.

## Raw data / reproduction

- Harness: `scratchpad/run_all.sh` (interactive), `scratchpad/run_static.sh` (`--static`).
- Manifests: `scratchpad/manifest.tsv`, `scratchpad/manifest_static.tsv`
  (`rel  exitA  exitB  IDENTICAL|DIFFER|MISSING  flatname`).
- Outputs: `scratchpad/outA*`, `scratchpad/outB*`; traps: `scratchpad/traps/`.
- Env A: `.venv/bin/python render.py <abs.tex> [--static] -o <out>` with `SCRIBA_ALLOW_ANY_OUTPUT=1`.
- Env B: `cd scratchpad && verifyB/bin/python render_driver.py <abs.tex> [--static] -o <out>`
  (verifyB = CPython 3.10 + `scriba-tex==0.26.1` from PyPI).
- Interactive: `identical 104 / differ 0 / missing 7`. Static: `identical 104 / differ 0 / missing 7`.
  Re-`cmp` of all 104 identical pairs: 0 mismatches.
