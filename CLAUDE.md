# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ToyDB is an educational relational database server written in Python. It implements a full RDBMS stack (SQL parsing through disk page management) optimized for clarity over performance. The project is built incrementally across 9 phases, each adding one major component while keeping the system runnable end-to-end.

Detailed specifications live in `specification/`:
- `MISSION.md` — goals, non-goals, design principles, supported SQL subset
- `ARCHITECTURE.md` — six-layer architecture, component APIs, file structure
- `ROADMAP.md` — phase-by-phase build plan with done criteria

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

After install, `toydb` is available as a CLI command.

## Build and Run

```bash
# Run REPL via CLI entry point (default mode)
toydb

# Or via module
python -m toydb

# Run as TCP server
toydb --mode server --port 9876

# Run as TCP client
toydb --mode client --host localhost --port 9876

# Run all tests
pytest

# Run a single test file
pytest tests/test_lexer.py

# Run a specific test
pytest tests/test_lexer.py::test_tokenize_select -v
```

## Dependencies

- Python 3.11+
- Standard library only for core engine (`struct`, `socket`, `threading`, `os`, `collections`, `dataclasses`, `typing`, `abc`, `enum`)
- `pytest` for tests (dev dependency only)
- No third-party packages in core — the point is building everything from scratch

## Versioning

Version format: `x.y.z` where:
- `x` — major version, changed manually by the user
- `y` — phase number (1–9)
- `z` — fix/patch within a phase

- Version tracked in: `pyproject.toml` and `toydb/__init__.py`
- Release history: `RELEASE.md`
- Git tags: `v{x}.{y}.0` after each phase completes

## Architecture

Six layers, data flows top-down (query) and bottom-up (results):

1. **Network** — TCP server, wire protocol, per-connection sessions
2. **SQL Frontend** — hand-written lexer → recursive descent parser → binder (name resolution)
3. **Query Processing** — logical plan → rule-based optimizer → physical plan
4. **Execution Engine** — Volcano iterator model (`open`/`next`/`close`)
5. **Storage Engine** — buffer pool (LRU, 64 frames), heap files (slotted pages), B+ tree indexes
6. **Disk Manager** — raw page I/O (4096-byte pages), WAL

Cross-cutting: Catalog (self-hosting metadata in `data/_catalog.dat`), Transaction Manager (2PL row-level locking), WAL + crash recovery (ARIES-style redo/undo).

## Key Design Constraints

- Each layer talks only to the layer directly below it — no skipping
- All AST nodes and plan nodes are frozen dataclasses
- Codebase target: 4000–6000 lines total, modules under 300 lines each
- Page size: 4096 bytes; tuple format uses null bitmap + big-endian encoding
- Buffer pool uses pin/unpin protocol; dirty pages respect WAL flush ordering
- The GIL is acknowledged but locking discipline is implemented as if it weren't there

## File Layout

```
toydb/             # main package
  parser/          # lexer, recursive descent parser, AST nodes, binder
  planner/         # logical planner, optimizer rules, plan nodes
  storage/         # disk manager, slotted pages, heap files, buffer pool, B+ tree
  txn/             # transaction manager, lock manager, WAL, recovery
  utils/           # tuple serialization, result formatter, error hierarchy
tests/             # pytest tests, one file per component + e2e
data/              # runtime data directory (created on first run)
specification/     # MISSION.md, ARCHITECTURE.md, ROADMAP.md
```

## Development Phases

The project is built in order, each phase producing a runnable system:

1. SQL parser + REPL + in-memory storage
2. Type system + expressions + catalog
3. Heap file storage (disk persistence)
4. Buffer pool manager
5. B+ tree index
6. WAL + crash recovery
7. Transactions (BEGIN/COMMIT/ROLLBACK, 2PL locking)
8. Query planner + Volcano executor (replaces in-memory executor)
9. TCP server + wire protocol

Phase 8 removes `executor_mem.py` and replaces it with `executor.py` (Volcano iterators). Until then, `executor_mem.py` executes AST directly.

## Claude Code Skills

- `/upload-issues <phase-issues-file>` — upload issues from a phase issues file to GitHub with labels and dependencies
- `/execute-issues <label> [--issue TDB-xxx] [--dry-run]` — execute GitHub issues for a phase: implement, validate, commit, push, close
