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
