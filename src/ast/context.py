from dataclasses import dataclass

from src.ast.symbol import ClassSymbol, VariableSymbol, FunctionSymbol
from src.ast.abc_class import Type

@dataclass
class Context():
    types: dict[str, ClassSymbol]
    val_type: dict[VariableSymbol, Type]
    func_type: dict[FunctionSymbol, tuple[Type, tuple[Type]]]