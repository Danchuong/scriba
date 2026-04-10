"""Seeded RNG object injected into Starlark during ``\\fastforward``.

The RNG uses Python's ``random.Random`` as the underlying generator,
seeded deterministically so that identical source always produces
byte-identical HTML output.

See ``docs/extensions/fastforward.md`` section 4 for the interface contract.
"""

from __future__ import annotations

import random


class StarlarkRNG:
    """Seeded RNG object injected into Starlark during ``\\fastforward``."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def random(self) -> float:
        """Return a uniform float in [0.0, 1.0)."""
        return self._rng.random()

    def randint(self, lo: int, hi: int) -> int:
        """Return a uniform integer in [lo, hi] inclusive."""
        return self._rng.randint(lo, hi)

    def uniform(self, lo: float, hi: float) -> float:
        """Return a uniform float in [lo, hi)."""
        return self._rng.uniform(lo, hi)

    def shuffle(self, lst: list) -> None:
        """Shuffle *lst* in place."""
        self._rng.shuffle(lst)

    def choice(self, lst: list):
        """Return a random element from *lst*."""
        return self._rng.choice(lst)
