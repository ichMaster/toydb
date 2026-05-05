# ToyDB -- Roadmap

## Overview

ToyDB is built in 9 phases. Each phase adds exactly one major component. After every phase the system is a working prototype: you can type SQL and get correct results. Later phases replace naive implementations from earlier phases with proper subsystems.

Estimated total effort: 4000--6000 lines of Python. Each phase adds roughly 400--700 lines.

```
Phase 1  SQL parser + REPL + in-memory storage        [SQL layer]
Phase 2  Type system + expressions + catalog           [SQL layer]
Phase 3  Heap file storage (disk persistence)          [Storage layer]
Phase 4  Buffer pool manager                           [Storage layer]
Phase 5  TCP server + wire protocol                    [Infrastructure]
Phase 6  B-tree index                                  [Storage layer]
Phase 7  WAL + crash recovery                          [Durability layer]
Phase 8  Transactions                                  [Durability layer]
Phase 9  Query planner + Volcano executor              [Infrastructure]
```

---

## Phase 1: SQL Parser + REPL + In-Memory Storage

### Component
Hand-written SQL lexer and recursive descent parser, interactive REPL, naive in-memory table storage using Python dicts.

### New Modules

| Module             | Responsibility                                |
|--------------------|-----------------------------------------------|
| `repl.py`          | Read-eval-print loop with readline support    |
| `parser/lexer.py`  | Character-by-character tokenizer              |
| `parser/parser.py` | Recursive descent parser producing AST        |
| `parser/ast_nodes.py` | Frozen dataclasses for every AST node      |
| `executor_mem.py`  | Executes AST directly on in-memory tables     |
| `table_mem.py`     | Table = name + column names + list of dicts   |
| `utils/formatter.py` | Pretty-print query results as ASCII table   |
| `utils/errors.py`  | ParseError, ExecutionError base classes       |

### Key Classes

```python
@dataclass(frozen=True)
class Token:
    type: TokenType   # enum: KEYWORD, IDENT, INT_LIT, STR_LIT, OPERATOR, ...
    value: str
    position: int

@dataclass(frozen=True)
class Select:
    columns: list[Expression]    # [Star()] or [ColumnRef(...), ...]
    table: str
    where: Optional[Expression]

@dataclass(frozen=True)
class CreateTable:
    name: str
    columns: list[str]           # untyped in Phase 1

class Lexer:
    def __init__(self, sql: str): ...
    def tokenize(self) -> list[Token]: ...

class Parser:
    def __init__(self, tokens: list[Token]): ...
    def parse(self) -> Statement: ...

class MemoryExecutor:
    def __init__(self, tables: dict[str, MemoryTable]): ...
    def execute(self, stmt: Statement) -> ExecutionResult: ...
```

### Supported SQL

```sql
CREATE TABLE t (col1, col2, col3);
INSERT INTO t VALUES (1, 'hello', 42);
SELECT * FROM t;
SELECT col1, col2 FROM t WHERE col1 = 1;
DELETE FROM t WHERE col2 = 'hello';
```

Note: no types in Phase 1. All values stored as Python objects. WHERE supports only simple comparisons (=, !=, <, >, <=, >=) with AND/OR.

### Demo Session

```
toydb> CREATE TABLE users (id, name, age);
OK
toydb> INSERT INTO users VALUES (1, 'Alice', 30);
OK (1 row)
toydb> INSERT INTO users VALUES (2, 'Bob', 22);
OK (1 row)
toydb> SELECT name FROM users WHERE age > 25;
+-------+
| name  |
+-------+
| Alice |
+-------+
1 row(s)
toydb> DELETE FROM users WHERE id = 2;
OK (1 row)
toydb> SELECT * FROM users;
+----+-------+-----+
| id | name  | age |
+----+-------+-----+
| 1  | Alice | 30  |
+----+-------+-----+
1 row(s)
```

### Tests

- `test_lexer.py`: tokenize various SQL strings, verify token types and values, test edge cases (string escaping, numeric formats, unknown characters).
- `test_parser.py`: parse valid SQL and assert AST structure, verify ParseError on malformed input.
- `test_e2e.py`: execute a sequence of CREATE/INSERT/SELECT/DELETE and verify results.

### Done Criteria

- [ ] REPL starts, accepts SQL, prints results or errors.
- [ ] CREATE TABLE, INSERT, SELECT (with column list and WHERE), DELETE all work.
- [ ] Pretty-printed ASCII table output.
- [ ] ParseError with position info on bad SQL.
- [ ] All tests pass.

---

## Phase 2: Type System + Expressions + Catalog

### Component
Typed columns, full expression evaluator with arithmetic and logic, system catalog for metadata, ORDER BY, LIMIT, UPDATE, SHOW TABLES, DESCRIBE.

### New Modules

| Module           | Responsibility                                        |
|------------------|-------------------------------------------------------|
| `types.py`       | DataType enum (INT, FLOAT, VARCHAR, BOOL), Value class |
| `expression.py`  | Recursive expression evaluator                        |
| `catalog.py`     | CatalogManager: in-memory metadata registry           |

### Modified Modules

| Module               | Changes                                          |
|----------------------|--------------------------------------------------|
| `parser/ast_nodes.py` | Add ColumnDef with type, Update node, OrderBy, Limit |
| `parser/parser.py`   | Parse types in CREATE TABLE, parse UPDATE, ORDER BY, LIMIT, expressions with precedence |
| `executor_mem.py`    | Use expression evaluator for WHERE, support UPDATE, ORDER BY, LIMIT |
| `repl.py`            | Add .help, .quit, SHOW TABLES, DESCRIBE          |

### Key Classes

