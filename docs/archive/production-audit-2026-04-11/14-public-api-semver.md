# Agent 14: Public API Surface + Semver Discipline

**Score:** 7/10
**Verdict:** ship-with-caveats

## Prior fixes verified
N/A — new scope.

## Critical Findings

1. **ScribaRuntimeError undeclared in public API** — `scriba/core/errors.py` defines `ScribaRuntimeError` (a fourth error class for runtime dependencies like missing Node.js), but it is NOT exported in `scriba/__init__.py.__all__` or `scriba/core/__init__.py.__all__`. This creates asymmetry: `ScribaError`, `RendererError`, `WorkerError`, `ValidationError` are public, but `ScribaRuntimeError` is orphaned. **Impact:** consumers attempting to catch this exception will face import errors; documentation must clarify this is intentionally private or it must be added to `__all__`.

2. **Architecture.md unmaintained for 0.1.1+ fields** — The locked contract document (`docs/spec/architecture.md`) defines `Document` with only four fields (`html`, `required_css`, `required_js`, `versions`), but the actual dataclass in `scriba/core/artifact.py` includes two additional fields added in 0.1.1-alpha: `block_data` (line 94) and `required_assets` (line 97). Neither field appears in the spec contract. **Impact:** consumers reading the spec assume a 4-field shape; this breaks their expectations silently at runtime.

3. **SCRIBA_VERSION lag on Document shape** — CHANGELOG notes that 0.1.1 added `block_data` and `required_assets` fields plus changed asset namespacing to `"renderer/basename"`, bumping `SCRIBA_VERSION` to `2`. But `SCRIBA_VERSION` is currently hardcoded to `2` in `_version.py` with no comment linking it to that 0.1.1 decision. If `Document` shape changes again in 0.6.0+, the constant must be bumped but the connection is invisible. **Risk:** easy to forget.

## High Findings

1. **Asset key format `"renderer/basename"` not enforced** — CHANGELOG documents the breaking change (0.1.1): `required_css`/`required_js` now use namespaced keys like `"tex/scriba-tex-content.css"`. However, the only place this is documented is CHANGELOG. The `artifact.py` docstring says "basenames only" (line 54), contradicting reality. No validation exists to prevent renderers from shipping non-namespaced keys. **Mitigation:** documentation is clear enough for adopters, but the code comment is stale.

2. **Deprecated alias lacks deprecation warning** — CHANGELOG notes `SubprocessWorker` as a deprecated alias for `PersistentSubprocessWorker` with a comment "remove in 0.2.0" (line 311 of `workers.py`). This was written in 0.1.1 (released 2026-04-08). We are now at 0.5.0. The alias still exists but without any `warnings.warn()` call on import or on `.send()`. **Impact:** consumers silently using the old name have no signal to migrate; the deprecation is effectively invisible.

3. **block_data/required_assets not documented in CHANGELOG 0.5.0** — These fields were added in 0.1.1 and are stable. However, 0.5.0 CHANGELOG makes no mention of them, leaving new adopters confused about their lifecycle. If a field had been removed or renamed since 0.1.1, this silence would hide a breaking change.

## Medium Findings

1. **__all__ is complete but asymmetric exports** — Top-level `scriba/__init__.py.__all__` (lines 28–50) correctly re-exports the core surface plus version constants and sanitization whitelist. However, `scriba/core/__init__.py.__all__` (lines 15–30) omits `PersistentSubprocessWorker`, `OneShotSubprocessWorker`, and worker pool members that are available via `scriba.core.workers`. These classes ARE exported from the top-level module but not from `core`, creating confusion about which submodule is canonical.

2. **Error class attributes added but not documented** — All four error classes (`RendererError`, `WorkerError`, `ScribaRuntimeError`, `ValidationError`) add custom attributes beyond the base `ScribaError` (e.g., `renderer`, `stderr`, `component`, `position`). These are stable and not mentioned in CHANGELOG, but adding new attributes to dataclass-like exceptions is technically API surface. None of this is in the architecture spec.

3. **Py classifier claim verified but versioning inversion** — `pyproject.toml` line 25 correctly declares `"Development Status :: 4 - Beta"`, matching the 0.5.0 upgrade from alpha to beta mentioned in CHANGELOG 0.5.0. However, 0.5.0 is still a 0.x release; per semver, any minor-version bump means breaking changes are allowed, but they must be documented. No breaking changes are noted in 0.5.0 CHANGELOG (only error-code additions and internal refactoring), so the claim is accurate.

## Low Findings

1. **ALLOWED_TAGS/ALLOWED_ATTRS stable since 0.1.0** — `scriba/sanitize/whitelist.py` shows comprehensive whitelists (44 tags, multiple SVG/MathML additions). CHANGELOG documents incremental additions in 0.2+ (SVG for diagrams), but base set is unchanged since 0.1.0. No risk here; the surface is frozen.

2. **RenderContext, Renderer, RendererAssets shapes unchanged since 0.1.0** — All three are locked per architecture spec and no breaking changes are noted in any CHANGELOG entry. Fields are stable.

3. **Pipeline, Block, RenderArtifact frozen except for 0.1.1 additions** — Block and RenderArtifact both gained the `metadata` optional field in 0.1.0 (stable). RenderArtifact added `block_id` and `data` in 0.1.1 (stable). Pipeline interface is unchanged.

## Notes

- **Recommendation:** Before 1.0.0, merge architecture.md with the 0.1.1 additions (`block_data`, `required_assets`, asset namespacing) into a locked contract. Add a section documenting why `ScribaRuntimeError` is intentionally private or move it to `__all__`.
- **Deprecation discipline:** Establish a deprecation warning for `SubprocessWorker` to unblock the 0.2.0 removal mentioned in code.
- **SemVer clarity:** 0.5.0 is a clean release with no breaking changes, but the gap between CHANGELOG and spec docs creates soft coupling.
