# Hunt 2 — Traceback Fuzz on d628b9b New Raise/Validate/Emit Paths

**Hunter:** BMAD bug-hunter, round 2
**Target class:** TRACEBACK LEAKS (CRITICAL) — a Python traceback reaching the author
**Surface:** the ~15 new raise/validate/emit paths added by commit `d628b9b`
("fix(sweep-1): close 16 round-1 findings")
**Method:** read-only on source; structured fuzz probes in scratchpad; render via
`.venv/bin/python render.py <p>.tex -o <out>` (both interactive and `--static`).

---

## Hand-off Brief

**1 root cause, CRITICAL, 13-primitive blast radius.** The commit's advertised
feature "bare-shape `\annotate`: strike spans the whole content box" (Package B)
introduced an **infinite recursion** that crashes the renderer with an
uncaught `RecursionError` (exit 1, full Python traceback printed to the author).

`render.py` only catches `ScribaError` and `OSError` (render.py:441-450).
`RecursionError` is neither, so it escapes the harness verbatim — the exact
CRITICAL class this hunt targets.

**Trigger (minimal, no `\narrate` needed):**
```
\begin{animation}[id="t", label="t"]
\shape{s}{Stack}{items=["A","B"], max_visible=2}
\step
\annotate{s}{strike=true}
\end{animation}
```
→ `RecursionError: maximum recursion depth exceeded` — exit 1, traceback.

**Precondition:** a **bare** shape target (no `.cell[...]`/`.node[...]` suffix)
+ `strike=true`, on any primitive whose content-rect set is empty (so the new
`_whole_shape_content_box()` hits its `bounding_box()` fallback) and whose
`bounding_box()` reserves annotation arrow-space (which re-enters the annotation
measure). It is **new to d628b9b**: before the commit a bare whole-shape strike
was a documented silent no-op (`resolve_annotation_box(self.name)` → `None`), so
the cycle-closing edge did not exist.

Everything else on the new surface is clean: all 9 E1123-guarded commands, the
E1104/E1105/E1116/E1124/E1530/E1540/E1542 guards, note math/empty/unicode/wrap,
`at=` exotics, `side=` threading, ephemeral-reannotate revert lifecycle, and the
note+`\zoom` re-anchor path all resolve to clean E-codes or soft warnings, in
both interactive and static mode.

---

## Confirmed CRITICAL — bare-shape strike infinite recursion

**Severity:** CRITICAL (uncaught Python traceback reaches author; documented feature)
**Codes that *should* have fired:** E1119 soft-drop (the existing `warnings.warn`
two lines below the crash site) — the recursion happens before it is reached.

### Minimal repro
```
\begin{animation}[id="t", label="t"]
\shape{s}{Stack}{items=["A","B"], max_visible=2}
\step
\annotate{s}{strike=true}
\end{animation}
```
`.venv/bin/python render.py min.tex -o out.html` → **exit 1**, RecursionError.
Reproduces identically with `--static`.

### The recursion cycle (raising frames)

The cycle-closing new edge is **`scriba/animation/primitives/base.py:1246` →
`base.py:1119`**, both added by d628b9b:

```
emit_annotation_arrows()            base.py:1240  elif ann.get("strike"):
  _sbox = self._whole_shape_content_box()   base.py:1246   <-- FIX 4 (new)
    _whole_shape_content_box()      base.py:1117  rects = resolve_self_content_rects()
      return self.bounding_box()    base.py:1119   <-- fallback when rects == []  (new)
        <Prim>.bounding_box()       e.g. plane2d.py:1190 / equation.py:472
          _reserved_arrow_above()   base.py:522
            annotation_height_above() base.py:438
              _annotation_extent()  base.py:458
                _measure_emit(parts) base.py:509
                  emit_annotation_arrows(...)  base.py:1246  <-- back to top
...RecursionError: maximum recursion depth exceeded
```

