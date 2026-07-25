from __future__ import annotations

import src.ast.stmt as stmt
import src.ast.base as base


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

    def visit_variable(self, node:stmt.VariableDeclStmt, flag:bool = False) -> symbol.VariableSymbol:
        string = node.name.ident
        if string in self.scope.sym:
            self.CallError_Symbol(node, string)
        sym = symbol.VariableSymbol(string, node)
        if flag:
            return sym
        self.scope.sym[string] = sym
        return sym

    def visit_class(self, node:stmt.ClassDeclStmt) -> symbol.ClassSymbol:
        string = node.name.ident
        sym = symbol.ClassSymbol(
            string,
            [],
            [],
            node
        )
        if string in self.scope.sym:
            self.CallError_Symbol(node, string)
        members:list[symbol.MemberSymbol] = []
        for i in node.member:
            members.append(symbol.MemberSymbol(self.visit_variable(i, True), sym))
        methods:list[symbol.MethodSymbol] = []
        for i in node.method:
            methods.append(symbol.MethodSymbol(self.visit_function(i, True), sym))
        sym.member = members
        sym.method = methods
        self.scope.sym[string] = sym
        self.ctx.types[string] = sym
        return sym

    def visit_function(self, node:stmt.FunctionDeclStmt, flag:bool = False) -> symbol.FunctionSymbol:
        string = node.name.ident
        if string in self.scope.sym:
            self.CallError_Symbol(node, string)
        sym = symbol.FunctionSymbol(string, [symbol.VariableSymbol(i.name, node) for i in node.params], node)
        if flag:
            return sym
        self.scope.sym[string] = sym
        return sym