# CSES 05 — Hoán vị: Mô tả hoạt ảnh mong đợi

## Tổng quan

- **Số khung hình:** 6
- **Thành phần:** 2 mảng (hoán vị + hiệu các phần tử liền kề)
- **Luồng trực quan:** Xây dựng theo hai giai đoạn (số chẵn rồi số lẻ), sau đó kiểm chứng

## Mô tả từng khung hình

### Khung 0 (Chiến lược)
- `perm`: [0,0,0,0,0,0,0,0] tất cả ở trạng thái chờ
- `diffs`: [0,0,0,0,0,0,0] tất cả ở trạng thái chờ
- Lời dẫn giải thích chiến lược đặt số chẵn trước rồi số lẻ sau

### Khung 1 (Đặt số chẵn)
- perm[0:3] = [2, 4, 6, 8] đánh dấu `current` (xanh dương)
- Lời dẫn: "Đặt các số chẵn"

### Khung 2 (Kiểm tra hiệu dãy chẵn)
- diffs[0:2] = [2, 2, 2] đánh dấu `done` (xanh lá)
- perm[0:3] đánh dấu `done` (xanh lá)
- Tất cả hiệu trong dãy chẵn đều bằng 2

### Khung 3 (Đặt số lẻ)
- perm[4:7] = [1, 3, 5, 7] đánh dấu `current` (xanh dương)
- Lời dẫn: "Đặt các số lẻ"

### Khung 4 (Kiểm tra ranh giới + hiệu dãy lẻ)
- diffs[3] = 7 đánh dấu `good` (xanh nhạt) — ranh giới quan trọng
- diffs[4:6] = [2, 2, 2] đánh dấu `done`
- perm.cell[3] và perm.cell[4] được tô sáng (vàng) — cặp ranh giới
- Lời dẫn giải thích tại sao ranh giới an toàn

### Khung 5 (Hoàn thành)
- Tất cả ô của perm và diffs đánh dấu `good` (xanh nhạt)
- Lời dẫn: hoán vị cuối cùng kèm tất cả các hiệu

## Đặc điểm trực quan
- Xây dựng hai giai đoạn tách biệt rõ ràng giữa số chẵn và số lẻ
- Mảng `diffs` cung cấp bằng chứng trực quan rằng tất cả hiệu >= 2
- Cặp ranh giới (8, 1) được tô sáng đặc biệt để thu hút sự chú ý
- Chuyển đổi màu xanh lá -> xanh nhạt thể hiện quá trình từ kiểm chứng đến thành công
