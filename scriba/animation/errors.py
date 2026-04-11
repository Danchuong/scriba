"""Animation-specific error codes (E1001 -- E1505).

These extend :mod:`scriba.core.errors` with animation domain codes.

Error code organisation
-----------------------
The catalog is grouped by subsystem:

* ``E1001``--``E1099`` — detection / structural (lexer, frame)
* ``E1050``--``E1059`` — diagram mode (reserved for future diagram work)
* ``E1100``--``E1149`` — parser / general command validation
* ``E1150``--``E1179`` — Starlark sandbox and ``\\foreach``
* ``E1180``--``E1199`` — frame / cursor limits
* ``E1360``--``E1369`` — substory
* ``E1400``--``E1459`` — primitive parameter validation (new Wave 2 split;
  was historically mega-bucket ``E1103``)
* ``E1460``--``E1469`` — Plane2D
* ``E1480``--``E1489`` — MetricPlot
* ``E1500``--``E1509`` — graph layout

The 1400-block was introduced in v0.5.1 to replace the ``E1103`` catch-all
with one code per (primitive, validation). ``E1103`` itself is retained as
a documented deprecated alias so that downstream code catching it continues
to work.
"""

from __future__ import annotations

from typing import Iterable

from scriba.core.errors import RendererError, ValidationError


# ---------------------------------------------------------------------------
# Fuzzy-match suggestion helper
# ---------------------------------------------------------------------------


def suggest_closest(
    needle: str,
    candidates: Iterable[str],
    *,
    cutoff: float = 0.6,
) -> str | None:
    """Return the closest candidate for *needle*, or ``None`` if none are close.

    Uses a simple Levenshtein-style ``difflib`` match. Kept intentionally
    tiny — just enough to print "did you mean: X?" hints for parser and
    validation errors across the codebase.

    Parameters
    ----------
    needle:
        The (likely typo-ed) string to look up.
    candidates:
        An iterable of valid candidate strings to compare against.
    cutoff:
        Minimum similarity ratio (0.0–1.0) required to return a match.
        Defaults to ``0.6`` to match :mod:`difflib` defaults.
    """
    import difflib

    close = difflib.get_close_matches(needle, list(candidates), n=1, cutoff=cutoff)
    return close[0] if close else None


# ---------------------------------------------------------------------------
# Animation error base class
# ---------------------------------------------------------------------------


class AnimationError(ValidationError):
    """Base class for all animation-specific errors.

    Inherits from :class:`ValidationError` so that existing ``except
    ValidationError`` handlers continue to work while also allowing callers
    to do ``except AnimationError`` for animation-only errors.
    """


# ---------------------------------------------------------------------------
# Comprehensive error code catalog
# ---------------------------------------------------------------------------

