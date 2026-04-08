#!/usr/bin/env bash
# Refresh the vendored KaTeX copy shipped inside the scriba wheel.
#
# Usage:
#   scripts/vendor_katex.sh [version]
#
# Default version: 0.16.11
#
# Downloads katex.min.js, katex.min.css, and all KaTeX_*.woff2 fonts
# from jsDelivr into scriba/tex/vendor/katex/. The CSS has its .woff
# and .ttf @font-face fallbacks stripped (woff2 only). VENDORED.md is
# updated in place with the new version, date, and JS SHA-256.

set -euo pipefail

KATEX_VERSION="${1:-0.16.11}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="${SCRIPT_DIR}/../scriba/tex/vendor/katex"
JS_TARGET="${VENDOR_DIR}/katex.min.js"
CSS_TARGET="${VENDOR_DIR}/katex.min.css"
FONTS_DIR="${VENDOR_DIR}/fonts"
META="${VENDOR_DIR}/VENDORED.md"
BASE="https://cdn.jsdelivr.net/npm/katex@${KATEX_VERSION}/dist"
LICENSE_URL="https://raw.githubusercontent.com/KaTeX/KaTeX/v${KATEX_VERSION}/LICENSE"

mkdir -p "${VENDOR_DIR}" "${FONTS_DIR}"

echo "Downloading KaTeX ${KATEX_VERSION} JS+CSS from ${BASE}"
curl -fsSL "${BASE}/katex.min.js"  -o "${JS_TARGET}"
curl -fsSL "${BASE}/katex.min.css" -o "${CSS_TARGET}"
curl -fsSL "${LICENSE_URL}"        -o "${VENDOR_DIR}/LICENSE"

echo "Downloading woff2 fonts referenced by katex.min.css"
FONTS=$(grep -oE "fonts/KaTeX_[A-Za-z0-9_-]+\.woff2" "${CSS_TARGET}" | sort -u)
for f in ${FONTS}; do
  curl -fsSL "${BASE}/${f}" -o "${VENDOR_DIR}/${f}"
done

echo "Stripping .woff and .ttf @font-face fallbacks from katex.min.css"
python3 - "${CSS_TARGET}" <<'PY'
import re, sys
p = sys.argv[1]
c = open(p).read()
c = re.sub(r',url\(fonts/[^)]+\.woff\) format\("woff"\),url\(fonts/[^)]+\.ttf\) format\("truetype"\)', '', c)
open(p, 'w').write(c)
PY

JS_SIZE=$(wc -c <"${JS_TARGET}" | tr -d ' ')
JS_SHA=$(shasum -a 256 "${JS_TARGET}" | awk '{print $1}')
CSS_SHA=$(shasum -a 256 "${CSS_TARGET}" | awk '{print $1}')
TODAY=$(date +%Y-%m-%d)

echo "Version:     ${KATEX_VERSION}"
echo "JS size:     ${JS_SIZE} bytes"
echo "JS SHA-256:  ${JS_SHA}"
echo "CSS SHA-256: ${CSS_SHA} (post-strip)"

python3 - "${META}" "${KATEX_VERSION}" "${JS_SHA}" "${CSS_SHA}" "${TODAY}" <<'PY'
import re, sys
meta_path, version, js_sha, css_sha, today = sys.argv[1:6]
text = open(meta_path).read()
text = re.sub(r"(katex@)[0-9.]+", rf"\g<1>{version}", text)
text = re.sub(r"(\| Version \| `)[^`]+(`)", rf"\g<1>{version}\g<2>", text)
text = re.sub(r"(\| Vendored on \| )[0-9-]+( \|)", rf"\g<1>{today}\g<2>", text)
text = re.sub(r"(katex\.min\.js \|[^|]*\|[^|]*\| `)[0-9a-f]+(`)", rf"\g<1>{js_sha}\g<2>", text)
text = re.sub(r"(katex\.min\.css \|[^|]*\|[^|]*\| `)[0-9a-f]+(` \(post-strip\))", rf"\g<1>{css_sha}\g<2>", text)
open(meta_path, "w").write(text)
PY

echo "Updated ${META}"
echo "Done. Commit katex.min.js, katex.min.css, fonts/*.woff2, LICENSE, and VENDORED.md together."
