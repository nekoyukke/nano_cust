from dataclasses import dataclass
from src.backend.ir.instr import *

@dataclass
class ListGet(Expr):
    list_id: int
    index: Expr


@dataclass
class ListLength(Expr):
    list_id: int


@dataclass
class ListContains(BoolExpr):
    list_id: int
    value: Expr