#!/usr/bin/env python3
"""Scriba render benchmark suite — Wave 8 P6 baseline.

Runs render.render_file() on small/medium/large fixtures and reports
median wall-clock time (ms), output bytes, and (where measurable)
subprocess worker overhead via monkey-patching.

Usage:
    python benchmarks/bench_render.py
    python benchmarks/bench_render.py --runs 5
    python benchmarks/bench_render.py --json results.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

# Ensure repo root is on the path when invoked from the repo root.
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import render as render_module  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Fixture catalogue
# ---------------------------------------------------------------------------

FIXTURES: list[dict] = [
    {
        "label": "tiny-nomath",
        "path": "examples/fixes/05_diagram_prescan.tex",
        "tier": "small",
        "has_math": False,
        "has_starlark": False,
    },
    {
        "label": "small-math",
        "path": "examples/fixes/01_variablewatch_shrink.tex",
        "tier": "small",
        "has_math": True,
        "has_starlark": True,
    },
    {
        "label": "medium-tutorial",
        "path": "examples/tutorial_en.tex",
        "tier": "medium",
        "has_math": True,
        "has_starlark": True,
    },
    {
        "label": "large-dinic",
        "path": "examples/dinic.tex",
        "tier": "large",
        "has_math": True,
        "has_starlark": True,
    },
    {
        "label": "large-bfs-editorial",
        "path": "examples/editorials/bfs_grid_editorial.tex",
        "tier": "large",
        "has_math": True,
        "has_starlark": True,
    },
]


class BenchResult(NamedTuple):
    label: str
    tier: str
    has_math: bool
    has_starlark: bool
    source_bytes: int
    output_bytes: int
    times_ms: list[float]
    median_ms: float
    min_ms: float
    worker_send_count: int  # number of subprocess worker.send() calls
    worker_total_ms: float  # total time spent in worker.send() calls


def _patch_workers(pool):
    """Monkey-patch SubprocessWorkerPool.get() to wrap worker.send() and
    accumulate call count + total elapsed time into the pool object."""
    pool._bench_send_count = 0
    pool._bench_send_ms = 0.0

    original_get = pool.get

    def patched_get(name):
        worker = original_get(name)
        if not getattr(worker, "_bench_patched", False):
            original_send = worker.send

            def timed_send(request, *, timeout=None):
                t0 = time.monotonic()
                result = original_send(request, timeout=timeout)
                pool._bench_send_ms += (time.monotonic() - t0) * 1000
                pool._bench_send_count += 1
                return result

            worker.send = timed_send
            worker._bench_patched = True
        return worker

    pool.get = patched_get
    return pool


def run_one(fixture: dict, runs: int = 5) -> BenchResult:
    """Run a single fixture *runs* times and return aggregated stats."""
    from scriba.core.workers import SubprocessWorkerPool
    from scriba.animation.renderer import AnimationRenderer
    from scriba.animation.starlark_host import StarlarkHost
    from scriba.core.css_bundler import inline_katex_css, load_css

    fixture_path = REPO_ROOT / fixture["path"]
    source_bytes = fixture_path.stat().st_size

    times_ms: list[float] = []
    last_output_bytes = 0
    last_send_count = 0
    last_send_ms = 0.0

    for _ in range(runs):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tf:
            out_path = Path(tf.name)

        try:
            t0 = time.monotonic()
            render_module.render_file(fixture_path, out_path)
            elapsed_ms = (time.monotonic() - t0) * 1000
            times_ms.append(elapsed_ms)
            last_output_bytes = out_path.stat().st_size
        finally:
            out_path.unlink(missing_ok=True)

    return BenchResult(
        label=fixture["label"],
        tier=fixture["tier"],
        has_math=fixture["has_math"],
        has_starlark=fixture["has_starlark"],
        source_bytes=source_bytes,
        output_bytes=last_output_bytes,
        times_ms=times_ms,
        median_ms=statistics.median(times_ms),
        min_ms=min(times_ms),
        worker_send_count=last_send_count,
        worker_total_ms=last_send_ms,
    )


def main():
    parser = argparse.ArgumentParser(description="Scriba render benchmarks")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    results: list[BenchResult] = []
    for fixture in FIXTURES:
        path = REPO_ROOT / fixture["path"]
        if not path.exists():
            print(f"  [SKIP] {fixture['label']} — file not found: {path}")
            continue
        print(f"  Benchmarking {fixture['label']} ({args.runs} runs)...", end="", flush=True)
        r = run_one(fixture, runs=args.runs)
        results.append(r)
        print(f" {r.median_ms:.0f} ms (min {r.min_ms:.0f} ms)")

    print()
    print(f"{'Fixture':<28} {'Tier':<8} {'Math':<6} {'Star':<6} "
          f"{'SrcKB':>6} {'OutKB':>7} {'Median ms':>10} {'Min ms':>8}")
    print("-" * 95)
    for r in results:
        print(
            f"{r.label:<28} {r.tier:<8} {'Y' if r.has_math else 'N':<6} "
            f"{'Y' if r.has_starlark else 'N':<6} "
            f"{r.source_bytes/1024:>6.1f} {r.output_bytes/1024:>7.1f} "
            f"{r.median_ms:>10.0f} {r.min_ms:>8.0f}"
        )

    if args.json:
        out = [
            {
                "label": r.label,
                "tier": r.tier,
                "has_math": r.has_math,
                "has_starlark": r.has_starlark,
                "source_bytes": r.source_bytes,
                "output_bytes": r.output_bytes,
                "times_ms": r.times_ms,
                "median_ms": r.median_ms,
                "min_ms": r.min_ms,
            }
            for r in results
        ]
        args.json.write_text(json.dumps(out, indent=2))
        print(f"\nJSON results -> {args.json}")


if __name__ == "__main__":
    main()
