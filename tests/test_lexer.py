import pytest

from toydb.parser.lexer import Lexer, TokenType
from toydb.utils.errors import ParseError


def test_tokenize_select_star():
    tokens = Lexer("SELECT * FROM users;").tokenize()
    types = [t.type for t in tokens]
    assert types == [
        TokenType.KEYWORD, TokenType.STAR, TokenType.KEYWORD,
        TokenType.IDENTIFIER, TokenType.SEMICOLON, TokenType.EOF,
    ]
    assert tokens[0].value == "SELECT"
    assert tokens[3].value == "users"


def test_tokenize_insert_with_literals():
    tokens = Lexer("INSERT INTO t VALUES (1, 'hello', 3.14);").tokenize()
    assert tokens[5].type == TokenType.INTEGER_LIT
    assert tokens[5].value == "1"
    assert tokens[7].type == TokenType.STRING_LIT
    assert tokens[7].value == "hello"
    assert tokens[9].type == TokenType.FLOAT_LIT
    assert tokens[9].value == "3.14"


def test_string_escaped_quote():
    tokens = Lexer("'it''s'").tokenize()
    assert tokens[0].type == TokenType.STRING_LIT
    assert tokens[0].value == "it's"


def test_all_operators():
    tokens = Lexer("= != < > <= >=").tokenize()
    ops = [t.value for t in tokens if t.type == TokenType.OPERATOR]
    assert ops == ["=", "!=", "<", ">", "<=", ">="]


def test_keywords_case_insensitive():
    for kw in ["select", "SELECT", "SeLeCt"]:
        tokens = Lexer(kw).tokenize()
        assert tokens[0].type == TokenType.KEYWORD
        assert tokens[0].value == "SELECT"


def test_unknown_character():
    with pytest.raises(ParseError) as exc_info:
        Lexer("@").tokenize()
    assert exc_info.value.position == 0


def test_empty_input():
    tokens = Lexer("").tokenize()
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.EOF


def test_whitespace_only():
    tokens = Lexer("   \t\n  ").tokenize()
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.EOF


def test_identifier_preserves_case():
    tokens = Lexer("myTable").tokenize()
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].value == "myTable"


def test_greater_equal_vs_greater_space_equal():
    tokens = Lexer(">=").tokenize()
    assert tokens[0].value == ">="

    tokens = Lexer("> =").tokenize()
    assert tokens[0].value == ">"
    assert tokens[1].value == "="
