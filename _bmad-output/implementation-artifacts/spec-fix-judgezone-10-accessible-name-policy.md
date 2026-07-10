# JudgeZone #10 — Accessible-Name Policy Fix (R-15)

**Status:** GREEN. Structural fix landed in both owned regions; targeted tests pass; no golden re-bless performed (by design — see below).

## Contract

A widget's accessible name comes from author-provided natural language only:
`label=` (diagrams), step `title=` (`\step[title=...]`), or narration text. When
none of these exist, the SVG emits **no `<title>` element at all**. The internal
`scene_id`/`id=` slug must never surface as a `<title>` — not as a first choice,
not as a fallback.

This closes the shared root cause behind two symptoms:

1. **100% of static diagrams** — `\begin{diagram}` forbids `\step[title=]` and
   `\narrate` at parse time (E1050/E1054), so every diagram hit the `scene_id`
   fallback unconditionally, even when `label=` was supplied (it was wired to
   the outer `<figure>`'s `aria-label` only, never to the inner `<svg>`'s own
   `<title>`).
2. **Animation "silent steps"** — a `\step` with neither `\narrate` nor
   `title=` (no validator forbids this combination) hit the same fallback.

## Code changes

### `scriba/animation/renderer.py` — `DiagramRenderer.render_block` (~:1113-1126)

Before, `label=` was never threaded past the outer figure. After, it's also
passed as the frame's `title=`, giving the SVG's own `<title>` builder
natural-language content to draw on:

```python
# BEFORE (~:1113-1119)
        snap = state.snapshot(index=1, narration=None)

        frame = _snapshot_to_frame_data(snap, 1, scene_id, ctx)
        minify = ctx.metadata.get("minify", True)
        # Forward env options exactly like the animation path — the emitter
        # half (aria-label, max-size) was wired and tested, but this call
        # site never fed it, so documented diagram label/width/height were
        # silently dropped.
        _opts = getattr(ir, "options", None)
        html = emit_html(

# AFTER (~:1113-1129)
        snap = state.snapshot(index=1, narration=None)

        # Forward env options exactly like the animation path — the emitter
        # half (aria-label, max-size) was wired and tested, but this call
        # site never fed it, so documented diagram label/width/height were
        # silently dropped. `label` is threaded into the frame's `title=`
        # below too: diagrams forbid \step[title=]/\narrate (E1050/E1054),
        # so without it the SVG's own <title> (JudgeZone #10 / R-15) would
        # have no natural-language content to draw on.
        _opts = getattr(ir, "options", None)
        frame = _snapshot_to_frame_data(
            snap, 1, scene_id, ctx,
            title=(getattr(_opts, "label", None) or None),
        )
        minify = ctx.metadata.get("minify", True)
        html = emit_html(
```

`_snapshot_to_frame_data`'s `title` param already existed (used by the
animation path); this call site simply never fed it. `title` also folds into
`FrameData.narration_html` as a side effect — verified inert for diagrams:
`emit_diagram_html` (`_html_stitcher.py`) never reads `narration_html`, only
the `svg_html` that `_emit_frame_svg` returns.

### `scriba/animation/_frame_renderer.py` — `_emit_frame_svg`'s title builder (~:1847-1902)

Before, an empty title/narration fell back to `scene_id`. After, it's emitted
as `""` and the `<title>` element is omitted entirely — mirroring the existing
conditional pattern already used one line above for `aria-labelledby`:

