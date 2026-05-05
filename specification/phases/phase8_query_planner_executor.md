# Phase 8: Query Planner + Volcano Executor

## Goal
Logical plan tree from AST. Rule-based optimizer. Volcano iterator execution model. JOIN support. EXPLAIN command. Replaces `executor_mem.py` entirely.

## Modules to Create

| Module                      | Responsibility                         |
|-----------------------------|----------------------------------------|
| `toydb/planner/__init__.py` | Package init                           |
| `toydb/planner/planner.py`  | AST -> logical plan tree               |
| `toydb/planner/optimizer.py` | Rule-based optimization passes        |
| `toydb/planner/plan_nodes.py` | Plan node dataclasses                |
| `toydb/executor.py`         | Volcano iterators (replaces executor_mem.py) |

## Modules to Remove

| Module                 | Replaced By                       |
|------------------------|-----------------------------------|
| `toydb/executor_mem.py` | `toydb/executor.py` (Volcano iterators) |

## Modules to Modify

| Module                      | Changes                              |
|-----------------------------|--------------------------------------|
| `toydb/parser/parser.py`    | Parse JOIN, GROUP BY, EXPLAIN        |
| `toydb/parser/ast_nodes.py` | Add Join, GroupBy, Explain AST nodes |
| `toydb/repl.py`             | Route through planner -> executor    |

## Tasks

### 1. AST and parser additions
- [ ] Add `JoinClause(table: str, alias: Optional[str], condition: Expression, join_type: str)` to ast_nodes.py
- [ ] Add `joins: list[JoinClause]` field to Select node
- [ ] Add `group_by: list[Expression]` field to Select node
- [ ] Add `Explain(statement: Statement)` node
- [ ] Add `AggregateFunc(name: str, arg: Expression)` node for COUNT, SUM, AVG, MIN, MAX
- [ ] Parse `JOIN table ON condition` in parser.py
- [ ] Parse `GROUP BY col1, col2`
- [ ] Parse `EXPLAIN SELECT ...`
- [ ] Parse table aliases: `FROM users u`
- [ ] Parse aggregate functions: `COUNT(*)`, `SUM(col)`, `AVG(col)`, `MIN(col)`, `MAX(col)`

### 2. Plan nodes (`planner/plan_nodes.py`)
- [ ] All nodes are frozen dataclasses
- [ ] `SeqScanNode(table_id: int, table_name: str)`
- [ ] `IndexScanNode(table_id: int, index_id: int, key_range: tuple[Optional, Optional])`
- [ ] `FilterNode(child: PlanNode, predicate: Expression)`
- [ ] `ProjectNode(child: PlanNode, columns: list[Expression], aliases: list[Optional[str]])`
- [ ] `SortNode(child: PlanNode, key: Expression, descending: bool)`
- [ ] `LimitNode(child: PlanNode, count: int)`
- [ ] `NestedLoopJoinNode(left: PlanNode, right: PlanNode, condition: Expression, join_type: str)`
- [ ] `AggregateNode(child: PlanNode, group_by: list[Expression], aggregates: list[AggregateExpr])`
- [ ] `InsertNode`, `UpdateNode`, `DeleteNode` for DML operations

### 3. Logical planner (`planner/planner.py`)
- [ ] Implement `Planner` class
- [ ] `plan(stmt: Statement) -> PlanNode` -- convert AST to plan tree
- [ ] SELECT: SeqScan -> Filter (WHERE) -> Project (columns) -> Sort (ORDER BY) -> Limit
- [ ] SELECT with JOIN: build NestedLoopJoinNode with scans as children
- [ ] SELECT with GROUP BY: add AggregateNode
- [ ] INSERT: InsertNode wrapping values
- [ ] UPDATE: scan + filter -> UpdateNode
- [ ] DELETE: scan + filter -> DeleteNode

