from __future__ import annotations

# resolve and typecheck.
# Notably, it processes members and methods as well.

import src.ast.stmt as stmt
import src.ast.base as base
import src.ast.expr as expr

import src.ast.symbol as symbol

from src.ast.scope import Scope

from src.ast.context import Context

from utils.error.collector import KinakoCollectorError
from utils.error.base import KinakoHelp, KinakoRelatedInfo, KinakoBaseError

class Resolver():
    def __init__(self, program: stmt.ProgramStmt, source:str, ctx:Context, scp:Scope) -> None:
        self.program: stmt.ProgramStmt = program
        self.source: str = source
        self.scope:Scope = scp
        self.ctx:Context = ctx
        self.error:list[KinakoBaseError] = []

    def CallError(
            self, message:str ,node:base.ASTNode,
            related: list[KinakoRelatedInfo] | None = None,
            help: list[KinakoHelp] | None = None
        ):
        """
        エラー呼び出し
        """
        err =  KinakoCollectorError(
            message,
            node.line,
            node.col,
            self.source,
            node.len,
            related,
            help
        )
        self.error.append(err)

    def CallError_Symbol(self, node:base.ASTNode, string:str):
        sym = self.scope.sym[string]
        match (sym):
            case symbol.VariableSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.decl.line, sym.decl.col, sym.decl.len)])
            case symbol.FunctionSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.decl.line, sym.decl.col, sym.decl.len)])
            case symbol.ClassSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.decl.line, sym.decl.col, sym.decl.len)])
            case symbol.MemberSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.val.decl.line, sym.val.decl.col, sym.val.decl.len)])
            case symbol.MethodSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.fnc.decl.line, sym.fnc.decl.col, sym.fnc.decl.len)])
            case _:
                self.CallError(f"すでに'{string}'は存在します。", node)

    def collect(self):
        self.visit_Program(self.program)
        return self.scope

    def visit_Program(self, program:stmt.ProgramStmt):
        for instr in program.instr:
            self.visit_stmt(instr)

    def visit_stmt(self, node:stmt.Stmt):
        match(node):
            case stmt.VariableDeclStmt():
                self.visit_variable(node)
            case stmt.FunctionDeclStmt():
                self.visit_function(node)
            case stmt.ClassDeclStmt():
                self.visit_class(node)
            case stmt.Ifstmt():
                self.visit_if(node)
            case stmt.WhileStmt():
                self.visit_while(node)
            case stmt.ForEachStmt():
                self.visit_foreach(node)
            case stmt.BlockStmt():
                self.visit_block(node)
            case stmt.ImportNode():
                self.visit_import(node)
            case stmt.SaveNode():
                self.visit_save(node)
            case stmt.UnSaveNode():
                self.visit_unsave(node)
            case stmt.ExprStmt():
                self.visit_exprstmt(node)
            case stmt.ReturnStmt():
                self.visit_return(node)
            case _:
                self.CallError("不明", node)

    def visit_expr(self, node:expr.Expr):
        match(node):
            case _:
                