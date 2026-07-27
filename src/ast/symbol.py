from __future__ import annotations

from dataclasses import dataclass

from src.ast.abc_class import Symbol
from src.ast.stmt import Stmt

@dataclass(repr=False)
class VariableSymbol(Symbol):
    name: str
    decl: Stmt

@dataclass(repr=False)
class ClassSymbol(Symbol):
    name: str
    member: list[MemberSymbol]
    method: list[MethodSymbol]
    decl: Stmt

@dataclass(repr=False)
class FunctionSymbol(Symbol):
    name: str
    parms: list[VariableSymbol]
    decl: Stmt

@dataclass(repr=False)
class MemberSymbol(Symbol):
    val: VariableSymbol
    cls: ClassSymbol

@dataclass(repr=False)
class MethodSymbol(Symbol):
    fnc: FunctionSymbol
    cls: ClassSymbol