```python
class DataType(Enum):
    INT = "INT"
    FLOAT = "FLOAT"
    VARCHAR = "VARCHAR"
    BOOL = "BOOL"

@dataclass(frozen=True)
class ColumnDef:
    name: str
    data_type: DataType
    max_length: Optional[int] = None   # for VARCHAR
    nullable: bool = True

@dataclass(frozen=True)
class BinaryOp:
    left: Expression
    op: str            # +, -, *, /, =, !=, <, >, <=, >=, AND, OR
    right: Expression

@dataclass(frozen=True)
class UnaryOp:
    op: str            # NOT, - (negation)
    operand: Expression

class ExpressionEvaluator:
    def evaluate(self, expr: Expression, row: dict, schema: list[ColumnDef]) -> Any: ...

class CatalogManager:
    def create_table(self, name: str, columns: list[ColumnDef]) -> int: ...
    def get_table(self, name: str) -> Optional[TableMeta]: ...
    def get_columns(self, table_id: int) -> list[ColumnMeta]: ...
    def list_tables(self) -> list[TableMeta]: ...
    def drop_table(self, name: str) -> None: ...
```

### Supported SQL (additions)

```sql
CREATE TABLE products (id INT, name VARCHAR(100), price FLOAT, active BOOL);
INSERT INTO products VALUES (1, 'Widget', 29.99, true);
SELECT name, price * 1.2 AS with_tax FROM products WHERE active = true AND price > 10;
SELECT * FROM products ORDER BY price DESC LIMIT 5;
UPDATE products SET price = price * 0.9 WHERE id = 1;
SHOW TABLES;
DESCRIBE products;
```

### Expression Precedence (lowest to highest)

1. OR
2. AND
3. NOT
4. Comparisons: =, !=, <, >, <=, >=
5. Addition: +, -
6. Multiplication: *, /
7. Unary: -, NOT
8. Primary: literal, column_ref, parenthesized expression

### Demo Session

```
toydb> CREATE TABLE products (id INT, name VARCHAR(100), price FLOAT, active BOOL);
OK
toydb> INSERT INTO products VALUES (1, 'Widget', 29.99, true);
OK (1 row)
toydb> INSERT INTO products VALUES (2, 'Gadget', 49.99, true);
OK (1 row)
toydb> INSERT INTO products VALUES (3, 'Thingy', 9.99, false);
OK (1 row)
toydb> SELECT name, price * 1.2 AS with_tax FROM products WHERE active = true AND price > 20;
+--------+----------+
| name   | with_tax |
+--------+----------+
| Widget | 35.99    |
| Gadget | 59.99    |
+--------+----------+
2 row(s)
toydb> SHOW TABLES;
+----------+
| name     |
+----------+
| products |
+----------+
toydb> DESCRIBE products;
+--------+--------------+----------+
| column | type         | nullable |
+--------+--------------+----------+
| id     | INT          | YES      |
| name   | VARCHAR(100) | YES      |
| price  | FLOAT        | YES      |
| active | BOOL         | YES      |
+--------+--------------+----------+
```

### Tests

- `test_expression.py`: evaluate arithmetic, comparisons, boolean logic, NULL handling, type coercion.
- `test_catalog.py`: create/drop/list tables, column metadata.
- `test_parser.py` (extended): parse typed CREATE TABLE, UPDATE, ORDER BY, LIMIT.
- `test_e2e.py` (extended): typed inserts with validation errors, ORDER BY + LIMIT, UPDATE.

### Done Criteria

- [ ] CREATE TABLE with typed columns.
- [ ] INSERT validates types (error on type mismatch).
- [ ] Complex WHERE with AND/OR/NOT and arithmetic.
- [ ] ORDER BY (ASC/DESC) and LIMIT work.
- [ ] UPDATE with expressions (SET price = price * 0.9).
- [ ] SHOW TABLES and DESCRIBE return correct metadata.
- [ ] All tests pass.

---

## Phase 3: Heap File Storage (Disk Persistence)

### Component
Disk manager for raw page I/O, slotted page layout, heap file for table data, tuple serialization. Data survives process restart.

### New Modules

| Module                 | Responsibility                                  |
|------------------------|-------------------------------------------------|
| `storage/disk_manager.py` | read_page / write_page / allocate_page       |
| `storage/page.py`      | SlottedPage: header + slot array + tuple data   |
| `storage/heap_file.py` | HeapFile: insert, get, delete, update, scan     |
| `utils/tuple_serde.py` | Serialize/deserialize Row <-> bytes             |

### Modified Modules

| Module           | Changes                                             |
|------------------|-----------------------------------------------------|
| `executor_mem.py` | Replace in-memory dict storage with HeapFile calls |
| `catalog.py`     | Persist catalog to `data/_catalog.dat` via heap file |
| `__main__.py`    | Create `data/` directory on first run               |

### Key Classes

```python
PAGE_SIZE = 4096

class DiskManager:
    def __init__(self, data_dir: str): ...
    def read_page(self, file_id: int, page_id: int) -> bytearray: ...
    def write_page(self, file_id: int, page_id: int, data: bytes) -> None: ...
    def allocate_page(self, file_id: int) -> int: ...
    def open_file(self, filename: str) -> int: ...

class SlottedPage:
    def __init__(self, data: bytearray = None): ...
    def insert(self, tuple_data: bytes) -> int:      # returns slot_id
    def get(self, slot_id: int) -> Optional[bytes]: ...
    def delete(self, slot_id: int) -> None: ...
    def free_space(self) -> int: ...
    def slot_count(self) -> int: ...
    def to_bytes(self) -> bytes: ...

    @classmethod
    def from_bytes(cls, data: bytes) -> 'SlottedPage': ...

class HeapFile:
    def __init__(self, disk_manager: DiskManager, file_id: int): ...
    def insert_tuple(self, data: bytes) -> tuple[int, int]:  # (page_id, slot_id)
    def get_tuple(self, page_id: int, slot_id: int) -> Optional[bytes]: ...
    def delete_tuple(self, page_id: int, slot_id: int) -> None: ...
    def scan(self) -> Iterator[tuple[int, int, bytes]]:  # (page_id, slot_id, data)

class TupleSerializer:
    @staticmethod
    def serialize(values: list[Any], schema: list[ColumnDef]) -> bytes: ...
    @staticmethod
    def deserialize(data: bytes, schema: list[ColumnDef]) -> list[Any]: ...
```

