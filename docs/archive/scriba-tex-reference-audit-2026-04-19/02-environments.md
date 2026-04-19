# §3–4 Environments Audit

Audited: `docs/SCRIBA-TEX-REFERENCE.md` lines 112–162 against:
- `scriba/animation/parser/grammar.py` (`_try_parse_options`, `_dispatch_command`)
- `scriba/animation/parser/ast.py` (`AnimationOptions`, `FrameIR`)
- `scriba/animation/constants.py` (`VALID_OPTION_KEYS`)
- `scriba/animation/detector.py` (`detect_animation_blocks`, `detect_diagram_blocks`)
- `scriba/animation/renderer.py` (`AnimationRenderer`, `DiagramRenderer`)
- `scriba/animation/emitter.py` / `_html_stitcher.py` / `_frame_renderer.py`
- `scriba/animation/errors.py` (`ERROR_CATALOG`)

---

## Findings

### [HIGH] `width`, `height`, `layout`, `grid` options accepted but never consumed (lines 119, 154)

Doc says: The option block `[id="...", label="..."]` implies these are the meaningful keys. The doc does not mention `width`, `height`, `layout`, or `grid` as environment-level options, but neither does it warn they are ignored.

Code does: `VALID_OPTION_KEYS` (`constants.py:46`) admits `"width"`, `"height"`, `"layout"`, and `"grid"`. `AnimationOptions` (`ast.py:290–298`) stores `width`, `height`, and `layout` as parsed fields with defaults (`layout` defaults to `"filmstrip"`). However:

- `width` and `height` are stored in `AnimationOptions` but are **never read** anywhere in `renderer.py`, `_html_stitcher.py`, `_frame_renderer.py`, or `emitter.py`. No SVG or `<figure>` element receives a `style` attribute from them.
- `layout` is stored (default `"filmstrip"`) but is **never read** by the renderer. The static filmstrip emitter hard-codes `data-layout="filmstrip"` unconditionally (`_html_stitcher.py:100`, `_html_stitcher.py:208`); `"stack"` is never applied.
- `grid` is in `VALID_OPTION_KEYS` but is **not a field** on `AnimationOptions` at all — it is silently discarded after validation passes. (Note: `grid` is a valid parameter name for the `MetricPlot` and `Plane2D` primitives and for the `Grid` primitive type, but it is not an environment-level concept.)

Recommendation: Either document all four accepted-but-inert keys explicitly with a "reserved / no effect" note, or remove `width`, `height`, `layout`, and `grid` from `VALID_OPTION_KEYS` until they are implemented. At minimum, warn authors using `layout=stack` that the option has no effect in the current version, to prevent silent no-ops.

---

### [HIGH] `\narrate` documented as "should" but "exactly one" is structurally enforced with different rules (line 141)

Doc says (line 141): "Each `\step` should have exactly one `\narrate`."

Code does: The parser (`grammar.py:276–284`) raises `E1055` if a second `\narrate` appears in the same step — so the upper bound (at most one) is a **hard error**, not a soft guideline. The lower bound (at least one) is **not enforced** at all: a `\step` with no `\narrate` is silently accepted; `narrate_body` defaults to `None` (`ast.py:333`) and produces an empty `<p class="scriba-narration">` in the output.

Recommendation: Replace "should have exactly one" with: "At most one `\narrate` per `\step` (a second raises `E1055`). Omitting `\narrate` is permitted and renders an empty narration paragraph."

---

### [HIGH] `\highlight` persistence rule differs between animation and diagram but doc says "same primitives" (lines 144–145, 151)

Doc says (line 144–145): "`\highlight` is **ephemeral** (auto-cleared at next `\step`)". Line 151 says diagram uses "same primitives" with no qualification.

Code does: `DiagramRenderer.render_block` (`renderer.py:708–709`) calls `SceneParser().parse(..., allow_highlight_in_prelude=True)`. The docstring for `DiagramRenderer` (`renderer.py:674`) explicitly states "`\highlight` is persistent (not ephemeral)" inside a diagram, because there are no steps to trigger the auto-clear. This difference is real and consequential — a `\highlight` in a diagram produces permanent SVG highlighting, while the same command in an animation prelude is an error (E1053 is raised unless `allow_highlight_in_prelude=True`).

Recommendation: Add a diagram-specific note: "In `diagram` environments, `\highlight` is allowed and behaves as persistent (there are no steps to clear it)."

---

### [HIGH] `\shape` after `\step` documented as MUST but only enforced in animation, not cross-checked against diagram (line 140)

Doc says (line 140): "All `\shape` declarations MUST be before first `\step`."

Code does: `grammar.py:246–255` raises `E1051` if `\shape` appears after any `\step`. This is correct for animation. In diagram mode, there are no `\step` commands (enforced after parsing), so `\shape` is always in the prelude by construction — no separate guard needed. The doc statement is accurate but could be clarified to note it only applies to the animation environment.

Recommendation: LOW-priority clarification. No code defect.

---

### [MED] `diagram` environment: `id=` option documented and parsed but applied inconsistently (line 154)

Doc says (line 154): `\begin{diagram}[id="my-diagram", label="Graph visualization"]` — implies `id` overrides the auto-generated scene ID.

