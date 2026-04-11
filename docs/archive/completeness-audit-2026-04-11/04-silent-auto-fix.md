# Completeness Audit 04 — Silent Auto-Fix Inventory

**Agent**: 4/14
**Scope**: Scriba v0.5.1 (HEAD `eb4f017`)
**Mode**: Read-only
**Trigger evidence**: During convex-hull compile, Scriba emits
`[E1462] polygon not closed — auto-closing` via `logger.warning` and
silently rewrites the author's polygon. Authors never see this unless
they tail logs.

## Scope

Find every site in `scriba/` where user intent is silently rewritten,
clamped, coerced, or dropped. For each site, classify severity, decide
whether it should be promoted to a strict `ScribaError` (with opt-in
override) or surfaced in a render report, and propose a remediation.

Patterns searched: `auto`, `clamp/clamping`, `silently`, `default to`,
`fall back`, `coerce`, `truncate`, `ignore` (for user input).

## Silent auto-fix inventory

### SF-1 — Polygon auto-close (E1462)
`scriba/animation/primitives/plane2d.py:247-254`

```python
if len(pts) >= 2 and pts[0] != pts[-1]:
    logger.warning("[E1462] polygon not closed — auto-closing")
self.polygons.append({"points": pts})
```

*What*: Author passes an open point list to `add_polygon`. Scriba logs a
warning and appends the open list unchanged; the SVG `<polygon>` element
visually closes the shape so the author sees a closed polygon they never
wrote.

*When*: Every `\apply{add_polygon=...}` and every initial
`\shape Plane2D{polygons=[...]}` where `pts[0] != pts[-1]`.

*Classification*: **DANGEROUS**. Author meaning is lost in two ways:
(a) the warning never reaches the author (plain `logger.warning`, no
render report), and (b) the comment at line 577 (`Auto-close: SVG
<polygon> auto-closes`) shows Scriba is **relying** on SVG-native
closing rather than explicitly appending `pts[0]` to `pts`, which means
the internal `polygons[i].points` list disagrees with the rendered
shape — selectors like `polygon[i].points[last]` would be off-by-one.

### SF-2 — Point outside viewport (E1463)
`scriba/animation/primitives/plane2d.py:197-199`

```python
if not (self.xrange[0] <= x <= self.xrange[1] and
        self.yrange[0] <= y <= self.yrange[1]):
    logger.warning("[E1463] point (%.2f, %.2f) is outside viewport", x, y)
self.points.append({...})
```

*What*: Point outside the declared viewport is logged and kept. SVG
clips it invisibly.

*Classification*: **HIDDEN**. Warning goes only to the log; author sees
an empty plane and no rendered marker. Not dangerous in the same way as
SF-1 (no rewrite of the value) but invisible.

### SF-3 — Degenerate line dropped (E1461)
`scriba/animation/primitives/plane2d.py:210-212`

```python
if abs(a) < 1e-12 and abs(b) < 1e-12:
    logger.warning("[E1461] degenerate line (a=0, b=0)")
    return
```

*What*: An `a*x + b*y = c` line with zero coefficients is dropped.
Subsequent element indices (`line[i]`, `line[i+1]`, ...) shift by one.

*Classification*: **DANGEROUS**. Drop is silent from the author's view,
*and* index shift corrupts every later selector that references a line
by position. The same pattern repeats in `_emit_lines` at lines 529 and
534 for off-viewport lines — those use `continue`, so a line that
parsed fine at `add_line` time disappears at emit time without any
index update or author-visible signal.

### SF-4 — Log-scale zero/negative clamp (E1484)
`scriba/animation/primitives/metricplot.py:589-596`

```python
if val <= 0:
    logger.warning("[E1484] log scale: non-positive value %s in series %r "
                   "clamped to 1e-9", val, series.name)
    val = 1e-9
```

*What*: Authoring `scale="log"` with a zero or negative datum silently
substitutes `1e-9`. The plotted curve dips to an arbitrary constant.

