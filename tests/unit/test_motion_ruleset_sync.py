"""The motion ruleset (A-* cards) stays anchored to real code + tests.

``docs/spec/motion-ruleset.md`` carries the A-rules in the same card format as
the smart-label R-rules, and ``scripts/check_ruleset_sync.py`` now scans both
files with one mechanism: every ``### A-*`` card must carry a ``**Code ref:**``
and a ``**Test ref:**``, symbol anchors are content-verified, test files must
exist, and ``pending`` anchors are honoured until their code lands. This test
holds the motion ruleset green and guards against the file being silently
dropped from the scanner's RULESETS list (which is exactly how the R-ruleset
drift went unnoticed before the guard was wired into CI).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_motion_ruleset_sync_guard_passes() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/check_ruleset_sync.py"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    # The motion ruleset must actually be scanned, not just the smart-label one.
    assert "motion-ruleset.md" in r.stdout, r.stdout + r.stderr
