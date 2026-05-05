# Phase 1 — GitHub Issues

## Issues Summary Table

| # | ID | Title | Size | Stage | Dependencies |
|---|---|---|---|---|---|
| 1 | TDB-001 | Project scaffold and package structure | S | 1 — Foundation | -- |
| 2 | TDB-002 | Error hierarchy | S | 1 — Foundation | TDB-001 |
| 3 | TDB-003 | SQL lexer | M | 2 — Parser | TDB-002 |
| 4 | TDB-004 | AST node definitions | S | 2 — Parser | TDB-001 |
| 5 | TDB-005 | Recursive descent SQL parser | M | 2 — Parser | TDB-003, TDB-004 |
| 6 | TDB-006 | In-memory table storage | S | 3 — Storage | TDB-001 |
| 7 | TDB-007 | Result formatter | S | 3 — Storage | TDB-001 |
| 8 | TDB-008 | In-memory executor | M | 4 — Execution | TDB-004, TDB-006, TDB-002 |
| 9 | TDB-009 | REPL and CLI entry point | M | 5 — Integration | TDB-005, TDB-008, TDB-007 |
| 10 | TDB-010 | Phase 1 test suite | M | 6 — Testing | TDB-009 |

**Size legend:** S = 1–2 days, M = 3–5 days

---

## Dependency Tree

```
            TDB-001 (scaffold)
                |
    +-----------+-----------+---------------+
    v           v           v               v
TDB-002     TDB-004     TDB-006         TDB-007
(errors)    (AST)       (table_mem)     (formatter)
    |           |           |               |
    v           |           |               |
TDB-003         |           |               |
(lexer)         |           |               |
    |           |           |               |
    +-----+-----+           |               |
          v                 |               |
      TDB-005               |               |
      (parser)              |               |
          |         +-------+               |
          |         v                       |
          |     TDB-008 <-- TDB-002         |
          |     (executor)                  |
          |         |                       |
          +---------+-----------+-----------+
                    v
                TDB-009
                (REPL)
                    |
                    v
                TDB-010
                (tests)
```

**Parallelization hints:**

- TDB-002, TDB-004, TDB-006, and TDB-007 can all run in parallel after TDB-001
- TDB-003 and TDB-006 can run in parallel
- TDB-005 and TDB-008 can overlap if TDB-004 is merged first

---

## Stage 1 — Foundation

### TDB-001 — Project scaffold and package structure

**Description:**
Set up the `toydb/` project skeleton with package structure, `__init__.py` files, and the minimal configuration needed for development.

**What needs to be done:**
- Create `toydb/` root package with `__init__.py`
- Create sub-packages with `__init__.py`: `parser/`, `utils/`
- Create `tests/` directory with `conftest.py`
- Create `pyproject.toml` with:
  - Python 3.11+ requirement
  - No runtime dependencies (stdlib only for core engine)
  - Dev dependency: `pytest`
  - Console script entry point: `toydb = "toydb.__main__:main"`
- Create placeholder `toydb/__main__.py` with `main()` function
- Create `data/` in `.gitignore` (runtime directory, created on first run)

**Dependencies:** None

**Expected result:**
A clean project skeleton that installs and imports correctly. `python -m toydb` runs without error (even if it does nothing yet).

**Acceptance criteria:**
- [ ] `pip install -e ".[dev]"` exits 0
- [ ] `python -m toydb` runs without ImportError
- [ ] All sub-packages import without errors: `from toydb.parser import *`, `from toydb.utils import *`
- [ ] `pytest` discovers test directory (even with no tests yet)
- [ ] `data/` is in `.gitignore`

---

### TDB-002 — Error hierarchy

**Description:**
Define the custom exception hierarchy used across all ToyDB modules. Every error carries a human-readable message and, where applicable, the source position in the SQL string.

**What needs to be done:**
- Create `toydb/utils/errors.py`
- Define `ToyDBError(Exception)` — base exception for all ToyDB errors, with `message: str`
- Define `ParseError(ToyDBError)` — syntax errors, unexpected tokens; adds `position: int` attribute for the character offset in the SQL string
- Define `ExecutionError(ToyDBError)` — runtime errors during statement execution

