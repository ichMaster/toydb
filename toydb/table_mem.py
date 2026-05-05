from collections.abc import Callable, Iterator

from toydb.utils.errors import ExecutionError


class MemoryTable:
    def __init__(self, name: str, column_names: list[str]):
        self.name = name
        self.column_names = column_names
        self._rows: list[dict] = []

    def insert(self, values: list) -> None:
        if len(values) != len(self.column_names):
            raise ExecutionError(
                f"Expected {len(self.column_names)} values, got {len(values)}"
            )
        row = dict(zip(self.column_names, values))
        self._rows.append(row)

    def scan(self) -> Iterator[dict]:
        return iter(self._rows)

    def delete(self, predicate: Callable[[dict], bool]) -> int:
        original_count = len(self._rows)
        self._rows = [row for row in self._rows if not predicate(row)]
        return original_count - len(self._rows)

    def row_count(self) -> int:
        return len(self._rows)
