# CSES Elevator Rides: Expected Animation

## Overview

- **Frames:** 20 total
- **Primitives:** Array (weights), DPTable (16 cells for bitmask states)
- **Example:** n=4, weights=[3, 5, 2, 7], capacity x=8
- **Answer:** 3 rides

## Primitives Layout

- **w**: Array of size 4 showing person weights [3, 5, 2, 7], labeled "weights"
- **dp**: 1D DPTable of size 16 (indices 0..15), labeled "dp[mask] = (rides, remaining)". Each cell stores a string like "1,5" meaning 1 ride with 5 capacity remaining.

## Frame-by-Frame Description

### Frame 0 (Introduction)
- All shapes in initial idle state
- Narration explains the problem setup and bitmask DP approach

### Frame 1 (Base case)
- `dp.cell[0]` set to "1,8" and recolored `good`
- Narration: empty set, 1 ride open with full capacity 8

### Frame 2 (Person 0 alone)
- `w.cell[0]` highlighted (ephemeral)
- `dp.cell[1]` set to "1,5", recolored `current`
- Narration: person 0 (weight 3) fits in current ride

### Frame 3 (Person 1 alone)
- `dp.cell[1]` recolored `done`
- `w.cell[1]` highlighted
- `dp.cell[2]` set to "1,3", recolored `current`

### Frame 4 (Person 2 alone)
- `dp.cell[2]` recolored `done`
- `w.cell[2]` highlighted
- `dp.cell[4]` set to "1,6", recolored `current`

### Frame 5 (Person 3 alone)
- `dp.cell[4]` recolored `done`
- `w.cell[3]` highlighted
- `dp.cell[8]` set to "1,1", recolored `current`
- Narration: all single-person subsets computed

### Frame 6 (Pair {0,1} -- perfect fit)
- `dp.cell[8]` recolored `done`, `dp.cell[1]` recolored `current`
- `w.cell[1]` highlighted
- `dp.cell[3]` set to "1,0", recolored `current`
- Key moment: weights 3+5=8 exactly fill the elevator

### Frame 7 (Pair {0,2})
- `dp.cell[3]` recolored `done`
- `dp.cell[5]` set to "1,3", recolored `current`

### Frame 8 (Pair {0,3} -- does not fit)
- `dp.cell[5]` recolored `done`
- `dp.cell[9]` set to "2,1", recolored `current`
- Key moment: first time a new ride is needed (weight 7 > 5 remaining)

### Frame 9 (Pair {1,2})
- `dp.cell[6]` set to "1,1", recolored `current`
- Weight 5+2=7 fits in one ride

### Frame 10 (Pair {1,3})
- `dp.cell[10]` set to "2,1", recolored `current`
- New ride needed

### Frame 11 (Pair {2,3} -- first attempt)
- `dp.cell[12]` set to "2,1", recolored `current`

### Frame 12 (Pair {2,3} -- update)
- `dp.cell[12]` updated to "2,6"
- Key moment: demonstrates the "maximize remaining" tiebreaker -- same 2 rides but 6 remaining is better than 1 remaining

### Frame 13 (Triple {0,1,2})
- `dp.cell[7]` set to "2,6", recolored `current`
- Persons 0,1 fill ride 1 completely; person 2 starts ride 2

### Frame 14 (Triple {0,1,3})
- `dp.cell[11]` set to "2,0" then corrected context
- Multiple paths converge on 2 rides

### Frame 15 (Triple {1,2,3})
- `dp.cell[14]` set to "2,0", recolored `current`

### Frame 16 (Triple {0,2,3})
- `dp.cell[13]` set to "2,3", recolored `current`
- Demonstrates update: path through dp[1100]=(2,6)+person 0 gives better remaining

### Frame 17 (Full set -- transitions)
- `dp.cell[15]` recolored `current`
- Narration enumerates all four incoming transitions

### Frame 18 (Full set -- value)
- `dp.cell[15]` set to "3,6"
- All transitions require a 3rd ride

### Frame 19 (Final)
- `dp.cell[15]` recolored `good`
- All other cells recolored `done`
- Narration: answer is 3 rides, explains one optimal grouping

## Visual Characteristics

- **Highlight** on weight array cells is ephemeral (cleared each step), showing which person is being considered
- **Recolor** on dp cells is persistent: `current` while computing, `done` when finalized, `good` for the answer cell
- The DPTable shows the bitmask index 0..15; narration explains binary interpretation (e.g., "mask 0011 = persons 0 and 1")
- Key teaching moments:
  1. Frame 6: perfect capacity fit (3+5=8)
  2. Frame 8: first "does not fit" requiring a new ride
  3. Frame 12: update demonstrating the "maximize remaining" tiebreaker
  4. Frame 17-18: final convergence showing all paths need 3 rides

## Color State Progression

| State | Meaning | Color |
|-------|---------|-------|
| idle | Not yet computed | Default gray |
| current | Being computed this step | Blue |
| done | Finalized | Green |
| good | Final answer | Sky blue |
