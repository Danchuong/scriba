# CSES: Chuyến thang máy

## Đề bài

Có **n** người cần sử dụng thang máy. Bạn biết cân nặng của từng người. Thang máy có sức chứa tối đa **x**. Hỏi số chuyến thang máy ít nhất cần thiết để chở hết tất cả n người? Mỗi người chỉ đi thang máy đúng một lần.

### Đầu vào

Dòng đầu tiên chứa hai số nguyên n và x: số người và sức chứa tối đa.

Dòng thứ hai chứa n số nguyên w_1, w_2, ..., w_n: cân nặng của mỗi người.

### Đầu ra

In ra số chuyến thang máy ít nhất.

### Ràng buộc

- 1 <= n <= 20
- 1 <= x <= 10^9
- 1 <= w_i <= x

### Ví dụ

**Đầu vào:**
```
4 8
3 5 2 7
```

**Đầu ra:**
```
3
```

Giải thích: Với cân nặng [3, 5, 2, 7] và sức chứa 8: chuyến 1 chở {3, 5} (tổng 8), chuyến 2 chở {2} (tổng 2), chuyến 3 chở {7} (tổng 7). Tổng cân nặng là 3+5+2+7 = 17 > 2*8 = 16, nên không thể chở hết trong 2 chuyến. Số chuyến tối thiểu là **3**.

---

## Cách tiếp cận: QHĐ Bitmask

Vì n <= 20, ta có thể biểu diễn mỗi tập con người dưới dạng bitmask. Với mỗi tập con (mask), ta tính cách xếp tối ưu vào các chuyến thang máy.

### Trạng thái

Với mỗi bitmask `mask` (biểu diễn những người đã được chở), lưu một cặp:

```
dp[mask] = (số_chuyến, sức_chứa_còn_lại)
```

- `số_chuyến`: số chuyến thang máy tối thiểu để chở đúng những người trong `mask`
- `sức_chứa_còn_lại`: sức chứa còn lại tối đa trong chuyến cuối cùng (trong tất cả các cách sắp xếp đạt được `số_chuyến` chuyến)

Ta muốn tối thiểu hóa `số_chuyến` trước, và trong các trường hợp bằng nhau, tối đa hóa `sức_chứa_còn_lại` (tham lam: để lại càng nhiều chỗ trống trong chuyến hiện tại càng tốt cho những người tiếp theo).

### Trường hợp cơ sở

```
dp[0] = (1, x)
```

Chưa chở ai. Ta bắt đầu với 1 chuyến có đầy đủ sức chứa x.

### Chuyển trạng thái

Với mỗi mask, thử thêm từng người i chưa có trong mask (bit i bằng 0):

```
new_mask = mask | (1 << i)
```

Nếu người i vừa chuyến hiện tại (`w[i] <= sức_chứa_còn_lại`):
- ứng_viên = (số_chuyến, sức_chứa_còn_lại - w[i])

Ngược lại, mở chuyến mới:
- ứng_viên = (số_chuyến + 1, x - w[i])

Cập nhật `dp[new_mask]` nếu ứng viên tốt hơn (ít chuyến hơn, hoặc cùng số chuyến nhưng còn nhiều chỗ trống hơn).

### Đáp án

```
dp[(1 << n) - 1].số_chuyến
```

Bitmask đầy đủ với tất cả n người đã được chở.

### Cài đặt C++

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, x;
    cin >> n >> x;

    vector<int> w(n);
    for (int i = 0; i < n; i++) {
        cin >> w[i];
    }

    int full = 1 << n;
    // dp[mask] = {số_chuyến, sức_chứa_còn_lại}
    vector<pair<int,int>> dp(full, {n + 1, 0});
    dp[0] = {1, x};

    for (int mask = 0; mask < full; mask++) {
        if (dp[mask].first > n) continue;
        for (int i = 0; i < n; i++) {
            if (mask & (1 << i)) continue;
            int new_mask = mask | (1 << i);
            pair<int,int> candidate;
            if (w[i] <= dp[mask].second) {
                candidate = {dp[mask].first, dp[mask].second - w[i]};
            } else {
                candidate = {dp[mask].first + 1, x - w[i]};
            }
            // Tốt hơn = ít chuyến hơn, hoặc cùng số chuyến nhưng còn nhiều chỗ hơn
            if (candidate.first < dp[new_mask].first ||
                (candidate.first == dp[new_mask].first &&
                 candidate.second > dp[new_mask].second)) {
                dp[new_mask] = candidate;
            }
        }
    }

    cout << dp[full - 1].first << "\n";
    return 0;
}
```

### Độ phức tạp

- **Thời gian:** O(2^n * n). Có 2^n tập con, với mỗi tập con ta thử n người.
- **Bộ nhớ:** O(2^n) cho bảng QHĐ.

---

## Tại sao cách này đúng

Ý tưởng then chốt là so sánh theo thứ tự từ điển (số_chuyến, -sức_chứa_còn_lại). Bằng cách tối thiểu hóa số chuyến trước và tối đa hóa sức chứa còn lại sau, ta tham lam xếp người vào ít chuyến nhất có thể. Bitmask đảm bảo ta xét mọi cách phân nhóm mà không bị trùng lặp. Vì n <= 20, tổng số phép tính 2^20 * 20 ~ 20 triệu hoàn toàn chạy được trong giới hạn thời gian.
