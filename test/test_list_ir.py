import unittest

from src.backend.ir.list import ListGet
from src.backend.ir.flow import While
from src.backend.ir.stmt import ListReset, ListSet, Move
from src.backend.irgen import IRGenerator
from src.frontend.ast.context import Context
from src.frontend.lexer.lexer import Lexer
from src.frontend.parser.parser import Parser
from src.frontend.semantic.collector import Collector
from src.frontend.semantic.resolver import Resolver


def build(source: str):
    context = Context({}, {}, {}, {}, {}, {}, {}, {}, {}, {})
    program = Parser(Lexer(source).tokenize(), source).parse()
    scope = Collector(program, source, context).collect()
    resolver = Resolver(program, source, context, scope)
    resolver.resolve()
    if resolver.error:
        raise AssertionError(resolver.error)
    return IRGenerator(program, source, context).visit()


class ListIRTests(unittest.TestCase):
    def test_list_uses_direct_scratch_list_operations(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    let numbers: list int;
                    numbers[0] = 20;
                    return numbers[0];
                }
            }
        """)

        sprite = module.sprites[0]
        names = [item.list_name for item in sprite.lists]
        self.assertTrue(any("numbers" in name for name in names))

        instructions = sprite.func[0].instr.instr
        self.assertTrue(any(isinstance(item, ListReset) for item in instructions))
        self.assertTrue(any(isinstance(item, ListSet) for item in instructions))

        returned = instructions[-1]
        self.assertIsInstance(instructions[-2], Move)
        self.assertIsInstance(instructions[-2].value, ListGet)

    def test_for_in_captures_the_list_length_before_looping(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    let numbers: list int;
                    for value in numbers { }
                    return 0;
                }
            }
        """)
        self.assertTrue(any(
            isinstance(instruction, While)
            for instruction in module.sprites[0].func[0].instr.instr
        ))



if __name__ == "__main__":
    unittest.main()