### Page Layout Detail

```
Byte offset    Content
-----------    -------
0..3           page_id (uint32)
4..5           num_slots (uint16)
6..7           free_start (uint16) -- points past last slot entry
8..9           free_end (uint16) -- points to start of last tuple
10..11         flags (uint16)
12..15         page_lsn (uint32) -- reserved for Phase 6

16..           Slot array (4 bytes each):
                 slot[i].offset (uint16) -- offset of tuple from page start
                 slot[i].length (uint16) -- byte length of tuple (0 = deleted)

               [free space gap]

..4095         Tuple data (packed from end of page toward slot array)
```

### Tuple Serialization Format

```
[null_bitmap: ceil(num_columns / 8) bytes]
[column_0 data]
[column_1 data]
...

Per-type encoding:
  INT:        4 bytes, big-endian signed int (struct '>i')
  FLOAT:      8 bytes, big-endian double (struct '>d')
  VARCHAR:    2 bytes length prefix (uint16) + UTF-8 bytes
  BOOL:       1 byte (0x00 or 0x01)
  NULL:       no bytes (indicated by null bitmap bit)
```

### Demo Session

```
toydb> CREATE TABLE big (id INT, val VARCHAR(20));
OK
toydb> -- insert 1000 rows via script --
toydb> SELECT COUNT(*) FROM big;
+-------+
| count |
+-------+
| 1000  |
+-------+
toydb> .quit

$ ls -la data/
_catalog.dat    1.2K
big.dat         52K     (13 pages * 4096 bytes)

$ python -m toydb
toydb> SELECT * FROM big WHERE id = 500;
+-----+----------+
| id  | val      |
+-----+----------+
| 500 | row_500  |
+-----+----------+
1 row(s)
-- data survived restart
```

### Tests

- `test_page.py`: insert/get/delete tuples on a SlottedPage, verify free space accounting, test page full condition.
- `test_heap_file.py`: insert 1000 tuples, scan all, delete some, verify scan returns correct remaining tuples.
- `test_tuple_serde.py`: round-trip serialize/deserialize for all types including NULLs.
- `test_e2e.py` (extended): restart persistence -- insert data, create fresh executor from disk, verify data is present.

### Done Criteria

- [ ] All table data stored in `data/{table_name}.dat` as slotted pages.
- [ ] Catalog persisted in `data/_catalog.dat`.
- [ ] Data survives process restart.
- [ ] Sequential scan reads all pages from disk.
- [ ] INSERT finds a page with free space (or allocates new page).
- [ ] DELETE marks slot as tombstone.
- [ ] All tests pass.

---

## Phase 4: Buffer Pool Manager

### Component
Fixed-size page cache between the executor and disk. LRU eviction policy. Pin/unpin protocol.

### New Modules

| Module                  | Responsibility                              |
|-------------------------|---------------------------------------------|
| `storage/buffer_pool.py` | BufferPoolManager: fetch, unpin, flush     |
| `storage/replacer.py`   | LRUReplacer: eviction ordering             |

### Modified Modules

| Module              | Changes                                        |
|---------------------|------------------------------------------------|
| `storage/heap_file.py` | Replace direct disk I/O with buffer pool calls |
| `repl.py`           | Add `.buffer_stats` and `.flush` commands       |

### Key Classes

```python
@dataclass
class Frame:
    page_id: Optional[int] = None
    file_id: Optional[int] = None
    data: bytearray = field(default_factory=lambda: bytearray(PAGE_SIZE))
    pin_count: int = 0
    is_dirty: bool = False

class LRUReplacer:
    def __init__(self, capacity: int): ...
    def record_access(self, frame_id: int) -> None: ...
    def set_evictable(self, frame_id: int, evictable: bool) -> None: ...
    def evict(self) -> Optional[int]: ...
    def size(self) -> int: ...   # number of evictable frames

class BufferPoolManager:
    def __init__(self, pool_size: int, disk_manager: DiskManager): ...
    def fetch_page(self, file_id: int, page_id: int) -> SlottedPage: ...
    def unpin_page(self, file_id: int, page_id: int, is_dirty: bool) -> None: ...
    def new_page(self, file_id: int) -> tuple[int, SlottedPage]: ...
    def flush_page(self, file_id: int, page_id: int) -> None: ...
    def flush_all(self) -> None: ...

    # Stats
    def hit_count(self) -> int: ...
    def miss_count(self) -> int: ...
    def hit_ratio(self) -> float: ...
```

### Pin/Unpin Protocol

1. Caller requests a page via `fetch_page(file_id, page_id)`.
2. Buffer pool checks `page_table`. If found: increment pin_count, return page.
3. If not found: call `replacer.evict()` to find a frame. If the evicted frame is dirty, flush it to disk first. Read the requested page from disk into the frame. Set pin_count=1.
4. Caller uses the page data.
5. Caller calls `unpin_page(file_id, page_id, is_dirty)`. Decrements pin_count. If dirty, marks frame dirty. If pin_count reaches 0, frame becomes evictable.

### Configuration

```python
# Default: 64 frames = 256 KB cache
BUFFER_POOL_SIZE = int(os.environ.get("TOYDB_POOL_SIZE", "64"))
```

### Demo Session

```
toydb> -- after inserting and querying data --
toydb> .buffer_stats
Buffer pool: 64 frames
  Used: 42 / 64
  Dirty: 7
  Hit ratio: 87.3% (4521 hits / 5178 total)
toydb> .flush
Flushed 7 dirty page(s) to disk.
toydb> .buffer_stats
Buffer pool: 64 frames
  Used: 42 / 64
  Dirty: 0
  Hit ratio: 87.5% (4528 hits / 5178 total)
```

