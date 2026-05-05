# Architecture

## Data Flow

A SQL statement flows through four components in Phase 1:

```
SQL string
    |
    v
[Lexer]        toydb/parser/lexer.py
    | tokens
    v
[Parser]       toydb/parser/parser.py
    | AST
    v
[Executor]     toydb/executor_mem.py
    | result
    v
[Formatter]    toydb/utils/formatter.py
    |
    v
ASCII output
```

## Components

### Lexer (`toydb/parser/lexer.py`)

Converts a SQL string into a list of typed tokens. Character-by-character scanning handles keywords, identifiers, literals, operators, and special characters.

Key types:
- `TokenType` — enum of all token categories
- `Token` — frozen dataclass with type, value, and position
- `Lexer` — stateful scanner with `tokenize()` method

### Parser (`toydb/parser/parser.py`)

Recursive descent parser that consumes tokens and produces an AST. One method per grammar rule with expression precedence (OR > AND > comparison > primary).

Key types:
- `Parser` — stateful parser with `parse()` entry point
- Helpers: `peek()`, `advance()`, `_expect()`

### AST Nodes (`toydb/parser/ast_nodes.py`)

Frozen dataclasses representing parsed SQL structure:

- **Statements:** `CreateTable`, `Insert`, `Select`, `Delete`
- **Expressions:** `Star`, `ColumnRef`, `Literal`, `BinaryOp`

All nodes are immutable after creation.

### Executor (`toydb/executor_mem.py`)

Executes AST statements against in-memory tables. Dispatches by statement type, evaluates WHERE expressions recursively, and returns `ExecutionResult`.

Key types:
- `MemoryExecutor` — takes a table registry, executes statements
- `ExecutionResult` — holds columns/rows for SELECT, or affected count for DML

### Table Storage (`toydb/table_mem.py`)

Naive in-memory storage using Python lists of dicts. Each table has a name, column list, and ordered row collection.

Key types:
- `MemoryTable` — insert, scan, delete, row_count

### Formatter (`toydb/utils/formatter.py`)

Renders query results as ASCII tables with auto-sized columns and row count footer.

### REPL (`toydb/repl.py`)

Interactive loop with readline support, multi-line input, dot-commands, and error handling. Ties all components together.

### Error Hierarchy (`toydb/utils/errors.py`)

- `ToyDBError` — base exception
- `ParseError` — syntax errors with position
- `ExecutionError` — runtime errors

## Module Map

```
toydb/
  __init__.py          # package root, __version__
  __main__.py          # CLI entry point (argparse)
  repl.py              # REPL loop
  executor_mem.py      # statement execution
  table_mem.py         # in-memory table storage
  parser/
    __init__.py
    lexer.py           # tokenizer
    parser.py          # recursive descent parser
    ast_nodes.py       # AST dataclasses
  utils/
    __init__.py
    errors.py          # exception hierarchy
    formatter.py       # ASCII table output
```
