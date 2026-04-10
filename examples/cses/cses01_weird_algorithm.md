# CSES Problem 1: Weird Algorithm

## Problem Statement

Consider an algorithm that takes as input a positive integer **n**. If **n** is even, the algorithm divides it by two. If **n** is odd, the algorithm multiplies it by three and adds one. The algorithm repeats this until **n** is **1**.

Your task is to simulate this algorithm and print each value of **n**, including the first and last value.

### Input

A single integer n.

### Output

Print all values of n during the algorithm on a single line, separated by spaces.

### Constraints

- 1 <= n <= 10^6

### Example

**Input:** `3`

**Output:** `3 2 1`

**Input:** `7`

**Output:** `7 22 11 34 17 52 26 13 40 20 10 5 16 8 4 2 1`

---

## Solution

This problem requires straightforward simulation of the Collatz conjecture. There is no clever optimization needed -- just follow the rules until n reaches 1.

### Algorithm

```
1. Read n
2. Print n
3. While n != 1:
   a. If n is even: n = n / 2
   b. If n is odd:  n = 3 * n + 1
   c. Print n
```

### C++ Solution

```cpp
#include <iostream>
using namespace std;

int main() {
    long long n;
    cin >> n;
    
    cout << n;
    while (n != 1) {
        if (n % 2 == 0) {
            n /= 2;
        } else {
            n = 3 * n + 1;
        }
        cout << " " << n;
    }
    cout << "\n";
    return 0;
}
```

### Key Implementation Details

1. **Use `long long`**: Even though the input n <= 10^6, intermediate values can exceed 2^31 - 1. For example, starting from n = 113383, the sequence reaches values above 2.5 billion. Always use 64-bit integers.

2. **Output format**: Values are separated by spaces with no trailing space. The simplest approach is to print the first value, then print `" " + value` for each subsequent step.

### Time Complexity

The Collatz conjecture states that this sequence always reaches 1, but this is unproven in general. However, for n <= 10^6 the sequences are known to terminate and are practically short (the longest sequence for n <= 10^6 has around 525 steps). The algorithm runs in O(steps) time where "steps" is the length of the Collatz sequence, which is empirically O(log n) to O(n) but has no known tight theoretical bound.

### Space Complexity

O(1) -- we only store the current value of n.

---

## Why This Works

The problem is pure simulation. There is no mathematical shortcut. The only pitfall is integer overflow: since 3n + 1 can temporarily push values far above the original input, 32-bit integers are insufficient. With `long long`, all inputs within the constraint are safe.
