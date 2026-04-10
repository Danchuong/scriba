# CSES Range Queries and Copies: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 18
- **Các cấu trúc:** Mảng (trạng thái mảng hiện tại, kích thước 4), Cây (segment tree, loại segtree với show_sum), Mảng (theo dõi phiên bản, kích thước 1)
- **Ví dụ:** n=4, mảng=[1, 3, 2, 5]
- **Các thao tác minh họa:** khởi tạo, truy vấn đoạn, cập nhật điểm với sao chép đường đi, sao chép (phiên bản mới), cập nhật lần hai, truy vấn cuối cùng

## Mô tả từng khung hình

### Khung 0 -- Khởi tạo
- Segment tree hiển thị với các lá [1, 3, 2, 5] và các tổng nội bộ đã tính
- Mảng hiển thị [1, 3, 2, 5]
- Thông tin phiên bản hiển thị 0
- Lời dẫn: giới thiệu segment tree ban đầu cho Phiên bản 0

### Khung 1 -- Phiên bản 0 hoàn tất
- Gốc [0,3], [0,1], [2,3] được tô màu hoàn tất (xanh lá)
- Lời dẫn: tổng kết số nút và các tổng (gốc=11, trái=4, phải=7)

### Khung 2 -- Truy vấn sum(0,3) phủ toàn bộ
- Gốc [0,3] được tô sáng
- Lời dẫn: phủ toàn bộ nên trả về sum=11 ngay lập tức, không cần đệ quy

### Khung 3 -- Truy vấn sum(1,2) bắt đầu
- Gốc được tô sáng, tất cả nút đặt về trạng thái mặc định
- Lời dẫn: chồng lấn một phần, cần đệ quy vào cả hai con

### Khung 4 -- Truy vấn sum(1,2) đệ quy
- Gốc mờ đi, [0,1] và [2,3] được tô sáng
- Lời dẫn: không con nào nằm hoàn toàn trong đoạn, đệ quy sâu hơn

### Khung 5 -- Truy vấn sum(1,2) tại các lá
- [0,0] và [3,3] đánh dấu hoàn tất (ngoài đoạn truy vấn, bỏ qua)
- [1,1] và [2,2] đánh dấu tốt (trong đoạn truy vấn, lấy giá trị)
- [0,1] và [2,3] mờ đi
- Lời dẫn: kết quả = 3 + 2 = 5

### Khung 6 -- Giới thiệu cập nhật
- Tất cả nút đặt về trạng thái mặc định
- Lời dẫn: giải thích khái niệm sao chép đường đi -- cập nhật a[1]=7 tạo nút mới, nút cũ giữ nguyên

### Khung 7 -- Xác định đường đi
- Lá [1,1] được tô sáng và đánh dấu đang xử lý
- Lời dẫn: đường đi là [0,3] -> [0,1] -> [1,1], 3 nút mới cho V1

### Khung 8 -- Trực quan hóa sao chép đường đi
- Các nút trên đường đi [0,3], [0,1], [1,1] đánh dấu đang xử lý (xanh dương) -- đây là các nút MỚI
- Các nút ngoài đường đi [2,3], [0,0], [2,2], [3,3] đánh dấu mờ -- đây là các nút CHIA SẺ với V0
- Lời dẫn: giải thích các tổng mới: lá=7, [0,1]=8, gốc=15

### Khung 9 -- Phiên bản 1 hoàn tất
- Các nút trên đường đi đánh dấu tốt (xanh nhạt) -- nút mới của V1
- Các nút chia sẻ đánh dấu mờ
- Ô mảng vị trí 1 cập nhật thành 7, đánh dấu đang xử lý
- Thông tin phiên bản cập nhật thành 1
- Lời dẫn: 3 nút mới được tạo, gốc V0 (sum=11) vẫn tồn tại, bộ nhớ O(log n)

### Khung 10 -- Bắt đầu thao tác sao chép
- Tất cả nút đặt về trạng thái mặc định
- Ô mảng vị trí 1 đặt lại
- Lời dẫn: sao chép V1 tạo V2, chỉ là sao chép con trỏ, O(1)

### Khung 11 -- Phiên bản 2 được tạo (Sao chép)
- Tất cả nút đánh dấu hoàn tất (xanh lá) -- toàn bộ cây chia sẻ với V1
- Thông tin phiên bản cập nhật thành 2
- Lời dẫn: V2 giống hệt V1, không cấp phát nút nào

### Khung 12 -- Bắt đầu cập nhật lần hai
- Tất cả nút đặt về trạng thái mặc định
- Lời dẫn: cập nhật a[3]=10 trên V2, đường đi là [0,3] -> [2,3] -> [3,3]

### Khung 13 -- Sao chép đường đi lần hai
- Các nút trên đường đi [0,3], [2,3], [3,3] đánh dấu đang xử lý (xanh dương) -- nút mới của V2
- Các nút ngoài đường đi [0,1], [0,0], [1,1], [2,2] đánh dấu mờ -- chia sẻ từ V1
- Lời dẫn: các tổng mới: lá=10, [2,3]=12, gốc=20

### Khung 14 -- Phiên bản 2 đã cập nhật
- Các nút trên đường đi đánh dấu tốt (xanh nhạt)
- Các nút chia sẻ đánh dấu hoàn tất (xanh lá)
- Ô mảng vị trí 3 cập nhật thành 10, đánh dấu đang xử lý
- Lời dẫn: tổng số nút qua 3 phiên bản = 13 thay vì 21

### Khung 15 -- Truy vấn V2 sum(0,3)
- Gốc được tô sáng
- Lời dẫn: gốc V2 sum=20, phủ toàn bộ, trả về ngay lập tức

### Khung 16 -- Tổng kết
- Tất cả nút và ô mảng đã sửa đổi đánh dấu tốt
- Lời dẫn: 3 phiên bản cùng tồn tại (V0 sum=11, V1 sum=15, V2 sum=20), tổng O(n + q log n)

## Đặc điểm trực quan

- **Ngữ nghĩa màu sắc:**
  - `idle` (xám mặc định): nút không hoạt động/đặt lại
  - `current` (xanh dương): nút đang được tạo hoặc xử lý ở bước này
  - `done` (xanh lá): nút đã thiết lập thuộc về một phiên bản
  - `good` (xanh nhạt): nút mới hoàn thành, nhấn mạnh trạng thái cuối
  - `dim` (mờ): nút chia sẻ/tái sử dụng từ phiên bản trước
  - `error` (đỏ): không sử dụng trong hoạt ảnh này
- **highlight** (vàng tạm thời): nút đang được kiểm tra trong truy vấn
- **Các điểm giảng dạy quan trọng:**
  - Khung 8-9: trực quan hóa sao chép đường đi -- đường xanh dương vs nút mờ chia sẻ
  - Khung 10-11: sao chép là O(1) -- chỉ là con trỏ, tất cả nút xanh lá/chia sẻ
  - Khung 13-14: cập nhật thứ hai cho thấy đường đi khác, tập chia sẻ khác
  - Khung 16: so sánh số nút (13 vs 21) minh họa rõ tiết kiệm bộ nhớ
- **Giới hạn trực quan hóa tính bền vững:** Cấu trúc Cây chỉ hiển thị một cây. Gốc các phiên bản cũ được giải thích qua lời dẫn vì không thể hiển thị hai cây đồng thời. Sơ đồ màu mờ/đang xử lý/tốt phân biệt "nút phiên bản mới" với "nút cũ chia sẻ" trong cùng một khung nhìn cây.
