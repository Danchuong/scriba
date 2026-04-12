# TikZ animate vs Scriba: Editorial Comparison

> Same problem, same algorithm, two completely different authoring
> experiences. This file shows what an editorial for **Frog 1** (AtCoder
> DP-A) looks like in TikZ `animate` vs Scriba `\begin{animation}`.

---

## The Problem

> There are $N$ stones numbered $0$ to $N-1$. Stone $i$ has height $h_i$.
> A frog starts at stone $0$ and wants to reach stone $N-1$. It can jump
> 1 or 2 stones forward, paying $|h_i - h_j|$. Find the minimum total cost.
>
> **Input**: $N=6$, $h = [2, 9, 4, 5, 1, 6]$
>
> **Answer**: $4$ (path $0 \to 2 \to 3 \to 5$, cost $2+1+1$)

---

## TikZ `animate` version

### Requirements

- TeX Live 2020+ (~4 GB install)
- `pdflatex` or `lualatex` compilation
- Output: PDF only (animation requires Adobe Acrobat to play)
- Viewer: **Adobe Acrobat only** -- Preview.app, Chrome PDF viewer, Evince, Okular do NOT support `/animate` timeline

### Source (~180 lines)

```latex
\documentclass[tikz]{standalone}
\usepackage{animate}
\usepackage{ifthen}
\usepackage{xcolor}

% ── Color definitions ────────────────────────
\definecolor{cellIdle}{HTML}{E8E8E8}
\definecolor{cellCurrent}{HTML}{3B82F6}
\definecolor{cellDone}{HTML}{22C55E}
\definecolor{cellPath}{HTML}{6366F1}
\definecolor{arrowGood}{HTML}{0EA5E9}
\definecolor{arrowInfo}{HTML}{A3A3A3}

% ── Helper macros ────────────────────────────
\newcommand{\heights}{2,9,4,5,1,6}
\newcommand{\dpvals}{{0,7,2,3,5,4}}
\newcommand{\cellw}{1.2}
\newcommand{\cellh}{0.8}

% ── Draw one cell (x, y, value, fill-color, label) ──
\newcommand{\cell}[5]{
  \fill[#4, rounded corners=2pt]
    ({#1*\cellw}, #2) rectangle +(\cellw, \cellh);
  \draw[gray!50, rounded corners=2pt]
    ({#1*\cellw}, #2) rectangle +(\cellw, \cellh);
  \node[font=\small\sffamily] at ({#1*\cellw+0.6}, {#2+0.4}) {#3};
  \node[font=\tiny\sffamily, below] at ({#1*\cellw+0.6}, #2) {#5};
}

% ── Draw arrow between cells ──
\newcommand{\dparrow}[4]{
  % #1=from-col, #2=to-col, #3=color, #4=label
  \draw[->, thick, #3]
    ({#1*\cellw+0.6}, -0.1) ..
    controls ({(#1+#2)*\cellw/2+0.6}, {-0.6-0.3*abs(#2-#1)}) ..
    ({#2*\cellw+0.6}, -0.1)
    node[midway, below, font=\tiny] {#4};
}

\begin{document}

% ── Timeline: 16 frames at 0.5s each = 8 seconds total ──
\begin{animateinline}[controls, loop]{2}

% ──────────── Frame 0: Initial state ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  % h[] row
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \foreach \v [count=\i from 0] in {2,9,4,5,1,6} {
    \cell{\i}{1}{\v}{cellIdle}{\i}
  }
  % dp[] row
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \foreach \i in {0,...,5} {
    \cell{\i}{-1}{}{cellIdle}{\i}
  }
  % Narration
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {Frog 1: 6 stones, heights $h = [2,9,4,5,1,6]$.};
\end{tikzpicture}

\newframe
% ──────────── Frame 1: dp[0] = 0 ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \cell{0}{1}{2}{cellCurrent}{0}
  \foreach \v [count=\i from 1] in {9,4,5,1,6} {
    \cell{\i}{1}{\v}{cellIdle}{\i}
  }
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \cell{0}{-1}{0}{cellDone}{0}
  \foreach \i in {1,...,5} {
    \cell{\i}{-1}{}{cellIdle}{\i}
  }
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {Base case: $dp[0] = 0$.};
\end{tikzpicture}

\newframe
% ──────────── Frame 2: dp[1] candidates ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \cell{0}{1}{2}{cellIdle}{0}
  \cell{1}{1}{9}{cellCurrent}{1}
  \foreach \v [count=\i from 2] in {4,5,1,6} {
    \cell{\i}{1}{\v}{cellIdle}{\i}
  }
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \cell{0}{-1}{0}{cellDone}{0}
  \cell{1}{-1}{}{cellCurrent}{1}
  \foreach \i in {2,...,5} {
    \cell{\i}{-1}{}{cellIdle}{\i}
  }
  \dparrow{0}{1}{arrowGood}{+7}
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {$dp[1]$: from stone 0, cost $|9-2| = 7$.};
\end{tikzpicture}

\newframe
% ──────────── Frame 3: dp[1] = 7 committed ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \cell{0}{1}{2}{cellIdle}{0}
  \cell{1}{1}{9}{cellIdle}{1}
  \cell{2}{1}{4}{cellCurrent}{2}
  \foreach \v [count=\i from 3] in {5,1,6} {
    \cell{\i}{1}{\v}{cellIdle}{\i}
  }
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \cell{0}{-1}{0}{cellDone}{0}
  \cell{1}{-1}{7}{cellDone}{1}
  \cell{2}{-1}{}{cellCurrent}{2}
  \foreach \i in {3,...,5} {
    \cell{\i}{-1}{}{cellIdle}{\i}
  }
  \dparrow{0}{2}{arrowGood}{+2}
  \dparrow{1}{2}{arrowInfo}{+5}
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {$dp[2]$: from 0 cost $2$, from 1 cost $12$. $\min = 2$.};
\end{tikzpicture}

\newframe
% ──────────── Frame 4: dp[2] = 2, show dp[3] ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \foreach \v [count=\i from 0] in {2,9,4,5,1,6} {
    \ifthenelse{\i=3}{\cell{\i}{1}{\v}{cellCurrent}{\i}}
      {\cell{\i}{1}{\v}{cellIdle}{\i}}
  }
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \cell{0}{-1}{0}{cellDone}{0}
  \cell{1}{-1}{7}{cellDone}{1}
  \cell{2}{-1}{2}{cellDone}{2}
  \cell{3}{-1}{}{cellCurrent}{3}
  \foreach \i in {4,5} {
    \cell{\i}{-1}{}{cellIdle}{\i}
  }
  \dparrow{1}{3}{arrowInfo}{+4}
  \dparrow{2}{3}{arrowGood}{+1}
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {$dp[3]$: from 1 cost $11$, from 2 cost $3$. $\min = 3$.};
\end{tikzpicture}

\newframe
% ──────────── Frame 5: dp[3] = 3, show dp[4] ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \foreach \v [count=\i from 0] in {2,9,4,5,1,6} {
    \ifthenelse{\i=4}{\cell{\i}{1}{\v}{cellCurrent}{\i}}
      {\cell{\i}{1}{\v}{cellIdle}{\i}}
  }
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \cell{0}{-1}{0}{cellDone}{0}
  \cell{1}{-1}{7}{cellDone}{1}
  \cell{2}{-1}{2}{cellDone}{2}
  \cell{3}{-1}{3}{cellDone}{3}
  \cell{4}{-1}{}{cellCurrent}{4}
  \cell{5}{-1}{}{cellIdle}{5}
  \dparrow{2}{4}{arrowGood}{+3}
  \dparrow{3}{4}{arrowInfo}{+4}
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {$dp[4]$: from 2 cost $5$, from 3 cost $7$. $\min = 5$.};
\end{tikzpicture}

\newframe
% ──────────── Frame 6: dp[4] = 5, show dp[5] ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \foreach \v [count=\i from 0] in {2,9,4,5,1,6} {
    \ifthenelse{\i=5}{\cell{\i}{1}{\v}{cellCurrent}{\i}}
      {\cell{\i}{1}{\v}{cellIdle}{\i}}
  }
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \cell{0}{-1}{0}{cellDone}{0}
  \cell{1}{-1}{7}{cellDone}{1}
  \cell{2}{-1}{2}{cellDone}{2}
  \cell{3}{-1}{3}{cellDone}{3}
  \cell{4}{-1}{5}{cellDone}{4}
  \cell{5}{-1}{}{cellCurrent}{5}
  \dparrow{3}{5}{arrowGood}{+1}
  \dparrow{4}{5}{arrowInfo}{+5}
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {$dp[5]$: from 3 cost $4$, from 4 cost $10$. $\min = 4$.};
\end{tikzpicture}

\newframe
% ──────────── Frame 7: Final -- highlight optimal path ────────────
\begin{tikzpicture}[x=1cm, y=1cm]
  \useasboundingbox (-0.3, -2.5) rectangle (7.8, 2.5);
  \node[font=\small\bfseries, anchor=east] at (-0.2, 1.4) {$h$};
  \foreach \v [count=\i from 0] in {2,9,4,5,1,6} {
    \ifthenelse{\i=0 \OR \i=2 \OR \i=3 \OR \i=5}
      {\cell{\i}{1}{\v}{cellPath}{\i}}
      {\cell{\i}{1}{\v}{cellIdle}{\i}}
  }
  \node[font=\small\bfseries, anchor=east] at (-0.2, -0.4) {$dp$};
  \foreach \v [count=\i from 0] in {0,7,2,3,5,4} {
    \ifthenelse{\i=0 \OR \i=2 \OR \i=3 \OR \i=5}
      {\cell{\i}{-1}{\v}{cellPath}{\i}}
      {\cell{\i}{-1}{\v}{cellDone}{\i}}
  }
  \dparrow{0}{2}{cellPath}{+2}
  \dparrow{2}{3}{cellPath}{+1}
  \dparrow{3}{5}{cellPath}{+1}
  \node[font=\small, text width=7cm, anchor=north west]
    at (0, -1.8) {Answer: $dp[5] = 4$. Path: $0 \to 2 \to 3 \to 5$.};
\end{tikzpicture}

\end{animateinline}
\end{document}
```

