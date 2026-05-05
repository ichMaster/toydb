# Phase 3: Heap File Storage (Disk Persistence)

## Goal
Disk manager for raw page I/O, slotted page layout, heap file for table data, tuple serialization. Data survives process restart.

## Modules to Create

| Module                       | Responsibility                            |
|------------------------------|-------------------------------------------|
| `toydb/storage/__init__.py`  | Package init                              |
| `toydb/storage/disk_manager.py` | read_page / write_page / allocate_page |
| `toydb/storage/page.py`      | SlottedPage: header + slot array + tuples |
| `toydb/storage/heap_file.py` | HeapFile: insert, get, delete, update, scan |
| `toydb/utils/tuple_serde.py` | Serialize/deserialize Row <-> bytes       |

## Modules to Modify

| Module               | Changes                                             |
|----------------------|-----------------------------------------------------|
| `toydb/executor_mem.py` | Replace in-memory dict storage with HeapFile calls |
| `toydb/catalog.py`   | Persist catalog to `data/_catalog.dat` via heap file |
| `toydb/__main__.py`  | Create `data/` directory on first run               |

## Tasks

### 1. Disk manager (`storage/disk_manager.py`)
- [ ] Define `PAGE_SIZE = 4096` constant
- [ ] Implement `DiskManager` class
- [ ] `__init__(self, data_dir: str)` -- create data_dir if it doesn't exist
- [ ] `open_file(filename: str) -> int` -- open/create file, return file_id
- [ ] `read_page(file_id: int, page_id: int) -> bytearray` -- seek to `page_id * PAGE_SIZE`, read PAGE_SIZE bytes
- [ ] `write_page(file_id: int, page_id: int, data: bytes) -> None` -- seek and write
- [ ] `allocate_page(file_id: int) -> int` -- extend file by one page, return new page_id
- [ ] `file_size(file_id: int) -> int` -- used to determine total page count
- [ ] All I/O is synchronous

### 2. Slotted page (`storage/page.py`)
- [ ] Implement `SlottedPage` class
- [ ] Page layout (4096 bytes total):
  - Header (16 bytes): page_id(4B), num_slots(2B), free_start(2B), free_end(2B), flags(2B), page_lsn(4B, reserved for Phase 6)
  - Slot array: grows forward from offset 16, 4 bytes per slot (offset 2B + length 2B)
  - Tuple data: grows backward from end of page
- [ ] `__init__(self, data: bytearray = None)` -- initialize empty page or parse from bytes
- [ ] `insert(tuple_data: bytes) -> int` -- insert tuple, return slot_id
- [ ] `get(slot_id: int) -> Optional[bytes]` -- return tuple data or None if deleted
- [ ] `delete(slot_id: int) -> None` -- set slot offset=0, length=0 (tombstone)
- [ ] `free_space() -> int` -- returns `free_end - free_start`
- [ ] `slot_count() -> int`
- [ ] `to_bytes() -> bytes`
- [ ] `from_bytes(cls, data: bytes) -> SlottedPage` classmethod
- [ ] Handle page-full condition (not enough free space for tuple + slot entry)

### 3. Tuple serialization (`utils/tuple_serde.py`)
- [ ] Implement `TupleSerializer` class with static methods
- [ ] `serialize(values: list[Any], schema: list[ColumnDef]) -> bytes`
- [ ] `deserialize(data: bytes, schema: list[ColumnDef]) -> list[Any]`
- [ ] Serialization format: `[null_bitmap][col0_data][col1_data]...`
- [ ] Null bitmap: 1 bit per column, rounded up to full bytes. Bit=1 means NULL
- [ ] INT: 4 bytes, big-endian signed (`struct.pack('>i', val)`)
- [ ] FLOAT: 8 bytes, big-endian double (`struct.pack('>d', val)`)
- [ ] VARCHAR: 2-byte length prefix (uint16) + UTF-8 encoded bytes
- [ ] BOOL: 1 byte (0x00 = false, 0x01 = true)
- [ ] NULL columns: set bit in bitmap, write no data bytes

### 4. Heap file (`storage/heap_file.py`)
- [ ] Implement `HeapFile` class
- [ ] `__init__(self, disk_manager: DiskManager, file_id: int)`
- [ ] `insert_tuple(data: bytes) -> tuple[int, int]` -- find page with space or allocate new, return (page_id, slot_id)
- [ ] `get_tuple(page_id: int, slot_id: int) -> Optional[bytes]`
- [ ] `delete_tuple(page_id: int, slot_id: int) -> None` -- mark slot as tombstone
- [ ] `update_tuple(page_id: int, slot_id: int, new_data: bytes)` -- delete + insert if size changed, or in-place update
- [ ] `scan() -> Iterator[tuple[int, int, bytes]]` -- iterate all live tuples across all pages, yield (page_id, slot_id, data)
- [ ] Page search for insert: scan pages for one with enough free space, fallback to allocate new page

### 5. Executor migration (`executor_mem.py`)
- [ ] Replace in-memory dict storage with HeapFile read/write calls
- [ ] Serialize tuples before insert using TupleSerializer
- [ ] Deserialize tuples when reading using TupleSerializer
- [ ] Route scan through HeapFile.scan()
- [ ] Route delete through HeapFile.delete_tuple()
- [ ] Route update through HeapFile.update_tuple()

### 6. Catalog persistence (`catalog.py`)
- [ ] Store catalog data in `data/_catalog.dat` using the same heap file mechanism
- [ ] Three logical system tables:
  - `sys_tables(table_id INT, name VARCHAR(64), heap_file VARCHAR(128), num_columns INT)`
  - `sys_columns(table_id INT, column_id INT, name VARCHAR(64), data_type INT, max_length INT, nullable BOOL)`
- [ ] Load catalog into memory at startup for fast lookup
- [ ] Write-through: modifications are persisted to disk immediately

### 7. Entry point update (`__main__.py`)
- [ ] Create `data/` directory on first run if it doesn't exist
- [ ] Initialize DiskManager with `data/` directory
- [ ] Bootstrap catalog on first run (create `_catalog.dat`)
- [ ] Load existing catalog on subsequent runs

### 8. Tests
- [ ] `tests/test_page.py`: insert/get/delete tuples on SlottedPage, verify free space accounting, test page-full condition
- [ ] `tests/test_heap_file.py`: insert 1000 tuples, scan all, delete some, verify scan returns correct remaining tuples
- [ ] `tests/test_tuple_serde.py`: round-trip serialize/deserialize for all types including NULLs
- [ ] `tests/test_e2e.py` (extended): restart persistence -- insert data, create fresh executor from disk, verify data is present

## Data File Layout

```
data/
  _catalog.dat           # system catalog heap file
  {table_name}.dat       # per-table heap files
```

## Done Criteria
- [ ] All table data stored in `data/{table_name}.dat` as slotted pages
- [ ] Catalog persisted in `data/_catalog.dat`
- [ ] Data survives process restart
- [ ] Sequential scan reads all pages from disk
- [ ] INSERT finds a page with free space (or allocates new page)
- [ ] DELETE marks slot as tombstone
- [ ] All tests pass
