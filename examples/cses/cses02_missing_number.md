# CSES Bài 2: Số Bị Thiếu

## Đề bài

Cho tất cả các số nguyên từ 1 đến n, ngoại trừ một số. Nhiệm vụ của bạn là tìm số bị thiếu đó.

**Đầu vào:** Dòng đầu tiên chứa một số nguyên n. Dòng thứ hai chứa n-1 số nguyên, mỗi số đều khác nhau và nằm trong đoạn [1, n].

**Đầu ra:** In ra số bị thiếu.

**Ràng buộc:** 2 <= n <= 2 * 10^5

### Ví dụ

Đầu vào:
```
5
2 3 1 5
```

Đầu ra:
```
4
```

---

## Cách 1: Công thức tổng

Tổng các số nguyên từ 1 đến n là n(n+1)/2. Lấy tổng kỳ vọng trừ đi tổng của n-1 số đã cho sẽ ra số bị thiếu.

**Tại sao đúng:** Đúng một số bị thiếu, nên tổng_kỳ_vọng - tổng_thực_tế chính là số đó.

**Trường hợp đặc biệt:** Với n lớn, tổng có thể lên đến ~2 * 10^10, vừa đủ cho số nguyên 64-bit nhưng sẽ tràn số nguyên 32-bit. Dùng `long long` trong C++.

### Mã C++

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

**Độ phức tạp thời gian:** O(n)
**Độ phức tạp bộ nhớ:** O(1)

---

## Cách 2: XOR

XOR tất cả các số nguyên từ 1 đến n, rồi XOR với tất cả các số đã cho. Vì a XOR a = 0 với mọi a, nên mỗi số xuất hiện ở cả hai phía sẽ triệt tiêu nhau, chỉ còn lại số bị thiếu.

**Tại sao đúng:** XOR có tính kết hợp, giao hoán, và nghịch đảo của chính nó. Mỗi số có mặt trong cả dãy đầy đủ lẫn đầu vào sẽ triệt tiêu về 0.

### Mã C++

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

**Độ phức tạp thời gian:** O(n)
**Độ phức tạp bộ nhớ:** O(1)

---

## So sánh

| Cách tiếp cận | Nguy cơ tràn số | Phép tính mỗi phần tử |
|----------------|-----------------|----------------------|
| Công thức tổng | Có (dùng `long long`) | 1 phép cộng |
| XOR | Không (giới hạn bởi n) | 1 phép XOR |

Cả hai cách đều có độ phức tạp thời gian O(n) và bộ nhớ O(1). Cách XOR tránh hoàn toàn vấn đề tràn số, trong khi cách dùng công thức tổng trực quan hơn.
