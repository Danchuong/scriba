"""value_change targets the VALUE text node, not the first ``<text>``.

Structural fix (0.26.4, JudgeZone report #6): on a name+value row the first
``<text>`` in the ``<g data-target>`` group is the NAME/index label, so the
old runtime ``querySelector('text')`` stamped and throbbed the label — a
``VariableWatch`` ``var[j]`` flashed its value onto the "j" name, then the
fs-snap restored "j" (flash-and-revert).

The renderer now tags the value ``<text>`` with ``data-role="value"`` on the
three affected primitives; the runtime prefers that node and falls back to the
LAST ``<text>``. This module pins the emitted DOM (renderer half) and mirrors
the runtime resolver against it; the JS selector strings themselves are pinned
in ``test_runtime_reverse.py::TestApplyTransitionBranches``.

Audited primitives (rendered, texts in document order):

    VariableWatch var   [name, value]   value LAST   -> AFFECTED (stamped name)
    HashMap bucket      [index, value]  value LAST   -> AFFECTED (stamped index)
    LinkedList node     [value, index]  value FIRST  -> naive last-text fallback
                                                       would grab the index
                                                       caption -> MUST be tagged
    Array/Grid/Queue/Stack/DPTable/Tree/Matrix/Bar/Graph cell/edge  single text
                                                       -> value is the only text
    Equation line       foreignObject (KaTeX)         -> no <text>; throb only
"""

from __future__ import annotations

import re

from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.variablewatch import VariableWatch


def _group(svg: str, target: str) -> str:
    """Extract ``<g data-target="target"> … </g>`` by matching ``<g>``/``</g>``
    (mirrors the runtime's ``stage.querySelector('[data-target=…]')``)."""
    needle = f'data-target="{target}"'
    i = svg.find(needle)
    assert i != -1, f"no data-target={target!r} in svg"
    start = svg.rfind("<g", 0, i)
    depth, j, n = 0, start, len(svg)
    while j < n:
        if svg.startswith("<g", j):
            depth += 1
            j += 2
        elif svg.startswith("</g>", j):
            depth -= 1
            j += 4
            if depth == 0:
                return svg[start:j]
        else:
            j += 1
    return svg[start:]


def _texts(group: str) -> list[str]:
    """All ``<text>`` inner strings in document order (tspans stripped)."""
    return [
        re.sub(r"<[^>]+>", "", m.group(1))
        for m in re.finditer(r"<text\b[^>]*>(.*?)</text>", group, re.DOTALL)
    ]


def _resolve_value_text(group: str) -> str | None:
    """Python mirror of the runtime resolver::

        var txt = el.querySelector('text[data-role="value"]');
        if (!txt) { var ts = el.querySelectorAll('text');
                    txt = ts.length ? ts[ts.length - 1] : null; }
    """
    m = re.search(
        r'<text\b[^>]*data-role="value"[^>]*>(.*?)</text>', group, re.DOTALL
    )
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1))
    ts = _texts(group)
    return ts[-1] if ts else None


# ---------------------------------------------------------------------------
# VariableWatch — name THEN value (the confirmed report #6 repro)
# ---------------------------------------------------------------------------


class TestVariableWatchValueNode:
    def test_value_text_is_tagged_and_resolves(self) -> None:
        w = VariableWatch("w", {"names": ["j"]})
        w.set_value("var[j]", "0")
        grp = _group(w.emit_svg(), "w.var[j]")
        assert 'data-role="value"' in grp
        assert _resolve_value_text(grp) == "0"

    def test_name_text_j_survives_value_stamp(self) -> None:
        # report #6 repro: the value must land on the VALUE node; the "j" name
        # must remain the name node (was overwritten, then reverted, before).
        w = VariableWatch("w", {"names": ["j"]})
        w.set_value("var[j]", "1")
        grp = _group(w.emit_svg(), "w.var[j]")
        texts = _texts(grp)
        assert texts[0] == "j", "the NAME is the FIRST <text> (why 'text' was wrong)"
        assert texts[-1] == "1", "the value is the LAST <text>"
        assert _resolve_value_text(grp) == "1"
        assert 'data-role="name"' in grp, "the name text is self-described too"


# ---------------------------------------------------------------------------
# HashMap — index THEN value
# ---------------------------------------------------------------------------


class TestHashMapValueNode:
    def test_value_tagged_index_is_first_text(self) -> None:
        hm = HashMap("hm", {"capacity": 4})
        hm.set_value("bucket[0]", "cat:3")
        grp = _group(hm.emit_svg(), "hm.bucket[0]")
        texts = _texts(grp)
        assert texts[0] == "0", "bucket index is the FIRST text (the old mis-target)"
        assert texts[-1] == "cat:3", "the bucket value is the LAST text"
        assert 'data-role="value"' in grp
        assert _resolve_value_text(grp) == "cat:3"


# ---------------------------------------------------------------------------
# LinkedList — value FIRST, index caption LAST (the fallback hazard)
# ---------------------------------------------------------------------------


class TestLinkedListValueNode:
    def test_tag_beats_last_text_fallback(self) -> None:
        ll = LinkedList("ll", {"data": [3, 7]})
        ll.set_value("node[0]", "9")
        grp = _group(ll.emit_svg(), "ll.node[0]")
        texts = _texts(grp)
        # value FIRST, "node[0]" index caption LAST — a naive last-text
        # fallback would grab the caption, so the value carries the tag.
        assert texts[0] == "9"
        assert texts[-1] == "node[0]"
        assert 'data-role="value"' in grp
        assert _resolve_value_text(grp) == "9", (
            "the tag must win over last-text; last-text here is the index caption"
        )


# ---------------------------------------------------------------------------
# Resolver fallback contract (untagged / synthetic groups)
# ---------------------------------------------------------------------------


class TestResolverFallback:
    def test_untagged_name_then_value_resolves_last(self) -> None:
        # an affected primitive rendered WITHOUT data-role (value is last):
        # the last-text fallback recovers the value.
        grp = '<g data-target="x"><text>name</text><text>VAL</text></g>'
        assert _resolve_value_text(grp) == "VAL"

    def test_untagged_single_text_resolves_it(self) -> None:
        grp = '<g data-target="x"><text>ONLY</text></g>'
        assert _resolve_value_text(grp) == "ONLY"

    def test_tag_overrides_value_first_layout(self) -> None:
        # value-first layout: last-text WOULD be wrong; the tag fixes it.
        grp = (
            '<g data-target="x">'
            '<text data-role="value">VAL</text><text>idx</text></g>'
        )
        assert _resolve_value_text(grp) == "VAL"

    def test_no_text_yields_none(self) -> None:
        # Equation lines are foreignObject (KaTeX) — no <text> to stamp.
        grp = '<g data-target="x"><foreignObject><div>a=b</div></foreignObject></g>'
        assert _resolve_value_text(grp) is None
