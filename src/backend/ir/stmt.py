from dataclasses import dataclass
from src.backend.ir.instr import *

@dataclass
class ListSet(Stmt):
    list_id: int
    index: Expr
    value: Expr


@dataclass
class ListInsert(Stmt):
    list_id: int
    index: Expr
    value: Expr


@dataclass
class ListDelete(Stmt):
    list_id: int
    index: Expr


@dataclass
class ListPush(Stmt):
    list_id: int
    value: Expr


@dataclass
class ListPop(Stmt):
    list_id: int