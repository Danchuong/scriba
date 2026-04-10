# CSES 03 — Repetitions: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 9
- **Đối tượng:** 2 mảng (chuỗi DNA + biến theo dõi)
- **Luồng trực quan:** Duyệt từ trái sang phải, theo dõi độ dài đoạn lặp

## Mô tả từng khung hình

### Khung 0
- `dna`: ["A","T","T","C","G","G","G","A"], cell[0] = đang xét (xanh dương)
- `vars`: [1, 1] — đoạn lặp hiện tại và max
- Lời dẫn: ký tự đầu A, run=1, max=1

### Khung 1 (vị trí 1, T != A)
- cell[0] đã xử lý (xanh lá), cell[1] đang xét (xanh dương)
- vars không đổi [1, 1]
- Bắt đầu đoạn lặp mới

### Khung 2 (vị trí 2, T == T)
- cell[2] đang xét, vars = [2, 2]
- Đoạn lặp kéo dài

### Khung 3 (vị trí 3, C != T)
- cell[3] đang xét, vars.cell[0] = 1
- Đoạn lặp mới

### Khung 4 (vị trí 4, G != C)
- cell[4] đang xét, vars.cell[0] = 1
- Đoạn lặp mới

### Khung 5 (vị trí 5, G == G)
- cell[5] đang xét, vars.cell[0] = 2
- Đoạn lặp kéo dài thành 2

### Khung 6 (vị trí 6, G == G) — KHOẢNH KHẮC QUAN TRỌNG
- cell[6] đang xét, vars = [3, 3]
- vars.cell[1] chuyển sang trạng thái `good` (xanh da trời)
- Tìm được max mới!

### Khung 7 (vị trí 7, A != G)
- cell[7] đang xét, vars.cell[0] = 1
- max vẫn là 3

### Khung 8 (Kết thúc)
- cell[7] đã xử lý, cells[4:6] đánh dấu `good` (xanh da trời) — chuỗi con GGG
- Lời dẫn: "Đáp án: 3"

## Đặc điểm trực quan
- Chuỗi con GGG (vị trí 4-6) được tô sáng trạng thái `good` ở cuối
- Mảng theo dõi `vars` hiển thị current/max cập nhật theo thời gian thực
- Mô hình duyệt rõ ràng từ trái sang phải