### 4. Optimizer (`planner/optimizer.py`)
- [ ] Rules applied in order, each is a tree-transforming function:
- [ ] **Predicate pushdown**: if a FilterNode sits above a JoinNode and the predicate references columns from only one side, push it below the join to that side
- [ ] **Index selection**: if a FilterNode sits directly above a SeqScanNode and the predicate is a simple comparison on an indexed column, replace both with IndexScanNode
- [ ] **Projection pruning**: walk plan top-down, collect which columns are referenced by upstream nodes, remove unreferenced columns from scan output
- [ ] Each rule: `optimize_rule(plan_node) -> plan_node` -- walks tree, returns transformed copy

### 5. Volcano executor (`executor.py`)
- [ ] Define abstract `Executor` base class:
  ```python
  class Executor(ABC):
      def open(self) -> None: ...
      def next(self) -> Optional[tuple]: ...
      def close(self) -> None: ...
  ```
- [ ] `SeqScanExecutor`: opens heap file, next() returns one tuple per page slot
- [ ] `IndexScanExecutor`: traverses B-tree, fetches matching tuples from heap
- [ ] `FilterExecutor`: calls child.next(), evaluates predicate, skips non-matching rows
- [ ] `ProjectExecutor`: calls child.next(), extracts requested columns
- [ ] `SortExecutor`: materializes all child tuples in open(), sorts, yields in next()
- [ ] `LimitExecutor`: counts calls to next(), returns None after limit reached
- [ ] `NestedLoopJoinExecutor`: for each left tuple, scans all right tuples, emits matches
- [ ] `AggregateExecutor`: materializes groups in open(), yields one tuple per group in next()
- [ ] `InsertExecutor`: writes tuples to heap file (and indexes), returns affected count
- [ ] `UpdateExecutor`: reads via child, modifies tuples in-place, returns affected count
- [ ] `DeleteExecutor`: reads via child, marks tuples as deleted, returns affected count
- [ ] Executor factory: `build_executor(plan_node) -> Executor` -- recursive mapping from plan nodes

### 6. EXPLAIN command
- [ ] Print the plan tree as indented text showing node types and parameters
- [ ] Show whether IndexScan or SeqScan was chosen
- [ ] Show predicate pushdown results

### 7. Wiring (`repl.py` and entry point)
- [ ] Route all statements through: Parser -> Planner -> Optimizer -> Executor
- [ ] Remove all references to `executor_mem.py`
- [ ] Delete `executor_mem.py`

### 8. Tests
- [ ] `tests/test_planner.py`: verify AST -> plan tree for SELECT, JOIN, ORDER BY, GROUP BY
- [ ] `tests/test_optimizer.py`:
  - Predicate pushdown: filter above join moves below
  - Index selection: SeqScan + Filter replaced by IndexScan
  - Projection pruning: unreferenced columns removed
- [ ] `tests/test_executor.py`:
  - SeqScanExecutor returns all rows
  - FilterExecutor filters correctly
  - NestedLoopJoinExecutor produces correct join results
  - SortExecutor sorts correctly
  - LimitExecutor stops after N rows
  - AggregateExecutor computes COUNT, SUM, AVG, MIN, MAX
- [ ] `tests/test_e2e.py` (extended): multi-table JOIN queries, GROUP BY with aggregates, EXPLAIN output

## Supported SQL (additions)

```sql
SELECT u.name, o.total
  FROM users u
  JOIN orders o ON u.id = o.user_id
  WHERE o.total > 100
  ORDER BY o.total DESC
  LIMIT 10;

SELECT department, COUNT(*), AVG(salary)
  FROM employees
  GROUP BY department;

EXPLAIN SELECT * FROM users WHERE age > 30;
```

## Done Criteria
- [ ] All SELECT/INSERT/UPDATE/DELETE use the Volcano executor pipeline
- [ ] `executor_mem.py` removed; `executor.py` is the single execution path
- [ ] JOIN works for two tables with ON condition
- [ ] GROUP BY with COUNT, SUM, AVG, MIN, MAX
- [ ] EXPLAIN prints the plan tree
- [ ] Optimizer applies predicate pushdown and index selection
- [ ] All tests pass
