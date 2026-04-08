"""Hard limits enforced by TexRenderer / math extraction.

See packages/scriba/CHANGELOG.md 0.1.1-alpha for the rationale.
"""

from __future__ import annotations

import pytest

from scriba import ValidationError


def test_max_math_items_exceeded(pipeline, ctx):
    # Each "$x$ " becomes one inline math item (the trailing space
    # prevents the double-dollar regex from collapsing adjacent pairs).
    src = "$x$ " * 501
    with pytest.raises(ValidationError):
        pipeline.render(src, ctx)


def test_max_math_items_at_cap_ok(pipeline, ctx):
    # Just under the cap should still parse (math worker may fail to
    # render in CI without node — that's caught and escaped; the cap
    # check happens before worker dispatch).
    src = "$x$ " * 500
    doc = pipeline.render(src, ctx)
    assert doc.html


def test_max_source_size_exceeded(pipeline, ctx):
    src = "a" * (1_048_576 + 1)
    with pytest.raises(ValidationError):
        pipeline.render(src, ctx)
