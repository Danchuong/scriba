"""D2Engine — DiagramEngine implementation backed by the D2 CLI.

See ``docs/scriba/03-diagram-plugin.md`` §Public API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from scriba.core.workers import SubprocessWorkerPool
from scriba.diagram.engine import DiagramEngineOutput


class D2Engine:
    """`DiagramEngine` implementation backed by the D2 CLI.

    Registers a :class:`SubprocessWorker` named ``"d2"`` into the supplied
    :class:`SubprocessWorkerPool` on construction.
    """

    name: str = "d2"

    def __init__(
        self,
        worker_pool: SubprocessWorkerPool,
        *,
        d2_binary: str | Path = "d2",
        theme: Literal[
            "default",
            "neutral-default",
            "neutral-grey",
            "dark-mauve",
            "flagship-terrastruct",
            "cool-classics",
            "mixed-berry-blue",
            "grape-soda",
            "aubergine",
            "colorblind-clear",
            "vanilla-nitro-cola",
            "orange-creamsicle",
            "shirley-temple",
            "earth-tones",
            "everglade-green",
            "buttered-toast",
            "terminal",
            "terminal-grayscale",
            "origami",
            "c4",
        ] = "default",
        layout_engine: Literal["dagre", "elk"] = "dagre",
        pad: int = 20,
        sketch: bool = False,
        timeout: float = 15.0,
    ) -> None:
        """Configure the D2 engine. See ``03-diagram-plugin.md`` §Public API."""
        raise NotImplementedError

    def render(self, source: str, theme: str) -> DiagramEngineOutput:
        """See :meth:`DiagramEngine.render`."""
        raise NotImplementedError
