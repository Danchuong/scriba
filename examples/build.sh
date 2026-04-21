#!/usr/bin/env bash
# Compile all .tex examples to .html (parallel).
# Usage: ./examples/build.sh [--open] [-j N]
#
# Output: .html files next to each .tex file
# These are gitignored — treat as build artifacts.

set -euo pipefail
cd "$(dirname "$0")/.."

OPEN_FLAG=""
JOBS="$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --open) OPEN_FLAG="--open"; shift ;;
        -j) JOBS="$2"; shift 2 ;;
        -j*) JOBS="${1#-j}"; shift ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

# Prefer project venv to avoid `uv run` resolve overhead per invocation.
if [[ -x ".venv/bin/python" ]]; then
    PY=".venv/bin/python"
else
    PY="uv run python"
fi

TMPDIR_RUN="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

render_one() {
    local tex="$1"
    local html="${tex%.tex}.html"
    local name="${tex#examples/}"
    if $PY render.py "$tex" -o "$html" $OPEN_FLAG </dev/null >/dev/null 2>&1; then
        printf "  %-50s OK\n" "$name"
        : > "$TMPDIR_RUN/ok.$$.$RANDOM"
    else
        printf "  %-50s FAILED\n" "$name"
        : > "$TMPDIR_RUN/fail.$$.$RANDOM"
    fi
}
export -f render_one
export PY OPEN_FLAG TMPDIR_RUN

find examples -name "*.tex" -type f | sort | \
    xargs -n1 -P"$JOBS" -I{} bash -c 'render_one "$@"' _ {}

ok=$(find "$TMPDIR_RUN" -name 'ok.*' 2>/dev/null | wc -l | tr -d ' ')
failed=$(find "$TMPDIR_RUN" -name 'fail.*' 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "Done. ok=$ok failed=$failed (jobs=$JOBS)"
[[ "$failed" -eq 0 ]]

