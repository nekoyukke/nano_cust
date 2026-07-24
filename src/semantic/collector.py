from __future__ import annotations

import src.ast.stmt as stmt
import src.ast.expr as expr
import src.ast.base as base

from src.ast.abc_class import Symbol, Type

import src.ast.type as type
import src.ast.symbol as symbol

from src.ast.scope import Scope

from src.ast.context import Context

from utils.error.collector import KinakoCollectorError
from utils.error.base import KinakoHelp, KinakoRelatedInfo, KinakoBaseError

class Collector():
    def __init__(self, program: stmt.ProgramStmt, source:str, ctx:Context) -> None:
        self.program: stmt.ProgramStmt = program
        self.source: str = source
        self.scope:Scope = Scope()
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
            case symbol.VariableSymbol()|symbol.FunctionDeclStmt():
                self.CallError(f"すでに'{string}'は存在します。", node)
            case _:
                self.CallError(f"すでに'{string}'は存在します。", node)

    def collect(self):
        self.visit_Program(self.program)
        return self.scope

    def visit_Program(self, program:stmt.ProgramStmt):
        for instr in program.instr:
            self.visit_stmt(instr)

    def visit_stmt(self, node:stmt.Stmt) -> symbol.Symbol:
        match(node):
            case stmt.VariableDeclStmt():
                return self.visit_variable(node)
            case stmt.ClassDeclStmt():
                return self.visit_class(node)
            case stmt.FunctionDeclStmt():
                return self.visit_function(node)
            case _:
                raise

    def visit_variable(self, node:stmt.VariableDeclStmt) -> symbol.VariableSymbol:
        string = node.name.ident
        if string in self.scope.sym:
            raise self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("重なる宣言場所", sym[string])])
        self.scope.sym[string]=symbol.VariableSymbol(string, node)
        return symbol.VariableSymbol(string, node)