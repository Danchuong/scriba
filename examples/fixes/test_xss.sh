#!/usr/bin/env bash
# Regression test: C2 — XSS via filename in <title> and <h1>
#
# Copies the fixture to a path with a malicious filename, renders it, then
# verifies the dangerous string is HTML-escaped in the output.
#
# Exit 0  → fix is in place (escaped output, no raw XSS payload)
# Exit 1  → regression (raw <img> found in output, or render failed)

set -euo pipefail

FIXTURE="$(dirname "$0")/18_xss_filename.tex"
MALICIOUS_NAME="<img src=x onerror=alert(1)>"
TMP_INPUT="/tmp/${MALICIOUS_NAME}.tex"
TMP_OUTPUT="/tmp/xss_test_out.html"

cp "$FIXTURE" "$TMP_INPUT"

# Render — must succeed
if ! uv run python render.py "$TMP_INPUT" -o "$TMP_OUTPUT" 2>&1; then
    echo "FAIL: render.py exited with an error" >&2
    rm -f "$TMP_INPUT" "$TMP_OUTPUT"
    exit 1
fi

# Check: escaped form is present in the output
if grep -qF '&lt;img' "$TMP_OUTPUT"; then
    echo "PASS: filename is HTML-escaped in output"
    RESULT=0
else
    echo "FAIL: escaped form '&lt;img' not found in output" >&2
    RESULT=1
fi

# Check: raw form must NOT appear in title or h1 (it would indicate XSS)
if grep -qE '<title>Scriba — .*<img' "$TMP_OUTPUT" || grep -qE '<h1>.*<img' "$TMP_OUTPUT"; then
    echo "FAIL: raw <img> found inside <title> or <h1> — XSS present" >&2
    RESULT=1
fi

rm -f "$TMP_INPUT" "$TMP_OUTPUT"
exit $RESULT
