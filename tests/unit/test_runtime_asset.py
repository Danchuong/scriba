"""Tests for scriba.animation.runtime_asset — Phase 4 (Wave 8).

Verifies that the external JS runtime asset is well-formed, content-hashed,
and produces a stable SHA-384 across multiple imports.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path


def test_runtime_js_file_exists() -> None:
    """The physical scriba.js file must exist in the static directory."""
    static_dir = Path(__file__).parent.parent.parent / "scriba" / "animation" / "static"
    assert (static_dir / "scriba.js").exists(), "scriba.js not found in static/"


def test_runtime_js_bytes_non_empty() -> None:
    from scriba.animation.runtime_asset import RUNTIME_JS_BYTES

    assert isinstance(RUNTIME_JS_BYTES, bytes)
    assert len(RUNTIME_JS_BYTES) > 1000, "scriba.js suspiciously small"


def test_runtime_js_sha384_stable() -> None:
    """SHA-384 must be deterministic and equal to re-computing from bytes."""
    from scriba.animation.runtime_asset import RUNTIME_JS_BYTES, RUNTIME_JS_SHA384

    expected = base64.b64encode(hashlib.sha384(RUNTIME_JS_BYTES).digest()).decode("ascii")
    assert RUNTIME_JS_SHA384 == expected


def test_runtime_js_filename_content_hashed() -> None:
    """Filename must embed the first 8 hex chars of the SHA-384 digest."""
    from scriba.animation.runtime_asset import RUNTIME_JS_BYTES, RUNTIME_JS_FILENAME

    hash8 = hashlib.sha384(RUNTIME_JS_BYTES).hexdigest()[:8]
    assert RUNTIME_JS_FILENAME == f"scriba.{hash8}.js"


def test_runtime_js_sha384_is_base64() -> None:
    """RUNTIME_JS_SHA384 must be a valid base64 string."""
    from scriba.animation.runtime_asset import RUNTIME_JS_SHA384

    decoded = base64.b64decode(RUNTIME_JS_SHA384)
    # SHA-384 produces 48 bytes
    assert len(decoded) == 48


def test_runtime_js_contains_scriba_init() -> None:
    """The runtime JS must contain the main initialiser entry point."""
    from scriba.animation.runtime_asset import RUNTIME_JS_BYTES

    content = RUNTIME_JS_BYTES.decode("utf-8")
    assert "_scribaInit" in content, "runtime missing _scribaInit function"
    assert "scriba-frames-" in content, "runtime missing island ID prefix"
