# Wave F — grammar.py split execution plan

**Date**: 2026-04-18
**Target**: `scriba/animation/parser/grammar.py` (1857 lines → multiple files all <800)
**Builds on**: `wave-D4-grammar-deferral.md`
**Strategy**: Test-first, mixin-based split (Option A from deferral note)

---

## Goal

Bring `grammar.py` under the 800-line hard limit while preserving:
- All 159 existing parser tests green
- The single public `SceneParser` class name
- All existing `from scriba.animation.parser.grammar import SceneParser` import paths
- Exact parse behavior (snapshot equivalence)

---

## Phase F1 — Sub-parser unit tests (prerequisite, NEVER skip)

Six new test files under `tests/unit/`, each exercising one parser concern in isolation
through `SceneParser.parse()` with narrow inputs (≥3 positive + ≥3 error paths each).

| Test file | Methods covered | Approx tests |
|---|---|---|
| `test_parser_foreach_unit.py` | `_parse_foreach`, `_parse_foreach_body` | 6+ |
| `test_parser_substory_unit.py` | `_parse_substory`, `_check_substory_trailing` | 6+ |
| `test_parser_param_value.py` | `_read_param_brace` (list, tuple, nested dict, interp) | 8+ |
| `test_parser_annotation_cmds.py` | `_parse_annotate`, `_parse_recolor`, `_parse_reannotate` | 8+ |
| `test_parser_interpolation.py` | `_check_interpolation_binding`, `_collect_compute_bindings` | 6+ |
| `test_parser_values_unit.py` | `_parse_interp_ref`, `_parse_list_value`, `_parse_tuple_value` | 6+ |

**Pass criterion**: All new tests green AND all 2700 existing tests still green.

**Commit**: `test: wave F1 — sub-parser unit tests for grammar split prep`

---

## Phase F2 — Easy extraction (Option B, low risk)

Extract pure-ish value parsers to `_grammar_values.py`:
- `_parse_interp_ref` (lines ~1617–1635)
- `_parse_list_value` (lines ~1637–1650)
- `_parse_tuple_value` (lines ~1652–1665)

Keep them as instance methods if they touch `self._advance()` / `self._peek()`. Use a
`_ValuesMixin` class (consistent with later phases). Wildcard re-export not needed since
they're private.

**Commit**: `refactor: wave F2 — extract _grammar_values.py mixin`

---

## Phase F3 — Foreach extraction

Move to `_grammar_foreach.py`:
- `_parse_foreach` (~75 lines)
- `_parse_foreach_body` (~80 lines)

Wrap in `_ForeachMixin`. Add `if TYPE_CHECKING:` block to declare shared `self.*`
attributes for mypy:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ast import Token

class _ForeachMixin:
    if TYPE_CHECKING:
        _tokens: list["Token"]
        _pos: int
        _foreach_depth: int
        _known_bindings: set[str]
        # ...
```

**Commit**: `refactor: wave F3 — extract _grammar_foreach.py mixin`

---

## Phase F4 — Substory extraction

Move to `_grammar_substory.py`:
- `_parse_substory` (~298 lines)
- `_check_substory_trailing` and any helpers exclusive to substory

This is the largest single extraction (~300 lines). Same mixin pattern as F3.

**Commit**: `refactor: wave F4 — extract _grammar_substory.py mixin`

---

## Phase F5 — Command parsers extraction

Move to `_grammar_commands.py`:
- `_parse_narrate`, `_parse_apply`, `_parse_highlight`, `_parse_recolor`,
  `_parse_reannotate`, `_parse_annotate`, `_parse_cursor` (lines ~677–954)

Wrap in `_CommandsMixin`.

**Commit**: `refactor: wave F5 — extract _grammar_commands.py mixin`

---

## Phase F6 — Final composition + verification

In `grammar.py`:
```python
from ._grammar_values import _ValuesMixin
from ._grammar_foreach import _ForeachMixin
from ._grammar_substory import _SubstoryMixin
from ._grammar_commands import _CommandsMixin

class SceneParser(
    _CommandsMixin,
    _SubstoryMixin,
    _ForeachMixin,
    _ValuesMixin,
):
    """Top-level scene parser."""

    def parse(self, source: str, ...) -> AnimationIR:
        ...
```

`grammar.py` final size target: <800 lines (should be ~600 after extracting ~600 lines
across F2–F5).

**Verification**:
```bash
pytest tests/ --ignore=tests/unit/test_parser_hypothesis.py -q   # all green
wc -l scriba/animation/parser/grammar.py scriba/animation/parser/_grammar_*.py
```

All split files MUST be <800 lines.

**Commit**: `refactor: wave F6 — slim grammar.py via mixin composition (1857 → N lines)`

---

## Risk mitigation

1. **Each phase commits independently** — if F4 breaks something, F1–F3 stay.
2. **Snapshot tests run after every phase** — any divergence in parsed AST fails fast.
3. **mypy guard**: after F6, run `mypy scriba/animation/parser/` to catch attribute
   resolution issues.
4. **MRO order matters**: list mixins from most-specific (commands) to least (values).
5. **Defer trigger**: if any phase finds a method with cross-mixin state coupling that
   wasn't anticipated, document it and stop — don't force the split.

---

## Agent allocation

- **F1 (tests)**: 2 parallel agents
  - Agent F1a: `test_parser_foreach_unit.py`, `test_parser_substory_unit.py`,
    `test_parser_interpolation.py`
  - Agent F1b: `test_parser_param_value.py`, `test_parser_annotation_cmds.py`,
    `test_parser_values_unit.py`
- **F2–F6**: 1 sequential agent each (5 phases, must serialize because each phase
  modifies grammar.py)

Total: 7 agent invocations across 2 batches (parallel F1, then serial F2→F6).

---

## Out-of-scope

- Refactoring grammar logic (only mechanical method moves)
- Changing `SceneParser` public API
- Adding new error codes or features
- Touching `lexer.py` or `ast.py` beyond import additions