`_whole_shape_content_box` (base.py:1109-1119):
```python
rects = self.resolve_self_content_rects()
if not rects:
    return self.bounding_box()      # <-- closes the cycle for empty-rect prims
```
For the 13 affected primitives `resolve_self_content_rects()` is empty, so the
fallback calls `bounding_box()`, which reserves annotation space by re-running the
annotation-measurement pass (`_measure_emit` → `emit_annotation_arrows`), which —
because this annotation is `strike=true` with `target == self.name` — re-enters
the FIX-4 branch. Unbounded self-recursion.

### Blast radius — `\annotate{S}{strike=true}` bare, per primitive type

| Primitive | Result | | Primitive | Result |
|-----------|--------|-|-----------|--------|
| CodePanel | **TRACEBACK** | | Array | E-clean (rejects target) |
| Deque | **TRACEBACK** | | BinaryHeap | E-clean |
| Forest | **TRACEBACK** | | Hypercube | E-clean |
| HashMap | **TRACEBACK** | | DPTable | OK (non-empty rects) |
| LinkedList | **TRACEBACK** | | Grid | OK |
| NumberLine | **TRACEBACK** | | Heatmap | OK |
| Plane2D | **TRACEBACK** | | Matrix | OK |
| Queue | **TRACEBACK** | | MetricPlot | OK |
| Stack | **TRACEBACK** | | TraceTable | OK |
| Tree | **TRACEBACK** | | | |
| Bar | **TRACEBACK** | | | |
| Equation | **TRACEBACK** | | | |
| VariableWatch | **TRACEBACK** | | | |

**13 of 22 primitive types crash.** The 9 clean types either reject the strike
target at construction (Array/BinaryHeap/Hypercube) or expose non-empty content
rects so `_whole_shape_content_box` never reaches the `bounding_box()` fallback
(DPTable/Grid/Heatmap/Matrix/MetricPlot/TraceTable).

### Controls (prove the precondition)
| Case | Result |
|------|--------|
| `\annotate{s.cell[0]}{strike=true}` (cell target, not bare) | exit 0 OK — no recursion |
| `\annotate{s}{label="x"}` (bare label, not strike) | exit 0, warns `[E1119]` — no recursion |
| `\recolor{s}{state=hidden}` then `\annotate{s}{strike=true}` | **TRACEBACK** (same root cause; whole-shape-hidden is not detected by the FIX-1 skip) |
| `\shape{e}{Equation}{lines=[...]}` + bare strike | **TRACEBACK** (same root cause) |

### Fix direction (advisory)
`_whole_shape_content_box()` must not re-enter the annotation measure. Either
compute the whole-shape box from a measurement-free geometry source, or guard the
`bounding_box()` fallback against re-entrancy (e.g. a reentrancy flag, or use a
raw/un-reserved content extent), or drop the bare-strike to the existing E1119
soft-drop when no content rects exist instead of falling back to `bounding_box()`.

---

## Full case matrix

356 render invocations across 3 batches (each ✕ interactive + static unless
noted). Classes: **E-clean** = exit 2 `error [E....]`; **OK** = exit 0 clean;
**WARN** = exit 0 with soft `[E....]`; **TRACEBACK** = exit 1 Python traceback.

### Summary counts
| Class | Count |
|-------|-------|
| E-clean | 263 |
| OK | 58 |
| WARN | 14 |
| **TRACEBACK** | **21** (all 1 root cause) |
| **Total runs** | **356** |

Distinct root causes: **1**. Distinct crashing primitive types: **13**.

### Batch 1 — param-dict edges on 9 E1123 commands + E1104/E1105/E1116/at=/side/compute (156 cases ✕ 2 = 312 runs)
All **E-clean/OK/WARN except** `4-strike-plane2d` and `4-strike-equation`
(→ TRACEBACK, both modes). Representative rows:

