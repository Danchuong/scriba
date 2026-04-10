# CSES Problem 3: Repetitions

## Problem Statement

You are given a DNA sequence: a string consisting of characters A, C, G, and T. Your task is to find the longest repetition in the string — that is, the maximum number of consecutive identical characters.

**Input:** A string of length n (1 <= n <= 10^6)

**Output:** The length of the longest consecutive repetition.

### Example

Input: `ATTCGGGA`

Output: `3` (the substring "GGG")

---

## Solution

Scan left to right, keeping track of the current run length and the maximum seen so far.

### Algorithm

```
1. current_run = 1, max_run = 1
2. For i = 1 to n-1:
   a. If s[i] == s[i-1]: current_run += 1
   b. Else: current_run = 1
   c. max_run = max(max_run, current_run)
3. Print max_run
```

### C++ Implementation

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    string s;
    cin >> s;

    int max_run = 1, cur = 1;
    for (int i = 1; i < (int)s.size(); i++) {
        if (s[i] == s[i-1]) {
            cur++;
        } else {
            cur = 1;
        }
        max_run = max(max_run, cur);
    }

    cout << max_run << endl;
    return 0;
}
```

### Complexity

- **Time:** O(n) — single pass
- **Space:** O(1) extra
