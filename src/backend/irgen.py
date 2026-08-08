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
        self.ctx:Context = ctx
        # fuckin containers
        self.name_list: list[str] = []
        # fuckint meens "fuck int" and "fuckin t"
        self.module_variable: dict[symbol.Symbol, Variable] = {}
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
        self.current_instr: list[Stmt] | None = None
        self.sprite_functions: dict[str, list[tuple[stmt.FunctionDeclStmt, symbol.FunctionSymbol, Function]]] = {}
    
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
            temp = self.new_variable(f"temp{len(self.temps)}", True)
            self.temps.append(temp)
            self.module.variables.append(temp)
        temp = self.temps[self.temp_pos]
        self.temp_pos+=1
        return temp

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
        sprites = [node for node in self.program.instr if isinstance(node, stmt.SpriteDeclStmt)]
        for sprite in sprites:
            self.declare_sprite(sprite)
        for sprite in sprites:
            self.generate_sprite(sprite)

    def declare_sprite(self, node:stmt.SpriteDeclStmt):
        self.name_list.append(node.name.ident)
        functions: list[tuple[stmt.FunctionDeclStmt, symbol.FunctionSymbol, Function]] = []
        for function_node in node.functions:
            function_symbol = function_node.name.sym
            if not isinstance(function_symbol, symbol.FunctionSymbol):
                raise ValueError(f"Unresolved Sprite function: {function_node.name.ident}")
            parameters: list[Variable] = []
            for parameter_symbol in function_symbol.parms:
                parameter = self.new_variable(parameter_symbol.name)
                self.module.variables.append(parameter)
                self.module_variable[parameter_symbol] = parameter
                parameters.append(parameter)
            function = Function(
                f"{node.name.ident}.{function_node.name.ident}",
                parameters,
                []
            )
            self.module_function[function_symbol] = len(self.module.func)
            self.module.func.append(function)
            functions.append((function_node, function_symbol, function))
        self.sprite_functions[node.name.ident] = functions
        self.name_list.pop()

    def generate_sprite(self, node:stmt.SpriteDeclStmt):
        functions = self.sprite_functions[node.name.ident]
        for function_node, function_symbol, function in functions:
            previous_instr = self.current_instr
            self.current_instr = function.instr
            self.reset_temp()
            self.visit_stmt(function_node.body)
            self.current_instr = previous_instr
            if function_symbol is self.ctx.entry:
                self.module.entry = function

    def emit(self, instruction: Stmt):
        if self.current_instr is None:
            raise ValueError("IR instruction emitted outside a function")
        self.current_instr.append(instruction)
    
    def visit_stmt(self, node:stmt.Stmt) -> Stmt:
        # what the fuck!?
        match(node):
            # 宣言系
            case stmt.VariableDeclStmt():
                variable_symbol = node.name.sym
                if not isinstance(variable_symbol, symbol.VariableSymbol):
                    raise ValueError(f"Unresolved variable: {node.name.ident}")
                variable = self.new_variable(node.name.ident)
                self.module.variables.append(variable)
                self.module_variable[variable_symbol] = variable
                if node.left is not None:
                    self.emit(Move(variable, self.visit_expr(node.left)))
                return

            # 式・返値系
            case stmt.ExprStmt():
                value = self.visit_expr(node.expr)
                if isinstance(value, Call):
                    self.emit(Move(self.trash, value))
                return
            case stmt.ReturnStmt():
                self.emit(Return(self.visit_expr(node.expr)))
                return

            # ブロック系
            case stmt.BlockStmt():
                for instruction in node.instr:
                    self.visit_stmt(instruction)
                return
            case stmt.ProgramStmt():
                self.visit_program()
                return

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
        match node:
            # 二項演算・単項演算・論理・代入
            case expr.BinaryExpr():
                left = self.visit_expr(node.left)
                right = self.visit_expr(node.right)
                match node.op:
                    case expr.BinaryKind.PLUS:
                        return Add(left, right)
                    case expr.BinaryKind.MINUS:
                        return Sub(left, right)
                    case expr.BinaryKind.MULT:
                        return Mul(left, right)
                    case expr.BinaryKind.DIV:
                        return Div(left, right)
                    case expr.BinaryKind.MOD:
                        return Mod(left, right)
                raise ValueError(f"Unsupported binary operator: {node.op}")
            case expr.UnaryExpr():
                value = self.visit_expr(node.expr)
                if node.op == expr.UnaryKind.PLUS:
                    return value
                return Sub(ImmExpr(Number(0)), value)
            case expr.LogicExpr():
                pass
            case expr.AssignExpr():
                pass
            
            # 変数・呼び出し
            case expr.Variable():
                if node.sym in self.module_variable:
                    return VariableExpr(self.module_variable[node.sym])
                raise ValueError(f"Variable has no IR storage: {node.ident}")
            case expr.CallExpr():
                function_symbol: symbol.FunctionSymbol | None = None
                if isinstance(node.call, expr.MemberExpr) and isinstance(node.call.member.sym, symbol.FunctionSymbol):
                    function_symbol = node.call.member.sym
                elif isinstance(node.call, expr.Variable) and isinstance(node.call.sym, symbol.FunctionSymbol):
                    function_symbol = node.call.sym
                if function_symbol not in self.module_function:
                    raise ValueError("Call target has no generated IR function")
                return Call(
                    self.module_function[function_symbol],
                    [self.visit_expr(argument) for argument in node.args]
                )
            
            # アクセス系 (AccessExpr)
            case expr.IndexExpr():
                pass
            case expr.MemberExpr():
                pass
            
            # リテラル系 (Literal)
            case expr.BoolLiteral():
                return ImmExpr(Number(1 if node.is_true else 0))
            case expr.IntLiteral():
                return ImmExpr(Number(node.number))
            case expr.FloatLiteral():
                return ImmExpr(Number(node.number))
            case expr.NoneLiteral():
                pass
            case expr.NullLiteral():
                pass
            case expr.StringLiteral():
                return ImmExpr(String(node.string))
            
            # 漏れ防止
            case _:
                raise ValueError(f"Unknown expression node: {type(expr).__name__}")
