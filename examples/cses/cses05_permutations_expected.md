# CSES 05 — Permutations: Expected Animation

## Overview

- **Frames:** 6 total
- **Primitives:** 2 Arrays (permutation + adjacent differences)
- **Visual flow:** Construction in two phases (evens then odds), verification

## Frame-by-Frame Description

### Frame 0 (Strategy)
- `perm`: [0,0,0,0,0,0,0,0] all idle
- `diffs`: [0,0,0,0,0,0,0] all idle
- Narration explains the even-first-then-odd strategy

### Frame 1 (Place evens)
- perm[0:3] = [2, 4, 6, 8] marked `current` (blue)
- Narration: "Place even numbers"

### Frame 2 (Verify even diffs)
- diffs[0:2] = [2, 2, 2] marked `done` (green)
- perm[0:3] marked `done` (green)
- All within-evens diffs are 2

### Frame 3 (Place odds)
- perm[4:7] = [1, 3, 5, 7] marked `current` (blue)
- Narration: "Place odd numbers"

### Frame 4 (Verify boundary + odd diffs)
- diffs[3] = 7 marked `good` (sky blue) — the critical boundary
- diffs[4:6] = [2, 2, 2] marked `done`
- perm.cell[3] and perm.cell[4] highlighted (yellow) — the boundary pair
- Narration explains boundary safety

### Frame 5 (Complete)
- All perm and diffs cells marked `good` (sky blue)
- Narration: final permutation with all diffs

## Visual Characteristics
- Two-phase construction clearly separates evens and odds
- The `diffs` array provides visual proof that all differences >= 2
- Boundary pair (8, 1) gets special highlight attention
- Green → sky blue color progression shows verification → success
