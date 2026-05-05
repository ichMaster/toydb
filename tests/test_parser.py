import pytest

from toydb.parser.ast_nodes import (
    BinaryOp, ColumnRef, CreateTable, Delete, Insert, Literal, Select, Star,
)
from toydb.parser.lexer import Lexer
from toydb.parser.parser import Parser
from toydb.utils.errors import ParseError


def parse(sql):
    tokens = Lexer(sql).tokenize()
    return Parser(tokens).parse()


def test_create_table():
    stmt = parse("CREATE TABLE users (id, name, age);")
    assert isinstance(stmt, CreateTable)
    assert stmt.name == "users"
    assert stmt.columns == ["id", "name", "age"]


def test_insert():
    stmt = parse("INSERT INTO users VALUES (1, 'Alice', 30);")
    assert isinstance(stmt, Insert)
    assert stmt.table == "users"
    assert stmt.values == [Literal(1), Literal("Alice"), Literal(30)]


def test_select_star():
    stmt = parse("SELECT * FROM users;")
    assert isinstance(stmt, Select)
    assert stmt.columns == [Star()]
    assert stmt.table == "users"
    assert stmt.where is None


def test_select_columns():
    stmt = parse("SELECT name, age FROM users;")
    assert isinstance(stmt, Select)
    assert stmt.columns == [ColumnRef(None, "name"), ColumnRef(None, "age")]


def test_select_where():
    stmt = parse("SELECT name FROM users WHERE age > 25;")
    assert isinstance(stmt, Select)
    assert isinstance(stmt.where, BinaryOp)
    assert stmt.where.op == ">"
    assert stmt.where.left == ColumnRef(None, "age")
    assert stmt.where.right == Literal(25)


def test_select_where_and():
    stmt = parse("SELECT * FROM users WHERE age > 1 AND name = 'x';")
    assert isinstance(stmt.where, BinaryOp)
    assert stmt.where.op == "AND"
    assert isinstance(stmt.where.left, BinaryOp)
    assert isinstance(stmt.where.right, BinaryOp)


def test_select_where_or():
    stmt = parse("SELECT * FROM users WHERE a = 1 OR b = 2;")
    assert isinstance(stmt.where, BinaryOp)
    assert stmt.where.op == "OR"


def test_delete_where():
    stmt = parse("DELETE FROM users WHERE id = 2;")
    assert isinstance(stmt, Delete)
    assert stmt.table == "users"
    assert isinstance(stmt.where, BinaryOp)


def test_missing_from():
    with pytest.raises(ParseError):
        parse("SELECT * users;")


def test_missing_closing_paren():
    with pytest.raises(ParseError):
        parse("CREATE TABLE t (a, b;")


def test_unexpected_token():
    with pytest.raises(ParseError) as exc_info:
        parse("123;")
    assert exc_info.value.position >= 0


def test_empty_statement():
    with pytest.raises(ParseError):
        parse(";")
