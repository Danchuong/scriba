#!/usr/bin/env python3
"""Build a side-by-side .tex-vs-render comparison page for the Phase-2 bugs."""
from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).parent
CORPUS = ROOT / "tests" / "doc_coverage" / "corpus"

# (section title, expected, bug, corpus id)
BUGS = [
    ("BUG 1 — \\compute result not interpolated into \\narrate",
     "narration reads “fib(6)=8”", "narration shows the literal placeholder", "cmd_compute_recursion"),
    ("BUG 1 — comprehension", "“Got [0, 2, 4, 6]”", "literal placeholder", "cmd_compute_comprehension"),
    ("BUG 1 — def/for/if", "“Computed 3”", "literal placeholder", "cmd_compute_def_for_if"),
    ("BUG 1 — indented body", "“total=6”", "literal placeholder", "cmd_compute_indented_body"),
    ("BUG 1 — int pow", "“INF=1000000000”", "literal placeholder", "cmd_compute_int_cap_pow"),
    ("BUG 2 — \\apply label= dropped",
     "a caption “my array”", "no caption rendered", "cmd_apply_label"),
    ("BUG 3 — \\reannotate label no-op",
     "step 2 label “orig”→“updated”, color info→good", "stays “orig” + info", "annot_reannotate_label"),
    ("BUG 3 — \\reannotate arrow_from no-op",
     "step 2 re-points arc to cell[0][0] + color path", "arc + color unchanged", "annot_reannotate_arrow_from"),
    ("BUG 4 — annotate position=inside",
     "label INSIDE the cell", "rendered identical to position=above (outside)", "annot_annotate_pos_inside"),
    ("BUG 5 — \\recolor inert: NumberLine nl.axis",
     "dimmed axis", "axis hardcoded idle, no state class", "prim_plot_nl_sel_axis"),
    ("BUG 5 — \\recolor inert: MetricPlot plot.all",
     "all elements recolored done", "MetricPlot emits zero state classes", "prim_plot_mp_sel_all"),
    ("BUG 6 — size brace scoped leaks braces",
     "sized text, no visible braces", "literal { } leak", "latex_size_brace_scoped"),
    ("BUG 6 — all size steps",
     "nine sized glyphs, no braces", "literal { } leak / misplaced spans", "latex_size_all_steps"),
    ("BUG 7 (contested) — graph string selector on int nodes",
     "no match, recolor dropped (E1115)", "node 1 IS recolored current", "prim_graph_node_int_as_string_E1115"),
    ("BUG 7 (contested) — stack recolor same step",
     "recolor dropped (§13.1)", "item[2] shows current", "prim_lin_stack_gotcha_same_step"),
    ("BUG 7 (contested) — queue recolor same step",
     "recolor dropped (§13.1)", "cell[2] shows current", "prim_lin_queue_gotcha_same_step"),
    ("BUG 8 — directed graph duplicate arrow-marker <defs>",
     "one <defs> with id=scriba-arrow-fwd", "two <defs>, duplicate id (invalid SVG)", "prim_graph_directed_true"),
]

rows = []
for title, expected, bug, cid in BUGS:
    tex_path = CORPUS / f"{cid}.tex"
    tex = tex_path.read_text() if tex_path.exists() else "(missing .tex)"
    rel = f"tests/doc_coverage/corpus/{cid}.html"
    rows.append(f"""
<section class="bug">
  <h2>{html.escape(title)}</h2>
  <p class="meta"><span class="exp">Expect:</span> {html.escape(expected)}
     &nbsp;|&nbsp; <span class="bug-l">Bug:</span> {html.escape(bug)}
     &nbsp;|&nbsp; <code>{cid}</code></p>
  <div class="pair">
    <div class="col">
      <div class="lab">.tex source</div>
      <pre><code>{html.escape(tex)}</code></pre>
    </div>
    <div class="col">
      <div class="lab">rendered output</div>
      <iframe src="{rel}" loading="lazy"></iframe>
    </div>
  </div>
</section>""")

page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Scriba render-bug comparison</title>
<style>
  body {{ font: 15px/1.5 -apple-system, system-ui, sans-serif; margin: 0; padding: 2rem 2.5rem; background:#f6f7f9; color:#1a1d21; }}
  h1 {{ font-size: 1.6rem; }}
  .intro {{ color:#52606d; max-width: 70ch; }}
  .bug {{ background:#fff; border:1px solid #dfe3e8; border-radius:10px; padding:1rem 1.25rem; margin:1.25rem 0; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
  .bug h2 {{ font-size:1.05rem; margin:.2rem 0 .4rem; }}
  .meta {{ font-size:.85rem; color:#52606d; margin:.2rem 0 .8rem; }}
  .exp {{ color:#027a55; font-weight:600; }}
  .bug-l {{ color:#c6282d; font-weight:600; }}
  .pair {{ display:grid; grid-template-columns: 1fr 1fr; gap:1rem; align-items:start; }}
  .lab {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; color:#7b8794; margin-bottom:.3rem; }}
  pre {{ margin:0; background:#0f1419; color:#e6e6e6; padding:.8rem; border-radius:8px; overflow:auto; font-size:12.5px; line-height:1.45; max-height:360px; }}
  iframe {{ width:100%; height:360px; border:1px solid #dfe3e8; border-radius:8px; background:#fff; }}
  code {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; }}
  @media (max-width: 900px) {{ .pair {{ grid-template-columns: 1fr; }} }}
</style></head><body>
<h1>Scriba render-bug comparison — Phase 2 findings</h1>
<p class="intro">Left = the <code>.tex</code> you wrote. Right = what scriba actually rendered.
Read the Expect/Bug line, then compare.</p>
{''.join(rows)}
</body></html>"""

out = ROOT / "render-bugs-comparison.html"
out.write_text(page)
print(f"wrote {out} ({len(BUGS)} bugs)")