ERROR_CATALOG: dict[str, str] = {
    # --- Detection / structural errors (E1001 -- E1099) ---
    "E1001": (
        "Unclosed \\begin{animation} or unbalanced braces/strings/"
        "interpolation. Fix: Check for matching \\end{animation} and "
        "balanced braces."
    ),
    "E1003": "Nested \\begin{animation} or \\begin{diagram} detected.",
    "E1004": "Unknown environment or substory option key.",
    "E1005": "Invalid option or parameter value.",
    "E1006": (
        "Unknown backslash command. Fix: Check command spelling. Valid "
        "commands: \\shape, \\compute, \\step, \\narrate, \\apply, "
        "\\highlight, \\recolor, \\annotate, \\reannotate, \\cursor, "
        "\\foreach, \\substory."
    ),
    "E1007": "Expected opening brace '{' after command.",
    "E1009": "Selector parse error (general).",
    "E1010": "Selector parse error: expected number, identifier, or specific character.",
    "E1011": "Unterminated string literal in selector.",
    "E1012": "Unexpected token kind (expected a different token type).",
    "E1013": "Source exceeds maximum size limit (1 MB).",
    # --- Diagram-specific errors (E1050 -- E1059) ---
    # reserved: diagram mode (not production-ready; raised only via lexer E1003
    # / parser E1050-E1056 once diagram mode ships. Catalog documents the
    # contract ahead of time so downstream tooling stays stable.)
    "E1050": "\\step is not allowed inside a diagram environment.",
    "E1051": "\\shape must appear before the first \\step.",
    "E1052": "Trailing text after \\step on the same line.",
    "E1053": "\\highlight is not allowed in the prelude (before any \\step).",
    "E1054": "\\narrate is not allowed inside a diagram environment.",
    "E1055": "Duplicate \\narrate in the same step.",
    "E1056": "\\narrate must be inside a \\step block.",
    # --- Parse errors (E1100 -- E1149) ---
    # reserved: E1100 is the generic parse-failure bucket surfaced by
    # `AnimationParseError`. Kept in catalog so that `except AnimationError`
    # handlers can still name the category even when no specific code applies.
    "E1100": "General parse failure inside animation body.",
    "E1102": (
        "Unknown primitive type in \\shape declaration. Fix: Check "
        "primitive type spelling. Valid types: Array, Grid, DPTable, "
        "Graph, Tree, NumberLine, Matrix, Heatmap, Stack, Plane2D, "
        "MetricPlot, CodePanel, HashMap, LinkedList, Queue, VariableWatch."
    ),
    "E1103": (
        "Primitive parameter validation error (DEPRECATED mega-bucket; "
        "new code should use the specific E14xx codes below). Retained "
        "for backward compat — still raised by annotation-per-frame "
        "cap and by some legacy call sites. The detail message identifies "
        "the specific primitive and constraint."
    ),
    "E1109": "Invalid \\recolor state or missing required state/color parameter.",
    "E1112": "Unknown annotation position.",
    "E1113": "Invalid or missing annotation color.",
    "E1114": (
        "Unknown keyword parameter for shape primitive. "
        "Fix: Check the parameter name against the primitive's accepted "
        "kwargs; a fuzzy 'did you mean' suggestion is included when a "
        "close match exists."
    ),
    # --- Starlark sandbox errors (E1150 -- E1179) ---
    "E1150": "Starlark parse/syntax error.",
    "E1151": "Starlark runtime evaluation failure.",
    "E1152": "Starlark evaluation timed out.",
    "E1153": "Starlark execution step count exceeded.",
    "E1154": "Starlark forbidden construct (import, while, class, lambda, etc.).",
    "E1155": "Starlark memory limit exceeded.",
    # --- Foreach errors (E1170 -- E1179) ---
    "E1170": "\\foreach nesting depth exceeds maximum (3).",
    "E1171": "\\foreach with empty body.",
    "E1172": (
        "Unclosed \\foreach, forbidden command inside \\foreach, or "
        "\\endforeach without matching \\foreach."
    ),
    "E1173": (
        "\\foreach iterable validation failure (invalid variable, "
        "binding not found, length exceeded, etc.)."
    ),
    # --- Frame / cursor errors (E1180 -- E1199) ---
    "E1180": (
        "Animation has >30 frames (warning) or \\cursor requires at "
        "least one target."
    ),
    "E1181": (
        "Animation has >100 frames (hard limit) or \\cursor requires "
        "an index parameter."
    ),
    "E1182": "Invalid \\cursor prev_state or curr_state value.",
    # --- Substory errors (E1360 -- E1369) ---
    "E1360": "Substory nesting depth exceeds maximum.",
    "E1361": "Unclosed \\substory (missing \\endsubstory).",
    "E1362": "\\substory must be inside a \\step block.",
    "E1365": "\\endsubstory without matching \\substory.",
    # reserved: E1366 ships as a warning (UserWarning subclass) via
    # grammar.py rather than as a raised exception. Catalog entry keeps
    # the message aligned so docs-sync tooling can render it.
    "E1366": "Substory with zero steps (warning).",
    "E1368": "Non-whitespace text on same line as \\substory or \\endsubstory.",
    # --- Primitive parameter validation (E1400 -- E1459) ---
    # Wave 2 split of the legacy E1103 mega-bucket. Allocation is one
    # contiguous sub-range per primitive so future fixes can extend in-place
    # without colliding.
    #
    # E1400-E1409: Array (size, data length)
    "E1400": (
        "Array requires 'size' or 'n' parameter. "
        "hint: add size=N where 1 <= N <= 10000."
    ),
    "E1401": (
        "Array 'size' parameter out of range; must be an integer "
        "between 1 and 10000 inclusive."
    ),
    "E1402": (
        "Array 'data' length does not match 'size'. "
        "hint: either drop 'data' (cells default to empty) or make "
        "len(data) == size."
    ),
    # E1410-E1419: Grid (rows, cols, data length)
    "E1410": (
        "Grid requires both 'rows' and 'cols' parameters. "
        "hint: use rows=R, cols=C where 1 <= R,C <= 500."
    ),
    "E1411": (
        "Grid 'rows'/'cols' parameter out of range; each must be an "
        "integer between 1 and 500 inclusive."
    ),
    "E1412": (
        "Grid 'data' length does not match rows*cols. "
        "hint: supply a flat list of length rows*cols or a 2D list "
        "with R rows each of length C."
    ),
    # E1420-E1429: Matrix and DPTable (rows, cols, cell cap, data length)
    "E1420": (
        "Matrix requires 'rows' and 'cols' parameters. "
        "hint: Matrix{name}{rows=R, cols=C}."
    ),
    "E1421": (
        "Matrix 'rows'/'cols' parameter out of range; each must be a "
        "positive integer."
    ),
    "E1422": (
        "Matrix 'data' length does not match rows*cols. "
        "hint: supply a flat list of length rows*cols or a 2D list "
        "with R rows each of length C."
    ),
    "E1425": (
        "Matrix/DPTable cell count exceeds maximum. "
        "hint: rows*cols must be <= 250000."
    ),
    "E1426": (
        "DPTable requires 'n' (1D) or both 'rows' and 'cols' (2D). "
        "hint: DPTable{name}{n=10} or DPTable{name}{rows=5, cols=5}."
    ),
    "E1427": (
        "DPTable 'n' parameter out of range; must be a positive integer."
    ),
    "E1428": (
        "DPTable 'rows'/'cols' parameter out of range; each must be a "
        "positive integer."
    ),
    "E1429": (
        "DPTable 'data' length does not match expected size. "
        "hint: len(data) must equal n (1D) or rows*cols (2D)."
    ),
    # E1430-E1439: Tree variants
    "E1430": (
        "Tree requires 'root' parameter. "
        "hint: Tree{name}{root=\"A\", nodes=[...], edges=[...]}."
    ),
    "E1431": (
        "Tree (kind=segtree) requires 'data' parameter. "
        "hint: supply data=[v0, v1, v2, ...] of leaf values."
    ),
    "E1432": (
        "Tree (kind=sparse_segtree) requires 'range_lo' and 'range_hi' "
        "parameters. hint: specify the valid index bounds."
    ),
    # E1440-E1449: Queue and Stack
    "E1440": (
        "Queue 'capacity' parameter out of range; must be a positive "
        "integer."
    ),
    "E1441": (
        "Stack 'max_visible' parameter out of range; must be a "
        "positive integer."
    ),
    # E1450-E1459: HashMap and NumberLine
    "E1450": (
        "HashMap requires a 'capacity' parameter. "
        "hint: HashMap{name}{capacity=N} where N >= 1."
    ),
    "E1451": (
        "HashMap 'capacity' parameter out of range; must be a "
        "positive integer."
    ),
    "E1452": (
        "NumberLine requires a 'domain' parameter. "
        "hint: NumberLine{name}{domain=[min, max]}."
    ),
    "E1453": (
        "NumberLine 'domain' must be a two-element [min, max] list."
    ),
    "E1454": (
        "NumberLine 'ticks' parameter out of range; must be <= 1000."
    ),
    # --- Plane2D errors (E1460 -- E1469) ---
    "E1460": "Degenerate viewport (xrange or yrange has equal endpoints).",
    # reserved: E1461-E1463 currently surface only as logger warnings from
    # the Plane2D draw pipeline. Retained in catalog as the documented
    # contract once strict mode is wired.
    "E1461": "Degenerate or out-of-viewport line geometry.",
    "E1462": "Polygon not closed (auto-closing applied).",
    "E1463": "Point is outside viewport bounds.",
    "E1465": "Invalid aspect value (must be 'equal' or 'auto').",
    # reserved: E1466 logged when the element cap is reached; not raised.
    "E1466": "Plane2D element cap reached.",
    # --- Graph primitive errors (E1470 -- E1479) ---
    "E1470": (
        "Graph requires a non-empty 'nodes' list. "
        "hint: Graph{name}{nodes=[...], edges=[...]}."
    ),
    # --- MetricPlot errors (E1480 -- E1489) ---
    "E1480": "MetricPlot requires at least one series.",
    "E1481": "MetricPlot series validation failure.",
    "E1483": "MetricPlot series exceeded maximum point count (hard limit).",
    "E1484": "Log scale: non-positive value clamped.",
    "E1485": "MetricPlot series data validation error.",
    "E1486": "Degenerate xrange in MetricPlot.",
    "E1487": "Same-axis series must share the same scale.",
    # --- Graph layout errors (E1500 -- E1505) ---
    # reserved: E1500-E1504 surface only as logger warnings from the stable
    # graph layout; E1505 is raised from graph_layout_stable.py. Catalog keeps
    # the contract visible.
    "E1500": "Graph layout convergence warning (objective too high).",
    "E1501": "Too many nodes for stable layout (falling back to force layout).",
    "E1502": "Too many frames for stable layout (falling back to force layout).",
    "E1503": "Stable layout fallback triggered.",
    "E1504": "layout_lambda out of valid range (clamped).",
    "E1505": "Invalid seed (must be non-negative integer).",
}


