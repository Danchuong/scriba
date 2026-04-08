"""DiagramEngine Protocol and DiagramEngineOutput dataclass.

See ``docs/scriba/03-diagram-plugin.md`` §Public API for the locked shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class DiagramEngine(Protocol):
    """Protocol for diagram rendering engines.

    Implementations produce SVG plus a per-step element mapping. The
    reference implementation for 0.3 is :class:`D2Engine`; a future
    ``MermaidEngine`` will satisfy the same protocol.
    """

    name: str  # e.g. "d2", "mermaid"

    def render(self, source: str, theme: str) -> "DiagramEngineOutput":
        """Render ``source`` and return SVG plus per-step element mapping."""
        ...


@dataclass(frozen=True)
class DiagramEngineOutput:
    """Result of a single diagram render.

    Attributes:
        svg: The master SVG markup with ``data-step="N"`` attributes
            stamped on every element that belongs to a step.
        frame_elements: Mapping of ``step_number -> set[element_id]``.
        total_steps: ``1`` for a static diagram, N for an N-step walkthrough.
    """

    svg: str
    frame_elements: dict[int, set[str]]
    total_steps: int
