"""Expand ``\\fastforward`` commands into sequential FrameIR objects.

The expansion produces N = floor(total_iters / sample_every) frames.
Each frame gets a narrate_body from the template (or a default) with
iteration-level placeholders.  Actual state changes come from Starlark
callbacks at runtime; at parse time the frames carry empty command tuples.
"""

from __future__ import annotations

from scriba.animation.parser.ast import FastForwardCommand, FastForwardMeta, FrameIR


def expand_fastforward(cmd: FastForwardCommand) -> tuple[FrameIR, ...]:
    """Expand a ``\\fastforward`` command into N sequential FrameIR objects.

    Each frame carries a :class:`FastForwardMeta` so that the renderer can
    run the Starlark ``iterate(scene, rng)`` callback at materialisation
    time and inject real state mutations.
    """
    n_frames = cmd.total_iters // cmd.sample_every
    frames: list[FrameIR] = []
    for k in range(1, n_frames + 1):
        iteration = k * cmd.sample_every
        if cmd.narrate_template is not None:
            narrate = cmd.narrate_template
        else:
            narrate = (
                f"Iteration {iteration} / {cmd.total_iters} "
                f"(frame {k})."
            )
        frames.append(
            FrameIR(
                line=cmd.line,
                commands=(),
                compute=(),
                narrate_body=narrate,
                ff_meta=FastForwardMeta(
                    total_iters=cmd.total_iters,
                    sample_every=cmd.sample_every,
                    seed=cmd.seed,
                    frame_index=k - 1,
                ),
            ),
        )
    return tuple(frames)
