# Phase 7: Transactions

## Goal
Transaction manager with BEGIN/COMMIT/ROLLBACK. Row-level locking with 2PL. Undo support for ROLLBACK using WAL before-images.

## Modules to Create

| Module                       | Responsibility                              |
|------------------------------|---------------------------------------------|
| `toydb/txn/transaction.py`   | TransactionManager: begin, commit, abort    |
| `toydb/txn/txn_context.py`   | TxnContext: per-transaction state           |
| `toydb/txn/lock_manager.py`  | LockManager: shared/exclusive row-level locks |

## Modules to Modify

| Module                 | Changes                                              |
|------------------------|------------------------------------------------------|
| `toydb/txn/wal.py`     | WAL records now carry real txn_id. Add COMMIT/ABORT. |
| `toydb/txn/recovery.py` | Add undo phase: roll back uncommitted transactions |
| `toydb/executor_mem.py` | Wrap operations in transaction context. Acquire locks. |
| `toydb/parser/parser.py` | Parse BEGIN, COMMIT, ROLLBACK                      |
| `toydb/parser/ast_nodes.py` | Add Begin, Commit, Rollback AST nodes           |
| `toydb/repl.py`         | Track current transaction in REPL session           |
| `toydb/utils/errors.py` | Add TransactionError                                |

## Tasks

### 1. AST and parser additions
- [ ] Add `Begin`, `Commit`, `Rollback` frozen dataclasses to ast_nodes.py
- [ ] Parse `BEGIN;`, `COMMIT;`, `ROLLBACK;` in parser.py

### 2. Transaction context (`txn/txn_context.py`)
- [ ] Define `TxnStatus` enum: ACTIVE, COMMITTED, ABORTED
- [ ] Define `TxnContext` dataclass:
  - `txn_id: int`
  - `status: TxnStatus`
  - `acquired_locks: list[LockRequest]`
  - `wal_records: list[int]` -- LSNs for undo on abort
  - `start_lsn: int`

### 3. Lock manager (`txn/lock_manager.py`)
- [ ] Define `LockMode` enum: SHARED, EXCLUSIVE
- [ ] Define `LockRequest` dataclass: `resource: tuple[int, int, int]` (table_id, page_id, slot_id), `mode`, `txn_id`
- [ ] Implement `LockManager` class
- [ ] `__init__(self, timeout_seconds: float = 5.0)`
- [ ] Lock table: `dict[resource_key, LockEntry]` where LockEntry tracks holders and wait queue
- [ ] `acquire(resource: tuple, mode: LockMode, txn_id: int) -> bool`:
  - SHARED + SHARED: compatible, both acquire
  - SHARED + EXCLUSIVE: conflict, second waits
  - EXCLUSIVE + EXCLUSIVE: conflict, second waits
  - Block on `threading.Condition` with timeout
  - If timeout expires, raise `TransactionError` (deadlock detection)
- [ ] `release_all(txn_id: int) -> None` -- release all locks held by a transaction
- [ ] Thread-safe: one global mutex for the lock table, per-resource condition variables

### 4. Transaction manager (`txn/transaction.py`)
- [ ] Implement `TransactionManager` class
- [ ] `__init__(self, wal: WALManager, lock_manager: LockManager)`
- [ ] `begin() -> TxnContext` -- allocate new txn_id, create TxnContext
- [ ] `commit(txn: TxnContext) -> None`:
  - Write COMMIT WAL record
  - Flush WAL (fsync)
  - Release all locks
  - Set status = COMMITTED
- [ ] `abort(txn: TxnContext) -> None`:
  - Undo changes by reading WAL records in reverse and applying before-images
  - Write ABORT WAL record
  - Release all locks
  - Set status = ABORTED
- [ ] Maintain `active_transactions: dict[txn_id, TxnContext]`

### 5. Autocommit mode
- [ ] When no explicit BEGIN is active, each statement is wrapped in an implicit transaction
- [ ] Auto-begin before execution
- [ ] Auto-commit after success
- [ ] Auto-abort on error

### 6. Executor integration (`executor_mem.py`)
- [ ] Accept optional `TxnContext` for all operations
- [ ] Acquire SHARED lock before reading a row
- [ ] Acquire EXCLUSIVE lock before writing (INSERT/UPDATE/DELETE) a row
- [ ] Include real txn_id in WAL records
- [ ] On error during execution, abort the transaction

### 7. REPL session tracking (`repl.py`)
- [ ] Track current transaction (None when in autocommit)
- [ ] BEGIN: start new transaction, store in session
- [ ] COMMIT: commit current transaction, clear session
- [ ] ROLLBACK: abort current transaction, clear session
- [ ] Display transaction state in prompt (e.g., `toydb(txn 42)>`)

### 8. Recovery undo phase (`txn/recovery.py`)
- [ ] After redo phase, scan for transactions that have no COMMIT or ABORT record
- [ ] For each uncommitted transaction:
  1. Read their WAL records in reverse order
  2. Apply before-images to undo changes
  3. Write ABORT record
- [ ] Three-phase recovery: Analysis -> Redo -> Undo

### 9. Tests
- [ ] `tests/test_transaction.py`:
  - BEGIN + INSERT + COMMIT: data visible after commit
  - BEGIN + INSERT + ROLLBACK: data not visible after rollback
  - Autocommit: single INSERT without BEGIN is committed
  - Abort on error: INSERT with type mismatch inside transaction rolls back entirely
- [ ] `tests/test_lock_manager.py`:
  - SHARED + SHARED: compatible, both acquire
  - SHARED + EXCLUSIVE: conflict, second waits
  - EXCLUSIVE + EXCLUSIVE: conflict, second waits
  - Deadlock timeout: two transactions lock resources in opposite order, one aborts
- [ ] `tests/test_recovery.py` (extended): crash with uncommitted transaction, verify undo on recovery

## Supported SQL (additions)

```sql
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;

BEGIN;
DELETE FROM orders WHERE status = 'cancelled';
ROLLBACK;
```

## Done Criteria
- [ ] BEGIN / COMMIT / ROLLBACK parsed and executed
- [ ] COMMIT flushes WAL and releases locks
- [ ] ROLLBACK undoes changes using WAL before-images
- [ ] Row-level SHARED/EXCLUSIVE locks work correctly
- [ ] Lock conflicts cause blocking (not errors)
- [ ] Deadlock detected via timeout, one transaction aborted
- [ ] Recovery handles uncommitted transactions (undo phase)
- [ ] Autocommit wraps single statements
- [ ] All tests pass
