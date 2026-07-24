from __future__ import annotations

from dataclasses import dataclass

from src.ast.abc_class import Symbol, Type

@dataclass
class VariableSymbol(Symbol):
    name: str
    tp: Type

@dataclass
class ClassSymbol(Symbol):
    name: str
    member: list[MemberSymbol]
    method: list[MethodSymbol]

@dataclass
class FunctionSymbol(Symbol):
    name: str
    parms: list[VariableSymbol]
    types: list[Type]
    ret: Type

@dataclass
class MemberSymbol(Symbol):
    val: VariableSymbol
    cls: ClassSymbol

@dataclass
class MethodSymbol(Symbol):
    fnc: FunctionSymbol
    cls: ClassSymbol