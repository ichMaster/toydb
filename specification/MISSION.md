# ToyDB -- Mission

## What is ToyDB

ToyDB is an educational relational database server written in Python. It implements the core concepts found in production systems like MySQL, PostgreSQL, and SQLite -- from SQL parsing down to disk page management -- in a codebase small enough for one person to understand completely.

The project exists for learning. Every design decision optimizes for clarity and pedagogical value over performance. Where a production database would use C, unsafe memory tricks, or OS-specific syscalls, ToyDB uses clean Python with explicit data structures and readable control flow.

## Goals

- Build a working SQL database server from scratch -- no ORM, no SQLite, no external query engines.
- Implement every major subsystem that a real RDBMS contains: parser, planner, executor, storage engine, buffer pool, indexing, write-ahead log, transactions, and network protocol.
- Maintain a working prototype after every development phase. The system is always runnable and demonstrable -- never in a half-built state.
- Keep the codebase under 6000 lines of Python. If a module grows beyond 300 lines, it needs refactoring or splitting.
- Every component should be testable in isolation. Unit tests accompany each phase.

## Non-Goals

- Production-grade performance. ToyDB will never compete with real databases on speed or scale.
- Full SQL compliance. We implement a practical subset, not the entire SQL standard.
- Multi-user production deployment. The concurrency model is educational, not battle-tested.
- Compatibility with MySQL/PostgreSQL wire protocols. ToyDB uses its own simple binary protocol.

## Design Principles

### Explicit over implicit

Every data structure is visible. Pages are byte arrays you can hex-dump. The buffer pool is a fixed-size list of frames. The B-tree is a set of pages with pointers you can trace. No magic -- if something happens, the code shows exactly how and where.

### Layered architecture with clean boundaries

Each layer talks only to the layer directly below it through a defined interface. The executor never touches disk directly. The parser never knows about pages. This means any layer can be swapped, tested, or inspected independently.

### Incremental development

The project is built in 9 phases. Each phase adds exactly one major component. After each phase, the system works end-to-end -- you can type SQL and get results. Early phases use naive implementations (in-memory dicts, sequential scan) that later phases replace with proper subsystems (heap files, index scans).

### Python idioms

Use dataclasses for AST nodes and records. Use typing throughout. Use `__iter__` and generator protocols for the Volcano execution model. Use `struct` module for page serialization. Use `abc.ABC` for interfaces between layers. Avoid third-party dependencies in the core engine -- stdlib only.

## Supported SQL (final state)

```sql
-- DDL
CREATE TABLE name (col1 TYPE, col2 TYPE, ...);
DROP TABLE name;
CREATE INDEX name ON table (column);

-- DML
INSERT INTO table VALUES (v1, v2, ...);
SELECT cols FROM table [JOIN table ON cond] [WHERE cond] [ORDER BY col [ASC|DESC]] [LIMIT n];
UPDATE table SET col = expr [WHERE cond];
DELETE FROM table [WHERE cond];

-- Transactions
BEGIN;
COMMIT;
ROLLBACK;

-- Utility
SHOW TABLES;
DESCRIBE table;
EXPLAIN SELECT ...;
```

## Data Types

| Type       | Size       | Description                |
|------------|------------|----------------------------|
| INT        | 4 bytes    | Signed 32-bit integer      |
| FLOAT      | 8 bytes    | 64-bit double              |
| VARCHAR(n) | 2 + len    | Variable-length UTF-8 text |
| BOOL       | 1 byte     | true / false               |

## Target Metrics

- Total codebase: 4000--6000 lines of Python
- Per-phase increment: 400--700 lines
- Page size: 4096 bytes
- Default buffer pool: 64 frames (256 KB)
- B-tree order: fits within one page (circa 50--100 keys depending on key size)
- WAL segment: single append-only file
- Network protocol overhead: 5 bytes per frame (4 length + 1 type)

## Language and Dependencies

- Python 3.11+
- Standard library only for core engine: struct, socket, threading, os, io, collections, dataclasses, typing, abc, enum
- pytest for testing (dev dependency only)
- No SQLAlchemy, no sqlite3, no pandas -- the whole point is building it ourselves
