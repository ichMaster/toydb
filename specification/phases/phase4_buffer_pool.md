# Phase 4: Buffer Pool Manager

## Goal
Fixed-size page cache between the executor and disk. LRU eviction policy. Pin/unpin protocol.

## Modules to Create

| Module                        | Responsibility                          |
|-------------------------------|-----------------------------------------|
| `toydb/storage/buffer_pool.py` | BufferPoolManager: fetch, unpin, flush |
| `toydb/storage/replacer.py`   | LRUReplacer: eviction ordering         |

## Modules to Modify

| Module                    | Changes                                        |
|---------------------------|------------------------------------------------|
| `toydb/storage/heap_file.py` | Replace direct disk I/O with buffer pool calls |
| `toydb/repl.py`           | Add `.buffer_stats` and `.flush` commands       |

## Tasks

### 1. LRU replacer (`storage/replacer.py`)
- [ ] Implement `LRUReplacer` class
- [ ] `__init__(self, capacity: int)`
- [ ] `record_access(frame_id: int) -> None` -- move to most-recently-used position
- [ ] `set_evictable(frame_id: int, evictable: bool) -> None` -- control whether a frame can be evicted
- [ ] `evict() -> Optional[int]` -- return least-recently-used unpinned frame_id, or None if all pinned
- [ ] `size() -> int` -- number of evictable frames
- [ ] Use `collections.OrderedDict` internally for O(1) operations

### 2. Frame data structure
- [ ] Define `Frame` dataclass:
  - `page_id: Optional[int]`
  - `file_id: Optional[int]`
  - `data: bytearray` (PAGE_SIZE bytes)
  - `pin_count: int`
  - `is_dirty: bool`

### 3. Buffer pool manager (`storage/buffer_pool.py`)
- [ ] Implement `BufferPoolManager` class
- [ ] `__init__(self, pool_size: int, disk_manager: DiskManager)` -- default pool_size=64
- [ ] Maintain `page_table: dict[tuple[int, int], int]` mapping (file_id, page_id) -> frame_id for O(1) lookup
- [ ] `fetch_page(file_id: int, page_id: int) -> SlottedPage`:
  - Check page_table, if found: increment pin_count, return page
  - If not found: call replacer.evict() to find a frame
  - If evicted frame is dirty, flush it to disk first
  - Read requested page from disk into frame
  - Set pin_count=1, return page
- [ ] `unpin_page(file_id: int, page_id: int, is_dirty: bool) -> None`:
  - Decrement pin_count
  - If dirty, mark frame dirty
  - If pin_count reaches 0, frame becomes evictable
- [ ] `new_page(file_id: int) -> tuple[int, SlottedPage]`:
  - Allocate page on disk
  - Find/evict a frame
  - Initialize empty page in frame
  - Return (page_id, page)
- [ ] `flush_page(file_id: int, page_id: int) -> None` -- write dirty page to disk immediately
- [ ] `flush_all() -> None` -- write all dirty pages to disk

### 4. Buffer pool stats
- [ ] Track hit_count and miss_count
- [ ] `hit_count() -> int`
- [ ] `miss_count() -> int`
- [ ] `hit_ratio() -> float`

### 5. Configuration
- [ ] Read pool size from env: `TOYDB_POOL_SIZE` (default 64 = 256 KB cache)

### 6. Heap file migration (`storage/heap_file.py`)
- [ ] Replace all direct `disk_manager.read_page()` / `write_page()` calls with `buffer_pool.fetch_page()` / `unpin_page()`
- [ ] Ensure proper pin/unpin discipline: every fetch has a matching unpin
- [ ] Mark pages dirty when modified

### 7. REPL commands (`repl.py`)
- [ ] Add `.buffer_stats` command: show frame count, used/total, dirty count, hit ratio
- [ ] Add `.flush` command: call `buffer_pool.flush_all()`, report flushed page count

### 8. Tests
- [ ] `tests/test_replacer.py`: LRU ordering -- access A, B, C, A; evict should return B (least recent)
- [ ] `tests/test_buffer_pool.py`:
  - Fetch a page, verify it returns correct data
  - Fetch more pages than pool size, verify eviction happens (LRU frame is evicted)
  - Pin a page, verify it is not evicted even when pool is full
  - Mark a page dirty, evict it, verify it was flushed to disk
  - Test hit/miss counting
- [ ] Verify all existing SQL operations work identically (transparent caching layer)

## Done Criteria
- [ ] All heap file I/O goes through the buffer pool
- [ ] LRU eviction works correctly under memory pressure
- [ ] Dirty pages are flushed before eviction
- [ ] `.buffer_stats` shows accurate hit ratio
- [ ] `.flush` writes all dirty pages to disk
- [ ] Existing SQL operations work identically (transparent caching layer)
- [ ] All tests pass
