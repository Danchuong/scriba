"""Shared type aliases for scriba core and sub-packages."""

from __future__ import annotations

from typing import Dict, List, Union

# Recursive JSON-value type alias.  Use this instead of ``dict[str, Any]``
# wherever the value is provably loaded from / destined for JSON
# (``json.loads``, ``json.dumps``, wire-protocol response dicts).
JsonValue = Union[None, bool, int, float, str, List["JsonValue"], Dict[str, "JsonValue"]]

__all__ = ["JsonValue"]