**Dependencies:** TDB-001

**Expected result:**
A clean exception hierarchy that other modules can import and raise. ParseError carries position info for user-facing error messages like `"Unexpected token 'FORM' at position 12"`.

**Acceptance criteria:**
- [ ] `from toydb.utils.errors import ToyDBError, ParseError, ExecutionError` works
- [ ] `ParseError("msg", position=12)` stores position as attribute
- [ ] `str(ParseError("Unexpected token", position=5))` produces a readable message including position
- [ ] All three exceptions are catchable via `except ToyDBError`

---

## Stage 2 — Parser

### TDB-003 — SQL lexer

**Description:**
Hand-written character-by-character tokenizer that converts a SQL string into a list of typed tokens. The lexer is the first stage of the SQL frontend pipeline.

**What needs to be done:**
- Create `toydb/parser/lexer.py`
- Define `TokenType` enum with values: `KEYWORD`, `IDENTIFIER`, `INTEGER_LIT`, `FLOAT_LIT`, `STRING_LIT`, `OPERATOR`, `COMMA`, `LPAREN`, `RPAREN`, `SEMICOLON`, `STAR`, `EOF`
- Define `Token` frozen dataclass with fields: `type: TokenType`, `value: str`, `position: int`
- Implement `Lexer` class:
  - `__init__(self, sql: str)` — store source string
  - `tokenize() -> list[Token]` — scan source and return token list ending with EOF
- Handle case-insensitive keywords: `SELECT`, `FROM`, `WHERE`, `INSERT`, `INTO`, `VALUES`, `CREATE`, `TABLE`, `DELETE`, `AND`, `OR`, `NOT`
- Handle identifiers — preserve original case, distinguish from keywords by uppercasing and checking keyword set
- Handle integer literals (`42`) and float literals (`3.14`)
- Handle string literals with single quotes (`'hello'`), including escaped quotes (`'it''s'`)
- Handle comparison operators: `=`, `!=`, `<`, `>`, `<=`, `>=`
- Handle special characters: `(`, `)`, `*`, `,`, `;`
- Skip whitespace (spaces, tabs, newlines)
- Raise `ParseError` with character position on unknown characters

**Dependencies:** TDB-002

**Expected result:**
Any valid Phase 1 SQL string tokenizes into the correct token sequence. Invalid characters produce a `ParseError` with position info.

**Acceptance criteria:**
- [ ] `Lexer("SELECT * FROM t;").tokenize()` returns `[KEYWORD:SELECT, STAR:*, KEYWORD:FROM, IDENTIFIER:t, SEMICOLON:;, EOF]`
- [ ] Keywords are case-insensitive: `select`, `SELECT`, `SeLeCt` all produce `KEYWORD` tokens
- [ ] Identifiers preserve case: `myTable` stays `myTable`
- [ ] Integer and float literals are distinguished: `42` → `INTEGER_LIT`, `3.14` → `FLOAT_LIT`
- [ ] String literals handle escaped quotes: `'it''s'` → `STRING_LIT:"it's"`
- [ ] Multi-character operators work: `!=`, `<=`, `>=`
- [ ] Unknown character raises `ParseError` with correct position
- [ ] Whitespace (spaces, tabs, newlines) is skipped

---

### TDB-004 — AST node definitions

**Description:**
Define frozen dataclasses for all Abstract Syntax Tree nodes produced by the parser. These are the structured representation of SQL statements that the executor consumes.

**What needs to be done:**
- Create `toydb/parser/ast_nodes.py`
- All nodes must be frozen dataclasses (`@dataclass(frozen=True)`)
- Define statement nodes:
  - `CreateTable(name: str, columns: list[str])` — untyped column list in Phase 1
  - `Insert(table: str, values: list[Expression])` — list of value expressions
  - `Select(columns: list[Expression], table: str, where: Optional[Expression])` — column list or Star, optional WHERE
  - `Delete(table: str, where: Optional[Expression])` — optional WHERE filter
