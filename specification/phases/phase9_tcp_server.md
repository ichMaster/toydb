# Phase 9: TCP Server + Wire Protocol

## Goal
TCP network server. Binary wire protocol. Per-connection sessions. Python client library.

## Modules to Create

| Module             | Responsibility                                  |
|--------------------|-------------------------------------------------|
| `toydb/server.py`  | TCP listener, thread-per-connection             |
| `toydb/protocol.py` | Wire protocol: encode/decode binary frames    |
| `toydb/session.py` | Per-connection state: current txn, autocommit   |
| `toydb/client.py`  | ToyDBClient: connect, execute, fetchall, close  |

## Modules to Modify

| Module            | Changes                                          |
|-------------------|--------------------------------------------------|
| `toydb/__main__.py` | Add `--mode server --port 9876` and `--mode client` CLI options |
| `toydb/repl.py`   | Refactor to share execution pipeline with server |

## Tasks

### 1. Wire protocol (`protocol.py`)
- [ ] Define message type constants:
  - 0x01 QUERY (client -> server): UTF-8 SQL string
  - 0x02 ROW_DATA (server -> client): serialized tuple
  - 0x03 OK (server -> client): affected row count (4B)
  - 0x04 ERROR (server -> client): error code (2B) + UTF-8 message
  - 0x05 READY (server -> client): empty (ready for next query)
  - 0x06 COLUMN_DESC (server -> client): column names and types
- [ ] Frame layout: `[payload_length: 4B uint32 big-endian][message_type: 1B][payload]`
- [ ] Implement `Protocol` class with static methods:
  - `read_frame(conn: socket) -> tuple[int, bytes]` -- read msg_type and payload
  - `write_frame(conn: socket, msg_type: int, payload: bytes) -> None`
  - `encode_row(row: tuple, schema: list[ColumnDef]) -> bytes`
  - `decode_row(data: bytes, schema: list[ColumnDef]) -> tuple`
  - `encode_column_desc(columns: list[ColumnDef]) -> bytes`
  - `decode_column_desc(data: bytes) -> list[ColumnDef]`
- [ ] Handle partial reads (TCP may fragment frames)
- [ ] Handle connection reset gracefully

### 2. Session (`session.py`)
- [ ] Implement `Session` class
- [ ] `__init__(self, conn: socket, engine: Engine)`
- [ ] Hold per-connection state:
  - Current transaction context (if any)
  - Autocommit flag
  - Default database
- [ ] `handle() -> None`:
  - Send READY
  - Loop: read QUERY frame, execute SQL, send results, send READY
  - On SELECT: send COLUMN_DESC, then ROW_DATA per row, then READY
  - On INSERT/UPDATE/DELETE: send OK with row count, then READY
  - On error: send ERROR, then READY
  - On disconnect: abort open transaction, clean up

### 3. TCP server (`server.py`)
- [ ] Implement `ToyDBServer` class
- [ ] `__init__(self, host: str, port: int, engine: Engine)`
- [ ] `start() -> None`:
  - `socket.bind((host, port))`
  - `socket.listen()`
  - Accept connections in a loop
  - Spawn one thread per connection: `Thread(target=Session(conn, engine).handle)`
- [ ] `stop() -> None` -- signal shutdown, close listener socket
- [ ] Log connection events: new connection, disconnect
- [ ] Handle socket errors without crashing the server

### 4. Client library (`client.py`)
- [ ] Implement `ToyDBClient` class
- [ ] `__init__(self, host: str = "localhost", port: int = 9876)`
- [ ] `connect() -> None` -- establish TCP connection, wait for READY
- [ ] `execute(sql: str) -> list[tuple]`:
  - Send QUERY frame
  - Read response frames until READY
  - If COLUMN_DESC + ROW_DATA: collect rows into list
  - If OK: return empty list (affected count available as attribute)
  - If ERROR: raise `ToyDBError` with server error message
- [ ] `close() -> None` -- close TCP connection
- [ ] Context manager support (`__enter__`/`__exit__`)

### 5. CLI modes (`__main__.py`)
- [ ] `--mode repl` (default): local REPL with direct engine access
- [ ] `--mode server --port 9876`: start TCP server
- [ ] `--mode client --host localhost --port 9876`: REPL that connects to server via ToyDBClient
- [ ] Parse CLI arguments with argparse

### 6. REPL refactor (`repl.py`)
- [ ] Extract execution pipeline so both REPL and server share the same code path
- [ ] REPL in client mode: send SQL via ToyDBClient, display results
- [ ] REPL in local mode: execute directly as before

### 7. Concurrency safety
- [ ] Shared state protected by threading locks:
  - Buffer pool: one lock per frame (fine-grained)
  - Lock manager: one global mutex for lock table, per-resource condition variables
  - WAL: one mutex for appending, one for flushing
  - Catalog: read-write lock (multiple readers, exclusive writer)
- [ ] Verify existing locks are correct for multi-connection access
- [ ] Handle client disconnect mid-transaction: abort open transaction, release locks

### 8. Tests
- [ ] `tests/test_protocol.py`: encode/decode round-trip for each message type
- [ ] `tests/test_server.py`:
  - Start server in background thread, connect with client, execute CREATE/INSERT/SELECT
  - Multiple concurrent clients inserting and reading
  - Client disconnects mid-transaction: server aborts the transaction
  - Malformed frame: server sends ERROR and stays alive
- [ ] `tests/test_client.py`: connect, execute, fetchall, close lifecycle
- [ ] `tests/test_e2e.py` (extended): full end-to-end through TCP: create table, insert, index, query, transaction

## Wire Protocol Sequences

```
SELECT query:
  Client:  QUERY("SELECT * FROM users")
  Server:  COLUMN_DESC(id:INT, name:VARCHAR, age:INT)
  Server:  ROW_DATA(1, 'Alice', 30)
  Server:  ROW_DATA(2, 'Bob', 22)
  Server:  READY

INSERT/UPDATE/DELETE:
  Client:  QUERY("INSERT INTO users VALUES (3, 'Carol', 28)")
  Server:  OK(affected_rows=1)
  Server:  READY

Error:
  Client:  QUERY("SELCT * FORM users")
  Server:  ERROR(code=1001, "Parse error at position 0: unexpected 'SELCT'")
  Server:  READY
```

## Done Criteria
- [ ] Server starts and listens on configured port
- [ ] Client library connects, sends queries, receives results
- [ ] Multiple concurrent connections work
- [ ] Transactions work across TCP (BEGIN in one query, COMMIT in another)
- [ ] Graceful handling of client disconnect (abort open transaction)
- [ ] Error messages sent back to client with error codes
- [ ] REPL mode still works (--mode repl)
- [ ] All tests pass
