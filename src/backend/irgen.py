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
        self.module = Module([], None)
        self.program:stmt.ProgramStmt = Program
        self.ctx:Context = ctx
        # fuckin containers
        # fuckint meens "fuck int" and "fuckin t"
        
        # symbolの変換
        self.module_variable: dict[symbol.Symbol, Variable] = {}
        self.module_function: dict[symbol.FunctionSymbol, int] = {}
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
        # 共通ではないっす
        self.temps: list[Variable] = []
        # sprite整理
        self.sprite: list[Sprite] = []
        # spriteの今のindex
        self.sprite_pos:int = 0

    def get_name(self) -> str:
        """名前取得"""
        # eazy <= no!!!
        return "__global__"

    def new_variable(self, name:str, es:bool = False) -> Variable:
        """変数追加"""
        self.count+=1
        if es:
            # nc is nano-cust
            return Variable(self.count, self.sprite_pos, "__nc_runtime__."+name)
        return Variable(self.count, self.sprite_pos, name)

    def new_list(self, name:str, es:bool = False) -> ListInfo:
        """新しいリスト"""
        self.count+=1
        if es:
            # nc is nano-cust
            return ListInfo("__nc_runtime__."+name)
        return ListInfo(self.get_name()+name)

    def reset_temp(self):
        """tempをリセット（stmt毎を想定）"""
        self.temp_pos = 0

    def get_temp(self):
        """あたらしいtempを生成して返す"""
        if (self.temp_pos >= len(self.temps)):
            # new one
            temp = self.new_variable(f"temp{len(self.temps)}", True)
            self.temps.append(temp)
            self.sprite[self.sprite_pos].variables.append(temp)
        temp = self.temps[self.temp_pos]
        self.temp_pos+=1
        return temp

    def visit(self) -> Module:
        "その名の通り。"
        # what
        for i in self.program.instr:
            if isinstance(i, stmt.SpriteDeclStmt):
                self.visit_sprite(i)
        return self.module

    def visit_sprite(self, node:stmt.SpriteDeclStmt):
        """sprite作る"""
        node.name
        sym = self.ctx.sprite[node.name.ident]
        self.make_sprite(sym)        

    def make_sprite(self, sym: symbol.SpriteSymbol):
        """sprite用の環境を作っちゃう"""
        self.make_runtime()
        self.make_storage(sym)

    def make_runtime(self,):
        """runtimeを作る"""
        # need neet now cow
        self.make_runtime_variable()
        self.make_runtime_list()
        return

    def make_runtime_variable(self):
        """特に変数"""
        self.trash = self.new_variable("__trash", True)
        self.sprite[self.sprite_pos].variables.append(self.trash)
        return

    def make_runtime_list(self):
        """オブジェクト関連"""
        self.object_address: ListInfo = self.new_list("__Object_address__", True)
        self.object_clstype: ListInfo = self.new_list("__Object_CLSType", True)
        self.alloc_stack: ListInfo = self.new_list("__Aloc_Stack__", True)
        self.scope_stack: ListInfo = self.new_list("__Scope_Stack__", True)
        self.Frame: ListInfo = self.new_list("__Frame__", True)
        self.sprite[self.sprite_pos].lists.append(self.object_address)
        self.sprite[self.sprite_pos].lists.append(self.object_clstype)
        self.sprite[self.sprite_pos].lists.append(self.alloc_stack)
        self.sprite[self.sprite_pos].lists.append(self.scope_stack)
        self.sprite[self.sprite_pos].lists.append(self.Frame)
        return

    def make_storage(self,  sym: symbol.SpriteSymbol):
        self.ctx.sprites_variable[sym]
        self.make_variable(sym)
        self.make_list(sym)

    def make_variable(self,  sym: symbol.SpriteSymbol):
        return

    def make_list(self,  sym: symbol.SpriteSymbol):
        return


    def visit_program(self):

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
        match node:
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
