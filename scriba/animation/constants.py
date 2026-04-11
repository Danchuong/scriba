"""Centralized constants for the Scriba animation system."""

# Valid state names for \recolor and \cursor
VALID_STATES = frozenset({
    "idle", "current", "done", "dim", "error", "good", "highlight", "path"
})

# Valid annotation colors
VALID_ANNOTATION_COLORS = frozenset({
    "info", "warn", "good", "error", "muted", "path"
})

# Valid annotation positions
VALID_ANNOTATION_POSITIONS = frozenset({
    "above", "below", "left", "right", "inside"
})

# Valid animation option keys
VALID_OPTION_KEYS = frozenset({
    "width", "height", "id", "label", "layout", "grid"
})

# Valid substory option keys
VALID_SUBSTORY_OPTION_KEYS = frozenset({
    "title", "id"
})

DEFAULT_STATE = "idle"

assert DEFAULT_STATE in VALID_STATES, (
    f"DEFAULT_STATE {DEFAULT_STATE!r} not in VALID_STATES"
)

# ---------------------------------------------------------------------------
# Starlark security sets
# ---------------------------------------------------------------------------

# Blocked attribute names (sandbox escape vectors)
BLOCKED_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "__class__",
        "__subclasses__",
        "__bases__",
        "__mro__",
        "__globals__",
        "__builtins__",
        "__import__",
        "__code__",
        "__func__",
        "__dict__",
        "__reduce__",
        "__reduce_ex__",
        "__init_subclass__",
    }
)

# Forbidden AST node types (imported as types in starlark_worker.py)
# Note: actual tuple of ast node types is constructed in starlark_worker.py
# since ast types are not plain strings.

# Forbidden builtins
FORBIDDEN_BUILTINS: frozenset[str] = frozenset(
    {
        "exec",
        "eval",
        "__import__",
        "open",
        "compile",
        "globals",
        "locals",
        "vars",
        "dir",
        "getattr",
        "setattr",
        "delattr",
        "type",
        "object",
        "super",
        "classmethod",
        "staticmethod",
        "property",
        "breakpoint",
        "exit",
        "quit",
        "help",
        "input",
        "memoryview",
        "bytearray",
        "bytes",
    }
)
