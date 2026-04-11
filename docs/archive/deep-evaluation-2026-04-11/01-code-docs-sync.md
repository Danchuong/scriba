# Agent 1: Code↔Docs Sync Audit

**Score: 7/10**

## Critical Findings

### C1: Stack Primitive Parameter Documentation (ruleset.md, line 360)

**Severity:** CRITICAL

Documentation states Stack accepts `capacity` or `n` parameters. Code reality (stack.py): Stack accepts `orientation`, `max_visible`, `items`, `cell_width`, `cell_height`, `gap` — no `capacity` or `n`.

**Impact:** Users attempting `\shape{s}{Stack}{capacity=10}` will fail.

**Fix:** Update ruleset.md line 360 to remove `capacity`/`n` and list actual parameters.

---

## High Findings

### H1: Queue Parameter Documentation Ambiguity (ruleset.md, line 372)

Ruleset says "(none; `capacity` optional, default 8)" which is correct but formatting is confusing compared to other entries.

### H2: Section Numbering Anomaly

Section labeled "5.2" and "5.2b" — should be "5.2" and "5.3".

---

## Medium Findings

### M1: SubstoryCommand vs SubstoryBlock Terminology

Documentation calls `\substory`/`\endsubstory` "commands" but implementation uses `SubstoryBlock`. Should clarify as "block construct".

### M2: Matrix/Heatmap Alias Not Documented

Both names work but docs don't clarify they're the same underlying class (`@register_primitive("Matrix", "Heatmap")`).

### M3: File Reference Wrong

ruleset.md line 138 references `06-primitives.md` but actual file is `primitives.md`.

---

## Low Findings

### L1: Stack Code Docstring References Wrong Path

stack.py line 6 references `docs/primitives/stack.md` while other primitives reference `06-primitives.md`.

---

## Consistency Matrix: 16 Primitives

| Primitive | Selectors Match | Params Documented | Status |
|-----------|----------------|-------------------|--------|
| Array | ✓ | ✓ | PASS |
| Grid | ✓ | ✓ | PASS |
| DPTable | ✓ | ✓ | PASS |
| Graph | ✓ | ✓ | PASS |
| Tree | ✓ | ✓ | PASS |
| NumberLine | ✓ | ✓ | PASS |
| Matrix/Heatmap | ✓ | ~* | PASS (alias not clarified) |
| **Stack** | ✓ | **✗** | **FAIL** |
| Plane2D | ✓ | ✓ | PASS |
| MetricPlot | ✓ | ✓ | PASS |
| CodePanel | ✓ | ✓ | PASS |
| HashMap | ✓ | ✓ | PASS |
| LinkedList | ✓ | ✓ | PASS |
| Queue | ✓ | ✓ | PASS |
| VariableWatch | ✓ | ✓ | PASS |

## Commands: 14/14 Implemented ✓

All documented commands (shape, compute, step, narrate, apply, highlight, recolor, reannotate, annotate, cursor, foreach, endforeach, substory, endsubstory) are present in code.
