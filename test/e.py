from src.frontend.parser.parser import Parser
from src.frontend.lexer.lexer import Lexer
from src.utils.error.error_lists import ErrorLists

from src.frontend.semantic.collector import Collector
from src.frontend.semantic.resolver import Resolver
from src.frontend.ast.stmt import ProgramStmt
from src.frontend.ast.scope import Scope

from src.frontend.ast.context import Context

def parse(string: str):
    pas = Parser(Lexer(string).tokenize(), string)
    result = pas.parse()
    print(ErrorLists(pas.error))
    return result

def collect(program:ProgramStmt, source:str, ctx:Context = Context({},{}, {}, {}, {}, {}, {}, {}, {}, {})):
    co = Collector(program, source, ctx)
    result = co.collect()
    print(ErrorLists(co.error))
    return (result, ctx)

def resolver(program:ProgramStmt, source:str, ctx:Context, scope:Scope):
    re = Resolver(program, source, ctx, scope)
    result = re.resolve()
    print(ErrorLists(re.error))
    return (result, ctx)

string=\
"""
let x:int = 1;
class Vector3 {
    let x:int;
    let y:int;
    let z:int;
    
    fn add(dx:int, dy:int, dz:int) -> int {
        return 0;
    }
    fn init() -> int {
        return 0;
    }
}
sprite Main {
    fn main() -> int { return Hero.jump(10); }
}
sprite Hero {
    fn jump(height: int) -> int { return height; }
}
"""

(ast:=parse(string))
print("collected")
print(*(cc:=collect(ast,string)), sep="\n"*3)
print("\n"*3)
print("resolved")
print(*(re := resolver(ast,string,cc[1],cc[0])), sep="\n"*3)