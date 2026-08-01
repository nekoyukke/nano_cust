from dataclasses import dataclass
from abc import ABC

@dataclass
class Value(ABC):
    pass

@dataclass
class Variable(Value):
    id: int
    name: str

@dataclass
class Immediate(Value, ABC):
    pass

@dataclass
class String(Immediate):
    value: str

@dataclass
class Number(Immediate):
    value: int
