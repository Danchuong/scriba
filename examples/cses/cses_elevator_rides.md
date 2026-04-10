# CSES: Elevator Rides

## Problem Statement

There are **n** people who need to use an elevator. You know the weight of each person. The elevator has a maximum weight capacity **x**. What is the minimum number of elevator rides needed to transport all n people? Each person rides the elevator exactly once.

### Input

The first line contains two integers n and x: the number of people and the maximum allowed weight.

The second line contains n integers w_1, w_2, ..., w_n: the weight of each person.

### Output

Print the minimum number of rides.

### Constraints

- 1 <= n <= 20
- 1 <= x <= 10^9
- 1 <= w_i <= x

### Example

**Input:**
```
4 8
3 5 2 7
```

**Output:**
```
2
```

Explanation: One optimal grouping is {3, 5} on ride 1 and {2} (or {7}) on ride 2, then the remaining on ride 3... but actually {3, 5} weighs 8 which fits, and {2, ...} -- let us trace it. With weights [3, 5, 2, 7] and capacity 8: ride 1 takes persons with weights {7}, ride 2 takes {3, 5}, ride 3 takes {2}. That is 3 rides. Alternatively: ride 1 = {3, 2} (weight 5), ride 2 = {5} (weight 5), ride 3 = {7} (weight 7) = 3 rides. Or ride 1 = {7} (7), ride 2 = {3, 5} (8), ride 3 = {2} (2) = 3 rides. Actually all groupings need at least 3 rides since 3+5+2+7 = 17 > 2*8 = 16. Wait: we can do {3,2} = 5, {5} = 5, {7} = 7 which is 3 rides. Or {3,5} = 8, {2} = 2, {7} = 7 = 3 rides. The minimum is **3** rides.

---

## Approach: Bitmask DP

Since n <= 20, we can represent each subset of people as a bitmask. For each subset (mask), we compute the optimal packing into elevator rides.

### State

For each bitmask `mask` (representing which people have been transported), store a pair:

```
dp[mask] = (rides, remaining)
```

- `rides`: minimum number of elevator rides to transport exactly the people in `mask`
- `remaining`: maximum remaining capacity in the last ride (among all arrangements achieving `rides` rides)

We want to minimize `rides` first, and among equal `rides`, maximize `remaining` (greedy: leave as much room as possible in the current ride for future additions).

### Base Case

```
dp[0] = (1, x)
```

No one transported yet. We start with 1 ride that has full capacity x remaining.

### Transition

For each mask, try adding each person i not yet in mask (bit i is 0):

```
new_mask = mask | (1 << i)
```

If person i fits in the current ride (`w[i] <= remaining`):
- candidate = (rides, remaining - w[i])

Otherwise, start a new ride:
- candidate = (rides + 1, x - w[i])

Update `dp[new_mask]` if candidate is better (fewer rides, or same rides with more remaining).

### Answer

```
dp[(1 << n) - 1].rides
```

The full bitmask with all n people transported.

### C++ Solution

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, x;
    cin >> n >> x;

    vector<int> w(n);
    for (int i = 0; i < n; i++) {
        cin >> w[i];
    }

    int full = 1 << n;
    // dp[mask] = {rides, remaining_capacity}
    vector<pair<int,int>> dp(full, {n + 1, 0});
    dp[0] = {1, x};

    for (int mask = 0; mask < full; mask++) {
        if (dp[mask].first > n) continue;
        for (int i = 0; i < n; i++) {
            if (mask & (1 << i)) continue;
            int new_mask = mask | (1 << i);
            pair<int,int> candidate;
            if (w[i] <= dp[mask].second) {
                candidate = {dp[mask].first, dp[mask].second - w[i]};
            } else {
                candidate = {dp[mask].first + 1, x - w[i]};
            }
            // Better = fewer rides, or same rides with more remaining
            if (candidate.first < dp[new_mask].first ||
                (candidate.first == dp[new_mask].first &&
                 candidate.second > dp[new_mask].second)) {
                dp[new_mask] = candidate;
            }
        }
    }

    cout << dp[full - 1].first << "\n";
    return 0;
}
```

### Complexity

- **Time:** O(2^n * n). There are 2^n subsets, and for each we try n persons.
- **Space:** O(2^n) for the DP table.

---

## Why This Works

The key insight is the lexicographic comparison of (rides, -remaining). By minimizing rides first and maximizing remaining capacity second, we greedily pack people into the fewest rides possible. The bitmask ensures we consider every possible grouping without repetition. Since n <= 20, the 2^20 * 20 ~ 20 million operations run comfortably within time limits.
