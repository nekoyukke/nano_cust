import unittest

from src.frontend.ast.context import Context
from src.frontend.lexer.lexer import Lexer
from src.frontend.parser.parser import Parser
from src.frontend.semantic.collector import Collector
from src.frontend.semantic.resolver import Resolver
from src.utils.error.syntax import KinakoSyntaxError
from src.backend.ir.flow import Call, Return
from src.backend.irgen import IRGenerator


class SpriteFrontendTest(unittest.TestCase):
    def test_sprite_function_call_is_resolved(self):
        source = """
        Sprite Main {
            fn main() -> int { return Hero.jump(10); }
        }
        Sprite Hero {
            fn jump(height: int) -> int { return height; }
        }
        """
        program = Parser(Lexer(source).tokenize(), source).parse()
        context = Context({}, {}, {}, {}, {}, {})
        collector = Collector(program, source, context)
        scope = collector.collect()
        resolver = Resolver(program, source, context, scope)
        resolver.resolve()

        self.assertEqual([], collector.error)
        self.assertEqual([], resolver.error)
        self.assertEqual("main", context.entry.name)
        call = program.instr[0].functions[0].body.instr[0].expr
        self.assertEqual("jump", call.call.member.sym.name)

        module = IRGenerator(program, source, context).visit()
        self.assertEqual(["Main.main", "Hero.jump"], [function.name for function in module.func])
        self.assertIs(module.func[0], module.entry)
        main_return = module.entry.instr[0]
        self.assertIsInstance(main_return, Return)
        self.assertIsInstance(main_return.value, Call)
        self.assertEqual(1, main_return.value.func_id)

    def test_top_level_function_is_rejected(self):
        source = "fn main() -> int { return 0; }"
        with self.assertRaises(KinakoSyntaxError):
            Parser(Lexer(source).tokenize(), source).parse()


if __name__ == "__main__":
    unittest.main()
