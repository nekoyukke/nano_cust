import unittest

from src.backend.ir.flow import Branch, Call, Return, While
from src.backend.ir.list import ListGet
from src.backend.ir.stmt import ListDelete, ListPush, ListSet, Move
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


class IRGeneratorFeatureTests(unittest.TestCase):
    def test_unary_number_expression_compiles(self):
        module = build("""
            sprite Main {
                fn main() -> int { return -1; }
            }
        """)

        self.assertIsInstance(module.sprites[0].func[0].instr.instr[-1], Return)

    def test_if_and_while_generate_flow_ir(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    let x: int = 1;
                    if x < 2 { x = 3; } else { x = 4; }
                    while x < 5 { x = x + 1; }
                    return x;
                }
            }
        """)

        instructions = module.sprites[0].func[0].instr.instr
        self.assertTrue(any(isinstance(item, Branch) for item in instructions))
        self.assertTrue(any(isinstance(item, While) for item in instructions))

    def test_direct_function_call_generates_call_expression(self):
        module = build("""
            sprite Main {
                fn increment(x: int) -> int { return x + 1; }
                fn main() -> int { return increment(2); }
            }
        """)

        instructions = module.sprites[0].func[-1].instr.instr
        returned = instructions[-1]
        self.assertIsInstance(returned, Return)
        self.assertTrue(any(isinstance(item, Call) for item in instructions))
        self.assertGreaterEqual(sum(isinstance(item, ListPush) for item in instructions), 2)
        self.assertGreaterEqual(sum(isinstance(item, ListDelete) for item in instructions), 2)

    def test_later_sprite_function_can_be_called(self):
        module = build("""
            sprite Main {
                fn main() -> int { return Hero.jump(2); }
            }
            sprite Hero {
                fn jump(height: int) -> int { return height; }
            }
        """)

        main_instructions = module.sprites[0].func[0].instr.instr
        call = next(item for item in main_instructions if isinstance(item, Call))
        self.assertEqual(call.callee.name, "jump")
        self.assertEqual(call.callee.params[0].sprite, 1)

    def test_new_and_scalar_field_access_use_runtime_lists(self):
        module = build("""
            class Box { let value: int; }
            sprite Main {
                fn main() -> int {
                    let box: Box = new Box;
                    box.value = 4;
                    return box.value;
                }
            }
        """)

        instructions = module.sprites[0].func[-1].instr.instr
        self.assertTrue(any(isinstance(item, ListPush) for item in instructions))
        self.assertTrue(any(isinstance(item, ListSet) for item in instructions))
        returned = instructions[-1]
        self.assertIsInstance(returned, Return)
        self.assertIsInstance(instructions[-2], Move)
        self.assertIsInstance(instructions[-2].value, ListGet)

    def test_method_call_sets_current_object_and_uses_member_storage(self):
        module = build("""
            class Box {
                let value: int;
                fn set(next: int) -> int { value = next; return value; }
                fn get() -> int { return value; }
            }
            sprite Main {
                fn main() -> int {
                    let box: Box = new Box;
                    box.set(7);
                    return box.get();
                }
            }
        """)

        sprite = module.sprites[0]
        main_instructions = sprite.func[-1].instr.instr
        self.assertTrue(any(
            isinstance(item, Move) and item.result.name.endswith("__CurrentObject__")
            for item in main_instructions
        ))
        self.assertTrue(any(isinstance(item, Call) for item in main_instructions))
        self.assertTrue(any(isinstance(item, ListSet) for item in sprite.func[0].instr.instr))

    def test_recursive_method_saves_and_restores_its_call_frame(self):
        module = build("""
            class Counter {
                let value: int;
                fn descend(n: int) -> int {
                    if n == 0 { return value; }
                    else { return descend(n - 1); }
                }
            }
            sprite Main {
                fn main() -> int {
                    let counter: Counter = new Counter;
                    return counter.descend(2);
                }
            }
        """)

        recursive_branch = module.sprites[0].func[0].instr.instr[0]
        self.assertIsInstance(recursive_branch, Branch)
        recursive_instructions = recursive_branch.false_label.instr
        self.assertTrue(any(isinstance(item, Call) for item in recursive_instructions))
        self.assertGreaterEqual(sum(isinstance(item, ListPush) for item in recursive_instructions), 2)
        self.assertGreaterEqual(sum(isinstance(item, ListDelete) for item in recursive_instructions), 2)

    def test_indirect_recursion_keeps_frames_only_inside_its_scc(self):
        module = build("""
            sprite Main {
                fn a(n: int) -> int {
                    if n == 0 { return 0; }
                    return b(n - 1);
                }
                fn b(n: int) -> int { return c(n); }
                fn c(n: int) -> int { return a(n); }
                fn main() -> int { return a(1); }
            }
        """)

        def has_frame_push(instructions):
            for instruction in instructions:
                if isinstance(instruction, ListPush) and instruction.list_id.list_name.endswith("__Frame__"):
                    return True
                if isinstance(instruction, Branch):
                    if has_frame_push(instruction.true_label.instr):
                        return True
                    if instruction.false_label and has_frame_push(instruction.false_label.instr):
                        return True
                if isinstance(instruction, While) and has_frame_push(instruction.body.instr):
                    return True
            return False

        functions = {function.name: function for function in module.sprites[0].func}
        self.assertTrue(has_frame_push(functions["a"].instr.instr))
        self.assertTrue(has_frame_push(functions["b"].instr.instr))
        self.assertTrue(has_frame_push(functions["c"].instr.instr))
        self.assertFalse(has_frame_push(functions["main"].instr.instr))

    def test_save_removes_and_unsave_restores_an_object_registration(self):
        module = build("""
            class Box { let value: int; }
            sprite Main {
                fn main() -> int {
                    let box: Box = new Box;
                    save box;
                    unsave box;
                    return 0;
                }
            }
        """)
        instructions = module.sprites[0].func[-1].instr.instr
        self.assertTrue(any(isinstance(item, While) for item in instructions))
        self.assertTrue(any(isinstance(item, ListPush) for item in instructions))

    def test_discarded_call_does_not_allocate_a_return_temporary(self):
        module = build("""
            sprite Main {
                fn side_effect() -> int { return 0; }
                fn main() -> int {
                    side_effect();
                    return 0;
                }
            }
        """)
        self.assertFalse(any(
            variable.name.startswith("__nc_runtime__.temp")
            for variable in module.sprites[0].variables
        ))

    def test_temporaries_are_reused_between_source_statements(self):
        module = build("""
            sprite Main {
                fn inc(value: int) -> int { return value + 1; }
                fn main() -> int {
                    let first: int = inc(1);
                    let second: int = inc(2);
                    return first + second;
                }
            }
        """)

        temporaries = [
            variable for variable in module.sprites[0].variables
            if variable.name.startswith("__nc_runtime__.temp")
        ]
        self.assertEqual(len(temporaries), 1)


if __name__ == "__main__":
    unittest.main()
