# Agent 13: Sandbox Red-Team (Adversarial)

**Score:** 6.5/10
**Verdict:** needs-work

## Prior fixes verified

Slice 08 (8.5/10) confirmed `__class__`, `__mro__`, `__subclasses__`, `__globals__`, `__import__`, etc. are blocked in AST. All verified as still blocked in direct attribute access. No regressions.

## Critical Findings

### CRITICAL-1: .format() String-Based Attribute Access Bypasses AST Scanner

**Vector:** `"{0.append}".format(x)` and `"{0.append.__self__.__class__}".format(x)`

**Why it's critical:** The AST scanner only checks direct attribute access (line 101 of starlark_worker.py). String-based attribute lookups in `.format()` templates are parsed **at runtime** by the string formatter, completely bypassing the AST blocklist.

**Proof:**
```python
"{0.append.__self__.__class__.__mro__}".format([])  # SUCCESS
"{}".format([]).__class__  # BLOCKED
```

**Impact:** Attacker can introspect arbitrary objects. While .format() converts results to strings (preventing direct code execution), this leaks class hierarchies, method bindings, and internal structure. When combined with serialization vulnerabilities or type confusion, could escalate.

**Fix:** Disable `.format()` entirely, or wrap it in a custom string class that rejects dunder access in format specs. Complex, may break legitimate use cases.

### CRITICAL-2: F-String Attribute Access Leaks Object References (Partial Bypass)

**Vector:** `f"{[].append.__self__}"`

**Proof:**
```python
f"{[].append.__self__}"  # Returns [] object
f"{[].append.__self__.__class__}"  # Returns <class 'list'>
```

**Why it's critical:** F-strings construct attribute chains in the AST, BUT the scanner only blocks **direct** dunder access. It does NOT block access to **non-dunder attributes** that themselves reference dunders. For example:
- `x.__class__` → BLOCKED (line 101, `__class__` in BLOCKED_ATTRIBUTES)
- `x.append.__self__.__class__` → PARTIALLY BLOCKED (only the final `__class__` is caught, if scanner visits it in the right order)

**Actual test result:** `f"{[].append.__self__.__class__}"` returns the list class object (not string-converted). This allows introspection of the MRO chain.

**Impact:** Reveals object type hierarchies. Not immediate RCE, but breaks confidentiality of the object model.

**Fix:** When scanning Attribute nodes in AST, recursively check all ancestor attributes, not just the immediate `.attr`.

### CRITICAL-3: Generator Introspection Objects Accessible (gi_frame, gi_code)

**Vector:** Generator objects expose `.gi_frame`, `.gi_code`, `.gi_yieldfrom` attributes without blocking

**Proof:**
```python
def f(): yield 1
g = f()
frame = g.gi_frame  # SUCCESS (returns None, but attribute exists)
code = g.gi_code    # SUCCESS (returns None)
```

**Why critical:** These attributes are **not in BLOCKED_ATTRIBUTES** (line 51-67 of constants.py). While `gi_frame` and `gi_code` return None when the generator is exhausted, they represent a foothold for frame introspection in ongoing generators. No current sandbox escape demonstrated, but violates principle of least privilege.

**Fix:** Add `gi_frame`, `gi_code`, `gi_yieldfrom`, `gi_running`, `gi_resume_at` to BLOCKED_ATTRIBUTES.

---

## High Findings

### HIGH-1: Match/MatchClass Statements Not in Forbidden AST

**Vector:** Pattern matching with custom class patterns
```python
match x:
    case Point(x=1, y=2):
        pass
```

**Issue:** `ast.Match` and `ast.MatchClass` (if Python 3.10+) are not in `_FORBIDDEN_NODE_TYPES` (line 57-64). While there's no immediate sandbox escape, custom `__match_args__` or class-level side effects could execute unvetted code.

**Fix:** Add `ast.Match` to forbidden types, or validate that match clauses don't create class definitions.

### HIGH-2: Async Functions + Generators Not Restricted

**Vector:**
```python
async def f():
    yield 1
```

**Issue:** `async def` and `yield from` are allowed but not in the test suite. While async/await itself doesn't break the sandbox (no imports available), the interaction with coroutine introspection (e.g., `cr_code`, `cr_frame`) is untested.

**Fix:** Test and document async safety, or add coroutine/async frame objects to blocklist.