*Classification*: **DANGEROUS**. A pedagogical plot that tries to show
"value reached zero" now shows "value reached 1e-9" with no indication
to the reader. The author almost certainly wanted either linear scale
or an explicit domain break.

### SF-5 — layout_lambda clamp (E1504)
`scriba/animation/primitives/graph_layout_stable.py:181-188`

```python
if lambda_weight < _LAMBDA_MIN or lambda_weight > _LAMBDA_MAX:
    logger.warning("E1504: layout_lambda=%.4f outside [%.2f, %.2f], clamping",
                   lambda_weight, _LAMBDA_MIN, _LAMBDA_MAX)
    lambda_weight = max(_LAMBDA_MIN, min(_LAMBDA_MAX, lambda_weight))
```

*What*: Out-of-range `layout_lambda` is clamped to `[0.01, 10]`.

*Classification*: **HIDDEN**. The parameter is a knob, not semantic
content — clamping is defensible, but the warning is invisible.

### SF-6 — Stable-layout fallback to force layout (E1501/E1502/E1503)
`scriba/animation/primitives/graph_layout_stable.py:191-206`

```python
if len(nodes) > _MAX_NODES:
    logger.warning("E1501: %d nodes exceeds limit of %d", len(nodes), _MAX_NODES)
    logger.warning("E1503: falling back to force layout")
    return None
```

*What*: >20 nodes or >50 frames silently downgrades the requested
stable layout to force-directed layout. The author asked for a stable
layout specifically to keep node positions consistent across frames;
force layout cannot guarantee that.

*Classification*: **DANGEROUS**. Author intent (stability) is lost
invisibly. A stable-layout request is semantic, not cosmetic.

### SF-7 — Queue pointer clamp on empty queue
`scriba/animation/primitives/queue.py:263-264, 331-332`

```python
rear_display = max(self.rear_idx - 1, 0)
# ...
idx = max(0, min(index, self.capacity - 1))
```

*What*: Empty queue draws front/rear pointer at cell 0 instead of not
drawing it at all.

*Classification*: **ACCEPTABLE**. Defensive rendering to avoid a
negative array index; the semantic (empty vs. one-element) is still
visible because cells show as empty.

### SF-8 — Stray `\end{animation}` silently ignored
`scriba/animation/detector.py:93-95`

```python
elif kind == "end":
    if open_start is None:
        # Stray \end{animation} — silently ignore (no matching open).
        continue
```

*What*: A stray `\end{animation}` without a matching `\begin` is
dropped without error.

*Classification*: **DANGEROUS**. The author almost certainly has
mismatched braces or a typo; dropping the token can cascade into
far-downstream parse errors that look unrelated. The unclosed-`\begin`
path already raises `UnclosedAnimationError` (E1001), so asymmetry is
unjustified.

### SF-9 — Substory prelude silently drops `\highlight`/`\apply`/`\recolor`
`scriba/animation/parser/grammar.py:1254-1273`

```python
elif inner_cmd == "highlight":
    cmd = self._parse_highlight()
    if sub_in_prelude:
        pass  # ignore in substory prelude
    else:
        sub_frame_commands.append(cmd)
# (same for apply, recolor)
```

*What*: When an author writes `\highlight`, `\apply`, or `\recolor`
inside a `\substory` block *before* the first `\step`, the parsed
command is silently discarded with no warning, no E-code, no diagnostic.

*Classification*: **DANGEROUS**. The author's state change vanishes
without a trace. Contrast with E1053 which does raise for `\highlight`
in the top-level prelude — substory prelude deserves the same
treatment.

### SF-10 — Compute-bindings best-effort swallow
`scriba/animation/parser/grammar.py:555-558`

```python
try:
    self._collect_compute_bindings(body)
except Exception:  # noqa: BLE001 — best effort, never fail parse
    pass
```

*What*: Any exception while pre-scanning Starlark assignments is
swallowed. Feeds the interpolation symbol-table, not runtime execution.

