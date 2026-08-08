from __future__ import annotations

import src.frontend.ast.stmt as stmt
import src.frontend.ast.base as base


import src.frontend.ast.symbol as symbol

from src.frontend.ast.scope import Scope

from src.frontend.ast.context import Context

from src.utils.error.collector import KinakoCollectorError
from src.utils.error.base import KinakoHelp, KinakoRelatedInfo, KinakoBaseError

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
        self.init()
        self.visit_Program(self.program)
        return self.scope

    def init(self):
        self.ctx.types

    def visit_Program(self, program:stmt.ProgramStmt):
        for instr in program.instr:
            self.visit_stmt(instr)

    def visit_stmt(self, node:stmt.Stmt) -> symbol.Symbol:
        match(node):
            case stmt.VariableDeclStmt():
                return self.visit_variable(node)
            case stmt.ClassDeclStmt():
                return self.visit_class(node)
            case stmt.SpriteDeclStmt():
                return self.visit_sprite(node)
            case stmt.FunctionDeclStmt():
                return self.visit_function(node)
            case _:
                raise

    def visit_variable(self, node:stmt.VariableDeclStmt, flag:bool = False) -> symbol.VariableSymbol:
        string = node.name.ident
        sym = symbol.VariableSymbol(string, node)
        if flag:
            return sym
        if string in self.scope.sym:
            self.CallError_Symbol(node, string)
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
        sym_class_element:symbol.Symbol
        members:list[symbol.MemberSymbol] = []
        for i in range(len(node.member)):
            sym_class_element = symbol.MemberSymbol(self.visit_variable(node.member[i], True), sym)
            members.append(sym_class_element)
            node.member[i].name.sym = sym_class_element
        methods:list[symbol.MethodSymbol] = []
        for i in range(len(node.method)):
            sym_class_element = symbol.MethodSymbol(self.visit_function(node.method[i], True), sym)
            methods.append(sym_class_element)
            node.method[i].name.sym = sym_class_element
        sym.member = members
        sym.method = methods
        self.scope.sym[string] = sym
        self.ctx.types[string] = sym
        return sym

    def visit_sprite(self, node:stmt.SpriteDeclStmt) -> symbol.SpriteSymbol:
        string = node.name.ident
        if string in self.scope.sym:
            self.CallError_Symbol(node, string)
        sym = symbol.SpriteSymbol(string, [], node)
        self.scope.sym[string] = sym
        function_names: set[str] = set()
        for function in node.functions:
            if function.name.ident in function_names:
                self.CallError(f"Sprite内で'{function.name.ident}'はすでに宣言されています", function)
                continue
            function_names.add(function.name.ident)
            function_symbol = self.visit_function(function, True)
            function.name.sym = function_symbol
            sym.functions.append(function_symbol)
        if string == "Main":
            main_functions = [function for function in sym.functions if function.name == "main"]
            if not main_functions:
                self.CallError("Sprite Main には main 関数が必要です", node)
            else:
                self.ctx.entry = main_functions[0]
        return sym

    def visit_function(self, node:stmt.FunctionDeclStmt, flag:bool = False) -> symbol.FunctionSymbol:
        string = node.name.ident
        if not flag and string in self.scope.sym:
            self.CallError_Symbol(node, string)
        sym = symbol.FunctionSymbol(string, [symbol.ArgsSymbol(j.name, node, i) for i,j in enumerate(node.params)], node)
        if flag:
            return sym
        self.scope.sym[string] = sym
        node.name.sym = sym
        return sym
