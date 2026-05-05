# ToyDB -- Architecture

## System Overview

ToyDB is a layered database engine. A SQL statement flows top-down through six layers, each with a single responsibility. Data flows bottom-up through the same stack when results are returned.

```
Client (REPL or TCP)
  |
  v
[1. Network Layer]        -- TCP listener, wire protocol, session state
  |
  v
[2. SQL Frontend]         -- Lexer -> Parser -> Binder (name resolution)
  |
  v
[3. Query Processing]     -- Logical plan -> Optimizer -> Physical plan
  |
  v
[4. Execution Engine]     -- Volcano iterator model: open/next/close
  |
  v
[5. Storage Engine]       -- Buffer pool, heap files, B-tree indexes
  |
  v
[6. Disk Manager]         -- Raw page I/O to data files and WAL
```

A cross-cutting Catalog provides metadata to layers 2-5. A Transaction Manager provides ACID guarantees across layers 4-6.

## Layer 1: Network Layer

### Responsibility
Accept TCP connections, deserialize incoming SQL from the wire protocol, serialize result rows back, manage per-connection session state.

### Components

**Server** (`server.py`)
- Listens on a configurable TCP port (default 9876).
- Spawns one thread per connection (educational simplicity over async scalability).
- Each connection gets a `Session` object.

**Wire Protocol** (`protocol.py`)
- Binary framing: `[4 bytes payload_length][1 byte message_type][payload]`.
- Message types:

| Code | Name     | Direction       | Payload                       |
|------|----------|-----------------|-------------------------------|
| 0x01 | QUERY    | client -> server | UTF-8 SQL string              |
| 0x02 | ROW_DATA | server -> client | Serialized tuple              |
| 0x03 | OK       | server -> client | Affected row count (4 bytes)  |
| 0x04 | ERROR    | server -> client | UTF-8 error message           |
| 0x05 | READY    | server -> client | Empty (ready for next query)  |

**Session** (`session.py`)
- Holds connection-specific state: current transaction context (if any), autocommit flag, default database.

### Interface to next layer
Session passes the raw SQL string down to the SQL Frontend and receives back an iterator of result tuples or a status message.

## Layer 2: SQL Frontend

### Responsibility
Transform a SQL string into a validated, resolved Abstract Syntax Tree (AST).

### Components

**Lexer** (`parser/lexer.py`)
- Hand-written character-by-character tokenizer.
- Token types: KEYWORD, IDENTIFIER, INTEGER_LIT, FLOAT_LIT, STRING_LIT, OPERATOR, COMMA, LPAREN, RPAREN, SEMICOLON, STAR, EOF.
- Keywords are case-insensitive. Identifiers preserve case.
- Produces a list of `Token(type, value, position)` objects.

**Parser** (`parser/parser.py`)
- Recursive descent parser. One method per grammar rule.
- Entry point: `parse(tokens) -> Statement`.
- Grammar (simplified):

```
statement       := create_table | drop_table | create_index
                 | insert | select | update | delete
                 | begin | commit | rollback
                 | show_tables | describe | explain

select          := SELECT column_list FROM table_ref
                   [join_clause] [where_clause]
                   [order_clause] [limit_clause]

column_list     := STAR | expression (COMMA expression)*
expression      := or_expr
or_expr         := and_expr (OR and_expr)*
and_expr        := comparison (AND comparison)*
comparison      := add_expr [comp_op add_expr]
add_expr        := mul_expr ((PLUS | MINUS) mul_expr)*
mul_expr        := unary ((STAR | SLASH) unary)*
unary           := [NOT | MINUS] primary
primary         := literal | column_ref | LPAREN expression RPAREN
                 | function_call
```

**AST Nodes** (`parser/ast_nodes.py`)
- All nodes are frozen dataclasses. Key types:
  - `CreateTable(name, columns: list[ColumnDef])`
  - `Insert(table, values: list[Expression])`
  - `Select(columns, table, joins, where, order_by, limit)`
  - `Update(table, assignments: list[Assignment], where)`
  - `Delete(table, where)`
  - `BinaryOp(left, op, right)`, `UnaryOp(op, operand)`, `Literal(value)`, `ColumnRef(table, name)`

