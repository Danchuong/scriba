# CSES Bài 5: Hoán vị

## Đề bài

Một hoán vị của các số nguyên 1, 2, ..., n được gọi là **hoán vị đẹp** nếu không tồn tại hai phần tử liền kề nào có hiệu bằng 1.

Cho n, hãy xây dựng một hoán vị đẹp nếu tồn tại.

**Đầu vào:** Một số nguyên n (1 <= n <= 10^6)

**Đầu ra:** Một hoán vị đẹp, hoặc "NO SOLUTION" nếu không tồn tại.

### Ví dụ

- n=1: `1`
- n=2: `NO SOLUTION` (chỉ có [1,2] và [2,1], cả hai đều có cặp liền kề hiệu bằng 1)
- n=3: `NO SOLUTION`
- n=4: `2 4 1 3`
- n=5: `2 4 1 3 5`

---

## Lời giải

**Chiến lược:** Đặt tất cả số chẵn trước, sau đó đặt tất cả số lẻ.

Với n >= 4: xuất ra `2, 4, 6, ..., 1, 3, 5, ...`

- Trong dãy số chẵn: mỗi cặp liền kề có hiệu bằng 2
- Trong dãy số lẻ: mỗi cặp liền kề có hiệu bằng 2
- Tại ranh giới (số chẵn cuối cùng, số lẻ đầu tiên): |n_chẵn - 1| >= 3 khi n >= 4

**Trường hợp đặc biệt:**
- n = 1: hiển nhiên `[1]`
- n = 2 hoặc n = 3: `NO SOLUTION`

### Cài đặt C++

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
        // Số chẵn trước, rồi số lẻ
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

### Độ phức tạp

- **Thời gian:** O(n)
- **Bộ nhớ:** O(1) (xuất trực tiếp)
