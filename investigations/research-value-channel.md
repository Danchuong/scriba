# Research — Value-Channel Dishonesty: the two deferred sub-findings

**Scope:** the two sub-findings deferred from `investigations/design-value-flipback.md`
(PART 1, rows 83–86; §PART 1 closing bullets). The 0.26.x `renders_value` gate
(`_frame_renderer.py:99 _validate_value_channels`, `base.py:408 renders_value`)
closed the value-**less** part class (Stack/NumberLine/CodePanel/Graph-node → E1105).
It does **not** touch either sub-finding below — both slip through because
`renders_value` returns its default `True` for Bar, Matrix, Plane2D, and MetricPlot.

**Read-only research case. No implementation.** Evidence-graded.

**Evidence grades:** Confirmed = cite `path:line` + rendered SVG / extracted `tr`
manifest • Deduced = code-path reasoning • Hypothesized = plausible, unproven.

**Method:** `.venv/bin/python render.py <probe>.tex -o _p.html`; extract each frame's
`tr:[…],fs:N` manifest and scan server-SVG text-nodes for the value token; probes in
scratchpad (`p1_bar`, `p2_matrix`, `p3_metricplot`, `p4a_plane_inrange`,
`p4b_plane_oob`, `p5_bar_novals`, `p6_bar_numdelta`, `p7_array`). All `_*.html`
cleaned up.

---

## Shared root cause (Confirmed — carried over, re-verified)

`\apply{X}{value=V}` splits into two independent paths that can disagree:

1. **Differ path.** `scene._apply_apply` records `value=str(V)` into `shape_states`
   **unconditionally** (`scene.py:978-1015`, esp. `:1008-1015`). Neither
   `_resolve_selector` nor `_ensure_target` consults the primitive's
   `validate_selector` or its numeric contract. The differ turns any recorded value
   delta into a `value_change` Transition (`differ.py:140-149` new-cell,
   `differ.py:223-234` both-exist) — **kind-agnostic, primitive-blind.**
2. **Render path.** A best-effort pre-pass calls `set_value` wrapped in
   `try/except: pass` (`_frame_renderer.py:209-212`); whether it surfaces depends on
   the primitive's `emit_svg`.

When path 2 drops the value (soft-drop) but path 1 still fires, the manifest carries a
`value_change` the server SVG never honored. At runtime
(`scriba.js:163-189`): `el2 = stage.querySelector(sel)`; if the element exists, stamp
`toVal` into `[data-role="value"]` else the **last `<text>`** in the group
(`:176-177`); then the `fs:1` snapshot replaces `innerHTML` with the server SVG →
revert. **Visible flip-back requires (a) a DOM element for the target AND (b) a
`<text>` inside its group.** Absent either, the runtime is a no-op and the dishonesty
is manifest-only.

The pre-differ ordering that any fix must respect is Confirmed:
`_prescan_value_widths` (→ `_validate_value_channels`) runs at
`_html_stitcher.py:229` **before** `compute_transitions` at `_html_stitcher.py:652`.

---

## SUB-FINDING 1 — non-numeric `value=` on Bar / Matrix — **CONFIRMED (visible when `show_values`)**

### Verdict
Bar and Matrix render `value=` **only when numeric**; a non-numeric value soft-drops in
`emit_svg`, but the differ still emits a `value_change` carrying the raw string. When
`show_values=true` the runtime stamps the string into the value/datum `<text>` and the
`fs` snapshot reverts it → **a genuine, visible flip-back on author-error input.** When
`show_values` is off, the same dishonest `value_change` is emitted but there is no
`<text>` to stamp → manifest-only.

### Evidence (Confirmed)

| Probe | server SVG honors value? | manifest `tr` (fs) | stampable `<text>` in group? | flip-back |
|---|---|---|---|---|
| `p1_bar` `h.bar[1] value=ZZZ`, `show_values=true` | **NO** — `ZZZ` 0/text-nodes; bar keeps height | `[["h.bar[1]","value",null,"ZZZ","value_change"]]` fs:1 | **YES** — `<text …>1</text>` inside `<g data-target="h.bar[1]">` | **YES** |
| `p2_matrix` `m.cell[0][0] value=ZZZ`, `show_values=true` | **NO** — cell keeps datum `0.1`/fill | `[["m.cell[0][0]","value",null,"ZZZ","value_change"]]` fs:1 | **YES** — `<text …>0.1</text>` inside cell `<g>` | **YES** |
| `p5_bar_novals` same, `show_values` off | NO | `[["h.bar[1]","value",null,"ZZZ","value_change"]]` fs:1 | **NO** — group is `<rect>`-only | no (manifest-only) |
| `p6_bar_numdelta` `h.bar[0] value=8` (numeric delta) | **YES** — frame1 height 124.44 + `<text>8</text>` vs frame0 46.67/`3` | `[["h.bar[0]","value",null,"8","value_change"]]` fs:1 | YES | **no — honest** (stamp == snapshot) |
| `p7_array` `a.cell[0] value=ZZZ` (control) | **YES** — Array renders `ZZZ` as text | honest `value_change` | YES | no — Array is a string container, not type-checked |

