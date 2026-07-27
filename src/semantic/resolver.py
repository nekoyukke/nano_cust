from __future__ import annotations

# resolve and typecheck.
# Notably, it processes members and methods as well.

import src.ast.stmt as stmt
import src.ast.base as base
import src.ast.expr as expr

import src.ast.symbol as symbol

from src.ast.scope import Scope

from src.ast.context import Context

import src.ast.type as types

from utils.error.collector import KinakoCollectorError
from utils.error.base import KinakoHelp, KinakoRelatedInfo, KinakoBaseError

class Resolver():
    def __init__(self, program: stmt.ProgramStmt, source:str, ctx:Context, scp:Scope) -> None:
        self.program: stmt.ProgramStmt = program
        self.source: str = source
        self.scope:Scope = scp
        self.ctx:Context = ctx
        self.error:list[KinakoBaseError] = []
        self.ret_tp: types.Type | None = None


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
        self.visit_Program(self.program)
        return self.scope

    def visit_Program(self, program:stmt.ProgramStmt):
        for instr in program.instr:
            match (instr):# isn't smart
                case stmt.VariableDeclStmt():
                    # ohohohohoho
                    # self.visit_variable(instr) # miss!!!
                    sym = self.scope.lookup(instr.name.ident)
                    if not sym:
                        continue # need error message.(maybe)
                    if not isinstance(sym, symbol.VariableSymbol):
                        continue # need erro...
                    tp:types.Type = self.TypeDef2Type(instr.contract) # toilet paper
                    if instr.left: # toilet paper
                        if (tp_left := self.visit_expr(instr.left)): # toilet paper
                            if tp != tp_left: # toilet paper
                                self.CallError(f"型が違います。設定元:{tp}, 検知先: {tp_left}", instr)
                    instr.tp = tp # toilet paper
                    instr.name.sym = sym
                    self.scope.sym[instr.name.ident] = sym
                    self.ctx.val_type[sym] = tp # ha?
                case stmt.FunctionDeclStmt():
                    self.visit_function(instr)
                case stmt.ClassDeclStmt():
                    self.visit_class(instr)
                case _: # what !?!?!??!
                    continue

    def visit_stmt(self, node:stmt.Stmt) -> bool:
        match(node):
            case stmt.VariableDeclStmt():
                self.visit_variable(node)
                return False
            case stmt.FunctionDeclStmt():
                self.visit_function(node) # we may not need this
            case stmt.ClassDeclStmt():
                self.visit_class(node) # too.
            case stmt.Ifstmt():
                self.visit_if(node)
            case stmt.WhileStmt():
                self.visit_while(node)
            case stmt.ForEachStmt():
                self.visit_foreach(node)
            case stmt.ReturnStmt():
                self.visit_return(node)
            case stmt.BlockStmt():
                self.scope = self.scope.push()
                for i in node.instr:
                    self.visit_stmt(i)
                self.scope = self.scope.pop()
            case _:
                for i in node.get_child():
                    if isinstance(i, stmt.Stmt):self.visit_stmt(i)
                    if isinstance(i, expr.Expr):self.visit_expr(i)

    def visit_return(self, node:stmt.ReturnStmt):
        tp = self.visit_expr(node.expr)
        self.ret_tp

    def visit_foreach(self, node:stmt.ForEachStmt):
        # (=^.^=) < hello ~
        itt_tp = self.visit_expr(node.iterator)
        var_tp = self.visit_expr(node.variable) # now now cow now cow cow
        if not isinstance(itt_tp, types.ListType):
            self.CallError(f"繰り返し不可能な入力。{itt_tp}", node)
            return
        if not var_tp: # if var is not none
            self.CallError(f"不明な型。{var_tp}", node)
            return
        if not itt_tp.element == var_tp:
            self.CallError(f"繰り返し不可能な型。{itt_tp} not eq {var_tp}", node)
            return
        self.scope = self.scope.push() # push corn
        # smybloo
        sym = symbol.VariableSymbol(
            node.variable.ident,
            node
        )
        self.scope.sym[node.variable.ident] = sym
        self.ctx.val_type[sym] = var_tp
        self.visit_stmt(node.loop)
        self.scope = self.scope.pop() # pop corn!!!

    def visit_while(self, node:stmt.WhileStmt):
        cond_tp = self.visit_expr(node.cond) # (cond_tp looks like Condom)
        if not isinstance(cond_tp, types.BooleanType):
            self.CallError(f"Boolean値のみの入力。{cond_tp}", node)
            return
        self.scope = self.scope.push() # push corn
        self.visit_stmt(node.loop)
        self.scope = self.scope.pop() # pop corn!!!

    def visit_if(self, node:stmt.Ifstmt):
        cond_tp = self.visit_expr(node.cond)
        if not isinstance(cond_tp, types.BooleanType):
            self.CallError(f"Boolean値のみの入力。{cond_tp}", node)
            return
        # what???????
        self.scope = self.scope.push() # push corn <= ???
        self.visit_stmt(node.then_stmt)
        self.scope = self.scope.pop() # pop corn!!!
        self.scope = self.scope.push() # push corn <= ???
        if node.else_stmt:self.visit_stmt(node.else_stmt)
        self.scope = self.scope.pop() # pop corn!!!
        return
        
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
        return
    
    def visit_function(self, node:stmt.FunctionDeclStmt):
        # Add a variable symbol
        # function is not good. class to
        # ctx and scope have already been added function symbol and variable symbol
        sym = self.scope.get_global().sym[node.name.ident] # what doing??
        if not isinstance(sym, symbol.FunctionSymbol):
            return self.CallError("Oops...不明なシンボル[管理者向け]", node)
        self.scope = self.scope.push()# push | new scope
        parms: list[types.Type] = []
        for i, j in zip(sym.parms, node.params): # fuckin'program
            self.scope.sym[i.name] = i
            self.ctx.val_type[i] = self.TypeDef2Type(j.type)
            parms.append(self.ctx.val_type[i]) # what !?
        # symbol
        tp:types.Function = types.Function(
            self.TypeDef2Type(node.result),
            parms
        )
        node.tp = tp;self.ctx.func_type[sym] = tp
        self.ret_tp = tp.ret
        self.visit_stmt(node.body) # body
        self.scope = self.scope.pop()# pop
        self.ret_tp = None
        return

    def visit_class(self, node:stmt.ClassDeclStmt):
        # no
        # getter
        sym_cls = self.ctx.types[node.name.ident]
        # fuckin'program
        self.scope = self.scope.push()
        for mb, ms in zip(node.member, sym_cls.member): # ms looks like Microsoft.
            tp:types.Type = self.TypeDef2Type(mb.contract)
            if mb.left:
                if (tp_left := self.visit_expr(mb.left)):
                    if tp != tp_left:
                        self.CallError(f"型が違います。設定元:{tp}, 検知先: {tp_left}", node)
            mb.tp = tp
            mb.name.sym = ms
            self.scope.sym[mb.name.ident] = ms
        for md,cmd in zip(node.method, sym_cls.method):
            # md looks like MDMA
            sym = cmd # command prompt
            if not isinstance(sym, symbol.FunctionSymbol):
                return self.CallError("Oops...不明なシンボル[管理者向け]", node)
            self.scope = self.scope.push()# push | new scope
            parms: list[types.Type] = []
            for i, j in zip(sym.parms, md.params): # fuckin'program
                self.scope.sym[i.name] = i
                self.ctx.val_type[i] = self.TypeDef2Type(j.type)
                parms.append(self.ctx.val_type[i]) # what !?
            # symbol
            tp_:types.Function = types.Function(
                self.TypeDef2Type(md.result),
                parms
            )
            md.tp = tp_;self.ctx.func_type[sym] = tp_
            self.visit_stmt(md.body) # body
            self.ret_tp = tp_.ret
            self.scope = self.scope.pop()# pop
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
                    # else:
                elif sym in set(self.ctx.func_type): # tp looks like toilet paper.
                    if isinstance(sym, symbol.FunctionSymbol) and isinstance(sym.decl, stmt.FunctionDeclStmt) and sym.decl.tp:
                        return sym.decl.tp
                    # else:
                elif sym in set(self.ctx.types.values()) and isinstance(sym, symbol.ClassSymbol):
                    # self.ctx.func_type looks like fuck_type
                    return types.UserDefType(sym=sym)
                self.CallError("エラー！！！", node) # fuckin error
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
            case _:
                pass