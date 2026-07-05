"""\\substory parent-shape mutations persist into subsequent parent frames
(docs/SCRIBA-TEX-REFERENCE.md:670). Guards against a regression that would
re-isolate the substory scope — the contract is documented AND relied upon by
a committed golden (interval_dp.tex:82,89), yet cmd_substory_state_persist.expect
only checks exit ``ok``, never the persisted content. This test locks the
content. See investigations/verify-substory-leak.md (defect REFUTED; this is
the hygiene deliverable).

Mode note: render.py's default is the interactive widget, whose frames are
``scriba-stage`` <div>s with substory frames nested in ``scriba-substory``
divs (no ``<li class="scriba-frame">``). The helper classifies stages by
substory-div nesting depth and asserts on the last parent-timeline (depth-0)
stage.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from render import render_file


def _last_parent_stage(html: str, target: str) -> dict | None:
    """Return {'val','state'} for ``target`` in the last substory-depth-0 stage."""

    class P(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.sub = 0
            self.stk = []
            self.instage = False
            self.cur = None
            self.incell = False
            self.intext = False
            self.res = []

        def handle_starttag(self, t, at):
            a = dict(at)
            c = a.get("class", "")
            if t == "div":
                is_sub = "scriba-substory" in c and all(
                    x not in c for x in ("container", "controls", "widget")
                )
                self.stk.append(is_sub)
                self.sub += is_sub
            if t == "svg" and "scriba-stage" in c:
                self.instage = True
                self.cur = {"depth": self.sub, "val": None, "state": None}
            if self.instage and t == "g" and a.get("data-target") == target:
                self.incell = True
                self.cur["state"] = c
            if self.incell and t == "text":
                self.intext = True

        def handle_endtag(self, t):
            if t == "text":
                self.intext = False
            if t == "g" and self.incell:
                self.incell = False
            if t == "svg" and self.instage:
                self.res.append(self.cur)
                self.instage = False
            if t == "div" and self.stk:
                if self.stk.pop():
                    self.sub -= 1

        def handle_data(self, d):
            d = d.strip()
            if (
                self.intext
                and self.cur
                and self.cur["val"] is None
                and d
                and len(d) <= 4
            ):
                self.cur["val"] = d

    p = P()
    p.feed(html)
    parents = [r for r in p.res if r["depth"] == 0]
    return parents[-1] if parents else None


def test_substory_mutation_persists_into_parent(tmp_path: Path) -> None:
    src = tmp_path / "s.tex"
    src.write_text(
        '\\begin{animation}[id="p", label="l"]\n'
        "\\shape{a}{Array}{size=3, data=[1,2,3]}\n"
        "\\step\n\\narrate{base}\n"
        '\\substory[title="Sub"]\n'
        "\\step\n\\recolor{a.cell[0]}{state=good}\n\\apply{a.cell[0]}{value=9}\n"
        "\\narrate{inside}\n\\endsubstory\n"
        "\\step\n\\narrate{after; a.cell[0] stays good and 9}\n"
        "\\end{animation}\n"
    )
    out = tmp_path / "s.html"
    render_file(src, out)
    stage = _last_parent_stage(out.read_text(), "a.cell[0]")
    assert stage is not None
    # docs:670 — the substory's parent-shape mutation persists into the
    # post-substory parent frame (both state and value).
    assert stage["state"] == "scriba-state-good"
    assert stage["val"] == "9"
