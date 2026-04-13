# Transition Tests Fix Plan

> **Date**: 2026-04-13
> **Status**: 12 integration tests failing in `tests/integration/test_animation_transitions.py`
> **Root cause**: Golden file / regex mismatch after `fs:` field was added to emitter output

---

## Discovery

The differ and transition system are **fully implemented and wired up**:

| Component | File | Status |
|-----------|------|--------|
| Diff engine | `scriba/animation/differ.py` (331 lines) | Complete |
| Transition/TransitionManifest types | `differ.py:14-40` | Complete |
| Emitter integration | `emitter.py:848-880` | Complete |
| JS animation runtime | `emitter.py:908-1050+` | Complete |
| Unit tests for differ | `tests/animation/test_differ.py` | Passing |
| Integration tests | `tests/integration/test_animation_transitions.py` | **FAILING** |
| Golden files | `tests/golden/animation/html_*.html` | **STALE** |

The differ works correctly. The emitter correctly computes and serializes transitions. The **only problem** is that golden files and test regex are out of sync with the current output format.

---

## Root Cause Analysis

### The `fs:` field

The emitter at `emitter.py:875` outputs frames with this format:

```javascript
{svg:`...`,narration:`...`,substory:`...`,label:`...`,tr:null,fs:0}
```

The `fs:` (full-sync) field was added after the golden files were written. Golden files have:

```javascript
{svg:`...`,narration:`...`,substory:`...`,label:`...`,tr:null}
```

### The regex

The test helper `_extract_tr_fields()` uses:

```python
re.findall(r",tr:(null|\[\[.*?\]\])\}", html)
```

This expects `tr:` to be the **last** field before `}`. With `fs:` after `tr:`, the regex never matches, returning `[]` for every test.

### Verified

```python
# Actual output for 2-step recolor:
# tr fields found: []   ← regex returns empty
#
# But tr: IS in the output:
# ...tr:null,fs:0}      ← frame 0
# ...tr:[["a.cell[1]","state","idle","current","recolor"]],fs:1}  ← frame 1
```

---

## Fix Plan

### Task 1: Update test regex (1 agent)

**File**: `tests/integration/test_animation_transitions.py:81`

Change regex from:
```python
re.findall(r",tr:(null|\[\[.*?\]\])\}", html)
```
To:
```python
re.findall(r",tr:(null|\[\[.*?\]\]),fs:\d\}", html)
```

This accounts for the `fs:N` field that now follows `tr:`.

### Task 2: Regenerate golden files (same agent)

**Files**: `tests/golden/animation/html_*.html` (4 files)

The golden files need to be regenerated from the current emitter output. For each:
1. Run the corresponding test source through the pipeline
2. Capture `artifact.html`
3. Write to the golden file

Golden files to regenerate:
- `html_two_step_recolor.html` — from `_SOURCE_RECOLOR`
- `html_value_change.html` — from `_SOURCE_VALUE_CHANGE`
- `html_element_add.html` — from `_SOURCE_ELEMENT_ADD`
- `html_identical_steps.html` — from `_SOURCE_IDENTICAL`

### Task 3: Verify all 12 tests pass (same agent)

After regex fix + golden regen, run:
```bash
python -m pytest tests/integration/test_animation_transitions.py -v
```

All 12 tests (16 cases including parametrize) should pass.

### Task 4: Update docs (separate agent)

Files that need minor updates to reflect that transitions are implemented:

| File | Current claim | Update |
|------|--------------|--------|
| `docs/guides/animation-plugin.md:23` | "Transitions between frames beyond pure CSS are NOT produced" | Remove or update — transitions ARE produced |
| `CHANGELOG.md` | No entry for transition fix | Add entry |

Files that are accurate and need NO update:
- `docs/spec/animation-css.md` — CSS transition rules are correct
- `docs/spec/environments.md` — "opacity fade" description still accurate
- `docs/spec/ruleset.md` — timing controls remain out-of-scope (correct)
- `docs/spec/svg-emitter.md` — emitter spec doesn't contradict current behavior

---

## Agent Plan

**2 agents total** (this is a small, targeted fix):

| Agent | Task | Files |
|-------|------|-------|
| **1** | Fix regex + regenerate golden files + verify tests | `test_animation_transitions.py`, `tests/golden/animation/html_*.html` |
| **2** | Update docs (animation-plugin.md, CHANGELOG.md) | `docs/guides/animation-plugin.md`, `CHANGELOG.md` |

### Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| Golden files contain SVG that varies by platform | Low | Golden comparison is only on `tr:` fields, not full HTML |
| Regex change breaks other tests | None | Regex is only used in this test file |
| Differ produces wrong transitions | None | `tests/animation/test_differ.py` already passes (unit-level) |
| `fs:` field format changes again | Low | Comment in test explaining the expected format |

### Pre-flight Check

Before spawning agents, verify the hypothesis:

```python
# This should return the correct tr: fields
re.findall(r",tr:(null|\[\[.*?\]\]),fs:\d\}", actual_html)
# Expected: ["null", '[["a.cell[1]","state","idle","current","recolor"]]']
```

---

## What NOT To Do

1. **Do NOT modify `differ.py`** — it's correct and passing unit tests
2. **Do NOT modify `emitter.py`** — the `fs:` field is intentional and correct
3. **Do NOT modify `renderer.py`** — pipeline integration is correct
4. **Do NOT rewrite golden files by hand** — generate from actual pipeline output
5. **Do NOT change the JS animation runtime** — it works correctly with `tr:` + `fs:` fields
