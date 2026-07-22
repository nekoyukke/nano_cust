import uuid
import json
import src.ast.base as _base
import src.ast.expr as _expr
import src.ast.stmt as _stmt

from dataclasses import dataclass, field

from typing import Any

@dataclass
class Block:
    id: str
    opcode: str

    next: str | None = None
    parent: str | None = None

    inputs: dict[Any,Any] = field(default_factory=dict[Any,Any])
    fields: dict[Any,Any] = field(default_factory=dict[Any,Any])

    shadow: bool = False
    topLevel: bool = False

    x: int = 0
    y: int = 0


@dataclass
class Statement:
    first: Block
    last: Block

class ScratchCodegen:
    def __init__(self, program: _stmt.ProgramStmt) -> None:
        self.program = program
        self.counter = 0
        self.blocks: dict[str, Block]

    def codegen(self):
        return 
    
    def new_block(self, opcode:str):
        self.counter += 1

        block = Block(
            id=f"B{self.counter}",
            opcode=opcode
        )

        self.blocks[block.id] = block

        return block

    def connect(self, left: Statement, right: Statement):
        left.last.next = right.first.id
        right.first.parent = left.last.id

        return Statement(
            left.first,
            right.last
        )
    
    def emit_program(self, program:_stmt.ProgramStmt):
        stmt = None

        for node in program.instr:

            current = self.emit_statement(node)

            if stmt is None:
                stmt = current
            else:
                stmt = self.connect(stmt, current)

        stmt.first.topLevel = True
        stmt.first.x = 0
        stmt.first.y = 0