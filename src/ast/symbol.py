from __future__ import annotations

from dataclasses import dataclass

from src.ast.abc_class import Symbol
from src.ast.stmt import ClassDeclStmt, FunctionDeclStmt, VariableDeclStmt

@dataclass
class VariableSymbol(Symbol):
    name: str
    decl: VariableDeclStmt

@dataclass
class ClassSymbol(Symbol):
    name: str
    member: list[MemberSymbol]
    method: list[MethodSymbol]
    decl: ClassDeclStmt

@dataclass
class FunctionSymbol(Symbol):
    name: str
    parms: list[VariableSymbol]
    decl: FunctionDeclStmt

@dataclass
class MemberSymbol(Symbol):
    val: VariableSymbol
    cls: ClassSymbol

@dataclass
class MethodSymbol(Symbol):
    fnc: FunctionSymbol
    cls: ClassSymbol