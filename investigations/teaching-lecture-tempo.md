# Lecture Tempo & Code-Sync — can scriba pace a CP lecture in time?

## Hand-off Brief

The #1 YouTube CP move — the current line of code lighting up **while** the array/graph updates in the same beat — is **Confirmed working**, not a gap: CodePanel exposes per-line state (`code.line[k]`), and the runtime co-commits a line `recolor` and a data-structure `value_change`/`recolor` into a **single frame transition** that animates simultaneously (rendered proof below). The prime suspect is acquitted. The real tempo gaps are elsewhere: `\invariant` is **static and non-interpolating** (a live "sum = k" is impossible via that surface), and the **sliding binding-caret soft-drops on CodePanel** so the active line can only cross-fade, never glide like an IDE debugger gutter.

## Coverage table

| Tempo gesture | Verdict | scriba surface (path:line) or the gap |
|---|---|---|
| **Code line synced to structure update** (PRIME) | **Covered (Confirmed)** | Per-line state group `data-target="code.line[k]"` emitted at `codepanel.py:302-321`; state driven by `\recolor`/`\highlight`/`\cursor` (no `active`/`line` ctor param — `ACCEPTED_PARAMS` = source/lines/label, `codepanel.py:83-87`). Runtime `animateTransition` applies **every** record in a frame's `tr` manifest in one pass (`scriba.js:380-433`); `recolor` swaps `scriba-state-*` (`scriba.js:152-159`), `value_change` bumps text+bounce (`scriba.js:160-172`) — both are phase-2, i.e. simultaneous. Differ emits per-target `recolor`/`value_change` generically (`differ.py:93-114,155-198`). |
| Advance several views in one command | Covered, **Awkward** | `\cursor{a.cell, code.line}{k}` multi-target hop = exact sugar for two `\recolor` (§5.11, ref 570-583). Gotcha: one index is applied to every family, but Array is 0-based and CodePanel 1-based, so the shared index can silently no-op the code line (observed in probe frame[2]: only `a.cell` records, no `code.line`). Robust idiom = explicit dual `\recolor`. |
| Gliding line-pointer (debugger gutter that slides down) | **Missing (Confirmed)** | `\cursor` **pin** (`id=`, the sliding caret) lists support Array/DPTable-1D/Stack/Queue/NumberLine only — CodePanel absent (§5.11, ref 608). Probe `\cursor{code}{id=p,at=1}`→`at=2` rendered with **no error** but produced **0 caret annotations, 0 `tr` records** across both frames — it soft-drops. Active line only cross-fades (`recolor`, DUR=180 ms `scriba.js:44`), never slides. |
| Progressive reveal (build up, don't dump) | Covered | `hidden` state on all primitives since 0.23.2 (§6, ref 879): `\recolor{t}{state=hidden}` then reveal on a later `\step`; runtime `element_add`/`element_remove` fade (`scriba.js:191-216`). BFS reveal pattern shipped in ref 1606-1620. |
| "Notice that…" back-reference | Covered | `\ref{target}{text}` — dashed ring + tint tracking the cell's state each frame (§5.15; rendered `scriba-ref-mark` + `stroke-dasharray`, `scriba-ref-state-current/done/dim/…`). `\hl{step-id}{tex}` — pure-CSS `:target` jump to a labelled `\step` (§5.14). |
| Persistent invariant on screen | **Awkward / partial (Confirmed gap)** | `\invariant{text}` pins one predicate across all frames (§5.17; rendered `<p class="scriba-invariant" role="note">`). But **static v1**: prelude-only, unchanging, and `${...}` is **not** interpolated — probe `\invariant{Sum stays = ${k}}` rendered the literal `Sum stays = ${k}`. A **live** invariant value must be faked with a VariableWatch row. |
| Per-step commentary synced to visual | Covered | `\narrate` per frame; `${compute}` interpolates in narration text (§13.2, ref 1900). Narration is swapped **after** the WAAPI settles, not at transition start (`scriba.js:406-411`, "A03" comment) → the spoken beat lands on the stable visual. Visible step-title via `\step[title="…"]`, supersedes the aria-label (§5.3, ref 420-423; rendered `scriba-step-title`). |
| Pause / emphasis on arrival ("…and THERE it is") | Covered | Delta-emphasis pulse on the identities that just changed, fired once the stage settles (`scriba.js:360-379,413`); capped at 8 targets (`EMPH_CAP`, `scriba.js:54`), 700 ms dwell (`DUR_EMPH`). Value scale-bounce (`DUR_VALUE=100`, `scriba.js:160-172`); `cursor_move`/`position_move` glide to the new seat (`scriba.js:217-234,324-340`). A `\highlight` on the code line rides **phase-1**, 50 ms **before** the data move (`DUR_STAGGER`, `scriba.js:393-398,428-432`) — a deliberate lead-in beat vs. `\recolor`'s simultaneity. |
| Scrub / replay backward (rewind) | Covered | Prev / ArrowLeft apply `_invertManifest` (`scriba.js:341-349,434-455`); `recolor`/`value_change`/`position_move`/`cursor_move` are self-inverse under a from/to swap, so the active line rewinds **line-by-line** and the array un-mutates. Reduced-motion path snaps instead (`scriba.js:436-448`). |
| Sub-explanation aside then return (digression) | Covered, **caveat** | `\substory` = nested frame run with its own Prev/Next counter (§5.13; `scene.py:387` `apply_substory`; `scriba.js:62-75` `initSub`). Caveat: structural mutations (`\recolor`/`\apply`) inside the aside **persist** into the parent after return — only `highlights`/`focus` are saved/restored (`scene.py:408-409,441-443`). The picture does **not** auto-reset after the digression. |

## Confirmed gaps (what a lecturer cannot reproduce)

### G1 — No live/dynamic invariant *(Confirmed)*
`\invariant` is prelude-only, static, and does **not** interpolate `${...}`. Rendered proof: `\invariant{Sum stays = ${k}}` with `\compute{k=5}`…`\compute{k=9}` emits the literal string `Sum stays = ${k}` in every frame. A lecturer's running invariant ("`sum` stays = 7 … now 12") is impossible on this surface. Interpolation scope explicitly excludes it (§13.2 lists `\foreach`/`\apply`/selector/`\narrate` only). **Workaround:** a VariableWatch row updated per `\step` — but that reads as a variable, not a pinned predicate.

### G2 — Active code line cannot glide; only cross-fades *(Confirmed)*
The sliding binding-caret (`\cursor{…}{id=…}`) soft-drops on CodePanel (probe: 0 annotations / 0 `tr` on both frames, no E-code). The active line therefore moves by `recolor` cross-fade (180 ms), never by a marker sliding down the gutter. The **sync** a YouTuber needs is fully covered; the specific **motion** of a gliding line-pointer is not. Minor for teaching, but it is a real absence.

### Prime target — RENDERED PROOF (acquittal, not a gap)
Probe: one `\step` recolors the code line forward **and** mutates the array. Extracted frame transition manifest (`tr`) for that step:

```
frame[1]  fs=1  5 records — ALL in one transition:
  recolor       code.line[1]   'current' -> 'done'     ← active line leaves
  recolor       code.line[2]   'idle'    -> 'current'  ← active line ARRIVES (moved)
  recolor       a.cell[0]      'idle'    -> 'current'  ← structure highlight
  value_change  a.cell[0]       null     -> '3'        ← structure MUTATES
  value_change  w.var[best]    '0'       -> '3'        ← variable updates
```

All five are bound to the **same** frame and animate together (`animateTransition`, `scriba.js:394-432`). The active/highlighted line **does** change across steps and **is** co-committed with the data-structure `\apply` in the same `\step`. Probe: `scratchpad/probe_codesync.tex` (14 static print frames also emitted → the highlight survives no-JS/reduced-motion/print).

## Conclusion + Confidence

scriba reproduces CP-lecture **tempo** well: the signature code-line↔structure sync is a first-class, co-committed, reversible transition with settle-synced narration, arrival emphasis, progressive reveal, back-reference rings, and nested digressions. **Confidence: High** on the prime target (rendered manifest proof, exact runtime path) and on G1/G2 (rendered refutation probes, no-error soft-drop confirmed). The two gaps are peripheral to the core move: a running invariant value (G1, VariableWatch workaround) and a gliding line marker (G2, cross-fade substitute). Secondary friction: multi-target `\cursor` index-space skew (0- vs 1-based) can silently no-op the code line — prefer explicit dual `\recolor`.
