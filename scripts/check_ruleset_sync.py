"""
Verify docs/spec/smart-label-ruleset.md R-* rules have valid code-ref + test-ref.

Run in CI to catch drift between ruleset and implementation.

Usage:
    python scripts/check_ruleset_sync.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RULESET = Path("docs/spec/smart-label-ruleset.md")
REPO_ROOT = Path(__file__).parent.parent.resolve()


def _safe_path(path: str) -> Path | None:
    """Resolve *path* under REPO_ROOT; reject traversal attempts."""
    fp = (REPO_ROOT / path).resolve()
    try:
        fp.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return fp


def main() -> int:
    text = RULESET.read_text(encoding="utf-8")
    rules = re.findall(r"^### R-(\d+) — (.+)$", text, re.MULTILINE)
    code_refs = re.findall(r"\*\*Code ref:\*\* `([^`]+)`", text)
    test_refs = re.findall(r"\*\*Test ref:\*\* `([^`]+)`", text)

    if len(rules) != 30:
        print(f"ERROR: expected 30 rules, found {len(rules)}")
        return 1

    errors = 0

    for ref in code_refs:
        if ref.startswith("pending"):
            continue
        # Parse "path/to/file.py:lineno" — may have extra description after the lineno
        m = re.match(r"([^:]+):(\d+)", ref)
        if not m:
            continue
        path, lineno = m.group(1), int(m.group(2))
        fp = _safe_path(path)
        if fp is None:
            print(f"ERROR: code-ref path escapes repo root: {ref}")
            errors += 1
            continue
        if not fp.exists():
            print(f"ERROR: code-ref file missing: {ref}")
            errors += 1
            continue
        lines = fp.read_text(encoding="utf-8").splitlines()
        if lineno > len(lines):
            print(
                f"ERROR: code-ref lineno out of range: {ref}"
                f" (file has {len(lines)} lines)"
            )
            errors += 1

    for ref in test_refs:
        if ref.startswith("pending"):
            continue
        # Format "path/to/test.py::ClassName::method" or "path/to/test.py"
        m = re.match(r"([^:]+)(?:::(.+))?", ref)
        if not m:
            continue
        path = m.group(1)
        fp = _safe_path(path)
        if fp is None:
            print(f"ERROR: test-ref path escapes repo root: {ref}")
            errors += 1
            continue
        if not fp.exists():
            print(f"ERROR: test-ref file missing: {ref}")
            errors += 1

    if errors:
        print(f"\n{errors} error(s) found")
        return 1

    pending_code = sum(1 for r in code_refs if r.startswith("pending"))
    pending_test = sum(1 for r in test_refs if r.startswith("pending"))
    print(
        f"OK: {len(rules)} rules, {len(code_refs)} code-refs"
        f" ({pending_code} pending), {len(test_refs)} test-refs"
        f" ({pending_test} pending) — all present files verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
