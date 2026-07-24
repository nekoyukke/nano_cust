from __future__ import annotations

import src.ast.stmt as stmt
import src.ast.expr as expr
import src.ast.base as base

from src.ast.abc_class import Symbol, Type

import src.ast.type as type
import src.ast.symbol as symbol

from src.ast.context import Context

class Collector():
    def __init__(self, program: stmt.ProgramStmt, source:str, ctx:Context) -> None:
        self.program: stmt.ProgramStmt = program
        self.source: str = source
        self.ctx:Context = ctx

    def collect(self):
        self.visit_Program(self.program)

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
        node.contract
        