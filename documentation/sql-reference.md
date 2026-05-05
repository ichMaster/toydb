# SQL Reference

This document covers all SQL supported in Phase 1 of ToyDB.

## Statements

### CREATE TABLE

Create a new table with named columns (untyped in Phase 1).

```sql
CREATE TABLE table_name (column1, column2, ...);
```

Example:
```sql
CREATE TABLE users (id, name, age);
```

### INSERT INTO

Insert a row of values into an existing table.

```sql
INSERT INTO table_name VALUES (value1, value2, ...);
```

The number of values must match the number of columns in the table.

Examples:
```sql
INSERT INTO users VALUES (1, 'Alice', 30);
INSERT INTO users VALUES (2, 'Bob', 22);
```

### SELECT

Query rows from a table with optional filtering.

```sql
SELECT * FROM table_name;
SELECT column1, column2 FROM table_name;
SELECT columns FROM table_name WHERE condition;
```

Examples:
```sql
SELECT * FROM users;
SELECT name, age FROM users;
SELECT * FROM users WHERE age > 25;
SELECT name FROM users WHERE age > 20 AND name = 'Alice';
```

### DELETE

Remove rows from a table with optional filtering.

```sql
DELETE FROM table_name;
DELETE FROM table_name WHERE condition;
```

Examples:
```sql
DELETE FROM users WHERE id = 2;
DELETE FROM users WHERE age < 18;
```

## Expressions

### Literals

| Type | Examples |
|------|----------|
| Integer | `42`, `0`, `999` |
| Float | `3.14`, `0.5` |
| String | `'hello'`, `'it''s'` (escaped quote) |

### Column References

Column names used in WHERE clauses and SELECT lists:

```sql
SELECT name FROM users WHERE age > 25;
```

### Comparison Operators

| Operator | Meaning |
|----------|---------|
| `=` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `>` | Greater than |
| `<=` | Less than or equal |
| `>=` | Greater than or equal |

### Logical Operators

| Operator | Meaning |
|----------|---------|
| `AND` | Both conditions must be true |
| `OR` | Either condition must be true |

Precedence (lowest to highest): OR, AND, comparisons.

Example:
```sql
SELECT * FROM users WHERE age > 20 AND name = 'Alice';
SELECT * FROM users WHERE age < 18 OR age > 65;
```

## Limitations (Phase 1)

- No column types (all values stored as Python objects)
- No UPDATE statement
- No ORDER BY or LIMIT
- No JOIN
- No aggregate functions (COUNT, SUM, etc.)
- No NULL literal in INSERT (but NULL can appear in results)
- No sub-queries
- Data is in-memory only (lost on exit)
- Single table per query
