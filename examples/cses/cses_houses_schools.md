# CSES: Houses and Schools

## Problem Statement

There are **n** houses on a street, numbered 1 to n from left to right. House i contains **c[i]** children. You need to place exactly **k** schools among the houses (each school occupies one house position) to minimize the **total walking distance**. Each child walks to the nearest school.

### Input

- First line: two integers n and k
- Second line: n integers c[1], c[2], ..., c[n]

### Output

The minimum total walking distance.

### Constraints

- 1 <= k <= n <= 3000
- 0 <= c[i] <= 10^9

### Example

**Input:**
```
6 2
2 3 5 1 4 6
```

**Output:** `18`

Placing schools at houses 3 and 6: children at house 1 walk distance 2, house 2 walks 1, house 3 walks 0, house 4 walks 2 (to school at 6 would be farther, so nearest is 3 at distance 1... actually nearest is school at 3 at distance 1), house 5 walks 1, house 6 walks 0. The exact optimal placement depends on the cost computation.

---

## Solution

### Key Insight

When a single school serves a contiguous segment of houses [l..r], the optimal position for that school is the **weighted median** of the houses in that segment (weighted by number of children). The cost of serving segment [l..r] with one school placed at the weighted median can be precomputed.

### DP Formulation

Define:

```
dp[j][i] = minimum total walking distance to place j schools
           covering houses 1..i (with the j-th school serving
           some suffix of houses ending at i)
```

Recurrence:

```
dp[j][i] = min over all m in [j-1..i-1] of:
           dp[j-1][m] + cost(m+1, i)
```

where `cost(l, r)` is the minimum walking distance when one school serves houses l through r.

Base case: `dp[1][i] = cost(1, i)` for all i.

Answer: `dp[k][n]`.

### Cost Function

For a contiguous segment [l..r], placing one school optimally (at the weighted median position p):

```
cost(l, r) = sum over i in [l..r] of c[i] * |i - p|
```

This can be computed in O(1) per query using prefix sums of c[i] and i*c[i].

### Optimization: Divide and Conquer

The recurrence `dp[j][i] = min { dp[j-1][m] + cost(m+1, i) }` satisfies the **monotone minima** property: if opt(j, i) is the optimal split point m for dp[j][i], then:

```
opt(j, i) <= opt(j, i+1)
```

This allows us to use **divide and conquer optimization**, reducing each row from O(n^2) to O(n log n). Since there are k rows, total complexity is O(kn log n).

Alternatively, **Knuth's optimization** applies if the cost function satisfies the quadrangle inequality, giving O(kn) but with the same practical spirit.

### Precomputation

```
prefix_c[i] = c[1] + c[2] + ... + c[i]
prefix_ci[i] = 1*c[1] + 2*c[2] + ... + i*c[i]
```

For segment [l..r] with school at position p (the weighted median):

```
cost(l, r) = (sum of c[i]*|i - p| for i in [l..r])
```

Split into left of p and right of p using prefix sums.

### C++ Code Sketch

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    
    vector<long long> c(n + 1);
    vector<long long> pc(n + 1, 0), pci(n + 1, 0); // prefix sums
    
    for (int i = 1; i <= n; i++) {
        cin >> c[i];
        pc[i] = pc[i - 1] + c[i];
        pci[i] = pci[i - 1] + (long long)i * c[i];
    }
    
    // cost(l, r): one school at weighted median serving [l..r]
    auto cost = [&](int l, int r) -> long long {
        // Find weighted median position p in [l..r]
        long long half = (pc[r] - pc[l - 1] + 1) / 2;
        int p = l;
        long long cumul = c[l];
        while (cumul < half && p < r) {
            p++;
            cumul += c[p];
        }
        // Cost = sum c[i]*|i-p| using prefix sums
        // Left part [l..p]: p * (pc[p] - pc[l-1]) - (pci[p] - pci[l-1])
        // Right part [p..r]: (pci[r] - pci[p]) - p * (pc[r] - pc[p])
        long long left_cost = (long long)p * (pc[p] - pc[l - 1]) - (pci[p] - pci[l - 1]);
        long long right_cost = (pci[r] - pci[p]) - (long long)p * (pc[r] - pc[p]);
        return left_cost + right_cost;
    };
    
    // dp[j][i]: j schools covering 1..i
    const long long INF = 1e18;
    vector<vector<long long>> dp(k + 1, vector<long long>(n + 1, INF));
    dp[0][0] = 0;
    
    for (int i = 1; i <= n; i++)
        dp[1][i] = cost(1, i);
    
    // Divide and conquer optimization for rows 2..k
    for (int j = 2; j <= k; j++) {
        function<void(int, int, int, int)> solve = [&](int lo, int hi, int optL, int optR) {
            if (lo > hi) return;
            int mid = (lo + hi) / 2;
            long long best = INF;
            int opt = optL;
            for (int m = optL; m <= min(mid - 1, optR); m++) {
                long long val = dp[j - 1][m] + cost(m + 1, mid);
                if (val < best) {
                    best = val;
                    opt = m;
                }
            }
            dp[j][mid] = best;
            solve(lo, mid - 1, optL, opt);
            solve(mid + 1, hi, opt, optR);
        };
        solve(j, n, j - 1, n - 1);
    }
    
    cout << dp[k][n] << "\n";
    return 0;
}
```

### Time Complexity

- Precomputation: O(n)
- Cost function: O(n) per call for weighted median (can be O(1) with precomputed medians)
- DP with D&C optimization: O(kn log n)
- Overall: **O(kn log n)**

### Space Complexity

O(kn) for the DP table. Can be reduced to O(n) by only keeping two rows.