**Binder** (integrated into parser or separate `binder.py`)
- Resolves table names and column names against the Catalog.
- Validates types: ensures comparison operands are compatible, INSERT values match column types.
- Attaches `table_id` and `column_id` to `ColumnRef` nodes.
- Reports errors with position information: `"Column 'agee' not found in table 'users' at position 34"`.

### Interface to next layer
Produces a validated `Statement` AST node. Passes it to the Query Processing layer.

## Layer 3: Query Processing

### Responsibility
Transform a validated AST into an optimized physical execution plan.

### Components

**Logical Planner** (`planner/planner.py`)
- Converts AST into a tree of relational algebra operators:
  - `SeqScanNode(table_id)` -- read all rows from a table
  - `FilterNode(child, predicate)` -- apply WHERE condition
  - `ProjectNode(child, columns)` -- select specific columns
  - `SortNode(child, key, direction)` -- ORDER BY
  - `LimitNode(child, count)` -- LIMIT
  - `NestedLoopJoinNode(left, right, condition)` -- JOIN
  - `AggregateNode(child, group_by, aggregates)` -- GROUP BY (future extension)
  - `IndexScanNode(table_id, index_id, key_range)` -- read via index

**Optimizer** (`planner/optimizer.py`)
- Rule-based, applied in order:
  1. **Predicate pushdown** -- push Filter nodes as close to Scan nodes as possible. A filter above a join that references only one side moves below the join to that side.
  2. **Index selection** -- if a Filter references a column with an available B-tree index and the operator is `=`, `<`, `>`, `<=`, `>=`, replace `SeqScan + Filter` with `IndexScan`.
  3. **Projection pruning** -- remove columns from scan output that are not needed by any upstream node.
- Each rule is a function `optimize_rule(plan_node) -> plan_node` that walks the tree and returns a transformed copy.

### Interface to next layer
Produces a `PlanNode` tree. Passes it to the Execution Engine.

## Layer 4: Execution Engine

### Responsibility
Execute the physical plan tree and produce result tuples using the Volcano iterator model.

### Core Abstraction

```python
class Executor(ABC):
    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def next(self) -> Optional[Tuple]: ...

    @abstractmethod
    def close(self) -> None: ...
```

Each `PlanNode` maps to one `Executor` subclass. Executors compose by nesting: calling `next()` on an outer executor triggers `next()` on its child -- a pull-based data flow.

### Executor Types

| Executor             | Behavior                                                        |
|----------------------|-----------------------------------------------------------------|
| SeqScanExecutor      | Opens heap file, calls `next()` to return one tuple per page slot |
| IndexScanExecutor    | Traverses B-tree, fetches matching tuples from heap              |
| FilterExecutor       | Calls child.next(), evaluates predicate, skips non-matching rows |
| ProjectExecutor      | Calls child.next(), extracts requested columns                   |
| SortExecutor         | Materializes all child tuples in open(), sorts, yields in next() |
| LimitExecutor        | Counts calls to next(), returns None after limit reached         |
| NestedLoopJoinExec   | For each left tuple, scans all right tuples, emits matches       |
| InsertExecutor       | Writes tuples to heap file (and indexes), returns affected count |
| UpdateExecutor       | Reads via child, modifies tuples in-place, returns affected count |
| DeleteExecutor       | Reads via child, marks tuples as deleted, returns affected count |

### Expression Evaluator (`expression.py`)
- `evaluate(expr: Expression, row: Tuple, schema: Schema) -> Value`
- Recursive evaluation of the expression tree.
- Handles type coercion: INT + FLOAT -> FLOAT, any comparison with NULL -> NULL.

### Interface to next layer
Executors call the Storage Engine to read/write tuples, fetch/unpin pages, and perform index lookups.

## Layer 5: Storage Engine

### Responsibility
Manage persistent data structures: heap files for table data, B-tree indexes for fast lookups, and a buffer pool for caching pages in memory.

### Components

**Buffer Pool Manager** (`storage/buffer_pool.py`)
- Central page cache between the execution engine and disk.
- Fixed number of frames (configurable, default 64).
- `page_table: dict[PageID, FrameID]` for O(1) lookup.
- API:
  - `fetch_page(page_id) -> Page` -- load from disk if not cached, pin the frame.
  - `unpin_page(page_id, is_dirty: bool)` -- allow eviction, mark dirty if modified.
  - `new_page() -> Page` -- allocate a fresh page, return it pinned.
  - `flush_page(page_id)` -- write dirty page to disk immediately.
  - `flush_all()` -- write all dirty pages (used during checkpoint).

