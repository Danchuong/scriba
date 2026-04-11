# Agent 20: Cross-Cutting Red-Team

**Score:** 6/10 (significant integration and safety gaps despite solid individual components)
**Verdict:** ship-with-caveats

## Prior fixes verified
N/A — red-team is new ground.

## Critical Findings

1. **Context Provider Failure Path Unguarded (P0)**
   - `Pipeline._prepare_ctx()` chains context providers without exception handling. If any provider raises an exception, Pipeline.render() propagates it uncaught.
   - More critically: **if a provider returns None instead of RenderContext**, subsequent code trying to access `ctx.resource_resolver` will raise `AttributeError` ("'NoneType' object has no attribute"), masking the real error source.
   - **Location:** `scriba/core/pipeline.py` lines 93-96, 111
   - **Impact:** Silent data corruption pathway; consumer sees confusing AttributeError instead of original provider failure.

2. **Placeholder Substitution Re-Entry Bug (P0)**
   - Line 153 uses naive `.replace()` to substitute placeholders. If `artifact.html` contains the NUL-delimited placeholder pattern (e.g., `\x00SCRIBA_BLOCK_0\x00`), a subsequent placeholder substitution may incorrectly replace content inside previously-rendered artifacts.
   - **Location:** `scriba/core/pipeline.py` lines 149-153
   - **Impact:** XSS amplification; malicious/adversarial artifact HTML can inject placeholders that trigger unintended substitutions.

3. **Context Providers Default-Bypass Semantics (P1)**
   - Line 84-87: `context_providers=[]` (explicitly empty list) is not None, so default providers are **silently bypassed**. Consumers expecting default tex_inline_provider wiring get none.
   - **Location:** `scriba/core/pipeline.py` lines 84-88
   - **Impact:** Silent feature loss; no error raised; TeX inline rendering stops working with no diagnostic.

## High Findings

4. **Worker Cleanup on Exception Suppression (H1)**
   - `Pipeline.close()` silently catches and ignores all exceptions from `renderer.close()` (line 213-214). If a renderer's close() leaks resources (files, subprocesses, temp files) and raises, the error is swallowed.
   - **Location:** `scriba/core/pipeline.py` lines 211-214
   - **Impact:** Resource leaks may occur without any warning in logs; diagnostic becomes impossible.

5. **Version Attribute Casting Without Type Check (H2)**
   - Line 191: `int(renderer.version)` assumes renderer.version exists and is int-coercible. If a renderer implements version as a string or object without `__int__`, TypeError is raised, not caught.
   - **Location:** `scriba/core/pipeline.py` line 191
   - **Impact:** One broken renderer crashes the entire pipeline render call after blocks are already rendered (partial failure mid-operation).

6. **JSON Encoding NUL-Byte Vulnerability in Workers (H3)**
   - Workers use `json.dumps(..., ensure_ascii=False)` which permits UTF-8 encoding of any Unicode, including rare combining characters or right-to-left marks that could interfere with line-based JSON parsing.
   - **Location:** `scriba/core/workers.py` lines 242, 345
   - **Impact:** Malformed JSON response if worker receives request with zero-width or combining characters; silent parse failure.

## Medium Findings

7. **No Exception Handling in Block Rendering Loop (M1)**
   - Lines 145-147: If `renderer.render_block()` raises an exception after some blocks are already rendered, the function exits with partial results. No cleanup of already-rendered artifacts.
   - **Location:** `scriba/core/pipeline.py` lines 143-147
   - **Impact:** Half-rendered documents; pipeline state inconsistent.

8. **Asset Path Overwrite Semantics Unclear (M2)**
   - Line 175/180: If two renderers have the same namespace and basenames (e.g., both named "tex" with "style.css"), the second one silently overwrites the first in `asset_paths`.
   - **Location:** `scriba/core/pipeline.py` lines 173-180
   - **Impact:** Wrong asset file returned to consumer; potential security misconfiguration.

9. **Test Coverage Gap: Context Provider Edge Cases (M3)**
   - No test verifies what happens when `context_providers=[]`, `context_providers=[None]`, or a provider returns None/wrong type.
   - **Impact:** Unspecified behavior for documented public API; regressions possible.

## Low Findings

10. **getattr with "unknown" Default Hides Missing Attributes (L1)**
    - Line 163, 169: `getattr(renderer, "name", "unknown")` masks if a renderer lacks the name attribute (should fail at __init__ validation). Inconsistent with lines 75-79 which explicitly require it.
    - **Location:** `scriba/core/pipeline.py` lines 163, 169
    - **Impact:** Silent fallback; asset namespacing becomes unpredictable.

## Notes

The core pipeline is well-structured for normal operation, but several safety boundaries are missing at integration points:

- **Defensive coding gap:** Context providers can fail silently without type validation. A two-line check (`if not isinstance(ctx, RenderContext)`) would catch 80% of provider bugs.
- **Placeholder substitution safety:** Use a counter-based or UUID-based placeholder format resistant to re-entry rather than naive `.replace()`.
- **Resource cleanup philosophy:** Swallowing close() exceptions is dangerous; at minimum log them at WARNING level.
- **Partial failure semantics:** Document whether render() returns partial results on exception or rolls back.

Most findings are integration defects that peer agents testing individual components would not catch. The placeholder substitution bug is the only one with direct XSS amplification risk.
