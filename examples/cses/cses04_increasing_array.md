# CSES Bài 4: Increasing Array (Mảng tăng dần)

## Đề bài

Cho một mảng gồm `n` số nguyên. Bạn cần biến đổi mảng sao cho nó không giảm, tức là mỗi phần tử phải lớn hơn hoặc bằng phần tử đứng trước nó.

Mỗi thao tác, bạn có thể tăng giá trị của một phần tử bất kỳ lên 1. Hỏi số thao tác tối thiểu cần thực hiện là bao nhiêu?

**Đầu vào:** Dòng đầu chứa số nguyên `n` (1 <= n <= 2 * 10^5). Dòng thứ hai chứa `n` số nguyên a_1, a_2, ..., a_n (1 <= a_i <= 10^9).

**Đầu ra:** In ra số thao tác tối thiểu.

### Ví dụ

```
Đầu vào:
5
3 2 5 1 7

Đầu ra:
5
```

Giải thích:

- Vị trí 0: giá trị 3. Phần tử đầu tiên, không cần xử lý.
- Vị trí 1: giá trị 2 < 3 (phần tử trước). Tăng 2 -> 3. Chi phí = 1. Tổng = 1.
- Vị trí 2: giá trị 5 >= 3 (phần tử trước). Không cần xử lý.
- Vị trí 3: giá trị 1 < 5 (phần tử trước). Tăng 1 -> 5. Chi phí = 4. Tổng = 5.
- Vị trí 4: giá trị 7 >= 5 (phần tử trước). Không cần xử lý.

Tổng số thao tác = 1 + 4 = **5**.

## Lời giải

Duyệt mảng từ trái sang phải, duy trì giá trị lớn nhất đã gặp. Khi `a[i]` nhỏ hơn giá trị lớn nhất hiện tại, ta phải tăng `a[i]` lên bằng giá trị đó, tốn `max - a[i]` thao tác. Nếu `a[i]` lớn hơn hoặc bằng giá trị lớn nhất, ta cập nhật giá trị lớn nhất thành `a[i]`.

Cách tiếp cận tham lam này là tối ưu vì:
1. Ta chỉ có thể tăng phần tử, không thể giảm.
2. Mỗi phần tử phải lớn hơn hoặc bằng phần tử đứng trước.
3. Cách rẻ nhất để thỏa mãn điều kiện là nâng mỗi phần tử vi phạm lên đúng bằng giá trị của phần tử trước đó (tức giá trị lớn nhất đang duy trì).

### Cài đặt C++

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

### Độ phức tạp

- **Thời gian:** O(n) -- duyệt mảng một lần.
- **Bộ nhớ:** O(1) phụ trợ (ngoài mảng đầu vào).
