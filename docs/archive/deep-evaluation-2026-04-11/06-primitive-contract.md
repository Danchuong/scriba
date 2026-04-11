# Agent 6: Primitive Contract Audit

**Score: 7.8/10**

## Critical Issues (4)

### C1: Return Type Inconsistency in bounding_box()

Base class specifies `-> BoundingBox`. 9 primitives return `tuple[float, float, float, float]` instead: Array, DPTable, Grid, Matrix, NumberLine + others.

### C2: Missing ClassVar Annotation on SELECTOR_PATTERNS

Only Array correctly uses `ClassVar[dict[str, str]]`. 15 primitives omit ClassVar.

### C3: No State Validation in set_state()

No validation against VALID_STATES. Any string accepted: `arr.set_state('cell[0]', 'nonexistent_state')` succeeds silently.

### C4: No Selector Validation in set_state()/set_value()

`set_state('cell[999]', 'error')` on a 5-element array silently accepted. Creates ghost state entries.

## Compliance Matrix

| Primitive | Constructor | SELECTOR_PATTERNS | validate_selector() | set_state() | render_svg() | Edge Cases |
|-----------|---|---|---|---|---|---|
| Array | ✓ | ⚠ ClassVar | ✓ | ✗ No validation | ✓ | ⚠ |
| CodePanel | ✓ | ⚠ ClassVar | ✓ (1-based) | ✗ | ✓ | ✓ |
| DPTable | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ⚠ |
| Graph | ⚠ empty | ⚠ ClassVar | ✓ | ✗ | ✓ | ⚠ |
| Grid | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ✓ |
| HashMap | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ✓ |
| LinkedList | ✓ | ⚠ ClassVar | ⚠ link off-by-one | ✗ | ✓ | ⚠ |
| Matrix | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ✓ |
| MetricPlot | ✓ | ⚠ ClassVar | ⚠ Only "all" | ✗ | ✓ | ⚠ |
| NumberLine | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ✓ |
| Plane2D | ✓ | ⚠ ClassVar | ⚠ Partial | ✗ | ✓ | ⚠ |
| Queue | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ⚠ |
| Stack | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ✓ |
| Tree | ✓ | ⚠ ClassVar | ✓ | ✗ | ✓ | ✓ |
| VariableWatch | ⚠ empty | ⚠ ClassVar | ✓ | ✗ | ✓ | ⚠ |

## Must Fix (Blocks Release)

1. Standardize bounding_box() return type to BoundingBox (9 primitives)
2. Add state validation in set_state() against VALID_STATES
3. Add selector validation in set_state()/set_value()/set_label()
4. Add ClassVar annotations (15 primitives)

## Should Fix (Before v1.0)

5. Fix LinkedList link[i] off-by-one validation
6. Add max size limits to DPTable, LinkedList
7. Standardize error types (HashMap, VariableWatch should use animation_error)
