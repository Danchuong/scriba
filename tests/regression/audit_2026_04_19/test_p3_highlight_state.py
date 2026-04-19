"""Regression tests for audit finding P3 — highlight state silently unreachable.

Audit finding: 6 primitives call ``get_state(suffix)`` in their ``emit_svg``
loop instead of ``resolve_effective_state(suffix)``.  The
``resolve_effective_state`` method (defined on ``PrimitiveBase``) is the
single place that promotes an idle cell to ``"highlight"`` when the suffix
is in ``self._highlighted``.  Calling ``get_state`` directly bypasses this
promotion, so ``\\highlight{<cell>}`` has zero visual effect for these
primitives.

Affected primitives and their call-sites:
  - CodePanel   (codepanel.py:212  — ``self.get_state(suffix)``)
  - LinkedList  (linkedlist.py:356 — ``self.get_state(node_suffix)``)
  - HashMap     (hashmap.py:272    — ``self.get_state(suffix)``)
  - VariableWatch (variablewatch.py:272 — ``self.get_state(suffix)``)
  - Queue       (queue.py:290      — ``self.get_state(suffix)``, but line 296
                  has an equivalent inline check — effectively already works)
  - Stack       (stack.py:239      — ``self.get_state(suffix)``, but lines
                  246-254 contain an equivalent inline check — already works)

Fix required: replace each ``self.get_state(suffix)`` in the emit loop
with ``self.resolve_effective_state(suffix)`` (or equivalent inline logic),
so that parts in ``self._highlighted`` render with the CSS class
``scriba-state-highlight``.

Test strategy:
  1. Construct the primitive with relevant data.
  2. Set ``prim._highlighted = {suffix}`` for the target part (mirroring
     what ``_frame_renderer.py:481`` does at runtime).
  3. Call ``prim.emit_svg()``.
  4. Assert that the SVG contains ``class="scriba-state-highlight"``
     associated with the targeted part.

Tests for CodePanel, LinkedList, HashMap, VariableWatch will FAIL today.
Tests for Queue and Stack document the current (passing) behaviour
because those primitives already have equivalent inline highlight logic;
they serve as reference implementations and must remain green after the fix.
"""

from __future__ import annotations

import pytest

from scriba.animation.primitives.codepanel import CodePanel
from scriba.animation.primitives.hashmap import HashMap
from scriba.animation.primitives.linkedlist import LinkedList
from scriba.animation.primitives.queue import Queue
from scriba.animation.primitives.stack import Stack
from scriba.animation.primitives.variablewatch import VariableWatch


# ---------------------------------------------------------------------------
# Shared assertion helper
# ---------------------------------------------------------------------------


def _assert_highlight_class_present(svg: str, target: str, label: str) -> None:
    """Assert that ``scriba-state-highlight`` appears near ``data-target=<target>``."""
    # The emitter wraps each part in a <g data-target="..."> element and sets
    # the class attribute to the state class.  After the fix the class must be
    # ``scriba-state-highlight`` for any part in the highlighted set.
    assert "scriba-state-highlight" in svg, (
        f"{label}: setting _highlighted={{'{target}'}} and calling emit_svg() "
        "must produce SVG containing 'scriba-state-highlight' but it did not.\n"
        "This means resolve_effective_state() is not being used in the emit loop."
    )