### Build command

```bash
pdflatex frog-editorial.tex    # produces frog-editorial.pdf
```

### What you get

- A PDF with a **play/pause/seek** timeline bar
- **Only works in Adobe Acrobat** -- all other PDF viewers show a static first frame
- Cannot be embedded in a web page (no HTML output)
- Cannot be sent by email (recipients need Acrobat)
- No step-by-step: the timeline plays continuously at 2 fps
- No narration system: text is baked into each frame as a TikZ `\node`

### Pain points

1. **Every frame is a full redraw.** TikZ `animate` has no state carry-forward. If frame 5 has 6 cells filled, you must draw all 6 cells from scratch in frame 5's `\begin{tikzpicture}`. Changing one cell's color means editing every frame that follows.

2. **No semantic states.** Color is raw hex. There is no `current`, `done`, `path` vocabulary -- you manage `\definecolor` yourself and must remember which hex means what.

3. **Arrows are manual geometry.** Each curved arrow requires explicit Bezier control points (`controls (x,y) .. (x,y)`). Adding a cell shifts all coordinates.

4. **Narration is a positioned node.** There is no `\narrate` -- you place a `\node` at a hardcoded `(x, y)` in every frame and manage line-wrapping yourself.

5. **Line count scales as $O(F \times C)$.** For $F$ frames and $C$ cells, every frame redraws every cell. The 8-frame, 6-cell example above is already ~180 lines. A 20-step animation on a 10-element array would be 500+ lines.

