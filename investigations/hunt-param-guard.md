# Hunt: E1105 `\apply`-param guard completeness + the param-surface silent-swallow class

## Hand-off Brief

The new E1105 guard (commit `33e7d7f`) is **correct on its own axis**: all 21 primitives' `APPLY_KEYS` exactly match the keys their `apply_command` reads, and the guard does **not** false-positive on indirect paths (`\foreach`-interpolated applies, interpolated structural spec dicts like `reparent={node=${n}}`, `\substory`, the structural-prescan replay) — every valid indirect apply I rendered exits clean. **However**, the guard's own generic allow-list `{state, value, label}` (`_frame_renderer.py:696`) over-permits `state`: `\apply{X}{state=done}` lands in `apply_params`, is consumed by nobody, and is silently swallowed — the guard whitelists `state` so no E1105 fires (rendered: the cell stays `scriba-state-idle`). Separately and more broadly, the **dual** of this hazard is wide open: the entire decoration/annotation command family (`\annotate`, `\note`, `\trace`, `\link`, `\combine`, `\group`, `\reannotate`, `\focus`, `\cursor`) performs **zero unknown-key validation** on its `{...}` param dict — a typo'd key (`colour=`, `strke=`, `scpe=`, `prev_stat=`, `labl=`) is silently dropped and the author's intent is lost with zero signal, exactly the class the project already hardened for env options (`grid` removal, 0.21.2), `\shape` ctors (E1114), and `\apply` (E1105).

## Findings table

| id | surface | verdict | severity | repro (typo → observed) |
|----|---------|---------|----------|------|
| A3 | guard generic set includes `state` | **Confirmed** | Medium (masked swallow / hole in the new fix) | `\apply{a.cell[0]}{state=done}` → cell stays `idle`, no E1105 |
| B-annotate | `\annotate{}{}` param dict | **Confirmed** | Medium | `colour=warn` → `-info`; `strke=true` → no strike |
| B-note | `\note{}{}` param dict | **Confirmed** | Medium | `colour=warn` → `-info` |
| B-trace | `\trace{}{}` param dict | **Confirmed** | Medium | `colour=warn` → `-info` |
| B-link | `\link{}{}` param dict | **Confirmed** | Medium | `colour=warn` → `-info` |
| B-combine | `\combine{}{}` param dict | **Confirmed** | Medium | unknown key → exit 0, dropped |
| B-group | `\group{}{}` param dict | **Confirmed** | Medium | `colour=warn` → hull `-info` |
| B-reannotate | `\reannotate{}{}` param dict | **Confirmed** | Medium | `labl="changed"` → label stays `orig` |
| B-focus | `\focus{}{}` param dict | **Confirmed** | Medium | `scpe=board` → board scope lost (other shape not dimmed) |
| B-cursor | `\cursor{}{}` param dict | **Confirmed** | Medium | `prev_stat=error` → prev cell `dim` (default), not `error` |
| B-recolor | `\recolor{}{}` param dict | **Confirmed (partial)** | Low | sole-key typo fails loud (E1109); extra unknown key alongside valid `state=` is swallowed |
| A1 | `\foreach`/interp/`reparent`/substory indirect applies | **Refuted** (guard robust) | — | all valid indirect applies render clean, no false E1105 |
| A2 | primitives w/o `apply_command` (Grid/Matrix/… base no-op) | **Refuted** | — | `APPLY_KEYS=frozenset()` correct; bogus key → E1105 is the *correct* raise (key was genuinely dead) |
| B4-ctor | `\shape{}{}{}` ctor params (all 20) | **Refuted** (validated) | — | E1114 fires; but see latent note below |
| B7-env | `\begin{animation}[…]`, `\substory[…]`, `\step[…]` | **Refuted** (validated) | — | E1004/E1005 fires on unknown option key |

**Counts: 10 Confirmed swallow points (2 distinct root causes: A3 hole + B-class across 9 commands) / 4 Refuted.**

---

## Evidence

All renders from repo root: `.venv/bin/python render.py <p>.tex -o ./_p.html`. Exit 0 + no E-code = silent swallow. Differential renders compare a correct-key CONTROL against a typo'd PROBE; identical exit 0 with divergent HTML = intent lost silently. Repro `.tex` files in scratchpad (`c_*.tex`, `a_*.tex`).

### A3 — the guard's generic set silently swallows `\apply{X}{state=…}` (hole in the new fix)

