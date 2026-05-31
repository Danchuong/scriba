#!/usr/bin/env python3
"""Refresh the golden corpus from the live ``examples/`` tree.

Copies every ``examples/**/*.tex`` that has a sibling rendered ``.html`` into
``tests/golden/examples/corpus/`` (flat — example basenames are unique). Run
this after adding or changing example ``.tex`` files, then re-run the golden
suite to review and accept the new output.

    python tests/golden/examples/sync_corpus.py
    pytest tests/golden/examples/ -v
"""

from __future__ import annotations

import shutil
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CORPUS = _HERE / "corpus"
_EXAMPLES = _HERE.parents[2] / "examples"


def main() -> None:
    _CORPUS.mkdir(parents=True, exist_ok=True)
    pairs = [
        (tex, tex.with_suffix(".html"))
        for tex in sorted(_EXAMPLES.rglob("*.tex"))
        if tex.with_suffix(".html").exists()
    ]
    seen: dict[str, Path] = {}
    for tex, _ in pairs:
        if tex.stem in seen:
            raise SystemExit(
                f"basename collision: {tex} vs {seen[tex.stem]} "
                "— flat corpus requires unique stems"
            )
        seen[tex.stem] = tex

    for tex, html in pairs:
        shutil.copy2(tex, _CORPUS / tex.name)
        shutil.copy2(html, _CORPUS / html.name)
    print(f"synced {len(pairs)} pairs into {_CORPUS.relative_to(_HERE.parents[2])}")


if __name__ == "__main__":
    main()