# ---------------------------------------------------------------------------
# P3 Tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestCodePanelHighlight:
    """CodePanel.emit_svg() must honour _highlighted for line selectors.

    Bug (codepanel.py:212): the emit loop calls ``self.get_state(suffix)``
    which always returns ``'idle'`` for a highlighted-but-unstated line,
    bypassing the highlight promotion in ``resolve_effective_state``.

    FAILS today; must PASS after the fix.
    """

    def test_highlighted_line_produces_highlight_class(self) -> None:
        """Setting _highlighted={'line[1]'} must produce scriba-state-highlight.

        Covers audit finding P3 for CodePanel (codepanel.py:212).
        """
        prim = CodePanel("cp", {"lines": ["x = 1", "y = 2", "return x + y"]})
        prim._highlighted = {"line[1]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "line[1]", "CodePanel")

    def test_highlighted_middle_line_produces_highlight_class(self) -> None:
        """Highlight works for any line index, not just the first."""
        prim = CodePanel("cp", {"lines": ["a", "b", "c", "d"]})
        prim._highlighted = {"line[3]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "line[3]", "CodePanel")

    def test_non_highlighted_line_stays_idle(self) -> None:
        """Lines NOT in _highlighted must remain ``scriba-state-idle``.

        This ensures the fix does not accidentally highlight every line.
        Must PASS both before and after the fix.
        """
        prim = CodePanel("cp", {"lines": ["x = 1", "y = 2"]})
        prim._highlighted = {"line[1]"}

        svg = prim.emit_svg()

        # line[2] is not highlighted, must appear as idle
        assert "scriba-state-idle" in svg, (
            "CodePanel: at least one line must keep scriba-state-idle when "
            "only line[1] is highlighted."
        )

    def test_highlight_overrides_idle_but_not_active_state(self) -> None:
        """A line with an explicit non-idle state must NOT be overridden by highlight.

        ``resolve_effective_state`` only promotes ``idle`` → ``highlight``.
        A ``current`` or ``active`` state must win.
        """
        prim = CodePanel("cp", {"lines": ["x = 1"]})
        prim.set_state("line[1]", "current")
        prim._highlighted = {"line[1]"}

        svg = prim.emit_svg()

        # The ``current`` state must win over highlight
        assert "scriba-state-current" in svg, (
            "CodePanel: explicit 'current' state must not be overridden by "
            "the highlight promotion."
        )


@pytest.mark.regression
class TestLinkedListHighlight:
    """LinkedList.emit_svg() must honour _highlighted for node selectors.

    Bug (linkedlist.py:356): the emit loop calls ``self.get_state(node_suffix)``
    instead of ``self.resolve_effective_state(node_suffix)``.

    FAILS today; must PASS after the fix.
    """

    def test_highlighted_node_produces_highlight_class(self) -> None:
        """Setting _highlighted={'node[0]'} must produce scriba-state-highlight.

        Covers audit finding P3 for LinkedList (linkedlist.py:356).
        """
        prim = LinkedList("ll", {"data": [10, 20, 30]})
        prim._highlighted = {"node[0]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "node[0]", "LinkedList")

    def test_highlighted_last_node_produces_highlight_class(self) -> None:
        """Highlight works for the last node as well as the first."""
        prim = LinkedList("ll", {"data": [1, 2, 3]})
        prim._highlighted = {"node[2]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "node[2]", "LinkedList")

    def test_non_highlighted_node_stays_idle(self) -> None:
        """Nodes NOT in _highlighted must remain idle after the fix."""
        prim = LinkedList("ll", {"data": [1, 2, 3]})
        prim._highlighted = {"node[0]"}

        svg = prim.emit_svg()

        assert "scriba-state-idle" in svg, (
            "LinkedList: at least one non-highlighted node must remain idle."
        )


@pytest.mark.regression
class TestHashMapHighlight:
    """HashMap.emit_svg() must honour _highlighted for bucket selectors.

    Bug (hashmap.py:272): the emit loop calls ``self.get_state(suffix)``
    instead of ``self.resolve_effective_state(suffix)``.

    FAILS today; must PASS after the fix.
    """

    def test_highlighted_bucket_produces_highlight_class(self) -> None:
        """Setting _highlighted={'bucket[0]'} must produce scriba-state-highlight.

        Covers audit finding P3 for HashMap (hashmap.py:272).
        """
        prim = HashMap("hm", {"capacity": 4})
        prim._highlighted = {"bucket[0]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "bucket[0]", "HashMap")

    def test_highlighted_middle_bucket_produces_highlight_class(self) -> None:
        """Highlight works for bucket[2] in a 4-bucket map."""
        prim = HashMap("hm", {"capacity": 4})
        prim._highlighted = {"bucket[2]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "bucket[2]", "HashMap")

    def test_non_highlighted_bucket_stays_idle(self) -> None:
        """Buckets NOT in _highlighted must stay idle."""
        prim = HashMap("hm", {"capacity": 4})
        prim._highlighted = {"bucket[0]"}

        svg = prim.emit_svg()

        assert "scriba-state-idle" in svg, (
            "HashMap: at least one non-highlighted bucket must remain idle."
        )


@pytest.mark.regression
class TestVariableWatchHighlight:
    """VariableWatch.emit_svg() must honour _highlighted for var selectors.

    Bug (variablewatch.py:272): the emit loop calls ``self.get_state(suffix)``
    instead of ``self.resolve_effective_state(suffix)``.

    FAILS today; must PASS after the fix.
    """

    def test_highlighted_var_produces_highlight_class(self) -> None:
        """Setting _highlighted={'var[x]'} must produce scriba-state-highlight.

        Covers audit finding P3 for VariableWatch (variablewatch.py:272).
        """
        prim = VariableWatch("vw", {"names": ["x", "y", "z"]})
        prim._highlighted = {"var[x]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "var[x]", "VariableWatch")

    def test_highlighted_second_var_produces_highlight_class(self) -> None:
        """Highlight works for ``var[y]`` as well."""
        prim = VariableWatch("vw", {"names": ["x", "y"]})
        prim._highlighted = {"var[y]"}

        svg = prim.emit_svg()

        _assert_highlight_class_present(svg, "var[y]", "VariableWatch")

    def test_non_highlighted_var_stays_idle(self) -> None:
        """Variables NOT in _highlighted must remain idle."""
        prim = VariableWatch("vw", {"names": ["x", "y"]})
        prim._highlighted = {"var[x]"}

        svg = prim.emit_svg()

        assert "scriba-state-idle" in svg, (
            "VariableWatch: at least one non-highlighted var must remain idle."
        )


# ---------------------------------------------------------------------------
# Queue and Stack: already pass due to equivalent inline logic.
# Documented here as reference implementations and non-regression guards.
# ---------------------------------------------------------------------------


@pytest.mark.regression
class TestQueueHighlightAlreadyWorks:
    """Queue already has inline highlight logic (queue.py:296) so this passes.

    Included to document the current behaviour and prevent regression if
    the inline logic is accidentally removed during the P3 fix refactor.
    """

    def test_highlighted_cell_produces_highlight_class(self) -> None:
        """Queue cell[0] in _highlighted renders as scriba-state-highlight.

        This test PASSES today due to queue.py line 296's inline check.
        It must continue to pass after the P3 fix.
        """
        prim = Queue("q", {"capacity": 3, "data": [10, 20, 30]})
        prim._highlighted = {"cell[0]"}

        svg = prim.emit_svg()

        assert "scriba-state-highlight" in svg, (
            "Queue: cell[0] in _highlighted must render as scriba-state-highlight."
        )


@pytest.mark.regression
class TestStackHighlightAlreadyWorks:
    """Stack already has inline highlight logic (stack.py:246-254) so this passes.

    Included to document the current behaviour and prevent regression.
    """

    def test_highlighted_item_produces_highlight_class(self) -> None:
        """Stack item[0] in _highlighted renders as scriba-state-highlight.

        This test PASSES today due to stack.py lines 246-254's inline check.
        It must continue to pass after the P3 fix.
        """
        prim = Stack("s", {"items": ["A", "B", "C"]})
        prim._highlighted = {"item[0]"}

        svg = prim.emit_svg()

        assert "scriba-state-highlight" in svg, (
            "Stack: item[0] in _highlighted must render as scriba-state-highlight."
        )
