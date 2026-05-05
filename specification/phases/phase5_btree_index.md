# Phase 5: B-Tree Index

## Goal
B+ tree index stored on disk pages via the buffer pool. CREATE INDEX command. Index scan operator for point and range queries.

## Modules to Create

| Module                          | Responsibility                              |
|---------------------------------|---------------------------------------------|
| `toydb/storage/btree.py`        | B+ tree: search, insert, delete, range_scan |
| `toydb/storage/index_manager.py` | Index lifecycle: create, drop, lookup      |

## Modules to Modify

| Module                      | Changes                                          |
|-----------------------------|--------------------------------------------------|
| `toydb/catalog.py`          | Store index metadata in sys_indexes              |
| `toydb/parser/parser.py`    | Parse CREATE INDEX syntax                        |
| `toydb/parser/ast_nodes.py` | Add CreateIndex AST node                         |
| `toydb/executor_mem.py`     | Choose IndexScan when index is available for WHERE |

## Tasks

### 1. AST and parser additions
- [ ] Add `CreateIndex(name: str, table: str, column: str)` frozen dataclass to ast_nodes.py
- [ ] Parse `CREATE INDEX idx_name ON table_name (column_name);` in parser.py

### 2. B+ tree node types
- [ ] Define `BTreeNode` base with `is_leaf`, `num_keys`, `keys`
- [ ] Define `InternalNode(BTreeNode)` with `child_page_ids: list[int]` (len = num_keys + 1)
- [ ] Define `LeafNode(BTreeNode)` with:
  - `next_leaf: Optional[int]` -- page_id of next leaf for range scans
  - `row_pointers: list[tuple[int, int]]` -- (page_id, slot_id) pairs
- [ ] Node page layout:
  - Internal: `[is_leaf(1B=0x00)][num_keys(2B)][keys...][child_page_ids...]`
  - Leaf: `[is_leaf(1B=0x01)][num_keys(2B)][next_leaf(4B)][keys...][row_pointers(6B each)...]`
- [ ] Serialize/deserialize nodes to/from page bytes

### 3. B+ tree operations (`storage/btree.py`)
- [ ] Implement `BTree` class
- [ ] `__init__(self, buffer_pool: BufferPoolManager, file_id: int, root_page_id: int)`
- [ ] `search(key: Any) -> Optional[tuple[int, int]]` -- point lookup, traverse from root to leaf
- [ ] `range_scan(low: Any, high: Any) -> Iterator[tuple[int, int]]` -- follow leaf chain via next_leaf pointers
- [ ] `insert(key: Any, page_id: int, slot_id: int) -> None`:
  - Find correct leaf node
  - Insert key + pointer
  - If leaf is full, split: create new leaf, move upper half of keys, update next_leaf pointers, push middle key up to parent
  - Handle recursive splits up to root (root split creates new root)
- [ ] `delete(key: Any) -> None` -- remove from leaf (lazy: no merge/rebalance in initial version)
- [ ] All node access goes through buffer pool (fetch_page/unpin_page)

### 4. Index manager (`storage/index_manager.py`)
- [ ] Implement `IndexManager` class
- [ ] `__init__(self, catalog: CatalogManager, buffer_pool: BufferPoolManager)`
- [ ] `create_index(name: str, table_name: str, column_name: str) -> None`:
  - Create new B-tree file via disk manager
  - Scan all existing tuples in the table
  - Insert each (key, page_id, slot_id) into the B-tree
  - Register index in catalog
- [ ] `get_index(table_name: str, column_name: str) -> Optional[BTree]`
- [ ] `drop_index(name: str) -> None`

### 5. Catalog extension (`catalog.py`)
- [ ] Add `sys_indexes` system table: `(index_id INT, table_id INT, column_id INT, name VARCHAR(64), is_unique BOOL, root_page_id INT)`
- [ ] Define `IndexMeta` dataclass
- [ ] `create_index(name, table_id, column_id, root_page_id) -> index_id`
- [ ] `get_indexes(table_id) -> list[IndexMeta]`
- [ ] `drop_index(index_id) -> None`

### 6. Scan selection logic (`executor_mem.py`)
- [ ] Implement naive scan selection:
  - If WHERE is `column op literal` and index exists on column and op is =, <, >, <=, >=: use IndexScan
  - Otherwise: use SeqScan (fallback)
- [ ] IndexScan: use B-tree search/range_scan to get (page_id, slot_id) pointers, then fetch tuples from heap file
- [ ] Maintain index on INSERT: add new entries to relevant B-tree indexes
- [ ] Maintain index on DELETE: remove entries from relevant B-tree indexes

### 7. Index data files
- [ ] Index files stored as `data/{table_name}_idx_{column_name}.dat`
- [ ] Each node occupies one page in the B-tree file

### 8. Tests
- [ ] `tests/test_btree.py`:
  - Insert 1000 sequential keys, search each one
  - Insert 1000 random keys, search each one
  - Range scan: insert keys 1..100, range_scan(25, 75) returns exactly 51 entries
  - Page split: insert enough keys to trigger leaf split, verify tree remains correct
  - Delete: delete keys, verify search returns None
- [ ] `tests/test_e2e.py` (extended): CREATE INDEX, verify SELECT uses IndexScan, verify correctness matches SeqScan

## Supported SQL (additions)

```sql
CREATE INDEX idx_users_age ON users (age);
SELECT * FROM users WHERE age = 30;        -- IndexScan (point)
SELECT * FROM users WHERE age > 20;        -- IndexScan (range)
SELECT * FROM users WHERE name = 'Alice';  -- SeqScan (no index on name)
```

## Done Criteria
- [ ] CREATE INDEX builds a B+ tree from existing table data
- [ ] Point lookup (WHERE col = val) uses index when available
- [ ] Range scan (WHERE col > val) follows leaf chain
- [ ] Leaf splits work correctly when a node overflows
- [ ] Index maintained on INSERT (new index entries added)
- [ ] Index maintained on DELETE (index entries removed)
- [ ] SeqScan still works as fallback for non-indexed queries
- [ ] All tests pass
