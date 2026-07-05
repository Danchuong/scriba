# Verify: `\substory` structural-mutation "leak" into the parent timeline

BMAD confirm-or-refute. Read-only on source; probes rendered via `render.py`;
no playwright (render + parse only).

## Hand-off Brief (3 sentences)

**Reachable? YES** — a `\substory` `\apply`/`\recolor` on a *parent*-declared
shape mutates the **shared** parent object (not a copy), in both the scene-state
layer and, decisively, the emitter's single shared primitive. **Defect?
REFUTED** — the mutation *does* persist into the post-substory parent frames,
but that persistence is the **documented, intended, and corpus-relied-upon
behavior** (`docs/SCRIBA-TEX-REFERENCE.md:670`: "the substory does not create an
isolated scope … carries forward into subsequent parent frames"), not a bug.
**Fix? NONE to the behavior** — "fixing" the leak would break the docs and a
committed golden (`interval_dp.tex`); the only real issue is a *latent layer
divergence* (scene-state snapshot is restored/ephemeral while the emitter
primitive persists) plus a **misleading code comment** at `scene.py:441`, for
which the correct action is a locking regression test + comment correction.

Grade: **REFUTED** (defect) / **CONFIRMED** (persistence behavior + reachability).
Confidence: **High** for static rendering; Medium for the differ/interactive
divergence sub-finding (not exercised — no playwright).

---

## 1. Reachability — CONFIRMED (shared parent object, both layers)

The critical question was: does a substory `\apply{parentShape.cell[0]}{…}`
mutate a **copy** or the **shared** parent object?

**Scene layer (shared, then restored).** `apply_substory` (`scene.py:387`)
registers only the substory's *own* shapes (`scene.py:428-429`,
`self.shape_states[shape.name] = {}`); it never removes parent shapes. So inside
a substory frame, `\apply` → `_ensure_target` (`scene.py:1238-1262`) resolves
`shape_name` in the still-present **shared** `self.shape_states` and mutates the
parent's entry. This IS then deep-restored at `scene.py:442`
(`self.shape_states = saved_shape_states`).

**Emitter layer (shared, NOT restored — this is what the reader sees).**
Primitives are instantiated **once** for the whole animation
(`renderer.py:685`). `_materialise_substory` only creates *local* primitives when
the substory declares its own shapes (`renderer.py:879-886`); a substory that
just mutates a parent shape has none, so the emitter falls back to the **parent**
primitives dict:

- `_html_stitcher.py:321` — `sub_primitives = substory.primitives if substory.primitives else primitives`

Rendered proof of reach (probe `probe_apply_leak.tex`, substory does
`\apply{arr.cell[0]}{value=99}`): the substory frame shows `arr.cell[0]=99`, i.e.
the substory reached and mutated the parent's `arr`.

---

## 2. Repro — the "leak" is REAL but is DOCUMENTED PERSISTENCE (defect REFUTED)

### 2a. Rendered persistence (three probes)

`probe_apply_leak.tex` — parent `arr=[1,2,3]`; substory `\apply{arr.cell[0]}{value=99}`;
then a parent `\step`. DOM-nesting parse (`parse_frank.py`) of the rendered HTML:

| stage | level | cell0 value | cell0 state | narration |
|------|-------|------|------|-----------|
| 0 | PARENT | 1 | idle | Baseline |
| 1 | substory(d1) | 99 | idle | Inside substory |
| 2 | **PARENT** | **99** | idle | **After substory** |

`probe_frank.tex` — substory sets **both** value=99 **and** state=good:

| stage | level | cell0 value | cell0 state |
|------|-------|------|------|
| 0 | PARENT | 1 | idle |
| 1 | substory | 99 | good |
| 2 | **PARENT** | **99** | **good** |

Both `value` (via `set_value`) and `state` (via `set_state`) persist — it is not
value-specific; the whole primitive accumulates.

