# Test \fastforward — Sắp xếp mảng bằng random swap (SA-style)

## Mục đích

Kiểm tra extension `\fastforward` thực sự chạy callback `iterate(scene, rng)` trong Starlark, thay đổi trạng thái shapes qua mỗi iteration, và chỉ sample tại các bước được chỉ định.

## Mô tả bài toán

Cho mảng 8 phần tử `[8, 3, 7, 1, 5, 2, 6, 4]`. Thuật toán random swap:
- Mỗi iteration: chọn ngẫu nhiên hai vị trí `i`, `j`
- Nếu swap giúp mảng "sắp xếp hơn" (phần tử nhỏ hơn ở vị trí nhỏ hơn), thực hiện swap
- Lặp 50 lần, seed=42, sample mỗi 10 iteration

## Cấu hình

```
\fastforward{50}{sample_every=10, seed=42}
```

- Tổng iterations: 50
- Sample mỗi: 10 iterations
- Số frame fastforward: 50 / 10 = **5 frames**
- Tổng bước widget: 1 (thủ công) + 5 (fastforward) + 1 (thủ công) = **7 bước**

## Các bước kỳ vọng (kết quả thực tế với seed=42)

| Bước | Loại | Iteration | Mảng | Sorted pairs |
|------|------|-----------|------|-------------|
| 1 | Thủ công | — | `[8,3,7,1,5,2,6,4]` | 3/7 |
| 2 | FF sample | 10 | `[3,8,1,6,4,2,7,5]` | 3/7 |
| 3 | FF sample | 20 | `[1,5,3,2,4,6,8,7]` | 4/7 |
| 4 | FF sample | 30 | `[1,2,3,5,4,6,8,7]` | 5/7 |
| 5 | FF sample | 40 | `[1,2,3,5,4,6,7,8]` | 6/7 |
| 6 | FF sample | 50 | `[1,2,3,4,5,6,7,8]` | 7/7 (sorted) |
| 7 | Thủ công | — | `[1,2,3,4,5,6,7,8]` | 7/7 |

## Điều kiện chấp nhận

- [ ] `\fastforward{50}{sample_every=10, seed=42}` tạo đúng 5 frame
- [ ] Callback `iterate(scene, rng)` được gọi 50 lần
- [ ] Mỗi frame sample hiển thị trạng thái mảng **thực sự khác nhau**
- [ ] 5 frame đều có mảng unique (không có 2 frame giống nhau)
- [ ] Frame cuối cùng (iter 50) hiển thị mảng đã sorted `[1,2,3,4,5,6,7,8]`
- [ ] Tổng số bước: 7
- [ ] Deterministic: cùng seed=42 → cùng kết quả mỗi lần build
- [ ] Widget dark theme, bảng màu Wong CVD