**LRU Replacer** (`storage/replacer.py`)
- Tracks unpinned frames in LRU order.
- `record_access(frame_id)` -- move to most-recently-used.
- `evict() -> Optional[FrameID]` -- return the least-recently-used unpinned frame.
- Uses `collections.OrderedDict` internally for O(1) operations.

**Heap File** (`storage/heap_file.py`)
- One heap file per table. File path: `data/{table_name}.dat`.
- Operations:
  - `insert_tuple(tuple_data: bytes) -> (page_id, slot_id)` -- find page with space, insert.
  - `get_tuple(page_id, slot_id) -> bytes` -- read specific tuple.
  - `delete_tuple(page_id, slot_id)` -- mark slot as deleted.
  - `update_tuple(page_id, slot_id, new_data: bytes)` -- delete + insert (if size changed) or in-place update.
  - `scan() -> Iterator[bytes]` -- iterate all live tuples across all pages.
- Uses the buffer pool for all page access -- never reads/writes disk directly.

**Slotted Page** (`storage/page.py`)
- Page size: 4096 bytes.
- Layout:

```
Offset 0:    [PageHeader: 16 bytes]
               page_id       (4 bytes, uint32)
               num_slots     (2 bytes, uint16)
               free_start    (2 bytes, uint16) -- end of slot array
               free_end      (2 bytes, uint16) -- start of tuple data
               flags         (2 bytes, uint16) -- is_leaf, etc.
               page_lsn      (4 bytes, uint32) -- LSN of last modification

Offset 16:   [Slot Array: grows forward, 4 bytes per slot]
               slot[0]: offset (2 bytes) + length (2 bytes)
               slot[1]: offset (2 bytes) + length (2 bytes)
               ...

               [Free Space]

             [Tuple Data: grows backward from end of page]
               tuple[n]: raw serialized bytes
               ...
               tuple[1]: raw serialized bytes
               tuple[0]: raw serialized bytes

Offset 4095: [End of page]
```

- A slot with offset=0 and length=0 means deleted (tombstone).
- `free_space() = free_end - free_start` -- available bytes for new tuples.

**Tuple Serialization** (`utils/tuple_serde.py`)
- Format: `[null_bitmap][col0_data][col1_data]...`
- Null bitmap: 1 bit per column, rounded up to full bytes. Bit=1 means NULL.
- INT: 4 bytes, big-endian signed (`struct.pack('>i', val)`).
- FLOAT: 8 bytes, big-endian double (`struct.pack('>d', val)`).
- VARCHAR: 2-byte length prefix (uint16) + UTF-8 encoded bytes.
- BOOL: 1 byte (0x00 = false, 0x01 = true).

**B-Tree Index** (`storage/btree.py`)
- B+ tree variant: all values in leaf nodes, internal nodes hold keys + child page pointers only.
- Leaf nodes have a `next_leaf` pointer for efficient range scans.
- Each node is one page, stored via the buffer pool.
- Node layout:

```
Internal node:
  [is_leaf(1B)][num_keys(2B)][keys...][child_page_ids...]

Leaf node:
  [is_leaf(1B)][num_keys(2B)][next_leaf(4B)][keys...][row_pointers...]
  where row_pointer = (page_id: uint32, slot_id: uint16)
```

- Operations:
  - `search(key) -> Optional[(page_id, slot_id)]` -- point lookup.
  - `range_scan(low, high) -> Iterator[(page_id, slot_id)]` -- follow leaf chain.
  - `insert(key, page_id, slot_id)` -- insert into leaf, split if full.
  - `delete(key)` -- remove from leaf (lazy: no merge/rebalance in initial version).

**Index Manager** (`storage/index_manager.py`)
- Maintains a registry of indexes per table (stored in catalog).
- `create_index(table, column) -> BTree` -- build index by scanning all existing tuples.
- `get_index(table, column) -> Optional[BTree]` -- look up existing index.

### Interface to next layer
All page reads/writes go through the buffer pool, which calls the Disk Manager.

## Layer 6: Disk Manager

