# anim-narrate-focus — `\ref` / `\focus` / `\step[title]` / `\invariant` design dossier

Repo: `scriba` @ `main` (0.22.2). Scope: **research + design only, no source edits.** Grades:
**Confirmed** = read in code or reproduced by probe; **Deduced** = inferred from confirmed code;
**Hypothesized** = design proposal, not yet built.

---

## Hand-off Brief (3 sentences)

Narration is a **raw string** carried untouched from parser to renderer, where `_render_narration`
(`renderer.py:152`) expands it in four passes — `\hl` macros → KaTeX `$…$` → span-restore → `\textbf`
text-commands — so the correct seam for `\ref{sel}{text}` is a **new renderer-level macro pass co-located
with `process_hl_macros`** (exact precedent: `hl_macro.py`, and the `${}` interpolation regex), resolving
the target's colour from the frame's own `shape_states` dict that is already in scope two lines above the
call site. `\focus{sel}` is a straight clone of the `\highlight` command spine (lexer keyword → `FocusCommand`
AST → `_apply_focus` ephemeral set → snapshot → `FrameData` → baked SVG class), and its "dim everything else"
emit needs **no differ work** because the stitcher already sets the full-resync flag `fs=1` whenever a frame's
SVG string changes (`_html_stitcher.py:586`). The one load-bearing surprise: **`scriba-highlighted` is a latent
no-op** — no CSS rule exists for it anywhere and no primitive bakes it (only the runtime differ toggles it
during a transition, over nothing), so `\highlight`'s *only* visible effect today is the idle→`scriba-state-highlight`
override, which means `\ref`/`② emphasis` cannot lean on the highlight set for a visible ring on an already-coloured
cell and must ship its own baked emphasis class + CSS.

---

## 1. Narration pipeline map (Confirmed unless noted)

| Stage | Location | What happens |
|---|---|---|
| Lexer keyword | `parser/lexer.py:70` (`_KNOWN_COMMANDS`) | `narrate` is a known command |
| Parse | `parser/_grammar_commands.py:63-65` `_parse_narrate` | `NarrateCommand(line,col, self._read_raw_brace_arg(tok))` — **RAW** brace body, *not* tokenised |
| Dispatch | `parser/grammar.py:257,276` | `narrate` → `_parse_narrate`; step-scoped (E-guard `\narrate must be inside a \step`) |
| AST | `parser/ast.py:177` `NarrateCommand`; `ast.py:370` `FrameIR.narrate_body: str\|None` | body threaded onto the frame |
| Grammar collect | `parser/grammar.py:185` `frame_narrate = result.body` → `grammar.py:203` `narrate_body=frame_narrate` | one narrate per step (dup → E-guard `grammar.py:267-269`) |
| Scene interpolate | `scene.py:249` in `apply_frame` → `_interpolate_narration` (`scene.py:608-640`) | `${name}` / `${name[idx]}` ← `\compute` bindings, regex `\$\{([^}]+)\}`; unknown name left intact |
| Snapshot | `scene.py:160` `FrameSnapshot.narration`; set at `scene.py:287` | frozen snapshot carries the interpolated string |
| **Render** | `renderer.py:337` `narration_html = _render_narration(snap.narration, scene_id, ctx, valid_hl_ids)`; def `renderer.py:152-204` | see 4-pass detail below |
| FrameData | `renderer.py:342` → `emitter.py:112` `FrameData.narration_html` (frozen, slots) | already-rendered HTML string |
| Sanitiser gate | `_html_stitcher.py:84` `_safe_narration_html` | **trust gate, not a sanitiser** — asserts `str`, passes scriba-internal HTML through verbatim; `<span class>` is allowed (`sanitize/whitelist.py:85`) |
| Interactive emit | `_html_stitcher.py:628` `<p class="scriba-narration" dir="auto" id="{scene}-narration" aria-live="polite">` | frame-0 narration inlined; per-frame in JS island |
| Print emit | `_html_stitcher.py:559-561` | narration `<p>` per print-frame → **`\ref` works no-JS/print for free** |
| JS swap | `static/scriba.js:103` (`snapToFrame`) and `scriba.js:307` (`animateTransition._finish`) | `narr.innerHTML = frames[i].narration`; **A03**: line 304-307 sets narration *after* WAAPI settles so `aria-live` fires on stable visual |

