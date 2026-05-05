from dataclasses import dataclass
from enum import Enum, auto

from toydb.utils.errors import ParseError


class TokenType(Enum):
    KEYWORD = auto()
    IDENTIFIER = auto()
    INTEGER_LIT = auto()
    FLOAT_LIT = auto()
    STRING_LIT = auto()
    OPERATOR = auto()
    COMMA = auto()
    LPAREN = auto()
    RPAREN = auto()
    SEMICOLON = auto()
    STAR = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    position: int


KEYWORDS = frozenset({
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES",
    "CREATE", "TABLE", "DELETE", "AND", "OR", "NOT",
})


class Lexer:
    def __init__(self, sql: str):
        self._sql = sql
        self._pos = 0

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self._pos < len(self._sql):
            ch = self._sql[self._pos]

            if ch.isspace():
                self._pos += 1
                continue

            if ch == '\'':
                tokens.append(self._read_string())
            elif ch.isdigit():
                tokens.append(self._read_number())
            elif ch.isalpha() or ch == '_':
                tokens.append(self._read_word())
            elif ch == '(':
                tokens.append(Token(TokenType.LPAREN, '(', self._pos))
                self._pos += 1
            elif ch == ')':
                tokens.append(Token(TokenType.RPAREN, ')', self._pos))
                self._pos += 1
            elif ch == '*':
                tokens.append(Token(TokenType.STAR, '*', self._pos))
                self._pos += 1
            elif ch == ',':
                tokens.append(Token(TokenType.COMMA, ',', self._pos))
                self._pos += 1
            elif ch == ';':
                tokens.append(Token(TokenType.SEMICOLON, ';', self._pos))
                self._pos += 1
            elif ch in ('=', '!', '<', '>'):
                tokens.append(self._read_operator())
            else:
                raise ParseError(f"Unknown character '{ch}'", position=self._pos)

        tokens.append(Token(TokenType.EOF, '', self._pos))
        return tokens

    def _read_string(self) -> Token:
        start = self._pos
        self._pos += 1  # skip opening quote
        value: list[str] = []
        while self._pos < len(self._sql):
            ch = self._sql[self._pos]
            if ch == '\'':
                if self._pos + 1 < len(self._sql) and self._sql[self._pos + 1] == '\'':
                    value.append('\'')
                    self._pos += 2
                else:
                    self._pos += 1  # skip closing quote
                    return Token(TokenType.STRING_LIT, ''.join(value), start)
            else:
                value.append(ch)
                self._pos += 1
        raise ParseError("Unterminated string literal", position=start)

    def _read_number(self) -> Token:
        start = self._pos
        has_dot = False
        while self._pos < len(self._sql) and (self._sql[self._pos].isdigit() or self._sql[self._pos] == '.'):
            if self._sql[self._pos] == '.':
                if has_dot:
                    break
                has_dot = True
            self._pos += 1
        value = self._sql[start:self._pos]
        token_type = TokenType.FLOAT_LIT if has_dot else TokenType.INTEGER_LIT
        return Token(token_type, value, start)

    def _read_word(self) -> Token:
        start = self._pos
        while self._pos < len(self._sql) and (self._sql[self._pos].isalnum() or self._sql[self._pos] == '_'):
            self._pos += 1
        value = self._sql[start:self._pos]
        if value.upper() in KEYWORDS:
            return Token(TokenType.KEYWORD, value.upper(), start)
        return Token(TokenType.IDENTIFIER, value, start)

    def _read_operator(self) -> Token:
        start = self._pos
        ch = self._sql[self._pos]
        if ch == '!' and self._pos + 1 < len(self._sql) and self._sql[self._pos + 1] == '=':
            self._pos += 2
            return Token(TokenType.OPERATOR, '!=', start)
        if ch == '<' and self._pos + 1 < len(self._sql) and self._sql[self._pos + 1] == '=':
            self._pos += 2
            return Token(TokenType.OPERATOR, '<=', start)
        if ch == '>' and self._pos + 1 < len(self._sql) and self._sql[self._pos + 1] == '=':
            self._pos += 2
            return Token(TokenType.OPERATOR, '>=', start)
        if ch == '!':
            raise ParseError(f"Unknown character '!'", position=self._pos)
        self._pos += 1
        return Token(TokenType.OPERATOR, ch, start)
