"""Regression tests for the Wave 8 centering audit.

The audit identified four distinct CSS-side defects that caused text
inside rect-based primitives to drift off-center:

    A. ``.scriba-index-label`` had no CSS rule at all; index labels on
       Array/Grid/DPTable fell through to SVG defaults.
    B. ``.scriba-primitive-label`` used ``text-anchor: start`` while
       Python emitters passed ``center_x`` as the x coordinate; captions
       drifted right by half their width.
    C. ``[data-primitive="..."] > [data-target] > text`` used a strict
       child combinator that broke when ArrayPrimitive wraps its content
       in ``<g transform="translate(...)">`` for annotation headroom.
    D. The CSS used ``dominant-baseline: middle`` while the Python inline
       callers used ``dominant-baseline: central``; the two are NOT
       equivalent and caused 1-3 px cross-primitive drift.

These tests pin the CSS contract so future regressions fail loudly.
Every assertion reads the shipped stylesheet verbatim — no rendering,
no browser. This makes the tests fast, deterministic, and independent
of font metrics.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_CSS_PATH = (
    Path(__file__).parent.parent.parent
    / "scriba"
    / "animation"
    / "static"
    / "scriba-scene-primitives.css"
)


@pytest.fixture(scope="module")
def css_text() -> str:
    return _CSS_PATH.read_text()


def _find_rule_block(css: str, selector_substring: str) -> str | None:
    """Return the declaration block for the first rule whose selector
    list contains *selector_substring*, or ``None`` if not found.

    The returned string is the content between the first ``{`` and the
    matching ``}``. Comment blocks are ignored.
    """
    # Strip /* ... */ comments to avoid false matches inside explanations.
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # Walk rule-by-rule: selector(s) up to the next ``{``, then the block.
    pos = 0
    while pos < len(stripped):
        brace = stripped.find("{", pos)
        if brace == -1:
            return None
        selector = stripped[pos:brace]
        if selector_substring in selector:
            end = stripped.find("}", brace)
            if end == -1:
                return None
            return stripped[brace + 1 : end]
        # Skip past this rule (find matching close brace)
        depth = 1
        i = brace + 1
        while i < len(stripped) and depth > 0:
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
            i += 1
        pos = i


# ---------------------------------------------------------------------------
# Bug A — ``.scriba-index-label`` must have its own CSS rule
# ---------------------------------------------------------------------------


class TestIndexLabelCentering:
    def test_index_label_rule_exists(self, css_text: str) -> None:
        """The ``.scriba-index-label`` class must have an explicit rule.

        Before Wave 8, this class was referenced by Array/DPTable but had
        no CSS rule at all, so labels fell through to SVG defaults
        (``text-anchor: start, dominant-baseline: alphabetic``) and
        visibly drifted right and high.
        """
        block = _find_rule_block(css_text, ".scriba-index-label")
        assert block is not None, (
            ".scriba-index-label has no CSS rule — Array/DPTable index "
            "labels will fall through to SVG defaults and appear shifted "
            "right + high. See Wave 8 audit Bug A."
        )

    def test_index_label_is_middle_anchored(self, css_text: str) -> None:
        block = _find_rule_block(css_text, ".scriba-index-label")
        assert block is not None
        assert "text-anchor:" in block and "middle" in block, (
            ".scriba-index-label must use text-anchor: middle so the label "
            "centers on the cell's horizontal midpoint that the Python "
            "emitter passes as the x coordinate."
        )

    def test_index_label_hangs_below_baseline(self, css_text: str) -> None:
        """Index labels sit BELOW the cell, so ``hanging`` places the top
        of the glyphs at the y coordinate rather than the alphabetic
        baseline."""
        block = _find_rule_block(css_text, ".scriba-index-label")
        assert block is not None
        assert "dominant-baseline:" in block and "hanging" in block, (
            ".scriba-index-label must use dominant-baseline: hanging so "
            "the label sits below the line passed as y rather than "
            "dipping below it."
        )


# ---------------------------------------------------------------------------
# Bug B — ``.scriba-primitive-label`` must be middle-anchored
# ---------------------------------------------------------------------------


class TestPrimitiveLabelCentering:
    def test_primitive_label_uses_middle_anchor(self, css_text: str) -> None:
        """Caption labels must be middle-anchored because Array/Grid/DPTable
        pass ``center_x`` (total_width // 2) as the x coordinate. Before
        Wave 8, the rule used ``text-anchor: start`` and captions drifted
        right by half their width.
        """
        block = _find_rule_block(css_text, ".scriba-primitive-label")
        assert block is not None, (
            ".scriba-primitive-label rule missing from the stylesheet."
        )
        # Check that text-anchor is middle (not start)
        anchor_match = re.search(r"text-anchor\s*:\s*([a-z]+)", block)
        assert anchor_match is not None, (
            ".scriba-primitive-label has no text-anchor declaration."
        )
        assert anchor_match.group(1) == "middle", (
            f".scriba-primitive-label uses text-anchor: "
            f"{anchor_match.group(1)} but every Python caller passes "
            "center_x as the x coordinate (array.py:259-277). "
            "Wave 8 audit Bug B."
        )


# ---------------------------------------------------------------------------
# Bug C — selector must tolerate intermediate wrappers
# ---------------------------------------------------------------------------


class TestCellTextSelectorRobustness:
    def test_array_cell_text_uses_descendant_combinator(
        self, css_text: str
    ) -> None:
        """The outer combinator between [data-primitive="array"] and
        [data-target] in the cell TEXT rule MUST be a descendant combinator
        (space), not a strict child (>), because ArrayPrimitive wraps its
        content in ``<g transform="translate(...)">`` when annotations need
        headroom (array.py:161-163). A strict child combinator would break
        the centering chain in that case.

        The inner combinator between [data-target] and text can stay as
        ``>`` because the cell's <text> is always a direct child of the
        data-target group.

        The cell RECT rule at lines 276-283 can keep ``>`` because it is
        shadowed by the per-state rules at lines 133+ (``.scriba-state-idle
        > rect``) which are class-based and unaffected by wrappers.
        """
        stripped = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
        for prim in ("array", "grid", "dptable"):
            # Scope specifically to the cell-text rule by requiring
            # ``[data-target] > text`` at the tail.
            pattern = re.compile(
                rf'\[data-primitive="{prim}"\]\s*([>\s])\s*\[data-target\]\s*>\s*text',
            )
            matches = list(pattern.finditer(stripped))
            assert matches, (
                f"Cell text selector for {prim!r} missing from CSS."
            )
            for match in matches:
                combinator = match.group(1).strip()
                assert combinator != ">", (
                    f"Cell text selector for data-primitive={prim!r} uses "
                    f"strict child combinator (>). This breaks when Array "
                    f"wraps content in <g transform> for annotation "
                    f"headroom. Wave 8 audit Bug C."
                )


# ---------------------------------------------------------------------------
# Bug D — dominant-baseline consistency between CSS and inline callers
# ---------------------------------------------------------------------------


class TestDominantBaselineConsistency:
    def test_cell_text_uses_central_not_middle(self, css_text: str) -> None:
        """Python inline callers (Stack/Queue/HashMap/LinkedList/Matrix) all
        pass ``dominant_baseline="central"``. The CSS rule for Array/Grid/
        DPTable must use the same value so cells centered via CSS visually
        match cells centered via inline style.

        ``middle`` aligns to the font's x-height midline while ``central``
        aligns to the em-box geometric center — they differ by 1-3 px in
        most browsers.
        """
        # Find the cell-text rule block — it's the first rule that sets
        # ``pointer-events: none`` after the selector list mentions both
        # ``[data-primitive="array"]`` and ``[data-target]``.
        stripped = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
        # Match the rule header we added: three selectors separated by
        # commas, each ending in ``[data-target] > text``.
        header = re.search(
            r'\[data-primitive="array"\][^{]*\[data-target\]\s*>\s*text[^{]*\{([^}]*)\}',
            stripped,
        )
        assert header is not None, (
            "Could not locate the Array/Grid/DPTable cell-text rule."
        )
        block = header.group(1)
        baseline = re.search(r"dominant-baseline\s*:\s*([a-z-]+)", block)
        assert baseline is not None, (
            "Cell-text rule has no dominant-baseline declaration."
        )
        assert baseline.group(1) == "central", (
            f"Cell-text rule uses dominant-baseline: {baseline.group(1)} "
            "but inline callers use 'central'. Wave 8 audit Bug D."
        )


# ---------------------------------------------------------------------------
# Bug cross-check — every CSS class referenced by a rect-based primitive
# must have a matching rule somewhere in the stylesheet.
# ---------------------------------------------------------------------------


class TestEveryReferencedClassHasCSS:
    """Grep the Python emitters for ``css_class=`` arguments and verify
    every class name lands somewhere in the stylesheet. Guards against a
    repeat of Bug A where a class name was referenced but never styled.
    """

    _PRIMITIVE_PY_DIR = (
        Path(__file__).parent.parent.parent / "scriba" / "animation" / "primitives"
    )

    def _collect_css_class_refs(self) -> set[str]:
        refs: set[str] = set()
        for py in self._PRIMITIVE_PY_DIR.glob("*.py"):
            text = py.read_text()
            for match in re.finditer(
                r'css_class\s*=\s*["\']([^"\']*)["\']', text
            ):
                for klass in match.group(1).split():
                    if klass.startswith("scriba-"):
                        refs.add(klass)
        return refs

    def test_all_scriba_classes_have_rules(self, css_text: str) -> None:
        referenced = self._collect_css_class_refs()
        stripped = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
        missing: list[str] = []
        for klass in sorted(referenced):
            if f".{klass}" not in stripped:
                missing.append(klass)
        assert not missing, (
            f"Primitives reference {len(missing)} CSS class(es) that have "
            f"no rule in scriba-scene-primitives.css: {missing}. "
            "See Wave 8 audit Bug A for the .scriba-index-label reference case."
        )
