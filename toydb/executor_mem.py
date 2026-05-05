from dataclasses import dataclass
from typing import Any, Optional

from toydb.parser.ast_nodes import (
    BinaryOp, ColumnRef, CreateTable, Delete, Expression, Insert, Literal,
    Select, Star, Statement,
)
from toydb.table_mem import MemoryTable
from toydb.utils.errors import ExecutionError


@dataclass
class ExecutionResult:
    columns: Optional[list[str]] = None
    rows: Optional[list[list]] = None
    affected_rows: Optional[int] = None
    message: Optional[str] = None


class MemoryExecutor:
    def __init__(self, tables: dict[str, MemoryTable] | None = None):
        self.tables: dict[str, MemoryTable] = tables if tables is not None else {}

    def execute(self, stmt: Statement) -> ExecutionResult:
        if isinstance(stmt, CreateTable):
            return self._execute_create(stmt)
        if isinstance(stmt, Insert):
            return self._execute_insert(stmt)
        if isinstance(stmt, Select):
            return self._execute_select(stmt)
        if isinstance(stmt, Delete):
            return self._execute_delete(stmt)
        raise ExecutionError(f"Unknown statement type: {type(stmt).__name__}")

    def _execute_create(self, stmt: CreateTable) -> ExecutionResult:
        if stmt.name in self.tables:
            raise ExecutionError(f"Table '{stmt.name}' already exists")
        self.tables[stmt.name] = MemoryTable(stmt.name, stmt.columns)
        return ExecutionResult(message="OK")

    def _execute_insert(self, stmt: Insert) -> ExecutionResult:
        table = self._get_table(stmt.table)
        values = [self._eval_expr(v, {}) for v in stmt.values]
        table.insert(values)
        return ExecutionResult(affected_rows=1)

    def _execute_select(self, stmt: Select) -> ExecutionResult:
        table = self._get_table(stmt.table)
        rows = list(table.scan())
        if stmt.where is not None:
            rows = [r for r in rows if self._eval_expr(stmt.where, r)]
        if len(stmt.columns) == 1 and isinstance(stmt.columns[0], Star):
            columns = table.column_names
            result_rows = [[row[col] for col in columns] for row in rows]
        else:
            columns = []
            for col_expr in stmt.columns:
                if isinstance(col_expr, ColumnRef):
                    columns.append(col_expr.name)
                else:
                    columns.append(str(col_expr))
            result_rows = [[self._eval_expr(c, row) for c in stmt.columns] for row in rows]
        return ExecutionResult(columns=columns, rows=result_rows)

    def _execute_delete(self, stmt: Delete) -> ExecutionResult:
        table = self._get_table(stmt.table)
        if stmt.where is None:
            count = table.delete(lambda _: True)
        else:
            count = table.delete(lambda row: self._eval_expr(stmt.where, row))
        return ExecutionResult(affected_rows=count)

    def _get_table(self, name: str) -> MemoryTable:
        if name not in self.tables:
            raise ExecutionError(f"Table '{name}' does not exist")
        return self.tables[name]

    def _eval_expr(self, expr: Expression, row: dict) -> Any:
        if isinstance(expr, Literal):
            return expr.value
        if isinstance(expr, ColumnRef):
            if expr.name not in row:
                raise ExecutionError(f"Column '{expr.name}' not found")
            return row[expr.name]
        if isinstance(expr, BinaryOp):
            left = self._eval_expr(expr.left, row)
            right = self._eval_expr(expr.right, row)
            return self._apply_op(expr.op, left, right)
        raise ExecutionError(f"Cannot evaluate expression: {type(expr).__name__}")

    def _apply_op(self, op: str, left: Any, right: Any) -> Any:
        if op == "=":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right
        if op == "AND":
            return left and right
        if op == "OR":
            return left or right
        raise ExecutionError(f"Unknown operator: {op}")
