# Hunt2: Adversarial attack on the round-1 fixes (commit d628b9b)

## Hand-off Brief

I attacked the 16 round-1 fixes in `d628b9b` on their own axes — trying to make each
one either **false-positive on a legit document** or **break a path it was supposed to
salvage**. Every attack was rendered through `render.py` (author-facing) and, for the
false-positive class, cross-checked with a **full 422-doc corpus differential** rendered
at both `d628b9b` and its parent `d628b9b^`.

**The fixes are robust. Zero Confirmed bugs of MED+ severity.** The decisive result is
the corpus differential: **all 422 shipping corpus docs produce byte-identical outcomes
(ok / warn:CODE / err:CODE) at both commits** — the new guards (E1123 command-param,
E1105 `state=`, E1124 double-zoom, E1112 `side`, E1125 note-clamp, E1530 tex+lines)
introduce **no false positive on any legit doc**. Every E1123 I could raise came from a
genuinely-invalid key (e.g. `id=` on `\annotate`, which has no such field); every other
error I hit while probing was a *different* pre-existing rule (E1005 value-quoting, E1491
`\trace` needs cells, E1006 command-forbidden-in-foreach), never the new guard.

The two most subtle fixes both survive adversarial scrutiny:

- **differ F4 (pure-removal element_add suppression)** *looks* dangerous — a pure
  `\apply{a}{remove=0}` now emits `tr=null, fs=0` even though the array SVG shifts
  (`[1,2,3,4,5]→[2,3,4,5]`). I traced the JS runtime: with `tr=null`, `show()` falls
  through to `snapToFrame()`, which does a full `stage.innerHTML=frames[i].svg` swap
  (`scriba.js:117`), so the shift still lands. `fs` is only ever consulted *inside*
  `animateTransition` (called only when `tr` is non-null). The pipeline is self-consistent
  (`tr` non-null ⟹ `fs=svg_changed`). Mixed `remove+insert` correctly **keeps**
  `element_add` (`is_structural` stays True). **Safe, verified end-to-end.**

- **reannotate `ephemeral=true` revert** is correct in all three orderings: basic revert,
  twice-in-one-step (keeps the *earliest* prior colour), and ephemeral-then-persistent
  (persistent clears the pending revert and sticks).

**One LOW/informational nit** (not a clean regression): a `\note` whose text contains a
literal `\n` leaks the raw newline char into a `<tspan>` under the new wrap path — but the
pre-fix single-line path also mangled `\n` (collapses to whitespace), the visual result is
identical (SVG whitespace-collapses the char to a space either way), and `\n` in notes is
undocumented. Barely worth flagging.

**Complementary to** the sibling round-2 files `hunt2-corpus-drift.md` and
`hunt2-traceback-fuzz.md` — this file owns the *fix-regression* axis (false positives +
salvage-path integrity). No overlap.

---

## Findings table

Evidence grade: **Confirmed** = rendered, cited proof. All rows rendered via
`.venv/bin/python render.py <p>.tex` (SCRIBA_ALLOW_ANY_OUTPUT=1). "Refuted" = the attack
did **not** break the fix (the fix is correct), proven by render.

