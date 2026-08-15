from __future__ import annotations
from dataclasses import dataclass, field

_type = type

import src.frontend.ast.expr as expr
import src.frontend.ast.stmt as stmt

from src.frontend.ast.context import Context
import src.frontend.ast.symbol as symbol
import src.frontend.ast.type as type

from src.backend.ir.boolexpr import *
from src.backend.ir.expr import *
from src.backend.ir.flow import *
from src.backend.ir.instr import *
from src.backend.ir.list import *
from src.backend.ir.module import *
from src.backend.ir.stmt import *
from src.backend.ir.value import *


@dataclass
class Expr_Result():
    exp:Expr
    stmt: list[Stmt] = field(default_factory=list[Stmt])

class IRGenerator:
    def __init__(self, Program:stmt.ProgramStmt, source:str, ctx:Context) -> None:
        self.module = Module([], None)
        self.program:stmt.ProgramStmt = Program
        self.ctx:Context = ctx
        # fuckin containers
        # fuckint meens "fuck int" and "fuckin t"
        
        # symbolの変換
        self.module_function: dict[symbol.FunctionSymbol, int] = {}
        # sprite整理
        self.sprite: list[Sprite] = []
        # spriteの今のindex
        self.sprite_pos:int = 0
        self._sprite_reset()

    def _sprite_reset(self):
        # sprict 共通ではないっす
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
        self.sprite_variable: dict[symbol.Symbol, Variable] = {}
        self.sprite_list: dict[symbol.Symbol, ListInfo] = {}

    def new_variable(self, name:str, es:bool = False) -> Variable:
        """変数追加"""
        self.count+=1
        if es:
            # nc is nano-cust
            return Variable(self.count, self.sprite_pos, "__nc_runtime__."+name)
        return Variable(self.count, self.sprite_pos, name)

    def new_list(self, name:str, nested:None|ListInfo, es:bool = False) -> ListInfo:
        """新しいリスト"""
        self.count+=1
        if es:
            # nc is nano-cust
            return ListInfo("__nc_runtime__."+name, nested)
        return ListInfo(name, nested)

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
        "その名の通り。エントリーポイント"
        # what
        for i in self.program.instr:
            if isinstance(i, stmt.SpriteDeclStmt):
                self.visit_sprite(i)
        return self.module

    def visit_sprite(self, node:stmt.SpriteDeclStmt):
        """sprite作る"""
        # sprict 共通ではないっす
        self._sprite_reset()
        sym = self.ctx.sprite[node.name.ident]
        self.make_sprite(sym)
        funcs:list[Function] = []
        for i in self.program.instr:
            if isinstance(i, stmt.ClassDeclStmt):
                funcs += self.visit_class(i)
        for i in node.functions:
            if not isinstance(i.name.sym, symbol.FunctionSymbol):
                continue
            symbols = i.name.sym
            self.module_function[symbols] = -1
        for i in node.functions:
            funcs.append(self.visit_function(i))
        self.module.sprites.append(Sprite(
            funcs,
            list(self.sprite_list.values()),
            list(self.sprite_variable.values())
        ))

    def make_sprite(self, sym: symbol.SpriteSymbol):
        """sprite用の環境を作っちゃう"""
        sprite = Sprite([], [], [])
        self.sprite.append(sprite)
        self.module.sprites.append(sprite)
        self.sprite_pos = len(self.sprite) - 1
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
        self.object_address: ListInfo = self.new_list("__Object_address__", None, True)
        self.object_clstype: ListInfo = self.new_list("__Object_CLSType", None, True)
        self.alloc_stack: ListInfo = self.new_list("__Aloc_Stack__", None, True)
        self.scope_stack: ListInfo = self.new_list("__Scope_Stack__", None, True)
        self.Frame: ListInfo = self.new_list("__Frame__", None, True)
        self.sprite[self.sprite_pos].lists.append(self.object_address)
        self.sprite[self.sprite_pos].lists.append(self.object_clstype)
        self.sprite[self.sprite_pos].lists.append(self.alloc_stack)
        self.sprite[self.sprite_pos].lists.append(self.scope_stack)
        self.sprite[self.sprite_pos].lists.append(self.Frame)
        return

    def make_storage(self, sym: symbol.SpriteSymbol):
        """ストレージ生成"""
        # 特に変数
        for i in self.ctx.sprites_variable[sym]:
            self._register_storage_item(i, self.ctx.val_type[i], sym)
        # 特にclass
        for cls in self.ctx.types.values():
            for member in cls.member:
                self._register_storage_item(member, self.ctx.member_type[member],sym)
            self._register_storage_item("__class__address__", type.ListType(type.NumberType()), sym)

    def _register_storage_item(self, item: symbol.VariableSymbol | symbol.MemberSymbol | str, tp: type.Type, sym:symbol.Symbol):
        """ストレージアイテムを保存"""
        name = self._storage_name(item)
        if isinstance(tp, type.ListType):
            self._create_nested_lists(name, tp, sym)
            return

        variable = self.new_variable(name)
        if not isinstance(item, str):
            self.sprite_variable[item] = variable
        self.sprite[self.sprite_pos].variables.append(variable)

    def _create_nested_lists(self, name: str, tp: type.ListType, sym:symbol.Symbol):
        """リスト生成が必須なら作る"""
        # first
        current_list: ListInfo = self.new_list(name, None)
        self.sprite[self.sprite_pos].lists.append(current_list)
        self.sprite_list[sym] = current_list
        current_name = f"{name}.__inner__"
        current_tp = tp.element
        # next
        while isinstance(current_tp, type.ListType):
            lst = self.new_list(current_name, current_list)
            current_list = lst
            self.sprite[self.sprite_pos].lists.append(lst)
            current_name = f"{current_name}.__inner__"
            current_tp = current_tp.element

    def _storage_name(self, item: symbol.VariableSymbol | symbol.MemberSymbol | str | symbol.MethodSymbol | symbol.ArgsSymbol) -> str:
        """ストレージ名を生成"""
        if isinstance(item, str):
            return "__nc_runtime__"+item+f"{id(item):x}"[-4:]
        # なんで過去の私memberとmethodのメンバ統一しない？？？？？？
        if isinstance(item, symbol.MemberSymbol):
            return f"{item.cls.name}.__member__.{item.val.name}"+f"{id(item):x}"[-4:]
        if isinstance(item, symbol.MethodSymbol):
            return f"{item.cls.name}.__method__.{item.fnc.name}"+f"{id(item):x}"[-4:]
        if isinstance(item, symbol.ArgsSymbol):
            return f"{item.name}.__at__.{item.idx}"+f"{id(item):x}"[-4:]
        return item.name+f"{id(item):x}"[-4:]

    def visit_function(self, node:stmt.FunctionDeclStmt, inner_name:str | None = None):
        """関数を回す。inner_nameは名前を追加"""
        if not isinstance(node.name.sym, symbol.FunctionSymbol | symbol.MethodSymbol):
            raise RuntimeError(node.name.sym)
        elif isinstance(node.name.sym, symbol.MethodSymbol):
            sym = node.name.sym.fnc
        else:
            sym = node.name.sym
        args:list[Variable] = []
        for p in sym.parms:
            name = self._storage_name(p)
            val = self.new_variable(name)
            self.sprite_variable[p] = val
            self.sprite[self.sprite_pos].variables.append(val)
            args.append(val) # おいしい
        # for i in # なにこれ
        body = self.visit_stmt_entry(node.body) # visitisicisit
        name = node.name.ident
        if inner_name:
            name += inner_name
        return Function(
            node.name.ident,
            args,
            body
        )

    def visit_class(self, node:stmt.ClassDeclStmt):
        """クラスの生成、ただ、forを回しているだけ"""
        funcs :list[Function] = []
        for i in node.method:
            funcs += [self.visit_function(i)]
        return funcs

    def visit_stmt_entry(self, node:stmt.Stmt) -> Block:
        """Blockを返す、entry関数"""
        if isinstance(node, stmt.BlockStmt):
            return Block(
                *[self.visit_stmt(i) for i in node.instr]
            )
        body = self.visit_stmt(node)
        if isinstance(body, Block):
            return body
        return Block(body)

    def get_type(self, sym:symbol.Symbol) -> type.Type:
        match (sym):
            case symbol.ArgsSymbol():
                return self.ctx.args_type[sym]
            case symbol.VariableSymbol():
                return self.ctx.val_type[sym]
            case symbol.FunctionSymbol():
                return self.ctx.func_type[sym]
            case symbol.MemberSymbol():
                return self.ctx.member_type[sym]
            case symbol.MethodSymbol():
                return self.ctx.method_type[sym]
            case _:
                raise

    def get_default_value(self, sym:symbol.Symbol) -> ImmExpr | None:
        tp = self.get_type(sym)
        if not isinstance(tp, type.BuildinType):
            return None
        match(tp):
            case _:
                pass
        
    def get_val_list(self, sym:symbol.Symbol):
        if sym in self.sprite_variable:
            return self.sprite_variable[sym]
        if sym in self.sprite_list:
            return self.sprite_list[sym]
        raise

    def visit_stmt(self, node:stmt.Stmt) -> list[Stmt]:
        """Stmtを返すvisiter"""
        # what the fuck!?
        match(node):
            # 宣言系
            case stmt.VariableDeclStmt():
                sym = node.name.sym
                if not sym:
                    raise
                variable = self.get_val_list(sym)
                # symbolをもとにげっちゅする
                if isinstance(variable, ListInfo):
                    return [ListReset(variable)] # 消去
                else:
                    if node.left:
                        left = self.visit_expr(node.left)
                        # val
                        return [*left.stmt, Move(variable, left.exp)]
                    # 何もしなくていいよん
                    # デフォ値
                    return [Move(variable, self.get_default_data())]

            # 式・返値系
            case stmt.ExprStmt():
                left = self.visit_expr(node.expr)
                return [*left.stmt, Move(self.trash, left.exp)] # ごみに捨てる。

            case stmt.ReturnStmt():
                pass

            # 制御構文系
            case stmt.Ifstmt():
                pass
            case stmt.WhileStmt():
                pass
            case stmt.ForEachStmt():
                pass

            # 外部操作・保存系
            case stmt.SaveNode():
                pass
            case stmt.UnSaveNode():
                pass

            # 漏れ防止
            case _:
                raise ValueError(f"Unknown statement node: {_type(node).__name__}")

    def visit_expr(self, node:expr.Expr) -> Expr_Result:
        """exprを返す関数。"""
        match node:
            # 二項演算・単項演算・論理・代入
            case expr.BinaryExpr():
                pass
            case expr.UnaryExpr():
                pass
            case expr.LogicExpr():
                pass
            case expr.AssignExpr():
                return self.visit_assign_expr(node)
            
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
                return Expr_Result(ImmExpr(Number(1 if node.is_true else 0)))
            case expr.IntLiteral():
                return Expr_Result(ImmExpr(Number(node.number)))
            case expr.FloatLiteral():
                return Expr_Result(ImmExpr(Number(node.number)))
            case expr.NoneLiteral():
                pass
            case expr.NullLiteral():
                pass
            case expr.StringLiteral():
                return Expr_Result(ImmExpr(String(node.string)))

            case expr.NewExpr():
                pass
            
            # 漏れ防止
            case _:
                raise ValueError(f"Unknown expression node: {_type(node).__name__}")

    def visit_assign_expr(self, node:expr.AssignExpr) -> Expr_Result:
        self.get_nest_L_value(node.right)
        match (node.op):
            case expr.AssignKind.ASSIGN:
                node.right # は？死ねや
                return Expr_Result(
                    node.left,
                )
            case expr.AssignKind.PULS:
                pass
            case expr.AssignKind.MINUS:
                pass
            case expr.AssignKind.MULT:
                pass
            case expr.AssignKind.DIV:
                pass
            case _:
                raise

    def get_nest_L_value(self, node:expr.Expr):
        match(node):
            case expr.MemberExpr():
                if not node.member.sym:
                    raise
                val = self.varis    [node.member.sym]
                self.get_nest_L_value(node.expr)
            case expr.IndexExpr():
                pass
            case expr.Variable():
                pass
            case expr.CallExpr():
                pass
            case _:
                raise # 知るか！？