from dataclasses import dataclass
from src.backend.ir.instr import *

from src.backend.ir.flow import *

@dataclass
class Function():
    name: str
    params: list[Variable]
    instr: list[Stmt]


@dataclass
class ListInfo():
    list_name : str

@dataclass
class Module():
    func: list[Function]
    lists: list[ListInfo]
    variables: list[Variable]
    entry: Function | None = None
