from src.frontend.parser.parser import Parser
from src.frontend.lexer.lexer import Lexer
from src.utils.error.error_lists import ErrorLists

from src.frontend.semantic.collector import Collector
from src.frontend.semantic.resolver import Resolver
from src.frontend.ast.stmt import ProgramStmt
from src.frontend.ast.scope import Scope

from src.frontend.ast.context import Context
import json
import tempfile
import zipfile
from pathlib import Path
from src.backend.irgen import IRGenerator
from src.backend.tosb3 import compile_to_sb3
from src.frontend.ast.context import Context
from src.frontend.lexer.lexer import Lexer
from src.frontend.parser.parser import Parser
from src.frontend.semantic.collector import Collector
from src.frontend.semantic.resolver import Resolver

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
class Vector2 {
    let x: int;
    let y: int;
}

class Vector3 {
    let x: int;
    let y: int;
    let z: int;

    fn add(dx: int, dy: int, dz: int) -> int {
        x = x + dx;
        y = y + dy;
        z = z + dz;
        return 0;
    }

    fn init() -> int {
        x = 0;
        y = 0;
        z = 0;
        return 0;
    }

    fn camera() -> Vector2 {
        let position: Vector2 = new Vector2();
        position.x = 0;
        position.y = 0;
        return position;
    }
}

sprite Main {
    fn main() -> int {
        let v: Vector3 = new Vector3();

        v.init();
        v.add(10, 20, 30);

        Move(0, 0);
        PenDown();
        Move(90, 90);
        PenUp();

        return 0;
    }
}
"""
def build(source: str):
    context = Context({}, {}, {}, {}, {}, {}, {}, {}, {}, {})
    program = Parser(Lexer(source).tokenize(), source).parse()
    scope = Collector(program, source, context).collect()
    resolver = Resolver(program, source, context, scope)
    resolver.resolve()
    if resolver.error:
        raise AssertionError(resolver.error)
    return IRGenerator(program, source, context).visit()

from src.backend.irgen import IRGenerator

module = build(string)
output = compile_to_sb3(module, "build/program.sb3")