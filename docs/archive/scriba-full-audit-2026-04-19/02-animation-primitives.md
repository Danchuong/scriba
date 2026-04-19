# Animation Primitives Audit — 2026-04-19

Scope: `scriba/animation/primitives/` — 16 concrete primitives plus `base.py`, `_types.py`, `layout.py`.

---

## 1. Overall Score: 7.5 / 10

The layer is architecturally coherent. `PrimitiveBase` enforces the four mandatory abstract methods, `BoundingBox` is a properly frozen dataclass, `STATE_COLORS` is a single source of truth, and the `layout.py` vstack helper eliminates the font-metric ratchet that plagued earlier waves. No security issues (no SQL, no shell exec, no eval). The score is held back by three clusters: incomplete highlight/hidden-state coverage across ~7 primitives, duplicate module-level code that belongs in `base.py`, and inconsistent `apply_command` override signatures that deviate silently from the base class contract.

---

## 2. Per-Primitive Scorecard

| Primitive | Score /10 | Notable Issues |
|---|---|---|
| **array** | 8 | `E1103` imported unused (F401); `_escape_xml` imported unused (F401); `_parse_index_labels` duplicated verbatim from `dptable.py`; no highlight path via `resolve_effective_state` — uses it correctly. |
| **codepanel** | 7 | No `_highlighted`/`resolve_effective_state` — highlight state is silently unreachable for any `line[i]` selector. No `resolve_annotation_point` override (annotation arrows cannot target lines). |
| **dptable** | 7.5 | `E1103` imported unused (F401); `_escape_xml` imported unused (F401); `_parse_index_labels` duplicated from `array.py`. `_emit_1d_cells` does not escape `target` in `data-target`; uses fixed `CELL_WIDTH` ignoring dynamic cell-width like Array does. |
| **graph** | 8.5 | Best-in-class: mutation API, warm-start relayout, Opt-4 memoisation, proper `_invalidate_addressable_cache`, `hidden` state handled. Inline weight-label constants (`_WEIGHT_FONT`, `_PILL_PAD_*`) defined inside the render loop (lines 765-768) — should be module-level named constants. |
| **grid** | 7.5 | `E1103` imported unused (F401). No `_min_arrow_above` guard in `bounding_box` (present in `emit_svg` but not `bounding_box` — diverges from Array pattern). Does not escape `data-target` attribute (uses bare f-string). |
| **hashmap** | 7 | `E1103` imported unused (F401); `digit_count` computed but never used (F841, line 116). No `_min_arrow_above` guard. `emit_svg` does not use `resolve_effective_state` — writes highlight state manually without the base helper. |
| **layout** | 9.5 | Exemplary: frozen `TextBox` dataclass, `__all__` declared, full docstrings, typed signatures, mathematical rationale cited. Minor: not strictly a primitive but lives in the primitives package without a note. |
| **linkedlist** | 7 | No `ACCEPTED_PARAMS` (empty frozenset inherits → no param validation). `apply_command` missing `target_suffix` kwarg (breaks base class signature). Index labels emitted via raw `<text>` instead of `_render_svg_text` (line 432–435) — bypasses LaTeX rendering path. No highlight support (`_highlighted` not consulted). |
| **matrix** | 7 | `E1103`, `DEFAULT_STATE`, `svg_style_attrs` imported unused (F401 ×3); ambiguous variable `l` (E741, line 218). No annotation arrow support (`resolve_annotation_point` not overridden, arrows cannot target cells). `bounding_box` does not reserve `arrow_above` space. |
| **metricplot** | 8 | Uses `logging` correctly. `ACCEPTED_PARAMS` and `SELECTOR_PATTERNS` defined. `addressable_parts` returns `[self.name]` rather than `["all"]` — inconsistent with every other primitive's "all" convention. No `bounding_box` `arrow_above` reservation. |
| **numberline** | 7.5 | `F841`: `end` assigned unused (line 379). Uses its own manual arrow loop instead of `emit_annotation_arrows` from base — code duplication with `queue.py`. `_arrow_height_above` private helper duplicates Queue's identical method. |
| **plane2d** | 7.5 | `Sequence` imported unused (F401). `colors` assigned but unused in `_emit_points` (F841, line 888). At 1227 lines this is the largest file — well over the 800-line limit. `xlabel`/`ylabel`/`label` accepted but silently produce no rendered output (documented as v0.6.2 follow-up, but no warning is emitted). |
| **queue** | 7 | `E1103` imported unused (F401). Implements its own arrow-drawing loop (lines 403–421) that partially duplicates `emit_annotation_arrows` from base; misses `plain_arrow` (`arrow=true`) path that the base handles. |
| **stack** | 7 | `E1103` imported unused (F401). **`ACCEPTED_PARAMS` is absent** (inherits the base's empty frozenset) — undocumented opt-out; unknown params silently accepted. `apply_command` missing `target_suffix` kwarg (breaks base signature). Uses `getattr(self, "_highlighted", set())` defensive guard — unnecessary since `_highlighted` is always set by `PrimitiveBase.__init__`. |
| **tree** | 8 | `apply_command` missing `target_suffix` kwarg. `wild-card import` from `tree_layout` (`from ... import *`) pollutes namespace. Sparse segtree init does not validate `range_lo <= range_hi`. |
| **variablewatch** | 8.5 | `apply_command` correctly carries `target_suffix`. Monotonic column-width invariant is properly maintained. `warnings.warn` inside `__init__` for empty `names` is correct. Minor: bare `import warnings` inside `__init__` (line 86) should be a top-level import. |

---

## 3. Cross-Cutting Findings

| Severity | File:Line | Issue | Fix |
|---|---|---|---|
| HIGH | `stack.py:69–332` | `ACCEPTED_PARAMS` is absent — class inherits the base's empty `frozenset()` which disables param validation entirely. Unknown `\\shape` params are silently accepted, masking typos like `max_visible=10` vs `max_visible=10` (identical) but failing to catch `orientaton=vertical`. No code comment explains this opt-out. | Add `ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset({"items", "orientation", "max_visible", "label"})` or add a class-level comment explaining why param validation is intentionally disabled. |
| HIGH | `stack.py:133`, `linkedlist.py:137`, `tree.py:229` | `apply_command` overrides drop the `target_suffix` keyword-only argument that `PrimitiveBase.apply_command` declares (line 430–436 in `base.py`). Any caller that passes `target_suffix=` to these three primitives silently discards it — a Liskov substitution violation that mypy misses because the base signature uses a default. | Add `*, target_suffix: str | None = None` to all three overrides to match the base contract. |
| HIGH | `codepanel.py:172–288` | `highlight` state is unreachable for any `line[i]`. The emit loop calls `get_state(suffix)` directly and never consults `_highlighted` or `resolve_effective_state`. A `\\highlight{code.line[3]}` command writes to `_highlighted` but the emitter ignores it. | Replace the inline `line_state = self.get_state(suffix)` with `line_state = self.resolve_effective_state(suffix)`. |
| HIGH | `linkedlist.py:352–436` | No highlight support. `emit_svg` calls `self.get_state(node_suffix)` and `self.get_state(link_suffix)` but never consults `_highlighted`. A `\\highlight{ll.node[2]}` command has zero visual effect. | Call `self.resolve_effective_state(suffix)` for each node/link instead of bare `get_state`. |
| HIGH | `hashmap.py:267–346` | No highlight support. `emit_svg` calls `get_state(suffix)` then propagates the `all` state manually but never checks `_highlighted`. A `\\highlight{hm.bucket[3]}` command has zero visual effect. | Replace `state = self.get_state(suffix)` / `all_state` pattern with `self.resolve_effective_state(suffix)` (which already handles `all` propagation via the base). |
| HIGH | `variablewatch.py:268–341` | Same issue: `get_state(suffix)` / manual `all` propagation, no `_highlighted` check. A `\\highlight{vars.var[i]}` command is silently ignored. | Use `self.resolve_effective_state(suffix)`. |
| HIGH | `tree.py:30` | `from scriba.animation.primitives.tree_layout import *` wildcard import — pollutes the module namespace with every private in `tree_layout.py` and makes it impossible to know what names are actually needed. | Replace with explicit named imports: `from scriba.animation.primitives.tree_layout import _build_segtree, _reingold_tilford, _shorten_line_to_circle`. |
| HIGH | `matrix.py:403–409` | `bounding_box` does not reserve `arrow_above` space. If an annotation arrow is attached to a matrix cell, `bounding_box` returns a height that does not include arrow headroom, causing the layout engine to undersize the viewBox and clip arrows. | Follow the Array/DPTable pattern: compute `arrow_above = arrow_height_above(...)` and add it to `h` before returning. |
| MEDIUM | `array.py:409–427` and `dptable.py:499–510` | `_parse_index_labels` is defined identically in both files (same function body, same module-level docstring). | Extract to `base.py` or a new `_helpers.py` module; import from there in both consumers. |
| MEDIUM | `plane2d.py:1–1227` | File is 1227 lines — 53 % over the 800-line project limit. The `_emit_points`, `_emit_lines`, `_emit_segments`, `_emit_polygons`, `_emit_regions` methods are cohesively grouped and could be extracted to `plane2d_emit.py` alongside the existing `plane2d_compute.py`. | Split emit helpers into `plane2d_emit.py`; keep `Plane2D` class and `apply_command` routing in `plane2d.py`. |
| MEDIUM | `array.py:11`, `dptable.py:11`, `grid.py:11`, `hashmap.py:17`, `matrix.py:14`, `queue.py:14`, `stack.py:14` | `E1103` (the error code constant) is imported from `scriba.animation.errors` but never referenced in the module body. Ruff F401 flags all seven. | Remove unused import in each file. |
| MEDIUM | `matrix.py:18`, `matrix.py:27` | `DEFAULT_STATE` and `svg_style_attrs` imported but unused. `svg_style_attrs` is a notable omission — it means Matrix does not apply state-driven inline colors to the stroke at all (colorscale controls fill, but state stroke is CSS-only). | Remove unused imports; if state-based stroke is intentional CSS-only behavior, add a comment saying so. |
| MEDIUM | `hashmap.py:116` | `digit_count = len(str(max_idx))` computed at line 116 inside `_index_col_width` but the value is never read — only `needed` is returned. | Remove the dead assignment or use `len(str(max_idx))` inline. |
| MEDIUM | `numberline.py:379` | `end = int(m.group(2))` inside `_parse_label_string` — `end` is never read after assignment. | Remove or use the value. |
| MEDIUM | `plane2d.py:888` | `colors = svg_style_attrs(state)` inside `_emit_points` — `colors` is computed but never read (the circle element uses only CSS class-driven state, not inline fill/stroke). | Remove the dead assignment or, if inline colors are needed for non-CSS consumers, use the variable. |
| MEDIUM | `numberline.py:196–203` and `queue.py:242–248` | Both primitives define an identically-structured `_arrow_height_above` private helper that wraps `arrow_height_above` with `_min_arrow_above` guard. This pattern appears in at least 4 primitives via inline `max(computed, getattr(self, "_min_arrow_above", 0))`. | Extract to `PrimitiveBase` as `effective_arrow_above(annotations)` so subclasses call `self.effective_arrow_above(anns)` rather than repeating the guard. |
| MEDIUM | `graph.py:765–768` | Weight-label rendering constants (`_WEIGHT_FONT = 11`, `_PILL_PAD_X = 5`, `_PILL_PAD_Y = 2`, `_PILL_R = 3`) are defined inside the inner `for` loop body — re-created on every edge iteration. | Hoist to module-level named constants. |
| MEDIUM | `queue.py:403–421` | Implements its own Bezier arrow loop that partially duplicates `emit_annotation_arrows` from `PrimitiveBase`. The local loop misses the `arrow=true` (plain pointer) path; `plain_arrow_svg` is never called. | Delete the local loop; call `self.emit_annotation_arrows(parts, effective_anns, render_inline_tex=render_inline_tex)` as Array, Grid, HashMap, and VariableWatch already do. |
| MEDIUM | `matrix.py:218` and `plane2d_compute.py:180` | Ambiguous variable name `l` (E741) — visually identical to `1` (one) in most fonts. | Rename to `label` or `lab` in `matrix.py`; rename in `plane2d_compute.py` to `segment_len` or `length`. |
| MEDIUM | `metricplot.py:751–753` | `addressable_parts` returns `[self.name]` (the shape name itself, e.g., `["plot"]`). Every other primitive returns suffixes like `["all"]` or `["cell[0]"]` without the shape-name prefix. `validate_selector` also accepts `suffix == self.name` as a special case. This breaks the uniform contract consumers depend on. | Change to `return ["all"]` and `validate_selector` to `return suffix == "all"`. |
| MEDIUM | `linkedlist.py:432–435` | Index labels below nodes are emitted via a raw `<text>` element instead of `_render_svg_text`. This means index labels cannot contain inline LaTeX math and bypass the shared text-rendering path. | Replace with `_render_svg_text(...)`. |
| MEDIUM | `variablewatch.py:86` | `import warnings` inside `__init__` body — executed every time a `VariableWatch` is constructed. | Move to top-level import. |
| LOW | `stack.py:232` | `hl_suffixes = getattr(self, "_highlighted", set())` — defensive `getattr` guard is unnecessary; `PrimitiveBase.__init__` unconditionally sets `self._highlighted = set()` (line 210 of `base.py`). Same pattern in `graph.py:835` and `plane2d.py:876`. | Replace `getattr(self, "_highlighted", set())` with `self._highlighted` in all three files. |
| LOW | `plane2d.py:118–138` | `xlabel`, `ylabel`, `label` are listed in `ACCEPTED_PARAMS` with a comment noting they have "no rendered effect" (v0.6.2 follow-up). No runtime warning is emitted when an author supplies these params. Authors will author files expecting labels, see nothing, and have no diagnostic signal. | Emit a `warnings.warn` or `_emit_warning` when `xlabel`/`ylabel` are supplied but cannot be rendered. |
| LOW | `dptable.py:358–398` (`_emit_1d_cells`) | `data-target` attribute interpolated directly without `_escape_xml`. All other primitives escape the target (e.g., `array.py:255`). Safe in practice since node names are validated as `\w+`, but inconsistent. | Wrap `target` in `_escape_xml(target)` for defensive consistency. |
| LOW | `grid.py:234` | Same as dptable — `data-target="{target}"` without `_escape_xml`. | Apply `_escape_xml`. |
| LOW | `plane2d.py:143–144` | Two `type: ignore[assignment]` comments on the `xrange`/`yrange` tuple assignments — the underlying issue is that `params.get("xrange", [-5.0, 5.0])` returns `list | None`, but the assignment annotation is `tuple[float, float]`. Fix the type rather than suppressing it. | Use `tuple(params.get("xrange", (-5.0, 5.0)))` with a named default constant and proper annotation. |

---

## 4. Consistency Matrix

Features that exist in some primitives but are missing in others.

| Feature | array | codepanel | dptable | graph | grid | hashmap | linkedlist | matrix | metricplot | numberline | plane2d | queue | stack | tree | variablewatch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ACCEPTED_PARAMS` defined | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | **N** | Y | Y |
| `resolve_annotation_point` override | Y | **N** | Y | Y | Y | Y | Y | **N** | **N** | Y | Y | Y | **N** | Y | Y |
| Uses `resolve_effective_state` | Y | **N** | Y | indirect | Y | **N** | **N** | Y | n/a | Y | indirect | indirect | indirect | indirect | **N** |
| `_min_arrow_above` guard in `bounding_box` | Y | n/a | Y | Y | **N** | **N** | Y | **N** | **N** | Y | **N** | Y | n/a | Y | Y |
| Arrow space in `bounding_box` (`arrow_above`) | Y | **N** | Y | Y | Y | Y | Y | **N** | **N** | Y | **N** | Y | **N** | Y | Y |
| Uses `emit_annotation_arrows` (base helper) | Y | **N** | Y | Y | Y | Y | Y | **N** | **N** | **N** | **N** | **N** | **N** | **N** | Y |
| `apply_command` has `target_suffix` kwarg | n/a | n/a | n/a | **N** | n/a | Y | **N** | n/a | **N** | n/a | **N** | **N** | **N** | **N** | Y |
| `_escape_xml` on `data-target` | Y | Y | partial | Y | **N** | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| Hidden state handled in render | n/a | **N** | n/a | Y | **N** | **N** | **N** | **N** | n/a | **N** | Y | **N** | **N** | Y | **N** |

Legend: Y = present, N = missing/incomplete, n/a = not applicable for this primitive type, indirect = uses inline equivalent rather than base method.

---

## 5. Top 3 Priorities

### Priority 1 — Fix the highlight/hidden state blindspot across 6 primitives

`codepanel`, `linkedlist`, `hashmap`, `variablewatch`, `queue`, and `stack` all call `get_state()` directly in their render loops and never consult `_highlighted` or `resolve_effective_state`. This means `\\highlight{...}` commands targeting these primitives have zero visual effect — a silent correctness bug that will manifest in any scene that uses highlight states on these structures.

The fix is mechanical: replace `get_state(suffix)` with `resolve_effective_state(suffix)` in each emit loop. For primitives that also do manual `all` state propagation (hashmap, variablewatch, queue), the base `resolve_effective_state` does not handle `all` propagation — that part should remain, but `_highlighted` should be checked afterward via `_is_highlighted`.

Relevant files:
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/codepanel.py:213`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/linkedlist.py:357`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/hashmap.py:272`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/variablewatch.py:272`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/queue.py:290`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/stack.py:239`

### Priority 2 — Fix the `apply_command` Liskov violation and document Stack's missing `ACCEPTED_PARAMS`

`stack.py`, `linkedlist.py`, `tree.py`, `graph.py`, `queue.py`, and `plane2d.py` all override `apply_command` without the `target_suffix: str | None = None` keyword argument that `PrimitiveBase` declares. Any caller that routes a targeted apply (e.g., `stack.cell[0]` with `value=X`) through the base dispatch will silently drop `target_suffix`. Only `hashmap.py` and `variablewatch.py` implement the full signature correctly.

Separately, `Stack` has no `ACCEPTED_PARAMS` at all — it inherits the empty `frozenset()` which disables validation entirely. If this is an intentional opt-out it must be documented at the class level; if not, the frozenset must be populated.

Relevant files:
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/base.py:430–436` (reference signature)
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/stack.py:69` (`ACCEPTED_PARAMS` missing), `stack.py:133` (`apply_command` signature)
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/linkedlist.py:137`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/tree.py:229`

### Priority 3 — Extract shared duplication into `base.py`: `_parse_index_labels`, `_arrow_height_above` guard, and `_min_arrow_above` in `bounding_box`

Three patterns are copy-pasted across multiple primitives:

1. `_parse_index_labels` is defined identically in `array.py:409` and `dptable.py:499`. Extract to `base.py` or `_types.py` and import from there.

2. The `effective_arrow_above` pattern — `max(arrow_height_above(...), getattr(self, "_min_arrow_above", 0))` — appears in-line in at least eight primitives. Promote to `PrimitiveBase.effective_arrow_above(annotations, *, cell_height, layout="1d")` and call it from each subclass.

3. Six primitives (`grid`, `hashmap`, `matrix`, `metricplot`, `plane2d`, `stack`) do not add `arrow_above` to their `bounding_box` return value, causing layout-engine underestimation when annotations are present. Fixing the extracted helper from point 2 will make this easier to audit and enforce.

Relevant files:
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/array.py:409`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/dptable.py:499`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/matrix.py:403`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/grid.py:290`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/hashmap.py:210`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/primitives/base.py:300–314` (candidate location for the extracted helper)

---

*Generated by the python-reviewer agent on 2026-04-19. Static tools run: ruff (18 issues, 11 files), mypy (no issues). No security issues found.*
