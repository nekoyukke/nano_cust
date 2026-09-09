from __future__ import annotations

import json
import zipfile
from dataclasses import fields, is_dataclass
from hashlib import md5
from pathlib import Path
from typing import Any

from src.backend.ir.boolexpr import And, Eq, Ge, Gt, Le, Lt, Ne, Not, Or
from src.backend.ir.expr import Add, BuiltinBoolExpr, BuiltinExpr, Div, ImmExpr, Mod, Mul, Sub, VariableExpr
from src.backend.ir.flow import Block, Branch, BuiltinCall, Call, Return, While
from src.backend.ir.list import ListGet, ListLength
from src.backend.ir.module import Function, Module, Sprite
from src.backend.ir.stmt import (
    ListDelete,
    ListInsert,
    ListPop,
    ListPush,
    ListReset,
    ListSet,
    Move,
)
from src.backend.ir.value import ListInfo, Number, String, Variable


class SB3Emitter:
    """Lower the Scratch-oriented IR into a self-contained Scratch 3 project."""

    def __init__(self, module: Module) -> None:
        self.module = module
        # Each source ``sprite`` remains a distinct Scratch target.  Function
        # calls across targets use the explicit broadcast calling convention
        # below; source sprites are not merely namespaces.
        self.flattened = False
        self.function_origin: dict[Function, str] = {}
        self.function_return_values: dict[Function, Variable] = {}
        if self.flattened:
            functions: list[Function] = []
            lists: list[ListInfo] = []
            variables: list[Variable] = []
            for sprite in module.sprites:
                return_value = next(
                    variable for variable in sprite.variables
                    if variable.name.endswith("__ReturnValue__")
                )
                for function in sprite.func:
                    functions.append(function)
                    self.function_origin[function] = sprite.name
                    self.function_return_values[function] = return_value
                lists.extend(sprite.lists)
                variables.extend(sprite.variables)
            self.sprites = [Sprite(functions, lists, variables, "nano_cust Runtime")]
        else:
            self.sprites = module.sprites
            for sprite in self.sprites:
                for function in sprite.func:
                    self.function_origin[function] = sprite.name
                    self.function_return_values[function] = next(
                        variable for variable in sprite.variables
                        if variable.name.endswith("__ReturnValue__")
                    )
        self.counter = 0
        self.blocks: dict[str, dict] = {}
        self.variable_ids: dict[int, str] = {}
        self.list_ids: dict[int, str] = {}
        self.argument_variables: set[int] = set()
        self.current_function: Function | None = None
        self.procedures: dict[Function, tuple[str, list[str], list[str]]] = {}
        self.assets: dict[str, bytes] = {}
        self.function_owner: dict[Function, int] = {}
        self.current_sprite: Sprite | None = None
        self.current_sprite_index: int | None = None
        self.current_return_value: Variable | None = None
        self.current_object: Variable | None = None
        self.current_return_stack: ListInfo | None = None
        self.return_flag_id: str | None = None
        self.return_flag_stack_id: str | None = None
        self.global_variables: dict[str, str] = {}
        self.global_lists: dict[str, str] = {}
        self.broadcasts: dict[str, str] = {}
        self.broadcast_ids: dict[str, str] = {}
        self.uses_pen = False

        for sprite_index, sprite in enumerate(self.sprites):
            for function in sprite.func:
                self.function_owner[function] = sprite_index

        self.live_functions = self.find_live_functions()
        self.remove_dead_literal_assignments()

        self.functions_requiring_return_flag = {
            function
            for sprite in self.sprites
            for function in sprite.func
            if function in self.live_functions and self.function_requires_return_flag(function)
        }
        self.sprites_requiring_return_flag = {
            index
            for index, sprite in enumerate(self.sprites)
            if any(function in self.functions_requiring_return_flag for function in sprite.func)
        }
        self.cross_sprite_functions = self.find_cross_sprite_functions()

        max_args = 0
        for sprite_index, sprite in enumerate(self.sprites):
            for function in sprite.func:
                if function in self.cross_sprite_functions:
                    max_args = max(max_args, len(function.params))
        for name in ([] if self.flattened or not self.cross_sprite_functions else ["__nc_cross_return_value__", *[
            f"__nc_cross_arg_{index}__" for index in range(max_args)
        ]]):
            self.global_variables[name] = self.new_id("g")
        # A broadcast handler can itself make a foreign-sprite call.  The
        # argument and result cells above are therefore a calling convention,
        # not permanent storage: save their old values before each call and
        # restore them afterwards.
        for name in ([] if self.flattened or not self.cross_sprite_functions else ["__nc_cross_return_stack__", *[
            f"__nc_cross_arg_{index}_stack__" for index in range(max_args)
        ]]):
            self.global_lists[name] = self.new_id("gl")
        for function, sprite_index in self.function_owner.items():
            if self.flattened or function not in self.cross_sprite_functions:
                continue
            message = f"__nc_call_{sprite_index}_{function.name}__"
            identifier = self.new_id("broadcast")
            # project.json stores broadcasts as {broadcast-id: display-name},
            # while blocks refer to them as [display-name, broadcast-id].
            self.broadcasts[identifier] = message
            self.broadcast_ids[message] = identifier

    def find_cross_sprite_functions(self) -> set[Function]:
        """Return only functions that are actually reached from another sprite."""
        cross_sprite_functions: set[Function] = set()

        def visit_block(block: Block, owner: int) -> None:
            for instruction in block.instr:
                if isinstance(instruction, Call):
                    if self.function_owner[instruction.callee] != owner:
                        cross_sprite_functions.add(instruction.callee)
                elif isinstance(instruction, Branch):
                    visit_block(instruction.true_label, owner)
                    if instruction.false_label is not None:
                        visit_block(instruction.false_label, owner)
                elif isinstance(instruction, While):
                    visit_block(instruction.body, owner)

        for function, owner in self.function_owner.items():
            if function not in self.live_functions:
                continue
            visit_block(function.instr, owner)
        return cross_sprite_functions

    def find_live_functions(self) -> set[Function]:
        """Mark functions reachable from Main.main through IR Call edges."""
        if self.module.entry_point is None:
            return set()
        live = {self.module.entry_point}
        pending = [self.module.entry_point]

        def called_by(block: Block) -> list[Function]:
            callees: list[Function] = []
            for instruction in block.instr:
                if isinstance(instruction, Call):
                    callees.append(instruction.callee)
                elif isinstance(instruction, Branch):
                    callees.extend(called_by(instruction.true_label))
                    if instruction.false_label is not None:
                        callees.extend(called_by(instruction.false_label))
                elif isinstance(instruction, While):
                    callees.extend(called_by(instruction.body))
            return callees

        while pending:
            function = pending.pop()
            for callee in called_by(function.instr):
                if callee not in live:
                    live.add(callee)
                    pending.append(callee)
        return live

    def remove_dead_literal_assignments(self) -> None:
        """Drop stores to variables that are never read and have no effects."""
        reads: set[int] = set()

        def read_expr(value: Any) -> None:
            if isinstance(value, VariableExpr):
                reads.add(id(value.value))
                return
            if is_dataclass(value):
                for field in fields(value):
                    read_expr(getattr(value, field.name))
            elif isinstance(value, list):
                for item in value:
                    read_expr(item)

        def collect(block: Block) -> None:
            for instruction in block.instr:
                if isinstance(instruction, Move):
                    read_expr(instruction.value)
                elif isinstance(instruction, (ListSet, ListInsert, ListPush)):
                    read_expr(instruction.index if hasattr(instruction, "index") else instruction.value)
                    if hasattr(instruction, "value"):
                        read_expr(instruction.value)
                elif isinstance(instruction, Branch):
                    read_expr(instruction.cond); collect(instruction.true_label)
                    if instruction.false_label is not None: collect(instruction.false_label)
                elif isinstance(instruction, While):
                    read_expr(instruction.cond); collect(instruction.body)
                elif isinstance(instruction, Return) and instruction.value is not None:
                    read_expr(instruction.value)
                elif isinstance(instruction, Call):
                    for parameter in instruction.params: read_expr(parameter)

        for function in self.live_functions:
            collect(function.instr)

        def prune(block: Block) -> None:
            kept: list[Stmt] = []
            for instruction in block.instr:
                if isinstance(instruction, Branch):
                    prune(instruction.true_label)
                    if instruction.false_label is not None: prune(instruction.false_label)
                elif isinstance(instruction, While):
                    prune(instruction.body)
                if (
                    isinstance(instruction, Move)
                    and id(instruction.result) not in reads
                    and isinstance(instruction.value, ImmExpr)
                ):
                    continue
                kept.append(instruction)
            block.instr = kept

        for function in self.live_functions:
            prune(function.instr)

    def function_requires_return_flag(self, function: Function) -> bool:
        """Whether this function needs a runtime flag to implement early return."""
        return self.block_requires_return_flag(function.instr)

    def block_requires_return_flag(self, block: Block) -> bool:
        for index, statement in enumerate(block.instr):
            if isinstance(statement, While) and self.block_may_return(statement.body):
                return True
            if isinstance(statement, Branch):
                if self.block_requires_return_flag(statement.true_label):
                    return True
                if statement.false_label and self.block_requires_return_flag(statement.false_label):
                    return True
            if self.statement_may_return(statement) and index + 1 < len(block.instr):
                return True
        return False

    def default_costume(self, name: str) -> dict[str, Any]:
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1" viewBox="0 0 1 1"></svg>'
        asset_id = md5(svg).hexdigest()
        self.assets[f"{asset_id}.svg"] = svg
        return {
            "assetId": asset_id,
            "name": name,
            "md5ext": f"{asset_id}.svg",
            "dataFormat": "svg",
            "bitmapResolution": 1,
            "rotationCenterX": 0,
            "rotationCenterY": 0,
        }

    def new_id(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}{self.counter}"

    def block(self, opcode: str, *, parent: str | None = None, top: bool = False) -> str:
        block_id = self.new_id("b")
        self.blocks[block_id] = {
            "opcode": opcode,
            "next": None,
            "parent": parent,
            "inputs": {},
            "fields": {},
            "shadow": False,
            "topLevel": top,
        }
        if top:
            self.blocks[block_id]["x"] = 0
            self.blocks[block_id]["y"] = 0
        return block_id

    def primitive(self, value: Number | String) -> list[Any]:
        if isinstance(value, Number):
            return [1, [4, str(value.value)]]
        return [1, [10, value.value]]

    def reporter_input(self, block_id: str, name: str, reporter: str | list[Any]) -> None:
        self.blocks[block_id]["inputs"][name] = reporter if isinstance(reporter, list) else [3, reporter, [10, ""]]
        if isinstance(reporter, str):
            self.blocks[reporter]["parent"] = block_id

    def variable_id(self, variable: Variable) -> str:
        return self.variable_ids[id(variable)]

    def list_id(self, list_info: ListInfo) -> str:
        return self.list_ids[id(list_info)]

    def variable_reporter(self, variable: Variable, parent: str | None = None) -> str:
        if id(variable) in self.argument_variables:
            block_id = self.block("argument_reporter_string_number", parent=parent)
            self.blocks[block_id]["fields"] = {"VALUE": [variable.name, None]}
            return block_id
        block_id = self.block("data_variable", parent=parent)
        self.blocks[block_id]["fields"] = {"VARIABLE": [variable.name, self.variable_id(variable)]}
        return block_id

    def internal_variable_reporter(self, name: str, identifier: str, parent: str | None = None) -> str:
        block_id = self.block("data_variable", parent=parent)
        self.blocks[block_id]["fields"] = {"VARIABLE": [name, identifier]}
        return block_id

    def set_internal_variable(self, name: str, identifier: str, value: Any, parent: str | None = None) -> str:
        block_id = self.block("data_setvariableto", parent=parent)
        self.blocks[block_id]["fields"] = {"VARIABLE": [name, identifier]}
        self.reporter_input(block_id, "VALUE", value)
        return block_id

    def list_length(self, list_info: ListInfo, parent: str | None = None) -> str:
        block_id = self.block("data_lengthoflist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [list_info.list_name, self.list_id(list_info)]}
        return block_id

    def global_reporter(self, name: str, parent: str | None = None) -> str:
        block_id = self.block("data_variable", parent=parent)
        self.blocks[block_id]["fields"] = {"VARIABLE": [name, self.global_variables[name]]}
        return block_id

    def set_global(self, name: str, value: Any, parent: str | None = None) -> str:
        block_id = self.block("data_setvariableto", parent=parent)
        self.blocks[block_id]["fields"] = {"VARIABLE": [name, self.global_variables[name]]}
        self.reporter_input(block_id, "VALUE", value)
        return block_id

    def global_list_length(self, name: str, parent: str | None = None) -> str:
        block_id = self.block("data_lengthoflist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [name, self.global_lists[name]]}
        return block_id

    def runtime_list_push(self, list_info: ListInfo, value: Any, parent: str | None = None) -> str:
        block_id = self.block("data_addtolist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [list_info.list_name, self.list_id(list_info)]}
        self.reporter_input(block_id, "ITEM", value)
        return block_id

    def runtime_list_last(self, list_info: ListInfo, parent: str | None = None) -> str:
        block_id = self.block("data_itemoflist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [list_info.list_name, self.list_id(list_info)]}
        self.reporter_input(block_id, "INDEX", self.list_length(list_info))
        return block_id

    def runtime_list_pop(self, list_info: ListInfo, parent: str | None = None) -> str:
        block_id = self.block("data_deleteoflist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [list_info.list_name, self.list_id(list_info)]}
        self.reporter_input(block_id, "INDEX", self.list_length(list_info))
        return block_id

    def global_list_last(self, name: str, parent: str | None = None) -> str:
        block_id = self.block("data_itemoflist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [name, self.global_lists[name]]}
        self.reporter_input(block_id, "INDEX", self.global_list_length(name))
        return block_id

    def push_global_list(self, name: str, value: Any, parent: str | None = None) -> str:
        block_id = self.block("data_addtolist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [name, self.global_lists[name]]}
        self.reporter_input(block_id, "ITEM", value)
        return block_id

    def pop_global_list(self, name: str, parent: str | None = None) -> str:
        block_id = self.block("data_deleteoflist", parent=parent)
        self.blocks[block_id]["fields"] = {"LIST": [name, self.global_lists[name]]}
        self.reporter_input(block_id, "INDEX", self.global_list_length(name))
        return block_id

    def one_based(self, index: Expr, parent: str | None = None) -> str:
        add = self.block("operator_add", parent=parent)
        self.reporter_input(add, "NUM1", self.expr(index))
        self.reporter_input(add, "NUM2", self.primitive(Number(1)))
        return add

    def expr(self, expression: Expr, parent: str | None = None) -> str | list[Any]:
        if isinstance(expression, ImmExpr):
            return self.primitive(expression.value)
        if isinstance(expression, VariableExpr):
            return self.variable_reporter(expression.value, parent)
        if isinstance(expression, BuiltinExpr | BuiltinBoolExpr):
            reporters = {
                "KeyPressed": ("sensing_keypressed", ("KEY_OPTION",)),
                "MousePressed": ("sensing_mousedown", ()),
                "MouseX": ("sensing_mousex", ()),
                "MouseY": ("sensing_mousey", ()),
                "Random": ("operator_random", ("FROM", "TO")),
                "Join": ("operator_join", ("STRING1", "STRING2")),
                "LetterOf": ("operator_letter_of", ("LETTER", "STRING")),
                "TextLength": ("operator_length", ("STRING",)),
                "Contains": ("operator_contains", ("STRING1", "STRING2")),
                "Round": ("operator_round", ("NUM",)),
                "Timer": ("sensing_timer", ()),
            }
            math_operations = {
                "Abs": "abs", "Floor": "floor", "Ceil": "ceiling", "Sqrt": "sqrt",
                "Sin": "sin", "Cos": "cos", "Tan": "tan", "Asin": "asin",
                "Acos": "acos", "Atan": "atan", "Ln": "ln", "Log": "log",
                "Exp": "e ^", "Exp10": "10 ^",
            }
            if expression.name in math_operations:
                block_id = self.block("operator_mathop", parent=parent)
                self.blocks[block_id]["fields"] = {
                    "OPERATOR": [math_operations[expression.name], None]
                }
                self.reporter_input(block_id, "NUM", self.expr(expression.params[0]))
                return block_id
            try:
                opcode, inputs = reporters[expression.name]
            except KeyError as error:
                raise NotImplementedError(f"unsupported builtin reporter: {expression.name}") from error
            block_id = self.block(opcode, parent=parent)
            for input_name, value in zip(inputs, expression.params):
                self.reporter_input(block_id, input_name, self.expr(value))
            return block_id
        if isinstance(expression, ListLength):
            return self.list_length(expression.list_id, parent)
        if isinstance(expression, ListGet):
            block_id = self.block("data_itemoflist", parent=parent)
            self.reporter_input(block_id, "INDEX", self.one_based(expression.index))
            self.blocks[block_id]["fields"] = {"LIST": [expression.list_id.list_name, self.list_id(expression.list_id)]}
            return block_id

        arithmetic = {
            Add: "operator_add", Sub: "operator_subtract", Mul: "operator_multiply",
            Div: "operator_divide", Mod: "operator_mod",
        }
        for ir_type, opcode in arithmetic.items():
            if isinstance(expression, ir_type):
                block_id = self.block(opcode, parent=parent)
                self.reporter_input(block_id, "NUM1", self.expr(expression.left))
                self.reporter_input(block_id, "NUM2", self.expr(expression.right))
                return block_id

        boolean = {
            Eq: "operator_equals", Lt: "operator_lt", Gt: "operator_gt",
            And: "operator_and", Or: "operator_or",
        }
        for ir_type, opcode in boolean.items():
            if isinstance(expression, ir_type):
                block_id = self.block(opcode, parent=parent)
                self.reporter_input(block_id, "OPERAND1" if ir_type in (And, Or) else "OPERAND1", self.expr(expression.left))
                self.reporter_input(block_id, "OPERAND2" if ir_type in (And, Or) else "OPERAND2", self.expr(expression.right))
                return block_id
        if isinstance(expression, Not):
            block_id = self.block("operator_not", parent=parent)
            self.reporter_input(block_id, "OPERAND", self.expr(expression.value))
            return block_id
        if isinstance(expression, Ne):
            block_id = self.block("operator_not", parent=parent)
            equals = self.block("operator_equals", parent=block_id)
            self.reporter_input(equals, "OPERAND1", self.expr(expression.left))
            self.reporter_input(equals, "OPERAND2", self.expr(expression.right))
            self.reporter_input(block_id, "OPERAND", equals)
            return block_id
        if isinstance(expression, Le):
            return self.expr(Or(Lt(expression.left, expression.right), Eq(expression.left, expression.right)), parent)
        if isinstance(expression, Ge):
            return self.expr(Or(Gt(expression.left, expression.right), Eq(expression.left, expression.right)), parent)
        raise NotImplementedError(f"unsupported expression: {type(expression).__name__}")

    def attach_substack(self, owner: str, name: str, block: Block) -> None:
        first = self.emit_statements(block.instr, owner)
        self.blocks[owner]["inputs"][name] = [2, first] if first else [2, None]

    def procedure_call(self, call: Call, parent: str | None) -> str:
        return self.procedure_call_inputs(call.callee, [self.expr(value) for value in call.params], parent)

    def can_inline(self, function: Function) -> bool:
        """Inline only straight-line, terminal-return functions safely."""
        return (
            "inline" in function.annotations
            and self.function_owner[function] == self.current_sprite_index
            and bool(function.instr.instr)
            and isinstance(function.instr.instr[-1], Return)
            and not any(isinstance(statement, (Branch, While)) for statement in function.instr.instr)
        )

    def inline_call(self, call: Call, parent: str | None) -> str:
        """Expand a compact @inline function at its call site."""
        first: str | None = None
        previous: str | None = None
        for parameter, value in zip(call.callee.params, call.params):
            assignment = self.emit_statement(Move(parameter, value), parent)
            assert assignment is not None
            first, previous = self.link(first, previous, assignment)
        body = self.emit_statements(call.callee.instr.instr[:-1], parent)
        if body is not None:
            first, previous = self.link(first, previous, body)
        if first is None:
            # A zero-argument `return` function still has the Move that
            # materializes its result, therefore this is defensive only.
            raise RuntimeError("inline call produced no blocks")
        return first

    def procedure_call_inputs(self, callee: Function, values: list[str | list[Any]], parent: str | None, *, manage_return_flag: bool = True) -> str:
        procedure = self.procedures[callee]
        proccode, argument_ids, _ = procedure
        block_id = self.block("procedures_call", parent=parent)
        self.blocks[block_id]["mutation"] = {
            "tagName": "mutation", "children": [], "proccode": proccode,
            "argumentids": json.dumps(argument_ids), "warp": "false",
        }
        for argument_id, value in zip(argument_ids, values):
            self.reporter_input(block_id, argument_id, value)
        if not manage_return_flag or callee not in self.functions_requiring_return_flag:
            return block_id
        if self.return_flag_id is None or self.return_flag_stack_id is None:
            raise RuntimeError("procedure call outside a sprite target")

        # Scratch has no return instruction for a custom block.  A callee sets
        # the flag when it executes IR Return.  The flag is saved per call so
        # recursive calls cannot stop their caller's remaining statements.
        first: str | None = None
        previous: str | None = None
        for current in (
            self.push_internal_return_flag(parent),
            self.set_internal_variable("__nc_backend_return_flag__", self.return_flag_id, self.primitive(Number(0)), parent),
            block_id,
            self.restore_internal_return_flag(parent),
        ):
            first, previous = self.link(first, previous, current)
        assert first is not None
        return first

    def push_internal_return_flag(self, parent: str | None) -> str:
        assert self.return_flag_id is not None and self.return_flag_stack_id is not None
        block_id = self.block("data_addtolist", parent=parent)
        self.blocks[block_id]["fields"] = {
            "LIST": ["__nc_backend_return_flag_stack__", self.return_flag_stack_id]
        }
        self.reporter_input(block_id, "ITEM", self.internal_variable_reporter("__nc_backend_return_flag__", self.return_flag_id))
        return block_id

    def restore_internal_return_flag(self, parent: str | None) -> str:
        assert self.return_flag_id is not None and self.return_flag_stack_id is not None
        set_flag = self.set_internal_variable(
            "__nc_backend_return_flag__", self.return_flag_id,
            self.internal_return_flag_stack_last(), parent,
        )
        delete = self.block("data_deleteoflist", parent=parent)
        self.blocks[delete]["fields"] = {
            "LIST": ["__nc_backend_return_flag_stack__", self.return_flag_stack_id]
        }
        self.reporter_input(delete, "INDEX", self.internal_return_flag_stack_length())
        self.blocks[set_flag]["next"] = delete
        self.blocks[delete]["parent"] = parent
        return set_flag

    def internal_return_flag_stack_length(self, parent: str | None = None) -> str:
        assert self.return_flag_stack_id is not None
        block_id = self.block("data_lengthoflist", parent=parent)
        self.blocks[block_id]["fields"] = {
            "LIST": ["__nc_backend_return_flag_stack__", self.return_flag_stack_id]
        }
        return block_id

    def internal_return_flag_stack_last(self, parent: str | None = None) -> str:
        assert self.return_flag_stack_id is not None
        block_id = self.block("data_itemoflist", parent=parent)
        self.blocks[block_id]["fields"] = {
            "LIST": ["__nc_backend_return_flag_stack__", self.return_flag_stack_id]
        }
        self.reporter_input(block_id, "INDEX", self.internal_return_flag_stack_length())
        return block_id

    def link(self, first: str | None, previous: str | None, block_id: str) -> tuple[str, str]:
        if first is None:
            first = block_id
        if previous is not None:
            self.blocks[previous]["next"] = block_id
            self.blocks[block_id]["parent"] = self.blocks[previous]["parent"]
        return first, self.tail(block_id)

    def tail(self, first: str) -> str:
        current = first
        while self.blocks[current]["next"] is not None:
            current = self.blocks[current]["next"]
        return current

    def cross_sprite_call(self, call: Call, parent: str | None) -> str:
        """Lower a foreign-sprite call through a synchronous broadcast."""
        if self.current_return_value is None:
            raise RuntimeError("cross-sprite call outside a sprite target")
        first: str | None = None
        previous: str | None = None
        def append(block_id: str) -> None:
            nonlocal first, previous
            first, previous = self.link(first, previous, block_id)

        # Preserve the complete foreign-call frame.  Saving every argument
        # slot, rather than just the callee's arity, is what makes A -> B -> C
        # calls restore A's pending B arguments exactly.
        append(self.push_global_list(
            "__nc_cross_return_stack__",
            self.global_reporter("__nc_cross_return_value__"),
            parent,
        ))
        for index in range(len(self.global_lists) - 1):
            name = f"__nc_cross_arg_{index}__"
            append(self.push_global_list(
                f"__nc_cross_arg_{index}_stack__", self.global_reporter(name), parent
            ))
        for index, value in enumerate(call.params):
            set_arg = self.set_global(f"__nc_cross_arg_{index}__", self.expr(value), parent)
            append(set_arg)
        owner = self.function_owner[call.callee]
        message = f"__nc_call_{owner}_{call.callee.name}__"
        broadcast = self.block("event_broadcastandwait", parent=parent)
        self.blocks[broadcast]["fields"] = {"BROADCAST_OPTION": [message, self.broadcast_ids[message]]}
        append(broadcast)
        restore = self.block("data_setvariableto", parent=parent)
        self.blocks[restore]["fields"] = {
            "VARIABLE": [self.current_return_value.name, self.variable_id(self.current_return_value)]
        }
        self.reporter_input(restore, "VALUE", self.global_reporter("__nc_cross_return_value__"))
        append(restore)
        for index in reversed(range(len(self.global_lists) - 1)):
            name = f"__nc_cross_arg_{index}__"
            append(self.set_global(
                name, self.global_list_last(f"__nc_cross_arg_{index}_stack__"), parent
            ))
            append(self.pop_global_list(f"__nc_cross_arg_{index}_stack__", parent))
        append(self.set_global(
            "__nc_cross_return_value__",
            self.global_list_last("__nc_cross_return_stack__"),
            parent,
        ))
        append(self.pop_global_list("__nc_cross_return_stack__", parent))
        if first is None:
            raise RuntimeError("call lowering produced no blocks")
        return first

    def emit_cross_sprite_handler(self, function: Function) -> None:
        owner = self.function_owner[function]
        message = f"__nc_call_{owner}_{function.name}__"
        hat = self.block("event_whenbroadcastreceived", top=True)
        self.blocks[hat]["fields"] = {"BROADCAST_OPTION": [message, self.broadcast_ids[message]]}
        inputs = [self.global_reporter(f"__nc_cross_arg_{index}__") for index in range(len(function.params))]
        call = self.procedure_call_inputs(function, inputs, hat)
        if (
            self.current_return_value is None
            or self.current_object is None
            or self.current_return_stack is None
        ):
            raise RuntimeError("cross-sprite handler has no return value variable")
        copy_result = self.set_global(
            "__nc_cross_return_value__",
            self.variable_reporter(self.current_return_value),
            hat,
        )
        # The target may already have a suspended procedure which made the
        # foreign call.  Re-entering it through a broadcast must therefore use
        # the same two-cell frame convention as IRGen's normal calls.
        sequence = [
            self.runtime_list_push(
                self.current_return_stack,
                self.variable_reporter(self.current_object),
                hat,
            ),
            self.runtime_list_push(
                self.current_return_stack,
                self.variable_reporter(self.current_return_value),
                hat,
            ),
            call,
            copy_result,
            self.set_internal_variable(
                self.current_return_value.name,
                self.variable_id(self.current_return_value),
                self.runtime_list_last(self.current_return_stack),
                hat,
            ),
            self.runtime_list_pop(self.current_return_stack, hat),
            self.set_internal_variable(
                self.current_object.name,
                self.variable_id(self.current_object),
                self.runtime_list_last(self.current_return_stack),
                hat,
            ),
            self.runtime_list_pop(self.current_return_stack, hat),
        ]
        # A foreign call is only emitted from an active statement.  Once its
        # handler has restored the suspended frame, its caller must be
        # runnable again even when this target was re-entered by a nested
        # broadcast.  Terminal-return-only targets have no such flag.
        if self.return_flag_id is not None:
            sequence.append(self.set_internal_variable(
                "__nc_backend_return_flag__", self.return_flag_id,
                self.primitive(Number(0)), hat,
            ))
        first: str | None = None
        previous: str | None = None
        for block_id in sequence:
            first, previous = self.link(first, previous, block_id)
        assert first is not None
        self.blocks[hat]["next"] = first

    def emit_statement(self, statement: Stmt, parent: str | None) -> str | None:
        if isinstance(statement, BuiltinCall):
            opcodes = {
                "Move": ("motion_gotoxy", ("X", "Y")),
                "MoveSteps": ("motion_movesteps", ("STEPS",)),
                "TurnRight": ("motion_turnright", ("DEGREES",)),
                "TurnLeft": ("motion_turnleft", ("DEGREES",)),
                "SetDirection": ("motion_pointindirection", ("DIRECTION",)),
                "PenDown": ("pen_penDown", ()),
                "PenUp": ("pen_penUp", ()),
                "PenColor": ("pen_setPenColorToColor", ("COLOR",)),
                "PenSize": ("pen_setPenSizeTo", ("SIZE",)),
                "ClearPen": ("pen_clear", ()),
                "Wait": ("control_wait", ("DURATION",)),
                "Say": ("looks_say", ("MESSAGE",)),
                "SayFor": ("looks_sayforsecs", ("MESSAGE", "SECS")),
                "Think": ("looks_think", ("MESSAGE",)),
                "ThinkFor": ("looks_thinkforsecs", ("MESSAGE", "SECS")),
                "Show": ("looks_show", ()), "Hide": ("looks_hide", ()),
                "NextCostume": ("looks_nextcostume", ()),
                "SetSize": ("looks_setsizeto", ("SIZE",)),
                "ChangeSize": ("looks_changesizeby", ("CHANGE",)),
                "ClearEffects": ("looks_cleargraphiceffects", ()),
                "SetX": ("motion_setx", ("X",)), "SetY": ("motion_sety", ("Y",)),
                "ChangeX": ("motion_changexby", ("DX",)), "ChangeY": ("motion_changeyby", ("DY",)),
                "GlideTo": ("motion_glidesecstoxy", ("SECS", "X", "Y")),
                "ResetTimer": ("sensing_resettimer", ()),
            }
            try:
                opcode, inputs = opcodes[statement.name]
            except KeyError as error:
                raise NotImplementedError(f"unsupported builtin: {statement.name}") from error
            if opcode.startswith("pen_"):
                self.uses_pen = True
            block_id = self.block(opcode, parent=parent)
            for input_name, value in zip(inputs, statement.params):
                self.reporter_input(block_id, input_name, self.expr(value))
            return block_id
        if isinstance(statement, Move):
            block_id = self.block("data_setvariableto", parent=parent)
            self.blocks[block_id]["fields"] = {"VARIABLE": [statement.result.name, self.variable_id(statement.result)]}
            self.reporter_input(block_id, "VALUE", self.expr(statement.value))
            return block_id
        if isinstance(statement, ListSet):
            block_id = self.block("data_replaceitemoflist", parent=parent)
            self.blocks[block_id]["fields"] = {"LIST": [statement.list_id.list_name, self.list_id(statement.list_id)]}
            self.reporter_input(block_id, "INDEX", self.one_based(statement.index))
            self.reporter_input(block_id, "ITEM", self.expr(statement.value))
            return block_id
        if isinstance(statement, ListInsert):
            block_id = self.block("data_insertatlist", parent=parent)
            self.blocks[block_id]["fields"] = {"LIST": [statement.list_id.list_name, self.list_id(statement.list_id)]}
            self.reporter_input(block_id, "INDEX", self.one_based(statement.index))
            self.reporter_input(block_id, "ITEM", self.expr(statement.value))
            return block_id
        if isinstance(statement, ListDelete):
            block_id = self.block("data_deleteoflist", parent=parent)
            self.blocks[block_id]["fields"] = {"LIST": [statement.list_id.list_name, self.list_id(statement.list_id)]}
            self.reporter_input(block_id, "INDEX", self.one_based(statement.index))
            return block_id
        if isinstance(statement, ListPop):
            block_id = self.block("data_deleteoflist", parent=parent)
            self.blocks[block_id]["fields"] = {"LIST": [statement.list_id.list_name, self.list_id(statement.list_id)]}
            self.reporter_input(block_id, "INDEX", self.list_length(statement.list_id))
            return block_id
        if isinstance(statement, ListPush):
            block_id = self.block("data_addtolist", parent=parent)
            self.blocks[block_id]["fields"] = {"LIST": [statement.list_id.list_name, self.list_id(statement.list_id)]}
            self.reporter_input(block_id, "ITEM", self.expr(statement.value))
            return block_id
        if isinstance(statement, ListReset):
            block_id = self.block("data_deletealloflist", parent=parent)
            self.blocks[block_id]["fields"] = {"LIST": [statement.list_id.list_name, self.list_id(statement.list_id)]}
            return block_id
        if isinstance(statement, Branch):
            opcode = "control_if_else" if statement.false_label else "control_if"
            block_id = self.block(opcode, parent=parent)
            self.reporter_input(block_id, "CONDITION", self.expr(statement.cond))
            self.attach_substack(block_id, "SUBSTACK", statement.true_label)
            if statement.false_label:
                self.attach_substack(block_id, "SUBSTACK2", statement.false_label)
            return block_id
        if isinstance(statement, While):
            block_id = self.block("control_repeat_until", parent=parent)
            not_active = self.block("operator_not")
            condition = (
                self.active_condition_reporter(statement.cond)
                if self.current_function in self.functions_requiring_return_flag
                else self.expr(statement.cond)
            )
            self.reporter_input(not_active, "OPERAND", condition)
            self.reporter_input(block_id, "CONDITION", not_active)
            self.attach_substack(block_id, "SUBSTACK", statement.body)
            return block_id
        if isinstance(statement, Call):
            if self.function_owner[statement.callee] != self.current_sprite_index:
                return self.cross_sprite_call(statement, parent)
            call = self.inline_call(statement, parent) if self.can_inline(statement.callee) else self.procedure_call(statement, parent)
            if self.flattened:
                assert self.current_function is not None
                caller_return = self.function_return_values[self.current_function]
                callee_return = self.function_return_values[statement.callee]
                if caller_return is not callee_return:
                    copy = self.set_internal_variable(
                        caller_return.name,
                        self.variable_id(caller_return),
                        self.variable_reporter(callee_return),
                        parent,
                    )
                    self.blocks[self.tail(call)]["next"] = copy
            return call
        if isinstance(statement, Return):
            # The return value has already been stored in __ReturnValue__ by
            # IRGen.  Stop following statements through the per-call flag.
            if self.current_function not in self.functions_requiring_return_flag:
                return None
            assert self.return_flag_id is not None
            return self.set_internal_variable(
                "__nc_backend_return_flag__", self.return_flag_id,
                self.primitive(Number(1)), parent,
            )
        raise NotImplementedError(f"unsupported statement: {type(statement).__name__}")

    def active_condition_reporter(self, condition: BoolExpr) -> str:
        assert self.return_flag_id is not None
        block_id = self.block("operator_and")
        equals = self.block("operator_equals", parent=block_id)
        self.reporter_input(equals, "OPERAND1", self.internal_variable_reporter("__nc_backend_return_flag__", self.return_flag_id))
        self.reporter_input(equals, "OPERAND2", self.primitive(Number(0)))
        self.reporter_input(block_id, "OPERAND1", equals)
        self.reporter_input(block_id, "OPERAND2", self.expr(condition))
        return block_id

    def guard_active(self, first: str, parent: str | None) -> str:
        assert self.return_flag_id is not None
        guard = self.block("control_if", parent=parent)
        equals = self.block("operator_equals", parent=guard)
        self.reporter_input(equals, "OPERAND1", self.internal_variable_reporter("__nc_backend_return_flag__", self.return_flag_id))
        self.reporter_input(equals, "OPERAND2", self.primitive(Number(0)))
        self.reporter_input(guard, "CONDITION", equals)
        self.blocks[guard]["inputs"]["SUBSTACK"] = [2, first]
        current: str | None = first
        while current is not None:
            self.blocks[current]["parent"] = guard
            current = self.blocks[current]["next"]
        return guard

    def statement_may_return(self, statement: Stmt) -> bool:
        """Whether executing this statement can set the current return flag."""
        if isinstance(statement, Return):
            return True
        if isinstance(statement, Branch):
            return (
                self.block_may_return(statement.true_label)
                or (statement.false_label is not None and self.block_may_return(statement.false_label))
            )
        if isinstance(statement, While):
            return self.block_may_return(statement.body)
        # Calls restore the caller's flag before control returns, so they do
        # not require a guard around the following statement.
        return False

    def block_may_return(self, block: Block) -> bool:
        return any(self.statement_may_return(statement) for statement in block.instr)

    def emit_statements(self, statements: list[Stmt], parent: str | None) -> str | None:
        first: str | None = None
        previous: str | None = None
        segment_first: str | None = None
        segment_previous: str | None = None
        guard_segment = False

        def flush_segment() -> None:
            nonlocal first, previous, segment_first, segment_previous
            if segment_first is None or segment_previous is None:
                return
            block_id = (
                self.guard_active(segment_first, parent)
                if guard_segment and self.current_function in self.functions_requiring_return_flag
                else segment_first
            )
            if first is None:
                first = block_id
            if previous is not None:
                self.blocks[previous]["next"] = block_id
                self.blocks[block_id]["parent"] = parent
            previous = self.tail(block_id)
            segment_first = None
            segment_previous = None

        for statement in statements:
            block_id = self.emit_statement(statement, parent)
            if block_id is None:
                continue
            if segment_first is None:
                segment_first = block_id
            elif segment_previous is not None:
                self.blocks[segment_previous]["next"] = block_id
                self.blocks[block_id]["parent"] = parent
            segment_previous = self.tail(block_id)

            # Statements through the first possible return may run without a
            # guard.  Everything after it is grouped into one guarded segment
            # until the next possible return, preserving early-return behavior
            # without wrapping every individual Scratch block.
            if self.statement_may_return(statement):
                flush_segment()
                guard_segment = True
        flush_segment()
        return first

    def register_procedures(self, sprite: Sprite) -> None:
        for function in sprite.func:
            if function not in self.live_functions:
                continue
            names = [parameter.name for parameter in function.params]
            argument_ids = [self.new_id("arg") for _ in function.params]
            suffix = "" if not names else " " + " ".join("%s" for _ in names)
            name = function.name
            if self.flattened:
                name = f"{self.function_origin[function]}__{name}"
            self.procedures[function] = (name + suffix, argument_ids, names)

    def emit_function(self, function: Function, top_level: bool = True) -> None:
        proccode, argument_ids, names = self.procedures[function]
        definition = self.block("procedures_definition", top=top_level)
        prototype = self.block("procedures_prototype", parent=definition)
        self.blocks[prototype]["shadow"] = True
        self.blocks[prototype]["mutation"] = {
            "tagName": "mutation", "children": [], "proccode": proccode,
            "argumentids": json.dumps(argument_ids), "argumentnames": json.dumps(names),
            "argumentdefaults": json.dumps(["" for _ in names]), "warp": "false",
        }
        self.blocks[definition]["inputs"] = {"custom_block": [1, prototype]}
        old_function = self.current_function
        old_arguments = self.argument_variables
        self.current_function = function
        self.argument_variables = {id(parameter) for parameter in function.params}
        first = self.emit_statements(function.instr.instr, definition)
        self.blocks[definition]["next"] = first
        self.current_function = old_function
        self.argument_variables = old_arguments

    def target(self, sprite: Sprite, layer_order: int) -> dict[str, Any]:
        self.blocks = {}
        self.current_sprite = sprite
        self.current_sprite_index = layer_order - 1
        self.variable_ids = {id(variable): self.new_id("v") for variable in sprite.variables}
        self.list_ids = {id(list_info): self.new_id("l") for list_info in sprite.lists}
        sprite_requires_return_flag = self.current_sprite_index in self.sprites_requiring_return_flag
        self.return_flag_id = self.new_id("v") if sprite_requires_return_flag else None
        self.return_flag_stack_id = self.new_id("l") if sprite_requires_return_flag else None
        self.current_return_value = next(
            (variable for variable in sprite.variables if variable.name.endswith("__ReturnValue__")),
            None,
        )
        self.current_object = next(
            (variable for variable in sprite.variables if variable.name.endswith("__CurrentObject__")),
            None,
        )
        self.current_return_stack = next(
            (list_info for list_info in sprite.lists if list_info.list_name.endswith("__ReturnStack__")),
            None,
        )
        self.register_procedures(sprite)
        for function in sprite.func:
            if function not in self.live_functions:
                continue
            self.emit_function(function)
        if not self.flattened:
            for function in sprite.func:
                if function in self.cross_sprite_functions:
                    self.emit_cross_sprite_handler(function)

        if self.module.entry_point in sprite.func:
            hat = self.block("event_whenflagclicked", top=True)
            entry_call = self.procedure_call_inputs(
                self.module.entry_point, [], hat, manage_return_flag=False
            )
            if self.module.entry_point in self.functions_requiring_return_flag:
                assert self.return_flag_id is not None
                clear = self.set_internal_variable(
                    "__nc_backend_return_flag__", self.return_flag_id,
                    self.primitive(Number(0)), hat,
                )
                self.blocks[hat]["next"] = clear
                self.blocks[clear]["next"] = entry_call
            else:
                self.blocks[hat]["next"] = entry_call

        used_variable_ids = {
            field[1]
            for block in self.blocks.values()
            for field_name, field in block["fields"].items()
            if field_name == "VARIABLE" and len(field) > 1
        }
        used_list_ids = {
            field[1]
            for block in self.blocks.values()
            for field_name, field in block["fields"].items()
            if field_name == "LIST" and len(field) > 1
        }
        return {
            "isStage": False, "name": sprite.name,
            "variables": {
                **{
                    self.variable_id(variable): [variable.name, 0]
                    for variable in sprite.variables
                    if self.variable_id(variable) in used_variable_ids
                },
                **({self.return_flag_id: ["__nc_backend_return_flag__", 0]}
                   if self.return_flag_id in used_variable_ids else {}),
            },
            "lists": {
                **{
                    self.list_id(list_info): [list_info.list_name, []]
                    for list_info in sprite.lists
                    if self.list_id(list_info) in used_list_ids
                },
                **({self.return_flag_stack_id: ["__nc_backend_return_flag_stack__", []]}
                   if self.return_flag_stack_id in used_list_ids else {}),
            },
            "broadcasts": {}, "blocks": self.blocks, "comments": {}, "currentCostume": 0,
            "costumes": [self.default_costume("costume1")], "sounds": [], "volume": 100, "layerOrder": layer_order,
            "tempo": 60, "videoTransparency": 50, "videoState": "on", "textToSpeechLanguage": None,
        }

    def project(self) -> dict[str, Any]:
        stage = {
            "isStage": True, "name": "Stage",
            "variables": {identifier: [name, 0] for name, identifier in self.global_variables.items()},
            "lists": {identifier: [name, []] for name, identifier in self.global_lists.items()},
            "broadcasts": self.broadcasts,
            "blocks": {}, "comments": {}, "currentCostume": 0,
            "costumes": [self.default_costume("backdrop1")], "sounds": [],
            "volume": 100, "layerOrder": 0, "tempo": 60, "videoTransparency": 50,
            "videoState": "on", "textToSpeechLanguage": None,
        }
        return {
            "targets": [stage, *[
                self.target(sprite, layer_order)
                for layer_order, sprite in enumerate(self.sprites, start=1)
            ]],
            "monitors": [], "extensions": ["pen"] if self.uses_pen else [], "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "nano_cust"},
        }


def compile_to_sb3(module: Module, output_path: str | Path) -> Path:
    """Write ``module`` as a Scratch 3 ``.sb3`` archive and return its path."""
    destination = Path(output_path)
    if destination.suffix != ".sb3":
        destination = destination.with_suffix(".sb3")
    destination.parent.mkdir(parents=True, exist_ok=True)
    emitter = SB3Emitter(module)
    project = emitter.project()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(project, ensure_ascii=False, separators=(",", ":")))
        for filename, data in emitter.assets.items():
            archive.writestr(filename, data)
    return destination