Code does: `DiagramRenderer.render_block` (`renderer.py:719–721`) applies `id` with a `hasattr` guard rather than the clean direct field access used by `AnimationRenderer` (`renderer.py:426–429`). Both work correctly in practice, but the diagram path's defensive `hasattr` is a code smell suggesting the diagram renderer was not updated when `AnimationOptions` grew the `id` field. More critically, the `label` option for diagram is parsed into `ir.options.label` but is **never used** — `emit_diagram_html` (`_html_stitcher.py:641–675`) emits no `aria-label` attribute and no caption, so the label is silently dropped.

Recommendation: Add `aria-label` to the `<figure class="scriba-diagram">` element using `ir.options.label` when present. Document that `label` sets the figure's accessible name.

---

### [MED] Undocumented accepted option: `layout` with value `"stack"` (line 119)

Doc says: Only shows `id` and `label` in the example option block.

Code does: `VALID_OPTION_KEYS` includes `"layout"` and `AnimationOptions.layout` accepts `Literal["filmstrip", "stack"]` with default `"filmstrip"` (`ast.py:298`). Authors can write `[layout=stack]` without an error, but it has zero effect on output (see finding #1 above).

Recommendation: Either document it as reserved-for-future-use, or remove it.

---

### [MED] Stray `\end{diagram}` is silently ignored, unlike animation (detector.py)

Doc says: Nothing on error behavior for stray `\end{diagram}`.

Code does: `detect_diagram_blocks` (`detector.py:161–168`) silently `continue`s on a stray `\end{diagram}` without a matching `\begin{diagram}`. By contrast, `detect_animation_blocks` raises `E1007` for the identical situation (`detector.py:97–107`). The asymmetry means a typo in a diagram close tag is silently dropped rather than flagged.

Recommendation: Document the asymmetry, or align the diagram detector to raise `E1007` on stray `\end{diagram}`.

---

### [LOW] `\compute` placement shown before `\shape` in §3.1 example but code accepts either order (lines 121–122)

Doc says (lines 121–122): Example shows `\compute{...}` appearing before `\shape{name}{...}` in the prelude.

Code does: The parser collects `shape` and `prelude_compute` into separate lists in any order within the prelude. Shapes declared after `\compute` blocks work identically.

Recommendation: Add a note that `\compute` and `\shape` can appear in any order in the prelude.

---

### [LOW] §3.2 frame limits described as "Soft limit: 30 / Hard limit: 100" but counting includes substory frames (lines 142)

Doc says (line 142): "Soft limit: 30 frames. Hard limit: 100 frames."

Code does: `renderer.py:440–448` counts `frame_count + _count_substory_frames(frames)` and applies the 30/100 thresholds to the combined total. An animation with 20 top-level frames and 85 substory steps across them triggers the hard limit even though the top-level frame count is only 20.

Recommendation: Clarify: "Soft limit: 30 total frames (including substory frames). Hard limit: 100 total frames."

---

### [LOW] E1005 error code cited for duplicate `\step` label — actual code used is correct but catalog message is misleading (emitter.py:173)

Doc says (line 192): "A duplicate label raises `E1005`."

Code does: `validate_frame_labels_unique` (`emitter.py:173`) raises `ValidationError(code="E1005")`. The `ERROR_CATALOG` entry for `E1005` reads `"Invalid option or parameter value."` — a generic message. The actual raised message is a specific duplicate-label string. The code and doc agree on the code number, but the catalog description does not reflect the duplicate-label use case.

Recommendation: Either add `E1019`-style language for duplicate frame labels, or expand the `E1005` catalog entry to mention this usage.

---

## Coverage Gaps

- **Undocumented valid option keys**: `width`, `height`, `layout`, `grid` are all accepted by the parser without error but never mentioned in §3 or §4. Authors hitting `E1004` for a mis-spelled key will be surprised to learn these keys exist.
- **`/scriba/diagram/` module does not exist**: The task brief referenced this path. Diagram functionality lives entirely in `scriba/animation/` (renderer, emitter, detector, parser). This should be noted in any contributor docs.
- **`\highlight` in animation prelude**: E1053 is raised when `\highlight` appears before the first `\step` in an animation. This is not mentioned in §3. The doc lists `\highlight` as ephemeral but never says it is banned from the prelude.
- **`\apply` in animation prelude**: Doc (line 123) shows `\apply` in the prelude as "optional initial state". This is correct and consistent with code — `prelude_commands` accepts `ApplyCommand`.
- **Nesting rules**: `NestedAnimationError` (E1003) fires on `\begin{animation}` inside another animation. There is no equivalent check for `\begin{diagram}` inside an animation or vice versa (the diagram detector runs independently on the full source). The doc does not address nesting at all.

---

## Verdict

**5/10**

The §3–4 section covers the essential structure accurately (options `id`/`label`, frame limits, delta semantics, `\highlight` ephemeral rule in animation). However it has two HIGH-severity omissions that will cause author confusion: (1) three option keys (`width`, `height`, `layout`) are silently accepted and ignored with no warning, plus a fourth (`grid`) is accepted and not even stored; (2) the `\narrate` "should" framing inverts the actual enforcement — the upper bound is hard, the lower bound is unenforced. The `\highlight` persistence difference between animation and diagram is a third HIGH gap that will produce unexpected output. Four MED/LOW findings cover diagram `label` being dropped, the stray-`\end{diagram}` silent skip, substory frame counting, and minor example ordering ambiguity.
