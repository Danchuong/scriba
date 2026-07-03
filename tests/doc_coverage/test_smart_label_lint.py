"""Ratchet on scripts/lint_smart_label.py ERROR count.

The linter encodes the smart-label forbidden-pattern contract (§5.3
FP-1..FP-6) but runs in advisory mode and was wired into nothing. Eleven
violations exist today — a mix of design-intended patterns awaiting
``@allow_forbidden_pattern`` suppressions and at least one genuine bypass
(R-30 NumberLine). Forcing zero would block legitimate patterns; retiring
the linter loses the signal. This ratchet fails only when a NEW violation
is introduced; lower the ceiling as the backlog clears.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CEILING = 3  # FP-6 route-through cleared 8 (2026-07-03); remaining: graph FP-2, plane2d FP-2/FP-3


def test_lint_error_count_does_not_grow() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/lint_smart_label.py"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    m = re.search(r"lint_smart_label: (\d+) error", r.stdout + r.stderr)
    assert m, f"could not parse linter output:\n{r.stdout}{r.stderr}"
    count = int(m.group(1))
    assert count <= _CEILING, (
        f"{count} forbidden-pattern violations (ceiling {_CEILING}) — a new "
        "one was introduced; fix it or add an explicit "
        "@allow_forbidden_pattern with rationale"
    )