### Tests

- `test_buffer_pool.py`:
  - Fetch a page, verify it returns correct data.
  - Fetch more pages than pool size, verify eviction happens (LRU frame is evicted).
  - Pin a page, verify it is not evicted even when pool is full.
  - Mark a page dirty, evict it, verify it was flushed to disk.
  - Test hit/miss counting.
- `test_replacer.py`: LRU ordering -- access A, B, C, A. Evict should return B (least recent).

### Done Criteria

- [ ] All heap file I/O goes through the buffer pool.
- [ ] LRU eviction works correctly under memory pressure.
- [ ] Dirty pages are flushed before eviction.
- [ ] `.buffer_stats` shows accurate hit ratio.
- [ ] `.flush` writes all dirty pages to disk.
- [ ] Existing SQL operations work identically (transparent caching layer).
- [ ] All tests pass.

---

## Phase 5: TCP Server + Wire Protocol

### Component
TCP network server. Binary wire protocol. Per-connection sessions. Python client library.

### New Modules

| Module        | Responsibility                                    |
|---------------|---------------------------------------------------|
| `server.py`   | TCP listener, thread-per-connection               |
| `protocol.py` | Wire protocol: encode/decode binary frames        |
| `session.py`  | Per-connection state: current txn, autocommit     |
| `client.py`   | ToyDBClient: connect, execute, fetchall, close    |

### Modified Modules

| Module        | Changes                                            |
|---------------|----------------------------------------------------|
| `__main__.py` | Add `--mode server --port 9876` CLI option         |
| `repl.py`     | Refactor to share execution pipeline with server   |

### Wire Protocol

```
Frame layout:
  [payload_length: 4 bytes, uint32, big-endian]
  [message_type: 1 byte]
  [payload: payload_length bytes]

Message types:
  0x01  QUERY         client -> server    UTF-8 SQL string
  0x02  ROW_DATA      server -> client    column_count(2B) + [col_type(1B) + col_data(varlen)]...
  0x03  OK            server -> client    affected_rows(4B)
  0x04  ERROR         server -> client    error_code(2B) + UTF-8 message
  0x05  READY         server -> client    empty (ready for next query)
  0x06  COLUMN_DESC   server -> client    column_count(2B) + [name_len(2B) + name + type(1B)]...

Query result sequence:
  Server receives QUERY ->
    If SELECT: send COLUMN_DESC, then ROW_DATA per row, then READY
    If INSERT/UPDATE/DELETE: send OK with row count, then READY
    If error: send ERROR, then READY
```

### Key Classes

```python
class ToyDBServer:
    def __init__(self, host: str, port: int, engine: Engine): ...
    def start(self) -> None:     # blocking, accepts connections
    def stop(self) -> None: ...

class Session:
    def __init__(self, conn: socket, engine: Engine): ...
    def handle(self) -> None:    # read queries, execute, send results
    @property
    def current_txn(self) -> Optional[TxnContext]: ...

class Protocol:
    @staticmethod
    def read_frame(conn: socket) -> tuple[int, bytes]:  # (msg_type, payload)
    @staticmethod
    def write_frame(conn: socket, msg_type: int, payload: bytes) -> None: ...
    @staticmethod
    def encode_row(row: tuple, schema: list[ColumnDef]) -> bytes: ...
    @staticmethod
    def decode_row(data: bytes, schema: list[ColumnDef]) -> tuple: ...

class ToyDBClient:
    def __init__(self, host: str = "localhost", port: int = 9876): ...
    def connect(self) -> None: ...
    def execute(self, sql: str) -> list[tuple]: ...
    def close(self) -> None: ...
```

### Server Architecture

```
Main thread:
  socket.bind((host, port))
  socket.listen()
  while running:
    conn, addr = socket.accept()
    thread = Thread(target=Session(conn, engine).handle)
    thread.start()

Session.handle():
  send READY
  while True:
    msg_type, payload = Protocol.read_frame(conn)
    if msg_type == QUERY:
      sql = payload.decode('utf-8')
      try:
        result = engine.execute(sql, session=self)
        send result (COLUMN_DESC + ROW_DATA* or OK)
      except ToyDBError as e:
        send ERROR
      send READY
```

### Demo Session

Terminal 1 (server):
```
$ python -m toydb --mode server --port 9876
[ToyDB] Server listening on 0.0.0.0:9876
[ToyDB] Connection from 127.0.0.1:54321
[ToyDB] Connection from 127.0.0.1:54322
```

Terminal 2 (client):
```python
from toydb.client import ToyDBClient

db = ToyDBClient("localhost", 9876)
db.connect()
db.execute("CREATE TABLE test (id INT, val VARCHAR(50))")
db.execute("INSERT INTO test VALUES (1, 'hello')")
db.execute("INSERT INTO test VALUES (2, 'world')")
rows = db.execute("SELECT * FROM test ORDER BY id")
for row in rows:
    print(row)
# (1, 'hello')
# (2, 'world')
db.close()
```

Terminal 3 (REPL over TCP):
```
$ python -m toydb --mode client --host localhost --port 9876
toydb(remote)> SELECT * FROM test;
+----+---------+
| id | val     |
+----+---------+
| 1  | hello   |
| 2  | world   |
+----+---------+
```

### Tests

- `test_protocol.py`: encode/decode round-trip for each message type.
- `test_server.py`:
  - Start server in background thread, connect with client, execute CREATE/INSERT/SELECT.
  - Multiple concurrent clients inserting and reading.
  - Client disconnects mid-query: server stays alive.
  - Malformed frame: server sends ERROR and stays alive.
- `test_client.py`: connect, execute, fetchall, close lifecycle.
- `test_e2e.py` (extended): full end-to-end test through TCP: create table, insert, query, verify results.

