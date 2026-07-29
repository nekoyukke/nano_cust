from src.parser.parser import Parser
from src.lexer.lexer import Lexer

from src.semantic.collector import Collector
from src.semantic.resolver import Resolver
from src.ast.stmt import ProgramStmt
from src.ast.scope import Scope

from src.ast.context import Context

def parse(string: str):
    return Parser(Lexer(string).tokenize(), string).parse()

def collect(program:ProgramStmt, source:str, ctx:Context = Context({},{}, {})):
    sc = Collector(program, source, ctx).collect()
    return (sc, ctx)

def resolver(program:ProgramStmt, source:str, ctx:Context, scope:Scope):
    re = Resolver(program, source, ctx, scope).resolve()
    return (re, ctx)

string=\
"""
let x:int = 1;
class Vector3 {
    let x:int;
    let y:int;
    let z:int;
}
fn add(x:int, y:int) -> int {
    let result:int = x+y;
    return result;
}
"""

(ast:=parse(string))
print(*(cc:=collect(ast,string)), sep="\n"*3)
print("\n"*3)
print(*resolver(ast,string,cc[1],cc[0]), sep="\n"*3)