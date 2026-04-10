# CSES 01 — Weird Algorithm: Expected Animation

## Overview

- **Frames:** 17 total (one per value in the Collatz sequence for n=7)
- **Primitives:** Array (current value), Array (sequence history), MetricPlot (value chart)
- **Sequence:** 7, 22, 11, 34, 17, 52, 26, 13, 40, 20, 10, 5, 16, 8, 4, 2, 1

## Frame-by-Frame Description

### Frame 0
- `val`: [7] highlighted as current
- `seq`: first cell shows 7, rest empty
- `plot`: first point at (0, 7)
- Narration: "Start with n = 7. 7 is odd, so next = 3*7 + 1 = 22"

### Frames 1–15 (Intermediate steps)
Each frame:
- `val` updates to new value
- `seq` fills in the next cell, previous cell marked `done`
- `plot` gets a new data point showing the hailstone pattern
- Narration explains whether n is even (divide by 2) or odd (3n+1)

Key moments:
- Frame 5 (n=52): peak value, spike visible on plot
- Frame 11 (n=5): "3*5+1=16, power of 2 -- will halve straight down to 1"
- Frames 12–16: smooth descent 16, 8, 4, 2, 1

### Frame 16 (Final)
- `val`: [1] marked `good` (sky blue)
- `seq`: all 17 cells filled, all marked `good`
- `plot`: complete hailstone curve
- Narration summarizes the full sequence

## Visual Characteristics
- MetricPlot creates iconic hailstone shape -- spikes on odd steps, cascades on even steps
- Sequence array provides horizontal timeline of all values
- Color progression: idle, current (blue), done (green), good (sky blue) at end
