from __future__ import annotations

from dataclasses import dataclass
from abc import ABC

from src.ast.abc_class import Symbol, Type

@dataclass
class BuildinType(Type, ABC):
    pass

@dataclass
class NumberType(BuildinType):
    pass

@dataclass
class StringType(BuildinType):
    pass

@dataclass
class BooleanType(BuildinType):
    pass

@dataclass
class ListType(BuildinType):
    element: Type

@dataclass
class UserDefType(Type):
    sym: Symbol

@dataclass
class Function(Type):
    ret: Type
    parms: list[Type]

@dataclass
class Class(Type):
    name: str