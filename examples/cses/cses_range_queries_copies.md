# CSES: Range Queries and Copies

## Problem Statement

You have an array of **n** integers. Your task is to process **q** queries of three types:

1. **Update:** Set `a[k] = x` in the current version.
2. **Sum query:** Compute the sum of elements `a[l..r]` in the current version.
3. **Copy:** Create a new version by copying the current array. Subsequent operations work on the new version; the old version is preserved and may be revisited later.

After a copy, operations apply to the newest version. Each version is an independent snapshot of the array at the time of copying.

### Input

The first line contains two integers n and q.
The second line contains n integers: the initial array.
Each of the next q lines describes a query:
- `1 k x v` -- in version v, set a[k] = x
- `2 l r v` -- in version v, compute sum of a[l..r]
- `3 v` -- copy version v to create a new version

### Constraints

- 1 <= n, q <= 2 * 10^5
- 1 <= a[i] <= 10^9

---

## Solution: Persistent Segment Tree

### Key Insight

A naive approach would copy the entire array on each type-3 query, leading to O(n) per copy and O(n * q) total memory. Instead, we use a **persistent segment tree** with **path copying**: each update creates only O(log n) new nodes along the root-to-leaf path, while sharing all unchanged subtrees with previous versions.

### How Path Copying Works

A standard segment tree for an array of size n has O(n) nodes. When we update a single element, only the nodes on the path from the leaf to the root change -- that is O(log n) nodes. In a persistent segment tree:

1. For each node on the update path, allocate a **new node** with the updated value.
2. The new node's children that are NOT on the update path simply **point to the old children** from the previous version.
3. Store the new root in a **roots array** indexed by version number.

This means:
- Old versions remain fully intact (their root still points to the original structure).
- Each update costs O(log n) time and O(log n) space (for the new nodes).
- Queries on any version work exactly like standard segment tree queries, starting from that version's root.

### Copy Operation

A copy is trivially O(1): just push the current root pointer into the roots array. The new version shares the entire tree with the source version until a future update diverges them via path copying.

### Data Structures

```cpp
struct Node {
    long long sum;
    int left, right;  // indices into a node pool
};

const int MAXN = 200005;
const int MAXNODES = MAXN * 40;  // ~n + q * log(n) nodes

Node tree[MAXNODES];
int pool = 0;
int roots[MAXN];  // roots[v] = root node index for version v
```

### Build

Build the initial segment tree from the array. This creates the standard O(n) nodes.

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

### Point Update (with persistence)

Create new nodes along the path from root to the target leaf. All other children are shared with the previous version.

```cpp
int update(int prev, int l, int r, int pos, long long val) {
    int id = pool++;
    tree[id] = tree[prev];  // copy the old node
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

### Range Sum Query

Standard segment tree query, unchanged from non-persistent version.

```cpp
long long query(int id, int l, int r, int ql, int qr) {
    if (ql > r || qr < l) return 0;
    if (ql <= l && r <= qr) return tree[id].sum;
    int mid = (l + r) / 2;
    return query(tree[id].left, l, mid, ql, qr)
         + query(tree[id].right, mid + 1, r, ql, qr);
}
```

### Main Loop

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

### Complexity

| Operation | Time | Space |
|-----------|------|-------|
| Build | O(n) | O(n) |
| Update | O(log n) | O(log n) new nodes |
| Query | O(log n) | O(1) |
| Copy | O(1) | O(1) |
| **Total** | **O(n + q log n)** | **O(n + q log n)** |

The space bound comes from each update allocating at most O(log n) new nodes, and copies being free (just a pointer copy).

---

## Why Persistent Over Other Approaches

- **Full copy on type-3**: O(n) per copy, O(n * q) total. Too slow.
- **Sqrt decomposition**: Cannot efficiently handle versioning.
- **Persistent segment tree**: O(log n) per operation, O(n + q log n) total space. Fits the constraints perfectly.

The persistent segment tree is the standard technique for problems requiring array versioning with point updates and range queries.
