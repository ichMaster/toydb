# ToyDB

ToyDB is an educational relational database server written in Python. It implements the core concepts found in production systems like MySQL, PostgreSQL, and SQLite — from SQL parsing down to disk page management — in a codebase small enough for one person to understand completely.

## Quick Start

```bash
# Clone and set up
git clone https://github.com/ichMaster/toydb.git
cd toydb
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Launch the REPL
toydb
```

## Example Session

```
toydb> CREATE TABLE users (id, name, age);
OK
toydb> INSERT INTO users VALUES (1, 'Alice', 30);
OK (1 row)
toydb> INSERT INTO users VALUES (2, 'Bob', 22);
OK (1 row)
toydb> SELECT name FROM users WHERE age > 25;
+-------+
| name  |
+-------+
| Alice |
+-------+
1 row(s)
toydb> DELETE FROM users WHERE id = 2;
OK (1 row)
toydb> SELECT * FROM users;
+----+-------+-----+
| id | name  | age |
+----+-------+-----+
| 1  | Alice | 30  |
+----+-------+-----+
1 row(s)
toydb> .quit
```

## Running Tests

```bash
pytest
pytest tests/test_lexer.py -v      # single file
pytest tests/test_e2e.py::test_full_lifecycle -v  # single test
```

## Documentation

See the [documentation/](documentation/) folder for detailed guides:

- [Getting Started](documentation/getting-started.md) — installation and first session
- [SQL Reference](documentation/sql-reference.md) — supported statements and syntax
- [Architecture](documentation/architecture.md) — component overview and data flow

## Project Structure

```
toydb/              # main package
  parser/           # lexer, parser, AST nodes
  utils/            # error hierarchy, result formatter
  executor_mem.py   # in-memory SQL executor
  table_mem.py      # in-memory table storage
  repl.py           # interactive REPL
tests/              # pytest test suite
specification/      # design docs and roadmap
documentation/      # user-facing documentation
```

## Design Principles

- **Clarity over performance** — code is written to teach, not to be fast
- **Standard library only** — no third-party dependencies in core engine
- **Incremental build** — each phase produces a runnable system
- **Small modules** — each file under 300 lines

## License

MIT
