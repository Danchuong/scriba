# CSES: Range Queries and Copies (Truy vấn đoạn và sao chép)

## Đề bài

Cho một mảng gồm **n** số nguyên. Nhiệm vụ của bạn là xử lý **q** truy vấn thuộc ba loại:

1. **Cập nhật:** Gán `a[k] = x` trong phiên bản hiện tại.
2. **Truy vấn tổng:** Tính tổng các phần tử `a[l..r]` trong phiên bản hiện tại.
3. **Sao chép:** Tạo phiên bản mới bằng cách sao chép mảng hiện tại. Các thao tác tiếp theo áp dụng lên phiên bản mới; phiên bản cũ được giữ nguyên và có thể truy cập lại sau.

Sau khi sao chép, các thao tác áp dụng lên phiên bản mới nhất. Mỗi phiên bản là một bản chụp độc lập của mảng tại thời điểm sao chép.

### Đầu vào

Dòng đầu tiên chứa hai số nguyên n và q.
Dòng thứ hai chứa n số nguyên: mảng ban đầu.
Mỗi dòng trong q dòng tiếp theo mô tả một truy vấn:
- `1 k x v` -- trong phiên bản v, gán a[k] = x
- `2 l r v` -- trong phiên bản v, tính tổng a[l..r]
- `3 v` -- sao chép phiên bản v để tạo phiên bản mới

### Ràng buộc

- 1 <= n, q <= 2 * 10^5
- 1 <= a[i] <= 10^9

---

## Lời giải: Segment Tree bền vững (Persistent Segment Tree)

### Ý tưởng chính

Cách tiếp cận đơn giản là sao chép toàn bộ mảng mỗi khi có truy vấn loại 3, dẫn đến O(n) cho mỗi lần sao chép và tổng bộ nhớ O(n * q). Thay vào đó, ta dùng **segment tree bền vững** với kỹ thuật **sao chép đường đi** (path copying): mỗi lần cập nhật chỉ tạo O(log n) nút mới dọc theo đường từ gốc đến lá, trong khi chia sẻ toàn bộ cây con không thay đổi với phiên bản trước.

### Cách hoạt động của sao chép đường đi

Một segment tree chuẩn cho mảng kích thước n có O(n) nút. Khi cập nhật một phần tử, chỉ các nút trên đường từ lá đến gốc bị thay đổi -- tức là O(log n) nút. Trong segment tree bền vững:

1. Với mỗi nút trên đường cập nhật, cấp phát một **nút mới** chứa giá trị đã cập nhật.
2. Các con của nút mới mà KHÔNG nằm trên đường cập nhật chỉ đơn giản **trỏ tới các con cũ** từ phiên bản trước.
3. Lưu gốc mới vào **mảng roots** được đánh chỉ số theo số phiên bản.

Điều này có nghĩa:
- Các phiên bản cũ hoàn toàn nguyên vẹn (gốc cũ vẫn trỏ đến cấu trúc ban đầu).
- Mỗi lần cập nhật tốn O(log n) thời gian và O(log n) bộ nhớ (cho các nút mới).
- Truy vấn trên bất kỳ phiên bản nào hoạt động giống hệt segment tree thông thường, bắt đầu từ gốc của phiên bản đó.

### Thao tác sao chép

Sao chép chỉ tốn O(1): chỉ cần đẩy con trỏ gốc hiện tại vào mảng roots. Phiên bản mới chia sẻ toàn bộ cây với phiên bản nguồn cho đến khi một cập nhật tương lai phân tách chúng qua sao chép đường đi.

### Cấu trúc dữ liệu

```cpp
struct Node {
    long long sum;
    int left, right;  // chỉ số trong bể nút (node pool)
};

const int MAXN = 200005;
const int MAXNODES = MAXN * 40;  // ~n + q * log(n) nút

Node tree[MAXNODES];
int pool = 0;
int roots[MAXN];  // roots[v] = chỉ số nút gốc của phiên bản v
```

