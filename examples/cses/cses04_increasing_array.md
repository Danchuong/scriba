# CSES Problem 4: Increasing Array

## Problem Statement

You are given an array of `n` integers. You want to modify the array so that it is
non-decreasing, i.e., every element is at least as large as the previous element.

In each move, you can increase the value of any element by one. What is the minimum
number of moves required?

**Input:** The first line contains an integer `n` (1 <= n <= 2 * 10^5). The second
line contains `n` integers a_1, a_2, ..., a_n (1 <= a_i <= 10^9).

**Output:** Print the minimum number of moves.

### Example

```
Input:
5
3 2 5 1 7

Output:
5
```

Explanation:

- Index 0: value 3. First element, no action needed.
- Index 1: value 2 < 3 (previous). Increase 2 -> 3. Cost = 1. Total = 1.
- Index 2: value 5 >= 3 (previous). No action needed.
- Index 3: value 1 < 5 (previous). Increase 1 -> 5. Cost = 4. Total = 5.
- Index 4: value 7 >= 5 (previous). No action needed.

Total moves = 1 + 4 = **5**.

## Solution

Scan the array left to right. Maintain a running maximum. Whenever `a[i]` is less than
the current maximum, we must increase `a[i]` to match the maximum, costing
`max - a[i]` moves. If `a[i]` is greater than or equal to the maximum, update the
maximum to `a[i]`.

This greedy approach is optimal because:
1. We can only increase elements, never decrease them.
2. Each element must be at least as large as its predecessor.
3. The cheapest way to satisfy the constraint is to raise each violating element to
   exactly the level of the previous element (i.e., the running maximum).

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;

    vector<long long> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }

    long long moves = 0;
    long long max_so_far = a[0];

    for (int i = 1; i < n; i++) {
        if (a[i] < max_so_far) {
            moves += max_so_far - a[i];
        } else {
            max_so_far = a[i];
        }
    }

    cout << moves << endl;
    return 0;
}
```

### Complexity

- **Time:** O(n) -- single pass through the array.
- **Space:** O(1) extra (beyond the input array).