*Classification*: **ACCEPTABLE**. The docstring is explicit that false
negatives are preferable to false positives, and the runtime Starlark
evaluator is authoritative. Keep as-is.

### SF-11 — Plane2D `_check_cap` converted to hard error (E1466)
`scriba/animation/primitives/plane2d.py:171-184`

The comment explicitly records "Converts the previous soft-drop
behaviour to a hard limit so users see data loss instead of silently
receiving a truncated plane." This is the *correct* shape for all the
other sites in this audit. **No action — reference model.**

### SF-12 — MetricPlot cell cap raises (E1483)
`scriba/animation/primitives/metricplot.py:99-102` documents the same
pattern: "this limit raises rather than silently truncating, so authors
see the error". Reference model.

### SF-13 — Pygments highlight: explicit language mismatch returns `None`
`scriba/tex/highlight.py:103-111`

Quoted: *"Explicit language: trust it. If it doesn't resolve, fall back
to plain — do NOT silently rewrite to a guessed lexer, the author asked
for something specific."* Reference model, no action.

### SF-14 — Emitter selector-mismatch warning-only
`scriba/animation/emitter.py:312-342`

```python
if not valid:
    warnings.warn(
        f"selector '{target_key}' does not match any "
        f"addressable part of '{shape_name}'"
    )
```

*What*: A typo'd or stale selector (e.g. `a.cell[99]` when `a` has 10
cells) emits a `UserWarning` and the emitter continues, rendering the
frame with the selector silently absent.

*Classification*: **HIDDEN**. The docstring's justification ("avoids
breaking existing animations with harmless stale selectors") is a
legacy-compat call, but authors writing new content see nothing if
their tests don't unsilence warnings.

## Classification table

| ID     | Site                                    | Severity    | Current surfacing        |
|--------|-----------------------------------------|-------------|--------------------------|
| SF-1   | Polygon auto-close (E1462)              | DANGEROUS   | `logger.warning`         |
| SF-2   | Point outside viewport (E1463)          | HIDDEN      | `logger.warning`         |
| SF-3   | Degenerate / off-viewport line (E1461)  | DANGEROUS   | `logger.warning`         |
| SF-4   | Log-scale non-positive clamp (E1484)    | DANGEROUS   | `logger.warning`         |
| SF-5   | `layout_lambda` clamp (E1504)           | HIDDEN      | `logger.warning`         |
| SF-6   | Stable-layout force fallback (E1501-03) | DANGEROUS   | `logger.warning`         |
| SF-7   | Queue pointer clamp on empty            | ACCEPTABLE  | code comment only        |
| SF-8   | Stray `\end{animation}` dropped         | DANGEROUS   | code comment only        |
| SF-9   | Substory-prelude command drop           | DANGEROUS   | code comment only        |
| SF-10  | Compute-bindings best-effort            | ACCEPTABLE  | code comment only        |
| SF-11  | Plane2D element cap (E1466)             | REFERENCE   | raises `AnimationError`  |
| SF-12  | MetricPlot point cap (E1483)            | REFERENCE   | raises `AnimationError`  |
| SF-13  | Pygments lang mismatch                  | REFERENCE   | returns None, no rewrite |
| SF-14  | Emitter selector mismatch               | HIDDEN      | `warnings.warn`          |

### E-codes in the catalog but never raised as errors

Cross-reference with `scriba/animation/errors.py`:

- **E1461, E1462, E1463, E1466** — Plane2D codes. E1466 *is* raised;
  E1461/E1462/E1463 are documented in the catalog as "currently surface
  only as logger warnings from the Plane2D draw pipeline. Retained in
  catalog as the documented contract once strict mode is wired" (lines
  251-253). The strict-mode wiring does not yet exist — dead contract.
- **E1484** — MetricPlot log-clamp. `logger.warning` only.
- **E1500, E1501, E1502, E1503, E1504** — graph layout. Docstring at
  lines 273-276 confirms these surface only as logger warnings. E1505
  (negative seed) *is* raised.
