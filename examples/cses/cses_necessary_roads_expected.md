# CSES Necessary Roads: Mô tả hoạt ảnh kỳ vọng

## Tổng quan

- **Số khung hình:** 16
- **Các cấu trúc:** Đồ thị (7 đỉnh, 8 cạnh), 2 Mảng (disc[] và low[], mỗi mảng kích thước 7)
- **Luồng trực quan:** Duyệt DFS với tính toán giá trị disc/low, phát hiện cạnh ngược, xác định cầu khi quay lui

## Mô tả từng khung hình

### Khung 0 (Giới thiệu)
- Đồ thị: tất cả đỉnh và cạnh ở trạng thái mặc định (idle)
- disc[]: tất cả ô hiển thị "-"
- low[]: tất cả ô hiển thị "-"
- Lời dẫn giới thiệu bài toán tìm cầu và thuật toán Tarjan

### Khung 1 (Bắt đầu DFS tại đỉnh 1)
- g.node[1]: đang xử lý (xanh dương)
- disc[1] = 0, low[1] = 0, cả hai ô đang xử lý
- Lời dẫn: DFS bắt đầu từ đỉnh 1

### Khung 2 (Thăm đỉnh 2)
- g.node[1]: hoàn tất (xanh lá), g.node[2]: đang xử lý
- g.edge[(1,2)]: hoàn tất (cạnh cây)
- disc[2] = 1, low[2] = 1

### Khung 3 (Thăm đỉnh 3)
- g.node[2]: hoàn tất, g.node[3]: đang xử lý
- g.edge[(2,3)]: hoàn tất (cạnh cây)
- disc[3] = 2, low[3] = 2

### Khung 4 (Cạnh ngược 3->1)
- g.edge[(3,1)]: đang xử lý (tô vàng cho cạnh ngược)
- low[3] cập nhật từ 2 thành 0, hiển thị trạng thái tốt (xanh nhạt)
- Lời dẫn giải thích phát hiện cạnh ngược: đỉnh 3 có thể nối tới tổ tiên 1

### Khung 5 (Thăm đỉnh 4)
- g.node[3]: hoàn tất, g.node[4]: đang xử lý
- g.edge[(3,4)]: hoàn tất (cạnh cây), g.edge[(3,1)]: mờ (cạnh ngược đã xử lý)
- disc[4] = 3, low[4] = 3

### Khung 6 (Thăm đỉnh 5)
- g.node[4]: hoàn tất, g.node[5]: đang xử lý
- g.edge[(4,5)]: hoàn tất (cạnh cây)
- disc[5] = 4, low[5] = 4

### Khung 7 (Thăm đỉnh 6)
- g.node[5]: hoàn tất, g.node[6]: đang xử lý
- g.edge[(5,6)]: hoàn tất
- disc[6] = 5, low[6] = 5

### Khung 8 (Thăm đỉnh 7)
- g.node[6]: hoàn tất, g.node[7]: đang xử lý
- g.edge[(6,7)]: hoàn tất
- disc[7] = 6, low[7] = 6

### Khung 9 (Cạnh ngược 7->5)
- g.edge[(7,5)]: đang xử lý (phát hiện cạnh ngược)
- low[7] cập nhật từ 6 thành 4, hiển thị trạng thái tốt (xanh nhạt)
- Lời dẫn: chu trình 5-6-7-5 bảo vệ các cạnh đó khỏi trở thành cầu

### Khung 10 (Quay lui 7->6)
- g.node[7]: hoàn tất, g.edge[(7,5)]: mờ
- low[6] cập nhật thành 4
- Kiểm tra cầu: low[7]=4 > disc[6]=5? Không -- cạnh 6-7 an toàn

### Khung 11 (Quay lui 6->5)
- low[5] cập nhật thành 4
- Kiểm tra cầu: low[6]=4 > disc[5]=4? Không -- cạnh 5-6 an toàn

### Khung 12 (Quay lui 5->4 -- tìm thấy cầu)
- low[4] giữ nguyên 3
- Kiểm tra cầu: low[5]=4 > disc[4]=3? ĐÚNG
- g.edge[(4,5)]: lỗi (đỏ) -- đánh dấu là cầu
- Lời dẫn: không có cạnh ngược nào từ {5,6,7} nối tới phía trên đỉnh 4

### Khung 13 (Quay lui 4->3 -- tìm thấy cầu)
- Kiểm tra cầu: low[4]=3 > disc[3]=2? ĐÚNG
- g.edge[(3,4)]: lỗi (đỏ) -- đánh dấu là cầu
- Lời dẫn: đỉnh 4 không có cạnh ngược, cây con của nó bị cô lập

### Khung 14 (Quay lui về gốc)
- low[2] = 0, low[1] = 0
- Cạnh 2-3 và 1-2 đều vượt qua kiểm tra cầu (không phải cầu)
- DFS hoàn tất

### Khung 15 (Kết quả cuối cùng)
- Chu trình {1,2,3}: các đỉnh và cạnh ở trạng thái tốt (xanh nhạt)
- Chu trình {5,6,7}: các đỉnh và cạnh ở trạng thái tốt (xanh nhạt)
- Đỉnh 4: lỗi (đỏ) -- đỉnh khớp (articulation point)
- Cạnh (3,4) và (4,5): lỗi (đỏ) -- cầu
- Mảng disc[] và low[]: tất cả ở trạng thái tốt
- Lời dẫn tổng kết: 2 cầu, độ phức tạp O(n + m)

## Đặc điểm trực quan

- Cạnh cây được tô màu hoàn tất (xanh lá) khi DFS tiến về phía trước
- Cạnh ngược nhấp nháy trạng thái đang xử lý (vàng) khi được phát hiện, sau đó mờ dần
- Các ô low[] nhấp nháy trạng thái tốt (xanh nhạt) khi được cập nhật bởi cạnh ngược
- Cạnh cầu được tô màu lỗi (đỏ) khi quay lui và thỏa điều kiện
- Khung cuối cùng thể hiện rõ cấu trúc thành phần hai-liên-thông: hai chu trình xanh lá/xanh nhạt nối với nhau qua các cạnh cầu đỏ qua đỉnh khớp đỏ
- Hai mảng cung cấp nhật ký liên tục về trạng thái thuật toán tại mỗi bước DFS
