import uuid
import json
import src.ast.base as _base
import src.ast.expr as _expr
import src.ast.stmt as _stmt

class ScratchCodegen:
    def __init__(self, program: _stmt.ProgramStmt) -> None:
        self.program = program
        