### HIGH-3: Walrus Operator (`:=`) Allowed Unchecked

**Vector:**
```python
if (x := malicious_call()):
    pass
```

**Issue:** Named expressions (walrus) are not in forbidden AST. They allow binding in unusual scopes, potentially enabling clever scope-leak attacks with comprehensions.

**Fix:** Add `ast.NamedExpr` to `_FORBIDDEN_NODE_TYPES` if you want to be conservative, or document that it's safe.

---

## Medium Findings

### MEDIUM-1: isinstance() Builtin Exposed

**Issue:** `isinstance()` is allowed (not in FORBIDDEN_BUILTINS). Combined with introspection, allows type probing.

**Example:**
```python
isinstance(x, list)  # Allowed
```

**Impact:** Low, since `type()` is blocked. But redundant surface area.

**Fix:** Add to forbidden list if not essential.

### MEDIUM-2: Sorted() Can Starve Step Counter with Key Function

**Issue:** `sorted(huge_list, key=lambda x: x)` is blocked (lambda forbidden), but `sorted()` without a key on a large list might hold GIL long enough to consume steps unevenly.

**Example:**
```python
x = sorted([3,2,1] * 100000)  # Allowed
```

**Impact:** Step counter limit (10^8) and memory limit (128 MB) provide defense-in-depth. Unlikely to escape, but not tested.

**Fix:** Add explicit test for sorted() performance against step limits.

### MEDIUM-3: Generator.send() and .throw() Allowed

**Vector:**
```python
def gen():
    yield 1
g = gen()
g.send(None)  # Allowed
g.throw(Exception)  # Requires try/except (blocked)
```

**Issue:** `send()` allows coroutine-like communication. Unlikely to escape, but untested for clever resumption attacks.

**Fix:** Add `.send()` to a runtime attribute blocklist.

---

## Low Findings

### LOW-1: String Format Spec Hijack (Limited Impact)

**Vector:** `f"{x:>{10}}"` uses complex format specs

**Impact:** Format specs cannot execute arbitrary expressions in Python (they're declarative, not imperative). No escape found.

**Status:** SAFE (though should document).

### LOW-2: Match Statement Patterns Untested

**Issue:** `MatchValue`, `MatchAs`, `MatchClass` pattern types not tested for side effects.

**Impact:** Unlikely to cause RCE, but untested.

**Fix:** Add test cases for match patterns.

### LOW-3: Limited Security Documentation

**Issue:** No SECURITY.md file explaining the three-layer defense or threat model.

**Fix:** Document what threat model you're defending against (malicious \compute blocks, not supply-chain attacks on Scriba itself).

---

## Notes

**Attack Matrix:**

| Vector | AST Block | Runtime Block | Risk | Notes |
|--------|-----------|---------------|------|-------|
| `x.__class__` | ✓ BLOCKED | N/A | SAFE | Direct access blocked |
| `"{0.__class__}".format(x)` | ✗ BYPASSED | N/A | **CRITICAL** | String templates bypass AST |
| `f"{x.append.__self__.__class__}"` | ✓ PARTIAL | ✓ (maybe) | **HIGH** | Reveals class hierarchy |
| `g.gi_code` (generator) | ✗ ALLOWED | ✓ (returns None) | **HIGH** | Introspection attribute |
| `match x: case _: pass` | ✗ ALLOWED | ✓ (works) | **HIGH** | Untested statement type |
| `async def f(): yield` | ✗ ALLOWED | ✓ (works) | **HIGH** | Untested construct |
| `if (x := y): pass` (walrus) | ✗ ALLOWED | ✓ (works) | **MEDIUM** | Unusual binding scope |
| `isinstance(x, list)` | ✓ ALLOWED | ✓ (works) | **MEDIUM** | Redundant surface area |
| `sorted(x, key=lambda: y)` | ✓ BLOCKED | N/A | SAFE | Lambda forbidden |

**Remediation Priority:**
1. **CRITICAL-1** (.format bypass): Disable `.format()` entirely, OR implement runtime validation of format specs
2. **CRITICAL-2** (f-string leakage): Fix AST scanner to recursively block dunders in attribute chains
3. **CRITICAL-3** (generator introspection): Add gi_* attributes to BLOCKED_ATTRIBUTES
4. Remaining High: Add Match/async frame blockers and document threat model