```python
# BEFORE (~:1847-1875, tail)
            else:
                _title_text = _re.sub(r"<[^>]+>", " ", _raw_narration).strip()
            if not _title_text:
                _title_text = scene_id
        # Re-encode for safe embedding inside <title>…</title>.
        _title_escaped = _html_mod.escape(_html_mod.unescape(_title_text))
        ...
        svg_parts: list[str] = [
            f'<svg class="scriba-stage-svg" viewBox="{viewbox}" '
            f'style="max-width:calc({vb_width}px * var(--scriba-diagram-font-scale, 1))" '
            f'role="img" '
            + (f'aria-labelledby="{_escape_fn(narration_id)}" ' if narration_id else "")
            + 
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<title>{_title_escaped}</title>',  # R-15: title first child
        ]

# AFTER (~:1847-1902, tail)
            else:
                _title_text = _re.sub(r"<[^>]+>", " ", _raw_narration).strip()
        # Re-encode for safe embedding inside <title>…</title>.  Empty when no
        # natural-language title/narration exists -- the <title> element is
        # then omitted below rather than populated with a non-prose id.
        _title_escaped = (
            _html_mod.escape(_html_mod.unescape(_title_text)) if _title_text else ""
        )
        ...
        svg_parts: list[str] = [
            f'<svg class="scriba-stage-svg" viewBox="{viewbox}" '
            f'style="max-width:calc({vb_width}px * var(--scriba-diagram-font-scale, 1))" '
            f'role="img" '
            + (f'aria-labelledby="{_escape_fn(narration_id)}" ' if narration_id else "")
            +
            f'xmlns="http://www.w3.org/2000/svg">'
            + (f'<title>{_title_escaped}</title>' if _title_escaped else ""),  # R-15
        ]
```

The `if not _title_text: _title_text = scene_id` branch is deleted outright —
`scene_id` is no longer read anywhere in this function's title logic. Both
edits stayed within the owned `~:1847-1902` region; `role="img"` (unconditional)
and the pre-existing `aria-labelledby` conditional were left untouched.

Because `_emit_frame_svg` is the single shared title builder for all four HTML
emission modes (`emit_diagram_html`, `emit_animation_html`,
`emit_interactive_html`, `emit_substory_html`), this one fix closes both the
diagram case and the animation silent-step case simultaneously — no changes
were needed in `_html_stitcher.py`.

## Tests added (TDD: RED confirmed before the fix, GREEN after)

| File | Test(s) added | Behavior asserted |
|---|---|---|
| `tests/unit/test_env_options_wired.py` | `test_diagram_label_reaches_svg_title`, `test_diagram_without_label_omits_svg_title`, `test_diagram_without_label_keeps_role_img_and_no_dangling_aria` | `label=` → `<title>{label}</title>`; no `label=` → no `<title>` at all, never the internal id; `role="img"` and no dangling `aria-labelledby` survive |
| `tests/animation/test_diagram_renderer.py` | extended `TestRenderStaticFigure.test_renders_single_figure` | no `label=` → no `<title>` in a real `DiagramRenderer.render_block` artifact |
| `tests/unit/test_phase_b_diagram.py` | extended `TestDiagramStaticFigure.test_shape_only_renders` | shape-only diagram (no options at all) → no `<title>` |
| `tests/unit/test_filmstrip_aria.py` | `test_frame_with_title_uses_it_as_svg_title`, `test_frame_without_title_or_narration_omits_svg_title` (+ extended `_make_frame` helper with a `title` param) | closes the R-15 spec/test-drift gap (Finding 6): this file is R-15's cited test ref but never asserted on `<title>` content before |
| `tests/unit/test_step_title.py` | `test_no_narration_no_title_omits_svg_title` | the animation "silent step" edge case (no `\narrate`, no `title=`) → no SVG-level `<title>`, verified against the full `render_file` HTML-document pipeline |

RED baseline: 6 new/modified assertions failed against pre-fix code (bug
reproduced exactly as the investigation doc predicted); 48 pre-existing tests
in these 5 files were already green and stayed green throughout.

**One self-caught test bug during GREEN verification:** the first version of
`test_no_narration_no_title_omits_svg_title` asserted `"<title>" not in
html_out`, which is too broad — `render_file` always wraps output in a full
HTML document with an unconditional `<title>Scriba — {filename}</title>` in
`<head>` (`render.py:37`), unrelated to the SVG fix. Corrected to
`html_out.count("<title>") == 1` (only the doc-level tag) plus an explicit
`"<title>d</title>" not in html_out` check against the scene's actual id.
Final run:

```
uv run pytest tests/unit/test_env_options_wired.py tests/unit/test_filmstrip_aria.py \
  tests/unit/test_step_title.py tests/unit/test_phase_b_diagram.py \
  tests/animation/test_diagram_renderer.py -q -p no:cacheprovider
54 passed in 0.59s
```

