# CSES: Necessary Roads (Cầu trong đồ thị)

## Đề bài

Cho một đồ thị vô hướng liên thông gồm **n** đỉnh và **m** cạnh. Nhiệm vụ của bạn là tìm tất cả các cạnh mà nếu xóa đi sẽ làm đồ thị mất tính liên thông. Những cạnh như vậy được gọi là **cầu** (bridge).

### Đầu vào

Dòng đầu tiên chứa hai số nguyên n và m: số đỉnh và số cạnh.

Tiếp theo là m dòng, mỗi dòng chứa hai số nguyên a và b: có một cạnh nối đỉnh a và đỉnh b.

### Đầu ra

Đầu tiên in số lượng cầu k, sau đó in k dòng mô tả các cầu đó.

### Ràng buộc

- 1 <= n <= 10^5
- 1 <= m <= 2 * 10^5
- Đồ thị liên thông

### Ví dụ

**Đầu vào:**
```
7 8
1 2
2 3
3 1
3 4
4 5
5 6
6 7
7 5
```

**Đầu ra:**
```
2
3 4
4 5
```

Cạnh (3,4) và (4,5) là cầu. Các đỉnh {1,2,3} tạo thành một chu trình và {5,6,7} cũng tạo thành một chu trình, nhưng đỉnh 4 nối hai phần này mà không có đường đi dự phòng. Xóa bất kỳ cầu nào cũng làm đồ thị mất liên thông.

---

## Lời giải

### Ý tưởng chính

Một cạnh (u, v) là cầu khi và chỉ khi không tồn tại cạnh ngược (back edge) nào từ cây con gốc v (trong cây DFS) có thể nối lên tới u hoặc tổ tiên của u. Điều này được thể hiện qua **thuật toán tìm cầu của Tarjan**.

### Thuật toán Tarjan

Ta thực hiện DFS và duy trì hai mảng:

- **disc[u]**: thời điểm phát hiện đỉnh u (thứ tự duyệt lần đầu)
- **low[u]**: thời điểm phát hiện nhỏ nhất có thể đạt được từ cây con gốc u thông qua các cạnh ngược

#### Tính low[u]

Với mỗi đỉnh kề v của u trong quá trình DFS:
1. Nếu v **chưa thăm**: đệ quy vào v, sau đó `low[u] = min(low[u], low[v])`
2. Nếu v **đã thăm** và v không phải cha của u (tức (u,v) là cạnh ngược): `low[u] = min(low[u], disc[v])`

#### Điều kiện cầu

Sau khi DFS quay về từ con v tới u:
- Nếu `low[v] > disc[u]`, thì cạnh (u, v) là **cầu**

Điều này có nghĩa là không có cạnh ngược nào từ cây con của v có thể nối tới u hoặc cao hơn, nên việc xóa cạnh (u,v) sẽ tách cây con của v ra khỏi phần còn lại.

### Code C++

```cpp
#include <bits/stdc++.h>
using namespace std;

int n, m, timer = 0;
vector<int> adj[100005];
int disc[100005], low[100005];
bool visited[100005];
vector<pair<int,int>> bridges;

void dfs(int u, int parent) {
    visited[u] = true;
    disc[u] = low[u] = timer++;
    for (int v : adj[u]) {
        if (!visited[v]) {
            dfs(v, u);
            low[u] = min(low[u], low[v]);
            if (low[v] > disc[u]) {
                bridges.push_back({u, v});
            }
        } else if (v != parent) {
            low[u] = min(low[u], disc[v]);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        adj[a].push_back(b);
        adj[b].push_back(a);
    }

    dfs(1, -1);

    cout << bridges.size() << "\n";
    for (auto [u, v] : bridges) {
        cout << u << " " << v << "\n";
    }
    return 0;
}
```

### Độ phức tạp thời gian

**O(n + m)** -- chỉ cần một lần DFS duyệt qua tất cả các đỉnh và cạnh.

### Độ phức tạp bộ nhớ

**O(n + m)** -- lưu danh sách kề cùng các mảng disc/low và ngăn xếp đệ quy.

---

## Tại sao thuật toán đúng

Cây DFS phân chia các cạnh thành **cạnh cây** (tree edge) và **cạnh ngược** (back edge). Một cạnh cây (u, v) là cầu khi và chỉ khi không có cạnh ngược nào trong cây con của v "nhảy qua" nó để nối tới u hoặc cao hơn. Giá trị low chính xác theo dõi tổ tiên cao nhất có thể đạt được qua các cạnh ngược. Khi `low[v] > disc[u]`, toàn bộ cây con của v sẽ bị cô lập nếu ta cắt cạnh (u, v).

### Các trường hợp đặc biệt

- **Đồ thị cây** (m = n-1): mọi cạnh đều là cầu
- **Đồ thị hai-liên-thông**: không có cầu nào
- **Cạnh song song giữa cùng một cặp đỉnh**: các cạnh song song không bao giờ là cầu (cần theo dõi chỉ số cạnh thay vì chỉ đỉnh cha để xử lý đúng trường hợp này)
