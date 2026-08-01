from __future__ import annotations

import src.frontend.ast.expr as ast_expr
import src.frontend.ast.stmt as ast_stmt

from src.frontend.ast.context import Context

from src.backend.ir.boolexpr import *
from src.backend.ir.expr import *
from src.backend.ir.flow import *
from src.backend.ir.instr import *
from src.backend.ir.list import *
from src.backend.ir.module import *
from src.backend.ir.stmt import *
from src.backend.ir.value import *


class IRGenerator:
    def __init__(self, Program:ast_stmt.ProgramStmt, source:str, ctx:Context) -> None:
        self.module = Module([],[],[])
        self.program:ast_stmt.ProgramStmt = Program

    def visit(self,) -> Module:
        self.program
        return self.module