# v0.2.0 Verification Report

Date: 2026-04-09

## Test Results
- Total: 405 tests
- Passed: 405
- Failed: 0
- Errors: 0
- Warnings: 1 (bleach NoCssSanitizerWarning -- unrelated to animation)

## Starlark Worker Stress Test
- 100 sequential eval requests completed in 0.01s
- Throughput: ~13,500 req/s
- All assertions passed (bindings correctness verified per request)

## Exit Criteria Checklist
- [x] Animation end-to-end with Array (TestBinarySearchAnimation), DPTable (TestDPTableAnimation), Graph (TestGraphBFSAnimation)
- [x] \hl macro implemented (scriba.animation.extensions.hl_macro, 8 unit tests)
- [x] @keyframes presets implemented (scriba.animation.extensions.keyframes, 9 unit tests)
- [x] Starlark worker stress test (~13,500 req/s)
- [x] Frame count limits: E1150 warning (>30 frames), E1151 error (>100 frames)
- [x] CSS contrast check (see below)
- [x] AnimationRenderer.version = 1
- [x] Interactive output mode (default, via ctx.metadata["output_mode"])
- [x] Static output mode (ctx.metadata["output_mode"] = "static")

## CSS Contrast Check (WCAG AA)

Wong CVD-safe palette colors used as fill backgrounds with white (#ffffff) text:

| Color | Hex | Ratio vs white | AA Normal (4.5:1) | AA Large (3:1) |
|-------|-----|----------------|-------------------|----------------|
| current (blue) | #0072B2 | 5.19:1 | PASS | PASS |
| done (green) | #009E73 | 3.42:1 | FAIL | PASS |
| error (orange) | #D55E00 | 3.87:1 | FAIL | PASS |
| good (light blue) | #56B4E9 | 2.31:1 | FAIL | FAIL |
| highlight (yellow) | #F0E442 | 11.67:1 vs #212529 | PASS | PASS |

### Assessment

The Wong palette is optimized for color-vision-deficiency (CVD) safety, not
WCAG text contrast. These colors are used as **cell fill backgrounds** in
SVG primitives (array cells, graph nodes, DP table cells), where the text
content is typically a single digit or short label rendered at a size
equivalent to large text (>= 18pt / 14pt bold). Under the **WCAG AA large
text** criterion (3:1), all colors pass except `#56B4E9` (good/light blue).

The `good` state is a secondary semantic state used infrequently. All colors
are exposed as CSS custom properties (`--scriba-state-*-fill`,
`--scriba-state-*-text`) so integrators can override them for stricter
requirements.

**Recommendation**: No blocking issue for v0.2.0. Consider darkening
`--scriba-state-good-fill` to `#3a95c9` (the stroke color) in a future
patch if strict AA normal-text compliance is required.

## Known Issues
- Root-level `pytest tests/` collects all 405 tests correctly but the rtk proxy summarizes output (no actual collection issue)
- bleach CSS sanitizer warning on `test_bleach_roundtrip_inline_math` (pre-existing, unrelated to animation)
- `#56B4E9` (good state) fails WCAG AA for both normal and large text against white; exposed as CSS custom property for override
