# Wave D4 — grammar.py split deferral

**Date**: 2026-04-18
**File**: `scriba/animation/parser/grammar.py`
**Line count**: 1857 lines (exceeds 800-line hard limit)
**Decision**: DEFER

---

## What was found

### Structure

`grammar.py` contains exactly **one class**: `SceneParser` (line 63 through EOF), with
37 methods totalling ~1800 lines of logic.  There are no module-level helper functions
beyond a single `_lazy_primitive_registry()` stub (lines 56-59).

The class is internally divided into informal comment sections:

| Lines | Section |
|-------|---------|
| 63–362 | `parse()` main loop + `_dispatch_command()` |
| 364–421 | Unknown-command diagnostics |
| 423–477 | Error recovery helpers |
| 479–583 | Options parser + `_parse_shape()` |
| 585–675 | Compute bindings / interpolation checking |
| 677–954 | Command parsers: narrate, apply, highlight, recolor, reannotate, annotate, cursor |
| 956–1110 | `_parse_foreach()` / `_parse_foreach_body()` |
| 1112–1409 | `_parse_substory()` |
| 1411–1857 | Shared primitives: brace readers, param parser, token navigation helpers |

### Why splitting is unsafe now

**Shared mutable instance state.**  Every method reads and writes the same set of
instance attributes:

- `self._tokens`, `self._pos` — token stream and cursor
- `self._source`, `self._lexer` — raw source for error messages
- `self._known_bindings` — interpolation symbol table (populated by `_parse_compute`,
  consumed by `_check_interpolation_binding` inside `_parse_apply`, `_parse_highlight`,
  selectors, and `_parse_foreach`)
- `self._substory_depth`, `self._substory_counter` — recursion guards
- `self._foreach_depth` — recursion guard
- `self._error_recovery`, `self._recovery_errors` — error recovery mode

Any file-level split that moves a subset of methods out would require either:

1. **Keeping them in the same class** — no line-count benefit.
2. **Mixin classes** (`class _ForeachMixin`, etc.) — Python mixins work, but require
   that all participating classes share `__init__` attribute setup.  This is non-trivial
   to test without sub-parser unit tests, and the pattern is not used elsewhere in
   scriba (Wave C1 used wildcard re-exports of *module-level* items, not class methods).
3. **Standalone functions receiving `self` as a parameter** — violates object model,
   makes mypy unhappy, and is semantically equivalent to keeping the methods in-class.

None of the three approaches matches the safe wildcard re-export pattern used in
Waves C1–C3.

**Test coverage is integration-only.**  159 tests exercise `SceneParser` but do so
exclusively through `SceneParser.parse(source)` end-to-end.  There are no tests that
call `_parse_cursor()`, `_parse_substory()`, `_read_param_brace()`, etc. in isolation.
A mixin refactor that accidentally broke state-sharing between methods (e.g. a forgetting
`self._known_bindings` update in a moved method) would not be caught until a higher-level
integration test triggered that exact code path.

---

## What would be needed before splitting

To safely split `grammar.py` into sub-modules (e.g. `_grammar_foreach.py`,
`_grammar_substory.py`, `_grammar_command_parsers.py`), the following prerequisite work
should be done first:

### 1. Sub-parser unit tests

Write focused tests for each major parsing method, exercising them in isolation (still
via `SceneParser.parse()` but with narrow inputs):

| Method group | Test file to create |
|---|---|
| `_parse_foreach` / `_parse_foreach_body` | `test_parser_foreach_unit.py` |
| `_parse_substory` | `test_parser_substory_unit.py` |
| `_parse_cursor` | already partially in `test_cursor_command.py` |
| `_read_param_brace` (list, tuple, nested dict, interp) | `test_parser_param_value.py` |
| `_parse_annotate`, `_parse_recolor`, `_parse_reannotate` | `test_parser_annotation_cmds.py` |
| `_check_interpolation_binding` + `_collect_compute_bindings` | `test_parser_interpolation.py` |

Coverage target: each method group should have at least 3 positive-path and 3 error-path
unit tests before the split.

### 2. Decide on split strategy

Option A (recommended): **Mixin classes in separate files, composed into `SceneParser`**

```python
# _grammar_foreach.py
class _ForeachMixin:
    def _parse_foreach(self) -> ForeachCommand: ...
    def _parse_foreach_body(self, ...) -> ForeachCommand: ...

# _grammar_substory.py
class _SubstoryMixin:
    def _parse_substory(self) -> SubstoryBlock: ...
    def _check_substory_trailing(self, ...) -> None: ...

# grammar.py  (slim orchestrator)
from ._grammar_foreach import _ForeachMixin
from ._grammar_substory import _SubstoryMixin

class SceneParser(_ForeachMixin, _SubstoryMixin):
    def parse(self, source: str, ...) -> AnimationIR: ...
```

The `__init__` attributes (`_tokens`, `_pos`, etc.) live in `SceneParser.__init__`
(already in `parse()`); mypy resolves them at runtime through the MRO.  This is the
lowest-risk mechanical split and preserves the single `SceneParser` public name.

Option B: **Pure function extraction with explicit parameter threading**

Extract stateless helpers (`_parse_interp_ref`, `_parse_list_value`,
`_parse_tuple_value`) into a new `_grammar_values.py`.  These three methods (lines
1617–1665) read only `self._tokens`/`self._pos` via `self._advance()` and
`self._peek()` — they could be refactored to accept a `(tokens, pos)` pair or a
lightweight `TokenStream` object.  This is lower risk than Option A but only reclaims
~50 lines.

### 3. Verification after split

```bash
uv run pytest tests/ -q   # expect full pass (2710+, 1 skip)
uv run mypy scriba/animation/parser/
```

---

## Risk assessment

| Risk | Severity | Notes |
|------|----------|-------|
| Broken `self.*` state sharing via mixin | HIGH | Needs unit test coverage first |
| Import cycles (grammar → ast → grammar) | MEDIUM | Already partially managed via `_lazy_primitive_registry` |
| mypy errors from mixin attribute references | MEDIUM | Type stubs or `TYPE_CHECKING` guards may be needed |
| Public API surface change | LOW | `SceneParser` name is unchanged; wildcard re-export not needed |

---

## Conclusion

The 1857-line `grammar.py` is over the 800-line limit but is **not safely splittable
today** without prerequisite unit test coverage and a deliberate mixin strategy.
Deferring preserves the current 2710-test green suite.  The prerequisite work above
(primarily the unit test files listed in §1) should be completed in a v0.9.x follow-up
before attempting the split.
