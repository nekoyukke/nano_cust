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
    let x:int;
    let y:int;
}

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
    fn camera(width:int, height:int, focalLength:int) -> Vector2 {
        let postion:Vector2 = new Vector2;
        postion.x = width / 2 + (x * focalLength) / z;
        postion.y = height / 2 + (y * focalLength) / z;
        return postion;
    }
}
sprite Main {
    fn main() -> int {
        let v1:Vector3 = new Vector3;
        let v2:Vector3 = new Vector3;
        v1.x = 3;v1.y=3;v1.z=3;
        v2.x = -3;v2.y=3;v2.z=3;
        let a1:list Vector3;
        let a2:list Vector3;
        a1.push(v1);
        a2.push(v2);
        draw(a1,a2);
        return 0;
    }
    fn draw(points1: list Vector3, points2:list Vector3) -> int {
        let pos:int = 0;
        while (pos<points1.length()) {
            let vec1:Vector2 = points1[pos].camera(480,360,30);
            let vec2:Vector2 = points2[pos].camera(480,360,30);
            Move(vec1.x, vec1.y);
            PenDown();
            Move(vec2.x, vec2.y);
            PenUp();
            pos = pos + 1;
        }
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
        print(ErrorLists(resolver.error))
        raise
    return IRGenerator(program, source, context).visit()

from src.backend.irgen import IRGenerator

module = build(string)
output = compile_to_sb3(module, "build/program.sb3")