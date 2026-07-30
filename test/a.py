from frontend.parser.parser import Parser
from frontend.lexer.lexer import Lexer

from frontend.semantic.collector import Collector
from frontend.ast.stmt import ProgramStmt

from frontend.ast.context import Context

def parse(string: str):
    return Parser(Lexer(string).tokenize(), string).parse()

def collect(program:ProgramStmt, source:str, ctx:Context = Context({},{}, {}, {}, {}, {})):
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