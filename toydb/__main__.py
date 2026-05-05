import argparse

from toydb.executor_mem import MemoryExecutor
from toydb.repl import REPL


def main():
    parser = argparse.ArgumentParser(prog="toydb", description="ToyDB — educational SQL database")
    parser.add_argument("--mode", choices=["repl"], default="repl", help="Run mode (default: repl)")
    parser.parse_args()

    executor = MemoryExecutor()
    repl = REPL(executor)
    repl.start()


if __name__ == "__main__":
    main()
