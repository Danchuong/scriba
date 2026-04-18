"""Canary tests confirming that eval_raw has been removed (D1, v0.9.0).

Two assertions:
1. ``StarlarkHost`` no longer has an ``eval_raw`` attribute — any attempt
   to call it raises ``AttributeError``.
2. Sending ``{"op": "eval_raw", ...}`` over the wire returns a structured
   ``E1156`` error with a migration hint pointing to ``\\compute{...}``.
"""

from __future__ import annotations

import json

import pytest

from scriba.core.workers import SubprocessWorkerPool
from scriba.animation.starlark_host import StarlarkHost


class TestEvalRawRemoved:
    def test_attribute_does_not_exist(self) -> None:
        """eval_raw must not be an attribute of StarlarkHost."""
        pool = SubprocessWorkerPool()
        try:
            host = StarlarkHost(pool)
            assert not hasattr(host, "eval_raw"), (
                "StarlarkHost.eval_raw still exists; it should have been removed in v0.9.0"
            )
            with pytest.raises(AttributeError):
                host.eval_raw({}, "x = 1")  # type: ignore[attr-defined]
        finally:
            pool.close()

    def test_wire_eval_raw_returns_e1156(self) -> None:
        """Wire-level op='eval_raw' must return E1156 with a migration hint."""
        pool = SubprocessWorkerPool()
        try:
            host = StarlarkHost(pool)
            worker = pool.get("starlark")
            response = worker.send(
                {"op": "eval_raw", "id": "canary-01", "globals": {}, "source": "x = 1"},
                timeout=5.0,
            )
            assert response.get("ok") is False, "expected ok=false for removed op"
            assert response.get("code") == "E1156", (
                f"expected E1156, got {response.get('code')!r}"
            )
            message: str = response.get("message", "")
            assert "eval_raw" in message, f"migration hint missing 'eval_raw': {message!r}"
            assert "compute" in message, f"migration hint missing 'compute': {message!r}"
        finally:
            pool.close()