### Done Criteria

- [ ] Server starts and listens on configured port.
- [ ] Client library connects, sends queries, receives results.
- [ ] Multiple concurrent connections work.
- [ ] Graceful handling of client disconnect.
- [ ] Error messages sent back to client with error codes.
- [ ] REPL mode still works (--mode repl).
- [ ] All tests pass.

---

## Phase 6: B-Tree Index

### Component
B+ tree index stored on disk pages via the buffer pool. CREATE INDEX command. Index scan operator for point and range queries.

### New Modules

| Module                   | Responsibility                                |
|--------------------------|-----------------------------------------------|
| `storage/btree.py`       | B+ tree: search, insert, delete, range_scan  |
| `storage/btree_page.py`  | Internal and leaf node page layouts           |
| `storage/index_manager.py` | Index lifecycle: create, drop, lookup       |
| `executor_mem.py` -> `scan.py` | SeqScan and IndexScan abstractions     |

### Modified Modules

| Module           | Changes                                              |
|------------------|------------------------------------------------------|
| `catalog.py`     | Store index metadata in sys_indexes                  |
| `parser/parser.py` | Parse CREATE INDEX syntax                          |
| `parser/ast_nodes.py` | Add CreateIndex AST node                        |
| `executor_mem.py` | Choose IndexScan when index is available for WHERE  |

### Key Classes

```python
@dataclass
class BTreeNode:
    is_leaf: bool
    num_keys: int
    keys: list[Any]

@dataclass
class InternalNode(BTreeNode):
    child_page_ids: list[int]      # len = num_keys + 1

@dataclass
class LeafNode(BTreeNode):
    next_leaf: Optional[int]       # page_id of next leaf (for range scan)
    row_pointers: list[tuple[int, int]]  # [(page_id, slot_id), ...]

class BTree:
    def __init__(self, buffer_pool: BufferPoolManager, file_id: int, root_page_id: int): ...
    def search(self, key: Any) -> Optional[tuple[int, int]]: ...
    def range_scan(self, low: Any, high: Any) -> Iterator[tuple[int, int]]: ...
    def insert(self, key: Any, page_id: int, slot_id: int) -> None: ...
    def delete(self, key: Any) -> None: ...

class IndexManager:
    def __init__(self, catalog: CatalogManager, buffer_pool: BufferPoolManager): ...
    def create_index(self, name: str, table_name: str, column_name: str) -> None: ...
    def get_index(self, table_name: str, column_name: str) -> Optional[BTree]: ...
    def drop_index(self, name: str) -> None: ...
```

### B+ Tree Node Layout on Page

```
Internal node (4096 bytes):
  [is_leaf: 1 byte = 0x00]
  [num_keys: 2 bytes, uint16]
  [keys: num_keys * key_size bytes]
  [child_page_ids: (num_keys + 1) * 4 bytes]

Leaf node (4096 bytes):
  [is_leaf: 1 byte = 0x01]
  [num_keys: 2 bytes, uint16]
  [next_leaf: 4 bytes, uint32 (0xFFFFFFFF = no next)]
  [keys: num_keys * key_size bytes]
  [row_pointers: num_keys * 6 bytes (4 page_id + 2 slot_id)]
```

### Scan Selection Logic (naive planner)

```python
def choose_scan(table: str, where: Optional[Expression], catalog, index_manager):
    if where is None:
        return SeqScan(table)
    # Check if WHERE is "column op literal" and index exists
    if isinstance(where, BinaryOp) and isinstance(where.left, ColumnRef):
        idx = index_manager.get_index(table, where.left.name)
        if idx and where.op in ('=', '<', '>', '<=', '>='):
            return IndexScan(idx, where.op, where.right.value)
    return SeqScan(table)   # fallback
```

### Supported SQL (additions)

```sql
CREATE INDEX idx_users_age ON users (age);
SELECT * FROM users WHERE age = 30;        -- IndexScan (point)
SELECT * FROM users WHERE age > 20;        -- IndexScan (range)
SELECT * FROM users WHERE name = 'Alice';  -- SeqScan (no index on name)
```

### Demo Session

```
toydb> CREATE TABLE users (id INT, name VARCHAR(50), age INT);
toydb> -- insert 10000 rows --
toydb> SELECT * FROM users WHERE age = 30;
-- SeqScan: reads all 250 pages
-- Time: 45ms
toydb> CREATE INDEX idx_age ON users (age);
OK (index built from 10000 rows)
toydb> SELECT * FROM users WHERE age = 30;
-- IndexScan: reads 3 pages (root -> internal -> leaf) + 1 data page
-- Time: 2ms
```

### Tests

- `test_btree.py`:
  - Insert 1000 sequential keys, search each one.
  - Insert 1000 random keys, search each one.
  - Range scan: insert keys 1..100, range_scan(25, 75) returns exactly 51 entries.
  - Page split: insert enough keys to trigger a leaf split, verify tree remains correct.
  - Delete: delete keys, verify search returns None.
- `test_e2e.py` (extended): CREATE INDEX, verify SELECT uses IndexScan, verify correctness of results matches SeqScan.

### Done Criteria

- [ ] CREATE INDEX builds a B+ tree from existing table data.
- [ ] Point lookup (WHERE col = val) uses index when available.
- [ ] Range scan (WHERE col > val) follows leaf chain.
- [ ] Leaf splits work correctly when a node overflows.
- [ ] Index maintained on INSERT (new index entries added).
- [ ] Index maintained on DELETE (index entries removed).
- [ ] SeqScan still works as fallback for non-indexed queries.
- [ ] All tests pass.

---

## Phase 7: WAL + Crash Recovery

### Component
Write-ahead log for durability. Checkpoint mechanism. Redo recovery on startup after crash.

### New Modules