### Responsibility
Lowest layer. Performs raw page I/O against data files and WAL.

### Components

**Disk Manager** (`storage/disk_manager.py`)
- One file handle per table data file, one for WAL.
- `read_page(file_id, page_id) -> bytes` -- seek to `page_id * PAGE_SIZE`, read `PAGE_SIZE` bytes.
- `write_page(file_id, page_id, data: bytes)` -- seek and write.
- `allocate_page(file_id) -> page_id` -- extend the file by one page, return the new page ID.
- `file_size(file_id) -> int` -- used to determine total page count.
- All I/O is synchronous. `os.fsync()` on WAL writes for durability.

## Cross-Cutting: Catalog

### Responsibility
Store and serve metadata about all database objects. Every layer above disk uses the catalog.

### Storage (`catalog.py`)
- Three logical tables (bootstrapped at first startup):
  - `sys_tables(table_id INT, name VARCHAR(64), heap_file VARCHAR(128), num_columns INT)`
  - `sys_columns(table_id INT, column_id INT, name VARCHAR(64), data_type INT, max_length INT, nullable BOOL)`
  - `sys_indexes(index_id INT, table_id INT, column_id INT, name VARCHAR(64), is_unique BOOL, root_page_id INT)`
- Catalog data is stored in its own heap file (`data/_catalog.dat`) using the same storage engine -- the catalog is self-hosting.
- At startup, the catalog is loaded into memory for fast lookup. Modifications are written through to disk.

### API
- `get_table(name) -> TableMeta` -- resolve table name to metadata.
- `get_columns(table_id) -> list[ColumnMeta]` -- column definitions for a table.
- `get_indexes(table_id) -> list[IndexMeta]` -- all indexes on a table.
- `create_table(name, columns) -> table_id` -- register a new table.
- `create_index(name, table_id, column_id) -> index_id` -- register a new index.
- `drop_table(table_id)` -- remove table and its indexes from catalog.
- `list_tables() -> list[TableMeta]` -- for SHOW TABLES.

## Cross-Cutting: WAL and Recovery

### Responsibility
Ensure durability. No committed data is lost, even on crash.

### Write-Ahead Log (`txn/wal.py`)
- Single append-only file: `data/wal.log`.
- WAL record format:

```
[record_length: 4 bytes, uint32]
[lsn: 8 bytes, uint64]
[txn_id: 4 bytes, uint32]
[record_type: 1 byte]
[table_id: 4 bytes, uint32]
[page_id: 4 bytes, uint32]
[payload_length: 4 bytes, uint32]
[payload: variable]
[checksum: 4 bytes, CRC32]
```

- Record types:
  - `INSERT (0x01)`: payload = serialized tuple bytes
  - `DELETE (0x02)`: payload = slot_id
  - `UPDATE (0x03)`: payload = slot_id + before_image + after_image
  - `COMMIT (0x10)`: payload = empty
  - `ABORT (0x11)`: payload = empty
  - `CHECKPOINT (0x20)`: payload = list of dirty (page_id, page_lsn) pairs

- WAL write protocol:
  1. Before any data page modification, append the WAL record.
  2. Before flushing a dirty page to disk, ensure its WAL records are flushed (`page_lsn <= flushed_lsn`).
  3. On COMMIT, force-flush WAL to disk (`os.fsync`), then release locks.

### Recovery Manager (`txn/recovery.py`)
- On startup, scans WAL from the last checkpoint.
- Phase 1 (Analysis): identify which transactions were active, which pages are dirty.
- Phase 2 (Redo): replay all records after checkpoint to bring pages up to date.
- Phase 3 (Undo): roll back any uncommitted transactions by applying before-images in reverse.
- After recovery, write a new checkpoint and truncate old WAL.

## Cross-Cutting: Transaction Manager

### Responsibility
Provide ACID guarantees for groups of operations.

### Components

**Transaction Manager** (`txn/transaction.py`)
- `begin() -> txn_id` -- allocate a new transaction ID, create TxnContext.
- `commit(txn_id)` -- write COMMIT WAL record, flush WAL, release locks.
- `abort(txn_id)` -- write ABORT WAL record, undo changes, release locks.
- Maintains `active_transactions: dict[txn_id, TxnContext]`.

