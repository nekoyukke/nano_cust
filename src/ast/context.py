from dataclasses import dataclass

from src.ast.symbol import ClassSymbol, Symbol
from src.ast.abc_class import Type

@dataclass
class Context():
    types: dict[str, ClassSymbol]
    sym_type: dict[Symbol, Type]