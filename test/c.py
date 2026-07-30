from frontend.parser.parser import Parser
from frontend.lexer.lexer import Lexer
from utils.error.error_lists import ErrorLists

from frontend.semantic.collector import Collector
from frontend.semantic.resolver import Resolver
from frontend.ast.stmt import ProgramStmt
from frontend.ast.scope import Scope

from frontend.ast.context import Context

def parse(string: str):
    pas = Parser(Lexer(string).tokenize(), string)
    result = pas.parse()
    print(ErrorLists(pas.error))
    return result

def collect(program:ProgramStmt, source:str, ctx:Context = Context({},{}, {}, {}, {}, {})):
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
        x = x + dx;
        y = y + dy;
        z = z + dz;
        return 0;
    }
    fn init() -> int {
        x=0;y=0;z=0;
        return 0;
    }
}
fn add(x:int, y:int) -> int {
    let result:int = x+y;
    return result;
}
fn main() -> int {
    let x: Vector3;
    x.init();
    x.add(3,4,1);
    return 0;
}
"""

(ast:=parse(string))
print(*(cc:=collect(ast,string)), sep="\n"*3)
print("\n"*3)
print(*resolver(ast,string,cc[1],cc[0]), sep="\n"*3)