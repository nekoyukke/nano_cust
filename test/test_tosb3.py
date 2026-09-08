import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.backend.irgen import IRGenerator
from src.backend.tosb3 import compile_to_sb3
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


class SB3Tests(unittest.TestCase):
    def test_writes_scratch_project_with_runtime_and_flow_blocks(self):
        module = build("""
            sprite Main {
                fn inc(value: int) -> int { return value + 1; }
                fn main() -> int {
                    let xs: list int;
                    xs[0] = inc(2);
                    if 1 < 2 { xs[1] = 4; }
                    while 1 < 0 { xs[2] = 5; }
                    return xs[0];
                }
            }
        """)

        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                self.assertIn("project.json", archive.namelist())
                self.assertTrue(any(name.endswith(".svg") for name in archive.namelist()))
                project = json.loads(archive.read("project.json"))

        main = project["targets"][1]
        opcodes = {block["opcode"] for block in main["blocks"].values()}
        self.assertEqual(main["name"], "Main")
        self.assertIn("event_whenflagclicked", opcodes)
        self.assertIn("procedures_definition", opcodes)
        self.assertIn("procedures_call", opcodes)
        self.assertIn("control_if", opcodes)
        self.assertIn("control_repeat_until", opcodes)
        self.assertIn("data_replaceitemoflist", opcodes)

    def test_cross_sprite_call_uses_a_synchronous_broadcast(self):
        module = build("""
            sprite Main {
                fn main() -> int { return Hero.jump(2); }
            }
            sprite Hero {
                fn jump(height: int) -> int { return height; }
            }
        """)

        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        self.assertEqual([target["name"] for target in project["targets"][1:]], ["Main", "Hero"])
        main_blocks = project["targets"][1]["blocks"].values()
        hero_blocks = project["targets"][2]["blocks"].values()
        self.assertTrue(any(block["opcode"] == "event_broadcastandwait" for block in main_blocks))
        self.assertTrue(any(block["opcode"] == "event_whenbroadcastreceived" for block in hero_blocks))

    def test_return_uses_a_recursion_safe_execution_flag(self):
        module = build("""
            sprite Main {
                fn fact(n: int) -> int {
                    if n == 0 { return 1; }
                    return n * fact(n - 1);
                }
                fn main() -> int { return fact(4); }
            }
        """)

        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        main = project["targets"][1]
        self.assertIn("__nc_backend_return_flag__", {
            value[0] for value in main["variables"].values()
        })
        self.assertIn("__nc_backend_return_flag_stack__", {
            value[0] for value in main["lists"].values()
        })

    def test_terminal_returns_do_not_create_a_return_flag_runtime(self):
        module = build("""
            sprite Main {
                fn twice(value: int) -> int { return value * 2; }
                fn main() -> int { return twice(3); }
            }
        """)

        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        main = project["targets"][1]
        self.assertNotIn("__nc_backend_return_flag__", {
            value[0] for value in main["variables"].values()
        })
        self.assertNotIn("__nc_backend_return_flag_stack__", {
            value[0] for value in main["lists"].values()
        })

    def test_local_only_program_has_no_cross_sprite_runtime(self):
        module = build("""
            sprite Main {
                fn helper() -> int { return 1; }
                fn main() -> int { return helper(); }
            }
        """)

        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        stage = project["targets"][0]
        main = project["targets"][1]
        self.assertFalse(stage["variables"])
        self.assertFalse(stage["lists"])
        self.assertFalse(stage["broadcasts"])
        self.assertFalse(any(
            block["opcode"] == "event_whenbroadcastreceived"
            for block in main["blocks"].values()
        ))

    def test_motion_and_pen_builtins_lower_to_native_scratch_blocks(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    Move(10, 20);
                    PenDown();
                    PenColor("#ff0000");
                    PenSize(3);
                    PenUp();
                    ClearPen();
                    return 0;
                }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))
        opcodes = {block["opcode"] for block in project["targets"][1]["blocks"].values()}
        self.assertTrue({
            "motion_gotoxy", "pen_penDown", "pen_setPenColorToColor",
            "pen_setPenSizeTo", "pen_penUp", "pen_clear",
        }.issubset(opcodes))
        self.assertIn("pen", project["extensions"])

    def test_keyboard_and_mouse_reporters_lower_to_sensing_blocks(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    let x: int = MouseX();
                    let y: int = MouseY();
                    if KeyPressed("space") && MousePressed() {
                        Move(x, y);
                    }
                    return 0;
                }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        opcodes = {
            block["opcode"] for block in project["targets"][1]["blocks"].values()
        }
        self.assertTrue({
            "sensing_keypressed", "sensing_mousedown", "sensing_mousex", "sensing_mousey",
        }.issubset(opcodes))

    def test_trigonometric_reporters_lower_to_scratch_math_operations(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    let value: int = Sin(30) + Cos(60) + Tan(45);
                    return value;
                }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        math_operations = [
            block for block in project["targets"][1]["blocks"].values()
            if block["opcode"] == "operator_mathop"
        ]
        self.assertEqual({block["fields"]["OPERATOR"][0] for block in math_operations}, {
            "sin", "cos", "tan",
        })

    def test_remaining_scratch_operator_reporters_lower_to_native_blocks(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    let random: int = Random(1, 10);
                    let text: string = Join("ab", LetterOf(1, "cd"));
                    let size: int = TextLength(text);
                    let rounded: int = Round(1.2);
                    let math: int = Abs(-2) + Floor(1.9) + Ceil(1.1) + Sqrt(4)
                        + Asin(0) + Acos(1) + Atan(1) + Ln(1) + Log(10) + Exp(1) + Exp10(2);
                    if Contains(text, "b") { return random + size + rounded + math; }
                    return 0;
                }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        blocks = project["targets"][1]["blocks"].values()
        opcodes = {block["opcode"] for block in blocks}
        self.assertTrue({
            "operator_random", "operator_join", "operator_letter_of", "operator_length",
            "operator_contains", "operator_round", "operator_mathop",
        }.issubset(opcodes))
        math_operations = {
            block["fields"]["OPERATOR"][0]
            for block in blocks if block["opcode"] == "operator_mathop"
        }
        self.assertTrue({
            "abs", "floor", "ceiling", "sqrt", "asin", "acos", "atan", "ln", "log", "e ^", "10 ^",
        }.issubset(math_operations))

    def test_string_literals_are_unquoted_and_escaped_in_sb3(self):
        module = build(r'''
            sprite Main {
                fn main() -> int {
                    let text: string = "日本語\n\"quoted\"\\slash";
                    return TextLength(text);
                }
            }
        ''')
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        string_values = [
            block["inputs"]["VALUE"]
            for block in project["targets"][1]["blocks"].values()
            if block["opcode"] == "data_setvariableto"
            and block["inputs"].get("VALUE", [None])[0] == 1
            and block["inputs"]["VALUE"][1][0] == 10
        ]
        self.assertIn([1, [10, '日本語\n"quoted"\\slash']], string_values)

    def test_inline_annotation_expands_a_straight_line_function_call(self):
        module = build("""
            sprite Main {
                @inline
                fn twice(value: int) -> int { return value * 2; }
                fn main() -> int { return twice(3); }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        blocks = project["targets"][1]["blocks"].values()
        # Only the green-flag entry invokes a custom block; `twice` itself is
        # expanded in `main`.
        self.assertEqual(sum(block["opcode"] == "procedures_call" for block in blocks), 1)

    def test_wait_looks_motion_and_timer_builtins_lower_to_native_blocks(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    ResetTimer(); Wait(0.1); Say("hi"); ThinkFor("...", 1);
                    Show(); SetSize(80); ChangeX(5); SetY(10); GlideTo(1, 0, 0);
                    return Timer();
                }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        opcodes = {block["opcode"] for block in project["targets"][1]["blocks"].values()}
        self.assertTrue({
            "control_wait", "looks_say", "looks_thinkforsecs", "looks_show", "looks_setsizeto",
            "motion_changexby", "motion_sety", "motion_glidesecstoxy", "sensing_resettimer", "sensing_timer",
        }.issubset(opcodes))

    def test_constant_folding_removes_literal_arithmetic_blocks(self):
        module = build("""
            sprite Main { fn main() -> int { return -1 + 1; } }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        opcodes = {block["opcode"] for block in project["targets"][1]["blocks"].values()}
        self.assertNotIn("operator_add", opcodes)
        self.assertNotIn("operator_subtract", opcodes)

    def test_unused_functions_and_literal_variables_are_not_emitted(self):
        module = build("""
            sprite Main {
                fn unused() -> int { let hidden: int = 7; return hidden; }
                fn main() -> int { let discarded: int = 123; return 0; }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        main = project["targets"][1]
        procedure_names = {
            block.get("mutation", {}).get("proccode", "")
            for block in main["blocks"].values()
            if block["opcode"] == "procedures_prototype"
        }
        variable_names = {value[0] for value in main["variables"].values()}
        self.assertNotIn("unused", procedure_names)
        self.assertFalse(any("discarded" in name for name in variable_names))

    def test_non_returning_statement_sequence_is_not_individually_guarded(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    let value: int = 1;
                    value = value + 1;
                    return value;
                }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        opcodes = {
            block["opcode"] for block in project["targets"][1]["blocks"].values()
        }
        self.assertNotIn("control_if", opcodes)

    def test_statements_after_a_possible_return_share_one_guard(self):
        module = build("""
            sprite Main {
                fn main() -> int {
                    if 1 == 1 { return 1; }
                    Move(10, 20);
                    Move(30, 40);
                    return 0;
                }
            }
        """)
        with tempfile.TemporaryDirectory() as directory:
            path = compile_to_sb3(module, Path(directory) / "program.sb3")
            with zipfile.ZipFile(path) as archive:
                project = json.loads(archive.read("project.json"))

        blocks = project["targets"][1]["blocks"].values()
        # One `if` is written in the source, and one additional `if` guards
        # the complete suffix after its early return.
        self.assertEqual(sum(block["opcode"] == "control_if" for block in blocks), 2)


if __name__ == "__main__":
    unittest.main()
