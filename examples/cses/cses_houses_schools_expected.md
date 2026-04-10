# CSES Houses and Schools: Expected Animation

## Overview

- **Frames:** 20 total
- **Primitives:** Array (children per house, 6 cells), DPTable (3 rows x 7 cols for dp[j][i]), Array (cost display, 1 cell)
- **Example:** n=6, k=2, children=[2, 3, 5, 1, 4, 6]
- **Answer:** dp[2][6] = 12

## Frame-by-Frame Description

### Frame 0 (Introduction)
- All shapes visible in initial state
- Array shows [2, 3, 5, 1, 4, 6] with labels 1..6
- DPTable is empty (3 rows for j=0,1,2 and 7 cols for i=0..6)
- Narration introduces the problem and DP formulation

### Frame 1 (Base case)
- dp[0][0] = 0, marked `done`
- Narration explains zero schools for zero houses

### Frames 2-8 (Row j=1: one school)
Each frame computes dp[1][i] for i=1..6:
- Frame 2: dp[1][1]=0 (school at house 1)
- Frame 3: dp[1][2]=2 (median at house 2)
- Frame 4: dp[1][3]=7 (median at house 3)
- Frame 5: dp[1][4]=8 (median at house 3)
- Frame 6: dp[1][5]=16 (median at house 3)
- Frame 7: dp[1][6]=33 (median shifts to house 4)
- Frame 8: Summary of row 1, transition to row 2

Visual behavior:
- Current cell is `current` (blue), finalized cells are `done` (green)
- Array range [0..i-1] is highlighted (ephemeral) showing the segment under consideration
- cost_val displays the computed cost(1, i) value

### Frames 9-18 (Row j=2: two schools)
Each frame computes dp[2][i] for i=2..6, showing the split point search:
- Frame 9: dp[2][2]=0 (trivial: one school per house)
- Frames 10-11: dp[2][3]=2, shows trying m=1 and m=2, picks m=2
- Frames 12-13: dp[2][4]=3, optimal split at m=2
- Frames 14-15: dp[2][5]=8, split at m=3 or m=4
- Frames 16-17: dp[2][6]=12, split at m=4

Visual behavior:
- When computing dp[2][i], the right segment being costed is highlighted in the array
- cost_val shows the cost(m+1, i) being evaluated
- Narration mentions monotonicity of optimal split points (D&C optimization justification)

### Frame 19 (Final answer)
- dp[2][6] marked `good` (sky blue)
- Houses 3 and 6 in the array marked `good` (school positions)
- cost_val shows 12
- Narration: "Answer: dp[2][6] = 12. Schools at houses 3 and 6."
- Explains the O(kn log n) complexity from D&C optimization

## DP Table Final State

```
j\i |  0     1     2     3     4     5     6
----+------------------------------------------
 0  |  0     -     -     -     -     -     -
 1  |  -     0     2     7     8    16    33
 2  |  -     -     0     2     3     8    12
```

## Visual Characteristics

- **DPTable** fills top to bottom (row j=1 then j=2), left to right within each row
- **Array highlights** show which houses are in the current cost segment
- **Color progression:** idle -> current (computing) -> done (finalized) -> good (answer cell)
- **cost_val** updates each frame to show the cost function output being evaluated
- **Monotonicity** is narrated: optimal split points move rightward as i increases, justifying D&C
- School positions (houses 3 and 6) are highlighted in the final frame