- Define expression nodes:
  - `Star()` — represents `SELECT *`
  - `ColumnRef(table: Optional[str], name: str)` — column reference, optional table qualifier
  - `Literal(value: Any)` — integer, float, or string literal value
  - `BinaryOp(left: Expression, op: str, right: Expression)` — comparison and logical operators
- Define `Expression` as a type alias or union of all expression node types
- Define `Statement` as a type alias or union of all statement node types

**Dependencies:** TDB-001

**Expected result:**
A complete set of immutable AST nodes covering all Phase 1 SQL grammar. Nodes are composable — `BinaryOp` can nest `ColumnRef`, `Literal`, and other `BinaryOp` nodes.

**Acceptance criteria:**
- [ ] All nodes are frozen dataclasses (immutable after creation)
- [ ] `Select(columns=[Star()], table="users", where=None)` creates valid AST for `SELECT * FROM users`
- [ ] `BinaryOp(ColumnRef(None, "age"), ">", Literal(25))` represents `age > 25`
- [ ] Nested expressions work: `BinaryOp(BinaryOp(...), "AND", BinaryOp(...))` for compound WHERE
- [ ] All nodes importable: `from toydb.parser.ast_nodes import CreateTable, Insert, Select, Delete, Star, ColumnRef, Literal, BinaryOp`

---

### TDB-005 — Recursive descent SQL parser

**Description:**
Recursive descent parser that consumes a token list from the lexer and produces a validated AST. One method per grammar rule, with clear error messages on malformed input.

**What needs to be done:**
- Create `toydb/parser/parser.py`
- Implement `Parser` class:
  - `__init__(self, tokens: list[Token])` — store token list, initialize cursor at position 0
  - `parse() -> Statement` — entry point, dispatches to statement-specific methods
- Implement token consumption helpers:
  - `peek() -> Token` — look at current token without consuming
  - `advance() -> Token` — consume current token and return it
  - `expect(token_type, value=None) -> Token` — consume and validate, raise `ParseError` if mismatch
  - `match(*token_types) -> bool` — check if current token matches any of the given types
- Implement statement parsers:
  - `parse_create_table()` — `CREATE TABLE name (col1, col2, ...)`
  - `parse_insert()` — `INSERT INTO name VALUES (v1, v2, ...)`
  - `parse_select()` — `SELECT columns FROM table [WHERE condition]`
  - `parse_delete()` — `DELETE FROM table [WHERE condition]`
- Implement expression parser with precedence:
  - `parse_expression()` → `parse_or()` → `parse_and()` → `parse_comparison()` → `parse_primary()`
  - OR (lowest precedence) → AND → comparisons (=, !=, <, >, <=, >=) → primary (literal, column_ref, parenthesized)
- Implement column list parser: `*` or comma-separated column references
- Raise `ParseError` with position info on unexpected tokens, missing keywords, unclosed parentheses

**Dependencies:** TDB-003, TDB-004

**Expected result:**
All Phase 1 SQL statements parse into correct ASTs. Malformed SQL produces `ParseError` with the position of the offending token.

**Acceptance criteria:**
- [ ] `CREATE TABLE users (id, name, age);` → `CreateTable("users", ["id", "name", "age"])`
- [ ] `INSERT INTO users VALUES (1, 'Alice', 30);` → `Insert("users", [Literal(1), Literal("Alice"), Literal(30)])`
- [ ] `SELECT * FROM users;` → `Select([Star()], "users", None)`
- [ ] `SELECT name FROM users WHERE age > 25;` → correct AST with `BinaryOp(ColumnRef, ">", Literal)`
- [ ] `SELECT * FROM users WHERE age > 25 AND name = 'Alice';` → nested `BinaryOp` with AND
- [ ] `DELETE FROM users WHERE id = 2;` → `Delete("users", BinaryOp(...))`
- [ ] Missing semicolon raises `ParseError`
- [ ] Unknown statement keyword raises `ParseError` with position
- [ ] Unclosed parenthesis raises `ParseError`

---

## Stage 3 — Storage

### TDB-006 — In-memory table storage

**Description:**
Naive in-memory table storage using Python dicts. Each table is a named collection of rows stored as dictionaries. This will be replaced by heap file storage in Phase 3.

