# Test \fastforward -- Chay nhanh nhieu iteration

## Muc dich

Kiem tra extension `\fastforward` co the chay nhieu iteration mot cach tu dong va chi lay mau (sample) tai nhung buoc duoc chi dinh. Nguoi dung cuoi cung nhin thay cac frame mau nhu the chung la cac buoc thu cong binh thuong -- khong co su khac biet nao ve mat giao dien.

## Mo ta bai toan

File `.tex` khai bao mot mang 5 phan tu `[5, 3, 1, 4, 2]`, sau do:

1. **Buoc thu cong dau tien** (`\step` + `\narrate`): Hien thi mang ban dau voi narration "Mang ban dau."
2. **`\fastforward{100}{sample_every=50, seed=42}`**: Chay 100 iteration, lay mau moi 50 iteration. Dieu nay tao ra **2 frame mau**:
   - Frame tai iteration 50: narration "Iteration 50 / 100."
   - Frame tai iteration 100: narration "Iteration 100 / 100."
3. **Buoc thu cong cuoi** (`\step` + `\narrate`): Narration "Hoan tat sau 100 iteration."

Tong cong: **4 buoc** trong widget.

## Cac buoc ky vong

| Buoc | Loai | Narration | Ghi chu |
|------|------|-----------|---------|
| 1 | Thu cong | "Mang ban dau." | Mang `[5,3,1,4,2]` trang thai idle |
| 2 | Fastforward (sample) | "Iteration 50 / 100." | Mang khong doi, narration tu dong sinh voi so iteration |
| 3 | Fastforward (sample) | "Iteration 100 / 100." | Mang khong doi, narration tu dong sinh voi so iteration |
| 4 | Thu cong | "Hoan tat sau 100 iteration." | Mang khong doi |

## Dieu kien chap nhan

- [ ] `\fastforward{100}{sample_every=50, seed=42}` tao ra dung 2 frame mau (tai iteration 50 va 100)
- [ ] Tong so buoc trong widget la 4 (1 thu cong + 2 fastforward + 1 thu cong)
- [ ] Cac frame fastforward trong giong het cac frame thu cong (nguoi dung khong phan biet duoc)
- [ ] Narration cua frame fastforward chua so iteration da duoc resolve (vd: "Iteration 50 / 100."), khong chua `${iter}` nguyen van
- [ ] Bo dem buoc hien thi dung: "Buoc 1 / 4", "Buoc 2 / 4", "Buoc 3 / 4", "Buoc 4 / 4"
- [ ] Nut Prev/Next hoat dong binh thuong qua tat ca 4 buoc
- [ ] Progress dots hien thi 4 cham, trang thai active/done cap nhat dung
- [ ] Widget su dung dark theme, bang mau Wong CVD, narration tieng Viet co dau
- [ ] Mang `[5, 3, 1, 4, 2]` hien thi nhat quan o tat ca 4 frame
