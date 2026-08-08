from dataclasses import dataclass
from src.backend.ir.instr import *

@dataclass
class Block:
    instr: list[Stmt]

@dataclass
class Branch(Stmt):
    cond: BoolExpr
    true_label: Block
    false_label: Block | None

@dataclass
class Return(Stmt):
    value: Expr | None = None


@dataclass
class Call(Expr):
    func_id: int
    params: list[Expr]
