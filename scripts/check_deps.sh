#!/usr/bin/env bash
# Check Scriba's Python dependencies for known CVEs.
#
# Tries `uv pip audit` first (if the uv plugin is available), then falls
# back to a direct `pip-audit` invocation. If neither is installed,
# prints an install hint and exits non-zero so CI jobs fail loudly.
#
# Usage:
#   scripts/check_deps.sh

set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  if uv pip audit --help >/dev/null 2>&1; then
    exec uv pip audit "$@"
  fi
fi

if command -v pip-audit >/dev/null 2>&1; then
  exec pip-audit "$@"
fi

cat >&2 <<'EOF'
scripts/check_deps.sh: neither `uv pip audit` nor `pip-audit` is available.

Install pip-audit, e.g.:

    uv tool install pip-audit
    # or
    pipx install pip-audit

Then re-run this script.
EOF
exit 1
