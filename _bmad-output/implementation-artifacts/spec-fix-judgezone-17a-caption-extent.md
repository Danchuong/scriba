# Spec-Fix: JudgeZone #17 Finding A — Stack Caption Bottom-Edge Double-Count

**Agent:** bmad-17a-extent
**Status:** DONE — fix GREEN, regression swept, zero golden corpus deltas identified.
**Investigation doc:** `_bmad-output/implementation-artifacts/investigations/judgezone-17a-stack-caption-extent-investigation.md`
**Sibling:** JudgeZone #15 (`spec-fix-judgezone-15-top-band-reservation.md`) — the
TOP-caption counterpart of this exact bug family, already fixed for
tree/forest/graph via `_top_band_layout()`. This fix is the bottom-caption
counterpart, confined to `Stack` (six of seven sibling primitives already
carry the equivalent fix; see investigation doc's precedent matrix).

## Contract

Whenever a `Stack` emits a caption **and** `_reserved_arrow_above() > 0`
(any annotation reserving space above the content frame), the caption's
painted bottom edge must land at or before the declared `bounding_box().height`
— never `arrow_above` px past it. `top_y` must be computed as:

```
top_y = bbox.height - caption_block_height - arrow_above
```

matching the already-established convention in `bar.py`, `hashmap.py`,
`hypercube.py`, `linkedlist.py`, `queue.py`, and `variablewatch.py`. When
`arrow_above == 0` (no such annotation), this is a byte-identical no-op —
zero behavior change for the common case.

## GitNexus impact analysis (pre-edit, mandatory)

Repo index was stale on first attempt (`impact`/`context` returned "not
found" for every `stack.py` symbol despite other files resolving fine;
`list_repos` showed `commitsBehind: 2`). Fixed via `node .gitnexus/run.cjs
analyze` (forced full rebuild — "Previous analyze run did not complete
cleanly"), 155.5s. Post-reindex:

```
impact(target="Stack.emit_svg", direction="upstream")
  -> uid: Method:scriba/animation/primitives/stack.py:Stack.emit_svg#3
  -> risk: LOW, impactedCount: 0
```

LOW risk, zero upstream callers outside the primitive's own render path —
cleared to edit.

## The fix — `scriba/animation/primitives/stack.py`

Single hunk, lines 432–450 (`emit_svg`'s caption-emission call). Diff:

```diff
+            # minus arrow_above: the caption is emitted INSIDE the
+            # translate(_, arrow_above) group, so anchoring at raw
+            # bbox.height painted it arrow_above px PAST the bbox
+            # bottom, eating the inter-primitive gap.
             self._emit_caption(
                 parts,
                 content_width=content_w,
                 footprint_width=int(bbox.width),
-                top_y=int(bbox.height - self._caption_block_height(content_w)),
+                top_y=int(
+                    bbox.height
+                    - self._caption_block_height(content_w)
+                    - arrow_above
+                ),
                 render_inline_tex=render_inline_tex,
             )
```

`arrow_above` reuses the local variable already computed at `emit_svg` line
334 (`arrow_above = self._reserved_arrow_above()`) — no new call, no new
state. Comment text mirrors `hashmap.py`/`linkedlist.py` verbatim (established
house convention for this fix family). `bounding_box()` is **not** touched —
it already included `arrow_above` correctly; only the caption's local
coordinate needed correcting to match the space it's emitted into. +9/-1
lines, single file.

## Tests: RED → GREEN

New test in `tests/unit/test_primitive_stack.py` (`TestAnnotationLayout`,
after `test_unannotated_bbox_unchanged_horizontal`):
`test_caption_stays_inside_bbox_with_arrow_above`. Constructs a `Stack` with a
long (wrapping) caption and a `position="above"` annotation, parses the
rendered SVG's `translate(_, arrow_above)` shift and the caption `<text>`/
`<tspan dy=...>` chain to compute the caption's true absolute bottom
(including `DESCENDER_RATIO` font-metric allowance, `layout.py`), and asserts
it does not exceed `bounding_box().height` (+1.0 tolerance).

RED (pre-fix):

```
caption bottom 207.2 escapes bbox height 189.0 (arrow_above=18)
```

GREEN (post-fix): full file —

```
35 passed in 0.91s
```

## Regression sweep

Full `test_primitive_stack.py` (own scope): **35 passed**.

Broader caption/annotation/cursor regression sweep (below-band lanes,
caption-within-bbox, pill-within-bbox, multicursor, phase-B stack edges,
obstacle protocol, annotation renders):

```
206 passed, 8 skipped
```

Full non-golden suite (`tests/`, excluding `tests/golden/` and three
pre-existing, unrelated `hypothesis`-dependent modules missing that optional
dependency in this environment — `tests/property/test_label_one_interpretation.py`,
`tests/property/test_smart_label_determinism.py`, `tests/unit/test_graph_mutation.py`,
`tests/unit/test_parser_hypothesis.py`):

```
1 failed, 5953 passed, 16 skipped, 1 xfailed
```

The 1 failure (`tests/unit/test_starlark_security.py::TestRecursionErrorNoPathLeak::
test_deeply_nested_expression_no_path_leak_via_worker`) is confirmed
pre-existing and unrelated: reproduces identically (`assert True is False`, a
Python-recursion-limit-detection sensitivity, not a caption/rendering
assertion) on a `git stash`-clean checkout with none of this fix's changes
present.

`detect_changes(scope=compare, base_ref=main, repo=scriba)`:

```json
{"summary": {"changed_count": 2, "affected_count": 0, "changed_files": 3, "risk_level": "low"},
 "changed_symbols": [
   {"id": "Class:scriba/animation/primitives/stack.py:Stack", "change_type": "touched"},
   {"id": "Method:scriba/animation/primitives/stack.py:Stack.emit_svg#3", "change_type": "touched"}],
 "affected_processes": []}
```

Exactly the two expected symbols, `risk_level: low`, zero affected processes.
(`changed_files: 3` includes the test file, which carries no indexed
"symbol" entry of its own.)

## Golden corpus impact: zero fixtures shift, disambiguated from concurrent work

`pytest tests/golden/ -q -k "stack"` initially showed 2 FAILED
(`04_stack_shrink`, `stack`). The diff content was exclusively CSS
custom-property substitution (`--scriba-pill-offset`, `--scriba-pill-pad-y`,
`--scriba-pill-border`, `--scriba-pill-btn`, etc., replacing hardcoded pixel/
rem values in `.scriba-stage-wrap`/`.scriba-controls`) — the concurrent
`bmad-17b-chrome` agent's in-progress `scriba-embed.css` work for JudgeZone
#17 Finding B, confirmed present in the working tree via `git status`
(`scriba-embed.css` modified, `tests/unit/test_controls_clearance_css.py`
untracked — neither owned or touched by this investigation).

Disambiguated by isolation:

1. `git stash` (all tracked changes, both agents') → both goldens **pass**
   (2 passed) — confirms both goldens are clean on `main`.
2. `git stash push -- scriba/animation/static/scriba-embed.css` (revert
   **only** the concurrent agent's CSS file, leaving this fix's `stack.py`/
   test changes in place) → both goldens **pass** (2 passed) — confirms this
   fix, in isolation, produces **zero** diff against either golden fixture.

**Zero goldens require re-blessing; none were re-blessed.** The earlier
2-failure signal was entirely attributable to the concurrent agent's CSS
work, not this fix.

## Regression risks

- The fix is additive-only inside an existing conditional branch
  (`if self.label is not None:`); it changes output only when
  `arrow_above > 0` for a captioned Stack — confirmed a no-op otherwise via
  both the golden-isolation check above and the cross-frame no-annotation
  control render in the investigation doc (byte-identical across all 16
  caption occurrences).
- `bounding_box()` was deliberately left untouched — the declared viewBox
  height was already correct; only the caption's local paint coordinate
  needed correcting. No risk of the cross-frame timeline-max prescan
  reserving a different (larger/smaller) height than before.
- No version bump, no CHANGELOG edit, no commit, no golden re-bless
  performed — per mandate.
