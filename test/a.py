import unittest

from utils.error.error_lists import ErrorLists
from src.parser.parser import Parser
from src.lexer.lexer import Lexer

from src.semantic.collector import Collector
from src.ast.stmt import ProgramStmt

from src.ast.context import Context

def parse(string: str):
    return Parser(Lexer(string).tokenize(), string).parse()

def collect(program:ProgramStmt, source:str, ctx:Context = Context({},{}, {})):
    sc = Collector(program, source, ctx).collect()
    return (sc, ctx)

string=\
"""
let x:int = 1;
class Vector3 {
    let x:int;
    let y:int;
    let z:int;
}
fn add(x:int, y:int) -> int {
    return x+y;
}
"""

(ast:=parse(string))
print(collect(ast,string))