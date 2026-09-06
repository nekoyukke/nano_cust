from __future__ import annotations
from dataclasses import dataclass, field

_type = type

import src.frontend.ast.expr as expr
import src.frontend.ast.stmt as stmt
import src.frontend.ast.base as base

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
        # A class method is emitted once per source sprite because every
        # sprite owns its own Scratch variables and runtime lists.
        self.module_function: dict[tuple[symbol.FunctionSymbol, int], Function] = {}
        self.sprite_positions: dict[symbol.SpriteSymbol, int] = {}
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
        self.current_object: Variable
        self.return_value: Variable
        self.object_address: ListInfo
        self.object_clstype: ListInfo
        self.alloc_stack: ListInfo
        self.scope_stack: ListInfo
        self.Frame: ListInfo
        self.return_stack: ListInfo
        self.class_instances: dict[symbol.ClassSymbol, ListInfo] = {}
        self.class_ids: dict[symbol.ClassSymbol, int] = {}
        self.temps: list[Variable] = []
        self.sprite_variable: dict[symbol.Symbol, Variable] = {}
        self.sprite_list: dict[symbol.Symbol, ListInfo] = {}
        self.list_handles: dict[int, Variable] = {}
        self.next_list_handle = 1

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
            name = "__nc_runtime__."+name
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
        # Register sprite functions before generating any body.  This lets a
        # sprite call a function owned by a sprite that appears later in the
        # source file; the placeholder is completed when its owner is visited.
        sprite_index = 0
        for node in self.program.instr:
            if isinstance(node, stmt.SpriteDeclStmt):
                sprite_symbol = self.ctx.sprite[node.name.ident]
                self.sprite_positions[sprite_symbol] = sprite_index
                for function_node in node.functions:
                    if isinstance(function_node.name.sym, symbol.FunctionSymbol):
                        self.module_function[(function_node.name.sym, sprite_index)] = Function(
                            function_node.name.ident,
                            [],
                            Block([]),
                        )
                sprite_index += 1
        for i in self.program.instr:
            if isinstance(i, stmt.SpriteDeclStmt):
                self.visit_sprite(i)
        if self.ctx.entry:
            for (function_symbol, _), function in self.module_function.items():
                if function_symbol is self.ctx.entry:
                    self.module.entry_point = function
                    break
        return self.module

    def visit_sprite(self, node:stmt.SpriteDeclStmt):
        """sprite作る"""
        # sprict 共通ではないっす
        self._sprite_reset()
        sym = self.ctx.sprite[node.name.ident]
        self.make_sprite(sym)
        function_nodes: list[stmt.FunctionDeclStmt] = []
        for i in self.program.instr:
            if isinstance(i, stmt.ClassDeclStmt):
                function_nodes.extend(i.method)
        function_nodes.extend(node.functions)

        # 関数本体を生成する前に、すべての関数オブジェクトを登録する。
        # これにより再帰・前方参照を直接Function参照として表現できる。
        funcs = [self.declare_function(i) for i in function_nodes]
        for function, function_node in zip(funcs, function_nodes):
            function.instr = self.visit_stmt_entry(function_node.body)
        # make_sprite() already registered the real target in module.sprites.
        # Appending a second Sprite here used to discard the runtime lists and
        # leave each source sprite represented twice.
        target = self.sprite[self.sprite_pos]
        target.func = funcs

    def make_sprite(self, sym: symbol.SpriteSymbol):
        """sprite用の環境を作っちゃう"""
        sprite = Sprite([], [], [], sym.name)
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
        self.current_object = self.new_variable("__CurrentObject__", True)
        self.return_value = self.new_variable("__ReturnValue__", True)
        self.sprite[self.sprite_pos].variables.extend([
            self.trash,
            self.current_object,
            self.return_value,
        ])
        return

    def make_runtime_list(self):
        """オブジェクト関連"""
        self.object_address: ListInfo = self.new_list("__Object_Address__", None, True)
        self.object_clstype: ListInfo = self.new_list("__Object_Class__", None, True)
        self.alloc_stack: ListInfo = self.new_list("__AllocStack__", None, True)
        self.scope_stack: ListInfo = self.new_list("__Scope_Stack__", None, True)
        self.Frame: ListInfo = self.new_list("__Frame__", None, True)
        self.return_stack: ListInfo = self.new_list("__ReturnStack__", None, True)
        self.sprite[self.sprite_pos].lists.append(self.object_address)
        self.sprite[self.sprite_pos].lists.append(self.object_clstype)
        self.sprite[self.sprite_pos].lists.append(self.alloc_stack)
        self.sprite[self.sprite_pos].lists.append(self.scope_stack)
        self.sprite[self.sprite_pos].lists.append(self.Frame)
        self.sprite[self.sprite_pos].lists.append(self.return_stack)
        return

    def make_storage(self, sym: symbol.SpriteSymbol):
        """ストレージ生成"""
        # 特に変数
        for i in self.ctx.sprites_variable[sym]:
            self._register_storage_item(i, self.ctx.val_type[i], sym)
        # 特にclass
        for class_id, cls in enumerate(self.ctx.types.values(), start=1):
            self.class_ids[cls] = class_id
            instances = self.new_list(f"{cls.name}.__instances__", None)
            self.class_instances[cls] = instances
            self.sprite[self.sprite_pos].lists.append(instances)
            for member in cls.member:
                self._register_storage_item(member, self.ctx.member_type[member],sym)
            self._register_storage_item("__class__address__", type.ListType(type.NumberType()), sym)

    def _register_storage_item(self, item: symbol.VariableSymbol | symbol.MemberSymbol | str, tp: type.Type, sym:symbol.Symbol):
        """ストレージアイテムを保存"""
        name = self._storage_name(item)
        if isinstance(item, symbol.MemberSymbol):
            storage = self.new_list(name, None)
            self.sprite_list[item] = storage
            self.sprite[self.sprite_pos].lists.append(storage)
            return
        if isinstance(tp, type.ListType):
            self._create_nested_lists(name, tp, item if not isinstance(item, str) else sym)
            return
        variable = self.new_variable(name)
        if not isinstance(item, str):
            self.sprite_variable[item] = variable
        self.sprite[self.sprite_pos].variables.append(variable)

    def _create_nested_lists(
        self,
        name: str,
        tp: type.ListType,
        storage_symbol: symbol.Symbol,
    ):
        """Create the concrete Scratch lists needed for a nested list value."""
        current_list = self.new_list(name, None)
        self.sprite[self.sprite_pos].lists.append(current_list)
        self.sprite_list[storage_symbol] = current_list
        # A list value is passed as a scalar handle.  The current direct-list
        # storage uses this stable handle as its reference identity; the arena
        # allocator can retain the same public handle convention.
        handle = self.new_variable(f"{name}.__handle__")
        self.list_handles[id(current_list)] = handle
        self.sprite[self.sprite_pos].variables.append(handle)
        current_name = f"{name}.__inner__"
        current_tp = tp.element
        while isinstance(current_tp, type.ListType):
            current_list = self.new_list(current_name, current_list)
            self.sprite[self.sprite_pos].lists.append(current_list)
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

    def declare_function(self, node:stmt.FunctionDeclStmt, inner_name:str | None = None) -> Function:
        """関数の空IRを生成して登録する。本文は後で生成する。"""
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
        name = node.name.ident
        if inner_name:
            name += inner_name
        function_key = (sym, self.sprite_pos)
        function = self.module_function.get(function_key)
        if function is None:
            function = Function(name, args, Block([]))
        else:
            function.name = name
            function.params = args
            function.instr = Block([])
        self.module_function[function_key] = function
        return function

    def get_function(self, sym: symbol.FunctionSymbol, sprite_pos: int | None = None) -> Function:
        key = (sym, self.sprite_pos if sprite_pos is None else sprite_pos)
        return self.module_function[key]

    def visit_function(self, node:stmt.FunctionDeclStmt, inner_name:str | None = None) -> Function:
        """互換用の単発生成。相互参照がある場合はdeclare_functionを先に使う。"""
        function = self.declare_function(node, inner_name)
        function.instr = self.visit_stmt_entry(node.body)
        return function

    def visit_class(self, node:stmt.ClassDeclStmt):
        """クラスの生成、ただ、forを回しているだけ"""
        funcs :list[Function] = []
        for i in node.method:
            funcs += [self.visit_function(i)]
        return funcs

    def visit_stmt_entry(self, node:stmt.Stmt) -> Block:
        """Blockを返す、entry関数"""
        if isinstance(node, stmt.BlockStmt):
            return Block([
                ir_stmt
                for ast_stmt in node.instr
                for ir_stmt in self.visit_stmt(ast_stmt)
            ])
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
        
    def get_val_list(self, sym:symbol.Symbol) -> Variable | ListInfo:
        if sym in self.sprite_variable:
            return self.sprite_variable[sym]
        if sym in self.sprite_list:
            return self.sprite_list[sym]
        # Function-local declarations are introduced by the resolver after
        # sprite storage has been prepared.  Materialize their Scratch storage
        # on first use instead of requiring them to be sprite fields.
        if isinstance(sym, symbol.VariableSymbol) and sym in self.ctx.val_type:
            self._register_storage_item(sym, self.ctx.val_type[sym], sym)
            if sym in self.sprite_variable:
                return self.sprite_variable[sym]
            if sym in self.sprite_list:
                return self.sprite_list[sym]
        raise KeyError(sym)

    def default_value(self, tp: type.Type) -> Expr | None:
        match tp:
            case type.NumberType():
                return ImmExpr(Number(0))
            case type.StringType():
                return ImmExpr(String(""))
            case type.BooleanType():
                return ImmExpr(Number(0))  # Scratchではfalse
            case type.UserDefType():
                return ImmExpr(Number(0))  # オブジェクトアドレス0をnull予約
            case type.ListType():
                return None               # ListResetを出す
            case _:
                raise TypeError(f"unsupported type: {tp}")
    
    def visit_stmt(self, node:stmt.Stmt) -> list[Stmt]:
        """Stmtを返すvisiter"""
        # what the fuck!?
        match(node):
            # 宣言系
            case stmt.VariableDeclStmt():
                sym = node.name.sym
                if not sym:
                    raise
                storage = self.get_val_list(sym)
                if isinstance(storage, ListInfo):
                    handle = self.list_handles.get(id(storage))
                    initial: list[Stmt] = [ListReset(storage)]
                    if handle is not None:
                        initial.append(Move(handle, ImmExpr(Number(self.next_list_handle))))
                        self.next_list_handle += 1
                    return initial
                if node.left:
                    left = self.visit_expr(node.left)
                    return [*left.stmt, Move(storage, left.exp)]
                if not node.tp:
                    raise ValueError("unresolved variable declaration")
                dv = self.default_value(node.tp)
                if dv:
                    return [Move(storage, dv)]
                raise ValueError(f"no default value for {node.tp}")

            # 式・返値系
            case stmt.ExprStmt():
                left = self.visit_expr(node.expr)
                return [*left.stmt, Move(self.trash, left.exp)] # ごみに捨てる。

            case stmt.ReturnStmt():
                value = self.visit_expr(node.expr)
                return [*value.stmt, Move(self.return_value, value.exp), Return(VariableExpr(self.return_value))]

            # 制御構文系
            case stmt.Ifstmt():
                condition = self.visit_expr(node.cond)
                if not isinstance(condition.exp, BoolExpr):
                    raise TypeError("if condition must lower to BoolExpr")
                then_block = self.visit_stmt_entry(node.then_stmt)
                else_block = self.visit_stmt_entry(node.else_stmt) if node.else_stmt else None
                return [*condition.stmt, Branch(condition.exp, then_block, else_block)]
            case stmt.WhileStmt():
                condition = self.visit_expr(node.cond)
                if not isinstance(condition.exp, BoolExpr):
                    raise TypeError("while condition must lower to BoolExpr")
                return [*condition.stmt, While(condition.exp, self.visit_stmt_entry(node.loop))]
            case stmt.ForEachStmt():
                # The iteration bound is captured before the first iteration;
                # appending to the list in the body therefore cannot extend
                # this loop unexpectedly.
                if not isinstance(node.iterator, expr.Variable) or not node.iterator.sym:
                    raise NotImplementedError("for-in requires a named list")
                list_id = self.get_val_list(node.iterator.sym)
                if not isinstance(list_id, ListInfo):
                    raise TypeError("for-in requires a list")
                if not node.variable.sym:
                    raise ValueError("unresolved for-in variable")
                element = self.sprite_variable.get(node.variable.sym)
                if element is None:
                    element = self.new_variable(self._storage_name(node.variable.sym))
                    self.sprite_variable[node.variable.sym] = element
                    self.sprite[self.sprite_pos].variables.append(element)
                index = self.get_temp()
                bound = self.get_temp()
                body = self.visit_stmt_entry(node.loop)
                body.instr = [
                    Move(element, ListGet(list_id, VariableExpr(index))),
                    *body.instr,
                    Move(index, Add(VariableExpr(index), ImmExpr(Number(1)))),
                ]
                return [
                    Move(index, ImmExpr(Number(0))),
                    Move(bound, ListLength(list_id)),
                    While(Lt(VariableExpr(index), VariableExpr(bound)), body),
                ]

            # 外部操作・保存系
            case stmt.SaveNode():
                value = self.visit_expr(node.source)
                index = self.get_temp()
                # Deleting a matching item shifts the following items left,
                # so do not advance the cursor on that path.  This also
                # removes duplicate registrations defensively.
                body = Block([
                    Branch(
                        Eq(ListGet(self.alloc_stack, VariableExpr(index)), value.exp),
                        Block([ListDelete(self.alloc_stack, VariableExpr(index))]),
                        Block([Move(index, Add(VariableExpr(index), ImmExpr(Number(1))))]),
                    )
                ])
                return [
                    *value.stmt,
                    Move(index, ImmExpr(Number(0))),
                    While(Lt(VariableExpr(index), ListLength(self.alloc_stack)), body),
                ]
            case stmt.UnSaveNode():
                value = self.visit_expr(node.source)
                return [*value.stmt, ListPush(self.alloc_stack, value.exp)]

            # 漏れ防止
            case _:
                raise ValueError(f"Unknown statement node: {_type(node).__name__}")

    def visit_expr(self, node:expr.Expr) -> Expr_Result:
        """exprを返す関数。"""
        match node:
            # 二項演算・単項演算・論理・代入
            case expr.BinaryExpr():
                left = self.visit_expr(node.left)
                right = self.visit_expr(node.right)
                match (node.op):
                    case expr.BinaryKind.PLUS:
                        return Expr_Result(Add(left.exp, right.exp), [*left.stmt, *right.stmt])
                    case expr.BinaryKind.MINUS:
                        return Expr_Result(Sub(left.exp, right.exp), [*left.stmt, *right.stmt])
                    case expr.BinaryKind.MULT:
                        return Expr_Result(Mul(left.exp, right.exp), [*left.stmt, *right.stmt])
                    case expr.BinaryKind.DIV:
                        return Expr_Result(Div(left.exp, right.exp), [*left.stmt, *right.stmt])
                    case expr.BinaryKind.MOD:
                        return Expr_Result(Mod(left.exp, right.exp), [*left.stmt, *right.stmt])
                    case expr.BinaryKind.LOGIC_AND:
                        if not isinstance(left.exp, BoolExpr) or not isinstance(right.exp, BoolExpr):
                            raise TypeError("&& operands must be boolean")
                        return Expr_Result(And(left.exp, right.exp), [*left.stmt, *right.stmt])
                    case expr.BinaryKind.LOGIC_OR:
                        if not isinstance(left.exp, BoolExpr) or not isinstance(right.exp, BoolExpr):
                            raise TypeError("|| operands must be boolean")
                        return Expr_Result(Or(left.exp, right.exp), [*left.stmt, *right.stmt])
            case expr.LogicExpr():
                left = self.visit_expr(node.left)
                right = self.visit_expr(node.right)
                comparisons: dict[expr.LogicKind, type[BoolExpr]] = {
                    expr.LogicKind.EQ: Eq,
                    expr.LogicKind.NE: Ne,
                    expr.LogicKind.LT: Lt,
                    expr.LogicKind.LE: Le,
                    expr.LogicKind.GT: Gt,
                    expr.LogicKind.GE: Ge,
                }
                return Expr_Result(
                    comparisons[node.op](left.exp, right.exp),
                    [*left.stmt, *right.stmt],
                )
            case expr.UnaryExpr():
                operand = self.visit_expr(node.expr)
                if node.op is expr.UnaryKind.PLUS:
                    return operand
                return Expr_Result(Sub(ImmExpr(Number(0)), operand.exp), operand.stmt)
            case expr.AssignExpr():
                return self.visit_assign_expr(node)
            
            # 変数・呼び出し
            case expr.Variable():
                if not node.sym:
                    raise ValueError(f"unresolved variable {node.ident}")
                if isinstance(node.sym, symbol.MemberSymbol):
                    field = self.get_val_list(node.sym)
                    if not isinstance(field, ListInfo):
                        raise TypeError("object field storage must be a Scratch list")
                    return Expr_Result(
                        ListGet(field, ListGet(self.object_address, VariableExpr(self.current_object)))
                    )
                storage = self.get_val_list(node.sym)
                if not isinstance(storage, Variable):
                    handle = self.list_handles.get(id(storage))
                    if handle is not None:
                        return Expr_Result(VariableExpr(handle))
                    raise TypeError("a Scratch list cannot be used as a scalar expression")
                return Expr_Result(VariableExpr(storage))
            case expr.CallExpr():
                args = [self.visit_expr(arg) for arg in node.args]
                preceding = [instruction for arg in args for instruction in arg.stmt]
                values = [arg.exp for arg in args]
                if isinstance(node.call, expr.Variable) and node.call.sym is None:
                    return Expr_Result(
                        ImmExpr(Number(0)),
                        [*preceding, BuiltinCall(node.call.ident, values)],
                    )
                if isinstance(node.call, expr.Variable):
                    if isinstance(node.call.sym, symbol.FunctionSymbol):
                        return self.emit_call(self.get_function(node.call.sym), values, preceding)
                    if isinstance(node.call.sym, symbol.MethodSymbol):
                        return self.emit_call(
                            self.get_function(node.call.sym.fnc),
                            values,
                            preceding,
                            VariableExpr(self.current_object),
                        )
                    raise NotImplementedError("unsupported call target")
                if isinstance(node.call, expr.MemberExpr) and isinstance(node.call.member.sym, symbol.FunctionSymbol):
                    if not isinstance(node.call.expr, expr.Variable) or not isinstance(node.call.expr.sym, symbol.SpriteSymbol):
                        raise TypeError("sprite function call requires a sprite receiver")
                    target_sprite = self.sprite_positions[node.call.expr.sym]
                    return self.emit_call(
                        self.get_function(node.call.member.sym, target_sprite),
                        values,
                        preceding,
                    )
                if isinstance(node.call, expr.MemberExpr) and node.call.member.ident in {"push", "pop"}:
                    if not isinstance(node.call.expr, expr.Variable) or not node.call.expr.sym:
                        raise NotImplementedError("list methods require a named list")
                    list_id = self.get_val_list(node.call.expr.sym)
                    if not isinstance(list_id, ListInfo):
                        raise TypeError("list method receiver must be a list")
                    if node.call.member.ident == "push":
                        if len(values) != 1:
                            raise ValueError("list.push requires exactly one argument")
                        return Expr_Result(
                            ImmExpr(Number(0)),
                            [*preceding, ListPush(list_id, values[0])],
                        )
                    if values:
                        raise ValueError("list.pop takes no arguments")
                    result = self.get_temp()
                    return Expr_Result(
                        VariableExpr(result),
                        [
                            *preceding,
                            Move(result, ListGet(
                                list_id,
                                Sub(ListLength(list_id), ImmExpr(Number(1))),
                            )),
                            ListPop(list_id),
                        ],
                    )
                if isinstance(node.call, expr.MemberExpr) and isinstance(node.call.member.sym, symbol.MethodSymbol):
                    receiver = self.visit_expr(node.call.expr)
                    return self.emit_call(
                        self.get_function(node.call.member.sym.fnc),
                        values,
                        [*receiver.stmt, *preceding],
                        receiver.exp,
                    )
                raise NotImplementedError("unsupported call target")
            
            # アクセス系 (AccessExpr)
            case expr.IndexExpr():
                if not isinstance(node.expr, expr.Variable) or not node.expr.sym:
                    raise NotImplementedError("only named Scratch lists are indexable")
                list_id = self.get_val_list(node.expr.sym)
                if not isinstance(list_id, ListInfo):
                    raise TypeError("index access requires a list")
                index = self.visit_expr(node.index)
                return Expr_Result(ListGet(list_id, index.exp), index.stmt)
            case expr.MemberExpr():
                if not isinstance(node.member.sym, symbol.MemberSymbol):
                    raise NotImplementedError("only object fields are implemented")
                object_id = self.visit_expr(node.expr)
                field = self.get_val_list(node.member.sym)
                if not isinstance(field, ListInfo):
                    raise TypeError("object field storage must be a Scratch list")
                return Expr_Result(
                    ListGet(field, ListGet(self.object_address, object_id.exp)),
                    object_id.stmt,
                )
            
            # リテラル系 (Literal)
            case expr.BoolLiteral():
                return Expr_Result(ImmExpr(Number(1 if node.is_true else 0)))
            case expr.IntLiteral():
                return Expr_Result(ImmExpr(Number(node.number)))
            case expr.FloatLiteral():
                return Expr_Result(ImmExpr(Number(node.number)))
            case expr.NoneLiteral():
                return Expr_Result(ImmExpr(Number(0)))
            case expr.NullLiteral():
                return Expr_Result(ImmExpr(Number(0)))
            case expr.StringLiteral():
                return Expr_Result(ImmExpr(String(node.string)))

            case expr.NewExpr():
                if not isinstance(node.types, base.UserDef_TypeDef):
                    raise TypeError("new requires a class type")
                cls = self.ctx.types[node.types.name]
                result = self.get_temp()
                address = self.get_temp()
                instances = self.class_instances[cls]
                instructions: list[Stmt] = [
                    Move(result, Add(ListLength(self.object_clstype), ImmExpr(Number(1)))),
                    Move(address, Add(ListLength(instances), ImmExpr(Number(1)))),
                    ListPush(self.object_clstype, ImmExpr(Number(self.class_ids[cls]))),
                    ListPush(self.object_address, VariableExpr(address)),
                    ListPush(instances, ImmExpr(Number(1))),
                ]
                for member in cls.member:
                    member_type = self.ctx.member_type[member]
                    if isinstance(member_type, type.ListType):
                        raise NotImplementedError("list-valued object fields are not implemented")
                    default = self.default_value(member_type)
                    if default is None:
                        raise TypeError(f"no default for member type {member_type}")
                    field = self.get_val_list(member)
                    if not isinstance(field, ListInfo):
                        raise TypeError("object field storage must be a Scratch list")
                    instructions.append(ListPush(field, default))
                return Expr_Result(VariableExpr(result), instructions)
            
            # 漏れ防止
            case _:
                raise ValueError(f"Unknown expression node: {_type(node).__name__}")

    def emit_call(
        self,
        callee: Function,
        params: list[Expr],
        preceding: list[Stmt],
        receiver: Expr | None = None,
    ) -> Expr_Result:
        """Emit a call frame and materialize its result in a temporary.

        The return stack stores pairs: the caller's current object followed by
        the caller's return-value cell.  The pair is restored in reverse order
        after the callee has produced its result.
        """
        result = self.get_temp()
        top = lambda: ListLength(self.return_stack)
        target = receiver or VariableExpr(self.current_object)
        instructions: list[Stmt] = [
            *preceding,
            ListPush(self.return_stack, VariableExpr(self.current_object)),
            ListPush(self.return_stack, VariableExpr(self.return_value)),
            Move(self.current_object, target),
            Call(callee, params),
            Move(result, VariableExpr(self.return_value)),
            Move(self.return_value, ListGet(self.return_stack, top())),
            ListDelete(self.return_stack, top()),
            Move(self.current_object, ListGet(self.return_stack, top())),
            ListDelete(self.return_stack, top()),
        ]
        return Expr_Result(VariableExpr(result), instructions)

    def visit_assign_expr(self, node:expr.AssignExpr) -> Expr_Result:
        right = self.visit_expr(node.right)
        if node.op is not expr.AssignKind.ASSIGN:
            raise NotImplementedError(f"assignment operator {node.op} is not implemented")
        match node.left:
            case expr.Variable():
                if not node.left.sym:
                    raise ValueError(f"unresolved variable {node.left.ident}")
                if isinstance(node.left.sym, symbol.MemberSymbol):
                    field = self.get_val_list(node.left.sym)
                    if not isinstance(field, ListInfo):
                        raise TypeError("object field storage must be a Scratch list")
                    return Expr_Result(
                        right.exp,
                        [*right.stmt, ListSet(
                            field,
                            ListGet(self.object_address, VariableExpr(self.current_object)),
                            right.exp,
                        )],
                    )
                target = self.get_val_list(node.left.sym)
                if not isinstance(target, Variable):
                    raise TypeError("a Scratch list cannot be assigned as a scalar")
                return Expr_Result(right.exp, [*right.stmt, Move(target, right.exp)])
            case expr.IndexExpr():
                if not isinstance(node.left.expr, expr.Variable) or not node.left.expr.sym:
                    raise NotImplementedError("only named Scratch lists are assignable")
                list_id = self.get_val_list(node.left.expr.sym)
                if not isinstance(list_id, ListInfo):
                    raise TypeError("index assignment requires a list")
                index = self.visit_expr(node.left.index)
                return Expr_Result(
                    right.exp,
                    [*index.stmt, *right.stmt, ListSet(list_id, index.exp, right.exp)],
                )
            case expr.MemberExpr():
                if not isinstance(node.left.member.sym, symbol.MemberSymbol):
                    raise NotImplementedError("only object field assignment is implemented")
                object_id = self.visit_expr(node.left.expr)
                field = self.get_val_list(node.left.member.sym)
                if not isinstance(field, ListInfo):
                    raise TypeError("object field storage must be a Scratch list")
                return Expr_Result(
                    right.exp,
                    [*object_id.stmt, *right.stmt,
                     ListSet(field, ListGet(self.object_address, object_id.exp), right.exp)],
                )
            case _:
                raise NotImplementedError("only variables and list indexes are assignable")