**What needs to be done:**
- Create `toydb/table_mem.py`
- Implement `MemoryTable` class:
  - `__init__(self, name: str, column_names: list[str])` — store table name and column definitions
  - `insert(values: list) -> None` — add a row as a dict mapping column names to values; raise `ExecutionError` if value count doesn't match column count
  - `scan() -> Iterator[dict]` — iterate all rows in insertion order
  - `delete(predicate: Callable[[dict], bool]) -> int` — remove rows matching predicate, return count of deleted rows
  - `row_count() -> int` — return current number of rows

**Dependencies:** TDB-001

**Expected result:**
A simple table abstraction that stores rows in memory. Supports insert, full scan, and predicate-based delete.

**Acceptance criteria:**
- [ ] `MemoryTable("users", ["id", "name"])` creates empty table
- [ ] `insert([1, "Alice"])` stores row as `{"id": 1, "name": "Alice"}`
- [ ] `insert([1])` with wrong value count raises `ExecutionError`
- [ ] `scan()` yields all rows in insertion order
- [ ] `delete(lambda row: row["id"] == 1)` removes matching row, returns 1
- [ ] `row_count()` returns correct count after inserts and deletes

---

### TDB-007 — Result formatter

**Description:**
Pretty-print query results as ASCII tables with borders, auto-sized columns, and a row count footer. This is the user-facing output for all SELECT queries in the REPL.

**What needs to be done:**
- Create `toydb/utils/formatter.py`
- Implement `format_results(columns: list[str], rows: list[list]) -> str`:
  - Draw ASCII table with `+`, `-`, `|` borders
  - Auto-size each column width based on the widest value (including header)
  - Left-align string values, right-align numeric values (or left-align everything for simplicity)
  - Handle empty result set — print header only with `0 row(s)` footer
  - Handle NULL values — display as `NULL`
  - Print row count footer: `N row(s)`

**Dependencies:** TDB-001

**Expected result:**
Query results display as readable ASCII tables matching the format:
```
+----+-------+-----+
| id | name  | age |
+----+-------+-----+
| 1  | Alice | 30  |
| 2  | Bob   | 22  |
+----+-------+-----+
2 row(s)
```

**Acceptance criteria:**
- [ ] Single-row result formats correctly with borders
- [ ] Multi-row result with varying column widths auto-sizes
- [ ] Empty result set prints header + `0 row(s)`
- [ ] NULL values display as `NULL`
- [ ] Column widths accommodate both header and data values
- [ ] Output is a plain string (no ANSI escape codes)

---

## Stage 4 — Execution

### TDB-008 — In-memory executor

**Description:**
Execute parsed AST statements against in-memory tables. The executor bridges the parser output to the storage layer, handling each statement type and evaluating WHERE expressions.

**What needs to be done:**
- Create `toydb/executor_mem.py`
- Implement `MemoryExecutor` class:
  - `__init__(self, tables: dict[str, MemoryTable])` — shared mutable table registry
  - `execute(stmt: Statement) -> ExecutionResult` — dispatch by statement type
- Define `ExecutionResult` dataclass or named tuple:
  - `columns: Optional[list[str]]` — column names for SELECT results
  - `rows: Optional[list[list]]` — row data for SELECT results
  - `affected_rows: Optional[int]` — count for INSERT/DELETE
  - `message: Optional[str]` — status message (e.g., "OK")
- Handle `CreateTable`:
  - Check table doesn't already exist (raise `ExecutionError` if duplicate)
  - Create new `MemoryTable` and add to registry
  - Return `"OK"` message
- Handle `Insert`:
  - Look up table (raise `ExecutionError` if not found)
  - Extract literal values from expression list
  - Call `table.insert(values)`
  - Return affected row count
- Handle `Select`:
  - Look up table (raise `ExecutionError` if not found)
  - Scan all rows
  - If WHERE present: evaluate predicate against each row, filter non-matching
  - If column list is `[Star()]`: return all columns
  - If specific columns: project only requested columns
  - Return column names and row data
- Handle `Delete`:
  - Look up table
  - Build predicate function from WHERE expression
  - Call `table.delete(predicate)`
  - Return affected row count
