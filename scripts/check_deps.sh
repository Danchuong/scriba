#!/usr/bin/env bash
# Check Scriba's Python dependencies for known CVEs.
#
# Tries `uv pip audit` first (if the uv plugin is available), then falls
# back to a direct `pip-audit` invocation. If neither is installed, we
# finally fall back to `uv run --with pip-audit pip-audit` so a fresh
# checkout can still run the scan without an explicit tool install.
#
# Usage:
#   scripts/check_deps.sh                   # human-readable output to stdout
#   scripts/check_deps.sh --json            # structured JSON to stdout
#   scripts/check_deps.sh --json --out P    # structured JSON to file P
#   scripts/check_deps.sh --out P           # human-readable output to file P
#
# Flags are forwarded to the underlying audit tool after being stripped
# of the wrapper-only options above. Any remaining flag is passed through
# unmodified, so e.g. `scripts/check_deps.sh --strict` works.
#
# Exit codes:
#   0  no advisories found (clean)
#   1  advisories found
#   2  no audit tool available (pip-audit / uv pip audit / uv run fallback)
#
# Note: pip-audit historically exits 1 for any non-clean scan regardless
# of severity. We preserve that behaviour and only remap "tool missing"
# to exit code 2.

set -euo pipefail

WANT_JSON=0
OUT_PATH=""
PASSTHROUGH=()

while (($# > 0)); do
  case "$1" in
    --json)
      WANT_JSON=1
      shift
      ;;
    --out)
      if (($# < 2)); then
        echo "scripts/check_deps.sh: --out requires a path" >&2
        exit 2
      fi
      OUT_PATH="$2"
      shift 2
      ;;
    --out=*)
      OUT_PATH="${1#--out=}"
      shift
      ;;
    --help|-h)
      sed -n '1,30p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      PASSTHROUGH+=("$1")
      shift
      ;;
  esac
done

if ((WANT_JSON == 1)); then
  PASSTHROUGH+=(--format json)
fi

# Pick the best available audit backend. `cmd` is an array so we can
# splice in flags without re-parsing.
#
# Order of preference:
#   1. `uv pip audit` — native uv plugin, audits the active uv venv.
#   2. `uv run --with pip-audit pip-audit` — runs pip-audit inside the
#      project's uv venv so the scan targets Scriba's resolved deps.
#      This is deliberately preferred over a bare `pip-audit` on PATH,
#      because a globally installed pip-audit would audit its own
#      tool environment instead of Scriba's, producing false negatives.
#   3. Bare `pip-audit` on PATH — fallback for environments without uv.
cmd=()

if command -v uv >/dev/null 2>&1; then
  if uv pip audit --help >/dev/null 2>&1; then
    cmd=(uv pip audit)
  else
    cmd=(uv run --with pip-audit pip-audit)
  fi
fi

if ((${#cmd[@]} == 0)) && command -v pip-audit >/dev/null 2>&1; then
  cmd=(pip-audit)
fi

if ((${#cmd[@]} == 0)); then
  cat >&2 <<'EOF'
scripts/check_deps.sh: no audit tool available.

Install pip-audit, e.g.:

    uv tool install pip-audit
    # or
    pipx install pip-audit

Then re-run this script. Exit code: 2.
EOF
  exit 2
fi

# Run the scan, capturing stdout so we can route it to --out if needed.
# We intentionally do not capture stderr — errors should still surface
# immediately.
set +e
if [[ -n "$OUT_PATH" ]]; then
  "${cmd[@]}" ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"} > "$OUT_PATH"
  rc=$?
else
  "${cmd[@]}" ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}
  rc=$?
fi
set -e

# Normalize exit codes. pip-audit returns 1 for any advisory. We keep
# that behaviour. If the underlying tool returned >1 because it failed
# to run at all, map to 2 so CI can distinguish "broken tool" from
# "advisory present".
case "$rc" in
  0|1) exit "$rc" ;;
  *)   exit 2 ;;
esac