6. **Output is PDF-only with Acrobat dependency.** The entire animation is unusable on the web, in email, or in any non-Acrobat PDF viewer.

---

## Scriba version

### Requirements

- Python 3.11+ with `scriba` package (pip install, ~2 MB)
- Node.js for KaTeX (math rendering only)
- Output: **self-contained HTML** -- works in every browser, email client, RSS reader, and print

### Source (68 lines)

```tex
\section{Frog 1 -- AtCoder DP-A}

Given $N = 6$ stones with heights $h = [2, 9, 4, 5, 1, 6]$.
A frog starts at stone $0$ and can jump 1 or 2 stones forward,
paying $|h_i - h_j|$. Find the minimum total cost to reach stone $N-1$.

$$
dp[i] = \min(dp[i-1] + |h_i - h_{i-1}|,\; dp[i-2] + |h_i - h_{i-2}|)
$$

\begin{animation}[id="frog1-dp", label="Frog 1 -- DP (AtCoder DP-A)"]
\shape{h}{Array}{size=6, data=[2,9,4,5,1,6], labels="0..5", label="$h$"}
\shape{dp}{Array}{size=6, data=["","","","","",""], labels="0..5", label="$dp$"}

\step
\narrate{6 stones, heights $h = [2,9,4,5,1,6]$. Find min cost from stone 0 to stone 5.}

\step
\recolor{h.cell[0]}{state=current}
\recolor{dp.cell[0]}{state=done}
\apply{dp.cell[0]}{value=0}
\narrate{Base case: $dp[0] = 0$. The frog starts here, no cost.}

\step
\cursor{h.cell, dp.cell}{1}
\annotate{dp.cell[1]}{label="+7", arrow_from="dp.cell[0]", color=good}
\narrate{$dp[1]$: only from stone 0. Cost $= |9-2| = 7$.}

\step
\apply{dp.cell[1]}{value=7}
\recolor{dp.cell[1]}{state=done}
\cursor{h.cell}{2}
\recolor{dp.cell[2]}{state=current}
\annotate{dp.cell[2]}{label="+2", arrow_from="dp.cell[0]", color=good}
\annotate{dp.cell[2]}{label="+5", arrow_from="dp.cell[1]", color=info}
\narrate{$dp[2]$: from 0 costs $0+2=2$, from 1 costs $7+5=12$. $\min = 2$.}

\step
\apply{dp.cell[2]}{value=2}
\recolor{dp.cell[2]}{state=done}
\cursor{h.cell, dp.cell}{3}
\annotate{dp.cell[3]}{label="+4", arrow_from="dp.cell[1]", color=info}
\annotate{dp.cell[3]}{label="+1", arrow_from="dp.cell[2]", color=good}
\narrate{$dp[3]$: from 1 costs $7+4=11$, from 2 costs $2+1=3$. $\min = 3$.}

\step
\apply{dp.cell[3]}{value=3}
\recolor{dp.cell[3]}{state=done}
\cursor{h.cell, dp.cell}{4}
\annotate{dp.cell[4]}{label="+3", arrow_from="dp.cell[2]", color=good}
\annotate{dp.cell[4]}{label="+4", arrow_from="dp.cell[3]", color=info}
\narrate{$dp[4]$: from 2 costs $2+3=5$, from 3 costs $3+4=7$. $\min = 5$.}

\step
\apply{dp.cell[4]}{value=5}
\recolor{dp.cell[4]}{state=done}
\cursor{h.cell, dp.cell}{5}
\annotate{dp.cell[5]}{label="+1", arrow_from="dp.cell[3]", color=good}
\annotate{dp.cell[5]}{label="+5", arrow_from="dp.cell[4]", color=info}
\narrate{$dp[5]$: from 3 costs $3+1=4$, from 4 costs $5+5=10$. $\min = 4$.}

\step
\apply{dp.cell[5]}{value=4}
\recolor{dp.cell[5]}{state=done}
\recolor{h.cell[0]}{state=path}
\recolor{h.cell[2]}{state=path}
\recolor{h.cell[3]}{state=path}
\recolor{h.cell[5]}{state=path}
\recolor{dp.cell[0]}{state=path}
\recolor{dp.cell[2]}{state=path}
\recolor{dp.cell[3]}{state=path}
\recolor{dp.cell[5]}{state=path}
\reannotate{dp.cell[2]}{color=path, arrow_from="dp.cell[0]"}
\reannotate{dp.cell[3]}{color=path, arrow_from="dp.cell[2]"}
\reannotate{dp.cell[5]}{color=path, arrow_from="dp.cell[3]"}
\narrate{Answer: $dp[5] = 4$. Optimal path: $0 \to 2 \to 3 \to 5$, cost $2+1+1 = 4$.}
\end{animation}

\subsection{Complexity}

Time: $O(N)$. Space: $O(N)$ (can be reduced to $O(1)$ with two variables).
```

