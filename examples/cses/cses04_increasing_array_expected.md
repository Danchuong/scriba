# CSES 04 — Increasing Array: Expected Animation

## Overview

- **Frames:** 9 total
- **Primitives:** 2 Arrays (main array + cost counter)
- **Visual flow:** Left-to-right scan, violations shown in red then fixed

## Frame-by-Frame Description

### Frame 0 (Initial)
- `a`: [3, 2, 5, 1, 7] all idle
- `cost`: [0]
- Narration explains the problem

### Frame 1 (Index 0)
- cell[0] marked `done` — first element always OK
- Max so far = 3

### Frame 2 (Index 1 — VIOLATION)
- cell[1] marked `error` (red) — value 2 < 3
- Narration: need +1

### Frame 3 (Index 1 — FIX)
- cell[1] value changes 2 → 3, marked `done`
- cost = 1

### Frame 4 (Index 2 — OK)
- cell[2] marked `current` then `done` — 5 >= 3

### Frame 5 (Index 3 — VIOLATION)
- cell[3] marked `error` — value 1 < 5
- Narration: need +4

### Frame 6 (Index 3 — FIX)
- cell[3] value changes 1 → 5, marked `done`
- cost = 5

### Frame 7 (Index 4 — OK)
- cell[4] current — 7 >= 5

### Frame 8 (Final)
- All cells marked `good` (sky blue)
- cost marked `good`
- Narration: "Total moves = 5"

## Visual Characteristics
- `error` state (red) clearly marks violations before fixing
- Values update in-place to show the "increase" operation
- Cost counter tracks running total
