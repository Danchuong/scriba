"""Regression tests for nested dict parameter values.

Covers Wave 5.1 Fix 2: ``\\apply{ll}{insert={index=0, value=42}}`` —
parameter values of the form ``{k=v, ...}`` should parse as nested
dicts rather than raising ``E1005`` on the ``{`` token.  This is the
idiomatic way to pass structured payloads to primitives like LinkedList
whose ``apply_command`` accepts ``insert={"index": i, "value": v}``.
"""

from __future__ import annotations

import pytest

from scriba.animation.parser.grammar import (
    ApplyCommand,
    SceneParser,
)


@pytest.fixture()
def parser() -> SceneParser:
    return SceneParser()


@pytest.mark.unit
class TestNestedDictParamValue:
    def test_linkedlist_insert_nested_dict(self, parser: SceneParser) -> None:
        src = (
            "\\shape{ll}{LinkedList}{values=[1,2,3]}\n"
            "\\step\n"
            "\\apply{ll}{insert={index=0, value=42}}\n"
        )
        ir = parser.parse(src)
        cmds = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ]
        assert len(cmds) == 1
        insert = cmds[0].params.get("insert")
        assert isinstance(insert, dict)
        assert insert == {"index": 0, "value": 42}

    def test_nested_dict_mixed_types(self, parser: SceneParser) -> None:
        src = (
            "\\shape{s}{Stack}{size=5}\n"
            "\\step\n"
            "\\apply{s}{push={label=\"top\", value=3.14}}\n"
        )
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        push = cmd.params["push"]
        assert isinstance(push, dict)
        assert push["label"] == "top"
        assert push["value"] == pytest.approx(3.14)

    def test_nested_dict_alongside_scalar(self, parser: SceneParser) -> None:
        """Scalar and dict params can mix inside one brace."""
        src = (
            "\\shape{ll}{LinkedList}{values=[1]}\n"
            "\\step\n"
            "\\apply{ll}{insert={index=0, value=7}, label=\"hi\"}\n"
        )
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        assert cmd.params["label"] == "hi"
        assert cmd.params["insert"] == {"index": 0, "value": 7}

    def test_empty_nested_dict(self, parser: SceneParser) -> None:
        src = (
            "\\shape{s}{Stack}{size=3}\n"
            "\\step\n"
            "\\apply{s}{push={}}\n"
        )
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        assert cmd.params["push"] == {}

    def test_deeply_nested_dict(self, parser: SceneParser) -> None:
        """Nested dicts can themselves contain nested dicts."""
        src = (
            "\\shape{s}{Array}{size=3}\n"
            "\\step\n"
            "\\apply{s}{meta={inner={x=1, y=2}, name=\"ok\"}}\n"
        )
        ir = parser.parse(src)
        cmd = [
            c for f in ir.frames for c in f.commands if isinstance(c, ApplyCommand)
        ][0]
        meta = cmd.params["meta"]
        assert isinstance(meta, dict)
        assert meta["name"] == "ok"
        assert meta["inner"] == {"x": 1, "y": 2}
