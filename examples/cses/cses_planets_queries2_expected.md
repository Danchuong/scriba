# CSES Planets Queries II: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 20
- **Các hình:** Đồ thị (6 đỉnh, 2 chu trình có hướng), Bảng DP (3x6 bảng binary lifting), Mảng (hiển thị đáp án)
- **Đồ thị ví dụ:** Hai chu trình độ dài 3: 1->2->3->1 và 4->5->6->4
- **Các truy vấn minh họa:** (1,3) = 2, (4,2) = -1, (1,1) = 0

## Mô tả từng khung hình

### Khung 0 -- Giới thiệu đồ thị
- Đồ thị hiển thị với 6 đỉnh và 6 cạnh có hướng, tất cả ở trạng thái nhàn rỗi
- Bảng DP và mảng đáp án hiển thị nhưng còn trống
- Lời dẫn: giới thiệu khái niệm đồ thị hàm (bậc ra = 1, thành phần dạng chữ rho)

### Khung 1 -- Tô sáng thành phần 1
- Các đỉnh 1, 2, 3 và cạnh (1,2), (2,3), (3,1) chuyển sang `current` (xanh dương)
- Lời dẫn: xác định chu trình đầu tiên có độ dài 3

### Khung 2 -- Tô sáng thành phần 2
- Thành phần 1 trở về trạng thái nhàn rỗi
- Các đỉnh 4, 5, 6 và cạnh (4,5), (5,6), (6,4) chuyển sang `current`
- Lời dẫn: xác định chu trình thứ hai, lưu ý không thể đi giữa các thành phần

### Khung 3 -- Thiết lập bảng
- Tất cả đỉnh đồ thị trở về trạng thái nhàn rỗi
- Lời dẫn: giới thiệu cấu trúc bảng binary lifting (hàng = k, cột = đỉnh)

### Khung 4 -- Điền lift[0] (1 bước)
- Hàng 0 của bảng DP được điền: [2, 3, 1, 5, 6, 4]
- Các ô hàng 0 đánh dấu `current`
- Lời dẫn: giải thích lift[0][i] = t[i], đích dịch chuyển trực tiếp

### Khung 5 -- Điền lift[1] (2 bước)
- Các ô hàng 0 chuyển sang `done`
- Hàng 1 được điền: [3, 1, 2, 6, 4, 5]
- Các ô hàng 1 đánh dấu `current`
- Lời dẫn: giải thích công thức nhảy đôi lift[1][i] = lift[0][lift[0][i]]

### Khung 6 -- Điền lift[2] (4 bước)
- Các ô hàng 1 chuyển sang `done`
- Hàng 2 được điền: [2, 3, 1, 5, 6, 4]
- Các ô hàng 2 đánh dấu `current`
- Lời dẫn: 4 mod 3 = 1, nên lift[2] trùng với lift[0] do độ dài chu trình

### Khung 7 -- Hoàn thành bảng
- Tất cả ô bảng DP chuyển sang `done`
- Lời dẫn: bảng hoàn thành, sẵn sàng trả lời truy vấn

### Khung 8 -- Thiết lập truy vấn 1: (1, 3)
- Đỉnh 1 chuyển sang `current`, đỉnh 3 được tô sáng (tạm thời)
- Đáp án hiển thị "?"
- Lời dẫn: giới thiệu truy vấn, cả hai đỉnh cùng thành phần

### Khung 9 -- Truy vấn 1 bước 1
- Cạnh (1,2) chuyển sang `current`, đỉnh 2 chuyển sang `done`
- Đỉnh 3 vẫn được tô sáng
- Lời dẫn: lần dịch chuyển đầu tiên, 1 -> 2

### Khung 10 -- Truy vấn 1 bước 2
- Cạnh (2,3) chuyển sang `current`, cạnh (1,2) chuyển sang `done`
- Đỉnh 1 chuyển sang `done`, đỉnh 3 chuyển sang `good` (xanh da trời)
- Lời dẫn: lần dịch chuyển thứ hai, 2 -> 3, đã đến đích, khoảng cách = 2

### Khung 11 -- Đáp án truy vấn 1
- Đáp án cập nhật thành "2", đánh dấu `good`
- Lời dẫn: xác nhận đáp án = 2

### Khung 12 -- Thiết lập truy vấn 2: (4, 2)
- Đồ thị trở về trạng thái nhàn rỗi
- Đỉnh 4 chuyển sang `current`, đỉnh 2 được tô sáng
- Đáp án trở về "?"
- Lời dẫn: truy vấn giữa hai thành phần khác nhau

### Khung 13 -- Từ chối truy vấn 2
- Đỉnh 4 và 2 chuyển sang `error` (đỏ)
- Tất cả cạnh bị mờ đi
- Lời dẫn: khác thành phần, không thể đến được

### Khung 14 -- Đáp án truy vấn 2
- Đáp án cập nhật thành "-1", đánh dấu `error`
- Lời dẫn: xác nhận đáp án = -1

### Khung 15 -- Thiết lập truy vấn bổ sung: (1, 1)
- Đồ thị trở về trạng thái nhàn rỗi
- Đỉnh 1 chuyển sang `current` và được tô sáng
- Đáp án trở về "?"
- Lời dẫn: cùng nguồn và đích

### Khung 16 -- Đáp án truy vấn bổ sung
- Đáp án cập nhật thành "0", đánh dấu `good`
- Đỉnh 1 đánh dấu `good`
- Lời dẫn: không cần dịch chuyển, đã ở tại đích

### Khung 17 -- Thảo luận về đỉnh đuôi
- Đồ thị và bảng trở về trạng thái nhàn rỗi
- Lời dẫn: giải thích cách xử lý các đỉnh đuôi (cây treo vào chu trình) bằng cách tính độ sâu

### Khung 18 -- Tổng kết
- Tất cả đỉnh và cạnh đánh dấu `good` (xanh da trời)
- Lời dẫn: tóm tắt thuật toán -- binary lifting + phát hiện chu trình, tổng độ phức tạp O((n+q) log n)

## Đặc điểm trực quan

- **Đồ thị** sử dụng bố cục cố định với cạnh có hướng cho thấy hai chu trình 3 đỉnh riêng biệt
- **Bảng DP** hiển thị bảng binary lifting được điền từng hàng (k=0,1,2)
- **Sự chuyển đổi màu:**
  - `idle` (xám) -- trạng thái mặc định
  - `current` (xanh dương) -- đỉnh đang hoạt động hoặc đang xử lý
  - `done` (xanh lá) -- đã được duyệt
  - `good` (xanh da trời) -- đã tìm thấy đáp án / thành công
  - `error` (đỏ) -- không thể / không đến được
  - `dim` (mờ) -- cạnh không liên quan
- **highlight** (vàng tạm thời) đánh dấu đỉnh đích trong quá trình duyệt truy vấn
- Hoạt ảnh minh họa ba loại truy vấn khác nhau: cùng chu trình và đến được, khác thành phần và không đến được, và truy vấn tầm thường (cùng đỉnh)