| id | fix attacked (round-1) | verdict | sev | repro / rendered proof |
|----|------------------------|---------|-----|------------------------|
| **A1** | E1123 guard — `\foreach` body substitution | **Refuted** | — | `\foreach{i}{0..2}\annotate{a.cell[${i}]}{label="x${i}",color=info}\endforeach` → rc=0. focus/reannotate/cursor in foreach also rc=0. Guard runs once on the literal-key template; `${i}` is only in values. |
| **A2** | E1123 — value is an InterpolationRef | **Refuted** | — | `\annotate{a.cell[0]}{label="val=${c}"}` → rc=0; label renders `val=2`. Guard checks keys only. |
| **A3** | E1123 — legacy `\cursor{a.cell}{2}` positional | **Refuted** | — | Legacy `{2}` builds an **empty** `kv` (`_grammar_commands.py:866-870`: only `=`-parts collected), so no synthetic key reaches the guard. rc=0. |
| **A4** | E1123 — `\playeach`-generated commands | **Refuted** | — | `\playeach` desugars to AST `CursorCommand`/`ApplyCommand` directly; `_validate_command_params` is **parse-time only**, so generated commands bypass it. Has its own action-key guard (`_grammar_playeach.py:102`). |
| **A5** | E1123 — quoted values containing `=` `,` `:` | **Refuted** | — | `\note{n1}{text="x = y = z",color=info}`, `\annotate{..}{label="a=b, c=d"}`, `label="ratio 3:4"` → rc=0, values intact in aria-label. Splitter not fooled → no false key. |
| **A6** | E1123 — false positive on any shipping doc | **Refuted (decisive)** | — | **422-doc corpus differential d628b9b^ vs d628b9b: 0 outcome changes.** No legit doc gains E1123/E1105/E1124/E1112/E1125/E1530. |
| **A7** | E1123 — frozenset omits a key a handler reads | **Refuted** | — | Audited all 9 handlers' `params.get`/`params[...]` reads vs their frozensets (`_grammar_commands.py:62-107`): every set matches its handler exactly, incl. emit-time downstream reads (`side`,`position`,`leader`,`arrow`) in `_svg_helpers.py:2126,2486`. |
| **B1** | `\apply{X}{state=}` → E1105 (scene / foreach / substory / mixed) | **Refuted** | — | E1105 fires in all four paths (rc=2). `\apply{a.cell[0]}{value=9, state=done}` also E1105 (first-unknown-key), steering to `\recolor`. `state=` was always read by nobody, so no legit path loses function. `\recolor` is a **separate** handler (`scene.py:1035`), unaffected. |
| **C1** | `side=` + `position=` together | **Refuted** | — | `\annotate{a.cell[1]}{position=below, side=above}` → key `a.cell[1]-position-below`, label_y=63 — **position wins, side ignored** (side is "soft; pinned at consumer" per commit). `position=` still works; side doesn't destructively override. |
| **C2** | `side=inside` excluded from enum (E1112 msg) | **Refuted** | — | rc=2 `E1112 unknown annotation side 'inside'; valid: above, below, left, right` — accurate, excludes `inside`. |
| **C3** | reannotate ephemeral revert (twice / then-persistent / double-ephemeral) | **Refuted** | — | Basic: F0 info→F1 error→F2 info. Twice-in-step: reverts to *earliest* (info, not warn). Then-persistent: F1 error→F2 good→F3 good (sticks). Double-ephemeral: no crash, annotation removed F1. |
| **D1** | `\note` wrap — `$math$` in note | **Refuted (pre-existing)** | — | Notes strip math via `strip_math_markup` (`_frame_renderer.py:1069`) — plain-text, never KaTeX — at **both** commits. Wrap can't split a formula that's already stripped. (Round-1's "renders KaTeX" claim was a mis-observation; not a d628b9b regression.) |
| **D2** | `\note` wrap — CJK long note (width metrics) | **Refuted** | — | 40-char Chinese note wraps to 4×12-char lines, rect w=144 in 208 board, rc=0, no clip, no false E1125. |
| **D3** | `\note` wrap — explicit `\n` in text | **LOW / info** | LOW | Raw newline leaks into a `<tspan>` under the new wrap path; but pre-fix also mangled it (single-line, collapses to space) and SVG whitespace-collapses the char identically → no visible delta. `\n` in notes undocumented. Not a clean regression. |
| **D4** | `\note` wrap — E1125 clamp path + wrapped note on a ZOOMED frame | **Refuted** | — | Note×`\zoom{a.cell[0]}`: note re-anchors to x=12 **inside** crop `viewBox=4 4 76 56` (was off-canvas x=333 in round-1 C2), wraps, E1125 warns. Wrap + re-anchor compose. E1125 text accurate (`errors.py:256-259`). |
| **E1** | `at=` compaction + `\zoom` on a compacted board | **Refuted** | — | `a at=[0,0]`, `b at=[100,100]`, `\zoom{b.cell[1]}` → `viewBox=270 64 76 56` — crop lands on b's **remapped** (compacted) offset, not 100×20px away. |
| **E2** | `at=` compaction — shape hidden mid-timeline (per-frame occupancy) | **Refuted** | — | b's cells hidden then shown across frames → board `viewBox=0 0 412 64` **stable every frame**. Tracks computed once from `placements` (declarations), not per-frame state. |
| **E3** | `at=` compaction — negative `at=` still caught | **Refuted** | — | `at=[-1,0]` → rc=2 `E1540 row and col must be non-negative integers`. |
| **F1** | strike hidden-skip — reappear when visible next frame | **Refuted** | — | cell[1] hidden F0 (`strikes=[]`), idle F1 (`strikes=['a.cell[1]-strike']`) — skip is per-frame emit; strike **reappears** correctly. |
| **F2** | strike hidden-skip — strike over `\focus` dim (dim≠hidden) | **Refuted** | — | cell[1] focus-dimmed (`defoc=2`) still carries `a.cell[1]-strike` (1 line). `resolve_effective_state` distinguishes dim from `hidden`. Strike stays. |
| **G1** | differ F4 — mixed `remove=+insert=` in one spec | **Refuted** | — | `\apply{a}{remove=0, insert={at=0,value=9}}` → F1 `tr=[["a","add",null,"idle","element_add"]]` — `is_structural` stays True (`_is_pure_removal` returns False on mixed). |
| **G2** | differ F4 — pure removal still renders (fs-snap salvage) | **Refuted (verified)** | — | Pure `remove=0` → `tr=null, fs=0`; SVG shifts `[1,2,3,4,5]→[2,3,4,5]`. `show()`→`snapToFrame` full innerHTML swap (`scriba.js:445,451,117`) delivers it. Deque `pop_front+pop_back` → F0 `[1,2,3,4]`→F1 `[2,3]`, stable viewBox. |
| **H1** | static `\invariant` — substory frames | **Refuted** | — | Static filmstrip & interactive **both** render invariant per **main** frame only (substory frames excluded in both) — consistent; the F1 fix makes static match interactive. |
| **H2** | live `\invariant` — undefined binding in one frame | **Refuted (pre-existing)** | — | `\invariant{val=${maybe}}` undefined-frame → literal `val = ${maybe}` (F7 policy, same as `\narrate`), defined-frame → `val = 5`. No crash. |

**Counts: 0 Confirmed bugs · 1 LOW/informational (D3) · 21 Refuted.**

---

## Evidence detail (load-bearing)

### G2 — differ F4 pure-removal is safe (the scariest-looking, fully cleared)
Round-1 F4 suppressed the bogus bare-shape `element_add` for pure removals
(`differ.py:19-52` `_is_pure_removal`; `:108-112` `is_structural = bool(ap) and not
_is_pure_removal(ap)`). Rendered manifest for `\apply{a}{remove=0}` (with a leading step so
it's a real F0→F1 transition): **`tr=null, fs=0`** — yet F0 SVG `[1,2,3,4,5]` and F1 SVG
`[2,3,4,5,∅]` differ. This is safe because:
- `fs` (`_html_stitcher.py:671`) is only read as `frames[i].fs` passed to
  `animateTransition` (`scriba.js:445-446`), which is only called when `frames[i].tr` is
  truthy. With `tr=null`, `show()` (`scriba.js:439-453`) skips both branches and calls
  `snapToFrame(i)` → `stage.innerHTML = frames[i].svg` (`:117`) = a full server-truth swap.
- The manifest logic is self-consistent: `tr` is non-null **only** in the `else` branch
  (`_html_stitcher.py:656-665`) where `_needs_sync = svg_changed`. So `tr` non-null ⟹
  `fs = svg_changed`; the runtime never relies on stale DOM.

Mixed `remove+insert`: `_is_pure_removal` sees `{remove, insert}`, `insert ∉
_REMOVAL_APPLY_KEYS` → returns False → `element_add` kept (`tr` non-null, `fs=1`). Correct.

### A6 — the corpus differential (decisive false-positive test)
`diff_corpus.sh`: render every `tests/doc_coverage/corpus/*.tex` (422 files) through both
`d628b9b` and a `d628b9b^` git worktree, recording `ok | warn:CODES | err:CODE` per doc.
`diff(sort par, sort cur)` = **empty**. No doc changed outcome. The guards fire only on
typos, which no shipping doc contains.

### C3 — reannotate ephemeral revert (rendered per-frame annotation colour)
```
re_A basic:            F0 info · F1 error · F2 info                (revert)
re_B twice-in-step:    F0 info · F1 error · F2 info                (earliest prior kept)
re_C ephem→persistent: F0 info · F1 error · F2 good  · F3 good     (persistent sticks)
```
Mechanism: `scene.py:1074-1092` sets `revert_color = ann.revert_color or ann.color` on
ephemeral, `None` on persistent; `apply_frame` (`scene.py:381-393`) removes ephemeral
annotations first, then `replace(a, color=a.revert_color)` on survivors.

### F1/F2 — strike hidden-skip is per-frame and state-aware
`base.py:1092-1108` `_target_state_is_hidden` strips the `{name}.` prefix and calls
`resolve_effective_state(suffix)`; `base.py:1231-1237` skips the strike `<g>` only when the
target's *current* effective state is `hidden`. So hidden→visible across frames re-emits the
strike (F1), and a `\focus` dim (a defocus *class*, not a state) leaves the strike lit (F2).

---

## Raw data

- Probes + harness: `scratchpad/h2/` (`gen.py`, `inspect.py`, `batch_corpus.py`,
  `diff_corpus.sh`); ~35 `.tex` probes. Renders were to `_h2out/` (removed) and a
  `wt_parent` git worktree at `d628b9b^` (removed, `git worktree prune`d).
- Corpus differential outputs: `scratchpad/h2/cur2.txt`, `par2.txt` (422 lines each,
  identical after sort), `diff_result.txt` (empty diff).
- Key code cites: `parser/_grammar_commands.py:62-107,141-179,229,345,408,508,543,576,672,
  740,787-801,866-873`; `_frame_renderer.py:414-460,719-773,1053-1130`; `differ.py:19-52,
  108-112`; `scene.py:381-393,1035,1074-1092`; `primitives/base.py:1092-1120,1231-1250`;
  `_html_stitcher.py:649-671`; `static/scriba.js:113-124,439-453`; `errors.py:256`.

## Conclusion + Confidence

The round-1 sweep is **well-built and does not regress legit documents**. Across ~35 targeted
adversarial probes and a full 422-doc parent-vs-child corpus differential, I found **no
false-positive** in any new guard and **no broken salvage path** in the geometry/manifest
fixes. The differ-F4 `fs=0` behaviour that looks like a runtime-honesty break is provably
delivered by the runtime's `snapToFrame` full-swap fallback. The single residual is a LOW,
visually-inert `\n`-in-note passthrough that predates the fix.

**Confidence: High.** Every Refuted row rests on a direct render (exit code + parsed SVG /
manifest / viewBox / annotation-class), and the false-positive class is closed by the
byte-level corpus differential rather than by code reading alone.

### RETURN — counts
- **Confirmed bugs: 0** · **LOW/informational: 1** (D3 `\n`-in-note passthrough) · **Refuted: 21**

### Top 3 one-liners
1. **Corpus differential is clean:** 422 shipping docs render to identical outcomes at
   `d628b9b^` vs `d628b9b` — the new command-param/apply/zoom/side/note guards false-positive
   on **zero** legit documents.
2. **differ-F4 pure-removal is safe:** `tr=null, fs=0` still renders the shifted array/deque
   because `show()`→`snapToFrame` does a full `innerHTML` swap; mixed `remove+insert` correctly
   keeps `element_add`.
3. **strike hidden-skip and reannotate-ephemeral-revert are both correct across frames:**
   strike skips only a `state=hidden` target (reappears when visible, stays over `\focus` dim),
   and the ephemeral revert keeps the earliest prior colour / yields to a later persistent recolor.
