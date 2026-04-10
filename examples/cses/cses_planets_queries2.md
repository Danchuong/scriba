# CSES: Planets Queries II

## Đề bài

Cho một **đồ thị hàm** gồm **n** hành tinh. Mỗi hành tinh **i** có một cổng dịch chuyển đưa bạn đến hành tinh **t[i]**. Cho **q** truy vấn dạng **(a, b)**, hãy xác định số lần dịch chuyển tối thiểu để đi từ hành tinh **a** đến hành tinh **b**, hoặc trả về **-1** nếu không thể đến được.

### Dữ liệu vào

- Dòng đầu: hai số nguyên n và q (1 <= n, q <= 2*10^5)
- Dòng thứ hai: n số nguyên t[1], t[2], ..., t[n] (1 <= t[i] <= n)
- q dòng tiếp theo: mỗi dòng hai số nguyên a và b cho một truy vấn

### Dữ liệu ra

Với mỗi truy vấn, in ra số lần dịch chuyển tối thiểu từ a đến b, hoặc -1 nếu không thể đến được b từ a.

### Ví dụ

**Dữ liệu vào:**
```
6 3
2 3 1 5 6 4
1 3
4 2
1 1
```

**Dữ liệu ra:**
```
2
-1
0
```

---

## Tính chất của đồ thị hàm

Đồ thị hàm (functional graph) là đồ thị có hướng mà mỗi đỉnh có đúng một cạnh đi ra (bậc ra = 1). Cấu trúc này tạo nên những đặc điểm nổi bật:

1. **Thành phần hình chữ rho (ρ)**: mỗi thành phần liên thông yếu có đúng một chu trình, với các cây treo vào các đỉnh trên chu trình (giống chữ cái Hy Lạp rho).
2. **Mọi đỉnh đều dẫn đến chu trình**: đi theo các cạnh từ bất kỳ đỉnh nào, ta chắc chắn sẽ đi vào một chu trình.
3. **Khả năng tiếp cận bị giới hạn**: đỉnh b chỉ có thể đến được từ đỉnh a nếu b nằm trên đường đi duy nhất từ a vào chu trình, hoặc b nằm trên cùng chu trình mà a sẽ đi tới.

Trong ví dụ của chúng ta, đồ thị có hai thành phần:
- Thành phần 1: các đỉnh {1, 2, 3} tạo thành chu trình 1 -> 2 -> 3 -> 1
- Thành phần 2: các đỉnh {4, 5, 6} tạo thành chu trình 4 -> 5 -> 6 -> 4

---

## Lời giải: Binary Lifting + Phát hiện chu trình

### Ý tưởng tổng quát

1. **Tìm chu trình**: dùng DFS hoặc duyệt lặp để xác định đỉnh nào thuộc chu trình và đỉnh nào là "đuôi" (cây dẫn vào chu trình).

2. **Tính toán độ sâu và thông tin chu trình**: với mỗi đỉnh, tính:
   - `depth[v]`: khoảng cách từ v đến chu trình mà nó dẫn tới
   - `cycle_id[v]`: chu trình mà đỉnh này thuộc về (hoặc dẫn tới)
   - `cycle_pos[v]`: vị trí trong chu trình (với các đỉnh trên chu trình)
   - `cycle_len[c]`: độ dài chu trình c

3. **Bảng nhảy đôi (binary lifting)**: tiền xử lý `lift[k][v]` = đỉnh đến được từ v sau 2^k lần dịch chuyển. Điều này cho phép nhảy bất kỳ khoảng cách nào trong O(log n).

4. **Trả lời truy vấn (a, b)**:
   - Nếu a và b ở khác thành phần: đáp án là **-1**.
   - Nếu b là tổ tiên của a trên nhánh đuôi: dùng binary lifting kiểm tra xem đi từ a có đến b không, và tính khoảng cách.
   - Nếu b nằm trên chu trình: đưa a xuống chu trình (mất depth[a] bước), rồi tính khoảng cách vòng từ điểm vào chu trình đến b.
   - Nếu b nằm trên nhánh đuôi nhưng không phải tổ tiên của a: đáp án là **-1** (không thể rời chu trình để quay ngược lên nhánh đuôi).

### Phân tích chi tiết các trường hợp

Với truy vấn (a, b):

**Trường hợp 1: b nằm trên đường đi từ a đến chu trình (depth[b] < depth[a], tức b gần chu trình hơn)**
- Nhảy a đi (depth[a] - depth[b]) bước. Nếu đến đúng b thì đáp án là depth[a] - depth[b]. Ngược lại, đáp án là -1.

**Trường hợp 2: Cả hai cùng dẫn đến một chu trình, b là đỉnh trên chu trình**
- Đưa a đến chu trình: mất depth[a] bước, đến đỉnh chu trình c_a.
- Tính khoảng cách vòng từ c_a đến b trong chu trình: (cycle_pos[b] - cycle_pos[c_a] + cycle_len) % cycle_len.
- Đáp án = depth[a] + khoảng_cách_vòng.