### Khởi tạo (Build)

Xây dựng segment tree ban đầu từ mảng. Bước này tạo O(n) nút theo chuẩn.

```cpp
int build(int l, int r, int a[]) {
    int id = pool++;
    if (l == r) {
        tree[id].sum = a[l];
        tree[id].left = tree[id].right = 0;
        return id;
    }
    int mid = (l + r) / 2;
    tree[id].left = build(l, mid, a);
    tree[id].right = build(mid + 1, r, a);
    tree[id].sum = tree[tree[id].left].sum + tree[tree[id].right].sum;
    return id;
}
```

### Cập nhật điểm (có bền vững)

Tạo các nút mới dọc theo đường từ gốc đến lá mục tiêu. Tất cả các con khác được chia sẻ với phiên bản trước.

```cpp
int update(int prev, int l, int r, int pos, long long val) {
    int id = pool++;
    tree[id] = tree[prev];  // sao chép nút cũ
    if (l == r) {
        tree[id].sum = val;
        return id;
    }
    int mid = (l + r) / 2;
    if (pos <= mid)
        tree[id].left = update(tree[prev].left, l, mid, pos, val);
    else
        tree[id].right = update(tree[prev].right, mid + 1, r, pos, val);
    tree[id].sum = tree[tree[id].left].sum + tree[tree[id].right].sum;
    return id;
}
```

### Truy vấn tổng đoạn

Truy vấn segment tree chuẩn, không thay đổi so với phiên bản không bền vững.

```cpp
long long query(int id, int l, int r, int ql, int qr) {
    if (ql > r || qr < l) return 0;
    if (ql <= l && r <= qr) return tree[id].sum;
    int mid = (l + r) / 2;
    return query(tree[id].left, l, mid, ql, qr)
         + query(tree[id].right, mid + 1, r, ql, qr);
}
```

### Vòng lặp chính

```cpp
int main() {
    int n, q;
    scanf("%d %d", &n, &q);
    int a[n];
    for (int i = 0; i < n; i++) scanf("%d", &a[i]);

    int ver = 0;
    roots[0] = build(0, n - 1, a);

    while (q--) {
        int type;
        scanf("%d", &type);
        if (type == 1) {
            int k, x, v;
            scanf("%d %d %d", &k, &x, &v);
            roots[v] = update(roots[v], 0, n - 1, k - 1, x);
        } else if (type == 2) {
            int l, r, v;
            scanf("%d %d %d", &l, &r, &v);
            printf("%lld\n", query(roots[v], 0, n - 1, l - 1, r - 1));
        } else {
            int v;
            scanf("%d", &v);
            ver++;
            roots[ver] = roots[v];
        }
    }
    return 0;
}
```

### Độ phức tạp

| Thao tác | Thời gian | Bộ nhớ |
|----------|-----------|--------|
| Khởi tạo | O(n) | O(n) |
| Cập nhật | O(log n) | O(log n) nút mới |
| Truy vấn | O(log n) | O(1) |
| Sao chép | O(1) | O(1) |
| **Tổng** | **O(n + q log n)** | **O(n + q log n)** |

Giới hạn bộ nhớ đến từ việc mỗi lần cập nhật cấp phát tối đa O(log n) nút mới, còn sao chép là miễn phí (chỉ sao chép con trỏ).

---

## Tại sao chọn Persistent Segment Tree

- **Sao chép toàn bộ khi loại 3**: O(n) mỗi lần sao chép, tổng O(n * q). Quá chậm.
- **Chia căn (sqrt decomposition)**: Không thể xử lý hiệu quả cơ chế phiên bản.
- **Persistent segment tree**: O(log n) mỗi thao tác, tổng bộ nhớ O(n + q log n). Hoàn toàn phù hợp với ràng buộc.

Persistent segment tree là kỹ thuật chuẩn cho các bài toán yêu cầu quản lý phiên bản mảng với cập nhật điểm và truy vấn đoạn.
