# CSES Bài 3: Repetitions (Lặp lại)

## Đề bài

Cho một chuỗi DNA gồm các ký tự A, C, G và T. Nhiệm vụ của bạn là tìm đoạn lặp dài nhất trong chuỗi — tức là số lượng ký tự giống nhau liên tiếp lớn nhất.

**Đầu vào:** Một chuỗi có độ dài n (1 <= n <= 10^6)

**Đầu ra:** Độ dài của đoạn lặp liên tiếp dài nhất.

### Ví dụ

Đầu vào: `ATTCGGGA`

Đầu ra: `3` (chuỗi con "GGG")

---

## Lời giải

Duyệt từ trái sang phải, theo dõi độ dài đoạn lặp hiện tại và giá trị lớn nhất đã gặp.

### Thuật toán

```
1. current_run = 1, max_run = 1
2. Với i = 1 đến n-1:
   a. Nếu s[i] == s[i-1]: current_run += 1
   b. Ngược lại: current_run = 1
   c. max_run = max(max_run, current_run)
3. In max_run
```

### Cài đặt C++

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

### Độ phức tạp

- **Thời gian:** O(n) — duyệt một lần
- **Bộ nhớ:** O(1) phụ trợ
