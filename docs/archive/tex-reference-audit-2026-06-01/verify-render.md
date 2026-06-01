# SCRIBA-TEX-REFERENCE.md render verification — 2026-06-01

Repo: `/Users/mrchuongdan/Documents/GitHub/scriba`
Renderer: `python3 render.py <file>.tex`
Scratch: `/tmp/`

## 1. §9 Complete Examples

All 7 fenced `latex` blocks in §9 extracted to `/tmp/ex_1.tex` … `/tmp/ex_7.tex` and rendered.

| Example | Source | Result | Matches doc? |
|---------|--------|--------|--------------|
| 9.1 Minimal Animation | ex_1.tex | Rendered OK | YES |
| 9.2 Static Diagram | ex_2.tex | Rendered OK | YES |
| 9.3 DP Editorial (Frog) | ex_3.tex | Rendered OK (1 block + 1 TeX region) | YES |
| 9.4 BFS Multiple Primitives | ex_4.tex | Rendered OK | YES |
| 9.5 foreach + compute | ex_5.tex | Rendered OK | YES |
| 9.6 Hidden State (BFS Tree) | ex_6.tex | Rendered OK | YES |
| 9.7 Dijkstra (full) | ex_7.tex | Rendered OK (1 block + 1 TeX region) | YES |

All §9 examples render. No failures.

## 2. Changed / new reference snippets

Minimal wrappers built in `/tmp/`; rendered to confirm documented behavior.

| Snippet | Expected (per doc) | Result | Matches doc? |
|---------|--------------------|--------|--------------|
| Graph `\apply{G}{set_weight={from="A",to="C",value=9}}` | Renders OK | Rendered OK | YES |
| Plane2D `\apply{p}{add_region={polygon=[(0,0),(1,2),(2,0)], fill="rgba(0,114,178,0.2)"}}` | Renders OK | Rendered OK | YES |
| Plane2D malformed `\apply{p}{add_point=5}` | ERROR E1467 | `error [E1467]: malformed point add-spec: 5` | YES |
| Matrix `colorscale="viridis"` | Renders OK | Rendered OK | YES |
| Matrix `colorscale="plasma"` | ERROR E1421 | `error [E1421]: Matrix colorscale 'plasma' is unknown; valid: viridis` | YES |
| Tree int nodes `root=8,nodes=[8,3,10]` + `\apply{T}{add_node={id="E",parent="3"}}` | Renders OK (str-normalized) | Rendered OK | YES |
| `\compute{target=4}` then `\recolor{a.cell[${target}]}{state=good}` (selector var outside foreach) | Renders OK | Rendered OK | YES |
| Unbound `\recolor{a.cell[${nope}]}{...}` | ERROR E1159 | `error [E1159]: selector index '${nope}' is not a known \compute binding` | YES |
| `\hl{ghost}{x}` referencing undeclared step (inside `\narrate`) | ERROR E1321 | `error [E1321]: \hl references unknown step-id 'ghost'` | YES |
| Valid `\hl{init}{...}` / `\hl{step1}{...}` to real label + implicit step{N} (inside `\narrate`) | Renders OK | Rendered OK | YES |
| Boolean lowercase `directed=true` | Renders OK | Rendered OK | YES |

## Notes

- `\hl` is **only valid inside `\narrate{...}`** (doc §5.13, line 616). Used as a
  standalone command it raises E1006 (unknown command), not E1321. The E1321 /
  valid-`\hl` checks above were therefore run with `\hl` placed inside `\narrate`,
  which is the documented usage — behavior matches the doc.

## Conclusion

All 7 §9 complete examples render successfully. All 11 changed/new snippet
behaviors match the documentation exactly (valid cases render; error cases emit
the documented E-codes E1467, E1421, E1159, E1321). No discrepancies found.
