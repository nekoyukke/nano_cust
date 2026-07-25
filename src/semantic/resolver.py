from __future__ import annotations

# resolve and typecheck.
# Notably, it processes members and methods as well.

import src.ast.stmt as stmt
import src.ast.base as base
import src.ast.expr as expr

import src.ast.symbol as symbol

from src.ast.scope import Scope

from src.ast.context import Context

import src.ast.type as types

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

    def resolve(self):
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
                self.scope = self.scope.push()
                self.visit_function(node)
                self.scope = self.scope.pop()
            case stmt.ClassDeclStmt():
                self.scope = self.scope.push()
                self.visit_class(node)
                self.scope = self.scope.pop()
            case stmt.Ifstmt():
                self.scope = self.scope.push()
                self.visit_if(node)
                self.scope = self.scope.pop()
            case stmt.WhileStmt():
                self.scope = self.scope.push()
                self.visit_while(node)
                self.scope = self.scope.pop()
            case stmt.ForEachStmt():
                self.scope = self.scope.push()
                self.visit_foreach(node)
                self.scope = self.scope.pop()
            case stmt.ReturnStmt():
                self.visit_return(node)
            case stmt.BlockStmt():
                self.scope = self.scope.push()
                for i in node.instr:
                    self.visit_stmt(i)
                self.scope = self.scope.pop()
            case _:
                return

    def visit_expr(self, node:expr.Expr) -> types.Type:
        match(node):
            case expr.Variable():
                sym = self.scope.lookup(node.ident)
                node.sym = sym
                if sym in self.ctx.val_type:
                    # ok
                    pass
                elif sym in self.ctx.func_type:
                    pass
                elif sym in self.ctx.types:
                    pass
                else:
                    self.CallError("エラー！！！", node)
            case expr.BinaryExpr():
                lt = self.visit_expr(node.left)
                rt = self.visit_expr(node.right)
                if lt == rt:
                    return lt
                self.CallError(f"型が違います。{lt}と{rt}", node)
            case expr.LogicExpr():
                lt = self.visit_expr(node.left)
                rt = self.visit_expr(node.right)
                if lt == rt:
                    return types.BooleanType()
                self.CallError(f"型が違います。{lt}と{rt}", node)
            case expr.AssignExpr():
                if not isinstance(node.left, expr.AccessExpr|expr.Variable):
                    self.CallError("呼び出し可能値ではありません", node)
                lt = self.visit_expr(node.left)
                rt = self.visit_expr(node.right)
                if lt == rt:
                    return lt
                self.CallError(f"型が違います。{lt}と{rt}", node)
            case _:
                pass