# Phase 6: WAL + Crash Recovery

## Goal
Write-ahead log for durability. Checkpoint mechanism. Redo recovery on startup after crash.

## Modules to Create

| Module                    | Responsibility                                  |
|---------------------------|--------------------------------------------------|
| `toydb/txn/__init__.py`   | Package init                                     |
| `toydb/txn/wal.py`        | WALManager: append records, flush, read back     |
| `toydb/txn/wal_record.py` | WAL record dataclasses and serialization         |
| `toydb/txn/recovery.py`   | RecoveryManager: replay WAL from last checkpoint |

## Modules to Modify

| Module                        | Changes                                     |
|-------------------------------|---------------------------------------------|
| `toydb/storage/buffer_pool.py` | Check page_lsn before flushing dirty pages |
| `toydb/storage/page.py`       | Read/write page_lsn field in header         |
| `toydb/executor_mem.py`       | Generate WAL records before modifying pages |
| `toydb/__main__.py`           | Run recovery on startup before accepting SQL |
| `toydb/repl.py`               | Add `.checkpoint` command                   |

## Tasks

### 1. WAL record types (`txn/wal_record.py`)
- [ ] Define `WALRecordType` enum:
  - INSERT (0x01): payload = serialized tuple bytes
  - DELETE (0x02): payload = slot_id
  - UPDATE (0x03): payload = slot_id + before_image + after_image
  - COMMIT (0x10): payload = empty
  - ABORT (0x11): payload = empty
  - CHECKPOINT (0x20): payload = list of dirty (page_id, page_lsn) pairs
- [ ] Define `WALRecord` frozen dataclass: `lsn`, `txn_id`, `record_type`, `table_id`, `page_id`, `payload`
- [ ] Implement binary serialization:
  ```
  [record_length: 4B uint32]
  [lsn: 8B uint64]
  [txn_id: 4B uint32]
  [record_type: 1B]
  [table_id: 4B uint32]
  [page_id: 4B uint32]
  [payload_length: 4B uint32]
  [payload: variable]
  [checksum: 4B CRC32]
  ```
- [ ] Implement binary deserialization with CRC32 integrity check

### 2. WAL manager (`txn/wal.py`)
- [ ] Implement `WALManager` class
- [ ] `__init__(self, wal_path: str)` -- open/create WAL file at `data/wal.log`
- [ ] `append(record: WALRecord) -> int` -- serialize and append, return LSN
- [ ] `flush() -> None` -- fsync WAL to disk
- [ ] `get_flushed_lsn() -> int`
- [ ] `read_from(start_lsn: int) -> Iterator[WALRecord]` -- read records from a given LSN forward
- [ ] `write_checkpoint(dirty_pages: list[tuple[int, int]]) -> None` -- write CHECKPOINT record
- [ ] `find_last_checkpoint() -> Optional[int]` -- scan backward for last CHECKPOINT, return its LSN
- [ ] Monotonically increasing LSN counter
- [ ] Thread-safe: one mutex for appending records, one for flushing

### 3. WAL protocol enforcement
- [ ] Before any data page modification, append WAL record (`executor_mem.py`)
- [ ] Buffer pool flush rule (`storage/buffer_pool.py`): never flush a page whose `page_lsn > flushed_wal_lsn`; force WAL flush first
- [ ] Page header (`storage/page.py`): read/write `page_lsn` field (bytes 12..15)
- [ ] Set `page_lsn = record.lsn` after applying a modification

### 4. Checkpoint mechanism
- [ ] Write CHECKPOINT record containing list of all dirty (file_id, page_id, page_lsn) in the buffer pool
- [ ] Flush all dirty pages to disk
- [ ] Flush WAL
- [ ] Add `.checkpoint` REPL command to trigger manual checkpoint

### 5. Recovery manager (`txn/recovery.py`)
- [ ] Implement `RecoveryManager` class
- [ ] `__init__(self, wal: WALManager, buffer_pool: BufferPoolManager, catalog: CatalogManager)`
- [ ] `recover() -> RecoveryStats` -- redo-only in Phase 6:
  1. Find last CHECKPOINT record in WAL
  2. Read all records after checkpoint LSN
  3. For each INSERT/UPDATE/DELETE record: fetch the target page; if `page_lsn < record.lsn`, apply the change (redo); otherwise skip
  4. Flush all redone pages
  5. Write a fresh checkpoint
- [ ] Return stats: records scanned, pages redone
- [ ] Redo must be idempotent (safe to replay same record twice)

### 6. Startup recovery (`__main__.py`)
- [ ] On startup, before accepting SQL, run `recovery_manager.recover()`
- [ ] Log recovery activity: checkpoint LSN, records replayed, pages redone

### 7. Executor WAL integration (`executor_mem.py`)
- [ ] Generate WAL record before every INSERT (payload = tuple bytes)
- [ ] Generate WAL record before every DELETE (payload = slot_id)
- [ ] Generate WAL record before every UPDATE (payload = slot_id + before_image + after_image)
- [ ] Use txn_id=0 for now (proper transactions in Phase 7)

### 8. Tests
- [ ] `tests/test_wal.py`:
  - Append records, read them back, verify LSN ordering
  - Write checkpoint, find_last_checkpoint returns correct LSN
  - Verify CRC32 integrity check catches corrupted records
- [ ] `tests/test_recovery.py`:
  - Insert rows, simulate crash (don't flush buffer pool), run recovery, verify data present
  - Insert rows + checkpoint + more inserts + crash, verify recovery replays only post-checkpoint records
  - Verify idempotent redo: run recovery twice, results are identical

## WAL File Location

```
data/wal.log    # single append-only WAL file
```

## Done Criteria
- [ ] Every INSERT/UPDATE/DELETE generates a WAL record before modifying pages
- [ ] Buffer pool respects WAL flush ordering (no dirty page flushed ahead of its WAL record)
- [ ] Checkpoint writes dirty page list and flushes everything
- [ ] Recovery on startup replays WAL and restores all committed data
- [ ] Redo is idempotent (safe to replay same record twice)
- [ ] `.checkpoint` REPL command triggers manual checkpoint
- [ ] All tests pass
