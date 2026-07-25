from __future__ import annotations

from dataclasses import dataclass

from src.ast.abc_class import Symbol
from src.ast.stmt import Stmt

@dataclass
class VariableSymbol(Symbol):
    name: str
    decl: Stmt

@dataclass
class ClassSymbol(Symbol):
    name: str
    member: list[MemberSymbol]
    method: list[MethodSymbol]
    decl: Stmt

@dataclass
class FunctionSymbol(Symbol):
    name: str
    parms: list[VariableSymbol]
    decl: Stmt

@dataclass
class MemberSymbol(Symbol):
    val: VariableSymbol
    cls: ClassSymbol

@dataclass
class MethodSymbol(Symbol):
    fnc: FunctionSymbol
    cls: ClassSymbol