# ---------------------------------------------------------------------------
# Detection errors (E1001 -- E1099)
# ---------------------------------------------------------------------------


class UnclosedAnimationError(AnimationError):
    """E1001: ``\\begin{animation}`` without matching ``\\end{animation}``."""

    code = "E1001"

    def __init__(self, position: int) -> None:
        super().__init__(
            "unclosed \\begin{animation}",
            position=position,
            code=self.code,
        )


class NestedAnimationError(AnimationError):
    """E1003: nested ``\\begin{animation}`` detected."""

    code = "E1003"

    def __init__(self, position: int) -> None:
        super().__init__(
            "nested \\begin{animation}",
            position=position,
            code=self.code,
        )


# ---------------------------------------------------------------------------
# Primitive error factory
# ---------------------------------------------------------------------------

# ``E1103`` is the legacy mega-bucket primitive code. Retained as a
# public constant so existing imports (``from scriba.animation.errors
# import E1103``) do not break. Prefer the specific E14xx codes above
# for new raise sites.
E1103 = "E1103"


def animation_error(
    code: str,
    detail: str,
    *,
    line: int | None = None,
    col: int | None = None,
    hint: str | None = None,
    source_line: str | None = None,
) -> AnimationError:
    """Create an :class:`AnimationError` with structured location fields.

    Parameters
    ----------
    code:
        The E-code string (e.g. ``"E1420"``). Call sites should reference
        the catalog block for their subsystem before picking a new code.
    detail:
        The human-readable message. Gold standard is "<offending value>;
        valid: <range-or-set>; <optional suggestion>".
    line, col:
        Optional 1-indexed source location. When available the raise
        site should thread these through so the rendered error includes
        ``at line N, col M``.
    hint:
        Optional short actionable suggestion displayed under
        ``hint:`` in the rendered error.
    source_line:
        Optional raw source line (without trailing newline). When
        supplied the rendered error includes a carat pointer under the
        offending column.

    Notes
    -----
    Historically the factory accepted only ``(code, detail)``. The new
    keyword-only location arguments default to ``None`` so every existing
    call site remains valid.
    """
    return AnimationError(
        detail,
        code=code,
        line=line,
        col=col,
        hint=hint,
        source_line=source_line,
    )