`cmd_substory_state_persist.tex` (the project's **own documented fixture**) —
substory `\recolor{a.cell[0]}{state=good}`, then parent frame narrated "cell 0
stays good":

| stage | level | cell0 value | cell0 state | narration |
|------|-------|------|------|-----------|
| 2 | **PARENT** | 1 | **good** | "Parent continues; cell 0 stays good." |

Renders exactly as the narration promises.

### 2b. Why this REFUTES the "defect" framing

- **Documented as intended.** `docs/SCRIBA-TEX-REFERENCE.md:670`: *"commands
  inside a `\substory` block (shapes, `\apply`, `\recolor`, `\annotate`) mutate
  the **parent** animation's scene state and persist after `\endsubstory`. The
  substory does not create an isolated scope: a `\recolor` on a parent shape
  inside the substory carries forward into subsequent parent frames exactly as if
  it had been issued at the parent level."*
- **A named fixture asserts it.** `tests/doc_coverage/corpus/cmd_substory_state_persist.expect`
  → `ok` / *"feature: \substory state persists into parent frames."*
- **A committed golden RELIES on it.** `tests/golden/examples/corpus/interval_dp.tex`:
  line 82 `\apply{dp.cell[2][5]}{value=2}` is issued **inside** a substory
  (lines 73-86); the post-substory parent frame (line 89) only
  `\recolor{dp.cell[2][5]}{state=done}` and **never re-sets the value**. Correct
  output requires the `value=2` to persist out of the substory. Removing the
  "leak" would render that cell empty — breaking the golden and author intent.

Three independent signals (docs + fixture + relied-upon golden) outweigh the one
`scene.py:441` comment that seeded the suspicion.

---

## 3. Root cause of the *persistence* (mechanism) + the real latent issue

**How it persists (correct-by-design):** `_emit_frame_svg` walks frames applying
each frame's state onto the **shared** primitive in place —
`prim.set_state(...)` (`_frame_renderer.py:1035`), `prim.set_value(...)`
(`_frame_renderer.py:1040`), and the structural `prim.apply_command(...)`
pre-pass for add_node/add_edge/remove (`_frame_renderer.py:832-859`) — then
`emit_svg()`. There is **no per-frame rollback**; mutations accumulate. This is
explicitly documented at `_html_stitcher.py:445-462` ("`_emit_frame_svg` … has a
side effect: it calls `prim.apply_command()` … mutations accumulate … in the live
primitives dict"). Substory frames render through the **same** parent primitives
(`_html_stitcher.py:321`; interactive path `:524`), so their mutations carry into
subsequent parent frames — i.e., persistence. (Width prescan and layout
measurement are *not* the vector: prescan snapshots/restores primitive state
`_frame_renderer.py:53-142`, and `measure_scene_layout` deep-copies primitives
`_frame_renderer.py:233`.)

**The real (inverse) latent issue — layer divergence.** The *scene-state
snapshot* IS restored (`scene.py:441-447`; comment says "substory mutations are
ephemeral"). Driving the exact renderer loop through the real `SceneState`
(`drive_scene.py`) shows the post-substory **parent snapshot** has
`arr.cell[0] = None` (reverted) — while the **rendered SVG** shows `99`. So the
two layers disagree:

- Emitter primitive → **persistent** (matches docs; drives static SVG).
- Scene snapshot → **ephemeral** (contradicts docs; the `scene.py:441` "ephemeral"
  comment is misleading).

For **static** output this is invisible (SVG comes from the primitive, which is
correct). It is only a latent risk for **snapshot-consuming** features — the JS
differ / interactive frame JSON / `\ref`-state / binding carets — which read the
reverted snapshot and could disagree with the displayed SVG (Hypothesized; not
exercised — no playwright).

Note: the premise (`investigations/teaching-lecture-tempo.md:20`) correctly
observed "mutations persist" but mis-attributed the mechanism to
`scene.py:408-409,441-443` ("only highlights/focus saved/restored"). In fact
`shape_states`/`annotations`/`bindings` are *also* restored there; persistence is
delivered by the **emitter primitive**, not by what `scene.py` restores.

---

## 4. Disposition + minimal action

**Do NOT alter the persistence behavior.** The suggested "fixes" (snapshot+restore
each primitive, deep-copy substory-visible primitives, or forbid substory `\apply`
on parent shapes with an E-code) would all **break** `docs:670`, the
`state_persist` fixture's contract, and the `interval_dp` golden. Rejected.

**Least-invasive correct actions (hygiene, low priority):**

1. **Lock the documented behavior with a content-asserting test** (below). Today
   `cmd_substory_state_persist.expect` only checks exit `ok` — *no test asserts the
   persisted content*, so a future well-meaning "isolation fix" could silently
   regress the documented contract. This test is the real deliverable value.
2. **Correct the misleading comment** at `scene.py:441` — replace "substory
   mutations are ephemeral" with a note that parent-shape mutations **persist via
   the emitter primitive** (per `docs:670`), and that the `shape_states` restore
   exists to scope substory-**local** shape ids and reset the substory frame
   counter (`scene.py:413`), *not* to make parent mutations ephemeral.
3. **(Optional, only if differ/interactive consistency is later shown to bite)**
   reconcile the snapshot layer to the documented persist semantics by removing
   only substory-**local** shape keys after the substory instead of a wholesale
   `self.shape_states = saved_shape_states` revert — so post-substory snapshots
   agree with the emitter. Defer until a concrete differ symptom is reproduced.

### TDD test (locks the documented persistence — RED before any erroneous "fix")

Mode note: `render.py`'s **default is the interactive widget** (`emitter.py:4`),
whose frames are `scriba-stage` `<div>`s with substory frames nested in
`scriba-substory` divs (there is **no** `<li class="scriba-frame">`). The test
therefore classifies stages by **substory-div nesting depth** and asserts on the
**last parent-timeline (depth-0) stage**. This helper is verified against three
rendered probes (`probe_frank` → value 99 + state good; the shipped
`cmd_substory_state_persist` fixture → state good; `probe_apply_leak` →
value 99, state idle).

```python
# tests/integration/test_substory_persistence.py
"""\substory parent-shape mutations persist into subsequent parent frames
(docs/SCRIBA-TEX-REFERENCE.md:670). Guards against a regression that would
re-isolate the substory scope. Verified against rendered probes 2026-07."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from render import render_file


def _last_parent_stage(html: str, target: str) -> dict | None:
    """Return {'val','state'} for `target` in the last substory-depth-0 stage."""
    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.sub = 0; self.stk = []; self.instage = False; self.cur = None
            self.incell = False; self.intext = False; self.res = []
        def handle_starttag(self, t, at):
            a = dict(at); c = a.get("class", "")
            if t == "div":
                is_sub = "scriba-substory" in c and all(
                    x not in c for x in ("container", "controls", "widget"))
                self.stk.append(is_sub); self.sub += is_sub
            if t == "svg" and "scriba-stage" in c:
                self.instage = True
                self.cur = {"depth": self.sub, "val": None, "state": None}
            if self.instage and t == "g" and a.get("data-target") == target:
                self.incell = True; self.cur["state"] = c
            if self.incell and t == "text":
                self.intext = True
        def handle_endtag(self, t):
            if t == "text": self.intext = False
            if t == "g" and self.incell: self.incell = False
            if t == "svg" and self.instage:
                self.res.append(self.cur); self.instage = False
            if t == "div" and self.stk:
                if self.stk.pop(): self.sub -= 1
        def handle_data(self, d):
            d = d.strip()
            if self.intext and self.cur and self.cur["val"] is None and d and len(d) <= 4:
                self.cur["val"] = d
    p = P(); p.feed(html)
    parents = [r for r in p.res if r["depth"] == 0]
    return parents[-1] if parents else None


def test_substory_mutation_persists_into_parent(tmp_path: Path) -> None:
    src = tmp_path / "s.tex"
    src.write_text(
        '\\begin{animation}[id="p", label="l"]\n'
        "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
        "\\step\n\\narrate{base}\n"
        '\\substory[title="Sub"]\n'
        "\\step\n\\recolor{a.cell[0]}{state=good}\n\\apply{a.cell[0]}{value=9}\n"
        "\\narrate{inside}\n\\endsubstory\n"
        "\\step\n\\narrate{after; a.cell[0] stays good and 9}\n"
        "\\end{animation}\n"
    )
    out = tmp_path / "s.html"
    render_file(src, out)
    stage = _last_parent_stage(out.read_text(), "a.cell[0]")
    assert stage is not None
    # docs:670 — the substory's parent-shape mutation persists into the
    # post-substory parent frame (both state and value).
    assert stage["state"] == "scriba-state-good"
    assert stage["val"] == "9"
```

Passes on current code (documented behavior) and fails loudly if a future change
re-isolates the substory scope — the guard the codebase is currently missing
(`cmd_substory_state_persist.expect` only checks exit `ok`, never content).

---

## 5. Conclusion

- **Reachability: CONFIRMED** — substory `\apply`/`\recolor` mutates the *shared*
  parent object; the emitter reuses parent primitives (`_html_stitcher.py:321`).
- **Suspected defect ("structural mutations leak = bug"): REFUTED** — the
  persistence is documented (`docs:670`), fixture-declared, and relied upon by a
  committed golden (`interval_dp.tex:82,89`); rendered probes confirm it works as
  documented.
- **Real latent finding: layer divergence** — scene snapshot restored/ephemeral
  (`scene.py:442`) vs emitter primitive persistent; harmless for static output,
  possible differ/interactive inconsistency (Hypothesized). Action: add the
  locking test + correct the `scene.py:441` comment; do **not** change behavior.

**Confidence: High** (defect refutation, reachability, static rendering — all
rendered). **Medium** (differ/interactive divergence — not exercised, no
playwright).

### Evidence index (all cited path:line)
- Persistence documented: `docs/SCRIBA-TEX-REFERENCE.md:670`, table `:98`.
- Fixture (only checks `ok`): `tests/doc_coverage/corpus/cmd_substory_state_persist.{tex,expect}`, harness `tests/doc_coverage/test_doc_coverage.py`.
- Corpus relies on persist: `tests/golden/examples/corpus/interval_dp.tex:82,89`.
- Scene restore + comment: `scene.py:387,428-429,441-447,1238-1262`.
- Driver: `renderer.py:685,834-847,879-886,888`.
- Emitter shared-primitive mutation: `_frame_renderer.py:1035,1040,832-859`; isolation of prescan/measure `:53-142,233`.
- Substory reuses parent primitives: `_html_stitcher.py:321,445-462,524`.
- Probes (scratchpad): `probe_apply_leak.tex`, `probe_frank.tex`, `drive_scene.py`, `parse_frank.py`; renders in gitignored `.scriba_tmp/verify_leak/`.