**Trường hợp 3: b là đỉnh đuôi mà a không thể đến**
- Đáp án là -1. Khi đã đi qua mức độ sâu của b mà không ở tại b, ta không bao giờ có thể quay lại.

### Mã nguồn C++ tham khảo

```cpp
#include <bits/stdc++.h>
using namespace std;

const int LOG = 18;

int main() {
    int n, q;
    scanf("%d%d", &n, &q);

    vector<int> t(n + 1);
    for (int i = 1; i <= n; i++) scanf("%d", &t[i]);

    // Binary lifting
    vector<vector<int>> lift(LOG, vector<int>(n + 1));
    for (int i = 1; i <= n; i++) lift[0][i] = t[i];
    for (int k = 1; k < LOG; k++)
        for (int i = 1; i <= n; i++)
            lift[k][i] = lift[k-1][lift[k-1][i]];

    // Tìm chu trình: theo dõi độ sâu đến chu trình, thành viên chu trình
    vector<int> depth(n + 1, -1), cycle_id(n + 1, -1);
    vector<int> cycle_pos(n + 1, -1), cycle_len;
    vector<int> vis(n + 1, 0); // 0=chưa thăm, 1=đang xử lý, 2=xong
    int num_cycles = 0;

    for (int i = 1; i <= n; i++) {
        if (vis[i]) continue;
        vector<int> path;
        int v = i;
        while (!vis[v]) {
            vis[v] = 1;
            path.push_back(v);
            v = t[v];
        }
        if (vis[v] == 1) {
            // Tìm thấy chu trình mới
            int cid = num_cycles++;
            int clen = 0;
            int u = v;
            vector<int> cyc_nodes;
            do {
                cycle_id[u] = cid;
                cycle_pos[u] = clen++;
                depth[u] = 0;
                vis[u] = 2;
                u = t[u];
            } while (u != v);
            cycle_len.push_back(clen);
        }
        // Đánh dấu các đỉnh còn lại trên đường đi là đã xong
        for (int u : path) {
            if (vis[u] == 1) vis[u] = 2;
        }
    }

    // BFS ngược từ đỉnh chu trình để tính độ sâu
    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; i++) rev[t[i]].push_back(i);

    queue<int> bfs;
    for (int i = 1; i <= n; i++)
        if (depth[i] == 0) bfs.push(i);

    while (!bfs.empty()) {
        int v = bfs.front(); bfs.pop();
        for (int u : rev[v]) {
            if (depth[u] == -1) {
                depth[u] = depth[v] + 1;
                cycle_id[u] = cycle_id[v];
                bfs.push(u);
            }
        }
    }

    // Hàm hỗ trợ: nhảy v về phía trước dist bước
    auto jump = [&](int v, int dist) -> int {
        for (int k = 0; k < LOG; k++)
            if ((dist >> k) & 1)
                v = lift[k][v];
        return v;
    };

    while (q--) {
        int a, b;
        scanf("%d%d", &a, &b);

        if (cycle_id[a] != cycle_id[b]) {
            printf("-1\n");
            continue;
        }

        if (depth[a] >= depth[b]) {
            // Thử đường đi trực tiếp: nhảy a đi (depth[a]-depth[b]) bước
            int dist = depth[a] - depth[b];
            if (jump(a, dist) == b) {
                printf("%d\n", dist);
            } else if (depth[b] == 0) {
                // b nằm trên chu trình, a đến chu trình ở đỉnh khác
                int ca = jump(a, depth[a]);
                int clen = cycle_len[cycle_id[b]];
                int cdist = (cycle_pos[b] - cycle_pos[ca] + clen) % clen;
                printf("%d\n", depth[a] + cdist);
            } else {
                printf("-1\n");
            }
        } else {
            // depth[a] < depth[b]: b xa chu trình hơn a
            // a không thể đến b (phải đi ngược trên nhánh đuôi)
            if (depth[b] == 0) {
                // b nằm trên chu trình, đưa a đến chu trình rồi đi vòng
                int ca = jump(a, depth[a]);
                int clen = cycle_len[cycle_id[b]];
                int cdist = (cycle_pos[b] - cycle_pos[ca] + clen) % clen;
                printf("%d\n", depth[a] + cdist);
            } else {
                printf("-1\n");
            }
        }
    }
    return 0;
}
```

### Độ phức tạp thời gian

- **Tiền xử lý**: O(n log n) cho bảng binary lifting, O(n) cho phát hiện chu trình và tính độ sâu.
- **Mỗi truy vấn**: O(log n) cho các bước nhảy binary lifting.
- **Tổng cộng**: O((n + q) log n).

### Độ phức tạp không gian

O(n log n) cho bảng binary lifting.
