"""
Verify the spec rulesets keep valid code-ref + test-ref anchors.

Covers both rule families with one mechanism:
- ``docs/spec/smart-label-ruleset.md`` — the ``R-*`` pill-placement rules.
- ``docs/spec/motion-ruleset.md`` — the ``A-*`` motion rules (how identity-keyed
  stage elements move between two server-authored frames).

Run in CI (wired into pytest via ``tests/doc_coverage/test_ruleset_sync.py`` and
``tests/unit/test_motion_ruleset_sync.py``) to catch drift between the rulesets
and the implementation.

The rule count is a structural invariant, not a hardcoded number (the old
``!= 31`` gate broke the day R-33/R-34 landed and, being wired into no CI,
nobody noticed — which is exactly how the doc drift accumulated): every
``### R-*`` / ``### A-*`` card must carry at least one ``**Code ref:**`` and one
``**Test ref:**``.

Reference anchors come in two forms:
- ``path/to/file.py:symbol`` — the anchor must appear in the file (rot-proof;
  preferred).
- ``path/to/file.py:123`` — legacy line anchor; only checks the line exists.

An anchor that names machinery not yet committed uses the ``pending`` escape
hatch (e.g. ``pending v0.23.0-dev``); such refs are skipped until they flip to a
real ``path:anchor``.

Usage:
    python scripts/check_ruleset_sync.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()

# (ruleset markdown, card-id regex) pairs. Each card is a ``### <ID> — Title``
# heading; the id regex distinguishes the two rule families that share the
# card format and the same code-ref/test-ref contract.
RULESETS: list[tuple[Path, str]] = [
    (REPO_ROOT / "docs/spec/smart-label-ruleset.md", r"R-[0-9]+[a-z]?"),
    (REPO_ROOT / "docs/spec/motion-ruleset.md", r"A-[0-9]+[a-z]?"),
]


def _safe_path(path: str) -> Path | None:
    """Resolve *path* under REPO_ROOT; reject traversal attempts."""
    fp = (REPO_ROOT / path).resolve()
    try:
        fp.relative_to(REPO_ROOT)
    except ValueError:
        return None
    return fp


def _check_code_ref(ref: str) -> str | None:
    """Return an error string for *ref*, or None when it verifies."""
    m = re.match(r"([\w./-]+\.(?:py|md|css|js)):([A-Za-z0-9_.]+)", ref)
    if not m:
        return None  # prose refs without a path:anchor shape are not checked
    path, anchor = m.group(1), m.group(2)
    fp = _safe_path(path)
    if fp is None:
        return f"code-ref path escapes repo root: {ref}"
    if not fp.exists():
        return f"code-ref file missing: {ref}"
    content = fp.read_text(encoding="utf-8")
    if anchor.isdigit():
        if int(anchor) > len(content.splitlines()):
            return (
                f"code-ref lineno out of range: {ref}"
                f" (file has {len(content.splitlines())} lines)"
            )
        return None
    if not re.search(rf"\b{re.escape(anchor)}\b", content):
        return f"code-ref symbol not found in file: {ref}"
    return None


def _check_ruleset(path: Path, id_pat: str) -> int:
    """Check one ruleset file; print an OK/ERROR line and return error count."""
    if not path.exists():
        print(f"ERROR: ruleset file missing: {path.name}")
        return 1

    text = path.read_text(encoding="utf-8")
    cards = list(re.finditer(rf"^### ({id_pat}) — .+$", text, re.MULTILINE))
    if not cards:
        print(f"ERROR: no rule cards found in {path.name}")
        return 1

    errors = 0

    # Structural invariant: every card carries both refs.
    for i, card in enumerate(cards):
        end = cards[i + 1].start() if i + 1 < len(cards) else len(text)
        block = text[card.end():end]
        if "**Code ref:**" not in block:
            print(f"ERROR: {card.group(1)} has no **Code ref:**")
            errors += 1
        if "**Test ref:**" not in block:
            print(f"ERROR: {card.group(1)} has no **Test ref:**")
            errors += 1

    code_refs = re.findall(r"\*\*Code ref:\*\* `([^`]+)`", text)
    test_refs = re.findall(r"\*\*Test ref:\*\* `([^`]+)`", text)

    for ref in code_refs:
        if ref.startswith("pending"):
            continue
        err = _check_code_ref(ref)
        if err:
            print(f"ERROR: {err}")
            errors += 1

    for ref in test_refs:
        if ref.startswith("pending"):
            continue
        m = re.match(r"([\w./-]+)(?:::.+)?", ref)
        if not m:
            continue
        fp = _safe_path(m.group(1))
        if fp is None:
            print(f"ERROR: test-ref path escapes repo root: {ref}")
            errors += 1
            continue
        if not fp.exists():
            print(f"ERROR: test-ref file missing: {ref}")
            errors += 1

    if errors:
        return errors

    pending_code = sum(1 for r in code_refs if r.startswith("pending"))
    pending_test = sum(1 for r in test_refs if r.startswith("pending"))
    print(
        f"OK {path.name}: {len(cards)} rules, {len(code_refs)} code-refs"
        f" ({pending_code} pending), {len(test_refs)} test-refs"
        f" ({pending_test} pending) — structure and anchors verified"
    )
    return 0


def main() -> int:
    errors = sum(_check_ruleset(path, id_pat) for path, id_pat in RULESETS)
    if errors:
        print(f"\n{errors} error(s) found")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
