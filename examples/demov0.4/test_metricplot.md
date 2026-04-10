# Test MetricPlot — Bieu do duong theo doi gia tri

## Muc dich
Kiem tra primitive MetricPlot voi hai chuoi du lieu (cost va temp) duoc cap nhat qua tung buoc. Xac nhan rang bieu do duong mo rong dung cach khi them diem moi, truc tung/hoanh co nhan va vach chia chinh xac, chu thich hien thi dung, va chi bao buoc hien tai (duong ke dut va cham tron) xuat hien tai vi tri dung.

## Mo ta bai toan
Mot MetricPlot duoc khai bao voi hai chuoi `cost` va `temp`, truc x la "step", truc y la "value". Qua ba buoc:
- Buoc 1: cost=10, temp=100 (mot diem duy nhat cho moi chuoi, truong hop suy bien)
- Buoc 2: cost=8, temp=90 (hai diem, noi bang doan thang)
- Buoc 3: cost=5, temp=70 (ba diem, polyline day du)

Chuoi "cost" dung mau Wong xanh (#0072B2, net lien), chuoi "temp" dung mau Wong do cam (#D55E00, net dut 6 3).

## Cac buoc ky vong
- **Buoc 1**: Bieu do hien thi hai cham don tai cost=10, temp=100. Truc y tu dong dieu chinh voi 10% padding. Chi co mot vi tri tren truc x. Duong ke dut dung chi bao buoc hien tai di qua cot duy nhat. Hai cham tron tai vi tri cac diem du lieu hien tai. Chu thich hien thi "cost" (xanh, net lien) va "temp" (do cam, net dut).
- **Buoc 2**: Bieu do hien thi hai doan thang (cost: 10->8, temp: 100->90). Truc x mo rong den vi tri buoc 2. Duong ke dut va cham tron di chuyen den vi tri buoc 2. Truc y dieu chinh lai pham vi neu can.
- **Buoc 3**: Bieu do hien thi hai polyline day du (cost: 10->8->5, temp: 100->90->70). Truc x mo rong den vi tri buoc 3. Duong ke dut va cham tron di chuyen den vi tri buoc 3. Truc y dieu chinh lai pham vi voi 10% padding.

## Dieu kien chap nhan
- [ ] Hai chuoi du lieu hien thi dung mau sac va kieu net (cost: #0072B2 net lien, temp: #D55E00 net dut 6 3)
- [ ] Polyline mo rong dung khi them diem moi qua tung buoc
- [ ] Buoc 1 chi hien thi cham don (truong hop suy bien 1 diem)
- [ ] Truc x co nhan "step" va vach chia, truc y co nhan "value" va vach chia
- [ ] Pham vi truc y tu dong dieu chinh voi 10% padding
- [ ] Chu thich (legend) hien thi ten chuoi, mau sac va kieu net tuong ung
- [ ] Duong ke dut dung (marker) xuat hien tai vi tri buoc hien tai
- [ ] Cham tron xuat hien tren moi polyline tai vi tri buoc hien tai
- [ ] Luoi (grid lines) hien thi nhe phia sau bieu do
- [ ] Nut Prev/Next hoat dong dung, Prev bi vo hieu hoa tai buoc 1, Next bi vo hieu hoa tai buoc 3
- [ ] Thanh diem tien trinh (progress dots) phan anh buoc hien tai
- [ ] Widget ho tro dark mode
