from dataclasses import dataclass

from src.ast.symbol import ClassSymbol

@dataclass
class Context():
    types: dict[str, ClassSymbol]