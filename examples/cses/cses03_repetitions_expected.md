# CSES 03 — Repetitions: Expected Animation

## Overview

- **Frames:** 9 total
- **Primitives:** 2 Arrays (DNA string + tracking vars)
- **Visual flow:** Left-to-right scan, tracking run length

## Frame-by-Frame Description

### Frame 0
- `dna`: ["A","T","T","C","G","G","G","A"], cell[0] = current (blue)
- `vars`: [1, 1] — current run and max
- Narration: first char A, run=1, max=1

### Frame 1 (index 1, T != A)
- cell[0] done (green), cell[1] current (blue)
- vars unchanged [1, 1]
- New run starts

### Frame 2 (index 2, T == T)
- cell[2] current, vars = [2, 2]
- Run extends

### Frame 3 (index 3, C != T)
- cell[3] current, vars.cell[0] = 1
- New run

### Frame 4 (index 4, G != C)
- cell[4] current, vars.cell[0] = 1
- New run

### Frame 5 (index 5, G == G)
- cell[5] current, vars.cell[0] = 2
- Run extends to 2

### Frame 6 (index 6, G == G) — KEY MOMENT
- cell[6] current, vars = [3, 3]
- vars.cell[1] gets `good` state (sky blue)
- New max found!

### Frame 7 (index 7, A != G)
- cell[7] current, vars.cell[0] = 1
- max stays at 3

### Frame 8 (Final)
- cell[7] done, cells[4:6] marked `good` (sky blue) — the GGG substring
- Narration: "Answer: 3"

## Visual Characteristics
- The GGG substring (indices 4-6) gets highlighted as `good` at the end
- The `vars` tracking array shows current/max updating in real-time
- Clear left-to-right scanning pattern
