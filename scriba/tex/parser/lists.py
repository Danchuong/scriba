"""Itemize and enumerate environments with arbitrary nesting.

See ``docs/scriba/02-tex-plugin.md`` §3 for the HTML output contract.
"""

from __future__ import annotations

import re
from typing import Callable

_UL_OPEN = '<ul class="scriba-tex-list scriba-tex-list-unordered">'
_OL_OPEN = '<ol class="scriba-tex-list scriba-tex-list-ordered">'
_LI_OPEN = '<li class="scriba-tex-list-item">'


def _process_nested_environment(
    text: str, env_name: str, callback: Callable[[str], str]
) -> str:
    """Walk ``\\begin{env}...\\end{env}`` blocks honoring nesting depth."""
    begin_tag = f"\\begin{{{env_name}}}"
    end_tag = f"\\end{{{env_name}}}"

    result_parts: list[str] = []
    pos = 0
    while pos < len(text):
        idx = text.find(begin_tag, pos)
        if idx == -1:
            result_parts.append(text[pos:])
            break
        result_parts.append(text[pos:idx])

        depth = 1
        search_start = idx + len(begin_tag)
        matched = False
        while depth > 0 and search_start < len(text):
            next_begin = text.find(begin_tag, search_start)
            next_end = text.find(end_tag, search_start)
            if next_end == -1:
                break
            if next_begin != -1 and next_begin < next_end:
                depth += 1
                search_start = next_begin + len(begin_tag)
            else:
                depth -= 1
                if depth == 0:
                    content = text[idx + len(begin_tag) : next_end]
                    result_parts.append(callback(content))
                    pos = next_end + len(end_tag)
                    matched = True
                    break
                search_start = next_end + len(end_tag)
        if not matched:
            result_parts.append(begin_tag)
            pos = idx + len(begin_tag)
    return "".join(result_parts)


def _items_to_html(content: str, open_tag: str, close_tag: str) -> str:
    raw_items = re.split(r"\\item\s*", content)
    items = [item.strip() for item in raw_items if item.strip()]
    body = "".join(_LI_OPEN + item + "</li>" for item in items)
    return open_tag + body + close_tag


def _process_itemize(content: str) -> str:
    content = _process_nested_environment(content, "itemize", _process_itemize)
    content = _process_nested_environment(content, "enumerate", _process_enumerate)
    return _items_to_html(content, _UL_OPEN, "</ul>")


def _process_enumerate(content: str) -> str:
    content = _process_nested_environment(content, "itemize", _process_itemize)
    content = _process_nested_environment(content, "enumerate", _process_enumerate)
    return _items_to_html(content, _OL_OPEN, "</ol>")


def apply_lists(text: str) -> str:
    """Expand all ``itemize`` / ``enumerate`` environments to ``<ul>`` / ``<ol>``."""
    text = _process_nested_environment(text, "itemize", _process_itemize)
    text = _process_nested_environment(text, "enumerate", _process_enumerate)
    return text
