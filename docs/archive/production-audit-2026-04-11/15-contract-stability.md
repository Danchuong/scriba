# Agent 15: Long-Term Contract Stability

**Score:** 6/10
**Verdict:** needs-work

## Prior fixes verified

N/A — new scope.

## Critical Findings

1. **No explicit stability policy for v1.0.** CHANGELOG explicitly marks v0.1.1 as introducing BREAKING changes to `Document.required_css/js` asset keys (namespaced format change). The roadmap notes "v1.0 API freeze" is "not scheduled" and references only "two consecutive minor releases with no HTML shape change + one external OJ in production" as a trigger — but this is a *measurement* of stability, not a *commitment* to it. **No README or CONTRIBUTING document promises backward compatibility after 1.0 lands.**

2. **E-code numbering: "append-only within E1001–E1299" mentioned in O4-quality-bar but NOT enforced in code.** The `docs/oss/O4-quality-bar.md` states: *"Error codes are append-only within E1001–E1299. Removing a code is a MAJOR bump; changing its message text is not."* However, this is a design note in `/docs/oss/`, not a locked spec. The actual `ERROR_CATALOG` in `scriba/animation/errors.py` has no docstring or commit-time guard stating this principle.

3. **Asset namespace format `<renderer>/<basename>` promised in CHANGELOG but not in locked spec.** Line 122-124 of CHANGELOG says BREAKING in v0.1.1: "Asset key shape changes (now namespaced as `<renderer>/<basename>`)." This is a **runtime contract**, but the `docs/spec/architecture.md` (the "locked" spec) does NOT mention the namespace format at all — only that RenderArtifact returns "basenames only" and the Pipeline does the aggregation. Consumers rely on this shape; renaming a renderer would silently break their asset resolution.

## High Findings

1. **ALLOWED_TAGS / ALLOWED_ATTRS: frozenset/Mapping but no version bump policy.** When a new tag or attribute is added, every consumer's bleach sanitizer config silently widens. The test `test_whitelist.py` validates structure and bleach roundtrip but does NOT test:
   - That the set is immutable between releases
   - That adding a tag requires bumping a version constant
   - That consumers can pin to a specific set version

   No test enforces "do not remove tags" as a breaking change.

2. **CSS class names (`.scriba-frame`, `.scriba-stage`, `.scriba-stage-svg`, etc.) are output-locked but have no contract document.** Found in examples and emitter code (e.g., `scriba/animation/emitter.py`) but:
   - Not listed in `docs/spec/architecture.md`
   - `docs/spec/animation-css.md` exists but is not linked from the locked specs section
   - No test explicitly validates that class names remain stable across releases

3. **SVG ID format `scriba-{sha256[:10]}` same issue.** `docs/spec/ruleset.md` line 30 mentions default ID as `"scriba-{sha256[:10]}"` but:
   - No locked spec defines the hash algorithm or truncation length as stable
   - Changing from SHA256 to SHA512 or truncation length from 10 to 8 chars would break consumer CSS selectors
   - No test pins the hash format

4. **Document.required_assets resolved Paths lack stability promise.** Field added in v0.1.1 but not mentioned in locked architecture spec. The pipeline populates it via `importlib.resources` paths, which are opaque; a repackaging of `scriba/tex/static/` files could change paths unexpectedly.

## Medium Findings

1. **Renderer.priority int tie-breaker tested but not part of locked spec.** Default is 100 (hardcoded in pipeline.py line 116), and the test `test_pipeline_priority_breaks_overlap_ties()` validates it works. But:
   - `docs/spec/architecture.md` mentions priority in the Protocol docstring but does NOT document the numeric range or promise that 100 stays the default
   - No test pin: "if no priority attribute, must default to 100"

2. **Pipeline constructor default context_providers undocumented.** Added in v0.1.1 (CHANGELOG line 109), the default is `_default_tex_inline_provider` which duck-types on `renderer.name == "tex"`. This is a hidden contract: if a consumer adds their own context provider, they may override or skip the tex wiring. No locked spec mentions this provider or its importance.

3. **RenderArtifact.block_id and .data shape not specified.** Added v0.1.1 but the locked spec says only: "Optional public data payload." No schema is defined; consumers may pattern-match on key names like `block_data["graph-0"]` — if the naming scheme changes, breakage is silent.

4. **SCRIBA_VERSION int is vehicle for cache invalidation, but policy is hidden.** v0.1.1 bumped it from 1 to 2 (CHANGELOG). There is no locked document stating:
   - When to bump SCRIBA_VERSION (only "when the core API changes in a way that invalidates consumer caches" — vague)
   - Whether it ever resets on v1.0
   - Whether consumers are expected to version-pin or assume compatibility within 0.x

## Low Findings

1. **Test coverage for contract stability is incomplete.** `test_whitelist.py` validates that `ALLOWED_TAGS` is a frozenset and `ALLOWED_ATTRS` is a Mapping, but does NOT:
   - Assert exact membership (`{p, br, strong, ...}`) so that accidental tag removal is caught
   - Assert that mutations raise TypeError (though frozenset does)

   Add: `assert ALLOWED_TAGS == frozenset({"p", "br", ...})` snapshot test.

2. **No documented handler for deprecation or feature-flag rollout.** If a breaking change is unavoidable (e.g., KaTeX upstream change), there is no stated deprecation window, warning mechanism, or feature-flag strategy.

3. **Error catalog docstring references location but catalog is in code.** `scriba/animation/errors.py` line 29 defines `ERROR_CATALOG` but does not include a note like "locked: error codes in E1001–E1299 are append-only; removing a code is BREAKING."

## Notes

| Contract | Documented? | Locked Spec? | Tested? |
|----------|------------|--------------|---------|
| Asset namespace `renderer/basename` | CHANGELOG only | No | Yes (test_pipeline.py:167–168) |
| E-code numbering (append-only) | O4-quality-bar.md (OSS docs) | No | No |
| ALLOWED_TAGS/ATTRS immutability | whitelist.py docstring | No | Partial (structure, no membership) |
| CSS class names (e.g., `.scriba-frame`) | animation-css.md (not linked) | No | No explicit test |
| SVG ID format `scriba-{sha256[:10]}` | ruleset.md | No | No |
| Renderer.priority default (100) | pipeline.py code | No | Yes (test_pipeline.py:174+) |
| Pipeline default context_providers | CHANGELOG only | No | No |
| SCRIBA_VERSION bump policy | architecture.md (vague) | No | No |

**Recommendation:** Before v1.0, create a **STABILITY.md** file at the repo root documenting:
- Frozen contracts: asset namespace, E-code range, CSS classes, SVG IDs, ALLOWED_TAGS/ATTRS
- When each is locked (e.g., "v0.1.1 onward")
- What breaks it (removal → MAJOR, addition → backward-compat)
- Migration window for any breaking change (e.g., "6-month deprecation period before removal")

Add snapshot tests pinning `ALLOWED_TAGS`, `ALLOWED_ATTRS`, and error code range to prevent silent regressions. Update architecture.md to include the namespaced asset format and CSS class names in the locked API section.