| Case | interp | static |
|------|--------|--------|
| 1-{annotate..cursor}-{empty,commas,keyonly,unbalq,nestbrace,unicodekey,dupkey,nestdictval,listval,tupleval,interpval,noeq} | E-clean / OK / WARN | same |
| 1-annotate-empty / -nestbrace / -dupkey / -interpval | OK | OK |
| 1-cursor-{commas,keyonly,dupkey,listval,tupleval,noeq} | WARN | WARN |
| 2-group-{emptypair,onepair,deepnest,emptytuple,mixed,dictish,emptylist,nullnode} | E-clean | E-clean |
| 3-apply-{emptyspec} | OK | OK |
| 3-apply-{bogustarget-unknownkey,unknownkey-interp,state,nestbrace} | E-clean | E-clean |
| 4-note-{mathonly,idunicode,idspaces,longwrap,longtoken} | OK | OK |
| 4-note-empty | E-clean | E-clean |
| **4-strike-plane2d** | **TRACEBACK** | **TRACEBACK** |
| **4-strike-equation** | **TRACEBACK** | **TRACEBACK** |
| 4-strike-metricplot | OK | OK |
| 4-strike-codepanel (invalid `code=` param) | E-clean | E-clean |
| 4-zoom-{equation} | OK | OK |
| 4-zoom-{undeclared,note} | E-clean | E-clean |
| 4-label-plane2d | WARN | WARN |
| 4-label-codepanel | E-clean | E-clean |
| 5-at-{nested,str,float,dup,mix} | E-clean | E-clean |
| 5-at-huge (`at=[1e9,1e9]`) | OK | OK |
| 6-reannot-side / 6-annot-side-{dict,list} | E-clean | E-clean |
| 6-reannot-{ephem-garbage,ephem-list,arrowfrom} / 6-annot-side-arrowfrom | OK | OK |
| 8-annot-label-undef / 8-interp-{dict,none} | OK | OK |
| 8-interp-list / 8-foreach-keyleak | E-clean | E-clean |
| 9-doublezoom (E1124) / 9-eq-texlines (E1530) | E-clean | E-clean |

### Batch 2 — bare-strike blast sweep across 22 primitive types (22 runs, interp)
13 TRACEBACK / 3 E-clean / 6 OK — see blast-radius table above.

### Batch 3 — remaining new paths (11 cases ✕ 2 = 22 runs)
| Case | interp | static |
|------|--------|--------|
| h-strike-hidden (recolor cell hidden + strike) | E-clean | E-clean |
| h-strike-hidden-label | E-clean | E-clean |
| h-note-zoom (note then zoom next step, re-anchor) | E-clean | E-clean |
| h-note-zoom-same (note + zoom same step) | E-clean | E-clean |
| h-ephem-lifecycle (ephemeral reannotate revert over 3 steps) | OK | OK |
| h-ephem-double (two ephemeral reannotate same frame) | OK | OK |
| h-note-hugetoken (200-char unbreakable token, tiny board) | E-clean | E-clean |
| h-side-emit (side= + arrow_from threaded to emit) | OK | OK |
| h-zoom-focus-zoom (zoom, focus, zoom in one step) | E-clean | E-clean |
| **h-strike-wholehidden** (recolor shape hidden + bare strike) | **TRACEBACK** | **TRACEBACK** |
| **h-eq-lines-strike** (Equation lines= + bare strike) | **TRACEBACK** | **TRACEBACK** |

---

## Conclusion

The command-param guard class (E1123) and the geometry/emit guards added by
d628b9b are **robust on the value side**: keys are always `IDENT` strings (so the
`sorted()` in `_validate_command_params` never sees mixed/unhashable keys), and
handlers wrap values in `str(...)` / use `in`-tuple membership, so dict/list/
tuple/InterpolationRef values into known keys degrade to clean E-codes rather
than tracebacks. `at=` is strictly normalized (E1540) before the board packer, so
the compaction path only ever sees hashable int tuples.

**The single defect is the Package B "bare-shape strike → whole content box"
feature (FIX 4):** `_whole_shape_content_box()`'s `bounding_box()` fallback closes
an infinite recursion for the 13 primitive types with empty content rects. It is
a **regression** (previously a silent no-op), reachable from a documented,
advertised author command, and it crashes with an uncaught `RecursionError` in
both interactive and static mode — a Confirmed CRITICAL traceback leak.

**Confidence: HIGH.** Minimal repro is 4 lines and deterministic; the raising
frames are cited from the live traceback; the 13/22 blast radius and the
precondition (bare target + empty content rects + arrow-reserving bounding_box)
are empirically pinned by controls; the introducing edge (base.py:1246 → :1119)
is confirmed present only in d628b9b.
