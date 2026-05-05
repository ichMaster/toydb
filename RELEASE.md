# ToyDB Release History

## 0.1.0 (2026-05-05)

Phase 1 — SQL Parser + REPL + In-Memory Storage

- TDB-001: Project scaffold and package structure — set up toydb package with sub-packages and pyproject.toml
- TDB-002: Error hierarchy — ToyDBError, ParseError with position, ExecutionError
- TDB-003: SQL lexer — hand-written tokenizer for keywords, literals, operators
- TDB-004: AST node definitions — frozen dataclasses for all SQL statement and expression nodes
- TDB-005: Recursive descent SQL parser — parser with expression precedence for all Phase 1 SQL
- TDB-006: In-memory table storage — MemoryTable with insert, scan, delete operations
- TDB-007: Result formatter — ASCII table output with auto-sized columns
- TDB-008: In-memory executor — execute AST against in-memory tables with WHERE evaluation
- TDB-009: REPL and CLI entry point — interactive REPL with readline, multi-line, error handling
- TDB-010: Phase 1 test suite — 32 tests covering lexer, parser, and end-to-end flows
- TDB-011: Phase 1 documentation — README, getting-started guide, SQL reference, architecture overview