# ---------------------------------------------------------------------------
# Parse errors (E1100 -- E1149)
# ---------------------------------------------------------------------------


class AnimationParseError(AnimationError):
    """E1100: general parse failure inside animation body."""

    code = "E1100"


# ---------------------------------------------------------------------------
# Scene errors (E1150 -- E1199)
# ---------------------------------------------------------------------------


class FrameCountWarning(UserWarning):
    """E1180: animation has >30 frames (warning, not an exception).

    Inherits from :class:`UserWarning` so it can be caught by
    ``warnings.catch_warnings()`` and ``warnings.filterwarnings()``.

    Visibility
    ----------
    This warning is surfaced via ``warnings.warn()`` from
    ``scriba.animation.parser.grammar``. End users only see it if they
    have not silenced ``UserWarning`` globally. The CLI (``render.py``)
    enables default warning filters so the message appears on stderr;
    library consumers that swallow warnings will miss it. A future
    enhancement could promote it to an explicit ``warnings_collector`` on
    ``RenderContext`` — tracked as follow-up in Wave 3.
    """

    code = "E1180"


class FrameCountError(RendererError):
    """E1181: animation has >100 frames (hard limit)."""

    code = "E1181"

    def __init__(self, count: int) -> None:
        super().__init__(
            f"animation has {count} frames, exceeding the 100-frame limit",
            renderer="animation",
            code=self.code,
        )


