from dataclasses import dataclass
from src.backend.ir.instr import *
from src.backend.ir.value import *

@dataclass
class Move(Stmt):
    result: Variable
    value: Expr


@dataclass
class VariableExpr(Expr):
    value: Variable


@dataclass
class ImmExpr(Expr):
    value: Immediate


@dataclass
class Add(Expr):
    left: Expr
    right: Expr


@dataclass
class Sub(Expr):
    left: Expr
    right: Expr


@dataclass
class Mul(Expr):
    left: Expr
    right: Expr


@dataclass
class Div(Expr):
    left: Expr
    right: Expr


@dataclass
class Mod(Expr):
    left: Expr
    right: Expr