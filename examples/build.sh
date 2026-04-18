#!/usr/bin/env bash
# Compile all .tex examples to .html
# Usage: ./examples/build.sh [--open]
#
# Output: .html files next to each .tex file
# These are gitignored — treat as build artifacts.

set -euo pipefail
cd "$(dirname "$0")/.."

OPEN_FLAG=""
if [[ "${1:-}" == "--open" ]]; then
    OPEN_FLAG="--open"
fi

count=0
failed=0

while IFS= read -r tex; do
    html="${tex%.tex}.html"
    name="${tex#examples/}"
    printf "  %-50s " "$name"
    if uv run python render.py "$tex" -o "$html" $OPEN_FLAG </dev/null 2>/dev/null; then
        echo "OK"
        count=$((count + 1))
    else
        echo "FAILED"
        failed=$((failed + 1))
    fi
done < <(find examples -name "*.tex" -type f | sort)

echo ""
echo "Done."
