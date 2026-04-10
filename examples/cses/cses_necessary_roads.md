# CSES: Necessary Roads (Bridges)

## Problem Statement

You are given an undirected connected graph with **n** nodes and **m** edges. Your task is to find all edges whose removal would disconnect the graph. These edges are called **bridges** (or necessary roads).

### Input

The first line has two integers n and m: the number of nodes and edges.

Then m lines follow, each containing two integers a and b: there is an edge between nodes a and b.

### Output

First print the number of necessary roads k, then print k lines describing them.

### Constraints

- 1 <= n <= 10^5
- 1 <= m <= 2 * 10^5
- The graph is connected

### Example

**Input:**
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

**Output:**
```
2
3 4
4 5
```

Edges (3,4) and (4,5) are bridges. Nodes {1,2,3} form a cycle and {5,6,7} form a cycle, but node 4 connects them with no redundant path. Removing either bridge disconnects the graph.

---

## Solution

### Key Insight

An edge (u, v) is a bridge if and only if there is no back edge from the subtree rooted at v (in a DFS tree) that reaches u or an ancestor of u. This is captured by **Tarjan's bridge-finding algorithm**.

### Tarjan's Algorithm

We perform a DFS and maintain two arrays:

- **disc[u]**: the discovery time of node u (when it was first visited)
- **low[u]**: the minimum discovery time reachable from the subtree rooted at u using back edges

#### Computing low[u]

For each neighbor v of u during DFS:
1. If v is **unvisited**: recurse into v, then `low[u] = min(low[u], low[v])`
2. If v is **visited** and v is not the parent of u (i.e., (u,v) is a back edge): `low[u] = min(low[u], disc[v])`

#### Bridge Condition

After DFS returns from child v back to u:
- If `low[v] > disc[u]`, then edge (u, v) is a **bridge**

This means there is no back edge from v's subtree that can reach u or above, so removing (u,v) disconnects v's subtree from the rest.

### C++ Solution

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

### Time Complexity

**O(n + m)** -- a single DFS visits every node and edge exactly once.

### Space Complexity

**O(n + m)** -- adjacency list storage plus the disc/low arrays and recursion stack.

---

## Why This Works

The DFS tree partitions edges into **tree edges** and **back edges**. A tree edge (u, v) is a bridge only if no back edge in v's subtree "jumps over" it to reach u or higher. The low value precisely tracks the highest ancestor reachable via back edges. When `low[v] > disc[u]`, v's entire subtree is isolated if we cut (u, v).

### Edge Cases

- **Tree graph** (m = n-1): every edge is a bridge
- **Biconnected graph**: no bridges exist
- **Multiple edges between same pair**: parallel edges are never bridges (need to track edge index, not just parent node, to handle this correctly)