### Build command

```python
from scriba import Pipeline, RenderContext, SubprocessWorkerPool
from scriba.tex import TexRenderer
from scriba.animation import AnimationRenderer

pool = SubprocessWorkerPool(max_workers=2)
pipeline = Pipeline(renderers=[
    AnimationRenderer(worker_pool=pool),
    TexRenderer(worker_pool=pool),
])
source = open("frog-editorial.tex").read()
ctx = RenderContext(resource_resolver=lambda _: None, theme="light")
with pipeline:
    doc = pipeline.render(source, ctx)
open("frog-editorial.html", "w").write(doc.html)
```

### What you get

- Self-contained **HTML** with prev/next step controls
- Works in **every browser**, email client, RSS reader, and `@media print`
- Zero JavaScript for diagram; minimal JS for step navigation (~1.1 KB)
- Each frame carries narration as real text (accessible, searchable, translatable)
- Deterministic output: same input always produces byte-identical HTML

---

## Side-by-side comparison

| Aspect | TikZ `animate` | Scriba |
|--------|----------------|--------|
| **Lines of code** | ~180 (8 frames, 6 cells) | ~68 (8 steps, 6 cells + prose) |
| **Scaling** | $O(F \times C)$ -- every frame redraws everything | $O(F)$ -- state carries forward, describe only changes |
| **State system** | None -- raw hex colors | 7 semantic states (`idle`, `current`, `done`, `dim`, `good`, `error`, `path`) |
| **Arrows** | Manual Bezier control points | `\annotate{target}{arrow_from="source", label="+7"}` |
| **Narration** | Manual `\node` placement per frame | `\narrate{...}` with LaTeX math support |
| **Cursor movement** | Redraw all cells with new colors | `\cursor{h.cell, dp.cell}{3}` (1 line) |
| **Output format** | PDF only | HTML (browser, email, RSS, print) |
| **Viewer requirement** | Adobe Acrobat only | Any browser |
| **Playback model** | Continuous timeline (play/pause/seek) | Discrete steps (prev/next) |
| **Math rendering** | Native LaTeX | KaTeX (98% LaTeX coverage) |
| **Install size** | ~4 GB (TeX Live) | ~2 MB (pip) + Node.js |
| **Build time** | 5-15s (pdflatex) | <1s (Python pipeline) |
| **Deterministic** | Depends on TeX engine state | Yes, by design (content-hash cacheable) |
| **Accessibility** | PDF accessibility is poor | Real `<ol>`, `<figure>`, `<p>` -- screen-reader friendly |
| **Embeddable in web** | No (PDF object/iframe only) | Yes (inline HTML) |
| **Email-safe** | No | Yes (zero JS for diagrams, minimal for animation) |

---

## What changes when the problem grows

Consider a 15-element array with 20 DP steps (typical editorial for Knapsack or LIS):

| Metric | TikZ `animate` | Scriba |
|--------|----------------|--------|
| Estimated lines | 800-1200 | 120-160 |
| Frames to manually redraw | 20 (each with 15 cells) | 0 (state carries forward) |
| Adding one step in the middle | Edit every subsequent frame | Insert one `\step` block |
| Changing a color scheme | Find-replace across all frames | Change one `\definecolor` equivalent in CSS |
| Reviewer readability | Low (coordinate soup) | High (reads like pseudocode) |

---

## Conclusion

TikZ `animate` is a general-purpose animation engine for PDF. It is powerful
for physics simulations, geometric constructions, and continuous-time
visualizations. But for **step-by-step algorithm editorials on the web**, it
requires enormous boilerplate, produces output that only works in Adobe
Acrobat, and scales poorly with problem size.

Scriba is purpose-built for this exact use case. The authoring cost is
proportional to the number of *state changes* (what the learner needs to
see), not to the total number of cells times frames. The output works
everywhere the editorial needs to reach.
