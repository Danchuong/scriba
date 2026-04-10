# CSES Bài 1: Thuật Toán Kỳ Lạ

## Đề bài

Cho một thuật toán nhận đầu vào là một số nguyên dương **n**. Nếu **n** chẵn, thuật toán chia nó cho hai. Nếu **n** lẻ, thuật toán nhân nó với ba rồi cộng thêm một. Thuật toán lặp lại quá trình này cho đến khi **n** bằng **1**.

Nhiệm vụ của bạn là mô phỏng thuật toán trên và in ra tất cả các giá trị của **n**, bao gồm giá trị đầu tiên và giá trị cuối cùng.

### Đầu vào

Một số nguyên duy nhất n.

### Đầu ra

In tất cả các giá trị của n trong quá trình thực hiện thuật toán trên một dòng, cách nhau bởi dấu cách.

### Ràng buộc

- 1 <= n <= 10^6

### Ví dụ

**Đầu vào:** `3`

**Đầu ra:** `3 2 1`

**Đầu vào:** `7`

**Đầu ra:** `7 22 11 34 17 52 26 13 40 20 10 5 16 8 4 2 1`

---

## Lời giải

Bài này chỉ yêu cầu mô phỏng trực tiếp giả thuyết Collatz. Không cần tối ưu gì phức tạp -- chỉ cần thực hiện đúng các phép tính cho đến khi n về 1.

### Thuật toán

```
1. Đọc n
2. In n
3. Khi n != 1:
   a. Nếu n chẵn: n = n / 2
   b. Nếu n lẻ:  n = 3 * n + 1
   c. In n
```

### Lời giải C++

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

### Chi tiết cài đặt quan trọng

1. **Dùng `long long`**: Mặc dù đầu vào n <= 10^6, các giá trị trung gian có thể vượt quá 2^31 - 1. Ví dụ, bắt đầu từ n = 113383, dãy số đạt tới các giá trị trên 2,5 tỷ. Luôn dùng số nguyên 64-bit.

2. **Định dạng đầu ra**: Các giá trị cách nhau bởi dấu cách, không có dấu cách thừa ở cuối. Cách đơn giản nhất là in giá trị đầu tiên, sau đó in `" " + giá trị` cho mỗi bước tiếp theo.

### Độ phức tạp thời gian

Giả thuyết Collatz khẳng định rằng dãy số này luôn kết thúc ở 1, nhưng điều này chưa được chứng minh tổng quát. Tuy nhiên, với n <= 10^6, các dãy số đều kết thúc và có độ dài tương đối ngắn (dãy dài nhất với n <= 10^6 có khoảng 525 bước). Thuật toán chạy trong O(số bước), trong đó "số bước" là độ dài dãy Collatz -- theo thực nghiệm vào khoảng O(log n) đến O(n), nhưng chưa có cận chặt về mặt lý thuyết.

### Độ phức tạp bộ nhớ

O(1) -- ta chỉ lưu giá trị hiện tại của n.

---

## Tại sao lời giải này đúng

Bài toán là mô phỏng thuần túy. Không có thủ thuật toán học nào cả. Cạm bẫy duy nhất là tràn số: vì phép tính 3n + 1 có thể đẩy giá trị lên rất cao so với đầu vào ban đầu, nên số nguyên 32-bit là không đủ. Với `long long`, mọi đầu vào trong phạm vi ràng buộc đều an toàn.
