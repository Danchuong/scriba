# CSES 02 -- Số Bị Thiếu: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 9
- **Các thành phần:** 2 Mảng (dãy số đã cho + bảng tính toán)
- **Luồng hình ảnh:** Duyệt từ trái sang phải, cộng dồn tổng

## Mô tả từng khung hình

### Khung hình 0 (Khởi tạo)
- `arr`: [1, 2, 3, 4, 6, 7, 8] tất cả ở trạng thái chờ
- `info`: [36, 0, 0] -- tổng kỳ vọng đã điền sẵn, tổng thực tế và số thiếu bằng 0
- Thuyết minh giải thích cách tiếp cận dùng công thức tổng

### Khung hình 1--7 (Duyệt mảng)
Mỗi khung hình:
- Tô sáng phần tử đang xét (viền vàng, tạm thời)
- Các phần tử trước đó đánh dấu `done` (xanh lá)
- `info.cell[1]` (tổng thực tế) được cập nhật với tổng cộng dồn
- Thuyết minh trình bày phép tính

Thời điểm đáng chú ý -- Khung hình 5 (chỉ số 4, giá trị = 6):
- Thuyết minh chỉ ra khoảng trống: nhảy từ 4 sang 6, gợi ý vị trí của số 5

### Khung hình 8 (Kết quả)
- Tất cả ô trong `arr` đánh dấu `done` (xanh lá)
- `info.cell[2]` (số thiếu) được gán giá trị 5 với trạng thái `good` (xanh da trời)
- Thuyết minh: "Số bị thiếu = 36 - 31 = 5"

## Đặc điểm hình ảnh
- Mảng `info` đóng vai trò bảng điều khiển hiển thị tổng kỳ vọng / tổng thực tế / số thiếu
- Mẫu duyệt (tô sáng phần tử hiện tại, đánh dấu xong cho phần tử trước) tạo ra tiến trình rõ ràng từ trái sang phải
