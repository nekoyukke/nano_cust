"""Command-line compiler for nano_cust source files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.backend.irgen import IRGenerator
from src.backend.tosb3 import compile_to_sb3
from src.frontend.ast.context import Context
from src.frontend.lexer.lexer import Lexer
from src.frontend.parser.parser import Parser
from src.frontend.semantic.collector import Collector
from src.frontend.semantic.resolver import Resolver


def compile_source(source_path: Path, output_path: Path, *, check_only: bool = False) -> Path | None:
    """Compile one nano_cust source file, raising ``ValueError`` on diagnostics."""
    source = source_path.read_text(encoding="utf-8")
    context = Context({}, {}, {}, {}, {}, {}, {}, {}, {}, {})
    program = Parser(Lexer(source).tokenize(), source).parse()
    scope = Collector(program, source, context).collect()
    resolver = Resolver(program, source, context, scope)
    resolver.resolve()
    if resolver.error:
        raise ValueError("\n".join(map(str, resolver.error)))
    if check_only:
        return None
    module = IRGenerator(program, source, context).visit()
    return compile_to_sb3(module, output_path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nano_cust",
        description="Compile nano_cust source code into a Scratch 3 project (.sb3).",
    )
    parser.add_argument("input", type=Path, help="input nano_cust source file")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="output .sb3 path (default: input filename with .sb3 extension)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="parse and type-check only; do not create an .sb3 file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    source_path: Path = args.input
    if not source_path.is_file():
        print(f"nano_cust: error: input file not found: {source_path}", file=sys.stderr)
        return 1
    output_path: Path = args.output or source_path.with_suffix(".sb3")
    try:
        generated = compile_source(source_path, output_path, check_only=args.check)
    except (OSError, ValueError) as error:
        print(f"nano_cust: error: {error}", file=sys.stderr)
        return 1
    if args.check:
        print(f"{source_path}: check passed")
    else:
        assert generated is not None
        print(f"{source_path} -> {generated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
