# Getting Started

## Prerequisites

- Python 3.11 or later
- pip (comes with Python)

## Installation

```bash
git clone https://github.com/ichMaster/toydb.git
cd toydb
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

After installation, `toydb` is available as a CLI command:

```bash
toydb          # launch REPL
python -m toydb  # alternative
```

## Your First Session

Launch the REPL:

```
$ toydb
ToyDB v0.1.0
Type .quit or .exit to leave.

toydb>
```

Create a table and insert data:

```sql
toydb> CREATE TABLE books (id, title, year);
OK
toydb> INSERT INTO books VALUES (1, 'The Hobbit', 1937);
OK (1 row)
toydb> INSERT INTO books VALUES (2, '1984', 1949);
OK (1 row)
toydb> INSERT INTO books VALUES (3, 'Dune', 1965);
OK (1 row)
```

Query the data:

```sql
toydb> SELECT * FROM books;
+----+------------+------+
| id | title      | year |
+----+------------+------+
| 1  | The Hobbit | 1937 |
| 2  | 1984       | 1949 |
| 3  | Dune       | 1965 |
+----+------------+------+
3 row(s)

toydb> SELECT title FROM books WHERE year > 1940;
+-------+
| title |
+-------+
| 1984  |
| Dune  |
+-------+
2 row(s)
```

Delete rows:

```sql
toydb> DELETE FROM books WHERE id = 2;
OK (1 row)
```

## Multi-Line Input

If your SQL doesn't end with `;`, the REPL waits for more input:

```
toydb> SELECT *
...> FROM books
...> WHERE year > 1940;
```

## Dot-Commands

| Command | Action |
|---------|--------|
| `.quit` | Exit the REPL |
| `.exit` | Exit the REPL |

## Error Handling

Errors don't crash the REPL — they print a message and you can continue:

```
toydb> SELECT * FROM nonexistent;
Error: Table 'nonexistent' does not exist
toydb> SELCT * FROM books;
Parse error: Expected statement keyword, got 'SELCT' at position 0
toydb>
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+C | Cancel current input |
| Ctrl+D | Exit the REPL |
| Up/Down arrows | Command history (readline) |
