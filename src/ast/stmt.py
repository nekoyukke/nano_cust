from dataclasses import dataclass
from abc import ABC

from src.ast.base import ASTNode, TypeDef, Parameter
import src.ast.expr as _expr


@dataclass(repr=False)
class Stmt(ASTNode, ABC):
    pass

# 宣言系
@dataclass(repr=False)
class VariableDeclStmt(Stmt):
    name: _expr.Variable
    contract: TypeDef
    left: _expr.Expr | None

@dataclass(repr=False)
class FunctionDeclStmt(Stmt):
    name: _expr.Variable
    result: TypeDef
    params: list[Parameter]
    body: Stmt


@dataclass(repr=False)
class ClassDeclStmt(Stmt):
    name: _expr.Variable
    method: list[FunctionDeclStmt]
    member: list[VariableDeclStmt]

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

@dataclass(repr=False)
class SaveNode(Stmt):
    source: _expr.Variable


@dataclass(repr=False)
class UnSaveNode(Stmt):
    source: _expr.Variable