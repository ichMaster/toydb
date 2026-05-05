import pytest

from tests.conftest import parse_and_execute
from toydb.utils.errors import ExecutionError


def test_full_lifecycle(executor):
    parse_and_execute(executor, "CREATE TABLE users (id, name, age);")
    parse_and_execute(executor, "INSERT INTO users VALUES (1, 'Alice', 30);")
    parse_and_execute(executor, "INSERT INTO users VALUES (2, 'Bob', 22);")

    result = parse_and_execute(executor, "SELECT * FROM users;")
    assert result.columns == ["id", "name", "age"]
    assert len(result.rows) == 2
    assert result.rows[0] == [1, "Alice", 30]
    assert result.rows[1] == [2, "Bob", 22]


def test_select_where_filters(populated_executor):
    result = parse_and_execute(populated_executor, "SELECT * FROM users WHERE age > 25;")
    assert len(result.rows) == 2
    names = [r[1] for r in result.rows]
    assert "Alice" in names
    assert "Charlie" in names


def test_select_column_projection(populated_executor):
    result = parse_and_execute(populated_executor, "SELECT name, age FROM users;")
    assert result.columns == ["name", "age"]
    assert result.rows[0] == ["Alice", 30]


def test_delete_and_verify(populated_executor):
    result = parse_and_execute(populated_executor, "DELETE FROM users WHERE id = 2;")
    assert result.affected_rows == 1

    result = parse_and_execute(populated_executor, "SELECT * FROM users;")
    assert len(result.rows) == 2
    ids = [r[0] for r in result.rows]
    assert 2 not in ids


def test_insert_nonexistent_table(executor):
    with pytest.raises(ExecutionError):
        parse_and_execute(executor, "INSERT INTO missing VALUES (1);")


def test_create_duplicate_table(executor):
    parse_and_execute(executor, "CREATE TABLE t (a);")
    with pytest.raises(ExecutionError):
        parse_and_execute(executor, "CREATE TABLE t (a);")


def test_select_nonexistent_table(executor):
    with pytest.raises(ExecutionError):
        parse_and_execute(executor, "SELECT * FROM missing;")


def test_where_and_or(executor):
    parse_and_execute(executor, "CREATE TABLE t (a, b);")
    parse_and_execute(executor, "INSERT INTO t VALUES (1, 10);")
    parse_and_execute(executor, "INSERT INTO t VALUES (2, 20);")
    parse_and_execute(executor, "INSERT INTO t VALUES (3, 30);")

    result = parse_and_execute(executor, "SELECT * FROM t WHERE a = 1 OR b = 30;")
    assert len(result.rows) == 2

    result = parse_and_execute(executor, "SELECT * FROM t WHERE a > 1 AND b < 30;")
    assert len(result.rows) == 1
    assert result.rows[0][0] == 2


def test_multiple_tables(executor):
    parse_and_execute(executor, "CREATE TABLE a (x);")
    parse_and_execute(executor, "CREATE TABLE b (y);")
    parse_and_execute(executor, "INSERT INTO a VALUES (1);")
    parse_and_execute(executor, "INSERT INTO b VALUES (2);")

    ra = parse_and_execute(executor, "SELECT * FROM a;")
    rb = parse_and_execute(executor, "SELECT * FROM b;")
    assert ra.rows == [[1]]
    assert rb.rows == [[2]]


def test_empty_table_select(executor):
    parse_and_execute(executor, "CREATE TABLE t (a);")
    result = parse_and_execute(executor, "SELECT * FROM t;")
    assert result.rows == []