### `_render_narration` four passes (`renderer.py:152-204`) — Confirmed
1. `process_hl_macros(text, …, span_wrapper=_stash_span, valid_step_ids=valid_hl_ids)` (`hl_macro.py:53`) — `\hl{step}{tex}` → `<span class="scriba-hl" data-hl-step="…">RENDERED</span>`, each span **stashed behind a `\x00HL{n}\x00` placeholder** so the next pass's escape can't clobber it.
2. `ctx.render_inline_tex(processed)` — extracts every bare `$…$`, KaTeX-renders it, HTML-escapes the free text between. (Plain-text escape is *deferred to here* so `<` inside `$\min_{j<1}$` survives — see the pass-1 `escape_plain_text=not has_tex` contract.)
3. restore stashed `\hl` spans.
4. `apply_text_commands(processed)` (`core/text_utils.py:67`) — `\textbf`/`\texttt`/`\emph`/… → inline HTML, run **after** TeX so tags aren't escaped.

**Probe (Confirmed, `scratchpad/an_probe.tex` → rendered):** a `\narrate{… \hl{scan}{cell 2} … $x^2$ … \textbf{bold} …}` produced
`…<span class="scriba-hl" data-hl-step="scan">cell 2</span> … <span class="scriba-tex-math-inline"><span class="katex">…</span> … <strong>bold</strong>…` inside `<p class="scriba-narration" … aria-live="polite">`. Cell classes baked as `data-target="a.cell[2]" class="scriba-state-current"`, `a.cell[0]` (highlighted, idle) → `class="scriba-state-highlight"`.

### Safe seam for inline `\ref` tokens (Confirmed + Deduced)
- Narrate body is a raw string end-to-end (`_read_raw_brace_arg`), so there is **no grammar token stream** to hook — grammar-level parsing (option i) would require tokenising the body, a large new surface. **Rejected.**
- Renderer-level regex (option ii) is the **established pattern**: `\hl` (regex + balanced-brace, `hl_macro.py:18,31`) and `${}` interpolation (regex, `scene.py:640`) both do exactly this. **Recommended.**
- `\ref{sel}{text}` where `text` contains `$…$`: process it in the **pass-1 stage alongside `\hl`**, render the `text` arg through `render_inline_tex` and wrap+stash the `<span>` — identical to how `\hl` renders its tex body and stashes. This guarantees the ref text's math is KaTeX'd and the ref `<span>` survives pass-2 escaping. `\textbf{…}` inside the ref text is handled by pass-4 on the restored string (same as everywhere else).

---

## 2. ④ `\ref{sel}{text}` — design (Hypothesized unless cited)

**One line:** narration macro that tints `text` with the target's *current-frame* state colour and rings the target on the stage. Opt-in; absent ⇒ zero output change.

### 2a. Parse site — **renderer-level, new module `extensions/ref_macro.py`** (mirror `hl_macro.py`)
- `process_ref_macros(narration, *, state_of: Callable[[str], str|None], render_inline_tex, span_wrapper, warn) -> tuple[str, set[str]]`.
- Regex `\\ref\{` + `_extract_braced` twice (reuse the exact helper shape from `hl_macro.py:31-50`) → `(sel, text)`.
- Returns the rewritten string **and the set of ref targets** (for emphasis merge).
- Wire into `_render_narration` (`renderer.py:190-201`) as a sibling call to `process_hl_macros`, sharing the same `_stash_span` list so both macro spans survive pass-2. `_render_narration` gains a `state_of`/`shape_states` param and returns `(html, ref_targets)`.

### 2b. Colour resolve (Confirmed data path)
- `_snapshot_to_frame_data` already builds the per-target dict `shape_states[shape][target] = {"state": ts.state, …}` at **`renderer.py:284-307`**, i.e. **before** the narration call at `renderer.py:337`. Pass a closure `state_of("a.cell[2]") → shape_states["a"]["a.cell[2]"]["state"]`.
- Map state → class using **VALID_ANNOTATION_STATE_COLORS** (`constants.py:44` = `{current, done, dim, good, error, path}`). Emit `<span class="scriba-ref scriba-ref-state-{state}">…`.
- Inks: **`--scriba-annotation-state-{state}`** (R-36 family) — `scriba-scene-primitives.css:177-182` (light) + `:742-747` (dark). **These are the correct tokens** because the narration word sits on the **page background**, not a coloured pill, and R-36 explicitly documents them WCAG-AA on white/dark (`css:170-176`). Do **not** use `--scriba-state-*-fill` (those are pill fills, unreadable as text ink on white).
- **idle / highlight / hidden / unknown-target → no ink**: emit bare `<span class="scriba-ref">` (inherits body colour) + emphasis only. Honest: an element with no signal state is not falsely coloured. This matches VALID_ANNOTATION_STATE_COLORS excluding idle/highlight/hidden (documented rationale at `constants.py:40-43`).

