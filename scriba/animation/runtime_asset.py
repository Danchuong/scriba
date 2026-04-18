"""Scriba JS runtime asset loader.

Reads ``scriba.js`` from the package static directory once at import time
and exposes the bytes, SHA-384 (base64), and content-hashed filename.
These are used by ``emitter.py`` when emitting external-runtime mode.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"
_SOURCE_FILENAME = "scriba.js"

# Read the raw JS bytes once at import time.
_js_path = _STATIC_DIR / _SOURCE_FILENAME
RUNTIME_JS_BYTES: bytes = _js_path.read_bytes()

# Compute SHA-384 for SRI integrity attribute.
_sha384_digest = hashlib.sha384(RUNTIME_JS_BYTES).digest()
RUNTIME_JS_SHA384: str = base64.b64encode(_sha384_digest).decode("ascii")

# Content-hashed filename (first 8 hex chars of SHA-384).
_hash8 = hashlib.sha384(RUNTIME_JS_BYTES).hexdigest()[:8]
RUNTIME_JS_FILENAME: str = f"scriba.{_hash8}.js"

__all__ = [
    "RUNTIME_JS_BYTES",
    "RUNTIME_JS_FILENAME",
    "RUNTIME_JS_SHA384",
]