**Transaction Context** (`txn/txn_context.py`)
- `txn_id: int`
- `status: enum (ACTIVE, COMMITTED, ABORTED)`
- `acquired_locks: list[(table_id, row_id, lock_mode)]`
- `wal_records: list[LSN]` -- for undo on abort
- `start_lsn: int` -- LSN at transaction start

**Lock Manager** (`txn/lock_manager.py`)
- Granularity: row-level locks identified by `(table_id, page_id, slot_id)`.
- Two modes: SHARED (for reads) and EXCLUSIVE (for writes).
- Compatibility matrix:

|            | SHARED     | EXCLUSIVE  |
|------------|------------|------------|
| SHARED     | compatible | conflict   |
| EXCLUSIVE  | conflict   | conflict   |

- Two-Phase Locking (2PL): locks are acquired as needed, all released only at commit/abort. No lock is released before the transaction ends.
- Deadlock handling: simple timeout (5 seconds). If a lock wait exceeds the timeout, abort the waiting transaction.
- Lock table: `dict[resource_key, LockEntry]` where `LockEntry` tracks holders and wait queue.

## Project File Structure

```
toydb/
  __init__.py
  __main__.py            # entry point: --mode repl|server
  repl.py                # interactive REPL with readline
  server.py              # TCP server
  client.py              # client library for connecting to server
  protocol.py            # wire protocol encode/decode
  session.py             # per-connection state

  parser/
    __init__.py
    lexer.py             # SQL tokenizer
    parser.py            # recursive descent parser
    ast_nodes.py         # AST dataclasses
    binder.py            # name resolution and type checking

  types.py               # DataType enum, Value wrapper
  expression.py          # expression evaluation engine
  catalog.py             # system catalog manager

  planner/
    __init__.py
    planner.py           # AST -> logical plan tree
    optimizer.py         # rule-based optimization
    plan_nodes.py        # plan node dataclasses

  executor.py            # Volcano iterators: open/next/close

  storage/
    __init__.py
    disk_manager.py      # raw page I/O
    page.py              # slotted page implementation
    heap_file.py         # heap file (table data)
    buffer_pool.py       # page cache
    replacer.py          # LRU eviction policy
    btree.py             # B+ tree index
    index_manager.py     # index registry and lifecycle

  txn/
    __init__.py
    transaction.py       # transaction manager
    txn_context.py       # per-transaction state
    lock_manager.py      # row-level locking
    wal.py               # write-ahead log
    wal_record.py        # WAL record types
    recovery.py          # crash recovery

  utils/
    __init__.py
    tuple_serde.py       # tuple serialization/deserialization
    formatter.py         # pretty-print result tables
    errors.py            # custom exception hierarchy

data/                    # runtime directory (created on first run)
  _catalog.dat           # system catalog heap file
  users.dat              # per-table heap files
  users_idx_age.dat      # per-index B-tree files
  wal.log                # write-ahead log

tests/
  test_lexer.py
  test_parser.py
  test_expression.py
  test_catalog.py
  test_page.py
  test_heap_file.py
  test_buffer_pool.py
  test_btree.py
  test_wal.py
  test_transaction.py
  test_planner.py
  test_executor.py
  test_e2e.py            # end-to-end SQL tests
  conftest.py            # shared fixtures
```

## Error Handling Strategy

All errors inherit from a base `ToyDBError`:

```
ToyDBError
  ParseError             # syntax errors, unexpected tokens
  BindError              # unresolved names, type mismatches
  PlanError              # unsupported operations
  ExecutionError         # runtime errors during execution
  StorageError           # page corruption, disk I/O failures
  TransactionError       # deadlock timeout, constraint violation
  ProtocolError          # malformed wire messages
```

Each error carries a human-readable message and, where applicable, the source position in the SQL string.

## Concurrency Model

- One thread per TCP connection.
- Shared state protected by threading locks:
  - Buffer pool: one lock per frame (fine-grained).
  - Lock manager: one global mutex for the lock table, per-resource condition variables for waiting.
  - WAL: one mutex for appending records, one for flushing.
  - Catalog: read-write lock (multiple readers, exclusive writer).
- The GIL limits true parallelism, but the locking discipline is correct and educational -- it demonstrates how a real database would synchronize without relying on a language-level global lock.