| Module              | Responsibility                                    |
|---------------------|---------------------------------------------------|
| `txn/wal.py`        | WALManager: append records, flush, read back      |
| `txn/wal_record.py` | WAL record dataclasses and serialization          |
| `txn/recovery.py`   | RecoveryManager: replay WAL from last checkpoint  |

### Modified Modules

| Module                  | Changes                                       |
|-------------------------|-----------------------------------------------|
| `storage/buffer_pool.py` | Check page_lsn before flushing dirty pages  |
| `storage/page.py`       | Read/write page_lsn field in header           |
| `executor_mem.py`       | Generate WAL records before modifying pages   |
| `__main__.py`           | Run recovery on startup before accepting SQL  |

### Key Classes

```python
@dataclass(frozen=True)
class WALRecord:
    lsn: int
    txn_id: int
    record_type: WALRecordType
    table_id: int
    page_id: int
    payload: bytes

class WALRecordType(Enum):
    INSERT = 0x01
    DELETE = 0x02
    UPDATE = 0x03
    COMMIT = 0x10
    ABORT = 0x11
    CHECKPOINT = 0x20

class WALManager:
    def __init__(self, wal_path: str): ...
    def append(self, record: WALRecord) -> int:  # returns LSN
    def flush(self) -> None:                     # fsync to disk
    def get_flushed_lsn(self) -> int: ...
    def read_from(self, start_lsn: int) -> Iterator[WALRecord]: ...
    def write_checkpoint(self, dirty_pages: list[tuple[int, int]]) -> None: ...
    def find_last_checkpoint(self) -> Optional[int]:  # returns LSN

class RecoveryManager:
    def __init__(self, wal: WALManager, buffer_pool: BufferPoolManager, catalog: CatalogManager): ...
    def recover(self) -> RecoveryStats: ...
```

### WAL Record Binary Format

```
[record_length: 4 bytes, uint32]        -- total length including this field
[lsn: 8 bytes, uint64]                  -- monotonically increasing
[txn_id: 4 bytes, uint32]               -- 0 for system operations
[record_type: 1 byte]                   -- see WALRecordType enum
[table_id: 4 bytes, uint32]
[page_id: 4 bytes, uint32]
[payload_length: 4 bytes, uint32]
[payload: variable length bytes]
[checksum: 4 bytes, CRC32 of everything above]
```

### WAL Protocol

1. Before modifying any data page: append WAL record with before/after images.
2. Mark page as dirty in buffer pool, set page_lsn = record's LSN.
3. Buffer pool flush rule: never flush a page whose page_lsn > flushed_wal_lsn. Force WAL flush first.
4. On COMMIT (Phase 7): force WAL flush, then return success.

### Checkpoint Protocol

1. Write CHECKPOINT record containing list of all dirty (file_id, page_id, page_lsn) in the buffer pool.
2. Flush all dirty pages to disk.
3. Flush WAL.
4. Future: truncate WAL segments before the checkpoint.

### Recovery Protocol (redo-only in Phase 6)

1. Find last CHECKPOINT record in WAL.
2. Read all records after the checkpoint LSN.
3. For each INSERT/UPDATE/DELETE record: fetch the target page. If page_lsn < record.lsn, apply the change (redo). Otherwise skip (already on disk).
4. Flush all redone pages.
5. Write a fresh checkpoint.

### Demo Session

```
toydb> INSERT INTO users VALUES (999, 'CrashTest', 99);
OK (1 row)

$ kill -9 $(pgrep -f toydb)

$ python -m toydb
[RECOVERY] Last checkpoint at LSN 4780
[RECOVERY] Replaying 3 WAL record(s)...
[RECOVERY]   Redo INSERT on users page 47 (page_lsn 4779 < record_lsn 4783)
[RECOVERY] Recovery complete. 1 page(s) redone.
toydb> SELECT * FROM users WHERE id = 999;
+-----+-----------+-----+
| id  | name      | age |
+-----+-----------+-----+
| 999 | CrashTest | 99  |
+-----+-----------+-----+
```

### Tests

- `test_wal.py`:
  - Append records, read them back, verify LSN ordering.
  - Write checkpoint, find_last_checkpoint returns correct LSN.
  - Verify CRC32 integrity check catches corrupted records.
