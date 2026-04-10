# Test \substory -- Khung con long nhau

## Muc dich

Kiem tra extension `\substory` / `\endsubstory` cua Scriba: kha nang tao mot khoi animation con (substory) long ben trong mot buoc cua animation cha. Substory co cac shape rieng, cac step rieng, va duoc hien thi nhu mot section thut vao voi duong vien trai, nam tron trong frame cua buoc cha.

## Mo ta bai toan

File TeX dinh nghia mot animation voi mang `a = [3, 1, 4, 1]` gom 4 phan tu.

- **Buoc 1 (cha):** To mau `a.cell[0]` thanh `current` (xanh duong `#0072B2`). Loi ke: "Processing element 0." Trong buoc nay co mot `\substory` voi tieu de "Sub-computation for element 0":
  - **Buoc con 1:** Tao mang con `sub = [3, 1]`, highlight `sub.cell[0]`. Loi ke: "Compare 3 and 1."
  - **Buoc con 2:** To mau tat ca o cua `sub` thanh `done` (xanh la `#009E73`). Loi ke: "Sub-computation complete."
- **Buoc 2 (cha):** To mau `a.cell[0]` thanh `done`. Loi ke: "Element 0 processed." Khong con substory.

Sau `\endsubstory`, trang thai cua animation cha (shape `a`, mau sac, vi tri) duoc phuc hoi va tiep tuc binh thuong.

## Cac buoc ky vong

### Buoc 1 -- parent frame

| Thanh phan | Trang thai |
|------------|-----------|
| `a.cell[0]` | `current` -- nen `#0072B2`, chu trang |
| `a.cell[1]` | `idle` -- nen `#f6f8fa`, vien `#d0d7de` |
| `a.cell[2]` | `idle` |
| `a.cell[3]` | `idle` |
| Narration | "Processing element 0." |

Ben trong frame nay, hien thi khoi substory:

#### Substory: "Sub-computation for element 0"

##### Sub-step 1

| Thanh phan | Trang thai |
|------------|-----------|
| `sub.cell[0]` | `current` -- nen `#0072B2`, chu trang |
| `sub.cell[1]` | `idle` -- nen `#f6f8fa` |
| Sub-narration | "Compare 3 and 1." |

##### Sub-step 2

| Thanh phan | Trang thai |
|------------|-----------|
| `sub.cell[0]` | `done` -- nen `#009E73`, chu trang |
| `sub.cell[1]` | `done` -- nen `#009E73`, chu trang |
| Sub-narration | "Sub-computation complete." |

### Buoc 2 -- parent frame

| Thanh phan | Trang thai |
|------------|-----------|
| `a.cell[0]` | `done` -- nen `#009E73`, chu trang |
| `a.cell[1]` | `idle` |
| `a.cell[2]` | `idle` |
| `a.cell[3]` | `idle` |
| Narration | "Element 0 processed." |

Khong co substory trong buoc nay.

## Phan cap hien thi (visual hierarchy)

```
scriba-widget
  +-- scriba-controls (Prev / Step 1 of 2 / Next / progress dots)
  +-- scriba-stage
  |     +-- SVG: mang a (parent)
  |     +-- section.scriba-substory  <-- chi xuat hien o buoc 1
  |           +-- tieu de "Sub-computation for element 0"
  |           +-- scriba-sub-controls (Prev / Sub 1 of 2 / Next)
  |           +-- scriba-sub-stage (SVG: mang sub)
  |           +-- scriba-sub-narration
  +-- scriba-narration (parent narration)
```

Section substory co:
- `border-left: 2px solid #0072B2`
- `padding-left: 1rem`
- `margin: 0.75rem 0 0.75rem 0.5rem`
- `aria-label="Substory: Sub-computation for element 0"`

## Quy tac ID frame

- Parent frame 1: `test-substory-frame-1`
- Substory frame 1 trong parent frame 1: `test-substory-frame-1-substory-1-frame-1`
- Substory frame 2 trong parent frame 1: `test-substory-frame-1-substory-1-frame-2`
- Parent frame 2: `test-substory-frame-2`

## Bang mau (Wong CVD palette)

| Trang thai | Mau nen | Mau vien | Mau chu |
|-----------|---------|----------|---------|
| `idle` | `#f6f8fa` | `#d0d7de` | `#212529` |
| `current` | `#0072B2` | `#005a8e` | `#ffffff` |
| `done` | `#009E73` | `#007a59` | `#ffffff` |

## Dieu kien chap nhan

- [ ] Substory hien thi trong `<section class="scriba-substory">`
- [ ] Section substory co `border-left: 2px solid` va padding thut vao
- [ ] Section substory co `aria-label` mo ta noi dung
- [ ] Substory co tieu de "Sub-computation for element 0" hien thi ro rang
- [ ] Substory co dieu huong rieng (Prev/Next) cho cac sub-step
- [ ] Sub-step SVG chi hien thi mang `sub`, khong hien thi mang `a`
- [ ] Sau `\endsubstory`, buoc 2 cua cha chi hien thi mang `a` voi `cell[0]` = done
- [ ] Substory chi xuat hien trong buoc 1, khong xuat hien trong buoc 2
- [ ] Frame IDs theo quy tac: `test-substory-frame-1-substory-1-frame-N`
- [ ] Widget ho tro dark mode
- [ ] Dieu huong Prev/Next va phim mui ten hoat dong cho ca parent va substory
- [ ] Narration cua parent va substory tach biet, khong lan lon