**Root cause.** `scene.py:955` `_apply_apply` builds `apply_params` from `extra = {k: … for k,v in cmd.params.items() if k not in ("value","label")}` (`scene.py:969`) — it strips **only** `value` and `label` into their own `ShapeTargetState` fields. `state` is **not** stripped, so `\apply{cell}{state=…}` lands in `apply_params`. No `apply_command` reads `params["state"]` (grepped all primitives — zero hits), and the frame renderer's value-layer reads the *separate* `.state` field (`_frame_renderer.py:1355 target_data.get("state","idle")`), never `apply_params[i]["state"]`. So `state` inside an apply spec is consumed by nobody. The guard's generic allow-list `_GENERIC_APPLY_KEYS = frozenset({"state","value","label"})` (`_frame_renderer.py:696`) nonetheless whitelists it, so E1105 never fires — the guard's own comment claims `state` "flow[s] to the primitive through set_state … the frame renderer's value-layer," which is **false** for the `\apply` path.

**Rendered proof (differential):**
```
CONTROL  \recolor{a.cell[0]}{state=done}  -> data-target="a.cell[0]" class="scriba-state-done"
PROBE    \apply{a.cell[0]}{state=done}     -> data-target="a.cell[0]" class="scriba-state-idle"   (exit 0, no E1105)
```
A plausible author mental model — `\apply{a.cell[0]}{value=5, state=done}` (set value **and** state in one apply) — silently loses the state. Because `value`/`label` are stripped upstream they can never reach `apply_params`, so the generic set's `value`/`label` entries are dead-but-harmless; only `state` is reachable, and it is dead-**and**-harmful. Either `state` should work on `\apply`, or it should raise E1105 ("use `\recolor`"); the current silent middle is the exact trap the commit set out to close.

### B-class — decoration/annotation commands perform no unknown-key validation

**Root cause.** Every handler in `parser/_grammar_commands.py` reads its keys with `params.get("known_key", default)` and enum-validates only the *values* of known keys; **none** validates that all keys in `params` are recognized. Unknown keys are silently dropped. (Contrast `\step`/env/substory bracket options, which gate keys against allow-lists → E1004, and `\shape` ctors → E1114, and `\apply` → E1105.)

**Rendered proofs** (typo → observed applied class/behavior; CONTROL with correct key shown where differential):

- **`\annotate`** (`_parse_annotate`, `_grammar_commands.py:629`)
  ```
  CONTROL color=warn  -> <g class="scriba-annotation scriba-annotation-warn" …>
  PROBE   colour=warn -> <g class="scriba-annotation scriba-annotation-info" …>   (default; typo dropped)
  ```
  Behavioral (boolean flag) — `strike`:
  ```
  baseline (no key)   viewBox="0 0 208 90"
  PROBE strke=true    viewBox="0 0 208 90"   (identical to baseline → strike NOT applied)
  CONTROL strike=true viewBox="0 0 212 92"   (strike geometry added)
  ```
- **`\note`** (`:467`): `colour=warn` → `<g class="scriba-annotation scriba-note scriba-annotation-info">` (default).
- **`\trace`** (`:309`): `colour=warn` → element uses `scriba-annotation-info`; control `color=warn` uses `-warn` (warn-class element count 10→12 control, stays 10 in typo).
- **`\link`** (`:391`): `colour=warn` → `scriba-link scriba-annotation-info` (default).
- **`\combine`** (`:424`): unknown key → exit 0, dropped.
- **`\group`** (`:559`): `colour=warn` → hull `scriba-annotation-info scriba-group` (default).
- **`\reannotate`** (`:257`): `labl="changed"` → annotation `aria-label="orig"` (unchanged); `color=warn` on the same command *does* apply (`-warn`), proving only the unknown key was dropped.
- **`\focus`** (`:127`, differential, 2 shapes):
  ```
  CONTROL scope=board -> shape b defocused (scriba-defocused count = 4)
  PROBE   scpe=board  -> shape b NOT defocused (count = 0; scope silently defaulted to "shape")
  ```
- **`\cursor`** (`_parse_cursor` legacy path, `:758-783`, differential, 2 steps):
  ```
  CONTROL prev_state=error -> prev cell a.cell[0] class="scriba-state-error"
  PROBE   prev_stat=error  -> prev cell a.cell[0] class="scriba-state-dim"   (default prev_state)
  ```
