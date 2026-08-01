from __future__ import annotations

import src.frontend.ast.expr as expr
import src.frontend.ast.stmt as stmt

from src.frontend.ast.context import Context
import src.frontend.ast.symbol as symbol

from src.backend.ir.boolexpr import *
from src.backend.ir.expr import *
from src.backend.ir.flow import *
from src.backend.ir.instr import *
from src.backend.ir.list import *
from src.backend.ir.module import *
from src.backend.ir.stmt import *
from src.backend.ir.value import *


class IRGenerator:
    def __init__(self, Program:stmt.ProgramStmt, source:str, ctx:Context) -> None:
        self.module = Module([],[],[])
        self.program:stmt.ProgramStmt = Program
        # fuckin containers
        self.name_list: list[str] = []
        # fuckint meens "fuck int" and "fuckin t"
        self.module_variable: dict[symbol.VariableSymbol, int] = {}
        self.module_function: dict[symbol.FunctionSymbol, int] = {}
        self.module_list: dict[str, int] = {}
        # counts
        self.count = 0
        self.temp_pos = 0
        # variable and lists
        self.trash:Variable
        self.object_address: ListInfo
        self.object_clstype: ListInfo
        self.alloc_stack: ListInfo
        self.scope_stack: ListInfo
        self.Frame: ListInfo
        self.temps: list[Variable] = []
    
    def get_name(self) -> str:
        # eazy
        if self.name_list:
            return "__global__.__"+"__.__".join(self.name_list) + "__"
        return "__global__."

    def new_variable(self, name:str, es:bool = False) -> Variable:
        self.count+=1
        if es:
            # nc is nano-cust
            return Variable(self.count, "__nc_runtime__."+name)
        return Variable(self.count, self.get_name()+name)

    def new_list(self, name:str, es:bool = False) -> ListInfo:
        self.count+=1
        if es:
            # nc is nano-cust
            return ListInfo("__nc_runtime__."+name)
        return ListInfo(self.get_name()+name)

    def reset_temp(self):
        self.temp_pos = 0

    def get_temp(self):
        if (self.temp_pos >= len(self.temps)):
            # new one
            self.temps.append(self.new_variable(f"temp{len(self.temps)}", True))
        self.temp_pos+=1
        return self.temps[self.temp_pos]

    def visit(self) -> Module:
        # what
        self.make_runtime()
        self.make_storage()
        self.visit_program()
        return self.module

    def make_runtime(self):
        # need neet now cow
        self.make_runtime_variable()
        self.make_runtime_list()
        return

    def make_runtime_variable(self):
        self.trash = self.new_variable("__trash", True)
        self.module.variables.append(self.trash)
        return

    def make_runtime_list(self):
        self.object_address: ListInfo = self.new_list("__Object_address__", True)
        self.object_clstype: ListInfo = self.new_list("__Object_CLSType", True)
        self.alloc_stack: ListInfo = self.new_list("__Aloc_Stack__", True)
        self.scope_stack: ListInfo = self.new_list("__Scope_Stack__", True)
        self.Frame: ListInfo = self.new_list("__Frame__", True)
        self.module.lists.append(self.object_address)
        self.module.lists.append(self.object_clstype)
        self.module.lists.append(self.alloc_stack)
        self.module.lists.append(self.scope_stack)
        self.module.lists.append(self.Frame)
        return

    def make_storage(self):
        self.make_variable()
        self.make_list()

    def make_variable(self):
        return

    def make_list(self):
        return


    def visit_program(self):
        for i in self.program.instr:
            match (i):
                case stmt.ClassDeclStmt():
                    pass
                case stmt.FunctionDeclStmt():
                    pass
                case stmt.VariableDeclStmt():
                    pass
                case _:
                    raise
    
    def visit_stmt(self, node:stmt.Stmt) -> Stmt:
        # what the fuck!?
        match(node):
            # 宣言系
            case stmt.VariableDeclStmt():
                pass

            # 式・返値系
            case stmt.ExprStmt():
                pass
            case stmt.ReturnStmt():
                pass

            # ブロック系
            case stmt.BlockStmt():
                pass
            case stmt.ProgramStmt():
                pass

            # 制御構文系
            case stmt.Ifstmt():
                pass
            case stmt.WhileStmt():
                pass
            case stmt.ForEachStmt():
                pass

            # 外部操作・保存系
            case stmt.ImportNode():
                pass
            case stmt.SaveNode():
                pass
            case stmt.UnSaveNode():
                pass

            # 漏れ防止
            case _:
                raise ValueError(f"Unknown statement node: {type(stmt).__name__}")

    def visit_expr(self, node:expr.Expr) -> Expr:
        match expr:
            # 二項演算・単項演算・論理・代入
            case expr.BinaryExpr():
                pass
            case expr.UnaryExpr():
                pass
            case expr.LogicExpr():
                pass
            case expr.AssignExpr():
                pass
            
            # 変数・呼び出し
            case expr.Variable():
                pass
            case expr.CallExpr():
                pass
            
            # アクセス系 (AccessExpr)
            case expr.IndexExpr():
                pass
            case expr.MemberExpr():
                pass
            
            # リテラル系 (Literal)
            case expr.BoolLiteral():
                pass
            case expr.IntLiteral():
                pass
            case expr.FloatLiteral():
                pass
            case expr.NoneLiteral():
                pass
            case expr.NullLiteral():
                pass
            case expr.StringLiteral():
                pass
            
            # 漏れ防止
            case _:
                raise ValueError(f"Unknown expression node: {type(expr).__name__}")