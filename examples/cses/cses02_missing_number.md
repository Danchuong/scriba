# CSES Problem 2: Missing Number

## Problem Statement

You are given all integers between 1 and n except one. Your task is to find the missing number.

**Input:** The first line contains an integer n. The second line contains n-1 integers, each distinct and in the range [1, n].

**Output:** Print the missing number.

**Constraints:** 2 <= n <= 2 * 10^5

### Example

Input:
```
5
2 3 1 5
```

Output:
```
4
```

---

## Approach 1: Sum Formula

The sum of integers from 1 to n is n(n+1)/2. Subtract the sum of the given n-1 numbers from this expected sum to get the missing number.

**Why it works:** Exactly one number is missing, so expected_sum - actual_sum isolates that number.

**Edge case:** For large n, the sum can reach ~2 * 10^10, which fits in a 64-bit integer but overflows a 32-bit one. Use `long long` in C++.

### C++ Code

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    cin >> n;

    long long expected_sum = n * (n + 1) / 2;
    long long actual_sum = 0;

    for (int i = 0; i < n - 1; i++) {
        long long x;
        cin >> x;
        actual_sum += x;
    }

    cout << expected_sum - actual_sum << "\n";
    return 0;
}
```

**Time complexity:** O(n)
**Space complexity:** O(1)

---

## Approach 2: XOR

XOR all integers from 1 to n, then XOR all the given numbers. Because a XOR a = 0 for any a, every number that appears in both cancels out, leaving only the missing number.

**Why it works:** XOR is associative, commutative, and self-inverse. Every number present in both the full range and the input cancels to zero.

### C++ Code

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    int xor_all = 0;
    for (int i = 1; i <= n; i++) {
        xor_all ^= i;
    }

    int xor_given = 0;
    for (int i = 0; i < n - 1; i++) {
        int x;
        cin >> x;
        xor_given ^= x;
    }

    cout << (xor_all ^ xor_given) << "\n";
    return 0;
}
```

**Time complexity:** O(n)
**Space complexity:** O(1)

---

## Comparison

| Approach | Overflow risk | Operations per element |
|----------|--------------|----------------------|
| Sum formula | Yes (use `long long`) | 1 addition |
| XOR | No (bounded by n) | 1 XOR |

Both approaches are O(n) time and O(1) space. The XOR approach avoids overflow entirely, while the sum approach is more intuitive.
