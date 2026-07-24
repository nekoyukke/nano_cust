from dataclasses import dataclass

from src.ast.abc_class import Symbol, Type
from src.ast.base import ASTNode

@dataclass
class Context():
    symbol: dict[Symbol, ASTNode]