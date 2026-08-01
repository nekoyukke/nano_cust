from dataclasses import dataclass
from src.backend.ir.instr import *

@dataclass
class Eq(BoolExpr):
    left: Expr
    right: Expr


@dataclass
class Ne(BoolExpr):
    left: Expr
    right: Expr


@dataclass
class Lt(BoolExpr):
    left: Expr
    right: Expr


@dataclass
class Le(BoolExpr):
    left: Expr
    right: Expr


@dataclass
class Gt(BoolExpr):
    left: Expr
    right: Expr


@dataclass
class Ge(BoolExpr):
    left: Expr
    right: Expr


@dataclass
class And(BoolExpr):
    left: BoolExpr
    right: BoolExpr


@dataclass
class Or(BoolExpr):
    left: BoolExpr
    right: BoolExpr


@dataclass
class Not(BoolExpr):
    value: BoolExpr