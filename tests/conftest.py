import pytest

from toydb.executor_mem import MemoryExecutor
from toydb.parser.lexer import Lexer
from toydb.parser.parser import Parser


@pytest.fixture
def executor():
    return MemoryExecutor()


@pytest.fixture
def populated_executor():
    ex = MemoryExecutor()
    parse_and_execute(ex, "CREATE TABLE users (id, name, age);")
    parse_and_execute(ex, "INSERT INTO users VALUES (1, 'Alice', 30);")
    parse_and_execute(ex, "INSERT INTO users VALUES (2, 'Bob', 22);")
    parse_and_execute(ex, "INSERT INTO users VALUES (3, 'Charlie', 35);")
    return ex


def parse_and_execute(executor, sql):
    tokens = Lexer(sql).tokenize()
    stmt = Parser(tokens).parse()
    return executor.execute(stmt)
