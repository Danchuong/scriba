#!/usr/bin/env bash
# Regression test: H1 — Path traversal via -o flag
#
# Runs render.py with -o pointing outside CWD and verifies it is rejected.
# Also verifies the SCRIBA_ALLOW_ANY_OUTPUT=1 opt-out works.
#
# Exit 0  → fix is in place (outside-cwd write rejected, opt-out accepted)
# Exit 1  → regression

set -euo pipefail

FIXTURE="$(dirname "$0")/19_path_traversal.tex"
ESCAPE_OUTPUT="/tmp/scriba_escape_test_$$.html"
RESULT=0

# ── Test 1: outside-CWD write must be rejected ──────────────────────────────
echo "Test 1: outside-cwd write should be rejected..."
STDERR_OUT=$(uv run python render.py "$FIXTURE" -o "$ESCAPE_OUTPUT" 2>&1) && GOT_EXIT=0 || GOT_EXIT=$?

if [ "$GOT_EXIT" -ne 1 ]; then
    echo "FAIL: expected exit 1, got $GOT_EXIT" >&2
    RESULT=1
fi

if echo "$STDERR_OUT" | grep -q "refusing to write outside cwd"; then
    echo "PASS: rejection message present"
else
    echo "FAIL: expected 'refusing to write outside cwd' in stderr, got: $STDERR_OUT" >&2
    RESULT=1
fi

if [ -f "$ESCAPE_OUTPUT" ]; then
    echo "FAIL: output file was created despite rejection" >&2
    rm -f "$ESCAPE_OUTPUT"
    RESULT=1
fi

# ── Test 2: opt-out env var allows the write ────────────────────────────────
echo "Test 2: SCRIBA_ALLOW_ANY_OUTPUT=1 should permit the write..."
SCRIBA_ALLOW_ANY_OUTPUT=1 uv run python render.py "$FIXTURE" -o "$ESCAPE_OUTPUT" 2>&1 && OPT_EXIT=0 || OPT_EXIT=$?

if [ "$OPT_EXIT" -ne 0 ]; then
    echo "FAIL: opt-out write failed with exit $OPT_EXIT" >&2
    RESULT=1
else
    echo "PASS: opt-out write succeeded"
fi

rm -f "$ESCAPE_OUTPUT"
exit $RESULT
