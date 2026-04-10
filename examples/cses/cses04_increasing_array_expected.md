# CSES 04 — Increasing Array: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 9
- **Đối tượng:** 2 mảng (mảng chính + bộ đếm chi phí)
- **Luồng trực quan:** Duyệt từ trái sang phải, vi phạm hiển thị màu đỏ rồi được sửa

## Mô tả từng khung hình

### Khung 0 (Khởi tạo)
- `a`: [3, 2, 5, 1, 7] tất cả ở trạng thái chờ
- `cost`: [0]
- Lời dẫn giải thích đề bài

### Khung 1 (Vị trí 0)
- cell[0] đánh dấu `done` — phần tử đầu tiên luôn hợp lệ
- Max hiện tại = 3

### Khung 2 (Vị trí 1 — VI PHẠM)
- cell[1] đánh dấu `error` (đỏ) — giá trị 2 < 3
- Lời dẫn: cần tăng thêm 1

### Khung 3 (Vị trí 1 — SỬA)
- cell[1] giá trị thay đổi 2 -> 3, đánh dấu `done`
- cost = 1

### Khung 4 (Vị trí 2 — HỢP LỆ)
- cell[2] đánh dấu `current` rồi `done` — 5 >= 3

### Khung 5 (Vị trí 3 — VI PHẠM)
- cell[3] đánh dấu `error` — giá trị 1 < 5
- Lời dẫn: cần tăng thêm 4

### Khung 6 (Vị trí 3 — SỬA)
- cell[3] giá trị thay đổi 1 -> 5, đánh dấu `done`
- cost = 5

### Khung 7 (Vị trí 4 — HỢP LỆ)
- cell[4] đang xét — 7 >= 5

### Khung 8 (Kết thúc)
- Tất cả ô đánh dấu `good` (xanh da trời)
- cost đánh dấu `good`
- Lời dẫn: "Tổng thao tác = 5"

## Đặc điểm trực quan
- Trạng thái `error` (đỏ) đánh dấu rõ ràng các vi phạm trước khi sửa
- Giá trị cập nhật trực tiếp tại chỗ để minh họa thao tác "tăng"
- Bộ đếm chi phí theo dõi tổng tích lũy
