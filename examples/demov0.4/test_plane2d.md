# Test Plane2D — Mat phang toa do 2D

## Muc dich

Kiem tra primitive `Plane2D` cua Scriba: kha nang hien thi mat phang toa do 2D voi luoi (grid), truc toa do (axes), va cac phep `\apply` de them diem (point) va duong thang (line) theo tung buoc (step).

## Mo ta bai toan

File `.tex` khai bao mot `Plane2D` voi:

- **Mien gia tri**: x thuoc [-3, 3], y thuoc [-3, 3]
- **Luoi**: bat (`grid=true`) — ve cac duong ke tai moi vi tri nguyen
- **Truc**: bat (`axes=true`) — ve truc x va truc y qua goc toa do, co mui ten o dau duong

Animation gom 3 buoc (step), moi buoc them mot doi tuong hinh hoc len mat phang.

## Cac buoc ky vong

- **Buoc 1**: Them diem tai toa do (1, 2).
  - Mat phang hien thi luoi va truc.
  - Mot hinh tron to mau xuat hien tai vi tri (1, 2).
  - Diem dang o trang thai "current" (mau xanh duong `#0072B2`).
  - Loi thuyet minh: "Them diem tai toa do (1, 2)."

- **Buoc 2**: Them duong thang y = x.
  - Duong thang y = x duoc ve, cat (clip) trong vung nhin cua mat phang (tu (-3, -3) den (3, 3)).
  - Diem (1, 2) chuyen sang trang thai "done" (mau xanh la `#009E73`).
  - Duong thang moi them o trang thai "current" (mau xanh duong `#0072B2`).
  - Nhan "y=x" hien thi gan duong thang.
  - Loi thuyet minh: "Them duong thang y = x."

- **Buoc 3**: Them diem thu hai tai toa do (-1, -1).
  - Diem moi xuat hien tai (-1, -1) o trang thai "current" (mau xanh duong `#0072B2`).
  - Diem (1, 2) va duong y = x chuyen sang trang thai "done" (mau xanh la `#009E73`).
  - Loi thuyet minh: "Them diem thu hai tai (-1, -1)."

## Dieu kien chap nhan

- [ ] Luoi toa do hien thi dung tai cac vi tri nguyen (-3 den 3 tren ca hai truc)
- [ ] Truc x/y co mui ten o dau duong
- [ ] Nhan so (tick label) hien thi tai cac vi tri nguyen, khong hien thi so 0
- [ ] Diem hien thi la hinh tron to mau, ban kinh khoang 4px
- [ ] Duong thang y = x duoc cat (clip) trong vung nhin, khong tran ra ngoai
- [ ] Nhan "y=x" hien thi o vi tri hop ly gan duong thang
- [ ] Trang thai mau theo Wong CVD palette: current = `#0072B2`, done = `#009E73`
- [ ] Doi tuong moi them o buoc hien tai mang mau "current", cac doi tuong cu chuyen sang "done"
- [ ] Dieu huong: nut Prev/Next, phim mui ten trai/phai, bo dem buoc (Step X / 3)
- [ ] Cham tien trinh (progress dots) phan anh dung buoc hien tai va cac buoc da qua
- [ ] Truc Y huong len trong quy uoc toan hoc (scale Y am trong SVG transform)
- [ ] Nhan van ban (text label) khong bi lat nguoc — render ngoai nhom transform
- [ ] Thuyet minh bang tieng Viet co dau
- [ ] Widget co nen toi (#1e1e2e), tuong thich voi thiet ke dark mode