- `test_recovery.py`:
  - Insert rows, simulate crash (don't flush buffer pool), run recovery, verify data present.
  - Insert rows + checkpoint + more inserts + crash, verify recovery replays only post-checkpoint records.
  - Verify idempotent redo: run recovery twice, results are identical.

### Done Criteria

- [ ] Every INSERT/UPDATE/DELETE generates a WAL record before modifying pages.
- [ ] Buffer pool respects WAL flush ordering (no dirty page flushed ahead of its WAL record).
- [ ] Checkpoint writes dirty page list and flushes everything.
- [ ] Recovery on startup replays WAL and restores all committed data.
- [ ] Redo is idempotent (safe to replay same record twice).
- [ ] `.checkpoint` REPL command triggers manual checkpoint.
- [ ] All tests pass.

---

## Phase 8: Transactions

### Component
Transaction manager with BEGIN/COMMIT/ROLLBACK. Row-level locking with 2PL. Undo support for ROLLBACK using WAL before-images.

### New Modules

| Module                 | Responsibility                                |
|------------------------|-----------------------------------------------|
| `txn/transaction.py`   | TransactionManager: begin, commit, abort     |
| `txn/txn_context.py`   | TxnContext: per-transaction state             |
| `txn/lock_manager.py`  | LockManager: shared/exclusive row-level locks |

### Modified Modules

| Module            | Changes                                                |
|-------------------|--------------------------------------------------------|
| `txn/wal.py`      | WAL records now carry txn_id. Add COMMIT/ABORT types.  |
| `txn/recovery.py` | Add undo phase: roll back uncommitted transactions.    |
| `executor_mem.py` | Wrap operations in transaction context. Acquire locks. |
| `parser/parser.py` | Parse BEGIN, COMMIT, ROLLBACK.                        |
| `repl.py`         | Track current transaction in REPL session.             |

### Key Classes

```python
@dataclass
class TxnContext:
    txn_id: int
    status: TxnStatus         # ACTIVE, COMMITTED, ABORTED
    acquired_locks: list[LockRequest]
    wal_records: list[int]    # LSNs for undo
    start_lsn: int

class TxnStatus(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"

class TransactionManager:
    def __init__(self, wal: WALManager, lock_manager: LockManager): ...
    def begin(self) -> TxnContext: ...
    def commit(self, txn: TxnContext) -> None: ...
    def abort(self, txn: TxnContext) -> None: ...

class LockMode(Enum):
    SHARED = "SHARED"
    EXCLUSIVE = "EXCLUSIVE"

@dataclass
class LockRequest:
    resource: tuple[int, int, int]   # (table_id, page_id, slot_id)
    mode: LockMode
    txn_id: int

class LockManager:
    def __init__(self, timeout_seconds: float = 5.0): ...
    def acquire(self, resource: tuple, mode: LockMode, txn_id: int) -> bool: ...
    def release_all(self, txn_id: int) -> None: ...
```

### 2PL Protocol

1. Growing phase: transaction acquires locks as it reads (SHARED) and writes (EXCLUSIVE).
2. No lock is released until commit/abort.
3. On COMMIT: write COMMIT record to WAL, flush WAL, release all locks.
4. On ABORT: undo changes by reading WAL records in reverse and applying before-images, write ABORT record, release all locks.

### Deadlock Handling

Simple timeout approach: `LockManager.acquire()` blocks on a `threading.Condition` with a timeout. If timeout expires, the requesting transaction is aborted and `TransactionError` raised.

### Autocommit Mode

When no explicit BEGIN is active, each statement is wrapped in an implicit transaction: auto-begin before execution, auto-commit after success, auto-abort on error.

### Recovery Enhancement (undo phase)

After redo phase, scan for transactions that have no COMMIT or ABORT record. For each:
1. Read their WAL records in reverse order.
2. Apply before-images to undo changes.
3. Write ABORT record.

### Demo Session

```
toydb> BEGIN;
OK (txn 42)
toydb> UPDATE accounts SET balance = balance - 100 WHERE id = 1;
OK (1 row)
toydb> UPDATE accounts SET balance = balance + 100 WHERE id = 2;
OK (1 row)
toydb> COMMIT;
OK (txn 42 committed)

toydb> BEGIN;
OK (txn 43)
toydb> DELETE FROM orders WHERE status = 'cancelled';
OK (17 rows)
toydb> ROLLBACK;
OK (txn 43 rolled back, 17 rows restored)
toydb> SELECT COUNT(*) FROM orders WHERE status = 'cancelled';
+-------+
| count |
+-------+
| 17    |
+-------+
```

### Concurrency Demo (two threads)

```
[T1] BEGIN;
[T1] UPDATE accounts SET balance = 0 WHERE id = 1;  -- acquires EXCLUSIVE lock
[T2] BEGIN;
[T2] SELECT * FROM accounts WHERE id = 1;           -- requests SHARED lock, BLOCKED
[T1] COMMIT;                                         -- releases locks
[T2] -- unblocked, reads balance = 0
[T2] COMMIT;
```

### Tests

- `test_transaction.py`:
  - BEGIN + INSERT + COMMIT: data visible after commit.
  - BEGIN + INSERT + ROLLBACK: data not visible after rollback.
  - Autocommit: single INSERT without BEGIN is committed.
  - Abort on error: INSERT with type mismatch inside transaction rolls back the entire transaction.
- `test_lock_manager.py`:
  - SHARED + SHARED: compatible, both acquire.
  - SHARED + EXCLUSIVE: conflict, second waits.
  - EXCLUSIVE + EXCLUSIVE: conflict, second waits.
  - Deadlock timeout: two transactions lock resources in opposite order, one aborts.
- `test_recovery.py` (extended): crash with uncommitted transaction, verify undo on recovery.

### Done Criteria

- [ ] BEGIN / COMMIT / ROLLBACK parsed and executed.
- [ ] COMMIT flushes WAL and releases locks.
- [ ] ROLLBACK undoes changes using WAL before-images.
- [ ] Row-level SHARED/EXCLUSIVE locks work correctly.
- [ ] Lock conflicts cause blocking (not errors).
- [ ] Deadlock detected via timeout, one transaction aborted.
- [ ] Recovery handles uncommitted transactions (undo phase).
- [ ] Autocommit wraps single statements.
- [ ] All tests pass.

---

## Phase 9: Query Planner + Volcano Executor

### Component
Logical plan tree from AST. Rule-based optimizer. Volcano iterator execution model. JOIN support. EXPLAIN command.

### New Modules

| Module               | Responsibility                                   |
|----------------------|--------------------------------------------------|
| `planner/planner.py` | AST -> logical plan tree                        |
| `planner/optimizer.py` | Rule-based optimization passes                |
| `planner/plan_nodes.py` | Plan node dataclasses                        |
| `executor.py`        | Volcano iterators replacing executor_mem.py      |

### Removed Modules

| Module             | Replaced By                          |
|--------------------|--------------------------------------|
| `executor_mem.py`  | `executor.py` (Volcano iterators)    |

### Key Classes

```python
# Plan nodes (frozen dataclasses)
@dataclass(frozen=True)
class SeqScanNode:
    table_id: int
    table_name: str

@dataclass(frozen=True)
class IndexScanNode:
    table_id: int
    index_id: int
    key_range: tuple[Optional[Any], Optional[Any]]  # (low, high), None = unbounded

@dataclass(frozen=True)
class FilterNode:
    child: PlanNode
    predicate: Expression

@dataclass(frozen=True)
class ProjectNode:
    child: PlanNode
    columns: list[Expression]
    aliases: list[Optional[str]]

@dataclass(frozen=True)
class SortNode:
    child: PlanNode
    key: Expression
    descending: bool

@dataclass(frozen=True)
class LimitNode:
    child: PlanNode
    count: int

@dataclass(frozen=True)
class NestedLoopJoinNode:
    left: PlanNode
    right: PlanNode
    condition: Expression
    join_type: str   # "INNER" for now

@dataclass(frozen=True)
class AggregateNode:
    child: PlanNode
    group_by: list[Expression]
    aggregates: list[AggregateExpr]   # COUNT, SUM, AVG, MIN, MAX

# Executor interface
class Executor(ABC):
    @abstractmethod
    def open(self) -> None: ...
    @abstractmethod
    def next(self) -> Optional[tuple]: ...
    @abstractmethod
    def close(self) -> None: ...

# Optimizer rules
def predicate_pushdown(plan: PlanNode) -> PlanNode: ...
def index_selection(plan: PlanNode, catalog: CatalogManager) -> PlanNode: ...
def projection_pruning(plan: PlanNode) -> PlanNode: ...
```

### Optimizer Rules (applied in order)

1. **Predicate pushdown**: if a FilterNode sits above a JoinNode and the predicate references columns from only one side, push the filter below the join to that side. Reduces the number of rows entering the join.

2. **Index selection**: if a FilterNode sits directly above a SeqScanNode and the predicate is a simple comparison on an indexed column, replace both with an IndexScanNode.

3. **Projection pruning**: walk the plan top-down, collect which columns are actually referenced by upstream nodes. Remove unreferenced columns from scan output.

### EXPLAIN Output

```
toydb> EXPLAIN SELECT u.name, o.total
  FROM users u JOIN orders o ON u.id = o.user_id
  WHERE o.total > 100
  ORDER BY o.total DESC LIMIT 10;

Limit(count=10)
  Sort(key=o.total, desc=true)
    Project(columns=[u.name, o.total])
      NestedLoopJoin(on: u.id = o.user_id)
        SeqScan(table=users)
        Filter(predicate: o.total > 100)
          IndexScan(table=orders, index=idx_total, range=(100, +inf))
```

### Supported SQL (additions)

```sql
SELECT u.name, o.total
  FROM users u
  JOIN orders o ON u.id = o.user_id
  WHERE o.total > 100
  ORDER BY o.total DESC
  LIMIT 10;

SELECT department, COUNT(*), AVG(salary)
  FROM employees
  GROUP BY department;

EXPLAIN SELECT * FROM users WHERE age > 30;
```

### Demo Session

```
toydb> CREATE TABLE users (id INT, name VARCHAR(50));
toydb> CREATE TABLE orders (id INT, user_id INT, total FLOAT);
toydb> -- insert data --
toydb> CREATE INDEX idx_total ON orders (total);
toydb> EXPLAIN SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.total > 100;
NestedLoopJoin(on: u.id = o.user_id)
  SeqScan(table=users)
  IndexScan(table=orders, index=idx_total, range=(100, +inf))
toydb> SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.total > 100 ORDER BY o.total DESC LIMIT 3;
+-------+--------+
| name  | total  |
+-------+--------+
| Alice | 299.99 |
| Bob   | 199.50 |
| Alice | 150.00 |
+-------+--------+
3 row(s)
```

### Tests

- `test_planner.py`: verify AST -> plan tree conversion for SELECT, JOIN, ORDER BY, GROUP BY.
- `test_optimizer.py`:
  - Predicate pushdown: filter above join moves below.
  - Index selection: SeqScan + Filter replaced by IndexScan.
  - Projection pruning: unreferenced columns removed.
- `test_executor.py`:
  - SeqScanExecutor returns all rows.
  - FilterExecutor filters correctly.
  - NestedLoopJoinExecutor produces correct join results.
  - SortExecutor sorts correctly.
  - LimitExecutor stops after N rows.
- `test_e2e.py` (extended): multi-table JOIN queries, GROUP BY with aggregates, EXPLAIN output.

### Done Criteria

- [ ] All SELECT/INSERT/UPDATE/DELETE use the Volcano executor pipeline.
- [ ] `executor_mem.py` removed; `executor.py` is the single execution path.
- [ ] JOIN works for two tables with ON condition.
- [ ] GROUP BY with COUNT, SUM, AVG, MIN, MAX.
- [ ] EXPLAIN prints the plan tree.
- [ ] Optimizer applies predicate pushdown and index selection.
- [ ] All tests pass.

## Summary: What Works After Each Phase

| Phase | You Can Do This                                              |
|-------|--------------------------------------------------------------|
| 1     | CREATE TABLE, INSERT, SELECT with WHERE, DELETE via REPL     |
| 2     | Typed columns, complex expressions, ORDER BY, LIMIT, UPDATE |
| 3     | All of the above, and data survives restart                  |
| 4     | All of the above, with transparent page caching              |
| 5     | Connect from another process over TCP                        |
| 6     | CREATE INDEX, fast point and range queries                   |
| 7     | All of the above, survives kill -9 (crash recovery)          |
| 8     | BEGIN/COMMIT/ROLLBACK, concurrent access with locking        |
| 9     | JOINs, GROUP BY, EXPLAIN, optimized query plans              |

## Dependency Graph

```
Phase 1 (parser + REPL)
  |
  v
Phase 2 (types + catalog)
  |
  v
Phase 3 (heap files)
  |
  v
Phase 4 (buffer pool)
  |
  v
Phase 5 (TCP server) --------> Phase 6 (B-tree) ----+
                                                      |
                                                      v
                                Phase 7 (WAL) ------> Phase 8 (transactions)
                                                       |
                                                       v
                                                 Phase 9 (planner)
```

Phases must be done in order 1 through 9. Each phase depends on all previous phases being complete.
