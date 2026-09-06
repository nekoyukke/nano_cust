import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from main import main


class CommandLineTests(unittest.TestCase):
    def test_compiles_source_to_requested_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "program.nc"
            output = root / "game.sb3"
            source.write_text(
                "sprite Main { fn main() -> int { Move(10, 20); return 0; } }",
                encoding="utf-8",
            )
            self.assertEqual(main([str(source), "-o", str(output)]), 0)
            self.assertTrue(output.is_file())

    def test_check_does_not_write_an_output_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text("sprite Main { fn main() -> int { return 0; } }", encoding="utf-8")
            self.assertEqual(main([str(source), "--check"]), 0)
            self.assertFalse(source.with_suffix(".sb3").exists())

    def test_check_rejects_collector_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text(
                "sprite Main { fn main() -> int { return 0; } fn main() -> int { return 1; } }",
                encoding="utf-8",
            )
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main([str(source), "--check"]), 1)
            self.assertIn("すでに宣言されています", stderr.getvalue())

    def test_check_rejects_unknown_characters(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text("sprite Main { fn main() -> int { return 0; } }@", encoding="utf-8")
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main([str(source), "--check"]), 1)
            self.assertIn("予期しない文字", stderr.getvalue())

    def test_check_reports_import_as_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text(
                'sprite Main { fn main() -> int { import "library"; return 0; } }',
                encoding="utf-8",
            )
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main([str(source), "--check"]), 1)
            self.assertIn("import はまだサポートされていません", stderr.getvalue())

    def test_check_rejects_a_return_only_inside_a_while_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text(
                "sprite Main { fn main() -> int { let x: int = 0; while x < 0 { return 1; } } }",
                encoding="utf-8",
            )
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main([str(source), "--check"]), 1)
            self.assertIn("functionから帰りません", stderr.getvalue())

    def test_check_rejects_duplicate_local_names(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text(
                "sprite Main { fn main() -> int { let value: int = 0; let value: int = 1; return value; } }",
                encoding="utf-8",
            )
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main([str(source), "--check"]), 1)
            self.assertIn("すでに'value'は存在します", stderr.getvalue())

    def test_check_reports_list_valued_object_fields_as_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text(
                "class Box { let values: list int; } sprite Main { fn main() -> int { return 0; } }",
                encoding="utf-8",
            )
            stderr = StringIO()
            with redirect_stderr(stderr):
                self.assertEqual(main([str(source), "--check"]), 1)
            self.assertIn("list 型フィールドはまだサポートされていません", stderr.getvalue())

    def test_force_type_allows_scratch_coercion(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.nc"
            source.write_text(
                'sprite Main { fn main() -> int { let value: string = "2"; value = value * value; return 0; } }',
                encoding="utf-8",
            )
            self.assertEqual(main([str(source), "--check", "--force-type"]), 0)
            self.assertEqual(main([str(source), "--check"]), 1)