The numeric vs non-numeric contrast is the crux: `p6` proves the numeric path is honest
end-to-end (server renders `8` as both height and label, so the stamp matches the snapshot
→ no revert); `p1`/`p2` prove the non-numeric path bakes a `value_change` the server drops.

### Code seam (Confirmed)
- Bar soft-drop: `bar.py:236-240` — `try: v = float(value) except (TypeError, ValueError): return`.
- Matrix soft-drop: `matrix.py:538-542` — `try: val = float(override) except (TypeError, ValueError): val = self.data[r][c]`.
- Value rendered as a stampable `<text>` only under `show_values`:
  `bar.py:392-408` (comment: *"the first `<text>` in the group, so value_change's
  pulse/stamp lands on it"*), `matrix.py:573-591`.
- Numeric-value-only parts (value channel): **Bar `bar[i]`, Matrix `cell[r][c]`.**
  Graph *edge* value is also `float()`-d (`graph.py:1341`) but is the documented,
  honoring edge-weight path (out of scope). **MetricPlot is NOT here** — its numeric
  series values are fed by series-keys (`\apply{plot}{cost=10}`, `metricplot.py:282`),
  not by `value=` on an addressable part; a `value=` on MetricPlot has no valid target
  (see Sub-finding 2). So the numeric-value-only value-channel set is exactly {Bar, Matrix}.

### Fix decision — **REJECT at author time with `E1107` (spec-mandated, currently unimplemented)**

`E1107` "Value type mismatch" is **already specified** with this exact case —
`docs/spec/environments.md:201`: *"`E1107` type mismatch (e.g., `value=` with a
non-numeric on an `Array` declared numeric)"*; also `docs/spec/primitives.md:82,86`,
`scene-ir.md:194`. But it is **defined nowhere in `errors.py` and raised nowhere in
`scriba/`** (Confirmed: zero code hits, zero tests). `errors.py:190` is `E1104`
(structural-shape mismatch), a different axis. So this fix *implements a documented-but-
dormant error code*, not a new invention.

