from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import src.ast.stmt as stmt
import src.ast.expr as expr
import src.ast.base as base


# ============================
# Symbol
# ============================

@dataclass
class Symbol:
    name: str
    node: Any


@dataclass
class VariableSymbol(Symbol):
    type: Any = None


@dataclass
class FunctionSymbol(Symbol):
    params: list[Any] | None = None
    result: Any = None


@dataclass
class ClassSymbol(Symbol):
    pass


@dataclass
class EnumSymbol(Symbol):
    values: dict[str, int] | None = None


# ============================
# Scope
# ============================

class Scope:

    def __init__(self, parent: Scope | None = None):
        self.parent = parent
        self.symbols: dict[str, Symbol] = {}

    def define(self, symbol: Symbol):
        if symbol.name in self.symbols:
            raise Exception(f"duplicate symbol '{symbol.name}'")
        self.symbols[symbol.name] = symbol

    def resolve(self, name: str) -> Symbol | None:
        if name in self.symbols:
            return self.symbols[name]

        if self.parent:
            return self.parent.resolve(name)

        return None


# ============================
# Semantic
# ============================

class SemanticAnalyzer:

    def __init__(self):
        self.global_scope = Scope()
        self.scope = self.global_scope

        self.current_class = None
        self.current_function = None

    # ------------------------
    # Entry
    # ------------------------

    def analyze(self, node: stmt.ProgramStmt):
        self.visit(node)

    # ------------------------
    # Visitor
    # ------------------------

    def visit(self, node:base.ASTNode|None) -> None:

        if node is None:
            return None

        match node:

            # Statements
            case stmt.ProgramStmt():
                return self.visit_ProgramStmt(node)

            case stmt.BlockStmt():
                return self.visit_BlockStmt(node)

            case stmt.ClassDeclStmt():
                return self.visit_ClassDeclStmt(node)

            case stmt.FunctionDeclStmt():
                return self.visit_FunctionDeclStmt(node)

            case stmt.VariableDeclStmt():
                return self.visit_VariableDeclStmt(node)

            case stmt.ExprStmt():
                return self.visit_ExprStmt(node)

            case stmt.ReturnStmt():
                return self.visit_ReturnStmt(node)

            case stmt.Ifstmt():
                return self.visit_Ifstmt(node)

            case stmt.WhileStmt():
                return self.visit_WhileStmt(node)

            case stmt.ForEachStmt():
                return self.visit_ForEachStmt(node)

            case stmt.ImportNode():
                return self.visit_ImportNode(node)

            case stmt.SaveNode():
                return self.visit_SaveNode(node)

            case stmt.UnSaveNode():
                return self.visit_UnSaveNode(node)

            # Expressions
            case expr.Variable():
                return self.visit_Variable(node)

            case expr.AssignExpr():
                return self.visit_AssignExpr(node)

            case expr.BinaryExpr():
                return self.visit_BinaryExpr(node)

            case expr.UnaryExpr():
                return self.visit_UnaryExpr(node)

            case expr.LogicExpr():
                return self.visit_LogicExpr(node)

            case expr.CallExpr():
                return self.visit_CallExpr(node)

            case expr.IndexExpr():
                return self.visit_IndexExpr(node)

            case expr.MemberExpr():
                return self.visit_MemberExpr(node)

            # Literals
            case expr.IntLiteral():
                return self.visit_IntLiteral(node)

            case expr.FloatLiteral():
                return self.visit_FloatLiteral(node)

            case expr.StringLiteral():
                return self.visit_StringLiteral(node)

            case expr.BoolLiteral():
                return self.visit_BoolLiteral(node)

            case expr.NoneLiteral():
                return self.visit_NoneLiteral(node)

            case expr.NullLiteral():
                return self.visit_NullLiteral(node)

            case _:
                raise NotImplementedError(
                    f"Semantic analyzer does not support {type(node).__name__}"
                    )

    # ========================
    # Statements
    # ========================

    def visit_ProgramStmt(self, node: stmt.ProgramStmt):

        # Pass1
        for i in node.instr:
            if isinstance(i, stmt.ClassDeclStmt):
                self.global_scope.define(ClassSymbol(i.name.ident, i))

            elif isinstance(i, stmt.FunctionDeclStmt):
                self.global_scope.define(FunctionSymbol(i.name.ident, i))

        # Pass2
        for i in node.instr:
            self.visit(i)

    def visit_BlockStmt(self, node: stmt.BlockStmt):

        old = self.scope
        self.scope = Scope(old)

        for i in node.instr:
            self.visit(i)

        self.scope = old

    def visit_ClassDeclStmt(self, node: stmt.ClassDeclStmt):

        self.current_class = node

        old = self.scope
        self.scope = Scope(old)

        for member in node.member:
            self.scope.define(
                VariableSymbol(member.name.ident, member)
            )

        for method in node.method:
            self.visit(method)

        self.scope = old
        self.current_class = None

    def visit_FunctionDeclStmt(self, node: stmt.FunctionDeclStmt):

        self.current_function = node

        old = self.scope
        self.scope = Scope(old)

        for p in node.params:
            self.scope.define(
                VariableSymbol(p.name, p)
            )

        self.visit(node.body)

        self.scope = old
        self.current_function = None

    def visit_VariableDeclStmt(self, node: stmt.VariableDeclStmt):

        self.scope.define(
            VariableSymbol(node.name.ident, node)
        )

        if node.left:
            self.visit(node.left)

    def visit_ExprStmt(self, node:stmt.ExprStmt):
        self.visit(node.expr)

    def visit_ReturnStmt(self, node:stmt.ReturnStmt):
        self.visit(node.expr)

    def visit_Ifstmt(self, node:stmt.Ifstmt):
        self.visit(node.cond)
        self.visit(node.then_stmt)
        self.visit(node.else_stmt)

    def visit_WhileStmt(self, node:stmt.WhileStmt):
        self.visit(node.cond)
        self.visit(node.loop)

    def visit_ForEachStmt(self, node:stmt.ForEachStmt):
        self.visit(node.iterator)
        self.visit(node.loop)

    def visit_ImportNode(self, node:stmt.ImportNode):
        pass

    def visit_SaveNode(self, node:stmt.SaveNode):
        self.visit(node.source)

    def visit_UnSaveNode(self, node:stmt.UnSaveNode):
        self.visit(node.source)

    # ========================
    # Expressions
    # ========================

    def visit_Variable(self, node: expr.Variable):

        symbol = self.scope.resolve(node.ident)

        if symbol is None:
            raise Exception(f"undefined variable '{node.ident}'")

        # TODO:
        # node.symbol = symbol

    def visit_AssignExpr(self, node:expr.AssignExpr):
        self.visit(node.left)
        self.visit(node.right)

    def visit_BinaryExpr(self, node:expr.BinaryExpr):
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryExpr(self, node:expr.UnaryExpr):
        self.visit(node.expr)

    def visit_LogicExpr(self, node:expr.LogicExpr):
        self.visit(node.left)
        self.visit(node.right)

    def visit_CallExpr(self, node:expr.CallExpr):

        self.visit(node.call)

        for arg in node.args:
            self.visit(arg)

        # TODO
        # resolve overload
        # check argument count
        # check argument type

    def visit_IndexExpr(self, node:expr.IndexExpr):
        self.visit(node.expr)
        self.visit(node.index)

    def visit_MemberExpr(self, node:expr.MemberExpr):
        self.visit(node.expr)

        # TODO
        # resolve member

    # ========================
    # Literals
    # ========================

    def visit_IntLiteral(self, node):
        pass

    def visit_FloatLiteral(self, node):
        pass

    def visit_StringLiteral(self, node):
        pass

    def visit_BoolLiteral(self, node):
        pass

    def visit_NoneLiteral(self, node):
        pass

    def visit_NullLiteral(self, node):
        pass