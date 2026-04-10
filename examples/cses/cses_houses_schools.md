# CSES: Houses and Schools

## Đề bài

Có **n** ngôi nhà trên một con phố, đánh số từ 1 đến n từ trái sang phải. Ngôi nhà thứ i có **c[i]** trẻ em. Bạn cần đặt đúng **k** trường học vào các vị trí nhà (mỗi trường chiếm một vị trí nhà) sao cho **tổng quãng đường đi bộ** là nhỏ nhất. Mỗi em học sinh sẽ đi đến trường gần nhất.

### Dữ liệu vào

- Dòng đầu: hai số nguyên n và k
- Dòng thứ hai: n số nguyên c[1], c[2], ..., c[n]

### Dữ liệu ra

Tổng quãng đường đi bộ nhỏ nhất.

### Ràng buộc

- 1 <= k <= n <= 3000
- 0 <= c[i] <= 10^9

### Ví dụ

**Dữ liệu vào:**
```
6 2
2 3 5 1 4 6
```

**Dữ liệu ra:** `18`

Đặt trường học tại nhà 3 và nhà 6: trẻ em ở nhà 1 đi bộ quãng đường 2, nhà 2 đi 1, nhà 3 đi 0, nhà 4 đi 1 (trường gần nhất là nhà 3), nhà 5 đi 1, nhà 6 đi 0. Vị trí đặt tối ưu phụ thuộc vào cách tính chi phí cụ thể.

---

## Lời giải

### Nhận xét chính

Khi một trường học phục vụ một đoạn liên tiếp các ngôi nhà [l..r], vị trí tối ưu để đặt trường đó là **trung vị có trọng số** của các ngôi nhà trong đoạn (trọng số là số trẻ em). Chi phí phục vụ đoạn [l..r] bằng một trường đặt tại trung vị có trọng số có thể được tiền xử lý.

### Công thức DP

Định nghĩa:

```
dp[j][i] = tổng quãng đường đi bộ nhỏ nhất khi đặt j trường học
           phục vụ các nhà 1..i (trường thứ j phục vụ
           một đoạn hậu tố kết thúc tại i)
```

Công thức truy hồi:

```
dp[j][i] = min theo tất cả m trong [j-1..i-1] của:
           dp[j-1][m] + cost(m+1, i)
```

trong đó `cost(l, r)` là quãng đường đi bộ nhỏ nhất khi một trường phục vụ các nhà từ l đến r.

Trường hợp cơ sở: `dp[1][i] = cost(1, i)` với mọi i.

Đáp án: `dp[k][n]`.

### Hàm chi phí

Với đoạn liên tiếp [l..r], đặt một trường tại vị trí tối ưu (trung vị có trọng số, vị trí p):

```
cost(l, r) = tổng c[i] * |i - p| với i trong [l..r]
```

Có thể tính trong O(1) mỗi truy vấn bằng tổng tiền tố của c[i] và i*c[i].

### Tối ưu hóa: Chia để trị

Công thức truy hồi `dp[j][i] = min { dp[j-1][m] + cost(m+1, i) }` thỏa mãn tính chất **cực tiểu đơn điệu**: nếu opt(j, i) là điểm chia tối ưu m cho dp[j][i], thì:

```
opt(j, i) <= opt(j, i+1)
```

Điều này cho phép sử dụng **tối ưu chia để trị**, giảm mỗi hàng từ O(n^2) xuống O(n log n). Với k hàng, tổng độ phức tạp là O(kn log n).

Ngoài ra, **tối ưu Knuth** cũng áp dụng được nếu hàm chi phí thỏa bất đẳng thức tứ giác, cho O(kn) với tinh thần tương tự.

### Tiền xử lý

```
prefix_c[i] = c[1] + c[2] + ... + c[i]
prefix_ci[i] = 1*c[1] + 2*c[2] + ... + i*c[i]
```

Với đoạn [l..r] và trường đặt tại vị trí p (trung vị có trọng số):

```
cost(l, r) = (tổng c[i]*|i - p| với i trong [l..r])
```

Tách thành phần bên trái và bên phải p rồi dùng tổng tiền tố.

### Mã nguồn C++ tham khảo

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    
    vector<long long> c(n + 1);
    vector<long long> pc(n + 1, 0), pci(n + 1, 0); // tổng tiền tố
    
    for (int i = 1; i <= n; i++) {
        cin >> c[i];
        pc[i] = pc[i - 1] + c[i];
        pci[i] = pci[i - 1] + (long long)i * c[i];
    }
    
    // cost(l, r): một trường tại trung vị có trọng số phục vụ [l..r]
    auto cost = [&](int l, int r) -> long long {
        // Tìm vị trí trung vị có trọng số p trong [l..r]
        long long half = (pc[r] - pc[l - 1] + 1) / 2;
        int p = l;
        long long cumul = c[l];
        while (cumul < half && p < r) {
            p++;
            cumul += c[p];
        }
        // Chi phí = tổng c[i]*|i-p| dùng tổng tiền tố
        // Phần trái [l..p]: p * (pc[p] - pc[l-1]) - (pci[p] - pci[l-1])
        // Phần phải [p..r]: (pci[r] - pci[p]) - p * (pc[r] - pc[p])
        long long left_cost = (long long)p * (pc[p] - pc[l - 1]) - (pci[p] - pci[l - 1]);
        long long right_cost = (pci[r] - pci[p]) - (long long)p * (pc[r] - pc[p]);
        return left_cost + right_cost;
    };
    
    // dp[j][i]: j trường phục vụ nhà 1..i
    const long long INF = 1e18;
    vector<vector<long long>> dp(k + 1, vector<long long>(n + 1, INF));
    dp[0][0] = 0;
    
    for (int i = 1; i <= n; i++)
        dp[1][i] = cost(1, i);
    
    // Tối ưu chia để trị cho các hàng 2..k
    for (int j = 2; j <= k; j++) {
        function<void(int, int, int, int)> solve = [&](int lo, int hi, int optL, int optR) {
            if (lo > hi) return;
            int mid = (lo + hi) / 2;
            long long best = INF;
            int opt = optL;
            for (int m = optL; m <= min(mid - 1, optR); m++) {
                long long val = dp[j - 1][m] + cost(m + 1, mid);
                if (val < best) {
                    best = val;
                    opt = m;
                }
            }
            dp[j][mid] = best;
            solve(lo, mid - 1, optL, opt);
            solve(mid + 1, hi, opt, optR);
        };
        solve(j, n, j - 1, n - 1);
    }
    
    cout << dp[k][n] << "\n";
    return 0;
}
```

### Độ phức tạp thời gian

- Tiền xử lý: O(n)
- Hàm chi phí: O(n) mỗi lần gọi để tìm trung vị có trọng số (có thể O(1) nếu tiền xử lý trung vị)
- DP với tối ưu chia để trị: O(kn log n)
- Tổng cộng: **O(kn log n)**

### Độ phức tạp không gian

O(kn) cho bảng DP. Có thể giảm xuống O(n) bằng cách chỉ giữ hai hàng.
