from dataclasses import dataclass

from src.ast.symbol import ClassSymbol, VariableSymbol, FunctionSymbol
from src.ast.abc_class import Type
from src.ast.type import Function

@dataclass
class Context():
    types: dict[str, ClassSymbol]
    val_type: dict[VariableSymbol, Type]
    func_type: dict[FunctionSymbol, Function]

    def __repr__(self) -> str:
        return f"{self.types}\n{self.val_type}\n{self.func_type}"