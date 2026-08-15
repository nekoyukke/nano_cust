from dataclasses import dataclass
from src.backend.ir.instr import *

@dataclass
class ListGet(Expr):
    list_id: ListInfo
    index: Expr


@dataclass
class ListLength(Expr):
    list_id: ListInfo


@dataclass
class ListContains(BoolExpr):
    list_id: ListInfo
    value: Expr