# CSES Houses and Schools: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 20
- **Các hình:** Mảng (số trẻ em mỗi nhà, 6 ô), Bảng DP (3 hàng x 7 cột cho dp[j][i]), Mảng (hiển thị chi phí, 1 ô)
- **Ví dụ:** n=6, k=2, trẻ em=[2, 3, 5, 1, 4, 6]
- **Đáp án:** dp[2][6] = 12

## Mô tả từng khung hình

### Khung 0 (Giới thiệu)
- Tất cả các hình hiển thị ở trạng thái ban đầu
- Mảng hiển thị [2, 3, 5, 1, 4, 6] với nhãn 1..6
- Bảng DP trống (3 hàng cho j=0,1,2 và 7 cột cho i=0..6)
- Lời dẫn giới thiệu bài toán và công thức DP

### Khung 1 (Trường hợp cơ sở)
- dp[0][0] = 0, đánh dấu `done`
- Lời dẫn giải thích: không trường cho không nhà

### Khung 2-8 (Hàng j=1: một trường)
Mỗi khung tính dp[1][i] với i=1..6:
- Khung 2: dp[1][1]=0 (trường tại nhà 1)
- Khung 3: dp[1][2]=2 (trung vị tại nhà 2)
- Khung 4: dp[1][3]=7 (trung vị tại nhà 3)
- Khung 5: dp[1][4]=8 (trung vị tại nhà 3)
- Khung 6: dp[1][5]=16 (trung vị tại nhà 3)
- Khung 7: dp[1][6]=33 (trung vị dịch sang nhà 4)
- Khung 8: Tổng kết hàng 1, chuyển sang hàng 2

Hành vi trực quan:
- Ô đang tính là `current` (xanh dương), ô đã xong là `done` (xanh lá)
- Đoạn mảng [0..i-1] được tô sáng (tạm thời) cho thấy đoạn đang xét
- cost_val hiển thị giá trị cost(1, i) vừa tính

### Khung 9-18 (Hàng j=2: hai trường)
Mỗi khung tính dp[2][i] với i=2..6, cho thấy quá trình tìm điểm chia:
- Khung 9: dp[2][2]=0 (tầm thường: mỗi nhà một trường)
- Khung 10-11: dp[2][3]=2, thử m=1 và m=2, chọn m=2
- Khung 12-13: dp[2][4]=3, chia tối ưu tại m=2
- Khung 14-15: dp[2][5]=8, chia tại m=3 hoặc m=4
- Khung 16-17: dp[2][6]=12, chia tại m=4

Hành vi trực quan:
- Khi tính dp[2][i], đoạn bên phải đang tính chi phí được tô sáng trong mảng
- cost_val hiển thị giá trị cost(m+1, i) đang xét
- Lời dẫn đề cập tính đơn điệu của điểm chia tối ưu (cơ sở cho tối ưu chia để trị)

### Khung 19 (Đáp án cuối cùng)
- dp[2][6] đánh dấu `good` (xanh da trời)
- Nhà 3 và nhà 6 trong mảng đánh dấu `good` (vị trí đặt trường)
- cost_val hiển thị 12
- Lời dẫn: "Đáp án: dp[2][6] = 12. Trường đặt tại nhà 3 và nhà 6."
- Giải thích độ phức tạp O(kn log n) nhờ tối ưu chia để trị

## Bảng DP trạng thái cuối

```
j\i |  0     1     2     3     4     5     6
----+------------------------------------------
 0  |  0     -     -     -     -     -     -
 1  |  -     0     2     7     8    16    33
 2  |  -     -     0     2     3     8    12
```

## Đặc điểm trực quan

- **Bảng DP** điền từ trên xuống dưới (hàng j=1 rồi j=2), từ trái sang phải trong mỗi hàng
- **Vùng tô sáng trên mảng** cho thấy những nhà nào thuộc đoạn chi phí đang tính
- **Sự chuyển đổi màu:** idle -> current (đang tính) -> done (đã xong) -> good (ô đáp án)
- **cost_val** cập nhật mỗi khung để hiển thị kết quả hàm chi phí đang xét
- **Tính đơn điệu** được giải thích trong lời dẫn: điểm chia tối ưu dịch sang phải khi i tăng, biện minh cho tối ưu chia để trị
- Vị trí đặt trường (nhà 3 và nhà 6) được tô sáng ở khung cuối cùng
