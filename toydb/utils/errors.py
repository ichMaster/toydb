class ToyDBError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ParseError(ToyDBError):
    def __init__(self, message: str, position: int = 0):
        self.position = position
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.message} at position {self.position}"


class ExecutionError(ToyDBError):
    pass
