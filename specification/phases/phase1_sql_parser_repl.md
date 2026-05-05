# Phase 1: SQL Parser + REPL + In-Memory Storage

## Goal
Hand-written SQL lexer and recursive descent parser, interactive REPL, naive in-memory table storage using Python dicts.

## Modules to Create

| Module                   | Responsibility                              |
|--------------------------|---------------------------------------------|
| `toydb/__init__.py`      | Package init                                |
| `toydb/__main__.py`      | Entry point: `--mode repl`                  |
| `toydb/repl.py`          | Read-eval-print loop with readline support  |
| `toydb/parser/__init__.py` | Package init                              |
| `toydb/parser/lexer.py`  | Character-by-character tokenizer            |
| `toydb/parser/parser.py` | Recursive descent parser producing AST      |
| `toydb/parser/ast_nodes.py` | Frozen dataclasses for every AST node    |
| `toydb/executor_mem.py`  | Executes AST directly on in-memory tables   |
| `toydb/table_mem.py`     | Table = name + column names + list of dicts |
| `toydb/utils/__init__.py` | Package init                               |
| `toydb/utils/formatter.py` | Pretty-print query results as ASCII table |
| `toydb/utils/errors.py`  | ParseError, ExecutionError base classes     |

## Tasks

### 1. Error hierarchy (`utils/errors.py`)
- [ ] Define `ToyDBError` base exception
- [ ] Define `ParseError(ToyDBError)` with `position` attribute
- [ ] Define `ExecutionError(ToyDBError)`

### 2. Lexer (`parser/lexer.py`)
- [ ] Define `TokenType` enum: KEYWORD, IDENTIFIER, INTEGER_LIT, FLOAT_LIT, STRING_LIT, OPERATOR, COMMA, LPAREN, RPAREN, SEMICOLON, STAR, EOF
- [ ] Define `Token` dataclass with `type`, `value`, `position` fields
- [ ] Implement `Lexer` class with `__init__(self, sql: str)` and `tokenize() -> list[Token]`
- [ ] Handle case-insensitive keywords: SELECT, FROM, WHERE, INSERT, INTO, VALUES, CREATE, TABLE, DELETE, AND, OR, NOT
- [ ] Handle identifiers (preserve case)
- [ ] Handle integer and float literals
- [ ] Handle string literals with single-quote escaping
- [ ] Handle operators: =, !=, <, >, <=, >=
- [ ] Handle special characters: (, ), *, ,, ;
- [ ] Skip whitespace
- [ ] Raise `ParseError` with position on unknown characters

### 3. AST nodes (`parser/ast_nodes.py`)
- [ ] Define all nodes as frozen dataclasses
- [ ] `CreateTable(name: str, columns: list[str])` -- untyped in Phase 1
- [ ] `Insert(table: str, values: list[Expression])`
- [ ] `Select(columns: list[Expression], table: str, where: Optional[Expression])`
- [ ] `Delete(table: str, where: Optional[Expression])`
- [ ] `Star()` -- represents SELECT *
- [ ] `ColumnRef(table: Optional[str], name: str)`
- [ ] `Literal(value: Any)`
- [ ] `BinaryOp(left: Expression, op: str, right: Expression)`

### 4. Parser (`parser/parser.py`)
- [ ] Implement `Parser` class with `__init__(self, tokens: list[Token])` and `parse() -> Statement`
- [ ] Parse `CREATE TABLE t (col1, col2, col3);`
- [ ] Parse `INSERT INTO t VALUES (v1, v2, ...);`
- [ ] Parse `SELECT * FROM t;`
- [ ] Parse `SELECT col1, col2 FROM t WHERE condition;`
- [ ] Parse `DELETE FROM t WHERE condition;`
- [ ] Parse WHERE clauses with AND/OR and simple comparisons (=, !=, <, >, <=, >=)
- [ ] Raise `ParseError` with position info on unexpected tokens

### 5. In-memory table storage (`table_mem.py`)
- [ ] Define `MemoryTable` class: `name`, `column_names: list[str]`, `rows: list[dict]`
- [ ] `insert(values: list) -> None`
- [ ] `scan() -> Iterator[dict]`
- [ ] `delete(predicate) -> int` -- returns number of deleted rows

### 6. In-memory executor (`executor_mem.py`)
- [ ] Define `MemoryExecutor` class with `__init__(self, tables: dict[str, MemoryTable])`
- [ ] `execute(stmt: Statement) -> ExecutionResult`
- [ ] Handle CREATE TABLE: create a new MemoryTable
- [ ] Handle INSERT: add row to the table
- [ ] Handle SELECT *: return all rows
- [ ] Handle SELECT with column list: project columns
- [ ] Handle SELECT with WHERE: filter rows using predicate evaluation
- [ ] Handle DELETE with WHERE: remove matching rows, return count

### 7. Result formatter (`utils/formatter.py`)
- [ ] Pretty-print results as ASCII table with borders
- [ ] Auto-size column widths based on content
- [ ] Print row count footer: `N row(s)`

### 8. REPL (`repl.py`)
- [ ] Read SQL input with readline support (history, line editing)
- [ ] Support multi-line input (continue until semicolon)
- [ ] Execute statement and print result or error
- [ ] Handle `.quit` or `.exit` to exit
- [ ] Handle Ctrl+C and Ctrl+D gracefully

### 9. Entry point (`__main__.py`)
- [ ] Parse CLI args (--mode repl for now)
- [ ] Initialize executor with empty table dict
- [ ] Start REPL

### 10. Tests
- [ ] `tests/test_lexer.py`: tokenize various SQL strings, verify token types and values, test edge cases (string escaping, numeric formats, unknown characters)
- [ ] `tests/test_parser.py`: parse valid SQL and assert AST structure, verify ParseError on malformed input
- [ ] `tests/test_e2e.py`: execute a sequence of CREATE/INSERT/SELECT/DELETE and verify results
- [ ] `tests/conftest.py`: shared fixtures

## Supported SQL

```sql
CREATE TABLE t (col1, col2, col3);
INSERT INTO t VALUES (1, 'hello', 42);
SELECT * FROM t;
SELECT col1, col2 FROM t WHERE col1 = 1;
DELETE FROM t WHERE col2 = 'hello';
```

## Done Criteria
- [ ] REPL starts, accepts SQL, prints results or errors
- [ ] CREATE TABLE, INSERT, SELECT (with column list and WHERE), DELETE all work
- [ ] Pretty-printed ASCII table output
- [ ] ParseError with position info on bad SQL
- [ ] All tests pass
