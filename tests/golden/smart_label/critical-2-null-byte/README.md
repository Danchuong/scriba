# critical-2-null-byte

## What this fixture guards

Regression guard for bug class C-2: a null byte (U+0000) embedded in an
annotation label must be stripped before it reaches the SVG `<text>` element.
Raw null bytes make SVG output non-well-formed XML, which breaks any downstream
parser (browser, Inkscape, CI artifact validators).

The **expected.svg** captures the FIXED state: the null byte has been stripped
and the label renders as `"ab"` (not `"a\x00b"`).

## Invariants exercised

T-1 (label text sanitization), §2.4 (guard against invalid character injection)

## Known-failing

`known_failing: true` — the null-byte stripping fix has not yet been merged
to main. The corpus runner will `xfail` this test until the fix lands.

Once the fix is merged:

1. Run `SCRIBA_UPDATE_GOLDEN=1 pytest tests/golden/smart_label/ -k critical-2-null-byte`
2. Verify the diff — only this fixture's `expected.svg` and `expected.sha256`
   should change.
3. Flip `known_failing` to `false` in the fixture metadata.
4. Add a CHANGELOG entry documenting the old and new SHA256.

## Rebase trigger notes

Rebase ONLY if the sanitization logic or pill geometry constants change.
KaTeX and Python float jitter are handled by the normalizer.
