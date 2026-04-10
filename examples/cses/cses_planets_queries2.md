# CSES: Planets Queries II

## Problem Statement

You are given a functional graph of **n** planets. Each planet **i** has a teleporter that sends you to planet **t[i]**. Given **q** queries of the form **(a, b)**, determine the minimum number of teleportations to get from planet **a** to planet **b**, or report **-1** if it is impossible.

### Input

- First line: two integers n and q (1 <= n, q <= 2*10^5)
- Second line: n integers t[1], t[2], ..., t[n] (1 <= t[i] <= n)
- Next q lines: two integers a and b per query

### Output

For each query, print the minimum number of teleportations from a to b, or -1 if b is not reachable from a.

### Example

**Input:**
```
6 3
2 3 1 5 6 4
1 3
4 2
1 1
```

**Output:**
```
2
-1
0
```

---

## Functional Graph Properties

A functional graph has exactly one outgoing edge per node (outdegree = 1). This creates a distinctive structure:

1. **Rho-shaped components**: each weakly connected component has exactly one cycle, with trees hanging off cycle nodes (like the Greek letter rho).
2. **Every node eventually reaches its component's cycle**: following the edges from any node, you must eventually enter a cycle.
3. **Reachability is limited**: node b is reachable from node a only if b lies on the unique path from a into the cycle, or b is on the same cycle that a eventually reaches.

In our example, the graph has two components:
- Component 1: nodes {1, 2, 3} forming cycle 1 -> 2 -> 3 -> 1
- Component 2: nodes {4, 5, 6} forming cycle 4 -> 5 -> 6 -> 4

---

## Solution: Binary Lifting + Cycle Detection

### High-Level Approach

1. **Find cycles**: use DFS or repeated traversal to identify which nodes belong to a cycle and which are "tails" (trees leading into the cycle).

2. **Compute depths and cycle info**: for each node, compute:
   - `depth[v]`: distance from v to the cycle it eventually enters
   - `cycle_id[v]`: which cycle the node belongs to (or leads to)
   - `cycle_pos[v]`: position within the cycle (for cycle nodes)
   - `cycle_len[c]`: length of cycle c

3. **Binary lifting table**: precompute `lift[k][v]` = the node reached from v after 2^k teleportations. This allows jumping any distance in O(log n).

4. **Answer queries (a, b)**:
   - If a and b are in different components: answer is **-1**.
   - If b is an ancestor of a on the tail: use binary lifting to check if walking from a reaches b, and compute the distance.
   - If b is on the cycle: walk a down to the cycle (depth[a] steps), then compute the cyclic distance from the cycle entry point to b.
   - If b is on the tail but not an ancestor of a: answer is **-1** (you cannot leave the cycle to go back up a tail).

### Detailed Case Analysis

For query (a, b):

**Case 1: b is on a's tail path (depth[b] >= depth[a] is impossible since we go toward cycle; actually depth[b] < depth[a] means b is closer to cycle)**
- Lift a by (depth[a] - depth[b]) steps. If we land on b, the answer is depth[a] - depth[b]. Otherwise, -1.

**Case 2: Both reach the same cycle, b is a cycle node**
- Walk a to the cycle: takes depth[a] steps, arriving at some cycle node c_a.
- Compute cyclic distance from c_a to b within the cycle: (cycle_pos[b] - cycle_pos[c_a] + cycle_len) % cycle_len.
- Answer = depth[a] + cyclic_distance.

**Case 3: b is a tail node that a cannot reach**
- Answer is -1. Once you pass b's depth level without being at b, you can never reach it.

### C++ Code Sketch

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

    // Find cycles: track depth to cycle, cycle membership
    vector<int> depth(n + 1, -1), cycle_id(n + 1, -1);
    vector<int> cycle_pos(n + 1, -1), cycle_len;
    vector<int> vis(n + 1, 0); // 0=unvisited, 1=in-progress, 2=done
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
            // Found a new cycle
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
        // Mark remaining path nodes as done
        for (int u : path) {
            if (vis[u] == 1) vis[u] = 2;
        }
    }

    // BFS/DFS from cycle nodes backward to compute depths
    // (reverse graph traversal)
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

    // Helper: jump v forward by dist steps
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
            // Try direct path: jump a by (depth[a]-depth[b]) steps
            int dist = depth[a] - depth[b];
            if (jump(a, dist) == b) {
                printf("%d\n", dist);
            } else if (depth[b] == 0) {
                // b is on cycle, a reaches cycle at different node
                int ca = jump(a, depth[a]);
                int clen = cycle_len[cycle_id[b]];
                int cdist = (cycle_pos[b] - cycle_pos[ca] + clen) % clen;
                printf("%d\n", depth[a] + cdist);
            } else {
                printf("-1\n");
            }
        } else {
            // depth[a] < depth[b]: b is farther from cycle than a
            // a cannot reach b (would need to go backward on tail)
            if (depth[b] == 0) {
                // b is on cycle, walk a to cycle then around
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

### Time Complexity

- **Preprocessing**: O(n log n) for binary lifting table, O(n) for cycle detection and depth computation.
- **Per query**: O(log n) for binary lifting jumps.
- **Total**: O((n + q) log n).

### Space Complexity

O(n log n) for the binary lifting table.
