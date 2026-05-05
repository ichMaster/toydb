import readline  # noqa: F401 — enables line editing in input()

from toydb.executor_mem import MemoryExecutor
from toydb.parser.lexer import Lexer
from toydb.parser.parser import Parser
from toydb.utils.errors import ExecutionError, ParseError
from toydb.utils.formatter import format_results


class REPL:
    def __init__(self, executor: MemoryExecutor):
        self._executor = executor

    def start(self) -> None:
        print("ToyDB v0.1.0")
        print("Type .quit or .exit to leave.\n")
        while True:
            try:
                sql = self._read_statement()
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue

            if sql is None:
                break

            stripped = sql.strip()
            if not stripped:
                continue

            try:
                tokens = Lexer(stripped).tokenize()
                stmt = Parser(tokens).parse()
                result = self._executor.execute(stmt)
                self._print_result(result)
            except ParseError as e:
                print(f"Parse error: {e}")
            except ExecutionError as e:
                print(f"Error: {e.message}")

    def _read_statement(self) -> str | None:
        lines: list[str] = []
        prompt = "toydb> "
        while True:
            try:
                line = input(prompt)
            except EOFError:
                if lines:
                    print()
                raise
            except KeyboardInterrupt:
                if lines:
                    print()
                    return ""
                raise

            if not lines and line.strip().startswith("."):
                cmd = line.strip().lower()
                if cmd in (".quit", ".exit"):
                    return None
                print(f"Unknown command: {line.strip()}")
                return ""

            lines.append(line)
            full = " ".join(lines)
            if full.rstrip().endswith(";"):
                return full
            prompt = "...> "

    def _print_result(self, result) -> None:
        if result.columns is not None:
            print(format_results(result.columns, result.rows))
        elif result.message:
            if result.affected_rows is not None:
                print(f"{result.message} ({result.affected_rows} row)")
            else:
                print(result.message)
        elif result.affected_rows is not None:
            print(f"OK ({result.affected_rows} row)")
