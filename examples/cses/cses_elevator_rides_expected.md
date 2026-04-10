# CSES Chuyến thang máy: Mô tả hoạt ảnh mong đợi

## Tổng quan

- **Số khung hình:** 20
- **Thành phần:** Mảng (cân nặng), Bảng QHĐ (16 ô cho các trạng thái bitmask)
- **Ví dụ:** n=4, cân nặng=[3, 5, 2, 7], sức chứa x=8
- **Đáp án:** 3 chuyến

## Bố cục thành phần

- **w**: Mảng kích thước 4 hiển thị cân nặng [3, 5, 2, 7], nhãn "weights"
- **dp**: Bảng QHĐ một chiều kích thước 16 (chỉ số 0..15), nhãn "dp[mask] = (rides, remaining)". Mỗi ô lưu chuỗi dạng "1,5" nghĩa là 1 chuyến với 5 sức chứa còn lại.

## Mô tả từng khung hình

### Khung 0 (Giới thiệu)
- Tất cả thành phần ở trạng thái chờ ban đầu
- Lời dẫn giải thích đề bài và cách tiếp cận QHĐ bitmask

### Khung 1 (Trường hợp cơ sở)
- `dp.cell[0]` đặt giá trị "1,8" và tô màu `good`
- Lời dẫn: tập rỗng, 1 chuyến mở sẵn với đầy đủ sức chứa 8

### Khung 2 (Người 0 một mình)
- `w.cell[0]` được tô sáng (tạm thời)
- `dp.cell[1]` đặt giá trị "1,5", tô màu `current`
- Lời dẫn: người 0 (nặng 3) vừa chuyến hiện tại

### Khung 3 (Người 1 một mình)
- `dp.cell[1]` tô màu `done`
- `w.cell[1]` được tô sáng
- `dp.cell[2]` đặt giá trị "1,3", tô màu `current`

### Khung 4 (Người 2 một mình)
- `dp.cell[2]` tô màu `done`
- `w.cell[2]` được tô sáng
- `dp.cell[4]` đặt giá trị "1,6", tô màu `current`

### Khung 5 (Người 3 một mình)
- `dp.cell[4]` tô màu `done`
- `w.cell[3]` được tô sáng
- `dp.cell[8]` đặt giá trị "1,1", tô màu `current`
- Lời dẫn: đã tính xong tất cả tập con một người

### Khung 6 (Cặp {0,1} -- vừa khít)
- `dp.cell[8]` tô màu `done`, `dp.cell[1]` tô màu `current`
- `w.cell[1]` được tô sáng
- `dp.cell[3]` đặt giá trị "1,0", tô màu `current`
- Điểm nhấn: cân nặng 3+5=8 lấp đầy vừa khít thang máy

### Khung 7 (Cặp {0,2})
- `dp.cell[3]` tô màu `done`
- `dp.cell[5]` đặt giá trị "1,3", tô màu `current`

### Khung 8 (Cặp {0,3} -- không vừa)
- `dp.cell[5]` tô màu `done`
- `dp.cell[9]` đặt giá trị "2,1", tô màu `current`
- Điểm nhấn: lần đầu tiên cần mở chuyến mới (nặng 7 > 5 còn lại)

### Khung 9 (Cặp {1,2})
- `dp.cell[6]` đặt giá trị "1,1", tô màu `current`
- Cân nặng 5+2=7 vừa trong một chuyến

### Khung 10 (Cặp {1,3})
- `dp.cell[10]` đặt giá trị "2,1", tô màu `current`
- Cần mở chuyến mới

### Khung 11 (Cặp {2,3} -- lần thử đầu)
- `dp.cell[12]` đặt giá trị "2,1", tô màu `current`

### Khung 12 (Cặp {2,3} -- cập nhật)
- `dp.cell[12]` cập nhật thành "2,6"
- Điểm nhấn: minh họa tiêu chí "tối đa hóa sức chứa còn lại" -- cùng 2 chuyến nhưng còn trống 6 tốt hơn còn trống 1

### Khung 13 (Bộ ba {0,1,2})
- `dp.cell[7]` đặt giá trị "2,6", tô màu `current`
- Người 0 và 1 lấp đầy chuyến 1; người 2 bắt đầu chuyến 2

### Khung 14 (Bộ ba {0,1,3})
- `dp.cell[11]` đặt giá trị "2,0" rồi hiệu chỉnh ngữ cảnh
- Nhiều đường đi hội tụ về 2 chuyến

### Khung 15 (Bộ ba {1,2,3})
- `dp.cell[14]` đặt giá trị "2,0", tô màu `current`

### Khung 16 (Bộ ba {0,2,3})
- `dp.cell[13]` đặt giá trị "2,3", tô màu `current`
- Minh họa cập nhật: đường qua dp[1100]=(2,6)+người 0 cho sức chứa còn lại tốt hơn

### Khung 17 (Tập đầy đủ -- chuyển trạng thái)
- `dp.cell[15]` tô màu `current`
- Lời dẫn liệt kê cả bốn chuyển trạng thái đến

### Khung 18 (Tập đầy đủ -- giá trị)
- `dp.cell[15]` đặt giá trị "3,6"
- Tất cả chuyển trạng thái đều cần chuyến thứ 3

### Khung 19 (Kết thúc)
- `dp.cell[15]` tô màu `good`
- Tất cả ô khác tô màu `done`
- Lời dẫn: đáp án là 3 chuyến, giải thích một cách phân nhóm tối ưu

## Đặc điểm trực quan

- **Tô sáng** trên ô mảng cân nặng là tạm thời (xóa mỗi bước), cho thấy người nào đang được xét
- **Tô màu** trên ô QHĐ là vĩnh viễn: `current` khi đang tính, `done` khi hoàn tất, `good` cho ô đáp án
- Bảng QHĐ hiển thị chỉ số bitmask 0..15; lời dẫn giải thích ý nghĩa nhị phân (ví dụ: "mask 0011 = người 0 và 1")
- Các điểm giảng dạy quan trọng:
  1. Khung 6: vừa khít sức chứa (3+5=8)
  2. Khung 8: lần đầu "không vừa" phải mở chuyến mới
  3. Khung 12: cập nhật minh họa tiêu chí "tối đa hóa sức chứa còn lại"
  4. Khung 17-18: hội tụ cuối cùng cho thấy mọi đường đều cần 3 chuyến

## Chuyển đổi trạng thái màu

| Trạng thái | Ý nghĩa | Màu |
|------------|----------|-----|
| idle | Chưa tính | Xám mặc định |
| current | Đang tính ở bước này | Xanh dương |
| done | Đã hoàn tất | Xanh lá |
| good | Đáp án cuối cùng | Xanh nhạt |
