# CSES 02 — Missing Number: Expected Animation

## Overview

- **Frames:** 9 total
- **Primitives:** 2 Arrays (given numbers + computation tracker)
- **Visual flow:** Left-to-right scan with running sum accumulation

## Frame-by-Frame Description

### Frame 0 (Initial)
- `arr`: [1, 2, 3, 4, 6, 7, 8] all idle
- `info`: [36, 0, 0] — expected sum pre-filled, actual and missing at 0
- Narration explains the sum formula approach

### Frames 1–7 (Scanning)
Each frame:
- Highlights the current element (yellow border, ephemeral)
- Previous elements marked `done` (green)
- `info.cell[1]` (actual sum) updated with running total
- Narration shows the arithmetic

Key moment — Frame 5 (index 4, value=6):
- Narration notes the gap: jumped from 4 to 6, hinting where 5 should be

### Frame 8 (Result)
- All `arr` cells marked `done` (green)
- `info.cell[2]` (missing) set to 5 with `good` state (sky blue)
- Narration: "Missing = 36 - 31 = 5"

## Visual Characteristics
- The `info` array acts as a dashboard showing expected/actual/missing
- The scanning pattern (highlight current, done for previous) creates a clear left-to-right progression
