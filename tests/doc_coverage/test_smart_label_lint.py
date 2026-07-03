"""Hold scripts/lint_smart_label.py at ZERO violations.

The linter encodes the smart-label forbidden-pattern contract (§5.3
FP-1..FP-6). It sat in advisory mode wired into nothing while 11
violations accumulated; the 2026-07-03 fp2/fp56/fp3 campaign cleared the
backlog (dispatcher route-through, unified content registries, constant
consolidation) with two documented ``@allow_forbidden_pattern``
suppressions. This gate fails the moment a NEW violation is introduced —
fix it or suppress it explicitly with a rationale.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CEILING = 0  # backlog fully cleared 2026-07-03 — hold at zero


def test_lint_error_count_does_not_grow() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/lint_smart_label.py"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    out = r.stdout + r.stderr
    if "no violations found" in out:
        count = 0
    else:
        m = re.search(r"lint_smart_label: (\d+) error", out)
        assert m, f"could not parse linter output:\n{out}"
        count = int(m.group(1))
    assert count <= _CEILING, (
        f"{count} forbidden-pattern violations (ceiling {_CEILING}) — a new "
        "one was introduced; fix it or add an explicit "
        "@allow_forbidden_pattern with rationale"
    )
