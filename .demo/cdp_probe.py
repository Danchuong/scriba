"""Drive Chrome via CDP to inspect the graph animation frame-by-frame.

Launches headless Chrome with remote debugging, loads the rendered HTML,
steps Next through every frame, screenshots each, and extracts node/edge
geometry from the live SVG to flag layout problems (overlap, off-canvas).
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path

import websocket  # websocket-client

HERE = Path(__file__).parent
import sys as _sys
URL = f"file://{HERE / (_sys.argv[1] if len(_sys.argv)>1 else 'graph_edge.html')}"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9222


def launch_chrome() -> subprocess.Popen:
    return subprocess.Popen(
        [
            CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
            "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--window-size=900,700", "--hide-scrollbars",
            "--remote-allow-origins=*",
            "--user-data-dir=/tmp/cdp_graph_probe",
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def ws_url() -> str:
    for _ in range(50):
        try:
            data = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            pages = [t for t in data if t["type"] == "page"]
            if pages:
                return pages[0]["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError("no CDP page target")


class CDP:
    def __init__(self, url: str):
        self.ws = websocket.create_connection(url, max_size=None)
        self._id = 0

    def cmd(self, method: str, **params):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})

    def evaluate(self, expr: str):
        r = self.cmd(
            "Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True
        )
        return r.get("result", {}).get("value")

    def shot(self, path: Path):
        r = self.cmd("Page.captureScreenshot", format="png")
        import base64
        path.write_bytes(base64.b64decode(r["data"]))


# JS run in-page: pull node centers + edge endpoints from the LIVE stage SVG.
PROBE_JS = r"""
(() => {
  const svg = document.querySelector('.scriba-stage .scriba-stage-svg')
            || document.querySelector('.scriba-stage-svg');
  if (!svg) return {error: 'no live stage svg'};
  const vb = svg.getAttribute('viewBox');
  const nodes = [...svg.querySelectorAll('[data-target^="G.node"]')].map(g => {
    const c = g.querySelector('circle');
    const t = g.querySelector('text');
    return {
      id: g.getAttribute('data-target'),
      cx: c ? +c.getAttribute('cx') : null,
      cy: c ? +c.getAttribute('cy') : null,
      r:  c ? +c.getAttribute('r')  : null,
      label: t ? t.textContent : null,
      cls: g.getAttribute('class'),
    };
  });
  const edges = [...svg.querySelectorAll('[data-target^="G.edge"]')].map(g => {
    const l = g.querySelector('line') || g.querySelector('path');
    return {
      id: g.getAttribute('data-target'),
      x1: l && l.getAttribute('x1'), y1: l && l.getAttribute('y1'),
      x2: l && l.getAttribute('x2'), y2: l && l.getAttribute('y2'),
      cls: g.getAttribute('class'),
    };
  });
  const weights = [...svg.querySelectorAll('text')]
      .map(t => t.textContent).filter(s => /^\d+$/.test(s));
  const counter = document.querySelector('.scriba-step-counter');
  return {viewBox: vb, step: counter && counter.textContent,
          nodes, edges, weightTexts: weights};
})()
"""


def main():
    proc = launch_chrome()
    try:
        cdp = CDP(ws_url())
        cdp.cmd("Page.enable")
        cdp.cmd("Runtime.enable")
        cdp.cmd("Page.navigate", url=URL)
        time.sleep(1.2)
        for step in range(4):
            time.sleep(0.5)
            info = cdp.evaluate(PROBE_JS)
            cdp.shot(HERE / f"graph_step{step}.png")
            print(f"\n=== STEP {step} ({info.get('step')}) viewBox={info.get('viewBox')}")
            for n in info.get("nodes", []):
                print(f"  node {n['label']!s:3} @({n['cx']},{n['cy']}) r={n['r']} {n['cls']}")
            for e in info.get("edges", []):
                print(f"  edge {e['id']} ({e['x1']},{e['y1']})->({e['x2']},{e['y2']}) {e['cls']}")
            print(f"  weight texts on stage: {info.get('weightTexts')}")
            # advance
            cdp.evaluate("document.querySelector('.scriba-btn-next')?.click()")
        print("\nscreenshots: .demo/graph_step0..3.png")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