### 2c. Emphasize the element — **the sharp edge** (Confirmed finding)
- **`scriba-highlighted` is dead paint:** `grep` across all CSS = no rule; across all primitives = never baked; only `differ.py:120,204` emits `highlight_on` and `scriba.js:145-149` toggles the class at runtime — over an element with no CSS for it, then wiped on full-sync. So `\highlight`'s only real visual is `resolve_effective_state` (`primitives/base.py:943-952`) turning **idle**+highlighted into `scriba-state-highlight`. On a `current`/`done`/… cell, `\highlight` is invisible.
- Therefore `\ref` emphasis **cannot** be "just add to the highlight set" and get a ring on a coloured cell. Two paths:
  - **v1 (recommended, de-risked): tint only, no ring.** The colour-link (word ink == element state) already defeats "naming without pointing" for the common case (the element is coloured, the word now matches it). Ship this first: zero SVG/primitive changes, zero differ changes.
  - **v1.1 fast-follow: baked emphasis.** Central post-process in `_frame_renderer` (single site): after the frame SVG string is assembled (`_frame_renderer.py:751`), for each ref/emphasis target (expanded via `_expand_selectors`, `_frame_renderer.py:346`) inject an additive class `scriba-emphasis` into its `<g data-target="X" class="…">`. Add one CSS rule (ring via `--scriba-widget-focus-ring` `css:103`, or `scriba-anim-pulse` — the `pulse` keyframe preset already exists at `extensions/keyframes.py:19-23`). Primitive-agnostic, opt-in, prints. This *also* fixes the latent `\highlight`-on-coloured-cell no-op if unified.
- **Do not** reuse the highlight set for `\ref` unless you also ship the emphasis CSS+bake — otherwise it silently does nothing on exactly the cells `\ref` usually points at.

### 2d. Failure modes
- Bad/undeclared selector → **soft**: keep the plain `text` (strip the `\ref` wrapper, no ink, no ring), emit a `RendererWarning`. Do **not** hard-error (narration typos must not blank a render). Proposed **E1322** (soft, non-fatal, adjacent to the `\hl` E1320-E1329 block) or reuse the E1115 "selector no-match" soft semantics (`errors.py:188`).
- Range/block selector → ambiguous colour: resolve against the exact key; if it isn't a single stated target, fall back to base `scriba-ref` (no ink). Document `\ref` as single-element.
- No-JS / print: static tinted `<span>` in the print `<p>` (`_html_stitcher.py:559`) — **works for free** (Confirmed path).

---

## 3. ⑤ `\focus{sel}` — design (Hypothesized; spine Confirmed via `\highlight`)

**One line:** spotlight the addressed set this frame; every other addressable cell gets `scriba-defocused` (dim). Ephemeral ⇒ auto-reverts next step.

### 3a. Command spine — clone `\highlight` end-to-end
| Concern | `\highlight` reference | `\focus` add |
|---|---|---|
| Lexer keyword | `lexer.py:72` | add `"focus"` to `_KNOWN_COMMANDS` (`lexer.py:65`) |
| AST | `HighlightCommand` (`ast.py`, imported `_grammar_commands.py:16`) | `FocusCommand(line,col,target: Selector)` |
| Parse | `_parse_highlight` `_grammar_commands.py:77-85` | `_parse_focus` (identical: `parse_selector` + return) |
| Dispatch | `grammar.py:278-288` (frame-only; prelude → E1053 unless flagged) | same guard; frame-only |
| Scene field | `self.highlights: set` `scene.py:180` | `self.focus: set[str]` field |
| Ephemeral clear | `apply_frame` clears `self.highlights` `scene.py:233` | clear `self.focus` there too ⇒ **auto-reverse next step is automatic** |
| Apply | `_apply_highlight` `scene.py:823-…` (E1116 undeclared-shape guard, `self.highlights.add`) | `_apply_focus` (same E1116 guard, `self.focus.add`); dispatch in `_apply_command` `scene.py:599` |
| Snapshot | `FrameSnapshot.highlights` `scene.py:156`, set `scene.py:283` | `FrameSnapshot.focus: frozenset[str]` |
| FrameData | (highlights fold into `shape_states["…"]["highlighted"]` `renderer.py:297-307`) | `FrameData.focus: tuple[str,…]` (`emitter.py:106`); `_snapshot_to_frame_data` copies `snap.focus` |

