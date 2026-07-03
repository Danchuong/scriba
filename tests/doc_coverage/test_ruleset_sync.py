"""The smart-label ruleset sync guard runs green — permanently wired.

scripts/check_ruleset_sync.py existed but was referenced by no CI or test,
so it silently broke (hardcoded rule count) the day R-33/R-34 landed — and
with it went the only mechanism that could have caught the ~10 rotted
code-refs and stale constants the spec accumulated. The guard is now
structural (every R-* card must carry code+test refs; symbol anchors are
verified against file content) and this test holds it green forever.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_ruleset_sync_guard_passes() -> None:
    r = subprocess.run(
        [sys.executable, "scripts/check_ruleset_sync.py"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