- **Reject, not coerce.** Bar heights / Matrix colours are intrinsically numeric — there
  is no string-display mode to coerce *into*. Bar even validates its `data` numeric at
  construction (`errors.py:584,592`). So a non-numeric `value=` is unconditionally an
  error (no per-instance "declared numeric" flag needed, unlike the spec's Array example).
- **Where.** A pre-differ predicate (sibling to `_validate_value_channels`, same
  `_prescan_value_widths` seam, `:171`). It must **not** live inside `set_value` — the
  prescan wraps `set_value` in `try/except: pass` (`:209-212`) and would swallow the
  raise (identical constraint to the E1105 gate, prior doc §"Structural mechanism" pt 2).
  Keep `set_value`'s soft-drop as a defensive backstop so the primitive-unit test
  `test_matrix_value_apply.py:82 test_non_numeric_value_keeps_datum` stays green.
- **Mechanism.** Add a capability e.g. `value_must_be_numeric(suffix) -> bool`
  (default `False`; `True` for Bar `bar[i]`, Matrix `cell[r][c]`), mirroring the
  `renders_value` shape. In the pre-differ pass, for each recorded value where the
  predicate holds and `float(value)` fails → `raise _animation_error("E1107", …,
  hint="Bar column heights are numeric; value= must be a number")`.

### Golden / version impact (Confirmed)
- **Zero** corpus `.tex` applies `value=` to Bar or Matrix. Every hit is in `docs/*.md`
  and numeric (`SCRIBA-TEX-REFERENCE.md:1591 value=9`, `bar.md:63 value=9`,
  `graph-stable-layout.md:387 value=1`). Corpus grep empty for the offending pattern.
- **No golden re-bless. `SCRIBA_VERSION` stays 22** — build-time error path, nothing
  baked into HTML; exactly the 0.26.2 precedent (`_version.py:278-291`: error-path
  guards that "only fire on input that was ALREADY broken" ⇒ no bump, byte-identical
  corpus). Add `E1107` to the `errors.py` registry (docstring narrative).
- **Test churn:** keep the primitive soft-drop test; **add** RED integration tests
  (render raises E1107 for `h.bar[i]`/`m.cell[r][c]` non-numeric; and a non-regression:
  numeric `value=` still renders + honest `value_change`).

### RED sketch
```python
def test_bar_nonnumeric_value_raises_e1107():
    tex = (r"\begin{animation}[id=b]\shape{h}{Bar}{data=[3,1,4], show_values=true}"
           r"\step\apply{h.bar[0]}{value=ZZZ}\narrate{x}\end{animation}")
    with pytest.raises(ScribaError) as e:   # RED today: renders, bakes value_change
        render_string(tex)
    assert e.value.code == "E1107" and "numeric" in e.value.hint.lower()

def test_bar_numeric_value_still_renders():         # regression fence
    # value=8 → server SVG shows height+label 8, honest value_change, no raise
    ...
```

---

## SUB-FINDING 2 — spurious `value_change` on E1115-invalid selectors — **CONFIRMED, NOT visible**

### Verdict
A `value=` on a selector that `validate_selector` rejects (E1115 soft-drop) is still
recorded by the scene and emitted by the differ as a `value_change` for a target with
**no DOM element**. Runtime `stage.querySelector(sel)` returns null → the whole handler
no-ops → **no visible flash, ever.** Pure manifest dishonesty; it also violates the
E1115 "soft-drop = no output change" promise (`bar.md:54`) in the manifest layer.

### Evidence (Confirmed)

| Probe | selector status | manifest `tr` (fs) | `data-target` DOM elements | runtime |
|---|---|---|---|---|
| `p3_metricplot` `plot.point[0] value=5` | **invalid always** (`metricplot.py:800-801`: only name/`all`) — E1115 ×4 | `[["plot.point[0]","value",null,"5","value_change"]]` fs:1 | **0** | no-op → no flash |
| `p4b_plane_oob` `p.point[9] value=ZZZ` | **invalid** (out-of-range) — E1115 ×4 | `[["p.point[9]","value",null,"ZZZ","value_change"]]` fs:1 | **0** | no-op → no flash |

The E1115 warnings fire from `_frame_renderer.py:210` (prescan `set_value`), `:780`
(`_validate_expanded_selectors`), `:1685`/`:1690` (per-frame set_state/set_value) —
i.e. the selector is rejected at **every** layer, yet the value still reaches the differ.

### Code seam (Confirmed — WHY)
`scene._apply_apply` records value unconditionally (`scene.py:1008-1015`); the differ is
primitive-blind (`differ.py:140-149`). The existing selector-validation pass
`_validate_expanded_selectors` (`_frame_renderer.py:741`, warn at `:780`) only **warns** —
it never strips the value from `shape_states`, so the differ still sees it.

### Fix decision — **GATE by dropping the value-record for invalid selectors (low priority)**
- **Drop, not raise.** The established E1115 contract is *soft-drop / warn / no output
  change*. Escalating an invalid selector to a hard error would change that contract and
  could break docs that tolerate soft-drops. The honest completion is to make the
  soft-drop reach the manifest: in the pre-differ pass, when `not validate_selector(suffix)`
  for a value-bearing target, **remove that value entry** so no `value_change` emits.
  Natural home: extend `_validate_expanded_selectors` (which already detects the case) or
  the `_prescan_value_widths` loop — both pre-differ.
- **Worth it?** Marginal. **No visible symptom.** It is manifest hygiene + contract
  consistency, not a bug fix. **"Leave as note" is defensible** if churn-averse; if taken,
  it is a small, low-risk drop.

### Golden / version impact (Confirmed)
- **Zero** corpus docs apply `value=` (or any `\apply`) to a `point[i]`. Gating changes
  manifest bytes only for already-broken docs → **no valid-doc byte change, no re-bless,
  `SCRIBA_VERSION` stays 22** (mirrors 0.26.2's "bogus no-op `element_add` on pure
  removals is suppressed", `_version.py:298` — a manifest-honesty drop that did not bump).

### RED sketch
```python
def test_invalid_selector_emits_no_value_change():
    tex = (r"\begin{animation}[id=m]\shape{plot}{MetricPlot}{series=[\"cost\"]}"
           r"\step\apply{plot}{cost=10}\narrate{a}"
           r"\step\apply{plot.point[0]}{value=5}\narrate{b}\end{animation}")
    manifest = extract_tr(render_string(tex))     # RED today
    assert not any(t.kind == "value_change" and "point[0]" in t.target for t in manifest)
```

---

## BONUS (surfaced by probe `p4a`) — Plane2D **in-range** `point[i]` `value=` is a MISSED `renders_value=False` case

Not either sub-finding as scoped, but found while separating them, and it re-classifies a
prior-doc row. `p4a` (`\apply{p.point[0]}{value=ZZZ}` with `point[0]` **in range**):

- Selector is **valid** — `validate_selector` accepts an in-range point (`plane2d.py:959-966`).
  The lone E1115 at `:210` is prescan-ordering noise (the point is added by the *structural*
  prescan **after** the value prescan), not a real rejection.
- Manifest emits `[["p.point[0]","value",null,"ZZZ","value_change"]]` fs:1, and the DOM
  element **exists** (`data-target="p.point[0]"` present).
- **But the point group is `<circle>`-only** (`plane2d.py:1407-1413`); point labels live in a
  separate `scriba-plane-labels` group. So the runtime finds **no `<text>`** to stamp →
  no-op → **never a visible flash** (regardless of labels).

This is the **same class as the core-4** (a part with no value display slot), not the
invalid-selector class. Plane2D simply never got a `renders_value` override, so its default
`True` slips past `_validate_value_channels`. **Cheapest fix: override
`Plane2D.renders_value("point[i]") → False`** (and, by inspection, likely
`line[i]`/`segment[i]`/`polygon[i]`/… — none render a per-element `value`), which makes the
existing E1105 gate reject it automatically — **no new mechanism.** MetricPlot needs no
override (it has no addressable value part at all; its `value=` targets are always
invalid → Sub-finding 2).

---

## Do they share one gate?

**Same architectural seam, three separate predicates + two dispositions.** All three ride
the pre-differ `_prescan_value_widths` / `_validate_value_channels` pass
(`_html_stitcher.py:229`, before the differ at `:652`):

| Case | predicate | disposition | error |
|---|---|---|---|
| Sub-1 Bar/Matrix non-numeric | `value_must_be_numeric(suffix)` **(new)** + `float()` fails | **raise** | E1107 (implement) |
| Sub-2 invalid selector | `not validate_selector(suffix)` **(existing)** | **drop value-record** | (completes E1115) |
| Bonus Plane2D point | `not renders_value(suffix)` **(existing gate)** | **raise** | E1105 (add primitive override) |

They do **not** share a single predicate: Sub-1 is a *content* check (raise), Sub-2 is a
*selector* check (drop, to honor E1115's soft-drop), Bonus is the *channel* check the
current gate already performs (just missing the Plane2D override).

---

## Conclusion

- **Sub-finding 1 — CONFIRMED, visible** (flip-back when `show_values=true`; manifest-only
  otherwise). Non-numeric `value=` on Bar/Matrix soft-drops server-side yet bakes a
  `value_change` carrying the string. **Recommend: implement the spec's dormant `E1107`
  and reject at author time** (pre-differ predicate; not inside `set_value`). Numeric path
  is honest (proven). **Impact: zero corpus, no re-bless, no `SCRIBA_VERSION` bump.**
- **Sub-finding 2 — CONFIRMED, never visible** (no DOM element → runtime no-op).
  Dishonest-manifest hygiene only. **Recommend: gate by dropping the value-record for
  invalid selectors** (completes E1115's soft-drop), **low priority — "leave as note" is
  defensible.** **Impact: zero valid-doc bytes, no bump.**
- **Bonus:** Plane2D in-range `point[i]` `value=` is a **missed member of the existing
  `renders_value=False` class** (never visible; `<circle>`-only group). Closes for free
  with a `Plane2D.renders_value` override on the geometric parts — the cheapest of the
  three and the one that reuses the shipped gate verbatim.

**Confidence: HIGH.** Every verdict is backed by a rendered SVG + extracted `tr` manifest
(8 probes) cross-checked against `emit_svg`/`set_value` source, the `scriba.js` handler,
and the spec's own `E1107`/`E1115` contracts. The one product choice (not a fact): whether
Sub-finding 2 is worth the churn given it has no visible symptom.
