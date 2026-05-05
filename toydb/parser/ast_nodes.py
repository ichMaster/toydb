from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union


@dataclass(frozen=True)
class Star:
    pass


@dataclass(frozen=True)
class ColumnRef:
    table: Optional[str]
    name: str


@dataclass(frozen=True)
class Literal:
    value: Any


@dataclass(frozen=True)
class BinaryOp:
    left: Expression
    op: str
    right: Expression


Expression = Union[Star, ColumnRef, Literal, BinaryOp]


@dataclass(frozen=True)
class CreateTable:
    name: str
    columns: list[str]


@dataclass(frozen=True)
class Insert:
    table: str
    values: list[Expression]


@dataclass(frozen=True)
class Select:
    columns: list[Expression]
    table: str
    where: Optional[Expression]


@dataclass(frozen=True)
class Delete:
    table: str
    where: Optional[Expression]


Statement = Union[CreateTable, Insert, Select, Delete]
