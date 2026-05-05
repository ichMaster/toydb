from toydb.parser.ast_nodes import (
    BinaryOp, ColumnRef, CreateTable, Delete, Expression, Insert, Literal,
    Select, Star, Statement,
)
from toydb.parser.lexer import Token, TokenType
from toydb.utils.errors import ParseError


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0

    def parse(self) -> Statement:
        token = self.peek()
        if token.type == TokenType.EOF:
            raise ParseError("Empty statement", position=token.position)
        if token.type != TokenType.KEYWORD:
            raise ParseError(
                f"Expected statement keyword, got '{token.value}'",
                position=token.position,
            )
        keyword = token.value
        if keyword == "CREATE":
            stmt = self._parse_create_table()
        elif keyword == "INSERT":
            stmt = self._parse_insert()
        elif keyword == "SELECT":
            stmt = self._parse_select()
        elif keyword == "DELETE":
            stmt = self._parse_delete()
        else:
            raise ParseError(
                f"Unknown statement keyword '{keyword}'",
                position=token.position,
            )
        self._expect(TokenType.SEMICOLON)
        return stmt

    def peek(self) -> Token:
        return self._tokens[self._pos]

    def advance(self) -> Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _expect(self, token_type: TokenType, value: str | None = None) -> Token:
        token = self.peek()
        if token.type != token_type:
            raise ParseError(
                f"Expected {token_type.name}, got '{token.value}'",
                position=token.position,
            )
        if value is not None and token.value != value:
            raise ParseError(
                f"Expected '{value}', got '{token.value}'",
                position=token.position,
            )
        return self.advance()

    def _expect_keyword(self, value: str) -> Token:
        token = self.peek()
        if token.type != TokenType.KEYWORD or token.value != value:
            raise ParseError(
                f"Expected '{value}', got '{token.value}'",
                position=token.position,
            )
        return self.advance()

    def _parse_create_table(self) -> CreateTable:
        self._expect_keyword("CREATE")
        self._expect_keyword("TABLE")
        name_token = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.LPAREN)
        columns: list[str] = []
        columns.append(self._expect(TokenType.IDENTIFIER).value)
        while self.peek().type == TokenType.COMMA:
            self.advance()
            columns.append(self._expect(TokenType.IDENTIFIER).value)
        self._expect(TokenType.RPAREN)
        return CreateTable(name=name_token.value, columns=columns)

    def _parse_insert(self) -> Insert:
        self._expect_keyword("INSERT")
        self._expect_keyword("INTO")
        table_token = self._expect(TokenType.IDENTIFIER)
        self._expect_keyword("VALUES")
        self._expect(TokenType.LPAREN)
        values: list[Expression] = []
        values.append(self._parse_primary())
        while self.peek().type == TokenType.COMMA:
            self.advance()
            values.append(self._parse_primary())
        self._expect(TokenType.RPAREN)
        return Insert(table=table_token.value, values=values)

    def _parse_select(self) -> Select:
        self._expect_keyword("SELECT")
        columns = self._parse_column_list()
        self._expect_keyword("FROM")
        table_token = self._expect(TokenType.IDENTIFIER)
        where = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "WHERE":
            self.advance()
            where = self._parse_expression()
        return Select(columns=columns, table=table_token.value, where=where)

    def _parse_delete(self) -> Delete:
        self._expect_keyword("DELETE")
        self._expect_keyword("FROM")
        table_token = self._expect(TokenType.IDENTIFIER)
        where = None
        if self.peek().type == TokenType.KEYWORD and self.peek().value == "WHERE":
            self.advance()
            where = self._parse_expression()
        return Delete(table=table_token.value, where=where)

    def _parse_column_list(self) -> list[Expression]:
        if self.peek().type == TokenType.STAR:
            self.advance()
            return [Star()]
        columns: list[Expression] = []
        columns.append(self._parse_column_ref())
        while self.peek().type == TokenType.COMMA:
            self.advance()
            columns.append(self._parse_column_ref())
        return columns

    def _parse_column_ref(self) -> ColumnRef:
        token = self._expect(TokenType.IDENTIFIER)
        return ColumnRef(table=None, name=token.value)

    def _parse_expression(self) -> Expression:
        return self._parse_or()

    def _parse_or(self) -> Expression:
        left = self._parse_and()
        while self.peek().type == TokenType.KEYWORD and self.peek().value == "OR":
            self.advance()
            right = self._parse_and()
            left = BinaryOp(left=left, op="OR", right=right)
        return left

    def _parse_and(self) -> Expression:
        left = self._parse_comparison()
        while self.peek().type == TokenType.KEYWORD and self.peek().value == "AND":
            self.advance()
            right = self._parse_comparison()
            left = BinaryOp(left=left, op="AND", right=right)
        return left

    def _parse_comparison(self) -> Expression:
        left = self._parse_primary()
        if self.peek().type == TokenType.OPERATOR:
            op = self.advance().value
            right = self._parse_primary()
            return BinaryOp(left=left, op=op, right=right)
        return left

    def _parse_primary(self) -> Expression:
        token = self.peek()
        if token.type == TokenType.INTEGER_LIT:
            self.advance()
            return Literal(value=int(token.value))
        if token.type == TokenType.FLOAT_LIT:
            self.advance()
            return Literal(value=float(token.value))
        if token.type == TokenType.STRING_LIT:
            self.advance()
            return Literal(value=token.value)
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return ColumnRef(table=None, name=token.value)
        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr
        raise ParseError(
            f"Unexpected token '{token.value}'", position=token.position
        )
