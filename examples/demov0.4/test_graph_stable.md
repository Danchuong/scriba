# Test Graph layout="stable" — Do thi voi vi tri node co dinh

## Muc dich

Kiem tra tinh nang `layout="stable"` cua primitive **Graph**. Khi bat co `layout="stable"`, vi tri (cx, cy) cua tat ca cac node phai giu nguyen giua moi buoc (step), bat ke trang thai cua cac canh thay doi nhu the nao. Day la tinh nang cot loi dam bao hoat hinh do thi khong bi "nhay" khi chuyen buoc.

## Mo ta bai toan

Do thi co huong gom 4 node `a`, `b`, `c`, `d` va 3 canh:

```
a --> b --> c --> d
```

Tham so: `directed=true`, `layout="stable"`, `layout_seed=42`.

Qua 3 buoc, cac canh lan luot duoc **highlight** (noi bat) roi chuyen sang trang thai **done** (hoan thanh). Cac node khong bao gio thay doi vi tri.

## Cac buoc ky vong

### Buoc 1 — Highlight canh a->b
- Canh `a->b` duoc highlight (vien vang, net dut).
- Cac canh `b->c`, `c->d` o trang thai idle (xam).
- Tat ca 4 node o vi tri co dinh, trang thai idle.
- Thuyet minh: *"Duong di a->b duoc noi bat."*

### Buoc 2 — a->b hoan thanh, highlight b->c
- Canh `a->b` chuyen sang trang thai **done** (xanh la).
- Canh `b->c` duoc **highlight** (vien vang, net dut).
- Canh `c->d` van idle.
- Tat ca 4 node giu nguyen vi tri.
- Thuyet minh: *"Chuyen sang canh b->c."*

### Buoc 3 — Tat ca hoan thanh
- Tat ca cac canh `a->b`, `b->c`, `c->d` o trang thai **done** (xanh la).
- Tat ca cac node o trang thai **done** (xanh la).
- Vi tri node khong thay doi.
- Thuyet minh: *"Tat ca cac canh da hoan thanh. Cac node giu nguyen vi tri."*

## Dieu kien chap nhan

- [ ] Vi tri (cx, cy) cua moi node giong het nhau o moi step — khong sai lech du chi 1 pixel
- [ ] Thuoc tinh `data-layout="stable"` co mat tren phan tu SVG goc
- [ ] Canh duoc highlight phai co overlay vang (gold), net dut (dashed), phan biet ro voi trang thai idle va done
- [ ] Trang thai done cua canh va node su dung mau xanh la (Wong CVD: #009E73)
- [ ] Do thi co huong — moi canh co dau mui ten (arrowhead marker)
- [ ] Widget co giao dien toi (dark), nut Prev/Next, chi bao buoc hien tai
- [ ] Thuyet minh bang tieng Viet co dau
- [ ] Bang mau tuan thu Wong CVD-safe palette
