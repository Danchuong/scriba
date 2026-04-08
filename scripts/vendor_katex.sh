#!/usr/bin/env bash
# Refresh the vendored KaTeX copy shipped inside the scriba wheel.
#
# Usage:
#   scripts/vendor_katex.sh [version]
#
# Default version: 0.16.11
#
# Downloads katex.min.js from jsDelivr, writes it to
# scriba/tex/vendor/katex/katex.min.js, and updates VENDORED.md with the
# new version, date, and SHA-256. Run from anywhere; paths are resolved
# relative to this script.

set -euo pipefail

VERSION="${1:-0.16.11}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR_DIR="${SCRIPT_DIR}/../scriba/tex/vendor/katex"
TARGET="${VENDOR_DIR}/katex.min.js"
META="${VENDOR_DIR}/VENDORED.md"
URL="https://cdn.jsdelivr.net/npm/katex@${VERSION}/dist/katex.min.js"
LICENSE_URL="https://raw.githubusercontent.com/KaTeX/KaTeX/v${VERSION}/LICENSE"

mkdir -p "${VENDOR_DIR}"

echo "Downloading KaTeX ${VERSION} from ${URL}"
curl -fsSL "${URL}" -o "${TARGET}"
curl -fsSL "${LICENSE_URL}" -o "${VENDOR_DIR}/LICENSE"

SIZE=$(wc -c <"${TARGET}" | tr -d ' ')
SHA=$(shasum -a 256 "${TARGET}" | awk '{print $1}')
TODAY=$(date +%Y-%m-%d)

echo "Version: ${VERSION}"
echo "Size:    ${SIZE} bytes"
echo "SHA-256: ${SHA}"

python3 - "${META}" "${VERSION}" "${SHA}" "${TODAY}" <<'PY'
import re, sys
meta_path, version, sha, today = sys.argv[1:5]
text = open(meta_path).read()
text = re.sub(r"(katex@)[0-9.]+", rf"\g<1>{version}", text)
text = re.sub(r"(\| Version \| `)[^`]+(`)", rf"\g<1>{version}\g<2>", text)
text = re.sub(r"(\| SHA-256 \| `)[^`]+(`)", rf"\g<1>{sha}\g<2>", text)
text = re.sub(r"(\| Vendored on \| )[0-9-]+( \|)", rf"\g<1>{today}\g<2>", text)
open(meta_path, "w").write(text)
PY

echo "Updated ${META}"
echo "Done. Remember to commit katex.min.js, LICENSE, and VENDORED.md together."
