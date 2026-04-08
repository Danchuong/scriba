"""6 validator tests per docs/scriba/02-tex-plugin.md §10.

These hit ``TexRenderer.validate()`` directly because ``validate`` is not
part of the ``Renderer`` Protocol and ``Pipeline`` does not expose it.
Error-message assertions use substring match (see PHASE2_DECISIONS.md D-08).
"""

from __future__ import annotations


def test_validate_balanced_dollars(tex_renderer):
    ok, msg = tex_renderer.validate("a $x$ b $$y$$ c")
    assert ok is True
    assert msg is None


def test_validate_odd_dollar_count(tex_renderer):
    ok, msg = tex_renderer.validate("a $x b $$y$$ c")
    assert ok is False
    assert msg is not None
    assert "$" in msg


def test_validate_unmatched_brace(tex_renderer):
    ok, msg = tex_renderer.validate(r"\textbf{hello")
    assert ok is False
    assert msg is not None
    assert "{" in msg or "brace" in msg.lower()


def test_validate_unknown_environment(tex_renderer):
    ok, msg = tex_renderer.validate(r"\begin{unknownenv}x\end{unknownenv}")
    assert ok is False
    assert msg is not None
    assert "environment" in msg.lower() or "unknownenv" in msg


def test_validate_mismatched_begin_end(tex_renderer):
    ok, msg = tex_renderer.validate(r"\begin{itemize}\item A\end{enumerate}")
    assert ok is False
    assert msg is not None
    assert r"\end" in msg or "match" in msg.lower()


def test_validate_empty_input(tex_renderer):
    ok, msg = tex_renderer.validate("")
    assert ok is True
    assert msg is None
