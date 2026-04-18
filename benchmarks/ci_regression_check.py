#!/usr/bin/env python3
"""CI regression gate for Scriba render performance.

Compares a new benchmark run against a stored baseline JSON.
Exits 1 if any fixture regresses beyond the threshold.

Usage:
    # Capture baseline (run once on main, commit result):
    python benchmarks/bench_render.py --runs 5 --json benchmarks/baseline.json

    # Check in CI:
    python benchmarks/ci_regression_check.py \
        --baseline benchmarks/baseline.json \
        --threshold 0.10

    # Or run bench + check in one step:
    python benchmarks/bench_render.py --runs 5 --json /tmp/current.json
    python benchmarks/ci_regression_check.py \
        --baseline benchmarks/baseline.json \
        --current /tmp/current.json \
        --threshold 0.10
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="Scriba CI regression gate")
    parser.add_argument("--baseline", type=Path, required=True,
                        help="Baseline JSON produced by bench_render.py")
    parser.add_argument("--current", type=Path, default=None,
                        help="Current run JSON (if omitted, runs bench_render.py now)")
    parser.add_argument("--threshold", type=float, default=0.10,
                        help="Max allowed regression fraction (default 0.10 = 10%%)")
    parser.add_argument("--runs", type=int, default=5,
                        help="Number of runs when auto-running the bench")
    args = parser.parse_args()

    if not args.baseline.exists():
        print(f"ERROR: baseline not found: {args.baseline}", file=sys.stderr)
        sys.exit(2)

    if args.current is None:
        tf = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        current_path = Path(tf.name)
        tf.close()
        bench_script = Path(__file__).parent / "bench_render.py"
        ret = subprocess.run(
            [sys.executable, str(bench_script),
             "--runs", str(args.runs),
             "--json", str(current_path)],
            check=False,
        )
        if ret.returncode != 0:
            print("ERROR: bench_render.py failed", file=sys.stderr)
            sys.exit(2)
    else:
        current_path = args.current

    baseline = {r["label"]: r for r in load_json(args.baseline)}
    current = {r["label"]: r for r in load_json(current_path)}

    failures: list[str] = []
    print(f"\n{'Fixture':<28} {'Baseline ms':>12} {'Current ms':>11} {'Delta':>8} {'Status':>8}")
    print("-" * 73)

    for label, cur in current.items():
        if label not in baseline:
            print(f"{label:<28} {'N/A':>12} {cur['median_ms']:>11.0f} {'N/A':>8} {'NEW':>8}")
            continue
        base = baseline[label]
        base_ms = base["median_ms"]
        cur_ms = cur["median_ms"]
        delta = (cur_ms - base_ms) / base_ms if base_ms > 0 else 0.0
        status = "OK"
        if delta > args.threshold:
            status = "FAIL"
            failures.append(
                f"{label}: {base_ms:.0f}ms -> {cur_ms:.0f}ms "
                f"(+{delta*100:.1f}% > {args.threshold*100:.0f}% threshold)"
            )
        elif delta < -0.05:
            status = "FASTER"
        print(f"{label:<28} {base_ms:>12.0f} {cur_ms:>11.0f} {delta*100:>+7.1f}% {status:>8}")

    print()
    if failures:
        print("REGRESSION DETECTED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"All fixtures within {args.threshold*100:.0f}% threshold. OK.")


if __name__ == "__main__":
    main()
