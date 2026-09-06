import unittest

from src.backend.ir.boolexpr import And, Or
from src.backend.ir.flow import Branch
from src.backend.irgen import IRGenerator
from src.frontend.ast.context import Context
from src.frontend.lexer.lexer import Lexer
from src.frontend.lexer.tokentype import TokenType
from src.frontend.parser.parser import Parser
from src.frontend.semantic.collector import Collector
from src.frontend.semantic.resolver import Resolver


def build(source: str):
    context = Context({}, {}, {}, {}, {}, {}, {}, {}, {}, {})
    parser = Parser(Lexer(source).tokenize(), source)
    program = parser.parse()
    if parser.error:
        raise AssertionError(parser.error)
    scope = Collector(program, source, context).collect()
    resolver = Resolver(program, source, context, scope)
    resolver.resolve()
    if resolver.error:
        raise AssertionError(resolver.error)
    return IRGenerator(program, source, context).visit()


class LogicalOperatorTests(unittest.TestCase):
    def test_lexer_prefers_and_over_single_ampersands(self):
        tokens = Lexer("left && right").tokenize()
        self.assertEqual([token.type for token in tokens], [
            TokenType.ID, TokenType.LOGIC_AND, TokenType.ID, TokenType.EOF,
        ])

    def test_and_expression_compiles_to_boolean_ir(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    if 1 < 2 && 3 < 4 { return 0; }
                    return 1;
                }
            }
        """)
        branch = module.sprites[0].func[0].instr.instr[0]
        self.assertIsInstance(branch, Branch)
        self.assertIsInstance(branch.cond, And)

    def test_or_expression_compiles_to_boolean_ir(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    if 1 > 2 || 3 < 4 { return 0; }
                    return 1;
                }
            }
        """)
        branch = module.sprites[0].func[0].instr.instr[0]
        self.assertIsInstance(branch, Branch)
        self.assertIsInstance(branch.cond, Or)


if __name__ == "__main__":
    unittest.main()
