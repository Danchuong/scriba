# CSES Problem 5: Permutations

## Problem Statement

A permutation of integers 1, 2, ..., n is called **beautiful** if there are no two adjacent elements whose difference is 1.

Given n, construct a beautiful permutation if one exists.

**Input:** An integer n (1 <= n <= 10^6)

**Output:** A beautiful permutation, or "NO SOLUTION" if none exists.

### Examples

- n=1: `1`
- n=2: `NO SOLUTION` (only [1,2] and [2,1], both have adjacent diff 1)
- n=3: `NO SOLUTION`
- n=4: `2 4 1 3`
- n=5: `2 4 1 3 5`

---

## Solution

**Strategy:** Place all even numbers first, then all odd numbers.

For n >= 4: output `2, 4, 6, ..., 1, 3, 5, ...`

- Within evens: each pair differs by 2
- Within odds: each pair differs by 2
- At the boundary (last even, first odd): |n_even - 1| >= 3 for n >= 4

**Edge cases:**
- n = 1: trivially `[1]`
- n = 2 or n = 3: `NO SOLUTION`

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;

    if (n == 1) {
        cout << 1 << endl;
    } else if (n <= 3) {
        cout << "NO SOLUTION" << endl;
    } else {
        // Evens first, then odds
        for (int i = 2; i <= n; i += 2) {
            cout << i << " ";
        }
        for (int i = 1; i <= n; i += 2) {
            cout << i << " ";
        }
        cout << endl;
    }

    return 0;
}
```

### Complexity

- **Time:** O(n)
- **Space:** O(1) (streaming output)
