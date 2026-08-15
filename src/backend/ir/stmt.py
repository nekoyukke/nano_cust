from dataclasses import dataclass
from src.backend.ir.instr import *

@dataclass
class Move(Stmt):
    result: Variable
    value: Expr

@dataclass
class ListSet(Stmt):
    list_id: ListInfo   
    index: Expr
    value: Expr


@dataclass
class ListInsert(Stmt):
    list_id: ListInfo
    index: Expr
    value: Expr


@dataclass
class ListDelete(Stmt):
    list_id: ListInfo
    index: Expr


@dataclass
class ListPush(Stmt):
    list_id: ListInfo
    value: Expr


@dataclass
class ListPop(Stmt):
    list_id: ListInfo


@dataclass
class ListReset(Stmt):
    list_id: ListInfo