- **`\recolor`** (`:167`, partial): a **sole** typo'd key fails loud because state/color are both absent → E1109 "requires at least one of 'state' or 'color'" (misleading message, but not silent). An unknown key *alongside* a valid `state=` is swallowed.

### Refuted items (guard is robust / surface already validated)

- **A1 indirect-path false positives — Refuted.** Rendered clean (exit 0, no false E1105):
  - `\foreach{i}{0..2} \apply{a}{insert={at=${i}, value=9}} \endforeach` (structural key via foreach + prescan).
  - `\foreach{i}{0..2} \apply{a.cell[${i}]}{value=${i}} \endforeach` (generic value + interpolated selector).
  - `\apply{t}{reparent={node=${n}, parent=${p}}}` (interpolated **structural spec dict** — the guard validates the top-level key `reparent`, not the interpolated nested values, so interpolation timing is a non-issue: `scene.py` resolves *values* via `_resolve_interp` while *keys* stay literal).
- **APPLY_KEYS ↔ apply_command parity — verified for all 21 primitives.** Read every `apply_command` body: array `{insert,remove,reorder}`, stack `{push,pop}`, queue/deque `{enqueue,dequeue,push_front,push_back,pop_front,pop_back}`, tree `{add_node,remove_node,reparent,add_link,remove_link}`, graph `{add_edge,remove_edge,set_weight}`, forest `{union}`, linkedlist `{insert,remove}`, equation `{lines,tex}`, tracetable `{row}`, plane2d (23 add/remove/move/rotate verbs — all dispatched, incl. `rotate_line`), bar/hashmap/hypercube (`frozenset()`, read only generic `value`), variablewatch/metricplot (property returning live var/series names). No structural key a primitive actually consumes is missing from its `APPLY_KEYS` → no valid-doc false positive from the per-primitive sets.
- **A2 base-no-op primitives — Refuted.** Grid/Matrix/DPTable/Numberline/CodePanel inherit `APPLY_KEYS=frozenset()` and the base no-op `apply_command`; a structural key on them now raises E1105, which is *correct* (the key was genuinely dead). No primitive consumes a non-generic key outside `apply_command`.
- **B4 `\shape` ctor / B7 bracket options — Refuted.** All 20 primitive classes declare non-empty `ACCEPTED_PARAMS` → E1114 fires (`\shape{h}{Bar}{bogusparam=1}` → E1114). Env/substory/step options gate keys against `VALID_OPTION_KEYS`/`VALID_SUBSTORY_OPTION_KEYS`/`{label,title}` → E1004/E1005.
  - *Latent note (not currently triggered):* `base.py:315` runs ctor validation only `if self.ACCEPTED_PARAMS:` — a future primitive that leaves `ACCEPTED_PARAMS` empty would silently skip ctor validation. All shipping primitives declare it, so no live bug today.

---

## Conclusion + Confidence

The E1105 guard is well-built where it acts, and it does not break valid documents through indirect paths — the false-positive risk the hunt targeted is **Refuted** with rendered proof. The two real defects are: **(A3)** the guard's generic allow-list re-opens a silent swallow for `\apply{X}{state=…}` — a hole inside the very fix meant to close silent apply swallows; and **(B-class)** the fix's dual is untouched — nine decoration/annotation commands silently drop unknown keys, so a single mistyped key name (`colour`, `strke`, `scpe`, `prev_stat`, `labl`) discards the author's intent with zero signal. This is the same failure class the project has been methodically hardening (env `grid`, `\shape` E1114, `\apply` E1105); the inconsistency is itself the trap — `\shape{a}{Array}{colour=x}` is loud, `\annotate{a.cell[0]}{colour=x}` is silent. Suggested fix shape: a shared `_validate_command_params(cmd_name, params, allowed)` mirroring `_validate_apply_spec`, called from each `_parse_*` handler; and drop `state` from `_GENERIC_APPLY_KEYS` (or route `\apply` `state=` to the value-layer's state channel in `scene.py`).

**Confidence: High.** Every Confirmed finding has an exit-0 render plus a differential HTML class/geometry/count diff isolating the dropped key. Code citations: `_frame_renderer.py:696,699-736,1355`; `scene.py:955,966-970`; `parser/_grammar_commands.py:167,257,309,391,424,467,559,629,696,758-783`; `base.py:303,315`. Root cause is uniform (`params.get` with no key-set check), so the B-class list is exhaustive for the second-brace command surfaces.