- Implement expression evaluator (inline or helper):
  - `evaluate_expr(expr: Expression, row: dict) -> Any`
  - Handle `Literal` — return value
  - Handle `ColumnRef` — look up column in row dict, raise `ExecutionError` if column not found
  - Handle `BinaryOp` — evaluate left and right, apply operator (=, !=, <, >, <=, >=, AND, OR)

**Dependencies:** TDB-004, TDB-006, TDB-002

**Expected result:**
All Phase 1 SQL statements execute correctly against in-memory tables. SELECT returns filtered and projected results. Expression evaluation handles comparisons and boolean logic.

**Acceptance criteria:**
- [ ] CREATE TABLE creates a new table; duplicate raises `ExecutionError`
- [ ] INSERT adds row; wrong value count raises `ExecutionError`
- [ ] INSERT into non-existent table raises `ExecutionError`
- [ ] `SELECT *` returns all columns and all rows
- [ ] `SELECT col1, col2` projects only requested columns
- [ ] `SELECT ... WHERE col = val` filters correctly
- [ ] `SELECT ... WHERE a > 1 AND b = 'x'` evaluates compound predicates
- [ ] DELETE removes matching rows and returns count
- [ ] Reference to non-existent column raises `ExecutionError`

---

## Stage 5 — Integration

### TDB-009 — REPL and CLI entry point

**Description:**
Interactive Read-Eval-Print Loop with readline support and the CLI entry point that bootstraps the system. This is the user-facing interface that ties parser, executor, and formatter together.

**What needs to be done:**

**REPL (`toydb/repl.py`):**
- Implement `REPL` class:
  - `__init__(self, executor: MemoryExecutor)` — store executor reference
  - `start() -> None` — enter interactive loop
- Read SQL input with `readline` support (command history, line editing)
- Support multi-line input: if line doesn't end with `;`, continue reading on next line with `...>` prompt
- For each complete statement:
  1. Tokenize with `Lexer`
  2. Parse with `Parser`
  3. Execute with `MemoryExecutor`
  4. Format and print result with `format_results` (for SELECT) or print status message (for DDL/DML)
- Handle errors gracefully:
  - `ParseError` — print error with position indicator
  - `ExecutionError` — print error message
  - Don't crash the REPL on errors — print and continue
- Handle `.quit` and `.exit` dot-commands to exit
- Handle `Ctrl+C` — cancel current input, print new prompt
- Handle `Ctrl+D` (EOF) — exit cleanly
- Print welcome banner on startup: `ToyDB v0.1.0` and prompt `toydb>`

**Entry point (`toydb/__main__.py`):**
- Implement `main()` function
- Parse CLI arguments with `argparse`: `--mode repl` (default and only mode in Phase 1)
- Initialize empty table registry
- Create `MemoryExecutor`
- Create and start `REPL`

**Dependencies:** TDB-005, TDB-008, TDB-007

**Expected result:**
`python -m toydb` launches an interactive SQL REPL. Users can create tables, insert data, query, and delete — all within a single session. Errors are printed without crashing.

**Acceptance criteria:**
- [ ] `python -m toydb` starts REPL with welcome banner and `toydb>` prompt
- [ ] Single-line SQL executes: `CREATE TABLE t (a, b);` → `OK`
- [ ] Multi-line SQL works: type `SELECT *` + Enter → `...>` prompt → `FROM t;` → results
- [ ] SELECT results display as formatted ASCII table
- [ ] INSERT/DELETE display affected row count
- [ ] `ParseError` prints message with position, REPL continues
- [ ] `ExecutionError` prints message, REPL continues
- [ ] `.quit` exits cleanly
- [ ] Ctrl+C cancels current input without exiting
- [ ] Ctrl+D exits cleanly
- [ ] Full demo session works:
  ```sql
  CREATE TABLE users (id, name, age);
  INSERT INTO users VALUES (1, 'Alice', 30);
  INSERT INTO users VALUES (2, 'Bob', 22);
  SELECT name FROM users WHERE age > 25;
  DELETE FROM users WHERE id = 2;
  SELECT * FROM users;
  ```

---