# ---------------------------------------------------------------------------
# Starlark errors (E1150 -- E1179)
# ---------------------------------------------------------------------------


class StarlarkEvalError(RendererError):
    """E1151: Starlark evaluation failure (runtime error)."""

    code = "E1151"

    def __init__(self, detail: str) -> None:
        super().__init__(
            f"Starlark evaluation error: {detail}",
            renderer="animation",
            code=self.code,
        )


# ---------------------------------------------------------------------------
# Helpers for Wave 3 migrations
# ---------------------------------------------------------------------------


def format_compute_traceback(tb_text: str) -> str:
    """Filter a Python traceback down to the user's ``\\compute{...}`` frames.

    The Starlark host currently returns the full CPython traceback with
    ``"<compute>"`` substrings marking user frames. Users are confused
    by the interleaved ``File "/path/to/starlark_worker.py"`` lines that
    describe Scriba internals. This helper strips every frame that is
    *not* inside a ``<compute>`` pseudo-file and keeps the trailing
    exception header.

    Currently unused. Cluster 1 owns ``starlark_worker.py`` and will
    migrate the raw-traceback assembly to call this helper in a follow-up
    change — the function lives here so the migration is a one-liner.

    Parameters
    ----------
    tb_text:
        Raw traceback text (output of ``traceback.format_exc()`` or
        equivalent) as returned by the worker subprocess.

    Returns
    -------
    str
        A filtered traceback. If no ``<compute>`` frames are found the
        input is returned unchanged so callers never lose information.
    """
    lines = tb_text.splitlines()
    kept: list[str] = []
    skip_next = False
    for idx, line in enumerate(lines):
        if skip_next:
            # Drop the source-code line that follows a ``File "..."`` entry.
            skip_next = False
            continue
        stripped = line.strip()
        if stripped.startswith("File "):
            if "<compute>" in stripped:
                kept.append(line)
            else:
                skip_next = True
            continue
        if stripped.startswith("Traceback"):
            kept.append(line)
            continue
        # Exception header or any other trailing line — always keep.
        kept.append(line)

    # If filtering produced nothing useful, return original so callers
    # never lose error context.
    if not any("<compute>" in line for line in kept):
        return tb_text
    return "\n".join(kept)


def validation_error_from_selector(
    message: str,
    *,
    position: int,
    source_line_offset: int = 0,
    code: str = "E1009",
    line: int | None = None,
) -> ValidationError:
    """Convert a selector parser ``position`` into a :class:`ValidationError`
    with a proper ``col`` field.

    The selector parser in ``scriba.animation.parser.selectors`` tracks a
    byte offset within the selector text (e.g. ``position=7`` inside
    ``"a.cell[X]"``). That offset is *not* the same as the source
    column — the column needs to be shifted by wherever the selector
    string begins on its source line.

    Parameters
    ----------
    message:
        The raw human-readable failure message.
    position:
        Byte offset inside the selector text (0-indexed) where parsing
        failed.
    source_line_offset:
        Column in the full source line where the selector text begins.
        Defaults to ``0`` so stand-alone callers still get a reasonable
        column estimate.
    code:
        The ``E101x`` error code to attach. Defaults to the generic
        ``E1009``.
    line:
        Optional 1-indexed source line.

    Returns
    -------
    ValidationError
        A :class:`ValidationError` with ``col`` set to
        ``source_line_offset + position`` so the renderer can point at
        the exact failing character.

    Notes
    -----
    Currently unused. Wave 3 will migrate
    ``scriba/animation/parser/selectors.py`` to call this helper when
    propagating errors out of the selector grammar. The helper lives
    here so the migration is a one-liner.
    """
    return ValidationError(
        message,
        code=code,
        position=position,
        line=line,
        col=source_line_offset + position,
    )