## Impact analysis (GitNexus)

`impact()` on both touched symbols (repo `scriba`, direction `upstream`,
callgraph mode):

| Symbol | impactedCount | risk (tool) | Direct callers (depth 1) |
|---|---|---|---|
| `_emit_frame_svg` (`_frame_renderer.py`) | 7 | LOW | `emit_animation_html`, `emit_substory_html`, `emit_interactive_html`, `emit_diagram_html` |
| `DiagramRenderer.render_block` (`renderer.py`) | 3 | LOW | `render.py:render_file` → `main` → CLI entry |

**Reconciling the tool's LOW rating against true blast radius:** the "LOW"
risk label reflects a narrow callgraph fan-out count (7 and 3 nodes,
respectively), not the behavioral output surface. `_emit_frame_svg`'s four
depth-1 callers are *all four* of scriba's HTML emission modes — collectively
they cover 100% of the SVG output the renderer ever produces. Depth-3 from
`_emit_frame_svg` reaches both `AnimationRenderer.render_block` and
`DiagramRenderer.render_block`, i.e. every top-level render entry point. In
practice: **this change touches every SVG frame the tool renders**, exactly as
anticipated ("expect HIGH; list affected flows"). Treat the tool's LOW as "few
call sites to reason about," not "small surface area affected."

`detect_changes(scope="unstaged")` reported `risk_level: "high"` for the
working tree as a whole, but that result is dominated by concurrent
sibling-agent edits to `scriba/animation/primitives/base.py` (`_below_lane_height`,
`_h_label_pad`) and `scriba/tex/renderer.py` — files explicitly outside this
task's scope fence, being edited in parallel by other BMAD agents in this
shared worktree. None of the 8 `affected_processes` it reported trace through
`_emit_frame_svg` or `DiagramRenderer.render_block`; the two symbols this fix
actually touched contribute 0 of those 8. The "high" verdict is not attributable
to this change.

## Repro verification (before → after)

Rendered via `render.py` (`--no-minify`) for all 4 cases, `<title>` extracted
by grep on the output HTML:

| Case | Source | Before (`<title>`) | After (`<title>`) |
|---|---|---|---|
| Diagram, no `label=` | `\begin{diagram}[id="internal-slug-x"]` | `<title>internal-slug-x</title>` (bug: internal id leaked) | *(none — SVG has no `<title>` element)* |
| Diagram, with `label=` | `\begin{diagram}[id="internal-slug-x", label="Two-element array"]` | `<title>internal-slug-x</title>` (bug: label ignored, id leaked) | `<title>Two-element array</title>` |
| Animation, narrated + titled step | 2 steps, one narrated, one `title="Swap"` | `<title>Initial state of the array.</title>` / `<title>Swap</title>` | **identical** — non-regression confirmed |
| Animation, silent step | `\step` with no `\narrate`, no `title=`, `id="internal-anim-slug-silent"` | `<title>internal-anim-slug-silent</title>` (bug: internal id leaked) | *(none — SVG has no `<title>` element)* |

(All four `.tex`/`.before.html`/`.after.html` files retained in the scratchpad
for reference.)

## Accessibility verification

- `role="img"` on the SVG: **unconditional**, unaffected by this change (line
  above the `aria-labelledby` conditional; untouched).
- `aria-labelledby`: unaffected — its own pre-existing conditional
  (`if narration_id else ""`) is independent of the `<title>` conditional
  added here. Diagrams pass `narration_id_override=""`, so they never emit
  `aria-labelledby` regardless of `<title>` presence — no dangling reference
  is possible in any of the 4 repro cases.
- Figure-level `aria-label` (outer `<figure>`, driven by `label=`): untouched
  by this fix — it was already correctly wired before this task; confirmed
  still passing via the pre-existing `TestDiagramAria` tests in
  `test_env_options_wired.py`.
- Net effect on computed accessible name (SVG 2 §5.1): when `<title>` is
  omitted and no `aria-label`/`aria-labelledby` sits on the `<svg>` itself,
  the SVG has no accessible name of its own — the enclosing `<figure>`'s
  `aria-label`/`aria-labelledby` is what assistive tech falls through to.
  This is strictly better than before (a fake, non-prose name) and never
  worse (no case regresses from "named" to "unlabeled" — the removed name was
  never a real one).