- **E1180 (FrameCountWarning)** — `UserWarning`, not `ScribaError`.
  Visibility only if the consumer has not silenced `UserWarning`
  globally. Catalog comment explicitly flags Wave 3 follow-up to
  promote it to a `warnings_collector` on `RenderContext` (errors.py
  lines 397-405). **That `warnings_collector` does not yet exist in
  the codebase** (grep returns no matches).

## Recommendations per site

### Promote to strict `AnimationError` (with opt-in `strict=False` override)

- **SF-1 (E1462)**: Raise by default. The render context already has a
  `strict` / `lax` distinction for CLI consumers; add `strict_plane2d`
  or piggyback on existing flag. If `strict=False`, *explicitly* append
  `pts[0]` to `pts` so internal state matches the rendered shape
  (today's implementation relies on SVG-native closing and leaves the
  internal list open — that's a separate correctness bug that cascades
  into selector indexing).
- **SF-3 (E1461)**: Raise by default for degenerate lines. For
  off-viewport lines in `_emit_lines`, either raise or keep the line in
  the primitive list and emit an invisible placeholder so index
  positions stay stable.
- **SF-4 (E1484)**: Raise by default. The fix-up of `val = 1e-9` is
  never the right behavior for a pedagogical animation; the author
  should have used a different scale or pre-transformed the data.
- **SF-6 (E1501/E1502/E1503)**: Raise by default. Author asked for a
  stable layout; silently handing them force layout breaks the reason
  they asked. Under `strict=False`, keep current behavior *and* stamp
  `render_metadata.layout = "force-fallback"` so downstream tooling
  can inspect.
- **SF-8 (detector stray end)**: Raise `UnmatchedEndError` with its own
  code in the E1001-E1099 block. Mirrors `UnclosedAnimationError`
  symmetrically.
- **SF-9 (substory prelude drop)**: Raise E1053 (or a new E1057
  "substory prelude: `\highlight`/`\apply`/`\recolor` not allowed") at
  parse time. No `strict=False` — this is pure author error.

### Keep silent but surface in a render report

Tracked cost: introduce a `RenderReport` / `warnings_collector` on
`RenderContext`. The `FrameCountWarning` catalog comment already
anticipates this — Wave 3 follow-up.

- **SF-2 (E1463)**, **SF-5 (E1504)**, **SF-14 (emitter selector
  mismatch)**: append a structured entry to the render report and
  expose on the CLI. These don't need to block the render, but they
  must not vanish into a logger the author never sees.

### Keep as-is with justification

- **SF-7** (queue empty pointer clamp) — defensive, no meaning is lost.
- **SF-10** (compute bindings best-effort) — documented non-authoritative
  pre-scan; runtime Starlark is the source of truth.
- **SF-11, SF-12, SF-13** — reference models; these are the shape the
  rest of the codebase should converge on.

## Severity summary

| Severity    | Count | Sites                                 |
|-------------|-------|---------------------------------------|
| DANGEROUS   | 6     | SF-1, SF-3, SF-4, SF-6, SF-8, SF-9    |
| HIDDEN      | 3     | SF-2, SF-5, SF-14                     |
| ACCEPTABLE  | 2     | SF-7, SF-10                           |
| REFERENCE   | 3     | SF-11, SF-12, SF-13                   |

**Top recommendation**: build the `warnings_collector` /
`render_report` surface on `RenderContext` that the errors.py catalog
comments already describe. Once that surface exists, SF-1, SF-3, SF-4,
SF-6, SF-8, SF-9 can be promoted to strict errors (with `strict=False`
diverting to the collector), and SF-2, SF-5, SF-14 can be kept
lax-by-default while still being visible to authors. Six of nine
non-trivial silent-fix sites disappear in one coordinated change.

**Dead contract**: E1461, E1462, E1463, E1466(partial), E1484, E1500,
E1501, E1502, E1503, E1504 all live in the catalog as "documented
contract for when strict mode is wired." Wiring strict mode is the
work this recommendation points at; until then, the catalog is
aspirational for half of the 1460-1509 block.
