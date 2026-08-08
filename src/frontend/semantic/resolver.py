from __future__ import annotations

# resolve and typecheck.
# Notably, it processes members and methods as well.

import src.frontend.ast.stmt as stmt
import src.frontend.ast.base as base
import src.frontend.ast.expr as expr

import src.frontend.ast.symbol as symbol

from src.frontend.ast.scope import Scope

from src.frontend.ast.context import Context

import src.frontend.ast.type as types

from src.utils.error.collector import KinakoCollectorError
from src.utils.error.base import KinakoHelp, KinakoRelatedInfo, KinakoBaseError

class Resolver():
    def __init__(self, program: stmt.ProgramStmt, source:str, ctx:Context, scp:Scope) -> None:
        self.program: stmt.ProgramStmt = program
        self.source: str = source
        self.scope:Scope = scp
        self.ctx:Context = ctx
        self.error:list[KinakoBaseError] = []
        self.ret_tp: types.Type | None = None
        self.sprite_sym:symbol.SpriteSymbol | None = None


    def CallError(
            self, message:str ,node:base.ASTNode,
            related: list[KinakoRelatedInfo] | None = None,
            help: list[KinakoHelp] | None = None
        ):
        """
        エラー呼び出し
        """
        err =  KinakoCollectorError(
            message,
            node.line,
            node.col,
            self.source,
            node.len,
            related,
            help
        )
        self.error.append(err)

    def CallError_Symbol(self, node:base.ASTNode, string:str):
        sym = self.scope.sym[string]
        match (sym):
            case symbol.VariableSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.decl.line, sym.decl.col, sym.decl.len)])
            case symbol.FunctionSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.decl.line, sym.decl.col, sym.decl.len)])
            case symbol.ClassSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.decl.line, sym.decl.col, sym.decl.len)])
            case symbol.MemberSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.val.decl.line, sym.val.decl.col, sym.val.decl.len)])
            case symbol.MethodSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.fnc.decl.line, sym.fnc.decl.col, sym.fnc.decl.len)])
            case symbol.ArgsSymbol():
                self.CallError(f"すでに'{string}'は存在します。", node, [KinakoRelatedInfo("かぶっている宣言場所", sym.decl.line, sym.decl.col, sym.decl.len)])
            case _:
                self.CallError(f"すでに'{string}'は存在します。", node)


    def TypeDef2Type(self, typed:base.TypeDef) -> types.Type:
        match (typed):
            case base.Number():
                return types.NumberType()
            case base.String():
                return types.StringType()
            case base.Boolean():
                return types.BooleanType()
            case base.List():
                return types.ListType(self.TypeDef2Type(typed.element))
            case base.UserDef_TypeDef():
                return types.UserDefType(self.ctx.types[typed.name])
            case _:
                raise

    def resolve(self):
        for instruction in self.program.instr:
            if isinstance(instruction, stmt.SpriteDeclStmt):
                self.declare_sprite_types(instruction)
        self.visit_Program(self.program)
        return self.scope

    def visit_Program(self, program:stmt.ProgramStmt):
        for instr in program.instr:
            match (instr):# isn't smart
                # case stmt.VariableDeclStmt():
                #     # ohohohohoho
                #     # self.visit_variable(instr) # miss!!!
                #     sym = self.scope.lookup(instr.name.ident)
                #     if not sym:
                #         continue # need error message.(maybe)
                #     if not isinstance(sym, symbol.VariableSymbol):
                #         continue # need erro...
                #     tp:types.Type = self.TypeDef2Type(instr.contract) # toilet paper
                #     if instr.left: # toilet paper
                #         if (tp_left := self.visit_expr(instr.left)): # toilet paper
                #             if tp != tp_left: # toilet paper
                #                 self.CallError(f"型が違います。設定元:{tp}, 検知先: {tp_left}", instr)
                #     instr.tp = tp # toilet paper
                #     instr.name.sym = sym
                #     self.scope.sym[instr.name.ident] = sym
                #     self.ctx.val_type[sym] = tp # ha?
                # case stmt.FunctionDeclStmt():
                #     self.visit_function(instr)
                case stmt.ClassDeclStmt():
                    self.visit_class(instr)
                case stmt.SpriteDeclStmt():
                    self.visit_sprite(instr)
                case _: # what !?!?!??!
                    continue

    def visit_stmt(self, node:stmt.Stmt) -> bool:
        match(node):
            case stmt.VariableDeclStmt():
                self.visit_variable(node)
                return False
            case stmt.FunctionDeclStmt():
                self.visit_function(node) # we may not need this
                return False
            case stmt.ClassDeclStmt():
                self.visit_class(node) # too.
                return False
            case stmt.SpriteDeclStmt():
                self.visit_sprite(node)
                return False
            case stmt.Ifstmt():
                return self.visit_if(node)
            case stmt.WhileStmt():
                return self.visit_while(node)
            case stmt.ForEachStmt():
                return self.visit_foreach(node)
            case stmt.ReturnStmt():
                return self.visit_return(node)
            case stmt.BlockStmt():
                self.scope = self.scope.push()
                ret = False
                for i in node.instr:
                    ret = ret or self.visit_stmt(i)
                self.scope = self.scope.pop()
                return ret
            case _:
                for i in node.get_child():
                    if isinstance(i, stmt.Stmt):self.visit_stmt(i)
                    if isinstance(i, expr.Expr):self.visit_expr(i)
                return False

    def visit_return(self, node:stmt.ReturnStmt):
        tp = self.visit_expr(node.expr)
        if self.ret_tp != tp:
            self.CallError(f"型が一致しません。宣言元:{self.ret_tp}実際の方:{tp}", node)
        return True

    def visit_foreach(self, node:stmt.ForEachStmt):
        # (=^.^=) < hello ~
        itt_tp = self.visit_expr(node.iterator)
        var_tp = self.visit_expr(node.variable) # now now cow now cow cow
        if not isinstance(itt_tp, types.ListType):
            self.CallError(f"繰り返し不可能な入力。{itt_tp}", node)
            return False
        if not var_tp: # if var is not none
            self.CallError(f"不明な型。{var_tp}", node)
            return False
        if not itt_tp.element == var_tp:
            self.CallError(f"繰り返し不可能な型。{itt_tp} not eq {var_tp}", node)
            return False
        self.scope = self.scope.push() # push corn
        # smybloo
        sym = symbol.VariableSymbol(
            node.variable.ident,
            node
        )
        self.scope.sym[node.variable.ident] = sym
        self.ctx.val_type[sym] = var_tp
        ret = self.visit_stmt(node.loop)
        self.scope = self.scope.pop() # pop corn!!!
        return ret

    def visit_while(self, node:stmt.WhileStmt):
        cond_tp = self.visit_expr(node.cond) # (cond_tp looks like Condom)
        if not isinstance(cond_tp, types.BooleanType):
            self.CallError(f"Boolean値のみの入力。{cond_tp}", node)
            return False
        self.scope = self.scope.push() # push corn
        ret = self.visit_stmt(node.loop)
        self.scope = self.scope.pop() # pop corn!!!
        return ret

    def visit_if(self, node:stmt.Ifstmt):
        cond_tp = self.visit_expr(node.cond)
        if not isinstance(cond_tp, types.BooleanType):
            self.CallError(f"Boolean値のみの入力。{cond_tp}", node)
            return False
        # what???????
        self.scope = self.scope.push() # push corn <= ???
        ret =  self.visit_stmt(node.then_stmt)
        self.scope = self.scope.pop() # pop corn!!!
        self.scope = self.scope.push() # push corn <= ???
        if node.else_stmt: ret = ret and self.visit_stmt(node.else_stmt)
        else: ret = ret and False
        self.scope = self.scope.pop() # pop corn!!!
        return ret
        
    def visit_variable(self, node:stmt.VariableDeclStmt):
        tp:types.Type = self.TypeDef2Type(node.contract)
        if node.left:
            if (tp_left := self.visit_expr(node.left)):
                if tp != tp_left:
                    self.CallError(f"型が違います。設定元:{tp}, 検知先: {tp_left}", node)
        node.tp = tp
        sym = symbol.VariableSymbol(
            node.name.ident,
            node
        )
        node.name.sym = sym
        self.scope.sym[node.name.ident] = sym
        self.ctx.val_type[sym] = tp
        if self.sprite_sym:
            self.ctx.sprites_variable[self.sprite_sym].append(sym)
        return
    
    def visit_function(self, node:stmt.FunctionDeclStmt, function_symbol:symbol.FunctionSymbol | None = None):
        # Add a variable symbol
        # function is not good. class to
        # ctx and scope have already been added function symbol and variable symbol
        sym = function_symbol or self.scope.get_global().sym[node.name.ident] # what doing??
        if not isinstance(sym, symbol.FunctionSymbol):
            return self.CallError("Oops...不明なシンボル[管理者向け]", node)
        self.scope = self.scope.push()# push | new scope
        parms: list[types.Type] = []
        # for i, j in zip(sym.parms, node.params): # fuckin'program
        for i in range(len(sym.parms)): # fuckin'program
            self.scope.sym[sym.parms[i].name] = sym.parms[i]
            # print("",sym.parms[i], hex(id(sym.parms[i])))
            self.ctx.args_type[sym.parms[i]] = self.TypeDef2Type(node.params[i].type)
            parms.append(self.ctx.args_type[sym.parms[i]]) # what !?
        # symbol
        tp:types.Function = types.Function(
            self.TypeDef2Type(node.result),
            parms
        )
        node.tp = tp;self.ctx.func_type[sym] = tp
        self.ret_tp = tp.ret
        res = self.visit_stmt(node.body) # body
        if not res: # trueならok
            self.CallError("functionから帰りません。", node)
        self.scope = self.scope.pop()# pop
        self.ret_tp = None
        return

    def visit_sprite(self, node:stmt.SpriteDeclStmt):
        sprite_symbol = self.scope.get_global().sym.get(node.name.ident)
        if not isinstance(sprite_symbol, symbol.SpriteSymbol):
            self.CallError("Sprite symbol was not collected", node)
            return
        self.sprite_sym = sprite_symbol
        self.ctx.sprites_args[self.sprite_sym] = []
        self.ctx.sprites_func[self.sprite_sym] = []
        self.ctx.sprites_variable[self.sprite_sym] = []
        self.declare_sprite_types(node)
        for function_symbol, function_node in zip(sprite_symbol.functions, node.functions):
            self.ctx.sprites_args[self.sprite_sym] += function_symbol.parms
            self.ctx.sprites_func[self.sprite_sym].append(function_symbol)
            self.visit_function(function_node, function_symbol)

    def declare_sprite_types(self, node:stmt.SpriteDeclStmt):
        sprite_symbol = self.scope.get_global().sym.get(node.name.ident)
        if not isinstance(sprite_symbol, symbol.SpriteSymbol):
            return
        for function_symbol, function_node in zip(sprite_symbol.functions, node.functions):
            self.ctx.func_type[function_symbol] = types.Function(
                self.TypeDef2Type(function_node.result),
                [self.TypeDef2Type(parameter.type) for parameter in function_node.params]
            )

    def visit_class(self, node:stmt.ClassDeclStmt):
        # no
        # getter
        sym_cls = self.ctx.types[node.name.ident]
        # fuckin'program
        self.scope = self.scope.push()
        # for mb, ms in zip(node.member, sym_cls.member): # ms looks like Microsoft.
        for i in range(len(node.member)):
            mb, ms = node.member[i], sym_cls.member[i]
            tp:types.Type = self.TypeDef2Type(mb.contract)
            if mb.left:
                if (tp_left := self.visit_expr(mb.left)):
                    if tp != tp_left:
                        self.CallError(f"型が違います。設定元:{tp}, 検知先: {tp_left}", node)
                        return
            self.ctx.member_type[ms] = tp
            mb.tp = tp
            mb.name.sym = ms
            self.scope.sym[mb.name.ident] = ms
        # for md,cmd in zip(node.method, sym_cls.method):
        for i in range(len(node.method)):
            md, cmd = node.method[i], sym_cls.method[i]
            # md looks like MDMA
            sym = cmd # command prompt
            self.scope = self.scope.push()# push | new scope
            parms: list[types.Type] = []
            # for i, j in zip(sym.parms, md.params): # fuckin'program
            for j in range(len(sym.fnc.parms)): # fuckin'program
                sp = sym.fnc.parms[j]
                mp = md.params[j]
                self.scope.sym[sp.name] = sp
                self.ctx.args_type[sp] = self.TypeDef2Type(mp.type)
                parms.append(self.ctx.args_type[sp]) # what !?
            # symbol
            tp_:types.Function = types.Function(
                self.TypeDef2Type(md.result),
                parms
            )
            md.tp = tp_;self.ctx.method_type[sym] = tp_
            self.ret_tp = tp_.ret
            res = self.visit_stmt(md.body) # body
            if not res: # trueならok
                self.CallError("functionから帰りません。", node)
            self.scope = self.scope.pop()# pop
            self.ret_tp = None
        self.scope = self.scope.pop()# pop corn🍿
        return

    def visit_expr(self, node:expr.Expr) -> types.Type | None:
        match(node):
            case expr.Variable():
                sym = self.scope.lookup(node.ident)
                node.sym = sym
                if not sym: # if none
                    self.CallError("symbolが不明。宣言されていません。", node)
                    return None
                if sym in self.ctx.val_type:# in variable
                    # ok
                    if isinstance(sym, symbol.VariableSymbol) and isinstance(sym.decl, stmt.VariableDeclStmt):
                        return sym.decl.tp
                    if isinstance(sym, symbol.VariableSymbol) and isinstance(sym.decl, stmt.ForEachStmt):
                        sym_ = sym.decl.variable.sym
                        if isinstance(sym_, symbol.VariableSymbol):
                            return self.ctx.val_type[sym_]
                    # else:
                elif sym in self.ctx.func_type: # tp looks like toilet paper.
                    if isinstance(sym, symbol.FunctionSymbol) and isinstance(sym.decl, stmt.FunctionDeclStmt) and sym.decl.tp:
                        return sym.decl.tp
                    # else:
                elif sym in self.ctx.types.values() and isinstance(sym, symbol.ClassSymbol):
                    # self.ctx.func_type looks like fuck_type
                    return types.UserDefType(sym=sym)
                elif sym in self.ctx.args_type and isinstance(sym, symbol.ArgsSymbol):
                    return self.ctx.args_type[sym]
                elif sym in self.ctx.method_type and isinstance(sym, symbol.MethodSymbol):
                    return self.ctx.method_type[sym]
                elif sym in self.ctx.member_type and isinstance(sym, symbol.MemberSymbol):
                    return self.ctx.member_type[sym]
                self.CallError(f"不明なエラー！！！", node, help = [KinakoHelp(f"scope:{self.ctx}"), KinakoHelp(f"symbol:{sym}#{f"{id(sym):x}"[-4:]}")]) # fuckin error
                return None
            case expr.BinaryExpr():
                lt = self.visit_expr(node.left)
                rt = self.visit_expr(node.right)
                if not (lt and rt):
                    self.CallError(f"型演算が失敗しました。", node)
                    return None
                if lt == rt:
                    return lt
                self.CallError(f"型が違います。{lt}と{rt}", node)
            case expr.LogicExpr():
                lt = self.visit_expr(node.left)
                rt = self.visit_expr(node.right)
                if not (lt and rt):
                    self.CallError(f"型演算が失敗しました。", node)
                    return None
                if lt == rt:
                    return types.BooleanType()
                self.CallError(f"型が違います。{lt}と{rt}", node)
            case expr.AssignExpr():
                if not isinstance(node.left, expr.AccessExpr|expr.Variable):
                    self.CallError("代入可能値ではありません", node)
                lt = self.visit_expr(node.left)
                rt = self.visit_expr(node.right)
                if not (lt and rt):
                    self.CallError(f"型演算が失敗しました。", node)
                    return None
                if lt == rt:
                    return lt
                self.CallError(f"型が違います。{lt}と{rt}", node)
            case expr.UnaryExpr():
                # 単項演算子 (+x, -x など)
                return self.visit_expr(node)

            case expr.CallExpr():
                # 関数呼び出し (foo(a, b))
                call = self.visit_expr(node.call)
                type_list: list[types.Type] = []
                for i in node.args:
                    i_t = self.visit_expr(i)
                    if i_t:
                        type_list.append(i_t)
                    else:
                        self.CallError(f"不明な値。{i}", node)
                        return
                if not isinstance(call, types.Function):
                    self.CallError(f"呼び出し不可能な型, {call}", node.call)
                    return
                if len(type_list) != len(call.parms):
                    self.CallError(
                        f"引数の個数が一致しません。期待: {len(call.parms)}個, 実際: {len(type_list)}個",
                        node
                    )
                    return None

                mismatches:list[str] = []
                for i, (actual, expected) in enumerate(zip(type_list, call.parms)):
                    if actual != expected:
                        mismatches.append(f"第{i + 1}引数 (期待: {expected}, 実際: {actual})")

                if mismatches:
                    error_msg = "引数の型が一致しません:\n  - " + "\n  - ".join(mismatches)
                    self.CallError(error_msg, node)
                    return None
                # 製鋼
                return call.ret
            case expr.IndexExpr():
                # 配列・リストアクセス (arr[i])
                base = self.visit_expr(node.expr)
                idx = self.visit_expr(node.index)
                if not isinstance(idx, types.NumberType):
                    self.CallError(f"インデックスアクセスはnumberが強制されます{idx}", node)
                    return None
                if not isinstance(base, types.ListType):
                    self.CallError(f"添え字不可能な値, {base}", node)
                    return None
                return base.element

            case expr.MemberExpr():
                if isinstance(node.expr, expr.Variable):
                    sprite = self.scope.lookup(node.expr.ident)
                    if isinstance(sprite, symbol.SpriteSymbol):
                        node.expr.sym = sprite
                        for function_symbol in sprite.functions:
                            if function_symbol.name == node.member.ident:
                                node.member.sym = function_symbol
                                return self.ctx.func_type.get(function_symbol)
                        self.CallError(f"Sprite '{sprite.name}' に関数 '{node.member.ident}' はありません", node)
                        return None
                # メンバーアクセス (obj.field)
                base = self.visit_expr(node.expr)
                if not base: # eq if base is not none
                    self.CallError("不明な型", node)
                    return
                # ok
                match (base):
                    case types.UserDefType():
                        sym = base.sym
                        if sym not in set(self.ctx.types.values()) or not isinstance(sym, symbol.ClassSymbol):
                            self.CallError("不明[Errrorororoororororor]", node)
                            return None
                        mm = [i.val.name for i in sym.member]
                        mb = [i.fnc.name for i in sym.method]
                        if node.member.ident in mm:
                            # ok
                            idx = mm.index(node.member.ident)
                            return self.ctx.member_type[sym.member[idx]]
                        if node.member.ident in mb:
                            # ok
                            idx = mb.index(node.member.ident)
                            return self.ctx.method_type[sym.method[idx]]
                        # うんこ(Unknown)
                        self.CallError("不明なメンバー名", node)
                    case types.NumberType():
                        pass
                    case types.ListType():
                        if node.member.ident == "push":
                            return types.Function(types.BooleanType(), [base.element])
                        if node.member.ident == "pop":
                            return types.Function(base.element, [])
                    case types.StringType():
                        pass
                    case types.BooleanType():
                        pass
                    case _:
                        raise
            case expr.BoolLiteral():
                return types.BooleanType()

            case expr.IntLiteral():
                return types.NumberType()

            case expr.FloatLiteral():
                return types.NumberType()

            case expr.StringLiteral():
                return types.StringType()

            case _:
                pass
