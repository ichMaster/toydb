# Phase 2: Type System + Expressions + Catalog

## Goal
Typed columns, full expression evaluator with arithmetic and logic, system catalog for metadata, ORDER BY, LIMIT, UPDATE, SHOW TABLES, DESCRIBE.

## Modules to Create

| Module              | Responsibility                                         |
|---------------------|--------------------------------------------------------|
| `toydb/types.py`    | DataType enum (INT, FLOAT, VARCHAR, BOOL), Value class |
| `toydb/expression.py` | Recursive expression evaluator                      |
| `toydb/catalog.py`  | CatalogManager: in-memory metadata registry            |

## Modules to Modify

| Module                    | Changes                                                          |
|---------------------------|------------------------------------------------------------------|
| `toydb/parser/ast_nodes.py` | Add ColumnDef with type, Update node, OrderBy, Limit           |
| `toydb/parser/parser.py`  | Parse types in CREATE TABLE, parse UPDATE, ORDER BY, LIMIT, full expression precedence |
| `toydb/executor_mem.py`   | Use expression evaluator for WHERE, support UPDATE, ORDER BY, LIMIT |
| `toydb/repl.py`           | Add .help, SHOW TABLES, DESCRIBE commands                        |
| `toydb/utils/errors.py`   | Add BindError                                                    |

## Tasks

### 1. Type system (`types.py`)
- [ ] Define `DataType` enum: INT, FLOAT, VARCHAR, BOOL
- [ ] Define `ColumnDef` frozen dataclass: `name`, `data_type`, `max_length` (for VARCHAR), `nullable`
- [ ] Define type compatibility rules: INT + FLOAT -> FLOAT, any comparison with NULL -> NULL

### 2. AST node extensions (`parser/ast_nodes.py`)
- [ ] Add `ColumnDef` node with type info to `CreateTable`
- [ ] Add `Update(table, assignments: list[Assignment], where)` node
- [ ] Add `Assignment(column: str, value: Expression)` node
- [ ] Add `OrderBy(expression, descending: bool)` to Select
- [ ] Add `limit: Optional[int]` to Select
- [ ] Add `UnaryOp(op: str, operand: Expression)` node for NOT and negation
- [ ] Add `ShowTables` statement node
- [ ] Add `DescribeTable(name: str)` statement node

### 3. Parser extensions (`parser/parser.py`)
- [ ] Parse typed CREATE TABLE: `CREATE TABLE t (id INT, name VARCHAR(100), price FLOAT, active BOOL)`
- [ ] Parse UPDATE: `UPDATE t SET col = expr [WHERE cond]`
- [ ] Parse ORDER BY with ASC/DESC
- [ ] Parse LIMIT
- [ ] Implement full expression precedence (lowest to highest):
  1. OR
  2. AND
  3. NOT
  4. Comparisons: =, !=, <, >, <=, >=
  5. Addition: +, -
  6. Multiplication: *, /
  7. Unary: -, NOT
  8. Primary: literal, column_ref, parenthesized expression
- [ ] Parse SHOW TABLES
- [ ] Parse DESCRIBE table_name
- [ ] Parse boolean literals (true, false)

### 4. Expression evaluator (`expression.py`)
- [ ] Implement `ExpressionEvaluator` class
- [ ] `evaluate(expr: Expression, row: dict, schema: list[ColumnDef]) -> Any`
- [ ] Handle arithmetic: +, -, *, /
- [ ] Handle comparisons: =, !=, <, >, <=, >=
- [ ] Handle boolean logic: AND, OR, NOT
- [ ] Handle type coercion: INT + FLOAT -> FLOAT
- [ ] Handle NULL propagation: any operation with NULL -> NULL
- [ ] Handle unary negation and NOT

### 5. Catalog manager (`catalog.py`)
- [ ] Define `TableMeta` dataclass: `table_id`, `name`, `columns: list[ColumnMeta]`
- [ ] Define `ColumnMeta` dataclass: `column_id`, `name`, `data_type`, `max_length`, `nullable`
- [ ] Implement `CatalogManager` class (in-memory for now, persisted in Phase 3)
- [ ] `create_table(name, columns) -> int` -- returns table_id
- [ ] `get_table(name) -> Optional[TableMeta]`
- [ ] `get_columns(table_id) -> list[ColumnMeta]`
- [ ] `list_tables() -> list[TableMeta]`
- [ ] `drop_table(name) -> None`
- [ ] Auto-increment table_id

### 6. Executor updates (`executor_mem.py`)
- [ ] Use `ExpressionEvaluator` for all WHERE clause evaluation
- [ ] Implement UPDATE execution: evaluate SET expressions, apply to matching rows
- [ ] Implement ORDER BY: sort result rows by key column(s), ASC/DESC
- [ ] Implement LIMIT: truncate result set
- [ ] Implement SHOW TABLES: return list from catalog
- [ ] Implement DESCRIBE: return column metadata from catalog
- [ ] Validate INSERT types against column definitions (raise ExecutionError on mismatch)

### 7. REPL updates (`repl.py`)
- [ ] Add `.help` command listing available commands
- [ ] Route SHOW TABLES and DESCRIBE through executor

### 8. Tests
- [ ] `tests/test_expression.py`: evaluate arithmetic, comparisons, boolean logic, NULL handling, type coercion
- [ ] `tests/test_catalog.py`: create/drop/list tables, column metadata
- [ ] `tests/test_parser.py` (extended): parse typed CREATE TABLE, UPDATE, ORDER BY, LIMIT
- [ ] `tests/test_e2e.py` (extended): typed inserts with validation errors, ORDER BY + LIMIT, UPDATE

## Supported SQL (additions over Phase 1)

```sql
CREATE TABLE products (id INT, name VARCHAR(100), price FLOAT, active BOOL);
INSERT INTO products VALUES (1, 'Widget', 29.99, true);
SELECT name, price * 1.2 AS with_tax FROM products WHERE active = true AND price > 10;
SELECT * FROM products ORDER BY price DESC LIMIT 5;
UPDATE products SET price = price * 0.9 WHERE id = 1;
SHOW TABLES;
DESCRIBE products;
```

## Done Criteria
- [ ] CREATE TABLE with typed columns
- [ ] INSERT validates types (error on type mismatch)
- [ ] Complex WHERE with AND/OR/NOT and arithmetic
- [ ] ORDER BY (ASC/DESC) and LIMIT work
- [ ] UPDATE with expressions (SET price = price * 0.9)
- [ ] SHOW TABLES and DESCRIBE return correct metadata
- [ ] All tests pass
