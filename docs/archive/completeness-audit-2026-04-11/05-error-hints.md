# Completeness Audit 05 — Error Hint Coverage

Agent 5 of 14. Scriba v0.5.1 @ HEAD eb4f017.

## Scope

Audit every E-code in `scriba/animation/errors.py` against its raise site(s)
and ask: does the error tell the author *how* to fix it? Specifically, does
it ship with

1. a concrete valid-values list, or
2. a `did you mean X?` fuzzy suggestion, or
3. an expected-format example ("hint: NumberLine{name}{domain=[min, max]}").

The reference implementation is the E1102 path in
`scriba/animation/parser/grammar.py::_validate_primitive_type` (line 511-547),
which uses `difflib.get_close_matches` via the module-local helper
`_fuzzy_suggest` (line 54-63). Every other raise site was checked for
whether it could be similarly upgraded.

Files audited:
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/errors.py`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/parser/grammar.py`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/parser/selectors.py`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/parser/lexer.py`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/scene.py`
- `/Users/mrchuongdan/Documents/GitHub/scriba/scriba/animation/starlark_worker.py`
- All `scriba/animation/primitives/*.py` constructors
- `docs/archive/production-audit-2026-04-11/05-error-catalog.md`

## E-code hint coverage table

Legend for **Hint?**:
- `enum` — raise site prints the full valid set ("valid: a, b, c")
- `example` — raise site prints a "hint: <example-code>" template
- `range` — raise site prints a numeric bound ("valid: 1..10000")
- `fuzzy` — raise site prints a `did you mean X?` difflib suggestion
- `—` — no hint; raw message only
- `orphan` — code is in catalog but never raised in `scriba/`

| Code | Subsystem | Raised in | Hint? | Could have fuzzy? | Priority |
|---|---|---|---|---|---|
| E1001 | lexer unclosed | lexer.py:276,331,391 | — | no (structural) | MEDIUM |
| E1003 | nested animation | — (catalog only) | orphan | n/a | LOW |
| E1004 | unknown option key | grammar.py:478, 1112, 1631, 1639 | enum | **YES** (VALID_OPTION_KEYS, 5 keys) | HIGH |
| E1005 | invalid option value | grammar.py:469, 1510, 1623, 1651 | — | partial (see notes) | MEDIUM |
| E1006 | unknown backslash cmd | grammar.py:361, 383, 1050, 1328 | enum (static list) | **YES** (14 known cmds) | HIGH |
| E1007 | expected `{` | lexer.py:250 | — | no | LOW |
| E1009 | selector generic | selectors.py:290 fallback | — | no | MEDIUM |
| E1010 | selector token | selectors.py:232,244,269,281 | — | no (char-level) | MEDIUM |
| E1011 | unterminated string | selectors.py:221 | — | no | LOW |
| E1012 | unexpected token kind | grammar.py:1728 | — | no | LOW |
| E1013 | source > 1 MB | grammar.py:101 | range | no | LOW |
| E1050-E1056 | diagram mode | grammar.py:259,280,289,301,1197,1238,1246,1686 | — | no (structural) | LOW (reserved) |
| E1100 | general parse | — (class only) | orphan | n/a | — |
| E1102 | unknown primitive | grammar.py:522, 540 | **enum+fuzzy** | DONE (Wave 4B) | HIGH (done) |
| E1103 | legacy primitive mega | scene.py:613 (annotation cap) | — | no | LOW |
| E1109 | recolor state | grammar.py:676, 717 | enum | **YES** (VALID_STATES, 4 values) | HIGH |
| E1112 | annotation position | grammar.py:795 | enum | **YES** (VALID_ANNOTATION_POSITIONS) | MEDIUM |
| E1113 | annotation color | grammar.py:695, 755, 804 | enum | **YES** (VALID_ANNOTATION_COLORS) | MEDIUM |
| E1150-E1155 | starlark | — (catalog only) | orphan | n/a | — |
| E1151 | starlark runtime | starlark_host.py wraps StarlarkEvalError | — | no | MEDIUM |
| E1170-E1172 | foreach structural | lexer/grammar | — | no | LOW |
| E1173 | foreach iterable | starlark_worker.py:270,277 | range | no | LOW |
| E1180 | frame > 30 warn | grammar.py UserWarning | — | n/a | LOW |
| E1181 | frame > 100 hard | errors.py:416 | range | no | LOW |
| E1182 | cursor states | — (catalog only) | orphan | n/a | — |
| E1360-E1368 | substory | grammar.py:289,301,339,349 | — | partial | LOW |
| E1400 | Array missing size | array.py:69 | example | n/a | HIGH |
| E1401 | Array size range | array.py:76,81 | range | n/a | HIGH |
| E1402 | Array data/size mismatch | array.py:90 | example | n/a | HIGH |
| E1410-E1412 | Grid | grid.py:47,61,109,118,123,128,133 | example | n/a | HIGH |
| E1420-E1429 | Matrix/DPTable | matrix.py, dptable.py | example | n/a | HIGH |
| E1430-E1432 | Tree | tree.py:317,352,379 | example | n/a | HIGH |
| E1440 | Queue capacity | queue.py:79 | range | n/a | MEDIUM |
| E1441 | Stack max_visible | stack.py:92 | range | n/a | MEDIUM |
| E1450-E1454 | HashMap/NumberLine | hashmap.py:77,84; numberline.py:77,83,98,106 | example | n/a | HIGH |
| E1460 | Plane2D viewport | plane2d.py:94,96 | — | no | MEDIUM |
| E1461-E1463, E1466 | Plane2D geom | — (logger warnings only) | orphan | n/a | LOW |
| E1465 | Plane2D aspect | plane2d.py:103 | enum (inline) | **YES** (2 values, typo likely) | MEDIUM |
| E1470 | Graph nodes | graph.py:211,225 | example | n/a | HIGH |
| E1480-E1487 | MetricPlot | metricplot.py:117,119,144,184,215,237 | mixed (some example) | partial | MEDIUM |
| E1500-E1505 | graph layout | graph_layout_stable.py | range | no | LOW |

## Prioritized hint-add list

Priority ranked by author hit-rate. Each entry: **raise site, current
message, proposed upgrade**.

### HIGH — parse-time, hit on every typo

**1. E1004 — unknown option key**
- Raise sites: `grammar.py:478`, `1112`, `1631` (step), `1639` (step dup).
- Current: `unknown option key 'lyout'; valid: id, label, layout, width, height`.
- Gap: no fuzzy hint. `VALID_OPTION_KEYS` has exactly five members — a
  one-char typo on `layout` is the single most likely author mistake.
- Upgrade: call `_fuzzy_suggest(key, sorted(VALID_OPTION_KEYS))` and attach
  as `hint="did you mean: layout?"`. Same pattern for the four call sites
  (env options, substory options, step options, step dup). Mechanical.

**2. E1006 — unknown backslash command**
- Raise sites: `grammar.py:361`, `383` (`_raise_unknown_command`), `1050`
  (inside step body), `1328` (substory body).
- Current: `unknown command \apl; valid commands: \shape, \compute, \step,
  \narrate, \apply, \highlight, \recolor, …`. Static hard-coded tuple at
  line 371-375.
- Gap: author will absolutely mistype `\aply`, `\recloor`, `\hihglight`,
  `\forech`. Fuzzy suggestion would land ~100 % of the time.
- Upgrade: replace the static `_VALID_COMMANDS_LIST` string with a real
  tuple, and in `_raise_unknown_command` call
  `_fuzzy_suggest(tok.value, _KNOWN_COMMANDS)` → `hint=f"did you mean:
  \\{sug}?"`. Keep enum in detail message as fallback.

**3. E1109 — unknown recolor state**
- Raise site: `grammar.py:676`.
- Current: `unknown recolor state 'active'; valid: active, highlight, idle,
  visited`. (Exact `VALID_STATES` is read from `constants.py`.)
- Gap: no fuzzy. `current` / `active` / `selected` / `done` are all likely
  author mistakes vs the real set `{active, highlight, idle, visited}`.
- Upgrade: fuzzy over `sorted(VALID_STATES)` — same shape as E1004.

**4. E1400/E1402/E1410/E1420/E1426/E1430/E1450/E1452/E1470 — primitive
   constructor "missing/invalid kwarg"**
- Already have `example` hints ("hint: Graph{name}{nodes=[...]}") —
  coverage is OK. No fuzzy needed here because the keyword *is* missing,
  not misspelled.
- But see next item for the mirror problem.

**5. NEW E-code needed — unknown kwarg to shape constructor**
- No raise site exists today. Every primitive `__init__` does
  `self.params.get("rows")` and silently ignores typos. An author who
  writes `\shape{a}{Array}{sise=10}` gets E1400 "missing 'size'" — the
  enum hint tells them the right key, which is half-decent, *but*
  `\shape{p}{Plane2D}{xranges=[...], yrange=[...]}` is accepted and
  silently renders with default xrange.
- Proposed: each primitive declares a class-level
  `ACCEPTED_PARAMS: frozenset[str]` and `PrimitiveBase.__init__` checks
  `params.keys() - ACCEPTED_PARAMS`, raising a new **E1114 — unknown
  primitive parameter** with a `_fuzzy_suggest` hint. This is the single
  highest-value hint to add, because today the typo is silent.
- Priority: **HIGH**, new code allocation required.

### MEDIUM — constructor limits and annotation validation

**6. E1112 — annotation position**
- Raise: `grammar.py:795`. Enum already present; add fuzzy over
  `VALID_ANNOTATION_POSITIONS` (6-ish values, very typo-prone:
  `above`/`below`/`left`/`right`/`center`/`over`).

**7. E1113 — annotation color**
- Raise: `grammar.py:695, 755, 804`. Same treatment; `VALID_ANNOTATION_COLORS`
  has ~6 semantic values (`info`, `warn`, `error`, `success`, …). Add
  fuzzy.

**8. E1465 — Plane2D aspect**
- Raise: `plane2d.py:103`. Only two valid values (`equal`, `auto`). Current
  message: `aspect must be 'equal' or 'auto', got 'equa'`. Fuzzy is
  overkill (two values) but the message is already the enum; OK.

**9. E1460 — Plane2D viewport**
- Raise: `plane2d.py:94,96`. Current: `"xrange has equal endpoints
  (degenerate viewport)"`. No hint. Add `hint="use xrange=[lo, hi] with
  lo != hi, e.g. xrange=[-1, 1]"`. Cheap.

**10. E1151 — starlark runtime**
- Surfaced by `scriba/animation/starlark_host.py`. No fuzzy (error is a
  real Python traceback). Ensure `format_compute_traceback` in `errors.py`
  is wired — audit 09-error-ux notes it is still unused.

### LOW — edge cases, rarely hit in practice

E1001 (unclosed env), E1013 (source size), E1181 (frame cap), E1505
(graph seed), E1441 (stack max_visible) — all already give the limit in
the detail. No fuzzy applies. Leave as-is.

## Suggested helper code sketches

### Sketch A — promote `_fuzzy_suggest` to a shared helper

Currently `_fuzzy_suggest` lives in `grammar.py` (private, lines 54-63)
and is only called once (E1102). Move it to `scriba/animation/errors.py`
alongside `animation_error()` so every raise site — grammar, selectors,
primitives — can import it without a circular dep.

```python
# scriba/animation/errors.py
from __future__ import annotations
import difflib
from typing import Iterable

def suggest_closest(
    name: str,
    candidates: Iterable[str],
    *,
    cutoff: float = 0.6,
) -> str | None:
    """Return the closest candidate to *name*, or None.

    Thin wrapper around difflib so every hint raise site can share
    one spelling of "did you mean".
    """
    close = difflib.get_close_matches(name, list(candidates), n=1, cutoff=cutoff)
    return close[0] if close else None


def hint_for_unknown(
    name: str,
    candidates: Iterable[str],
    *,
    kind: str = "value",
) -> str | None:
    """Build a human-facing hint string for an unknown value."""
    cands = sorted(candidates)
    sug = suggest_closest(name, cands)
    if sug:
        return f"did you mean {sug!r}?"
    if len(cands) <= 8:
        return f"valid {kind}s: {', '.join(cands)}"
    return None
```

### Sketch B — parser-side enum validator

Inline wrapper used by every grammar raise site that currently builds the
valid-list manually (E1004, E1006, E1109, E1112, E1113).

```python
# scriba/animation/parser/grammar.py
from scriba.animation.errors import suggest_closest

def _raise_unknown_enum(
    self,
    *,
    kind: str,            # "option key", "state", "command"
    got: str,
    valid: frozenset[str] | tuple[str, ...],
    code: str,
    tok: Token,
) -> None:
    valid_sorted = sorted(valid)
    sug = suggest_closest(got, valid_sorted)
    hint = f"did you mean {sug!r}?" if sug else None
    raise ValidationError(
        f"unknown {kind} {got!r}; valid: {', '.join(valid_sorted)}",
        position=tok.col,
        code=code,
        line=tok.line,
        col=tok.col,
        source_line=self._source_line_at(tok.line),
        hint=hint,
    )
```

Then each call site becomes one line, e.g. for E1109:

```python
if state not in VALID_STATES:
    self._raise_unknown_enum(
        kind="recolor state",
        got=state,
        valid=VALID_STATES,
        code="E1109",
        tok=tok,
    )
```

Six call sites collapse to six uniform invocations.

### Sketch C — new E1114 unknown-param check in `PrimitiveBase`

```python
# scriba/animation/primitives/base.py
class PrimitiveBase(abc.ABC):
    # Subclasses override with their accepted params.
    ACCEPTED_PARAMS: ClassVar[frozenset[str]] = frozenset()

    def __init__(self, name: str = "", params: dict[str, Any] | None = None):
        self.name = name
        self.params = params if params is not None else {}
        if self.ACCEPTED_PARAMS:
            unknown = set(self.params) - self.ACCEPTED_PARAMS
            if unknown:
                bad = sorted(unknown)[0]
                sug = suggest_closest(bad, self.ACCEPTED_PARAMS)
                hint = (
                    f"did you mean {sug!r}?"
                    if sug else
                    f"accepted: {', '.join(sorted(self.ACCEPTED_PARAMS))}"
                )
                raise animation_error(
                    "E1114",
                    f"{type(self).__name__}: unknown parameter {bad!r}",
                    hint=hint,
                )
        # … rest of existing init
```

Each primitive then declares e.g.
`ACCEPTED_PARAMS = frozenset({"size", "n", "data", "labels", "label"})`.
Backward compatibility: subclasses that do not yet declare the set keep
the existing silent behaviour (empty frozenset → no check), so the change
is opt-in per primitive.

### Sketch D — selector path fuzzy (optional, LOW)

`SelectorParser` could at `_error` time fetch the declared shape's
`SELECTOR_PATTERNS` keys and suggest the closest one. This is harder
because the parser runs before shape context is available — would need
a post-parse validation pass in `scene.py::_ensure_target`. Deferred.

## Severity summary

- **HIGH, not yet wired**: E1004, E1006, E1109 (fuzzy upgrade), plus new
  **E1114** (primitive unknown kwarg). Four items. Together they cover the
  "mistyped name" path for option keys, commands, recolor states, and
  shape kwargs — the four most author-visible classes of typo.
- **HIGH, already wired**: E1102 (primitive type name) — confirmed in
  Wave 4B at `grammar.py:537` via `_fuzzy_suggest`.
- **HIGH, enum-only is sufficient**: E1400, E1402, E1410, E1420, E1426,
  E1430, E1450, E1452, E1470 — the author is *missing* a kwarg, not
  mistyping one. Existing `hint: <example>` format is correct. No change.
- **MEDIUM**: E1112, E1113 (annotation enums — fuzzy low-cost win), E1460
  (viewport example hint), E1151 (wire `format_compute_traceback`).
- **LOW / leave-alone**: structural lexer codes (E1001/E1007/E1011/E1012),
  limit codes (E1013/E1181/E1441/E1505), orphan codes (E1003, E1100,
  E1150-E1155 except E1151, E1182, E1461-E1463, E1466).
- **Orphan cleanup** (out of scope for hints but flagged by audit
  05-error-catalog): 13 codes defined but never raised. Either wire them
  or retire them; hint coverage is vacuously 0 %.

Total raise sites surveyed: ~70. Raise sites with any hint today: ~35
(50 %). Raise sites with `did you mean` today: **1** (E1102 only).
Adding Sketch A+B+C would bring fuzzy coverage from 1 → 7 E-codes and
would eliminate the biggest class of silent-typo bugs in primitive
construction (E1114).

The lowest-cost / highest-value next action is Sketch B applied to the
five existing enum sites in `grammar.py`: roughly 30 lines of diff, no
new E-codes, and it mirrors the exact pattern already shipped for E1102.
