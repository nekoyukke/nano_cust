from __future__ import annotations

from dataclasses import dataclass

from src.ast.abc_class import Symbol
from src.ast.stmt import Stmt

@dataclass(repr=False)
class VariableSymbol(Symbol):
    name: str
    decl: Stmt
    def __hash__(self):
        return hash((self.name, id(self.decl)))

@dataclass(repr=False)
class ClassSymbol(Symbol):
    name: str
    member: list[MemberSymbol]
    method: list[MethodSymbol]
    decl: Stmt
    def __hash__(self):
        return hash((self.name, tuple(self.member), tuple(self.method), id(self.decl)))

@dataclass(repr=False)
class FunctionSymbol(Symbol):
    name: str
    parms: list[VariableSymbol]
    decl: Stmt
    def __hash__(self):
        return hash((self.name, tuple(self.parms), id(self.decl)))

@dataclass(repr=False, unsafe_hash=True)
class MemberSymbol(Symbol):
    val: VariableSymbol
    cls: ClassSymbol

@dataclass(repr=False, unsafe_hash=True)
class MethodSymbol(Symbol):
    fnc: FunctionSymbol
    cls: ClassSymbol