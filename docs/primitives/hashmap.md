# Primitive Spec: `HashMap`

> Status: **draft**. Extends base spec `environments.md` SS5
> (primitive catalog).

---

## 1. Purpose

`HashMap` renders a bucket-based hash table as a vertical two-column table:
an index column on the left and an entries column on the right showing key-value
pairs. It unlocks:

- Hash table collision resolution editorials (separate chaining).
- Hash function distribution visualization showing which buckets receive entries.
- Dictionary / associative array operation walkthroughs.

The design uses bucket-level granularity only -- individual entries within a
bucket are not independently selectable. Each bucket displays a single text
string (e.g. `"cat:3  car:7"`) representing all entries in that bucket.

---

## 2. Shape declaration

```latex
\shape{hm}{HashMap}{
  capacity=8,
  label="Hash Table"
}
```

### 2.1 Required parameters

| Parameter   | Type             | Description                                    |
|-------------|------------------|------------------------------------------------|
| `capacity`  | positive integer | Number of buckets. Must be >= 1.               |

### 2.2 Optional parameters

| Parameter | Type   | Default | Description                                    |
|-----------|--------|---------|------------------------------------------------|
| `label`   | string | none    | Caption text rendered below the table.          |

---

## 3. Addressable parts (selectors)

| Selector          | Addresses                                            |
|-------------------|------------------------------------------------------|
| `hm`              | The entire hash map (whole-shape target)             |
| `hm.bucket[i]`   | Bucket at 0-based index `i`, where `0 <= i < capacity`. |
| `hm.all`          | All buckets.                                         |

Index bounds: bucket index must be in `[0, capacity-1]`. Out-of-range indices
are rejected by the selector validator.

---

## 4. Apply commands

### 4.1 Set bucket value

```latex
\apply{hm.bucket[3]}{value="cat:3  car:7"}
```

Sets the display text for bucket 3. The value is a plain string representing
all entries in that bucket. The entries column auto-widens to fit the longest
bucket value.

### 4.2 Bulk apply

There is no whole-map bulk insert command. To populate multiple buckets, issue
separate `\apply` commands per bucket.

### 4.3 Persistence

Value assignments are **persistent** -- they carry forward to later frames per
base spec SS3.5 semantics.

---

## 5. Semantic states

Standard SS9.2 state classes are applied to individual bucket row `<g>` elements:

```latex
\recolor{hm.bucket[3]}{state=current}   % highlight bucket 3
\recolor{hm.all}{state=dim}             % dim all buckets
\highlight{hm.bucket[5]}               % ephemeral highlight on bucket 5
```

The `all` selector propagates to individual buckets: if a bucket has no specific
state override and `all` is set to a non-idle state, the bucket inherits that
state.

| State       | Visual effect                                          |
|-------------|--------------------------------------------------------|
| `idle`      | Default: gray index column, white entries column       |
| `current`   | Entries column fill #0072B2 (Wong blue), white text    |
| `done`      | Entries column fill #009E73 (Wong green), white text   |
| `dim`       | Opacity 0.35                                           |
| `error`     | Entries column fill #D55E00 (Wong vermillion)          |
| `good`      | Entries column fill #009E73 alt tone                   |
| `highlight` | Gold border #F0E442, 3px dashed (ephemeral)            |

The index column always uses the theme's `bg_alt` color regardless of state.
Only the entries column background changes with state.

---

## 6. Visual conventions

The hash map is rendered as a bordered vertical table:

```
+-----+----------------------------+
|  0  |                            |
+-----+----------------------------+
|  1  | apple:5                    |
+-----+----------------------------+
|  2  |                            |
+-----+----------------------------+
|  3  | cat:3  car:7               |
+-----+----------------------------+
|  4  |                            |
+-----+----------------------------+
         Hash Table
```

- **Index column**: left column with bucket indices (0-based), centered text,
  gray background (`bg_alt`). Width scales with digit count (minimum 40px).
- **Entries column**: right column with bucket contents, left-aligned text.
  Width auto-expands from longest value (minimum 200px).
- **Row height**: 40px per bucket.
- **Dividers**: a vertical line separates index and entries columns; horizontal
  lines separate rows (except above the first row).
- **Outer border**: 1px border with 4px corner radius around the entire table.

---

## 7. Example

```latex
\begin{animation}[id=hash-insert]
\shape{hm}{HashMap}{capacity=5, label="h(x) = x mod 5"}

\step
\apply{hm.bucket[2]}{value="7"}
\recolor{hm.bucket[2]}{state=current}
\narrate{Insert key 7. h(7) = 7 mod 5 = 2. Place in bucket 2.}

\step
\recolor{hm.bucket[2]}{state=idle}
\apply{hm.bucket[3]}{value="13"}
\recolor{hm.bucket[3]}{state=current}
\narrate{Insert key 13. h(13) = 13 mod 5 = 3. Place in bucket 3.}

\step
\recolor{hm.bucket[3]}{state=idle}
\apply{hm.bucket[2]}{value="7  12"}
\recolor{hm.bucket[2]}{state=current}
\narrate{Insert key 12. h(12) = 12 mod 5 = 2. Collision with 7 -- chain in bucket 2.}

\step
\recolor{hm.bucket[2]}{state=done}
\recolor{hm.bucket[3]}{state=done}
\narrate{All insertions complete.}
\end{animation}
```