## Goldens expected to shift (NOT re-blessed — human review required)

Corrected count against the original estimate ("14 diagram docs"): verified by
direct inspection, **23** of the 107 `.tex` fixtures in
`tests/golden/examples/corpus/` contain a real `\begin{diagram}` block, and
every one of them currently has a `<title>{scene_id}</title>` (or, where
`label=` is set, an ignored-label `<title>{scene_id}</title>`) baked into its
paired `.html` golden — all 23 will shift:

```
05_diagram_prescan, apt_window_diagram, bfs_grid_editorial, diagram_intro,
diagram, diagram_multi, diagram_grid, fft_butterfly, dijkstra_editorial,
gep_v2_smoke, knapsack_editorial, mcmf, plane2d_annotations, plane2d_lines,
plane2d_ticks, segtree_editorial, test_edge_overlap, test_plane2d_dense,
test_plane2d_edges, test_reference_graph_tree, test_reference_unionfind,
test_reference_tex_heavy, two_sum_editorial
```

Additionally, a heuristic scan for the animation "silent step" pattern (a
`\step` with no `\narrate{...}` before the next `\step`/`\end{animation}` and
no `title=` on the `\step[...]` tag itself) across the full 107-file corpus
found **5 more** non-diagram fixtures that currently leak their scene id as a
`<title>` and will also shift (spot-checked against their current golden
`.html`, confirming the exact bug pattern in each):

```
10_selector_out_of_range, 12_selector_unknown_accessor,
14_annotate_arrow_bool, 17_empty_substory, decoration_spiral
```

**Total: 28 of 107 corpus goldens in `tests/golden/examples/corpus/` shift.**
None re-blessed, per instruction — `sync_corpus.py`/golden re-bless is left for
a human-reviewed follow-up pass.

Two other golden suites were checked and are **unaffected**:
- `tests/golden/animation/*.html` (5 differ/html fixtures) — verified
  empirically: none currently contain any `<title>` tag, so this code path
  doesn't reach the fallback this fix touches. No regression risk.