## Stage 6 — Testing

### TDB-010 — Phase 1 test suite

**Description:**
Unit and integration tests covering all Phase 1 components: lexer, parser, executor, and end-to-end SQL flows. The test suite validates correctness and catches regressions.

**What needs to be done:**

**Shared fixtures (`tests/conftest.py`):**
- Fixture: `executor` — returns a fresh `MemoryExecutor` with empty table registry
- Fixture: `populated_executor` — returns executor with a `users` table pre-loaded with sample rows
- Helper: `parse_and_execute(executor, sql)` — tokenize + parse + execute in one call

**Lexer tests (`tests/test_lexer.py`):**
- Tokenize `SELECT * FROM users;` — verify token types and values
- Tokenize `INSERT INTO t VALUES (1, 'hello', 3.14);` — verify literals
- Tokenize string with escaped quote: `'it''s'` → correct STRING_LIT value
- Tokenize all operators: `=`, `!=`, `<`, `>`, `<=`, `>=`
- Tokenize keywords case-insensitively: `select`, `SELECT`, `SeLeCt`
- Unknown character raises `ParseError` with correct position
- Empty input produces only EOF token
- Whitespace-only input produces only EOF token
- Multiple consecutive operators (e.g., `>=` vs `> =`)

**Parser tests (`tests/test_parser.py`):**
- Parse `CREATE TABLE` — verify AST structure with column names
- Parse `INSERT INTO ... VALUES` — verify literal values in AST
- Parse `SELECT *` — verify Star node
- Parse `SELECT col1, col2` — verify ColumnRef nodes
- Parse `SELECT ... WHERE col = val` — verify BinaryOp with correct operator
- Parse `SELECT ... WHERE a > 1 AND b = 'x'` — verify nested BinaryOp with AND
- Parse `SELECT ... WHERE a = 1 OR b = 2` — verify OR
- Parse `DELETE FROM ... WHERE` — verify Delete AST
- Missing `FROM` keyword raises `ParseError`
- Missing closing parenthesis raises `ParseError`
- Unexpected token raises `ParseError` with position
- Empty statement raises `ParseError`

**End-to-end tests (`tests/test_e2e.py`):**
- Full lifecycle: CREATE → INSERT multiple rows → SELECT * → verify all rows
- SELECT with WHERE filters correctly
- SELECT with column list projects correctly
- DELETE removes correct rows, SELECT confirms
- INSERT into non-existent table raises `ExecutionError`
- CREATE TABLE with duplicate name raises `ExecutionError`
- SELECT from non-existent table raises `ExecutionError`
- WHERE with AND/OR logic evaluates correctly
- Multiple tables can coexist independently
- Empty table returns 0 rows on SELECT

**Dependencies:** TDB-009

**Expected result:**
`pytest` runs clean with all tests passing. Tests cover happy paths, edge cases, and error conditions for every Phase 1 component.

**Acceptance criteria:**
- [ ] `pytest` exits 0 with all tests passing
- [ ] Lexer tests cover all token types, edge cases, and error conditions
- [ ] Parser tests cover all statement types and error conditions
- [ ] End-to-end tests cover full CREATE/INSERT/SELECT/DELETE lifecycle
- [ ] Error condition tests verify correct exception types and messages
- [ ] Tests run in isolation (no shared state between test functions)

---

## Phase 1 scope notes

**Total effort:** ~2–3 weeks for a single developer.

**Critical path:** TDB-001 → TDB-002 → TDB-003 → TDB-005 → TDB-009 → TDB-010

**Parallel tracks:**
- Track A (parser): TDB-002 → TDB-003 → TDB-005
- Track B (storage + formatter): TDB-006 + TDB-007 (independent, can run in parallel with Track A)
- Track C (executor): TDB-008 (needs TDB-004 + TDB-006, can overlap with TDB-005)

**Companion documents:**
- `specification/phases/phase1_sql_parser_repl.md` — detailed task breakdown
- `specification/ARCHITECTURE.md` — system architecture and file structure
- `specification/ROADMAP.md` — full 9-phase roadmap
- `specification/MISSION.md` — goals, design principles, supported SQL