### 3b. Emit (Confirmed mechanics)
- In `_frame_renderer`, when `frame.focus` non-empty: expand it via `_expand_selectors` (`_frame_renderer.py:346` — handles `range[a:b]`, `block[a:b][c:d]`, `all`, `top`; primitive-agnostic ⇒ **reuse, don't reinvent**). Then scan the assembled SVG for every `data-target="X"` and inject `scriba-defocused` on those **not** in the expanded focus set (same central post-process site as `\ref` emphasis, `_frame_renderer.py:751`).
- CSS (new, `scriba-scene-primitives.css`): `.scriba-defocused { opacity:.35; filter:saturate(.35); }` — compositor-friendly; dark-mode token if needed. A focused cell keeps its own `scriba-state-*`; defocus is orthogonal overlay.
- **Transitions: no differ change needed for v1.** `_needs_sync[i] = svg_changed` (`_html_stitcher.py:586`) is already set whenever the frame SVG differs; a focus-set change alters the SVG ⇒ `fs=1` ⇒ JS `_finish(true)` does `stage.innerHTML = frames[toIdx].svg` (`scriba.js:302`) so the dim lands after the WAAPI settle. Optional future polish: differ `focus_on/off` for a cross-fade (not required).

### 3c. Semantics
- Multiple `\focus` in one step → **union** (set add). ✓
- Interaction: `\focus` dims non-focus cells across **all** shapes; `\recolor`/`\highlight`/state on a focused cell is preserved; on a defocused cell the state class stays but is visually muted. Reasonable and predictable.
- Failure: bad selector → **soft** (E1115 path via `_validate_expanded_selectors` `_frame_renderer.py:426`); undeclared shape → **E1116 hard** (mirror `_apply_highlight` guard). Matches the brief's "focus sel sai → soft E1115".

---

## 4. ⑩a `\step[title="…"]` — assessment (Confirmed surface; Medium cost)

- Today `_try_parse_step_options` (`_grammar_tokens.py:345-433`) parses **only** `[label=ident]` and **returns `str | None`**. STRING values already lex (`:374` accepts `TokenKind.STRING`), so `title="Fill the base row"` parses without lexer work.
- Changes:
  1. Accept a second key `title` in the loop; keep `label` as-is; unknown keys still E1004 (`:391-399`). Enforce the 3-5-word guidance as a **soft warning**, not a hard cap.
  2. **Return type widens** `str | None` → a small `StepOptions(label: str|None, title: str|None)` (or a 2-tuple). Ripples to **2 callers**: `grammar.py:253` and `_grammar_substory.py:233`. Mechanical.
  3. Thread `title` onto `FrameIR` (`ast.py:357`) → snapshot → `FrameData.title` (`emitter.py:106`) → emit.
- Render + aria: emit a heading before narration, e.g. `<p class="scriba-step-title">{title}</p>` (or `<h3>`), included in both interactive scaffold (`_html_stitcher.py:628` region) and print frame (`:554-564`). For a11y, set the **frame region `aria-label`** to the title, or prepend title into the aria-live text so it is announced. Note: `_frame_renderer.py:575-598` already derives a `<title>`/`aria-labelledby` from **stripped narration**; an explicit `\step[title]` should **supersede** that derived title — REFERENCE must say so.
- Cost: **Medium**, fully mechanical. No new state-machine surface.

---

## 5. ⑩b `\invariant{…}` — assessment (recommend scoped v1, defer the hard part)

- Unlike `\highlight`/`\focus` (ephemeral, cleared each frame) an invariant is **persistent across frames** — that is the new, more expensive surface. Two shapes:
  - **v1 (recommended): prelude-level `\invariant{text}`**, rendered **once** as a pinned panel `<p class="scriba-invariant">` below the widget (static; no per-frame diffing, no snapshot/FrameData field, no differ, print = one static line). ~20% of the cost, ~80% of the value ("this predicate holds throughout").
  - **Deferred: per-step mutable invariant.** Needs a persistent `self.invariant: str|None` that **survives** the `apply_frame` ephemeral clear (`scene.py:233`), threaded snapshot→FrameData→emit and re-rendered per frame, plus print duplication and (if it should animate) differ awareness. Disproportionate for the payoff.
- **Recommendation: ship prelude-static v1; defer per-step** with the rationale above. If per-step is later required, model the persistence on `bindings` (survives clear) rather than on the highlight/focus ephemeral sets.

---

## 6. Test + patch plans (RED-first)

### `\ref` (④)
- **RED unit** `tests/unit/test_ref_macro.py` (model on `tests/unit/test_hl_macro.py`): `process_ref_macros(r"\ref{a.cell[2]}{pivot}", state_of=lambda t:"current")` ⇒ `<span class="scriba-ref scriba-ref-state-current">pivot</span>`; idle/unknown ⇒ bare `scriba-ref`; `$x$` in text ⇒ KaTeX via callback; `<b>` in text ⇒ escaped (mirror `test_hl_macro.py:61-66`); bad selector ⇒ plain text + warning captured.
- **RED integration** (model on `test_animation_emitter.py`): render a 2-step animation, assert frame-1 narration `<p>` contains the tinted span with the frame's state; assert emphasis target ⇒ `scriba-emphasis` on `<g data-target>` (v1.1) or absent (v1).
- **Doc-coverage corpus** `tests/doc_coverage/corpus/ref_state_link.tex` + `.expect` (`ok\nfeature: §5.14 \ref{sel}{text} state-tinted narration link`) and `neg_E1322_ref_bad_target.{tex,expect}` (`error E1322`).
- **Patch**: `extensions/ref_macro.py` (new); `_render_narration` signature+call (`renderer.py:152,190,337`); `_snapshot_to_frame_data` merge ref targets into emphasis channel (`renderer.py:337-348`); CSS `.scriba-ref`, `.scriba-ref-state-*`, `.scriba-emphasis`; `errors.py` E1322; REFERENCE §5.14.

### `\focus` (⑤)
- **RED scene unit**: `\focus{a.cell[1]}` ⇒ `snapshot.focus == {"a.cell[1]"}`; next frame w/o focus ⇒ `snapshot.focus == frozenset()` (auto-reverse); undeclared shape ⇒ E1116.
- **RED emitter unit**: rendered SVG has `scriba-defocused` on `data-target` cells outside the focus set and **not** on focused ones; union of two `\focus` lines.
- **Corpus** `focus_spotlight.{tex,expect}`; `neg_E1116_focus_undeclared.{tex,expect}`.
- **Patch**: `lexer.py:65`; `FocusCommand` in `ast.py` + `_grammar_commands.py` `_parse_focus`; `grammar.py:278`-style dispatch; `scene.py` field+clear+`_apply_focus`+dispatch; `FrameSnapshot.focus`; `FrameData.focus`; central defocus injection in `_frame_renderer.py`; CSS `.scriba-defocused`; REFERENCE §5.15.

### `\step[title]` (⑩a)
- **RED parser unit**: `_try_parse_step_options` on `\step[label=x, title="Fill"]` ⇒ `(label="x", title="Fill")`; `title` alone valid; both callers still green.
- **RED emitter unit**: `FrameData.title` ⇒ `scriba-step-title` element + frame `aria-label`; supersedes narration-derived `<title>`.
- **Patch**: `_grammar_tokens.py:345` + return type + 2 callers; `FrameIR.title`; `FrameData.title`; emit (interactive + print); REFERENCE §5.3 update.

### `\invariant` (⑩b, v1)
- **RED**: prelude `\invariant{text}` ⇒ one `scriba-invariant` panel present on the widget and every print frame; no snapshot field touched.
- **Patch**: parse in prelude; carry on `AnimationIR`; emit once; CSS `.scriba-invariant`; REFERENCE §5.16.

### Golden impact (Deduced)
- **Narration/SVG deltas are opt-in** — existing goldens' bodies change only if they use the new commands.
- **CSS churn is global**: the state/animation CSS is inlined into every output, so adding `.scriba-ref-*`, `.scriba-emphasis`, `.scriba-defocused`, `.scriba-step-title`, `.scriba-invariant` **regenerates every golden HTML** (mechanical, expected — same class of churn as prior P2 CSS-token regens). Plan a single `pytest --snapshot-update`/golden-regen commit isolated from logic.

---

## 7. R-cards + REFERENCE + E-codes (drafts)

### R-cards (ruleset.md style, `docs/spec/ruleset.md`)
- **R-39 `\ref` narration state-link** — In `\narrate`, `\ref{sel}{text}` renders `text` tinted with `sel`'s current-frame state ink (`--scriba-annotation-state-*`, R-36) when `sel`'s state ∈ {current,done,dim,good,error,path}; otherwise base `scriba-ref` (no ink). Optional baked `scriba-emphasis` ring on `sel`. Bad/undeclared `sel` ⇒ soft (plain text + warning, E1322). Opt-in; renders in print/no-JS.
- **R-40 `\focus` spotlight** — `\focus{sel}` (frame-only, ephemeral) marks `sel` as focused; every other addressable cell gets `scriba-defocused` this frame; cleared at next `\step`. Union across multiple `\focus`. Undeclared shape ⇒ E1116; non-matching part ⇒ soft E1115. No persistent-state mutation.

### REFERENCE drafts (`docs/SCRIBA-TEX-REFERENCE.md`, extend §5)
- **§5.14 `\ref{target}{text}`** — "Inside `\narrate`, colours `text` to match `target`'s current visual state and (optionally) rings the element on the stage, so naming a cell also points at it. Ink follows the R-36 annotation-state palette; idle/unstyled targets render as plain emphasised text. A typo'd target degrades to plain text with a warning (E1322)." Example mirroring the §5.3 `\hl` block.
- **§5.15 `\focus{target}`** — "Ephemeral spotlight: dims every cell except `target` for this frame; auto-clears at the next `\step`. Combine multiple `\focus` for a union. Orthogonal to `\recolor`/`\highlight`."
- **§5.3 update** — document `title="…"` next to `label=…`; note it supersedes the narration-derived frame title and sets the step's aria-label.
- **§5.16 `\invariant{text}`** (v1) — "Prelude-only; pins a predicate panel shown across all frames."

### E-codes (`scriba/animation/errors.py` catalog + `docs/spec/error-codes.md`)
- **E1322** (new, soft, `\hl`/`\ref` block E1320-E1329): "`\ref` references an unknown or undeclared target — the reference degrades to plain text (warning)." Non-fatal.
- **E1115** (reuse, soft): `\focus` selector matches no addressable part — silently dimmed-nothing + warning (existing `_validate_expanded_selectors`).
- **E1116** (reuse, hard): `\focus` references an undeclared shape (mirror `_apply_highlight`).
- **E1004** (reuse): unknown `\step` option key (title typo'd).

---

## 8. Open questions (≤5)

1. **`\ref` emphasis in v1: ship or defer?** Recommendation = tint-only v1 (zero SVG risk), baked `scriba-emphasis` as v1.1. Confirm the colour-link alone is acceptable for the first cut, or require the ring immediately (adds the central `_frame_renderer` injection + CSS).
2. **Unify or leave `scriba-highlighted`?** It is currently dead paint (no CSS, never baked). If `\ref`/② emphasis ships a real `scriba-emphasis`, do we also retrofit `\highlight` on coloured cells to use it (fixes a latent no-op) or leave `\highlight` idle-only as historically shipped?
3. **`\ref` on a range/`all` selector** — forbid (single-element only, clean colour) or resolve to first stated cell? Recommendation = single-element, soft-warn on range.
4. **`\step[title]` placement** — dedicated `<h3 class="scriba-step-title">` heading above narration, or fold into the existing narration-derived `<title>`/`aria`? Recommendation = explicit heading + supersede derived title.
5. **`\invariant` scope** — accept prelude-static v1 and defer per-step-mutable, per §5? Confirm no near-term need for a changing invariant.

---

### Appendix — probe artifacts
`scratchpad/an_probe.tex` (+ `an_probe.html`): 2-step Array animation exercising `\hl`, `$x^2$`, `\textbf`, `\highlight`, `\recolor{…}{state=current/done}`. Confirmed: narration span/KaTeX/`<strong>` composition, `aria-live="polite"`, and `data-target … class="scriba-state-{current|highlight|idle}"` baking. Grep-confirmed repo-wide: **no `.scriba-highlighted` CSS, no primitive baking it** (`scriba/**/*.css`, `scriba/**/primitives/*.py`).