- `tests/golden/smart_label/*` (bug-B, critical-2-null-byte, ok-simple) —
  structurally out of scope: these fixtures call `emit_arrow_svg` in
  `_svg_helpers.py` directly (annotation-arrow `<title>`, a different,
  untouched code path — `bug-B`'s `<title>Arrow from arr.cell[0] to
  arr.cell[0]: self</title>` is that unrelated arrow-label title, not the
  frame-level title this task fixes).

## Regression risks

- **Diagrams without `label=` lose their SVG `<title>` entirely.** This is the
  intended fix, not a defect — the prior `<title>` was never a real accessible
  name, just a leaked internal slug. Any downstream tooling that scraped
  `<title>` text expecting the id (e.g. a hypothetical test or script keying
  off `<title>{id}</title>`) would break; none was found in the 5 targeted
  test files or the touched code paths.
- **`title=` now has two folding destinations for diagrams**: `FrameData.title`
  feeds both `narration_html` (dead for diagrams — confirmed `emit_diagram_html`
  never reads it) and the new `_emit_frame_svg` title builder. If a future
  change adds diagram narration rendering, this side effect will need
  re-checking — flagged here rather than silently relied upon.
- **28 golden fixtures now fail byte-for-byte comparison** until re-blessed by
  a human reviewer (explicitly deferred, not done in this task).
- No changes were made to `_html_stitcher.py`, `_svg_helpers.py`,
  `primitives/base.py`, `plane2d.py`, `tex/renderer.py`, or `parser/*` — scope
  fence held. `detect_changes()` shows unrelated concurrent edits to
  `primitives/base.py` and `tex/renderer.py` from other agents in this shared
  worktree; those are not part of this change and are not this task's
  responsibility.

## Deferred (out of scope for this task)

`\includegraphics alt=filename` — a separate, related accessible-name smell
(the `alt=` text defaults to the raw filename rather than natural language) —
was noted in the original investigation but is explicitly **not** addressed
here per the task's scope fence. It shares the same underlying policy
("accessible names must be natural language, never an internal
identifier-shaped string") and would be a natural follow-up once this fix is
reviewed and the 28 goldens are re-blessed.

---

## Sweep wave (wave 2)

Verification/closure sweep run by agent **sweep-title** on top of the wave-1
fix above. Confirms the accessible-name policy holds corpus-wide and closes
the three residual gaps wave-1 left open (conformance test, error guidance,
spec-text drift). No emitter code needed a new fix — see "Channels swept"
below.

### Channels swept

| Channel | Location | Verdict |
|---|---|---|
| SVG root `<title>` (all 4 HTML modes) | `_frame_renderer.py:_emit_frame_svg` | Already fixed (wave 1) |
| Filmstrip `<figure>` `aria-label` | `_html_stitcher.py:emit_animation_html` (~:251-258, 320-329) | Safe — `label or first-frame-label or "Animation"`, no id fallback |
| Diagram `<figure>` `aria-label` | `_html_stitcher.py:emit_diagram_html` (~:863) | Safe — omitted entirely when no `label=` |
| Interactive PLAYER `role="region"` `aria-label` | `_html_stitcher.py:emit_interactive_html` (~:694,730) | Safe — `label or "Animation"`, no id fallback. **Answers the open question: label-based, not id-based.** |
| Substory `<section>` `aria-label` | `_html_stitcher.py:emit_substory_html` (~:404-406) | Safe — author `title` defaults to the fixed literal `"Sub-computation"` (`ast.py:546`), never an id |
| "Print frame" narration swap | `_html_stitcher.py` (~:573-584) | Safe — pure string substitution reusing the already-fixed `svg_html`, not a second title-generation path |
| Annotation arrow `<title>`/`aria-description` | `_svg_helpers.py:emit_plain_arrow_svg`/`emit_arrow_svg` (~:2926-2997) | Safe by design — `arrow_from`/`target` are author-written selector strings ("Arrow from X to Y"), not internal slugs; already reviewed/excluded in the wave-1 artifact |
| Graph edge `<title>`/`aria-label` | `graph.py` (~:2294,2507,2517,2523) | Safe by design — `u`/`v` are author-supplied `nodes=[...]` ids, same structural-description pattern as arrows |
| Cursor annotation `aria-label` | `primitives/base.py` (~:883-916) | Safe — author cursor `id=` (or fixed literal `"c"` fallback); meant to be spoken, categorically different from an internal `scene_id` |
| Link/note annotation `aria-label` | `_frame_renderer.py` (~:1420,1654) | Safe — `label or "link"` / `display or "note"`, no id fallback |
| `aria-describedby` | n/a | Never emitted by any renderer; exists only as a sanitizer allowlist entry for pass-through of raw author HTML (`sanitize/whitelist.py:67`) |
| `<desc>` | n/a | Not emitted anywhere in `scriba/` |
| `figcaption` | n/a | Not emitted anywhere in `scriba/`; allowlist-only pass-through entry |
| `data-*` attributes | various | Out of scope per brief (not screen-reader-reachable as names) |
| MetricPlot / CodePanel | `primitives/metricplot.py`, `primitives/codepanel.py` | No own `aria-label`/`title`/`role="img"` emission — inherit the shared frame-level wrapping, already covered |
| "Embed" mode | n/a | Does not exist as a distinct emission mode in this codebase |

**Residuals found: none.** Every channel either already uses the safe
`label-or-generic-fallback` pattern (never an id) or carries legitimate
author-supplied structural content (arrow/edge endpoint ids, cursor ids) that
is categorically different from an internal `scene_id`/widget-id slug — no new
emitter fix was needed or made.

### Conformance test

Added `tests/conformance/test_r15_accessible_name_policy.py`
(`@pytest.mark.conformance`), walking the blessed golden corpus
(`tests/golden/examples/corpus/*.html`, 107 files) directly rather than
re-rendering fixtures:

- **R15-01** (`test_title_never_surfaces_internal_id`): no `<title>` text in a
  document equals any `data-scriba-scene` / `data-substory-id` / widget `id=`
  value collected from that same document.
- **R15-02** (`test_role_img_or_region_aria_label_traces_to_author_content`):
  no `aria-label` on a `role="img"` or `role="region"` element equals an
  internal id — covers the SVG root and the interactive PLAYER widget, the
  two literal `role="img"`/`"region"` emitters in the codebase.
- `test_corpus_is_non_empty`: guards against a silently-vacuous parametrize
  list (path drift, 0 params "passing" on nothing).

Result: **215 passed** (107 × 2 + 1) — the corpus is clean, zero flags. This
also resolved an open question from this sweep: the "28 goldens not yet
re-blessed" (wave-1's list) already contain the *fixed* rendered output on
disk — re-blessing is a pending human sign-off formality, not stale/buggy
content. Verified directly on `diagram.html`/`diagram.tex` (no `label=`, no
narration → correctly zero `<title>` and zero `aria-label` in the emitted
SVG/figure) and confirmed corpus-wide via a standalone probe script before
writing the test.

### Error guidance (E1050 / E1054)

Both were stale in a real, user-facing way: before wave-1 there was no path
to a natural-language diagram name at all, so "remove `\narrate`" / "switch
to `\begin{animation}`" were the *only* available advice. Post wave-1,
`label=` on `\begin{diagram}` reaches the SVG `<title>` directly, so a user
reaching for `\narrate` or `\step[title=...]` inside a diagram most likely
wanted exactly that. Updated:

- `scriba/animation/errors.py` — `ERROR_CATALOG["E1050"]` and `["E1054"]` now
  embed inline `Fix:` guidance pointing to `label=`, following the existing
  in-catalog `"... Fix: ..."` convention already used by `E1001`/`E1006`/
  `E1102` etc. (message text only — the `code="E1050"`/`"E1054"` raise sites
  in `renderer.py` and all error-code assertions in tests match on the code
  string, not this prose; confirmed via grep before editing).
- `docs/spec/error-codes.md` — the "Common Fix" cells for E1050/E1054 updated
  to match, each now naming `label=` and citing R-15.
- `mcp__gitnexus__impact` on `ERROR_CATALOG` (upstream): both candidate symbol
  nodes report `impactedCount: 0`, `risk: LOW` — confirmed low-risk before
  editing.
- Verified no regression: `tests/core/test_strict_mode.py` (E-code
  enumeration, code-only) and all `E1050`/`E1054`
  `pytest.raises(..., match="E1050"/"E1054")` assertions in
  `tests/animation/test_diagram_renderer.py` and
  `tests/unit/test_phase_b_diagram.py` match on the `code=` value, not this
  prose — unaffected.

### Spec-text sync (R-15)

`docs/spec/smart-label-ruleset.md:1024-1043` was confirmed **stale** against
the implemented policy in three ways, all fixed:

1. **Normative claim wrong.** "Each `<svg>` root MUST have a `<title>`..." was
   unconditional; the implemented rule is conditional on natural-language
   content existing, with explicit omission (never a `scene_id` fallback)
   otherwise. Rewritten as a two-clause MUST (title-when-content /
   omit-when-none) that names JudgeZone #10 directly.
2. **Scope wrong.** Said `_html_stitcher.py` (SVG root emission); the actual
   shared title builder lives in `_frame_renderer.py:_emit_frame_svg`, called
   from all four `_html_stitcher.py` emission modes. Corrected.
3. **Code ref / Test ref stale.** Code ref cited line 423 (drifted); corrected
   to the current title-source-selection (`:1856`) and conditional-emission
   (`:1911`) lines. Test ref cited only
   `test_frames_with_label_uses_frame_label`, which asserts on the *figure*
   `aria-label`, not the SVG `<title>` — added the two wave-1 tests that
   actually assert `<title>` content/omission
   (`test_frame_with_title_uses_it_as_svg_title`,
   `test_frame_without_title_or_narration_omits_svg_title`) plus this sweep's
   new corpus-wide conformance test.

A second, independently-discovered copy of the same drift was found and fixed
in **`docs/spec/svg-emitter.md:863-868`**, which explicitly documented the old
behavior ("title content is the scene's label text (**or `scene_id` as
fallback**)") — the literal pre-fix bug, still asserted as current behavior in
a live spec doc. Left as-is, the two specs would disagree about the same
rule; updated to match `smart-label-ruleset.md`'s corrected text, with its
line-423 citation corrected to the current location. (Not in the original
scope-fence file list, but same rule/same root cause as the in-scope fix, pure
prose, zero code risk — judged in-spirit of the "docs change explicitly
allowed for spec-accuracy" carve-out rather than scope creep.)

`investigations/sweep-spec-code-drift.md:129` also cites a now-stale R-15 line
number (`:521`) — left untouched: it is a dated point-in-time investigation
report, not living documentation, so an aging citation there is expected and
not a spec-accuracy defect.

### Verification

```
uv run pytest tests/unit/test_env_options_wired.py tests/unit/test_filmstrip_aria.py \
  tests/unit/test_step_title.py tests/conformance/test_r15_accessible_name_policy.py \
  -q -p no:cacheprovider
```
→ **243 passed.**

Broader sweep for regressions from the shared `errors.py` edit:
`uv run pytest tests/unit/ tests/conformance/ tests/animation/ tests/core/ -q`
→ **5067 passed, 9 skipped, 1 xfailed, 1 failed.** The one failure
(`test_primitive_css_centering.py::TestEveryReferencedClassHasCSS::test_all_scriba_classes_have_rules`,
missing CSS for `.scriba-plane-label-text`) traces to `plane2d.py` /
`scriba-plane2d.css`, neither of which this sweep touched — `git status`
shows both under concurrent modification by another agent (matches the JZ-13
label-textmode artifact filenames present in this shared worktree). Unrelated
to this task, not fixed here.

### Files touched (wave 2)

- `tests/conformance/test_r15_accessible_name_policy.py` (new)
- `scriba/animation/errors.py` (E1050/E1054 catalog text only)
- `docs/spec/error-codes.md` (E1050/E1054 Common Fix cells only)
- `docs/spec/smart-label-ruleset.md` (R-15 section only, :1024-1043 region)
- `docs/spec/svg-emitter.md` (R-15 citation only, :863-868 region)

No version bump, no CHANGELOG edit, no commit — per scope fence.

### Follow-up finding (unowned — flagged to team-lead)

`\includegraphics alt=filename` (the item wave-1 deferred, see "Deferred"
section above) was independently re-investigated by teammate **sweep-label**
during their own wave-2 sweep and handed back here. Their finding, confirmed
accurate: `scriba/tex/parser/images.py:_parse_options` has no `alt=` option
key at all (only `scale`/`width`/`height`), so `apply_includegraphics` always
emits `alt="{html.escape(filename)}"` — the accessible name is unconditionally
the raw filename, never author text, and can never be omitted. Textbook JZ-10
signature.

Unlike the four channels fixed in this sweep, this is **not** a cheap,
in-family tack-on for either agent that looked at it:

- It's a **documented contract**, not an oversight — `docs/guides/tex-plugin.md`
  §3's HTML-output table pins `alt="fig.png"` explicitly.
- Two snapshot tests (`includegraphics_with_scale`,
  `includegraphics_with_width_cm` in `tests/tex/test_tex_snapshots.py`) and
  one XSS test (`tests/tex/test_tex_xss.py:26`, whose docstring narrative
  relies on the filename landing in `alt` for its escaping check) all assert
  the current behavior — a real fix means contract-doc sync *and* snapshot
  regen, not a text-only change.
- It doesn't fit sweep-label's JZ-13 family either (measure≠paint≠announce
  divergence) — it's a single-consumer bad-accessible-name-choice smell,
  which makes it R-15/JZ-10-shaped, but bigger in blast radius than this
  task's scope fence (new `alt=` option key, parser changes, doc + snapshot
  updates) was authorized for.

Neither sweep-label nor sweep-title has implemented a fix. Logged here so
it isn't silently dropped by both sweeps — needs an explicit ownership/scope
decision (new task) from team-lead, not a unilateral pickup.
