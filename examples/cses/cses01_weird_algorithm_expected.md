# CSES 01 -- Thuật Toán Kỳ Lạ: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 17 (mỗi khung ứng với một giá trị trong dãy Collatz của n=7)
- **Các thành phần:** Mảng (giá trị hiện tại), Mảng (lịch sử dãy số), MetricPlot (đồ thị giá trị)
- **Dãy số:** 7, 22, 11, 34, 17, 52, 26, 13, 40, 20, 10, 5, 16, 8, 4, 2, 1

## Mô tả từng khung hình

### Khung hình 0
- `val`: [7] được tô sáng là giá trị hiện tại
- `seq`: ô đầu tiên hiển thị 7, các ô còn lại trống
- `plot`: điểm đầu tiên tại (0, 7)
- Thuyết minh: "Bắt đầu với n = 7. 7 là số lẻ, nên bước tiếp theo = 3*7 + 1 = 22"

### Khung hình 1--15 (Các bước trung gian)
Mỗi khung hình:
- `val` cập nhật sang giá trị mới
- `seq` điền vào ô tiếp theo, ô trước đó được đánh dấu `done`
- `plot` thêm một điểm dữ liệu mới thể hiện hình dạng "mưa đá"
- Thuyết minh giải thích n chẵn (chia cho 2) hay lẻ (3n+1)

Các thời điểm đáng chú ý:
- Khung hình 5 (n=52): giá trị đỉnh, đỉnh nhọn xuất hiện trên đồ thị
- Khung hình 11 (n=5): "3*5+1=16, lũy thừa của 2 -- sẽ chia đôi liên tục xuống 1"
- Khung hình 12--16: hạ dần đều 16, 8, 4, 2, 1

### Khung hình 16 (Kết thúc)
- `val`: [1] được đánh dấu `good` (xanh da trời)
- `seq`: tất cả 17 ô đã điền, toàn bộ đánh dấu `good`
- `plot`: đường cong "mưa đá" hoàn chỉnh
- Thuyết minh tóm tắt toàn bộ dãy số

## Đặc điểm hình ảnh
- MetricPlot tạo ra hình dạng "mưa đá" đặc trưng -- nhảy vọt ở bước lẻ, tụt xuống ở bước chẵn
- Mảng dãy số cung cấp dòng thời gian ngang hiển thị tất cả các giá trị
- Chuyển đổi màu sắc: chờ xử lý, đang xét (xanh dương), xong (xanh lá), hoàn tất (xanh da trời) ở cuối
