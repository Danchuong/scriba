#!/usr/bin/env python3
"""Tiny JSON-line echo worker for SubprocessWorker tests.

Protocol: read one JSON object per line from stdin, write one JSON
response per line to stdout.

Recognized request fields:
  - "echo": str   -> response echoes it back as {"echo": <value>}
  - "sleep": float -> the worker sleeps that many seconds before responding
  - "die": true   -> the worker exits with status 1 immediately

On startup the worker writes "fake-worker ready" to stderr so the
SubprocessWorker can wait for the ready_signal.
"""

from __future__ import annotations

import json
import sys
import time


def main() -> int:
    print("fake-worker ready", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"error": "bad-json"}) + "\n")
            sys.stdout.flush()
            continue

        if req.get("die"):
            return 1

        if "sleep" in req:
            try:
                time.sleep(float(req["sleep"]))
            except (TypeError, ValueError):
                pass

        resp = {}
        if "echo" in req:
            resp["echo"] = req["echo"]
        if not resp:
            resp = {"ok": True}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
