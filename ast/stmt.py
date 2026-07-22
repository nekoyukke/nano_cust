from dataclasses import dataclass
from abc import ABC

from ast.base import ASTNode, Identifier, Parameter
import ast.expr as _expr


@dataclass(repr=False)
class Stmt(ASTNode, ABC):
    pass

# 宣言系
@dataclass(repr=False)
class VariableDeclStmt(Stmt):
    name: _expr.Variable
    contract: Identifier
    left: _expr.Expr | None

@dataclass(repr=False)
class FunctionDeclStmt(Stmt):
    name: _expr.Variable
    result: Identifier
    params: list[Parameter]
    body: Stmt

# そのほか

@dataclass(repr=False)
class ExprStmt(Stmt):
    expr: _expr.Expr

@dataclass(repr=False)
class ReturnStmt(Stmt):
    expr: _expr.Expr

# ブロック系
@dataclass(repr=False)
class BlockStmt(Stmt):
    instr: list[Stmt]

@dataclass(repr=False)
class ProgramStmt(Stmt):
    instr: list[Stmt]

# 制御構文系
@dataclass(repr=False)
class Ifstmt(Stmt):
    cond: _expr.Expr
    then_stmt: Stmt
    else_stmt: Stmt | None

@dataclass(repr=False)
class WhileStmt(Stmt):
    cond: _expr.Expr
    loop: Stmt

@dataclass(repr=False)
class ForEachStmt(Stmt):
    iterator: _expr.Expr
    variable: _expr.Variable
    loop: Stmt

@dataclass(repr=False)
class ImportNode(Stmt):
    source: str