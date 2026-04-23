#!/usr/bin/env bash
# Compile .tex examples to .html (parallel).
# Usage: ./examples/build.sh [MODE] [--open] [-j N]
#
# Modes (pick one; default: all):
#   --smoke          Fast sanity: examples/smoke/
#   --demos          Full showcase: examples/demos/
#   --fixtures       Regression fixtures: examples/fixtures/{pass,expected-fail}/
#                    expected-fail/*.tex MUST fail to render (pinned error cases).
#   --algorithms     examples/algorithms/
#   --all            Everything under examples/ (default)
#
# Output: .html next to each .tex — gitignored build artifacts.

set -euo pipefail
cd "$(dirname "$0")/.."

OPEN_FLAG=""
JOBS="$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"
MODE="all"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --smoke) MODE="smoke"; shift ;;
        --demos) MODE="demos"; shift ;;
        --fixtures) MODE="fixtures"; shift ;;
        --algorithms) MODE="algorithms"; shift ;;
        --all) MODE="all"; shift ;;
        --open) OPEN_FLAG="--open"; shift ;;
        -j) JOBS="$2"; shift 2 ;;
        -j*) JOBS="${1#-j}"; shift ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -x ".venv/bin/python" ]]; then
    PY=".venv/bin/python"
else
    PY="uv run python"
fi

TMPDIR_RUN="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

# Compile .tex; success/failure tagged by bucket.
#   pass-path:        render MUST succeed
#   expected-fail:    render MUST fail (inverted)
render_one() {
    local tex="$1"
    local html="${tex%.tex}.html"
    local name="${tex#examples/}"
    local is_expected_fail=0
    [[ "$tex" == examples/fixtures/expected-fail/* ]] && is_expected_fail=1

    if $PY render.py "$tex" -o "$html" $OPEN_FLAG </dev/null >/dev/null 2>&1; then
        rc=0
    else
        rc=1
    fi

    if [[ $is_expected_fail -eq 1 ]]; then
        if [[ $rc -ne 0 ]]; then
            printf "  %-55s OK (expected-fail)\n" "$name"
            : > "$TMPDIR_RUN/ok.$$.$RANDOM"
        else
            printf "  %-55s UNEXPECTED-PASS\n" "$name"
            : > "$TMPDIR_RUN/fail.$$.$RANDOM"
        fi
    else
        if [[ $rc -eq 0 ]]; then
            printf "  %-55s OK\n" "$name"
            : > "$TMPDIR_RUN/ok.$$.$RANDOM"
        else
            printf "  %-55s FAILED\n" "$name"
            : > "$TMPDIR_RUN/fail.$$.$RANDOM"
        fi
    fi
}
export -f render_one
export PY OPEN_FLAG TMPDIR_RUN

case "$MODE" in
    smoke)      ROOTS=(examples/smoke) ;;
    demos)      ROOTS=(examples/demos) ;;
    fixtures)   ROOTS=(examples/fixtures) ;;
    algorithms) ROOTS=(examples/algorithms) ;;
    all)        ROOTS=(examples) ;;
esac

find "${ROOTS[@]}" -name "*.tex" -type f | sort | \
    xargs -n1 -P"$JOBS" -I{} bash -c 'render_one "$@"' _ {}

ok=$(find "$TMPDIR_RUN" -name 'ok.*' 2>/dev/null | wc -l | tr -d ' ')
failed=$(find "$TMPDIR_RUN" -name 'fail.*' 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "Done. mode=$MODE ok=$ok failed=$failed (jobs=$JOBS)"
[[ "$failed" -eq 0 ]]
