#!/usr/bin/env python3
"""Visual regression compare tool (structural HTML diff).

Usage:
    python compare.py BASELINE.html CANDIDATE.html [--output diff.txt]
                      [--ignore-attrs class,style] [--quiet]

Current implementation: structural-HTML-diff only. Two HTML files are
parsed into DOM trees, normalized (whitespace, attribute order), and
compared node-by-node. Any textual or structural mismatch is reported
to stdout (or ``--output``) and the process exits non-zero.

A future version will add browser-rendered pixel diffs via Playwright.
See ``docs/ops/visual-regression.md`` for the roadmap and
``scripts/visual_regression/README.md`` for the KaTeX-upgrade context.

Exit codes:
    0  identical after normalization
    1  structural or textual differences found
    2  invalid arguments or unreadable input files
"""

from __future__ import annotations

import argparse
import difflib
import html.parser
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Attributes whose order we treat as meaningless.
_STABLE_ATTR_SORT = True

# Elements whose inner whitespace should be preserved verbatim. Scriba's
# output includes <pre> from lstlisting blocks and <script>/<style> from
# the HTML harness.
_PRESERVE_WS_TAGS = frozenset({"pre", "script", "style", "textarea", "code"})


@dataclass
class Node:
    """A minimal normalized DOM node.

    Immutable-ish: we build the tree once, then never mutate it.
    """

    tag: str
    attrs: tuple[tuple[str, str], ...]
    children: list["Node"] = field(default_factory=list)
    text: str = ""
    is_text: bool = False

    def render(self, depth: int = 0) -> Iterable[str]:
        indent = "  " * depth
        if self.is_text:
            yield f"{indent}#text {self.text!r}"
            return
        attr_str = " ".join(f"{k}={v!r}" for k, v in self.attrs)
        yield f"{indent}<{self.tag}{' ' + attr_str if attr_str else ''}>"
        for child in self.children:
            yield from child.render(depth + 1)
        yield f"{indent}</{self.tag}>"


class _NormalizingParser(html.parser.HTMLParser):
    """Build a simplified DOM tree with whitespace normalization."""

    def __init__(self, ignore_attrs: frozenset[str]) -> None:
        super().__init__(convert_charrefs=True)
        self._root = Node(tag="#root", attrs=())
        self._stack: list[Node] = [self._root]
        self._ignore_attrs = ignore_attrs
        # Track whether we're inside a preserve-whitespace element.
        self._preserve_depth = 0

    @property
    def root(self) -> Node:
        return self._root

    def _normalize_attrs(
        self, attrs: list[tuple[str, str | None]]
    ) -> tuple[tuple[str, str], ...]:
        cleaned: list[tuple[str, str]] = []
        for key, value in attrs:
            if key in self._ignore_attrs:
                continue
            cleaned.append((key, value if value is not None else ""))
        if _STABLE_ATTR_SORT:
            cleaned.sort()
        return tuple(cleaned)

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        node = Node(tag=tag, attrs=self._normalize_attrs(attrs))
        self._stack[-1].children.append(node)
        self._stack.append(node)
        if tag in _PRESERVE_WS_TAGS:
            self._preserve_depth += 1

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        node = Node(tag=tag, attrs=self._normalize_attrs(attrs))
        self._stack[-1].children.append(node)
        # self-closing: no stack push.

    def handle_endtag(self, tag: str) -> None:
        if len(self._stack) > 1 and self._stack[-1].tag == tag:
            if tag in _PRESERVE_WS_TAGS:
                self._preserve_depth = max(0, self._preserve_depth - 1)
            self._stack.pop()
        # Silently tolerate mismatched tags; normalization is lossy on
        # purpose and we do not want to bail on slightly dirty HTML.

    def handle_data(self, data: str) -> None:
        if self._preserve_depth > 0:
            text = data
        else:
            text = " ".join(data.split())
        if not text:
            return
        self._stack[-1].children.append(
            Node(tag="#text", attrs=(), text=text, is_text=True)
        )


def parse_html(path: Path, ignore_attrs: frozenset[str]) -> Node:
    """Parse ``path`` into a normalized DOM tree."""
    source = path.read_text(encoding="utf-8", errors="replace")
    parser = _NormalizingParser(ignore_attrs=ignore_attrs)
    parser.feed(source)
    parser.close()
    return parser.root


def render_lines(node: Node) -> list[str]:
    """Produce a stable line-based serialization for diffing."""
    return list(node.render())


def diff_trees(baseline: Node, candidate: Node) -> list[str]:
    """Return a unified diff between two rendered trees."""
    left = render_lines(baseline)
    right = render_lines(candidate)
    return list(
        difflib.unified_diff(
            left,
            right,
            fromfile="baseline",
            tofile="candidate",
            lineterm="",
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compare.py",
        description="Structural HTML regression diff for Scriba output.",
    )
    parser.add_argument("baseline", type=Path, help="path to baseline HTML")
    parser.add_argument("candidate", type=Path, help="path to candidate HTML")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="write diff to this path instead of stdout",
    )
    parser.add_argument(
        "--ignore-attrs",
        default="",
        help="comma-separated list of attribute names to ignore",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress diff body; only set exit code",
    )
    args = parser.parse_args(argv)

    if not args.baseline.is_file():
        print(f"error: baseline not found: {args.baseline}", file=sys.stderr)
        return 2
    if not args.candidate.is_file():
        print(f"error: candidate not found: {args.candidate}", file=sys.stderr)
        return 2

    ignore = frozenset(
        a.strip() for a in args.ignore_attrs.split(",") if a.strip()
    )

    baseline_tree = parse_html(args.baseline, ignore)
    candidate_tree = parse_html(args.candidate, ignore)

    diff = diff_trees(baseline_tree, candidate_tree)
    if not diff:
        if not args.quiet:
            print("compare.py: no structural differences")
        return 0

    body = "\n".join(diff) + "\n"
    if args.output is not None:
        args.output.write_text(body, encoding="utf-8")
        if not args.quiet:
            print(f"compare.py: {len(diff)} diff lines written to {args.output}")
    elif not args.quiet:
        sys.stdout.write(body)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
