from typing import Callable

from lexer.token import Token
from lexer.tokentype import TokenType
import ast.base as _base
import ast.expr as _expr
import ast.stmt as _stmt
from utils.error.resolver import KinakoResolverError
from utils.error.base import KinakoHelp, KinakoRelatedInfo, KinakoBaseError

class SemanticAnalyzer():
    def __init__(self, program:_stmt.ProgramStmt, source: str, context:_ctx.Context) -> None:
        self.program = program
        self.context = context
        self.source = source
        self.error:list[KinakoBaseError] = []
        self.scope = Scope(None, {})
    
    def resolve(self):
        # トップレベルに限らず、すべての定義を参照。
        return self._visit_program()